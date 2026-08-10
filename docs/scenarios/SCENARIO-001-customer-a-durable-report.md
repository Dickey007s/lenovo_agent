# SCENARIO-001：客户 A 经营汇报的受控持久任务

| 字段 | 内容 |
| --- | --- |
| Scenario ID | `SCENARIO-001` |
| Owner | Office Agent 项目组 |
| Status | `Ready` |
| Decision | [`DR-0002`](../decisions/DR-0002-bounded-durable-office-loop.md) |
| 设计来源 | `USER-FEEDBACK-20260810-01/02`、`MEETING-DECK-0716-V2-01`、`SCRIPT-V5-202607`、`REPO-BASELINE-84AABC9`、`REACT-ICLR-2023`、`LANGGRAPH-DURABLE-20260810`、`NIST-AI-RMF-1.0` |

## 1. 用户、触发与当前问题

目标用户是需要准备客户经营会材料的项目负责人或客户经理。触发条件是：经营会临近，用户要从邮件、CRM、预测表和项目周报中整理经营分析、风险页和客户回复草稿，并且任务可能跨越较长时间、设备切换和服务重启。

当前 V0.1 可以编辑工作区并治理一次副作用动作，但没有长期 Task、分支、工件版本和任务级控制事实。用户只能看到一次对话或一次 Run，无法可靠判断：任务是否仍在推进、哪个分支被证据阻塞、其他分支是否安全继续、当前工件来自哪个版本，以及恢复后是否重复执行。

目标是让用户围绕同一个 Task ID 观察、纠偏和接管任务，并且只在服务端验证与提交完成后看到“完成”。

## 2. 业务价值与明确边界

本场景验证的是固定 Fixture 下的长期任务协议、持久状态、分支隔离、控制事件和可验证提交，不验证真实客户数据接入、真实跨端身份、生产级多实例一致性或 Adaptive Swarm。

- 所有邮件、CRM、金额、项目和客户名称都是 Demo Fixture。
- 本场景不发送邮件、不写入 CRM；若后续产生副作用动作，必须进入现有 `RunService → Risk/Policy/Evidence/Approval/Permit → Tool Gateway → Simulator` 链路。
- “客户 A 场景具有代表性”“Task Bar 降低理解成本”“分支控制符合用户心智”仍是待用户研究验证的假设。
- 设计来源 Source ID 与运行时 Fixture `source_ref` 是两套概念，不能互相替代。

## 3. Task Contract

| 契约项 | 固定 Fixture |
| --- | --- |
| Title | 客户 A 经营汇报 |
| Objective | 形成可审阅的经营分析、风险页和客户回复草稿 |
| Deliverables | `operating-analysis`、`risk-brief`、`reply-draft` |
| Deadline | Demo 中使用固定截止时间；不是生产 SLA |
| Budget | 最多 12 个 Loop step、30 次工具调用、3,600 秒运行时间 |
| Allowed capabilities | 只读 Fixture 查询、文档草稿、邮件草稿；不允许真实外部写入 |
| Completion | 三个必需工件均有来源、通过验证、无未解决冲突并进入同一个 Verified Commit |

运行时 Fixture 来源：

| source_ref | 内容与版本 | 所有权边界 |
| --- | --- | --- |
| `fixture:mail/customer-a:2026-06-15` | 客户来信与问题摘要 | Demo Fixture，不是真实邮箱 |
| `fixture:crm/customer-a:official-revenue-v3` | 正式经营口径：2,400 万 | Demo Fixture，不是真实 CRM |
| `fixture:forecast/customer-a:revenue-v2` | 预测口径：2,680 万 | Demo Fixture，不是真实预测系统 |
| `fixture:project/customer-a:weekly-v5` | 项目风险和里程碑 | Demo Fixture，不是真实项目系统 |

## 4. 主路径

