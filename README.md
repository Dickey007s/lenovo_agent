# Office Agent V0.1

> V0.1 定稿基线，2026-07-14。一个以办公工作区为主体、由 Agent 协助编辑，并对副作用动作实施确定性治理与人工确认的 P0 原型。

最新阶段的目标架构、最终讲稿、交互原型和 0716 汇报原件见 [`docs/final-reference/`](docs/final-reference/README.md)。这些材料用于后续版本转向参考，不改变本页描述的 V0.1 已实现边界。

## 项目定位

本项目不是“把聊天框放进办公软件”，而是在邮件、文档、报价表、任务、日历、报销和 CRM 等既有工作区之上增加 Agent 辅助层：用户可以独立编辑和保存，Agent 能读取当前未保存内容并直接修改工作区；只有涉及发送、系统写入或外部影响时，系统才创建受控动作，执行风险评估、证据校验、人工审批和一次性授权。

V0.1 重点验证三件事：

1. **工作区与对话解耦**：左侧是可独立操作的办公工作区，右侧是持续存在的 Agent 对话；切换视图不会丢失对话。
2. **模型负责理解，代码负责治理**：LLM 生成自然语言、工作区草稿和业务候选字段；风险等级、策略、证据、审批、Permit 和工具执行全部由服务端确定性逻辑决定。
3. **人工确认是自动化链路的一部分**：受控动作不会停在“请确认”的文字提示，而是通过可交互确认卡完成补证据、逐角色审批、最终授权，再把 Simulator 结果返回给 Agent 闭环回应。

所有产生副作用的工具当前均为 **Simulator**，不会发送真实邮件、写入真实日历、CRM、OA 或任务系统。

## V0.1 已实现能力

### 办公工作区

| 视图 | 当前能力 |
| --- | --- |
| 邮件 | 空白编辑器、新邮件入口、收件人/抄送/主题/正文/附件编辑、保存、Agent 渐进式写入、受控发送 |
| 文档 | 分章节编辑、Agent 生成会议纪要或周报、来源与修改记录 |
| 报价表 | 类 Excel 行列编辑、确定性行级核算、最低折后比例与待复核提示、导入入口占位 |
| 任务 | 默认从“准备客户 A 经营汇报”进入；“进度 / 成果 / 执行记录”三种模式分别承载业务下一步、服务端工件与原手工待办 |
| 日历 | 全宽月历一级视图、日期格内嵌日程条目、点击进入当日安排、新建与编辑、受控创建邀请 |
| 报销 | 报销单与发票核查、异常提示、受控发起补件请求 |
| CRM | 商机阶段和下一步编辑、受控更新商机 |
| 审计 | Run 事件流、Trace、审批、Permit 与 Simulator 执行记录 |

工作区按用户持久化到 PostgreSQL。当前每种视图维护一个活动 `WorkspaceArtifact`；邮件“新邮件”会创建新的空白活动 Artifact，并解除上一封邮件的动作绑定。V0.1 尚未实现收件箱、草稿箱和多文档列表。

### Agent 与实时交互

- OpenAI-compatible LLM 负责多轮对话、通识问答、工作区草稿和 `ActionCandidate` 生成。
- `ConversationPlan` 与 `ActionCandidate` 使用 Pydantic 严格校验；网关不支持 JSON mode 时自动回退到 Schema Prompt，并最多执行一次结构修复。
- 对话使用 SSE 流式输出；工作区更新使用 `artifact.stream.started → artifact.delta → artifact.updated` 增量协议。
- 邮件正文按文本块呈现打字效果；文档章节、任务、报价和日历项目按项出现，并显示轻量“Agent 正在编辑”状态。
- 普通非敏感通识问题走直接问答路径，避免误复用上一轮办公动作；企业内部事实仍只能来自受信上下文。
- 报价核算、复算、最低折后比例检查和来源追问不再交给模型自由计算：后端用 Decimal、前端用整数分与 BigInt 按同一逐行舍入规则投影。基线三行的标准总价为 272000 元、折后总价为 253400 元、优惠金额为 18600 元、综合折后比例为 93.16%（约 9.32 折）、优惠率为 6.84%。
- 未保存的项目名、数量、折后比例和有效期可以参与当前回答；报价编号、客户、币种、最低折后比例、标准价和来源仍由服务端拥有。旧小计/总计会被忽略并重算，非法字段会停止聚合显示和回答，不回退到历史金额。
- 未保存上下文和保存请求都绑定当前 `WorkspaceArtifact.artifact_id/revision`。旧版本保存返回 409，页面保留本地草稿并读取最新版本；不同字段修改可经显式三方重应用合并，同一字段双方都修改时不会静默覆盖。
- 进入发送等副作用链路后，服务端从当前 Artifact 重建收件人、附件、正文和治理元数据，忽略模型伪造的 Action 参数与来源；规划期间 Artifact 改变则不创建动作。无法解析的姓名、畸形邮箱或不透明附件被确定性 deny，用户自报 evidence 不能把未解析值变成可信证据。Run 绑定发起它的真实 Conversation Thread，跨 Thread 续写被拒绝；动作终态说明失败后可重新读取，成功重试复用同一完成消息。
- 用户在等待 Agent 返回期间继续修改工作区时，前端以请求发出时版本为编辑起点处理晚到 `artifact.updated`：不同字段自动保留双方修改，同字段双改进入显式冲突，Agent 结果不再直接覆盖新输入。
- 风险等级和判断规则只在确认前的 Agent 回复中出现一次；执行完成后只反馈成功、失败或拒绝结果。

