# SCENARIO-078: Result-driven Office Work

- User: office coordinator preparing onboarding/recruitment/account-reading notes.
- Trigger: simple business requests arrive without an execution graph.
- Pain: previous5-node example prescribes tasks/dependencies, hiding whether the system can adapt.
- Goal: original request determines initial routing; actual findings can justify bounded new work.
- Completion: clear source-backed results, actual initial/adaptive work accounted for, exceptions explicit.
- Source: [stakeholder](../sources/USER-FEEDBACK-20261024-adaptive-progress.md).
- Decision: [DR-0091](../decisions/DR-0091-result-driven-bounded-adaptation.md).
- Evidence: [DR-0091](../evidence/DR-0091-ADAPTIVE-PROGRESS-20261024.md). Real initial routing and no-add decisions observed; additions verified only with controlled model responses.

User starts readonly office todos. Planner proposes initial work; server chooses route. An admitted collaborative task returns grounded results, then a coordination review may decide no new work or propose a new question tied to actual findings. Server validates the append-only addition before another ready wave. UI shows the initial reason and the recorded adjustment; details remain collapsed.

Failed/ambiguous work is not repaired by creating an equivalent new Agent. Missing/unapproved source, human-decision trigger, malformed review and insufficient execution budget cannot silently authorize work. Late replies after pause/stop do not add nodes. Old outcomes stay; review failures remain explicit. New work and its execution receipt are separate facts.
