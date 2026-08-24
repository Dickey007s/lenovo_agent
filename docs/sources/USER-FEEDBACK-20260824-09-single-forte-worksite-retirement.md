# Stakeholder feedback: single FORTE worksite and legacy retirement

## Source metadata

- Source ID: `USER-FEEDBACK-20260824-FORTE-ONLY-09`
- Type: Stakeholder product decision and browser feedback
- Date: 2026-08-24, Asia/Shanghai
- Owner: Office Agent project team
- Related decision: [`DR-0017`](../decisions/DR-0017-single-forte-worksite-and-legacy-retirement.md)
- Screenshot: [`user-feedback-20260824-forte-only-offline.png`](../evidence/assets/user-feedback-20260824-forte-only-offline.png)

## Original feedback

> 目标是唯一 FORTE 工作现场、删除旧工作区运行入口/客户A固定数据，历史 docs/evidence保留为历史记录但明确 retired。

The attached browser capture is retained as page evidence, not as additional quoted user text. It shows a transitional page with the legacy mail/document/quote/task/calendar/expense/CRM/audit rail, a “返回工作区” action, three unavailable scenario cards, and an undifferentiated `Failed to fetch` / offline state. The PNG is `1316 x 887`, `80179` bytes, SHA-256 `E79097991E06ACBFACB2954BC576EA0182A9B1A4E731CEC120B9AB9E71BDB0C3`.

## Supported judgment

1. The current product must have one public entry and one visible worksite: the FORTE-backed Harness.
2. Legacy workspace navigation, legacy runtime routes, and the fixed Customer A dataset must not remain part of the current product tree or public runtime surface.
3. Historical decisions, scenarios, evidence, screenshots, and Git history must remain traceable, but they must be explicitly marked `Retired` so that a previously verified vertical slice is not mistaken for current behavior.
4. Recovery feedback must distinguish service unavailability, a temporarily unavailable catalog, and catalog integrity failure; the UI may not collapse all three into `Failed to fetch`.

## Limitations

This is one stakeholder's product direction and one browser-state capture. It is not target-user research and does not prove that the converged worksite improves comprehension, trust, efficiency, or task success. The capture proves that a confusing transitional failure state was observed; it does not by itself prove the later repair. Current implementation claims require the separate DR-0017 Evidence.
