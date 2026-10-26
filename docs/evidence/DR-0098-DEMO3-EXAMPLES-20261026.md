# DR-0098 Demo3 Example Evidence

Date: 2026-10-26. Local dirty worktree; no commit or PR. Scope: fixed-policy examples and original action workflows.

## Automated Results

- `.venv/Scripts/python.exe -m pytest tests/unit/test_office_action_examples.py tests/unit/test_office_actions.py -q`: **70 passed**. Includes 12 catalog inputs evaluated by real policy and one identity/coverage check.
- `pnpm exec tsc --noEmit` in apps/web: passed.
- `pnpm exec playwright test e2e/office-action-examples.spec.ts e2e/office-actions.spec.ts e2e/copilot-principles.spec.ts`: **29 passed**, 2.3 minutes. Real isolated FastAPI on8011 and Next on3011, system Edge. No mock success responses for examples. Existing network-loss test deliberately intercepts one response to verify idempotency.
- Twelve preset tests inspect actual status, model_called=false and external_action=none; then exercise the corresponding controls. The thirteenth new browser check covers draft field replacement and390px layout. Existing16 browser regressions cover action and preference safeguards.
- After shortening selector labels, the13 example browser checks passed again (43.4seconds), as did type checking. `node scripts/check-demo3-examples-report.cjs` verified HTML at1440/390px, all local links/images, no page errors or horizontal overflow, and the running3028 preview's unchecked strong-confirmation state. That preview item was deferred, not submitted externally.

## Visual Inspection

Desktop1440x1000 and mobile390x844 captured under [outputs](../../outputs/demo3-examples-20261026/). The selector is folded by default. After opening, only one selected case is shown, not twelve cards. Native select options were shortened to task titles after inspection; the boundary remains separately visible below. The main pane scrolls for long two-material forms rather than shrinking text.

## Demonstration Scope

[Catalog](../../apps/web/app/office-action-examples.json) supplies synthetic pasted inputs. It neither creates approved workspace files nor changes server state by selection. States and receipts are from the existing fixed server policy, not the catalog's expected_status. No model, real email, enterprise task or formal approval occurs. The embedded instruction case proves only literal non-executing excerpt behavior. No PostgreSQL, multi-instance or target-user study was run.

Preview: `scripts/start-demo3-examples.ps1`,3028/8028, in-memory, model endpoint disabled. Existing3000/3027 services remain untouched. Preview history is not durable across restarts.
