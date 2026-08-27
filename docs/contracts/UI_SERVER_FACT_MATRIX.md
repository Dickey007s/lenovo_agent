# UI-server fact matrix

This is the current `DR-0034` one-action recovery and explicit source-choice
surface, on top of the `DR-0033` closable Branch-lane review, `DR-0032`
persistent decision/recovery contract, `DR-0029`
server-verified Evidence Anchors and `DR-0026`
branch-selective append-only result loop and `DR-0024` whole-workspace contract.
`DR-0025` group-resume and embedded-artifact facts remain a historical baseline
in their dated Evidence only.

下表中的 Authority 列即“服务端权威字段”；浏览器草稿与传输状态会明确另列，
不能冒充业务事实。
Prompt、思维链、原始模型响应、绝对路径、哈希和内部策略标识在普通界面默认隐藏。

## 1. File-manager workspace and task draft

| UI state/action | User-visible meaning | Authority | Transition/recovery/idempotency | Hidden |
| --- | --- | --- | --- | --- |
| Service available | HTTP API and workspace projection succeeded | health/workspace response | may browse or start; not an SSE fact | previous stream, network stack |
| Workspace unavailable | service or catalog cannot provide authoritative files | fetch failure or controlled 503 | retry; no static fallback files | stack trace, partial/stale catalog |
| Whole repository tree | 15 top-level folders, nested subfolders and 96 public inputs | `GET /v1/harness/workspace` `folders[]` + safe file `display_path` | tree projection is read-only until refreshed | task prompt, rubric, solution, role partitions, raw path/hash |
| Expand/search/type filter | client changes visible branches of the file tree; search keeps matching ancestors open | browser state over server projection | no server mutation and no Agent scope change | no claim that visible files are the Run input |
| File preview selection | choose what the user is looking at | browser state + preview GET | does not constrain Agent evidence | internal ref/path/hash |
| Task composer | user writes the actual instruction | browser draft; POST/Snapshot `instruction` | required 3-2,000 chars | hidden benchmark-task fallback is forbidden |
| Loop bounds | user chooses hard limits before invocation | browser draft; Snapshot `contract.options` | rounds 1-3, files/round 1-8, model calls 2-6, deadline 20-3000s | token/cost estimates not owned by server |
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
| Review-page source switch | compare one Gap/Finding with an associated safe file | Gap/Finding refs resolved through workspace + Preview GET | changes only the review-page preview; Run version is unchanged | source file mutation, semantic proof, raw ref/path/hash |
| Finding evidence selection | jump to one server-verified source location | Finding `evidence_anchors[].file_ref/locator_kind/start/end` + Preview GET | browser switches file, scrolls and highlights; Run version is unchanged | client-guessed position, source Diff or semantic proof |

## 3. Agent Control Loop, plan and result

