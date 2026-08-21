# DR-0015：从主流 Agent 对比推进到 Demo 2 受控执行

| 字段 | 内容 |
| --- | --- |
| Decision ID | `DR-0015` |
| Owner | Office Agent 项目组 |
| Date | 2026-08-21 |
| Status | `Limited Verified`（仅固定客户 A、单 API 进程、memory、真实模型受控内部执行）；技术差异与用户价值仍为 `Design claim / Draft` |
| Scope | 汇报用技术对比、八模块缺口，以及 Demo 2 从 Admission 到无外部副作用的受控内部执行纵切 |
| Depends on | `DR-0008`、`DR-0011`、`DR-0012`、`DR-0013`、`docs/research/COMPETITOR-RESEARCH-OPENCLAW-CODEX-CLAUDE-CODE-20260821.md` |

## 1. 场景与问题

目标用户是同时处理客户、项目和内部流程的销售负责人或项目负责人。用户打开今日工作驾驶舱后，已有四项工作需要处理：客户 A 经营汇报、供应商邮件回复、周报格式统一和报销异常核查。第一纵切只能解释工作优先级和记录本次路由；本轮又为固定客户 A 落地了受控内部执行，使用户能区分“已选方式”“运行中”“因事实冲突增派工作单元”和“内部工件包已完成”。

本决策把 Demo 2 分成两个诚实的阶段：第一阶段是 Admission/route preview；第二阶段只在用户确认 Adaptive Swarm 后创建有边界的 `Demo2ExecutionSnapshot`，读取限定演示资料，生成 `SharedArtifactVersion`，按有序 `SwarmEvent` 显示 Worker、重排、验证和汇总。不得把外部邮件、CRM、日历写入混入 Demo 2，外部副作用继续交由 Demo 3 Action Gate。

当前已满足的限定完成条件是：用户能看见为什么选择这种组织方式，能确认并启动一次固定范围执行，能看到服务端拥有的 4 个 Worker、5 个 Artifact、有序事件、动态增派和最终回执；前端没有根据动画或固定 sleep 自行宣布完成。用户手动解决任意冲突、预算耗尽控制、跨进程恢复和通用工作单元编排仍为 Draft。

关键异常路径包括来源校验失败/运行中变化、Worker 失败、重复启动、版本过期、SSE 断线和执行结果未知。当前实现会对来源异常 fail closed、对 Worker 失败结束整轮并取消未完成兄弟，对 Owner/版本/幂等冲突返回确定性错误；跨进程恢复、预算耗尽和任意局部分支接管仍待实现与验证。

## 2. 技术对比结论

官方材料显示 OpenClaw、Codex、Claude Code 已覆盖多 Agent/子 Agent、后台任务、权限或 sandbox、会话/任务恢复和开发者可观察性。因此“支持多 Agent”“支持后台”“有人工确认”不再单独构成 Office Agent 创新。更稳妥的差异主张是：Office Agent 把企业业务对象、来源版本、共享工件、语义动作和实际影响反馈纳入统一前后端协议。

| 差异层 | 主流方案公开能力（官方材料） | Office Agent 目标差异 | 对用户交互的影响 | 当前状态 |
| --- | --- | --- | --- | --- |
| 执行中心 | Gateway、代码仓库/终端、当前目录和 session 是主要执行中心 | 以 Task/Branch/Artifact/ControlEvent 组织业务工作 | 用户从“命令/线程进度”转向“哪项业务材料正在处理、处于哪一步” | Draft |
| 事实与版本 | session、transcript、diff、worktree 或任务记录 | 每个建议绑定业务对象、来源文档/字段、版本和验证状态 | 冲突卡可解释“旧事实是什么、当前操作要写什么、为何暂停” | Draft；Demo 1 固定路径已有限定证据 |
| 多 Agent | 独立 workspace/session、并行 threads、foreground/background subagents | Admission 后动态 Worker 只能读取限定来源，并把结果写入共享工件版本 | 用户看见工作单元、依赖、重排和已验证汇总，而不是 Agent 头像墙 | 固定客户 A 纵切 `Limited Verified`；通用化 Draft |
| 动作治理 | 命令/工具权限、sandbox、host approval 或 permission mode | ActionSpec 绑定 ArtifactVersion、Evidence、Risk、Approval、Permit 和目标影响 | 用户确认“会改变/会重新核对/保持不变/不会发生”，而不是只批准命令 | Demo 3 固定路径限定范围 Verified；通用化 Draft |
| 影响反馈 | 主要围绕 diff、tool、command、task/session 可观察性 | 双时态 `impact_preview → execution_receipt`，预演与实际回执严格分开 | 提交前知道后果，提交后只看到服务端真正发生的变化；未知结果进入待核对 | Demo 1/2/3 各有固定纵切；统一跨 Demo Draft |
| 失败与恢复 | session resume、rewind、fork、cron/task state 等产品形态 | 版本过期、源改变、证据冲突和响应未知均 fail closed，保留草稿和已提交工件 | 用户知道该重新核对什么，恢复不会静默覆盖新输入 | Draft |

