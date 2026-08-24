# FORTE data workbench and verifiable trace Evidence (2026-08-24)

## Status

`Limited Verified` for the fixed public FORTE workbench, bounded file preview, user-authored task contract, two-call read-only analysis, selected-file citation validation and ordered trace. User comprehension, reduced cognitive load, semantic result correctness and production readiness remain `Draft`.

## Claim under test

At implementation `fffa36a8cc83e895aaba35276568ad79e348f541` plus follow-up `041186d`, the sole product page lets a user browse allowlisted benchmark content, select files, submit an original instruction, receive a cited read-only analysis, and inspect server-backed stages and two model receipts. The successful path ends at `completed`, but no Tool Gateway, Artifact mutation, Connector or external action occurs.

## Source and decision

| Item | Evidence | Supports | Limitation |
| --- | --- | --- | --- |
| stakeholder feedback | [`USER-FEEDBACK-20260824-DATA-WORKBENCH-10`](../sources/USER-FEEDBACK-20260824-10-data-workbench-and-trace.md) | data-first UI, free browsing/task input, compact verifiable trace | one stakeholder; no user study and no feedback screenshot |
| design decision | [DR-0018](../decisions/DR-0018-forte-data-workbench-and-verifiable-trace.md) | current interaction, API and truth boundaries | design text does not prove runtime |
| FORTE import | source commit `345c1ec1487139db9dd319787fa9405ba85d1869`, top-level MIT, existing manifest | fixed public source and provenance | public benchmark, not enterprise production data |

## Implementation binding

