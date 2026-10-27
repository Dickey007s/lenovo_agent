# DR-0077 case-based copilot review evidence

2026-10-10. Limited Verified for the listed engineering checks. Backend unchanged;
human understanding, business benefit and design-effect hypotheses remain unverified.
Source: [request and research](../sources/USER-FEEDBACK-20261010-copilot-cases.md).
Decision: [DR-0077](../decisions/DR-0077-case-based-copilot-review.md).

## Archive before application edits

Successful archive: `E:/Project/office-agent-archives/20261010-171203/`.
Snapshot `e3970776fa07b8dddf8dd702f0384d4be3a7aece`, reference
`codex/archive-before-copilot-20261010-171203`, original HEAD `fa974ae`.
ZIP: `system-source-and-reports.zip`, 2276 entries. SHA256:
`8B7F8682B4CE5FAB58422E4FB5744AB00905FAD64B8241E4D1F0AA9C2F31003B`.
Temporary Git index and separate commit-tree/ref preserved the original branch,
index and status. ZIP entry count and hashes of three main UI files were checked.
Excluded: ignored outputs, runtime/database, secrets/.env, dependencies/builds.
This is a source/UI/report archive, not a running database/session backup. No full
application restore was tested. RESTORE.md describes a separate-directory restore.

First attempt failed byte hashing because Git normalized line endings. It was not
used as the final archive. The successful second attempt disabled line-ending
normalization in its temporary index; the real Git configuration was not changed.

## Tests and screenshots

- Before application edits: 3 real-API case tests passed, 22.1 seconds. No model
  configuration or database; screenshots `c02-before/c08-before/c11-before.png`.
- Intermediate browser batch: 15 passed, 1 failed. The old source-preview test
  clicked a now-open source disclosure, closed it and could not find its button.
  Adjusted the assertion to require the new open default, then click source preview.
  Failure trace remains under outputs/copilot-cases-20261010/after/.
- Python office-actions + reporting governance: 50 passed, 1.95 seconds;
  outputs/copilot-cases-20261010/backend.xml. This is not all backend tests.
- TypeScript final check passed. A screenshot-helper typing error (Node.remove)
  was corrected to parentNode.removeChild; no product behavior changed.
- Final combined browser batch: **150 passed, 0 failed**, 353.05 seconds. Covers
  harness-workbench, office-actions, office-navigation-races and the three new
  copilot-case-review tests. XML: outputs/copilot-cases-20261010/final-browser.xml.
  This is the stated combination, not every independent report/prototype suite.
- Offline report: 1600 / 1280 / 390 px passed, zero horizontal overflow, zero
  page errors, zero network requests. All six screenshot switches, keyboard
  disclosures, image loads and local links passed. See
  [report-checks.json](../reports/copilot-cases-20261010/report-checks.json).
  A syntax typo in the initial verifier was fixed before this successful run.
- Manually inspected desktop draft/source, complete revision-change screenshot,
  390 px action screenshot, and desktop/mobile report screenshots. Original
  localhost:3000 returned HTTP 200; its service was not restarted.
- No new production build or full backend/PG suite was run. Final source lint
  and scoped git diff --check passed. Original branch is unchanged; new work is
  local/uncommitted, archive is a separate local ref and has not been pushed.

All case material is synthetic. Browser tests exercise the real isolated API and
fixed-rule action code; the broader harness suite also contains mocked snapshots.
Before screenshots use a 1600x1400 viewport with existing scroll containers. Final
after screenshots temporarily expand ancestor scroll containers to include all
controls; no business data is modified for capture. They are not evidence of an
equal-height usability experiment. Mobile has a 390x844 viewport.

## UI-server mapping and limitations

Source = source_excerpt; draft = preview; revision = revision; saved edit = history
event edit_draft; before/after = earlier revision input/content_snapshot; explicit
judgment = decision + decision_note receipt. Unknown is local transport state.
Screenshots and tests do not prove human understanding, business correctness,
external actions, provider quality, database restart or closed Worker recovery.
The report explicitly records that last unresolved boundary as a counterexample.
