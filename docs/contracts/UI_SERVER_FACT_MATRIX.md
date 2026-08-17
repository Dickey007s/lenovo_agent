# UI—服务端事实矩阵（Demo 1、Demo 2 与报价工作区）

> 状态：Demo 1 与报价协议映射 `Ready`，交互决策 `DR-0005` 为 `Draft`，报价核算决策 `DR-0006` 在固定演示报价、当前公式、revision 协议和被测恢复路径内为 `Verified`；`DR-0007` 在固定客户回复草稿到治理 Run 的单一纵切内为 `Verified`；Demo 2 `DR-0008` 的单进程 memory WorkCockpitSnapshot、路由解释和本次选择纵切为限定范围 `Verified`。自动化只能验证投影与调用语义，不能代替真实用户理解、真实 Connector、Adaptive Swarm Runtime、生产报价规则或多实例一致性验证。

## 1. 组件映射

| UI 状态或组件 | 用户含义 | 服务端权威字段 | Snapshot / SSE | 允许动作 | 失败与恢复 | 默认隐藏 |
| --- | --- | --- | --- | --- | --- | --- |
| 固定 Demo 1 空态（当前交互 Draft） | 尚无 Task 时，本轮将准备客户 A 的经营分析、风险页和回复草稿 | 客户端复制固定 `/v1/demo1/tasks` 创建模板；创建后必须与返回的 `contract.title/objective/deliverables` 一致 | 初始 `GET /tasks` 确认无 Task 后才显示；加载中只显示读取态 | 一次“开始准备汇报”依次调用 create 与 start | 初始列表慢时不显示创建动作；create 成功/start 未知时进入既有 pending 对账 | 不把客户端模板副本冒充 Snapshot；通用模板描述接口尚未实现 |
| 非 Tasks 工作区的后台任务摘要（当前交互 Draft） | 用户编辑邮件、文档等工作区时，只需要知道是否有当前/上一轮经营汇报以及是否需要前往处理 | `TaskSnapshot.contract.title/objective/status/phase`；`taskSyncState/taskTransportState` 是客户端事实 | 初始列表、mutation 响应；Task SSE 只触发完整 Snapshot 对账 | “打开任务 / 前往处理 / 查看任务 / 查看汇报”只切换到 Tasks；“前往处理”进入 Tasks 后聚焦待确认标题；断线时可重新连接或立即对账 | 保留最后确认 Snapshot；`task=null` 时按 loading、connecting、reconnecting、synced 分别表达读取、连接、恢复和确认无任务，只有 synced 可显示可开始事实；跳转不产生 TaskEvent | Conflict 候选、来源、分支控制、Task ID、预算、版本和 Runtime 明细 |
| 任务简报、主要下一步与摘要（当前工程代理已通过） | 当前要准备的三项结果、材料核对数、业务状态、同步状态和一个状态推进主动作 | `TaskSnapshot.status/phase/contract.title/contract.objective/contract.deliverables/branches/conflicts/last_commit`；`taskSyncState/taskTransportState` 是客户端事实 | 初始列表、创建/mutation 响应；Task SSE 触发 `GET /tasks/{id}` 对账 | Ready 开始；Conflict 的弱化入口定位到待确认项；Committed 查看成果；刷新为次要动作 | 未同步时禁用控制并可立即对账；同步版本只表达对账结果，budget/owner/internal step 不进入业务摘要 | Prompt、内部调度、实际幂等键、完整 Task JSON、网络栈、数据库类型与内部重试日志 |
| 三份材料的当前状态（当前工程代理已通过） | 每份材料的当前内容、核对/冲突和是否纳入本轮成果 | `contract.deliverables[]`、`branches[].status/artifact_heads`、`artifact_versions[]`、`verification_reports[]`、`conflicts[]`、`last_commit` | Snapshot、`BRANCH_STATUS_CHANGED`、工件/验证/冲突/Commit 事件后 GET 对账 | 有 head 时打开成果；具体控制在待确认区 | 单分支错误只影响对应材料；没有 head/report/Commit 时明确等待，不用颜色补造进度 | Branch version、Worker 对话、内部计划文本、完整 Trace payload |
| 待确认项（当前工程代理已通过） | `waiting_input` 中的 open Conflict、为什么必须由人决定、候选依据、受影响材料和固定 Demo 决定后果 | `status`、`conflicts[].status/subject/summary/source_refs/candidate_values`、Branch/head/report、固定 `resolve_evidence` 语义、`TaskSnapshot.version` | Snapshot、`CONFLICT_OPENED/RESOLVED`、`CONTROL_ACCEPTED/APPLIED` | 只在 Tasks 工作区开放；唯一状态推进动作采用固定 CRM 正式来源；同分支按服务端可定位顺序逐项开放；查看材料；次级补证、Pause、Take over；可切 Agent | 只有 `waiting_input` 投影可操作卡；resolved 后记录变为已解决；failed/cancelled 终态隐藏残留 open 卡但不改写记录；请求失败先对账；Steer 只反馈待后续循环应用 | 非 Tasks 工作区不渲染本组件；普通业务 DOM 不接收原始 `source_ref`、未授权来源正文或检索日志；未知来源使用隐藏占位 |
| 来源依据投影（当前交互 Draft） | 用户知道这些是演示数据，并能读懂邮件、CRM、预测表或项目周报及版本 | 服务端 `source_refs[]` 原值；客户端固定 allowlist 仅负责显示标签 | 随包含 Conflict 或 Artifact 的完整 Snapshot 到达，不单独产生事件 | 展开“查看演示数据来源”；真实控制仍提交协议要求的原始来源值 | 已知值投影为“演示数据 · 业务来源（版本）”；未知值显示“内部标识已隐藏” | 原始 `fixture:` / `source:` / 路径 / URL / 凭据形态不进入普通业务 DOM；序号 DOM key 不复用原始值 |
| 本轮成果（当前工程代理已通过） | 服务端确认的三项成果、验证状态以及客户回复仍为草稿、未发送 | 终态 `status`、`last_commit.artifact_version_ids`、`artifact_versions[]`、`verification_reports[]` | resolved mutation / Task SSE 后的 Snapshot | 打开经营分析、风险页、客户回复草稿；查看折叠审计证据 | 缺少终态、Commit 或工件时不得显示完成；成果按契约顺序排列 | state hash、版本与事件等审计细节默认折叠；不暗示真实外部发送 |
| 已核对客户回复的受控动作（DR-0007 限定范围 Verified） | 用户把已完成成果准备成外发动作，并在发送前理解对象、风险与后果 | `TaskSnapshot.status/last_commit`、目标 `ArtifactVersion`、passed `VerificationReport`；`ProposedActionSpec.task_artifact_binding`、`RunSnapshot.risk/control_plan/status` | `POST /tasks/{task_id}/artifacts/{artifact_version_id}/actions/email-send` 返回 Run；后续审批/授权 REST 与 Run 审计 SSE | 在当前已验证回复上“准备发送”；Gate 中批准、拒绝、确认执行；查看最终 Simulator 结果 | 准备不等于发送；历史/未验证工件禁用；绑定事实在每个治理门前重校验，变化则 Action 失效；拒绝/失败不回滚 Task；结果未知时同 key 对账 | 原始内容摘要、Commit state hash、Permit、策略内部秘密；业务界面只显示成果版本和演示目标，不暗示真实邮件已发出 |
| 开始新一轮汇报（当前交互 Draft） | 开始另一轮独立经营汇报，不是重置当前 Task，也不是把它改回可启动状态 | 新 round key 的 `POST /v1/demo1/tasks` 返回新 Task ID 和 `ready / contract` Snapshot；随后新 Task 的 `POST /start` 返回其后续 Snapshot | 两个 mutation 响应；随后 Task SSE/GET 对账 | 终态时一次点击创建并启动；同轮重试复用 key | create 成功/start 未知时按 pending mutation 对账；旧 Task、Artifact、Event、Commit 不修改 | round key、旧 Task 内部标识；不暗示旧轮次已删除或已有历史轮次选择器 |
| Task Artifact Workspace（PR 4 已实现，PR 6 已验证历史防误读） | 当前 Branch head、版本、验证、冲突、结构化内容、来源、lineage 与 Commit，以及是否主动固定查看历史版本 | `contract.deliverables[]`、`branches[].artifact_heads/status`、`artifact_versions[]`、`verification_reports[]`、`conflicts[]`、`last_commit`；`follow_head/pinned_history` 是客户端选择事实 | mutation 响应；Task SSE 后的完整 Snapshot 对账 | 从泳道打开 head、选择分支/版本、返回当前版本、按需展开来源与验证检查 | 默认 mutation 后跟随新 head；主动选择非 head 时显示历史 banner 与当前 head；candidate/conflict 不显示完成；当前只读 | 按 `artifact.kind` allowlist 投影；未知 kind/字段默认隐藏；非安全或疑似敏感 `source_ref` 显示隐藏占位 |
| Tasks“执行记录”（保留） | 原工作台待办仍可按状态分栏查看和编辑 | `WorkspaceArtifact(kind=tasks)` | Workspace API 与 Conversation SSE | 在“进度 / 成果 / 执行记录”间切换；修改优先级、状态和内容并保存 | Task Snapshot 不覆盖手工待办内容；状态变化仅重排本地看板，保存后才更新 WorkspaceArtifact | 两套数据模型的内部 ID 与调度细节 |
| Task Control（PR 3 部分实现） | 用户能否记录方向指令、暂停或接管固定分支 | `TaskSnapshot.version`、`controls[]`、Branch status、服务端允许转换 | `CONTROL_ACCEPTED`；分支控制另有 `CONTROL_APPLIED` | Steer、Pause branch、Resume、Take over、Return control | pending mutation 将原 key、intent 和预期版本写入当前标签页 `sessionStorage` 并冻结新控制；offline/reconnecting 时可同 key 对账，重放确认后再 GET 最新 Snapshot；`409` 后刷新并提示复核 | idempotency key、权限哈希 |
| Tasks 中的待我决定 / Agent 对话模式 | 用户是在处理当前 Task 阻塞，还是继续通用 Agent 对话 | 客户端右侧模式；Conversation Thread/Message 与 Action Gate 仍走既有事实链 | 模式切换无 Task API/SSE；Agent 模式继续使用 Conversation/Run SSE | 只在 Tasks 工作区切换待我决定与 Agent 对话；切换不重建 Conversation | 离开 Tasks 后卸下决定面板，仅保留后台任务摘要；Action Gate 继续使用原 tray | 非 Tasks 工作区不复刻 Conflict/Control；Conversation 内部 Prompt、CoT、Permit token、工具秘密 |
| Stream Health Badge（已并入 Task Bar） | 浏览器是否能读取并对账服务端 Snapshot | 客户端 `taskSequenceRef/taskSyncState/taskTransportState`，不属于业务状态 | EventSource open/error、新 TaskEvent、对账 GET | offline 可手动重新连接，reconnecting/pending 可立即对账；未同步时禁止 Task Control | 自动重连；Snapshot 对 `version/last_event_sequence` 与已观察 SSE floor 单调应用；旧 GET 被拒绝，未覆盖 floor 时保持 `reconnecting`；PR 5 已实测进程重启，PR 6 已测两项乱序 | 网络栈、数据库类型和内部重试日志 |
| Verified Commit Summary（已实现） | 服务端是否已生成最近 Commit | `last_commit.summary/committed_at/task_version/state_hash/artifact_version_ids/verification_report_ids` | Snapshot、`CHECKPOINT_COMMITTED`、`TASK_COMMITTED` | 查看摘要、提交版本、工件/报告数量与 state hash | 没有服务端 Commit 时不得出现完成；引用/hash 有内存回归，PostgreSQL 16.14 已验证 v3 Commit 跨进程恢复 | 原始 Trace payload、签名和密钥 |
| Task Error Banner（部分实现） | mutation 是否被拒绝、过期或结果待确认 | HTTP 状态、重新 GET 的 Snapshot version；`last_error` 完整路径尚未实现 | mutation 响应与 Snapshot 对账 | 复核后重新提交 | `5xx` 只显示结果待确认；不凭客户端异常宣告失败 | 堆栈、内部服务地址、敏感参数 |
| Action Gate Tray | 某个副作用动作是否可执行 | `RunSnapshot.risk/control_plan/permit/tool_result/thread_id`；注册 capability 的 Action 由当前 WorkspaceArtifact 内容与 revision 确定性重建；DR-0007 的固定路径另携带 `task_artifact_binding` | Conversation `action.proposed`、Task 工件准备动作响应、Run API/SSE、绑定 Thread 的 continue stream | 补证据、审批、Authorize；结果未确认送达时重新读取 | 模型参数/source_refs 不直接执行，内容不匹配或 Artifact 竞态时不创建动作；Task 绑定变化时失效；未解析纯文本收件人/附件类别固定 deny且自报 evidence 不能解锁；跨 Thread continue 拒绝；完成说明单进程重放同一消息 | Permit token、策略内部秘密、模型伪造 payload/source、Task 内容摘要与内部重放缓存 |

