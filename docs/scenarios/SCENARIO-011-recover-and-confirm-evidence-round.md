# SCENARIO-011：中断恢复与逐轮补证

> 生命周期：本场景保留为 `DR-0025` 的整组补证历史路径。当前“选择一条待处理分支、
> 保留其他分支、恢复任一成果版本”的用户路径见
> [`SCENARIO-012`](SCENARIO-012-selective-branch-and-artifact-restore.md)。

## 用户、触发与痛点

一名用户让 Agent 研究整个办公资料库并核对跨文件事实。第一轮已经形成部分结论，
但仍有一份本轮选中的材料没有进入可核对引用；此时继续调用模型会消耗剩余预算。
任务还可能因为浏览器刷新或 API 进程重启而中断。

用户需要回答的不是“系统内部是什么状态”，而是三个办公问题：现有成果保住了吗，
为什么还要继续一轮，以及确认后 Agent 会对成果造成什么变化。

## 主路径

1. 用户提交目标，服务端冻结整库合同并开始第一轮。
2. Planner/Analyst 返回后，服务端验证引用并生成“任务证据简报 v1”。
3. Evidence Gate 发现缺口且预算允许，Run 进入 `waiting_input`；不自动发起下一次模型调用。
4. 前台并排显示缺口、下一轮目的、剩余预算和三个动作：确认继续、先调整方向、结束并保留。
5. 用户点击“确认并继续核对”，服务端用 expected version 与幂等键接受 `resume`，并把下一轮范围锁定为刚才展示的缺失证据。
6. Planner 只能围绕这些待核文件编排补证计划，Plan Validator 要求全部覆盖；轨迹显示“正在核对上轮尚未覆盖的证据”。
7. 下一轮形成 v2。若证据门满足，v2 变为已提交并形成逻辑 Commit；v1 仍可回看。
8. 用户从引用打开来源文件，再决定是否复核结论或确认一个新的后续任务。

## 恢复路径

1. 浏览器刷新：客户端读取 session 中的 Run id，GET 权威 Snapshot，再从 `after=N` 恢复事件流。
2. 浏览器没有本地 id：客户端列出 Owner 最近 Runs，只恢复最近非终态 Run。
3. API 重启且 PostgreSQL 可用：服务端恢复已完成轮次、版本、事件和命令回执；未完成轮次被回滚，追加 `checkpoint_recovered` 并暂停。
4. 用户检查轨迹后显式 resume。恢复本身不会重放中断的 Planner/Analyst 调用。
5. API 使用 memory：重启后 Run 不存在，前台不得伪造恢复成功。

## 完成条件

- 缺口且可继续时，确认前模型调用计数不再增长，状态为 `waiting_input/paused`。
- resume 使用当前 Snapshot version 和唯一幂等键；重复提交返回同一回执。
- 补证轮的 `round.input_file_refs` 等于上一轮 `next_step.candidate_file_refs`；不能改去探索未被用户确认的文件。
- 页面刷新回到同一 Run，版本和 sequence 不倒退。
- 进程恢复删除未完成轮次但保留所有已完成轮次、逻辑成果版本和已接受命令。
- 每个成果版本能回到对应轮次的引用数量；最终 Commit 仍显示 `review_required=true`、`external_action=none`。
- 普通 UI 不显示数据库 DSN、表、绝对路径、完整 hash、Prompt、思维链或 raw provider response。

## 异常路径

| 异常 | 服务端行为 | 前台恢复 |
| --- | --- | --- |
| resume 使用旧版本 | 409，不开始新轮次 | GET 最新 Snapshot 后让用户重审 |
| 同一幂等键用于不同控制 | 409 | 保留当前任务和控制草稿 |
| 进程在模型调用中退出 | 不把未完成轮次视为完成，不自动重放 | 显示检查点已恢复，等待显式继续 |
| PostgreSQL 不可用 | API 启动失败而不是降级读取旧假状态 | 显示 API 离线；修复数据库或明确使用 memory |
| 用户选择停止 | 在安全点形成 bounded/user-stopped Brief | 保留已完成轮次和版本，不生成虚假 Commit |

## 来源与证据边界

- Stakeholder 来源：`USER-FEEDBACK-20260826-19` 与既有 Control Loop 参考图/命名反馈。
- 工程依据：PostgreSQL 事务化 JSON Snapshot、Owner/version/idempotency、Snapshot + ordered SSE 的既有项目策略。
- 数据依据：FORTE 固定公开输入清单；不使用真实企业文件或未公开 benchmark task。
- 本场景没有目标用户研究，不证明交互更清晰、恢复提高效率或模型结论更正确。
