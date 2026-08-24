# Loop、Swarm 与统一 Agent Runtime 目标架构

本文整理本地最终汇报、讲稿和最新评审反馈中的有效技术方向，作为 V0.1 之后的目标架构输入。它不是当前能力清单，不改变现有 API、Pydantic 协议、Risk/Policy 规则、Permit、Gateway 或 Simulator 边界。

最终原始参考集及“下一步重点”逐条覆盖矩阵见 [`docs/final-reference/`](final-reference/README.md)。

当前实现事实仍以源码、`README.md`、`ARCHITECTURE.md`、`WORKSPACE_AND_STREAMING.md` 和 `GOVERNANCE_AND_ACTIONS.md` 为准。固定 Demo 1 已落地 Task Contract、服务端 Task/Branch Snapshot、只读 Artifact Workspace、局部 Conflict、控制状态机、Commit 和顺序 API 进程恢复；DR-0007 落地已验证客户回复到治理 Run 的窄桥；DR-0015 又在固定客户 A、单 API 进程 memory 内落地受控模型 Worker、SharedArtifactVersion、固定事实冲突重排和无外部副作用回执。DR-0016 正在把三套固定体验收敛到 FORTE Workspace + 统一 Harness；当前第一纵切仅覆盖来源目录、内部 Planner、确定性计划校验和 `ready_to_execute`，三 Demo 执行迁移仍为 Draft。真正后台持续的 Loop、跨端身份、通用动态 Worker/Conflict Resolver 和真实 Connector 仍是目标能力。

## 1. 需要解决的问题

目标架构把 Office Agent 从一次对话或一次动作，扩展为可持续推进、可动态组织、可受控执行的工作系统，重点处理三类问题：

1. 长任务运行时间变长后，目标可能漂移、状态可能丢失、未经验证的事实可能在后续步骤被放大。
2. 复杂任务需要并行处理时，固定角色和纯对话式交接难以统一事实、版本、成本和停止条件。
3. Agent 具备真实动作能力后，任务进度不能绕过当前的证据、审批、授权和 Gateway 安全边界。

产品目标不是让更多任务静默自动化，而是让工作在 Task Contract、证据、预算、权限和用户控制下持续收敛，并形成可验证交付。

## 2. 一个底座、两层增强、三类控制

### 2.1 一个底座

统一 Agent Runtime 承载任务、状态、上下文、执行、工具、验证、策略和追踪。底座保持小而稳定，复杂能力通过明确接口按需接入。

### 2.2 两层增强

- **Agent Control Loop**：面向长期任务，使用持久状态、证据门、预算与停止条件，让同一 Task ID 可暂停、恢复、纠偏和接管。
- **Governed Adaptive Swarm**：面向高价值、高广度且可并行的复杂任务，在 Admission 通过后动态生成 Worker，并通过共享工件、验证器和控制面收敛结果。

### 2.3 三类控制

- **任务控制**：Steer、Pause branch、Take over。
- **证据控制**：Evidence Gate、Verifier、Conflict Resolver。
- **业务动作控制**：沿用当前 Risk、Policy、Evidence、Approval、Permit 和 Tool Gateway 链路。

## 3. 八个统一常驻 Harness 模块

