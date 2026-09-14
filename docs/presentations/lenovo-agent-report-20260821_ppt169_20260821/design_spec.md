# Lenovo Office Agent - Design Spec

> Human-readable design narrative for the 16-page project review deck. Claims are deliberately bounded by the cited source or evidence record. The machine-readable execution contract is `spec_lock.md`.

## I. Project Information

| Item | Value |
| ---- | ----- |
| **Project Name** | Lenovo Office Agent - From Agent Activity to Governed Work Delivery |
| **Canvas Format** | ppt169 (1280x720) |
| **Page Count** | 16 |
| **Design Style** | Swiss minimal: restrained editorial grid, thin rules, asymmetric evidence placement, red/green status accents, no decorative gradients |
| **Target Audience** | 联想方产品、设计与技术评审，以及华南理工项目组后续汇报评审者 |
| **Use Case** | 项目阶段性汇报：解释技术对比、三 Demo 的真实状态、用户交互影响、前后端事实对齐与下一轮验证计划 |
| **Delivery Purpose** | balanced / business presentation |
| **Formula Policy** | text-only |
| **Image Usage** | provided images only; no AI-generated assets |
| **Generation Mode** | continuous |
| **Refine Spec** | false |
| **Content Strategy** | 在不改变事实和证据边界的前提下，重组材料为问题张力、技术判断、Demo 1-3、证据边界和下一步实验的汇报叙事；保留关键数字、版本、来源和限制，不把 Draft 或 Limited Verified 写成生产能力。 |
| **Created Date** | 2026-08-21 |

## II. Canvas Specification

| Property | Value |
| -------- | ----- |
| **Format** | ppt169 |
| **Dimensions** | 1280 x 720 |
| **viewBox** | `0 0 1280 720` |
| **Margins** | 56px left/right, 44px top, 36px bottom |
| **Content Area** | 1168 x 640; title band 72px, footer/source line 24px |

## III. Visual Theme

### Theme Style

- **Mode**: narrative
- **Visual style**: swiss-minimal
- **Theme**: Light theme
- **Tone**: 企业级、证据导向、克制但具有现场感；通过真实 UI 截图与原生结构图形成“业务界面 + 运行事实”的双层叙事。

### Color Scheme

| Role | HEX | Purpose |
| ---- | --- | ------- |
| **Background** | `#F7F9FC` | 主背景 |
| **Secondary bg** | `#EAF0F7` | 信息区、图表浅底 |
| **Surface** | `#FFFFFF` | 卡片、证据面板、原生结构图表面与截图衬底 |
| **Primary** | `#0B3A70` | 标题、主线、架构节点 |
| **Accent** | `#D71920` | 冲突、风险、需要决策的状态 |
| **Secondary accent** | `#16845B` | 已验证、完成、保持不变 |
| **Body text** | `#172230` | 正文 |
| **Secondary text** | `#526579` | 说明、来源、边界 |
| **Tertiary text** | `#8291A3` | 页码与细注 |
| **Border/divider** | `#CAD6E3` | 分割线、图片边界 |
| **Success** | `#16845B` | Verified / completed |
| **Warning** | `#D71920` | conflict / risk / not verified |
| **Grid** | `#DCE5EF` | 原生图形网格，低对比度 |

### AI Image Strategy

无 AI 图片。所有视觉证据使用仓库既有真实 UI 截图；架构、对比、时序和成熟度使用可编辑 SVG 原生图形重绘。

## IV. Typography System

### Font Plan

**Typography direction**: CJK-first enterprise sans with restrained Latin labels.

| Role | Chinese | English | Fallback tail |
| ---- | ------- | ------- | ------------- |
| **Title** | Microsoft YaHei UI | Segoe UI | Arial, sans-serif |
| **Body** | Microsoft YaHei UI | Segoe UI | Arial, sans-serif |
| **Emphasis** | Microsoft YaHei UI | Segoe UI | Arial, sans-serif |
| **Code** | — | Consolas | "Courier New", monospace |

**Per-role font stacks**:

- Title: `'Microsoft YaHei UI','Segoe UI',Arial,sans-serif`
- Body: `'Microsoft YaHei UI','Segoe UI',Arial,sans-serif`
- Emphasis: `'Microsoft YaHei UI','Segoe UI',Arial,sans-serif`
- Code: `Consolas,"Courier New",monospace`

### Font Size Hierarchy

| Role | Size | Use |
| ---- | ---- | --- |
| Cover title | 56 | P01 hero claim |
| Page title | 44 | all page titles |
| Subtitle | 30 | page lead |
| Lead | 30 | core assertion line |
| Body | 24 | primary copy and table cells |
| Annotation | 18 | captions and evidence labels |
| Micro | 14 | compact metadata and dense status detail |
| Label | 15 | navigation, badges and small control labels |
| Caption | 17 | image captions and supporting explanations |
| Footnote | 16 | source, version, boundary |
| Hero number | 56 | only P09 / P15 key metrics |

## V. Layout Principles

### Page Structure

