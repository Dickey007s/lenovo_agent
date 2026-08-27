# Whole-folder workspace and streaming

## 1. Interaction model

The product is one office folder, not a Scenario chooser. The persistent layout
is:

- left: one hierarchical file tree projected from safe business paths, with
  nested-folder expansion, search, type filters and file metadata;
- center: task composer, Loop contract, file preview, round/branch progress,
  immutable brief history, restore actions, next-task proposals and an
  in-context issue-review page;
- right: actual Agent trajectory, budget, controls and model receipts.

These regions answer five user questions in order: what data exists, what goal
do I have, what evidence did the Agent choose, what did it do, and which next
task can I confirm.

## 2. Browse before invocation

`GET /v1/harness/workspace` returns 15 business folders and 96 file projections.
Opening a file calls the preview route but does not create a Run or invoke a
model. The preview header shows business path, extension, size and row/page
count. A security footer explains integrity, read-only, active-content and
external-resource behavior.

The user may inspect any file. The browser projects `folders[]` and each safe
`display_path` into top-level and nested directories. Expand/collapse, search,
type filters and the open preview are client presentation state and do not
change server truth or Agent scope. Search keeps matching ancestors visible and
temporarily expands them. The UI does not expose profession/role partitions or
file-selection checkboxes, raw internal paths or complete hashes.

## 3. Task composer

The task is always user-authored. Example chips only fill the editable textarea;
they do not start a task. The Run button remains disabled until the instruction
contains at least three characters.

The user sets visible limits for rounds, files per round, model calls and
Agent execution time. The default is 1,200 seconds and the accepted range is
20 to 3,000 seconds. This limit counts only active Agent execution:
`waiting_input` and explicit pause time are excluded. The context contract is
the entire allowlisted workspace; the Agent
chooses a smaller evidence set each round. Changing the instruction or limits
changes the command signature. If a
start response is unknown, the client retries the unchanged signature with the
same idempotency key; a known terminal retry uses a fresh key and independent
Run. Once accepted, the active instruction, whole-workspace scope and limits are
frozen in the Snapshot and task controls are disabled until the Run terminates.

## 4. Preview contract

| Preview | User-visible projection | Safety boundary |
| --- | --- | --- |
| XLSX/CSV | bounded table with row numbers | formulas/macros not executed; first visible sheet for XLSX |
| DOCX | extracted text | no macros; relationship scan; external resources not loaded |
| PDF | page count and extracted text layer | encrypted/oversized input fails closed; active resources not run |
| TXT/MD/JSON/log/code | bounded decoded text | content displayed as text, never executed |

Truncation is explicitly labeled. A parser/integrity error replaces the preview
with a safe error; stale or partial data is not shown as valid.

## 5. Agent Control Loop, result and citation

Each round is a visible `Observe -> Plan -> Act(read-only) -> Verify -> Evidence
Gate` progression. The plan appears only after the server validates the model
candidate. It uses business operation labels. `只写本轮成果` means a logical
read-only Run result in the current round, not that a file or ArtifactVersion
was written.

Before analysis, the round displays `input_file_refs` and `selection_reason` as
“Agent 本轮自主选择”. Planner metadata access does not mean all 96 file bodies
entered the model; only the server-approved, budgeted round files reach the
Analyst.

The server compiles every validated plan unit into a stable Branch and reconciles
its verified/missing refs after analysis. The Evidence Gate shows which branches
are complete, which are waiting and whether another round fits the remaining
budget. If more work is possible, the Run enters `waiting_input` instead of
spending the next round automatically. The user chooses one “继续此分支”; the
versioned `resume` carries that `branch_id`, and nothing is claimed to have
happened until the receipt returns. The next round is restricted to that
Branch's displayed missing files; unselected branches keep their waiting state.
The Gap area projects each unresolved item as one Branch lane rather than a flat
button list: Branch identity and status lead to current safe file labels, then the
Evidence Gate reason and the next available action. These cells join only by
server-owned `branch_id`; they do not imply parallel Workers or successful use of
every listed file.
If the same recovery reaches `stopped/bounded`, there is no next round inside the
old Run. The UI replaces resume controls with unfinished Branch cards. Selecting
one combines its objective with optional user direction and creates a new
whole-workspace Run; the old Snapshot, receipts and ArtifactVersions stay intact.

Opening a Gap first shows an Agent-owned recovery sheet, not a request to edit a
source file. `next_step.recovery_kind` distinguishes malformed analysis,
unresolved source location and ordinary evidence coverage; Branch refs and model
receipts show what was attempted and adopted. A user may inspect candidate files,
but without an Evidence Anchor the page never invents a row highlight. Guidance
is optional: a waiting Run can retry only the affected Branch with an empty
feedback field, while a terminal Run must create a new independent task.

