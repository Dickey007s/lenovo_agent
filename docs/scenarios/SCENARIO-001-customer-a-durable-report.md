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

PR 3 之前的 V0.1 基线可以编辑工作区并治理一次副作用动作，但没有长期 Task、分支、工件版本和任务级控制事实。原流程只能看到一次对话或一次 Run，无法可靠判断：任务是否仍在推进、哪个分支被证据阻塞、其他分支是否安全继续、当前工件来自哪个版本，以及恢复后是否重复执行。

目标是让用户围绕同一个 Task ID 观察、纠偏和接管任务，并且只在服务端验证与提交完成后看到“完成”。

## 2. 业务价值与明确边界

本场景验证的是固定 Fixture 下的任务协议、可持久状态模型、分支隔离、控制事件和可验证提交，不验证真实客户数据接入、真实跨端身份、生产级多实例一致性或 Adaptive Swarm。PR 3 的 start 是一次同步 mutation，不是后台持续调度器。

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
| Deadline | 当前客户 A Fixture 为 `null`；自定义契约测试覆盖到期前拒绝 mutation，不代表生产 SLA |
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

| 阶段 | 服务端行为 | PR 3 前台输出 | 当前证据与边界 |
| --- | --- | --- | --- |
| Contract | 创建稳定 `TaskContract`、Task ID、三个分支和预算 | Active Task Bar 显示目标、阶段、预算、版本和 Task ID | 已实现：`TASK_CREATED` + `TaskSnapshot.version=1` |
| Observe | 从四个代码内固定 Fixture `source_ref` 生成 Observe Trace | 不显示原始 Prompt 或内部推理 | 已产生 `LOOP_STEP_STARTED/COMPLETED`；不是真实 Connector 读取 |
| Plan | 为三个固定交付物记录分支运行 Trace | 分支列表在 start 响应后显示服务端终态 | 已产生 `BRANCH_STATUS_CHANGED`；事务中间态不对浏览器逐步可见 |
| Act | 由确定性代码生成候选工件 | 当前没有完整 Artifact 列表 | 服务端已产生 `ARTIFACT_VERSION_CREATED`；不来自 LLM |
| Verify | 发现 2,400 万与 2,680 万冲突，只阻塞经营分析分支 | 冲突卡显示来源、候选值、影响分支和解决动作 | 固定 Fixture 主路径与截图已覆盖；不证明真实业务收益 |
| Control | 用户选择正式口径，或提交分支控制 | 只有服务端 Snapshot 确认后才更新；Steer accepted 只称已记录待应用 | Resolve/分支控制已有事实；Steer 重新规划尚未实现 |
| Commit | 解决最后一个 open Conflict 时重新验证经营分析，并联动重生成、验证客户回复后再生成 TaskCommit；若仍有其他冲突则不生成 reply v3 或 Commit | 只在 `last_commit` 存在时显示最近提交摘要 | Artifact lineage/head、Verification、open Conflict gate 与 state hash 已有内存回归；PostgreSQL 待验 |

## 5. 异常与恢复路径

