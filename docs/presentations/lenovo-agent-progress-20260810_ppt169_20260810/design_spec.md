# Lenovo Office Agent Progress Review - Design Spec

> Human-readable design narrative for the 2026-08-10 progress review. The machine execution contract is `spec_lock.md`; on divergence, `spec_lock.md` wins.

## I. Project Information

| Item | Value |
| ---- | ----- |
| **Project Name** | Office Agent Runtime：从架构共识到可验证 Demo 1 |
| **Canvas Format** | PPT 16:9 (1280 x 720) |
| **Page Count** | 11 |
| **Design Style** | Pyramid narrative + Swiss Minimal visual system |
| **Target Audience** | 联想方项目负责人、产品与技术决策者，以及华南理工联合项目团队 |
| **Use Case** | 0716-v2 会后阶段评审：说明四个 PR 已完成什么、前台如何承接后台事实、证据能支持到哪里、下一轮如何推进 |
| **Delivery Purpose** | `balanced` business |
| **Content Strategy** | balanced default：以结论先行重新组织材料，但所有数字、实现状态、来源和边界均来自项目 sources，不引入外部事实 |
| **Created Date** | 2026-08-10 |

---

## II. Canvas Specification

| Property | Value |
| -------- | ----- |
| **Format** | PPT 16:9 |
| **Dimensions** | 1280 x 720 |
| **viewBox** | `0 0 1280 720` |
| **Margins** | left/right 56, top 40, bottom 32 |
| **Content Area** | 1168 x 648 |

---

## III. Visual Theme

### Theme Style

- **Mode**: `pyramid`，先给出工程结论，再用治理、四个 PR 和证据链支撑，最后收束到下一轮验收顺序。
- **Visual style**: `swiss-minimal`，强调网格、对齐、硬边界、少装饰和可投影的证据层级。
- **Theme**: Light theme.
- **Tone**: 克制、工程化、证据优先；绿色只表示已验证事实，琥珀色表示边界或待补证据，红色只表示禁止越界的风险。

### Color Scheme

| Role | HEX | Purpose |
| ---- | --- | ------- |
| **Background** | `#F7F9F8` | 页面主背景 |
| **Secondary bg** | `#EEF3F0` | 轻量分区、证据带 |
| **Surface** | `#FFFFFF` | 截图承载、少量卡片和标签底色 |
| **Primary** | `#1C2A24` | 标题、结构线、主文本 |
| **Accent** | `#14865F` | 已验证事实、主路径、确认状态 |
| **Secondary accent** | `#C58B2B` | 边界、待验证项、风险提示 |
| **Body text** | `#202824` | 正文 |
| **Secondary text** | `#52605A` | 注释和次级说明 |
| **Tertiary text** | `#74817B` | 页脚、来源、低权重标签 |
| **Border/divider** | `#CDD8D2` | 分隔线和截图边框 |
| **Grid** | `#DFE7E3` | Swiss 网格、表格细线 |
| **Success** | `#14865F` | 通过、已合并、已验证 |
| **Warning** | `#C58B2B` | 未验证、部分覆盖、边界 |
| **Danger** | `#B34B3E` | 禁止宣称或安全风险 |

No gradients are used. Hierarchy comes from alignment, type scale, whitespace, rules, and restrained solid fills.

---

## IV. Typography System

### Font Plan

**Typography direction**: CJK-primary rational sans with stable Windows/PPT rendering.

| Role | Chinese | English | Fallback tail |
| ---- | ------- | ------- | ------------- |
| **Title** | `Microsoft YaHei UI` | `Segoe UI` | `Arial`, `sans-serif` |
| **Body** | `Microsoft YaHei UI` | `Segoe UI` | `Arial`, `sans-serif` |
| **Emphasis** | `Microsoft YaHei UI` | `Segoe UI` | `Arial`, `sans-serif` |
| **Code** | — | `Consolas`, `Courier New` | `monospace` |

**Per-role font stacks**:

- Title: `'Microsoft YaHei UI','Segoe UI',Arial,sans-serif`
- Body: `'Microsoft YaHei UI','Segoe UI',Arial,sans-serif`
- Emphasis: `'Microsoft YaHei UI','Segoe UI',Arial,sans-serif`
- Code: `Consolas, "Courier New", monospace`

### Font Size Hierarchy

**Baseline (unitless px)**: Body font size = 24.

