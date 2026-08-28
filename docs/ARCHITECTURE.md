# Office Agent V0.2 architecture

## 1. Current vertical slice

```text
Browser: unified file manager + task composer + trace
  -> GET /v1/harness/workspace
  -> GET /v1/harness/workspace/files/{file_ref}
  -> POST user instruction + loop bounds
  -> POST versioned pause/resume/steer/stop/rollback controls
  -> named SSE + Snapshot reconciliation

FastAPI Harness
  -> BenchmarkWorkspaceCatalog
  -> HarnessRuntime
       -> OpenAI-compatible Planner
       -> server Policy Compiler + Plan Validator
       -> admitted deterministic office adapter + run-workspace Artifact Verifier
       -> OpenAI-compatible Analyst
       -> Result/Citation Validator
       -> server-owned Branch DAG + branch Evidence Gate + bounded Loop Controller
       -> append-only logical ArtifactVersion + TaskCommit pointer/restore
       -> isolated real office Artifact store + Owner-scoped download
       -> HarnessStateStore
            -> PostgreSQL snapshots/receipts/artifacts/commits when DATABASE_DSN is configured
            -> process-local memory fallback otherwise
```

Only `health_router` and the Harness router are mounted. Legacy conversation,
Task, Demo2, Run/Gate, quote and Customer A runtimes are not initialized by the
current product app.

## 2. Data trust boundary

The pinned source is FORTE commit
`345c1ec1487139db9dd319787fa9405ba85d1869`. The active
`public-suite-manifest.json` declares 15 task records and 96 input files.

`BenchmarkWorkspaceCatalog`:

1. validates manifest schema/totals and every declared task/input byte;
2. rejects duplicate/undeclared paths, path escape, symlink, size/hash drift,
   archive explosion and unsupported active content;
3. exposes only input files as business-labeled stable refs;
4. produces bounded table/document/PDF/text previews;
5. never executes macros/scripts or loads external resources;
6. gives the Planner safe metadata for the complete input index, then gives the
   Analyst bounded text only for refs selected and approved in the current round.

Public projection excludes task instructions, rubric, solution, grading,
filesystem path and SHA-256. `task.md` is provenance, not hidden context.

## 3. Workspace and task contract

The public workspace identity is fixed as `forte-public-office`. The browser may
search, filter and preview files, but those actions do not constrain Agent scope. A start
request must contain:

- workspace id;
- Owner-scoped idempotency key;
- expected version 1;
- a 3-2,000 character user instruction;
- 1-24 rounds, 1-24 files per round, 2-60 model calls and a 20-14,400 second deadline.

Defaults are 12 rounds, 16 files per round, 30 model calls and 7,200 active
seconds. The larger bounds remove the historical fixed-three-round assumption;
they do not remove explicit stop, model-call, file or active-time governance.

The server freezes all 96 allowlisted input refs, `scope_mode=whole_workspace`
and loop bounds in the Run Snapshot. Client-owned `selected_file_refs` are not
accepted. During a Run, the UI freezes the task composer rather than pretending
new text would affect the active contract.

## 4. Planning and analysis ownership

The Planner returns strict JSON business intent. It does not own file identity,
source allowlist, side-effect scope, human gate or execution fact.

The server compiles the candidate into a `HarnessPlan`:

- read/inspect/verify intent maps to no side effect;
- result intent may map to `run_workspace_write`, which remains a server-owned
  write intent and is not execution evidence by itself;
- external-action preview requires the server-owned human-gate policy;
- units, dependencies, cycles, per-round refs, tools, artifacts and gates are
  validated deterministically.
- every validated unit becomes a stable server-owned Branch with dependencies,
  evidence state and human-gate state; model output cannot assign Branch identity
  or completion.

After the Plan Validator accepts a plan, the Scenario Effect Gate may admit one
of twelve fixed, server-owned local office capabilities by matching the original
user instruction and the frozen FORTE input set. This is not a hidden Scenario
selector and the model cannot name a validator into existence. The adapter reads
only Catalog-approved bytes, writes new CSV/Markdown/DOCX/ZIP files into the
isolated Run Workspace, runs a deterministic validator, stores immutable file
metadata and emits an EffectReceipt. TC-03/08/09 remain explicit
`blocked_external_boundary` because their SQL/Web/cron dependencies are not
authorized. The original FORTE bytes are checked before and after the gate and
are never modified.

