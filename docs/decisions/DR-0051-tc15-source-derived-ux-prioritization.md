# DR-0051：TC-15 全量来源推导、逐组规则引用与人工方案边界

- 状态：Limited Verified；实现 `22aa685`、真实 Provider、PostgreSQL、下载复核和 [PR #67 远端门](https://github.com/Dickey007s/lenovo_agent/actions/runs/33226861708/job/99032179492) 已通过
- 日期：2026-08-29
- Source：`USER-FEEDBACK-20260829-TC15-SOURCE-DERIVED-UX-PRIORITIZATION`
- Scenario：`SCENARIO-036`

## 决策

1. TC-15 仍由 Workspace-first 普通指令触发，不增加 Scenario 选择器。固定适配器只允许 `uiux-021` 的一份 XLSX、一份规则 Markdown 和一份页面规范 DOCX。
2. 服务端从批准 XLSX 原始字节读取全部行，不使用 bounded Preview 计算。每行保留 locator 和全部原字段，并进入 included、excluded 或 manual review。
3. 严重度、全量分母、3%/5% 频次规则、3×3 优先级矩阵与页面规范全部从批准来源解析。3% 的闭/开区间冲突被显式保留；恰好命中边界时不应用优先级矩阵。
4. 每组保存实际应用的规则引用。`rule_id` 内容寻址到语义槽位、来源摘录与参数；locator 单独保留。正常组应用严重度、频率和优先级三条规则，边界组保留两侧频率规则且无优先级规则。
5. 来源未批准操作到页面元素的 crosswalk。24 项映射均标为 `controlled_adapter_assumption/review_required`；新增未知操作进入 manual review。
6. 来源也未批准具体技术方案。成果只保留来源矩阵处置、页面规范与待审批模板，`suggestion_status=no_approved_solution_source`。
7. 两份工件为 `交互规范优化方案.csv` 和 `交互行为逐行归因台账.csv`。Verifier 重读三份批准来源，并重新解析最终 CSV bytes，逐字段核对规则引用、全量分母、排序、contributors、逐行守恒和边界。
8. `ux_prioritization_outcome` 同时进入 Artifact、EffectReceipt、Snapshot/API 和 PostgreSQL。前台分四层显示确定性验证、全量覆盖/数据质量、逐组来源推导和方案/生产动作未发生。
9. 原 FORTE 输入保持只读，`external_action=none`。`completed` 只说明来源、计算、排序和工件结构门通过，不表示具体方案获批或体验改善。

## 前后端事实

| 前台 | 服务端事实 | 不允许推断 |
| --- | --- | --- |
| 完整日志覆盖 | `source_row_count/analyzed_row_count/row_decisions[]` | bounded Preview 等于完整来源 |
| P0-P4 与每组“为何这样分级” | `groups[]`、`rule_refs[]`、`rules[]`、locator | P0 已立项或规则由浏览器计算 |
| 3% 边界定义冲突 | `rule_conflicts[]` 与边界组两侧 frequency refs | 系统已替 UX 负责人选择口径 |
| 重复事件与映射假设 | `duplicate_*`、`mappings[]`、`unmapped_count` | 重复已去重或映射来自 DOCX |
| 方案待批、生产未改 | `suggestion_status`、`human_review_required=true`、`external_action=none` | 方案有效、UI 已修改或实验已启动 |

## 验证门

- canonical 完整来源、尾部独有组合和当前动态分布；当前数字不得成为生产 success 常量。
- 合法新增行、同步新增痛点、阈值/严重度/矩阵/页面规范顺序变化，只更新受影响投影和内容寻址规则引用。
- 来源消除 3% 冲突后仍通过；恰好 3% 且冲突存在时保持待人工确认。
- 多/隐藏 Sheet、宏/外链、截断、额外/缺失规范表、非法值、未知规则和成果篡改 fail closed。
- PostgreSQL 重启后 Artifact、EffectReceipt、outcome 与下载字节一致；只证明顺序 Runtime 恢复。
- 1440 px 三栏和 390 px 单栏覆盖 canonical、动态阈值和 Verifier failure；自动化与截图不证明用户理解。

## 研究边界

Microsoft HAI Guidelines、Google HEART 与 W3C 状态消息/目标尺寸只支持交互设计和可访问性取向，不批准当前排序或解决方案，也不能替代真实用户研究。当前纵切不是线上遥测、通用 UX 引擎、自动修复、A/B 实验或生产发布。
