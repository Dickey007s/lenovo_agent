# SCENARIO-004: Cross-period finance evidence task

| Field | Value |
| --- | --- |
| Acceptance lens | Demo 1; not a runtime identity |
| Generic work profile | `single_task + bounded_loop + evidence_gate + human_gate`; current scope `read_only_analysis` |
| Status | bounded data preview/read-only analysis `Limited Verified`; durable Artifact/Commit migration `Draft` |
| Source | FORTE `Finance-018`, commit `345c1ec1487139db9dd319787fa9405ba85d1869`, top-level MIT; original bytes pinned by `DR-0016` |
| Target user | Finance operations lead or account reconciliation owner |

## Trigger and current pain

The user receives three period workbooks and must identify unpaid, uncollected, and long-lived balances. The retired Customer A prototype began with a predetermined conflict and deliverables. The current FORTE workbench lets the user inspect actual rows, select files, ask an original question and obtain a cited review-required result. It still does not produce a durable evidence Artifact or prove the accounting interpretation.

## Goal and completion condition

The Agent must produce versioned unpaid and uncollected summaries, identify balances that remain unchanged across all periods, and cite the source workbook, sheet, row range, and field mapping for every highlighted result. Completion requires a validated artifact commit; a model-generated narrative without evidence bindings is insufficient.

## Intended Harness flow

1. Catalog verifies raw task provenance and all three workbooks, then freezes a Workspace Snapshot; only sanitized Prompt text enters the internal Planner.
2. Planner reads only file metadata and bounded table schemas before generating a DAG.
3. Admission validates file paths, registered tools, dependency order and budget.
4. The durable scheduler reads one period at a time and checkpoints normalized records.
5. The verifier checks row-level citations, period coverage, numeric totals and persistent-balance criteria.
6. Mapping ambiguity or conflicting entity identity creates a server conflict and a user decision; otherwise the Agent continues without interruption.
7. Commit contains the output versions, evidence bindings, verification reports and workspace fingerprint.

This flow must be implemented by the reusable single-task executor. Selecting the Finance collection or calling the scenario “Demo 1” must not enable a private Demo-only code path.

## Frontend experience

- Data browser: three original workbooks with public-benchmark label and bounded real rows.
- Task composer: the user selects source files and asks the reconciliation question.
- Current trace: Planner/Analyst receipts and eight server events; no Prompt or chain of thought.
- Current result: findings link to selected file labels, show only three by default, and remain explicitly pending review.
- Target evidence table/decision tray: row-level entailment, ambiguity decisions and Commit remain `Draft`.

## Key exceptions

| Exception | Expected behavior |
| --- | --- |
| Workbook/hash mismatch or unsupported feature | Fail closed before planning; show the affected file and recovery action |
| Required sheet/column missing | Stop the affected unit; retain verified checkpoints; do not infer values |
| Entity names cannot be mapped safely | Open a mapping conflict; other independent work may continue |
| Model plan references an unknown file/tool | Reject the plan; do not create a fallback labeled as model output |
| Browser disconnect | Reconcile from the latest Snapshot/event sequence; do not restart completed reads |

## Boundary

The current workbench is governed by DR-0018. One live Finance-018 Run over two selected workbooks reached `completed` v9/seq 8: Planner and Analyst were both adopted, 10 findings cited only the two selected stable refs, `review_required=true`, and no external side effect occurred. The server checked citation membership, not the semantic or numerical correctness of those findings. No Tool Gateway, ArtifactVersion or Commit was created; durable execution remains `Draft`.

The files are public benchmark inputs, not production finance records. Raw `task.md`, `task_instruction`, rubric and solution content stay out of the public API/UI. This scenario does not prove arbitrary workbook understanding, cross-process recovery, accounting correctness, or user-value improvement until corresponding evidence exists; E2E is not user research.
