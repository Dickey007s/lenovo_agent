# DR-0089 Evidence: Everyday Office Todos

Date: 2026-10-24. HEAD fa974ae plus uncommitted work. No new commit or PR.
Decision: [DR-0089](../decisions/DR-0089-office-todo-outcomes-and-routing.md).
Scenario: [SCENARIO-076](../scenarios/SCENARIO-076-understand-office-todo-outcomes.md).
Source: [user request](../sources/USER-FEEDBACK-20261024-demo2-office-todos.md).

## Actual Execution

Web3010 / API8010, same source application, memory store, configured deepseek-v4-pro. No server restart in this slice. Keys and raw provider responses are not included.
`scripts/exercise-office-todos.cjs` drove the actual UI twice. Each pass selected two groups and started six separate Tasks. Total12 starts,26 model calls, two adaptive Runs with four called/adopted Worker receipts. All12 ended completed with reviewable analysis; no files generated or external business actions executed.

| Case | First Run suffix (prefix harness:) | Retest Run suffix | Route / calls each |
| --- | --- | --- | --- |
| Word recruitment requirement | 2db6aee8a0bb4e208a58e4d75f3ceed7 | ab4eec3c12ae424480bdc630d6313eb5 | single_controller /2 |
| Excel counterparty balances | 09419cee78ec43f49a0623df846b853d | f1d8ff40b2144baa84b84a361687f26e | single_controller /2 |
| Onboarding + recruitment checklist | 10e0d0dd2c29450b9a3d5d23acaa74ce | e2aa20a44c8e4065aae61803b61bb924 | adaptive_readonly_workers /3 |
| Common office software | 537db71e22b041dc85ca6d334f320c04 | a6462685a513433a8219a19cdb26ac30 | single_controller /2 |
| Business role requirement | 1ca8815d345543b384e40d7f3b598e70 | 94d40a57bfc0419e81438fb5841736dc | single_controller /2 |
| Two recruitment documents | 242ac86dded1411f89204789f248a5a4 | 1ada41c494734c3eba8c986919ad63fc | fixed_workflow /2 |

Snapshots, original screenshots and browser checks: `outputs/office-todos-20261024/`; second pass in `retest/`, final GET-only task/source review in `review/`. First-pass results were not overwritten.

The retest adaptive Run has analysis_started at13:52:59.675933Z and13:53:00.621693Z; first analysis_completed at13:53:06.847487Z. The overlapping model work is real for this Run. Across independent Tasks, analysis also overlapped; this is not a distributed-runtime or speedup benchmark.

## What Was Delivered

- Recruitment: cited Word requirements such as Python/data-processing skills or the BD role's education/communication requirement. The requested single example can differ across runs; not a complete hiring evaluation.
- Accounts: two accounts for the named counterparty, including other receivable opening1,500,000, debit200,000 and closing1,700,000. A second prepaid account has blank balances and a150,000 debit. Retest prose uses the source direction marker 平; do not interpret it as a bank receipt or an independent accounting audit.
- Cross-domain checklist: common software 大象 IM、学城文档、Microsoft365 plus one independently cited BD recruitment requirement. Two Workers returned and both contributions were adopted.
- Same-family pair: two cited job requirements, processed sequentially. Current same-directory heuristic kept this out of the worker route, despite two plan units. No artificial multi-agent forcing.

## Problems Found And Changes

1. Long disabled instructions remained after submission; now collapsed behind a short task title.
2. First-pass multi-agent preview showed two onboarding findings and hid the recruitment result. Preview now covers distinct Branches first.
3. Leaving the batch destroyed its local view. It now stays mounted across task/space navigation; explicit new task resets it. Refresh persistence is still absent.
4. Planned topology looked like executed work. Labels now separate admission, active work packages, called receipts and adoption.
5. Graph used branch-only fallback for an old Worker. It now requires the current Contribution/attempt before displaying adopted output. A controlled stale-attempt regression covers this.
6. Empty usable output, missing materials and pending decisions cannot become green just from Loop completion.

## Verification

- Live desktop1680 and mobile390: both passes have no page errors or horizontal overflow. Task/detail/back navigation did not add starts.
- Final `scripts/review-office-todos.cjs`: six task viewport checks, source inspection, zero POSTs, zero page errors, zero horizontal overflow. Screenshots visually inspected for readable source/result and work-package output.
- HTML report rendered through answer-me-with-html with three embedded real screenshots; `scripts/check-office-todos-report.cjs` passed desktop1680/mobile390 image-load, embedding, page-error and overflow checks. Report: `docs/reports/office-todos-20261024/index.html`.
- `pnpm exec tsc --noEmit`: passed.
- Python focused regression:15 passed, covering automatic readonly, Worker reliability and reporting governance.
- Frontend focused regression:24 passed, six projection checks plus18 browser cases. The first stale-attempt fixture initially omitted the Task current pointer and therefore opened no task; adding the actual matching pointer corrected the test setup, not product behavior.

```powershell
node scripts/exercise-office-todos.cjs
node scripts/exercise-office-todos.cjs outputs/office-todos-20261024/retest
node scripts/review-office-todos.cjs
.venv/Scripts/python.exe -m pytest tests/acceptance/test_automatic_readonly.py tests/acceptance/test_demo12_worker_reliability.py tests/unit/test_reporting_governance.py -q
# cwd apps/web
pnpm exec playwright test e2e/todo-summary.spec.ts e2e/harness-workbench.spec.ts --config playwright.integration.config.ts --grep 'todo summary|unified reference' --reporter list
```

## Limitations

These are simple readonly analysis examples, not arbitrary office editing. No calibrated difficulty/confidence model, optimal scheduling proof, productivity study, general success-rate result or new batch persistence. Actual failures were not induced in these12 live runs; partial/stale/unknown paths were tested with controlled fixtures. Evidence anchors locate text, not establish semantic correctness. Current API memory history will disappear on restart; snapshots preserve this run evidence.
