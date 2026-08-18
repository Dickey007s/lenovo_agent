# Demo 1 渐进阶段证据

| 字段 | 内容 |
| --- | --- |
| Evidence ID | `DEMO1-PROGRESSIVE-STAGES-20260817` |
| Decision | [`DR-0009`](../decisions/DR-0009-progressive-demo1-stages.md) |
| Scenario | [`SCENARIO-001`](../scenarios/SCENARIO-001-customer-a-durable-report.md) |
| Status | `Verified`（限定工程范围） |
| Implementation | `13c9c13` |
| Pull request | [`#14`](https://github.com/Dickey007s/lenovo_agent/pull/14) |

## 1. 已证明的工程事实

- `start` 只进入 v2 Observe，不再一次返回 Verify 终态。
- 四次 `advance` 分别产生 v3 Plan、v4 Act、v5 Verify、v6 `waiting_input / verify`；v6 固定为 5 个 ArtifactVersion、1 个 open Conflict、2 个 passed VerificationReport，解决证据后 v7 committed。
- 每个阶段都形成独立 Task version、`stage_records` 和有序事件；相同幂等键重放不重复写入。
- Plan/Act 通过严格 Schema，并且只有与服务端批准模板逐字段一致的面向用户文字才记录为 `model`；当前运行配置使用 `deepseek-v4-pro`，模型失败或内容不合约时显式 `template_fallback`。恶意 Plan 中的思维链、内部 ID、`fixture:` 和状态不会进入阶段记录。完整 Demo 契约还校验预算与截止时间。身份、来源、金额、验证、冲突、Commit 和动作仍由服务端确定。
- 浏览器只按服务端 Snapshot 顺序协调下一阶段；刷新恢复、旧 Snapshot 防回退、阶段回看和移动端主路径已有自动化覆盖。
- Verify 进行中只显示核对进展；产生 open Conflict 后只展开阻塞材料，2 份已核对材料默认压缩。普通 DOM 不显示原始 `fixture:` 来源。

## 2. 运行验证

| 验证项 | 命令或证据 | 结果 |
| --- | --- | --- |
| Python 全量 | `uv run pytest -q` | `138 passed, 1 skipped in 3.14s` |
| Ruff | `uv run ruff check .` | passed |
| Frontend lint | `corepack.cmd pnpm --dir apps/web lint` | passed |
| Frontend build | `corepack.cmd pnpm --dir apps/web build` | passed |
| Browser E2E | `corepack.cmd pnpm --dir apps/web test:e2e` | `35 passed (1.9m)` |
| 渐进主路径稳定性 | `... test:e2e --grep "progressive Task Runtime" --repeat-each=3` | `3 passed (29.5s)` |
| 治理门槛 | `uv run pytest -q tests/unit/test_reporting_governance.py` | `4 passed` |
| 结构化模型 smoke | 当前配置 `deepseek-v4-pro`，`thinking=disabled` | Plan/Act 均返回 `origin=model` 且与服务端批准模板一致。只证明连通和响应契约，不证明质量、成本或 SLA |

模型 smoke 输出只保留非敏感摘要：

```json
{"model":"deepseek-v4-pro","plan_origin":"model","plan_matches_approved":true,"act_origin":"model","act_matches_approved":true,"last_error":null}
```

## 3. 视觉证据

| 文件 | 尺寸 | bytes | SHA-256 |
| --- | --- | ---: | --- |
| [`demo1-progressive-01-observe-desktop.png`](screenshots/demo1-progressive-01-observe-desktop.png) | `1440 x 900` | `103533` | `8AD2EF84D069622EC1BDAE7BAE9B1C49C88C3B6A7563BF5C14C220F79C39343D` |
| [`demo1-progressive-02-plan-desktop.png`](screenshots/demo1-progressive-02-plan-desktop.png) | `1440 x 900` | `97618` | `D15D9990404378253534F88901515B75DB9A3384181861280A0ACFCB946CF71B` |
| [`demo1-progressive-03-act-desktop.png`](screenshots/demo1-progressive-03-act-desktop.png) | `1440 x 900` | `90623` | `586153231E900F231AEC0216B523E24FC877048DE4CA2198178175A489F20A00` |
| [`demo1-progressive-03b-act-review-desktop.png`](screenshots/demo1-progressive-03b-act-review-desktop.png) | `1440 x 900` | `120103` | `6287FEEAD36BAB99B4BD867AA4EA82D02BF30152ADC8E83F8F0758396A17E15D` |
| [`demo1-progressive-04-verify-desktop.png`](screenshots/demo1-progressive-04-verify-desktop.png) | `1440 x 900` | `82556` | `93FFD48F0FF3BFFB0B29D1DD99708AA475AE3A8D7601421A8C18D34903118429` |
| [`demo1-progressive-05-decision-desktop.png`](screenshots/demo1-progressive-05-decision-desktop.png) | `1440 x 900` | `144706` | `CC446D0FD8A67163953FDF8F0346C01F92009A7A79AB0991872A2FA1C75D3647` |
| [`demo1-progressive-06-decision-mobile.png`](screenshots/demo1-progressive-06-decision-mobile.png) | `390 x 2383` | `125646` | `A517DBBA2B10B1B643C1480200228C3090E6D41D0E764D0B686310B614AEAC9D` |
| [`demo1-progressive-07-committed-desktop.png`](screenshots/demo1-progressive-07-committed-desktop.png) | `1440 x 900` | `140752` | `171AE633DC8B78E04136D2A5C94B6758A3DF7AAD6DA15BB2BE34DC3A8E92C0E4` |

这些截图证明被测视口中的阶段信息、候选回看、Verify 进展、决策压缩和终态成果没有明显重叠或横向溢出。它们不证明真实用户已经理解，也不证明 900ms 阶段停留是最佳节奏。

## 4. 当前边界

本证据只证明固定客户 A Fixture、单浏览器协调的渐进阶段。浏览器关闭后任务停在最后一个已持久化 Snapshot，当前没有后台 scheduler；跨 API 实例没有 LLM 调用 lease，可能产生重复供应商调用但 Store CAS 仍防重复提交。预算是 steps/tool calls/runtime，不是 token cost；未记录 provider token、attempt 或账单。它不证明真实 Connector、Adaptive Swarm、模型质量、生产稳定性或用户理解改善。至少 5 名目标用户的无引导形成性测试仍未运行。
