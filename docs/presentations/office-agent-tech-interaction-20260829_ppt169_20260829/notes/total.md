# 01_会回答不等于可交付

这次汇报大部分内容沿用 07-16 的主线：未来办公 Agent 不是把聊天做得更长，而是让工作在持续、协作、治理和交付四个方向上收敛。右侧换成当前 Agent 能力页的真实运行截图；它把任务进展、协作方式和证据核对按需展开。15 个目录、96 份输入文件仍是这条能力链的固定办公资料环境。今天新增的重点只有两个：第一，主流方案现在发展到哪里；第二，技术差异怎样具体改变用户动作和前台反馈。当前截图来自公开 FORTE 固定数据，不是企业生产环境，也不证明用户价值。

转场：先看 07-16 的三个 Demo 分工在当前版本里发生了什么变化。

证据/边界：当前系统实测；不把截图当作正式用户研究。

预期问题：这次相对 07-16 到底新增了什么，而不是换了一套说法？

# 02_谁有资格成为当前结论

07-16 把三个 Demo 分成时间连续性、复杂任务组织和动作风险。这个分工保留不变。当前版本真正补上的，是把每个 Demo 的进展落到 Workspace 范围、Branch 证据门、WorkUnit 依赖、Contribution 采用、真实 Artifact 和未执行边界。Demo 2 已经不再只是目标框图：服务端能够给出真实 WorkUnit DAG，并以单进程、显式波次、每波最多三个只读 Worker 形成受控纵切；但它仍不是分布式 Swarm。对用户而言，界面不再只说 Agent 正在运行，而要说明为什么停、从哪里继续、谁依赖谁、哪一批需要确认、确认后会改变什么。这里的设计依据来自 Microsoft HAI Guidelines 对能力边界、上下文和纠正控制的要求，以及 ReAct 对环境反馈循环的启发。它们支持设计方向，不证明当前方案优于竞品。

转场：下面回到 07-16 的核心架构，解释这些状态由谁负责。

证据/边界：https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ ；https://arxiv.org/abs/2210.03629

预期问题：为什么一定要拆成三个 Demo，而不是做一个大而全的 Agent？

# 03_一个底座两层增强三类控制

这一页先不要急着记英文名，只看三层关系。最下面的统一 Agent Runtime 是每个任务都要经过的底座，它稳定承接任务、状态、上下文、执行、能力、证据、策略和追踪。没有这层，Agent 仍然只是一次模型调用，任务中断以后不知道从哪里继续，也无法说明某个结论或动作来自哪一步。

第一层增强是 Agent Control Loop。它只在任务需要多轮推进、等待补证或恢复时发挥价值。07-16 希望它解决时间维连续性；当前已经落地的是受限单 Loop、服务端 Branch、Evidence Gate、ArtifactVersion 和 Snapshot/SSE。第二层增强是 Governed Adaptive Swarm，它面向高价值、跨来源、可并行的复杂工作。当前已经形成最小受控纵切：Topology Admission、WorkUnit DAG、每波最多三个进程内只读 Worker、Contribution Gate 与统一 Artifact；但 durable queue、远端 Worker、通用 Resolver 和多实例调度仍是目标。

左侧三类控制不是第三层业务能力，而是贯穿所有层的约束。Task Control 决定目标、预算、暂停与停止；Evidence Control 决定来源、冲突、验证和模型说明是否采用；Action Control 决定风险、审批、Permit 和执行回执。它们最终让前台只需要回答三件事：任务现在走到哪，当前结论凭什么成立，哪些动作真的发生了。

转场：下一页把底座拆成八个稳定职责，并说明每两个模块共同回答一个用户问题。

证据/边界：https://docs.langchain.com/oss/javascript/langgraph/persistence ；https://openai.github.io/openai-agents-python/human_in_the_loop/ ；https://modelcontextprotocol.io/specification/draft/client/elicitation

预期问题：为什么不把所有任务都放进 Loop 或 Swarm？因为增强层有额外状态与协调成本，只有任务的时间跨度和组织复杂度值得时才应启用。

# 04_八个稳定职责

八个模块不是八个前台页面，而是一次任务从定范围到可恢复的四段责任链。

