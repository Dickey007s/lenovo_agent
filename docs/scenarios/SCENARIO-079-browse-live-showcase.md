# SCENARIO-079: Browse the current system's real office cases

## User goal

A viewer understands the task input, actual system work, evidence, human boundary and output without opening the development environment.

## Flow

1. Open the offline showcase and choose a capability tab and case.
2. Read its business instruction. Move through the actual screenshot steps.
3. Open a screenshot at native resolution to inspect evidence or Agent receipts.
4. Read the actual outcome and expand provenance/boundaries where needed.
5. Use browser back/reload, keyboard navigation or another case without losing orientation.

## Acceptance

- Eight stories across three tabs; every screenshot loads at 1920x1200.
- Rule-based direct handling, missing material and explicit human choice are distinct.
- Human continuation stays in the same Task, with parent/child evidence.
- Demo2 distinguishes single-controller and three-worker actual routes without prescribing counts in input.
- No expansion animation when the real review chose no addition.
- Demo3 content edits invalidate earlier confirmation; human material selection needs a reason.
- Offline screenshot browsing makes no HTTP requests or model calls.
- 1920/1440/768/390 widths have no page-level horizontal overflow.

See [DR-0092](../decisions/DR-0092-live-showcase-refresh.md) and its Evidence for the bounded observations and unsuccessful attempts.