### 1.2 Demo 2 智能工作驾驶舱（DR-0008，限定范围 Verified）

以下字段和页面已在固定演示纵切中实现。服务端当前仅使用 memory；固定队列和路由选择不等于后台执行。

| UI 状态或组件 | 用户含义 | 服务端权威字段 | Snapshot / SSE | 允许动作 | 失败与恢复 | 默认隐藏 |
| --- | --- | --- | --- | --- | --- | --- |
| 驾驶舱固定队列 | 四项统一工作来自当前 Owner 的固定演示 Snapshot；顺序由服务端给出 | `WorkCockpitSnapshot.owner_id/backend/version/last_event_sequence/items[]`；每项 `facts` | `GET /demo2/cockpit`；当前没有 Demo 2 SSE | 查看工作卡、演示来源、业务条件和固定队列位置 | GET 未返回前只显示读取态；失败保留已有 Snapshot并提供重新读取 | 原始 Prompt、检索日志、原始 `fixture:` ID、内部来源路径 |
| 路由解释 | 用户知道每项任务为什么进入某种处理方式 | `items[].recommendation/allowed_modes/route_profiles` | 同一 Snapshot；路由解释不由前端自算 | 展开路由理由和允许模式 | 字段缺失或版本过期时显示待核对，不补造推荐 | 模型思维链、策略内部权重、Worker 对话 |
| 三项简单任务固定路由 | 报销异常、供应商邮件、周报分别使用 Tool Call、Single Agent、Fixed Workflow 的固定演示选择 | 对应 `items[].recommendation`、`selected_mode`、`selection_source=admission`、`execution_status=not_started` | 同一 Cockpit Snapshot | 查看规则选择；单一允许模式的 radio 禁用且没有确认按钮 | 读取失败后重新 GET；不创建 Worker | 真实工具调用、模型调用、成本账单、时延日志 |
| 客户 A 待决定 | 复杂任务尚未自动启动；用户需要在允许模式中作出本次选择 | `items[].allowed_modes=[single_agent,fixed_workflow,adaptive_swarm]`、`selected_mode`、`selection_source`、`override_scope`、`version`；响应另含 `cockpit_version/cockpit_last_event_sequence` | `POST /demo2/work-items/{id}/route` 返回 `RouteSelectionResult` | 接受推荐、选择其他允许模式、暂不选择；范围固定为 `this_run` | 只应用服务端返回的聚合版本；`expected_version` 冲突保留本地意图并 GET 最新 Snapshot；未知结果先 GET 对账 | 内部 Admission 打分过程、底层调度图、实际幂等键 |
| Adaptive Swarm 推荐/本次选择 | 用户选择了复杂协作方式，但系统尚未开始执行 | `items[].selected_mode=adaptive_swarm`、`selection_source`、`override_scope`、`execution_status=not_started` | 选择 mutation 返回的 `RouteSelectionResult.item`；没有执行 API/事件 | 查看依据，或用另一允许模式覆盖本次选择 | 不允许的模式或过期版本返回 409；任何错误都不能改写为已启动 | 不展示“已启动”“运行中”“已完成”、真实 Worker、真实 Connector、实际成本/时延 |
| 演示策略成本/时效预测 | 用户看到的是固定规则给出的工具调用上限、预计秒数和并行上限，不是实测结果 | `items[].route_profiles[].forecast.source_type=fixture_policy_forecast`、`estimated_tool_calls/estimated_runtime_seconds/max_workers` | 随 WorkCockpitSnapshot 返回 | 查看预测与选择代价 | Schema 缺失时页面不能补数字 | 供应商账单、模型 Token 计费、真实 SLA、未经测量的节省比例 |
| 驾驶舱读取与恢复边界 | 浏览器是否读到了当前进程的最新 WorkCockpitSnapshot | 客户端 loading/error + 服务端 `owner_id/version/last_event_sequence` | 初始/手动 GET 与 mutation 后 GET 对账；无 SSE | 重新读取、冲突后复核并重试 | 保留最后确认 Snapshot；memory API 重启会丢选择，不宣称跨进程恢复 | 网络栈、数据库 DSN、内部重试日志 |

