# DR-0005：用 Task Director 把长任务的编排、决策与恢复带到前台

| 字段 | 内容 |
| --- | --- |
| Decision ID | `DR-0005` |
| Owner | Office Agent 项目组 |
| Date | 2026-08-11 |
| Status | `Draft`（2026-08-11 可理解性验收重新打开；既有工程证据仍按原范围保留） |
| Scope | Demo 1 Tasks 主视图、跨工作区任务摘要、首次用途理解、来源标签、新一轮语义、单一下一步、决策后果、完成成果、失败恢复、工件历史与移动端主路径 |
| Depends on | `DR-0001`、`DR-0002`、`DR-0004`、现有 `TaskSnapshot` / Control / SSE 协议 |

## 1. 用户场景与问题

目标用户仍是准备客户 A 经营会材料的项目负责人或客户经理。任务启动后，用户需要快速判断当前阶段、三个交付分支各自进展、哪个分支被证据阻塞、现有工件能否提交，以及此刻自己必须做什么；发生断线、冲突解决或工件换版后，还要能确认当前看到的是不是最新服务端事实。

既有 Runtime 已经能显示这些事实，但长期任务明细被压缩在通用 Agent 对话旁的窄面板中。冲突证据和决定动作分居工作区与 Runtime，用户需要跨区域来回寻找；通用聊天记录又长期占据主要空间。工件 mutation 后若仍停留在旧版本，历史内容还可能与当前 Branch head 并列出现而缺少足够强的区分。

上一轮工程完成条件是：Tasks 默认进入第一类 Task Director 工作区；左侧用编排画布集中呈现阶段、分支、工件、验证、冲突和 Commit，右侧默认只放需要用户处理的 Decision Inbox，同时允许切回 Agent 对话；移动端阻塞摘要可到达决策区；用户主动查看旧版本时有明确历史标识，mutation 后默认跟随新的 Branch head。所有业务结论必须继续来自服务端 Snapshot，不能为匹配参考图伪造进度、恢复或执行结果。

2026-08-11 的实际试用反馈指出当前系统“还有很多问题”，且 Stakeholder “有点看不懂这个是要做什么”。随后针对运行页面的反馈又指出，`fixture:...` 来源标识“这些是什么意思”，并询问“再次演示”是不是把当前状态设回可启动状态。因此，上述工程完成条件不再等同于交互完成。本决策重新打开为 `Draft`，新增九个必须同时通过的完成门槛：

1. 首次理解：没有功能讲解时，用户能从首屏理解系统正在帮助准备客户 A 经营汇报、协调三项交付物，并只在需要决定时请人介入。
2. 单一下一步：空态一次点击创建并启动；Conflict 只保留一个改变状态的主要动作，定位、导航、刷新和审计入口降级；Committed 转入成果复核。
3. 决策后果：提交前说明冲突、来源、受影响分支、将改变的内容和不会发生的真实外部动作。
4. 完成成果：终态直接呈现三项交付物、验证结果和可复核下一步，不能只留下“没有待决策项”的空状态。
5. 失败恢复：重新对账、`409`、历史版本和等待状态都要说明发生了什么以及用户如何回到最新可操作事实。
6. 移动端主路径：`390 x 844` 视口中从任务摘要到主要决定、后果和恢复入口可达，无横向溢出或被次要信息遮挡。
7. 跨工作区职责：只有 Tasks 工作区显示冲突决定、分支控制和任务成果；邮件等其他工作区只显示后台任务摘要和前往 Tasks 的入口。
8. 来源可理解：固定 Demo 1 的已知来源显示为“演示数据 · 业务来源（版本）”，原始 `fixture:` ID 不进入普通业务 DOM；未知来源继续 fail closed。
9. 新一轮语义：终态入口统一为“开始新一轮汇报”，一次点击创建独立 Task 并启动，旧轮次不重置、不覆盖；在历史轮次选择入口实现前，不得把“已保留”解释为用户可在界面中任意切换旧轮次。

