# DR-0038：用用户任务语言呈现原表格位置恢复

- 状态：Accepted；本地工程门与 PR #48 PostgreSQL 顺序恢复门 `Limited Verified`
- 日期：2026-08-28
- Owner：Office Agent 项目组
- Source：`USER-FEEDBACK-20260828-SOURCE-LOCATION-USER-LANGUAGE`

## 场景与问题

TC-05 已经生成三个通过确定性检查的 Run Workspace 成果，但一条 Agent 说明仍未找到
`2026往来明细.xlsx` 中可跳转、高亮的具体行或单元格。旧页面把这件小而局部的问题写成
“审计项、待定位来源、同一来源影响内部步骤”，用户无法判断成果是否已经生成、现在需要
自己做什么，以及点击恢复会不会重做成果。

同样的 `source_location` 缺口还可能出现在两种不同状态：成果尚未通过，或旧 Run 已经终止。
三种状态不能共用一套“成果可用”话术。

## 决定

1. 浏览器先根据服务端 Artifact、EffectReceipt、Run 状态和 `recovery_kind=source_location`
   投影三种用户状态：成果已通过但位置待补、成果尚未通过且位置待补、旧 Run 已终止。
2. 已通过状态主标题固定回答成果与缺口：“成果已生成，还有 N 条说明缺少原表格位置”。
   首屏说明已知文件但缺少具体行或单元格，并明确成果文件不受影响、Agent 说明仍需人工复核。
3. 非终态、无结构化 EvidenceResolution 的普通定位缺口，主动作是“查找原表格位置”，只提交
   当前 Branch 的 versioned/idempotent `resume`。打开页面、查看成果和展开详情都不花下一轮预算。
4. 已通过状态提供“查看已生成成果”，只滚动到现有 Artifact 区，不生成、覆盖或重新验证文件。
5. `Branch/Gap/Resolution`、受影响内部数量、原始失败说明和恢复边界进入默认折叠的“技术详情”。
   这些事实保留可审计性，但不再承担首屏解释任务。
6. 若存在 `ambiguous` Resolution，仍要求用户从真实候选中选一个，不默认选择；若旧 Run 已终止，
   只能创建新任务，不伪装原地恢复。

## 前台与后端事实

| 用户看到什么 | 服务端事实 | 动作与边界 |
| --- | --- | --- |
| 成果已生成，说明位置待补 | 至少一个 Artifact；对应 EffectReceipt/Artifact checks 全部通过；Run 仍有 `source_location` Gap | 可查看成果；可只恢复一个 Branch；Run 不冒充 `completed` |
| 成果尚未通过，说明位置待补 | `source_location` Gap 存在，但没有全部通过的当前成果集合 | 不声称成果可用；只处理对应 Branch |
| 旧任务已结束，需要新建任务 | terminal Run + 保留的 `source_location` Gap | 创建新 Run；旧 Snapshot、ArtifactVersion 与回执不覆盖 |
| 已知文件，缺少行或单元格 | Gap `missing_file_refs[]` 和安全 Catalog 显示名 | 不是文件缺失、日期错误、金额验算失败或成果生成失败 |
| 技术详情 | 原始 Branch/Gap/Resolution、失败 detail 和数量 | 默认折叠，不从客户端合并事实反推 Worker 并行 |

## 交互影响

用户不再先解码 Runtime 术语，而是先完成一个判断：成果是否可用。若可用，下一步只有查看成果
或让 Agent 继续查找原表格位置；若不可用或 Run 已终止，页面明确改变话术与动作。技术事实没有
被删除，只是按“任务状态 -> 影响 -> 动作 -> 技术详情”的顺序渐进披露。

## 验证与边界

浏览器测试必须覆盖三种状态、技术详情默认折叠、已通过状态的成果入口、非终态只提交目标
`branch_id`、终态打开新任务路径，以及桌面/390 px 无页面级横向溢出。自动化与截图只能证明
事实投影、动作负载和布局，不能证明目标用户理解、效率或信任改善。Evidence Anchor 仍只证明
位置和来源成员关系，不证明 Agent 说明的语义、金额或完整性。
