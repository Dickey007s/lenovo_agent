# DR-0013：Demo 身份导航与调用轨迹证据层

| 字段 | 内容 |
| --- | --- |
| Decision ID | `DR-0013` |
| Owner | Office Agent 项目组 |
| Date | 2026-08-20 |
| Status | `Verified`（限定当前 Demo 1/2/3 工程范围） |
| Scope | Demo 1/2/3 的业务身份、服务端处理来源投影、已运行/未调用/未执行边界和普通审计展示 |
| Depends on | `DR-0009`、`DR-0011`、`DR-0012`、`USER-FEEDBACK-20260820-05`、`UI_SERVER_FACT_MATRIX` |

## 1. 用户场景与完成条件

目标用户是第一次查看 Office Agent 演示的业务负责人。用户从邮件、任务或驾驶舱进入页面后，需要立即知道当前属于哪个 Demo、该 Demo 要证明什么，以及 Agent 当前真实调用了哪些服务、哪些没有调用、哪些动作尚未执行。当前工程已经把这些信息投影到三个 Demo 的业务工作区，但它不是新增的通用 `call_trace` 协议。

当前验证的完成条件是：

1. Demo 1/2/3 的工作区首屏能以产品级客户端信息架构说明身份和目标；当前状态副标题再从 Task/WorkCockpit/Run 事实投影；切换视图不重置 Task、Run、Artifact、Event 或 Conversation。
2. 调用来源直接投影现有服务端事实：Demo 1 使用 `TaskStageRecord.processing`，Demo 2 使用 `RouteSelectionReceipt.processing`，Demo 3 复用 `RunSnapshot` 的治理字段和结果字段。
3. 前台区分“已运行 / 未调用 / 未执行 / 待核对”；只有模型来源单独显示“模型已调用”，不把 Demo 2 的 selected 写成 running，也不把 Simulator 写成真实外部写入。
4. 普通业务 UI 只显示业务标签和服务端摘要；可以显示“Permit Service”“Permit 已签发/未签发”等业务级组件与指标，但 Prompt、CoT、原始 payload、密钥、Permit token/内容/permit_id/签名、trace/action/run 内部 ID、Worker 对话和底层日志不进入普通 DOM。

## 2. 三个 Demo 的业务身份与事实投影

| Demo | 用户看到的业务身份 | 当前事实来源 | 前台调用语义 | 必须隐藏或不得宣称 |
| --- | --- | --- | --- | --- |
| Demo 1：长任务与分支 | 客户 A 经营汇报任务 | 客户端 Demo 导航 + `TaskSnapshot.stage_records[]`，每项的 `processing`、`generation_source`、阶段状态和时间 | 阶段完成统一显示“已运行”；`processing.model_called=true` 额外显示“模型已调用”；`output_used=model` 才表示模型输出被采用；模板回退显示回退事实 | 阶段动画不是调用事实；旧 Snapshot 缺少阶段处理字段时显示“模型调用待核对”；不暗示浏览器关闭后后台无人值守 |
| Demo 2：工作组织与路由 | 智能工作驾驶舱 | `WorkCockpitSnapshot`、`RouteProfile`、`RouteSelectionReceipt.processing`、`execution_status` | Receipt 存在表示本轮路由已运行并记录；`processing.path=policy_engine` 且 `model_called=false` 表示未调用大模型；Worker、Connector 和外部动作保持未调用 | selected/admission 不等于 running；Fixture forecast 不等于实测成本或时延 |
| Demo 3：风险与动作治理 | 动作影响账本与治理回执 | `RunSnapshot.status/control_plan/evidence/approvals/permit/tool_result/impact_preview/execution_receipt` 及 Run SSE/AuditEvent | 治理链按 RunSnapshot 字段投影为已运行、等待、已签发或停止；业务词使用“执行许可服务”“受控演示工具”；有确定成功 `tool_result` 才显示工具已运行，unknown 显示“工具结果待核对” | Permit/Gateway/Simulator 只作为二级技术元信息，不等于真实 Connector 或真实业务系统写入 |

## 3. 已实现的前台投影，不新增通用协议

工程没有新增或假设通用 `call_trace[]`。前端为每个 Demo 把现有服务端事实翻译成同一组业务语义；统一的是显示语义，不是后端协议字段。

### 3.1 Demo 1：`TaskStageRecord.processing`

`TaskStageRecord.processing` 的事实字段为：