## 2. 来源与依据

| Source ID | 类型 | 支持的判断 | 局限 |
| --- | --- | --- | --- |
| `USER-FEEDBACK-20260811-INTERACTION-01` | Stakeholder 用户反馈与方向选择 | 前台设计与用户交互应成为一等推进目标；选择第二个 Task Director 方向 | 不是目标用户研究或效果证据 |
| `DESIGN-REFERENCE-TASK-DIRECTOR-OPTION2-20260811` | 选中视觉参考 | 支持编排画布、Decision Inbox、工作台密度和状态色的信息层级 | 不是运行截图；图中的时间、进度和动作不能直接视为产品事实 |
| `USER-FEEDBACK-20260810-01/02` | 治理要求与 0716-v2 会后反馈 | 每次推进必须同时说明前台影响、后端事实、场景与来源 | 不指定具体布局，也不证明该布局有效 |
| `FRONTEND-E2E-DEMO1-PR4-20260810`、`POSTGRES-BACKED-API-RESTART-DEMO1-PR5-20260811` | 既有运行证据 | 证明当前 TaskSnapshot 主路径、工件工作区和断线对账事实可供新前台复用 | 不验证本轮新布局、历史防误读或用户价值 |
| `TASK-DIRECTOR-INTERACTION-DEMO1-PR6-20260811` | 历史源码、自动化、浏览器与截图证据 | 证明 `a47cb28` 原 PR 6 基线的固定 Fixture 布局、既有控制、历史版本区分与被测响应式路径 | 不描述当前可理解性修订；不证明真实 Connector、通用后台 Loop 或用户价值 |
| `TASK-DIRECTOR-DESIGN-QA-20260811` | 参考图与历史实现视觉复审 | 绑定 `a47cb28` 的两轮比较关闭当时的历史混淆、移动阶段轨、裁切与原始协议词等 P1/P2 | 不描述当前可理解性修订；视觉通过不等于目标用户更快或更正确地决策 |
| `USER-FEEDBACK-20260811-USABILITY-02` | Stakeholder feedback | 当前原型的产品用途和主路径仍不清楚，触发本决策重新进入可理解性修订 | 不是用户研究，不能量化问题发生率或替代目标用户任务测试 |
| `USER-FEEDBACK-20260811-ROUND-AND-SOURCE-03` | Stakeholder feedback | 原始 Fixture 来源和“再次演示”动作语义不清；支持明确演示数据性质、跨工作区职责和创建独立新轮次的动作语义 | 不是用户研究；不证明修订后的标签或动作已被目标用户理解，历史轮次选择入口仍未实现 |
| `TASK-DIRECTOR-ROUND-AND-SOURCE-CLARITY-20260811` | 源码、浏览器自动化与截图证据 | 非 Tasks 摘要、来源标签/DOM 投影和独立新轮次 create+start 已由完整浏览器 E2E 与 Mail 截图覆盖 | 工程证据不证明目标用户理解；历史轮次选择、真实 Connector 和通用后台 Loop 未实现 |
| `TASK-DIRECTOR-USABILITY-AUDIT-DEMO1-PR6-20260811` | Draft 可理解性验收与工程代理证据 | 固定首次理解、单一下一步、决策后果、完成成果、恢复和移动端验收门槛；当前浏览器脚本与截图已验证可见信息和主路径 | 工程代理不证明真实用户理解；5 人无引导研究未完成 |

完整登记见 [`SOURCE_REGISTER.md`](SOURCE_REGISTER.md)。

## 3. 决策与取舍

