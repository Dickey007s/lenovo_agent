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