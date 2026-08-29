# DR-0052 对账能力证据记录

- 状态：实现与离线门已验证；真实 Provider/PostgreSQL 纵切待主任务在授权预算内执行
- 日期：2026-08-29
- 决策：`DR-0052-authoritative-outcome-and-narrative-reconciliation.md`
- 场景：`SCENARIO-037`

## 已验证

1. 服务端从通过校验的 `EffectReceipt` 生成紧凑 `verified_effect_context`，不扩大原始文件预览，也不向前台泄露内部摘要细节。
2. 模型返回后，Runtime 对完整覆盖、计数、优先级、未批准方案和重复已完成工作进行对账；`consistent` 采用，`partial` 仅作补充，`contradictory/stale` 拒绝。
3. 被拒说明不进入公共当前 `Result`、`Finding`、`Follow-up`、逻辑 Brief 或 `TaskCommit`；已通过 Artifact/EffectReceipt 保留。
4. 没有确定性成果的普通研究任务保持 `authority=model_only` 与 `review_required=true`，不会伪造确定性结论。
5. 单元、契约和既有场景回归门通过：`uv run pytest -q tests/unit`（366 passed）；目标 Ruff、前端 lint 和生产 build 通过。
6. 1440px 与 390px 的拒绝态截图已留存，前台只显示一个当前结论，冲突详情默认折叠。

## 历史问题复现

TC-15 历史 Run `harness:731c429f82a941438b838fa8982699fd` 的确定性成果为 212/212 行、87 个组合、P0/P1/P2/P3/P4 为 25/40/14/6/2；模型说明却声称只覆盖 60 行、将 P0 改写为 P1，并要求再次统计全部 212 行。该基线只作为脱敏回归输入，不修改旧 Run、旧 Evidence 或旧 manifest。

## 尚待执行

本记录不冒充真实 Provider 或 PostgreSQL 证据。主任务需在授权预算内启动新的 `deepseek-v4-pro` + PostgreSQL Run，复读 Snapshot 后补充 Run ID、Owner、对账状态、冲突类型、Artifact/Effect、重启一致性和最终 live manifest。真实运行只能证明该次模型说明与结构化成果的一致性，不证明语义全面、方案有效或用户体验改善。
