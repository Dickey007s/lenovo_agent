# Demo 2 PR-1：可解释 Admission 与本次路由选择工程证据

| 字段 | 内容 |
| --- | --- |
| Evidence ID | `DEMO2-PR1-EXPLAINABLE-ADMISSION-EVIDENCE-20260817` |
| Decision | [`DR-0008`](../decisions/DR-0008-demo2-explainable-admission.md) |
| Scenario | [`SCENARIO-002`](../scenarios/SCENARIO-002-demo2-explainable-admission.md) |
| Status | `Verified`（限定范围） |
| Scope | 四项固定演示工作、服务端固定队列与路由解释、客户 A 仅本次路由选择、Admission 预览和未启动执行边界 |
| 当前结论 | 单进程 memory 纵切已实现，并通过聚焦后端、完整 Python、完整浏览器、静态检查、生产构建和视觉走查；不外推为真实 Swarm 或用户价值 |

## 1. 被验证的用户流程

1. 用户进入 Tasks 后首先看到“今天的工作，应该怎么处理”，而不是 Worker 监控台。
2. 服务端返回四项固定演示工作。供应商邮件、周报格式统一、报销异常核查只显示固定轻量路由；客户 A 显示需要决定。
3. 用户查看客户 A 的业务价值、资料广度、可并行工作包、截止压力、风险与资源边界，并比较三种允许方式。
4. 用户确认推荐或选择其他允许方式。请求固定为 `scope=this_run`，带 `expected_version` 与 `idempotency_key`。
5. 成功后页面只显示“执行方式已记录，任务尚未启动”。409 时保留本地选择，GET 最新 Snapshot 后要求复核。

## 2. 后端与前台事实

| 可见事实 | 权威来源 | 被测边界 |
| --- | --- | --- |
| 四项工作与固定顺序 | `GET /v1/demo2/cockpit` 的 `WorkCockpitSnapshot.items[]` | 每个 Owner 独立生成固定 Fixture；不是 Connector 聚合或动态排序 |
| 三项轻量路由 | `allowed_modes` 单值、`selected_mode`、`selection_source=admission` | radio 禁用且没有确认按钮；不表示已经调度 |
| 客户 A 推荐与理由 | `recommendation.mode/reasons/policy_version`、`route_profiles` | 前端不计算 Admission 分数，不展示思维链或策略权重 |
| 本次选择 | `POST /v1/demo2/work-items/{id}/route` 返回的 `RouteSelectionResult` | 服务端同时返回驾驶舱聚合版本与新 WorkItem；推荐为 `admission`，其他允许模式为 `user_override + this_run` |
| 未启动边界 | `execution_status=not_started` | 没有 Worker、共享工件、Verifier、外部动作或完成状态 |
| 规则预测 | `forecast.source_type=fixture_policy_forecast` 与三项数值 | UI 标“规则预测”；不支持实际成本、时延或 SLA 结论 |
| 读取与恢复 | GET、mutation 响应、409 后 GET | 当前没有 Demo 2 SSE；API 重启会丢 memory 选择 |

## 3. 自动化结果

| 命令 | 结果 | 证明范围 |
| --- | --- | --- |
| `uv run pytest -q tests/unit/test_demo2_models.py tests/integration/test_demo2_cockpit.py` | `6 passed (1.29s)` | 严格 Schema、四项建议、Owner 隔离、版本、幂等、选择来源、固定路由拒绝、未知字段拒绝和未启动边界 |
| `uv run ruff check ...Demo2 files...` | `All checks passed` | 新 Python 路径静态检查 |
| `pnpm --dir apps/web lint` | `tsc --noEmit` 通过 | TypeScript 类型与组件编译 |
| `pnpm --dir apps/web exec playwright test e2e/demo2-work-cockpit.spec.ts --project=system-browser` | `5 passed (13.0s)` | 真实 API 队列、固定路由只读、覆盖选择 body、409 草稿保留、内部 ID 隐藏、390px overflow/44px |
| `uv run pytest -q` | `118 passed, 1 skipped (2.79s)` | 完整 Python 回归；skip 是需显式外部环境的 opt-in 路径 |
| `uv run ruff check .` | `All checks passed` | 完整 Python 静态检查 |
| `pnpm --dir apps/web lint` / `pnpm --dir apps/web build` | 均通过 | TypeScript 与 Next.js 生产构建 |
| `pnpm --dir apps/web test:e2e` | `34 passed (1.2m)` | Demo 1、报价、Action Gate、Demo 2 与恢复路径的完整 system Edge 回归 |
| `git diff --check` | 通过，仅换行提示 | 补丁无空白错误 |

