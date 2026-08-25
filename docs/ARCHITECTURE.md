# Office Agent V0.2 architecture

## 1. Current vertical slice

```text
Browser: whole-folder office workbench + trace
  -> GET /v1/harness/workspace
  -> GET /v1/harness/workspace/files/{file_ref}
  -> POST user instruction + selected refs
  -> named SSE + Snapshot reconciliation

FastAPI Harness
  -> BenchmarkWorkspaceCatalog
  -> HarnessRuntime
       -> OpenAI-compatible Planner
       -> server Policy Compiler + Plan Validator
       -> OpenAI-compatible Analyst
       -> Result/Citation Validator
       -> in-memory Run/Event/Idempotency store
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
6. gives the Analyst bounded text only for the refs selected in this Run.

Public projection excludes task instructions, rubric, solution, grading,
filesystem path and SHA-256. `task.md` is provenance, not hidden context.

## 3. Workspace and task contract

The public workspace identity is fixed as `forte-public-office`. The browser may
search, expand folders, preview files and draft selection/instruction. A start
request must contain:

- workspace id;
- Owner-scoped idempotency key;
- expected version 1;
- a 3-2,000 character user instruction;
- 1-20 unique stable `file_ref` values.

The server revalidates all refs and freezes selected source documents in the
Run Snapshot. The model cannot expand the source set. Unknown, duplicate or
out-of-workspace refs fail closed.

## 4. Planning and analysis ownership

The Planner returns strict JSON business intent. It does not own file identity,
source allowlist, side-effect scope, human gate or execution fact.

The server compiles the candidate into a `HarnessPlan`:

- read/inspect/verify intent maps to no side effect;
- result intent may map to `run_workspace_write`, which means a logical current
  Run result only and is not an Artifact mutation;
- external-action preview requires the server-owned human-gate policy;
- units, dependencies, cycles, selected refs, tools, artifacts and gates are
  validated deterministically.

The Analyst receives the user instruction, validated public plan and safe
selected-file content. It returns 1-10 findings with at least one selected ref
per finding and `review_required=true`. Citation membership is checked; semantic
truth, completeness and arithmetic are not.

## 5. State and streaming

The Snapshot is authoritative. Named events are a readable ordered projection:

```text
workspace_index -> planning_started -> planning_completed -> plan_validation
-> analysis_started -> analysis_completed -> result_validation -> task_completed
```

Each event increments sequence and state transition increments Snapshot version.
The client applies Snapshot monotonically, reconnects from `after=N`, then uses
final GET reconciliation. A transport animation or configured model name is not
evidence that a model call occurred; only `HarnessModelReceipt.called` is.

All Run state is one-process memory. API restart loses Run/event/idempotency
state. `X-User-Id` is not signed authentication.

## 6. Frontend architecture

The root page keeps three independently meaningful regions:

- folder rail: searchable folder/file inventory, metadata and explicit scope;
- work area: task composer, safe preview, validated plan and cited result;
- activity pane: ordered events and two model receipts.

The UI shows business facts and recovery actions, not internal protocol. A
citation is an interaction: it selects and opens the referenced file preview.
Preview security and result-review boundaries remain available without turning
the primary page into an architecture document.

## 7. Eight module maturity

| Module | Current implementation | Missing target work |
| --- | --- | --- |
| Workspace Catalog & Safe Preview | full public folder, 96 refs, bounded previews and integrity checks | enterprise Connector/data policy |
| Task Contract | user instruction, selected refs, Owner/key/version | durable task contract and production identity |
| Planner | strict model candidate and call receipt | quality evaluation and iterative steering |
| Admission/Policy/Validator | server compilation and deterministic graph/source checks | dynamic topology admission |
| Scheduler & Worker Manager | not connected | bounded loop, adaptive workers, leases and recovery |
| Tool Gateway | not connected | governed real/simulated tools and receipts |
| Artifact Workspace & Verifier | read-only result and citation membership | immutable versions, semantic/numeric validators and Commit |
| Checkpoint/Event/Governance | ordered memory events and idempotent start | durable checkpoint, replay, policy/approval/Permit integration |

## 8. Security and claim boundary

The current slice has no file write, shell, Web, SQL, scheduler, email, CRM or
other external Connector. Plan tool labels are intent declarations; no Tool
Gateway is invoked. `completed` means a reviewable response exists, not that an
office task, artifact or external process completed.

See [`DR-0022`](decisions/DR-0022-workspace-folder-and-arbitrary-task-contract.md),
[`SCENARIO-008`](scenarios/SCENARIO-008-whole-folder-office-workspace.md),
[UI-server fact matrix](contracts/UI_SERVER_FACT_MATRIX.md) and
[current Evidence](evidence/FORTE-FOLDER-WORKSPACE-EVIDENCE-20260825.md).
