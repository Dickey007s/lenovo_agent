# DR-0090: Multi-stage Worker Display

Date: 2026-10-24. Status: Limited Verified. HEAD fa974ae plus uncommitted working tree.

## Scenario And Source

[User request](../sources/USER-FEEDBACK-20261024-more-than-two-agents.md), [SCENARIO-077](../scenarios/SCENARIO-077-five-worker-office-brief.md), [Evidence](../evidence/DR-0090-FIVE-WORKERS-20261024.md).

Two independent analyses demonstrate only the minimum collaboration. The new default editable group is “跨部门简报 · 分阶段协作”: one brief with three independent source analyses and two dependent checks, plus two simple office todos. Existing two example groups remain available.

## Frontend Decision

- Group actual WorkUnits by dependency depth. Resolve references using work_unit_id, unit_id or branch_id. Missing parents and cycles appear under “依赖待核对”, not independent work.
- Stage headings describe dependency order, not dispatch waves or concurrency. Six roots in one stage do not prove six simultaneous executions.
- Each node retains actual Branch title, status and dependencies. Matching current Contribution/Worker receipts supply adoption and role labels. Unadopted output and failed/pending work remain visible.
- When there are more than three WorkUnits, individual result excerpts collapse behind “查看结果”. Task, source, full results and cooperation records remain available.
- An unstarted dependent package says “等待前序成果” when parents are missing/incomplete. Returned but unadopted work remains explicitly unadopted.

## Server Contract

No backend, prompt, admission, API, budget or permission change. Instructions request useful dependencies, not an exact Worker-count override. Existing automatic_readonly and maximum three ready Workers per dispatch remain. Model planning/admission may vary in future runs. Difficulty and optimal agent count are not established by this example.

The current real sample generated five distinct execution Workers, with a Planner call preceding them. The coordinator is not counted as a sixth execution Worker. Two actual reservations were 3 + 2; five concurrent or distributed Workers are not claimed. Downstream review consumes approved upstream Contributions and rereads approved sources through existing DR-0066.

## Verification And Limits

Two actual repetitions of three Tasks: six Tasks,20 model calls, ten called/adopted Worker receipts across the two complex Tasks. Both complex Tasks had five WorkUnits, two waves and two immutable logical Artifact versions. Desktop/mobile, dependency helper and regression checks are recorded in Evidence.

Only readonly analysis was delivered. No new Word/Excel file, hiring decision, permission change, bank validation or original-file modification. Rejected: fake agent counts, lifting the concurrency cap just for visual impact, new separate Demo2 UI, hiding source uncertainty, treating two successes as a general success rate.
