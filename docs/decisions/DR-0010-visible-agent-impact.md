# DR-0010：用影响预演与变化回执呈现 Agent 操作价值

| 字段 | 内容 |
| --- | --- |
| Decision ID | `DR-0010` |
| Owner | Office Agent 项目组 |
| Date | 2026-08-20 |
| Status | `Verified`（固定 Demo 1 的限定工程范围） |
| Scope | Demo 1 固定客户 A 收入口径决定的提交前影响预演、提交后服务端变化回执和前后端结构化协议 |
| Scenario | [`SCENARIO-001`](../scenarios/SCENARIO-001-customer-a-durable-report.md) |
| Primary source | [`USER-FEEDBACK-20260820-03`](../sources/USER-FEEDBACK-20260820-03-agent-impact-visibility.md) |

## 1. 用户场景与问题

客户经理看到“CRM 正式收入 2400 万元”和“预测收入 2680 万元”的冲突时，不只需要知道应该点击哪个按钮，还需要在点击前看懂：经营分析会如何变化、客户回复是否重新核对、已经通过的风险页会不会被重写、是否会向客户发送内容。点击后，用户还需要确认这些变化是否真的由服务端落地，而不是只看到一个成功 Toast。

此前 Decision Inbox 用一段静态说明概括后果，无法逐项对比“之前与之后”，也没有独立的实际变化回执。完成条件是：服务端给出可执行选项及预期影响；前台提交前逐项展示影响；服务端完成 mutation 后把实际影响写入可持久化事实；前台再以变化回执展示实际版本、核对和外部动作边界。

关键异常包括旧 Snapshot 没有新字段、选项不可执行、选项与来源不匹配、版本冲突、mutation 结果未知和仍有其他 open Conflict。上述情况不得由前端猜测最终影响。

## 2. 来源与依据

