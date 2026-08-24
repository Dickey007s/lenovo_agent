# DR-0017: Single FORTE worksite and legacy runtime retirement

| Field | Value |
| --- | --- |
| Decision ID | `DR-0017` |
| Date | 2026-08-24 |
| Status | `Limited Verified` for the current product surface and bounded recovery paths; user value remains `Draft` |
| Trigger | `USER-FEEDBACK-20260824-FORTE-ONLY-09` |
| Scenarios | [`SCENARIO-004`](../scenarios/SCENARIO-004-forte-finance-durable-evidence.md), [`SCENARIO-005`](../scenarios/SCENARIO-005-forte-release-adaptive-team.md), [`SCENARIO-006`](../scenarios/SCENARIO-006-forte-governed-operations-action.md), [`SCENARIO-007`](../scenarios/SCENARIO-007-single-forte-worksite-entry.md) |
| Evidence | [`FORTE-ONLY-WORKSITE-RETIREMENT-EVIDENCE-20260824`](../evidence/FORTE-ONLY-WORKSITE-RETIREMENT-EVIDENCE-20260824.md) |
| Implementation | [`b2b759b106738fbb3aed597319208e8ff4718cc7`](https://github.com/Dickey007s/lenovo_agent/commit/b2b759b106738fbb3aed597319208e8ff4718cc7) + [`5fab10fb4f638958ff78b39583a4eace2e99396b`](https://github.com/Dickey007s/lenovo_agent/commit/5fab10fb4f638958ff78b39583a4eace2e99396b) |
| Delivery | [PR #24](https://github.com/Dickey007s/lenovo_agent/pull/24), open and unmerged at evidence capture |

## 1. Problem

DR-0016 introduced a FORTE-backed worksite, but the repository still shipped two product identities at once: the new Harness and the legacy mail/document/quote/task/calendar/expense/CRM/audit workspaces with fixed Customer A runtimes. The transitional browser capture in the source record also reduced service failure and catalog-integrity failure to the same `Failed to fetch` message. A reviewer could not tell which surface was current, which runtime facts still applied, or whether the public dataset had failed integrity checks.

The product needs one inspectable front door. Historical vertical slices should remain auditable without remaining executable or being cited as current behavior.

## 2. Decision

The current product surface is the FORTE `工作现场` only:

```text
FORTE Scenario Pack
  -> safe public Catalog projection
  -> Task Contract
  -> deepseek-v4-pro Planner candidate
  -> deterministic Plan Validator
  -> memory Snapshot + ordered SSE
  -> ready_to_execute
```

The root page contains the three FORTE scenarios, a source workspace, a dynamic plan area, and a right-side Agent activity rail. It does not expose a legacy workspace rail or a return-to-legacy-workspace action. Desktop uses a resizable right rail; mobile uses a resizable lower rail.

The API exposes exactly six OpenAPI paths: `/v1/health`, two Scenario routes, and three Harness Run routes. Legacy workspace, thread, task, Demo 1, Demo 2, Demo 3, run-governance, and action routes are not mounted. Their service modules and product tests were removed from the current tree. Generic risk, authorization, gateway, and simulator packages may remain as target-architecture building blocks; their presence does not make them current routes or prove execution.

The fixed `demo-enterprise-data/customer-a/` files are removed from the current Git tree. Historical commits, evidence, screenshots, and source records remain available. “Removed from the current tree” does not mean erased from Git history.

## 3. Failure and recovery semantics

The frontend must preserve three distinct facts:

| Condition | Server/client fact | User-visible state | Recovery |
| --- | --- | --- | --- |
| API unreachable | health request fails | “工作现场暂时离线” / “办公服务正在恢复” | bounded automatic retry plus explicit retry |
| API available, Catalog temporarily unavailable | health succeeds; Scenario request fails without integrity detail | “工作场景暂时不可用” | keep service available, retry Catalog |
| Catalog integrity failure | Scenario request returns 503 with integrity detail | “工作场景需要更新” | do not invent scenarios; retry after source repair |
| Scenario detail unavailable | list projection exists; detail request fails | explicit use of Catalog public information | retain public projection, do not expose internal task text |
| Run stream active | current EventSource is open | “事件流实时” | apply ordered events and GET Snapshot |
| No active stream, API healthy | health succeeds | “服务可用” | no claim of real-time streaming |

The integrity incident that triggered this repair came from line-ending normalization: the old `.gitattributes` converted five upstream CRLF Markdown files to LF while the manifest expected the upstream bytes. The fixed checkout restores upstream bytes, marks FORTE source inputs binary, maps Catalog failures to a controlled 503, and lets the UI distinguish and automatically recover from the failure classes.

## 4. Frontend and server facts

| User sees | Authoritative fact | Allowed action | Hidden or prohibited |
| --- | --- | --- | --- |
| Three FORTE scenario tabs | `GET /v1/harness/scenarios` safe projection | select a scenario | raw `task.md`, sanitized Planner prompt, rubric, solution, internal path/hash |
| Source file tree | Scenario projection or frozen `source_documents[]` | inspect business label and summary | absolute path, full hash, benchmark control fields |
| Task contract | public goal, deliverables, boundary, allowed capabilities and gate summary | review before starting | internal task instruction and grading fields |
| Dynamic plan | validated public `plan.units[]` | inspect dependencies and inputs | chain of thought, Worker conversation, unvalidated plan |
| Model receipt | `HarnessModelReceipt.called/model/elapsed_ms/output_used` | distinguish call, adoption, and validation | animation as proof; configured model name as proof of a call |
| Ready banner | Snapshot `status=ready_to_execute`, v6/seq 5 | start a new independent planning round | “task completed”, tool/Artifact/Connector/external-action claims |
| Offline/catalog notice | health/Catalog request result | wait for automatic retry or retry now | generic `Failed to fetch` as the only explanation |

## 5. Lifecycle policy

Previous `Verified` or `Limited Verified` evidence remains valid only for the commit, route, data, and UI recorded at the time. It receives a separate lifecycle label: `Retired from current product`. The historical result is not rewritten, and its old test numbers are not replaced by current numbers. Current applicability and replacements are indexed in [`RETIREMENT_REGISTER.md`](RETIREMENT_REGISTER.md).

`DR-0001` remains active governance. `DR-0016` remains the active foundation for the FORTE Catalog/Planner/Validator contract. DR-0017 supersedes only the transitional coexistence of FORTE and legacy product surfaces.

## 6. Evidence and boundary

The bounded engineering claim is `Limited Verified`: commits and PR are bound; a fresh clone at `5fab10f...` matched all 11 FORTE files and `115352` bytes with zero hash/size mismatches; the Customer A path was absent; OpenAPI contained only six paths; legacy route probes returned 404; Python `47 passed in 2.42s`, Ruff, lint and build passed; Harness E2E `11 passed in 41.4s`; and one observed Finance-018 live run reached `ready_to_execute` with a real model receipt.

There is no independent screenshot of the final converged UI in this change. The retained screenshot is negative stakeholder evidence of the pre-fix transitional state; E2E is an engineering proxy, not visual or user-research evidence. Runtime state and idempotency remain single-process memory. `X-User-Id` is an unsigned placeholder. No Scheduler, Worker, tool, Artifact mutation, approval, Permit, Connector, or external action is exposed or executed. Product comprehension and value remain `Draft`.

## 7. Rejected alternatives

- **Hide legacy navigation but keep its public routes**: rejected because the runtime and documentation would still have two current products.
- **Delete historical evidence**: rejected because it destroys traceability and makes older claims impossible to audit.
- **Rename old evidence as current FORTE evidence**: rejected because Customer A facts cannot be transferred to new runs.
- **Treat any 503 as an offline API**: rejected because integrity failure requires different user action and must fail closed.
