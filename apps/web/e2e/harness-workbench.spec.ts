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
const pdfFile = fileItem("forte-2222222222222222", "forte-folder-222222222222", "授权委托书.pdf", "法务", "PDF", "pdf", "合同与授权/授权委托书.pdf");
const docxFile = fileItem("forte-3333333333333333", "forte-folder-333333333333", "岗位说明.docx", "人力招聘", "DOCX", "document");
const txtFile = fileItem("forte-4444444444444444", "forte-folder-444444444444", "运行日志.txt", "可靠性工程", "TXT", "text");
const workflowFile = fileItem("forte-5555555555555555", "forte-folder-555555555555", "workflow.py", "算法研发", "PY", "text", "search_agent_workflow/workflow.py");
const searchLogFile = fileItem("forte-6666666666666666", "forte-folder-555555555555", "search_agent.log", "算法研发", "LOG", "text", "search_agent_workflow/search_agent.log");

function fileItem(fileRef: string, folderId: string, label: string, group: string, extension: FileItem["extension"], kind: FileItem["preview_kind"], nestedPath?: string): FileItem {
  return {
    file_ref: fileRef,
    folder_id: folderId,
    display_label: label,
    display_group: group,
    display_path: `${group}/${nestedPath ?? label}`,
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
  { folder_id: workflowFile.folder_id, display_label: "算法研发", display_summary: "搜索 Agent 代码与运行记录", files: [workflowFile, searchLogFile] },
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
  if (fileRef === workflowFile.file_ref) return { ...base, kind: "text", text: "AI 搜索 Agent - Workflow 核心模块\n\nclass QueryAnalysisNode:\n    intent = llm.classify(query)\n    rewritten = llm.rewrite(query)\n    drift_score = semantic_drift(query, rewritten)\n\nclass SearchPlanNode:\n    route = choose(intent, rewritten)\n    if intent == 'news':\n        route.append('web_search_news')\n\nclass FallbackPlanNode:\n    route = choose(intent, rewritten)" };
  if (fileRef === searchLogFile.file_ref) return { ...base, kind: "text", text: "2026-08-24 request=Breaking news about AI regulation today\nintent=factual\nrewrite=detailed explanation of AI regulation\nroute=web_search+knowledge_base\nweb_search_news_called=false" };
  return { ...base, kind: "text", text: "2026-08-24 09:30 service healthy" };
}

function plan(fileRefs: string[]) {
  return { summary: "先从整个资料库索引中选择相关资料，再核对事实并形成带引用的结果。", selection_reason: "文件名与摘要直接涉及当前目标，先读取这些最小证据。", units: [
    { unit_id: "read", title: "读取相关资料", objective: "读取 Agent 从整个资料库自主选择的公开文件。", input_file_refs: fileRefs, depends_on: [], tool: "file.read", requires_human_gate: false, side_effect: "none", artifact_name: null, artifact_type: null },
    { unit_id: "answer", title: "形成分析结果", objective: "回答用户问题并标注文件依据。", input_file_refs: fileRefs, depends_on: ["read"], tool: "artifact.write", requires_human_gate: false, side_effect: "run_workspace_write", artifact_name: "analysis-result", artifact_type: "analysis" },
  ] };
}

function snapshot(
  body: { workspace_id: string; instruction: string },
  status: "queued" | "planning" | "waiting_input" | "paused" | "completed" | "stopped" | "failed" = "completed",
  sequence = 16,
) {
  const allFiles = folders.flatMap((folder) => folder.files);
  const failed = status === "failed";
  const terminal = ["completed", "stopped", "failed"].includes(status);
  const firstRefs = [workflowFile.file_ref, searchLogFile.file_ref];
  const secondRefs = [pdfFile.file_ref];
  const selected = [workflowFile, searchLogFile, pdfFile];
  const roundOneReadBranch = "branch-111111111111";
  const roundOneAnswerBranch = "branch-222222222222";
  const roundTwoReadBranch = "branch-333333333333";
  const roundTwoAnswerBranch = "branch-444444444444";
  const finding = (refs: string[], title: string) => ({
    summary: `${title}：已形成带文件引用和精确位置的只读结论。`,
    findings: [{
      finding_id: title === "第一轮核对完成" ? "finding-111111111111" : "finding-222222222222",
      affected_branch_ids: title === "第一轮核对完成" ? [roundOneReadBranch] : [roundTwoAnswerBranch],
      title,
      detail: title === "第一轮核对完成" ? "设计要求新闻意图进入 web_search_news，但运行记录显示该请求被判为 factual，最终没有调用新闻搜索。" : "授权范围只覆盖本项目合同审阅。",
      fact_summary: title === "第一轮核对完成" ? "新闻类请求被识别为事实查询，专用新闻搜索没有被调用。" : "授权文件仅覆盖本项目合同审阅。",
      impact: title === "第一轮核对完成" ? "时效性查询可能使用不适合的检索路径，结果需要重新核对。" : "超出授权范围的后续动作不能直接推进。",
      file_refs: refs,
      evidence_anchors: title === "第一轮核对完成" ? [
        { file_ref: workflowFile.file_ref, role: "expected", label: "新闻意图应进入专用搜索", locator_kind: "text_lines", start: 8, end: 11, excerpt: "class SearchPlanNode:\n    route = choose(intent, rewritten)\n    if intent == 'news':\n        route.append('web_search_news')" },
        { file_ref: searchLogFile.file_ref, role: "observed", label: "实际没有调用新闻搜索", locator_kind: "text_lines", start: 2, end: 5, excerpt: "intent=factual\nrewrite=detailed explanation of AI regulation\nroute=web_search+knowledge_base\nweb_search_news_called=false" },
      ] : [
        { file_ref: pdfFile.file_ref, role: "support", label: "授权范围原文", locator_kind: "text_lines", start: 1, end: 1, excerpt: "授权范围：仅限本项目合同审阅。" },
      ],
      evidence_resolutions: [],
      review: title === "第一轮核对完成" ? {
        requires_human_decision: true,
        question: "下一步应按设计修正路由，还是先补充版本与运行证据？",
        why_human: "现有文件能证明设计与运行记录不一致，但不能替业务负责人决定修复优先级。",
        options: [
          { option_id: "A", label: "先核对版本", meaning: "先确认代码与日志来自同一版本，再决定是否修改。", agent_next_step: "核对代码版本、日志时间和发布记录，形成差异清单。", next_instruction: "核对 workflow.py 与 search_agent.log 是否来自同一代码版本，列出可唯一定位的版本与时间证据。", affected_branch_ids: [roundOneReadBranch], required_file_refs: refs, estimated_additional_rounds: 1, external_action: "none" },
          { option_id: "B", label: "按设计提修复建议", meaning: "暂以设计文件为准，先形成路由修复建议，但不直接改文件。", agent_next_step: "形成路由修改建议、影响范围和待验证项。", next_instruction: "以 workflow.py 的新闻路由设计为准，核对 search_agent.log 并形成只读修复建议与待验证清单。", affected_branch_ids: [roundOneReadBranch], required_file_refs: refs, estimated_additional_rounds: 1, external_action: "none" },
        ],
        recommended_option_id: "A",
        recommendation_reason: "先核对版本可以避免把跨版本差异误判为当前缺陷。",
        after_confirmation: "Agent 将把你的选择作为新任务目标，继续只读核对并形成可审查结果。",
      } : {
        requires_human_decision: false,
        question: "授权范围是否已被准确引用？",
        why_human: "这一步只需核对原文，不涉及业务口径选择。",
        options: [],
        recommended_option_id: null,
        recommendation_reason: "按原文复核即可。",
        after_confirmation: "复核通过后可再决定是否启动后续任务。",
      },
    }],
    follow_ups: ["继续核对授权范围与财务往来之间是否存在执行约束，并形成待办清单。"],
    review_required: true,
  });
  const gap = secondRefs.length ? [{
    gap_id: "gap-111111111111",
    branch_id: roundOneAnswerBranch,
    label: `仍有 ${secondRefs.length} 份本轮选择资料缺少可核对引用`,
    detail: "这些资料已由 Agent 纳入本轮证据范围，需要下一轮继续核对。",
    candidate_file_refs: secondRefs,
  }] : [];
  const roundOne = {
    round_number: 1,
    status: status === "planning" || status === "paused" ? "running" : "completed",
    phase: status === "planning" || status === "paused" ? "plan" : "evidence_gate",
    question: body.instruction,
    steer_instruction: null,
    input_file_refs: [...firstRefs, ...secondRefs],
    branch_ids: [roundOneReadBranch, roundOneAnswerBranch],
    plan: plan([...firstRefs, ...secondRefs]),
    model_receipt: { called: true, model: "deepseek-v4-pro", elapsed_ms: 1350, output_used: true },
    result: status === "planning" || status === "paused" ? null : finding(firstRefs, "第一轮核对完成"),
    analysis_receipt: status === "planning" || status === "paused" ? null : { called: true, model: "deepseek-v4-pro", elapsed_ms: 2180, output_used: true },
    verified_file_refs: status === "planning" || status === "paused" ? [] : firstRefs,
    evidence_gaps: status === "planning" || status === "paused" ? [] : gap,
    next_step: status === "planning" || status === "paused" ? null : {
      decision: secondRefs.length ? "waiting_input" : "completed",
      reason: secondRefs.length ? "本轮仍有已选择资料未形成引用，需要你确认是否继续使用下一轮预算。" : "完成条件已满足。",
      next_question: secondRefs.length ? "继续补齐尚未核对的证据。" : null,
      candidate_file_refs: secondRefs,
      candidate_branch_ids: [roundOneAnswerBranch],
      evidence_resolutions: [],
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
    branch_ids: [roundTwoReadBranch, roundTwoAnswerBranch],
    plan: plan(secondRefs),
    model_receipt: { called: true, model: "deepseek-v4-pro", elapsed_ms: 1120, output_used: true },
    result: finding(secondRefs, "第二轮补证完成"),
    analysis_receipt: { called: true, model: "deepseek-v4-pro", elapsed_ms: 1760, output_used: true },
    verified_file_refs: secondRefs,
    evidence_gaps: [],
    next_step: { decision: "completed", reason: "本轮自主选择的证据均已形成可核对引用。", next_question: null, candidate_file_refs: [], candidate_branch_ids: [], evidence_resolutions: [] },
    started_at: new Date().toISOString(),
    completed_at: new Date().toISOString(),
  } : null;
  const rounds = status === "queued" || failed ? [] : [roundOne, ...(roundTwo ? [roundTwo] : [])];
  const allFindings = status === "completed"
    ? [finding(firstRefs, "第一轮核对完成").findings[0], ...(secondRefs.length ? [finding(secondRefs, "第二轮补证完成").findings[0]] : [])]
    : [];
  const branchState = status === "planning" || status === "paused" ? "running" : status === "stopped" ? "stopped" : "completed";
  const branch = (branchId: string, unitId: string, roundNumber: number, title: string, refs: string[], branchStatus: string, parentBranchId: string | null, dependencies: string[] = []) => ({
    branch_id: branchId,
    unit_id: unitId,
    round_number: roundNumber,
    parent_branch_id: parentBranchId,
    title,
    objective: `核对“${title}”所需的公开办公资料。`,
    depends_on: dependencies,
    input_file_refs: refs,
    verified_file_refs: branchStatus === "completed" ? refs : [],
    missing_file_refs: branchStatus === "completed" ? [] : refs,
    status: branchStatus,
    requires_human_gate: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  });
  const branches = status === "queued" || failed ? [] : [
    branch(roundOneReadBranch, "read", 1, "读取相关资料", firstRefs, branchState === "running" ? "running" : "completed", null),
    branch(roundOneAnswerBranch, "answer", 1, "形成分析结果", secondRefs, status === "completed" ? "completed" : status === "waiting_input" ? "waiting_input" : branchState, null, [roundOneReadBranch]),
    ...(roundTwo ? [
      branch(roundTwoReadBranch, "read", 2, "继续读取缺口资料", secondRefs, "completed", roundOneAnswerBranch),
      branch(roundTwoAnswerBranch, "answer", 2, "补齐分支证据", secondRefs, "completed", roundOneAnswerBranch, [roundTwoReadBranch]),
    ] : []),
  ];
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
    source_documents: status === "queued" ? [] : allFiles.map(({ file_ref, display_label, display_group, display_summary }) => ({ file_ref, display_label, display_group, display_summary })),
    selection_reason: `已冻结整个资料库的 ${allFiles.length} 份文件索引，Agent 自主检索相关证据`,
    contract: {
      contract_version: "agent-control-loop.v1",
      goal: body.instruction,
      scope_mode: "whole_workspace",
      allowed_file_refs: allFiles.map((file) => file.file_ref),
      completion_criteria: ["所有结论都有文件引用", "剩余缺口和停止原因可见"],
      max_rounds: 3,
      max_files_per_round: 6,
      max_model_calls: 6,
      deadline_seconds: 1200,
      external_action: "none",
    },
    budget: {
      max_rounds: 3,
      max_files_per_round: 6,
      max_model_calls: 6,
      deadline_seconds: 1200,
      rounds_used: rounds.length,
      files_verified: status === "completed" ? selected.length : status === "planning" || status === "paused" ? 0 : firstRefs.length,
      model_calls_used: status === "completed" ? rounds.length * 2 : status === "planning" || status === "paused" ? 1 : 0,
      elapsed_ms: status === "completed" ? 6410 : 1550,
      stop_reason: status === "stopped" ? "用户在安全点停止" : null,
    },
    rounds,
    current_round: rounds.length,
    control_state: status === "paused" || status === "waiting_input" ? "paused" : status === "stopped" ? "stopped" : "running",
    control_events: [],
    decision_records: [],
    branches,
    active_branch_id: status === "waiting_input" || status === "completed" ? roundOneAnswerBranch : null,
    artifact_versions: rounds.map((round, index) => ({
      artifact_id: "artifact-111111111111",
      version: index + 1,
      title: "任务证据简报",
      kind: "evidence_brief",
      status: round.evidence_gaps.length ? "draft" : "verified",
      round_number: round.round_number,
      summary: round.result?.summary ?? "本轮成果正在形成。",
      findings: round.result?.findings ?? [],
      follow_ups: round.result?.follow_ups ?? [],
      evidence_gaps: round.evidence_gaps,
      source_file_refs: round.verified_file_refs,
      finding_count: round.result?.findings.length ?? 0,
      parent_version: index ? index : null,
      created_at: new Date().toISOString(),
      review_required: true,
      external_action: "none",
    })),
    commits: status === "completed" ? [{
      commit_id: "commit-111111111111",
      artifact_id: "artifact-111111111111",
      artifact_version: rounds.length,
      operation: "commit",
      parent_commit_id: null as string | null,
      summary: "已提交通过证据门的只读任务简报，仍需用户审阅。",
      committed_at: new Date().toISOString(),
      external_action: "none",
    }] : [],
    last_commit: status === "completed" ? {
      commit_id: "commit-111111111111",
      artifact_id: "artifact-111111111111",
      artifact_version: rounds.length,
      operation: "commit",
      parent_commit_id: null as string | null,
      summary: "已提交通过证据门的只读任务简报，仍需用户审阅。",
      committed_at: new Date().toISOString(),
      external_action: "none",
    } : null,
    brief: status === "completed" ? {
      outcome: "completed",
      summary: `Agent Control Loop 完成 ${rounds.length} 轮，从整个资料库中自主选择并只读核对了 ${selected.length} 份相关资料；已形成待用户确认的下一步建议。`,
      verified_file_refs: selected.map((file) => file.file_ref),
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
      follow_ups: ["继续核对授权范围与财务往来之间是否存在执行约束，并形成待办清单。"],
      review_required: true,
    } : null,
    validation_errors: failed ? ["规划使用了当前任务范围外的资料或能力，系统已安全停止。请重新规划。"] : [],
    events: status === "queued" ? [] : [{ sequence, event_name: failed ? "harness_failed" : status === "completed" ? "loop_committed" : status === "stopped" ? "loop_stopped" : status === "waiting_input" ? "evidence_gate" : "round_started", occurred_at: new Date().toISOString(), status, message: failed ? "本轮未通过服务端校验，已停止且未发生外部动作。" : "服务端状态已更新。", details: {} }],
  };
}

function sourceLocationRecoverySnapshot(body: { workspace_id: string; instruction: string }, candidateCount = 2) {
  const base = snapshot(body, "waiting_input", 12);
  const branches = base.branches.map((branch) => ({
    ...branch,
    status: "waiting_input",
    verified_file_refs: [],
    missing_file_refs: branch.input_file_refs,
  }));
  const gaps = branches.map((branch, index) => ({
    gap_id: `gap-${String(index + 1).padStart(12, "0")}`,
    branch_id: branch.branch_id,
    label: `“${branch.title}”分支的原文尚未唯一定位`,
    detail: "模型已返回候选内容，但服务端不能把引用唯一匹配到安全预览。",
    candidate_file_refs: branch.missing_file_refs,
  }));
  const round = {
    ...base.rounds[0],
    status: "completed",
    phase: "evidence_gate",
    result: null,
    analysis_receipt: { called: true, model: "deepseek-v4-pro", elapsed_ms: 2230, output_used: false },
    verified_file_refs: [],
    evidence_gaps: gaps,
    next_step: {
      decision: "waiting_input",
      reason: "模型已返回候选结论，但服务端无法把原文片段唯一定位到安全预览。本轮计划、文件范围和模型调用记录已保留；请缩小到一个分支后继续。",
      next_question: "只核对所选分支，用更长且唯一的原文定位关键事实。",
      candidate_file_refs: branches.flatMap((branch) => branch.missing_file_refs),
      candidate_branch_ids: branches.map((branch) => branch.branch_id),
      recovery_kind: "source_location",
      evidence_resolutions: [{
        resolution_id: "resolution-111111111111",
        finding_id: "finding-333333333333",
        finding_title: "新闻路由候选原文位置不唯一",
        fact_summary: "Agent 引用的 route = choose 语句在同一文件出现两次。",
        impact: "服务端不能确定 Agent 指的是主路由还是回退路由。",
        branch_id: branches[0].branch_id,
        file_ref: workflowFile.file_ref,
        role: "contradiction",
        label: "路由选择语句",
        query_excerpt: "route = choose(intent, rewritten)",
        status: "ambiguous",
        reason: `同一片段在安全预览中匹配到 ${candidateCount} 个位置，服务端不能替用户选择。`,
        source_revision: "rev-20260827-a",
        candidates: [
          { candidate_id: "candidate-111111111111", file_ref: workflowFile.file_ref, locator_kind: "text_lines", start: 9, end: 9, excerpt: "route = choose(intent, rewritten)", source_revision: "rev-20260827-a", context_before: "# 主路由", context_after: "return route" },
          { candidate_id: "candidate-222222222222", file_ref: workflowFile.file_ref, locator_kind: "text_lines", start: 14, end: 14, excerpt: "route = choose(intent, rewritten)", source_revision: "rev-20260827-a", context_before: "# 回退路由", context_after: "return fallback" },
          ...(candidateCount >= 3 ? [{ candidate_id: "candidate-333333333333", file_ref: workflowFile.file_ref, locator_kind: "text_lines", start: 19, end: 19, excerpt: "route = choose(intent, rewritten)", source_revision: "rev-20260827-a", context_before: "# 兼容路由", context_after: "return compat" }] : []),
        ],
        selected_candidate_id: null,
      }],
      decision_requests: [{
        decision_request_id: "request-111111111111",
        finding_id: "finding-333333333333",
        resolution_id: "resolution-111111111111",
        branch_id: branches[0].branch_id,
        source_revision: "rev-20260827-a",
        expected_version: 13,
        idempotency_ref: "idem-111111",
        candidate_ids: ["candidate-111111111111", "candidate-222222222222", ...(candidateCount >= 3 ? ["candidate-333333333333"] : [])],
        consequence: "只重跑受影响分支，不修改源文件，不执行外部动作。",
        state: "pending",
      }],
    },
  };
  return {
    ...base,
    version: 13,
    last_event_sequence: 12,
    budget: { ...base.budget, rounds_used: 1, files_verified: 0, model_calls_used: 3, elapsed_ms: 6100 },
    rounds: [round],
    current_round: 1,
    branches,
    active_branch_id: null,
    artifact_versions: [{ ...base.artifact_versions[0], summary: round.next_step.reason, findings: [], follow_ups: [], evidence_gaps: gaps, source_file_refs: [], finding_count: 0 }],
    analysis_receipt: round.analysis_receipt,
    result: null,
    validation_errors: [],
    events: [
      { sequence: 10, event_name: "analysis_validation_rejected", occurred_at: new Date().toISOString(), status: "analyzing", message: "修复后的候选结论仍无法唯一定位原文，未采用。", details: {} },
      { sequence: 11, event_name: "analysis_recovery_required", occurred_at: new Date().toISOString(), status: "analyzing", message: round.next_step.reason, details: {} },
      { sequence: 12, event_name: "evidence_gate", occurred_at: new Date().toISOString(), status: "waiting_input", message: round.next_step.reason, details: {} },
    ],
  };
}

function boundedAnalysisRecoverySnapshot(body: { workspace_id: string; instruction: string }) {
  const base = sourceLocationRecoverySnapshot(body);
  const branches = base.branches.map((branch) => ({ ...branch, status: "stopped" }));
  const gaps = branches.map((branch, index) => ({
    gap_id: `gap-bounded-${String(index + 1).padStart(7, "0")}`,
    branch_id: branch.branch_id,
    label: `“${branch.title}”分支仍缺少可核对结果`,
    detail: `该分支还有 ${branch.missing_file_refs.length} 份已选资料没有进入通过服务端核对的结论。`,
    candidate_file_refs: branch.missing_file_refs,
  }));
  const reason = "分析模型已经响应，但返回内容仍未形成可核对结构；当前预算不足以再次核对，系统已保留计划与调用记录并安全停止。";
  const round = {
    ...base.rounds[0],
    evidence_gaps: gaps,
    next_step: {
      decision: "budget_exhausted",
      reason,
      next_question: null,
      candidate_file_refs: branches.flatMap((branch) => branch.missing_file_refs),
      candidate_branch_ids: branches.map((branch) => branch.branch_id),
      recovery_kind: "analysis_output",
      evidence_resolutions: [],
    },
  };
  return {
    ...base,
    status: "stopped",
    control_state: "stopped",
    version: 15,
    last_event_sequence: 14,
    budget: { ...base.budget, stop_reason: "Agent 执行时间预算已耗尽" },
    rounds: [round],
    branches,
    artifact_versions: [{ ...base.artifact_versions[0], summary: reason, evidence_gaps: gaps }],
    brief: {
      outcome: "bounded",
      summary: `Agent Control Loop 到达预算边界；仍有 ${gaps.length} 条分支需要后续处理。`,
      verified_file_refs: [],
      unresolved_gaps: gaps,
      rounds_completed: 1,
      external_action: "none",
    },
    events: [
      { sequence: 12, event_name: "analysis_recovery_required", occurred_at: new Date().toISOString(), status: "analyzing", message: reason, details: {} },
      { sequence: 13, event_name: "evidence_gate", occurred_at: new Date().toISOString(), status: "verifying", message: reason, details: { recovery_kind: "analysis_output" } },
      { sequence: 14, event_name: "loop_budget_stopped", occurred_at: new Date().toISOString(), status: "stopped", message: "Agent Control Loop 已在预算边界停止，并保留未完成项。", details: { outcome: "bounded", external_action: false } },
    ],
  };
}

function locationFailureSnapshot(body: { workspace_id: string; instruction: string }) {
  const base = sourceLocationRecoverySnapshot(body);
  return {
    ...base,
    status: "failed",
    control_state: "running",
    rounds: base.rounds.map((round) => ({ ...round, status: "failed", next_step: null })),
    branches: base.branches.map((branch) => ({ ...branch, status: "failed" })),
    artifact_versions: [],
    validation_errors: ["本轮未通过服务端安全校验，且未发生外部动作。请重新运行。"],
    events: [
      { sequence: 11, event_name: "analysis_validation_rejected", occurred_at: new Date().toISOString(), status: "analyzing", message: "修复后的候选结论仍无法唯一定位原文，未采用。", details: {} },
      { sequence: 12, event_name: "harness_failed", occurred_at: new Date().toISOString(), status: "failed", message: "本轮未通过服务端校验，已停止且未发生外部动作。", details: {} },
    ],
  };
}
async function fulfillJson(route: Route, body: unknown, status = 200) { await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) }); }

