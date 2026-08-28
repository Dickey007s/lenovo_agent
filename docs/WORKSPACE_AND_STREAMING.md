# Whole-folder workspace and streaming

## 1. Interaction model

The product is one office folder, not a Scenario chooser. The persistent layout
is:

- left: one hierarchical file tree projected from safe business paths, with
  nested-folder expansion, search, type filters and file metadata;
- center: task composer, Loop contract, file preview, round/branch progress,
  verified Run Workspace files, immutable brief history, restore actions,
  next-task proposals and an
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
Agent execution time. Defaults are 12 rounds, 16 files per round, 30 model
calls and 7,200 seconds; accepted maxima are 24/24/60/14,400. The time limit
counts only active Agent execution:
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

Each round is a visible `Observe -> Plan -> Act -> Verify -> Evidence Gate`
progression. The plan appears only after the server validates the model
candidate. A model plan label such as `只写本轮成果` remains intent, not execution
evidence. For twelve fixed local capabilities, the admitted server adapter may
then create a real isolated Run Workspace file and run a deterministic verifier.
Only `workspace_artifacts[]`, `effect_receipts[]` and downloadable bytes prove
that bounded effect; other plans remain read-only analysis.

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

DR-0036 adds an outcome-first exception without changing those recovery controls.
If every visible Run Workspace Artifact passed but the latest round still waits on
source location, the Artifact/download/check section is shown first and the Gate
label becomes “成果可用，审计待补充”. Gaps sharing the same candidate source refs
and failure detail are grouped into one audit item and say that the missing fact is
the Agent's exact source location, not a missing file or incorrect date. Different
failures in the same file stay separate. This grouping is client-only; one real
Branch ID is still used for any resume, and the Run is not presented as `completed`.

DR-0037 makes each Run Workspace file explain itself before download. The card
shows service-owned `covered_period`, `statistic_basis`, `purpose` and optional
`record_count`; its `source_file_refs` are labeled as content sources. The TC-05
CSVs therefore each show one 2026 content source, while the cross-period note
shows all three periods. The EffectReceipt still exposes the adapter's full task
context. Review text, evidence excerpts and safe previews use a larger tested
type scale; tables retain inner scrolling so 390 px does not create page-level
overflow.

DR-0038 removes Runtime vocabulary from the first screen of a `source_location`
recovery. If all visible Artifacts passed, the page says the files are generated,
names the known source file, explains that only its exact row/cell is missing and
offers “查找原表格位置” plus “查看已生成成果”. If no verified Artifact exists or
the Run is terminal, the status and action change. Branch/Gap/Resolution facts
remain in collapsed technical details; only an explicit primary action spends the
next Branch budget.

DR-0039 gives process-design Artifacts an explicit execution boundary. Optional
Artifact facts `deliverable_type`, `key_outputs`, `review_guidance` and
`execution_summary` appear before technical receipts. For TC-10 the card and the
task close say that only a flow-design DOCX was generated; “发起外呼拨号” and
“写 CRM” are document nodes, while EffectReceipt proves no dialing, CRM write or
SMS action occurred. The DOCX itself repeats its question, source, boundary and
review responsibility before the full flow.

DR-0040 gives code-change Artifacts an explicit review and self-test surface.
Optional `key_outputs_label` names the list as “文件变更” or “验证结论” instead
of borrowing TC-10's terminal-state vocabulary. Optional `self_test` contains
the original instruction, expected files, commands, expected checks and failure
signals. The browser shows these before technical receipts; commands wrap at
390 px and do not execute when the card opens. TC-02 still writes only a fixed
algorithm-013 copy. Passing checks mean the downloaded copy compiled and its
declared tests matched execution, not that the original repository was changed
or automatically merged. The card also states that the current default policy
deterministically steps through planned tools and is replaceable; it does not
claim that a model inside the ZIP selects actions from Observations. Outer
Planner/Analyst receipts remain in the Run trace, not in the Artifact policy.

DR-0041 makes the TC-04 test evidence inspectable before download. The browser
renders `self_test.test_suites[]` as five readable suite summaries with real test
files and 15/16/15/23/48 counts; IDs are collapsed and scroll inside the suite.
The server asserts that these public IDs, the ZIP `test-manifest.json` and actual
collected IDs are one set. The UI never invents placeholder names, never reads
benchmark task/rubric/solution files, and opening the list does not execute tests
or spend model budget. Desktop uses at most three columns and 390 px uses one.