上述对比只来自官方文档/仓库/博客的能力与定位描述，不是竞品实测；不能据此说 OpenClaw、Codex 或 Claude Code 做不到业务治理，也不能宣称 Office Agent 已取得用户效果。

## 3. Office Agent 的四个差异支柱

1. **业务事实**：模型只提出自然语言、ArtifactDraft 或 ActionCandidate；身份、来源、字段事实、风险和状态由服务端拥有。
2. **共享工件收敛**：Worker 不通过对话转述交接，而把带来源、版本、digest 和验证状态的 `SharedArtifactVersion` 写入共享空间；冲突只影响相关分支。
3. **语义动作治理**：治理对象不是“允许执行某条命令”，而是“基于哪个业务工件、向哪个目标、改变什么字段、风险和证据是否满足”。
4. **双时态影响反馈**：提交前由服务端 `impact_preview` 说明将改变/重核/保持/不发生；提交后由 `execution_receipt` 说明实际发生，二者不能互相冒充。

这四项作为“相对主流方案的差异”和“能改善用户理解/效率”的判断仍是设计主张。Demo 2 固定纵切已经为业务事实、共享工件和内部执行回执提供工程证据，但不能把实现存在直接推导为新颖性、竞品缺失或用户效果。

## 4. Demo 2 当前状态机（Limited Verified）

```text
待决定
  → 用户确认本次路由（RouteSelectionReceipt，仍 not_started）
  → 用户启动协作（Demo2ExecutionSnapshot）
  → EXECUTION_STARTED
  → 三个初始 WORKER_STARTED / WORKER_COMPLETED
  → SharedArtifactVersion
  → DYNAMIC_REPLAN（seq 9）
  → WORKER_ADDED（seq 10，收入口径核验）
  → EXECUTION_VERIFYING / ARTIFACT_VERIFIED
  → EXECUTION_COMPLETED（seq 15）
  → ExecutionReceipt(external_side_effect=none)
```

首个受控执行包使用客户 A 经营汇报：收入事实核对、项目风险提取、客户要求核对三个初始工作单元，以及由收入口径冲突确定性增派的收入口径核验。资料范围仅来自项目生成的仿真文件，外部 Connector 不调用。模型只生成受限业务摘要/要点；服务端拥有 Worker 身份、来源、依赖、状态、事件、工件版本/digest 和完成回执。普通 UI 不暴露 Prompt、思维链、Worker 对话或原始内部 ID。

## 5. UI—后端事实矩阵

| 前台状态 | 用户看到/可做什么 | 权威后端事实 | 事件/版本/权限 | 状态 |
| --- | --- | --- | --- | --- |
| 推荐协作方式 | 看六类 Admission 依据和工作组织预演；改选或暂不确认 | `WorkCockpitSnapshot`、`RouteProfile.impact_preview` | `cockpit_version` + `expected_version`；仅 Owner 可选 | 限定范围 Verified |
| 已确认本次协作 | 看“本次已选择”，知道还未产生内部执行结果；可启动 | `WorkItemSnapshot.selection_receipt/execution_id/execution_status` | 选择回执幂等；启动使用 `expected_version + idempotency_key` | 限定范围 Verified |
| 协作已启动 | 看三个初始业务工作单元、状态和依赖 | `Demo2ExecutionSnapshot.workers/events` | `EXECUTION_STARTED/WORKER_STARTED` 单调 sequence；仅 Owner | 限定范围 Verified |
| 处理中 | 看每个工作单元阶段、模型是否真实调用、耗时和共享工件；不看原始日志 | `workers[].processing`、`SharedArtifactVersion[]` | GET Snapshot + SSE；Artifact version/digest | 限定范围 Verified |
| 动态重排 | 看服务端为什么增派收入口径核验 | `SwarmEvent.details` + 新 `Demo2WorkerSpec` | seq 9 `DYNAMIC_REPLAN`、seq 10 `WORKER_ADDED` | 固定冲突触发 Limited Verified；任意调度 Draft |
| 已验证汇总 | 看 5 个共享工件、来源和完成状态 | `SharedArtifactVersion[]` + `ExecutionReceipt` | `ARTIFACT_VERIFIED`、seq 15 `EXECUTION_COMPLETED` | 限定范围 Verified |
| 外部动作边界 | 明确“未触发外部动作”，需要另行进入 Demo 3 | `ExecutionReceipt.external_side_effect=none` | 内部完成不触发外部 Connector | 限定范围 Verified |
| 失败/恢复 | 来源异常或 Worker 失败时看终态；断线后 GET 对账 | failed Snapshot/Event；当前 memory backend | 单进程 Owner/幂等/版本隔离；跨进程无恢复 | 部分自动化；生产恢复 Draft |

