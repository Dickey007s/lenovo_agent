# UI-server fact matrix

This is the current `DR-0022` whole-folder workbench contract. Historical
Scenario/Task/Cockpit/Action mappings remain in their dated Evidence only.

下表中的 Authority 列即“服务端权威字段”；浏览器草稿与传输状态会明确另列，
不能冒充业务事实。
Prompt、思维链、原始模型响应、绝对路径、哈希和内部策略标识在普通界面默认隐藏。

## 1. Folder workspace and task draft

| UI state/action | User-visible meaning | Authority | Transition/recovery/idempotency | Hidden |
| --- | --- | --- | --- | --- |
| Service available | HTTP API and workspace projection succeeded | health/workspace response | may browse or start; not an SSE fact | previous stream, network stack |
| Workspace unavailable | service or catalog cannot provide authoritative files | fetch failure or controlled 503 | retry; no static fallback files | stack trace, partial/stale catalog |
| Whole folder tree | 15 public business folders and 96 inputs | `GET /v1/harness/workspace` | read-only until refreshed | task prompt, rubric, solution, path/hash |
| External-dependency folder | public task record has no local input | folder `availability/external_dependency_label` | cannot be selected as invented local data | remote credentials/endpoints |
| Search/expand | client filters visible folder tree | browser state | no server mutation | no capability claim |
| File checkbox/chip | include/remove file from task draft | browser draft; POST revalidation | 1-20 unique refs; changing scope changes command signature | unselected content |
| Task composer | user writes the actual instruction | browser draft; POST/Snapshot `instruction` | required 3-2,000 chars | hidden benchmark-task fallback is forbidden |
| Run start | server accepted one independent read-only command | POST Owner/key/version/instruction/refs | unknown response reuses same key; changed or known retry uses new key | internal command signature |

## 2. File preview

| UI state/action | User-visible meaning | Authority | Transition/recovery | Hidden |
| --- | --- | --- | --- | --- |
| Metadata | business path, type, bytes, row/page count | workspace/file projection | selecting file triggers preview GET only | raw relative/absolute path and digest |
| Table preview | bounded XLSX/CSV rows | preview response | parser/integrity failure replaces content | macros/formula execution/full workbook internals |
| Document preview | bounded DOCX/PDF text | preview response | encrypted/unsafe/unsupported is unavailable | embedded active content/external loads |
| Text preview | bounded TXT/MD/JSON/log/code | preview response | displayed only, never executed | shell/script execution |
| Security footer | integrity verified, read-only, no active/external resource execution | `BenchmarkPreviewSecurity` | cannot be inferred from extension alone | scanner implementation details |
| Citation click | reopen a finding's selected source | result `file_ref` resolved through workspace | selects file and switches to preview | source path/hash |

## 3. Run, plan and result

| UI state | User-visible meaning | Authority | Ordered transition | Hidden |
| --- | --- | --- | --- | --- |
| Selected files frozen | the Run context is fixed | `workspace_index`, `source_documents[]` | seq 1 | internal path/hash/safe content |
| Planner started/returned | provider call stage, not acceptance | `planning_started/completed` | seq 2-3 | Prompt, CoT, raw candidate |
| Planner receipt | not called/adopted/not adopted and elapsed time | `model_receipt.called/output_used/elapsed_ms` | independent of plan validation | token/provider trace |
| Validated plan | server compiled/accepted work intent | `plan_validation`, public plan | seq 4 | raw tool/effect/gate IDs |
| Analyst started/returned | provider analysis stage, not completion | `analysis_started/completed` | seq 5-6 | Prompt, CoT, raw response |
| Analyst receipt | not called/adopted/not adopted and elapsed time | `analysis_receipt.*` | independent of result validation | token/provider trace |
| Citation validation | every finding stays inside selected refs | `result_validation` | seq 7 | false semantic/numeric proof claim |
| Initial result, review required | read-only response is available | Snapshot `result`, `review_required=true` | findings expandable; citations reopen sources | quality-pass/external-success claim |
| Completed | response passed schema/ref/boundary checks | `status=completed`, `task_completed` | seq 8 / current implementation v9; final GET | Artifact Commit, tool execution, business completion |
| Safely stopped | model/schema/plan/source/citation check failed | `status=failed`, `harness_failed`, safe errors | no result; fresh retry | raw validator/compiler/provider error |

## 4. Preview and validation limits

| Fact | Current guarantee | Not guaranteed |
| --- | --- | --- |
| workspace inventory | 15 folders, 96 input refs from pinned manifest | unpublished FORTE tasks or live enterprise drive |
| XLSX/CSV | first visible sheet/CSV, <=30 columns, <=120 rows | arbitrary workbook features or formula truth |
| DOCX/PDF/TXT | bounded extracted/read text, <=30,000 chars | OCR completeness, layout fidelity or semantic accuracy |
| stable ref | deterministic for pinned public input path | production document identity |
| plan compilation | server-owned effects/gates plus graph/source checks | plan quality or tool execution |
| result validation | citation membership in frozen selected set | entailment, exhaustive matching or arithmetic |
| completed | reviewable read-only response exists | task correctness, Artifact, Connector or external process completion |

## 5. Transport and lifecycle

- Snapshot version and event sequence never decrease in the browser.
- A terminal event requires final GET; a nonterminal disconnect uses GET plus
  `after=N`.
- “trajectory live” requires an open current EventSource; “service available”
  only requires successful HTTP.
- Missing/wrong-owner Run returns the same 404.
- `X-User-Id` is unsigned and all Run state is one-process memory.
- Plan operation labels declare intent. The current Runtime does not invoke a
  Tool Gateway or mutate an ArtifactVersion.

## 6. Evidence and applicability

Current contract: [`DR-0022`](../decisions/DR-0022-workspace-folder-and-arbitrary-task-contract.md),
[`SCENARIO-008`](../scenarios/SCENARIO-008-whole-folder-office-workspace.md),
[workspace interaction/source record](../research/WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825.md)
and [Evidence](../evidence/FORTE-FOLDER-WORKSPACE-EVIDENCE-20260825.md).

Automated checks are engineering proxies, not user research. User
comprehension, calibrated trust and task value remain `Draft`.
