# DR-0004：终态保留旧记录并开始独立新一轮汇报

| 字段 | 内容 |
| --- | --- |
| Decision ID | `DR-0004` |
| Owner | Office Agent 项目组 |
| Date | 2026-08-10 |
| Status | `Verified`（独立 Task 与创建幂等语义）；当前入口文案和自动启动属于 `DR-0005` 的 `Draft` 交互修订 |
| Scope | Demo 1 创建幂等语义、终态新一轮入口、旧轮次保留和刷新恢复 |

## 1. 用户场景与问题

演示者完成一次客户 A Demo 1 后刷新页面，希望从右上角再次开始完整演示。原实现的 `TaskService.create_demo1` 把幂等键固定为 `demo1-customer-a:{owner}`，因此同一用户再次调用只会返回第一次创建、现已 committed 的 Task；前端终态 Task Bar 也没有新建入口。

原完成条件是：终态 Task 刷新后仍可见；用户通过终态入口得到新的服务端 Task ID 和 `ready / contract` Snapshot；旧 Task、工件、事件和 Commit 保留；同一次创建请求重试不产生重复 Task。Action Gate 打开或创建进行中时入口不可用。

2026-08-11 后续反馈表明“再次演示”会被理解为重置当前状态或把旧 Task 设置回可启动状态。当前交互语义因此改为：终态入口显示“开始新一轮汇报”，前端先创建独立 Task，再立即启动该新 Task；旧终态 Task 不被回滚、删除或覆盖。固定路径启动后通常直接进入 `waiting_input / verify`，不是把当前状态设置成“可以启动 Demo”。多轮 Task 虽由服务端保留，前端历史轮次选择入口仍未实现。

## 2. 来源与依据

| Source ID | 类型 | 精确引用 | 日期或版本 | 支持判断 | 局限 |
| --- | --- | --- | --- | --- | --- |
| `USER-ISSUE-20260810-DEMO1-REPEAT` | 用户反馈 | 当前任务：“右上角的demo1演示启动一次之后刷新无法演示第二次，解决” | 2026-08-10 | 证明重复演示是明确问题 | 不指定协议实现 |
| `SOURCE-TASKSERVICE-FIXED-DEMO1-KEY` | 源码事实 | 修复前 `services/api/app/application/tasks.py:create_demo1` 固定使用 `demo1-customer-a:{owner_id}` | 读取于 2026-08-10 | 解释同 Owner 永远返回旧 Task 的根因 | 只描述修复前行为 |
| `E2E-DEMO1-REPEAT-20260810` | 浏览器运行证据 | `apps/web/e2e/demo1-runtime.spec.ts` 主路径末尾的 committed → reload → 再次演示断言 | 2026-08-10 | 证明真实 FastAPI/Next.js/Edge 路径创建第二个不同 Task ID | 内存 TaskStore；不证明 PostgreSQL 重启 |
| `USER-FEEDBACK-20260811-ROUND-AND-SOURCE-03` | Stakeholder feedback | [`USER-FEEDBACK-20260811-05-source-labels-and-new-round.md`](../sources/USER-FEEDBACK-20260811-05-source-labels-and-new-round.md) | 2026-08-11 | 证明“再次演示”的重置/新建语义不清，支持改为“开始新一轮汇报”并解释独立 Task | 不证明新文案已被目标用户理解，也不证明历史轮次选择能力 |
| `TASK-DIRECTOR-ROUND-AND-SOURCE-CLARITY-20260811` | 源码、浏览器自动化与截图证据 | [`DEMO1-ROUND-AND-SOURCE-CLARITY-EVIDENCE-20260811.md`](../evidence/DEMO1-ROUND-AND-SOURCE-CLARITY-EVIDENCE-20260811.md)，完整浏览器 E2E `12 passed (44.5s)` | 2026-08-11 | 证明当前 Web 一键 create+start 独立新 Task，列表保留旧 committed Task | 不证明用户理解或历史轮次选择；内存 E2E 不等于数据库故障恢复 |

