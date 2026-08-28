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
boundary checks. Separately, 12 fixed local office capabilities can now produce
real isolated run-workspace files with deterministic verifier receipts. Neither
fact means an arbitrary answer is correct, a FORTE source was changed or an
external business action happened.

## Current product

The root page is the only product entry:

- left: one searchable, collapsible folder tree containing all 96 public FORTE
  input files, with file-type filters and no role or Demo partition;
- center: file metadata, CSV/XLSX/PDF/DOCX/TXT/code preview, a free-form task
  composer, loop budget, round history, server-owned task branches, evidence
  gaps, controls, append-only result history, real run-workspace Artifact
  downloads and verifier receipts, a cited read-only brief and up to four
  proposed next tasks;
- right: current phase, ordered server events and separate Planner/Analyst
  adoption receipts;
- boundary: the Run freezes the complete allowlisted index; each round exposes
  only the Agent-selected, server-budgeted files to analysis. Originals stay
  read-only, results require review and no external action occurs.

The default complete-task budget is 12 rounds, 16 files per round, 30 model
calls and 7,200 Agent-active seconds. Public maxima are 24/24/60/14,400. Human
review in `waiting_input` and an explicit pause do not consume active time. The
four caps remain independent.

The primary flow is:

```text
browse or search the whole repository
  -> inspect safe file preview
  -> author an original task
  -> freeze a whole-workspace AgentControlLoopContract and budget
  -> deepseek-v4-pro Planner selects a minimal evidence set and explains why
  -> server compiles and validates scope, tools, dependencies and effects
  -> an admitted deterministic office tool may write a real isolated Artifact
  -> server verifies fields/numbers/order/rules/tests and records an EffectReceipt
  -> deepseek-v4-pro Analyst reads the approved safe projections
  -> Analyst separates fact, impact and human decision options, then returns exact quote candidates
  -> server uniquely resolves safe-preview locations and keeps only reviewable findings
  -> server validates citation membership, evidence anchors and the Evidence Gate
  -> location/structure cannot be adopted: one bounded repair, then preserve valid work and pause one branch
  -> retry-only gap shows one recommended Branch action; optional clues and audit details stay collapsed
  -> ambiguous quote requires the user to choose one real source position before Branch recovery
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

## Eight-path API

```text
GET  /v1/health
GET  /v1/harness/workspace
GET  /v1/harness/workspace/files/{file_ref}
POST /v1/harness/runs
GET  /v1/harness/runs?limit={1..20}
GET  /v1/harness/runs/{run_id}
GET  /v1/harness/runs/{run_id}/artifacts/{artifact_id}
POST /v1/harness/runs/{run_id}/controls
GET  /v1/harness/runs/{run_id}/events?after={sequence}
```

The former Scenario list/detail routes are not mounted. There are nine public
operations over eight OpenAPI paths because `GET` and `POST` share `/runs`.
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
subset of module 5; a 12-capability deterministic local adapter subset of
module 6; a read-only result, citation, Evidence Gate, logical append-only
ArtifactVersion, TaskCommit pointer/restore, isolated run-workspace file and
deterministic verifier subset of module 7;
and a Snapshot/event, branch control, idempotency and optional PostgreSQL
restart-recovery subset of module 8. Distributed Worker scheduling, a general
Tool Gateway, arbitrary source-file mutation, general semantic verification,
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
- `DR-0031` raises the default active deadline from 120 to 1,200 seconds and
  excludes human waiting/pause from elapsed time. It also replaces vague
  “missing evidence” copy with an Agent-owned recovery sheet: failure type,
  affected Branch, attempted files, call/adoption receipt, preserved work and a
  direct “retry only this Branch” action. Terminal Runs create a new task rather
  than pretending to resume. A sanitized real `deepseek-v4-pro` run records a
  12-second human wait with unchanged active elapsed, followed by one-Branch
  recovery and completion; this is control-path evidence, not an answer-quality
  claim.
- `DR-0032` makes evidence ambiguity and human decisions recoverable server facts.
  `EvidenceResolution` now emits `exact/ambiguous/unavailable/stale/rejected`;
  `DecisionRequest/DecisionRecord` bind the current source revision, candidate,
  Branch, expected version and idempotency receipt. A real PostgreSQL 17.11 gate
  proves that an open three-candidate decision survives restart, accepting one
  candidate resumes only its Branch, preserves v1 and appends v2. These records
  remain nested in Snapshot JSONB, not an independently queryable decision ledger;
  no database CAS, multi-instance lease or in-flight model replay is claimed.
- `DR-0033` fixes the front-end projection of that contract. Open
  `DecisionRequest` packets come from the Snapshot top level; closing a review
  exits immediately and only then attempts a truthful `defer` receipt, so a 409
  can never trap the user. Evidence Gaps are shown as Branch lanes connecting
  Branch, current materials, Evidence Gate and next action. This is a UI fact
  projection, not proof of parallel Workers or improved user outcomes.
- `DR-0034` separates two human jobs that previously looked alike. A retry-only
  Branch now presents one recommended action without requiring file edits or
  input; optional clues and audit details are collapsed. An ambiguous source
  Branch instead requires an explicit candidate choice and keeps accept disabled
  until the user selects one real location. No Runtime protocol or budget rule
  changed, and the claimed clarity benefit remains a user-study hypothesis.
- `DR-0035` replaces the fixed three-round product assumption with a 12-round
  default and adds a Scenario Effect Gate. Twelve local FORTE tasks now generate
  real CSV/Markdown/DOCX/ZIP files in an isolated Run Workspace with deterministic
  checks and Owner-scoped download; three SQL/Web/Scheduler tasks stay
  `blocked_external_boundary`. The first real six-scenario run failed `0/6` and
  is retained; after moving deterministic work before Analyst narration and
  simplifying the model contract, all six priority effects passed. Model
  adoption, deterministic effect and Run terminal status remain separate facts.
- `DR-0036` fixes the TC-01 state where a 5/5 verified CSV looked unfinished
  because PDF layout wrapped “技术研发” across two Preview lines. The server now
  permits a punctuation/whitespace-insensitive fallback only after strict matching
  fails and still requires a unique location; repeated matches remain ambiguous.
  Findings whose verified observed dates all fall outside the explicit instruction
  window are omitted, and a human Gate without an exact contradiction Anchor is
  suppressed. When a historical Snapshot still has an audit-location gap, the UI
  shows the verified outcome first and groups duplicate same-source/same-failure
  gaps without changing server Branch state.
- `DR-0037` separates TC-05 task context from each file's content semantics.
  The two CSV cards now state that they contain 2026 ending-balance records,
  while only the cross-period note carries all three periods and zombie-account
  checks. Artifact cards expose server-owned period, basis, purpose and optional
  record count; review body text, evidence excerpts and safe previews are larger
  on desktop and 390 px. This remains one fixed Finance-018 adapter, not a
  general finance verifier or proof of improved user understanding.
- `DR-0038` turns a remaining `source_location` gap into one user task instead
  of a wall of Runtime terms. A verified result says that files are already
  generated and one Agent explanation still lacks a row/cell location; its
  primary action resumes only the affected Branch. Unverified and terminal Runs
  use different wording and never borrow the verified-result claim.
- `DR-0039` makes TC-10 distinguish a flow-design DOCX from external execution.
  The service-owned Artifact now states its type, M1 scope, source basis, six
  terminal states, review reason and execution boundary. The result area and
  task close both say that dialing, CRM writes and SMS did not occur. The
  downloaded DOCX repeats that boundary before its complete flow. This remains
  one fixed Operations-008 adapter, not a general outbound engine.
- `DR-0040` replaces TC-02's historical 9-file mini package with a refactor of
  the complete algorithm-013 project copy. The ZIP now retains every real input,
  includes a unified diff, machine-readable changes, Chinese review notes, a
  self-test card and manifest-matched test receipts. The main entry uses a
  bounded ReAct action/observation controller while the original Workflow, LLM
  and ToolRegistry contracts remain reviewable. Its default policy
  deterministically steps through planned tools behind a replaceable
  `action_policy`; it does not prove model-driven action selection inside the
  downloaded project. The outer Planner/Analyst provider calls are separate
  facts. Both deliverables project the same twelve verifier `check_id` values;
  Run-level UI and receipts therefore report one shared 12-item checklist rather
  than inflating it to 24 checks. This is one fixed adapter, not an arbitrary code
  sandbox, automatic PR path or OS-level network isolation.
- `DR-0041` replaces TC-04's historical 105-test `contracts.py` false green
  with the complete 44-file dev-015 project copy. The same 117 named tests run
  before and after three real-source fixes; the unpatched copy must expose five
  target failures, while the fixed copy must pass 117/117 and keep each changed
  file above 80% statement coverage. The self-test card shows five real suites,
  files, counts and expandable collected IDs from the same public manifest used
  by the ZIP. Before the roughly one-minute builder starts, the Runtime freezes
  all 46 allowlisted inputs and persists a started event; the synchronous build
  and test subprocesses then run through an in-process worker thread so health,
  Run GET, workspace browsing and SSE remain available. A duplicate dispatch for
  the same Run/capability is ignored, and failure emits `scenario_effect_failed`
  without a green Artifact. This remains one fixed adapter, not an arbitrary
  test sandbox, OS-level network isolation, real endpoint integration, automatic
  PR path, multi Worker scheduler or resumable Tool Gateway.
- `DR-0042` replaces TC-12's historical repair-only 9/9 Vitest receipt with the
  complete 11-file qa-003 dashboard-toolkit copy and one manifest-owned 71-case
  test set. The same tests first expose the original alias failure, then the
  growth, sorting and date-boundary defects across three red stages, before the
  four-file fix passes 71/71. Three changed business modules each have their own
  V8 statements/lines >=85% and branches >=75% gate. The ZIP includes the full
  copy, unified diff, stage JSON, coverage, real test IDs and an independently
  rerun self-test. This remains a fixed qa-003 adapter, not an arbitrary
  JavaScript sandbox, OS-level network isolation, automatic PR or production
  multi-tenant execution.
- `DR-0043` replaces TC-11's historical name-list risk check with a strict
  four-source contract and an 18-row service-owned ledger. Risk levels now
  derive from PRD priority, test reason and compatibility exceptions; four
  formal business Gates retain numerator, denominator, operator and threshold.
  The UI can therefore show two simultaneous truths: both files passed nine
  deterministic source/formula/structure checks, while the business decision is
  still `4/4 Gates failed -> 不得上线`. This remains one fixed pm-014 adapter; it
  does not execute a release, write configuration or prove a general release
  audit engine.
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
The current active-budget and Agent-gap recovery increment is tracked in
[`ACTIVE-BUDGET-AND-AGENT-GAP-RECOVERY-20260826`](docs/evidence/ACTIVE-BUDGET-AND-AGENT-GAP-RECOVERY-EVIDENCE-20260826.md).
The current exact evidence-location interaction is tracked in
[`PINPOINT-EVIDENCE-REVIEW-20260826`](docs/evidence/PINPOINT-EVIDENCE-REVIEW-EVIDENCE-20260826.md).
The current actionable review and recoverable-analysis interaction is tracked in
[`ACTIONABLE-REVIEW-AND-RECOVERY-20260826`](docs/evidence/ACTIONABLE-REVIEW-AND-RECOVERY-EVIDENCE-20260826.md).
The current persistent decision and Finding/Branch-local recovery increment is tracked in
[`DR-0032-POSTGRES-DECISION-RECOVERY-EVIDENCE-20260827`](docs/evidence/DR-0032-POSTGRES-DECISION-RECOVERY-EVIDENCE-20260827.md).
The current closable-review and Branch-lane interaction increment is tracked in
[`DR-0033-CLOSABLE-REVIEW-BRANCH-LANES-EVIDENCE-20260827`](docs/evidence/DR-0033-CLOSABLE-REVIEW-BRANCH-LANES-EVIDENCE-20260827.md).
The current one-action recovery and explicit source-choice increment is tracked in
[`DR-0034-ONE-ACTION-RECOVERY-EVIDENCE-20260827`](docs/evidence/DR-0034-ONE-ACTION-RECOVERY-EVIDENCE-20260827.md).
The current TC-01 outcome-first and evidence-localization increment is tracked in
[`DR-0036-TC01-OUTCOME-EVIDENCE-LOCALIZATION-EVIDENCE-20260828`](docs/evidence/DR-0036-TC01-OUTCOME-EVIDENCE-LOCALIZATION-EVIDENCE-20260828.md).
The current TC-05 artifact-semantics and review-readability increment is tracked in
[`DR-0037-TC05-ARTIFACT-SEMANTICS-AND-REVIEW-READABILITY-EVIDENCE-20260828`](docs/evidence/DR-0037-TC05-ARTIFACT-SEMANTICS-AND-REVIEW-READABILITY-EVIDENCE-20260828.md).
The source-location user-language and local-recovery increment is tracked in
[`DR-0038-USER-LANGUAGE-SOURCE-LOCATION-RECOVERY-EVIDENCE-20260828`](docs/evidence/DR-0038-USER-LANGUAGE-SOURCE-LOCATION-RECOVERY-EVIDENCE-20260828.md).
The current TC-11 source-derived release Gate increment is tracked in
[`DR-0043-TC11-DERIVED-RELEASE-GATES-EVIDENCE-20260828`](docs/evidence/DR-0043-TC11-DERIVED-RELEASE-GATES-EVIDENCE-20260828.md).

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
- [可证伪竞争差异、八个同场挑战与前台影响研究](docs/research/COMPETITIVE-WHITE-SPACE-AND-FALSIFIABLE-DIFFERENTIATORS-20260826.md)
- [可处置人工决策与失败恢复研究](docs/research/ACTIONABLE-HUMAN-DECISION-AND-FAILURE-RECOVERY-20260826.md)
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
- [DR-0036：成果优先、版面容错定位与任务范围收敛](docs/decisions/DR-0036-outcome-first-and-layout-tolerant-evidence.md)
- [SCENARIO-022：成果已验证时，把来源定位作为独立审计项](docs/scenarios/SCENARIO-022-verified-outcome-and-audit-location.md)
- [TC-01 成果与引用定位 Evidence](docs/evidence/DR-0036-TC01-OUTCOME-EVIDENCE-LOCALIZATION-EVIDENCE-20260828.md)
- [DR-0037：TC-05 成果语义与问题审查可读性](docs/decisions/DR-0037-tc05-artifact-semantics-and-review-readability.md)
- [SCENARIO-023：在下载前理解财务成果并清楚审查证据](docs/scenarios/SCENARIO-023-understand-finance-artifacts-and-review-evidence.md)
- [TC-05 成果语义与审查可读性 Evidence](docs/evidence/DR-0037-TC05-ARTIFACT-SEMANTICS-AND-REVIEW-READABILITY-EVIDENCE-20260828.md)
- [DR-0038：用用户任务语言呈现原表格位置恢复](docs/decisions/DR-0038-user-language-source-location-recovery.md)
- [SCENARIO-024：理解并恢复缺少的原表格位置](docs/scenarios/SCENARIO-024-understand-and-recover-missing-table-location.md)
- [原表格位置用户语言与局部恢复 Evidence](docs/evidence/DR-0038-USER-LANGUAGE-SOURCE-LOCATION-RECOVERY-EVIDENCE-20260828.md)
- [DR-0043：TC-11 来源推导风险、正式业务 Gate 与双状态前台](docs/decisions/DR-0043-tc11-derived-release-gates.md)
- [SCENARIO-029：从四份发布资料推导上线 Gate 并审查整改计划](docs/scenarios/SCENARIO-029-review-derived-release-gates.md)
- [TC-11 来源推导上线 Gate Evidence](docs/evidence/DR-0043-TC11-DERIVED-RELEASE-GATES-EVIDENCE-20260828.md)
- [可恢复 Control Loop Evidence](docs/evidence/DURABLE-EVIDENCE-GATE-ARTIFACT-EVOLUTION-EVIDENCE-20260826.md)
- [整库自主研究 Evidence](docs/evidence/AUTONOMOUS-WHOLE-WORKSPACE-RESEARCH-EVIDENCE-20260825.md)
- [Agent Control Loop 三轮只读纵切证据](docs/evidence/AGENT-CONTROL-LOOP-BOUNDED-READONLY-EVIDENCE-20260825.md)
- [主流方案、办公场景与交互影响研究](docs/research/WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825.md)
- [Agent Control Loop 当前实现审计与下一纵切](docs/research/AGENT-CONTROL-LOOP-IMPLEMENTATION-AUDIT-20260825.md)
- [15 类办公测试目录](docs/testing/FORTE-PUBLIC-OFFICE-TASK-TEST-CASES-20260825.md)
- [公开数据套件清单](docs/research/FORTE-PUBLIC-SUITE-INVENTORY-20260825.md)

A dated historical document proves only its recorded commit and scope unless a
living document explicitly carries the fact forward.
