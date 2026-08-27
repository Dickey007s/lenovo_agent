# DR-0032-POSTGRES-DECISION-RECOVERY-EVIDENCE-20260827

## 状态

`Limited Verified`。2026-08-27 使用本机 PostgreSQL 17.11 实际执行顺序 Runtime 重启门；
本状态只覆盖被测协议、前台路径与真实 Provider 控制路径，不覆盖语义正确性、多实例或用户价值。

## 当前代码审计

`PostgresHarnessStateStore` 当前创建 `harness_run_state`、`harness_artifact_version`、
`harness_task_commit` 和 `harness_idempotency` 四张表。Run Snapshot 以 JSONB 原子写入，因此
Snapshot 中已有的 `EvidenceResolution` 与 `DecisionRecord` 会随 Run 重启恢复；它们没有独立的
追加表、来源修订约束或多实例 CAS。恢复 running round 时只保留 completed rounds，未提交的
当前 Branch/结果不会自动重放。

## 验证账本

| Gate | 当前结果 | 目标证据 |
| --- | --- | --- |
| 完整 Python | `85 passed` | 协议、Runtime、路由、状态库与 PostgreSQL 集成 |
| Runtime 定向 | `45 passed` | 五 Finding 挑战、五态 Resolution、DecisionRequest/Record、负向状态机与局部恢复 |
| PostgreSQL 17.11 | `2 passed` | 中断恢复；三候选待决重启；只恢复目标 Branch；v1/v2；再次重启 |
| 前端 TypeScript / build | `lint passed`、`build passed` | 契约类型、生产构建与普通 DOM 边界 |
| 浏览器 | `23 passed` | 桌面/390 px 候选对照、defer 后继续、cancel、断线恢复与既有路径 |
| 静态门 | Ruff passed、`git diff --check` 无错误 | Python 静态检查与补丁 whitespace |

## 关键挑战结果

确定性 Runtime 挑战建立 5 条 Finding 和 5 个 Branch，其中 4 条 quote 唯一定位，另一条在
同一文件出现三次。首轮 v1 保留四条 Finding 与完成 Branch；DecisionRequest 暴露三项服务端
候选。用户接受一项后，服务端重新读取当前 Catalog、校验 source revision、重算 candidate，
只恢复第五条 Branch 并 append v2，v1 不变。

真实 PostgreSQL 测试在 ambiguous Snapshot 后关闭 Runtime，再创建新 Runtime：开放的
DecisionRequest、三项 candidate、v1 和已完成 Branch 均保留；accept 后出现
`branch_resumed_from_checkpoint`，完成 v2；第二次重启后 DecisionRecord 与两版成果一致。

## 真实 Provider 与界面

真实 `deepseek-v4-pro` 运行见脱敏清单
[`dr-0032-evidence-resolution-live-run.json`](manifests/dr-0032-evidence-resolution-live-run.json)。
它在 PostgreSQL 上执行 2 轮、6 次模型调用：首轮两次分析结构均未采用，系统保留 v1 和两个
waiting Branch；用户只恢复“核对行政办公入职信息”，第二轮把范围缩到 2 份文件，采用 4 条
Finding 并 append v2，最终因“模型调用预算已耗尽”有界停止。该记录证明控制路径，不证明
Finding 正确或完整。

![桌面端三段式 Decision Packet、候选原文与真实预览](screenshots/dr-0032-decision-packet-desktop.png)

![390 px 下候选、处置动作、Branch 与轨迹保持可用](screenshots/dr-0032-decision-packet-mobile.png)

| 工件 | 尺寸 / 字节 | SHA-256 |
| --- | --- | --- |
| `dr-0032-decision-packet-desktop.png` | `1440 x 1100` / `145141` | `207F334B786EEA7D8024DB22DE29A9817967D5BA9C33D77AA119D8C769D5C39F` |
| `dr-0032-decision-packet-mobile.png` | `390 x 4750` / `275528` | `C897C3F99C069F639A08ECD1D83CADB4652F65A64789AAE3E359F59647AA79BE` |
| `dr-0032-evidence-resolution-live-run.json` | `3681` bytes | `345BFADCA7CD20BCF070FE485FF9DDF20B729556059822F4F0A632088E1BD509` |

## 仍然不能推断

- Evidence Anchor 只证明批准范围内的位置和成员关系，不证明蕴含、算术、覆盖或业务判断。
- `DecisionRequest/DecisionRecord/EvidenceResolution` 仍嵌在 Snapshot JSONB，不能独立查询审计。
- PostgreSQL `upsert` 无 CAS；本轮只证明顺序单 Runtime，不证明并发、多实例、高可用或 lease。
- 恢复不会续跑中断 HTTP；当前仍无可写 Office Artifact、Worker、Tool Gateway、Connector 或外部动作。
- 自动化、截图和单一 Stakeholder 反馈不是目标用户研究。