| Role | Size | Weight | Use |
| ---- | ---- | ------ | --- |
| Cover number | 320 | 700 | P01 巨型 `4` 证据钩子 |
| Cover title | 72 | 700 | P01 主标题与大型结论 |
| Hero number | 56 | 700 | PR 数量、证据数量等单点指标 |
| Page title | 44 | 700 | P02-P11 页面标题 |
| Subtitle | 32 | 600 | 封面副标题、章节级短句 |
| Lead | 28 | 600 | 每页唯一核心结论句 |
| Subheading | 28 | 600 | 内容分区标题 |
| Body content | 24 | 400 | 正文和关键说明 |
| Annotation / caption | 18 | 400 | 图注、状态标签、引用说明 |
| Micro annotation | 16 | 400 | P07 紧凑事实投影与证据计数 |
| Page number / footnote | 14 | 400 | 页码、来源、边界脚注 |

---

## V. Layout Principles

### Page Structure

- **Header area**: y=40-126；左侧页码/章节标签，标题不超过两行，右侧可放状态标记。
- **Content area**: y=144-656；按信息重量使用非对称分栏、流程、证据截图或裸文本分区，不把每一页做成同一种卡片网格。
- **Footer area**: y=672-688；来源、边界或 PR 链接，14px，使用 tertiary text，保持 32px bottom safe margin。

### Layout Pattern Library

- P01 使用排版海报：巨型 `4` 作为证据钩子，标题沿左侧网格展开。
- P02/P05/P06/P08/P11 使用清晰的水平或垂直流程，但每页结构不同。
- P03 使用三柱结构，把治理要求写成完成门槛而不是口号。
- P04 使用来源链和协议层级，不使用截图。
- P07 让真实 Demo 截图成为页面主视觉，原生 SVG 只做证据标注。
- P09 使用四个证据数字和两张恢复截图，数字之间不相加。
- P10 使用左右对照但不做“优缺点”措辞，而是“已证明 / 未证明”。

### Spacing Specification

**Universal**:

| Element | Recommended Range | Current Project |
| ------- | ----------------- | --------------- |
| Safe margin from canvas edge | 40-60 | 56 horizontal, 40 top, 32 bottom |
| Content block gap | 24-40 | 28-36 |
| Icon-text gap | 8-16 | 12 |

**Card-based layouts**:

| Element | Recommended Range | Current Project |
| ------- | ----------------- | --------------- |
| Card gap | 20-32 | 20 |
| Card padding | 20-32 | 22 |
| Card border radius | 8-16 | 4 |
| Single-row card height | 530-600 | 520 when used |
| Double-row card height | 265-295 | 252 each when used |
| Three-column card width | 360-380 | 368 |

**Non-card containers**:

- Use 32-48px whitespace between naked text blocks and 1px grid rules as separators.
- Dense text line-height is 1.42x; breathing pages use 1.6x.
- Screenshots use native ratio with no crop and a 2px matte frame; never obscure state, version, conflict, Commit, or recovery wording.
- Repeating motif: a 6px accent rule and small `PXX` index anchor; no shadows, decorative orbs, gradients, or nested cards.

---

## VI. Icon Usage Specification

### Source

- **Built-in icon library**: `chunk-filled`
- **Usage method**: SVG placeholder `<use data-icon="chunk-filled/icon-name" .../>`; only the inventory below is approved.

### Recommended Icon List

| Purpose | Icon Path | Page |
| ------- | --------- | ---- |
| 治理门槛/通过 | `chunk-filled/shield-check` | P03, P10 |
| 分支与 PR 演进 | `chunk-filled/git-branch` | P02, P06 |
| 持久状态 | `chunk-filled/database` | P05, P11 |
| 前台界面 | `chunk-filled/desktop` | P07, P08 |
| 协议与工件 | `chunk-filled/file` | P04, P07 |
| 验证通过 | `chunk-filled/circle-checkmark` | P02, P09 |
| 边界与风险 | `chunk-filled/triangle-exclamation` | P06, P10 |
| 恢复与对账 | `chunk-filled/arrows-repeat` | P05, P08, P09 |
| 版本/工件层级 | `chunk-filled/layers` | P07 |
| 目标与路线 | `chunk-filled/target-arrow` | P01, P11 |
| 用户研究 | `chunk-filled/users` | P04, P11 |
| 时序与恢复 | `chunk-filled/clock` | P09, P11 |
| 工程实现 | `chunk-filled/code` | P04, P05 |
| 来源映射 | `chunk-filled/link` | P04, P08 |

