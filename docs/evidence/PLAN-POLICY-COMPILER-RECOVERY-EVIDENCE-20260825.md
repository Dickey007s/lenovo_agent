# Plan Policy Compiler Recovery Evidence · 2026-08-25

## 1. Status and scope

Status: `Limited Verified` for the current fixed FORTE read-only Harness, one API process and the tested desktop/browser path.

This evidence supports [DR-0020](../decisions/DR-0020-server-owned-plan-policy-compilation.md). It records both the negative progression and the final repair; failed intermediate runs are not erased.

## 2. Trigger evidence

| Artifact | Dimensions | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| [`user-feedback-20260825-plan-validation-language.png`](assets/user-feedback-20260825-plan-validation-language.png) | `1308 x 1231` | `190718` | `936E16A314770BB512872FB27799C4A03A937BE4986DD5CCDEE94BDF389616B1` |

The screenshot shows a provider call receipt marked “未采用” and a raw internal validation message. It is product feedback evidence, not root-cause or usability-study evidence.

## 3. Negative progression

| Run | Observed result | What it isolated |
| --- | --- | --- |
| `harness:ee52e7bdf85d430495c8d01c694d5e6c` | Planner called for `17603 ms`; candidate rejected | model-owned `side_effect` omitted the required workspace-write mapping |
| `harness:0017632...` | failed after `13769 ms` | compiler still required model-authored artifact metadata |
| `harness:d149a5...` | failed after `13607 ms` | model attached artifact metadata to a non-write verification unit |

The final compiler therefore supplies safe write defaults and strips artifact metadata from non-write tools before deterministic validation.

The first failure is bound to the saved feedback screenshot and API log. The latter two prefixes/timings are interactive development observations without a checked-in raw Run manifest; they preserve the repair sequence but are not independently auditable evidence on the same level as the final API/browser records.

## 4. Final live evidence

### API live run

- Run: `harness:b8bc82e6f34048ff8ce523014cd52e64`
- terminal: `completed`, v9/seq 8
- Planner: `14561 ms`, output adopted
- Analyst: `25011 ms`, output adopted
- plan: 8 units; three `table.inspect`, three `file.read`, one `evidence.verify`, one `artifact.write`
- compiled effects: read/inspect/verify=`none`; write=`run_workspace_write`
- result: 10 findings; no external side effect

### Browser live run

- Run: `harness:5dee3a8fb9a841a1a09e28dba9932fe2`
- terminal: `completed`, v9/seq 8
- Planner: `15059 ms`, `已采用`
- Analyst: `13443 ms`, `已采用`
- result: 3 findings over the selected FORTE Finance files
- DOM assertions: no `artifact.write` and no `run_workspace_write`

The resulting business answer identified three unchanged-balance records in that specific task response. This observation does not establish a general semantic or numerical quality claim.

| Artifact | Dimensions | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| [`dr-0020-safe-plan-compiler-completed.png`](screenshots/dr-0020-safe-plan-compiler-completed.png) | `1440 x 1000` | `208783` | `F8898A3AF5599199062F564E4396F267A012BC4A323D27FE4655A3E31B26BDB8` |

## 5. Automated verification

| Check | Result |
| --- | --- |
| focused Harness Python | `23 passed in 1.52s` |
| full Python | `56 passed in 2.57s` |
| Ruff | passed |
| web lint | passed |
| Harness browser E2E | `8 passed in 25.1s` |
| production build | compile `2.1s`; TypeScript `3.7s`; static generation `656ms` |
| `git diff --check` | passed; only Windows line-ending warnings |

The browser suite covers business-safe failure projection, the three receipt labels, active/terminal command states, known-failure fresh-key retry and unknown-outcome same-key retry.

## 6. Claim boundary

This evidence proves that the tested current Runtime no longer asks the model to own internal side-effect enums, safely compiles the observed plan intents, retains deterministic validation, hides raw protocol failures in ordinary UI and completes a real two-call read-only run.

It does not prove model plan quality, result correctness, universal plan compilability, persistent execution, production identity, Scheduler/Worker behavior, Tool Gateway or Artifact mutation, Connector action, cost/SLA, competitor difference or user understanding. The product remains read-only and memory-only.

## 7. Delivery

- implementation commit: [`373b79a`](https://github.com/Dickey007s/lenovo_agent/commit/373b79a)
- delivery PR: [#25](https://github.com/Dickey007s/lenovo_agent/pull/25), open and not yet merged
- first documentation/evidence commit: [`07e4684`](https://github.com/Dickey007s/lenovo_agent/commit/07e4684)
