# Office Agent V0.2 API

Base URL: `http://localhost:8010`.

## 1. Public surface

OpenAPI exposes exactly seven paths:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/health` | process health and configured model/storage labels |
| GET | `/v1/harness/scenarios` | safe Scenario list |
| GET | `/v1/harness/scenarios/{scenario_id}` | one safe Scenario |
| GET | `/v1/harness/scenarios/{scenario_id}/files/{file_ref}` | bounded allowlisted file preview |
| POST | `/v1/harness/runs` | start an idempotent read-only task |
| GET | `/v1/harness/runs/{run_id}` | Owner-scoped public Snapshot |
| GET | `/v1/harness/runs/{run_id}/events?after=N` | ordered SSE after a sequence |

Legacy workspace/thread/task/Demo prefixes remain unmounted.

## 2. Owner and persistence

Harness Run endpoints use `X-User-Id`; omitted requests use demo default `demo_user`. This unsigned header is not production authentication. Missing and wrong-owner Runs both return 404 before SSE StreamingResponse creation.

Runs, results, receipts, events, in-flight model calls and idempotency records live in one API process memory and disappear on restart.

## 3. Scenario and stable files

Scenario responses contain business fields and:

```json
{
  "work_profile": {
    "task_topology": "single_task",
    "orchestration": "bounded_loop",
    "control_requirements": ["evidence_gate", "human_gate"],
    "current_runtime_scope": "read_only_analysis"
  },
  "files": [
    {
      "file_ref": "forte-a0bccc1df48cc6a1",
      "display_label": "2025 年上半年往来明细",
      "display_group": "财务往来",
      "display_summary": "Excel 表格，共 1 个工作表；..."
    }
  ]
}
```

`work_profile` is a generic capability composition, not a Demo switch. Public, internal and Planner projections omit `demo_id` and `experience_policy`. `current_runtime_scope=read_only_analysis` is authoritative for the current Runtime; `bounded_loop` or `adaptive_swarm` describes the target organization policy and does not prove that executor ran.

`file_ref` is stable for a pinned Scenario/path pair and hides the relative path. Public Scenario payloads omit raw task instruction, rubric, solution, grading, path and hash.

## 4. File preview

```http
GET /v1/harness/scenarios/Finance-018/files/forte-a0bccc1df48cc6a1
```

Table response:

```json
{
  "scenario_id": "Finance-018",
  "file_ref": "forte-a0bccc1df48cc6a1",
  "display_label": "2025 年上半年往来明细",
  "display_group": "财务往来",
  "display_summary": "...",
  "kind": "table",
  "sheet_name": "sheet1",
  "columns": ["科目名称", "客商名称", "方向"],
  "rows": [{"row_number": 2, "values": ["...", "...", "..."]}],
  "total_rows": 75,
  "text": null,
  "truncated": false
}
```

The Catalog rechecks size/hash before each preview. XLSX output is the first visible sheet, at most 30 columns and 120 data rows. Markdown output is at most 30,000 characters. Unknown Scenario/ref returns 404; source-integrity failure returns controlled 503.

Preview is a bounded projection of public benchmark input, not an arbitrary filesystem read API.

## 5. Start a Run

```http
POST /v1/harness/runs
X-User-Id: demo_user
Content-Type: application/json
```

```json
{
  "scenario_id": "Finance-018",
  "idempotency_key": "harness:client-generated-key",
  "expected_version": 1,
  "instruction": "只检查余额连续不变的客商，并说明引用文件。",
  "selected_file_refs": [
    "forte-a0bccc1df48cc6a1",
    "forte-b6e701bcf4494076"
  ]
}
```

`instruction` is optional, 3-2,000 characters; omission uses the Scenario default and records `instruction_source=dataset_task`. `selected_file_refs` is optional; omission selects the Scenario's allowlisted inputs. When supplied, it must be nonempty, unique, well-formed and belong to that Scenario.

The response is `202 Accepted` with `{"run": snapshot, "replayed": false}`. Reusing the same Owner/key/request returns the prior start result with `replayed=true`. Reusing the key for different content returns 409.

## 6. Snapshot

Important public fields:

```json
{
  "run_id": "harness:...",
  "scenario_id": "Finance-018",
  "status": "completed",
  "version": 9,
  "last_event_sequence": 8,
  "instruction": "...",
  "instruction_source": "user",
  "source_documents": [{"file_ref": "...", "display_label": "..."}],
  "plan": {"summary": "...", "units": []},
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
    "follow_ups": ["..."],
    "review_required": true
  },
  "validation_errors": [],
  "events": []
}
```

Statuses are `queued`, `indexing`, `planning`, `validating`, `analyzing`, `verifying`, `completed`, `failed`, plus compatibility `ready_to_execute` when the Runtime is built without an Analyst.

For the current Runtime, `completed` means an Analyst response passed schema, citation-scope and read-only-boundary checks. The business UI projects this as “初步结果已形成”. It does not mean the answer is correct, plan-declared tools executed, an ArtifactVersion was committed or an external system changed.

### Plan candidate compilation

The provider response is not the public `HarnessPlan` and does not own `side_effect`. The server compiles allowlisted intent before validation: result-write intent maps to the current Run workspace, action preview maps to an external-action declaration with a human gate, and read/inspect/verify intent maps to no side effect. Raw candidate fields and internal compiler errors are not public API facts.

## 7. Result validation

`HarnessTaskResult` requires 1-10 findings and `review_required=true`. Each finding needs at least one `file_ref`. The server checks that all cited refs belong to the frozen selected source set.

This is reference-membership validation. The API does not claim semantic proof, formula verification, exhaustive matching or row-level entailment. A preserved Finance-018 regression recomputes 23 unchanged balances totaling `1,845,444.71`, whereas one live model Snapshot stated 20 and `2,202,000`; see [DR-0018 Evidence](evidence/FORTE-DATA-WORKBENCH-TRACE-EVIDENCE-20260824.md). The current server therefore does not present `result_validation` as a quality pass.

## 8. SSE

```http
GET /v1/harness/runs/{run_id}/events?after=3
Accept: text/event-stream
```

Successful production order:

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

The SSE `id` equals event sequence. `after=N` returns only later events. Heartbeats carry no business state. Terminal event closes the stream and requires final GET reconciliation; nonterminal interruption uses GET plus `after=N` recovery.

## 9. Error meaning

| Result | Meaning | Frontend behavior |
| --- | --- | --- |
| connection failure | API unreachable | bounded automatic and explicit retry |
| Scenario 503 | Catalog unavailable/integrity invalid | fail closed; do not invent data |
| preview 404 | unknown Scenario/ref | keep selection; show explicit preview error |
| preview 503 | selected source failed integrity | do not show stale/partial preview |
| Run/SSE 404 | missing or wrong Owner | do not reveal ownership; clear stale Run |
| start 409 | idempotency/contract conflict | preserve task and reconcile |
| `status=failed` | plan, model structure, source or citation validation failed | show safe business error; do not enable a result; hide raw tool/effect identifiers |

Public `validation_errors[]` are a fail-closed business projection. Raw validator/compiler details remain internal. A known terminal retry creates a new command/key; only an unknown start outcome with the unchanged command signature reuses the original idempotency key.

See [UI—server fact matrix](contracts/UI_SERVER_FACT_MATRIX.md).
