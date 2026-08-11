# SCENARIO-001：客户 A 经营汇报的受控持久任务

| 字段 | 内容 |
| --- | --- |
| Scenario ID | `SCENARIO-001` |
| Owner | Office Agent 项目组 |
| Status | `Ready` |
| Decision | [`DR-0002`](../decisions/DR-0002-bounded-durable-office-loop.md)、[`DR-0005`](../decisions/DR-0005-task-director-interaction.md) |
| 设计来源 | `USER-FEEDBACK-20260810-01/02`、`USER-FEEDBACK-20260811-INTERACTION-01`、`USER-FEEDBACK-20260811-USABILITY-02`、`USER-FEEDBACK-20260811-ROUND-AND-SOURCE-03`、`DESIGN-REFERENCE-TASK-DIRECTOR-OPTION2-20260811`、`TASK-DIRECTOR-USABILITY-AUDIT-DEMO1-PR6-20260811`、`TASK-DIRECTOR-ROUND-AND-SOURCE-CLARITY-20260811`、`MEETING-DECK-0716-V2-01`、`SCRIPT-V5-202607`、`REPO-BASELINE-84AABC9`、`REACT-ICLR-2023`、`LANGGRAPH-DURABLE-20260810`、`NIST-AI-RMF-1.0`；PR 5 运行来源为 `POSTGRES-WINDOWS-16.14-20260811`、`POSTGRES-BACKED-API-RESTART-DEMO1-PR5-20260811` |

## 1. 用户、触发与当前问题

目标用户是需要准备客户经营会材料的项目负责人或客户经理。触发条件是：经营会临近，用户要从邮件、CRM、预测表和项目周报中整理经营分析、风险页和客户回复草稿，并且任务可能跨越较长时间、设备切换和服务重启。

PR 3 之前的 V0.1 基线可以编辑工作区并治理一次副作用动作，但没有长期 Task、分支、工件版本和任务级控制事实。原流程只能看到一次对话或一次 Run，无法可靠判断：任务是否仍在推进、哪个分支被证据阻塞、其他分支是否安全继续、当前工件来自哪个版本，以及恢复后是否重复执行。

目标是让用户围绕同一个 Task ID 观察、纠偏和接管任务，并且只在服务端验证与提交完成后看到“完成”。DR-0005 当前把根路径改为业务任务：先说明要得到三项材料，空态一次点击创建并启动，冲突时解释原因与具体后果，完成后直接列成果；协议版本和审计信息下沉。该信息层级已通过工程代理回归，但是否帮助目标用户理解仍是 `Draft`，不改变服务端状态机。

## 2. 业务价值与明确边界

本场景验证的是固定 Fixture 下的任务协议、可持久状态模型、分支隔离、控制事件、交付物工作区和可验证提交。PR 5 已把 TaskStore 的持久性验证推进到同一 PostgreSQL 16.14 数据库上的顺序 API 进程恢复，但不验证 Conversation、数据库故障、真实客户数据接入、真实跨端身份、生产级多实例一致性或 Adaptive Swarm。当前 start 是一次同步 mutation，不是后台持续调度器。

- 所有邮件、CRM、金额、项目和客户名称都是 Demo Fixture。
- 普通业务 UI 将已知来源明确标为“演示数据”并使用业务名称；本文件保留原始 `source_ref` 只是为了记录协议与审计事实，不代表这些内部 ID 应显示给用户。
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