| 组件 | 目标职责 | 当前仓库基础 | 主要缺口 |
| --- | --- | --- | --- |
| Scenario Pack & Workspace Catalog | 固定来源版本，校验 manifest、原字节、路径、hash、大小、链接与解析器，冻结只读 Workspace Snapshot | FORTE commit `345c1ec...`、MIT、11 个原始文件、Catalog 与三个公共办公场景；旧 Demo 1 另有仿真来源包 | 任意企业文件夹、生产 Connector、运行时下载与通用解析器 |
| Task Contract | 绑定目标、交付物、数据边界、允许能力、预算/截止时间和人工 Gate | FORTE 公共场景已有目标/交付物/边界投影；固定 Demo 1 有严格完整契约 | 可编辑通用契约、生产权限、统一预算/截止时间和 Worker 子契约 |
| Planner | 从内部净化任务与 Workspace Index 生成有界 DAG 候选 | DR-0016 首纵切使用 `deepseek-v4-pro` 严格 JSON Planner；模型调用、采纳与校验分开记录 | 规划质量、任意任务泛化、成本/质量对照与模型降级策略 |
| Admission & Plan Validator | 确定性校验路径、工具、副作用、Artifact 元数据、依赖、环、预算与 Human Gate | DR-0016 校验路径/tool/side-effect/Artifact/dependency/cycle/gate；Demo 2 另有固定路由 Admission | 统一资源 Admission、生产策略、预算与质量阈值 |
| Scheduler & Worker Manager | 执行 ready unit，管理 Worker、依赖、并行、暂停、失败和 replan | 固定 Demo 2 有单进程受控 Worker 纵切；DR-0016 首纵切明确不启动 Scheduler/Worker | 三 Demo 迁移、后台队列、跨进程恢复、通用 replan 和 Worker lease |
| Tool Gateway | 统一模型外工具、Connector、沙箱和最小权限调用 | 既有 Tool Gateway + 5 个 Simulator；DR-0016 首纵切只校验 allowlist，不调用工具 | 公共 Workspace 读写工具执行、真实 Connector、凭据代理和资源账本 |
| Artifact Workspace & Verifier | 版本化输出、绑定来源/digest，验证覆盖度/一致性并收敛冲突 | 旧 Demo 有 ArtifactVersion/SharedArtifactVersion/VerificationReport；DR-0016 首纵切只校验 Artifact 声明 | FORTE 三场景执行工件、通用验证器、冲突收敛与最终 Commit |
| Checkpoint, Event & Governance Control | 持久化 Snapshot/事件，承载恢复、分支、Steer、Approval、Permit 与业务回执 | 旧 Task/Audit/Checkpoint 纵切；DR-0016 有单进程 memory Snapshot、Owner、幂等 start 和有序 SSE | Harness 持久化、统一控制协议、跨进程幂等、多实例事件和生产身份 |

这八个名称是 DR-0016 之后的唯一常驻模块清单。旧表中的 Durable Task State、Context State Manager、Execution Loop、Capability Runtime、Evidence & Quality Verifier、Control Policy、Trace & Checkpoints 已分别收敛到 Catalog/Contract、Scheduler、Gateway、Artifact/Verifier 和 Checkpoint/Event/Governance 的职责中，不再作为第二套八模块汇报。该表是实施边界，不是完成度宣传；扩展时应复用当前动作治理链路，而不是另建可绕过 RunService 的授权系统。

## 4. Agent Control Loop

目标循环包含五个可审计阶段：

1. **Observe**：读取事件、状态、来源和环境反馈。
2. **Plan**：根据 Task Contract 生成分支、依赖、预算与完成条件。
3. **Act**：通过 Scheduler & Worker Manager 和 Tool Gateway 调用能力并提交候选中间工件。
4. **Verify**：核对来源、一致性、质量、风险和完成条件。
5. **Commit**：只把 Artifact Workspace & Verifier 通过的状态、工件与 Trace 写入 Checkpoint, Event & Governance Control。

外围控制必须进入每一轮，而不是在最终交付前补一次检查：

- Task Contract 保持方向；
- Evidence Gate 只暂停受影响分支；
- Budget & Stop 限制时间、工具、Worker 和模型消耗；
- Steer、Pause branch、Take over 保留用户控制权；
- 涉及副作用的动作继续走当前 RunService 与 Tool Gateway。

恢复语义必须以持久化状态和幂等操作为基础。前端不能用“继续任务”按钮伪造后台持续运行，也不能把视觉进度当作已提交事实。

## 5. Governed Adaptive Swarm

