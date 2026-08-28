# Office Agent V0.2 API

Base URL: `http://localhost:8010`.

## 1. Public surface

OpenAPI exposes eight paths and nine operations:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/health` | process health and configured model/storage labels |
| GET | `/v1/harness/workspace` | whole public office folder projection |
| GET | `/v1/harness/workspace/files/{file_ref}` | bounded, integrity-checked file preview |
| POST | `/v1/harness/runs` | start an idempotent bounded read-only Agent Control Loop |
| GET | `/v1/harness/runs?limit=10` | list recent Owner-scoped Runs for recovery |
| GET | `/v1/harness/runs/{run_id}` | Owner-scoped public Snapshot |
| GET | `/v1/harness/runs/{run_id}/artifacts/{artifact_id}` | Owner-scoped download of one verified Run Workspace file |
| POST | `/v1/harness/runs/{run_id}/controls` | versioned, idempotent pause/resume/steer/stop/rollback |
| GET | `/v1/harness/runs/{run_id}/events?after=N` | ordered named SSE after a sequence |

The former Scenario list/detail/preview routes and legacy
workspace/thread/task/Demo prefixes are not mounted.

## 2. Owner and persistence

Run endpoints use `X-User-Id`; omission uses `demo_user`. This unsigned header
is a demonstration Owner placeholder, not production authentication. Missing
and wrong-owner Runs both return 404 before the SSE response is created.

There are nine operations over eight OpenAPI paths because `GET` and `POST`
share `/runs`. With `DATABASE_DSN`, accepted Run snapshots, start/control
idempotency receipts, ArtifactVersions and TaskCommits are stored in
PostgreSQL; the latter two are independent append-only rows. Verified Run
Workspace file metadata remains in the Snapshot, while the bytes live in the
isolated server Artifact store and are rechecked on download. On startup, an
interrupted nonterminal Run is rolled back to completed rounds, receives
`checkpoint_recovered` and pauses; an in-flight provider request is never
automatically replayed. In-flight HTTP requests, asyncio tasks and conditions
remain process-local. Without `DATABASE_DSN`, the state store is memory and all
Run state disappears on restart.

## 3. Whole workspace

```http
GET /v1/harness/workspace
```

Representative response:

```json
{
  "workspace_id": "forte-public-office",
  "title": "FORTE 公开办公资料库",
  "dataset_version": "345c1ec1487139db9dd319787fa9405ba85d1869",
  "license": "MIT",
  "folder_count": 15,
  "file_count": 96,
  "previewable_file_count": 96,
  "folders": [
    {
      "folder_id": "forte-folder-...",
      "display_label": "财务",
      "availability": "local_input_bundle",
      "file_count": 3,
      "files": [
        {
          "file_ref": "forte-a0bccc1df48cc6a1",
          "display_label": "2025 年上半年往来明细",
          "display_path": "财务/2025 年上半年往来明细.xlsx",
          "extension": ".xlsx",
          "size": 12345,
          "preview_kind": "table",
          "preview_available": true
        }
      ]
    }
  ]
}
```

This projection comes from `public-suite-manifest.json`. It omits benchmark
task instructions, rubric, solution, grading material, source path and digest.
Two task-only external-dependency folders may have zero local input files and
cannot be used to fabricate local data.

`display_path` is a safe business path and may contain nested segments, for
example `算法研发/search_agent_workflow/main.py`. The browser may project these
segments as a folder tree. Expand, search and type-filter state is client-owned;
it does not change the server workspace projection or a Run's whole-workspace
scope. `display_path` is not an operating-system absolute path.

## 4. File preview

```http
GET /v1/harness/workspace/files/forte-a0bccc1df48cc6a1
```

All preview responses include business labels, size, bounded content and:

```json
{
  "security": {
    "integrity_verified": true,
    "read_only": true,
    "active_content_executed": false,
    "external_resources_loaded": false,
    "notes": ["..."]
  }
}
```

Preview kinds:

| Kind | Formats | Bounded output |
| --- | --- | --- |
| `table` | XLSX, CSV | at most 30 columns and 120 rows |
| `document` | DOCX | at most 30,000 extracted characters |
| `pdf` | PDF text layer | page count plus at most 30,000 characters |
| `text` | TXT, Markdown, JSON, logs and code | at most 30,000 characters |
| `unavailable` | encrypted/unsupported/unsafe | safe reason, no guessed content |

Before reading, the Catalog validates relative allowlisted path, declared size,
SHA-256, non-symlink file and archive expansion bounds. It rejects DOCM/macro
content, does not run active content and does not fetch external resources.
Unknown ref is 404; source integrity failure is controlled 503.

## 5. Start a Run

```http
POST /v1/harness/runs
X-User-Id: demo_user
Content-Type: application/json
```

```json
{
  "workspace_id": "forte-public-office",
  "idempotency_key": "harness:client-generated-key",
  "expected_version": 1,
  "instruction": "研究整个资料库，找出值得继续推动的工作，并逐条引用依据。",
  "loop": {
    "max_rounds": 12,
    "max_files_per_round": 16,
    "max_model_calls": 30,
    "deadline_seconds": 7200
  }
}
```

`instruction` is required and contains 3-2,000 characters. The request does not
accept `selected_file_refs`: the server freezes the complete allowlisted input
index and the Planner autonomously selects a bounded evidence set for each
round. Sending a client-owned file scope is rejected as an unknown field.

`loop` is optional and defaults to the values above. Bounds are 1-24 rounds,
1-24 files per round, 2-60 model calls and 20-14400 seconds. The server freezes
these values plus `scope_mode=whole_workspace` and all stable input refs into
`AgentControlLoopContract`; the browser cannot change the scope or budget while
a Run is active. `deadline_seconds` is an active execution deadline: elapsed
time is frozen during `waiting_input`, explicit pause and terminal states, then
continues from the accumulated active elapsed on a legal resume. It does not
hard-cancel an in-flight provider HTTP request.

The response is `202 Accepted` with `{"run": snapshot, "replayed": false}`.
Reusing the same Owner/key/request returns the original start result with
`replayed=true`. Reusing that key for different content returns 409.

`GET /v1/harness/runs?limit=10` returns `{"runs": [...]}` ordered by the
latest server update. It is Owner-scoped and exists so a browser without local
session state can discover a recoverable nonterminal Run. The client must still
GET the selected Run and reconnect SSE from its authoritative sequence.

## 6. Public Snapshot

Important fields:

```json
{
  "run_id": "harness:...",
  "workspace_id": "forte-public-office",
  "status": "completed",
  "version": 22,
  "last_event_sequence": 21,
  "instruction": "...",
  "instruction_source": "user",
  "source_documents": [
    {"file_ref": "forte-...", "display_label": "...", "display_group": "..."}
  ],
  "contract": {
    "contract_version": "agent-control-loop.v1",
    "goal": "...",
    "scope_mode": "whole_workspace",
    "allowed_file_refs": ["forte-...", "... all 96 stable refs ..."],
    "max_rounds": 12,
    "max_files_per_round": 16,
    "max_model_calls": 30,
    "deadline_seconds": 7200,
    "external_action": "none"
  },
  "budget": {
    "rounds_used": 2,
    "files_verified": 8,
    "model_calls_used": 5,
    "elapsed_ms": 71461,
    "stop_reason": null
  },
  "rounds": [],
  "branches": [
    {
      "branch_id": "branch-...",
      "unit_id": "verify-revenue",
      "round_number": 1,
      "parent_branch_id": null,
      "title": "核对收入证据",
      "depends_on": [],
      "input_file_refs": ["forte-..."],
      "verified_file_refs": ["forte-..."],
      "missing_file_refs": [],
      "status": "completed",
      "requires_human_gate": false
    }
  ],
  "active_branch_id": null,
  "control_state": "running",
  "control_events": [],
  "decision_requests": [],
  "decision_records": [],
  "workspace_artifacts": [
    {
      "artifact_id": "workspace-artifact-0123456789ab",
      "capability_id": "office-finance-reconciliation",
      "scenario_id": "TC-05",
      "title": "跨期往来款核对结果",
      "file_name": "跨期往来款核对结果.csv",
      "media_type": "text/csv",
      "size": 4821,
      "version": 1,
      "round_number": 1,
      "source_file_refs": ["forte-..."],
      "validator_id": "validator-finance-reconciliation-v1",
      "verifier_status": "passed",
      "checks": [
        {"check_id": "check-row-formula", "label": "逐行公式复算", "passed": true, "detail": "全部通过"}
      ],
      "download_path": "/v1/harness/runs/harness:.../artifacts/workspace-artifact-0123456789ab",
      "original_inputs_modified": false,
      "review_required": true,
      "external_action": "none"
    }
  ],
  "effect_receipts": [
    {
      "receipt_id": "effect-receipt-0123456789ab",
      "capability_id": "office-finance-reconciliation",
      "scenario_id": "TC-05",
      "status": "passed",
      "state": "冻结三个只读工作簿",
      "action": "在隔离 Run Workspace 生成核对表并复算",
      "observation": "三个 Artifact 的确定性检查通过",
      "cost": "本地确定性处理；没有外部调用",
      "result": "工件可下载，原始输入未修改",
      "artifact_ids": ["workspace-artifact-0123456789ab"],
      "external_action": "none"
    }
  ],
  "artifact_versions": [
    {
      "artifact_id": "artifact-...",
      "version": 1,
      "status": "verified",
      "kind": "evidence_brief",
      "round_number": 1,
      "summary": "...",
      "findings": [],
      "follow_ups": [],
      "evidence_gaps": [],
      "source_file_refs": ["forte-..."],
      "review_required": true,
      "external_action": "none"
    }
  ],
  "commits": [
    {
      "commit_id": "commit-...",
      "artifact_id": "artifact-...",
      "artifact_version": 1,
      "operation": "commit",
      "parent_commit_id": null,
      "external_action": "none"
    }
  ],
  "last_commit": {
    "commit_id": "commit-...",
    "artifact_version": 1,
    "operation": "commit",
    "external_action": "none"
  },
  "brief": {
    "outcome": "completed",
    "rounds_completed": 2,
    "external_action": "none"
  },
  "plan": {
    "summary": "...",
    "selection_reason": "为什么本轮选择这些文件",
    "units": []
  },
  "model_receipt": {
    "called": true,
    "model": "deepseek-v4-pro",
    "elapsed_ms": 14685,
    "output_used": true
  },
  "analysis_receipt": {
    "called": true,
    "model": "deepseek-v4-pro",
    "elapsed_ms": 18041,
    "output_used": true
  },
  "result": {
    "summary": "...",
    "findings": [
      {
        "title": "...",
        "detail": "...",
        "fact_summary": "发生了什么",
        "impact": "不处理会影响什么",
        "file_refs": ["forte-..."],
        "evidence_anchors": [
          {
            "file_ref": "forte-...",
            "role": "observed",
            "label": "实际运行记录",
            "locator_kind": "text_lines",
            "start": 42,
            "end": 45,
            "excerpt": "...server-copied bounded source text..."
          }
        ],
        "review": {
          "requires_human_decision": true,
          "question": "需要按哪一种口径继续？",
          "why_human": "两个业务来源冲突，服务端不能替用户选择权威口径。",
          "options": [
            {
              "option_id": "A",
              "label": "先核对版本",
              "meaning": "先确认测试使用的代码版本。",
              "agent_next_step": "只读核对版本与时间记录。",
              "next_instruction": "核对测试记录与发布记录是否属于同一代码版本。",
              "affected_branch_ids": ["branch-0123456789ab"],
              "required_file_refs": ["forte-0123456789abcdef"],
              "estimated_additional_rounds": 1,
              "external_action": "none"
            },
            {
              "option_id": "B",
              "label": "先形成修复建议",
              "meaning": "按现有设计基线形成只读修改建议。",
              "agent_next_step": "输出待修改位置和验证清单。",
              "next_instruction": "基于当前设计基线形成只读修复建议和验证清单。",
              "affected_branch_ids": ["branch-0123456789ab"],
              "required_file_refs": ["forte-0123456789abcdef"],
              "estimated_additional_rounds": 1,
              "external_action": "none"
            }
          ],
          "recommended_option_id": "A",
          "recommendation_reason": "先消除版本差异可避免错误归因。",
          "after_confirmation": "创建新的只读 Control Loop 继续核对。"
        }
      }
    ],
    "follow_ups": ["由用户确认后可作为新 Run 启动的下一步任务"],
    "review_required": true
  },
  "validation_errors": []
}
```

`source_documents` and `contract.allowed_file_refs` are the full safe workspace
index. They are not the files read by the Analyst. The authoritative per-round
evidence scope is `rounds[].input_file_refs`, and the public reason is
`rounds[].plan.selection_reason`. The server compiler caps the union of those
refs at `max_files_per_round` before any file content reaches the Analyst.

`branches[]` is the server-owned projection of validated plan units. Branch
identity, dependency, verified/missing refs and status are not model-owned UI
interpretations. `rounds[].branch_ids` connects a round to its Branch records;
`active_branch_id` identifies the branch selected for a resumed evidence round.

`result.follow_ups` contains at most four model-proposed next tasks. It is not a
server-side acceptance record. The current browser starts a separate Run only
after the user confirms one proposal. There is no per-follow-up citation field
in the current contract. A review UI may show the current result's Finding refs
as explicitly labeled context, but must not present them as direct evidence for
an individual proposal.

The issue-review page reuses the Preview endpoint. Finding review uses its own
`file_refs` and server-resolved `evidence_anchors`; Gap/Branch review uses
`candidate_file_refs` or `missing_file_refs`. Opening or selecting an Anchor is
client-only. Closing a pending human-decision sheet is different: the browser
records `command=decision`, `decision_action=defer` before closing, so omission
is not confused with rejection and the versioned receipt survives reconnect.

The Analyst supplies verbatim quote candidates, not trusted line numbers. The
server resolves each accepted candidate against the exact bounded table/text
projection used in that round, requires a unique row or text match, removes the
raw candidate and publishes only `evidence_anchors`. `text_lines` refers to
safe extracted preview lines; for PDF/DOCX it is not an original page or native
paragraph coordinate. `table_rows` is row-level, not cell-level semantic proof.
Each newly adopted Finding needs at least one resolved Anchor. Anchor membership
and location do not prove entailment, arithmetic, completeness or correctness.
Text resolution first uses strict whitespace-normalized matching. If that yields
no candidate and the normalized quote has at least 12 characters, the server may
ignore safe-Preview layout whitespace and punctuation while retaining its line
map. Exactly one position becomes `exact`; repeated positions remain `ambiguous`.
This is not fuzzy or semantic matching.
If the first Analyst candidate cannot be uniquely located, the Runtime may spend
one additional Analyst call inside the same Run budget. It emits
`analysis_validation_rejected` before retrying and never publishes rejected
content. Each quote receives a server-owned EvidenceResolution: `exact` means one
bounded Preview location, `ambiguous` means multiple candidates and `unavailable`
means none. A source revision change emits `stale`; a candidate that fails the
server's current-source recomputation emits `rejected`. A second attempt may retain only uniquely anchored
Findings and emit `analysis_partial_adopted` plus `partial_artifact_saved`. The
unresolved Finding and candidates remain in `next_step.evidence_resolutions`; only
their affected Branches wait. If no Finding can be adopted, the round is still
preserved with `recovery_kind=source_location`. Repeated schema failures use
`analysis_output`. Scope or integrity violations still fail closed.

After resolution, the Runtime may omit a Finding when every verified `observed`
month/day lies outside an explicit Chinese date window in the original instruction;
it emits `analysis_scope_filtered`. A model-proposed human review without an exact
`contradiction` Anchor is removed with `decision_gate_suppressed`. These rules do
not authorize an out-of-scope ref and do not implement a general predicate compiler.

`review.options[]` is model-proposed handling context, not a server decision or
approval. Every option projects `affected_branch_ids`, `required_file_refs`,
`estimated_additional_rounds` and `external_action=none`. The browser first posts
a versioned and idempotent `decision` command bound to the Finding/Resolution and
Branch. `accept`, `decline` and `defer` become `decision_records[]`; they do not
alter source files or perform an external action. Accepting a business option then
combines its `next_instruction`, label and optional feedback in a new independent
Run. Accepting an ambiguous source candidate instead records the candidate, steers
the current Run and resumes only the affected waiting Branch.

`recovery_kind` does not imply that every Run is resumable. When the same
recoverable gap reaches `status=stopped` with `next_step.decision=budget_exhausted`,
the old Run is terminal and must not receive `resume` or `steer`. The client may
use one ID from `candidate_branch_ids`, the matching Branch objective and optional
user direction to POST a new whole-workspace Run. Prior Branches, receipts and
ArtifactVersions remain on the old Snapshot; the new Planner autonomously selects
and validates evidence again rather than inheriting the old file set as authority.

For a nonterminal Gap, the client derives its recovery sheet only from the latest
Snapshot: `next_step.recovery_kind`, the bound Branch objective/status and refs,
Gap candidates, plus Planner/Analyst `called/output_used` receipts. A missing
Anchor means the server has no unique source position; it is not permission for
the browser to invent a row or ask the user to edit the candidate file. Feedback
is optional. A waiting Branch may be resumed directly; if feedback is supplied,
the client records a versioned steer before the versioned Branch resume.

The API does not add a separate “retry modal” state. The browser derives the
interaction from the same Snapshot facts: non-ambiguous recoverable Branches show
one recommended resume and keep optional feedback/audit detail collapsed;
`EvidenceResolution(status=ambiguous)` shows the candidate count and requires an
explicit selection before `decision_action=accept` can be submitted. No request is
sent and no next-round budget is consumed merely by opening either surface.

Current statuses are `queued`, `indexing`, `planning`, `validating`,
`analyzing`, `verifying`, `waiting_input`, `paused`, `completed`, `stopped`
and `failed`;
compatibility `ready_to_execute` is retained for runtimes built without an
Analyst.

`decision_records[]` is append-only Snapshot state. Each record carries a stable
Decision ID, `action`, Finding/Resolution/Branch binding, selected option or
candidate when applicable, optional user feedback, accepted task version and
`external_action=none`. It is the reconciliation fact after reconnect; a toast or
button animation is not a decision receipt.

Open `decision_requests[]` are authoritative at the Run Snapshot top level.
Any round-level copy is a compatibility projection and may be absent. Clients
must bind decisions with the packet's Finding, Resolution, Branch, public source
revision and current expected version. Closing a UI may happen before a best-effort
`defer`; a failed control response does not change packet state and must not be
presented as a DecisionRecord.

The current PostgreSQL adapter persists these records only as part of the Run
Snapshot JSONB. Runtime validation enforces current source revision and candidate
recomputation, but the database has no independent DecisionRecord/EvidenceResolution
table, source-revision foreign-key constraint or multi-instance CAS. The DR-0032
restart gate verifies sequential Runtime recovery of one pending decision; it is
not a claim that an interrupted provider call or concurrent writer is durable.

`workspace_artifacts[]` and `effect_receipts[]` are separate from the model's
logical evidence brief. An effect receipt records
`state -> action -> observation -> cost -> result`; an Artifact record names the
server-owned validator and its checks. Only `verifier_status=passed`, verified
bytes and a successful Owner-scoped download prove that the fixed local adapter
created a real Run Workspace file. They do not prove arbitrary instructions are
implemented, and they never authorize a source-file or external-system mutation.

`artifact_versions` and `commits` are safe Snapshot projections of independent
append-only Store records. ArtifactVersion contains the complete logical
read-only brief for one completed round; it remains `draft` or `verified` and is
not mutated to represent submission. TaskCommit separately selects the current
version. `operation=rollback` means the current brief pointer was restored to a
historical version by creating another Commit. None of these facts means an
original office file or external system changed.

`completed` means the Evidence Gate found no unresolved citation gap in the
selected evidence and the read-only results passed schema, selected-citation,
evidence-location and boundary checks. It does not mean the answer is
semantically correct or a plan-declared tool executed. Conversely, a verified
Run Workspace Artifact can survive a later Analyst rejection or waiting state;
the UI must show model adoption, Loop state and deterministic effect as three
different facts.

## 7. Download a verified Run Workspace Artifact

```http
GET /v1/harness/runs/{run_id}/artifacts/{artifact_id}
X-User-Id: demo_user
```

The route accepts only an Artifact ID already bound to the same Owner and Run.
Before returning bytes it verifies the stored record, file size and private
digest. Success uses the recorded media type, `Content-Disposition: attachment`,
`X-Content-Type-Options: nosniff` and `Cache-Control: private, no-store`.
Unknown Owner/Run/Artifact returns 404; missing or drifted bytes fail closed with
503. The public Snapshot and DOM never expose the private digest or storage path.

## 8. Control a Run

```http
POST /v1/harness/runs/{run_id}/controls
X-User-Id: demo_user
Content-Type: application/json

