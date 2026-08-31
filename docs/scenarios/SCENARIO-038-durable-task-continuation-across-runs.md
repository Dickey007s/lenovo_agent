# SCENARIO-038：同一办公任务跨 Run 延续而不覆盖历史

- 状态：`Limited Verified`；本地合同/Runtime/API/浏览器纵切，PostgreSQL 与 Provider 门仍开放
- 决策：`DR-0053`
- Source：`USER-FEEDBACK-20260830-DEMO1-DEMO2-CONTINUATION`、
  `DURABLE-AGENT-RUNTIMES-OFFICIAL-20260830`、`HAI-MIXED-INITIATIVE-RESEARCH-20260830`

## 用户与触发

- 用户：需要跨日完成财务、项目或经营分析，且必须复查来源和历史成果的办公用户。
- 触发：一个 Run 已到预算/终态，但仍有一条业务 Branch 值得继续；或来源在两次执行
  之间发生变化，需要保留旧结论并形成新版本。
- 痛点：只放大 Run 轮数会隐藏成本边界；重新开一条聊天又要求用户重讲背景，且无法
  证明旧成果是否被覆盖、旧引用是否仍有效。

## 前置条件

1. 旧 Run 属于当前 Owner，状态为 terminal 或明确 budget-stopped。
2. 旧 Run 至少有一个 Branch、ArtifactVersion 或 TaskCommit 可作为继承基线。
3. Workspace Catalog 能重新核对当前来源 revision 与安全 Preview。
4. 当前仍是 `external_action=none`；不因“继续任务”获得新的外部动作权限。

## 主路径

1. 用户打开旧 Run，查看已完成、未完成和待核对 Branch，以及 v1/v2 等历史成果。
2. 用户选择一条 Branch，点击“继续未完成任务”。
3. 浏览器提交旧 Run expected version、幂等键和所选 Branch ID；不提交客户端猜测的
   文件范围或内部来源 hash。当前实现没有额外的提交前 continuation preview。
4. 服务端校验 Owner、状态、Branch 归属、current Workspace revision 与 idempotency，创建
   相同 `task_id`、新 `run_id`、有 `parent_run_id` 的后继 Run。
5. child Snapshot 记录 `carried_branch_id`、旧 Artifact/Commit 基线和该 Branch 的精确
   `recheck_file_refs`；即便 Workspace revision 未变化，也重新核对这条 Branch 的批准
   来源，不把旧模型自由文本当作新 Run 权威事实。
6. 来源 revision 变化时 `source_revision_changed=true`，前台明确提示只重核批准范围。
7. 后继 Run 在新合同和预算内继续 Observe/Plan/Act/Verify/Commit，只推进所选工作线。
8. 新成果形成新的 ArtifactVersion 和 TaskCommit。旧 Run、旧 Event、旧 Artifact、旧
   Commit 和源文件保持不变。

## 典型 Demo 镜头

旧 Run 的 `customer-facts` 与 `project-risk` 已完成，`revenue-baseline` 因正式口径
2400 万与预测口径 2680 万等待。用户先结束当日工作，次日从同一 Task 继续收入分支，
选择正式口径作为当前值并保留预测差异。系统只恢复收入分支，最终在新 Run 生成 v2；
旧 Run 的 v1 仍可打开。

## 异常路径

- **来源变化**：Manifest/file revision 与旧 Run 不同。服务端把对应事实标为 recheck，
  不得静默携带旧 Anchor。
- **旧 expected version**：返回 409；不创建新 Run，不新增 Event/Artifact/Commit。
- **重复幂等键**：返回同一 continuation receipt；不得多建后继 Run。
- **Branch 不属于旧 Run**：fail closed；公共错误不泄露其他 Owner 的 Branch 是否存在。
- **旧 Run 仍在运行**：不允许 continuation；用户先 pause/stop 或等待终态。
- **完整性失败**：Workspace Catalog/Preview fail closed，不创建可执行后继 Run。
- **memory 模式重启**：明确本轮不可恢复，不用本地缓存伪造 Task 历史。
- **未完成模型调用**：不自动重放；后继 Run 从服务端定义的安全边界重新计划。

## 前台输出

