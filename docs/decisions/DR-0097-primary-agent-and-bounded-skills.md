# DR-0097: Primary Agent and Bounded Skills

Date: 2026-10-26. Status: Limited Verified for the implementation and fixed examples below. No new commit/PR.

## 场景与来源

[User source](../sources/USER-FEEDBACK-20261026-primary-design-alignment.md), [SCENARIO-084](../scenarios/SCENARIO-084-primary-agent-multiple-items.md). The accepted design was primary execution, progressive skills, necessary delegation and existing evidence/permission controls. DR-0096 did not change the initial two-independent-units-to-workers admission rule. The onboarding/recruitment example exposed this gap.

## 前台交互影响

The existing unified Task graph shows one primary executor when single_controller has no Worker ledger. Multiple business Branches remain distinct, not renamed into Agents. Task/result details and selected method names remain folded. No new workspace, no new approval click, no fabricated calls. Historical Worker graphs stay unchanged. Real errors, incomplete work, evidence and controls remain available.

## 后端事实映射

- Add optional typed `execution_approach` and bounded `skill_ids` to candidate, compiled and public Plan. Strategy has mode primary/delegate, business reason, and benefit none/parallel_depth/context_isolation/review_separation. It is a model recommendation, not a calibrated utility score.
- Built-in provider Planner receives skill metadata only and is instructed to separate business decomposition from delegation. If it omits a strategy, the provider adapter defaults to primary. Existing persisted Plans and custom legacy planners with no strategy retain their historical admission semantics; manual admission is unchanged.
- In automatic_readonly admission, an explicit primary proposal or a delegate proposal with benefit=none keeps multiple work items on single_controller. Risk/human gates precede this selection. A delegate proposal must still pass existing source structure, independence, budget and time checks. No model can grant execution authority.
- Primary multi-unit plans use the existing normal Analyst path once per round, preserving all units, requirement accounting, Branch evidence gates and results. No collapsing of numbered requirements into one unit. Planning and analysis remain separate model calls, not an uninterrupted conversational model process.
- Three server-authored methods are allowlisted: source_extract, rule_compare, table_reconcile. Planning sees short descriptions; only selected method bodies enter the built-in Analyst payload. Selection is task-level and shared with scoped Workers. Methods are prompt instructions, not code tools, file-source evidence, installed third-party skills or permission grants. Unknown IDs fail schema validation. Public output contains IDs and sanitized strategy reason, not procedure bodies.
- Existing bounded single-unit post-result delegation and team-wave reviews remain. **Multi-unit primary analysis does not yet enter that post-result review path.** This increment does not implement the full general primary-Agent tool/delegation loop.

## 验证与边界

[Evidence](../evidence/DR-0097-PRIMARY-DESIGN-20261026.md): 154 backend tests, 18 browser/projection checks, type checking, four real-provider tasks. Three simple tasks completed, including the unchanged onboarding/recruitment instruction with two Branches, one analysis call and two adopted findings. A broader risk brief was blocked by a human-gate plan before analysis; it is not a successful showcase.

No new framework dependency, direct-tool routing, general skills marketplace, recursive teams, optimal team-size claim, semantic coverage proof or user study. No PostgreSQL rerun. Real-provider dynamic expansion remains unverified. Prior documents and old runs retain their historical facts.
