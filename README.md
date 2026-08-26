# Office Agent V0.2

Office Agent is one FORTE-backed office folder, not a gallery of registered
Demo scenarios. A user can browse the entire public office repository like a
file manager, inspect bounded safe previews and submit only a goal. The Agent
then searches the whole safe index, explains which evidence it selected, runs a
server-backed Agent Control Loop and proposes source-bound next tasks that start
only after human confirmation.

The current product is deliberately narrow. `completed` means the Planner
candidate passed server policy/structure checks and the Analyst response passed
schema, selected-reference, server-resolved evidence-location and read-only
boundary checks. It does not mean the answer is correct, a file was changed or
an external business action happened.

## Current product

The root page is the only product entry:

- left: one searchable, collapsible folder tree containing all 96 public FORTE
  input files, with file-type filters and no role or Demo partition;
- center: file metadata, CSV/XLSX/PDF/DOCX/TXT/code preview, a free-form task
  composer, loop budget, round history, server-owned task branches, evidence
  gaps, controls, append-only result history, a cited read-only brief and up to
  four proposed next tasks;
- right: current phase, ordered server events and separate Planner/Analyst
  adoption receipts;
- boundary: the Run freezes the complete allowlisted index; each round exposes
  only the Agent-selected, server-budgeted files to analysis. Originals stay
  read-only, results require review and no external action occurs.

The primary flow is:

```text
browse or search the whole repository
  -> inspect safe file preview
  -> author an original task
  -> freeze a whole-workspace AgentControlLoopContract and budget
  -> deepseek-v4-pro Planner selects a minimal evidence set and explains why
  -> server compiles and validates scope, tools, dependencies and effects
  -> deepseek-v4-pro Analyst reads the approved safe projections
  -> Analyst separates fact, impact and human decision options, then returns exact quote candidates
  -> server uniquely resolves safe-preview locations and keeps only reviewable findings
  -> server validates citation membership, evidence anchors and the Evidence Gate
  -> location/structure cannot be adopted: one bounded repair, then preserve valid work and pause one branch
  -> evidence missing: pause the affected task branches before spending another round
  -> user chooses one branch: next round is bound to that branch's missing sources
  -> ordered SSE + authoritative Snapshot
  -> one append-only logical evidence-brief ArtifactVersion per completed round
  -> separate TaskCommit selects the current version + proposed next tasks
  -> user may restore an older brief by creating another TaskCommit; history remains
  -> human confirms one proposal -> independent new Control Loop
```

Model receipts distinguish `未调用`, `已采用` and `未采用`. A returned model
response that fails server validation is not presented as success. A rejected
plan may be repaired once within the same model-call budget, and both the
rejection and retry remain visible in the ordered trace. Ordinary UI
hides Prompt, chain-of-thought, raw provider response, absolute path, digest,
benchmark task/rubric/solution and internal effect/gate identifiers.

## General Agent, three acceptance lenses

Demo names do not unlock capability or select private code paths:

- Demo 1 tests a decomposed single task, bounded loop, evidence/human pause and
  later resume;
- Demo 2 tests multiple work units, adaptive scheduling and shared-artifact
  convergence;
- Demo 3 applies a cross-cutting risk/action gate to either topology.

The current Runtime is a `bounded_read_only_control_loop`. Validated plan units
become server-owned task branches; a user can continue one waiting branch while
the others keep their state. Logical evidence briefs and TaskCommits are stored
as independent append-only records, and a versioned rollback command can move
the current result pointer without deleting history or modifying source files.
PostgreSQL also restores accepted snapshots and idempotency receipts after API
restart. Adaptive Workers, writable office artifacts, multi-instance leases and
governed external actions remain target architecture, not current claims.

## Public data and preview boundary

FORTE is pinned to commit
`345c1ec1487139db9dd319787fa9405ba85d1869` under its top-level MIT license.
The imported public set contains 15 task records plus 96 input files: 111 files
and `1,780,445` bytes. The official repository describes a 180-task benchmark
but publishes only one demo per profession; this project does not claim access
to the unpublished tasks.

`public-suite-manifest.json` is the active read-only inventory. Every preview
revalidates allowlisted relative path, size, SHA-256, non-symlink file and
bounded format handling. The current all-file smoke produces 96/96 previews:
70 text/code, 11 document, 9 table and 6 PDF. Macro/active content and external
resources are never executed or loaded.

`task.md` remains provenance only. It is not a hidden default instruction and
does not enter ordinary UI or model-selected context. The user supplies an
instruction; the server freezes all 96 stable refs, while the Planner sees only
safe metadata and autonomously selects a bounded set for each round.

