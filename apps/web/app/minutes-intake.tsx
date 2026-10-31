"use client";

import { useState } from "react";
import { IconFileText, IconLoader2, IconScissors } from "@tabler/icons-react";
import { DEMO_MINUTES } from "./minutes-demo";
import type { MinutesSeed } from "./todo-batch";

type SplitResponse = { is_multi: boolean; method: "model" | "rules"; summary: string; todos: MinutesSeed["todos"] };

function readSplit(value: unknown): SplitResponse | null {
  const raw = value as Partial<SplitResponse> | null;
  if (!raw || typeof raw !== "object" || !Array.isArray(raw.todos) || typeof raw.is_multi !== "boolean") return null;
  const todos = raw.todos.filter(item => item && typeof item.instruction === "string" && item.instruction.trim())
    .map(item => ({ title: String(item.title ?? ""), instruction: item.instruction, source_quote: String(item.source_quote ?? "") }));
  return { is_multi: raw.is_multi, method: raw.method === "rules" ? "rules" : "model", summary: String(raw.summary ?? ""), todos };
}

// Main-entry helper: paste meeting minutes, let the server split them, and hand the result to
// the caller. One item goes to the single-task box; several go to the multi-task list.
export function MinutesIntake({ apiBase, headers, disabled, onSingle, onMulti }: {
  apiBase: string; headers: Record<string, string>; disabled?: boolean;
  onSingle: (instruction: string) => void; onMulti: (seed: Omit<MinutesSeed, "id">) => void;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function split() {
    if (busy) return;
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`${apiBase}/v1/harness/minutes/split`, {
        method: "POST", headers, body: JSON.stringify({ minutes: text }), signal: AbortSignal.timeout(90000),
      });
      if (!response.ok) {
        const detail = await response.json().then(body => body?.detail).catch(() => null);
        throw new Error(typeof detail === "string" ? detail : `拆分失败（HTTP ${response.status}）`);
      }
      const result = readSplit(await response.json());
      if (!result || !result.todos.length) throw new Error("没有从纪要里识别出需要办理的事项，请检查纪要内容");
      if (result.is_multi) onMulti({ method: result.method, summary: result.summary, todos: result.todos });
      else { onSingle(result.todos[0].instruction); setMessage("只识别出 1 项事项，已填入上方任务指令，确认后点启动即可。"); }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "拆分失败，请稍后重试");
    } finally {
      setBusy(false);
    }
  }

  return <details className="minutes-intake">
    <summary><IconFileText aria-hidden="true"/>从会议纪要拆分待办</summary>
    <p>粘贴一段会议纪要，系统会找出其中要办的事。只有一件就填入任务指令；有多件则跳到多任务待办，等你确认后再开始。</p>
    <textarea aria-label="会议纪要" value={text} maxLength={6000} disabled={disabled || busy} placeholder="粘贴会议纪要全文" onChange={event => setText(event.target.value)}/>
    <div>
      <button type="button" className="minutes-demo" disabled={disabled || busy} onClick={() => { setText(DEMO_MINUTES); setMessage(""); }}>载入示例纪要</button>
      <button type="button" className="minutes-split" disabled={disabled || busy || text.trim().length < 10} onClick={() => void split()}>
        {busy ? <IconLoader2 aria-hidden="true"/> : <IconScissors aria-hidden="true"/>}{busy ? "正在拆分" : "拆分待办"}
      </button>
    </div>
    {message && <p role="status" className="minutes-message">{message}</p>}
  </details>;
}
