# USER-FEEDBACK-20260829-TC15-SOURCE-DERIVED-UX-PRIORITIZATION

## 来源

- 类型：Stakeholder 场景审计、交互验收与工程验收边界
- 日期：2026-08-29，Asia/Shanghai
- 场景：FORTE 固定 `uiux-021`，从完整交互日志、痛点规则和页面规范形成离线优先级台账
- 状态：已记录；实现结论由 `DR-0051` 与对应 Evidence 单独验证

## 问题定位

历史 `_ux_prioritization` 使用最多 120 行的 bounded Preview，而批准工作簿实际有 212 个数据行。旧成果恰好只覆盖前 120 行中的 66 个有效组合，漏掉后 92 行新增的 21 个组合；66 个重叠组合中还有 22 个频次档位因分母和计数变化而改变。旧 6/6 检查仍全部通过，因此是来源覆盖不足导致的 false green。

此外，旧实现把严重度、频次、优先级矩阵、操作到规范元素的映射、排序和具体优化建议写在生产代码里，再检查同一内存结果。它不能回答“这一组为什么是这个等级”，也会把没有批准来源的解决方案冒充为研究结论。

Stakeholder 要求：

1. 只从三份批准原始字节计算，完整覆盖 212 行，每行进入 included/excluded/manual review 之一。
2. 动态解析严重度、频次阈值、3×3 矩阵和 28 个页面规范元素；3% 边界冲突不得猜测。
3. 操作到规范元素没有批准映射表时，只能显示为固定适配器假设；具体方案保持待 UX 负责人补充/批准。
4. 每个聚合组必须保存实际使用的严重度、频率和优先级规则 ID 与 locator。规则 ID 使用“语义键 + 来源内容短哈希”，规则内容变化时引用随之变化；3% 边界组保存两侧频率规则且不应用优先级规则。
5. 两份 CSV 必须由服务端重读三份来源和最终 bytes 独立复核；来源冲突被消除时仍可通过，不能把“冲突必须存在”写成成功门。
6. 前台分开确定性验证、全量覆盖与数据质量、逐组排序与来源、方案待批和生产动作未发生；1440 px 与 390 px 均可读。

## 研究与交互依据

- Microsoft Research，[Guidelines for Human-AI Interaction](https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/)：只支持在界面中说明能力边界、显示上下文并提供纠正/接管路径，不批准 uiux-021 的排序或方案。
- Google Research，[HEART: Measuring the User Experience on a Large Scale](https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/)：只支持把行为信号与产品目标、指标建立可解释关系；反向说明单份离线日志频次不能证明体验改善。
- W3C，[Understanding Success Criterion 4.1.3: Status Messages](https://www.w3.org/WAI/WCAG21/Understanding/status-messages)：只作动态 Run、检查和错误回执可感知的前台参考。
- W3C，[Understanding Success Criterion 2.5.5: Target Size](https://www.w3.org/WAI/WCAG21/Understanding/target-size)：只作按钮与移动端可操作目标尺寸参考。

这些官方/研究来源不是当前日志的现场证据，不批准具体修复方案，也不能替代真实 UX 用户研究。

## 完成条件与局限

- 当前公开来源应动态得到 212 行、87 个组合和 P0-P4 分布；这些数字是当前来源观测，不是生产 success 常量。
- 阈值、矩阵、严重度、规范顺序、合法新行/痛点变化必须更新受影响事实和规则引用；错误输入和成果篡改 fail closed。
- 当前只是固定 `uiux-021` 的离线优先级适配器，不是用户研究、线上遥测、通用产品分析、设计效果证明、自动改 UI、A/B 实验或生产发布。
