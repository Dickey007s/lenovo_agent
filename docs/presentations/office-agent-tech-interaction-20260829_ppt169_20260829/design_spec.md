# Office Agent：从会回答到可验证办公结论 - Design Spec

> Human-readable design narrative — rationale, audience, style, color choices, content outline. Read once by downstream roles for context.
>
> Machine-readable execution contract: `spec_lock.md` (color / typography / icon / image short form). Executor re-reads `spec_lock.md` before every SVG page to resist context-compression drift. Keep both in sync; on divergence, `spec_lock.md` wins.

## I. Project Information

| Item | Value |
| ---- | ----- |
| **Project Name** | Office Agent：从会回答到可验证办公结论 |
| **Canvas Format** | PPT 16:9 (1280×720) |
| **Page Count** | 17 |
| **Design Style** | Pyramid narrative + data-journalism visual style |
| **Target Audience** | Lenovo CAAI 产品、架构、前端与业务评审人员 |
| **Use Case** | 项目会议、方案评审、PPT 主讲汇报 |
| **Delivery Purpose** | `balanced` business：一页一个主张，辅以适量事实、场景和边界 |
| **Content Strategy** | 以 07-16《未来办公 Agent：Loop、Swarm 与受治理执行》为主体骨架，保留“一个底座、两层增强、三类控制”、八模块、技术演进、Control Loop、三类 Demo 与证据门；只补入已经验证的 Workspace 场景和必要的线上研究，不堆新概念 |
| **Created Date** | 2026-08-29 |

**Core message**：延续 07-16 的判断，未来办公 Agent 的关键不是一次回答更强，而是让工作在 Task Contract、Evidence、Budget、Control 与 Trace 约束下持续收敛。当前 Office Agent 用 Workspace-first、服务端采用门和可回开的成果，把这套方向落到一条受限但可验证的办公纵切。

---

## II. Canvas Specification

| Property | Value |
| -------- | ----- |
| **Format** | PPT 16:9 |
| **Dimensions** | 1280×720 |
| **viewBox** | `0 0 1280 720` |
| **Margins** | 左右 52，上 42，下 34 |
| **Content Area** | 1176×620；标题区约 86，正文区约 486，页脚区约 28 |

---

## III. Visual Theme

### Theme Style

- **Mode**: `pyramid`
- **Visual style**: `data-journalism`
- **Theme**: Light theme
- **Tone**: 克制、证据导向、业务可读；蓝色表示可信流程，琥珀色表示待决或边界，红色只表示冲突或拒绝
- **Visual motif**: 贯穿全稿的“结论合同线”：细蓝线连接来源、计划、成果、回执和当前结论；遇到待决转琥珀，遇到冲突转红

### Color Scheme

| Role | HEX | Purpose |
| ---- | --- | ------- |
| **Background** | `#F7F8FA` | 页面底色 |
| **Secondary bg** | `#EDF1F4` | 分区带、次级信息面 |
| **Surface** | `#FFFFFF` | 截图框、证据面、表格面 |
| **Primary** | `#132A3A` | 标题、主结构、深色文字 |
| **Accent** | `#1769E0` | 已验证流程、链接、关键事实 |
| **Secondary accent** | `#D97706` | 待决、风险、边界 |
| **Body text** | `#1B2733` | 正文 |
| **Secondary text** | `#5A6B7C` | 注释、辅助说明 |
| **Tertiary text** | `#7C8A98` | 页脚、来源 |
| **Border/divider** | `#CBD5DF` | 分隔线、证据框 |
| **Grid** | `#E3E8ED` | 图表网格、轻分隔 |
| **Success** | `#2E7D32` | 已核验、已保留 |
| **Warning** | `#B54708` | 待人工、边界提示 |
| **Danger** | `#C0362C` | 矛盾、拒绝、阻断 |

### Gradient Scheme

本稿不使用装饰性渐变背景。截图上的可读性仅用同色两段式线性遮罩；业务状态仍由实色、边框和文字共同表达，避免只靠颜色。

---

## IV. Typography System

### Font Plan

**Typography direction**: CJK-first 的事实型无衬线；标题有力量但不营销化，接口字段使用等宽字体。

