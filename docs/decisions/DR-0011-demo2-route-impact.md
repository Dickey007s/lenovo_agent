# DR-0011：让 Demo 2 路由选择先预演工作组织，再返回服务端回执

| 字段 | 内容 |
| --- | --- |
| Decision ID | `DR-0011` |
| Owner | Office Agent 项目组 |
| Date | 2026-08-20 |
| Status | `Verified`（限定工程范围） |
| Scope | Demo 2 客户 A 的服务端路由影响预演、跨工作区即时影响地图、路由选择回执与刷新恢复 |
| Depends on | `DR-0008`、`DR-0010`、`SCENARIO-002`、`UI_SERVER_FACT_MATRIX` |
| Explicit non-goal | 本轮不启动真实 Agent/Worker，不实现 Shared Artifact Workspace、真实 Connector、真实成本/时延测量或跨进程恢复 |

## 1. 用户场景与问题

销售负责人面对 Single Agent、Fixed Workflow 与 Adaptive Swarm 三种名称时，真正需要判断的不是技术名词本身，而是选择后任务会怎样分配、哪里可以并行、什么时候需要人、哪些动作不会发生。此前驾驶舱主要展示推荐理由和预测数字，用户仍需自行把“模式名称”翻译成工作影响，选择后也只有“已记录、尚未启动”的状态提示。

完成条件是：服务端为每种允许模式提供结构化影响预览；用户在右侧切换模式时，左侧主工作区即时显示同一服务端预览；确认后服务端返回独立选择回执，页面显示实际记录的模式、版本变化、来源、范围和未执行边界；刷新后可从当前进程的 Snapshot 恢复同一回执。预览不能被当作执行结果，选择也不能被写成启动。

关键异常包括旧 Snapshot 没有影响字段、模式不可选、版本冲突、结果未知和 API 进程重启。字段缺失时前端必须禁用确认或显示不可预演，而不是补造治理语义；409 保留本地选择并重新读取；memory 重启丢失选择时不得声称恢复。

## 2. 来源与依据

| Source ID | 类型 | 精确引用 | 支持的判断 | 局限 |
| --- | --- | --- | --- | --- |
| `USER-FEEDBACK-20260820-03` | Stakeholder product feedback | [`USER-FEEDBACK-20260820-03-agent-impact-visibility.md`](../sources/USER-FEEDBACK-20260820-03-agent-impact-visibility.md) | 把创新前端与 Agent 操作影响可见设为第一优先级 | 单一 Stakeholder 方向要求，不证明设计新颖或有效 |
| `HAI-GUIDELINES-CHI2019` | 同行评审研究与研究机构页面 | Microsoft Research, Guidelines for Human-AI Interaction，CHI 2019 | 支持及时说明系统能做什么、正在做什么并允许用户校正 | 通用指南，不定义本项目协议和界面 |
| `GOOGLE-PAIR-FEEDBACK-CONTROL-2021` | 官方设计实践 | Google PAIR, Feedback + Control，2021 版 Guidebook | 支持尽快反馈用户选择如何影响系统，并保持控制与自动化平衡 | 设计实践，不是本项目用户研究 |
| `DR-0008`、`SCENARIO-002` | 既有内部决策与场景 | Demo 2 可解释 Admission、固定队列与 `this_run` 选择 | 提供当前服务端路由、版本、幂等和未启动边界 | 旧纵切只证明选择，不包含结构化影响或回执 |
| `DR-0010` | 既有交互决策 | Demo 1 的“预期影响 + 实际回执”双时态模式 | 支持把同一原则扩展到路由选择，但需重新绑定 Demo 2 事实 | Demo 1 的 Task Artifact 变化不能直接充当 Demo 2 路由事实 |
| `USER-FEEDBACK-20260820-04`、`PROCESSING-PATH-REALISM-20260820` | Stakeholder 反馈与运行证据 | [`USER-FEEDBACK`](../sources/USER-FEEDBACK-20260820-04-processing-path-realism.md)、[`Evidence`](../evidence/PROCESSING-PATH-REALISM-EVIDENCE-20260820.md) | 只记录路由的毫秒级操作不能写成执行，且应明确规则路径未调用模型 | 不证明真实 Swarm、用户理解或延迟 SLA |

## 3. 决策

采用“跨区域影响地图 + 选择前预演 + 服务端选择回执”的交互：

