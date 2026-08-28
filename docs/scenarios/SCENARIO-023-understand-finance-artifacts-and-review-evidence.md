# SCENARIO-023：在下载前理解财务成果并清楚审查证据

## 用户与触发

- 用户：需要复核往来余额的财务或业务负责人。
- 触发：用户输入“核对三期往来明细，生成未付统计、未收统计，并判断是否存在僵尸账款”。
- 数据：FORTE 公开 `Finance-018` 的 2025 上半年、2025 下半年、2026 三份 XLSX。

## 主路径

1. Agent Control Loop 冻结整库索引并由固定 `office-finance-reconciliation` 适配器读取三份
   公开输入，原件保持只读。
2. 适配器从 2026 工作簿生成正数贷方期末余额的未付 CSV 和正数借方期末余额的未收 CSV。
3. 适配器按同一科目与客商比较三期正数借方期末余额，生成跨期说明。
4. 成果卡直接显示标题、涵盖期间、统计口径、用途、记录数、内容来源和自己的检查项。
5. 用户可下载文件或展开逐项检查；若打开 Finding 审查页，能以更大字号查看事实、影响、
   证据摘录和安全预览。

## 完成条件

- 未付卡显示 2026 期末、正数贷方口径、31 条记录、1 份内容来源。
- 未收卡显示 2026 期末、正数借方口径、2 条记录、1 份内容来源。
- 跨期说明卡显示三个期间、借方未收余额比较、3 份内容来源。
- 两个 CSV 不携带三期来源完整或僵尸账款检查；跨期说明不冒充 CSV 行内容。
- 桌面与 390 px 的问题审查页主要正文和证据达到新字号基线，页面级无横向溢出。

## 异常路径

- Artifact 缺少语义字段时，浏览器仍显示旧摘要和下载入口，但不得从文件名推导期间。
- 任一确定性检查失败时显示该 Artifact 检查失败，不把其他文件一并标为失败。
- Preview 完整性失败继续 fail closed；字号或布局不能绕过安全读取边界。

## 不会发生

- 不修改 FORTE 原始账表，不记账，不发起付款。
- 不把 31/2 说成期间数量，也不把两个 CSV 说成三期合并表。
- 不把固定 `Finance-018` 适配器表述为通用财务语义验证能力。

## 来源与验证

- 来源：[`USER-FEEDBACK-20260828-tc05-artifact-meaning-and-review-readability`](../sources/USER-FEEDBACK-20260828-tc05-artifact-meaning-and-review-readability.md)。
- Decision：[`DR-0037`](../decisions/DR-0037-tc05-artifact-semantics-and-review-readability.md)。
- Evidence：[`DR-0037-TC05-ARTIFACT-SEMANTICS-AND-REVIEW-READABILITY-EVIDENCE-20260828`](../evidence/DR-0037-TC05-ARTIFACT-SEMANTICS-AND-REVIEW-READABILITY-EVIDENCE-20260828.md)。
