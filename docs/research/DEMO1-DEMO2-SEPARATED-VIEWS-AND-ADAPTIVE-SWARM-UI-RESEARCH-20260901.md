# Agent 能力页、Demo 2 驾驶舱与 Adaptive Swarm 前台研究

- 日期：2026-09-01
- 状态：`Ready` research input；产品效果仍为 `Draft`
- 用户来源：`USER-FEEDBACK-20260901-DEMO1-DEMO2-SEPARATED-WORKSPACES`、
  `USER-FEEDBACK-20260901-AGENT-CAPABILITY-PAGE-AND-FUTURE-COCKPIT`
- 07-16 基线：`未来办公Agent_一小时汇报讲稿_v5` 的 Demo 1 时间维连续性、Demo 2
  智能工作驾驶舱与 Adaptive Swarm Admission
- 当前工程基线：`DR-0053`、`DR-0054`、`DR-0055` 与 `SCENARIO-042`

> 2026-09-01 纠正：初版研究把 Demo 1 Loop 留在根页面、把 Adaptive Swarm 全屏工作台
> 直接作为 Demo 2 组织视图。Stakeholder 指出这会把“Agent 能力”和“Demo 业务演示”混为
> 一谈。现行结论改为：Loop 与 Adaptive Swarm 同属 Agent 能力，在独立能力页并列；07-16
> 的智能工作驾驶舱仍是后续 Demo 2 业务页面，当前不得用 Swarm inspector 代替。

## 1. 先定位问题

当前页面已经有 Task lineage、Round、Branch、Evidence Gate、TopologyAdmission、Worker
回执、WorkUnit、Contribution 和 ArtifactVersion，但它们被放在同一条纵向页面中。
这造成的不是“能力缺失”，而是信息架构把两个不同问题混在了一起：

- Demo 1 要回答：同一个业务任务跨轮次、跨 Run 如何继续，旧成果是否保留，现在应从
  哪里接着做。
- Demo 2 要回答：复杂任务为什么需要协作，如何拆成可并行和有依赖的工作包，哪些候选
  真正进入统一成果，局部失败影响谁。

当这两类信息同屏平铺时，用户会看到很多 Worker 与台账字段，却看不到 07-16 定义的
`Adaptive Swarm` 产品主线；同时也很难把一次任务与另一条历史任务区分开。

## 2. 主流基线告诉我们什么

### 2.1 多任务历史与隔离已是主流交互