DR-0042 uses the same progressive disclosure for TC-12. The Artifact summary
first shows Stage A/B/C red evidence, Stage D `71/71`, four changed files,
per-file coverage and the manual-merge boundary. Its `self_test.test_suites[]`
then shows the real metrics/data/filter files and 23/20/28 counts; test IDs are
collapsed and scroll inside the card. Opening the list or downloading the ZIP
does not rerun a model, edit FORTE input or create a PR.

DR-0043 applies progressive disclosure to business Gate outcomes. The TC-11
surface first renders `business_gate_outcome.decision`, the count of failed
formal Gates and each Gate's source-owned formula. Auxiliary quality metrics and
the 18-row ledger stay expandable. Artifact cards then show deterministic
verification and downloads with an explicit warning that formula/source/file
checks do not mean the business Gates passed. A failed Verifier keeps the cards
red and suppresses a reliable-report claim even when a source-derived business
decision is otherwise available. Opening the outcome does not call a model,
write configuration or execute a release.

DR-0044 applies the same truth separation to TC-07. The result area first shows
`legal_review_outcome.decision`, then three parallel states: deterministic
source/file verification, legal business Gate and signing/human review. Summary
counts come from the service-owned 126-row assessment ledger. Six document
sections are collapsed by default; opening one exposes its 21 rule records with
status, level, source location, excerpt, fact, judgment, reason, owner,
remediation and exit condition. `unverifiable` is displayed as missing material,
not as pass or fail. A lawyer-license field without a Registry/Connector receipt
therefore stays visibly unresolved. Opening these details does not call a model,
validate a signature, sign a document or make an authorization effective.

DR-0045 applies the same truth separation to TC-06. The result area first says
that this is a human-review aid, not a hiring or rejection decision, then shows
three parallel states: deterministic source/file verification, role-matching
advice and final HR decision. Dynamic totals come from the service-owned
`candidate_review_outcome`; the browser does not recompute them. Role sections
contain five candidate cards, collapsed by default. Opening one exposes every
condition's four-state result, JD and resume locations/excerpts, source fact,
judgment, human follow-up and exit condition. `unverifiable` is displayed as
missing evidence rather than a negative result, while an explicit JD exception
stays an HR decision. The candidate list uses content-width-driven `auto-fit`
cards and falls back to one column in the narrow center pane and at 390 px.
Opening these details does not call a model, change ATS state, notify a candidate
or execute a hiring action.

DR-0046 applies the three-state projection to TC-05. The result area first says
that the output is a cross-period risk candidate review, not a payment,
write-off, posting or bad-debt decision. It then shows deterministic source/file
verification, the current 2026 payable/receivable totals plus zero or more
candidates, and the still-pending finance disposition as separate service-owned
facts. A positive candidate uses an amber review state rather than a system-
failure state. Expanding a candidate shows its subject, counterparty, the three
period amounts and source locators; doing so is browser-only and does not call a
model, alter a workbook or perform an accounting action.

DR-0047 gives TC-10 a four-state projection. The first screen says that the
output is a flow-design document, not dialing, CRM/SMS execution or legal
advice. It then shows deterministic source/DOCX/graph checks, dynamic rule
coverage and reachable terminals, pending business/compliance approval, and
the explicit no-action receipt as separate server-owned facts. Expanding a
rule reveals its approved line locator, excerpt and mapped node/edge/guard/
terminal IDs. A legal source mutation changes these counts and parameters from
the public outcome; the browser does not parse Markdown, invent a percentage or
call a model when details open. Unsupported or conflicting rules remain visible
as a failed effect rather than being hidden behind an old `13/13` label.

DR-0048 further requires sentence-fragment completeness within each approved
line. A second normative sentence appended to a recognized TIME/FREQ/IDENTITY
line becomes its own public rule and mapping when supported, or stops the fixed
adapter when unknown/conflicting. The UI only renders the resulting service-
owned `rules[]`; sharing a source locator never allows it to merge two rules or
guess that a keyword was covered.

