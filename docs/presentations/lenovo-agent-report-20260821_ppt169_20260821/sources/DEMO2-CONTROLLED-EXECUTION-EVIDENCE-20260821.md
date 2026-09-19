# Demo 2 受控内部执行 Evidence（2026-08-21）

| 字段 | 内容 |
| --- | --- |
| Evidence ID | `DEMO2-CONTROLLED-EXECUTION-20260821` |
| Decision | [`DR-0015`](../decisions/DR-0015-mainstream-comparison-and-demo2-controlled-execution.md) |
| Scenario | [`SCENARIO-002`](../scenarios/SCENARIO-002-demo2-explainable-admission.md) |
| Status | `Limited Verified`（固定客户 A、单 API 进程、memory、真实模型受控内部执行） |
| Date | 2026-08-21 |
| Implementation commit | [`252f8d02725f341137f1580d4230003d2477ecca`](https://github.com/Dickey007s/lenovo_agent/commit/252f8d02725f341137f1580d4230003d2477ecca) |
| Pull request | [PR #22](https://github.com/Dickey007s/lenovo_agent/pull/22)（未在本 Evidence 中声明已合并） |

## 1. 结论与限定范围

在固定客户 A 经营汇报场景、项目生成的仿真文件、单个 FastAPI 进程和 memory store 内，Demo 2 已从“记录 Adaptive Swarm 路由”推进到真实受控内部执行：服务端创建执行 Snapshot，启动三个初始工作单元，依据文件中的收入口径冲突产生动态重排并增派第四个工作单元，形成 5 个共享工件版本，最后产生 `completed` 回执。四个工作单元均通过已配置的 `deepseek-v4-pro` 发起真实模型请求，并只在输出与服务端批准业务文本一致时采用模型结果。

该结论只证明固定工程纵切真实运行。它不证明通用 Adaptive Swarm、后台无人值守、跨进程恢复、真实 Connector、生产身份、多实例一致性、模型质量、成本/时延改善或用户价值。主流技术差异和用户交互价值仍是 `Design claim / Draft`。

## 2. 服务端事实链

| 阶段 | 服务端事实 | 用户可见投影 | 边界 |
| --- | --- | --- | --- |
| 路由已选 | `WorkItemSnapshot.selected_mode=adaptive_swarm`、`selection_receipt`、`execution_status=not_started` | 已记录本次方式，尚未启动 | 路由回执不是执行回执 |
| 启动 | `POST /v1/demo2/work-items/{work_item_id}/execution` 返回 202、`execution_id` 和 Snapshot | 协作已启动，显示受限资料范围 | 只允许固定客户 A 与 Adaptive Swarm；Owner、版本和幂等由服务端校验 |
| 初始并行 | 三个 `Demo2WorkerSpec` 与有序 `WORKER_STARTED/WORKER_COMPLETED` | 收入事实核对、项目风险提取、客户要求核对 | Worker 身份、来源、状态和依赖由服务端拥有；模型不拥有控制面 |
| 动态重排 | sequence 9 `DYNAMIC_REPLAN`，sequence 10 `WORKER_ADDED` | 解释为何因“确认收入/预测收入”冲突增派收入口径核验 | 当前是固定文件事实触发的确定性重排，不是通用调度学习 |
| 共享收敛 | `SharedArtifactVersion[]` 带版本、来源文档、digest 与状态 | 展示业务摘要、来源与工件状态 | 不展示 Prompt、思维链、Worker 对话或原始内部 ID |
| 完成 | sequence 15、`ExecutionReceipt.status=completed`、4 workers、5 artifacts、`external_side_effect=none` | 显示内部汇报工件包已完成，明确未触发外部动作 | 不表示邮件、CRM、OA、日历或任务系统已写入 |

执行读取与回放接口为 `GET /execution`、`GET /execution/events?after=` 和 `GET /execution/stream?after=`。SSE sequence 是时序事实；响应丢失或事件缺口时，前端必须重新 GET 完整 Snapshot 对账，不能依赖动画或本地计时器宣布完成。

状态协议以当前 Pydantic 契约和运行服务为准：启动前是 `WorkItemSnapshot.execution_status=not_started`；创建后当前 Runtime 的整轮 `Demo2ExecutionSnapshot.status` 可达 `queued/running/verifying/completed/failed`。Pydantic 枚举虽保留 Execution `cancelled` 与 `EXECUTION_CANCELLED`，但当前没有取消路由或写入该终态的服务转换，因此它只是协议兼容保留，不能列为已实现路径。单个 `Demo2WorkerSpec.status` 只允许 `queued/running/completed/failed/cancelled`，没有 Worker `verifying` 或 Demo 2 `waiting_input`；`EXECUTION_VERIFYING` 表示整轮正在核验最终共享工件，而不是某个 Worker 进入验证状态。

## 3. Live `deepseek-v4-pro` 两轮事实与证据等级

两轮记录的可复核等级不同。第一轮数字来自本轮交互式运行文字记录，仓库中没有对应的原始 JSON/manifest/log 工件，因此只能作为补充运行记录，不能与第二轮独立复核。第二轮由仓库内浏览器 manifest、执行 Snapshot 摘要、6 张截图及实际文件 SHA-256 共同支撑，是本 Evidence 的主要可复核运行证据。

### 3.1 第一轮模型运行（交互式运行记录，非独立仓库工件）

| 事实 | 观测值 |
| --- | --- |
| 整轮墙钟时间 | `8799 ms` |
| 模型输出采用 | `4 / 4` |
| 四个工作单元真实模型耗时 | `4956 / 4268 / 3590 / 3665 ms` |
| 模型 | `deepseek-v4-pro` |

这些数字仅来自本轮交互式运行文字记录，仓库内没有对应的原始 manifest、结构化日志或可独立重算工件；后续引用必须同时带上这一限定，不能把它写成与第二轮 manifest 同等级的可复核证据。整轮墙钟时间也不能用四个 Worker 耗时求和推导；工作单元并发运行，因此这里只分别保留整轮观测和每个模型请求观测。`4 / 4 model adopted` 只表示记录中四个响应通过严格业务文本校验并被采用，不证明模型质量或生产 SLA。

### 3.2 第二轮浏览器运行（主要可复核证据）

仓库内浏览器证据 manifest 记录四个工作单元均为 `path=language_model`、`model_called=true`、`model=deepseek-v4-pro`、`output_used=model`：

| 工作单元 | 触发 | 模型耗时 |
| --- | --- | --- |
| 收入事实核对 | `initial_plan` | `6200 ms` |
| 项目风险提取 | `initial_plan` | `5190 ms` |
| 客户要求核对 | `initial_plan` | `4450 ms` |
| 收入口径核验 | `dynamic_replan` | `3735 ms` |

该轮最终 Snapshot 为 `completed`，`last_event_sequence=15`，包含 4 个 Worker、5 个 Artifact；sequence 9 为重排，sequence 10 为增派，sequence 15 为完成。回执固定为 `external_side_effect=none`，摘要为“已完成四个受限工作单元并生成共享汇报工件包，未触发外部动作。”

## 4. 浏览器截图与哈希

截图清单来自 [`dr-0015-demo2-controlled-execution-manifest.json`](screenshots/dr-0015-demo2-controlled-execution-manifest.json)，采集时间 `2026-08-21T03:48:25.370Z`，浏览器为 Microsoft Edge 的 Playwright system channel。

| 状态 | 文件 | 尺寸 | SHA-256 |
| --- | --- | --- | --- |
| 已选择、未启动 | [`1440-selected-not-started`](screenshots/dr-0015-demo2-controlled-execution-1440-selected-not-started.png) | 1440 x 1000 | `014e7b10df4730f1a88c5182cccd89114675de585acdbf6ad8c10a67d9a17c56` |
| 运行中 | [`1440-running`](screenshots/dr-0015-demo2-controlled-execution-1440-running.png) | 1440 x 1000 | `8ad1a4a768036447dff465c4b81fabf26ee0d6e437f4a67cf8161948a3759428` |
| 动态重排 | [`1440-dynamic-replan`](screenshots/dr-0015-demo2-controlled-execution-1440-dynamic-replan.png) | 1440 x 1000 | `9614f2d6f4695f03295e1b9beb6f27553f1cffa0bcc34b1f94a03cbdab4ee54b` |
| 完成主视图 | [`1440-completed`](screenshots/dr-0015-demo2-controlled-execution-1440-completed.png) | 1440 x 1000 | `52d788b3a01085ffcb40c88880f5b4753648fc7110285952efcf8b2c4cccb8ec` |
| 完成回执 | [`1440-completed-receipt`](screenshots/dr-0015-demo2-controlled-execution-1440-completed-receipt.png) | 1440 x 1000 | `da5083b6c82830a989063d9e9916bab171aefeb1758d8655b42420c9ffff8ebf` |
| 移动端完成 | [`390-completed`](screenshots/dr-0015-demo2-controlled-execution-390-completed.png) | 390 x 3856 | `b441ab7b3ea8c3c26c7686e71c9f2e5e7170a2d16bc4e0fbe9715f2bc7ea8949` |

移动端 manifest 记录 `innerWidth=390`、`scrollWidth=390`、`overflow=false`。唯一控制台错误是缺少 `/favicon.ico` 的 404，评估为非阻塞，不影响本轮业务路径；该判断不等于没有其他未覆盖的视觉或可用性问题。

## 5. 自动化与静态检查

| 验证 | 本轮结果 |
| --- | --- |
| Python 全量 | `178 passed, 1 skipped in 6.31s` |
| 浏览器全量 | `41 passed (2.0m)` |
| Ruff | passed |
| 前端 lint | passed（3.16s） |
| Next.js build | passed（compile 2.4s / TypeScript 6.6s / static 579ms） |
| Governance | `4 passed in 0.05s` |
| Diff check | passed |

封口时长期服务仍运行在 Web `http://localhost:3000` 与 API `http://localhost:8010`；health 返回模型 `deepseek-v4-pro`、checkpoint `memory`、task store `memory`。这证明本轮运行配置和服务可达，不把 memory 后端写成持久化能力，也不把自动化通过写成用户研究或模型质量结论。

## 6. 必须保留的边界

- `X-User-Id` / `X-User-Roles` 仍是未签名的 P0 身份占位，生产必须替换为 SSO/JWT 与可信角色映射。
- Demo 2 Execution Store、锁、幂等结果、事件和 SSE 均为单 API 进程 memory；API 重启、跨进程恢复、多实例并发和分布式执行 lease 没有证据。
- 来源是 `demo-enterprise-data/customer-a/` 项目生成仿真文件，不是 Lenovo、真实客户、实时企业数据库或 Connector。
- 本轮没有调用真实邮件、CRM、OA、日历或任务系统；`external_side_effect=none` 是服务端回执事实。
- 模型只生成受限业务摘要和要点，服务端拥有身份、来源、依赖、状态、事件、工件版本、digest、验证和回执；Prompt、思维链和 Worker 内部对话不进入普通业务 UI。
- 当前动态重排由固定收入口径冲突触发；没有证明任意任务、任意冲突、预算耗尽、跨进程恢复或通用冲突解决。
- 没有目标用户研究、真实竞品对照实验、成本账单、质量基准或时延 SLA。官方竞品材料只支持能力/定位判断，不证明竞品做不到本方案。
