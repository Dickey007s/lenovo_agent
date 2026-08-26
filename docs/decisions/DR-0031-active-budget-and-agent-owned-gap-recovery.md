# DR-0031：按实际执行计时的预算与 Agent 自有缺口恢复

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`，限 active deadline、精确停止原因、Gap 处置与确定性恢复路径 |
| 日期 | 2026-08-26 |
| 触发来源 | [`USER-FEEDBACK-20260826-ACTIVE-BUDGET-AND-GAP-RECOVERY`](../sources/USER-FEEDBACK-20260826-budget-and-evidence-gap-recovery.md) |
| 延续依据 | [`ACTIONABLE-HITL-RECOVERY-RESEARCH-20260826`](../research/ACTIONABLE-HUMAN-DECISION-AND-FAILURE-RECOVERY-20260826.md) 与 `DR-0030` |
| 场景 | [`SCENARIO-017`](../scenarios/SCENARIO-017-resume-agent-owned-evidence-gap.md) |
| Evidence | [`ACTIVE-BUDGET-AND-AGENT-GAP-RECOVERY-20260826`](../evidence/ACTIVE-BUDGET-AND-AGENT-GAP-RECOVERY-EVIDENCE-20260826.md) |
| 延续/替代 | 延续 Branch 级恢复；替代把人工等待计入 deadline 和把无 Anchor Gap 呈现为源文件修复请求的行为 |

## 问题定位

旧 Runtime 从 Run 建立时持续累计墙钟时间。Agent 进入 `waiting_input` 后，用户阅读证据、开会
或离开页面的时间仍会消耗 deadline。恢复一条 Branch 时，Run 可能尚未发起新调用就进入预算
终态。旧 Gap 页面又把“候选文件”和“证据不足”交给用户，却没有说明真正失败的是模型结构、
原文定位还是证据覆盖，用户只能误以为自己需要修改表格。

## 决策

1. `deadline_seconds` 默认值从 `120` 提高十倍为 `1200`，合法范围从 `20..300` 调整为
   `20..3000`。轮次数、模型调用数和每轮文件数仍是独立边界，不随时间预算放开。
2. `budget.elapsed_ms` 只累计 Agent active 区间。进入 `waiting_input`、执行 pause 或到达终态时
   冻结计时；从合法 resume 恢复 active 计时。持久化恢复从最后一个权威 Snapshot 的 elapsed
   继续，不重放在途模型调用。
3. 预算拒绝按实际门槛写入 `budget.stop_reason`：模型调用耗尽显示“模型调用预算已耗尽”，
   active deadline 耗尽显示“Agent 执行时间预算已耗尽”，轮次门由 Evidence Gate 记录。
4. 无 Anchor 的 Evidence Gap 统一投影为“Agent 执行缺口”。前台先说明发生了什么、只影响哪
   个 Branch、已经保留什么、用户现在能做什么，不再暗示源文件已错。
5. Gap 恢复上下文必须由 Snapshot 事实派生：`recovery_kind`、Branch objective/status、
   `input_file_refs/verified_file_refs`、Planner/Analyst receipt 和 Run terminal 状态。浏览器不得
   从自然语言猜错误类型或原文位置。
6. `waiting_input` 时，用户可以留空反馈并直接“让 Agent 只重试此分支”；有补充反馈时先
   versioned steer，再 versioned resume 该 Branch。terminal Run 不接受 resume，只能创建目标
   收窄但仍重新冻结整库索引的新 Run。
7. 候选文件保留安全 Preview，但无 Anchor 时不显示伪高亮。页面明确“这里没有高亮，不是让
   你猜哪一行”，以及“不会要求你改源文件、不会执行外部动作”。

## 技术差异及其交互后果

| 技术差异 | 旧用户流程 | 新用户流程 | 前台输出 |
| --- | --- | --- | --- |
| 墙钟 deadline -> active deadline | 人在阅读时预算继续减少，恢复后可能立即停止 | 人可以核对证据后再继续，预算只花在 Agent 工作上 | `Agent 执行时间`、已用 active 秒数、精确停止原因 |
| 120 秒默认 -> 1200 秒默认 | 一到两次真实模型往返就接近边界 | 多轮 Planner/Analyst 有可用余量 | 默认 1200 秒，上限 3000 秒 |
| “缺少证据” -> Agent 执行缺口 | 用户猜文件哪里错、该改什么 | 先知道 Agent 哪一步没完成，再直接重试最小 Branch | 原目标、尝试文件、调用/采用、保留项、无外部动作 |
| 强迫用户补材料 -> 可选线索 | 用户不知道也无法推进 | 不懂可以留空，系统仍能按确定性恢复指令重试 | 可选反馈框、主按钮“只重试本分支” |
| terminal resume 暗示 -> 新 Run | 点继续后无效或误以为旧调用复活 | 终态明确创建独立任务，旧事实不变 | “创建新任务继续此分支”、旧 Run 已结束 |
| 文件候选 -> 无伪定位 | 整份表格出现但没有问题位置 | 明确文件只是本轮尝试范围，不要求用户猜行 | 无 Anchor 警示、安全 Preview、无高亮说明 |

## 前后台统一事实

| UI 状态/动作 | 服务端事实 | 用户能做什么 | 隐藏或不得声称 |
| --- | --- | --- | --- |
| Agent 执行时间 | Contract `deadline_seconds` 与 Snapshot `budget.elapsed_ms` | 设置 20 到 3000 秒，查看已用 active 时间 | 人工等待耗时、硬取消在途 HTTP |
| 精确预算终态 | `budget.stop_reason`、`loop_budget_stopped` | 知道是调用、时间还是轮次边界 | 统一 raw `budget_exhausted` |
| Agent 执行缺口 | `next_step.recovery_kind`、Gap/Branch、model receipt | 识别结构、定位或覆盖问题 | 源文件已错、模型没调用 |
| 尝试过的文件 | Branch `input_file_refs`、Gap `candidate_file_refs` | 打开安全 Preview 了解上下文 | 这些文件必然含答案 |
| 只重试本分支 | nonterminal waiting Branch + expected version/idempotency | 可选 steer 后 resume 一条 Branch | 重跑其他 Branch、修改文件 |
| 终态续办 | terminal status + Branch objective + 新 Task Contract | 创建新的独立 whole-workspace Run | 续跑旧 Provider 调用或覆盖旧 ArtifactVersion |

## 验证与边界

- 单测覆盖新默认/上限，以及在 `waiting_input` 期间 elapsed 不增长；既有预算、Branch、幂等和
  持久化测试继续通过。
- Playwright 覆盖可恢复 Gap 的可选反馈、只重试目标 Branch、terminal Gap 创建新 Run，且
  页面首屏可见“问题在 Agent 的交付，不在源文件”和主动作。
- 截图和自动化不证明真实用户理解、模型质量、成本收益或生产 SLA。
- deadline 仍只阻止发起新的模型调用，不硬取消正在进行的 HTTP 请求；当前仍最多三轮、
  单 Controller、只读结果、`review_required=true`、`external_action=none`。