- **Header area**: 72px; page number, section label, concise title, one red/green status mark when useful.
- **Content area**: 604px; one visual spine plus 2-4 supporting blocks. Avoid full-page card grids; use rules, scaled evidence, and native lines to keep the deck breathable.
- **Footer area**: 24px source/boundary strip. Every page carries a small source tag and status (`Verified`, `Limited Verified`, or `Draft`).

### Layout Pattern Library

| Pattern | Use in this deck |
| ------- | ---------------- |
| **Asymmetric split (3:7 / 2:8)** | P05, P06, P10: dominant screenshot or process with a short argument rail |
| **Symmetric split (5:5)** | P02 competitor comparison, P11 Demo 3 before/after |
| **Layered architecture** | P03 architecture and P13 unified three-Demo contract |
| **Pipeline with stages** | P07 front/backend SSE facts and P08 Demo 2 execution |
| **Native evidence collage** | P01, P06, P09, P11: screenshots remain no-crop and are treated as proof, not decoration |
| **Negative-space-driven** | P16 closing call: one large sentence + four test gates |

### Spacing Specification

- Safe margin: 56px.
- Content block gap: 28px.
- Icon-text gap: 10px.
- Card gap only where unavoidable: 20px; radius 8px; border 1px.
- Image evidence: never crop; fit native ratio with `xMidYMid meet` and a 1px border.

## VI. Icon Usage Specification

- **Source**: project copy of the built-in `tabler-outline` library.
- **Usage method**: `<use data-icon="tabler-outline/clock" .../>` with 2px stroke; every icon must come from the concrete inventory below.

| Purpose | Icon Path | Page |
| ------- | --------- | ---- |
| long-running task | `tabler-outline/clock` | P01, P05 |
| business fact / source | `tabler-outline/file-search` | P01, P06 |
| branch / route | `tabler-outline/git-branch` | P02, P08 |
| control loop | `tabler-outline/refresh` | P03, P07 |
| architecture / modules | `tabler-outline/layout-dashboard` | P03, P04 |
| model / worker | `tabler-outline/users-group` | P08, P09 |
| shared artifact | `tabler-outline/file-check` | P09, P10 |
| evidence / verify | `tabler-outline/shield-check` | P06, P10, P14 |
| conflict | `tabler-outline/alert-triangle` | P05, P06, P09 |
| approval / human gate | `tabler-outline/user-check` | P11 |
| action | `tabler-outline/bolt` | P11, P13 |
| server fact / API | `tabler-outline/server-2` | P12 |
| experiment | `tabler-outline/chart-infographic` | P15, P16 |
| next step | `tabler-outline/map-route` | P16 |

Inventory was checked against `C:/Users/73811/.codex/skills/ppt-master/templates/icons/tabler-outline/`; only names listed in `spec_lock.md` may be used.

## VII. Visualization Reference List

Catalog read: `C:/Users/73811/.codex/skills/ppt-master/templates/charts/charts_index.json`. The following are exact catalog matches; pages not listed here use free native SVG diagrams.

