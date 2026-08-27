# DR-0033：可退出的问题审查与分支状 Evidence Gap

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`；实现、自动化、真实 PostgreSQL 回归与截图已完成，目标用户效果仍待研究 |
| 日期 | 2026-08-27 |
| 触发来源 | [`USER-FEEDBACK-20260827-CLOSABLE-REVIEW-AND-BRANCH-LANES`](../sources/USER-FEEDBACK-20260827-closable-review-and-branch-lanes.md) |
| 上游协议 | [`DR-0032`](DR-0032-persistent-decision-and-local-recovery.md) |
| 场景 | [`SCENARIO-019`](../scenarios/SCENARIO-019-close-review-and-handle-one-branch.md) |
| Evidence | [`DR-0033-CLOSABLE-REVIEW-BRANCH-LANES-EVIDENCE-20260827`](../evidence/DR-0033-CLOSABLE-REVIEW-BRANCH-LANES-EVIDENCE-20260827.md) |

## 问题定位

服务端把开放的 `DecisionRequest` 放在 Run Snapshot 顶层，浏览器却只读取历史轮次中的兼容字段。
当用户从历史轮次打开 ambiguous Resolution 时，关闭动作漏传 `decision_request_id`，服务端返回
409；前端又把“回执写入成功”误作“允许关闭”的条件，因此形成不可退出的模态页。

Evidence Gap 同时被压缩为一排同权按钮。按钮只说“哪条分支缺证据”，没有在首屏显示分支使用了
什么材料、停在哪个 Gate、只影响哪里以及接下来能做什么，用户必须逐个点开才能理解任务结构。

## 决策

1. 浏览器以 Snapshot 顶层 `decision_requests[]` 为当前权威，并兼容读取旧轮次投影；`state=open`
   规范化为前端 `pending`。Finding/Resolution 操作优先使用待决单绑定的 Branch、来源修订和请求 ID。
2. 关闭或 Escape 先退出审查页，再异步写入 `defer`。回执成功时待决单保持可继续；409、断网或其他
   失败只显示非阻塞错误并刷新 Snapshot，不得重新锁住页面，也不得谎称暂缓已经记录。
3. 只把 Evidence Gap 区改为 Branch lane。每行固定呈现“分支 -> 当前材料 -> Evidence Gate ->
   下一步”，并由 `branch_id` 把 Gap、DecisionRequest、EvidenceResolution 和安全文件标签连接起来。
4. 分支行只投影服务端事实：Branch 状态、输入/已验证/缺失引用、Gap 描述、Resolution 状态和开放
   DecisionRequest。没有 Anchor 时不伪造行号，没有 Resolution 时不冒充“需要确认原文位置”。
5. 点击“确认原文位置”或“查看并处理”仍打开现有审查页；控制动作继续使用 expected version 与
   幂等键。分支图不是并行 Worker 运行证明，也不改变 Runtime 调度。

## 前后台统一

| 前台元素 | 服务端事实 | 用户动作 | 隐藏/禁止推断 |
| --- | --- | --- | --- |
| 分支身份与状态 | `branches[].branch_id/title/status` | 打开对应问题 | 内部 unit ID、Worker 数量 |
| 当前材料 | Branch `input_file_refs/verified_file_refs` + Workspace 标签 | 打开审查页后查看安全 Preview | 原始路径、完整哈希、内容已正确使用 |
| Evidence Gate | `evidence_gaps[]` + `EvidenceResolution.status` | 比较候选或查看缺口 | 语义正确、完整性、模型置信度 |
| 下一步 | 顶层 `decision_requests[]` 或 Gap recovery mode | 确认原文、查看并处理 | 文件已改、外部动作已执行 |
| 关闭审查页 | 浏览器先关闭；`decision` 回执决定是否已 defer | 稍后重开继续 | 失败回执伪装成成功 |

## 验收门

- 顶层 `DecisionRequest(state=open)` 能驱动 Resolution 处置，并携带正确 request/revision/Branch。
- defer 202 时关闭并形成回执；defer 409 时也能立即退出，并显示“回执未写入”的可恢复提示。
- Gap 区在桌面显示连续分支路径，在 390 px 堆叠但不产生横向溢出。
- 既有 accept/decline/defer/cancel、Branch 局部恢复、ArtifactVersion 和 PostgreSQL 门不回归。

## 边界

本决策修复协议投影和交互可达性，不修改 Runtime 的证据判定、调度或持久化模型。自动化与截图不是
用户研究；“更容易理解分支”在目标用户测试前仍是 `Draft`。
