# Demo 1 PR 5 PostgreSQL-backed API Restart Evidence

| 字段 | 内容 |
| --- | --- |
| Evidence ID | `POSTGRES-BACKED-API-RESTART-DEMO1-PR5-20260811` |
| Date | 2026-08-11，Asia/Shanghai |
| Branch | `feature/demo1-postgres-restart-20260811` |
| Tested implementation | Git commit `4634d8a` |
| Decision | [`DR-0002`](../decisions/DR-0002-bounded-durable-office-loop.md) |
| Scenario | [`SCENARIO-001`](../scenarios/SCENARIO-001-customer-a-durable-report.md) |
| Status | `Verified engineering path`，仅限固定 Demo 1 Fixture、本机 PostgreSQL 16.14、同一数据库和顺序启动的单个 API 进程 |

## 1. 场景、来源与成功标准

场景异常路径是：用户已经得到 `v2 / waiting_input` 或 `v3 / committed` 的长期 Task，API 进程退出后重新启动。用户应看到最后确认的 Snapshot 仍保留、控制暂时禁用、连接恢复后继续显示同一 Task ID、版本、分支 head、工件和 Commit；重放旧命令不能产生重复事件、工件或 Commit。

运行时使用 EDB 发布的 PostgreSQL 16.14 Windows x64 binaries。下载文件为 `postgresql-16.14-2-windows-x64-binaries.zip`，大小 `325741585` bytes，SHA-256 `8A7F54C1968D5D49BDCD3F66B1291F736C74B8CB6A26E9874771FCC7837DBF38`。便携运行目录位于 Git 忽略的 `.runtime/`，没有提交二进制、数据目录、DSN 或凭据。官方来源与局限登记在 [`SOURCE_REGISTER`](../decisions/SOURCE_REGISTER.md)。

成功标准：

1. API A 使用 PostgreSQL TaskStore 创建并启动任务，得到 `v2 / waiting_input / sequence 32 / 5 ArtifactVersion`。
2. 只停止 API A；API B 使用同一数据库后，`GET /tasks/{id}` 与 `GET /tasks` 必须逐字段恢复同一 v2 Snapshot。
3. API B 解决最后冲突并得到 `v3 / committed / sequence 45 / 7 ArtifactVersion / 1 TASK_COMMITTED`。
4. 只停止 API B；API C 必须逐字段恢复同一 v3 Snapshot。
5. API C 重放旧 start key 返回原 v2，重放旧 resolve key 返回原 v3；当前 GET 仍为 v3，数据库行数完全不增加。
6. 浏览器在 API 停止时保留旧 Snapshot、显示恢复状态并禁用控制；新进程启动后显示已同步且 Task 事实不变。

## 2. 可重复后端验收

新增的 opt-in 系统测试是 [`tests/system/test_postgres_api_restart.py`](../../tests/system/test_postgres_api_restart.py)，薄封装是 [`scripts/verify-postgres-restart.ps1`](../../scripts/verify-postgres-restart.ps1)。普通 `pytest` 未配置维护库 DSN 时明确 skip，不会连接或修改开发者数据库；opt-in 用例只创建随机 `oa_restart_*` 数据库，并在 `finally` 中停止自己启动的 API、强制断开该随机库连接后删除该库。

复现入口：

```powershell
$env:OFFICE_AGENT_POSTGRES_ADMIN_DSN = "<PostgreSQL 16 maintenance database DSN>"
.\scripts\verify-postgres-restart.ps1
```

2026-08-11 实际结果：

```text
api_a_pid=58056
api_b_pid=59268
api_c_pid=56124
postgres_server_version=160014
task_version=3
status=committed
event_rows=45
artifact_rows=7
commit_rows=1
state_hash=sha256:11d54c157ac99893c5377157198ea7b10401237c528623861db44e096b96241a
1 passed in 9.62s
```

测试同时断言：API A/B 都在下一进程启动前退出，API C 完成后也退出；健康接口的 `task_store=postgres`；自动化只验证 TaskStore，所以主动保持 `checkpoint=memory`；v2/v3 的列表与详情响应均与重启前完全相等；两个历史幂等响应分别等于原 v2/v3；重放前后 `1 task / 45 events / 7 artifacts / 1 commit` 不变。测试结束后随机数据库和三个测试 API 进程均已清理。PID 仅作为单次运行诊断记录，不作为跨平台正确性断言，因为操作系统允许复用已退出进程的 PID。

## 3. 前台输出与服务端事实

本机 system Edge 在同一页面中连接 Next.js `3000` 和 PostgreSQL-backed FastAPI `8013`。基于 tested implementation `4634d8a` 的最终一轮使用隔离数据库和 API listener PID `2800 → 58320 → 7128` 顺序重启，Task ID 始终为 `task_3584e2b9aa06d2b025c1f71d1c107813`；v2 为 `sequence 32 / 5 artifacts`，v3 为 `sequence 45 / 7 artifacts`，最终 state hash 为 `sha256:9749bc4cd945ec11f2a872016abd8efc3ee4559829a313e2b142d652a33ffb3d`。PID 只记录本轮进程身份；验收后隔离数据库已删除，演示服务恢复为本地常驻数据库。

