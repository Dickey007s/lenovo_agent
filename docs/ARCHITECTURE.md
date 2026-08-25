# Office Agent V0.2 Architecture

## 1. Current boundary

```text
Browser: FORTE data workbench + trace
  -> seven-path FastAPI surface
  -> BenchmarkScenarioCatalog
       -> pinned manifest/upstream bytes/license
       -> safe Scenario + stable file_ref
       -> bounded XLSX/Markdown preview
       -> private Planner policy context
  -> HarnessRuntime
       -> freeze user instruction + selected file_ref set
       -> deepseek-v4-pro Planner
       -> deterministic plan validation
       -> deepseek-v4-pro Analyst over safe previews
       -> deterministic citation-scope validation
       -> memory Snapshot + ordered SSE + idempotency
  -> completed + review_required=true
```

The current Runtime performs a bounded read-only analysis. It does not invoke Scheduler/Worker, Tool Gateway, ArtifactVersion/Commit, Approval/Permit, Connector or an external action.

## 2. Source and preview boundary

`demo-enterprise-data/forte/manifest.json` binds 11 source files at FORTE commit `345c1ec1487139db9dd319787fa9405ba85d1869`, totaling `115352` bytes. Catalog loading checks declared path, root boundary, symlink, size, SHA-256, type and parser constraints. Task/input files retain upstream bytes and are binary-marked against line-ending normalization.

Raw `task.md` is provenance. It is not previewable and does not enter the public API or Analyst. The Catalog publishes:

- Scenario business fields and safe display metadata;
- stable opaque `file_ref` values derived from Scenario ID plus the allowlisted relative path;
- the first visible XLSX sheet, bounded to 30 columns and 120 data rows; or
- allowlisted input Markdown bounded to 30,000 characters.

Filesystem path, full hash, task instruction, rubric, solution, grading metadata, Prompt, chain of thought and raw model response remain outside ordinary UI.

## 3. User Task Contract

The start command freezes:

- Scenario ID;
- user instruction, or a Scenario default;
- one or more selected `file_ref` values;
- Owner, expected version and idempotency key.

The server rejects duplicate/invalid refs and refs outside the current Scenario. `instruction_source=user|dataset_task` remains visible in the Snapshot. An unknown response can be retried with the same command key; changing content under the key returns 409.

The Scenario policy is expressed as a generic `work_profile`, never a Demo identity:

```json
{
  "task_topology": "single_task | multi_task",
  "orchestration": "bounded_loop | adaptive_swarm",
  "control_requirements": ["evidence_gate", "human_gate", "risk_gate"],
  "current_runtime_scope": "read_only_analysis"
}
```

The first three fields describe the intended reusable capability composition. `current_runtime_scope` prevents that target policy from being mistaken for current execution. The pinned FORTE Catalog currently supplies the profile; dynamic Admission from arbitrary user work remains `Draft`.

## 4. Model and validation boundaries

### Planning call

The Planner receives the user goal, safe file metadata and server policy. It returns a restricted candidate with business intent, dependencies, selected refs and allowlisted tool intent; it does not own internal `side_effect` values.

The server compiles that candidate into a strict `HarnessPlan`: workspace-result intent receives the server-owned write scope, action-preview intent receives the external-action scope and required human gate, and read/inspect/verify intent receives no side effect. The validator then checks unit IDs, dependencies/cycles, selected refs, allowlisted tools, compiled effects, logical Artifact names and gates. Compilation is policy normalization, not tool execution or Artifact mutation.

### Analysis call

The Analyst receives the instruction, validated plan and server-produced safe previews. It returns a strict `HarnessTaskResult` with 1-10 findings, optional follow-ups and `review_required=true`.

The server validates that every finding cites only the frozen selected refs. It does not validate semantic correctness, accounting interpretation, arithmetic, exhaustive coverage or whether a cited source proves the precise sentence. A deterministic Finance regression produces 23 / `1,845,444.71` where the observed model response produced 20 / `2,202,000`; this negative result is evidence that citation-scope validation cannot be treated as answer validation.