| 阶段 | 服务端行为 | Task Director 前台输出 | 当前证据与边界 |
| --- | --- | --- | --- |
| Contract | 创建稳定 `TaskContract`、Task ID、三个分支和预算 | 初始列表完成前显示读取态；无 Task 时固定空态说明三项成果，一次点击依次创建并启动；已有 Task 显示目标与业务下一步，版本/预算进入审计 | 已实现：`TASK_CREATED` + `TaskSnapshot.version=1`；空态是固定 Demo 创建模板副本，通用模板接口尚未实现 |
| Observe | 从四个代码内固定 Fixture `source_ref` 生成 Observe Trace | 不显示原始 Prompt 或内部推理 | 已产生 `LOOP_STEP_STARTED/COMPLETED`；不是真实 Connector 读取 |
| Plan | 为三个固定交付物记录分支运行 Trace | 阶段轨与三个 Branch 泳道在 start 响应后显示服务端终态 | 已产生 `BRANCH_STATUS_CHANGED`；事务中间态不对浏览器逐步可见，阶段轨不能冒充流式进度 |
| Act | 由确定性代码生成候选工件 | 泳道从 Branch head 打开共享工件，查看 v/status、结构化内容与 lineage | 服务端已产生 `ARTIFACT_VERSION_CREATED`；PR 6 E2E 覆盖经营分析 v1、follow-head 与历史版本，不来自 LLM |
| Verify | 发现 2,400 万与 2,680 万冲突，只阻塞经营分析分支 | 待确认区说明为什么需要人、两个口径、经营分析/回复草稿会如何更新、风险页保持状态，以及唯一 resolve 主动作 | 当前 E2E 与冲突截图已覆盖固定 Fixture；不证明真实来源、业务收益或用户决策质量 |
| Control | 用户选择正式口径，或提交分支控制 | 只有服务端 Snapshot 确认后才更新；补证按钮先准备 Steer，提交后也只称已记录待应用 | Resolve/分支控制已有事实；Steer 重新规划尚未实现 |
| Commit | 解决最后一个 open Conflict 时重新验证经营分析，并联动重生成、验证客户回复后再生成 TaskCommit；若仍有其他冲突则不生成 reply v3 或 Commit | 只在 `last_commit` 存在时列出经营分析、风险页、客户回复草稿三项可复核成果，并明确回复未发送；版本和 state hash 收进审计 | 内存与 PostgreSQL 跨 API 进程回归、真实本地浏览器主路径已覆盖；不代表发送邮件或数据库故障恢复 |
| New round | 终态以新 round key 创建独立 Task，再对新 Task 执行 start；旧轮次不 mutation | “开始新一轮汇报”一次点击后进入新一轮待确认状态；不是把旧 Task 重置为 ready | 完整浏览器 E2E 已覆盖新旧 Task 同时保留；当前没有历史轮次选择入口，不证明用户理解该语义 |

## 5. 异常与恢复路径

| 异常 | 服务端真值 | 用户反馈与动作 | 验收要求 |
| --- | --- | --- | --- |
| 证据冲突 | 单个 `BranchSnapshot.status=waiting_evidence` | 优先显示冲突摘要和解决动作；工件区同步显示冲突，Fixture `source_ref` 默认折叠 | PR 3 内存测试与 PR 4 浏览器主路径已覆盖；其他分支不得被暂停 |
| SSE 断线 | 业务状态不变，客户端仅失去更新 | 顶部和 Task 面板一致显示恢复中，保留最后 Snapshot 并禁用 Task Control | PR 5 已通过停止 API 进程验证同页断线、自动重连和 GET 对账；停机期间无新事件，`after` 缺口回放仍待补 |
| start 发送前失败 | 服务端仍为 v1、0 个 ArtifactVersion | 显示结果待确认，保存原 key，reload 后允许立即对账 | PR 4 E2E 已覆盖；同 key 重试后为 v2、5 个唯一工件 |
| 服务端已提交但响应丢失 | 幂等 marker 保存首次结果，浏览器尚未知 | 应用原 key 查询首次结果，再 GET 最新 Snapshot | 后端内存测试有幂等证据，但该浏览器路径未测试，不能与发送前 abort 混同 |
| 旧版本控制 | `expected_task_version` 不等于当前版本 | 返回 `409`，刷新到当前 version 并要求复核 | API、内存测试与当前 PR 6 浏览器回归已覆盖版本提示、复核和重试成功；字段级变更摘要与重新应用入口仍待补 |
| 预算/截止时间不足 | 预计用量超契约或到期时在 mutation 前拒绝；`TaskBudgetSnapshot.exhausted` 字段存在 | 当前显示服务端拒绝原因 | 后端 gate 与内存测试已覆盖；专门的顶层/分支耗尽状态、缩小范围/申请额度和恢复 UI 未实现 |
| 权限不足 | 服务端拒绝控制或来源读取 | 保持只读，说明需要的角色或来源权限 | 当前只验证 Owner scope；生产 RBAC 未实现 |
| 进程重启 | 从持久 Snapshot、事件和工件版本恢复；重启本身不新增业务事件 | 继续显示同一 Task ID、v2 冲突或 v3 Commit；恢复前控制禁用 | PR 5 已在 PostgreSQL 16.14、三个顺序 API 进程上验证 v2/v3；Conversation、数据库重启/崩溃和多实例并发未覆盖 |
| 单分支失败 | 仅受影响分支 `failed` | 显示失败范围、最近 Commit 和恢复选项 | 目标，当前未实现 |
| Take over | 分支进入 `taken_over` | 显示当前控制权和 Return control | 只实现状态机；人工编辑和新 ArtifactVersion 未实现 |
| 固定查看历史工件 | Branch head 已前进，但用户主动选择旧 ArtifactVersion | 显示“正在查看历史版本”、当前 head 版本和返回动作；默认 mutation 后自动跟随新 head | PR 6 专用 E2E 与历史截图已验证 `follow_head/pinned_history`；仍未测量目标用户误读率 |
| 多轮 Task 历史 | `GET /tasks` 返回当前 Owner 的多轮 Snapshot | 默认恢复最近活动 Task，否则显示最近终态 Task | 当前没有历史轮次选择器；旧轮次保留不等于用户可从 UI 自由切换 |
| Action Gate 打开 | RunSnapshot 进入等待证据、审批或授权 | Gate 使用独立网格行；Task 面板视觉隐藏且不可交互，但保持挂载以保留 Steer 草稿；Task Bar 操作禁用，Gate 收起后行高缩至 58px | 已实现交互互斥；Task Artifact 与 Action 失效尚未绑定 |