本节所有行均限定在 `DR-0008` 的单进程固定演示纵切。它只覆盖固定队列、路由解释、客户 A 的本次模式选择和服务端 Admission 事实；拖拽调序、长期排序偏好、真实执行、动态 Worker、Shared Artifact Workspace、Verifier/Resolver、成本/时效实测和跨进程恢复留待后续决策与证据。

当前 Task Director 展示的仍是固定 Demo 1 的服务端状态，不是通用 Agent 执行器。Task、分支、工件、验证、冲突和 Commit 必须逐项映射上述 Snapshot 字段；不存在于 Snapshot/TaskEvent 的事实不得由前端文案、颜色、泳道或 Toast 补造。顶部连接文案映射独立客户端传输状态，pending mutation/Snapshot 对账仍由 Task 同步状态表达；右侧模式、活动工作区和工件选择模式同样只是客户端事实。非 Tasks 工作区只能投影后台任务摘要并跳转到 Tasks，不得提交决定或分支控制。字段 allowlist 与 Conflict/Artifact 共用的 `source_ref` 投影只放行契约中的四个已知 Demo 1 Fixture 引用，将其显示为带“演示数据”前缀的业务标签，并使用与原值无关的序号 DOM key；原始标识不进入普通业务 DOM，其他值 fail closed。这只是前端第二道防线，服务端仍保存原值且尚无通用字段可见性 Schema/display projection。

