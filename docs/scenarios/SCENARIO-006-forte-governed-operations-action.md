# SCENARIO-006: Governed operations action design

| Field | Value |
| --- | --- |
| Related Demo | Demo 3 |
| Status | shared planning slice `Limited Verified`; execution migration `Draft` |
| Source | FORTE `Operations-008`, commit `345c1ec1487139db9dd319787fa9405ba85d1869`, top-level MIT; original bytes pinned by `DR-0016` |
| Target user | Operations policy owner or collection-process supervisor |

## Trigger and current pain

The user asks the Agent to design an AI-assisted M1 collection-call process. A plausible process diagram alone is unsafe: calling time, recording notice, retry limit, human escalation and terminal-state rules must govern every proposed action. The retired Demo 3 began from a fixed email-send candidate; the current FORTE worksite starts from the public policy document but stops before action execution.

## Goal and completion condition

The Agent produces a versioned process artifact and a set of bounded action candidates. Deterministic Risk, Policy, Evidence, Approval, Permit and Tool Gateway components decide which simulated actions are allowed. Completion requires a policy-linked artifact and explicit receipt; no real phone call, blacklist update or external system write occurs.

## Intended Harness flow

1. Catalog verifies and freezes the source requirements document and raw task provenance; only sanitized Prompt text enters the internal Planner.
2. Planner derives process-design units and identifies potential governed actions.
3. Admission validates tools, data boundary and mandatory human gates.
4. Model drafts process content; deterministic policy compiles the source constraints into checks.
5. Proposed action binds the current artifact version, target scope, policy evidence and impact preview.
6. The user sees what would change, be rechecked, remain unchanged and not happen.
7. Approval may produce a one-time Permit for a Simulator capability; denial or mismatch preserves the artifact and records why execution did not occur.

## Frontend experience

- Policy source panel links each constraint to the imported document section.
- Process canvas distinguishes model-authored content from deterministic gates.
- Action impact ledger appears before confirmation and receipt after the command.
- Unknown identity, unclear data class, out-of-hours call or exhausted retry budget is visibly denied.
- Technical audit can show service names and event summaries, but normal UI hides Permit tokens, raw payloads and model reasoning.

## Key exceptions

| Exception | Expected behavior |
| --- | --- |
| Policy requirement cannot be parsed or cited | Stop action planning; do not infer permission |
| Recipient identity or data class unresolved | Deterministic deny; user self-assertion cannot satisfy evidence |
| Artifact changes after approval | Invalidate action, approval and Permit; require re-evaluation |
| Permit replay or parameter mismatch | Gateway rejects and records a no-change receipt |
| Simulator failure or unknown result | Preserve artifact, show result unknown/failure and provide bounded retry/reconcile |

## Boundary

The DR-0016 foundation Evidence contains one manifest-bound `deepseek-v4-pro` run with 1 public file, 4 dynamic plan units and v6/seq 5 `ready_to_execute` in 10243 ms. DR-0017 makes this Scenario part of the sole current worksite but does not make the retired action path current. It does not draft the process Artifact, create an ActionCandidate, run Risk/Policy/Evidence/Approval/Permit or call a Simulator. That execution migration remains `Draft`.

The task source is a public benchmark requirement document. Raw `task.md`, `task_instruction`, rubric and solution content stay out of the public API/UI. The current project has no real dialer or collection-system Connector. A successful Simulator receipt in a later bounded slice still cannot be reported as a real customer contact or production policy deployment; E2E is not user research.