DR-0049 gives TC-13 a four-layer projection. The first screen says that the
output is public-sample cleaning and a strategy draft, not customer research,
sales-effectiveness proof or CRM execution. It then shows deterministic
source/Markdown/CSV verification, dynamic cleaning and profile facts plus the
review-required duplicate-policy assumption, a strategy template awaiting a
sales owner, and the explicit no-action receipt. Opening a sample reveals its
approved CSV row, raw-to-cleaned transformations, all matched profiles,
priority decision and final label/exclusion; opening a rule reveals its approved
locator. Canonical input displays zero priority witnesses rather than pretending
the priority order ran. These panels render `customer_segmentation_outcome` and
do not parse source files, call a model or mutate CRM state.

DR-0050 gives TC-14 a four-layer incident-review projection. The first screen
states that the output is an offline review of a fixed public log, not online
monitoring, a root-cause conclusion or command execution. It then separates
deterministic source/Markdown/CSV verification, observations and contradictory
source facts, hypotheses/proposals awaiting SRE review, and the explicit fact
that no Elasticsearch or business action occurred. Expanding an observation,
conflict, hypothesis or proposal reveals only service-owned safe locators,
support/counter evidence, risk, unresolved target, preconditions, rollback,
verification and official API semantics. Expansion is read-only, calls no
model and never executes a command.

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

### 5.1 Verified Run Workspace files

When a fixed local capability is admitted, the center pane adds a compact
Artifact section that answers four separate questions: what file was created,
which deterministic checks passed, which FORTE sources were read, and what did
not happen. CSV/Markdown/DOCX/ZIP files download through the Owner/Run-scoped
Artifact route. The public UI never receives the server storage path or private
digest. The original FORTE source remains read-only and every receipt states
`external_action=none`.

Each Artifact retains its own `checks[]` so the user can review that file in
isolation. The section header, task conclusion, EffectReceipt observation and
verification event count unique checks by server-owned `check_id`; repeated
projection of the same checklist across multiple deliverables is shown as a
shared checklist and is never multiplied by the number of files.

The section deliberately keeps three statuses separate: Planner/Analyst
`called/output_used`, deterministic effect `passed/failed/blocked`, and overall
Loop `waiting/completed/failed`. A verified Artifact remains visible if the later
Analyst result is rejected; conversely, an adopted model answer without a passed
Artifact validator is not presented as task-effect success. TC-03/08/09 show an
external-boundary receipt instead of fabricated SQL/Web/cron execution.

## 6. Call receipts and trace

The right pane distinguishes:

- `未调用`: no provider request occurred;
- `已采用`: provider returned and server checks accepted the output;
- `未采用`: provider returned but checks rejected the output.

The trace also projects `deterministic_office_tool_started`,
`run_workspace_artifact_written`, `deterministic_verification_completed` and
`scenario_effect_failed` or `scenario_effect_bounded`. These events are ordered change notifications; the
Snapshot remains authoritative.

For TC-04, the started event is committed before the roughly one-minute fixed
builder begins. Its message says that the isolated copy and real tests are in
progress and intentionally omits a percentage. The Runtime freezes all 46
allowlisted inputs on the event-loop thread, then passes only that immutable
view to `asyncio.to_thread`; the worker cannot re-read the live Catalog. During
this wait, workspace browsing, health, Run GET and SSE remain responsive.

