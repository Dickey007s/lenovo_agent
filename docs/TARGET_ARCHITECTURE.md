# Target Architecture and Delivery Map

## 1. Product thesis

OpenClaw, Codex and Claude Code already document tools, permissions, background work, session recovery and multi-agent/subagent patterns. Office Agent must not present those primitives alone as novelty.

The target distinction is an enterprise-office interaction contract:

1. work starts from a versioned business source and Task Contract;
2. every visible state is backed by a server Snapshot or ordered event;
3. agents converge through versioned shared Artifacts and explicit verification;
4. external-action candidates are governed semantically, not only by shell/tool permission;
5. the foreground shows both prospective impact and actual receipt.

This is a design claim, not a verified superiority claim. The comparison uses official material, not competitor hands-on testing.

## 2. Mainstream comparison and UI impact

| Dimension | Mainstream official-material observation | Office Agent target | User-interaction consequence |
| --- | --- | --- | --- |
| Primary object | session, coding task, channel, repository/worktree or command | business Task, source version, Artifact and ControlEvent | user sees which business material and version is affected |
| Multi-agent work | subagents, parallel threads, background jobs are documented | Scheduler plus shared Artifact convergence and verification | user reviews one converged work graph instead of raw Worker chat |
| Permission/control | command/tool approval and sandboxing are common | semantic target, data, change and reversibility checks | confirmation says what changes, what is rechecked and what remains |
| Long-run recovery | session/history/resume patterns are documented | durable Task/Artifact/Event checkpoints | restart should resume from an auditable business state, not a prose recap |
| Observability | plans, tools, diff, tokens, logs and task status | business source, model receipt, validation, evidence and action receipt | internal logs stay hidden; decision-relevant facts stay visible |
| Output | code diff, command result or conversational response | versioned office Artifact plus governance receipt | user can compare versions, citations and downstream effects |

Sources and limitations are registered in [competitor research](research/COMPETITOR-RESEARCH-OPENCLAW-CODEX-CLAUDE-CODE-20260821.md) and the [Source Register](decisions/SOURCE_REGISTER.md). Do not say a competitor “cannot” do something unless independently tested.

## 3. Eight canonical modules

| # | Module | Current maturity | Current gap | Next evidence gate |
| --- | --- | --- | --- | --- |
| 1 | Scenario Pack & Workspace Catalog | Limited Verified | only three pinned public scenarios | versioned enterprise source adapter, identity and data-policy tests |
| 2 | Task Contract | Limited Verified | server-fixed, not negotiated or persisted | editable contract versioning, budget/deadline and recovery |
| 3 | Planner | Limited Verified | one model path; no quality baseline | fixed-set quality/cost study and fallback evidence |
| 4 | Admission & Plan Validator | Limited Verified | bounded path/tool/effect/dependency checks | budget, policy and replanning admission |
| 5 | Scheduler & Worker Manager | Draft | no current execution command | queued/running/cancel/retry/lease tests and visible receipts |
| 6 | Tool Gateway | Draft | generic package not connected to Harness | capability registry, validated invocation and unknown-outcome handling |
| 7 | Artifact Workspace & Verifier | Draft | plan declarations only | immutable versions, provenance, merge/conflict and verification |
| 8 | Checkpoint, Event & Governance Control | Partial | memory only; unsigned Owner | durable store, production identity, audit, approval and Permit |

## 4. Three Demo migrations

### Demo 1: durable evidence task

Current: Finance-018 safe sources, Task Contract, real-model plan and deterministic validation.

Target: execute workbook inspection, create cited Artifact versions, checkpoint each stage, expose conflict/branch decisions and Commit. The user should see evidence accumulate progressively rather than landing directly on a dense verification screen.

### Demo 2: adaptive collaboration

Current: pm-014 produces a validated dependency plan from PRD, configuration and two test reports.

Target: Admission selects an execution strategy; Scheduler creates Workers; shared Artifacts converge; new evidence can trigger visible replanning. The user should see why work was split or changed, but not raw Worker conversations.

### Demo 3: governed action

Current: Operations-008 can produce plan units that declare human-gated external-action candidates.

Target: verified Artifact to ActionCandidate to Risk/Policy/Evidence/Approval/Permit/Gateway/Simulator, with preview and receipt. The user should see the exact semantic impact before confirming and the observed result afterward.

All three execution migrations are `Draft`.

## 5. Delivery order

1. Preserve the sole worksite and source-integrity boundary.
2. Add durable Run/Event/Task Contract storage and production identity.
3. Implement Demo 1 Artifact execution and verifier as the first end-to-end execution slice.
4. Add Scheduler/Worker and replanning for Demo 2 on the same Artifact protocol.
5. Bind Demo 3 governance and Simulator to verified FORTE Artifacts.
6. Add real Connector only after deterministic identity, policy, idempotency and failure recovery are evidenced.
7. Run target-user comprehension studies; keep value claims `Draft` until then.

## 6. Current verified boundary

DR-0017 is `Limited Verified` for the single FORTE worksite, exact source package, safe projection, real-model planning, deterministic validation, memory Snapshot/SSE and recovery states. It stops at `ready_to_execute`; there is no independent final-current UI screenshot and no user study.