| 前台状态 | 服务端或传输事实 | 用户动作与恢复 | 隐藏内容 |
| --- | --- | --- | --- |
| API 在线、Snapshot 已读取 | `GET TaskSnapshot` 成功；客户端 `syncState=synced` | 显示“已连接当前工作区 / 状态已同步”，允许服务端合法控制 | DSN、幂等键、完整 Task JSON |
| API 进程停止 | EventSource error；没有新的业务 Snapshot | 保留最后确认的 Task ID、v2 冲突或 v3 Commit；显示“服务连接中断，正在恢复 / 正在重新对账”；控制禁用 | 网络堆栈、内部重试日志、原始事件 payload |
| API 新进程启动 | EventSource 重连后重新 `GET /tasks/{id}` | 只有 GET 成功并对账后恢复“已连接 / 已同步”和控制 | 不增加 PostgreSQL 技术徽标，不生成 `TASK_RESTORED` 业务事件 |
| 冲突来源展开 | `conflicts[].source_refs` | 仅四个已知 Demo 1 Fixture 引用可见；其他引用显示隐藏占位 | token、secret、signature、URL、路径或其他未知内部标识 |

顶部连接文案此前会在 Task 面板已断线时仍显示“已连接当前工作区”。本轮新增独立 `taskTransportState`，只让 EventSource/Task API 连接事实驱动顶部“连接中/已连接/连接中断”文案；`taskSyncState=reconnecting` 仍可单独表达 pending mutation 或 Snapshot 对账，不再被误报为网络断线。冲突卡与 Artifact Workspace 现在复用同一个 `formatSourceReference` 投影，只放行契约中的四个已知 Demo 1 Fixture 引用，其他值 fail closed；URL、路径和凭据形态负例已有回归。该投影只是前端第二道防线，不替代服务端授权和脱敏。

## 4. 浏览器截图

| 文件 | 尺寸 | SHA-256 | 证明范围 |
| --- | --- | --- | --- |
| [`demo1-postgres-backed-api-restart-v2.png`](screenshots/demo1-postgres-backed-api-restart-v2.png) | 1440 x 900 | `0A923BD4D8D8E21A23C66C9EB03F5BB4B2456337B45928B6F4706268E6A7E1CA` | API A 下 v2 冲突 Snapshot 与已连接状态 |
| [`demo1-postgres-backed-api-restart-disconnected-v2.png`](screenshots/demo1-postgres-backed-api-restart-disconnected-v2.png) | 1440 x 900 | `2C1BE2EF20CFA56406A9ABB30EA2889E87AB0ACDC47487EA831975F87A861839` | API 停止后仍保留 v2，顶部和 Task 面板一致显示恢复中，控制禁用 |
| [`demo1-postgres-backed-api-restart-recovered-v2.png`](screenshots/demo1-postgres-backed-api-restart-recovered-v2.png) | 1440 x 900 | `AB8C3990B4BDA9F35CC0F1D0FAE82F3B4F8D18B5159C1A71585160A96F6D3F01` | API B 恢复后同一 Task ID、v2 冲突与已同步状态 |
| [`demo1-postgres-backed-api-restart-v3.png`](screenshots/demo1-postgres-backed-api-restart-v3.png) | 1440 x 900 | `9BF76FC4386FAB2ECDB88934369E396A11E01F5DC687352F57D61FF33F174865` | API B 下 v3 committed 与三个 committed 分支 |
| [`demo1-postgres-backed-api-restart-recovered-v3.png`](screenshots/demo1-postgres-backed-api-restart-recovered-v3.png) | 1440 x 900 | `60DC9EBEFED37EDD281293F25957A3AB6998109700F98458ABFAE025ED79AC45` | API C 恢复后同一 v3 Commit 与已同步状态 |

浏览器流程使用一次性、Git 忽略的本地 Playwright runner 驱动 system Edge，并实际断言连接文案、控制禁用、同 Task ID、v2/v3 Snapshot 全等和最终 state hash；它不是本 PR 提交的持续自动化用例。可重复、提交到仓库的恢复证据以第 2 节的 Python system test 为准。

## 5. 当前可说与不可说

可以限定陈述：

- 固定 Demo 1 TaskStore 已在本机 PostgreSQL 16.14 上通过两个恢复点、三个顺序 API 进程的跨进程恢复验证。
- 相同 start/resolve key 在后续状态和再次重启后仍返回首次结果，数据库没有新增事件、ArtifactVersion 或 Commit。
- 前台在 API 断开时保留最后确认 Snapshot、禁用控制并显示恢复状态；新进程可用后重新 GET 同一服务端事实。

仍不得陈述：

- 不得说整个工作区会话无损恢复。Conversation Thread/Message 仍在 API 内存中，旧 thread ID 重启后失效；本证据只覆盖 Task 面板和 Task API。
- 不得说已验证数据库进程重启、事务中途崩溃、已有库迁移、多实例并发通知、负载均衡或生产故障恢复。
- 不得把本次同页 EventSource 断开与重连称为断线期间事件回放证明；停机期间没有新业务事件，`after` 缺口、多实例和响应丢失仍待测。
- 不得说固定 start 是真实后台长任务、LLM 规划或真实 CRM/邮件读取；它仍是一次事务内物化的固定 Fixture。
- 不得把功能正确性和截图扩展为用户更易理解、更少等待或更有效接管；`H-001` 至 `H-004` 仍需目标用户研究。

## 6. 回归

- PostgreSQL opt-in system test：`1 passed in 9.62s`。
- system Edge suite：`3 passed in 17.9s`；其中两条为 PR 4 浏览器路径，一条为本轮新增的 source-ref fail-closed 负例回归；pending mutation 路径还断言传输在线时顶部不误报网络断线。
- 完整 Python：`56 passed, 1 skipped in 2.68s`；skip 是未向普通测试进程提供 opt-in 维护库 DSN 的 PostgreSQL system test。
- 治理文档定向回归：`4 passed in 0.03s`。
- `uv run ruff check .`、`pnpm --dir apps/web lint`、`pnpm --dir apps/web build` 与 `git diff --check` 均通过。
