# 主流 Agent 方案对比研究：OpenClaw、Codex、Claude Code

| 字段 | 内容 |
| --- | --- |
| 记录日期 | 2026-08-21（Asia/Shanghai） |
| 研究范围 | OpenClaw、OpenAI Codex、Anthropic Claude Code；补充 LangGraph 作为运行时参照 |
| 来源约束 | 仅使用官方文档、官方仓库、官方博客或官方帮助中心 |
| 研究目的 | 为 Office Agent 汇报中的技术对比、场景来源、交互影响和 Demo 2 执行设计提供可追溯依据 |
| 证据边界 | “官方文档未提及”只表示本轮检索范围内未见该承诺，不等于功能绝对不存在；不能把产品定位差异写成效果或用户研究结论 |
| 实现跟进 | 本研究提出的 Demo 2 纵切随后已在固定客户 A、单 API 进程 memory、真实模型且无外部动作范围内完成 `Limited Verified`；见 `DR-0015` 与对应 Evidence。差异与用户价值主张仍为 Draft |

## 1. 先给结论

三类主流方案已经覆盖了很多“Agent 能做什么”的能力：工具调用、文件/终端操作、权限控制、子 Agent、后台任务、会话恢复和开发者可观察性。因此 Office Agent 不应把“有多 Agent”“有审批”“能后台运行”单独作为创新点。

真正值得形成差异的方向是：把 Agent 放进企业业务对象和业务事实之间，而不是只把它当作终端/代码工作流；把模型建议、业务证据、版本冲突、风险控制和实际影响做成一条可验证的前后端协议；让用户在业务界面看到“当前正在改变什么、会重新核对什么、保持什么、不会发生什么”，并且这些状态都来自服务端 Snapshot、Artifact 或有序 ControlEvent。

对 Demo 2 的直接结论是：“推荐自适应协作群组但 execution_status=not_started”只能证明 Admission/路由选择，不足以证明 PPT 中的“复杂任务的蜂群协作与动态调度”。研究之后，项目已在固定客户 A、单 API 进程 memory 内实现受控内部执行：用户独立启动后创建受限 Worker、读取项目仿真资料、生成共享工件并暴露有序重排/验证/完成事件；外部邮件、CRM、日历写入仍交给 Demo 3 的 Action Gate。该实现不把研究差异主张升级为竞品或用户效果结论。

## 2. 官方来源台账

以下链接均于 2026-08-21 访问。每一条同时记录它支持的判断和局限，不能只在 PPT 中列产品名称。

