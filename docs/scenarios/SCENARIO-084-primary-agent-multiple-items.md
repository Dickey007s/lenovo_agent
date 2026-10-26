# SCENARIO-084: Multiple Work Items, One Primary Executor

Source: [user feedback](../sources/USER-FEEDBACK-20261026-primary-design-alignment.md). Contract: [DR-0097](../decisions/DR-0097-primary-agent-and-bounded-skills.md).

1. Submit the existing onboarding/recruitment checklist goal in Demo2, without specifying Agent count.
2. Preserve the software and job-requirement business work items and their approved sources.
3. Planner may choose primary processing with a short reason and selected method. Two work items must not automatically mean two Agents.
4. Existing scope/permission/budget gates still apply. If delegated, a proposal is not permission and does not bypass those gates.
5. One primary analysis may return findings for both units; both Branch evidence gates must pass independently. Empty or rejected results must not produce a green executor.
6. The graph shows one primary executor and the actual two work items. Method and reason disclosure must not start a new call. Desktop/mobile must not overflow.
7. Existing single-unit and team review tests continue to pass. Multi-unit primary post-result expansion remains explicitly outside this increment.

Evidence: [DR-0097 evidence](../evidence/DR-0097-PRIMARY-DESIGN-20261026.md).
