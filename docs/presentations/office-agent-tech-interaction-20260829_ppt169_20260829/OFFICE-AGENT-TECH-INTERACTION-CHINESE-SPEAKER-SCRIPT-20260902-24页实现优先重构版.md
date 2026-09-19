# Office Agent 技术差异与交互影响中文讲稿：24 页实现优先重构版

对应文件：[Office-Agent-技术差异与交互影响-20260902-24页实现优先重构版.pptx](exports/Office-Agent-技术差异与交互影响-20260902-24页实现优先重构版.pptx)
建议时长：42 至 48 分钟
内容结构：P01-P12 先讲当前实现与边界；P13-P24 再讲市场研究、技术差异、用户流程、前台输出和验证计划。

## 使用说明

讲述时始终区分三类事实：已经实现、有限实现、目标能力。官方竞品资料用于说明市场基线，文献与协议用于说明设计来源，当前系统截图用于说明工程纵切；任何一类都不能替代目标用户研究。

## P01 未来办公智能体：当前实现与交互影响

建议时长：1 分钟

这次汇报改成两段。前半段先回答“我们沿 07-16 设计真正实现了什么”，后半段再回答“它与主流方案有什么差异、会怎样改变用户流程和前台输出”。

右侧保留当前系统真实界面，提醒听众这不是只讲概念。当前系统已经把资料库、任务合同、规划校验、分支证据门、成果文件、状态快照和有序记录放到同一工作面，但仍是固定公开数据上的受限只读纵切。

整场始终区分三类事实：已经实现、有限实现、目标能力。竞品官方资料用于说明市场基线；文献和协议用于说明设计来源；自动化与截图不是用户研究。

转场：先看 07-16 三个方向今天分别落到了什么程度。

证据/边界：当前系统实测；市场差异与用户价值仍需固定配置同测和目标用户研究。

### 研究链接

- https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/

## P02 先讲落地：07-16 设计如何进入系统

建议时长：1.5 分钟

这一页先给出结论，不让听众等到后半段才知道当前系统做到哪里。

Demo 1 是已实现的时间维纵切：同一任务可以跨运行继续，分支、成果版本和局部恢复有服务端事实。Demo 2 是有限实现：服务端能编译依赖路线，用户确认后按波次启动最多三个进程内只读执行单元，贡献采用和统一成果分开记录；它不是分布式协作运行时。Demo 3 仍是目标能力：当前能区分成果已经生成与外部动作未发生，但生产连接器、身份授权、执行许可和幂等外部回执尚未实现。

因此当前最准确的描述是：一条可恢复、可核对的只读办公任务纵切，不是完整执行器。

转场：下面把这三个方向重新放回一个底座、两层增强和三类控制。

证据/边界：当前系统实测；持久状态与人工审批机制参考官方运行时实践。

### 研究链接

- https://docs.langchain.com/oss/python/langgraph/persistence
- https://openai.github.io/openai-agents-python/human_in_the_loop/

## P03 一个底座、两层增强、三类控制

建议时长：2.5 分钟

这一页先不要急着记英文名，只看三层关系。最下面的统一 Agent Runtime 是每个任务都要经过的底座，它稳定承接任务、状态、上下文、执行、能力、证据、策略和追踪。没有这层，Agent 仍然只是一次模型调用，任务中断以后不知道从哪里继续，也无法说明某个结论或动作来自哪一步。

第一层增强是 Agent Control Loop。它只在任务需要多轮推进、等待补证或恢复时发挥价值。07-16 希望它解决时间维连续性；当前已经落地的是受限单 Loop、服务端 Branch、Evidence Gate、ArtifactVersion 和 Snapshot/SSE。第二层增强是 Governed Adaptive Swarm，它面向高价值、跨来源、可并行的复杂工作。当前已经形成最小受控纵切：Topology Admission、WorkUnit DAG、每波最多三个进程内只读 Worker、Contribution Gate 与统一 Artifact；但 durable queue、远端 Worker、通用 Resolver 和多实例调度仍是目标。

左侧三类控制不是第三层业务能力，而是贯穿所有层的约束。Task Control 决定目标、预算、暂停与停止；Evidence Control 决定来源、冲突、验证和模型说明是否采用；Action Control 决定风险、审批、Permit 和执行回执。它们最终让前台只需要回答三件事：任务现在走到哪，当前结论凭什么成立，哪些动作真的发生了。

转场：接着把这套骨架拆成八个稳定职责。

