# DR-0096 Evidence

Date: 2026-10-26. Working tree, no new commit/PR. [Decision](../decisions/DR-0096-single-agent-result-driven-delegation.md), [scenario](../scenarios/SCENARIO-083-single-agent-then-delegate.md), [source](../sources/USER-FEEDBACK-20261026-modern-delegation.md).

## Implementation And Tests

Shared executor now accepts eligible automatic single-unit plans, then uses existing review/addition/commit. New origin and labels distinguish single execution from subsequent delegation. No new framework dependency.

150 backend checks passed in6.58s. Command: `.venv/Scripts/python.exe -m pytest tests/acceptance/test_single_agent_adaptation.py tests/acceptance/test_adaptive_progress.py tests/unit/test_adaptive_review.py tests/acceptance/test_automatic_readonly.py tests/acceptance/test_demo12_worker_reliability.py tests/acceptance/test_demo12_reviewed_collaboration.py tests/unit/test_harness_runtime.py tests/acceptance/test_demo1_demo2_fixed_scenarios.py tests/acceptance/test_demo12_output_and_dependencies.py tests/unit/test_workunit_ledger.py -q`.

New controlled cases cover one-to-two/three execution chains, no-add, source/trigger rejection, review error, spare-call gating, pause/stop, manual isolation, checkpoint non-replay and route eligibility. These are controlled model outputs, not live expansion.

Parent-preservation initially failed: identical source/title output replaced the parent's latest aggregate entry. Fixed with Branch-scoped server finding IDs before acceptance. Immutable old versions were not changed. Initial fixture keys were too short and manual-task wait was unbounded; fixed test inputs and used existing bounded state polling, without relaxing production checks.

Browser command in apps/web: `pnpm exec playwright test e2e/harness-workbench.spec.ts e2e/todo-summary.spec.ts e2e/worker-stages.spec.ts --grep 'adaptive adjustment|todo summary|worker stages'`:16 passed. Desktop1586/mobile390 adjustment screenshots: `outputs/single-adaptive-20261026/regression/`. They are fixtures, not actual expansion. `pnpm exec tsc --noEmit` passed after fixing a test-only `as never` type error. `git diff --check` passed with existing line-ending warnings.

## Real Provider Runs

Isolated memory API8026/web3026 via `scripts/start-demo12-live.ps1`; original3000 untouched. Existing configured credentials unchanged. Browser submitted three default goals through normal Run API. Capture command: `scripts/exercise-office-todos.cjs outputs/single-adaptive-20261026/live 0` with DEMO_API_URL/DEMO_WEB_URL pointing to isolated services.

| Run | Task | Execution Agents | Model calls | Review |
| --- | --- | ---: | ---: | --- |
| harness:264c681af99645aeb2d0dcfe83b74212 | 整理招聘要求 | 1 | 3 | single_agent / unchanged |
| harness:416703d2ff8a4835bc4391515f1021f5 | 核对一笔往来账 | 1 | 3 | single_agent / unchanged |
| harness:bc37724060654055a82d949cb9520fb8 | 准备入职与招聘交接清单 | 2 | 4 | worker_wave / unchanged |

All three reached completed with adopted readonly findings. Total10 calls includes planning, execution and three reviews. Zero live additions. These are page analysis, not Word/Excel delivery, hiring decisions, access changes or bank confirmation. No universal coverage/semantic-correctness claim.

Public snapshots: `outputs/single-adaptive-20261026/live/set-0-task-{1,2,3}.json`. Screenshots: `set-0-task-{1,2,3}-agents.png` and corresponding results,1680/390 overviews. `browser-checks.json`:zero page errors, no horizontal overflow, no new Run starts during detail navigation. Single-Agent task screenshot visually inspected; ordinary detail stays folded.

## Remaining Scope

Actual model single-to-team expansion not observed. No PostgreSQL/multi-instance test, full suite, user study or SDK comparison. Skills/tool progressive disclosure and general model-owned execution loop remain design work. Existing Python runtime retained; no LangGraph/Strands dependency introduced.