| Page | Template | Path | Summary-quote | Usage |
| ---- | -------- | ---- | ------------- | ----- |
| P02 | comparison_table | `templates/charts/comparison_table.svg` | "Pick for 2-4 plans/products compared across many feature rows (dense matrix). Skip for pricing-tier marketing layout (use comparison_columns)." | OpenClaw / Codex / Claude Code / Office Agent comparison |
| P03 | layered_architecture | `templates/charts/layered_architecture.svg` | "Pick for 3-4 horizontal architecture layers (presentation/service/data), 2-4 module cards per layer, each card = title + 1-line description (description required, even if source brief). Skip if no per-module descriptions (use icon_grid) or no horizontal layering (use module_composition)." | Runtime / enhancement / control architecture |
| P04 | icon_grid | `templates/charts/icon_grid.svg` | "Pick for 4-9 parallel features/capabilities/services as icon cards — feature grid, service lineup, benefits matrix, brand values, product highlights. Skip for sequential ordering (use numbered_steps) or hierarchical layers (use pyramid_chart)." | Eight minimum Runtime modules and maturity badges |
| P05 | process_flow | `templates/charts/process_flow.svg` | "Pick for 3-8 sequential steps connected by simple arrows — approval workflows, customer onboarding, request handling, lifecycle stages. Skip if cyclical (use circular_stages) or stages produce named outputs (use pipeline_with_stages)." | User-facing problem to business-state workflow |
| P06 | process_flow | `templates/charts/process_flow.svg` | "Pick for 3-8 sequential steps connected by simple arrows — approval workflows, customer onboarding, request handling, lifecycle stages. Skip if cyclical (use circular_stages) or stages produce named outputs (use pipeline_with_stages)." | Demo 1 来源冲突处理：Observe-Plan-Act-Verify-Commit 与冲突门 |
| P07 | client_server_flow | `templates/charts/client_server_flow.svg` | "Pick for left-side clients + right-side servers with labeled bidirectional arrows for key interactions (request/response/push). Each module = name + 1-line description; each arrow must have an action label. Skip for non-distributed flows (use process_flow)." | Task / Artifact / ControlEvent / SSE alignment |
| P08 | pipeline_with_stages | `templates/charts/pipeline_with_stages.svg` | "Pick for 3-5 horizontal pipeline stages, each = title + 1-line description + output artifact, connected by arrows (data pipelines, ETL, build pipelines). Skip if any stage lacks an artifact (use process_flow or numbered_steps)." | Demo 2 execution packages and outputs |
| P09 | timeline | `templates/charts/timeline.svg` | "Pick for 3-8 milestone events on a horizontal time axis (no duration). Skip for tasks with start/end ranges (use gantt_chart) or vertical layout (use roadmap_vertical)." | seq 1-15, replan at seq 9/10, completion at seq 15 |
| P10 | module_composition | `templates/charts/module_composition.svg` | "Pick for one parent container wrapping 3-N child module cards, each = title + 2-3 bullets — fits 'Feature X contains 3 parts, each with its own description'. Skip if source has only labels without descriptions (use numbered_steps or icon_grid)." | Shared Artifact convergence package |
| P11 | process_flow | `templates/charts/process_flow.svg` | "Pick for 3-8 sequential steps connected by simple arrows — approval workflows, customer onboarding, request handling, lifecycle stages. Skip if cyclical (use circular_stages) or stages produce named outputs (use pipeline_with_stages)." | Preview -> evidence -> approval -> permit -> simulator receipt |
| P12 | client_server_flow | `templates/charts/client_server_flow.svg` | "Pick for left-side clients + right-side servers with labeled bidirectional arrows for key interactions (request/response/push). Each module = name + 1-line description; each arrow must have an action label. Skip for non-distributed flows (use process_flow)." | UI state to Snapshot / Event / Receipt facts |
| P13 | layered_architecture | `templates/charts/layered_architecture.svg` | "Pick for 3-4 horizontal architecture layers (presentation/service/data), 2-4 module cards per layer, each card = title + 1-line description (description required, even if source brief). Skip if no per-module descriptions (use icon_grid) or no horizontal layering (use module_composition)." | Three Demos on one Runtime and shared protocols |
| P14 | feature_matrix_table | `templates/charts/feature_matrix_table.svg` | "Pick for competitive feature checklist with checkmarks across products. Skip for qualitative scores (use harvey_balls_table) or pricing tier marketing (use comparison_columns)." | Evidence status and boundary matrix |
| P15 | comparison_table | `templates/charts/comparison_table.svg` | "Pick for 2-4 plans/products compared across many feature rows (dense matrix). Skip for pricing-tier marketing layout (use comparison_columns)." | Four-route controlled experiment |
| P16 | roadmap_vertical | `templates/charts/roadmap_vertical.svg` | "Pick for 4-8 milestones on a vertical timeline with status indicators. Skip for horizontal time emphasis (use timeline) or tasks with durations (use gantt_chart)." | Next validation gates |

**Runners-up considered**:

- `hub_spoke` rejected for P03/P13: these pages have horizontal service/control layers, not a core capability with surrounding spokes.
- `process_flow` rejected for P09: seq 1-15 is a milestone timeline with no duration, so `timeline` is more exact.
- `harvey_balls_table` rejected for P14: evidence state is categorical (`Verified` / `Limited Verified` / `Draft`), not a qualitative score.

## VIII. Image Resource List

All image rows are existing user/project materials. No AI image is needed. Use `no-crop` for every screenshot so exact UI evidence remains readable.

**Ratio authority**: For asset validation, `PixelAspectRatio` and the actual `Width ÷ Height` of the source bitmap are authoritative. `AspectRatio` in `analysis/image_analysis.csv` records the PPT display-frame ratio and must not be used to infer source-image geometry.

