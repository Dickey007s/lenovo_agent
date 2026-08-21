# Office Agent V0.1 · Agent Handoff

这是 V0.1 定稿基线。后续 Agent 开始修改、分析或制作汇报前，按以下顺序读取：

1. `README.md`：产品定位、能力边界、运行与验收结论。
2. `docs/ARCHITECTURE.md`：分层、信任边界、持久化和调用链。
3. `docs/WORKSPACE_AND_STREAMING.md`：工作区模型、前端交互和 SSE。
4. `docs/GOVERNANCE_AND_ACTIONS.md`：ActionSpec、风险、策略、证据、审批、Permit。
5. `docs/API.md`：真实路由、请求和事件协议。
6. `docs/PRESENTATION_BRIEF.md`：对外叙事、演示路径和不可夸大的边界。
7. `docs/DECISION_AND_REPORTING_GOVERNANCE.md`：所有决策、推进、PR、Demo 和汇报必须通过的场景、来源、前台与后端事实门槛。
8. 修改 Demo 1 Task Runtime 时，再读 `docs/decisions/DR-0002-bounded-durable-office-loop.md`、`docs/scenarios/SCENARIO-001-customer-a-durable-report.md` 和 `docs/contracts/` 下的协议与 UI 事实矩阵。
9. 修改报价工作台、报价上下文或报价问答时，再读 `docs/decisions/DR-0006-deterministic-quote-calculation.md`、对应 Source/Evidence 和 `docs/contracts/UI_SERVER_FACT_MATRIX.md` 的报价映射。
10. 修改 Task 最终工件进入业务动作的桥接时，再读 `docs/decisions/DR-0007-task-artifact-action-bridge.md`、对应 Evidence、`docs/GOVERNANCE_AND_ACTIONS.md` 与 Task/UI 协议。
11. 修改 Demo 2 智能工作驾驶舱、Admission、路由选择或 WorkCockpitSnapshot 时，再读 `docs/decisions/DR-0008-demo2-explainable-admission.md`、`docs/decisions/DR-0011-demo2-route-impact.md`、`docs/scenarios/SCENARIO-002-demo2-explainable-admission.md`、对应 Evidence 与 `docs/contracts/UI_SERVER_FACT_MATRIX.md` 的 Demo 2 区域。
12. 修改 Demo 3 Action Gate、动作影响账本、治理回执或 Simulator 边界时，再读 `docs/decisions/DR-0007-task-artifact-action-bridge.md`、`docs/decisions/DR-0010-visible-agent-impact.md`、`docs/decisions/DR-0012-demo3-action-impact-ledger.md`、`docs/scenarios/SCENARIO-003-demo3-action-impact-ledger.md`、对应 Evidence、`docs/GOVERNANCE_AND_ACTIONS.md`、`docs/API.md` 与 `docs/contracts/UI_SERVER_FACT_MATRIX.md` 的 Demo 3 区域。

源码永远高于文档。行为变更后必须同步相关文档；不要只改 README 的宣传描述。关键实现路径：

```text
apps/web/app/page.tsx                         前端状态、工作区、对话和确认卡
apps/web/app/styles.css                       布局、滚动、动效和视觉
services/api/app/api/routes.py                HTTP 与 SSE API
services/api/app/application/conversations.py 对话、上下文、Artifact 与流式事件
services/api/app/application/llm.py           OpenAI-compatible 适配与结构校验
services/api/app/application/runs.py          治理 Run 和执行编排
packages/contracts/models.py                  安全边界协议
packages/risk_core/                           风险、策略和 ControlPlan
packages/evidence/                            Mock Evidence Resolver
packages/agent_runtime/workflow.py             LangGraph interrupt/resume
packages/authorization/service.py             Ed25519 Permit
packages/tool_gateway/gateway.py               Permit 校验与工具注册
simulators/                                   非真实副作用工具
tests/                                        单元与端到端回归
```

必须保留的产品与安全不变量：