```text
path / model_called / model / elapsed_ms / output_used
```

前端同时读取 `stage_records[].status`、`generation_source`、`summary` 和时间戳。阶段完成统一显示“已运行”；Plan/Act 的 `processing.model_called=true` 才额外显示“模型已调用”，且 `output_used=model` 才表示模型输出被采用；模型被调用但输出不被采用时显示“模板回退”；Observe/Verify/Commit 的确定性路径显示“已运行 · 未调用大模型”。兼容旧数据时，v>1 且没有 `stage_records`，或旧 Plan/Act 记录缺少 `processing`，统一显示“模型调用待核对”，不得推断为未调用。

### 3.2 Demo 2：`RouteSelectionReceipt.processing`

`RouteSelectionReceipt.processing` 的事实字段为：

```text
path / model_called / elapsed_ms
```

当前实现固定为 `path=policy_engine`、`model_called=false`。Admission 和路由选择因此显示“规则引擎已运行、未调用大模型”；Receipt 不存在时显示等待用户记录本轮方式。`WorkItemSnapshot.execution_status` 仍是 `not_started` 时，Worker Runtime 与外部 Tool 的前台状态为未调用。

### 3.3 Demo 3：复用 `RunSnapshot` 治理字段

Demo 3 不新增调用轨迹字段，直接由治理状态投影：

```text
status / control_plan / evidence / approvals / permit / tool_result
impact_preview / execution_receipt
```

前端将风险策略、证据核对、人工决定、执行许可服务和受控演示工具分成步骤。通用完成状态显示“已运行”；只有模型来源显示“模型已调用”。步骤状态只从 `RunSnapshot` 和受控 Run 事件得出；`tool_result.status=succeeded` 才显示受控演示工具已运行，unknown 显示“工具结果待核对”，不可写成未调用或未执行。Permit/Gateway/Simulator 只在二级技术元信息中出现。普通审计时间线把事件投影为业务标签与摘要，原始事件字段仍留在 API/服务端审计边界。

## 4. 后端事实与显示边界

| 前台语义 | 真实依据 | 不得推断 |
| --- | --- | --- |
| 已运行 | 对应阶段、规则、治理步骤或工具已经由服务端 Snapshot/有序事件记录完成 | 不得由按钮点击、动画、模型名或耗时单独推断 |
| 模型已调用 | 对应 `TaskStageProcessing.model_called=true` 或 Conversation processing 的模型路径 | 不得把模型名、配置存在或等待动画单独写成已调用 |
| 未调用 | 服务端明确 `model_called=false`、未生成 Receipt/ToolResult，或当前步骤明确不需要该能力；不适用于旧 Demo 1 缺少 processing 的 Plan/Act | 不得把“没有错误”写成成功 |
| 未执行 | Demo 2 `execution_status=not_started`、Demo 3 治理链在执行前停止且没有工具结果 | 不得把 selected、执行许可服务或受控演示工具能力目录写成业务系统已改变 |
| 工具结果待核对 | Demo 3 存在 unknown/无法确认的工具结果或响应缺口 | 不得写成工具未调用、未执行、成功或失败，也不得自动重试副作用 |
| 待核对 | Snapshot 缺字段、事件/响应缺口、版本冲突或当前事实无法对账 | 不得自动重试副作用、复用旧结果或补造成功 |

普通业务 UI 隐藏 Prompt、CoT、raw `event_type/payload/trace`、密钥、Permit token/内容/permit_id/签名、内部 ID、Worker 对话、供应商原始响应和无决策价值的日志；“Permit Service”及“Permit 已签发/未签发”这类业务级状态可以展示。受控技术审计可以按权限读取原值，但不属于普通 Demo 展示。

## 5. 工程验证证据

本决策在固定 Demo 1/2/3 路径内标记为 `Verified`：

