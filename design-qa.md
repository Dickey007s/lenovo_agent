# Demo 1 / Demo 2 Reference UI QA

## 2026-09-12 integrated boundary pass

Added original-task Agent/user boundary explanations and an unframed Swarm admission/receipt strip.
Fixed single-controller wording, ready-before-dispatch labels and ready-wave source projection.
Screenshot review also found coincident orthogonal dependency lines that looked like one shared bus;
curved paths now retain separate source/target pairs. Partial-fixture WorkUnit dependencies were aligned
with its Branch facts rather than accepting contradictory test data. See
[DR-0063 Evidence](docs/evidence/DR-0063-INTEGRATED-BOUNDARIES-AND-SWARM-FACTS-20260912.md).
1440/390 px fixture screenshots are separate from live Provider and user comprehension. The mobile DAG
remains horizontally scrollable within its own surface. Q-01 coverage and actual-user understanding remain open.

Date: 2026-09-11. Scope: `/agent-capabilities` and its evidence-choice surface.

## Findings

The initial tested states had no remaining actionable P0/P1/P2 visual findings.
The follow-up acceptance pass found UI-01 (new task from collaboration did not show a composer)
and UI-02 (evidence choice omitted the current claim context); both are now fixed and regression-tested.
Q-01 remains open: a real log-analysis run received a truncated prefix and produced insufficiently
scoped prose. This is a content-coverage failure, not a visual pass. See the
[acceptance report](docs/reports/demo12-acceptance-20260911/index.html).
The updated choice page was also inspected at 390 px; claim, candidates and buttons fit without overlap.
This is a reference-aligned redesign, not a pixel-identical reproduction of the supplied
illustrative Run. Dynamic facts deliberately differ from the mock.

## Comparison Evidence

Source visual truth is the user's five supplied PNGs. Four focused product views are
preserved under `docs/reports/demo12-redesign-20260911/references/`; the first, dense
control-console reference informs the optional full audit rather than the default screen.

| View | Source | Browser-rendered implementation |
| --- | --- | --- |
| Progress | [Reference](docs/reports/demo12-redesign-20260911/references/progress.png) | [1672 px](docs/reports/demo12-redesign-20260911/screenshots/progress-1672.png) |
| Execution record | [Reference](docs/reports/demo12-redesign-20260911/references/record.png) | [1672 px](docs/reports/demo12-redesign-20260911/screenshots/record-1672.png) |
| Collaboration | [Reference](docs/reports/demo12-redesign-20260911/references/collaboration.png) | [1672 px](docs/reports/demo12-redesign-20260911/screenshots/collaboration-1672.png) |
| Evidence choice | [Reference](docs/reports/demo12-redesign-20260911/references/evidence.png) | [1672 px](docs/reports/demo12-redesign-20260911/screenshots/evidence-1672.png) |

- Source: 1672 x 941 pixels, verified from PNG headers. Implementation: 1672 x 940 CSS/pixels,
  device scale factor 1. The source has one additional bottom border pixel; this is excluded
  from fidelity judgments. No density resampling, compositing or screenshot editing was applied.
- Source and implementation pairs were opened together in the same image comparison calls.
  Candidate labels, highlighted quotes, navigation and node text were readable at that size;
  separate cropped images were not needed for those regions.
- Additional browser viewports: 1440 px and 390 x 844. Mobile graph is intentionally locally
  scrollable, not compressed to illegible nodes. See [graph](docs/reports/demo12-redesign-20260911/screenshots/collaboration-390.png),
  [review first viewport](docs/reports/demo12-redesign-20260911/screenshots/evidence-390.png)
  and [review candidates after scrolling](docs/reports/demo12-redesign-20260911/screenshots/evidence-candidates-390.png).
- Screenshots use actual React components with controlled API fixtures. The reference has
  Run 2, three business branches and illustrative PRD lines; the recovery fixture has Run 1,
  two waiting branches and real fixture locations. The collaboration fixture has five WorkUnits
  with different dependencies. Counts, names, positions and colors must follow Snapshot facts,
  so these are state differences, not pixel-comparison failures.