| Role | Chinese | English | Fallback tail |
| ---- | ------- | ------- | ------------- |
| **Title** | `Microsoft YaHei` | `Segoe UI Semibold` | `Arial, sans-serif` |
| **Body** | `Microsoft YaHei` | `Segoe UI` | `Arial, sans-serif` |
| **Emphasis** | `Microsoft YaHei` | `Segoe UI Semibold` | `Arial, sans-serif` |
| **Code** | — | `Consolas, Courier New` | `monospace` |

**Per-role font stacks**:

- Title: `"Microsoft YaHei", "Segoe UI Semibold", Arial, sans-serif`
- Body: `"Microsoft YaHei", "Segoe UI", Arial, sans-serif`
- Emphasis: `"Microsoft YaHei", "Segoe UI Semibold", Arial, sans-serif`
- Code: `Consolas, "Courier New", monospace`

### Font Size Hierarchy

**Baseline (unitless px)**: Body font size = 24.

| Role | Size | Weight | Usage |
| ---- | ---- | ------ | ----- |
| Cover title | 76 | Bold | P01 主张 |
| Page title | 46 | Bold | 全稿页标题 |
| Hero number | 68 | Bold | 15、96、212/212 等单一强调 |
| Subtitle | 32 | SemiBold | 章节式副标题 |
| Lead / core message | 28 | SemiBold | 每页主张句 |
| Subheading | 28 | SemiBold | 场景名、模块名 |
| Body | 24 | Regular | 主体文本 |
| Annotation | 17 | Regular | 标签、场景步骤、截图注释 |
| Footnote | 14 | Regular | 来源、证据状态与禁止推断 |

**Formula policy**: `text-only`。本稿没有需渲染的复杂公式，协议字段保持可编辑文本。

---

## V. Layout Principles

### Page Structure

- **Header area**: 42–118；左对齐页标题，右上角用“当前事实 / 目标设计 / 研究依据”小标签说明证据类型。
- **Content area**: 124–646；截图、流程和场景均围绕一个主结论组织，禁止一页堆满同等权重卡片。
- **Footer area**: 660–696；左侧来源缩写和边界，右侧页码。

### Layout Pattern Library

| Pattern | Use in this deck |
| ------- | ---------------- |
| **Typographic poster + hero object** | P01：冲突式标题与 Workspace 实景并置 |
| **Negative-space-driven** | P02、P10：让核心差异与冲突回执单独落地 |
| **Asymmetric split (3:7 / 2:8)** | P05、P08、P11：一侧结论，一侧真实界面或机制图 |
| **Pipeline / causal chain** | P04、P07、P08、P17：技术差异如何改变用户流程 |
| **Layered architecture** | P06：八模块的当前纵切与目标缺口 |
| **Evidence comparison** | P09、P10、P12、P15：成果、模型说明、前台状态并列 |
| **Scenario ledger** | P12–P15：触发、动作、停顿、前台、后端和边界在同一阅读路径中 |

### Spacing Specification

| Element | Current Project |
| ------- | --------------- |
| Safe margin from canvas edge | 52 |
| Content block gap | 28–36 |
| Icon-text gap | 12 |
| Card gap | 24 |
| Card padding | 24 |
| Card border radius | 6 |

页面优先使用分隔线、浅色带和留白；卡片只用于独立重复项、审计包或场景记录，不做卡片套卡片。

---

## VI. Icon Usage Specification

### Source

- **Built-in icon library**: `tabler-outline`
- **Stroke width**: 2
- **Usage method**: `<use data-icon="tabler-outline/icon-name" ... stroke-width="2"/>`
- **Brand marks**: 不使用伪造竞品截图或品牌图标；竞品以产品名和官方来源标题呈现

### Recommended Icon List

