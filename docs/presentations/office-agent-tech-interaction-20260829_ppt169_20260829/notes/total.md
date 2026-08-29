# 01_会回答不等于可交付

这次汇报大部分内容沿用 07-16 的主线：未来办公 Agent 不是把聊天做得更长，而是让工作在持续、协作、治理和交付四个方向上收敛。右侧是当前系统真实 Workspace，15 个目录、96 份输入文件说明我们已经把抽象架构放进一个固定办公资料环境。今天新增的重点只有两个：第一，主流方案现在发展到哪里；第二，技术差异怎样具体改变用户动作和前台反馈。当前截图来自公开 FORTE 固定数据，不是企业生产环境，也不证明用户价值。

转场：先看 07-16 的三个 Demo 分工在当前版本里发生了什么变化。

证据/边界：当前系统实测；不把截图当作正式用户研究。

预期问题：这次相对 07-16 到底新增了什么，而不是换了一套说法？

---

# 02_谁有资格成为当前结论

07-16 把三个 Demo 分成时间连续性、复杂任务组织和动作风险。这个分工保留不变。当前版本真正补上的，是把每个 Demo 的进展落到 Workspace 范围、Branch 证据门、真实 Artifact 和未执行边界。对用户而言，界面不再只说 Agent 正在运行，而要说明为什么停、从哪里继续、谁在做、依赖什么、确认后会改变什么。这里的设计依据来自 Microsoft HAI Guidelines 对能力边界、上下文和纠正控制的要求，以及 ReAct 对环境反馈循环的启发。它们支持设计方向，不证明当前方案优于竞品。

转场：下面回到 07-16 的核心架构，解释这些状态由谁负责。

证据/边界：https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ ；https://arxiv.org/abs/2210.03629

预期问题：为什么一定要拆成三个 Demo，而不是做一个大而全的 Agent？

---

# 03_主流方案在审什么

这一页完整继承 07-16 的“一个底座、两层增强、三类控制”。统一 Runtime 负责 Task、State、Context、Execution、Capability、Evidence、Policy 和 Trace；长任务用 Agent Control Loop 增强，复杂任务用 Governed Adaptive Swarm 增强；Task、Evidence、Action 三类控制贯穿所有层。需要把当前边界说透：现在真实存在的是受限单 Loop、固定成果适配器和 Snapshot/SSE；多 Worker、通用 Tool Gateway、真实 Connector 仍是目标。线上运行时实践说明持久状态、人机暂停和恢复是常见方向，但业务语义仍需应用自己定义。

转场：把底座继续拆开，就是 07-16 的八个稳定职责。

证据/边界：https://docs.langchain.com/oss/javascript/langgraph/persistence ；https://openai.github.io/openai-agents-python/human_in_the_loop/

预期问题：哪些模块已经能跑，哪些只是目标架构？

---

# 04_技术差异改变用户流程

八个模块不是为了把架构画复杂，而是让每个用户状态都有责任主体。Catalog 负责能看什么，Task Contract 负责目标与范围，Planner 提议路径，Policy Compiler 决定能不能启动。后四项里，当前 Scheduler 只有受限单 Loop，Tool Gateway 还没有通用接入，Artifact 与 Verifier 依靠固定适配器，Checkpoint 和 Governance 有 Snapshot、SSE 与可选 PostgreSQL 恢复子集。用户不会直接操作模块名，但会看到浏览与回开、分支与依赖、成果与校验、暂停与恢复。蓝、橙、灰分别表示当前、部分和目标，不能互相替代。

转场：这些模块为什么会逐步出现，下一页沿着技术演进说明。

证据/边界：当前系统实测；MCP、ReAct、LangGraph 只作线上架构参照。

预期问题：八个模块会不会让前台变得更复杂？

---

# 05_固定挑战现场

这页把 07-16 的 P05 到 P09 合并成一条链。Prompt Engineering 关注一次指令与示例；ReAct 把工程对象扩展到 Action 和 Observation；Context Engineering 开始管理系统指令、工具、外部数据和历史；Harness Engineering 再把权限、沙箱和工具环境纳入系统；Loop Engineering 是我们对触发、验证、记录和恢复的方案归纳。最后一步是办公交付：业务成果、来源、人工决定和未执行边界都可复核。需要强调，这些阶段名不是学界统一年表，而是为了说明系统责任为什么不断外扩。

