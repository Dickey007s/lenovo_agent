# Execution Lock

## canvas
- viewBox: 0 0 1280 720
- format: PPT 16:9

## mode
- mode: pyramid

## visual_style
- visual_style: data-journalism

## colors
- bg: #F7F8FA
- secondary_bg: #EDF1F4
- surface: #FFFFFF
- primary: #132A3A
- accent: #1769E0
- secondary_accent: #D97706
- text: #1B2733
- text_secondary: #5A6B7C
- text_tertiary: #7C8A98
- border: #CBD5DF
- grid: #E3E8ED
- success: #2E7D32
- warning: #B54708
- danger: #C0362C

## typography
- font_family: &quot;Microsoft YaHei&quot;, &quot;Segoe UI&quot;, Arial, sans-serif
- title_family: &quot;Microsoft YaHei&quot;, &quot;Segoe UI Semibold&quot;, Arial, sans-serif
- emphasis_family: &quot;Microsoft YaHei&quot;, &quot;Segoe UI Semibold&quot;, Arial, sans-serif
- code_family: Consolas, &quot;Courier New&quot;, monospace
- body: 24
- title: 46
- cover_title: 76
- hero_number: 68
- subtitle: 32
- lead: 28
- subheading: 28
- dense_heading: 21
- compact_body: 18
- annotation: 17
- small_body: 16
- compact_annotation: 15
- footnote: 14
- micro: 13

## icons
- library: tabler-outline
- stroke_width: 2
- inventory: folder, folders, search, shield-check, file-text, route, robot, check, circle-check, alert-triangle, refresh, database, versions, user-check, link, server, eye, timeline, lock, activity, git-branch, clipboard-check, briefcase, chart-bar, list-details, message-circle, cpu, arrows-exchange, file-spreadsheet, plug, player-pause, history, quote, target-arrow

## images
- workspace_desktop: images/dr-0022-folder-workspace-desktop.png | no-crop
- tc01_confusion: images/user-feedback-20260828-tc01-artifact-and-citation-confusion.png | no-crop
- tc01_outcome_first: images/dr-0036-tc01-outcome-first-desktop.png | no-crop
- decision_packet: images/dr-0032-decision-packet-desktop.png | no-crop
- artifact_effect: images/scenario-effect-gate-artifact-desktop.png | no-crop
- tc14_sre: images/tc14-sre-diagnosis-desktop.png | no-crop
- tc15_ux: images/tc15-ux-prioritization-desktop.png | no-crop
- reconciliation_desktop: images/narrative-reconciliation-rejected-desktop-1440x1100.png | no-crop
- reconciliation_mobile: images/narrative-reconciliation-rejected-mobile-390x844.png | no-crop
- live_run_completed: images/dr-0036-tc01-live-run-completed.png | no-crop
- effect_gate_full: images/scenario-effect-gate-desktop.png | no-crop
- mixed_branch_actions: images/dr-0034-mixed-branch-actions-desktop.png | no-crop
- review_readability: images/dr-0037-review-readability-desktop.png | no-crop
- capability_progress: images/dr-0058-agent-capabilities-progress.png | no-crop
- adaptive_execution_workspace: images/dr-0058-adaptive-execution-workspace-1440.png | no-crop
- capability_evidence_review: images/dr-0058-agent-capabilities-evidence-review.png | no-crop

## page_rhythm
- P01: anchor
- P02: breathing
- P03: dense
- P04: dense
- P05: dense
- P06: dense
- P07: dense
- P08: dense
- P09: dense
- P10: breathing
- P11: dense
- P12: dense
- P13: dense
- P14: dense
- P15: dense
- P16: dense
- P17: dense
- P18: dense
- P19: dense
- P20: dense
- P21: dense
- P22: dense
- P23: dense
- P24: anchor

## page_charts
- P03: layered_architecture
- P04: icon_grid
- P05: chevron_chain_with_tail
- P06: icon_grid
- P07: pipeline_with_stages
- P09: process_flow
- P10: vertical_list
- P24: chevron_chain_with_tail

## provenance
- narrative_base: 07-16 future office agent deck
- visual_identity: 07-16 light technical briefing; white/light-gray canvas, dark navy titles, blue evidence flow, orange human/risk gates, green adopted outcomes
- research_sources: online official competitor docs, papers, and user-interaction research only
- current_system_evidence: 固定公开场景的受控运行；Demo 2 为受控演示样例
- user_research_boundary: 截图、自动化和现场反馈均不是正式目标用户研究
- research_footer: 页面放可点击官方短链接，完整 URL 保留在演讲者备注 `[Sources]` 区块
- compact_layout: 不保留页顶延续标签、日期、封面计数、空色带或没有独立信息价值的小字说明
- forbidden_source_footer: README, DR, Scenario, Evidence, Detailed Chinese Report, internal document paths

## forbidden
- Mixing icon libraries
- rgba()
- `<style>`, `class`, `<foreignObject>`, `textPath`, `@font-face`, `<animate*>`, `<script>`, `<iframe>`, `<symbol>`+`<use>`
- `<g opacity>`
- HTML named entities in text