### 治理与执行闭环

- 严格协议：`ActionCandidate`、`ProposedActionSpec`、`RiskAssessment`、`PolicyEffect`、`EvidenceRecord`、`ControlPlan`、`ApprovalRecord`、`PermitMetadata`、`ToolExecutionResult`。
- Risk Engine 根据影响范围、数据类别、可逆性和信息完整度计算 L0-L4；L5 仅用于受限能力、受限执行或凭据暴露。
- Policy Engine 对外发邮件、外部日历邀请、内部系统写入、报价数据、非受管设备和受限能力应用确定性规则。
- Evidence Resolver 模拟企业通讯录、文件哈希、DLP、CRM 报价库、日历、项目、OA 和 CRM 权限校验。
- LangGraph `interrupt/resume` 覆盖补证据、人工审批和最终授权三个 Gate。
- Ed25519 JWT Permit 绑定用户、capability、动作哈希、参数哈希、策略版本、审批、有效期、单次使用和幂等键。
- Tool Gateway 校验签名、过期、主体、capability、参数、策略版本和重放后，才允许调用 Simulator。
- 已端到端注册 5 个执行 capability：`email.send`、`task.create`、`calendar.invite`、`crm.opportunity.update`、`expense.request_evidence`。
- 工作区内容在动作绑定后发生变化时，旧 Action 会被作废，不能用旧审批执行新参数。
- 配置 PostgreSQL 时，Workspace、Run、Audit 和 LangGraph checkpoint 具备持久化路径；当前 Demo 3 动作账本的跨进程 Run 创建幂等、Permit replay、响应丢失恢复和 Conversation Thread/Message 恢复仍需独立证据，不能由该配置推断为高可用。

### Demo 1 经营汇报任务、交付物与恢复闭环（PR 4-6）

