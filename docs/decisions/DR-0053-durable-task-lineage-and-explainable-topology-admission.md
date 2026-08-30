# DR-0053：跨 Run 任务谱系与可解释协作拓扑准入

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Proposed`；尚未形成工程 Evidence，不得写成当前能力 |
| 日期 | 2026-08-30 |
| 用户来源 | `USER-FEEDBACK-20260830-DEMO1-DEMO2-CONTINUATION` |
| 研究 | [`DEMO1-DEMO2-DURABLE-TASK-AND-ADAPTIVE-ORCHESTRATION-RESEARCH-20260830`](../research/DEMO1-DEMO2-DURABLE-TASK-AND-ADAPTIVE-ORCHESTRATION-RESEARCH-20260830.md) |
| 场景 | [`SCENARIO-038`](../scenarios/SCENARIO-038-durable-task-continuation-across-runs.md)、[`SCENARIO-039`](../scenarios/SCENARIO-039-explainable-topology-and-verified-worker-convergence.md) |
| Evidence | 待实现后新增，不复用历史 Demo 1/2 截图冒充 |

## 问题

当前 Agent Control Loop 已从历史最多三轮发展为默认最多 12 轮的单 Controller 有界
Runtime，并具备 Run 内 Branch、分支级 Evidence Gate、append-only 逻辑
`ArtifactVersion`/`TaskCommit`、有限成果适配器、Snapshot/named SSE 和可选 PostgreSQL
恢复。但仍存在两个产品断点：

1. Run 到达终态或预算边界后，用户只能新建另一个 Run；服务端没有稳定业务 Task
   身份，也不能审计“新 Run 继承了什么、什么必须重核”。简单继续扩大单 Run 预算会
   隐藏这个断点，并使成本、来源变化和故障恢复更难说明。
2. Planner 可以分解多个工作单元，但仍由单 Controller/Analyst 路径执行。若直接增加
   Worker，系统会退化为“模型决定开几个 Agent、多个回答最后再合成”，无法证明路线
   合理、贡献可信、失败局部化或用户得到更清楚的结果。

## 决策

在现有八个统一模块内分两层推进，不新增第九模块，不恢复 Demo 专属 API。

### 1. Demo 1：新增跨 Run 稳定 Task lineage

1. 在模块 2 `Task Contract` 中引入服务端生成的稳定 `task_id`。`run_id` 继续标识一次
   有界执行，两者不得混用。
2. 一个后继 Run 必须绑定 `task_id`、`parent_run_id`、基线 `TaskCommit`、继承的
   Branch/Artifact、冻结来源 revision 与重核原因。
3. 只允许从 terminal 或明确 budget-stopped Run 创建后继 Run；旧 Run Snapshot、Event、
   ArtifactVersion、TaskCommit 永远不改写。
4. 用户只选择需要继续的工作线。服务端重新校验 owner、expected version、幂等键、
   来源 revision 和 Branch 归属；未选分支不重跑。
5. 来源未变化的已核对事实可作为 carried context；来源变化、完整性失败、过期 Anchor、
   未完成模型调用和待决高风险事项必须重核，不得静默继承。
6. 前台操作命名为“在同一任务下继续”，并明确这是一个新的有界 Run，而不是给旧 Run
   无限加轮次。

### 2. Demo 2：先准入，再启动受限只读 Worker

1. 在模块 4 `Admission, Policy Compiler & Plan Validator` 中新增服务端拥有的
   `TopologyAdmission`。首个纵切只产生三种可执行路线：
   `single_controller`、`fixed_workflow`、`adaptive_readonly_workers`。
2. 07-16 的 `direct_tool` 保留为目标路线，但在通用 Tool Gateway 未实现前只能返回
   unavailable/target，不得由固定适配器或前台动画冒充。
3. Admission 只使用冻结的结构事实：来源跨度、工作包独立性、依赖耦合、预算、
   side-effect/risk 与可验证收益依据。模型可以建议，不拥有最终路线。
4. `adaptive_readonly_workers` 必须显式显示预计 Worker 上限和预算，并由用户确认后
   才能启动。首个纵切最多三个并发 Worker，不允许递归增兵。
5. 模块 5 `Scheduler & Worker Manager` 只调度由 validated plan 编译出的 Branch/WorkUnit；
   Worker 只能读取批准来源，不能写源文件、调用 Connector 或代表用户批准其他 Worker。
6. 模块 7 `Artifact Workspace & Verifier` 把每个 Worker 返回视为 Contribution candidate。
   候选必须通过现有 file membership、Evidence Anchor、Branch Evidence Gate 和适用的
   deterministic-outcome/narrative reconciliation，才能进入共享成果。
7. 合并由稳定服务端规则完成。开放冲突、stale 来源、无 Anchor 或被拒贡献不得进入
   当前 Artifact；最后返回、文字更长或置信语气更强都不构成覆盖权。
8. 一个 Worker 失败只暂停其 WorkUnit/Branch。已采用 Contribution、旧 ArtifactVersion
   和其他 Worker 的完成状态保留；恢复只新增版本，不原地改写。

## 八模块归属

| 现有模块 | 本决策新增职责 | 明确不做 |
| --- | --- | --- |
| 1. Workspace Catalog & Safe Preview | 为继承/Worker 重核来源 revision 与安全 Preview | 不提供生产 Connector |
| 2. Task Contract | 稳定 `task_id`、Run lineage、继承合同 | 不把聊天 session 当业务 Task |
| 3. Planner | 提议工作包、依赖和路线候选 | 不决定最终拓扑或直接启动 Worker |
| 4. Admission, Policy Compiler & Plan Validator | 编译/拒绝拓扑、预算和工作包范围 | 不以模型自评收益作为事实 |
| 5. Scheduler & Worker Manager | 有界只读 Worker、依赖、局部暂停与收尾 | 不做递归 Swarm、多实例 lease |
| 6. Tool Gateway | 保留 `direct_tool` 目标接口 | 本阶段不接真实工具/Connector |
| 7. Artifact Workspace & Verifier | Contribution Gate、确定性合并、新 ArtifactVersion | 不做通用语义证明器 |
| 8. Checkpoint, Event & Governance Control | Task/Run 谱系、Admission/Worker receipts、PG 恢复 | 不声称 HA、在途 HTTP 续跑 |

## 拟议公开合同

字段名是实现约束候选；开发时可按现有命名规范调整，但语义不得丢失。

### Task 与 Run lineage

| 对象 | 必需字段 | 语义 |
| --- | --- | --- |
| `TaskIdentity` | `task_id`、`owner_id`、`created_at` | 跨 Run 稳定业务任务身份 |
| `RunLineage` | `run_id`、`task_id`、`parent_run_id`、`lineage_depth` | 一次有界执行及父子关系 |
| `ContinuationContract` | `source_run_version`、`carried_branch_ids`、`base_artifact_version`、`base_task_commit_id`、`source_revision`、`recheck_items` | 本次继承与重核边界 |
| `ContinuationReceipt` | `created_run_id`、`applied_version`、`idempotency_ref`、`carried_count`、`recheck_count` | 服务端实际创建结果 |

### Topology 与 Worker

| 对象 | 必需字段 | 语义 |
| --- | --- | --- |
| `TopologyAdmission` | `route`、`state`、`reason_codes`、`policy_version`、`estimated_model_calls`、`max_parallel_workers`、`benefit_evidence`、`requires_confirmation` | 路线建议与准入事实 |
| `WorkUnit` | `work_unit_id`、`branch_id`、`dependency_ids`、`allowed_file_refs`、`status` | 服务端批准的工作包 |
| `WorkerReceipt` | `worker_run_id`、`work_unit_id`、`called`、`returned`、`elapsed_ms`、`output_used`、`stop_reason` | 实际 Worker 执行与采用分离 |
| `Contribution` | `contribution_id`、`work_unit_id`、`finding_ids`、`evidence_resolution_ids`、`revision`、`status`、`rejection_reason` | 进入共享成果前的候选 |
| `MergeReceipt` | `input_contribution_ids`、`adopted_ids`、`rejected_ids`、`conflict_ids`、`artifact_version`、`merge_policy_version` | 服务端合并结果 |

### 状态与事件

- Admission：`proposed / confirmation_required / admitted / downgraded / rejected`。
- WorkUnit：`pending / blocked / running / waiting_input / completed / failed / cancelled`。
- Contribution：`candidate / verified / adopted / rejected / stale / conflicted`。
- 建议 named SSE：`task_continuation_created`、`topology_admission_proposed`、
  `topology_admitted`、`work_unit_started`、`worker_returned`、
  `worker_contribution_adopted`、`worker_contribution_rejected`、
  `work_unit_waiting_input`、`contributions_merged`。

事件仍只是 Snapshot 的有序投影；前台断线后必须 GET 对账，不能仅凭 SSE 推断当前态。

## 路线准入规则

首版规则必须确定性、可测试、可解释，不能把一个不可见综合分数当作答案。

| 条件 | 路线倾向 | 理由 |
| --- | --- | --- |
| 单来源、单工作包或强顺序依赖 | `single_controller` | 并行没有真实工作面 |
| 多份同结构来源、稳定规则、顺序合并 | `fixed_workflow` | 确定性适配器优先于重复模型调用 |
| 至少两个独立工作包、跨来源、预算充足、只读、无开放高风险动作 | `adaptive_readonly_workers`，需确认 | 并行有可验证工作面，但成本更高 |
| 预算不足、依赖高度耦合、完整性失败 | downgrade/reject | 不允许为了展示多 Agent 破坏安全边界 |
| 存在真实工具/外部动作诉求 | 当前 `direct_tool` unavailable，转人工或只形成提案 | 模块 6 尚未接入 |

`benefit_evidence` 只允许 `unknown / structural_parallelism / measured_baseline`。
没有同场基线时一律不得显示具体节省百分比、质量提升或 ROI。

## 前台交互影响

### Demo 1

用户在一个 Task 页面中查看多段 Run 历史。每段 Run 有自己的预算、状态和成果，但
共享稳定任务目标。终态页面可选择一条未完成/受影响 Branch，前台先预览：

- 将继承哪些完成事实和成果版本；
- 哪些来源因 revision 变化需要重核；
- 新 Run 的预算和外部动作边界；
- 旧 Run 与旧成果不会被覆盖。

创建成功后，新 Run 出现在同一时间轴中。用户不需要复制旧 Prompt，也不会误以为
旧 Run 被重新打开。

### Demo 2

前台不做多 Agent 聊天墙，而在统一驾驶舱中增加三个层级：

1. **路线建议**：推荐路线、业务化理由、预算、风险和“收益未知”边界。
2. **工作包**：依赖、批准来源、实际 Worker 状态、等待/失败影响。
3. **统一成果**：已采用/未采用 Contribution、冲突、Evidence、ArtifactVersion。

只有 `confirmation_required` 的高成本只读 Worker 路线显示确认按钮。普通单 Controller
和固定流程直接按既有合同运行；`direct_tool` 未实现时显示不可用，不提供假按钮。

## UI—服务端事实映射

| 前台文案 | 服务端事实 | 禁止推断 |
| --- | --- | --- |
| 同一任务的新一段执行 | `task_id` 相同、`parent_run_id` 有值、新 `run_id` | 旧 Run 被修改或无限续命 |
| 已继承 2 条工作线，1 项需重核 | continuation carried/recheck 明细 | 旧来源天然仍正确 |
| 推荐固定流程 | Admission `route=fixed_workflow` + reason codes | Worker 已启动 |
| 建议 3 个只读 Worker，等待确认 | `confirmation_required` + `max_parallel_workers=3` | 多 Worker 一定更快/更好 |
| Worker 已返回、结果未采用 | `returned=true/output_used=false` + Contribution rejection | Worker 没调用或整个任务失败 |
| 2 项可用，1 项待核对 | 两项 adopted、一项 waiting/conflicted | 最终任务已全部正确 |
| 已形成 v2，v1 保留 | 新 ArtifactVersion/TaskCommit | 源文件被回滚或写回 |

## 安全与治理

- Owner、expected version 与幂等语义覆盖 continuation、Admission 确认和 WorkUnit 控制。
- Worker 只获得批准来源的最小范围；公共 API/DOM 不暴露 raw hash、绝对路径、Prompt、
  CoT、Provider response、密钥或内部验证表达式。
- Catalog/Preview 完整性失败继续 fail closed。普通 Contribution 定位失败局部化；不能把
  安全完整性失败降级为可忽略的 Worker 警告。
- 当前 `external_action=none` 保持不变。任何发送、付款、生产变更或真实 Connector
  均不在本决策首版范围。
- `X-User-Id` 仍是演示 Owner，不构成生产身份。

## 验证门

### Demo 1 必须通过

- 终态/预算停止 Run 创建后继 Run，`task_id` 不变、`run_id` 改变，旧 Snapshot/Event/
  Artifact/Commit bytes 不变。
- 只继承用户选择的 Branch；来源 revision 变化转为 recheck，不能静默采用旧 Anchor。
- 相同幂等键不重复创建；旧 expected version 返回 409 且无状态变化。
- PostgreSQL 两次重启后 lineage、等待决定和当前 Artifact 指针一致。
- SSE 断线恢复和 final GET 不产生倒序状态。
- 1440/390 px 能看到父 Run、继承、重核、新预算与历史成果入口。

### Demo 2 必须通过

- 相同冻结合同得到相同 route/reason；单来源、强依赖、预算不足负例不启动 Worker。
- `adaptive_readonly_workers` 未确认前没有 Worker/模型调用；确认后并发不超过 3。
- 至少 4 个 WorkUnit 覆盖依赖、延迟、失败、歧义与成功；无 orphan unit。
- 无来源、stale、篡改、错误算术或对账冲突的 Contribution 不进入 Artifact。
- 一个 Worker 失败时其他 adopted Contribution 与旧 Artifact 保留；只恢复目标 WorkUnit。
- named SSE、Snapshot、PostgreSQL、幂等控制和浏览器投影一致。
- 前台不显示内部 Agent 聊天，不把 `returned` 写成 adopted，不把推荐写成执行。

工程门至少包括 unit、真实 PostgreSQL integration、真实 Provider 受控运行、API/DOM
敏感字段扫描、1440/390 Playwright 与下载成果独立解析。自动化只能把决策升级到限定
工程 `Limited Verified`，不能升级用户价值判断。

## 拒绝的替代方案

1. **继续把单 Run 轮数放大。** 拒绝。预算只是安全边界，不能替代跨 Run 任务身份、
   来源重核和历史不可变性。
2. **模型输出几个 Worker 就启动几个。** 拒绝。模型不拥有预算、风险或路线准入。
3. **所有复杂任务默认 Swarm。** 拒绝。官方实践明确多 Agent 有协调和 Token 成本，
   强依赖任务可能更差。
4. **用多个聊天窗口作为 Demo 2。** 拒绝。它把上下文搬运和结果收敛责任交给用户。
5. **让 synthesis Agent 决定最终真相。** 拒绝。合并必须服从服务端来源、Evidence、
   deterministic outcome 与版本合同。
6. **复活历史固定 Customer A/Demo API。** 拒绝。Demo 是通用 Runtime 的验收视角，
   不是产品模式或隐藏脚本入口。

## Claim Ledger

| Claim | 状态 | 依据 | 升级条件 |
| --- | --- | --- | --- |
| 当前已有 Run 内分支、成果版本与可选 PG 恢复 | `Current` | 当前源码/living docs | 保持回归测试 |
| 当前已有跨 Run Task lineage | `False` | 现行 Harness 无业务 `task_id` 协议 | 完成本决策 Demo 1 门 |
| 当前已有通用多 Worker Runtime | `False` | 当前是单 Controller | 完成本决策 Demo 2 门 |
| 路线准入是候选产品差异 | `Proposed` | 07-16 + 官方调研 | 同场基线和工程 Evidence |
| 统一驾驶舱提升理解/效率 | `Draft` | HAI 研究支持方向 | 目标用户形成性研究 |

## 边界

本决策不声称竞品不能实现 Task lineage、Evidence Gate 或服务端收敛；只规定本项目的
原生合同。它也不证明多 Worker 更快、更便宜、更正确，不实现真实 Connector、生产
身份、可写源文件、多实例 lease、HA 或外部动作。实现前所有新增能力保持 `Proposed`。