Each round's Planner receives the current question, safe metadata for remaining files,
budget and any accepted steer instruction. A rejected candidate may be repaired
once within the same budget; rejection and retry are ordered facts. The server
also caps the union of model-selected refs at `max_files_per_round`, preserving
the model's highest-priority order and repairing dependencies. The Analyst
receives the user instruction, validated public plan and safe content only for
that approved round. It returns 1-3 findings with approved refs, a short fact,
separate impact, optional structured human-decision options, verbatim quote
candidates and `review_required=true`. The Runtime ignores model-supplied
locations, uniquely resolves each candidate against that same bounded safe
content, and publishes server-owned `evidence_anchors`. Every newly adopted
Finding needs at least one Anchor. Citation membership and source location are
checked; semantic truth, completeness and arithmetic are not. If the first
strict text match has no candidate, the resolver may ignore safe-Preview layout
whitespace and punctuation while retaining a character-to-line map. This fallback
requires at least 12 normalized characters and exactly one position; repeated
matches remain `ambiguous`, so it is not fuzzy or semantic matching. After Anchor
resolution, a Finding whose verified `observed` dates all fall outside an explicit
Chinese month/day window in the instruction is omitted with
`analysis_scope_filtered`. A model-proposed human review without any exact
`contradiction` Anchor is removed with `decision_gate_suppressed`; neither rule
weakens file-scope or Catalog-integrity fail-closed checks.

If the first
Analyst output cannot be uniquely located, the Runtime records
`analysis_validation_rejected` and permits at most one new Analyst call within
the same budget; the browser never receives rejected prose as an adopted result.
The resolver records `exact`, `ambiguous`, `unavailable`, `stale` or `rejected`
for each quote. Source revision changes produce `stale`; a server-recomputed
candidate mismatch produces `rejected`. A valid subset is adopted with
`analysis_partial_adopted` and an append-only partial ArtifactVersion. Unresolved
Finding/Resolution facts pause only their bound Branches. If neither attempt
yields a usable Finding, the Runtime preserves Plan/Branch/call facts and pauses
with `next_step.recovery_kind=source_location`; repeated schema failures use
`analysis_output`. If another round does not fit the budget, the same facts end
as `stopped/bounded`: the terminal Run is not resumable, but its candidate Branch
may seed a new Task Contract and whole-workspace Run. Out-of-scope references
remain a fail-closed security error.

The Evidence Gate compares referenced files with each Branch's approved set. It
alone decides which branches are `completed`, `waiting_input` or stopped, and
then decides the Run state; the model does not write either fact. When more than
one branch could close a gap, the server pauses before spending another round.
The user selects one waiting `branch_id`; the next round is scoped only to that
Branch's `missing_file_refs`, while unselected branches remain waiting. The Plan
Validator requires all confirmed refs to remain in the plan, so confirmation
cannot silently become unrelated workspace exploration.

The deadline is an active execution budget, not Run wall-clock age. The default
is 7,200 seconds and the public bound is 20 to 14,400 seconds. The Runtime freezes
`budget.elapsed_ms` when it enters `waiting_input`, applies a user pause or
reaches a terminal state, then resumes from the accumulated active elapsed at a
legal Branch resume. Human reading time therefore does not consume model work
budget. The model-call and round caps remain separate, and the deadline still
blocks only a new call rather than hard-cancelling an in-flight HTTP request.

Each completed round creates an independent append-only logical evidence-brief
ArtifactVersion. A successful final Gate creates a separate TaskCommit that
selects the latest verified version; it does not mutate that version to express
commit state. A versioned/idempotent `rollback` verifies an existing immutable
record, creates another TaskCommit and moves the current brief pointer. It never
deletes history or changes a FORTE source file. Final `follow_ups` remain
suggestions until a user explicitly starts a separate Run.

