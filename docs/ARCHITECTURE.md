# Office Agent V0.2 architecture

## 1. Current vertical slice

```text
Browser: unified file manager + task composer + trace
  -> GET /v1/harness/workspace
  -> GET /v1/harness/workspace/files/{file_ref}
  -> POST user instruction + loop bounds
  -> POST versioned pause/resume/steer/stop controls
  -> named SSE + Snapshot reconciliation

FastAPI Harness
  -> BenchmarkWorkspaceCatalog
  -> HarnessRuntime
       -> OpenAI-compatible Planner
       -> server Policy Compiler + Plan Validator
       -> OpenAI-compatible Analyst
       -> Result/Citation Validator
       -> human-confirmed Evidence Gate + bounded Loop Controller
       -> logical ArtifactVersion + final logical Commit
       -> HarnessStateStore
            -> PostgreSQL snapshots/receipts when DATABASE_DSN is configured
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
- 1-3 rounds, 1-8 files per round, 2-6 model calls and a 20-300 second deadline.

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

Each round's Planner receives the current question, safe metadata for remaining files,
budget and any accepted steer instruction. A rejected candidate may be repaired
once within the same budget; rejection and retry are ordered facts. The server
also caps the union of model-selected refs at `max_files_per_round`, preserving
the model's highest-priority order and repairing dependencies. The Analyst
receives the user instruction, validated public plan and safe content only for
that approved round. It returns 1-10 findings with at least one approved ref per
finding and `review_required=true`. Citation membership is checked; semantic
truth, completeness and arithmetic are not.

The Evidence Gate compares referenced files with the current round's approved
set. It alone decides `waiting_input`, `completed` or `budget_exhausted`; the
model does not write terminal state. When another round could close a gap, the
server pauses before spending that budget and requires an idempotent `resume`.
The resumed evidence round is scoped to the prior Gate's candidate refs, and the
Plan Validator requires all of them to remain in the plan; confirmation cannot
silently turn into unrelated workspace exploration.
Each completed round creates a logical read-only evidence-brief version. A
successful final Gate marks the latest version `committed` and records a logical
Commit. These records are part of the Run Snapshot, not independently immutable
Artifact/TaskCommit rows. Final `follow_ups` remain suggestions until a user
explicitly starts a separate Run.

## 5. State and streaming

The Snapshot is authoritative. Named events are a readable ordered projection:

```text
workspace_index -> round_started -> planning_started -> planning_completed
-> optional plan_validation_rejected/retry -> plan_validation
-> analysis_started -> analysis_completed -> result_validation -> evidence_gate
-> optional human resume -> next round or loop_committed/loop_budget_stopped/loop_stopped
```

Each event increments sequence and state transition increments Snapshot version.
The client applies Snapshot monotonically, reconnects from `after=N`, then uses
final GET reconciliation. A transport animation or configured model name is not
evidence that a model call occurred; only `HarnessModelReceipt.called` is.

Control commands use expected version and owner-scoped idempotency. Pause and
stop apply at safe points between calls; steer applies to the next round.
`HarnessStateStore` atomically stores the accepted Snapshot with start/control
receipts. On PostgreSQL startup, terminal and paused Runs are restored. Any
interrupted round is removed, a `checkpoint_recovered` event is appended and
the Run pauses at the last completed round; model calls are not automatically
replayed. The browser restores its known Run id, or discovers the most recent
nonterminal Owner Run via `GET /runs`. Memory fallback does not survive an API
restart. `X-User-Id` is not signed authentication, and there is no multi-instance
lease or notification channel.

## 6. Frontend architecture

The root page keeps three independently meaningful regions:

- file-manager rail: one flat searchable inventory, type filters and metadata;
- work area: task composer, loop contract, safe preview, round canvas, evidence
  gaps, explicit continue decision, result-version history and cited brief;
- activity pane: current phase, budget, ordered events and model adoption receipts.

The UI shows business facts and recovery actions, not internal protocol. A
citation is an interaction: it selects and opens the referenced file preview.
Preview security and result-review boundaries remain available without turning
the primary page into an architecture document.

## 7. Eight module maturity

| Module | Current implementation | Missing target work |
| --- | --- | --- |
| Workspace Catalog & Safe Preview | full public folder, 96 refs, bounded previews and integrity checks | enterprise Connector/data policy |
| Task Contract | user instruction, complete workspace scope, loop bounds, Owner/key/version | durable task contract and production identity |
| Planner | strict candidate, autonomous evidence selection, per-round receipt and one bounded repair | retrieval-quality evaluation and richer replanning policy |
| Admission/Policy/Validator | server compilation and deterministic graph/source checks | dynamic topology admission |
| Scheduler & Worker Manager | one bounded single-loop controller | adaptive workers, leases and recovery |
| Tool Gateway | not connected | governed real/simulated tools and receipts |
| Artifact Workspace & Verifier | per-round logical evidence-brief versions, citation membership, human Evidence Gate and final logical Commit | independently immutable records, semantic/numeric validators and TaskCommit |
| Checkpoint/Event/Governance | ordered events, controls, idempotent commands and optional PostgreSQL restart recovery | multi-instance lease/notification, in-flight cancellation, policy/approval/Permit integration |

## 8. Security and claim boundary

The current slice has no file write, shell, Web, SQL, scheduler, email, CRM or
other external Connector. Plan tool labels are intent declarations; no Tool
Gateway is invoked. `completed` means a reviewable response exists, not that an
office task, artifact or external process completed.

See [`DR-0024`](decisions/DR-0024-autonomous-whole-workspace-research.md),
[`SCENARIO-010`](scenarios/SCENARIO-010-autonomous-whole-workspace-research.md),
[UI-server fact matrix](contracts/UI_SERVER_FACT_MATRIX.md) and
[current Evidence](evidence/AUTONOMOUS-WHOLE-WORKSPACE-RESEARCH-EVIDENCE-20260825.md).
