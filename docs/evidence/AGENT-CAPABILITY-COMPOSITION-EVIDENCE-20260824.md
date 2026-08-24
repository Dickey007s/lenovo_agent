# Agent capability composition contract evidence

| Field | Value |
| --- | --- |
| Evidence ID | `AGENT-CAPABILITY-COMPOSITION-EVIDENCE-20260824` |
| Date | 2026-08-24 |
| Decision | [DR-0019](../decisions/DR-0019-capability-composed-agent-runtime.md) |
| Source | [USER-FEEDBACK-20260824-CAPABILITY-COMPOSITION-11](../sources/USER-FEEDBACK-20260824-11-generic-capability-composition.md) |
| Status | `Limited Verified` for the strict generic Scenario/Planner contract only |
| Implementation | [`eef656e`](https://github.com/Dickey007s/lenovo_agent/commit/eef656e), delivered in open [PR #25](https://github.com/Dickey007s/lenovo_agent/pull/25) |

## 1. Claim under test

The current Agent Harness must not branch on presentation identities such as `demo1`, `demo2` or `demo3`. Public, internal and Planner Scenario projections must use one strict capability-composition contract:

```text
work_profile.task_topology
work_profile.orchestration
work_profile.control_requirements
work_profile.current_runtime_scope
```

Demo 1/2/3 remain reporting and acceptance lenses. They do not create capabilities.

## 2. Implemented facts

- `BenchmarkWorkProfile` restricts topology to `single_task|multi_task`, orchestration to `bounded_loop|adaptive_swarm`, controls to `evidence_gate|human_gate|risk_gate`, and the current scope to `read_only_analysis`.
- duplicate control requirements fail validation.
- the fail-closed FORTE Catalog maps each pinned Scenario to a generic profile.
- public, internal and Planner projections no longer contain `demo_id` or `experience_policy`.
- the frontend requires and validates `work_profile`; its Scenario type no longer has a Demo field.
- the API leak regression explicitly rejects serialized `demo_id` and `experience_policy`.

## 3. Observed local API

After restarting the current API from this branch, `GET /v1/harness/scenarios` returned three Scenarios and contained neither legacy field:

| Scenario | Topology | Orchestration | Controls | Current scope |
| --- | --- | --- | --- | --- |
| `Finance-018` | `single_task` | `bounded_loop` | `evidence_gate,human_gate` | `read_only_analysis` |
| `pm-014` | `multi_task` | `adaptive_swarm` | `evidence_gate,human_gate` | `read_only_analysis` |
| `Operations-008` | `single_task` | `bounded_loop` | `evidence_gate,human_gate,risk_gate` | `read_only_analysis` |

This observation verifies contract projection, not execution of those target policies.

## 4. Automated verification

| Check | Result |
| --- | --- |
| Catalog + Runtime focused Python | `30 passed in 2.56s` |
| Full Python | `53 passed in 2.51s` |
| Ruff | passed |
| TypeScript lint | passed |
| Next.js production build | passed; compile `5.9s`, TypeScript `4.6s`, static generation `677ms` |
| Harness browser E2E | `8 passed in 52.5s` |
| `git diff --check` | passed; Windows line-ending notices only |

The browser suite uses the strict new `work_profile` fixtures. If the frontend still required a Demo ID, the Catalog load and all main workbench paths would fail.

## 5. Frontend/server mapping

| Frontend rule | Server fact | Hidden/blocked inference |
| --- | --- | --- |
| business collections remain the primary navigation | Scenario list and safe file projection | no Demo mode switch |
| future processing-mode receipt uses `work_profile` | Catalog today; future Admission Snapshot later | profile is not proof of execution |
| current UI remains read-only | `current_runtime_scope=read_only_analysis`, existing Run events/result | no loop/swarm animation, Worker fiction or action claim |

## 6. Boundary and next gate

This Evidence proves only the removal of Demo-specific identity from the current contract and the validity of three generic profiles. The Catalog still fixes each acceptance profile; the Agent does not yet dynamically classify arbitrary tasks.

It does not prove a single-task bounded executor, branch pause/resume, adaptive multi-task scheduling, Worker self-organization, shared Artifact convergence, durable checkpoints, Risk Gate execution, Connector access or user value. Those remain `Draft` until they emit corresponding Snapshots/events/Artifacts and pass dedicated acceptance scenarios.