证据/边界：https://docs.langchain.com/oss/javascript/langgraph/persistence ；https://openai.github.io/openai-agents-python/human_in_the_loop/ ；https://modelcontextprotocol.io/specification/draft/client/elicitation

预期问题：为什么不把所有任务都放进 Loop 或 Swarm？因为增强层有额外状态与协调成本，只有任务的时间跨度和组织复杂度值得时才应启用。

### 研究链接

- https://arxiv.org/abs/2210.03629
- https://docs.langchain.com/oss/javascript/langgraph/persistence
- https://openai.github.io/openai-agents-python/human_in_the_loop/
- https://modelcontextprotocol.io/specification/draft/client/elicitation

## P04 智能体最小运行时：八个稳定职责

建议时长：2.5 分钟

八个模块不是八个前台页面，而是一次任务从定范围到可恢复的四段责任链。

第一段是“定范围”。Workspace Catalog & Safe Preview 负责哪些资料可以安全读取，Task Contract 负责目标、范围、完成条件和禁止事项。前台要回答的是“你读了哪些资料、任务边界是什么”。

第二段是“定计划”。Planner 可以提出分支、依赖和资料范围，但计划不能因为模型返回就直接运行。Admission、Policy Compiler & Plan Validator 还要校验预算、来源、依赖、工具和副作用。前台要回答的是“为什么这样拆、什么计划被拒绝或修复”。

第三段是“推进执行”。Scheduler & Worker Manager 决定哪个分支先做、依赖谁、何时等待、何时恢复；当前已经支持服务端编译的 WorkUnit DAG、显式波次和每波最多三个进程内只读 Worker。Tool Gateway 仍应统一真实工具的授权、超时、幂等和回执，但当前没有通用实现。前台要回答的是“现在做到哪一步、谁依赖谁、哪个分支受影响、动作是否真的执行”。

第四段是“成果恢复”。Artifact Workspace & Verifier 保存成果版本并执行当前固定场景的确定性检查；Checkpoint, Event & Governance Control 让 Snapshot 成为状态权威，SSE 只做有序投影，并提供可选 PostgreSQL 重启恢复子集。前台要回答的是“结果能否下载、核对、审计和恢复”。

所以模块对后端是职责，对用户只有四个问题：读什么、怎么做、做到哪、结果能不能复核与恢复。蓝色表示当前实现，橙色表示部分近似，灰色表示目标，不能把目标模块写成现有能力。

转场：有了职责边界，再看当前实现究竟做到哪里、缺口在哪里。

证据/边界：当前系统实测；ReAct、LangGraph、MCP 与 A2A 只作线上架构参照。

预期问题：八个模块会不会让前台更复杂？不会要求用户操作模块名，但必须把模块产生的关键状态翻译成业务语言。

### 研究链接

- https://arxiv.org/abs/2210.03629
- https://docs.langchain.com/oss/javascript/langgraph/persistence
- https://modelcontextprotocol.io/specification/draft/client/elicitation
- https://a2a-protocol.org/latest/specification/

## P05 智能体控制循环：当前实现与缺口

建议时长：2 分钟

中心五段里，Observe 和 Plan 已有清晰纵切；Act 仍主要是只读分析和固定成果适配器；Verify 能做 Schema、引用定位和部分确定性成果检查；Commit 是 append-only 的逻辑 ArtifactVersion 与 TaskCommit。外围控制里，Task Contract、Evidence Gate 和 Trace 较完整，Budget、Steer/Pause、Durable State 是部分近似，Takeover 和通用执行仍缺。旧审计曾给出约 30% 的历史架构成熟度基线，但那不是当前覆盖率，更不是模型质量。现阶段最准确的说法是：有反馈与恢复的只读办公任务纵切。

转场：下面用真实系统界面走完整条办公任务纵切。

证据/边界：https://docs.langchain.com/oss/javascript/langgraph/persistence ；https://openai.github.io/openai-agents-python/human_in_the_loop/ ；https://a2a-protocol.org/latest/specification/

预期问题：什么时候可以把它称为完整 Control Loop？

### 研究链接

- https://docs.langchain.com/oss/javascript/langgraph/persistence
- https://openai.github.io/openai-agents-python/human_in_the_loop/
- https://a2a-protocol.org/latest/specification/

## P06 我们到底做了什么：跑通办公任务纵切

建议时长：2 分钟

这页回答最直接的问题：我们到底做了什么。不是又做了一张 Agent 对话页面，而是把一条办公任务纵切跑通了。

