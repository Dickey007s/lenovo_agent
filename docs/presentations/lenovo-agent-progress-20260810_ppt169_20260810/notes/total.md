# 01_cover

这次汇报只回答一个问题：七一六 v2 之后，我们把架构共识推进到了什么可验证程度。答案是，四个已经合并的 Pull Request，把治理要求、服务端任务事实、固定场景执行和真实浏览器界面连成了一条可审查证据链。这里的关键词是可审查，而不是生产级完成；真实持久恢复、连接器和用户价值仍然需要后续证据。

---

# 02_four_prs

先给结论，四个 Pull Request 已经形成了一个受治理的 Demo 1 纵切。第一个固定场景、来源和协议，第二个建立 TaskStore、接口、事件流和真实 Task Bar，第三个加入固定循环、局部冲突、控制与提交，第四个把同一份服务端 Snapshot 投影到交付物工作区并完成浏览器验证。这个链条证明工程路径已经串通，但不能被扩展成通用后台长任务或生产验收结论。

---

# 03_hard_gates

为了避免后端先行、前台补图和来源失联，我们把七一六 v2 的反馈写成了三项完成门槛。每个推进都必须说明用户看见什么、这个状态由哪个服务端事实产生，以及设计判断来自哪一条可追溯来源。Prompt、思维链、Worker 内部对话、密钥和底层堆栈默认隐藏，因为它们不会帮助用户做决定。缺少任何一项，内容都不能进入完成结论。

---

# 04_protocol_sources

在写 Runtime 代码之前，我们先把来源按证明力分级。用户反馈和会议材料证明需求与演示输入，ReAct、LangGraph 和 NIST 支持设计原则，只有提交、源码、测试、截图和端到端运行才能证明本地实现。与此同时，我们固定了 Task、Branch、ArtifactVersion、VerificationReport、ConflictRecord、ControlEvent、TaskEvent 和 TaskCommit 等核心实体。PR 四的三十七个 Python 测试只证明协议、类型和治理入口，并不证明 Store、事件流或前台已经运行。

---

# 05_server_truth

有了协议以后，PR 五解决的是 Task Bar 的真值来源。前台读取 Task ID、目标、阶段、预算和版本，接口提供创建、列表、详情与按 after 游标读取的 Task SSE，Store 则保存 Snapshot、事件和工件版本，并执行 Owner 隔离与创建幂等。针对性七个测试和全量四十四个 Python 测试验证了内存路径。PostgreSQL 目前只有保存代码路径，没有本机实跑、进程重启、多实例通知或浏览器端到端证据。

---

# 06_controlled_loop

在服务端 Task 真值之上，PR 六加入固定客户 A 的受控状态转换。Start 在一次原子 mutation 中物化 Observe、Plan、Act 和 Verify，正式口径二千四百万元与预测口径二千六百八十万元只阻塞经营分析分支，其他分支仍可形成已验证工件。只有最后一个冲突解决、经营分析重新验证、客户回复更新到第三版以后，服务端才生成 TaskCommit 和 state hash。针对性十五个与全量五十六个 Python 测试支持这条固定路径，但它不是后台持续调度，Steer 也只能表述为已经记录、等待后续循环应用。

---

# 07_artifact_workspace

接下来把视线转到用户真正看到的界面。右侧 Task Runtime 与左侧 Artifact Workspace 共享同一份 Snapshot，分支 head、版本、结构化内容、验证、冲突、lineage 和 Commit 都来自服务端，前端不会补造工件或完成状态。固定三类工件使用 allowlist，未知字段和不安全的 source reference 默认隐藏，但这只是前端第二道投影，不是服务端通用脱敏保证。System Edge 的两条端到端用例覆盖了主路径和发送前失败恢复，主路径终态是一项任务、三个已提交分支和七个唯一工件版本。

---

# 08_ui_fact_mapping

这张图是以后每次前端设计都要回看的事实映射。Task Bar 对应 TaskSnapshot，分支与冲突对应 branches、conflicts 和事件，工件区对应 artifact versions、verification reports 与 last commit，控制动作必须等待服务端 mutation 返回新的 Snapshot。Action Gate 仍然读取独立的 RunSnapshot，所以 Task Runtime 与副作用动作目前还是两条事实链。SSE 只负责发现变化，随后必须重新读取 Snapshot 对账；连接颜色、动画和 Toast 都不是业务真值。

---

# 09_evidence_scoreboard

为了让进度可复核，我们把证据按类型分别计数。四表示四个已合并 Pull Request，五十六表示 PR 六时点的全量 Python 回归，二表示 PR 七的 system Edge 浏览器端到端用例，五表示带实测尺寸和 SHA 二百五十六摘要的截图。底部两张图只证明浏览器在请求发送前中止后，能够保留原 key、刷新页面并用同 key 对账，最终没有生成重复工件。它不证明服务端已经提交、但响应在返回途中丢失的恢复路径。

---

# 10_claim_boundary

到这里必须把已证明和未证明清楚分开。我们已经证明协议与来源留痕、内存 Store 的固定状态转换、局部冲突、工件 lineage、验证、Commit 和指定浏览器路径。我们还没有证明 PostgreSQL 与 API 重启、多实例一致性、SSE 断线与序号缺口、提交后响应丢失、真实模型与连接器、通用脱敏、工件到动作失效绑定和人工编辑新版本。关于 Task Bar 是否降低理解成本、分支隔离是否带来业务收益，以及控制动作是否符合用户心智，仍然只是待用户研究的假设。

---

# 11_next_roadmap

因此下一轮不扩概念面，而是按四个连续 Pull Request 补齐会改变完成结论的证据。第一步实跑 PostgreSQL 并做 API 重启对账，第二步覆盖提交后响应丢失与 Task SSE 断线恢复，第三步建立工件与 Action 的版本绑定并验证旧审批和 Permit 失效，第四步围绕四项用户假设开展目标任务测试。每一步都要再次通过场景与来源、服务端事实、前台输出、运行证据和限制这五个门槛。完成这些基础证据之后，真实 Connector 与 Adaptive Swarm 仍需分别进入实现与验证，只有新增对应运行证据后才能写入“已实现”结论。