| Filename | Dimensions | Ratio | Purpose | Type | Layout pattern | Acquire Via | Status | Reference | text_policy | page_role |
| -------- | ---------- | ----- | ------- | ---- | -------------- | ----------- | ------ | --------- | ----------- | --------- |
| `image1.jpeg` | 1280x724 | 1.768 | historical cover/context visual from 0716-v2 | Diagram | #73 Full-bleed poster image + side title stack + #27 Linear gradient mask for text legibility | user | Existing | 0716-v2 cover candidate; use only as historical context, not current evidence | embedded | hero_page |
| `image8.png` | 1672x941 | 1.777 | prior architecture reference for one base/two enhancements/three controls | Diagram | #44 Background image + native network/architecture diagram | user | Existing | 0716-v2 P03 architecture reference; redraw all labels natively | embedded | local |
| `image9.png` | 1672x941 | 1.777 | eight-module reference | Diagram | #50 Tiled grid (2×2, 2×3, 3×3) with equal cells | user | Existing | 0716-v2 P04 minimum runtime components; current maturity is updated natively | embedded | local |
| `image30.png` | 1672x941 | 1.777 | workspace-first interaction principle | Diagram | #48 Side-by-side comparison (before/after, A/B, then/now) | user | Existing | 0716-v2 workspace-first evidence; supports user-flow contrast | embedded | local |
| `image32.png` | 1672x940 | 1.779 | workspace and artifact dual-stream | Diagram | #39 Background image + flow nodes drawn over the scene | user | Existing | 0716-v2 human-agent co-editing and SSE story | embedded | local |
| `image33.png` | 1672x941 | 1.777 | model output vs deterministic governance boundary | Diagram | #44 Background image + native network/architecture diagram | user | Existing | 0716-v2 governance boundary; redraw labels for current protocols | embedded | local |
| `image36.png` | 1672x941 | 1.777 | risk ladder and L5 deny boundary | Diagram | #41 Background image + measurement lines and module tags (engineering overlay) | user | Existing | 0716-v2 risk framing; current claims remain fixed-scope | embedded | local |
| `image41.png` | 1672x941 | 1.777 | Demo 1 workspace -> confirmation -> simulator receipt | Diagram | #48 Side-by-side comparison (before/after, A/B, then/now) + #70 Image with thin colored matte frame | user | Existing | 0716-v2 Demo 1 interaction reference; current file-backed evidence is E1 | embedded | local |
| `image42.png` | 1960x1039 | 1.886 | blank mail workspace with Agent side panel | Photography | #80 Side hero image + staggered evidence cards | user | Existing | current workspace-first UI; do not infer execution from blank state | embedded | local |
| `image43.png` | 1963x1041 | 1.886 | mail artifact with visible governance panel | Photography | #80 Side hero image + staggered evidence cards | user | Existing | current business UI and action gate context | embedded | local |
| `image44.png` | 1672x941 | 1.777 | calendar-side action context from earlier prototype | Diagram | #48 Side-by-side comparison (before/after, A/B, then/now) | user | Existing | 0716-v2 Demo 2 action context; label as historical context, not current swarm execution | embedded | local |
| `image39.png` | 649x493 | 1.316 | action confirmation tray close-up | Photography | #62 Same image, two references — full view + zoom-callout | user | Existing | Demo 3 confirmation interaction; Simulator only | embedded | local |
| `image40.png` | 1672x941 | 1.777 | one-time Permit and re-check logic | Diagram | #48 Side-by-side comparison (before/after, A/B, then/now) | user | Existing | 0716-v2 Permit explanation; current Demo 3 receipt remains simulator-bounded | embedded | local |
| `image45.png` | 1568x931 | 1.684 | calendar business workspace with action conversation | Photography | #80 Side hero image + staggered evidence cards | user | Existing | current business UI; external action claims must be simulator-labelled | embedded | local |
| `image46.png` | 1573x933 | 1.686 | calendar approval card | Photography | #80 Side hero image + staggered evidence cards | user | Existing | current confirmation tray; user sees business consequence, not Permit internals | embedded | local |
| `dr-0015-demo2-controlled-execution-1440-selected-not-started.png` | 1440x1000 | 1.44 | Demo 2 route selected, execution not started | Diagram | #48 Side-by-side comparison (before/after, A/B, then/now) | user | Existing | E2 selected-not-started state; route receipt is not execution | embedded | P08 |
| `dr-0015-demo2-controlled-execution-1440-running.png` | 1440x1000 | 1.44 | Demo 2 controlled execution running | Diagram | #48 Side-by-side comparison (before/after, A/B, then/now) | user | Existing | E2 running state; workers and model calls are observable facts | embedded | P08 |
| `dr-0015-demo2-controlled-execution-1440-dynamic-replan.png` | 1440x1000 | 1.44 | Demo 2 dynamic replan after revenue conflict | Diagram | #45 Background image + numbered hotspots with sidebar legend | user | Existing | E2 seq 9/10 replan and worker-added state | embedded | P09 |
| `dr-0015-demo2-controlled-execution-1440-completed.png` | 1440x1000 | 1.44 | Demo 2 completed execution | Diagram | #48 Side-by-side comparison (before/after, A/B, then/now) | user | Existing | E2 seq 15 completion; four workers and five artifacts | embedded | P09 |
| `dr-0015-demo2-controlled-execution-1440-completed-receipt.png` | 1440x1000 | 1.44 | Demo 2 completion receipt and no external action | Diagram | #62 Same image, two references — full view + zoom-callout | user | Existing | E2 execution receipt; external_side_effect=none | embedded | P10 |
| `dr-0015-demo2-controlled-execution-390-completed.png` | 390x3856 | 0.10 | Demo 2 mobile completed execution view | Diagram | #53 Vertical image stack | user | Existing | E2 mobile no-crop responsive evidence | embedded | P09 |

Screenshots for the current Demo 2 controlled execution run are staged in `images/` with the exact filenames above. They are sourced from `docs/evidence/DEMO2-CONTROLLED-EXECUTION-EVIDENCE-20260821.md` and must remain `no-crop`.

## IX. Content Outline

### Part 1: Why This Office Agent Must Be Different