## Seven-path API

```text
GET  /v1/health
GET  /v1/harness/workspace
GET  /v1/harness/workspace/files/{file_ref}
POST /v1/harness/runs
GET  /v1/harness/runs?limit={1..20}
GET  /v1/harness/runs/{run_id}
POST /v1/harness/runs/{run_id}/controls
GET  /v1/harness/runs/{run_id}/events?after={sequence}
```

The former Scenario list/detail routes are not mounted. There are eight public
operations over seven OpenAPI paths because `GET` and `POST` share `/runs`.
`X-User-Id` remains an unsigned demonstration Owner placeholder. With
`DATABASE_DSN`, accepted Run snapshots, command receipts, ArtifactVersions and
TaskCommits are stored in PostgreSQL. Recovery rolls an interrupted model call
back to the last completed round and pauses for the user; it never silently
replays the call. Without a database, health reports `memory` and process-
restart recovery is unavailable.

## Eight modules

1. Workspace Catalog & Safe Preview
2. Task Contract
3. Planner
4. Admission, Policy Compiler & Plan Validator
5. Scheduler & Worker Manager
6. Tool Gateway
7. Artifact Workspace & Verifier
8. Checkpoint, Event & Governance Control

Current implementation covers modules 1-4; a bounded single-loop controller
subset of module 5; a read-only result, citation, Evidence Gate, logical
append-only ArtifactVersion and TaskCommit pointer/restore subset of module 7;
and a Snapshot/event, branch control, idempotency and optional PostgreSQL
restart-recovery subset of module 8. Distributed Worker scheduling, a real Tool
Gateway, writable office artifacts, semantic/numeric verification,
multi-instance coordination and governed external action remain target work.

## Evidence status

- `DR-0021` is `Limited Verified` for importing and inventorying the complete
  pinned public demo suite.
