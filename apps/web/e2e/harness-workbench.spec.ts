import { expect, test, type Page, type Route } from "@playwright/test";

type FileItem = {
  file_ref: string;
  folder_id: string;
  display_label: string;
  display_group: string;
  display_path: string;
  display_summary: string;
  extension: string;
  mime: string;
  size: number;
  preview_kind: "table" | "document" | "pdf" | "text";
  preview_available: true;
};

const csvFile = fileItem("forte-1111111111111111", "forte-folder-111111111111", "往来余额.csv", "财务管理", "CSV", "table");
const pdfFile = fileItem("forte-2222222222222222", "forte-folder-222222222222", "授权委托书.pdf", "法务", "PDF", "pdf");
const docxFile = fileItem("forte-3333333333333333", "forte-folder-333333333333", "岗位说明.docx", "人力招聘", "DOCX", "document");
const txtFile = fileItem("forte-4444444444444444", "forte-folder-444444444444", "运行日志.txt", "可靠性工程", "TXT", "text");

function fileItem(fileRef: string, folderId: string, label: string, group: string, extension: FileItem["extension"], kind: FileItem["preview_kind"]): FileItem {
  return {
    file_ref: fileRef,
    folder_id: folderId,
    display_label: label,
    display_group: group,
    display_path: `${group}/${label}`,
    display_summary: `${extension} 办公文件 · 12 KB`,
    extension,
    mime: extension === "CSV" ? "text/csv" : extension === "TXT" ? "text/plain" : "application/octet-stream",
    size: 12_288,
    preview_kind: kind,
    preview_available: true,
  };
}

const seedFolders = [
  { folder_id: csvFile.folder_id, display_label: "财务管理", display_summary: "跨期间往来资料", files: [csvFile] },
  { folder_id: pdfFile.folder_id, display_label: "法务", display_summary: "合同与授权材料", files: [pdfFile] },
  { folder_id: docxFile.folder_id, display_label: "人力招聘", display_summary: "岗位与候选人材料", files: [docxFile] },
  { folder_id: txtFile.folder_id, display_label: "可靠性工程", display_summary: "运行日志与服务资料", files: [txtFile] },
];

const folders = Array.from({ length: 15 }, (_, folderIndex) => {
  const seed = seedFolders[folderIndex];
  const folderId = seed?.folder_id ?? `forte-folder-${String(folderIndex + 1).padStart(12, "0")}`;
  const targetCount = folderIndex < 6 ? 7 : 6;
  const files = seed ? [...seed.files] : [];
  while (files.length < targetCount) {
    const fileIndex = foldersFileIndex(folderIndex, files.length);
    files.push(fileItem(`forte-${fileIndex.toString(16).padStart(16, "0")}`, folderId, `办公资料 ${folderIndex + 1}-${files.length + 1}.txt`, seed?.display_label ?? `业务目录 ${folderIndex + 1}`, "TXT", "text"));
  }
  return {
    folder_id: folderId,
    display_label: seed?.display_label ?? `业务目录 ${folderIndex + 1}`,
    display_summary: seed?.display_summary ?? "公开办公输入资料",
    availability: "local_input_bundle",
    external_dependency_label: null,
    file_count: files.length,
    total_bytes: files.reduce((total, file) => total + file.size, 0),
    files,
  };
});

function foldersFileIndex(folderIndex: number, fileIndex: number) { return 10_000 + folderIndex * 100 + fileIndex; }

const workspace = {
  workspace_id: "forte-public-office",
  title: "FORTE 公开办公资料库",
  dataset_label: "公开办公基准数据 · FORTE",
  dataset_version: "固定版本 · 345c1ec",
  source_label: "AGI-Eval-Official/FORTE 公开 demo inputs",
  license: "Apache-2.0",
  data_boundary: "只读访问清单内公开输入文件；不连接真实企业系统。",
  file_count: folders.reduce((total, folder) => total + folder.files.length, 0),
  folder_count: folders.length,
  previewable_file_count: folders.reduce((total, folder) => total + folder.files.length, 0),
  folders,
};