Swarm 是复杂任务的一种执行方式，不是所有任务的默认模式。Admission 应先比较增量收益与协调成本，再把任务路由到 Tool Call、Single Agent、Fixed Workflow 或 Adaptive Swarm。

Admission 至少考虑：

- Value：交付价值与业务影响；
- Breadth：来源广度与专业跨度；
- Parallelism：可独立并行的工作包数量；
- Deadline：截止压力和等待成本；
- Risk：事实冲突、权限与真实动作风险；
- Budget：Worker、工具、时间和模型消耗上限。

通过 Admission 后的目标链路为：

```text
Admission → Supervisor → Dynamic Workers → Shared Artifact Workspace
          → Verifier / Conflict Resolver → Control Plane → 单一结果出口
```

Worker 使用隔离上下文和最小权限；事实、来源、负责人、状态和版本写入共享工件，而不是只在 Agent 对话中转述。Conflict Resolver 的输出必须回写所有受影响工件并重新验证。任何 Worker 都不能直接签发 Permit 或调用未注册的副作用工具。

## 6. 三个目标 Demo

### Demo 1：受控持久任务

同一 Task ID 持续推进经营分析、风险页和回复草稿。Verify 发现某个事实口径冲突时，只暂停受影响分支，其他分支继续生成可核查工件。用户可跨端发出 Steer、Pause branch 或 Take over 控制事件；最终交付包含来源、版本、验证结果和 Trace。

当前 V0.1 已在固定 Fixture 中实现 Task Contract、分支状态、控制事件、工件版本、Commit 和有边界的幂等恢复，但 start 仍是一次同步 mutation，Steer 不会立即重规划，也没有真实跨端身份或后台 Worker。它是目标 Demo 的纵切，不是完整跨端持续运行能力。

### Demo 2：智能工作驾驶舱

驾驶舱聚合任务、解释排序并允许用户调序。每项任务根据复杂度进入 Tool Call、Single Agent、Fixed Workflow 或 Adaptive Swarm。Swarm 只处理通过 Admission 的复杂任务，完成后把状态、待确认事项和统一工件包返回驾驶舱。

驾驶舱是用户入口，Swarm 是后台执行方式。前端不应把 Worker 数量或对话轮次当作价值指标，而应展示任务状态、来源、冲突、预算和需要用户决定的节点。

### 6.1 Demo 2 第一纵切：可解释 Admission（DR-0008，限定范围 Verified）

2026-08-17 的第一纵切先验证用户能否看懂“今天有哪些工作、准备采用什么方式”，不把动态 Worker 作为首屏价值。服务端 `WorkCockpitSnapshot` 固定返回四项演示任务：客户 A 经营汇报、供应商邮件回复、周报格式统一、报销异常核查。后三项分别由 Admission 固定选择 Single Agent、Fixed Workflow、Tool Call；客户 A 保持待决定，并允许 Single Agent、Fixed Workflow、Adaptive Swarm 三种模式。

用户可以查看固定队列中的路由解释，并将客户 A 的路由选择限定为“仅本次生效”；拖拽调序和长期排序偏好留待后续。复杂任务打开 Admission 时展示 Value、Breadth、Parallelism、Deadline、Risk、Budget 六类依据。第一纵切的 route mutation 只能处于“推荐”或“本次已选择”，其 `execution_status` 必须保持 `not_started`；它自身不能显示已启动、运行中、已完成或节省成本。下方第二纵切通过独立命令启动，不改变这个选择/执行分离不变量。

当前已实现 `WorkCockpitSnapshot`、四项固定演示工作、三项轻量固定路由、客户 A 三种允许模式、版本/幂等路由选择与驾驶舱前台。成本与时效只允许以 `route_profiles[].forecast.source_type=fixture_policy_forecast` 出现，表示演示策略预测，不是实际账单、实测耗时或生产 SLA。具体场景、事实映射、工程证据和边界见 [`DR-0008`](decisions/DR-0008-demo2-explainable-admission.md)、[`SCENARIO-002`](scenarios/SCENARIO-002-demo2-explainable-admission.md) 和 [`Demo 2 PR-1 Evidence`](evidence/DEMO2-PR1-EXPLAINABLE-ADMISSION-EVIDENCE-20260817.md)。

