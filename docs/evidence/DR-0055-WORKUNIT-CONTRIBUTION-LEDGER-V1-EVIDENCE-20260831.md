# DR-0055 WorkUnit / Contribution Ledger V1 工程 Evidence

- 日期：2026-08-31
- 状态：`Limited Verified`
- 决策：[`DR-0055`](../decisions/DR-0055-durable-workunit-and-contribution-ledger.md)
- 场景：[`SCENARIO-041`](../scenarios/SCENARIO-041-workunit-contribution-ledger-and-partial-convergence.md)
- 测试合同：[`WORKUNIT-CONTRIBUTION-LEDGER-V1-GATES-20260831`](../testing/WORKUNIT-CONTRIBUTION-LEDGER-V1-GATES-20260831.md)

## 1. 本轮到底验证了什么

本轮在既有 `Task -> Run -> Branch -> ArtifactVersion/TaskCommit` 权威关系上，加入了
Branch 绑定的最小 `WorkUnitRecord` 和 append-only `ContributionRecord`。它解决的不是
“同时显示几个 Agent”，而是 Demo 2 的四个可核查问题：哪个工作包已经预留并实际调用、
哪个模型返回形成了候选、哪个候选获准进入统一成果、一个工作包中断后哪些兄弟成果仍然
成立。

当前源码实现并验证了以下有限纵切：

1. validated Branch DAG 先完整投影为 WorkUnit；`work_unit_id` 与 Branch 一一绑定，依赖和
   批准来源由服务端校验，公共投影不暴露 Owner、raw revision、内部 reservation digest
   或 Provider 原始回复。
2. Worker 调用前先持久化 reservation、attempt、预算和 `worker_wave_reserved`；调用开始、
   候选形成、采用/等待/失败和波次提交分别留下 named SSE，返回不等于采用。
3. 每次返回新增不可变 Contribution。已有 v1、兄弟 Branch 和已采用候选不会因局部失败、
   等待或后续重试被覆盖；新一波收敛只追加 v2。
4. PostgreSQL 重启遇到已预留或运行中的 Worker 时，保留 validated Branch DAG、
   `TopologyAdmission`、已完成 Contribution 和成果历史，把未确认的在途 WorkUnit 标成
   `checkpoint_recovered_in_flight_worker`，不自动重放模型调用。
5. 用户显式重试时必须使用新的幂等键、当前 Run version 和原 Branch 批准来源；原键原
   payload 只回放旧回执，原键配变化 payload 冲突。恢复后只重试目标 WorkUnit，attempt
   从 1 增至 2，其他 Branch 和 ArtifactVersion 保留。
6. 三期同结构财务任务继续由 `fixed_workflow` 处理，不创建 Worker WorkUnit、Contribution
   或 Worker named event，防止“有多 Agent 字样就强行并行”。

这是一条进程内只读 Worker 的持久执行台账，不是 durable queue、lease、远端 Worker、
多实例调度器或通用执行器。

## 2. 源码与协议事实

| 事实 | 当前实现位置 | 能证明什么 | 不能证明什么 |
| --- | --- | --- | --- |
| WorkUnit/Contribution 合同与公共脱敏 | [`harness_models.py`](../../packages/contracts/harness_models.py) | 状态、attempt、Branch/来源/候选关联有结构化合同 | 生产身份、跨租户授权 |
| 独立 Memory/PostgreSQL 台账与约束 | [`workunit_ledger.py`](../../services/api/app/application/workunit_ledger.py)、[`harness_storage.py`](../../services/api/app/application/harness_storage.py) | append-only、owner/scope、版本、依赖和 parent Run 条件检查 | 多实例 lease、分布式锁或高可用 |
| 预留、调用、候选、采用与恢复 | [`harness_runtime.py`](../../services/api/app/application/harness_runtime.py) | 模型调用前预留；局部返回与统一成果分开；重启不自动重放 | 在途 HTTP 续跑、远端 Worker 或外部动作 |
| 公共 API 与 UI | [`harness_routes.py`](../../services/api/app/api/harness_routes.py)、[`harness-workbench.tsx`](../../apps/web/app/harness-workbench.tsx) | Run Snapshot 可投影工作包和候选采用事实；前台使用业务标题和中文回执 | 用户理解、信任或效率已经改善 |

