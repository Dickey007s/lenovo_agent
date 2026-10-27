# DR-0088：按证据与权限展示人机分工

日期：2026-10-24。状态：Limited Verified，限记录中的本地回归和真实模型案例。
实现：未提交工作树，HEAD 基线 fa974ae；无新 PR。
来源：[用户反馈](../sources/USER-FEEDBACK-20261024-human-agent-division.md)。
场景：[SCENARIO-075](../scenarios/SCENARIO-075-distinguish-system-work-human-judgment-and-repair.md)。
验证：[Evidence](../evidence/DR-0088-TASK-RESPONSIBILITY-20261024.md)。

## 决策

在统一工作台的原首轮安排区加入“这次怎么分工”，不建立独立演示产品。沿用原 Task、Run、DecisionRequest、Branch、ArtifactVersion 和审核页。
“高置信”不实现为模型自报百分比：来源定位通过只证明位置，并不证明结论正确。分工投影不授予任何新执行权限。

1. 系统已处理：来自当前 Result 或同 Run 保留 ArtifactVersion 的发现；绑定工作项均完成、有非 context 的定位依据、不含待决、也没有未通过的业务 Gate。展示实际结果和原文入口。
2. 需要人判断：结构化 finding.review 与待决记录，保留问题、why_human 和原审核页互斥选项。分析 Branch 完成不能消除业务待决；已记录的决定不算纯自动处理。
3. 需要补事实：已公开的 uncovered_requirements 单列，不能用一个猜测选项代替真实材料。各轮缺源按标题合并保留，不因下一轮空列表而消失。
4. 来源多位置：依据既有 DecisionRequest/Resolution，说明是在选择引用位置，不是业务批准。缺少候选时保持不可假定已解决。
5. Agent 未完成：来源定位/结构输出恢复、普通未完成项、依赖分歧和协作用量授权分别说明。只有既有恢复控制才可继续，不自动重试或伪造人决策。

背景引用不进入“系统已处理”；仍保留在完整依据和成果。旧记录没有 Branch/Anchor 时不显示自动成功。业务 Gate 未通过优先显示警告。

## 真实试验推动的更正

第一轮财务案例中 Planner 把往来账当作查找银行回单的候选，Analyst 给出只有 context 引用的缺源说明。此前投影仅凭有 Anchor 就把它算入“系统已处理”，属于误导。
本次改为绑定 Branch 完成且有直接定位依据才进入该栏，不能从中文标题猜测分类。同时加强 Planner 提示：相同主体或相关主题不等于所需凭证；索引没有对应凭证时记 uncovered，而非读取旁证冒充完成。
提示改进不是语义来源匹配的确定性校验；一次复测成功不保证任意任务不会再次误选。

## 交互

- 原有三个常见案例保留。新增三个分工案例放在“更多人机分工示例”内，不同时堆六张卡。
- 当前页展示两栏，普通系统结果默认两项、其余展开；人工事项不折叠隐藏。Agent 未完成说明在等待时展开。
- 最近任务列表区分待你判断、待核对依据、待补资料和业务条件未通过。服务端 completed 只表示本次 Loop 完成，不能掩盖这些条件。
- 打开案例、查看依据或打开决定页不提交 POST、不调用模型。确认继续仍沿用版本化 decision + 当前终态同 Task /continue；历史只读、选项不预选。
- Demo2 automatic_readonly 继续原自动策略，本次未添加人工派发确认；Demo3 固定事项规则和 action-controls 不变。

## 服务端映射

| 展示 | 权威事实 | 不允许推断 |
| --- | --- | --- |
| 系统处理的分析 | Result/ArtifactVersion.findings，affected_branch_ids，Branch.status，evidence_anchors | calibrated confidence、真实开通或业务获批 |
| 人的业务取舍 | review.requires_human_decision/question/why_human、DecisionRequest/Record | 暂停即人工裁决、默认推荐等于人选择 |
| 需要补事实 | rounds[].plan.uncovered_requirements 的既有公共投影 | 已上传、已找到银行回单、外部系统已搜索 |
| 技术恢复 | next_step.recovery_kind/candidate_branch_ids | 需要人猜答案、修改原件 |
| 协作授权 | ready_branch_ids、execution_policy、waiting_input | 可信度低、已经派发 |
| 保留与交接 | ArtifactVersion、task_id、parent_run_id、/continue | 新独立任务或已完成外部动作 |

## 验证与限制

真实八次有界运行共十六次模型调用，包括三组首测、三组复测、一次明确的人类选择后续办及一条保留供演示的待决任务。完整编号、错误、截图、回归命令见 Evidence。
没有校准置信度阈值、通用语义验证、用户理解研究、资料上传闭环或外部业务动作。本条不声称所有低置信任务都能自动准确分类；当前没有结构化事实时只展示未完成，不猜测业务裁决。
