# USER-FEEDBACK-20260831：先固定 Demo 1/2 场景门，再扩展持久状态

| 字段 | 内容 |
| --- | --- |
| Source ID | `USER-FEEDBACK-20260831-DEMO1-DEMO2-FIXED-SCENARIO-HARDENING` |
| 类型 | Stakeholder 产品与研发推进授权 |
| 日期 | 2026-08-31，Asia/Shanghai |
| Owner | Office Agent 项目组 |

## 原始要求摘要

Stakeholder 确认继续推进项目，并接受以下顺序：先把 Demo 1/2 做成固定、可重复、
可对账的场景门，再进入 Task/WorkUnit 持久化、真实 PostgreSQL、真实 Provider 和
目标用户试用。继续保持既有分工：文档、调研、场景和 Evidence 由当前任务负责，
源码开发由既有开发任务中的 Luna 子 Agent 完成。

## 支持的决策

1. 当前优先级不是再增加 Agent 数量，而是证明已有跨 Run continuation、Topology
   Admission 和只读 Worker 收敛在固定正例、反例和失败注入下成立。
2. Demo 1 必须证明 parent 不变、child 只继承一条批准 Branch、来源重核范围精确。
3. Demo 2 必须同时有 adaptive 正例和 fixed-workflow 反例；Prompt 中出现“多 Agent”
   不能成为准入事实。
4. 固定场景自动化通过后，才决定是否进入独立 Task ledger、持久 WorkUnit 和
   Worker 局部恢复。

## 局限

这是单一 Stakeholder 的推进授权，不是目标用户研究、竞品实测或业务效果证明。
它不授权付费 Provider、生产 Connector、源文件修改或外部动作，也不能把确定性
Fixture 通过写成模型质量、数据库恢复或用户体验改善。
