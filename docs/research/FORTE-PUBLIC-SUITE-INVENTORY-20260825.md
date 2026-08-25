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

The downloaded suite and the current product allowlist are deliberately
separate:

- `public-suite-manifest.json`: all 15 public task records and 96 public input
  files, for audit and staged test development;
- `manifest.json`: the current runtime allowlist for `Finance-018`, `pm-014`
  and `Operations-008` only.

Downloading a DOCX, PDF or source tree is not equivalent to safely previewing,
editing, executing or grading it. The ten newly staged local-input tasks need
format adapters, privacy projection, deterministic validators, run-workspace
writes and policy gates before they can enter the product Catalog. The two
external tasks need real governed Connectors and remain disabled.

## Source and limitations

Primary source: [AGI-Eval-Official/FORTE](https://github.com/AGI-Eval-Official/FORTE),
pinned at the commit above, top-level MIT license. The inventory supports a
reproducible public test-data claim only. It does not prove real enterprise
data access, production representativeness, user value, task quality or access
to the unpublished full benchmark.
