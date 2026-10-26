# Office Agent V0.2 中文汇报卡片

## 2026-10-26 主 Agent 优先的设计对齐

讲述主线：主 Agent 统一负责目标，按需加载处理方法，明确有委派收益才组队；证据与权限仍由原系统控制。本轮把工作项和执行人数分开，接入三个固定方法。相同入职交接目标由两个执行 Agent 改为一个主分析，保留两个工作项与依据。4项真实任务中3项完成，1项因计划含人工门而阻塞，共9次调用。多工作项主路径处理后扩编尚未接通，不讲成完整通用自主循环；本轮不证明质量提高或最优人数。见 [DR-0097 Evidence](evidence/DR-0097-PRIMARY-DESIGN-20261026.md)。

## 2026-10-26 单项处理后按结果追加

可以讲：单个只读工作项完成后，预算允许时检查是否需要补核；通过服务端校验后追加，保留原贡献和旧版本。真实两项单 Agent、一项双 Agent，共10次调用，均未追加。单到多的执行在受控响应下通过，尚无本轮真实扩编案例。技能库、最优人数、成本降低和业务正确性并未由此证明。见 [DR-0096 Evidence](evidence/DR-0096-SINGLE-AGENT-DELEGATION-20261026.md)。

## 2026-10-25 可复核的演示实例

当前 3000 入口已更新后台，并真实执行 17 次任务。推荐顺序：Word 要求分组 → 按明确例外整理权限 → 缺到账凭证 → 未批准的权限变更 → Demo2 三项待办。Demo2 实际为 3、1、1 个执行 Agent；复杂任务的协调检查没有新增工作。只读页面分析，不是生成办公文件或真实业务操作。共 7 例使用 17 次模型调用；所有迭代合计 46 次。未入选的漏项/过度推断留在记录中，不能声称通用完整性已解决。见 [Evidence](evidence/DR-0094-DEMO-READINESS-20261025.md)。

## 2026-10-25 录屏反馈后的减法

把一次点击看原文、同任务切换处理记录、逐行看 Agent 分工做清楚。删除常驻示例、空人工栏和主区预算分母；没有取消权限和预算。首轮补的是可理解的执行流程，不宣称模型更聪明。后续建议与原任务欠项分开；缺少独立理由的旧建议明确保留这一限制。验证和未完成项见 [DR-0093 Evidence](evidence/DR-0093-BLURT-WORKBENCH-20261025.md)。

## 2026-10-25 用当前系统重跑演示页

[新版案例页](showcase/office-agent-20261024/index.html)分三类能力、八个故事展示。真实模型案例覆盖明确规则、缺凭证、同任务人工续办和多任务自主分工；固定规则案例覆盖草稿修订、确认失效和人工取舍。发布案例共 17 次模型调用；包含未采用首跑和额外截图尝试共 29 次。三 Agent 协作后的实际检查选择不新增，不得讲成真实动态扩编成功。没有外部业务执行。详见 [DR-0092 Evidence](evidence/DR-0092-LIVE-SHOWCASE-20261025.md)。

## 2026-10-24 从预设分工转向按结果调整

可以讲：输入只给办公目标，模型提出工作包，服务端按独立性、来源和预算确定执行方式。每批完成后，协调模型检查是否需要追加有依据的新工作；画面只显示实际原因、节点与回执。
不能讲：已经实证自主扩编、最优团队规模、任意动态重规划或自动修正所有错误。18个真实任务中的10次协调判断均未新增；新增工作及二次派发仅在受控响应下验证。引用通过仍可能误读例外，详见 [Evidence](evidence/DR-0091-ADAPTIVE-PROGRESS-20261024.md)。

## 2026-10-24 不止双 Agent：分析之后有人接续核对

可讲：新增周度办公简报案例。3个执行 Agent 分别分析招聘 Word、办公软件 PDF、往来账 Excel；随后2个执行 Agent 基于前序结果和原文做汇总/金额核对。真实重复两次，均为3+2两波、5份采用结果，每次复杂任务6次模型调用。同组另有两个单 Agent 待办；两组运行总计6个任务、20次调用。
界面分层显示实际工作包，结果点击展开。不能讲5个同时并行、动态最优人数、分布式蜂群、自动招聘/开权限/核实银行到账，也未生成新的办公文件。见 [Evidence](evidence/DR-0090-FIVE-WORKERS-20261024.md)。


## 2026-10-24 Demo2 用办公待办讲清分工

可讲：六个简单待办各实跑两次，共12个任务、26次模型调用。单文件摘录走单 Agent；同类招聘资料保持顺序；入职规则与招聘要求由两个执行 Agent 真实重叠处理，分别产出可回看原文的分析。未点击人工派发确认。
界面先看任务、实际分工和结果；指令与回执收起，查看详情可回到本次待办。实际截图和编号见 DR-0089 Evidence。
不可讲：任务难度已被智能量化、多 Agent 必然更好、所有输出业务正确、已生成办公文件或实际开通权限。当前同目录顺序准入仍是保守结构规则，不是最优调度证明。

## 2026-10-24 谁来做，为什么

可讲：同一任务里，系统先处理有来源、可按明确规则整理的内容。缺少银行回单与请求改变权限例外分别交给人补事实、作选择；技术补证单列，不笼统甩给人。
三组真实模型案例各复测一次；明确选择“维持现规则”后，在同一 Task 完成后续核对。真实截图与运行编号见 DR-0088 Evidence。
不可讲：我们已校准模型置信度、引用即正确、补充资料闭环已完成、实际开通权限或负责人已作真实业务审批。提示修正后的缺源识别只有单样例复测，不是泛化保证。

## 2026-10-24 用一个任务讲清楚前后过程

可讲：Demo1 从 Excel、Word、入职清单开始；先说明目标和资料，再显示真实处理安排。后续建议留在同一个任务里，原结果可切回查看。
实测暴露并修复了“后续要求没有原背景导致跨业务漂移”和“只读示例错误进入文件工具”的问题。记录见 DR-0087 Evidence。
不可讲：模型思维链完全透明、所有人都能理解、所有缺源都能准确判断、后续分支一定完成或多分支任意并行。实跑后续分支仍出现来源定位不足，已保留有效部分并等待处理。

## 2026-10-24 真实模型实操

可以说：三个只读待办分别启动，各自判断单 Agent 或多 Agent；本轮真实复测出现两项单 Agent 完成、一项双 Worker 并行完成，非动画或固定回执。
Demo1 实跑覆盖规则摘录、代码日志对照、缺批准依据；暂停时已完成工作和保留引用可见。实测遇到引用过长、引用定位失败并做了复测，不能只展示成功截图。
不能说：通用难度评分、任意任务必成功、分布式蜂群、语义缺源已解决、批准书已找到、用户体验效果已验证。
旧模型禁用预览3000与本次模型实跑3010必须区分；项目仍是一套源码，不是另一个静态演示系统。运行标识、数量和边界以 DR-0086 Evidence 为准。

## 2026-10-23 统一设计第一阶段

可以说：原入口已换成统一三栏，任务、原文依据和成果共用一套导航；工作包图区分待派发、回执和采用。
不能说：18张图的所有功能已实现、像素级一致、Demo2已无人参与多任务调度、Demo3已有独立资料目录。
本轮截图的分析任务来自受控回执，事项是实际固定规则API。验证与失败修复见 DR-0085 Evidence；不是用户效果研究。

## 2026-10-23 八案演示

[能力演示页](showcase/office-agent-20261023/index.html)按任务推进、工作包协作、人工决定组织八案，27 张原系统截图。
Demo1/2 明确是受控回执演示；Demo3 为本轮实际固定规则 API，无模型、无外部业务动作。
可以说界面与流程可演示，不能说八案都是本轮模型实跑、任意指令都能复现、分布式蜂群已完成或用户效果已验证。
来源、交互与定向成果提示修复见 DR-0084 Evidence。

## 2026-10-22 走查表述

本轮可说：按用户路径走过资料、任务、等待、核对、成果和协作，修复草稿入口矛盾与协作状态误导，减少重复回执和次要操作。
不可说：做了真实用户实验、模型完成率提升、真实模型新产出或人机共驾全部完成。任务中间态使用受控 API 回执；细节见 DR-0083 Evidence。

## 2026-10-22 等待与协作表达

原等待页合并重复说明，把问题和操作放在一起；协作图缩短状态、归组下游影响，保留实际依赖。
这是展示层改进，不是新的蜂群能力。受控截图与回归不证明用户理解提升，结果见 DR-0082 Evidence。

## 2026-10-22 首页结构重排

