# Office Agent target architecture

本文件描述目标架构，不是当前能力清单。当前实现边界以源码、API、Evidence
和下表 `Current` 列为准。
下文标为 target 或 not connected 的项目都是尚未完成的目标能力。历史 Demo
只在各自 Evidence 约束的提交范围内成立；现行 FORTE 工作区已能在隔离 Run
Workspace 中生成有限办公成果，但不修改 96 份源文件，也不挂载生产 Connector
或外部动作路由。

## 1. Product thesis

The Agent is general; Demo 1/2/3 are acceptance views over one capability
runtime. The product begins from an inspectable office workspace, not a hidden
Prompt or Demo switch. Users author a task and bounds, observe
server-backed execution facts and review outputs against sources. In the
current interaction, users choose the goal while the Agent chooses a bounded
evidence set from the complete safe workspace index.

Current implementation reaches a cited, bounded multi-round Controller,
server-owned task Branches, independent append-only logical result history and
twelve fixed artifact adapters. It also has a limited Demo 1/2 vertical: stable
Task lineage plus a minimal owner-scoped Task Ledger/current pointer across bounded
Runs, deterministic topology admission and at most
three in-process read-only Analyst Workers after explicit confirmation. Every
validated Worker Branch now also has a minimal durable WorkUnit record and each
return appends an immutable Contribution candidate in memory or PostgreSQL. Every
source-file mutation, distributed Worker/lease, multi-instance coordination and
Connector statement below is target design unless explicitly marked current.

## 2. Eight shared modules

| Module | Stable responsibility | Current | Target interaction impact |
| --- | --- | --- | --- |
| 1. Workspace Catalog & Safe Preview | file identity, integrity, safe projection and source policy | 15 folders/96 inputs, bounded preview | users inspect data before invocation and understand capability gaps |
| 2. Task Contract | goal, workspace scope, budget, deadline and completion criteria | instruction + whole-workspace refs + bounded rounds/files/calls/deadline + stable `task_id`, minimal current pointer, dual Task/Run versions and Run lineage | user states intent without doing retrieval first, can identify the current Run and continue one approved Branch without rewriting context |
| 3. Planner | retrieve evidence, propose work intent and dependencies | strict per-round Planner with autonomous evidence selection and one budgeted repair | users see what the Agent chose, why, and whether the plan was adopted |
| 4. Admission, Policy Compiler & Validator | choose topology, compile policy, validate graph/sources/gates | server compilation/plan checks plus deterministic `single_controller` / `fixed_workflow` / `adaptive_readonly_workers` admission | route explanation shows why work stays single, uses a fixed workflow or waits for Worker confirmation |
| 5. Scheduler & Worker Manager | bounded loop or adaptive workers, leases and replanning | one in-process bounded Controller plus an explicitly confirmed, process-local, maximum-three read-only Worker wave over ready Branches; full-DAG WorkUnits, pre-dispatch reservation and explicit checkpoint-recovered unit retry | live work map shows actual units, waiting and replanning without Worker chat |
| 6. Tool Gateway | capability registry, Permit, idempotency and execution receipts | not connected | proposed impact appears before confirmation; actual impact after receipt |
| 7. Artifact Workspace & Verifier | immutable versions, evidence, conflict and Commit | append-only logical evidence briefs/TaskCommits, fixed Run Workspace artifacts, citation/Anchor/Branch gates, immutable Contribution candidates, result restore and deterministic merge of adopted Worker contributions | users review versions and evidence instead of trusting final prose |
| 8. Checkpoint, Event & Governance Control | durable state, ordered events, risk/evidence/approval | ordered controls/events, per-Run monotonic streaming, minimal Task Ledger/current pointer, Branch-bound WorkUnit/Contribution ledger, Task/Run lineage, memory or PostgreSQL records and safe restart recovery | current/history, candidate/adoption state, concurrency conflicts, disconnect/restart recovery and human gates become explicit states |

## 3. Shared runtime composition

```text
Workspace Folder
  -> Task Contract
  -> Planner intent
  -> Admission + Policy Compiler + Plan Validator
  -> one of:
       bounded single-task loop
       adaptive multi-task scheduler/workers
  -> Artifact versions + deterministic/model verifiers
  -> cross-cutting Risk/Evidence/Human Gate
  -> Commit or governed Tool Gateway receipt
  -> durable Snapshot/Event stream
```

