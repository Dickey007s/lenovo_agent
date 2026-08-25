# DR-0023：先实现 Agent Control Loop 的三轮只读纵切

> 生命周期说明：本决策定义的通用只读 Control Loop 继续有效；`memory`、自动
> `next_round` 和无成果版本的历史限制已由 [`DR-0025`](DR-0025-durable-evidence-gate-and-artifact-evolution.md)
> 更新。本文数字和 Evidence 仍只描述当时实现。

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`；仅限 FORTE 公开输入、单 API 进程 memory、最多三轮的只读纵切 |
| 日期 | 2026-08-25 |
| 触发来源 | `USER-FEEDBACK-20260825-CONTROL-LOOP-16`、`USER-FEEDBACK-20260825-CONTROL-LOOP-NAMING-17` |
| 研究审计 | [`AGENT-CONTROL-LOOP-IMPLEMENTATION-AUDIT-20260825`](../research/AGENT-CONTROL-LOOP-IMPLEMENTATION-AUDIT-20260825.md) |
| 场景 | [`SCENARIO-009`](../scenarios/SCENARIO-009-agent-control-loop.md) |
| Evidence | [`AGENT-CONTROL-LOOP-BOUNDED-READONLY-20260825`](../evidence/AGENT-CONTROL-LOOP-BOUNDED-READONLY-EVIDENCE-20260825.md)；实现 `8364b1e`；open PR [#28](https://github.com/Dickey007s/lenovo_agent/pull/28) |

> 当前适用性：`DR-0023` 的 Loop 状态、预算、控制和 Evidence Gate 继续有效；其中“用户先选允许文件”的范围交互已由 [`DR-0024`](DR-0024-autonomous-whole-workspace-research.md) 取代。历史 Evidence 仍只证明当时提交。

## 问题

本决策形成前，Workspace Harness 能让用户浏览文件、限定范围、调用 Planner 与
Analyst、查看顺序轨迹并回开引用，但服务端只执行一次单向流水。Verifier 不会产生
下一轮问题，用户也不能在中途暂停、调整方向或停止。实现提交 `8364b1e` 已把这条
单向流水升级为一个有界、只读、可控制的 Agent Control Loop 纵切；它仍不是目标架构
中的持久化长期 Runtime。

## 决策

本轮实现 Agent Control Loop 中一个最多三轮、严格只读、可暂停的路径，暂不同时引入
真实文件写入、Adaptive Swarm 或外部动作：

1. 用户以 `AgentControlLoopContract` 指定研究目标和预算；当前合同由服务端冻结完整资料库索引，Planner 自主选择每轮证据；
2. Agent 先读取目录索引，再由服务端批准本轮实际读取的文件；
3. 每轮固定经过 `Observe -> Plan -> Act(read-only) -> Verify -> Evidence Gate`；
4. Verifier 只能输出 `commit / wait_for_human / next_round / stop` 四类决定；
5. 只有证据缺口存在且预算仍允许时才能进入下一轮；
6. 用户可以 `pause / resume / steer / stop`，所有命令携带 expected version 与幂等键；
7. 最终 `AgentControlLoopBrief` 逐项绑定来源，并明确已覆盖、未覆盖、冲突和剩余风险；
8. 第一版允许使用 memory Store，但前台和文档不得称为 Durable State。

此外，Planner 候选若未通过结构、文件范围、工具、依赖或副作用校验，服务端最多允许
一次预算内修复。拒绝与重试都写入有序事件，并消耗同一模型调用预算；前台显示
“未采用”，不能把模型返回冒充成已执行计划。

## 当前实现事实

- `POST /v1/harness/runs` 冻结 Goal、完整资料库索引、最大轮次、每轮文件、模型调用和 deadline；
- 每轮都持久在当前进程 Snapshot 的 `rounds[]` 中，不覆盖上一轮；
- Evidence Gate 仅由服务端决定 `next_round / completed / budget_exhausted`；
- `POST /v1/harness/runs/{run_id}/controls` 支持 `pause / resume / steer / stop`，携带
  `expected_version` 与幂等键；
- named SSE 与最终 GET Snapshot 共同驱动前台，旧 sequence/version 不回退；
- 真实 `deepseek-v4-pro` 运行完成 2 轮、8 份文件、5 次模型调用和 21 条事件，第一轮
  第一个计划被拒绝后只重试一次并通过；
- `Commit` 只形成 `AgentControlLoopBrief`，不等于 Durable Artifact 或 TaskCommit。

## 为什么先做只读三轮

- 它能直接证明“Verify 的结果是否真的改变下一轮”，而不是重复调用模型；
- 它把预算、停止原因和人工控制放进主路径，优先补齐用户最能感知的 Loop 缺口；
- 它复用现有文件 Catalog、Preview、Planner、Analyst、named SSE 和引用回开；
- 它不把文件写入、外部动作和多 Worker 的风险同时引入，便于定位问题和形成证据。

## 前台交互影响

| 用户问题 | 前台输出 | 目标服务端事实 | 默认隐藏 |
| --- | --- | --- | --- |
| Agent 为什么读这些文件？ | 本轮问题、候选范围和选择理由 | `AgentControlLoopRound.input_file_refs` 与批准理由 | Prompt、思维链、绝对路径 |
| 它发现了什么？ | 新证据、冲突、引用与相对上一轮的变化 | `RoundFinding`、`EvidenceGap`、验证回执 | 原始 provider response |
| 为什么还要继续？ | “证据缺口 + 下一轮目的 + 剩余预算” | `GateDecision=next_round` | 内部策略枚举和调试日志 |
| 为什么停下？ | 完成、等待人、预算耗尽或用户停止 | 终态、停止原因和 Event | 含糊的完成动画 |
| 我能改变方向吗？ | 暂停、继续、调整方向、结束并提交 | `ControlEvent`、expected version 和回执 | 未确认即生效的本地假状态 |
| 最终得到什么？ | 有来源的推进建议、未解决问题和覆盖范围 | `AgentControlLoopBrief` | 无证据的自动结论 |

## 后端所有权

- `AgentControlLoopContract` 拥有目标、范围、验收条件、预算和截止时间；
- `AgentControlLoopRound` 拥有每轮文件、只读操作意图、模型回执、发现、验证和证据缺口；
- Loop Controller 拥有状态转换，模型不能直接写 `next_round` 或终态；
- Budget Controller 拥有轮次、文件、模型调用、工具调用和墙钟上限；
- Control Event 拥有 pause/resume/steer/stop 的版本与幂等语义；
- 浏览器只拥有草稿、展示、传输状态和用户命令，不推断完成或剩余预算。

## 验证门槛

以下门槛已在 Evidence 所列范围内满足，因此本决策升级为 `Limited Verified`：

- 至少一个真实 Run 由第一轮 Verify 产生 Evidence Gap，并触发第二轮；
- 每轮来源、只读操作意图、模型回执、验证、预算和 Gate 决定都来自服务端 Snapshot/Event；
- pause、steer、resume 和 stop 有版本冲突、幂等重放与前台回执测试；
- 预算耗尽、模型失败、文件变化、SSE 断线和迟到 Snapshot 均 fail closed；
- 最终建议能回开来源，并列出未覆盖目录与未解决问题；
- 桌面和移动端证明轮次、证据和控制不会互相遮挡；
- 文档持续说明 memory 状态不是 Durable State；
- 形成性用户测试之前，不声称建议更有价值、流程更清晰或效率更高。

尚未满足的目标架构门槛包括 PostgreSQL/Checkpoint 恢复、跨实例 lease、不可变
ArtifactVersion/TaskCommit、真实 Tool Gateway、多 Worker、外部动作治理和形成性用户测试。

## 非目标

- 不在本纵切写回源文件或调用真实 Connector；
- 不实现 Demo 2 多 Worker 自组织；
- 不实现 Demo 3 外部动作审批和 Permit；
- 不把模型私有思维链暴露到 UI；
- 不从三轮工程通过推导生产高可用或用户价值。
