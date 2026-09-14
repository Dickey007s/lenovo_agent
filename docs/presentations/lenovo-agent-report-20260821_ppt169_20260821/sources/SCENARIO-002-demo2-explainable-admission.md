# SCENARIO-002：智能工作驾驶舱的可解释 Admission 与受控内部执行

| 字段 | 内容 |
| --- | --- |
| Scenario ID | `SCENARIO-002` |
| Decision | [`DR-0008`](../decisions/DR-0008-demo2-explainable-admission.md)、[`DR-0011`](../decisions/DR-0011-demo2-route-impact.md)、[`DR-0015`](../decisions/DR-0015-mainstream-comparison-and-demo2-controlled-execution.md) |
| Status | Admission/路由 `Verified`；固定客户 A 受控内部执行 `Limited Verified` |
| Owner | Office Agent 项目组 |
| Scope | 固定演示队列、路由解释、仅本次选择，以及固定客户 A 的单 API 进程 memory 受控模型 Worker/共享工件/动态增派/完成回执 |
| 当前性质 | 已实现并验证固定纵切；不是通用 Adaptive Swarm、跨进程 Runtime、真实 Connector，也不证明用户价值 |

## 1. 目标用户与触发条件

目标用户是需要同时处理客户、项目、内部流程和日程的销售负责人或项目负责人。用户在一天开始或临近多个截止时间时打开智能工作驾驶舱，提出“看看今天重点”或直接进入今日工作视图。

当前痛点是工作信号分散在邮件、CRM、项目、报销和日历中。用户不仅不知道先处理什么，也不知道 Agent 为什么选择某种执行方式；如果系统直接展示多个 Worker，用户还需要理解一套与业务目标无关的内部调度语言。

本场景的目标不是证明“多 Agent 越多越好”，而是让用户先看懂：今天有哪些工作、每项工作准备采用什么方式，以及用户能否只改变本次路由选择。

## 2. 完成条件

本轮必须由服务端 Snapshot 或有序事件驱动以下事实：

1. 固定演示来源标签由服务端随工作项返回，并在普通 UI 明确“演示数据”性质。
2. 四项固定演示任务具有稳定的业务标题、截止压力、来源范围和路由解释；本纵切使用服务端提供的固定队列，不声称实现排序调序。
3. 三项简单任务的初始路由由 Admission 固定提供：Tool Call、Single Agent、Fixed Workflow；客户 A 经营汇报暂不自动选择，进入待决定状态，并允许 Single Agent、Fixed Workflow、Adaptive Swarm 三种模式。
4. 用户可以将客户 A 的模式选择限定为“仅本次运行”，服务端返回新的 WorkCockpitSnapshot 版本和幂等结果；本纵切不实现拖拽排序或长期排序偏好。
5. Adaptive Swarm 在路由选择完成后必须先保持 `execution_status=not_started`；只有用户另行启动且版本匹配，才创建独立执行 Snapshot。
6. Admission 展示 Value、Breadth、Parallelism、Deadline、Risk、Budget 六类依据。`route_profiles[].forecast.source_type` 固定为 `fixture_policy_forecast`，不写成实测成本、实测时延或生产 SLA。
7. 每个允许模式由服务端给出影响预演，至少覆盖工作分配、协调、人工介入、规则预测、执行边界与外部动作边界；前端不得根据模式名自行补造。
8. 确认后产生服务端选择回执与连续历史。左侧显示实际变化，右侧显示精简回执；同模式重复、缺 route profile/preview 均失败且不增加版本。
9. 固定客户 A 启动后产生三个初始业务工作单元；文件事实中的收入口径冲突触发 sequence 9 重排和 sequence 10 增派第四个核验单元。
10. 完成时产生 4 个 Worker、5 个 SharedArtifactVersion 与 sequence 15 完成回执；`external_side_effect=none` 明确没有外部写入。

## 3. 固定演示任务

以下四项任务是本轮确定性 Fixture，不代表真实企业任务列表：