第一层是 Workspace。系统面对的是 15 个顶层目录、96 份输入文件，文件都通过服务端 allowlist、大小、哈希、格式和非链接校验后再进入安全预览。第二层是 Task Contract。用户只写任务目标，服务端冻结可读范围、预算、禁止动作和当前版本。第三层是 Planner 与 Analyst。模型调用、服务端校验和模型输出采用分别记录，不再把“模型返回了”写成“当前结论已经采用”。第四层是 Branch Evidence Gate。某条证据不能唯一定位时，只让受影响分支等待，其他已完成成果继续保留。第五层是真实 Artifact 与回执。当前固定场景可以生成可下载文件，执行具名确定性检查，并把 Snapshot 和有序 Trace 留下来。

右侧不是概念图，而是当前系统完成一条固定办公任务后的完整运行界面：左侧是资料库，中间是任务、Agent 路径和成果，右侧是有序 Control Loop 记录。

这条链已经证明的是固定公开数据上的受限纵切；尚未证明的是通用语义正确、任意办公文件写入、生产级 Connector 和生产 SLA。

转场：先看用户只说目标、系统自主选择资料。

证据/边界：当前系统实测；截图来自固定公开数据运行，不是竞品对照或生产环境。

预期问题：这是不是一个为固定演示写死的流程？当前确有固定成果适配器，但 Workspace、合同、分支、证据门、Snapshot 和 Trace 是通用运行时结构。

### 研究链接

- https://github.com/Dickey007s/lenovo_agent/blob/8a5e01567ad89a24a6aac8ac8d58c438409c1346/README.md
- https://github.com/Dickey007s/lenovo_agent/blob/8a5e01567ad89a24a6aac8ac8d58c438409c1346/docs/ARCHITECTURE.md

## P07 实操 1：用户只说目标，智能体自主选择资料

建议时长：1.5 分钟

用户做的第一件事只有一个：写清业务目标。

服务端创建 Run 时冻结完整 allowlisted 输入索引，scope_mode 是 whole_workspace。Planner 看到的是安全元数据，而不是绝对路径、隐藏任务、答案或内部哈希；它提出本轮需要的资料和分支，服务端再校验预算、来源、依赖、工具和禁止动作。

前台因此必须补上三类反馈。第一，解释本轮为什么选择这些资料；第二，区分规划模型和分析模型是否调用、输出是否被采用；第三，持续显示当前轮次、剩余调用预算、阶段和有序 Trace。用户少做了文件选择，但系统多承担了范围解释责任。

转场：再看证据出现歧义时，为什么只恢复受影响分支。

证据/边界：当前系统实测；全库范围、服务端 Planner 和前台 Trace 的显示均以本次 Snapshot 为准。

预期问题：为什么不把全部 96 份文件都交给模型？因为服务端需要控制上下文、成本和来源范围，并保留每轮选择依据。

### 研究链接

- https://github.com/Dickey007s/lenovo_agent/blob/8a5e01567ad89a24a6aac8ac8d58c438409c1346/docs/decisions/DR-0024-autonomous-whole-workspace-research.md

## P08 实操 2：证据有歧义，只恢复受影响的分支

建议时长：1.5 分钟

这页展示证据出现歧义时的真实处理。典型情况不是“没有源文件”，而是模型给出的逐字片段在安全预览里出现多次，服务端无法唯一决定应该回开哪一处。

界面先用业务语言回答三件事：发生了什么、这会影响什么、用户现在需要做什么。然后给出候选原文位置和安全预览高亮。用户选择的是来源位置，不是在替 Agent 判断结论一定正确。

右下角的小图展示同一轮里不同 Branch 可以有不同动作：一条需要用户确认原文位置，另一条可能只需要继续本分支。DecisionRequest 绑定 expected_version、source_revision、候选和受影响 Branch；来源版本变化时进入 stale，不能把旧选择直接套到新文件。

用户确认后，只恢复目标 Branch。已完成 ArtifactVersion、其他 Branch 和已有核对记录不被覆盖。这是局部恢复和整轮重跑在用户体验上的关键差别。

转场：接着看真实成果、确定性校验和模型说明怎样分层。

证据/边界：当前系统实测；位置确认只证明 locator 与来源成员关系，不证明自然语言蕴含、穷举或算术全面正确。

预期问题：为什么还要人选位置？格式原生 Locator 尚未完全覆盖，当前保留可审计的人工决定比服务端猜一个位置更稳妥。

### 研究链接

