# UI—Server Fact Matrix

This is the current DR-0018 workbench contract plus the DR-0019 generic capability-profile boundary and DR-0020 server-owned policy compiler. Historical Task/Cockpit/Action mappings remain in retired Evidence.

## 1. Data workbench

| UI state/location | User-visible meaning/action | 服务端权威字段 or event | Transition/recovery/idempotency | 默认隐藏 | Evidence/status |
| --- | --- | --- | --- | --- | --- |
| Header: 服务可用 | API/Catalog reachable; no active Run stream | successful health/Catalog and no open EventSource | user may browse or run | previous stream state | E2E; Limited Verified |
| Header: 轨迹实时 | current nonterminal SSE is open | EventSource `open` for current Run | still requires ordered events/GET | heartbeat/raw transport | E2E/live screenshot; Limited Verified |
| Header: 正在重连/暂时离线 | recovery active or API unreachable | stream/request failure | GET + `after=N`, automatic/explicit retry | stack trace | E2E; Limited Verified |
| Business collections | three safe FORTE Scenario groups | `GET /v1/harness/scenarios` | switching clears current local Run view | Demo identity, task/rubric/solution | tests/E2E |
| Scenario work profile | reusable target topology/orchestration/gates plus honest current scope | `work_profile.task_topology/orchestration/control_requirements/current_runtime_scope` | Catalog-fixed today; dynamic Admission remains Draft | `demo_id`, `experience_policy`, false execution animation | contract/API tests; Limited Verified |
| File checkbox | include/exclude a file from this task | POST `selected_file_refs`; server membership validation | UI retains at least one; edits create new command signature | source path/hash | tests/E2E |
| File preview | actual bounded public benchmark content | preview route by Scenario + `file_ref` | unknown/integrity failure is explicit; no fallback data | path/hash/raw task | tests/E2E |
| Task composer | user defines the question | POST `instruction`; Snapshot `instruction/instruction_source` | 3-2,000 chars; edit invalidates pending command key | hidden benchmark task substitution | tests/E2E |
| Run start | create one independent read-only task | POST Owner/key/version/instruction/refs | identical unknown outcome reuses key; known failed/completed retry uses a fresh key | internal task handle | tests/E2E |

## 2. Plan, result and trace

| UI state/location | User-visible meaning/action | 服务端权威字段 or event | Transition/recovery/idempotency | 默认隐藏 | Evidence/status |
| --- | --- | --- | --- | --- | --- |
| 已锁定所选文件 | Run context frozen | `workspace_index`, public `source_documents[]` | seq 1 / v2 | internal path/hash/summary |
| 规划模型开始/返回 | Planner call stage | `planning_started/completed` | seq 2-3; not validation | Prompt, CoT, raw response |
| 规划调用 receipt | `未调用` / `已采用` / `校验未通过` plus elapsed observation | `model_receipt.called/model/elapsed_ms/output_used` | independent of Analyst; rejection is not “not called” | provider trace/tokens/raw candidate |
| 已校验的工作图 | server-compiled and validated public plan | `plan_validation`, public `plan.units[]` | seq 4; operation labels are intent only | raw tool/effect IDs and unvalidated candidate |
| 分析模型开始/返回 | Analyst call over safe previews | `analysis_started/completed` | seq 5-6; not completion | Prompt, CoT, raw response |
| 分析调用 receipt | whether Analyst called/adopted and elapsed observation | `analysis_receipt.*` | independent of Planner receipt | provider trace/tokens |
| 服务端核对文件引用 | each finding cites selected refs | `result_validation` | seq 7; membership only | false claim of semantic proof |
| 模型初步结论 · 待复核 | read-only model result available | Snapshot `result`, `review_required=true` | default first 3 findings; user expands remainder | hidden findings are user-expandable, not absent |
| Citation label | which selected file a finding references | `result.findings[].file_refs` resolved against `source_documents[]` | unknown ref fails Run | internal path/hash |
| 仍需你判断 | follow-up needs human review | `result.follow_ups[]`, `review_required=true` | no automatic approval/action | fabricated decision |
| 初步结果已形成 | response available in memory and trace terminal | `status=completed`, `task_completed`, result present | seq 8 / v9; terminal GET | correctness, quality-pass, external success or Artifact Commit claim |
| 本轮已安全停止 | source/model/plan/result validation failed | `status=failed`, `harness_failed`, safe `validation_errors[]` | no result tab; “重新规划” starts a fresh-key Run | stack/raw response/raw tool/effect IDs |

## 3. Preview and validation limits

| Fact | Current guarantee | Not guaranteed |
| --- | --- | --- |
| XLSX preview | first visible sheet, <=30 columns, <=120 data rows | arbitrary workbook features or full-sheet UI |
| Markdown preview | allowlisted input, <=30,000 chars | raw task instruction |
| stable `file_ref` | deterministic for pinned Scenario/path | a production enterprise document identity |
| plan compilation + validation | server-owned effects/gates plus refs/tools/dependencies | plan quality or tool execution |
| result validation | every citation ref belongs to selected set | claim entailment, exhaustive matching, arithmetic or policy correctness |
| deterministic spreadsheet check | regression reproduces 23 unchanged items / `1,845,444.71` | not yet part of the Runtime; observed model response stated 20 / `2,202,000` |
| `completed` | response passed schema/ref/read-only checks and needs review | answer correctness, quality pass, tool, Artifact, Connector or business process completion |

## 4. Model and action boundary

The two receipts are the only foreground facts for model calls. Configured model name, duration animation or event prose cannot substitute for `called/output_used`.

Plan fields `file.read`, `table.inspect`, `artifact.write`, `evidence.verify` and `action.preview` are declarations. The current successful path directly invokes the Analyst over Catalog previews; it does not invoke Tool Gateway or mutate an ArtifactVersion.

## 5. Ownership and lifecycle

- Snapshot version and event sequence must increase monotonically.
- Terminal event requires final GET; nonterminal disconnect uses GET + `after=N`.
- Missing/wrong-owner Run returns the same 404.
- `X-User-Id` is unsigned and all state is one-process memory.
- DR-0016 planning-only and DR-0017 six-path screenshots/numbers remain historical; DR-0018 governs current applicability.
- DR-0019 makes Demo 1/2/3 acceptance lenses only; a target `bounded_loop` or `adaptive_swarm` profile must not be rendered as executed while `current_runtime_scope=read_only_analysis`.

See [DR-0018](../decisions/DR-0018-forte-data-workbench-and-verifiable-trace.md), [DR-0019](../decisions/DR-0019-capability-composed-agent-runtime.md), [workbench Evidence](../evidence/FORTE-DATA-WORKBENCH-TRACE-EVIDENCE-20260824.md) and [capability-contract Evidence](../evidence/AGENT-CAPABILITY-COMPOSITION-EVIDENCE-20260824.md).
