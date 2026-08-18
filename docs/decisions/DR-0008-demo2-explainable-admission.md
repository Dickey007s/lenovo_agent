# DR-0008：Demo 2 先实现可解释 Admission 与仅本次路由选择

| 字段 | 内容 |
| --- | --- |
| Decision ID | `DR-0008` |
| Owner | Office Agent 项目组 |
| Date | 2026-08-17 |
| Status | `Verified`（限定范围） |
| Scope | Demo 2 第一纵切：智能工作驾驶舱的固定演示队列、路由解释、仅本次路由选择与服务端驱动 Admission 预览 |
| Depends on | `DR-0002`、`DR-0005`、`TARGET_ARCHITECTURE`、`SCENARIO-002`、`UI_SERVER_FACT_MATRIX` |
| Explicit non-goal | 本轮不实现真实 Adaptive Swarm、动态 Worker、真实 Connector、真实成本/时效测量或生产调度器 |

## 1. 用户场景与问题

目标用户是需要同时处理客户、项目、报销和日程事项的销售负责人或项目负责人。用户打开驾驶舱后，希望知道今天最应该先做什么、排序依据是什么，以及每项工作应该用简单查询、单 Agent、固定流程还是复杂协作来准备。

此前系统已验证 Demo 1 的单任务持续状态和 Demo 3 的动作治理，但尚未形成 Demo 2 的服务端多工作项与路由事实。本决策已补上固定驾驶舱和 Admission 纵切；若继续直接展示动态 Worker，用户仍会先看到后台组织形式而不是业务价值，同时当前也没有真实 Worker、Connector、成本或时效证据。

完成条件是：服务端返回四项固定演示任务、固定队列位置、路由解释和 Admission 依据；三项简单任务按 Admission 固定路由，客户 A 进入待决定并允许三种模式；用户可将客户 A 的模式选择限定为本次运行；选择 Adaptive Swarm 后仍保持 `execution_status=not_started`，明确停在执行边界。本纵切不实现拖拽调序或长期排序偏好。

关键异常包括初始读取失败、版本过期、不允许的选择、选择结果未知和 API 进程重启。异常不得由前端补造或静默重试为另一种业务含义。

## 2. 来源与依据

| Source ID | 类型 | 精确引用 | 支持判断 | 局限 |
| --- | --- | --- | --- | --- |
| `USER-FEEDBACK-20260810-02` | Stakeholder 会后反馈 | [`USER-FEEDBACK-20260810-02-0716-v2-follow-up.md`](../sources/USER-FEEDBACK-20260810-02-0716-v2-follow-up.md)，Demo 2 与“下一步重点”原文 | 方案必须同时补充场景、来源、交互影响和前后端统一 | 用户摘要，不是签字纪要或用户研究 |
| `MEETING-DECK-0716-V2-01` | 阶段汇报原件 | `docs/final-reference/0716-v2.pptx`，SHA 与文件清单见 [`final-reference/README.md`](../final-reference/README.md) | 三 Demo 和八个常驻组件的阶段方向 | 原件年份存在上下文歧义，不证明实现 |
| `SCRIPT-V5-202607` | 内部设计讲稿 | [`未来办公Agent_一小时汇报讲稿_v5.md`](../final-reference/未来办公Agent_%E4%B8%80%E5%B0%8F%E6%97%B6%E6%B1%87%E6%8A%A5%E8%AE%B2%E7%A8%BF_v5.md)，P18-P22 | 支持四种执行方式、Admission、驾驶舱排序解释和结果回收的产品叙事 | 内部设计输入，不是运行证据 |
| `TARGET-ARCHITECTURE` | 仓库目标架构 | [`TARGET_ARCHITECTURE.md`](../TARGET_ARCHITECTURE.md):71-91、101-140、174-182 | 支持 Swarm 按需路由、六类 Admission 依据、前后端事实映射和先单任务后 Swarm 的顺序 | 目标能力，不能写成当前实现 |
| `USER-FEEDBACK-20260817-01` | Stakeholder 推进与成本偏好 | [`USER-FEEDBACK-20260817-01-demo2-continued-iteration.md`](../sources/USER-FEEDBACK-20260817-01-demo2-continued-iteration.md) | 支持继续推进并保持成本敏感的协作方式 | 不提供业务成本、时效或质量测量 |

