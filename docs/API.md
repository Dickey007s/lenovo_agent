# Office Agent V0.2 API

Base URL: `http://localhost:8010`.

## 1. Public surface

The application exposes exactly six OpenAPI paths:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/health` | process health and configured model/storage labels |
| GET | `/v1/harness/scenarios` | safe public Scenario list |
| GET | `/v1/harness/scenarios/{scenario_id}` | one safe public Scenario |
| POST | `/v1/harness/runs` | start an independent planning round |
| GET | `/v1/harness/runs/{run_id}` | read the Owner-scoped public Snapshot |
| GET | `/v1/harness/runs/{run_id}/events?after=N` | ordered SSE after a sequence |

Legacy `/v1/workspace`, `/v1/threads`, `/v1/tasks`, `/v1/demo1`, `/v1/demo2` and `/v1/demo3` prefixes are not mounted and return 404.

## 2. Owner and durability

Harness endpoints use `X-User-Id`; if omitted, the demo default is `demo_user`. This header is unsigned and is not production authentication. GET and SSE return the same 404 for missing and wrong-owner Runs so resource existence is not disclosed across Owners.

Runs, events, in-flight planning tasks and idempotency results are single-process memory. API restart loses them.

## 3. Scenario projection

`GET /v1/harness/scenarios` returns:

```json
{
  "scenarios": [
    {
      "scenario_id": "Finance-018",
      "demo_id": "demo1",
      "title": "跨期间财务证据任务",
      "goal": "...",
      "deliverables": ["..."],
      "data_boundary": "...",
      "human_gate_summary": "...",
      "allowed_capabilities": ["..."],
      "dataset_label": "公开办公基准数据 · FORTE",
      "dataset_version": "FORTE 公开版本 · 345c1ec",
      "experience_policy": "durable_task",
      "files": [
        {
          "display_label": "...",
          "display_group": "...",
          "display_summary": "..."
        }
      ]
    }
  ]
}
```

The projection intentionally omits raw task instruction, rubric, solution, grading fields, internal path, absolute path and full hash. Catalog integrity failure returns `503 {"detail":"场景目录完整性校验失败"}`; no partial Scenario is returned.

## 4. Start a Run

```http
POST /v1/harness/runs
X-User-Id: demo_user
Content-Type: application/json
```

```json
{
  "scenario_id": "Finance-018",
  "idempotency_key": "ui-20260824-example",
  "expected_version": 1
}
```

The response is `202 Accepted`:

```json
{
  "run": {
    "run_id": "harness:...",
    "owner_id": "demo_user",
    "scenario_id": "Finance-018",
    "status": "queued",
    "version": 1,
    "last_event_sequence": 0,
    "source_documents": [],
    "selection_reason": null,
    "plan": null,
    "model_receipt": null,
    "validation_errors": [],
    "events": []
  },
  "replayed": false
}
```

Reusing the same Owner/idempotency key with the same request returns the prior result and `replayed=true`. Reusing it for a different request, or violating the start contract, returns 409.

## 5. Snapshot and plan

Run status is one of `queued`, `indexing`, `planning`, `validating`, `ready_to_execute`, or `failed`.

A public plan unit contains:

```json
{
  "unit_id": "unit-1",
  "title": "...",
  "objective": "...",
  "input_file_refs": ["source-1"],
  "depends_on": [],
  "tool": "file.read",
  "requires_human_gate": false,
  "side_effect": "none",
  "artifact_name": null,
  "artifact_type": null
}
```

`input_file_refs` are public Run-scoped references, not source paths. `model_receipt` contains `called`, `model`, `elapsed_ms`, and `output_used`. Model call, adoption and validation must be presented separately.

`ready_to_execute` is the current terminal success state. It means the plan passed deterministic validation and is waiting at an execution boundary; it does not mean a Worker, tool, Artifact or external action ran.

## 6. SSE

```http
GET /v1/harness/runs/{run_id}/events?after=3
Accept: text/event-stream
X-User-Id: demo_user
```

Each message uses the event sequence as SSE `id`:

```text
id: 4
event: plan_validation
data: {"sequence":4,"event_name":"plan_validation","status":"validating",...}
```

A normal successful order is:

```text
workspace_index
planning_started
planning_completed
plan_validation
ready_to_execute
```

`after=N` returns only later events. The client must apply monotonically increasing sequence values and reconcile with GET after terminal events or transport interruption. Heartbeats carry no business state.

## 7. Errors and frontend meaning

| HTTP/result | Meaning | Required frontend behavior |
| --- | --- | --- |
| connection failure | API unreachable | show service recovery state; bounded automatic retry and explicit retry |
| 503 from Scenario routes | Catalog unavailable or integrity invalid | keep fail closed; show Catalog-specific message; never invent sources |
| 404 Scenario | unknown Scenario | keep current safe selection or ask user to choose |
| 404 Run/SSE | missing or wrong Owner | do not reveal ownership; clear stale Run and start a new round |
| 409 start | idempotency or contract conflict | preserve local context and reconcile rather than double-start |
| `status=failed` | planning/validation failed | show `validation_errors`; do not show a ready or execution-success state |

See [UI—server fact matrix](contracts/UI_SERVER_FACT_MATRIX.md) and [worksite streaming behavior](WORKSPACE_AND_STREAMING.md).
