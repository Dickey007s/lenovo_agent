# SCENARIO-039：可解释路线准入与受限 Worker 的统一成果收敛

- 状态：`Proposed`
- 决策：`DR-0053`
- Source：`USER-FEEDBACK-20260830-DEMO1-DEMO2-CONTINUATION`、
  `MULTI-AGENT-ORCHESTRATION-OFFICIAL-20260830`、
  `AGENT-INTEROP-AND-ELICITATION-OFFICIAL-20260830`、
  `HAI-MIXED-INITIATIVE-RESEARCH-20260830`

## 用户与触发

- 用户：同时处理多个办公来源、需要知道系统为何分工以及哪份结果可采用的业务负责人。
- 触发：Validated plan 包含多个工作包；其中可能有独立并行任务，也可能只是多份同
  结构文件的顺序核对。
- 痛点：简单显示多个 Agent 容易把路线、执行和采用混为一谈；用户被迫打开多个会话，
  自己判断冲突并复制结果，且多 Agent 可能只增加成本。

## 前置条件

1. Task Contract、Workspace scope、预算和 `external_action=none` 已由服务端冻结。
2. Planner 候选已通过 plan/source/dependency/tool/side-effect 校验。
3. 通用 Tool Gateway 未实现，因此 `direct_tool` 只能作为 unavailable 目标路线。
4. Worker 只能只读批准来源，数量和并发均有硬上限。

## 路线选择主路径

1. 服务端从 validated plan 计算来源跨度、工作包独立性、依赖、预算和风险。
2. 生成 `TopologyAdmission`，路线为 `single_controller`、`fixed_workflow` 或
   `adaptive_readonly_workers`，同时给出稳定 reason codes 与收益依据状态。
3. 单 Controller/固定流程按现有方式直接推进；高成本只读 Worker 路线先进入
   `confirmation_required`，未确认前不产生 Worker 或模型调用。
4. 用户看到业务化路线说明、预计上限和边界，确认或选择降级。
5. 确认后，服务端把 validated plan 编译为 WorkUnit DAG，最多启动三个只读 Worker。
6. 每个 Worker 只接收自己的 Branch、approved file refs、完成条件和预算，返回结构化
   Contribution candidate。
7. Runtime 先做引用 membership、Evidence Anchor、Branch Evidence Gate 和适用的
   deterministic outcome/narrative reconciliation，再决定 adopted/rejected/waiting。
8. 稳定合并器只把 adopted Contribution 写入新的 ArtifactVersion；TaskCommit 指向
   当前统一成果。前台只呈现工作包和统一结果，不要求用户管理 Worker 对话。

## 正向镜头：跨部门上线准备

用户要求核对产品、法务、运营、质量和发布材料。五个工作包中有三个可独立读取，两个
依赖前置结果。Admission 建议最多三个只读 Worker，并说明跨来源与独立工作面；用户
确认后，三个 Worker 并发，后续两个按依赖启动。最终驾驶舱显示 5/5 工作包、4 项
adopted、1 项待人工确认和一个统一成果版本。

## 反向镜头：三期财务核对

用户要求核对三期同结构财务明细。虽然有三份文件，但同一口径、顺序合并和固定确定性
检查占主导，Admission 推荐 `fixed_workflow`。前台解释没有启动多个 Worker 的原因，
并显示未付统计、未收统计、跨期核对说明三个成果各自代表什么。

## 异常路径

- **单来源或强依赖**：降级为 `single_controller`/`fixed_workflow`，不启动 Worker。
- **预算不足**：显示降级理由；用户可以结束或在新合同中确认预算，不得静默超额。
- **收益未知**：允许基于结构并行性建议，但前台明确“尚无同场收益证据”。
- **一个 Worker 超时/失败**：只标记目标 WorkUnit；其他 adopted Contribution 保留。
- **Evidence 歧义**：目标 WorkUnit 进入 waiting_input，其他结果可形成 partial v1。
- **stale/tampered candidate**：服务端重算 revision/candidate 后拒绝；不进入合并。
- **开放冲突**：ConflictRecord 未解决前禁止相关 Contribution 进入当前 Commit。
- **用户停止单元**：只停止指定 WorkUnit；停止整个 Task 需要独立全局控制命令。
- **外部动作**：只形成建议，绝不发送邮件、付款、改生产或调用真实 Connector。

## 前台输出

