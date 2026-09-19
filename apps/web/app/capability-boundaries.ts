export type CopilotBoundaryFacts = {
  readOnly: boolean;
  terminal: boolean;
  status: string;
  controlState: string;
  candidateCount: number;
  hasDecision: boolean;
  unavailableDecisions: number;
  readyWorkers: number;
  waitingBranch: boolean;
  businessDecision: string | null;
  businessInvalid: boolean;
};

type BoundaryNotice = {
  key: string;
  title: string;
  agent: string;
  human: string;
  limit: string;
  tone: "neutral" | "attention" | "blocked";
};

// Explanations of existing server facts, never permission decisions.
export function projectCopilotBoundaries(facts: CopilotBoundaryFacts): BoundaryNotice[] {
  if (facts.readOnly) return [{ key: "history", title: "历史只读", agent: "保留这次执行的结果和记录。", human: "查看历史；需要操作时先回到当前执行。", limit: "历史页面不能批准新动作或继续旧执行。", tone: "neutral" }];
  const notices: BoundaryNotice[] = [];
  if (facts.businessDecision !== null) notices.push({ key: "business", title: facts.businessInvalid ? "业务判断尚不成立" : "业务规则未通过", agent: facts.businessDecision || "保留来源检查结果，不推断业务条件已经满足。", human: "查看业务规则、未通过项和整改依据。", limit: "文件生成或校验通过不代表业务获准；本系统不执行上线、签署或外发。", tone: "blocked" });
  if (facts.hasDecision) notices.push(facts.candidateCount > 0
    ? { key: "evidence", title: "证据选择边界", agent: `保留 ${facts.candidateCount} 个候选位置，不替你猜选。`, human: "对照原文选择引用位置，也可以暂缓。", limit: facts.terminal ? "确认只记录位置；继续处理仍需创建同一任务的新 Run。" : "选择引用不是批准业务结论，也不修改原文件。", tone: "attention" }
    : { key: "judgment", title: "人工判断边界", agent: "列出已定位事实、影响和可选处理方式。", human: "查看问题后决定下一步，或暂缓处理。", limit: "记录决定不等于修改原文件或执行外部动作。", tone: "attention" });
  if (facts.unavailableDecisions > 0) notices.push({ key: "incomplete", title: "决定资料尚不完整", agent: `${facts.unavailableDecisions} 项待决还缺少可操作的证据资料。`, human: "等待状态核对，不对缺失候选作确认。", limit: "没有完整依据，不能把普通重试当成已经作出决定。", tone: "attention" });
  if (facts.readyWorkers > 0 && !facts.terminal) notices.push({ key: "workers", title: "协作用量边界", agent: `${facts.readyWorkers} 个工作包已就绪，本批等待明确确认。`, human: "查看协作范围与剩余预算，再决定是否派发。", limit: "确认仅针对本批只读 Worker，不扩大文件范围或外部动作权限。", tone: "attention" });
  if (facts.waitingBranch && !facts.hasDecision && !facts.unavailableDecisions && !facts.readyWorkers) notices.push({ key: "retry", title: "执行恢复边界", agent: "保留已完成成果，只重新处理选中的分支。", human: "选择需要继续的分支；不必先改文件或填写答案。", limit: facts.terminal ? "旧执行已结束；继续会创建同一任务的新 Run，不覆盖旧结果。" : "点击继续才授权下一轮重试，不代表补证已经成功。", tone: "attention" });
  if (!notices.length) {
    if (facts.status === "failed") notices.push({ key: "failed", title: "执行失败待核对", agent: "保留已返回的执行记录，不宣称任务完成。", human: "查看失败原因与现有成果，再决定后续任务。", limit: "未显示待决不代表任务成功。", tone: "blocked" });
    else if (facts.terminal) notices.push({ key: "ended", title: "本次执行已结束", agent: "保留已有成果、调用回执与版本记录。", human: "复核结果，决定后续是否继续或新建任务。", limit: "执行结束不代表业务正确，也不代表外部动作发生。", tone: "neutral" });
    else if (["paused", "pause_requested"].includes(facts.controlState)) notices.push({ key: "paused", title: facts.controlState === "paused" ? "执行已暂停" : "正在请求暂停", agent: facts.controlState === "paused" ? "等待后续控制，不自行当作你已同意继续。" : "在安全点处理暂停，不宣称在途调用已被取消。", human: "检查已有结果，再决定是否继续。", limit: "继续执行不等于批准新的业务动作。", tone: "attention" });
    else notices.push({ key: "bounded", title: "既有范围内推进", agent: "按当前合同读取批准资料并核对结果。", human: "当前没有完整的待决事项；可以查看进展或请求暂停。", limit: "不因没有确认弹窗就获得新的权限；原资料不被修改。", tone: "neutral" });
  }
  return notices;
}