## 5. State and streaming

The Snapshot is authoritative. Named events are a readable ordered projection:

```text
workspace_index -> round_started -> planning_started -> planning_completed
-> optional plan_validation_rejected/retry -> plan_validation
-> optional deterministic_office_tool_started
   -> run_workspace_artifact_written
   -> deterministic_verification_completed
   or scenario_effect_failed
   or scenario_effect_bounded
-> analysis_started -> analysis_completed -> result_validation -> evidence_gate
-> optional branch-selected human resume -> next round or loop_committed/loop_budget_stopped/loop_stopped
-> optional artifact_version_restored after terminal human restore
```

Each event increments sequence and state transition increments Snapshot version.
The client applies Snapshot monotonically, reconnects from `after=N`, then uses
final GET reconciliation. A transport animation or configured model name is not
evidence that a model call occurred; only `HarnessModelReceipt.called` is.

Control commands use expected version and owner-scoped idempotency. Pause and
stop apply at safe points between calls; steer applies to the next round;
rollback applies only to a terminal committed Run. `HarnessStateStore`
atomically stores the accepted Snapshot and receipts, optionally with new
append-only ArtifactVersion/TaskCommit rows. On PostgreSQL startup, terminal and
paused Runs plus their independent artifact history are restored. Any interrupted
round and its uncommitted Branch records are removed, a `checkpoint_recovered`
event is appended and the Run pauses
at the last completed round; model calls are not automatically replayed. The
browser restores its known Run id, or discovers the most recent nonterminal
Owner Run via `GET /runs`. Memory fallback does not survive an API restart.
`X-User-Id` is not signed authentication, and there is no multi-instance lease
or notification channel.

Long fixed Scenario Effects do not execute their synchronous builders on the
FastAPI event loop. The Runtime first verifies and freezes the exact allowlisted
bytes and safe previews, persists `deterministic_office_tool_started`, then runs
the builder through `asyncio.to_thread`. TC-04 freezes 46 inputs: 44 project
files plus PRD and technical-design context. The worker cannot re-read the live
Catalog. An in-process `(owner, run, capability)` claim prevents duplicate
dispatch while the first effect is active; Artifact IDs and receipts remain
server-owned.

This preserves health, Run GET, workspace browsing and SSE responsiveness while
the roughly one-minute test subprocesses run. It is still a single Controller
with an in-process worker thread, not a Scheduler/Worker implementation. A
process restart cannot continue the thread or its subprocess; PostgreSQL only
recovers the last committed Snapshot and pauses according to the existing
checkpoint rule. `scenario_effect_failed` records failure without fabricating an
Artifact or durable tool-execution receipt.

Run Workspace Artifact metadata and EffectReceipts are part of the authoritative
Snapshot. Artifact bytes are stored outside the public FORTE tree in an isolated,
Owner/Run-scoped directory and are rechecked against the private digest before
download. PostgreSQL restart restores the metadata through the Snapshot; the
separate Artifact store preserves the bytes on the same host. This is not an
object store, a general Tool Gateway, multi-host durability or transactional
coordination between database and filesystem.

`EvidenceResolution` and human decisions are currently nested in the authoritative
Snapshot JSONB. This preserves records committed before a restart, but is not an
independent append-only decision ledger and has no database-level source-revision
or compare-and-swap constraint. An interrupted running round is still discarded
by the recovery policy; only completed rounds and their artifacts are restored.
DR-0032's real PostgreSQL 17.11 sequential Runtime gate verifies that an open
three-candidate DecisionRequest survives restart, accept resumes only the bound
Branch, v1 remains immutable and v2 is appended, and the final Snapshot survives
another restart. This still does not establish an independent decision ledger,
database CAS or multi-instance safety.

## 6. Frontend architecture

The root page keeps three independently meaningful regions:

- file-manager rail: a collapsible hierarchy projected from server-owned
  `folders[]/display_path`, plus search, type filters and safe file opening;
