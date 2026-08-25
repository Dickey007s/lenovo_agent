# DR-0022: Replace registered scenarios with one whole-folder office workspace

## Decision metadata

| Field | Value |
| --- | --- |
| Status | `Ready for final evidence` |
| Date | 2026-08-25 |
| Trigger | `USER-FEEDBACK-20260825-WHOLE-FOLDER-14` |
| Research | [`WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825`](../research/WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825.md) |
| Scenario | [`SCENARIO-008`](../scenarios/SCENARIO-008-whole-folder-office-workspace.md) |
| Evidence | [`FORTE-FOLDER-WORKSPACE-EVIDENCE-20260825`](../evidence/FORTE-FOLDER-WORKSPACE-EVIDENCE-20260825.md) |
| Implementation | To be bound after commit |
| Delivery | To be bound after PR creation |

## Problem

The preceding workbench presented three registered Scenario groups. That made
the Agent look as though it acquired capabilities only when a Demo was chosen,
and prevented users from treating the benchmark as an ordinary office folder.
It also kept most of the pinned public FORTE files outside the product surface.

## Decision

The current product exposes one server-owned FORTE public office workspace:

1. The workspace contains all 15 public task folders and all 96 public input
   files imported from the pinned FORTE repository.
2. The browser displays a searchable folder tree. Users can open file metadata
   and a bounded read-only preview without starting a task.
3. Users explicitly select up to 20 files from any folder and write an original
   instruction. No benchmark `task.md`, rubric, solution or hidden task prompt
   becomes the user task.
4. CSV/XLSX, PDF, DOCX and text/code files have server-produced safe previews.
   Every preview is preceded by manifest path, size, hash, symlink and type
   checks. Active content and external resources are not executed.
5. A Run freezes only the selected `file_ref` values. Planning and result
   citations must stay inside that scope.
6. The ordinary UI shows ordered server events, separate model-call receipts,
   the validated plan and clickable citations. It does not show Prompt,
   chain-of-thought, raw provider output, absolute paths, hashes or validator
   protocol strings.

This is a general workspace contract. Demo 1, Demo 2 and Demo 3 remain
acceptance lenses for single-task loops, multi-task organization and governed
actions; they are not product modes that unlock private capability.

## User-flow impact

The interaction changes from `choose a prepared scenario -> watch its fixed
path` to `browse office files -> inspect evidence -> choose scope -> author a
task -> observe validated execution facts -> reopen cited evidence -> review`.

This makes file scope and provenance visible before model invocation. It also
adds a cost: users must make an explicit scope choice. Search, folder grouping,
file metadata, examples and selection chips reduce that burden without silently
selecting data on the user's behalf.

## Frontend output

| User question | Visible answer | Server fact | Hidden detail |
| --- | --- | --- | --- |
| What data exists? | 15 business folders, 96 files, type and size | `GET /v1/harness/workspace` | task prompt, rubric, solution, path, hash |
| What is in this file? | bounded table or document preview, row/page count and security note | `GET /v1/harness/workspace/files/{file_ref}` | macros, external fetches, full binary |
| What will the Agent read? | selected-file count and removable chips | request `selected_file_refs`; server revalidation | unselected workspace bytes |
| Did a model run? | called/adopted/not-adopted receipt and elapsed time | `HarnessModelReceipt` | Prompt, chain-of-thought, raw response |
| What did it do? | ordered execution trajectory and validated plan | named SSE plus Run Snapshot | raw event payload and validator code |
| Where did a claim come from? | clickable business file labels | result `file_refs` checked against frozen scope | absolute source path and digest |
| Did it act externally? | explicit read-only boundary and review warning | plan side-effect policy and terminal Snapshot | speculative UI animation |

## Backend ownership

- `public-suite-manifest.json` owns the imported byte inventory.
- `BenchmarkWorkspaceCatalog` owns safe paths, manifest integrity, format
  parsing, preview bounds and the public projection.
- `HarnessRuntime` owns the Run, selected source freeze, model receipts,
  server-compiled plan policy, event sequence, citations and terminal status.
- The browser owns only search, expansion, selection draft, instruction draft,
  transport state and presentation.

## Verification and boundary

The current implementation can prove folder/file inventory, bounded preview,
scope enforcement, ordered streaming, citation membership and a read-only
result in one API process. It does not prove semantic or numerical correctness,
durable recovery, distributed workers, file mutation, real Connector calls,
production identity or user value. FORTE is public benchmark data, not a live
enterprise database.

The decision becomes `Limited Verified` only after code commit, focused and
full automation, desktop/mobile browser evidence, manifest/hash checks and a
delivery PR are bound in the Evidence record.
