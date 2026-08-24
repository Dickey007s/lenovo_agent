# DR-0016: Public workspace driven Agent Harness

| Field | Value |
| --- | --- |
| Decision ID | `DR-0016` |
| Status | Data import `Verified` in a bounded scope; catalog/planning/frontend vertical slice `Limited Verified`; execution migration remains `Draft` |
| Owner | Office Agent project team |
| Trigger | `USER-FEEDBACK-20260824-WORKSPACE-HARNESS-08` |
| Source dataset | Public FORTE repository pinned at `345c1ec1487139db9dd319787fa9405ba85d1869`, top-level MIT; 11 original imported files and `115352` bytes are fixed by the local manifest |
| Evidence | [`FORTE-WORKSPACE-AGENT-HARNESS-EVIDENCE-20260824`](../evidence/FORTE-WORKSPACE-AGENT-HARNESS-EVIDENCE-20260824.md), `Limited Verified`; live manifest [`dr-0016-harness-live-runs.json`](../evidence/manifests/dr-0016-harness-live-runs.json); implementation [`fdcc3d819686b0d0afd99fcd0b637b5329607835`](https://github.com/Dickey007s/lenovo_agent/commit/fdcc3d819686b0d0afd99fcd0b637b5329607835); [PR #23](https://github.com/Dickey007s/lenovo_agent/pull/23), merged to `master` by `0001a85533409150b1da735263fc1c9e389d8539` |

## 1. Problem

The existing demonstrations use different fixed services, fixed task identities, and scenario-specific values. Although the backend now records real model calls and ordered facts in several paths, the user still experiences a scripted product: the files do not feel like a coherent workspace, the work graph appears predetermined, and the frontend presents the result of orchestration more strongly than the Harness that produced it.

The redesign must make three things visible without exposing internal reasoning: which source files were available, how the Harness turned the task into a validated work graph, and which model/tool/control facts actually changed the run.

## 2. Decision

Adopt a single `Scenario Pack -> Harness Run -> Frontend Projection` architecture. The three demos become three execution policies over the same runtime contract, not three unrelated products.

```text
Public Scenario Pack
  -> read-only Workspace Snapshot
  -> Task Contract
  -> model-generated Plan DAG
  -> deterministic Admission
  -> Scheduler / Workers / Tools
  -> Shared Artifacts + Verifier
  -> Checkpoints + Ordered Events
  -> Governance / Human Control
  -> Commit or Execution Receipt
```

The first implementation vertical slice ends at `HarnessRun.status=ready_to_execute` and must say `计划已通过服务端校验，尚未执行任务`. It has no execution command and cannot claim that a tool ran, an Artifact was written, the source task or any of the three demos completed, or an external action occurred.

### 2.1 Source and planner privacy boundary

The imported files preserve the upstream bytes. The three raw `task.md` files remain in the repository only as provenance records; they are not workspace files and are not public scenario fields. The Catalog extracts only the text between `## Prompt` and `## Grading Criteria`, rejects benchmark metadata markers, and gives the resulting sanitized task text only to the internal Planner context.

The public scenario REST response and ordinary UI must not contain raw `task.md`, `task_instruction`, `solution`, `rubric`, grading criteria, absolute paths, full hashes or benchmark-internal identifiers. This is a release gate, not a cosmetic hiding rule: a server response that contains those values fails this vertical slice even if the frontend does not render them.

## 3. Eight resident Harness modules

| Module | Backend responsibility | User-visible projection |
| --- | --- | --- |
| Scenario Pack & Workspace Catalog | Verify provenance manifest, file allowlist, hashes, size, links and supported parsers; freeze a workspace snapshot | Real file tree, public-benchmark label, readable file metadata and cited sheet/section |
| Task Contract | Bind the sanitized internal task instruction, expected outputs, budget, deadline, allowed capabilities and data boundary | Public goal, deliverables and what the Agent may access; never raw task text or benchmark grading fields |
| Planner | Use the configured model to generate a bounded DAG from the sanitized task and workspace index | Gradually appearing work graph and model-call receipt, not Prompt, benchmark instruction or chain of thought |
| Admission & Plan Validator | Validate paths, tools, dependencies, cycle-free graph, budget and human-gate requirements | Why a unit is allowed, blocked, or needs the user; no hidden score theater |
| Scheduler & Worker Manager | Run ready units according to the selected execution policy and record assignment/replan facts | Active units, dependencies, waiting reason, dynamic additions and actual elapsed time |
| Tool Gateway | Execute only registered read/write/simulation capabilities against the run workspace | File/tool call receipt, affected object and result status; no raw payload or credential |
| Artifact Workspace & Verifier | Version outputs, bind citations/digests, run deterministic and model-bounded checks, detect conflicts | Current artifact, source trail, verification result, conflict and what must be decided |
| Checkpoint, Event & Governance Control | Persist versioned snapshots/events; implement pause, steer, branch, approval, Permit and receipt semantics | Recovery state, human decisions, four-part impact ledger and what did or did not happen |

The eight names in this table are canonical for the unified Harness. Earlier maturity tables using `Durable Task State / Context State Manager / Execution Loop / Capability Runtime / Evidence & Quality Verifier / Control Policy / Trace & Checkpoints` are mapped into these eight ownership boundaries and must not be presented as a second resident-module list.

## 4. Three demo policies

### Demo 1: durable evidence task

- Scenario Pack: FORTE `Finance-018`.
- Policy: `durable_task`.
- User goal: derive unpaid/uncollected summaries and identify persistent balances from three period workbooks.
- Harness emphasis: incremental Observe/Plan/Execute/Verify checkpoints, evidence citations, resumable units, branch only when an ambiguous mapping or conflicting ledger fact is found.
- Frontend: file shelf + progressive task journey + evidence-linked output table + decision tray only when the server records a conflict.
- Boundary: no fixed 2400/2680 conflict; no source row or conflict may be invented by the UI or model.

### Demo 2: adaptive collaboration

- Scenario Pack: FORTE `pm-014`.
- Policy: `adaptive_team`.
- User goal: determine release readiness from PRD, configuration, functional tests and compatibility tests.
- Harness emphasis: model-generated DAG, deterministic Admission, parallel ready units, shared artifact versions, dependency-aware reconciliation, dynamic worker addition only when a new server fact requires it.
- Frontend: workload map, worker-to-file assignment, shared artifact convergence, actual model/tool receipts and a clear `no external action` completion boundary.
- Boundary: worker count and replan sequence are run facts, not constants copied from the former customer-A demo.

### Demo 3: governed action

- Scenario Pack: FORTE `Operations-008`.
- Policy: `governed_action`.
- User goal: design and review an AI-assisted collection-call process under explicit operational constraints.
- Harness emphasis: the model drafts process content and action candidates; deterministic Risk, Policy, Evidence, Approval, Permit and Tool Gateway decide whether a simulated action is allowed.
- Frontend: process artifact, policy citations, action-impact ledger, missing evidence, human gate and an execution receipt that explicitly says no real dial-out occurred.
- Boundary: the imported rules do not authorize production contact. All side effects remain Simulator-only.

## 5. Frontend information architecture

The default user-facing name is `工作现场`, not `Harness debugger`. The intended first screen is the work itself: source workspace on the left, progressive/dynamic plan in the center and service-owned receipts on the right. A technical Harness label may appear only as secondary context.

1. **Workspace shelf**: original files, type, public-source label, fingerprint summary and selected evidence location.
2. **Agent journey**: ordered stages appear only after the matching Snapshot/event; the page never opens directly at Verify unless the recovered run is actually there.
3. **Dynamic work graph**: units, dependencies, source files, allowed capability and human-gate status come from the validated plan.
4. **Live activity rail**: model call started/completed, elapsed time, tool call and verification receipts. It shows results, not Prompt, chain of thought or Worker conversation.
5. **Artifact desk**: versioned outputs and citations; a user can pin history or follow the current head.
6. **Decision and impact tray**: why the user is needed, what confirmation will change/recheck/preserve/not do, and the post-command receipt.
7. **Recovery state**: reconnecting, last confirmed version, result unknown, retry with the same idempotency key, and explicit process-restart limits.

## 6. Server facts and states for the first vertical slice

| Frontend state | Authoritative fact | Event/response | Allowed action | Boundary |
| --- | --- | --- | --- | --- |
| Scenario available | safe public scenario projection | `GET /v1/harness/scenarios` | Open workspace | Catalog success does not mean a run exists; response must not contain `task_instruction`, rubric or solution |
| Files indexed | frozen `HarnessRunSnapshot.source_documents[]` | run Snapshot + `workspace_index` | Inspect file metadata | File content is read-only; absolute path hidden |
| Model planning | `HarnessRun.status=planning` + processing receipt | `planning_started` | Wait | Animation alone cannot claim a model call; cancel is not implemented |
| Model response returned | `HarnessModelReceipt.called=true/output_used=false` | `planning_completed` | Wait for validation | A completed model HTTP call is neither adoption nor validation |
| Plan ready | validated `HarnessPlan` + `HarnessModelReceipt.output_used=true` | `plan_validation` | Review plan | Output is adopted only after server validation passes; adoption does not prove business quality |
| Plan failed | typed error and retained workspace snapshot | `harness_failed` | Retry with a new command/key | No fallback plan may be labeled as model output |
| Ready to execute | `HarnessRun.status=ready_to_execute` | Snapshot/SSE | Execution command in a later slice | Must display `尚未执行`, not completed |

## 7. Validation gates

The first vertical slice is complete only when:

- imported bytes, license, manifest, SHA-256 and privacy scan are recorded;
- catalog rejects extra/missing/tampered/path-escape/symlink/unsupported files;
- two different valid model plans can be accepted without frontend code changes;
- invalid path, tool, dependency, cycle or human-gate output fails closed;
- idempotent start, owner isolation, monotonic Snapshot/event application and SSE reconnect are tested; terminal events close after one stream plus final GET, while non-terminal interruption resumes with `after=N`;
- desktop and 390px views show file identity, progressive stages, dynamic DAG and actual model receipt without horizontal overflow;
- the current product and report explicitly separate `ready_to_execute` from execution completion;
- public API/DOM leak checks reject `task_instruction`, rubric, solution and raw task content;
- model-call, model-output-adoption and server-validation facts are asserted independently;
- target-user comprehension remains unverified until a moderated or unmoderated study is run; E2E and screenshots are engineering proxies only.

## 8. Rejected alternatives

- **Rename the current fixtures**: rejected because it changes appearance without changing source truth.
- **Combine unrelated datasets into a synthetic customer folder**: rejected for the first slice because the user explicitly requested an existing dataset rather than a constructed scenario.
- **Expose raw model traces to prove the Agent is real**: rejected because Prompt/chain-of-thought/Worker conversation add risk and do not provide a trustworthy business receipt.
- **Migrate all three execution engines in one unverified change**: rejected. The shared catalog and dynamic planning contract land first; execution policies migrate behind explicit evidence gates.

## 9. Evidence status and limitations

The FORTE import and local integrity audit are `Verified` only for the pinned public revision, MIT license text, 11 original files, manifest/hash/path checks and read-only index. The unified catalog/planning/frontend vertical slice is `Limited Verified` only for the three fixed scenarios and current single-process runtime: the manifest binds three `deepseek-v4-pro` runs at v6/seq 5 `ready_to_execute`, API/DOM privacy assertions, six desktop/mobile screenshots and complete automation (`199 passed, 1 skipped`; browser `48 passed`; Ruff/lint/build passed). Implementation commit `fdcc3d819686b0d0afd99fcd0b637b5329607835`, first evidence-document commit `265ffb6f1e4f35416b0020deff9becee9a3a26a2`, and PR #23 merged by `0001a85533409150b1da735263fc1c9e389d8539` are bound. Demo 1/2/3 execution migration remains `Draft`.

FORTE is a public benchmark, not a production enterprise dataset. The first runtime is single-API-process memory and stops at `ready_to_execute`; it has no Scheduler/Worker execution, tool invocation, Artifact mutation, approval, Permit, Connector or external side effect. Model called, output adopted and server validation passed are separate facts. Automated tests and E2E do not prove target-user comprehension, trust, efficiency or task success.

DR-0017 now makes this architecture the sole current product surface and retires the former coexistence with legacy workspaces. The six screenshots bound to DR-0016 show that transitional surface; they remain valid historical engineering evidence but are not final-current UI screenshots. See [DR-0017](DR-0017-single-forte-worksite-and-legacy-retirement.md) and the [retirement register](RETIREMENT_REGISTER.md).

**Current applicability (2026-08-24):** DR-0018 extends this planning foundation with the seventh preview route, a second Analyst call, an eight-event path and a review-required read-only response. The DR-0016 six-path, v6/seq 5 `ready_to_execute`, run timings, screenshots and test numbers remain unchanged historical facts; use [DR-0018](DR-0018-forte-data-workbench-and-verifiable-trace.md) for current UI/API/terminal claims.