| Purpose | Icon Path | Page |
| ------- | --------- | ---- |
| Workspace / file scope | `tabler-outline/folders`, `tabler-outline/search`, `tabler-outline/file-text` | P01, P07, P11 |
| Policy / evidence | `tabler-outline/shield-check`, `tabler-outline/lock`, `tabler-outline/link` | P03, P04, P08, P09 |
| Agent / planning | `tabler-outline/robot`, `tabler-outline/route`, `tabler-outline/git-branch` | P03–P09 |
| Artifact / receipt | `tabler-outline/file-spreadsheet`, `tabler-outline/clipboard-check`, `tabler-outline/circle-check` | P10–P16 |
| Durable state / recovery | `tabler-outline/database`, `tabler-outline/refresh`, `tabler-outline/versions`, `tabler-outline/history` | P03, P08, P09, P17 |
| Human decision / boundary | `tabler-outline/user-check`, `tabler-outline/alert-triangle`, `tabler-outline/player-pause`, `tabler-outline/plug` | P08–P17 |

---

## VII. Visualization Reference List

Catalog read: 71 templates

| Page | Template | Path | Summary-quote (verbatim from `charts_index.json`) | Usage |
| ---- | -------- | ---- | ------------------------------------------------- | ----- |
| P03 | layered_architecture | `templates/charts/layered_architecture.svg` | "Pick for 3-4 horizontal architecture layers (presentation/service/data), 2-4 module cards per layer, each card = title + 1-line description (description required, even if source brief)." | 复用 07-16 的“一个底座、两层增强、三类控制” |
| P04 | icon_grid | `templates/charts/icon_grid.svg` | "Pick for 4-9 parallel features/capabilities/services as icon cards — feature grid, service lineup, benefits matrix, brand values, product highlights." | 复用 07-16 八模块，更新为当前统一模块名 |
| P05 | chevron_chain_with_tail | `templates/charts/chevron_chain_with_tail.svg` | "Pick for 4-6 sequential chevron blocks plus a final wedge representing aggregate outcome — Porter's value chain (primary + support activities mapped to margin), process leading to a summary deliverable, contribution chain to a result." | 合并 07-16 的 Prompt、Agent Loop、Context、Harness、Loop Engineering 演进 |
| P06 | icon_grid | `templates/charts/icon_grid.svg` | "Pick for 4-9 parallel features/capabilities/services as icon cards — feature grid, service lineup, benefits matrix, brand values, product highlights." | 六种主流方案的交互对象，不做能力胜负表 |
| P07 | pipeline_with_stages | `templates/charts/pipeline_with_stages.svg` | "Pick for 3-5 horizontal pipeline stages, each = title + 1-line description + output artifact, connected by arrows (data pipelines, ETL, build pipelines)." | 技术责任变化如何进入用户流程和前台反馈 |
| P09 | process_flow | `templates/charts/process_flow.svg` | "Pick for 3-8 sequential steps connected by simple arrows — approval workflows, customer onboarding, request handling, lifecycle stages." | Observe、Plan、Act、Verify、Commit 与控制环 |
| P10 | vertical_list | `templates/charts/vertical_list.svg` | "Pick for 3-6 numbered key points each with a short description — design principles, core tenets, action items, key takeaways, recommendations, executive summary points." | 六个具体办公场景作为后续 Demo 入口 |
| P24 | chevron_chain_with_tail | `templates/charts/chevron_chain_with_tail.svg` | "Pick for 4-6 sequential chevron blocks plus a final wedge representing aggregate outcome — Porter's value chain (primary + support activities mapped to margin), process leading to a summary deliverable, contribution chain to a result." | 五步路线图汇聚到“可证伪差异” |

**Runners-up considered**:

- `comparison_table` | rejected for P06：会把官方说明误读为同场能力胜负，违背“不从未提及推断做不到”的边界。
- `circular_stages` | rejected for P09：当前不是无限自治循环，受限 Loop 有明确预算、暂停和终点。
- `roadmap_vertical` | rejected for P24：路线不是日历里程碑，而是多个工程能力汇聚成一个可证伪结论。

---

## VIII. Image Resource List

