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
       -> OpenAI-compatible Analyst
       -> Result/Citation Validator
       -> server-owned Branch DAG + branch Evidence Gate + bounded Loop Controller
       -> append-only logical ArtifactVersion + TaskCommit pointer/restore
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
- 1-3 rounds, 1-8 files per round, 2-6 model calls and a 20-3,000 second deadline.

The server freezes all 96 allowlisted input refs, `scope_mode=whole_workspace`
and loop bounds in the Run Snapshot. Client-owned `selected_file_refs` are not
accepted. During a Run, the UI freezes the task composer rather than pretending
new text would affect the active contract.

## 4. Planning and analysis ownership

The Planner returns strict JSON business intent. It does not own file identity,
source allowlist, side-effect scope, human gate or execution fact.

The server compiles the candidate into a `HarnessPlan`:

- read/inspect/verify intent maps to no side effect;
- result intent may map to `run_workspace_write`, which means a logical current
  Run result only and is not an Artifact mutation;
- external-action preview requires the server-owned human-gate policy;
- units, dependencies, cycles, per-round refs, tools, artifacts and gates are
  validated deterministically.
- every validated unit becomes a stable server-owned Branch with dependencies,
  evidence state and human-gate state; model output cannot assign Branch identity
  or completion.

Each round's Planner receives the current question, safe metadata for remaining files,
budget and any accepted steer instruction. A rejected candidate may be repaired
once within the same budget; rejection and retry are ordered facts. The server
also caps the union of model-selected refs at `max_files_per_round`, preserving
the model's highest-priority order and repairing dependencies. The Analyst
receives the user instruction, validated public plan and safe content only for
that approved round. It returns 1-10 findings with approved refs, a short fact,
separate impact, optional structured human-decision options, verbatim quote
candidates and `review_required=true`. The Runtime ignores model-supplied
locations, uniquely resolves each candidate against that same bounded safe
content, and publishes server-owned `evidence_anchors`. Every newly adopted
Finding needs at least one Anchor. Citation membership and source location are
checked; semantic truth, completeness and arithmetic are not. If the first
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
is 1,200 seconds and the public bound is 20 to 3,000 seconds. The Runtime freezes
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
  immutable result history, restore actions, cited brief and a full-page issue
  review surface for Gap, Branch, Finding and next-task proposals;
- activity pane: current phase, budget, ordered events and model adoption receipts.

The UI shows business facts and recovery actions, not internal protocol. A
citation is an interaction: it selects and opens the referenced file preview.
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
This is not a source-file Diff or semantic verification. Proposal context is
explicitly not a per-proposal citation. Preview security and result-review
boundaries remain available without turning the primary page into an
architecture document.

## 7. Eight module maturity

| Module | Current implementation | Missing target work |
| --- | --- | --- |
| Workspace Catalog & Safe Preview | full public folder, 96 refs, bounded previews and integrity checks | enterprise Connector/data policy |
| Task Contract | user instruction, complete workspace scope, loop bounds, Owner/key/version | durable task contract and production identity |
| Planner | strict candidate, autonomous evidence selection, per-round receipt and one bounded repair | retrieval-quality evaluation and richer replanning policy |
| Admission/Policy/Validator | server compilation and deterministic graph/source checks | dynamic topology admission |
| Scheduler & Worker Manager | one bounded single-loop controller with server-owned Branch states and selective continuation | parallel/adaptive workers, leases and multi-instance recovery |
| Tool Gateway | not connected | governed real/simulated tools and receipts |
| Artifact Workspace & Verifier | independent append-only logical evidence-brief versions, citation membership, server-resolved preview Anchors, branch Evidence Gate, TaskCommit pointer and restore | writable isolated office artifacts, semantic/numeric validators and conflict records |
| Checkpoint/Event/Governance | ordered events, branch/rollback controls, idempotent commands, independent records and optional PostgreSQL restart recovery | multi-instance lease/notification, in-flight cancellation, policy/approval/Permit integration |

## 8. Security and claim boundary

The current slice has no file write, shell, Web, SQL, scheduler, email, CRM or
other external Connector. Plan tool labels are intent declarations; no Tool
Gateway is invoked. `completed` means a reviewable response exists, not that an
office task, artifact or external process completed.

See [`DR-0030`](decisions/DR-0030-actionable-review-and-recoverable-analysis.md),
[`SCENARIO-016`](scenarios/SCENARIO-016-actionable-finding-and-recoverable-analysis.md),
[`DR-0028`](decisions/DR-0028-hierarchical-workspace-and-evidence-review.md),
[`SCENARIO-014`](scenarios/SCENARIO-014-inspect-agent-issue-in-context.md),
[`DR-0029`](decisions/DR-0029-server-verified-evidence-anchors.md),
[`SCENARIO-015`](scenarios/SCENARIO-015-pinpoint-and-compare-agent-evidence.md),
[`DR-0026`](decisions/DR-0026-selective-branch-and-immutable-artifact-history.md),
[`SCENARIO-012`](scenarios/SCENARIO-012-selective-branch-and-artifact-restore.md),
[UI-server fact matrix](contracts/UI_SERVER_FACT_MATRIX.md) and
[current Evidence](evidence/ACTIONABLE-REVIEW-AND-RECOVERY-EVIDENCE-20260826.md).