## 3. 决策与备选

`POST /v1/demo1/tasks` 接受可选 `Idempotency-Key` 作为演示轮次。前端每次用户显式开始新一轮时生成新 key；请求失败后当前页面复用该 key，成功后清除。相同 Owner+key 返回已存在 Task 当前已持久化的 Snapshot，不新增 `TASK_CREATED`、不回退已发生的 mutation；不同 key 创建独立 Task。未传 header 时保留原 Owner 默认 key，兼容旧客户端和既有调用。

当前 Web 的“开始新一轮汇报”是组合动作，不是新的服务端路由：create 成功并应用新 Snapshot 后，前端再向新 Task 提交 `start`。create 与 start 各自使用自己的幂等语义；任一步结果未知时继续既有对账流程，不能把旧 Task 当作回退目标。未采用 reset/reopen 旧 Task，因为它会破坏终态、Artifact lineage、Commit 和审计语义。

未采用删除或重置旧 Task，因为这会破坏审计、Artifact lineage、Commit 和恢复事实。未采用前端伪造空白 Task，因为 Task ID、契约、分支和状态必须由服务端产生。

## 4. 后端事实与前台输出

- 权威事实仍是新 `TaskSnapshot.task_id/status=ready/phase=contract/version=1` 和新的 `TASK_CREATED(sequence=1)`。
- 旧终态 Snapshot 不修改、不删除；`GET /tasks` 同时返回两轮 Task。
- 前端刷新优先恢复未终止 Task；只有当前展示终态 Task 时出现“开始新一轮汇报”。
- 点击后显示“正在准备”，收到新 Task 的 create Snapshot 后继续 start；只有服务端返回的新 Snapshot 才能改变界面。固定客户 A 路径启动后通常进入冲突待确认，不再停留在单独的“启动任务”步骤。
- Action Gate 打开时按钮禁用；接口不可用时保留旧终态事实，不提前显示新任务成功。
- 实际 `Idempotency-Key` 不在普通 UI 中展示。
- `GET /tasks` 继续保留并返回旧轮次，但当前界面没有历史轮次选择器；不能声称用户可从前台自由切换所有旧轮次。

## 5. 验证与边界

聚焦路由基线回归 `6 passed`，覆盖同 key 重放得到同 Task、不同 key 得到不同 Task、列表同时保留两轮。system Edge E2E `2 passed (17.5s)`，主用例新增完成一轮、刷新、点击“再次演示”、出现可用“启动任务”、列表包含不同新 Task ID 和旧 committed Task 的断言。全量回归为 Python `57 passed`、Ruff、前端 TypeScript lint 和 Next.js 生产构建通过。重启本地 `8010/3000` 后又用独立 smoke Owner 验证：同 key 返回同 Task、换 key 返回不同 `ready / contract` Task、列表数量为 2，前端 HTTP 200。PR 5 合并兼容回归还中断了首次“再次演示”创建请求，验证旧 Task 仍显示已连接，重试复用同 key 且只创建一个新 Task；合并后聚焦路由回归为 `7 passed`，新增断言跨路由复用同 key 但契约不同时返回 409。

该结论自身只验证固定 Fixture 与内存 TaskStore 浏览器路径。后续 PR 5 另行验证了同一 PostgreSQL 16.14 数据库、三个顺序 API 进程的 v2/v3 恢复；数据库故障或重启、多实例通知和演示轮次列表选择仍未验证。历史测试中的“再次演示”是当时 UI 文案，不是当前产品术语；历史 evidence 没有反写。当前“开始新一轮汇报”组合动作另由 `TASK-DIRECTOR-ROUND-AND-SOURCE-CLARITY-20260811` 的 `12 passed (44.5s)` 记录。新一轮不会复制真实企业数据或触发真实 Connector，自动化通过也不证明用户已经理解新文案。
