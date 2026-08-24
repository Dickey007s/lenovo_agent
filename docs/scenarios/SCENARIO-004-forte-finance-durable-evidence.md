# SCENARIO-004: Cross-period finance evidence task

| Field | Value |
| --- | --- |
| Related Demo | Demo 1 |
| Status | shared planning slice `Limited Verified`; execution migration `Draft` |
| Source | FORTE `Finance-018`, commit `345c1ec1487139db9dd319787fa9405ba85d1869`, top-level MIT; original bytes pinned by `DR-0016` |
| Target user | Finance operations lead or account reconciliation owner |

## Trigger and current pain

The user receives three period workbooks and must identify unpaid, uncollected, and long-lived balances. The current prototype begins with a predetermined conflict and three predetermined deliverables. It does not show whether the Agent located the right sheets, how it mapped columns across periods, or which evidence made a balance suspicious.

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

## Frontend experience

- Workspace shelf: three original workbooks with public-benchmark label and workbook metadata.
- Agent journey: file inspection, schema mapping, period normalization, reconciliation, verification and commit appear progressively.
- Evidence table: each flagged balance links back to a workbook/sheet/row reference.
- Live activity: actual model and table-tool receipts with duration; no Prompt or chain of thought.
- Decision tray: appears only for a recorded ambiguity and explains what the decision will change, recheck, preserve and not do.

## Key exceptions

| Exception | Expected behavior |
| --- | --- |
| Workbook/hash mismatch or unsupported feature | Fail closed before planning; show the affected file and recovery action |
| Required sheet/column missing | Stop the affected unit; retain verified checkpoints; do not infer values |
| Entity names cannot be mapped safely | Open a mapping conflict; other independent work may continue |
| Model plan references an unknown file/tool | Reject the plan; do not create a fallback labeled as model output |
| Browser disconnect | Reconcile from the latest Snapshot/event sequence; do not restart completed reads |

## Boundary

The current shared Harness vertical slice has one manifest-bound `deepseek-v4-pro` run with 3 public files, 10 dynamic plan units and v6/seq 5 `ready_to_execute` in 17112 ms. It does not read workbook rows through tools, create the finance artifacts above or Commit the task. That execution migration remains `Draft`.

The files are public benchmark inputs, not production finance records. Raw `task.md`, `task_instruction`, rubric and solution content stay out of the public API/UI. This scenario does not prove arbitrary workbook understanding, cross-process recovery, accounting correctness, or user-value improvement until corresponding evidence exists; E2E is not user research.