| 区域 | 用户看到 | 用户可做 | 默认隐藏 |
| --- | --- | --- | --- |
| 路线建议 | 推荐路径、理由、预算、风险、收益依据 | 确认 Worker、选择固定流程、取消 | 内部权重、Prompt、CoT |
| 工作包 | 业务名称、依赖、批准来源、状态、阻塞影响 | 展开证据、暂停/继续目标单元 | Worker 私聊和原始 response |
| 实际回执 | `已调用/已返回/已采用` 分开、耗时 | 查看未采用原因摘要 | 密钥、内部验证表达式 |
| 统一成果 | adopted/待核对/冲突、ArtifactVersion | 下载、回开引用、恢复历史版本 | “最后回复即真相” |
| 边界 | 只读、无外部动作、最多 Worker 数 | 停止、调整下一轮方向 | 假 Connector 或执行动画 |

## 后端事实映射

| 前台状态 | 服务端权威事实 |
| --- | --- |
| 推荐固定流程 | Admission `route=fixed_workflow` + reason codes |
| 建议三个 Worker，等待确认 | `route=adaptive_readonly_workers`、`confirmation_required`、`max_parallel_workers=3` |
| Worker 已开始 | `work_unit_started` + actual Worker receipt |
| Worker 已返回但未采用 | `returned=true/output_used=false` + Contribution rejection |
| 两项可用、一项待核对 | adopted Contribution IDs + waiting WorkUnit/Resolution |
| 已合并为 v2 | MergeReceipt + new ArtifactVersion/TaskCommit |
| 未发生外部动作 | Contract `external_action=none` + no Tool/Connector receipt |

## 完成条件

- 相同冻结合同的路线和理由稳定；低并行/强依赖/预算不足负例不启动 Worker。
- 未确认 `adaptive_readonly_workers` 前没有模型调用；确认后并发和总数不越界。
- WorkUnit 依赖、状态、Worker receipt、Contribution 和合并结果可从 Snapshot/Event 对账。
- 无 Anchor、stale、篡改、错误算术或与确定性成果矛盾的候选不进入当前 Artifact。
- 单 Worker 失败不清空其他 adopted Contribution，恢复只重跑目标 WorkUnit。
- 用户无需打开多个 Agent 会话即可判断路线、失败影响和当前统一成果。

## 自动化验收用例

1. `single_source_contract_is_admitted_to_single_controller`。
2. `three_period_same_schema_finance_uses_fixed_workflow`。
3. `independent_cross_source_units_require_confirmation_before_workers_start`。
4. `confirmed_worker_route_never_exceeds_three_parallel_workers`。
5. `worker_failure_preserves_other_adopted_contributions`。
6. `ambiguous_worker_evidence_waits_only_target_work_unit`。
7. `tampered_or_stale_contribution_is_rejected_before_merge`。
8. `deterministic_outcome_conflict_rejects_worker_narrative`。
9. `postgres_restart_preserves_admission_units_contributions_and_current_artifact`。
10. `desktop_and_mobile_show_one_cockpit_without_worker_chat_transcripts`。

## 用户研究任务

形成性测试给参与者两种界面：多个 Worker 聊天窗口与统一驾驶舱。参与者需回答：

1. 为什么选择这条路线，Worker 是否真的启动；
2. 哪个工作包失败，其他成果是否还能用；
3. 哪条 Contribution 已采用，哪条只返回未采用；
4. 下一次点击会改变什么，是否会触发外部动作。

理解正确率、恢复步数、中断次数和主观控制感是待测指标，不得在测试前写成改进结论。

## 设计来源 Source ID 与运行时 Fixture `source_ref`

- `MULTI-AGENT-ORCHESTRATION-OFFICIAL-20260830`：并行 Agent、共享任务和成本边界。
- `AGENT-INTEROP-AND-ELICITATION-OFFICIAL-20260830`：Task/Artifact/结构化人工输入。
- `HAI-MIXED-INITIATIVE-RESEARCH-20260830`：能力说明、后果、纠错、主动性控制。
- 正向 Fixture 使用公开 FORTE 多目录输入或专门构造的 allowlisted 测试资料；反向 Fixture
  复用三期财务结构。任何业务公司名和数值都必须标记为公开/合成测试事实。

## 当前边界

当前 main 是单 Controller，虽然有 Branch、固定适配器、Artifact/Commit 和 Evidence
Gate，但没有通用 `TopologyAdmission`、Worker DAG 或 Contribution merge。本场景在
源码、真实 PostgreSQL、Provider、浏览器和 Evidence 完成前保持 `Proposed`；官方竞品
资料也不证明其他产品不能实现同类合同。
