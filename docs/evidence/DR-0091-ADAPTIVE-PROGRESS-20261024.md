# DR-0091 Adaptive Progress Evidence

Date: 2026-10-24. Working tree based on fa974ae, no new commit/PR. Decision: [DR-0091](../decisions/DR-0091-result-driven-bounded-adaptation.md). Scenario: [SCENARIO-078](../scenarios/SCENARIO-078-result-driven-office-work.md). Source: [user request](../sources/USER-FEEDBACK-20261024-adaptive-progress.md).

## Scope And Verdict

Limited Verified: append-only bounded work additions are implemented and exercised through the real Runtime using controlled model responses. Live initial planning/routing and post-wave no-add decisions are observed with deepseek-v4-pro. **Real-provider dynamic addition has not been observed and is not accepted as demonstrated.** No distributed execution, optimal team sizing, semantic correctness guarantee, external action or arbitrary replanning is claimed. Single-controller tasks do not acquire a post-analysis expansion loop in this slice.

## Actual Provider Iterations

Every task was submitted through the real browser and API; no mocked route or response. Isolated app3014/API8014 uses memory storage. API restarts were idle-only and previous public histories archived under `outputs/adaptive-swarm-20261024/server`. Original3010/8010 was not restarted. Archives remain local; they are not restored durable Tasks.

| Output subdirectory | Actual tasks | Model calls | What happened |
| --- | ---: | ---: | --- |
| first | 3 | 6 | Main onboarding goal selected an irrelevant PRD, stayed single-controller and waited on missing coverage. Other two completed. |
| second | 3 | 6 | Generic planning guidance removed irrelevant sources; coherent onboarding work still stayed single-controller. |
| third | 3 | 9 | Business-only cross-department goal produced3 execution Workers; two simpler tasks stayed single-controller. Coordination chose no addition. |
| variants | 3 | 13 | Two/two/three Workers. All three reviews chose no addition. Semantic issues detected by manual source inspection. |
| final-variants | 3 | 14 | Reviewer received fuller finding detail. Two/two/three Workers; one analysis repair. Still no addition. |
| source-grounded | 3 | 13 | Reviewer received bounded original source content. Two/two/three Workers and three no-add decisions. |
| Total | 18 | 61 | 10 real coordination calls, zero expanded decisions. |

Exact Run IDs, raw instructions, terminal status, review receipts and counts: `outputs/adaptive-swarm-20261024/live-summary.json`, generated from all18 saved Snapshots by `scripts/review-adaptive-swarm.cjs`. Individual snapshots and screenshots remain in each subdirectory. These are repeated iterations of office goals, not18 distinct benchmark scenarios or a measured success rate.

Representative actual runs:
- Initial business-only three-Worker brief: `harness:b67e12a03cf24e20b3cf2068af4e2533`, planner +3 Workers +coordinator =5 calls.
- Final source-grounded two-Worker case: `harness:9841f2ca63cf4e39986d8e399f951f36`.
- Final source-grounded three-Worker case: `harness:12026b9c974349e1924a873eca3e7bc6`.

## Problems Found By Walking The UI

1. Earlier onboarding interpretations falsely treated source-defined exceptions as missing rules. Later output correctly described override precedence but still called it a conflict. A successful Anchor match proves location, not a correct interpretation; coordinator no-add is also only a model judgment. The review now receives the safe bounded source projection, but the semantic problem is not claimed solved.
2. The final two-Worker run contains3 findings; its recruitment finding has only context-role anchors. The overview excluded it from delivered analysis yet silently showed completion of the remaining2. Fixed: context-only findings remain visible as unfinished. No source roles or server terminal status are rewritten. Dedicated regression covers this exact pattern.
3. Three-node graphs still expanded long paragraphs while larger graphs folded them. Now every result is folded by default; actual status, title, dependencies and adjustment reason remain visible. Review timing and headline no longer run together.

## Automated Checks

- `tests/acceptance/test_adaptive_progress.py` and `tests/unit/test_adaptive_review.py`:20 passed. Tests cover addition/no-add, provenance/scope rejection, human decision exclusion, duplicate/used trigger rejection, budget reservation, pause/stop races, checkpoint interruption, two-review cap and more-than-three total roots without lifting concurrent-wave cap.
- Broader backend command: adaptive_progress, adaptive_review, harness_runtime, automatic_readonly, demo12_worker_reliability, demo12_reviewed_collaboration, demo1_demo2_fixed_scenarios, collaboration_review:114 passed.
- Focused browser/projection group: unified reference workbench, worker stages, todo summary, task responsibility:39 passed. Provider responses in these tests are fixtures, not live evidence.
- `pnpm exec tsc --noEmit`: passed. `git diff --check`: passed with existing Windows line-ending notices.
- Broader earlier browser selection:36 passed,1 failed. The legacy test at `apps/web/e2e/harness-workbench.spec.ts:6980` expects a retired root-page “Agent 能力” link and old navigation before reaching dispatch. It is not included in the39-pass group and remains unmigrated; the full browser suite is not claimed green.
- Initial system Python lacked psycopg and failed collection; tests were rerun in the project `.venv`. An intermediate source-projection helper typo was caught by failing tests and corrected before the final source-grounded runs. A controlled expansion fixture repeated an identical objective; the fixture now creates distinct objectives rather than weakening the duplicate gate.
- PostgreSQL/multi-process restart, user study and full repository test suite not run this turn.

## Actual Browser Inspection

`scripts/review-adaptive-swarm.cjs` opens the actual completed three-Worker task, expands a real result and opens evidence. At1680 and390 pixels, no horizontal overflow, no page errors and zero POSTs during inspection. Screenshots and checks: `outputs/adaptive-swarm-20261024/review/`. The final screenshots were visually inspected, not only checked for selector success. The available in-app browser connection was unavailable, so the executable check used installed Edge through Playwright.

## Remaining Acceptance Gap

The implementation can append work and execute it without repeating roots in controlled tests, including a3→4→5 Worker progression. This is not a live model success. A future live example must naturally expose a new unresolved question, produce a grounded addition, execute the new Worker and preserve prior outputs. Do not preset the team or force expansion to obtain a screenshot. Cancellation/replacement of already scheduled work and promotion from a single controller remain outside this bounded slice.