function previewFor(fileRef: string) {
  const file = folders.flatMap((folder) => folder.files).find((item) => item.file_ref === fileRef)!;
  const base = {
    workspace_id: "forte-public-office",
    file_ref: file.file_ref,
    folder_id: file.folder_id,
    display_label: file.display_label,
    display_group: file.display_group,
    display_path: file.display_path,
    display_summary: file.display_summary,
    mime: file.mime,
    size: file.size,
    sheet_name: null,
    columns: [] as string[],
    rows: [] as { row_number: number; values: string[] }[],
    total_rows: null as number | null,
    text: null as string | null,
    page_count: null as number | null,
    truncated: false,
    security: {
      integrity_verified: true,
      read_only: true,
      active_content_executed: false,
      external_resources_loaded: false,
      notes: ["清单、大小与 SHA-256 已在服务端核对", "没有执行宏、脚本或外部资源"],
    },
  };
  if (fileRef === csvFile.file_ref) return { ...base, kind: "table", columns: ["客商", "方向", "期末余额"], rows: [{ row_number: 2, values: ["星海科技", "借", "1500000"] }], total_rows: 30 };
  if (fileRef === pdfFile.file_ref) return { ...base, kind: "pdf", text: "授权范围：仅限本项目合同审阅。", page_count: 2 };
  if (fileRef === docxFile.file_ref) return { ...base, kind: "document", text: "岗位职责：负责商户拓展与经营分析。" };
  return { ...base, kind: "text", text: "2026-08-24 09:30 service healthy" };
}

function plan(selectedRefs: string[]) {
  return { summary: "先读取所选资料，再核对事实并形成带引用的结果。", units: [
    { unit_id: "read", title: "读取所选资料", objective: "读取用户选择的公开文件。", input_file_refs: selectedRefs, depends_on: [], tool: "file.read", requires_human_gate: false, side_effect: "none", artifact_name: null, artifact_type: null },
    { unit_id: "answer", title: "形成分析结果", objective: "回答用户问题并标注文件依据。", input_file_refs: selectedRefs, depends_on: ["read"], tool: "artifact.write", requires_human_gate: false, side_effect: "run_workspace_write", artifact_name: "analysis-result", artifact_type: "analysis" },
  ] };
}