- https://github.com/Dickey007s/lenovo_agent/blob/8a5e01567ad89a24a6aac8ac8d58c438409c1346/docs/decisions/DR-0032-persistent-decision-and-local-recovery.md
- https://github.com/Dickey007s/lenovo_agent/blob/8a5e01567ad89a24a6aac8ac8d58c438409c1346/docs/decisions/DR-0038-user-language-source-location-recovery.md

## P09 实操 3：成果可检查，模型说明不覆盖事实

建议时长：1.5 分钟

左侧展示成果与业务效果分层。当前固定场景能够在隔离 Run 工作区生成真实文件，用户可以下载；系统还会执行具名确定性检查，并记录 EffectReceipt。与此同时，付款、核销、发送、写 CRM 等未发生动作会继续明确显示为未发生。

右侧展示模型说明与确定性成果冲突时的处理。模型确实被调用，因此 called=true；但它给出的行数或分组与确定性成果不一致时，output_used=false。前台只保留一套当前结论，冲突说明进入审计轨迹，而不是与通过检查的成果并排争夺用户注意力。

这一步把“模型说了什么”和“系统已经采用什么”分开，也把“文件存在”和“业务动作发生”分开。对用户的直接影响，是成果可以先用、依据可以继续审、错误说明不会覆盖事实。

当前边界仍然清楚：固定检查只证明特定字段、结构和效果，不是通用语义真值证明器；成果通过也不代表业务价值或最终判断自动成立。

转场：这三段实操汇总到 Demo 1 的时间维连续性。

证据/边界：当前系统实测；固定成果适配器与叙事对账覆盖既定场景，不外推到任意办公任务。

预期问题：固定检查会不会把模型变得多余？不会，模型仍负责规划、跨资料归纳和提出候选；确定性检查负责约束可复算事实。

### 研究链接

- https://github.com/Dickey007s/lenovo_agent/blob/8a5e01567ad89a24a6aac8ac8d58c438409c1346/docs/decisions/DR-0052-authoritative-outcome-and-narrative-reconciliation.md
- https://github.com/Dickey007s/lenovo_agent/blob/8a5e01567ad89a24a6aac8ac8d58c438409c1346/docs/decisions/DR-0035-scenario-effect-gate-and-run-workspace-artifacts.md

## P10 Demo 1：时间维连续性，单个任务如何持续推进

建议时长：2 分钟

Demo 1 来自 07-16 的时间维连续性。目标不是让 Agent 永远运行，而是让同一个 Task ID 在多轮任务中有稳定的任务契约、状态版本、分支和恢复点。流程仍然是 Task Contract、Observe、Plan、Act、Verify、Commit。

07-16 的关键镜头是 Verify 同时发现正式口径 2,400 万和预测口径 2,680 万。正确处理不是整项任务失败，也不是让模型自行选择，而是 Evidence Gate 只让 revenue-baseline 分支进入 waiting_input；customer-facts 和 project-risk 分支继续产出并保留。用户给出 Steer，采用正式口径并保留预测差异说明，系统只恢复受影响分支，最后把版本、来源、验证结果和 Trace 一起 Commit。

当前系统已经具备服务端 Branch、分支级 Evidence Gate、append-only ArtifactVersion、TaskCommit、局部恢复和可选 PostgreSQL 重启恢复。还没有生产级跨端身份、任意办公工件写入和长期后台 Worker。因此这一页不是把 07-16 演示冒充当前实测，而是说明我们已经完成了其中最关键的一段状态与证据纵切。

前台变化是用户不必重开对话、重讲背景；他在同一任务里看见哪个分支完成、哪个分支为何停、选择后恢复什么、旧成果是否保留。

转场：时间维成立后，再看 Demo 2 怎样处理组织复杂度。

证据/边界：https://docs.langchain.com/oss/javascript/langgraph/persistence ；https://openai.github.io/openai-agents-python/human_in_the_loop/

预期问题：现在已经支持手机和电脑控制同一生产任务吗？没有，当前证明的是服务端状态、分支与恢复机制，生产身份和跨端控制仍是目标。

### 研究链接

- https://docs.langchain.com/oss/javascript/langgraph/persistence
- https://openai.github.io/openai-agents-python/human_in_the_loop/

## P11 Demo 2：复杂任务怎样拆解并收敛

建议时长：2.5 分钟

Demo 2 仍然保留 07-16 的智能工作驾驶舱作为目标产品面，但这一页不再只讲目标框图，而是先回答一个可以直接演示的输入、过程和输出。

输入是一条复杂但只读的办公任务：分别核对产品上线、搜索 Agent 运行和用户交互三条工作线的风险与证据，先独立核对，再形成统一简报。用户不需要指定五个 Agent，也不需要自己分配会话。

