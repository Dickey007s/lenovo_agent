# UI—Server Fact Matrix

This matrix is the current product contract. Historical Task/Cockpit/Action mappings are retired and indexed in [RETIREMENT_REGISTER](../decisions/RETIREMENT_REGISTER.md).

## 1. Active worksite facts

| UI state/location | User-visible meaning/action | 服务端权威字段 or event | Transition, recovery and idempotency | 默认隐藏 | Evidence/status |
| --- | --- | --- | --- | --- | --- |
| Header: 连接中 | service/Catalog or Run transport is unresolved | pending health/Catalog/Run request | wait; no business-state transition | request internals, Key | E2E; Limited Verified |
| Header: 服务可用 | API/Catalog is reachable; no active Run SSE | successful health/Catalog and no open EventSource | user may select/start/retry | prior stream state | E2E; Limited Verified |
| Header: 事件流实时 | current nonterminal Run SSE is open | EventSource `open` for current `run_id` | events still require sequence checks | heartbeat/log payload | E2E; Limited Verified |
| Header: 正在重连 | a nonterminal transport failed and recovery is active | EventSource error or failed GET with retained Run | GET Snapshot, then resume `after=N` | raw network exception | E2E; Limited Verified |
| Header: 暂时离线 | API remains unreachable after bounded retry | health request failure | automatic retry plus explicit retry | generic stack trace | E2E; Limited Verified |
| Scenario tabs | three safe FORTE work policies | `GET /v1/harness/scenarios` | selection is local view state; does not mutate a Run | raw task instruction, rubric, solution, path/hash | Catalog tests/E2E; Limited Verified |
| Scenario detail fallback | public list data remains usable while detail is unavailable | list projection exists; detail GET failed | show explicit notice; retry detail later | raw `task.md` fallback | E2E; Limited Verified |
| Source tree | business labels, groups and summaries for allowed inputs | public Scenario `files[]`; Run `source_documents[]` after index | index event freezes Run-scoped refs | absolute/internal path, full hash, parser internals | tests/E2E; Limited Verified |
| Task Contract | goal, deliverables, data boundary, allowed capabilities, human gate summary | public Scenario contract | review before start; no client edits in current slice | sanitized Planner context, grading data | tests/E2E; Limited Verified |
| Start button | create one independent planning round | POST body `scenario_id/idempotency_key/expected_version` | same Owner/key/request replays; conflicting reuse 409 | internal task handle | tests/E2E; Limited Verified |
| Read phase | source index is frozen | Snapshot `status=indexing`, event `workspace_index` | only after server event/Snapshot | raw source path/hash | live/E2E; Limited Verified |
| Plan phase | model is proposing a plan | `planning_started`, `planning_completed` | not proof of validation or execution | Prompt, CoT, raw response | live/E2E; Limited Verified |
| Model receipt | call occurred, model label, elapsed observation, adoption result | `HarnessModelReceipt.called/model/elapsed_ms/output_used` | call/adoption displayed separately | token details, provider trace | live/E2E; Limited Verified |
| Dynamic plan graph | the adopted, public validated candidate and dependencies | public `plan.summary/units[]` | render only public refs; no client-created units | internal input paths and unvalidated candidate | live/E2E; Limited Verified |
| Validate phase | server checks source refs, tools, dependencies, effects and gates | event `plan_validation`, empty `validation_errors` | does not mean business quality or execution | validator internals beyond useful error | live/E2E; Limited Verified |
| Ready banner | plan passed validation and waits before execution | Snapshot `status=ready_to_execute`, event `ready_to_execute` | terminal SSE closes; final GET; “开始新一轮” creates a new Run | any fabricated Worker/tool/Artifact receipt | live/E2E; Limited Verified |
| Failed banner | planning or validation stopped | Snapshot `status=failed`, `validation_errors[]`, `harness_failed` event | terminal GET; user can start new round | stack trace/raw model response | tests/E2E; Limited Verified |
| Catalog unavailable | service reachable but Catalog temporarily failed | Scenario request failure without integrity classification | retain no invented Scenario; automatic/explicit retry | internal exception | E2E; Limited Verified |
| Catalog integrity failure | source package requires repair/update | Scenario 503 with integrity detail | fail closed; retry only after source repair | affected raw path/hash in ordinary UI | tests/E2E; Limited Verified |
| Run not found/wrong Owner | stale or inaccessible Run | GET/SSE 404 before stream creation | clear stale Run; start new round | whether another Owner owns it | route tests; Limited Verified |

## 2. Plan declaration is not execution

| Public unit field | Current meaning | Forbidden UI inference |
| --- | --- | --- |
| `tool=file.read/table.inspect` | proposed allowlisted tool | the file was opened or inspected |
| `tool=artifact.write` | proposed logical workspace write | an Artifact exists |
| `side_effect=run_workspace_write` | candidate may write inside a future Run workspace | source or workspace changed |
| `side_effect=external_action` | candidate crosses a future governed-action boundary | approval, Permit or Connector ran |
| `requires_human_gate=true` | a future execution would require a gate | a gate was created or approved |

The current Snapshot has no Worker status, tool receipt, Artifact version, verification, Commit, approval, Permit or execution receipt. Any corresponding UI is `Draft`.

## 3. Ownership and sequence rules

- Apply only Snapshot versions and Event sequences that are newer than the current client fact.
- SSE `after=N` is a recovery cursor, not a completion signal.
- Terminal events require a final GET; nonterminal interruption requires GET plus resumed SSE.
- Missing and wrong-owner Runs both return 404.
- `X-User-Id` is an unsigned demo placeholder, and all state is one-process memory.
- Client animation, elapsed time, configured model name or prose cannot upgrade a state.

## 4. Lifecycle boundary

The fixed Customer A Task Runtime, quote workbench, Demo 2 controlled Worker run and Demo 3 Action Gate mappings remain historical. Their Evidence is not deleted, but they are not current frontend or API facts. See [DR-0017](../decisions/DR-0017-single-forte-worksite-and-legacy-retirement.md).
