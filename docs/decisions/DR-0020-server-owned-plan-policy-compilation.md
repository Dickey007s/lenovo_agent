# DR-0020: Server-owned plan policy compilation

| Field | Value |
| --- | --- |
| Decision ID | `DR-0020` |
| Date | 2026-08-25 |
| Status | `Limited Verified` in the current FORTE read-only Harness |
| Trigger | `USER-FEEDBACK-20260825-PLAN-POLICY-12` |
| Scenarios | [SCENARIO-004](../scenarios/SCENARIO-004-forte-finance-durable-evidence.md), [SCENARIO-005](../scenarios/SCENARIO-005-forte-release-adaptive-team.md), [SCENARIO-006](../scenarios/SCENARIO-006-forte-governed-operations-action.md), [SCENARIO-007](../scenarios/SCENARIO-007-single-forte-worksite-entry.md) |
| Source | [Stakeholder feedback and screenshot](../sources/USER-FEEDBACK-20260825-12-plan-policy-and-readable-failure.md) |
| Evidence | [Plan policy compiler recovery evidence](../evidence/PLAN-POLICY-COMPILER-RECOVERY-EVIDENCE-20260825.md) |
| Implementation | [`373b79a`](https://github.com/Dickey007s/lenovo_agent/commit/373b79a) |
| Delivery | [PR #25](https://github.com/Dickey007s/lenovo_agent/pull/25), open and not yet merged |

## 1. Problem

The Planner was asked to generate server-internal `side_effect` values. A valid business plan could therefore be rejected because the model omitted or mismatched an internal enum. The failure was then projected verbatim to the business UI as `artifact.write 必须映射为 run_workspace_write`, while the call receipt said only “未采用”. The user could neither understand the failure nor tell whether the model had actually run.

This was an ownership error, not merely a copy problem. Source scope, operation scope, write boundary and human-gate requirements are policy facts and cannot be delegated to model prose.

## 2. Decision

The model now returns a restricted plan candidate containing business intent, dependencies, selected file refs and an allowlisted tool intent. It does not return `side_effect`.

The server compiles the candidate before validation:

| Model intent | Server-owned compiled fact |
| --- | --- |
| `artifact.write` | `side_effect=run_workspace_write`; safe logical artifact defaults are supplied when absent |
| `action.preview` | `side_effect=external_action`; `requires_human_gate=true` |
| read/inspect/verify intent | `side_effect=none`; incompatible artifact metadata is removed |

The existing validator remains defense in depth for source membership, allowlisted tools, unit identity, dependencies/cycles, safe artifact naming and gate/effect consistency. Compilation does not execute a tool or create an ArtifactVersion.

## 3. Frontend impact

- planning receipts say `未调用`, `已采用` or `校验未通过`;
- `校验未通过` means the provider returned a candidate but the server did not accept it;
- ordinary failures use business recovery text and do not expose raw tool/effect identifiers;
- an active run disables the command as `Agent 处理中`;
- a known failed terminal offers `重新规划` with a fresh idempotency key;
- a known completed terminal offers `再次运行` with a fresh key;
- only an unknown start outcome retries with the original key.

Prompt, chain of thought, provider payload, raw candidate, internal enum and stack trace remain hidden.

## 4. Backend fact mapping

| Frontend fact | Server fact |
| --- | --- |
| 规划调用中/已返回 | `planning_started` / `planning_completed` |
| 已采用 | `model_receipt.called=true` and `output_used=true` |
| 校验未通过 | `model_receipt.called=true` and `output_used=false` plus failed Snapshot |
| 安全停止 | `status=failed`, `harness_failed`, safe public `validation_errors[]` |
| 已校验工作图 | compiled `HarnessPlan` passed deterministic validation and `plan_validation` was emitted |

Raw validation details remain available to internal logs/tests but are not part of the public failure projection.

## 5. Validation and evidence

The implementation is covered by compiler, validator, public-projection and browser retry tests. A final live browser run used `deepseek-v4-pro`, adopted both Planner and Analyst outputs, reached `completed` v9/seq 8 and rendered no raw `artifact.write` or `run_workspace_write` string. Exact identifiers, timings, screenshot hashes and command results are in the linked Evidence.

## 6. Boundary

This is `Limited Verified` only for the fixed FORTE read-only Harness in one memory API process. It proves policy ownership, fail-closed compilation, readable projection and the tested retry semantics. It does not prove plan quality, semantic/numeric correctness, durable recovery, Scheduler/Worker execution, Tool Gateway invocation, Artifact mutation, Connector action, production identity or user comprehension.

## 7. Relationship to DR-0019

DR-0019 remains the generic capability-composition decision. DR-0020 refines module 4: Admission and plan validation now include a server-owned policy compiler between the model candidate and the validator. Demo identity still does not select capabilities.
