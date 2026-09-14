# DR-0060：显式新建任务入口与独立草稿

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`；前台纵切和受控浏览器门通过 |
| 日期 | 2026-09-03 |
| 用户来源 | [`USER-FEEDBACK-20260903-NEW-TASK-CONVERSATION-ENTRY`](../sources/USER-FEEDBACK-20260903-new-task-conversation-entry.md) |
| 前置决策 | `DR-0054`、`DR-0056`、`DR-0057`、`DR-0058` |
| 场景 | [`SCENARIO-047`](../scenarios/SCENARIO-047-start-an-independent-task-conversation.md) |
| 测试合同 | [`NEW-TASK-CONVERSATION-GATES-20260903`](../testing/NEW-TASK-CONVERSATION-GATES-20260903.md) |
| Evidence | [`DR-0060-NEW-TASK-CONVERSATION-EVIDENCE-20260903`](../evidence/DR-0060-NEW-TASK-CONVERSATION-EVIDENCE-20260903.md) |

## 1. 问题

系统已经能通过新 instruction 创建独立 Task，也能把最近 Run 按 `task_id` 分成任务会话，
但 Workspace 和 Agent 能力页没有明确的“新建任务”动作。用户只能在终态表单中改写文字，
难以判断这是继续当前 Task、覆盖旧记录，还是创建独立会话。

## 2. 决策

Workspace 顶部和 `/agent-capabilities` 工具栏都提供“新建任务”。点击后只进入客户端草稿：

1. 关闭当前 EventSource，并使旧 Run 的迟到响应失效；
2. 清除当前选中的 Run、Task pointer、审查页和任务文字；
3. 保留资料库浏览状态、预算设置、服务端 Task/Run 和最近任务会话；
4. 明确提示上一任务不会停止或删除，可从历史返回；
5. 聚焦空白任务输入框，不发 POST、不调用模型、不消费预算；
6. 用户启动后才调用既有 `POST /v1/harness/runs`，由服务端创建独立 Task/Run。

浏览器用一个 session-scoped 草稿标记避免刷新后自动重新打开旧 Run。该标记不是 Task
身份或服务端事实；打开历史 Run 或收到合法新 Run Snapshot 时立即清除。草稿文字本身不做
持久化。

## 3. 幂等与连续性

- 未知启动响应仍按原合同复用同一 command key；
- 明确点击“新建任务”会清除上一条已知启动 command，随后即使文字完全相同也生成新 key；
- 点击按钮不向旧 Run 发送 `stop/pause`，所以旧 Run 不会因切换界面被改变；
- 新 Task 成功后进入任务会话列表；选择旧记录仍通过 Task GET 判定 current/history。

## 4. 前台与权威

| 前台状态 | 权威 | 边界 |
| --- | --- | --- |
| 新任务草稿 | 浏览器状态和 session 标记 | 不是空 Task、Run 或后端保存 |
| 上一任务保留 | 没有控制 POST；服务端原 Task/Run 不变 | 不承诺旧 Run 已完成，只是不因本动作停止 |
| 新任务已创建 | 成功的 POST Run Snapshot，含新 `task_id/run_id` | 与相同文字、最近列表顺序无关 |
| 返回旧任务 | recent Runs + Task current pointer | 最近 20 个 Run 不是无限 Task list |

## 5. 当前边界

- 没有新增公开 API、空 Task 记录、草稿云同步或任务重命名；
- 只保存“正在新建”的浏览器会话标记，不保存未提交文字；
- 自动化和截图证明受控事实映射，不证明目标用户体验收益；
- 当前 `X-User-Id` 仍是未签名演示 Owner。

## 6. 验证结论

Workspace 与 Agent 能力页入口、无副作用草稿、输入聚焦、刷新保持、历史保留、独立 Task
提交、相同文字使用新幂等键以及桌面/390 px 布局均通过定向门；全量浏览器、lint、build 和
变更检查结果见 DR-0060 Evidence。
