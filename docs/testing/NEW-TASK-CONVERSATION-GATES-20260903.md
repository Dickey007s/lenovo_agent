# 新建任务会话验收门

- 日期：2026-09-03
- 状态：`Limited Verified`
- 决策：`DR-0060`
- 场景：`SCENARIO-047`

## 一、行为门

- 当前 Run 存在时，“新建任务”在 Workspace 和 Agent 能力页均可见。
- 点击后任务输入为空、可编辑并获得焦点；当前 Run、Task pointer、审查页和 SSE 被移出当前视图。
- 点击本身没有 `POST /runs` 或控制请求，旧任务仍在最近会话中。
- session 草稿标记阻止刷新自动恢复旧 Run；打开历史或成功启动后清除。
- 提交后只调用既有 `POST /v1/harness/runs`，新 Task 作为第三个独立会话出现。
- 再次新建并提交相同文字时，启动幂等键不同。

## 二、视觉与可访问性门

- 按钮使用加号图标和“新建任务”文字，不依赖陌生图标猜测。
- 草稿提示明确“上一任务不会停止或删除”和“启动后才创建”。
- 1440 px 与 390 px 不出现按钮文字逐字断行、横向溢出或控件遮挡。
- 新建后焦点进入任务输入；按钮和输入保持可访问名称。

## 三、工程门

```powershell
pnpm --dir apps/web lint
pnpm --dir apps/web build
pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts --grep "clean draft|survives refresh"
pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts
git diff --check
```

本轮不修改服务端协议，因此不以浏览器 Fixture 冒充 Provider、PostgreSQL、模型质量或用户研究。

执行结果：定向 Playwright `3 passed`，全量 Playwright `84 passed`，reporting governance
`4 passed`，Web lint/build 与 `git diff --check` 通过。完整边界见 DR-0060 Evidence。
