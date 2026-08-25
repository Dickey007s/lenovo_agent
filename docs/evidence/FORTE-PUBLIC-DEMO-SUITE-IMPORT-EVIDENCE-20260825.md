# FORTE public demo suite import evidence

## Status

`Limited Verified` for acquisition and byte integrity only.

## Evidence scope

| Fact | Evidence |
| --- | --- |
| Source | Official FORTE repository at `345c1ec1487139db9dd319787fa9405ba85d1869` |
| Local source cache | `.runtime/forte-upstream-345c1ec`, ignored by Git, detached at the pinned commit |
| Reproducible import | [`scripts/sync-forte-public-demos.py`](../../scripts/sync-forte-public-demos.py) |
| Complete inventory | [`public-suite-manifest.json`](../../demo-enterprise-data/forte/public-suite-manifest.json) |
| Test design | [`FORTE-PUBLIC-OFFICE-TASK-TEST-CASES-20260825.md`](../testing/FORTE-PUBLIC-OFFICE-TASK-TEST-CASES-20260825.md) |

The inventory manifest is `35,927` bytes with SHA-256
`BC2BC5AE1C58D5CC9C5983C972326CE4DBB09855FC724BE4E1530D66011E2D60`.

## Observed inventory

- 15 public task records;
- 96 public input files across 13 local-input tasks;
- two task-only external-dependency examples;
- 111 imported task/input files;
- `143,462` task bytes, `1,636,983` input bytes and `1,780,445` total bytes;
- no imported path under `solution/` or `skills/`.

## Validation

- `uv run python scripts/sync-forte-public-demos.py .runtime/forte-upstream-345c1ec`
  returned `Imported 15 public demos, 96 inputs, 1780445 bytes.`
- `uv run pytest -q tests/unit/test_forte_public_suite.py tests/unit/test_benchmark_scenario_catalog.py`
  returned `12 passed in 1.41s` during implementation.
- `uv run ruff check scripts/sync-forte-public-demos.py tests/unit/test_forte_public_suite.py`
  passed during implementation.
- Full Python: `58 passed in 2.42s`.
- Full Ruff: passed. The immutable public fixture root is excluded from project
  lint rather than modifying upstream code bytes.
- Web TypeScript lint: passed.
- Next.js production build: passed; compile `2.2s`, TypeScript `3.5s`, static
  generation `646ms`.
- Reporting governance: `4 passed in 0.03s`.
- Local Markdown links across the ten changed/new living and evidence documents:
  passed.
- staged `git diff --check`: passed; all 111 manifest-declared source files are
  tracked or staged. The imported `.log` fixture is explicitly unignored while
  ordinary runtime logs remain ignored.
- Implementation commit and PR are pending final commit/push and must be
  appended rather than guessed.

The integrity test verifies every imported path, size and SHA-256, rejects
solution/skills leakage by inventory equality, and proves the current
three-task runtime pack is an exact subset of the public suite.

## Boundaries

- The official public repository is not the complete 180-task benchmark.
- Acquisition is not parser support, execution support or a quality result.
- The current product Catalog still exposes only Finance, release readiness
  and operations scenarios.
- Two examples have no local input bundle and require external systems.
- Public benchmark records are not Lenovo data, a real customer workspace or
  a production Connector.
- No solution, grading result, user study, model-quality result or task-success
  claim is included in this evidence.