| UI state | User-visible meaning | Authority | Ordered transition | Hidden |
| --- | --- | --- | --- | --- |
| Whole index frozen | the Run can search the complete allowlisted repository | `workspace_index`, `contract.scope_mode`, `source_documents[]` | seq 1 | internal path/hash/file bodies |
| Round started | another bounded Observe cycle began | `round_started`, `rounds[]` | round number and remaining budget increase monotonically | hidden subtask prompt |
| Planner started/returned | provider call stage, not acceptance | `planning_started/completed` | per round | Prompt, CoT, raw candidate |
| Planner receipt | not called/adopted/not adopted and elapsed time | round `model_receipt.called/output_used/elapsed_ms` | independent of plan validation | token/provider trace |
| Candidate rejected | returned candidate was not adopted | `plan_validation_rejected` | at most one repair using the same call budget | raw validator/provider error |
| Validated plan | server compiled/accepted this round's work intent | `plan_validation`, round public plan | after accepted candidate only | raw tool/effect/gate IDs |
| Task branches | validated work units now have server-owned identity, dependency and evidence state | `branches[]`, `round.branch_ids` | created after plan validation; state changes only through server verification/control | Branch ID generation and validator internals |
| Agent-selected evidence | files chosen for this round and business reason | `round.input_file_refs`, `plan.selection_reason` | after server budget/compiler validation | full metadata index, model ranking internals |
| Analyst started/returned | provider analysis stage, not completion | `analysis_started/completed` | per round | Prompt, CoT, raw response |
| Analyst receipt | not called/adopted/not adopted and elapsed time | round `analysis_receipt.*` | independent of result validation | token/provider trace |
| Citation and location validation | every Finding stays inside this round's approved refs and has at least one quote uniquely resolved in the exact bounded source | `result_validation`, `result.findings[].evidence_anchors` | before Evidence Gate; model quote candidates are removed before public projection | false semantic/numeric proof claim, raw quote candidate or model-supplied line number |
| Evidence gap Branch lane | the Agent has not produced an adoptable result for one or more bounded Branches; the header says how many are waiting and each row distinguishes “无需核对文件，建议重试” from “需要从 N 个原文位置中选 1 个” | `branches[]` joined by `evidence_gaps[].branch_id`; Branch input/verified/missing refs; top-level `decision_requests[]`; `EvidenceResolution.status/candidates[]` | prior rounds/branches/versions remain visible; opening is read-only; only a versioned Branch decision/resume creates work | claim that visual lanes prove parallel Workers, a candidate file is wrong or the evidence guarantees truth |
| Agent gap recovery sheet | retry-only user sees one recommended Branch action before optional explanation; ambiguous user first sees why a human is needed, what to select and what happens next | latest Round `next_step.recovery_kind`, bound Branch objective/status/input/verified refs, Gap candidates, EvidenceResolution and Planner/Analyst `called/output_used` | opening has no mutation; optional clue and audit/Preview are collapsed; waiting Run may steer then resume only that Branch; terminal Run creates a new task | raw validator text, invented row/highlight, mandatory source edit, mandatory feedback or replay of a terminal provider call |
| Retry-only Branch action | user can continue one recoverable Branch without editing files or filling an answer | waiting Branch + non-ambiguous Gap/Resolution + recovery mode; control POST `resume(branch_id)` and optional prior `steer` | primary action is unique; opening does not call a model or charge the next round; unselected Branches remain waiting | automatic retry, hidden budget spend, all-Branch resume |
| Gap/Branch review page | user can inspect where the gap occurred, what it says and which candidate/missing files are available | `round_number`, business Branch title, `evidence_gaps[]`, Branch `missing_file_refs`, Preview GET | open has no mutation; close/Escape exits immediately, then attempts a versioned `defer` only for an open structured decision; a 409/error stays visible outside the closed dialog and does not claim a receipt | raw Branch ID, claim that candidate files solve the gap, invented diff or trapping the user until a network write succeeds |
| Continue one Branch | user authorizes one more bounded round only for the selected Branch | control POST `resume` with `branch_id`, returned ControlEvent, `active_branch_id`; next `round.input_file_refs` equals that Branch's missing refs | only valid for a waiting Branch; all other waiting Branches remain unchanged | a click animation as execution proof or unrelated files silently entering the round |
| Result version | one completed round formed an independent append-only logical evidence brief | `artifact_versions[]` safe projection plus Store ArtifactVersion row | version and parent increase monotonically; content is not overwritten | source-file write, semantic correctness or mutable current-result fiction |
| Read-only Act | the Agent formed an intermediate analysis, not a side effect | round result and `external_side_effect=none` | Verify follows in the same round | tool execution or source-file mutation claim |
| Completed | server Gate created a separate TaskCommit selecting the latest verified logical brief | `status=completed`, `loop_committed`, `brief`, `commits[]`, `last_commit` | final GET after terminal event; ArtifactVersion is not mutated | source-file commit, tool execution or business correctness |
| Historical version restored | current brief pointer moved to an existing version and history remains | `artifact_version_restored`, rollback TaskCommit, `last_commit.artifact_version` | versioned/idempotent control; versions and prior Commits never decrease | file rollback, deleted work or model-call undo |
| Active-time budget | time is charged only while the Agent is running | Contract `deadline_seconds`, Snapshot `budget.elapsed_ms`, Runtime active/frozen state | defaults to 1,200 seconds; freezes in waiting/pause/terminal and resumes from accumulated active elapsed | wall-clock age, reset-on-resume or hard cancellation of an in-flight HTTP call |
| Budget stopped | no new provider call may start and the concrete boundary is visible | `status=stopped`, `brief.outcome=bounded`, `budget.stop_reason`, `loop_budget_stopped` | preserves completed rounds and partial brief | raw `budget_exhausted` as the only explanation, hard cancellation of an in-flight HTTP call |
| Continue after bounded stop | the terminal Run cannot resume; one unresolved Branch may seed a new Task Contract | `status=stopped`, latest `next_step.recovery_kind/candidate_branch_ids`, Branch objectives/refs, preserved `artifact_versions[]`; then a new Run POST | add optional direction and create an independent whole-workspace Run for one Branch objective | `resume` on the terminal Run, mutation of the old Run, guaranteed reuse of prior file selection or external action |
| User stopped | stop was applied at a safe point | `status=stopped`, `loop_stopped` | preserves completed rounds | rollback or deletion claim |
| Safely stopped | model/schema/plan/source/citation check failed | `status=failed`, `harness_failed`, safe errors | no result; fresh retry | raw validator/compiler/provider error |
| Next-task proposals | Agent suggests up to four follow-up tasks from the current bounded analysis; each proposal is not independently source-verified | terminal `result.follow_ups` | suggestion alone creates no server mutation | claim that work already started or that every proposal has a per-item citation |
| Finding review page | user compares one Agent finding with exact server-resolved safe-preview locations | `result.findings[].title/detail/file_refs/evidence_anchors`, matching Artifact round when available, Preview GET | select Anchor/open/close has no server mutation | semantic/numeric correctness, entailment, native PDF/DOCX coordinates |
| Finding handling sheet | user scans fact, impact and whether a human business choice is required | Finding `fact_summary`, `impact`, `review.requires_human_decision/question/why_human` | view/expand does not mutate the Run | claim that the model framing or impact is correct |
| Finding decision options | user first chooses a handling path, then may reveal and compare the Agent recommendation | Finding `review.options[]` with Branch/source/round/action impacts, `recommended_option_id`, `recommendation_reason`; browser selection/reveal state | selecting/revealing is browser draft only; recommendation is hidden before initial choice | approval, policy-optimality, source-file change or action execution |
| Record a Finding choice | user accepts, declines, defers or cancels one Finding and may add feedback | versioned/idempotent `command=decision`; top-level Snapshot `decision_requests[]`; `decision_records[]`; `decision_recorded` | close/Escape first exits and then attempts `defer`; defer remains actionable; failed defer is an explicit non-blocking error; cancel closes the packet without pretending the evidence was rejected; accept binds one owned option | file edit, external action, approval correctness, automatic follow-up or a failed defer presented as recorded |
| Start accepted Finding work | an accepted option becomes a new independent task | new Run POST containing selected `next_instruction`, decision label and feedback after the receipt succeeds | new idempotency key; prior Run/result/DecisionRecord stays immutable | mutation of the old Run or continuation of an in-flight provider call |
| Evidence location state | user sees whether a quote has one, many, no current match, a changed source or a rejected candidate | `next_step.evidence_resolutions[]`: `exact/ambiguous/unavailable/stale/rejected`, source revision and candidate IDs | compare real positions; accept, decline, defer, cancel, supplement a source hint or retry only the bound Branch | semantic entailment, invented coordinates, raw digest or source hash |
| Partial analysis adopted | only Findings with server-resolved Anchors become public; unresolved records stay actionable | `analysis_partial_adopted`, `partial_artifact_saved`, Artifact findings, EvidenceResolution and Branch status | review retained Findings; open unresolved candidates separately | content or correctness of omitted Findings |
| Analysis recovery required | two bounded attempts yielded no adoptable Finding/structure but legal scope and prior work remain | `analysis_recovery_required`, Round `next_step.recovery_kind`, candidate Branches, `status=waiting_input` | add steer text and resume one waiting Branch | result acceptance, model not called or file modified |
| Candidate disambiguation | one quote matches multiple real positions and requires one human source-location choice | `evidence_disambiguation_required`, `EvidenceResolution(status=ambiguous).candidates[]`, open DecisionRequest | compare source positions; no default candidate; accept stays disabled until one candidate is selected, then versioned/idempotent decision resumes only the bound Branch | server or Agent chose for the user, random location, other Branches reran |
| Resume recovery Branch | selected evidence decision is consumed at a safe checkpoint | `DecisionRequest`, `decision_recorded`, `branch_resumed_from_checkpoint`; optional `control_steer_recorded` for user feedback | continue only the bound waiting Branch; reconnect from Snapshot/SSE; v1 remains while resumed work appends v2 | lost ArtifactVersion, replay of completed Branches or external action |
| Legacy terminal analysis failure | an older Run stopped before the recoverable protocol existed | `status=failed`, safe validation error, preserved instruction/Plan/Branch/call facts | create a new smallest-scope Run | interrupted call resumed or failed output adopted |
| Proposal context review | user sees the result context before deciding whether to start the suggestion | one `result.follow_ups[]` string + union of current Finding refs | explicitly labeled not independently source-verified; no mutation | direct per-proposal citation or accepted-proposal state |
| Confirm proposal | user turns one suggestion into an independent new Loop | new POST `/v1/harness/runs` with exact proposal text | new idempotency key; previous Run/result preserved | nonexistent proposal-accept state |

