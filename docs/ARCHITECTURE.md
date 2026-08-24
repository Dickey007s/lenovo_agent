# Office Agent V0.2 Architecture

## 1. Current boundary

The current product is one FORTE-backed planning worksite:

```text
Browser
  -> six-path FastAPI surface
  -> BenchmarkScenarioCatalog
       -> pinned manifest + upstream bytes + license
       -> safe public Scenario projection
       -> private sanitized Planner context
  -> HarnessRuntime
       -> source index
       -> deepseek-v4-pro plan candidate
       -> deterministic Plan Validator
       -> memory Snapshot + ordered events + idempotency result
  -> public Snapshot / SSE
  -> ready_to_execute
```

The Runtime deliberately stops before execution. There is no public command or mounted service for Worker scheduling, tool use, Artifact mutation, approval, Permit, Connector, or external action.

## 2. Trust boundaries

### Source boundary

`demo-enterprise-data/forte/manifest.json` binds 11 vendored source files at FORTE commit `345c1ec1487139db9dd319787fa9405ba85d1869`, totaling `115352` bytes. Catalog loading checks declared path, root boundary, symlink status, size, SHA-256, type and parser constraints.

Five upstream Markdown files contain CRLF bytes. Task and input files are marked binary in `.gitattributes` so Git cannot silently normalize those bytes away from the manifest. Any mismatch fails closed.

### Planner boundary

Raw `task.md` is provenance, not public content. The Catalog produces two separate projections:

- public Scenario: business title, goal, deliverables, data boundary, gate summary, capability labels and safe file labels/summaries;
- internal Planner context: sanitized instruction, allowlisted tool/effect policy and internal source metadata.

The public API and ordinary DOM must not contain `task_instruction`, rubric, solution, grading content, absolute path, full hash, Prompt, chain of thought, raw model response or secrets.

### Model and validation boundary

The model can propose a `HarnessPlan`; it does not own scenario identity, source identity, Run state, event sequence, validation result or execution outcome. The server validates:

- unit identity and dependency graph, including cycles;
- input file references against the frozen source set;
- tool and side-effect values against the Scenario policy;
- `artifact.write` logical naming and `run_workspace_write` mapping;
- human-gate declarations for external-action candidates.

`called=true`, `output_used=true`, and `status=ready_to_execute` are separate facts. A model response can be called but not adopted; an adopted plan still must pass deterministic validation.

## 3. Runtime state

Statuses are `queued -> indexing -> planning -> validating -> ready_to_execute`, or `failed`. A successful run emits:

```text
workspace_index
planning_started
planning_completed
plan_validation
ready_to_execute
```

Snapshot version and event sequence increase monotonically. Start is bound to Owner and idempotency key. GET and SSE enforce the same Owner scope; missing and wrong-owner Runs both return 404.

Runs, events, in-flight planning tasks and idempotency results live only in one API process. API restart loses them. The configured health response may still expose `checkpoint=memory` and `task_store=memory`; this is not durable recovery.

## 4. Frontend projection

The root page imports only `HarnessWorkbench`. The worksite shows:

- Scenario and safe source material;
- the public Task Contract;
- progressive read/plan/validate/ready stages;
- validated plan units and dependencies;
- a resizable desktop right rail or mobile lower rail with server activity and model receipt;
- separate recovery states for service unreachable, Catalog unavailable and Catalog integrity failure.

“事件流实时” requires an open EventSource. After a terminal event the client closes SSE and performs a final GET. A nonterminal interruption resumes with `after=N`; the client does not fabricate missing events or a completed status.

## 5. Eight canonical modules

| Module | Current state | Current evidence | Next boundary |
| --- | --- | --- | --- |
| 1. Scenario Pack & Workspace Catalog | Implemented, bounded | pinned FORTE bytes, manifest checks, safe/private projections | Connector-backed enterprise source adapters |
| 2. Task Contract | Implemented, bounded | public goal, deliverables, data boundary, capability/gate summary | editable/versioned enterprise contracts |
| 3. Planner | Implemented, bounded | real-model candidate and receipt | quality evaluation, model policy and fallback studies |
| 4. Admission & Plan Validator | Implemented, bounded | deterministic path/tool/dependency/effect/gate checks | budgets, richer policy and replanning admission |
| 5. Scheduler & Worker Manager | Draft | no current execution command | leases, cancellation, recovery and dynamic Worker control |
| 6. Tool Gateway | Draft for current product | generic package exists but is not mounted | current-contract capability registry and governed invocation |
| 7. Artifact Workspace & Verifier | Draft | plan declarations only | versioned outputs, citations, verification and Commit |
| 8. Checkpoint, Event & Governance Control | Partial | memory Snapshot, ordered SSE, Owner/idempotency | durable store, production identity, execution controls and audit |

This table is the only maturity vocabulary used in code review and reporting.

## 6. Lifecycle

The legacy workspace shell, fixed Customer A runtimes, action routes and Customer A data are absent from the current tree. Historical decisions and Evidence remain valid for their recorded commits, but are retired from current-product claims. See [DR-0017](decisions/DR-0017-single-forte-worksite-and-legacy-retirement.md) and the [retirement register](decisions/RETIREMENT_REGISTER.md).

Current implementation evidence is [FORTE-only worksite Evidence](evidence/FORTE-ONLY-WORKSITE-RETIREMENT-EVIDENCE-20260824.md). Its status is `Limited Verified`; user comprehension and value remain `Draft`.
