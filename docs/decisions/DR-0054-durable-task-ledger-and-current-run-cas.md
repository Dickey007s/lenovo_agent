# DR-0054：独立 Task Ledger 与当前 Run 版本控制

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`；memory/API/browser 定向门通过，真实 PostgreSQL Task 门未运行 |
| 日期 | 2026-08-31 |
| 用户来源 | `USER-FEEDBACK-20260831-DEMO1-DEMO2-FIXED-SCENARIO-HARDENING` |
| 前置决策 | `DR-0053` 的有限 Task lineage 与固定场景门 |
| 研究 | `DURABLE-AGENT-RUNTIMES-OFFICIAL-20260830`、`DURABLE-ENTITY-STATE-OFFICIAL-20260831` |
| 场景 | [`SCENARIO-040`](../scenarios/SCENARIO-040-task-current-run-cas-and-restart.md) |
| 测试合同 | [`TASK-LEDGER-V1-GATES-20260831`](../testing/TASK-LEDGER-V1-GATES-20260831.md) |
| Evidence | [`DR-0054-TASK-LEDGER-V1-EVIDENCE-20260831`](../evidence/DR-0054-TASK-LEDGER-V1-EVIDENCE-20260831.md) |

## 问题

`DR-0053` 已经把 `task_id`、父子 Run、成果基线和来源重核范围放进每个 Run
Snapshot，并证明单线程 continuation 不改写 parent。`DR-0054` 实施前，Runtime 仍通过
扫描内存中全部 Run 计算下一个 `run_sequence`；没有独立 Task current pointer，也不能
对两个并发 continuation 做 Task 级版本仲裁。下列断点是本次实现要关闭的历史基线。

这会在用户流程中留下三个断点：

1. 两个页面同时从同一旧 Run 点击继续，Run 自身的 expected version 都可能合法，但
   Task 只能有一个明确的当前 Run；不能让前台自行猜测哪个 child 是当前工作面。
2. 重启后虽然每个 Run Snapshot 仍可恢复，用户仍缺少一个直接可查询的 Task 权威对象，
   无法一次回答“当前 Run、当前成果指针、历史 Run”分别是什么。
3. 后续 WorkUnit ledger 若没有稳定 Task 写入边界，会继续依赖 Snapshot 内嵌数组，难以
   做局部恢复、状态查询和 PostgreSQL CAS。

## 研究依据与不当推断边界

[OpenClaw Task Flow](https://docs.openclaw.ai/automation/taskflow) 把多步骤 Flow 保存为
独立 durable record，包含 revision、JSON state 与 linked task records；每次变更携带
expected revision，过期写入冲突而不是覆盖新状态。
[Restate Services](https://docs.restate.dev/foundations/services) 把 Virtual Object 描述为
按 key 隔离的持久实体，并以单写者语义协调同一 key 的并发修改；
[Restate State](https://docs.restate.dev/develop/ts/state) 区分可写 exclusive handler 和
只读 shared handler。

这些来源支持“稳定实体 + 版本化写入 + 可并发查询”是成熟运行时模式，不证明本项目应
采用这些产品、已经具备同等故障语义，或其他竞品缺少办公 Task/Evidence 设计。本项目
仍使用自己的 FastAPI/PostgreSQL 纵切，并只声明自动化实际覆盖的边界。

## 决策

### 1. Task 成为独立服务端记录

新增 Owner-scoped `TaskRecord`，只保存跨 Run 必须稳定且需要 CAS 的最小事实：

- `task_id`、`task_version`、`workspace_id`、`workspace_revision`；
- `current_run_id`、`current_run_sequence`、`parent_run_id`；
- `created_at/updated_at`。

`owner_id` 是服务端访问控制字段，不进入公共响应。Task 不是 chat session，也不是把
所有 Run 内容复制一遍；Run Snapshot 继续拥有单次执行、Branch、Budget、Event、
ArtifactVersion 和 TaskCommit 细节。公共 Task 查询从权威 `current_run_id` 指向的
Snapshot 派生当前状态、成果指针与完整 lineage，避免 Task 表和 Run 表分别保存同一成果
事实后发生漂移。若 current Run 不存在或 lineage 不一致，查询和恢复都必须 fail closed，
不能返回合成的 `unknown` 状态。

### 2. 两层 version 分工

- `run.version`：保护一个 Run 内的 pause/resume/steer/decision/worker 等状态变更。
- `task_version`：保护跨 Run current pointer 和 lineage 变更。

continuation 必须同时提交 parent `expected_version` 与 `expected_task_version`。任一过期
都返回 409，且不新增 child、Task 版本、Event、Artifact 或 Commit。成功创建 child 时，
Task version 只增加一次，并将 current pointer 指向 child；同幂等键 replay 返回同一
child，不再次增加版本。

### 3. 原子写入边界

Task record、child Run Snapshot 和 start idempotency receipt 必须在一个 State Store
commit 中生效。PostgreSQL 使用同一事务和条件更新；memory adapter 在同一锁内模拟相同
语义。不得出现以下中间态：

- child 已存在但 Task current pointer 仍指向 parent；
- Task 已前移但 child/幂等回执不存在；
- 两个不同 child 都从同一个 `expected_task_version` 成功。

### 4. 查询与前台

首版只增加 `GET /v1/harness/tasks/{task_id}`，不增加任务删除、任意切换 current、批量
改写或跨 Owner 查询。公共响应只返回当前 Task 摘要和 Run lineage，不暴露 raw hash、
内部路径、Owner ID、Prompt 或 Provider response。

Run 公共 Snapshot 增加 `task_version`。前台继续按钮同时提交两种 expected version；
Task 时间线明确标记“当前 Run”。若 Task CAS 冲突，页面保留原画面和 SSE generation，
提示用户刷新当前 Task，而不是先切换到一个未获权威指针的 child。

### 5. 旧数据恢复

新表不存在时 setup 可从同 Owner、同 `task_id` 的旧 Run Snapshot 做一次保守 backfill：

1. 按 `run_sequence` 验证为唯一递增 lineage；
2. 选择唯一最大 sequence 作为 current；
3. 若同一最大 sequence 对应多个 Run、父子关系损坏或成果指针不一致，fail closed，
   不按更新时间静默猜选；
4. backfill 不自动重放模型调用，也不修改旧 Run。

## 本阶段明确不做

- 独立 WorkUnit/Contribution ledger、Worker queue/lease、远端 Worker 和多实例 HA；
- per-file revision 服务、源文件写回、真实 Connector 或外部动作；
- Task list、删除、跨 Task 合并、任意 current pointer 回拨；
- 把 PostgreSQL 表创建或测试收集写成真实数据库恢复已通过。

WorkUnit ledger 是下一纵切：它将绑定本决策的 `task_id/task_version`，独立保存
WorkUnit 状态、依赖、最新 Contribution 和局部恢复版本，但不会与 Task V1 同批冒进。

## 前台交互影响

| 阶段 | 用户看到 | 用户可做 | 后端事实 | 禁止推断 |
| --- | --- | --- | --- | --- |
| parent 终态 | Task 时间线、当前 Run 标记、未完成 Branch | 选择一条继续 | Task/current Run + parent version | 旧 Run 会被重开 |
| continuation 成功 | 新 Run 成为当前；parent 与 v1 保留 | 进入 child、返回 parent | Task version +1、current pointer=child | child 已完成业务任务 |
| 两页竞争 | 后提交页面提示 Task 已更新 | 刷新并查看当前 child | stale `expected_task_version` 409 | 系统随机丢失任务 |
| 重启后 | 同一 Task/current Run/历史 Run | 从当前 Run 继续审查 | 独立 Task record + Run records | 在途模型调用被续跑 |
| ledger 完整性失败 | Task 暂不可继续 | 查看错误、联系维护 | setup/backfill fail closed | 选择最新时间即安全 |

## 验证门

1. 初始 Run 同时创建 version 1 Task record；Task 查询只对 Owner 可见。
2. continuation 原子创建 child 并将 Task version +1；parent bytes 不变。
3. 两个请求使用同一旧 Task version 时只有一个成功；失败方零状态变化。
4. 同幂等键 replay 不重复增加 Task version、run sequence 或 lineage。
5. memory store 重建 Runtime 后 Task current pointer 与 lineage 一致。
6. 旧 Snapshot backfill 唯一时成功、冲突时 fail closed。
7. PostgreSQL 测试必须包含条件更新和事务回滚；无 DSN 时明确 skip。
8. 浏览器标出当前/历史 Run，409 时不提前切 SSE 或覆盖 parent；Task GET 失败必须可重试。

当前 memory/API 定向门、Task Ledger browser mock、Ruff、lint 与 build 已通过；七项
PostgreSQL integration 已收集但因本机无 `TEST_DATABASE_DSN` 全部 skip。既有 TC-04
subprocess 经独立复核为约 42 秒的真实 baseline/compile/self-test 长任务，不是挂死或本
分支回归；相关 scenario-effect 文件 `35 passed in 228.01s`。当前整库 Python 为
`410 passed, 23 skipped`，整库 Playwright 为 `68 passed`。真实 Provider 和目标用户研究
未运行。因此本决策只能标 `Limited Verified`，
不能升级为生产 durable Task、WorkUnit/Worker durability 或用户价值结论。
