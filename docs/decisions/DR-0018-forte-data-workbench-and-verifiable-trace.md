# DR-0018: FORTE data workbench and verifiable read-only trace

| Field | Value |
| --- | --- |
| Decision ID | `DR-0018` |
| Date | 2026-08-24 |
| Status | `Limited Verified` for the recorded three-collection implementation; whole-folder foreground is superseded by [`DR-0022`](DR-0022-workspace-folder-and-arbitrary-task-contract.md); usability and user value remain `Draft` |
| Trigger | `USER-FEEDBACK-20260824-DATA-WORKBENCH-10` |
| Scenarios | [SCENARIO-004](../scenarios/SCENARIO-004-forte-finance-durable-evidence.md), [SCENARIO-005](../scenarios/SCENARIO-005-forte-release-adaptive-team.md), [SCENARIO-006](../scenarios/SCENARIO-006-forte-governed-operations-action.md), [SCENARIO-007](../scenarios/SCENARIO-007-single-forte-worksite-entry.md) |
| Evidence | [FORTE-DATA-WORKBENCH-TRACE-EVIDENCE-20260824](../evidence/FORTE-DATA-WORKBENCH-TRACE-EVIDENCE-20260824.md) |
| Implementation | [`fffa36a8cc83e895aaba35276568ad79e348f541`](https://github.com/Dickey007s/lenovo_agent/commit/fffa36a8cc83e895aaba35276568ad79e348f541) + [`041186d`](https://github.com/Dickey007s/lenovo_agent/commit/041186d) |
| Delivery | [PR #25](https://github.com/Dickey007s/lenovo_agent/pull/25), open and not yet merged |

## 1. Problem

The preceding worksite was still organized around explaining three Demo policies and ended at a plan. The stakeholder could not freely inspect the benchmark data, decide which files mattered, ask an original question, or see an actual answer. Dense explanatory copy also competed with the user's real work.

The next vertical slice must make data and user intent primary. It must remain honest about what happened: two bounded model calls and deterministic checks can produce a cited read-only result, but no Tool Gateway, Artifact mutation, Connector or external action runs.

Current applicability note: this Decision preserves the first data-workbench,
two-call trace and numerical negative result. Its three registered collections
and Scenario routes are historical. `DR-0022` now governs one whole folder,
96 safe file projections and a user-authored selected-file task.

## 2. Decision

The root page becomes a `FORTE 数据工作台`:

- left: three business-labeled data collections, search, file selection and stable `file_ref`;
- center: real bounded file preview, a user-editable task composer, validated plan and analysis result tabs;
- right: a compact ordered trajectory with separate planning and analysis receipts;
- bottom boundary: selected-source and no-external-action constraints.

The ordinary foreground does not use Demo 1/2/3 as its primary navigation. [DR-0019](DR-0019-capability-composed-agent-runtime.md) subsequently removed `demo_id` and `experience_policy` from public, internal and Planner Scenario projections in favor of a generic `work_profile`; Demo labels are acceptance/reporting lenses only.

## 3. Seven-path API

DR-0018 adds one bounded preview route to the existing six-path Harness:

```text
GET  /v1/health
GET  /v1/harness/scenarios
GET  /v1/harness/scenarios/{scenario_id}
GET  /v1/harness/scenarios/{scenario_id}/files/{file_ref}
POST /v1/harness/runs
GET  /v1/harness/runs/{run_id}
GET  /v1/harness/runs/{run_id}/events
```

`file_ref` is a stable opaque reference derived from Scenario identity and the allowlisted relative path. The preview endpoint revalidates manifest size/hash and returns only the first visible worksheet, at most 30 columns and 120 data rows, or at most 30,000 Markdown characters. It exposes business labels and cell/text content, not filesystem path, hash, raw `task.md`, rubric, solution or grading metadata.

## 4. Run contract

The start command accepts:

- `scenario_id`;
- a user `instruction` of 3-2,000 characters, or the Scenario default;
- one or more unique `selected_file_refs`;
- `expected_version=1` and an idempotency key.

The server rejects malformed, duplicate, unknown or cross-Scenario file references. A retry after an unknown start result must reuse the same key for the same command; different content with that key returns 409.

The selected sources and instruction are frozen in the Run Snapshot. `instruction_source` distinguishes `user` from `dataset_task`.

## 5. Two-call read-only loop

```text
freeze selected files
  -> planner call
  -> deterministic plan validation
  -> analyst call over safe previews
  -> deterministic file-reference validation
  -> completed, review_required=true
```

Both calls use `deepseek-v4-pro`, strict JSON schemas, temperature 0 and a request with thinking disabled. The foreground exposes `called/model/elapsed_ms/output_used` separately for each call. It does not expose Prompt, chain of thought or raw model responses.

The server validates that every result finding cites at least one selected `file_ref` and no unselected reference. This is citation-scope validation, not semantic proof that the finding, amount or row interpretation is correct. Every successful result therefore has `review_required=true`.

A deterministic Finance-018 cross-period check later reproduced 23 unchanged non-empty balances totaling `1,845,444.71`, while the observed model Snapshot stated 20 items totaling `2,202,000`. This negative result is part of the decision: `result_validation` does not verify business semantics, exhaustive coverage or arithmetic. The foreground therefore says “模型初步结论 · 待复核”, shows three findings by default, and states that the server checked file references and the read-only boundary rather than recomputing the values.

The analyst is called directly with server-produced safe previews. A plan's `tool` or `artifact.write` fields remain declarations; no current Tool Gateway invocation or `ArtifactVersion` mutation occurs. The result lives in the memory Snapshot.

## 6. Ordered foreground trace

A successful current run emits eight events and ends at Snapshot v9 / seq 8:

| Seq | Event | User-visible meaning |
| --- | --- | --- |
| 1 | `workspace_index` | selected files were frozen |
| 2 | `planning_started` | planning model call began |
| 3 | `planning_completed` | plan candidate returned |
| 4 | `plan_validation` | server accepted paths, tools, dependencies and gates |
| 5 | `analysis_started` | analyst began over safe previews |
| 6 | `analysis_completed` | structured result candidate returned |
| 7 | `result_validation` | selected-file citation scope passed |
| 8 | `task_completed` | an initial read-only result is available for human review |

The trace shows observable stages and receipts, not internal reasoning or every hidden retry. Invalid plan/result structure, unknown citation or source-integrity failure ends in `harness_failed`; the UI must not fabricate a partial result.

## 7. Frontend/server fact mapping

| User sees or does | Authoritative fact | Recovery/hidden boundary |
| --- | --- | --- |
| browse a table/Markdown file | preview route response for Scenario + `file_ref` | preview failure is explicit; path/hash/task instruction hidden |
| select files | local selection submitted as `selected_file_refs` | server revalidates membership; at least one remains selected |
| write a task | POST `instruction`, echoed by Snapshot | no hidden benchmark task substituted for a user instruction |
| planning/analysis receipts | `model_receipt` and `analysis_receipt` | configured model name or animation is not call evidence |
| plan | public validated `plan.units[]` | tool labels do not imply tools executed |
| result findings and citations | `result.findings[].file_refs` after `result_validation` | citation membership is not factual correctness |
| “初步结果已形成” | `status=completed`, `task_completed`, result present | means a response passed schema/reference checks, not that its conclusion is correct |
| “仍需你判断” | `review_required=true`, `follow_ups[]` | no automatic approval or action |

## 8. Evidence and boundary

The implementation baseline is `fffa36a8cc83e895aaba35276568ad79e348f541`; follow-up `041186d` binds the review-first result wording, progressive disclosure and deterministic ground-truth regression. Focused Catalog/Runtime verification is `30 passed in 2.46s`; the catalog regression file is `10 passed`. The final Harness browser run is `8 passed in 26.8s`. Full Python is `53 passed in 2.68s`; Ruff and web lint pass; the production build passes with `2.5s` compile, `4.4s` TypeScript and `810ms` static generation. [PR #25](https://github.com/Dickey007s/lenovo_agent/pull/25) is open and not yet merged.

One observed Finance-018 live run reached `completed` v9/seq 8. The planning and analysis calls were both adopted, ten findings cited two stable selected references, and the result required review. A second real Run was captured while running and later reached the same terminal protocol. Exact sanitized facts, screenshot provenance and the negative deterministic comparison are in the linked Evidence and manifest.

`completed` is therefore an orchestration/projection fact, not a quality pass. A deterministic spreadsheet operator and claim-level verification should be the next vertical slice; both remain `Draft` until implemented and evidenced.

This status does not prove arbitrary workbook correctness, semantic claim accuracy, user comprehension, reduced reading load, production identity, durable recovery, cross-process idempotency, Worker scheduling, Artifact convergence, Tool Gateway execution, Connector access or external side effects.

## 9. Rejected alternatives

- **Keep a Demo switcher as the primary shell**: rejected because it makes the system presentation-led rather than work-led.
- **Send filesystem paths to the browser/model**: rejected because stable opaque references are sufficient and safer to project.
- **Expose raw reasoning as the trace**: rejected because observable actions, receipts and validation are the decision-relevant facts.
- **Treat file citation as proof of correctness**: rejected because membership validation cannot verify the model's semantic claim.
- **Call the Snapshot result an Artifact Commit**: rejected because no current Artifact versioning or Commit protocol is invoked.