async function mockHarness(page: Page, options: { failFirstStart?: boolean; disconnect?: boolean; failed?: boolean; locationFailure?: boolean; sourceRecovery?: boolean; sourceRecoveryThreeCandidates?: boolean; boundedRecovery?: boolean; workspaceFailures?: number; interactiveLoop?: boolean; evidenceGate?: boolean } = {}) {
  let workspaceCalls = 0; let startCalls = 0; let streamCalls = 0;
  let currentBody = { workspace_id: "forte-public-office", instruction: "" };
  // Mock snapshots intentionally cover several server state shapes in one route.
  let currentSnapshot: any = snapshot(currentBody, "queued");
  let controlSequence = 2;
  const starts: (typeof currentBody & { idempotency_key: string })[] = [];
  const controls: { command: string; instruction?: string; branch_id?: string; artifact_version?: number; decision_action?: string; finding_id?: string; resolution_id?: string; selected_option_id?: string; selected_candidate_id?: string; decision_request_id?: string; source_revision?: string; feedback?: string; idempotency_key: string; expected_version: number }[] = [];
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
    if (path === "/v1/harness/runs" && route.request().method() === "GET") {
      return fulfillJson(route, { runs: [] });
    }
    if (path === "/v1/harness/runs" && route.request().method() === "POST") {
      startCalls += 1;
      const body = route.request().postDataJSON() as typeof currentBody & { idempotency_key: string };
      currentBody = body; starts.push(body);
      if (options.failFirstStart && startCalls === 1) return fulfillJson(route, { detail: "任务启动结果未知" }, 503);
      currentSnapshot = options.locationFailure
        ? locationFailureSnapshot(body)
        : options.boundedRecovery
          ? boundedAnalysisRecoverySnapshot(body)
        : options.sourceRecovery
          ? sourceLocationRecoverySnapshot(body, options.sourceRecoveryThreeCandidates ? 3 : 2)
          : snapshot(body, options.evidenceGate ? "waiting_input" : options.interactiveLoop ? "planning" : "queued", options.interactiveLoop || options.evidenceGate ? controlSequence : 16);
      controlSequence = Math.max(controlSequence, currentSnapshot.last_event_sequence);
      return fulfillJson(route, { run: currentSnapshot, replayed: startCalls > 1 }, 202);
    }
    if (path.endsWith("/controls") && route.request().method() === "POST") {
      const control = route.request().postDataJSON() as { command: "pause" | "resume" | "steer" | "stop" | "rollback" | "decision"; instruction?: string; branch_id?: string; artifact_version?: number; decision_action?: "accept" | "decline" | "defer" | "cancel"; finding_id?: string; resolution_id?: string; selected_option_id?: string; selected_candidate_id?: string; decision_request_id?: string; source_revision?: string; feedback?: string; idempotency_key: string; expected_version: number };
      controls.push(control);
      const command = control.command;
      controlSequence = Math.max(controlSequence + 1, currentSnapshot.last_event_sequence + 1);
      if (command === "decision") {
        const record = {
          decision_id: `decision-${String(controls.length).padStart(12, "0")}`,
          action: control.decision_action ?? "defer",
          finding_id: control.finding_id ?? "finding-111111111111",
          resolution_id: control.resolution_id ?? null,
          branch_id: control.branch_id ?? null,
          selected_option_id: control.selected_option_id ?? null,
          selected_candidate_id: control.selected_candidate_id ?? null,
          feedback: control.feedback ?? null,
          idempotency_ref: "idem-111111",
          recorded_at: new Date().toISOString(),
          accepted_task_version: control.expected_version + 1,
          external_action: "none",
        };
        currentSnapshot = {
          ...currentSnapshot,
          version: control.expected_version + 1,
          last_event_sequence: controlSequence,
          decision_records: [...currentSnapshot.decision_records, record],
          events: [...currentSnapshot.events, { sequence: controlSequence, event_name: "decision_recorded", occurred_at: new Date().toISOString(), status: currentSnapshot.status, message: "人工决定已写入版本化回执；尚未发生外部动作。", details: {} }],
        };
        return fulfillJson(route, { run: currentSnapshot, replayed: false }, 202);
      }
      if (command === "rollback") {
        const completed = snapshot(currentBody, "completed", control.expected_version);
        const targetVersion = control.artifact_version ?? 1;
        const target = completed.artifact_versions.find((item) => item.version === targetVersion)!;
        const rollbackCommit = {
          commit_id: `commit-rollback-${targetVersion}`,
          artifact_id: target.artifact_id,
          artifact_version: targetVersion,
          operation: "rollback",
          parent_commit_id: completed.last_commit?.commit_id ?? null,
          summary: `已将当前任务简报恢复为 v${targetVersion}；历史版本均保留，原始办公文件未修改。`,
          committed_at: new Date().toISOString(),
          external_action: "none",
        };
        currentSnapshot = {
          ...completed,
          result: { summary: target.summary, findings: target.findings, follow_ups: target.follow_ups, review_required: true },
          last_commit: rollbackCommit,
          commits: [...completed.commits, rollbackCommit],
          events: [{ sequence: control.expected_version, event_name: "artifact_version_restored", occurred_at: new Date().toISOString(), status: "completed", message: rollbackCommit.summary, details: {} }],
        };
        return fulfillJson(route, { run: currentSnapshot, replayed: false }, 202);
      }
      if (command === "steer" && currentSnapshot.status === "waiting_input") {
        currentSnapshot = {
          ...currentSnapshot,
          version: control.expected_version + 1,
          last_event_sequence: controlSequence,
          events: [...currentSnapshot.events, { sequence: controlSequence, event_name: "control_steer_recorded", occurred_at: new Date().toISOString(), status: "waiting_input", message: "方向指令已记录，将应用于目标分支。", details: {} }],
        };
        return fulfillJson(route, { run: currentSnapshot, replayed: false }, 202);
      }
      const priorDecisions = currentSnapshot.decision_records;
      currentSnapshot = {
        ...snapshot(
        currentBody,
        command === "pause" ? "paused" : command === "stop" ? "stopped" : command === "resume" ? "completed" : "planning",
        command === "resume" ? 16 : controlSequence,
        ),
        decision_records: priorDecisions,
      };
      return fulfillJson(route, { run: currentSnapshot, replayed: false }, 202);
    }
    if (path.endsWith("/events")) {
      streamCalls += 1; streams.push(url.toString());
      const after = Number(url.searchParams.get("after") ?? "0");
      const all = ["workspace_index", "round_started", "planning_started", "planning_completed", "plan_validation", "analysis_started", "analysis_completed", "result_validation", "evidence_gate", "round_started", "planning_started", "planning_completed", "analysis_started", "analysis_completed", "evidence_gate", options.failed ? "harness_failed" : "loop_committed"];
      if (options.interactiveLoop || options.evidenceGate || options.sourceRecovery || options.boundedRecovery) {
        const sequence = Math.max(after + 1, currentSnapshot.last_event_sequence);
        const terminalEvent = currentSnapshot.status === "completed" ? "loop_committed" : currentSnapshot.status === "stopped" ? "loop_stopped" : currentSnapshot.status === "waiting_input" ? "evidence_gate" : "round_started";
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
      if (options.interactiveLoop || options.evidenceGate || options.sourceRecovery || options.boundedRecovery || options.locationFailure) return fulfillJson(route, currentSnapshot);
      currentSnapshot = snapshot(currentBody, options.failed ? "failed" : "completed");
      return fulfillJson(route, currentSnapshot);
    }
    return fulfillJson(route, { detail: "not found" }, 404);
  });
  return { starts, controls, streams, get startCalls() { return startCalls; }, get streamCalls() { return streamCalls; } };
}