## 3. 决策与备选

采用“驾驶舱先于 Swarm”的最小纵切：

1. 使用四项固定演示任务和服务端固定队列，先让用户看懂统一任务卡、路由解释和业务状态。
2. 三项简单任务由 Admission 固定路由；客户 A 不自动选择，服务端返回允许的 Single Agent、Fixed Workflow、Adaptive Swarm 三种模式。
3. 复杂任务进入服务端 Admission 预览，至少记录 Value、Breadth、Parallelism、Deadline、Risk、Budget 六类依据。
4. 客户 A 的模式选择只在本次运行生效。选择推荐的 Adaptive Swarm 时 `selection_source=admission`；降级到其他允许模式时 `selection_source=user_override`，并记录 `override_scope=this_run`。
5. Adaptive Swarm 只有“推荐”或“本次已选择”两种业务选择状态；`execution_status` 固定为 `not_started`。
6. 成本与时效只能使用 `route_profiles[].forecast` 展示，且 `source_type=fixture_policy_forecast`；UI 必须标注为规则预测，不得伪装成模型账单、真实 Worker 运行或实测 SLA。

未采用以下方案：

- **先做动态 Worker**：当前没有通用 Worker 生命周期、共享工件、Verifier/Resolver 运行证据；会把用户价值问题隐藏在内部调度中。
- **只改静态 HTML**：不能证明 Snapshot、版本、幂等和恢复语义，且违反前后端统一门槛。
- **让前端自行打分或决定路由**：会把队列、预算和 Admission 真值放到浏览器，无法审计或恢复。
- **把“已选择”写成“已启动”**：会把用户偏好与执行事实混为一谈。

## 4. 后端事实与当前协议

当前已新增独立 `Demo2CockpitService` 与服务端拥有的 `WorkCockpitSnapshot`，没有复用可编辑的 `WorkspaceArtifact(kind=tasks)` 作为编排真值。服务端只使用 memory；持久化与跨进程恢复不属于本纵切。当前字段包括：

| 事实 | 当前字段 | 语义 |
| --- | --- | --- |
| 驾驶舱版本 | `WorkCockpitSnapshot.owner_id/backend/version/last_event_sequence` | 固定队列和路由选择绑定的服务端版本；`backend=memory` |
| 来源标签 | `WorkCockpitSnapshot.items[].facts.source_labels` | 每个固定任务的演示来源业务标签，不包含原始内部 ID |
| 固定队列 | `WorkCockpitSnapshot.items[]` 的服务端顺序 | 本纵切只展示服务端提供的固定队列；拖拽调序留后续，不作为当前事实 |
| 路由建议 | `items[].recommendation/allowed_modes/route_profiles` | 服务端 Admission 建议、六类理由、允许模式和每种模式的业务解释/规则预测 |
| 路由选择 | `items[].selected_mode/selection_source/override_scope` | 推荐选择来自 `admission`；其他允许选择来自 `user_override`，范围为 `this_run` |
| 规则预测 | `items[].route_profiles[].forecast` | `source_type=fixture_policy_forecast` 与工具次数、秒数、并行上限；不是实测 |
| 执行边界 | `items[].execution_status` | 本轮固定为 `not_started`；没有 Worker 运行事实就不能显示其他状态 |
| WorkItem 版本 | `items[].version/last_event_sequence/last_event_type` | 每个任务 Admission 与选择状态的版本和事件类型 |

