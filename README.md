# Office Agent V0.2

本次系统源码同步的包含范围、运行入口与验证限制见 [2026-10-26 同步记录](docs/evidence/SYSTEM-SOURCE-SYNC-20261026.md)。截图、录屏、PPT 和渲染报告属于本地交付材料，本次不随源码上传；历史文档中的这些链接在仅克隆源码时可能不可用。

## 2026-10-26 Demo3 十二个预设边界案例

在原 Demo3 的新事项表单展开“演示案例”，可选择十二个办公场景，覆盖自动整理、撤销、草稿修订、缺信息、确认、重核、受限拒绝、材料判断和暂缓找回。选择仅填入可编辑材料，不提交或批准。全部沿用固定规则 API，不调用模型或执行外部动作。见 [案例讲解清单](docs/reports/demo3-examples-20261026/index.html)、[DR-0098](docs/decisions/DR-0098-demo3-ready-boundary-examples.md) 与 [验证](docs/evidence/DR-0098-DEMO3-EXAMPLES-20261026.md)。

## 2026-10-26 主 Agent 优先与按需方法

任务拆分不再直接等于 Agent 人数：真实 Planner 单独提出自行处理或委派建议，服务端保留准入权。三个固定处理方法按需加载；原工作台显示一个主 Agent 处理多个工作项。原入职交接指令实跑保留两项结果，由双执行改为一次主分析。多工作项主路径的处理后扩编仍待接通。见 [DR-0097](docs/decisions/DR-0097-primary-agent-and-bounded-skills.md)、[Evidence](docs/evidence/DR-0097-PRIMARY-DESIGN-20261026.md) 与 [设计对齐页](docs/reports/primary-design-alignment-20261026/index.html)。

## 2026-10-26 单 Agent 后按结果追加核对

Demo2 的合格单工作项也进入真实执行台账，并在结果返回后判断是否需要补核；不用先开多人团队。只有服务端批准新增工作才更新协作方式，保留原贡献和旧版本。不引入新框架依赖。150项后端、16项浏览器/投影检查通过；3项真实待办共10次调用均未追加，真实模型扩编仍未验证。见 [DR-0096](docs/decisions/DR-0096-single-agent-result-driven-delegation.md) 与 [Evidence](docs/evidence/DR-0096-SINGLE-AGENT-DELEGATION-20261026.md)。

## 2026-10-26 三个工作区统一与分层展示

Demo2 总览先看任务、状态和一条结果，指令、统计与其他结果按需展开；错误和未完成项不隐藏。Demo3 对齐原工作台的表单、状态条和来源对照，保留全部人工确认与风险控制。修复隐藏依据区域在总览底部出现的问题。23 项定向浏览器回归及类型检查通过；新版实跑截图按主区真实状态验收。见 [DR-0095](docs/decisions/DR-0095-unified-demo-information-hierarchy.md) 与 [Evidence](docs/evidence/DR-0095-UNIFIED-DEMO-POLISH-20261026.md)。

## 2026-10-25 当前入口与实跑示例

3000 入口的旧后台已存档并更新。Demo1 的六个示例统一收在折叠区；Demo2 默认三项待办缩小到明确的人员、招聘要求和账目记录。实跑 17 次、46 次调用，推荐 7 个有来源的案例；缺材料与待判断仍保留。不是所有 completed 结果都入选。入口预检：`node scripts/demo-service-preflight.cjs http://localhost:8000`。见 [DR-0094](docs/decisions/DR-0094-live-demo-readiness.md) 与 [实跑证据](docs/evidence/DR-0094-DEMO-READINESS-20261025.md)。

## 2026-10-25 Blurt 录屏反馈改版

按确认后的 12 项清单精简输入、依据核对与协作展示。普通引用一次进入原文，空人工栏不再出现；同任务分支保持可切换，Agent 分行显示真实状态。续办公开目标不再投影内部背景 JSON。实际预算和人工权限不变。
处理步骤当前是执行流程展示；建议独立理由仍缺失，不把这些写成新模型能力。见 [DR-0093](docs/decisions/DR-0093-blurt-focused-workbench.md) 与 [验证及未完成项](docs/evidence/DR-0093-BLURT-WORKBENCH-20261025.md)。

## 2026-10-25 手机对齐手册

[36 页图文 PDF](output/pdf/office-agent-system-guide-20261025.pdf) 按当前代码与真实运行解释三个 Demo、证据捕获、人机交接和有限自适应协作。首次名词释义、实际案例、流程图与未实现边界均保留。见[阅读导览](docs/reports/system-alignment-20261025/index.html)和[来源与验证](docs/reports/system-alignment-20261025/README.md)。本次仅制作文档与只读截图，不构成新一轮模型能力评测。

## 2026-10-25 新版实跑演示页

[八个案例的截图演示](docs/showcase/office-agent-20261024/index.html)已用当前系统重跑，旧版保留。Demo1/2 是真实模型运行，Demo3 是不调用模型的固定规则事项。31 步展示使用 30 张不同的 1920x1200 截图；两种 Demo2 视角共用一批真实任务，不重复计数。结果、未完成部分与验证范围见 [DR-0092](docs/decisions/DR-0092-live-showcase-refresh.md) 和 [Evidence](docs/evidence/DR-0092-LIVE-SHOWCASE-20261025.md)。

## 2026-10-24 Demo2 按结果调整的有限实现

默认待办只写办公目标，不再规定 Agent 数量与分工。自动只读协作新增按结果评估：模型可提出追加工作，服务端核对来源、前序、预算后再派发。每批仍最多3个，累计工作项不等于同时运行人数。界面显示初始分工原因与实际调整，节点结果按需展开。
18次真实任务启动、61次模型调用出现单 Agent、两人和三人安排；10次协调判断均未新增工作。动态追加链路仅有受控测试证据，不能声称真实模型扩编已验收。具体问题、测试与限制见 [DR-0091](docs/decisions/DR-0091-result-driven-bounded-adaptation.md) / [Evidence](docs/evidence/DR-0091-ADAPTIVE-PROGRESS-20261024.md)。下方五人示例是旧版预设分工的历史证据，不是本轮自主扩编结果。

## 2026-10-24 Demo2 五个执行 Agent 与两阶段交接

新增默认示例“跨部门简报 · 分阶段协作”。真实跑通两次：先3个 Agent 独立分析，再2个 Agent 接续核对和汇总；同组两个简单待办仍为单 Agent 路径。任务图按依赖分层，较多节点的结果按需展开。
这是5个执行 Agent、每波最多3个，不是5个同时运行，也未修改调度策略。六个任务共20次真实调用，见 [DR-0090](docs/decisions/DR-0090-multistage-worker-display.md) / [Evidence](docs/evidence/DR-0090-FIVE-WORKERS-20261024.md)。
[分工图与真实截图](docs/reports/swarm-stages-20261024/index.html)。


## 2026-10-24 Demo2 办公待办与结果摘要

两组共六个只读办公示例已各实跑两次，覆盖单 Agent、同类资料顺序处理、跨来源双 Agent 协作。待办启动后先看任务、实际执行与分析结果，指令和回执按需展开；详情可返回同一组待办。
这是前台投影改进，不增加模型难度评分或新调度器。26次真实模型调用及边界见 [DR-0089](docs/decisions/DR-0089-office-todo-outcomes-and-routing.md) / [Evidence](docs/evidence/DR-0089-OFFICE-TODOS-20261024.md)。
[六个案例与真实页面截图](docs/reports/office-todos-20261024/index.html)。

## 2026-10-24 人机分工与三组真实案例

原任务页新增“这次怎么分工”：系统已处理的分析、需要人的判断或材料、Agent 自身尚未完成的工作分开显示，不用虚构置信度百分比。
“更多人机分工示例”提供明确入职例外、往来账缺银行回单、申请改变权限例外三组任务。已实跑三组并完成一次同任务的人类选择后续办。
任务列表不会再把仍有待决或缺源的分析统一标为已完成；Demo2 自动只读策略不变。范围和误分类修正见 [DR-0088](docs/decisions/DR-0088-evidence-based-human-agent-division.md) / [Evidence](docs/evidence/DR-0088-TASK-RESPONSIBILITY-20261024.md)。
[图文说明与真实页面](docs/reports/task-responsibility-20261024/index.html) 包含三组案例、一次同任务交接及尚未实现的边界。

## 2026-10-24 同任务分支与普通办公案例

Demo1 的后续建议改为同一 Task 内续办，保留原目标、原记录与成果，使用“初始处理 / 后续分支”切换。
开始前展示预期文件与交付目标，首轮展示真实计划及已送入分析的资料；例子改为 Excel 往来账、入职清单、Word 招聘要求。
执行后的建议经原 `/continue` 创建新的有界 Run，不另建业务 Task；历史只读，当前终态才能续办，不支持任意历史节点并行分叉。
见 [DR-0087](docs/decisions/DR-0087-task-branches-and-first-round-brief.md) 与 [实测与限制](docs/evidence/DR-0087-TASK-JOURNEY-20261024.md)。下文“后续建议新建独立任务”为历史合同，已由本条替代。

## 2026-10-24 真实待办执行与证据补齐

Demo2 现可一次提交三个可编辑的只读待办，每项分别调用原 `/runs` API，并按服务端判断走单 Agent 或自动只读协作。
新增通用 `automatic_readonly` 启动策略，非前端自动确认；旧手动策略仍是 API 默认值。没有新增持久 Batch、优先级队列或分布式调度。
Demo1 暂停后仍展示已保留成果中的原文，明确未完成原因；Worker 核对来源计数已对齐 Branch。
本次真实模型试用地址为 `http://localhost:3010/`，原3000预览未停；3010使用独立 memory 会话，重启不保留在线历史。
见 [DR-0086](docs/decisions/DR-0086-automatic-readonly-todos-and-visible-evidence.md) 和 [本轮实测](docs/evidence/DR-0086-LIVE-DEMO12-20261024.md)。本条更新下文10月23日“多待办尚未接入”的历史范围。

## 2026-10-23 统一界面第一阶段

原 `/` 已改为参考图的三栏工作台：三个 Demo 入口共用任务、依据、成果视图；新增原文引用总览和真实工作包状态图。
这次只替换前台组织方式，仍使用共享只读资料库和原 Task/Run。Demo2 多任务自动调度、资料导入、Demo3 独立目录尚未实现。
`/agent-capabilities` 保留完整记录。旧版工作树已存档，边界及测试见 [DR-0085](docs/decisions/DR-0085-unified-reference-workbench.md) 和 [Evidence](docs/evidence/DR-0085-UNIFIED-UI-20261023.md)。
本条替代下文历史版本中“没有 Demo 前台选择”的展示描述，但不改变 Runtime 或授权合同。

## 2026-10-23 能力演示页

[八个案例与 27 张原系统截图](docs/showcase/office-agent-20261023/index.html)：按任务推进、只读协作、人机共驾切换，离线浏览，不替换原工作台、不自动启动任务。
Demo1/2 为受控回执截图，Demo3 为实际固定规则 API；来源与边界逐案标注。
截图走查同时修正有通过检查却被称为“仅失败回执”的成果兜底提示，见 [DR-0084](docs/decisions/DR-0084-screenshot-capability-showcase.md) 与 [Evidence](docs/evidence/DR-0084-SHOWCASE-20261023.md)。