{
  "command": "steer",
  "instruction": "下一轮优先核对付款条件",
  "expected_version": 12,
  "idempotency_key": "control-client-generated-key"
}
```

Commands are `pause`, `resume`, `steer`, `stop`, `rollback` and `decision`.
`steer` requires an instruction and applies only to the next round. Pause and
stop are accepted immediately but applied only at a safe point between model
calls. A stale version, illegal transition or same key with different content
returns 409. An identical replay returns the first control result with
`replayed=true`.

Human decisions use the same version/idempotency rules:

```json
{
  "command": "decision",
  "decision_action": "accept",
  "decision_request_id": "decision-request-0123456789ab",
  "finding_id": "finding-0123456789ab",
  "resolution_id": "resolution-0123456789ab",
  "branch_id": "branch-0123456789ab",
  "selected_candidate_id": "candidate-0123456789ab",
  "source_revision": "rev-0123456789abcdef",
  "feedback": "只核对这个分支，不重跑已完成分支。",
  "expected_version": 13,
  "idempotency_key": "decision-client-generated-key"
}
```

An accepted Finding decision must select one of that Finding's A/B/C options; an
accepted EvidenceResolution must reference its current server DecisionRequest,
select one owned candidate ID and carry the public source-revision token. Decline,
defer or cancel cannot carry a selected option/candidate. The server validates all
Finding/Resolution/Branch bindings and appends `decision_records[]` without
changing Branch, ArtifactVersion or external state.

When the Evidence Gate emits `next_step.decision=waiting_input`, the Snapshot
already has `control_state=paused`. `resume` must carry one waiting
`branch_id`; it authorizes only that branch's next evidence round. The round is
restricted to that Branch's `missing_file_refs`, its validated plan must cover
all of them, and other waiting branches remain unchanged. A missing, unknown or
non-waiting Branch returns 409. For backward compatibility, a resume without a
Branch selects only the first waiting branch; it never advances all branches.

`rollback` applies only to a terminal committed Run and requires
`artifact_version`. The server loads and verifies that independent
ArtifactVersion, rejects restoring the already-current version, then appends a
new `operation=rollback` TaskCommit and returns the restored brief. It does not
delete versions, undo a model call or modify workspace files. A Run retains at
most 20 TaskCommit records; reaching that bound fails closed and requires a new
independent Run instead of truncating history.

## 9. Plan policy and result validation

The provider returns a plan candidate, not the public plan. The server compiles
allowlisted intent into owned effect/gate semantics, then validates unit IDs,
dependencies, source refs, tools, logical artifacts and human gates. Raw
candidate fields and compiler errors are not public facts.

A plan that fails structure or deterministic validation is marked `未采用`.
The server permits at most one repair attempt, only when the same Loop budget
still has a model call and time available. Both attempts consume the budget and
produce ordered events. There is no unbounded or hidden retry loop.

The current Analyst receives safe projections only from selected refs. Each
finding requires at least one selected `file_ref`; an out-of-scope citation
fails the Run. This proves reference membership only, not entailment,
exhaustiveness, arithmetic or policy correctness.

## 10. SSE

```http
GET /v1/harness/runs/{run_id}/events?after=3
Accept: text/event-stream
```

Representative two-round success order:

```text
workspace_index
round_started
planning_started
planning_completed
plan_validation_rejected (optional, followed by one retry)
plan_validation
deterministic_office_tool_started (when one fixed local capability is admitted)
run_workspace_artifact_written (for each isolated file)
deterministic_verification_completed (after all deterministic checks)
scenario_effect_bounded (for an explicit external/unsupported boundary)
analysis_started
analysis_completed
analysis_structure_rejected (optional, followed by one bounded retry)
analysis_validation_rejected (optional, followed by one bounded retry)
analysis_scope_filtered (optional when all verified observed dates are outside the instruction window)
decision_gate_suppressed (optional when a proposed human Gate has no contradiction Anchor)
analysis_partial_adopted (optional when only verified Findings remain)
analysis_recovery_required (optional before a guided waiting state)
evidence_disambiguation_required (optional for multiple real source positions)
partial_artifact_saved (optional when valid work is preserved)
decision_requested (optional for a human business choice)
result_validation
evidence_gate
decision_recorded (after accept / decline / defer / cancel)
evidence_resolution_stale (when the frozen source revision changed)
evidence_resolution_rejected (when the server-recomputed candidate is invalid)
control_resume_recorded (required when evidence_gate waits for the user)
branch_resumed_from_checkpoint (when only one recovery Branch continues)
round_started
planning_started
planning_completed
plan_validation
analysis_started
analysis_completed
result_validation
evidence_gate
loop_committed
artifact_version_restored (optional later human restore)
```

`checkpoint_recovered` may appear after an API restart backed by PostgreSQL.
It proves a persisted Snapshot was restored and the Run paused; it does not
prove an interrupted model call was resumed or replayed.

SSE `id` equals the event sequence. `after=N` returns only later events.
Heartbeats carry no business state. A terminal event is followed by final GET
reconciliation; a nonterminal interruption uses GET plus `after=N` recovery.

## 11. Error semantics

| Result | Meaning | Frontend response |
| --- | --- | --- |
| connection failure | API unreachable | keep draft; bounded automatic/explicit retry |
| workspace 503 | manifest/catalog integrity invalid | show integrity-specific fail-closed state; no model call |
| preview 404 | unknown ref | keep selection; show explicit preview error |
| preview 503 | selected byte failed integrity/safe parsing | never show stale/partial content |
| Run/SSE 404 | missing or wrong Owner | same public response; clear stale Run |
| start 409 | idempotency/contract conflict | preserve instruction/selection and reconcile |
| control 409 | stale version or illegal transition | GET current Snapshot; preserve command draft and let the user retry |
| decision 409 | Finding/Resolution/Branch binding is stale, or option/candidate is not owned by that record | GET current Snapshot; keep the user's feedback draft and choose from current facts |
| branch control 409 | selected Branch is missing, no longer waiting or outside the current Gate | GET current Snapshot and choose a still-waiting Branch |
| artifact restore 409 | version is current, missing or fails independent-record verification | keep current pointer and history; do not fabricate restore |
| Artifact download 404 | Artifact is not owned by this Run/Owner | keep Snapshot state; do not guess another file |
| Artifact download 503 | stored bytes are missing or fail size/digest verification | show a fail-closed download error; never return partial/drifted bytes |
| `status=waiting_input` | one or more Branches could close a visible evidence gap | inspect sources, optionally steer, then explicitly resume one Branch or stop |
| passed `workspace_artifacts[]` plus `status=waiting_input` | deterministic outcome is downloadable, while Analyst audit location remains unresolved | show outcome first and group only same-source/same-failure gaps in the browser; do not change Snapshot Branches or claim `completed` |
| `next_step.recovery_kind=source_location` | legal-scope candidate could not be uniquely mapped to safe Preview | for unavailable: show one recommended Branch retry with optional details collapsed; for ambiguous: require one explicit candidate choice before accept |
| `next_step.recovery_kind=analysis_output` | provider responded twice without a usable public result structure | keep raw output hidden; show one recommended minimal-Branch retry, optional feedback or stop |
| `checkpoint_recovered` | server restored a PostgreSQL Snapshot and paused | reconcile the trace; explicitly resume from the safe checkpoint |
| `loop_budget_stopped` | round/call/active deadline prevents another step; `budget.stop_reason` names the actual boundary | show the precise Chinese reason, bounded brief, preserved facts and candidate Branches; create a new Branch-scoped task instead of resuming the terminal Run |
| `status=failed` | model/schema/plan/source/citation validation failed | show safe business error and no result |

See [UI-server fact matrix](contracts/UI_SERVER_FACT_MATRIX.md),
[`DR-0036`](decisions/DR-0036-outcome-first-and-layout-tolerant-evidence.md),
[`DR-0034`](decisions/DR-0034-one-action-recovery-and-explicit-source-choice.md),
[`DR-0031`](decisions/DR-0031-active-budget-and-agent-owned-gap-recovery.md)
and [current Evidence](evidence/DR-0036-TC01-OUTCOME-EVIDENCE-LOCALIZATION-EVIDENCE-20260828.md).
