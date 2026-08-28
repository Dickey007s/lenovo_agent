# DR-0044：TC-07 来源推导授权核查、三状态前台与不签署边界

- 状态：Accepted；来源合同、逐规则 builder/verifier、三状态前台、下载解析和 PostgreSQL 顺序恢复已落地，验证结论见对应 Evidence
- 日期：2026-08-28
- Source：`USER-FEEDBACK-20260828-TC07-SOURCE-DERIVED-LEGAL-REVIEW`
- Scenario：`SCENARIO-030`

## 决策

1. TC-07 继续由 Workspace-first 普通指令触发，不增加 Scenario 选择器。固定适配器只允许一份 Legal-020 规则 Markdown 与六份委托书 DOCX；逻辑 ID、文件名、路径、allowlist、大小和内容必须唯一。
2. 服务端从 Markdown 表格解析全部 21 条规则。规则代码必须唯一，等级只能为高、中、低，名称、触发条件和说明不能为空；缺失、重复、未知或歧义等级全部 fail closed。
3. 服务端从冻结 DOCX 字节解析段落、表格和包结构。委托人、受托人、身份证、统一社会信用代码与律师执业证号必须绑定各自主体字段，禁止全文首个号码串线。
4. 每份文件对 21 条规则形成 `triggered/not_triggered/unverifiable`，共 126 条。每条保留规则、来源文件、段落或表格位置、摘录、事实、判断、原因、责任人、处置动作和退出条件；综合等级只从当前来源中已触发规则动态取最高。
5. 当前六份公开 DOCX 的签署占位为空，且包内没有 media、drawing、pict、嵌入或数字签名；没有获批的草稿豁免，所以 R05 动态触发。签署对象即使存在，也只证明有可审查对象，不证明签名真实或授权生效。
6. 委托书 4 缺律师执业证号时 M03 为 `triggered`。委托书 2、6 虽出现证号，但没有律师资格 Registry/Connector 回执，因此为 `unverifiable`；非律师诉讼代理人的关系或法院许可材料不足时同样为 `unverifiable`。
7. 输出真实 `授权委托书风控报告.docx` 和 `授权委托书逐项核查台账.csv`。Verifier 必须重新读取批准来源并复算规则、状态、最高等级、位置、摘要与 126 行守恒，不能用报告结论反向验证报告。
8. 前台投影三个并列状态：确定性文件/计算验证、法务业务 Gate、签署与人工复核。`verifier_status=passed` 不覆盖 `business_gate_outcome.status=failed`，也不改变 `legal_review_outcome.human_review_required=true`。
9. 原 FORTE 输入保持只读，`external_action=none`。当前系统不签署文件、不验证签名真伪、不认定授权有效，也不提供正式法律意见。

## 前后端事实

| 前台 | 服务端事实 | 不允许推断 |
| --- | --- | --- |
| 不得据此签署，必须法务复核 | `legal_review_outcome.status/decision`；`business_gate_outcome.status=failed` | Artifact 生成失败；系统已经作出正式法律意见 |
| 确定性检查通过或失败 | Artifact `verifier_status/checks[]` 与 EffectReceipt `status/checks[]` | 授权有效、签名真实或可直接签署 |
| 6 份高风险、11 项关键资料不足、0/6 可审查签署证据 | `legal_review_outcome` 的动态计数 | 固定样本常量；关键资料不足就是已触发风险 |
| 每份 21 条逐项判断 | `documents[].assessments[]`，绑定 `source_file_ref/locator/excerpt` | 浏览器自行抽取、补全或猜测规则状态 |
| 证号存在但资质未核验 | M03 `status=unverifiable` 与缺少 Registry/Connector 的 `reason` | 字段存在等于律师资格有效 |
| 没有签署或外部动作 | `original_inputs_modified=false`、`external_action=none` | 已盖章、已签署、已使授权生效 |

## 拒绝的替代方案

- 写死每份委托书的风险答案或历史“2 高/4 中”：拒绝。来源变异必须改变结果。
- 只检查报告中是否出现预期文案：拒绝。Verifier 从批准来源重算后核对成果。
- 有执业证号就判律师资格通过：拒绝。没有 Registry/Connector 时只能不可验证。
- 从全文寻找第一个身份证号或统一社会信用代码：拒绝。主体字段必须隔离。
- 把空签署栏当作签署证据，或因“可能是草稿”排除 R05：拒绝。例外必须是服务端批准、版本化且可审计的新合同。
- 用绿色文件检查暗示可以签署：拒绝。业务 Gate 与人工复核状态独立显示。

## 验证门

- 正向来源变异补齐一份文档的主体字段、授权/责任条款和可审查签署对象后，只改变该文件的相关判断和动态汇总。
- 委托人无证件、受托人有证件仍触发 R01；反向字段也不得串线。
- 委托书 2、6 的 M03 为不可验证；委托书 4 无证号直接触发；关键资料不足计数随状态变化。
- 空正文、缺一份、未知第七份、重复逻辑 ID、相同内容冒充两份、规则表损坏、日期非法/倒置和字段冲突均失败。
- 篡改 DOCX/CSV、缺行、重复行或固定旧摘要均使两份 Artifact 与 EffectReceipt 失败。
- 真实 PostgreSQL 重启后两份 Artifact、三状态事实、126 条台账与下载 bytes 一致；只证明顺序 Runtime 已提交恢复。
