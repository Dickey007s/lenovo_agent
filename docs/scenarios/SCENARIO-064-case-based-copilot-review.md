# SCENARIO-064: Review a draft, a changed message and conflicting materials

Date: 2026-10-10. Status: Limited Verified for listed engineering paths; user outcomes unverified.
Decision: DR-0077. Source: USER-FEEDBACK-20261010-COPILOT-CASES.

## User, trigger and goal

A project lead prepares review materials: extract an internal note, revise a
planned message from Wednesday to Friday, and record a comparison between an email
and meeting minutes. The material is synthetic, nonsensitive and user supplied.
The goal is to understand what can proceed automatically, what decision is needed
and what actually changes after that decision.

## Paths and completion criteria

1. C02: choose excerpt preparation in the original new-task action view. See source
   beside the draft; edit and save. Source must not change; revision increases and
   the heading distinguishes human revision. This creates only an internal record.
2. C08: prepare a test message, check the fields, change Wednesday to Friday. See
   old checks cleared, the current version and changed content. Confirm stays
   disabled until fresh checks. Defer/reload must not confirm or send anything.
3. C11: compare two user-provided statements. Neither option is selected by default.
   A choice without rationale cannot submit. Save one decision_note with both source
   statements unchanged. The browser must not POST a downstream Run or Worker wave.

## Exception paths

Unknown submissions keep the existing request body and idempotency key, with an
unknown-result context rather than a generic finished label. Source preview stays
available when expanded or collapsed. Version conflict, incomplete materials,
defer/reopen and navigation race contracts are unchanged. Users may decline or
defer; no default approval or time-based consent is introduced.

## Source, interface and backend authority

Teammate submission handbook C02/C08/C11 supplies the case definitions. UI changes
are limited to OfficeActionWorkbench and CSS. office_action source_excerpt,
preview/history, revision and decision/receipt are the facts. No model inference
is used to choose a risk or a correct material. The source excerpt is bounded;
scrolling the preview is not proof of exhaustive semantic review.

## Evaluation

Engineering assertions: source preservation, explicit decision, revision reset,
no automatic downstream POST, mobile width and unchanged Loop/Swarm regression.
User-study proposal (not performed): detect an incorrect date, explain confirmation
scope and recover after deferral; measure accuracy, time and mistaken assumptions
using counterbalanced old/new layouts. Do not substitute click counts for benefit.
