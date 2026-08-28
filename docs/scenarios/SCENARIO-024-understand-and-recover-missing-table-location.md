# SCENARIO-024：理解并恢复缺少的原表格位置

## 用户与触发

- 用户：正在复核 TC-05 财务成果的业务负责人。
- 触发：三个成果文件已经生成，但一条 Agent 说明只知道来自
  `2026往来明细.xlsx`，尚未定位到具体行或单元格。
- 数据：FORTE 公开 `Finance-018` 输入与当前 Run Snapshot。

## 主路径：成果已通过

1. 成果区先显示三个已经通过确定性检查的文件及其期间、口径和用途。
2. Gap 区显示“成果已生成，还有 1 条说明缺少原表格位置”。
3. 页面说明已知来源文件、不知道具体行或单元格，并明确该 Agent 说明仍需人工复核。
4. 用户可点“查看已生成成果”，页面只回到现有 Artifact；不调用模型、不花预算。
5. 用户点“查找原表格位置”，浏览器提交当前版本、幂等键和一个真实 `branch_id`。
6. Runtime 只从该 Branch 的检查点继续；其他 Branch、已通过 Artifact 和历史版本保持不变。

## 分叉状态

- 成果尚未通过：标题改为“成果尚未通过，说明位置待查找”，不得声称已有文件可用。
- 旧 Run 已终止：标题改为“旧任务已结束，需要新建任务”，只能创建独立新 Run。
- 多候选：显示“从 N 个原文位置中选 1 个”，未选择前不得提交 accept。

## 完成条件

- 首屏不出现 Branch、Gap、Resolution 或“内部步骤”等系统术语。
- “技术详情”默认折叠，展开后仍能看到受影响数量、失败说明与恢复边界。
- 普通非终态定位缺口的主动作只恢复当前 Branch，不重新生成或覆盖 Artifact。
- 页面明确这不是文件缺失、日期错误、金额验算失败或成果生成失败。
- 桌面和 390 px 都能看到主动作，且无页面级横向溢出。

## 不会发生

- 不修改 FORTE 原表，不发送外部动作，不自动花下一轮预算。
- 不把“成果文件已通过”解释为 Agent 说明已经正确。
- 不把浏览器合并显示的一个问题解释为服务端 Branch 合并或并行 Worker。

## 来源与验证

- Source：[`USER-FEEDBACK-20260828-SOURCE-LOCATION-USER-LANGUAGE`](../sources/USER-FEEDBACK-20260828-tc05-artifact-meaning-and-review-readability.md)。
- Decision：[`DR-0038`](../decisions/DR-0038-user-language-source-location-recovery.md)。
- Evidence：[`DR-0038-USER-LANGUAGE-SOURCE-LOCATION-RECOVERY-EVIDENCE-20260828`](../evidence/DR-0038-USER-LANGUAGE-SOURCE-LOCATION-RECOVERY-EVIDENCE-20260828.md)。
