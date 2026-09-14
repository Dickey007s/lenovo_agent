# SCENARIO-003：Demo 3 动作影响账本

| 字段 | 内容 |
| --- | --- |
| Scenario ID | `SCENARIO-003` |
| Status | `Verified`（限定固定场景工程范围） |
| Decision | [`DR-0012`](../decisions/DR-0012-demo3-action-impact-ledger.md) |
| Scope | 固定客户 A 已核对回复草稿进入 Email Simulator 的治理链 |

## 1. 目标用户与触发条件

目标用户是客户经理。用户已经完成客户 A 经营汇报，页面显示经营分析、风险页和客户回复草稿均已核对，但客户回复仍未发送。用户点击“准备发送客户回复”，系统创建治理 Run，而不是直接发送。

用户在确认前需要理解四件事：动作会改变什么、哪些事实需要重新核对、哪些汇报成果保持不变，以及哪些外部动作不会发生。用户在补证、审批、授权、拒绝、失效或执行后需要看到与服务端事实一致的状态变化。

## 2. 完成条件

1. Action Gate 显示服务端 `impact_preview` 和四类 `ImpactItem`。
2. “准备动作”“批准”和“确认执行”是三个不同承诺。
3. 只有服务端返回 `execution_receipt` 后，前台才显示实际执行结果。
4. 拒绝、绑定变化、篡改或 Simulator 失败不改变已提交 Task。
5. 页面不把 Simulator 结果表述为真实邮件已发送。

## 3. 异常路径

| 路径 | 用户应看到 | 服务端事实 |
| --- | --- | --- |
| 缺少报价或 DLP 证据 | 需要补充可信依据 | `WAITING_EVIDENCE`、`EvidenceRecord` |
| 需要当前用户确认 | 等待你的确认 | `WAITING_APPROVAL`、`required_approvals` |
| 用户拒绝 | 动作已阻止，汇报成果未改变 | `ApprovalRecord=rejected`、`DENIED` |
| Task/Artifact 变化 | 动作已失效，需要重新准备 | `ACTION_INVALIDATED`、绑定校验失败 |
| 参数篡改 | 参数与批准内容不一致，未执行 | `TAMPER_BLOCKED` |
| Simulator 失败 | 模拟执行失败，成果未回滚 | `FAILED`、无真实外部写入 |
| 请求结果未知 | 结果待确认，正在重新读取 | `GET /runs/{run_id}` 与 Run SSE 对账 |

## 4. 来源与局限

本场景来源于 `USER-FEEDBACK-20260813-DEMO-BRIDGE-05`、`MEETING-DECK-0716-V2-01`、`SCRIPT-V5-202607`、`USER-FEEDBACK-20260820-03`、`HAI-GUIDELINES-CHI2019` 和 `GOOGLE-PAIR-FEEDBACK-CONTROL-2021`，具体引用与局限见 [`DR-0012`](../decisions/DR-0012-demo3-action-impact-ledger.md) 与 [`SOURCE_REGISTER`](../decisions/SOURCE_REGISTER.md)。这些来源支持场景和交互原则，不证明用户理解或真实业务效果。

本场景只验证固定演示收件人、固定客户回复草稿和 Email Simulator。真实邮箱、真实 CRM/DLP/通讯录、通用附件、批量外发、动态 Connector、生产身份和跨进程高可用均不在范围内。自动化证据不等同于目标用户理解、效率或决策质量改善；这些仍需独立用户研究。
