# DR-0007：已验证任务工件以不可变版本进入受控动作

| 字段 | 内容 |
| --- | --- |
| Decision ID | `DR-0007` |
| Owner | Office Agent 项目组 |
| Date | 2026-08-13 |
| Status | `Verified`（仅限固定客户 A、最终客户回复草稿、当前 L4 策略链、Email Simulator 与被测前台路径） |
| Scope | Demo 1 最终工件进入 Demo 3 Risk / Evidence / Approval / Permit / Simulator 的最小跨 Demo 纵切 |
| Depends on | `DR-0002`、`DR-0005`、`TaskCommit`、`VerificationReport`、`ProposedActionSpec`、`RunService` |

## 1. 用户场景与问题

目标用户是完成客户经营汇报后准备采取下一步业务动作的客户经理。Demo 1 已能形成经营分析、风险页和客户回复草稿，但完成态原先只告诉用户“草稿未发送”，没有把这个结果安全地交给 Demo 3。用户若回到聊天重新描述发送意图，系统会失去 Task Commit、工件版本和验证报告之间的确定绑定，也很难解释确认卡究竟基于哪一版成果。

本轮完成条件是：只允许最终 `TaskCommit` 中、状态为 verified 且有 passed `VerificationReport` 的客户回复草稿准备外部邮件动作；前台先明确“准备动作，不是发送”，然后展示绑定成果、目标、L4 原因和为什么需要用户确认；批准后才签发一次性 Permit 并调用 Email Simulator；拒绝后不执行，也不改变已完成的 Task、ArtifactVersion 或 Commit。

关键异常路径包括：历史版本、未验证版本、非最终提交工件、Owner 不匹配、绑定事实变化、重复点击、准备请求结果未知、用户拒绝和结果说明暂未送达。前五类必须 fail closed；同一未知请求使用同一幂等键重试；收到明确准备结果后，下一次主动准备使用新键；拒绝仅终止该 Run；结果说明继续沿既有 continuation 重放语义恢复。

## 2. 来源与依据

| Source ID | 类型 | 精确引用 | 支持判断 | 局限 |
| --- | --- | --- | --- | --- |
| `USER-FEEDBACK-20260813-DEMO-BRIDGE-05` | Stakeholder feedback | [`USER-FEEDBACK-20260813-07-task-artifact-action-bridge.md`](../sources/USER-FEEDBACK-20260813-07-task-artifact-action-bridge.md) | 继续按三个 Demo 的高层关系迭代，并把设计、实现和交互一起推进 | 不是用户研究，不证明当前交互有效 |
| `MEETING-DECK-0716-V2-01` | 阶段汇报原件 | `docs/final-reference/0716-v2.pptx`，原件与哈希登记见 [`SOURCE_REGISTER`](SOURCE_REGISTER.md) | 三 Demo 分别处理持续任务、复杂协作和动作风险；共享工件、证据、控制与 Trace | 内部阶段材料，不证明 Runtime 或产品效果 |
| `SCRIPT-V5-202607` | 内部设计讲稿 | [`未来办公Agent_一小时汇报讲稿_v5.md`](../final-reference/未来办公Agent_一小时汇报讲稿_v5.md)，P03、P04、P21、P22 | P22 明确 Demo 1 输出已验证工件与 Trace，Demo 3 控制真实动作；P03/P04 要求通过稳定接口接入统一 Runtime | 内部衍生设计，不是独立行业证据或运行验证 |
| `TASK-ARTIFACT-ACTION-BRIDGE-20260813` | 源码、自动化、浏览器与截图证据 | [`DEMO1-DEMO3-TASK-ARTIFACT-ACTION-BRIDGE-EVIDENCE-20260813.md`](../evidence/DEMO1-DEMO3-TASK-ARTIFACT-ACTION-BRIDGE-EVIDENCE-20260813.md)，实现提交 `d827f29`，文档提交 `d1cc746` | 当前固定纵切已实现版本绑定、L4 Gate、批准/拒绝、Permit、Simulator 和结果说明 | 不证明真实邮件、通用 Artifact Action、Adaptive Swarm、生产持久化或用户理解 |

## 3. 决策与备选

采用“先绑定不可变事实，再准备动作”的服务端桥接：

1. 新增 `TaskArtifactBinding`，绑定 `task_id/version`、`commit_id/state_hash`、`artifact_id/version_id/version/content_digest`、`deliverable_id` 和 `verification_report_id`。
2. `TaskService` 只导出当前 Owner 的最终提交且验证通过的 ArtifactVersion，并可在证据、审批、授权和执行前重新验证全部绑定事实。
3. 专用准备接口把固定客户回复草稿转为确定性 `email.send` ActionCandidate。收件人是明确的演示地址，主题和正文来自绑定版本；模型不决定目标、风险、审批或执行参数。
4. `RunService` 将绑定写入 `ProposedActionSpec` 的参数哈希与创建幂等摘要。绑定变化时旧 Action 进入 failed 并失效，旧审批和 Permit 不能复用。
5. 前台在任务完成态提供唯一“准备发送客户回复”入口。确认卡同时回答依据版本、动作目标、风险原因、为什么找人以及拒绝的后果；批准后才执行 Simulator。

