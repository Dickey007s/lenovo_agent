# SCENARIO-085: Present Different Human-Agent Boundaries

- Target user: presenter explaining human-agent interaction choices to project reviewers.
- Trigger: select a prepared office case instead of typing material during a meeting.
- Pain: six generic operation defaults do not supply enough distinct, repeatable stories.
- Source: [2026-10-26 feedback](../sources/USER-FEEDBACK-20261026-demo3-more-examples.md).
- Decision: [DR-0098](../decisions/DR-0098-demo3-ready-boundary-examples.md).

## Flow

1. Open the original Demo3 space, expand the example selector and pick a case.
2. Inspect or edit synthetic input. No network mutation or authorization occurs on selection.
3. Click Start; the original server returns actual preparation/result status.
4. Show the relevant boundary: undo, edit, clarify, confirm, recheck, deny, judge or defer.
5. Finish or defer before starting another case. Reopen deferred work from actual recent records.

## Acceptance

- Twelve unique named presets, four groups, six distinct initial server states.
- Switching presets cannot retain the prior case's second material, source or formatting field.
- Contacts and missing deadlines are not guessed; completing them still requires confirmation.
- Strong confirmation starts unchecked; revision invalidates every check.
- Material choice and rationale are never populated by the preset; defer saves no decision.
- Existing actions never expose a shortcut that replaces input without revise/version checks.
- Results retain external_action=none and model_called=false.
- Narrow screens remain usable without page-level horizontal overflow.

Not an automatic case player, arbitrary agent runtime, new file import, external action connector or full-history task manager. Recent records remain capped at twenty Runs.
