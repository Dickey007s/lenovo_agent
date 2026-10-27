# SCENARIO-065 Export saved context without implying delegation

2026-10-19. Limited Verified for the recorded browser paths; human comprehension unverified.
Decision: DR-0078. Source: USER-FEEDBACK-20261019-PRINCIPLES-DELIVERABLES.

User: a review coordinator comparing two contradictory deadlines or lacking a task owner/date.
Trigger: the user cannot complete the current decision and needs another person's help.
Pain: the old export omitted the target, deadline, concrete next decision and return constraints.
Goal: retain the saved state in a useful local note, without pretending to assign a person or start approval.

Main path: enter two nonsensitive materials; start comparison; defer; download the handoff; reload the same Run; explicitly choose a material and state a reason; record one decision_note. Download contains both original materials, revision, status, next decision and absence of external action.

Alternative path: start create_task without owner/date. Show exact missing fields and no submission. Export records the missing information; it does not execute, pause or mutate the task.

Exceptions: while busy, editing, or outcome unknown, export is disabled. Unsaved field edits are not part of a saved-state note. Recent items only cover the current owner's latest 20 Runs. In-memory reload persistence is not restart/cross-device recovery. Denied requests still cannot resume using Loop controls.

Frontend: state and missing fields remain visible; histories stay collapsed. Backend: all exported fields map to saved office_action; next-decision prose is an explanation rather than an authorization. No version/idempotency contract changes. Completion: correct downloadable text, zero POST on export, no preselection, rationale required, decided receipt only and no external action. Narrow-screen check: 390px no horizontal overflow.

Evidence: [DR-0078](../evidence/DR-0078-HANDOFF-20261019.md). User study is proposed separately and not performed.