| 业务任务 | 业务信号 | 建议路由 | Swarm 状态 | 执行状态 |
| --- | --- | --- | --- | --- |
| 客户 A 经营汇报 | 今日截止、业务价值高、跨邮件/CRM/项目周报/日历核对 | 待决定；允许 Single Agent / Fixed Workflow / Adaptive Swarm | Adaptive Swarm 可由用户仅本次选择并独立启动 | WorkItem 先为 `not_started`；当前整轮 Execution 可达 `queued/running/verifying/completed/failed`；Execution cancel 为 Draft；Worker 无 `verifying/waiting_input` |
| 供应商邮件回复 | 今日需形成一版独立草稿 | Single Agent | Admission 固定路由 | `not_started` |
| 周报格式统一 | 明早前完成的稳定重复整理 | Fixed Workflow | Admission 固定路由 | `not_started` |
| 报销异常核查 | 待补证据的单项查证 | Tool Call | Admission 固定路由 | `not_started` |

“成本”和“时效”在本场景中只表示演示策略给出的预估标签或区间。当前受控执行有真实模型调用耗时和执行墙钟观测，但没有 Connector 访问、计费记录、生产基线或 SLA，不能显示“节省了多少成本”或“快了多少”。

## 4. 核心流程

1. **读取固定队列**：驾驶舱 GET 当前 Owner 的四项固定演示任务；返回前只显示读取态。
2. **查看工作条件**：服务端给出固定队列顺序、业务价值、资料广度、可并行工作包、截止压力、风险和资源边界；本纵切不宣称动态排序。
3. **解释与预演**：用户查看路由依据和允许模式；切换模式时，左侧立即显示服务端给出的工作影响，而不是模型思维链或内部评分过程。
4. **本次选择**：客户 A 用户在看见 `before → after` 后确认某个允许模式，选择范围限定为“仅本次运行”；本纵切不实现拖拽调序或长期排序偏好。
5. **路由预览**：四项任务同时展示服务端推荐路由和业务含义。三项简单任务已按 Admission 固定路由，客户 A 保持待决定；路由选择不等于开始执行。
6. **Admission**：用户打开客户 A 的 Admission，查看六类依据、演示预算与预计等待标签；可以选择推荐的 Adaptive Swarm、降级到 Single Agent/Fixed Workflow 或暂不选择。
7. **选择来源**：选择推荐的 Adaptive Swarm 时 `selection_source=admission`；用户降级时 `selection_source=user_override`，并记录 `override_scope=this_run`。
8. **停在执行前**：用户选择 Adaptive Swarm 后先显示“已选择，尚未启动执行”，并保持 `execution_status=not_started`。
9. **独立启动**：用户明确启动后，服务端校验 Owner、版本、幂等键、模式和演示来源，再创建 `Demo2ExecutionSnapshot`。
10. **受控并行与重排**：三个初始工作单元并行处理；服务端从文件事实识别收入冲突，产生 sequence 9 重排和 sequence 10 增派收入口径核验。
11. **共享收敛**：每个工作单元写入带来源、版本和 digest 的共享工件；最终确定性汇总与验证形成第 5 个工件。
12. **完成回执**：sequence 15 完成后，前端只根据 `ExecutionReceipt` 显示内部工件包完成和 `external_side_effect=none`；外部业务动作另进 Demo 3。

## 5. 关键异常路径

