# DR-0030：可处置问题审查与可恢复分析门

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`，限结构化 Finding、服务端原文定位、有界分析修复和确定性前端回归 |
| 日期 | 2026-08-26 |
| 触发来源 | [`USER-FEEDBACK-20260826-ACTIONABLE-RECOVERY`](../sources/USER-FEEDBACK-20260826-actionable-conflict-and-recovery.md) |
| 研究依据 | [`ACTIONABLE-HITL-RECOVERY-RESEARCH-20260826`](../research/ACTIONABLE-HUMAN-DECISION-AND-FAILURE-RECOVERY-20260826.md) |
| 场景 | [`SCENARIO-016`](../scenarios/SCENARIO-016-actionable-finding-and-recoverable-analysis.md) |
| Evidence | [`ACTIONABLE-REVIEW-AND-RECOVERY-20260826`](../evidence/ACTIONABLE-REVIEW-AND-RECOVERY-EVIDENCE-20260826.md) |
| 延续/替代 | 延续 `DR-0029` 的服务端 Evidence Anchor；替代“任一 Finding 无法定位即整轮失败”的交互与运行边界 |

## 问题定位

精确高亮只回答“原文在哪里”，没有回答“人现在该决定什么”。同时，`DR-0029` 的第二次
定位失败会把 Run 置为 `failed`，把已验证分支、有效 Finding 和可恢复下一步一起藏在终态
错误后面。这既增加理解成本，也让局部的模型引用问题升级成整个任务的死路。

## 决策

1. Finding 新增可选 `fact_summary`、`impact` 和 `review`。`review` 包含是否需要人工决定、
   问题、为什么必须由人决定、2-3 个 A/B/C 互斥选项、推荐项与理由、确认后的系统行为。
2. 每个选项必须提供完整 `next_instruction`、`agent_next_step`、受影响 Branch、所需来源、
   预计新增轮次和 `external_action=none`。`accept/decline/defer` 先以 expected version 和幂等键
   写入当前 Run 的 DecisionRecord；接受业务选项后才创建独立只读 Run。
3. 审查页改为“事实 -> 影响 -> 人工动作”的三步处置单；证据索引与真实安全 Preview 并排。
   每项明确显示文件、服务端位置和逐字摘录，点击后切换并高亮实际文件内容。
   Agent 推荐默认隐藏，用户先选初始口径，再主动“对照 Agent 建议”，避免解释先锚定判断。
4. Runtime 把引用范围违规继续作为安全失败；但把“合法范围内无法唯一定位”降为 Finding
   级可恢复问题。每条 quote 记录 `exact/ambiguous/unavailable`；`stale/rejected` 仅预留在协议中。
   首次失败最多一次受控 Analyst 重试；第二次保留可核对 Finding 并记录省略数。
5. 若没有任何可采用 Finding，Runtime 保留计划、文件范围、调用回执和 Branch，在预算允许时
   以 `waiting_input` 暂停。`next_step.recovery_kind` 区分 `source_location` 与
   `analysis_output`，并给出候选 Branch 和下一轮最小目标。
6. 若已无预算，使用 `stopped/bounded`，不生成伪结果，也不得继续显示会让人误以为旧 Run
   可以 `resume` 的控件。前台必须列出尚未完成的候选 Branch；用户可补充方向，并把其中一条
   变成新的 Task Contract 与独立 Run。旧 Run、调用回执、Branch 状态和 ArtifactVersion 保持
   不变。升级前遗留的 `failed` Run 同样显示已保留事实、未发生动作和“缩小范围重新核对”入口。
7. 普通 UI 不显示 raw quote、Prompt、CoT、provider response、内部路径或 validator 字符串。
8. `ambiguous` 必须给出所有服务端候选位置。用户接受一个候选后，系统先记录 DecisionRecord，
   再 steer 并只 resume 绑定的 waiting Branch；关闭处置页记录 `defer`，不能静默丢弃。

## 技术差异及其交互后果

| 技术差异 | 旧用户流程 | 新用户流程 | 前台输出 |
| --- | --- | --- | --- |
| 长段 Finding -> 结构化处置单 | 自己从一段话里找事实、风险和建议 | 按 1/2/3 扫描后再看完整说明 | 事实、影响、是否必须人决断 |
| 文件级关联 -> 证据与实际 Preview 并排 | 打开多个文件自行搜索 | 点证据即切到真实文件实际位置 | 文件名、行/表格行、逐字摘录、高亮 |
| Agent 建议 -> 互斥人工选项 | 不知道该怎么回应 Agent | 先选初判，再展开建议；接受、否决或暂缓都有回执 | A/B/C、影响预演、反馈框、DecisionRecord |
| 局部定位失败 -> Finding 级有界修复 | 任一坏引用令整个 Run 失败 | 自动修复一次，保留可核对部分 | 未采用、受控重试、省略数 |
| terminal failed -> EvidenceResolution + Branch 级恢复 | 只能猜测是否重跑全部 | 比较真实候选位置，或选择最小 Branch 补证 | exact/ambiguous/unavailable、已保留/未采用/未发生 |
| 无预算 -> 终态分支续办 | 页面说“继续”但终态不能恢复，只能重新输入任务 | 看见边界、保留项和未完成 Branch；补充方向后以一条 Branch 创建新 Run | `stopped/bounded`、候选 Branch、ArtifactVersion、新 Task Contract、无外部动作 |

## 前后台统一事实

| UI 状态/动作 | 服务端事实 | 用户能做什么 | 不得声称 |
| --- | --- | --- | --- |
| 三步处置单 | Finding `fact_summary/impact/review.requires_human_decision` | 快速判断是否需要参与 | 语义正确、风险已验证 |
| 证据来自文件 | `evidence_anchors[]` + Preview GET | 点击证据并核对实际高亮 | 模型自报位置、客户端猜测位置 |
| 处理选项 | Finding `review.options[]` + Branch/source/round/action impacts | 选择口径、补充反馈 | Agent 已执行该选项 |
| 接受/否决/暂缓 | `decision_records[]`、`decision_recorded`、version/idempotency | 留下可重连回执；关闭即暂缓 | 审批正确、外部动作发生 |
| 接受业务选项 | DecisionRecord 成功后新 Run POST 与新 idempotency key | 启动独立只读任务 | 修改旧 Run、编辑原文件、外部动作 |
| 定位恢复 | `EvidenceResolution`、`evidence_disambiguation_required`、waiting Branch | 比较候选；确认后 steer/resume 一条 Branch | 候选结论已成立、其他分支重跑 |
| 结构恢复 | `recovery_kind=analysis_output`、两条 rejected event | 选择最小 Branch 重试 | 模型没有调用、失败内容已采用 |
| 部分采用 | `analysis_partial_adopted` + result/artifact findings | 查看保留结果和省略数 | 被省略 Finding 的内容或正确性 |
| 预算终态续办 | `status=stopped`、`brief.outcome=bounded`、`next_step.candidate_branch_ids/recovery_kind`、旧 ArtifactVersion | 补充方向，以一条未完成 Branch 创建新 Task Contract | 对 terminal Run 调用 resume、覆盖旧 Run、保证复用旧文件范围 |
| 历史失败恢复 | `status=failed`、validation error、原 instruction/branch/call facts | 创建缩小范围的新 Run | 旧调用被续跑或错误结果被提交 |

## 验证与边界

- 单测覆盖合法 Anchor、部分采用、连续两次定位失败、首次结构失败后修复、连续两次结构失败后
  暂停，以及既有安全范围违规 fail closed。
- Playwright 覆盖三步处置单、真实文件高亮、A/B/C、accept/defer 回执、反馈生成新 Run、
  候选消歧、只恢复目标 Branch、断线后恢复待决状态、历史失败恢复，以及预算终态按 Branch
  创建新 Run 且不发送旧 Run control。
- 一次真实 `deepseek-v4-pro` Run 在第一轮进入人工 Branch 选择，第二轮首次定位部分拒绝、
  自动重试后采用，最终按预算有界停止。它不证明 Finding 正确或推荐合理。
- 当前已有 `accept/decline/defer` 的版本化幂等回执，但没有文件修改建议 Diff、可写 Artifact、
  Tool Gateway 或外部动作；DecisionRecord 不是审批通过证明。
- 自动化和截图不是用户研究；“更清晰、更可控”继续是待验证假设。
