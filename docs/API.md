# Office Agent V0.2 API

Base URL: `http://localhost:8010`.

## 1. Public surface

OpenAPI exposes seven paths:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/health` | process health and configured model/storage labels |
| GET | `/v1/harness/workspace` | whole public office folder projection |
| GET | `/v1/harness/workspace/files/{file_ref}` | bounded, integrity-checked file preview |
| POST | `/v1/harness/runs` | start an idempotent bounded read-only Agent Control Loop |
| GET | `/v1/harness/runs?limit=10` | list recent Owner-scoped Runs for recovery |
| GET | `/v1/harness/runs/{run_id}` | Owner-scoped public Snapshot |
| POST | `/v1/harness/runs/{run_id}/controls` | versioned, idempotent pause/resume/steer/stop/rollback |
| GET | `/v1/harness/runs/{run_id}/events?after=N` | ordered named SSE after a sequence |

The former Scenario list/detail/preview routes and legacy
workspace/thread/task/Demo prefixes are not mounted.

## 2. Owner and persistence

Run endpoints use `X-User-Id`; omission uses `demo_user`. This unsigned header
is a demonstration Owner placeholder, not production authentication. Missing
and wrong-owner Runs both return 404 before the SSE response is created.

There are eight operations over seven OpenAPI paths because `GET` and `POST`
share `/runs`. With `DATABASE_DSN`, accepted Run snapshots, start/control
idempotency receipts, ArtifactVersions and TaskCommits are stored in
PostgreSQL; the latter two are independent append-only rows. On startup, an
interrupted nonterminal Run is rolled back to completed rounds, receives
`checkpoint_recovered` and pauses; an in-flight provider request is never
automatically replayed. In-flight HTTP requests, asyncio tasks and conditions
remain process-local. Without `DATABASE_DSN`, the state store is memory and all
Run state disappears on restart.

## 3. Whole workspace

```http
GET /v1/harness/workspace
```

Representative response:

```json
{
  "workspace_id": "forte-public-office",
  "title": "FORTE 公开办公资料库",
  "dataset_version": "345c1ec1487139db9dd319787fa9405ba85d1869",
  "license": "MIT",
  "folder_count": 15,
  "file_count": 96,
  "previewable_file_count": 96,
  "folders": [
    {
      "folder_id": "forte-folder-...",
      "display_label": "财务",
      "availability": "local_input_bundle",
      "file_count": 3,
      "files": [
        {
          "file_ref": "forte-a0bccc1df48cc6a1",
          "display_label": "2025 年上半年往来明细",
          "display_path": "财务/2025 年上半年往来明细.xlsx",
          "extension": ".xlsx",
          "size": 12345,
          "preview_kind": "table",
          "preview_available": true
        }
      ]
    }
  ]
}
```

This projection comes from `public-suite-manifest.json`. It omits benchmark
task instructions, rubric, solution, grading material, source path and digest.
Two task-only external-dependency folders may have zero local input files and
cannot be used to fabricate local data.

`display_path` is a safe business path and may contain nested segments, for
example `算法研发/search_agent_workflow/main.py`. The browser may project these
segments as a folder tree. Expand, search and type-filter state is client-owned;
it does not change the server workspace projection or a Run's whole-workspace
scope. `display_path` is not an operating-system absolute path.

## 4. File preview

```http
GET /v1/harness/workspace/files/forte-a0bccc1df48cc6a1
```

All preview responses include business labels, size, bounded content and:

```json
{
  "security": {
    "integrity_verified": true,
    "read_only": true,
    "active_content_executed": false,
    "external_resources_loaded": false,
    "notes": ["..."]
  }
}
```

Preview kinds:

| Kind | Formats | Bounded output |
| --- | --- | --- |
| `table` | XLSX, CSV | at most 30 columns and 120 rows |
| `document` | DOCX | at most 30,000 extracted characters |
| `pdf` | PDF text layer | page count plus at most 30,000 characters |
| `text` | TXT, Markdown, JSON, logs and code | at most 30,000 characters |
| `unavailable` | encrypted/unsupported/unsafe | safe reason, no guessed content |

Before reading, the Catalog validates relative allowlisted path, declared size,
SHA-256, non-symlink file and archive expansion bounds. It rejects DOCM/macro
content, does not run active content and does not fetch external resources.
Unknown ref is 404; source integrity failure is controlled 503.

## 5. Start a Run

```http
POST /v1/harness/runs
X-User-Id: demo_user
Content-Type: application/json
```

```json
{
  "workspace_id": "forte-public-office",
  "idempotency_key": "harness:client-generated-key",
  "expected_version": 1,
  "instruction": "研究整个资料库，找出值得继续推动的工作，并逐条引用依据。",
  "loop": {
    "max_rounds": 3,
    "max_files_per_round": 6,
    "max_model_calls": 6,
    "deadline_seconds": 120
  }
}
```

`instruction` is required and contains 3-2,000 characters. The request does not
accept `selected_file_refs`: the server freezes the complete allowlisted input
index and the Planner autonomously selects a bounded evidence set for each
round. Sending a client-owned file scope is rejected as an unknown field.

`loop` is optional and defaults to the values above. Bounds are 1-3 rounds,
1-8 files per round, 2-6 model calls and 20-300 seconds. The server freezes
these values plus `scope_mode=whole_workspace` and all stable input refs into
`AgentControlLoopContract`; the browser cannot change the scope or budget while
a Run is active.

The response is `202 Accepted` with `{"run": snapshot, "replayed": false}`.
Reusing the same Owner/key/request returns the original start result with
`replayed=true`. Reusing that key for different content returns 409.

`GET /v1/harness/runs?limit=10` returns `{"runs": [...]}` ordered by the
latest server update. It is Owner-scoped and exists so a browser without local
session state can discover a recoverable nonterminal Run. The client must still
GET the selected Run and reconnect SSE from its authoritative sequence.

## 6. Public Snapshot

Important fields:

```json
{
  "run_id": "harness:...",
  "workspace_id": "forte-public-office",
  "status": "completed",
  "version": 22,
  "last_event_sequence": 21,
  "instruction": "...",
  "instruction_source": "user",
  "source_documents": [
    {"file_ref": "forte-...", "display_label": "...", "display_group": "..."}
  ],
  "contract": {
    "contract_version": "agent-control-loop.v1",
    "goal": "...",
    "scope_mode": "whole_workspace",
    "allowed_file_refs": ["forte-...", "... all 96 stable refs ..."],
    "max_rounds": 3,
    "max_files_per_round": 6,
    "max_model_calls": 6,
    "deadline_seconds": 120,
    "external_action": "none"
  },
  "budget": {
    "rounds_used": 2,
    "files_verified": 8,
    "model_calls_used": 5,
    "elapsed_ms": 71461
  },
  "rounds": [],
  "branches": [
    {
      "branch_id": "branch-...",
      "unit_id": "verify-revenue",
      "round_number": 1,
      "parent_branch_id": null,
      "title": "核对收入证据",
      "depends_on": [],
      "input_file_refs": ["forte-..."],
      "verified_file_refs": ["forte-..."],
      "missing_file_refs": [],
      "status": "completed",
      "requires_human_gate": false
    }
  ],
  "active_branch_id": null,
  "control_state": "running",
  "control_events": [],
  "artifact_versions": [
    {
      "artifact_id": "artifact-...",
      "version": 1,
      "status": "verified",
      "kind": "evidence_brief",
      "round_number": 1,
      "summary": "...",
      "findings": [],
      "follow_ups": [],
      "evidence_gaps": [],
      "source_file_refs": ["forte-..."],
      "review_required": true,
      "external_action": "none"
    }
  ],
  "commits": [
    {
      "commit_id": "commit-...",
      "artifact_id": "artifact-...",
      "artifact_version": 1,
      "operation": "commit",
      "parent_commit_id": null,
      "external_action": "none"
    }
  ],
  "last_commit": {
    "commit_id": "commit-...",
    "artifact_version": 1,
    "operation": "commit",
    "external_action": "none"
  },
  "brief": {
    "outcome": "completed",
    "rounds_completed": 2,
    "external_action": "none"
  },
  "plan": {
    "summary": "...",
    "selection_reason": "为什么本轮选择这些文件",
    "units": []
  },
  "model_receipt": {
    "called": true,
    "model": "deepseek-v4-pro",
    "elapsed_ms": 14685,
    "output_used": true
  },
  "analysis_receipt": {
    "called": true,
    "model": "deepseek-v4-pro",
    "elapsed_ms": 18041,
    "output_used": true
  },
  "result": {
    "summary": "...",
    "findings": [
      {"title": "...", "detail": "...", "file_refs": ["forte-..."]}
    ],
    "follow_ups": ["由用户确认后可作为新 Run 启动的下一步任务"],
    "review_required": true
  },
  "validation_errors": []
}
```

`source_documents` and `contract.allowed_file_refs` are the full safe workspace
index. They are not the files read by the Analyst. The authoritative per-round
evidence scope is `rounds[].input_file_refs`, and the public reason is
`rounds[].plan.selection_reason`. The server compiler caps the union of those
refs at `max_files_per_round` before any file content reaches the Analyst.

`branches[]` is the server-owned projection of validated plan units. Branch
identity, dependency, verified/missing refs and status are not model-owned UI
interpretations. `rounds[].branch_ids` connects a round to its Branch records;
`active_branch_id` identifies the branch selected for a resumed evidence round.

`result.follow_ups` contains at most four model-proposed next tasks. It is not a
server-side acceptance record. The current browser starts a separate Run only
after the user confirms one proposal. There is no per-follow-up citation field
in the current contract. A review UI may show the current result's Finding refs
as explicitly labeled context, but must not present them as direct evidence for
an individual proposal.

The issue-review page adds no endpoint. Finding review uses its own `file_refs`;
Gap/Branch review uses `candidate_file_refs` or `missing_file_refs`; actual
content still comes from the preview endpoint. Opening or closing review is a
client action and does not change Run version or create a ControlEvent.

Current statuses are `queued`, `indexing`, `planning`, `validating`,
`analyzing`, `verifying`, `waiting_input`, `paused`, `completed`, `stopped`
and `failed`;
compatibility `ready_to_execute` is retained for runtimes built without an
Analyst.

`artifact_versions` and `commits` are safe Snapshot projections of independent
append-only Store records. ArtifactVersion contains the complete logical
read-only brief for one completed round; it remains `draft` or `verified` and is
not mutated to represent submission. TaskCommit separately selects the current
version. `operation=rollback` means the current brief pointer was restored to a
historical version by creating another Commit. None of these facts means an
original office file or external system changed.

`completed` means the Evidence Gate found no unresolved citation gap in the
selected evidence and the read-only results passed schema, selected-citation
and boundary checks. It does not mean the answer is semantically correct or a
plan-declared tool executed.

## 7. Control a Run

```http
POST /v1/harness/runs/{run_id}/controls
X-User-Id: demo_user
Content-Type: application/json