#### Slide 01 - Cover: Agent 做事之后，企业还需要什么？

- **Cover impact**: The audience sees a real office workspace crossing three states—Task, Artifact, Control—rather than a generic bot hero. Composition: full-bleed light field with three no-crop UI evidence windows connected by a thin red-to-green business consequence line; title floats in the negative space.
- **Layout**: #73 full-bleed poster image + side title stack, using image1.jpeg only as a restrained historical texture; native labels and the current thesis sit above it.
- **Title**: 让 Agent 做事之后，企业还需要什么？
- **Subtitle**: 从“调用发生”到“业务结果可被看见、验证、控制”
- **Info**: Office Agent V0.1 · 2026-08-21 · 阶段性汇报
- **Core assertion**: 主流 Agent 正在解决“如何让 Agent 多做事”，本项目聚焦“如何让企业工作在事实、版本与控制下持续收敛”。
- **Scenario**: 客户经理/项目负责人让 Agent 汇总客户经营信息并准备后续动作；痛点不是没有模型，而是不知道它改变了什么、依据是什么、下一步是否会产生副作用。
- **Source / Evidence / Boundary / Status**: `MEETING-DECK-0716-V2-01`, `USER-FEEDBACK-20260821-07`; E1/E2/E3 provide fixed-scope proof; thesis is `Design claim / Draft`.

#### Slide 02 - 主流方案解决了什么，我们还要补什么

- **Layout**: #48 side-by-side comparison + native `comparison_table` shell; four columns with one final Office Agent column highlighted by business-object language.
- **Title**: OpenClaw、Codex、Claude Code 都在让 Agent 更能执行
- **Core message**: “多 Agent、后台运行、权限与恢复”已经是主流能力，差异必须落到企业业务事实和用户影响。
- **Visualization**: `comparison_table`.
- **Content**: OpenClaw：Gateway、session、multi-agent routing、automation、exec approval；Codex：thread/worktree、并行 coding agents、background automations、review；Claude Code：subagents、permissions、sandbox、hooks、resume/fork。Office Agent adds Task/Branch/Artifact/ControlEvent as the user-facing business protocol, not just another execution harness.
- **Interaction impact**: 用户从“看 thread / diff / command”转向“看哪个业务材料在处理、哪个来源冲突、确认后会改变什么”。
- **Source / Evidence / Boundary / Status**: `OPENCLAW-*`, `CODEX-*`, `CLAUDE-*` official source register in competitor research; no head-to-head benchmark; comparison claim is `Draft`.

#### Slide 03 - 新定位：业务事实是 Agent 的主语

- **Layout**: #44 native network/architecture diagram; center “business fact” with three layers around it.
- **Title**: 我们不是再做一个聊天入口，而是把 Agent 放进业务事实之间
- **Core message**: Agent 的自然语言只能提出建议，服务端必须拥有身份、来源、版本、风险和结果。
- **Visualization**: `layered_architecture`.
- **Content**: Layer 1 user workspaces: mail / calendar / quote / tasks. Layer 2 Office Agent Runtime: Task + Context + Execution + Evidence. Layer 3 controls: Policy + Approval + Permit + Simulator. The user-visible consequence line is `source -> artifact -> control -> receipt`.
- **Interaction impact**: 前台不暴露 prompt/CoT/底层 token，而用来源标签、分支状态、冲突卡、共享工件和四类动作影响解释系统。
- **Source / Evidence / Boundary / Status**: `TARGET_ARCHITECTURE.md`, `DR-0015` §§2-3, `UI_SERVER_FACT_MATRIX`; architecture is implementation-backed, general product differentiation is `Draft`.

### Part 2: Architecture and Minimum Runtime

#### Slide 04 - 八个常驻模块，三种成熟度

- **Layout**: #50 tiled grid with an 8-module maturity ribbon; avoid equal decorative cards by grouping modules by status.
- **Title**: 八个最小模块先把“能运行”变成“可持续、可验证、可控制”
- **Core message**: 复杂能力不是默认常驻，而是按任务复杂度和风险按需装配。
- **Visualization**: `icon_grid`.
- **Content**: Task Contract; Durable Task State; Context State Manager; Execution Loop; Capability Runtime; Evidence & Quality Verifier; Control Policy; Trace & Checkpoints. Mark fixed customer-A paths `Limited Verified`, common/generalized paths `Draft`.
- **Interaction impact**: 用户看到的是可读业务状态；每个状态都有 Snapshot/Event/Artifact/Receipt 事实来源。
- **Source / Evidence / Boundary / Status**: `DR-0015` §6 and `TARGET_ARCHITECTURE.md`; Demo 1 fixed path and Demo 2 fixed path have bounded evidence; full runtime maturity remains `Draft`.

#### Slide 05 - 交互起点：先承认用户的问题