| 异常 | 前台恢复 | 服务端边界 |
| --- | --- | --- |
| 驾驶舱 GET 失败 | 保留已显示的最后 Snapshot，提供重新读取 | 不补造来源、任务数量或选择状态 |
| 路由选择版本过期 | 保留用户本次选择草稿，读取最新 Snapshot 后让用户复核 | `expected_version` 不匹配时返回冲突，不静默覆盖 |
| 所选模式不在允许范围 | 保留当前 Snapshot 与草稿，提示重新复核允许模式 | 返回 409，不产生 Worker，不静默选择其他模式 |
| 路由 profile 或影响预演缺失 | 显示“影响预演暂不可用”并禁用确认 | 返回 409，cockpit/item 版本不变，不由前端填补 |
| 重复确认同一模式 | 保持已记录回执与版本，按钮不可再次提交 | 新幂等键也返回 409，不制造“无变化”的变化记录 |
| 选择结果未知 | 显示“结果待确认”，使用同一幂等键对账 | 不按网络异常宣布失败或成功 |
| API 进程重启 | 重新 GET 固定初始 Snapshot，并明确当前选择不具备恢复证据 | 当前 memory 选择会丢失；不伪装成跨进程恢复 |
| 执行启动重复/版本过期 | 保留当前选择和页面事实，GET 最新 WorkItem/Execution 对账 | 同命令幂等重放；冲突返回 409，不重复创建执行 |
| 来源缺失、篡改或运行中变化 | 显示执行失败与重新核对来源，不用旧工件冒充完成 | manifest/摘要校验 fail closed；不产生完成 receipt |
| Worker 失败 | 显示失败工作单元与整轮终态，保留已形成的只读事实 | 服务端终止整轮并取消未完成兄弟；不生成成功回执 |
| SSE 中断/事件缺口 | 显示“状态待核对”并重新 GET 完整 Snapshot | sequence 是顺序事实；前端不自行补事件或宣布完成 |

## 6. 前台与后台边界

前台展示任务目标、来源性质、固定队列位置、路由解释、允许模式、六类 Admission 依据、演示预算/时效预测、当前版本和待用户决定。前台不展示原始 Prompt、思维链、Worker 对话、内部 Worker 名称、原始 `fixture:` ID、密钥、Token、Permit、底层日志或无决策价值的调度噪声。

本场景的“已选择 Adaptive Swarm”只表示用户对本次路由作出选择；“已启动/运行中/验证中/已完成”必须来自独立 execution Snapshot 和有序事件。即使内部状态 completed，也必须同时显示 `external_side_effect=none`，不得表述成真实邮件、CRM、OA、日历或任务系统已写入，更不得推断节省成本。

## 7. 来源与局限

- `USER-FEEDBACK-20260810-02`：要求同时补充场景、来源、前台交互和前后端统一；不证明 Demo 2 已实现。
- `MEETING-DECK-0716-V2-01`：0716-v2 原始阶段汇报；支持三 Demo 方向和八个常驻组件背景，不证明 Runtime 或用户效果。
- `SCRIPT-V5-202607`：P20、P18-P22 描述驾驶舱、排序、分流、Admission、Shared Artifact Workspace 与返回驾驶舱叙事；属于内部设计输入，不是运行证据。
- `TARGET-ARCHITECTURE`：第 5、6、7、8、10 节定义 Admission、四种路由、前端事实映射和先单任务后 Swarm 的顺序；仍是目标架构。
- `USER-FEEDBACK-20260817-01`：要求继续推进并关注协作成本；不提供成本、时效或质量实测。
- `USER-FEEDBACK-20260820-03`：把创新前端与 Agent 操作影响可见设为第一目标；是 Stakeholder 方向，不证明当前方案有效。
- `HAI-GUIDELINES-CHI2019`、`GOOGLE-PAIR-FEEDBACK-CONTROL-2021`：支持及时说明系统能力、状态和选择影响；通用研究/设计实践不替代本项目工程证据或用户研究。

当前已有 Admission/route 协议、API、影响预演/回执，以及固定客户 A 的受控执行 Snapshot、真实模型 Worker、共享工件、有序 SSE、固定冲突重排和完成回执。两轮 live 模型与六张截图见 [`DEMO2-CONTROLLED-EXECUTION-20260821`](../evidence/DEMO2-CONTROLLED-EXECUTION-EVIDENCE-20260821.md)。没有目标用户研究、真实 Connector、跨进程恢复、真实计费、成本/质量基准或生产时延 SLA；因此执行只标 `Limited Verified`，不能升级为通用 Adaptive Swarm 或用户价值已验证。

## 8. 从 Admission 到受控内部执行（Limited Verified）

### 8.1 新场景