{
  "command": "steer",
  "instruction": "下一轮优先核对付款条件",
  "expected_version": 12,
  "idempotency_key": "control-client-generated-key"
}
```

Commands are `pause`, `resume`, `steer`, `stop` and `rollback`. `steer` requires
an instruction and applies only to the next round. Pause and stop are accepted
immediately but applied only at a safe point between model calls. A stale
version, illegal transition or same key with different content returns 409. An
identical replay returns the first control result with `replayed=true`.

When the Evidence Gate emits `next_step.decision=waiting_input`, the Snapshot
already has `control_state=paused`. `resume` must carry one waiting
`branch_id`; it authorizes only that branch's next evidence round. The round is
restricted to that Branch's `missing_file_refs`, its validated plan must cover
all of them, and other waiting branches remain unchanged. A missing, unknown or
non-waiting Branch returns 409. For backward compatibility, a resume without a
Branch selects only the first waiting branch; it never advances all branches.

`rollback` applies only to a terminal committed Run and requires
`artifact_version`. The server loads and verifies that independent
ArtifactVersion, rejects restoring the already-current version, then appends a
new `operation=rollback` TaskCommit and returns the restored brief. It does not
delete versions, undo a model call or modify workspace files. A Run retains at
most 20 TaskCommit records; reaching that bound fails closed and requires a new
independent Run instead of truncating history.

## 8. Plan policy and result validation

The provider returns a plan candidate, not the public plan. The server compiles
allowlisted intent into owned effect/gate semantics, then validates unit IDs,
dependencies, source refs, tools, logical artifacts and human gates. Raw
candidate fields and compiler errors are not public facts.

A plan that fails structure or deterministic validation is marked `未采用`.
The server permits at most one repair attempt, only when the same Loop budget
still has a model call and time available. Both attempts consume the budget and
produce ordered events. There is no unbounded or hidden retry loop.

The current Analyst receives safe projections only from selected refs. Each
finding requires at least one selected `file_ref`; an out-of-scope citation
fails the Run. This proves reference membership only, not entailment,
exhaustiveness, arithmetic or policy correctness.

## 9. SSE

```http
GET /v1/harness/runs/{run_id}/events?after=3
Accept: text/event-stream
```

Representative two-round success order:

```text
workspace_index
round_started
planning_started
planning_completed
plan_validation_rejected (optional, followed by one retry)
plan_validation
analysis_started
analysis_completed
result_validation
evidence_gate
control_resume_recorded (required when evidence_gate waits for the user)
round_started
planning_started
planning_completed
plan_validation
analysis_started
analysis_completed
result_validation
evidence_gate
loop_committed
artifact_version_restored (optional later human restore)
```

`checkpoint_recovered` may appear after an API restart backed by PostgreSQL.
It proves a persisted Snapshot was restored and the Run paused; it does not
prove an interrupted model call was resumed or replayed.

SSE `id` equals the event sequence. `after=N` returns only later events.
Heartbeats carry no business state. A terminal event is followed by final GET
reconciliation; a nonterminal interruption uses GET plus `after=N` recovery.

## 10. Error semantics

| Result | Meaning | Frontend response |
| --- | --- | --- |
| connection failure | API unreachable | keep draft; bounded automatic/explicit retry |
| workspace 503 | manifest/catalog integrity invalid | show integrity-specific fail-closed state; no model call |
| preview 404 | unknown ref | keep selection; show explicit preview error |
| preview 503 | selected byte failed integrity/safe parsing | never show stale/partial content |
| Run/SSE 404 | missing or wrong Owner | same public response; clear stale Run |
| start 409 | idempotency/contract conflict | preserve instruction/selection and reconcile |
| control 409 | stale version or illegal transition | GET current Snapshot; preserve command draft and let the user retry |
| branch control 409 | selected Branch is missing, no longer waiting or outside the current Gate | GET current Snapshot and choose a still-waiting Branch |
| artifact restore 409 | version is current, missing or fails independent-record verification | keep current pointer and history; do not fabricate restore |
| `status=waiting_input` | one or more Branches could close a visible evidence gap | inspect sources, optionally steer, then explicitly resume one Branch or stop |
| `checkpoint_recovered` | server restored a PostgreSQL Snapshot and paused | reconcile the trace; explicitly resume from the safe checkpoint |
| `loop_budget_stopped` | round/call/deadline prevents another step | show bounded brief and unresolved gaps |
| `status=failed` | model/schema/plan/source/citation validation failed | show safe business error and no result |

See [UI-server fact matrix](contracts/UI_SERVER_FACT_MATRIX.md),
[`DR-0026`](decisions/DR-0026-selective-branch-and-immutable-artifact-history.md)
and [current Evidence](evidence/DEMO1-BRANCH-ARTIFACT-CONTROL-EVIDENCE-20260826.md).
