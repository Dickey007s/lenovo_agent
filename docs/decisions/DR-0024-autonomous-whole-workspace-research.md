# DR-0024：整库自主研究取代手工文件范围选择

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`，仅限固定 FORTE 公开资料库、单 API 进程 memory、只读分析与被测浏览器路径 |
| 日期 | 2026-08-25 |
| 触发来源 | [`USER-FEEDBACK-20260825-18`](../sources/USER-FEEDBACK-20260825-18-autonomous-whole-folder-research.md) |
| 场景 | [`SCENARIO-010`](../scenarios/SCENARIO-010-autonomous-whole-workspace-research.md) |
| Evidence | [`AUTONOMOUS-WHOLE-WORKSPACE-RESEARCH-EVIDENCE-20260825`](../evidence/AUTONOMOUS-WHOLE-WORKSPACE-RESEARCH-EVIDENCE-20260825.md) |
| 被取代范围 | `DR-0022` 的客户端 `selected_file_refs` 交互；其公开数据、安全预览与来源边界继续有效 |

## 问题

原工作台已经从 Demo 选择器收敛为一个 FORTE 文件夹，但仍要求用户先勾选 1 到 20 份文件。这把检索责任推回给用户，也让左侧目录继续像任务分类器，而不是日常文件管理器。既有 Agent Control Loop 能分轮规划和核对，却没有把最终 `follow_ups` 变成“人工确认后启动下一轮工作”的清晰闭环。

## 决策

1. 根页面只呈现一个扁平、可搜索、可按文件类型筛选的办公资料库；职业/角色分组不进入普通 UI。
2. 浏览和预览只服务于人的理解，不构成 Run 的权限或来源选择。
3. `POST /v1/harness/runs` 只接收用户目标、幂等键、版本与 Loop 预算，不接收 `selected_file_refs`。
4. 服务端在创建 Run 时冻结完整 allowlisted 输入索引，`scope_mode=whole_workspace`。
5. Planner 只看到安全元数据索引，自主选择本轮文件并输出业务化 `selection_reason`。
6. 服务端拥有每轮文件预算、工具、依赖与副作用策略；即使模型超选，也只采用预算内高优先级证据。
7. Analyst 只读取服务端批准的本轮文件安全投影；结论必须引用本轮文件。
8. 最终最多展示四个下一步建议。建议只是模型候选，不是已执行事实；用户点击确认才以建议文本启动新的独立 Run。

## 技术差异及其交互后果

| 技术差异 | 旧流程 | 新流程 | 前台输出 |
| --- | --- | --- | --- |
| 服务端冻结完整索引 | 用户先猜哪些文件相关 | 用户只表达目标 | “96 份文件统一检索”与完整资料库 |
| Planner 自主检索 | 勾选范围等于上下文 | Agent 从安全元数据中选证据 | 每轮文件标签与“为什么选” |
| Policy Compiler 限制每轮证据 | 用户通过少选控制成本 | 服务端按预算裁剪模型候选 | 实际采用范围与预算说明 |
| Evidence Gate 约束结果引用 | 只检查是否引用用户选择集 | 只检查是否引用本轮批准集 | 已核对文件、缺口和未采用回执 |
| 建议与新 Run 分离 | `follow_ups` 是静态文字 | 人确认后才创建下一 Loop | “确认并启动”，旧结果仍保留 |

## 前后台统一事实

- “全部文件”来自 `GET /v1/harness/workspace` 的 96 个公开输入投影。
- “整个资料库”来自 `AgentControlLoopContract.scope_mode` 与 `allowed_file_refs`，不是浏览器选择状态。
- “Agent 本轮自主选择”来自 `rounds[].input_file_refs` 和 `plan.selection_reason`。
- “模型已采用/未采用”来自 Planner/Analyst receipt 的 `called/output_used`。
- “建议下一步”来自终态 `result.follow_ups`；点击确认发起新的 `POST /runs`，当前协议没有“proposal accepted”持久状态。
- 文件管理器不显示 `task.md`、rubric、solution、绝对路径、完整 digest、Prompt 或思维链。

## 边界

- 完整索引与 Run 仍在单 API 进程 memory；API 重启不恢复。
- Planner 自主选证据不等于检索质量已验证；模型可能漏掉关键文件。
- 当前每轮最多 8 份文件，Analyst 不读取全部 96 份正文。
- 建议确认只是启动一个新的只读 Run，不会修改源文件或执行外部动作。
- 没有形成性用户测试，不能声称新界面更易懂或更高效。

## 实现与验证绑定

- 实现提交：[`2b8e58c`](https://github.com/Dickey007s/lenovo_agent/commit/2b8e58c161df02d4f2c09bc2692db76d075f2ae2)。
- 交付 PR：[#29](https://github.com/Dickey007s/lenovo_agent/pull/29)，当前开放、未合并。
- 当前自动化、真实模型运行和截图哈希见本决策绑定的 Evidence；自动化不证明检索质量或用户价值。