- work area: task composer, loop contract, safe preview, round canvas, evidence
  gaps projected as Branch lanes (Branch -> current material -> Evidence Gate ->
  next action), server-backed task-branch state, branch-specific continue decision,
  immutable result history, restore actions, verified Run Workspace files with
  deterministic checks/downloads, cited brief and a full-page issue
  review surface for Gap, Branch, Finding and next-task proposals;
- activity pane: current phase, budget, ordered events and model adoption receipts.

The UI shows business facts and recovery actions, not internal protocol. A
citation is an interaction: it selects and opens the referenced file preview.
The Artifact area independently shows whether the model call happened, whether
its output was adopted, whether a deterministic local effect passed, what file
was written and which side effects did not occur. It never collapses these into
one green “completed” state.
When every Run Workspace Artifact is verified but the Loop still waits on an
audit-location Gap, the work area renders the outcome before Branch/Gaps and says
“成果可用，审计待补充”. Gaps with the same candidate source refs and failure detail
may be grouped into one user-visible audit item only in this state; different failures
in the same file remain separate. The grouping is client projection; server Branch
IDs, versions and recovery controls are unchanged.
The issue-review surface reuses the same preview route and organizes authoritative
Snapshot facts as Agent proposal -> server record -> human review. For Findings,
it first separates fact, impact and the required human action, then renders the
server-owned Anchor roles beside the actual safe Preview and jumps to highlighted
text/table rows. A structured decision exposes mutually exclusive choices and
user feedback. The Agent recommendation stays hidden until the user selects an
initial option and asks to compare. Accept/decline/defer first become a versioned,
idempotent DecisionRecord bound to Finding/Resolution/Branch. Accepting a business
option then creates a new read-only Run; accepting an ambiguous source position
steers and resumes only its current waiting Branch. Closing a pending sheet exits
the modal immediately and then attempts a versioned defer; a 409 or transport
failure remains a visible non-blocking error and cannot be called a recorded
decision. None of these operations edits the source. The
browser never derives a location from claim text. A budget-stopped recovery view
similarly creates a new Run for one unresolved Branch objective and never sends
`resume` or `steer` to the terminal Run; prior ArtifactVersions remain attached
to the old Snapshot. A Gap without an Anchor is presented as an Agent execution
gap, not a source-file defect: the sheet derives structure/location/coverage type,
attempted refs and model adoption from Snapshot facts, keeps feedback optional,
and exposes “retry only this Branch” as the primary nonterminal action. No Anchor
means no invented row number or highlight.
The front end does not treat every waiting Branch as the same human job. A
retry-only `source_location/analysis_output` state puts one recommended Branch
resume first and collapses optional clues, stop reasons and Preview. An
`ambiguous` EvidenceResolution instead explains why a human is needed, requires
one explicit candidate choice and disables accept until that choice exists. This
changes information order only; version, idempotency, budget and recovery remain
server-owned.
This is not a source-file Diff or semantic verification. Proposal context is
explicitly not a per-proposal citation. Preview security and result-review
boundaries remain available without turning the primary page into an
architecture document.

DR-0037 adds artifact-level semantics without widening the Tool Gateway. A real
Run Workspace Artifact may carry `covered_period`, `statistic_basis`, `purpose`
and `record_count`; `source_file_refs` then names that file's content sources,
while the EffectReceipt retains the whole fixed-adapter context. For TC-05 this
means the two 2026 CSVs no longer inherit three-period source/check claims, and
only the cross-period note owns the three-period comparison. These fields are
service-owned deterministic facts, not model narration or a general finance
ontology. The larger review typography changes only the browser projection.

DR-0038 changes only the browser projection and action hierarchy for
`source_location`. The UI derives verified/unverified/terminal presentation from
server-owned Artifact/EffectReceipt, Run status and Gap facts. A nonterminal
retry-only Gap resumes one bound Branch; a structured Resolution still uses the
Decision protocol, and a terminal Run still creates a new Task Contract. Internal
Branch/Gap/Resolution facts remain auditable under progressive disclosure. This
projection does not mutate Snapshot truth or spend budget before an explicit action.

