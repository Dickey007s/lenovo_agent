# DR-0057：Agent 能力页与智能工作驾驶舱边界

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Draft`；等待源码、浏览器和完整回归 Evidence |
| 日期 | 2026-09-01 |
| 用户来源 | `USER-FEEDBACK-20260901-AGENT-CAPABILITY-PAGE-AND-FUTURE-COCKPIT` |
| 研究输入 | `DEMO1-DEMO2-SEPARATED-VIEWS-AND-ADAPTIVE-SWARM-UI-RESEARCH-20260901` 纠正版 |
| 前置决策 | `DR-0053`、`DR-0054`、`DR-0055`、`DR-0056` |
| 场景 | [`SCENARIO-044`](../scenarios/SCENARIO-044-agent-capability-page-and-future-smart-cockpit.md) |
| 测试合同 | [`AGENT-CAPABILITY-PAGE-AND-COCKPIT-BOUNDARY-GATES-20260901`](../testing/AGENT-CAPABILITY-PAGE-AND-COCKPIT-BOUNDARY-GATES-20260901.md) |
| Evidence | 待实现提交、浏览器截图和验证日志形成后登记 |

## 1. 冲突

`DR-0056` 正确识别了时间维与组织维不能继续挤在根页面，却把独立 Adaptive Swarm
工作台直接称为 Demo 2 的演示面。这与 07-16 基线冲突：

- `Agent Control Loop` 是 Agent 如何跨轮次、跨 Run 持续工作的能力；
- `Adaptive Swarm` 是 Agent 面对复杂任务时如何准入、拆解、协作和收敛的能力；
- Demo 2 的演示产品面是“智能工作驾驶舱”，它从业务任务队列出发，按需选择多种执行
  路线，Adaptive Swarm 只是其中一种路线。

因此“能力检查页”和“业务驾驶舱”必须分开。否则用户会把一个 Runtime 事实面误认为
完整 Demo 2，也会把 Demo 2 缩成只有 Swarm 的技术页面。

## 2. 决策：三个产品面，不是三套 Runtime

### 2.1 Workspace

根页面继续负责资料库、任务输入、安全预览、当前成果和用户决策。它不是 Demo 选择器，
也不显示假任务队列。

### 2.2 Agent 能力页

新增可直接访问和刷新的 `/agent-capabilities`。该页面基于同一个 Owner、Task、Run 和
公共 Snapshot，同时呈现两块同级运行能力：

1. **循环执行能力**：任务会话、Task current pointer、Run 时间线、Round、Branch、
   Evidence Gate、ArtifactVersion、控制与恢复。它回答“同一个任务怎样继续”。
2. **协同编排能力**：TopologyAdmission、批准来源、Branch/WorkUnit DAG、Worker receipt、
   Contribution Gate、v1/v2 与局部失败影响。它回答“复杂任务怎样拆解、协作并收敛”。

两块能力必须使用同一个当前 Run 上下文。选择另一任务会话或历史 Run 后，两个区域一起
切换；历史 Run 整页只读且不接 SSE。页面不能变成静态能力宣传页，也不能从前端常量生成
Worker、路线或成果。

### 2.3 智能工作驾驶舱

智能工作驾驶舱是后续独立页面和 Demo 2 的业务演示载体，当前状态为目标设计。它至少应
包含：

- 按优先级组织的真实任务队列；
- Tool Call、Single Agent、Fixed Workflow、Adaptive Swarm 的服务端路线选择；
- Admission、执行/协作 Workspace、Verify 和待人确认的状态回执；
- 完成后回到队列，以及高风险动作转 Demo 3 Gate 的路径。

本轮不新增该路由、不画假队列、不硬编码“客户 A 经营汇报”，也不把静态 07-16 概念图
当作运行 Evidence。后续实现必须另立 Scenario、Decision、真实 Snapshot 合同和验收门。

## 3. 命名与导航

- 根页面导航使用“Agent 能力”，进入 `/agent-capabilities`。
- 能力页的两个一级区域使用“Agent Control Loop”和“Adaptive Swarm”或对应中文能力名；
  `Demo 1`、`Demo 2` 只作为汇报镜头，不作为服务端状态或 Scenario 入口。
- 旧“打开 Adaptive Swarm 工作台”可重构为能力页内的组织维区域；不得继续把 dialog 本身
  写成 Demo 2 演示完成。
- “智能工作驾驶舱”在实现前只存在于设计文档，不显示可点击但无真实后端的产品入口。

## 4. 技术差异与用户流程影响

主流官方资料已经支持 thread/checkpoint、manager/worker、agent teams、shared task 和
Swarm。本项目不声称竞品做不到。当前差异假设仍是同一服务端事实链把 Task、Run、批准
来源、候选返回、采用和 ArtifactVersion 连起来。

本次新增的交互差异是把“系统能力解释”和“业务任务经营”分开：

| 用户问题 | 所在页面 | 交互结果 |
| --- | --- | --- |
| 我的资料和成果在哪里 | Workspace | 浏览来源、提出任务、查看结果与处理例外 |
| Agent 这一轮为什么这样推进 | Agent 能力页 | 同时核对循环时间线与协作组织图 |
| 今天有哪些任务、优先做哪个、用什么路线 | 未来智能工作驾驶舱 | 从队列分派并回收状态；当前尚未实现 |

这样既不让普通办公工作面承担全部协议细节，也不让未来驾驶舱退化为一张 Swarm 技术图。
这个效果仍需目标用户研究，不能由自动化预先宣称“更清楚”。

## 5. 前台与服务端事实

| 前台内容 | 服务端权威 | 当前边界 |
| --- | --- | --- |
| 任务会话和 Run | Owner-scoped recent Runs + Task current pointer | 只发现最近 20 个 Run，不是 Task list |
| Loop 状态 | Run Snapshot、rounds、branches、events、artifact_versions | 完成不等于业务正确 |
| Adaptive 路线 | `topology_admission.mode/reasons` | Tool Call 仍非当前 route mode |
| 工作包和依赖 | `branches[]/work_units[]` | 单进程有限 Scheduler 子集 |
| Worker 返回与采用 | `worker_runs[]/contributions[]` + Branch Gate | 返回不等于采用或语义正确 |
| 驾驶舱队列 | 尚无公开合同 | 当前不得显示为已实现 |

## 6. 当前不做

- 不新增 Demo/Scenario API 或静态 Demo selector；
- 不实现或伪造智能驾驶舱、客户任务队列、路由执行和 Demo 3 转交；
- 不把当前最多三名进程内只读 Analyst Worker 称为 Dynamic Workers、分布式 Swarm 或生产
  调度；
- 不从截图、Fixture 或 Stakeholder 反馈推断目标用户理解、效率或信任已经改善。

## 7. 进入 `Limited Verified` 的门槛

必须完成独立路由、两个能力使用同一 Snapshot、任务会话切换、历史只读、Adaptive/Fixed
正反例、Workspace 往返、直接刷新、桌面/390 px、公共字段审计、定向和全量回归，并同步
living docs 与 Evidence。智能驾驶舱无论本轮门是否通过，仍保持 `尚未实现`。
