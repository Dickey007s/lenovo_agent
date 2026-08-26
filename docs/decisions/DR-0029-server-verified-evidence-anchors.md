# DR-0029：服务端验证的证据锚点与原文定位审查

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`，限有界安全预览、引用唯一匹配和确定性前端回归 |
| 日期 | 2026-08-26 |
| 触发来源 | [`USER-FEEDBACK-20260826-23`](../sources/USER-FEEDBACK-20260826-23-pinpoint-agent-evidence.md) |
| 场景 | [`SCENARIO-015`](../scenarios/SCENARIO-015-pinpoint-and-compare-agent-evidence.md) |
| Evidence | [`PINPOINT-EVIDENCE-REVIEW-20260826`](../evidence/PINPOINT-EVIDENCE-REVIEW-EVIDENCE-20260826.md) |
| 延续/替代 | 延续 `DR-0028` 的问题审查页；替代其“只能定位到文件”的当前实现边界 |

## 问题定位

`DR-0028` 解决了“问题没有入口”，但没有解决“入口打开后仍不知道问题在哪里”。Finding
只有 `file_refs`，前台能证明关联文件属于本轮范围，却不能从长代码、日志、文档或表格中
指出 Agent 实际依据的段落。若由浏览器搜索 Finding 文案生成高亮，位置将变成客户端猜测，
破坏“每个 UI 状态由服务端事实产生”的统一策略。

## 决策

1. Analyst 对每条 Finding 提交逐字 `evidence_quotes` 候选和证据角色，但不得提交可信行号。
2. Runtime 在传给 Analyst 的同一份有界安全内容上解析候选：文本必须唯一匹配，表格必须
   唯一匹配一行；只接受 Finding 自身 `file_refs` 且属于本轮批准范围的引用。
3. Runtime 清除模型候选，只把服务端生成的 `evidence_anchors` 写入 Round Result、
   ArtifactVersion 和公共 Snapshot。Anchor 包含 `file_ref/role/label/locator_kind/start/end/excerpt`。
4. 每条新 Finding 至少需要一处已解析 Anchor。零 Anchor 的候选结果不采用；在同一轮模型
   调用预算内，Runtime 最多允许 Analyst 再提交一次更长、更唯一的逐字候选。首次拒绝、修复
   调用和最终采用/拒绝都写入有序 Trace，动画、模型配置名和模型自报位置不能替代服务端校验。
5. 前台将长段 Finding 重组为“Agent 判断 -> 编号证据链 -> 原文高亮”。证据角色使用中文
   `设计预期/实际观测/支持证据/矛盾证据/相关上下文`；点击 Anchor 后切换文件并滚动高亮。
6. 文本定位是安全预览行；表格定位是数据行。PDF/DOCX 不声称原生页码或段落坐标，表格
   不声称单元格级验证。
7. 旧成果、Gap 和 proposal 没有 Anchor 时保留文件级审查，并明确“不会伪造高亮”。

## 技术差异及其交互后果

| 技术差异 | 旧用户流程 | 新用户流程 | 前台输出 |
| --- | --- | --- | --- |
| 文件级 citation -> 服务端 Evidence Anchor | 打开文件后自行全文搜索 | 先看原子证据，再一键跳到原文 | 证据编号、角色、文件、行范围、短摘录 |
| 模型自述 -> 服务端唯一匹配 | 无法知道位置是否真实 | 只看到服务端确认存在且唯一的片段 | “服务端已匹配原文”；无 Anchor 则不高亮 |
| 静默丢弃 -> 有界 Analyst 修复 | 用户不知道模型为何没有结果 | 看到“原文位置未通过，正在受控重试”，且重试消耗预算 | `analysis_validation_rejected`、两次独立 Model Receipt |
| 长结论 -> 预期/观测对照 | 在一段话中辨认两个来源 | 在两项证据间切换比较 | 设计预期、实际观测、判断关系 |
| 整份预览 -> 定位态预览 | 手工滚动代码/日志/表格 | 点击证据后自动切换、滚动、聚焦 | 定位条、行号、左侧标线、聚焦背景 |
| 引用边界继续显式 | 高亮容易被误解为结论正确 | 将“位置正确”和“语义成立”分开判断 | 黄色边界说明、`review_required=true` |

## 前后台统一事实

| UI 状态/动作 | 服务端事实 | 用户能做什么 | 隐藏或不得声称 |
| --- | --- | --- | --- |
| 证据链 | Finding `evidence_anchors[]` | 扫描证据角色和位置 | raw quote candidate、Prompt、CoT |
| 点击证据 | Anchor `file_ref/locator_kind/start/end` + Preview GET | 切换并跳到原文 | 客户端猜测行号、Run 已改变 |
| 高亮摘录 | Anchor `excerpt` 与 Preview 内容 | 对照服务端截取的原文 | entailment、数值/质量验证 |
| 服务端已匹配 | `result_validation` 后 `output_used=true` | 知道位置通过范围与唯一匹配 | 模型结论正确、文件已修改 |
| 无精确位置 | 旧 Snapshot 或非 Finding 记录无 Anchor | 继续文件级核对 | 静态示例、伪造高亮 |

## 验证与边界

- Python 单测覆盖文本行、表格行、候选清除、重复片段拒绝和整轮 Runtime 采用路径。
- Playwright 覆盖设计/观测证据切换、跨文件定位、滚动高亮、旧协议退化和移动端无横向溢出。
- 真实 `deepseek-v4-pro` Run 完成 2 轮、4 次调用，服务端采用 23 处 Anchor；另保留一次
  歧义短引用被拒的负例。详见 Evidence 与脱敏 manifest。该运行只证明 Provider 候选经过当前
  规则可被采用，不证明 Finding 语义正确。
- `Limited Verified` 不证明语义蕴含、模型正确、用户效率、信任、生产可靠性或业务价值。
