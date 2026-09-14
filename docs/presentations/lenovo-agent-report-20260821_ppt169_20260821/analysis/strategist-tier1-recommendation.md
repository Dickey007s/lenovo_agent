# Tier 1 Strategist Recommendation

> 目标：向联想方汇报 Office Agent 当前阶段的技术判断、三个 Demo、前后端统一策略与可复核证据。本文件只属于 PPT Master Step 3/Step 4 的 Tier 1 推荐，不是 `design_spec.md`、不是 `spec_lock.md`，也不触发确认页面。

## Routing

- **Template route**: free design. 用户没有提供含有效 `design_spec.md` 的模板目录。
- **Canvas**: `ppt169`, `1280x720`, `0 0 1280 720`。
- **Mode**: `narrative`，页面内部使用金字塔式结论与证据编排。叙事从真实业务张力开始，经过技术比较，进入 Demo 1/2/3 的可见证据，最后落到验证边界和下一步实验。
- **Visual style**: `swiss-minimal`，推荐安全选项。严格信息网格、清晰层级、锐利分隔线和克制强调色，使真实截图、业务事实和来源标签成为视觉主体。
- **Delivery purpose**: `balanced`，兼顾会议投影与会后阅读。
- **Page range**: 14-16，推荐 15 页；如果需要完整保留来源与证据边界，采用 16 页。

## Tier 1 Anchors

### Audience

主要受众是联想方产品、设计与技术评审者，以及参与 0716-v2 后续评审的团队成员。他们要判断的不只是“后台能不能调用模型”，而是 Agent 是否能在办公场景中形成可理解、可追踪、可控制的业务体验。次要受众是华南理工项目组与后续评审者，需要能够追溯每个结论的场景、来源、前台影响、后端事实和验证证据。

### Delivery purpose

使用 `balanced` / 均衡·商务。后续 Tier 2 正文基线为 24px；页面密度应一页一个断言、一个主视觉和一个简短证据脚注，避免技术附录式堆字，也避免 keynote 式只剩口号。

### Content divergence

建议文案：**在不改变事实和证据边界的前提下，重组材料为“问题张力 → 技术判断 → 三个可见 Demo → 证据与边界 → 下一步实验”的汇报叙事。保留关键数字、版本、来源和限制；不把 Draft、Limited Verified 或仿真数据写成生产能力。**

这是 balanced 重组，而非照搬 0716-v2 原页顺序。任何扩展都必须来自仓库来源和证据文件，不能因为叙事需要而创造事实。

## Visual Style Spectrum

| Spectrum | Catalog id | Temperament | Use |
|---|---|---|---|
| Safe | `swiss-minimal` | 稳定、克制，像高质量产品架构评审 | 推荐。最适合真实截图、协议图、状态时序与证据标签。 |
| Shifted | `editorial` | 有叙事张力，像《经济学人》专题报道 | 让用户问题和 Demo 故事更有记忆点，但保持信息严谨。 |
| Bold | `blueprint` | 工程宣言感，像一张可审阅的系统蓝图 | 突出八模块、状态转换、SSE 时序和控制边界。 |

中心叙事不是“我们也有多 Agent”，而是：**主流 Agent 已经解决让 Agent 多做事；Office Agent 继续追问企业办公中如何让业务结果有证据、可控制、可执行、可追责。**

## Core Story

1. **技术差异**：OpenClaw、Codex、Claude Code 的官方材料已显示 session、工具、subagent、后台执行、权限、sandbox、恢复和 review 等成熟方向；不要把“多 Agent/后台/审批”单独宣称为创新。Office Agent 的差异应落在业务事实、共享工件收敛、语义动作治理和服务端事实投影。
2. **场景与来源**：以客户 A 经营汇报为贯穿案例。历史业务文件包含 CRM 正式收入 2400 万元、预测收入 2680 万元；Agent 不能自行挑选最终口径，必须把冲突变成用户可理解的决定。
3. **交互影响**：用户看到 Agent 的状态、依据、等待点、影响预演和完成回执，而不是 Prompt、思维链、Worker 对话或底层日志。
4. **前后端统一**：Task、Branch、Artifact、ControlEvent、Snapshot 与 SSE 是事实链；每个 UI 状态必须绑定服务端事实，不能用前端动画推断完成。

## Full Narrative Skeleton

### Act I — The question has changed

**Slide 01 — Cover: “让 Agent 做事”之后，企业还需要什么？**
- Assertion: 企业办公 Agent 的难点不是完成一次调用，而是让长程业务结果持续收敛且可追责。
- Visual: 三个真实工作区截面（Task / Cockpit / Action Gate）组成一条 `Task → Artifact → Control` 细线；不要用泛化机器人插画代替产品画面。