---

## VII. Visualization Reference List

| Page | Template | Path | Summary-quote (verbatim from `charts_index.json`) | Usage |
| ---- | -------- | ---- | ------------------------------------------------- | ----- |
| P02 | chevron_process | `templates/charts/chevron_process.svg` | "Pick for 3-6 phase methodology with chunky arrow-chain progression and deliverables per phase. Skip for <=2 phases or non-linear flow (use process_flow), or chain ending in an aggregate outcome wedge (use chevron_chain_with_tail)." | 四个 PR 的连续工程交付链 |
| P03 | vertical_pillars | `templates/charts/vertical_pillars.svg` | "Pick for 1×3 / 1×4 / 1×5 vertical column layout where each pillar = one independent category with title + bullets — PEST (Political/Economic/Social/Technological), four-pillar strategy overview, side-by-side independent categories. Skip for 2×2 quadrant (use quadrant_text_bullets), pricing tiers (use comparison_columns), or 2×2 parallel aspects (use labeled_card)." | 三项写死的治理门槛 |
| P05 | layered_architecture | `templates/charts/layered_architecture.svg` | "Pick for 3-4 horizontal architecture layers (presentation/service/data), 2-4 module cards per layer, each card = title + 1-line description (description required, even if source brief). Skip if no per-module descriptions (use icon_grid) or no horizontal layering (use module_composition)." | Task Bar、API/SSE、Store 三层事实链 |
| P06 | process_flow | `templates/charts/process_flow.svg` | "Pick for 3-8 sequential steps connected by simple arrows — approval workflows, customer onboarding, request handling, lifecycle stages. Skip if cyclical (use circular_stages) or stages produce named outputs (use pipeline_with_stages)." | Observe-Plan-Act-Verify-Commit 与冲突门 |
| P08 | client_server_flow | `templates/charts/client_server_flow.svg` | "Pick for left-side clients + right-side servers with labeled bidirectional arrows for key interactions (request/response/push). Each module = name + 1-line description; each arrow must have an action label. Skip for non-distributed flows (use process_flow)." | UI 状态到服务端 Snapshot/Event 的映射 |
| P09 | kpi_cards | `templates/charts/kpi_cards.svg` | "Pick for 4-8 standalone numeric metrics shown as overview cards (2x2 or 1x4) — exec summary opener, dashboard headline, quarterly recap, results-at-a-glance. Skip if metrics have target baselines (use bullet_chart) or single hero number (use gauge_chart)." | PR、Python、E2E、截图证据记分板 |
| P10 | pros_cons_chart | `templates/charts/pros_cons_chart.svg` | "Pick for bilateral pros/cons list, 2-5 items per side. Skip for full feature comparison (use comparison_table) or numeric A/B mirror data (use butterfly_chart)." | 改写为“已证明 / 未证明”的双边界对照 |
| P11 | roadmap_vertical | `templates/charts/roadmap_vertical.svg` | "Pick for 4-8 milestones on a vertical timeline with status indicators. Skip for horizontal time emphasis (use timeline) or tasks with durations (use gantt_chart)." | 下一轮四个连续验收 PR |

**Runners-up considered**:

- `numbered_steps` | rejected for P02: 四个 PR 不只是编号说明，还需要显示前一 PR 为后一 PR 提供可审查交付物，chevron progression 更合适。
- `comparison_table` | rejected for P10: 页面只有两组边界主张，不是跨多行功能对比；双侧证据清单更清晰。
- `pipeline_with_stages` | rejected for P06: Observe/Plan/Act/Verify 并非每阶段都有独立命名输出，使用 process_flow 可避免伪造交付物。

---

## VIII. Image Resource List

