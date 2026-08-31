# Task Ledger V1 验收门（2026-08-31）

- 状态：`Limited Verified`；定向实现门通过，真实 PostgreSQL Task 门未运行
- 决策：`DR-0054`
- 场景：`SCENARIO-040`

## 1. TL-01 初始 Task 与查询

- 启动普通 Run 后，State Store 同时存在 version 1 Task record，current 指向该 Run。
- `GET /v1/harness/tasks/{task_id}` 对 Owner 返回 sanitized Task 与 lineage；其他 Owner
  返回 404/403，不暴露 Owner、内部路径或 raw hash。
- Run 公共 Snapshot 的 `task_id/task_version/current-run` 投影与 Task 查询一致。
- Task 查询只读台账和它指向的 Run；不得在 GET 时临时扫描 Run 并写入缺失台账。
  台账存在但 current Run 缺失、或旧 Run 存在但台账缺失时返回完整性错误，不合成
  `unknown` 状态。当前 Artifact/Commit 指针由 current Run 派生，不在 Task 表重复维护。

## 2. TL-02 原子 continuation

- parent 有 completed + unfinished Branch、v1 Artifact/TaskCommit。
- continuation 同时携带 `expected_version` 与 `expected_task_version`。
- 成功后 child 同 Task、新 Run、sequence+1，Task version+1/current=child；parent 全量
  Snapshot/Event/Artifact/Commit 不变。
- store failure 注入必须使 Task、child、幂等 receipt 全部不变。
- PostgreSQL continuation 必须在同一事务中同时校验 parent Run version 与 Task version，
  不能只依赖某一 API 进程的内存预检。

## 3. TL-03 sibling CAS 与幂等

- 两个不同幂等键从同一 parent、同一旧 Task version 竞争：只能一个成功。
- 失败请求返回 409，Run 数、Task version、lineage、Events、Artifact 和 Commit 不变。
- 成功请求使用同幂等键 replay：返回同一 child，不重复前移 Task。
- 同幂等键不同 payload：409，不能复用旧 receipt 生成另一 child。

## 4. TL-04 重启与旧数据 backfill

- 同一个 InMemory store 重建 Runtime 后，Task/current/lineage 与重启前一致，不自动重放
  模型调用。
- 只有旧 Run Snapshot 时，唯一递增 sequence 可回填 Task；重复最大 sequence、断裂 parent
  或冲突 pointer 必须 fail closed。
- PostgreSQL integration 覆盖真实事务/CAS/restart；没有 `TEST_DATABASE_DSN` 时只记 skip。

## 5. TL-05 前台

- Task 时间线明确标“当前 Run”，旧 Run 和历史成果仍可打开。
- continuation 请求包含两种 expected version。
- Task 409 时保留 parent 画面与 SSE generation，提示刷新；刷新后只出现权威 child。
- Task GET 失败时显示可重试状态，不能只依赖下一条 Run Snapshot 偶然触发重试。
- 1440 px 与 390 px 正文不小于既有门槛，无页面级横向滚动。

## 6. 证明边界

| 门 | 可以证明 | 不能证明 |
| --- | --- | --- |
| memory unit/API | Task/Run 原子状态机、Owner、CAS、幂等 | 真实数据库、多实例 |
| simulated restart | 相同 adapter 的加载/回填语义 | 进程崩溃、磁盘故障 |
| PostgreSQL integration | 单数据库顺序事务与重启 | HA、lease、跨区域 |
| browser mock/真实 API | 请求字段、冲突反馈和响应式投影 | 目标用户一定理解 |

## 7. 当前执行记录

- 定向 memory/API/Demo 1/2 Python：`92 passed`。
- PostgreSQL Task Ledger：`7 collected`、`7 skipped`，原因是未配置
  `TEST_DATABASE_DSN`；不得写成真实数据库已通过。
- Task Ledger browser mock：`4 passed`；Ruff、TypeScript lint 与 production build 通过。
- 整库 Python：`410 passed, 23 skipped in 277.38s`；整库 Playwright：`68 passed
  (2.6m)`。skip 仍按各自环境门解释，不能合并写成全功能验证。
- 既有 TC-04 单测经独立复核为 `1 passed in 42.23s`，相关 scenario effects 为
  `35 passed in 228.01s`；10 秒 faulthandler 只报告仍在等待真实 subprocess。真实
  Provider 和目标用户研究均未运行。

## 8. 本阶段禁止升级的结论

- Task ledger 不等于 WorkUnit queue、Worker lease 或分布式执行器。
- PostgreSQL 表已创建不等于真实 PostgreSQL 门已通过。
- current pointer 一致不等于业务结果正确。
- 自动化不能替代 Provider 结果验证或用户研究。