过程由服务端事实决定。Topology Admission 编译出五个 WorkUnit，其中三个是根工作包，两个依赖前序结果。第一波返回后，三个 Contribution 分别进入采用门；只有带批准来源和可定位证据的候选才能进入 Artifact。两个依赖工作包显示“下一波待确认”，由用户明确启动，而不是后台无声扩张预算。

输出是一个统一工作面：左侧阶段轨回答现在走到哪，中央 DAG 回答谁依赖谁，右侧当前影响只突出唯一主要动作，底部结果条说明三份贡献已经采用、Artifact v1 已保留、还有两个工作包待确认。用户管理的是统一成果和下一步，不是多个 Agent 对话。

边界必须讲清：这是单服务进程、顺序批次、每批最多三个只读执行单元的受控演示样例。它没有持久任务队列、租约、远端执行单元或多实例协调，也不是完整的智能工作驾驶舱；自动化和截图同样不能证明这种协作方式更快、更准或更易理解。

转场：协作之后，还必须把方案与真实执行隔离。

证据/边界：https://docs.openclaw.ai/concepts/multi-agent ；https://a2a-protocol.org/latest/specification/ ；https://www.nngroup.com/articles/progressive-disclosure/

预期问题：多个执行单元一定比单一流程好吗？不一定，当前也没有效果证据；只有同任务、同模型、同来源和同预算下的增量收益高于协调与验证开销时，才应该启用自适应协作。

### 研究链接

- https://a2a-protocol.org/latest/specification/
- https://docs.openclaw.ai/concepts/multi-agent
- https://www.nngroup.com/articles/progressive-disclosure/

## P12 Demo 3：动作维风险，方案与执行必须隔离

建议时长：2 分钟

Demo 3 保留 07-16 的 Risk Gate。Risk Lens 从动作影响、数据敏感度、可逆性、权限和缺失信息评估风险，再映射到 L0-L5：L0 自动执行，L1 执行并通知，L2 只生成草稿，L3 普通确认，L4 强确认，L5 直接拒绝。

真正关键的是动作链。Agent 先提出方案，前台展示动作对象、影响范围和可逆性；Evidence Gate 与 Risk Lens 给出来源和风险理由；需要人工确认时，用户明确同意后才生成 Permit；执行后必须返回可核验的 ExecutionReceipt，或者明确写出动作未发生。这样“方案”“草稿”“批准”和“执行”不会被混成一个绿色完成状态。

页面下半部分使用当前真实界面截图，说明目前已经实现的有限一段：实际 Artifact、具名 Validator、EffectReceipt 和未发生边界可以分层展示。但生产 Connector、身份授权、Permit 防重放与真实外部动作仍未实现，所以系统不会发送邮件、付款、写 CRM 或执行生产命令。

前台的直接变化是按钮不能只写“确认”。用户必须先看见对象、影响、证据、风险级别、可逆性和执行回执，才能知道自己的点击究竟会改变什么。

转场：实现讲完以后，下面进入市场与技术调研。

证据/边界：https://openai.github.io/openai-agents-python/human_in_the_loop/ ；https://modelcontextprotocol.io/specification/draft/client/elicitation ；https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/

预期问题：当前是不是已经具备 L0-L5 的生产执行能力？没有，L0-L5 是目标控制模型，当前只有固定成果和未执行边界的有限实现。

### 研究链接

- https://openai.github.io/openai-agents-python/human_in_the_loop/
- https://modelcontextprotocol.io/specification/draft/client/elicitation
- https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/

## P13 技术演进：工程对象不断外扩

建议时长：1.5 分钟

这页把 07-16 的 P05 到 P09 合并成一条链。Prompt Engineering 关注一次指令与示例；ReAct 把工程对象扩展到 Action 和 Observation；Context Engineering 开始管理系统指令、工具、外部数据和历史；Harness Engineering 再把权限、沙箱和工具环境纳入系统；Loop Engineering 是我们对触发、验证、记录和恢复的方案归纳。最后一步是办公交付：业务成果、来源、人工决定和未执行边界都可复核。需要强调，这些阶段名不是学界统一年表，而是为了说明系统责任为什么不断外扩。

转场：先把商业产品、邻近工具和底层协议分开。

证据/边界：https://arxiv.org/abs/2005.14165 ；https://arxiv.org/abs/2210.03629 ；https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents ；https://docs.langchain.com/oss/javascript/langgraph/persistence

