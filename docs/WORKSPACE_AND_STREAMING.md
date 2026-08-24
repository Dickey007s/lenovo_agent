# 工作区、对话与流式协议

本文描述 V0.1 的交互模型、工作区数据、Agent 上下文和 SSE 事件，是修改前端交互或 ConversationService 时的对齐基线。

## 1. 交互原则

V0.1 采用 **workspace-first** 结构，而不是以聊天记录为唯一产物：

- 左侧为办公工作区和视图工具栏，右侧保留持续存在的 Agent 区域。根路径默认进入 Demo 1 Tasks；左侧先回答本轮要准备什么和下一步，右侧默认显示“现在需要你做什么”，并可切回同一 Agent 对话。离开 Tasks 后，右侧只保留后台任务摘要和返回 Tasks 的入口，不继续展示冲突决定或分支控制。
- 中间分隔条可拖动，双方独立滚动；切换工作区只替换左侧内容。
- 用户无需 Agent 也能编辑、保存或从工作区发起操作。
- Agent 接收当前活动视图和浏览器中的未保存内容，可以直接更新该工作区。
- 需要人工介入时，确认卡从对话输入区上方弹出，不遮挡历史消息，也不禁止继续对话。
- 审批不是独立页面。确认完成后动作继续运行，Simulator 结果再由 Agent 以自然语言收尾。

前端入口是 `apps/web/app/page.tsx`，主要视觉和动效位于 `apps/web/app/styles.css`。普通工作区保留暖纸底色、墨黑正文与工作区身份色；Demo 1 Task Director 使用更中性的高密度工作台，蓝色表达当前交互或运行阶段、绿色表达服务端已验证事实、琥珀色表达等待证据或人工决定。颜色、图标、连接线和进度式布局都不是业务真值。各工作区页头标题是固定的“XX 工作台”名称，不随 Artifact 数据变化；Task Director 标题和目标是例外，直接投影当前 `TaskSnapshot.contract`。移动端关键操作目标至少 44px。

`DR-0016` 已把统一“工作现场”设为三 Demo 的默认体验：来源工作区在左、渐进阶段与动态计划在中、服务端活动回执在右。该第一纵切只在固定 FORTE 三场景、单进程 memory 和 `ready_to_execute` 边界为 `Limited Verified`，不删除普通 WorkspaceArtifact、对话或既有 Demo Runtime，也不表示三 Demo 已迁移执行。

## 2. WorkspaceArtifact

`services/api/app/application/conversation_models.py` 中的 `WorkspaceArtifact` 是工作区的服务端协议：

```text
artifact_id          当前活动产物的唯一标识
revision             当前活动产物的单调保存版本，从 1 开始
kind                 mail | document | quote | tasks | calendar | expense | crm
title                工作区标题
content              各视图的业务内容
sources              受信来源、系统、摘要和读取权限
linked_action_id     当前内容绑定的受控动作
linked_run_id        对应治理 Run
requires_recheck     动作绑定后内容是否又被修改
change_history       系统、用户和 Agent 的修改记录
updated_at           最后更新时间
```

工作区按 `user_id + kind` 保存。V0.1 每类只维护一个活动 Artifact，不提供收件箱、文件列表或历史版本浏览器。Conversation Thread 中也可带 Artifact 快照，但跨刷新恢复以 Workspace Store 为准。

### 2.1 各工作区 content 形状

| kind | 主要字段 | V0.1 行为 |
| --- | --- | --- |
| `mail` | `to[]`、`cc[]`、`subject`、`body`、`attachments[]` | 新用户为空白编辑器；“新邮件”创建新 Artifact，并清除旧动作绑定 |
| `document` | `document_type`、`sections[{heading, body}]` | 分章节编辑，Agent 可按章节渐进写入 |
| `quote` | `quote_id`、`customer`、`currency`、`valid_until`、`approved_floor`、`items[{name, qty, unit_price, discount, subtotal}]`、`total`、`approval` | 类表格编辑；行小计、四项汇总与最低折后比例状态由确定性公式投影；导入仅为界面占位 |
| `tasks` | `tasks[{id, title, source, priority, status, reason}]` | “执行记录”按状态分栏维护手工任务卡；“进度 / 成果”只投影 `TaskSnapshot`，不写入该 WorkspaceArtifact |
| `calendar` | `month`、`selected_date`、`events[{id, title, date, start, end, attendees, location, agenda}]` | 一级为全宽月历，日期格内嵌日程条目；点击进入当日安排视图（可前后翻日、返回月历），支持受控邀请 |
| `expense` | `case_id`、`owner`、`amount`、`status`、`invoices[]`、`anomalies[]` | 展示报销核查结果并可受控发起补件 |
| `crm` | `customer`、`opportunity_id`、`amount`、`before`、`suggested_stage`、`next_step` | 编辑商机建议并可受控更新 CRM 阶段 |

