# Office Agent V0.2 中文汇报卡片

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
十五条场景的实际效果、失败修复轨迹、真实模型运行和外部边界见
[`SCENARIO-EFFECT-GATE-20260827`](evidence/SCENARIO-EFFECT-GATE-20260827.md)
与[中文效果账本](reports/SCENARIO-EFFECT-GATE-LEDGER-20260827.md)。

## 3. PPT 页面卡片

| 页码 | 中文结论 | 建议画面 | 证据与边界 |
| --- | --- | --- | --- |
| 1 | Office Agent 从一个可逐级展开的统一办公资料库开始，而不是从 Demo 或职业按钮开始 | 15 个顶层目录、嵌套子目录与文件预览同屏截图 | `DR-0028/24`；目录来自安全路径投影，公开基准数据不是真实企业网盘 |
| 2 | 真正的问题不是缺少聊天框，而是上下文不可见、执行过程不可核对 | 旧流程与文件夹优先流程对比 | Stakeholder 反馈，不是用户研究 |
| 3 | 一个 Runtime、八个通用模块、三种验收视角 | 分层架构图；Demo 1/2 加跨拓扑 Demo 3 | 当前能力与目标能力必须用不同颜色 |
| 4 | 整库、多来源、引用、计划、暂停、恢复和知识成果已经是主流基线；我们的候选差异是“结论采用由服务端裁决” | Microsoft 365 Copilot、NotebookLM、deep research、Codex、Claude、OpenClaw 的能力底线汇入证据采用合同 | 官方文档研究，不是竞品实测；独占结论必须通过同场挑战 |
| 5 | 用户给目标，Agent 负责从整库找证据，但选择过程必须可见、可限、可复核 | 浏览 -> 下达目标 -> Agent 选证据 -> 观察 -> 引用 -> 复核 | 实现侧重点差异，不是优越性结论 |
| 6 | 固定公开数据版本，让演示中的每份材料都能被现场检查 | 15 个文件夹、96 份文件、格式分布 | FORTE 固定 commit；不是真实企业数据 |
| 7 | 安全预览把“Agent 读了什么”变成可见契约 | CSV/PDF/DOCX/TXT 预览拼图和安全说明 | 路径、大小、hash、符号链接和解析器测试 |
| 8 | Harness 把模型调用、内容采用、确定性办公效果和整体 Loop 状态分开 | 事件、模型回执、可下载工件与检查结果时序 | Snapshot/Receipt/Artifact 事实；不展示思维链，也不把 `completed` 当作效果通过 |
| 9 | Agent 说“有问题”之后，用户要同时看懂事实、影响、真实原文和自己必须决定的下一步 | 问题处置单：1 事实 -> 2 影响 -> 3 人工动作；证据与实际文件并排；A/B/C + 反馈 | `DR-0030/29`；推荐是模型候选，确认只创建新只读 Run |
| 10 | Agent Control Loop 会把计划变成可核对任务分支；前台先区分“授权重试”与“必须由人选择原文”，人阅读时不消耗 Agent 执行预算 | 单一推荐重试按钮、三候选原文且未选前禁用、active elapsed、成果 v1→v2、终态新 Run | `DR-0034/32/31/30`；真实 PostgreSQL 只证明顺序 Runtime；Branch 不等于并行 Worker，terminal Run 不可 resume |
| 11 | Demo 2 验收多任务自组织、动态调度和共享工件汇聚 | Worker、依赖与动态重排图 | 目标设计；当前产品没有通用 Worker Runtime |
| 12 | Demo 3 对单任务和多任务统一施加风险与动作控制 | 影响预演 -> 证据 -> 审批 -> Permit -> 回执 | 目标设计；当前没有真实外部动作 |
| 13 | 当前 12 个本地 FORTE 场景已有真实隔离工件与确定性验证；3 个外部依赖场景明确阻断 | 12 通过、3 `blocked_external_boundary` 的效果账本；六个真实 `deepseek-v4-pro` 运行 | `DR-0035` 限定能力，不等于任意办公任务或用户价值；模型质量、效果验证、Loop 终态分开报告 |
| 14 | 历史约 30% 审计基线已升级为可见分支、可恢复逻辑成果和固定本地可写工件；下一步仍是通用 Tool Gateway、多 Worker 与外部动作治理 | Branch、Run Workspace Artifact 与 Demo 2/3 目标架构叠加图 | `30%` 只代表历史基线；当前真实工件仅来自十二个服务端固定适配器，不是通用 Agent 执行环境 |
| 15 | 同一个任务可以“成果已通过、Agent 审计说明仍待修复”；用户必须先知道成果能否用，再决定是否处理引用位置 | TC-01 5/5 成果在前、两个同源 Gap 合并为一个审计项；PDF “技术/研发”断行修复前后 | `DR-0036`；Artifact 通过不等于 Run completed，Anchor 仍不证明语义正确 |
| 16 | 成果文件必须在下载前说清“哪个期间、怎么算、拿来做什么” | TC-05 三张成果卡：两个 2026 明细与一个三期核对说明；问题审查页字号修复前后 | `DR-0037`；内容来源与任务上下文分开，Finance-018 仍是固定适配器；自动化不证明用户理解 |
| 17 | 一个引用跳转缺口不应被包装成系统失败：先说成果是否已生成，再给一个动作 | TC-05 “成果已生成，还有 1 条说明缺少原表格位置”；查看成果、查找位置、技术详情三层 | `DR-0038`；只恢复目标 Branch，不覆盖 Artifact；未通过和旧 Run 使用不同话术 |
| 18 | 代码测试的关键不是绿灯数字，而是同一套测试能否先抓住原缺陷、再验证修复 | TC-12 Stage A/B/C 红灯 -> Stage D 71/71；三套真实测试、四文件 diff、逐文件 coverage 与下载复跑 | `DR-0042`；固定 qa-003 适配器，不是任意 JS 沙箱、自动 PR 或 OS 级断网 |
| 19 | 一个任务可以“成果文件检查通过，但业务结论仍是不通过”；前台必须同时讲清两种真相 | TC-11 两份 Artifact 共享 9 项确定性检查，同时四条来源推导上线 Gate 全失败；首屏“不得上线”+公式，辅助指标和 18 项台账渐进展开 | `DR-0043`；固定 pm-014 适配器，不执行上线、不改配置；自动化不证明用户理解 |

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
11. 运行 TC-05：先让观众不下载文件，直接从三张卡读出期间、统计口径、用途与 31/2 条记录；说明两个 CSV 只来自 2026，三期来源与僵尸比较只属于说明。再展示模型是否调用/采用、隔离工件、逐项确定性检查和下载按钮；指出即使 Analyst 未采用，已通过的工件仍保留。随后展示 TC-03/08/09 的外部边界回执，证明系统没有伪造 SQL/Web/cron。
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
| 预算终态分支续办 | 用户不会在不可恢复的页面里反复点“继续” | 旧 Run 已结束、保留项、未完成 Branch、用此分支创建新任务 | `status=stopped`、`brief.outcome=bounded`、candidate Branch + 新 Run POST；不向旧 Run 发送 control |
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
- “当前三轮只读 Loop 已等同完整 Demo 1 Durable Runtime，或 Demo 2/3 已全部完成”；
- “内存 Snapshot 具备跨进程持久化或多实例高可用”；
- “PostgreSQL Snapshot 恢复等于在途模型调用可续跑、跨实例调度或多实例高可用”；
- “独立 append-only 逻辑 ArtifactVersion/TaskCommit 等于真实办公文件写入、源文件回滚或 Tool Gateway 动作”；
- “Branch 状态与逐条继续等于多个 Worker 已并行、自组织或动态调度”；
- “Evidence Gate 已验证语义真值、数值正确性或业务完整性”；
- “整库、引用、计划、暂停、恢复或知识工作是本项目独有”；
- 在没有固定配置竞品实测时声称“主流竞品做不到”或“全面领先”；
- 在没有用户研究时声称“新界面更清晰、更可信或效率更高”。