转场：接下来不按功能打勾，而按用户实际审查的对象看主流方案。

证据/边界：https://arxiv.org/abs/2005.14165 ；https://arxiv.org/abs/2210.03629 ；https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents ；https://docs.langchain.com/oss/javascript/langgraph/persistence

预期问题：Loop Engineering 是正式术语还是本方案的归纳？

---

# 06_主流方案的交互对象

Microsoft 365 Copilot 让用户引用文件、邮件、会议和站点；ChatGPT deep research 让用户审研究计划、来源、实时进度和带引用报告；Codex App 把 Task、隔离工作区、Diff 和审查队列做成核心对象；Claude Code 围绕项目会话、工具动作和验证结果；OpenClaw 围绕 Gateway Task、路由、会话与审批；ReAct 提供 Action-Observation 的基础循环。这里不做胜负判断，也不从官方文档未提及推断竞品做不到。Office Agent 的候选差异，是把资料、业务结论、成果、人工决定和未执行边界放进同一审查链。

转场：这个差异只有落到用户流程上才有意义。

证据/边界：https://support.microsoft.com/en-US/Microsoft-365-Copilot/refer-to-specific-files-and-more-in-microsoft-365-copilot ；https://help.openai.com/en/articles/10500283-deep-research ；https://openai.com/index/introducing-the-codex-app/ ；https://code.claude.com/docs/en/how-claude-code-works ；https://docs.openclaw.ai/automation/tasks ；https://arxiv.org/abs/2210.03629

预期问题：你们能否证明这些产品没有类似的业务治理能力？答案是不能，尚未同场实测。

---

# 07_技术差异改变流程

用户先说目标，服务端冻结完整允许范围，而不是要求用户提前猜文件；Planner 提议计划，服务端再校验预算、依赖、工具和禁止动作；模型被调用与模型输出被采用是两个事实；证据定位多义时只处理受影响 Branch；最后把 Artifact、说明和外部动作分层。于是前台每一步都能回答用户动作、反馈和后端事实。这个设计与 deep research 的来源控制、MCP Elicitation 的结构化补充请求、HAI Guidelines 的纠正与控制原则相互呼应，但当前实测仍局限于固定公开数据。

转场：当这条流程跨多轮运行，风险会被循环放大。

证据/边界：https://help.openai.com/en/articles/10500283-deep-research ；https://modelcontextprotocol.io/specification/draft/client/elicitation ；https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/

预期问题：为什么不让模型自己判断哪些输出可信？

---

# 08_长任务Loop风险

方向漂移、上下文退化、错误复利、成本扩张、权限漂移和停止困难，是 07-16 已经提出的六类风险。它们对应六个前台问题：目标是否仍一致、用了哪版来源、预算还剩多少、允许什么动作、哪条 Branch 受影响、如何暂停恢复或接管。这里不能夸大当前实现：系统最多三轮，pause 和 stop 只在模型调用之间的安全点生效，也不会硬取消在途 HTTP。它解决了一部分状态透明与局部恢复问题，还不是无限自治的长任务执行器。

转场：下一页把 Observe、Plan、Act、Verify、Commit 和外围控制放在一起看。

证据/边界：https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents ；https://docs.langchain.com/oss/javascript/langgraph/persistence ；https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/

预期问题：三轮预算是否足够？当前只能说它是固定上限，不是所有任务的合理预算。

---

# 09_Agent_Control_Loop

中心五段里，Observe 和 Plan 已有清晰纵切；Act 仍主要是只读分析和固定成果适配器；Verify 能做 Schema、引用定位和部分确定性成果检查；Commit 是 append-only 的逻辑 ArtifactVersion 与 TaskCommit。外围控制里，Task Contract、Evidence Gate 和 Trace 较完整，Budget、Steer/Pause、Durable State 是部分近似，Takeover 和通用执行仍缺。旧审计曾给出约 30% 的历史架构成熟度基线，但那不是当前覆盖率，更不是模型质量。现阶段最准确的说法是：有反馈与恢复的只读办公任务纵切。

转场：下面不再讲抽象模块，直接看六个办公场景。

证据/边界：https://docs.langchain.com/oss/javascript/langgraph/persistence ；https://openai.github.io/openai-agents-python/human_in_the_loop/ ；https://a2a-protocol.org/dev/specification/

预期问题：什么时候可以把它称为完整 Control Loop？

