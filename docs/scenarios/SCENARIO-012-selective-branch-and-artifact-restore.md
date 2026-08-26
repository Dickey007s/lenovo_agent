# SCENARIO-012：选择待处理分支并恢复历史成果

## 用户、触发与痛点

用户让 Agent 在整个 FORTE 办公资料库中完成一项跨文件任务。Planner 把任务拆成多个
相互依赖的工作单元；Analyst 已完成其中一部分，但两条分支仍缺少可核对引用。用户不想
让 Agent 自动消耗剩余预算，也不想为了处理一条分支而丢掉另一条分支的状态。

任务结束后，用户还需要比较不同轮次的成果。如果新版不符合当前汇报口径，用户希望把
“当前成果”恢复到旧版，同时保留新版和全部操作记录。

## 主路径

1. 服务端校验 Planner 候选计划，并把每个通过校验的工作单元编译为稳定 Branch；依赖、输入范围和人工门由服务端记录。
2. Analyst 返回后，服务端按每条 Branch 的输入引用计算 `completed` 或 `waiting_input`，而不是由浏览器猜测。
3. Evidence Gate 暂停整个 Run。前台显示每条分支的业务标题、依赖数量、资料数量和缺口数量。
4. 用户选择其中一条“继续此分支”。versioned/idempotent `resume` 携带 `branch_id`；其他等待分支原样保留。
5. 下一轮 Planner 只能看到所选 Branch 的 `missing_file_refs`。该分支补齐后，如果还有其他缺口，系统再次暂停并让用户选择。
6. 每个完成轮次把完整简报内容写成独立 append-only ArtifactVersion；最终 Evidence Gate 新建 TaskCommit 指向通过校验的版本。
7. 用户在成果历史中选择旧版本并点击恢复。服务端先核对独立 ArtifactVersion 的 digest，再新建 `operation=rollback` 的 TaskCommit；旧版本、新版本和原 Commit 均不删除。
8. 前台立即显示当前指针、恢复后的简报内容和“已恢复历史成果版本”轨迹；原始 FORTE 文件始终不变。

## 完成条件

- `round.branch_ids`、`snapshot.branches[]` 与 validated plan units 一一对应，Branch ID 由服务端生成。
- 两条分支等待时，选择 A 后的下一轮输入只包含 A 的缺失引用；B 仍保持 `waiting_input`。
- Branch 状态、Evidence Gap、resume ControlEvent 与 active branch 能通过 Snapshot 对账。
- ArtifactVersion 和 TaskCommit 分别写入 append-only 存储；相同主键不同 digest 必须 fail closed。
- 恢复版本只新增 TaskCommit 并移动 `last_commit`，ArtifactVersion 数量和历史 Commit 不减少。
- PostgreSQL 验证覆盖至少四个顺序 Runtime：中断、恢复完成、恢复旧版本、再次恢复并读取当前指针。
- 普通 UI 不显示数据库表、digest、内部路径、Prompt、思维链、raw provider response 或内部工具策略字符串。

## 异常路径

| 异常 | 服务端行为 | 前台恢复 |
| --- | --- | --- |
| branch_id 不存在或已完成 | 409，不启动模型调用 | 刷新 Snapshot，重新选择仍在等待的分支 |
| 旧 Snapshot version | 409 | 对账后重新审阅分支状态 |
| ArtifactVersion 独立记录缺失或 digest 不一致 | 409，拒绝恢复 | 显示不可恢复，不伪造当前版本变化 |
| 恢复当前版本 | 409 | 保持当前指针，不新增 Commit |
| PostgreSQL 不可用 | API 启动失败 | 显示 API 离线；不得回退成静态成功数据 |
| 预算耗尽 | 等待分支转为 stopped，保留已完成分支和版本 | 显示剩余缺口与停止原因 |

## 来源与证据边界

- Stakeholder 来源：`USER-FEEDBACK-20260826-20`，延续 0716-v2 的 Demo 1 分支管理与前台影响要求。
- 工程依据：validated plan DAG、Evidence Gate、Owner/version/idempotency、Snapshot + ordered SSE 和 PostgreSQL append-only records。
- 数据依据：FORTE 固定公开输入清单，不使用真实客户文件或未公开 benchmark task。
- 本场景验证顺序单 Controller 的分支级控制，不等于 Demo 2 多任务自组织或并行 Worker。
- 自动化和截图不是用户研究；理解、信任、效率与业务质量仍为 `Draft`。
