# FORTE public benchmark inputs

This directory contains a read-only import of the complete public demo suite
shipped by [AGI-Eval-Official/FORTE](https://github.com/AGI-Eval-Official/FORTE)
at commit `345c1ec1487139db9dd319787fa9405ba85d1869`. The upstream repository
reports a 180-task benchmark, but its public Git repository ships one demo task
for each of 15 professions. It does not publish the complete 180-task set. The
upstream repository is released under MIT; the license text is retained in
`THIRD_PARTY_LICENSE.txt`.

The files are **public benchmark inputs**, not Lenovo data, a real customer
workspace, a live enterprise database, or a connected system. The benchmark
uses business-shaped names and records, but this import does not establish
that any person or company named in a file is fictional or real. It is kept
for reproducible evaluation and interactive harness demonstrations.

Downloaded public scope:

- 15 original `task.md` records covering administration, algorithm, business
  analysis, development, finance, HR, legal, marketing, general automation,
  operations, product management, QA, sales, SRE, and UI/UX;
- 96 original files under 13 local `input/` bundles, totaling `1,636,983`
  bytes;
- two task-only demos (`ba-079` and `Misc-AT-003`) whose prompts depend on an
  external Datasette endpoint or web search plus a global cron service;
- 111 imported source files and `1,780,445` bytes when the 15 task records are
  included.

`public-suite-manifest.json` is the complete download and integrity inventory.
`manifest.json` remains the smaller runtime allowlist used by the current
product: `Finance-018`, `pm-014`, and `Operations-008`. The other downloaded
tasks are staged test data, not an assertion that the current browser or
runtime can already preview, execute, or grade every format.

Only the original `task.md` provenance records and `input/` files are imported.
FORTE `solution/` and `skills/` are intentionally excluded. The original
`task.md` front matter includes grading/rubric metadata; it is retained only
for provenance and is never exposed to the Agent Harness or ordinary UI. The
runtime catalog extracts only the bounded `## Prompt` section before the
grading section. The complete downloaded inventory is in
`public-suite-manifest.json`; the current runtime allowlist remains in
`manifest.json`. The runtime catalog must fail closed on missing, modified,
extra, symlinked, or path-escaping files and never reads solution material.

Initial runtime-subset audit performed 2026-08-24:

- all imported XLSX files are OOXML workbooks without VBA projects, external
  workbook link parts, formulas, hidden sheets, or hyperlink relationships;
- no email address, telephone number, identity-card number, URL, token, or
  password was found in the imported input values or Markdown text;
- workbook owner names and business/customer names remain content in the
  public benchmark and are not asserted to be synthetic or real.

Public-suite expansion performed 2026-08-25:

- the complete public repository was cloned and detached at the pinned commit;
- all 15 public task records and all 96 public input files were copied without
  importing any `solution/` or `skills/` path;
- `public-suite-manifest.json` records every imported path, byte size, MIME
  type, availability class, and SHA-256;
- automated integrity tests verify the complete public suite and prove that
  the current three-task runtime manifest is an exact subset;
- safe preview adapters, execution tools, output validation, and policy gates
  for the ten newly staged local-input tasks remain separate implementation
  work and must not be inferred from the download.