DR-0081 在原工作台先展示文件和业务结论，完整执行记录按需查看，全部未完成项仍可找到。
这是展示改进，不是新能力或用户收益证据。界面截图为受控 API；验收范围见对应 Evidence。

## 2026-10-22 参考图对照

继续在原系统做信息减法：省略全已完成分支的重复清单、合并能力页文件成果入口、让协作图先于统计出现。
这是展示层改善，不是新调度能力或目标用户效果。未完成分支、业务否决与原确认控制不隐藏。
截图为本轮原前端加受控 API，nanoMuse 借鉴仍限于既有研究的信息分层原则。验证见 DR-0080 Evidence。

## 2026-10-20 原则增量

原工作台新增三处限定实践：R12 个人整理方式可记住及撤回；R14 旧摘录先预览再保存新版本；
R10 最近记录按待处理筛选。不是自动授权、源文件回滚或完整待办系统，验证见 DR-0079 Evidence。
10 月 19 日默认视频已改为 30 秒无声短版，保留历史长版，剪辑来源不变。

## 2026-10-19 三案与设计交付

[交付入口](deliverables/copilot-20261019/index.html)：六份设计文档及带中文合成讲解的三案视频。
本轮新增是交接说明补强、R01-R16 实践对照和可评审的场景/流程/技术/体验方案；原六类事项和原则手册归队友。
案例一复用 10 月 10 日实际运行；案例二是本次受控 Fixture；案例三是本次真实固定规则 API，不调用模型。
不得将剪辑拼接说成一次连续真实模型运行，也不得把文件检查、人工判断和业务批准混为一谈。

## 三个共驾案例的设计依据

[案例解读](reports/copilot-cases-20261010/index.html)：C02 准备草稿不等于批准内容，C08 修改后需核对
新版本，C11 记录判断不等于启动下游。手册和原事项能力归队友，本轮新增的是案例分析、定向 UI 调整
及前后测试。三篇文献是设计依据，不是本系统用户收益证据；Worker 人工恢复闭环仍未完成。
先前版本已独立存档，细节见 [DR-0077 Evidence](evidence/DR-0077-COPILOT-CASES-20261010.md)。

## 实际改善怎么讲