第一段是“定范围”。Workspace Catalog & Safe Preview 负责哪些资料可以安全读取，Task Contract 负责目标、范围、完成条件和禁止事项。前台要回答的是“你读了哪些资料、任务边界是什么”。

第二段是“定计划”。Planner 可以提出分支、依赖和资料范围，但计划不能因为模型返回就直接运行。Admission、Policy Compiler & Plan Validator 还要校验预算、来源、依赖、工具和副作用。前台要回答的是“为什么这样拆、什么计划被拒绝或修复”。

第三段是“推进执行”。Scheduler & Worker Manager 决定哪个分支先做、依赖谁、何时等待、何时恢复；当前已经支持服务端编译的 WorkUnit DAG、显式波次和每波最多三个进程内只读 Worker。Tool Gateway 仍应统一真实工具的授权、超时、幂等和回执，但当前没有通用实现。前台要回答的是“现在做到哪一步、谁依赖谁、哪个分支受影响、动作是否真的执行”。

第四段是“成果恢复”。Artifact Workspace & Verifier 保存成果版本并执行当前固定场景的确定性检查；Checkpoint, Event & Governance Control 让 Snapshot 成为状态权威，SSE 只做有序投影，并提供可选 PostgreSQL 重启恢复子集。前台要回答的是“结果能否下载、核对、审计和恢复”。

所以模块对后端是职责，对用户只有四个问题：读什么、怎么做、做到哪、结果能不能复核与恢复。蓝色表示当前实现，橙色表示部分近似，灰色表示目标，不能把目标模块写成现有能力。

转场：这些职责为什么会逐步出现，下一页沿技术演进解释系统责任如何外扩。

证据/边界：当前系统实测；ReAct、LangGraph、MCP 与 A2A 只作线上架构参照。

预期问题：八个模块会不会让前台更复杂？不会要求用户操作模块名，但必须把模块产生的关键状态翻译成业务语言。

# 05_固定挑战现场

这页把 07-16 的 P05 到 P09 合并成一条链。Prompt Engineering 关注一次指令与示例；ReAct 把工程对象扩展到 Action 和 Observation；Context Engineering 开始管理系统指令、工具、外部数据和历史；Harness Engineering 再把权限、沙箱和工具环境纳入系统；Loop Engineering 是我们对触发、验证、记录和恢复的方案归纳。最后一步是办公交付：业务成果、来源、人工决定和未执行边界都可复核。需要强调，这些阶段名不是学界统一年表，而是为了说明系统责任为什么不断外扩。

转场：接下来不按功能打勾，而按用户实际审查的对象看主流方案。

证据/边界：https://arxiv.org/abs/2005.14165 ；https://arxiv.org/abs/2210.03629 ；https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents ；https://docs.langchain.com/oss/javascript/langgraph/persistence

预期问题：Loop Engineering 是正式术语还是本方案的归纳？

# 06_主流方案的交互对象

Microsoft 365 Copilot 让用户引用文件、邮件、会议和站点；ChatGPT deep research 让用户审研究计划、来源、实时进度和带引用报告；Codex App 把 Task、隔离工作区、Diff 和审查队列做成核心对象；Claude Code 围绕项目会话、工具动作和验证结果；OpenClaw 围绕 Gateway Task、路由、会话与审批；ReAct 提供 Action-Observation 的基础循环。这里不做胜负判断，也不从官方文档未提及推断竞品做不到。Office Agent 的候选差异，是把资料、业务结论、成果、人工决定和未执行边界放进同一审查链。

转场：这个差异只有落到用户流程上才有意义。

证据/边界：https://support.microsoft.com/en-US/Microsoft-365-Copilot/refer-to-specific-files-and-more-in-microsoft-365-copilot ；https://help.openai.com/en/articles/10500283-deep-research ；https://openai.com/index/introducing-the-codex-app/ ；https://code.claude.com/docs/en/how-claude-code-works ；https://docs.openclaw.ai/automation/tasks ；https://arxiv.org/abs/2210.03629

预期问题：你们能否证明这些产品没有类似的业务治理能力？答案是不能，尚未同场实测。

# 07_技术差异改变流程