| Filename | Dimensions | Ratio | Purpose | Type | Layout pattern | Acquire Via | Status | Reference | text_policy | page_role |
| -------- | ---------- | ----- | ------- | ---- | -------------- | ----------- | ------ | --------- | ----------- | --------- |
| `dr-0022-folder-workspace-desktop.png` | 1440×900 | 1.60 | Workspace 首屏与固定资料挑战现场 | Screenshot | #19 Image floating in whitespace with thin frame and caption + #70 Image with thin colored matte frame | user | Existing | 真实 Workspace 截图，不裁掉目录、任务区和状态栏 |  |  |
| `user-feedback-20260828-tc01-artifact-and-citation-confusion.png` | 1374×1275 | 1.08 | TC-01 旧体验：成果存在但引用缺口造成重复待办 | Screenshot | #48 Side-by-side comparison (before/after, A/B, then/now) + #46 Background image + bordered "lens" rectangle highlighting a sub-region | user | Existing | 用户反馈截图，红框区域保留 |  |  |
| `dr-0036-tc01-outcome-first-desktop.png` | 791×1686 | 0.47 | TC-01 outcome-first 改进后的纵向页面 | Screenshot | #53 Vertical image stack + #70 Image with thin colored matte frame | user | Existing | 完整纵向截图，按比例缩放 |  |  |
| `dr-0032-decision-packet-desktop.png` | 1440×1100 | 1.31 | Evidence Resolution 与 Decision Packet 的可处置界面 | Screenshot | #19 Image floating in whitespace with thin frame and caption + #46 Background image + bordered "lens" rectangle highlighting a sub-region | user | Existing | 保留问题首页、候选定位和局部恢复动作 |  |  |
| `scenario-effect-gate-artifact-desktop.png` | 441×605 | 0.73 | 真实 Artifact 与确定性校验回执 | Screenshot | #19 Image floating in whitespace with thin frame and caption + #70 Image with thin colored matte frame | user | Existing | 证明成果文件与回执分层 |  |  |
| `tc14-sre-diagnosis-desktop.png` | 1440×1100 | 1.31 | TC-14 条件式诊断与未执行边界 | Screenshot | #48 Side-by-side comparison (before/after, A/B, then/now) + #46 Background image + bordered "lens" rectangle highlighting a sub-region | user | Existing | 与 TC-15 并列展示 |  |  |
| `tc15-ux-prioritization-desktop.png` | 1440×1100 | 1.31 | TC-15 完整数据排序与规则依据 | Screenshot | #48 Side-by-side comparison (before/after, A/B, then/now) + #46 Background image + bordered "lens" rectangle highlighting a sub-region | user | Existing | 与 TC-14 并列展示 |  |  |
| `narrative-reconciliation-rejected-desktop-1440x1100.png` | 1440×1100 | 1.31 | 当前系统桌面端冲突说明拒绝态 | Screenshot | #48 Side-by-side comparison (before/after, A/B, then/now) + #70 Image with thin colored matte frame | user | Existing | 当前结论与说明采用回执 |  |  |
| `narrative-reconciliation-rejected-mobile-390x844.png` | 390×844 | 0.46 | 当前系统移动端同一拒绝态 | Screenshot | #48 Side-by-side comparison (before/after, A/B, then/now) + #70 Image with thin colored matte frame | user | Existing | 和桌面截图形成跨端对照 |  |  |
| `dr-0036-tc01-live-run-completed.png` | 1440×1000 | 1.44 | 当前系统完整 Run：自然语言目标、全库检索、真实成果与有序 Trace | Screenshot | #19 Image floating in whitespace with thin frame and caption | user | Existing | 新增实操页主图，不裁掉输入区、成果卡或右侧 Trace |  |  |
| `scenario-effect-gate-desktop.png` | 1280×720 | 1.78 | 当前系统真实成果、确定性检查与 EffectReceipt 全景 | Screenshot | #48 Side-by-side comparison + #70 thin matte frame | user | Existing | 展示成果文件与验证回执分层 |  |  |
| `dr-0034-mixed-branch-actions-desktop.png` | 761×361 | 2.11 | 不同 Branch 的补定位与继续动作 | Screenshot | #46 bordered lens + inset | user | Existing | 作为局部恢复页的小图，不冒充完整运行证明 |  |  |
| `dr-0037-review-readability-desktop.png` | 1380×972 | 1.42 | 可读性改进后的证据复核页 | Screenshot | #19 Image floating in whitespace with thin frame and caption | user | Existing | 展示事实、影响、动作、原文位置与安全预览 |  |  |

