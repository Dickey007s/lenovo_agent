# System Source Sync: 2026-10-26

## Scope

Source baseline: `fa974ae339c9c4d97d0505eb3eef3e8a81e8ca11`, matching origin/master when fetched for this sync. Target: origin `codex/demo123-integration`; master is not changed by this push.

This source snapshot includes the accumulated unified workbench, same-task follow-up branches, evidence and responsibility projection, bounded adaptive readonly execution, primary-first planning/method loading, Demo3 controls and twelve prepared examples. API/contracts, tests, decision/scenario/source/evidence documents and selected startup/preflight scripts are included.

Local presentation decks, generated images, screenshots, recordings, rendered HTML/PDF reports, build caches, sessions and environment credentials are intentionally excluded. References to local report/screenshot outputs in historical evidence are not a claim that those media are included in this source-only sync. Their files remain on the original workstation; operational code does not depend on these presentation assets.

## Validation

- Full backend `pytest -q --disable-warnings --maxfail=3`: **646 passed, 26 skipped**,336.43seconds. PostgreSQL-dependent tests are skipped without their test DSN; no PostgreSQL verification is claimed here.
- Web `pnpm exec tsc --noEmit`: passed.
- `node --test scripts/demo-service-preflight.test.cjs`:3 passed.
- Previous same-day focused Demo3 browser gate:29 passed; final example-only rerun13 passed, recorded in DR-0098 Evidence.
- Full browser gate is not green: historical `copilot-case-review.spec.ts` still uses the retired “办理事项” entry instead of “Demo 3 · 人机共驾”. The three C02/C08/C11 screenshot cases time out on that locator. Run configured to stop at3 failures; the rest of the full suite is not established by this run. No test assertion was removed to mask this failure.
- Staged-file audit: no environment/cache/media files, no common secret-format matches, and no missing relative frontend imports. This is a bounded local check, not a production security audit.
- `git diff --cached --check`: passed before commit.

## Reproduce

Use the tracked lockfiles and existing README setup. `scripts/start-demo12-live.ps1` starts the original application with locally configured provider credentials and isolated in-memory state. `scripts/start-demo3-examples.ps1` starts an isolated fixed-rule preview with model access disabled. Neither script embeds credentials or replaces an occupied port's server.

The twelve Demo3 inputs are in `apps/web/app/office-action-examples.json`; they can be selected in the original Demo3 form. Static presenter HTML and PPT are separate local deliverables, not required to run these inputs.
