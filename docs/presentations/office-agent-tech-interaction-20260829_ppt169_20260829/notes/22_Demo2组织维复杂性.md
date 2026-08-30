Demo 2 保留 07-16 的智能工作驾驶舱。驾驶舱先聚合邮件、CRM、项目、报销和日历中的工作信号，生成今日重点，解释截止时间、客户等级和业务影响，并允许用户调整本次优先级。

随后每项待办走成本合适的路径。简单查证用 Tool Call，独立草稿用 Single Agent，稳定重复任务用 Fixed Workflow，只有高价值、跨来源、可并行且预算可承受的任务才进入 Adaptive Swarm。Swarm Admission 通过后，Supervisor 根据覆盖度和依赖生成 Worker；Worker 围绕 Shared Artifact 协作；Verifier 检查事实和成果，Conflict Resolver 只在冲突时介入；最终统一结果、待确认项和 Trace 回到同一个驾驶舱。

这一设计的交互价值不是“屏幕上出现更多 Agent”，而是用户只管理优先级、路由理由和统一成果，不需要在多个会话之间搬运上下文。系统还要解释为什么选择某条执行路径、Swarm 增加的质量或速度收益是否值得协调成本。

当前产品没有通用多 Worker Runtime，也没有完整 Swarm Admission、Supervisor 和 Resolver。现状是单 Controller、服务端 Branch 与固定成果适配器。这一页明确保留 07-16 的目标产品形态，作为后续架构与用户研究方向，不写成现行能力。

转场：无论任务由单 Agent、Workflow 还是 Swarm 完成，只要下一步涉及真实发送、付款或生产变更，都要进入 Demo 3 的动作风险门。

证据/边界：https://docs.openclaw.ai/multi-agent ；https://a2a-protocol.org/dev/specification/ ；https://modelcontextprotocol.io/specification/draft/client/elicitation

预期问题：多 Agent 一定比单 Agent 好吗？不一定，只有增量收益高于协调、验证和成本开销时才应该启动。