# Stakeholder 反馈：Agent 能力页与未来智能工作驾驶舱分层

- Source ID：`USER-FEEDBACK-20260901-AGENT-CAPABILITY-PAGE-AND-FUTURE-COCKPIT`
- 日期：2026-09-01
- 类型：Stakeholder 产品反馈
- 关联：`DR-0057`、`SCENARIO-044`

## 原始反馈

> 不对，我观察到一个冲突的地方，demo2的设计本来是这样一个智能座舱，这个是demo2的
> 演示，但是demo2代表的agent能力还是像前面说的一样。所以我想，demo2的能力，还是像
> 我刚刚说的一样，和demo1的循环一起作为agent的能力，在一个新页面中展示，这个demo2
> 的演示效果呢，后面可以单独做一页智能座舱来实现。

附件中的 07-16 视觉基线把 Demo 2 标为“智能工作驾驶舱”，以任务队列承接日常工作，
复杂任务按需进入 `Adaptive Swarm`；右侧依次表达 Admission、Dynamic Workers、Workspace
与 Verify，并在完成、待确认和转 Demo 3 之间回到驾驶舱。

## 支持的产品判断

1. `Agent Control Loop` 与复杂任务拆解/协作是同一个 Agent Runtime 的两类能力，应在
   一个独立“Agent 能力”页面并列展示，而不是分别冒充 Demo 1、Demo 2 的业务演示页。
2. Demo 2 的业务演示载体仍是“智能工作驾驶舱”：它从多任务队列出发，根据任务特点
   选择 Tool Call、Single Agent、Fixed Workflow 或 Adaptive Swarm，再回收执行与验证状态。
3. 当前已经实现的任务会话、Loop、TopologyAdmission、WorkUnit、Contribution 和 v1/v2
   可以支持“Agent 能力”页；它们还不足以证明智能驾驶舱已经实现。
4. 本轮先纠正信息架构和产品命名；驾驶舱作为后续独立页面设计，不能用假任务队列、假
   路由或静态回执提前冒充完成。

## 局限

这是单一 Stakeholder 的产品方向反馈，不是目标用户研究、可用性验证、竞品实测或业务
收益证据。附件是演示概念参考，不是当前系统运行截图，也不能覆盖服务端 Snapshot 事实。