| 异常 | 服务端真值 | 用户反馈与动作 | 验收要求 |
| --- | --- | --- | --- |
| 证据冲突 | 单个 `BranchSnapshot.status=waiting_evidence` | 优先显示冲突摘要和解决动作；候选值与 Fixture `source_ref` 默认折叠 | PR 3 固定路径已覆盖；其他分支不得被暂停 |
| SSE 断线 | 业务状态不变，客户端仅失去更新 | 显示重新连接并禁用 Task Control | 已有自动重连、当前 Task 优先读取与 Snapshot 对账代码；完整浏览器断线 E2E 待补 |
| 旧版本控制 | `expected_task_version` 不等于当前版本 | 返回 `409`，刷新到当前 version 并要求复核 | API 与内存测试已覆盖；字段变更摘要和完整 E2E 待补 |
| 预算/截止时间不足 | 预计用量超契约或到期时在 mutation 前拒绝；`TaskBudgetSnapshot.exhausted` 字段存在 | 当前显示服务端拒绝原因 | 后端 gate 与内存测试已覆盖；专门的顶层/分支耗尽状态、缩小范围/申请额度和恢复 UI 未实现 |
| 权限不足 | 服务端拒绝控制或来源读取 | 保持只读，说明需要的角色或来源权限 | 当前只验证 Owner scope；生产 RBAC 未实现 |
| 进程重启 | 从持久 Snapshot、事件和工件版本恢复 | 继续显示同一 Task ID 和最后确认 Commit | 目标；PostgreSQL 本机运行与真实重启未验证 |
| 单分支失败 | 仅受影响分支 `failed` | 显示失败范围、最近 Commit 和恢复选项 | 目标，PR 3 未实现 |
| Take over | 分支进入 `taken_over` | 显示当前控制权和 Return control | 只实现状态机；人工编辑和新 ArtifactVersion 未实现 |
| Action Gate 打开 | RunSnapshot 进入等待证据、审批或授权 | Gate 使用独立网格行；Task 面板视觉隐藏且不可交互，但保持挂载以保留 Steer 草稿；Task Bar 操作禁用，Gate 收起后行高缩至 58px | 已实现交互互斥；Task Artifact 与 Action 失效尚未绑定 |

## 6. 前台信息层级

PR 3 默认展示：目标、Task ID、阶段、预算、分支状态、冲突摘要、待处理动作和最近 Commit。候选值与 Fixture `source_ref` 按需展开。

PR 4 目标展示：来源名称与更新时间、工件版本和历史、验证结果、Artifact head 与脱敏 Trace 摘要；这些不能写成 PR 3 已有前台事实。

默认隐藏：原始 Prompt、思维链、Worker 内部对话、JWT/Permit、幂等键、权限哈希、完整工具参数、密钥、堆栈、未脱敏个人信息和无决策价值的调度日志。

Task UI 与 Action Gate 必须各自读取服务端事实。Gate 打开时视觉隐藏 Task 明细、冻结控制但保留组件草稿，只是避免并发控制，不代表两条领域链已经建立版本绑定；在 Task Artifact 与 Action 参数哈希真正关联前，不能声称 Task 改动会自动使旧 Action 失效。

## 7. 验收指标

以下是实现验收目标，不是当前结果：

- 持久恢复：重启前后 Task ID、版本、Artifact head 和 state hash 一致率 `100%`。当前无 PostgreSQL 重启结果。
- 幂等恢复：重复命令、重复 resume 和网络重试导致的重复 ArtifactVersion/Commit 数为 `0`。原结果重放已有内存回归；PostgreSQL 重启待补。
- 分支隔离：收入冲突发生时，只有目标分支进入 `waiting_evidence`。固定 Fixture 内存测试已有阶段证据。
- 前后端一致：UI 终态与服务端 Snapshot 终态一致率 `100%`。当前有代码映射与截图，没有完整浏览器 E2E。
- 控制反馈：本地 Demo 的控制事件到可见服务端确认目标 `P95 ≤ 2s`。尚未采集时延分布。
- 用户理解、认知负担和接管效果尚未测量，不能在功能验收后自动宣称改善。

## 8. 证据位置

- 协议与状态机：[`TASK_RUNTIME_PROTOCOL.md`](../contracts/TASK_RUNTIME_PROTOCOL.md)
- UI—服务端事实：[`UI_SERVER_FACT_MATRIX.md`](../contracts/UI_SERVER_FACT_MATRIX.md)
- 设计来源：[`SOURCE_REGISTER.md`](../decisions/SOURCE_REGISTER.md)
- PR 3 运行证据：[`DEMO1-PR3-RUNTIME-EVIDENCE.md`](../evidence/DEMO1-PR3-RUNTIME-EVIDENCE.md)
- 后续实现证据：最终自动化测试、PostgreSQL 重启实验、完整浏览器 E2E 和用户研究；在产生前均标记为待验证。
