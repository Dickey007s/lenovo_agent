# DR-0087：同任务后续分支与首轮任务说明

日期：2026-10-24。状态：Limited Verified，仅限本地定向测试与记录的真实模型样例。
实现：未提交工作树，HEAD 基线 fa974ae；无新 PR。
来源：[USER-FEEDBACK-20261024-TASK-BRANCHES](../sources/USER-FEEDBACK-20261024-task-branches-and-plain-office-cases.md)。
场景：[SCENARIO-074](../scenarios/SCENARIO-074-continue-office-task-with-visible-plan.md)。
验证：[Evidence](../evidence/DR-0087-TASK-JOURNEY-20261024.md)。

## 场景与来源

用户不接受“完成建议后另建一个任务”的割裂体验，也不能从技术文件名理解任务。
本条替代旧 follow_ups 确认后创建独立 Task 的合同；旧单分支补证限制继续生效。
保留统一工作台、共享资料库及 Demo2/3；不是新建一个演示产品。

## 决策

- 原 `/runs/{id}/continue` 增加 `purpose=follow_up`，须提供 instruction 且不得混用 branch_id；默认仍是 unfinished_branch，必须提供 branch_id。
- follow_up 是用户确认的一段后续要求，不是服务端逐项验证过的建议，也不以建议索引作为批准凭据。
- 当前终态 Run 才能续办。服务端保留同 task_id，新增 run_id/sequence/parent；Task 指针、Snapshot、幂等回执沿用同一提交边界。原 Run、成果与回执不变。
- 仍校验 Owner、Run version、Task version、current pointer。历史记录只读，不允许从旧分支另开并行分叉。活动 Run 须先处理当前待办或结束并保留，不能绕过为新任务。
- Follow-up 继承原输出权限，analysis_only 不因建议文字获得写权限；执行策略默认 manual，不沿用自动协作授权。
- 后续建议重新规划资料范围，不伪造旧 evidence 继承；未完成 Branch 的继续仍严格限制 missing_file_refs。
- 模型上下文包含原任务目标和直接前段要求，明确仅作背景，不能当证据。本次结论需重新读取来源和定位，不导入历史私有思维链或原始模型回包。此上下文能降低脱离原主题的风险，但不是语义关联的形式化保证。
- Task GET 增加 goal、lineage[].instruction/continuation_reason。goal 从最早同 Task Snapshot 派生；不新增 Task 写协议。

## 前台交互影响

任务标题保留初始目标；“初始处理 / 后续分支”切换实际 Run 记录。切换只 GET，不调用模型；历史结果只读。
这里的分支是同一 Task 的顺序处理阶段，不是同一 Run 内 WorkUnit/Branch 的并行任务图，也不是任意历史分叉树。
同页请求结果未知时保持原命令和幂等键，禁止外层切换/新建，重试相同操作；跨刷新命令恢复仍未实现。
既有 lineage 最多100段、最近任务列表20次运行的窗口不变，不宣称全量无限历史。

空白 Demo1 提供 Excel 往来账、入职清单、Word 招聘检查表三个输入。明确选择 analysis_only，避免自然语言“只在页面整理”未被输出策略识别。
开始前显示预计文件与交付目标，可编辑指令；提交后按真实首轮 Plan 显示要求、文件、步骤、目标。
选中文件不等于已读取；只有 model_input_coverage 记录才标“已送入分析”，不表示整文件覆盖或业务正确。
有协作准入时仍保留任务说明，协作图按需展开；首轮说明不被蜂群视图顶替。
这里展示的是可审查计划、选择理由及执行事实，不是私有思维链。未增加规划后强制人工批准的服务端 Gate。

## 后端事实映射

| 界面含义 | 权威字段 | 动作与边界 |
| --- | --- | --- |
| 一个任务、多个后续分支 | Task.task_id / current_run_id / lineage；Run.parent_run_id | 当前终态续办，旧段 GET 只读 |
| 初始业务目标 | Task.goal | 最早同 Task instruction，不被建议覆盖 |
| 本段要求 | Run.instruction | 确认后的用户文本，不是自动执行事实 |
| 首轮文件与安排 | rounds[0].input_file_refs / plan / selection_reason | 尚无 Plan 不伪造处理步骤 |
| 已送入分析 | rounds[0].model_input_coverage | 不等于来源语义核验通过 |
| 结果保留 | ArtifactVersion / workspace_artifacts | 不把建议当成果，不把旧成果说成新成果 |

## 验证与边界

命令、真实运行编号、失败与复测见 Evidence。服务端身份/CAS/幂等用受控模型回归；真实模型验证交互与具体案例，不证明通用准确率。
实跑先暴露后续任务缺上下文导致跨业务漂移，以及页面只读样例错误进入文件工具，均保留原记录并修复。
复测的后续任务仍可遇到待协作授权、证据定位不足；不能将此记录描述成全部完成。
没有新增文件上传、任意写文件、外部动作、分布式执行、真实人事决策或目标用户研究。

拒绝方案：只前端改标题但创建新 Task；复制历史结论当可靠证据；自动放行人工门；强制把所有模型运行包装为成功。