| 阶段 | 用户看到 | 用户可做 | 不应看到/推断 |
| --- | --- | --- | --- |
| 旧 Run 终态 | 已完成、待继续、预算停止原因、历史成果 | 选一条 Branch、打开旧证据 | “多加几轮”假按钮 |
| 继续动作 | 目标 Branch、为何新建 Run、旧成果不覆盖 | 点击“继续未完成任务”或不处理 | raw hash、绝对路径、内部评分 |
| 创建成功 | “任务持续链 · Run 2”、基线成果、精确重核范围 | 进入新 Run、查看父子关系 | 旧 Run 被重新打开 |
| 来源变化 | 哪些事实需重核及原因 | 回开当前安全 Preview、继续或结束 | 旧证据天然仍正确 |
| 新 Run 完成 | v2 与当前指针，v1 仍保留 | 下载/复核/恢复历史版本 | 源文件已写回或回滚 |

## 后端事实映射

| 前台状态 | 服务端权威事实 |
| --- | --- |
| 同一业务任务 | 新旧 Run `task_id` 相同 |
| 新一段执行 | 新 `run_id`、`parent_run_id=旧 run_id` |
| 继续的工作线 | `carried_branch_id`，且只能是旧 Run 的所选 Branch |
| 需要重核 | `recheck_file_refs[]` + `source_revision_changed` + `workspace_revision` |
| 旧成果保留 | 旧 ArtifactVersion/TaskCommit bytes 与行记录未变 |
| 新成果 | 新 Run 的 ArtifactVersion + 新 TaskCommit |
| 已从服务端恢复 | health task store=PostgreSQL + recovered Snapshot/Event |

## 完成条件

- 相同 Task 下至少存在两个 Run，父子关系、继承和重核范围可从公共业务投影核对。
- 只推进所选 Branch，未选 Branch 和旧成果状态不变。
- 来源变化时旧 Anchor 不被直接采用；用户可从重核项回开当前 Preview。
- 重复请求和旧 version 已有确定性自动化结果；PostgreSQL 重启测试已收集但本机无 DSN
  而跳过，不能算已验证。
- 1440/390 px 不要求用户复制 Prompt，也不把 Run、Task、Artifact 三种身份混成一条。

## 自动化验收用例

1. `test_demo1_continuation_creates_child_run_with_exact_carried_branch_scope`。
2. `test_demo1_continuation_http_route_returns_same_task_child_run`。
3. `test_postgres_demo1_continuation_lineage_cas_and_restart`：已收集；无
   `TEST_DATABASE_DSN` 时 skip。
4. 浏览器 `Demo 1 shows a durable task timeline and continues only the unfinished branch`：
   覆盖 child Run、批准来源、来源变化条件式提示、桌面/390 px 字号与无横向溢出。
5. 聚焦门
   `test_demo1_http_continuation_preserves_parent_and_limits_changed_source_scope`：覆盖
   changed/unchanged revision、父 Snapshot/Event/Artifact/Commit 不变、精确 child scope、
   幂等 replay、旧 version 和 Owner 负向路径；见
   [`固定场景 Evidence`](../evidence/DR-0053-DEMO1-DEMO2-FIXED-SCENARIO-GATES-EVIDENCE-20260831.md)。

## 设计来源 Source ID 与运行时 Fixture `source_ref`

- `USER-FEEDBACK-20260830-DEMO1-DEMO2-CONTINUATION`：要求延续 07-16 Demo 1。
- `DURABLE-AGENT-RUNTIMES-OFFICIAL-20260830`：Run/Workflow 持久与恢复是行业基线。
- `HAI-MIXED-INITIATIVE-RESEARCH-20260830`：说明状态、后果、纠错和用户控制。
- 运行 Fixture 必须使用公开 FORTE allowlisted 输入或专门构造的无敏感测试来源，并把
  `source_ref` 绑定到上述 Source ID；不能把 2400/2680 当成真实企业事实。

## 当前边界

当前实现已有服务端 `task_id`、同 Task child Run、单 Branch 范围、基线成果、Workspace
revision/精确重核 refs、公共投影和 Task 时间线。`DR-0054` 又增加最小 owner-scoped
Task record/current pointer、Task GET 和 Task/Run 双版本仲裁；Run Snapshot 仍拥有
Branch、Budget、Event、Artifact/Commit 等执行细节。revision 主要是 Workspace 数据集级，
不是完整 per-file 版本服务；也没有 WorkUnit ledger、queue/lease 或多实例执行协调。
新增 Task PostgreSQL 门在本机没有 DSN 而跳过，真实 Provider 未运行，
也没有目标用户研究。因此这里只能标 `Limited Verified`，不能声称跨进程门、业务正确性、
用户理解或效率已经改善。