| Filename | Dimensions | Ratio | Purpose | Type | Layout pattern | Acquire Via | Status | Reference | text_policy | page_role |
| -------- | ---------- | ----- | ------- | ---- | -------------- | ----------- | ------ | --------- | ----------- | --------- |
| demo1-pr4-conflict-artifact-desktop.png | 1440 x 900 | 1.60 | P07 主证据图：冲突态 Task 与 Artifact Workspace | Interface screenshot | #49 Asymmetric collage + #70 Image with thin colored matte frame | user | Existing | `FRONTEND-E2E-DEMO1-PR4-20260810`, SHA-256 `D1AF0ACB...F9AB7ABE` |  |  |
| demo1-pr4-conflict-artifact-mobile.png | 390 x 1260 | 0.31 | P07 移动端布局证据 | Interface screenshot | #17 Picture-in-picture inset + #70 Image with thin colored matte frame | user | Existing | 390 x 844 viewport full-page capture, SHA-256 `3460B4AF...F41165E5` |  |  |
| demo1-pr4-committed-artifact-desktop.png | 1440 x 900 | 1.60 | P07 提交态与客户回复 v3 证据 | Interface screenshot | #49 Asymmetric collage + #70 Image with thin colored matte frame | user | Existing | `FRONTEND-E2E-DEMO1-PR4-20260810`, SHA-256 `4E015E57...5D51A39` |  |  |
| demo1-pr4-pending-recovery.png | 1280 x 720 | 1.78 | P09 请求发送前失败后的结果待确认状态 | Interface screenshot | #48 Side-by-side comparison (before/after, A/B, then/now) + #70 Image with thin colored matte frame | user | Existing | pending recovery screenshot, SHA-256 `075C9BB1...FE8617` |  |  |
| demo1-pr4-reconciled.png | 1280 x 720 | 1.78 | P09 reload 后同 key 对账回到服务端 Snapshot | Interface screenshot | #48 Side-by-side comparison (before/after, A/B, then/now) + #70 Image with thin colored matte frame | user | Existing | reconciled screenshot, SHA-256 `AC9DED46...81B5226` |  |  |

All screenshot rows are `no-crop` in `spec_lock.md`; critical state, version, conflict, Commit, and recovery labels must remain visible.

**Image-as-canvas coverage note**: 本 deck 不采用 #38-#46 的截图内原生覆盖层，因为五张图片都是需要完整保留像素和状态语义的 UI 证据；覆盖卡片、连线或网络节点会遮挡版本、冲突、Commit 或恢复提示。P07/P09 的说明全部放在截图边界之外，以 no-crop 证据图 + 独立 SVG 注释实现。

---

## IX. Content Outline

### Part 1: Conclusion and Governance

#### Slide 01 - Cover

- **Cover impact**: 用巨型数字 `4` 作为具体钩子，直接表达“四个已合并 PR”；采用 Swiss typographic poster，数字占据右半幅，左侧标题与一条绿色证据线对齐，不使用装饰背景或卡片。
- **Layout**: Negative-space-driven typographic poster with giant number, left-aligned title stack, and a small evidence footer.
- **Title**: Office Agent Runtime
- **Subtitle**: 从架构共识到可验证 Demo 1
- **Info**: 0716-v2 会后推进汇报 · 2026.08.10 · 联想 × 华南理工
- **Sources**: `TARGET_ARCHITECTURE.md` §2-4；`REPORT_STATUS_SNAPSHOT.md`。
- **Evidence / Status**: `Verified progress snapshot`；master=`0a02bb9`，四个 PR 已合并。
- **Boundary**: 封面只宣告阶段进展，不宣告生产级长任务 Runtime、真实恢复或 Adaptive Swarm 已完成。

#### Slide 02 - 先给结论：四个 PR 已形成可审查纵切

- **Layout**: Four-stage horizontal chevron chain; a full-width boundary band sits below, not inside the stages.
- **Title**: 四个 PR 已形成可审查纵切
- **Core message**: 我们已经把治理门槛、服务端任务事实、固定 Fixture 状态转换和真实浏览器前台投影串成一条工程证据链，但它仍不是生产级长任务引擎。
- **Visualization**: chevron_process (see VII. Visualization Reference List)
- **Content**:
  - PR #4 / 协议与留痕：Scenario、Source、Task/Branch/Artifact/Control/Event/Commit。
  - PR #5 / 服务端真值：TaskStore、REST、Owner scope、SSE、真实 Task Bar。
  - PR #6 / 受控状态转换：Observe-Plan-Act-Verify、局部冲突、控制、Commit。
  - PR #7 / 前台闭环：Artifact Workspace、移动端、真实 Edge E2E。
  - 边界：固定 Fixture、主要为内存 Store；PostgreSQL 重启、SSE 断线、真实 Connector 和用户价值仍待补证。
