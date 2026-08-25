# DR-0019: Capability-composed Agent runtime

| Field | Value |
| --- | --- |
| Decision ID | `DR-0019` |
| Date | 2026-08-24 |
| Status | generic capability principle carried forward; the recorded public `work_profile` projection is historical; bounded execution, adaptive swarm and governed action remain `Draft` |
| Trigger | `USER-FEEDBACK-20260824-CAPABILITY-COMPOSITION-11` |
| Scenarios | [SCENARIO-004](../scenarios/SCENARIO-004-forte-finance-durable-evidence.md), [SCENARIO-005](../scenarios/SCENARIO-005-forte-release-adaptive-team.md), [SCENARIO-006](../scenarios/SCENARIO-006-forte-governed-operations-action.md) |
| Source | [Stakeholder clarification](../sources/USER-FEEDBACK-20260824-11-generic-capability-composition.md) and the historical [Demo architecture reference](../evidence/assets/user-feedback-20260824-generic-capability-composition.png) |
| Evidence | [Capability profile migration evidence](../evidence/AGENT-CAPABILITY-COMPOSITION-EVIDENCE-20260824.md) |
| Implementation | [`eef656e`](https://github.com/Dickey007s/lenovo_agent/commit/eef656e) |
| Delivery | [PR #25](https://github.com/Dickey007s/lenovo_agent/pull/25), open and not yet merged |

## 1. Problem

The data-first workbench already removed Demo navigation from the foreground, but the public Scenario, internal Catalog and Planner policy still carried `demo_id` and `experience_policy`. That made the architecture say that a capability belongs to a presentation mode. It also made a future runtime likely to branch on “Demo 1/2/3” instead of choosing reusable mechanisms from the task.

Current applicability note: `DR-0022` removes the public Scenario/profile
projection entirely and keeps Demo identities out of the product surface. The
principle that one Runtime composes reusable capabilities remains active; the
target topology executors are still not implemented.

## 2. Decision

Demos are acceptance lenses, not runtime identities. The Agent owns a common capability set and composes a work policy from three dimensions:

```text
task_topology: single_task | multi_task
orchestration: bounded_loop | adaptive_swarm
control_requirements: evidence_gate | human_gate | risk_gate
```

The current public/internal/Planner Scenario contract uses `work_profile` and no longer contains `demo_id` or `experience_policy`. `current_runtime_scope=read_only_analysis` remains explicit so a target profile cannot be mistaken for executed behavior.

The acceptance compositions are:

| Acceptance lens | Generic composition | Intended behavior |
| --- | --- | --- |
| Demo 1 | `single_task + bounded_loop + evidence_gate + human_gate` | decompose one task, advance through checkpoints, pause when evidence is insufficient or a human judgment is required, then resume and commit |
| Demo 2 | `multi_task + adaptive_swarm + evidence_gate + human_gate` | admit multiple work units, schedule parallelizable work, add or cancel units when facts change, and converge through shared artifacts |
| Demo 3 | `risk_gate` applied to either topology | preview business impact and require deterministic policy/evidence/approval/permit before a side effect; it is not a separate orchestration engine |

## 3. Runtime architecture

```text
Workspace sources + user instruction
  -> Task Contract
  -> Admission selects topology, orchestration and gates
  -> generic Decomposer / Planner
  -> bounded Loop or adaptive Scheduler / Workers
  -> shared Artifact + Verifier
  -> Evidence / Human / Risk controls
  -> Commit and, only when permitted, Tool Gateway action
```

Capabilities are registered independently of benchmark scenarios. A Scenario may provide a recommended acceptance profile and a restricted tool/source policy, but it does not create the underlying capability. The same bounded loop, swarm scheduler and risk gate must be callable for new office folders and user-authored tasks once their runtime slices exist.

## 4. Frontend impact

The foreground remains work-led:

- the user starts from files and an instruction, not a Demo selector;
- the server-selected processing mode should appear as a small “本轮如何处理” receipt only after Admission;
- a single-task view should show decomposition, the active checkpoint and the precise pause reason instead of dumping the final conflict;
- a multi-task view should show real work units, dependencies, additions/cancellations and artifact convergence instead of Worker chat;
- risk control should appear contextually only when an action is proposed;
- Prompt, chain of thought, raw Worker conversations and internal IDs remain hidden.

The current UI does not yet render a server Admission receipt because the current Runtime stops at read-only planning/analysis. It must not animate a bounded loop or swarm as if those engines ran.

## 5. Backend fact mapping

| Contract fact | Current source | Current boundary |
| --- | --- | --- |
| `work_profile.task_topology` | fail-closed Catalog projection | fixed per three pinned FORTE acceptance scenarios; dynamic Admission is not implemented |
| `work_profile.orchestration` | fail-closed Catalog projection | target organization policy only |
| `work_profile.control_requirements` | fail-closed Catalog projection | target gates; current read-only path only enforces source, plan and citation checks |
| `work_profile.current_runtime_scope` | strict public contract | always `read_only_analysis` in the current Runtime |
| actual plan/result/events | `HarnessRun` Snapshot and ordered SSE | two model calls and deterministic structural/reference validation only |

The removal of Demo identity from the contract is an implemented compatibility break. Actual task-policy classification, bounded executor, adaptive Scheduler/Workers, durable checkpoints, Artifact Commit and governed external action remain `Draft`.

## 6. Validation and claim boundary

The Evidence records contract tests, public-payload leak checks, frontend parsing and full verification. This proves that current code no longer requires or returns Demo identities and that each pinned Scenario has a valid generic profile.

It does not prove that the current Agent can yet execute Demo 1 or Demo 2 semantics. It also does not prove task classification quality, dynamic self-organization, durable recovery, external action safety or user value.

The later [DR-0020](DR-0020-server-owned-plan-policy-compilation.md) refines the current module-4 implementation: the model proposes operation intent while a server-owned compiler assigns effect/write/gate policy before deterministic validation. This does not change the Draft status of bounded execution, adaptive swarm or governed action.

## 7. Rejected alternatives

- **Keep `demo_id` internal only**: rejected because internal coupling still shapes Planner and future runtime branches.
- **Build three independent runtimes**: rejected because it duplicates state, scheduling and control semantics and prevents generalization to user-authored tasks.
- **Show target orchestration immediately in the UI**: rejected because a policy label is not evidence that the executor ran.
- **Treat Demo 3 as a third scheduler**: rejected because risk/action control must apply consistently to both single-task and multi-task work.
