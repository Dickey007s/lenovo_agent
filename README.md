# Office Agent V0.2

Office Agent is now a single FORTE-backed worksite for inspecting public office files, generating a model-proposed work graph, validating that graph deterministically, and showing the resulting server facts in the frontend.

The current product is a planning vertical slice. It stops at `ready_to_execute`: no Worker, tool, Artifact mutation, approval, Permit, Connector, or external side effect is executed.

## Current product

The root page is the only product entry. It contains:

- a source workspace with safe file labels and summaries;
- three FORTE scenarios for durable evidence work, adaptive collaboration, and governed action design;
- a public task contract and dynamic plan graph;
- a right-side Agent activity rail driven by Snapshot and ordered SSE facts;
- explicit service, Catalog, integrity, retry, model-call, adoption, validation, and not-executed states.

The previous mail, document, quote, task, calendar, expense, CRM, audit, Task Runtime, cockpit, and fixed action-gate products are retired. Their current-tree frontend components, API routes, services, tests, and `demo-enterprise-data/customer-a/` files have been removed. Historical decisions and evidence remain in Git and under `docs/`, with lifecycle status in [`RETIREMENT_REGISTER.md`](docs/decisions/RETIREMENT_REGISTER.md).

## Evidence status

[`DR-0017`](docs/decisions/DR-0017-single-forte-worksite-and-legacy-retirement.md) is `Limited Verified` only for the current engineering surface:

