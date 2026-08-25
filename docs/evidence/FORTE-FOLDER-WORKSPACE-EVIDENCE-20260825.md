# FORTE whole-folder workspace Evidence

## Status

`Limited Verified` for the bounded engineering path described below.
Implementation, fresh-service live runs, screenshots, final automation and the
delivery PR are bound in this record. Semantic correctness, target-user value
and production readiness remain unverified.

## Scope

This record covers only the pinned public FORTE folder workspace, bounded file
previews, arbitrary selected-file tasks, public projection, event recovery and
the tested desktop/mobile browser paths. It does not cover semantic answer
quality, durable recovery, external action or user value.

## Source and inventory

- FORTE commit: `345c1ec1487139db9dd319787fa9405ba85d1869`.
- Public task folders: 15.
- Public input files: 96.
- Imported task and input files: 111, `1,780,445` bytes.
- Runtime previews: 96/96 files; observed distribution in the all-file smoke is
  70 text/code, 11 document, 9 table and 6 PDF previews.
- `task.md`, solution and skill content are not part of Agent-selected context
  or ordinary UI.

## Implementation evidence

| Item | Result |
| --- | --- |
| Focused Python | `26 passed in 15.37s` |
| Full Python | `51 passed in 13.16s` |
| Ruff | passed |
| Frontend typecheck | passed |
| Production build | compile `2.4s`, TypeScript `3.2s`, static generation `682ms` |
| Browser | `8 passed in 22.9s` |
| Governance | `4 passed in 0.03s` |
| Changed-document links | 23 files, 0 missing local links |
| Diff check | passed |

## Fresh-service live runs

The final API live run used two selected files, a user-authored onboarding
privacy/review task and the configured `deepseek-v4-pro`. It reached
`completed`, Snapshot v9 / event sequence 8, with four plan units, six cited
findings and `review_required=true`. Planning took `10,968 ms`; analysis took
`14,869 ms`; both outputs were adopted. The separate browser run took
`8.7 s + 16.7 s`, displayed the intermediate trajectory and had no console
errors. These timings are observations, not SLA or cost claims.

The model result was checked only for schema, selected-file citation membership
and the read-only boundary. No semantic or numerical quality result is claimed.

## Tested facts

- the public API contains `/v1/harness/workspace` and
  `/v1/harness/workspace/files/{file_ref}`; the retired Scenario routes are not
  mounted;
- the public workspace contains 15 folders and 96 safe file projections;
- CSV, PDF, DOCX and TXT are previewed after manifest integrity checks;
- macros and external resources are not executed, encrypted/unsafe inputs fail
  closed and preview/context sizes are bounded;
- a user can select files across folders, author an arbitrary instruction and
  retry an unknown start response with the same command key;
- model receipts distinguish not called, adopted and returned-but-not-adopted;
- named SSE resumes from the last event sequence;
- every result citation is checked against the frozen selected source set and
  can reopen the corresponding file preview;
- the 390 px tested path retains folder browse, selection, task input, preview,
  trajectory and result access without page-level horizontal overflow.

## Screenshot manifest

The machine-readable record is
[`dr-0022-forte-folder-workspace.json`](manifests/dr-0022-forte-folder-workspace.json).
It binds nine fresh-service captures covering the folder tree, CSV, PDF, DOCX,
TXT, explicit task scope, live trajectory, cited result and the 390 px path.
All desktop captures are `1440x900`; the mobile full-page capture is
`390x2884` with `scrollWidth=390`. Browser console errors: none.

The result screenshot also verifies that model-authored control references are
projected back to business file labels; raw `forte-*` identifiers do not appear
in ordinary visible copy.

## Delivery

- Implementation commit:
  [`0794648477ad0061a5460127af8800a021019366`](https://github.com/Dickey007s/lenovo_agent/commit/0794648477ad0061a5460127af8800a021019366).
- Documentation commit: pending.
- Pull request: [#27](https://github.com/Dickey007s/lenovo_agent/pull/27),
  stacked on the still-open public-suite [#26](https://github.com/Dickey007s/lenovo_agent/pull/26).
  A PR link is delivery traceability, not proof that the change is merged.

## Boundaries

`completed` means a schema-valid read-only result with source membership checks
is available for review. It does not mean the conclusion, arithmetic or office
task is correct. The current Run store is one API process in memory;
`X-User-Id` is an unsigned demo owner header. There is no persistent queue,
distributed Worker lease, writable Artifact workspace, Tool Gateway execution,
real Connector, production authentication or target-user research.
