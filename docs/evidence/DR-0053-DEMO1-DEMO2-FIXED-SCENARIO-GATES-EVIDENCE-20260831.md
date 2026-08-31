# DR-0053 Demo 1/2 固定场景门 Evidence（2026-08-31）

## 结论

- 状态：`Limited Verified`，仅限固定 Fixture、真实进程内 Runtime、真实 FastAPI 路由
  和既有浏览器 mock API 投影。
- 新增聚焦入口：
  `tests/acceptance/test_demo1_demo2_fixed_scenarios.py`，三组场景均通过。
- 证明范围：Demo 1 的单 Branch continuation 不覆盖父 Run；Demo 2 的五工作包
  adaptive 两波局部收敛，以及三期同结构财务不被 Prompt 强制升级为 Worker 路线。
- 不证明：真实 Provider 输出质量、真实 PostgreSQL 重启、多实例 Worker、源文件写回、
  用户理解改善或业务收益。

验收合同见
[`DEMO1-DEMO2-FIXED-SCENARIO-GATES-20260831`](../testing/DEMO1-DEMO2-FIXED-SCENARIO-GATES-20260831.md)。

## 留痕

| 类型 | 记录 |
| --- | --- |
| 用户授权 | `USER-FEEDBACK-20260831-DEMO1-DEMO2-FIXED-SCENARIO-HARDENING` |
| 文档合同提交 | `87af4df` |
| Luna 原始实现提交 | `bc927b96868dd0653bf0f644721194f45668aafa` |
| Luna 审计补强提交 | `9158daa18c64cfbc1398603681fa70d6042b8ad4` |
| 整合分支提交 | `765a093`、`810158b` |
| 数据边界 | 小型 allowlisted 合成 Catalog；未修改 FORTE 输入、未调用 Connector |

## FSG-D1：只继续一条未完成工作线

测试通过正常 `HarnessRuntime` 形成一个有完成 Branch、未完成 Branch 和 v1
ArtifactVersion 的终态 parent；测试 Fixture 仅为该 parent 补入可审计的 v1
`TaskCommit` 指针。随后通过真实
`POST /v1/harness/runs/{run_id}/continue` 创建 child。

已断言：

1. child 与 parent 的 `task_id` 相同，`run_id` 不同，`run_sequence+1`，并绑定准确的
   `parent_run_id/carried_branch_id`。
2. instruction 即使要求“重新检查整个资料库并扩大范围”，child Branch 的输入和缺失
   refs 仍不超出所选 Branch 的批准 refs。
3. Workspace revision 变化时公开 `source_revision_changed=true`；恢复原 revision 时为
   `false`。两条路径都保守公开相同的精确 `recheck_file_refs`。
4. 创建 child 前后的 parent Snapshot 全量 JSON 相同，因此其 Event、ArtifactVersion、
   TaskCommit、version 和状态没有被 continuation 改写。
5. 同幂等键重放返回同一 child；旧 expected version 返回 409；其他 Owner 请求返回
   403/404，不能从公共错误确认对象存在性。

这证明的是 continuation 合同和范围约束，不是独立 Task ledger。当前 Task/current
pointer 仍分散在 Run Snapshot 中，revision 仍以 Workspace 数据集级为主。

## FSG-D2A：五工作包两波局部收敛

固定计划包含三条 root 和两条 dependent Branch。服务端准入为
`adaptive_readonly_workers` 后先停在 `waiting_input`：Planner 已留下 1 次调用回执，
但 Analyst Worker 调用与 `worker_runs` 都为 0；等待确认没有偷偷启动 Worker。

第一波只提交三个 ready roots，注入两条 adopted 和一条 ambiguous：

- 形成只含两条已采用 finding 的 append-only v1 和 TaskCommit；
- ambiguous root 保持 `waiting_input`，只阻塞依赖它的下游；
- 另一条依赖已满足的 Branch 成为唯一 `ready_branch_id`；
- 直接提交 blocked Branch 会抛 `HarnessConflictError`，且拒绝前后 Snapshot、version、
  Events、ArtifactVersion 和 TaskCommit 完全不变。