| Source ID | 类型 | 精确引用 | 支持的判断 | 局限 |
| --- | --- | --- | --- | --- |
| `USER-FEEDBACK-20260820-03` | Stakeholder feedback | [`USER-FEEDBACK-20260820-03-agent-impact-visibility.md`](../sources/USER-FEEDBACK-20260820-03-agent-impact-visibility.md) | 把创新交互和 Agent 操作影响可见设为首要目标 | 不证明当前方案有效 |
| `HAI-GUIDELINES-CHI2019` | 同行评审研究与研究机构页面 | Microsoft Research, [Guidelines for Human-AI Interaction](https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/)，CHI 2019；2026-08-20 访问 | 支持让系统说明能做什么、正在做什么，并支持用户在 AI 交互中校正与控制 | 通用 HAI 指南，不定义本项目协议或界面，也不证明当前实现符合全部指南 |
| `GOOGLE-PAIR-FEEDBACK-CONTROL-2021` | 官方设计实践 | Google PAIR, [Feedback + Control](https://pair.withgoogle.com/guidebook-v2/chapter/feedback-controls/)；2026-08-20 访问 | 支持解释用户输入如何影响系统、尽快显示影响，并平衡自动化与用户控制 | 设计实践，不是本项目用户研究或运行证据 |
| `USER-FEEDBACK-20260811-INTERACTION-01`、`DR-0005` | 历史 Stakeholder 选择与内部决策 | Task Director 与 Decision Inbox 方向 | 影响预演应进入既有左工作区/右决定区，而不是另建审批页 | 历史实现只证明当时的工程代理门槛 |

## 3. 决策

采用“事实差异预演 + 服务端变化回执”的双时态交互：

1. `ConflictRecord.resolution_options[]` 由服务端暴露允许执行的决定，不由前端根据候选数组推断。
2. 每个选项包含 `expected_impact.changes[]`，逐项描述 `before → after`，并标记 `will_change / will_recheck / unchanged / no_external_action`。
3. Decision Inbox 在唯一主动作之前展示影响预演。用户先看见自己的决定、会改变的材料、会重新核对的材料、保持不变的材料和不会发生的外部动作，再提交控制命令。
4. `resolve_evidence` 携带 `resolution_option_id` 与来源引用；服务端校验选项可执行且来源匹配。
5. mutation 成功后，服务端把实际变化写入 `ControlEvent.impact_receipt`，包括任务版本、实际 ArtifactVersion、VerificationReport、Commit、外部副作用和实际 `changes[]`。
6. Task Director 在完成态显示“服务端变化回执”，用同一差异语言连接用户决定与最终材料；只有返回的 `impact_receipt` 才能触发该回执。
7. 旧 Snapshot 的 `resolution_options=[]`、旧 ControlEvent 的 `impact_receipt=null` 保持兼容；此时沿用保守说明，不伪造结构化影响。

不采用纯前端预测动画：它不能证明服务端状态变化。也不把模型思维过程、内部工具调用或 Worker 对话展示为影响：这些信息既不等于业务结果，也会增加认知负担。当前 V0.1 不建设任意控制命令的通用影响推演器，只覆盖固定 Demo 1 的收入口径决定。

## 4. 前台输出与恢复

| 时点 | 用户看见什么 | 用户动作与反馈 | 失败或等待 | 默认隐藏 |
| --- | --- | --- | --- | --- |
| 提交前 | “影响预演”逐项显示经营分析、客户回复草稿、风险页和外部发送的前后变化 | 提交服务端批准的唯一选项 | 选项缺失或不可执行时主动作禁用；旧 Snapshot 只显示保守说明 | 原始 `fixture:`、option 内部来源、模型过程、事件 ID |
| 提交中 | 保持当前 Snapshot，控制禁用并显示同步状态 | 不重复提交新业务含义 | 结果未知时沿用既有幂等键与 GET 对账 | 网络栈、重试日志 |
| 提交后 | “服务端变化回执”显示实际改变、实际重新核对、保持不变、未发生外部发送和任务版本 | 查看成果或进入后续受治理动作 | 409 刷新后复核；无 receipt 时不显示成功回执 | Commit hash、完整 Artifact ID、Verification 内部日志 |

“提交完成”与“外部动作执行”严格分离。本轮 receipt 即使形成 TaskCommit，也必须显示客户回复仍为草稿且未发送。后续“准备发送”继续进入 Demo 3 的 Risk/Evidence/Approval/Permit/Gateway 链路。

## 5. 后端事实与协议

权威链路为：

```text
ConflictRecord.resolution_options[].expected_impact
  → TaskControlCommand.resolution_option_id + selected_source_ref
  → TaskService 校验 option/source/version/idempotency
  → 原子写 Snapshot + ControlEvent.impact_receipt + TaskEvent
  → 浏览器应用新 Snapshot
  → TaskImpactReceiptView
```

`expected_impact` 是当前服务端选项的预期业务影响，不是完成事实；`impact_receipt` 是 mutation 已应用后的实际事实。两者必须分别建模，前端不得把 preview 复制成 receipt。实际 receipt 只记录本次控制产生的新 ArtifactVersion 与 VerificationReport；仍有其他冲突时 `commit_created=false`、验证为 `partial`，任务保持 `waiting_input`。

幂等语义沿用 Task Control：相同 key 和相同命令返回首次 Snapshot，不重复生成 receipt、工件、验证或 Commit；版本冲突返回 409。receipt 持久化在 Snapshot 的 ControlEvent 中，因此刷新后仍可恢复。普通业务 UI 只显示业务标签和版本差异，不暴露内部 ID。

## 6. 验证与边界

工程封口已覆盖：严格 Schema 与旧 Snapshot 兼容、非法 option/source 拒绝、最终与部分完成 receipt、幂等零重复、浏览器请求携带 option ID、提交前 preview、提交后 receipt、桌面/移动布局、全量回归和截图 hash。实现为 `258861f`，PR 为 [#16](https://github.com/Dickey007s/lenovo_agent/pull/16)，证据位置为 [`DEMO1-AGENT-IMPACT-PREVIEW-EVIDENCE-20260820`](../evidence/DEMO1-AGENT-IMPACT-PREVIEW-EVIDENCE-20260820.md)。

本决策即使工程验证通过，也只能证明固定 Fixture 的协议与被测交互。它不证明真实用户理解更快、决策更好，也不证明通用 Agent 动作都可预测。至少 5 名目标用户的无引导测试、非确定性工具结果、多个可执行选项、部分失败和真实 Connector 仍需后续研究。

Demo 2 已在 [`DR-0011`](DR-0011-demo2-route-impact.md) 中复用同一双时态原则，但绑定的是 `RouteProfile.impact_preview → RouteSelectionReceipt`：选择前说明工作如何组织，选择后只证明服务端已记录路由，仍不等于 Worker 或外部动作已经启动。对应工程证据见 [`DEMO2-ROUTE-IMPACT-EVIDENCE-20260820`](../evidence/DEMO2-ROUTE-IMPACT-EVIDENCE-20260820.md)。