async function openFile(page: Page, file: string) {
  await page.getByRole("textbox", { name: "搜索文件或目录" }).fill(file);
  await page.locator(".workspace-tree-file").filter({ hasText: file }).click();
}

test("shows one complete folder workspace instead of registered scenarios", async ({ page }) => {
  await mockHarness(page); await page.goto("/");
  await expect(page.getByRole("heading", { name: "办公资料库" })).toBeVisible();
  await expect(page.locator(".workspace-facts")).toContainText("96 份文件统一检索");
  await expect(page.locator(".workspace-facts")).toContainText("96 份可安全预览");
  await expect(page.locator('.workspace-tree-folder-row[aria-level="1"]')).toHaveCount(15);
  await expect(page.getByRole("treeitem", { name: "展开文件夹 法务" })).toBeVisible();
  await page.getByRole("treeitem", { name: "展开文件夹 法务" }).click();
  await expect(page.getByRole("treeitem", { name: "展开文件夹 法务/合同与授权" })).toBeVisible();
  await page.getByRole("treeitem", { name: "展开文件夹 法务/合同与授权" }).click();
  await expect(page.getByRole("treeitem", { name: `打开 ${pdfFile.display_path}` })).toBeVisible();
  await expect(page.getByText("星海科技")).toBeVisible();
  if (process.env.CAPTURE_DR0028_EVIDENCE === "1") {
    await page.locator(".data-workbench-grid").screenshot({ path: "../../docs/evidence/screenshots/dr-0028-hierarchical-workspace.png" });
  }
  const body = await page.locator("body").innerText();
  expect(body).not.toMatch(/注册场景|Demo\s*[123]|scenario_id|task_instruction|sha256/i);
});

