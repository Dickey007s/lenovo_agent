# SCENARIO-038：同一办公任务跨 Run 延续而不覆盖历史

- 状态：`Proposed`
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
2. 用户选择一条 Branch，点击“在同一任务下继续”。
3. 前台先展示 continuation preview：父 Run、继承 Branch、基线成果、需要重核的来源、
   新预算和旧成果不会被覆盖。
4. 用户确认后，浏览器提交旧 Run expected version、幂等键和所选 Branch ID；不提交
   客户端猜测的文件范围或内部来源 hash。
5. 服务端校验 Owner、状态、Branch 归属、current source revision 与 idempotency，创建
   相同 `task_id`、新 `run_id`、有 `parent_run_id` 的后继 Run。
6. 未变化且已核对的事实作为 carried context；变化、stale、未完成或未过 Gate 的内容
   进入 `recheck_items`。
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
| 继续预览 | 父 Run、继承项、重核项、新预算、无外部动作 | 确认或取消 | raw hash、绝对路径、内部评分 |
| 创建成功 | 同一 Task 的新 Run 时间轴、继承回执 | 进入新 Run、返回旧 Run | 旧 Run 被重新打开 |
| 来源变化 | 哪些事实需重核及原因 | 回开当前安全 Preview、继续或结束 | 旧证据天然仍正确 |
| 新 Run 完成 | v2 与当前指针，v1 仍保留 | 下载/复核/恢复历史版本 | 源文件已写回或回滚 |

## 后端事实映射

| 前台状态 | 服务端权威事实 |
| --- | --- |
| 同一业务任务 | 新旧 Run `task_id` 相同 |
| 新一段执行 | 新 `run_id`、`parent_run_id=旧 run_id` |
| 已继承 | `ContinuationContract.carried_branch_ids` 与 receipt |
| 需要重核 | `recheck_items[]` + current source revision result |
| 旧成果保留 | 旧 ArtifactVersion/TaskCommit bytes 与行记录未变 |
| 新成果 | 新 Run 的 ArtifactVersion + 新 TaskCommit |
| 已从服务端恢复 | health task store=PostgreSQL + recovered Snapshot/Event |

## 完成条件

- 相同 Task 下至少存在两个 Run，父子关系、继承和重核范围可从公共业务投影核对。
- 只推进所选 Branch，未选 Branch 和旧成果状态不变。
- 来源变化时旧 Anchor 不被直接采用；用户可从重核项回开当前 Preview。
- PostgreSQL 重启、SSE 断线、重复请求和旧 version 均有确定性结果。
- 1440/390 px 不要求用户复制 Prompt，也不把 Run、Task、Artifact 三种身份混成一条。

## 自动化验收用例

1. `terminal_run_creates_child_run_under_same_task_id`。
2. `continuation_carries_only_selected_branch_and_preserves_others`。
3. `changed_source_revision_moves_carried_fact_to_recheck`。
4. `same_idempotency_key_replays_same_child_run_receipt`。
5. `stale_expected_version_creates_no_run_or_event`。
6. `postgres_restart_preserves_lineage_and_current_commit_pointer`。
7. `sse_reconnect_monotonically_projects_child_run_creation`。
8. `mobile_continuation_preview_wraps_without_hiding_recheck_items`。

## 设计来源 Source ID 与运行时 Fixture `source_ref`

- `USER-FEEDBACK-20260830-DEMO1-DEMO2-CONTINUATION`：要求延续 07-16 Demo 1。
- `DURABLE-AGENT-RUNTIMES-OFFICIAL-20260830`：Run/Workflow 持久与恢复是行业基线。
- `HAI-MIXED-INITIATIVE-RESEARCH-20260830`：说明状态、后果、纠错和用户控制。
- 运行 Fixture 必须使用公开 FORTE allowlisted 输入或专门构造的无敏感测试来源，并把
  `source_ref` 绑定到上述 Source ID；不能把 2400/2680 当成真实企业事实。

## 当前边界

当前 main 已有 Run 内 Branch/Artifact/Commit 和可选 PostgreSQL 恢复，但没有这里定义
的跨 Run `task_id` 与 continuation contract。本场景在实现、真实 PostgreSQL、Provider、
浏览器和 Evidence 完成前保持 `Proposed`；自动化也不证明目标用户更信任或更高效。