- `TaskService` 从严格的 `TaskContractDraft` 创建服务端拥有的 `TaskContract`、`TaskSnapshot`、三个初始 `BranchSnapshot` 和首条 `TASK_CREATED`。新任务仍从 `ready / contract` 开始。
- 完成、失败或取消后，Tasks 工作区右上角显示“开始新一轮汇报”。这不是把当前 Task 重置成可启动状态：前端使用新的 `Idempotency-Key` 创建独立 Task，并立即启动新 Task；旧 Task、工件、事件和 Commit 不被重置或覆盖。服务端列表会保留多轮 Task，但前端尚无历史轮次选择入口。
- `POST /v1/tasks/{task_id}/start` 只把固定客户 A Task 从 `ready / contract` 推进到 `running / observe`（v2）；浏览器随后以带版本和幂等键的 `POST /v1/tasks/{task_id}/advance` 一次推进一个阶段：v3 Plan、v4 Act、v5 Verify、v6 `waiting_input / verify`。Plan/Act 通过严格 `TaskStageAgent` 调用当前配置的 `deepseek-v4-pro`；只有与服务端批准模板逐字段一致的业务文字才记录为 `model`，否则显式 `template_fallback`。Observe/Verify/Commit 仍由确定性服务完成。
- `POST /v1/tasks/{task_id}/controls` 接受带 `expected_task_version` 和 `idempotency_key` 的 Steer、Pause、Resume、Take over、Return control 与 Resolve evidence。分支控制只有在服务端返回新 Snapshot 后才显示为已应用；Steer 当前只进入 `accepted` 时，前端只显示“方向指令已记录，等待后续循环应用”。
- `TaskStore` 的内存与 PostgreSQL 实现包含 Snapshot、TaskEvent 和 ArtifactVersion 的 mutation 路径。`start` 和 `resolve_evidence` 会在写入前校验预计步骤、工具调用、运行时长和截止时间，超限时拒绝 mutation。PR 5 已用 PostgreSQL 16.14 隔离数据库和三个顺序 API 进程验证 v2/v3 Snapshot 恢复、原幂等响应重放，以及 Event/ArtifactVersion/Commit 零新增。
- 根路径默认进入经营汇报任务。初始列表返回前只显示读取态，不允许重复创建；确认没有 Task 后，空态说明要得到经营分析、风险页和客户回复草稿，“开始准备汇报”一次点击完成创建与启动。Conflict 顶部只保留弱化的“查看待确认项”定位，真正改变状态的主动作只有“采用正式口径并继续核对”；Committed 转入成果复核。主摘要只保留材料核对、业务状态和同步状态，版本、预算、Owner 等内部运行字段不再抢占业务主路径。
- 冲突决定、候选依据和分支控制只在 Tasks 工作区显示。邮件、文档等非 Tasks 工作区的右侧只保留“后台任务”摘要与“打开任务 / 前往处理 / 查看任务 / 查看汇报”入口；点击只切换到 Tasks，不提交 Task Control。
- 任务进度仍来自同一 `TaskSnapshot`，而 `stage_records` 是每个阶段的服务端 UI 事实：读取资料、拆分任务、生成材料、核对事实分别对应独立 Snapshot/version、摘要、详情、工件引用、来源和时间。v6 固定事实为 5 个工件、1 个开放冲突、2 个已验证工件；解决冲突后 v7 为 `committed / commit`。视觉阶段、连接线和颜色不能自行推断进度。
- 收入冲突区在提交前同时说明“为什么需要你”，并读取服务端 `resolution_options[].expected_impact` 逐项预演经营分析、客户回复草稿、风险页和外部发送的 `before → after`。主动作提交 `resolution_option_id + resolve_evidence`；服务端应用后把实际工件、验证、Commit、版本和未发送边界写入 `ControlEvent.impact_receipt`，完成态再显示“变化回执”。查看材料是次级动作；Steer、Pause 和 Take over 收入“其他处理方式”。
- 完成态直接列出 `last_commit` 支持的三项可复核成果，并明确客户回复仍为草稿、未发送；不再用“没有待决策项”代表完成。每个 Branch head 可在“成果”中查看当前版本、验证、冲突、结构化内容、来源、lineage 与 Commit 证据；默认 mutation 后跟随新 head，用户主动查看旧版本时显示明确历史 banner 和返回动作。
- “执行记录”保留原手工待办编辑流程。固定 Demo 1 的四个已知 `source_ref` 投影为“演示数据 · 客户往来邮件 / CRM 正式收入记录 / 收入预测表 / 客户项目周报（版本）”；原始 `fixture:` 标识和未知来源值不进入普通业务 DOM，未知值显示隐藏占位。服务端仍保存原值用于校验与审计；这只是前端第二道防线，不代表服务端数据删除，也不是通用字段安全保证。
- Task SSE 只用于发现新事件并触发 Snapshot 对账；同步标记只表示客户端传输状态，不代表后台仍在执行。未知 mutation 会在当前标签页保存原 key、intent 与预期版本。浏览器 E2E 已覆盖 start 请求发送前 abort、reload、同 key 对账和无重复工件；PR 5 的 system Edge 运行还覆盖同页 API 进程停止、控制禁用、顶部与 Task 面板一致显示恢复中，以及新进程启动后的 Snapshot 对账。尚未覆盖请求已到服务端但响应丢失或断线期间产生新事件的 `after` 回放。
- 最终提交且验证通过的客户回复草稿现在可以进入 Demo 3 治理链。完成态只提供“准备发送客户回复”：服务端把 Task、Commit、ArtifactVersion、内容摘要和 VerificationReport 绑定到 `ProposedActionSpec`，确认卡展示版本、L4 原因、外部目标和为什么必须由人确认；批准后才签发一次性 Permit 并调用 Email Simulator。绑定变化时旧 Action 失效，拒绝或动作失败不会回滚已完成的 Task Commit。
- Action Gate 打开时保留后台任务摘要，但 Task 跳转与 Tasks 中的决定控制不可用。Gate 使用右侧完整独立网格行，收起后把空间归还给对话。当前 Task 派生动作只支持固定客户 A 的最终回复草稿与演示地址，不是通用 Artifact Action registry。

这仍是固定演示数据的单 Task 纵切，不是通用后台调度器或真实 Connector。浏览器在每次 Snapshot 确认后协调下一次 `advance`；关闭浏览器后停在最后一个已持久化阶段，重新打开再继续。预算当前是步骤、工具调用和运行时长预算，不是 token 成本或供应商账单；同进程同 key 有并发去重，跨实例只有 CAS/幂等保护而没有分布式 LLM lease。模型 smoke 只证明连通和严格响应形状，不证明生成质量。人工编辑后产生新版本、响应丢失、断线事件回放、数据库故障/迁移、多实例通知、通用后台 Loop 和目标用户理解仍待验证。Task 恢复也不等于 Conversation 恢复，Thread/Message 仍在 API 内存中。