## 6. 前台信息层级

进度页默认展示：业务目标、三项材料、当前主要下一步、材料核对数、用户语言阶段、当前材料、验证/冲突和是否纳入成果。预算、Owner 与内部步数从业务主路径隐藏；同步版本只用于说明浏览器已对账到哪个服务端状态，不能在断线时写成任务仍在推进。Tasks 右侧默认呈现“现在需要你做什么”，用户可切到既有 Agent 对话；模式切换不重建 Conversation，也不产生 TaskEvent。邮件等非 Tasks 工作区只显示后台任务摘要与返回 Tasks 的入口，不复刻待确认卡或控制。

Tasks 视图用“进度 / 成果 / 执行记录”三个模式保留长期 Task 与手工待办。成果默认跟随 Branch head；主动选择旧版本时显示历史 banner。人工编辑 Task Artifact、创建新 ArtifactVersion、通用 Trace 浏览器和异常恢复中心仍是后续目标。

默认隐藏：原始 Prompt、思维链、Worker 内部对话、JWT/Permit、幂等键、权限哈希、完整工具参数、密钥、DSN、堆栈、未脱敏个人信息和无决策价值的调度日志。三个固定 Artifact kind 使用字段 allowlist，未知 kind/字段默认隐藏；Conflict Card 与 Artifact Workspace 共用 `source_ref` 投影，四个已知 Demo 1 值显示为带“演示数据”前缀的业务标签，普通业务 DOM 使用序号 key，不接收原始 ID，其他值 fail closed。这是前端第二道投影，不替代服务端授权、脱敏或未来通用字段可见性 Schema；允许字段中的任意文本仍需服务端保证。

Task UI 与 Action Gate 必须各自读取服务端事实。Gate 打开时视觉隐藏 Task 明细、冻结控制但保留组件草稿，只是避免并发控制，不代表两条领域链已经建立版本绑定；在 Task Artifact 与 Action 参数哈希真正关联前，不能声称 Task 改动会自动使旧 Action 失效。

## 7. 验收指标

以下同时列出验收目标与截至 PR 6 的限定结果：

