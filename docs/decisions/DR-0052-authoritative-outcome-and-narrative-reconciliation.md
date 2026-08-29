# DR-0052：服务端确定性成果与模型说明对账

- 状态：Draft，待真实 Provider、PostgreSQL、完整工程门与 PR 证据收口
- 日期：2026-08-29
- Source：`USER-FEEDBACK-20260829-DETERMINISTIC-OUTCOME-NARRATIVE-CONFLICT`
- Scenario：`SCENARIO-037`

## 决策

1. 不新增第九模块。`narrative_reconciliation` 是模块 7 `Artifact Workspace & Verifier` 与模块 8 `Checkpoint, Event & Governance Control` 的通用子能力。
2. 固定确定性 Effect 仍先于 Analyst 执行。Runtime 仅从已通过 EffectReceipt 生成 `verified_effect_context`，其中包含成果类型、内容寻址版本、紧凑计数和必要的分组事实；bounded 文件 Preview 继续只承担原文引用。
3. Analyst 通过既有结构、范围与 Anchor 校验后，Runtime 才执行叙事对账。`called=true` 只证明模型返回；只有 `model_disposition=adopted` 才设置 `output_used=true` 并允许模型 Result、Finding、Follow-up、Brief 与 Commit 进入公共当前结论。
4. 公共协议区分 `consistent / partial / contradictory / stale / not_applicable`，权威区分 `deterministic_outcome / model_only`，采用区分 `adopted / supplemental / rejected`。冲突回执只保留稳定 ID、类型、脱敏摘录、结构化事实路径、期望/观测和严重度，不公开原始 Provider response 或思维链。
5. `contradictory` 与 `stale` 拒绝模型说明；`partial` 只作内部补充草稿，不覆盖确定性成果；`consistent` 才采用。没有确定性成果的普通研究任务保持 `model_only/review_required`，不能伪称已经验证。
6. 模型说明被拒不删除已通过 Artifact、EffectReceipt 或下载 bytes。若确定性成果完整，Run 仍可完成，但公共 Result/发现/建议只显示服务端权威投影；模型冲突默认折叠在轨迹中且不产生用户待办。
7. 前台权威提示必须同时满足：`reconciliation.authority=deterministic_outcome`，并且存在 passed Artifact 或 passed EffectReceipt。失败、受限或空回执只能显示“尚未形成可采用的确定性成果”。
8. TC-15 是首个纵切：检测宣称只覆盖 60/120 行、与 212/87 或 P0-P4 不一致、把未批准技术方案写成当前结论，以及重复要求已经完成的全量计算。协议名称、状态机和前台组件不使用 TC-15 专属名称。

## 技术差异与交互影响

旧流程把 `Analyst returned`、`output_used` 和 `Run completed` 混成一个绿灯。新流程把模型候选放在服务端成果之后对账：用户不再同时看到“212 行已算完”和“还需统计 212 行”两套真相；被拒说明仍可审计，但不会形成错误 Finding 按钮或下一步任务。

这不是把模型从产品中拿掉。模型继续负责整库选证据和可审查说明；服务端只对当前已有结构化事实做一致性门。没有确定性 outcome 的任务仍是 model-only 并等待人工复核。

## 前后端事实

| 前台 | 服务端事实 | 隐藏/禁止推断 |
| --- | --- | --- |
| 模型说明已采用 | `status=consistent`、`model_disposition=adopted`、`output_used=true` | 模型语义全面或方案有效 |
| 模型说明仅补充 | `status=partial`、`model_disposition=supplemental`、`output_used=false` | 补充草稿可以覆盖成果 |
| 成果完成、模型说明未采用 | `status=contradictory|stale`、`model_disposition=rejected`、passed Artifact/Receipt | Artifact 失败或用户需要修文件 |
| 以服务端确定性成果为准 | `authority=deterministic_outcome` 且至少一个 passed Artifact/Receipt | failed/bounded 回执也有权威结论 |
| 尚无可采用确定性成果 | 没有上述权威组合 | 模型说明或失败回执可以冒充当前结论 |
| 折叠冲突详情 | `conflicts[]` 脱敏投影 | 原始 Provider response、Prompt、CoT |

## 验证门

- 原历史矛盾样本必须被拒：模型 returned，`output_used=false`，公共 Result/Brief/Finding/Follow-up 不含草稿，passed Artifact 不变。
- 准确复述结构化事实可 adopted；不提供可比事实为 partial/supplemental；旧成果版本为 stale/rejected。
- failed/bounded-only 前台不得显示确定性权威提示。
- PostgreSQL 重启后对账状态、冲突回执、Artifact/Effect 和公共 Result 选择一致。
- live manifest 同时记录 model returned、model adopted、authority、reconciliation 与冲突种类；矛盾而 `output_used=true` 必须失败。
- 1440 与 390 px 只显示一个当前结论，拒绝详情默认折叠且无横向溢出。

## 边界

当前对账只证明模型叙事与当前结构化确定性事实是否一致，不证明语义完整、方案正确、排序外部有效或体验改善。首个具体规则覆盖固定 uiux-021；它不是通用自然语言事实证明器、用户研究、多 Worker 协调或生产动作审批。