- **Layout**: #80 side hero image + staggered evidence cards using image42/43 as current workspace context; left rail is one user story, right rail is business-state path.
- **Title**: 用户不是想“调用模型”，而是想把一项工作推进到可交付
- **Core message**: 工作区是主角，Agent 是协作层；每一步都应让用户知道当前工作对象与下一步影响。
- **Visualization**: `process_flow`.
- **Content**: trigger: “请整理客户 A 经营汇报并给出可确认的下一步”； current flow: manually switch mail/CRM/calendar and rely on chat summary; target flow: read allowed sources -> draft artifact -> conflict/evidence gate -> verified artifact -> controlled action.
- **Interaction impact**: 用户可继续编辑工作区；Agent 读取活动视图和未保存 context，但不能直接覆盖用户新输入。
- **Source / Evidence / Boundary / Status**: `USER-FEEDBACK-20260811-*` and `SCENARIO-001/002/003`; current UI evidence in image42/43; user comprehension and productivity remain `Draft` until study.

#### Slide 06 - Demo 1：长任务不是一次性回答

- **Layout**: #48 before/after with image41 and a native phase strip; keep screenshot no-crop and place conflict callout outside the image.
- **Title**: Demo 1：同一个 Task 持续推进，分支冲突不会把整项工作推倒重来
- **Core message**: 长任务的价值不在“回答更长”，而在于状态、分支、来源和人工决定可以继续。
- **Visualization**: `process_flow`.
- **Content**: v1 contract -> v2 running/observe -> v3 plan -> v4 act -> v5 verify -> v6 waiting for decision -> v7 committed. File-backed source conflict binds to field facts; only affected branch pauses; other verified artifacts remain.
- **Interaction impact**: Tasks 工作区显示阶段、分支状态、冲突候选、来源和“开始新一轮汇报”；普通业务界面只显示摘要和入口。
- **Source / Evidence / Boundary / Status**: E1 `DEMO1-FILE-BACKED-SOURCES-EVIDENCE-20260820`, `SCENARIO-001`; fixed customer A / project-generated files / bounded path `Verified`; generic durable runtime is not claimed.

### Part 3: Demo 2 and the Visible Execution Loop

#### Slide 07 - 前后台统一：每一个 UI 状态都有服务器事实

- **Layout**: #39 flow nodes + #44 native architecture overlay; left is UI state, right is Snapshot/Event/Receipt, middle is labeled SSE arrows.
- **Title**: “正在处理”不能靠动画，必须由服务端事实产生
- **Core message**: UI 的可见状态是协议投影，不是前端推断。
- **Visualization**: `client_server_flow`.
- **Content**: `Task/Branch/Artifact/ControlEvent` and `WorkCockpitSnapshot/Demo2ExecutionSnapshot` are the authoritative facts. GET gives reconciliation; SSE gives ordered updates; `message_id`, version, digest and idempotency protect duplicate or late events.
- **Interaction impact**: waiting, running, replan, verified, unknown all have explicit recovery actions; raw prompt, CoT, worker dialogue and logs stay hidden.
- **Source / Evidence / Boundary / Status**: `UI_SERVER_FACT_MATRIX.md`, `DR-0015` §5, `DEMO2-CONTROLLED-EXECUTION-EVIDENCE`; protocol mapping is `Limited Verified` in fixed paths, cross-process recovery is `Draft`.

#### Slide 08 - Demo 2：从“选了群组”到真的受控执行

- **Layout**: #76 Mid-page image belt with native text inset + `pipeline_with_stages`; bind `dr-0015-demo2-controlled-execution-1440-selected-not-started.png` and `dr-0015-demo2-controlled-execution-1440-running.png` as the selected-to-running visual transition, with native execution stages below.
- **Title**: Demo 2：用户确认后，Adaptive Swarm 才真正启动
- **Core message**: Route selection is not execution; explicit start creates a bounded internal execution snapshot.
- **Visualization**: `pipeline_with_stages`.
- **Content**: 1 Admission preview: value / breadth / parallelism / deadline / risk / budget. 2 User confirms this run. 3 Three initial workers: revenue facts, project risk, customer requirements. 4 Allowlisted files reveal revenue conflict; service adds a fourth verification worker. 5 Shared package is verified; `external_side_effect=none`.
- **Interaction impact**: user sees selected-not-started, queued/running, worker progress, sources, replan reason, shared artifacts, and final no-external-action receipt.
- **Source / Evidence / Boundary / Status**: E2, `DR-0015` §§4-5, `SCENARIO-002`; fixed customer A, memory single-process, deepseek-v4-pro controlled run is `Limited Verified`; generic swarm and production queue are `Draft`.

#### Slide 09 - Demo 2 运行事实：冲突真的让计划改变

