# DR-0053：跨 Run 任务谱系与可解释协作拓扑准入

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`；仅限本决策列出的本地合同、Runtime 与浏览器自动化范围 |
| 日期 | 2026-08-30；实现与研究复核 2026-08-31 |
| 用户来源 | `USER-FEEDBACK-20260830-DEMO1-DEMO2-CONTINUATION` |
| 研究 | [`DEMO1-DEMO2-DURABLE-TASK-AND-ADAPTIVE-ORCHESTRATION-RESEARCH-20260830`](../research/DEMO1-DEMO2-DURABLE-TASK-AND-ADAPTIVE-ORCHESTRATION-RESEARCH-20260830.md) |
| 场景 | [`SCENARIO-038`](../scenarios/SCENARIO-038-durable-task-continuation-across-runs.md)、[`SCENARIO-039`](../scenarios/SCENARIO-039-explainable-topology-and-verified-worker-convergence.md) |
| Evidence | [`DR-0053-DEMO1-DEMO2-RUNTIME-EVIDENCE-20260831`](../evidence/DR-0053-DEMO1-DEMO2-RUNTIME-EVIDENCE-20260831.md)；[`DR-0053-DEMO1-DEMO2-FIXED-SCENARIO-GATES-EVIDENCE-20260831`](../evidence/DR-0053-DEMO1-DEMO2-FIXED-SCENARIO-GATES-EVIDENCE-20260831.md)；原始门禁清单 [`demo1-demo2-runtime-20260831-validated-v2.json`](../evidence/manifests/demo1-demo2-runtime-20260831-validated-v2.json) |

## 问题

本决策形成时，Agent Control Loop 已从历史最多三轮发展为默认最多 12 轮的单
Controller 有界 Runtime，并具备 Run 内 Branch、分支级 Evidence Gate、append-only
逻辑 `ArtifactVersion`/`TaskCommit`、有限成果适配器、Snapshot/named SSE 和可选
PostgreSQL 恢复，当时存在两个产品断点：

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
5. 当前纵切采取保守策略：所选 Branch 的批准来源始终进入 `recheck_file_refs`，旧模型
   采用事实不作为 child 权威；来源变化额外令 `source_revision_changed=true`。未来若要
   直接携带已核对事实，必须另加 per-file revision/Anchor 有效性门。
6. 前台操作命名为“继续未完成任务”，并明确这是一个新的有界 Run，而不是给旧 Run
   无限加轮次。

### 2. Demo 2：先准入，再启动受限只读 Worker

1. 在模块 4 `Admission, Policy Compiler & Plan Validator` 中新增服务端拥有的
   `TopologyAdmission`。首个纵切只产生三种可执行路线：
   `single_controller`、`fixed_workflow`、`adaptive_readonly_workers`。
2. 07-16 的 `direct_tool` 保留为目标路线，但在通用 Tool Gateway 未实现前只能返回
   unavailable/target，不得由固定适配器或前台动画冒充。
3. Admission 只使用冻结的结构事实：来源跨度、工作包独立性、依赖耦合、预算和
   side-effect/risk。模型可以建议，不拥有最终路线；当前没有收益预测字段。
4. `adaptive_readonly_workers` 必须显式显示预计 Worker 上限和预算，并由用户确认后
   才能启动。首个纵切最多三个并发 Worker，不允许递归增兵。
5. 模块 5 `Scheduler & Worker Manager` 只调度由 validated plan 编译出的 Branch/WorkUnit；
   Worker 只能读取批准来源，不能写源文件、调用 Connector 或代表用户批准其他 Worker。
6. 模块 7 `Artifact Workspace & Verifier` 把每个 Worker 返回视为 Contribution candidate。
   候选必须通过现有 file membership、Evidence Anchor、Branch Evidence Gate 和适用的
   deterministic-outcome/narrative reconciliation，才能进入共享成果。
7. 合并由稳定服务端规则完成。当前无 Anchor、越 Branch 来源、异常或叙事对账被拒的
   贡献不得进入 Artifact；最后返回、文字更长或语气更强都不构成覆盖权。Worker stale
   revision 与通用数值冲突门仍是后续扩展。
8. 一个 Worker 失败只影响其 Branch，已采用 Contribution、旧 ArtifactVersion 和其他
   Worker 的完成状态保留。Worker 专属局部恢复状态机尚未实现。

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

## 已实现公开合同

以下记录 `DR-0053` 当前实现，而不是把目标对象包装成现行字段。没有独立
`TaskIdentity`、`ContinuationContract`、`Contribution ID` 或 `MergeReceipt` 表；现行
事实直接保存在 Run Snapshot、普通 ArtifactVersion/TaskCommit 与 Worker packet 中。

### Task 与 Run lineage

| 对象 | 必需字段 | 语义 |
| --- | --- | --- |
| `HarnessRunSnapshot` / 公共投影 | `task_id`、`run_id`、`run_sequence`、`parent_run_id`、`continuation_reason`、`carried_branch_id` | 稳定业务 Task 与一次有界 Run 的父子关系 |
| 同一 Snapshot | `base_artifact_version`、`base_task_commit`、`workspace_revision`、`recheck_file_refs`、`source_revision_changed` | 后继 Run 的成果基线、冻结 Workspace revision 与精确重核范围 |
| `HarnessContinuationRequest` | `branch_id`、`expected_version`、`idempotency_key`、可选 `instruction/loop` | Owner-scoped、版本化、幂等地创建同 Task child Run；服务端 Branch 目标仍是范围权威 |

### Topology 与 Worker

| 对象 | 必需字段 | 语义 |
| --- | --- | --- |
| `TopologyAdmission` | `admission_version`、`mode`、`work_unit_breadth`、`independent_branch_count`、`dependency_parallelism`、`source_span`、`remaining_model_calls`、`remaining_time_seconds`、`external_action`、`reasons`、`user_confirmation_required` | 由 validated plan 与冻结服务端事实编译的路线建议 |
| `HarnessReadonlyWorkersRequest` | `branch_ids`、`expected_version`、`idempotency_key`、`confirmed` | 只有明确确认后才可执行当前 ready Branch；空 `branch_ids` 时由服务端 Scheduler 选择 |
| `ReadonlyWorkerRequest` | `worker_run_id`、`branch_id`、`goal`、`source_file_refs`、`expected_version` | 进程内只读 Analyst Worker 的最小批准范围 |
| `ReadonlyWorkerContribution` | `worker_run_id`、`branch_id`、`outcome`、`summary`、`source_file_refs`、`evidence_anchors`、`model_called`、`output_used`、`elapsed_ms`、`error`、`narrative_reconciliation`、`findings` | Worker 返回、调用和采用分开；`findings` 上限 96，不再静默截为 3 |
| `SharedArtifactMerge` | `artifact_id`、`version`、`adopted_worker_run_ids`、`adopted_contributions`、`waiting_branch_ids`、`failed_worker_run_ids`、`external_action` | 只合入 adopted 且有 Anchor 的贡献，并进入普通 append-only Artifact 历史 |

### 状态与事件

- 现行 Admission `mode` 为 `single_controller / fixed_workflow /
  adaptive_readonly_workers`；只有第三种令 `user_confirmation_required=true`。
- Branch 继续沿用现行 `waiting/running/completed/failed` 等状态；当前没有独立持久
  `WorkUnit` 或 Worker lease 状态机。
- Worker `outcome` 为 `adopted / failed / ambiguous / rejected`；`output_used=true` 只允许
  adopted 且通过 Anchor/叙事对账的候选。
- 现行 named SSE 为 `topology_admission`、`topology_confirmation_required`、
  `control_topology_override_recorded`、`worker_returned`、`contribution_adopted`、
  `contribution_waiting`、`contribution_rejected`、`topology_workers_completed`。child Run
  由 `/continue` 返回新 Snapshot，不伪造一个尚不存在的 `task_continuation_created` 事件。

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

当前协议没有 `benefit_evidence` 字段，只公开结构事实和 `reasons`。没有同场基线时一律
不得显示具体节省百分比、质量提升或 ROI；未来若增加收益字段，只允许区分 unknown、
结构并行依据和真实同场测量，不能用模型自评填充。

## 前台交互影响

### Demo 1

用户在一个 Task 时间线中查看多段 Run。每段 Run 有自己的预算、状态和成果，但共享
稳定 Task 身份。终态页面选择一条未完成/受影响 Branch 后，点击“继续未完成任务”；
当前没有独立的提交前 continuation preview，child Snapshot 返回后在时间线中说明：

- 以哪些旧成果版本为基线，但不把旧模型事实直接带为新结论；
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

只有 `user_confirmation_required=true` 的高成本只读 Worker 路线显示确认按钮。普通单 Controller
和固定流程直接按既有合同运行；`direct_tool` 未实现时显示不可用，不提供假按钮。

## UI—服务端事实映射

| 前台文案 | 服务端事实 | 禁止推断 |
| --- | --- | --- |
| 同一任务的新一段执行 | `task_id` 相同、`parent_run_id` 有值、新 `run_id` | 旧 Run 被修改或无限续命 |
| 继续一条工作线，列出需重核来源 | `carried_branch_id`、`recheck_file_refs`、`source_revision_changed` | 旧来源天然仍正确或多个 Branch 被复制 |
| 推荐固定流程 | Admission `mode=fixed_workflow` + `reasons[]` | Worker 已启动 |
| 建议最多 3 个只读 Worker，等待确认 | `mode=adaptive_readonly_workers` + `user_confirmation_required=true` + `remaining_model_calls` | 多 Worker 一定更快/更好 |
| Worker 已返回、结果未采用 | `model_called=true/output_used=false` + `outcome/error` | Worker 没调用或整个任务失败 |
| 2 项可用，1 项待核对 | 两个 adopted `worker_runs` + 一个 waiting/failed Branch | 最终任务已全部正确 |
| 已形成 v2，v1 保留 | 新 ArtifactVersion/TaskCommit | 源文件被回滚或写回 |

## 安全与治理

- Owner、expected version 与幂等语义覆盖 continuation、Worker 确认和 topology override；
  当前没有独立 WorkUnit control API。
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
- `adaptive_readonly_workers` 未确认前没有 Worker/Analyst Worker 调用；Planner 已为
  计划与准入留下调用回执，等待确认不得新增模型调用；确认后并发不超过 3。
- 至少 4 个 WorkUnit 覆盖依赖、延迟、失败、歧义与成功；无 orphan unit。
- 无来源、stale、篡改、错误算术或对账冲突的 Contribution 不进入 Artifact。
- 一个 Worker 失败时其他 adopted Contribution 与旧 Artifact 保留；只恢复目标 WorkUnit。
- named SSE、Snapshot、PostgreSQL、幂等控制和浏览器投影一致。
- 前台不显示内部 Agent 聊天，不把 `returned` 写成 adopted，不把推荐写成执行。

当前本地门：unit `383 passed`；全量 Playwright `64 passed`；Ruff、compileall、Web
lint/build 通过；后续公开投影与字号收尾定向 Python `65 passed`、桌面/390 px
Playwright `2 passed`；来源变化条件式提示与 390 px Task 时间线又由两个独立 E2E
补丁覆盖，目标 Playwright 均为 `2 passed`。新增 PostgreSQL integration 收集 3 项，但本机没有
`TEST_DATABASE_DSN`，因此 `3 skipped`，不能算通过；真实 Provider 未获付费授权也未运行。
这些自动化只把本决策升级到限定工程 `Limited Verified`，不升级用户价值判断。

明确未通过/未执行的升级门是：真实 PostgreSQL、真实 Provider、Worker stale revision、
通用数值冲突验证、Worker 专属持久局部恢复，以及目标用户形成性研究。

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
| 当前已有跨 Run Task lineage 与最小 Task Ledger 的有限纵切 | `Limited Verified` | `task_id`/child Run/单 Branch/Task GET/双版本 CAS/公共重核投影自动化、隔离 PostgreSQL 17.11 的 7 项顺序事务门与 Evidence | Provider 门、WorkUnit ledger 与多实例执行协调 |
| 当前已有进程内受限只读 Worker 纵切 | `Limited Verified` | 最多三 Worker、采用门、确定性合并、局部失败自动化 | durable queue/lease、多实例、真实 Provider |
| 路线准入是本项目原生合同 | `Limited Verified` | 07-16 + 官方调研 + 确定性 unit/E2E | 同场基线验证业务收益 |
| 统一驾驶舱提升理解/效率 | `Draft` | HAI 研究支持方向 | 目标用户形成性研究 |

## 边界

本决策不声称竞品不能实现 Task lineage、Evidence Gate 或服务端收敛；只规定本项目的
原生合同。它也不证明多 Worker 更快、更便宜、更正确。当前 Worker 是同一进程内的
受限 Analyst 调用，不是通用分布式执行器；不存在 queue/lease、多实例所有权或 Worker
专属 DecisionRequest。当前也不实现真实 Connector、生产身份、源文件写回、HA 或外部
动作。PostgreSQL、Provider 和目标用户门未完成的结论必须继续明确标注。
