# DR-0032：持久化人工决定与 Finding/Branch 局部恢复

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Draft`；等待真实 PostgreSQL 门与 Runtime 实现完成 |
| 日期 | 2026-08-27 |
| 触发来源 | [`USER-FEEDBACK-20260826-ACTIONABLE-RECOVERY`](../sources/USER-FEEDBACK-20260826-actionable-conflict-and-recovery.md) |
| 研究依据 | [`ACTIONABLE-HUMAN-DECISION-AND-FAILURE-RECOVERY-20260826`](../research/ACTIONABLE-HUMAN-DECISION-AND-FAILURE-RECOVERY-20260826.md)、`COMPETITIVE-WHITE-SPACE-AND-FALSIFIABLE-DIFFERENTIATORS-20260826` |
| 场景 | [`SCENARIO-018`](../scenarios/SCENARIO-018-persistent-decision-and-local-recovery.md) |
| Evidence | [`DR-0032-POSTGRES-DECISION-RECOVERY-EVIDENCE-20260827`](../evidence/DR-0032-POSTGRES-DECISION-RECOVERY-EVIDENCE-20260827.md) |

## 问题定位

当前 PostgreSQL 将完整 Run Snapshot 写入 JSONB，所以已写入 Snapshot 的
`EvidenceResolution` 与 `DecisionRecord` 会随 Run 一起恢复；但两者不是独立的追加账本，
也没有来源修订、候选版本和决定回执之间的数据库约束。进程在 running round 中断时，恢复逻辑
会丢弃该轮尚未提交的 Branch 与结果，只回到最后完成轮次。没有专门的重启门，不能把这种行为
写成“人工决定可靠恢复”。

## 决策

1. `EvidenceResolution` 由服务端拥有，至少区分 `exact`、`ambiguous`、`unavailable`、
   `stale`、`rejected`；模型只提供 quote 候选，不提供最终位置或状态。
2. 定位失败缩小到 Finding/Branch。已完成 Branch、已采用 Finding 和 ArtifactVersion 不因
   相邻 Finding 失败而丢失；安全完整性、任务合同损坏和无法建立可信状态仍 fail closed。
3. `DecisionRequest` 描述开放的人机决定，绑定 Run、Branch、Finding、Resolution、来源修订、
   候选、后果和 `external_action=none`。`DecisionRecord` 记录 accept/decline/defer/cancel，
   并保留 expected version、幂等键和生效回执。人的选择不是文件事实。
4. 接受候选后只恢复绑定 Branch，并产生新的 ArtifactVersion；旧版本和其他 Branch 保持不变。
   所有控制请求必须携带 expected version 与幂等键，Snapshot 仍是权威，SSE 只是变化投影。
5. 当前数据库模型仍是 Snapshot JSONB 加独立 Artifact/Commit 表；本决策不宣称已有独立
   Decision ledger、CAS、多实例 lease 或在途模型调用续跑。

## 验证门

真实 PostgreSQL 测试必须覆盖：三处相同 quote 的候选消歧；重启后 pending DecisionRequest、
EvidenceResolution 和已完成 ArtifactVersion 保留；接受后只恢复目标 Branch 并追加 v2；再次
重启后 v1/v2 与 DecisionRecord 一致；重复幂等键、旧版本、来源修订、篡改候选、拒绝候选、
全部不可用和完整性失败均不改变错误边界。没有 `TEST_DATABASE_DSN` 时测试只能标记 skipped，
不能升级为 Verified。