- `DR-0022` remains historical `Limited Verified` evidence for the one-folder
  product, 96 safe previews and its former selected-file browser path. That
  manual-scope interaction is superseded by `DR-0024`. Implementation
  [`0794648`](https://github.com/Dickey007s/lenovo_agent/commit/0794648477ad0061a5460127af8800a021019366)
  and [PR #27](https://github.com/Dickey007s/lenovo_agent/pull/27) are bound;
  the stacked series #25-#29 was consolidated into `master` on 2026-08-25.
- `DR-0023` is `Limited Verified` for the bounded read-only Agent Control Loop.
  Implementation `8364b1e` and stacked [PR #28](https://github.com/Dickey007s/lenovo_agent/pull/28)
  are bound and now merged through the consolidated series. A real
  `deepseek-v4-pro` run completed 2 rounds over 8 FORTE files with 5 model calls
  and 21 ordered events; the first candidate plan was rejected, visibly retried
  once within budget, then adopted.
- `DR-0024` replaces the `DR-0022` manual selected-file interaction with a
  whole-workspace contract, Agent-owned per-round evidence selection and
  human-confirmed next-task proposals. Its final verification is recorded in
  the linked Evidence ledger.
- `DR-0025` adds the human-confirmed between-round Evidence Gate, logical result
  versions, current-Run restoration and optional PostgreSQL restart recovery.
  PR #30 is merged through `8c55422`; its group-resume and Snapshot-embedded
  artifact conclusions are retained as historical baseline.
- `DR-0026` adds server-owned task branches, branch-selective continuation,
  independent append-only logical ArtifactVersion/TaskCommit records and a
  history-preserving restore command. Current local checks are `63 passed,
  1 skipped`, Runtime `26 passed`, browser `13 passed`, plus Ruff/lint/build.
  PR #31 also passed the PostgreSQL 17.11 four-Runtime restart integration gate;
  it is merged into `master` as `697e38b`, and the job URL plus exact boundary
  are bound in the dated Evidence.
- `DR-0028` projects the server-owned workspace paths as a collapsible folder
  tree and adds an in-context review page for Branch gaps, Findings and
  next-task proposals. It reuses the existing safe Preview API, makes citation
  limits explicit and does not add semantic verification or per-proposal
  citations.
- `DR-0029` adds server-verified Evidence Anchors. A Finding now carries exact
  safe-preview text lines or table rows resolved from verbatim model quotes;
  the review page compares evidence roles and jumps to highlighted source
  locations. Location verification still does not prove semantic correctness.
- `DR-0030` turns an anchored Finding into a Chinese problem-handling sheet:
  fact, impact, human-decision need, mutually exclusive choices, Agent next step
  and user feedback are separate. Accept, decline and defer are versioned,
  idempotent receipts bound to a Finding/Resolution/Branch; an accepted business
  choice then starts a new read-only Run. Location results are `exact`,
  `ambiguous` or `unavailable`; one bounded repair preserves valid Findings,
  completed Branches and ArtifactVersions, while only affected Branches wait for
  candidate selection or guided recovery. When recovery reaches a
  `stopped/bounded` budget terminal, the UI no longer suggests that the old Run
  can resume: it lists unfinished Branches and creates a new whole-workspace Run
  for the selected Branch objective, preserving the old Run and artifacts.
  Security-scope violations still fail closed.
- No target-user study has been run. Clarity, trust, efficiency and user value
  remain hypotheses.

Detailed claims and limits live in
[`FORTE-FOLDER-WORKSPACE-EVIDENCE-20260825`](docs/evidence/FORTE-FOLDER-WORKSPACE-EVIDENCE-20260825.md)
and [`AGENT-CONTROL-LOOP-BOUNDED-READONLY-20260825`](docs/evidence/AGENT-CONTROL-LOOP-BOUNDED-READONLY-EVIDENCE-20260825.md).
The current whole-workspace interaction is tracked in
[`AUTONOMOUS-WHOLE-WORKSPACE-RESEARCH-20260825`](docs/evidence/AUTONOMOUS-WHOLE-WORKSPACE-RESEARCH-EVIDENCE-20260825.md).
The current Demo 1 branch/artifact increment is tracked in
[`DEMO1-BRANCH-ARTIFACT-CONTROL-20260826`](docs/evidence/DEMO1-BRANCH-ARTIFACT-CONTROL-EVIDENCE-20260826.md).
The current folder hierarchy and issue-review interaction is tracked in
[`WORKSPACE-TREE-AND-EVIDENCE-REVIEW-20260826`](docs/evidence/WORKSPACE-TREE-AND-EVIDENCE-REVIEW-EVIDENCE-20260826.md).
The current exact evidence-location interaction is tracked in
[`PINPOINT-EVIDENCE-REVIEW-20260826`](docs/evidence/PINPOINT-EVIDENCE-REVIEW-EVIDENCE-20260826.md).
The current actionable review and recoverable-analysis interaction is tracked in
[`ACTIONABLE-REVIEW-AND-RECOVERY-20260826`](docs/evidence/ACTIONABLE-REVIEW-AND-RECOVERY-EVIDENCE-20260826.md).

## Local run

Requirements: Python `>=3.12,<3.13`, Node/pnpm compatible with the lockfile and
an OpenAI-compatible `/chat/completions` endpoint.

```dotenv
LLM_BASE_URL=https://your-openai-compatible-endpoint.example/v1
LLM_API_KEY=replace-me
LLM_MODEL=deepseek-v4-pro
```

Never commit `.env`, API keys, production credentials or real customer data.

```powershell
.\scripts\start-demo.ps1
.\scripts\stop-demo.ps1
```

本地启动器只把当前 PowerShell 进程中显式设置的 `DATABASE_DSN` 视为外部
PostgreSQL 授权；没有 Docker 且没有该显式变量时，会覆盖 `.env` 中可能残留的
数据库地址并明确回退到单进程 memory。模型端点、Key 与模型名仍可从 `.env`
读取。启动后以 `/v1/health` 的 `checkpoint`、`task_store` 为最终事实，不能只看
启动提示推断是否具备重启恢复。

- Web: <http://localhost:3000>
- API: <http://localhost:8010>
- OpenAPI: <http://localhost:8010/docs>

## Verification

```powershell
uv run pytest -q
uv run ruff check .
pnpm --dir apps/web lint
pnpm --dir apps/web build
pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts
```

## Living records

- [当前架构](docs/ARCHITECTURE.md)
- [HTTP API 与 SSE](docs/API.md)
- [工作区与流式交互](docs/WORKSPACE_AND_STREAMING.md)
- [前后端事实矩阵](docs/contracts/UI_SERVER_FACT_MATRIX.md)
- [目标架构](docs/TARGET_ARCHITECTURE.md)
- [中文汇报卡片](docs/PRESENTATION_BRIEF.md)
- [详细中文汇报稿与 17 页图文规划](docs/reports/OFFICE-AGENT-DETAILED-CHINESE-REPORT-20260825.md)
- [来源台账](docs/decisions/SOURCE_REGISTER.md)
- [DR-0022](docs/decisions/DR-0022-workspace-folder-and-arbitrary-task-contract.md)
- [SCENARIO-008](docs/scenarios/SCENARIO-008-whole-folder-office-workspace.md)
- [DR-0023：三轮只读 Agent Control Loop](docs/decisions/DR-0023-agent-control-loop.md)
- [SCENARIO-009：Agent 研究当前文件夹并提出下一步](docs/scenarios/SCENARIO-009-agent-control-loop.md)
- [DR-0024：整库自主研究与人工确认下一轮](docs/decisions/DR-0024-autonomous-whole-workspace-research.md)
- [SCENARIO-010：Agent 自主研究整个办公资料库](docs/scenarios/SCENARIO-010-autonomous-whole-workspace-research.md)
- [DR-0025：可恢复检查点、人工证据门与成果演进](docs/decisions/DR-0025-durable-evidence-gate-and-artifact-evolution.md)
- [SCENARIO-011：中断恢复与逐轮补证](docs/scenarios/SCENARIO-011-recover-and-confirm-evidence-round.md)
- [DR-0026：可选择任务分支与不可变成果历史](docs/decisions/DR-0026-selective-branch-and-immutable-artifact-history.md)
- [SCENARIO-012：按分支补证并恢复历史成果](docs/scenarios/SCENARIO-012-selective-branch-and-artifact-restore.md)
- [Demo 1 分支与成果控制 Evidence](docs/evidence/DEMO1-BRANCH-ARTIFACT-CONTROL-EVIDENCE-20260826.md)
- [DR-0027：本地启动状态库选择](docs/decisions/DR-0027-truthful-local-state-store-selection.md)
- [SCENARIO-013：真实的本地状态库回退](docs/scenarios/SCENARIO-013-truthful-local-state-store-fallback.md)
- [本地启动状态库优先级 Evidence](docs/evidence/START-DEMO-DSN-PRECEDENCE-EVIDENCE-20260826.md)
- [DR-0028：分层文件目录与问题审查页](docs/decisions/DR-0028-hierarchical-workspace-and-evidence-review.md)
- [SCENARIO-014：在原始资料中核对 Agent 问题](docs/scenarios/SCENARIO-014-inspect-agent-issue-in-context.md)
- [分层文件目录与问题审查页 Evidence](docs/evidence/WORKSPACE-TREE-AND-EVIDENCE-REVIEW-EVIDENCE-20260826.md)
- [DR-0029：服务端验证的证据锚点](docs/decisions/DR-0029-server-verified-evidence-anchors.md)
- [SCENARIO-015：定位并对照 Agent 证据](docs/scenarios/SCENARIO-015-pinpoint-and-compare-agent-evidence.md)
- [原文定位审查 Evidence](docs/evidence/PINPOINT-EVIDENCE-REVIEW-EVIDENCE-20260826.md)
- [DR-0030：可处置问题审查与可恢复分析门](docs/decisions/DR-0030-actionable-review-and-recoverable-analysis.md)
- [SCENARIO-016：从可定位问题到人工决断，并从分析失败继续](docs/scenarios/SCENARIO-016-actionable-finding-and-recoverable-analysis.md)
- [可处置问题与失败恢复 Evidence](docs/evidence/ACTIONABLE-REVIEW-AND-RECOVERY-EVIDENCE-20260826.md)
- [可恢复 Control Loop Evidence](docs/evidence/DURABLE-EVIDENCE-GATE-ARTIFACT-EVOLUTION-EVIDENCE-20260826.md)
- [整库自主研究 Evidence](docs/evidence/AUTONOMOUS-WHOLE-WORKSPACE-RESEARCH-EVIDENCE-20260825.md)
- [Agent Control Loop 三轮只读纵切证据](docs/evidence/AGENT-CONTROL-LOOP-BOUNDED-READONLY-EVIDENCE-20260825.md)
- [主流方案、办公场景与交互影响研究](docs/research/WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825.md)
- [Agent Control Loop 当前实现审计与下一纵切](docs/research/AGENT-CONTROL-LOOP-IMPLEMENTATION-AUDIT-20260825.md)
- [15 类办公测试目录](docs/testing/FORTE-PUBLIC-OFFICE-TASK-TEST-CASES-20260825.md)
- [公开数据套件清单](docs/research/FORTE-PUBLIC-SUITE-INVENTORY-20260825.md)

A dated historical document proves only its recorded commit and scope unless a
living document explicitly carries the fact forward.