- Python 全量：`154 passed, 1 skipped in 4.32s`。
- 浏览器全量：`38 passed (2.3m)`。
- Ruff、前端 lint、build 通过；governance：`4 passed`。
- `TaskStageProcessing` 已增加跨字段一致性校验：确定性路径不得携带模型调用/模型输出；语言模型路径必须有观测到的模型调用和模型名，且不得宣称确定性输出。
- 最终截图及 SHA-256：
  - [`dr-0013-demo1-call-trace-1181.png`](../evidence/screenshots/dr-0013-demo1-call-trace-1181.png)，`1181 x 900`，`177208` bytes，`A89F08005BADCD8A5DAEA80FFE02F928A1A58213B4A4170EBB7E35D6E6C7705B`。
  - [`dr-0013-demo1-call-trace-mobile-390.png`](../evidence/screenshots/dr-0013-demo1-call-trace-mobile-390.png)，`390 x 3562`，`197942` bytes，`7796489B3E42174C25DF5C4DAF30BEC84B5260B7295A746A946DC28BFEBFCB5B`。
  - [`dr-0013-demo2-call-trace-desktop.png`](../evidence/screenshots/dr-0013-demo2-call-trace-desktop.png)，`1280 x 720`，`167318` bytes，`2EE9A61E5F6FE329957E928C1D4D899D11BB6595C123DCD912C29463B565E29E`。
  - [`dr-0013-demo2-call-trace-mobile-390.png`](../evidence/screenshots/dr-0013-demo2-call-trace-mobile-390.png)，`390 x 3355`，`209084` bytes，`AF829EDFA908A50459920CA747F7FAC644FCFD80719036965A1043D21E691E30`。
  - [`dr-0013-demo3-call-trace-1440.png`](../evidence/screenshots/dr-0013-demo3-call-trace-1440.png)，`1440 x 900`，`221443` bytes，`DB3C4F93D01CD479FF1C39F27C27A572022983EB3AC012AE3B1A1AEDE57AECC2`。
  - [`dr-0013-demo3-call-trace-mobile-390.png`](../evidence/screenshots/dr-0013-demo3-call-trace-mobile-390.png)，`390 x 2957`，`186934` bytes，`7F27A54658B17D1E685C3764792FE57926DC61E7AB197DB6339C6C56ABC707E2`。
  - [`dr-0013-demo1-live-model-call-trace-1280.png`](../evidence/screenshots/dr-0013-demo1-live-model-call-trace-1280.png)，`1280 x 720`，`144016` bytes，`DE0BDE56EE62E53D7D8B0A9993C9F35752260C778055E1A68104B6BE40B165B6`；一次本机 memory 运行记录 Observe/Verify deterministic `0 ms`，Plan/Act 使用 `deepseek-v4-pro`，分别 `4469 ms`、`5016 ms`，且 `model_called=true/output_used=model`；全局 Demo 导航在滚动后仍保留当前 Demo 与切换入口。

详细测试、截图和边界见 [`DEMO-IDENTITY-AND-CALL-TRACE-EVIDENCE-20260820`](../evidence/DEMO-IDENTITY-AND-CALL-TRACE-EVIDENCE-20260820.md)。真实模型截图只证明单次连通与处理来源，不证明模型质量、token 成本或 SLA。实现与文档主体提交为 `5e3bc9c`，对应 [PR #20](https://github.com/Dickey007s/lenovo_agent/pull/20)。

## 6. 来源与局限

| Source ID | 支持判断 | 局限 |
| --- | --- | --- |
| `USER-FEEDBACK-20260820-05-DEMO-IDENTITY-CALL-TRACE` | 用户要求前端同时看见 Demo 1/2/3 并知道调用了什么 | 单一 Stakeholder 反馈，不是用户研究 |
| `USER-FEEDBACK-20260820-04` | 支持区分确定性路径、模型调用、路由记录和真实等待 | 不证明增加等待或显示处理来源能改善体验 |
| `HAI-GUIDELINES-CHI2019` / `GOOGLE-PAIR-FEEDBACK-CONTROL-2021` | 支持反馈能力边界、状态和用户控制 | 通用设计指南，不定义本项目协议或效果 |
| `DR-0009` / `DR-0011` / `DR-0012` | 提供三个 Demo 的既有服务端事实与边界 | 历史决策不能替代本次统一前台投影证据 |
| `DEMO-IDENTITY-AND-CALL-TRACE-EVIDENCE-20260820` | 提供当前代码、自动化和截图的限定工程证据 | 截图和自动化不证明真实用户理解 |

## 7. 当前边界

Verified 仅覆盖固定 Demo 场景、客户端产品级 Demo 导航、当前被测桌面/移动布局和现有服务端事实投影。它不证明真实用户理解、真实 Connector/Worker、Adaptive Swarm 已执行、后台无人值守、生产身份、生产持久化、跨进程执行幂等/Permit replay、多实例或数据库恢复。没有服务端事实时，UI 必须显示“待核对”，不能由统一文案或本地状态猜测。