function snapshot(
  body: { workspace_id: string; instruction: string; selected_file_refs: string[] },
  status: "queued" | "planning" | "paused" | "completed" | "stopped" | "failed" = "completed",
  sequence = 16,
) {
  const selected = folders.flatMap((folder) => folder.files).filter((file) => body.selected_file_refs.includes(file.file_ref));
  const failed = status === "failed";
  const terminal = ["completed", "stopped", "failed"].includes(status);
  const firstRefs = body.selected_file_refs.slice(0, Math.max(1, Math.ceil(body.selected_file_refs.length / 2)));
  const secondRefs = body.selected_file_refs.slice(firstRefs.length);
  const finding = (refs: string[], title: string) => ({
    summary: `${title}：已形成带文件引用的只读结论。`,
    findings: [{ title, detail: "该结论只来自本轮实际读取的公开文件。", file_refs: refs }],
    follow_ups: ["请业务人员复核结论口径"],
    review_required: true,
  });
  const gap = secondRefs.length ? [{
    gap_id: "gap-111111111111",
    label: `仍有 ${secondRefs.length} 份允许资料缺少可核对引用`,
    detail: "这些资料仍在用户划定范围内，需要下一轮继续核对。",
    candidate_file_refs: secondRefs,
  }] : [];
  const roundOne = {
    round_number: 1,
    status: status === "planning" || status === "paused" ? "running" : "completed",
    phase: status === "planning" || status === "paused" ? "plan" : "evidence_gate",
    question: body.instruction,
    steer_instruction: null,
    input_file_refs: firstRefs,
    plan: plan(firstRefs),
    model_receipt: { called: true, model: "deepseek-v4-pro", elapsed_ms: 1350, output_used: true },
    result: status === "planning" || status === "paused" ? null : finding(firstRefs, "第一轮核对完成"),
    analysis_receipt: status === "planning" || status === "paused" ? null : { called: true, model: "deepseek-v4-pro", elapsed_ms: 2180, output_used: true },
    verified_file_refs: status === "planning" || status === "paused" ? [] : firstRefs,
    evidence_gaps: status === "planning" || status === "paused" ? [] : gap,
    next_step: status === "planning" || status === "paused" ? null : {
      decision: secondRefs.length ? "next_round" : "completed",
      reason: secondRefs.length ? "仍有允许资料未形成引用，预算允许继续一轮。" : "完成条件已满足。",
      next_question: secondRefs.length ? "继续补齐尚未核对的证据。" : null,
      candidate_file_refs: secondRefs,
    },
    started_at: new Date().toISOString(),
    completed_at: status === "planning" || status === "paused" ? null : new Date().toISOString(),
  };
  const roundTwo = secondRefs.length && status === "completed" ? {
    round_number: 2,
    status: "completed",
    phase: "evidence_gate",
    question: "继续补齐尚未核对的证据。",
    steer_instruction: null,
    input_file_refs: secondRefs,
    plan: plan(secondRefs),
    model_receipt: { called: true, model: "deepseek-v4-pro", elapsed_ms: 1120, output_used: true },
    result: finding(secondRefs, "第二轮补证完成"),
    analysis_receipt: { called: true, model: "deepseek-v4-pro", elapsed_ms: 1760, output_used: true },
    verified_file_refs: secondRefs,
    evidence_gaps: [],
    next_step: { decision: "completed", reason: "允许范围内的文件均已形成可核对引用。", next_question: null, candidate_file_refs: [] },
    started_at: new Date().toISOString(),
    completed_at: new Date().toISOString(),
  } : null;
  const rounds = status === "queued" || failed ? [] : [roundOne, ...(roundTwo ? [roundTwo] : [])];
  const allFindings = status === "completed"
    ? [finding(firstRefs, "第一轮核对完成").findings[0], ...(secondRefs.length ? [finding(secondRefs, "第二轮补证完成").findings[0]] : [])]
    : [];
  return {
    run_id: "harness:workspace-run",
    owner_id: "demo_user",
    workspace_id: "forte-public-office",
    status,
    version: status === "queued" ? 1 : sequence + 1,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    last_event_sequence: status === "queued" ? 0 : sequence,
    instruction: body.instruction,
    instruction_source: "user",
    source_documents: status === "queued" ? [] : selected.map(({ file_ref, display_label, display_group, display_summary }) => ({ file_ref, display_label, display_group, display_summary })),
    selection_reason: `用户划定了 ${selected.length} 份公开文件`,
    contract: {
      contract_version: "agent-control-loop.v1",
      goal: body.instruction,
      allowed_file_refs: body.selected_file_refs,
      completion_criteria: ["所有结论都有文件引用", "剩余缺口和停止原因可见"],
      max_rounds: 3,
      max_files_per_round: 4,
      max_model_calls: 6,
      deadline_seconds: 120,
      external_action: "none",
    },
    budget: {
      max_rounds: 3,
      max_files_per_round: 4,
      max_model_calls: 6,
      deadline_seconds: 120,
      rounds_used: rounds.length,
      files_verified: status === "completed" ? body.selected_file_refs.length : status === "planning" || status === "paused" ? 0 : firstRefs.length,
      model_calls_used: status === "completed" ? rounds.length * 2 : status === "planning" || status === "paused" ? 1 : 0,
      elapsed_ms: status === "completed" ? 6410 : 1550,
      stop_reason: status === "stopped" ? "用户在安全点停止" : null,
    },
    rounds,
    current_round: rounds.length,
    control_state: status === "paused" ? "paused" : status === "stopped" ? "stopped" : "running",
    control_events: [],
    brief: status === "completed" ? {
      outcome: "completed",
      summary: `Agent Control Loop 完成 ${rounds.length} 轮，只读核对了 ${body.selected_file_refs.length} 份允许资料；所有结论仍等待用户复核。`,
      verified_file_refs: body.selected_file_refs,
      unresolved_gaps: [],
      rounds_completed: rounds.length,
      external_action: "none",
    } : status === "stopped" ? {
      outcome: "user_stopped",
      summary: "用户已停止 Agent Control Loop，现有证据和缺口已经保留。",
      verified_file_refs: [],
      unresolved_gaps: gap,
      rounds_completed: 0,
      external_action: "none",
    } : null,
    plan: status === "queued" || failed ? null : plan(roundTwo ? secondRefs : firstRefs),
    model_receipt: status === "queued" ? null : { called: true, model: "deepseek-v4-pro", elapsed_ms: 1350, output_used: !failed },
    analysis_receipt: status === "completed" ? { called: true, model: "deepseek-v4-pro", elapsed_ms: 2180, output_used: true } : null,
    result: status === "completed" ? {
      summary: `Agent Control Loop 完成 ${rounds.length} 轮，只读核对了允许资料。`,
      findings: allFindings,
      follow_ups: ["请业务人员复核长期未变的原因"],
      review_required: true,
    } : null,
    validation_errors: failed ? ["规划使用了当前任务范围外的资料或能力，系统已安全停止。请重新规划。"] : [],
    events: status === "queued" ? [] : [{ sequence, event_name: failed ? "harness_failed" : status === "completed" ? "loop_committed" : status === "stopped" ? "loop_stopped" : "round_started", occurred_at: new Date().toISOString(), status, message: failed ? "本轮未通过服务端校验，已停止且未发生外部动作。" : "服务端状态已更新。", details: {} }],
  };
}
async function fulfillJson(route: Route, body: unknown, status = 200) { await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) }); }

