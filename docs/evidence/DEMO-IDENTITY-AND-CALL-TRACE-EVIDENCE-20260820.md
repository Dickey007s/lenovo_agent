# Demo 身份与调用轨迹证据（2026-08-20）

| 字段 | 内容 |
| --- | --- |
| Evidence ID | `DEMO-IDENTITY-AND-CALL-TRACE-EVIDENCE-20260820` |
| Decision | [`DR-0013`](../decisions/DR-0013-demo-identity-and-call-trace.md) |
| Status | `Verified`（限定当前 Demo 1/2/3 工程范围） |
| 日期 | 2026-08-20，Asia/Shanghai |
| 实现 commit | `5e3bc9c` |
| 文档主体 commit | `5e3bc9c`（本次元数据由后续封口提交回填） |
| PR URL | [#20](https://github.com/Dickey007s/lenovo_agent/pull/20) |

## 1. 场景与验证问题

目标用户是第一次查看 Office Agent 的业务负责人。验证目标是让用户在同一产品中看见 Demo 1/2/3 的业务身份，并能区分当前服务端事实是已运行、未调用、未执行还是待核对；只有模型路径显示“模型已调用”，而不是把界面上的技术名称、路由选择或模拟器能力误解为真实执行。

本 Evidence 只验证固定 Demo 路径的工程投影，不宣称真实用户已经理解或产生效率/信任提升。

## 2. 实际事实映射

| Demo | 前台投影 | 服务端事实 | 关键边界 |
| --- | --- | --- | --- |
| Demo 1：长任务与分支 | 各阶段的业务摘要、处理来源、模型是否调用、输出是否被采用和耗时 | `TaskSnapshot.stage_records[].processing`：`path/model_called/model/elapsed_ms/output_used`，以及 `status/generation_source` | 阶段完成显示“已运行”；`model_called=true` 才显示“模型已调用”；`output_used=model` 才是模型输出被采用；阶段动画、模型名和耗时不能单独证明调用成功；不证明后台无人值守 |
| Demo 2：工作组织与路由 | Admission、路由记录、Worker/Connector 未调用、执行尚未启动 | `WorkCockpitSnapshot`、`RouteSelectionReceipt.processing`：`path/model_called/elapsed_ms`，以及 `execution_status` | 当前规则路径为 `policy_engine` 且不调用模型；Receipt 表示路由规则已运行；selected 不等于 running；不证明 Worker、Connector、成本或时延效果 |
| Demo 3：风险与动作治理 | 风险策略、证据、人工决定、执行许可服务、受控演示工具和结果的业务步骤 | `RunSnapshot.status/control_plan/evidence/approvals/permit/tool_result/impact_preview/execution_receipt`，Run SSE/AuditEvent | 业务 UI 以“执行许可服务”“受控演示工具”为主，Permit/Gateway/Simulator 仅为二级技术元信息；`tool_result.status=succeeded` 才显示工具已运行，unknown 显示“工具结果待核对”；不等于真实外部写入 |

统一的是前台语义，不是新增后端 `call_trace[]`。Demo 1/2/3 分别读取既有处理字段或治理字段，缺少服务端事实时显示待核对，不由前端补造。

Demo 1 另有一次真实配置模型路径截图：新任务 v6 的 `Observe` 为 deterministic `0 ms`；`Plan` 使用 `deepseek-v4-pro`，`model_called=true`、`output_used=model`、`4469 ms`；`Act` 使用 `deepseek-v4-pro`，`model_called=true`、`output_used=model`、`5016 ms`；`Verify` 为 deterministic `0 ms`。这是一次本机 memory 路径的连通与处理来源证据，不是模型质量、token 成本或延迟 SLA 结论。

## 3. 验证矩阵

| 验证项 | 工程断言 | 结果 |
| --- | --- | --- |
| Demo 身份 | 三个 Demo 以业务名称和目标进入工作区/调用记录区域 | 通过，见截图 |
| Demo 1 处理来源 | `TaskStageRecord.processing` 驱动阶段已运行、模型已调用和模型采用/回退语义 | 通过，见聚焦 E2E 与截图 |
| Demo 2 处理来源 | `RouteSelectionReceipt.processing` 显示规则路径、模型未调用和本轮路由回执 | 通过，见聚焦 E2E 与截图 |
| Demo 2 未执行 | `execution_status=not_started` 时 Worker/Connector 不显示为已执行 | 通过，见聚焦 E2E 与截图 |
| Demo 3 治理来源 | `RunSnapshot` 治理字段驱动策略、证据、人工决定、执行许可服务和受控演示工具状态 | 通过，见聚焦 E2E 与截图 |
| 工具结果未知 | unknown 工具结果显示“工具结果待核对”，不写成未调用/未执行/成功/失败 | 通过，见聚焦 E2E |
| Demo3 身份切换 | proposal 或 Task-derived action 出现时全局切换到 Demo3/审计，避免仍停留在 Demo1/2 的身份 | 通过，见聚焦 E2E |
| TaskStageProcessing 一致性 | 确定性路径不能声称模型调用/模型输出；语言模型路径必须有模型调用和模型名 | 通过，见 Python 回归 |
| 审计隐藏边界 | 普通业务审计页只显示业务标签和服务端摘要；raw event/payload/trace、内部原值不进入普通展示 | 通过，包含在全量浏览器回归 |
| 响应式 | Demo 1/2/3 均保存桌面与 `390px` 移动长页；全局 Demo 导航在任务滚动后保持可见，Demo 3 移动调用链自然展开 | 通过，见截图；不等同于用户理解测试 |

## 4. 自动化与质量门槛

- Python 全量：`154 passed, 1 skipped in 4.32s`。
- 浏览器全量：`38 passed (2.3m)`。
- Ruff：通过。
- 前端 lint：通过。
- 前端 build：通过。
- 治理测试：`4 passed`。

## 5. 截图清单与校验

以下 hash 为当前工作树文件的 SHA-256；截图只证明被测布局/状态，不证明用户理解。

| 文件 | 尺寸 | 字节 | SHA-256 |
| --- | --- | ---: | --- |
| [`dr-0013-demo1-call-trace-1181.png`](screenshots/dr-0013-demo1-call-trace-1181.png) | `1181 x 900` | 177208 | `A89F08005BADCD8A5DAEA80FFE02F928A1A58213B4A4170EBB7E35D6E6C7705B` |
| [`dr-0013-demo1-call-trace-mobile-390.png`](screenshots/dr-0013-demo1-call-trace-mobile-390.png) | `390 x 3562` | 197942 | `7796489B3E42174C25DF5C4DAF30BEC84B5260B7295A746A946DC28BFEBFCB5B` |
| [`dr-0013-demo1-live-model-call-trace-1280.png`](screenshots/dr-0013-demo1-live-model-call-trace-1280.png) | `1280 x 720` | 144016 | `DE0BDE56EE62E53D7D8B0A9993C9F35752260C778055E1A68104B6BE40B165B6` |
| [`dr-0013-demo2-call-trace-desktop.png`](screenshots/dr-0013-demo2-call-trace-desktop.png) | `1280 x 720` | 167318 | `2EE9A61E5F6FE329957E928C1D4D899D11BB6595C123DCD912C29463B565E29E` |
| [`dr-0013-demo2-call-trace-mobile-390.png`](screenshots/dr-0013-demo2-call-trace-mobile-390.png) | `390 x 3355` | 209084 | `AF829EDFA908A50459920CA747F7FAC644FCFD80719036965A1043D21E691E30` |
| [`dr-0013-demo3-call-trace-1440.png`](screenshots/dr-0013-demo3-call-trace-1440.png) | `1440 x 900` | 221443 | `DB3C4F93D01CD479FF1C39F27C27A572022983EB3AC012AE3B1A1AEDE57AECC2` |
| [`dr-0013-demo3-call-trace-mobile-390.png`](screenshots/dr-0013-demo3-call-trace-mobile-390.png) | `390 x 2957` | 186934 | `7F27A54658B17D1E685C3764792FE57926DC61E7AB197DB6339C6C56ABC707E2` |

## 6. 来源与限制

来源包括用户反馈 [`USER-FEEDBACK-20260820-05`](../sources/USER-FEEDBACK-20260820-05-demo-identity-and-call-trace.md)、Demo 1/2/3 的既有决策与 Evidence、当前源码协议和本次自动化/截图运行结果。用户反馈支持“前端要看见 Demo1/2/3 且知道调用了什么”的问题定义；源码和测试支持限定工程事实；截图支持被测布局和状态；真实模型截图还支持本次单机 memory 路径确实记录了模型调用和耗时。

本 Evidence 不证明：真实用户理解、用户研究结论、模型质量、token 成本、延迟 SLA、真实 Connector/Worker、Adaptive Swarm 已运行、后台无人值守、生产身份、生产持久化、跨进程执行幂等/Permit replay、多实例或数据库恢复。`email_simulator`、`email.send`、`PERMIT_ISSUED`、Permit token/内容/permit_id/签名等原始技术值只留在 API/服务端审计或受控技术视图；普通业务 UI 以“执行许可服务”“受控演示工具”等业务词为主，Permit/Gateway/Simulator 仅为二级技术元信息。