1. `RouteProfile.impact_preview` 由服务端为每种模式提供任务分配、并行与等待、人工介入、规则预测、执行边界和外部动作边界。
2. 用户在右侧原生 radio 切换模式时，左侧主工作区的影响地图立即切换为对应预览；这只改变浏览器草稿，不发送 mutation。
3. 影响地图按“任务怎么分配、并行与等待、什么时候需要你、演示策略预测、执行状态、不会发生”六个业务问题组织，不展示 Agent 头像、Worker 对话或内部调度图。
4. 确认请求仍使用 `expected_version + scope=this_run + idempotency_key`。服务端成功后生成 `RouteSelectionReceipt`，独立记录驾驶舱和工作项版本前后、选择来源、选择范围、规则预测、实际记录变化、执行状态与外部副作用边界。
5. 左侧影响地图由蓝色“选择前预演”变为绿色“服务端已记录”，并以真实 receipt 的 `before → after` 显示实际记录变化；右侧只显示精简回执、来源、范围和审计入口，避免重复一整份影响列表。两处都必须继续显示“未执行”。
6. `impact_preview` 与 `selection_receipt` 保持可选以读取旧 Snapshot；但新服务端选择缺少 preview 时必须拒绝 mutation，前端也禁用确认。
7. 路由选择回执随 `WorkItemSnapshot` 返回并进入现有幂等结果，因此同一进程内 GET 和相同 key 重放能恢复同一回执；`selection_receipts[]` 按版本连续追加，再次改选会保留真实上一方式。旧 Snapshot 只有 latest receipt 时在读取时归一化为一条历史。当前 memory 后端不支持跨进程恢复。
8. 已记录的相同方式不得用新幂等键再次确认并制造无意义版本；缺少 route profile 或 impact preview 时必须 409 且版本不变。
9. 主动作改为“记录本轮方式”，提交栏持续说明这是 `policy_engine` 规则路由、不调用 LLM，也不会启动协作。服务端写入结构化 runtime log 的真实毫秒耗时，不添加模拟等待。

不采用只在 Toast 中写“已切换模式”，因为它不能说明影响，也不能刷新恢复。不采用显示多个 Agent 头像，因为当前没有 Worker 生命周期事实。不使用 LLM 自由生成影响文案；当前影响是固定策略事实，避免把不可控解释当成治理承诺。

## 4. 前台输出与恢复

| 时点 | 用户看见什么 | 用户动作与反馈 | 失败或等待 | 默认隐藏 |
| --- | --- | --- | --- | --- |
| 选择前 | 左侧蓝色工作组织影响地图；右侧模式、推荐和逐项 `before → after` | 切换模式只更新预演；确认按钮关联当前预演 | preview 缺失时禁用确认并说明不可预演 | 原始 Prompt、策略权重、内部 ID、Worker 对话 |
| 提交中 | 保持当前 Snapshot 和本地选择，按钮进入等待态 | 不改变任务内容，不重复发明新语义 | 结果未知时沿用既有幂等与 GET 对账 | 网络重试、幂等键、日志 |
| 提交后 | 左侧绿色实际变化地图；右侧精简选择回执、来源、范围、版本审计和“尚未执行” | 可查看记录版本；再次改选时先看到新预演，确认后历史追加 | 同模式重复、缺 profile/preview 与版本过期均 409；memory 重启不宣称恢复 | receipt ID、原始来源 ID、内部事件序号 |

移动端不缩小成不可读的调度图。影响地图改为六条自然纵向信息，工作队列、主工作区和右侧决策依次展开；完整工作条件与路线比较默认收进原生折叠区，首要保留影响预演、推荐、当前选择和确认动作。关键可见控件至少 44px，页面本身不横向溢出。

## 5. 后端事实与协议

权威链路为：

```text
RouteProfile.impact_preview
  → 浏览器 draftMode 切换与影响地图投影
  → RouteSelectionRequest(mode, this_run, expected_version, idempotency_key)
  → Demo2CockpitService 校验模式、版本、preview 与幂等
  → WorkItemSnapshot.selection_receipt + RouteSelectionResult.item
  → 浏览器应用服务端 WorkItemSnapshot
  → 选择回执与刷新恢复
```

`RouteImpactPreview.execution_status_before/after` 当前都只能为 `not_started`，`external_side_effect` 只能为 `none`。`RouteSelectionReceipt` 记录的是路由选择 mutation 已应用，不是 Agent 执行、Worker 创建或任务完成。预测仍来自 `AdmissionForecast.source_type=fixture_policy_forecast`；服务端生成确定性 receipt ID 并把完整结果写入现有幂等缓存。

## 6. 验证与边界

最终证据记录在 [`DEMO2-ROUTE-IMPACT-EVIDENCE-20260820`](../evidence/DEMO2-ROUTE-IMPACT-EVIDENCE-20260820.md)。当前已覆盖严格 Schema/旧快照归一化、三种模式差异、推荐与覆盖来源、连续选择历史、同模式重复拒绝、缺事实 fail-closed、版本变化、GET 恢复、幂等重放、409 草稿保留、桌面/移动截图、完整 Python/浏览器回归与静态检查。

即使工程验证通过，也只能证明固定 Fixture 的协议、投影和被测恢复语义。它不证明目标用户更快理解、模式推荐正确、Adaptive Swarm 已实现、成本或时延改善。至少 5 名目标用户的无引导比较测试、真实执行事件、Shared Artifact Workspace、Verifier、真实 Connector、持久化 Store 和多实例一致性仍属于后续工作。
