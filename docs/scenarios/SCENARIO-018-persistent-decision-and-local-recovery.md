# SCENARIO-018：重启后保留证据决定，并只恢复受影响分支

## 用户与触发

发布负责人要求 Agent 研究整个 FORTE 资料库。四条 Finding 已唯一定位并形成部分成果，另一条
Finding 的逐字片段在同一文件中出现三次。Agent 不能替用户随机选择位置，用户需要先比较候选，
再决定是否让该 Branch 继续。

## 主路径

1. Agent 自主检索整库并产生 `exact` 与 `ambiguous` 的 EvidenceResolution；四条已完成 Branch
   和 ArtifactVersion v1 立即保留。
2. 页面生成 Decision Packet，列出候选原文、冲突原因、只重跑哪个 Branch、剩余预算和不会发生
   的外部动作。
3. API 重启后，Snapshot 恢复开放的 DecisionRequest、候选、v1 和已完成 Branch；不自动重放在途
   模型调用。
4. 用户选择一个候选。服务端以 expected version 和幂等键写入 DecisionRecord，再从检查点恢复
   目标 Branch；其他四条 Branch 不重新调用模型。
5. 新结果形成 ArtifactVersion v2，v1 仍可回看。再次重启后两版成果、决定回执和最终位置保持一致。

## 异常路径

| 异常 | 服务端行为 | 用户动作 |
| --- | --- | --- |
| 三个候选都合法 | `ambiguous`，不随机采用 | 选择候选、暂不采用或只重试该 Branch |
| 来源修订变化 | `stale`，不静默移动 Anchor | 查看修订差异并重跑受影响 Branch |
| 候选越界或完整性失败 | `rejected`，安全失败 | 更换来源；不能强制采用 |
| 旧 expected version | 409，保留用户草稿 | 重新 GET Snapshot 后再决定 |
| running round 在重启中断 | 只恢复最后完成检查点 | 明确继续，不声称恢复在途调用 |

## 来源与边界

- Stakeholder 负例与两张截图：`USER-FEEDBACK-20260826-ACTIONABLE-RECOVERY`。
- 研究依据、五态 Resolution、Decision Packet 和验证设计：`ACTIONABLE-HITL-RECOVERY-RESEARCH-20260826`。
- 本场景验证的是状态、定位和恢复协议，不证明 Finding 语义正确、用户价值或外部动作能力。