公开 API 没有新增 Demo 选择器或 WorkUnit CRUD。WorkUnit/Contribution 仍通过 Run
Snapshot 和现有 `/workers` 派发边界呈现；`worker_idempotency` 的 `reserved/completed`
内部值不会进入 `PublicHarnessRunSnapshot`。

## 3. 固定场景与负向门

### 3.1 五工作包两波收敛

[`test_demo2_runtime.py`](../../tests/unit/test_demo2_runtime.py) 验证五个 WorkUnit 先完整
建立：三个独立 root 构成第一波，两个 dependent 只在前置采用后进入第二波。第一波形成
3 条 Contribution，第二波累计 5 条；全部采用后 WorkUnit 均为 `adopted`，ArtifactVersion
分别绑定 v1/v2，并各有一次 `worker_wave_reserved` 与 `worker_wave_committed`。

### 3.2 局部等待与兄弟成果保留

[`test_demo1_demo2_fixed_scenarios.py`](../../tests/acceptance/test_demo1_demo2_fixed_scenarios.py)
验证第一波出现 adopted 与 waiting 混合状态时，五条 WorkUnit 投影仍完整，已采用
Contribution 与 v1 保留，只有依赖问题 Branch 的下游阻塞；继续其他可用分支后新增候选，
不清空先前成果。固定财务反例断言 `work_units == []`、`contributions == []`，且不存在
Worker/Contribution named event。

### 3.3 幂等、破损记录与恢复

单元与 PostgreSQL 集成门覆盖：重复 reservation 原键原 payload 零新增；变化 payload
冲突；越 Owner、orphan Branch、错误依赖、越界来源、空 Branch 投影、重复 Contribution、
非递增 version 和非整数 parent Run version 均 fail closed。重启只允许
`checkpoint_recovered_in_flight_worker` 的失败 WorkUnit 用新键显式回到 ready，不把普通
失败偷偷改成可重试。

## 4. 真实 PostgreSQL 门

本轮临时启动隔离 PostgreSQL 17.11，使用独立数据库用户、数据目录和端口运行：

```powershell
uv run pytest -q tests/integration/test_postgres_demo1_demo2.py tests/integration/test_postgres_task_ledger.py
```

最终结果：`10 passed in 10.84s`，其中 Demo 1/2 WorkUnit 重启门 3 项，Task Ledger 事务门
7 项。测试完成后 PostgreSQL 进程已停止，测试端口确认关闭。临时数据目录仍留在本机
`%TEMP%` 下，未使用破坏性清理命令；它不包含提交内容，也没有监听进程。
该结果是在公共 Owner 隔离、stale/contradictory 双重拒绝和 Runtime 聚合回滚三项终审
修复全部合入之后重新执行，不沿用修复前的数据库结果。

真实门之前保留了三次有价值的失败：首次因测试用户配置错误未进入业务验证；第二次暴露
测试把“同一键变化 payload”误写成无条件 replay；第三次先暴露重试使用过期来源，随后
进一步暴露重启恢复会删除 Worker Branch DAG。后两项推动测试改为严格幂等语义，并修复
Runtime，使 Branch/TopologyAdmission/已完成 Contribution 在 Worker checkpoint 恢复中
保留。这些失败不是最终通过证据，但说明门确实拦截了错误，而不是只验证表能创建。

合并前源码终审还发现 `PublicHarnessRunSnapshot` 继承了内部 `owner_id`。这与公共 API
不得泄露 Owner 的合同冲突。修复提交 `86fa40a` 从公共模型和 `public_snapshot()` 投影中
移除该字段，同时保留私有 Snapshot 与路由参数的 Owner 鉴权；新增 HTTP Run GET 与 SSE
JSON 负向断言。相关 Harness/Demo/Acceptance/WorkUnit 定向回归为
`73 passed in 8.51s`，Ruff 与 diff-check 通过。这个缺陷说明“内部对象有 Owner”与
“公共响应必须隐藏 Owner”必须由测试分别约束。

同一次终审又发现一个合入门 P1：叙事对账已判断 `stale` 或 `contradictory` 时，若候选
外层状态仍伪装成 adopted，旧 merge 路径可能继续接收。修复提交 `8ef059a` 在 Worker
结果规范化与 `merge_adopted_contributions` 两层都强制转为 rejected、
`output_used=false`；两组参数化负向测试确认 stale/contradictory 候选永不进入成果。
相关定向回归为 `75 passed in 3.13s`，Ruff 与 diff-check 通过。

