# Agent Control Loop 三轮只读纵切证据

> Evidence ID：`AGENT-CONTROL-LOOP-BOUNDED-READONLY-20260825`
> 状态：`Limited Verified`
> 实现提交：`8364b1e403ce11c928683f28eb106ce218029315`
> PR：[#28](https://github.com/Dickey007s/lenovo_agent/pull/28)，当前为 open、未合并，基于 PR #27 的 FORTE 文件工作现场。

## 1. 证明范围

本证据只证明：在当前 `deepseek-v4-pro` 配置、FORTE 公开办公输入、单个 API
进程内存状态和只读边界下，用户能够自行选择文件并提交任意任务；服务端能够执行最多
三轮的 `Observe -> Plan -> Act(read-only) -> Verify -> Evidence Gate -> Commit`，
并把每轮、预算、证据缺口、模型采用状态和人工控制投影到前台。

它不证明生产级 Durable State、跨进程恢复、后台队列、多 Worker 自组织、真实文件写入、
真实 Connector、模型质量、用户价值或成本收益。

## 2. 场景与来源

- 用户场景：[`SCENARIO-009`](../scenarios/SCENARIO-009-agent-control-loop.md)。
- 决策：[`DR-0023`](../decisions/DR-0023-agent-control-loop.md)。
- 用户命名与交互要求：`USER-FEEDBACK-20260825-CONTROL-LOOP-16`、
  `USER-FEEDBACK-20260825-CONTROL-LOOP-NAMING-17`。
- 数据来源：FORTE 固定公开输入，运行中选择财务、人力、法务、研发交付四类 8 份文件；
  不是 Lenovo、真实客户资料或企业实时数据库。
- 原始运行摘要与截图哈希：
  [`dr-0023-agent-control-loop-live-run.json`](manifests/dr-0023-agent-control-loop-live-run.json)。

## 3. 后端事实

真实运行任务为：

> 比较财务、人力、法务和研发资料，找出相互矛盾或缺少依据的事项，分轮核对并给出下一步建议。

运行结果：

| 事实 | 结果 |
| --- | --- |
| 终态 | `completed` |
| 轮次 | 2 轮，第一轮 `next_round`，第二轮 `completed` |
| 文件 | 8 份允许文件，8 份形成可核对引用 |
| 模型调用 | 5 次，均计入服务端预算 |
| 总运行观测 | `71461 ms` |
| 有序事件 | 21 条，末事件 `loop_committed` |
| 外部动作 | `none` |
| 最终简报 | 完成 2 轮，只读核对 8 份允许资料，结论仍等待人工复核 |

第一轮第一次规划返回后，服务端拒绝了候选计划，并产生 sequence 5
`plan_validation_rejected`：

> 候选计划未通过服务端校验，未采用；正在进行预算内的受控重试。

第二次规划通过范围、工具、依赖和只读副作用校验后才被采用。这个事实证明“模型返回”
不等于“系统采用”；受控重试也消耗同一 `max_model_calls` 预算，不是隐藏的免费重试。

## 4. 前台影响

| 用户要知道什么 | 当前前台输出 | 服务端事实 |
| --- | --- | --- |
| 允许 Agent 看什么 | 8 份文件冻结为当前任务范围，运行中不可改 | `contract.allowed_file_refs`、`workspace_index` |
| Agent 正在做什么 | 当前轮次、读取/规划/分析/核对/证据门阶段 | `rounds[]`、named SSE |
| 模型是否真的调用 | 模型名、耗时、已采用/未采用 | `model_receipt`、`analysis_receipt` |
| 为什么继续 | 第一轮证据缺口、候选文件、服务端决定 | `evidence_gaps[]`、`next_step=next_round` |
| 我能否干预 | 暂停、继续、调整下一轮方向、结束并保留 | `ControlEvent`、expected version、幂等回执 |
| 最后得到了什么 | 只读简报、引用文件、未解决项、无外部动作 | `AgentControlLoopBrief`、`loop_committed` |

Prompt、思维链、原始 provider response、绝对路径、内部文件哈希和未经投影的失败原因
不进入普通业务 UI。

## 5. 截图

| 状态 | 证据 |
| --- | --- |
| 自由选文件、设置目标与预算 | [`ready desktop`](screenshots/dr-0023-agent-control-loop-ready-desktop.png) |
| 第一轮真实运行，输入被冻结 | [`round 1 running`](screenshots/dr-0023-agent-control-loop-round1-running-desktop.png) |
| 第一轮证据不足并触发第二轮 | [`evidence gate`](screenshots/dr-0023-agent-control-loop-evidence-gate-desktop.png) |
| 两轮完成与服务端轨迹 | [`completed desktop`](screenshots/dr-0023-agent-control-loop-completed-desktop.png) |
| 390px 完整工作现场 | [`completed mobile`](screenshots/dr-0023-agent-control-loop-completed-mobile.png) |
| 390px 可核对 Agent 路径 | [`trace mobile`](screenshots/dr-0023-agent-control-loop-trace-mobile.png) |

六张图片实际尺寸与 SHA-256 见 manifest。桌面 `scrollWidth=1440`，移动端
`scrollWidth=390`，本次浏览器运行未观察到业务 console error。

## 6. 自动化

| 检查 | 结果 |
| --- | --- |
| `uv run pytest -q` | `56 passed in 13.56s` |
| `uv run pytest -q tests/unit/test_harness_runtime.py` | `19 passed in 0.95s` |
| `uv run ruff check .` | passed |
| `pnpm --dir apps/web lint` | passed |
| `pnpm --dir apps/web build` | compile `1.826s`、TypeScript `3.1s`、static `617ms` |
| Harness Playwright | `9 passed in 21.7s` |
| `git diff --check` | passed；仅 Windows LF/CRLF 提示 |

自动化覆盖任意任务、跨目录文件选择、两轮循环、证据缺口、来源回开、模型计划拒绝后
一次受控修复、预算停止、pause/steer/resume/stop、幂等键、Owner、SSE 断线续订、
失败安全停止和 390px 无横向溢出。

## 7. 边界

1. Store 是单 API 进程 memory；API 重启会丢失 Run、Snapshot、Event 和控制状态。
2. 浏览器关闭不会让 UI 自动恢复到原 Run；当前没有历史任务选择入口。
3. pause/stop 在模型调用之间的安全点生效，不会中断已发出的模型请求。
4. deadline 用于阻止新模型调用，不是对在途 HTTP 请求的硬取消。
5. 第一版只核对引用是否来自允许文件；这不是语义真值、数值正确性或人工业务确认。
6. `Commit` 当前是内存中的只读 Brief，不是不可变 ArtifactVersion、TaskCommit 或持久化 checkpoint。
7. 一次 live 成功和工程自动化不能证明产品更易懂、工作效率提高或建议质量更好；这些仍需形成性用户研究。
