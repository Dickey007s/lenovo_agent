# DR-0005 Task Director Design QA

> Historical visual baseline for commit `a47cb28`. The visual comparison below remains valid for that recorded implementation, but it does not close the current usability decision. The current business-first revision and screenshots are tracked in `docs/evidence/DEMO1-PR6-USABILITY-COMPREHENSION-AUDIT-20260811.md`; `DR-0005` remains `Draft` until unguided participant testing is completed.

## Comparison Target

- Source visual truth: `docs/evidence/assets/dr-0005-task-director-option2-reference.png`
- Rendered implementation: `docs/evidence/screenshots/dr-0005-task-director-conflict-desktop.png`
- Full comparison: `docs/evidence/screenshots/dr-0005-reference-implementation-comparison.png`
- Focused comparisons:
  - `docs/evidence/screenshots/dr-0005-orchestration-focused-comparison.png`
  - `docs/evidence/screenshots/dr-0005-decision-focused-comparison.png`
- Responsive evidence:
  - `docs/evidence/screenshots/dr-0005-task-director-decision-mobile.png`
  - `docs/evidence/screenshots/dr-0005-task-director-committed-desktop.png`
  - `docs/evidence/screenshots/dr-0005-task-director-history-desktop.png`

## Normalization

- Source pixels: `1487 x 1058`.
- Desktop implementation pixels: `1487 x 1058`.
- Desktop CSS viewport: `1487 x 1058`, device scale factor `1`.
- Density normalization: none required; the source and desktop implementation use the same pixel dimensions.
- Mobile CSS viewport: `390 x 844`, device scale factor `1`; the evidence is a `390 x 2544` full-page capture of the same conflict state.
- Compared state: Demo 1 at Task version `v2`, `waiting_input / verify`, two submitted branch checkpoints, one open revenue conflict, and no final TaskCommit.

## Browser Evidence

- The local implementation was opened and exercised in the Codex in-app browser at `1487 x 1058` and `390 x 844`.
- Browser measurements found no page-level horizontal overflow at either viewport.
- Browser console inspection found no application errors or warnings; only React development information and the Next.js HMR connection were present.
- Automated browser coverage exercised create, start, Decision/Agent switching, the mobile decision jump, pause, resume, disabled invalid resolution, visible `409` feedback, successful resolution, final commit, follow-head selection, and pinned-history recovery.

## Required Fidelity Surfaces

- Fonts and typography: the implementation keeps the reference's compact Chinese sans-serif hierarchy while raising task metadata and decision copy to readable sizes. Long labels wrap or clamp without overlap; letter spacing is not compressed.
- Spacing and layout: the left navigation, task header, fact strip, five-stage rail, branch lanes, right Decision Inbox, and direction composer preserve the reference's command-center composition. The implementation intentionally uses fewer unsupported stage details rather than inventing facts.
- Colors and tokens: neutral white/gray surfaces, cobalt primary actions, green verified states, and amber blocked states match the reference's semantic palette. No decorative gradients or oversized radii were introduced.
- Image and asset fidelity: the target contains no product imagery requiring recreation. The selected reference is retained verbatim; interface icons use one Tabler outline library instead of handcrafted SVG or text glyph substitutes.
- Copy and content: generated timestamps, fake recovery claims, waiting durations, unsupported share actions, raw artifact kinds, event sequence numbers, and naked hashes are omitted or moved behind evidence disclosure. Visible claims map to the current Snapshot or client synchronization state.
- Interaction and accessibility: tabs support roving focus and arrow keys; the mobile five-stage rail is fully visible; visible mobile task actions are at least `44px`; errors use live regions; historical versions have an explicit warning and return action.

## Comparison History

### Pass 1: blocked

- P1: historical `v1` mixed a candidate artifact with the current green resolved-conflict state.
- P2: the mobile stage rail hid Verify and Commit behind horizontal scrolling.
- P2: small metadata and a fixed nested Decision pane reduced mobile readability and clipped secondary actions.
- P2: raw protocol details such as `analysis`, `risk_brief`, `reply_draft`, `TaskCommit`, event sequence, and state hash appeared in the primary business interface.
- P2: transient toast evidence obscured the mobile commit condition in the capture.

### Fixes

- Historical mode now labels conflict information as the current Task Snapshot, keeps the current branch head separate, and makes clear that a resolved current conflict neither identifies the resolution version nor validates the selected historical artifact.
- Mobile stages use five equal tracks with concise labels; the current Verify stage is always visible.
- Decision content expands naturally on stacked layouts; typography and line heights were increased; all primary and secondary actions remain reachable.
- Protocol kinds are translated or hidden, final commit wording is user-facing, and hashes are available only through an explicit evidence disclosure.
- Evidence screenshots wait for transient notices to disappear.

### Pass 2: passed

- Full-view comparison confirms the same task-command-center hierarchy and region proportions without overlaps or clipped persistent controls.
- Focused orchestration comparison confirms the five-stage flow, branch-local evidence blocking, verified checkpoint distinction, and final-submit boundary.
- Focused Decision Inbox comparison confirms the primary evidence decision, related artifact, steer preparation, and branch controls remain visible and fact-bound.
- Mobile and history captures close the earlier P1/P2 findings. No actionable P0, P1, or P2 findings remain.

## Residual Boundaries

- Visual similarity and browser correctness do not prove that target users make faster or better decisions; that requires a separate usability study.
- The source contains unsupported recovery, timing, sharing, and progress claims. Their omission is an intentional product-truth constraint, not a fidelity defect.
- The current Demo remains a fixed Fixture and does not prove real CRM, email, or long-running connector execution.

final result: passed
