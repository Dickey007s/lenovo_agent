# SCENARIO-017：人阅读期间不烧预算，并只恢复 Agent 未完成的分支

## 用户、触发与痛点

一名发布负责人要求 Agent 在整个办公资料库中核对产品需求、功能测试和上线清单。Planner
拆出多个 Branch，Analyst 已读取候选文件，但返回结构未通过校验或逐字引用无法唯一定位。
用户需要时间打开文件、核对上下文，再决定是否继续。旧实现会在用户阅读时消耗 deadline，
并用“缺少证据”要求用户猜源文件哪里有错。

## 主路径

1. Run 以默认 `1200 秒` active deadline 启动，服务端继续约束最多三轮、模型调用数和每轮
   1 到 8 份文件。
2. Agent 执行 Observe、Plan 和只读分析。每次 active 阶段写入有序 Trace 和调用回执。
3. 某个 Branch 因 `analysis_output`、`source_location` 或 `evidence_missing` 进入
   `waiting_input`。Runtime 冻结 active elapsed；其他 Branch、Finding、ArtifactVersion 不回退。
4. 用户打开问题处置单。页面先显示“问题在 Agent 的交付，不在源文件”，并列出原目标、
   Agent 尝试的文件数量、模型是否调用/结果是否采用、保留项和无外部动作边界。
5. 用户可以打开候选文件查看完整安全 Preview。没有 Evidence Anchor 时不出现行高亮，页面
   明确不要求用户猜位置或修改源文件。
6. 用户可以不填任何线索，直接点“让 Agent 只重试此分支”；也可以补充版本号、日期或字段
   线索。后者先记录 steer，再 resume 绑定 Branch。
7. Runtime 从已消耗的 active elapsed 继续计时。人工等待时长不计入；后续轮次只处理被选择
   Branch 的 missing refs，其他 Branch 保持原状态。

## 终态路径

若旧 Run 已因调用、时间或轮次预算进入 `stopped/bounded`，页面显示精确 stop reason、旧 Run
已结束和已经保留的事实。用户不能向旧 Run 发送 resume，而是选择一条 Branch 创建新的独立
只读 Run。新 Run 重新冻结整个资料库索引并自主检索，不声称恢复旧模型调用。

## 完成条件

- 默认 active deadline 为 1200 秒，上限为 3000 秒；人工等待和暂停不增长 elapsed。
- waiting Gap 页面首屏能回答“发生了什么、只影响哪里、保留了什么、现在能做什么”。
- 用户不提供领域答案也能只重试目标 Branch；补充反馈为可选。
- terminal Gap 只能创建新 Run，不能向终态发送 resume。
- 无 Anchor 时不伪造行号、高亮或源文件修改建议。
- 既有 ArtifactVersion、其他 Branch 和 `external_action=none` 明确可见且不被覆盖。

## 异常路径

| 异常 | 前后台行为 | 用户恢复 |
| --- | --- | --- |
| 模型结构未采用 | `recovery_kind=analysis_output`，保留调用回执与候选文件 | 留空或补充线索，只重试该 Branch |
| 原文不能唯一定位 | `recovery_kind=source_location`，无 Anchor 不高亮 | Agent 重新寻找更长且唯一的逐字引用 |
| 没有候选文件 | 显示 0 份尝试范围，不填静态示例 | 新一轮从 whole workspace 自主检索 |
| 人长时间不操作 | `waiting_input` 下 active elapsed 冻结 | 随后仍可在剩余 active budget 中恢复 |
| terminal Run | control 不再可用，精确说明停止原因 | 以一条 Branch 创建新的独立 Run |
| workspace 完整性失败 | 继续 fail closed，不当作普通 Gap | 修复资料库完整性后创建新 Run |

## 来源与边界

- Stakeholder 来源：[`USER-FEEDBACK-20260826-ACTIVE-BUDGET-AND-GAP-RECOVERY`](../sources/USER-FEEDBACK-20260826-budget-and-evidence-gap-recovery.md)。
- 研究和前序设计：[`DR-0030`](../decisions/DR-0030-actionable-review-and-recoverable-analysis.md) 与
  [`ACTIONABLE-HITL-RECOVERY-RESEARCH-20260826`](../research/ACTIONABLE-HUMAN-DECISION-AND-FAILURE-RECOVERY-20260826.md)。
- 自动化和截图只验证状态映射、按钮可达与预算不在人工等待时增长，不证明语义正确、
  用户效率、信任、生产稳定性或业务价值。
