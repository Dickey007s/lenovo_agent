Demo 3 保留 07-16 的 Risk Gate。Risk Lens 从动作影响、数据敏感度、可逆性、权限和缺失信息评估风险，再映射到 L0-L5：L0 自动执行，L1 执行并通知，L2 只生成草稿，L3 普通确认，L4 强确认，L5 直接拒绝。

真正关键的是动作链。Agent 先提出方案，前台展示动作对象、影响范围和可逆性；Evidence Gate 与 Risk Lens 给出来源和风险理由；需要人工确认时，用户明确同意后才生成 Permit；执行后必须返回可核验的 ExecutionReceipt，或者明确写出动作未发生。这样“方案”“草稿”“批准”和“执行”不会被混成一个绿色完成状态。

页面下半部分使用当前真实界面截图，说明目前已经实现的有限一段：实际 Artifact、具名 Validator、EffectReceipt 和未发生边界可以分层展示。但生产 Connector、身份授权、Permit 防重放与真实外部动作仍未实现，所以系统不会发送邮件、付款、写 CRM 或执行生产命令。

前台的直接变化是按钮不能只写“确认”。用户必须先看见对象、影响、证据、风险级别、可逆性和执行回执，才能知道自己的点击究竟会改变什么。

转场：三个 Demo 的方向保留，但下一步必须继续用可证伪证据而不是更多概念升级结论。

证据/边界：https://openai.github.io/openai-agents-python/human_in_the_loop/ ；https://modelcontextprotocol.io/specification/draft/client/elicitation ；https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/

预期问题：当前是不是已经具备 L0-L5 的生产执行能力？没有，L0-L5 是目标控制模型，当前只有固定成果和未执行边界的有限实现。