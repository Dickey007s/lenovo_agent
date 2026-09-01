# SCENARIO-044：同页核对循环与协作能力，驾驶舱保持后续目标

- 状态：`Draft`；等待实现与浏览器 Evidence
- 日期：2026-09-01
- 决策：`DR-0057`
- 用户来源：`USER-FEEDBACK-20260901-AGENT-CAPABILITY-PAGE-AND-FUTURE-COCKPIT`

## 1. 目标用户与完成条件

产品负责人或项目负责人已经运行一条办公任务，需要回答两组问题：这条 Task 跨 Run 怎样
继续；复杂任务怎样拆成工作包、哪些 Worker 返回被采用。用户应在一个“Agent 能力”页面
核对两组事实，而不是把 Swarm dialog 误认为完整 Demo 2 驾驶舱。

完成条件：

1. 从 Workspace 可进入独立 `/agent-capabilities`，刷新后仍可恢复服务端 Run；
2. 同页显示 Agent Control Loop 与 Adaptive Swarm 两块同级能力；
3. 两块区域使用同一个 selected Run，切换历史记录后同时只读；
4. Adaptive 与 Fixed Workflow 都只显示真实 Snapshot；
5. 页面不出现伪任务队列或“智能工作驾驶舱已完成”的暗示。

## 2. 可直接使用的输入

### 输入 A：循环执行能力

> 根据入职时间表和分配规则，生成 3 月 20 日至 4 月 20 日的入职资产匹配表。逐项核对
> 人员、岗位、资产和特殊备注；不要修改源文件，发现证据位置不唯一时只暂停受影响分支。

在一条未完成 Branch 上继续后，Task 包含 Run 1 与 Run 2。能力页应显示 current pointer、
历史只读、旧成果保留和只继续目标 Branch。

### 输入 B：协同编排能力

> 请分别核对产品上线、搜索 Agent 运行和用户交互三条工作线中最需要人工处理的风险与
> 证据，形成一份跨职能风险与待办简报。按工作包列出已核对来源、关键发现、缺口、受
> 影响下游和下一步；先独立核对，再统一收敛。不要修改源文件，不要执行代码，不调用
> 外部系统。

当服务端选择 `adaptive_readonly_workers` 时，能力页显示十份批准来源、三个根工作包、
两个依赖工作包、确认门、Worker receipt、Contribution Gate 和 v1/v2。若实际选择固定
流程，则诚实显示本次未启动 Adaptive Swarm。

## 3. 用户过程

1. 用户在 Workspace 运行输入 A 或 B。
2. 点击“Agent 能力”，浏览器进入独立 URL，并恢复当前 Owner 的 Run 上下文。
3. 页面上部或第一视图显示 Loop 的 Task/Run/Round/Branch/Evidence/Artifact 状态。
4. 同一页面的协同区域显示实际路线。Adaptive 时展开 WorkUnit 与 Contribution；非
   Adaptive 时显示真实原因和空态。
5. 用户打开任务会话并切到历史 Run；两块能力一起进入历史只读，不连接历史 SSE。
6. 用户返回 Workspace，原任务和资料上下文仍可继续查看。

## 4. 前台输出

- 页面身份：“Agent 能力”，而不是“Demo 2”或“智能工作驾驶舱”。
- 循环执行：当前/历史 Run、轮次、Branch、Evidence Gate、版本和恢复动作。
- 协同编排：路线、来源、依赖、Worker 调用/采用、Contribution 与成果版本。
- 边界：当前只读、进程内、每波最多三个 Worker；逻辑版本不冒充 DOCX/CSV。
- 导航：返回 Workspace；不显示尚无合同支撑的驾驶舱按钮或任务队列。

## 5. 失败路径

### 历史 Run

Task pointer 指向 Run 2 时打开 Run 1，整页显示历史只读。控制、Branch continuation 和
Worker confirmation 不可用；只有 current Run 恢复 SSE。

### 搜索工作包歧义

搜索 Contribution waiting，只阻断依赖它的统一待办；产品/交互贡献和已有 v1 保留。
能力页说明“停在哪里、影响谁、保留什么”，不把整个 Agent 标成失败。

### Fixed Workflow

三期同结构财务核对不值得启动 Swarm时，能力页高亮 Fixed Workflow，明确零 Worker；
不得为了演示填入五个假 WorkUnit。

### API 或 Task pointer 失败

页面 fail closed 并提供重试或返回 Workspace；不能用本地缓存、同名 instruction 或更新时间
猜测当前 Task。

## 6. 未来智能工作驾驶舱场景边界

07-16 Demo 2 后续应另建独立 Scenario：用户进入按优先级排列的业务任务队列，选择经营
汇报、周报、邮件或报销核查；服务端为每项任务选择 Tool Call、Single Agent、Fixed
Workflow 或 Adaptive Swarm，经过 Admission、Workspace、Verify 后返回完成/待确认状态。

当前公开 API 没有驾驶舱队列、优先级、跨 Task dispatch 或 Demo 3 转交合同，因此本场景
只记录边界，不把该过程列为当前完成条件。

## 7. 当前边界

- 会话发现仍限最近 20 个 Run；memory 状态库随 API 重启丢失。
- Worker 是单 API 进程内、每波最多三个的只读 Analyst，不是 Dynamic Worker 平台。
- 没有通用 Tool Gateway、Connector、Conflict Resolver、分布式 queue/lease 或外部动作。
- 自动化和截图不是目标用户研究；“能力页更容易理解”的结论仍为 `Draft`。
