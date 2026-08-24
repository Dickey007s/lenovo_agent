# Governance and Action Boundary

## 1. Current governed path

The current product governs a read-only analysis result:

```text
server-owned Scenario + selected source set
  -> model plan candidate
  -> deterministic plan validation
  -> model result candidate over safe previews
  -> deterministic selected-file citation validation
  -> completed response + review_required=true
```

No current route continues into a Tool Gateway or external action. Retained risk, evidence, authorization, gateway and simulator packages are future building blocks, not mounted current capabilities.

The work policy is generic: `task_topology`, `orchestration` and `control_requirements`. Demo names never select a governance shortcut. `risk_gate` must apply to any single-task or multi-task plan that proposes a side effect; `evidence_gate` and `human_gate` pause the affected work based on server facts, not presentation mode.

## 2. Server-owned facts

The server owns:

- Scenario identity, manifest integrity, safe preview and stable `file_ref`;
- frozen instruction, instruction source and selected file set;
- allowed tools/effect declarations;
- Run identity, Owner, version, status and sequence;
- plan validation and result citation-scope validation;
- separate planning/analysis call receipts and adoption facts;
- result schema, `review_required=true` and no-external-action terminal message.

The model proposes plan/result text. It does not own source identity, state, sequence, validation, execution or external-effect facts.

## 3. Deterministic checks

### Before analysis

A plan fails closed for duplicate/unknown units, cycles, unselected file refs, unallowlisted tools/effects, unsafe Artifact names, invalid `artifact.write` mapping, or an external-action declaration without `action.preview` and a human gate.

### Before completion

A result fails closed when its schema is invalid, has no findings, omits citations, cites an unselected ref or does not require review.

Citation validation checks membership only. It is not semantic, numeric, exhaustive, policy or row-level verification. The deterministic Finance regression produces 23 / `1,845,444.71`, while the observed live response produced 20 / `2,202,000`; the frontend must not label `completed` or `result_validation` “事实已证明” or “质量通过”.

## 4. Plan declaration versus action

| Declaration | Current meaning | Not current |
| --- | --- | --- |
| `file.read/table.inspect/evidence.verify` | proposed plan intent | no Tool Gateway receipt |
| `artifact.write + run_workspace_write` | proposed logical result organization | no ArtifactVersion, mutation or Commit |
| `action.preview + external_action + human gate` | a future governed-action boundary | no approval, Permit, Simulator or Connector |
| `status=completed` | an initial bounded read-only response is reviewable | no correctness, quality-pass or external business-process claim |

The Analyst is called directly with Catalog previews. This is model inference over server-projected data, not a generic tool-execution loop.

## 5. Foreground impact

The current UI must show:

- selected file count and read-only boundary before start;
- separate planning and analysis receipts;
- named server events, not raw reasoning;
- result citations resolved to visible file labels;
- follow-ups under “仍需你判断”;
- a final statement that the result needs review and no external action occurred.

It must hide Prompt, chain of thought, raw response, filesystem path/hash, rubric/solution/grading data, credentials and internal logs.

## 6. Future action chain

The following remains `Draft`:

```text
reviewed result
  -> deterministic spreadsheet operator + claim verifier
  -> immutable ArtifactVersion + verifier
  -> semantic ActionCandidate
  -> Risk / Policy / Evidence
  -> human Approval
  -> signed Permit
  -> Tool Gateway
  -> Simulator or Connector
  -> execution receipt
```

Future foreground impact should retain the four classes 会改变、会重新核对、保持不变、不会发生 and distinguish preview from actual receipt. Historical Customer A action Evidence cannot verify migration to the current workbench.

## 7. Evidence boundary

[DR-0018 Evidence](evidence/FORTE-DATA-WORKBENCH-TRACE-EVIDENCE-20260824.md) binds two observed Finance-018 read-only Runs, focused automation, three provenance-scoped screenshots, a deterministic negative regression and implementation baseline `fffa36a...`. It does not prove semantic correctness, user value, production identity/durability or any external action.
