Demo 2 仍然保留 07-16 的智能工作驾驶舱作为目标产品面，但这一页不再只讲目标框图，而是先回答一个可以直接演示的输入、过程和输出。

输入是一条复杂但只读的办公任务：分别核对产品上线、搜索 Agent 运行和用户交互三条工作线的风险与证据，先独立核对，再形成统一简报。用户不需要指定五个 Agent，也不需要自己分配会话。

过程由服务端事实决定。Topology Admission 编译出五个 WorkUnit，其中三个是根工作包，两个依赖前序结果。第一波返回后，三个 Contribution 分别进入采用门；只有带批准来源和可定位证据的候选才能进入 Artifact。两个依赖工作包显示“下一波待确认”，由用户明确启动，而不是后台无声扩张预算。

输出是一个统一工作面：左侧阶段轨回答现在走到哪，中央 DAG 回答谁依赖谁，右侧当前影响只突出唯一主要动作，底部结果条说明三份贡献已经采用、Artifact v1 已保留、还有两个工作包待确认。用户管理的是统一成果和下一步，不是多个 Agent 对话。

边界必须讲清：这是单 API 进程、顺序波次、每波最多三个只读 Worker 的 controlled fixture。它不是 durable queue、远端 Worker、分布式 Swarm，也不是已经完成的智能工作驾驶舱；自动化和截图同样不能证明多 Worker 更快、更准或更易理解。

转场：无论任务由单 Agent、Workflow 还是 Swarm 完成，只要下一步涉及真实发送、付款或生产变更，都要进入 Demo 3 的动作风险门。

证据/边界：https://docs.openclaw.ai/concepts/multi-agent ；https://a2a-protocol.org/v0.3.0/specification/ ；https://www.nngroup.com/articles/progressive-disclosure/

预期问题：多 Agent 一定比单 Agent 好吗？不一定，当前也没有效果证据；只有同任务、同模型、同来源和同预算下的增量收益高于协调与验证开销时，才应该启动 Adaptive 路线。