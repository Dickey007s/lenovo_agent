# Target Architecture and Delivery Map

> 这是一张目标能力与成熟度地图，**不是当前能力清单**。Current facts are explicitly labeled below.

## 1. Product thesis

OpenClaw, Codex and Claude Code official materials already describe tools, permissions, background work, session recovery and agent delegation. Office Agent should not present those primitives alone as novelty.

The target distinction is an office interaction contract:

1. users inspect and choose versioned business sources;
2. users own the task instruction;
3. every visible stage comes from a server Snapshot or ordered event;
4. shared outputs carry source citations and explicit verification;
5. possible side effects receive semantic impact preview and actual receipt.

This remains a design claim, not a verified superiority claim. Official documentation is not competitor hands-on testing.

## 2. Mainstream comparison and UI impact

| Dimension | Mainstream official-material observation | Office Agent target | User-interaction consequence |
| --- | --- | --- | --- |
| Primary object | session, coding task, channel, repo/worktree or command | business Task, selected source version, Artifact and ControlEvent | user sees which business files and version matter |
| User intent | prompt/session centered | explicit Task Contract over selected files | user defines the question instead of watching a preset Demo |
| Multi-agent work | subagents, threads and background jobs documented | Scheduler plus shared Artifact convergence | user reviews one converged work graph, not Worker chat |
| Permission | command/tool approval and sandbox common | semantic target/data/change/reversibility checks | confirmation explains business impact |
| Observability | plans, tools, diff, tokens, logs, status | source, call receipts, validation, citations and action receipt | internal reasoning stays hidden; decision facts remain visible |
| Output | conversational answer, code diff or command result | versioned office Artifact and governance receipt | user can compare citations, versions and downstream effects |

Sources and limitations: [competitor research](research/COMPETITOR-RESEARCH-OPENCLAW-CODEX-CLAUDE-CODE-20260821.md) and [Source Register](decisions/SOURCE_REGISTER.md).

## 3. Eight canonical modules

| # | Module | Current maturity | Current gap | Next evidence gate |
| --- | --- | --- | --- | --- |
| 1 | Scenario Pack & Workspace Catalog | Limited Verified | three pinned public collections; bounded preview | enterprise adapter, data policy and source identity |
| 2 | Task Contract | Limited Verified | instruction/selection are memory-only | versioned contract, budget/deadline and durable recovery |
| 3 | Planner | Limited Verified | Planner + Analyst on one model; no quality baseline | fixed-set quality/cost study and fallback policy |
| 4 | Admission & Plan Validator | Limited Verified | structural plan and citation membership only; one live Finance answer disagreed with deterministic ground truth | spreadsheet operator, claim-level semantic/numeric verifier, budgets and replanning |
| 5 | Scheduler & Worker Manager | Draft | no Scheduler/Worker execution | queue, lease, retry, cancellation and recovery |
| 6 | Tool Gateway | Draft | no current invocation | current capability registry, Permit and unknown-outcome receipt |
| 7 | Artifact Workspace & Verifier | Partial | Snapshot result; no immutable Artifact | version, provenance, merge/conflict, verification and Commit |
| 8 | Checkpoint, Event & Governance Control | Partial | memory events/idempotency, unsigned Owner | durable store, production identity, audit and action control |

## 4. Capability composition, not Demo runtimes

The Agent owns one reusable capability layer. Admission composes a work policy from the task and available evidence:

```text
task_topology = single_task | multi_task
orchestration = bounded_loop | adaptive_swarm
control_requirements = evidence_gate | human_gate | risk_gate
```

The three Demos are acceptance lenses over that layer:

| Demo lens | Composition | User-visible proof target |
| --- | --- | --- |
| Demo 1 | one task + bounded loop + evidence/human gates | a task is decomposed, advances checkpoint by checkpoint, pauses at the exact uncertain unit, accepts a human decision, resumes and commits a traceable artifact |
| Demo 2 | multiple tasks + adaptive swarm + evidence/human gates | real work units self-organize from dependencies, run in parallel when allowed, replan when facts change and converge into a shared verified artifact |
| Demo 3 | risk gate across either topology | an intended side effect shows semantic impact, deterministic controls and the actual execution/no-execution receipt |

Selecting a benchmark collection never grants a capability. Scenario policy constrains sources/tools and can recommend a profile; the Runtime capability registry and control plane are shared. The current code only exposes `current_runtime_scope=read_only_analysis`, so all three execution proof targets remain `Draft`.

## 5. Current cross-scenario slice

The current workbench applies one interaction contract to three FORTE collections:

- Finance-018: inspect period workbooks and ask a custom reconciliation question;
- pm-014: inspect PRD/config/test inputs and ask a release-readiness question;
- Operations-008: inspect policy Markdown and ask a governed-process question.

Current completion is a cited, review-required, read-only Snapshot response. It is not a correctness/quality pass, versioned Artifact, multi-Worker execution or governed external action. In the recorded Finance case, the model stated 20 / `2,202,000`; a deterministic regression reproduced 23 / `1,845,444.71`.

## 6. 尚未完成的目标能力

以下迁移都是目标设计，不是现行产品能力。历史动作原型中的**当前执行结果仍全部来自 Simulator**；现行 FORTE 数据工作台没有调用这些旧动作路径，也没有真实 Connector 副作用。

### Durable evidence

Add row/field-level evidence, immutable Artifact versions, checkpoints, conflict/branch decisions and Commit. The frontend should progressively accumulate evidence rather than dump a final explanation.

### Adaptive collaboration

Add Admission, Scheduler, Workers, shared Artifact convergence and visible replanning. Show why work splits or changes, while hiding raw Worker conversations.

### Governed action

Bind reviewed Artifact to ActionCandidate, Risk/Policy/Evidence, Approval, Permit, Gateway and Simulator/Connector. Show semantic impact before confirmation and actual receipt afterward.

All three execution migrations remain `Draft`.

## 7. Delivery order

1. Preserve the data-first workbench, stable refs, preview integrity and truthful trace.
2. Add a deterministic spreadsheet operator and claim verification beyond citation membership; the Finance negative regression is the acceptance baseline.
3. Persist Task Contract, Run/Event and immutable Artifact versions under production identity.
4. Implement the generic single-task bounded executor and durable evidence/Commit; use Demo 1 only as its first acceptance scenario.
5. Extend the same Task/Artifact/Event contracts with adaptive Scheduler/Workers and shared convergence; use Demo 2 as the acceptance scenario.
6. Apply the shared risk/action control plane to both topologies; use Demo 3 to verify impact preview, approval and receipts.
7. Add governed Simulator, then real Connector only after identity/idempotency/recovery evidence.
8. Run target-user studies for clarity, trust and task success.

## 8. Current evidence boundary

[DR-0018](decisions/DR-0018-forte-data-workbench-and-verifiable-trace.md) is `Limited Verified` for the fixed FORTE workbench, bounded preview, two model calls per observed Run, selected-ref validation, eight-event trace and an initial Finance-018 response. Its two live observations, three provenance-scoped screenshots and deterministic negative regression do not verify semantic correctness, durable recovery, external action or user value.

[DR-0019](decisions/DR-0019-capability-composed-agent-runtime.md) is `Limited Verified` only for replacing Demo-specific Scenario/Planner identity with a strict generic `work_profile`. It does not verify bounded execution, adaptive self-organization or governed action.