### 1.1 报价工作区与确定性问答（DR-0006）

| UI 状态或组件 | 用户含义 | 服务端事实与客户端当前值 | REST / SSE | 允许动作 | 失败与恢复 | 默认隐藏 |
| --- | --- | --- | --- | --- | --- | --- |
| 报价身份与最低折后比例 | 当前核对的是哪张演示报价、针对哪个客户、使用什么币种和批准底线 | 服务端 `WorkspaceArtifact(kind=quote).artifact_id/revision/content.quote_id/customer/currency/approved_floor` 与 `sources`；客户端不能覆盖 | `GET /workspace`、保存响应或 `artifact.updated` | 编辑有效期；查看演示来源 | 服务端字段缺失/非法时显示“待核验”，不能前端补 88% | 原始缓存、凭据、真实系统地址；不得暗示实时 CRM |
| 报价行编辑 | 用户可在当前视图修改项目名、数量与折后比例，并看到尚未保存的结果 | 浏览器当前 `workspace_context.items[].name/qty/discount`；`unit_price` 来自服务端基线；行数必须与服务端版本一致 | 消息显式携带上下文与 `workspace_artifact_id/revision`；保存携带 `expected_artifact_id/revision` | 修改 `name/qty/discount/valid_until`、保存、询问核算 | 无效、越界、超限或行数不一致时 fail closed；修正字段后恢复 | 客户端提交的 `quote_id/customer/currency/approved_floor/unit_price/sources/approval` 不进入权威合并 |
| 行小计与四项汇总 | 当前标准总价、优惠金额/优惠率、综合折后比例/折数、折后总计 | 服务端 Decimal 结果是保存与 Agent 回答事实；前端整数分/BigInt 按同一公式即时投影；旧 `subtotal/total` 不可信 | 未保存编辑只更新本地投影；保存响应规范化；Agent 回复走 Conversation SSE | 编辑后即时核对；保存；要求再算 | 任一行无效时所有聚合值显示“待核对”，不得显示部分总计或历史值 | Decimal/BigInt 中间值、旧合计、模型生成金额 |
| 最低折后比例状态 | 每行是否低于批准底线；这不是“总优惠率” | 服务端 `approved_floor` 与当前每行 `discount`；前端只翻译结果 | 当前上下文核算；保存响应；确定性 Agent 回复 | 检查最低折后比例；修正低于底线的行 | 无底线时显示不可核验；低于底线列出行项目；不能把综合比例高于底线替代逐行检查 | 内部规则实现、未提供的审批推断 |
| 报价核算/来源 Agent 回答 | 回答使用当前屏幕值、逐行公式和演示来源，不从历史对话补金额 | `ConversationService` 将当前可编辑值合并到服务端报价基线后调用 Decimal Quote Calculator；LLM 不生成数值 | `message.created → assistant.status(calculating) → message.started → assistant.delta* → message.completed` | “核算/再算/检查底线/说明来源”；写入或发送进入既有业务规划/治理 | 显式空上下文或非法字段时明确拒绝猜测；同线程流在单进程内串行 | Prompt、思维链、Thread 锁、历史错误金额、真实 CRM 暗示 |
| 已保存、待重新复核 | 当前修改已持久化，但不能沿用演示基线审批 | `WorkspaceArtifact.content.approval.status=needs_review`、`requires_recheck=true`；绑定旧 Action 时由服务端失效 | `PUT /workspace/quote` 完整响应；后续 `GET /workspace` | 修正并再次保存；等待后续复核 | 422 时保留当前未保存输入和上一个服务端版本，不显示已保存 | 旧审批或 Permit 不得作为当前版本状态展示 |
| 工作区版本冲突与晚到 Agent 结果 | 当前草稿基于旧版本，或用户在请求等待期间又编辑；系统未覆盖新输入 | 保存 409 / `workspace.conflict.latest_artifact`；请求时 Artifact/edit token、编辑起点和草稿是客户端恢复事实 | `PUT /workspace/quote` 409 后 `GET /workspace`；SSE `workspace.conflict` 或晚到 `artifact.updated` | 查看最新版本；重新应用仅本地独有修改；复核后再保存 | 不同字段可三方重应用；同字段双改、缺失 base 或行结构变化时列出冲突并拒绝自动合并；等待期本地编辑保持可见 | 内部锁、edit token、revision 比较日志；不把当前机制称为多人实时协作 |

