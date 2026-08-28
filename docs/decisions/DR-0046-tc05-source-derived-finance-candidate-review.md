# DR-0046：TC-05 来源推导跨期财务候选与人工处置边界

- 状态：Accepted；来源合同、独立 builder/verifier、三状态前台与 PostgreSQL 顺序恢复已落地，最终工程门见对应 Evidence
- 日期：2026-08-29
- Source：`USER-FEEDBACK-20260829-TC05-SOURCE-DERIVED-FINANCE-REVIEW`
- Scenario：`SCENARIO-032`

## 决策

1. TC-05 继续由 Workspace-first 普通指令触发，不增加 Scenario 选择器。固定适配器只允许 `Finance-018` 的 2025 上半年、2025 下半年和 2026 三份 XLSX；逻辑期间、文件名、展示路径、allowlist、声明大小和冻结字节必须满足固定来源合同，且三份字节互异。
2. 服务端直接解析批准 XLSX 原始字节。每条业务行保留期间、`source_file_ref`、工作表、Excel 行号和 `A:J` locator；两个同名“方向”列按固定位置区分期初与期末，不生成 `direction#2` 之类含糊字段。
3. 同一期间的“科目名称+客商名称”必须唯一。重复键、未知方向、非法或非有限金额、公式、错误单元格、空业务表、损坏工作簿或来源错配均 fail closed；当前固定适配器不自行汇总重复行。
4. 2026 未付只取正数贷方期末余额，2026 未收只取正数借方期末余额。两个 CSV 只绑定 2026 内容来源，并逐行保留金额、方向和 Excel locator。
5. “僵尸账款候选”只是一条固定启发式：同一科目和客商在三个期间均为正数借方期末余额，且金额完全相同。候选为 0、1 或多条都可以通过确定性计算；`check-finance-zombie` 验证枚举是否与批准来源重算一致，不要求候选为空。
6. 输出真实 `未付统计.csv`、`未收统计.csv` 和 `跨期核对说明.md`。Markdown 绑定三个期间，列出候选、三期金额和位置、方法、局限、复核动作与退出条件。
7. Verifier 必须重新读取批准来源，并独立解析已生成 CSV/Markdown，逐字段核对表头、行、唯一键、排序、金额、合计、locator、候选集合和边界文本；不能使用生成前列表自证。
8. `finance_review_outcome` 同时写入三份 Artifact 和 EffectReceipt，并随 Snapshot 持久化。前台分别投影：来源/计算/成果结构、当前明细与风险候选、最终财务处置。
9. 候选大于 0 使用琥珀色“需财务复核”，不是系统失败；候选为 0 也不能写成“无账务风险”。绿色 Artifact 只证明固定计算与文件结构，不证明会计结论。
10. 原 FORTE 输入保持只读，`external_action=none`。系统不付款、不核销、不记账、不确认坏账，也不修改来源工作簿。

## 前后端事实

| 前台 | 服务端事实 | 不允许推断 |
| --- | --- | --- |
| 这是跨期风险候选，不是付款、核销、记账或坏账确认 | `finance_review_outcome.status=review_required`、`decision`、`human_review_required=true` | Agent 已完成会计处置 |
| 来源、计算与三份成果确定性检查通过或失败 | Artifact `verifier_status/checks[]` 与 EffectReceipt `status` | 僵尸账款业务定义正确或可以自动核销 |
| 2026 未付/未收数量与合计 | `finance_review_outcome.unpaid_count/unpaid_total/unreceived_count/unreceived_total` | 两个 CSV 合并了三个期间 |
| 当前发现 N 条候选 | `finance_review_outcome.candidate_count/candidates[]` | N 必须为 0；候选就是坏账或僵尸账款定论 |
| 展开候选的三期金额与位置 | `candidates[].sources[]` 的期间、file ref、工作表、行号、locator 和金额 | 浏览器自行抽取或计算候选 |
| 最终财务处置尚未发生 | outcome 与 EffectReceipt `external_action=none`、`original_inputs_modified=false` | 已付款、核销、记账、确认坏账或修改原表 |

## 拒绝的替代方案

- 用固定“无候选”作为绿色 Gate：拒绝。合法来源出现候选是业务发现，不是验证故障。
- 生成列表后再用同一内存列表验证输出：拒绝。Verifier 必须重读批准来源和生成字节。
- 把两个 CSV 的三份任务上下文当作内容来源：拒绝。两个明细只来自 2026，三期来源只属于跨期说明与 EffectReceipt。
- 同期间重复键静默覆盖或自行求和：拒绝。固定输入缺少主体、科目编码、币种和子项合同，必须 fail closed。
- 把绿色文件卡写成“可付款/可核销”：拒绝。确定性文件检查、业务候选和最终动作分层展示。

## 验证门

- 将 2026 年绵阳长城发展融资担保有限公司的借方期末余额由 170 万改为 150 万时，产生 1 条候选，三份 Artifact 与 EffectReceipt 仍通过；前台显示琥珀色人工复核。
- 再改变任一期间解除相同余额时，候选回到 0；只改变 2025 来源且未形成候选时，两个 2026 CSV 字节保持不变。
- 2026 新增、删除、改额或借贷方向变化只影响来源驱动的明细、合计和跨期说明。
- 重复键、空表、未知方向、非法/非有限金额、公式、错误单元格、缺/多/错路径来源、同内容冒充和损坏 XLSX 均失败。
- 篡改成果金额、行、locator、候选、旧固定文案或损坏 CSV/Markdown 时，Artifact 与 EffectReceipt 转红。
- 真实 PostgreSQL 重启后三份 Artifact、EffectReceipt、`finance_review_outcome` 和下载字节一致；这只证明顺序 Runtime 已提交恢复。
- 1440 px 三栏和 390 px 单栏覆盖 0 候选、1 条候选与 Verifier failure；截图和自动化不证明财务用户理解或业务政策正确。