- 工作区在左、Agent 在右；双方独立滚动，中间可拖动，切换工作区不重建对话。
- 用户可以独立编辑和保存；Agent 接收活动视图与未保存的 `workspace_context`。
- 人工确认使用对话底部非模态 tray，不恢复独立审批页，也不完全遮挡消息区。
- Demo 1 的冲突决定、候选依据和分支控制只在 Tasks 工作区显示；非 Tasks 工作区只显示后台任务摘要和前往 Tasks 的入口，跳转本身不得提交 Task Control。
- Demo 1 的文件来源在普通业务 UI 中必须标为“演示数据”并使用可读业务标签；原始 `fixture:` ID 和未知内部标识不得进入 DOM。服务端仍保留稳定控制 ID 用于校验与审计。
- Demo 1 当前来源包位于 `demo-enterprise-data/customer-a/`，仅是项目生成的仿真文件，不是 Lenovo、真实客户、实时企业数据库或 Connector。服务端必须先以 `manifest.json` 做 allowlist、相对路径、文件大小、非符号链接和 SHA-256 校验，再做受限结构化解析；创建时冻结 `TaskSnapshot.source_documents[]`，冲突以 `ConflictRecord.operation_context` 绑定文件字段事实。文件缺失、篡改、解析失败或摘要变化必须 fail closed；前台只显示文件名、系统标签、记录时间和字段依据，隐藏 `fixture:` 控制 ID、绝对路径和完整摘要。
- 涉及 Task 决策或副作用的主要动作必须优先展示服务端拥有的影响：提交前说明会改变什么、重新核对什么、保持什么和不会发生什么，提交后只依据实际 Snapshot/Event 回执展示已经发生的变化。前端动画、模型说明或静态文案不得冒充变化事实。
- 终态入口统一为“开始新一轮汇报”：创建独立 Task 并立即启动，旧 Task、Artifact、Event 与 Commit 不得重置或覆盖。当前没有历史轮次选择入口，不得把后台保留表述成前台可自由切换历史轮次。
- 报价工作台的行小计、标准总价、折后总价、优惠金额、综合折后比例、优惠率和最低折后比例检查必须由确定性公式产生，LLM 只能解释结果，不能充当计算器。服务端拥有 `quote_id/customer/currency/approved_floor/unit_price/sources`；当前用户只能通过工作区编辑 `name/qty/discount/valid_until`，客户端 `subtotal/total/approval` 永远不是权威事实。
- 报价任一必需字段无效、越界、超限或行数与服务端版本不一致时必须 fail closed：前台不显示部分总计，Agent 不回退到历史金额，保存接口不写入猜测结果。保存后的规范化报价若相对基线有修改，必须标记 `needs_review` / `requires_recheck`，不能沿用旧审批。
- 显式发送未保存 `workspace_context` 时必须同时提交服务端 `artifact_id + revision`；保存必须提交 `expected_artifact_id + expected_revision`。版本过期时不得覆盖最新内容：前端保留当前草稿、读取最新 Artifact，并只允许查看最新版本或基于编辑起点/本地草稿/最新版本做有界三方重应用；同字段双改必须交给用户处理。
- LLM 产生的 Artifact `sources`、Action 参数、目标范围、数据分类、状态变化类型和可逆性都不是权威事实。服务端必须保留/生成受信来源，并从当前可见 Artifact 与 capability 重建可执行动作；内容不匹配、目标不确定或版本在规划期间变化时 fail closed。动作终态说明允许同一 API 进程内幂等重放同一个 `message.completed`，前端按 `message_id` 更新而不是重复追加。
- 不得把动作自身携带的未知姓名、畸形邮箱或不透明附件当作“已验证证据”。收件人身份未解析、邮箱格式不合法或附件数据类别不明时必须确定性 deny，用户自报同一值不能解锁；格式合法的已知邮箱与可分类附件才沿正常 Evidence/Approval/Permit 链路。Conversation 创建的 Run 必须绑定真实 Thread，同一用户也不能把一个 Thread 的结果续写到另一个 Thread。
- 用户在等待 Agent 返回 Artifact 期间仍可继续编辑。晚到的 `artifact.updated` 必须以请求发出时版本为 base 做三方处理：不同字段保留双方修改，同字段双改进入显式冲突；不得把晚到 Agent 结果直接覆盖用户新输入。
- 动作确认后必须继续执行并由 Agent 返回结果，前端不能硬编码“已完成”。
- LLM 只生成自然语言、ArtifactDraft 与 ActionCandidate；Risk、Policy、Evidence、Approval、Permit 和工具执行由确定性代码决定。
- 风险规则不能退化为“所有外部动作都是 L5”。普通累计最高 L4；L5 仅由受限能力、受限执行或凭据公开等硬条件触发。
- 风险判断在确认前的 Agent 文本中只输出一次；确认卡可保留结构化风险，最终结果不重复风险段落。
- Artifact 绑定动作后若内容改变，旧 Action 必须失效；不能复用旧审批或 Permit。
- Task 派生动作只能来自当前 Owner 的最终 `TaskCommit` 中、已经 passed 验证的不可变 ArtifactVersion；必须绑定 Task/Commit/Artifact/Verification 的身份、版本和 digest，并在证据、审批、授权与执行前重新校验。前台“准备动作”不得表述为已发送，拒绝或动作失败不得回滚已完成的 Task Commit。
- `email.send` 等执行结果当前全部来自 Simulator。不得在文档、UI 或汇报中表述为真实邮件、CRM、日历或 OA 写入。
- 25 类 ActionCandidate 是协议目录，不代表全部可执行；当前只有 5 个 capability 注册了端到端 Simulator。
- Demo 2 第一纵切只允许使用四项固定演示任务、服务端 `WorkCockpitSnapshot`、固定队列、路由解释和客户 A 的 `this_run` 模式选择；三项简单任务的 Admission 路由是固定演示选择，拖拽调序和长期排序偏好不属于本纵切。
- Demo 2 的可选路由必须优先展示服务端 `RouteProfile.impact_preview`：右侧选择改变左侧工作组织影响地图，确认后只能依据 `WorkItemSnapshot.selection_receipt` 显示已记录变化。预演不是回执，路由已选不是任务已执行；缺少服务端 preview/receipt 时前端不得自行补造。
- Demo 2 的 Adaptive Swarm 只能标记为推荐或本次已选择；没有真实 Worker/Connector/执行事件时，`execution_status` 必须为 `not_started`。`selection_source=admission` 表示接受推荐，降级必须为 `selection_source=user_override`，并使用 `override_scope=this_run`。
- Demo 2 的成本/时效只能使用 `route_profiles[].forecast.source_type=fixture_policy_forecast` 语义；不得写成真实账单、实测时延、节省比例、生产 SLA 或已验证效果。当前服务端边界是 memory，跨进程恢复与真实执行均待证据。
- Demo 3 动作影响账本只能使用服务端 `impact_preview` 与 `execution_receipt`。每个 `ImpactItem` 必须包含 `item_id/change_kind/label/before/after`，且固定映射为 `target-change→will_change`、`binding-recheck→will_recheck`、`task-preserved→unchanged`、`real-connector-not-called→no_external_action`；预演不是回执，`ToolExecutionResult.succeeded` 只证明 Simulator 返回结果。
- Demo 3 的四类前台影响固定为“会改变 / 会重新核对 / 保持不变 / 不会发生”。拒绝、绑定失效、参数篡改、Permit 重放和 Simulator 失败都必须保留已完成 Task/Artifact/Commit 不变的回执。
- Demo 3 不得表述真实邮箱、CRM、OA、日历或任务系统发生写入；当前仅覆盖固定场景和五个 Simulator capability。RunStore、Permit replay、Thread/Message 与完成消息的跨进程恢复边界必须按证据表述，不能从配置 PostgreSQL 推断为高可用。
- Demo 3 当前仅在固定客户 A `reply_draft → email.send`、四个治理场景、被测桌面/移动路径内为 `Verified`；无用户研究、真实 Connector、生产身份、跨进程执行幂等/Permit replay、多实例或数据库恢复证据时，不得扩展为通用能力或用户效果结论。实现与文档 commit、PR URL 必须回填到 DR-0012 Evidence 后才能封口。
- Demo 3 普通业务审计工作台不得渲染 raw `event_type`、`payload`、`trace` 或 `email_simulator`、`email.send`、`PERMIT_ISSUED`、Permit token/内容/permit_id/签名；必须投影为业务标签与服务端摘要，可以显示“Permit Service”“Permit 已签发/未签发”等业务级状态。内部原值只保留在 API/服务端审计与授权技术视图。
- Demo 1/2/3 的通用完成状态在前台显示“已运行”，只有模型事实显示“模型已调用”；Demo 3 以“执行许可服务”“受控演示工具”为主，Permit/Gateway/Simulator 仅在二级技术元信息出现。unknown 工具结果必须显示“工具结果待核对”，不得写成未调用或未执行。
- Demo 3 的 proposal 或 Task-derived action 出现时，前端必须全局切换到 Demo 3/审计视图，避免身份仍停留在 Demo 1/2。`TaskStageProcessing` 必须保持跨字段一致：确定性路径不得声称模型调用/模型输出；语言模型路径必须有观测调用和模型名。