预期问题：Loop Engineering 是正式术语还是本方案的归纳？

### 研究链接

- https://arxiv.org/abs/2005.14165
- https://arxiv.org/abs/2210.03629
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

## P14 先分赛道：直接竞品、邻近工具与底层方法不能混比

建议时长：2 分钟

这一页先纠正原稿最大的比较问题：Microsoft 365 Copilot、Glean、Atlassian Rovo、ChatGPT、Codex App、OpenClaw 和 ReAct 不是同一层对象。

市场至少要分成办公套件内嵌、企业知识与智能体平台、通用研究工作台、任务执行工作台、方法与协议五类。真正可比的是用户要审查什么对象，以及状态、证据、成果、人工门和动作事实如何衔接。

因此，本页不是竞品排名，也不据官方资料的缺失推断某个产品做不到某事。

转场：第一组直接竞品是原生办公套件。

### 研究链接

- https://learn.microsoft.com/en-us/microsoft-365/copilot/researcher-agent
- https://workspace.google.com/blog/product-announcements/introducing-google-workspace-studio-agents-for-everyday-work
- https://www.glean.com/platform
- https://docs.glean.com/user-guide/assistant/deep-research
- https://www.atlassian.com/software/rovo/features
- https://www.notion.com/help/enterprise-search
- https://help.openai.com/en/articles/10500283-deep-research
- https://support.claude.com/en/articles/11088861-use-research-on-claude
- https://openai.com/index/introducing-the-codex-app/
- https://code.claude.com/docs/en/how-claude-code-works
- https://docs.openclaw.ai/
- https://react-lm.github.io/
- https://modelcontextprotocol.io/specification/
- https://a2a-protocol.org/latest/specification/

## P15 办公套件竞品：优势在原生上下文和真实应用动作

建议时长：2 分钟

这一页讲直接办公套件竞争。Microsoft 的强项是与 Microsoft 365 工作内容和权限体系相连，Researcher with Computer Use 还能在安全虚拟环境里操作网站和应用。Google 的强项是 Workspace 原生上下文和 Workspace Studio 的跨应用自动化。

这意味着 Office Agent 不能用“多来源”“整库”“有引用”来定义独占差异。当前更准确的说法是：Office Agent 正在验证服务端冻结范围、分支证据门、成果校验和人工控制是否能在一条办公链路里闭合。

转场：第二组看企业知识与智能体平台。

### 研究链接

- https://support.microsoft.com/en-us/microsoft-365-copilot/get-started-using-researcher-with-computer-use-in-microsoft-365-copilot-frontier
- https://learn.microsoft.com/en-us/microsoft-365/copilot/researcher-agent
- https://support.microsoft.com/en-us/microsoft-365-copilot/get-started-with-analyst-in-microsoft-copilot
- https://workspace.google.com/blog/product-announcements/introducing-google-workspace-studio-agents-for-everyday-work
- https://workspace.google.com/blog/product-announcements/introducing-workspace-intelligence

## P16 知识工作台：全源搜索已经成为日常入口

建议时长：2 分钟

Notion AI 是原稿遗漏的重要直接竞品。它把工作空间、连接应用和互联网放进统一入口，支持收窄范围、引用回开和研究模式；官方文档还说明，部分连接器能在连接应用中采取动作。

同一赛道还包括 Glean 与 Atlassian Rovo。Glean 以权限感知的企业搜索和知识图谱为底座，向深度研究、智能体和动作扩展；Rovo 把搜索、对话、深度研究、智能体与自动化嵌入 Jira 和 Confluence。这里用 Notion 的界面作为日常知识工作入口的可视例子，不代表只研究了 Notion。

因此，Office Agent 不能把全源检索、企业连接或引用回开本身写成独占能力。可以继续验证的，是服务端证据准入、模型采用、分支缺口、确定性办公成果与动作事实是否能形成更严格的合同。

转场：第三组看跨来源研究工作台。

### 研究链接

- https://www.notion.com/help/enterprise-search
- https://www.notion.com/help/notion-ai-faqs
- https://www.notion.com/help/notion-ai-connectors
- https://www.glean.com/platform
- https://docs.glean.com/user-guide/assistant/deep-research
- https://www.atlassian.com/software/rovo/features

## P17 跨来源研究：用户已经在审计划、来源、进度与报告

建议时长：2 分钟

ChatGPT 深度研究已经覆盖来源选择、计划审阅、进度展示、运行中中断、引用报告和多格式下载。Claude Research 也会在内部上下文和 Web 上开展多步研究，并输出可检查引用。