DR-0039 adds optional `deliverable_type`, `key_outputs`, `review_guidance` and
`execution_summary` to the service-owned Run Workspace Artifact. TC-10 uses them
to distinguish a flow-design DOCX from execution: the document and browser state
say that dialing, CRM and SMS are described nodes but did not occur. The fixed
verifier still owns the 13 checks, while the EffectReceipt owns prohibited side
effects and `external_action=none`. These fields do not create a Connector,
Permit, general outbound engine or production compliance approval.

DR-0040 adds optional `key_outputs_label` and `self_test` to the same
service-owned Artifact contract. TC-02 uses them to expose exact file changes,
download commands, declared checks and failure signals without letting the
browser infer code facts from a Scenario name. Its fixed adapter copies all
seven algorithm-013 inputs to a temporary Run Workspace, preserves five contract
files byte-for-byte, modifies the copied config/main entry and adds a bounded
ReAct controller plus tests. Its default policy deterministically walks the
Planner-selected tools through a replaceable `action_policy`; the outer provider
Planner/Analyst are not this internal policy. The verifier compares declared and
executed test IDs and independently rechecks the downloaded ZIP. This does not
prove model-driven action selection inside the project and does not add a general
shell, arbitrary repository support, dependency installation, automatic merge or
OS-level network isolation. Artifact cards keep their own `checks[]` projection,
but Run-level counts and EffectReceipt wording deduplicate repeated `check_id`
values. Two files using one checklist are therefore twelve unique checks, not
twenty-four independent checks.

DR-0041 extends `self_test` with service-owned `test_suites[]`,
`test_manifest_file` and a manifest/collected-set receipt. The fixed TC-04
adapter copies all 44 files under dev-015 `input/source-code`, runs one 117-case
test set on the unpatched copy, applies three real-source fixes, then reruns the
same collected IDs. Each changed file has its own >=80% coverage gate; aggregate
coverage is separate. Artifact and EffectReceipt source arrays allow up to the
96-file Workspace so the 44 real content refs are not truncated. This is a
bounded deterministic adapter, not a general Scheduler/Worker, shell or sandbox.

DR-0042 applies the same inspectable-test contract to the fixed qa-003
dashboard-toolkit adapter. It freezes and copies all 11 public inputs, runs one
71-case manifest through three intentional red stages and one final green stage,
then independently unpacks and reruns the ZIP. The four-file diff and per-file V8
coverage are server-owned facts; the UI projects three suites of 23/20/28 without
inventing IDs. This proves one bounded JavaScript repair effect, not a general
repository executor, automatic PR path or OS-level network sandbox.

DR-0043 adds a generic business-outcome layer without weakening deterministic
Artifact verification. The fixed pm-014 adapter validates four source-table
contracts, derives one 18-row feature ledger and four formal release Gates, then
stores the same `business_gate_outcome` on both Artifacts and the EffectReceipt.
Reason base levels come from the PRD rule cells, while risk totals and all user-
facing counts are recomputed from the ledger; unknown/ambiguous levels and any
count mismatch fail closed rather than falling back to sample constants.
`verifier_status=passed` means the source/formula/file checks passed;
`business_gate_outcome.status=failed` independently means the source-derived
release conditions failed. The browser projects both rather than converting a
business failure into an Artifact failure or hiding it behind a green check.
This is not a general rules engine, release executor or configuration writer.

DR-0044 reuses that separation for the fixed Legal-020 auxiliary review. A
source-derived builder validates one rule Markdown and six unique DOCX packages,
parses all 21 rules and produces one assessment for every document/rule pair.
The parser binds principal and agent identity fields to their own subject rows;
package-level media/drawing/pict/embedding/signature evidence is distinct from a
blank signature placeholder. The same `legal_review_outcome` is stored on both
Artifacts and the EffectReceipt, while `business_gate_outcome` holds three legal
review Gates. `verifier_status=passed`, a failed legal Gate and
`human_review_required=true` can therefore all be true at once. An attorney
license string without a Registry/Connector receipt remains `unverifiable`. This
is not legal advice, signature validation, authorization effectiveness or a
general contract-review engine.