用户先说目标，服务端冻结完整允许范围，而不是要求用户提前猜文件；Planner 提议计划，服务端再校验预算、依赖、工具和禁止动作；模型被调用与模型输出被采用是两个事实；证据定位多义时只处理受影响 Branch；最后把 Artifact、说明和外部动作分层。于是前台每一步都能回答用户动作、反馈和后端事实。这个设计与 deep research 的来源控制、MCP Elicitation 的结构化补充请求、HAI Guidelines 的纠正与控制原则相互呼应，但当前实测仍局限于固定公开数据。

转场：当这条流程跨多轮运行，风险会被循环放大。

证据/边界：https://help.openai.com/en/articles/10500283-deep-research ；https://modelcontextprotocol.io/specification/draft/client/elicitation ；https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/

预期问题：为什么不让模型自己判断哪些输出可信？

# 08_长任务Loop风险

方向漂移、上下文退化、错误复利、成本扩张、权限漂移和停止困难，是 07-16 已经提出的六类风险。它们对应六个前台问题：目标是否仍一致、用了哪版来源、预算还剩多少、允许什么动作、哪条 Branch 受影响、如何暂停恢复或接管。这里不能夸大当前实现：系统最多三轮，pause 和 stop 只在模型调用之间的安全点生效，也不会硬取消在途 HTTP。它解决了一部分状态透明与局部恢复问题，还不是无限自治的长任务执行器。

转场：下一页把 Observe、Plan、Act、Verify、Commit 和外围控制放在一起看。

证据/边界：https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents ；https://docs.langchain.com/oss/javascript/langgraph/persistence ；https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/

预期问题：三轮预算是否足够？当前只能说它是固定上限，不是所有任务的合理预算。

# 09_Agent_Control_Loop

中心五段里，Observe 和 Plan 已有清晰纵切；Act 仍主要是只读分析和固定成果适配器；Verify 能做 Schema、引用定位和部分确定性成果检查；Commit 是 append-only 的逻辑 ArtifactVersion 与 TaskCommit。外围控制里，Task Contract、Evidence Gate 和 Trace 较完整，Budget、Steer/Pause、Durable State 是部分近似，Takeover 和通用执行仍缺。旧审计曾给出约 30% 的历史架构成熟度基线，但那不是当前覆盖率，更不是模型质量。现阶段最准确的说法是：有反馈与恢复的只读办公任务纵切。

转场：下面不再讲抽象模块，直接看六个办公场景。

证据/边界：https://docs.langchain.com/oss/javascript/langgraph/persistence ；https://openai.github.io/openai-agents-python/human_in_the_loop/ ；https://a2a-protocol.org/v0.3.0/specification/

预期问题：什么时候可以把它称为完整 Control Loop？

# 10_六个办公场景

六个场景覆盖了成果、证据、人工判断和外部动作四种风险。TC-01 看成果与引用定位怎样分离；TC-05 看统计和会计判断怎样分离；TC-06、TC-07 把招聘与法务的最终权威留给人；TC-10 把文档产出和真实外呼拆开；TC-14、TC-15 处理来源冲突和模型说明冲突。每个场景都用同一条讲法：触发、Agent 路径、停顿、前台输出、后端事实和当前边界。这样场景不是故事，而是可以复现、失败和升级的测试。

转场：先从用户反馈最强烈的入职资产匹配开始。

证据/边界：https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ ；https://www.w3.org/TR/prov-o/ ；https://openai.github.io/openai-agents-python/human_in_the_loop/

预期问题：这些场景是不是为了 Demo 人工定制？答案是固定适配器范围内验证，尚未通用化。

# 11_TC01入职资产

用户输入的是根据时间表和规则生成 3 月 20 日到 4 月 20 日的资产匹配表。旧界面把已生成成果、引用定位缺口和 Loop 等待状态混在一起，用户自然会以为任务失败。实际上三件事可以同时成立：资产表通过文件检查；某段逐字 quote 在预览中出现多次，无法唯一定位；用户只需处理这一处审计问题。“缺一份引用”缺的是唯一可回开的定位，不是缺源文件，也不代表日期算错。当前前台把成果置顶、同源缺口合并，并说明补定位不影响现有成果。

转场：下一页继续回答“三期输入为什么只有两类统计文件”。

证据/边界：https://platform.claude.com/docs/en/build-with-claude/citations ；https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ ；左侧为用户反馈样本，非正式目标用户研究。

