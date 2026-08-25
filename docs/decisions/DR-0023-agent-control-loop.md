# DR-0023：先实现 Agent Control Loop 的三轮只读纵切

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Draft`；尚无实现或运行证据 |
| 日期 | 2026-08-25 |
| 触发来源 | `USER-FEEDBACK-20260825-CONTROL-LOOP-16`、`USER-FEEDBACK-20260825-CONTROL-LOOP-NAMING-17` |
| 研究审计 | [`AGENT-CONTROL-LOOP-IMPLEMENTATION-AUDIT-20260825`](../research/AGENT-CONTROL-LOOP-IMPLEMENTATION-AUDIT-20260825.md) |
| 场景 | [`SCENARIO-009`](../scenarios/SCENARIO-009-agent-control-loop.md) |
| Evidence | 待实现后新增；当前没有可升级状态的运行证据 |

## 问题

当前 Workspace Harness 能让用户浏览文件、限定范围、调用 Planner 与 Analyst、
查看顺序轨迹并回开引用，但服务端只执行一次单向流水。Verifier 不会产生下一轮
研究问题，用户也不能在中途暂停、调整方向或停止。因此当前不能称为参考架构中的
长期 Agent Control Loop。

## 决策

下一条工程纵切先实现 Agent Control Loop 中一个最多三轮、严格只读、可暂停的路径，
暂不同时引入真实文件写入、Adaptive Swarm 或外部动作：

1. 用户以 `AgentControlLoopContract` 指定研究目标、允许目录范围、完成条件和预算；
2. Agent 先读取目录索引，再由服务端批准本轮实际读取的文件；
3. 每轮固定经过 `Observe -> Plan -> Act(read-only) -> Verify -> Evidence Gate`；
4. Verifier 只能输出 `commit / wait_for_human / next_round / stop` 四类决定；
5. 只有证据缺口存在且预算仍允许时才能进入下一轮；
6. 用户可以 `pause / resume / steer / stop`，所有命令携带 expected version 与幂等键；
7. 最终 `AgentControlLoopBrief` 逐项绑定来源，并明确已覆盖、未覆盖、冲突和剩余风险；
8. 第一版允许使用 memory Store，但前台和文档不得称为 Durable State。

## 为什么先做只读三轮

- 它能直接证明“Verify 的结果是否真的改变下一轮”，而不是重复调用模型；
- 它把预算、停止原因和人工控制放进主路径，优先补齐用户最能感知的 Loop 缺口；
- 它复用现有文件 Catalog、Preview、Planner、Analyst、named SSE 和引用回开；
- 它不把文件写入、外部动作和多 Worker 的风险同时引入，便于定位问题和形成证据。

## 前台交互影响

| 用户问题 | 前台输出 | 目标服务端事实 | 默认隐藏 |
| --- | --- | --- | --- |
| Agent 为什么读这些文件？ | 本轮问题、候选范围和选择理由 | `ControlLoopRoundSnapshot.selected_file_refs` 与批准理由 | Prompt、思维链、绝对路径 |
| 它发现了什么？ | 新证据、冲突、引用与相对上一轮的变化 | `RoundFinding`、`EvidenceGap`、验证回执 | 原始 provider response |
| 为什么还要继续？ | “证据缺口 + 下一轮目的 + 剩余预算” | `GateDecision=next_round` | 内部策略枚举和调试日志 |
| 为什么停下？ | 完成、等待人、预算耗尽或用户停止 | 终态、停止原因和 Event | 含糊的完成动画 |
| 我能改变方向吗？ | 暂停、继续、调整方向、结束并提交 | `ControlEvent`、expected version 和回执 | 未确认即生效的本地假状态 |
| 最终得到什么？ | 有来源的推进建议、未解决问题和覆盖范围 | `AgentControlLoopBrief` | 无证据的自动结论 |

## 后端所有权

- `AgentControlLoopContract` 拥有目标、范围、验收条件、预算和截止时间；
- `ControlLoopRoundSnapshot` 拥有每轮文件、工具/模型回执、发现、验证和证据缺口；
- Loop Controller 拥有状态转换，模型不能直接写 `next_round` 或终态；
- Budget Controller 拥有轮次、文件、模型调用、工具调用和墙钟上限；
- Control Event 拥有 pause/resume/steer/stop 的版本与幂等语义；
- 浏览器只拥有草稿、展示、传输状态和用户命令，不推断完成或剩余预算。

## 验证门槛

只有同时出现以下证据，才能把本决策从 `Draft` 升级为限定工程路径的
`Limited Verified`：

- 至少一个真实 Run 由第一轮 Verify 产生 Evidence Gap，并触发第二轮；
- 每轮来源、模型/工具回执、验证、预算和 Gate 决定都来自服务端 Snapshot/Event；
- pause、steer、resume 和 stop 有版本冲突、幂等重放与前台回执测试；
- 预算耗尽、模型失败、文件变化、SSE 断线和迟到 Snapshot 均 fail closed；
- 最终建议能回开来源，并列出未覆盖目录与未解决问题；
- 桌面和移动端证明轮次、证据和控制不会互相遮挡；
- 文档持续说明 memory 状态不是 Durable State；
- 形成性用户测试之前，不声称建议更有价值、流程更清晰或效率更高。

## 非目标

- 不在本纵切写回源文件或调用真实 Connector；
- 不实现 Demo 2 多 Worker 自组织；
- 不实现 Demo 3 外部动作审批和 Permit；
- 不把模型私有思维链暴露到 UI；
- 不从三轮工程通过推导生产高可用或用户价值。
