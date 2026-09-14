# DR-0062：动态边界设计 Evidence

## 2026-09-12 产品方向核对

按 [用户最新纠偏](../sources/USER-FEEDBACK-20260912-integrate-copilot-in-existing-system.md) 形成 [会议简稿](../reports/DEMO3-COPILOT-PROGRESS-BRIEF-20260912.md)。读取源码确认 `apps/web/app/page.tsx` 与 `apps/web/app/agent-capabilities/page.tsx` 仍引用同一 `HarnessWorkbench`；组件内 Loop、协作视图和证据审查入口，以及后端 `continue_unfinished_task` / `execute_admitted_readonly_workers` 仍存在。没有以独立 HTML 替换正式入口。源码存在性不等于运行验收。

快速联网复核 Cocoa、Plan-Then-Execute、When Should Users Check? 的原始摘要/元数据及 Magentic-UI 官方介绍，不重复计为新研究条目。本轮仅调整汇报和方向说明，无新 HTML/PPT、无业务源码修改、无模型/Runtime/浏览器执行。检查时 3000/8010 监听数为 0，未宣称服务可用或新集成通过。之前的研究与测试记录仍按原日期保留。

文档收尾：`uv run pytest tests/unit/test_reporting_governance.py -q` 为 4 passed；5 份定向文档的 41 个本地链接均存在，JSON 台账计数为 6 篇论文、3 篇官方材料。仅验证治理、路径与计数，不验证页内锚点、用户效果或集成运行。

## 2026-09-12 研究推荐增量

[用户委派调研请求](../sources/USER-FEEDBACK-20260912-delegated-copilot-research.md) 后，新增 [6 篇论文与 3 篇官方实践](../reports/copilot-boundary-design-20260911/research/followup-20260912/recommendations.md)。主/子 Agent 分工定向核验原始来源，逐项保留方法、版本、读取范围、限制和待测反例；不是系统综述、论文复现或本项目用户效果。

同一离线 HTML 的研究视图增补分类、搜索、阅读顺序与证据展开。合并 Node 测试 60 passed、静态检查 130 passed、治理 4 passed、TypeScript exit 0；[新增 JUnit](../reports/copilot-boundary-design-20260911/research-test-results-20260912.xml) 与 [完整日期记录](../reports/copilot-boundary-design-20260911/verification.md) 可复核。浏览器仍受策略限制，新增 E2E 断言未执行，没有新截图或用户数据。当前八情境、Runtime 与外部动作边界不变，保持 Draft。

## 2026-09-11 原始记录

日期：2026-09-11。设计状态仍为 `Draft`；不是新 Runtime 能力。

- 来源：[用户新要求](../sources/USER-FEEDBACK-20260911-dynamic-boundary-not-fixed-levels.md)、[8 项增量研究](../reports/copilot-boundary-design-20260911/research/sources.json)。
- 决策：[DR-0062](../decisions/DR-0062-dynamic-boundary-design-experiment.md)；场景：[SCENARIO-049](../scenarios/SCENARIO-049-dynamic-boundary-handoff-design.md)。
- 完整时间线、截图、修复与限制：[verification.md](../reports/copilot-boundary-design-20260911/verification.md)。
- 初版离线浏览器 3 passed；其后内置 Browser URL policy 拒绝直接导航，未绕过或再次换浏览器访问。
- 追加“收件人改回不复活旧授权”反例先红后绿；最终 22 项模型测试、124 项静态检查、4 项治理测试与 TypeScript 检查通过。
- 最后授权撤销/消费、状态文案和焦点修订没有浏览器复验；新增 E2E 断言未执行。截图不能充当最终补丁已验收。
- 无 Provider、Runtime、数据库或外部动作；无用户实验、论文统计复现或真实 Connector 安全测试。既有 Q-01 内容完整性问题未修复。

未提交、未创建 PR、未发布。不能把设计探索或合成回执写成已实现业务动作控制。

## 2026-09-12 后续记录

来源为 [用户理解与继续测试反馈](../sources/USER-FEEDBACK-20260912-user-comprehension-and-testing.md)。本轮调整状态、后果、版本对照和失败查询，增加 `presenter.js` 业务投影及五项非诱导理解任务；详见 [问题与修复](../reports/copilot-boundary-design-20260911/usability-review-20260912.md)。

三个新增模型反例先得到 22 passed / 3 failed，修复后模型 25 + 投影 27 = 52 passed，静态检查 127 passed，治理 4 passed，TypeScript exit 0。原始 [JUnit 记录](../reports/copilot-boundary-design-20260911/test-results-20260912.xml) 与 [日期分段验证](../reports/copilot-boundary-design-20260911/verification.md) 保留证据层次。

没有新的浏览器运行、截图或用户数据；主/子 Agent 源码走查不能当作用户研究。页面布局/点击/焦点的最终门仍未通过，不把旧截图归到本轮。真实工作台、Provider、数据库和 Q-01 未改变，状态继续 `Draft`。