所有截图均为当前系统实测留痕，不作为外部研究来源。竞品与技术方向页只使用线上官方页面、论文与正式用户交互研究，不生成或伪造竞品运行截图。现场反馈截图只标为“用户反馈样本”，不冒充正式目标用户研究。

---

## IX. Content Outline

### Part 1: 延续 07-16 的主线

#### Slide 01 - Cover

- **Title**: 未来办公 Agent：从一次回答到可治理工作系统
- **Subtitle**: 技术演进、主流方案、办公场景与前台交互影响
- **Layout**: 左侧保留 07-16 的“持续 / 协作 / 治理 / 交付”主张，右侧使用当前 Workspace 实景。

#### Slide 02 - 这次改版带来的能力跃迁

- **Title**: 从“回答与恢复”升级为“持续、协作、治理、交付”
- **Core message**: 延续 07-16 的三段分工：Demo 1 管时间连续性，Demo 2 管复杂任务组织，Demo 3 管动作风险；当前版本把 Workspace、证据和真实成果补进这条链。
- **Content**: 原 07-16 主张、当前真实纵切、尚未实现边界三层；不再放内部文档名作为来源。

#### Slide 03 - 一个底座、两层增强、三类控制

- **Visualization**: `layered_architecture`
- **Content**: 用“什么时候启动、解决什么、用户看到什么”解释三层关系。统一 Agent Runtime 是所有任务共用的状态、执行、证据与审计底座；Agent Control Loop 解决时间维连续性；Governed Adaptive Swarm 解决组织维复杂性；Task / Evidence / Action Control 横切所有层。当前只实现受限单 Loop、固定成果适配器和部分恢复；多 Worker 与真实外部动作仍是目标。

#### Slide 04 - 八个最小运行时模块

- **Visualization**: `icon_grid`
- **Content**: 不再堆八张并列卡片，而把八个模块整理成四段责任链：定范围（Workspace Catalog + Task Contract）、定计划（Planner + Policy Compiler/Validator）、推进与执行（Scheduler/Worker + Tool Gateway）、成果与恢复（Artifact/Verifier + Checkpoint/Event/Governance）。每段同时回答负责什么、用户看到什么、当前实现到哪里。

#### Slide 05 - 技术演进：工程对象不断外扩

- **Visualization**: `chevron_chain_with_tail`
- **Content**: Prompt Engineering → ReAct / Agent Loop → Context Engineering → Harness Engineering → Loop Engineering → 受治理办公交付。保留 07-16 P05–P09 的内容骨架，只用线上论文和官方文档作研究来源。

### Part 2: 主流方案与交互差异

#### Slide 06 - 主流方案的差别，首先是“用户在审什么”

- **Visualization**: `icon_grid`
- **Content**: Microsoft 365 Copilot、ChatGPT deep research、Codex App、Claude Code、OpenClaw、ReAct；按工作内容/研究报告/代码任务/项目会话/Gateway Task/Action-Observation 交互对象叙述，不做能力胜负表。

#### Slide 07 - 技术差异如何改变用户流程

- **Visualization**: `pipeline_with_stages`
- **Content**: Workspace 合同 → 服务端计划编译 → 模型采用门 → Branch 局部恢复 → Artifact/Effect/外部动作分层。每段写用户动作、前台反馈和后端事实。

#### Slide 08 - 长任务 Loop 的六类风险

- **Content**: 方向漂移、上下文退化、错误复利、成本扩张、权限漂移、停止困难；研究依据为 Microsoft HAI Guidelines、ReAct 与持久运行时官方文档。当前最大边界是最多三轮只读 Loop，不是无限反馈驱动执行器。

#### Slide 09 - Agent Control Loop：当前实现与缺口

- **Visualization**: `process_flow`
- **Content**: Observe → Plan → Act → Verify → Commit，外围 Task Contract、Evidence Gate、Budget & Stop、Steer/Pause/Takeover、Durable State、Trace；严格区分“当前真实实现 / 部分近似 / 尚未实现”。