| 阶段 | 服务端行为 | 前台输出 | 验证事实 |
| --- | --- | --- | --- |
| Contract | 创建稳定 `TaskContract`、Task ID、三个分支和预算 | Task Bar 显示目标、阶段、预算和 Task ID | `TASK_CREATED` + `TaskSnapshot.version=1` |
| Observe | 读取四个允许的 Fixture 来源并固定版本 | 来源摘要和同步状态，不显示原始 Prompt | `LOOP_STEP_STARTED/COMPLETED`，Trace 含 source refs |
| Plan | 建立经营分析、风险、收入口径三个受控分支 | 分支列表显示 queued/running 和依赖 | `BRANCH_STATUS_CHANGED` |
| Act | 生成候选事实、风险和收入说明工件 | 工件列表显示 candidate、版本和来源 | `ARTIFACT_VERSION_CREATED` |
| Verify | 发现 2,400 万与 2,680 万冲突，只暂停收入分支 | 冲突卡显示来源、影响范围和可选动作；其他分支继续 | `CONFLICT_OPENED` + 收入分支 `waiting_evidence` |
| Control | 用户选择正式口径并要求保留预测差异说明 | 控制提交先显示“待服务端确认”，随后显示应用版本 | `CONTROL_ACCEPTED/APPLIED` + `CONFLICT_RESOLVED` |
| Commit | 重新验证受影响工件并提交三项交付物 | 只在收到提交事实后显示完成、版本、验证和 Trace 摘要 | `CHECKPOINT_COMMITTED` + `TASK_COMMITTED` + state hash |

## 5. 异常与恢复路径

| 异常 | 服务端真值 | 用户反馈与动作 | 验收要求 |
| --- | --- | --- | --- |
| 证据冲突 | 单个 `BranchSnapshot.status=waiting_evidence` | 显示受影响分支、两个来源和解决动作 | 其他分支不得被暂停，冲突事实不得进入最终 Commit |
| SSE 断线 | 业务状态不变，客户端仅失去更新 | 显示“更新暂时中断，任务可能仍在后台运行”；禁用有副作用的任务控制 | 以 `after=last_sequence` 回放后再用 Snapshot 对账 |
| 旧版本控制 | `expected_task_version` 不等于当前版本 | 返回 `409`，提示任务已在其他设备更新 | 不自动重放旧指令，不乐观修改分支状态 |
| 预算耗尽 | `budget.exhausted=true`，受影响分支暂停 | 显示预算原因，可缩小范围、申请额度或接管 | 不继续后台循环，不显示无限进度 |
| 权限不足 | 服务端拒绝控制或来源读取 | 保持只读，说明需要的角色或来源权限 | 不回放被拒绝命令，不泄露受限来源内容 |
| 进程重启 | 从持久 Snapshot、事件和工件版本恢复 | 继续显示同一 Task ID 和最后确认 Commit | 不重复工具调用、不重复 ArtifactVersion、不重复 Commit |
| 单分支失败 | 仅受影响分支 `failed` | 显示失败范围、最近 Commit 和恢复选项 | 其他可运行分支继续；顶层不得误报整任务失败 |
| Take over | 分支进入 `taken_over` | 显示当前控制权和可人工编辑范围 | Agent 不再写该分支，Return control 后从新版本恢复 |

## 6. 前台信息层级

默认展示：目标、Task ID、阶段、预算、分支状态、来源名称与更新时间、工件版本、冲突、验证结果、待处理动作、最近 Commit 和脱敏 Trace 摘要。

默认隐藏：原始 Prompt、思维链、Worker 内部对话、JWT/Permit、幂等键、权限哈希、完整工具参数、密钥、堆栈、未脱敏个人信息和无决策价值的调度日志。

## 7. 验收指标

以下是实现验收目标，不是当前结果：

- 持久恢复：重启前后 Task ID、版本、Artifact head 和 state hash 一致率 `100%`。
- 幂等恢复：重复命令、重复 resume 和网络重试导致的重复 ArtifactVersion/Commit 数为 `0`。
- 分支隔离：收入冲突发生时，只有目标分支进入 `waiting_evidence`。
- 前后端一致：UI 终态与服务端 Snapshot 终态一致率 `100%`。
- 控制反馈：本地 Demo 的控制事件到可见服务端确认目标 `P95 ≤ 2s`。
- 用户理解、认知负担和接管效果尚未测量，不能在功能验收后自动宣称改善。

## 8. 证据位置

- 协议与状态机：[`TASK_RUNTIME_PROTOCOL.md`](../contracts/TASK_RUNTIME_PROTOCOL.md)
- UI—服务端事实：[`UI_SERVER_FACT_MATRIX.md`](../contracts/UI_SERVER_FACT_MATRIX.md)
- 设计来源：[`SOURCE_REGISTER.md`](../decisions/SOURCE_REGISTER.md)
- 后续实现证据：各 PR 的自动化测试、Task Trace、桌面/移动截图和最终汇报；在产生前均标记为待验证。
