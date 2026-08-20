# DR-0012：Demo 3 动作影响账本与治理回执

| 字段 | 内容 |
| --- | --- |
| Decision ID | `DR-0012` |
| Owner | Office Agent 项目组 |
| Date | 2026-08-20 |
| Status | `Verified`（限定固定 Demo 3 工程范围） |
| Scope | Demo 3 Action Gate 的提交前影响预演、治理过程状态和终态执行回执 |
| Depends on | `DR-0007`、`DR-0010`、`GOVERNANCE_AND_ACTIONS`、`RunSnapshot`、`AuditEvent` |

## 1. 用户场景与完成条件

目标用户是完成客户 A 经营汇报后，准备把已经核对通过的客户回复草稿交给外部动作治理的客户经理。用户点击“准备发送客户回复”后，不应只看到风险等级和“请确认”，而应在同一 Action Gate 中知道这次动作会改变什么、还要重新核对什么、哪些成果保持不变，以及哪些外部动作不会发生。

本决策的最小纵切是固定 `reply_draft → email.send`。`self`、`internal`、`external`、`pricing` 四个现有 Demo 3 场景用于风险与治理回归；其余四个已注册 Simulator capability 只在协议兼容和边界测试中覆盖，不因此宣称已具备通用动作影响预测器。

完成条件：

1. `RUN_CREATED` 返回服务端生成的 `impact_preview`，而不是前端或 LLM 自行拼装的影响说明。
2. 预演固定分成“会改变 / 会重新核对 / 保持不变 / 不会发生”四类。
3. 证据、审批、授权、执行、拒绝、失效、篡改和失败后，前台只依据 `RunSnapshot` 与有序 `AuditEvent` 更新状态。
4. `execution_receipt` 只在对应服务端事实产生后出现；预演不得复制成回执。
5. 拒绝、动作失效或 Simulator 失败不改变已完成的 Task Commit、ArtifactVersion 或 VerificationReport。

关键异常路径包括：缺证据、L5/受限能力拒绝、审批拒绝、Task Artifact 绑定变化、参数篡改、Permit 重放、请求结果未知、Simulator 失败和页面刷新。

## 2. 来源与局限

| Source ID | 类型 | 精确引用 | 支持判断 | 局限 |
| --- | --- | --- | --- | --- |
| `USER-FEEDBACK-20260813-DEMO-BRIDGE-05` | Stakeholder feedback | `docs/sources/USER-FEEDBACK-20260813-07-task-artifact-action-bridge.md` | 三个 Demo 需要形成从已验证成果到受控动作的可解释闭环 | 不是目标用户研究，不证明确认卡有效 |
| `MEETING-DECK-0716-V2-01` | 阶段汇报原件 | `docs/final-reference/0716-v2.pptx`，哈希见 `docs/decisions/SOURCE_REGISTER.md` | 三 Demo 的高层关系和 Demo 3 风险控制定位 | 内部阶段材料，不证明实现或用户效果 |
| `SCRIPT-V5-202607` | 内部设计讲稿 | `docs/final-reference/未来办公Agent_一小时汇报讲稿_v5.md` P03/P04/P21/P22 | 支持已验证工件、风险分级和受控动作的演示叙事 | 内部衍生设计，不是独立行业证据 |
| `USER-FEEDBACK-20260820-03` | Stakeholder feedback | `docs/sources/USER-FEEDBACK-20260820-03-agent-impact-visibility.md` | 将 Agent 操作影响可见设为前台创新重点 | 不证明新交互已经改善理解或效率 |
| `HAI-GUIDELINES-CHI2019` | 研究/官方页面 | Microsoft Research, *Guidelines for Human-AI Interaction*, CHI 2019 | 支持及时反馈、状态说明和用户校正 | 通用指南，不定义本项目协议 |
| `GOOGLE-PAIR-FEEDBACK-CONTROL-2021` | 官方设计实践 | Google PAIR, *Feedback + Control*, 2021 | 支持解释用户输入如何影响系统并保留控制权 | 设计实践，不是本项目运行证据 |
| `TASK-ARTIFACT-ACTION-BRIDGE-20260813` | 源码、自动化与截图 | `docs/evidence/DEMO1-DEMO3-TASK-ARTIFACT-ACTION-BRIDGE-EVIDENCE-20260813.md` | 证明固定客户回复草稿可绑定进入 L4 Gate、Permit 和 Email Simulator | 不证明真实发送、通用动作或跨进程 Run 恢复 |