### Part 3: 六个具体办公场景

#### Slide 10 - 六个场景，共用同一条治理主线

- **Visualization**: `vertical_list`
- **Content**: TC-01 入职资产、TC-05 跨期往来款、TC-06 招聘筛选、TC-07 法务授权、TC-10 合规外呼流程、TC-14/15 冲突诊断与模型说明对账。每项列触发、产物、人工门和未执行边界。

#### Slide 11 - TC-01：成果正确，不等于引用定位完整

- **Content**: 触发、用户动作、Agent 路径、停顿、前台输出、后端事实、来源与边界完整展开；先展示可下载资产匹配表，再解释定位问题只影响审计引用，不等于日期或成果失败。

#### Slide 12 - TC-05：三期往来款统计

- **Content**: 三份工作簿共同进入任务，但“未付统计.csv”和“未收统计.csv”只提取最新 2026 期的正数贷/借方余额；“跨期核对说明.md”才比较三个期间。前台必须解释三份成果各自代表什么；僵尸账款、核销和记账均保留财务复核。

#### Slide 13 - TC-06 / TC-07：高影响判断要保留人工门

- **Content**: 招聘场景只形成候选建议与依据，不执行录用/淘汰；法务场景只形成规则台账与风险候选，不代表法律意见或签署动作。引用 Microsoft HAI Guidelines 的能力边界、纠正与控制原则。

#### Slide 14 - TC-10 / TC-14：形成方案，不等于执行动作

- **Content**: 合规外呼只生成流程图/DOCX，不拨号、不写 CRM、不发短信；SRE 只形成条件式诊断与止损提案，不执行 ES 命令、不触发生产降级。前台同时列“已发生”和“未发生”。

#### Slide 15 - TC-15：模型说明不能覆盖确定性成果

- **Content**: 完整 212 行 → 87 组与两份 passed CSV；模型若声称只看 60 行或改写 P0，服务端显示 `called=true` 但 `output_used=false`，只保留一个当前结论。强调这是固定场景一致性验证，不是通用真值证明器。

### Part 4: 前台输出与实操纵切

#### Slide 16 - 前台交互要回答五个问题

- **Content**: 现在完成了什么、依据是什么、为什么停、我确认后会改变什么、什么绝不会发生；把成果置顶、状态可解释、证据可回开、局部决定和未执行边界落到桌面/移动端。研究依据为 Microsoft HAI Guidelines、W3C Status Messages、W3C Target Size 与 Google HEART；当前截图和现场反馈不是正式用户研究。

#### Slide 17 - 我们到底做了什么：一条可核对的办公任务纵切

- **Layout**: 左侧五步纵向链，右侧放当前完整 Run 实景。
- **Content**: 15 个目录、96 份文件的安全资料库；自然语言任务；服务端计划与 Branch；Planner/Analyst 调用和采用回执；真实成果、确定性校验、Snapshot 与有序 Trace。明确当前纵切仍是有界只读研究和固定成果适配器。

#### Slide 18 - 实操 1：用户只说目标，Agent 自主选择资料

- **Layout**: 左侧 2/3 使用完整 Run 截图，右侧依次解释用户动作、服务端事实和前台反馈。
- **Content**: 浏览器不提交 `selected_file_refs`；服务端冻结完整 allowlisted 输入索引；Planner 只看安全元数据并选择本轮证据；前台显示选中资料、模型是否采用、剩余预算和实时 Trace。自主选择不等于穷举正确。

#### Slide 19 - 实操 2：证据有歧义，只恢复受影响的分支

- **Layout**: 大图展示可读性改进后的证据复核页，小图展示不同 Branch 的处理动作。
- **Content**: 用户先看事实、影响、下一步，再在安全预览里确认原文位置；选择只改变目标 Branch，已完成成果和其他 Branch 保留。选择的是来源位置，不是让用户替 Agent 对结论背书。

#### Slide 20 - 实操 3：成果可检查，模型说明不覆盖事实

