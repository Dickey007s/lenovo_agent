# DR-0004：终态 Demo 1 可刷新并开始新一轮演示

| 字段 | 内容 |
| --- | --- |
| Decision ID | `DR-0004` |
| Owner | Office Agent 项目组 |
| Date | 2026-08-10 |
| Status | `Verified` |
| Scope | Demo 1 创建幂等语义、终态 Active Task Bar 入口、刷新后的重复演示 |

## 1. 用户场景与问题

演示者完成一次客户 A Demo 1 后刷新页面，希望从右上角再次开始完整演示。原实现的 `TaskService.create_demo1` 把幂等键固定为 `demo1-customer-a:{owner}`，因此同一用户再次调用只会返回第一次创建、现已 committed 的 Task；前端终态 Task Bar 也没有新建入口。

完成条件：终态 Task 刷新后仍可见；用户点击“再次演示”得到新的服务端 Task ID 和 `ready / contract` Snapshot；旧 Task、工件、事件和 Commit 保留；同一次创建请求重试不产生重复 Task。Action Gate 打开或创建进行中时入口不可用。

## 2. 来源与依据

| Source ID | 类型 | 精确引用 | 日期或版本 | 支持判断 | 局限 |
| --- | --- | --- | --- | --- | --- |
| `USER-ISSUE-20260810-DEMO1-REPEAT` | 用户反馈 | 当前任务：“右上角的demo1演示启动一次之后刷新无法演示第二次，解决” | 2026-08-10 | 证明重复演示是明确问题 | 不指定协议实现 |
| `SOURCE-TASKSERVICE-FIXED-DEMO1-KEY` | 源码事实 | 修复前 `services/api/app/application/tasks.py:create_demo1` 固定使用 `demo1-customer-a:{owner_id}` | 读取于 2026-08-10 | 解释同 Owner 永远返回旧 Task 的根因 | 只描述修复前行为 |
| `E2E-DEMO1-REPEAT-20260810` | 浏览器运行证据 | `apps/web/e2e/demo1-runtime.spec.ts` 主路径末尾的 committed → reload → 再次演示断言 | 2026-08-10 | 证明真实 FastAPI/Next.js/Edge 路径创建第二个不同 Task ID | 内存 TaskStore；不证明 PostgreSQL 重启 |

## 3. 决策与备选

`POST /v1/demo1/tasks` 接受可选 `Idempotency-Key` 作为演示轮次。前端每次用户显式开始新一轮时生成新 key；请求失败后当前页面复用该 key，成功后清除。相同 Owner+key 仍返回第一次创建的 Snapshot，不同 key 创建独立 Task。未传 header 时保留原 Owner 默认 key，兼容旧客户端和既有调用。

未采用删除或重置旧 Task，因为这会破坏审计、Artifact lineage、Commit 和恢复事实。未采用前端伪造空白 Task，因为 Task ID、契约、分支和状态必须由服务端产生。

## 4. 后端事实与前台输出

- 权威事实仍是新 `TaskSnapshot.task_id/status=ready/phase=contract/version=1` 和新的 `TASK_CREATED(sequence=1)`。
- 旧终态 Snapshot 不修改、不删除；`GET /tasks` 同时返回两轮 Task。
- 前端刷新优先恢复未终止 Task；只有当前展示终态 Task 时出现“再次演示”。
- 点击后显示“创建中”，收到新 Snapshot 后切换到新 Task Runtime、清除旧工件选择并显示“启动任务”。
- Action Gate 打开时按钮禁用；接口不可用时保留旧终态事实，不提前显示新任务成功。
- 实际 `Idempotency-Key` 不在普通 UI 中展示。

## 5. 验证与边界

聚焦路由回归 `6 passed`，覆盖同 key 重放得到同 Task、不同 key 得到不同 Task、列表同时保留两轮。system Edge E2E `2 passed (17.5s)`，主用例新增完成一轮、刷新、点击“再次演示”、出现可用“启动任务”、列表包含不同新 Task ID 和旧 committed Task 的断言。全量回归为 Python `57 passed`、Ruff、前端 TypeScript lint 和 Next.js 生产构建通过。重启本地 `8010/3000` 后又用独立 smoke Owner 验证：同 key 返回同 Task、换 key 返回不同 `ready / contract` Task、列表数量为 2，前端 HTTP 200。

该结论只验证固定 Fixture 与内存 TaskStore 浏览器路径。PostgreSQL 跨进程恢复、多实例通知和演示轮次列表选择仍是现有边界；“再次演示”不会复制真实企业数据或触发真实 Connector。
