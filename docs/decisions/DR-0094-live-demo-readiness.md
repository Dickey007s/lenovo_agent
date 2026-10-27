# DR-0094：同一入口的实跑与示例验收

日期：2026-10-25。状态：Limited Verified，仅限记录中的固定样例。
实现：现有未提交工作树；没有新提交或 PR。

## 场景与来源

[用户原话](../sources/USER-FEEDBACK-20261025-demo-readiness.md)要求处理执行失败并安排好用的示例。
[SCENARIO-081](../scenarios/SCENARIO-081-ready-office-examples.md)定义验收。
实查发现 3000 前端连接的 8000 服务仍为旧进程，拒绝 execution_policy 字段，返回 422。
旧的两条财务 Run 在 Planner 两次结构输出校验后失败，没有 Analyst 调用。旧回执不能确定底层 Provider 错误类型，不归因为证据不足。

## 前台交互影响

统一保留 http://localhost:3000。旧两条失败 Snapshot 存档后更新后台；不把公开 JSON 存档说成可恢复 checkpoint。
Demo1 六个普通办公/人机分工示例放在一个默认折叠区，不恢复常驻三卡。点击只填输入，提交才执行。
Demo2 默认三项待办缩小资料与输出范围，目标不指定人数或分工。
Word 示例明确把全部必备条件与全部加分项分组交付，不再让已要求的内容变成可选建议。
失败和不完整运行不删除、不改绿。推荐案例按真实结果、来源与覆盖验收，不只看 completed。

## 后端事实映射

不改变 Runtime、公开协议、授权或预算。选择示例只改变浏览器输入。
使用既有 model_receipt / analysis_receipt / worker_runs / contributions / adaptive_reviews / findings / anchors。
缺到账凭证看 uncovered_requirements；未批准变更看 review.requires_human_decision。二者的 Run completed 不代表业务闭环。
实跑工具增加只读 OpenAPI 预检，旧服务缺少 automatic_readonly 时在调用模型前报错。它不是完整版本一致性或 Provider 健康验证。

## 验证与边界

[Evidence](../evidence/DR-0094-DEMO-READINESS-20261025.md)记录 17 次真实运行、46 次调用、推荐 7 例和排除原因。
7 例包含 5 个有界分析结果、1 个缺材料、1 个待负责人选择。只交付页面分析，不生成新的 Word/Excel，不执行业务动作。
真实复杂任务为 3 个 Worker，协调检查没有新增工作；不是动态扩编成功证明。
普通自然语言需求仍可能漏项，模型也可能作过度推断。本轮是示例收敛与验收，不是通用语义完整性修复。