## 3. 前台影响账本

“动作影响账本”是一个业务投影，不展示内部 Action payload。每个 `ImpactItem` 至少包含：

```text
item_id / change_kind / label / before / after
```

`change_kind` 只允许以下四类协议值，并且 `item_id → change_kind` 是服务端固定映射，不允许由前端、LLM 或用户改写：

| `item_id` | `change_kind` | 前台含义 | 预演态 | 回执态 |
| --- | --- | --- | --- | --- |
| `target-change` | `will_change` | 会改变 | 预计改变目标对象或治理状态 | 服务端已记录的实际变化 |
| `binding-recheck` | `will_recheck` | 会重新核对 | 仍需满足的证据、权限或审批 | 已重新核对、缺失、失效或冲突 |
| `task-preserved` | `unchanged` | 保持不变 | 不会被本动作改写的成果和范围 | 服务端确认仍保持不变 |
| `real-connector-not-called` | `no_external_action` | 不会发生 | 确认前不会产生外部动作 | 本轮没有真实外部写入，或动作被阻止 |

预演必须标注“预计 / 尚未执行”；回执必须标注“已记录 / 已核对 / 未执行 / 模拟器结果”。`ToolExecutionResult.status=succeeded` 只能使前台显示“模拟器已返回结果”，不能显示真实邮箱、CRM、OA 或日历已经改变。

前台应隐藏：`run_id`、`action_id`、`trace_id`、Permit token、完整哈希、原始 `source_refs`、策略内部 ID、Prompt、思维链、Worker 对话和完整工具参数。审计视图仍可在授权范围内查看事件摘要。

## 4. 后端事实与协议

现有 `RunSnapshot` 的协议字段为：

```text
impact_preview: ActionImpactPreview | null
execution_receipt: ActionExecutionReceipt | null
```

`ActionImpactPreview` 至少保留 `preview_id/action_id/action_hash/policy_version/items/executor/external_side_effect/generated_at/task_artifact_binding`；`ActionExecutionReceipt` 至少保留 `receipt_id/action_id/action_hash/status/items/execution_id/permit_id/simulator/external_side_effect/error_code/failure_stage/retryable/observed_at`。两者必须绑定当前 `action.action_id` 与 `control_plan.action_hash`。`impact_preview.items` 与 `execution_receipt.items` 使用 `ImpactItem`。`impact_preview` 在服务端完成 Action、Risk、Policy、Evidence 和 ControlPlan 评估后生成；`execution_receipt` 只能由服务端状态转换和执行结果生成。它们不属于 LLM 候选字段。

事实映射如下：

| 前台区域 | 权威事实 |
| --- | --- |
| 动作与目标 | `ProposedActionSpec.target_scope/recipients/resources/data_classes/state_change_type/reversibility` |
| 已核对成果 | `TaskArtifactBinding`、`TaskSnapshot.last_commit`、`ArtifactVersion`、`VerificationReport` |
| 风险与理由 | `RiskAssessment.risk_level/dimensions/reason_codes` |
| 重新核对 | `EvidenceRecord`、`PolicyEffect.required_evidence`、`ControlPlan.missing_requirements` |
| 审批与授权 | `ApprovalRecord`、`ControlPlan.status/required_approvals`、`PermitMetadata` |
| 治理回执 | `RunSnapshot.status`、`AuditEvent` 的 `CONTROL_PLAN_UPDATED/APPROVAL_RECORDED/PERMIT_ISSUED` |
| 执行回执 | `ToolExecutionResult`、`TOOL_EXECUTED`、`ACTION_INVALIDATED/TAMPER_BLOCKED` |

同一 `action_id + action_hash` 的事件按 `sequence` 应用；刷新和 SSE 重连必须通过 `GET /runs/{run_id}` 对账。结果未知时保留原创建或执行幂等语义，不以按钮点击、Toast 或动画推断动作结果。

## 5. 前台状态时序

```text
RUN_CREATED
  -> impact_preview / 尚未执行
  -> WAITING_EVIDENCE / 需要重新核对
  -> WAITING_APPROVAL / 等待确认
  -> READY_TO_AUTHORIZE / 条件已满足
  -> PERMIT_ISSUED / 已授权，尚未执行
  -> TOOL_EXECUTED / 模拟器已返回结果
```

