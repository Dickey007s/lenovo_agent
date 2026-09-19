# 01_任务进展

这一轮不是另起一套演示系统，而是保留原来的办公资料库和 Agent 能力页，继续优化同一个任务的界面。第一张是原系统的任务进展页。我们把信息顺序调整成用户先看到现在需要处理什么，再看到已经完成什么、保留了什么成果。完整执行记录按需查看，不要求用户先理解内部术语才能继续工作。Agent Control Loop 和 Adaptive Swarm 都仍然保留，并且使用同一套 Task、Run 和 Snapshot 状态。

截图说明：2026-09-11 原 React 页面受控测试截图，输入是公开 Snapshot 测试数据，不代表一次真实模型调用的成功证明。截图未用 imagegen 重绘或修改。原始文件：docs/reports/demo12-polish-20260911/screenshots/progress-1672.png。

# 02_证据核对

这张展示 Agent Control Loop 中需要人工选择证据位置时的界面。系统先说明为什么需要人参与，以及选择会影响哪一部分。右边展示实际候选原文，而不是让用户猜行号，也不替用户默认选择。选定依据只是解决引用位置，不等于批准业务结论，更不会授予外发权限。恢复时沿用已有成果，只处理相关分支；如果旧 Run 已经结束，需要按合同创建同一任务的子 Run，不能假装旧 Run 又恢复执行。

截图说明：2026-09-11 原系统受控测试，原始文件：docs/reports/demo12-polish-20260911/screenshots/evidence-1672.png。证据选择、决定回执、创建后续 Run 和实际执行是不同事实，不应合并成一个“确认即完成”。

# 03_蜂群协作

我们这里的蜂群，当前准确地说是受限的主控与只读 Worker 协作。服务端先判断工作包是否可以拆分、依赖关系是否满足，再由用户显式确认派发；每批最多三个进程内 Worker。截图中的三条调用和两条采用是分开记录的：返回了内容，不代表已经进入成果。要经过来源、证据位置和适用校验，才能采用。一个工作包有问题时，只阻塞它和真实下游，其他成果保留。我们希望突出的是来源约束、贡献核验和局部恢复与长期任务历史的整合。目前只能称工程差异候选，没有同配置实测，不能宣称算法创新或比单 Agent 更好、更便宜。

截图说明：2026-09-12 原系统受控测试，原始文件：docs/evidence/screenshots/dr-0063-fixture-swarm-1440.png；图中的调用与采用是 fixture 回执投影，不是真实 Provider 本轮运行。当前不是分布式 Worker Runtime，没有开放式子委派，也没有任意外部动作执行。

# 04_Agent论文调研

调研已经从泛化的交互和信任研究，转向 LLM Agent 自身的机制。我们整理了十六篇相关论文，并按四条线选读。第一，HiL-Bench 和 SAGE-Agent 研究什么时候应该求助，以及如何针对真正缺失的信息提问。第二，SWEET-RL 和 Collaborative Gym 关注人的反馈是否真正进入后续推理、工作状态和成果修正。第三，AgentSpec 与 AgentDojo 提醒我们，执行权限必须由 Runtime 强制约束，资料中的指令不构成授权。第四，Intelligent AI Delegation 与 MAST 用来检查多 Agent 委派、交接、验证和错误传播。由此，Demo3 不只是 Demo1 的暂停按钮，而是回答为什么停、问谁、问什么、回答能改变什么，以及什么情况下仍然不能执行。

阅读边界：十六篇按论文身份去重，包含既有资料重分类，不是十六篇全文精读，也不是算法复现。各篇阅读深度见项目研究文档。以下列出重点八篇的一手链接，机制到本项目的映射是我们的设计推论。

- HiL-Bench (Human-in-Loop Benchmark): Do Agents Know When to Ask for Help? https://arxiv.org/abs/2604.09408v4
- Structured Uncertainty guided Clarification for LLM Agents (SAGE-Agent): https://aclanthology.org/2026.findings-acl.2028/
- SWEET-RL: Training Multi-Turn LLM Agents on Collaborative Reasoning Tasks: https://arxiv.org/abs/2503.15478v1
- Collaborative Gym: A Framework for Enabling and Evaluating Human-Agent Collaboration: https://arxiv.org/abs/2412.15701v6
- AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents: https://arxiv.org/abs/2503.18666v3
- AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents: https://arxiv.org/abs/2406.13352v3
- Intelligent AI Delegation: https://arxiv.org/abs/2602.11865v1
- Why Do Multi-Agent LLM Systems Fail? (MAST): https://arxiv.org/abs/2503.13657v3

