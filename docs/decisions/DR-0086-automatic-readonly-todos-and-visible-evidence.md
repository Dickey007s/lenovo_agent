# DR-0086：多待办自主只读执行与可见证据

日期：2026-10-24。状态：Limited Verified，限定本地单进程、指定资料库、定向测试与实跑案例。
实现：未提交工作树；HEAD 基线 fa974ae。没有新 PR。
场景：[SCENARIO-073](../scenarios/SCENARIO-073-run-independent-office-todos.md)。
来源：[USER-FEEDBACK-20261024](../sources/USER-FEEDBACK-20261024-live-demo12.md)。
验证：[Evidence](../evidence/DR-0086-LIVE-DEMO12-20261024.md)。

## 场景与来源

用户要求 Demo1 多次真实操作、展示中断与证据；Demo2 预设多个待办、分别调用模型并逐项判断单 Agent 或多 Agent。
本决策增量替代 DR-0053 中“每波必须临时确认”的限制，但仅限提交时明确选择的新自主只读策略。旧手动路径不变。

## 决策

- `POST /runs` 新增通用 `execution_policy=manual|automatic_readonly`，默认 manual；不使用 Demo 私有功能开关。
- 自主策略必须同时提交 `output_preference=analysis_only` 且不得附带 action。启动请求、幂等摘要、内部持久 Snapshot 和公共投影保留该策略。manual 不进入旧启动摘要，兼容原幂等键。
- UI 一次提交三个可编辑待办，逐个调用原 POST /runs；每项立即独立运行，不等上一项完成。不是三项拼成一个大指令。
- 每项保留自己的 Task、Run、模型预算、服务端拓扑判断、证据和成果。UI 默认每项3轮、8文件/轮、8模型调用、600秒；API 仍使用既有合同上限。
- 拓扑仍由独立工作包、依赖、来源结构、预算与人工门决定。不加入模型自评难度分，也不保证复杂任务一定开多 Agent。
- 自主策略遇到人工门或副作用计划停止，不执行这些工作。普通单控制器顺序执行；准入只读协作后服务端自动派发1至3个 ready Branch，最多12波且受调用、时间、版本容量等原门约束。
- 自动派发不伪造 `confirmed=true`；授权来自持久化的启动策略。进入既有 Worker 执行函数后仍检查 Owner、Run version、来源、依赖、预算、幂等和贡献采用条件。
- 后续只派发从未尝试且依赖满足的 ready 工作。引用歧义、失败和业务判断不自动选择/批准，也不循环重试。一个失败保留其他成果；暂停或停止阻止下一波。
- 重启仍走原检查点恢复策略，不自动重放在途调用。新策略不声称完成 PostgreSQL/分布式恢复验收。
- Worker 合入后同步 budget 与本轮已核对来源计数，使用实际 Branch verified refs 的去重并集，不按返回数量计数。

## 前台交互影响

三个 Demo 保持同一外壳。Demo2 空白任务变为三项待办，启动后每项可看状态、执行方式、分工理由和详情。
任务历史分类优先保留自主策略，因此单 Agent 的 Demo2 任务不会刷新后跑到 Demo1。
待办启动结果未知时锁住编辑和外层导航，同页面重试复用原 payload/key，不重发已确认项。
批次发起仍由浏览器组织：没有服务端 Batch 实体、跨 Task 优先级调度或持久批次队列；刷新会失去本页批次表，但已受理任务可从历史找回。未知提交跨刷新恢复未实现。

依据页显示已完成工作项、未完成原因、可展开的有疑问引用、原文角色、文件与行号。
Run 暂无顶层 Result 时，从同 Run 最新保留 ArtifactVersion 展示引用并明确标注版本，不能把“没有最终结果”误写成“没有证据”。
需要判断的发现不因默认只显示前三项而隐藏。原文定位不等于语义充分或业务批准。
自主策略隐藏手动 Worker 派发按钮；协作记录仍可查看。无 DecisionRequest 的 Worker 歧义仍只读展示，不制造恢复权限。

## 后端事实映射

| 界面 | 权威事实 | 禁止推断 |
| --- | --- | --- |
| 三项待办分别已受理 | 三个 /runs 回执及不同 task_id/run_id | 新增持久 Batch 调度器 |
| 单 Agent / 多 Agent | 每个 Run 的 topology_admission | 预设任务名决定路线、客观难度评分 |
| 已自主启动协作 | execution_policy + automatic_topology_authorized + worker_wave_reserved | 前端动画/自动点击授权 |
| 多 Worker 已执行 | analysis_started/completed、worker_runs.model_called | 仅凭节点数量声称并行 |
| 结果已采用 | contribution gate_status、output_used、ArtifactVersion | 返回即采用、已批准业务 |
| 中断仍有证据 | Branch + ArtifactVersion.findings.evidence_anchors | 暂停清空已有成果 |
| 已核对文件数 | Branch verified_file_refs 去重，写回预算与轮次 | 候选文件数、模型看到就等于通过 |

## 验证与边界

命令、运行编号、截图和失败复测见 Evidence。真实模型、固定规则 API、受控模型测试分别报告。
没有任意办公写入、外部动作、分布式 Worker、全量语义验证、模型成功率或用户研究结论。
实际缺批准书案例暴露 Planner 可能选择相近材料，最终触发引用歧义而不是准确报告缺源；没有放行批准，也没有把选择位置当作补足批准书。此语义缺源识别仍需后续工作。

拒绝方案：前端自动点击原确认按钮、所有任务强制多 Agent、重复重试直到看起来成功、放宽引用校验来刷通过。
