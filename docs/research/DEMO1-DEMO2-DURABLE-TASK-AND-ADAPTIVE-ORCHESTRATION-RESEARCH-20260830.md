# Demo 1/2 深入研究：跨 Run 任务连续性与可解释协作拓扑

- 日期：2026-08-30
- 状态：`Ready` 研究输入；其中产品价值与用户体验判断仍为 `Draft`
- 用户来源：`USER-FEEDBACK-20260830-DEMO1-DEMO2-CONTINUATION`
- 对应决策：`DR-0053`
- 对应场景：`SCENARIO-038`、`SCENARIO-039`

## 1. 研究问题与结论

这轮研究不再把“可以暂停”“可以多开几个 Agent”当作创新点。持久化、暂停恢复、
任务列表、并行子 Agent 和流式状态，已经出现在多种主流 Agent SDK、开发者产品和
工作流运行时中。真正需要回答的是：这些机制进入办公任务后，谁有资格改变当前
结论，用户怎样知道旧成果没有被覆盖，以及多 Worker 何时值得启动。

本轮形成两个可证伪的产品方向：

1. **Demo 1 从 Run 连续升级为 Task 连续。** 当前系统已能在一个 Run 内维护服务端
   Branch、Evidence Gate、最多 12 轮预算、append-only 逻辑 `ArtifactVersion`、
   `TaskCommit` 和可选 PostgreSQL 重启恢复；下一步不是继续放大单 Run 预算，而是
   引入跨 Run 的稳定 `task_id` 与来源谱系。一个 Run 到达预算或终态后，用户可以
   在同一个业务任务下创建后继 Run，明确哪些分支、证据和成果被继承，哪些必须
   重新核对。旧 Run 永远不被改写。
2. **Demo 2 从“多 Agent 展示”升级为可解释的拓扑准入与服务端收敛。** 系统不按
   Prompt 中的“请多 Agent”直接扩容，而是由服务端根据来源跨度、工作包独立性、
   依赖耦合、预算与风险给出路线和理由。只有被确认的高并行只读任务才启动受限
   Worker；每个 Worker 的候选必须经过现有引用、Anchor、Evidence Gate 和适用的
   确定性对账，才能进入统一成果。

这两个方向保持 07-16 的原始分工：Demo 1 解决时间维连续性，Demo 2 解决组织维
复杂性。它们不新增第九模块，也不恢复旧 Scenario/Demo 专属 API。

## 2. 现行事实、近似能力与目标设计

### 2.1 当前真实实现

- 用户在 FORTE Workspace-first 文件管理器中面对 15 个目录、96 份可安全预览输入；
  Run scope 由服务端冻结为整库，浏览器不提交隐藏文件范围。
- `AgentControlLoopOptions.max_rounds` 当前默认 12、上限 24；默认每轮最多 16 份文件、
  30 次模型调用、7200 秒活动期限。历史“固定三轮”已经不是当前预算口径。
- 当前是单 Controller 的有界流程。Planner 和 Analyst 真实调用与采用状态分开，
  服务端编译 Branch、校验本轮来源、解析 Evidence Anchor，并维护 Snapshot/named SSE。
- 每轮完成后可生成 append-only 逻辑 `ArtifactVersion`；`TaskCommit` 只移动当前版本
  指针，恢复历史成果不会删除新版或改写源文件。
- 配置 PostgreSQL 时可保存 Snapshot、事件、幂等回执、成果和提交；重启后不会
  自动重放中断的模型调用，而是在可审查检查点暂停。
- 十二个固定服务端适配器可在隔离 Run Workspace 生成有限类型成果并作确定性检查；
  这不是通用 Tool Gateway，也不是任意办公文件执行环境。

### 2.2 部分近似

- `run_id` 可标识一个 Run，PostgreSQL 可恢复该 Run，但当前没有跨多个终态 Run 的
  稳定业务 `task_id`、父子 Run 谱系和继承回执。