### 6.2 Demo 2 第二纵切：受控内部执行（DR-0015，Limited Verified）

2026-08-21 的第二纵切保留“选择不等于执行”，新增独立 execution command。固定客户 A 选择 Adaptive Swarm 后，用户显式启动；服务端创建 `Demo2ExecutionSnapshot`，并行运行收入事实、项目风险、客户要求三个受限模型工作单元。文件中的确认收入/预测收入冲突触发 sequence 9 `DYNAMIC_REPLAN` 和 sequence 10 `WORKER_ADDED`，增派收入口径核验；最终 sequence 15 完成，形成 4 个 Worker、5 个 SharedArtifactVersion 和 `external_side_effect=none` 的回执。

模型固定为 `deepseek-v4-pro`，只生成受限业务摘要和要点；服务端拥有身份、来源、依赖、状态、事件、工件版本/digest、验证和回执。当前 Execution Store/锁/幂等/SSE 均在单 API 进程 memory 内，API 重启无恢复，也没有真实 Connector、生产身份或外部动作。两轮 live 模型和六张截图见 [`DEMO2-CONTROLLED-EXECUTION-20260821`](evidence/DEMO2-CONTROLLED-EXECUTION-EVIDENCE-20260821.md)。这证明固定工程路径，不证明通用 Adaptive Swarm、用户理解或成本/质量改善。

### Demo 3：真实动作 Risk Gate

Demo 3 复用当前工作区、非模态确认卡和确定性治理链。目标架构不得用演示稿中的颜色或文案替换当前风险算法：

- 普通风险累计最高为 L4；
- L5 只由受限 capability、受限执行或凭据公开等硬条件触发；
- Risk、Policy、Evidence、Approval、Permit 和执行结果全部由服务端确定性逻辑产生；
- 当前执行结果仍全部来自 Simulator。

DR-0007 已验证第一条跨 Demo 连接：Demo 1 的 `committed + passed` 客户回复可带 Task/Commit/ArtifactVersion/Verification 绑定进入 Demo 3 `email.send` Gate，并在治理门前重校验。它证明“已核对成果可以作为受控动作输入”，但只支持固定演示地址和 Simulator，不代表通用任务成果或真实企业动作已经接通。

演示稿中的 L0-L5 视觉阶梯是交互叙事，不是新的规范性评分实现。任何映射变更都必须同步 Pydantic 协议、RunService、前端类型、文档和回归测试。

## 7. 与常见方案的设计差异

| 常见起点 | 本目标架构增加的约束 | 对用户交互的影响 |
| --- | --- | --- |
| 一次 Prompt 或一次工具循环 | Task Contract、Durable State、Verify/Commit、恢复点 | 用户看到持续任务、版本和可恢复状态，而不是一串孤立回答 |
| 固定角色多 Agent | Admission、动态 Worker、预算与停止条件 | 只在收益足够时组队，并解释为何进入 Swarm |
| 通过对话传递结果 | Shared Artifact Workspace、来源、负责人和版本 | 用户围绕统一工件审阅，不必追踪 Agent 聊天转述 |
| 最终结果一次性验收 | 每轮 Evidence Gate、Verifier 和冲突回写 | 冲突在受影响分支停靠，其他分支可继续 |
| 前端直接宣布完成 | Verified Commit、Trace、真实工具结果 | 完成状态来自服务端提交与验证事实 |

## 8. 前后端交互对齐

后续原型应优先验证技术变化如何改变用户体验：