报价、任务、报销和 CRM 中声称来自业务系统的记录由确定性 Fixture 合并，模型不能覆盖这些 Connector-owned 字段；模型主要负责文本草稿和候选动作。报价的服务端所有字段为 `quote_id/customer/currency/approved_floor/items[].unit_price/sources`，当前用户可编辑字段为 `valid_until/items[].name/qty/discount`。`subtotal/total/approval` 不能从浏览器升级为权威事实。

报价即时汇总由前端整数分/BigInt 投影，服务端保存与 Agent 数值回答由 Decimal/`ROUND_HALF_UP` 投影，二者都先将每行标准金额舍入到分，再按该行折后比例计算并舍入折后小计，最后求和。基线结果是标准总价 272000 元、折后总价 253400 元、优惠金额 18600 元、综合折后比例 93.16%（约 9.32 折）、优惠率 6.84%。任一行无效时，前端所有聚合值都显示“待核对”，而不是继续显示部分总计。

### 2.2 Demo 1 Task Director

Tasks 主视图采用三个客户端模式，它们不改变服务端 Task 状态：

| 模式 | 前台职责 | 权威事实 |
| --- | --- | --- |
| `director`（前台“进度”） | 业务任务、三项材料、单一主要下一步、用户语言阶段、当前材料、核对/冲突与是否纳入成果 | 当前 `TaskSnapshot`；不存在的 head/report/Commit 必须显示等待或缺失 |
| `artifacts`（前台“成果”） | 当前与历史 ArtifactVersion、来源、检查、lineage 和 Commit | `branches[].artifact_heads`、`artifact_versions[]`、`verification_reports[]`、`conflicts[]`、`last_commit` |
| `manual`（前台“执行记录”） | 原手工待办看板 | `WorkspaceArtifact(kind=tasks)`；不与 TaskSnapshot 相互覆盖 |

初始 `/v1/tasks` 未返回时只显示读取态，不暴露创建动作；确认无 Task 后，固定 Demo 1 空态使用 `/v1/demo1/tasks` 客户 A 创建模板的客户端副本，一次点击依次创建并启动。已有 Task 的标题、目标和交付物全部取自 `TaskSnapshot.contract`。终态“开始新一轮汇报”也依次 create 与 start：新 round key 创建独立 Task，旧 Task 不修改；start 只进入 v2 `running / observe`，浏览器随后在服务端确认后逐次协调四个 `advance`，不是把旧状态重置为可启动。通用产品仍需服务端模板描述接口，不能把固定空态副本扩展成通用事实。

右侧在 Tasks 中默认进入 `decisions`。open Conflict 先解释为什么需要人和两个口径，再读取 `resolution_options[].expected_impact` 以差异行展示“会改变 / 会重新核对 / 保持不变 / 不会发生”；主动作提交服务端 `resolution_option_id + resolve_evidence`。新 Snapshot 返回后，左侧完成态只从 `ControlEvent.impact_receipt` 显示“服务端变化回执”，让用户把自己的决定与实际材料版本、核对、Commit 和未发送边界对应起来。查看材料、补证、暂停和接管降低层级；用户可切到 `agent` 继续同一 Conversation。“补充更多依据”只填充方向输入，提交后也只能显示 `steer accepted / 等待后续循环应用`。右侧模式切换不重建 Conversation，也不产生 TaskEvent。邮件、文档等非 Tasks 工作区不挂载决定控制，只从同一 Snapshot 显示“后台任务”摘要。

当 Task 已 `committed` 时，三项成果仍首先作为可阅读结果出现；只有当前 `reply_draft` 同时被 Commit 引用并具有 passed VerificationReport 时，成果区才显示“准备发送”。点击后前端调用专用准备接口并切到同一 Conversation 的 Action Gate。该动作不会把 Task 改成 sending，也不表示邮件已发出。Gate 显示绑定成果版本、固定演示目标、风险、为什么需要确认和拒绝后果；用户先批准，再确认执行。拒绝、绑定失效或 Simulator 失败后，原 Task Commit 和三项成果继续保留。

工件选择使用客户端 `follow_head` 与 `pinned_history` 两种语义。默认跟随服务端 Branch head；用户主动选择旧版本时必须显示历史版本 banner、当前 head 版本和返回动作。mutation 完成后，`follow_head` 自动选择新 head；任何旧 candidate 都不能静默冒充当前已验证工件。