- **Layout**: #45 Background image + numbered hotspots with sidebar legend; bind `dr-0015-demo2-controlled-execution-1440-dynamic-replan.png`, `dr-0015-demo2-controlled-execution-1440-completed.png`, and `dr-0015-demo2-controlled-execution-390-completed.png`; make seq 9/10 the visual red pivot and seq 15 the green endpoint.
- **Title**: Demo 2 的创新不在头像墙，而在“发现冲突后改变工作组织”
- **Core message**: 服务端事件把动态重排变成用户可理解的业务原因。
- **Visualization**: `timeline`.
- **Content**: seq 1-8: execution starts and initial workers run; seq 9 `DYNAMIC_REPLAN`: two files disagree on revenue basis; seq 10 `WORKER_ADDED`: revenue-definition verification; seq 11-14: artifacts and checks converge; seq 15 `EXECUTION_COMPLETED`: 4 workers, 5 artifacts, no external side effect.
- **Interaction impact**: user sees “为什么多出一个工作单元、它核对什么、原有结果是否保留”； no worker transcripts or internal IDs.
- **Source / Evidence / Boundary / Status**: E2 manifest/screenshots and run facts; four model outputs adopted in a live observation but wall-clock is not a production SLA; event sequence is `Limited Verified`.

#### Slide 10 - 共享工件：对话交接变成可验证收敛

- **Layout**: #49 Asymmetric collage with `dr-0015-demo2-controlled-execution-1440-completed-receipt.png` as the large receipt canvas, three native source/verification inserts, and dependency lines; all bitmap screenshots remain no-crop.
- **Title**: 多 Agent 的结果不靠“互相转述”，而靠共享工件版本收敛
- **Core message**: Worker 的交付单位是带来源、版本、digest 和验证状态的 Artifact。
- **Visualization**: `module_composition`.
- **Content**: Parent: Customer A verified report package. Child modules: revenue basis, project risk, customer response draft, revenue-definition check. Each child states source refs, owner, version and verification. Conflict affects only dependent branch; the final package preserves verified work.
- **Interaction impact**: user can inspect “来自哪里、谁处理、当前版本、是否通过验证”，and can decide whether to enter Demo 3; no raw worker chat.
- **Source / Evidence / Boundary / Status**: `SCENARIO-002` §8, E2, `UI_SERVER_FACT_MATRIX`; shared Artifact fixed path `Limited Verified`, general cross-worker consistency `Draft`.

### Part 4: Demo 3 and the Unified Contract

#### Slide 11 - Demo 3：动作前先展示后果

- **Layout**: #48 before/after + native `process_flow`; image39/46 as confirmation-tray proof, four impact categories as a vertical ledger.
- **Title**: Demo 3：用户批准的不是一条命令，而是一次具体业务后果
- **Core message**: “会改变 / 会重新核对 / 保持不变 / 不会发生”让风险控制成为可理解的交互。
- **Visualization**: `process_flow`.
- **Content**: artifact binding -> evidence and risk -> approval -> one-time Permit -> simulator execution -> receipt. Preview says what will happen; receipt says what actually happened. Rejection, invalidation, parameter mismatch and simulator failure preserve the completed Task/Artifact/Commit.
- **Interaction impact**: non-modal confirmation tray stays in context; user can inspect sources, approve/deny, recover unknown result and return to the business workspace.
- **Source / Evidence / Boundary / Status**: E3, `SCENARIO-003`, `DR-0012`, `GOVERNANCE_AND_ACTIONS`; fixed customer A reply_draft -> email.send simulator path `Verified`; no real email/CRM/OA write.

#### Slide 12 - 前后端统一协议：让设计策略落到服务边界

- **Layout**: #44 native client/server flow; show UI vocabulary on left and server facts on right, with one-to-one arrows and a red “do not infer” rail.
- **Title**: 前端展示什么，后端就必须能证明什么
- **Core message**: Task / Branch / Artifact / ControlEvent are the shared vocabulary between product design and runtime implementation.
- **Visualization**: `client_server_flow`.
- **Content**: Task bar ← TaskSnapshot; branch state ← Branch/ConflictRecord; shared artifact ← ArtifactVersion; waiting card ← ControlEvent + required approval; result banner ← execution_receipt. Every state includes version, permission, idempotency and failure/recovery semantics.
- **Interaction impact**: no “秒完成” fake state, no old amount fallback, no frontend-generated risk or permit; missing fact becomes “状态待核对”.
- **Source / Evidence / Boundary / Status**: `UI_SERVER_FACT_MATRIX`, `API.md`, `DECISION_AND_REPORTING_GOVERNANCE`; protocol is a design/engineering invariant, cross-demo generalization remains `Draft`.

#### Slide 13 - 三 Demo 是同一个 Runtime 的三种用户视角

- **Layout**: #44 native architecture + three horizontal experience bands; Demo 1/2/3 each has one visible state and one server fact.
- **Title**: 三个 Demo 不是三套产品，而是同一底座上的三种“工作影响”
- **Core message**: 持续运行解决时间连续性，协作执行解决复杂任务组织，动作治理解决业务副作用控制。
- **Visualization**: `layered_architecture`.
- **Content**: Runtime base: contract, state, context, execution, capability, evidence, policy, trace. Demo 1: Task/Branch/Artifact. Demo 2: Admission/Worker/Shared Artifact. Demo 3: ActionSpec/Impact Preview/Permit/Receipt. Shared protocol: sources, versions, events, user control.
- **Interaction impact**: user recognizes the same state language across mail, calendar, quote, task and audit surfaces.
- **Source / Evidence / Boundary / Status**: `TARGET_ARCHITECTURE`, `DR-0015`, E1/E2/E3; fixed verticals have evidence, one unified product experience is `Draft`.