### Demo 2 智能工作驾驶舱第一纵切（DR-0008，限定范围 Verified）

当前已实现服务端驱动的 `WorkCockpitSnapshot` 单进程 memory 纵切和“智能工作驾驶舱”前台。固定演示队列包含客户 A 经营汇报、供应商邮件回复、周报格式统一、报销异常核查四项工作；后三项由 Admission 固定选择 Single Agent、Fixed Workflow、Tool Call，客户 A 保持待决定并允许 Single Agent、Fixed Workflow、Adaptive Swarm。

用户可以查看业务价值、资料广度、可并行工作包、截止压力、风险和资源边界，比较允许的执行方式，并将客户 A 的选择限定为“仅本次运行”。选择推荐模式时 `selection_source=admission`，选择其他允许模式时为 `user_override` 与 `override_scope=this_run`。mutation 使用预期版本和幂等键；409 会保留用户草稿并重新读取服务端事实。无论推荐还是选择，`execution_status` 都是 `not_started`。

路由选择现在采用双时态影响交互：服务端在每个 `RouteProfile.impact_preview` 中说明任务如何分配、哪里并行与等待、什么时候需要用户、规则预测、执行边界和不会发生的外部动作。用户在右侧切换模式时，左侧工作区的影响地图立即使用同一预览变化；确认成功后，服务端把版本、选择来源、范围与实际记录变化写入 `WorkItemSnapshot.selection_receipt/selection_receipts[]`，页面再切换为绿色实际变化地图，右侧显示精简回执。同模式重复确认和缺 route profile/preview 均 fail closed 且版本不变。预演与回执都明确“未执行”，刷新只恢复当前 memory 进程中的服务端回执。