---

# 10_六个办公场景

六个场景覆盖了成果、证据、人工判断和外部动作四种风险。TC-01 看成果与引用定位怎样分离；TC-05 看统计和会计判断怎样分离；TC-06、TC-07 把招聘与法务的最终权威留给人；TC-10 把文档产出和真实外呼拆开；TC-14、TC-15 处理来源冲突和模型说明冲突。每个场景都用同一条讲法：触发、Agent 路径、停顿、前台输出、后端事实和当前边界。这样场景不是故事，而是可以复现、失败和升级的测试。

转场：先从用户反馈最强烈的入职资产匹配开始。

证据/边界：https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ ；https://www.w3.org/TR/prov-o/ ；https://openai.github.io/openai-agents-python/human_in_the_loop/

预期问题：这些场景是不是为了 Demo 人工定制？答案是固定适配器范围内验证，尚未通用化。

---

# 11_TC01入职资产

用户输入的是根据时间表和规则生成 3 月 20 日到 4 月 20 日的资产匹配表。旧界面把已生成成果、引用定位缺口和 Loop 等待状态混在一起，用户自然会以为任务失败。实际上三件事可以同时成立：资产表通过文件检查；某段逐字 quote 在预览中出现多次，无法唯一定位；用户只需处理这一处审计问题。“缺一份引用”缺的是唯一可回开的定位，不是缺源文件，也不代表日期算错。当前前台把成果置顶、同源缺口合并，并说明补定位不影响现有成果。

转场：下一页继续回答“三期输入为什么只有两类统计文件”。

证据/边界：https://platform.claude.com/docs/en/build-with-claude/citations ；https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ ；左侧为用户反馈样本，非正式目标用户研究。

预期问题：为什么服务端不能总是一次定位准确？因为当前主要依靠逐字 quote 与安全预览匹配，格式原生 Locator 仍需补齐。

---

# 12_TC05三期往来款

这里需要纠正一个容易产生的理解：三份输入工作簿，不是三期各输出一份统计。未付统计和未收统计只看最新 2026 期，分别提取正数贷方与正数借方期末余额；当前固定来源是 31 条和 2 条。真正使用三个期间的是跨期核对说明，它比较同一科目和客商的借方余额是否连续不变，当前风险候选为 0。前台必须在下载前解释三份成果各自代表什么。统计和候选都不是会计处置，系统没有付款、核销或记账。

转场：财务判断要保留人工门，招聘和法务更是如此。

证据/边界：https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ ；https://www.w3.org/TR/prov-o/ ；数字仅属于当前固定来源版本。

预期问题：0 条候选是否等于不存在僵尸账款？不等于，只表示这套固定启发式没有命中。

---

# 13_高影响判断人工门

招聘场景读取两份 JD 和五份简历，输出候选顺序、支持证据、缺失信息和复核项；材料冲突时进入待复核，系统不执行录用或淘汰。法务场景从六份授权文件抽取主体、期限和范围，形成规则台账与风险候选；不一致时不自动裁决，也不代表法律意见或签署动作。两边共同体现 HAI Guidelines 的原则：系统要说明能力边界、给出上下文、允许用户纠正，并在高影响决定中保留人的控制权。

转场：有了人工门，还要继续区分“形成方案”和“执行动作”。

证据/边界：https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ ；自动化只验证固定成果，不验证公平性、法律适用性或业务效果。

预期问题：候选建议是否可能放大偏见？可能，因此需要规则、证据、隐私与人工复核共同约束。

---

# 14_方案不等于执行

TC-10 读取来源后生成流程图与 DOCX，这些文件和结构检查是真实发生的；拨号、写 CRM、发短信没有发生，因为没有 Connector receipt。TC-14 的日志存在相互冲突的信号，系统保留支持与反证，生成条件式诊断和止损提案，但不执行 ES 命令，也不触发生产降级。前台不能把“建议下一步”写成“已经执行”，也不能把未接入外部系统显示成失败。更准确的界面是并列展示已发生和未发生，让用户看到业务后果边界。

转场：最后一个场景处理的是模型说明和确定性成果互相冲突。

证据/边界：https://openai.github.io/openai-agents-python/human_in_the_loop/ ；https://modelcontextprotocol.io/specification/draft/client/elicitation ；https://www.w3.org/TR/prov-o/