Task 同步状态与传输状态仍是客户端事实：它们只说明浏览器是否已经对账和 SSE/GET 是否可用，不表示后台 Loop 进度。主摘要只显示材料核对、业务状态和同步状态；预算、Owner 与内部步数从业务主路径隐藏，必要时由执行记录或服务端证据复核。完成态直接列出 `last_commit` 支持的三项成果和“回复草稿未发送”边界。服务端列表保留多轮 Task，但当前前端只自动选择最近活动 Task，否则选择最近终态 Task，没有历史轮次选择入口。移动端把编排画布改为纵向流，并从阻塞摘要提供到待确认项的可达路径，不通过缩小字体或横向页面滚动保留桌面泳道。

原 PR 6 视觉基线的浏览器 E2E 为 `6 passed (34.5s)`，历史 [`design-qa.md`](../design-qa.md) 只证明当时记录视图的视觉实现。收到用途不清反馈后的当前工程代理回归为 `12 passed (43.7s)`；新增单次开始、延迟列表加载防重复创建、无任务离线时左右区域一致、快速重复开始只产生一次 create/start、同分支多冲突按顺序开放且按剩余冲突解释后果、失败终态覆盖残留冲突卡、完成成果以及 Conflict/Committed 的 `1181 x 900` 溢出断言。既有 `390 x 844` 移动、乱序 Snapshot、`409`、历史版本与 source-ref 回归继续通过。该结果仍不证明目标用户理解、效率或决策质量改善，`DR-0005` 保持 `Draft`。

随后来源与轮次语义修订的完整浏览器 E2E 为 `12 passed (44.5s)`：覆盖非 Tasks 只显示后台摘要/跳转、已知来源显示“演示数据”且原始 ID 不进入 DOM、终态一键 create+start 新 Task 并保留旧 Task。独立证据见 [`DEMO1-ROUND-AND-SOURCE-CLARITY-EVIDENCE-20260811.md`](evidence/DEMO1-ROUND-AND-SOURCE-CLARITY-EVIDENCE-20260811.md)。这仍是工程证据，不证明用户理解。

DR-0007 的跨 Demo 浏览器路径进一步覆盖：完成本轮 → 从已验证客户回复准备动作 → Action Gate 核对绑定版本和演示目标 → 批准与确认执行 → Agent 返回 Simulator 结果；拒绝路径则验证 Task 仍为 committed。完整浏览器为 `29 passed (1.4m)`。该证据只证明被测交互和服务端绑定，不证明真实邮件发送、用户理解或通用 Task 成果动作。

### 2.3 Demo 2 智能工作驾驶舱

Tasks 工作区新增客户端 `cockpit` 模式，并把它设为当前默认入口。它不复用 Demo 1 `TaskSnapshot` 推断多任务状态，而是读取独立的 `WorkCockpitSnapshot`：左侧显示四项固定演示工作的统一队列、演示来源、业务条件和三种候选方式比较；右侧显示当前工作项的服务端推荐、理由、规则预测和允许选择。

三项轻量工作只有一个 `allowed_modes` 值，前台以只读已选状态展示且不提供确认按钮。客户 A 才显示 Single Agent、Fixed Workflow、Adaptive Swarm 三个服务端允许选项。确认 mutation 带 `expected_version`、`scope=this_run` 和 `idempotency_key`；收到服务端新 `WorkItemSnapshot` 后才显示“已记录”，并始终同时显示“任务尚未启动”。409 时保留本地单选草稿，重新 GET 最新驾驶舱后让用户复核；其他未知结果先 GET 对账，相同模式已被服务端记录才显示成功，否则保留同一请求语义。

客户 A 的模式 radio 与左侧主工作区形成一组跨区域影响预演：切换本地 `draftMode` 不提交请求，但左侧立即投影所选 `route_profiles[].impact_preview`，显示工作分配、并行与等待、人的介入、策略预测、执行状态与不会发生的动作。服务端确认后，左侧由蓝色预演变为绿色实际变化地图，右侧显示精简 `selection_receipt` 并把焦点移到回执标题；完整 `before → after` 不在窄侧栏重复。`selection_receipts[]` 连续保留当前 memory Snapshot 内的改选历史，同模式重复和缺 route profile/preview 均 409 且版本不变。刷新后只有 GET 返回同一 receipt 才恢复成功状态，Toast 和颜色都不能代替服务端事实。

Demo 2 的 Admission/route 仍通过 GET/POST 对账；固定客户 A 的受控执行另使用 execution GET、event replay 与 SSE。选择回执必须先显示“已选择、尚未启动”，用户启动后才根据整轮 `Demo2ExecutionSnapshot.status` 显示当前 Runtime 可达的 `queued/running/verifying/completed/failed`；协议枚举中的 Execution `cancelled` 尚无当前取消路由/转换，只能按 Draft/兼容状态处理。单个工作单元只显示 `queued/running/completed/failed/cancelled`，不显示 Worker `verifying` 或 Demo 2 `waiting_input`；`verifying` 专指整轮共享工件核验。四个业务工作单元、5 个共享工件、动态增派和完成回执均投影服务端 Snapshot/有序事件；API 进程重启会丢失 memory 选择与执行，因此 UI 不得显示跨进程恢复。`route_profiles[].forecast` 只投影为“规则预测”；Prompt、思维链、内部来源 ID、策略权重、Worker 对话和底层日志不进入业务 DOM。移动端把队列改为横向可选择条、详情与右侧决策区改为纵向自然流；关键可见控件至少 44px，页面不允许整体横向溢出。

