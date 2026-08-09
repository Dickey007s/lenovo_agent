# Loop、Swarm 与统一 Agent Runtime 目标架构

本文整理本地最终汇报、讲稿和最新评审反馈中的有效技术方向，作为 V0.1 之后的目标架构输入。它不是当前能力清单，不改变现有 API、Pydantic 协议、Risk/Policy 规则、Permit、Gateway 或 Simulator 边界。

当前实现事实仍以源码、`README.md`、`ARCHITECTURE.md`、`WORKSPACE_AND_STREAMING.md` 和 `GOVERNANCE_AND_ACTIONS.md` 为准。本文出现的 Task Contract、长期任务分支、跨端控制、动态 Worker、Shared Artifact Workspace 和 Conflict Resolver 均为尚未完成的目标能力。

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
| Task Contract | 定义 Task ID、目标、边界、交付物、来源范围和完成条件 | `ActionCandidate`、`ProposedActionSpec` 可表达单次动作 | 缺少长期任务契约、交付物清单和完成条件协议 |
| Durable Task State | 保存事件、分支、版本、控制事件和中间工件 | Run、Workspace、Audit 与 LangGraph checkpoint 可持久化 | 缺少统一长期任务/分支状态；Thread/Message 仍在内存 |
| Context State Manager | 按步骤、权限和版本组装最小上下文投影 | `trusted_context`、`workspace_context` 和来源引用 | 缺少按步骤的上下文投影、版本污染控制和预算策略 |
| Execution Loop | Observe → Plan → Act → Verify → Commit | LangGraph 已用于治理 Gate | 尚无可后台持续运行的长期任务循环 |
| Capability Runtime | 统一模型、工具、Connector、沙箱和临时 Worker 调度 | Tool Gateway 和 5 个 Simulator capability | 缺少真实 Connector、通用沙箱、资源预算和 Worker 生命周期 |
| Evidence & Quality Verifier | 校验来源、一致性、覆盖度、质量与工件冲突 | Mock Evidence Resolver 和确定性证据目录 | 尚无跨工件质量验证、冲突解析和重新验证 |
| Control Policy | 决定继续、暂停分支、重规划、降级、接管或停止 | Risk/Policy/ControlPlan 已覆盖业务动作 | 缺少任务预算、停止条件和分支级控制事件 |
| Trace & Checkpoints | 记录状态提交、工具、证据、版本、控制和恢复点 | Audit SSE、Trace API、Postgres checkpoint | 缺少长期任务统一 Trace、工件版本和恢复 UI |

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

这不是当前 V0.1 的跨端能力。实现前必须完成 Task Contract、分支状态、控制事件、幂等恢复和设备身份设计。

### Demo 2：智能工作驾驶舱

驾驶舱聚合任务、解释排序并允许用户调序。每项任务根据复杂度进入 Tool Call、Single Agent、Fixed Workflow 或 Adaptive Swarm。Swarm 只处理通过 Admission 的复杂任务，完成后把状态、待确认事项和统一工件包返回驾驶舱。

驾驶舱是用户入口，Swarm 是后台执行方式。前端不应把 Worker 数量或对话轮次当作价值指标，而应展示任务状态、来源、冲突、预算和需要用户决定的节点。

### Demo 3：真实动作 Risk Gate

Demo 3 复用当前工作区、非模态确认卡和确定性治理链。目标架构不得用演示稿中的颜色或文案替换当前风险算法：

- 普通风险累计最高为 L4；
- L5 只由受限 capability、受限执行或凭据公开等硬条件触发；
- Risk、Policy、Evidence、Approval、Permit 和执行结果全部由服务端确定性逻辑产生；
- 当前执行结果仍全部来自 Simulator。

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

1. 定义 Task Contract、Task/Branch State、Artifact Version 和 Control Event 协议。
2. 在现有 PostgreSQL/Checkpoint 基础上实现长期任务持久化和幂等恢复。
3. 建立单任务 Observe/Plan/Act/Verify/Commit 循环，不先引入 Swarm。
4. 接入任务级预算、停止、Steer、Pause branch 和 Take over，并补审计测试。
5. 实现 Shared Artifact Workspace 与独立 Verifier/Conflict Resolver。
6. 用离线基准验证 Admission 后，再引入动态 Worker 和 Control Plane。
7. 最后扩展前端驾驶舱、分支控制和跨端体验，并保持当前动作治理不变量。

每一步都必须保留当前稳定行为，并通过局部协议和回归测试接入；不得为了展示 Loop 或 Swarm 而绕过现有安全链。
