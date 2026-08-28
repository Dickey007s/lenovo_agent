# UI-server fact matrix

This is the current `DR-0036` outcome-first evidence-localization surface on top
of the `DR-0035` Scenario Effect Gate and Run Workspace Artifact surface,
`DR-0034` one-action recovery, `DR-0033` closable
Branch-lane review, `DR-0032`
persistent decision/recovery contract, `DR-0029`
server-verified Evidence Anchors and `DR-0026`
branch-selective append-only result loop and `DR-0024` whole-workspace contract.
`DR-0025` group-resume and embedded-artifact facts remain a historical baseline
in their dated Evidence only.

下表中的 Authority 列即“服务端权威字段”；浏览器草稿与传输状态会明确另列，
不能冒充业务事实。
Prompt、思维链、原始模型响应、绝对路径、哈希和内部策略标识在普通界面默认隐藏。

## 1. File-manager workspace and task draft

| UI state/action | User-visible meaning | Authority | Transition/recovery/idempotency | Hidden |
| --- | --- | --- | --- | --- |
| Service available | HTTP API and workspace projection succeeded | health/workspace response | may browse or start; not an SSE fact | previous stream, network stack |
| Workspace unavailable | service or catalog cannot provide authoritative files | fetch failure or controlled 503 | retry; no static fallback files | stack trace, partial/stale catalog |
| Whole repository tree | 15 top-level folders, nested subfolders and 96 public inputs | `GET /v1/harness/workspace` `folders[]` + safe file `display_path` | tree projection is read-only until refreshed | task prompt, rubric, solution, role partitions, raw path/hash |
| Expand/search/type filter | client changes visible branches of the file tree; search keeps matching ancestors open | browser state over server projection | no server mutation and no Agent scope change | no claim that visible files are the Run input |
| File preview selection | choose what the user is looking at | browser state + preview GET | does not constrain Agent evidence | internal ref/path/hash |
| Task composer | user writes the actual instruction | browser draft; POST/Snapshot `instruction` | required 3-2,000 chars | hidden benchmark-task fallback is forbidden |
| Loop bounds | user chooses hard limits before invocation | browser draft; Snapshot `contract.options` | defaults 12 rounds/16 files/30 calls/7200s; bounds 1-24/1-24/2-60/20-14400s | token/cost estimates not owned by server |
| Run start | server accepted one independent bounded whole-workspace contract | POST Owner/key/version/instruction/options | unknown response reuses same key; changed or known retry uses new key | internal command signature |
| Frozen active contract | current instruction, all stable refs and limits cannot silently change | Snapshot `scope_mode/allowed_file_refs` and run-active state | composer/options disabled until terminal | local edits pretending to affect active Run |

## 2. File preview

| UI state/action | User-visible meaning | Authority | Transition/recovery | Hidden |
| --- | --- | --- | --- | --- |
| Metadata | business path, type, bytes, row/page count | workspace/file projection | selecting file triggers preview GET only | raw relative/absolute path and digest |
| Table preview | bounded XLSX/CSV rows | preview response | parser/integrity failure replaces content | macros/formula execution/full workbook internals |
| Document preview | bounded DOCX/PDF text | preview response | encrypted/unsafe/unsupported is unavailable | embedded active content/external loads |
| Text preview | bounded TXT/MD/JSON/log/code | preview response | displayed only, never executed | shell/script execution |
| Security footer | integrity verified, read-only, no active/external resource execution | `BenchmarkPreviewSecurity` | cannot be inferred from extension alone | scanner implementation details |
| Citation click | reopen a finding's selected source | result `file_ref` resolved through workspace | selects file and switches to preview | source path/hash |
| Review-page source switch | compare one Gap/Finding with an associated safe file | Gap/Finding refs resolved through workspace + Preview GET | changes only the review-page preview; Run version is unchanged | source file mutation, semantic proof, raw ref/path/hash |
| Finding evidence selection | jump to one server-verified source location | Finding `evidence_anchors[].file_ref/locator_kind/start/end` + Preview GET | browser switches file, scrolls and highlights; Run version is unchanged | client-guessed position, source Diff or semantic proof |

## 3. Agent Control Loop, plan and result