## Iteration History

| Earlier finding | Severity | Fix | Post-fix evidence |
| --- | --- | --- | --- |
| Legacy 1180 px content limit made the working area too narrow | P1 | Scoped route width and content shell overrides | Progress and collaboration 1672 px |
| Hidden accessibility label appeared in the task title | P2 | Scoped `sr-only` declaration | All four desktop views |
| Evidence columns used intrinsic width instead of available width | P1 | Full-width grid and bounded columns | Evidence 1672 px |
| DAG node details could clip and duplicate navigation displaced results | P2 | Fixed node geometry, shorter dependency labels, peer side tabs, collapsed detailed route facts | Collaboration 1672/1440/390 px; bounding checks |
| Execution record inherited the previous page scroll position | P2 | Reset surface scroll on view/Run changes; removed conflicting panel-only smooth scroll | Record 1672 px; toolbar position regression |
| Evidence/body and file labels were too small relative to the reference | P2 | Desktop evidence body 17 px; record file labels 16 px; mobile overrides retained | Evidence and record final desktop captures |
| Full-page capture of a fixed mobile dialog included the background below its viewport | Evidence issue | Capture dialog viewport and a separate scrolled candidate viewport | Two mobile review images |

## Fidelity Surfaces

1. Fonts: Segoe UI, Microsoft YaHei, sans-serif; local `msyh.ttc` exists. The source does not
   identify its exact font file. Titles retain strong hierarchy, normal letter spacing and
   readable body text. Compact audit metadata remains 13-14 px instead of the mock's larger
   presentation text. This is an accepted working-tool density difference, not exact font matching.
2. Layout: 68 px top toolbar, constrained wide workspace, peer navigation, branch rows, actual
   dependency graph, and a dedicated two-column review. Viewport scroll remains available for
   longer real content. Repeated nodes and candidates have restrained 4-8 px radii.
3. Colors: white/light gray surfaces, blue primary actions, green adopted/preserved facts,
   amber waits and red errors. No ornamental gradients or illustrations. Color is accompanied
   by text/icons, not the only status signal.
4. Assets: existing Tabler icons are retained. The dependency SVG is a data graph, not an
   illustration substitute. Original reference PNGs and actual captures remain sharp and
   unmodified. The operational reference contains no photographic asset to replace.
5. Copy: backend names, counts, file locations and versions are not hardcoded from screenshots.
   Preview does not select a candidate. Terminal confirmation says it records the location,
   not that the old Run resumes. Response loss remains an unknown outcome, not a false failure.

## Interaction Verification

- Full Playwright suite: 90 passed after the final scroll/typography changes.
- Six focused redesign cases cover no preselection, preview/selection separation, source and
  request identity, top-level authority, stale and terminal states, confirmation/defer errors,
  dialog focus boundary, and graph bounding checks.
- Existing cases cover history, current-pointer conflicts, branch continuation, Worker approval,
  immutable versions, new drafts and source previews. Their fixture scope is preserved.
- Real local API health reports memory state; the actual Codex in-app browser loaded the workspace,
  switched peer tabs and opened an empty draft without submitting a task. Console errors: none.
- An old test-server tab was unavailable after its server stopped; a new tab was used for the
  separately running actual preview. No security interstitial was bypassed.

## Residual Gaps

- No target-user study, real Provider run, PostgreSQL restart gate, screen-reader study or
  exhaustive zoom/browser/device matrix was performed in this redesign pass.
- Independent report HTML and Demo 3 draft are not covered by this app QA pass. The co-driving
  report's file URL was refused by browser policy; it was not served through another route to
  bypass that refusal. Its 38 checks are source/VM checks, not browser rendering evidence.
- P3: evaluate larger audit metadata and mobile sticky confirmation with target users after
  reviewing actual long-content tasks. These are follow-up preferences, not current blockers.