- Branch 可表达同一 Run 内的业务工作线，Planner 也可生成多个 plan unit；当前仍由
  单一 Controller/Analyst 路径推进，不是多个独立 Worker 的调度与收敛。
- 前台可显示 Branch、引用、成果版本和控制回执；尚未形成统一的“路线建议、工作包、
  实际 Worker、采用状态、阻塞影响”驾驶舱。

### 2.3 尚未实现

- 跨 Run `task_id`、`parent_run_id`、继承分支/成果/来源 revision 的强类型合同。
- 通用 `TopologyAdmission`、受限 Worker DAG、Worker lease、共享成果候选和确定性合并。
- 通用 Tool Gateway、真实 Connector、生产写入、多实例协调、语义/数值通用 Verifier。
- 能证明体验、效率、信任或业务质量改善的目标用户研究。

## 3. 07-16 必须保留的产品不变量

### 3.1 Demo 1：时间维连续性

07-16 的关键不是“Agent 一次跑很久”，而是同一业务任务在时间上保持稳定身份、
任务契约、状态版本、业务分支和恢复点。主流程仍然是：

```text
Task Contract -> Observe -> Plan -> Act -> Verify -> Commit
```

典型冲突是正式收入 2400 万与预测口径 2680 万同时存在。系统不应让模型擅自选择，
也不应让整个任务失败；只让 `revenue-baseline` 分支暂停，其他客户事实和项目风险
成果继续保留。用户选择“正式口径作为当前结论，同时保留预测差异说明”后，系统只
恢复受影响分支，并将来源、版本、验证和 Trace 一起提交。

本轮把“不必重讲背景”具体化为跨 Run 的可审计继承，而不是让一个 Run 无限续命。

### 3.2 Demo 2：组织维复杂性

07-16 的目标形态是一个智能工作驾驶舱：聚合邮件、CRM、项目、报销和日历等工作
信号，解释优先级，并按任务特征选择成本合适的处理路径：

```text
直接工具 -> 单 Agent -> 固定流程 -> Adaptive Swarm
```

当前阶段不实现真实 Connector，也不把这些来源伪装成已接入。可先在现有只读办公
资料范围内验证后三种路径的准入、工作包和成果采用；“直接工具”保留为 Tool Gateway
完成后的目标路径。

Demo 2 的价值不在屏幕上出现很多 Agent 头像，而在用户只管理优先级、路线理由、
例外和统一成果。多 Worker 必须证明其任务可并行且收益可能覆盖协调成本；否则应
回退到单 Controller 或固定流程。

## 4. 主流技术已经解决了什么

### 4.1 持久化、暂停和跨天工作已经是基线

