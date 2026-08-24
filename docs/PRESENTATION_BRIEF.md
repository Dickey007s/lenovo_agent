# Office Agent V0.2 Presentation Brief

## 1. One-sentence position

Office Agent turns a pinned public office dataset into a user-operated workbench: inspect data, choose context, ask a task, then verify two model receipts, server checks, file citations and the no-external-action boundary.

## 2. Reporting rule

Every slide must pass [DECISION_AND_REPORTING_GOVERNANCE.md](DECISION_AND_REPORTING_GOVERNANCE.md): 场景与来源、前台交互影响、后端事实映射、验证与边界. Historical Customer A or DR-0016/0017 facts cannot be presented as the current workbench.

## 3. Recommended story

| Slide | Core message | Visual/evidence | Boundary |
| --- | --- | --- | --- |
| 1. User problem | too much explanation and Demo framing hide the user's real work | verbatim Feedback 10 | one stakeholder, not research |
| 2. Mainstream baseline | tools, permissions, sessions and delegation are already mainstream | official-material comparison | not competitor testing |
| 3. Product thesis | business source, user-owned task, verifiable trace and semantic impact | four-pillar diagram | differentiation/value still Draft |
| 4. Data workbench | actual benchmark data is the first screen | DR-0018 result desktop screenshot | replayed persisted Snapshot, not a new model call |
| 5. Real source | pinned FORTE bytes become stable safe refs and previews | source/preview diagram | public benchmark, not enterprise database |
| 6. Two-call loop | Planner then Analyst, each with independent receipt | running desktop screenshot + eight events | screenshot is second live Run around 1.8s |
| 7. Result truth | citations can pass while the numerical answer is wrong | desktop/mobile result screenshots + deterministic 23 / `1,845,444.71` versus model 20 / `2,202,000` | `completed` is not a quality pass |
| 8. Frontend/backend alignment | every state maps to a field or named event | UI—server fact matrix | no animation/CoT as fact |
| 9. Eight modules | current and target capabilities stay separate | maturity table | modules 5-6 and durable Artifact remain Draft |
| 10. Three policies | finance, release and operations share one work contract | three collection examples | not three independent completed Demos |
| 11. Engineering evidence | code, focused tests, live records and screenshots have distinct roles | Evidence ledger | engineering checks do not prove user value |
| 12. Next proof | semantic verifier, durable Artifact, Scheduler, action governance, user study | phased roadmap | no production/value claim |

## 4. Technical comparison wording

Use:

> OpenClaw, Codex and Claude Code official materials show that tool use, permissions, sessions, background work and delegation are already mainstream. Our target distinction is the office user's control surface: choose business data, define the task, inspect what was called and validated, review cited outputs, and see the effect boundary.

Do not claim competitors “cannot” support an untested capability, Office Agent is “first”, or the workbench is safer/faster/easier without comparative and user evidence.

## 5. Current demo narration

1. Open `FORTE 数据工作台`; do not begin with architecture prose.
2. Browse an actual table or Markdown input and point out the public benchmark label.
3. Check the files that should define the task context.
4. Write a new question and run it.
5. Follow eight named stages and distinguish planning call, plan validation, analysis call and citation validation.
6. Open the result. By default the summary and only three findings are visible; “展开结论” and “查看其余7条发现” are explicit user choices.
7. Read the title “模型初步结论 · 待复核” and explain that the server checked file references and the read-only boundary, not the numerical conclusion.
8. Close on `completed`: an initial response exists in memory and passed schema/reference/boundary checks; the negative deterministic comparison shows it was not numerically correct, it requires review, and no external action occurred.

Never call displayed plan tool labels “executed tools”. Never call the result an Artifact Commit.

## 6. Screenshot provenance

| Screenshot | Provenance | Allowed use | Prohibited inference |
| --- | --- | --- | --- |
| [`dr-0018-data-workbench-running-desktop.png`](evidence/screenshots/dr-0018-data-workbench-running-desktop.png) | second real Run `harness:f3a071...`, captured around 1.8s; final Run later completed v9/seq 8 | show real in-progress trajectory and receipt waiting states | not timing benchmark or proof of background execution |
| [`dr-0018-data-workbench-result-desktop.png`](evidence/screenshots/dr-0018-data-workbench-result-desktop.png) | prior real Run `harness:8c9...` persisted Snapshot replayed into the formal UI by browser POST | show final desktop projection of a real persisted Snapshot | not a third model call or cross-restart/history recovery |
| [`dr-0018-data-workbench-result-mobile.png`](evidence/screenshots/dr-0018-data-workbench-result-mobile.png) | same replayed `harness:8c9...` Snapshot at 390px; no horizontal overflow | show mobile engineering layout | not a mobile user study |

Console/page errors were 0 for these captures. Exact hashes and dimensions are in [DR-0018 Evidence](evidence/FORTE-DATA-WORKBENCH-TRACE-EVIDENCE-20260824.md).

## 7. Evidence ledger

| Claim | Status | Evidence | Cannot imply |
| --- | --- | --- | --- |
| seven-path data workbench | Limited Verified | `fffa36a...` + `041186d`, focused Python `30 passed` | production readiness |
| browse/select/custom task | Limited Verified | focused browser `8 passed in 26.8s` + screenshots | user comprehension |
| two real model calls | observed | two live Run records | quality, repeatability or SLA |
| cited initial result | Limited Verified | v9/seq 8 Snapshot facts and manifest | semantic/numeric correctness |
| deterministic negative comparison | Verified regression fact | public-preview test reproduces 23 / `1,845,444.71` | a Runtime semantic verifier already exists |
| no external effect | current boundary | Runtime/events/result footer | future Connector governance |
| reduced text improves clarity | Draft | no target-user study | usability claim |

Final verification is Python `53 passed in 2.68s`, Ruff and web lint passed, and the production build passed (`2.5s` compile, `4.4s` TypeScript, `810ms` static generation). [PR #25](https://github.com/Dickey007s/lenovo_agent/pull/25) is open and not yet merged.

## 8. Source trail

- [Source Register](decisions/SOURCE_REGISTER.md)
- [Stakeholder Feedback 10](sources/USER-FEEDBACK-20260824-10-data-workbench-and-trace.md)
- [DR-0018](decisions/DR-0018-forte-data-workbench-and-verifiable-trace.md)
- [DR-0018 Evidence](evidence/FORTE-DATA-WORKBENCH-TRACE-EVIDENCE-20260824.md)
- [FORTE audit](research/FORTE-DATASET-AUDIT-20260824.md)
- [Competitor research](research/COMPETITOR-RESEARCH-OPENCLAW-CODEX-CLAUDE-CODE-20260821.md)