- 顶层任务条持续显示 Task ID、目标、阶段、预算和最近 Commit；
- 分支视图区分 running、waiting evidence、paused、failed 和 committed；
- Steer、Pause branch、Take over 都写入服务端控制事件并进入 Trace；
- 驾驶舱解释任务排序和执行方式路由，用户调整可限定为“仅本次”或持久偏好；
- Shared Artifact Workspace 展示来源、版本、冲突和验证状态，不暴露无价值的内部对话；
- Risk Gate 继续位于对话底部非模态 tray，副作用动作逐项确认，不与任务级控制混成一个按钮；
- 所有进度、完成、失败和成本状态均由服务端 Snapshot/SSE 驱动。

前端可降低理解成本，但不能拥有风险判断、分支真值、预算扣减、Permit 或执行成功状态。

### 8.1 决策、交互与来源留痕

后续架构决策、实现推进、PR、Demo 和汇报必须遵守 [`DECISION_AND_REPORTING_GOVERNANCE.md`](DECISION_AND_REPORTING_GOVERNANCE.md)，并同时维护三类可审计记录：

1. **场景与来源记录**：目标用户、触发条件、当前流程或痛点、完成条件、异常路径，以及每项设计判断的精确来源、日期或版本、支持范围和局限。
2. **前台交互记录**：用户可见状态、可用动作、即时反馈、等待与失败恢复、需要隐藏的内部细节，以及对应的可用性或理解度假设。
3. **后端事实映射**：每个 UI 状态对应的服务端实体、字段、版本、`Snapshot` 或 SSE 事件，包含状态转换、权限、幂等和 Trace 语义。

没有场景与来源的方向只能视为假设；没有前台交互影响的技术决策不完整；没有后端事实映射的界面只能视为静态概念；没有测试、Trace 或用户研究证据的结果不能标记为已验证或已完成。

## 9. 设计来源与验证路径

目标架构来自本地场景原型、最终汇报与讲稿，并参考以下一手研究和工程实践：

