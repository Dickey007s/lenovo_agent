# FORTE Data Workbench and Streaming

## 1. Work-led layout

The root page is one data workbench, not a Demo selector or internal log console.

- left: searchable FORTE collections and explicit file checkboxes;
- center: task composer plus data, plan and result views;
- right: compact Agent trajectory and two model receipts;
- mobile: the same facts remain usable at 390px without horizontal overflow.

The interface prioritizes actual data and the user's task. Explanatory policy text is secondary and collapsible.

## 2. Browse and select

1. Health and Scenario list load.
2. The first business collection opens with all its files selected.
3. Clicking a file requests `/scenarios/{scenario_id}/files/{file_ref}`.
4. XLSX preview shows a bounded real table; Markdown preview shows bounded input text.
5. A user can search collections and uncheck files, but the UI keeps at least one selected.
6. Changing collection resets the current Run/trace and selects that collection's file set.

Preview state is independent from Run state. A preview error must not fabricate data or silently substitute another file.

## 3. User-owned task

The task composer accepts a free-form instruction and shows how many files are selected. Starting sends the exact trimmed instruction and selected `file_ref` values with an idempotency key.

If the start response is unknown, the local command retains its key. A retry with unchanged Scenario/instruction/files reuses it. Editing the task or selection creates a new command signature/key.

The Snapshot echoes `instruction` and `instruction_source`. The frontend must not replace a user instruction with hidden benchmark text.

## 4. Progressive trajectory

| Stage | Server fact | User meaning |
| --- | --- | --- |
| selected sources frozen | `workspace_index` | these files define the current context |
| planning call | `planning_started/completed` + `model_receipt` | a work graph candidate was requested/returned |
| plan check | `plan_validation` | paths, refs, tools, dependencies and gates passed |
| analysis call | `analysis_started/completed` + `analysis_receipt` | a structured read-only result candidate was requested/returned |
| result check | `result_validation` | all finding refs belong to the selected set |
| initial result | `status=completed`, `task_completed`, result present | “初步结果已形成”; a response is available and still needs human review |

The trace shows observable server stages, not chain of thought or raw logs. “结果采用” comes from the matching receipt's `output_used=true`; elapsed animation is not evidence.

## 5. Data, plan and result views

### Data preview

Shows safe display labels, sheet/text content and truncation. It hides internal path/hash and task/grading metadata.

### Task plan

Shows validated public units, dependencies, selected file labels and business tool labels. A displayed `artifact.write` or `action.preview` is proposed intent only; the current Runtime does not invoke those tools.

### Analysis result

Shows “模型初步结论 · 待复核”, a three-line summary, three findings by default, file-label citations and follow-ups. “展开结论” and “查看其余7条发现” are explicit user actions for the observed ten-finding result. The footer says the result is model-generated, reference-scope checked, subject to human review, and has no external action.

The server did not recompute the displayed numbers. A deterministic Finance regression found 23 / `1,845,444.71` while the observed model response stated 20 / `2,202,000`. The UI must therefore describe `result_validation` as a file-reference and read-only-boundary check, never as numerical or semantic verification.

The view switches to result only after a `completed` Snapshot with a valid result. Failure must keep the result tab disabled.

## 6. Connection semantics

| UI label | Exact fact |
| --- | --- |
| 连接中 | initial transport unresolved |
| 服务可用 | API/Catalog reachable; no active EventSource |
| 轨迹实时 | current nonterminal EventSource open |
| 正在重连 | nonterminal recovery active |
| 暂时离线 | retry budget reached with API unreachable |

Catalog loading distinguishes service unreachable, temporary Catalog failure and integrity failure. It uses bounded automatic retry plus explicit retry and never invents a fallback Scenario.

## 7. SSE recovery

- apply only events with sequence greater than the last applied;
- after each nonterminal event, GET the Snapshot;
- on nonterminal stream error, GET then reconnect with `after=N`;
- on `task_completed`, `harness_failed` or compatibility `ready_to_execute`, close SSE and perform one final GET;
- treat heartbeat as transport liveness only;
- missing/wrong-owner Run returns 404 before stream creation.

Snapshot version and event sequence are server facts. The client cannot promote a task to completed.

## 8. Privacy and current limits

Ordinary UI hides raw `task.md`, Planner policy context, Prompt, chain of thought, raw model response, path, hash, rubric, solution, credentials and lower-level logs. The Analyst receives safe previews only.

All Run state is memory-only. There is no background Scheduler/Worker, Tool Gateway execution, versioned Artifact, durable recovery, production identity, Connector or external action.

DR-0018 includes one actual running screenshot and two result screenshots produced by replaying a real persisted Snapshot through the same formal UI. Replay is not another model call or product history/restart recovery. These screenshots and browser E2E support tested engineering behavior, not the claim that users find the page clearer or the trajectory easier to understand; no target-user study exists.
