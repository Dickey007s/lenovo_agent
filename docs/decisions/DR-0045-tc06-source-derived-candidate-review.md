# DR-0045：TC-06 来源推导双岗位辅助筛选与 HR 决策边界

- 状态：Accepted；来源合同、逐条件 builder/verifier、三状态前台、下载解析和 PostgreSQL 顺序恢复已落地，最终工程门见对应 Evidence
- 日期：2026-08-29
- Source：`USER-FEEDBACK-20260829-TC06-SOURCE-DERIVED-CANDIDATE-REVIEW`
- Scenario：`SCENARIO-031`

## 决策

1. TC-06 继续由 Workspace-first 普通指令触发，不增加 Scenario 选择器。固定适配器只允许 `hr-001` 的两份 JD DOCX 与五份简历 PDF；逻辑 ID、文件名、展示路径、allowlist、大小与原始内容必须满足固定来源合同。
2. 服务端从冻结 DOCX/PDF 字节和安全文本抽取岗位条件与履历事实。每个条件必须保留 JD 与简历的 `source_file_ref`、locator 和 excerpt；姓名、学历、年限与能力事实不得跨候选人或跨主体借用。
3. 两个岗位独立推导，条件状态只能是 `met / not_met / unverifiable / human_exception_required`。未提及的事实保持 `unverifiable`；只有明确“无”或可复算数值低于无例外硬门槛时才是 `not_met`。
4. JD 明示“大专及以上（优秀者可放宽）”时，低于默认学历门槛的候选人必须进入 `human_exception_required`，由招聘人员结合来源支持判断是否适用例外，不能自动淘汰。
5. 总体建议只使用 `recommended_for_human_review / explicit_hard_gap / insufficient_evidence / exception_review_required`，不输出“已录用、已淘汰、已通过招聘”。
6. 输出真实 `外卖商户BD岗位辅助筛选报告.docx`、`文本评测岗位辅助筛选报告.docx` 和 `候选人岗位条件逐项台账.csv`。每份岗位报告只绑定该 JD 与五份简历；联合台账绑定全部七份来源。
7. Verifier 必须重新读取批准来源并复算条件、状态、建议、计数、位置、摘要和隐私边界，再核对 DOCX/CSV；不能使用报告中的结论反向验证报告，也不能保存固定岗位×候选答案。
8. 默认移除邮箱、手机号、地址、性别、年龄、照片及明显人口属性代理字段。姓名只作为五份固定来源的核对主键。当前没有公平性用户研究或人口属性评估，不能声称无偏。
9. `candidate_review_outcome` 同时写入三份 Artifact 和 EffectReceipt，并随 Snapshot 持久化。前台分别投影：来源/成果确定性检查、岗位匹配建议、最终 HR 决定；绿色 Artifact 不覆盖资料不足、人工例外或待决状态。
10. 原 FORTE 输入保持只读，`external_action=none`。系统不写 ATS、不通知候选人、不作背景调查、身份核验或正式录用决定。

## 前后端事实

| 前台 | 服务端事实 | 不允许推断 |
| --- | --- | --- |
| 这是人工复核建议，不是录用或淘汰决定 | `candidate_review_outcome.status=review_required`、`decision`、`human_review_required=true` | Agent 已代替 HR 作最终决定 |
| 确定性检查通过或失败 | Artifact `verifier_status/checks[]` 与 EffectReceipt `status` | 所有候选事实真实、建议公平或可以自动录用 |
| 有来源支持 32、明确不满足 6、资料不足 71、人工例外 1 | `candidate_review_outcome` 动态计数与 110 条 assessment 守恒 | 固定样本常量；缺失事实就是不满足 |
| 王琳达需要判断学历例外 | `reviews[].assessments[condition_id=BD-EDUCATION].status=human_exception_required` 与双来源事实 | 自动放宽、自动淘汰或服务端已经作出例外决定 |
| 孙博文 8 个月低于 1 年 | 文本评测年限条件、履历日期事实与 `not_met` 判断 | 其他候选或 BD 岗位也不满足；已拒绝孙博文 |
| 按岗位、候选人和条件展开 | `reviews[].assessments[]` 的双来源位置、事实、判断、动作和退出条件 | 浏览器自行抽取、补全或重算匹配 |
| 最终 HR 决定尚未发生 | `candidate_review_outcome.external_action=none`、EffectReceipt `external_action=none` | ATS 写入、邮件通知、背景调查或招聘流程已推进 |

## 拒绝的替代方案

- 保存固定姓名对应的匹配结论，再检查输出是否等于同一答案：拒绝。来源变异必须改变受影响条件。
- 未在简历写到就判不满足：拒绝。缺失信息只能是 `unverifiable`。
- 有 JD 例外仍按默认门槛自动淘汰：拒绝。例外属于人的决策。
- 把模型摘要当确定性 Verifier：拒绝。Planner/Analyst 与本地来源重算效果是独立事实。
- 把一个岗位的 JD 同时列作另一个岗位报告的直接内容来源：拒绝。单岗位报告只绑定本岗位 JD 与五份简历。
- 用绿色成果文件暗示已录用、无偏或已完成候选人通知：拒绝。文件结构、建议与最终动作必须分层。

## 验证门

- 正向来源变异把孙博文 AI 经验由 8 个月改为超过 1 年时，只改变孙博文×文本评测相关条件与建议；其他候选和 BD 岗位不变。
- 合法把文本评测年限阈值改为 6 个月或 2 年时，相关判断和汇总动态变化；移除王琳达例外条款后只改变其学历条件。
- 姓名或字段串线、同内容冒充、缺/多来源、空或损坏 DOCX/PDF、非法/倒置日期、学历或年限冲突均 fail closed。
- 隐私泄漏、DOCX/CSV 篡改、缺行、重复行或旧固定名单使三份 Artifact 与 EffectReceipt 失败。
- 真实 PostgreSQL 重启后三份 Artifact、EffectReceipt、110 条 outcome 和下载 SHA 一致；这只证明顺序 Runtime 已提交恢复。
- 1440 px 普通三栏与 390 px 页面检查目录、三状态、候选条件展开、字号和横向溢出；截图与自动化不证明招聘人员理解或决策质量。