- [ReAct](https://arxiv.org/abs/2210.03629)：把推理与环境动作交错组织，为 Observe/Act 循环提供研究基础。
- [LangGraph 官方文档](https://docs.langchain.com/oss/python/langgraph/overview)：持久执行、状态、流式与 human-in-the-loop 的运行时实践。
- [OpenAI Swarm](https://github.com/openai/swarm)：用于理解轻量 Agents、handoffs 和客户端编排的教育性框架；不等同于动态组织产品架构。
- [Anthropic 多 Agent Research 系统](https://www.anthropic.com/engineering/multi-agent-research-system)：Orchestrator-Worker 与并行子 Agent 的生产实践。
- [NIST AI RMF 1.0](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10)：持续治理、风险记录和人类监督职责的通用依据。

进一步落地前还需要补三类证据：

1. 与单 Agent、固定 Workflow 和固定多 Agent 的同任务对照实验；
2. 针对长期任务恢复、分支控制、冲突理解和确认负担的用户研究；
3. 质量、时延、成本、越权拦截、恢复成功率和人工接管效果的可重复评测。

## 10. 实施顺序

Demo 1 的实施决策、场景、协议和前台事实映射已经固定在 [`DR-0002`](decisions/DR-0002-bounded-durable-office-loop.md)、[`SCENARIO-001`](scenarios/SCENARIO-001-customer-a-durable-report.md)、[`TASK_RUNTIME_PROTOCOL.md`](contracts/TASK_RUNTIME_PROTOCOL.md) 和 [`UI_SERVER_FACT_MATRIX.md`](contracts/UI_SERVER_FACT_MATRIX.md)。其中固定纵切已有分阶段运行证据；交互是否真正提升理解仍由 `DR-0005` 以 `Draft` 管理。Demo 1 到 Demo 3 的窄桥由 [`DR-0007`](decisions/DR-0007-task-artifact-action-bridge.md) 单独记录，不把一条已验证路径外推为整个目标架构完成。

1. 定义 Task Contract、Task/Branch State、Artifact Version 和 Control Event 协议。
2. 在现有 PostgreSQL/Checkpoint 基础上实现长期任务持久化和幂等恢复。
3. 建立单任务 Observe/Plan/Act/Verify/Commit 循环，不先引入 Swarm。
4. 接入任务级预算、停止、Steer、Pause branch 和 Take over，并补审计测试。
5. 实现 Shared Artifact Workspace 与独立 Verifier/Conflict Resolver；固定只读版本和一条 Task Artifact/Action 绑定已落地，下一步扩展前仍需通用契约与用户研究。
6. 用离线基准验证 Admission 后，再引入动态 Worker 和 Control Plane。
7. 最后扩展前端驾驶舱、分支控制和跨端体验，并保持当前动作治理不变量。

`DR-0008` 是执行前的产品/协议验证纵切；`DR-0015` 进一步把固定客户 A 的受控模型 Worker、共享工件、固定事实冲突增派、验证和无外部副作用回执标为单 API 进程 memory 范围的 `Limited Verified`。通用动态 Worker/Resolver、后台队列、持久恢复、真实 Connector、生产身份和用户价值仍是尚未完成的目标能力，不进入当前完成清单。

每一步都必须保留当前稳定行为，并通过局部协议和回归测试接入；不得为了展示 Loop 或 Swarm 而绕过现有安全链。

## 11. 2026-08 汇报对比补充（Draft）

本节用于汇报准备，不改变当前协议或实现状态。主流方案的能力判断来自 [`COMPETITOR-RESEARCH-OPENCLAW-CODEX-CLAUDE-CODE-20260821`](research/COMPETITOR-RESEARCH-OPENCLAW-CODEX-CLAUDE-CODE-20260821.md) 的官方材料登记；官方材料不是竞品实测，不能据此宣称竞品做不到某项业务能力。

| 维度 | OpenClaw / Codex / Claude Code 的公开主流形态 | Office Agent 目标设计 | 用户交互变化 | 当前状态 |
| --- | --- | --- | --- | --- |
| 执行中心 | Gateway、代码仓库/终端、当前目录和 session | 业务 Task、Branch、Artifact、ControlEvent 成为一等事实 | 用户看“我的哪项业务工作正在推进”，不只看命令或线程 | Draft |
| 多 Agent | 独立 Agent、并行 thread、subagent/background、worktree 或 workspace 隔离 | Admission 后创建有边界 Worker，结果汇入 SharedArtifactVersion | 用户看到业务工作单元、依赖和重排，不用追踪 Agent 对话 | 固定客户 A `Limited Verified`；通用化 Draft |
| 事实与版本 | transcript、diff、worktree、session/task state | 来源文档/字段、版本、digest、验证状态绑定业务工件 | 冲突卡解释旧事实、当前操作和暂停原因 | Demo 1 有限定工程证据；通用 Draft |
| 权限与审批 | 工具策略、sandbox、host approval、permission mode、hooks | Risk/Evidence/Approval/Permit 绑定语义动作、工件版本和目标影响 | 用户确认“会改变什么”，而不是只批准一条命令 | Demo 3 固定路径限定 Verified；通用 Draft |
| 影响反馈 | diff、tool、command、task/session 可观察性 | `impact_preview → execution_receipt` 双时态事实链 | 提交前预演，提交后只显示真实回执；结果未知则待核对 | 各 Demo 固定纵切；跨 Demo Draft |
| 恢复与失败 | session resume、rewind、fork、cron/task state | 源版本变化、证据冲突、未知结果 fail closed，保留草稿/Commit | 用户知道重核什么，不会被旧结果静默覆盖 | Draft |

### 11.1 八模块成熟度和缺口（汇报用）

| 模块 | 已有基础 | 仍需补齐 | 汇报不可夸大 |
| --- | --- | --- | --- |
| Scenario Pack & Workspace Catalog | FORTE 固定 commit/MIT/原字节与只读 Catalog；旧 Demo 1 另有仿真来源校验 | 任意企业文件夹、Connector、通用解析器 | 公开 benchmark 不是生产企业数据 |
| Task Contract | FORTE 三场景安全业务投影；Demo 1 固定完整契约 | 可编辑通用模板、生产权限、预算/截止时间、Worker 子契约 | 不是全业务通用 |
| Planner | DR-0016 严格 JSON Planner 首纵切 | 任意任务质量、对照、降级与成本边界 | 模型被调用不等于输出采用或计划通过 |
| Admission & Plan Validator | DR-0016 路径/工具/副作用/依赖/环/Gate 校验；Demo 2 固定 Admission | 资源/预算/质量统一 Admission | `ready_to_execute` 不等于执行 |
| Scheduler & Worker Manager | 固定 Demo 2 单进程 Worker 纵切 | FORTE 三 Demo 迁移、后台队列、暂停恢复、通用 replan、lease | 固定纵切不等于通用 Swarm |
| Tool Gateway | 5 个 Simulator capability；Harness 计划工具 allowlist | Workspace 工具执行、Connector、沙箱、凭据和资源账本 | 当前 Harness 首纵切未调用任何工具 |
| Artifact Workspace & Verifier | 旧 Demo 的 Artifact/Verification/Conflict 基础 | FORTE 执行工件、跨工件质量规则、通用 Resolver 和 Commit | 首纵切没有生成或验证业务工件 |
| Checkpoint, Event & Governance Control | Task/Audit/Checkpoint 基础；Harness 单进程 Snapshot/Owner/幂等/SSE | Harness 持久化、统一控制、跨进程/多实例与生产身份 | memory 事件不等于生产恢复 |

上述表格是目标设计和缺口清单。除文中明确标为 Verified 的固定纵切，其余均为 Draft/待验证。

## 12. FORTE Workspace + 统一 Harness 第一纵切（DR-0016，Limited Verified）

本轮用公开 FORTE 固定 commit `345c1ec1487139db9dd319787fa9405ba85d1869`、顶层 MIT 和本地 manifest 中 11 个原始文件作为同一 Scenario Pack 来源。三份 raw `task.md` 只作 provenance；Catalog 提取净化 Prompt 供内部 Planner，不向公共 API、SSE 或普通 UI 返回 `task_instruction`、rubric、solution 或 grading 内容。前台默认从“工作现场”进入：左侧是安全来源与文件业务标签，中间是渐进阶段和动态计划，右侧是服务端活动回执。

第一纵切只实现 `Scenario Pack -> Task Contract -> Planner -> Admission & Plan Validator -> ready_to_execute`。模型是否调用、输出是否采用、计划是否通过服务端校验必须分别由 `HarnessModelReceipt.called`、`output_used` 和 Snapshot/Event 证明。`ready_to_execute` 明确表示 Scheduler/Worker、Tool Gateway 执行、Artifact mutation、Verifier Commit、Connector 和外部副作用都没有发生。Finance-018、pm-014、Operations-008 对 Demo 1/2/3 的真实执行迁移仍为 Draft；旧固定 Demo 的事实不能复制成 FORTE 运行事实。

当前 `Limited Verified` 范围绑定三次 `deepseek-v4-pro` live 规划、六张截图、Python `199 passed, 1 skipped in 7.93s`、浏览器 `48 passed (3.6m)`、Ruff/lint/build 通过、实现 `fdcc3d819686b0d0afd99fcd0b637b5329607835`、首份证据文档提交 `265ffb6f1e4f35416b0020deff9becee9a3a26a2` 和 open、未合并 PR #23。精确 Manifest 与边界见 [`FORTE-WORKSPACE-AGENT-HARNESS-EVIDENCE-20260824`](evidence/FORTE-WORKSPACE-AGENT-HARNESS-EVIDENCE-20260824.md)。浏览器 E2E 只作为工程代理，不能替代目标用户理解、信任、效率或任务成功研究。