[OpenAI Agents SDK: Running agents](https://openai.github.io/openai-agents-python/running_agents/)
定义 Agent loop、可序列化 `RunState`，并列出 Dapr、Temporal、Restate、DBOS 等
durable execution 集成；[Human-in-the-loop](https://openai.github.io/openai-agents-python/human_in_the_loop/)
支持工具审批的暂停、保存和恢复。LangGraph 的
[Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) 与
[Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) 通过 checkpointer、
`thread_id` 和 `Command(resume=...)` 保存并恢复图状态。Temporal
[官方文档](https://docs.temporal.io/) 以持久 Workflow、Activity、retry、signal、timer
处理长流程和故障恢复。

因此，“我们能暂停/恢复”不能单独作为差异。办公产品必须继续回答：恢复的是哪条业务
分支，旧成果是否保留，来源是否仍有效，恢复是否会重复模型调用或外部副作用。

### 4.2 并行 Agent 与任务看板也已经是基线

[Codex App](https://openai.com/index/introducing-the-codex-app/) 提供多线程、并行任务、
worktree 隔离和结果审查。[OpenAI Agents SDK: Agent orchestration](https://openai.github.io/openai-agents-python/multi_agent/)
区分 manager 式 `agents as tools`、handoff 和代码编排。Claude Code
[Agent teams](https://code.claude.com/docs/en/agent-teams) 提供 lead、独立 teammate、
共享任务列表和消息，并明确实验状态、协调开销和高 Token 成本。

Anthropic 的工程文章
[How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
报告其内部研究评测的提升，同时说明多 Agent 在其数据中约使用聊天 15 倍 Token，
且不适合强依赖、难并行任务。该数字只适用于其产品与内部评测，不能外推成本或质量。

OpenClaw 的 [Swarm](https://docs.openclaw.ai/tools/swarm) 已支持显式 fan-out/fan-in、
结构化结果、并发上限、子任务上限和 fail-closed 审批；
[Background tasks](https://docs.openclaw.ai/automation/tasks) 将执行状态与交付状态分开，
[Task Flow](https://docs.openclaw.ai/automation/taskflow) 保存 running/waiting/terminal
流程状态。由此可见，“我们有多个 Agent、进度和任务列表”也不是充分差异。

### 4.3 Agent 互操作与结构化向用户追问正在标准化

[A2A Protocol specification](https://a2a-protocol.org/dev/specification/) 把 Task、Message、
Artifact、streaming/push 和 `input_required` 作为 Agent 互操作对象；关键结果应由
Artifact 表达，而非只存在于瞬时消息中。

MCP 的 [Elicitation](https://modelcontextprotocol.io/specification/draft/client/elicitation)
允许服务器通过结构化表单或 URL 请求用户补充输入，并要求客户端显示请求方、用途、
取消/拒绝与敏感信息边界。该规范仍为 draft，且不规定具体产品 UI。

这说明未来的人机交互会从“用户主动发一条 Prompt”扩展为运行中的结构化决策请求。
本项目的 `DecisionRequest`、Branch 选择和预算扩容应映射为清晰的业务问题，而不是
把协议字段直接倾倒给用户。

### 4.4 人机交互研究要求能力边界、纠错与主动性控制

Microsoft Research 的 CHI 2019 论文
[Guidelines for Human-AI Interaction](https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/)
提出 18 条指导，并通过 49 名设计从业者对 20 个 AI 产品的多轮评估验证其适用性。
它支持说明能力边界、当前状态、纠错、后果和全局控制，但不证明本项目的具体 UI 有效。

Horvitz 的
[Principles of mixed-initiative user interfaces](https://doi.org/10.1145/302979.303030)
强调系统主动与直接操控之间的适当平衡。IBM Research 的 IUI 2025 论文
[Controlling AI Agent Participation in Group Conversations](https://research.ibm.com/publications/controlling-ai-agent-participation-in-group-conversations-a-human-centered-approach)
发现参与者不喜欢 Agent 主导群体讨论，并提出针对 Agent 何时、说什么、在哪里说、
由谁控制的交互分类。该研究场景是群体创意讨论，不能直接当作办公驾驶舱用户结论，
但支持“主动性必须可控”的设计假设。

## 5. 与主流方案的可证伪差异候选

以下措辞有意不用“竞品做不到”。公开资料未描述某项能力，不能推断产品绝对没有；
本项目只能声明自身要提供的原生合同，并通过同场任务验证。

### 5.1 差异一：Task lineage，而不是只有 session/run continuation

主流方案通常以 session、thread、run、workflow 或 task record 保存执行上下文。本项目
拟把办公业务任务设为高于 Run 的稳定对象：

- `task_id` 不随预算停止、应用重启或新 Run 改变；
- 后继 Run 必须声明 `parent_run_id`、继承 Branch、基线 `ArtifactVersion/TaskCommit`、
  冻结来源 revision 和需要重核的事实；
- 旧 Run 和旧成果不可变；新事实只能形成新版本和新提交；
- 前台将“继续任务”与“重试一次 Run”分开，明确本次继承与重核范围。

可证伪标准：若后继 Run 不能证明旧成果未改、来源 revision 受检、未选分支未被重跑，
就不能宣称 Task 连续性成立。

### 5.2 差异二：Topology Admission，而不是按用户措辞或模型偏好扩容

多 Agent 的默认诱惑是“复杂就多开”。本项目拟把路线选择交给服务端准入策略，输入
只使用可审计结构事实：

- 来源数量和目录跨度；
- 工作包能否独立、依赖是否强耦合；
- 可用模型调用、时间和文件预算；
- 读写/外部动作风险；
- 是否存在可验证的预期收益依据。

首个纵切只允许 `single_controller`、`fixed_workflow`、
`adaptive_readonly_workers`。目标中的 `direct_tool` 在通用 Tool Gateway 出现前必须
显示“当前不可用”，不能由前台动画冒充。

可证伪标准：相同冻结合同必须给出稳定路线和理由；低并行、强依赖或预算不足任务
不得启动 Worker。无法证明收益时显示“预期收益未知”，而不是伪造节省时间或质量分。

### 5.3 差异三：Worker contribution 先过服务端事实门，再进入共享成果

Worker 的返回只是一份候选，不是共同结论。每份候选至少绑定：

- `work_unit_id`、`branch_id`、approved `file_ref`；
- 服务端解析的 Evidence Anchor；
- Worker 实际调用、返回与采用回执；
- 与确定性 Artifact/Effect 的适用对账；
- 合并状态与拒绝原因。

只有服务端 Gate 通过的贡献可以进入新的 `ArtifactVersion`。合并顺序由稳定规则决定，
不能让最后返回或文字更自信的 Worker 覆盖服务端事实。

可证伪标准：注入无来源、重复 quote、过期 revision、错误算术或与确定性成果冲突的
Worker 候选，均不得进入当前成果；其失败必须局部化并保留已采用贡献。

### 5.4 差异四：一个业务驾驶舱，而不是多个 Agent 聊天室

用户不需要阅读每个 Worker 的完整对话。前台的一等对象是：

- 今日/本次任务优先级；
- 路线建议、理由与预算；
- 工作包、依赖、等待原因和实际 Worker 回执；
- 统一成果、冲突、待确认项和版本历史。

Prompt、CoT、原始 Provider response、内部路径和内部验证字符串继续隐藏。用户可在
必要时展开贡献摘要与证据，但不承担 Agent 之间搬运上下文的工作。

可证伪标准：目标用户能否在不打开 Worker 会话的情况下判断“为什么分工、哪一项
失败、成果是否受影响、下一步会改变什么”，必须通过形成性用户测试，而不是截图自证。

## 6. 技术差异如何逐步改变用户流程

| 技术变化 | 旧流程 | 新流程 | 前台必须输出 | 后端权威事实 |
| --- | --- | --- | --- | --- |
| 跨 Run `task_id` | Run 停止后重新输入背景 | 在同一任务下创建后继 Run | 继承内容、需重核内容、旧成果链接 | Task lineage、parent Run、source revision、base commit |
| 分支级继承 | 整体重跑或整体复制 | 只带入未完成/受影响分支 | “继续哪条工作线”与未选分支状态 | carried Branch IDs、recheck reasons |
| 路线准入 | 用户要求或模型自行多开 | 服务端建议路径，用户确认高成本路线 | 路线理由、预算、风险、收益未知项 | Admission receipt、policy version、expected version |
| 受限 Worker | 多个回复并列 | 独立工作包并发、服务端统一收敛 | 工作包、依赖、实际开始/完成/采用 | WorkUnit、Worker receipt、ordered events |
| 贡献采用门 | 生成即显示 | Anchor/验证/对账通过后才采用 | 已采用、未采用、阻塞影响 | Contribution status、Evidence Gate、reconciliation |
| 不可变合并 | 合成文本覆盖旧结果 | 新 ArtifactVersion + 新 TaskCommit | v1/v2、当前指针、恢复说明 | append-only Artifact/Commit |
| 主动性控制 | Agent 随时打断或沉默 | 仅证据缺口、冲突、预算和高风险点请求人 | 为什么现在需要我、选择后果、稍后处理 | DecisionRequest、deadline、notification policy |

因果链必须完整：例如“启动三个 Worker”本身不是交互价值；只有并行工作包实际启动、
贡献逐项过 Gate、局部失败不清空其他成果，并最终减少用户在多个会话间核对的负担，
才能形成可测试的体验假设。

## 7. 具体办公场景与验收镜头

### 场景 A：跨日财务报告出现正式/预测口径冲突

- 触发：用户要求更新客户经营报告；正式文件为 2400 万，预测文件为 2680 万。
- 用户动作：首次只提交目标；冲突出现后选择“正式口径作为当前值，保留预测差异”。
- Agent 路径：单 Controller 读取安全来源，分解 `customer-facts`、
  `revenue-baseline`、`project-risk`；只有收入基线进入等待。
- 停顿/失败：冲突不能由模型自行消解；用户离开或应用重启后仍保留待决状态。
- 前台输出：已完成分支继续显示成果；冲突卡说明两种口径、来源位置、选择后果；
  继续后只显示收入分支恢复，并生成 v2。
- 后端事实：Branch Evidence Gate、DecisionRequest、expected version、Evidence Anchor、
  append-only ArtifactVersion/TaskCommit；跨 Run 时再绑定 `task_id/parent_run_id`。
- 设计来源：07-16 Demo 1；OpenAI HITL、LangGraph interrupts、Microsoft HAI 指南。
- 当前边界：Run 内局部恢复已存在；跨终态 Run 的稳定 Task lineage 尚未实现。

### 场景 B：12 轮预算到达，但一条工作线仍值得继续

- 触发：整库研究到达当前合同的轮次或模型调用上限，已有两条分支完成、一条未完成。
- 用户动作：查看已完成成果和未完成范围，点击“在同一任务下继续这一工作线”。
- Agent 路径：旧 Run 终态不变；服务端创建后继 Run，只继承指定 Branch、基线成果和
  未过期来源，重新编译新预算合同。
- 停顿/失败：来源 revision 改变时必须先提示重核；旧 expected version 或重复命令
  返回冲突/幂等回执，不得重复创建后继 Run。
- 前台输出：不是“再加几轮”，而是“新一段执行”；显示父 Run、继承 2 项、重核 1 项、
  新预算和旧成果只读链接。
- 后端事实：拟议 `task_id`、Run lineage、carried Branch、base Artifact/Commit、source
  revision、start idempotency。
- 设计来源：Temporal durable workflow、OpenClaw Task Flow、A2A Task lifecycle。
- 当前边界：当前默认 12 轮且可到 24；跨 Run 继承协议尚未实现。

### 场景 C：API 重启后从检查点恢复，而不是重复模型调用

- 触发：Planner 已完成、Analyst 调用尚未完成时 API 进程退出。
- 用户动作：重新打开任务，先查看恢复说明，再决定继续或结束并保留成果。
- Agent 路径：PostgreSQL 恢复已提交轮次、Branch、Artifact 和 Decision；未完成调用
  不自动重放，等待用户确认后从安全边界继续。
- 停顿/失败：memory 模式必须明确“本轮不可恢复”；多实例并发仍不受支持。
- 前台输出：显示“已恢复到哪个检查点、哪些不会自动重放、哪些成果已保留”。
- 后端事实：Snapshot、ordered events、`checkpoint_recovered`、task store health、
  idempotency receipts。
- 设计来源：OpenAI durable integrations、LangGraph persistence、Temporal。
- 当前边界：单 PostgreSQL 顺序恢复已有实现；跨 Run Task lineage 和多实例 lease 未实现。

### 场景 D：三期财务明细不应因为文件多就启动 Swarm

- 触发：用户要求核对三期明细，生成未付统计、未收统计和跨期说明。
- 用户动作：确认目标与来源范围，查看系统路线建议。
- Agent 路径：三份同结构来源需要顺序合并和统一确定性规则，依赖耦合较强；Admission
  推荐 `fixed_workflow`，而非多 Worker。
- 停顿/失败：任一期来源完整性失败则 fail closed；候选为 0 也可合法通过，不用为
  “看起来有成果”制造异常。
- 前台输出：说明“为什么没有启动多个 Agent”：同一口径、顺序依赖、固定检查更可靠；
  显示实际三个成果各自代表什么以及确定性检查回执。
- 后端事实：TopologyAdmission、固定适配器、EffectReceipt、Artifact checks、
  narrative reconciliation。
- 设计来源：Anthropic 多 Agent 适用边界、Claude teams 协调开销、当前 TC-05 实践。
- 当前边界：固定财务纵切已有；通用 Admission receipt 尚未实现。

### 场景 E：跨部门上线核验适合受限并行 Worker

- 触发：用户要求汇总产品、法务、运营、质量和发布材料，形成上线准备简报；来源跨多个
  目录，五个检查包相对独立，最终需要统一冲突和缺口。
- 用户动作：查看系统推荐的 `adaptive_readonly_workers`、工作包和预算，明确确认启动。
- Agent 路径：服务端生成最多三个并发只读 Worker，分别处理批准来源；完成后把候选
  贡献交给 Evidence Gate 和合并器，最后生成统一 ArtifactVersion。
- 停顿/失败：若工作包依赖未满足则不启动；预算不足时降级为固定流程；高风险外部动作
  只形成提案，不执行。
- 前台输出：一张驾驶舱显示 5 个工作包、依赖、当前状态、实际 Worker 数、采用/未采用
  贡献和统一结果，不打开五个聊天室。
- 后端事实：TopologyAdmission、WorkUnit DAG、Worker receipts、Contribution、
  ordered events、deterministic merge、ArtifactVersion/TaskCommit。
- 设计来源：OpenAI orchestration、Anthropic multi-agent research、Claude agent teams、
  OpenClaw Swarm、A2A Artifact。
- 当前边界：这是目标纵切；当前 main 没有通用多 Worker Runtime。

### 场景 F：一个 Worker 引用歧义，其他成果不能被清空

- 触发：三个 Worker 中一个引用文本在文件中出现三次，Runtime 只能得到 ambiguous
  Evidence Candidate；另外两个 Worker 已产生唯一 Anchor。
- 用户动作：只在问题卡中选择该 Worker 对应的原文位置，或选择稍后处理。
- Agent 路径：两个已通过贡献先形成 v1；歧义贡献绑定单一 Branch/WorkUnit 等待；
  用户选择后只恢复该单元，重算 revision 与 candidate，形成 v2。
- 停顿/失败：篡改 candidate、来源 revision 变化或错误 expected version 必须拒绝；
  不得重跑已完成 Worker。
- 前台输出：明确“已有 2 项可用，1 项待确认；当前成果可下载但仍需复核”；展示问题
  对统一结果的影响，而不是泛化成“任务失败”。
- 后端事实：DecisionRequest、EvidenceResolution、affected Branch/WorkUnit、
  branch resume event、append-only v1/v2。
- 设计来源：当前 DR-0032 的局部恢复协议、OpenAI HITL、MCP Elicitation。
- 当前边界：单 Controller Branch 的歧义恢复已有；Worker 贡献级恢复尚未实现。

### 场景 G：低价值单文件查证必须拒绝多 Worker 请求

- 触发：用户在 Prompt 中写“请让五个 Agent 并行检查这一行合同日期”，但来源只有一份
  且完成条件确定。
- 用户动作：无需二次确认，接受系统降级建议；如坚持扩容，只能看到不可执行原因。
- Agent 路径：Admission 选择 `single_controller`，记录强依赖、低并行度与预算浪费理由。
- 停顿/失败：不能因为用户提到“Swarm”就绕过服务端上限；不能伪造节省时间。
- 前台输出：一句业务化解释和预计路径，不展示内部评分；结果仍走来源与 Anchor 核对。
- 后端事实：policy version、route、reason codes、no worker-spawn receipt。
- 设计来源：Anthropic 多 Agent 成本/适用性说明、Claude agent teams 文档。
- 当前边界：通用 Admission 未实现；该场景将作为负向验收。

### 场景 H：用户调低主动性，只在真正阻塞时被打断

- 触发：长任务有多次进度变化，但只有一处来源冲突和一次预算扩容需要人决定。
- 用户动作：选择“仅关键决定通知”，稍后处理普通进度；必要时全局暂停。
- Agent 路径：普通事件进入 Trace/摘要；只有 DecisionRequest、预算、完整性失败和高风险
  Gate 触发前台待办；用户选择后从相应分支继续。
- 停顿/失败：通知设置不能改变服务端安全门；拒绝或超时必须保留等待状态。
- 前台输出：通知频率、为什么现在需要我、可延后与不可延后的区别、选择后果。
- 后端事实：notification policy、DecisionRequest state、deadline、pause/stop receipt。
- 设计来源：Microsoft HAI 指南、Horvitz mixed-initiative、IBM IUI 2025。
- 当前边界：当前有 pause/stop/decision；可调主动性和用户研究尚未实现。

## 8. 会改变用户与 AI 交互方式的技术方向

### 8.1 从 Prompt 输入转向 Task Contract 与例外监督

用户仍以自然语言表达目标，但系统应把范围、完成条件、预算、外部动作和人工门冻结
成服务端合同。用户的主要工作从反复重写 Prompt，转为处理少量证据缺口、冲突、
预算和高风险例外。

### 8.2 从连续聊天转向 Artifact-first 协作

对长任务和多 Worker，Message 用于沟通，Artifact 才是可提交结果。当前项目继续把
Finding、Evidence Anchor、ArtifactVersion、TaskCommit 和确定性回执作为主对象，
而不是让“最后一条回答”覆盖历史。

### 8.3 从静态单 Agent 转向动态但可解释的执行拓扑

Agent 数量不是固定产品配置，而是服务端基于合同选择的成本决策。UI 需要解释路线
和实际采用效果，而不是只显示模型头像或“Swarm 已启动”动画。

### 8.4 从全程确认转向关键检查点确认

逐工具点击会让用户疲劳，完全自治又会隐藏错误。更合理的是让系统在来源冲突、证据
歧义、预算扩容、成果合并冲突和外部动作前停下，同时允许用户调整通知与主动性。

### 8.5 从“Agent 声称完成”转向执行、采用和业务效果三层回执

当前 `called/output_used/elapsed_ms` 已分离。Demo 2 还要继续区分：

- Worker 是否实际启动并返回；
- Worker 候选是否通过服务端 Gate 并进入成果；
- 多 Worker 是否真的带来速度、覆盖或质量收益。

第三层在没有同场基线和用户研究前一律标“未知”，不能用前两层代替。

## 9. 开发顺序与可证伪门

### 第一阶段：Demo 1 Task lineage

1. 在现有八模块内扩展稳定 Task 身份、Run lineage、继承范围和来源重核回执。
2. 后继 Run 只能由终态/预算停止的旧 Run 创建；旧 Run、Artifact、Commit 不变。
3. 先覆盖单分支继承、来源变化、重复 start、PostgreSQL 重启和 SSE 对账。
4. 前台只增加“在同一任务下继续”与继承说明，不引入无限预算措辞。

通过门：跨 Run 的任务、分支、来源、成果和幂等测试均通过，1440/390 px 能清楚说明
继承与重核范围；真实 PostgreSQL 重启后结果一致。

### 第二阶段：Demo 2 Topology Admission

1. 先实现只读、确定性、服务端拥有的 Admission receipt，不先实现自治增兵。
2. 相同合同得到稳定路线；`direct_tool` 在 Tool Gateway 前明确 unavailable。
3. 用户只对高成本 `adaptive_readonly_workers` 作显式确认。
4. 负向测试覆盖低并行、强依赖、预算不足、外部动作和收益未知。

通过门：路线理由来自冻结服务端事实，前台不泄露内部评分，也不把“推荐”写成“执行”。

### 第三阶段：受限 Worker 与服务端收敛

1. 最多三个只读 Worker，只处理服务端批准的 Branch/WorkUnit 和文件范围。
2. 每个贡献必须过 Anchor/Evidence Gate/适用的 narrative reconciliation。
3. 合并稳定、append-only；单 Worker 失败不清空已采用贡献。
4. named SSE、Snapshot、PostgreSQL、断线恢复和幂等控制保持单调一致。

通过门：注入延迟、失败、歧义、stale、篡改与模型矛盾后，只有目标工作包受影响，
旧成果与未受影响贡献保持不变。

## 10. 用户研究与效果验证计划

自动化只能证明协议和被测 UI，不证明体验改善。形成性测试至少比较：

1. 单 Run 重新开始 vs. Task lineage 继续：用户是否能正确说出继承了什么、重核了什么。
2. 多聊天窗口 vs. 统一驾驶舱：用户是否能定位失败工作包和判断成果受影响范围。
3. 无路线解释 vs. Admission receipt：用户是否能区分推荐、实际执行和收益未知。
4. 全量通知 vs. 关键检查点通知：中断次数、漏处理决定和主观控制感如何变化。

建议指标：任务状态理解正确率、证据回开成功率、错误恢复步数、被打断次数、过度信任
比例、完成时间和主观控制感。样本、招募、任务和统计计划未形成前，所有体验结论保持
`Draft`。

## 11. Claim Ledger

| 判断 | 状态 | 依据 | 边界 |
| --- | --- | --- | --- |
| 当前默认最多 12 轮、上限 24 | `Current` | 当前 contract/source | 不等于适合无限长任务 |
| 当前有 Run 内 Branch、Evidence Gate、Artifact/Commit、可选 PG 恢复 | `Current` | 当前源码与 living docs | 不等于跨 Run Task lineage |
| 持久状态、暂停和并行 Agent 已是主流能力 | `Research-supported` | OpenAI、LangGraph、Temporal、Codex、Claude、OpenClaw 官方资料 | 不是竞品同场实测 |
| Task lineage + contribution adoption 是候选差异 | `Proposed` | 07-16、现有协议、上述空白分析 | 尚未工程验证或用户验证 |
| Admission 可减少无意义多 Worker | `Hypothesis` | 多 Agent 成本/适用性资料 | 尚无本项目成本或质量实验 |
| 统一驾驶舱比多聊天更清晰 | `Draft` | HAI/mixed-initiative 研究与产品假设 | 必须做目标用户研究 |

## 12. 研究局限

- 竞品资料主要是官方文档、工程文章和产品公告，不是同一办公数据、同一模型、同一预算
  下的功能实测。
- 公开资料未提及某项能力，不代表竞品不能通过扩展实现；本文只比较公开产品重心与
  本项目拟建立的原生合同。
- Anthropic 的 Token 和内部评测数字、IBM 群聊研究、Microsoft 通用指导均不能直接
  外推到本项目目标用户。
- 本文是研发输入。只有完成源码、PostgreSQL、Provider、浏览器、负向测试和 Evidence
  后，相应能力才能从 `Proposed` 升级；只有完成用户研究，体验判断才能升级。