| UI state | User-visible meaning | Authority | Ordered transition | Hidden |
| --- | --- | --- | --- | --- |
| Whole index frozen | the Run can search the complete allowlisted repository | `workspace_index`, `contract.scope_mode`, `source_documents[]` | seq 1 | internal path/hash/file bodies |
| Round started | another bounded Observe cycle began | `round_started`, `rounds[]` | round number and remaining budget increase monotonically | hidden subtask prompt |
| Planner started/returned | provider call stage, not acceptance | `planning_started/completed` | per round | Prompt, CoT, raw candidate |
| Planner receipt | not called/adopted/not adopted and elapsed time | round `model_receipt.called/output_used/elapsed_ms` | independent of plan validation | token/provider trace |
| Candidate rejected | returned candidate was not adopted | `plan_validation_rejected` | at most one repair using the same call budget | raw validator/provider error |
| Validated plan | server compiled/accepted this round's work intent | `plan_validation`, round public plan | after accepted candidate only | raw tool/effect/gate IDs |
| Deterministic local effect started | one fixed server-owned capability matched the user instruction; its complete allowlisted inputs were frozen before dispatch | `deterministic_office_tool_started.details.capability_id/scenario_id/frozen_source_file_count/external_action`; current Snapshot/version | persisted after plan validation and before the synchronous builder enters `asyncio.to_thread`; no model field can create this authority | private adapter implementation, input bytes, fabricated percentage or claim that work already completed |
| Long local effect remains observable | the fixed builder may still be running, while workspace, health, Run GET and SSE remain usable | open nonterminal Snapshot plus ordered started event; HTTP/SSE responsiveness gate | builder reads only a frozen Catalog view; one in-process `(owner, run, capability)` claim rejects duplicate dispatch | multi Worker, durable Tool Gateway, resumable subprocess or production SLA |
| Local effect failed | the fixed builder/verifier did not complete and no verified deliverable was committed | `scenario_effect_failed`, then ordinary fail-closed Run facts; no new Artifact/EffectReceipt | failure event is persisted before the Run failure transition; prior Snapshot facts remain | failed package exists, old Artifact was overwritten or automatic recovery succeeded |
| Run Workspace file available | a real isolated file was written and can be downloaded | `workspace_artifacts[]`, `run_workspace_artifact_written`, Owner/Run-scoped Artifact GET | file appears only after store write; download rechecks private size/digest | storage path, private digest, claim that FORTE source changed |
| Artifact meaning before download | exact period, row basis, use and optional record count declared by the fixed server adapter | Artifact `covered_period/statistic_basis/purpose/record_count` | projected only when fields are present; `record_count` is checked against generated content | inference from filename, summary or number of refs; claim of general finance semantics |
| Process-design meaning before download | the file is a design deliverable, what it answers, its key outputs and why a human still reviews it | Artifact `deliverable_type/key_outputs[]/review_guidance` | projected only from fixed-adapter fields; TC-10 lists six terminal states | inference from model prose, general outbound completeness or approval |
| Code-copy change meaning before download | the isolated project copy, changed/preserved files, default policy boundary and human merge boundary | Artifact `deliverable_type/key_outputs_label/key_outputs[]/review_guidance/execution_summary`; `changes.json.internal_action_policy/model_driven_internal_react_verified` inside the download | TC-02 fields come from the fixed adapter after the real copy/test path; outer Planner/Analyst receipts remain separate | original FORTE tree changed, PR created, arbitrary repository refactored, model autonomously selected actions inside the ZIP |
| Downloadable self-test card | user can reproduce the fixed checks after download | Artifact `self_test.instruction/expected_files/commands/expected_checks/failure_signals` | rendered read-only; opening never executes a command or spends model budget | browser executed the commands, test count is a permanent business maximum, OS-level sandboxing |
| Visible real test inventory | user can see which suites, files and collected tests produced the total | Artifact `self_test.test_suites[]/test_manifest_file/test_manifest_matches_collected`; ZIP `test-manifest.json/test-results.json` | TC-04 and TC-12 services compare suite IDs with builder manifest and actual collected IDs; browser only renders them | placeholder test names, hidden benchmark files, count-only proof or browser-generated test facts |
| TC-12 red-to-green repair | the same public Vitest set first exposes the original defects and later validates the isolated fix | Artifact `key_outputs/checks[]`, `self_test.test_suites[]`; ZIP stage A/B/C/D JSON, `changes.patch`, coverage and independent-rerun receipt | show three red stages before final 71/71, four changed files, per-file thresholds and manual merge boundary | FORTE source changed, arbitrary JavaScript executed, tests installed online, OS network isolation or PR created |
| TC-12 fixed-command failure | the isolated copy and failure evidence were preserved, but the package is not verified for merge | failed Artifact `verifier_status/checks[]`, failed EffectReceipt, conditional `review_guidance`; ZIP stage D JSON, coverage and independent-rerun receipt | never project 71/71 as green; show `当前包不得合并`, the three evidence paths and `重新启动新的 TC-12 Run` | successful Artifact effect, safe-to-merge package, in-place retry or a rewritten historical receipt |
| Business Gate decision | deterministic files may be valid while source-derived business conditions fail | Artifact and EffectReceipt `business_gate_outcome.status/decision/gates[]/auxiliary_metrics[]/records[]`; Artifact `summary/review_guidance` use server-derived counts | show the non-green decision and formal formulas before auxiliary metrics and the 18-row ledger; derive risk counts from `records[]` and keep Artifact verification separate | business failure means file generation failed, a green Artifact means release approved, the browser computed the decision, or the current sample always has eight risks |
| TC-07 three-state legal review | source/file checks, legal business Gates and signing/human review are three simultaneous facts | Artifact and EffectReceipt `verifier_status/checks[]`, `business_gate_outcome`, `legal_review_outcome.status/decision/human_review_required/signing_evidence_count` | show the legal decision first, then three distinct status blocks; a green deterministic check must not cover a failed legal Gate or pending human review | passed file check means the document may be signed, a legal opinion was issued, signature authenticity was verified or authorization is effective |
| TC-07 per-document rule ledger | every one of six approved DOCX files has one service-derived assessment for each of 21 source rules | `legal_review_outcome.documents[].assessments[]` with `status/rule_level/source_file_ref/locator/excerpt/fact/judgment/reason/owner/remediation/exit_condition` | keep six documents collapsed by default; expand one to inspect all 21 readable records; render `unverifiable` as missing material, not a pass/fail guess; choose one/two columns from the result container width so filenames and facts remain readable | browser-extracted facts, hidden task/rubric data, a fixed risk answer, an evidence locator proving legal validity, or viewport width changing server facts |
| TC-07 dynamic source variant | one repaired document can change the service-owned counts without changing the React component or the other five documents | `legal_review_outcome.high_risk_document_count/no_trigger_document_count/signing_evidence_count`, per-document `highest_triggered_level/triggered_count/signing_evidence_status` and business Gate numerators | project 5/6 high-risk documents, 1/6 signing evidence and DOC-04 `无已触发风险` when those are the current facts; never retain canonical 6/6 or 0/6 strings | browser-side recomputation, a fixed canonical total, or one repaired document proving the other five are valid |
| TC-07 qualification boundary | a license number can be present while qualification remains unverified without an external authoritative receipt | M03 assessment `status=unverifiable`, source excerpt and reason naming missing Registry/Connector; dynamic `critical_unverifiable_count` | state that the field exists but qualification has not been checked; keep the item in the human-review count | field presence equals verified attorney status, the server called a Registry or a Connector action occurred |
| TC-07 verifier failure | source or output verification did not establish a reliable DOCX/CSV | failed Artifact `verifier_status/checks[]`, failed EffectReceipt and failure review guidance | keep both deliverables red and direct the user to a new bounded TC-07 Run after fixing the source or verifier issue | legal-risk text can override failed files, 126 rows are reliable, or the historical Run was rewritten |
| TC-06 three-state candidate review | source/file checks, role-matching advice and the final HR decision are three simultaneous facts | Artifact and EffectReceipt `verifier_status/checks[]`, `candidate_review_outcome.status/decision/human_review_required/fairness_evaluated` | show the human-decision boundary first, then three distinct status blocks; a green deterministic check must not cover missing evidence, an exception or pending HR review | passed file check means a candidate was hired/rejected, the system proved fairness, ATS state changed or a notification was sent |
| TC-06 per-condition ledger | every approved candidate has one source-derived assessment for every parsed condition in each role | `candidate_review_outcome.reviews[].assessments[]` with `status`, both source refs, both locators/excerpts, fact, judgment, reason, owner, human action and exit condition | keep ten role/candidate cards collapsed by default; expand one to inspect readable records; render `unverifiable` as missing evidence and `human_exception_required` as an HR choice | browser-extracted facts, hidden task/rubric data, a fixed pass list, missing means not_met, or an evidence locator proves resume truth |
| TC-06 dynamic source/threshold variant | one resume fact or JD threshold can change only the source-affected assessments and summary | dynamic `candidate_review_outcome` counts and affected `reviews[]`; E2E public fixture imports the service-built manifest | project the current 33/5/71/1 repaired variant when Sun AI experience is 16 months; never retain canonical 32/6/71/1 strings | browser-side recomputation, a fixed canonical total, or one repaired condition proving another role/candidate |
| TC-06 privacy and action boundary | the fixed reports omit nonessential contact/demographic values and no hiring side effect occurred | Artifact privacy check, EffectReceipt `prohibited_side_effects[]/external_action=none`, `candidate_review_outcome.fairness_evaluated=false/external_action=none` | state that the output is redacted and fairness has not been evaluated; require HR review | proof of no bias, identity verification, background check, ATS write, candidate notification or formal decision |
| TC-06 verifier failure | source, privacy or output verification did not establish reliable DOCX/CSV files | failed three Artifact `verifier_status/checks[]`, failed EffectReceipt and conditional failure guidance | keep all three deliverables red; do not show `11/11` or a reliable-advice claim; start a new bounded TC-06 Run after repair | model prose can override failed files, 110 rows are reliable, or the historical Run was rewritten |
| TC-05 three-state finance review | source/file checks, cross-period candidates and final finance disposition are three simultaneous facts | Artifact and EffectReceipt `verifier_status/checks[]`, `finance_review_outcome.status/decision/candidate_count/human_review_required` | lead with the no-accounting-action boundary, then show deterministic verification, current totals/candidates and pending finance review separately | passed files mean a candidate is confirmed, a payment/write-off/posting occurred or finance approved it |
| TC-05 positive candidate | a valid source-derived candidate is a business review item, not a verifier failure | `finance_review_outcome.candidates[]` with key, three amounts, approved source refs and Excel locators; Effect/Artifacts remain `passed` | use amber “发现 N 条候选，需财务复核”; expand the exact sources and review/exit actions | red system-failure state, automatic bad-debt conclusion, browser-computed candidate or accounting action |
| TC-05 zero candidate | the current exact-balance heuristic found no candidate, while finance review remains open | `candidate_count=0`, `status=review_required`, decision/method/limitations and `external_action=none` | say “当前启发式未发现候选，仍需财务复核” | proof that no stale receivable exists or finance work is complete |
| TC-05 verifier failure | source or generated CSV/Markdown verification did not establish reliable deliverables | failed Artifact `verifier_status/checks[]`, failed EffectReceipt and failure guidance | keep all three deliverables red and do not project reliable totals/candidates from them; start a new bounded TC-05 Run after repair | candidate text or a model conclusion can override failed files |
| TC-11 verifier failure | source or file verification did not establish a reliable report | failed Artifact `verifier_status/checks[]`, failed EffectReceipt and conditional recovery guidance | keep both deliverables red; do not show `9/9` or a reliable-report claim; start a new TC-11 Run after repair | business Gate text can override a failed Verifier, an unreliable file can be used for release, or the historical Run was rewritten |
| Artifact content sources | files whose values actually form this one Artifact | Artifact `source_file_refs` | TC-05 CSVs bind only 2026; cross-period note binds all three periods | treating EffectReceipt task context as per-file content coverage |
| Fixed-adapter task context | all source files admitted to deterministic capability execution | EffectReceipt `source_file_refs` | receipt remains separate from each Artifact | displaying three task inputs as though every output merged three periods |
| Deterministic verification | named checks passed or failed for the exact Artifact; repeated IDs may project one shared checklist onto multiple files | Artifact `validator_id/verifier_status/checks[]`, `deterministic_verification_completed.details.check_count/passed_check_count`, EffectReceipt observation | effect success requires all checks; each card keeps its checks, while Run totals deduplicate by `check_id` and conservatively combine pass state | multiplying one checklist by Artifact count, validator internals or unsupported general correctness claims |
| External effect boundary | SQL/Web/cron/real external action was not authorized or available | EffectReceipt `status=blocked_external_boundary`, `scenario_effect_bounded`, prohibited side effects | preserve instruction/scope/receipts; do not fabricate an Artifact or success | credentials, fake Connector result or scheduled job |
| Design artifact versus execution | only a document was generated; action words inside it are future process nodes, not receipts | Artifact `execution_summary/external_action=none`; EffectReceipt `prohibited_side_effects[]/external_action=none` | show prominently in the Artifact area and task close; TC-10 says no dialing, CRM write or SMS | Connector invocation, rollback or external execution |
| TC-10 four-state outbound review | deterministic source/DOCX/graph verification, source-rule coverage, final approval and actual actions are four simultaneous facts | Artifact and EffectReceipt `verifier_status/checks[]`, `outbound_flow_outcome.status/rules[]/graph_integrity/human_approval_required/external_action` | lead with “这是流程设计”; show file/graph status, N/N coverage and reachable terminals, pending approval and no dialing/CRM/SMS/deny-list/human-transfer separately | a green file means approved, a workflow node means executed, or the source proves current law |
| TC-10 rule drill-down | user can see which approved sentence produced which graph elements | `outbound_flow_outcome.rules[].rule_id/group/locator/excerpt/coverage_state/mapped_*_ids` | group by server-provided rule group; opening is read-only and spends no model budget | browser parsing the Markdown, guessed mappings, internal prompt or raw validator state |
| TC-10 unsupported/conflicting rule | the fixed adapter cannot establish complete coverage from this source revision | failed Artifact/EffectReceipt checks plus outcome `status=invalid`, `unsupported_count/conflict_count` and graph facts | keep the Artifact red, name the missing/unsupported path and require a new bounded Run after source/design repair | retaining historical `13/13`, silently dropping a rule or claiming approval |
| Task branches | validated work units now have server-owned identity, dependency and evidence state | `branches[]`, `round.branch_ids` | created after plan validation; state changes only through server verification/control | Branch ID generation and validator internals |
| Agent-selected evidence | files chosen for this round and business reason | `round.input_file_refs`, `plan.selection_reason` | after server budget/compiler validation | full metadata index, model ranking internals |
| Analyst started/returned | provider analysis stage, not completion | `analysis_started/completed` | per round | Prompt, CoT, raw response |
| Analyst receipt | not called/adopted/not adopted and elapsed time | round `analysis_receipt.*` | independent of result validation | token/provider trace |
| Citation and location validation | every Finding stays inside this round's approved refs and has at least one quote uniquely resolved in the exact bounded source | `result_validation`, `result.findings[].evidence_anchors` | before Evidence Gate; model quote candidates are removed before public projection | false semantic/numeric proof claim, raw quote candidate or model-supplied line number |
| Layout-tolerant unique location | a PDF/DOCX Preview line wrap or punctuation split no longer creates a false missing citation when there is exactly one normalized location | strict match first; server line-mapped layout normalization; resulting exact Anchor | only after zero strict candidates and at least 12 normalized characters; multiple positions stay ambiguous | fuzzy/semantic match, native PDF coordinates, entailment or server guessing |
| Instruction date-scope filter | a Finding whose verified observed dates all fall outside the user's explicit month/day window does not block the current task | `analysis_scope_filtered`, filtered count, original instruction and resolved observed Anchors | after source resolution and before result adoption | generic object/department/version filter support or an inferred date window |
| Human Gate admission | a model-proposed decision blocks the user only when the Finding has an exact contradiction Anchor | `decision_gate_suppressed` or a retained `review` plus contradiction Anchor | unsupported review becomes ordinary Finding review; true conflicts keep DecisionRequest flow | claim that all ordinary Findings are correct or need no human review |
| Verified outcome with audit pending | a deterministic file is usable even though Agent source-location audit still waits | passed EffectReceipt, all visible Artifact checks passed, latest `waiting_input` Gap; UI label “成果可用，审计待补充” | Artifact/download/checks render before Branch/Gaps; only Gaps with the same candidate refs and failure detail may be grouped in the browser | Run `completed`, deleted/merged Branches, same-file distinct failures being one audit item or audit location proving task correctness |
| Evidence gap Branch lane | the Agent has not produced an adoptable result for one or more bounded Branches; the header says how many are waiting and each row distinguishes “无需核对文件，建议重试” from “需要从 N 个原文位置中选 1 个” | `branches[]` joined by `evidence_gaps[].branch_id`; Branch input/verified/missing refs; top-level `decision_requests[]`; `EvidenceResolution.status/candidates[]` | prior rounds/branches/versions remain visible; opening is read-only; only a versioned Branch decision/resume creates work | claim that visual lanes prove parallel Workers, a candidate file is wrong or the evidence guarantees truth |
| Agent gap recovery sheet | retry-only user sees one recommended Branch action before optional explanation; ambiguous user first sees why a human is needed, what to select and what happens next | latest Round `next_step.recovery_kind`, bound Branch objective/status/input/verified refs, Gap candidates, EvidenceResolution and Planner/Analyst `called/output_used` | opening has no mutation; optional clue and audit/Preview are collapsed; waiting Run may steer then resume only that Branch; terminal Run creates a new task | raw validator text, invented row/highlight, mandatory source edit, mandatory feedback or replay of a terminal provider call |
| Retry-only Branch action | user can continue one recoverable Branch without editing files or filling an answer | waiting Branch + non-ambiguous Gap/Resolution + recovery mode; control POST `resume(branch_id)` and optional prior `steer` | primary action is unique; opening does not call a model or charge the next round; unselected Branches remain waiting | automatic retry, hidden budget spend, all-Branch resume |
| Gap/Branch review page | user can inspect where the gap occurred, what it says and which candidate/missing files are available | `round_number`, business Branch title, `evidence_gaps[]`, Branch `missing_file_refs`, Preview GET | open has no mutation; close/Escape exits immediately, then attempts a versioned `defer` only for an open structured decision; a 409/error stays visible outside the closed dialog and does not claim a receipt | raw Branch ID, claim that candidate files solve the gap, invented diff or trapping the user until a network write succeeds |
| Continue one Branch | user authorizes one more bounded round only for the selected Branch | control POST `resume` with `branch_id`, returned ControlEvent, `active_branch_id`; next `round.input_file_refs` equals that Branch's missing refs | only valid for a waiting Branch; all other waiting Branches remain unchanged | a click animation as execution proof or unrelated files silently entering the round |
| Result version | one completed round formed an independent append-only logical evidence brief | `artifact_versions[]` safe projection plus Store ArtifactVersion row | version and parent increase monotonically; content is not overwritten | source-file write, semantic correctness or mutable current-result fiction |
| Read-only Act | the Agent formed an intermediate analysis and no admitted local adapter ran | round result and `external_side_effect=none`, empty `workspace_artifacts[]` | Verify follows in the same round | tool execution or source-file mutation claim |
| Completed | server Gate created a separate TaskCommit selecting the latest verified logical brief | `status=completed`, `loop_committed`, `brief`, `commits[]`, `last_commit` | final GET after terminal event; ArtifactVersion is not mutated | source-file commit, arbitrary task correctness or external effect; deterministic Artifact success is a separate fact |
| Historical version restored | current brief pointer moved to an existing version and history remains | `artifact_version_restored`, rollback TaskCommit, `last_commit.artifact_version` | versioned/idempotent control; versions and prior Commits never decrease | file rollback, deleted work or model-call undo |
| Active-time budget | time is charged only while the Agent is running | Contract `deadline_seconds`, Snapshot `budget.elapsed_ms`, Runtime active/frozen state | defaults to 7,200 seconds, max 14,400; freezes in waiting/pause/terminal and resumes from accumulated active elapsed | wall-clock age, reset-on-resume or hard cancellation of an in-flight HTTP call |
| Budget stopped | no new provider call may start and the concrete boundary is visible | `status=stopped`, `brief.outcome=bounded`, `budget.stop_reason`, `loop_budget_stopped` | preserves completed rounds and partial brief | raw `budget_exhausted` as the only explanation, hard cancellation of an in-flight HTTP call |
| Continue after bounded stop | the terminal Run cannot resume; one unresolved Branch may seed a new Task Contract | `status=stopped`, latest `next_step.recovery_kind/candidate_branch_ids`, Branch objectives/refs, preserved `artifact_versions[]`; then a new Run POST | add optional direction and create an independent whole-workspace Run for one Branch objective | `resume` on the terminal Run, mutation of the old Run, guaranteed reuse of prior file selection or external action |
| User stopped | stop was applied at a safe point | `status=stopped`, `loop_stopped` | preserves completed rounds | rollback or deletion claim |
| Safely stopped | model/schema/plan/source/citation check failed | `status=failed`, `harness_failed`, safe errors | no result; fresh retry | raw validator/compiler/provider error |
| Next-task proposals | Agent suggests up to four follow-up tasks from the current bounded analysis; each proposal is not independently source-verified | terminal `result.follow_ups` | suggestion alone creates no server mutation | claim that work already started or that every proposal has a per-item citation |
| Finding review page | user compares one Agent finding with exact server-resolved safe-preview locations | `result.findings[].title/detail/file_refs/evidence_anchors`, matching Artifact round when available, Preview GET | select Anchor/open/close has no server mutation | semantic/numeric correctness, entailment, native PDF/DOCX coordinates |
| Finding handling sheet | user scans fact, impact and whether a human business choice is required | Finding `fact_summary`, `impact`, `review.requires_human_decision/question/why_human` | view/expand does not mutate the Run | claim that the model framing or impact is correct |
| Finding decision options | user first chooses a handling path, then may reveal and compare the Agent recommendation | Finding `review.options[]` with Branch/source/round/action impacts, `recommended_option_id`, `recommendation_reason`; browser selection/reveal state | selecting/revealing is browser draft only; recommendation is hidden before initial choice | approval, policy-optimality, source-file change or action execution |
| Record a Finding choice | user accepts, declines, defers or cancels one Finding and may add feedback | versioned/idempotent `command=decision`; top-level Snapshot `decision_requests[]`; `decision_records[]`; `decision_recorded` | close/Escape first exits and then attempts `defer`; defer remains actionable; failed defer is an explicit non-blocking error; cancel closes the packet without pretending the evidence was rejected; accept binds one owned option | file edit, external action, approval correctness, automatic follow-up or a failed defer presented as recorded |
| Start accepted Finding work | an accepted option becomes a new independent task | new Run POST containing selected `next_instruction`, decision label and feedback after the receipt succeeds | new idempotency key; prior Run/result/DecisionRecord stays immutable | mutation of the old Run or continuation of an in-flight provider call |
| Evidence location state | user sees whether a quote has one, many, no current match, a changed source or a rejected candidate | `next_step.evidence_resolutions[]`: `exact/ambiguous/unavailable/stale/rejected`, source revision and candidate IDs | compare real positions; accept, decline, defer, cancel, supplement a source hint or retry only the bound Branch | semantic entailment, invented coordinates, raw digest or source hash |
| Partial analysis adopted | only Findings with server-resolved Anchors become public; unresolved records stay actionable | `analysis_partial_adopted`, `partial_artifact_saved`, Artifact findings, EvidenceResolution and Branch status | review retained Findings; open unresolved candidates separately | content or correctness of omitted Findings |
| Analysis recovery required | two bounded attempts yielded no adoptable Finding/structure but legal scope and prior work remain | `analysis_recovery_required`, Round `next_step.recovery_kind`, candidate Branches, `status=waiting_input` | add steer text and resume one waiting Branch | result acceptance, model not called or file modified |
| Candidate disambiguation | one quote matches multiple real positions and requires one human source-location choice | `evidence_disambiguation_required`, `EvidenceResolution(status=ambiguous).candidates[]`, open DecisionRequest | compare source positions; no default candidate; accept stays disabled until one candidate is selected, then versioned/idempotent decision resumes only the bound Branch | server or Agent chose for the user, random location, other Branches reran |
| Verified result, table position pending | generated files passed deterministic checks while one Agent explanation lacks a unique row/cell | passed `workspace_artifacts[].checks`, corresponding `effect_receipts[]`, `recovery_kind=source_location`, grouped Branch/Gap projection | show files first; “查看已生成成果” is read-only; “查找原表格位置” resumes one bound Branch; technical facts are collapsed | file missing, date/amount failure, Agent explanation proved correct, Run completed, Artifact overwritten |
| Unverified result, table position pending | a `source_location` Gap exists but no current all-passed Artifact set establishes a usable result | Run/Artifact/EffectReceipt plus Branch/Gap facts | say the result is not yet verified; handle only the bound Branch | borrow the verified-result claim or hide an Artifact failure |
| Terminal source-location gap | an old Run ended with the Gap preserved | terminal `status`, preserved Branch/Gap, Snapshot/version | create a new task from the smallest scope; preserve the old Run | resume a terminal Run or claim in-place continuation |
| Resume recovery Branch | selected evidence decision is consumed at a safe checkpoint | `DecisionRequest`, `decision_recorded`, `branch_resumed_from_checkpoint`; optional `control_steer_recorded` for user feedback | continue only the bound waiting Branch; reconnect from Snapshot/SSE; v1 remains while resumed work appends v2 | lost ArtifactVersion, replay of completed Branches or external action |
| Legacy terminal analysis failure | an older Run stopped before the recoverable protocol existed | `status=failed`, safe validation error, preserved instruction/Plan/Branch/call facts | create a new smallest-scope Run | interrupted call resumed or failed output adopted |
| Proposal context review | user sees the result context before deciding whether to start the suggestion | one `result.follow_ups[]` string + union of current Finding refs | explicitly labeled not independently source-verified; no mutation | direct per-proposal citation or accepted-proposal state |
| Confirm proposal | user turns one suggestion into an independent new Loop | new POST `/v1/harness/runs` with exact proposal text | new idempotency key; previous Run/result preserved | nonexistent proposal-accept state |

