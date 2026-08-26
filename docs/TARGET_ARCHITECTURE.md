# Office Agent target architecture

本文件描述目标架构，不是当前能力清单。当前实现边界以源码、API、Evidence
和下表 `Current` 列为准。
下文标为 target 或 not connected 的项目都是尚未完成的目标能力。历史 Demo
在其当时的提交范围内，当前执行结果仍全部来自 Simulator；现行 FORTE
工作区则不挂载任何工具执行或外部动作路由。

## 1. Product thesis

The Agent is general; Demo 1/2/3 are acceptance views over one capability
runtime. The product begins from an inspectable office workspace, not a hidden
Prompt or Demo switch. Users author a task and bounds, observe
server-backed execution facts and review outputs against sources. In the
current interaction, users choose the goal while the Agent chooses a bounded
evidence set from the complete safe workspace index.

Current implementation reaches a cited, bounded multi-round read-only brief,
server-owned task Branches and independent append-only logical result history.
Every source-file mutation, multi-instance coordination, Worker swarm and
Connector statement below is target design unless explicitly marked current.

## 2. Eight shared modules

| Module | Stable responsibility | Current | Target interaction impact |
| --- | --- | --- | --- |
| 1. Workspace Catalog & Safe Preview | file identity, integrity, safe projection and source policy | 15 folders/96 inputs, bounded preview | users inspect data before invocation and understand capability gaps |
| 2. Task Contract | goal, workspace scope, budget, deadline and completion criteria | instruction + whole-workspace refs + bounded rounds/files/calls/deadline | user states intent without doing retrieval first |
| 3. Planner | retrieve evidence, propose work intent and dependencies | strict per-round Planner with autonomous evidence selection and one budgeted repair | users see what the Agent chose, why, and whether the plan was adopted |
| 4. Admission, Policy Compiler & Validator | choose topology, compile policy, validate graph/sources/gates | server compilation and plan checks | route explanation shows why work stays single, splits or stops |
| 5. Scheduler & Worker Manager | bounded loop or adaptive workers, leases and replanning | one in-process bounded Controller with Branch states and selective resume | live work map shows actual units, waiting and replanning without Worker chat |
| 6. Tool Gateway | capability registry, Permit, idempotency and execution receipts | not connected | proposed impact appears before confirmation; actual impact after receipt |
| 7. Artifact Workspace & Verifier | immutable versions, evidence, conflict and Commit | append-only logical evidence briefs/TaskCommits, citation membership, Branch Evidence Gate and result restore | users review versions and evidence instead of trusting final prose |
| 8. Checkpoint, Event & Governance Control | durable state, ordered events, risk/evidence/approval | ordered controls/events, memory or PostgreSQL Snapshot/records, safe restart recovery | disconnect/restart recovery and human gates become explicit states |

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

The current `DR-0026` vertical slice validates a bounded read-only single-task
loop with Branch-selective continuation, append-only logical ArtifactVersion/
TaskCommit records and PostgreSQL restart integration. It does not validate
writable office artifacts, multi-instance leases or parallel Workers. Demo 1
ultimately validates the bounded durable single-task branch. Demo 2 validates the adaptive
multi-task branch. Demo 3 validates the same cross-cutting action gate for both.
Capabilities are registered once; a Demo identity never creates a special
private executor.

## 4. Mainstream difference and user flow

Official OpenClaw material foregrounds Gateway/channel/session/tool control;
Codex foregrounds project threads, worktrees and review queues; Claude Code
foregrounds project-directory agent loops, tools, subagents and permissions.
Those are strong patterns and can be extended. This project deliberately
foregrounds an office repository, Agent-selected evidence and business citations.

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
  -> confirm one proposed next task to start a new Loop
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

Current precursor: at most three read-only rounds, explicit file/model/deadline
bounds, server-owned Branch DAG, branch-selective Evidence Gate, one budgeted
plan repair, safe-point controls, independent append-only logical
ArtifactVersion/TaskCommit records and history-preserving restore. PostgreSQL can
recover the single-Controller checkpoint and records. Target additions: writable
isolated office artifacts, semantic/numeric evidence, explicit conflicts,
multi-instance lease/notification and verified source-file Commit. Initial
acceptance data comes from FORTE administration, finance, sales and SRE folders.

## 6. Demo 2 target: governed adaptive office swarm

Multiple work units are admitted into an adaptive topology. Scheduler and
Workers share immutable Artifact versions, add/reorder units when evidence
changes and converge through a verifier rather than majority prose.

The user sees business work packages, dependencies, actual model/tool receipts,
replanning reason and convergence condition. Raw Worker prompts, chain-of-thought
and private conversations stay hidden. Initial acceptance data comes from FORTE
release readiness, legal review, recruitment and code-workspace folders.

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
3. Add file-level evidence locations plus task-specific deterministic validators.
4. Add a writable isolated Run workspace and immutable office-file Artifacts;
   keep source-file Commit separate from the current logical brief TaskCommit.
5. Add Demo 2 Scheduler/Workers and multi-instance leases over the same
   Task/Branch/Artifact/Event contracts.
6. Add Demo 3 Risk/Evidence/Approval/Permit/Gateway control to both topologies.
7. Add production identity and durable/multi-process recovery.
8. Add governed Connectors only after impact preview, idempotency and failure
   receipts are verified.
9. Run target-user formative studies for comprehension, trust and task success.

## 10. Claim boundary

Current `Limited Verified` facts are folder inventory, bounded preview,
whole-workspace autonomous scope, bounded multi-round read-only Loop, model
receipts, one budgeted plan repair, server plan/Branch checks, citation
membership, branch Evidence Gate, ordered events, controls, PostgreSQL-backed
single-Controller recovery and independent append-only logical brief/TaskCommit
history. Writable office Artifacts, semantic correctness, multi-instance leases,
adaptive Workers, Tool Gateway, real Connectors, production identity and user
value are not current capabilities.
