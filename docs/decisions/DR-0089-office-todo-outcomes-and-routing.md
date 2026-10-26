# DR-0089: Everyday Todo Outcomes And Routing

Date: 2026-10-24. Status: Limited Verified. Implementation: uncommitted working tree, HEAD fa974ae; no new PR.

## 场景与来源

[User request](../sources/USER-FEEDBACK-20261024-demo2-office-todos.md), [SCENARIO-076](../scenarios/SCENARIO-076-understand-office-todo-outcomes.md), [Evidence](../evidence/DR-0089-OFFICE-TODOS-20261024.md).
The stakeholder wants simple office tasks with understandable routing and outputs. Existing DR-0086 automatic_readonly authority remains unchanged.

## 前台交互影响

- Two selectable groups offer six editable Excel, Word and onboarding PDF tasks. Opening/selecting/editing examples makes no POST.
- On submission, full instructions collapse. Each row shows business title, routing and actual adopted analysis. Preview prioritizes one finding per distinct Branch, up to three, instead of letting one worker occupy all preview slots. Full findings remain in the task.
- Missing requirements, pending business/source decisions and unfinished Branches cannot become a green completion merely because the Loop completed. Empty usable output is labelled as such.
- Admission, in-flight work packages, model call receipts and adopted output have distinct wording. No numeric difficulty/confidence score is invented.
- The collaboration graph shows one actual adopted output per work package; current attempt must match the Contribution. Old attempt output cannot be presented as current success.
- Original instructions, routing reasons and counts disclose on demand. Errors and unfinished-item titles stay visible. Task/Source/Result views and full capability page remain.
- TodoBatch stays mounted while browsing details or switching spaces. Return to this batch is GET-only; explicit New Task clears the local batch and opens a new composer, without stopping accepted runs. Refresh still loses the local batch; server task history remains subject to the existing recent20 and state-store boundaries.
- Unknown starts keep existing locked payload, navigation and idempotency retry. No new manual approval is introduced for Demo2.

## 后端事实映射

No server, contract, permission, model prompt or scheduler change.

| Display | Authority | Forbidden inference |
| --- | --- | --- |
| Proposed single/multi/sequential route | topology_admission.mode/reasons | Objective difficulty or optimal worker count |
| In progress / received / adopted | work_units.state; worker_runs.model_called/output_used | Admission or node count proves execution |
| Analysis summary | DR-0088 responsibility projection of Result/retained Artifact, Branch, anchor and decisions | Source location proves correctness or approval |
| Current work-package output | matching latest_contribution_id + branch_id + attempt + gate_status | Old adopted attempt is current success |
| Retained batch navigation | mounted browser component and accepted run_id | Durable server batch or cross-refresh recovery |

Counts of Worker receipts are attempts, not total distinct Agents. A single-controller path may call Planner and Analyst; it does not mean one API call. The same-directory fixed_workflow policy is an existing conservative heuristic, not evidence that parallelism could never help.

## 验证与边界

See Evidence for all12 live Run IDs,26 calls, actual overlap, screenshots and regression commands. All readonly analysis tasks completed in this bounded sample; there was no human dispatch confirmation. No output DOCX/XLSX, email, installation, permission change, recruitment decision or original-file mutation occurred. Browser tests are controlled checks, not target-user research. No throughput/speedup or general success-rate claim.

Rejected: preset names forcing topology, fake live worker animations, hiding failures, rewriting output to match the intended story, and making a separate Demo2 product.
