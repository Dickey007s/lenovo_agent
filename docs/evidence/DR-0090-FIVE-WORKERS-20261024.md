# DR-0090 Evidence: Five Execution Workers In Two Stages

Date: 2026-10-24. HEAD fa974ae plus uncommitted tree. [Decision](../decisions/DR-0090-multistage-worker-display.md), [Scenario](../scenarios/SCENARIO-077-five-worker-office-brief.md), [Source](../sources/USER-FEEDBACK-20261024-more-than-two-agents.md).

## Real Provider Runs

Web3010/API8010, deepseek-v4-pro, memory store. `scripts/exercise-office-todos.cjs <output-directory> 2` started the new three-task group twice through the real UI. No mocked responses in these runs. No human dispatch confirmation. Six Tasks,20 total calls; each complex Task used one Planner plus five Worker calls, each simple Task two calls.

| Task | First Run (prefix harness:) | Retest Run | Calls each |
| --- | --- | --- | --- |
| 周度办公简报 | 5a7782b0cadf49559ba33bedf205fcf2 | b06c6dfb34f449f5b5f9909aca86f83e | 6 |
| 商务岗位要求 | 4779ad9114674b718450dccd2fdc5bbe | afb8d265f9f64711a60a0e068c2a63d0 | 2 |
| 新员工入职信息 | ea43aeeeb05f48d7b6d47dcc21c7b21c | d87687ad716c48ba921ec0974dfc7482 | 2 |

All six completed. Each complex Task: five WorkUnits, five called/used/adopted Worker receipts, two reservations sized3/2, Artifact v1/v2. Three source_analysis roles, one synthesis_review with two supported prior-contribution assessments, one dependency_review with one supported assessment. First complex run has six findings, retest seven: findings are not Worker counts.

## Observed Overlap And Handoff

UTC on2026-10-24. First run first-wave starts14:07:53.664904,54.507211,55.355186; earliest completion14:08:01.936285. Second-wave reservation14:08:03.421186, starts03.653768/04.453963, completions12.130406/16.313585.

Retest first-wave starts14:09:48.406432,49.292458,50.128991; first completion56.860546, last58.884457. Second-wave reservation14:09:59.576488, starts59.798246/14:10:00.562695; completions14:10:08.912638/11.596762. Thus three overlapping analyses followed by two overlapping checks, not five simultaneous executions. No throughput comparison was conducted.

## Concrete Outputs

- Recruitment: Python coding, scripting and data-processing requirements from the Word job description.
- Administration: 大象 IM、学城文档、Microsoft365 from the common-software PDF rule.
- Accounts: named counterparty other-receivable opening1,500,000, debit200,000, closing1,700,000 from Excel.
- Downstream synthesis: checked two actual prior Contributions against their sources; recruitment and software are separate document topics, not a same-person hiring/permission approval.
- Downstream amount check: compared the actual prior Contribution against the original Excel row. No bank receipt or independent financial audit.
- Simple tasks: BD education requirement; 吴嘉木 entry dated4月07日（周二）,研发,不开通研发权限. No access change executed.

## Validation

- `pnpm exec tsc --noEmit`: passed.
- Playwright integration filtered `worker stages|todo summary|unified reference`:30 passed. Covers dependency aliases/depth/cycles, six roots not a dispatch wave, five-node desktop/mobile disclosure, stale attempts, manual-policy preservation and existing batch navigation.
- Pytest automatic_readonly, worker_reliability, reviewed_collaboration, collaboration_review and reporting_governance:37 passed.
- Both real-run browser checks: no page errors, no horizontal overflow at1680/390; readonly detail navigation created no extra starts.
- `scripts/review-worker-stages.cjs`: final1680x1400/390x844 review; all five nodes present, results initially folded, dependent result and source inspected. Zero POSTs, page errors or horizontal overflow. Screenshots manually inspected.
- HTML report rendered with answer-me-with-html, zero writing warnings;1680/390 checks show embedded screenshot loaded, no horizontal overflow or page errors. Governance recheck after documentation:4 passed.

Evidence files: `outputs/swarm-stages-20261024/first/`, `retest/`, `review/`, `regression/`. These contain public snapshots, start IDs, active-root/dependent-stage screenshots, final source/result screenshots and checks. They are local verification artifacts, not stable production telemetry.

No new backend behavior, production deployment, target-user study, generated office-file delivery or general business-correctness claim. Prior DR-0066 controlled evidence remains unchanged; this record adds only these two live handoff observations.