Both requests use `deepseek-v4-pro`, temperature 0, strict JSON and `thinking.type=disabled`. Public receipts separately expose `called/model/elapsed_ms/output_used`; no chain of thought is projected.

## 5. State and events

The production path is:

```text
queued
  -> indexing
  -> planning
  -> validating
  -> analyzing
  -> verifying
  -> completed
```

The success trace has eight events:

```text
workspace_index
planning_started
planning_completed
plan_validation
analysis_started
analysis_completed
result_validation
task_completed
```

Each event increments Snapshot version and sequence; a new successful Run starts at v1/seq 0 and ends v9/seq 8. `failed` is terminal. `ready_to_execute` remains a compatibility state when no Analyst adapter exists, but is not the current production success path.

GET and SSE enforce Owner scope; missing and wrong-owner Runs both return 404. Terminal SSE closes and the client performs a final GET. Nonterminal interruptions reconcile Snapshot and resume with `after=N`.

Runs, results, events, in-flight calls and idempotency records live in one API process memory. Restart loses them.

## 6. Frontend projection

The root page imports one workbench:

- dataset browser with search and explicit file selection;
- real bounded file preview;
- user-owned task composer;
- validated plan and cited result views;
- separate planning/analysis receipts;
- eight-event trajectory and fail-closed recovery.

The plan's tool fields are readable intent declarations. The analysis is performed directly by the Harness over Catalog previews; no Tool Gateway or Artifact mutation is implied. `completed` is projected as “初步结果已形成”: a response is ready for review, not that its conclusion is correct or an external business process completed.

## 7. Eight canonical modules

| Module | Current state | Current evidence | Next boundary |
| --- | --- | --- | --- |
| 1. Scenario Pack & Workspace Catalog | Limited Verified | manifest, safe Scenario, stable refs, bounded preview | enterprise source adapters and data policy |
| 2. Task Contract | Limited Verified | user instruction, selected refs, Owner/version/idempotency | editable durable contracts, budget/deadline |
| 3. Planner | Limited Verified | separate Planner and Analyst receipts | quality evaluation, fallback/model policy |
| 4. Admission & Plan Validator | Limited Verified | plan checks plus result citation-scope check | deterministic spreadsheet operator, claim verifier, budgets and replanning admission |
| 5. Scheduler & Worker Manager | Draft | no current execution scheduler | lease, retry, cancellation and recovery |
| 6. Tool Gateway | Draft | retained package is not invoked | current capability registry and receipts |
| 7. Artifact Workspace & Verifier | Partial | memory result plus selected-ref validation | immutable Artifact versions, provenance, merge and Commit |
| 8. Checkpoint, Event & Governance Control | Partial | memory Snapshot, eight ordered events, Owner/idempotency | durable store, production identity and action governance |

Demo 1/2/3 do not add modules. They exercise different compositions of the same modules: Demo 1 uses a single-task bounded loop and pauses on evidence/human gates; Demo 2 uses multi-task adaptive scheduling and shared-artifact convergence; Demo 3 applies the risk gate across either topology before a side effect.

## 8. Lifecycle

[DR-0016](decisions/DR-0016-public-workspace-agent-harness.md) remains the historical planning foundation. [DR-0017](decisions/DR-0017-single-forte-worksite-and-legacy-retirement.md) remains the historical product-convergence decision. [DR-0018](decisions/DR-0018-forte-data-workbench-and-verifiable-trace.md) defines the current workbench. [DR-0019](decisions/DR-0019-capability-composed-agent-runtime.md) defines the generic capability contract and the execution migration boundary.

Current implementation Evidence is [FORTE data workbench and trace](evidence/FORTE-DATA-WORKBENCH-TRACE-EVIDENCE-20260824.md). User comprehension and value remain `Draft`.