## 2026-10-22 用户视角走查

[DR-0083](docs/decisions/DR-0083-user-walkthrough-and-consistent-results.md) 修复根页已保留草稿却显示空白的矛盾；协作弹窗先展示确认与工作状态，再展开台账和来源。
等待时可选调整折叠，文件筛选收为下拉；Loop/Swarm 与原入口保留。
这是助手走查与受控回归，不是用户研究或新模型能力，见 [Evidence](docs/evidence/DR-0083-USER-WALKTHROUGH-20261022.md)。

## 2026-10-22 等待说明与协作图减法

[DR-0082](docs/decisions/DR-0082-concise-waiting-and-collaboration.md) 合并等待区重复说明，逐项保留问题和操作，资料/原因按需展开。
协作图改用短状态文案，合并下游等待说明但保留全部名称；批准范围与预算不隐藏。
原系统入口与后端协议不变，验证范围见 [Evidence](docs/evidence/DR-0082-WAITING-COPY-20261022.md)。

## 2026-10-22 原任务页结构整理

[DR-0081](docs/decisions/DR-0081-delivery-first-root-overview.md) 将真实成果提前，发布复核结论与文件并列；
未完成工作不截断，普通成功执行记录按需展开。原 Loop/Swarm、完整成果和错误控制保留。
当前验证见 [Evidence](docs/evidence/DR-0081-TASK-OVERVIEW-20261022.md)，不代表用户效果研究。

## 2026-10-22 参考图对照与前端减法

[DR-0080](docs/decisions/DR-0080-reference-led-information-hierarchy.md) 对照早期 Image 2 图：根页省略全已完成分支的重复清单，能力页合并文件成果入口，协作图优先于详细统计。
待办、业务拒绝、原控制与完整记录保留；无 Runtime/API 变化。范围与验证见[本轮 Evidence](docs/evidence/DR-0080-REFERENCE-UI-20261022.md)。

## 2026-10-20 原则继续落地

[DR-0079](docs/decisions/DR-0079-revocable-preferences-and-draft-recovery.md) 在原事项工作台补个人文本整理偏好及撤回、旧摘录预览后保存为新版本、最近待处理筛选。
偏好不代替确认，历史和原文不覆盖，最近列表仍只覆盖二十个 Run。验证范围见对应 Evidence，不代表全部原则已实现。

## 2026-10-19 原则实践与评审交付

[设计文档与三案视频](docs/deliverables/copilot-20261019/index.html)整理原型、场景流程、交互图、技术路径、亮点与体验指标。
DR-0078 补强原事项页的已保存交接说明，不新增 Runtime 或审批能力。视频分别标明历史实跑、受控协作及真实固定规则 API；十六条原则的未实现项仍明确保留。

## 2026-10-10 人机共驾案例审查

先存档现有源码与未提交成果，再从队友 C02/C08/C11 回看原工作台：草稿与来源就近对照、
内容变化时显式重核、人工判断不冒充自动续办。没有新增 Runtime 或独立产品入口。
[三个案例图文解读](docs/reports/copilot-cases-20261010/index.html)区分研究依据、原能力和本轮调整；
[DR-0077](docs/decisions/DR-0077-case-based-copilot-review.md)与对应 Evidence 记录验证边界。

## 2026-10-10 Demo1 界面继续减法

根任务区收起普通执行方式，终态不再展示不可用的 pause / stop / steer 控件，单轮省略切换条。
通过文件的长说明按需展开；失败、自测卡、业务否决与可用控制保留。能力页完整记录不变。
汇报补充证据捕获链与真实两波协作，见 [DR-0076](docs/decisions/DR-0076-calm-demo1-and-evidence-explanation.md) 与对应 Evidence。

## 2026-10-10 Demo1 交付表达

当前成果优先显示真实文件及文件检查结果，不再把逻辑版本空态写成没有产出；历史轮次与当前处理分开，
预览文件名不再出现在执行/成果视图冒充任务输入。保留原入口与 Loop/Swarm。
见 [DR-0075](docs/decisions/DR-0075-demo1-task-and-delivery-clarity.md) 和 [Evidence](docs/evidence/DR-0075-DEMO1-CLARITY-20261010.md)。

## 2026-10-08 工作区信息分层

续增：[执行记录分层](docs/decisions/DR-0074-execution-detail-disclosure.md)将普通历史、本轮材料、
已完成分支与版本列表按需展开；未完成分支、续办/来源变化与错误不折叠。验证见对应 Evidence。

原工作台的过程记录按需打开；资料目录可收起并保留筛选；已提交研究任务的输入与预算进入
“任务要求与运行设置”，当前目标、问题和成果仍在主区。原 Loop/Swarm 与事项能力不变。
见 [DR-0073](docs/decisions/DR-0073-focused-workspace-disclosure.md) 与[本轮验证](docs/evidence/DR-0073-FOCUSED-WORKSPACE-20261008.md)。

## 2026-10-07 统一工作台整合

本轮合并远程 Demo3 与本地 Demo1/2 优化，目标是一个办公工作台内的不同任务视图，
不是三套系统。原资料库、Agent Control Loop、Adaptive Swarm 和六类固定单步事项均保留。
入口共用与迟到响应隔离的合同见 [DR-0072](docs/decisions/DR-0072-unified-workbench-and-response-ownership.md)，
当前验证状态见 [Evidence](docs/evidence/DR-0072-INTEGRATION-20261007.md)。该合同为 Limited Verified，
仅限统一入口、已测试的迟到响应隔离与兼容共存；最终单次浏览器 149 项通过，后端 573 项通过、
26 个 PG 条件跳过，末次类型检查与 webpack 构建通过。Worker 歧义人工确认到下游恢复仍是后续独立纵切。
Demo3 文档为避免与本地编号冲突迁为 DR-0070/0071、SCENARIO-057/058，历史证据不重写。

## 单步事项与 Demo3（2026-09-19）

Demo3 已与主分支的 Task 台账、只读 Worker 和新版能力页代码合并，验证进度及编号迁移见[合并记录](docs/evidence/DEMO3-MASTER-MERGE-20260919.md)。单步事项仍不调用模型或真实业务系统。

2026-09-23 修复 PostgreSQL 测试清理遗漏，并将三组数据库测试及清理回归纳入同一 CI，见[失败与修复记录](docs/evidence/POSTGRES-TEST-ISOLATION-20260923.md)。Runtime 的 Task/Run 完整性检查保持不变。

统一工作台增加“办理事项”：个人文本整理与撤销、资料逐字摘录、测试协作任务、
测试发件强确认、受限请求及材料对照人工判断。摘录支持原位编辑，暂缓事项可从最近记录找回。
此路径使用固定服务端规则和真实版本/幂等回执，不调用
模型，也不连接真实办公系统；既有资料研究与 Artifact 能力保持原有范围。
下文 Planner/Analyst、成果验证等说明适用于资料研究路径，不适用于这六类事项记录。

[对外提交版：设计指导手册](docs/design/submission/人机共驾设计指导手册_v1.0.md)、[边界情形与接管案例库](docs/design/submission/边界情形与接管案例库_v1.0.md)、[Demo3 设计方案与评审材料](docs/design/submission/Demo3设计方案与评审材料_v1.0.md)已纳入仓库，与下述内部开发版分开维护。

[开发版指导手册与设计评审](docs/design/DEMO3-DEVELOPMENT-HANDBOOK-20260918.md)
对应提交版 R01-R16 与 C00-C12，并列明未覆盖项。
[DR-0070](docs/decisions/DR-0070-single-action-boundary-workbench.md) 与
[运行证据](docs/evidence/DR-0053-SINGLE-ACTION-EVIDENCE-20260918.md)记录实现边界。
当前公开 API 为 12 个 path、13 个 operation，增加 `/action-controls`。
[DR-0071](docs/decisions/DR-0071-demo3-editable-drafts-and-human-judgment.md)与[本轮证据](docs/evidence/DR-0054-DEMO3-COLLABORATION-EVIDENCE-20260919.md)记录草稿版本、材料判断、最近事项与交接说明。
## 2026-09-22 只读来源核对

[DR-0069](docs/decisions/DR-0069-readonly-source-counts-and-reviewable-coverage.md) 在原 Loop/Worker
路径拦截固定产品资料中的受支持计数冲突，不生成文件或假验证绿灯。XLSX 首个可见表最多 240 行，
模型文本最多 30000 字符，总正文仍受 120000 字节约束；覆盖回执不等于完整理解。
[本轮报告](docs/reports/demo12-source-checks-20260922/README.md) 保留两次真实任务仍待核对的事实，
没有新增页面，也没有宣称真实下游交接或通用语义验证已完成。

## 2026-09-22 成果分层与任务验收

成果页先看结论，普通依据按需展开，所有待决仍默认可见；“分析记录已保存”不冒充结论正确。
财务文件长口径收起，期间、用途、下载与复核边界保留。原入口和 Loop/Swarm 不变。
两次真实任务共 8 次模型调用：财务三份文件独立复算通过；跨领域协作仍等待，且已采用分析
出现 P0/提测数量错误，结论验收未通过。局部续办另用受控 Runtime 验证，不冒充真实模型恢复。
见 [本轮结果、截图和自测](docs/reports/demo12-outcomes-20260922/README.md)、
[DR-0068](docs/decisions/DR-0068-result-reading-and-independent-task-acceptance.md)。

## 2026-09-22 前端减法与用户流程走查

原入口与 Loop/Swarm 不变。进展页合并重复的分支/成果，工作项摘要和来源按需展开；成果与
版本历史直接进入专注内容区，返回保留原页面状态。协作先看分工图，交接与核对意见进入既有
回执详情；冲突、业务否决和不完整待决仍默认可见。
见 [走查与可操作用例](docs/reports/demo12-simple-20260922/README.md) 和
[DR-0067](docs/decisions/DR-0067-task-first-progressive-disclosure.md)。这是前端工程改进，不是真人效果研究。

## 2026-09-22 论文驱动的局部修复与交接核对

原任务输入增加显式输出约定；新 Run 的只读 Worker 增加按真实依赖分工、逐项前序核对与最多
一次目标修复。歧义/分歧不会自动改成支持，已有成果保留。原进展页增加交付清单与待办优先，
原协作页显示模型核对意见，Control Loop/Adaptive Swarm 与入口不变。
见 [8 篇正式论文及迁移限制](docs/research/HUMAN-AGENT-TOP-VENUE-TO-DEMO12-20260922.md)、
[本轮验收](docs/reports/demo12-research-20260922/README.md)、
[DR-0066](docs/decisions/DR-0066-reviewed-handoffs-and-output-agreement.md)。
这是限定工程实现，不是论文算法复现、独立真值验证或人类业务裁决闭环；Demo3 接入约定不变。

## 2026-09-21 输出约束与前序成果传递

