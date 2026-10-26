# DR-0098: Demo3 Ready Boundary Examples

Date: 2026-10-26. Status: Limited Verified within the fixed-rule demonstration scope. Local worktree, no commit or PR.

## 场景与来源

[User feedback](../sources/USER-FEEDBACK-20261026-demo3-more-examples.md): the presenter needs more than two or three prepared Demo3 cases, covering different human-agent boundaries. The existing handbook R01-R16 guides the catalog; these are synthetic demonstration materials, not user research or enterprise records. Scenario: [SCENARIO-085](../scenarios/SCENARIO-085-demo3-prepared-boundary-examples.md).

## 前台交互影响

The original OfficeActionWorkbench draft gains a closed disclosure with twelve examples in four native select groups. Selection replaces only draft input. Users can edit it and explicitly start through the existing button. There is no auto-submit, prechecked confirmation, preselected material decision or second product entry point. Selecting another example fully replaces fields, avoiding stale alternative_content/source_ref/format_style. The picker is absent for an existing action, including an incomplete or deferred one; those use the original revise, defer, cancel and history controls. Busy, blocked and unknown-result states retain the existing fieldset/navigation locks.

Examples cover reversible text, revocable formatting preference, draft revision, quoted instructions, ambiguous contact, absent deadline, ordinary confirmation, strong confirmation, version recheck, restricted commitment, material judgment and deferred judgment. Short boundary labels are draft context only; result states always come from the server.

## 后端事实映射

No backend, protocol, permission, model or policy change. The JSON catalog is browser input data plus presenter/test metadata. Only `input` enters the existing POST /runs `action`; expected_status, steps and principle IDs are not submitted. OfficeAction.status, required_checks, missing_fields, source_excerpt, revision, history, decision and receipt remain authoritative. All cases have source_ref=null and synthetic pasted content. These are not newly imported workspace files.

The restricted message exercises the current exact-term deny rule. The quoted instruction case exercises only non-executing deterministic excerpt preparation. Neither establishes general semantic risk classification or model injection defense. Preference changes are optional and never auto-saved by choosing a preset.

## 验证与边界

[Evidence](../evidence/DR-0098-DEMO3-EXAMPLES-20261026.md): twelve real API browser starts with boundary-specific interactions, existing action/principle regressions, unit policy checks, type checks and desktop/mobile inspection. No real email, enterprise task, approval, model calls, production identity or user-study claim. Preview is isolated in-memory, with model access disabled. Source materials and previous reports are unchanged.