- implementation commits [`b2b759b106738fbb3aed597319208e8ff4718cc7`](https://github.com/Dickey007s/lenovo_agent/commit/b2b759b106738fbb3aed597319208e8ff4718cc7) and [`5fab10fb4f638958ff78b39583a4eace2e99396b`](https://github.com/Dickey007s/lenovo_agent/commit/5fab10fb4f638958ff78b39583a4eace2e99396b);
- [PR #24](https://github.com/Dickey007s/lenovo_agent/pull/24), open and unmerged at evidence capture;
- fresh-clone verification at `5fab10f...`: 11 FORTE files, `115352` bytes, zero size/hash mismatches, no Customer A path;
- OpenAPI contains six paths; legacy workspace/thread/task/Demo prefixes return 404;
- Python `47 passed in 2.42s`, Ruff passed, web lint passed, production build passed, Harness browser E2E `11 passed in 41.4s`;
- one observed Finance-018 `deepseek-v4-pro` run reached v6/seq 5 `ready_to_execute`, generated 10 plan units in `16838 ms`, and recorded `called=true/output_used=true` with no tool or external action.

There is no new independent screenshot of the final converged UI. The new PNG in DR-0017 Evidence is the stakeholder's negative pre-fix capture. E2E is an engineering proxy, not a screenshot review or user study. Exact facts and boundaries are in [`FORTE-ONLY-WORKSITE-RETIREMENT-EVIDENCE-20260824`](docs/evidence/FORTE-ONLY-WORKSITE-RETIREMENT-EVIDENCE-20260824.md).

## Three scenarios

| Demo policy | FORTE source | Current capability | Still Draft |
| --- | --- | --- | --- |
| Demo 1: durable evidence task | `Finance-018`, three period workbooks | safe source projection, task contract, real-model plan, deterministic validation | execution loop, checkpoints across restart, evidence table, conflict/branch/Commit |
| Demo 2: adaptive collaboration | `pm-014`, PRD plus three test/config workbooks | dynamic dependency plan from four files | Scheduler, Worker execution, replan, shared Artifact convergence |
| Demo 3: governed action | `Operations-008`, professional process requirements | plan units can declare human-gated external-action candidates | Risk/Evidence/Approval/Permit/Simulator execution in the FORTE worksite |

The old Customer A 4-Worker/5-Artifact run, quote calculation, and email Simulator paths are historical vertical slices. They cannot be copied into a current FORTE run claim.

## Architecture

```text
Browser: single FORTE worksite
  -> FastAPI: six public paths
  -> BenchmarkScenarioCatalog
       -> pinned manifest / bytes / license
       -> safe public Scenario projection
       -> private sanitized Planner context
  -> HarnessRuntime
       -> Workspace index
       -> deepseek-v4-pro Planner candidate
       -> deterministic Plan Validator
       -> memory Snapshot + ordered events + idempotency result
  -> public Snapshot / SSE projection
  -> ready_to_execute
```

The eight canonical Harness modules are:

1. Scenario Pack & Workspace Catalog
2. Task Contract
3. Planner
4. Admission & Plan Validator
5. Scheduler & Worker Manager
6. Tool Gateway
7. Artifact Workspace & Verifier
8. Checkpoint, Event & Governance Control

Only the planning slice of modules 1-4 and the memory event/control subset of module 8 are current product facts. Modules 5-7 and durable/governed execution remain target architecture.

## API

OpenAPI exposes exactly:

```text
GET  /v1/health
GET  /v1/harness/scenarios
GET  /v1/harness/scenarios/{scenario_id}
POST /v1/harness/runs
GET  /v1/harness/runs/{run_id}
GET  /v1/harness/runs/{run_id}/events?after={sequence}
```

`X-User-Id` is an unsigned demonstration owner placeholder. Harness Run, event, planning task, and idempotency state are single-process memory and disappear on API restart.

## Source boundary

The application reads a vendored, pinned subset of [AGI-Eval-Official/FORTE](https://github.com/AGI-Eval-Official/FORTE) at commit `345c1ec1487139db9dd319787fa9405ba85d1869`, under the upstream top-level MIT license. The local manifest binds 8 input files plus 3 raw `task.md` provenance records, 11 files and `115352` bytes total.

Vendored task/input bytes are marked binary so Git does not normalize upstream CRLF Markdown. Catalog validation checks allowlist, path boundary, symlink, size, hash, supported type, and parser constraints before planning. Integrity failure returns controlled 503 and the UI shows a Catalog-specific recovery state.

Raw `task.md`, sanitized Planner context, rubric, solution, grading metadata, absolute paths, and complete hashes do not enter the public API or ordinary DOM. FORTE is public benchmark input, not Lenovo data, a real customer folder, an enterprise database, or a live Connector.

## Local run

Requirements:

- Python `>=3.12,<3.13`
- Node.js and pnpm compatible with the locked frontend
- an OpenAI-compatible `/chat/completions` endpoint

Create `.env` from `.env.example` and configure the existing model:

```dotenv
LLM_BASE_URL=https://your-openai-compatible-endpoint.example/v1
LLM_API_KEY=replace-me
LLM_MODEL=deepseek-v4-pro
```

Never commit `.env`, API keys, production credentials, or real customer information.

Start and stop:

```powershell
.\scripts\start-demo.ps1
.\scripts\stop-demo.ps1
```

Default addresses:

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

Current PR #24 evidence: Python `47 passed in 2.42s`; Harness E2E `11 passed in 41.4s`; Ruff, lint, and build passed. These numbers describe the smaller current Harness product and retained safety primitives. They do not include tests for retired products.

## Living documentation

- [Architecture](docs/ARCHITECTURE.md)
- [HTTP API and SSE](docs/API.md)
- [Worksite and streaming behavior](docs/WORKSPACE_AND_STREAMING.md)
- [Current governance and action boundary](docs/GOVERNANCE_AND_ACTIONS.md)
- [UI to server fact matrix](docs/contracts/UI_SERVER_FACT_MATRIX.md)
- [Target architecture and eight modules](docs/TARGET_ARCHITECTURE.md)
- [Presentation brief](docs/PRESENTATION_BRIEF.md)
- [Decision and reporting governance](docs/DECISION_AND_REPORTING_GOVERNANCE.md)
- [Source register](docs/decisions/SOURCE_REGISTER.md)
- [DR-0016 FORTE Harness foundation](docs/decisions/DR-0016-public-workspace-agent-harness.md)
- [DR-0017 product convergence](docs/decisions/DR-0017-single-forte-worksite-and-legacy-retirement.md)
- [Retirement register](docs/decisions/RETIREMENT_REGISTER.md)

Historical docs and presentation exports are retained for audit. A dated historical document is not a current product contract unless a living doc explicitly says so.