前端不得通过 Worker 数量、动画、客户端计时器、模型名或 `200 OK` 自行推断状态；缺失 Snapshot/事件/receipt 时显示“状态待核对”。

## 6. 八个常驻 Runtime 模块的成熟度与缺口

| 模块 | 当前成熟度（只陈述已有边界） | 下一步缺口 | 汇报口径 |
| --- | --- | --- | --- |
| Task Contract | Demo 1 固定客户 A 有严格契约 | 通用模板、修改/取消、Demo 2 Worker 子契约 | 固定纵切已有；通用能力 Draft |
| Durable Task State | Task Snapshot/Event/Artifact/Commit 有 PostgreSQL 顺序恢复证据；Demo 2 Execution Snapshot/Event 为 memory | Demo 2 跨进程恢复、并发和事件缺口回放 | 不能宣称全系统长期恢复 |
| Context State Manager | 有 `trusted_context`、`workspace_context`、来源引用；Demo 2 Worker 读取固定 allowlisted 文件事实 | 通用最小权限投影、跨 Worker 版本隔离、预算化上下文 | 固定来源 Limited Verified；通用 Draft |
| Execution Loop | Demo 1 有受限阶段循环；Demo 2 有固定执行、并行 Worker、重排、验证和完成事件 | 后台队列、暂停/恢复、预算耗尽和任意重规划 | 固定 Demo 2 单进程 Limited Verified |
| Capability Runtime | Tool Gateway + 5 个 Simulator；Demo 2 有受限模型 Worker 生命周期 | 真实 Connector、沙箱、资源账本和跨进程 lease | 模型 Worker 固定纵切 Limited Verified；生产 Draft |
| Evidence & Quality Verifier | 固定来源、Conflict、VerificationReport 和 Action Evidence | 跨工件质量规则、真实来源解析、可扩展 Resolver | 固定场景 Verified，通用 Draft |
| Control Policy | Risk/Policy/ControlPlan 与固定 Task 控制状态；Demo 2 固定事实冲突触发增派 | 通用 Worker 降级、停止、预算与重排策略 | 固定触发 Limited Verified；通用 Draft |
| Trace & Checkpoints | TaskEvent、ArtifactVersion、Commit、Audit SSE、PostgreSQL checkpoint；Demo 2 有 memory Snapshot/SSE/receipt | Demo 2 持久化、统一业务 Trace、跨域回放 | 单进程执行 Trace Limited Verified |

## 7. 下一轮研究与验证计划

1. 先固定同一客户 A 任务的四种路由对照：Tool Call、Single Agent、Fixed Workflow、Adaptive Swarm；记录质量、时延、规则预算、人工确认负担和异常率，不能只比较 Worker 数量。
2. 把当前固定冲突触发的 Demo 2 执行扩展为可验证的失败/预算/局部暂停路径，并评估 PostgreSQL/outbox/后台队列；未完成前保持 Draft。
3. 补至少 5 人无引导理解测试：用户能否说出当前谁在做什么、为什么暂停、确认后改变什么、哪些事情不会发生。
4. 只在内部协作纵切稳定后，把已验证共享工件桥接到 Demo 3 Action Gate；不让 Demo 2 直接调用外部 Connector。

## 8. 决策边界

- 官方材料是能力/定位来源，不是竞品实测；不要写“竞品没有/做不到”。
- 本 DR 的固定客户 A、单 API 进程、memory、真实模型受控内部执行以 [`DEMO2-CONTROLLED-EXECUTION-20260821`](../evidence/DEMO2-CONTROLLED-EXECUTION-EVIDENCE-20260821.md) 为 `Limited Verified`；跨进程恢复、真实 Connector、通用调度、成本/质量效果和用户研究不得写入“已实现”。
- “相对主流方案更创新”“用户更容易理解”“效率/质量提升”等结论仍是 `Design claim / Draft`。官方材料不是竞品实测，不能说竞品做不到。
- Sol 负责本轮规划、Luna 负责具体执行是协作编排偏好，不进入用户可见产品协议，不作为模型效果结论。
