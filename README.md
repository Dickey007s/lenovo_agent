# Office Agent V0.2

Office Agent is a single FORTE-backed data workbench. A user can inspect public office files, choose the files in scope, write an original task, and follow a server-backed path from planning to a cited read-only result.

The current product can return a bounded analysis inside one memory Run. `completed` means the Planner passed structural plan checks and the Analyst response passed schema, selected-reference and read-only-boundary checks. It does not mean the conclusion is correct, or that a Tool Gateway, ArtifactVersion, Connector or external business action ran.

## Current product

The root page is the only product entry:

- left: three business-labeled FORTE collections, file search and explicit selection;
- center: real bounded table/Markdown preview, free-form task input, validated plan and “模型初步结论 · 待复核”; three findings are visible by default and the rest are user-expandable;
- right: eight ordered server events plus separate planning and analysis model receipts;
- boundary: selected public files are read-only, results require human review, and no external action occurs.

The Planner proposes business intent rather than internal side-effect enums. The server compiles that candidate into allowlisted operation semantics, then validates sources, tools, dependencies and gates. Model receipts say `未调用`, `已采用` or `校验未通过`; ordinary failures do not expose raw tool/effect identifiers.

The ordinary UI and Runtime contract are work-led rather than Demo-led. Public, internal and Planner Scenario projections use a generic `work_profile` (`task_topology`, `orchestration`, `control_requirements`, `current_runtime_scope`); they do not carry `demo_id` or `experience_policy`.

Demo 1/2/3 are acceptance lenses over the same Agent capabilities:

- Demo 1: one decomposed task, bounded checkpoint loop, evidence/human pause and later resume;
- Demo 2: multiple work units, adaptive scheduling and shared-artifact convergence;
- Demo 3: a cross-cutting risk/action gate applied to either topology, not a separate task engine.

The current `work_profile.current_runtime_scope` is always `read_only_analysis`. The current product does not yet execute the bounded loop, adaptive swarm or governed action path; those remain target architecture under [DR-0019](docs/decisions/DR-0019-capability-composed-agent-runtime.md).

Legacy mail, document, quote, task, calendar, expense, CRM, audit and fixed Customer A runtimes remain retired. Historical decisions and Evidence retain their recorded facts; current applicability is governed by [DR-0018](docs/decisions/DR-0018-forte-data-workbench-and-verifiable-trace.md) and the [retirement register](docs/decisions/RETIREMENT_REGISTER.md).

## Evidence status

