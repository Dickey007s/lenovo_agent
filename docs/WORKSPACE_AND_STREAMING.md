# Whole-folder workspace and streaming

## 1. Interaction model

The product is one office folder, not a Scenario chooser. The persistent layout
is:

- left: folders, files, search, metadata and selection checkboxes;
- center: task composer and tabs for file preview, plan and result;
- right: actual Agent trajectory and model receipts.

These regions answer four user questions in order: what data exists, what will
the Agent read, what did it actually do, and where did the answer come from.

## 2. Browse before invocation

`GET /v1/harness/workspace` returns 15 business folders and 96 file projections.
Opening a file calls the preview route but does not create a Run or invoke a
model. The preview header shows business path, extension, size and row/page
count. A security footer explains integrity, read-only, active-content and
external-resource behavior.

The user may inspect unselected files. Only explicit checkbox selection enters
the task scope. Search and expansion are client presentation state and do not
change server truth.

## 3. Task composer

The task is always user-authored. Example chips only fill the editable textarea;
they do not start a task. The Run button remains disabled until the instruction
contains at least three characters and one file is selected.

Selection chips show the visible context contract. Clearing or changing the
instruction changes the command signature. If a start response is unknown, the
client retries the unchanged signature with the same idempotency key; a known
terminal retry uses a fresh key and independent Run.

## 4. Preview contract

| Preview | User-visible projection | Safety boundary |
| --- | --- | --- |
| XLSX/CSV | bounded table with row numbers | formulas/macros not executed; first visible sheet for XLSX |
| DOCX | extracted text | no macros; relationship scan; external resources not loaded |
| PDF | page count and extracted text layer | encrypted/oversized input fails closed; active resources not run |
| TXT/MD/JSON/log/code | bounded decoded text | content displayed as text, never executed |

Truncation is explicitly labeled. A parser/integrity error replaces the preview
with a safe error; stale or partial data is not shown as valid.

## 5. Plan, result and citation

The plan tab appears only after the server validates the model candidate. It
uses business operation labels. `只写本轮成果` means a logical Run result in
the current plan, not that a file or ArtifactVersion was written.

The result tab appears only after citation-scope validation. It is labeled
`模型初步结论 · 待复核`. A citation button resolves against the workspace
projection, selects that file and switches back to its preview. This keeps
evidence review inside the main task flow.

## 6. Call receipts and trace

The right pane distinguishes:

- `未调用`: no provider request occurred;
- `已采用`: provider returned and server checks accepted the output;
- `未采用`: provider returned but checks rejected the output.

Elapsed milliseconds are an observed call duration, not production SLA or cost.
The trajectory uses named server events and business summaries. Prompt,
chain-of-thought, raw provider response, token traces and validator code stay
hidden.

## 7. Streaming and reconciliation

For a nonterminal Run the client opens:

```text
GET /v1/harness/runs/{run_id}/events?after={last_observed_sequence}
```

Rules:

1. apply only events for the current Run;
2. never decrease Snapshot version or last event sequence;
3. use SSE only as ordered change notification;
4. read the current Snapshot after business events;
5. on nonterminal failure, reconnect from `after=N`;
6. after a terminal event, close the stream and perform final GET.

The header says the service is available when HTTP is reachable. It says the
trajectory is live only while an EventSource is open. Transport state is a
browser fact, not a server task phase.

## 8. Failure and recovery

| Failure | Visible state | Preserved | Recovery |
| --- | --- | --- | --- |
| API offline | workspace unavailable/offline | local task draft when possible | bounded retry and explicit retry |
| manifest integrity invalid | integrity-specific unavailable state | no stale catalog | repair/import source then retry |
| preview error | file-specific safe error | folder/selection/task draft | reopen or choose another file |
| unknown start result | reconciling | same instruction/refs/key | replay identical request |
| model/schema/policy failure | safe stop plus receipt | selected scope and instruction | revise or create a fresh Run |
| SSE interruption | reconnecting | current Snapshot and last sequence | GET plus `after=N` |

## 9. Responsive behavior

Desktop keeps folder, work area and activity pane visible. Narrow layouts stack
the same functions rather than shrinking the folder tree into an unreadable
diagram. The tested 390 px path keeps file selection, task input, preview,
trajectory, plan, result and citation actions touch-usable and avoids page-level
horizontal overflow. Tables may scroll inside their own preview region.

## 10. Hidden details

Ordinary DOM must not contain benchmark task prompt/rubric/solution, raw path,
digest, model Prompt, chain-of-thought, raw response, credentials, internal
effect/gate enums or low-level logs. The UI may show business labels, bounded
content, call receipts, validation status and citations because those facts help
the user decide or recover.
