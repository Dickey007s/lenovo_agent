# SCENARIO-076: Understand Office Todo Outcomes

- Target user: an office coordinator preparing recruitment, onboarding and account-reading notes.
- Trigger: several small readonly work items need completion without managing Agent chats.
- Current pain: long instructions dominate the batch, actual outputs are hidden, planned collaboration looks executed, and leaving the batch loses its local overview.
- Goal: identify what each task did, why its execution route was chosen, what remains unfinished and where its source is.
- Completion condition: separate accepted Tasks; actual per-task route/call/adoption facts; outcomes linked to source views; read-only return to the same batch; original instructions retained.
- Decision: [DR-0089](../decisions/DR-0089-office-todo-outcomes-and-routing.md).
- Source: [USER-FEEDBACK-20261024-DEMO2-OFFICE-TODOS](../sources/USER-FEEDBACK-20261024-demo2-office-todos.md).
- Evidence status: Limited Verified; live bounded samples plus controlled regression. Not user research.

## Happy Path

1. Select daily office or personnel-document examples and edit the three instructions if needed.
2. Start all: three independent Run API requests authorize automatic readonly processing under DR-0086.
3. A one-file extraction runs under one controller. Independent cross-domain work can enter bounded readonly workers. Same-directory work can remain sequential according to existing admission policy.
4. Read a concise adopted result per work item. Expand reasons only when interested.
5. Open task, inspect actual work-package output and source, then return to the same batch without starting anything.

## Exceptions And Controls

- Unknown start: same payload and key on retry, already accepted tasks skipped; navigation stays locked until resolved.
- One rejected/unresolved contribution: preserve adopted sibling findings, show unfinished title, no fabricated human choice or automatic approval.
- Loop completed with missing evidence or human decision: do not label the business task fully complete.
- No usable output: no green analysis-delivered claim.
- Old attempt: no current adopted box unless the latest contribution and attempt match.
- Refresh: local batch lost; accepted tasks remain in recent history while server state survives. New Task resets only the composer.

## Frontend And Backend Facts

See DR-0089 and UI_SERVER_FACT_MATRIX. All server Task/Run owner, version, idempotency, readonly source and budget rules remain. Hidden details are instructions/reasons/receipts; errors and unfinished work are not hidden. This slice does not add cross-Task priorities, distributed scheduling or a learned difficulty estimator.