- **Sources**: `REPORT_STATUS_SNAPSHOT.md`；`DR-0002-bounded-durable-office-loop.md` §3、§6。
- **Evidence / Status**: `Verified engineering vertical slice`；merge commits `5d4d5bc / 2923d19 / dd9cedc / 0a02bb9`。
- **Boundary**: “可审查纵切”只覆盖固定 Fixture 与已列工程路径，不等于通用后台运行或生产验收。

#### Slide 03 - 0716-v2 反馈被写成三项硬门槛

- **Layout**: Three unequal vertical pillars with a single bottom rule labeled “缺一项，不进入完成结论”.
- **Title**: 0716-v2 反馈不再是提醒，而是完成门槛
- **Core message**: 从现在起，每个决策、推进和汇报都必须同时回答用户看见什么、该状态由哪个服务端事实产生，以及设计判断来自哪里。
- **Visualization**: vertical_pillars (see VII. Visualization Reference List)
- **Content**:
  - 前台输出：显示目标、状态、版本、冲突、验证、待确认动作；失败与恢复必须进入交互设计。
  - 前后端统一：每个 UI 状态映射 Snapshot 字段或有序 Event；颜色、动画和 Toast 不是事实。
  - 场景与来源：User feedback、会议原件、内部脚本、论文/官方文档、源码与测试分别登记支持范围和局限。
  - 默认隐藏：Prompt、思维链、Worker 内部对话、幂等键、Permit、密钥、完整堆栈与无决策价值日志。
- **Sources**: `DR-0001-reporting-and-interaction-gates.md`；`SOURCE_REGISTER.md`；`UI_SERVER_FACT_MATRIX.md`。
- **Evidence / Status**: `Verified governance gate`；治理入口与防回退测试已落地。
- **Boundary**: 治理规则本身不证明某个 UI 有效，也不替代具体 Runtime、用户研究或运行证据。

### Part 2: Four PRs

#### Slide 04 - PR #4：先固定场景、来源与协议

- **Layout**: Left evidence spine from source types to one scenario; right protocol stack with thin dividers and no card grid.
- **Title**: PR #4：先让设计与事实有出处
- **Core message**: 在写 Runtime 代码前，我们先固定客户 A 场景、来源台账、核心实体协议和 UI 事实矩阵，防止静态原型或口头判断冒充实现证据。
- **Content**:
  - 来源台账：`USER-FEEDBACK-20260810-02`、0716-v2 原件、内部讲稿、仓库基线、ReAct、LangGraph 官方文档、NIST AI RMF。
  - 来源分级：反馈证明“必须做什么”；论文和框架支持原则；源码与测试才能证明本地实现。
  - 核心协议：Task、Branch、ArtifactVersion、TaskEvent、ControlEvent、VerificationReport、ConflictRecord、TaskCommit。
  - 场景边界：设计 Source ID 与运行时 Fixture `source_ref` 是两套概念，不能互相替代。
  - 验证：全量 Python `37 passed`；只证明协议、类型、治理入口和防回退测试。
- **Sources**: `SOURCE_REGISTER.md`；`SCENARIO-001-customer-a-durable-report.md`；`DR-0002-bounded-durable-office-loop.md` §2-4、§6。
- **Evidence / Status**: PR #4 `Verified contract/governance foundation`；全量 Python `37 passed`。
- **Boundary**: 只证明协议、类型和留痕门槛，不证明 TaskStore、SSE、Loop 或真实前台已运行。

#### Slide 05 - PR #5：Task Bar 背后有了服务端真值

- **Layout**: Three horizontal architecture layers: UI, API/SSE, Store; arrows explicitly label REST Snapshot and event discovery.
- **Title**: PR #5：从“画一个 Task Bar”到“由 Snapshot 驱动”
- **Core message**: Task Bar 不再展示客户端模拟进度，而是读取 Owner 隔离、可幂等创建、可按序查询的服务端 Task 事实。
- **Visualization**: layered_architecture (see VII. Visualization Reference List)
- **Content**:
  - UI 层：Active Task Bar 显示 Task ID、目标、阶段、预算、版本和同步状态。
  - API 层：创建、列表、详情；Task SSE 以 `after` 读取新事件并发送 heartbeat。
  - Store 层：内存与 PostgreSQL 保存代码路径；Snapshot、TaskEvent、ArtifactVersion 的 owner scope。
  - 创建事实：新任务从 `ready / contract` 开始，带三个初始 Branch 和 `TASK_CREATED(sequence=1)`。
  - 验证：针对性 `7 passed`、全量 Python `44 passed`；没有 PostgreSQL 实跑、API 重启、多实例或浏览器 E2E。