报价前端即时投影只用于让用户核对当前未保存输入，不是独立业务真值。跨 API 边界的报价身份、标准价、底线、规范化总计和 `needs_review` 仍由 Workspace 服务端事实约束；Agent 回答必须重新从这些事实计算。基线演示值与来源记录见 [`DR-0006`](../decisions/DR-0006-deterministic-quote-calculation.md) 与对应 Evidence：全量 Python `108 passed, 1 skipped (2.62s)`，报价/Conversation 聚焦 `54 passed (1.72s)`，报价浏览器 `15 passed (23.6s)`，完整浏览器 `27 passed (1.1m)`，Ruff、lint、build 通过。`Verified` 只覆盖上述固定范围；Workspace 锁/revision 仍是单 API 进程内机制，没有数据库 CAS 或多实例验证。

## 2. 状态文案与颜色不是事实

前端可把服务端枚举翻译为中文，但不能改变语义：

| 服务端状态 | 建议中文 | 用户可做什么 | 禁止推断 |
| --- | --- | --- | --- |
| Task `running` | 任务运行中 | 查看分支、Steer、暂停或接管 | 不能按动画估算完成比例 |
| Task `waiting_input` | 等待你的决定 | 处理冲突或接管 | 不能把单分支等待写成整任务失败 |
| Task `paused` | 已暂停 | Resume 或 Take over | 不能声称后台仍在执行 |
| Task `taken_over` | 由你接管 | 当前只能归还控制 | PR 4 仍无人工编辑并创建新 ArtifactVersion 的闭环 |
| Task `verifying` | 正在验证 | 查看候选工件，等待结果 | candidate 不能显示已完成 |
| Task `committed` | 已验证并提交 | 查看 Commit、工件与验证结果 | 必须同时存在服务端 Commit 事实；普通 UI 不展示内部 Trace |
| Branch `waiting_evidence` | 此分支等待依据 | 解决冲突、Pause 或 Take over | 其他分支状态保持独立 |
| Branch `failed` | 此分支失败 | 查看原因、从 Commit 恢复或接管 | 不自动覆盖为整个 Task failed |

