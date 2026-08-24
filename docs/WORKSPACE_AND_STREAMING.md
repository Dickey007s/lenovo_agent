# FORTE Worksite and Streaming

## 1. One worksite

The root page is the product. There is no legacy app rail or “return to workspace” path.

The desktop composition has a main worksite and a resizable right activity rail. The mobile composition keeps the worksite first and moves the activity rail below it with a bounded resize control. These regions project the same Run facts:

- source and Scenario contract;
- progressive read, plan, validate and ready stages;
- validated dynamic plan;
- Agent activity, model receipt and recovery status.

The interface is not a log viewer. It shows business labels, dependencies, validation and user-relevant boundaries while hiding Prompt, chain of thought, raw model response, task instruction, rubric, solution, internal path/hash and secrets.

## 2. Scenario flow

1. The client checks health and loads the safe Scenario list.
2. The user selects one of three FORTE scenarios.
3. Detail loading may enrich the list projection. If detail is temporarily unavailable, the page explicitly says it is using the Catalog's public information; it never falls back to raw `task.md`.
4. “开始本轮” posts a new Owner-scoped Run with an idempotency key.
5. The page renders Snapshot state immediately, opens SSE for nonterminal progress, and applies events only in increasing sequence order.
6. When `ready_to_execute` or `failed` arrives, SSE closes and a final GET reconciles the Snapshot.
7. “开始新一轮” creates a new independent Run. It does not reset or overwrite a prior Run.

Selecting a different Scenario changes the visible public source and contract. It does not migrate an in-flight Run to another Scenario.

## 3. Progressive disclosure

The UI must not open directly on a dense validation result unless the recovered server Snapshot is already in that state.

| Phase | Visible only when | User meaning |
| --- | --- | --- |
| Read | public Scenario exists; `workspace_index` confirms frozen Run sources | which safe files are in this round |
| Plan | `planning_started` / `planning_completed` | the model is proposing a work graph; call and adoption are separate |
| Validate | `plan_validation` | the server checked paths, tools, dependencies, effects and gates |
| Ready | Snapshot `status=ready_to_execute` | plan is reviewable and not executed |

The plan graph is rendered from the public `plan.units[]`; it cannot be reconstructed from animation timing or prose. A plan unit that declares `artifact.write` or `external_action` is still only a validated candidate.

## 4. Connection facts

Frontend connection labels have exact meanings:

| UI label | Fact |
| --- | --- |
| 连接中 | initial health/Catalog or Run transport has not resolved |
| 服务可用 | API/Catalog is available and no active EventSource is open |
| 事件流实时 | the current nonterminal Run EventSource is open |
| 正在重连 | a nonterminal stream or service request failed and recovery is in progress |
| 暂时离线 | retry budget reached with API unreachable |

The UI must not show “事件流实时” merely because a previous stream existed or health is green.

## 5. Catalog failure and recovery

The client distinguishes:

- `service_unreachable`: health request cannot reach the API;
- `catalog_unavailable`: API responds but Catalog cannot currently be loaded;
- `catalog_invalid`: the service reports Catalog integrity failure.

The client performs bounded automatic retry with increasing delay and retains an explicit retry control. On integrity failure it shows that the work scenarios need repair/update, not a generic model or network error. No fixture Scenario is invented.

The incident behind DR-0017 was byte-level: Git LF normalization changed upstream CRLF Markdown while the manifest expected upstream bytes. The fix restores the original bytes, marks source inputs binary, returns a controlled 503 and lets the UI recover after the Catalog is healthy.

## 6. SSE recovery

- Start reading from `after=last_event_sequence`.
- Apply only events with a greater sequence than the last applied event.
- On nonterminal stream failure, mark reconnecting, GET the Snapshot, then resume from its sequence.
- On terminal event, close the EventSource and perform one final GET; do not keep a terminal stream connected.
- A missing or wrong-owner Run returns 404 before StreamingResponse is created.
- Heartbeats are transport liveness only and never change business state.

Snapshot status/version and event sequence are server facts. The client never promotes a Run to ready or failed on its own.

## 7. Current limitations

Run and stream state are single-process memory and disappear on API restart. There is no cross-process event broker, durable checkpoint, background Worker, Connector, production identity or execution recovery.

DR-0017 has no independent screenshot of the final converged UI. The stakeholder screenshot is negative pre-fix evidence; browser E2E is an engineering proxy and not a user study. Current usability, comprehension and value remain `Draft`.
