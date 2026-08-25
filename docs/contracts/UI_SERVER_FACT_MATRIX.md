# UI-server fact matrix

This is the current `DR-0025` recoverable loop plus the `DR-0024`
whole-workspace workbench. Historical manual-selection/Scenario/Task mappings
remain in their dated Evidence only.

下表中的 Authority 列即“服务端权威字段”；浏览器草稿与传输状态会明确另列，
不能冒充业务事实。
Prompt、思维链、原始模型响应、绝对路径、哈希和内部策略标识在普通界面默认隐藏。

## 1. File-manager workspace and task draft

| UI state/action | User-visible meaning | Authority | Transition/recovery/idempotency | Hidden |
| --- | --- | --- | --- | --- |
| Service available | HTTP API and workspace projection succeeded | health/workspace response | may browse or start; not an SSE fact | previous stream, network stack |
| Workspace unavailable | service or catalog cannot provide authoritative files | fetch failure or controlled 503 | retry; no static fallback files | stack trace, partial/stale catalog |
| Whole repository | one flat list of 96 public inputs | `GET /v1/harness/workspace` | read-only until refreshed | task prompt, rubric, solution, role partitions, path/hash |
| Search/type filter | client filters the visible file-manager list | browser state | no server mutation and no scope change | no capability claim |
| File preview selection | choose what the user is looking at | browser state + preview GET | does not constrain Agent evidence | internal ref/path/hash |
| Task composer | user writes the actual instruction | browser draft; POST/Snapshot `instruction` | required 3-2,000 chars | hidden benchmark-task fallback is forbidden |
| Loop bounds | user chooses hard limits before invocation | browser draft; Snapshot `contract.options` | rounds 1-3, files/round 1-8, model calls 2-6, deadline 20-300s | token/cost estimates not owned by server |
| Run start | server accepted one independent read-only whole-workspace contract | POST Owner/key/version/instruction/options | unknown response reuses same key; changed or known retry uses new key | internal command signature |
| Frozen active contract | current instruction, all stable refs and limits cannot silently change | Snapshot `scope_mode/allowed_file_refs` and run-active state | composer/options disabled until terminal | local edits pretending to affect active Run |

## 2. File preview

| UI state/action | User-visible meaning | Authority | Transition/recovery | Hidden |
| --- | --- | --- | --- | --- |
| Metadata | business path, type, bytes, row/page count | workspace/file projection | selecting file triggers preview GET only | raw relative/absolute path and digest |
| Table preview | bounded XLSX/CSV rows | preview response | parser/integrity failure replaces content | macros/formula execution/full workbook internals |
| Document preview | bounded DOCX/PDF text | preview response | encrypted/unsafe/unsupported is unavailable | embedded active content/external loads |
| Text preview | bounded TXT/MD/JSON/log/code | preview response | displayed only, never executed | shell/script execution |
| Security footer | integrity verified, read-only, no active/external resource execution | `BenchmarkPreviewSecurity` | cannot be inferred from extension alone | scanner implementation details |
| Citation click | reopen a finding's selected source | result `file_ref` resolved through workspace | selects file and switches to preview | source path/hash |

## 3. Agent Control Loop, plan and result

| UI state | User-visible meaning | Authority | Ordered transition | Hidden |
| --- | --- | --- | --- | --- |
| Whole index frozen | the Run can search the complete allowlisted repository | `workspace_index`, `contract.scope_mode`, `source_documents[]` | seq 1 | internal path/hash/file bodies |
| Round started | another bounded Observe cycle began | `round_started`, `rounds[]` | round number and remaining budget increase monotonically | hidden subtask prompt |
| Planner started/returned | provider call stage, not acceptance | `planning_started/completed` | per round | Prompt, CoT, raw candidate |
| Planner receipt | not called/adopted/not adopted and elapsed time | round `model_receipt.called/output_used/elapsed_ms` | independent of plan validation | token/provider trace |
| Candidate rejected | returned candidate was not adopted | `plan_validation_rejected` | at most one repair using the same call budget | raw validator/provider error |
| Validated plan | server compiled/accepted this round's work intent | `plan_validation`, round public plan | after accepted candidate only | raw tool/effect/gate IDs |
| Agent-selected evidence | files chosen for this round and business reason | `round.input_file_refs`, `plan.selection_reason` | after server budget/compiler validation | full metadata index, model ranking internals |
| Analyst started/returned | provider analysis stage, not completion | `analysis_started/completed` | per round | Prompt, CoT, raw response |
| Analyst receipt | not called/adopted/not adopted and elapsed time | round `analysis_receipt.*` | independent of result validation | token/provider trace |
| Citation validation | every finding stays inside this round's approved refs | `result_validation` | before Evidence Gate | false semantic/numeric proof claim |
| Evidence gap | current evidence is insufficient and another round has a bounded purpose | `evidence_gaps[]`, `evidence_gate`, `next_step=waiting_input` | prior round/version remains visible; no new call starts until resume | claim that the missing file guarantees truth |
| Continue confirmation | user authorizes one more bounded round over the displayed missing evidence | control POST `resume`, returned version and ControlEvent; next `round.input_file_refs` equals prior Gate candidates | only valid from server-paused Evidence Gate; validator requires all confirmed refs | a click animation as execution proof or unrelated files silently entering the round |
| Result version | one completed round formed a logical evidence brief | `artifact_versions[]` and round result | version and parent increase monotonically inside the Run | standalone immutable artifact or source-file write |
| Read-only Act | the Agent formed an intermediate analysis, not a side effect | round result and `external_side_effect=none` | Verify follows in the same round | tool execution or source-file mutation claim |
| Completed | server Gate committed the latest logical version and a reviewable brief | `status=completed`, `loop_committed`, `brief`, `last_commit` | final GET after terminal event | standalone TaskCommit, tool execution, business correctness |
| Budget stopped | no new provider call may start | `status=stopped`, `brief.outcome=bounded`, `loop_budget_stopped` | preserves completed rounds and partial brief | hard cancellation of an in-flight HTTP call |
| User stopped | stop was applied at a safe point | `status=stopped`, `loop_stopped` | preserves completed rounds | rollback or deletion claim |
| Safely stopped | model/schema/plan/source/citation check failed | `status=failed`, `harness_failed`, safe errors | no result; fresh retry | raw validator/compiler/provider error |
| Next-task proposals | Agent suggests up to four follow-up tasks from the current bounded analysis; each proposal is not independently source-verified | terminal `result.follow_ups` | suggestion alone creates no server mutation | claim that work already started or that every proposal has a per-item citation |
| Confirm proposal | user turns one suggestion into an independent new Loop | new POST `/v1/harness/runs` with exact proposal text | new idempotency key; previous Run/result preserved | nonexistent proposal-accept state |

