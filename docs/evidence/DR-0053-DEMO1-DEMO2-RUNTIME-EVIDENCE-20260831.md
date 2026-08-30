# DR-0053 Demo 1/2 Runtime Evidence（2026-08-31）

## 结论

- 状态：`Limited Verified`。
- 证明范围：Demo 1 的同 Task child Run/单 Branch 续办，以及 Demo 2 的确定性拓扑准入、
  显式确认、最多三进程内只读 Worker、贡献采用门和统一成果投影，在列出的本地自动化
  范围内成立。
- 不证明：真实 Provider 的业务正确性或质量、真实 PostgreSQL 重启门、分布式 Worker、
  多实例 lease、生产 Connector、源文件写回、用户理解提升或业务收益。

原始机器可读记录保存在
[`demo1-demo2-runtime-20260831-validated-v2.json`](manifests/demo1-demo2-runtime-20260831-validated-v2.json)。
旧 `demo1-demo2-runtime-20260831-final.json` 的红灯与边界保持原样，没有用新结果覆盖历史。

## 实现谱系

- 开发分支：`codex/demo1-demo2-runtime-20260830`。
- 纵切基线 HEAD：`bb4894750c4a9a305c775687b7f73b62532e4ef0`。
- 前台可读性收尾：`b9d7e3b`。
- 公共 continuation 重核事实投影：`7214385b29f8007cd74d98300b9820c64ddce407`。
- 来源版本变化公共提示定向 E2E：`1a1c8d29d05bb549090c6b72489dacd75fcd4cd3`。
- Demo 1 桌面/390 px Task 时间线与来源变化可读性 E2E：
  `80391373e267b455997843f0dd064006816f59ff`。
- 文档和 Evidence 不把这些提交描述为通用分布式执行器；后续补丁必须 append-only 留痕。

## Demo 1 已证事实

1. `task_id` 与 `run_id` 分离；terminal parent 续办会创建同 `task_id`、新 `run_id` 的
   child Run，并递增 `run_sequence`。
2. child 只携带用户所选且由服务端批准的一个 `carried_branch_id`，其首轮来源严格等于
   该 Branch 的 `missing_file_refs` 或批准输入 refs。可选自然语言 instruction 不能扩大范围。
3. Snapshot 保存 `parent_run_id`、基线 ArtifactVersion/TaskCommit、Workspace revision、
   `recheck_file_refs` 与 `source_revision_changed`；公共 API 不再把后两项默认为空/false。
4. 旧 Run、旧 ArtifactVersion 和旧 TaskCommit 不被重开或改写。child 收到合法 Snapshot
   后浏览器才切换 SSE generation；失败请求保留 parent UI。
5. UI 展示 Task 时间线、“继续未完成任务”、为何创建新 Run、批准来源和来源版本变化提醒。

这仍不是独立 durable Task ledger。Task current pointer、多个 child 的并发仲裁、per-file
内容 revision 和多实例 CAS 尚未实现。

## Demo 2 已证事实

1. Validated plan 由服务端确定性编译为 `single_controller`、`fixed_workflow` 或
   `adaptive_readonly_workers`。输入只包括工作单元宽度、独立 Branch、依赖并行度、冻结
   来源结构/span、剩余 calls/time 和 `external_action=none`。
2. 同一职能/同结构资料、风险/人工门、独立 roots 超过三条或预算不足时保持保守路线。
   只有 adaptive route 等待显式确认；未确认前不启动 Worker。
3. 每波最多三个进程内只读 Analyst Worker，只读取 ready Branch 的批准 refs。模型返回、
   `model_called` 和 `output_used` 分开；无 Anchor、越 Branch 来源、叙事对账拒绝或异常的
   候选不能合入。
4. adopted 贡献由稳定规则合入普通 append-only ArtifactVersion/TaskCommit。一个 Worker
   失败或 ambiguous 时，其他 adopted 贡献与既有成果保留。
5. findings/Artifact 治理上限提高到 96；11 条 Worker findings 的回归测试证明不再静默
   截为三条。这不证明模型能穷举所有业务事实。
6. UI 只显示一个业务驾驶舱：路线理由、结构事实、确认、实际 Worker 回执、下一波 ready
   Branch 和统一成果；不显示多个 Worker 聊天窗口。

当前没有 durable Worker queue/lease、远端 Worker、递归 Swarm、Worker 专属持久
DecisionRequest 或通用 ConflictRecord。

## 自动化记录

| 门 | 结果 | 能证明 | 不能证明 |
| --- | --- | --- | --- |
| `uv run pytest -q tests/unit --disable-warnings --maxfail=1` | `383 passed` | 本提交范围内的 Python unit 合同与负向路径 | 真实数据库、Provider、用户价值 |
| `pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts --reporter=line` | `64 passed / 0 failed` | 受控 mock API 下的全量浏览器回归，含 Demo 1/2 | Provider/数据库端到端业务效果 |
| `uv run ruff check .`、compileall、Web lint/build | 通过 | 静态/构建门 | 运行质量与业务正确性 |
| 公共投影与字号收尾定向 Python | `65 passed` | `recheck_file_refs`/`source_revision_changed` round-trip 与目标 Runtime 回归 | 真实 source revision 变化 |
| Demo 1/2 定向 Playwright | 每次 `2 passed`；基础面板、来源变化条件式提示、390 px 收尾均通过 | 新面板、来源变化、批准重核范围和 Task 时间线可见，关键字号与桌面/390 px 无横向溢出 | 目标用户认为更清晰 |
| `tests/integration/test_postgres_demo1_demo2.py` | 收集 3 项，`3 skipped` | 测试代码可收集 | PostgreSQL 门未执行，绝不能写“通过” |
| 真实 Provider | 未运行 | 没有产生未授权付费调用 | 不证明真实计划、Worker、Finding 或成果质量 |

## PostgreSQL 待执行门

已提交的三个 integration case 分别覆盖：

1. Demo 1 child lineage、CAS、幂等 replay、Owner 边界与 restart；
2. Demo 2 adopted Worker Artifact/receipt 在 restart 后保留且不重放；
3. 已预留但中断的 Worker 调用在 restart 后不自动重放。

本机没有可用 `TEST_DATABASE_DSN`；另一次连接尝试约 120 秒无输出后安全中止，记为
`blocked_external`。只有在真实 PostgreSQL 环境中三项实际通过，才可升级该门。

## 场景映射

- [`SCENARIO-038`](../scenarios/SCENARIO-038-durable-task-continuation-across-runs.md)：
  同一办公任务跨 Run 延续而不覆盖历史。
- [`SCENARIO-039`](../scenarios/SCENARIO-039-explainable-topology-and-verified-worker-convergence.md)：
  可解释路线准入、显式确认与受限 Worker 的统一成果收敛。
- 手工与自动化试用步骤见
  [`DEMO1-DEMO2-USER-VALIDATION-CASES-20260831`](../testing/DEMO1-DEMO2-USER-VALIDATION-CASES-20260831.md)。

## 剩余边界

`Limited Verified` 不是“功能完整”或“效果已证”。下一次升级必须分别留下：真实
PostgreSQL 结果、受控 Provider manifest、固定公开 FORTE 场景的前后端对账、异常截图，
以及目标用户能否正确理解继承范围、路线理由、Worker 采用与失败影响的形成性研究。
