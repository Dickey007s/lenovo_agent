# 线上研究来源与 07-16 内容继承表

## 使用规则

- 07-16《未来办公 Agent：Loop、Swarm 与受治理执行》是本次 PPT 的内容骨架，不作为外部研究来源。
- README、Decision、Scenario、Evidence 和内部详细报告只用于核对当前系统事实，不在页面上冒充研究、竞品调研、文献或用户研究来源。
- 竞品判断只依据线上官方材料；“官方材料未强调某能力”不能推出竞品做不到。
- 当前界面截图标为“当前系统实测”；现场反馈标为“用户反馈样本，非正式目标用户研究”。

## 07-16 内容继承

| 本次页码 | 继承的 07-16 内容 | 本次只补充什么 |
| --- | --- | --- |
| 01 | P01 从跨端聊天到可治理工作系统 | 当前 Workspace 实景 |
| 02 | P02 能力跃迁与三个 Demo 分工 | 当前真实纵切和缺口 |
| 03 | P03 一个底座、两层增强、三类控制 | 当前实现/目标边界 |
| 04 | P04 八个最小运行时组件 | 统一模块名和前台投影 |
| 05 | P05-P09 Prompt、Loop、Context、Harness、Loop Engineering | 线上论文与官方来源 |
| 08 | P10 长任务方向漂移风险 | 当前最多三轮只读边界 |
| 09 | P11 Agent Control Loop | 当前模块级完成度 |
| 10-15 | P12、P20、P21 的 Demo 讲法 | 六个真实办公场景 |
| 17 | P23-P24 路线与结论 | 可证伪挑战和目标用户研究门 |

## 竞品官方资料

1. Microsoft 365 Copilot，`Refer to specific files and more in Microsoft Copilot`：工作内容、文件、邮件、会议和站点引用。  
   https://support.microsoft.com/en-US/Microsoft-365-Copilot/refer-to-specific-files-and-more-in-microsoft-365-copilot
2. OpenAI，`Deep research in ChatGPT`：研究计划、来源范围、实时进度、可中断调整和带引用报告。  
   https://help.openai.com/en/articles/10500283-deep-research
3. OpenAI，`Introducing the Codex app`：并行 Agent、隔离工作区、长任务、审查和 Automations。  
   https://openai.com/index/introducing-the-codex-app/
4. Anthropic，`How Claude Code works`：项目上下文、工具循环、验证、会话恢复与分叉。  
   https://code.claude.com/docs/en/how-claude-code-works
5. OpenClaw，`Background tasks`：Gateway 拥有的后台 Task、任务状态与可观察性。  
   https://docs.openclaw.ai/automation/tasks
6. OpenClaw，`Multi-agent routing`：Agent、Workspace、Session 与路由隔离。  
   https://docs.openclaw.ai/multi-agent

## 文献与技术方向

1. Brown 等，`Language Models are Few-Shot Learners`：通过文本指令与少量示例规定任务，作为 Prompt Engineering 阶段的代表性研究。  
   https://arxiv.org/abs/2005.14165
2. Yao 等，`ReAct: Synergizing Reasoning and Acting in Language Models`：Reasoning、Action、Observation 的交替循环。  
   https://arxiv.org/abs/2210.03629
3. Anthropic，`Effective context engineering for AI agents`：从单个 Prompt 扩展到对系统指令、工具、外部数据和历史状态的整体管理。  
   https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
4. Model Context Protocol，`Elicitation`：结构化补充信息请求、原因说明与取消语义。  
   https://modelcontextprotocol.io/specification/draft/client/elicitation
5. A2A Protocol，`Specification`：Task 状态、消息、Artifact 与输入需求。  
   https://a2a-protocol.org/dev/specification/
6. LangGraph，`Persistence` 与 `Time travel`：Checkpoint、恢复点、状态复用和分支重跑。  
   https://docs.langchain.com/oss/javascript/langgraph/persistence  
   https://docs.langchain.com/oss/python/langgraph/use-time-travel
7. W3C，`PROV-O`：Entity、Activity、Agent、生成、使用和修订关系。  
   https://www.w3.org/TR/prov-o/

## 人机交互与用户研究依据

1. Amershi 等，`Guidelines for Human-AI Interaction`：说明能力边界、及时展示上下文、支持纠正和控制。  
   https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/
2. Rodden、Hutchinson、Fu，`Measuring the User Experience on a Large Scale: User-Centered Metrics for Web Applications`：HEART 体验度量框架。  
   https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/
3. W3C，`Understanding Success Criterion 4.1.3: Status Messages`：状态变化应可被感知而不强制打断焦点。  
   https://www.w3.org/WAI/WCAG21/Understanding/status-messages
4. W3C，`Understanding Success Criterion 2.5.5: Target Size`：交互目标尺寸与可操作性。  
   https://www.w3.org/WAI/WCAG21/Understanding/target-size

## 不能推出的结论

- 不能说主流竞品做不到 Workspace、证据门、恢复或业务 Artifact。
- 不能把固定公开数据上的系统实测写成生产 SLA、全面正确或用户价值。
- 不能把截图、自动化和现场单次反馈写成正式用户研究结果。
