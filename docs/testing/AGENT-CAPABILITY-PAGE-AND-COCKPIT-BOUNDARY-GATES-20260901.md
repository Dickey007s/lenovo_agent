# Agent 能力页与驾驶舱边界验收门

- 日期：2026-09-01
- 状态：`Limited Verified`；工程门已执行，未来驾驶舱不在本轮验收范围
- 决策：`DR-0057`
- 场景：`SCENARIO-044`

## 一、用户可直接试的用例

### TC-CAP-01：独立页面往返与刷新

从 Workspace 点击“Agent 能力”，确认 URL 进入 `/agent-capabilities`。刷新页面后仍从公开
API 恢复 Run；点击返回后回到 Workspace。页面不是 modal，也不是静态介绍页。

### TC-CAP-02：两种能力在同一 Run 下并列

打开一条 Adaptive Run。预期同页可见 Agent Control Loop 和 Adaptive Swarm 两个一级
区域；Task/Run 身份一致，来源、工作包、回执和版本都来自同一 Snapshot。

### TC-CAP-03：历史 Run 整页只读

在任务会话中打开同 Task 的旧 Run。预期 Loop 控制、Branch continue 和 Worker confirmation
均不可操作；历史 Run 不连接 SSE。切回 current 后从其最新 sequence 连接。

### TC-CAP-04：Adaptive 正例

使用 SCENARIO-044 输入 B 或固定公共 Fixture。预期显示 10 份来源、3 root + 2 dependent、
确认前零 Worker、实际回执、Contribution 状态和逻辑 v1/v2，并显示当前有限实现边界。

### TC-CAP-05：Fixed Workflow 反例

使用三期同结构财务核对或 fixed Fixture。预期高亮 Fixed Workflow，显示“本次未启动
Adaptive Swarm”，Worker/Contribution 为空。

### TC-CAP-06：没有伪驾驶舱

搜索 DOM、可访问名称和公开请求。预期不存在硬编码“客户 A 经营汇报”队列、假优先级、
假 Tool Call/Single Agent 执行或可点击但无合同的智能驾驶舱入口。

### TC-CAP-07：桌面与 390 px

两个能力区域在桌面可扫描，在 390 px 变为稳定单列；事实和回执字号不低于 13 px，辅助
说明不低于 12 px；无页面横向溢出、遮挡或不可达导航。

## 二、自动化门

- 直接打开 `/agent-capabilities`、刷新和返回 Workspace。
- recent Runs 按 `task_id` 分组；相同 instruction 的不同 Task 不合并。
- selected Run 切换同时更新 Loop 与协同区域，不混用两个 Snapshot。
- history/current 由 Task pointer 决定；历史无 EventSource 和控制。
- Adaptive 5 个业务 WorkUnit、10 份来源、Worker/Contribution/v1/v2 来自 Fixture Snapshot。
- Fixed Workflow 和无 admission 不生成假 Worker。
- DOM 不暴露 owner、raw unit/branch ID、digest、绝对路径、Prompt、CoT 或 raw response。
- 根 Workspace 的资料库、15/96、安全预览、任务输入、成果和审查回归通过。

## 三、工程门

```powershell
uv run pytest -q
uv run ruff check .
pnpm --dir apps/web lint
pnpm --dir apps/web build
pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts
git diff --check
```

真实 PostgreSQL、真实 Provider 和形成性用户走查必须单列；没有运行就不能由 Fixture 或
已有历史 Evidence 替代。

2026-09-01 执行结果：能力页定向 Playwright `4 passed`，截图钩子 `1 passed`，全量
Playwright `77 passed`，全量 Python `418 passed, 23 skipped`，Ruff、Web lint/build、
汇报治理与 `git diff --check` 通过。详见
[`DR-0057 Evidence`](../evidence/DR-0057-AGENT-CAPABILITY-PAGE-EVIDENCE-20260901.md)。

## 四、尚不验收的未来驾驶舱

任务队列、优先级、跨 Task dispatch、四路线真实执行、完成后回队列与 Demo 3 风险转交
均不属于本轮工程门。后续实现智能工作驾驶舱时必须另建 API/Scenario/Evidence，不能把
本页通过当成驾驶舱通过。
