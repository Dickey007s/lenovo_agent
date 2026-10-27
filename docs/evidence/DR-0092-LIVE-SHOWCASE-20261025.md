# DR-0092 Evidence: current-system showcase

Capture date: 2026-10-24 UTC; packaged 2026-10-25 local. Working tree based on fa974ae, not committed. App localhost:3014, API localhost:8014, actual deepseek-v4-pro provider, memory store. No request routing/mock responses in capture script.

## Published observations

| Case | Run suffix | Calls | Observation |
| --- | --- | ---: | --- |
| rule | 5cff919e1ead4c43b58bb4b6da838ee2 | 2 | Rule and personal exception anchored; readonly result |
| missing | 541ec9ad67404de7ada3dab8d767f657 | 2 | Ledger row located; receipt absent; balance is not payment proof |
| handoff | 30b41b203ee44882b8e68e88d8d0789c / fefe7c4358d84b0d8b0decfefc052635 | 4 | Human choice then child Run; both task-5579c1e34209 |
| batch task 1 / swarm | ffa72210bc2347b79f198cc13acecdfe | 5 | Three Worker receipts; review chose no addition |
| batch task 2 | 3a91f39aa02b419abe3e900617cc2eea | 2 | Single-controller readonly analysis |
| batch task 3 | 0f0fdafe985549c482c3a441fe8bcce9 | 2 | Single-controller readonly analysis |
| draft | dd4fe56cbafc4a6e898213eef50644ef | 0 | Human edit saved as version 2 |
| send | dc4011032e994589b0311c88a67ceaac | 0 | Edit cleared confirmation; disabled until rechecked; test receipt only |
| judgment | 7c13a34f6a554591b09e8392f26cdded | 0 | No preselected choice; reason required; no business approval |

Published: 7 model Runs / 17 model calls plus 3 fixed-rule Runs. Eight stories contain 31 steps / 30 distinct screenshots: swarm step 1 reuses the same batch-input screenshot. Full IDs and capture types are in `docs/showcase/office-agent-20261024/capture-*.json`. Public snapshots and request logs remain under `outputs/showcase-live-20261024`, not in the share package.

## Attempts not presented as successful captures

- First missing run 637a2e3117c44db88d948d2d64c2fa39 used 3 calls, ended waiting with no adopted analysis because source positioning failed. Original snapshots and screenshots retained under `first-missing/`.
- First three-task batch used 9 calls and finished, but the UI capture wait was too short for the delayed state update. Snapshots retained under `first-batch/`. Second batch was rerun for a coherent capture sequence, not spliced with the first.
- Total across published and additional attempts: 29 actual model calls. The second missing run's final two screenshots were reopened readonly; input/process screenshots belong to that same second run.
- The swarm planning screenshot still shows planning. Caption explicitly says no division result has arrived; it is not labeled as active Worker execution. Final screenshots show the real three receipts.
- A terminal reload can initially select the result surface before the task surface. Capture waits for restoration before navigating. No claim this underlying UX was fixed.

## Checks

Final user-directed restoration: original desktop sidebar layout and uncropped screenshots restored. The expanded/cropped layout described below is historical, not the delivered default. Updated regression verifies the sidebar sits right of the story, image width matches its frame, and native-size opening remains available; all 124 step checks are rerun.

Readability follow-up (2026-10-25): full-width screenshots, horizontal case selection, task-area/full-frame segmented control, and native-resolution lightbox default. All original PNG bytes remain unchanged. Four-width regression also checks crop scale >1.39 relative to full-frame, complete-frame bounds, native 1920px width, and keyboard close behavior. Human-review frame uses its modal bounds rather than the normal workspace bounds. Visual inspection at 1440px confirms the task text is no longer squeezed beside a case sidebar.

`node scripts/test-showcase-live-20261024.cjs`: passed 124 case/step viewport checks (31 steps x 4 widths), three tabs, restart, disclosure, lightbox/native-size, keyboard, Escape/focus, reload/back, invalid hash, clipboard/fallback, missing-image recovery. Zero page errors and zero HTTP requests during offline browsing. Fixed dialog close-event focus theft in showcase JS.

Visual inspections included actual ledger evidence, human decision dialog, Worker result display, changed-content confirmation, and desktop/mobile showcase layouts. No full application suite rerun in this reporting-only slice. Source-location validity does not establish semantic correctness. No external business action, production deployment, file mutation, unrestricted swarm or real-provider dynamic expansion claimed.