### 2.4 FORTE Workspace + 统一 Harness 工作现场（DR-0016，Limited Verified 规划纵切）

工作现场是统一 Harness 的业务前台，不是内部调试器。三个区域各自承担一个用户问题：

| 区域 | 用户问题 | 当前服务端事实 | 默认隐藏 |
| --- | --- | --- | --- |
| 左侧来源工作区 | “Agent 本轮可以看哪些资料？” | 安全公共场景投影与 `PublicHarnessRunSnapshot.source_documents[].file_ref/display_*` | raw `task.md`、内部净化 Prompt、`task_instruction`、rubric/solution/grading、绝对路径、完整 hash |
| 中间动态计划 | “Agent 准备怎么做，依赖与边界是什么？” | `HarnessRunSnapshot.status/plan/model_receipt/validation_errors` 和有序事件 | Prompt、CoT、模型原始响应、静态预画的伪 DAG |
| 右侧活动回执 | “模型是否调用、结果是否采用、执行是否发生？” | `HarnessModelReceipt.called/output_used/elapsed_ms`、`HarnessEvent`、`execution_started=false` | Key、供应商 payload、内部堆栈、无决策价值日志 |

进入页面时先显示三个安全场景和原始 input 的业务标签，再由用户开始本轮。四个前台阶段固定翻译服务端事实：读取文件（`workspace_index`）、生成计划（`planning_started/completed`）、校验计划（`plan_validation`）、准备执行（`ready_to_execute`）。页面不能一打开就跳到校验；恢复时只有 Snapshot 的真实 status/version/sequence 可以决定当前位置。

动态计划节点来自服务端安全公共 `plan.units[]`，可以在不同真实模型运行中改变数量、依赖、`input_file_refs` 和允许工具，前端不得按 Demo 写固定 Worker 模板，也不得接收内部 path/hash。`called=true` 显示“模型已调用”；`output_used=true` 显示模型计划已被采用；`ready_to_execute` 才显示“计划已通过服务端校验，尚未执行”。三者不得合并。当前没有 execution command、Scheduler/Worker、工具调用、Artifact 写入、审批或 Permit；按钮点击与动画都不能显示任务完成。

断线后页面保留最后确认 Snapshot 和 event sequence；非终态意外断流先 GET 对账，再以 `after=N` 继续 SSE。收到 `ready_to_execute` 或 `harness_failed` 后关闭唯一终态连接，并只做一次最终 GET，不再循环重连。单进程 API 重启则 Run 丢失，只能明确提示重新开始新一轮，不能声称恢复。`X-User-Id` 仍是 P0 占位。桌面/移动 E2E 只验证被测工程投影，不属于用户研究。

## 3. 来源、权限和修改记录

每个 `SourceReference` 包含：

```text
source_id | label | system | excerpt | permission | updated_at
```

来源、权限使用和修改记录收纳在工作区底部的“上下文与治理”折叠区，默认不占用主编辑画布。其设计目的不是装饰，而是区分：

- 哪些内容来自模型生成；
- 哪些事实来自演示用邮箱、CRM、知识库、项目系统、日历或 OA Fixture；
- 当前用户以什么权限读取；
- 保存、Agent 修改和动作失效分别在何时发生。

这些来源在 V0.1 中是确定性 Demo 数据，并非真实 Connector 返回值。Demo 1 当前的文件包位于 `demo-enterprise-data/customer-a/`：manifest allowlist、相对路径、文件大小、非符号链接和 SHA-256 通过后，受限解析器把 `.eml/.csv/.json` 形成 `TaskSnapshot.source_documents[]`，并在创建时冻结。Conflict 卡的字段级差异来自服务端 `ConflictRecord.operation_context`，不是前端或模型推断。普通业务 UI 显示“演示数据 · 文件名 / 系统标签 / 记录时间”，原始 `fixture:` 控制 ID、绝对路径和完整摘要只保留在服务端校验/审计，不进入 DOM；未知来源、缺文件、篡改或解析失败显示“待核对”并 fail closed，不回退到旧金额或静态事实。这些文件是项目生成仿真，不是 Lenovo/真实客户数据、实时企业数据库或 Connector。

