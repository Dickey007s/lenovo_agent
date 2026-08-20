# SCENARIO-002：智能工作驾驶舱的可解释 Admission 与本次路由选择

| 字段 | 内容 |
| --- | --- |
| Scenario ID | `SCENARIO-002` |
| Decision | [`DR-0008`](../decisions/DR-0008-demo2-explainable-admission.md)、[`DR-0011`](../decisions/DR-0011-demo2-route-impact.md) |
| Status | `Verified`（限定范围） |
| Owner | Office Agent 项目组 |
| Scope | Demo 2 第一纵切：服务端驱动的固定演示队列、路由解释、仅本次路由选择与 Admission 预览 |
| 当前性质 | 已实现并验证单进程 memory 纵切；不是 Adaptive Swarm Runtime，也不证明用户价值 |

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
5. Adaptive Swarm 只能处于“推荐”或“本次已选择”状态；在真正 Worker Runtime 未实现前，`execution_status` 必须为 `not_started`。
6. Admission 展示 Value、Breadth、Parallelism、Deadline、Risk、Budget 六类依据。`route_profiles[].forecast.source_type` 固定为 `fixture_policy_forecast`，不写成实测成本、实测时延或生产 SLA。
7. 每个允许模式由服务端给出影响预演，至少覆盖工作分配、协调、人工介入、规则预测、执行边界与外部动作边界；前端不得根据模式名自行补造。
8. 确认后产生服务端选择回执与连续历史。左侧显示实际变化，右侧显示精简回执；同模式重复、缺 route profile/preview 均失败且不增加版本。

## 3. 固定演示任务

以下四项任务是本轮确定性 Fixture，不代表真实企业任务列表：

| 业务任务 | 业务信号 | 建议路由 | Swarm 状态 | 执行状态 |
| --- | --- | --- | --- | --- |
| 客户 A 经营汇报 | 今日截止、业务价值高、跨邮件/CRM/项目周报/日历核对 | 待决定；允许 Single Agent / Fixed Workflow / Adaptive Swarm | 尚未选择 | `not_started` |
| 供应商邮件回复 | 今日需形成一版独立草稿 | Single Agent | Admission 固定路由 | `not_started` |
| 周报格式统一 | 明早前完成的稳定重复整理 | Fixed Workflow | Admission 固定路由 | `not_started` |
| 报销异常核查 | 待补证据的单项查证 | Tool Call | Admission 固定路由 | `not_started` |

“成本”和“时效”在本场景中只表示演示策略给出的预估标签或区间；没有真实模型调用、Worker 调度、Connector 访问、计费记录或端到端时延测量，不能显示“节省了多少成本”或“快了多少”。

## 4. 核心流程

1. **读取固定队列**：驾驶舱 GET 当前 Owner 的四项固定演示任务；返回前只显示读取态。
2. **查看工作条件**：服务端给出固定队列顺序、业务价值、资料广度、可并行工作包、截止压力、风险和资源边界；本纵切不宣称动态排序。
3. **解释与预演**：用户查看路由依据和允许模式；切换模式时，左侧立即显示服务端给出的工作影响，而不是模型思维链或内部评分过程。
4. **本次选择**：客户 A 用户在看见 `before → after` 后确认某个允许模式，选择范围限定为“仅本次运行”；本纵切不实现拖拽调序或长期排序偏好。
5. **路由预览**：四项任务同时展示服务端推荐路由和业务含义。三项简单任务已按 Admission 固定路由，客户 A 保持待决定；路由选择不等于开始执行。
6. **Admission**：用户打开客户 A 的 Admission，查看六类依据、演示预算与预计等待标签；可以选择推荐的 Adaptive Swarm、降级到 Single Agent/Fixed Workflow 或暂不选择。
7. **选择来源**：选择推荐的 Adaptive Swarm 时 `selection_source=admission`；用户降级时 `selection_source=user_override`，并记录 `override_scope=this_run`。
8. **停在执行前**：即使用户选择 Adaptive Swarm，也显示“已选择，尚未启动执行”，并保持 `execution_status=not_started`。
9. **回执与改选**：服务端返回实际记录变化和连续版本历史；刷新恢复同一回执。再次选择其他方式先回到预演，确认后历史追加；相同方式不重复写版本。

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

## 6. 前台与后台边界

前台展示任务目标、来源性质、固定队列位置、路由解释、允许模式、六类 Admission 依据、演示预算/时效预测、当前版本和待用户决定。前台不展示原始 Prompt、思维链、Worker 对话、内部 Worker 名称、原始 `fixture:` ID、密钥、Token、Permit、底层日志或无决策价值的调度噪声。

本场景的“已选择 Adaptive Swarm”只表示用户对本次路由作出选择；除非后续另有服务端执行事件和真实 Worker 证据，否则不得显示“已启动”“运行中”“已完成”或“节省成本”。

## 7. 来源与局限

- `USER-FEEDBACK-20260810-02`：要求同时补充场景、来源、前台交互和前后端统一；不证明 Demo 2 已实现。
- `MEETING-DECK-0716-V2-01`：0716-v2 原始阶段汇报；支持三 Demo 方向和八个常驻组件背景，不证明 Runtime 或用户效果。
- `SCRIPT-V5-202607`：P20、P18-P22 描述驾驶舱、排序、分流、Admission、Shared Artifact Workspace 与返回驾驶舱叙事；属于内部设计输入，不是运行证据。
- `TARGET-ARCHITECTURE`：第 5、6、7、8、10 节定义 Admission、四种路由、前端事实映射和先单任务后 Swarm 的顺序；仍是目标架构。
- `USER-FEEDBACK-20260817-01`：要求继续推进并关注协作成本；不提供成本、时效或质量实测。
- `USER-FEEDBACK-20260820-03`：把创新前端与 Agent 操作影响可见设为第一目标；是 Stakeholder 方向，不证明当前方案有效。
- `HAI-GUIDELINES-CHI2019`、`GOOGLE-PAIR-FEEDBACK-CONTROL-2021`：支持及时说明系统能力、状态和选择影响；通用研究/设计实践不替代本项目工程证据或用户研究。

当前已有协议、API、影响预演/回执、完整浏览器工程代理、完整 Python 回归与截图证据，但没有目标用户研究、真实 Connector、动态 Worker、真实计费、成本账单或端到端时延基准。因此本场景只在单进程固定演示范围内标为 `Verified`，不能升级为用户价值或 Adaptive Swarm 已验证。