所以 Office Agent 的市场表达不能停留在“会研究、有来源、能暂停”。更值得验证的是：每条业务结论是否经过服务端来源准入；部分采用能否保留；证据缺口是否能单分支恢复；成果是否由独立 Verifier 证明已经生成。

转场：第四组看长期任务执行工作台。

### 研究链接

- https://help.openai.com/en/articles/10500283-deep-research
- https://openai.com/index/introducing-deep-research/
- https://help.openai.com/en/articles/11487775-apps-in-chatgpt
- https://support.claude.com/en/articles/11088861-use-research-on-claude
- https://www.anthropic.com/news/integrations

## P18 任务执行工作台：用户审改了什么、验证了没有

建议时长：2 分钟

Codex App 和 Claude Code 不是 Office Agent 的直接办公套件竞品，但它们定义了长任务执行工作台的用户预期：任务有独立状态，执行有隔离环境，变更有 Diff，验证有命令回执，人工可以中断、批准和恢复。

Office Agent 的候选差异不在于“也能跑长任务”，而在于把办公来源、业务 Finding、Evidence Gate、办公 Artifact、人工 Decision 和未执行边界放进同一条事实链。

转场：把这些产品压缩成五个真正可比的审查对象。

### 研究链接

- https://openai.com/index/introducing-the-codex-app/
- https://code.claude.com/docs/en/how-claude-code-works

## P19 真正该比的，不是功能数量，而是五个可审查对象

建议时长：2.5 分钟

这一页把前面的产品叙事收敛为五个可审查对象。

办公套件强在原生上下文和平台动作；研究工作台强在来源、计划、进度和报告；代码执行工作台强在任务、隔离环境、变更和验证。Office Agent 当前尝试把冻结资料库、Task / Run / Branch、Evidence Gate、办公成果与 Verifier 回执放在同一条链路里。

这仍然只是结构上的候选差异，不能替代固定配置的同场实测。

转场：再据此说明 Office Agent 可以主张什么、不能主张什么。

### 研究链接

- https://learn.microsoft.com/en-us/microsoft-365/copilot/researcher-agent
- https://workspace.google.com/blog/product-announcements/introducing-google-workspace-studio-agents-for-everyday-work
- https://www.notion.com/help/enterprise-search
- https://help.openai.com/en/articles/10500283-deep-research
- https://support.claude.com/en/articles/11088861-use-research-on-claude
- https://openai.com/index/introducing-the-codex-app/
- https://code.claude.com/docs/en/how-claude-code-works

## P20 Office Agent 的候选差异：不是能力更多，而是证明链更完整

建议时长：2.5 分钟

这一页给出最重要的结论。Office Agent 当前可以陈述的是“可证伪的合同集成差异候选”，不是已经胜过竞品。

已有证据：整库索引冻结，计划进入服务端 Branch / Topology，Finding 绑定批准来源与 Anchor，模型返回和采用分开，隔离 Artifact 有 Verifier 和历史版本。

未有证据：原生办公套件 Connector、源文件写回、远端 Worker、分布式 lease、多实例协调、生产认证和用户研究。

下一步应做固定配置同场实测，至少回答四个问题：结论能否定位，暂停后能否只补一支，成果是否真写出，计划、批准和执行是否严格分开。

转场：候选差异最终必须落实到用户流程。

### 研究链接

- E:/Project/Lenovo CAAI AI Agent/README.md
- E:/Project/Lenovo CAAI AI Agent/docs/ARCHITECTURE.md
- E:/Project/Lenovo CAAI AI Agent/docs/contracts/UI_SERVER_FACT_MATRIX.md
- E:/Project/Lenovo CAAI AI Agent/docs/research/DEMO1-DEMO2-DURABLE-TASK-AND-ADAPTIVE-ORCHESTRATION-RESEARCH-20260830.md
- E:/Project/Lenovo CAAI AI Agent/docs/decisions/DR-0053-durable-task-lineage-and-explainable-topology-admission.md
- E:/Project/Lenovo CAAI AI Agent/docs/decisions/DR-0055-durable-workunit-and-contribution-ledger.md

## P21 技术差异如何一步步改变用户流程

建议时长：2 分钟

用户先说目标，服务端冻结完整允许范围，而不是要求用户提前猜文件；Planner 提议计划，服务端再校验预算、依赖、工具和禁止动作；模型被调用与模型输出被采用是两个事实；证据定位多义时只处理受影响 Branch；最后把 Artifact、说明和外部动作分层。于是前台每一步都能回答用户动作、反馈和后端事实。这个设计与 deep research 的来源控制、MCP Elicitation 的结构化补充请求、HAI Guidelines 的纠正与控制原则相互呼应，但当前实测仍局限于固定公开数据。