预期问题：未来接入 Connector 后如何防止重复动作？需要 Permit、版本、幂等和执行回执共同约束。

---

# 15_TC15模型说明对账

TC-15 的确定性成果覆盖 212 行、形成 87 组，P0 到 P4 为 25、40、14、6、2。真实模型调用却声称只看了 60 行，并改写 P0 优先级。如果前台同时展示两套说法，用户会看到假绿和重复待办。当前服务端把模型调用和采用拆开：模型仍是 called=true，但 output_used=false；回执为 contradictory、deterministic_outcome、rejected。两份通过检查的成果继续保留，冲突说明只进入审计轨迹。这个机制只验证固定场景的结构化事实一致性，不是通用真值判断。

转场：从这些场景回到前台，用户真正需要先回答的只有五个问题。

证据/边界：https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ ；https://www.w3.org/WAI/WCAG21/Understanding/status-messages

预期问题：一致就一定正确吗？不一定，一致只说明结构化事实没有冲突。

---

# 16_前台交互五个问题

业务用户首先要知道五件事：完成了什么、依据是什么、为什么停、确认后会改变什么、什么绝不会发生。首屏只放当前结论、成果、复核状态和未执行边界；展开层解释来源、校验、模型说明采用和局部决定；审计层再放 Snapshot、version、named SSE 和 DecisionRecord。这样技术事实没有消失，只是不抢占业务阅读顺序。现在的截图和现场反馈还不是正式用户研究。下一步要让目标用户无引导说出结果、来源、影响和下一步，并用 HEART 记录理解、负担与任务成功。

转场：接下来用四页真实界面，把前面讲的系统纵切完整走一遍。

证据/边界：https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ ；https://www.w3.org/WAI/WCAG21/Understanding/status-messages ；https://www.w3.org/WAI/WCAG21/Understanding/target-size ；https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/

预期问题：怎样证明界面真的更清晰？需要目标用户任务测试，不是更多截图。

---

# 17_我们到底做了什么

这页回答最直接的问题：我们到底做了什么。不是又做了一张 Agent 对话页面，而是把一条办公任务纵切跑通了。

第一层是 Workspace。系统面对的是 15 个顶层目录、96 份输入文件，文件都通过服务端 allowlist、大小、哈希、格式和非链接校验后再进入安全预览。第二层是 Task Contract。用户只写任务目标，服务端冻结可读范围、预算、禁止动作和当前版本。第三层是 Planner 与 Analyst。模型调用、服务端校验和模型输出采用分别记录，不再把“模型返回了”写成“当前结论已经采用”。第四层是 Branch Evidence Gate。某条证据不能唯一定位时，只让受影响分支等待，其他已完成成果继续保留。第五层是真实 Artifact 与回执。当前固定场景可以生成可下载文件，执行具名确定性检查，并把 Snapshot 和有序 Trace 留下来。

右侧不是概念图，而是当前系统完成 TC-01 后的完整运行界面：左侧是资料库，中间是任务、Agent 路径和成果，右侧是有序 Control Loop 记录。

这条链已经证明的是固定公开数据上的受限纵切；尚未证明的是通用语义正确、任意办公文件写入、生产级 Connector 和生产 SLA。

转场：下一页从用户输入开始，看“自主选择资料”具体怎样发生。

证据/边界：当前系统实测；截图来自固定公开数据运行，不是竞品对照或生产环境。

预期问题：这是不是一个为固定 Demo 写死的流程？当前确有固定成果适配器，但 Workspace、合同、分支、证据门、Snapshot 和 Trace 是通用运行时结构。

---

# 18_实操1自主选择资料

用户做的第一件事只有一个：写清业务目标。浏览器不会再要求用户先勾选文件，也不会提交客户端的 selected_file_refs。这样减少了一个“用户必须先知道答案在哪里”的前置负担。

服务端创建 Run 时冻结完整 allowlisted 输入索引，scope_mode 是 whole_workspace。Planner 看到的是安全元数据，而不是绝对路径、隐藏任务、答案或内部哈希；它提出本轮需要的资料和分支，服务端再校验预算、来源、依赖、工具和禁止动作。

前台因此必须补上三类反馈。第一，解释本轮为什么选择这些资料；第二，区分规划模型和分析模型是否调用、输出是否被采用；第三，持续显示当前轮次、剩余调用预算、阶段和有序 Trace。用户少做了文件选择，但系统多承担了范围解释责任。

