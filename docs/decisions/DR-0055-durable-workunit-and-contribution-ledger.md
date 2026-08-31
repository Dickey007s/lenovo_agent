# DR-0055：Branch 绑定的 WorkUnit 与不可变 Contribution 台账

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Draft`；等待源码、Memory/PostgreSQL、浏览器和固定场景门回填 |
| 日期 | 2026-08-31 |
| 用户来源 | `USER-FEEDBACK-20260831-DEMO1-DEMO2-FIXED-SCENARIO-HARDENING` |
| 前置决策 | `DR-0053` 的可解释拓扑准入与受限 Worker；`DR-0054` 的独立 Task Ledger |
| 研究来源 | `MULTI-AGENT-ORCHESTRATION-OFFICIAL-20260830`、`AGENT-INTEROP-AND-ELICITATION-OFFICIAL-20260830`、`HAI-MIXED-INITIATIVE-RESEARCH-20260830` |
| 场景 | [`SCENARIO-041`](../scenarios/SCENARIO-041-workunit-contribution-ledger-and-partial-convergence.md) |
| 测试合同 | [`WORKUNIT-CONTRIBUTION-LEDGER-V1-GATES-20260831`](../testing/WORKUNIT-CONTRIBUTION-LEDGER-V1-GATES-20260831.md) |
| Evidence | 待运行后登记，不能由本文设计推断通过 |

## 问题

`DR-0053` 已经证明服务端可以根据 validated plan 选择 `single_controller`、
`fixed_workflow` 或 `adaptive_readonly_workers`，并在用户确认后启动每波最多三个进程内
只读 Analyst Worker。Worker 的返回和采用已经分开，失败的 Worker 不会清空兄弟分支
已经形成的成果。但当前 `worker_runs` 和 `shared_artifacts` 仍是 Run Snapshot 中的投影，
尚不足以回答四个办公用户真正关心的问题：

1. 页面刷新或服务重启后，哪个工作包已经预留、实际调用、返回、采用或失败？
2. 同一工作包重试时，旧候选是否保留，还是被新回复覆盖？
3. 一个工作包失败时，具体阻塞了谁，为什么其他成果仍然可用？
4. Worker 的文字已经返回，为什么它有时仍不能进入统一成果？

继续增加 Worker 数量不会关闭这些断点。下一纵切应先建立最小可恢复执行台账，把
“任务如何拆分”“Worker 实际做了什么”“哪份候选获准进入成果”分成不同权威对象。

## 研究依据与不当推断边界

[OpenAI Agents SDK: Agent orchestration](https://openai.github.io/openai-agents-python/multi_agent/)
区分 manager、handoff 和代码编排，并指出只有互不依赖的工作才适合并行。
[Anthropic: How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
公开了 orchestrator-worker 方式、工作包边界、协调与 Token 成本，并明确强依赖任务并不
适合当前多 Agent。该文中的性能和约 15 倍聊天 Token 数据仅属于其内部系统与评测，
不能外推为本项目收益。

[A2A Protocol specification](https://a2a-protocol.org/latest/specification/) 把 Task 状态、
Artifact、按序事件和 `input-required` 作为可互操作对象；Artifact 表示任务输出，而不等同
于瞬时消息。[Microsoft Research: Guidelines for Human-AI Interaction](https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/)
要求及时说明系统状态、能力边界、后果，并支持用户纠错和撤回。

这些资料支持“工作状态、返回候选和可采用成果应分开”“并行必须有适用条件”“用户应
看到失败影响和下一步”的设计方向。它们不证明本项目已经达到上述产品的可靠性，也不
证明竞品不能实现同类 Office Evidence 治理。固定自动化和截图也不能代替目标用户研究。

## 决策

### 1. Branch 仍是业务与证据权威

Validated plan 编译出的 `Branch` 继续拥有业务目标、依赖、批准来源和 Evidence Gate。
首版 `work_unit_id` 必须直接复用 `branch_id`，形成一对一关系。WorkUnit 不复制或改写
Branch 目标，也不另建第二张工作分解图。

`WorkUnitRecord` 只记录执行事实：所属 Task/Run、依赖投影、批准来源投影、执行状态、
attempt、版本、预留、最新 Contribution、开始/返回时间和安全错误码。Branch 告诉系统
“这项业务工作是什么、依赖谁、需要哪些证据”；WorkUnit 告诉用户“这次执行走到哪里”。

### 2. WorkUnit 使用服务端状态机

首版状态集合为：

```text
pending -> ready -> reserved -> running -> returned
                                      -> failed
