Demo 1 来自 07-16 的时间维连续性。目标不是让 Agent 永远运行，而是让同一个 Task ID 在多轮任务中有稳定的任务契约、状态版本、分支和恢复点。流程仍然是 Task Contract、Observe、Plan、Act、Verify、Commit。

07-16 的关键镜头是 Verify 同时发现正式口径 2,400 万和预测口径 2,680 万。正确处理不是整项任务失败，也不是让模型自行选择，而是 Evidence Gate 只让 revenue-baseline 分支进入 waiting_input；customer-facts 和 project-risk 分支继续产出并保留。用户给出 Steer，采用正式口径并保留预测差异说明，系统只恢复受影响分支，最后把版本、来源、验证结果和 Trace 一起 Commit。

当前系统已经具备服务端 Branch、分支级 Evidence Gate、append-only ArtifactVersion、TaskCommit、局部恢复和可选 PostgreSQL 重启恢复。还没有生产级跨端身份、任意办公工件写入和长期后台 Worker。因此这一页不是把 07-16 演示冒充当前实测，而是说明我们已经完成了其中最关键的一段状态与证据纵切。

前台变化是用户不必重开对话、重讲背景；他在同一任务里看见哪个分支完成、哪个分支为何停、选择后恢复什么、旧成果是否保留。

转场：时间连续性解决以后，Demo 2 处理的是同时有很多待办和复杂分工时，工作如何被组织。

证据/边界：https://docs.langchain.com/oss/javascript/langgraph/persistence ；https://openai.github.io/openai-agents-python/human_in_the_loop/

预期问题：现在已经支持手机和电脑控制同一生产任务吗？没有，当前证明的是服务端状态、分支与恢复机制，生产身份和跨端控制仍是目标。