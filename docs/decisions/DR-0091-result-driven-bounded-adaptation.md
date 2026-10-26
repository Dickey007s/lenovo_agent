# DR-0091: Result-driven Bounded Adaptation

Date: 2026-10-24. Status: Limited Verified for bounded Runtime gates and UI; real-provider expansion remains unverified. Working tree based on fa974ae; no new commit/PR.

## 场景与来源

[Stakeholder source](../sources/USER-FEEDBACK-20261024-adaptive-progress.md), [SCENARIO-078](../scenarios/SCENARIO-078-result-driven-office-work.md). Earlier DR-0090 demonstrated real5-worker execution, but its input prescribed the five work items and dependencies. It did not prove result-driven team adjustment.

## 前台交互影响

Default office examples now specify business goals and readonly boundaries, not Agent numbers, graph layers or delegation instructions. Existing unified Task view shows a short initial route reason and an “执行调整” section only when a real review record exists. It distinguishes assessing, added work, no addition, rejected adjustment and discarded late adjustment. Detailed reasons and work-package results expand on demand. No fabricated live nodes or automatic approval buttons.

## 后端事实映射

- Automatic readonly mode gains at most two result-driven coordination reviews per Run. They run after real Worker returns, before wave commit/terminal status, and only with budget for review plus useful execution beyond outstanding work. Each review consumes a model call reserved before invocation, with persisted record and ordered event.
- Coordinator receives original instruction, existing work, approved-source bounded safe content and actual source-located adopted findings. Content uses the same allowlisted, size-bounded projection as Analyst; truncation is not evidence of absence. It may add0–2 readonly work items, explaining each new question and its triggering Finding IDs. It does not rewrite old work, retry failed units, decide human choices or add sources outside the original plan.
- Server requires adopted parents, grounded trigger identities, parent-source inclusion, no reused trigger, no exact duplicate objective, no human-decision trigger, plan capacity12 and remaining-call capacity. Semantic necessity is still a model judgment, not proven entailment or optimality.
- Valid additions compile to server-owned IDs, Branches and WorkUnits in the same locked wave commit, then use ordinary source/anchor/Contribution and reviewed-handoff gates. Existing adopted siblings and immutable versions remain. Actual new Worker execution is separate from a proposal being admitted.
- Review failure does not delete valid output or turn missing review into a clean finish. It leaves waiting status with an explicit reason and no addition. Pause/stop during a review discards new work; in-flight calls are not claimed canceled. Reserved in-flight waves retain existing checkpoint/no-autoreplay semantics.
- Automatic readonly admission can accept more than three independent roots and use ready waves capped at3; same-directory independent multi-source work is no longer excluded solely by directory. Same-structure repeated work, insufficient budgets, unsafe plans and missing source facts retain conservative routes. Legacy manual policy remains unchanged.
- Public `adaptive_reviews` and ordered `adaptive_review_started/completed` events record reasons, trigger IDs, new Branch IDs, called/adopted flags and elapsed time. Public text uses existing business projection. Existing Owner, version, idempotency, source and budget gates remain.

## 验证与边界

See [Evidence](../evidence/DR-0091-ADAPTIVE-PROGRESS-20261024.md). Controlled tests cover actual Runtime extension/unchanged/rejection, controls during a delayed response, restart, two-review cap, budget preservation and legacy admission. The 18 real-provider tasks used 61 model calls during iteration. Ten coordination reviews all chose no addition: no claim of real-provider dynamic expansion. Some source-anchored prose remains semantically inaccurate; source location is not entailment. This slice is append-only bounded adaptation inside an already admitted readonly collaboration, not arbitrary agent replacement, unlimited recursive teams, production scheduling, a calibrated difficulty model or a cross-Task global queue. Single-controller work does not gain a new team-expansion loop here.

Live inspection also exposed context-only findings disappearing from the task overview. Such findings now remain visible as unfinished instead of silently dropping out of an otherwise green delivery. This changes the browser projection only, not server completion or evidence roles. Worker excerpts now collapse for all team sizes, and review time labels have their own line.
