# DR-0083：用户走查与一致的草稿、协作展示

日期：2026-10-22。状态：Limited Verified，仅限认知走查与本轮前端回归，见 Evidence。
来源：[用户反馈与走查](../sources/USER-FEEDBACK-20261022-user-walkthrough.md)。
场景：[SCENARIO-070](../scenarios/SCENARIO-070-walk-from-task-to-delivery.md)。
证据：[Evidence](../evidence/DR-0083-USER-WALKTHROUGH-20261022.md)。
前置：DR-0024/0028、0034/0036、0052/0053、0069、0074、0081/0082。

## 前台交互影响

1. 根页与能力页共用 ResultView 的已保留版本回退。没有公共 Result、没有文件/EffectReceipt，
   且没有 rejected/supplemental 叙事时，才展示 Commit 指向或最后一个逻辑版本。
   标为分析草稿、结论待复核；不生成文件、不宣称完成。文件/回执的权威及失败路径不被草稿覆盖。
2. 根页“Agent 路径”改为“执行进展”，成果页增加明确返回入口。
   未形成内容时短说明指向进展，不再使用机制名称解释空白页。
3. 原协作弹窗优先展示本批确认范围、预算与只读上限，再展示全部工作包的状态和依赖名称。
   台账、来源、版本和每项任务长说明按需展开。能力页的完整依赖图不替换。
4. ready IDs 投影为“就绪，待你确认”，ambiguous 回执为“引用位置待核对”，未知状态不伪装运行中。
   执行和贡献通过 worker_run_id 与 branch_id 精确关联为一行，调用/采用、失败与定位数仍可见。
   原始来源和采用摘要按需查看；无对应 Worker 的贡献单独保留，不能静默丢掉。
5. 协作派发仅允许 waiting_input 且服务端 ready 集合中的 running Branch，按原顺序最多三个。
   不再把空 ready 集合当作所有 running Branch 的通行许可。版本、幂等、Owner 和服务端验证不变。
6. compact 等待时去掉无效的总暂停按钮，将方向输入标为可选并折叠。
   逐项恢复、候选选择、停止、错误仍可见；运行中的暂停/调整不折叠。
7. 文件类型使用原生下拉，不改变文件目录、预览或整库任务范围。选择器支持键盘。
8. 弹窗键盘循环纳入可见 summary，排除折叠内容；Escape 仍返回触发按钮。

## 后端事实映射

没有后端、模型输入、持久层或公开协议变更。所有成果仍来自当前 Snapshot 的 Result、
ArtifactVersion、TaskCommit、WorkspaceArtifact、EffectReceipt 和 NarrativeReconciliation。
Branch / WorkUnit / Worker / Contribution 与 ready IDs 决定协作展示，不从文案猜状态或关联。
浏览、折叠、返回和新建草稿不提交命令；新建草稿不会停止旧任务。

## 验证与边界

受控主路径、无 ready 批次、失败文件、拒绝叙事、手机首屏和键盘均需检查，结果见 Evidence。
助手认知走查不等于目标用户研究。本轮没有证明真实模型正确性、多任务调度、数据库恢复、
外部动作或 Worker 歧义人工恢复闭环。
