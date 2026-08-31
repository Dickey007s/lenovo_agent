# DR-0054 Task Ledger V1 工程 Evidence（2026-08-31）

## 1. 结论与证据生命周期

- 状态：`Limited Verified`。
- 决策：[`DR-0054`](../decisions/DR-0054-durable-task-ledger-and-current-run-cas.md)。
- 场景：[`SCENARIO-040`](../scenarios/SCENARIO-040-task-current-run-cas-and-restart.md)。
- 测试合同：[`TASK-LEDGER-V1-GATES-20260831`](../testing/TASK-LEDGER-V1-GATES-20260831.md)。
- 代码审计基线：`5d5f33a`；Luna 实现/测试原始提交
  `57455c6`、`1c50ca9`、`78b9e07`、`be6fae0`、`043dfe0`、`e12ea9a`、`ab95c8d`；文档分支
  对应提交 `fc52b28`、`296caf2`、`0bb4650`、`0bd0aa6`、`c3bcf78`、`304ffe2`、`1f58e6f`。

本 Evidence 只证明被列出的 owner-scoped Task record、双版本 continuation、
current/history 前台和 fail-closed 恢复合同在当前自动化边界成立。它不证明真实
PostgreSQL Task 恢复、多实例执行、Provider 质量、业务结果正确或用户体验改善。

## 2. 场景与研究依据

目标场景不是“再增加一个任务列表”，而是两个页面从同一终态 parent Run 同时继续时，
系统必须只承认一个 current child，同时保留 parent 与旧成果。设计参考：