终审最后补上 Runtime 聚合提交 failure injection。修复提交 `0a51db6` 在 reservation
持久化失败时恢复旧内存 Snapshot，保证 dispatch 前失败不会调用 handler，也不会让预算、
version 或幂等状态假前进；在 Worker 已返回但 merge 聚合提交失败时，Runtime 回到
reservation 后的安全状态，不留下 Artifact/Contribution/Commit，底层 storage transaction
继续负责数据库回滚。两阶段 failing-store 测试与相关定向回归为
`76 passed in 3.21s`，Ruff 与 diff-check 通过。

## 5. 最终工程门

| 验证 | 结果 | 说明 |
| --- | --- | --- |
| `uv run pytest -q` | `417 passed, 23 skipped in 283.30s` | skipped 项按各自环境合同保留；不冒充已运行 |
| 真实 PostgreSQL 定向组合 | `10 passed in 10.84s` | PostgreSQL 17.11，单主机顺序事务与重启门 |
| `uv run ruff check .` | 通过 | Python 静态检查 |
| `pnpm --dir apps/web lint` | 通过 | 前台 lint；最终文档收口后再次复核 |
| `pnpm --dir apps/web build` | 通过 | Next.js 16.2.10 production build |
| Playwright 全量 | `68 passed in 2.6m` | 包含工作包/候选中文标签、无 raw `u1`、1440/390 布局 |
| 公共 Snapshot 隐私终审 | `73 passed in 8.51s` | Run GET/SSE 不含 `owner_id`；内部 Owner 校验保留 |
| stale/contradictory 合入门终审 | `75 passed in 3.13s` | 规范化与 merge 双重拒绝 adopted-looking 候选 |
| Runtime 聚合提交 failure injection | `76 passed in 3.21s` | dispatch 前零调用；merge 失败无假 Artifact/Contribution/Commit |

Playwright 和固定 Fixture 能证明被测状态、操作和布局可重复，不是目标用户研究。真实
Provider 未在本轮重新调用，因此不能据此比较模型质量、Token 成本、延迟或多 Worker
收益。

## 6. 研究依据与交互后果

- [OpenAI Agents SDK: Agent orchestration](https://openai.github.io/openai-agents-python/multi_agent/)
  与 [Anthropic: How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
  支持按依赖选择代码编排和有限并行，而不是默认打开多个 Agent。前台因此先解释路线与
  并行条件，再让用户确认；强依赖财务任务保留固定流程。
- [A2A Protocol specification](https://a2a-protocol.org/latest/specification/) 区分 Task 状态、
  Artifact、按序事件和 `input-required`。本项目据此把 WorkUnit 执行、Contribution 候选
  和 Artifact 采用分开，但不宣称实现或兼容 A2A。
- [Microsoft Research: Guidelines for Human-AI Interaction](https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/)
  支持及时说明状态、能力边界、后果和纠错入口。前台因此显示“实际执行回执”“候选成果”
  “原文定位”和局部失败影响，隐藏 reservation、digest 与内部 validator。

这些官方来源支持设计方向，不是竞品同场实测，也不能从文档未提及推断竞品做不到。

## 7. 剩余边界

- 没有 durable/distributed queue、Worker lease、远端 Worker、多实例 ownership 或 HA；
- 没有 Worker 专属 pause/cancel/DecisionRequest；显式重试仍经过现有受控派发入口；
- 没有真实 Tool Gateway、Connector、源文件写回或外部动作；
- Anchor 只证明位置与批准来源 membership，不证明语义、穷举、算术或业务正确；
- 没有真实 Provider 对照、目标用户研究或业务 KPI，因此不能声称更快、更准、更省成本，
  也不能声称用户已经更容易理解。
- failure injection 已覆盖 reservation 与 merge 两个聚合持久化点，但没有穷举进程终止、
  驱动断连、网络分区、磁盘损坏或多实例竞争，不能扩大成任意故障点或 HA 保证。

结论仅为：Demo 2 已从 Snapshot 内的临时 Worker 投影推进到 Branch 绑定、Memory/PostgreSQL
可恢复、候选 append-only 且可与统一成果对账的有限纵切；完整 Scheduler & Worker
Manager 仍未实现。