`route_profiles[].forecast.source_type` 固定为 `fixture_policy_forecast`，只表示固定规则预测，不代表真实账单、实测耗时、Worker、Connector 或生产 SLA。当前没有 Demo 2 SSE、PostgreSQL 恢复、动态 Worker、Shared Artifact Workspace 或真实执行。工程证据包含聚焦 Python `6 passed`、专用 system Edge `5 passed`、完整 Python `118 passed, 1 skipped`、完整浏览器 `34 passed` 和三张桌面/移动截图；Ruff、前端 lint、生产构建与 diff-check 通过。实现位于堆叠 PR [#13](https://github.com/Dickey007s/lenovo_agent/pull/13)，依赖 PR #12。详见 [`DR-0008`](docs/decisions/DR-0008-demo2-explainable-admission.md)、[`SCENARIO-002`](docs/scenarios/SCENARIO-002-demo2-explainable-admission.md) 与 [`Demo 2 Evidence`](docs/evidence/DEMO2-PR1-EXPLAINABLE-ADMISSION-EVIDENCE-20260817.md)。

2026-08-20 的路由影响扩展实现为 `db461ec`、PR [#17](https://github.com/Dickey007s/lenovo_agent/pull/17)：已完成聚焦协议/服务 `11 passed`、完整 Python `144 passed, 1 skipped`、专用 Demo 2 浏览器 `5 passed`、完整浏览器 `35 passed`，并保存桌面预演、桌面回执和 `390px` 移动长页截图。该证据只证明固定策略事实、选择回执和被测交互，不证明 Adaptive Swarm 已执行或用户理解提升。详见 [`DR-0011`](docs/decisions/DR-0011-demo2-route-impact.md) 与对应 [`Evidence`](docs/evidence/DEMO2-ROUTE-IMPACT-EVIDENCE-20260820.md)。

### Demo 3 动作影响账本（DR-0012，Verified 限定范围）

Demo 3 的前台重点是“动作影响账本”：用户在 Action Gate 中先看到“会改变 / 会重新核对 / 保持不变 / 不会发生”，再分别进入补证、审批、授权和执行。提交前只显示服务端 `impact_preview`；治理或执行事实确认后才显示 `execution_receipt`。每个 `ImpactItem` 使用 `item_id/change_kind/label/before/after`，不能由前端或 LLM 补造。

当前最小场景仍是固定客户 A 的已核对 `reply_draft → email.send`。拒绝、成果版本变化、参数篡改、Permit 重放和 Simulator 失败都必须保持 Task Commit、ArtifactVersion 和 VerificationReport 不变。`ToolExecutionResult.succeeded` 只代表 Email/Office Simulator 返回成功，不代表真实邮箱、CRM、OA、日历或任务系统已写入。

当前固定工程纵切已完成验证：Python `151 passed, 1 skipped in 3.69s`、完整浏览器 `37 passed (2.2m)`，并新增审计工作台回归；Ruff、governance `4 passed in 0.02s`、前端 lint 和 build 通过，视觉终验无 P0/P1。普通业务 UI 只显示业务标签与服务端摘要，不渲染 raw event/payload/trace 或 `email_simulator`、`email.send`、`PERMIT_ISSUED`、`Permit`；内部原值仅留 API/服务端审计。四张桌面/移动截图及 SHA-256 见 Evidence。该结果不证明目标用户理解、真实 Connector、生产身份、跨进程执行幂等/Permit replay、多实例或数据库恢复。实现提交为 `9335470`，对应 [PR #18](https://github.com/Dickey007s/lenovo_agent/pull/18)；文档提交在首次证据提交后回填。详见 [`DR-0012`](docs/decisions/DR-0012-demo3-action-impact-ledger.md)、[`SCENARIO-003`](docs/scenarios/SCENARIO-003-demo3-action-impact-ledger.md) 与 [`Demo 3 Evidence`](docs/evidence/DEMO3-ACTION-IMPACT-LEDGER-EVIDENCE-20260820.md)。

## 技术架构

```mermaid
flowchart LR
    UI["Next.js 工作区 + Agent 对话"]
    API["FastAPI Conversation / Run / Task API"]
    TASK["TaskService + TaskStore"]
    LLM["OpenAI-compatible LLM"]
    CONTRACT["Pydantic Contracts"]
    GOVERN["Risk + Policy + Evidence + ControlPlan"]
    GRAPH["LangGraph Human-in-the-loop"]
    AUTH["Ed25519 Authorization Service"]
    GATEWAY["Tool Gateway"]
    SIM["Email / Office Simulators"]
    PG["PostgreSQL + LangGraph Checkpoint"]

    UI <-->|"REST + SSE"| API
    API --> TASK
    TASK <--> PG
    API --> LLM
    LLM --> CONTRACT
    CONTRACT --> GOVERN
    GOVERN --> GRAPH
    GRAPH --> AUTH
    AUTH --> GATEWAY
    GATEWAY --> SIM
    API <--> PG
```

核心依赖方向是：**LLM 输出候选业务事实 → 严格协议校验 → 确定性治理 → 人工 Gate → 一次性授权 → Gateway 校验 → Simulator**。模型不能直接签发 Permit、改变风险等级、伪造证据或调用工具。

详细说明见：

- [系统架构与技术路线](docs/ARCHITECTURE.md)
- [ActionSpec、风险、策略与授权](docs/GOVERNANCE_AND_ACTIONS.md)
- [工作区、对话与流式协议](docs/WORKSPACE_AND_STREAMING.md)
- [HTTP API 与 SSE 事件](docs/API.md)
- [演示脚本与 Presentation Brief](docs/PRESENTATION_BRIEF.md)
- [Loop、Swarm 与统一 Agent Runtime 目标架构](docs/TARGET_ARCHITECTURE.md)
- [决策、推进与汇报治理](docs/DECISION_AND_REPORTING_GOVERNANCE.md)
- [Demo 1 Task Runtime 协议](docs/contracts/TASK_RUNTIME_PROTOCOL.md)
- [Demo 1 UI—服务端事实矩阵](docs/contracts/UI_SERVER_FACT_MATRIX.md)
- [Demo 1 场景与决策记录](docs/scenarios/SCENARIO-001-customer-a-durable-report.md)
- [Demo 1 PR 3 运行证据与边界](docs/evidence/DEMO1-PR3-RUNTIME-EVIDENCE.md)
- [Demo 1 PR 4 前端与 E2E 证据](docs/evidence/DEMO1-PR4-FRONTEND-E2E-EVIDENCE.md)
- [Demo 1 PR 5 PostgreSQL-backed API 重启证据](docs/evidence/DEMO1-PR5-POSTGRES-BACKED-API-RESTART-EVIDENCE.md)
- [LLM API 连通性证据](docs/evidence/LLM-API-SMOKE-EVIDENCE-20260811.md)
- [前端视觉同步与 Demo 1 兼容决策](docs/decisions/DR-0003-frontend-visual-refresh-sync.md)
- [前端视觉同步与兼容证据](docs/evidence/DR-0003-FRONTEND-VISUAL-SYNC-EVIDENCE.md)
- [Demo 1 独立新一轮汇报决策](docs/decisions/DR-0004-repeatable-demo1-rounds.md)
- [Task Director 交互决策](docs/decisions/DR-0005-task-director-interaction.md)
- [Task Director 交互证据](docs/evidence/DEMO1-PR6-TASK-DIRECTOR-INTERACTION-EVIDENCE.md)
- [可理解性验收与工程代理证据](docs/evidence/DEMO1-PR6-USABILITY-COMPREHENSION-AUDIT-20260811.md)
- [来源与新一轮语义修订证据](docs/evidence/DEMO1-ROUND-AND-SOURCE-CLARITY-EVIDENCE-20260811.md)
- [Demo 1 已验证工件进入 Demo 3 动作治理决策](docs/decisions/DR-0007-task-artifact-action-bridge.md)
- [Demo 1 → Demo 3 Task Artifact 动作桥接证据](docs/evidence/DEMO1-DEMO3-TASK-ARTIFACT-ACTION-BRIDGE-EVIDENCE-20260813.md)
- [Demo 2 可解释 Admission 决策（限定范围 Verified）](docs/decisions/DR-0008-demo2-explainable-admission.md)
- [Demo 2 智能工作驾驶舱场景（限定范围 Verified）](docs/scenarios/SCENARIO-002-demo2-explainable-admission.md)
- [Demo 2 PR-1 工程证据](docs/evidence/DEMO2-PR1-EXPLAINABLE-ADMISSION-EVIDENCE-20260817.md)
- [Demo 2 路由影响预演与选择回执决策](docs/decisions/DR-0011-demo2-route-impact.md)
- [Demo 2 路由影响预演与选择回执证据](docs/evidence/DEMO2-ROUTE-IMPACT-EVIDENCE-20260820.md)
- [Demo 1 渐进阶段决策（限定范围 Verified）](docs/decisions/DR-0009-progressive-demo1-stages.md)
- [Demo 1 渐进阶段工程证据](docs/evidence/DEMO1-PROGRESSIVE-STAGES-EVIDENCE-20260817.md)
- [Demo 1 Agent 影响预演与变化回执决策](docs/decisions/DR-0010-visible-agent-impact.md)
- [Demo 1 Agent 影响预演与变化回执证据](docs/evidence/DEMO1-AGENT-IMPACT-PREVIEW-EVIDENCE-20260820.md)
- [Demo 3 动作影响账本决策（Verified 限定范围）](docs/decisions/DR-0012-demo3-action-impact-ledger.md)
- [Demo 3 动作影响账本场景（Verified 固定场景）](docs/scenarios/SCENARIO-003-demo3-action-impact-ledger.md)
- [Demo 3 动作影响账本证据（Verified 限定范围）](docs/evidence/DEMO3-ACTION-IMPACT-LEDGER-EVIDENCE-20260820.md)
- [来源台账](docs/decisions/SOURCE_REGISTER.md)

## 目录结构

```text
apps/web/                         Next.js 16 + React 19 前端
packages/contracts/               动作与 Task Runtime 协议、哈希
packages/risk_core/               风险、策略和 ControlPlan
packages/evidence/                确定性 Mock Evidence Resolver
packages/agent_runtime/           LangGraph interrupt/resume 工作流
packages/authorization/           Ed25519 Permit 签发
packages/tool_gateway/            Permit 校验与工具路由
packages/audit/                   内存/PostgreSQL 审计日志
services/api/app/application/     ConversationService、RunService、TaskService 与存储适配器
services/api/app/api/             FastAPI 路由
simulators/                       邮件与办公动作 Simulator
tests/                            单元与集成测试
docs/                             架构、治理、协议、API 和演示资料
```

## 本地运行

### 环境要求

- Windows 10/11（启动脚本按 PowerShell 编写）
- Python 3.12、[uv](https://docs.astral.sh/uv/)
- Node.js、pnpm/Corepack
- Docker Desktop（PostgreSQL 16）

复制配置并填写实际的 OpenAI-compatible 推理地址和 Key：

```powershell
Copy-Item .env.example .env
```

```dotenv
LLM_BASE_URL=https://your-openai-compatible-endpoint.example/v1
LLM_API_KEY=replace_me
LLM_MODEL=deepseek-v4-pro
LLM_THINKING_MODE=disabled
DATABASE_DSN=postgresql://agent:agent@127.0.0.1:5432/office_agent
LANGGRAPH_CHECKPOINT_DSN=postgresql://agent:agent@127.0.0.1:5432/office_agent
```

不要把真实 Key 提交到仓库。`LLM_BASE_URL` 必须指向模型推理服务，项目调用 `${LLM_BASE_URL}/chat/completions`。

Windows 推荐直接运行：

```powershell
.\scripts\start-demo.ps1
```

脚本会检查 Docker Desktop、启动 PostgreSQL、FastAPI 和 Next.js：

- 前端：<http://localhost:3000>
- API：<http://localhost:8010>
- OpenAPI：<http://localhost:8010/docs>
- 健康检查：<http://localhost:8010/v1/health>

停止服务：

```powershell
.\scripts\stop-demo.ps1
```

也可以分别启动：

```powershell
uv sync
uv run python -m services.api.run

pnpm --dir apps/web install
pnpm --dir apps/web dev
```

## 验证

```powershell
uv run pytest -q
uv run ruff check .
pnpm --dir apps/web lint
pnpm --dir apps/web build
```

V0.1 定稿基线和 Demo 1 各 PR 的实际验证结果记录在 [`DR-0002`](docs/decisions/DR-0002-bounded-durable-office-loop.md) 及对应 evidence。PR 3 封口验证为全量 Python `56 passed`；PR 4 的 system Edge E2E 为 `2 passed (18.4s)`。PR 5 与前端视觉刷新/可重复演示合并后的封口回归为：PostgreSQL 16.14 opt-in 系统测试 `1 passed (9.78s)`，system Edge suite `3 passed (17.0s)`，完整 Python `58 passed, 1 skipped (2.00s)`。PR 6 原 Task Director 工程封口为浏览器 `6 passed (34.5s)`。收到“看不懂系统要做什么”的 Stakeholder 反馈后，本轮改以业务任务重排首屏、单次开始、决策后果和完成成果；该轮浏览器为 `12 passed (43.7s)`，Python 为 `58 passed, 1 skipped (2.24s)`，Ruff、前端 lint 和生产构建通过，并保存 `1181 x 900` 三状态与 `390 x 844` CSS 视口截图。随后针对来源与“再次演示”歧义的修订完成浏览器 `12 passed (44.5s)`，覆盖非 Tasks 只显示后台摘要、已知来源标为演示数据且原始 ID 不入 DOM，以及“开始新一轮汇报”创建并启动独立 Task、旧 Task 保留；另保存 `1440 x 900` Mail 摘要截图。新增回归只证明预设信息、动作和服务端事实一致，不证明真实用户已经理解。故 [`DR-0005`](docs/decisions/DR-0005-task-director-interaction.md) 保持 `Draft`，至少 5 人无引导形成性测试尚未运行。固定 Demo 1 Task 测试不调用真实 LLM；独立 LLM smoke 只验证 `deepseek-v4-pro` 通用问答与 Conversation SSE 连通性。

报价错误修复的来源、决策、前台—后端事实链和证据分别记录在 [`USER-FEEDBACK-20260811-06`](docs/sources/USER-FEEDBACK-20260811-06-quote-calculation-grounding.md)、[`DR-0006`](docs/decisions/DR-0006-deterministic-quote-calculation.md) 和 [`QUOTE-WORKSPACE-DETERMINISTIC-CALCULATION-EVIDENCE-20260811`](docs/evidence/QUOTE-WORKSPACE-DETERMINISTIC-CALCULATION-EVIDENCE-20260811.md)。实现提交为 `2f9866f + fe865bd + e2c4b56`；全量 Python 为 `108 passed, 1 skipped (2.62s)`，报价/Conversation 聚焦为 `54 passed (1.72s)`，完整浏览器为 `27 passed (1.1m)`，其中报价浏览器为 `15 passed (23.6s)`，Ruff、前端 lint 与生产构建通过。`DR-0006` 因此仅在固定演示报价、当前公式、当前协议和被测前台恢复范围内为 `Verified`，不是生产级报价引擎或用户可用性结论。

2026-08-13 的跨 Demo 迭代把最终且验证通过的客户回复草稿接入 Demo 3 治理链。实现提交 `d827f29`、文档提交 `d1cc746` 的封口结果为 Python `112 passed, 1 skipped (4.11s)`、完整 system Edge `29 passed (1.4m)`、Demo 1 浏览器 `13 passed (1.0m)`，Ruff、前端 lint、生产构建与治理门槛通过。浏览器覆盖 L4 Gate、绑定版本、批准后 Permit + Email Simulator、拒绝后 Task Commit 不变以及确定性结果说明；这是固定 Fixture 的工程证据，不证明真实发送或用户已经理解。决策和证据见 [`DR-0007`](docs/decisions/DR-0007-task-artifact-action-bridge.md) 与 [`TASK-ARTIFACT-ACTION-BRIDGE-20260813`](docs/evidence/DEMO1-DEMO3-TASK-ARTIFACT-ACTION-BRIDGE-EVIDENCE-20260813.md)，对应堆叠 PR [#12](https://github.com/Dickey007s/lenovo_agent/pull/12)。

> 说明：上方历史回归段落中“固定 Demo 1 Task 测试不调用真实 LLM”仅描述旧 atomic 测试；当前 progressive Runtime 的运行配置允许 Plan/Act 通过严格适配器调用 `deepseek-v4-pro`，单元测试默认注入确定性 agent。模型 smoke 仍只证明连通和严格响应，不证明质量。

2026-08-17 的渐进 Runtime 修订实现为 `13c9c13`：start 只进入 Observe，四次 `advance` 才依次确认 Plan、Act、Verify 和待决策状态，解决证据后提交；完整 Demo 契约（含预算与截止时间）和 Plan/Act 安全文本均在服务端校验。封口结果为 Python `138 passed, 1 skipped (3.14s)`、完整浏览器 `35 passed (1.9m)`、渐进主路径连续三次 `3 passed (29.5s)`，Ruff、前端 lint/build 与治理门槛通过；八张截图覆盖阶段等待、候选回看、核对进展、移动决策和成果终态。该结论只证明固定 Fixture 的协议与被测交互，不证明后台无人值守、模型质量或用户理解改善。

2026-08-20 的 Agent 影响交互实现为 `258861f`、PR [#16](https://github.com/Dickey007s/lenovo_agent/pull/16)：服务端为收入口径决定提供结构化影响选项，前台在提交前逐项预演经营分析、回复草稿、风险页和外部发送的变化，提交后再用 `ControlEvent.impact_receipt` 展示实际落地回执。封口结果为 Python `139 passed, 1 skipped (4.74s)`、完整浏览器 `35 passed (1.9m)`、Ruff、前端 lint/build、治理门槛与 diff-check 通过，另有三张带 hash 的桌面/移动截图。该结论只证明固定 Fixture 的前后端事实一致与被测交互，不证明真实用户理解改善或任意真实动作均可准确预演。

## 数据、身份与安全边界

- `X-User-Id` 与 `X-User-Roles` 只是 V0.1 Demo 身份头，默认前端使用 `demo_user` 和 `current_user,sales_manager`；生产环境必须替换为经过验证的 SSO/JWT。
- 内部邮箱、CRM、报价、OA、知识库和日历内容均为确定性演示数据，不是真实企业数据；固定 Demo 1 的普通业务 UI 必须明确标注“演示数据”，不得显示原始 `fixture:` ID。
- 报价工作台不访问真实 CRM/CPQ/ERP；当前公式只覆盖数量、标准价和单行折后比例，不含税费、汇率、阶梯价、套餐依赖或真实审批制度。当前模型仍为 `deepseek-v4-pro`，但报价数值问答由确定性代码完成。
- Workspace revision 校验和 Conversation/Workspace 锁当前只在单个 API 进程内形成一致性保护；没有数据库原子 compare-and-swap、多实例锁或跨实例 Conversation 顺序验证。前端三方重应用也不是通用多人协作文档合并器。
- 未解析收件人/附件当前采用固定 deny，而不是已接入企业通讯录或内容分类服务；附件名称识别只适用于演示规则。Run/Thread 绑定与结果重放仍随 Conversation 内存边界，API 重启后不恢复。
- 未配置 Permit PEM 文件时，服务启动会生成进程级 Ed25519 密钥；重启后旧 Permit 失效。
- 所有副作用工具均为 Simulator；UI 中的“发送成功”“创建成功”只代表 Simulator 成功。
- 对话 Thread/Message 当前保存在 API 进程内存中，重启后丢失；Workspace、Run、Audit 和 LangGraph checkpoint 在配置 PostgreSQL 时可恢复。
- Task 在未配置数据库时同样只保存在 API 进程内存中；Demo 1 mutation 会写 Snapshot、TaskEvent 和 ArtifactVersion。配置 PostgreSQL 后对应表为 `agent_tasks`、`agent_task_events` 和 `agent_task_artifact_versions`。本机 PostgreSQL 16.14 已验证同一数据库上的顺序 API 进程恢复；该结论不覆盖数据库重启/崩溃、多实例并发、迁移或 Conversation Thread/Message。
- 当前没有 Alembic 迁移、生产级 RBAC、真实 Connector、后台任务队列、分布式 Permit 重放存储、Task 跨实例通知和多实例一致性保障。

## V0.1 验收结论

V0.1 已形成可演示的完整闭环：**用户或 Agent 编辑工作区 → Agent 提议动作 → 服务端评估风险与策略 → 系统取证/人工审批 → 用户最终授权 → Permit 约束执行 → Simulator 返回结果 → Agent 完成对话闭环 → 审计可追溯**。

后续版本应优先替换身份、Connector 和持久化边界，而不是把更多决策权交给模型。V0.1 的核心资产是可验证的治理链路与工作区协同范式，而不是真实办公系统覆盖率。