目标用户仍是需要组织客户经营汇报的销售负责人或项目负责人。用户在客户 A 的 Admission 页面确认 Adaptive Swarm 后，可以独立启动受控协作；系统把经营汇报拆成收入事实、项目风险、客户要求三个初始工作单元，并因文件收入口径冲突增派核验单元。服务端生成带来源、版本和 digest 的共享工件，产生有序启动、完成、重排、增派、验证和完成事实；最终停在“内部工件包已完成、未触发外部动作”。

关键异常路径包括：来源版本变化、Worker 超时/失败、共享工件字段冲突、预算耗尽、断线/重启和执行结果未知。前台只停止受影响工作单元，保留已验证工件和用户草稿；不能用汇总 Agent 的文字覆盖冲突，也不能用动画假装完成。

### 8.2 Admission→执行 UI—后端事实矩阵草案

| UI 状态 | 用户可见内容/动作 | 服务端事实来源 | 有序事件与版本 | 状态 |
| --- | --- | --- | --- | --- |
| 推荐协作方式 | 看 Value/Breadth/Parallelism/Deadline/Risk/Budget 和组织预演；改选/暂不确认 | `WorkCockpitSnapshot`、`RouteProfile.impact_preview` | `cockpit_version`、`expected_version` | 限定范围 Verified |
| 已确认本次方式 | 看“本次已选择”，知道还没有执行结果；可启动 | `WorkItemSnapshot.selection_receipt/execution_status` | 选择与启动分别使用版本/幂等 | 限定范围 Verified |
| 协作已启动 | 看三个初始工作单元和依赖关系 | `Demo2ExecutionSnapshot.workers/events` | `EXECUTION_STARTED/WORKER_STARTED` + sequence | Limited Verified |
| 处理中 | 看阶段、模型调用事实、最近工件和等待原因，不看 Prompt/日志 | `workers[].processing`、`SharedArtifactVersion[]` | GET + SSE；artifact version/digest | Limited Verified |
| 动态重排 | 看为何增派收入口径核验 | `SwarmEvent.details`、新增 Worker | seq 9 `DYNAMIC_REPLAN`、seq 10 `WORKER_ADDED` | 固定冲突触发 Limited Verified |
| 已验证汇总 | 看 5 个共享工件、来源和验证状态 | `SharedArtifactVersion[]`、`ExecutionReceipt` | `ARTIFACT_VERIFIED`、seq 15 `EXECUTION_COMPLETED` | Limited Verified |
| 外部动作边界 | 明确“未触发外部动作”；另行进入 Demo 3 | `ExecutionReceipt.external_side_effect=none` | 内部完成不自动执行外部动作 | Limited Verified |
| 失败/恢复 | 来源或 Worker 失败时看终态；断线后 GET 对账 | failed Snapshot/Event | 单进程恢复有限；跨进程 Draft | 部分自动化；生产 Draft |

前端不得以 Worker 数量、客户端计时器、模型名或 HTTP 成功自行推断执行状态；缺少 Snapshot、事件或回执时必须显示“状态待核对”。Worker 对话、原始 Prompt、思维链、密钥和内部调度噪声只在受控技术审计面保留。

### 8.3 设计来源与待验证项

- `MEETING-DECK-0716-V2-01` 与 `SCRIPT-V5-202607`：支持 Demo 2 蜂群协作与八模块的阶段方向，不证明执行已实现。
- `COMPETITOR-RESEARCH-OPENCLAW-CODEX-CLAUDE-CODE-20260821`：支持主流方案已有多 Agent、后台、权限和可观察性，促使差异落在业务事实、共享工件和影响回执；不是竞品实测。
- `USER-FEEDBACK-20260821-07`：要求技术差异转成交互影响并保留场景与来源；单一 Stakeholder 反馈，不证明理解或效果。
- `HAI-GUIDELINES-CHI2019`、`GOOGLE-PAIR-FEEDBACK-CONTROL-2021`：支持及时反馈、状态解释和用户控制；通用设计依据，不替代本项目用户研究。

固定客户 A 受控内部执行已经有 Worker、共享工件、重排、真实模型和浏览器 Evidence，因此可在严格范围内说“Adaptive Swarm 受控执行已启动并完成”。不能写“通用动态调度已实现”，也不能把工程证据改写成用户理解、质量、成本或时延改善。