转场：流程变化背后，还要关注六个正在改变交互方式的技术方向。

证据/边界：https://help.openai.com/en/articles/10500283-deep-research ；https://modelcontextprotocol.io/specification/draft/client/elicitation ；https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/

预期问题：为什么不让模型自己判断哪些输出可信？

### 研究链接

- https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/
- https://help.openai.com/en/articles/10500283-deep-research
- https://modelcontextprotocol.io/specification/draft/client/elicitation

## P22 六个技术方向，正在改变用户与 AI 的交互方式

建议时长：2 分钟

这页不是再列一组后台名词，而是说明六个技术方向怎样改变用户与 AI 的关系。

第一，持久状态和检查点把交互对象从聊天历史变成任务状态，用户需要看版本、恢复点和分叉。第二，证据锚点与确定性校验要求前台分开模型返回、服务端采用和可验证结果。第三，受治理的多执行单元把多个会话变成依赖、批次、贡献门和统一成果。第四，工具连接和权限标准化扩大可用上下文，也迫使界面说明可读范围、授权和数据去向。第五，动作许可和幂等回执把“确认”扩展为影响预览、风险级别、审批和实际执行事实。第六，MCP 与 A2A 让工具和智能体更容易发现与通信，但协议不替产品决定怎样呈现风险、纠偏和接管。

这些来源支持方向判断，不证明当前方案更好。尤其目标用户是否更容易理解结果、是否降低纠偏成本，仍需任务测试。

转场：这些技术方向最后都要翻译成前台的阅读顺序和反馈。

证据/边界：协议定义连接和运行语义，不规定完整产品交互；用户价值尚未验证。

### 研究链接

- https://docs.langchain.com/oss/python/langgraph/persistence
- https://openai.github.io/openai-agents-python/human_in_the_loop/
- https://modelcontextprotocol.io/specification/draft/client/elicitation
- https://a2a-protocol.org/latest/specification/
- https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/

## P23 前台交互只需要先回答五个问题

建议时长：2 分钟

业务用户首先要知道五件事：完成了什么、依据是什么、为什么停、确认后会改变什么、什么绝不会发生。首屏只放当前结论、成果、复核状态和未执行边界；展开层解释来源、校验、模型说明采用和局部决定；审计层再放 Snapshot、version、named SSE 和 DecisionRecord。这样技术事实没有消失，只是不抢占业务阅读顺序。现在的截图和现场反馈还不是正式用户研究。下一步要让目标用户无引导说出结果、来源、影响和下一步，并用 HEART 记录理解、负担与任务成功。

转场：最后用一套证据计划约束下一阶段结论。

证据/边界：https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ ；https://www.w3.org/WAI/WCAG21/Understanding/status-messages ；https://www.w3.org/WAI/WCAG21/Understanding/target-size ；https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/

预期问题：怎样证明界面真的更清晰？需要目标用户任务测试，不是更多截图。

### 研究链接

- https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/
- https://www.w3.org/WAI/WCAG21/Understanding/status-messages
- https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/

## P24 下一阶段：把实现与研究变成可证伪证据

建议时长：2 分钟

最后把方案设计依据和下一阶段验证放在同一页。

第一类是工程实测：当前系统在固定公开资料上产生的任务状态、成果文件和回执。第二类是竞品同测：不能只读官方文档，要冻结同一任务、模型、来源和预算比较用户究竟审什么。第三类是文献与标准：ReAct、Human-AI Interaction Guidelines、MCP、A2A、持久执行和人工审批说明可采用的机制与设计原则。第四类是目标用户研究：让真实办公用户在无引导条件下说明当前结果、依据、影响和下一步，并记录理解、纠偏负担、接管效率与任务成功。

任何一类都不能单独证明优势。只有工程结果可复现、竞品同测可对照、来源可追溯、目标用户能够理解，而且失败和未实现边界保持可见，差异候选才可以升级为对外结论。

转场：本次汇报到这里，评审重点是是否同意按这四类证据继续验证。

证据/边界：当前没有目标用户研究，不承诺全面领先、生产 SLA 或用户价值提升。

### 研究链接

- https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/
- https://modelcontextprotocol.io/specification/draft/client/elicitation
- https://a2a-protocol.org/latest/specification/
- https://www.w3.org/TR/prov-o/
- https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/
