# FORTE public benchmark inputs

This directory is a read-only import of selected original `input/` files and
task instructions from [AGI-Eval-Official/FORTE](https://github.com/AGI-Eval-Official/FORTE)
at commit `345c1ec1487139db9dd319787fa9405ba85d1869`. The upstream repository
is released under MIT; the exact license text is retained in
`THIRD_PARTY_LICENSE.txt`.

The files are **public benchmark inputs**, not Lenovo data, a real customer
workspace, a live enterprise database, or a connected system. The benchmark
uses business-shaped names and records, but this import does not establish
that any person or company named in a file is fictional or real. It is kept
for reproducible evaluation and interactive harness demonstrations.

Imported tasks:

- `Finance-018`: three accounting workbooks for a cross-period receivables /
  payables analysis.
- `pm-014`: a PRD, release checklist, functional test report, and browser
  compatibility matrix for a release-readiness review.
- `Operations-008`: a domain note for a compliant M1 overdue-card outbound
  call flow.

Only the original `task.md` provenance records and `input/` files are imported.
FORTE `solution/` and `skills/` are intentionally excluded. The original
`task.md` front matter includes grading/rubric metadata; it is retained only
for provenance and is never exposed to the Agent Harness or ordinary UI. The
runtime catalog extracts only the bounded `## Prompt` section before the
grading section. The allowlist, provenance, byte size, and SHA-256 values are
in `manifest.json`. The runtime catalog must fail closed on missing, modified,
extra, symlinked, or path-escaping files and never reads solution material.

Audit performed 2026-08-24:

- all imported XLSX files are OOXML workbooks without VBA projects, external
  workbook link parts, formulas, hidden sheets, or hyperlink relationships;
- no email address, telephone number, identity-card number, URL, token, or
  password was found in the imported input values or Markdown text;
- workbook owner names and business/customer names remain content in the
  public benchmark and are not asserted to be synthetic or real.
