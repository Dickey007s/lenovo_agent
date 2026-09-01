# SCENARIO-043：任务会话回看与 Adaptive Swarm 独立工作台

- 状态：`Historical Limited Verified`；页面归属由 `SCENARIO-044` 修订
- 日期：2026-09-01
- 决策：`DR-0056`
- 用户来源：`USER-FEEDBACK-20260901-DEMO1-DEMO2-SEPARATED-WORKSPACES`
- 研究来源：Codex app、OpenAI Agents SDK、Anthropic、Claude Code、OpenClaw、LangGraph、
  Microsoft HAI 官方资料
- 工程 Evidence：[`DR-0056-DEMO1-DEMO2-SEPARATED-WORKSPACES-EVIDENCE-20260901`](../evidence/DR-0056-DEMO1-DEMO2-SEPARATED-WORKSPACES-EVIDENCE-20260901.md)

> 本场景的服务端事实与历史只读门仍是有效历史证据；“Adaptive Swarm 工作台即 Demo 2
> 演示页”的解释不再是当前设计。现行场景见
> [`SCENARIO-044`](SCENARIO-044-agent-capability-page-and-future-smart-cockpit.md)。

## 1. 场景目标

同一个产品需要同时回答两个问题，但不能把所有信息挤在一个页面：

- 用户如何回到昨天或刚才的任务，看清它经过哪些 Run、现在从哪里继续？
- 一个跨产品、算法和交互的复杂任务为什么进入 Adaptive Swarm，怎样拆分、协作、局部
  失败并收敛？

场景把前者放在主页面的 Agent Control Loop，把后者放在独立全屏工作台。两者都读取
同一份服务端 Task/Run/Snapshot，不新增 Demo 假数据。

## 2. 用户与完成条件

- 用户：同时管理多个办公分析任务，需要回看旧任务，也需要监督复杂协作的产品负责人、
  项目负责人或研发经理。
- 痛点：任务运行记录混在一条长页面中；旧 Run 与当前 Run 容易混淆；Worker 细节很多，
  但 `Adaptive Swarm` 的路线、协作图和统一成果不清楚。
- 完成条件：两个 Task 各自形成会话；同 Task 的 child Run 在会话内；历史 Run 只读；
  Adaptive Run 可打开全屏工作台并看见真实路线、工作包、回执、采用、v1/v2 与局部失败；
  非 Adaptive Run 不显示伪 Worker。

## 3. 可直接使用的输入

### 3.1 会话 A：Demo 1 时间维任务

首个 Run 输入：

> 根据入职时间表和分配规则，生成 3 月 20 日至 4 月 20 日的入职资产匹配表。逐项核对
> 人员、岗位、资产和特殊备注；不要修改源文件，发现证据位置不唯一时只暂停受影响分支。

当一条未完成 Branch 需要续办时，用户在当前 Task 中选择该 Branch，系统创建 Run 2。
Run 1 保留为历史，只读回看；Run 2 只重核该 Branch 批准的来源。这个镜头验证的是同一
Task 跨 Run 连续性，不要求启动 Adaptive Swarm。

### 3.2 会话 B：Demo 2 组织维任务

新建另一条任务会话并输入：

> 请分别核对产品上线、搜索 Agent 运行和用户交互三条工作线中最需要人工处理的风险与
> 证据，形成一份跨职能风险与待办简报。按工作包列出已核对来源、关键发现、缺口、受
> 影响下游和下一步；先独立核对，再统一收敛。不要修改源文件，不要执行代码，不调用
> 外部系统。

固定工程门使用 `SCENARIO-042` 的十份 FORTE 输入：产品管理 4 份、算法研发 3 份、
用户体验 3 份。真实 Provider 仍可根据计划事实选择非 Adaptive 路线，页面必须如实显示。

## 4. 用户动作与系统过程

### 4.1 回看两条任务会话

1. 用户打开“任务会话”，看到会话 A 和会话 B 两个卡片；标题来自各自 instruction 摘要。
2. 打开会话 A，页面显示 Run 1、Run 2；当前 Run 有“当前”标记，Run 1 标为“历史只读”。
3. 用户点击 Run 1，系统关闭当前 SSE，GET Run 1 Snapshot，保留文件、证据、结果和 Trace
   的查看能力，但不显示控制、Branch 续办或 Worker 确认。
4. 用户点击“打开当前 Run”，系统根据 Task pointer GET Run 2；如果它仍在运行，再连接
   Run 2 的 SSE。
5. 用户切到会话 B，旧会话状态不被覆盖；新指令不与会话 A 合并。

### 4.2 主页面理解 Demo 1

会话 A 的主页面按 Task Contract、Round、Branch、Evidence Gate、ArtifactVersion 和
Run lineage 展示。用户能回答：

- 这是同一 Task 的第几次 Run；
- 旧 Run 形成了什么成果；
- 哪个 Branch 在等待，为什么只继续它；
- 新 Run 是否保留旧成果，并只读取批准来源。

Topology/Worker 的完整台账不再挤占主页面；若本次存在协作路线，只显示紧凑摘要和入口。

### 4.3 在独立工作台理解 Demo 2

1. 用户在会话 B 点击“打开 Adaptive Swarm 工作台”。
2. 工作台先显示四条路线框架，只高亮服务端实际选择。若为
   `adaptive_readonly_workers`，标题下同时显示“当前有限实现：受限只读 Worker”。
