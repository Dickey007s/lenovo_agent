# DR-0009：把 Demo 1 从单次终态提交改为可恢复的渐进阶段

| 字段 | 内容 |
| --- | --- |
| Decision ID | `DR-0009` |
| Owner | Office Agent 项目组 |
| Date | 2026-08-17 |
| Status | `Verified`（限定工程范围；用户理解仍待验证） |
| Scope | Demo 1 固定 Fixture 的 Observe、Plan、Act、Verify 渐进状态、受控模型调用、阶段回看与恢复 |
| Scenario | [`SCENARIO-001`](../scenarios/SCENARIO-001-customer-a-durable-report.md) |
| Primary source | [`USER-FEEDBACK-20260817-02`](../sources/USER-FEEDBACK-20260817-02-demo1-progressive-stages.md) |

## 1. 场景与问题

客户经理启动“客户 A 经营汇报”后，需要知道系统正在读取什么、如何拆分三份交付物、目前生成了哪些候选材料，以及为什么最终停下来请求确认。现有实现把四个阶段放在一次同步 mutation 中，前台第一次收到的 Snapshot 已经是 `verify / waiting_input`；因此用户只能看到“前三步已经结束”的结论，不能理解过程，也无法在刷新后回看每一步的服务端事实。

完成条件不是播放一段前端动画，而是每个阶段都形成独立、持久、幂等的服务端 Snapshot 和事件。浏览器可以自动请求下一步，但只能展示服务端已经确认的阶段；刷新或断线后必须从当前 Snapshot 继续。

## 2. 决策

采用“服务端单阶段 mutation + 浏览器顺序协调”的 V0.1 纵切：

1. `start` 只把 Task 从 `ready / contract` 推进到 `running / observe`。
2. 新增幂等 `advance` mutation；每次只完成当前阶段并启动下一个阶段。
3. Observe 只解析服务端允许的固定来源并记录来源摘要；不调用模型。
4. Plan 使用当前配置的 `deepseek-v4-pro` 生成受限的三交付物工作包说明；只有交付物集合和面向用户文字都与服务端批准模板逐字段一致时才记录为 `model`，否则回退安全模板。
5. Act 使用同一模型生成受限的叙事草稿字段，并遵循相同的精确批准规则；工件身份、来源、lineage、金额、状态与 digest 仍由服务端确定。模型不可产生或覆盖这些字段。
6. Verify 由确定性代码重新计算验证报告与冲突；模型输出不能自证通过。
7. 每个 Snapshot 持久化阶段记录，包含阶段状态、面向用户的摘要、可显示详情、工件引用、生成来源和时间；不保存或展示思维链。
8. 模型不可用、超时或输出不合约时，允许使用明确标记为 `template_fallback` 的确定性模板继续固定 Demo；前台不得表述为“模型已完成”。

V0.1 不引入真正的后台调度器。只要浏览器保持打开，前端会在收到当前阶段的服务端确认后请求下一阶段；关闭浏览器后任务停在最后一个已持久化阶段，重新打开后继续。这比原先单次 mutation 可观察、可恢复，但不能对外称为无人值守后台长任务。

## 3. 前台交互影响

| 服务端阶段 | 用户首先看见什么 | 可执行动作与反馈 | 默认隐藏 |
| --- | --- | --- | --- |
| `ready / contract` | 任务目标、三份预期成果、一个“开始准备”动作 | 启动后等待服务端返回 Observe Snapshot | 版本、幂等键、预算内部计数 |
| `running / observe` | “正在读取本轮允许来源”与可读来源类别 | 可离开当前工作区；失败时重试当前阶段 | 原始 `fixture:`、查询参数、模型提示词 |
| `running / plan` | 三份材料的拆分结果和各自目标 | 已完成阶段可点击回看 | 模型推理、Worker 对话 |
| `running / act` | 候选材料逐步出现，明确“尚未核对” | 可打开当前候选工件 | 未验证内容不得使用成功绿或“已完成” |
| `verifying / verify` | 先显示核对过程；只有服务端产生冲突后才进入待决定 | 成功则继续，冲突则只展开阻塞分支 | 验证内部日志、完整 hash |
| `waiting_input` | 一个需要人的决定、原因、后果和唯一主动作 | 决策确认后继续服务端验证与 Commit | 两个已通过分支默认压缩，减少首屏负担 |
| `committed` | 三份成果、验证状态、回复仍未发送 | 查看成果或准备受治理动作 | TaskCommit 内部协议进入审计详情 |

阶段轨允许回看已完成阶段，但回看不改变 Task phase、不触发 control。默认选择始终跟随当前服务端阶段；用户主动回看后显示“正在查看已完成阶段”，并提供返回当前阶段。

## 4. 后端事实与协议

