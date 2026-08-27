# DR-0032-POSTGRES-DECISION-RECOVERY-EVIDENCE-20260827

## 状态

`Draft`。本文件记录真实 PostgreSQL 验证门和当前边界；没有 `TEST_DATABASE_DSN` 时，测试为
`skipped`，不得写成 PostgreSQL 已通过。

## 当前代码审计

`PostgresHarnessStateStore` 当前创建 `harness_run_state`、`harness_artifact_version`、
`harness_task_commit` 和 `harness_idempotency` 四张表。Run Snapshot 以 JSONB 原子写入，因此
Snapshot 中已有的 `EvidenceResolution` 与 `DecisionRecord` 会随 Run 重启恢复；它们没有独立的
追加表、来源修订约束或多实例 CAS。恢复 running round 时只保留 completed rounds，未提交的
当前 Branch/结果不会自动重放。

## 验证账本

| Gate | 当前结果 | 目标证据 |
| --- | --- | --- |
| PostgreSQL 现有恢复测试 | `1 passed`（需要 `TEST_DATABASE_DSN`） | 中断、恢复、ArtifactVersion/TaskCommit、rollback |
| DR-0032 顺序恢复测试 | `skipped`（本机未提供 DSN） | 三候选、pending DecisionRequest、重启、目标 Branch、v2、再次重启 |
| 幂等/版本负测 | 待实现 | 重复 key、旧 version、stale revision、篡改 candidate、拒绝候选 |

实现门通过前，只能报告“Snapshot JSONB 具备保存能力，尚未有 DR-0032 真实重启证据”。
