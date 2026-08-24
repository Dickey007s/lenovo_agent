# Governance and Action Boundary

## 1. Current governance

The current FORTE worksite governs plans, not actions. Its live path is:

```text
server-owned Scenario and source set
  -> model plan candidate
  -> deterministic Admission & Plan Validator
  -> public validated plan
  -> ready_to_execute
```

No current route continues beyond this boundary. Generic risk, evidence, authorization, tool-gateway and simulator packages may remain in the repository, but they are not mounted capabilities of the current product.

## 2. Server-owned facts

The server owns:

- Scenario identity, safe public contract and frozen source references;
- allowed tools and side-effect categories;
- Run identity, Owner, version, status and ordered event sequence;
- unit dependency validity and source-reference mapping;
- validation outcome and error list;
- whether the model was called, whether its output was adopted, and elapsed observation;
- the fact that execution has not started.

The model owns only bounded plan text and intent. The frontend owns presentation and local interaction state, not business truth.

## 3. Deterministic plan checks

A proposed plan fails closed when it contains:

- unknown or duplicate unit identities;
- unknown dependencies or a dependency cycle;
- an input path outside the frozen Scenario source set;
- a tool or side effect outside the Scenario policy;
- a source write or path-shaped Artifact name;
- `artifact.write` without `side_effect=run_workspace_write`;
- `run_workspace_write` without `artifact.write`;
- an external-action candidate without a human-gate declaration;
- malformed or excessive units.

The successful UI wording is “计划已通过服务端校验，尚未执行”. It must never be shortened to “任务已完成”.

## 4. Visible impact

Even before execution exists, the UI must make plan impact legible:

| Plan declaration | What the user may see | What must remain explicit |
| --- | --- | --- |
| `side_effect=none` | read/inspect/analyze candidate | no source or external system is changed |
| `run_workspace_write` | proposed logical Artifact name/type | no Artifact has been written yet |
| `external_action` + human gate | proposed action boundary and gate requirement | no approval, Permit, tool or Connector has run |

The four future impact classes remain useful design principles: 会改变、会重新核对、保持不变、不会发生. They are not current execution receipts.

## 5. Target action chain

The future execution architecture remains `Draft`:

```text
validated plan
  -> Scheduler / Worker
  -> versioned Artifact + verification
  -> semantic ActionCandidate
  -> Risk / Policy / Evidence
  -> human Approval
  -> signed Permit
  -> Tool Gateway
  -> Simulator or Connector
  -> execution receipt
```

Before any part becomes current, it must be bound to the FORTE Task Contract and exposed through new server facts, tests, Evidence and UI mappings. The existence of historical Customer A Simulator evidence does not verify migration to this worksite.

## 6. Required execution invariants

These remain target requirements:

- an action must bind the current immutable Artifact version, verification and digest;
- policy, evidence, approval and Permit must be rebuilt or revalidated after any bound content change;
- impact preview is not an execution receipt;
- denial, expiry, tampering or tool failure must preserve completed upstream work;
- unknown tool outcome must be “待核对”, never inferred as success or no-op;
- real Connector writes must be distinguished from Simulator results;
- internal event payload, token, signature, Prompt and chain of thought stay out of ordinary business UI.

Until those facts are implemented in the current Harness, every execution, governance and user-value statement is `Draft`.

## 7. Evidence boundary

[DR-0017 Evidence](evidence/FORTE-ONLY-WORKSITE-RETIREMENT-EVIDENCE-20260824.md) verifies only the single worksite, source integrity, safe planning projection, deterministic validation, Snapshot/SSE, recovery behavior and no-execution boundary. One live Finance-018 run reached `ready_to_execute`; it did not call a tool or produce an external side effect.