- [OpenClaw Task Flow](https://docs.openclaw.ai/automation/taskflow)：durable Flow record、
  revision conflict 和 linked task records；
- [Restate Services](https://docs.restate.dev/foundations/services)：keyed persistent entity；
- [Restate State](https://docs.restate.dev/develop/ts/state)：可写 exclusive handler 与只读
  shared handler 的职责区分。

这些官方来源只支持“稳定实体 + 版本化写入 + 可查询当前状态”是成熟运行时模式；不证明
本项目与这些产品能力对等，也不证明其他 Agent 缺少办公 Task/Evidence 设计。

## 3. 当前实现事实

### 3.1 最小 Task authority

`TaskRecord` 只保存 Task/Owner、`task_version`、Workspace identity/revision、
current Run/sequence/parent 与时间。Branch、Budget、Event、ArtifactVersion 和 TaskCommit
仍归每个 Run Snapshot。公共 Task 查询从 current Run 派生状态、当前 Artifact/Commit 和
lineage，不在 Task 表复制第二套成果真相。

### 3.2 双版本与原子提交

- `run.version` 保护 parent Run 内状态；`task_version` 保护跨 Run current pointer。
- continuation 同时携带两种 expected version、Branch 和 owner-scoped idempotency key。
- 初始 start 与 continuation 通过 `HarnessStateStore.commit_task_transition` 在同一提交
  边界写入 Task、Run 和 start receipt；continuation 另写 Task receipt。
- sibling 请求只有一个能从同一旧 Task version 前移；同请求 replay 返回同一 child；
  不同 payload、旧 Run/Task version、历史 parent 或错误 Owner 都拒绝。

### 3.3 查询、恢复与隐藏边界

`GET /v1/harness/tasks/{task_id}` 是第十一个公开 path。它只对 Owner 返回 sanitized
current pointer、当前 Run 派生字段和最多 100 条近期 lineage；`lineage_total` 与
`lineage_truncated` 说明是否省略更早记录。Task 缺失但 Run 存在、current Run 缺失、
版本/identity/parent 链损坏时 fail closed，不合成 `unknown`，也不在 GET 时按时间猜选。
旧 Snapshot 只允许在 Runtime setup 中按连续 sequence 和完整 parent 链保守 backfill。

公共 API/DOM 不暴露 `owner_id`、数据库字段、内部路径、完整 hash、Prompt、CoT、raw
Provider response 或内部 digest。

## 4. 前台交互结果

- continuation 成功后，child 显示“当前 Run”；parent 与历史成果仍可查看。
- continuation 409 不先切换 SSE、不清空 parent，也不把动画当作 child 已创建。
- Task current pointer 不同于当前画面时，parent 标为“历史 Run”，用户可直接打开权威
  current Run。
- Task GET 失败不应永久锁住 fetch key；页面保留已渲染 Run，并提供重试路径。
- `version`/SSE sequence 可在 child 从 1 开始，因为它们属于 Run；`task_version` 才跨
  Run 单调前移。

这些浏览器检查证明请求字段、状态投影和被测响应式行为，不证明目标用户一定理解冲突。

## 5. 已执行验证

| 门 | 命令 | 结果 | 能证明 | 不能证明 |
| --- | --- | --- | --- | --- |
| Task/Demo 定向 Python | `uv run pytest -q tests/unit/test_task_ledger.py tests/unit/test_harness_runtime.py tests/unit/test_demo2_runtime.py tests/acceptance/test_demo1_demo2_fixed_scenarios.py` | `92 passed in 4.12s` | memory/API Task 状态机、Demo 1/2 回归 | 真实 DB/Provider |
| PostgreSQL 收集 | `uv run pytest -q tests/integration/test_postgres_task_ledger.py --collect-only` | `7 collected` | 七项门存在 | SQL 已执行 |
| PostgreSQL 本机 | `uv run pytest -q tests/integration/test_postgres_task_ledger.py` | `7 skipped in 0.22s`，无 `TEST_DATABASE_DSN` | skip 边界明确 | 真实事务/CAS/restart |
| 整库 Python | `uv run pytest -q` | `410 passed, 23 skipped in 277.38s` | 当前整库 Python 回归 | 23 项环境门后的真实外部系统 |
| Ruff | `uv run ruff check .` | `All checks passed!` | 当前整库 Python 静态规范 | 行为正确 |
| Web lint | `pnpm --dir apps/web lint` | 通过 | TypeScript 类型门 | 浏览器行为 |
| Web build | `pnpm --dir apps/web build` | 通过 | production build | 用户体验 |
| Task Ledger browser | `pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts --grep "Task Ledger\|Task GET failure\|current Run" --reporter=line` | `4 passed (13.9s)` | current/history、409、终态/非终态 GET retry mock | 真实 API/DB、用户理解 |
| 整库 browser | `pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts --reporter=line` | `68 passed (2.6m)` | 当前整库浏览器回归 | 目标用户理解与真实 PostgreSQL |

## 6. 竞争与负向门

当前测试明确覆盖：

1. 两个 sibling continuation 竞争同一 Task version，只有一个 child 成功；parent JSON、
   Event、Artifact/Commit 与 Run 数不被失败方改变。
2. 同幂等键同 payload replay 不重复前移；同 key 不同 payload/version 返回冲突。
3. Task 缺失但 Run 存在、store 失败、重复 sequence、断裂 parent、非法根 parent、current
   pointer 不一致或持久 payload Owner 不一致都 fail closed；legacy backfill 同样要求根 Run
   无 parent。
4. 101 条 lineage 返回 `lineage_total=101`、`lineage_truncated=true`，公共列表保留 current。
5. PostgreSQL 文件包含初始同幂等键竞争、不同 digest、sibling CAS、parent Run 与 Task
   双版本同事务校验、Task version 必须只递增 1、事务回滚、restart 与 current/lineage
   复读，但本机没有执行这些 SQL 路径。

## 7. 未关闭的门与剩余边界

### 7.1 TC-04 是长任务，不是本分支挂死

首次全量观察曾在
`test_all_twelve_local_scenarios_write_real_verified_artifacts[TC-04]` 等待较久。独立 Luna
诊断用 `-o faulthandler_timeout=10` 确认堆栈在
`scenario_effects.py::_run_fixed_command -> subprocess.run -> communicate`，随后让命令
自然完成：TC-04 为 `1 passed in 42.23s`，两个 `run_self_test.py` 约 17.5/16.2 秒且
`rc=0`；整个 `tests/unit/test_scenario_effects.py` 为 `35 passed in 228.01s`。相关源码与
本分支 parent blob 相同，所以这是既有真实 baseline/compile/self-test 成本，不是 Task
Ledger 回归。最终门随后完整通过 `410 passed, 23 skipped`，浏览器为 `68 passed`；本
Evidence 使用的是当前运行数字，不复用此前 `386 passed` 历史结果。

### 7.2 尚未执行

- 没有 `TEST_DATABASE_DSN`，Task Ledger 的真实 PostgreSQL 七项门全部 skip；
- 未运行付费/真实 Provider，不评价 Planner/Analyst 质量；
- 未做两个真实 API 进程、多实例 lease/notification、崩溃注入或高可用验证；
- 未实现 WorkUnit/Contribution ledger、durable Worker queue/lease 或远端 Worker；
- 未做目标用户研究，不能宣称当前/历史 Run 提示提升理解、信任或效率。

## 8. 可对外表述

可以说：当前 Demo 1 已有一个最小 Task authority，能在被测 memory/API/UI 范围内用
Task/Run 双版本阻止 sibling child 同时成为 current，并保留旧 Run/成果。

不能说：系统已经是生产级 durable Task/WorkUnit 平台、真实 PostgreSQL/多实例已通过、
任务结果正确，或这种交互已经被用户证明更清晰。