- **Sources**: `DR-0002-bounded-durable-office-loop.md` §4、§6；`UI_SERVER_FACT_MATRIX.md` §5；`REPORT_STATUS_SNAPSHOT.md`。
- **Evidence / Status**: PR #5 `Verified in-memory creation/API path`；针对性 `7 passed`，全量 `44 passed`。
- **Boundary**: PostgreSQL 只有代码路径；本机未实跑、未重启、未验证多实例通知和浏览器端到端。

#### Slide 06 - PR #6：固定 Fixture 的受控 Loop

- **Layout**: Observe-Plan-Act-Verify-Commit process flow with an amber conflict gate interrupting only the operating-analysis branch.
- **Title**: PR #6：让冲突、控制和 Commit 成为服务端事实
- **Core message**: 固定客户 A 路径已能原子地产生有序 Trace、工件版本、验证报告、局部冲突和最终 Commit，并通过版本与幂等约束避免客户端补造完成状态。
- **Visualization**: process_flow (see VII. Visualization Reference List)
- **Content**:
  - Observe / Plan / Act / Verify：`start` 在一次 mutation 中物化阶段 Trace，事务提交后浏览器才看到结果。
  - 局部冲突：正式口径 2,400 万与预测口径 2,680 万只阻塞经营分析分支，其他两分支保持独立。
  - Resolve：解决最后一个 open Conflict 后，经营分析重验、客户回复联动到 v3，再产生 TaskCommit/state hash。
  - Control：Pause、Resume、Take over、Return control 已有状态事实；Steer 只称“已记录，等待后续循环应用”。
  - 验证：针对性 `15 passed`、全量 Python `56 passed`；这不是后台持续调度，也不是任意中间 checkpoint 恢复。
- **Sources**: `DEMO1-PR3-RUNTIME-EVIDENCE.md` §1、§3-5；`SCENARIO-001-customer-a-durable-report.md` §4-5；`DR-0002-bounded-durable-office-loop.md` §4、§6。
- **Evidence / Status**: PR #6 `Verified fixed-Fixture runtime path`；针对性 `15 passed`，全量 `56 passed`。
- **Boundary**: start 是一次原子 mutation；中间阶段不逐步可见，Steer 未重新规划，PostgreSQL/重启/真实 Connector 未验。

#### Slide 07 - PR #7：同一 Snapshot 驱动任务与工件工作区

- **Layout**: Asymmetric screenshot collage: conflict desktop is dominant, committed desktop is the outcome strip, mobile is a narrow inset; three native callouts point to version/conflict/Commit facts.
- **Title**: PR #7：后台状态终于落到可操作的前台
- **Core message**: 右侧 Task Runtime 与左侧 Artifact Workspace 现在共享同一服务端 Snapshot，用户能看到分支 head、版本、验证、冲突、lineage 和 Commit，而前端不创建虚假工件或完成状态。
- **Content**:
  - Artifact Workspace：当前 head、结构化内容、验证结果、冲突、来源、完整 lineage、最近 Commit/state hash。
  - 交互连续性：Task 面板直达工件；“长期任务工件 / 工作台待办”双 tab 保留原手工待办。
  - 安全投影：三个固定 artifact kind 使用 allowlist，未知 kind/字段隐藏；安全 `source_ref` 才显示。
  - 边界：这是前端第二道投影，不是服务端通用脱敏，也不证明字段中的任意文本天然安全。
  - 浏览器证据：system Edge `2 passed (18.4s)`；主路径终态 1 Task、3 committed Branch、7 个唯一 ArtifactVersion。
- **Sources**: `DEMO1-PR4-FRONTEND-E2E-EVIDENCE.md` §1-5；`UI_SERVER_FACT_MATRIX.md` §1、§5；`REPORT_STATUS_SNAPSHOT.md`。
- **Evidence / Status**: PR #7 `Verified fixed-Fixture frontend path`；system Edge `2 passed (18.4s)`，五张带 SHA 的截图。
- **Boundary**: 恢复用例是请求发送前 abort；不证明服务端提交后响应丢失、SSE 断线、通用脱敏或用户价值。

