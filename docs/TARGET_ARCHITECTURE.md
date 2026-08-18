# Loop、Swarm 与统一 Agent Runtime 目标架构

本文整理本地最终汇报、讲稿和最新评审反馈中的有效技术方向，作为 V0.1 之后的目标架构输入。它不是当前能力清单，不改变现有 API、Pydantic 协议、Risk/Policy 规则、Permit、Gateway 或 Simulator 边界。

最终原始参考集及“下一步重点”逐条覆盖矩阵见 [`docs/final-reference/`](final-reference/README.md)。

当前实现事实仍以源码、`README.md`、`ARCHITECTURE.md`、`WORKSPACE_AND_STREAMING.md` 和 `GOVERNANCE_AND_ACTIONS.md` 为准。固定 Demo 1 已落地 Task Contract、服务端 Task/Branch Snapshot、只读 Artifact Workspace、局部 Conflict、控制状态机、Commit 和顺序 API 进程恢复；DR-0007 又落地了已验证客户回复到治理 Run 的窄桥。真正后台持续的 Loop、跨端身份、动态 Worker、通用 Shared Artifact Workspace/Conflict Resolver 和真实 Connector 仍是目标能力。

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

## 3. 八个常驻 Runtime 组件

| 组件 | 目标职责 | 当前仓库基础 | 主要缺口 |
| --- | --- | --- | --- |
| Task Contract | 定义 Task ID、目标、边界、交付物、来源范围和完成条件 | 固定 Demo 1 已有严格 Task Contract、3 项 Deliverable 与完成条件 | 缺少通用契约模板、修改/取消和生产权限语义 |
| Durable Task State | 保存事件、分支、版本、控制事件和中间工件 | 固定 Task Snapshot/Event/ArtifactVersion 已支持 PostgreSQL 顺序 API 进程恢复；Run、Workspace、Audit 与 checkpoint 可持久化 | 缺少通用长期执行状态、数据库故障/多实例证据；Thread/Message 仍在内存 |
| Context State Manager | 按步骤、权限和版本组装最小上下文投影 | `trusted_context`、`workspace_context` 和来源引用 | 缺少按步骤的上下文投影、版本污染控制和预算策略 |
| Execution Loop | Observe → Plan → Act → Verify → Commit | LangGraph 已用于治理 Gate | 尚无可后台持续运行的长期任务循环 |
| Capability Runtime | 统一模型、工具、Connector、沙箱和临时 Worker 调度 | Tool Gateway 和 5 个 Simulator capability | 缺少真实 Connector、通用沙箱、资源预算和 Worker 生命周期 |
| Evidence & Quality Verifier | 校验来源、一致性、覆盖度、质量与工件冲突 | 固定 Fixture 已有 VerificationReport、局部 Conflict 与重验证；业务动作有 Evidence Resolver | 缺少通用跨工件质量规则、真实来源解析和可扩展冲突策略 |
| Control Policy | 决定继续、暂停分支、重规划、降级、接管或停止 | Risk/Policy/ControlPlan 已覆盖业务动作；固定 Task 有 Steer/Pause/Take over 状态机与预算门 | 缺少 Steer 实际重规划、通用停止/降级和跨分支调度 |
| Trace & Checkpoints | 记录状态提交、工具、证据、版本、控制和恢复点 | TaskEvent/ArtifactVersion/Commit、Audit SSE、Trace API、Postgres checkpoint | 缺少中间阶段可见 checkpoint、统一恢复 UI 和跨域 Trace 视图 |

这张表是实施边界，不是完成度宣传。扩展时应复用当前成熟的动作治理链路，而不是另建一套可绕过 RunService 的授权系统。

## 4. Agent Control Loop

目标循环包含五个可审计阶段：

1. **Observe**：读取事件、状态、来源和环境反馈。
2. **Plan**：根据 Task Contract 生成分支、依赖、预算与完成条件。
3. **Act**：通过 Capability Runtime 调用能力并提交候选中间工件。
4. **Verify**：核对来源、一致性、质量、风险和完成条件。
5. **Commit**：只把验证通过的状态、工件与 Trace 写入 Durable Task State。

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

用户可以查看固定队列中的路由解释，并将客户 A 的路由选择限定为“仅本次生效”；拖拽调序和长期排序偏好留待后续。复杂任务打开 Admission 时展示 Value、Breadth、Parallelism、Deadline、Risk、Budget 六类依据。Adaptive Swarm 在本纵切只能处于“推荐”或“本次已选择”，其 `execution_status` 必须保持 `not_started`；没有真实 Worker、Connector、计费或端到端运行证据，不得显示已启动、运行中、已完成或节省成本。

当前已实现 `WorkCockpitSnapshot`、四项固定演示工作、三项轻量固定路由、客户 A 三种允许模式、版本/幂等路由选择与驾驶舱前台。成本与时效只允许以 `route_profiles[].forecast.source_type=fixture_policy_forecast` 出现，表示演示策略预测，不是实际账单、实测耗时或生产 SLA。具体场景、事实映射、工程证据和边界见 [`DR-0008`](decisions/DR-0008-demo2-explainable-admission.md)、[`SCENARIO-002`](scenarios/SCENARIO-002-demo2-explainable-admission.md) 和 [`Demo 2 PR-1 Evidence`](evidence/DEMO2-PR1-EXPLAINABLE-ADMISSION-EVIDENCE-20260817.md)。

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

`DR-0008` 是在真实 Swarm 之前的产品/协议验证纵切，不改变上述实施顺序：当前只把单进程 memory 驾驶舱、Admission 解释和受限选择标为限定范围 `Verified`；动态 Worker、共享工件、执行循环、Verifier/Resolver、持久恢复和用户价值仍是尚未完成的目标能力，不进入当前完成清单。

每一步都必须保留当前稳定行为，并通过局部协议和回归测试接入；不得为了展示 Loop 或 Swarm 而绕过现有安全链。
