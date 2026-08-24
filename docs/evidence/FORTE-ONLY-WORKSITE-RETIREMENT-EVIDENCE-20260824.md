# FORTE-only worksite and legacy retirement Evidence (2026-08-24)

## Status

`Limited Verified` for the current repository tree, public runtime surface, tested frontend recovery paths, and one observed live planning run. User comprehension, user value, execution, and production readiness remain `Draft`.

## Claim under test

The current product has one FORTE worksite. Legacy workspaces, routes, service modules, product tests, and Customer A files are absent from the current tree and runtime surface. Historical records remain available and are marked retired. The current Harness still stops at `ready_to_execute`.

## Source and stakeholder evidence

| Item | Evidence | What it supports | Limitation |
| --- | --- | --- | --- |
| Stakeholder direction | [`USER-FEEDBACK-20260824-FORTE-ONLY-09`](../sources/USER-FEEDBACK-20260824-09-single-forte-worksite-retirement.md) | one FORTE worksite, legacy retirement, history retention | one stakeholder; not user research |
| Browser failure capture | [`user-feedback-20260824-forte-only-offline.png`](assets/user-feedback-20260824-forte-only-offline.png), `1316 x 887`, `80179` bytes, SHA-256 `E79097991E06ACBFACB2954BC576EA0182A9B1A4E731CEC120B9AB9E71BDB0C3` | transitional legacy rail and undifferentiated offline state were observable | negative pre-fix evidence, not a final-state screenshot |
| FORTE source | upstream commit `345c1ec1487139db9dd319787fa9405ba85d1869`, top-level MIT, local manifest | source identity and redistribution basis | public benchmark, not enterprise production data |

## Implementation and delivery binding

| Item | Value |
| --- | --- |
| retirement implementation | [`b2b759b106738fbb3aed597319208e8ff4718cc7`](https://github.com/Dickey007s/lenovo_agent/commit/b2b759b106738fbb3aed597319208e8ff4718cc7) |
| recovery follow-up | [`5fab10fb4f638958ff78b39583a4eace2e99396b`](https://github.com/Dickey007s/lenovo_agent/commit/5fab10fb4f638958ff78b39583a4eace2e99396b) |
| PR | [#24](https://github.com/Dickey007s/lenovo_agent/pull/24), open and unmerged at capture |
| fresh-clone verification | remote PR branch cloned into an ignored verification checkout; HEAD exactly `5fab10f...` |

The fresh clone contained 11 FORTE files and `115352` source bytes with zero path/size/hash mismatches. The fixed Customer A path did not exist. The local `.runtime` verification path is intentionally not part of the external evidence contract.

## Current product surface

OpenAPI contained exactly six paths:

```text
/v1/health
/v1/harness/scenarios
/v1/harness/scenarios/{scenario_id}
/v1/harness/runs
/v1/harness/runs/{run_id}
/v1/harness/runs/{run_id}/events
```

Probes under the old `/v1/workspace`, `/v1/threads`, `/v1/tasks`, `/v1/demo1`, `/v1/demo2`, and `/v1/demo3` prefixes returned 404. Legacy API/application services and product-specific tests were removed from the current tree. The root frontend imports only the Harness worksite and activity rail; the old workspace rail and legacy product components are absent.

This evidence proves route and tree retirement, not secure deletion from Git history. Historical commits and evidence still contain the old names and facts by design.

## Data integrity incident and repair

The observed offline state was traced to source-byte drift rather than a model failure. The previous `.gitattributes` treated the FORTE Markdown inputs as text and normalized upstream CRLF to LF, while the manifest expected the upstream byte hashes. Catalog validation therefore failed closed.

The implementation restored upstream bytes, marked the vendored FORTE task/input files as binary, retained manifest/license files as LF text, converted Catalog integrity exceptions to controlled 503 responses, and split frontend status into API unreachable, Catalog unavailable, and Catalog invalid. The UI retries automatically and provides an explicit retry; it does not invent a Scenario on integrity failure.

## Observed live planning run

One final Finance-018 observation used the configured `deepseek-v4-pro` model. The recorded run ID prefix was `harness:bce...`; it reached version 6 / sequence 5 `ready_to_execute`, produced 10 plan units, and recorded `called=true`, `output_used=true`, `elapsed_ms=16838`. No tool or external action occurred.

This is an interactive final verification record, not a repository-bound repeated experiment or quality benchmark. The earlier DR-0016 manifest remains a separate historical run set and must not have its timings silently replaced.

## Automated verification

| Check | Result | Boundary |
| --- | --- | --- |
| Python full suite | `47 passed in 2.42s` | current Harness and retained safety primitives; retired product tests no longer exist |
| Ruff | passed | static Python check |
| Web lint | passed | frontend static check |
| Next production build | passed; compile `2.1s`, TypeScript `4.1s`, static generation `757ms` | current build observation |
| Harness browser E2E | `11 passed in 41.4s` | root entry, three scenarios, privacy, recovery, streaming, idempotency, desktop/mobile engineering proxy |
| FORTE integrity | 11 files, `115352` bytes, all size/hash checks matched | fixed source revision only |
| Route retirement | six OpenAPI paths; legacy prefixes 404 | current application build only |

## Visual evidence boundary

There is no independent screenshot of the final converged UI in this change. The only new PNG is the user's negative pre-fix capture. The 11 browser tests cover desktop and 390px behavior, but E2E is not a screenshot review and neither is user research. Older DR-0016 screenshots show the previous transitional surface and remain historical; they must not be presented as the final DR-0017 UI.

## Remaining boundaries

- `X-User-Id` is an unsigned demonstration placeholder, not production identity.
- Runs, ordered events, idempotency records, and async planning live in one API process memory and are lost on restart.
- The product stops at `ready_to_execute`. It has no execution command, Scheduler, Worker, tool call, Artifact mutation/verification/Commit, approval, Permit, Connector, or external side effect.
- Generic risk, authorization, gateway, and simulator packages retained in the repository are not mounted current product capabilities.
- No target-user study has measured comprehension, trust, efficiency, task success, or value.
- PR #24 being open does not mean the change is merged into `master`.

Structured facts are duplicated in [`dr-0017-forte-only-worksite.json`](manifests/dr-0017-forte-only-worksite.json) for hash and delivery checks.