Demo 1 当前 Runtime 事实（2026-08-20，文件驱动修订）：create 为 v1 `ready / contract`；创建前必须从 `demo-enterprise-data/customer-a/` manifest allowlist/hash 校验并解析文件，冻结 `TaskSnapshot.source_documents[]`；冲突字段来自文件事实与 `ConflictRecord.operation_context`。start 仅进入 v2 `running / observe`；浏览器在 Snapshot 确认后四次调用幂等 advance，依次得到 v3 Plan、v4 Act、v5 Verify、v6 `waiting_input / verify`，固定为 5 个工件、1 个 open conflict、2 个 passed verification；resolve 后 v7 `committed / commit`。`stage_records` 是 UI 事实且旧快照默认空数组。Plan/Act 通过严格 `TaskStageAgent` 调用 `deepseek-v4-pro`，但只有与服务端批准模板逐字段一致的业务文字才记录为 `model`，否则显式 `template_fallback`；Observe/Verify/Commit 确定性，模型不拥有身份、来源、状态、冲突、验证或 Commit。固定渐进路径还要求完整 Demo 契约，包括预算和截止时间。浏览器关闭不会后台继续，预算是 steps/tool calls/runtime 而非 token cost；同进程同 key 有锁，跨实例无分布式 LLM lease。模型 smoke 只证明连通与严格响应，不证明质量。文件证据已由实现 `5b07702`、PR #21、Python `166 passed, 1 skipped`、浏览器 `38 passed` 和桌面/移动截图按限定工程范围封口；精确 hash 与边界见 `docs/evidence/DEMO1-FILE-BACKED-SOURCES-EVIDENCE-20260820.md`。

