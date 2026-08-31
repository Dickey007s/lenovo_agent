# SCENARIO-040：两个页面同时续办时只有一个当前 Run

- 状态：`Proposed`
- 决策：`DR-0054`
- Source：`USER-FEEDBACK-20260831-DEMO1-DEMO2-FIXED-SCENARIO-HARDENING`、
  `DURABLE-ENTITY-STATE-OFFICIAL-20260831`

## 用户、触发与完成条件

- 用户：跨日处理同一办公任务、可能在多个页面或由同一团队成员重复打开任务的负责人。
- 触发：parent Run 已终态并有一个可继续 Branch；两个页面都显示相同的旧 Task/Run
  版本，并几乎同时点击继续。
- 痛点：只校验 Run version 不能回答哪个 child 是 Task 当前工作面；若两个都成功，用户
  会看到分叉成果并被迫自行判断。
- 完成条件：第一个合法请求原子创建 child 并前移 Task current pointer；第二个旧 Task
  version 请求明确冲突、零状态变化，刷新后可看到同一个权威 child。

## 主路径

1. 页面 A、B 打开同一 parent，读取 `run.version=N`、`task_version=T`。
2. 两页选择同一未完成 Branch。浏览器提交 parent version、Task version、Branch 与各自
   幂等键，不提交客户端猜测的文件范围。
3. 页面 A 先到达，服务端在同一 store commit 中写入 child Run、start idempotency
   receipt，并把 Task 从 T 更新为 T+1、current 指向 child。
4. 页面 B 的条件更新因 Task 已是 T+1 而失败；服务端不创建第二个 child。
5. 页面 B 保留 parent 画面，提示“当前任务已有新的 Run，请刷新查看”，刷新 Task 后
   看到与页面 A 相同的 current child。
6. child 仍只推进所选 Branch，旧 Run/Event/Artifact/Commit 不变。

## 前台输出

| 阶段 | 页面 A | 页面 B |
| --- | --- | --- |
| 提交前 | 当前 Run 为 parent；可继续一个 Branch | 相同 |
| A 成功 | 时间线新增 child，child 标“当前 Run” | 暂时仍显示 parent |
| B 冲突 | 不受影响 | 显示 Task 已更新；不清空旧成果、不切 SSE |
| B 刷新 | child 仍为 current | 同一 child、同一 Task version |

## 后端事实

- Task record：`task_id/task_version/current_run_id/current_run_sequence`；Run lineage 由同
  `task_id` 的不可变 Snapshot 派生，不在 Task 表再复制一份 `run_ids`。
- parent Run：`expected_version`、Branch 归属、immutable Artifact/Commit。
- continuation receipt：Owner、两种 expected version、幂等 digest 与 child Run。
- State Store：Task 条件更新、child Run 和 receipt 同一提交边界。

## 异常路径

- **同幂等键同请求重试**：返回相同 child；Task version 不再递增。
- **同幂等键不同请求**：409；不泄露原请求内容。
- **旧 Run version**：即使 Task version 当前也拒绝，避免从过期 parent 状态继续。
- **错误 Owner**：404/403；不能查询 Task 或 child 是否存在。
- **store 在事务中失败**：Task、child、receipt 全部回滚。
- **重启前有在途模型调用**：只恢复已提交 Task/Run 检查点，不自动重放调用。
- **旧数据有重复最大 run sequence**：backfill fail closed，不按 updated_at 猜 current。

## 用户自行验证问题

1. 哪个 Run 是当前工作面，旧 Run 是否还在？
2. 第二个页面的失败是否说明任务丢失，还是说明需要刷新？
3. 刷新是否出现两个 child？
4. continuation 是否扩大了文件范围或触发外部动作？

该场景的自动化通过只能证明版本与状态合同。用户是否理解冲突提示、是否减少误操作，
仍需要目标用户形成性测试。
