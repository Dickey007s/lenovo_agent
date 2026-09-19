# Office Agent 当前市场竞品研究与可证伪差异

更新时间：2026-09-02  
研究范围：办公套件内嵌智能体、企业知识与智能体平台、通用研究工作台、任务执行工作台，以及相关方法和协议。  
证据口径：竞品只采用官方产品页、帮助中心和规范；Office Agent 只采用当前源码、README、架构文档和已通过验证门的系统事实。

## 一、结论先行

1. 当前市场已经普遍覆盖多来源检索、企业连接、引用回开、研究进度、可中断任务和工作流自动化。Office Agent 不能把这些能力单独写成独占优势。
2. Office Agent 当前最值得验证的差异，不是“能力更多”，而是把资料范围、任务状态、业务分支、来源证据、模型采用、办公成果、人工决策和真实动作放进同一条可核对的事实链。
3. 这仍是候选差异，不是竞品领先结论。尚未完成固定模型、固定资料、固定预算和固定任务的同场实测。
4. Office Agent 当前明显弱于成熟平台的地方，是原生办公连接、源文件写回、跨应用动作、生产认证、远程执行单元、多实例协调和用户研究。
5. “单一流程、固定流程、自适应集群”不是三种互斥产品形态。前两者分别描述执行拓扑与流程生成方式，自适应集群描述受治理的组织增强层。

## 二、先把市场分层

| 赛道 | 代表产品 | 用户主要审查什么 | 与 Office Agent 的关系 |
| --- | --- | --- | --- |
| 办公套件内嵌 | Microsoft 365 Copilot、Google Workspace with Gemini | 邮件、文档、会议、企业资料和跨应用动作 | 直接竞品；强项是原生上下文、权限和真实应用动作 |
| 企业知识与智能体平台 | Glean、Atlassian Rovo、Notion AI | 权限化知识、连接应用、搜索、研究、自动化和业务动作 | 直接竞品；强项是连接广度、企业权限和工作流入口 |
| 通用研究工作台 | ChatGPT 深度研究、Claude Research | 来源范围、研究计划、过程、引用和报告 | 部分直接；强项是开放网络研究和报告体验 |
| 任务执行工作台 | Codex App、Claude Code、OpenClaw | 任务线程、工作区、变更、命令、验证和恢复 | 邻近范式；定义了长任务状态与审查体验的用户预期 |
| 方法与协议 | ReAct、MCP、A2A | 推理循环、工具连接和智能体通信 | 不是竞品；它们不单独定义完整产品、治理或办公交付体验 |

这个分层比“功能勾选表”更重要。相同的“搜索”“暂停”“智能体”字样，在不同产品中可能对应完全不同的工作对象、状态权威和动作边界。

## 三、竞品逐项分析

### 3.1 Microsoft 365 Copilot

- 核心位置：直接嵌入 Microsoft 365 工作内容和权限体系。
- 用户审查对象：工作来源、研究任务、生成内容和应用内动作。
- 当前公开能力：Researcher 可面向工作内容与互联网开展研究；Computer Use 在隔离环境中操作网站或应用，并可在动作前请求确认；Analyst 面向数据分析任务。
- 对 Office Agent 的压力：原生邮件、文档、会议、SharePoint 和真实应用动作不是 Office Agent 当前具备的能力。
- 不能据此推出：官方材料没有展示 Office Agent 当前这套分支级证据门和成果版本合同，不等于 Microsoft 一定没有等价内部机制。

官方依据：