预期问题：为什么服务端不能总是一次定位准确？因为当前主要依靠逐字 quote 与安全预览匹配，格式原生 Locator 仍需补齐。

# 12_TC05三期往来款

这里需要纠正一个容易产生的理解：三份输入工作簿，不是三期各输出一份统计。未付统计和未收统计只看最新 2026 期，分别提取正数贷方与正数借方期末余额；当前固定来源是 31 条和 2 条。真正使用三个期间的是跨期核对说明，它比较同一科目和客商的借方余额是否连续不变，当前风险候选为 0。前台必须在下载前解释三份成果各自代表什么。统计和候选都不是会计处置，系统没有付款、核销或记账。

转场：财务判断要保留人工门，招聘和法务更是如此。

证据/边界：https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ ；https://www.w3.org/TR/prov-o/ ；数字仅属于当前固定来源版本。

预期问题：0 条候选是否等于不存在僵尸账款？不等于，只表示这套固定启发式没有命中。

# 13_高影响判断人工门

招聘场景读取两份 JD 和五份简历，输出候选顺序、支持证据、缺失信息和复核项；材料冲突时进入待复核，系统不执行录用或淘汰。法务场景从六份授权文件抽取主体、期限和范围，形成规则台账与风险候选；不一致时不自动裁决，也不代表法律意见或签署动作。两边共同体现 HAI Guidelines 的原则：系统要说明能力边界、给出上下文、允许用户纠正，并在高影响决定中保留人的控制权。

转场：有了人工门，还要继续区分“形成方案”和“执行动作”。

证据/边界：https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ ；自动化只验证固定成果，不验证公平性、法律适用性或业务效果。

预期问题：候选建议是否可能放大偏见？可能，因此需要规则、证据、隐私与人工复核共同约束。

# 14_方案不等于执行

TC-10 读取来源后生成流程图与 DOCX，这些文件和结构检查是真实发生的；拨号、写 CRM、发短信没有发生，因为没有 Connector receipt。TC-14 的日志存在相互冲突的信号，系统保留支持与反证，生成条件式诊断和止损提案，但不执行 ES 命令，也不触发生产降级。前台不能把“建议下一步”写成“已经执行”，也不能把未接入外部系统显示成失败。更准确的界面是并列展示已发生和未发生，让用户看到业务后果边界。

转场：最后一个场景处理的是模型说明和确定性成果互相冲突。

证据/边界：https://openai.github.io/openai-agents-python/human_in_the_loop/ ；https://modelcontextprotocol.io/specification/draft/client/elicitation ；https://www.w3.org/TR/prov-o/

预期问题：未来接入 Connector 后如何防止重复动作？需要 Permit、版本、幂等和执行回执共同约束。

# 15_TC15模型说明对账

TC-15 的确定性成果覆盖 212 行、形成 87 组，P0 到 P4 为 25、40、14、6、2。真实模型调用却声称只看了 60 行，并改写 P0 优先级。如果前台同时展示两套说法，用户会看到假绿和重复待办。当前服务端把模型调用和采用拆开：模型仍是 called=true，但 output_used=false；回执为 contradictory、deterministic_outcome、rejected。两份通过检查的成果继续保留，冲突说明只进入审计轨迹。这个机制只验证固定场景的结构化事实一致性，不是通用真值判断。

转场：从这些场景回到前台，用户真正需要先回答的只有五个问题。

证据/边界：https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ ；https://www.w3.org/WAI/WCAG21/Understanding/status-messages

预期问题：一致就一定正确吗？不一定，一致只说明结构化事实没有冲突。

# 16_前台交互五个问题

业务用户首先要知道五件事：完成了什么、依据是什么、为什么停、确认后会改变什么、什么绝不会发生。首屏只放当前结论、成果、复核状态和未执行边界；展开层解释来源、校验、模型说明采用和局部决定；审计层再放 Snapshot、version、named SSE 和 DecisionRecord。这样技术事实没有消失，只是不抢占业务阅读顺序。现在的截图和现场反馈还不是正式用户研究。下一步要让目标用户无引导说出结果、来源、影响和下一步，并用 HEART 记录理解、负担与任务成功。

转场：接下来用四页真实界面，把前面讲的系统纵切完整走一遍。