The current runtime validates a bounded Controller with Branch-selective resume,
append-only logical ArtifactVersion/TaskCommit records, fixed isolated artifact
adapters and optional PostgreSQL restart recovery. `DR-0053/54/55` add a limited
Demo 1/2 vertical: a terminal Run can create a same-Task child Run for exactly
one server-approved Branch, while a minimal owner-scoped Task record and
`task_version` choose one authoritative current Run; a validated plan receives deterministic topology
admission and, only after confirmation, may execute up to three in-process
read-only Workers whose adopted contributions merge into the normal Artifact
history. `DR-0055` persists the Branch DAG as WorkUnits, appends every return as
a Contribution, and supports no-auto-replay plus explicit target-only retry after
a Worker checkpoint recovery. It does not validate source-file writes, distributed Workers, leases or
multi-instance scheduling. Demo 3 validates the same cross-cutting action gate
for both future topologies. Capabilities are registered once; a Demo identity
never creates a special private executor.

## 4. Mainstream difference and user flow

Official OpenClaw material now includes durable Task Flow, revision conflicts,
bounded Swarm and provenance guidance in addition to Gateway/channel/session/tool
control; Codex foregrounds project threads, worktrees and review queues; Claude
Code foregrounds project-directory agent loops, tools, subagents and permissions.
Those are strong patterns and can be extended. This project's candidate
difference is therefore narrower: it deliberately binds an office repository,
Agent-selected evidence, Branch-scoped recheck, contribution adoption and
append-only office results in one server-owned contract. This is not an
exclusive-capability claim.

The resulting flow is:

```text
message/project first
  -> Agent discovers context and requests permissions as needed

current Office Agent
  -> browse files
  -> inspect safe content
  -> write a goal without preselecting files
  -> Agent searches the complete safe index
  -> observe selected evidence/call/adoption/validation/receipt
  -> reopen citations and review
  -> confirm one proposed follow-up or continue one unfinished Branch in a same-Task child Run
```

This is an implementation emphasis, not evidence of superior usability. The
full source comparison and limitations are retained in
[`WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825`](research/WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825.md).

## 5. Demo 1 target: bounded durable office loop

One user task is decomposed, then advances through observable checkpoints:

```text
contract -> observe -> plan -> act -> verify -> commit
```

When evidence is insufficient or a decision is human-owned, only the relevant
branch pauses. The user sees what is ready, what is blocked, why they are needed
and what their decision will change. Resume continues from durable state without
repeating committed work.

Current limited vertical: a default 12-round (maximum 24) bounded Controller with
explicit file/model/active-deadline bounds, server-owned Branch DAG,
branch-selective Evidence Gate, one budgeted plan repair, safe-point controls,
independent append-only logical ArtifactVersion/TaskCommit records and
history-preserving restore. A terminal Run can now create a new child Run under
the same server-owned `task_id`; the child records sequence, parent, selected
Branch, base Artifact/Commit, frozen Workspace revision and exact recheck refs.
The old Run stays immutable, and the browser resets its SSE cursor only after a
valid child snapshot. `DR-0054` now atomically commits the Task/current pointer,
Run and continuation receipts, requires parent Run plus Task expected versions,
and exposes a sanitized current/history projection. Seven Task tests and three
Demo 1/2 Worker recovery tests passed against an isolated PostgreSQL 17.11
instance. `DR-0055` adds a Branch-bound WorkUnit/Contribution ledger with strict
reservation replay and explicit recovered-unit retry. Later additions are a
distributed queue/lease, finer per-file source revisions, general
writable office artifacts, broader semantic/numeric evidence, multi-instance
lease/notification and verified source-file Commit. Initial acceptance data comes from FORTE administration,
finance, sales and SRE folders.

## 6. Demo 2 target: governed adaptive office swarm

Multiple work units are admitted into an adaptive topology. Scheduler and
Workers share immutable Artifact versions, add/reorder units when evidence
changes and converge through a verifier rather than majority prose.

The first limited increment is now implemented as service-owned
`TopologyAdmission`. It chooses `single_controller`, `fixed_workflow` or
`adaptive_readonly_workers` from frozen source structure/span, work-unit
independence, dependencies, remaining calls/time and `external_action=none`.
Same-function material and plans wider than three independent roots stay on the
fixed route. The adaptive route requires explicit user confirmation and starts
at most three process-local read-only Analyst Workers in each ready wave.
`direct_tool` remains a future route until the general Tool Gateway exists.
Every Worker return is a candidate: source membership, Evidence Anchor,
Branch Evidence Gate and applicable narrative/deterministic reconciliation
decide whether it is adopted before a stable merge into the normal Artifact
history. A failed/ambiguous Worker does not erase adopted siblings.

