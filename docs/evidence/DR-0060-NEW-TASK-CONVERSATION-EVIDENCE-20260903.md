# DR-0060 新建任务会话工程 Evidence（2026-09-03）

## 结论

状态：`Limited Verified`。Workspace 与 Agent 能力页已提供显式“新建任务”入口；点击只进入
客户端草稿，不创建空 Task、不调用模型、不停止或删除上一任务。用户提交后仍由现有 Run
start 协议创建独立 Task。

## 1. 源码事实

- `beginNewTask` 关闭 EventSource、递增页面 generation、清除当前 Run/Task/审查状态和旧启动键；
- `NEW_TASK_DRAFT_SESSION_KEY` 只保存草稿模式，刷新时仍加载最近历史但不自动选择旧 Run；
- `applySnapshot` 与历史选择会清除草稿标记；
- Workspace 和 `/agent-capabilities` 共用同一动作，并在新建后聚焦任务输入；
- 已知成功的 start command 被释放，因此后续相同文字不会复用旧幂等键。

## 2. 浏览器验证

受控 Fixture 覆盖：

- 当前非终态 Run -> 新建任务 -> 空白可编辑输入；
- 点击前后 `POST /runs` 数量保持 0，旧两项任务会话仍可查看；
- 启动后新增独立 Task，会话数从 2 变为 3；
- 再次以相同文字启动，两个 `idempotency_key` 不同；
- Agent 能力页可新建，刷新后保持草稿且不显示旧 Task；
- 当前 Run 切回历史再切回 current 时仍从 `after=4` 恢复 SSE。

截图：

- [`dr-0060-new-task-desktop.png`](screenshots/dr-0060-new-task-desktop.png)
- [`dr-0060-new-task-capabilities-390.png`](screenshots/dr-0060-new-task-capabilities-390.png)

人工查看确认桌面入口、草稿说明、390 px 双按钮和任务输入无重叠或逐字断行。

## 3. 自动化

- 定向 Playwright：`3 passed`，覆盖两条新任务用例与 current SSE 回归；
- 全量 Playwright：`84 passed in 3.0m`；第一次全量复跑为 `83 passed, 1 failed`，失败来自
  SessionHistory Fixture 把 Run 2 的 `task_version` 回落为 1；修正 Fixture 权威版本后，失败
  用例定向通过并完成上述全量绿灯；
- Web lint：`tsc --noEmit` 通过；
- Web build：成功生成 `/`、`/_not-found`、`/agent-capabilities` 和 `/icon.png`；
- reporting governance：`4 passed`；
- `git diff --check`：通过，仅有既有 Windows 行尾提示。

## 4. 限制

- 浏览器只保存草稿模式，不保存未提交文字；
- 最近会话仍只覆盖 Owner 最近 20 个 Run，不是 Task list；
- 离开 SSE 不会停止旧 Run，也不保证旧 Run 已完成；
- 没有运行真实 Provider、PostgreSQL、目标用户研究或多实例测试；
- 本轮没有新增或修改公开 API。