- **Layout**: 左右并列真实成果/EffectReceipt 与模型说明拒绝态。
- **Content**: 固定场景适配器在隔离 Run 工作区生成文件并执行具名确定性检查；模型 `called=true` 但与确定性结果冲突时 `output_used=false`；前台只保留一个当前结论，审计轨迹保留被拒说明。当前检查不等于通用语义真值证明。

### Part 5: 07-16 三个 Demo 的验收镜头

#### Slide 21 - Demo 1：时间维连续性

- **Content**: 恢复 07-16 P12 的单任务主线：Task Contract → Observe/Plan/Act → Verify 发现 2400 万与 2680 万口径冲突 → 只暂停 revenue-baseline → 用户 Steer → Commit 可追溯工件。对照当前真实实现与仍缺的跨端身份、通用可写成果和长期后台 Worker。

#### Slide 22 - Demo 2：组织维复杂性

- **Content**: 恢复 07-16 P20 的智能工作驾驶舱主线：五类工作信号聚合 → 今日重点与用户调序 → Tool Call / Single Agent / Fixed Workflow / Adaptive Swarm 分流 → Admission、动态 Worker、共享工件、Verifier/Resolver → 结果回到驾驶舱。明确当前没有通用多 Worker Runtime。

#### Slide 23 - Demo 3：动作维风险控制

- **Content**: 恢复 07-16 P21 的 Risk Gate：动作提案 → 影响预演 → Evidence/Risk Lens → L0-L5 → Human Gate → Permit → Execution Receipt。右侧用当前 Effect Gate 实景说明已实现的是成果、确定性效果和未发生边界，不是生产 Connector 执行。

### Part 6: 研究与下一步

#### Slide 24 - 下一阶段：把 07-16 方向变成可证伪证据

- **Visualization**: `chevron_chain_with_tail`
- **Content**: 原生 Locator → 携证成果包 → 通用业务 Verifier → Worker/Tool/Connector → 固定配置竞品挑战与目标用户研究；只有同场任务和用户研究通过后，差异候选才能升级为已验证优势。

---

## X. Speaker Notes Requirements

One speaker note file per page, saved to `notes/`:

- **Filename**: match SVG name, for example `01_cover.md`.
- **Total duration**: 40–45 minutes.
- **Style**: 中文会议主讲，结论先行；每页先说“这页要证明什么”，再说“事实、交互影响、边界”。
- **Source retention**: 竞品、技术演进、交互设计和用户研究页在备注中保留线上官方页面、论文或研究页面的完整 URL；项目事实只标“当前系统实测”并说明测试范围，不把 README、Decision、Scenario 或内部报告列成研究来源。
- **07-16 continuity**: 备注明确哪些判断沿用 07-16，哪些是当前系统实测补充，避免把新增字段名讲成新的产品概念。
- **Boundary discipline**: 使用“当前真实实现 / 部分近似 / 目标设计 / Limited Verified / Draft”等证据标签；避免“全面准确、用户已经更信任、竞品不能做”。

---

## XI. Technical Constraints Reminder

### SVG Generation Must Follow

1. viewBox: `0 0 1280 720`.
2. Background uses `<rect>` elements.
3. Text wrapping uses `<tspan>`; `<foreignObject>` is forbidden.
4. Transparency uses `fill-opacity` / `stroke-opacity`; `rgba()` is forbidden.
5. Forbidden: `mask`, `<style>`, `class`, `foreignObject`, `textPath`, `animate*`, `script`, `iframe`.
6. Use only colors, fonts, icons and images in `spec_lock.md`.
7. Every top-level content group has a descriptive `id`; aim for 3–8 content groups per slide.
8. Real screenshots use `preserveAspectRatio="xMidYMid meet"`; do not crop away evidence context.
9. Chinese text and protocol fields remain editable; no text is baked into screenshots or generated imagery.

### PPT Compatibility Rules

- No `<g opacity="...">`; set opacity on child elements.
- Inline styles only; no external CSS or `@font-face`.
- XML-reserved characters must be escaped; do not use HTML named entities.
- Icons use the synced `tabler-outline` library only, with `stroke-width="2"`.
- Page transitions may use the exporter default; no unsolicited per-element entrance animations.