第二波只提交服务端 ready 的 dependent Branch，形成 v2；v1 的序列化内容保持不变，
v2 累计三条 finding，Worker 调用计数从 3 增至 4，Planner 仍只有 1 次调用。事件中同时
保留 `contribution_adopted`、`contribution_waiting` 和
`topology_workers_completed`，因此“返回”“采用”“等待”没有被合成一个状态。

这证明的是单进程、调用方提供 handler 的只读 Worker 合同，不是 durable queue、lease、
远端 Worker 或真实模型并发效果。

## FSG-D2B：三期财务保持固定流程

Fixture 提供三份同结构财务来源，并故意把 instruction 写成“请用多个 Agent 并行
处理”。服务端仍根据冻结的结构事实选择 `fixed_workflow`，而不是把 Prompt 当作拓扑
授权。

已断言普通 Planner 和 Analyst 各调用 1 次，`worker_runs=[]`，不存在名称含
`worker` 或 `contribution` 的事件，也没有 `topology_confirmation_required`。这证明
未启动 Worker 路线；三个业务成果的中文含义和响应式展示继续由既有浏览器门验证。

## 运行记录

| 命令 | 本次整合分支结果 | 可以证明 | 不能证明 |
| --- | --- | --- | --- |
| `uv run pytest -q tests/acceptance/test_demo1_demo2_fixed_scenarios.py tests/unit/test_demo2_runtime.py tests/unit/test_harness_runtime.py` | `68 passed in 3.50s` | 新固定场景门与相关 Runtime 回归 | Provider、数据库、用户价值 |
| `uv run ruff check tests/acceptance/test_demo1_demo2_fixed_scenarios.py tests/unit/test_demo2_runtime.py tests/unit/test_harness_runtime.py` | 通过 | 目标 Python 静态门 | 运行效果 |
| `pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts --grep "Demo 1/2 runtime acceptance" --reporter=line` | `2 passed in 33.6s` | mock API 下的 Task 时间线、来源变化、Worker 确认/回执、两波和 390 px 投影 | 真实 Runtime 与浏览器联机、用户觉得清楚 |
| `uv run pytest -q` | `386 passed, 16 skipped in 302.74s` | 整库 Python 回归；新门已被默认收集 | 被环境门跳过的数据库/外部集成 |
| `uv run ruff check .` | 通过 | 整库 Python 静态门 | 运行质量 |
| `pnpm --dir apps/web lint` | 通过 | TypeScript 类型门 | 浏览器行为 |
| `pnpm --dir apps/web build` | 通过 | Next.js 生产构建 | 部署与用户效果 |
| `pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts --reporter=line` | `64 passed in 2.5m` | mock API 下的整套浏览器回归 | 真实 Provider/数据库端到端 |
| `uv run pytest -q tests/unit/test_reporting_governance.py`、Markdown 相对链接检查、`git diff --check` | `4 passed`、7 个变更文档链接通过、无 whitespace error | 文档治理和本轮链接完整性 | 外部网页永久可用、文档结论自动正确 |

本次 16 个 pytest skip 保持为环境门未执行事实，没有升级为通过。其中现有 Demo 1/2
PostgreSQL integration 仍需要真实 `TEST_DATABASE_DSN`；Provider 和用户研究也未运行。

## 下一步门

1. 在真实 `TEST_DATABASE_DSN` 下运行现有 Demo 1/2 PostgreSQL 顺序恢复门。
2. 将 Task current pointer、WorkUnit/Contribution/Worker reservation 从 Run Snapshot
   内嵌状态升级为可查询、可 CAS 的持久记录；仍先做单实例顺序语义。
3. 只有确定性门与 PostgreSQL 门都通过后，才为固定公开任务授权一次真实 Provider
   manifest；Provider 成功也不替代业务正确性验证。
4. 最后让目标用户完成 continuation、adaptive 正例和 fixed 反例，记录理解正确率、
   恢复步数和误触发，而不是用自动化代替用户研究。