async function mockHarness(page: Page, options: { failFirstStart?: boolean; disconnect?: boolean; failed?: boolean; workspaceFailures?: number; interactiveLoop?: boolean } = {}) {
  let workspaceCalls = 0; let startCalls = 0; let streamCalls = 0;
  let currentBody = { workspace_id: "forte-public-office", instruction: "", selected_file_refs: [csvFile.file_ref] };
  let currentSnapshot = snapshot(currentBody, "queued");
  let controlSequence = 2;
  const starts: (typeof currentBody & { idempotency_key: string })[] = [];
  const controls: { command: string; instruction?: string; idempotency_key: string; expected_version: number }[] = [];
  const streams: string[] = [];
  await page.route("**/v1/**", async (route) => {
    const url = new URL(route.request().url()); const path = url.pathname;
    if (path === "/v1/health") return fulfillJson(route, { status: "ok" });
    if (path === "/v1/harness/workspace") {
      workspaceCalls += 1;
      if (workspaceCalls <= (options.workspaceFailures ?? 0)) return fulfillJson(route, { detail: "temporary" }, 503);
      return fulfillJson(route, workspace);
    }
    if (path.startsWith("/v1/harness/workspace/files/")) return fulfillJson(route, previewFor(path.split("/").at(-1)!));
    if (path === "/v1/harness/runs" && route.request().method() === "POST") {
      startCalls += 1;
      const body = route.request().postDataJSON() as typeof currentBody & { idempotency_key: string };
      currentBody = body; starts.push(body);
      if (options.failFirstStart && startCalls === 1) return fulfillJson(route, { detail: "任务启动结果未知" }, 503);
      currentSnapshot = snapshot(body, options.interactiveLoop ? "planning" : "queued", options.interactiveLoop ? controlSequence : 16);
      return fulfillJson(route, { run: currentSnapshot, replayed: startCalls > 1 }, 202);
    }
    if (path.endsWith("/controls") && route.request().method() === "POST") {
      const control = route.request().postDataJSON() as { command: "pause" | "resume" | "steer" | "stop"; instruction?: string; idempotency_key: string; expected_version: number };
      controls.push(control);
      const command = control.command;
      controlSequence += 1;
      currentSnapshot = snapshot(
        currentBody,
        command === "pause" ? "paused" : command === "stop" ? "stopped" : command === "resume" ? "completed" : "planning",
        command === "resume" ? 16 : controlSequence,
      );
      return fulfillJson(route, { run: currentSnapshot, replayed: false }, 202);
    }
    if (path.endsWith("/events")) {
      streamCalls += 1; streams.push(url.toString());
      const after = Number(url.searchParams.get("after") ?? "0");
      const all = ["workspace_index", "round_started", "planning_started", "planning_completed", "plan_validation", "analysis_started", "analysis_completed", "result_validation", "evidence_gate", "round_started", "planning_started", "planning_completed", "analysis_started", "analysis_completed", "evidence_gate", options.failed ? "harness_failed" : "loop_committed"];
      if (options.interactiveLoop) {
        const sequence = Math.max(after + 1, currentSnapshot.last_event_sequence);
        const terminalEvent = currentSnapshot.status === "completed" ? "loop_committed" : currentSnapshot.status === "stopped" ? "loop_stopped" : "round_started";
        const body = `id: ${sequence}\nevent: ${terminalEvent}\ndata: ${JSON.stringify({ sequence, event_name: terminalEvent, occurred_at: new Date().toISOString(), message: "服务端状态已更新。" })}\n\n`;
        return route.fulfill({ status: 200, contentType: "text/event-stream", body });
      }
      const eventNames = options.disconnect && streamCalls === 1 ? ["workspace_index"] : all.slice(after);
      const body = eventNames.map((eventName, index) => {
        const sequence = after + index + 1;
        return `id: ${sequence}\nevent: ${eventName}\ndata: ${JSON.stringify({ sequence, event_name: eventName, occurred_at: new Date().toISOString(), message: eventName === "harness_failed" ? "本轮未通过服务端校验。" : "服务端状态已更新。" })}\n\n`;
      }).join("");
      return route.fulfill({ status: 200, contentType: "text/event-stream", body });
    }
    if (path.startsWith("/v1/harness/runs/")) {
      if (options.disconnect && streamCalls === 1) return fulfillJson(route, { ...snapshot(currentBody, "queued"), status: "indexing", last_event_sequence: 1, version: 2 });
      if (options.interactiveLoop) return fulfillJson(route, currentSnapshot);
      return fulfillJson(route, snapshot(currentBody, options.failed ? "failed" : "completed"));
    }
    return fulfillJson(route, { detail: "not found" }, 404);
  });
  return { starts, controls, streams, get startCalls() { return startCalls; }, get streamCalls() { return streamCalls; } };
}

