# Office Agent V0.2

Office Agent is one FORTE-backed office folder, not a gallery of registered
Demo scenarios. A user can browse public office files, inspect a bounded safe
preview, select files across folders, write an original task and follow a
server-backed path from planning to a cited read-only result.

The current product is deliberately narrow. `completed` means the Planner
candidate passed server policy/structure checks and the Analyst response passed
schema, selected-reference and read-only-boundary checks. It does not mean the
answer is correct, a file was changed or an external business action happened.

## Current product

The root page is the only product entry:

- left: one searchable office folder tree with 15 public FORTE task folders
  and 96 input files;
- center: file metadata, CSV/XLSX/PDF/DOCX/TXT/code preview, selected-file
  chips, a free-form task composer, validated plan and cited initial result;
- right: ordered server events and separate Planner/Analyst call receipts;
- boundary: only selected files enter the Run, originals stay read-only,
  results require review and no external action occurs.

The primary flow is:

```text
browse folders
  -> inspect safe file preview
  -> select 1-20 files
  -> author an original task
  -> deepseek-v4-pro Planner proposes business intent
  -> server compiles and validates policy
  -> deepseek-v4-pro Analyst reads selected safe projections
  -> server validates citation membership
  -> ordered SSE + authoritative memory Snapshot
  -> initial result, review_required=true, external side effect none
```

Model receipts distinguish `未调用`, `已采用` and `未采用`. A returned model
response that fails server validation is not presented as success. Ordinary UI
hides Prompt, chain-of-thought, raw provider response, absolute path, digest,
benchmark task/rubric/solution and internal effect/gate identifiers.

## General Agent, three acceptance lenses

Demo names do not unlock capability or select private code paths:

- Demo 1 tests a decomposed single task, bounded loop, evidence/human pause and
  later resume;
- Demo 2 tests multiple work units, adaptive scheduling and shared-artifact
  convergence;
- Demo 3 applies a cross-cutting risk/action gate to either topology.

The current Runtime is still `read_only_analysis`. Bounded execution,
adaptive Workers, versioned Artifact/Commit and governed actions are target
architecture, not current claims.

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
does not enter ordinary UI or model-selected context. The user must supply an
instruction and explicit selected file refs.

## Six-path API

```text
GET  /v1/health
GET  /v1/harness/workspace
GET  /v1/harness/workspace/files/{file_ref}
POST /v1/harness/runs
GET  /v1/harness/runs/{run_id}
GET  /v1/harness/runs/{run_id}/events?after={sequence}
```

The former Scenario list/detail routes are not mounted. `X-User-Id` remains an
unsigned demonstration Owner placeholder. Runs, receipts, events and
idempotency records live in one API process memory and disappear on restart.

## Eight modules

1. Workspace Catalog & Safe Preview
2. Task Contract
3. Planner
4. Admission, Policy Compiler & Plan Validator
5. Scheduler & Worker Manager
6. Tool Gateway
7. Artifact Workspace & Verifier
8. Checkpoint, Event & Governance Control

Current implementation covers modules 1-4, a bounded result/citation subset of
module 7 and the memory event/idempotency subset of module 8. Modules 5-6,
writable versioned Artifact/Commit, durable checkpointing and governed external
action remain target work.

## Evidence status

- `DR-0021` is `Limited Verified` for importing and inventorying the complete
  pinned public demo suite.
- `DR-0022` is `Limited Verified` for the one-folder product, 96 safe previews,
  arbitrary selected-file task and current browser path. Implementation
  [`0794648`](https://github.com/Dickey007s/lenovo_agent/commit/0794648477ad0061a5460127af8800a021019366)
  and stacked [PR #27](https://github.com/Dickey007s/lenovo_agent/pull/27) are
  bound; the PR is open and this is not a merged-state claim.
- Current checks: focused Python `26 passed`, full Python `51 passed`, Harness
  browser `8 passed`; Ruff, frontend typecheck, production build, governance,
  local-link and diff checks pass. A real configured-model browser run recorded
  `8.7 s` planning and `16.7 s` analysis before the review-required result.
- No target-user study has been run. Clarity, trust, efficiency and user value
  remain hypotheses.

Detailed claims and limits live in
[`FORTE-FOLDER-WORKSPACE-EVIDENCE-20260825`](docs/evidence/FORTE-FOLDER-WORKSPACE-EVIDENCE-20260825.md).

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
- [主流方案、办公场景与交互影响研究](docs/research/WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825.md)
- [Agent Control Loop 当前实现审计与下一纵切](docs/research/AGENT-CONTROL-LOOP-IMPLEMENTATION-AUDIT-20260825.md)
- [15 类办公测试目录](docs/testing/FORTE-PUBLIC-OFFICE-TASK-TEST-CASES-20260825.md)
- [公开数据套件清单](docs/research/FORTE-PUBLIC-SUITE-INVENTORY-20260825.md)

A dated historical document proves only its recorded commit and scope unless a
living document explicitly carries the fact forward.
