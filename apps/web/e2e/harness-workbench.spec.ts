import { expect, test, type Page, type Route } from "@playwright/test";
import tc04TestManifest from "../../../docs/evidence/manifests/tc04-public-test-manifest-20260828.json";
import tc11BusinessOutcome from "../../../docs/evidence/manifests/tc11-business-gate-outcome-20260828.json";
import tc12TestManifest from "../../../docs/evidence/manifests/tc12-public-test-manifest-20260828.json";

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

const csvFile = fileItem("forte-1111111111111111", "forte-folder-111111111111", "2026往来明细.xlsx", "财务管理", "XLSX", "table");
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
  if (fileRef === csvFile.file_ref) return { ...base, kind: "table", columns: ["客商", "方向", "期末余额"], rows: [{ row_number: 2, values: ["星海科技股份有限公司华东区域企业服务中心", "借", "1,500,000.00"] }], total_rows: 30 };
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
      max_rounds: 12,
      max_files_per_round: 16,
      max_model_calls: 30,
      deadline_seconds: 7200,
      external_action: "none",
    },
    budget: {
      max_rounds: 12,
      max_files_per_round: 16,
      max_model_calls: 30,
      deadline_seconds: 7200,
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
    decision_requests: [],
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
    workspace_artifacts: [],
    effect_receipts: [],
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

function verifiedEffectSnapshot(body: { workspace_id: string; instruction: string }) {
  const base = snapshot(body, "completed", 20);
  const artifactIds = [
    "workspace-artifact-111111111111",
    "workspace-artifact-222222222222",
    "workspace-artifact-333333333333",
  ];
  const artifacts = [{
    artifact_id: artifactIds[0],
    capability_id: "office-finance-reconciliation",
    scenario_id: "TC-05",
    title: "2026 期末未付明细",
    file_name: "未付统计.csv",
    media_type: "text/csv",
    size: 2399,
    version: 1,
    round_number: 1,
    source_file_refs: [csvFile.file_ref],
    validator_id: "validator-finance-reconciliation-v1",
    verifier_status: "passed",
    checks: [
      { check_id: "check-finance-current-source", label: "2026 内容来源", passed: true, detail: "明细行只取自 2026 往来工作簿，不是三期合并表。" },
      { check_id: "check-finance-unpaid-rows", label: "未付逐行复算", passed: true, detail: "31 条贷方期末余额逐行相等。" },
      { check_id: "check-finance-unpaid-sort", label: "未付排序", passed: true, detail: "按客商升序、同客商金额降序。" },
    ],
    summary: "31 条记录已逐行复算。",
    covered_period: "2026 年期末",
    statistic_basis: "筛选期末余额大于 0 且方向为“贷”的行；每行代表一个科目与客商组合。",
    purpose: "查看 2026 年期末待付款项；不是三期合并表。",
    record_count: 31,
    download_path: `/v1/harness/runs/${base.run_id}/artifacts/${artifactIds[0]}`,
    created_at: new Date().toISOString(),
    original_inputs_modified: false,
    review_required: true,
    external_action: "none",
  }, {
    artifact_id: artifactIds[1],
    capability_id: "office-finance-reconciliation",
    scenario_id: "TC-05",
    title: "2026 期末未收明细",
    file_name: "未收统计.csv",
    media_type: "text/csv",
    size: 340,
    version: 1,
    round_number: 1,
    source_file_refs: [csvFile.file_ref],
    validator_id: "validator-finance-reconciliation-v1",
    verifier_status: "passed",
    checks: [
      { check_id: "check-finance-current-source", label: "2026 内容来源", passed: true, detail: "明细行只取自 2026 往来工作簿，不是三期合并表。" },
      { check_id: "check-finance-unreceived-rows", label: "未收逐行复算", passed: true, detail: "2 条借方期末余额逐行相等。" },
      { check_id: "check-finance-unreceived-sort", label: "未收排序", passed: true, detail: "按客商升序、同客商金额降序。" },
    ],
    summary: "2 条记录已逐行复算。",
    covered_period: "2026 年期末",
    statistic_basis: "筛选期末余额大于 0 且方向为“借”的行；每行代表一个科目与客商组合。",
    purpose: "查看 2026 年期末待收款项；2 表示记录数，不是期间数。",
    record_count: 2,
    download_path: `/v1/harness/runs/${base.run_id}/artifacts/${artifactIds[1]}`,
    created_at: new Date().toISOString(),
    original_inputs_modified: false,
    review_required: true,
    external_action: "none",
  }, {
    artifact_id: artifactIds[2],
    capability_id: "office-finance-reconciliation",
    scenario_id: "TC-05",
    title: "三期僵尸账款核对说明",
    file_name: "跨期核对说明.md",
    media_type: "text/markdown",
    size: 620,
    version: 1,
    round_number: 1,
    source_file_refs: [csvFile.file_ref, pdfFile.file_ref, docxFile.file_ref],
    validator_id: "validator-finance-reconciliation-v1",
    verifier_status: "passed",
    checks: [
      { check_id: "check-finance-source", label: "三期来源完整", passed: true, detail: "三个固定期间工作簿均通过 Catalog 完整性检查。" },
      { check_id: "check-finance-zombie", label: "跨期僵尸账款复算", passed: true, detail: "按同一客商、同一科目、三期借方期末余额逐项比较。" },
    ],
    summary: "三期借方未收余额已比较，结论为无僵尸账款。",
    covered_period: "2025 年上半年、2025 年下半年、2026 年",
    statistic_basis: "按同一科目名称与客商名称，对三期正数借方期末余额逐项比较。",
    purpose: "识别三期借方未收余额连续不变的僵尸账款候选。",
    record_count: null,
    download_path: `/v1/harness/runs/${base.run_id}/artifacts/${artifactIds[2]}`,
    created_at: new Date().toISOString(),
    original_inputs_modified: false,
    review_required: true,
    external_action: "none",
  }];
  return {
    ...base,
    workspace_artifacts: artifacts,
    effect_receipts: [{
      receipt_id: "effect-receipt-111111111111",
      capability_id: "office-finance-reconciliation",
      scenario_id: "TC-05",
      status: "passed",
      state: "已冻结 3 份 FORTE 输入，原始文件保持只读。",
      action: "调用确定性财务核对工具并写入隔离运行工作区。",
      observation: "生成 3 份真实成果文件，共 7 项唯一确定性检查（重复 ID 已合并），7/7 通过。",
      cost: "0 次额外模型调用；仅消耗本机确定性计算。",
      result: "所有确定性效果门通过，成果仍需用户复核。",
      source_file_refs: [csvFile.file_ref, pdfFile.file_ref],
      artifact_ids: artifactIds,
      prohibited_side_effects: ["不覆盖原始账表", "不记账", "不发起付款"],
      created_at: new Date().toISOString(),
      external_action: "none",
    }],
    events: [
      ...base.events,
      { sequence: 17, event_name: "deterministic_office_tool_started", occurred_at: new Date().toISOString(), status: "verifying", message: "已调用确定性办公工具；本次不额外调用模型。", details: {} },
      { sequence: 18, event_name: "run_workspace_artifact_written", occurred_at: new Date().toISOString(), status: "verifying", message: "已在隔离运行工作区生成“未付统计.csv”。", details: {} },
      { sequence: 19, event_name: "deterministic_verification_completed", occurred_at: new Date().toISOString(), status: "verifying", message: "真实成果文件已通过确定性效果门，仍需用户复核。", details: {} },
    ],
    last_event_sequence: 20,
  };
}

function outboundEffectSnapshot(body: { workspace_id: string; instruction: string }) {
  const base = snapshot(body, "completed", 20);
  const artifactId = "workspace-artifact-101010101010";
  const terminalStates = ["PTP登记", "转人工跟进", "安排重拨", "停止外呼（达上限）", "加入禁呼名单", "案件升级"];
  const checks = [
    "专业说明来源完整",
    "唯一开始节点",
    "拨号前时段 Gate",
    "接通与未接通互斥",
    "每日 3 次 / 每小时 1 次上限",
    "录音告知先于身份确认",
    "身份确认先于欠款引导",
    "第三方禁呼",
    "本人态度分支",
    "无效通话回到频次判断",
    "高风险情况转人工",
    "六类终态齐全",
    "外部动作均未发生",
  ].map((label, index) => ({
    check_id: `check-outbound-${String(index + 1).padStart(2, "0")}`,
    label,
    passed: true,
    detail: index === 12 ? "只在隔离 Run Workspace 生成 DOCX；拨号、CRM 与短信回执均为 none。" : `${label}已由固定规则复核。`,
  }));
  const executionSummary = "本次只生成流程设计 DOCX。文档中的“发起外呼拨号”“写 CRM”等是流程节点描述，不是执行回执；实际没有拨号、没有写 CRM、没有发送短信。";
  return {
    ...base,
    workspace_artifacts: [{
      artifact_id: artifactId,
      capability_id: "office-compliant-outbound-flow",
      scenario_id: "TC-10",
      title: "M1 逾期用户合规外呼流程设计",
      file_name: "外呼流程-M1逾期用户AI外呼催收流程图.docx",
      media_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      size: 2840,
      version: 1,
      round_number: 1,
      source_file_refs: [docxFile.file_ref],
      validator_id: "validator-compliant-outbound-flow-v1",
      verifier_status: "passed",
      checks,
      summary: "依据《专业性说明.md》生成完整流程设计，覆盖六类终态；本次没有执行外呼。",
      covered_period: "信用卡 M1 逾期阶段",
      statistic_basis: "只采用《专业性说明.md》中的时段、频次、录音、身份确认、第三方禁呼、转人工和终态规则。",
      purpose: "供业务与合规负责人审阅流程是否可采用；不是拨号、CRM 或短信执行工具。",
      record_count: null,
      deliverable_type: "流程设计 DOCX",
      key_outputs: terminalStates,
      key_outputs_label: "6 类关键终态",
      review_guidance: "13 项确定性规则检查通过后，仍需业务与合规负责人复核当前制度口径、话术和实际系统接入方案。",
      execution_summary: executionSummary,
      download_path: `/v1/harness/runs/${base.run_id}/artifacts/${artifactId}`,
      created_at: new Date().toISOString(),
      original_inputs_modified: false,
      review_required: true,
      external_action: "none",
    }],
    effect_receipts: [{
      receipt_id: "effect-receipt-101010101010",
      capability_id: "office-compliant-outbound-flow",
      scenario_id: "TC-10",
      status: "passed",
      state: "已冻结《专业性说明.md》，原始文件保持只读。",
      action: "生成流程设计 DOCX，并执行 13 项确定性规则检查。",
      observation: "1 份 DOCX 可下载，13/13 项规则检查通过。",
      cost: "0 次额外模型调用；仅消耗本机确定性计算。",
      result: "流程设计文件已生成，仍需业务与合规负责人复核。",
      source_file_refs: [docxFile.file_ref],
      artifact_ids: [artifactId],
      prohibited_side_effects: ["不拨号", "不写 CRM", "不发送短信"],
      created_at: new Date().toISOString(),
      external_action: "none",
    }],
    events: [
      ...base.events,
      { sequence: 17, event_name: "deterministic_office_tool_started", occurred_at: new Date().toISOString(), status: "verifying", message: "固定合规流程工具开始生成文档。", details: {} },
      { sequence: 18, event_name: "run_workspace_artifact_written", occurred_at: new Date().toISOString(), status: "verifying", message: "流程设计 DOCX 已写入隔离运行工作区。", details: {} },
      { sequence: 19, event_name: "deterministic_verification_completed", occurred_at: new Date().toISOString(), status: "verifying", message: "13 项规则检查通过；没有外部动作。", details: {} },
    ],
    last_event_sequence: 20,
  };
}

function reactRefactorEffectSnapshot(body: { workspace_id: string; instruction: string }) {
  const base = snapshot(body, "completed", 20);
  const artifactIds = ["workspace-artifact-202020202020", "workspace-artifact-212121212121"];
  const common = {
    capability_id: "office-code-react-refactor",
    scenario_id: "TC-02",
    version: 1,
    round_number: 1,
    source_file_refs: [csvFile.file_ref, pdfFile.file_ref, docxFile.file_ref],
    validator_id: "validator-code-project-copy-v2",
    verifier_status: "passed",
    covered_period: "FORTE 固定 commit 345c1ec 的 algorithm-013 输入版本",
    statistic_basis: "完整复制 7 个输入文件后，仅在隔离副本修改 2 个并新增 ReAct 控制器、测试与审计文件",
    purpose: "供代码评审者下载、独立复测并人工合并；不会覆盖 FORTE 原文件",
    record_count: null,
    review_guidance: "先核对 CHANGESET.patch，再按自测卡运行两条命令。全部通过后人工挑选合并；当前系统不会写回仓库或发起 PR。",
    created_at: new Date().toISOString(),
    original_inputs_modified: false,
    review_required: true,
    external_action: "none",
  };
  const checks = [
    "完整复制真实项目", "原契约文件逐字保留", "主入口改走有界 ReAct", "可机器审查改动",
    "完整副本编译", "测试清单与执行一致", "风险契约测试齐全", "迭代上限 1 到 20",
    "非法动作与工具拒绝", "只记录动作与观察", "默认策略边界明确", "固定测试无网络调用",
  ].map((label, index) => ({ check_id: `check-react-${index}`, label, passed: true, detail: `${label}已由固定 TC-02 Verifier 复核。` }));
  const selfTest = {
    instruction: "把搜索 Agent 从固定 Workflow 重构为带迭代上限和轨迹的 ReAct 结构。",
    expected_files: ["search_agent_workflow/", "search_agent_workflow/CHANGESET.patch", "search_agent_workflow/test_receipt.json"],
    commands: ["python -m compileall -q search_agent_workflow", "python -m unittest discover -s search_agent_workflow/tests -v"],
    expected_checks: ["当前 20 项 unittest 与包内清单一致且全部通过", "真实 ToolRegistry 调用与 action/observation 轨迹可核对", "默认策略确定性执行已规划工具，action_policy 接口可替换", "外层 Planner/Analyst 调用不冒充代码包内部 action policy", "原查询漂移、质量降级、来源配额、句界截断行为保持"],
    failure_signals: ["任一命令退出码非 0", "声明测试 ID 与执行集合不一致", "main.py 仍只调用 SearchWorkflow"],
  };
  return {
    ...base,
    workspace_artifacts: [{
      ...common,
      artifact_id: artifactIds[0],
      title: "algorithm-013 有界 ReAct 控制结构代码包",
      file_name: "search-agent-react-refactor.zip",
      media_type: "application/zip",
      size: 48210,
      checks,
      summary: "已从真实项目副本生成可审查 ZIP；编译与 20 项测试通过。",
      deliverable_type: "完整可运行项目副本",
      key_outputs: ["修改 config.py：增加 1 到 20 次迭代边界", "修改 main.py：主入口改走 bounded ReAct", "新增 react_agent.py：复用原 LLM、ToolRegistry、WorkflowState 与业务节点", "默认策略按已规划工具依次执行；action_policy 可替换；未证明包内模型自主 ReAct", "原 workflow.py、llm.py、tools.py、requirements.txt、search_agent.log 逐字保留"],
      key_outputs_label: "文件变更",
      execution_summary: "编译退出码 0；实际运行 20 项 unittest；本次固定测试未调用网络、未安装依赖、未调用生产搜索；runner 不具备 OS 级 socket 隔离；外层 Planner/Analyst 不是包内 action policy。",
      self_test: selfTest,
      download_path: `/v1/harness/runs/${base.run_id}/artifacts/${artifactIds[0]}`,
    }, {
      ...common,
      artifact_id: artifactIds[1],
      title: "TC-02 测试与改动说明",
      file_name: "TC-02测试与改动说明.md",
      media_type: "text/markdown",
      size: 1820,
      checks,
      summary: "说明固定五节点如何变为有界 ReAct 控制结构，并记录默认策略边界、20 项真实测试与人工合并步骤。",
      deliverable_type: "测试回执与改动说明",
      key_outputs: ["完整副本编译及 20 项测试通过", "公开轨迹只有 action/observation，不含私有思维过程", "默认策略确定性执行已规划工具；未证明包内模型自主 ReAct", "原 FORTE 输入未覆盖，external_action=none"],
      key_outputs_label: "验证结论",
      execution_summary: "编译 120 ms，测试 150 ms；失败时成果卡必须标红并停止人工合并。",
      self_test: null,
      download_path: `/v1/harness/runs/${base.run_id}/artifacts/${artifactIds[1]}`,
    }],
    effect_receipts: [{
      receipt_id: "effect-receipt-202020202020",
      capability_id: "office-code-react-refactor",
      scenario_id: "TC-02",
      status: "passed",
      state: "已冻结 algorithm-013 的 7 个输入文件，原始树保持只读。",
      action: "复制真实项目到隔离 Run Workspace，修改副本并执行固定编译和测试。",
      observation: "生成 2 份真实成果文件，共享 12 项确定性检查，12/12 通过。",
      cost: "0 次额外模型调用；仅消耗本机固定代码变换与测试。",
      result: "固定 TC-02 效果门通过，等待人工代码评审与合并。",
      source_file_refs: common.source_file_refs,
      artifact_ids: artifactIds,
      prohibited_side_effects: ["不修改 FORTE 原始源码", "不安装依赖", "本次固定测试不调用生产搜索"],
      created_at: new Date().toISOString(),
      external_action: "none",
    }],
    last_event_sequence: 20,
  };
}

function evaluationPlatformEffectSnapshot(body: { workspace_id: string; instruction: string }) {
  const base = snapshot(body, "completed", 20);
  const sourceRefs = folders.flatMap((folder) => folder.files).slice(0, 44).map((file) => file.file_ref);
  const artifactIds = ["workspace-artifact-404040404040", "workspace-artifact-414141414141"];
  const checks = [
    ["check-eval-full-copy", "完整复制真实评测平台", "隔离副本包含 source-code 全部 44 个前后端文件。"],
    ["check-eval-baseline-red", "修复前先复现缺陷", "覆盖三类缺陷的五个回归均先出现红灯。"],
    ["check-eval-real-diff", "三处真实源码可审查", "模型删除、追加序号和 P99 均有 unified diff。"],
    ["check-eval-five-test-areas", "五类真实对象均有测试", "五类测试直接导入真实 Service、Engine 与 Utils。"],
    ["check-eval-compile", "完整后端与测试可编译", "compileall 退出码 0。"],
    ["check-eval-test-manifest", "声明与实际测试 ID 一致", "117 个具名测试与 manifest 完全一致。"],
    ["check-eval-real-tests", "真实项目测试零失败", "117/117 通过，0 失败，0 错误。"],
    ["check-eval-changed-source-coverage", "变更源码逐文件覆盖率", "model_service.py 97.9%；dataset_service.py 97.8%；evaluation_engine.py 89.2%。"],
    ["check-eval-aggregate-coverage", "真实模块汇总覆盖率", "选定 Service、Engine、Utils 汇总语句覆盖率 95.7%。"],
    ["check-eval-mock-http", "外部 HTTP 只使用 Mock", "没有调用真实模型 endpoint。"],
    ["check-eval-review-package", "下载包可独立复跑", "完整副本、diff、清单、双阶段回执和自测卡均在 ZIP 中。"],
    ["check-eval-source-unchanged", "FORTE 原始项目保持只读", "生成与测试后 44 个 source-code 文件字节不变。"],
  ].map(([check_id, label, detail]) => ({ check_id, label, passed: true, detail }));
  const selfTest = {
    instruction: "为评测平台补充单元测试，覆盖 Service、执行引擎和工具类；真实运行测试，修复失败，并给出覆盖率与修改文件。",
    expected_files: ["evaluation-platform/app/", "evaluation-platform/frontend/", "evaluation-platform/tests/", "evaluation-platform/changes.patch", "evaluation-platform/test-manifest.json", "evaluation-platform/test-results.json"],
    commands: ["python -m compileall -q app tests run_self_test.py", "python run_self_test.py"],
    expected_checks: [
      "当前 117 个具名测试与 manifest 完全一致且全部通过",
      "模型 Service 15 项、数据集 Service 16 项、实验 Service 15 项",
      "执行引擎 23 项、工具类与事务 48 项",
      "三份变更源码逐文件覆盖率均不低于 80%",
      "HTTP 使用 MockTransport，Session 回滚隔离可核对",
    ],
    failure_signals: ["命令退出码非 0", "声明测试 ID 与实际集合不一致", "任一变更源码覆盖率低于 80%", "ZIP 缺完整真实项目副本"],
    test_manifest_file: "evaluation-platform/test-manifest.json",
    test_manifest_matches_collected: true,
    test_suites: tc04TestManifest.categories,
  };
  const common = {
    capability_id: "office-code-test-and-fix",
    scenario_id: "TC-04",
    version: 1,
    round_number: 1,
    source_file_refs: sourceRefs,
    validator_id: "validator-evaluation-platform-project-v2",
    verifier_status: "passed",
    checks,
    covered_period: "dev-015/source-code 完整 44 文件隔离副本",
    statistic_basis: "五类共 117 项具名测试；三份变更源码逐文件覆盖率均不低于 80%；选定真实模块汇总覆盖率 95.7%",
    purpose: "用于下载、复跑、审查 diff 后由人工合并；FORTE 原件未覆盖，未调用真实模型端点，未运行前端脚本，也未自动创建 PR。",
    record_count: null,
    key_outputs_label: "真实修复与测试范围",
    review_guidance: "先审查 changes.patch 与修复前后回执，再在已有依赖环境复跑自测命令；通过后由人工决定如何合并。",
    execution_summary: "未修复完整副本先出现 5 个红灯；修复后运行 117 项具名测试，117/117 通过；三份变更源码覆盖率均超过 80%。",
    created_at: new Date().toISOString(),
    original_inputs_modified: false,
    review_required: true,
    external_action: "none",
  };
  return {
    ...base,
    workspace_artifacts: [{
      ...common,
      artifact_id: artifactIds[0],
      title: "评测平台修复包",
      file_name: "评测平台真实修复包.zip",
      media_type: "application/zip",
      size: 264000,
      summary: "完整复制 44 个真实项目文件，包含三处源码修复、117 项测试、逐文件覆盖率和复跑入口。",
      deliverable_type: "完整真实工程隔离副本（ZIP）",
      key_outputs: ["修复模型删除状态：只阻止 RUNNING 实验", "修复追加导入序号：从 max_seq + 1 开始", "修复 P99 小样本最近秩索引", "五类测试直接导入真实 Service、Engine 与 Utils", "117 个测试 ID 与 manifest 一致，117/117 通过", "model_service.py 97.9%；dataset_service.py 97.8%；evaluation_engine.py 89.2%"],
      self_test: selfTest,
      download_path: `/v1/harness/runs/${base.run_id}/artifacts/${artifactIds[0]}`,
    }, {
      ...common,
      artifact_id: artifactIds[1],
      title: "TC-04 真实测试报告",
      file_name: "TC-04真实测试报告.md",
      media_type: "text/markdown",
      size: 5400,
      summary: "分别记录旧 105 项替身 false green、真实未修复副本红灯和修复后 117 项绿灯。",
      deliverable_type: "真实命令、测试清单与覆盖率报告（Markdown）",
      key_outputs: ["修复前真实副本：5 个失败或错误", "修复后真实副本：117/117 通过", "三份变更源码逐文件覆盖率均超过 80%", "原 FORTE 44 个 source-code 文件未改动"],
      self_test: null,
      download_path: `/v1/harness/runs/${base.run_id}/artifacts/${artifactIds[1]}`,
    }],
    effect_receipts: [{
      receipt_id: "effect-receipt-404040404040",
      capability_id: "office-code-test-and-fix",
      scenario_id: "TC-04",
      status: "passed",
      state: "已冻结完整 source-code 的 44 个 FORTE 输入，原始文件保持只读。",
      action: "复制真实项目到隔离 Run Workspace，先跑红灯，再修复三处真实源码并复跑。",
      observation: "生成 2 份真实成果文件，共享 12 项确定性检查，12/12 通过。",
      cost: "0 次额外模型调用；本地测试进程未安装依赖。",
      result: "真实项目修复包与报告可下载，等待人工代码评审与合并。",
      source_file_refs: sourceRefs,
      artifact_ids: artifactIds,
      prohibited_side_effects: ["不修改 FORTE 原始源码", "不调用真实模型 endpoint", "不运行前端 package script", "不自动创建 PR"],
      created_at: new Date().toISOString(),
      external_action: "none",
    }],
    last_event_sequence: 20,
  };
}

function dashboardToolkitEffectSnapshot(body: { workspace_id: string; instruction: string }) {
  const base = snapshot(body, "completed", 20);
  const sourceRefs = folders.flatMap((folder) => folder.files).slice(0, 11).map((file) => file.file_ref);
  const artifactIds = ["workspace-artifact-121212121212", "workspace-artifact-131313131313"];
  const checks = [
    ["check-tc12-complete-copy", "完整 11 文件隔离副本", "冻结并复制 dashboard-toolkit 全部 11/11 个允许输入文件。"],
    ["check-tc12-source-unchanged", "FORTE 原始项目保持只读", "四阶段测试和独立复跑前后输入树不变。"],
    ["check-tc12-stage-a-alias-red", "原配置解析红灯", "Stage A 真实复现 @ 指向 ./source 的解析失败。"],
    ["check-tc12-stage-b-business-red", "配置修复后的业务红灯", "Stage B 复现增长率、排序副作用、相等值和日期函数未导出。"],
    ["check-tc12-stage-c-boundary-red", "日期闭区间红灯", "Stage C 复现开始日和结束日被排除。"],
    ["check-tc12-final-green", "同一测试集最终全绿", "Stage D 71/71 通过，零失败。"],
    ["check-tc12-manifest", "测试清单与实际收集一致", "页面、manifest 和 collected IDs 同为 71 项。"],
    ["check-tc12-coverage", "逐文件覆盖率达到门槛", "metrics 100/100/100；transformer 100/91.3/100；filter 100/97.5/100。"],
    ["check-tc12-diff-scope", "真实修改范围可审查", "统一 diff 只修改配置和三个真实业务源码。"],
    ["check-tc12-independent-rerun", "下载包独立解压复跑", "独立临时目录运行固定入口，测试 ID、覆盖率、退出码和 manifest 再次一致。"],
    ["check-tc12-fixed-runner-boundary", "固定本地执行边界", "未运行来源 scripts、未联网安装，不声称 OS 级断网。"],
    ["check-tc12-catalog-reread", "原始输入再次读取一致", "测试后重新读取 11/11 输入，字节与引用不变。"],
  ].map(([check_id, label, detail]) => ({ check_id, label, passed: true, detail }));
  const selfTest = {
    instruction: "为三个看板工具模块编写 Vitest，修复源码并真实运行测试。",
    expected_files: ["dashboard-toolkit/src/", "dashboard-toolkit/tests/", "dashboard-toolkit/changes.patch", "dashboard-toolkit/test-manifest.json", "dashboard-toolkit/evidence/", "dashboard-toolkit/run-self-test.mjs"],
    commands: ["node dashboard-toolkit/run-self-test.mjs apps/web/node_modules/vitest/vitest.mjs"],
    expected_checks: ["Stage A 必须因原 @ 别名指向 ./source 而红灯", "Stage B 必须由真实源码复现增长率、排序副作用和未导出日期函数", "Stage C 必须由真实测试复现日期闭区间缺陷", "Stage D 必须 71/71 通过且零失败", "三个测试套件必须直接导入真实业务模块", "test-manifest.json 声明集合必须等于实际 collected IDs", "三份变更业务源码 statements/lines >= 85%，branches >= 75%"],
    failure_signals: ["命令退出码非 0，或最终出现 failed/error", "任一阶段没有出现预期红灯，说明测试未证明原缺陷", "声明 ID 与实际 collected IDs 不一致", "任一变更业务源码覆盖率未达到逐文件门槛"],
    test_manifest_file: "dashboard-toolkit/test-manifest.json",
    test_manifest_matches_collected: true,
    test_suites: tc12TestManifest.test_suites.map((suite) => ({
      suite_id: suite.id,
      label: suite.label,
      test_files: suite.test_files,
      test_count: suite.test_count,
      test_ids: suite.test_ids,
    })),
  };
  const common = {
    capability_id: "office-js-test-and-fix",
    scenario_id: "TC-12",
    version: 1,
    round_number: 1,
    source_file_refs: sourceRefs,
    validator_id: "validator-dashboard-toolkit-project-v2",
    verifier_status: "passed",
    checks,
    covered_period: "固定 FORTE qa-003 / dashboard-toolkit 公开输入",
    statistic_basis: "完整 11/11 输入；同一套 71 项 Vitest 的 Stage A/B/C 红灯与 Stage D 绿灯；Vitest 与 coverage-v8 均为 1.6.1。",
    purpose: "用于下载、复跑和审查统一 diff；不会覆盖 FORTE 原件，也不会自动创建或合并 PR。",
    record_count: null,
    key_outputs_label: "红灯到绿灯与修复影响",
    key_outputs: [
      "Stage A：原配置真实复现 @ 指向 ./source 的模块解析红灯。",
      "Stage B：只修配置后，增长率分母、排序副作用、相等值和日期函数未导出仍真实失败。",
      "Stage C：只补日期函数导出后，开始日和结束日排除测试仍失败。",
      "Stage D：应用完整修复后 71/71 项真实 Vitest 全部通过。",
      "配置修复：@ 别名改为真实 src，测试才能加载三个业务模块。",
      "指标修复：增长率以旧值为分母，避免经营指标失真。",
      "转换修复：排序不再修改调用方数组，相等值保持稳定顺序。",
      "筛选修复：日期函数可导入，并把起止日期纳入闭区间。",
      "metricsCalculator.js：statements 100%，branches 100%，lines 100%",
      "dataTransformer.js：statements 100%，branches 91.3%，lines 100%",
      "filterEngine.js：statements 100%，branches 97.5%，lines 100%",
      "清单一致：页面、test-manifest.json 与实际 collected IDs 同为 71 项。",
    ],
    review_guidance: "先确认三阶段红灯确实对应原缺陷，再复跑最终测试并审查 changes.patch；当前只是固定 qa-003 适配器，不是任意 JavaScript 沙箱。",
    execution_summary: "Agent 在隔离副本中先用同一套 71 项 Vitest 复现三阶段红灯，再修复四个真实文件并实现 71/71 通过；FORTE 原文件没有被覆盖。",
    self_test: selfTest,
    created_at: new Date().toISOString(),
    original_inputs_modified: false,
    review_required: true,
    external_action: "none",
  };
  return {
    ...base,
    workspace_artifacts: [{
      ...common,
      artifact_id: artifactIds[0],
      title: "看板工具库修复包",
      file_name: "看板工具库修复包.zip",
      media_type: "application/zip",
      size: 118000,
      summary: "完整 11 文件隔离副本、四文件真实 diff、三阶段红灯、71 项测试与逐文件覆盖率均可下载复查。",
      deliverable_type: "完整看板工具库隔离修复副本（ZIP）",
      download_path: `/v1/harness/runs/${base.run_id}/artifacts/${artifactIds[0]}`,
    }, {
      ...common,
      artifact_id: artifactIds[1],
      title: "TC-12 真实测试报告",
      file_name: "TC-12真实测试报告.md",
      media_type: "text/markdown",
      size: 6100,
      summary: "同一测试集先证明原缺陷，再验证修复后 71/71 通过和逐文件覆盖率门。",
      deliverable_type: "分阶段 Vitest、覆盖率与独立复跑报告（Markdown）",
      self_test: null,
      download_path: `/v1/harness/runs/${base.run_id}/artifacts/${artifactIds[1]}`,
    }],
    effect_receipts: [{
      receipt_id: "effect-receipt-121212121212",
      capability_id: "office-js-test-and-fix",
      scenario_id: "TC-12",
      status: "passed",
      state: "已冻结 qa-003 的完整 11 文件看板工具库，原始输入保持只读。",
      action: "复制到隔离 Run Workspace，用同一套 Vitest 分阶段复现红灯、修复并复跑。",
      observation: "生成 2 份真实成果文件，共享 12 项确定性检查，12/12 通过。",
      cost: "0 次额外模型调用；固定本地测试未联网安装依赖。",
      result: "修复包与真实测试报告可下载，等待人工代码评审与合并。",
      source_file_refs: sourceRefs,
      artifact_ids: artifactIds,
      prohibited_side_effects: ["不修改 FORTE 原始源码", "不运行来源 package scripts", "不访问真实 endpoint", "不自动创建 PR"],
      created_at: new Date().toISOString(),
      external_action: "none",
    }],
    last_event_sequence: 20,
  };
}

function failedDashboardToolkitEffectSnapshot(body: { workspace_id: string; instruction: string }) {
  const base = dashboardToolkitEffectSnapshot(body);
  const reviewGuidance = "当前包不得合并。请查看 dashboard-toolkit/evidence/stage-d-final-result.json、coverage-summary.json 和 independent-unpack-rerun.json；修复后重新启动一项新的 TC-12 Run。";
  const checks = base.workspace_artifacts[0].checks.map((check: { check_id: string; label: string; passed: boolean; detail: string }) => check.check_id === "check-tc12-final-green"
    ? { ...check, label: "最终测试命令未通过", passed: false, detail: "最终固定命令未通过；查看 stage-d-final-result.json 后重新启动新的 TC-12 Run。" }
    : check);
  return {
    ...base,
    status: "failed",
    workspace_artifacts: base.workspace_artifacts.map((artifact: Record<string, unknown>) => ({
      ...artifact,
      verifier_status: "failed",
      checks,
      summary: "隔离副本、统一 diff 和失败证据已保留；固定测试未通过，当前包不得合并。",
      statistic_basis: "完整 11/11 输入文件与分阶段失败证据；最终固定命令未通过，不形成测试全绿结论。",
      key_outputs: [
        "当前固定测试命令未完成全部验证，这不是测试全绿回执。",
        "当前包不得合并；隔离副本、统一 diff 和失败证据已经保留。",
        "请查看 Stage D 结果 JSON、coverage-summary.json 与独立复跑回执。",
        "修复执行环境或源码后，重新启动一项新的 TC-12 Run。",
      ],
      review_guidance: reviewGuidance,
      execution_summary: "固定测试命令未完成全部验证；当前包不得合并。FORTE 原文件没有被覆盖。",
      self_test: artifact.self_test ? {
        ...(artifact.self_test as Record<string, unknown>),
        expected_checks: [
          "当前 Stage D 或独立复跑未通过，不得把本轮标为测试全绿",
          "查看 evidence/stage-d-final-result.json 与对应 Vitest JSON",
          "查看 evidence/coverage-summary.json 与 independent-unpack-rerun.json",
          "修复后必须重新启动一项新的 TC-12 Run",
        ],
      } : null,
    })),
    effect_receipts: base.effect_receipts.map((receipt: Record<string, unknown>) => ({
      ...receipt,
      status: "failed",
      observation: "生成 2 份失败证据成果，共享 12 项确定性检查，其中最终固定命令未通过。",
      result: "固定命令失败，当前包不得合并；请查看阶段 JSON、coverage 和独立复跑回执。",
    })),
  };
}

function releaseReadinessEffectSnapshot(
  body: { workspace_id: string; instruction: string },
  options: { repairedF02?: boolean } = {},
) {
  const base = snapshot(body, "completed", 20);
  const artifactIds = ["workspace-artifact-111122223333", "workspace-artifact-444455556666"];
  const sourceRefs = [csvFile.file_ref, pdfFile.file_ref, docxFile.file_ref, txtFile.file_ref];
  const businessOutcome = structuredClone(tc11BusinessOutcome);
  const riskTotal = options.repairedF02 ? 7 : 8;
  const missingTotal = 5;
  if (options.repairedF02) {
    const severeGate = businessOutcome.gates.find((gate) => gate.gate_id === "business-gate-severe-zero")!;
    severeGate.numerator = 3;
    severeGate.actual = 3;
    severeGate.result = "3 项严重问题未清零，不满足上线条件。";
    const p0Metric = businessOutcome.auxiliary_metrics.find((metric) => metric.metric_id === "business-metric-p0-case-pass")!;
    p0Metric.numerator = 58;
    p0Metric.value = 95.1;
    const overallMetric = businessOutcome.auxiliary_metrics.find((metric) => metric.metric_id === "business-metric-overall-case-pass")!;
    overallMetric.numerator = 114;
    overallMetric.value = 90.5;
    const f02 = businessOutcome.records.find((record) => record.record_id === "F02")!;
    f02.test_status = "通过";
    f02.test_reason = "无";
    f02.passed_cases = f02.total_cases;
    f02.compatibility_issue_count = 0;
    f02.compatibility_issue_environments = [];
    f02.rules_hit = [];
    f02.base_risk_level = "none";
    f02.compatibility_risk_level = "none";
    f02.final_risk_level = "none";
    f02.affected_gate_ids = [];
  }
  const checks = [
    ["check-release-source-contract", "四份来源结构与交叉引用", "PRD 18 项、三张执行表各 13 项；表头、编号、名称、优先级、状态、数字和八环境均由服务端逐项校验。"],
    ["check-release-gate-formulas", "四项正式上线 Gate 逐式复算", "每项保留分子、分母、运算符、阈值、实际值和 PRD 来源规则；零分母会直接失败。"],
    ["check-release-risk-ledger", "逐功能风险按规则取唯一最高等级", "风险由 P0、原因类型和异常环境数推导；同一功能只保留最高等级。"],
    ["check-release-gate-aggregation", "上线结论由 Gate 聚合", "结论取决于四项 Gate 的布尔聚合，不检查固定功能名称或固定结论文案。"],
    ["check-release-auxiliary-separation", "辅助指标不冒充上线 Gate", "分级与综合用例通过率单独标为辅助指标。"],
    ["check-release-ledger-csv", "CSV 18 行与动态风险计数可独立复算", "台账一行一个 PRD 功能，各风险等级计数必须与服务端 records 一致。"],
    ["check-release-report-tables", "DOCX 包含结构化核验表与动态数量", `报告包含四项 Gate、辅助指标、18 项矩阵、${riskTotal} 项风险、${missingTotal} 项未提测和整改计划表。`],
    ["check-release-remediation", "整改项有负责人和退出条件", "每项整改绑定功能编号、研发负责人、来源问题、动作和可验证退出条件。"],
    ["check-release-no-action", "四份原件未改且没有外部动作", "生成前后重新读取四份 allowlisted 原件并逐字节比较；只在隔离运行工作区写入 DOCX/CSV，没有上线、配置写入或通知动作。"],
  ].map(([check_id, label, detail]) => ({ check_id, label, passed: true, detail }));
  const common = {
    capability_id: "office-release-readiness",
    scenario_id: "TC-11",
    version: 1,
    round_number: 1,
    source_file_refs: sourceRefs,
    validator_id: "validator-release-readiness-v2",
    verifier_status: "passed",
    checks,
    covered_period: "AIPilot Console v2.5 本次上线审核批次",
    statistic_basis: "PRD 18 项功能为全集；上线配置、功能测试和兼容测试各 13 项，按功能编号交叉核对并由 PRD 规则计算。",
    purpose: "支持发布负责人复核是否满足上线条件；不代替人工审批，不执行上线或修改配置。",
    record_count: 18,
    key_outputs: ["正式上线 Gate：4/4 未通过，结论为不得上线", `风险：严重 ${options.repairedF02 ? 3 : 4}、主要 2、次要 2`, `未提测功能：${missingTotal} 项`, "用例通过率是辅助质量指标，不作为正式上线 Gate"],
    key_outputs_label: "上线复核要点",
    review_guidance: `请由发布、研发和测试负责人逐项确认四条上线 Gate、${riskTotal} 项风险与 ${missingTotal} 项未提测功能；本次没有执行上线或修改配置。`,
    execution_summary: "已在隔离运行工作区生成并校验上线报告和逐功能台账；没有执行上线、没有修改配置。",
    business_gate_outcome: businessOutcome,
    created_at: new Date().toISOString(),
    original_inputs_modified: false,
    review_required: true,
    external_action: "none",
  };
  return {
    ...base,
    workspace_artifacts: [{
      ...common,
      artifact_id: artifactIds[0],
      title: "上线合规与风险报告",
      file_name: "上线合规与风险报告.docx",
      media_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      size: 28140,
      summary: `结构化报告包含正式 Gate、18 项矩阵、${riskTotal} 项风险、${missingTotal} 项未提测功能和整改计划。`,
      deliverable_type: "上线合规与风险报告 DOCX",
      download_path: `/v1/harness/runs/${base.run_id}/artifacts/${artifactIds[0]}`,
    }, {
      ...common,
      artifact_id: artifactIds[1],
      title: "上线功能风险逐项台账",
      file_name: "上线功能风险逐项台账.csv",
      media_type: "text/csv",
      size: 11840,
      summary: "18 行逐功能台账保留来源行、风险规则、Gate 影响、负责人和退出条件，可下载复算。",
      deliverable_type: "逐功能风险台账 CSV",
      download_path: `/v1/harness/runs/${base.run_id}/artifacts/${artifactIds[1]}`,
    }],
    effect_receipts: [{
      receipt_id: "effect-receipt-111122223333",
      capability_id: "office-release-readiness",
      scenario_id: "TC-11",
      status: "passed",
      state: "已冻结 4 份 FORTE 输入，原始文件保持只读。",
      action: "生成上线报告与逐功能风险台账，并执行 9 项确定性检查。",
      observation: "生成 2 份真实成果文件，共享 9 项确定性检查，9/9 通过。业务 Gate 4/4 未通过。",
      cost: "0 次额外模型调用；仅消耗本机确定性解析、计算与文件写入。",
      result: "确定性检查通过；业务 Gate 未通过，结论为“不得上线”。",
      source_file_refs: sourceRefs,
      artifact_ids: artifactIds,
      prohibited_side_effects: ["不执行上线", "不改配置"],
      business_gate_outcome: businessOutcome,
      created_at: new Date().toISOString(),
      external_action: "none",
    }],
    last_event_sequence: 20,
  };
}

function failedReleaseReadinessEffectSnapshot(body: { workspace_id: string; instruction: string }) {
  const base = releaseReadinessEffectSnapshot(body);
  const checks = base.workspace_artifacts[0].checks.map((check: { check_id: string; label: string; passed: boolean; detail: string }) => check.check_id === "check-release-report-tables"
    ? { ...check, passed: false, label: "DOCX 结构检查未通过", detail: "下载物未达到结构化报告门；当前成果不得作为可靠上线报告。" }
    : check);
  return {
    ...base,
    status: "failed",
    workspace_artifacts: base.workspace_artifacts.map((artifact: Record<string, unknown>) => ({
      ...artifact,
      verifier_status: "failed",
      checks,
      summary: "计算过程和失败证据已保留，但成果文件结构未通过确定性检查。",
      review_guidance: "当前成果不得作为可靠上线报告；请查看失败检查并重新启动新的 TC-11 Run。",
      execution_summary: "确定性文件检查失败；没有执行上线，也没有修改配置。",
    })),
    effect_receipts: base.effect_receipts.map((receipt: Record<string, unknown>) => ({
      ...receipt,
      status: "failed",
      observation: "两份成果中至少一项确定性文件检查未通过；失败证据已保留。",
      result: "当前成果不得作为可靠上线报告；没有执行上线或修改配置。",
    })),
  };
}

function boundedEffectSnapshot(body: { workspace_id: string; instruction: string }) {
  const base = snapshot(body, "completed", 18);
  return {
    ...base,
    workspace_artifacts: [],
    effect_receipts: [{
      receipt_id: "effect-receipt-222222222222",
      capability_id: "office-remote-sql-analysis",
      scenario_id: "TC-03",
      status: "blocked_external_boundary",
      state: "已识别用户目标并冻结当前公开资料库范围。",
      action: "检查外部 Connector、授权和稳定依赖。",
      observation: "所需外部依赖未获授权，未调用模型猜测外部数据。",
      cost: "0 次模型调用；0 个外部动作。",
      result: "按外部事实边界阻断；没有生成伪造结果。",
      source_file_refs: [],
      artifact_ids: [],
      prohibited_side_effects: ["不伪造 SQL 结果", "不连接未授权数据库"],
      created_at: new Date().toISOString(),
      external_action: "none",
    }],
    events: [
      ...base.events,
      { sequence: 17, event_name: "scenario_effect_bounded", occurred_at: new Date().toISOString(), status: "verifying", message: "按外部事实边界阻断；没有生成伪造结果。", details: {} },
    ],
    last_event_sequence: 18,
  };
}

function tableEvidenceReviewSnapshot(body: { workspace_id: string; instruction: string }) {
  const base: any = snapshot(body, "completed", 20);
  const original = base.result.findings[0];
  const tableFinding = {
    ...original,
    title: "超长客商期末余额需要复核",
    detail: "星海科技股份有限公司华东区域企业服务中心的期末余额需要结合方向与金额核对。",
    file_refs: [csvFile.file_ref],
    evidence_anchors: [{
      file_ref: csvFile.file_ref,
      role: "observed",
      label: "客商期末余额",
      locator_kind: "table_rows",
      start: 2,
      end: 2,
      excerpt: "星海科技股份有限公司华东区域企业服务中心 | 借 | 1,500,000.00",
    }],
  };
  return {
    ...base,
    result: { ...base.result, findings: [tableFinding] },
    rounds: base.rounds.map((round: any, index: number) => index === 0
      ? { ...round, result: { ...round.result, findings: [tableFinding] } }
      : round),
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
  const decisionRequests = [{
    decision_request_id: "request-111111111111",
    finding_id: "finding-333333333333",
    resolution_id: "resolution-111111111111",
    branch_id: branches[0].branch_id,
    source_revision: "rev-20260827-a",
    expected_version: 13,
    idempotency_ref: "idem-111111",
    candidate_ids: ["candidate-111111111111", "candidate-222222222222", ...(candidateCount >= 3 ? ["candidate-333333333333"] : [])],
    consequence: "只重跑受影响分支，不修改源文件，不执行外部动作。",
    state: "open",
  }];
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
    },
  };
  return {
    ...base,
    version: 13,
    last_event_sequence: 12,
    budget: { ...base.budget, rounds_used: 1, files_verified: 0, model_calls_used: 3, elapsed_ms: 6100 },
    rounds: [round],
    current_round: 1,
    decision_requests: decisionRequests,
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

function verifiedArtifactAuditPendingSnapshot(body: { workspace_id: string; instruction: string }, distinctDetails = false) {
  const base = sourceLocationRecoverySnapshot(body);
  const effect = verifiedEffectSnapshot(body);
  const branches = base.branches.map((branch, index) => ({
    ...branch,
    title: index === 0 ? "读取入职物资权限软件分配规则" : "生成入职资产匹配表",
    objective: index === 0 ? "核对岗位分类和备注覆盖规则" : "按时间表和规则形成成果",
    input_file_refs: index === 0 ? [pdfFile.file_ref] : [csvFile.file_ref, pdfFile.file_ref],
    verified_file_refs: index === 0 ? [] : [csvFile.file_ref],
    missing_file_refs: [pdfFile.file_ref],
  }));
  const gaps = branches.map((branch, index) => ({
    gap_id: `gap-onboarding-${String(index + 1).padStart(4, "0")}`,
    branch_id: branch.branch_id,
    label: `“${branch.title}”的规则原文尚未定位`,
    detail: distinctDetails && index === 1
      ? "PDF 中另一条规则缺少独立的可回开位置。"
      : "PDF 安全预览中的版面换行导致 Agent 引用未能逐字匹配。",
    candidate_file_refs: [pdfFile.file_ref],
  }));
  const round = {
    ...base.rounds[0],
    question: body.instruction,
    input_file_refs: [csvFile.file_ref, pdfFile.file_ref],
    branch_ids: branches.map((branch) => branch.branch_id),
    evidence_gaps: gaps,
    next_step: {
      ...base.rounds[0].next_step,
      reason: "成果检查已经通过；Agent 的规则说明仍缺少一个可回开的原文位置。",
      candidate_file_refs: [pdfFile.file_ref],
      candidate_branch_ids: branches.map((branch) => branch.branch_id),
      evidence_resolutions: [],
      decision_requests: [],
    },
  };
  const artifact = {
    ...effect.workspace_artifacts[0],
    capability_id: "office-onboarding-assets",
    scenario_id: "TC-01",
    title: "入职资产匹配表",
    file_name: "入职资产匹配表.csv",
    source_file_refs: [csvFile.file_ref, pdfFile.file_ref],
    checks: [
      { check_id: "check-onboarding-date", label: "日期范围", passed: true, detail: "仅保留 3 月 20 日至 4 月 20 日的九名员工。" },
      { check_id: "check-onboarding-columns", label: "列结构", passed: true, detail: "成果包含员工、资产、权限和工位列。" },
      { check_id: "check-onboarding-mapping", label: "分配规则", passed: true, detail: "岗位分类与 PDF 优先级规则均已核对。" },
      { check_id: "check-onboarding-notes", label: "备注覆盖", passed: true, detail: "多条特殊备注均已生效。" },
      { check_id: "check-onboarding-readonly", label: "原文件只读", passed: true, detail: "原始 FORTE 输入没有被修改。" },
    ],
  };
  return {
    ...base,
    rounds: [round],
    branches,
    decision_requests: [],
    workspace_artifacts: [artifact],
    effect_receipts: [{
      ...effect.effect_receipts[0],
      capability_id: "office-onboarding-assets",
      scenario_id: "TC-01",
      source_file_refs: [csvFile.file_ref, pdfFile.file_ref],
      artifact_ids: [artifact.artifact_id],
      observation: "生成 1 份真实成果文件，执行 5 项确定性检查。",
      result: "5 项确定性效果门通过；Agent 来源说明仍需补齐定位。",
    }],
    artifact_versions: [{
      ...base.artifact_versions[0],
      summary: round.next_step.reason,
      evidence_gaps: gaps,
      source_file_refs: [csvFile.file_ref],
    }],
  };
}

function verifiedFinanceArtifactAuditPendingSnapshot(body: { workspace_id: string; instruction: string }) {
  const base = verifiedArtifactAuditPendingSnapshot(body);
  const effect = verifiedEffectSnapshot(body);
  const branches = base.branches.map((branch, index) => ({
    ...branch,
    title: index === 0 ? "核对 2026 未付说明" : "核对 2026 未收说明",
    objective: index === 0 ? "核对未付明细说明所依据的原表格位置" : "核对未收明细说明所依据的原表格位置",
    input_file_refs: [csvFile.file_ref],
    verified_file_refs: [],
    missing_file_refs: [csvFile.file_ref],
  }));
  const gaps = branches.map((branch, index) => ({
    gap_id: `gap-finance-${String(index + 1).padStart(4, "0")}`,
    branch_id: branch.branch_id,
    label: `“${branch.title}”的原表格位置尚未找到`,
    detail: "Agent 已引用 2026 往来明细，但没有返回可唯一跳转到行或单元格的位置。",
    candidate_file_refs: [csvFile.file_ref],
  }));
  const round = {
    ...base.rounds[0],
    question: body.instruction,
    input_file_refs: [csvFile.file_ref],
    branch_ids: branches.map((branch) => branch.branch_id),
    evidence_gaps: gaps,
    next_step: {
      ...base.rounds[0].next_step,
      reason: "成果检查已经通过；一条 Agent 说明仍缺少可跳转到原表格的具体位置。",
      candidate_file_refs: [csvFile.file_ref],
      candidate_branch_ids: branches.map((branch) => branch.branch_id),
    },
  };
  return {
    ...base,
    rounds: [round],
    branches,
    workspace_artifacts: effect.workspace_artifacts,
    effect_receipts: effect.effect_receipts,
    artifact_versions: [{
      ...base.artifact_versions[0],
      summary: round.next_step.reason,
      evidence_gaps: gaps,
      source_file_refs: [csvFile.file_ref],
    }],
  };
}

function unverifiedArtifactLocationPendingSnapshot(body: { workspace_id: string; instruction: string }) {
  const base = verifiedFinanceArtifactAuditPendingSnapshot(body);
  const branch = { ...base.branches[0], status: "waiting_input" };
  const gap = base.rounds[0].evidence_gaps[0];
  const round = {
    ...base.rounds[0],
    branch_ids: [branch.branch_id],
    evidence_gaps: [gap],
    next_step: {
      ...base.rounds[0].next_step,
      reason: "相关文件已经找到，但说明尚未定位到具体行或单元格，成果仍需继续检查。",
      candidate_branch_ids: [branch.branch_id],
    },
  };
  return {
    ...base,
    workspace_artifacts: [],
    effect_receipts: [],
    branches: [branch],
    rounds: [round],
    artifact_versions: [],
  };
}

function terminalArtifactLocationPendingSnapshot(body: { workspace_id: string; instruction: string }) {
  const base = unverifiedArtifactLocationPendingSnapshot(body);
  const branch = { ...base.branches[0], status: "stopped" };
  const round = {
    ...base.rounds[0],
    branch_ids: [branch.branch_id],
    next_step: {
      ...base.rounds[0].next_step,
      decision: "budget_exhausted",
      reason: "旧任务已到预算边界，说明的原表格位置尚未找到。",
      candidate_branch_ids: [branch.branch_id],
    },
  };
  return {
    ...base,
    status: "stopped",
    control_state: "stopped",
    branches: [branch],
    rounds: [round],
    budget: { ...base.budget, stop_reason: "Agent 执行时间预算已耗尽" },
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

async function mockHarness(page: Page, options: { failFirstStart?: boolean; failDecisionDefer?: boolean; disconnect?: boolean; failed?: boolean; locationFailure?: boolean; sourceRecovery?: boolean; sourceRecoveryThreeCandidates?: boolean; verifiedArtifactAuditPending?: boolean; verifiedArtifactAuditPendingDistinct?: boolean; verifiedFinanceArtifactAuditPending?: boolean; unverifiedArtifactLocationPending?: boolean; terminalArtifactLocationPending?: boolean; boundedRecovery?: boolean; effectArtifact?: boolean; outboundEffect?: boolean; reactEffect?: boolean; evaluationEffect?: boolean; dashboardEffect?: boolean; dashboardEffectFailed?: boolean; releaseEffect?: boolean; releaseEffectRepaired?: boolean; releaseEffectFailed?: boolean; effectBoundary?: boolean; reviewTable?: boolean; workspaceFailures?: number; interactiveLoop?: boolean; evidenceGate?: boolean } = {}) {
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
    if (path.includes("/artifacts/") && route.request().method() === "GET") {
      if (options.outboundEffect) return route.fulfill({ status: 200, contentType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", body: "mock-docx-bytes", headers: { "Content-Disposition": "attachment; filename*=UTF-8''%E5%A4%96%E5%91%BC%E6%B5%81%E7%A8%8B-M1%E9%80%BE%E6%9C%9F%E7%94%A8%E6%88%B7AI%E5%A4%96%E5%91%BC%E5%82%AC%E6%94%B6%E6%B5%81%E7%A8%8B%E5%9B%BE.docx" } });
      if (options.reactEffect) return route.fulfill({ status: 200, contentType: "application/zip", body: "mock-zip-bytes" });
      if (options.evaluationEffect) return route.fulfill({ status: 200, contentType: "application/zip", body: "mock-evaluation-zip-bytes", headers: { "Content-Disposition": "attachment; filename*=UTF-8''%E8%AF%84%E6%B5%8B%E5%B9%B3%E5%8F%B0%E7%9C%9F%E5%AE%9E%E4%BF%AE%E5%A4%8D%E5%8C%85.zip" } });
      if (options.dashboardEffect) return route.fulfill({ status: 200, contentType: "application/zip", body: "mock-dashboard-zip-bytes", headers: { "Content-Disposition": "attachment; filename*=UTF-8''%E7%9C%8B%E6%9D%BF%E5%B7%A5%E5%85%B7%E5%BA%93%E4%BF%AE%E5%A4%8D%E5%8C%85.zip" } });
      return route.fulfill({ status: 200, contentType: "text/csv; charset=utf-8", body: "科目名称,客商名称,未付款项\n应付账款,星海科技,100.00\n", headers: { "Content-Disposition": "attachment; filename*=UTF-8''%E6%9C%AA%E4%BB%98%E7%BB%9F%E8%AE%A1.csv" } });
    }
    if (path === "/v1/harness/runs" && route.request().method() === "GET") {
      return fulfillJson(route, { runs: [] });
    }
    if (path === "/v1/harness/runs" && route.request().method() === "POST") {
      startCalls += 1;
      const body = route.request().postDataJSON() as typeof currentBody & { idempotency_key: string };
      currentBody = body; starts.push(body);
      if (options.failFirstStart && startCalls === 1) return fulfillJson(route, { detail: "任务启动结果未知" }, 503);
      currentSnapshot = options.terminalArtifactLocationPending
        ? terminalArtifactLocationPendingSnapshot(body)
        : options.unverifiedArtifactLocationPending
          ? unverifiedArtifactLocationPendingSnapshot(body)
        : options.verifiedFinanceArtifactAuditPending
          ? verifiedFinanceArtifactAuditPendingSnapshot(body)
      : options.verifiedArtifactAuditPending || options.verifiedArtifactAuditPendingDistinct
        ? verifiedArtifactAuditPendingSnapshot(body, options.verifiedArtifactAuditPendingDistinct)
        : options.reviewTable
        ? tableEvidenceReviewSnapshot(body)
        : options.effectArtifact
        ? verifiedEffectSnapshot(body)
        : options.outboundEffect
        ? outboundEffectSnapshot(body)
        : options.reactEffect
        ? reactRefactorEffectSnapshot(body)
        : options.evaluationEffect
        ? evaluationPlatformEffectSnapshot(body)
        : options.dashboardEffectFailed
        ? failedDashboardToolkitEffectSnapshot(body)
        : options.dashboardEffect
        ? dashboardToolkitEffectSnapshot(body)
        : options.releaseEffectFailed
          ? failedReleaseReadinessEffectSnapshot(body)
        : options.releaseEffectRepaired
          ? releaseReadinessEffectSnapshot(body, { repairedF02: true })
        : options.releaseEffect
        ? releaseReadinessEffectSnapshot(body)
        : options.effectBoundary
          ? boundedEffectSnapshot(body)
        : options.locationFailure
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
      if (command === "decision" && control.decision_action === "defer" && options.failDecisionDefer) {
        return fulfillJson(route, { detail: "待决项版本已经变化，暂缓回执未写入；页面已刷新到最新状态。" }, 409);
      }
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
      if (options.interactiveLoop || options.evidenceGate || options.sourceRecovery || options.verifiedArtifactAuditPending || options.verifiedArtifactAuditPendingDistinct || options.verifiedFinanceArtifactAuditPending || options.unverifiedArtifactLocationPending || options.terminalArtifactLocationPending || options.boundedRecovery) {
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
      if (options.interactiveLoop || options.evidenceGate || options.sourceRecovery || options.verifiedArtifactAuditPending || options.verifiedArtifactAuditPendingDistinct || options.verifiedFinanceArtifactAuditPending || options.unverifiedArtifactLocationPending || options.terminalArtifactLocationPending || options.boundedRecovery || options.locationFailure || options.effectArtifact || options.outboundEffect || options.reactEffect || options.evaluationEffect || options.dashboardEffect || options.dashboardEffectFailed || options.releaseEffect || options.releaseEffectRepaired || options.releaseEffectFailed || options.effectBoundary) return fulfillJson(route, currentSnapshot);
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
    loop: { max_rounds: 12, max_files_per_round: 16, max_model_calls: 30, deadline_seconds: 7200 },
  });
  expect(state.starts[0]).not.toHaveProperty("selected_file_refs");
  await expect(page.getByText("规划模型")).toBeVisible();
  await expect(page.getByText("分析模型")).toBeVisible();
  await expect(page.locator(".loop-view").getByRole("heading", { name: instruction })).toBeVisible();
  await page.getByRole("button", { name: /第 1 轮/ }).click();
  await expect(page.getByText("Agent 本轮自主选择")).toBeVisible();
  await expect(page.getByText("文件名与摘要直接涉及当前目标，先读取这些最小证据。")).toBeVisible();
  await expect(page.getByText("待处理分支")).toBeVisible();
  await expect(page.locator(".loop-round-detail > footer strong")).toHaveText("等待人工输入");
  await expect(page.locator(".loop-branches")).toContainText("任务分支现场");
  await expect(page.locator(".loop-branches")).toContainText("形成分析结果");
  await expect(page.locator(".artifact-evolution")).toContainText("不可变成果历史");
  await expect(page.locator(".artifact-evolution")).toContainText("当前 v2");
  await page.getByRole("button", { name: /发现与建议/ }).click();
  await expect(page.getByRole("heading", { name: /完成 2 轮/ })).toBeVisible();
  expect(await page.locator("body").innerText()).not.toContain("forte-");
});

test("shows a real run-workspace file, deterministic checks and a download", async ({ page }) => {
  await mockHarness(page, { effectArtifact: true });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对三期往来明细，生成未付统计、未收统计，并判断是否存在僵尸账款。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const artifacts = page.locator(".workspace-artifacts");
  await expect(artifacts).toContainText("Agent 已生成 3 份真实成果文件");
  await expect(artifacts).toContainText("2026 期末未付明细");
  await expect(artifacts).toContainText("2026 期末未收明细");
  await expect(artifacts).toContainText("三期僵尸账款核对说明");
  await expect(artifacts).toContainText("3 份成果共 7 项唯一确定性检查，7/7 通过");
  await expect(artifacts).toContainText("涵盖期间");
  await expect(artifacts).toContainText("统计口径");
  await expect(artifacts).toContainText("用途");
  await expect(artifacts).toContainText("31 条记录");
  await expect(artifacts).toContainText("2 条记录");
  await expect(artifacts).toContainText("不是三期合并表");
  await expect(artifacts).toContainText("2025 年上半年、2025 年下半年、2026 年");
  await expect(artifacts).toContainText("1 份内容来源");
  await expect(artifacts).toContainText("3 份内容来源");
  await expect(artifacts).toContainText("原始 FORTE 文件没有被修改");
  await artifacts.getByText("查看逐项检查").first().click();
  await expect(artifacts).toContainText("31 条贷方期末余额逐行相等");
  await artifacts.getByText("查看效果回执").click();
  await expect(artifacts).toContainText("0 次额外模型调用");

  const downloadPromise = page.waitForEvent("download");
  await artifacts.getByRole("button", { name: "下载成果" }).first().click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("未付统计.csv");

  if (process.env.CAPTURE_SCENARIO_EFFECT_GATE === "1") {
    await page.screenshot({ path: "../../docs/evidence/screenshots/scenario-effect-gate-desktop.png", fullPage: true });
    await artifacts.screenshot({ path: "../../docs/evidence/screenshots/scenario-effect-gate-artifact-desktop.png" });
  }
  if (process.env.CAPTURE_DR0037_EVIDENCE === "1") {
    await artifacts.screenshot({ path: "../../docs/evidence/screenshots/dr-0037-tc05-artifact-semantics-desktop.png" });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  const metrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(metrics.scroll).toBeLessThanOrEqual(metrics.viewport);
  const artifactMetrics = await artifacts.evaluate((element) => ({ width: element.clientWidth, scroll: element.scrollWidth }));
  expect(artifactMetrics.scroll).toBeLessThanOrEqual(artifactMetrics.width);
  if (process.env.CAPTURE_DR0037_EVIDENCE === "1") {
    await artifacts.screenshot({ path: "../../docs/evidence/screenshots/dr-0037-tc05-artifact-semantics-mobile.png" });
  }
  if (process.env.CAPTURE_SCENARIO_EFFECT_GATE === "1") {
    await artifacts.screenshot({ path: "../../docs/evidence/screenshots/scenario-effect-gate-artifact-mobile.png" });
    await page.screenshot({ path: "../../docs/evidence/screenshots/scenario-effect-gate-mobile.png", fullPage: true });
  }
});

test("distinguishes a TC-10 flow document from real outbound execution", async ({ page }) => {
  await mockHarness(page, { outboundEffect: true });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("根据专业性说明生成信用卡 M1 逾期用户 AI 外呼催收流程图文档。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const artifacts = page.locator(".workspace-artifacts");
  const actionBoundary = page.locator(".workspace-action-result");
  const conclusion = page.locator(".loop-effect-conclusion");
  await expect(artifacts).toContainText("Agent 已生成 1 份真实成果文件");
  await expect(actionBoundary).toContainText("这次实际发生了什么");
  await expect(actionBoundary).toContainText("本次只生成流程设计 DOCX");
  await expect(actionBoundary).toContainText("流程节点描述，不是执行回执");
  await expect(actionBoundary).toContainText("实际没有拨号、没有写 CRM、没有发送短信");
  await expect(actionBoundary).toContainText("不拨号");
  await expect(actionBoundary).toContainText("不写 CRM");
  await expect(actionBoundary).toContainText("不发送短信");

  await expect(artifacts).toContainText("成果类型");
  await expect(artifacts).toContainText("流程设计 DOCX");
  await expect(artifacts).toContainText("适用范围");
  await expect(artifacts).toContainText("信用卡 M1 逾期阶段");
  await expect(artifacts).toContainText("采用依据");
  await expect(artifacts).toContainText("《专业性说明.md》");
  await expect(artifacts).toContainText("使用边界");
  await expect(artifacts).toContainText("6 类关键终态");
  for (const state of ["PTP登记", "转人工跟进", "安排重拨", "停止外呼（达上限）", "加入禁呼名单", "案件升级"]) {
    await expect(artifacts).toContainText(state);
  }
  await expect(artifacts).toContainText("为什么仍需人工复核");
  await expect(artifacts).toContainText("业务与合规负责人复核当前制度口径、话术和实际系统接入方案");
  await artifacts.getByText("查看逐项检查").click();
  await expect(artifacts).toContainText("13/13 项检查");
  await expect(artifacts).toContainText("每日 3 次 / 每小时 1 次上限");
  await expect(artifacts).toContainText("外部动作均未发生");

  await expect(conclusion).toContainText("本次任务结语");
  await expect(conclusion).toContainText("本次只生成流程设计 DOCX");
  await expect(conclusion).toContainText("13/13 项规则检查通过");

  const downloadPromise = page.waitForEvent("download");
  await artifacts.getByRole("button", { name: "下载成果" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("外呼流程-M1逾期用户AI外呼催收流程图.docx");

  const actionHeadingSize = await actionBoundary.locator("h4").evaluate((element) => Number.parseFloat(getComputedStyle(element).fontSize));
  expect(actionHeadingSize).toBeGreaterThanOrEqual(14);
  if (process.env.CAPTURE_TC10_EFFECT_EVIDENCE === "1") {
    await artifacts.screenshot({ path: "../../docs/evidence/screenshots/tc10-outbound-effect-desktop.png" });
    await conclusion.screenshot({ path: "../../docs/evidence/screenshots/tc10-outbound-conclusion-desktop.png" });
  }

  await page.setViewportSize({ width: 390, height: 844 });
  const pageMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  const artifactMetrics = await artifacts.evaluate((element) => ({ width: element.clientWidth, scroll: element.scrollWidth }));
  expect(pageMetrics.scroll).toBeLessThanOrEqual(pageMetrics.viewport);
  expect(artifactMetrics.scroll).toBeLessThanOrEqual(artifactMetrics.width);
  await expect(actionBoundary).toContainText("实际没有拨号、没有写 CRM、没有发送短信");
  if (process.env.CAPTURE_TC10_EFFECT_EVIDENCE === "1") {
    await artifacts.screenshot({ path: "../../docs/evidence/screenshots/tc10-outbound-effect-mobile.png" });
  }
});

test("explains the real TC-02 project copy, diff, self-test and merge boundary", async ({ page }) => {
  await mockHarness(page, { reactEffect: true });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("把搜索 Agent 从固定 Workflow 重构为带迭代上限和轨迹的 ReAct 结构。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const artifacts = page.locator(".workspace-artifacts");
  const selfTest = page.locator(".workspace-artifact-self-test");
  await expect(artifacts).toContainText("Agent 已生成 2 份真实成果文件");
  await expect(artifacts).toContainText("2 份成果共享 12 项确定性检查，12/12 通过");
  await expect(artifacts).not.toContainText("24/24");
  await expect(artifacts).not.toContainText("执行 24 项");
  await expect(artifacts.locator(".workspace-artifact-status")).toHaveCount(2);
  await expect(artifacts.locator(".workspace-artifact-status").first()).toContainText("使用同一验证清单");
  await expect(page.locator(".loop-effect-conclusion")).toContainText("2 份成果共享 12 项规则检查，12/12 通过");
  await expect(page.locator(".workspace-effect-receipt")).toContainText("生成 2 份真实成果文件，共享 12 项确定性检查，12/12 通过");
  await expect(artifacts).toContainText("algorithm-013 有界 ReAct 控制结构代码包");
  await expect(artifacts).toContainText("完整可运行项目副本");
  await expect(artifacts).toContainText("测试回执与改动说明");
  await expect(artifacts).toContainText("不会覆盖 FORTE 原文件");
  await expect(artifacts).toContainText("固定五节点");
  await expect(artifacts).toContainText("action/observation");
  await expect(artifacts).toContainText("action_policy 可替换");
  await expect(artifacts).toContainText("未证明包内模型自主 ReAct");
  await expect(artifacts).toContainText("外层 Planner/Analyst 不是包内 action policy");
  await expect(artifacts).toContainText("文件变更");
  await expect(artifacts).not.toContainText("4 类关键终态");
  await expect(artifacts).toContainText("runner 不具备 OS 级 socket 隔离");

  await expect(selfTest).toContainText("下载后可以自己验证");
  await expect(selfTest).toContainText("TC-02 自测卡");
  await expect(selfTest).toContainText("python -m compileall -q search_agent_workflow");
  await expect(selfTest).toContainText("python -m unittest discover -s search_agent_workflow/tests -v");
  await expect(selfTest.getByText("查看应通过的测试与失败信号")).toBeVisible();
  await selfTest.getByText("查看应通过的测试与失败信号").click();
  await expect(selfTest).toContainText("真实 ToolRegistry 调用");
  await expect(selfTest).toContainText("main.py 仍只调用 SearchWorkflow");

  const downloadPromise = page.waitForEvent("download");
  await artifacts.getByRole("button", { name: "下载成果" }).first().click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("search-agent-react-refactor.zip");

  const commandSize = await selfTest.locator("code").first().evaluate((element) => Number.parseFloat(getComputedStyle(element).fontSize));
  expect(commandSize).toBeGreaterThanOrEqual(10);
  if (process.env.CAPTURE_TC02_EFFECT_EVIDENCE === "1") {
    await page.setViewportSize({ width: 1440, height: 1000 });
    const evidenceStyle = await page.addStyleTag({ content: `
      html, body, .harness-app-shell { height: auto !important; overflow: visible !important; }
      .harness-app-shell { display: block !important; }
      .harness-workspace-shell { overflow: visible !important; }
      .harness-agent-shell, .harness-app-divider, .dataset-browser { display: none !important; }
      .data-workbench { width: 1400px !important; }
      .data-workbench-grid { grid-template-columns: minmax(0, 1fr) !important; }
    ` });
    await artifacts.screenshot({ path: "../../docs/evidence/screenshots/tc02-real-project-refactor-desktop.png" });
    await evidenceStyle.evaluate((element) => element.parentNode?.removeChild(element));
  }

  await page.setViewportSize({ width: 390, height: 844 });
  const pageMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  const artifactMetrics = await artifacts.evaluate((element) => ({ width: element.clientWidth, scroll: element.scrollWidth }));
  expect(pageMetrics.scroll).toBeLessThanOrEqual(pageMetrics.viewport);
  expect(artifactMetrics.scroll).toBeLessThanOrEqual(artifactMetrics.width);
  await expect(selfTest).toContainText("TC-02 自测卡");
  if (process.env.CAPTURE_TC02_EFFECT_EVIDENCE === "1") {
    await artifacts.screenshot({ path: "../../docs/evidence/screenshots/tc02-real-project-refactor-mobile.png" });
  }
});

test("shows the real TC-04 project tests, per-file coverage and manual merge boundary", async ({ page }) => {
  await mockHarness(page, { evaluationEffect: true });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("为评测平台补充单元测试，覆盖 Service、执行引擎和工具类；真实运行测试，修复失败，并给出覆盖率与修改文件。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const artifacts = page.locator(".workspace-artifacts");
  const selfTest = page.getByRole("region", { name: "TC-04 自测卡" });
  const testSuites = page.getByRole("region", { name: "真实测试清单" });
  await expect(artifacts).toContainText("Agent 已生成 2 份真实成果文件");
  await expect(artifacts).toContainText("2 份成果共享 12 项确定性检查，12/12 通过");
  await expect(artifacts).not.toContainText("24/24");
  await expect(artifacts).toContainText("评测平台修复包");
  await expect(artifacts).toContainText("TC-04 真实测试报告");
  await expect(artifacts).toContainText("完整真实工程隔离副本");
  await expect(artifacts).toContainText("完整 44 文件隔离副本");
  await expect(artifacts).toContainText("44 份内容来源");
  await expect(artifacts).toContainText("117/117 通过");
  await expect(artifacts).toContainText("model_service.py 97.9%");
  await expect(artifacts).toContainText("dataset_service.py 97.8%");
  await expect(artifacts).toContainText("evaluation_engine.py 89.2%");
  await expect(artifacts).toContainText("FORTE 原件未覆盖");
  await expect(artifacts).toContainText("未自动创建 PR");
  await expect(page.locator(".workspace-action-result")).toContainText("未修复完整副本先出现 5 个红灯");
  await expect(page.locator(".loop-effect-conclusion")).toContainText("三份变更源码覆盖率均超过 80%");

  await expect(selfTest).toContainText("TC-04 自测卡");
  await expect(selfTest).not.toContainText("TC-02 自测卡");
  await expect(selfTest).toContainText("python -m compileall -q app tests run_self_test.py");
  await expect(selfTest).toContainText("python run_self_test.py");
  await expect(testSuites).toContainText("117 项");
  await expect(testSuites).toContainText("页面测试 ID、evaluation-platform/test-manifest.json 与实际 collected IDs 是同一集合");
  for (const [label, count, files, representative] of [
    ["模型 Service", "15 项", "tests/test_model_service.py · tests/test_model_service_matrix.py", "test_model_service.ModelServiceTests.test_delete_rejects_running_experiment"],
    ["数据集 Service", "16 项", "tests/test_dataset_service.py · tests/test_dataset_service_matrix.py", "test_dataset_service.DatasetServiceTests.test_append_uses_next_sequence_after_current_maximum"],
    ["实验 Service", "15 项", "tests/test_experiment_service.py · tests/test_experiment_service_matrix.py", "test_experiment_service.ExperimentServiceTests.test_create_experiment_commits_and_starts_real_engine_contract"],
    ["执行引擎", "23 项", "tests/test_evaluation_engine.py · tests/test_evaluation_engine_matrix.py", "test_evaluation_engine.EvaluationEngineTests.test_execute_never_exceeds_experiment_concurrency"],
    ["工具类与事务", "48 项", "tests/test_utils.py · tests/test_utils_boundaries.py", "test_utils.UtilityTests.test_rollback_is_isolated_from_a_new_session"],
  ] as const) {
    const suite = testSuites.locator("details").filter({ hasText: label });
    await expect(suite).toContainText(count);
    await expect(suite).toContainText(files);
    await suite.locator("summary").click();
    await expect(suite).toContainText(representative);
    await suite.locator("summary").click();
  }
  const testListType = await testSuites.evaluate((element) => ({
    explanation: Number.parseFloat(getComputedStyle(element.querySelector(":scope > header p")!).fontSize),
    suiteTitle: Number.parseFloat(getComputedStyle(element.querySelector("summary b")!).fontSize),
    suiteCount: Number.parseFloat(getComputedStyle(element.querySelector("summary strong")!).fontSize),
    fileName: Number.parseFloat(getComputedStyle(element.querySelector("summary small")!).fontSize),
    testId: Number.parseFloat(getComputedStyle(element.querySelector("ol code")!).fontSize),
  }));
  expect(testListType.explanation).toBeGreaterThanOrEqual(11);
  expect(testListType.suiteTitle).toBeGreaterThanOrEqual(12);
  expect(testListType.suiteCount).toBeGreaterThanOrEqual(12);
  expect(testListType.fileName).toBeGreaterThanOrEqual(11);
  expect(testListType.testId).toBeGreaterThanOrEqual(11);
  await selfTest.getByText("查看应通过的测试与失败信号").click();
  await expect(selfTest).toContainText("模型 Service 15 项");
  await expect(selfTest).toContainText("执行引擎 23 项");
  await expect(selfTest).toContainText("工具类与事务 48 项");
  await expect(selfTest).toContainText("任一变更源码覆盖率低于 80%");

  await artifacts.getByText("查看逐项检查").first().click();
  await expect(artifacts).toContainText("修复前先复现缺陷");
  await expect(artifacts).toContainText("117 个具名测试与 manifest 完全一致");

  const downloadPromise = page.waitForEvent("download");
  await artifacts.getByRole("button", { name: "下载成果" }).first().click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("评测平台真实修复包.zip");

  const commandSize = await selfTest.locator("code").first().evaluate((element) => Number.parseFloat(getComputedStyle(element).fontSize));
  expect(commandSize).toBeGreaterThanOrEqual(10);
  if (process.env.CAPTURE_TC04_EFFECT_EVIDENCE === "1") {
    await page.setViewportSize({ width: 1440, height: 1100 });
    await artifacts.scrollIntoViewIfNeeded();
    await page.screenshot({ path: "../../docs/evidence/screenshots/tc04-real-platform-tests-desktop.png" });
    const evidenceStyle = await page.addStyleTag({ content: `
      .harness-app-shell { display: block !important; }
      .harness-workspace-shell { overflow: visible !important; }
      .harness-agent-shell, .harness-app-divider, .dataset-browser { display: none !important; }
      .data-workbench { width: 1400px !important; }
      .data-workbench-grid { grid-template-columns: minmax(0, 1fr) !important; }
      .workspace-artifacts { align-self: start !important; height: max-content !important; }
    ` });
    const evidenceHeight = await artifacts.evaluate((element) => element.scrollHeight);
    await page.setViewportSize({ width: 1440, height: Math.min(6000, evidenceHeight + 40) });
    await artifacts.screenshot({ path: "../../docs/evidence/screenshots/tc04-real-platform-tests-artifact-focus.png" });
    await evidenceStyle.evaluate((element) => element.parentNode?.removeChild(element));
  }

  await page.setViewportSize({ width: 390, height: 844 });
  const pageMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  const artifactMetrics = await artifacts.evaluate((element) => ({ width: element.clientWidth, scroll: element.scrollWidth }));
  expect(pageMetrics.scroll).toBeLessThanOrEqual(pageMetrics.viewport);
  expect(artifactMetrics.scroll).toBeLessThanOrEqual(artifactMetrics.width);
  await expect(selfTest).toContainText("TC-04 自测卡");
  await expect(testSuites).toContainText("117 项");
  await testSuites.locator("details").filter({ hasText: "工具类与事务" }).locator("summary").click();
  await expect(testSuites).toContainText("test_utils.UtilityTests.test_rollback_is_isolated_from_a_new_session");
  const suiteMetrics = await testSuites.evaluate((element) => ({ width: element.clientWidth, scroll: element.scrollWidth }));
  expect(suiteMetrics.scroll).toBeLessThanOrEqual(suiteMetrics.width);
  if (process.env.CAPTURE_TC04_EFFECT_EVIDENCE === "1") {
    await artifacts.screenshot({ path: "../../docs/evidence/screenshots/tc04-real-platform-tests-mobile.png" });
  }
});

test("shows TC-12 real Vitest red-to-green evidence and the exact public manifest", async ({ page }) => {
  await mockHarness(page, { dashboardEffect: true });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("为三个看板工具模块编写 Vitest，修复源码并真实运行测试。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const artifacts = page.locator(".workspace-artifacts");
  const selfTest = page.getByRole("region", { name: "TC-12 自测卡" });
  const testSuites = page.getByRole("region", { name: "真实测试清单" });
  await expect(artifacts).toContainText("Agent 已生成 2 份真实成果文件");
  await expect(artifacts).toContainText("2 份成果共享 12 项确定性检查，12/12 通过");
  await expect(artifacts).not.toContainText("24/24");
  await expect(artifacts).toContainText("看板工具库修复包");
  await expect(artifacts).toContainText("TC-12 真实测试报告");
  await expect(artifacts).toContainText("完整 11 文件隔离副本");
  await expect(artifacts).toContainText("11 份内容来源");
  await expect(page.locator(".workspace-action-result")).toContainText("同一套 71 项 Vitest 复现三阶段红灯");
  for (const statement of [
    "Stage A：原配置真实复现 @ 指向 ./source 的模块解析红灯",
    "Stage B：只修配置后",
    "Stage C：只补日期函数导出后",
    "Stage D：应用完整修复后 71/71 项真实 Vitest 全部通过",
    "增长率以旧值为分母",
    "排序不再修改调用方数组",
    "起止日期纳入闭区间",
    "metricsCalculator.js：statements 100%",
    "dataTransformer.js：statements 100%，branches 91.3%",
    "filterEngine.js：statements 100%，branches 97.5%",
  ]) await expect(artifacts).toContainText(statement);
  await expect(artifacts).toContainText("不会自动创建或合并 PR");
  await expect(artifacts).toContainText("固定 qa-003 适配器，不是任意 JavaScript 沙箱");

  await expect(selfTest).toContainText("node dashboard-toolkit/run-self-test.mjs apps/web/node_modules/vitest/vitest.mjs");
  await expect(testSuites).toContainText("71 项");
  await expect(testSuites).toContainText("页面测试 ID、dashboard-toolkit/test-manifest.json 与实际 collected IDs 是同一集合");
  for (const [label, count, fileName, representative] of [
    ["指标计算", "23 项", "tests/metricsCalculator.test.js", "tests/metricsCalculator.test.js::metricsCalculator > calculates positive growth from the old value"],
    ["数据转换", "20 项", "tests/dataTransformer.test.js", "tests/dataTransformer.test.js::dataTransformer > does not mutate the caller array"],
    ["筛选与分页", "28 项", "tests/filterEngine.test.js", "tests/filterEngine.test.js::filterEngine > includes the start date boundary"],
  ] as const) {
    const suite = testSuites.locator("details").filter({ hasText: label });
    await expect(suite).toContainText(count);
    await expect(suite).toContainText(fileName);
    await suite.locator("summary").click();
    await expect(suite).toContainText(representative);
    await suite.locator("summary").click();
  }
  await expect(testSuites).not.toContainText("business_boundary_1");
  const suiteType = await testSuites.evaluate((element) => ({
    explanation: Number.parseFloat(getComputedStyle(element.querySelector(":scope > header p")!).fontSize),
    suiteTitle: Number.parseFloat(getComputedStyle(element.querySelector("summary b")!).fontSize),
    fileName: Number.parseFloat(getComputedStyle(element.querySelector("summary small")!).fontSize),
    testId: Number.parseFloat(getComputedStyle(element.querySelector("ol code")!).fontSize),
  }));
  expect(suiteType.explanation).toBeGreaterThanOrEqual(11);
  expect(suiteType.suiteTitle).toBeGreaterThanOrEqual(12);
  expect(suiteType.fileName).toBeGreaterThanOrEqual(11);
  expect(suiteType.testId).toBeGreaterThanOrEqual(11);
  await selfTest.getByText("查看应通过的测试与失败信号").click();
  await expect(selfTest).toContainText("Stage A 必须因原 @ 别名指向 ./source 而红灯");
  await expect(selfTest).toContainText("Stage D 必须 71/71 通过且零失败");
  await expect(selfTest).toContainText("任一阶段没有出现预期红灯");

  const downloadPromise = page.waitForEvent("download");
  await artifacts.getByRole("button", { name: "下载成果" }).first().click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("看板工具库修复包.zip");

  if (process.env.CAPTURE_TC12_EFFECT_EVIDENCE === "1") {
    await page.setViewportSize({ width: 1440, height: 1100 });
    await artifacts.scrollIntoViewIfNeeded();
    await page.screenshot({ path: "../../docs/evidence/screenshots/tc12-real-vitest-desktop.png", fullPage: true });
  }

  await page.setViewportSize({ width: 390, height: 844 });
  const pageMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  const artifactMetrics = await artifacts.evaluate((element) => ({ width: element.clientWidth, scroll: element.scrollWidth }));
  expect(pageMetrics.scroll).toBeLessThanOrEqual(pageMetrics.viewport);
  expect(artifactMetrics.scroll).toBeLessThanOrEqual(artifactMetrics.width);
  const filterSuite = testSuites.locator("details").filter({ hasText: "筛选与分页" });
  await filterSuite.locator("summary").click();
  await expect(filterSuite).toContainText("tests/filterEngine.test.js::filterEngine > uses a later comparator rule when values are equal");
  const suiteMetrics = await testSuites.evaluate((element) => ({ width: element.clientWidth, scroll: element.scrollWidth }));
  expect(suiteMetrics.scroll).toBeLessThanOrEqual(suiteMetrics.width);
  if (process.env.CAPTURE_TC12_EFFECT_EVIDENCE === "1") {
    await artifacts.scrollIntoViewIfNeeded();
    await page.screenshot({ path: "../../docs/evidence/screenshots/tc12-real-vitest-mobile.png", fullPage: true });
  }
});

test("keeps deterministic verification separate from the TC-11 business release decision", async ({ page }) => {
  await mockHarness(page, { releaseEffect: true });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("综合 PRD、上线配置、功能测试和兼容测试，给出上线结论与改进计划。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const artifacts = page.locator(".workspace-artifacts");
  const outcome = page.getByRole("status", { name: "业务 Gate 结论" });
  await expect(artifacts).toContainText("Agent 已生成 2 份真实成果文件");
  await expect(artifacts.locator(":scope > header > b")).toHaveText("业务 Gate 4/4 未通过");
  await expect(outcome.getByRole("heading", { name: "不得上线" })).toBeVisible();
  await expect(outcome).toContainText("确定性检查通过不等于可以上线");
  for (const statement of [
    "5/7 = 71.4%",
    "4/5 = 80.0%",
    "2/5 = 40.0%",
    "4 项严重问题未清零",
  ]) await expect(outcome).toContainText(statement);
  await expect(outcome.locator(".business-gate-list > li")).toHaveCount(4);
  await expect(artifacts).toContainText("上线合规与风险报告 DOCX");
  await expect(artifacts).toContainText("逐功能风险台账 CSV");
  await expect(artifacts).toContainText("只代表公式、来源和文件结构已复核，不代表业务 Gate 通过");
  await expect(page.locator(".loop-effect-conclusion")).toContainText("业务 Gate 4/4 未通过");
  await expect(page.locator(".loop-effect-conclusion")).toContainText("不得上线");

  await outcome.getByText("查看辅助质量指标").click();
  for (const statement of ["93.4%", "86.4%", "85.7%", "89.7%", "不作为正式上线 Gate"]) await expect(outcome).toContainText(statement);
  await outcome.getByText("查看 18 项逐功能台账").click();
  await expect(outcome.locator(".business-ledger > ol > li")).toHaveCount(18);
  await expect(outcome).toContainText("F17");
  await expect(outcome).toContainText("界面语言预览");
  await expect(outcome).toContainText("严重 4 · 主要 2 · 次要 2");
  await expect(outcome).toContainText("没有执行上线、没有修改配置");

  const typeSizes = await outcome.evaluate((element) => ({
    conclusion: Number.parseFloat(getComputedStyle(element.querySelector(":scope > header h3")!).fontSize),
    gateTitle: Number.parseFloat(getComputedStyle(element.querySelector(".business-gate-list h4")!).fontSize),
    gateDetail: Number.parseFloat(getComputedStyle(element.querySelector(".business-gate-list p")!).fontSize),
    ledgerDetail: Number.parseFloat(getComputedStyle(element.querySelector(".business-ledger dd")!).fontSize),
  }));
  expect(typeSizes.conclusion).toBeGreaterThanOrEqual(20);
  expect(typeSizes.gateTitle).toBeGreaterThanOrEqual(13);
  expect(typeSizes.gateDetail).toBeGreaterThanOrEqual(11);
  expect(typeSizes.ledgerDetail).toBeGreaterThanOrEqual(11);
  let overflow = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(overflow.scroll).toBeLessThanOrEqual(overflow.width);
  if (process.env.CAPTURE_TC11_EFFECT_EVIDENCE === "1") {
    await page.setViewportSize({ width: 1440, height: 1100 });
    await page.screenshot({ path: "../../docs/evidence/screenshots/tc11-release-gate-desktop.png", fullPage: true });
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(outcome.getByRole("heading", { name: "不得上线" })).toBeVisible();
  overflow = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(overflow.scroll).toBeLessThanOrEqual(overflow.width);
  const outcomeOverflow = await outcome.evaluate((element) => ({ width: element.clientWidth, scroll: element.scrollWidth }));
  expect(outcomeOverflow.scroll).toBeLessThanOrEqual(outcomeOverflow.width);
  if (process.env.CAPTURE_TC11_EFFECT_EVIDENCE === "1") {
    await page.screenshot({ path: "../../docs/evidence/screenshots/tc11-release-gate-mobile.png", fullPage: true });
  }
});

test("renders a source-derived seven-risk TC-11 summary without a stale fixed total", async ({ page }) => {
  await mockHarness(page, { releaseEffectRepaired: true });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("综合 PRD、上线配置、功能测试和兼容测试，给出上线结论与改进计划。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const artifacts = page.locator(".workspace-artifacts");
  const outcome = page.getByRole("status", { name: "业务 Gate 结论" });
  await expect(artifacts.locator(":scope > header > b")).toHaveText("业务 Gate 4/4 未通过");
  await expect(artifacts).toContainText("7 项风险");
  await expect(artifacts).not.toContainText("8 项风险");
  await outcome.getByText("查看 18 项逐功能台账").click();
  await expect(outcome).toContainText("严重 3 · 主要 2 · 次要 2 · 无风险项 11");
  const f02 = outcome.locator(".business-ledger > ol > li").filter({ hasText: "F02" });
  await expect(f02).toContainText("无风险项");
});

test("keeps a failed TC-11 verifier red instead of presenting a reliable report", async ({ page }) => {
  await mockHarness(page, { releaseEffectFailed: true });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("综合 PRD、上线配置、功能测试和兼容测试，给出上线结论与改进计划。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const artifacts = page.locator(".workspace-artifacts");
  await expect(artifacts).toContainText("DOCX 结构检查未通过");
  await expect(artifacts).toContainText("当前成果不得作为可靠上线报告");
  await expect(artifacts).not.toContainText("9/9 通过");
  await expect(artifacts).not.toContainText("所有确定性效果门通过");
  await expect(artifacts.locator(":scope > ol > li.is-failed")).toHaveCount(2);
  await expect(artifacts.locator(":scope > ol > li.is-passed")).toHaveCount(0);
});

test("keeps a failed TC-12 fixed command red and tells the user not to merge", async ({ page }) => {
  await mockHarness(page, { dashboardEffectFailed: true });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("为三个看板工具模块编写 Vitest，修复源码并真实运行测试。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const artifacts = page.locator(".workspace-artifacts");
  await expect(artifacts).toContainText("当前固定测试命令未完成全部验证");
  await expect(artifacts).toContainText("当前包不得合并");
  await expect(artifacts).toContainText("stage-d-final-result.json");
  await expect(artifacts).toContainText("coverage-summary.json");
  await expect(artifacts).toContainText("重新启动一项新的 TC-12 Run");
  await expect(artifacts).not.toContainText("71/71");
  await expect(artifacts).not.toContainText("所有确定性效果门通过");
});

test("explains a verified finance result in user language and resumes only the location branch", async ({ page }) => {
  const state = await mockHarness(page, { verifiedFinanceArtifactAuditPending: true });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对三期往来明细，生成未付、未收和僵尸账款说明。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const artifacts = page.locator(".workspace-artifacts");
  const recovery = page.locator(".loop-source-recovery");
  const locationCard = page.locator(".loop-gap-branches > li");
  const technicalDetails = page.locator(".loop-gap-technical-details");
  await expect(artifacts).toContainText("Agent 已生成 3 份真实成果文件");
  await expect(artifacts).toContainText("2026 期末未付明细");
  await expect(recovery).toContainText("成果已生成，还有 1 条说明缺少原表格位置");
  await expect(page.locator(".loop-gap")).toContainText("成果已生成，还有 1 条说明缺少原表格位置");
  await expect(locationCard).toHaveCount(1);
  await expect(locationCard).toContainText("系统知道这条说明来自《2026往来明细.xlsx》，但还没定位到具体行或单元格。");
  await expect(locationCard).toContainText("不影响已经生成的成果文件；这条 Agent 说明仍需人工复核。");
  await expect(locationCard.getByRole("button", { name: "查找原表格位置" })).toBeVisible();
  await expect(locationCard.getByRole("button", { name: "查看已生成成果" })).toBeVisible();
  await expect(page.locator(".trace-current-round")).toContainText("成果已生成，说明位置待查找");
  await expect(page.locator(".loop-branches")).toHaveCount(0);
  await expect(technicalDetails).not.toHaveAttribute("open", "");
  await expect(technicalDetails.getByText("2 个 Branch / 2 个 Gap")).not.toBeVisible();
  await expect(page.getByText("同一来源影响 2 个内部步骤")).toHaveCount(0);
  await expect(page.locator(".loop-view")).not.toContainText("缺 1 份引用");
  await expect(page.locator(".loop-view")).not.toContainText("建议重试此分支");
  await expect(page.locator(".loop-view")).not.toContainText("共有 2 个待处理");
  const outcomeFirst = await page.evaluate(() => {
    const outcome = document.querySelector(".workspace-artifacts");
    const audit = document.querySelector(".loop-source-recovery");
    return Boolean(outcome && audit && (outcome.compareDocumentPosition(audit) & Node.DOCUMENT_POSITION_FOLLOWING));
  });
  expect(outcomeFirst).toBe(true);

  if (process.env.CAPTURE_DR0038_EVIDENCE === "1") {
    await page.setViewportSize({ width: 1600, height: 1000 });
    await page.locator(".loop-gap").screenshot({ path: "../../docs/evidence/screenshots/dr-0038-source-location-user-language-desktop.png" });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  const metrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(metrics.scroll).toBeLessThanOrEqual(metrics.viewport);
  if (process.env.CAPTURE_DR0038_EVIDENCE === "1") {
    await page.locator(".loop-gap").screenshot({ path: "../../docs/evidence/screenshots/dr-0038-source-location-user-language-mobile.png" });
  }
  await technicalDetails.getByText("技术详情").click();
  await expect(technicalDetails.getByText("2 个 Branch / 2 个 Gap")).toBeVisible();
  await locationCard.getByRole("button", { name: "查看已生成成果" }).click();
  await expect(artifacts).toBeInViewport();
  await locationCard.getByRole("button", { name: "查找原表格位置" }).click();
  expect(state.controls.at(-1)).toMatchObject({ command: "resume", branch_id: "branch-111111111111" });
});

test("states clearly when an unverified result still needs an original table position", async ({ page }) => {
  await mockHarness(page, { unverifiedArtifactLocationPending: true });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对财务说明并定位原表格位置。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const gap = page.locator(".loop-gap");
  await expect(gap).toContainText("成果尚未通过，还有 1 条说明缺少原表格位置");
  await expect(gap).toContainText("当前还不能确认成果；这不是文件缺失、日期错误或金额验算失败。");
  await expect(gap.getByRole("button", { name: "查找原表格位置" })).toBeVisible();
  await expect(gap.getByRole("button", { name: "查看已生成成果" })).toHaveCount(0);
  await expect(gap).not.toContainText("成果已生成，还有 1 条说明缺少原表格位置");
});

test("requires a new task when an old run ended before locating the table position", async ({ page }) => {
  await mockHarness(page, { terminalArtifactLocationPending: true });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("继续核对旧任务中的财务说明。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const gap = page.locator(".loop-gap");
  await expect(gap).toContainText("这次任务已结束，还有 1 条说明未定位");
  await expect(gap).toContainText("旧 Run 不能原地继续");
  await expect(gap.getByRole("button", { name: "创建新任务查找位置" })).toBeVisible();
  await gap.getByRole("button", { name: "创建新任务查找位置" }).click();
  await expect(page.getByRole("dialog")).toContainText("新建任务，只续办此分支");
});

test("keeps distinct audit failures separate even when they reference the same file", async ({ page }) => {
  await mockHarness(page, { verifiedArtifactAuditPendingDistinct: true });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("根据入职时间表和分配规则，生成入职资产匹配表。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  await expect(page.locator(".loop-gap-branches > li")).toHaveCount(2);
  await expect(page.locator(".loop-gap")).toContainText("成果已生成，还有 2 条说明缺少原表格位置");
  await expect(page.getByText("同一来源影响 2 个内部步骤")).toHaveCount(0);
});

test("shows an external boundary instead of a fabricated result", async ({ page }) => {
  await mockHarness(page, { effectBoundary: true });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("连接只读 Datasette，分析网约车经营数据并复核指标。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const boundary = page.locator(".workspace-artifacts.is-bounded");
  await expect(boundary).toContainText("这项任务尚不能生成可信成果");
  await expect(boundary).toContainText("缺少已授权的外部连接");
  await expect(boundary).toContainText("没有生成伪造结果");
  await expect(boundary.getByRole("button", { name: "下载成果" })).toHaveCount(0);
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
  const retryLane = page.locator(".loop-gap-branches > li").filter({ hasText: "形成分析结果" });
  await expect(retryLane).toContainText("无需核对文件，建议重试");
  await expect(retryLane.getByRole("button", { name: "继续此分支" })).toBeEnabled();
  expect(state.controls).toHaveLength(0);
  await retryLane.getByRole("button", { name: "继续此分支" }).click();
  const retryDialog = page.getByRole("dialog", { name: /Agent 尚未完成/ });
  await expect(retryDialog).toContainText("下一步只做 1 件事");
  await expect(retryDialog).toContainText("不需要修改文件，也不需要填写内容");
  await expect(retryDialog.locator(".gap-extra-hint textarea")).toBeHidden();
  await retryDialog.getByText("为什么停下 / 查看相关文件").click();
  await expect(retryDialog).toContainText("第 1 轮 / 形成分析结果");
  await expect(retryDialog).toContainText("这里没有高亮，不是让你猜哪一行");
  await expect(retryDialog).toContainText("授权范围：仅限本项目合同审阅。");
  if (process.env.CAPTURE_DR0031_EVIDENCE === "1") {
    await retryDialog.screenshot({ path: "../../docs/evidence/screenshots/dr-0031-actionable-gap-recovery.png" });
  }
  await retryDialog.getByRole("button", { name: "继续任务，只重试此分支" }).click();
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

test("keeps the review body, evidence and safe table preview readable on desktop and mobile", async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 1000 });
  await mockHarness(page, { reviewTable: true });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对超长客商的期末余额并打开问题审查页。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await page.getByRole("button", { name: /发现与建议/ }).click();
  await page.getByRole("button", { name: "打开审查页" }).first().click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("星海科技股份有限公司华东区域企业服务中心");
  await expect(dialog).toContainText("1,500,000.00");
  const sizes = await dialog.evaluate((element) => {
    const size = (selector: string) => {
      const node = element.querySelector(selector);
      return node ? Number.parseFloat(getComputedStyle(node).fontSize) : 0;
    };
    return {
      fact: size(".review-summary-steps strong"),
      impact: size(".evidence-review-claim details p"),
      excerpt: size(".evidence-anchor-item q"),
      metadata: size(".evidence-anchor-item em"),
      callout: size(".active-evidence-callout q"),
      table: size(".table-preview td"),
    };
  });
  expect(sizes.fact).toBeGreaterThanOrEqual(14);
  expect(sizes.impact).toBeGreaterThanOrEqual(14);
  expect(sizes.excerpt).toBeGreaterThanOrEqual(13);
  expect(sizes.metadata).toBeGreaterThanOrEqual(11);
  expect(sizes.callout).toBeGreaterThanOrEqual(13);
  expect(sizes.table).toBeGreaterThanOrEqual(15);
  const desktopOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(desktopOverflow).toBeLessThanOrEqual(0);
  if (process.env.CAPTURE_DR0037_EVIDENCE === "1") {
    await dialog.screenshot({ path: "../../docs/evidence/screenshots/dr-0037-review-readability-desktop.png" });
  }

  await page.setViewportSize({ width: 390, height: 844 });
  const mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(mobileOverflow).toBeLessThanOrEqual(0);
  const reviewOverflow = await dialog.evaluate((element) => element.scrollWidth - element.clientWidth);
  expect(reviewOverflow).toBeLessThanOrEqual(0);
  await expect(dialog.getByRole("button", { name: "关闭问题审查页" })).toBeVisible();
  if (process.env.CAPTURE_DR0037_EVIDENCE === "1") {
    await dialog.screenshot({ path: "../../docs/evidence/screenshots/dr-0037-review-readability-mobile.png" });
  }
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

test("always closes the review page even when the defer receipt conflicts", async ({ page }) => {
  const state = await mockHarness(page, { failDecisionDefer: true }); await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对新闻搜索路由并说明如何处理。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();
  await page.getByRole("button", { name: /发现与建议/ }).click();
  await page.getByRole("button", { name: "打开审查页" }).first().click();

  const dialog = page.getByRole("dialog", { name: "需要你核对并决定下一步" });
  await dialog.getByRole("button", { name: "关闭问题审查页" }).click();

  await expect(dialog).toBeHidden();
  await expect.poll(() => state.controls.length).toBe(1);
  await expect(page.locator(".workspace-error")).toContainText("暂缓回执未写入");
  if (process.env.CAPTURE_DR0033_EVIDENCE === "1") {
    await page.screenshot({ path: "../../docs/evidence/screenshots/dr-0033-review-closed-after-conflict.png", fullPage: true });
  }
});

test("accepts a source candidate for bounded branch recovery", async ({ page }) => {
  const state = await mockHarness(page, { sourceRecovery: true }); await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对跨文件版本冲突并逐条定位原文。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const recovery = page.locator(".loop-source-recovery");
  await expect(recovery).toContainText("需要选择原文的分支与可以直接重试的分支已经分开标注");
  await page.locator(".loop-gap-branches > li").first().getByRole("button", { name: "选择原文位置" }).click();
  const dialog = page.getByRole("dialog", { name: "从 2 个原文位置中选 1 个" });
  await expect(dialog).toContainText("从 2 个真实位置中选 1 个");
  const acceptLocation = dialog.getByRole("button", { name: "采用此位置并只重跑本分支" });
  await expect(acceptLocation).toBeDisabled();
  await dialog.getByRole("button", { name: /选择候选原文 2：workflow\.py/ }).click();
  await expect(acceptLocation).toBeEnabled();
  if (process.env.CAPTURE_DR0032_EVIDENCE === "1") {
    await page.setViewportSize({ width: 1440, height: 1100 });
    await page.screenshot({ path: "../../docs/evidence/screenshots/dr-0032-decision-packet-desktop.png", fullPage: true });
  }
  if (process.env.CAPTURE_DR0030_EVIDENCE === "1") {
    await dialog.screenshot({ path: "../../docs/evidence/screenshots/dr-0030-evidence-disambiguation.png" });
    await dialog.locator(".evidence-resolution-decision").screenshot({ path: "../../docs/evidence/screenshots/dr-0030-evidence-disambiguation-action.png" });
  }
  await dialog.getByText("查看技术回执与其他处理方式").click();
  await dialog.getByRole("textbox", { name: "补充给重跑分支的反馈（可选）" }).fill("同时核对版本字段。" );
  await acceptLocation.click();

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
  await expect(recovery).toContainText("需要选择原文的分支与可以直接重试的分支已经分开标注");
  await page.locator(".loop-gap-branches > li").first().getByRole("button", { name: "选择原文位置" }).click();
  const dialog = page.getByRole("dialog", { name: "从 3 个原文位置中选 1 个" });
  await expect(dialog).toContainText("为什么需要你");
  await expect(dialog).toContainText("你只需要选什么");
  await expect(dialog).toContainText("选完发生什么");
  await expect(dialog.getByRole("button", { name: "关闭问题审查页" })).toBeVisible();
  const acceptLocation = dialog.getByRole("button", { name: "采用此位置并只重跑本分支" });
  await expect(acceptLocation).toBeDisabled();
  await expect(dialog.getByRole("button", { name: /选择候选原文 1：workflow\.py/ })).toBeVisible();
  await expect(dialog.getByRole("button", { name: /选择候选原文 2：workflow\.py/ })).toBeVisible();
  await expect(dialog.getByRole("button", { name: /选择候选原文 3：workflow\.py/ })).toBeVisible();

  const mobileMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(mobileMetrics.scroll).toBeLessThanOrEqual(mobileMetrics.viewport);
  const ambiguousDialogMetrics = await dialog.evaluate((element) => ({ width: element.clientWidth, scroll: element.scrollWidth }));
  expect(ambiguousDialogMetrics.scroll).toBeLessThanOrEqual(ambiguousDialogMetrics.width);
  if (process.env.CAPTURE_DR0034_EVIDENCE === "1") {
    await page.screenshot({ path: "../../docs/evidence/screenshots/dr-0034-ambiguous-choice-mobile.png" });
  }
  await dialog.getByRole("button", { name: /选择候选原文 3：workflow\.py/ }).click();
  await expect(dialog).toContainText("已选 1 个位置");
  await expect(acceptLocation).toBeEnabled();
  if (process.env.CAPTURE_DR0032_EVIDENCE === "1") {
    await page.screenshot({ path: "../../docs/evidence/screenshots/dr-0032-decision-packet-mobile.png", fullPage: true });
  }
  await acceptLocation.click();

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
  await page.locator(".loop-gap-branches > li").first().getByRole("button", { name: "选择原文位置" }).click();

  const dialog = page.getByRole("dialog", { name: "从 2 个原文位置中选 1 个" });
  await dialog.getByText("查看技术回执与其他处理方式").click();
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

  await page.locator(".loop-gap-branches > li").first().getByRole("button", { name: "选择原文位置" }).click();
  let dialog = page.getByRole("dialog", { name: "从 2 个原文位置中选 1 个" });
  await dialog.getByText("查看技术回执与其他处理方式").click();
  await dialog.getByRole("button", { name: "保留现有结果，稍后处理" }).click();
  await expect.poll(() => state.controls.length).toBe(1);
  expect(state.controls[0].decision_action).toBe("defer");

  await page.locator(".loop-gap-branches > li").first().getByRole("button", { name: "选择原文位置" }).click();
  dialog = page.getByRole("dialog", { name: "从 2 个原文位置中选 1 个" });
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
  const sourceChoice = page.locator(".loop-gap-branches > li").first().getByRole("button", { name: "选择原文位置" });
  await expect(sourceChoice).toBeVisible();

  await page.reload();
  await expect(sourceChoice).toBeVisible();
  await sourceChoice.click();
  await expect(page.getByRole("dialog", { name: "从 2 个原文位置中选 1 个" })).toContainText("从 2 个真实位置中选 1 个");
  expect(state.controls).toHaveLength(0);
});

test("shows one recommended retry action without making optional input look required", async ({ page }) => {
  const state = await mockHarness(page, { sourceRecovery: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对跨文件版本冲突并逐条定位原文。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const retryLane = page.locator(".loop-gap-branches > li").nth(1);
  await expect(retryLane).toContainText("无需核对文件，建议重试");
  await retryLane.getByRole("button", { name: "继续此分支" }).click();

  const dialog = page.getByRole("dialog", { name: /下一步：只重试/ });
  await expect(dialog).toContainText("下一步只做 1 件事");
  await expect(dialog).toContainText("直接让 Agent 重试此分支");
  await expect(dialog).toContainText("不需要修改文件，也不需要填写内容");
  await expect(dialog.getByRole("button", { name: "继续任务，只重试此分支" })).toBeVisible();
  await expect(dialog.getByRole("button", { name: "暂不处理此分支" })).toBeVisible();
  await expect(dialog.getByText("我有额外线索")).toBeVisible();
  await expect(dialog.locator(".gap-extra-hint textarea")).toBeHidden();
  await expect(dialog.getByText("为什么停下 / 查看相关文件")).toBeVisible();
  await expect(dialog.locator(".evidence-workbench-disclosure.is-gap")).not.toHaveAttribute("open", "");
  const mobileMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(mobileMetrics.scroll).toBeLessThanOrEqual(mobileMetrics.viewport);
  const retryDialogMetrics = await dialog.evaluate((element) => ({ width: element.clientWidth, scroll: element.scrollWidth }));
  expect(retryDialogMetrics.scroll).toBeLessThanOrEqual(retryDialogMetrics.width);
  if (process.env.CAPTURE_DR0034_EVIDENCE === "1") {
    await page.screenshot({ path: "../../docs/evidence/screenshots/dr-0034-retry-action-mobile.png" });
  }

  await dialog.getByRole("button", { name: "继续任务，只重试此分支" }).click();
  await expect.poll(() => state.controls.map((item) => item.command)).toEqual(["resume"]);
  expect(state.controls[0].branch_id).toBe("branch-222222222222");
});

test("pauses an unlocatable result with a guided branch recovery", async ({ page }) => {
  const state = await mockHarness(page, { sourceRecovery: true }); await page.goto("/");
  await page.getByRole("textbox", { name: "任务指令" }).fill("核对跨文件版本冲突并逐条定位原文。");
  await page.getByRole("button", { name: "启动 Control Loop" }).click();

  const recovery = page.locator(".loop-source-recovery");
  await expect(recovery).toContainText("共有 2 个待处理，每次处理 1 个");
  await expect(recovery).toContainText("已保留");
  await expect(recovery).toContainText("未采用");
  await expect(recovery).toContainText("未发生");
  const branchLanes = page.locator(".loop-gap-branches > li");
  await expect(branchLanes).toHaveCount(2);
  await expect(branchLanes.first()).toContainText("当前材料");
  await expect(branchLanes.first()).toContainText("证据门");
  await expect(branchLanes.first()).toContainText("下一步");
  await expect(page.locator(".loop-gap > header")).toContainText("共有 2 个待处理，每次处理 1 个");
  await expect(branchLanes.first()).toContainText("需要从 2 个原文位置中选 1 个");
  await expect(branchLanes.first().getByRole("button", { name: "选择原文位置" })).toBeVisible();
  await expect(branchLanes.nth(1)).toContainText("无需核对文件，建议重试");
  await expect(branchLanes.nth(1).getByRole("button", { name: "继续此分支" })).toBeVisible();
  if (process.env.CAPTURE_DR0034_EVIDENCE === "1") {
    await page.setViewportSize({ width: 1600, height: 1000 });
    await page.locator(".loop-gap").screenshot({ path: "../../docs/evidence/screenshots/dr-0034-mixed-branch-actions-desktop.png" });
  }
  if (process.env.CAPTURE_DR0033_EVIDENCE === "1") {
    await page.setViewportSize({ width: 1600, height: 1000 });
    await page.locator(".loop-gap").screenshot({ path: "../../docs/evidence/screenshots/dr-0033-branch-evidence-lanes.png" });
  }
  await branchLanes.nth(1).getByRole("button", { name: "继续此分支" }).click();
  const retryDialog = page.getByRole("dialog", { name: /下一步：只重试/ });
  await retryDialog.getByText("我有额外线索").click();
  await retryDialog.getByRole("textbox", { name: "给 Agent 的线索（可选）" }).fill("优先核对版本字段和测试时间。");
  if (process.env.CAPTURE_DR0030_EVIDENCE === "1") {
    await retryDialog.screenshot({ path: "../../docs/evidence/screenshots/dr-0030-source-location-recovery.png" });
  }
  await retryDialog.getByRole("button", { name: "继续任务，只重试此分支" }).click();

  await expect.poll(() => state.controls.map((control) => control.command)).toEqual(["steer", "resume"]);
  expect(state.controls[0].instruction).toContain("用户补充：优先核对版本字段和测试时间。");
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
  const gapDialog = page.getByRole("dialog", { name: /用“.*”分支新建任务/ });
  await expect(gapDialog).toContainText("旧 Run 已结束，不能原地续跑");
  await expect(gapDialog).toContainText("新建任务，只续办此分支");
  await expect(gapDialog).toContainText("不需要修改文件，也不需要填写内容");
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