**Slide 02 — The user tension**
- Assertion: 用户真正面对的是来源冲突、状态丢失、分支漂移和副作用不可见。
- Visual: 客户 A 的历史文件与当前经营汇报形成冲突；用 `2400 万 CRM` 与 `2680 万预测` 两个业务字段构成视觉张力，对比 chat-only 与 evidence-bound flow。

**Slide 03 — What 0716-v2 locked**
- Assertion: 项目已收敛到“一个统一 Runtime、两个增强能力、三类控制机制”和八个常驻组件。
- Visual: 一条三层架构带，不做八张孤立卡片；将八模块作为从意图到结果的路径标注，并标出成熟度 `Limited Verified / Partial / Draft`。

### Act II — A sharper comparison

**Slide 04 — Mainstream Agent solutions have moved forward**
- Assertion: OpenClaw、Codex、Claude Code 已覆盖重要的 runtime 能力，但公开材料关注重点不同。
- Visual: 三列官方来源能力地图：OpenClaw 的 Gateway/多 Agent/后台与执行审批；Codex 的 thread/worktree/diff/background/review；Claude Code 的 session/subagent/permission/sandbox/hooks。
- Footer: 官方文档访问 2026-08-21；本页不是竞品实测，不根据“未提及”推出“绝对不存在”。

**Slide 05 — The difference we are actually designing**
- Assertion: Office Agent 把中心从 Agent activity 移向 business consequence。
- Visual: 四个转换：`tool permission → semantic action governance`、`chat handoff → shared artifact convergence`、`progress animation → server-owned truth`、`model output → evidence-bound result`。旁注明确“不是宣称独有多 Agent/后台/审批”。

**Slide 06 — Eight modules as a user-facing contract**
- Assertion: 八模块不是后台清单，而是用户可以看到、等待、校正和追责的事实路径。
- Visual: 左侧模块/事实拥有者，右侧可见状态/用户动作；重点连出 Task Contract、Context State、Execution Loop、Evidence/Verifier、Control Policy、Trace/Checkpoint。

### Act III — Three demos, one visible logic

**Slide 07 — Demo 1: long task becomes a recoverable branch**
- Assertion: 用户不会每次打开都直接跳到“核对事实”，而是看到读取资料→拆分任务→生成材料→核对事实的渐进阶段。
- Visual: Task workspace 的真实截图配阶段时间线、一个开放冲突和用户确认动作；强调每一步由服务端 Snapshot/version 推进。

**Slide 08 — Demo 1: files are evidence, not decoration**
- Assertion: 仿真历史文件可以产生可复查冲突，但不能伪装成 Lenovo 的实时企业数据库。
- Visual: 客户来信、CRM 收入 CSV、预测 CSV、项目周报 JSON 的文件卡片，字段连到冲突卡；展示 manifest allowlist、SHA-256、受限解析、fail closed。

**Slide 09 — Demo 2: selecting a route is not executing**
- Assertion: Admission 先让用户理解工作组织方式，再由独立启动动作真正运行。
- Visual: 右侧切换 Single Agent / Fixed Workflow / Adaptive Swarm，左侧影响地图同步变化；分开 `预演`、`已选择`、`not_started` 和 `已记录回执`。

**Slide 10 — Demo 2: the bounded swarm actually happens**
- Assertion: 明确启动后，三个初始工作单元并行执行，收入冲突触发动态重排和第四个核验工作单元，最后收敛为共享工件。
- Visual: `start → 3 workers → revenue conflict → DYNAMIC_REPLAN(seq 9) → WORKER_ADDED(seq 10) → 5 artifacts → seq 15 complete` 的事件瀑布；只在服务端观测到时显示 `模型已调用/输出已采用`。
- Boundary: 固定客户 A、项目生成仿真文件、单 API 进程 memory、`external_side_effect=none`。

**Slide 11 — Demo 3: consequence before action**
- Assertion: 用户在动作前看见会改变什么、会重新核对什么、保持什么和不会发生什么，动作后只看真实 execution receipt。
- Visual: 四类影响账本与非模态确认 tray；Simulator 只做二级注释，主层不写成真实邮件、CRM、OA 或日历写入。

### Act IV — The interaction strategy is the architecture

