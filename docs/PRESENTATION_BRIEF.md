# Office Agent V0.2 presentation brief

## 1. One-sentence story

We are not building three scripted Demos. We are building one general office
Agent Harness that starts from inspectable files, makes data scope explicit,
shows what the Agent actually called and accepted, and lets users review every
result against the same evidence.

## 2. Mandatory reporting frame

Every architecture or Demo claim must include:

1. concrete user/scenario trigger and exception path;
2. exact source ID, date/version, supported judgment and limitation;
3. technical difference from mainstream practice;
4. resulting change to the user's interaction flow;
5. visible frontend state/action/feedback/recovery;
6. authoritative server fact and hidden internals;
7. Evidence status and claims that remain Draft.

The retained source pack is
[`WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825`](research/WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825.md).
所有汇报状态与完成口径还必须遵守
[`DECISION_AND_REPORTING_GOVERNANCE.md`](DECISION_AND_REPORTING_GOVERNANCE.md)。
每项结论必须同时写清场景与来源、前台交互影响、后端事实和验证边界。

## 3. Recommended slide story

| Page | Claim | Visual | Evidence/boundary |
| --- | --- | --- | --- |
| 1 | Office Agent begins from an office folder, not a Demo button | full current workbench screenshot | `DR-0022`; public benchmark, not enterprise drive |
| 2 | The problem is hidden context and invisible execution, not lack of another chat box | prior flow vs folder-first flow | Stakeholder feedback; not user research |
| 3 | One Runtime, eight modules, three acceptance lenses | layered architecture with Demo 1/2 plus cross-cutting Demo 3 | current vs target colors must differ |
| 4 | Mainstream products prove sessions, tools, subagents and review are now baseline | official-source comparison table | OpenClaw/Codex/Claude official docs; no competitor benchmarking |
| 5 | Our deliberate emphasis is explicit office evidence scope | browse -> inspect -> select -> instruct -> observe -> cite -> review | implementation difference, not superiority claim |
| 6 | A pinned public dataset makes the Demo inspectable | 15 folders, 96 files and type distribution | FORTE commit/inventory; not real enterprise data |
| 7 | Safe preview turns data access into a visible contract | CSV/PDF/DOCX/TXT preview mosaic plus security facts | path/size/hash/symlink/parser tests |
| 8 | The Harness separates model call, adoption and validation | event/receipt sequence | receipt and Snapshot facts; no CoT exposure |
| 9 | Citations are navigation, not decoration | result citation reopening source preview | membership check only; not semantic truth |
| 10 | Demo 1 target is a bounded single task that pauses at evidence/human decisions | checkpoint/branch loop | target design; executor not current |
| 11 | Demo 2 target is adaptive multi-task organization over shared artifacts | worker/dependency/replan map | target design; current product has no Workers |
| 12 | Demo 3 governs actions from either topology | impact preview -> evidence -> approval -> permit -> receipt | target design; current no external action |
| 13 | Current proof and preserved negative result | tests/screenshots plus Finance mismatch | cited result can still be wrong |
| 14 | Next milestone is deterministic verification plus isolated Artifact workspace | roadmap | Draft until implementation evidence |

## 4. Live Demo path

1. Open `/` directly into `办公资料库`.
2. Expand two folders and inspect file type, size and a safe preview before any
   model call.
3. Select files from more than one folder and write an original task.
4. Start the Run and point to separate Planner/Analyst receipts. Do not call an
   animation a model invocation.
5. Show the validated plan and explain that business operations are intent,
   not executed tools.
6. Open a result citation and return to the exact source preview.
7. End on the review/no-external-action boundary.

Avoid beginning with eight-module architecture. The user first needs to see the
data, task and evidence loop the architecture supports.

## 5. Mainstream comparison wording

Safe wording:

- OpenClaw foregrounds a self-hosted Gateway, channels, sessions, routing, tools
  and host approvals in its official material.
- The Codex app foregrounds parallel project threads, worktrees, change review,
  Skills and Automation review queues.
- Claude Code foregrounds project-directory context, agent/tool loops,
  subagents, permission modes and multiple developer interfaces.
- This project deliberately foregrounds a server-owned office folder, explicit
  per-task file scope, visible call/adoption/validation facts and citations that
  reopen business evidence.

Do not say competitors cannot support these ideas. Official documentation is
not a controlled product test, and absence from a cited page is not proof that a
capability does not exist.

## 6. Interaction impact to say explicitly

| Technical choice | User-flow change | Frontend output |
| --- | --- | --- |
| whole-folder server catalog | browse before asking | folders, metadata, availability |
| explicit selected refs | user owns context boundary | selection chips and count |
| bounded format adapters | inspect evidence without execution | table/document preview and security footer |
| policy compiler after model | model cannot silently own side effects | call receipt separate from validated plan |
| ordered events + Snapshot | progress/recovery is factual | trajectory, reconnecting and final reconciliation |
| citation membership | review stays inside the task | citation button reopens source |
| review-required terminal state | completion is not correctness | `模型初步结论 · 待复核`, no external-action statement |

## 7. Evidence status

Current verification for `DR-0022` before implementation commit/PR binding:

- focused Python: `26 passed in 15.37s`;
- full Python: `51 passed in 13.16s`;
- browser: `8 passed in 22.9s`;
- Ruff and frontend typecheck: passed;
- production build: compile `2.4s`, TypeScript `3.2s`, static `682ms`;
- fresh browser run: `8.7 s` planning + `16.7 s` analysis, both adopted;
- nine screenshots and their SHA-256 values are manifest-bound; commit/PR is pending.

Exact final numbers must be copied from
[`FORTE-FOLDER-WORKSPACE-EVIDENCE-20260825`](evidence/FORTE-FOLDER-WORKSPACE-EVIDENCE-20260825.md),
not from an older deck or Evidence file.

## 8. Claims not allowed

- “the full 180-task FORTE dataset was downloaded”;
- “public FORTE files are real Lenovo or customer enterprise data”;
- “all 15 FORTE tasks are solved”;
- “a citation proves a conclusion or number is correct”;
- “a plan operation means a tool/file write happened”;
- “Demo 1/2 executors and Demo 3 real action gate are already current”;
- “API memory state is durable or multi-instance”;
- “the new UI is clearer, more trusted or more efficient” without user research.
