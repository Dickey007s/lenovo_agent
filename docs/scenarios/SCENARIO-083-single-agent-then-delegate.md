# SCENARIO-083: Single Agent Then Delegate

- Target user: office colleague giving business goals without Agent counts.
- Trigger: a single readonly analysis returns findings that may warrant a new question.
- Pain: the previous single-controller path could not enter result-driven delegation.
- Goal: finish simple work directly; append justified checks without redoing the parent.
- Completion: output, original/adaptive work and actual call history remain visible in one Task.
- Source: [user authorization](../sources/USER-FEEDBACK-20261026-modern-delegation.md).
- Decision: [DR-0096](../decisions/DR-0096-single-agent-result-driven-delegation.md).
- Status: Limited Verified within [Evidence](../evidence/DR-0096-SINGLE-AGENT-DELEGATION-20261026.md).

Main path: submit goal; validated single unit executes; source/anchor checks adopt output; budget-reserved review proposes no addition or grounded new work; code validates and appends; existing dependency-aware executor handles the new Branch. Same Task retains original contribution and new receipts.

Exceptions: no spare budget means no review. Missing/deferred requirements retain conservative routing. Human judgment cannot be delegated away. Invalid source/trigger leaves a blocked adjustment and preserved output. Pause/stop prevents late promotion; restart does not replay interrupted review. User may inspect evidence/results or stop/use existing recovery; inspection causes no model call.

UI reads Task/Run, original topology event, current topology, adaptive_reviews.origin/status/added_branch_ids and actual WorkUnit/Worker/Contribution records. Reasons expand on demand; prompts and internal IDs remain hidden. A dependent chain proves sequencing, not parallelism, semantic truth or optimal staffing.