决策、推进与汇报的硬门槛：

- 每个方案、决策、实现项、PR、Demo 和汇报结论都必须同时记录：用户场景与问题、依据来源、前台交互影响、后端事实来源、验证证据与当前边界。
- 场景记录必须包含目标用户、触发条件、当前流程或痛点、目标与完成条件、关键异常路径；不能只写抽象能力名称。
- 来源必须给出可追溯的精确引用、日期或版本、它支持的判断以及局限。用户反馈、用户研究、竞品实践、论文、官方文档、源码和运行证据必须分类；推断与假设不得写成已验证事实。
- 前台影响必须说明用户看见什么状态、可执行什么动作、得到什么反馈、失败或等待时如何恢复，以及哪些内部细节应隐藏。不得把原始 Prompt、思维链、Worker 对话、密钥、底层日志或无决策价值的内部状态直接暴露给用户。
- 每个 UI 状态必须映射到服务端 `Snapshot`、持久化字段或有序事件，并写清状态转换、版本、权限和幂等语义。前端不得自行推断任务完成、分支真值、预算、风险、Permit 或执行成功。
- 任一项缺少“场景与来源”“前台交互影响”“后端事实映射”“验证证据”之一时，状态只能标记为 `Draft` 或“待验证”，不得表述为已确认、已完成、已实现或可对外结论。
- 具体记录格式、强制矩阵和完成门槛以 `docs/DECISION_AND_REPORTING_GOVERNANCE.md` 为准；行为或叙事变化必须同步更新对应记录。

技术约束：Python 固定 `>=3.12,<3.13`；前端使用 Next.js 16、React 19 和 TypeScript；API 使用 FastAPI；持久化使用 PostgreSQL 16；LLM 调用 OpenAI-compatible `/chat/completions`。不要提交 `.env`、真实 Key、真实客户信息或生产凭据。

修改前先搜索现有模式，保持局部改动，不做无关重构。涉及协议时同步检查前端类型、Pydantic 模型、RunService、测试和文档。涉及风险与授权时必须补回归测试，不能只依靠 UI 手测。

提交或交付前运行：

```powershell
uv run pytest -q
uv run ruff check .
pnpm --dir apps/web lint
pnpm --dir apps/web build
```

本地启动与停止：

```powershell
.\scripts\start-demo.ps1
.\scripts\stop-demo.ps1
```

默认地址为前端 `http://localhost:3000`、API `http://localhost:8010`、OpenAPI `http://localhost:8010/docs`。若运行结果与本文档不一致，以源码和命令输出为准，并修正文档。

与用户沟通时使用中文直接回答，不复述问题；优先使用连续短段落，减少不必要的标题、列表和空行。