## Implementation Checklist

- [x] Compare supplied visual targets and rendered views together.
- [x] Repair width, node clipping, typography and view navigation issues.
- [x] Re-capture and re-run functional regression after the fixes.
- [x] Preserve server authority, historical data and explicit user choice.
- [x] Record draft, fixture and unverified-runtime limitations.

## Follow-Up Polish And Research Library (2026-09-11)

This section is the latest pass. Earlier results above remain historical evidence.
The user explicitly approved Playwright automation alongside the Codex in-app browser.

### Findings And Recheck

| Finding | Severity | Resolution |
| --- | --- | --- |
| Long real goal was truncated with no full-text surface | P2 | Native goal disclosure, 1280/390 px tests; no new Run or control |
| Actual evidence confirm button was entirely below a 720 px viewport | P1 | Fixed review action bar; measured y=662-706 versus previous y=907-953 |
| An experimental sticky main control bar covered the Artifact | P1 | Removed main-bar stickiness after side-by-side reference comparison |
| Fixed review bar intercepted the lower cancel action | P1 | Override legacy review grid with natural flow; real desktop/mobile cancel clicks pass |
| Search blur replaced the research-library button being clicked | P1 | Search uses input; dropdowns use change; first-click reset/detail regression passes |
| Research mapping captions fell into the icon column | P2 | Put the icon wrapper across rows and captions in text column; height assertion passes |

### Visual Recheck

- Reference progress/evidence PNGs and final app screenshots were opened together at 1672 px.
  Source has 941 rows; app capture viewport is 940 rows. No screenshot compositing or resizing edits.
- Fonts: existing Segoe UI / Microsoft YaHei; bounded two-line 17 px title with readable full goal.
  Compact task panels retain working-tool density rather than increasing every heading.
- Layout: reference-aligned white workspace, peer tabs, stages, alert, Branch rows and Artifact.
  Branches fill available columns; review is two-column desktop, stacked mobile, with reserved footer space.
- Colors: blue actions, amber pending, green preserved/adopted facts, gray supporting metadata.
  Research library uses white bands, restrained rules and colored source types, not decorative cards.
- Assets: existing Tabler icons; library bundles licensed Tabler output. Reference images and captures
  are actual PNG/JPEG assets; all data and status labels remain evidence-dependent.
- Copy: selected candidate is not a recorded decision; preview is not approval; no false external action.
  Library separates observations, framework semantics and proposed Demo changes, including research limits.
- Mobile evidence first-view and scrolled candidates were both inspected. The final 390 px image shows
  both candidates, no blank paint region, no overlap and a disabled visible confirmation action.
- New research library desktop/mobile, detail and mapping images were inspected; both title and caption
  stay inside their surfaces. Long content scrolls; dialog closes with Escape and returns focus.

### Latest Verification

- Full Playwright: **96 passed** (94 app + 2 standalone library), including regenerated screenshots.
- TypeScript and isolated production build: passed. Reporting governance: 4 passed.
- Research source/data/VM checks: 61 passed, separately recorded from browser validation.
- Actual Codex browser: historical task, goal disclosure and evidence review verified; console errors none.
  The existing task still has three model calls. No new paid Provider run was made in this pass.
- The old Demo3 sandbox file that was denied remains untouched; only the new library received
  separately authorized offline Playwright verification. No alternate route was used for the denied file.

Evidence: [polish report](docs/reports/demo12-polish-20260911/README.md),
[research browser record](docs/reports/copilot-research-library-20260911/browser-verification.md),
[combined record](docs/evidence/DEMO12-POLISH-AND-COPILOT-RESEARCH-EVIDENCE-20260911.md).

Residuals: Q-01 text-input truncation remains open. No user-effect, Provider, PostgreSQL restart,
distributed Worker, screen-reader or exhaustive zoom/device claim. Previous P3 sticky-confirmation
exploration has now been implemented and checked locally, not validated as a user-performance gain.

final result: passed