继续改原系统，不更换入口。明确“只在页面展示 / 不生成文件”的新任务会在写入前拦截固定文件
生成器；协作页新增真实的前序成果传递记录。下游 Worker 收到直接前序已采用摘要、版本及来源，
但仍须回到批准原文核对引用。旧成果和任务记录保留，Demo3 接入约定不在本轮范围。
见 [本轮实测与可操作用例](docs/reports/demo12-handoff-20260921/README.md)、
[DR-0065](docs/decisions/DR-0065-output-policy-and-scoped-dependency-handoffs.md)。

## 2026-09-20 Demo1/2 可靠性

沿用原入口与 UI，本轮聚焦成果/模型说明对账、资料输入范围、局部续办与真实只读 Worker 验证。
见 [可操作用例与真实运行记录](docs/reports/demo12-reliability-20260920/README.md)、
[DR-0064](docs/decisions/DR-0064-demo12-reliability-and-bounded-narratives.md)。
新对账只覆盖入职、财务、上线的受限指标；自由说明保留为待复核草稿。模型资料范围披露不等于
全文续读完成。失败样本、真实 Provider 与确定性测试分别记账，本轮不处理 Demo3 接入约定。

## 正式入口与本轮方向

继续在原系统上优化，不另建产品。办公资料库入口仍为 `/`，Agent Control Loop 与 Adaptive Swarm 入口仍为 `/agent-capabilities`；两处共用 `HarnessWorkbench` 和既有 Task/Run/Snapshot。默认本地地址分别为 `http://localhost:3000/` 与 `http://localhost:3000/agent-capabilities`，须先启动服务。

**Demo3 沿用上述工作台，保留 Loop 与蜂群协作底座。** 远程已实现六类固定规则单步事项与版本化回执，本轮合入本地优化并收敛入口。它们不调用模型、不执行外部业务动作，也尚未成为 Worker 歧义恢复流程。`docs/reports/` 中的早期 HTML 仍是辅助研究/评审材料，部分包含离线模拟，不是替代系统或本轮集成证据。

[最新会议简稿：三个 Demo、八个边界案例与蜂群差异](docs/reports/DEMO123-BOUNDARIES-AND-SWARM-BRIEF-20260912.md) 取代只报论文数量的口径。原能力页已增加既有边界解释和协作调用/采用事实，ready 工作包不再写成已执行，原 Loop/Swarm 底座保留。见 [DR-0063](docs/decisions/DR-0063-integrated-copilot-boundaries-and-swarm-facts.md) 与 [本轮 Evidence](docs/evidence/DR-0063-INTEGRATED-BOUNDARIES-AND-SWARM-FACTS-20260912.md)。这不是通用权限引擎或 Demo3 全场景闭环完成；长文覆盖、业务批准和外部执行仍未实现。不新增 HTML 演示或 PPT。

## 2026-09-11 UI 重设计

`/agent-capabilities` 依用户参考图重构为任务进展、按轮执行记录、协作方式和专注证据核对。
仍共用同一 Task / Run / Snapshot 与既有 API；无默认候选、历史只读、来源过期、终态续办和
失败回执边界见 [DR-0061](docs/decisions/DR-0061-reference-aligned-capabilities-and-evidence-choice.md)。
[HTML 评审报告](docs/reports/demo12-redesign-20260911/index.html) 提供参考对照与实际截图；
[人机共驾交互沙盘](docs/reports/human-agent-copilot-20260911/index.html) 与
[会议简报](docs/reports/human-agent-copilot-20260911/report.html) 是独立 `Draft` 设计包，不是
已实现的 Demo 3 Runtime。[本轮 Evidence](docs/evidence/DR-0061-REFERENCE-ALIGNED-CAPABILITIES-EVIDENCE-20260911.md)
单列真实测试与未验证范围。

[主动实测与验收报告](docs/reports/demo12-acceptance-20260911/index.html) 和
[5 条可操作用例](docs/testing/DEMO12-ACCEPTANCE-CASES-20260911.md) 记录了随后发现的两个 UI 问题与修复。
全量浏览器回归 91 项通过，但真实日志任务的内容完整性未通过：模型单文件输入被截断，摘要未清楚限定范围。
此开放问题不能被测试数量、可定位引用或已采用状态掩盖。

[第二轮视觉与交互打磨](docs/reports/demo12-polish-20260911/index.html) 增加长目标全文展开、
完整任务书写区、自适应分支宽度与始终可见的证据确认区，附可操作验收用例。
[人机共驾研究资料库](docs/reports/copilot-research-library-20260911/index.html) 收集经核验的论文、
官方文档与博客，并区分研究发现、工程合同和产品设计假设；它不是已实现的通用接管策略。

[动态边界设计实验](docs/reports/copilot-boundary-design-20260911/index.html) 进一步脱离预设等级，
以具体授权范围、内容澄清、版本失效、未知回执和主动接管组成 8 类离线情境，并保留最新研究反证。
此方案仍为 [DR-0062 Draft](docs/decisions/DR-0062-dynamic-boundary-design-experiment.md)，不修改当前 Runtime 或真实动作权限。

[2026-09-12 用户理解与测试迭代](docs/reports/copilot-boundary-design-20260911/usability-review-20260912.md)
继续完善同一原型：明确“确认不等于发送”、查询失败保留未知、当前/历史草稿与具体数据条件，
并增加五个非诱导理解任务。源码和自动化结果与尚未开展的目标用户测试、尚未完成的最终浏览器门分开记录。

[2026-09-12 共驾调研推荐](docs/reports/copilot-boundary-design-20260911/research/followup-20260912/recommendations.md)
增补 6 篇论文与 3 篇官方实践，重点为共同计划、参与的反效果、检查时机与局部纠错；同一 HTML 的“研究与方案”页提供筛选及证据限制。属于定向设计依据，不表示新能力或用户效果已验证。

Office Agent is one FORTE-backed office folder, not a gallery of registered
Demo scenarios. A user can browse the entire public office repository like a
file manager, inspect bounded safe previews and submit only a goal. The Agent
then searches the whole safe index, explains which evidence it selected, runs a
server-backed Agent Control Loop and proposes source-bound next tasks that start
only after human confirmation.

The current product is deliberately narrow. `completed` means the Planner
candidate passed server policy/structure checks and the Analyst response passed
schema, selected-reference, server-resolved evidence-location and read-only
boundary checks. Separately, 12 fixed local office capabilities can now produce
real isolated run-workspace files with deterministic verifier receipts. Neither
fact means an arbitrary answer is correct, a FORTE source was changed or an
external business action happened.

## Current product

The root page is the daily Workspace entry:

- left: one searchable, collapsible folder tree containing all 96 public FORTE
  input files, with file-type filters and no role or Demo partition;
- center: file metadata, CSV/XLSX/PDF/DOCX/TXT/code preview, a free-form task
  composer, loop budget, round history, server-owned task branches, evidence
  gaps, controls, append-only result history, real run-workspace Artifact
  downloads and verifier receipts, a cited read-only brief and up to four
  proposed next tasks;
- right: current phase, ordered server events and separate Planner/Analyst
  adoption receipts;
- boundary: the Run freezes the complete allowlisted index; each round exposes
  only the Agent-selected, server-budgeted files to analysis. Originals stay
  read-only, results require review and no external action occurs.

The root links to `/agent-capabilities`, an inspection route that projects Agent
Control Loop and Adaptive Swarm facts from the same selected Snapshot. It defaults
to a concise execution-progress view; complete Loop records and the collaboration
view are disclosed only when requested. The collaboration view uses the actual
service-selected route and a compact admission/work-package/contribution/artifact
projection, while sources and execution receipts remain collapsed. It is not a
Demo selector, another Runtime or the future Demo 2 smart work cockpit.

Both the Workspace and Agent capabilities route expose **New task**. The action
first opens a clean client draft, closes the selected Run stream and leaves the
previous server Task/Run untouched. It does not create an empty Task or spend
model budget. A new independent Task exists only after the user submits an
instruction through the existing Run-start contract; recent task conversations
remain available for return.

The default complete-task budget is 12 rounds, 16 files per round, 30 model
calls and 7,200 Agent-active seconds. Public maxima are 24/24/60/14,400. Human
review in `waiting_input` and an explicit pause do not consume active time. The
four caps remain independent.

The primary flow is:

```text
browse or search the whole repository
  -> inspect safe file preview
  -> explicitly open a new-task draft without stopping or deleting prior work
  -> author an original task
  -> freeze a whole-workspace AgentControlLoopContract and budget
  -> explicitly numbered business requirements are accounted for as current, deferred or uncovered
  -> deepseek-v4-pro Planner selects a minimal evidence set and explains why
  -> server compiles and validates scope, tools, dependencies and effects
  -> an admitted deterministic office tool may write a real isolated Artifact
  -> server verifies fields/numbers/order/rules/tests and records an EffectReceipt
  -> deepseek-v4-pro Analyst reads the approved safe projections
  -> Analyst separates fact, impact and human decision options, then returns exact quote candidates
  -> server uniquely resolves safe-preview locations and keeps only reviewable findings
  -> server validates citation membership, evidence anchors and the Evidence Gate
  -> location/structure cannot be adopted: one bounded repair, then preserve valid work and pause one branch
  -> retry-only gap shows one recommended Branch action; optional clues and audit details stay collapsed
  -> ambiguous quote requires the user to choose one real source position before Branch recovery
  -> evidence missing: pause the affected task branches before spending another round
  -> user chooses one branch: next round is bound to that branch's missing sources
  -> ordered SSE + authoritative Snapshot
  -> one append-only logical evidence-brief ArtifactVersion per completed round
  -> separate TaskCommit selects the current version + proposed next tasks
  -> user may restore an older brief by creating another TaskCommit; history remains
  -> terminal Run with an unfinished Branch may create a same-Task child Run that rechecks only approved refs
  -> human confirms one proposal -> independent new Control Loop
```

Model receipts distinguish `未调用`, `已采用` and `未采用`. A returned model
response that fails server validation is not presented as success. A rejected
plan may be repaired once within the same model-call budget, and both the
rejection and retry remain visible in the ordered trace. Analyst calls use an
independent 180-second timeout and a strict compact JSON draft; truncation,
invalid JSON/schema, Provider failure, Branch binding and source-location
failure remain distinct facts. One bounded repair may preserve an adoptable
subset, otherwise only the affected Branch pauses with an explicit recovery
kind. Ordinary UI
hides Prompt, chain-of-thought, raw provider response, absolute path, digest,
benchmark task/rubric/solution and internal effect/gate identifiers.

## General Agent, three acceptance lenses

Demo names do not unlock capability or select private code paths:

- Demo 1 tests a decomposed single task, bounded loop, evidence/human pause and
  later resume;
- Demo 2 tests multiple work units, adaptive scheduling and shared-artifact
  convergence;
- Demo 3 demonstrates independent simple actions with different human-control boundaries in the same workbench. The current six-operation slice uses fixed policy and isolated test records; a general cross-topology risk/action gate remains a target.

