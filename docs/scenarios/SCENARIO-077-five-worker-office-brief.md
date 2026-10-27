# SCENARIO-077: Five-worker Office Brief

- User: office coordinator collecting weekly recruitment, administration and account-reading notes.
- Pain: a two-node demo cannot show downstream collaboration; a flat larger graph becomes cluttered.
- Goal: inspect real source analysis, dependent review, individual output and source evidence without managing Worker approvals.
- Input: three approved Word/PDF/Excel sources; five explicit requirements in a single Task, plus separate recruitment and onboarding todos.
- Completion: actual adopted summaries and dependency assessments, with all five work items accounted for. Not approval of a hiring, finance or access-control action.
- Decision: [DR-0090](../decisions/DR-0090-multistage-worker-display.md).
- Source: [stakeholder request](../sources/USER-FEEDBACK-20261024-more-than-two-agents.md).
- Evidence: [limited real runs and controlled regressions](../evidence/DR-0090-FIVE-WORKERS-20261024.md).

## Flow

1. Open Demo2, select the default cross-department brief group, inspect or edit three todos. No model call until submission.
2. Start the batch. Each Task uses its existing Run API request; simple tasks may stay under a single controller.
3. For the complex task, the model plans recruitment extraction, common-software extraction and counterparty amount extraction independently.
4. After adopted parents are available, one Worker reviews/summarizes the recruitment and software outputs; another compares the amount output with Excel.
5. Open Task to see dependency stages. Expand only the desired output; inspect Sources or full Results when needed.

## Exceptions

Rejected or ambiguous parent output remains visible and does not silently authorize dependent work. Accepted siblings remain retained under existing gates. Old attempts cannot become current green outputs. Missing/cyclic dependency projections are marked unknown. No human gate is fabricated for a Worker failure. Current permission, retry and budget limits remain; this example does not promise the same decomposition on every model run.