DR-0016 的统一 Harness 使用另一条明确隔离的来源链：FORTE 公开仓库固定 commit `345c1ec1487139db9dd319787fa9405ba85d1869`、顶层 MIT 和本地 manifest 中 11 个原始文件/`115352` bytes。8 个 input 是普通工作现场的候选来源；3 个 raw `task.md` 只保留 provenance，不显示为工作区文件。Catalog 仅把 Prompt 净化文本送入内部 Planner，公共 API/UI 不得出现 `task_instruction`、rubric、solution 或 grading 内容。前台必须标“公开办公基准数据”，不能称为真实企业文件或客户数据库。

## 4. Agent 上下文与规划

发送消息时，前端调用：

```json
{
  "message": "根据当前内容写一封客户确认邮件",
  "active_view": "mail",
  "workspace_artifact_id": "artifact_demo_mail",
  "workspace_revision": 3,
  "workspace_context": {
    "to": ["client-a@example.com"],
    "cc": [],
    "subject": "",
    "body": "用户尚未保存的正文",
    "attachments": []
  }
}
```

`workspace_context` 表达浏览器当前未保存的编辑内容。显式发送时必须同时携带当前 `workspace_artifact_id/workspace_revision`；省略/`null` 表示使用已保存 Artifact 且不要求该 token。普通工作区以当前值形成 active workspace；报价工作区会先把当前 `name/qty/discount/valid_until` 合并到服务端基线，再确定性重算，不能覆盖报价编号、客户、币种、最低折后比例、标准价、来源或审批。显式 `{}` 表示当前上下文为空并 fail closed，不能悄悄回退到旧金额。服务端还会加入当前时间和按关键词检索到的 Demo 企业记录，形成 trusted context。

LLM 必须返回严格的 `ConversationPlan`：

```text
assistant_response   给用户的自然语言
focus_view           建议聚焦的工作区
artifact             可选的工作区草稿
action               可选的 ActionCandidate
```

规划结果经 Pydantic 校验，失败时最多修复一次。普通公共知识问题走直接问答路径，避免无关问题继承上一轮动作；涉及公司、客户、报价、报销、权限等企业事实的问题必须依赖 trusted context，不能用模型常识伪造内部记录。

Harness Planner 是独立的严格规划协议：内部只接收安全场景契约、净化任务文本和 allowlisted input 索引，返回 `HarnessPlan.summary/units[]`。该 Planner 不拥有 Run/事件身份、来源真值、执行状态、Artifact 版本、验证结论、Approval 或 Permit；路径、工具、副作用、Artifact 名称、依赖、环和 Human Gate 均由服务端验证。模型调用、输出采纳与服务端 validation 是三个分离事实。

报价核算、复算、最低折后比例检查和来源追问是更窄的确定性分支：ConversationService 从当前活动报价调用 Quote Calculator，并直接形成可读回答，LLM 不生成金额。写入、修改、保存、发送、创建或导入等业务动作不会被该分支截获，继续进入 `ConversationPlan` 与治理链路。来源回答必须说明数据是当前屏幕中的固定演示报价、公式为数量 × 标准价 × 折后比例，且没有访问真实 CRM。

## 5. 对话 SSE 协议

`POST /v1/threads/{thread_id}/messages/stream` 和动作完成后的 continue 接口均返回 `text/event-stream`。每个事件的 `event:` 名称与 JSON 中的 `type` 相同。

| 事件 | 关键字段 | 前端职责 |
| --- | --- | --- |
| `message.created` | `message` | 立即插入用户消息 |
| `assistant.status` | `status`、`label` | 显示“理解任务/继续执行”等短状态 |
| `message.started` | `message` | 建立空的 Agent 消息气泡 |
| `assistant.delta` | `message_id`、`delta` | 逐段追加文字，形成流式回复 |
| `message.completed` | `message` | 用服务端终态替换临时消息 |
| `ui.focus` | `view` | 切换到 Agent 正在处理的工作区 |
| `artifact.stream.started` | `artifact`、`fields` | 初始化渐进写入状态 |
| `artifact.delta` | `kind`、`artifact_id`、`field`、`value` 或 `item` | 增量更新正文、章节、行或卡片 |
| `artifact.updated` | `artifact` | 接受服务端最终 Artifact |
| `workspace.conflict` | `view`、`latest_artifact` | 保留本地草稿；展示查看最新版本或有界三方重应用，不创建动作 |
| `action.proposed` | `run` | 在输入框上方打开确认卡并订阅 Run |
| `action.closed` | `run_id`、`status` | 关闭确认卡或标记最终状态 |
| `error` | `detail` | 结束当前流并显示可理解错误 |

典型顺序：