证据/边界：https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ ；https://www.w3.org/WAI/WCAG21/Understanding/status-messages ；https://www.w3.org/WAI/WCAG21/Understanding/target-size ；https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/

预期问题：怎样证明界面真的更清晰？需要目标用户任务测试，不是更多截图。

# 17_我们到底做了什么

这页回答最直接的问题：我们到底做了什么。不是又做了一张 Agent 对话页面，而是把一条办公任务纵切跑通了。

第一层是 Workspace。系统面对的是 15 个顶层目录、96 份输入文件，文件都通过服务端 allowlist、大小、哈希、格式和非链接校验后再进入安全预览。第二层是 Task Contract。用户只写任务目标，服务端冻结可读范围、预算、禁止动作和当前版本。第三层是 Planner 与 Analyst。模型调用、服务端校验和模型输出采用分别记录，不再把“模型返回了”写成“当前结论已经采用”。第四层是 Branch Evidence Gate。某条证据不能唯一定位时，只让受影响分支等待，其他已完成成果继续保留。第五层是真实 Artifact 与回执。当前固定场景可以生成可下载文件，执行具名确定性检查，并把 Snapshot 和有序 Trace 留下来。

右侧不是概念图，而是当前系统完成 TC-01 后的完整运行界面：左侧是资料库，中间是任务、Agent 路径和成果，右侧是有序 Control Loop 记录。

这条链已经证明的是固定公开数据上的受限纵切；尚未证明的是通用语义正确、任意办公文件写入、生产级 Connector 和生产 SLA。

转场：下一页从用户输入开始，看“自主选择资料”具体怎样发生。

证据/边界：当前系统实测；截图来自固定公开数据运行，不是竞品对照或生产环境。

预期问题：这是不是一个为固定 Demo 写死的流程？当前确有固定成果适配器，但 Workspace、合同、分支、证据门、Snapshot 和 Trace 是通用运行时结构。

# 18_实操1自主选择资料

用户做的第一件事只有一个：写清业务目标。浏览器不会再要求用户先勾选文件，也不会提交客户端的 selected_file_refs。这样减少了一个“用户必须先知道答案在哪里”的前置负担。

服务端创建 Run 时冻结完整 allowlisted 输入索引，scope_mode 是 whole_workspace。Planner 看到的是安全元数据，而不是绝对路径、隐藏任务、答案或内部哈希；它提出本轮需要的资料和分支，服务端再校验预算、来源、依赖、工具和禁止动作。

前台因此必须补上三类反馈。第一，解释本轮为什么选择这些资料；第二，区分规划模型和分析模型是否调用、输出是否被采用；第三，持续显示当前轮次、剩余调用预算、阶段和有序 Trace。用户少做了文件选择，但系统多承担了范围解释责任。

这里不能把“自主选择资料”说成“已经穷举所有相关资料”。当前最多三轮，选择仍可能不完整，所以完成结果仍需证据核对、成果检查和人工复核。

转场：如果选择到的来源文字不能唯一定位，系统不会把整项任务推倒重来。

证据/边界：当前系统实测；全库范围、服务端 Planner 和前台 Trace 的显示均以本次 Snapshot 为准。

预期问题：为什么不把全部 96 份文件都交给模型？因为服务端需要控制上下文、成本和来源范围，并保留每轮选择依据。

# 19_实操2局部补证恢复

这页展示证据出现歧义时的真实处理。典型情况不是“没有源文件”，而是模型给出的逐字片段在安全预览里出现多次，服务端无法唯一决定应该回开哪一处。

界面先用业务语言回答三件事：发生了什么、这会影响什么、用户现在需要做什么。然后给出候选原文位置和安全预览高亮。用户选择的是来源位置，不是在替 Agent 判断结论一定正确。

右下角的小图展示同一轮里不同 Branch 可以有不同动作：一条需要用户确认原文位置，另一条可能只需要继续本分支。DecisionRequest 绑定 expected_version、source_revision、候选和受影响 Branch；来源版本变化时进入 stale，不能把旧选择直接套到新文件。

用户确认后，只恢复目标 Branch。已完成 ArtifactVersion、其他 Branch 和已有核对记录不被覆盖。这是局部恢复和整轮重跑在用户体验上的关键差别。