颜色、图标、进度条、动效、Toast 和按钮 disabled 状态都是 UI 表达，不能成为风险、预算、验证、执行或完成的权威来源。

## 3. 控制提交时序

```mermaid
sequenceDiagram
    participant U as 用户
    participant UI as Web
    participant API as Task API
    participant S as TaskService
    participant DB as Durable Store

    U->>UI: Steer / Pause / Take over
    UI->>API: command + expected_task_version + idempotency_key
    UI-->>U: 显示“正在提交”，业务状态不变
    API->>S: 校验身份、状态转换、版本与幂等
    S->>DB: 原子写 Snapshot + ControlEvent + TaskEvent
    DB-->>S: commit
    S-->>UI: 新 TaskSnapshot
    alt 分支控制已应用
        S-->>UI: 新 Snapshot + CONTROL_APPLIED
        UI-->>U: 按服务端版本更新状态
    else Steer 仅被接受
        S-->>UI: 新 Snapshot + CONTROL_ACCEPTED
        UI-->>U: 显示“已记录，等待后续循环应用”
    end
```

服务端返回 `409` 时，UI 必须读取最新 Snapshot，并让用户看到哪些字段发生变化；不得用旧 version 自动重试含义可能已经改变的命令。当前 PR 6 浏览器回归已覆盖版本提示、复核和用户再次提交成功；字段级变更摘要和重新应用入口仍未完成，PR 4 当时也未覆盖该路径。

## 4. 断线、过期与恢复

1. **断线**：显示“服务连接中断，正在恢复 / 正在重新对账”；保留最后确认 Snapshot，停止模拟进度，禁用新的控制提交。固定路径没有可据此声称仍在推进的后台 worker；PR 5 已通过停止 API 进程实测该前台状态。
2. **重连**：EventSource 重连后 GET Snapshot；重复事件按 `task_id + sequence` 去重。PR 5 已验证没有停机期新事件时的自动重连和 v2/v3 对账；PR 6 又验证延迟旧 GET 不能回滚较新 mutation Snapshot。
3. **序号缺口**：已观察 SSE sequence 成为 Snapshot 应用和 `synced` 的下限；PR 6 验证未覆盖该 floor 的乱序 GET 不会污染 UI 或伪标已同步。真实停机期事件缺口的完整回放仍未验收。
4. **旧版本**：`409` 后不改变业务状态；当前展示服务端最新 version、提示复核并允许用户再次提交。字段级变更摘要和重新应用入口仍待实现。
5. **身份过期**：`401/403` 后转只读，保留未提交 Steer 文本但不自动重放。
6. **服务重启**：PostgreSQL 16.14 下已验证同一数据库、三个顺序 API 进程恢复 v2/v3；内存模式进程退出后仍会丢失，Conversation Thread/Message 也不会随 Task 恢复。
7. **请求结果未知**：先显示“结果待确认”，把原 key、intent 和预期版本保存在当前标签页；同 key 确认首次结果后再 GET 最新 Snapshot。PR 4 E2E 已覆盖请求发送前 abort、reload 后入口可达、同 key 重试和无重复工件；请求已到服务端但响应丢失尚未覆盖。

当前 EventSource 只通过 `after` 查询参数传递游标，不使用 `Last-Event-ID`；服务端轮询 TaskStore，没有跨实例通知总线。前端会在连接打开或收到事件后重新 GET Snapshot，在连接错误后自动重试，并对 mutation 409/未知结果重新读取 Snapshot；Snapshot 应用同时检查当前 version、last sequence 和已观察 SSE floor。PR 4 已证明发送前 abort 恢复，PR 5 已证明同页 API 进程停止/重启，PR 6 已证明两类 GET/SSE 乱序防回滚。真实事件缺口回放、身份过期、服务端已提交但响应丢失和多实例连接迁移仍未完成浏览器 E2E。

