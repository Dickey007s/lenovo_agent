# DR-0084：基于原系统截图的能力演示

日期：2026-10-23。状态：Limited Verified；仅限 [Evidence](../evidence/DR-0084-SHOWCASE-20261023.md) 的范围。
场景：[SCENARIO-071](../scenarios/SCENARIO-071-browse-office-capability-cases.md)。
实现：当前工作树增量，未提交、未建立 PR；HEAD 基线 fa974ae339c9c4d97d0505eb3eef3e8a81e8ca11。

## 场景与来源

[USER-FEEDBACK-20261023-CAPABILITY-SHOWCASE](../sources/USER-FEEDBACK-20261023-capability-showcase.md) 要求以三组能力栏、五六个以上案例和逐张系统截图讲解能力。
三张附件仅作为布局参考，不作为系统能力证据。案例输入由本轮自拟；现有 Fixture 及固定规则 API 支持状态展示，不支持通用模型效果或用户收益。

## 前台交互影响

新增独立的离线讲解目录 `docs/showcase/office-agent-20261023/`，不替换原系统入口。
八案按任务推进、只读协作、人机共驾分组。指令、截图、当前步骤和最终产出形成主路径，来源与边界按需展开。
支持步骤箭头、键盘、原尺寸大图、手机横向案例列表、地址恢复、复制指令和明确的加载错误。
用户切图只改变页面状态，不创建 Task、不派发 Worker、不执行事项。打开工作台不自动提交。

捕获时发现 ResultView 在有 passed 文件/回执但无 Result 和确定性 authority 时，错误地断言“只保留失败或受限回执”。
本轮增加中性提示“检查结果已保留，分析结论尚未形成”。失败详情、业务否决、待办与原对账权威条件不变。
这是 DR-0052 第 7 条的边界澄清：缺少权威组合不能声明权威，但也不能否认已存在的 passed 检查。

## 后端事实映射

静态案例元数据只负责讲解，不进入协议。图片来自原前端；Demo1/2 用现有受控 Snapshot，Demo3 用真实固定规则 API。
文件状态仍对应 workspace_artifacts.verifier_status 与 effect_receipts.status；分析权威仍同时要求 reconciliation.authority=deterministic_outcome 和 passed 证据。
协作图对应 WorkUnit 依赖、Branch、Worker 和 Contribution；不从图片推断真实并行执行。
Demo3 的 office_action.status/revision/receipt 为服务端事实；捕获断言 model_called=false、external_action=none。
没有新 API、无模型输入变化、无存储或权限变化。截图缺失只显示加载错误，不伪造完成状态。

## 验证与边界

八案捕获 27 张 1600 × 1000 截图；四视口离线交互检查，具体结果见 Evidence。
新增成果提示定向浏览器回归覆盖根页、能力页；既有失败与拒绝叙事回归保留。
本轮不运行真实 Provider、不验证数据库重启或业务效果；受控两波并非实际模型协作证据。
Worker 歧义人工恢复到下游未闭环；截图回放不是自然语言通用任务演示引擎。
