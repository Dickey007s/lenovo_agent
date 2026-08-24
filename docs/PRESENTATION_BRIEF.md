# Office Agent V0.2 Presentation Brief

## 1. One-sentence position

Office Agent is not another “multi-agent can call tools” demo. It is a FORTE-backed office worksite that binds source, Task Contract, model plan, deterministic validation and foreground receipts, then stops honestly at `ready_to_execute`.

## 2. Reporting rule

Every slide and spoken claim must pass [DECISION_AND_REPORTING_GOVERNANCE.md](DECISION_AND_REPORTING_GOVERNANCE.md): it needs 场景与来源、前台交互影响、后端事实映射、验证与边界. Historical Customer A screenshots or run numbers cannot describe the current product.

## 3. Recommended 12-slide story

| Slide | Core message | Visual | Evidence/claim boundary |
| --- | --- | --- | --- |
| 1. Why now | long office tasks fail when source, state and impact are invisible | source → plan → validation → receipt flow | problem framing; not a measured prevalence claim |
| 2. Mainstream baseline | OpenClaw/Codex/Claude Code already cover tools, permissions, sessions and parallel/background work | official-material comparison table | official docs, not competitor testing |
| 3. Our design thesis | novelty target is business-fact alignment, shared Artifact convergence, semantic action governance and two-time impact feedback | four design pillars | `Draft` differentiation/value claim |
| 4. One worksite | old product identities are retired; FORTE worksite is the only current entry | current layout schematic, not a fabricated screenshot | DR-0017 + code/E2E; no independent final screenshot |
| 5. Real source | 3 public FORTE folders, 8 input files plus 3 provenance task files | source tree with safe labels | pinned commit/MIT/11 files/`115352` bytes |
| 6. Eight modules | one canonical Runtime architecture | maturity matrix | modules 1-4 + memory part of 8 current; 5-7 Draft |
| 7. Demo 1 | cross-period finance planning from three workbooks | progressive source/plan/validate journey | planning only; no row-level execution or Artifact |
| 8. Demo 2 | release evidence becomes a dynamic dependency plan | plan graph and future replan lane | Scheduler/Worker/shared Artifact remain Draft |
| 9. Demo 3 | action candidates declare gate and effect before execution | future impact preview → receipt | current product never executes action |
| 10. Frontend/backend alignment | every label comes from a Snapshot field or ordered event | UI—server fact matrix | no animation or model prose as truth |
| 11. Engineering evidence | source integrity, route retirement, E2E, live model planning | Evidence ledger | bounded engineering evidence only |
| 12. Next proof | durable execution, Artifact convergence, governance, then user study | phased roadmap | no production/value claim yet |

## 4. Technical comparison wording

Use:

> OpenClaw, Codex and Claude Code official materials show that tools, permissions, background work, sessions and agent delegation are already mainstream. Our target distinction is not the number of Agents. It is how an office user sees business source, shared Artifact state, semantic impact and execution receipt.

Do not use:

- “competitors do not support multi-agent/background/approval”;
- “Office Agent is the first”;
- “our approach is safer/faster/more trusted” without a controlled evaluation;
- “the demos are complete” when the current Runtime stops before execution.

## 5. Demo narration

1. Open the sole FORTE worksite and select a Scenario.
2. Point to public source labels and the Task Contract; explain what is deliberately hidden.
3. Start a new round. Let read, planning and validation appear progressively.
4. In the activity rail, distinguish model called, output adopted and plan validated.
5. At `ready_to_execute`, say: “计划已经通过服务端校验，但任何工具和外部动作都还没有执行。”
6. Switch scenarios to show one Runtime contract supporting three policies, not three unrelated products.
7. Close with the target execution migration and its evidence gates.

Never use the negative user-feedback screenshot as a final-state product image. It is evidence of the pre-fix problem only. Older DR-0016 screenshots are transitional history. The current visual state lacks an independent new screenshot.

## 6. Evidence ledger

| Claim | Status | Evidence | Cannot imply |
| --- | --- | --- | --- |
| one current worksite and six API paths | Limited Verified | implementation `b2b759b...` + `5fab10f...`, PR #24, OpenAPI/404 probes | merge to master or product adoption |
| FORTE source exactness | Verified for fixed import | fresh-clone 11 files/`115352` bytes/0 mismatches; source commit `345c1ec...` | enterprise production realism |
| frontend recovery and privacy | Limited Verified | Harness E2E `11 passed in 41.4s` | user comprehension or visual quality |
| real-model planning | observed bounded run | Finance-018, `deepseek-v4-pro`, `16838 ms`, 10 units, called/adopted, v6/seq 5 | quality, SLA, savings or repeated benchmark |
| no current execution | Verified current boundary | code/routes/Snapshot `ready_to_execute` | future Scheduler/Worker/action capability |
| user value and trust | Draft | no target-user study | effectiveness claim |

Automated acceptance for PR #24: Python `47 passed in 2.42s`; Ruff passed; web lint passed; build passed (compile `2.1s`, TypeScript `4.1s`, static `757ms`); Harness E2E `11 passed in 41.4s`.

PR #24 was open and unmerged at evidence capture. The implementation commits are `b2b759b106738fbb3aed597319208e8ff4718cc7` and `5fab10fb4f638958ff78b39583a4eace2e99396b`.

## 7. Source trail

- [Source Register](decisions/SOURCE_REGISTER.md)
- [FORTE audit](research/FORTE-DATASET-AUDIT-20260824.md)
- [Competitor research](research/COMPETITOR-RESEARCH-OPENCLAW-CODEX-CLAUDE-CODE-20260821.md)
- [DR-0016](decisions/DR-0016-public-workspace-agent-harness.md)
- [DR-0017](decisions/DR-0017-single-forte-worksite-and-legacy-retirement.md)
- [DR-0017 Evidence](evidence/FORTE-ONLY-WORKSITE-RETIREMENT-EVIDENCE-20260824.md)
- [Retirement register](decisions/RETIREMENT_REGISTER.md)