async function selectFile(page: Page, folder: string, file: string) {
  const folderButton = page.getByRole("button", { name: new RegExp(folder) }).first();
  if (await folderButton.getAttribute("aria-expanded") !== "true") await folderButton.click();
  const row = page.locator(".dataset-files > div").filter({ hasText: file });
  if (!(await row.locator("input[type=checkbox]").isChecked())) await row.locator("label").click();
  await row.getByRole("button", { name: new RegExp(file) }).click();
}

test("shows one complete folder workspace instead of registered scenarios", async ({ page }) => {
  await mockHarness(page); await page.goto("/");
  await expect(page.getByRole("heading", { name: "办公资料库" })).toBeVisible();
  await expect(page.locator(".workspace-facts")).toContainText("15 个业务目录");
  await expect(page.locator(".workspace-facts")).toContainText("96 份可安全预览");
  await expect(page.getByText("星海科技")).toBeVisible();
  const body = await page.locator("body").innerText();
  expect(body).not.toMatch(/注册场景|Demo\s*[123]|scenario_id|task_instruction|sha256/i);
});

test("previews CSV, PDF, DOCX and TXT with security facts", async ({ page }) => {
  await mockHarness(page); await page.goto("/");
  await expect(page.getByText("星海科技")).toBeVisible();
  await selectFile(page, "法务", pdfFile.display_label);
  await expect(page.getByText("授权范围：仅限本项目合同审阅。")).toBeVisible();
  await selectFile(page, "人力招聘", docxFile.display_label);
  await expect(page.getByText("岗位职责：负责商户拓展与经营分析。")).toBeVisible();
  await selectFile(page, "可靠性工程", txtFile.display_label);
  await expect(page.getByText("service healthy")).toBeVisible();
  await expect(page.getByText("安全预览", { exact: true })).toBeVisible();
  await expect(page.getByText(/没有执行宏、脚本或外部资源/)).toBeVisible();
});

test("runs an arbitrary task over files selected across folders", async ({ page }) => {
  const state = await mockHarness(page); await page.goto("/");
  await selectFile(page, "财务管理", csvFile.display_label);
  await selectFile(page, "法务", pdfFile.display_label);
  const instruction = "比较财务往来与授权材料，列出需要人工复核的事实。";
  await page.getByRole("textbox", { name: "任务指令" }).fill(instruction);
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await expect.poll(() => state.starts.length).toBe(1);
  expect(state.starts[0]).toMatchObject({
    workspace_id: "forte-public-office",
    instruction,
    selected_file_refs: [csvFile.file_ref, pdfFile.file_ref],
    loop: { max_rounds: 3, max_files_per_round: 4, max_model_calls: 6, deadline_seconds: 120 },
  });
  await expect(page.getByText("规划模型")).toBeVisible();
  await expect(page.getByText("分析模型")).toBeVisible();
  await expect(page.locator(".loop-view").getByRole("heading", { name: instruction })).toBeVisible();
  await page.getByRole("button", { name: /第 1 轮/ }).click();
  await expect(page.getByText("证据缺口")).toBeVisible();
  await expect(page.locator(".loop-round-detail > footer strong")).toHaveText("继续下一轮");
  await page.getByRole("button", { name: /任务简报/ }).click();
  await expect(page.getByRole("heading", { name: /完成 2 轮/ })).toBeVisible();
  expect(await page.locator("body").innerText()).not.toContain("forte-");
});

