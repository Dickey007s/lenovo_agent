# Workspace-centric Office Agent: mainstream comparison, scenarios and interaction impact

## 1. Document purpose

This is the retained source record for the next report. It connects technical
architecture to user flow and frontend output. It separates official product
facts, research inspiration, Stakeholder requirements, current implementation
evidence and unverified hypotheses.

Status: `Research and design record`. Product facts are source-backed at the
versions below. Claims about relative usability, trust, speed or user value are
`Draft` until target-user research is run.

## 2. Sources and what they support

| Source ID | Type and exact source | Version/date | Supported fact | Limitation |
| --- | --- | --- | --- | --- |
| `OPENCLAW-OFFICIAL-20260825` | [OpenClaw overview](https://docs.openclaw.ai/), [runtime architecture](https://docs.openclaw.ai/agent-runtime-architecture), [exec approvals](https://docs.openclaw.ai/tools/exec-approvals) | accessed 2026-08-25 | self-hosted Gateway, sessions/routing, built-in/plugin Harnesses, tools and host execution approvals | does not prove an office-folder evidence UX or that this project outperforms it |
| `OPENAI-CODEX-APP-20260202` | OpenAI, [Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/) | 2026-02-02 | parallel Agent threads, worktrees, review of changes, Skills and Automation review queue | software-development product description; not a direct office-work benchmark |
| `CLAUDE-CODE-OFFICIAL-20260825` | Anthropic, [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works), [subagents](https://code.claude.com/docs/en/sub-agents), [permissions](https://code.claude.com/docs/en/permissions) | accessed 2026-08-25 | project-directory context, tool loop, subagents, permissions and multiple interfaces | code/project workflow; official docs do not establish this project's usability |
| `REACT-ICLR-2023` | Yao et al., [ReAct](https://arxiv.org/abs/2210.03629) | ICLR 2023, arXiv v3 | interleaving reasoning, action and observation can organize an Agent trajectory | does not prescribe durable state, office file UI, policy compiler or citation controls |
| `FORTE-PINNED-20260825` | [AGI-Eval-Official/FORTE](https://github.com/AGI-Eval-Official/FORTE), commit `345c1ec1487139db9dd319787fa9405ba85d1869` | pinned 2026-08-25 | public office benchmark spans 15 professions; public repo contains one demo per profession | public benchmark, not a production enterprise database or user study |
| `USER-FEEDBACK-20260825-WHOLE-FOLDER-14` | [Stakeholder feedback](../sources/USER-FEEDBACK-20260825-14-folder-workspace-and-interaction-reporting.md) | 2026-08-25 | whole-folder browsing, file information, four-format preview/control and report traceability are required | one Stakeholder, not representative user research |

## 3. Mainstream comparison and interaction consequences

The comparison is about emphasis, not an exclusivity claim. OpenClaw, Codex and
Claude Code continue to evolve and can be extended. We do not claim that they
cannot implement any pattern below.

| Approach | Primary interaction object in cited material | Strong design emphasis | This project's deliberate difference | User-flow consequence |
| --- | --- | --- | --- | --- |
| OpenClaw | message, session, channel and Gateway | always-available multi-channel Agent, routing, tools and host approvals | one server-owned office folder, explicit per-task file scope and evidence citations are the foreground | users inspect data and scope first, rather than beginning from a message channel |
| Codex app | project thread, worktree and review queue | parallel software tasks, isolated changes and result review | public office files are read-only source evidence; plans/results are reviewed against selected business files | users review citations and business findings rather than code diffs/worktree changes |
| Claude Code | project directory plus terminal/IDE Agent loop | broad project context, tool use, subagents, permission modes and checkpoints | the model does not receive silent whole-workspace authority; the user chooses bounded files and server policy validates the plan | an extra scope-selection step appears before execution, reducing hidden context expansion |
| ReAct-style Agent | reasoning/action/observation trajectory | iterative plan updates through environment interaction | ordinary UI shows receipts, validated operations and server events, not chain-of-thought | users see what was called and accepted without exposing private reasoning traces |
| Current Office Agent | folder, selected files, user-authored task, Run Snapshot and citations | provenance-first office analysis with server-owned policy | one interface supports arbitrary cross-folder questions; Demo identities are acceptance lenses only | browse -> inspect -> select -> instruct -> observe -> cite -> review |

## 4. Why the architecture changes the UI

### 4.1 Server-owned workspace catalog

Technical difference: public file identity, manifest integrity, preview parsing
and safe projection are owned by the server, not inferred from filenames in the
browser or supplied by the model.

Frontend effect: the user sees a normal folder tree, type, size, row/page count
and a security note. Integrity failure is distinct from network failure. Raw
paths and hashes stay in the audit layer.

### 4.2 Explicit task-scoped context

Technical difference: a Run freezes user-selected `file_ref` values, and both
plan and result validation reject references outside that set.

Frontend effect: selected-file chips form a visible contract. The user can
remove scope before the model call and reopen citations afterward. This makes
context control inspectable, at the cost of one deliberate selection step.

### 4.3 Model intent plus deterministic policy compiler

Technical difference: a model proposes business intent; the server compiles
effect/gate policy and validates dependencies, tools, sources and citations.

Frontend effect: “模型已调用” is separate from “内容已采用” and “服务端已校验”.
A returned but rejected model response is visible as not adopted, not disguised
as a successful step or a generic failure.

### 4.4 Ordered events plus authoritative Snapshot

Technical difference: named events explain progress while the Run Snapshot is
the state authority. Sequence numbers support reconnect without fabricating
progress.

Frontend effect: users see a business trajectory, elapsed call receipts,
reconnecting state and final reconciliation. Animation alone never proves a
model call or task completion.

### 4.5 Evidence-in-place results

Technical difference: every finding must cite one or more frozen selected
files. Membership validation is deterministic; semantic correctness is not.

Frontend effect: citations are actions, not footnote decoration. Clicking one
returns the user to the same safe preview. The result remains “待复核” because
membership is weaker than entailment or numerical verification.

## 5. Concrete use scenarios

| Scenario | Trigger | Agent topology lens | Human role | Completion evidence |
| --- | --- | --- | --- | --- |
| Finance cross-period reconciliation | three period workbooks need comparison | Demo 1 bounded single-task loop | decide ambiguous accounting definitions; verify totals | selected sheets, deterministic totals, cited rows, reviewed output |
| Onboarding asset allocation | roster CSV must be matched to PDF policy | Demo 1 with evidence pause | resolve conflicting or missing allocation rule | mapping table, exception list and source rule citations |
| Resume and JD comparison | two jobs and multiple candidate documents | Demo 2 multi-task organization | own the hiring decision and sensitive-data review | per-candidate evidence, cross-worker consistency and review receipt |
| Release readiness | PRD, configuration and test reports disagree | Demo 2 adaptive reconciliation | decide unresolved release conflicts | worker graph, conflict reconciliation and cited report set |
| Incident diagnosis | a log needs a timeline and mitigation options | Demo 1 plus Demo 3 Risk Gate | approve any real command; current product stays read-only | cited log lines, proposed actions and explicit no-execution receipt |
| External SQL or scheduled Web task | task has no local input and needs a Connector | Demo 3 governed capability boundary | approve scope, credentials and side effect | current expected result is a deterministic capability block |

The detailed 15-case catalog remains in
[`FORTE-PUBLIC-OFFICE-TASK-TEST-CASES-20260825`](../testing/FORTE-PUBLIC-OFFICE-TASK-TEST-CASES-20260825.md).

## 6. HCI directions carried into the product

1. **Mixed-initiative scoping**: the Agent can suggest a plan, but the user owns
   the initial data boundary and any later high-impact expansion.
2. **Progressive disclosure**: folder and result summaries lead; security,
   validation and detailed trace remain available without dominating the page.
3. **Legibility without chain-of-thought**: show calls, operations, validations,
   receipts and citations instead of private reasoning text.
4. **Provenance as navigation**: evidence links return to the exact source
   preview and make review part of the primary path.
5. **Recoverable collaboration**: idempotent start, monotonic Snapshot and SSE
   resume prevent a retry from silently starting a second task or rolling back.
6. **Topology-independent capability**: the same workspace, source, policy,
   event and evidence components serve single-task, swarm and governed-action
   flows. Demo names do not gate capabilities.
7. **Human authority at uncertainty**: schema/policy failure stops safely;
   semantic or numerical uncertainty is shown as review work, not hidden behind
   a completed animation.

## 7. Frontend output contract

| State | What the user sees | What produces it | What remains hidden |
| --- | --- | --- | --- |
| workspace ready | folder/file count and searchable tree | validated public workspace projection | benchmark task prompt, rubric, solution, raw manifest |
| file selected/open | metadata, safe preview and security statement | file preview route after integrity validation | full binary, macros, external loads, path/hash |
| task draft | selected-file chips and user instruction | browser draft only | no claim that server accepted it |
| task accepted | frozen scope and first trajectory event | POST Run response and seq 1 | internal Run IDs in primary copy |
| model running/returned | called model, elapsed time, adopted/not-adopted | model receipt | Prompt, chain-of-thought, raw output |
| plan accepted | readable ordered work plan | server-compiled and validated plan | raw effect/gate identifiers |
| result ready | initial findings, clickable citations, review warning | validated result with selected `file_ref` membership | correctness claim, external-action claim |
| stream interrupted | reconnecting and retry state | transport fact plus last event sequence | invented progress |
| integrity invalid | source-specific fail-closed message | controlled 503 from Catalog | partial/stale folder data |

## 8. Current implementation facts and open hypotheses

### Implemented and testable

- one public workspace with 15 folders and 96 files;
- bounded previews for XLSX/CSV, PDF, DOCX and text/code formats;
- manifest, size, hash, path, symlink, archive and active-content controls;
- arbitrary cross-folder selected scope and user-authored instruction;
- server-compiled plan policy, separate model receipts, ordered events and
  selected-scope citations;
- read-only result and no external side effect.

### Not yet proved

- users understand the folder-first flow faster than the prior Scenario UI;
- explicit selection creates the right balance between control and effort;
- citations improve calibrated trust or error detection;
- the model completes all 15 FORTE tasks correctly;
- persistent recovery, distributed workers, real file writes or Connectors;
- production identity, enterprise data policy or representative user value.

## 9. Report checklist

Every slide or Demo claim derived from this document must include:

- one concrete user scenario and its exception path;
- one precise source ID and its limitation;
- the technical difference and the resulting user-flow change;
- the visible frontend state/action/feedback/recovery;
- the authoritative server fact and hidden internal details;
- current Evidence status and the claims it does not support.
