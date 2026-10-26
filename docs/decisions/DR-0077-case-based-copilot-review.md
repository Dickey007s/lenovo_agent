# DR-0077: Case-based copilot review in the existing workbench

Date: 2026-10-10. Status: Limited Verified for the tested presentation and action
paths. User benefit remains Draft; exact results are recorded in Evidence.

## Scenario and sources

The user requests a recoverable archive before changing the current UI, then a small
set of cases drawn from the teammate's human-agent collaboration work, not a formal
delivery package or a separate product. Source: USER-FEEDBACK-20261010-COPILOT-CASES.
The teammate's submission handbook C02/C08/C11 and R05/R06/R07/R08/R10/R14/R16 are
the local design basis. Research sources and their limits are recorded in the Source.
Scenario: [SCENARIO-064](../scenarios/SCENARIO-064-case-based-copilot-review.md).

## Frontstage interaction

- C02: show source beside the draft, open by default; stack on narrow screens. Keep
  editing and source preview. A saved edit_draft history event changes the main
  heading to human-revised draft; no claim of semantic summarization.
- C08: when an open item has differences against the previous revision, name the
  changed fields and open their before/after comparison. Existing check invalidation
  and version guards remain unchanged. Historical draft changes remain collapsed.
- C11: state before and after the decision that a saved choice does not edit source,
  approve business or automatically dispatch other tasks. No preselection is added.
- Unknown response takes precedence over generic finished/waiting context wording.
  Request recovery remains the same original-body/idempotent replay path.

The report is offline explanation with real-API synthetic-case screenshots and
paper links. It is not a new system entry point. Original Loop/Swarm stays intact.

## Backend facts

No API or Runtime changes. Authoritative fields remain office_action.status,
revision, input, source_excerpt, preview, history, decision and receipt. Field
differences derive from the latest lower-revision history item, not inferred risk.
unknown is transport-local, not a new server terminal state. R/C numbers are not
new permissions. A case-based design justification is not evidence of user benefit.

## Verification and boundaries

[Evidence](../evidence/DR-0077-COPILOT-CASES-20261010.md) records the source archive,
baseline 3 tests, failed intermediate test, final regression and report checks.
No model, email, approval service or production database is used in these cases.
Worker ambiguity -> human decision -> dependency release is still an open design
gap. No full formal deliverables or external integration were added.
