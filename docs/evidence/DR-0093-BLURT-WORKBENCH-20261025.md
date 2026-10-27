# DR-0093 验证记录

日期：2026-10-25。未提交工作树，原有修改保留。[Decision](../decisions/DR-0093-blurt-focused-workbench.md)、[Scenario](../scenarios/SCENARIO-080-focused-evidence-and-agent-lanes.md)、[Source](../sources/USER-FEEDBACK-20261025-blurt-workbench.md)。

## 清单落点

| 项 | 本轮处理 | 边界 |
| --- | --- | --- |
| I-001/002 | 删除整库小字、三个常驻案例、重复确认块 | 其他分工示例折叠，原模型输入不变 |
| I-003 | 显示读取、分析、引用核对三阶段；实际计划按需展开 | 没有新增细粒度 Planner 协议 |
| I-004/006 | 普通发现不套人工处置单；统一入口直接开原文；文件预览聚焦滚动 | 真正待决、歧义、恢复控件保留 |
| I-005 | 主区去调用/轮数分母，预算设置仍可达 | 实际预算没有取消 |
| I-007/008 | 可选扩展与原任务欠项分开；明确缺少独立理由和直接引用 | 未实现新建议理由字段，不编造历史理由 |
| I-009 | 零人工项不显示空栏 | 待决、缺源、否决与未完成项不隐藏 |
| I-010 | 任务分支吸顶，两项手机并排；协作安排去堆叠统计 | Task 与 Run 身份不变 |
| I-011 | 一行一个 Agent，身份、状态、依赖、结果；窗口与主区复用 | 计划岗位不等于已派发，无台账不造 Worker |
| I-012 | 服务端公开投影与前端展示都使用续办业务目标 | 私有上下文仍供模型使用；旧进程尚未加载后端新代码 |

## 自动验证

- `pnpm --dir apps/web lint`：通过。
- `uv run pytest tests/acceptance/test_task_followups.py tests/acceptance/test_automatic_readonly.py tests/acceptance/test_adaptive_progress.py -q`：23 passed。覆盖同任务续办、私有背景继续提供模型而公开 question 不外露、幂等与错误 parent、自动只读与调整门。
- Playwright 56 项针对性回归通过：39 项浏览器用例，17 项分工/依赖/待办投影测试。覆盖桌面与 390px、普通依据、未预选的候选、同任务丢回执重试、历史只读、吸顶切换、内部目标兼容投影、已返回未采用、旧 attempt 不冒充本次采用，以及业务否决可见。
- 最后增加普通文件入口聚焦和进入视口断言，单独重跑对应原文用例：1 passed。这是上述 56 项中的同一用例，不累计为 57 个独立用例。

```powershell
pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts e2e/task-responsibility.spec.ts e2e/worker-stages.spec.ts e2e/todo-summary.spec.ts --grep 'unified reference workbench|result-first reading|copilot integration|same-task continuation only|source candidate|polish keeps evidence|^.*task-responsibility.spec|^.*worker-stages.spec|^.*todo-summary.spec'
```

曾尝试完整的 198 项组，在 49 项后因旧入口相关失败停止：44 通过、5 失败，余项未运行。失败集中于 `simple user walkthrough` 的两种尺寸及 `focused workbench preserves context` 的三种尺寸，仍查询旧“办公资料库”标题和旧入口/容器。需要另行迁移核对，不能将本次写成全量回归通过，也未做旧版本对照来证明这些全部是既存失败。最初针对性回归的两项失败为本轮移除确认块后旧断言和带待决 fixture 的错误空栏预期，已纠正并复测。

## 浏览与截图

原生浏览器连接没有可用 IAB，改用项目已有 Playwright/Edge 执行界面检查。

`node scripts/inspect-blurt-feedback.cjs http://localhost:3010/`：对现有真实历史任务只读浏览 4 项，打开安全原文、查看任务与桌面/手机视口。0 POST，0 pageerror，未新增模型调用。结果见 `outputs/blurt-feedback-20261025/live-3010/checks.json`；截图 `source-0.png` 对照 Word 招聘原文，`task-0.png` 展示既有五个 Worker 的实际回执。它们是旧运行的新界面回看，不是本轮重新执行五 Agent。

`http://localhost:3000/` 主入口也做了页面加载及两种视口检查，连接 8000；该次检查未访问已有任务，不能冒充完整业务走查。3010 连接 8010，有现存真实协作历史。两处服务都继续运行，未清空或重启内存服务。

受控状态截图位于 `outputs/blurt-feedback-20261025/`：`new-task.png`、`evidence-desktop.png`、`evidence-mobile.png`、`branches-390.png`、`team-dialog.png`。这些是路由 fixture，不是新模型实验。

## 未验证

本轮不调用付费模型，不重做真实自动扩编试验，不改变预算/权限/批准流程。没有用户理解度实测，也没有完整部署验收。API 公开投影修复经隔离测试；现有内存 API 进程未重启，需先保留任务再加载新后端。前端兼容展示已避免旧进程的内部目标出现在页面上。
