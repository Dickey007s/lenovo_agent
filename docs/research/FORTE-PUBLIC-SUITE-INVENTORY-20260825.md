# FORTE public suite inventory

## Status

`Verified` for the pinned public repository inventory and imported byte set.
This is not evidence that the current Agent executes every task.

## Repository fact

The official FORTE README says the full benchmark has 180 tasks across 15
professions. The same README explicitly says the public repository ships one
demo task per profession. At pinned commit
`345c1ec1487139db9dd319787fa9405ba85d1869`, the public repository contains:

- 15 `data/tasks/*.md` task records;
- 96 files under `data/assets/<task_id>/input/`;
- 13 tasks with a local input bundle;
- two task-only examples: `ba-079` depends on a remote Datasette endpoint and
  `Misc-AT-003` depends on Web search plus a global cron service;
- `143,462` task-record bytes and `1,636,983` input bytes, or `1,780,445`
  imported bytes in total.

The public repository at this revision is therefore small. The presumed
multi-gigabyte download is not the public FORTE demo suite. A separate dataset,
Workspace-Bench, advertises much larger workspace archives and remains a
different second-stage candidate; its size and license cannot be transferred
to FORTE.

## Import method

The complete official repository was cloned locally to the ignored cache
`.runtime/forte-upstream-345c1ec` and detached at the pinned commit. The
reproducible importer is
[`scripts/sync-forte-public-demos.py`](../../scripts/sync-forte-public-demos.py).
It copies only:

- `data/tasks/<task_id>.md` to `<task_id>/task.md`;
- `data/assets/<task_id>/input/**` to `<task_id>/input/**`;
- the top-level MIT license.

It intentionally excludes every `solution/` and `skills/` path. The complete
path/size/MIME/SHA-256 inventory is
[`public-suite-manifest.json`](../../demo-enterprise-data/forte/public-suite-manifest.json).

## File distribution

| Extension | Files | Example task types |
| --- | ---: | --- |
| `.py` | 34 | Agent architecture and evaluation platform code |
| `.docx` | 11 | JD, resumes, legal documents, marketing and UI specifications |
| `.js` | 10 | dashboard utility library and Vitest work |
| `.md` | 7 | rules, PRD and domain knowledge |
| `.xlsx` | 7 | finance, release, behavior-log and structured review |
| `.pdf` | 6 | resumes and administration allocation rules |
| `.tsx` | 6 | frontend source tree |
| `.json` | 4 | package/config/source data |
| `.txt` | 3 | SRE log and code configuration |
| `.csv` | 2 | onboarding and customer survey data |
| other code/log formats | 6 | CSS, HTML, shell, TS and log |

## Runtime boundary

`DR-0022` now uses `public-suite-manifest.json` as the active read-only product
inventory: 15 folders and 96 input files enter one safe public workspace.
`task.md` files remain provenance records and are not user task prompts or
Agent-selected context. The older three-Scenario `manifest.json` is a historical
artifact and is not the current public route contract.

All 96 inputs have bounded preview adapters, including DOCX, PDF, CSV/XLSX and
text/code. That does not mean they are safely editable, executable or graded.
Task-specific deterministic validators, writable Run artifacts, code sandbox,
Worker orchestration and policy gates remain separate implementation work. The
two task-only external examples still need governed Connectors and have no local
file payload to select.

## Source and limitations

Primary source: [AGI-Eval-Official/FORTE](https://github.com/AGI-Eval-Official/FORTE),
pinned at the commit above, top-level MIT license. The inventory supports a
reproducible public test-data claim only. It does not prove real enterprise
data access, production representativeness, user value, task quality or access
to the unpublished full benchmark.