DR-0018 is `Limited Verified` for implementation [`fffa36a8cc83e895aaba35276568ad79e348f541`](https://github.com/Dickey007s/lenovo_agent/commit/fffa36a8cc83e895aaba35276568ad79e348f541) plus result-review follow-up [`041186d`](https://github.com/Dickey007s/lenovo_agent/commit/041186d), delivered in open [PR #25](https://github.com/Dickey007s/lenovo_agent/pull/25):

- public OpenAPI surface: seven paths, including bounded file preview;
- focused Catalog/Runtime Python suite: `30 passed in 2.46s`;
- current focused Harness browser run: `8 passed in 26.8s`;
- one observed Finance-018 live Run: `harness:8c9b10d493004bd9aac305c294f48fa6`, `completed` v9/seq 8;
- Planner: `deepseek-v4-pro`, `14685 ms`, called and adopted;
- Analyst: `deepseek-v4-pro`, `18041 ms`, called and adopted;
- result: 10 findings, citations limited to two selected stable `file_ref` values, `review_required=true`, external side effect `none`.

A deterministic regression over the same safe previews found 23 unchanged balances totaling `1,845,444.71`; the live model Snapshot stated 20 and `2,202,000`. This preserved negative result proves why citation membership is not answer correctness. The current build and three final-UI screenshots are registered in the Evidence with their distinct live/replay provenance. Final verification is Python `53 passed in 2.68s`, Ruff and web lint passed, and the production build passed (`2.5s` compile, `4.4s` TypeScript, `810ms` static generation). There is no target-user study.

DR-0019 is separately `Limited Verified` for implementation [`eef656e`](https://github.com/Dickey007s/lenovo_agent/commit/eef656e): the current public/internal/Planner contract contains no Demo identity and exposes strict generic work profiles. Focused Python is `30 passed in 2.56s`, full Python is `53 passed in 2.51s`, Harness browser E2E is `8 passed in 52.5s`, and Ruff/lint/build pass. This is contract evidence only, not evidence that bounded execution, adaptive self-organization or governed action already runs.

DR-0020 is `Limited Verified` for implementation [`373b79a`](https://github.com/Dickey007s/lenovo_agent/commit/373b79a): server-owned policy compilation now sits between the model candidate and the plan validator. A final live browser Run reached `completed` v9/seq 8 with Planner `15059 ms` and Analyst `13443 ms`, both adopted, while ordinary DOM contained neither `artifact.write` nor `run_workspace_write`. Current verification is full Python `56 passed in 2.57s`, Harness browser E2E `8 passed in 25.1s`, Ruff/lint/build passed. This does not prove plan or answer quality.

## Current flow

```text
FORTE manifest and bytes
  -> safe Scenario list
  -> bounded file preview
  -> user instruction + selected file_ref values
  -> deepseek-v4-pro Planner
  -> server-owned policy compilation
  -> deterministic plan validation
  -> deepseek-v4-pro read-only Analyst over safe previews
  -> deterministic citation-scope validation
  -> memory Snapshot + ordered SSE
  -> completed, review_required=true, external_side_effect=none
```

The success path emits:

```text
workspace_index
planning_started
planning_completed
plan_validation
analysis_started
analysis_completed
result_validation
task_completed
```

Model call, output adoption, plan validation, result citation validation and task completion are separate facts.

## Data and citation boundary

The FORTE source is pinned to commit `345c1ec1487139db9dd319787fa9405ba85d1869` under the upstream top-level MIT license. Two inventories deliberately coexist:

- `public-suite-manifest.json` binds the complete public repository demo suite: 15 task records plus 96 input files, 111 files and `1780445` bytes;
- the current runtime `manifest.json` binds 8 inputs plus 3 raw task records: 11 files and `115352` bytes for the three product scenarios.

The official repository reports a 180-task benchmark but publishes only one demo per profession. The complete public suite is downloaded for staged testing; the product does not claim access to the unpublished tasks or runtime support for every downloaded format.

Each input gets a stable opaque `file_ref`. The preview endpoint revalidates the manifest and exposes only:

- first visible XLSX sheet, at most 30 columns and 120 data rows; or
- at most 30,000 characters from an allowlisted input Markdown file.

Public API/DOM/model analysis input excludes filesystem path, SHA-256, raw task instruction, rubric, solution and grading material. Prompt, chain of thought and raw model responses are not exposed.

Every finding must cite one or more selected `file_ref` values. This proves reference membership only; it does not prove that the narrative or calculation is semantically correct, exhaustive or arithmetically valid. The current server does not recompute spreadsheet claims. Human review is mandatory; a deterministic spreadsheet operator and claim verifier remain target architecture.

## Seven-path API

```text
GET  /v1/health
GET  /v1/harness/scenarios
GET  /v1/harness/scenarios/{scenario_id}
GET  /v1/harness/scenarios/{scenario_id}/files/{file_ref}
POST /v1/harness/runs
GET  /v1/harness/runs/{run_id}
GET  /v1/harness/runs/{run_id}/events?after={sequence}
```

`POST /runs` accepts `scenario_id`, optional user `instruction`, optional `selected_file_refs`, `expected_version` and `idempotency_key`. Unknown or cross-Scenario refs fail closed. Unknown start outcomes reuse the same command key.

`X-User-Id` remains an unsigned demonstration placeholder. Runs, results, receipts, events and idempotency records are single-process memory and disappear on API restart.

## Eight modules

1. Scenario Pack & Workspace Catalog
2. Task Contract
3. Planner
4. Admission & Plan Validator
5. Scheduler & Worker Manager
6. Tool Gateway
7. Artifact Workspace & Verifier
8. Checkpoint, Event & Governance Control

Current implementation covers modules 1-4, a bounded result/citation subset of module 7, and the memory event/idempotency subset of module 8. Scheduler/Worker, Tool Gateway invocation, versioned Artifact/Commit, durable checkpointing and governed external action remain target architecture.

## Local run

Requirements:

- Python `>=3.12,<3.13`
- Node.js and pnpm compatible with the lockfile
- an OpenAI-compatible `/chat/completions` endpoint

```dotenv
LLM_BASE_URL=https://your-openai-compatible-endpoint.example/v1
LLM_API_KEY=replace-me
LLM_MODEL=deepseek-v4-pro
```

Never commit `.env`, API keys, production credentials or real customer information.

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

## Living documentation

- [Architecture](docs/ARCHITECTURE.md)
- [HTTP API and SSE](docs/API.md)
- [Worksite and streaming](docs/WORKSPACE_AND_STREAMING.md)
- [Governance and action boundary](docs/GOVERNANCE_AND_ACTIONS.md)
- [UI—server fact matrix](docs/contracts/UI_SERVER_FACT_MATRIX.md)
- [Target architecture](docs/TARGET_ARCHITECTURE.md)
- [Presentation brief](docs/PRESENTATION_BRIEF.md)
- [Decision/reporting governance](docs/DECISION_AND_REPORTING_GOVERNANCE.md)
- [Source register](docs/decisions/SOURCE_REGISTER.md)
- [DR-0018](docs/decisions/DR-0018-forte-data-workbench-and-verifiable-trace.md)
- [DR-0018 Evidence](docs/evidence/FORTE-DATA-WORKBENCH-TRACE-EVIDENCE-20260824.md)
- [DR-0019](docs/decisions/DR-0019-capability-composed-agent-runtime.md)
- [DR-0019 Evidence](docs/evidence/AGENT-CAPABILITY-COMPOSITION-EVIDENCE-20260824.md)
- [DR-0021 public suite expansion](docs/decisions/DR-0021-forte-public-suite-expansion.md)
- [15-case office test catalog](docs/testing/FORTE-PUBLIC-OFFICE-TASK-TEST-CASES-20260825.md)
- [public suite inventory](docs/research/FORTE-PUBLIC-SUITE-INVENTORY-20260825.md)

A dated historical document is not a current product contract unless a living doc explicitly says so.
