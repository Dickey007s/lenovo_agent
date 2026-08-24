# SCENARIO-005: Adaptive release-readiness collaboration

| Field | Value |
| --- | --- |
| Related Demo | Demo 2 |
| Status | shared planning slice `Limited Verified`; execution migration `Draft` |
| Source | FORTE `pm-014`, commit `345c1ec1487139db9dd319787fa9405ba85d1869`, top-level MIT; original bytes pinned by `DR-0016` |
| Target user | Product manager or release owner |

## Trigger and current pain

Before a release decision, the user must reconcile a PRD, release configuration, functional test report and compatibility test report. The current Demo 2 always starts from four fixed work items and a predetermined worker/replan sequence. It can prove its own vertical slice, but it does not make the Harness feel reusable across a new folder.

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

## Frontend experience

- File shelf groups product requirement, configuration, functional test and compatibility evidence.
- Dynamic work map shows current units, dependencies, selected files, model/tool receipts and why a new unit was added.
- Shared artifact desk shows convergence and competing versions rather than Worker conversation.
- The user can inspect or pause a unit, but worker count and completion are server facts.
- Completion says the internal readiness package is ready and deployment has not happened.

## Key exceptions

| Exception | Expected behavior |
| --- | --- |
| Planner creates a cyclic or unauthorized graph | Reject the graph before execution |
| A worker fails | Mark the unit failed, cancel dependent units, preserve unrelated verified artifacts |
| Two reports disagree | Add a reconciliation unit only through a server replan event |
| Source changes during the run | Fail the affected bindings and require a new workspace version |
| SSE gap or reconnect | GET the full Snapshot and resume after the confirmed event sequence |

## Boundary

The current shared Harness vertical slice has one manifest-bound `deepseek-v4-pro` run with 4 public files, 6 dynamic plan units and v6/seq 5 `ready_to_execute` in 13577 ms. It does not start Scheduler/Workers, read the four files through tools, produce SharedArtifactVersions or decide release readiness. That execution migration remains `Draft`.

This scenario uses public benchmark inputs and a simulated run workspace. Raw `task.md`, `task_instruction`, rubric and solution content stay out of the public API/UI. It does not prove a general distributed swarm, production deployment, cost savings, SLA improvement, or target-user understanding; E2E is not user research.