## 4. Human control

| UI action/state | User-visible meaning | Authority | Transition/recovery/idempotency | Hidden |
| --- | --- | --- | --- | --- |
| Pause | request a stop at the next safe point | control POST `pause`, returned Snapshot/ControlEvent | expected version + idempotency; does not cancel an in-flight model call | local instant-pause fiction |
| Resume | continue a paused Run | control POST `resume` | only from server-paused state | browser-only state change |
| Steer next round | record a direction for the next round | control POST `steer`, `pending_steer`/ControlEvent | does not rewrite an already accepted round | claim that current result changed immediately |
| Stop and keep | terminate at a safe point and preserve work | control POST `stop`, terminal Snapshot | idempotent replay returns original command result | deletion/rollback claim |
| Version conflict | another fact is newer than this control | HTTP 409 + current Snapshot reconciliation | refresh, review, submit a new command | field-level merge not implemented |

## 5. Preview and validation limits

| Fact | Current guarantee | Not guaranteed |
| --- | --- | --- |
| workspace inventory | 15 folders, 96 input refs from pinned manifest | unpublished FORTE tasks or live enterprise drive |
| XLSX/CSV | first visible sheet/CSV, <=30 columns, <=120 rows | arbitrary workbook features or formula truth |
| DOCX/PDF/TXT | bounded extracted/read text, <=30,000 chars | OCR completeness, layout fidelity or semantic accuracy |
| stable ref | deterministic for pinned public input path | production document identity |
| plan compilation | server-owned effects/gates plus graph/source checks and one bounded repair | plan quality or tool execution |
| result validation | citation membership in the server-approved round set | entailment, exhaustive matching or arithmetic |
| Evidence Gate | decides continue/stop from explicit gaps and remaining bounds | semantic truth or human acceptance |
| completed | reviewable logical brief/Commit exists in the authoritative Run Snapshot | task correctness, standalone immutable Artifact, Connector or external process completion |

## 6. Transport and lifecycle

- Snapshot version and event sequence never decrease in the browser.
- A terminal event requires final GET; a nonterminal disconnect uses GET plus
  `after=N`.
- “trajectory live” requires an open current EventSource; “service available”
  only requires successful HTTP.
- Missing/wrong-owner Run returns the same 404.
- `X-User-Id` is unsigned. With `DATABASE_DSN`, Snapshot and command receipts
  are PostgreSQL-backed; without it they remain one-process memory.
- `checkpoint_recovered` proves a persisted Snapshot was restored and paused.
  It does not prove an interrupted model call was cancelled or replayed.
- Plan operation labels and read-only Act declare intent/analysis. The current
  Runtime does not invoke a Tool Gateway or modify source files. Its logical
  versions are embedded in the Run, not independently immutable records.
- Pause/stop apply between provider calls; deadline prevents a new call but does
  not hard-cancel an in-flight request.
- Browser refresh restores a known Run id; `GET /runs` can discover the latest
  nonterminal Owner Run. There is not yet a full history chooser.

## 7. Evidence and applicability

Current contract: [`DR-0025`](../decisions/DR-0025-durable-evidence-gate-and-artifact-evolution.md),
[`DR-0024`](../decisions/DR-0024-autonomous-whole-workspace-research.md),
[`DR-0023`](../decisions/DR-0023-agent-control-loop.md),
[`SCENARIO-010`](../scenarios/SCENARIO-010-autonomous-whole-workspace-research.md),
[`SCENARIO-009`](../scenarios/SCENARIO-009-agent-control-loop.md),
[workspace interaction/source record](../research/WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825.md)
and [current whole-workspace Evidence](../evidence/AUTONOMOUS-WHOLE-WORKSPACE-RESEARCH-EVIDENCE-20260825.md).

Automated checks are engineering proxies, not user research. User
comprehension, calibrated trust and task value remain `Draft`.
