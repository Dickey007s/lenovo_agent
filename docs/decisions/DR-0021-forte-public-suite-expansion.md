# DR-0021: Expand to the complete public FORTE demo suite

## Decision metadata

| Field | Value |
| --- | --- |
| Status | `Limited Verified` for public-byte acquisition and integrity inventory; runtime expansion remains `Ready` |
| Date | 2026-08-25 |
| Trigger | `USER-FEEDBACK-20260825-BROADER-FORTE-13` |
| Source | `FORTE-PUBLIC-SUITE-INVENTORY-20260825` |
| Evidence | [`FORTE-PUBLIC-DEMO-SUITE-IMPORT-EVIDENCE-20260825`](../evidence/FORTE-PUBLIC-DEMO-SUITE-IMPORT-EVIDENCE-20260825.md) |
| Implementation | [`e7597369d5cfbab59082e8af2d5a822e691a12cc`](https://github.com/Dickey007s/lenovo_agent/commit/e7597369d5cfbab59082e8af2d5a822e691a12cc) |
| Delivery | [PR #26](https://github.com/Dickey007s/lenovo_agent/pull/26), open and stacked on PR #25; not merged |

## Problem

The first FORTE workbench exposed only three scenarios and eight input files.
That was enough to validate the first safe Catalog and read-only trace, but too
narrow to test whether one general Agent can handle varied office work. It also
made the product appear scenario-specific.

## Decision

Import every task record and input byte that the pinned official FORTE
repository publicly ships. Preserve a strict separation between acquisition
and product capability:

1. `public-suite-manifest.json` records all 15 public task records and 96 input
   files.
2. The current `manifest.json` continues to register only the three scenarios
   whose safe projection is already implemented.
3. `solution/` and `skills/` are never imported.
4. `ba-079` and `Misc-AT-003` remain task-only, external-dependency tests. They
   cannot appear as runnable local-file scenarios.
5. New formats enter the runtime only through explicit parser, preview,
   validator, work-profile and control-policy changes with tests.

The shared capability layer remains generic. The 15 cases are workload probes;
they do not add demo-specific private code paths.

## Scenario and source

The target user is the product/technical reviewer who needs to test office
tasks beyond three curated demonstrations. The trigger is a request to inspect
more file types and issue more varied tasks. Completion for this decision is a
reproducible public download, a complete manifest, a test-case catalog, exact
runtime-boundary wording and integrity tests.

The official repository supports the count and bytes of the public demo suite.
Stakeholder feedback supports the need for broader coverage. Neither source
proves the current runtime can complete the new tasks or that the public data
represents a production enterprise workspace.

## Frontend impact

This import does not silently add new tabs or claim new runnable scenarios.
When staged tasks are later surfaced, the browser must distinguish:

- available now;
- downloaded but adapter/validator pending;
- requires an external Connector;
- blocked by integrity or policy.

Users may see readable task/file labels, format, source and availability. Raw
task instructions, rubric/solution metadata, absolute paths, hashes and hidden
evaluation content remain absent from ordinary UI. Clicking a staged task must
not start a model call until the server says the scenario is runnable.

## Backend facts

- Pinned upstream revision:
  `345c1ec1487139db9dd319787fa9405ba85d1869`.
- Complete public inventory: 15 task records, 96 inputs, 111 files and
  `1,780,445` bytes.
- Local-input tasks: 13; task-only external-dependency tasks: 2.
- Current product allowlist: three tasks and 11 original files, unchanged.
- The sync script validates the upstream Git revision, permits only known
  public file types, excludes solution/skills and generates SHA-256 records.
- Integrity tests compare every imported byte with the full inventory and the
  active runtime subset with the full inventory.

## Verification and boundary

The import and integrity contract are `Limited Verified` by the evidence file.
No new parser, file preview, model task, Worker, Tool Gateway, Artifact write,
Connector or external effect is claimed here. The 15-case test document is
`Ready`, not execution evidence. Access to the remaining unpublished 165 tasks
is not claimed.

## Next implementation gate

The first runtime expansion should add CSV/PDF/DOCX/TXT adapters and six
staged cases: administration, HR, legal, sales, SRE and UI/UX. It must include
safe preview, citations, deterministic validation, privacy projection and a
separate run workspace before updating the active manifest.
