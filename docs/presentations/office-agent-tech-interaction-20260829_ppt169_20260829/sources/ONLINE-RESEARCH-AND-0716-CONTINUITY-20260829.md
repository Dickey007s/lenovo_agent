# 线上研究来源与 07-16 内容继承表

## 使用规则

- 本表中的线上链接已于 2026-09-02 复核；页面版本变化后仍需在下一次汇报前重新检查。
- 07-16《未来办公 Agent：Loop、Swarm 与受治理执行》是本次 PPT 的内容骨架，不作为外部研究来源。
- README、Decision、Scenario、Evidence 和内部详细报告只用于核对当前系统事实，不在页面上冒充研究、竞品调研、文献或用户研究来源。
- 竞品判断只依据线上官方材料；“官方材料未强调某能力”不能推出竞品做不到。
- 当前系统页面截图只证明固定公开场景的受控运行；第 22 页是受控演示样例，不是生产调度或分布式运行证据。截图与自动化都不作为正式目标用户研究。
- LangGraph 与 MCP 页面可能随文档版本变化；A2A 固定引用 `v0.3.0`。三者本次访问日期均为 2026-09-02。

## 07-16 内容继承

| 本次页码 | 继承的 07-16 内容 | 本次只补充什么 |
| --- | --- | --- |
| 01 | P01 从跨端聊天到可治理工作系统 | 当前 Workspace 实景 |
| 02 | P02 能力跃迁与三个 Demo 分工 | 当前真实纵切和缺口 |
| 03 | P03 一个底座、两层增强、三类控制 | 当前实现/目标边界 |
| 04 | P04 八个最小运行时组件 | 统一模块名和前台投影 |
| 05 | P05-P09 Prompt、Loop、Context、Harness、Loop Engineering | 线上论文与官方来源 |
| 08 | P10 长任务方向漂移风险 | 当前默认 12 轮、公开上限 24 轮；另受文件、模型调用与主动运行时间预算约束 |
| 09 | P11 Agent Control Loop | 当前模块级完成度 |
| 10-15 | P12、P20、P21 的 Demo 讲法 | 六个真实办公场景 |
| 17-20 | 07-16 的“持续、协作、治理、交付”主张 | 当前系统真实界面的完整操作纵切 |
| 21 | P12 Demo 1：受控持久任务 | 当前 Branch、Evidence Gate、ArtifactVersion 与恢复的真实映射；跨端和长期 Worker 仍为目标 |
| 22 | P20 Demo 2：智能工作驾驶舱 | 驾驶舱仍是目标产品面；受控样例展示 5 个工作包的依赖关系、首批 3 份贡献采用、成果版本 1 与下一批人工确认，并明确单服务进程、顺序批次和只读边界 |
| 23 | P21 Demo 3：真实动作前的 Risk Gate | 保留 L0-L5 与 Permit 目标；补当前 Artifact、EffectReceipt 和“未发生”界面实测 |
| 24 | P23-P24 路线与结论 | 可证伪挑战和目标用户研究门 |

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
   https://docs.openclaw.ai/concepts/multi-agent
7. Anthropic，`Create custom subagents`：独立上下文、受限工具、前台/后台执行和恢复机制。
   https://code.claude.com/docs/en/sub-agents

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
   https://a2a-protocol.org/v0.3.0/specification/
6. OpenAI Agents SDK，`Human-in-the-loop`：在敏感工具调用前暂停，保存状态，并在批准、拒绝或修改后恢复。
   https://openai.github.io/openai-agents-python/human_in_the_loop/
7. LangGraph，`Persistence` 与 `Time travel`：Checkpoint、恢复点、状态复用和分支重跑。
   https://docs.langchain.com/oss/javascript/langgraph/persistence  
   https://docs.langchain.com/oss/python/langgraph/use-time-travel
8. W3C，`PROV-O`：Entity、Activity、Agent、生成、使用和修订关系。
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
5. Nielsen Norman Group，`Progressive Disclosure`：首层保留核心任务，把低频复杂信息延后；同时提醒连续嵌套过深会增加迷失风险。
   https://www.nngroup.com/articles/progressive-disclosure/
6. Horvitz，`Principles of Mixed-Initiative User Interfaces`：在不确定条件下比较直接行动、询问用户与保持不打扰，为“只有服务端形成待决请求时才突出人工操作”提供设计依据。
   https://www.microsoft.com/en-us/research/wp-content/uploads/2016/11/chi99horvitz.pdf
7. W3C WAI-ARIA APG，`Tabs Pattern` 与 `Disclosure Pattern`：约束任务进展/协作方式切换和按需展开的键盘与可访问性行为。
   https://www.w3.org/WAI/ARIA/apg/patterns/tabs/
   https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/

## 不能推出的结论

- 不能说主流竞品做不到 Workspace、证据门、恢复或业务 Artifact。
- 不能把固定公开数据上的系统实测写成生产 SLA、全面正确或用户价值。
- 不能把截图、自动化和现场单次反馈写成正式用户研究结果。