原报告新增 [六个前后案例](reports/september-progress-20261010/index.html#improvements)。最强证据为：
同指令禁止文件却产出 2 份变为 0 份；原来已采用的 6/7、14/13 错数在当前回放中被拒；
同份 UX 表供给从 60/212 变为 212/212 行。交接是实际前序输入，不是蜂群质量优势；
续办框架原已存在，补的是局部失败修复与验证。数据与本轮 52 项定向回归见
[BEFORE-AFTER](reports/september-progress-20261010/BEFORE-AFTER.md)，不得将历史 162 项浏览器结果当本轮新跑。

## 证据捕获与协作补充

九月进展 HTML 已补证据捕获五步、实际 PRD 的 89/94 行锚点与三种定位结果，以及六步多 Agent
流程和 9.21 两波部分采用记录。锚点证明位置，不证明结论正确；9.21 真实交接不倒算为 9.22
新增逐项核对协议的完整真实验收。Demo1 原界面减法见 DR-0076；不改变系统入口或 Runtime。

## 2026-10-10 九月以来本方进展

[离线图文汇报](reports/september-progress-20261010/index.html)按系统全貌、阶段时间线、界面前后、
真实办公交付、Loop/Swarm 机制和未完成项组织，含讲稿、原截图与录屏。
只统计本方 Demo1/2、研究验证及后续整合，不把队友 Demo3 原始实现或八月基线算成本期新增。
已提交与本地未提交进展分开；归属、来源、字段和验证范围见该目录 README。

## 2026-10-10 Demo1 主线

汇报配图：[四张系统流程图](reports/system-flow-20261010/index.html)，包含统一入口、Demo1 循环、
Demo2 依赖协作、一次真实上线资料核对。前三张是当前合同的概念流程，第四张才是实际 Run；
来源、字段映射和导出验收见该目录 README。不得把协作示意图当作一次真实五包完成证据。

先演示具体办公目标、输入材料和实际下载物，再按需解释 Control Loop 与恢复机制。
不得将旧模拟续办视频写成真实模型续办证据。本次受限真实核对与 UI 修改见
[DR-0075 Evidence](evidence/DR-0075-DEMO1-CLARITY-20261010.md)。文件生成、Run 终态、
模型解释采用、业务批准分别汇报；原系统和 Swarm 保留，不另立演示产品。

## 2026-10-08 工作区减法

续增：原资料库执行区按需展示普通历史、材料、已完成分支和版本，不再重复完整目标。
异常、未完成分支与控制仍保留；这是信息分层，不是新调度能力。见 [DR-0074](decisions/DR-0074-execution-detail-disclosure.md)。

在原系统落实 nanoMuse 研究中“辅助信息按需展示”的原则：过程记录、目录和已提交任务设置
不再同时占满页面，原待办、错误、成果与 Loop/Swarm 不变。这是本项目原创前端改动，
不是复制组件、完整竞品改造或已证明用户效率提升。见 [DR-0073 验证](evidence/DR-0073-FOCUSED-WORKSPACE-20261008.md)。

## 2026-10-07 统一工作台整合口径

主线是“在同一办公任务工作台读取资料、观察执行、处理需要人的决定”，不是三个独立产品。
远程六类单步事项和本地 Loop/Swarm 优化均保留；本轮计划收敛入口并隔离旧请求的迟到响应。
当前合同为 [DR-0072 Limited Verified](decisions/DR-0072-unified-workbench-and-response-ownership.md)，
仅限统一入口、已测迟到响应隔离及共存。后端最终单次 573 passed、26 个 PG 条件跳过；浏览器
147 项门后又发现并修复两项导航竞态，单独 2 项通过，随后最终单次组合门 149 项通过；末次类型检查、webpack 构建和全库 Ruff 均通过。失败历史仍保留，不是加总旧数字。
准确进度及截图引用[本轮证据](evidence/DR-0072-INTEGRATION-20261007.md)。
材料对照的人工判断记录，不等于 Worker 歧义已解决；后者到贡献采用、依赖解除和下游执行尚待另期验证。

## Demo3 当前可展示范围（2026-09-19）

Demo1 讨论时间维持续执行与局部续办，Demo2 讨论受限工作包分工与贡献采用，Demo3 展示同一工作台中的
不同单步事项。当前有六种固定规则处理：个人文本整理可撤销、资料摘录留草稿、
协作任务普通确认、发件强确认、受限动作停止，以及材料对照后的人工判断记录。
摘录可原位编辑，暂缓事项可从最近记录找回，受限事项可下载交接说明。任务与发件只保存测试记录，
未创建真实企业任务、未发送邮件、未接审批、未调用模型。

提交版包含设计手册和 13 个结构化案例，开发版逐项标明实现及未覆盖部分。
已有方案自查和工程验证，尚无设计方正式评审或目标用户研究；不能声称边界分级
已获业务批准、用户体验提升、生产分布式 Worker 或通用 Risk Gate 已实现。原系统已有每波最多三个、显式确认的进程内只读 Worker，不应再写成完全没有多 Worker。
见 [Demo3 设计与评审](design/DEMO3-DEVELOPMENT-HANDBOOK-20260918.md)。
## 2026-09-22 只读任务质量补强

在原 Loop/Swarm 路径增加固定产品计数核对，历史两条已采用错误现在可被拦住，且不生成用户
禁止的文件。补齐此次交互表 212 行及两份搜索文件输入，保留原预览与分层界面。两次真实复跑
共 9 次模型调用，第二次产品计数/比例与来源一致，但另两分支仍有重复引用，下游未执行。
必须说“修复部分已知质量缺口”，不能说“五项完整协作验收通过”。[报告](reports/demo12-source-checks-20260922/README.md)。

## 2026-09-22 成果与独立验收

在原系统进一步收起引用和财务长口径，待决、文件用途和真实业务边界保留。实际跑了财务与
跨领域协作两个任务，共 8 次模型调用；财务三份下载文件独立复算通过。跨领域仍等待，且
保存分析里有 P0/提测数量错误，必须讲为未通过结论验收，不能拿引用定位证明正确。
受控测试验证局部失败、保留成果及原接口续办，不是真实模型恢复成功率。见
[报告与原始失败证据](reports/demo12-outcomes-20260922/README.md)。未新增真人试用或蜂群优势证据。

## 2026-09-22 前台减法

在原系统内走查输入、待办、成果和协作，合并重复信息并把低频细节收起。成果和历史直接打开，
协作先看分工图，必要核对不被隐藏。可讲源码、明确用例和当前工程回归；不能讲真人已经看懂、
效率提升或误批减少。见 [走查记录](reports/demo12-simple-20260922/README.md)，不是独立新 Demo。

## 2026-09-22 研究驱动的四条改进

[最新简报与验收](reports/demo12-research-20260922/README.md) 和
[8 篇正式论文地图](research/HUMAN-AGENT-TOP-VENUE-TO-DEMO12-20260922.md) 对应原系统的输出约定、
有界单包修复、前序逐项核对、交付/待办展示。可以讲工程门、保留成果和模型分歧，不可讲论文
训练复现、独立语义验证、人类业务裁决闭环或蜂群收益已证实。新机制本轮没有真实 Provider 或
真人试用结果；现有 Loop/Swarm 继续保留，不另做产品，Demo3 接入约定不变。

## 下一次会议简稿

优先使用 [三个 Demo、八个边界案例与蜂群差异简稿](reports/DEMO123-BOUNDARIES-AND-SWARM-BRIEF-20260912.md)，不制作新 PPT 或演示网站。主线是“Demo1 接着做，Demo2 分工与采用，Demo3 定义谁能决定什么”。原能力页已增加既有边界解释和协作回执事实，保留 Loop/Swarm；这只是第一部分前端整合，不是 Demo3 全场景闭环或业务授权。研究 HTML 不替代产品，离线测试不证明集成通过。蜂群是受限 orchestrator-worker，其贡献采用与局部恢复组合是可证伪工程差异候选，不是已证明的新算法或竞品优势。[本轮 Evidence](evidence/DR-0063-INTEGRATED-BOUNDARIES-AND-SWARM-FACTS-20260912.md) 单列验证范围。

## 动态边界研究增量（2026-09-11）

[研究与可操作原型](reports/copilot-boundary-design-20260911/index.html) 不以 L0-L5/R0-R3 作为设计约束。
可讲：比较具体授权、澄清、失效、对账与接管的交互差异，研究中保留“少提示未带来更强越界保护”的反证。
不可讲：有界授权已经优于逐动作确认，已完成目标用户实验，或当前具备真实审批/外部动作能力。
[DR-0062](decisions/DR-0062-dynamic-boundary-design-experiment.md) 和 [SCENARIO-049](scenarios/SCENARIO-049-dynamic-boundary-handoff-design.md)
仍为 Draft；场景与来源、前台交互影响、后端事实映射、验证与边界分别记账。

2026-09-12 [用户理解迭代](reports/copilot-boundary-design-20260911/usability-review-20260912.md) 把“当前结果、原因、下一步后果”与工程术语分开，增加旧/新附件对照、未知查询失败路径和五个非诱导任务。可讲实际源码问题与测试，不可讲目标用户已经看懂；没有参与者结果，最终浏览器门也未完成。

2026-09-12 [下一轮阅读推荐](reports/copilot-boundary-design-20260911/research/followup-20260912/recommendations.md) 增加 6 篇论文和 3 篇官方实践。可讲“共同参与不只是审批”，以及参与过多、主观信任未校准和检查成本的反例；不可讲本项目已完成共同计划编辑、自动权限分类或真人效果对照。合成用户评估、开发者样本与普通办公人员不能混称。

## 2026-09-11 会议材料

[Demo 1/2 重设计 HTML](reports/demo12-redesign-20260911/index.html) 对照用户参考与真实前端截图。
可讲：同一任务的循环进展、按轮记录、WorkUnit 依赖、显式协作确认、候选位置选择与局部保留。
不可讲：截图等于真实模型任务成功、图等于分布式 Swarm、已有风险引擎或通用审批系统。
[人机共驾手册](reports/human-agent-copilot-20260911/guide.md)、
[8 案例沙盘](reports/human-agent-copilot-20260911/index.html) 和
[Demo 3 简报](reports/human-agent-copilot-20260911/report.html) 为 `Draft`，浏览器验证限制明确保留。
三个 Demo 完成后的完整行业回溯仍是后续门，不由本轮定向引用替代。
场景与来源、前台交互影响、后端事实映射、验证与边界见
[DR-0061](decisions/DR-0061-reference-aligned-capabilities-and-evidence-choice.md)。

后续 [主动验收报告](reports/demo12-acceptance-20260911/index.html) 记录真实 Provider 单任务与 91 项受控回归。
两个 UI 问题已修复；真实日志任务的完整性未通过，模型输入截断前半段但摘要未限定范围。
会上应展示这个失败案例，不得以调用回执、引用定位或全绿 E2E 代替全文业务正确性。

[第二轮打磨报告](reports/demo12-polish-20260911/index.html) 展示长目标、空白任务、确认区可达性和自测迭代。
[人机共驾研究资料库](reports/copilot-research-library-20260911/index.html) 提供论文、官方文档/博客、
研究限制及 Demo 设计映射。可以讲适当依赖、核验成本与接管后的恢复粒度；不能讲“人机组合必然更好”、
“增加解释必然减少过度依赖”或“有审批接口就等于权限安全”。风险分层与交互方案仍待目标用户验证。

本文件记录面向会议、PPT 和产品评审的中文表述。英文只保留产品名、
接口名、协议字段和原始来源标题。

## 1. 一句话定位

我们不是在制作三套写死的 Demo，而是在建设一个证据编译型 Office Agent
Harness：用户只给业务目标，Agent 在完整资料库中自主找证据，但模型候选必须
经过服务端范围、计划和来源位置校验才能进入不可覆盖的逻辑成果；十二个固定
本地能力还能生成隔离 Run Workspace 文件并接受确定性复核。最终仍明确待复核、
没有修改 FORTE 原件、没有执行外部动作。

## 2. 汇报硬门槛

每个架构、Demo 或产品结论必须同时回答：

1. 用户是谁，在什么办公场景下触发，异常路径是什么；
2. 设计来源是什么，Source ID、日期或版本、支持判断和局限是什么；
3. 与主流方案相比，技术侧重点有什么不同；
4. 这种技术差异怎样改变用户交互流程；
5. 前台显示什么状态、提供什么动作、如何反馈和恢复；
6. 每个 UI 状态由哪个后端事实产生，哪些内部细节默认隐藏；
7. 当前 Evidence 状态是什么，还有哪些结论只能标为 `Draft`。

完整门槛遵循
[`DECISION_AND_REPORTING_GOVERNANCE.md`](DECISION_AND_REPORTING_GOVERNANCE.md)。
汇报必须同时保留“场景与来源”“前台交互影响”“后端事实映射”和
“验证与边界”。研究来源包见
[`WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825`](research/WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825.md)。
Agent Control Loop 的逐模块历史基线、当前有界效果纵切和后续缺口见
[`AGENT-CONTROL-LOOP-IMPLEMENTATION-AUDIT-20260825`](research/AGENT-CONTROL-LOOP-IMPLEMENTATION-AUDIT-20260825.md)。
完整的项目化讲稿、七个办公场景、七个图示区和 17 页 PPT 结构见
[`OFFICE-AGENT-DETAILED-CHINESE-REPORT-20260825`](reports/OFFICE-AGENT-DETAILED-CHINESE-REPORT-20260825.md)。
最新“为什么必须选我们”的候选能力、八个竞品同场挑战和官方来源见
[`COMPETITIVE-WHITE-SPACE-AND-FALSIFIABLE-DIFFERENTIATORS-20260826`](research/COMPETITIVE-WHITE-SPACE-AND-FALSIFIABLE-DIFFERENTIATORS-20260826.md)。
07-16 Demo 1 时间维连续性与 Demo 2 组织维复杂性的下一阶段研究、八个场景、主流基线
和交互影响见
[`DEMO1-DEMO2-DURABLE-TASK-AND-ADAPTIVE-ORCHESTRATION-RESEARCH-20260830`](research/DEMO1-DEMO2-DURABLE-TASK-AND-ADAPTIVE-ORCHESTRATION-RESEARCH-20260830.md)；
跨 Run Task lineage 与受限进程内只读 Worker 已形成 `Limited Verified` 纵切，
工程 Evidence 见
[`DR-0053-DEMO1-DEMO2-RUNTIME-EVIDENCE-20260831`](evidence/DR-0053-DEMO1-DEMO2-RUNTIME-EVIDENCE-20260831.md)。
`DR-0054` 又把 Demo 1 的 lineage 升级为最小 owner-scoped Task Ledger/current pointer，
工程 Evidence 见
[`DR-0054-TASK-LEDGER-V1-EVIDENCE-20260831`](evidence/DR-0054-TASK-LEDGER-V1-EVIDENCE-20260831.md)。
`DR-0055` 又把 Demo 2 的 Branch Worker 升级为最小 WorkUnit/Contribution 台账，
工程 Evidence 见
[`DR-0055-WORKUNIT-CONTRIBUTION-LEDGER-V1-EVIDENCE-20260831`](evidence/DR-0055-WORKUNIT-CONTRIBUTION-LEDGER-V1-EVIDENCE-20260831.md)。
`DR-0056` 先把两个镜头从一条长页面中拆开：最近 Run 按 `task_id` 分成任务会话，并形成
独立全屏 Adaptive Swarm 工作台。该工程 Evidence 仍有效，但 `DR-0057` 纠正了产品解释：
Workspace 是办公工作面；新的 `/agent-capabilities` 把 Agent Control Loop 与 Adaptive Swarm
作为同一 Agent 的时间维和组织维能力，共用同一个 Task/Run/Snapshot。`DR-0058` 又把首版
两块完整面同屏改为四条直接路径：默认任务进展、按需完整执行记录、单独协作方式和专注
原文核对。它们不是四级连续导航，也不是四套 Runtime。07-16 Demo 2 仍是后续单独实现的
“智能工作驾驶舱”，Adaptive Swarm 只是它按需选择的一条路线。本轮不画假任务队列，也不
把能力页或旧 dialog 说成驾驶舱已经完成。这个分层只改变前台投影；历史 Run 只读且不接
SSE，当前 Worker 仍是单进程受限只读实现。Adaptive 正例的协作页现在进一步用左侧阶段
轨、中央真实 WorkUnit DAG、右侧当前影响和底部成果条解释“为什么拆、谁依赖谁、哪里
停、什么已经保留”；父子关系用方向连线表达，当前轮 `ready_branch_ids` 统一显示为“下一
波待确认 / 可执行”，主要确认动作放在右侧当前影响区；Fixed/Single 不画假 DAG。
`DR-0060` 补上两个页面共同的“新建任务”入口：点击只退出当前 Run 投影并进入空白草稿，
不创建空 Task、不停止旧 Run；提交指令后才由现有 start 协议创建独立 Task。旧任务仍可从
任务会话返回，相同文字的新任务也使用新的幂等键。
Task/WorkUnit 的隔离 PostgreSQL 17.11 单主机顺序门已经通过，但 Provider 同场、多实例、
远端 Worker 与用户研究仍未完成，不能写成生产级 Task 服务或通用/分布式 Worker。
十五条场景的实际效果、失败修复轨迹、真实模型运行和外部边界见
[`SCENARIO-EFFECT-GATE-20260827`](evidence/SCENARIO-EFFECT-GATE-20260827.md)
与[中文效果账本](reports/SCENARIO-EFFECT-GATE-LEDGER-20260827.md)。

## 3. PPT 页面卡片

| 页码 | 中文结论 | 建议画面 | 证据与边界 |
| --- | --- | --- | --- |
| 1 | Office Agent 从一个可逐级展开的统一办公资料库开始，而不是从 Demo 或职业按钮开始 | 15 个顶层目录、嵌套子目录与文件预览同屏截图 | `DR-0028/24`；目录来自安全路径投影，公开基准数据不是真实企业网盘 |
| 2 | 真正的问题不是缺少聊天框，而是上下文不可见、执行过程不可核对 | 旧流程与文件夹优先流程对比 | Stakeholder 反馈，不是用户研究 |
| 3 | 一个 Runtime、八个通用模块、三种验收视角 | 长任务拆分、多任务规划、不同简单事项的单步办理 | 当前能力与目标能力必须用不同颜色 |
| 4 | 整库、多来源、引用、计划、暂停、恢复和知识成果已经是主流基线；我们的候选差异是“结论采用由服务端裁决” | Microsoft 365 Copilot、NotebookLM、deep research、Codex、Claude、OpenClaw 的能力底线汇入证据采用合同 | 官方文档研究，不是竞品实测；独占结论必须通过同场挑战 |
| 5 | 用户给目标，Agent 负责从整库找证据，但选择过程必须可见、可限、可复核 | 浏览 -> 下达目标 -> Agent 选证据 -> 观察 -> 引用 -> 复核 | 实现侧重点差异，不是优越性结论 |
| 6 | 固定公开数据版本，让演示中的每份材料都能被现场检查 | 15 个文件夹、96 份文件、格式分布 | FORTE 固定 commit；不是真实企业数据 |
| 7 | 安全预览把“Agent 读了什么”变成可见契约 | CSV/PDF/DOCX/TXT 预览拼图和安全说明 | 路径、大小、hash、符号链接和解析器测试 |
| 8 | Harness 把模型调用、内容采用、确定性办公效果和整体 Loop 状态分开 | 事件、模型回执、可下载工件与检查结果时序 | Snapshot/Receipt/Artifact 事实；不展示思维链，也不把 `completed` 当作效果通过 |
| 9 | Agent 说“有问题”之后，用户要同时看懂事实、影响、真实原文和自己必须决定的下一步 | 问题处置单：1 事实 -> 2 影响 -> 3 人工动作；证据与实际文件并排；A/B/C + 反馈 | `DR-0030/29`；推荐是模型候选，确认只创建新只读 Run |
| 10 | Demo 1 把一次 Run 的停止变成同一 Task 的下一段执行，同时允许用户显式开始另一项独立工作；最近记录按 `task_id` 隔离成任务会话，Task Ledger 再决定打开的 child 是否为当前工作面 | “新建任务”空白草稿、任务会话抽屉、Run 1→Run 2、全局“历史 Run 只读”、当前非终态 Run 才恢复 SSE、基线成果与来源变化提示 | `DR-0053/54/56/60`、`SCENARIO-038/040/043/047`；点击新建不创建空 Task 或停止旧 Run，提交后才创建；会话发现只覆盖最近 20 个 Run，不是无限 Task list；child 是新 Run，Run version 可从 1 开始 |
| 11 | 先把 Agent 能力与 Demo 产品面说清：能力页用同一 Snapshot 回答“任务怎样跨 Run 继续”和“复杂任务怎样拆解协作”，但默认先回答“现在进展如何、是否需要我处理”；07-16 Demo 2 智能工作驾驶舱仍是下一阶段产品面 | `/agent-capabilities` 实际界面四镜头：任务进展、完整执行记录、协作方式、确认结论依据；协作镜头用左侧阶段轨、3 root+2 dependent 动态 DAG、右侧当前影响和底部成果条展示实际来源、Worker called/adopted/elapsed、Contribution Gate、v1/v2；旁注未来驾驶舱队列与四路线，不画成当前截图 | `DR-0053/55/57/58`、`SCENARIO-039/041/042/044/045`；四层是同一 Snapshot 的渐进披露；当前每批最多 3 个进程内只读 Analyst Worker；没有驾驶舱队列、跨 Task dispatch、durable queue/lease、分布式 Swarm、用户研究或质量收益证明 |
| 12 | Demo 3 对单任务和多任务统一施加风险与动作控制 | 影响预演 -> 证据 -> 审批 -> Permit -> 回执 | 目标设计；当前没有真实外部动作 |
| 13 | 当前 12 个本地 FORTE 场景已有真实隔离工件与确定性验证；3 个外部依赖场景明确阻断 | 12 通过、3 `blocked_external_boundary` 的效果账本；六个真实 `deepseek-v4-pro` 运行 | `DR-0035` 限定能力，不等于任意办公任务或用户价值；模型质量、效果验证、Loop 终态分开报告 |
| 14 | 历史约 30% 审计基线已升级为可见分支、最小 Task Ledger/current pointer、Branch 绑定的 WorkUnit/Contribution 台账、跨 Run 谱系、可解释拓扑、受限 Worker、可恢复逻辑成果和固定本地可写工件；下一步是 queue/lease、通用 Tool Gateway、分布式 Worker 与外部动作治理 | Task record→current Run→Branch/WorkUnit→Contribution→ArtifactVersion 的当前链路、Topology Admission、Run Workspace Artifact 与 Demo 3 目标架构叠加图 | `30%` 只代表历史基线；当前 WorkUnit 台账不是 durable queue/lease，Worker 与真实工件仍受限于单进程/固定适配器 |
| 15 | 同一个任务可以“成果已通过、Agent 审计说明仍待修复”；用户必须先知道成果能否用，再决定是否处理引用位置 | TC-01 5/5 成果在前、两个同源 Gap 合并为一个审计项；PDF “技术/研发”断行修复前后 | `DR-0036`；Artifact 通过不等于 Run completed，Anchor 仍不证明语义正确 |
| 16 | 成果文件必须在下载前说清“哪个期间、怎么算、拿来做什么” | TC-05 三张成果卡：两个 2026 明细与一个三期核对说明；问题审查页字号修复前后 | `DR-0037`；内容来源与任务上下文分开，Finance-018 仍是固定适配器；自动化不证明用户理解 |
| 17 | 一个引用跳转缺口不应被包装成系统失败：先说成果是否已生成，再给一个动作 | TC-05 “成果已生成，还有 1 条说明缺少原表格位置”；查看成果、查找位置、技术详情三层 | `DR-0038`；只恢复目标 Branch，不覆盖 Artifact；未通过和旧 Run 使用不同话术 |
| 18 | 代码测试的关键不是绿灯数字，而是同一套测试能否先抓住原缺陷、再验证修复 | TC-12 Stage A/B/C 红灯 -> Stage D 71/71；三套真实测试、四文件 diff、逐文件 coverage 与下载复跑 | `DR-0042`；固定 qa-003 适配器，不是任意 JS 沙箱、自动 PR 或 OS 级断网 |
| 19 | 一个任务可以“成果文件检查通过，但业务结论仍是不通过”；前台必须同时讲清两种真相 | TC-11 两份 Artifact 共享 9 项确定性检查，同时四条来源推导上线 Gate 全失败；首屏“不得上线”+公式，辅助指标和 18 项台账渐进展开 | `DR-0043`；固定 pm-014 适配器，不执行上线、不改配置；自动化不证明用户理解 |
| 20 | 简历辅助筛选不能把“没写到”变成“不满足”，也不能让绿色文件检查替 HR 作决定 | TC-06 首屏三状态、110 条双来源条件、王琳达人工例外、孙博文 8 个月与 1 年门槛、动态来源变异 | `DR-0045`；固定 hr-001 适配器，不是通用 ATS、正式招聘决定、公平性证明或候选人通知 |
| 21 | 业务上发现风险候选不等于系统失败，也不等于系统已经做出会计决定 | TC-05 三状态首屏、0 候选基线与 1 候选来源变体、三期 Excel locator、三份下载物 | `DR-0046`；固定 Finance-018 精确余额启发式，不是通用总账、僵尸账款定论、付款/核销/记账或坏账确认 |
| 22 | 一份流程图可以结构正确，但仍未获得合规审批，更不代表已经执行 | TC-10 四状态首屏、来源行到节点/边/守卫的映射、身份在录音与欠款前、动态时段/频次变体、DOCX 六类表格 | `DR-0047`；固定 Operations-008 流程设计适配器，不是外呼系统、最新监管验证、法律意见、拨号/CRM/短信或生产审批 |
| 23 | 客户画像文件可以计算正确，但重复口径仍是假设、销售策略仍是草案，也没有发生任何客户动作 | TC-13 四层首屏、11 个逐行清洗记录、0 个 canonical 优先级 witness、多标签动态变体、两份可下载成果 | `DR-0049`；固定 Sales-020 公开样本适配器，不是真实客户研究、销售效果证明、CRM、自动营销或通用分群引擎 |
| 24 | SRE 报告可以结构正确，同时保留来源矛盾、根因不确定和“所有动作尚未发生” | TC-14 四层首屏、三组来源冲突、支持/反证链、未解析 endpoint、只读预检与条件式写提案、两份可下载成果 | `DR-0050`；固定 SRE-010 离线复盘适配器，不是在线监控、根因定论、Elasticsearch Connector、命令执行或生产审批 |
| 25 | Agent 不应拿一小段 Preview 冒充整份日志，也不应只列全局规则让用户自己猜“为何这样排” | TC-15 212/212 全量覆盖、旧 66 组对新 87 组、逐组 contributors 与内容寻址 rule refs、3% 冲突、两份 CSV、方案/生产动作未发生 | `DR-0051`；固定 uiux-021 离线排序适配器，不是用户研究、线上遥测、设计效果证明、自动修复或发布 |
| 26 | 模型返回不等于模型说明可成为当前结论 | 先展示 212/212 的服务端成果，再展开历史“只看 60 行/P0 改 P1”冲突；新协议保留 Artifact、拒绝错误说明并让前台只剩一个当前结论 | `DR-0052`；只证明叙事与结构化事实一致性，不证明语义全面、方案有效或体验改善 |

## 4. 现场演示卡片

1. 直接打开 `/`，进入“办公资料库”。
2. 从左侧文件夹逐级展开顶层目录和嵌套子目录，也可搜索或按类型筛选；打开文件并强调浏览不会限制 Agent 范围。
3. 不勾选文件，只输入一个现场提出的新目标，并设置轮次、每轮文件、模型调用和 Agent 执行时间；说明默认 `12/16/30/7200`，人工阅读和暂停不计入 active 时间。
4. 启动 Loop，指出合同已冻结完整 96 文件索引；Planner 与 Analyst 的独立模型回执才是调用事实。
5. 展示 Agent 本轮选择了哪些文件、为什么选择，以及服务端如何把超预算候选限制在本轮上限内。
6. 在 Evidence Gate 停下来，先让观众读 Branch 总览中的两类动作：普通缺口标“无需核对文件，建议重试”，点开后首屏只有“继续任务，只重试此分支”；额外线索和停下原因默认折叠。关闭审查页应立即返回 Loop；即使 defer 回执冲突也不能把用户困在弹窗。
7. 展示成果简报从 v1 到 v2；再恢复 v1，说明系统只新增一条 TaskCommit、当前指针改变，v2 与原文件都没有被覆盖。
8. 对 Finding 点“打开审查页”：先按 1/2/3 讲事实、影响和人工动作，再在左侧选择“设计预期/实际观测”，让右侧真实文件跳到并高亮原文；强调位置匹配不等于结论正确。
9. 先选择 A/B/C 中自己的初始口径，再点“对照 Agent 建议”；补充“同时核对发布记录中的代码版本”后确认。指出推荐默认隐藏以减少锚定，确认只创建新只读 Loop，不会直接改源文件。
10. 再展示一次 ambiguous 恢复态：首屏只回答为什么需要人、从几个真实位置中选哪一个、选择后只恢复哪条 Branch；不预选候选，未选择前主按钮禁用。若预算已到 `stopped/bounded`，明确说明旧 Run 不可继续，并用一条 Branch 创建新的独立任务。
11. 运行 TC-05：先让观众不下载文件，直接从三张卡读出期间、统计口径、用途与动态记录数；说明两个 CSV 只来自 2026，三期来源与候选比较只属于说明。先展示当前 0 候选的“仍需财务复核”，再用批准来源变体展示 1 条候选仍为计算通过、但以琥珀色等待人工处置。展开三期 locator，说明系统没有付款、核销、记账或确认坏账。最后展示模型调用/采用、隔离工件、逐项确定性检查和下载按钮；随后展示 TC-03/08/09 的外部边界回执，证明系统没有伪造 SQL/Web/cron。
12. 对建议点“查看形成依据”，说明建议尚未逐项绑定引用；只有点击“确认并启动”才创建新 Loop。
13. 运行 TC-12：先展示历史 9/9 为什么不足，再在两份成果中依次指出 Stage A/B/C 的真实红灯、Stage D 71/71、23/20/28 三套公开测试和三个逐文件 coverage。下载 ZIP 后按自测卡复跑，强调系统修改的是隔离副本，最终仍由人审查 `changes.patch` 并决定是否合并。
13. 展示 TC-01 的负例与修复：原页面已有可下载 CSV，却把同一 PDF 定位缺口重复成两个“重试分支”；新页面先显示 5/5 成果，再把它合并成一个“不影响成果”的审计项。随后说明新 Run 会直接容忍 PDF 版面断行、过滤 4 月 20 日之后的候选，并取消没有矛盾 Anchor 的人工阻塞。
14. 展示 TC-05 的来源位置缺口：先读“成果已生成”和已知工作簿，再点“查看已生成成果”；返回后点“查找原表格位置”，只恢复受影响 Branch。最后展开“技术详情”说明审计事实仍保留，但普通用户不必先理解 Branch/Gap/Resolution。

演示不要从八模块架构图开始。先让观众看到数据、任务、轨迹和证据闭环，
再解释支撑它的架构。

## 5. 主流方案对比卡片

### 办公与研究型竞品底线

- Microsoft 365 Copilot 可以引用文件、文件夹、站点、邮件、会议和工作内容，Copilot Chat
  提供内联引用与来源侧栏，Copilot Notebooks 可用数百个 References。
- NotebookLM（当前官方帮助页重定向为 Gemini Notebook）、ChatGPT deep research 和
  Claude Research 都已提供多来源带引用研究；ChatGPT deep research 还允许审查计划、
  查看进度和中途调整。
- 因此“96 份文件、自动找资料、有引用、能暂停”都不能单独作为独占点。汇报必须转向
  Finding 怎样被服务端采用、成果版本如何保存、完成边界是否可验证。

### OpenClaw

- 官方资料重点：自托管 Gateway、Channel、Session、Routing、Tool 和主机执行审批。
- 我们的侧重点：把一个服务端拥有的办公资料库、Agent 选证据的理由和引用放到第一屏。
- 交互影响：用户可以先检查数据，但不必先完成检索；提交目标后再监督 Agent 如何缩小范围。

### Codex App

- 官方资料重点：并行项目任务、隔离工作区、结果审查、Skill 和 Automation；2026 年已明确
  扩展到报告、表格、演示文稿、合同、研究和跨职能知识工作。
- 我们的侧重点：办公文件是只读业务证据，计划与结果需要回到 Agent 实际采用的文件核对。
- 交互影响：用户主要审查业务结论的采用回执、证据和版本，而不只审产出文件或 Diff。

### Claude Code

- 官方资料重点：项目目录上下文、Agent/Tool Loop、Subagent、Permission Mode 和多种开发界面。
- 我们的侧重点：模型可检索完整安全索引，但每轮正文访问由服务端预算和校验约束，不能静默读取所有内容。
- 交互影响：用户少做一次手工范围选择，改为在执行中查看“选了什么、为什么选、是否被采用”。

### ReAct 与当前 Office Agent

- ReAct 启发：以 Reasoning、Action、Observation 交替组织执行轨迹。
- 当前落地：普通前台只展示模型调用、业务操作、服务端校验、回执和引用，不暴露私有思维链。
- 用户流程：浏览 -> 下达目标 -> Agent 自主选证据 -> 查看轨迹 -> 打开引用 -> 确认下一步。
- TC-02 当前只证明真实 algorithm-013 副本具备有界、可插拔的 ReAct 控制结构。默认策略确定性执行已规划工具；没有证明模型依据 Observation 在副本内自主选动作。外层 `deepseek-v4-pro` Planner/Analyst 回执必须单列，不能当作下载代码包内部策略。

不能表述为“竞品没有这些能力”或“本方案优于竞品”。官方文档不是受控竞品测试，
引用页面没有提及某项能力，也不能证明产品绝对不具备它。只有固定产品版本、账户、入口、
允许配置和同一 FORTE 挑战的真实失败记录，才能限定地写“该配置当前不能完成”。

### 当前可证伪独占候选

- 冻结完整 96 份安全索引，同时让 Analyst 每轮只读服务端批准的 1-24 份正文投影；默认上限 16。
- Planner/Analyst 的 `called`、`output_used`、`elapsed_ms` 分开，模型真实返回也可能被服务端拒绝。
- 每条进入成果的 Finding 必须有批准 `file_ref` 内的服务端 Evidence Anchor；引用是采用门，
  不是生成后的装饰。
- 证据简报按 append-only `ArtifactVersion` 演进，`TaskCommit` 只选择当前版本，恢复不覆盖新版。
- `completed` 仍固定 `review_required=true`、`external_action=none`，完成页同时证明待复核和未执行。
- 十二个固定本地办公能力额外要求真实 Run Workspace bytes、服务端确定性 validator 和
  EffectReceipt；模型文本、引用或 `completed` 都不能替代效果门。

这些是本项目当前原生保证的组合，但还不是“已验证独占”。下一步用不知道资料位置、跨文件
冲突、重复 quote、部分分支失败、完整性失败、成果恢复、混合执行指令和外部数据缺失八个
场景做同场挑战。

## 6. 技术差异到交互影响卡片

| 技术选择 | 用户流程变化 | 前台输出 | 后端事实 |
| --- | --- | --- | --- |
| 服务端拥有完整文件目录与安全展示路径 | 用户可以逐级找文件，也可先浏览再提问 | 顶层文件夹、嵌套子目录、文件信息、可用状态 | `GET /v1/harness/workspace` 的 `folders[]/display_path` |
| 整库合同 + 每轮自主选证据 | 用户不用先猜文件，但能监督 Agent 缩小范围 | 96 文件统一检索、本轮文件与选择理由 | `scope_mode`、`allowed_file_refs`、`round.input_file_refs` |
| 有界格式适配器 | 不执行文件也能检查证据 | 表格/文档预览和安全说明 | 文件预览路由与完整性校验 |
| 模型之后还有策略编译器 | 模型不能静默决定副作用 | “模型已调用”与“计划已校验”分开 | Model Receipt 与服务端 Plan |
| 固定本地 Scenario Effect Gate | 用户看到的“已完成”必须落到真实文件和可复算检查，而不是一段模型回答 | 可下载 CSV/MD/DOCX/ZIP、检查清单、原件未修改、外部动作未发生 | `workspace_artifacts[]`、`effect_receipts[]`、Artifact GET 与 named SSE |
| 来源推导法务核查与三状态反馈 | 用户不再把固定风险答案或绿色文件检查误读为“可以签署”，还能逐份查看哪条规则已触发、哪条只因资料不足无法判断 | “不得据此签署，必须法务复核”、文件检查/法务 Gate/签署复核三状态、六份文件的 21 条规则台账 | `legal_review_outcome.documents[].assessments[]` + `business_gate_outcome` + Artifact `verifier_status`；固定 Legal-020，不是正式法律意见或签署验证 |
| 来源推导招聘辅助与 HR 决策边界 | 用户不再把缺失简历字段误读成不满足，也不会把文件验证通过误读成录用或淘汰 | “人工复核建议，不是录用或淘汰决定”、来源检查/岗位建议/HR 待决三状态、按岗位与候选人展开双来源条件 | `candidate_review_outcome.reviews[].assessments[]` + Artifact `verifier_status` + EffectReceipt `external_action=none`；固定 hr-001，不证明公平或正式招聘决定 |
| 设计成果与执行回执分层 | 用户不会把流程文档中的动作词误读为 Agent 已经拨号或写系统 | “只生成流程设计 DOCX”、六类终态、人工复核原因、未拨号/未写 CRM/未发短信 | Artifact `deliverable_type/key_outputs/review_guidance/execution_summary` + EffectReceipt `external_action=none` |
| 真实代码副本与自测分层 | 用户能区分“改造真实项目”与“另造一个演示包”，并知道如何复测和人工合并 | 完整 algorithm-013 副本、文件变更、两条命令、测试 ID 清单、失败信号 | Artifact `self_test/key_outputs_label` + ZIP/diff/JSON receipt + download content gate |
| 双阶段真实项目测试 | 用户不再被“105 项通过”蒙蔽，能看到真实模块、修复前红灯和修复后覆盖门 | dev-015 完整 44 文件副本、五类 117 项可展开测试、三处 diff、逐文件覆盖率 | Artifact `test_suites[]` + unpatched/final results + public/ZIP manifest 集合一致门 |
| 长测试移出 API 事件循环 | 用户等待约一分钟时仍能看资料、Run 状态和真实轨迹，不会因为一个 builder 让整个服务像离线 | “正在复制并运行真实测试”、完成/失败事实，无虚构百分比 | 46 份输入冻结 + `asyncio.to_thread` + `deterministic_office_tool_started/scenario_effect_failed`；不是多 Worker 或可恢复 Tool Gateway |
| 外部依赖显式阻断 | 用户不会把缺 Connector/权限的安全停止误读为任务成功 | `blocked_external_boundary`、缺失依赖与禁止副作用 | EffectReceipt + `scenario_effect_bounded`；不生成伪 Artifact |
| 有序事件加权威 Snapshot | 进度和恢复依据事实 | 轨迹、重连中、最终对账 | named SSE 与 Run Snapshot |
| 引用范围校验 + 问题审查页 | 用户不用在缺口卡和 96 份文件之间来回猜，可以从问题直接对照原文 | 轮次/分支定位、审查记录、关联文件、安全预览 | Gap/Branch/Finding refs + Preview GET；不等于语义正确 |
| 服务端 Evidence Anchor | 用户不用在整份代码、日志或表格中手工搜索 Agent 的依据，可以在预期与观测之间逐项切换 | 编号证据链、证据角色、行范围、原文摘录、自动跳转与高亮 | Finding `evidence_anchors[]` + Preview GET；模型 quote 需唯一匹配，位置不等于 entailment |
| 结构化问题处置单 | 用户不用从一段长解释中自行提炼事实、影响和操作 | 1/2/3 摘要、是否需要人工决断 | Finding `fact_summary/impact/review`；不证明模型判断正确 |
| 人工处理选项与反馈 | 用户能明确告诉 Agent 接受、否决还是暂缓，采用哪种口径，还要核对什么 | A/B/C、影响预演、反馈框、决定回执 | `decision_records[]` + 新 Run POST；当前没有文件写入或外部动作 |
| 终态仍要求复核 | 完成不等于正确 | “模型初步结论 · 待复核” | `review_required=true` |
| 服务端 Evidence Gate | 验证结果可决定继续还是停止 | 本轮缺口、下一轮目的、剩余预算 | `rounds[].evidence_gaps` 与 `next_step` |
| 成果与说明位置分层 | 用户先判断真实文件是否已生成，再看 Agent 说明是否能回开原表格 | “成果已生成，还有 N 条说明缺少原表格位置”、查看成果、查找位置、技术详情 | passed Artifact/EffectReceipt + waiting `source_location` Gap；客户端合并不改 Branch，不等于 Run completed |
| 轮次间人工证据门 | 证据不足时由人决定是否继续花预算 | “确认并继续核对”、调整方向或停止 | `status=waiting_input`、`control_state=paused`、resume 回执 |
| active deadline | 用户阅读、开会或暂停时不会把 Agent 预算烧光 | “Agent 执行时间”、已用 active 秒数、精确停止原因 | 默认 7200 秒、上限 14400 秒；`budget.elapsed_ms/stop_reason`，waiting/pause 冻结 |
| Agent 自有缺口处置 | 用户不再被要求替 Agent 猜行号或修改候选文件 | 原目标、尝试文件、模型调用/采用、保留项、无外部动作、只重试本分支 | `recovery_kind` + Branch/Gap + model receipt；无 Anchor 不高亮 |
| 两类待处理分流 | 用户先知道自己只是授权 Agent 重试，还是必须提供一个原文位置判断 | “无需核对文件，建议重试”/“从 N 个位置中选 1 个”；输入和技术回执渐进披露 | `recovery_kind` + `EvidenceResolution.status/candidates[]` + DecisionRequest；打开页面不调用模型、不消耗下一轮预算 |
| 服务端任务 Branch | 用户不用把整组缺口一次性全放行，可只推进一条工作线 | 分支状态、依赖、资料/缺口数量、“继续此分支” | `branches[]`、`candidate_branch_ids`、`active_branch_id`、带 `branch_id` 的 resume |
| 分支状 Evidence Gap | 用户无需逐个打开扁平按钮猜任务结构，可在一行内看见“分支 -> 材料 -> 证据门 -> 下一步” | Branch lane、当前安全文件标签、Gate 原因、确认/处理入口 | `branches[]` + `evidence_gaps[].branch_id` + 顶层 `decision_requests[]`；不代表多 Worker 并行 |
| 可退出的问题审查 | 用户可以先离开再回来，不会被暂缓回执的 409 或断网困在模态页 | 立即关闭、回执失败提示、待决项仍可重开 | 浏览器退出状态 + versioned `decision` 回执 + Snapshot 刷新；失败不得显示为已 defer |
| 版本化人工控制 | 用户不必只能等待模型跑完 | 暂停、继续、调整下一轮、结束并保留 | `ControlEvent`、expected version、幂等回执 |
| Snapshot 持久化与安全恢复 | 刷新/进程重启不必把已完成轮次当作丢失 | “检查点已恢复”、原轮次/预算/版本、显式继续 | PostgreSQL `HarnessStateStore`、`checkpoint_recovered` |
| 独立不可变成果记录 | 用户看见每轮成果，提交不再通过改写版本表达 | 简报 v1/v2、草稿/已核对、当前版本指针 | append-only `ArtifactVersion`、独立 `TaskCommit` |
| 受控成果恢复 | 用户可以恢复旧简报且不丢掉新版 | “恢复”、当前 vN、“已恢复历史成果版本” | rollback ControlEvent、新 TaskCommit、`artifact_version_restored` |
| 有界候选修复 | 模型返回未通过时不会静默采用 | `未采用` 与预算内重试 | `plan_validation_rejected` / `analysis_validation_rejected`、模型调用计数 |
| EvidenceResolution + Finding 级恢复 | 一条坏引用不再抹掉全部有效结果；多候选或无候选都有明确下一步 | exact/ambiguous/unavailable、已保留/未采用/未发生 | `evidence_resolutions[]`、`partial_artifact_saved`、`next_step.recovery_kind` |
| 预算终态分支续办 | 用户不会在不可恢复的页面里反复点“继续” | 旧 Run 已结束、保留项、未完成 Branch、用此分支创建同 Task 新 Run | `status=stopped`、`brief.outcome=bounded`、candidate Branch + `/continue`；不向旧 Run 发送 resume control |
| Task current pointer 与双版本 CAS | 两个页面同时续办时，用户不用猜哪个 child 才是当前任务；失败页不丢旧成果 | “当前 Run/历史 Run”、中性状态冲突提示、“打开当前 Run”、Task 查询失败重试 | `GET /tasks/{task_id}`、`task_version` + parent `run.version`、原子 Task/Run/receipt；当前不等于 Task list、多实例调度或 WorkUnit queue |
| WorkUnit 与候选采用台账 | 用户无需管理多个 Agent 聊天，也能区分哪个工作包实际执行、哪个只返回候选、哪个进入统一成果，以及失败影响谁 | 业务工作包、实际执行回执、候选成果、原文定位、v1/v2 和“已有可用成果” | `work_units[]`、`contributions[]`、Branch Gate、ArtifactVersion、named SSE；公共投影隐藏 raw unit ID/revision/reservation，当前不等于 queue/lease 或远端 Worker |
| Worker checkpoint 显式恢复 | API 重启不会偷偷重放不确定的模型调用，也不会清空已采用兄弟成果 | “上次调用未确认返回，未自动重试”、目标工作包恢复入口、保留的 v1/v2 | `checkpoint_recovered_in_flight_worker` + 新幂等键 + 当前 Run version；只允许恢复目标单元，不证明 Provider 未收费或多实例安全 |
| 版本化人工决定 | 关闭不再等于“什么都没发生”，重连后仍能对账 | 接受/否决/暂缓、回执版本、无外部动作 | `decision_records[]`、`decision_recorded`、expected version + idempotency |
| 人工确认下一步 | Agent 建议不会自动扩张任务；用户先看形成上下文 | “尚未逐项验证”“查看形成依据”“确认并启动” | 终态 `follow_ups` + Finding refs 上下文 + 新 Run POST |
| 决定与证据重启恢复（DR-0032） | 用户不因 API 重启丢失待决候选或已完成成果 | 重启后继续同一 Decision Packet；接受后只恢复目标 Branch 并生成 v2 | 真实 PostgreSQL 顺序 Runtime 门已通过；当前仍嵌在 Snapshot JSONB 中，无独立 ledger/CAS，不证明多实例并发安全 |

## 7. 当前证据卡片

`DR-0022` 是历史手工选文件基线；`DR-0023/24` 证明整库只读 Loop；
`DR-0025` 是整组补证与 Snapshot 内成果版本的已合并历史基线；`DR-0026`
记录分支选择、独立不可变成果与恢复；`DR-0028/29` 记录目录、问题审查页和原文定位；
`DR-0030` 记录可处置 Finding 与可恢复分析门：

- 完整 Python：`73 passed, 1 skipped`；聚焦 Runtime：`35 passed`；
- Harness 浏览器：`20 passed`；覆盖接受/暂缓回执、候选消歧、只恢复目标 Branch、重连恢复，
  以及预算终态以一条 Branch 创建新 Run 且不控制旧 Run；
- Ruff、lint 与生产 build 通过；准确命令、时长和最终 PR 记录在 `DR-0030` Evidence；
- 预算终态续办经 [PR #38](https://github.com/Dickey007s/lenovo_agent/pull/38) 合并为
  [`5445000`](https://github.com/Dickey007s/lenovo_agent/commit/54450007617527971b98c229bcd25aaa9ee1de45)，远端检查通过；
- PR #31 的 PostgreSQL 17.11 workflow `1 passed in 1.84s`，四个顺序 Runtime 覆盖中断、恢复完成、历史版本恢复和再次读取当前指针；这不是多实例高可用；
- 两条等待分支可逐条继续，未选分支保持等待；ArtifactVersion 与 TaskCommit 分表 append-only，恢复只新增 Commit；
- 新的 DecisionRecord 把 accept/decline/defer 绑定到 Finding/Resolution/Branch；它证明回执存在，不证明业务审批正确；
- `exact/ambiguous/unavailable/stale/rejected` 是服务端拥有的原文位置状态，不是 Finding 真值；来源变化会进入 `stale`，候选重算不一致会进入 `rejected`；
- DR-0032 的 `DecisionRequest`、来源修订校验、五态 EvidenceResolution、局部 Branch 恢复与 PostgreSQL 顺序重启门已在限定范围内实现；当前仍不能宣称独立决定账本、并发 CAS、多实例协调或在途调用恢复。
- DR-0054 的最小 Task record、Task GET、Task/Run 双版本、sibling CAS、幂等 replay、current/history 前台和 fail-closed 旧数据恢复已有定向工程门；Task Ledger 定向 Python `92 passed`、浏览器 `4 passed`，整库 Python `410 passed, 23 skipped`、Playwright `68 passed`，Ruff/lint/build 通过。随后隔离 PostgreSQL 17.11 的七项 Task transaction gate 全部通过，并补上破损 parent version fail-closed；这仍不证明多实例协调、WorkUnit durable state 或 Provider 质量。
- DR-0055 的 Branch 绑定 WorkUnit、append-only Contribution、两波 v1/v2、局部 waiting、严格 reservation replay、fixed-flow 反例和 checkpoint-recovered 目标重试已形成限定纵切；最新全量 Python `417 passed, 23 skipped`、Playwright `68 passed`，隔离 PostgreSQL 17.11 的 Demo/Task 组合为 `10 passed`，Ruff/lint/build 通过。这证明单主机持久台账，不证明 queue/lease、远端 Worker、多实例、Provider 效果或用户价值。
- DR-0056 把 Demo 1 时间维和 Demo 2 组织维拆成任务会话、历史只读 Run 与独立 Adaptive Swarm 工作台；定向浏览器 `4 passed`、全量 Playwright `73 passed`、全量 Python `418 passed, 23 skipped`，Ruff/lint/build、治理与变更链接检查通过。截图来自固定 Fixture，不是真实 Provider 或用户研究；当前仍只是进程内、每波最多三个的只读 Worker。
- DR-0057 纠正产品身份并新增 `/agent-capabilities`：Loop 与 Adaptive 使用同一个 selected Run 同页展示，历史一起只读，来源来自安全 Catalog，Evidence Review 仍可回开；能力页定向 `4 passed`、全量 Playwright `77 passed`、全量 Python `418 passed, 23 skipped`，Ruff/lint/build/治理通过。智能工作驾驶舱没有实现，也没有在前台放占位入口。
- DR-0058 在不改 Runtime 的前提下把能力页收敛为四条渐进披露路径：默认任务进展、完整执行记录、协作方式和确认结论依据；主要待办来自 open DecisionRequest，协作方式把实际路线投影为任务准入、工作包、贡献汇合、核验与成果，工作包/来源/执行回执默认折叠。视觉重构最终 Playwright `77 passed`，但自动化与受控 Fixture 截图只证明工程映射，不能证明用户理解、效率或信任改善；本轮没有补真实 Provider、PostgreSQL 或目标用户研究。
- DR-0060 在 Workspace 与 Agent 能力页增加“新建任务”：空白草稿本身无服务端写入，旧 Task/Run 不变，提交后才创建独立 Task；刷新保持草稿、历史可返回且相同文字的新任务使用新幂等键。定向和全量浏览器结果见本次 Evidence；没有补 Provider、PostgreSQL 或目标用户研究。
- DR-0034 的全量门为 Python `83 passed, 2 skipped`、PostgreSQL `2 passed`、Harness browser `25 passed`，Ruff/lint/build 通过；它证明两类待处理动作的前台映射和 390 px 回归，不证明“3 秒内理解”或用户价值。
- DR-0036 的门为 Python 定向 `78 passed`、本机全量 `116 passed, 3 skipped`、远端 PostgreSQL 17 `3 passed`、Harness browser `29 passed`、Ruff/lint/build 通过；一次真实 `deepseek-v4-pro` TC-01 在第 1 轮完成，真实 CSV 5/5、三 Branch 完成、0 Gap/开放 DecisionRequest。本机三个 skip 已由 PR #45 顺序 PostgreSQL 门补证，但仍不证明多实例；一次 Provider 成功也不证明重复稳定性或目标用户理解提升。
- 两张确定性浏览器图分别展示“继续此分支”与“恢复 v1”；它们证明 UI/服务端字段映射，不是真实模型运行；
- 最终截图绑定的真实浏览器运行：整库冻结 96 份索引，Agent 自主选择并核对 3 份文件，2 次 `deepseek-v4-pro` 调用，形成 5 条发现和 4 条待确认建议；
- 3 张最终文件管理器/建议截图及 SHA-256 写入 Evidence；1440px 与 390px 无页面横向溢出；
- 实现提交 [`2b8e58c`](https://github.com/Dickey007s/lenovo_agent/commit/2b8e58c161df02d4f2c09bc2692db76d075f2ae2)；
- PR #25-#31 已合并到 `master`；`DR-0026` 由 [PR #31](https://github.com/Dickey007s/lenovo_agent/pull/31) 合并为 `697e38b`，PostgreSQL 门已通过。

`DR-0023` 的历史数字仍只证明当时的手工范围版本。当前最终数字必须取自
[`AUTONOMOUS-WHOLE-WORKSPACE-RESEARCH-20260825`](evidence/AUTONOMOUS-WHOLE-WORKSPACE-RESEARCH-EVIDENCE-20260825.md)，
不得把旧版 PPT 或历史 Evidence 当作当前 UI/API 事实。

## 8. 禁止对外表述

- “已经下载 FORTE 未公开的完整 180 条任务”；
- “FORTE 公开文件是真实 Lenovo 或客户企业数据”；
- “15 类 FORTE 任务已经全部解决”；
- “有引用就证明结论或数字正确”；
- “计划里出现操作，就说明工具或文件写入已经发生”；
- “当前最小 Task Ledger/current pointer 与 WorkUnit/Contribution 台账已等同生产级 Durable Task/Worker 服务，或 Demo 2/3 已全部完成”；
- “内存 Snapshot 具备跨进程持久化或多实例高可用”；
- “PostgreSQL Snapshot 恢复等于在途模型调用可续跑、跨实例调度或多实例高可用”；
- “独立 append-only 逻辑 ArtifactVersion/TaskCommit 等于真实办公文件写入、源文件回滚或 Tool Gateway 动作”；
- “一次进程内最多三个 Analyst Worker 等于分布式 Swarm、生产调度、Worker lease 或多实例恢复”；
- “Topology Admission 证明多 Worker 更快、更便宜、更正确”；
- “Evidence Gate 已验证语义真值、数值正确性或业务完整性”；
- “整库、引用、计划、暂停、恢复或知识工作是本项目独有”；
- 在没有固定配置竞品实测时声称“主流竞品做不到”或“全面领先”；
- 在没有用户研究时声称“新界面更清晰、更可信或效率更高”。

## 9. 2026-09-14 完整办公任务汇报图

新增[四图与实跑记录](reports/office-task-story-20260914/README.md)，使用原系统中同一个真实入职资产准备 Run，按“30 人名单与 PDF 输入、Agent 选材和处理、原文复核、9 人 CSV 交付”讲清完整任务。此次共试跑四类任务、12 次实际模型调用、8 个下载文件；27 项文件核验通过，不代表模型语义正确。

图内标注保留了入职模型误解 PDF 规则的事实，没有将证据定位当作结论正确。财务、上线和入职的叙事对账缺口及 UX 误拦截候选已记录，尚未修复。四次均为单 Controller，不是蜂群实测；本次没有修改产品、执行外部动作、重跑全量回归或完成目标用户研究。汇报应使用[简短说明](reports/office-task-story-20260914/汇报说明.md)中的完成范围，不以历史测试或图像后期标注替代系统事实。

2026-09-15 根据“界面截不全”的反馈，补充[1920 像素宽的完整页面版](reports/office-task-story-20260914/full-size-20260915/README.md)，并附无标注原图；成果长图保留至页面底部。输入页是原指令复现，后续页重开同一真实 Run，本次未新增模型调用或功能完成声明。

## 2026-10-26 Demo3 演示补充

原工作台现有十二个可选择的预设案例。推荐讲解顺序：自动整理并撤销、同名联系人澄清、修改后重新确认、冲突材料判断、受限承诺拒绝。全部是固定规则和测试记录，不是模型推理或真实外部动作。完整输入与逐步操作见 [演示清单](reports/demo3-examples-20261026/index.html)，验证见 [DR-0098 Evidence](evidence/DR-0098-DEMO3-EXAMPLES-20261026.md)。