test("pauses, steers and resumes the same Agent Control Loop from server receipts", async ({ page }) => {
  const state = await mockHarness(page, { interactiveLoop: true }); await page.goto("/");
  await selectFile(page, "财务管理", csvFile.display_label);
  await selectFile(page, "法务", pdfFile.display_label);
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对所选资料，并在证据不足时继续下一轮。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await expect(page.locator(".loop-view")).toContainText("第 1 轮");
  await expect(page.getByRole("button", { name: "当前 Loop 运行中" })).toBeDisabled();
  await expect(page.getByRole("textbox", { name: "任务指令" })).toBeDisabled();
  await expect(page.locator(".dataset-files input[type=checkbox]:checked").first()).toBeDisabled();

  await page.getByLabel("调整下一轮方向").fill("下一轮优先核对授权范围");
  await page.locator(".loop-controls form").getByRole("button", { name: "记录" }).click();
  await expect.poll(() => state.controls.some((control) => control.command === "steer" && control.instruction === "下一轮优先核对授权范围")).toBeTruthy();

  await page.locator(".loop-control-actions").getByRole("button", { name: "暂停" }).click();
  await expect(page.getByText("Loop 已暂停，现有轮次、引用和预算都已保留。")).toBeVisible();
  await expect.poll(() => state.controls.some((control) => control.command === "pause")).toBeTruthy();

  await page.locator(".loop-control-actions").getByRole("button", { name: "继续" }).click();
  await expect(page.locator(".loop-brief")).toContainText("完成 2 轮");
  await expect(page.locator(".loop-brief")).toContainText("外部动作：未发生");
  await expect(page.getByRole("button", { name: "启动 Control Loop" })).toBeEnabled();
  expect(state.controls.map((control) => control.command)).toEqual(["steer", "pause", "resume"]);
});

test("opens a cited source file from an analysis finding", async ({ page }) => {
  await mockHarness(page); await page.goto("/");
  await selectFile(page, "财务管理", csvFile.display_label);
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对余额并引用来源文件。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await page.getByRole("button", { name: /任务简报/ }).click();
  await page.getByRole("button", { name: csvFile.display_label }).last().click();
  await expect(page.getByText("星海科技")).toBeVisible();
  await expect(page.getByRole("button", { name: "文件预览" })).toHaveClass(/is-active/);
});

test("reuses the same command key when a start response is unknown", async ({ page }) => {
  const state = await mockHarness(page, { failFirstStart: true }); await page.goto("/");
  await selectFile(page, "财务管理", csvFile.display_label);
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对所选文件中的余额变化。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await expect(page.getByLabel("工作现场").getByText("任务启动结果未知")).toBeVisible();
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await expect.poll(() => state.starts.length).toBe(2);
  expect(state.starts[0].idempotency_key).toBe(state.starts[1].idempotency_key);
});

test("reconnects the event stream from the last observed sequence", async ({ page }) => {
  const state = await mockHarness(page, { disconnect: true }); await page.goto("/");
  await selectFile(page, "财务管理", csvFile.display_label);
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对所选文件中的余额变化。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await expect.poll(() => state.streamCalls).toBeGreaterThanOrEqual(2);
  expect(state.streams.some((url) => new URL(url).searchParams.get("after") === "1")).toBeTruthy();
});

test("explains an unavailable workspace and fails closed without a result", async ({ page }) => {
  await mockHarness(page, { workspaceFailures: 1, failed: true }); await page.goto("/");
  await expect(page.getByRole("heading", { name: "办公资料库暂时无法读取" })).toBeVisible();
  await page.getByRole("button", { name: "重新读取" }).click();
  await expect(page.getByRole("heading", { name: "办公资料库" })).toBeVisible();
  await selectFile(page, "财务管理", csvFile.display_label);
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对所选文件中的余额变化。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await expect(page.getByText("本轮已安全停止")).toBeVisible();
  await expect(page.locator("body")).not.toContainText(/artifact\.write|run_workspace_write/);
});

test("mobile keeps folder browsing, task input, preview and trajectory usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 }); await mockHarness(page); await page.goto("/");
  await expect(page.getByRole("heading", { name: "办公资料库" })).toBeVisible();
  const metrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(metrics.scroll).toBeLessThanOrEqual(metrics.viewport);
  await expect(page.getByRole("textbox", { name: "任务指令" })).toBeVisible();
  await expect(page.locator(".table-preview")).toBeVisible();
  const shortControls = await page.locator("button:visible, summary:visible").evaluateAll((nodes) => nodes.filter((node) => (node as HTMLElement).getBoundingClientRect().height < 44).map((node) => ({ text: node.textContent, height: (node as HTMLElement).getBoundingClientRect().height })));
  expect(shortControls).toEqual([]);
});
