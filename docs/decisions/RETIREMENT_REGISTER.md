# Legacy product retirement register

## Purpose

This register separates historical validity from current product applicability. `Retired` means an artifact no longer describes the current public UI, API, runtime, data, or acceptance suite. It does not revoke a test result that was valid for the recorded commit. Source records and Git history remain intact.

The retirement decision is [`DR-0017`](DR-0017-single-forte-worksite-and-legacy-retirement.md), dated 2026-08-24. [`DR-0022`](DR-0022-workspace-folder-and-arbitrary-task-contract.md) governs the current six-path whole-folder workbench and read-only analysis. DR-0016/0017/0018 retain their historical foundation and convergence facts but no longer describe the current folder/API contract.

## Decisions and contracts

| Artifact | Historical scope | Lifecycle from DR-0017 | Current replacement |
| --- | --- | --- | --- |
| `DR-0001` | reporting and interaction gates | Active | remains the governance gate |
| `DR-0002` to `DR-0009` | fixed Task, workspace, quote, action bridge, cockpit and progressive UI slices | Retired from current product | DR-0016/0017 and SCENARIO-004/005/006/007 |
| `DR-0010` | visible impact preview on fixed Demo 1 | implementation retired; principle carried forward | DR-0017 fact/impact mapping; future execution Draft |
| `DR-0011` | fixed Demo 2 route impact | Retired from current product | unified Harness plan and future Scheduler Draft |
| `DR-0012` | fixed Demo 3 action impact ledger | implementation retired; governance principle carried forward | future FORTE governed execution Draft |
| `DR-0013` | legacy Demo identity navigation and call trace | implementation retired; truthful call receipts carried forward | Harness model receipt and activity rail |
| `DR-0014` | Customer A file-backed sources | Retired from current product | FORTE manifest and Catalog |
| `DR-0015` | mainstream comparison plus fixed Customer A controlled execution | execution slice retired; research comparison remains Draft reference | competitor research + FORTE target architecture |
| `DR-0016` | FORTE Catalog, Planner, Validator and transitional worksite | Active historical foundation | extended by DR-0017/0018; its six-path/ready screenshots remain historical |
| `DR-0017` | sole FORTE product surface and legacy retirement | Active lifecycle decision | current interaction/API/terminal projection extended by DR-0018 |
| `DR-0018` | three-collection data browsing, user task, two-call read-only result and verifiable trace | Historical interaction/runtime foundation | extended and replaced in the foreground by DR-0022 |
| `DR-0019/0020` | generic capability profile and server-owned plan policy | Active carried-forward runtime principles | used by DR-0022 |
| `DR-0021` | complete public suite acquisition and inventory | Active data foundation | surfaced by DR-0022 |
| `DR-0022` | whole-folder workspace, safe multi-format preview and arbitrary selected-file task | Active current product contract | current living docs and SCENARIO-008 |
| `TASK_RUNTIME_PROTOCOL.md` | legacy Task Runtime protocol | Retired historical contract | Harness API and UI fact matrix |

## Scenarios

| Artifact | Lifecycle | Current replacement |
| --- | --- | --- |
| `SCENARIO-001` Customer A durable report | Retired historical scenario | `SCENARIO-004` |
| `SCENARIO-002` fixed cockpit/controlled execution | Retired historical scenario | `SCENARIO-005` |
| `SCENARIO-003` fixed Customer A action ledger | Retired historical scenario | `SCENARIO-006` |
| `SCENARIO-004/005/006` | Active acceptance-source scenarios; their old three-collection foreground is historical | available as tasks within the whole folder |
| `SCENARIO-007` | Historical three-collection data-workbench/recovery journey | `SCENARIO-008` |
| `SCENARIO-008` | Active whole-folder browse/select/task/evidence journey | current product shell and trace |

## Historical evidence

All rows below retain their original claims, commits, test counts, screenshots, and hashes. They must not be used to describe the current UI/API/data.

| Evidence document | Historical subject | Lifecycle |
| --- | --- | --- |
| `DR-0003-FRONTEND-VISUAL-SYNC-EVIDENCE.md` | legacy visual/workspace merge | Retired |
| `DEMO1-PR3-RUNTIME-EVIDENCE.md` | fixed Demo 1 runtime | Retired |
| `DEMO1-PR4-FRONTEND-E2E-EVIDENCE.md` | legacy Task Artifact workspace | Retired |
| `DEMO1-PR5-POSTGRES-BACKED-API-RESTART-EVIDENCE.md` | legacy TaskStore restart | Retired |
| `DEMO1-PR6-TASK-DIRECTOR-INTERACTION-EVIDENCE.md` | legacy Task Director | Retired |
| `DEMO1-PR6-USABILITY-COMPREHENSION-AUDIT-20260811.md` | legacy comprehension engineering proxy | Retired |
| `DEMO1-ROUND-AND-SOURCE-CLARITY-EVIDENCE-20260811.md` | legacy round/source labels | Retired |
| `QUOTE-WORKSPACE-DETERMINISTIC-CALCULATION-EVIDENCE-20260811.md` | legacy quote workspace | Retired |
| `DEMO1-DEMO3-TASK-ARTIFACT-ACTION-BRIDGE-EVIDENCE-20260813.md` | legacy Task-to-action bridge | Retired |
| `DEMO1-PROGRESSIVE-STAGES-EVIDENCE-20260817.md` | legacy progressive stages | Retired |
| `DEMO2-PR1-EXPLAINABLE-ADMISSION-EVIDENCE-20260817.md` | legacy cockpit Admission | Retired |
| `DEMO1-AGENT-IMPACT-PREVIEW-EVIDENCE-20260820.md` | legacy conflict impact preview | Retired |
| `DEMO2-ROUTE-IMPACT-EVIDENCE-20260820.md` | legacy route impact | Retired |
| `DEMO3-ACTION-IMPACT-LEDGER-EVIDENCE-20260820.md` | legacy governed action path | Retired |
| `DEMO-IDENTITY-AND-CALL-TRACE-EVIDENCE-20260820.md` | legacy three-Demo navigation | Retired |
| `PROCESSING-PATH-REALISM-EVIDENCE-20260820.md` | legacy quote/cockpit/model path labels | Retired |
| `DEMO1-FILE-BACKED-SOURCES-EVIDENCE-20260820.md` | Customer A source package | Retired |
| `DEMO2-CONTROLLED-EXECUTION-EVIDENCE-20260821.md` | fixed Customer A Worker execution | Retired |

`LLM-API-SMOKE-EVIDENCE-20260811.md` remains a historical connectivity observation, not current product acceptance evidence. DR-0016 Evidence remains the historical planning foundation; DR-0017 Evidence governs the retirement claim at its recorded boundary. `FORTE-DATA-WORKBENCH-TRACE-EVIDENCE-20260824.md` preserves the three-collection terminal and numerical negative result. `FORTE-FOLDER-WORKSPACE-EVIDENCE-20260825.md` is the current whole-folder Evidence record once its Draft delivery fields are bound.

## Sources, research, and presentations

Stakeholder feedback sources are never deleted or rewritten. A source can remain historically relevant even when its implementation is retired. `ENTERPRISE-DEMO-DATA-RESEARCH-20260820` is a historical design input; the FORTE audit/selection and mainstream comparison remain active research references with their existing limitations.

Generated presentation directories and `final-reference/` are dated historical artifacts. They are not living product documentation and are not rewritten by DR-0017. Any new report must use the living docs and current Evidence rather than copying a historical slide claim.