`TaskSnapshot.stage_records` 是阶段 UI 的唯一业务事实来源；客户端连接状态仍由浏览器传输状态产生，二者不得混为一谈。每个 `start/advance` 请求携带 `expected_task_version` 和 `idempotency_key`：

```text
ready/contract
  --start--> running/observe
  --advance--> running/plan
  --advance--> running/act
  --advance--> running/verify
  --advance--> waiting_input/verify 或 committed/commit
```

每次成功 mutation 恰好增加一个 Task version 并原子写入 Snapshot、阶段事件和该阶段新产生的 ArtifactVersion。相同 key 重放返回首次结果；旧版本返回 `409`。模型调用发生在 mutation 提交之前，提交时仍执行 expected-version CAS；如果期间版本变化，丢弃模型结果，不得覆盖更新后的 Task。

模型只返回严格结构化且与批准模板一致的业务文字；不一致内容不会进入阶段记录。以下事实永远由服务端生成或校验：Task/Branch/Artifact 身份、Owner、来源引用、phase/status、预算、验证、冲突、Commit、digest/state hash、风险、审批、Permit 与任何副作用 Action。固定渐进路径还要求完整 Demo 契约（包括预算与截止时间）一致，通用 Task 不能只复制标题和来源后进入这条演示序列。

## 5. 来源、验证与边界

| Source ID | 支持的判断 | 不能证明 |
| --- | --- | --- |
| `USER-FEEDBACK-20260817-02` | 当前直接跳到第 4 步且信息过载；应展示 1→2→3 的真实过程 | 新交互已降低认知负担 |
| `MEETING-DECK-0716-V2-01`、`SCRIPT-V5-202607` | Demo 1 目标是持续运行、分支管理与治理 Loop | 当前 Runtime 仍是浏览器协调的单 Task 纵切，不具备后台自治能力 |
| `REACT-ICLR-2023` | Observe/Reason/Act 交错组织任务轨迹的研究依据 | 持久协议、办公 UI 或本项目效果 |
| `LANGGRAPH-DURABLE-20260810` | checkpoint、状态更新和恢复的工程原则 | 本项目实现正确或生产可用 |
| `LLM-API-SMOKE-20260811` | 当前模型文本通路已连通 | Task 结构化 Plan/Act 的质量、稳定性或成本 |

完成本决策至少需要：阶段协议与 API 回归、幂等/409/失败回退、刷新恢复、真实 1→2→3→4 浏览器断言、移动端无溢出、模型结构化 smoke、截图和全量测试。目标用户理解仍需单独研究，在此之前只能称为工程代理验收。

## 6. 备选与拒绝原因

- 纯前端延时动画：拒绝。它不产生服务端事实，刷新后不可恢复，并会伪造进度。
- 继续一次性 start、只增加事件时间线：拒绝。事务提交前中间事件不可见，仍不能体验或恢复阶段。
- 所有阶段都调用模型：拒绝。来源读取、验证和提交需要确定性信任边界，额外 token 也不等于更可信。
- 本轮直接建设后台队列与多 Worker Runtime：暂缓。它扩大范围并延后用户反馈闭环；先验证单 Task 渐进协议和交互。

## 7. 当前封口事实（2026-08-17）

固定序列为 v1 create `ready / contract`，v2 start `running / observe`，四次 advance 分别落到 v3 `plan`、v4 `act`、v5 `verifying / verify`、v6 `waiting_input / verify`；v6 包含 5 个 ArtifactVersion、1 个 open Conflict、2 个 passed VerificationReport，`resolve_evidence` 后 v7 `committed / commit`。`stage_records` 是 UI 事实，旧 Snapshot 缺失时默认空数组。

同进程相同 advance key 由锁避免重复模型调用；跨实例只依赖 expected-version CAS/idempotency marker，没有分布式 LLM lease。预算只统计 steps、tool calls、runtime，不是 token 成本。Plan/Act 的 `deepseek-v4-pro` 严格 smoke 仅证明连通与响应契约，不证明生成质量。

实现提交 `13c9c13`；完整 Python 为 `138 passed, 1 skipped (3.14s)`，完整浏览器为 `35 passed (1.9m)`，渐进主路径连续三次为 `3 passed (29.5s)`，Ruff、前端 lint/build 与治理门槛通过。真实模型 smoke 中 Plan/Act 均返回批准模板并记录为 `model`；恶意 Plan 文本、修改预算或截止时间的伪 Demo 契约均由自动化回归拒绝。八张截图覆盖 Observe、Plan、Act 等待、Act 回看、Verify、Decision、移动长页与 committed。详细 hash 和边界见 [`DEMO1-PROGRESSIVE-STAGES-20260817`](../evidence/DEMO1-PROGRESSIVE-STAGES-EVIDENCE-20260817.md)。这只把协议与被测交互标为限定范围 `Verified`；“用户更容易理解”的假设仍是 Draft。