### Part 3: Fact Mapping and Evidence

#### Slide 08 - 前台状态必须能指回服务端事实

- **Layout**: Client/server flow with UI modules on the left, TaskSnapshot/Event facts on the right, REST/SSE arrows in the center, and a hidden-details rail at the bottom.
- **Title**: 每个 UI 状态都必须能回答“依据是什么”
- **Core message**: UI 只负责翻译服务端事实和提供动作入口；Snapshot、Event 与 RunSnapshot 才决定任务、分支、冲突、控制、Commit 和副作用动作的真实状态。
- **Visualization**: client_server_flow (see VII. Visualization Reference List)
- **Content**:
  - Active Task Bar → `TaskSnapshot.task_id/status/phase/version/contract/budget`。
  - Branch / Conflict → `branches[]`、`conflicts[]` 和对应 TaskEvent。
  - Artifact Workspace → `artifact_versions[]`、`verification_reports[]`、`last_commit`。
  - Task Control → `controls[]`、Branch status、expected version 与 mutation Snapshot。
  - Action Gate → 独立 `RunSnapshot.risk/control_plan/permit/tool_result`，尚未与 Task Artifact 版本绑定。
  - 时序：Task SSE 只发现变化，随后 GET Snapshot 对账；连接状态不代表后台仍在执行。
- **Sources**: `UI_SERVER_FACT_MATRIX.md` §1-4；`SCENARIO-001-customer-a-durable-report.md` §6。
- **Evidence / Status**: `Partially verified`；固定主路径映射已验，SSE 浏览器恢复与通用 display projection 未验。
- **Boundary**: UI 文案、颜色、Toast、进度条和连接状态均不是业务真值；Action Gate 与 Task Runtime 仍是两条事实链。

#### Slide 09 - 工程证据记分板

- **Layout**: Four metric cards in the top half; pending/reconciled screenshots form a no-crop before/after strip below.
- **Title**: 我们用可复核证据汇报，不把不同测试相加
- **Core message**: 四个 PR 均有对应的代码、自动化或浏览器证据，但每个数字只支持它明确覆盖的工程范围。
- **Visualization**: kpi_cards (see VII. Visualization Reference List)
- **Content**:
  - `4` 个已合并 PR：#4 / #5 / #6 / #7。
  - `56`：PR 3 时点全量 Python 回归，不与 PR 1 的 37 或 PR 2 的 44 相加。
  - `2`：PR 4 system Edge 浏览器 E2E，耗时 18.4s，不是 Python 测试。
  - `5`：带实测尺寸和 SHA-256 的 PR 4 截图。
  - 恢复证据：发送前 abort → `sessionStorage` 保留原 key/intent → reload → 同 key 重试 → 5 个唯一 ArtifactVersion；不证明服务端已提交但响应丢失。
- **Sources**: `REPORT_STATUS_SNAPSHOT.md`；`DEMO1-PR3-RUNTIME-EVIDENCE.md` §3；`DEMO1-PR4-FRONTEND-E2E-EVIDENCE.md` §2-3。
- **Evidence / Status**: `Verified recorded runs`；37/44/56 是不同 PR 时点，2 是浏览器 E2E，5 是截图数量。
- **Boundary**: 各数字不得相加或外推；Fixture 金额不是业务效果指标，截图不能独立证明 hash、幂等或用户理解。

#### Slide 10 - 已证明什么，也明确没有证明什么

- **Layout**: Bilateral evidence field with a green verified column, an amber unverified column, and a red one-line anti-overclaim rule.
- **Title**: 工程闭环成立，不等于生产能力成立
- **Core message**: 当前证据足以支持固定 Fixture 的受控前后端纵切，但不足以支持真实持久恢复、真实连接器、通用安全或用户价值结论。
- **Visualization**: pros_cons_chart adapted as proved/not-proved (see VII. Visualization Reference List)
- **Content**:
  - 已证明：协议与来源留痕；内存 Store 主要路径；固定 Observe-Plan-Act-Verify；局部冲突；Artifact lineage；Commit/state hash；指定浏览器主路径与发送前 abort 恢复。
  - 未证明：PostgreSQL/API 重启；多实例通知；Task SSE 断线/序号缺口；服务端提交后响应丢失；真实 LLM/Connector；Artifact → Action 失效；人工编辑新版本。
  - 用户研究仍缺：`H-001` 至 `H-004` 仍是 Draft hypothesis，不能把功能正确性写成理解成本、等待时间或接管效果改善。
