# Office Agent - Design Spec

## I. Project Information

- Project Name: Office Agent 系统优化与人机共驾调研
- Canvas Format: PPT 16:9, 1280 x 720
- Page Count: 6 total, without an extra cover
- Target Audience: 项目合作方与评审老师
- Use Case: 约 5 分钟中文阶段汇报
- Delivery Purpose: balanced
- Content Strategy: balanced default, source-grounded compression
- Created Date: 2026-09-12
- Confirmation: chat, 简洁评审风 and recommended A confirmed

## II. Canvas Specification

- viewBox: 0 0 1280 720
- Margins: 48 horizontal, 32 top, 28 bottom
- Header: 32-112. Content: 130-650. Footer: 680.

## III. Visual Theme

- Mode: briefing
- Visual style: swiss-minimal
- Theme: light, flat composition, no decorative cards
- Colors: background #FFFFFF, secondary background #F4F6F8, primary #1557D2, accent/success #008A63, secondary accent/warning #B86A00, body #182230, secondary text #596579, border #DCE2E8.
- Image Rendering: minimalist-swiss
- Image Palette: cool-corporate
- No gradients, shadows, decorative shapes or fixed autonomy levels.

## IV. Typography System

- Chinese title/body/emphasis: Microsoft YaHei. Latin-only text: Arial.
- Title/Body/Emphasis stacks: "Microsoft YaHei", Arial, sans-serif
- Code stack: Consolas, "Courier New", monospace. No code block planned.
- Size slots, unitless: title 44, subtitle 28, body 24, annotation 16, footnote 16, feature 48.
- Available Windows fonts verified in the font registry. No new font installation.

## V. Layout Principles

- P01-02: large original wide screenshots with a restrained side caption.
- P03: original tall screenshot alongside editable explanation of Worker receipts.
- P04: flat four-row research digest, no invented performance chart.
- P05: native editable case table with four scenarios.
- P06: one imagegen framework illustration and concise existing/next-step text.
- Preserve screenshot proportions and full original images. No generated UI or fake before/after.
- Screenshot labels clearly say original system and controlled test data.

## VI. Icon Usage Specification

- No added decorative icons. Original screenshot icons remain unchanged.

## VII. Visualization Reference List

Catalog read: 71 templates

| Page | Template | Path | Summary-quote | Usage |
| --- | --- | --- | --- | --- |
| P05 | basic_table | F:/CodexData/home/skills/ppt-master/templates/charts/basic_table.svg | Pick for plain tabular text/number grid, 3-8 columns. Skip if cells need visual bars (use consulting_table) or qualitative scores (use harvey_balls_table). | Four office cases in a simple editable table |
| P06 | no-template-match | imagegen framework | N/A | Generated conceptual image with original task at its center, not a hierarchy or a new product |

Fewer than 3 visualization pages. Runners-up: comparison_table rejected because cases are not competing products. matrix_2x2 rejected because the boundary has more than two independent dimensions. layered_architecture rejected because Demo1/2/3 are not three runtime layers. P04 is a plain research digest with related prose, not a numerical visualization.

## VIII. Image Resource List

| File | Native dimensions | Page | Acquire Via | Status | Purpose |
| --- | --- | --- | --- | --- | --- |
| images/progress.png | 1672 x 940 | P01 | user | Sourced | Original product progress, 2026-09-11 controlled Snapshot |
| images/evidence.png | 1672 x 940 | P02 | user | Sourced | Original focused evidence review, controlled Snapshot |
| images/swarm.png | 1440 x 1100 | P03 | user | Sourced | Original Swarm partial adoption, 2026-09-12 controlled Snapshot |
| images/copilot-framework.png | 1536 x 1024 | P06 | ai | Generated | Shared office task, Loop, Swarm, human boundary as research integration concept |

Generated image: page_role local, type framework, text_policy embedded only for stable module names. Page title, conclusions and progress wording remain editable.

## IX. Content Outline