## 4. Human control

| UI action/state | User-visible meaning | Authority | Transition/recovery/idempotency | Hidden |
| --- | --- | --- | --- | --- |
| Pause | request a stop at the next safe point | control POST `pause`, returned Snapshot/ControlEvent | expected version + idempotency; freezes active elapsed at the safe point and does not cancel an in-flight model call | local instant-pause fiction |
| Resume | continue a paused Run | control POST `resume` | only from server-paused state; restarts active elapsed without charging paused time | browser-only state change or deadline reset |
| Steer next round | record a direction for the next round | control POST `steer`, `pending_steer`/ControlEvent | does not rewrite an already accepted round | claim that current result changed immediately |
| Stop and keep | terminate at a safe point and preserve work | control POST `stop`, terminal Snapshot | idempotent replay returns original command result | deletion/rollback claim |
| Restore result version | select a historical logical brief without overwriting history | control POST `rollback` with `artifact_version`; returned Snapshot/ControlEvent | completed committed Run only; expected version + idempotency; appends a TaskCommit | original file rollback or deletion of newer ArtifactVersion |
| Version conflict | another fact is newer than this control | HTTP 409 + current Snapshot reconciliation | refresh, review, submit a new command | field-level merge not implemented |

## 5. Preview and validation limits

| Fact | Current guarantee | Not guaranteed |
| --- | --- | --- |
| workspace inventory | 15 folders, 96 input refs from pinned manifest | unpublished FORTE tasks or live enterprise drive |
| XLSX/CSV | first visible sheet/CSV, <=30 columns, <=120 rows | arbitrary workbook features or formula truth |
| DOCX/PDF/TXT | bounded extracted/read text, <=30,000 chars | OCR completeness, layout fidelity or semantic accuracy |
| stable ref | deterministic for pinned public input path | production document identity |
| plan compilation | server-owned effects/gates plus graph/source checks and one bounded repair | plan quality or tool execution |
| result validation | citation membership plus at least one uniquely resolved safe-preview Anchor per new Finding | entailment, exhaustive matching, arithmetic, native page coordinates or cell semantics |
| structured review | required fields/options and recommendation membership pass schema/runtime checks | recommendation quality, correct risk framing or human acceptance |
| Evidence Gate | decides continue/stop from explicit gaps and remaining bounds | semantic truth or human acceptance |
| completed | reviewable logical brief plus an independent TaskCommit pointer exists | task correctness, source-file Artifact, Connector or external process completion |