Workspace revision 恢复是独立于 Task mutation 的较小机制：保存 409 或 `workspace.conflict` 后保留草稿并显式选择最新/三方重应用，报价浏览器已覆盖不同字段合并与同字段冲突。它不使用 Task 的 idempotency key、Snapshot sequence 或 SSE `after`，也不证明数据库 CAS、多实例锁、离线重放或历史版本浏览。

## 当前 Demo 1 渐进映射（2026-08-17）

| 用户看到的状态 | 服务端事实 | 浏览器行为与边界 |
| --- | --- | --- |
| 读取资料 | v2 `running / observe` + `stage_records[observe]` | `start` 后显示；确认 Snapshot 后才请求下一步 |
| 拆分任务 | v3 `running / plan` + Plan record | 严格适配器结果只作为摘要/详情；身份和来源由服务端重建 |
| 生成材料 | v4 `running / act` + Act record | 显示候选工件，不能显示为已验证 |
| 核对事实 | v5 `verifying / verify`，随后 v6 `waiting_input / verify` | v6 显示 5 工件、1 open conflict、2 passed verification |
| 已提交 | v7 `committed / commit` + `last_commit` | 仅收到服务端 Commit 才显示完成 |

`stage_records` 缺失时使用默认空数组以兼容旧 Snapshot；客户端不能用动画、SSE payload、版本猜测或 token 预算推导阶段。关闭浏览器只保留最后一次持久化 mutation，重新打开后继续协调；无后台 scheduler。Plan/Act 使用 `deepseek-v4-pro`，只有与服务端批准模板逐字段一致的文字才记录为 `model`，否则显式 `template_fallback`；smoke 只证明连接和严格响应，不证明质量。预算是 steps/tool calls/runtime，不是 token cost；跨实例无分布式 LLM lease。原始 `fixture:`、思维链和内部 ID 只在受控服务端边界处理，普通 DOM 使用“演示数据”业务标签。

## 5. 实现与验证责任