- 持久恢复：重启前后 Task ID、版本、Artifact head 和 state hash 一致率目标 `100%`。PR 5 的固定 Fixture 在 v2/v3、三个顺序 API 进程的逐字段比较为 `100%`；不能外推到未测场景或生产总体。
- 幂等恢复：重复命令、重复 resume 和网络重试导致的重复 ArtifactVersion/Commit 数目标为 `0`。PR 5 在重启后重放旧 start/resolve key，新增 Event/ArtifactVersion/Commit 均为 `0`；响应丢失浏览器路径仍待补。
- 分支隔离：收入冲突发生时，只有目标分支进入 `waiting_evidence`。固定 Fixture 内存测试已有阶段证据。
- 前后端一致：UI 终态与服务端 Snapshot 终态一致率目标 `100%`。PR 5 的服务端 Snapshot 在 v2/v3 跨 API 进程比较中逐字段一致；PR 6 最终 E2E 又断言 Task Director 标题/阶段/分支/冲突/Commit、控制反馈、follow-head 与历史状态。尚未对 UI 全字段投影或所有错误状态、事件缺口、响应丢失做总体测量，不能宣称总体 100%。
- 前台工程闭环：原 PR 6 基线为全量浏览器 `6 passed (34.5s)`；当前可理解性修订为 `12 passed (43.7s)`。新增单次开始、加载防重复创建、无任务离线一致性、快速重复开始只产生一次 create/start、同分支多冲突顺序与阶段后果、终态优先、具体后果、三项成果和 `1181 x 900` 溢出断言，既有乱序 Snapshot、`409`、移动、历史和 source-ref 回归继续通过。该结果不证明用户理解或效率提升，`DR-0005` 保持 `Draft`。
- 来源与新一轮修订：完整浏览器 E2E `12 passed (44.5s)`，覆盖非 Tasks 摘要/跳转、已知来源的“演示数据”标签与原始 ID 不入 DOM、新一轮 create+start 和旧 Task 保留；`1440 x 900` Mail 截图记录摘要层级。该结果仍不证明用户理解，历史轮次选择入口未实现。
- 控制反馈：本地 Demo 的控制事件到可见服务端确认目标 `P95 ≤ 2s`。尚未采集时延分布。
- 用户理解、认知负担和接管效果尚未测量，不能在功能验收后自动宣称改善。

## 8. 证据位置

- 协议与状态机：[`TASK_RUNTIME_PROTOCOL.md`](../contracts/TASK_RUNTIME_PROTOCOL.md)
- UI—服务端事实：[`UI_SERVER_FACT_MATRIX.md`](../contracts/UI_SERVER_FACT_MATRIX.md)
- 设计来源：[`SOURCE_REGISTER.md`](../decisions/SOURCE_REGISTER.md)
- PR 3 运行证据：[`DEMO1-PR3-RUNTIME-EVIDENCE.md`](../evidence/DEMO1-PR3-RUNTIME-EVIDENCE.md)
- PR 4 前端 E2E 证据：[`DEMO1-PR4-FRONTEND-E2E-EVIDENCE.md`](../evidence/DEMO1-PR4-FRONTEND-E2E-EVIDENCE.md)
- PR 5 PostgreSQL-backed API 重启证据：[`DEMO1-PR5-POSTGRES-BACKED-API-RESTART-EVIDENCE.md`](../evidence/DEMO1-PR5-POSTGRES-BACKED-API-RESTART-EVIDENCE.md)
- PR 6 Task Director 运行与视觉证据：[`DEMO1-PR6-TASK-DIRECTOR-INTERACTION-EVIDENCE.md`](../evidence/DEMO1-PR6-TASK-DIRECTOR-INTERACTION-EVIDENCE.md)
- PR 6 可理解性验收与工程代理证据：[`DEMO1-PR6-USABILITY-COMPREHENSION-AUDIT-20260811.md`](../evidence/DEMO1-PR6-USABILITY-COMPREHENSION-AUDIT-20260811.md)
- 来源与新一轮修订证据：[`DEMO1-ROUND-AND-SOURCE-CLARITY-EVIDENCE-20260811.md`](../evidence/DEMO1-ROUND-AND-SOURCE-CLARITY-EVIDENCE-20260811.md)
- 后续实现证据：响应丢失、断线期间事件回放、数据库故障/迁移、多实例、Artifact/Action 绑定和用户研究；在产生前均标记为待验证。
