# SCENARIO-007: Single FORTE data workbench entry and recovery

| Field | Value |
| --- | --- |
| Scenario ID | `SCENARIO-007` |
| Status | `Limited Verified` for the current engineering path; comprehension, result quality and user value `Draft` |
| Decisions | [`DR-0017`](../decisions/DR-0017-single-forte-worksite-and-legacy-retirement.md), [`DR-0018`](../decisions/DR-0018-forte-data-workbench-and-verifiable-trace.md) |
| Sources | `USER-FEEDBACK-20260824-FORTE-ONLY-09`, `USER-FEEDBACK-20260824-DATA-WORKBENCH-10` |

## Target user and trigger

The target user is a product or technical reviewer who needs to inspect public office data, define an analysis question and understand what the Agent actually did. The scenario starts at `/`, with or without a reachable API and valid FORTE Catalog.

## Current pain

The former product led with Demo framing and explanatory copy. It did not make benchmark data, user-selected context or a user-authored task the primary work. A planning-only terminal also left the user without an answer. When the Catalog failed, an unclassified fetch error made service failure and source-integrity failure hard to distinguish.

## Goal and completion condition

The first screen is one FORTE data workbench. The user can browse a bounded preview, choose files, write an instruction, follow two independently receipted model calls and inspect a cited read-only result. The current successful Run ends at `completed` v9/seq 8 only after schema and selected-reference checks; it still requires human review and performs no external action. Completion does not mean the finding text or arithmetic is correct.

## Frontend journey

1. The workbench loads three business-labeled FORTE collections and their safe file labels.
2. The user searches, selects and previews allowlisted table or Markdown content.
3. The user writes an original task and starts an idempotent Run over the selected `file_ref` values.
4. The right rail follows eight named server events and shows separate Planner and Analyst receipts.
5. The center shows the validated plan, then “模型初步结论 · 待复核”; three findings are visible by default and the remaining findings require an explicit expand action.
6. The terminal boundary says an initial result is available in memory, file references were checked, numbers still need human verification and no external action occurred.

## Server fact matrix

| Situation | Server/client fact | UI response | Recovery boundary |
| --- | --- | --- | --- |
| Initial load | health + Scenario list | one workbench and three collections | no static fallback Scenario invented |
| File browse | preview route for Scenario + stable `file_ref` | bounded real table/Markdown projection | no path/hash/raw task disclosure |
| User task | POST instruction + selected refs | show the user's task and selected-source scope | server revalidates unique in-Scenario refs |
| Planner | `planning_started/completed`, `model_receipt` | show call/adoption receipt separately from validation | animation is not call evidence |
| Plan check | `plan_validation` and public plan | show accepted work graph | plan tool labels are not executed tools |
| Analyst | `analysis_started/completed`, `analysis_receipt` | show second independent call/adoption receipt | no Prompt, chain of thought or raw response |
| Result check | `result_validation`, `review_required=true` | show citations and human-review warning | validates ref membership, not semantics or arithmetic |
| Terminal response | `completed`, version 9, sequence 8, `task_completed` | “初步结果已形成”; new task remains possible | no correctness, Artifact, Tool, Connector or business-completion claim |
| API offline | health/fetch failure | offline/recovering state | bounded retry and explicit retry |
| Catalog integrity invalid | controlled 503 | “工作场景需要更新” | fail closed until source bytes are repaired |
| Stream interruption | nonterminal EventSource error | reconnecting and `after=N` resume | terminal state reconciles with final GET |

## Hidden details

The ordinary UI hides raw `task.md`, Planner/Analyst Prompt, chain of thought, raw model output, rubric, solution, absolute path, full hash, internal source IDs, credentials and lower-level logs. Demo IDs are not foreground navigation. The old Customer A dataset and legacy route names do not appear in the current DOM or public API.

## Evidence boundary

Current focused E2E covers browsing, selection, custom instruction, two receipts, ordered streaming, recovery, fail-closed behavior and the 390px layout. The running screenshot records an actual second live Run; the result screenshots replay a previously persisted real Snapshot into the same formal UI and do not prove a third model call or product history recovery. A deterministic Finance cross-period regression also demonstrates that the observed model result was numerically wrong, so `completed` cannot be presented as correctness. See [`FORTE-DATA-WORKBENCH-TRACE-EVIDENCE-20260824`](../evidence/FORTE-DATA-WORKBENCH-TRACE-EVIDENCE-20260824.md).

These engineering checks and one Stakeholder feedback record are not target-user research. Whether users understand the trace, trust the right facts, find the page less dense or complete real work more effectively remains `Draft`.
