# SCENARIO-037：只保留一个可复核的当前结论

## 用户与触发

- 用户：查看 Agent 结果、需要判断哪份说明可相信的办公用户。
- 触发：固定确定性 Effect 已生成完整成果，而 Analyst 同时返回摘要、发现或后续建议。
- 痛点：旧 TC-15 Run 同时展示“完整 212 行已复算”和“只看到前 60 行、还需统计 212 行”，用户无法判断哪一个是当前事实。

## 主路径

1. Planner 通过服务端校验，固定适配器在隔离 Run Workspace 生成并验证成果。
2. Runtime 从 passed EffectReceipt 生成内容寻址的 `verified_effect_context`；TC-15 包含 212/212、87、P0-P4 和紧凑分组事实。
3. Analyst 在既有安全范围内返回说明。服务端先做结构、引用与 Anchor 校验，再比较覆盖、计数、分组优先级、方案边界和 follow-up。
4. 一致说明进入公共当前结果；不可比较说明只作补充；矛盾或过期说明被拒，不进入 Finding、建议、Brief 或 Commit。
5. 前台先展示确定性成果，再显示说明采用回执。被拒原因默认折叠，当前结论只有一份，用户无需额外确认。

## 异常路径

- 模型声称只分析 60/120 行，或要求重新统计已经完成的 212 行：`contradictory/rejected`。
- 模型把来源矩阵 P0 改写为 P1，或数量与当前 outcome 不一致：`contradictory/rejected`。
- 模型把 `no_approved_solution_source` 下的具体技术方案写成确定结论：`contradictory/rejected`。
- 模型返回时 outcome revision 已变化：`stale/rejected`。
- 模型没有提供可比较计数或优先级：`partial/supplemental`，不覆盖成果。
- 没有确定性 Effect：`not_applicable/model_only`，模型结果继续标记人工复核。
- 只有 failed/bounded Artifact 或 Receipt：前台明确没有可采用确定性成果，不显示权威提示。

## 完成条件

- passed Artifact、EffectReceipt 与下载 bytes 在模型说明被拒后仍保留。
- `called=true/output_used=false` 与 rejection receipt 同时可见；公共 Result、Finding、Follow-up、Brief 和 Commit 不含被拒草稿。
- Snapshot、named SSE、API、PostgreSQL 重启和前台对 `narrative_reconciliation` 的投影一致。
- 1440/390 页面只显示一个当前结论，冲突详情可审计但默认折叠。

## 边界

该场景不证明模型说明语义完整，也不证明确定性 outcome 本身具有外部效度。没有结构化 outcome 的普通任务仍需人工判断；自动化和截图不是用户研究。
