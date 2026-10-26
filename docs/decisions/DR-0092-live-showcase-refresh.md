# DR-0092: Live screenshot showcase refresh

Date: 2026-10-25. Status: Limited Verified for actual captures and offline browsing.

## Source and scenario

[User source](../sources/USER-FEEDBACK-20261024-showcase-rerun.md), [SCENARIO-079](../scenarios/SCENARIO-079-browse-live-showcase.md).

## Decision

Preserve the old 20261023 showcase and publish a separate 20261024 capture folder. Keep three capability tabs and eight case stories. Demo1/2 use actual provider responses rather than routed fixtures; Demo3 uses the existing fixed-rule API, without a model or external actions. Publish 1920x1200 screenshots with native-size viewing and relative offline assets.

The two Demo2 stories are two views of the same three-task batch, not separate experiments. Its first task has three Worker receipts and a real unchanged coordination review. No actual dynamic expansion is claimed. Inputs state office goals without specifying Agent counts. The missing-bank-receipt story preserves its first unsuccessful attempt in outputs and publishes a second actual run. A completed Run does not establish that missing business evidence is resolved.

## UI and server mapping

Captured screenshots are projections of actual Run/Task state. Public capture manifests identify Run IDs, Task IDs, model calls, statuses and capture type. Task continuation is supported by matching parent/child task_id; worker counts use worker_runs; adaptation uses adaptive_reviews. Demo3 receipts explicitly retain model_called=false and external_action=none. The offline page does not execute a task. Its local workbench link only works on a machine running the application.

Only showcase presentation and capture/validation scripts change. No Runtime/API behavior changed here. Closing the screenshot dialog now avoids stealing keyboard focus after a later user navigation.

2026-10-25 readability update: user reported screenshot text too small. Move case selection above the story, give screenshots the full content width, and default to a viewport over the task area. Preserve original image bytes and offer full-frame mode. The human-review modal uses its own bounds so its left explanation is not clipped. Lightbox now opens at native resolution; fit-to-window remains available. This is image presentation, not a recapture or changed system state.

## Evidence and limits

Final layout choice, 2026-10-25: user requested restoring the original layout. The full-width/cropped presentation above was an intermediate iteration and is no longer active. Desktop again has left screenshots/right case navigation, uncropped images, and the original responsive mobile layout. Native-resolution lightbox opening remains.

[Evidence](../evidence/DR-0092-LIVE-SHOWCASE-20261025.md). Thirty-one presentation steps reuse thirty distinct screenshots. Four viewport checks cover every step. This is browser and bounded scenario evidence, not a full application regression, user study, business certification or guarantee of repeatable model decisions. Capture attempts exposed SSE display delay and source-location rejection; neither is hidden or described as fixed Runtime behavior.