The Branch overview and review sheet distinguish two human jobs before showing
technical detail. A retry-only Branch says “无需核对文件，建议重试”; its first
screen offers one recommended “继续任务，只重试此分支” action, while optional
clues and “为什么停下 / 查看相关文件” stay collapsed. An ambiguous Resolution
says “需要从 N 个原文位置中选 1 个”; no candidate is preselected and accept is
disabled until the user chooses. Neither surface starts another call or charges
the next-round budget before an explicit control receipt. A terminal Run uses a
separate new-task label rather than pretending to resume.

Open human decisions are authoritative in the Snapshot-level
`decision_requests[]`; round-level copies are compatibility projections only.
Closing or pressing Escape exits the review surface before the browser attempts a
versioned `defer`. A successful receipt keeps the packet actionable as deferred;
a 409 or transport failure is displayed outside the closed review surface and the
browser refreshes the Snapshot. The UI never traps the user until a network write
succeeds and never labels a failed defer as recorded.

Each completed round creates an independent append-only logical evidence-brief
ArtifactVersion. The final brief appears only after citation-scope validation
and a server-owned terminal decision; a separate TaskCommit selects the current
version. Restoring a historical version creates another TaskCommit and moves the
current pointer without deleting any version or changing an original office
file. Every result remains labeled for human review. A citation button resolves
against the workspace projection, selects that file and switches back to its
preview. A Finding, Branch or Evidence Gap can also open a full-page review
surface: it presents the business claim, round/branch location, authoritative
server record, associated refs and the same safe Preview response together.

For a new Finding, the Analyst also supplies short verbatim quote candidates.
The server resolves them against the exact bounded content used in that round,
requires a unique text/table match and publishes `evidence_anchors`. The review
surface renders those Anchors as a numbered evidence chain. Selecting one
switches to its file, displays the server locator and highlights the matching
safe-preview lines or table row. The browser never derives positions from the
Finding prose. If an old result or non-Finding record has no Anchor, the page
states that only file-level review is available and does not invent a highlight.
The Git-like history is an information structure, not a source-file diff or a
claim that semantic correctness has been proven.

An adopted Finding may also carry `fact_summary`, `impact` and a structured
`review`. The review page presents these as `1 发生了什么 -> 2 不处理的影响 ->
3 现在需要谁做什么`, with the evidence index and actual Preview side by side.
When human judgment is required, A/B/C choices state what each choice means,
which Branches and sources will be revisited, the estimated additional rounds
and `external_action=none`. Optional feedback is recorded with a versioned
`decision` receipt. Accepting then starts an independent read-only Run; declining
does not start work, and closing records `defer`. No path claims that an office
file was modified.

A model candidate that fails server validation is shown as `未采用`; at most
one bounded repair attempt may follow and it consumes the same model-call
budget. The rejected candidate itself never becomes the visible plan.

The final result may contain up to four proposed next tasks. They do not change
server state by themselves. `查看形成依据` shows the current result's Finding
refs as context and explicitly states that `follow_ups` has no per-item citation
contract. Clicking `确认并启动` copies the exact proposal into a new start request
and creates an independent Run; dismissing, reviewing or editing a proposal has
no side effect on the completed Run.

## 6. Call receipts and trace

The right pane distinguishes:

- `未调用`: no provider request occurred;
- `已采用`: provider returned and server checks accepted the output;
- `未采用`: provider returned but checks rejected the output.

Elapsed milliseconds are an observed call duration, not production SLA or cost.
The trajectory uses named server events and business summaries. It also exposes
the authoritative round, budget usage and safe-point controls. Prompt,
chain-of-thought, raw provider response, token traces and validator code stay
hidden.

`pause` and `stop` take effect only at a safe point between model calls;
`steer` is recorded for the next round; `resume` continues a selected waiting
branch; `rollback` restores a historical logical brief only after completion.
Each command carries Owner, expected version and an idempotency key. Branch
resume additionally carries `branch_id`, and restore carries `artifact_version`.
The UI waits for the returned Snapshot instead of pretending that a click
already changed the server.

The current Run id is kept in browser session state. After refresh, the client
first reconciles that id with `GET /runs/{run_id}`; when no local id exists it
may discover the most recent nonterminal Owner Run through `GET /runs`. A
`checkpoint_recovered` badge is shown only when that server event exists.

## 7. Streaming and reconciliation

For a nonterminal Run the client opens:

```text
GET /v1/harness/runs/{run_id}/events?after={last_observed_sequence}
```

Rules:

1. apply only events for the current Run;
2. never decrease Snapshot version or last event sequence;
3. use SSE only as ordered change notification;
4. read the current Snapshot after business events;
5. on nonterminal failure, reconnect from `after=N`;
6. after a terminal event, close the stream and perform final GET.

The header says the service is available when HTTP is reachable. It says the
trajectory is live only while an EventSource is open. Transport state is a
browser fact, not a server task phase.

## 8. Failure and recovery