| Item | Value |
| --- | --- |
| implementation commits | [`fffa36a8cc83e895aaba35276568ad79e348f541`](https://github.com/Dickey007s/lenovo_agent/commit/fffa36a8cc83e895aaba35276568ad79e348f541) + [`041186d`](https://github.com/Dickey007s/lenovo_agent/commit/041186d) |
| sanitized live manifest | [`dr-0018-forte-data-workbench-live-run.json`](manifests/dr-0018-forte-data-workbench-live-run.json) |
| PR | [#25](https://github.com/Dickey007s/lenovo_agent/pull/25), open and not yet merged |
| first documentation/evidence commit | [`2bb0e4a6369576e8f4407ab25d3e6a0c0efca6e7`](https://github.com/Dickey007s/lenovo_agent/commit/2bb0e4a6369576e8f4407ab25d3e6a0c0efca6e7) |

## Current foreground

The root page is titled `FORTE 数据工作台`. It exposes:

- three business-named data collections without foreground Demo 1/2/3 navigation;
- search, explicit file checkboxes and one active file preview;
- real first-sheet XLSX rows or bounded Markdown text from the server;
- a free-form 3-2,000 character task composer;
- data preview, validated plan and analysis result views;
- a separate right-side trace with planning receipt, analysis receipt and named events;
- a result footer that states human review is required and no external action occurred.

The final result view uses the title `模型初步结论 · 待复核`, shows three findings by default and requires an explicit action to reveal the remaining seven. It also states that the server checked file references and the read-only boundary, but did not recompute the displayed values. Three current-UI screenshots are registered below with distinct provenance. Browser assertions and screenshots remain engineering evidence; they cannot establish that the reduced-copy layout is clearer to users.

## Seven-path public surface

Code and focused route tests cover the added preview route:

```text
/v1/health
/v1/harness/scenarios
/v1/harness/scenarios/{scenario_id}
/v1/harness/scenarios/{scenario_id}/files/{file_ref}
/v1/harness/runs
/v1/harness/runs/{run_id}
/v1/harness/runs/{run_id}/events
```

The preview route revalidates the allowlisted file bytes. XLSX output is limited to the first visible sheet, 30 columns and 120 data rows; Markdown output is limited to 30,000 characters. Public payloads omit source path, SHA-256, raw task instruction, rubric, solution and grading material. An unknown `file_ref` returns 404; an integrity failure returns controlled 503.

## Stable source and citation boundary

`file_ref` is deterministically derived from Scenario ID plus allowlisted relative path, but the path itself remains private. The Run freezes the user's unique selected refs. Both the plan and result may cite only that frozen set.

The result validator checks set membership for every `finding.file_refs[]`. It does not validate whether the narrative is semantically correct, whether a number was interpreted under the right accounting rule, or whether a cited file proves the exact sentence. `review_required=true` is therefore mandatory.

The visible result is a `HarnessTaskResult` stored in the memory Snapshot. It is not an `ArtifactVersion`, verified Artifact Commit or external-system record.

## Observed live runs

The following values were transcribed into the sanitized manifest from one interactive live verification:

| Fact | Observed value |
| --- | --- |
| Run | `harness:8c9b10d493004bd9aac305c294f48fa6` |
| Scenario | `Finance-018` |
| Terminal fact | `completed`, v9, sequence 8 |
| Planner | `deepseek-v4-pro`, `14685 ms`, `called=true`, `output_used=true` |
| Analyst | `deepseek-v4-pro`, `18041 ms`, `called=true`, `output_used=true` |
| Result | 10 findings, `review_required=true` |
| Selected/cited refs | `forte-a0bccc1df48cc6a1`, `forte-b6e701bcf4494076` |
| External effect | `none` |

The two refs correspond to the selected public labels “2025 年上半年往来明细” and “2025 年下半年往来明细”. The manifest intentionally omits finding prose, raw cells, prompts, responses and internal paths/hashes.

This is a sanitized interactive run record, not a raw exported Snapshot or independently replayable quality result. The durations are observations of these two calls, not an SLA, cost model or productivity claim.

A second real Run, recorded by prefix `harness:f3a071...`, was captured while its trace was in progress and later reached `completed` v9/seq 8. Its Planner call was adopted in `14155 ms`; its Analyst call was adopted in `17122 ms`. This second observation is not a repeated quality benchmark and does not establish latency stability.

## Honest negative result

The observed first Snapshot stated 20 unchanged items totaling `2,202,000`. A deterministic regression now reads the same public safe previews and groups non-empty closing balances by `(科目名称, 客商名称, 期末方向)`. It reproduces **23** unchanged items with an absolute-value total of **`1,845,444.71`**.

The regression is [`test_finance_cross_period_ground_truth_is_deterministically_reproducible`](../../tests/unit/test_benchmark_scenario_catalog.py). Its test file passes `10 passed`. This mismatch demonstrates that the current `result_validation` only checks response schema, selected `file_ref` membership and the read-only boundary. It does **not** check business semantics, exhaustive coverage or arithmetic correctness. Accordingly, `completed` means an initial response was returned and passed those bounded checks; it does not mean the Finance task was answered correctly or quality passed.

This negative evidence motivated the foreground title, the three-finding default and the explicit numerical-review warning. A deterministic spreadsheet operator and claim-level verification are the next target; neither is current capability.

## Screenshot provenance

| Screenshot | Dimensions / bytes / SHA-256 | What it records | Boundary |
| --- | --- | --- | --- |
| [`dr-0018-data-workbench-running-desktop.png`](screenshots/dr-0018-data-workbench-running-desktop.png) | `1440 x 900`; `136670`; `41B57A38C571C69B5624777A1E0376BADAA4A70B52D968470B12DB4D4D47EC61` | actual second real Run `harness:f3a071...` about 1.8 seconds after start | an in-progress trace, not a timing benchmark or terminal proof |
| [`dr-0018-data-workbench-result-desktop.png`](screenshots/dr-0018-data-workbench-result-desktop.png) | `1440 x 900`; `180565`; `9EC29203B0D5D24665152D468A690B2F78C42FD8C7D53112694253D52D377850` | the first real persisted Snapshot `harness:8c9...` projected into the final desktop UI by browser POST replay | not a third model call and not product history/restart recovery |
| [`dr-0018-data-workbench-result-mobile.png`](screenshots/dr-0018-data-workbench-result-mobile.png) | `390 x 3284`; `178485`; `C4226CF19DBECCD85233E7861EEBE768A7B88DF1F6176A9A6DC2863C2CD09A00` | the same replayed Snapshot at 390px, three findings visible and “查看其余7条发现” available | `scrollWidth=390`, console/page errors 0; still not a mobile user study |

The result replay exercised the same formal UI projection, but it is a capture technique rather than a current product history-loading feature. It did not invoke the model again. The running image and result images must not be presented as if they share one screenshot transaction.

## Ordered trace

The live success path recorded eight ordered events:

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

The UI projects those events into business labels. It does not expose chain of thought, Prompt, hidden model attempts or raw logs. A named event proves that the server recorded a stage transition; it does not by itself prove the semantic quality of the stage output.

## Verification

| Check | Current result | Boundary |
| --- | --- | --- |
| focused Python Catalog/Runtime suite | `30 passed in 2.46s` | current preview, selection, planning, analysis, citation, privacy, idempotency and route contracts |
| Harness browser workbench suite | `8 passed in 26.8s` | final current eight-test run; browsing, task input, trace, retry, recovery, fail-closed and mobile engineering paths |
| deterministic Finance ground truth | test file `10 passed`; regression linked above | reproduces `23` / `1,845,444.71` and preserves the observed mismatch as a negative result |
| web build | compile `2.5s`; TypeScript `4.4s`; static generation `810ms` | current build succeeds; no usability inference |
| final full Python/Ruff/lint suite | Python `53 passed in 2.68s`; Ruff passed; web lint passed | current repository quality gates, not a user or production result |
| live model observations | manifest linked above | two Finance-018 observations; not effectiveness evaluation |

## Fail-closed paths

- malformed/duplicate or unknown selected refs are rejected;
- file preview revalidates source bytes and rejects unknown refs;
- invalid Planner or Analyst JSON records `output_used=false` and fails the Run;
- plan refs outside the selected set fail validation;
- result refs outside the selected set fail validation and no result is presented as complete;
- unknown start response reuses the same idempotency command on retry;
- SSE interruption resumes after the last observed sequence and reconciles by Snapshot.

## Remaining boundaries

- `X-User-Id` remains an unsigned demo placeholder.
- Run, result, receipts, events and idempotency live in one API process memory and disappear on restart.
- The analyst receives server-produced public previews, not an arbitrary filesystem or Connector.
- The service does not deterministically recompute spreadsheet findings or verify claim entailment; the recorded negative result shows why human numerical review is required.
- No Scheduler/Worker lease, Tool Gateway invocation, Artifact mutation/verification/Commit, approval, Permit, real Connector or external action occurs.
- Thinking is disabled in the request and no chain of thought enters the public projection; this does not claim knowledge of undocumented internal model processing.
- No target-user study measures whether users find the page clearer, can interpret the trace, complete tasks correctly or trust the result appropriately.