### P01 原系统重构：任务进展
- Core message: 原办公资料库和能力页继续保留，共用同一任务状态。
- Cover impact: 原系统任务进展大截图直接证明本轮工作的对象，省去空封面。
- Screenshot: progress.png, original proportions.
- Supporting copy: 执行进展默认展开。待确认事项集中呈现。当前成果与历史保留。
- Visible scope: 原系统截图，受控测试数据，2026-09-11。

### P02 Agent Control Loop：证据核对与局部恢复
- Core message: 用户知道为什么需要确认，以及确认后影响什么。
- Screenshot: evidence.png, original proportions.
- Supporting copy: 两处原文并排核对。无默认选择。只处理相关分支，保留其他成果。
- Visible caveat: 选择依据只记录引用位置，不授予业务或外发权限。

### P03 Adaptive Swarm：分工与贡献采用
- Core message: 协作页展示服务端准入、工作包依赖和实际采用。
- Screenshot: swarm.png, original proportions.
- Supporting copy: 3 条调用，2 条采用。待核对项只影响真实依赖。每批最多 3 个进程内只读 Worker。
- Candidate differentiation: 来源约束、贡献核验、局部恢复与成果历史的组合。
- Caveat: 工程差异候选，尚无竞品同场结果。

### P04 人机共驾调研：四条 Agent 技术线
- Core message: 已梳理 16 篇相关论文，按机制选读，设计推论与论文算法分开。
- Four rows: 选择性求助 / HiL-Bench、SAGE-Agent / 分清自己补做和需要人补口径。
- 多轮反馈利用 / SWEET-RL、Collaborative Gym / 人的回答应改变当前任务与目标成果。
- 执行权限约束 / AgentSpec、AgentDojo / 来源内容不成为指令，动作前核验权限。
- 多 Agent 委派验证 / Intelligent AI Delegation、MAST / 权限不扩大，返回不直接等于采用。
- Caveat: 定向选读，尚未接入论文算法或验证用户收益。

### P05 办公任务中的边界与应对
- Core message: 结合后果、证据、权限、版本和回执决定交互，不采用固定 L0-L5。
- Table columns: 情境 / 边界 / 处理方式 / 当前状态。
- Missing location / 执行缺口 / Agent 先重试，保留成果 / 已有。
- Repeated quote / 证据歧义 / 人选真实位置，过期重核 / 已有。
- UX exactly 3% / 规则冲突 / 保留计算，业务负责人定口径 / 批准待实现。
- Send report / 对外动作 / 保留内部成果，明确未发送 / 外部执行不支持。
- Caveat: 报告文件通过检查，仍可能不满足上线或签署条件。

### P06 Demo3 的整合方向
- Core message: 共驾设计进入同一 Task，沿用原 Loop 与 Swarm。
- Illustration: copilot-framework.png.
- Existing: 原页面已整合边界说明与协作回执。
- Next: 补齐长文本覆盖、业务口径澄清与反馈后的局部更新。
- Evaluation: 测漏问、无谓打扰、反馈利用和越权；另做真人理解测试。
- Closing impact: 同一任务的共享状态与明确决策权作为最终图像锚点，避免新造孤立 Demo。
- Caveat: 图为研究整合示意，Demo3 全场景闭环尚未完成。

## X. Speaker Notes Requirements

- 约 5 分钟，中文平实口语，每页约 40-55 秒。
- 每页保留来源文件或论文链接，不把研究建议写成现有能力。
- 独立 notes/total.md 与 PPT speaker notes 内容一致。

## XI. Technical Constraints Reminder

- Hand-author each SVG sequentially after re-reading spec_lock.md.
- SVG owns layout text and image placement. Generated bitmap owns only internal stable diagram labels.
- Use ppt-master source layout and quality/post-processing workflow. Native PPTX assembly uses JavaScript @oai/artifact-tool to preserve editable text and the case table, avoiding python-pptx as required by the host presentation implementation.
- SVG and native slide geometry must agree. Inspect every final rendered slide.
- Preserve old project files. Final PPTX in exports, private validation outside exports.
