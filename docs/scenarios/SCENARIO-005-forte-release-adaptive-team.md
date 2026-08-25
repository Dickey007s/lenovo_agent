# SCENARIO-005: Adaptive release-readiness collaboration

| Field | Value |
| --- | --- |
| Acceptance lens | Demo 2; not a runtime identity |
| Generic work profile | `multi_task + adaptive_swarm + evidence_gate + human_gate`; current scope `read_only_analysis` |
| Status | workbench/preview/read-only contract `Limited Verified`; release conclusion and adaptive execution `Draft` |
| Source | FORTE `pm-014`, commit `345c1ec1487139db9dd319787fa9405ba85d1869`, top-level MIT; original bytes pinned by `DR-0016` |
| Target user | Product manager or release owner |

## Trigger and current pain

Before a release decision, the user must reconcile a PRD, release configuration, functional test report and compatibility test report. The retired fixed Demo 2 used predetermined work and Worker steps. The current workbench exposes all four public inputs, lets the user select context and ask a custom question, and can return a cited read-only result. A live semantic release-readiness result, adaptive Workers and replanning remain unevidenced.

## Goal and completion condition

The Agent must determine release readiness, coverage, failed or untested functions, compatibility gaps and remediation priorities. Completion requires a shared, versioned release-readiness artifact whose conclusions cite the relevant files and whose checks pass. No production deployment is triggered.

## Intended Harness flow

1. Catalog freezes the four-source workspace and raw task provenance; only sanitized Prompt text enters the internal Planner.
2. Planner generates a DAG from the available evidence and expected output rather than from a client-side worker template.
3. Admission decides whether units can run in parallel and validates allowed file tools, budget and human-gate rules.
4. Scheduler starts dependency-free units and records their real assignments.
5. Workers write source-bound SharedArtifactVersions; they never own source identity, status or verification truth.
6. A discrepancy discovered in outputs may create a reconciliation unit through a versioned replan; no discrepancy means no synthetic extra worker.
7. Verifier produces the final readiness result and `external_side_effect=none` receipt.

This flow must be implemented by the reusable multi-task Scheduler/Worker layer. Selecting pm-014 or calling it “Demo 2” must not create synthetic Workers or unlock a Demo-only execution path.

## Frontend experience

- Data browser groups requirement, configuration, functional and compatibility evidence and previews real bounded content.
- The user chooses files, writes a release question and sees independent Planner/Analyst receipts.
- Current result citations resolve to selected file labels and require review.
- Dynamic Worker map, shared Artifact convergence, pause and replan controls remain target interactions.
- `completed` can only mean the read-only analysis result exists; deployment has not happened.

## Key exceptions

| Exception | Expected behavior |
| --- | --- |
| Planner creates a cyclic or unauthorized graph | Reject the graph before execution |
| A worker fails | Mark the unit failed, cancel dependent units, preserve unrelated verified artifacts |
| Two reports disagree | Add a reconciliation unit only through a server replan event |
| Source changes during the run | Fail the affected bindings and require a new workspace version |
| SSE gap or reconnect | GET the full Snapshot and resume after the confirmed event sequence |

## Boundary

DR-0018 makes the preview/custom-task/two-call/citation contract current for this collection, and focused E2E covers browsing its public files. No new live pm-014 model result is bound to DR-0018 Evidence, so semantic release readiness remains `Draft`. The Runtime does not start Scheduler/Workers, invoke tools, produce SharedArtifactVersions or deploy a release.

This scenario uses public benchmark inputs and a simulated run workspace. Raw `task.md`, `task_instruction`, rubric and solution content stay out of the public API/UI. It does not prove a general distributed swarm, production deployment, cost savings, SLA improvement, or target-user understanding; E2E is not user research.