转场：最后看成果已经生成后，系统如何区分文件事实、业务效果和模型说明。

证据/边界：当前系统实测；位置确认只证明 locator 与来源成员关系，不证明自然语言蕴含、穷举或算术全面正确。

预期问题：为什么还要人选位置？格式原生 Locator 尚未完全覆盖，当前保留可审计的人工决定比服务端猜一个位置更稳妥。

# 20_实操3成果校验与说明拒绝

左侧展示成果与业务效果分层。当前固定场景能够在隔离 Run 工作区生成真实文件，用户可以下载；系统还会执行具名确定性检查，并记录 EffectReceipt。与此同时，付款、核销、发送、写 CRM 等未发生动作会继续明确显示为未发生。

右侧展示模型说明与确定性成果冲突时的处理。模型确实被调用，因此 called=true；但它给出的行数或分组与确定性成果不一致时，output_used=false。前台只保留一套当前结论，冲突说明进入审计轨迹，而不是与通过检查的成果并排争夺用户注意力。

这一步把“模型说了什么”和“系统已经采用什么”分开，也把“文件存在”和“业务动作发生”分开。对用户的直接影响，是成果可以先用、依据可以继续审、错误说明不会覆盖事实。

当前边界仍然清楚：固定检查只证明特定字段、结构和效果，不是通用语义真值证明器；成果通过也不代表业务价值或最终判断自动成立。

转场：有了这条当前纵切，下面把它重新放回 07-16 的三个 Demo，分别看时间、组织和动作三个维度哪些已经落地、哪些仍是目标。

证据/边界：当前系统实测；固定成果适配器与叙事对账覆盖既定场景，不外推到任意办公任务。

预期问题：固定检查会不会把模型变得多余？不会，模型仍负责规划、跨资料归纳和提出候选；确定性检查负责约束可复算事实。

# 21_Demo1时间维连续性

Demo 1 来自 07-16 的时间维连续性。目标不是让 Agent 永远运行，而是让同一个 Task ID 在多轮任务中有稳定的任务契约、状态版本、分支和恢复点。流程仍然是 Task Contract、Observe、Plan、Act、Verify、Commit。

07-16 的关键镜头是 Verify 同时发现正式口径 2,400 万和预测口径 2,680 万。正确处理不是整项任务失败，也不是让模型自行选择，而是 Evidence Gate 只让 revenue-baseline 分支进入 waiting_input；customer-facts 和 project-risk 分支继续产出并保留。用户给出 Steer，采用正式口径并保留预测差异说明，系统只恢复受影响分支，最后把版本、来源、验证结果和 Trace 一起 Commit。

当前系统已经具备服务端 Branch、分支级 Evidence Gate、append-only ArtifactVersion、TaskCommit、局部恢复和可选 PostgreSQL 重启恢复。还没有生产级跨端身份、任意办公工件写入和长期后台 Worker。因此这一页不是把 07-16 演示冒充当前实测，而是说明我们已经完成了其中最关键的一段状态与证据纵切。

前台变化是用户不必重开对话、重讲背景；他在同一任务里看见哪个分支完成、哪个分支为何停、选择后恢复什么、旧成果是否保留。

转场：时间连续性解决以后，Demo 2 处理的是同时有很多待办和复杂分工时，工作如何被组织。

证据/边界：https://docs.langchain.com/oss/javascript/langgraph/persistence ；https://openai.github.io/openai-agents-python/human_in_the_loop/

预期问题：现在已经支持手机和电脑控制同一生产任务吗？没有，当前证明的是服务端状态、分支与恢复机制，生产身份和跨端控制仍是目标。

# 22_Demo2组织维复杂性

Demo 2 仍然保留 07-16 的智能工作驾驶舱作为目标产品面，但这一页不再只讲目标框图，而是先回答一个可以直接演示的输入、过程和输出。

输入是一条复杂但只读的办公任务：分别核对产品上线、搜索 Agent 运行和用户交互三条工作线的风险与证据，先独立核对，再形成统一简报。用户不需要指定五个 Agent，也不需要自己分配会话。

过程由服务端事实决定。Topology Admission 编译出五个 WorkUnit，其中三个是根工作包，两个依赖前序结果。第一波返回后，三个 Contribution 分别进入采用门；只有带批准来源和可定位证据的候选才能进入 Artifact。两个依赖工作包显示“下一波待确认”，由用户明确启动，而不是后台无声扩张预算。

