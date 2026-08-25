# SCENARIO-008: Browse one office folder and author an arbitrary task

| Field | Value |
| --- | --- |
| Scenario ID | `SCENARIO-008` |
| Status | `Ready for final evidence`; user comprehension and value remain `Draft` |
| Decision | [`DR-0022`](../decisions/DR-0022-workspace-folder-and-arbitrary-task-contract.md) |
| Sources | `USER-FEEDBACK-20260825-WHOLE-FOLDER-14`, `FORTE-PUBLIC-SUITE-INVENTORY-20260825` |

## Target user and trigger

The target user is an office knowledge worker or product reviewer who enters a
shared business folder without a preselected Demo. They need to inspect the
available material, choose a defensible scope and ask a task-specific question.

## Current pain

A registered Scenario catalog makes the experience resemble a scripted demo.
Users cannot first build their own understanding of the workspace, and it is
unclear whether the Agent can combine files outside a prepared example.

## Goal and completion condition

The user can browse all available public FORTE folders, open CSV/PDF/DOCX/TXT
and spreadsheet/code previews, select files across folders, write an original
task and obtain an initial cited result. Completion requires every displayed
citation to reopen one of the frozen selected files. The result remains marked
for human review and must state that no external action occurred.

## Primary journey

1. The root page loads one office workspace and displays folder/file counts.
2. The user searches folders and opens file metadata before invoking a model.
3. The server validates the file byte and returns a bounded read-only preview.
4. The user selects one to twenty files from any folder and writes a task.
5. The server freezes the selected refs, then the Planner returns intent that
   is compiled and validated by server policy.
6. The Analyst receives only safe content from the selected files.
7. The user follows named events and two model receipts, then reviews the
   validated plan and initial result.
8. Clicking a citation reopens the exact business-labeled source preview.

## Concrete office tasks

| Task | File mix | Expected interaction | Current boundary |
| --- | --- | --- | --- |
| Cross-period finance review | three XLSX files | select periods, ask for stable balances, reopen cited sheets | model numbers still need deterministic checking |
| Onboarding allocation | CSV plus PDF policy | inspect roster and rule, ask for exceptions, pause on ambiguous mappings | read-only result; no account or purchase action |
| Resume/JD comparison | DOCX and PDF | select one JD and candidate files, compare evidence per criterion | sensitive decision remains human-owned |
| Release-readiness review | Markdown plus XLSX | combine requirements and test reports, inspect conflicting facts | no production release or issue creation |
| Incident diagnosis | TXT log | ask for a timeline and bounded remediation options | commands are suggestions only |
| Cross-folder synthesis | files from two professions | author an original question not present in FORTE tasks | source scope is enforced; semantic quality is unproved |

## Failure and recovery

| Failure | Visible behavior | Recovery |
| --- | --- | --- |
| workspace manifest or file hash invalid | integrity-specific unavailable state; no model call | repair/reimport bytes, then retry |
| unsupported/encrypted/active file | preview unavailable with safe reason | choose another file or add a reviewed adapter |
| no files or short instruction | Run action disabled | select explicit scope and complete the instruction |
| model output fails schema/policy | receipt says returned but not adopted; Run safely stops | revise instruction or retry a new round |
| SSE disconnects | reconnecting state and `after=N` resume | server Snapshot remains authoritative |
| result cites an unselected file | deterministic result rejection | no result is shown as completed |

## Frontend acceptance

- The main page contains no Scenario/Demo selector.
- File browsing, task authoring, preview and trajectory are all reachable on a
  390 px viewport without horizontal page overflow.
- CSV/PDF/DOCX/TXT preview security facts are visible without raw path/hash.
- Model call and adoption are visually separate from plan/result validation.
- A citation button opens the referenced source file.
- The ordinary DOM contains no task prompt, rubric, solution, absolute path,
  digest, Prompt, chain-of-thought or raw policy identifier.

## Research boundary

This scenario is derived from Stakeholder feedback, FORTE public files and
mainstream Agent product/documentation review. It is not yet supported by a
target-user study. Whether the folder-first flow lowers cognitive load or
improves trust remains a hypothesis for formative testing.