- [Researcher with Computer Use](https://support.microsoft.com/en-us/microsoft-365-copilot/get-started-using-researcher-with-computer-use-in-microsoft-365-copilot-frontier)
- [Researcher agent](https://learn.microsoft.com/en-us/microsoft-365/copilot/researcher-agent)
- [Analyst](https://support.microsoft.com/en-us/microsoft-365-copilot/get-started-with-analyst-in-microsoft-copilot)

### 3.2 Google Workspace with Gemini 与 Workspace Studio

- 核心位置：在 Gmail、Drive、Docs、Chat 等办公应用中统一理解上下文，并把智能体和自动化放入同一套件。
- 用户审查对象：跨应用资料、智能体配置、触发条件和自动化结果。
- 当前公开能力：Workspace Studio 支持创建、管理和分享跨应用智能体与自动化；Workspace Intelligence 强调对办公上下文的统一理解。
- 对 Office Agent 的压力：Google 直接拥有办公应用和动作面，Office Agent 当前只有隔离成果，不写回来源应用。
- Office Agent 仍可验证的方向：把每个结论、缺口、人工决定和动作事实形成更细的可审查合同。

官方依据：

- [Google Workspace Studio](https://workspace.google.com/blog/product-announcements/introducing-google-workspace-studio-agents-for-everyday-work)
- [Workspace Intelligence](https://workspace.google.com/blog/product-announcements/introducing-workspace-intelligence)

### 3.3 Glean

- 核心位置：以权限感知的企业搜索和知识图谱为底座，向助手、深度研究、智能体和动作扩展。
- 用户审查对象：企业资料范围、连接源、引用报告、智能体步骤与连接应用动作。
- 当前公开能力：连接企业系统和互联网，按原权限检索；深度研究生成带完整链接引用的长报告；智能体可组合信息收集、总结、判断和动作。
- 对 Office Agent 的压力：企业连接广度、权限继承、知识图谱和动作生态已经是成熟竞品能力。
- Office Agent 仍可验证的方向：冻结资料版本、分支级证据缺口、模型采用与确定性成果校验之间是否有更清晰的对账关系。

官方依据：

- [Glean 企业人工智能平台](https://www.glean.com/platform)
- [Glean Deep Research](https://docs.glean.com/user-guide/assistant/deep-research)
- [Glean Agents](https://docs.glean.com/agents/introduction)
- [Glean 企业搜索](https://www.glean.com/enterprise-search)

### 3.4 Atlassian Rovo

- 核心位置：以 Jira、Confluence 和 Teamwork Graph 为工作上下文，组合搜索、对话、深度研究、智能体与自动化。
- 用户审查对象：跨产品知识、搜索来源、智能体权限、工作项和自动化动作。
- 当前公开能力：搜索 Atlassian 与第三方应用；深度研究可综合内部资料、连接应用和互联网并输出引用报告；智能体经许可可创建或编辑 Jira、Confluence 内容。
- 对 Office Agent 的压力：Rovo 已经把“查找、理解、行动”放进企业协作平台，并有真实工作项动作。
- Office Agent 仍可验证的方向：对动作未发生、模型未采用、分支只恢复一支等负事实给出更显式的状态证明。

官方依据：

- [Rovo 功能](https://www.atlassian.com/software/rovo/features)
- [什么是 Rovo](https://support.atlassian.com/rovo/docs/what-is-rovo/)
- [Rovo Studio](https://www.atlassian.com/software/rovo/studio)

### 3.5 Notion AI

- 核心位置：把 Notion 页面、数据库、连接应用与互联网统一为日常搜索和研究入口。
- 用户审查对象：来源范围、回答引用、研究问题和连接器动作。
- 当前公开能力：企业搜索可收窄来源并回开引用；研究模式处理开放问题；部分连接器支持在连接应用中采取动作。
- 对 Office Agent 的压力：“全源搜索 + 引用回开”已经是市场基线。
- Office Agent 仍可验证的方向：服务端来源准入、模型返回与采用分离、分支恢复和成果校验能否形成更强的治理合同。

官方依据：

- [Notion Enterprise Search](https://www.notion.com/help/enterprise-search)
- [Notion AI Connectors](https://www.notion.com/help/notion-ai-connectors)

### 3.6 ChatGPT 深度研究

- 核心位置：面向开放网络、文件和连接应用的长时研究工作台。
- 用户审查对象：来源选择、研究计划、运行进度、引用报告和导出文件。
- 当前公开能力：可指定网站和来源，研究计划可审，运行可中断，最终报告带引用并可导出为 Markdown、Word 或 PDF。
- 对 Office Agent 的压力：“有来源、有计划、有进度、可中断、可导出”不能作为独占差异。
- Office Agent 仍可验证的方向：业务分支是否有服务端证据门，成果是否有独立校验回执，人工决定是否不被模型文案替代。

官方依据：

- [ChatGPT 深度研究帮助](https://help.openai.com/en/articles/10500283-deep-research)
- [Introducing deep research](https://openai.com/index/introducing-deep-research/)

### 3.7 Claude Research

- 核心位置：把互联网与已连接内部资料组合成多步研究和带引用报告。
- 用户审查对象：研究开关、补充来源、过程引导和最终引用。
- 当前公开能力：在研究过程中继续引导；通过 Integrations 连接外部工作上下文。
- 对 Office Agent 的压力：多步研究、内部资料和引用也已经是市场基线。
- Office Agent 仍可验证的方向：局部分支恢复、证据位置唯一性、模型未采用状态和办公成果历史。

官方依据：

- [Claude Research](https://support.claude.com/en/articles/11088861-use-research-on-claude)
- [Claude Integrations](https://www.anthropic.com/news/integrations)

### 3.8 Codex App 与 Claude Code

- 核心位置：不是直接办公资料竞品，而是成熟的长任务执行工作台范式。
- 用户审查对象：独立任务、工作区、差异、命令、测试、权限和恢复点。
- 对 Office Agent 的启示：长任务连续、隔离执行、人工审查和可恢复会话已经形成用户预期；Office Agent 需要证明办公资料、业务结论、证据和办公成果也能达到同等可审查性。

官方依据：

- [Codex App](https://openai.com/index/introducing-the-codex-app/)
- [Claude Code 工作原理](https://code.claude.com/docs/en/how-claude-code-works)

### 3.9 OpenClaw、ReAct、MCP 与 A2A

- OpenClaw 是相邻运行时和通道入口，不宜与 Microsoft 365 Copilot 直接做同层产品比较。
- ReAct 是推理与行动循环方法，不是完整产品。
- MCP 规定模型上下文和工具连接方式，不规定任务状态、证据门、成果校验或前台交互。
- A2A 规定智能体间通信与任务协作方式，不自动提供 Office Agent 当前强调的业务证据和办公成果合同。

官方依据：

- [OpenClaw Docs](https://docs.openclaw.ai/)
- [ReAct](https://react-lm.github.io/)
- [MCP Specification](https://modelcontextprotocol.io/specification/)
- [A2A Specification](https://a2a-protocol.org/latest/specification/)

## 四、单一流程、固定流程与自适应集群的关系

这三个词描述的不是同一维度。

### 4.1 单一流程

单一流程描述执行拓扑：一个主控制器按顺序推进任务。它可以处理固定步骤，也可以根据证据动态决定下一轮。

### 4.2 固定流程

固定流程描述流程生成方式：步骤、工具、输入和校验规则在运行前已经确定。它既可以由一个执行单元串行运行，也可以把预先定义的独立步骤并行派发。

### 4.3 自适应集群

自适应集群描述组织增强：服务端先判断工作包是否独立、依赖是否满足、来源是否冻结、预算是否足够、是否只读和是否需要人工确认；满足条件后，才按批次派发多个执行单元。贡献必须经过来源范围、原文锚点和叙事对账，才能进入正常成果历史。

### 4.4 四种组合

| 流程生成方式 | 单一执行拓扑 | 多执行单元拓扑 |
| --- | --- | --- |
| 固定 | 固定顺序流水线；最易复现和验证 | 固定分工并行；步骤不随运行证据改变 |
| 自适应 | 当前 Agent Control Loop 主体；每轮按证据选择下一步 | Governed Adaptive Swarm；只在准入通过后动态分工和收敛 |

Office Agent 当前不是“默认一开就多智能体”。它的底座仍是单主控制器的自适应循环；自适应集群只是一层受治理增强。当前实现必须由用户明确确认，每批最多三个进程内只读执行单元，并按依赖波次顺序推进；它不是远程、分布式或高可用集群。

## 五、按五个审查对象比较

| 审查对象 | 办公套件内嵌 | 企业知识与研究平台 | 任务执行工作台 | Office Agent 当前 |
| --- | --- | --- | --- | --- |
| 工作对象 | 邮件、文档、会议、企业图谱 | 网页、文件、连接应用、企业知识 | 仓库、终端、任务线程 | 冻结资料库、任务、运行、分支 |
| 持久状态 | 应用活动、自动化流程 | 研究计划、来源、报告、智能体运行 | 会话、工作区、检查点 | 双版本状态、分支、成果历史 |
| 证据 | 来源链接、应用上下文 | 引用、步骤、来源列表 | 差异、命令和测试 | 文件引用、原文锚点、分支证据门 |
| 成果 | 文档、消息、图表、自动化 | 带引用报告和导出文件 | 代码修改、分支、合并请求 | 隔离办公成果和独立校验回执 |
| 人工与动作 | 设置范围；动作受平台权限控制 | 审计划、可中断；部分连接器可动作 | 审权限、差异与命令 | 选分支、决策、回滚；外部动作未实现 |

## 六、Office Agent 当前可陈述的候选差异

以下每项都必须带“当前实现”或“候选差异”，不能直接写成市场领先：

1. 资料范围在运行创建时由服务端冻结，浏览器不能偷偷改动本轮整库范围。
2. 模型计划必须通过服务端范围、工具、副作用、人工门和预算校验，才会形成稳定分支。
3. 每个新发现必须绑定批准来源，并至少有一个由服务端唯一定位的原文锚点。
4. 模型“已经返回”和“结果被采用”是两个事实；矛盾或不合规文案可保留为审计回执，但不能进入当前结论。
5. 一个分支缺证时，可以保留其他已采用结果，并只恢复目标分支。
6. 固定本地办公能力会在隔离运行空间生成真实文件，并由独立校验器产生回执。
7. 成果版本和任务提交是追加式历史；回滚只移动逻辑指针，不删除历史或修改源文件。
8. 计划、人工批准、实际执行和“没有执行”必须分别展示，不能把建议写成已发生动作。

## 七、当前不能声称的差异

1. 不能声称已经优于 Microsoft、Google、Glean、Rovo、Notion、ChatGPT 或 Claude。
2. 不能声称多来源、整库、引用、暂停、恢复、研究计划或连接器是独占能力。
3. 不能把当前最多三个进程内只读执行单元写成分布式集群。
4. 不能把 `completed` 写成业务正确、生产可用、用户价值或外部动作已经发生。
5. 不能声称会写回原 Office 文件、发送消息、更新客户系统、拨号或执行外部业务动作。
6. 不能把自动化截图和工程测试当成用户研究或效率提升证据。

## 八、固定配置同场实测建议

只有完成以下同场实验，候选差异才可能升级为市场结论。

### 8.1 固定条件

- 同一组公开办公资料。
- 同一任务指令和成功条件。
- 尽可能相同的模型档位、运行时间和调用预算。
- 明确记录每个平台允许的连接器、权限和人工步骤。
- 输出原始运行记录、引用、下载文件和人工操作录像。

### 8.2 至少验证四个核心问题

1. 结论能否回到唯一且可打开的原文位置？
2. 证据不足后，能否只补目标分支而不重做已通过部分？
3. 声称生成的办公成果是否真的存在，并可独立复验？
4. 计划、模型建议、人工批准和真实执行是否被明确分开？

### 8.3 建议记录的指标

- 来源命中率与无效引用率。
- 原文定位唯一率与定位失败恢复率。
- 分支局部恢复比例和重复工作量。
- 成果下载成功率、结构校验通过率和独立复验通过率。
- 模型返回但未采用的可见性。
- 未执行动作被误报为已执行的次数。
- 完成时间、模型调用量、人工确认次数和恢复次数。

这些指标应作为验证协议，不应在实测前用于打分或宣布胜负。

## 九、PPT 图像来源

增强版 PPT 新增九张界面或结构图，均来自官方页面或当前系统真实截图：

| 图像 | 来源 |
| --- | --- |
| Microsoft Researcher | [Microsoft Support](https://support.microsoft.com/en-us/microsoft-365-copilot/get-started-using-researcher-with-computer-use-in-microsoft-365-copilot-frontier) |
| Google Workspace Studio | [Google Workspace Blog](https://workspace.google.com/blog/product-announcements/introducing-google-workspace-studio-agents-for-everyday-work) |
| Notion Enterprise Search | [Notion Help](https://www.notion.com/help/enterprise-search) |
| ChatGPT 指定网站研究 | [OpenAI Help](https://help.openai.com/en/articles/10500283-deep-research) |
| Claude Research | [Claude Support](https://support.claude.com/en/articles/11088861-use-research-on-claude) |
| Codex App 多任务界面 | [OpenAI](https://openai.com/index/introducing-the-codex-app/) |
| Claude Code 执行循环 | [Claude Code Docs](https://code.claude.com/docs/en/how-claude-code-works) |
| Office Agent 执行进展 | 当前系统真实界面 |
| Office Agent 证据核对 | 当前系统真实界面 |

## 十、Office Agent 内部事实依据

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/contracts/UI_SERVER_FACT_MATRIX.md`
- `docs/PRESENTATION_BRIEF.md`
- `docs/research/DEMO1-DEMO2-DURABLE-TASK-AND-ADAPTIVE-ORCHESTRATION-RESEARCH-20260830.md`
- `docs/decisions/DR-0053-durable-task-lineage-and-explainable-topology-admission.md`
- `docs/decisions/DR-0055-durable-workunit-and-contribution-ledger.md`

## 十一、研究边界

- 本文是官方资料与当前实现的结构化分析，不是采购建议或最终竞品排名。
- 官方资料能说明产品公开定位和能力重点，不能据其未提及内容推断竞品一定缺少某种内部实现。
- Office Agent 当前证据来自工程纵切、固定公开数据和隔离验证门，不证明任意办公任务质量、生产可靠性或业务价值。
