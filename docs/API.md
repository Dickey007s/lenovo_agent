# Office Agent V0.2 API

Base URL: `http://localhost:8010`.

## 1. Public surface

OpenAPI exposes six paths:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/health` | process health and configured model/storage labels |
| GET | `/v1/harness/workspace` | whole public office folder projection |
| GET | `/v1/harness/workspace/files/{file_ref}` | bounded, integrity-checked file preview |
| POST | `/v1/harness/runs` | start an idempotent read-only task |
| GET | `/v1/harness/runs/{run_id}` | Owner-scoped public Snapshot |
| GET | `/v1/harness/runs/{run_id}/events?after=N` | ordered named SSE after a sequence |

The former Scenario list/detail/preview routes and legacy
workspace/thread/task/Demo prefixes are not mounted.

## 2. Owner and persistence

Run endpoints use `X-User-Id`; omission uses `demo_user`. This unsigned header
is a demonstration Owner placeholder, not production authentication. Missing
and wrong-owner Runs both return 404 before the SSE response is created.

Runs, model receipts, results, events, in-flight calls and idempotency records
live in one API process memory and disappear on restart.

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
  "instruction": "比较所选文件中的关键变化，并逐条引用依据。",
  "selected_file_refs": [
    "forte-a0bccc1df48cc6a1",
    "forte-b6e701bcf4494076"
  ]
}
```

`instruction` is required and contains 3-2,000 characters.
`selected_file_refs` is required, unique and contains 1-20 stable refs from the
one workspace. The server rejects unknown refs and supplies no benchmark-task
fallback.

The response is `202 Accepted` with `{"run": snapshot, "replayed": false}`.
Reusing the same Owner/key/request returns the original start result with
`replayed=true`. Reusing that key for different content returns 409.

## 6. Public Snapshot

Important fields:

```json
{
  "run_id": "harness:...",
  "workspace_id": "forte-public-office",
  "status": "completed",
  "version": 9,
  "last_event_sequence": 8,
  "instruction": "...",
  "instruction_source": "user",
  "source_documents": [
    {"file_ref": "forte-...", "display_label": "...", "display_group": "..."}
  ],
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
    "follow_ups": [],
    "review_required": true
  },
  "validation_errors": []
}
```

Current statuses are `queued`, `indexing`, `planning`, `validating`,
`analyzing`, `verifying`, `completed` and `failed`; compatibility
`ready_to_execute` is retained for runtimes built without an Analyst.

`completed` means a read-only result passed schema, selected-citation and
boundary checks. It does not mean the answer is correct, plan-declared tools
ran, a versioned Artifact was committed or an external system changed.

## 7. Plan policy and result validation

The provider returns a plan candidate, not the public plan. The server compiles
allowlisted intent into owned effect/gate semantics, then validates unit IDs,
dependencies, source refs, tools, logical artifacts and human gates. Raw
candidate fields and compiler errors are not public facts.

The current Analyst receives safe projections only from selected refs. Each
finding requires at least one selected `file_ref`; an out-of-scope citation
fails the Run. This proves reference membership only, not entailment,
exhaustiveness, arithmetic or policy correctness.

## 8. SSE

```http
GET /v1/harness/runs/{run_id}/events?after=3
Accept: text/event-stream
```

Current success order:

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

SSE `id` equals the event sequence. `after=N` returns only later events.
Heartbeats carry no business state. A terminal event is followed by final GET
reconciliation; a nonterminal interruption uses GET plus `after=N` recovery.

## 9. Error semantics

| Result | Meaning | Frontend response |
| --- | --- | --- |
| connection failure | API unreachable | keep draft; bounded automatic/explicit retry |
| workspace 503 | manifest/catalog integrity invalid | show integrity-specific fail-closed state; no model call |
| preview 404 | unknown ref | keep selection; show explicit preview error |
| preview 503 | selected byte failed integrity/safe parsing | never show stale/partial content |
| Run/SSE 404 | missing or wrong Owner | same public response; clear stale Run |
| start 409 | idempotency/contract conflict | preserve instruction/selection and reconcile |
| `status=failed` | model/schema/plan/source/citation validation failed | show safe business error and no result |

See [UI-server fact matrix](contracts/UI_SERVER_FACT_MATRIX.md),
[`DR-0022`](decisions/DR-0022-workspace-folder-and-arbitrary-task-contract.md)
and [current Evidence](evidence/FORTE-FOLDER-WORKSPACE-EVIDENCE-20260825.md).