test("previews CSV, PDF, DOCX and TXT with security facts", async ({ page }) => {
  await mockHarness(page); await page.goto("/");
  await expect(page.getByText("星海科技")).toBeVisible();
  await openFile(page, pdfFile.display_label);
  await expect(page.getByText("授权范围：仅限本项目合同审阅。")).toBeVisible();
  await openFile(page, docxFile.display_label);
  await expect(page.getByText("岗位职责：负责商户拓展与经营分析。")).toBeVisible();
  await openFile(page, txtFile.display_label);
  await expect(page.getByText("service healthy")).toBeVisible();
  await expect(page.getByText("安全预览", { exact: true })).toBeVisible();
  await expect(page.getByText(/没有执行宏、脚本或外部资源/)).toBeVisible();
});

test("runs an arbitrary task while the agent selects evidence from the whole workspace", async ({ page }) => {
  const state = await mockHarness(page); await page.goto("/");
  const instruction = "比较财务往来与授权材料，列出需要人工复核的事实。";
  await page.getByRole("textbox", { name: "任务指令" }).fill(instruction);
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await expect.poll(() => state.starts.length).toBe(1);
  expect(state.starts[0]).toMatchObject({
    workspace_id: "forte-public-office",
    instruction,
    loop: { max_rounds: 3, max_files_per_round: 6, max_model_calls: 6, deadline_seconds: 1200 },
  });
  expect(state.starts[0]).not.toHaveProperty("selected_file_refs");
  await expect(page.getByText("规划模型")).toBeVisible();
  await expect(page.getByText("分析模型")).toBeVisible();
  await expect(page.locator(".loop-view").getByRole("heading", { name: instruction })).toBeVisible();
  await page.getByRole("button", { name: /第 1 轮/ }).click();
  await expect(page.getByText("Agent 本轮自主选择")).toBeVisible();
  await expect(page.getByText("文件名与摘要直接涉及当前目标，先读取这些最小证据。")).toBeVisible();
  await expect(page.getByText("证据缺口")).toBeVisible();
  await expect(page.locator(".loop-round-detail > footer strong")).toHaveText("等待人工输入");
  await expect(page.locator(".loop-branches")).toContainText("任务分支现场");
  await expect(page.locator(".loop-branches")).toContainText("形成分析结果");
  await expect(page.locator(".artifact-evolution")).toContainText("不可变成果历史");
  await expect(page.locator(".artifact-evolution")).toContainText("当前 v2");
  await page.getByRole("button", { name: /发现与建议/ }).click();
  await expect(page.getByRole("heading", { name: /完成 2 轮/ })).toBeVisible();
  expect(await page.locator("body").innerText()).not.toContain("forte-");
});