这里不能把“自主选择资料”说成“已经穷举所有相关资料”。当前最多三轮，选择仍可能不完整，所以完成结果仍需证据核对、成果检查和人工复核。

转场：如果选择到的来源文字不能唯一定位，系统不会把整项任务推倒重来。

证据/边界：当前系统实测；全库范围、服务端 Planner 和前台 Trace 的显示均以本次 Snapshot 为准。

预期问题：为什么不把全部 96 份文件都交给模型？因为服务端需要控制上下文、成本和来源范围，并保留每轮选择依据。

---

# 19_实操2局部补证恢复

这页展示证据出现歧义时的真实处理。典型情况不是“没有源文件”，而是模型给出的逐字片段在安全预览里出现多次，服务端无法唯一决定应该回开哪一处。

界面先用业务语言回答三件事：发生了什么、这会影响什么、用户现在需要做什么。然后给出候选原文位置和安全预览高亮。用户选择的是来源位置，不是在替 Agent 判断结论一定正确。

右下角的小图展示同一轮里不同 Branch 可以有不同动作：一条需要用户确认原文位置，另一条可能只需要继续本分支。DecisionRequest 绑定 expected_version、source_revision、候选和受影响 Branch；来源版本变化时进入 stale，不能把旧选择直接套到新文件。

用户确认后，只恢复目标 Branch。已完成 ArtifactVersion、其他 Branch 和已有核对记录不被覆盖。这是局部恢复和整轮重跑在用户体验上的关键差别。

转场：最后看成果已经生成后，系统如何区分文件事实、业务效果和模型说明。

证据/边界：当前系统实测；位置确认只证明 locator 与来源成员关系，不证明自然语言蕴含、穷举或算术全面正确。

预期问题：为什么还要人选位置？格式原生 Locator 尚未完全覆盖，当前保留可审计的人工决定比服务端猜一个位置更稳妥。

---

# 20_实操3成果校验与说明拒绝

左侧展示成果与业务效果分层。当前固定场景能够在隔离 Run 工作区生成真实文件，用户可以下载；系统还会执行具名确定性检查，并记录 EffectReceipt。与此同时，付款、核销、发送、写 CRM 等未发生动作会继续明确显示为未发生。

右侧展示模型说明与确定性成果冲突时的处理。模型确实被调用，因此 called=true；但它给出的行数或分组与确定性成果不一致时，output_used=false。前台只保留一套当前结论，冲突说明进入审计轨迹，而不是与通过检查的成果并排争夺用户注意力。

这一步把“模型说了什么”和“系统已经采用什么”分开，也把“文件存在”和“业务动作发生”分开。对用户的直接影响，是成果可以先用、依据可以继续审、错误说明不会覆盖事实。

当前边界仍然清楚：固定检查只证明特定字段、结构和效果，不是通用语义真值证明器；成果通过也不代表业务价值或最终判断自动成立。

转场：有了这条实操纵切，最后再看下一阶段怎样把差异候选升级为证据。

证据/边界：当前系统实测；固定成果适配器与叙事对账覆盖既定场景，不外推到任意办公任务。

预期问题：固定检查会不会把模型变得多余？不会，模型仍负责规划、跨资料归纳和提出候选；确定性检查负责约束可复算事实。

---

# 21_下一阶段证据路线

下一阶段仍然延续 07-16 的目标：让工作在约束下持续收敛，但结论必须经过五道证据门。先做 PDF、XLSX、DOCX 的格式原生 Locator；再让 Artifact、EffectReceipt、provenance 和未执行边界一起导出；随后把固定适配器扩展成可配置业务 Verifier；再引入 Worker、Tool、Connector、Permit 和幂等回执；最后冻结同一任务、模型和来源做竞品同场挑战，并开展目标用户研究。只有这些门通过，“差异候选”才可以升级为“已验证优势”。

转场：请评审决定的不是一句“看起来不错”，而是是否同意按这五道门继续生产证据。

证据/边界：https://modelcontextprotocol.io/specification/draft/client/elicitation ；https://a2a-protocol.org/dev/specification/ ；https://www.w3.org/TR/prov-o/ ；https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ ；https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/

预期问题：当前可以对外承诺什么？只能承诺固定公开数据上的系统实测与明确边界，不承诺全面领先、生产 SLA 或用户价值。