## 6. Transport and lifecycle

- Snapshot version and event sequence never decrease in the browser.
- A terminal event requires final GET; a nonterminal disconnect uses GET plus
  `after=N`.
- “trajectory live” requires an open current EventSource; “service available”
  only requires successful HTTP.
- Missing/wrong-owner Run returns the same 404.
- `X-User-Id` is unsigned. With `DATABASE_DSN`, Snapshot, command receipts,
  ArtifactVersions and TaskCommits are PostgreSQL-backed; without it they remain
  one-process memory.
- Local `start-demo.ps1` chooses Docker first, then a `DATABASE_DSN` explicitly
  present in the launching PowerShell process, otherwise memory. In the final
  case it overrides a stale `.env` database value. UI/service availability and
  restart-recovery claims must use `/v1/health.checkpoint` and `task_store`, not
  the launcher message or the mere presence of `.env`.
- `checkpoint_recovered` proves a persisted Snapshot was restored and paused.
  It does not prove an interrupted model call was cancelled or replayed.
- Plan operation labels and read-only Act declare intent/analysis. The current
  Runtime does not invoke a Tool Gateway or modify source files. Its logical
  evidence briefs and TaskCommits are independent append-only records, but they
  are not writable office files or external-action receipts.
- Pause/stop apply between provider calls; deadline prevents a new call but does
  not hard-cancel an in-flight request.
- Browser refresh restores a known Run id; `GET /runs` can discover the latest
  nonterminal Owner Run. There is not yet a full history chooser.

## 7. Evidence and applicability

Current contract: [`DR-0030`](../decisions/DR-0030-actionable-review-and-recoverable-analysis.md),
[`SCENARIO-016`](../scenarios/SCENARIO-016-actionable-finding-and-recoverable-analysis.md),
[`DR-0026`](../decisions/DR-0026-selective-branch-and-immutable-artifact-history.md),
[`DR-0025`](../decisions/DR-0025-durable-evidence-gate-and-artifact-evolution.md),
[`DR-0024`](../decisions/DR-0024-autonomous-whole-workspace-research.md),
[`DR-0023`](../decisions/DR-0023-agent-control-loop.md),
[`SCENARIO-012`](../scenarios/SCENARIO-012-selective-branch-and-artifact-restore.md),
[`SCENARIO-010`](../scenarios/SCENARIO-010-autonomous-whole-workspace-research.md),
[`SCENARIO-009`](../scenarios/SCENARIO-009-agent-control-loop.md),
[workspace interaction/source record](../research/WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825.md)
and [current branch/artifact Evidence](../evidence/DEMO1-BRANCH-ARTIFACT-CONTROL-EVIDENCE-20260826.md).

Automated checks are engineering proxies, not user research. User
comprehension, calibrated trust and task value remain `Draft`.