| Failure | Visible state | Preserved | Recovery |
| --- | --- | --- | --- |
| API offline | workspace unavailable/offline | local task draft when possible | bounded retry and explicit retry |
| manifest integrity invalid | integrity-specific unavailable state | no stale catalog | repair/import source then retry |
| preview error | file-specific safe error | file list and task draft | reopen or choose another file |
| unknown start result | reconciling | same instruction/limits/key | replay identical request |
| model/schema/policy failure | safe stop plus receipt | whole-workspace contract, instruction and completed rounds | revise or create a fresh Run |
| rejected plan candidate | not adopted plus bounded retry | frozen contract and used-call count | server retries once if budget allows; otherwise fails closed |
| one or more source locations cannot be resolved | rejected/partial-adoption trace | valid Findings, approved Plan, files, Branches and receipts | retry once; adopt the valid subset or pause one candidate Branch with `recovery_kind=source_location` |
| one source quote has multiple real matches | `evidence_disambiguation_required` + `EvidenceResolution(status=ambiguous)` | completed Branches, ArtifactVersion and all candidates | compare candidates; record the selected candidate; steer and resume only its Branch |
| pending human decision is closed | `decision_recorded(action=defer|cancel)` | Finding, evidence, user feedback draft and all execution facts | defer stays actionable; cancel closes the packet without marking the source rejected; use a fresh version for any later control |
| repeated malformed analysis output | structure-rejected trace | approved Plan, files, Branches and both call receipts | pause one candidate Branch with `recovery_kind=analysis_output`; do not expose raw response |
| evidence insufficient | Agent execution-gap sheet, waiting Branch, missing evidence and model adoption receipt | prior rounds, all Branch states, versions and citations | leave guidance empty and retry one Branch, optionally add direction, or preserve the gap |
| recovery reaches budget terminal | `status=stopped`, `brief.outcome=bounded`, candidate Branches and `recovery_kind` | old Run, Plan, call receipts, Branch state and ArtifactVersions | choose one unfinished Branch, add optional direction and POST a new Task Contract; never resume the terminal Run |
| pause/steer/stop requested | pending until a safe point | current Snapshot and command receipt | reconcile returned version; resume or inspect terminal brief |
| human reviews or pauses for a long time | active elapsed is frozen while waiting/paused | consumed active time, Branch state, versions and receipts | resume from the same active budget; wall-clock waiting does not force an immediate stop |
| SSE interruption | reconnecting | current Snapshot and last sequence | GET plus `after=N` |
| browser refresh | current Run and sequence restored | task, rounds, receipts and controls | GET current Run, then SSE `after=N` |
| API restart with PostgreSQL | recovered checkpoint, paused | completed rounds, Branch states, events, command receipts and independent ArtifactVersion/TaskCommit rows | inspect trace, then explicitly resume the intended Branch |
| historical result restored | current pointer changes to a verified old brief | every ArtifactVersion and prior TaskCommit | review restored brief or select another version; original files stay unchanged |
| API restart without PostgreSQL | no recoverable Run | browser task draft only | start a new Run or configure `DATABASE_DSN` |

DR-0032 clarifies the PostgreSQL boundary: an open `DecisionRequest`, its
`EvidenceResolution` candidates and a recorded `DecisionRecord` are durable only
because they are nested in the Run Snapshot JSONB. ArtifactVersion and TaskCommit
remain separate append-only rows. This is not an independent decision ledger,
source-revision constraint, CAS or multi-instance guarantee. A running round
interrupted by restart is intentionally not replayed.
The real PostgreSQL 17.11 sequential gate now verifies pending-decision restart,
target-Branch-only resume, v1/v2 preservation and a second restart. The browser
path separately verifies desktop and 390 px candidate comparison, defer-then-final
decision, cancel and reconnect; neither gate is a user study.
DR-0034 adds only a browser projection gate: deterministic E2E checks retry-first
and ambiguous-choice-first screens, disabled accept before selection, collapsed
optional details and 390 px overflow. It does not change the DR-0032 persistence
or recovery state machine.

## 9. Responsive behavior

Desktop keeps file manager, work area and activity pane visible. Narrow layouts
stack the same functions rather than shrinking the file list into an unreadable
diagram. The tested 390 px path keeps file browsing, task input, loop bounds,
rounds, Evidence Gate, controls, final brief and citation actions touch-usable
and avoids page-level horizontal overflow. Tables may scroll inside their own
preview region.

## 10. Hidden details

Ordinary DOM must not contain benchmark task prompt/rubric/solution, raw path,
digest, model Prompt, chain-of-thought, raw response, credentials, internal
effect/gate enums, unvalidated quote candidates or low-level logs. The UI may
show business labels, bounded content, server-resolved Evidence Anchors, call
receipts, validation status, Branch states, evidence gaps, controls and
citations because those facts help the user decide or recover.
The current logical evidence briefs and TaskCommits are independent append-only
records and their safe projections are also present in the Run Snapshot. This
proves result-history preservation, not a source-file write, semantic truth,
Tool Gateway call or external action.
