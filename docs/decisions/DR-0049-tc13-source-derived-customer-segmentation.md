# DR-0049：TC-13 来源推导画像清洗、策略草案与四层事实

- 状态：Accepted；来源合同、动态清洗与分类、两份工件独立 Verifier、前台四层事实和 PostgreSQL 顺序恢复已落地，最终工程门见对应 Evidence
- 日期：2026-08-29
- Source：`USER-FEEDBACK-20260829-TC13-SOURCE-DERIVED-CUSTOMER-SEGMENTATION`
- Scenario：`SCENARIO-034`

## 决策

1. TC-13 继续由 Workspace-first 普通指令触发，不增加 Scenario 选择器。固定适配器只允许 `sales-020` 的问卷 CSV 与规则 Markdown，并绑定逻辑 ID、文件名、展示路径、allowlist、声明大小、file ref 和冻结字节。
2. 服务端严格解析 CSV 编码、唯一表头、样本 ID、0..10 整数评分、中文数字与空值；未知中文、负数、小数、越界、CSV 注入、重复 ID、错列或损坏输入 fail closed。
3. 服务端从批准 Markdown 的安全行号动态解析清洗、阈值、优先级、排除、输出列和报告结构。未知、重复、冲突、第四画像或未知强制栏目不得静默通过。
4. 每个原始行保留 raw/cleaned 值、转换、全部命中画像、是否应用优先级、最终标签或排除原因、duplicate_of、source locator 和 rule refs。
5. 来源没有定义“重复样本”的比较键。固定适配器采用 `exact_non_id_payload`：除样本 ID 外全部原始字段完全相同才视为重复，并保留第一条；这是 `policy_assumption/review_required`，不是来源已经澄清的业务规则。
6. canonical 没有多标签 witness，前台必须显示 `0`，不能声称当前数据已经验证优先级；变体加入真实多标签样本后才投影裁决。
7. 规则只批准栏目，没有批准话术、功能、行业结论或销售排序。Markdown 中只能生成 `draft_template/no_approved_strategy_source`，并明确待销售负责人补充和批准。
8. 两份工件是 `客户画像及销售策略.md` 与 `客户画像逐样本台账.csv`。Verifier 重读两份批准源字节，再独立解析最终 Markdown/CSV，逐字段核对动态计数、画像、重复、locator、规则引用、报告结构和无动作边界。
9. `customer_segmentation_outcome` 同时写入 Artifact 和 EffectReceipt，并随 Snapshot/PostgreSQL 持久化。前台分别投影确定性来源/工件检查、清洗事实、策略人工复核和外部动作未发生。
10. 原 FORTE 输入保持只读；`external_action=none`。`completed` 只说明本轮模型与确定性合同通过，不表示分类适用于真实客户、策略获批或销售动作发生。

## 前后端事实

| 前台 | 服务端事实 | 不允许推断 |
| --- | --- | --- |
| 这是公开样本的画像清洗与策略草案 | `customer_segmentation_outcome.status=sales_review_required` | 真实客户研究或销售效果已验证 |
| 来源、Markdown、CSV 确定性检查通过或失败 | Artifact `verifier_status/checks[]`、EffectReceipt `status` | 画像业务适用或策略已批准 |
| 11 原始行、8 分类、3 排除等动态事实 | outcome 的 counts、`profile_counts`、`samples[]` | 数量必须固定为当前版本 |
| 重复口径仍需业务确认 | `duplicate_policy_assumption=exact_non_id_payload`、`policy_assumption_review_required=true` | 来源已经定义重复主键 |
| canonical priority witness 为 0 | `priority_witness_count=0` | 当前来源已验证优先级裁决 |
| 策略待销售负责人补充和批准 | `strategy_evidence_status=no_approved_strategy_source` | 页面模板是确定性销售建议 |
| 客户、CRM、商机与营销动作均未发生 | `external_action=none`、禁止副作用 | 已联系客户、写 CRM 或执行营销 |

## 拒绝的替代方案

- 写死样本 ID、阈值或当前分布后自证：拒绝。合法来源变化必须动态进入结果。
- 把 `重复保留第一条` 擅自解释为手机号、公司名或任意相似度去重：拒绝。当前只允许公开的保守假设并要求复核。
- 为满足报告栏目虚构话术、产品功能和销售优先级：拒绝。没有批准来源就只能给空模板和边界。
- 用 Artifact 绿灯替代销售判断：拒绝。确定性文件正确、分类业务适用、策略批准和外部动作是四种不同事实。
- 从浏览器 fixture 反推服务端答案：拒绝。E2E fixture 由服务端公共 manifest 导出，只验证投影与布局。

## 验证门

- canonical 当前动态为 11 原始行、10 唯一载荷、1 精确重复、8 分类、2 无法归类、合计排除 3，画像为技术/安全/敏捷 `3/3/2`，priority witness `0`；这些不是生产 success 常量。
- 阈值、优先级、缺失默认、新样本、sample ID、行业/规模与真实多标签样本变异动态更新相应字段。
- exact payload 重复保留首条；重复 ID、CSV 注入、非法分数、未知中文、来源错配、第四画像、未知规范与成果篡改 fail closed。
- 真实 PostgreSQL 重启后两份 Artifact、EffectReceipt、outcome 与下载字节一致；只证明顺序 Runtime 恢复。
- 1440 px 三栏和 390 px 单栏覆盖 canonical、动态阈值、多标签 witness 与 Verifier failure；自动化与截图不证明用户理解或业务价值。