#### Slide 14 - 证据与边界：我们已经证明到哪里

- **Layout**: #50 evidence matrix with bold status badges and a narrow “not yet” column; keep density controlled by 3 rows per region.
- **Title**: 证据不是装饰：每一个“已完成”都必须带范围
- **Core message**: 当前成果足以证明固定纵切可运行，但还不足以证明通用能力或用户效果。
- **Visualization**: `feature_matrix_table`.
- **Content**: Verified: Demo 1 fixed file-backed conflict path, Demo 3 fixed simulator action ledger. Limited Verified: Demo 2 fixed customer A, single API process memory, real model controlled internal execution. Draft: production recovery, real connectors, generalized swarm, cost/quality benefit, competitor benchmark, user research.
- **Interaction impact**: status badges sit beside every visual claim; “not called / not started / external action none” are explicit, not implied.
- **Source / Evidence / Boundary / Status**: E1/E2/E3, `DR-0015` §8, `PRESENTATION_BRIEF`; this page itself is `Verified` as a scope summary.

### Part 5: From Demonstration to Research Evidence

#### Slide 15 - 下一步实验：同一个任务，四种路由

- **Layout**: #48 asymmetric comparison table with one central task story and four route columns; native metric rails below.
- **Title**: 下一步不再只展示“我们能跑”，而要证明“为什么这样组织更值得用”
- **Core message**: 用同一客户 A 任务对照 Tool Call、Single Agent、Fixed Workflow、Adaptive Swarm，比较质量、时延、规则预算、人工确认负担与异常率。
- **Visualization**: `comparison_table`.
- **Content**: Freeze task/source/model where appropriate; vary only route policy. Metrics: verified artifact completeness, conflict recovery correctness, time-to-verified package, model calls, control events, human confirmations, failure/unknown rate. Preserve negative results and separate model capability from orchestration effects.
- **Interaction impact**: participant sees four understandable work organizations, not internal implementation names; ask them to predict current owner, waiting reason and next consequence before revealing the receipt.
- **Source / Evidence / Boundary / Status**: `DR-0015` §7, competitor research methodology; no results yet, so the whole page is `Draft / planned study`.

#### Slide 16 - Closing：把“Agent 做了什么”变成“工作发生了什么”

- **Closing impact**: Leave the review panel with a concrete call: approve the next evidence loop, not a generic “thank you”. Composition: one large closing sentence on the left; four numbered validation gates on the right with a green route from prototype to evidence.
- **Layout**: #81 illustration-as-layout field implemented with native geometry and negative space; no background photo, one thin ascending roadmap line.
- **Visualization**: `roadmap_vertical`.
- **Title**: 下一阶段的目标，不是更多 Agent，而是更可信的工作交付
- **Content**: 1. 固化四路由对照； 2. 完成失败/预算/局部暂停与跨进程恢复； 3. 开展至少 5 人无引导理解测试； 4. 只把已验证共享工件桥接到 Demo 3。 Closing line: “让用户看见 Agent 的影响，也让系统只承认它真正证明过的影响。”
- **Source / Evidence / Boundary / Status**: `DR-0015` §7 and `DECISION_AND_REPORTING_GOVERNANCE`; forward plan is `Draft / next gate`, not a committed production roadmap.

## X. Speaker Notes Requirements

Create one speaker note per page in `notes/01_cover.md` through `notes/16_closing.md`. Each note must contain: 45-75 second spoken script, one transition sentence, one evidence/boundary cue, and the expected audience question. P01 asks “什么是业务后果”；P08 pauses before the explicit start; P09 explains seq 9/10; P14 reads the boundary statuses; P16 asks for agreement on the four validation gates.

## XI. Technical Constraints Reminder

1. viewBox: `0 0 1280 720`.
2. Use `<rect>` backgrounds; use `<tspan>` for wrapping; no `<foreignObject>`.
3. Use `fill-opacity` / `stroke-opacity`; never `rgba()`.
4. Forbidden: `<style>`, `class`, `foreignObject`, `textPath`, `animate*`, `script`, `iframe`, `symbol` + `<use>`.
5. `marker-start` / `marker-end` only with `<marker>` in `<defs>` and triangle/diamond/circle shapes.
6. `clipPath` only on `<image>` with one shape child; screenshot images are `preserveAspectRatio="xMidYMid meet"` and no-crop.
7. Text is native SVG, not baked into screenshots; source and boundary footers are editable.
8. Use only `tabler-outline` inventory in `spec_lock.md`, with 2px stroke.
9. Do not expose prompt, chain-of-thought, secret, raw internal ID, raw event payload, permit token or simulator internals in the business-facing visual layer.
10. Evidence language must preserve `Verified`, `Limited Verified`, `Draft`; no production, user-effect or competitor-absence claim without evidence.