## 4. Human control

| UI action/state | User-visible meaning | Authority | Transition/recovery/idempotency | Hidden |
| --- | --- | --- | --- | --- |
| Pause | request a stop at the next safe point | control POST `pause`, returned Snapshot/ControlEvent | expected version + idempotency; freezes active elapsed at the safe point and does not cancel an in-flight model call | local instant-pause fiction |
| Resume | continue a paused Run | control POST `resume` | only from server-paused state; restarts active elapsed without charging paused time | browser-only state change or deadline reset |
| Steer next round | record a direction for the next round | control POST `steer`, `pending_steer`/ControlEvent | does not rewrite an already accepted round | claim that current result changed immediately |
| Stop and keep | terminate at a safe point and preserve work | control POST `stop`, terminal Snapshot | idempotent replay returns original command result | deletion/rollback claim |
| Restore result version | select a historical logical brief without overwriting history | control POST `rollback` with `artifact_version`; returned Snapshot/ControlEvent | completed committed Run only; expected version + idempotency; appends a TaskCommit | original file rollback or deletion of newer ArtifactVersion |
| Version conflict | another fact is newer than this control | HTTP 409 + current Snapshot reconciliation | refresh, review, submit a new command | field-level merge not implemented |

## 5. Preview and validation limits

| Fact | Current guarantee | Not guaranteed |
| --- | --- | --- |
| workspace inventory | 15 folders, 96 input refs from pinned manifest | unpublished FORTE tasks or live enterprise drive |
| XLSX/CSV | first visible sheet/CSV, <=30 columns, <=120 rows | arbitrary workbook features or formula truth |
| DOCX/PDF/TXT | bounded extracted/read text, <=30,000 chars | OCR completeness, layout fidelity or semantic accuracy |
| stable ref | deterministic for pinned public input path | production document identity |
| plan compilation | server-owned effects/gates plus graph/source checks and one bounded repair | plan quality or tool execution |
| fixed local office effect | twelve named FORTE capabilities create isolated CSV/Markdown/DOCX/ZIP outputs with deterministic checks | arbitrary instruction execution, a general Tool Gateway, source mutation or external action |
| external-boundary receipt | TC-03/08/09 explicitly record that SQL/Web/cron effects did not run | successful task effect, Connector availability or scheduling |
| result validation | citation membership plus at least one uniquely resolved safe-preview Anchor per new Finding | entailment, exhaustive matching, arithmetic, native page coordinates or cell semantics |
| structured review | required fields/options and recommendation membership pass schema/runtime checks | recommendation quality, correct risk framing or human acceptance |
| Evidence Gate | decides continue/stop from explicit gaps and remaining bounds | semantic truth or human acceptance |
| completed | reviewable logical brief plus an independent TaskCommit pointer exists | task correctness, deterministic Artifact success, Connector or external process completion |