This is an interaction guarantee for one API process, not a Worker platform.
The in-process thread and its subprocesses do not survive an API restart;
PostgreSQL restores the last committed Snapshot and pauses under the existing
checkpoint rule. A failed builder emits `scenario_effect_failed` and no green
Artifact/EffectReceipt.

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
| PDF/DOCX layout splits one otherwise exact quote | no user interruption when the normalized location is unique | strict candidate, safe Preview line map and all scope checks | ignore layout whitespace/punctuation only after strict matching fails; require one location, otherwise keep ambiguous |
| all verified observed dates in a Finding are outside the explicit instruction window | `analysis_scope_filtered` trace; no Gap or DecisionRequest for that Finding | in-scope Findings, Artifact and model receipt | omit only the out-of-window Finding; unsupported range expressions are not guessed |
| model asks for a human decision without contradiction evidence | `decision_gate_suppressed` trace; ordinary Finding review | exact support/expected Anchors and Artifact | do not create an artificial DecisionRequest; real contradiction Anchors still use the decision protocol |
| Artifact passed while source location still waits | outcome/download first, “成果已生成，还有 N 条说明缺少原表格位置”, same-source/same-failure gaps grouped | Artifact/EffectReceipt, every underlying Branch/Gap and current version | view generated files or explicitly resume one real Branch; technical facts stay collapsed; do not call the Run completed, collapse distinct failures or merge server Branches |
| one source quote has multiple real matches | `evidence_disambiguation_required` + `EvidenceResolution(status=ambiguous)` | completed Branches, ArtifactVersion and all candidates | compare candidates; record the selected candidate; steer and resume only its Branch |
| pending human decision is closed | `decision_recorded(action=defer|cancel)` | Finding, evidence, user feedback draft and all execution facts | defer stays actionable; cancel closes the packet without marking the source rejected; use a fresh version for any later control |
| repeated malformed analysis output | structure-rejected trace | approved Plan, files, Branches and both call receipts | pause one candidate Branch with `recovery_kind=analysis_output`; do not expose raw response |
| evidence insufficient | Agent execution-gap sheet, waiting Branch, missing evidence and model adoption receipt | prior rounds, all Branch states, versions and citations | leave guidance empty and retry one Branch, optionally add direction, or preserve the gap |
| recovery reaches budget terminal | `status=stopped`, `brief.outcome=bounded`, candidate Branches and `recovery_kind` | old Run, Plan, call receipts, Branch state and ArtifactVersions | choose one unfinished Branch, add optional direction and POST a new Task Contract; never resume the terminal Run |
| pause/steer/stop requested | pending until a safe point | current Snapshot and command receipt | reconcile returned version; resume or inspect terminal brief |
| human reviews or pauses for a long time | active elapsed is frozen while waiting/paused | consumed active time, Branch state, versions and receipts | resume from the same active budget; wall-clock waiting does not force an immediate stop |
| deterministic local effect fails | failed EffectReceipt and check details | source bytes, model receipts, prior Branches and any earlier verified Artifact | inspect the failed check; fix the owned adapter/validator and start a fresh run without altering FORTE inputs |
| task requires SQL/Web/cron authority | `blocked_external_boundary` receipt | user instruction, frozen scope, model receipts and prohibited-side-effect list | configure and authorize a real Connector later; do not treat safe blocking as effect success |
| Artifact download fails integrity | file-specific fail-closed error | Snapshot metadata and all other Run facts | keep the failed bytes hidden; repair the Artifact store and retry the same Owner/Run-scoped download |
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
Run Workspace Artifact metadata is likewise restored through Snapshot JSONB;
same-host bytes persist in the separate isolated Artifact store and are rechecked
at download. This does not prove transactional database/filesystem commit,
multi-host durability or object-store replication.
The real PostgreSQL 17.11 sequential gate now verifies pending-decision restart,
target-Branch-only resume, v1/v2 preservation and a second restart. The browser
path separately verifies desktop and 390 px candidate comparison, defer-then-final
decision, cancel and reconnect; neither gate is a user study.
DR-0034 adds only a browser projection gate: deterministic E2E checks retry-first
and ambiguous-choice-first screens, disabled accept before selection, collapsed
optional details and 390 px overflow. It does not change the DR-0032 persistence
or recovery state machine.
DR-0036 adds deterministic Anchor/scope/Gate admission rules plus a browser-only
same-source/same-failure audit grouping for verified outcomes. It does not add semantic proof,
a generic task-filter compiler or an Artifact-driven override of Loop terminal state.
DR-0037 adds Artifact meaning fields and corrects TC-05 attribution. It does not
turn Finance-018 into a reusable accounting ontology or prove user comprehension.
DR-0046 replaces the old zero-candidate success assumption with independent
source and output recomputation. It remains a fixed exact-balance heuristic and
does not add currencies, legal entities, ageing, in-period activity, write-off
policy, a Connector or a general ledger.
DR-0038 adds a three-state user-language projection and target-Branch action. It
does not prove the Agent explanation, user comprehension or a new recovery protocol.

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
citations because those facts help the user decide or recover. Verified Artifact
metadata, checks, downloads and bounded effect receipts are also public because
they are the execution evidence for the twelve fixed local capabilities.
The current logical evidence briefs and TaskCommits are independent append-only
records and their safe projections are also present in the Run Snapshot. This
proves result-history preservation, not a source-file write or semantic truth.
The fixed local adapters prove only their named validators and isolated output;
they are not a general Tool Gateway, Connector or external action.
