# 用户反馈：TC-01 成果已完成，但“缺引用”和“重试分支”使状态难以理解

## 来源

- Source ID：`USER-FEEDBACK-20260828-TC01-OUTCOME-CITATION-CONFUSION`
- 类型：Stakeholder 真实试用反馈与结果复核
- 日期：2026-08-28，Asia/Shanghai
- 任务：`根据入职时间表和分配规则，生成 3 月 20 日至 4 月 20 日的入职资产匹配表。`
- 关联：`DR-0036`、`SCENARIO-022`

## 用户观察

用户下载并打开了 `入职资产匹配表.csv`，确认入职日期没有明显问题，但同一页面同时显示
“缺 1 份引用”“建议重试此分支”“重试此分支”和多个待处理分支。用户无法判断：成果究竟能否
使用、源文件是否有问题、日期是否算错，以及自己是否必须再次操作。

原始界面与成果截图：

- [`user-feedback-20260828-tc01-artifact-and-citation-confusion.png`](../evidence/screenshots/user-feedback-20260828-tc01-artifact-and-citation-confusion.png)，`1374 x 1275`，250084 bytes，SHA-256 `F19BB14B38EFBADA97609C20AD8BF31B80923140D11578445991303930015616`。
- [`user-feedback-20260828-tc01-generated-output.png`](../evidence/screenshots/user-feedback-20260828-tc01-generated-output.png)，`1653 x 670`，155989 bytes，SHA-256 `6C06AAB74E7EC9857EE5CE8B02AE3BE9EA5FA6697E625708B190A228114E6B05`。

## 支持的判断

- “成果效果是否通过”和“Agent 说明中的原文位置是否可回开”是两种不同状态，不能用同一组警告文案表达。
- 已验证成果应先于内部 Branch/Evidence Gap 展示，并明确引用定位缺口不等于源文件缺失、日期错误或成果失效。
- 同一来源定位失败投影到多个内部 Branch 时，普通用户不应看到多个含义相同的重试入口。
- TC-01 必须继续验证 PDF 规则原文、日期范围和特殊备注，而不是只检查 CSV 已生成。

## 不能支持的判断

- 这是一次 Stakeholder 试用反馈，不是目标用户样本研究，不能量化问题发生率或理解提升。
- 用户人工查看日期没有发现问题，不等于所有字段、规则和备注都正确；成果正确性仍以确定性 Verifier 为准。
- 该反馈不能证明竞品不存在类似能力或问题。