## 6. Transport and lifecycle

- Snapshot version and event sequence never decrease in the browser.
- A terminal event requires final GET; a nonterminal disconnect uses GET plus
  `after=N`.
- “trajectory live” requires an open current EventSource; “service available”
  only requires successful HTTP.
- Missing/wrong-owner Run returns the same 404.
- `X-User-Id` is unsigned. With `DATABASE_DSN`, Snapshot, command receipts,
  ArtifactVersions and TaskCommits are PostgreSQL-backed; without it they remain
  one-process memory.
- Run Workspace Artifact metadata/effect receipts live in the Snapshot; same-host
  Artifact bytes live in a separate isolated store and are rechecked on download.
  This is not a transactional database/filesystem commit or multi-host durability.
- Local `start-demo.ps1` chooses Docker first, then a `DATABASE_DSN` explicitly
  present in the launching PowerShell process, otherwise memory. In the final
  case it overrides a stale `.env` database value. UI/service availability and
  restart-recovery claims must use `/v1/health.checkpoint` and `task_store`, not
  the launcher message or the mere presence of `.env`.
- `checkpoint_recovered` proves a persisted Snapshot was restored and paused.
  It does not prove an interrupted model call was cancelled or replayed.
- Plan operation labels declare intent only. Twelve fixed server-owned local
  adapters can create verified isolated office/code files; the current Runtime
  still has no general Tool Gateway and never modifies FORTE source files. Logical
  evidence briefs/TaskCommits, real Run Workspace files and external-action
  receipts remain three different facts.