1. Tasks 使用专用的 Task Director 组合，而不是把长期任务继续作为通用聊天旁的附属面板。它仍保持“工作区在左、Agent 在右”的产品结构，只是右侧默认呈现更紧迫的 Decision Inbox，并允许用户随时切换到 Agent 对话。
2. 左侧编排画布不是第二套任务状态机。标题、目标、版本、任务阶段、预算、分支、工件 head、验证、冲突和 Commit 全部由现有 `TaskSnapshot` 投影；阶段色、布局、图标和展开状态只是表达。
3. Decision Inbox 只提升已经存在的服务端动作。收入冲突的主动作继续提交 `resolve_evidence` 并选择契约内 CRM 正式来源；“准备补证指令”只把文字放入方向输入，真正提交后也仅显示 `steer=accepted`、等待后续循环应用。
4. 工件选择区分 `follow_head` 与 `pinned_history`。默认跟随 Branch head；用户主动选择非 head 版本时显示“正在查看历史版本”，并提供返回当前版本的动作。mutation 后不能让旧内容静默冒充当前版本。
5. 移动端采用纵向编排和可到达的决策路径，不把桌面泳道强行缩成不可读缩略图；页面本身不得产生横向溢出。
6. 本轮不新增后端协议、Task 状态、控制种类或真实 Connector，也不把同步/传输状态写成 Task 业务进度。
7. 首屏和每个主状态优先表达“正在做什么、卡在哪里、现在做什么、决定会改变什么、完成后得到什么”。`Task Director`、Snapshot version、Loop step、内部状态枚举和事件序号降级到审计层，不能承担产品用途说明。
8. 一个状态只设置一个业务主动作。Conflict 的主动作必须在提交前展示后果；Committed 的主动作必须指向服务端确认的交付成果，而不是继续强调已经为空的 Decision Inbox。
9. Task 决策控制只属于 Tasks 工作区。非 Tasks 工作区的右侧仅显示“后台任务”摘要、服务端确认的当前/上一轮状态和跳转按钮；跳转只改变客户端活动视图，不提交 Task Control。
10. 来源显示必须先说明数据性质。四个固定 Demo 1 来源投影为带“演示数据”前缀的业务标签；DOM key 使用与原值无关的序号，普通业务 DOM 不保留原始 `source_ref`。服务端 Snapshot 和 API 仍保留原始标识用于校验与审计。
11. 终态入口采用“开始新一轮汇报”，而不是“再次演示”。该动作依次调用 create 与 start：新的 round key 创建独立 Task，随后以新 Task 的服务端版本启动；上一轮 Snapshot、Artifact、Event 和 Commit 不被修改。当前没有历史轮次选择器，这是明确缺口。

未采用继续扩张原窄 Runtime，因为它会延续证据与动作分离、业务状态截断和聊天占据主空间的问题。未采用纯静态大屏，因为它无法处理控制、历史版本和断线恢复，也违反服务端事实门槛。未采用完整内部 Trace/Worker 会话作为主视图，因为这些信息会增加认知负担并暴露不应前台展示的实现细节。

## 4. 前台目标输出与交互（Draft）