returned -> adopted | waiting | rejected
pending/ready -> blocked
```

- `pending/ready/blocked` 从 Branch DAG 与前置 Gate 事实派生，浏览器不能自行推进。
- `reserved` 必须先于模型调用持久化，绑定 attempt、预算和幂等回执。
- `running` 只表示已开始调用，不表示返回或采用。
- `returned` 表示形成了不可变 Contribution candidate。
- `adopted/waiting/rejected/failed` 分别表示已进入成果、需核对、服务端拒绝、调用失败。
- 服务重启遇到 `reserved/running` 时必须转为可审查失败或需处理状态，不自动重放
  Provider 调用。

### 3. 每次 Worker 返回都追加 Contribution

`ContributionRecord` 是不可变候选，至少绑定：

- 服务端生成的 `contribution_id`、Owner、Task、Run、WorkUnit/Branch、attempt 和
  `worker_run_id`；
- 冻结的 Run/Catalog revision、批准 `source_file_refs`、结构化 Evidence Anchor；
- `model_called/output_used/elapsed_ms` 回执、Gate 结论与安全原因；
- 进入哪个 `ArtifactVersion`，或为什么未进入；
- 创建时间。

重试必须增加 attempt 并新增 Contribution，不能覆盖旧候选。公共投影不得暴露 Owner、
raw hash/digest、绝对路径、Prompt、CoT、raw Provider response 或内部验证表达式。

`ArtifactVersion/TaskCommit` 继续是统一成果权威；`SharedArtifactMerge` 只保留兼容投影。
“最后返回”“文字更长”“Worker 自称已完成”都不能成为覆盖权。

### 4. 三层版本各管一件事

- `task_version` 只保护跨 Run current pointer，不因 Worker 波次增加。
- `run.version` 保护当前 Run 的 Snapshot、预算、事件和波次。
- `work_unit.version` 保护单个 WorkUnit 的预留、返回和采用迁移。
- Contribution 的 attempt 是不可变候选序号，不代替 CAS。

同一幂等键和相同 payload 必须返回原回执；同一键配不同 payload 必须冲突。过期 Run 或
WorkUnit version 必须零状态变化，不能先扣预算、调用模型或追加空候选。

### 5. 原子边界

1. **预留事务**：Run CAS、WorkUnit `ready -> reserved`、attempt、预算、幂等回执和
   `worker_wave_reserved` 一起提交，然后才允许调用 Worker。
2. **返回事务**：每个 Worker 返回后追加 Contribution，更新 WorkUnit，并追加
   `worker_returned/contribution_recorded`；返回本身不等于采用。
3. **收敛事务**：按服务端 `work_unit_id/branch_id` 稳定排序，执行来源、Anchor、
   Evidence Gate 和适用的 deterministic/narrative reconciliation；原子更新 Branch、
   WorkUnit、ArtifactVersion、TaskCommit、Snapshot 和 named SSE。

不得出现“预算已扣但无预留”“Contribution 存在但 WorkUnit 不认识”“Artifact 已更新但
采用状态仍是 returned”或重复请求新增第二个 ArtifactVersion 的中间态。

### 6. 保持现有公开路径

不新增 WorkUnit CRUD 或 Demo 专属 API。`POST /v1/harness/runs/{run_id}/workers` 继续负责
确认和派发；Run GET/Snapshot 增加脱敏 `work_units` 与 `contributions`。Task GET 仍只给
current Run 和 lineage 摘要，不倾倒所有候选。

保留兼容事件：`worker_returned`、`contribution_adopted`、`contribution_waiting`、
`contribution_rejected`、`topology_workers_completed`。新增最小执行事实：
`worker_wave_reserved`、`work_unit_started`、`contribution_recorded`、
`work_unit_failed`、`worker_wave_committed`。Snapshot 是状态权威，SSE 只作按序投影。

### 7. 前台不展示 Worker 聊天墙

现有拓扑卡增加“工作包”和“候选采用记录”：

- 每个工作包显示业务名称、依赖、批准来源、状态、attempt 和失败影响；
- 明确分开“实际返回”与“进入成果”，并给出等待/拒绝的业务化原因；
- Contribution 可回开批准来源和 Anchor，但不能把定位证据说成语义正确；
- 当前统一成果显示 `ArtifactVersion`，部分采用时显示“已有可用成果，仍有工作包待处理”；
- 只把需要人处理的异常提升为行动入口，正常事件留在可展开 Trace。

用户管理的是路线、工作包、例外和统一成果，不需要打开多个 Agent 私聊，也不需要理解
reservation、digest 或内部 validator 字段。

## Demo 1 与 Demo 2 的关系

- Demo 1 的 Task Ledger 解决时间维连续性：旧 Run、旧 Artifact 和 current pointer 不被
  覆盖。
- Demo 2 的 WorkUnit/Contribution Ledger 解决组织维收敛：多个工作包各自留下执行与
  采用记录，局部失败不清空兄弟成果。
- 两者共享 Task/Run/Branch/ArtifactVersion/TaskCommit，不形成两套产品或第九模块。

## 验证门

1. 五单元 DAG 第一波三个 root、第二波两个 dependent；无 orphan/duplicate WorkUnit。
2. 两个 adopted、一个 ambiguous 时，兄弟 Contribution 和已有 Artifact 保留，只有受影响
   下游 blocked。
3. 越 Branch 来源、无 Anchor、重复定位、stale revision、篡改候选和对账冲突不进入
   Artifact，且拒绝记录仍可审计。
4. 三期同结构财务任务保持 `fixed_workflow`，不创建 Worker WorkUnit/Contribution 事件。
5. Owner、Run/WorkUnit version、幂等 replay/冲突和稳定 merge 顺序有负向自动化。
6. Memory 与 PostgreSQL 重启不自动重放 `reserved/running` Worker；无真实 DSN 时明确
   skip，不能把 collect 写成数据库通过。
7. SSE sequence 与最终 GET 可对账；断线恢复不倒序。
8. 1440 px 与 390 px 浏览器显示状态、采用影响和 Anchor 入口，正文 13–14 px、辅助文字
   至少 12 px且无横向溢出。

## 本阶段明确不做

- durable/distributed queue、lease、多实例协调、远端 Worker 或递归 Swarm；
- Worker 专属 pause/cancel/DecisionRequest/control API；
- 真实 Provider、Tool Gateway、Connector、外部动作或源文件写回；
- 通用 ConflictRecord、通用语义/数值 Verifier 或生产身份；
- 多 Worker 更快、更便宜、更正确，或前台理解/信任已经提升的结论。

因此，即使本决策的自动化全部通过，也只能把 Branch 绑定的只读进程内 Worker 台账标为
`Limited Verified`，不能称为完整 Scheduler/Worker Runtime 或生产 Adaptive Swarm。