DR-0045 adds the same truth separation to fixed hr-001 candidate review without
turning the system into an ATS. A source-derived builder validates two unique JD
DOCX files and five unique resume PDFs, parses 14 BD conditions and 8 text-
evaluation conditions, and produces one assessment for every role/candidate/
condition combination. Each assessment carries both JD and resume source refs,
safe locators and excerpts; identity, education, experience and skills remain
bound to one resume. Missing facts are `unverifiable`, explicit gaps can be
`not_met`, and an explicit JD exception becomes `human_exception_required`.
The same `candidate_review_outcome` is stored on all three Artifacts and the
EffectReceipt, so `verifier_status=passed`, incomplete evidence and a pending HR
decision can all be true at once. The two role reports bind only their own JD
plus five resumes; the joint ledger binds all seven sources. This is not a
general hiring engine, fairness proof, background check, identity verifier or
candidate-notification system.

DR-0046 applies source-derived verification to the fixed Finance-018 adapter.
It validates three unique period workbooks and parses each row into a period,
source file, sheet, Excel row/cell locator, subject, counterparty, direction and
finite ending balance. The two 2026 CSV files and the three-period Markdown are
then parsed again and compared with a fresh recomputation from the approved XLSX
bytes. `finance_review_outcome` is stored on all three Artifacts and the
EffectReceipt. A deterministic pass, one or more cross-period candidates and a
pending finance decision may therefore coexist. Candidate enumeration is an
exact-balance heuristic, not a bad-debt conclusion, accounting policy, payment,
write-off, posting or source-workbook edit.

DR-0047 applies the same source-derived pattern to the fixed Operations-008
process-design adapter. The server freezes exactly one approved Markdown file,
parses each normative fragment into a rule ledger and builds stable node, edge,
guard and terminal records. Graph admission verifies one START, reachability,
terminal closure, identity/recording/debt order, third-party disclosure limits
and rule coverage. The generated DOCX is parsed again and compared with a fresh
source derivation. `outbound_flow_outcome` is stored on the Artifact and
EffectReceipt, so deterministic verification, complete source coverage,
pending business/compliance approval and zero external actions remain distinct
facts. This does not add a Connector, legal opinion, current-regulation registry
or production outbound engine.

DR-0048 makes that fragment boundary enforceable. A line selected for one known
rule is not treated as fully consumed: every normative sentence fragment must
match one expected semantic pattern, compile to a supported extra-human guard,
or fail closed as unsupported/conflicting. The original line locator remains
the audit anchor. This avoids both whole-line false green and browser-side
keyword inference; it is still a fixed Operations-008 parser rather than a
general policy language.

DR-0049 applies source-derived verification to the fixed Sales-020 adapter. The
server freezes exactly one survey CSV and one rule Markdown, validates the CSV
encoding/schema/value domain and derives cleaning, thresholds, priority,
exclusion and report structure from approved rule locators. Every source row
becomes a decision record with raw and cleaned values, transformations, all
matched profiles, priority application, final label or exclusion and duplicate
link. `customer_segmentation_outcome` is stored on both Artifacts and the
EffectReceipt, so deterministic file verification, a review-required duplicate
assumption, a draft strategy and zero external actions remain distinct facts.
The generated Markdown and CSV are parsed again against a fresh source
derivation. This is not a CRM, customer study, sales-effectiveness verifier or
general clustering engine.

## 7. Eight module maturity