```mermaid
sequenceDiagram
    participant U as 用户
    participant UI as Web
    participant C as ConversationService
    participant L as LLM
    participant R as RunService

    U->>UI: 发送指令
    UI->>C: message + active_view + workspace_context
    C-->>UI: message.created / assistant.status
    C->>L: ConversationPlan
    L-->>C: 回复 + ArtifactDraft + ActionCandidate
    C-->>UI: ui.focus
    C-->>UI: artifact.stream.started
    loop 增量呈现
        C-->>UI: artifact.delta
    end
    C-->>UI: artifact.updated
    C->>R: 创建受控动作
    R-->>C: RunSnapshot
    C-->>UI: action.proposed
    C-->>UI: message.started / assistant.delta / message.completed
```

报价确定性回答使用较短时序：`message.created → assistant.status(status=calculating) → message.started → assistant.delta* → message.completed`。回复事件与 LLM 回复共用同一 UI 协议，但数值来自服务端 Quote Calculator。同一 API 进程内同一 Thread 的流串行更新，避免并发消息用旧 Thread 覆盖；这不提供跨进程顺序、Thread 持久化或断线游标恢复。

显式上下文的 Artifact/revision 已过期，或 LLM 规划期间活动/目标 Artifact 发生变化时，服务端发出 `workspace.conflict` 并停止写回和动作创建。Web 保留当前输入，读取事件中的最新 Artifact；“重新应用我的修改”只把相对编辑起点发生变化且未被服务端同时改动的字段应用到最新版本。同字段双改、缺失编辑起点或报价行结构变化会列出冲突字段并拒绝自动合并。“查看最新版本”会明确放弃当前草稿并采用服务端版本。

即使请求发出时 revision 有效，用户也可能在 Agent 流返回前继续编辑。Web 在发起请求时记录各工作区的 Artifact 快照与本地 edit token；晚到 `artifact.stream.started/delta/updated` 不直接覆盖请求后的编辑。最终 Artifact 与本地草稿改动不同字段时自动保留双方并继续显示“未保存修改”，同字段双改则把 Agent 版本作为最新版本放入相同冲突 UI，用户输入保持可见。

## 6. 工作区渐进写入

渐进写入是交互呈现，不是逐 token 数据库存储：

1. 服务端先计算并保存最终 Artifact。
2. `_stream_artifact_update` 比较旧内容和目标内容。
3. 字符串按文本块发送，列表按项目发送；不适合渐进的字段直接给出终值。
4. 前端显示光标、淡入、高亮或“Agent 正在编辑”状态。
5. `artifact.updated` 到达后，以服务端最终对象校准界面。

因此刷新页面看到的是最终状态，不会重播打字动画。动画不能被当作事务进度，也不能替代服务端保存结果。

## 7. 确认卡与动作闭环

确认卡位于右侧对话底部、输入框上方，采用非模态 tray：

- 保持消息区可滚动、输入框可使用；
- 显示一次结构化风险等级、简要规则、capability、目标和状态；
- 缺证据时显示补证据操作；
- 缺审批时按角色显示批准/拒绝；
- 条件满足后显示最终执行确认；
- 执行后调用 continue stream，让 Agent 返回最终结果，而不是由卡片硬编码“任务完成”。

风险说明只在动作确认前的 Agent 文本中出现一次；确认卡保留结构化风险字段属于操作控件，不再在执行结果文本中重复。

可执行动作在创建 Run 前重新绑定当前 Artifact：模型提供的收件人、附件、payload、目标范围、数据分类、状态变化类型、可逆性和 `source_refs` 不直接进入执行；服务端按 capability 从可见 Artifact 重建并绑定 `artifact_id/revision/content`。ArtifactDraft 的模型来源也被服务端保留值或默认来源覆盖。内容不匹配时不创建动作；纯文本姓名、畸形邮箱或附件数据类别不明时，Run 由确定性策略置为 `DENIED`，Mock Evidence 不把 Action 自身值或用户自报姓名/哈希当作可信佐证。格式合法的邮箱和已分类报价附件仍可沿 Evidence/Approval/Permit 链路执行 Simulator。

Conversation 创建的 Run 绑定发起它的真实 Thread；continue stream 会拒绝同一用户从另一 Thread 续写该 Run。动作结果说明暂时失败时，前端保留“重新读取结果”；成功生成后，同一 API 进程重试会重放相同 `message.completed`，前端按 `message_id` 更新而不是重复追加。

## 8. 保存、修改与失效

- 用户点击保存时调用 `PUT /v1/workspace/{kind}`，同时提交 `expected_artifact_id/expected_revision`；服务端只在 token 匹配时合并 content、递增 `revision` 并追加修改记录。
- Artifact 已绑定 Action 后再次保存会设置 `requires_recheck=true`，并作废旧 Action；旧审批和旧 Permit 不能用于新内容。
- Agent 更新工作区时同样产生修改记录，并将新动作绑定到当前 Artifact。
- 邮件“新邮件”调用 `POST /v1/workspace/mail/new`，创建空白邮件 Artifact；这也是已编辑邮件返回空白编辑器的正式入口。
- 报价保存先按服务端字段所有权合并并重算小计/总计。相对基线修改 `name/qty/discount/valid_until` 时，保存结果设置 `approval.status=needs_review` 和 `requires_recheck=true`；字段无效时返回 422，不持久化猜测值。

