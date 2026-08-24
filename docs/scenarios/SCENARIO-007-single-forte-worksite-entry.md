# SCENARIO-007: Single FORTE worksite entry and recovery

| Field | Value |
| --- | --- |
| Scenario ID | `SCENARIO-007` |
| Status | `Limited Verified` for the current engineering path; comprehension and value `Draft` |
| Decision | [`DR-0017`](../decisions/DR-0017-single-forte-worksite-and-legacy-retirement.md) |
| Source | `USER-FEEDBACK-20260824-FORTE-ONLY-09` |

## Target user and trigger

The target user is a product or technical reviewer opening Office Agent to understand what the Agent can inspect and what has actually happened. The scenario starts at `/`, with or without a reachable API and valid FORTE Catalog.

## Current pain

The transitional product showed both the new Harness and the retired office-workspace rail. When the Catalog could not load, the page displayed `Failed to fetch`, so the user could not distinguish an offline service from a corrupt source package. Historical Customer A files and routes also made it unclear which demo facts were current.

## Goal and completion condition

The first screen is one FORTE worksite. The user can select Finance-018, pm-014, or Operations-008, inspect public file labels and the task contract, start an independent planning round, follow model/validation receipts, and see `ready_to_execute` without any execution claim. Completion requires that the final UI contains no legacy workspace entry and that each visible state is backed by Scenario, Snapshot, Event, health, or request facts.

## Frontend journey

1. The worksite loads the safe Scenario Catalog and presents three business scenarios.
2. The source panel shows only public labels and summaries; the center shows the task contract.
3. Starting a round creates a new idempotent Harness Run and moves through indexing, planning, validation, and ready states.
4. The right rail shows whether the service is available, whether an event stream is active, model-call facts, validation, and recovery.
5. At `ready_to_execute`, the page says the plan passed server validation and has not been executed. A new round creates a distinct Run.

## Server fact matrix

| Situation | Server/client fact | UI response | Recovery boundary |
| --- | --- | --- | --- |
| Initial load | health + Scenario list | one worksite and three scenarios | no static fallback scenario invented |
| API offline | health/fetch failure | offline/recovering state | automatic retry and explicit retry |
| Catalog unavailable | health succeeds, Catalog fails | service available, Catalog retrying | do not label API offline |
| Catalog integrity invalid | controlled 503 integrity detail | “工作场景需要更新” | fail closed until source is repaired |
| Scenario detail failure | list projection remains valid | explicit Catalog-preview notice | no raw task fallback |
| Model planning | Snapshot status and processing event | live activity only while SSE is active | animation alone is not a call fact |
| Stream interruption | EventSource error before terminal state | reconnecting and `after=N` resume | final GET reconciles Snapshot |
| Terminal plan | `ready_to_execute`, version 6, sequence 5 | ready banner and new-round action | no execution, Artifact, or external-action claim |

## Hidden details

The ordinary UI hides raw `task.md`, sanitized Planner context, rubric, solution, absolute path, complete hash, internal source IDs, Prompt, chain of thought, Worker conversation, credentials, and lower-level logs. The old Customer A dataset and legacy route names must not appear in the current DOM or public API.

## Evidence boundary

Current E2E covers the root entry, all three scenarios, API recovery, Catalog-unavailable and integrity-invalid states, detail fallback, ordered/terminal streaming, idempotent retry, privacy, desktop, and 390px behavior. It does not replace a final-state screenshot or user study. See [`FORTE-ONLY-WORKSITE-RETIREMENT-EVIDENCE-20260824`](../evidence/FORTE-ONLY-WORKSITE-RETIREMENT-EVIDENCE-20260824.md).