The current Runtime is a `bounded_read_only_control_loop`. Validated plan units
become server-owned task branches; a user can continue one waiting branch while
the others keep their state. Logical evidence briefs and TaskCommits are stored
as independent append-only records, and a versioned rollback command can move
the current result pointer without deleting history or modifying source files.
PostgreSQL also restores accepted snapshots and idempotency receipts after API
restart.

The Demo 1/2 increment specified in
[`DR-0053`](docs/decisions/DR-0053-durable-task-lineage-and-explainable-topology-admission.md)
is now a limited current vertical slice. Demo 1 gives one business Task a stable
`task_id` across bounded parent/child Runs; a terminal Run can create a new Run
for exactly one unfinished Branch while the parent and its Artifact/Commit history
remain immutable. Demo 2 compiles validated plan facts into
`single_controller`, `fixed_workflow` or `adaptive_readonly_workers`; only the
last route asks for explicit confirmation and dispatches at most three in-process,
Branch-scoped read-only Analyst Workers per wave. Only anchored, adopted
contributions enter a new normal ArtifactVersion/TaskCommit. This is not a
distributed Worker platform, production lease system, general Tool Gateway or
evidence that multi-Worker execution improves quality, time or user outcomes.

[`DR-0054`](docs/decisions/DR-0054-durable-task-ledger-and-current-run-cas.md)
adds a limited owner-scoped Task Ledger. Initial start and one-Branch continuation
atomically persist the Task pointer, Run Snapshot and idempotency receipt. A
continuation must satisfy both the parent `run.version` and `task_version`; two
sibling requests from the same Task version cannot both become current. The UI
keeps a losing page on the immutable parent, marks it as historical and can open
the authoritative current Run through `GET /v1/harness/tasks/{task_id}`. This is
not a WorkUnit queue, Worker lease, production identity service or multi-instance
coordinator. The seven dedicated Task Ledger tests now pass against an isolated
PostgreSQL 17.11 instance after a malformed-parent-version fail-closed fix; this
is a single-host sequential transaction gate, not multi-instance execution or HA.

[`DR-0055`](docs/decisions/DR-0055-durable-workunit-and-contribution-ledger.md)
adds the next limited Demo 2 slice: every validated Worker Branch has a durable
`WorkUnitRecord`, and every Worker return appends an immutable
`ContributionRecord`. Reservation is committed before dispatch; returned and
adopted remain different facts. PostgreSQL restart preserves the validated
Branch DAG, completed contributions and v1/v2 history, marks an unconfirmed
in-flight unit as checkpoint-recovered failed, and never auto-replays it. A new
idempotency key plus current Run version can explicitly retry only that recovered
unit. This is still an in-process read-only Analyst Worker ledger, not a durable
queue, lease, remote Worker runtime or multi-instance scheduler. The isolated
PostgreSQL 17.11 Demo/Task combination passed 10 tests; the later fixed Demo 2
scenario gate brought full Python to 418 passed with 23 environment skips and
Playwright to 69 passed.

[`DR-0056`](docs/decisions/DR-0056-demo1-loop-and-adaptive-swarm-workspaces.md)
separates those two acceptance lenses in the frontstage without creating a
Demo API. The root page now groups the Owner's recent Runs by `task_id` as task
conversations; an opened Run is checked against the Task current pointer before
it is marked current or historical. Historical Runs remain inspectable but do
not receive SSE or expose controls. Demo 1 stays on the main Agent Control Loop
surface. The then-current implementation opened a full-screen Adaptive Swarm workbench that projects the
actual TopologyAdmission, approved sources, Branch/WorkUnit dependencies,
Worker receipts, Contribution gate and append-only Artifact versions. The
workbench labels the current implementation as bounded, in-process and
read-only; it is not a distributed Swarm, Task list service or proof of user
benefit. The separated-view engineering gate passes 73 Playwright tests, lint,
build and the existing 418-pass Python suite; screenshots and exact claim
boundaries are recorded in the DR-0056 Evidence. That Evidence remains valid for
the tested dialog, but `DR-0057` supersedes its interpretation as the Demo 2
product surface.

[`DR-0057`](docs/decisions/DR-0057-agent-capability-page-and-smart-cockpit-boundary.md)
corrects the product boundary against the 07-16 reference. The root remains the
Workspace. `/agent-capabilities` shows the Agent Control Loop and Adaptive Swarm
as two peer projections of the same selected Task/Run/Snapshot, including real
safe source labels and evidence review. Demo 2 itself remains the future smart
work cockpit: a server-backed task queue that chooses Tool Call, Single Agent,
Fixed Workflow or Adaptive Swarm and returns each task to one confirmation view.
No cockpit route, queue or dispatch contract is implemented in this slice, and
the UI does not render a placeholder that could be mistaken for one. The
integrated engineering gate passes 77 Playwright tests, 418 Python tests with 23
environment skips, Ruff, lint, build and reporting governance; exact screenshots
and claim boundaries are recorded in the DR-0057 Evidence.

[`DR-0058`](docs/decisions/DR-0058-progressive-disclosure-agent-capability-page.md)
keeps that one-Task/Run/Snapshot boundary but replaces the first dense, simultaneous
projection with four direct disclosure paths: concise execution progress, complete
execution record, collaboration method and one focused evidence decision. The first
screen is driven by open `DecisionRequest`, Branch state and the current
ArtifactVersion; it does not turn every Evidence gap into a user action. The
organization view still shows only the service-owned route and real WorkUnit,
Worker and Contribution facts. This is a presentation change, not a new Runtime,
distributed Swarm or completed smart work cockpit. Engineering checks and remaining
research limits are recorded in the DR-0058 Evidence.

The latest DR-0058 follow-up turns the Adaptive organization view from a route
summary into a Snapshot-driven execution workspace: a left stage rail, a dynamic
`work_units/depends_on` DAG, a derived current-impact panel and a compact result bar
share one screen, while sources and receipts remain disclosures. Fixed and single
routes still render no synthetic DAG or Worker activity. This closer visual match
uses visible parent-to-dependent arrows, projects the current Round's
`ready_branch_ids` as the next wave awaiting confirmation, and keeps that action in
the current-impact panel. It is verified only with controlled fixtures; it is not a
distributed scheduler, a live user study or the future Demo 2 cockpit.

[`DR-0059`](docs/decisions/DR-0059-explicit-requirement-accounting-and-bounded-analysis-recovery.md)
closes the visible “six requirements become five” ambiguity for a bounded
numbered-input syntax. Each explicit item is recorded as a current Plan unit,
an approved-source item deferred by this round's bounds, or an uncovered item
in the frozen public index. Deferred items keep a real waiting Branch and can be
continued one at a time; they are not mislabeled as missing data or silently
sent to an empty Worker wave. Internal Catalog title hints help Planner retrieval
without entering the public Workspace/Snapshot. Two real `deepseek-v4-pro` runs,
fixed fixtures and exact limitations are recorded in the DR-0059 Evidence; they
do not prove business correctness, general requirement parsing or user benefit.

[`DR-0060`](docs/decisions/DR-0060-new-task-conversation-entry.md) adds the
missing frontstage entry for an independent task conversation. “New task” is a
browser draft state rather than a server Task: it closes the selected stream,
clears the current projection, preserves prior history and creates nothing until
submit. Refresh preserves draft mode; opening history or accepting a new Snapshot
clears it. Repeating identical instruction text after another explicit new-task
action uses a fresh idempotency key. This adds no API path, cloud draft or task
deletion behavior.

## Public data and preview boundary

FORTE is pinned to commit
`345c1ec1487139db9dd319787fa9405ba85d1869` under its top-level MIT license.
The imported public set contains 15 task records plus 96 input files: 111 files
and `1,780,445` bytes. The official repository describes a 180-task benchmark
but publishes only one demo per profession; this project does not claim access
to the unpublished tasks.

`public-suite-manifest.json` is the active read-only inventory. Every preview
revalidates allowlisted relative path, size, SHA-256, non-symlink file and
bounded format handling. The current all-file smoke produces 96/96 previews:
70 text/code, 11 document, 9 table and 6 PDF. Macro/active content and external
resources are never executed or loaded.

`task.md` remains provenance only. It is not a hidden default instruction and
does not enter ordinary UI or model-selected context. The user supplies an
instruction; the server freezes all 96 stable refs, while the Planner sees only
safe metadata and autonomously selects a bounded set for each round.

## Twelve-path API

```text
GET  /v1/health
GET  /v1/harness/workspace
GET  /v1/harness/workspace/files/{file_ref}
POST /v1/harness/runs
GET  /v1/harness/runs?limit={1..20}
GET  /v1/harness/runs/{run_id}
GET  /v1/harness/tasks/{task_id}
POST /v1/harness/runs/{run_id}/continue
POST /v1/harness/runs/{run_id}/workers
GET  /v1/harness/runs/{run_id}/artifacts/{artifact_id}
POST /v1/harness/runs/{run_id}/controls
POST /v1/harness/runs/{run_id}/action-controls
GET  /v1/harness/runs/{run_id}/events?after={sequence}
```

The former Scenario list/detail routes are not mounted. There are thirteen public
operations over twelve OpenAPI paths because `GET` and `POST` share `/runs`.
`X-User-Id` remains an unsigned demonstration Owner placeholder. With
`DATABASE_DSN`, accepted Run snapshots, the minimal Task Ledger, Branch-bound
WorkUnits/Contributions, command/reservation receipts, ArtifactVersions and
TaskCommits are stored in PostgreSQL. Ordinary recovery rolls an interrupted
model round back to the last completed round. A committed Worker reservation
instead preserves its validated Branch DAG and completed candidates, marks the
unconfirmed unit recovered failed, and requires an explicit new-key retry. Neither
path silently replays a call. Without a database, health reports `memory` and process-
restart recovery is unavailable.

## Eight modules

1. Workspace Catalog & Safe Preview
2. Task Contract
3. Planner
4. Admission, Policy Compiler & Plan Validator
5. Scheduler & Worker Manager
6. Tool Gateway
7. Artifact Workspace & Verifier
8. Checkpoint, Event & Governance Control

Current implementation covers modules 1-4, including deterministic topology
admission; a bounded single-loop controller plus an explicitly confirmed,
in-process read-only Worker, Branch-bound WorkUnit and append-only Contribution
subset of module 5; module 6 remains unconnected as a
general Tool Gateway; module 7 includes a read-only result/citation/Evidence Gate,
logical append-only ArtifactVersion, TaskCommit pointer/restore, twelve fixed
deterministic local adapters with isolated run-workspace files, deterministic
verifiers and gated Worker contribution merge;
and a Snapshot/event, Task/Run lineage, branch/topology control, idempotency and
optional PostgreSQL Task/WorkUnit restart-recovery subset of module 8. Distributed Worker
leases, cross-process dispatch, a general
Tool Gateway, arbitrary source-file mutation, general semantic verification,
multi-instance coordination and governed external action remain target work.

## Evidence status

- `DR-0021` is `Limited Verified` for importing and inventorying the complete
  pinned public demo suite.
