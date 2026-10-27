# DR-0096: Single-agent Result-driven Delegation

Date: 2026-10-26. Status: Limited Verified for bounded execution, controls and UI. Working tree, no new commit/PR.

## 场景与来源

[User authorization](../sources/USER-FEEDBACK-20261026-modern-delegation.md), [SCENARIO-083](../scenarios/SCENARIO-083-single-agent-then-delegate.md). User accepted framework-neutral on-demand delegation, not a LangGraph migration. This is the first implemented slice of the [design](../reports/swarm-modern-design-20261026/index.html), not its entire skills/tool framework.

## 前台交互影响

Single-item automatic tasks show one actual execution node. Review says “单 Agent 处理后”; unchanged reasons stay folded. A committed addition changes the heading to “单 Agent 起步 → 按结果追加核对”. Planned work is not a returned call or proof of parallelism. Existing Task, evidence, result, stop and history remain. No new entrypoint or human confirmation in autonomous readonly work. Errors remain visible.

## 后端事实映射

- An automatic_readonly, analysis_only task with exactly one plan unit and one Branch can use the existing scoped Worker executor and ledger while admission remains single_controller. It must have no deferred/uncovered requirements, dependency, side effect, human gate, office_action or explicit topology override; planner must support review_progress. Other routes stay unchanged.
- The first execution is one Agent. Its adopted contribution enters the existing budget-reserved review. Review requires spare budget for a useful additional execution. Eligible simple tasks may cost one additional model call; no cost-saving claim.
- Reuse existing reviewer, validator and executor. Limits remain two reviews per Run, two additions per review, twelve plan units and three Workers per wave. Source, adopted-parent, trigger and human-decision gates remain.
- Only valid committed additions promote current topology. Initial topology_admission event remains single_controller. Plan, Branches, WorkUnits, review and topology commit together; old versions and contributions remain. Dependent work is sequential after its parent, not necessarily parallel.
- Additive `adaptive_reviews[].origin` defaults to worker_wave for historical records; eligible initial single work uses single_agent. Ordered events, Owner, version, idempotency and transactional rollback remain.
- Worker finding IDs now include Branch identity before anchor resolution. Previously same title/fact/source in later work could replace the parent's finding in the latest aggregate. Historical IDs are not migrated; new anchor and dependency bindings use scoped IDs.
- Pause/stop discards late additions. Interrupted reviews are discarded at setup, never automatically replayed. Review failure preserves results but remains blocked.

## 验证与边界

[Evidence](../evidence/DR-0096-SINGLE-AGENT-DELEGATION-20261026.md): 150 backend checks, 16 browser/projection checks and TypeScript checking. Three real-provider tasks used10 calls: two single-Agent tasks and one two-Agent task; all reviews chose no addition. Real-provider single-to-team expansion remains unverified. Controlled tests cover one-to-two/three execution chains, parent preservation, source rejection, budgets, controls, manual isolation and checkpoint non-replay.

This is a single-plan-unit readonly slice, not arbitrary mid-analysis upgrades, role replacement, recursive teams, a capability marketplace or general model-owned tool loop. Multi-unit conservative/fixed routes do not gain promotion. Skills progressive loading and external SDK adapter remain planned. No PostgreSQL rerun or user study. Same model in separate contexts does not establish independent judgment or quality gains.