| Source ID | 类型 | 精确官方引用 | 支持的判断 | 局限 |
| --- | --- | --- | --- | --- |
| `OPENCLAW-HOME-20260821` | 官方文档 | [OpenClaw Docs](https://docs.openclaw.ai/)；首页的 What is OpenClaw / How it works | OpenClaw 是自托管 Gateway，把多个消息渠道、Agent、CLI、Web UI 和节点接到一个 Gateway；Gateway 是 session、routing、channel connection 的事实中心 | 产品是个人/开发者自托管网关，不能直接证明企业业务治理或用户效果 |
| `OPENCLAW-RUNTIME-20260821` | 官方文档 | [Agent runtime architecture](https://docs.openclaw.ai/agent-runtime-architecture) | 官方 runtime 包含 attempt loop、model/provider wiring、compaction、transcript/session wiring、tool policy 和 host/sandbox 工具 | 这是运行时所有权和目录结构，不等于每个业务工作流都拥有可审计的业务状态机 |
| `OPENCLAW-MULTI-20260821` | 官方仓库文档 | [Multi-agent concepts](https://github.com/openclaw/openclaw/blob/main/docs/concepts/multi-agent.md) | 每个 Agent 可有独立 workspace、身份规则、agentDir 和 session store；可以按 Agent/workspace/sender 做路由隔离 | 独立 Agent/workspace 说明隔离与路由，不等于共享业务 Artifact 的版本、证据和合并协议 |
| `OPENCLAW-BACKGROUND-20260821` | 官方文档 | [Automation](https://docs.openclaw.ai/automation)；[Cron jobs](https://docs.openclaw.ai/automation/cron-jobs) | OpenClaw 有 background task ledger、scheduler、hooks、task flow；cron 持久化 job、runtime state 和 run history，Gateway 重启后保留调度 | 后台任务 ledger/cron 证明任务可跟踪与调度，不证明企业业务对象被正确更新 |
| `OPENCLAW-SESSION-20260821` | 官方文档 | [Session management deep dive](https://docs.openclaw.ai/reference/session-management-compaction)；[Session tools](https://docs.openclaw.ai/session-tool) | per-agent SQLite 存 session rows 和 append-only transcript；`sessions_spawn` 为隔离子 Agent session，并可在任务完成后回报 | 持久化的是 Agent session/transcript；官方说明 multi-user ownership 是 usability，不是工具、凭据和文件的安全边界 |
| `OPENCLAW-PERM-20260821` | 官方文档 | [Exec approvals](https://docs.openclaw.ai/tools/exec-approvals)；[Security](https://docs.openclaw.ai/gateway/security)；[Sandboxing](https://docs.openclaw.ai/sandboxing) | Exec 要经过 tool policy、host approval、allowlist/ask/full 等控制；sandbox 通过 workspaceAccess、隔离和节点配对约束执行范围；审批请求绑定 canonical command context | 它是通用命令/主机权限模型；本轮材料没有看到 Task/Artifact/业务字段/影响账本这种业务语义协议 |
| `CODEX-CLI-20260821` | 官方帮助/文档 | [Codex CLI](https://learn.chatgpt.com/docs/codex/cli)；[OpenAI Codex repository](https://github.com/openai/codex) | Codex CLI 在项目目录中形成“读文件→规划→编辑→运行工具→检查 diff”的终端循环，可交互或 `codex exec` 用于脚本/CI；支持权限、sandbox、skills/plugins、cloud handoff | 主要叙事是代码仓库和终端工程循环，不能把代码 diff、命令审批等同于企业业务决策治理 |
| `CODEX-APP-20260821` | 官方博客 | [Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/) | Codex App 支持多个 agent thread 并行、项目分组、worktree 隔离、diff review、skills、后台 Automations 和 review queue；默认限制工作目录并对 elevated command 请求权限 | 多 Agent 的隔离副本和 review queue 很接近 Demo 2 的执行体验，但核心对象仍是 coding task/worktree/diff，不是企业业务 Artifact/证据冲突 |
| `CODEX-LONG-RUN-20260821` | 官方博客 | [Codex for (almost) everything](https://openai.com/index/codex-for-almost-everything/) | Codex 可以复用 conversation thread，按计划唤醒并跨天/周继续任务；summary pane 可追踪 plans、sources、artifacts；memory 和外部工具上下文用于提出下一步工作 | 博客描述的是产品能力方向和示例，不提供 Office Agent 业务场景的运行证据或用户研究 |
| `CLAUDE-WORKS-20260821` | 官方文档 | [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works) | 每个 conversation 是绑定当前目录的 session；本地 JSONL 记录消息/工具结果；支持 rewind、resume、fork、worktree 和 compaction | 这是开发者会话恢复模型；不等于企业业务对象和跨系统操作的事务恢复 |
| `CLAUDE-SUBAGENT-20260821` | 官方文档 | [Custom subagents](https://code.claude.com/docs/en/sub-agents) | Subagent 能按工具、permission mode 和规则限制能力；支持 foreground/background；background 完成后回到主会话并留在任务面板 | 子 Agent 的工具限制和结果回报不等于共享工件的强类型版本协议或动态调度的业务回执 |
| `CLAUDE-PERM-20260821` | 官方文档 | [Security](https://code.claude.com/docs/en/security)；[Permissions](https://code.claude.com/docs/en/permissions)；[Sandboxing](https://code.claude.com/docs/en/sandboxing) | 默认只读，编辑/命令/网络等行为需要权限；permissions 与 OS-level sandbox 叠加，支持 allow/ask/deny、路径和域名限制 | 这是“工具能否做”的权限体系；本轮未见业务风险等级、Evidence/Approval/Permit 绑定到业务工件版本的完整链路 |
| `CLAUDE-HOOKS-20260821` | 官方文档 | [Hooks](https://code.claude.com/docs/en/hooks) | Hooks 可在 PreToolUse、PostToolUse、PermissionRequest、TaskCompleted 等生命周期点调用 command/HTTP/MCP/prompt/agent；async hook 可后台运行 | Hooks 是扩展点和生命周期拦截器，不能自动提供统一的企业 Task/Branch/Artifact/ControlEvent 业务协议 |
| `CLAUDE-ENTERPRISE-20260821` | 官方文档 | [Admin setup](https://code.claude.com/docs/en/admin-setup) | 企业可集中管理权限、sandbox、MCP、plugin、hook、CLAUDE.md 和 OpenTelemetry usage/cost visibility | 管理平面和使用遥测不等于业务事实、客户数据来源或用户交互状态的可解释闭环 |
| `LANGGRAPH-RUNTIME-20260821` | 官方文档 | [LangGraph overview](https://langchain-ai.github.io/langgraph/index.html)；[Persistence](https://langchain-ai.github.io/langgraph/concepts/time-travel/) | LangGraph 定位为 orchestration runtime，提供 durable execution、streaming、human-in-the-loop 和 persistence；checkpointer 支持 thread 级状态、恢复和 time travel | 它是框架/运行时能力，不是开箱即用的企业前台或业务治理产品；应用仍需自行定义证据、权限、事实和交互协议 |

## 3. 维度对比

| 维度 | OpenClaw | OpenAI Codex | Claude Code | Office Agent 应形成的差异 |
| --- | --- | --- | --- | --- |
| 产品中心 | 自托管 Gateway + 多渠道个人 Agent | 代码仓库、终端、worktree、skills 和 cloud/app task | 当前目录、终端、代码和 session | 企业工作区中的业务对象、来源、版本、分支和动作影响 |
| 执行循环 | Gateway 路由 → Agent loop → tools/plugins → session/transcript；可后台 task/cron | prompt → 读仓库 → 计划 → 工具/编辑 → 测试/diff → review；App 支持并行 threads | prompt → tool loop → permission/hook → subagent/background → session transcript | `Task Contract → Observe → Plan → Act → Verify → Commit`，每一步产生可回放的服务端事实 |
| 长任务 | 持久 session、SQLite transcript、cron/task ledger、compaction/memory | App automations 可定时唤醒，cloud/threads/worktrees 支持长任务 | JSONL session、resume/fork、compaction、background subagent | 长任务不只是“还在跑”，而是显示当前阶段、待决策、来源版本、分支状态、预算和恢复点 |
| 多 Agent | 多 Agent 路由、独立 workspace/session；native subagent 或 ACP 外部 harness | 多线程并行、隔离 worktree；并行 coding agents | foreground/background subagents、fork、worktree | Demo 2 不只显示“选了 swarm”，而要真实创建受限 Worker、共享已验证 Artifact、显示依赖/阻塞/重排和汇总结果 |
| 权限/审批 | tools policy + sandbox + host exec approval + pairing/node capability | sandbox + approval modes；默认工作区约束和 elevated approval | permissions + OS sandbox + managed settings + hooks；默认 read-only | 风险和审批绑定 `ActionSpec + ArtifactVersion + Evidence + Policy + Permit`，前台显示业务影响而不是只显示命令授权 |
| 文件/工作区 | agent workspace 是 cwd/记忆；可隔离 sandbox workspace | repo/worktree、terminal、文件 diff、skills | current directory、CLAUDE.md、worktree、文件快照 | 邮件/CRM/报价/日历是一级业务界面；Agent 读写的是 Artifact，文件、来源和字段事实可追溯 |
| 可观察性 | Control UI、task audit、sessions list/history、tool policy/sandbox explain | thread、diff、summary pane、review queue、commands/approvals | task panel、session history、hooks、OpenTelemetry | 业务用户看到“会改变/会重新核对/保持不变/不会发生”；技术审计再提供内部事件和 trace |
| 恢复/持久化 | Gateway-owned SQLite session rows/transcripts、cron state、memory files | thread/worktree/cloud task/automation 等产品级续作；具体状态依产品 surface | JSONL transcripts、file snapshots、resume/fork；SDK 可选择持久或无状态 | DB 中持久化 Task/Branch/Artifact/ControlEvent/approval/permit receipt；版本过期、源文件改动、断线和重复提交 fail closed |
| 企业治理 | 自托管、pairing、tool/agent policy、节点能力控制 | sandbox、权限规则、team/project configuration、review | managed settings、MCP/plugin/hook 管控、OTel、usage/cost | 以业务事实和动作风险为中心的治理，而非把“允许运行某命令”当作全部治理 |

## 4. 事实、推断和不可过度宣称

### 已由官方材料支持的事实

1. OpenClaw、Codex App 和 Claude Code 都已经提供不同形态的并行/后台 Agent 或任务管理；因此“我们支持多 Agent/后台运行”不能单独作为创新。
2. 三者都提供权限、sandbox 或审批相关控制；因此“我们有人工确认”也不能单独作为创新。
3. 三者都保留会话、任务或 transcript 的某种持久化/恢复形态；因此“我们支持长任务恢复”必须说明恢复的对象、版本和边界。
4. Codex App、OpenClaw Control UI、Claude Code task/session UI 都在改善可观察性，但主要围绕 coding task、session、diff、command、tool 或 token，而不是企业业务字段冲突和跨系统事实一致性。

### 基于官方材料的受限推断

1. 这些产品的公开官方材料以 coding/terminal/tool harness 或个人 gateway 为中心。不能据此断言它们没有任何业务治理功能；更稳妥的表述是：在本轮检索到的官方材料中，没有把“业务 Artifact 版本、来源证据、字段冲突、动作影响账本”作为统一产品主协议展示。
2. Office Agent 的差异应落在“业务语义和可审计事实的前台投影”，而不是“后台多调用几个模型”。这是一项产品/架构推断，后续需要 Demo 证据和用户理解测试支持，不能称为已验证用户价值。

## 5. 对 Office Agent 设计的改进要求

### 5.1 Demo 2 从“方案记录”升级为“受控执行纵切”

Demo 2 第一纵切的 `selected_mode`、`selection_receipt` 和 `execution_status=not_started` 是诚实的，但只覆盖 Admission。研究建议的受控执行状态机现已由 `DR-0015` 在固定工程范围落地；下列是当时的目标抽象，不等于当前类名或通用生产能力：

```text
待决定
  → 用户确认本次协作方式
  → AdmissionReceipt
  → 创建 WorkerRun（资料核对 / 经营分析 / 风险提取 / 汇总）
  → WorkerStarted / WorkerProgress / ArtifactCreated
  → WorkerBlocked 或 EvidenceConflict
  → SchedulerReplanned（重排或补派）
  → VerifierPassed
  → SwarmCommit（共享工件版本）
  → 等待用户确认下一步业务动作
```

必须使用服务端事实，不通过前端 sleep 伪造等待：

- `WorkItemSnapshot`：业务工作项状态、版本、当前 route、selection receipt；
- `WorkerRun`：worker 身份、允许的工具/来源范围、状态、开始/结束和失败原因；
- `SharedArtifactVersion`：产物、来源文档/字段、digest、验证状态和依赖；
- `ControlEvent`：有序启动、进度、阻塞、重排、验证和提交事件；
- `ExecutionReceipt`：只描述确实发生的内部协作；没有外部 Connector 时明确 `no_external_action`；
- `BudgetLedger`：记录本轮规则预算/调用次数/超时边界，不能把策略 forecast 写成真实节省；
- `Verifier/Resolver`：失败或冲突时暂停相关分支，不能由汇总 Agent 自行覆盖证据。

### 5.2 前台不能做成 Worker 日志墙

业务用户不需要看到原始 prompt、链路 token、Worker 对话或内部函数名。建议采用三层交互：

1. 首屏是“任务进度地图”：四个业务工作单元、当前状态、依赖、是否需要人；
2. 展开单元后是“为什么”：读取了哪些演示资料、形成了什么中间工件、哪个事实冲突导致暂停；
3. 技术审计入口才显示 event id、model/provider、tool capability、trace 摘要和版本 digest。

用户应该能直接回答：现在谁在做什么、为什么停了、我确认后会改变什么、哪些事情绝不会发生。

### 5.3 与 Demo 1 和 Demo 3 的衔接

- Demo 1 提供“长任务持续运行、分支和事实冲突”的单任务基线；Demo 2 将同一套 Task/Artifact/ControlEvent 协议扩展到并行工作单元；
- Demo 2 只负责内部资料处理和共享工件生成，不直接发送邮件或写 CRM；
- Demo 3 接收 Demo 2 的最终已验证 ArtifactVersion，重新做风险、证据、审批和 Permit 绑定；
- 如果任何来源文件、Artifact 或版本在执行中变化，Demo 2 必须显示“需要重新核对”，不能继续沿用旧决策。

## 6. 汇报可直接使用的比较表述

> OpenClaw、Codex 和 Claude Code 已经把 Agent 的工具调用、终端工作、子 Agent、后台任务、权限和会话恢复做得很强。Office Agent 不把这些基础能力重新包装成创新，而是在企业办公场景中增加一层业务事实与交互控制：Agent 的每个建议都必须绑定当前业务对象、来源版本和验证状态；每个前台状态都来自服务端事实；每个可能产生副作用的动作都在提交前显示影响预演、在提交后显示执行回执。这样用户看到的不是“Agent 在后台调用了几个工具”，而是“我的哪项业务材料正在被谁处理、依据是什么、哪里存在冲突、确认之后会改变什么”。

这段话仍然是设计主张，不是用户效果结论。Demo 2 已有固定受控执行工程 Evidence，但仍需同任务路由对照和至少 5 人无引导理解测试验证差异与用户价值。