- `DR-0022` remains historical `Limited Verified` evidence for the one-folder
  product, 96 safe previews and its former selected-file browser path. That
  manual-scope interaction is superseded by `DR-0024`. Implementation
  [`0794648`](https://github.com/Dickey007s/lenovo_agent/commit/0794648477ad0061a5460127af8800a021019366)
  and [PR #27](https://github.com/Dickey007s/lenovo_agent/pull/27) are bound;
  the stacked series #25-#29 was consolidated into `master` on 2026-08-25.
- `DR-0023` is `Limited Verified` for the bounded read-only Agent Control Loop.
  Implementation `8364b1e` and stacked [PR #28](https://github.com/Dickey007s/lenovo_agent/pull/28)
  are bound and now merged through the consolidated series. A real
  `deepseek-v4-pro` run completed 2 rounds over 8 FORTE files with 5 model calls
  and 21 ordered events; the first candidate plan was rejected, visibly retried
  once within budget, then adopted.
- `DR-0024` replaces the `DR-0022` manual selected-file interaction with a
  whole-workspace contract, Agent-owned per-round evidence selection and
  human-confirmed next-task proposals. Its final verification is recorded in
  the linked Evidence ledger.
- `DR-0025` adds the human-confirmed between-round Evidence Gate, logical result
  versions, current-Run restoration and optional PostgreSQL restart recovery.
  PR #30 is merged through `8c55422`; its group-resume and Snapshot-embedded
  artifact conclusions are retained as historical baseline.
- `DR-0026` adds server-owned task branches, branch-selective continuation,
  independent append-only logical ArtifactVersion/TaskCommit records and a
  history-preserving restore command. Current local checks are `63 passed,
  1 skipped`, Runtime `26 passed`, browser `13 passed`, plus Ruff/lint/build.
  PR #31 also passed the PostgreSQL 17.11 four-Runtime restart integration gate;
  it is merged into `master` as `697e38b`, and the job URL plus exact boundary
  are bound in the dated Evidence.
- `DR-0028` projects the server-owned workspace paths as a collapsible folder
  tree and adds an in-context review page for Branch gaps, Findings and
  next-task proposals. It reuses the existing safe Preview API, makes citation
  limits explicit and does not add semantic verification or per-proposal
  citations.
- `DR-0029` adds server-verified Evidence Anchors. A Finding now carries exact
  safe-preview text lines or table rows resolved from verbatim model quotes;
  the review page compares evidence roles and jumps to highlighted source
  locations. Location verification still does not prove semantic correctness.
- `DR-0030` turns an anchored Finding into a Chinese problem-handling sheet:
  fact, impact, human-decision need, mutually exclusive choices, Agent next step
  and user feedback are separate. Accept, decline and defer are versioned,
  idempotent receipts bound to a Finding/Resolution/Branch; an accepted business
  choice then starts a new read-only Run. Location results are `exact`,
  `ambiguous` or `unavailable`; one bounded repair preserves valid Findings,
  completed Branches and ArtifactVersions, while only affected Branches wait for
  candidate selection or guided recovery. When recovery reaches a
  `stopped/bounded` budget terminal, the UI no longer suggests that the old Run
  can resume. The historical DR-0030 path created a fresh whole-workspace Run;
  DR-0053 now supersedes that terminal recovery with a same-Task child Run whose
  first scope is the selected Branch, preserving the old Run and artifacts.
  Security-scope violations still fail closed.
- `DR-0031` raises the default active deadline from 120 to 1,200 seconds and
  excludes human waiting/pause from elapsed time. It also replaces vague
  “missing evidence” copy with an Agent-owned recovery sheet: failure type,
  affected Branch, attempted files, call/adoption receipt, preserved work and a
  direct “retry only this Branch” action. Terminal Runs create a new bounded
  same-Task child Run rather than pretending to resume. A sanitized real
  `deepseek-v4-pro` run records a
  12-second human wait with unchanged active elapsed, followed by one-Branch
  recovery and completion; this is control-path evidence, not an answer-quality
  claim.
- `DR-0032` makes evidence ambiguity and human decisions recoverable server facts.
  `EvidenceResolution` now emits `exact/ambiguous/unavailable/stale/rejected`;
  `DecisionRequest/DecisionRecord` bind the current source revision, candidate,
  Branch, expected version and idempotency receipt. A real PostgreSQL 17.11 gate
  proves that an open three-candidate decision survives restart, accepting one
  candidate resumes only its Branch, preserves v1 and appends v2. These records
  remain nested in Snapshot JSONB, not an independently queryable decision ledger;
  no database CAS, multi-instance lease or in-flight model replay is claimed.
- `DR-0033` fixes the front-end projection of that contract. Open
  `DecisionRequest` packets come from the Snapshot top level; closing a review
  exits immediately and only then attempts a truthful `defer` receipt, so a 409
  can never trap the user. Evidence Gaps are shown as Branch lanes connecting
  Branch, current materials, Evidence Gate and next action. This is a UI fact
  projection, not proof of parallel Workers or improved user outcomes.
- `DR-0034` separates two human jobs that previously looked alike. A retry-only
  Branch now presents one recommended action without requiring file edits or
  input; optional clues and audit details are collapsed. An ambiguous source
  Branch instead requires an explicit candidate choice and keeps accept disabled
  until the user selects one real location. No Runtime protocol or budget rule
  changed, and the claimed clarity benefit remains a user-study hypothesis.
- `DR-0035` replaces the fixed three-round product assumption with a 12-round
  default and adds a Scenario Effect Gate. Twelve local FORTE tasks now generate
  real CSV/Markdown/DOCX/ZIP files in an isolated Run Workspace with deterministic
  checks and Owner-scoped download; three SQL/Web/Scheduler tasks stay
  `blocked_external_boundary`. The first real six-scenario run failed `0/6` and
  is retained; after moving deterministic work before Analyst narration and
  simplifying the model contract, all six priority effects passed. Model
  adoption, deterministic effect and Run terminal status remain separate facts.
- `DR-0036` fixes the TC-01 state where a 5/5 verified CSV looked unfinished
  because PDF layout wrapped “技术研发” across two Preview lines. The server now
  permits a punctuation/whitespace-insensitive fallback only after strict matching
  fails and still requires a unique location; repeated matches remain ambiguous.
  Findings whose verified observed dates all fall outside the explicit instruction
  window are omitted, and a human Gate without an exact contradiction Anchor is
  suppressed. When a historical Snapshot still has an audit-location gap, the UI
  shows the verified outcome first and groups duplicate same-source/same-failure
  gaps without changing server Branch state.
- `DR-0037` separates TC-05 task context from each file's content semantics.
  The two CSV cards now state that they contain 2026 ending-balance records,
  while only the cross-period note carries all three periods and zombie-account
  checks. Artifact cards expose server-owned period, basis, purpose and optional
  record count; review body text, evidence excerpts and safe previews are larger
  on desktop and 390 px. This remains one fixed Finance-018 adapter, not a
  general finance verifier or proof of improved user understanding.
- `DR-0038` turns a remaining `source_location` gap into one user task instead
  of a wall of Runtime terms. A verified result says that files are already
  generated and one Agent explanation still lacks a row/cell location; its
  primary action resumes only the affected Branch. Unverified and terminal Runs
  use different wording and never borrow the verified-result claim.
- `DR-0039` makes TC-10 distinguish a flow-design DOCX from external execution.
  The service-owned Artifact now states its type, M1 scope, source basis, six
  terminal states, review reason and execution boundary. The result area and
  task close both say that dialing, CRM writes and SMS did not occur. The
  downloaded DOCX repeats that boundary before its complete flow. This remains
  one fixed Operations-008 adapter, not a general outbound engine.
- `DR-0040` replaces TC-02's historical 9-file mini package with a refactor of
  the complete algorithm-013 project copy. The ZIP now retains every real input,
  includes a unified diff, machine-readable changes, Chinese review notes, a
  self-test card and manifest-matched test receipts. The main entry uses a
  bounded ReAct action/observation controller while the original Workflow, LLM
  and ToolRegistry contracts remain reviewable. Its default policy
  deterministically steps through planned tools behind a replaceable
  `action_policy`; it does not prove model-driven action selection inside the
  downloaded project. The outer Planner/Analyst provider calls are separate
  facts. Both deliverables project the same twelve verifier `check_id` values;
  Run-level UI and receipts therefore report one shared 12-item checklist rather
  than inflating it to 24 checks. This is one fixed adapter, not an arbitrary code
  sandbox, automatic PR path or OS-level network isolation.
- `DR-0041` replaces TC-04's historical 105-test `contracts.py` false green
  with the complete 44-file dev-015 project copy. The same 117 named tests run
  before and after three real-source fixes; the unpatched copy must expose five
  target failures, while the fixed copy must pass 117/117 and keep each changed
  file above 80% statement coverage. The self-test card shows five real suites,
  files, counts and expandable collected IDs from the same public manifest used
  by the ZIP. Before the roughly one-minute builder starts, the Runtime freezes
  all 46 allowlisted inputs and persists a started event; the synchronous build
  and test subprocesses then run through an in-process worker thread so health,
  Run GET, workspace browsing and SSE remain available. A duplicate dispatch for
  the same Run/capability is ignored, and failure emits `scenario_effect_failed`
  without a green Artifact. This remains one fixed adapter, not an arbitrary
  test sandbox, OS-level network isolation, real endpoint integration, automatic
  PR path, multi Worker scheduler or resumable Tool Gateway.
- `DR-0053` adds two bounded Demo 1/2 slices without creating Demo-specific
  product modes. Demo 1 stores `task_id`, parent Run, run sequence, selected
  unfinished Branch, base Artifact/Commit and current Workspace revision in the
  child Snapshot; `/continue` creates a new Run and leaves the parent immutable.
  Demo 2 persists a deterministic `TopologyAdmission`, separates admission from
  `/workers` confirmation, reserves model-call budget before dispatch, limits a
  wave to three ready Branches and appends only anchored adopted contributions to
  the normal Artifact/Commit history. Analyst/Worker findings use a governance
  maximum of 96 rather than a three-item analysis cap; the browser initially
  shows three only as a collapsible density choice. Unit and 1440/390 browser gates pass. The
  earlier three PostgreSQL restart tests have since run as part of the isolated
  DR-0055 gate; no paid Provider run or target-user study was performed.
  Therefore this is a limited in-process read-only slice, not proof of production
  durability, distributed Workers or business benefit.
- `DR-0054` adds a minimal owner-scoped Task record and two-level optimistic
  concurrency. Initial start and continuation commit Task/current pointer, Run
  and receipts as one State Store transition; `task_version` protects cross-Run
  current selection while `run.version` still protects one Run's controls. The
  public Task projection derives status, Artifact/Commit pointers and up to 100
  recent lineage items from immutable Run Snapshots. Targeted Python tests are
  `92 passed`, Task Ledger browser tests are `4 passed`, Ruff/lint/build pass,
  and seven PostgreSQL 17.11 tests pass. This proves only a single-host sequential
  transaction gate, not multi-instance safety, Provider quality or user comprehension.
- `DR-0055` binds every adaptive Worker Branch to an independently persisted
  WorkUnit and appends every return as a Contribution candidate. Full-DAG
  projection, two-wave v1/v2 convergence, partial waiting, fixed-workflow
  exclusion, strict reservation replay and checkpoint-recovered explicit retry
  are covered. Full Python is `417 passed, 23 skipped`; Playwright is `68 passed`;
  the real PostgreSQL 17.11 Demo/Task gate is `10 passed`. The frontend shows
  business work names, actual execution receipts, candidate outcomes and source
  location without exposing raw unit IDs. This remains a local read-only ledger,
  not a distributed scheduler, remote Worker platform or production executor.
- `DR-0042` replaces TC-12's historical repair-only 9/9 Vitest receipt with the
  complete 11-file qa-003 dashboard-toolkit copy and one manifest-owned 71-case
  test set. The same tests first expose the original alias failure, then the
  growth, sorting and date-boundary defects across three red stages, before the
  four-file fix passes 71/71. Three changed business modules each have their own
  V8 statements/lines >=85% and branches >=75% gate. The ZIP includes the full
  copy, unified diff, stage JSON, coverage, real test IDs and an independently
  rerun self-test. This remains a fixed qa-003 adapter, not an arbitrary
  JavaScript sandbox, OS-level network isolation, automatic PR or production
  multi-tenant execution.
- `DR-0043` replaces TC-11's historical name-list risk check with a strict
  four-source contract and an 18-row service-owned ledger. Risk levels now
  derive from PRD priority, the reason rule's own level cell, test facts and
  compatibility exceptions; unknown or ambiguous rule levels fail closed. Risk
  totals and the report/review summaries are recomputed from the ledger rather
  than fixed at the current sample's eight risks. Four
  formal business Gates retain numerator, denominator, operator and threshold.
  The UI can therefore show two simultaneous truths: both files passed nine
  deterministic source/formula/structure checks, while the business decision is
  still `4/4 Gates failed -> 不得上线`. This remains one fixed pm-014 adapter; it
  does not execute a release, write configuration or prove a general release
  audit engine.
- `DR-0044` replaces TC-07's historical fixed risk answers with a source-derived
  Legal-020 review. The service validates one rule table and six unique DOCX
  sources, evaluates all 21 rules for every document and verifies a 126-row CSV
  plus structured DOCX from the approved bytes. Principal and agent identity
  fields are isolated; an attorney license number without a Registry/Connector
  receipt remains `unverifiable`. The UI shows file verification, legal business
  Gates and signing/human review as three different states. This is an auxiliary
  fixed-input review, not legal advice, signature validation or authorization.
- `DR-0045` replaces TC-06's historical fixed candidate answers with a
  source-derived hr-001 review. The service validates two role-specific JD DOCX
  files and five unique resume PDFs, derives 14 BD and 8 text-evaluation
  conditions, and verifies two structured role reports plus a 110-row joint
  ledger from the approved bytes. Missing resume facts remain `unverifiable`,
  explicit source gaps can be `not_met`, and the BD education exception remains
  a human decision. The UI separates deterministic file checks, matching advice
  and the final HR decision. This is a fixed auxiliary review, not a general ATS,
  hiring decision, fairness proof, background check or candidate notification.
- `DR-0046` replaces TC-05's historical self-checking finance lists with a
  source-derived Finance-018 review. The service validates exactly three unique
  period workbooks, parses every business row with an Excel locator, recomputes
  the two 2026 ending-balance CSV files and independently verifies the three-
  period candidate note from the generated bytes. Zero, one or many candidates
  can all pass deterministic verification; the UI separately shows file checks,
  the current candidate count and the still-pending finance decision. This is a
  fixed heuristic review, not a general ledger or an accounting action.
- `DR-0047` replaces TC-10's historical fixed flow and self-checking 13-item
  list with a source-derived Operations-008 rule ledger and traversable graph.
  The service parses the approved Markdown line by line, maps every supported
  atomic requirement to stable nodes, edges, guards or terminals, and verifies
  the generated DOCX by parsing it again. The UI separates deterministic file
  and graph checks, rule coverage, pending approval and the fact that dialing,
  CRM, SMS, deny-list writes and human transfer did not occur. This is a fixed
  process-design adapter, not a general outbound system or legal opinion.
- `DR-0048` closes a source-completeness false green in that adapter. A selected
  Markdown line is consumed as auditable sentence fragments rather than marked
  wholesale by line number: supported inline high-age/serious-illness transfer
  requirements become independent rules and graph guards, while unknown or
  conflicting inline requirements fail closed. It also replaces fixed-yield
  async test waits with monotonic deadlines; neither change broadens TC-10 into
  a general policy compiler or production execution system.
- `DR-0049` replaces TC-13's fixed sample IDs, thresholds, distributions and
  sales wording with a source-derived Sales-020 cleaning ledger. The service
  validates exactly one approved survey CSV and one approved rule Markdown,
  derives every row conversion/profile/exclusion from those bytes, and then
  independently parses the generated Markdown and CSV. The UI separates
  deterministic files, cleaning facts and duplicate-policy assumption, a draft
  strategy awaiting sales approval, and the fact that no customer or CRM action
  occurred. This is a fixed public-sample adapter, not customer research, a CRM
  or a general segmentation engine.
- `DR-0050` replaces TC-14's fixed SRE numbers, commands and self-checking
  strings with a source-derived SRE-010 observation ledger. The service freezes
  the single approved log, separates observations from hypotheses, preserves
  three canonical source conflicts, and emits only unexecuted read-only,
  conditional-write and business-mitigation proposals. The Markdown and CSV are
  parsed again against a fresh source derivation. The UI separates deterministic
  file verification, contradictory observations, SRE review and the fact that
  no Elasticsearch or business action occurred. This is a fixed offline-review
  adapter, not monitoring, root-cause proof, a Connector or change approval.
- `DR-0051` replaces TC-15's 120-row Preview calculation, fixed rule answers and
  invented solution text with a full-workbook uiux-021 ledger. The service reads
  all approved XLSX rows, derives severity/frequency/priority and page specs from
  source bytes, retains duplicate/conflict/mapping assumptions, and independently
  parses both generated CSVs. Every group exposes the exact content-addressed
  source rules used. The UI separates deterministic coverage, data-quality facts,
  prioritization review and the fact that no design, experiment or production UI
  action occurred. This is not user research or a general UX analytics engine.
- `DR-0052` adds a generic narrative-reconciliation gate after deterministic
  effects and Analyst validation. A passed effect supplies compact authoritative
  facts to the Analyst; returned prose is adopted only when comparable claims
  agree. Contradictory or stale prose remains an auditable receipt but cannot
  enter the current Result, findings, follow-ups, Brief or Commit, while verified
  workspace files remain available. The UI claims deterministic authority only
  when the reconciliation protocol and a passed Artifact/EffectReceipt agree.
  This checks narrative consistency, not semantic completeness or business value.
- No target-user study has been run. Clarity, trust, efficiency and user value
  remain hypotheses.

Detailed claims and limits live in
[`FORTE-FOLDER-WORKSPACE-EVIDENCE-20260825`](docs/evidence/FORTE-FOLDER-WORKSPACE-EVIDENCE-20260825.md)
and [`AGENT-CONTROL-LOOP-BOUNDED-READONLY-20260825`](docs/evidence/AGENT-CONTROL-LOOP-BOUNDED-READONLY-EVIDENCE-20260825.md).
The current whole-workspace interaction is tracked in
[`AUTONOMOUS-WHOLE-WORKSPACE-RESEARCH-20260825`](docs/evidence/AUTONOMOUS-WHOLE-WORKSPACE-RESEARCH-EVIDENCE-20260825.md).
The current Demo 1 branch/artifact increment is tracked in
[`DEMO1-BRANCH-ARTIFACT-CONTROL-20260826`](docs/evidence/DEMO1-BRANCH-ARTIFACT-CONTROL-EVIDENCE-20260826.md).
The current cross-Run lineage and bounded topology/Worker increment is tracked in
[`DR-0053-DEMO1-DEMO2-RUNTIME-EVIDENCE-20260831`](docs/evidence/DR-0053-DEMO1-DEMO2-RUNTIME-EVIDENCE-20260831.md),
with user-replayable checks in
[`DEMO1-DEMO2-USER-VALIDATION-CASES-20260831`](docs/testing/DEMO1-DEMO2-USER-VALIDATION-CASES-20260831.md).
The current folder hierarchy and issue-review interaction is tracked in
[`WORKSPACE-TREE-AND-EVIDENCE-REVIEW-20260826`](docs/evidence/WORKSPACE-TREE-AND-EVIDENCE-REVIEW-EVIDENCE-20260826.md).
The current active-budget and Agent-gap recovery increment is tracked in
[`ACTIVE-BUDGET-AND-AGENT-GAP-RECOVERY-20260826`](docs/evidence/ACTIVE-BUDGET-AND-AGENT-GAP-RECOVERY-EVIDENCE-20260826.md).
The current exact evidence-location interaction is tracked in
[`PINPOINT-EVIDENCE-REVIEW-20260826`](docs/evidence/PINPOINT-EVIDENCE-REVIEW-EVIDENCE-20260826.md).
The current actionable review and recoverable-analysis interaction is tracked in
[`ACTIONABLE-REVIEW-AND-RECOVERY-20260826`](docs/evidence/ACTIONABLE-REVIEW-AND-RECOVERY-EVIDENCE-20260826.md).
The current persistent decision and Finding/Branch-local recovery increment is tracked in
[`DR-0032-POSTGRES-DECISION-RECOVERY-EVIDENCE-20260827`](docs/evidence/DR-0032-POSTGRES-DECISION-RECOVERY-EVIDENCE-20260827.md).
The current closable-review and Branch-lane interaction increment is tracked in
[`DR-0033-CLOSABLE-REVIEW-BRANCH-LANES-EVIDENCE-20260827`](docs/evidence/DR-0033-CLOSABLE-REVIEW-BRANCH-LANES-EVIDENCE-20260827.md).
The current one-action recovery and explicit source-choice increment is tracked in
[`DR-0034-ONE-ACTION-RECOVERY-EVIDENCE-20260827`](docs/evidence/DR-0034-ONE-ACTION-RECOVERY-EVIDENCE-20260827.md).
The current TC-01 outcome-first and evidence-localization increment is tracked in
[`DR-0036-TC01-OUTCOME-EVIDENCE-LOCALIZATION-EVIDENCE-20260828`](docs/evidence/DR-0036-TC01-OUTCOME-EVIDENCE-LOCALIZATION-EVIDENCE-20260828.md).
The current TC-05 artifact-semantics and review-readability increment is tracked in
[`DR-0037-TC05-ARTIFACT-SEMANTICS-AND-REVIEW-READABILITY-EVIDENCE-20260828`](docs/evidence/DR-0037-TC05-ARTIFACT-SEMANTICS-AND-REVIEW-READABILITY-EVIDENCE-20260828.md).
The source-location user-language and local-recovery increment is tracked in
[`DR-0038-USER-LANGUAGE-SOURCE-LOCATION-RECOVERY-EVIDENCE-20260828`](docs/evidence/DR-0038-USER-LANGUAGE-SOURCE-LOCATION-RECOVERY-EVIDENCE-20260828.md).
The current TC-11 source-derived release Gate increment is tracked in
[`DR-0043-TC11-DERIVED-RELEASE-GATES-EVIDENCE-20260828`](docs/evidence/DR-0043-TC11-DERIVED-RELEASE-GATES-EVIDENCE-20260828.md).
The current TC-06 source-derived candidate review increment is tracked in
[`DR-0045-TC06-SOURCE-DERIVED-CANDIDATE-REVIEW-EVIDENCE-20260829`](docs/evidence/DR-0045-TC06-SOURCE-DERIVED-CANDIDATE-REVIEW-EVIDENCE-20260829.md).
The current TC-05 source-derived finance candidate review increment is tracked in
[`DR-0046-TC05-SOURCE-DERIVED-FINANCE-REVIEW-EVIDENCE-20260829`](docs/evidence/DR-0046-TC05-SOURCE-DERIVED-FINANCE-REVIEW-EVIDENCE-20260829.md).
The current TC-10 source-derived outbound-flow increment is tracked in
[`DR-0047-TC10-SOURCE-DERIVED-OUTBOUND-FLOW-EVIDENCE-20260829`](docs/evidence/DR-0047-TC10-SOURCE-DERIVED-OUTBOUND-FLOW-EVIDENCE-20260829.md).
Its inline normative-fragment and stable Effect-wait correction is tracked in
[`DR-0048-TC10-FRAGMENT-CONSUMPTION-AND-STABLE-WAIT-EVIDENCE-20260829`](docs/evidence/DR-0048-TC10-FRAGMENT-CONSUMPTION-AND-STABLE-WAIT-EVIDENCE-20260829.md).
The current TC-13 source-derived customer-segmentation increment is tracked in
[`DR-0049-TC13-SOURCE-DERIVED-CUSTOMER-SEGMENTATION-EVIDENCE-20260829`](docs/evidence/DR-0049-TC13-SOURCE-DERIVED-CUSTOMER-SEGMENTATION-EVIDENCE-20260829.md).
The current TC-14 source-derived SRE incident-review increment is tracked in
[`DR-0050-TC14-SOURCE-DERIVED-SRE-DIAGNOSIS-EVIDENCE-20260829`](docs/evidence/DR-0050-TC14-SOURCE-DERIVED-SRE-DIAGNOSIS-EVIDENCE-20260829.md).
The current TC-15 full-workbook UX-prioritization increment is tracked in
[`DR-0051-TC15-SOURCE-DERIVED-UX-PRIORITIZATION-EVIDENCE-20260829`](docs/evidence/DR-0051-TC15-SOURCE-DERIVED-UX-PRIORITIZATION-EVIDENCE-20260829.md).
The current deterministic-outcome and model-narrative reconciliation increment is tracked in
[`DR-0052-NARRATIVE-RECONCILIATION-EVIDENCE-20260829`](docs/evidence/DR-0052-NARRATIVE-RECONCILIATION-EVIDENCE-20260829.md).

## Local run

Requirements: Python `>=3.12,<3.13`, Node/pnpm compatible with the lockfile and
an OpenAI-compatible `/chat/completions` endpoint.

```dotenv
LLM_BASE_URL=https://your-openai-compatible-endpoint.example/v1
LLM_API_KEY=replace-me
LLM_MODEL=deepseek-v4-pro
LLM_ANALYSIS_TIMEOUT_SECONDS=180
STATE_STORE_MODE=auto
```

Never commit `.env`, API keys, production credentials or real customer data.

```powershell
.\scripts\start-demo.ps1
.\scripts\stop-demo.ps1
```

本地启动器只把当前 PowerShell 进程中显式设置的 `DATABASE_DSN` 视为外部
PostgreSQL 授权；没有 Docker 且没有该显式变量时，会覆盖 `.env` 中可能残留的
数据库地址：启动器设置非空 `STATE_STORE_MODE=memory`，Runtime 据此明确回退到
单进程 memory，而不是依赖 Windows 后台进程能否继承空环境变量。默认
`STATE_STORE_MODE=auto`；显式 `postgres` 但没有 DSN 会拒绝启动。模型端点、Key
与模型名仍可从 `.env`
读取。启动后以 `/v1/health` 的 `checkpoint`、`task_store` 为最终事实，不能只看
启动提示推断是否具备重启恢复。

- Web: <http://localhost:3000>
- API: <http://localhost:8010>
- OpenAPI: <http://localhost:8010/docs>

## Verification

```powershell
uv run pytest -q
uv run ruff check .
pnpm --dir apps/web lint
pnpm --dir apps/web build
pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts
```

## Living records

- [当前架构](docs/ARCHITECTURE.md)
- [HTTP API 与 SSE](docs/API.md)
- [工作区与流式交互](docs/WORKSPACE_AND_STREAMING.md)
- [前后端事实矩阵](docs/contracts/UI_SERVER_FACT_MATRIX.md)
- [目标架构](docs/TARGET_ARCHITECTURE.md)
- [中文汇报卡片](docs/PRESENTATION_BRIEF.md)
- [详细中文汇报稿与 17 页图文规划](docs/reports/OFFICE-AGENT-DETAILED-CHINESE-REPORT-20260825.md)
- [可证伪竞争差异、八个同场挑战与前台影响研究](docs/research/COMPETITIVE-WHITE-SPACE-AND-FALSIFIABLE-DIFFERENTIATORS-20260826.md)
- [可处置人工决策与失败恢复研究](docs/research/ACTIONABLE-HUMAN-DECISION-AND-FAILURE-RECOVERY-20260826.md)
- [Demo 1/2 跨 Run 任务连续性、拓扑准入与交互影响研究](docs/research/DEMO1-DEMO2-DURABLE-TASK-AND-ADAPTIVE-ORCHESTRATION-RESEARCH-20260830.md)
- [Demo 1/2 分层工作面与 Adaptive Swarm 前台研究](docs/research/DEMO1-DEMO2-SEPARATED-VIEWS-AND-ADAPTIVE-SWARM-UI-RESEARCH-20260901.md)
- [DR-0056：Demo 1 Loop 与 Demo 2 Adaptive Swarm 分层工作面](docs/decisions/DR-0056-demo1-loop-and-adaptive-swarm-workspaces.md)
- [SCENARIO-043：任务会话回看与 Adaptive Swarm 独立工作台](docs/scenarios/SCENARIO-043-task-conversations-and-adaptive-swarm-workbench.md)
- [Demo 1 / Demo 2 分层工作面验收门](docs/testing/DEMO1-DEMO2-SEPARATED-WORKSPACE-GATES-20260901.md)
- [Demo 1 / Demo 2 分层工作面工程 Evidence](docs/evidence/DR-0056-DEMO1-DEMO2-SEPARATED-WORKSPACES-EVIDENCE-20260901.md)
- [DR-0057：Agent 能力页与智能工作驾驶舱边界](docs/decisions/DR-0057-agent-capability-page-and-smart-cockpit-boundary.md)
- [SCENARIO-044：同页核对循环与协作能力，驾驶舱保持后续目标](docs/scenarios/SCENARIO-044-agent-capability-page-and-future-smart-cockpit.md)
- [Agent 能力页与驾驶舱边界验收门](docs/testing/AGENT-CAPABILITY-PAGE-AND-COCKPIT-BOUNDARY-GATES-20260901.md)
- [Agent 能力页工程 Evidence](docs/evidence/DR-0057-AGENT-CAPABILITY-PAGE-EVIDENCE-20260901.md)
- [DR-0058：Agent 能力页四层渐进披露](docs/decisions/DR-0058-progressive-disclosure-agent-capability-page.md)
- [SCENARIO-045：从任务进展逐层查看执行、协作与原文依据](docs/scenarios/SCENARIO-045-progressive-agent-capability-review.md)
- [Agent 能力页四层渐进披露验收门](docs/testing/AGENT-CAPABILITY-PROGRESSIVE-DISCLOSURE-GATES-20260901.md)
- [Agent 能力页四层渐进披露工程 Evidence](docs/evidence/DR-0058-AGENT-CAPABILITY-PROGRESSIVE-DISCLOSURE-EVIDENCE-20260901.md)
- [DR-0059：显式要求逐项记账与受限分析恢复](docs/decisions/DR-0059-explicit-requirement-accounting-and-bounded-analysis-recovery.md)
- [SCENARIO-046：六项复杂任务逐项记账并从分析失败继续](docs/scenarios/SCENARIO-046-account-for-explicit-requirements-and-recover-analysis.md)
- [显式要求与分析恢复工程 Evidence](docs/evidence/DR-0059-EXPLICIT-REQUIREMENT-AND-ANALYSIS-RECOVERY-EVIDENCE-20260902.md)
- [DR-0060：显式新建任务入口与独立草稿](docs/decisions/DR-0060-new-task-conversation-entry.md)
- [SCENARIO-047：从当前工作进入一个独立新任务](docs/scenarios/SCENARIO-047-start-an-independent-task-conversation.md)
- [新建任务会话验收门](docs/testing/NEW-TASK-CONVERSATION-GATES-20260903.md)
- [新建任务会话工程 Evidence](docs/evidence/DR-0060-NEW-TASK-CONVERSATION-EVIDENCE-20260903.md)
- [来源台账](docs/decisions/SOURCE_REGISTER.md)
- [DR-0054：独立 Task Ledger 与当前 Run 版本控制](docs/decisions/DR-0054-durable-task-ledger-and-current-run-cas.md)
- [SCENARIO-040：两个页面同时续办时只有一个当前 Run](docs/scenarios/SCENARIO-040-task-current-run-cas-and-restart.md)
- [Task Ledger V1 工程 Evidence](docs/evidence/DR-0054-TASK-LEDGER-V1-EVIDENCE-20260831.md)
- [DR-0055：Branch 绑定的 WorkUnit 与不可变 Contribution 台账](docs/decisions/DR-0055-durable-workunit-and-contribution-ledger.md)
- [SCENARIO-041：五个工作包的可恢复执行与局部成果收敛](docs/scenarios/SCENARIO-041-workunit-contribution-ledger-and-partial-convergence.md)
- [SCENARIO-042：跨职能风险与待办简报的输入、过程与输出](docs/scenarios/SCENARIO-042-demo2-cross-functional-risk-brief.md)
- [Demo 2 输入、过程与输出场景门](docs/testing/DEMO2-INPUT-PROCESS-OUTPUT-GATES-20260831.md)
- [Demo 2 输入、过程与输出工程 Evidence](docs/evidence/DR-0055-DEMO2-INPUT-PROCESS-OUTPUT-EVIDENCE-20260831.md)
- [WorkUnit / Contribution Ledger V1 工程 Evidence](docs/evidence/DR-0055-WORKUNIT-CONTRIBUTION-LEDGER-V1-EVIDENCE-20260831.md)
- [DR-0053：跨 Run 任务谱系与可解释协作拓扑准入](docs/decisions/DR-0053-durable-task-lineage-and-explainable-topology-admission.md)
- [SCENARIO-038：同一办公任务跨 Run 延续而不覆盖历史](docs/scenarios/SCENARIO-038-durable-task-continuation-across-runs.md)
- [SCENARIO-039：可解释路线准入与受限 Worker 统一收敛](docs/scenarios/SCENARIO-039-explainable-topology-and-verified-worker-convergence.md)
- [DR-0022](docs/decisions/DR-0022-workspace-folder-and-arbitrary-task-contract.md)
- [SCENARIO-008](docs/scenarios/SCENARIO-008-whole-folder-office-workspace.md)
- [DR-0023：三轮只读 Agent Control Loop](docs/decisions/DR-0023-agent-control-loop.md)
- [SCENARIO-009：Agent 研究当前文件夹并提出下一步](docs/scenarios/SCENARIO-009-agent-control-loop.md)
- [DR-0024：整库自主研究与人工确认下一轮](docs/decisions/DR-0024-autonomous-whole-workspace-research.md)
- [SCENARIO-010：Agent 自主研究整个办公资料库](docs/scenarios/SCENARIO-010-autonomous-whole-workspace-research.md)
- [DR-0025：可恢复检查点、人工证据门与成果演进](docs/decisions/DR-0025-durable-evidence-gate-and-artifact-evolution.md)
- [SCENARIO-011：中断恢复与逐轮补证](docs/scenarios/SCENARIO-011-recover-and-confirm-evidence-round.md)
- [DR-0026：可选择任务分支与不可变成果历史](docs/decisions/DR-0026-selective-branch-and-immutable-artifact-history.md)
- [SCENARIO-012：按分支补证并恢复历史成果](docs/scenarios/SCENARIO-012-selective-branch-and-artifact-restore.md)
- [Demo 1 分支与成果控制 Evidence](docs/evidence/DEMO1-BRANCH-ARTIFACT-CONTROL-EVIDENCE-20260826.md)
- [DR-0027：本地启动状态库选择](docs/decisions/DR-0027-truthful-local-state-store-selection.md)
- [SCENARIO-013：真实的本地状态库回退](docs/scenarios/SCENARIO-013-truthful-local-state-store-fallback.md)
- [本地启动状态库优先级 Evidence](docs/evidence/START-DEMO-DSN-PRECEDENCE-EVIDENCE-20260826.md)
- [DR-0028：分层文件目录与问题审查页](docs/decisions/DR-0028-hierarchical-workspace-and-evidence-review.md)
- [SCENARIO-014：在原始资料中核对 Agent 问题](docs/scenarios/SCENARIO-014-inspect-agent-issue-in-context.md)
- [分层文件目录与问题审查页 Evidence](docs/evidence/WORKSPACE-TREE-AND-EVIDENCE-REVIEW-EVIDENCE-20260826.md)
- [DR-0029：服务端验证的证据锚点](docs/decisions/DR-0029-server-verified-evidence-anchors.md)
- [SCENARIO-015：定位并对照 Agent 证据](docs/scenarios/SCENARIO-015-pinpoint-and-compare-agent-evidence.md)
- [原文定位审查 Evidence](docs/evidence/PINPOINT-EVIDENCE-REVIEW-EVIDENCE-20260826.md)
- [DR-0030：可处置问题审查与可恢复分析门](docs/decisions/DR-0030-actionable-review-and-recoverable-analysis.md)
- [SCENARIO-016：从可定位问题到人工决断，并从分析失败继续](docs/scenarios/SCENARIO-016-actionable-finding-and-recoverable-analysis.md)
- [可处置问题与失败恢复 Evidence](docs/evidence/ACTIONABLE-REVIEW-AND-RECOVERY-EVIDENCE-20260826.md)
- [DR-0036：成果优先、版面容错定位与任务范围收敛](docs/decisions/DR-0036-outcome-first-and-layout-tolerant-evidence.md)
- [SCENARIO-022：成果已验证时，把来源定位作为独立审计项](docs/scenarios/SCENARIO-022-verified-outcome-and-audit-location.md)
- [TC-01 成果与引用定位 Evidence](docs/evidence/DR-0036-TC01-OUTCOME-EVIDENCE-LOCALIZATION-EVIDENCE-20260828.md)
- [DR-0037：TC-05 成果语义与问题审查可读性](docs/decisions/DR-0037-tc05-artifact-semantics-and-review-readability.md)
- [SCENARIO-023：在下载前理解财务成果并清楚审查证据](docs/scenarios/SCENARIO-023-understand-finance-artifacts-and-review-evidence.md)
- [TC-05 成果语义与审查可读性 Evidence](docs/evidence/DR-0037-TC05-ARTIFACT-SEMANTICS-AND-REVIEW-READABILITY-EVIDENCE-20260828.md)
- [DR-0038：用用户任务语言呈现原表格位置恢复](docs/decisions/DR-0038-user-language-source-location-recovery.md)
- [SCENARIO-024：理解并恢复缺少的原表格位置](docs/scenarios/SCENARIO-024-understand-and-recover-missing-table-location.md)
- [原表格位置用户语言与局部恢复 Evidence](docs/evidence/DR-0038-USER-LANGUAGE-SOURCE-LOCATION-RECOVERY-EVIDENCE-20260828.md)
- [DR-0043：TC-11 来源推导风险、正式业务 Gate 与双状态前台](docs/decisions/DR-0043-tc11-derived-release-gates.md)
- [SCENARIO-029：从四份发布资料推导上线 Gate 并审查整改计划](docs/scenarios/SCENARIO-029-review-derived-release-gates.md)
- [TC-11 来源推导上线 Gate Evidence](docs/evidence/DR-0043-TC11-DERIVED-RELEASE-GATES-EVIDENCE-20260828.md)
- [DR-0044：TC-07 来源推导授权核查与三状态前台](docs/decisions/DR-0044-tc07-source-derived-legal-delegation-review.md)
- [SCENARIO-030：从一份规则和六份委托书逐项推导复核清单](docs/scenarios/SCENARIO-030-review-six-delegations-with-source-derived-rules.md)
- [TC-07 来源推导授权核查 Evidence](docs/evidence/DR-0044-TC07-SOURCE-DERIVED-LEGAL-REVIEW-EVIDENCE-20260828.md)
- [DR-0045：TC-06 来源推导双岗位辅助筛选与 HR 决策边界](docs/decisions/DR-0045-tc06-source-derived-candidate-review.md)
- [SCENARIO-031：用两份 JD 与五份简历形成可追溯的人工复核建议](docs/scenarios/SCENARIO-031-review-two-jobs-and-five-resumes-with-source-derived-conditions.md)
- [TC-06 来源推导双岗位辅助筛选 Evidence](docs/evidence/DR-0045-TC06-SOURCE-DERIVED-CANDIDATE-REVIEW-EVIDENCE-20260829.md)
- [DR-0046：TC-05 来源推导跨期风险候选与财务处置边界](docs/decisions/DR-0046-tc05-source-derived-finance-candidate-review.md)
- [DR-0047：TC-10 来源推导外呼流程图与四层审批边界](docs/decisions/DR-0047-tc10-source-derived-outbound-flow.md)
- [DR-0048：TC-10 规范片段消费与稳定 Effect 等待](docs/decisions/DR-0048-tc10-fragment-consumption-and-stable-effect-wait.md)
- [DR-0049：TC-13 来源推导画像清洗、策略草案与四层事实](docs/decisions/DR-0049-tc13-source-derived-customer-segmentation.md)
- [SCENARIO-032：从三期往来明细推导可复核风险候选](docs/scenarios/SCENARIO-032-review-three-period-finance-candidates-from-source.md)
- [TC-05 来源推导财务候选 Evidence](docs/evidence/DR-0046-TC05-SOURCE-DERIVED-FINANCE-REVIEW-EVIDENCE-20260829.md)
- [TC-10 来源推导外呼流程 Evidence](docs/evidence/DR-0047-TC10-SOURCE-DERIVED-OUTBOUND-FLOW-EVIDENCE-20260829.md)
- [TC-10 规范片段消费与稳定等待 Evidence](docs/evidence/DR-0048-TC10-FRAGMENT-CONSUMPTION-AND-STABLE-WAIT-EVIDENCE-20260829.md)
- [SCENARIO-034：从公开问卷与规则推导可复核画像清洗和策略草案](docs/scenarios/SCENARIO-034-review-source-derived-customer-segmentation.md)
- [TC-13 来源推导客户画像 Evidence](docs/evidence/DR-0049-TC13-SOURCE-DERIVED-CUSTOMER-SEGMENTATION-EVIDENCE-20260829.md)
- [DR-0050：TC-14 来源推导 SRE 事故复盘与未执行提案](docs/decisions/DR-0050-tc14-source-derived-sre-incident-review.md)
- [SCENARIO-035：从公开日志形成可复核事故复盘](docs/scenarios/SCENARIO-035-review-source-derived-sre-incident.md)
- [TC-14 来源推导 SRE 复盘 Evidence](docs/evidence/DR-0050-TC14-SOURCE-DERIVED-SRE-DIAGNOSIS-EVIDENCE-20260829.md)
- [DR-0051：TC-15 完整日志来源推导与逐组规则引用](docs/decisions/DR-0051-tc15-source-derived-ux-prioritization.md)
- [SCENARIO-036：从完整交互日志形成可回溯优先级](docs/scenarios/SCENARIO-036-review-source-derived-ux-prioritization.md)
- [TC-15 来源推导交互优先级 Evidence](docs/evidence/DR-0051-TC15-SOURCE-DERIVED-UX-PRIORITIZATION-EVIDENCE-20260829.md)
- [DR-0052：服务端确定性成果与模型说明对账](docs/decisions/DR-0052-authoritative-outcome-and-narrative-reconciliation.md)
- [SCENARIO-037：只保留一个可复核的当前结论](docs/scenarios/SCENARIO-037-reconcile-model-narrative-with-authoritative-outcome.md)
- [模型说明对账 Evidence](docs/evidence/DR-0052-NARRATIVE-RECONCILIATION-EVIDENCE-20260829.md)
- [可恢复 Control Loop Evidence](docs/evidence/DURABLE-EVIDENCE-GATE-ARTIFACT-EVOLUTION-EVIDENCE-20260826.md)
- [整库自主研究 Evidence](docs/evidence/AUTONOMOUS-WHOLE-WORKSPACE-RESEARCH-EVIDENCE-20260825.md)
- [Agent Control Loop 三轮只读纵切证据](docs/evidence/AGENT-CONTROL-LOOP-BOUNDED-READONLY-EVIDENCE-20260825.md)
- [主流方案、办公场景与交互影响研究](docs/research/WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825.md)
- [Agent Control Loop 当前实现审计与下一纵切](docs/research/AGENT-CONTROL-LOOP-IMPLEMENTATION-AUDIT-20260825.md)
- [15 类办公测试目录](docs/testing/FORTE-PUBLIC-OFFICE-TASK-TEST-CASES-20260825.md)
- [公开数据套件清单](docs/research/FORTE-PUBLIC-SUITE-INVENTORY-20260825.md)

A dated historical document proves only its recorded commit and scope unless a
living document explicitly carries the fact forward.
