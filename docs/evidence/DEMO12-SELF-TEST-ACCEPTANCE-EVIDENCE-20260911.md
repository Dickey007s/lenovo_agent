# Demo 1/2 主动验收 Evidence

- 日期：2026-09-11；当前共享工作区未提交变更，未创建 commit/PR。
- 来源：[用户主动验收要求](../sources/USER-FEEDBACK-20260911-self-testing-and-acceptance-cases.md)。
- 决策：DR-0060 / DR-0061；场景：SCENARIO-047 / SCENARIO-048。
- [操作用例与失败判据](../testing/DEMO12-ACCEPTANCE-CASES-20260911.md)。
- [HTML 观察报告](../reports/demo12-acceptance-20260911/index.html)。

## 发现与处理

| ID | 发现 | 状态 | 证据 |
| --- | --- | --- | --- |
| UI-01 | 协作视图点击新建任务，草稿已清空但输入面未打开 | 已修复 | 真实页面复现；新增用例先失败于 aria-selected=false，修复后通过 |
| UI-02 | 歧义候选页缺少待核对判断的标题/摘要 | 已修复 | 直接投影 Resolution finding_title/fact_summary；未确认标签、无预选不变 |
| Q-01 | 模型摘要把截断前半段当作整份日志范围 | 未解决 | 真实 Run 摘要与后段来源反例；本轮不修改 Runtime/来源读取合同 |

新建任务显式移除旧协作 hash，切换到输入面并清理前台局部展开状态，不依赖 Run ID 变化。
Playwright 使用独立 `.next-playwright` 构建目录，避免与用户正在使用的 3000 开发服务争用锁；测试 API 仍是 8011。

## 真实 Provider 观察

通过实际内置浏览器提交 AC-02 原始输入；不是 API Fixture，也不是配置模型名冒充调用。

- Run：`harness:2e562ba94fc741dbba66bf1b7fef4cb7`；Task：`task-62be38fdd37c`。
- 检查点：memory；模型回执：`deepseek-v4-pro`。
- 第 1 轮，2 份批准来源，3 次模型调用，active elapsed `63559 ms`。
- 事件 3–4：Planner；7–8：首次 Analyst；9：定位拒绝；10–11：受控 Analyst 重试；12：仍有部分定位失败。
- 事件 13 明确无确定性成果可供叙事对账；15 要求歧义消解；16 最小分支等待。
- `status=waiting_input`、`control_state=paused`；v1 逻辑简报保留 2 条发现；不是整项任务完成。
- 4 个真实候选对应日志第 13/39/65/91 行；实际预览成功；未选中、未确认、未启动下一轮。
- 关闭成功写入 defer（事件 17）；新建空草稿与历史回开后，Run/Task、调用数和成果保持不变。
- 没有 Worker 派发，没有下载办公写入成果，没有执行 FORTE 源码，没有外部动作。

## Q-01 原因定位

当前 `benchmark_workspace_catalog.py` 的 `MAX_AGENT_TEXT_PER_FILE=12_000`，
`agent_file_inputs()` 对模型输入单独截断并带 `truncated`，不同于浏览器完整安全文本预览。
原日志共 25,211 字符；前 12,000 字符到约 109 行，不含第 113 行后的第二次启动。
完整原文的 155/162、212/216 行分别有 news 分类与 web_search_news 选择。
当前摘要没有声明只分析前段，因而不能用于整日志的完整结论。

这是可重复的输入覆盖边界，不是一次随机模型幻觉的充分证据；有 `truncated` 标记也不等于已实现未读区间的检索和完成门。
本轮把问题列为开放项，没有提高读取上限、硬编码来源或用 UI 文案偷偷修饰原始模型摘要。

## 工程门

- 新建任务 RED：1 failed / 2 passed，失败明确为协作 tab 未退出。
- 修复后定向 GREEN：3 passed，15 秒。
- 全量 Playwright：91 passed，3.3 分钟；包含 Demo 1/2 受控协作、选择冲突与移动端回归。
- `pnpm --dir apps/web lint`：通过；`pnpm --dir apps/web build`：通过，5/5 静态页面。
- 文档治理：4 passed；新增报告检查脚本 Ruff 通过；`git diff --check` 通过（仅已有 LF/CRLF 提示）。
- 截图资产检查发现浏览器实际返回 JPEG，初始 `.png` 扩展名错误；已改为 `.jpg`，不重新编码或编辑图像。
- 真实页面截图可视检查：输入面恢复、判断上下文与无预选；报告 HTML 仅做源/链接/资产检查，不冒称独立浏览器验收。
- 定向截图复跑：1 passed，17.3 秒；[390 px 判断与候选](../reports/demo12-acceptance-20260911/controlled/evidence-candidates-390.png) 已可视检查，无重叠或横向溢出。
- HTML 源检查：6 个唯一 ID、8 个链接、4 个 JPEG 资产通过；实际工作台浏览器 error 日志为空。
- 5 份验收关联 Markdown 的 20 个本地链接通过检查。

## 范围限制

这一次真实单分支运行不证明语义完整性、业务质量、通用 Swarm、PostgreSQL 重启、分布式 Worker 或目标用户效果。
自动化继续使用受控 API；没有付费模型批量回归。本轮前端修改不声称再次执行全部 Python Runtime 测试。
