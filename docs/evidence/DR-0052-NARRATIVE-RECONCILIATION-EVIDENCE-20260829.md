# DR-0052 对账能力证据记录

- 状态：Limited Verified（真实 Provider + 便携 PostgreSQL 单 Run 已验证；不代表语义质量或用户体验）
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

## 真实纵切

- Owner：`tc15-narrative-reconciliation-20260829`
- Run：`harness:e29ba8fee2134e59a7e4519a54a76d9c`
- 服务：`deepseek-v4-pro`，PostgreSQL `127.0.0.1:55432/office_agent`
- 模型：Planner/Analyst 均 `called=true`；Analyst 返回但 `output_used=false`
- 对账：`status=contradictory`、`authority=deterministic_outcome`、`model_disposition=rejected`
- 冲突：`unsupported_solution_claim`
- 成果：2 个 CSV Artifact、1 个通过的 EffectReceipt；下载大小与独立内容校验均通过，212/212 行、87 个组合、P0/P1/P2/P3/P4 为 25/40/14/6/2
- 重启：API 重启后同一 Run 保持 `completed`、2 个 Artifact、1 个 EffectReceipt、对账状态和 `analysis_output_used=false`；详见两个 live manifest

## 尚待执行

真实运行只能证明该次模型说明与结构化成果的一致性，不证明语义全面、方案有效或用户体验改善；当前仍缺真实用户研究、生产写入、外部动作和多实例高可用证据。