另八篇相关文献：

- Active Task Disambiguation with LLMs: https://arxiv.org/abs/2502.04485
- Robots That Ask For Help: Uncertainty Alignment for Large Language Model Planners (KnowNo): https://arxiv.org/abs/2307.01928v2
- When Search Agents Should Ask: DiscoBench for Clarification-Aware Deep Search: https://arxiv.org/abs/2606.27669v2
- Aligning LLM Agents by Learning Latent Preference from User Edits (PRELUDE / CIPHER): https://proceedings.neurips.cc/paper_files/paper/2024/file/f75744612447126da06767daecce1a84-Paper-Conference.pdf
- Tau2-Bench: Evaluating Conversational Agents in a Dual-Control Environment: https://arxiv.org/abs/2506.07982v1
- Magentic-UI: Towards Human-in-the-loop Agentic Systems: https://arxiv.org/abs/2507.22358v1
- HAS-Bench: Evaluating LLM-Based Human-Agent Systems under Configurable Human Participation: https://arxiv.org/abs/2607.04329v1
- LLM-Based Human-Agent Collaboration and Interaction Systems: A Survey: https://aclanthology.org/2026.findings-acl.1811/

研究台账：docs/research/DEMO3-AI-AGENT-BOUNDARY-LITERATURE-20260912.md，核验日期 2026-09-12。不转述论文性能百分比；尚未接入 SAGE-Agent、SWEET-RL 训练或 AgentSpec DSL。

# 05_边界案例

我们把研究映射到八个办公案例，这里展示四个。财务摘要只是定位失败时，应由 Agent 在合法范围内重试，不让用户替它修文件。同一句话出现在两个真实位置时，才请人选择引用位置。UX 频率恰好落在百分之三边界时，计算结果可以保留，但规则冲突需要业务负责人确定口径。报告发送客户则是另一类边界：即使内容已经核对，没有外部执行权限也不能发送。这里不把所有情况压成固定 L0 到 L5，而是分别检查后果、证据、权限、版本和执行回执。尤其要区分报告文件检查通过、业务可以上线或签署，以及真实动作已经发生。

实现边界：表格前两行已有恢复或决定合同；UX 规则批准待实现；当前系统不支持真实对外发送。多维判断是产品设计初稿，未实现自动风险评级，也未经用户研究证明优于等级制。

案例出处：docs/research/DEMO3-BOUNDARY-RULES-AND-CASES-20260912.md。相关机制参考 SAGE-Agent（针对性消歧）、AgentSpec（执行前约束）、AgentDojo（材料信任）和 Intelligent AI Delegation（权限与验证）。这些论文并未验证本项目的具体业务规则。

# 06_整合方向

最后，Demo3 的方向是进入同一套办公任务，而不是新增一个让用户找不到入口的演示站。Control Loop 负责连续执行，Swarm 负责受限分工，共驾边界决定什么时候要请人补充信息、选择口径或交回决策权。当前已经把边界说明和调用、采用回执放回原页面；接下来还要补齐长文本覆盖、业务口径澄清，以及人的反馈怎样触发局部成果更新。测试也不能只看按钮能不能点击，还要测该问的是否漏问、不该问的是否打扰、反馈是否真正被使用，以及越权动作是否被拦截。自动测试之后还需要真实办公用户的理解测试。

状态说明：这是整合方向示意，不是已经实现的完整架构或全场景闭环。长文本输入覆盖问题仍开放；业务审批、任意外部动作和通用策略引擎尚未实现。本次 PPT 制作未更改产品源码，也未重跑模型、PostgreSQL 或目标用户实验。

图片来源：使用用户指定的 imagegen 生成概念配图，白底蓝绿科研风格；原系统截图均保持原样。提示词和图片记录位于 images/image_prompts.md 与 images/image_prompts.json。