- Pause/stop apply between provider calls; deadline prevents a new call but does
  not hard-cancel an in-flight request.
- Browser refresh restores a known Run id; `GET /runs` can discover the latest
  nonterminal Owner Run. There is not yet a full history chooser.

## 7. Evidence and applicability

Current contract: [`DR-0036`](../decisions/DR-0036-outcome-first-and-layout-tolerant-evidence.md),
[`SCENARIO-022`](../scenarios/SCENARIO-022-verified-outcome-and-audit-location.md),
[`DR-0035`](../decisions/DR-0035-scenario-effect-gate-and-run-workspace-artifacts.md),
[`SCENARIO-021`](../scenarios/SCENARIO-021-verifiable-office-artifact-effect.md),
[`DR-0030`](../decisions/DR-0030-actionable-review-and-recoverable-analysis.md),
[`SCENARIO-016`](../scenarios/SCENARIO-016-actionable-finding-and-recoverable-analysis.md),
[`DR-0026`](../decisions/DR-0026-selective-branch-and-immutable-artifact-history.md),
[`DR-0025`](../decisions/DR-0025-durable-evidence-gate-and-artifact-evolution.md),
[`DR-0024`](../decisions/DR-0024-autonomous-whole-workspace-research.md),
[`DR-0023`](../decisions/DR-0023-agent-control-loop.md),
[`SCENARIO-012`](../scenarios/SCENARIO-012-selective-branch-and-artifact-restore.md),
[`SCENARIO-010`](../scenarios/SCENARIO-010-autonomous-whole-workspace-research.md),
[`SCENARIO-009`](../scenarios/SCENARIO-009-agent-control-loop.md),
[workspace interaction/source record](../research/WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825.md)
and [current TC-01 outcome/evidence localization Evidence](../evidence/DR-0036-TC01-OUTCOME-EVIDENCE-LOCALIZATION-EVIDENCE-20260828.md).
TC-05 Artifact meaning and review typography additionally follow
[`DR-0037`](../decisions/DR-0037-tc05-artifact-semantics-and-review-readability.md),
[`SCENARIO-023`](../scenarios/SCENARIO-023-understand-finance-artifacts-and-review-evidence.md)
and [current TC-05 Evidence](../evidence/DR-0037-TC05-ARTIFACT-SEMANTICS-AND-REVIEW-READABILITY-EVIDENCE-20260828.md).
Source-derived candidate and finance-disposition projection additionally follow
[`DR-0046`](../decisions/DR-0046-tc05-source-derived-finance-candidate-review.md),
[`SCENARIO-032`](../scenarios/SCENARIO-032-review-three-period-finance-candidates-from-source.md)
and [current DR-0046 Evidence](../evidence/DR-0046-TC05-SOURCE-DERIVED-FINANCE-REVIEW-EVIDENCE-20260829.md),
plus [`DR-0047`](../decisions/DR-0047-tc10-source-derived-outbound-flow.md),
[`SCENARIO-033`](../scenarios/SCENARIO-033-review-source-derived-outbound-flow.md)
and [current DR-0047 Evidence](../evidence/DR-0047-TC10-SOURCE-DERIVED-OUTBOUND-FLOW-EVIDENCE-20260829.md).
Source-location wording and recovery additionally follow
[`DR-0038`](../decisions/DR-0038-user-language-source-location-recovery.md),
[`SCENARIO-024`](../scenarios/SCENARIO-024-understand-and-recover-missing-table-location.md)
and [current DR-0038 Evidence](../evidence/DR-0038-USER-LANGUAGE-SOURCE-LOCATION-RECOVERY-EVIDENCE-20260828.md).

Automated checks are engineering proxies, not user research. User
comprehension, calibrated trust and task value remain `Draft`.