The second limited increment, `DR-0055`, persists the complete validated Branch
DAG as WorkUnits before dispatch. Reservation, attempt, budget and an ordered
event are committed before the model call; every return appends an immutable
Contribution, while adoption remains a separate Gate. PostgreSQL restart
preserves completed candidates and v1/v2, marks only an unconfirmed in-flight
unit as recovered failed, and never auto-replays it. A new idempotency key plus
current Run version can retry only that recovered unit. This is still not a
durable queue, lease, remote Worker runtime or multi-instance scheduler.

The user sees business work packages, dependencies, actual model/tool receipts,
replanning reason and convergence condition. Raw Worker prompts, chain-of-thought
and private conversations stay hidden. Initial acceptance data comes from FORTE
release readiness, legal review, recruitment and code-workspace folders.

The detailed research, scenarios and falsifiable gates are recorded in
[`DR-0053`](decisions/DR-0053-durable-task-lineage-and-explainable-topology-admission.md),
[`SCENARIO-038`](scenarios/SCENARIO-038-durable-task-continuation-across-runs.md)
and [`SCENARIO-039`](scenarios/SCENARIO-039-explainable-topology-and-verified-worker-convergence.md),
plus [`DR-0055`](decisions/DR-0055-durable-workunit-and-contribution-ledger.md)
and [`SCENARIO-041`](scenarios/SCENARIO-041-workunit-contribution-ledger-and-partial-convergence.md).
The implemented subset is `Limited Verified` by unit, browser and isolated
single-host PostgreSQL 17.11 automation; real Provider evidence, remote or
multi-instance execution and target-user research remain open.

## 7. Demo 3 target: risk and action gate

Any write or external action from either topology passes:

```text
ActionCandidate -> Risk -> Policy -> Evidence -> Human approval when required
-> Permit -> Tool Gateway -> execution receipt -> Artifact/Event update
```

The frontend always answers four questions: what will change, what will be
rechecked, what stays unchanged and what will not happen. A preview is never an
execution receipt. Current product performs no external action.

## 8. Deterministic verification priorities

Citation membership is insufficient. The next verifier layer should add:

1. spreadsheet row/formula and cross-period total checks;
2. CSV schema, count preservation and sorting checks;
3. document-rule coverage and contradiction checks;
4. log timeline/source-line checks;
5. code diff, command and test receipts in an isolated workspace;
6. output-format checks for CSV/DOCX/Markdown artifacts.

The preserved Finance negative result remains an acceptance baseline: a cited
model answer can still be numerically wrong.

## 9. Delivery order

1. Preserve whole-workspace browsing, safe preview, autonomous bounded evidence selection and truthful
   call/validation trace.
2. Preserve the bounded read-only Agent Control Loop, server-owned Branches and
   append-only logical result history.
3. Preserve the implemented minimal Task Ledger/current pointer, cross-Run
   lineage and bounded topology/Worker vertical; retain its real single-host
   PostgreSQL transaction gate and run an authorized Provider gate separately
   without broadening claims.
4. Preserve the implemented Task/Branch-bound WorkUnit/Contribution Ledger with
   explicit unit version, dependency, immutable candidate and local recovery state;
   next add a real queue/lease only after its ownership and failure semantics are tested.
5. Add file-level evidence locations plus task-specific deterministic validators.
6. Broaden the writable isolated Run workspace and immutable office-file
   Artifacts; keep source-file Commit separate from the current logical brief
   TaskCommit.
7. Evolve the current process-local Worker wave into a durable Scheduler with
   queue/lease, multi-instance ownership and explicit conflict convergence over
   the same Task/Branch/Artifact/Event contracts.
8. Add Demo 3 Risk/Evidence/Approval/Permit/Gateway control to both topologies.
9. Add production identity and durable/multi-process recovery.
10. Add governed Connectors only after impact preview, idempotency and failure
   receipts are verified.
11. Run target-user formative studies for comprehension, trust and task success.

## 10. Claim boundary

Current `Limited Verified` facts are folder inventory, bounded preview,
whole-workspace autonomous scope, bounded multi-round Controller, model receipts,
one budgeted plan repair, server plan/Branch checks, citation membership, Branch
Evidence Gate, fixed isolated Artifact adapters, ordered events and controls,
optional PostgreSQL-backed single-Controller recovery, independent append-only
logical brief/TaskCommit history, minimal owner-scoped Task record/current pointer,
dual-version bounded Task/Run continuation, deterministic
topology admission, an explicitly confirmed maximum-three in-process read-only
Worker wave, Branch-bound WorkUnit state, immutable Contribution candidates and
explicit checkpoint-recovered unit retry. Semantic correctness, source-file mutation, distributed or
multi-instance Worker leases, Tool Gateway, real Connectors, production identity,
durable queue/lease ownership, measured Worker benefit and user value are not current capabilities.