**Slide 12 — Frontend output is a projection of backend truth**
- Assertion: 每个 UI 状态都由命名的服务端事实产生，而不是由本地乐观状态或动画推断。
- Visual: `Task / Branch / Artifact / ControlEvent → Snapshot → ordered SSE → UI`；举例 `waiting_input`→确认 tray、`selection_receipt`→影响回执、`execution_receipt`→完成/无外部动作。

**Slide 13 — What the user sees, and what stays hidden**
- Assertion: 前台暴露决策所需的影响，隐藏会增加认知负担或风险的实现细节。
- Visual: 两层玻璃盒。可见：来源标签、工件版本、工作单元状态、冲突原因、等待动作、回执；隐藏：Prompt、CoT、Worker transcript、raw payload、Permit token、绝对路径、内部 ID。

### Act V — Evidence and next move

**Slide 14 — What is verified today**
- Assertion: 当前有强的限定范围工程证据，但不是生产就绪声明。
- Visual: 证据阶梯：Demo 1 文件驱动与渐进运行 `Verified（限定范围）`；Demo 2 受控执行 `Limited Verified`（4 workers/5 artifacts/seq 9-10-15）；Demo 3 影响账本 `Verified（固定 Simulator 场景）`。

**Slide 15 — The next experiment**
- Assertion: 下一步应做同一场景、同一数据、同一 harness 下的受控比较，而不是继续孤立堆功能。
- Visual: Single Agent / Fixed Workflow / Fixed Multi-Agent / Adaptive Swarm 四泳道；比较收敛、冲突可见性、用户决定质量和恢复行为。竞品 head-to-head 与用户研究标记为 Pending。

**Slide 16 — Closing: from “agent can act” to “business can trust”**
- Assertion: Office Agent 的目标不是无限自主，而是让业务结果沿着 source→task→artifact→control→receipt 可见、可证、可控地推进。
- Visual: 回到开场的三个工作区画面，闭合成一条业务结果链；最后只提出一个决策：在扩展 Runtime 边界前，先用真实评审者/用户验证交互模型。

## Source and Evidence Discipline

- **Meeting/stakeholder direction**: `sources/0716-v2.md` 与项目登记的 2026-08-21 汇报要求；支持五项汇报重点，但不是用户研究。
- **Official competitor research**: `sources/COMPETITOR-RESEARCH-OPENCLAW-CODEX-CLAUDE-CODE-20260821.md`；支持能力/定位比较，不是竞品效果实测。
- **Architecture/contracts**: `sources/TARGET_ARCHITECTURE.md`、`sources/UI_SERVER_FACT_MATRIX.md`、`sources/DR-0015-mainstream-comparison-and-demo2-controlled-execution.md`；支持八模块和前后端事实映射。
- **Demo 1 evidence**: `sources/DEMO1-FILE-BACKED-SOURCES-EVIDENCE-20260820.md` 与场景文件；支持文件 manifest/hash、字段冲突和限定范围渐进运行。
- **Demo 2 evidence**: `sources/DEMO2-CONTROLLED-EXECUTION-EVIDENCE-20260821.md`；支持四个 Worker、五个共享工件、seq 9/10/15 和无外部动作。
- **Demo 3 evidence**: `sources/DEMO3-ACTION-IMPACT-LEDGER-EVIDENCE-20260820.md`；支持四类影响账本和 Simulator 边界。
- **Interaction references**: Microsoft HAI Guidelines（CHI 2019）与 Google PAIR Feedback + Control；支持设计方向，不证明本产品效果。

## Guardrails

- 真实截图和业务文件字段是主视觉；AI 生成图只可用于封面/章节的抽象氛围，不得伪装为产品状态。
- 不使用代码、Prompt、思维链、底层日志、Permit token、绝对路径或 raw event 作为主叙事。
- 每个 Demo 页面都标记 `演示数据`、`固定客户 A`、验证状态和 `无外部动作` 等边界。
- 不写“主流方案没有多 Agent/后台/审批/恢复”；使用“官方材料强调 X，本项目聚焦 Y”的可追溯表达。
- 不把模型耗时写成生产 SLA、成本节省、质量分数或用户价值证据。
- `Draft`、`Limited Verified`、`Verified（限定范围）`必须视觉区分。

## Tier 2 Handoff

Tier 2 在用户确认 anchors 后再派生：Lenovo-compatible blue/green/red state palette、CJK-safe sans typography（balanced body 24px）、单一 outline/duotone icon library、真实截图和业务图优先、cover/章节 breathing rhythm、Demo 事件瀑布和证据页 dense rhythm。不要从本文件直接生成 SVG 或 `spec_lock.md`，必须先读取 Tier 1 `result.json` 并重新生成 Tier 2 candidates。