拒绝、L5、绑定变化、篡改和失败分别进入“已阻止 / 动作已失效 / 参数不一致 / 执行失败”，并在账本中保留“保持不变”和“不会发生”事实。任何终态文案都不能绕过 `RunSnapshot` 或有序事件。

## 6. 验证矩阵与证据边界

| 验证项 | 必须断言 | 证据状态 |
| --- | --- | --- |
| 四类预演 | `RUN_CREATED` 返回四类固定 `ImpactItem`，不含内部 ID 和真实发送措辞 | 已验证：Python + E2E |
| `external` | L4、等待当前用户确认、审批前无执行 | 已验证：Python 场景回归与桌面预演 |
| `pricing` | 缺报价证据时只允许补证，不出现执行 CTA | 已验证：Python 场景回归 |
| `internal` | 非受管设备确定性 `DENIED`，无审批和执行 | 已验证：Python 场景回归 |
| `self` | 低风险路径仍显示目标、范围和最小治理事实 | 已验证：Python 场景回归 |
| 拒绝与失败 | Run 终态改变，Task Commit/Artifact/Verification 不变 | 已验证：后端回归与拒绝截图；失败前台未单独截图 |
| 绑定变化 | 旧 Action、审批和 Permit 失效 | 已验证：Task Artifact bridge 回归 |
| 参数篡改与 Permit 重放 | `TAMPER_BLOCKED` / `PERMIT_REPLAYED`，不产生第二次执行 | 已验证：后端回归；无独立篡改截图 |
| Simulator | 结果含 `simulated=true`，前台明确非真实外部写入 | 已验证：成功回执 E2E 与后端回归 |
| 刷新、断线、未知结果 | GET/SSE 对账、无重复 Run/事件/完成消息 | 部分验证：终态重放与未知结果已测；跨进程/断线恢复仍待验证 |
| 前台响应式 | 桌面、移动、键盘、读屏、无横溢和 44px 触控门槛 | 已验证：桌面/移动 E2E；用户理解仍待研究 |

工程验证记录见 [`DEMO3-ACTION-IMPACT-LEDGER-20260820`](../evidence/DEMO3-ACTION-IMPACT-LEDGER-EVIDENCE-20260820.md)：Python `151 passed, 1 skipped in 3.69s`、完整 E2E `37 passed (2.2m)`（含审计工作台 raw 字段隐藏回归）、Ruff/governance `4 passed in 0.02s`/lint/build 通过；视觉终验无 P0/P1，四张截图的尺寸、文件大小和 SHA-256 已在 Evidence 记录。实现提交为 `9335470`，对应 [PR #18](https://github.com/Dickey007s/lenovo_agent/pull/18)；文档提交在首次证据提交后回填。

## 7. Simulator 与系统边界

- 当前只有 `email.send`、`task.create`、`calendar.invite`、`crm.opportunity.update`、`expense.request_evidence` 五个 capability 注册了 Simulator。
- `email_simulator` 与 `office_action_simulator` 的成功只代表模拟器返回成功，不代表真实邮箱、CRM、OA、日历或任务系统发生变化。
- 当前固定桥接只覆盖客户 A 的最终 `reply_draft → email.send`，不是通用 Artifact Action registry。
- 当前工程证据主要使用内存 RunStore；Task 派生 Run 的 PostgreSQL 重启、多实例创建幂等、响应丢失后的跨进程恢复和真实 Connector 仍未知。
- Permit replay set、Conversation Thread/Message 和完成消息重放存在进程边界；不得把进程内证据表述为高可用或生产级恢复。
- 没有真实 SSO/RBAC、后台执行队列、动态 Connector 或目标用户研究。工程自动化只能证明协议投影和被测路径，不证明用户理解、效率或业务价值。

## 8. 关联项

- `DR-0007`：已验证 Task Artifact 进入受控动作的窄桥。
- `DR-0010`：影响预演与变化回执的双时态交互原则。
- `docs/scenarios/SCENARIO-003-demo3-action-impact-ledger.md`：本决策的固定场景。
- `docs/evidence/DEMO3-ACTION-IMPACT-LEDGER-EVIDENCE-20260820.md`：限定范围工程证据；commit、PR 和部分异常视觉证据待补。
