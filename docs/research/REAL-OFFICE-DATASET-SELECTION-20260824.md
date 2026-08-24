# Public office workspace dataset selection

## Research question

Which existing public dataset can provide original office files for all three Office Agent demonstrations without inventing a customer folder or stitching facts from unrelated datasets?

## Selection criteria

1. Original office files are available as task input, not only screenshots or prose.
2. A task has a bounded input folder and a traceable task instruction.
3. Redistribution terms and source revision can be recorded.
4. The files support evidence reading, multi-file coordination, or governed action design.
5. The first integration does not require a multi-gigabyte workspace download.
6. Solution, rubric, private data, and benchmark-internal traces can be excluded from the product workspace.

## Candidates

| Dataset | Relevant facts | Strength | Constraint | Decision |
| --- | --- | --- | --- | --- |
| [FORTE](https://github.com/AGI-Eval-Official/FORTE) | 180 professional tasks; bundled demo tasks use office formats and per-task `input/` folders; repository license is MIT | Directly usable task folders and instructions; small enough to audit and pin | Public benchmark input, not real company data; each imported file still needs privacy and integrity review | Selected for the first vertical slice |
| [Workspace-Bench](https://opendatabox.github.io/Workspace-Bench/dataset/) | 20,476 files, 74 types, 388 tasks and five workspace personas | Closest to a broad enterprise filesystem | Full Chinese and English workspace archives are about 18 GB each; task data and data-license boundaries need separate review | Second-stage candidate |
| [EnterpriseRAG-Bench](https://github.com/onyx-dot-app/EnterpriseRAG-Bench) | More than 500,000 synthetic company documents across common enterprise sources | Strong retrieval and conflicting-information evaluation | It is synthetic and is not organized as a single office folder experience | Not selected for this slice |

## Selected source revision

- Dataset: FORTE
- Repository: <https://github.com/AGI-Eval-Official/FORTE>
- Pinned revision: `345c1ec1487139db9dd319787fa9405ba85d1869`
- License to verify and preserve: repository top-level MIT license
- Content label in UI: `公开办公基准数据`

The pinned revision, 11 imported files/`115352` bytes, SHA-256 values, file structure, workbook metadata and privacy scan have been independently recorded by the local manifest and audit before entering the Scenario Pack. The application does not download data at runtime.

## Three source tasks

| Demo | FORTE task | Original inputs | Why it fits |
| --- | --- | --- | --- |
| Demo 1: durable evidence work | [`Finance-018`](https://github.com/AGI-Eval-Official/FORTE/blob/345c1ec1487139db9dd319787fa9405ba85d1869/data/tasks/Finance-018.md) | Three period-based accounts-receivable/payable workbooks | The Agent must inspect a time series of source files, checkpoint progress, cite rows, and identify long-lived balances instead of repeating a fixed revenue conflict |
| Demo 2: adaptive collaboration | [`pm-014`](https://github.com/AGI-Eval-Official/FORTE/blob/345c1ec1487139db9dd319787fa9405ba85d1869/data/tasks/pm-014.md) | PRD, release configuration, functional test report, compatibility test report | The Harness can generate a dependency graph from the available evidence, schedule parallel units, add reconciliation work when reports disagree, and converge into a shared release-readiness artifact |
| Demo 3: governed action | [`Operations-008`](https://github.com/AGI-Eval-Official/FORTE/blob/345c1ec1487139db9dd319787fa9405ba85d1869/data/tasks/Operations-008.md) | A professional requirements document for an AI collection-call process | The Agent can draft a process and propose controlled actions while deterministic policy enforces calling time, recording notice, retry limits, escalation, and no real dial-out |

The final column describes target execution fit, not current execution evidence. DR-0016 is `Limited Verified` only for loading these fixed public files, generating a real-model dynamic Plan, deterministic validation and frontend receipts up to `ready_to_execute`; Scheduler/Worker, file tools, Artifact mutation, governed action execution and user value remain `Draft`.

## Data boundary

- Import the original `task.md` as a provenance record plus the `input/` files required by the selected task.
- Do not import `solution/` or `skills/`. The raw `task.md` front matter may retain rubric/solution metadata only as provenance; the Catalog extracts only the `## Prompt` section before `## Grading Criteria` for the internal Planner. Raw task text, sanitized Prompt, `task_instruction`, grading, solution paths, benchmark traces, generated answers and hidden evaluation content never enter the public API or ordinary UI.
- Preserve original bytes and license text; record source URL, pinned commit, file size, MIME type, and SHA-256.
- Treat the imported folder as read-only. Agent output goes to a separate run workspace.
- Reject path escape, symbolic links, extra files, oversize files, hash mismatch, unsupported formats, macros, external workbook links, or privacy findings that have not been reviewed.
- The frontend may show file name, public benchmark label, document type, version/fingerprint summary, and cited sheet/section. It must hide absolute paths and benchmark-internal IDs.

## What this source does not prove

The selected files support a more realistic and reproducible office workflow. They do not prove access to a real enterprise database, a production Connector, target-user value, generalization to arbitrary folders, or permission to treat benchmark entities as real customers.