| 区域 | 用户看见什么 | 用户可做什么 | 反馈与恢复 | 默认隐藏 |
| --- | --- | --- | --- | --- |
| 任务简报与主要下一步 | 客户 A 经营汇报、三项交付目标、当前业务状态、阻塞原因和一个主要下一步 | 空态一次点击创建并启动；已有 Ready Task 时开始准备；Conflict 时处理收入决定；Committed 时查看交付成果 | 初始列表未完成时只显示读取态，不允许重复创建；未同步时保留最后确认事实并显示重新对账；终态新建不覆盖旧 Task | Task ID、Snapshot version、Loop step、原始枚举、幂等键、DSN、网络重试日志 |
| 非 Tasks 工作区后台任务摘要 | 当前是否有进行中的经营汇报；终态时明确这是“上一轮汇报” | 只可打开 Tasks；断线时重新连接或立即对账 | 点击“打开任务 / 前往处理 / 查看任务 / 查看汇报”只切换到 Tasks，不执行冲突决定或分支控制 | 冲突卡、候选来源、分支控制、Task ID、预算和版本 |
| 任务进展 | 读取资料、拆分任务、生成材料、核对事实、准备完成五个用户语言阶段；每份材料的当前成果、核对/冲突和是否纳入结果 | 打开服务端确认的当前材料 | 没有 head/report/Commit 时明确显示等待，不补造完成比例 | Prompt、思维链、Worker 对话、完整 Trace JSON、预算与内部步数 |
| 待我决定 | 当前 open Conflict、正式/候选口径、来源、受影响交付物，以及“采用后会改变什么、不会执行什么” | 采用正式口径；查看受影响工件；次要位置提供补证、暂停或接管 | mutation 提交中冻结重复动作；只有新 Snapshot 才改变业务状态；Simulator 边界始终可见 | 原始检索日志、未知或敏感来源、权限哈希、未由协议支持的后果 |
| 完成成果 | 服务端确认的三项交付物、验证结果、Commit 摘要和可复核下一步 | 打开交付物并复核，不把空决策列表作为完成反馈 | 只在终态 Snapshot 和 `last_commit` 支持时出现；缺少任一事实则保持等待或部分完成 | 前端推断的完成比例、真实发送或外部写入暗示 |
| 开始新一轮汇报 | 这是另一轮独立任务，不是把当前 Task 重置为可启动状态 | 一次点击创建并启动新 Task | 新 Task 采用新 round key；同轮网络重试复用 key；旧轮次保留但当前没有历史轮次选择入口 | round key、旧 Task 的内部标识和“已可任意切换历史轮次”的暗示 |
| Agent 模式 | 既有 Conversation 历史、输入和 Action Gate | 切回通用对话并继续既有办公协作 | 切换不重建 Conversation；Action Gate 继续使用原确定性治理链 | CoT、Prompt、Permit token 和工具秘密 |
| 共享工件 | Branch head、版本、验证、内容、来源、lineage 与 Commit | 选择版本或返回当前 head | 历史版本显示强提醒；默认 mutation 后跟随新 head | 未在 kind allowlist 中的字段与非安全 source ref |
| 移动端 | 纵向事实摘要、材料状态和阻塞摘要 | 从“查看待确认项”跳到“待我决定” | 无横向页面溢出；控制仍服从同步和 pending 状态 | 桌面专用密度和装饰性连接信息 |

## 5. 后端事实映射

完整逐项映射见 [`UI_SERVER_FACT_MATRIX.md`](../contracts/UI_SERVER_FACT_MATRIX.md)。本轮没有新增 API；关键映射为：