| Module | Current implementation | Missing target work |
| --- | --- | --- |
| Workspace Catalog & Safe Preview | full public folder, 96 refs, bounded previews and integrity checks | enterprise Connector/data policy |
| Task Contract | user instruction, complete workspace scope, loop bounds, Owner/key/version | durable task contract and production identity |
| Planner | strict candidate, autonomous evidence selection, per-round receipt and one bounded repair | retrieval-quality evaluation and richer replanning policy |
| Admission/Policy/Validator | server compilation and deterministic graph/source checks | dynamic topology admission |
| Scheduler & Worker Manager | one bounded single-loop controller with server-owned Branch states and selective continuation | parallel/adaptive workers, leases and multi-instance recovery |
| Tool Gateway | twelve fixed local deterministic office adapters with EffectReceipts; no model-owned dispatch | reusable governed tool registry, arbitrary safe commands, Web/SQL/Scheduler/Connector receipts |
| Artifact Workspace & Verifier | independent append-only logical evidence-brief versions, citation membership, server-resolved preview Anchors, branch Evidence Gate, TaskCommit pointer/restore, plus isolated CSV/Markdown/DOCX/ZIP files and named deterministic validators for twelve fixed capabilities | general writable office workspace, reusable semantic/numeric verifier framework, conflict-aware edits and multi-host Artifact durability |
| Checkpoint/Event/Governance | ordered events, branch/rollback controls, idempotent commands, independent records and optional PostgreSQL restart recovery | multi-instance lease/notification, in-flight cancellation, policy/approval/Permit integration |

## 8. Security and claim boundary

The current slice can write only new files in an isolated Run Workspace through
twelve fixed server-owned adapters. It never modifies FORTE sources and has no
general shell, Web, SQL, scheduler, email, CRM or external Connector. Fixed code
validators run only service-owned commands in one-use temporary directories and
receive a minimal OS environment allowlist; provider keys, tokens, database DSNs,
`PYTHONPATH` and user shell hooks are not inherited. Plan tool labels remain
intent declarations; only Artifact/Effect receipts prove a fixed adapter ran.
`completed` means a reviewable logical response exists, not that a deterministic
Artifact or external process completed.
The fixed TC-02 test path did not call network or production search, but the
runner does not block direct sockets at the OS boundary. Reports must preserve
that distinction.

See [`DR-0036`](decisions/DR-0036-outcome-first-and-layout-tolerant-evidence.md),
[`SCENARIO-022`](scenarios/SCENARIO-022-verified-outcome-and-audit-location.md),
[`DR-0037`](decisions/DR-0037-tc05-artifact-semantics-and-review-readability.md),
[`SCENARIO-023`](scenarios/SCENARIO-023-understand-finance-artifacts-and-review-evidence.md),
[`DR-0038`](decisions/DR-0038-user-language-source-location-recovery.md),
[`SCENARIO-024`](scenarios/SCENARIO-024-understand-and-recover-missing-table-location.md),
[`DR-0035`](decisions/DR-0035-scenario-effect-gate-and-run-workspace-artifacts.md),
[`SCENARIO-021`](scenarios/SCENARIO-021-verifiable-office-artifact-effect.md),
[`DR-0034`](decisions/DR-0034-one-action-recovery-and-explicit-source-choice.md),
[`SCENARIO-020`](scenarios/SCENARIO-020-retry-or-select-one-source.md),
[`DR-0030`](decisions/DR-0030-actionable-review-and-recoverable-analysis.md),
[`SCENARIO-016`](scenarios/SCENARIO-016-actionable-finding-and-recoverable-analysis.md),
[`DR-0028`](decisions/DR-0028-hierarchical-workspace-and-evidence-review.md),
[`SCENARIO-014`](scenarios/SCENARIO-014-inspect-agent-issue-in-context.md),
[`DR-0029`](decisions/DR-0029-server-verified-evidence-anchors.md),
[`SCENARIO-015`](scenarios/SCENARIO-015-pinpoint-and-compare-agent-evidence.md),
[`DR-0026`](decisions/DR-0026-selective-branch-and-immutable-artifact-history.md),
[`SCENARIO-012`](scenarios/SCENARIO-012-selective-branch-and-artifact-restore.md),
[UI-server fact matrix](contracts/UI_SERVER_FACT_MATRIX.md) and
[current TC-01 Evidence](evidence/DR-0036-TC01-OUTCOME-EVIDENCE-LOCALIZATION-EVIDENCE-20260828.md) and
[current TC-05 Evidence](evidence/DR-0046-TC05-SOURCE-DERIVED-FINANCE-REVIEW-EVIDENCE-20260829.md),
plus [current source-location language Evidence](evidence/DR-0038-USER-LANGUAGE-SOURCE-LOCATION-RECOVERY-EVIDENCE-20260828.md).
