# DR-0038 原表格位置用户语言与局部恢复 Evidence

- 日期：2026-08-28
- 状态：`Draft`，待完整工程门、截图与 PR 收尾
- Decision：[`DR-0038`](../decisions/DR-0038-user-language-source-location-recovery.md)
- Scenario：[`SCENARIO-024`](../scenarios/SCENARIO-024-understand-and-recover-missing-table-location.md)
- Source：[`USER-FEEDBACK-20260828-SOURCE-LOCATION-USER-LANGUAGE`](../sources/USER-FEEDBACK-20260828-tc05-artifact-meaning-and-review-readability.md)

## 负例

[`user-feedback-20260828-source-location-jargon.png`](screenshots/user-feedback-20260828-source-location-jargon.png)
显示旧页面把一个局部引用跳转缺口写成“审计项、来源定位、内部步骤”。该截图只能证明用户看到
了这组真实文案并提出困惑，不证明新方案已经更容易理解。

## 实现事实

1. 浏览器从 Artifact/EffectReceipt、Run terminal 状态和 `source_location` Gap 投影三种不同状态。
2. 已通过状态前置成果、已知文件、缺少行或单元格、影响和两个用户动作；内部协议默认折叠。
3. 普通非终态“查找原表格位置”直接提交目标 Branch 的 `resume`；structured Resolution、
   ambiguous 或 terminal 状态仍走各自受控路径。
4. “查看已生成成果”只滚动到当前 Artifact 区，不调用模型、不生成文件。

## 待补验证

- 本地 Python、Ruff、TypeScript lint、Next build 与完整 Playwright 数字。
- 三状态 E2E、目标 `branch_id` 控制负载、技术详情折叠和 390 px 无溢出。
- 修复后桌面/390 px 截图、尺寸、字节和 SHA-256。
- PR、远端 PostgreSQL 顺序恢复门与 merge SHA。

## 证明边界

本轮最多证明前台文案、状态映射、目标 Branch 控制和被测布局。它不证明用户理解提升、Agent
说明正确、通用财务 Verifier、原文件修改、真实外部动作、独立 Decision ledger 或多实例并发安全。