- 标题、目标、版本、任务状态、阶段和预算来自 `TaskSnapshot.contract`、`version`、`status`、`phase` 与 `budget`。
- 分支泳道来自 `branches[]`；交付定义来自 `contract.deliverables[]`；最新工件来自 `branches[].artifact_heads` 与 `artifact_versions[]`；验证、冲突和提交分别来自 `verification_reports[]`、`conflicts[]` 与 `last_commit`。
- “等待你的决定”只在 `TaskSnapshot.status=waiting_input` 且存在 open Conflict 时出现；failed/cancelled 终态即使保留 open 记录也优先显示失败/取消事实。任务完成只在 `last_commit` 和终态 Snapshot 支持时出现。
- 已有任务的首屏业务用途来自 `contract.title/objective/deliverables`。尚无 Task 时，空态来自固定 `/v1/demo1/tasks` 创建模板的客户 A 场景副本，不是 Snapshot 事实；其文案由 E2E 与创建后的契约校验保持一致。通用产品仍需服务端模板/场景描述接口，不能长期依赖客户端副本。初始 Task 列表未返回时保持读取态，不能先显示可创建空态。
- 主要下一步是对服务端事实的有限表达：终态状态优先；仅 `waiting_input` 的 open `conflicts[]` 进入可操作决定；未启动状态使用契约允许的启动命令，终态且存在 `last_commit` 时进入成果复核；前端不得用计时器、动画进度或局部请求成功自行改变业务阶段。
- 决策后果必须由 open `ConflictRecord`、受影响 Branch/Artifact head 与既有 `resolve_evidence` 语义共同支持；协议未提供的外部影响不得写入确认文案。
- 完成成果只读取终态 `status`、`last_commit`、`artifact_heads` 和 `verification_reports[]`。缺少 Commit 或验证报告时不能用“已完成”掩盖部分完成。
- `taskSyncState`、`taskTransportState`、右侧模式、工作区模式和工件选择模式是客户端交互事实，不是 Task 业务字段。它们只能描述浏览器是否已对账、当前显示哪个视图以及用户是否固定查看历史版本。
- 非 Tasks 工作区的后台任务摘要仍读取同一 `TaskSnapshot.status/phase/contract` 和客户端同步状态；其“打开任务 / 前往处理 / 查看任务 / 查看汇报”只改变 `activeView`、Tasks 模式与右侧模式，不产生 Task API mutation 或 TaskEvent。
- 来源业务标签来自客户端固定 allowlist；服务端 `source_refs[]` 仍用于 `resolve_evidence` 校验和审计。普通业务 DOM 只接收投影后的标签及序号 key，不接收原始 `fixture:` 值；未知值显示“内部标识已隐藏”。
- “开始新一轮汇报”先以新 `Idempotency-Key` 调用 `POST /v1/demo1/tasks` 得到独立 `ready / contract` Snapshot，再调用该 Task 的 `POST /start`。前端只有在服务端 Snapshot 应用成功后推进显示；旧终态 Task 不参与这两个 mutation。固定路径通常直接进入 `waiting_input / verify`，不是停在“可启动 Demo”状态。
- 同一 Task 的 Snapshot 只在 `version` 不低于当前版本、`last_event_sequence` 不低于当前 Snapshot 与已观察 SSE sequence floor 时应用；否则保留较新事实并保持重新对账，不能被乱序旧 GET 回滚或伪标 `synced`。
- `resolve_evidence`、Pause、Resume、Take over、Return control 和 Steer 继续携带 `expected_task_version` 与幂等键。业务状态只在服务端返回新 Snapshot 后改变；`steer` 当前只产生 `CONTROL_ACCEPTED`。

## 6. 失败、等待与安全边界

- SSE 或 GET 不可用时保留最后确认 Snapshot，显示“正在重新对账”，禁用新 Task Control；不能把传输中断写成任务失败，也不能声称后台仍在运行。
- `409` 后读取最新 Snapshot并要求用户复核，不基于旧版本自动重放含义可能已变化的控制。
- open Conflict 未解决时只标记受影响 Branch，其他分支的状态继续以各自 Snapshot 为准。
- 用户查看历史版本时必须显示当前 head 版本与返回动作；历史 candidate 不能以布局、颜色或文案冒充已验证 head。
- 未知 Artifact 字段和非安全 `source_ref` 继续 fail closed。Task Director 不展示原始 Prompt、思维链、Worker 内部对话、密钥、JWT/Permit、底层日志或无决策价值的内部调度。
- `email.send` 等仍是 Simulator；Task Director 展示客户回复草稿或 Commit 不代表真实邮件、CRM、日历或 OA 写入。
- 多轮数据虽可由 `GET /v1/tasks` 返回，但当前前端没有历史轮次选择入口；默认恢复最近活动 Task，否则显示最近终态 Task。不能把后台保留误写成前台已具备轮次浏览能力。

## 7. 验证与当前状态

既有固定 Fixture 工程验收仍是有效的窄范围证据：全量浏览器 E2E `6 passed (34.5s)`、专用 Task Director 用例 `1 passed (21.6s)`、Python `58 passed, 1 skipped (3.46s)`，Ruff、前端 lint 和生产构建通过；Snapshot 乱序、历史版本和被测桌面/移动视口也有记录。它们证明脚本能找到控件、命令与服务端事实按预期衔接，不证明真实用户理解系统用途、找到正确下一步、预测决定后果或识别完成成果。