test("restores an immutable artifact version without overwriting history", async ({ page }) => {
  const state = await mockHarness(page); await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对两轮证据并保留成果版本。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await expect(page.locator(".artifact-evolution")).toContainText("当前 v2");

  const versionOne = page.locator(".artifact-evolution li").filter({ hasText: "v1" });
  await versionOne.getByRole("button", { name: "恢复" }).click();

  await expect(page.locator(".artifact-evolution")).toContainText("当前 v1");
  await expect(page.getByText("已恢复历史成果版本")).toBeVisible();
  expect(state.controls.at(-1)).toMatchObject({ command: "rollback", artifact_version: 1 });
  if (process.env.CAPTURE_DR0026_EVIDENCE === "1") {
    await page.locator(".artifact-evolution").screenshot({
      path: "../../docs/evidence/screenshots/dr-0026-artifact-restore.png",
    });
  }
  await page.getByRole("button", { name: /发现与建议/ }).click();
  await expect(page.getByText("任务证据简报 v1 · 已恢复")).toBeVisible();
});

test("pauses, steers and resumes the same Agent Control Loop from server receipts", async ({ page }) => {
  const state = await mockHarness(page, { interactiveLoop: true }); await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("研究整个资料库，并在证据不足时继续下一轮。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await expect(page.locator(".loop-view")).toContainText("第 1 轮");
  await expect(page.getByRole("button", { name: "当前 Loop 运行中" })).toBeDisabled();
  await expect(page.getByRole("textbox", { name: "任务指令" })).toBeDisabled();
  await expect(page.getByText(/Agent 正在整个资料库中自主检索/)).toBeVisible();

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

test("holds an evidence gap until the user confirms another round", async ({ page }) => {
  const state = await mockHarness(page, { evidenceGate: true }); await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对跨文件事实，证据不足时先停下来。 ");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await expect(page.locator(".loop-round-detail > footer strong")).toHaveText("等待人工输入");
  await expect(page.getByRole("button", { name: "继续此分支" })).toBeEnabled();
  expect(state.controls).toHaveLength(0);
  await page.getByRole("button", { name: "查看问题" }).click();
  await expect(page.getByRole("dialog", { name: "Agent 尚未完成：形成分析结果" })).toBeVisible();
  await expect(page.getByRole("dialog")).toContainText("第 1 轮 / 形成分析结果");
  await expect(page.getByRole("dialog")).toContainText("问题在 Agent 的交付，不在源文件");
  await expect(page.getByRole("dialog")).toContainText("这里没有高亮，不是让你猜哪一行");
  await expect(page.getByRole("dialog")).toContainText("你不需要修改源文件");
  await expect(page.getByRole("dialog")).toContainText("给 Agent 的线索（可选，不清楚可以留空）");
  await expect(page.getByRole("dialog")).toContainText("授权范围：仅限本项目合同审阅。");
  if (process.env.CAPTURE_DR0031_EVIDENCE === "1") {
    await page.getByRole("dialog").screenshot({ path: "../../docs/evidence/screenshots/dr-0031-actionable-gap-recovery.png" });
  }
  await page.getByRole("button", { name: "让 Agent 只重试此分支" }).click();
  if (process.env.CAPTURE_DR0026_EVIDENCE === "1") {
    await page.locator(".loop-branches").screenshot({
      path: "../../docs/evidence/screenshots/dr-0026-branch-control.png",
    });
  }

  await expect.poll(() => state.controls.map((item) => item.command)).toEqual(["resume"]);
  expect(state.controls[0].branch_id).toBe("branch-222222222222");
  await expect(page.locator(".loop-brief")).toContainText("完成 2 轮");
});

test("restores the current server run after a page reload", async ({ page }) => {
  await mockHarness(page, { interactiveLoop: true }); await page.goto("/");
  const instruction = "研究整个资料库并保留可恢复轨迹。";
  await page.getByRole("textbox", { name: "任务指令" }).fill(instruction);
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await expect(page.locator(".loop-view")).toContainText(instruction);

  await page.reload();
  await expect(page.locator(".loop-view")).toContainText(instruction);
  await expect(page.getByRole("button", { name: "当前 Loop 运行中" })).toBeDisabled();
});

test("opens a cited source file from an analysis finding", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await mockHarness(page); await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对余额并引用来源文件。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await page.getByRole("button", { name: /发现与建议/ }).click();
  await page.getByRole("button", { name: "打开审查页" }).first().click();
  await expect(page.getByRole("dialog", { name: "需要你核对并决定下一步" })).toBeVisible();
  await expect(page.getByRole("dialog")).toContainText("高亮位置由服务端从逐字引用解析");
  await expect(page.getByRole("dialog")).toContainText("设计预期");
  await expect(page.getByRole("dialog")).toContainText("实际观测");
  await expect(page.locator('[data-evidence-focus="true"]')).toHaveCount(4);
  if (process.env.CAPTURE_DR0029_EVIDENCE === "1") {
    await page.getByRole("dialog").screenshot({ path: "../../docs/evidence/screenshots/dr-0029-pinpoint-evidence-review.png" });
  }
  await page.getByRole("button", { name: "定位证据 2：实际没有调用新闻搜索" }).click();
  await expect(page.getByText("正在核对：实际没有调用新闻搜索")).toBeVisible();
  await expect(page.locator('[data-evidence-focus="true"]')).toHaveCount(4);
  await expect(page.locator('[data-evidence-focus="true"]').last()).toContainText("web_search_news_called=false");
  if (process.env.CAPTURE_DR0028_EVIDENCE === "1") {
    await page.getByRole("dialog").screenshot({ path: "../../docs/evidence/screenshots/dr-0028-finding-review.png" });
  }
  if (process.env.CAPTURE_DR0029_EVIDENCE === "1") await page.getByRole("dialog").screenshot({ path: "../../docs/evidence/screenshots/dr-0029-observed-source-highlight.png" });
  await page.getByRole("button", { name: "关闭问题审查页" }).click();
  await page.getByRole("button", { name: workflowFile.display_label }).last().click();
  await expect(page.getByText("class QueryAnalysisNode:")).toBeVisible();
  await expect(page.getByRole("button", { name: "预览" })).toHaveClass(/is-active/);
});

test("turns a finding into an evidence-backed human decision and a new task", async ({ page }) => {
  const state = await mockHarness(page); await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对新闻搜索路由并说明如何处理。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await page.getByRole("button", { name: /发现与建议/ }).click();
  await page.getByRole("button", { name: "打开审查页" }).first().click();

  const dialog = page.getByRole("dialog", { name: "需要你核对并决定下一步" });
  if (process.env.CAPTURE_DR0030_EVIDENCE === "1") {
    await dialog.screenshot({ path: "../../docs/evidence/screenshots/dr-0030-actionable-finding-evidence.png" });
  }
  await expect(dialog).toContainText("1发生了什么");
  await expect(dialog).toContainText("2不处理的影响");
  await expect(dialog).toContainText("3现在需要谁做什么");
  await expect(dialog).toContainText("需要你决断");
  await expect(dialog).toContainText("来自 workflow.py · 第 8-11 行 · 服务端逐字匹配");
  await expect(dialog).toContainText("下方黄色区域是这段内容在文件预览中的实际位置");
  await expect(dialog.getByText(/Agent 推荐/)).toHaveCount(0);

  await dialog.locator(".decision-options label").filter({ hasText: "按设计提修复建议" }).click();
  await dialog.getByRole("button", { name: "对照 Agent 建议" }).click();
  await expect(dialog).toContainText("你的选择是 B，系统不会替你改选");
  await dialog.getByRole("textbox", { name: "补充给 Agent 的反馈（可选）" }).fill("同时核对发布记录中的代码版本。");
  if (process.env.CAPTURE_DR0030_EVIDENCE === "1") {
    await dialog.screenshot({ path: "../../docs/evidence/screenshots/dr-0030-actionable-finding-review.png" });
  }
  await dialog.getByRole("button", { name: "接受并交给 Agent" }).click();

  await expect.poll(() => state.controls.length).toBeGreaterThanOrEqual(1);
  expect(state.controls[0]).toMatchObject({
    command: "decision",
    decision_action: "accept",
    finding_id: "finding-111111111111",
    selected_option_id: "B",
    feedback: "同时核对发布记录中的代码版本。",
  });
  await expect.poll(() => state.starts.length).toBe(2);
  expect(state.starts[1].instruction).toContain("形成只读修复建议与待验证清单");
  expect(state.starts[1].instruction).toContain("用户决定：B · 按设计提修复建议");
  expect(state.starts[1].instruction).toContain("同时核对发布记录中的代码版本");
});

test("records closing a pending decision as defer and restores the receipt", async ({ page }) => {
  const state = await mockHarness(page); await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对新闻搜索路由并说明如何处理。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await page.getByRole("button", { name: /发现与建议/ }).click();
  await page.getByRole("button", { name: "打开审查页" }).first().click();
  await page.getByRole("button", { name: "关闭问题审查页" }).click();

  await expect.poll(() => state.controls.length).toBe(1);
  expect(state.controls[0]).toMatchObject({
    command: "decision",
    decision_action: "defer",
    finding_id: "finding-111111111111",
  });

  await page.getByRole("button", { name: /发现与建议/ }).click();
  await page.getByRole("button", { name: "打开审查页" }).first().click();
  await expect(page.getByRole("dialog")).toContainText("人工决定已记录");
  await expect(page.getByRole("dialog")).toContainText("已暂缓");
  if (process.env.CAPTURE_DR0030_EVIDENCE === "1") {
    await page.locator(".decision-record-receipt").screenshot({ path: "../../docs/evidence/screenshots/dr-0030-decision-receipt.png" });
  }
  await page.getByRole("button", { name: "否决这条发现" }).click();
  await expect.poll(() => state.controls.length).toBe(2);
  expect(state.controls[1]).toMatchObject({
    command: "decision",
    decision_action: "decline",
    finding_id: "finding-111111111111",
  });
});

test("accepts a source candidate for bounded branch recovery", async ({ page }) => {
  const state = await mockHarness(page, { sourceRecovery: true }); await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对跨文件版本冲突并逐条定位原文。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const recovery = page.locator(".loop-source-recovery");
  await expect(recovery).toContainText("1 处多候选");
  await recovery.getByRole("button", { name: "选择原文位置" }).click();
  const dialog = page.getByRole("dialog", { name: "需要你确认原文位置" });
  await expect(dialog).toContainText("2 个位置都匹配，需要你选择");
  await dialog.getByRole("button", { name: /选择候选原文 2：workflow\.py/ }).click();
  if (process.env.CAPTURE_DR0032_EVIDENCE === "1") {
    await page.setViewportSize({ width: 1440, height: 1100 });
    await page.screenshot({ path: "../../docs/evidence/screenshots/dr-0032-decision-packet-desktop.png", fullPage: true });
  }
  if (process.env.CAPTURE_DR0030_EVIDENCE === "1") {
    await dialog.screenshot({ path: "../../docs/evidence/screenshots/dr-0030-evidence-disambiguation.png" });
    await dialog.locator(".evidence-resolution-decision").screenshot({ path: "../../docs/evidence/screenshots/dr-0030-evidence-disambiguation-action.png" });
  }
  await dialog.getByRole("textbox", { name: "补充给重跑分支的反馈（可选）" }).fill("同时核对版本字段。" );
  await dialog.getByRole("button", { name: "采用此位置并只重跑本分支" }).click();

  await expect.poll(() => state.controls.map((item) => item.command)).toEqual(["decision"]);
  expect(state.controls[0]).toMatchObject({
    decision_action: "accept",
    resolution_id: "resolution-111111111111",
    selected_candidate_id: "candidate-222222222222",
    decision_request_id: "request-111111111111",
    source_revision: "rev-20260827-a",
    branch_id: "branch-111111111111",
  });
});

test("keeps three ambiguous locations comparable on mobile and records a bounded decision", async ({ page }) => {
  const state = await mockHarness(page, { sourceRecovery: true, sourceRecoveryThreeCandidates: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("在整库中核对新闻路由的真实实现位置。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const recovery = page.locator(".loop-source-recovery");
  await expect(recovery).toContainText("1 处多候选");
  await recovery.getByRole("button", { name: "选择原文位置" }).click();
  const dialog = page.getByRole("dialog", { name: "需要你确认原文位置" });
  await expect(dialog).toContainText("3 个位置都匹配，需要你选择");
  await expect(dialog).toContainText("待决编号");
  await expect(dialog).toContainText("源文件版本 rev-20260827-a");
  await expect(dialog).toContainText("只重跑受影响分支");
  await expect(dialog).toContainText("不会改原文件，不会调用外部业务系统");
  await expect(dialog.getByRole("button", { name: /选择候选原文 1：workflow\.py/ })).toBeVisible();
  await expect(dialog.getByRole("button", { name: /选择候选原文 2：workflow\.py/ })).toBeVisible();
  await expect(dialog.getByRole("button", { name: /选择候选原文 3：workflow\.py/ })).toBeVisible();

  const mobileMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(mobileMetrics.scroll).toBeLessThanOrEqual(mobileMetrics.viewport);
  await dialog.getByRole("button", { name: /选择候选原文 3：workflow\.py/ }).click();
  await expect(dialog).toContainText("已选择一个真实位置");
  if (process.env.CAPTURE_DR0032_EVIDENCE === "1") {
    await page.screenshot({ path: "../../docs/evidence/screenshots/dr-0032-decision-packet-mobile.png", fullPage: true });
  }
  await dialog.getByRole("button", { name: "采用此位置并只重跑本分支" }).click();

  await expect.poll(() => state.controls.map((item) => item.command)).toEqual(["decision"]);
  expect(state.controls[0]).toMatchObject({
    command: "decision",
    decision_action: "accept",
    selected_candidate_id: "candidate-333333333333",
    decision_request_id: "request-111111111111",
    source_revision: "rev-20260827-a",
    resolution_id: "resolution-111111111111",
  });
});

test("cancels an unresolved evidence request without presenting it as rejected", async ({ page }) => {
  const state = await mockHarness(page, { sourceRecovery: true });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对路由证据，但暂不作出来源选择。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await page.locator(".loop-source-recovery").getByRole("button", { name: "选择原文位置" }).click();

  const dialog = page.getByRole("dialog", { name: "需要你确认原文位置" });
  await dialog.getByRole("button", { name: "取消这次待决" }).click();
  await expect.poll(() => state.controls.length).toBe(1);
  expect(state.controls[0]).toMatchObject({ command: "decision", decision_action: "cancel", resolution_id: "resolution-111111111111" });
  expect(state.controls[0].selected_candidate_id).toBeUndefined();
});

test("keeps a deferred evidence request actionable until a final decision", async ({ page }) => {
  const state = await mockHarness(page, { sourceRecovery: true });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("先保留路由证据问题，稍后再确认原文位置。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const recovery = page.locator(".loop-source-recovery");
  await recovery.getByRole("button", { name: "选择原文位置" }).click();
  let dialog = page.getByRole("dialog", { name: "需要你确认原文位置" });
  await dialog.getByRole("button", { name: "保留现有结果，稍后处理" }).click();
  await expect.poll(() => state.controls.length).toBe(1);
  expect(state.controls[0].decision_action).toBe("defer");

  await recovery.getByRole("button", { name: "选择原文位置" }).click();
  dialog = page.getByRole("dialog", { name: "需要你确认原文位置" });
  await expect(dialog.getByRole("button", { name: "采用此位置并只重跑本分支" })).toBeVisible();
  await dialog.getByRole("button", { name: /选择候选原文 1：workflow\.py/ }).click();
  await dialog.getByRole("button", { name: "采用此位置并只重跑本分支" }).click();
  await expect.poll(() => state.controls.length).toBe(2);
  expect(state.controls[1]).toMatchObject({ command: "decision", decision_action: "accept", selected_candidate_id: "candidate-111111111111" });
});

test("restores a pending source disambiguation after reconnect", async ({ page }) => {
  const state = await mockHarness(page, { sourceRecovery: true }); await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对跨文件版本冲突并逐条定位原文。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await expect(page.getByRole("button", { name: "选择原文位置" })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("button", { name: "选择原文位置" })).toBeVisible();
  await page.getByRole("button", { name: "选择原文位置" }).click();
  await expect(page.getByRole("dialog", { name: "需要你确认原文位置" })).toContainText("2 个位置都匹配，需要你选择");
  expect(state.controls).toHaveLength(0);
});

test("pauses an unlocatable result with a guided branch recovery", async ({ page }) => {
  const state = await mockHarness(page, { sourceRecovery: true }); await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对跨文件版本冲突并逐条定位原文。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const recovery = page.locator(".loop-source-recovery");
  await expect(recovery).toContainText("同一段候选原文匹配到多个真实位置");
  await expect(recovery).toContainText("已保留");
  await expect(recovery).toContainText("未采用");
  await expect(recovery).toContainText("未发生");
  await recovery.getByRole("textbox", { name: "补充给下一轮的方向（可选）" }).fill("优先核对版本字段和测试时间。");
  if (process.env.CAPTURE_DR0030_EVIDENCE === "1") {
    await recovery.screenshot({ path: "../../docs/evidence/screenshots/dr-0030-source-location-recovery.png" });
  }
  await recovery.getByRole("button", { name: "只重试本分支" }).first().click();

  await expect.poll(() => state.controls.map((control) => control.command)).toEqual(["steer", "resume"]);
  expect(state.controls[0].instruction).toBe("优先核对版本字段和测试时间。");
  expect(state.controls[1].branch_id).toBe("branch-222222222222");
  await expect(page.locator(".loop-brief")).toContainText("完成 2 轮");
});

test("creates a new scoped task instead of pretending a budget-stopped run can resume", async ({ page }) => {
  const state = await mockHarness(page, { boundedRecovery: true }); await page.goto("/");
  const originalInstruction = "核对资料库中的上线条件和测试结论。";
  await page.getByRole("textbox", { name: "任务指令" }).fill(originalInstruction);
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const recovery = page.locator(".loop-terminal-recovery");
  await expect(recovery).toContainText("当前 Run 已到预算边界，不能继续原地运行");
  await expect(recovery).toContainText("旧 Run、调用回执和成果版本保持不变");
  await expect(recovery).toContainText("原文件修改或外部动作");
  await expect(page.locator(".trace-recovery-hint")).toContainText("本次 Run 已结束");
  await page.locator(".loop-gap").getByRole("button").first().click();
  const gapDialog = page.getByRole("dialog", { name: /Agent 尚未完成/ });
  await expect(gapDialog).toContainText("旧 Run 已结束；你可让 Agent 用这个分支创建新任务");
  await expect(gapDialog).toContainText("创建新任务继续此分支");
  await expect(gapDialog).toContainText("问题在 Agent 的交付，不在源文件");
  if (process.env.CAPTURE_DR0031_EVIDENCE === "1") {
    await gapDialog.screenshot({ path: "../../docs/evidence/screenshots/dr-0031-terminal-gap-recovery.png" });
  }
  await gapDialog.getByRole("button", { name: "关闭问题审查页" }).click();
  await recovery.getByRole("textbox", { name: "补充给新任务的方向（可选）" }).fill("优先核对版本号和测试日期。" );
  if (process.env.CAPTURE_DR0030_EVIDENCE === "1") {
    await recovery.screenshot({ path: "../../docs/evidence/screenshots/dr-0030-bounded-branch-recovery.png" });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  const mobileMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(mobileMetrics.scroll).toBeLessThanOrEqual(mobileMetrics.viewport);
  await recovery.locator(".source-recovery-branches article").filter({ hasText: "读取相关资料" }).getByRole("button", { name: "用此分支创建新任务" }).click();

  await expect.poll(() => state.starts.length).toBe(2);
  expect(state.controls).toHaveLength(0);
  expect(state.starts[1].instruction).toContain(originalInstruction);
  expect(state.starts[1].instruction).toContain("续办分支：读取相关资料");
  expect(state.starts[1].instruction).toContain("优先核对版本号和测试日期");
  expect(state.starts[1].instruction).toContain("这些只是历史选择，不限制新 Run 重新检索整个资料库");
  expect(state.starts[1].instruction).toContain("只读分析，不修改原文件，不执行外部动作");
});

test("starts a new whole-workspace loop only after the user confirms an agent proposal", async ({ page }) => {
  const state = await mockHarness(page); await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("研究整个资料库并提出下一步。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await page.getByRole("button", { name: /发现与建议/ }).click();
  const proposal = "继续核对授权范围与财务往来之间是否存在执行约束，并形成待办清单。";
  await expect(page.getByText(proposal)).toBeVisible();
  await page.getByRole("button", { name: "查看形成依据" }).click();
  await expect(page.getByRole("dialog", { name: "建议 1" })).toBeVisible();
  await expect(page.getByRole("dialog")).toContainText("当前协议没有为每条 follow_up 单独绑定引用");
  await page.getByRole("button", { name: "关闭问题审查页" }).click();
  await page.getByRole("button", { name: "确认并启动" }).click();
  await expect.poll(() => state.starts.length).toBe(2);
  expect(state.starts[1].instruction).toBe(proposal);
  expect(state.starts[1]).not.toHaveProperty("selected_file_refs");
});

test("reuses the same command key when a start response is unknown", async ({ page }) => {
  const state = await mockHarness(page, { failFirstStart: true }); await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对资料库中的余额变化。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await expect(page.getByLabel("工作现场").getByText("任务启动结果未知")).toBeVisible();
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await expect.poll(() => state.starts.length).toBe(2);
  expect(state.starts[0].idempotency_key).toBe(state.starts[1].idempotency_key);
});

test("reconnects the event stream from the last observed sequence", async ({ page }) => {
  const state = await mockHarness(page, { disconnect: true }); await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对资料库中的余额变化。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await expect.poll(() => state.streamCalls).toBeGreaterThanOrEqual(2);
  expect(state.streams.some((url) => new URL(url).searchParams.get("after") === "1")).toBeTruthy();
});

test("explains an unavailable workspace and fails closed without a result", async ({ page }) => {
  const state = await mockHarness(page, { workspaceFailures: 1, failed: true }); await page.goto("/");
  await expect(page.getByRole("heading", { name: "办公资料库暂时无法读取" })).toBeVisible();
  await page.getByRole("button", { name: "重新读取" }).click();
  await expect(page.getByRole("heading", { name: "办公资料库" })).toBeVisible();
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对资料库中的余额变化。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await expect(page.getByText("本轮已安全停止")).toBeVisible();
  await expect(page.locator(".loop-failure-recovery")).toContainText("这次运行已停下，但不是死路");
  await expect(page.getByRole("button", { name: "缩小范围重新核对" })).toBeEnabled();
  await page.getByRole("button", { name: "缩小范围重新核对" }).click();
  await expect.poll(() => state.starts.length).toBe(2);
  await expect(page.locator("body")).not.toContainText(/artifact\.write|run_workspace_write/);
});

test("explains a legacy location failure and offers the smallest retry", async ({ page }) => {
  const state = await mockHarness(page, { locationFailure: true }); await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对 F07 测试结论与代码版本。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const recovery = page.locator(".loop-failure-recovery");
  await expect(recovery).toContainText("候选结论无法唯一定位到原文");
  await expect(recovery).toContainText("任务目标、服务端计划、3 次模型调用记录和已选文件范围都还在");
  if (process.env.CAPTURE_DR0030_EVIDENCE === "1") {
    await recovery.screenshot({ path: "../../docs/evidence/screenshots/dr-0030-legacy-failure-recovery.png" });
  }
  await recovery.getByRole("button", { name: "缩小范围重新核对" }).click();
  await expect.poll(() => state.starts.length).toBe(2);
  expect(state.starts[1].instruction).toContain("恢复策略：先只核对");
});

test("mobile keeps file-manager browsing, task input, preview and trajectory usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 }); await mockHarness(page); await page.goto("/");
  await expect(page.getByRole("heading", { name: "办公资料库" })).toBeVisible();
  const metrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(metrics.scroll).toBeLessThanOrEqual(metrics.viewport);
  await expect(page.getByRole("textbox", { name: "任务指令" })).toBeVisible();
  await expect(page.locator(".table-preview")).toBeVisible();
  const shortControls = await page.locator("button:visible, summary:visible").evaluateAll((nodes) => nodes.filter((node) => (node as HTMLElement).getBoundingClientRect().height < 44).map((node) => ({ text: node.textContent, height: (node as HTMLElement).getBoundingClientRect().height })));
  expect(shortControls).toEqual([]);
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对余额并打开问题审查页。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await page.getByRole("button", { name: /发现与建议/ }).click();
  await page.getByRole("button", { name: "打开审查页" }).first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog")).toContainText("选择一条，右侧打开真实文件并高亮对应位置");
  const reviewMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(reviewMetrics.scroll).toBeLessThanOrEqual(reviewMetrics.viewport);
  const closeBox = await page.getByRole("button", { name: "关闭问题审查页" }).boundingBox();
  expect(closeBox?.width).toBeGreaterThanOrEqual(44);
  expect(closeBox?.height).toBeGreaterThanOrEqual(44);
});