本纵切路由选择 mutation 必须带 `expected_version`、`scope=this_run` 与 `idempotency_key`；服务端返回 `RouteSelectionResult.cockpit_version/cockpit_last_event_sequence/item` 后，前端才同时更新驾驶舱聚合版本与客户 A 的选择，不自行推算版本。版本冲突时保留本地选择草稿并重新 GET Cockpit；未知结果先 GET 对账，不凭客户端错误宣布结果。当前没有 Demo 2 SSE。未来若真的启动 Worker，还必须另建执行事件、预算消耗、工件版本、Verifier 和恢复证据，不能由本决策的 `selected_mode` 状态推断。

## 5. 前台输出与隐藏边界

驾驶舱首屏展示“今天有哪些工作、为什么建议这样处理”；任务卡显示业务标题、固定队列位置、截止压力、来源性质、业务影响、建议路由和当前选择范围。展开 Admission 时显示六类业务依据、演示策略预测和“选择后尚未启动执行”的边界。

用户可执行：查看路由解释、接受客户 A 的推荐模式、将客户 A 降级到其他允许模式、暂不选择、查看演示来源和重新对账。本纵切不提供拖拽调序或长期排序偏好。动作反馈必须区分“推荐”“本次已选择”“执行未启动”“结果待确认”。

默认隐藏：原始 Prompt、思维链、Worker 对话、Worker 内部名称、原始 `fixture:` ID、模型 Token、Permit、底层日志、网络重试、策略内部权重和无业务含义的调度图。技术审计信息只能在受控审计视图中开放。

固定四项任务及来源均为演示数据。普通 UI 不得显示原始内部来源 ID；成本和时效必须标为演示策略预测，不显示为“实际节省”或“实测耗时”。

## 6. 验证计划与当前证据

本轮验收问题：

1. 首次用户能否理解驾驶舱是“统一查看和安排今日工作”的入口，而不是聊天记录或 Worker 监控台？
2. 三项简单任务是否按 Admission 固定路由，客户 A 是否明确处于待决定并显示三种允许模式？
3. 路由解释是否能支持用户选择本次模式，而不需要阅读内部模型过程？
4. 用户选择 Adaptive Swarm 后，界面是否明确保持 `execution_status=not_started`，不产生虚假运行或完成状态？
5. 版本冲突、不允许的模式、未知结果和 API 读取失败时，是否保留最后服务端事实并可恢复？

协议、API、驾驶舱交互、聚焦后端测试、5 条专用浏览器用例、完整回归和三张视觉证据已经产生，见 [`DEMO2-PR1-EXPLAINABLE-ADMISSION-EVIDENCE-20260817.md`](../evidence/DEMO2-PR1-EXPLAINABLE-ADMISSION-EVIDENCE-20260817.md)。因此本决策只在单进程固定演示范围内标为 `Verified`：可以写“已实现可解释 Admission 纵切”，不能写“已启动 Swarm”“节省成本”“提升效率”或“目标用户已经理解”。

## 7. 关联项

- Scenario：[`SCENARIO-002`](../scenarios/SCENARIO-002-demo2-explainable-admission.md)
- Source：`USER-FEEDBACK-20260817-01`、`USER-FEEDBACK-20260810-02`、`MEETING-DECK-0716-V2-01`、`SCRIPT-V5-202607`
- UI 事实矩阵：[`UI_SERVER_FACT_MATRIX.md`](../contracts/UI_SERVER_FACT_MATRIX.md) 的 Demo 2 区域
- Evidence：[`DEMO2-PR1-EXPLAINABLE-ADMISSION-EVIDENCE-20260817.md`](../evidence/DEMO2-PR1-EXPLAINABLE-ADMISSION-EVIDENCE-20260817.md)
- 实现提交：`82df6b8`；完整 Python `118 passed, 1 skipped`；完整浏览器 `34 passed`；堆叠 PR [#13](https://github.com/Dickey007s/lenovo_agent/pull/13)（依赖 PR #12）
