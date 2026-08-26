# Decision and Reporting Governance

This is the hard gate for every design, implementation item, PR, Demo and report. A claim is not complete unless it covers 场景与来源、前台交互影响、后端事实映射、验证与边界.

## 1. Claim states

| State | Meaning |
| --- | --- |
| `Draft` | an idea, target, hypothesis or implementation without all gates |
| `Ready` | design contract is complete enough to implement; runtime evidence is not implied |
| `Limited Verified` | evidence supports the claim only inside an explicit fixed scope |
| `Verified` | all stated acceptance gates passed for the stated scope; production or user value is not implied unless tested |
| `Rejected` | a considered path is intentionally not pursued, with reason |
| `Retired` | historical evidence remains valid for its recorded commit but no longer describes the current product |

Never use “completed” as a substitute for one of these states.

## 2. Required decision record

Every Decision Record must contain:

### 场景与来源

- Source ID and exact traceable location;
- source category: stakeholder feedback, user research, official product material, literature, repository/code, runtime evidence, or hypothesis;
- date, version or commit;
- what judgment it supports;
- what it cannot support.

Official product documentation is not competitor hands-on testing. E2E is not user research. A single stakeholder comment is not representative user evidence.

### 前台交互影响

- what the user sees before, during and after the state change;
- which action the user can take;
- waiting, error, retry and recovery behavior;
- internal details deliberately hidden;
- wording that separates preview, request, recorded selection, validated plan, execution and receipt.

### 后端事实映射

- authoritative Snapshot, field or ordered event for every UI state;
- transition and terminal semantics;
- version, sequence, Owner and idempotency rules;
- source and policy ownership;
- fail-closed behavior when a fact is missing or contradictory.

### 验证与边界

- test/run/screenshot/user-study evidence with exact identifier and result;
- implementation commit, documentation commit when available, and PR state;
- fixed scope and known untested paths;
- prohibited inference.

If any section is missing, status must remain `Draft`.

## 3. Scenario record

Every Scenario must state:

| Field | Required content |
| --- | --- |
| target user | role and responsibility |
| trigger | the concrete business moment |
| current pain | present workflow or failure |
| goal | desired business outcome |
| completion condition | observable success |
| happy path | ordered user/Agent interaction |
| exception path | missing source, conflict, offline, denial, stale version or unknown outcome |
| source | Source IDs and limitations |
| frontend impact | visible state/action/recovery/hidden detail |
| backend facts | Snapshot/field/event/version/Owner/idempotency |
| evidence status | Draft/Ready/Limited Verified/Verified with boundary |

An abstract capability name is not a Scenario.

Demo names are acceptance/reporting lenses, not runtime feature flags. A Demo may bind a concrete Scenario to a generic task topology, orchestration policy and control requirements, but it must not introduce private capabilities that are unavailable to user-authored tasks. Every Demo report must state which generic modules were exercised and which target capabilities remain Draft.

## 4. 来源台账

`docs/decisions/SOURCE_REGISTER.md` is the canonical 来源台账. New sources are append-only and use stable IDs. Preserve stakeholder wording verbatim where authorized, distinguish a screenshot's visible content from interpretation, and record file hash/size when the local asset is evidence.

Never rewrite an old source to fit a later design. Add a new Source and link supersession or retirement instead.

## 5. UI—服务端事实映射

`docs/contracts/UI_SERVER_FACT_MATRIX.md` is the canonical UI—服务端事实映射. Each row must include:

- UI location and exact user-facing meaning;
- 服务端权威字段 or ordered event;
- allowed user action;
- transition/recovery semantics;
- 默认隐藏 internal data;
- verification and current lifecycle.

The frontend must not infer completion, model call, Artifact mutation, risk, approval, Permit, tool success or external effect from animation, elapsed time, prose or configured model name.

Model-generated tool names, write scopes, effect classes and gate requirements are proposals, not authority. A server-owned compiler/validator must produce those policy facts before they can appear in a public Snapshot; ordinary UI and reports must use business projections rather than raw protocol identifiers.

For model-generated results, a citation that belongs to the selected source set proves only reference membership unless a separate semantic/numeric verifier exists. Reports must not rename citation-scope validation as factual correctness. `completed` must be qualified by the concrete completed scope, such as “read-only analysis result available for review”.

A user-facing Finding must not end at “Agent says there is a problem”. The living
fact matrix must record its source location, whether human judgment is required,
what each visible choice causes, how feedback enters a new command and what does
not happen. Recoverable model location/structure failures must preserve valid
work and expose a next action; security-scope and integrity violations remain
fail closed. Any recommendation is model-proposed context, not approval evidence.
An accept/decline/defer interaction counts as implemented only when the server
returns a versioned, idempotent DecisionRecord bound to the current Finding or
EvidenceResolution. A client-only selected radio button or toast is a Draft.

## 6. Evidence hierarchy

| Evidence | Supports | Does not automatically support |
| --- | --- | --- |
| source hash/manifest check | exact fixed source bytes | data realism or usefulness |
| unit/integration test | code contract on tested path | visual quality or production reliability |
| browser E2E | tested UI workflow and DOM assertions | comprehension, trust or adoption |
| screenshot review | visible state at one viewport/time | backend truth or task success |
| live model run | that configured call and observed response path | model quality, repeatability, SLA or cost savings |
| fresh-clone verification | remote branch reproducibility at fixed HEAD | merge status |
| target-user study | measured task/user outcome for its protocol | broader population without study design |

Negative results and incidents must remain in Evidence. A repair does not erase the pre-fix observation.

## 7. Lifecycle and retirement

Historical Evidence retains its original numbers and scope. When a product surface is removed:

1. create a Decision explaining replacement and retained principles;
2. add it to `RETIREMENT_REGISTER.md`;
3. update living docs so old facts are not current;
4. keep Source, Evidence, screenshots and Git history;
5. never reuse a retired run as evidence for a new Scenario.

A centralized retirement register is sufficient; mass-editing every historical Evidence file is optional and should be avoided when it adds churn without clarity.

## 8. PR and report checklist

Before delivery, verify:

- Decision and Scenario link exact Source IDs;
- UI—服务端事实映射 matches current code;
- implementation commit and PR URL/state are recorded;
- automatic test numbers are exact and dated;
- screenshots are identified as current, transitional or negative;
- Draft future states are not written as implemented;
- production identity, durable recovery, real Connector and user research are not inferred;
- living docs and retirement lifecycle are synchronized;
- governance test, Markdown link check and `git diff --check` pass.

The current FORTE product application of this policy is [DR-0018](decisions/DR-0018-forte-data-workbench-and-verifiable-trace.md). The generic capability-composition rule is [DR-0019](decisions/DR-0019-capability-composed-agent-runtime.md). DR-0016/0017 remain historical foundations with their original evidence scope.