## 9. V0.1 边界

- Thread 和 Message 在 API 进程内存中，重启后不恢复。
- 每个用户每种 kind 只有一个活动 WorkspaceArtifact。
- 当前只有活动 WorkspaceArtifact 的 409 检测与前端有界三方重应用，不是通用冲突合并或多人协作；没有自动保存节流、离线队列或历史版本恢复。Workspace 锁与 revision 比较只在单 API 进程内，数据库原子 CAS 和多实例协调未实现或验证。
- 邮件附件仅保存元数据/名称，不上传真实文件。
- 报价导入、真实邮箱目录、日历账户切换等仅为后续 Connector 扩展点。
- 报价核算只覆盖数量、标准价和单行折后比例，不含税费、汇率、阶梯价、套餐依赖或真实审批规则；当前来源为固定演示数据，不访问真实 CRM/CPQ/ERP。
- SSE 没有断线游标恢复；Run 审计流单独支持 `after` 序号续订。
- 动作结果的 `message.completed` 重放缓存与 Conversation Thread 一样位于单 API 进程内，重启后不恢复。

## 10. Demo 1 Task 阶段与浏览器协调（2026-08-17）

Tasks 工作区的“读取资料 / 拆分任务 / 生成材料 / 核对事实”不是前端动画，而是 `TaskSnapshot.stage_records` 中的服务端事实。`start` 返回 v2 `running / observe`；浏览器在确认后依次提交四次 `advance`，得到 v3 Plan、v4 Act、v5 Verify、v6 `waiting_input / verify`。v6 展示 5 个工件、1 个待解决冲突和 2 个已验证工件，解决后 v7 才显示 Commit。

Plan/Act 可以调用当前 `deepseek-v4-pro`，但前台看到的阶段文字不是任意模型输出：适配器与 TaskService 都要求它与服务端批准模板逐字段一致，否则明确记录为 `template_fallback`。思维链、内部 ID、原始来源引用和模型自报状态不会进入 `stage_records`。固定路径还校验包括预算与截止时间在内的完整 Demo 契约。

阶段轮询只由浏览器协调。关闭标签页后任务停在最后一个已持久化阶段，重新打开通过 GET/SSE 对账后继续；不存在后台 scheduler 或“关闭浏览器仍在运行”的事实。SSE payload 不能直接推断完成状态。旧 Snapshot 没有 `stage_records` 时按空数组兼容读取，不补造历史阶段。

来源显示使用可读业务标签“演示数据”，文件证据卡只显示服务端 `source_documents[]` 的 display_name、system_label、recorded_at、record_status 和 allowlisted facts；原始 `fixture:`、绝对路径、完整 SHA-256、prompt、思维链和内部日志只保留在服务端校验/审计。阶段详情可显示摘要、受限详情、工件引用、来源和时间。预算文案只表达运行时预算，不展示或推断 token 成本、供应商账单或模型质量。来源文件校验失败时阶段不能继续，前台保持待核对状态。

## 11. Demo 3 动作影响账本（DR-0012 Verified 限定范围）

Action Gate 在创建 Run 后先展示服务端 `impact_preview`，并在 Run 事件或执行结果确认后展示 `execution_receipt`。两者都使用 `ImpactItem(item_id/change_kind/label/before/after)`，且固定映射 `target-change→will_change`、`binding-recheck→will_recheck`、`task-preserved→unchanged`、`real-connector-not-called→no_external_action`；前台固定翻译为“会改变 / 会重新核对 / 保持不变 / 不会发生”。

Run SSE 的 `RUN_CREATED`、`EVIDENCE_SUBMITTED`、`CONTROL_PLAN_UPDATED`、`APPROVAL_RECORDED`、`PERMIT_ISSUED`、`TOOL_EXECUTED`、`ACTION_INVALIDATED`、`TAMPER_BLOCKED` 和终态事件是唯一时序事实；前端收到事件后必须以 `GET /runs/{run_id}` 的完整 Snapshot 对账。结果未知时显示“结果待确认”，不得由动画、按钮或本地状态宣告执行成功。

桌面 Action Gate 的主按钮按阶段显示“提交依据 / 批准 / 确认执行”，移动端保持同一顺序并保证触控尺寸。确认前不得写成“已发送”；Simulator 成功只显示“模拟器已返回结果”，不显示真实邮箱、CRM、OA 或日历写入。拒绝、失效、篡改和失败需明确反馈且保留 Task Commit 不变。当前验证为固定 Demo 3 工程路径；断线/跨进程对账、真实 Connector、生产身份和用户理解仍待独立证据。

