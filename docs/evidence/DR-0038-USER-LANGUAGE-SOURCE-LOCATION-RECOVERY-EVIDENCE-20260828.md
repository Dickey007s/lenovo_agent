# DR-0038 原表格位置用户语言与局部恢复 Evidence

- 日期：2026-08-28
- 状态：`Limited Verified`（本地完整工程门；远端 PostgreSQL 门待 PR 收尾）
- 实现：[`15d606e895118928e8e99ea70e61b7e9bc7819b1`](https://github.com/Dickey007s/lenovo_agent/commit/15d606e895118928e8e99ea70e61b7e9bc7819b1)
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

## 本地验证

- `uv run pytest -q`：`116 passed, 3 skipped in 36.76s`。三个 skip 是需要显式
  `TEST_DATABASE_DSN` 的 PostgreSQL 集成门，不能写成本地已验证。
- `uv run ruff check .`：通过。
- `pnpm --dir apps/web lint`：通过。首次与 build 并行时因 `.next/types` 被 build 重建而失败，
  build 完成后顺序重跑通过；这是门禁调度冲突，不是产品断言。
- `pnpm --dir apps/web build`：通过，Next.js 静态根页面生成成功。
- `pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts`：
  `32 passed in 1.0m`。
- 三状态回归分别锁定“已生成”“尚未通过”“旧任务已结束”；普通定位动作的 mock control
  负载精确为 `command=resume`、`branch_id=branch-111111111111`。
- 多候选 `accept/cancel/defer/reconnect` 路径在首次全量回归中暴露前台分流回归；修正为 ambiguous
  继续走 DecisionRequest 后，8 条定向回归和 32 条全量浏览器回归全部通过。
- 390 px 回归断言页面 `scrollWidth <= clientWidth`；技术详情默认关闭，展开后仍显示
  `2 个 Branch / 2 个 Gap` 与恢复边界。

## 修复后截图

- [`dr-0038-source-location-user-language-desktop.png`](screenshots/dr-0038-source-location-user-language-desktop.png)，
  `761 x 357`，34501 bytes，SHA-256 `BD25052B257CFFAA6763F850A9D012D7AA2C234AEF71C8D210A0B9D3C75ABE6D`。
- [`dr-0038-source-location-user-language-mobile.png`](screenshots/dr-0038-source-location-user-language-mobile.png)，
  `330 x 702` 的 390 px 视口内容区，34988 bytes，SHA-256 `D40E2CB3F3A57A2D2CA366A61ADE25652AFC97585B816E4C7164FAA1FA03F088`。

两张图证明被测内容区中主标题、已知来源、影响、主动作、成果入口与折叠技术详情可见，
不证明真实用户已理解，也不代表整个页面只包含该截图范围。

## 待补远端证据

- PR、远端 PostgreSQL 顺序恢复门、merge SHA 与最新 `master` 重启健康状态。

## 证明边界

本轮最多证明前台文案、状态映射、目标 Branch 控制和被测布局。它不证明用户理解提升、Agent
说明正确、通用财务 Verifier、原文件修改、真实外部动作、独立 Decision ledger 或多实例并发安全。