- **Sources**: `DR-0002-bounded-durable-office-loop.md` §4-6；`DEMO1-PR4-FRONTEND-E2E-EVIDENCE.md` §4-5；`SCENARIO-001-customer-a-durable-report.md` §2、§7。
- **Evidence / Status**: `Ready overall / verified bounded paths`；本页是 claim boundary，不是新的实现证据。
- **Boundary**: “未证明”项保持未验证；`H-001` 至 `H-004` 在用户研究完成前必须继续标记 Draft hypothesis。

#### Slide 11 - Closing: 下一轮只补会改变完成结论的证据

- **Closing impact**: 让听众离场时记住四个连续验收动作：真实持久化、真实恢复、Action 绑定、用户证据；用一条向下收敛的 vertical roadmap 把每一步连接到“可进入下一阶段”的验收门，不以 Thank-you 收尾。
- **Layout**: Four-milestone vertical roadmap on the left; right side holds acceptance criteria and the final line “真实 Connector 与 Adaptive Swarm 仍需独立实现与验证”.
- **Title**: 下一轮：四个连续 PR，把剩余假设变成证据
- **Core message**: 接下来不扩概念面，而是按恢复风险和用户价值顺序补齐四类证据，完成后再讨论真实 Connector 与 Adaptive Swarm。
- **Visualization**: roadmap_vertical (see VII. Visualization Reference List)
- **Content**:
  - PR A：PostgreSQL 实跑 + API 重启，对账 Task ID、version、event sequence、Artifact head、state hash。
  - PR B：服务端提交后响应丢失 + Task SSE `after`/序号缺口/Snapshot 对账浏览器 E2E。
  - PR C：Artifact/Action 版本绑定，旧审批与 Permit 失效；人工接管创建新 ArtifactVersion。
  - PR D：围绕 `H-001` 至 `H-004` 做目标用户任务测试，记录场景、样本、行为、结果与局限。
- **Sources**: `DEMO1-PR4-FRONTEND-E2E-EVIDENCE.md` §5；`SCENARIO-001-customer-a-durable-report.md` §5、§7；`DR-0002-bounded-durable-office-loop.md` §6。
- **Evidence / Status**: `Proposed / Draft roadmap`；尚未实现或批准为完成项。
- **Boundary**: 真实 Connector 与 Adaptive Swarm 不进入当前“已实现”结论；每一 PR 仍需独立通过场景、来源、后端、前台与验证门槛。

---

## X. Speaker Notes Requirements

- **Total duration**: 12-15 minutes.
- **Style**: formal, evidence-led, conversational enough for joint review.
- **Purpose**: report progress, prevent overclaiming, and secure agreement on the next four acceptance slices.
- **Filename**: match SVG basename after `total_md_split.py` (for example `01_cover.md`).
- **Content**: each page includes a 45-90 second script, explicit transition, source cue, and one sentence naming the claim boundary. P07 may use up to 120 seconds for the screenshot walkthrough.

---

## XI. Technical Constraints Reminder

### SVG Generation Must Follow:

1. viewBox: `0 0 1280 720`
2. Background uses `<rect>` elements.
3. Text wrapping uses `<tspan>`; `<foreignObject>` is forbidden.
4. Transparency uses `fill-opacity` / `stroke-opacity`; `rgba()` is forbidden.
5. Forbidden: `<mask>`, `<style>`, `class`, `<foreignObject>`, `textPath`, `animate*`, `script`, `iframe`.
6. Text characters use raw Unicode; XML reserved characters are escaped as `&amp;`, `&lt;`, `&gt;`, `&quot;`, `&apos;`.
7. `marker-start` / `marker-end` is allowed only with a marker in `<defs>`, `orient="auto"`, and triangle/diamond/circle geometry.
8. `clipPath` is allowed only on `<image>` with one native shape child.

### PPT Compatibility Rules:

- `<g opacity="...">` is forbidden; set opacity on each child.
- Images use `preserveAspectRatio="xMidYMid meet"` because every project screenshot is no-crop evidence.
- Inline attributes only; external CSS and `@font-face` are forbidden.
- Use only locked colors, fonts, icons, images, rhythms, and chart templates from `spec_lock.md`.