输出是一个统一工作面：左侧阶段轨回答现在走到哪，中央 DAG 回答谁依赖谁，右侧当前影响只突出唯一主要动作，底部结果条说明三份贡献已经采用、Artifact v1 已保留、还有两个工作包待确认。用户管理的是统一成果和下一步，不是多个 Agent 对话。

边界必须讲清：这是单 API 进程、顺序波次、每波最多三个只读 Worker 的 controlled fixture。它不是 durable queue、远端 Worker、分布式 Swarm，也不是已经完成的智能工作驾驶舱；自动化和截图同样不能证明多 Worker 更快、更准或更易理解。

转场：无论任务由单 Agent、Workflow 还是 Swarm 完成，只要下一步涉及真实发送、付款或生产变更，都要进入 Demo 3 的动作风险门。

证据/边界：https://docs.openclaw.ai/concepts/multi-agent ；https://a2a-protocol.org/v0.3.0/specification/ ；https://www.nngroup.com/articles/progressive-disclosure/

预期问题：多 Agent 一定比单 Agent 好吗？不一定，当前也没有效果证据；只有同任务、同模型、同来源和同预算下的增量收益高于协调与验证开销时，才应该启动 Adaptive 路线。

# 23_Demo3动作维风险控制

Demo 3 保留 07-16 的 Risk Gate。Risk Lens 从动作影响、数据敏感度、可逆性、权限和缺失信息评估风险，再映射到 L0-L5：L0 自动执行，L1 执行并通知，L2 只生成草稿，L3 普通确认，L4 强确认，L5 直接拒绝。

真正关键的是动作链。Agent 先提出方案，前台展示动作对象、影响范围和可逆性；Evidence Gate 与 Risk Lens 给出来源和风险理由；需要人工确认时，用户明确同意后才生成 Permit；执行后必须返回可核验的 ExecutionReceipt，或者明确写出动作未发生。这样“方案”“草稿”“批准”和“执行”不会被混成一个绿色完成状态。

页面下半部分使用当前真实界面截图，说明目前已经实现的有限一段：实际 Artifact、具名 Validator、EffectReceipt 和未发生边界可以分层展示。但生产 Connector、身份授权、Permit 防重放与真实外部动作仍未实现，所以系统不会发送邮件、付款、写 CRM 或执行生产命令。

前台的直接变化是按钮不能只写“确认”。用户必须先看见对象、影响、证据、风险级别、可逆性和执行回执，才能知道自己的点击究竟会改变什么。

转场：三个 Demo 的方向保留，但下一步必须继续用可证伪证据而不是更多概念升级结论。

证据/边界：https://openai.github.io/openai-agents-python/human_in_the_loop/ ；https://modelcontextprotocol.io/specification/draft/client/elicitation ；https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/

预期问题：当前是不是已经具备 L0-L5 的生产执行能力？没有，L0-L5 是目标控制模型，当前只有固定成果和未执行边界的有限实现。

# 24_下一阶段证据路线

下一阶段仍然延续 07-16 的目标：让工作在约束下持续收敛，但结论必须经过五道证据门。先做 PDF、XLSX、DOCX 的格式原生 Locator；再让 Artifact、EffectReceipt、provenance 和未执行边界一起导出；随后把固定适配器扩展成可配置业务 Verifier；再把当前进程内 Worker 纵切升级为 durable queue/lease、远端 Worker 和多实例恢复，并接入 Tool、Connector、Permit 与幂等动作回执；最后冻结同一任务、模型、来源和预算做竞品同场挑战，并开展目标用户研究。只有这些门通过，“差异候选”才可以升级为“已验证优势”。

转场：请评审决定的不是一句“看起来不错”，而是是否同意按这五道门继续生产证据。

证据/边界：https://modelcontextprotocol.io/specification/draft/client/elicitation ；https://a2a-protocol.org/v0.3.0/specification/ ；https://www.w3.org/TR/prov-o/ ；https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ ；https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/

预期问题：当前可以对外承诺什么？只能承诺固定公开数据上的系统实测与明确边界，不承诺全面领先、生产 SLA 或用户价值。
