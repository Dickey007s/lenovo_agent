# DR-0056：Demo 1 Loop 与 Demo 2 Adaptive Swarm 分层工作面

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Draft`；等待源码、浏览器和完整回归 Evidence |
| 日期 | 2026-09-01 |
| 用户来源 | `USER-FEEDBACK-20260901-DEMO1-DEMO2-SEPARATED-WORKSPACES` |
| 前置决策 | `DR-0053` 的 Task lineage/Topology Admission、`DR-0054` 的 Task Ledger、`DR-0055` 的 WorkUnit/Contribution Ledger |
| 研究来源 | `DEMO1-DEMO2-SEPARATED-VIEWS-AND-ADAPTIVE-SWARM-UI-RESEARCH-20260901` |
| 场景 | [`SCENARIO-043`](../scenarios/SCENARIO-043-task-conversations-and-adaptive-swarm-workbench.md) |
| 测试合同 | [`DEMO1-DEMO2-SEPARATED-WORKSPACE-GATES-20260901`](../testing/DEMO1-DEMO2-SEPARATED-WORKSPACE-GATES-20260901.md) |
| Evidence | 待实现提交、浏览器截图与验证日志形成后登记 |

## 问题

当前前台把 Task 时间线、Control Loop、TopologyAdmission、Worker wave、WorkUnit、
Contribution 和 ArtifactVersion 全部放在一个纵向页面。虽然服务端事实已经存在，但
用户很难回答：

1. 这是哪一次任务？之前运行过的任务在哪里？
2. 眼前的 Run 是同一 Task 的下一段，还是一条新任务？
3. Demo 1 的跨轮次/跨 Run 持续推进与 Demo 2 的复杂协作分别在哪里？
4. 为什么页面显示 Worker 和工作包，却没有一个清楚的 `Adaptive Swarm` 工作面？

继续在同一页面加卡片只会放大问题。本决策不新增 Demo 专属 Runtime，也不改变八模块；
只重构信息架构，让同一组服务端事实按“时间维”和“组织维”分别呈现。

## 研究结论与边界

[Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/)、
[LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)、
[Claude Code agent teams](https://code.claude.com/docs/en/agent-teams)、
[OpenAI Agents SDK orchestration](https://openai.github.io/openai-agents-python/multi_agent/)、
[Anthropic multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
与 [OpenClaw Swarm](https://docs.openclaw.ai/tools/swarm) 说明 thread/checkpoint、多 Agent、
共享任务、manager/worker、受限 fan-out 和进度回执均已是主流方向。

因此本项目不声称竞品“不能做会话历史或 Swarm”。本轮差异假设是：面向办公交付时，
任务会话、Run、工作包、批准来源、Worker 返回、服务端采用和 ArtifactVersion 应由同一
服务端事实链连接；用户不需要进入多个 Worker 私聊才能判断当前成果。这个假设仍需用户
研究，工程自动化只能证明前后台一致。

## 决策

### 1. 不新增 Demo 选择器，增加真实任务会话区

根页面继续是唯一 FORTE Workspace-first 工作现场，不新增 `/scenarios`、`demo_id` 或
固定 Demo 数据。页面增加“任务会话”区：

- 会话身份严格等于 `task_id`，不是 instruction 文本、浏览器 tab 或时间戳；
- `GET /v1/harness/runs?limit=20` 提供 Owner 范围内最近 Run，浏览器按 `task_id` 分组；
- 每个组用最新 Run 的 instruction 摘要、当前状态和 `run_sequence` 显示一个会话卡；
- 选中会话后，再以 `GET /v1/harness/tasks/{task_id}` 的 lineage 显示该 Task 最近最多
  100 个 Run；点击某一 Run 必须 GET 它自己的公共 Snapshot；
- 前台明确“显示最近 20 个 Run 涉及的任务”，不能暗示拥有无限历史或 Task list API；
- `sessionStorage` 只可记住最后打开的 Run，不得成为会话列表或状态权威。

新 instruction 仍由 `POST /runs` 创建新 Task；Branch continuation 仍由 `POST
/runs/{run_id}/continue` 创建同 Task 的 child Run。浏览器不能靠标题相同把两个 Task
合并，也不能把同一 Task 的 child 当成新会话。

### 2. 历史 Run 是可审查、不可控制的页面状态

当渲染 Run 不是 Task current pointer 时，页面显示“历史 Run，只读回看”：

- 允许查看 Snapshot、Branch、Evidence、ArtifactVersion、Trace 与安全文件预览；
- 隐藏或禁用 pause/resume/steer/stop/rollback、Branch continue、Worker confirmation；
- 不连接该历史 Run 的 SSE；只在用户切回 current 且 current 非终态时连接事件；
- “打开当前 Run”使用 Task pointer 的 `current_run_id` 再 GET，不按更新时间猜测；
- 历史 Snapshot 不被新事件覆写，切换会话时先关闭旧 transport、重置 Run 级 sequence。

这使 Demo 1 的时间维连续性成为真实可操作路径，而不是一段解释文案。

### 3. 主页面只负责 Demo 1 的 Agent Control Loop

弹窗外保留：Workspace、Task Contract、Round、Branch、Evidence Gate、控制、
ArtifactVersion/TaskCommit、Run lineage 和结果。Topology/Worker/WorkUnit/Contribution
的完整明细移出主页面，只保留一个紧凑摘要：

- 本次路线；
- 是否需要/已经完成人工确认；
- 工作包完成/等待/失败数量；
- 当前逻辑成果版本；
- “打开 Adaptive Swarm 工作台”按钮。

摘要仍完全来自当前 Snapshot。没有 `topology_admission` 时不造 Swarm 状态，只显示当前
Run 尚未形成协作路线。

### 4. Demo 2 使用独立全屏 Adaptive Swarm 工作台

工作台使用 `role=dialog` 或等价可访问全屏容器，标题必须是“Adaptive Swarm 工作台”，
并始终显示边界徽标“当前有限实现：受限只读 Worker”。它包含六个事实区：

1. **路线与 Admission**：用 Tool Call、Single Controller、Fixed Workflow、Adaptive
   Swarm 四条路线解释产品框架，只高亮服务端实际 `topology_admission.mode`。当前协议
   没有 Tool Call mode，因此 Tool Call 只能标“目标能力，未在本 Run 执行”。
2. **确认门**：显示是否需要用户确认、确认前零 Worker 调用、预算和为什么值得并行。
3. **Supervisor 工作图**：按服务端 Branch/WorkUnit 的 dependency/wave 展示业务名称、
   批准来源和被谁阻塞；不暴露 raw unit ID。
4. **Worker 回执**：显示 `called/output_used/elapsed_ms/outcome` 与工作包状态；不把
   `called=true` 说成已采用。
5. **Contribution Gate**：把 returned、adopted、waiting、rejected、failed 分开，并提供
   Evidence Anchor 回开入口。
6. **统一成果与失败影响**：显示 ArtifactVersion v1/v2、保留的兄弟成果和受影响下游；
   没有 `workspace_artifacts` 时明确“尚未生成 DOCX/CSV 下载文件”。

`adaptive_readonly_workers` 在中文产品层映射为 `Adaptive Swarm`，但协议值保持不变，
并在同屏说明：当前仅为当前 API 进程内、每波最多三个、只读 Analyst Worker；不是
distributed queue、lease、动态扩缩、远端 Worker、Connector、完整 Tool Gateway、
Conflict Resolver、外部动作或生产 Swarm。

### 5. 非 Adaptive 路线也能打开工作台，但不伪造协作

当实际 mode 为 `single_controller` 或 `fixed_workflow` 时，入口改为“查看协作路线”或
保留统一工作台入口，打开后显示“本次未启动 Adaptive Swarm”及服务端 Admission 原因。
Worker、WorkUnit、Contribution 区只显示真实空态，不能用演示图填充。

这样 Demo 2 同时证明“该并行时受控协作”和“不该并行时不并行”。

### 6. 弹窗交互与字号

- 全屏工作台使用页面级布局，不把卡片嵌套进卡片；桌面支持横向 DAG/分栏，390 px 改为
  单列并保持稳定宽度。
- 正文、事实和回执使用 13-14 px；辅助说明不得低于 12 px。
- 支持关闭按钮、`Escape`、焦点锁定与关闭后返回入口；背景不可继续操作。
- 任何标题、文件名和中文状态不得横向溢出或遮挡；不使用缩放字体掩盖问题。

### 7. 前台状态与后端事实映射

| 前台状态 | 权威事实 | 用户可做 | 禁止暗示 |
| --- | --- | --- | --- |
| 任务会话卡 | Owner-scoped recent Run Snapshots，按 `task_id` 分组 | 打开某 Task 的最新/历史 Run | 无限历史、浏览器本地持久化、跨 Owner 可见 |
| Run 时间线 | Task pointer `current_run_id/task_version/lineage` | 选择 Run、打开 current | 旧 Run 被重新启动、parent 被修改 |
| 历史只读 | 渲染 Run 与 Task current pointer 不同 | 查看证据和成果 | 控制、SSE 或 Worker 调用仍作用于历史 |
| Adaptive 摘要 | `topology_admission/work_units/contributions/artifact_versions` | 打开工作台 | 模型自己决定后已自动花费 |
| 路线高亮 | `topology_admission.mode/reasons` | 查看原因、在允许时确认 Worker | 未实现路线已执行 |
| Supervisor 工作图 | Branch/WorkUnit dependency 与状态 | 查看来源、依赖和失败影响 | 动态分布式调度或 raw Worker 私聊 |
| 候选采用 | Contribution + Branch Gate + ArtifactVersion | 回开 Evidence、处理例外 | 返回即采用、Anchor 即语义正确 |

## Demo 1 与 Demo 2 的分工

- Demo 1：时间维。一个 Task 的 Run 1、Run 2、轮次、分支、Evidence Gate 和成果历史在
  主页面持续呈现。
- Demo 2：组织维。复杂任务在独立工作台中展示路线、Admission、Supervisor、Worker、
  Contribution Gate 与统一成果。
- 两者共享 Task/Run/Branch/WorkUnit/Contribution/ArtifactVersion，不形成两套 Runtime。

## 当前不做

- 不新增 Scenario/Demo API、硬编码 Demo 入口或假 Agent 对话；
- 不把每个 Worker 做成用户必须管理的聊天框；用户要求的聊天隔离是业务 Task 会话；
- 不新增 Task list API，首版复用最近 Run 列表并明确最多 20 个 Run 的发现范围；
- 不实现动态 Worker 类型、分布式 queue/lease、多实例协调、真实 Connector/Tool Gateway、
  Conflict Resolver、外部动作或源文件写回；
- 不从自动化或截图推断用户理解、效率、信任或业务效果已经改善。

## 进入 `Limited Verified` 的门槛

只有实现提交、定向/全量自动化、1440/390 截图、公共字段审计与 living docs 全部完成，
本决策才能从 `Draft` 升为 `Limited Verified`。测试细节见对应测试合同；用户研究结论在
任何情况下仍保持 `Draft`，直到真实目标用户完成任务走查。