自动化只能证明指定协议、DOM、请求与被测恢复语义一致，不能证明目标用户已经理解或任何执行方式优于其他方式。

## 4. 视觉证据

| 文件 | 尺寸 | SHA-256 | 说明 |
| --- | --- | --- | --- |
| [`demo2-work-cockpit-admission-1440.png`](screenshots/demo2-work-cockpit-admission-1440.png) | `1440 x 900` | `E9785FF1C55CAB8AC6FFA661E1A30AC1D000FD2D260B00275B507D6F81B66F18` | 初始四项队列、客户 A 工作条件、路线比较与右侧推荐 |
| [`demo2-work-cockpit-route-selected-1440.png`](screenshots/demo2-work-cockpit-route-selected-1440.png) | `1440 x 900` | `305CA07B58D73A0E0F0CA1594A937CB1405750DE61B08767DC766DBAD16D015D` | 选择固定流程后的服务端记录状态，仍明确未启动 |
| [`demo2-work-cockpit-mobile-390.png`](screenshots/demo2-work-cockpit-mobile-390.png) | `390 x 2309` full-page | `35048F1E05419C2EAD037BCBF06ADA13A8F63ECD99F92799C3819C729DA20C4D` | 390px 纵向布局、横向工作队列、详情与决策区 |

视觉走查确认：桌面保持左工作区、右 Agent 决策区和中间可拖动结构；移动端页面本身不横向溢出，关键可见操作目标至少 44px。截图是固定演示运行证据，不是可用性研究。

## 5. 来源与留痕

- Stakeholder 推进要求：[`USER-FEEDBACK-20260817-01`](../sources/USER-FEEDBACK-20260817-01-demo2-continued-iteration.md)。
- 0716-v2 阶段原件与边界：[`final-reference/README.md`](../final-reference/README.md)。
- Demo 2 内部产品输入：[`未来办公Agent_一小时汇报讲稿_v5.md`](../final-reference/未来办公Agent_%E4%B8%80%E5%B0%8F%E6%97%B6%E6%B1%87%E6%8A%A5%E8%AE%B2%E7%A8%BF_v5.md) P18-P22。
- 当前实现位置：`packages/contracts/demo2_models.py`、`services/api/app/application/demo2_cockpit.py`、`apps/web/app/work-cockpit.tsx`、`apps/web/app/page.tsx`。

## 6. 当前边界

本证据不支持以下结论：Adaptive Swarm 已实现或启动；Worker 已被动态创建；四项工作来自真实邮箱、CRM、OA、日历；已实现动态排序或拖拽调序；成本降低、时延提升或质量提升；Demo 2 状态跨 API 进程恢复；目标用户已经理解驾驶舱。

当前服务端为 memory，无 Demo 2 SSE、PostgreSQL Store、多实例通知、Shared Artifact Workspace、Verifier/Resolver 或执行循环。`max_workers` 只是规则预测上限，不是已运行 Worker 计数。所有来源标签和业务数值均为固定演示数据。

## 7. 交付封口

- 实现提交：`82df6b8`
- PR：`待回填`
- 完整回归：Python `118 passed, 1 skipped (2.79s)`；浏览器 `34 passed (1.2m)`；Ruff、lint、build、diff-check 通过
- 用户研究：未运行；至少 5 人无引导形成性测试留待后续