未采用“用户在聊天里重新描述发送”，因为会丢失 Task Commit 与验证版本的确定关联。未采用“完成后直接发送”，因为外部客户动作必须经过 L4 人工确认。未采用浏览器自行拼接 ActionSpec，因为 Task、Commit、Verification 与动作参数都是服务端信任边界。未在本轮启动 Adaptive Swarm，因为跨 Demo 工件接口是其后续结果进入治理层的共同前置，且当前能够形成更小、更可验证的纵切。

## 4. 后端事实与状态转换

| 事实或状态 | 权威来源 | 转换与语义 |
| --- | --- | --- |
| 可准备成果 | `TaskSnapshot.status=committed`、`last_commit.artifact_version_ids`、verified `ArtifactVersion`、passed `VerificationReport` | 任一事实缺失即 409，不创建 Run |
| 动作绑定 | `ProposedActionSpec.task_artifact_binding` | 进入 Action payload digest、Run Snapshot、审计和执行前校验；不依赖 UI 选中态 |
| 创建幂等 | `RunSnapshot.creation_idempotency_key/creation_digest` | 同 Owner+key+同候选返回同 Run；同 key 不同事实返回 409；前端只在结果未知时保留 key |
| 风险与控制 | `RiskAssessment`、`PolicyEffect`、`EvidenceRecord`、`ControlPlan` | 固定外部客户邮件为 L4；证据满足后等待 `current_user` 批准 |
| 用户拒绝 | `ApprovalRecord(decision=rejected)` 与重评估后的 `ControlPlan.status=DENIED` | 不签发 Permit、不调用工具、不修改 Task Commit |
| 批准与执行 | `ApprovalRecord(approved)` → `READY_TO_AUTHORIZE` → Permit → ToolGateway | 每一步再次验证 TaskArtifactBinding；成功结果来自 `email_simulator` |
| 结果说明 | 绑定 Run 的终态与 Conversation continuation | 使用确定性边界文案，不调用模型猜测真实发送；同一进程内可重放相同完成消息 |

Task 本身在 Commit 后保持终态，不因为派生 Run 的批准、拒绝或执行而改变。Run 是独立治理状态；两者通过不可变 Binding 关联，而不是共享一个模糊的“已完成”标志。

## 5. 前台输出与隐藏边界

完成态继续先展示三项已核对成果，并明确客户回复仍是草稿、未发送。唯一主动作“准备发送客户回复”旁写清：下一步会创建受控动作，随后展示风险、目标和确认；当前固定收件人是演示地址，最终执行只进入 Simulator。

确认卡显示“基于已核对成果”、客户回复草稿版本、本轮汇报版本、L4 原因、外部客户影响、目标邮箱和“为什么需要你确认”。批准按钮不叫“发送”，而是先记录批准；只有状态变为 `READY_TO_AUTHORIZE` 后才出现“确认执行”。拒绝后 Agent 明确说明没有执行、没有连接真实邮箱；已完成汇报继续保持 committed。

普通 UI 不展示 Commit state hash、content digest、verification report ID、创建幂等键、Permit、完整 Action 参数、策略内部角色 ID或底层审计 payload。审计视图仍可查看有权限的 Trace 摘要。前端不得用当前选中工件、按钮颜色或 Toast 推断绑定有效、风险等级、审批满足或执行成功。

## 6. 验证与边界

独立证据见 [`DEMO1-DEMO3-TASK-ARTIFACT-ACTION-BRIDGE-EVIDENCE-20260813.md`](../evidence/DEMO1-DEMO3-TASK-ARTIFACT-ACTION-BRIDGE-EVIDENCE-20260813.md)。实现提交 `d827f29`、文档提交 `d1cc746` 的封口结果：Python 全量 `112 passed, 1 skipped (4.11s)`；完整 system Edge 浏览器 `29 passed (1.4m)`，其中 Demo 1 文件 `13 passed (1.0m)`；治理 `4 passed`；Ruff、前端 lint、Next.js build 和 diff-check 通过。两张 `1440 x 900` 截图记录 Gate 与 Simulator 结果。

因此本决策仅在固定客户 A、最终回复草稿、当前 L4 规则、内存浏览器路径和 Email Simulator 内为 `Verified`。它不覆盖真实邮箱、用户可用性、任意工件/动作映射、多收件人、附件、Task 派生 Run 的 PostgreSQL 重启恢复、多实例创建幂等、数据库 CAS、真实身份、历史轮次选择、Adaptive Swarm 或生产 SLA。

## 7. 关联项

- Source：`USER-FEEDBACK-20260813-DEMO-BRIDGE-05`、`MEETING-DECK-0716-V2-01`、`SCRIPT-V5-202607`
- Evidence：`TASK-ARTIFACT-ACTION-BRIDGE-20260813`
- API：`POST /v1/tasks/{task_id}/artifacts/{artifact_version_id}/actions/email-send`
- 协议：`TaskArtifactBinding`、`ProposedActionSpec.task_artifact_binding`
- 实现提交：`d827f29`
- 文档提交：`d1cc746`
- PR：[#12](https://github.com/Dickey007s/lenovo_agent/pull/12)，堆叠在开放的 PR #11 之上
