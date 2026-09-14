# DR-0059：显式要求逐项记账与受限分析恢复

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`；真实 Provider 与工程门通过，业务正确性和用户效果仍为 `Draft` |
| 日期 | 2026-09-02 |
| 用户来源 | [`USER-FEEDBACK-20260902-COMPLEX-TASK-REQUIREMENT-ACCOUNTING`](../sources/USER-FEEDBACK-20260902-complex-task-requirement-accounting.md) |
| 前置决策 | `DR-0024`、`DR-0030`、`DR-0053`、`DR-0055`、`DR-0058` |
| 场景 | [`SCENARIO-046`](../scenarios/SCENARIO-046-account-for-explicit-requirements-and-recover-analysis.md) |
| Evidence | [`DR-0059-EXPLICIT-REQUIREMENT-AND-ANALYSIS-RECOVERY-EVIDENCE-20260902`](../evidence/DR-0059-EXPLICIT-REQUIREMENT-AND-ANALYSIS-RECOVERY-EVIDENCE-20260902.md) |

## 1. 问题

复杂指令会同时受到 Planner 结构、每轮文件预算和 Analyst 输出质量影响。旧路径只公开最终
Plan/Branch：模型少建一条、服务端裁掉一条和资料库确实没有来源在前台看起来都像“少了一
条”。Analyst 返回截断 JSON、非 JSON、Schema 错误或无法绑定业务分支时，也可能只留下笼统
的未采用状态。Adaptive 页面还可能在没有 ready Branch 时显示“继续下一批”。

这些不是同一种失败，不能用一条模糊文案覆盖。

## 2. 决策

### 2.1 明确编号要求必须逐项记账

只有指令同时包含“业务分支/以下事项/以下要求/分别核对/分别检查/逐项核对”等明确标记，
并形成连续的 `1..N` 编号时，Runtime 才启用显式要求合同；当前 `N` 上限为 12。普通叙述中的
零散数字不触发该合同。

Planner 的私有候选必须对每一项返回 `requirement_coverage`，状态只能是：

- `planned`：绑定本轮一个唯一根工作单元；
- `deferred`：冻结索引中已有批准候选来源，但受文件预算或依赖顺序限制，本轮不执行；
- `uncovered`：整个冻结索引中没有可识别来源，不得伪造文件引用。

服务端校验编号完整、不重复，`planned` 必须绑定真实根单元，多个要求不能共用同一根单元，
`deferred` 候选必须属于 allowlist，`uncovered` 必须没有候选引用。文件预算裁掉一个已计划根
单元时，服务端把它改记为 `deferred`，而不是静默删除。

### 2.2 公共状态区分执行、延后和缺源

私有 `requirement_coverage` 不直接公开。公共 Plan 只投影：

- `units[]`：本轮实际可执行工作包；
- `deferred_requirements[]`：有已批准候选来源、尚未进入本轮；
- `uncovered_requirements[]`：当前冻结索引无法形成来源。

每个延后项同时形成稳定的 `waiting_input` Branch。Planner 可读取从安全 Preview 首个业务标题
派生的内部 `planner_search_hint`，用于弥补文件名过于抽象的问题；该字段不进入公共 Workspace、
Snapshot 或前台。

### 2.3 Analyst 失败按事实分类并受限修复

Analyst 仍只允许严格 JSON，不接受从散文中猜结构。分析调用使用独立的 180 秒超时和
12,000 token 上限。Runtime 分开记录截断、非 JSON、Schema 错误、超时、Provider 错误、
工作单元绑定错误和来源定位错误；最多再调用一次进行受控修复。

为降低复杂任务把大量同类行逐条展开而造成截断的概率，Analyst 提示按工作包压缩：每个根
单元最多两条候选 Finding、每个下游汇总单元最多一条，提示级总量不超过 24。公共/服务端
结果合同仍允许 96 条，已经返回且通过校验的 Finding 不得静默截断；这是输出组织约束，
不是“最多发现三条”或穷举正确性的承诺。

有可采用 Finding 时保留合法子集，其余进入 Branch Evidence Gap。两次都没有可采用结构时，
保留 Plan、Branch、模型 `called/output_used/elapsed_ms` 和既有成果，并以
`next_step.recovery_kind=analysis_output` 暂停最小分支。范围越权和 Catalog 完整性错误仍
fail closed。

### 2.4 延后分支不能进入空 Worker 波次

Worker 汇合后，`next_step.candidate_branch_ids/candidate_file_refs` 必须继续包含已有来源的
延后 Branch。只有最新 `ready_branch_ids` 非空时才允许显示 Worker 确认动作。没有 ready 波
次时，协作页提示回到工作进展选择后续分支；工作进展把延后项与本轮工作包分开，并把“继续
此项”绑定到真实 Branch resume。

## 3. 交互后果

| 服务端事实 | 前台表达 | 不得表达 |
| --- | --- | --- |
| 本轮 `units[]` | “N 条可执行分支” | 所有明确要求都已执行 |
| `deferred_requirements[]` + waiting Branch | “已知来源，尚未进入本轮”并提供单项继续 | 资料缺失、已完成或下一批 Worker 已 ready |
| `uncovered_requirements[]` | “冻结资料库中没有足够来源” | 搜索过互联网、竞品或企业系统 |
| Analyst 首次失败、二次部分采用 | 显示调用、重试、采用与缺口 | 模型未调用或整项任务成功 |
| 两次无可采用结构 | 分支级 `analysis_output` 恢复 | 采用失败文本或要求用户修改源文件 |

## 4. 当前边界

- 编号识别是受限语法，不是通用自然语言需求编译器；
- `planner_search_hint` 来自既有安全 Preview，不扩大 Run scope，也不证明语义匹配正确；
- 每轮 16 文件仍可能把有来源的要求排到后续轮次；
- 来源位置通过不证明语义、穷举、数值或业务结论正确；
- 自动化和两次 Provider 运行不是目标用户研究；
- 本次不修改 PPT，不实现分布式 Worker、外部动作或智能工作驾驶舱。

## 5. 验证结论

真实 `deepseek-v4-pro` 六项任务在首轮形成 6 条公共 Branch：4 条本轮执行、2 条有来源的
后续分支、0 条缺源；服务端因独立分支超过受限 Worker 上限选择 `fixed_workflow`。可见 Run
的 Analyst 首次因业务分支绑定失败被拒绝，受控重试后采用并进入 `waiting_input`。另一条三轮
Run 又验证了来源定位失败后的重试、部分采用、延后分支继续和预算停止。精确运行事实、截图、
测试命令和限制见 DR-0059 Evidence。