## 12. 处理来源与真实等待

Conversation 回答在 `message.started/message.completed` 中携带相同的 `processing`：确定性报价为 `deterministic_formula`，通用回答或业务规划为 `language_model`，确定性动作回执可为 `policy_engine`。右侧消息完成后保留“处理来源 + 真实耗时”；真实模型请求等待期间显示配置模型名，确定性路径明确“未调用大模型”。该元数据不暴露 Prompt、思维链、Token、Key 或供应商原始响应。

Demo 2 路由按钮只写入服务端选择，因此命名为“记录本轮方式”，并明确规则路由不调用模型、不会自动启动协作。独立“启动协作”动作只有在 Adaptive Swarm 已选且版本匹配时出现；运行等待、Worker 模型耗时和最终完成都来自 execution Snapshot/Event。系统禁止用固定 sleep 伪造模型思考；毫秒级公式/规则应立即完成，模型路径的等待和耗时必须来自真实调用。

## 13. Demo 身份与处理来源投影（DR-0013 Verified 限定范围）

用户打开前台时，首屏先显示客户端产品级的 Demo 1、Demo 2 或 Demo 3 业务身份与目标；当前状态副标题再从对应 Task、WorkCockpit、Demo2Execution 或 Run Snapshot 对账。统一显示“已运行 / 未调用 / 未执行 / 待核对”，只有模型来源显示“模型已调用”，但工程不新增通用 `call_trace` 字段。

Demo 1 直接投影 `TaskSnapshot.stage_records[].processing`（`path/model_called/model/elapsed_ms/output_used`）及阶段状态；Demo 2 的路由选择投影 `RouteSelectionReceipt.processing`，受控内部执行投影 `Demo2ExecutionSnapshot.workers[].processing/events/receipt`；Demo 3 复用 `RunSnapshot.status/control_plan/evidence/approvals/permit/tool_result/impact_preview/execution_receipt` 与 Run SSE/AuditEvent。Demo 2 的 selected 不等于 running，completed 也只表示内部工件包完成且 `external_side_effect=none`；Demo 3 以“执行许可服务”“受控演示工具”为主，Permit/Gateway/Simulator 仅是二级技术元信息。v>1 的 Demo 1 缺少 `stage_records`，或旧 Plan/Act 缺少 `processing` 时显示“模型调用待核对”，不得推断未调用；unknown 工具结果显示“工具结果待核对”，不得写成未调用或未执行。Proposal 或 Task-derived action 出现时，前端全局切换到 Demo3/审计视图，避免继续显示 Demo1/2 身份。

普通业务 UI 不显示 Prompt、CoT、raw `event_type/payload/trace`、密钥、Permit token/内容/permit_id/签名、内部 ID、Worker 对话或供应商原始响应；“执行许可服务”“受控演示工具”及必要的“已运行/结果待核对”业务状态可以显示，技术审计另行受控。移动端按 Demo 身份、当前阶段、调用状态、下一步渐进披露，不把完整事件列表堆在首屏。工程验证和截图见 [`DEMO-IDENTITY-AND-CALL-TRACE-EVIDENCE-20260820`](evidence/DEMO-IDENTITY-AND-CALL-TRACE-EVIDENCE-20260820.md)。

## 14. Harness Snapshot 与 SSE（DR-0016，Limited Verified 规划纵切）

Harness 的命名事件为 `workspace_index`、`planning_started`、`planning_completed`、`plan_validation`、`ready_to_execute` 和失败时的 `harness_failed`。每个事件带单调 `sequence`；浏览器用 `after` 续读并在事件到达后 GET 完整 `HarnessRunSnapshot`。不存在或非当前 Owner 的 Run 在建流前统一返回 404。事件只通知阶段变化，Snapshot 才拥有当前 status、version、来源、plan、model receipt 和 validation errors。

正常路径的四个前台阶段与五个服务端事件不是一一合并的动画：`planning_started` 只说明进入规划；`planning_completed` 必须结合 `model_receipt.called/output_used`；`plan_validation` 才允许显示服务端校验通过；`ready_to_execute` 固定显示“尚未执行”。失败时保留文件范围和真实模型调用回执，清楚说明执行未启动。终态只维持一次 SSE 连接并最终 GET；非终态断流用 `after=N` 续读。当前 memory Runtime 在 API 重启后无法恢复，SSE 重连只覆盖同一进程仍持有 Run 的情况。三次 live run、六张桌面/移动截图和 `48 passed (3.6m)` 浏览器结果见 [`FORTE-WORKSPACE-AGENT-HARNESS-EVIDENCE-20260824`](evidence/FORTE-WORKSPACE-AGENT-HARNESS-EVIDENCE-20260824.md)；它们不是用户研究。