[OpenAI: Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/)
把多个 Agent 工作放在按项目组织的独立 thread 中，并用 worktree 隔离并行代码工作。
[LangGraph: Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
把 checkpoint 按 thread 组织，支持查看历史状态、恢复、人工中断和 time travel。

这些资料支持“会话/任务历史必须有稳定身份，历史状态应可回看”的方向。它们也说明
thread/history 本身不是本项目独有创新。本项目需要避免用浏览器 `sessionStorage` 拼出
一套看似存在、刷新后却失真的历史；会话卡必须来自 Owner 范围内真实 Run/Task 事实。

### 2.2 多 Agent 的并行、团队和共享任务也已是主流能力

[OpenAI Agents SDK: Agent orchestration](https://openai.github.io/openai-agents-python/multi_agent/)
区分 manager、handoff、LLM 编排和代码编排，并明确独立任务才适合并行。
[Anthropic: How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
公开了 orchestrator-worker、并行搜索和汇总模式，同时说明协调、任务拆分和成本是主要
工程难点。[Claude Code agent teams](https://code.claude.com/docs/en/agent-teams) 提供
team lead、teammate、共享 task list、依赖和直接会话，并明确该能力仍为实验性，且
协调与 Token 开销显著。[OpenClaw Swarm](https://docs.openclaw.ai/tools/swarm) 公开了
有界并发、collector child、结构化结果和进度回执。

因此不能声称“市面竞品不能拆任务、不能并行、不能显示 Agent 会话”。本项目本轮的差异
假设是：办公用户不需要进入每个 Worker 私聊来判断最终采用了什么；服务端应把任务路线、
批准来源、工作包依赖、返回候选、Evidence Gate 与不可变成果版本放在同一份可审查合同中。
这仍是待用户研究验证的产品假设，不是竞品能力否定。

### 2.3 人机交互研究要求显示状态、后果和纠错入口

[Microsoft Research: Guidelines for Human-AI Interaction](https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/)
给出 18 条通用指南，并通过 49 名设计从业者对 20 个 AI 产品的多轮评估验证其相关性。
其中“及时说明系统能做什么”“显示状态”“支持有效纠错”“说明用户动作后果”直接支持：

- 历史 Run 要标成只读，避免用户误以为可在旧状态上继续操作；
- 启动高成本 Worker 前显示 Admission 原因并要求确认；
- Worker 返回与成果采用必须分开；
- 局部失败应说明影响的下游，而不是只给一个“失败”徽标；
- 非 Adaptive 路线也要说明为什么本次没有启动 Swarm。

该研究不证明本项目界面已经更易懂；正式结论仍需目标用户走查和任务测试。

## 3. 设计决策：Workspace、Agent 能力页、未来驾驶舱

### 3.1 Workspace 负责办公现场

根页面继续是 FORTE Workspace-first 办公资料库，负责浏览安全来源、输入目标、查看成果和
处理例外。任务会话仍按 `task_id` 来自 Owner 范围内 recent Runs；历史/current 由 Task
pointer 判断，而不是由浏览器缓存猜测。

### 3.2 Agent 能力页同时解释时间维与组织维

新增独立 `/agent-capabilities`，但不新增 Demo 选择器。页面使用同一个 selected Run 的
公共 Snapshot，并列两块同级能力：

1. **Agent Control Loop**：Task/Run、Round、Branch、Evidence Gate、控制、恢复和
   ArtifactVersion，回答“同一个任务如何跨轮次、跨 Run 继续”。
2. **Adaptive Swarm**：实际 Route/Admission、Supervisor 工作图、Worker
   `called/output_used/elapsed_ms`、Contribution Gate、依赖和 v1/v2，回答“复杂任务如何
   拆解、协作并收敛”。

选择任务会话或历史 Run 时，两块能力必须一起切换。历史页整页只读且不接 SSE。这个页面
是运行事实检查面，不是静态能力宣传页，也不是 Demo 2 的任务队列。

### 3.3 智能工作驾驶舱仍是后续 Demo 2 演示面

07-16 的 Demo 2 从按优先级排列的日常任务出发，根据服务端事实进入 Tool Call、Single
Agent、Fixed Workflow 或 Adaptive Swarm，再经过 Admission、Workspace、Verify 和人工
确认回到驾驶舱。它解决“今天有哪些任务、优先做哪个、Agent 选了哪条执行路线”的业务
经营问题。

当前 API 没有驾驶舱任务队列、跨 Task 优先级/dispatch 或 Demo 3 转交合同，因此本轮只
保留这一目标设计，不新增可点击假页面。后续驾驶舱应消费同一 Task/Run/WorkUnit/Artifact
事实，而不是再造一套 Runtime。

## 4. 与主流方案的关键差异及交互后果

| 维度 | 主流公开能力基线 | 本项目本轮选择 | 对用户流程的影响 |
| --- | --- | --- | --- |
| 历史组织 | thread/session/checkpoint 已很常见 | `task_id` 是业务会话；Run 是同一任务的有界执行段 | 用户先选任务，再看 Run；旧 Run 可回看但不误操作 |
| 多 Agent 可见性 | 可切换 Agent thread、team pane 或 teammate | 默认不展示 Worker 私聊，集中展示 WorkUnit、来源、回执与采用 | 用户不需复制粘贴多个答案，只审查统一成果和例外 |
| 是否并行 | manager/team/swarm 可发起并行 | 服务端按 DAG、来源跨度、预算和动作边界做 Admission | 用户在花费前知道为什么协作，并能拒绝回到单 Controller |
| 返回与成果 | 多数框架提供消息、结果和 trace 原语 | Contribution returned 与 Artifact adopted 分开 | “Agent 说完了”不再自动等于“当前结论已采用” |
| 局部失败 | 框架可表达 task/dependency 状态 | Branch/WorkUnit 绑定 Evidence Gate 与 append-only v1/v2 | 用户只处理受影响分支，已核对成果不被清空 |
| 前台层级 | 常见方式是 task/thread/team 面板 | Workspace 负责办公现场；独立 Agent 能力页并列 Loop 与 Adaptive；未来驾驶舱负责多任务经营 | 用户不再把 Runtime inspector 误认成完整 Demo 2，也不需要在根页面承受全部协议细节 |

表中“主流公开能力”只来自官方资料，不是同场竞品实测；未提及的能力不能推断为竞品
做不到。

## 5. 为什么这仍然沿用 07-16，而不是另起炉灶

07-16 已规定三段演示的职责：Demo 1 用循环执行讲时间维连续性，Demo 2 用智能工作驾驶舱
讲复杂工作管理与组织维协作，Demo 3 管动作维风险。Loop 和 Adaptive Swarm 都是支撑演示
的 Agent 能力，不等于演示页面本身。Demo 2 的驾驶舱让复杂工作在 Tool Call、Single
Agent、Fixed Workflow 与 Adaptive Swarm 之间分流；Swarm 内部再由 Admission、Supervisor、
Worker、Shared Artifact、Verifier/Resolver 和 Control Plane 协作。

本轮不是新增第四个产品，而是把当前已经真实落地的最小子集放回这个叙事：

- 已实现：可解释拓扑准入、最多每波三个进程内只读 Worker、Branch/WorkUnit、不可变
  Contribution、Evidence Gate、逻辑 ArtifactVersion v1/v2、局部失败保留和独立 Agent
  能力页所需的公共事实。
- 部分近似：Planner/Runtime 共同承担有限 Supervisor；Branch Gate 近似 Verifier 的来源与
  定位子集；Snapshot/控制命令近似有限 Control Plane。
- 尚未实现：智能驾驶舱任务队列/优先级/跨 Task dispatch、真实 Tool Call/Connector、
  动态 Worker 类型与扩缩、通用
  Conflict Resolver、语义/数值 Verifier、分布式 queue/lease、外部动作和生产身份。

## 6. 可证伪的验收假设

1. 两个不同 Task 必须显示为两个会话；刷新后仍来自服务端，而不是浏览器本地假历史。
2. 同一 Task 的 child Run 必须在同一会话内；旧 Run 不应收到 SSE 或暴露控制按钮。
3. `/agent-capabilities` 必须在同一 Run 下同时显示 Loop 与 Adaptive 两块能力，并可返回
   Workspace；不能只是 modal 或静态介绍页。
4. 没有 Adaptive Admission 的 Run 不得显示伪 Worker；协同区域应解释“本次未启动”。
5. Adaptive Run 必须展示确认门、真实工作包、批准来源、回执、采用状态和 v1/v2。
6. 一个根工作包 ambiguous 时，只阻断它的 dependent；旁支与旧版本仍可见。
7. 页面不得显示假智能驾驶舱队列；桌面与 390 px 下正文 13-14 px、辅助文字至少 12 px，
   无横向溢出。

通过这些门只能证明界面与服务端事实一致。是否更清楚、是否降低认知负担、是否提高
任务成功率，仍需至少 5 名目标用户用 Demo 1 和 Demo 2 完成“找回旧任务、解释路线、
定位失败影响、判断当前成果”四个任务，并记录完成率、错误和口述困惑点。