Stakeholder 的本轮试用反馈构成反例，说明不能再用上述工程通过率关闭交互决策。当前已完成一轮以业务任务为中心的修订：根路径默认进入经营汇报；空态一次点击完成创建与启动；初始列表加载中不暴露创建动作，无任务离线时左右区域使用同一恢复事实；快速重复开始由 in-flight guard 收敛；没有 `conflict_id` 的 resolve 只开放每分支第一条 open conflict，并按剩余冲突解释阶段后果；只有 `waiting_input` 投影可操作冲突，失败或取消终态优先；Committed 列出三项服务端确认成果。浏览器回归为 `12 passed (43.7s)`，Python 为 `58 passed, 1 skipped (2.24s)`，Ruff、前端 lint 与生产构建通过；四张当前截图及哈希已回填。它们只证明预设信息和路径存在且与服务端事实一致。至少 5 名接近目标角色参与者的无引导任务测试仍未运行，因此 `DR-0005` 保持 `Draft`，不得表述为用户已经理解或可用性问题已解决。完整边界见 [`DEMO1-PR6-USABILITY-COMPREHENSION-AUDIT-20260811.md`](../evidence/DEMO1-PR6-USABILITY-COMPREHENSION-AUDIT-20260811.md)。

在上述工程验收之后，`USER-FEEDBACK-20260811-ROUND-AND-SOURCE-03` 又暴露了来源与轮次动作的理解歧义。当前 living decision 已将非 Tasks 摘要、带“演示数据”的来源标签、原始 ID 不入 DOM，以及“开始新一轮汇报”创建并启动独立 Task 写成新门槛；历史 PR 6 evidence 未被反写。后续工程证据单独记录在 [`DEMO1-ROUND-AND-SOURCE-CLARITY-EVIDENCE-20260811.md`](../evidence/DEMO1-ROUND-AND-SOURCE-CLARITY-EVIDENCE-20260811.md)：完整浏览器 E2E 为 `12 passed (44.5s)`，Mail 摘要截图为 `1440 x 900`。它们只证明投影与调用语义，不证明用户已经理解；`DR-0005` 继续保持 `Draft`。

## 8. 关联项

- 场景：[`SCENARIO-001`](../scenarios/SCENARIO-001-customer-a-durable-report.md)
- 事实矩阵：[`UI_SERVER_FACT_MATRIX.md`](../contracts/UI_SERVER_FACT_MATRIX.md)
- 方向选择反馈原文：[`USER-FEEDBACK-20260811-03`](../sources/USER-FEEDBACK-20260811-03-task-director.md)
- 可理解性问题反馈原文：[`USER-FEEDBACK-20260811-04`](../sources/USER-FEEDBACK-20260811-04-usability-comprehension.md)
- 来源与新一轮问题反馈原文：[`USER-FEEDBACK-20260811-05`](../sources/USER-FEEDBACK-20260811-05-source-labels-and-new-round.md)
- 来源与新一轮修订证据：[`DEMO1-ROUND-AND-SOURCE-CLARITY-EVIDENCE-20260811.md`](../evidence/DEMO1-ROUND-AND-SOURCE-CLARITY-EVIDENCE-20260811.md)
- 选中参考图：[`dr-0005-task-director-option2-reference.png`](../evidence/assets/dr-0005-task-director-option2-reference.png)
- 运行与视觉证据：[`DEMO1-PR6-TASK-DIRECTOR-INTERACTION-EVIDENCE.md`](../evidence/DEMO1-PR6-TASK-DIRECTOR-INTERACTION-EVIDENCE.md)
- Draft 任务验收：[`DEMO1-PR6-USABILITY-COMPREHENSION-AUDIT-20260811.md`](../evidence/DEMO1-PR6-USABILITY-COMPREHENSION-AUDIT-20260811.md)
- Design QA：[`design-qa.md`](../../design-qa.md)
