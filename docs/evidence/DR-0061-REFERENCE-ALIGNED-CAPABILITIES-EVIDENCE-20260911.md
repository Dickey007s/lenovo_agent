# DR-0061：参考图能力页与证据选择验证

- 日期：2026-09-11，Asia/Shanghai。
- 决策：[DR-0061](../decisions/DR-0061-reference-aligned-capabilities-and-evidence-choice.md)。
- 场景：[SCENARIO-048](../scenarios/SCENARIO-048-review-progress-collaboration-and-evidence-choice.md)。
- 可视化交付：[重设计评审 HTML](../reports/demo12-redesign-20260911/index.html)。

以下为最初重设计验收快照。随后用户要求主动测试，发现两个 UI 漏项并修复，
且真实 Provider 单任务暴露内容覆盖问题；最新结果见
[主动验收 Evidence](DEMO12-SELF-TEST-ACCEPTANCE-EVIDENCE-20260911.md)。不追改历史测试口径。

## 已执行

| 检查 | 结果 | 边界 |
| --- | --- | --- |
| `uv run pytest -q` | 429 passed, 23 skipped，439.10 秒 | 未满足数据库条件门；无本轮 PostgreSQL 复跑 |
| `uv run ruff check .` | 通过 | 静态检查 |
| `pnpm --dir apps/web lint` | 通过 | TypeScript 检查，不是浏览器验收 |
| 定向 Playwright | 6 passed | 预览/选择、失败退出、权威 ID、stale、终态、DAG 尺寸 |
| 全量 Playwright | 90 passed，最终 3.3 分钟 | 早期 85 passed / 2 failed 为旧导航选择器，已修复；最终包含滚动位置回归 |
| `pnpm --dir apps/web build` | 通过，5/5 静态页生成 | 不替代实际服务连通性 |
| 文档治理门 | 4 passed | 新文档落盘后单独复跑 |
| 实际预览 | 3000 前端、8010 API；health=ok，memory | 未提交任务；配置模型名不算调用证明 |
| 评审 HTML 源检查 | 唯一 ID、14 个链接、8 张 PNG 尺寸、JS 语法通过 | 不等于该 HTML 的独立浏览器验收 |

## 新增覆盖

源候选无预选、查看原文不改变选择、确认 ID/revision/version/幂等键、对话框焦点边界、
确认冲突、defer 冲突立即退出、同 Finding 多 Resolution、顶层新 revision 优先、stale
非 pending、终态仅记录引用、部分协作与 1672/1440/390 px 图节点不裁切。
进入执行记录或切换能力视图时回到顶部，避免沿用上个视图的滚动位置。

实际内置浏览器已检查资料加载、同级视图切换与新任务草稿，控制台无错误。
后台 `Start-Process` 方式曾被执行策略拒绝；预览改由正常工具受管命令运行，
未改系统策略、网络暴露或安全设置。旧 3011 测试服务结束后的页签失效，未操作其错误页。

## 截图与比较

正式截图均为真实 React 组件 + Playwright 受控 API，并非真实模型生成的任务成果。

- [任务进展](../reports/demo12-redesign-20260911/screenshots/progress-1672.png)
- [执行记录](../reports/demo12-redesign-20260911/screenshots/record-1672.png)
- [组织维协作](../reports/demo12-redesign-20260911/screenshots/collaboration-1672.png)
- [原文候选确认](../reports/demo12-redesign-20260911/screenshots/evidence-1672.png)
- [手机协作](../reports/demo12-redesign-20260911/screenshots/collaboration-390.png)
- [手机证据核对](../reports/demo12-redesign-20260911/screenshots/evidence-390.png)
- [手机候选原文](../reports/demo12-redesign-20260911/screenshots/evidence-candidates-390.png)
- [视觉 QA](../../design-qa.md)

## 独立子 Agent

[人机共驾设计包](../reports/human-agent-copilot-20260911/README.md) 含两个 HTML、8 个案例、
手册与来源台账。38 项源级检查与 JavaScript 语法检查通过；浏览器因 `file://` 策略拒绝，
未绕过，不能宣称实际 DOM/E2E 或手机视觉已验证。沙盘不连接 Runtime、不执行外部动作。

## 未验证

本轮没有真实 Provider 调用、真实 PostgreSQL 重启、多实例 lease、生产身份、外部动作、
跨设备测试或目标用户研究。UI 明确边界不等于已实现通用风险分级引擎。完整行业回溯尚未开展。
