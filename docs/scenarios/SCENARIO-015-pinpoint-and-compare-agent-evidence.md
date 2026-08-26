# SCENARIO-015：在原文中定位并对照 Agent 的判断依据

## 用户、触发与痛点

一名办公用户要求 Agent 检查一个搜索工作流为什么没有按设计调用新闻检索。Agent 读取
`workflow.py` 和 `search_agent.log` 后提出“查询改写与意图识别疑似未按设计生效”。旧审查页
只能打开这两份文件，用户仍需手工在长代码和日志中寻找相关段落，也无法立即分清哪一段是
设计预期、哪一段是实际观测。

## 主路径

1. Analyst 针对每条 Finding 返回 1 到 6 个逐字引用候选，并标注
   `expected/observed/support/contradiction/context` 证据角色。
2. 服务端只在本轮批准的 `file_ref` 和传给 Analyst 的有界安全内容中查找候选。文本必须
   唯一匹配到行范围；表格必须唯一匹配到一行。服务端据此生成 `evidence_anchors`，不接受
   模型自报行号。
3. 如果一条 Finding 没有任何可唯一定位的引用，候选分析不进入成果。预算允许时，Runtime
   给 Analyst 一次不含原文的安全校验反馈，要求改用更长且唯一的逐字引用；前台轨迹显示
   “原文位置未通过，正在受控重试”。修复仍失败时 Run 才按现有失败边界安全停止。
4. 用户打开 Finding 审查页。最上方先看到 Agent 判断，其下是编号证据链：设计预期、实际
   观测、支持或矛盾证据，每项显示文件名、位置和服务端截取的短原文。
5. 用户点击一项证据。审查页自动切换文件，顶部显示“正在核对”，预览滚动到对应文本行或
   表格行，并以高对比背景、左侧标线和行号标记。
6. 用户在同一页面逐项切换预期与观测，确认原文位置无误后，再独立判断 Agent 的语义结论
   是否成立。打开、切换和关闭审查页都不改变 Run version。

## 完成条件

- 每个新 Finding 至少有一处服务端验证过的 `evidence_anchor`。
- Evidence Anchor 包含稳定 `file_ref`、角色、业务标签、定位类型、起止位置和服务端原文摘录。
- 文本、代码、日志、PDF/DOCX 提取文本可定位并高亮行；CSV/XLSX 可定位并高亮表格行。
- 点击证据后文件、位置提示、高亮与 Snapshot 中的 Anchor 一致；浏览器不自行解析 Finding
  文案生成位置。
- 旧 Snapshot 或 Gap/建议没有 Anchor 时，页面诚实退化为文件级核对并明确无精确定位。

## 异常路径

| 异常 | 前后台行为 | 用户恢复 |
| --- | --- | --- |
| 模型引用不存在 | 服务端丢弃该候选；若 Finding 无剩余 Anchor，则在预算内最多修复一次 | 查看“未采用/受控重试”轨迹；仍失败时重新发起或调整目标 |
| 同一片段多处出现 | 视为不能唯一定位，不任选其中一处；要求 Analyst 改用更长原文 | 用户不会看到服务端猜出的任意位置 |
| 引用超出本轮文件 | 服务端拒绝，`output_used=false` | 查看模型已调用但未采用的回执 |
| Preview 截断 | Anchor 只能落在本轮实际提供的有界内容中 | 用户可打开现有安全预览；不得声称核对了截断外内容 |
| PDF/DOCX 无文本层 | 不生成文本 Anchor | 仅保留文件级关联或安全停止，不伪造页码 |
| 旧成果没有 Anchor | 前台显示“当前只能定位到文件” | 重新运行后使用新协议生成可定位 Finding |

## 来源与边界

- Stakeholder 来源：[`USER-FEEDBACK-20260826-23`](../sources/USER-FEEDBACK-20260826-23-pinpoint-agent-evidence.md)。
- 延续来源：[`USER-FEEDBACK-20260826-22`](../sources/USER-FEEDBACK-20260826-22-hierarchical-workspace-and-evidence-review.md)。
- 工程事实：安全 Preview、每轮 `input_file_refs`、Finding `file_refs`、Snapshot、顺序事件和
  `review_required=true`。
- 自动化与截图只证明协议映射、跳转和高亮，不证明用户理解、判断速度、模型质量或业务价值。
