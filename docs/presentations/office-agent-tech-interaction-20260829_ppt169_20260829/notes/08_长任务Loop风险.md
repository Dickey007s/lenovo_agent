方向漂移、上下文退化、错误复利、成本扩张、权限漂移和停止困难，是 07-16 已经提出的六类风险。它们对应六个前台问题：目标是否仍一致、用了哪版来源、预算还剩多少、允许什么动作、哪条分支受影响、如何暂停恢复或接管。这里不能夸大当前实现：系统默认 12 轮、公开上限 24 轮，并受文件数、模型调用次数和主动运行时间的独立预算约束；暂停和停止只在模型调用之间的安全点生效，也不会硬取消正在进行的请求。它解决了一部分状态透明与局部恢复问题，还不是无限自治的长任务执行器。

转场：下一页把 Observe、Plan、Act、Verify、Commit 和外围控制放在一起看。

证据/边界：https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents ；https://docs.langchain.com/oss/javascript/langgraph/persistence ；https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/

预期问题：12 轮是否足够？默认值不是质量承诺；是否足够仍要由完成条件、其他预算和场景实测共同判断。