| PR | 前台最小输出 | 后端事实 | 必须提供的证据 |
| --- | --- | --- | --- |
| PR 1 | 只定义 TypeScript 类型与本矩阵，不宣称页面已实现 | Pydantic 目标协议 | 严格 Schema 测试、TypeScript 编译 |
| PR 2 | 已实现真实 Task Bar、同步状态和 Snapshot 读取 | 已实现 Store、创建/读取 API、Owner scope、创建幂等和 `TASK_CREATED` SSE | 当前自动化覆盖内存 Store 恢复、Owner 隔离、创建幂等和游标；PostgreSQL 重启、多实例通知与浏览器 E2E 仍未验证 |
| PR 3 | 已实现固定 Fixture 的最薄 Branch/Conflict/Control/Commit；Action Gate 打开时视觉隐藏明细并保留草稿 | 单次 start/resolve mutation、Verifier、ControlEvent、ArtifactVersion | 已有内存引用/hash/幂等测试、桌面/移动冲突截图和桌面提交态截图；PostgreSQL 重启和完整浏览器恢复仍待补 |
| PR 4 | 已实现只读 Task Artifact Workspace、Tasks 双 tab、Task 面板直达工件和移动端布局 | 复用 PR 3 Snapshot/Event/Artifact/Verification/Conflict/Commit | system Edge E2E `2 passed (18.4s)`；覆盖主路径、发送前 abort/reload/同 key恢复、桌面/移动截图与被测 overflow/44px；SSE/响应丢失/PostgreSQL/用户研究仍待补 |
| PR 5 | 顶部按独立传输状态显示已连接/中断，Task Bar 单独显示同步/对账；断线时保留 Snapshot 并禁用控制；Conflict/Artifact 共用 fail-closed source-ref 投影 | PostgreSQL TaskStore 恢复 v2/v3；历史 mutation result Snapshot；事件/工件唯一约束与 Commit 状态机 | 合并兼容回归：opt-in PostgreSQL system test `1 passed (9.78s)`，三个顺序 API 进程、两个演示轮次、原 Task 45 events/7 artifacts/1 commit；system Edge suite `3 passed (17.0s)`，另有基线同页断线/恢复五张截图；事件缺口/响应丢失/用户研究仍待补 |
| PR 6 | 原基线实现 Task Director/Decision Inbox、历史版本与 Snapshot 单调应用；当前修订改为根路径业务任务、单次开始、具体决定后果和完成成果 | 复用现有 TaskSnapshot/Control；无 Task 空态为固定 Demo 模板副本；客户端拒绝低 version/sequence 或未覆盖 SSE floor 的 Snapshot；快速重复开始由 in-flight guard 收敛；没有 `conflict_id` 的 resolve 只开放每分支第一条 open conflict；只有 `waiting_input` 投影可操作冲突，终态优先；无任务 offline 在左右区域使用同一恢复事实 | 原基线 [`TASK-DIRECTOR-INTERACTION-DEMO1-PR6-20260811`](../evidence/DEMO1-PR6-TASK-DIRECTOR-INTERACTION-EVIDENCE.md) 为 `6 passed (34.5s)`；当前 Draft [`TASK-DIRECTOR-USABILITY-AUDIT-DEMO1-PR6-20260811`](../evidence/DEMO1-PR6-USABILITY-COMPREHENSION-AUDIT-20260811.md) 为 `12 passed (43.7s)`；工程代理通过不证明用户理解，5 人测试未运行 |
| 当前后续修订（工程范围已验证，交互结论 Draft） | 非 Tasks 只保留后台摘要与跳转；来源明确标为演示数据且原始 ID 不入 DOM；终态入口为“开始新一轮汇报”并一键创建、启动独立 Task | 仍复用同一 TaskSnapshot、source_refs、创建/启动幂等协议；旧 Task 不 mutation，前端也不新增历史轮次选择事实 | 来源为 [`USER-FEEDBACK-20260811-ROUND-AND-SOURCE-03`](../sources/USER-FEEDBACK-20260811-05-source-labels-and-new-round.md)；独立工程证据为 [`TASK-DIRECTOR-ROUND-AND-SOURCE-CLARITY-20260811`](../evidence/DEMO1-ROUND-AND-SOURCE-CLARITY-EVIDENCE-20260811.md)，完整浏览器 E2E `12 passed (44.5s)`；历史 PR 6 evidence 未反写，自动化不证明用户理解 |
| DR-0006 报价修订（限定范围 Verified） | 当前行即时核算、指标区分、错误停算、待复核、版本/晚到结果冲突恢复与可追溯 Agent 回答 | Decimal/BigInt 同公式；Workspace Artifact/revision/request epoch；请求发送快照作为三方 base；服务端来源与字段所有权；Artifact/Thread 绑定 Action；严格收件人识别与确定性 unresolved-context deny；结果完成消息重放 | [`QUOTE-WORKSPACE-DETERMINISTIC-CALCULATION-EVIDENCE-20260811`](../evidence/QUOTE-WORKSPACE-DETERMINISTIC-CALCULATION-EVIDENCE-20260811.md)：提交 `2f9866f + fe865bd + e2c4b56`；Python `108 passed, 1 skipped (2.62s)`；聚焦 `54 passed (1.72s)`；报价浏览器 `15 passed (23.6s)`；完整浏览器 `27 passed (1.1m)`；不证明用户理解、真实 Connector/计价或多实例 CAS |
| DR-0007 Task 工件动作桥（限定范围 Verified） | 完成态列出成果，当前已验证客户回复提供“准备发送”；Gate 显示绑定版本、演示目标、L4 风险、确认原因和拒绝后果 | TaskService 校验 Commit/ArtifactVersion/Verification；RunService 持久化并重校验 `TaskArtifactBinding`；Policy/Evidence/Approval/Permit/Gateway 延续 Demo 3 事实链 | [`TASK-ARTIFACT-ACTION-BRIDGE-20260813`](../evidence/DEMO1-DEMO3-TASK-ARTIFACT-ACTION-BRIDGE-EVIDENCE-20260813.md)：实现提交 `d827f29`、文档提交 `d1cc746`、PR #12；Python `112 passed, 1 skipped`；完整浏览器 `29 passed`；Ruff、lint、build 与治理测试通过；不证明真实发送、通用工件动作、跨重启 Run 幂等或用户价值 |
| DR-0008 Demo 2 可解释 Admission（限定范围 Verified） | 四项固定演示任务的固定队列、路由解释与客户 A 仅本次模式选择；Adaptive Swarm 推荐/选择后保持 `execution_status=not_started` | 已实现 `WorkCockpitSnapshot(owner_id/backend/version/last_event_sequence/items)`、`RouteSelectionResult(cockpit_version/cockpit_last_event_sequence/item)` 与 WorkItem 路由事实；当前仅 memory | [`DEMO2-PR1-EXPLAINABLE-ADMISSION-EVIDENCE-20260817`](../evidence/DEMO2-PR1-EXPLAINABLE-ADMISSION-EVIDENCE-20260817.md)；聚焦 Python 6 passed、专用浏览器 5 passed、完整 Python 118 passed/1 skipped、完整浏览器 34 passed，Ruff/lint/build/diff-check 通过 | 只允许查看解释、接受推荐、选择其他允许模式或暂不选择；scope 为 `this_run`；不覆盖拖拽调序、长期偏好或执行 | 409 保留本地选择并 GET 对账；未知结果先 GET；memory 重启不恢复；预测标记 `fixture_policy_forecast` | 原始 Prompt、思维链、内部来源 ID、策略权重、Token、Permit、真实账单和未测量的节省/时延 |