3. Admission 区解释为什么当前任务跨三个来源组、存在三个独立根工作包和两个依赖工作包，
   并显示剩余预算与人工确认门。
4. 用户确认前 Worker 调用数必须为零；确认后第一波最多启动三个只读 Worker。
5. Supervisor 工作图显示三个根工作包：产品上线、搜索 Agent 运行、用户交互；第二波显示
   产品影响/交互优先级与搜索风险/统一待办两个 dependent。
6. 每个工作包显示真实批准文件、调用回执和 Contribution 状态；returned 与 adopted 分开。
7. 第一波 adopted 形成逻辑 v1，第二波形成 v2；v1 不被覆盖。
8. 用户可从 Contribution 打开证据审查并回到安全 Preview 的原文位置。

## 5. 前台输出

### 5.1 任务会话区

- 会话标题：instruction 的安全摘要；
- 状态：每条记录来自其 Run Snapshot；只有打开后才用 Task pointer 标记 current/history；
- Run 数：只统计最近 20 个 Run 响应中已经发现的同 Task 记录，不按浏览器缓存补齐；
- 历史提示：最近 Run 发现范围受 `GET /runs?limit=20` 限制，不能显示“全部历史”；
- 选择反馈：当前会话、当前 Run 与历史 Run 有明确区分。

### 5.2 Demo 1 主页面

- 继续显示可操作的 Loop、分支、证据门、版本、停止和恢复；
- 历史 Run 只显示“只读回看”，控制按钮不可用；
- 协作只显示路线、工作包计数、当前成果版本和工作台入口，不展开 Worker 聊天墙。

### 5.3 Demo 2 工作台

- 顶部：实际路线、Admission 原因、确认状态、当前有限实现边界；
- 中部：Wave/DAG、工作包、批准来源、Worker receipts；
- 下部：Contribution Gate、ArtifactVersion v1/v2、局部失败影响、Evidence 回开；
- 非 Adaptive 路线：显示“本次未启动 Adaptive Swarm”及原因，Worker 区为空；
- 逻辑成果：没有 `workspace_artifacts` 时明确“尚未生成 DOCX/CSV 下载文件”。

## 6. 失败与停顿

### 6.1 历史 Run 被误当作当前 Run

- 触发：用户点击 Run 1，而 Task current pointer 已指向 Run 2。
- 服务端事实：Run 1 Snapshot 不变；Task GET 指向 Run 2。
- 前台：显示历史只读；关闭 Run 2 的 SSE 后不连接 Run 1 SSE；所有写控制隐藏或禁用。
- 恢复：点击“打开当前 Run”，再次以 Task pointer 为准。

### 6.2 搜索 Agent 工作包 Anchor 歧义

- 触发：搜索 Agent Contribution 的 quote 在批准来源中有多个匹配位置。
- 服务端：该 Contribution waiting/ambiguous，不 adopted；依赖它的统一待办 blocked。
- 保留：产品上线和用户交互 Contribution、部分 v1 和可继续的产品/交互 dependent 保留。
- 前台：工作图只将受影响路径标黄，列出“为什么停、影响谁、已保留什么”；不把整个
  Swarm 标成失败。

### 6.3 本次不值得启动 Swarm

- 触发：三期同结构财务资料具有强顺序依赖，或任务只形成一个工作包。
- 服务端：mode 为 `fixed_workflow` 或 `single_controller`，`worker_runs=[]`。
- 前台：工作台解释“本次未启动 Adaptive Swarm”，不生成 Supervisor/Worker 假记录。

### 6.4 服务离线或 Task pointer 不一致

- 会话列表不能用静态假数据兜底；Run list/Task GET 失败分别显示可重试错误。
- Task pointer 完整性错误必须 fail closed，不能按最近更新时间猜一个 current Run。

## 7. 后端事实

| 用户看到的内容 | 服务端事实 |
| --- | --- |
| 一条任务会话 | 相同 Owner 下相同 `task_id` 的 recent Run 集合 |
| 会话内 Run 时间线 | Owner 范围内 recent Runs 按 `task_id` 分组；Task pointer 只确认 current/history |
| 历史只读 | 渲染 `run_id != current_run_id` |
| 当前 Loop | Run Snapshot、rounds、branches、artifact_versions、events |
| Adaptive 路线 | `topology_admission.mode/reasons/user_confirmation_required` |
| 工作图 | branches + work_units 的 dependency/status/approved refs |
| Worker 已调用/采用 | worker receipt `called/output_used` + contribution state |
| v1/v2 | append-only `artifact_versions` 与 TaskCommit pointer |
| 局部阻塞 | Branch/WorkUnit dependency 与 waiting/blocked 状态 |

## 8. 当前边界

- 当前会话发现范围来自最近 20 个 Run，不是通用 Task list 或无限历史搜索。
- 当前 Worker 仍是单 API 进程内、每波最多三个的只读 Analyst Worker。
- 当前 Supervisor 是 Planner/Runtime/DAG 的有限组合，不是会动态发明角色的生产调度器。
- 当前没有完整 Resolver、语义/数值 Verifier、分布式 queue/lease、Connector 或外部动作。
- 当前逻辑 ArtifactVersion 不等于可下载 DOCX/CSV。
- 自动化与截图不证明目标用户真的理解 Demo 1/2；用户走查仍为必需后续。
