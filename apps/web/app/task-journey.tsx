"use client";

import { IconCheck, IconFileDescription, IconGitBranch, IconLoader2 } from "@tabler/icons-react";
import { useEffect, useRef } from "react";
import type { HarnessRun } from "./harness-workbench";
import { projectTaskResponsibility, type ResponsibilityItem } from "./task-responsibility";

export const OFFICE_EXAMPLES = [
  {
    title: "核对 Excel 往来账",
    input: ["2026往来明细.xlsx"],
    outcome: "一条账目核对结果，附原始表格行与待确认事项。",
    instruction: "帮我核对一笔往来账。阅读财务管理的《2026往来明细.xlsx》，找出绵阳长城发展融资担保有限公司的其他应收往来，列明期初余额、本期变动和期末余额，并引用对应表格行。没有收款凭证就不要说已经收到款，也不要把账面余额当成逾期金额。只在页面整理，不修改原表。",
  },
  {
    title: "准备新员工入职清单",
    input: ["3月20日-4月20日入职时间表.csv", "入职物资权限软件分配.pdf"],
    outcome: "一份入职准备清单，把可安排事项与需要确认的例外分开。",
    instruction: "帮我准备吴嘉木的入职清单。对照《3月20日-4月20日入职时间表.csv》和《入职物资权限软件分配.pdf》，列出入职日期、岗位以及需要准备的物资和权限。特别核对名单里的特殊备注，不要用通用岗位规则覆盖个人例外；遇到冲突或材料不足，保留两处原文并提出需要人确认的问题。只在页面整理，不实际开通权限或采购。",
  },
  {
    title: "整理 Word 招聘要求",
    input: ["文本评测岗位JD.docx"],
    outcome: "一张区分必备条件与加分条件的招聘检查表。",
    instruction: "帮我把《文本评测岗位JD.docx》的任职要求整理成两组招聘要点：一组汇总全部必备条件，另一组汇总全部加分条件。两组都要在本次结果中列出并附原文，不能把已要求的加分条件留作后续建议。只整理这两组要求，不补充岗位门槛，不评价候选人，不修改原文件。",
  },
  {
    title: "按明确例外整理权限",
    input: ["3月20日-4月20日入职时间表.csv", "入职物资权限软件分配.pdf"],
    outcome: "吴嘉木的软件权限清单，按已写明的例外直接整理，不重复要求人决定。",
    instruction: "只整理吴嘉木的软件权限清单。核对《3月20日-4月20日入职时间表.csv》中他的岗位和备注，再按《入职物资权限软件分配.pdf》的特殊备注覆盖规则，列出应保留和不应开通的软件。规则已经明确时直接应用，不要把默认规则与明确例外误当成需人工裁决的冲突。引用个人记录与覆盖规则。只在页面分析，不实际开通权限。",
  },
  {
    title: "有余额，不等于已收款",
    input: ["2026往来明细.xlsx"],
    outcome: "先整理有依据的账面余额；缺失的到账凭证单列，不猜测收款事实。",
    instruction: "请分别核对以下要求：\n1. 阅读《2026往来明细.xlsx》，整理绵阳长城发展融资担保有限公司其他应收往来的期初余额、本期变动、期末余额，引用原始行。\n2. 核对这笔款的银行到账回单，判断是否已实际收到款。如果资料库没有到账回单，明确记为缺少来源，不用账面余额替代到账证明。\n只在页面分析，不修改表格，不发送催款。第2项缺少材料不能抹去第1项已有结果。",
  },
  {
    title: "新人申请开通 GitHub Enterprise",
    input: ["3月20日-4月20日入职时间表.csv", "入职物资权限软件分配.pdf"],
    outcome: "保留按现规则得到的清单，将改变个人例外的请求单列，不擅自开通。",
    instruction: "准备吴嘉木的软件权限清单，并评估一个尚未批准的变更请求：希望给他开通 GitHub Enterprise。先核对《3月20日-4月20日入职时间表.csv》的个人备注与《入职物资权限软件分配.pdf》的覆盖规则。系统直接整理现规则允许的通用软件；变更请求若与明确的不开通备注冲突，引用原文，说明为什么需负责人决定，区分维持现规则与整理变更申请两条后续路径。两条路径都只是分析或申请草稿，不执行开通，不把本指令当授权。",
  },
  {
    title: "入职三件事：岗位、权限、回款",
    input: ["外卖商户BD岗位JD.docx", "3月20日-4月20日入职时间表.csv", "入职物资权限软件分配.pdf", "2026往来明细.xlsx"],
    outcome: "三项工作并行推进；需要负责人决定或缺少来源的那一支停下等你，其余照常完成。",
    instruction: "请分别核对以下要求：\n1. 阅读《外卖商户BD岗位JD.docx》，摘出学历和沟通要求，附原文。\n2. 准备吴嘉木的软件权限清单，并评估一个尚未批准的变更请求：希望给他开通 GitHub Enterprise。先核对《3月20日-4月20日入职时间表.csv》的个人备注与《入职物资权限软件分配.pdf》的覆盖规则；变更请求若与明确的不开通备注冲突，引用原文，说明为什么需要负责人决定，区分维持现规则与整理变更申请两条后续路径，不要自行裁决。\n3. 核对绵阳长城发展融资担保有限公司那笔其他应收往来的银行到账回单，判断是否已实际收到款。如果资料库没有到账回单，明确记为缺少来源，不用账面余额替代。\n只在页面分析，不修改文件，不开通权限，不发送催款。第2、3项遇到的问题，不能抹去第1项已有的结果。",
  },
] as const;

export function officeTaskTitle(instruction: string) {
  return OFFICE_EXAMPLES.find(item => item.instruction === instruction)?.title
    ?? instruction.replace(/^请分别核对以下要求[：:]\s*/u, "").split(/[。\n]/)[0].slice(0, 60);
}

type Source = { file_ref: string; display_label: string };

export function TaskBrief({ instruction, files, onFile }: { instruction: string; files: Source[]; onFile: (ref: string) => void }) {
  const example = OFFICE_EXAMPLES.find(item => item.instruction === instruction);
  if (!instruction.trim()) return null;
  return <section className="task-brief" aria-label="开始前核对任务">
    <h3>这次要完成什么</h3><p>{example?.outcome ?? instruction}</p>
    <div><span>预计资料</span>{example ? example.input.map(name => {
      const file = files.find(item => item.display_label === name);
      return file ? <button type="button" key={name} onClick={() => onFile(file.file_ref)}><IconFileDescription/>{name}</button> : <span key={name}>{name} · 尚未找到</span>;
    }) : <span>提交后由 Agent 从资料库选择，再展示实际处理范围。</span>}</div>
    <small>预计资料不是已读取记录；原文件保持不变。任务要求可在上方修改。</small>
  </section>;
}

export function TaskProcess({ run, files, onFile, onFinding, onEvidence }: { run: HarnessRun; files: Source[]; onFile: (ref: string) => void; onFinding: (finding: NonNullable<HarnessRun["result"]>["findings"][number]) => void; onEvidence: () => void }) {
  const first = run.rounds[0];
  const plan = first?.plan.length ? first.plan : null;
  const supplied = new Set(first?.model_input_coverage.map(item => item.file_ref) ?? []);
  const selected = first?.input_file_refs ?? [];
  const finished = ["completed", "stopped", "failed", "ready_to_execute"].includes(run.status);
  const waiting = run.status === "waiting_input" || run.control_state === "paused";
  const steps = [
    { title: "明确目标", complete: true },
    { title: "选择资料", complete: Boolean(plan) },
    { title: waiting && first?.analysis_receipt?.output_used ? "已形成部分分析" : "形成分析", complete: Boolean(first?.analysis_receipt?.output_used) },
    { title: "保留成果", complete: run.artifact_versions.length > 0 || run.workspace_artifacts.length > 0 },
  ];
  return <section className="task-process" aria-label="首轮任务安排">
    <header><h2>先把任务说清楚</h2><span>{finished ? "第 1 轮记录" : waiting ? "当前已暂停" : "第 1 轮安排"}</span></header>
    <ol className="task-process-steps">{steps.map((step, index) => <li key={step.title} className={step.complete ? "is-done" : ""}><i>{step.complete ? <IconCheck/> : index + 1}</i>{step.title}</li>)}</ol>
    <TaskResponsibility run={run} onFinding={onFinding} onEvidence={onEvidence}/>
    <details className="task-process-record" open={!waiting && !finished}><summary>查看首轮目标、资料与安排</summary><dl><div><dt>你的要求</dt><dd>{run.instruction}</dd></div>
      <div><dt>本轮文件</dt><dd>{selected.length ? <div className="task-process-files">{selected.map(ref => <button key={ref} onClick={() => onFile(ref)}><IconFileDescription/><span>{files.find(item => item.file_ref === ref)?.display_label ?? "来源资料"}<small>{supplied.has(ref) ? "已送入分析" : "计划处理"}</small></span></button>)}</div> : <p>{finished ? "未形成通过校验的文件范围。" : "正在从资料库选择相关文件，尚未读取全部文件。"}</p>}</dd></div>
      <div><dt>处理安排</dt><dd>{plan ? <ol className="task-working-steps">
        <li><b>读取本轮资料</b><span>{selected.map(ref => files.find(item => item.file_ref === ref)?.display_label ?? "来源资料").join("、")} · {supplied.size ? "已送入分析" : "待读取"}</span></li>
        <li><b>按任务要求分析</b>{plan.map(unit => <details key={unit.node_id}><summary>{unit.label}</summary><p>{unit.description}</p></details>)}</li>
        <li><b>核对引用，保留结果</b><span>{first?.analysis_receipt?.output_used ? "本轮分析已采用；具体结论与引用见成果和依据。" : "分析返回后核对原文位置；无法定位的内容不作为已确认结果。"}</span></li>
      </ol> : <p>{finished ? "本次未形成可执行计划。" : <><IconLoader2 aria-hidden="true"/>正在整理目标与处理步骤。</>}</p>}</dd></div>
      <div><dt>交付目标</dt><dd>{OFFICE_EXAMPLES.find(item => item.instruction === run.instruction)?.outcome ?? "形成带原文依据的分析结果，单列未完成事项与后续建议。"}</dd></div>
    </dl>
    {first?.selection_reason && <details><summary>为什么选这些文件</summary><p>{first.selection_reason}</p></details>}</details>
  </section>;
}

function TaskResponsibility({ run, onFinding, onEvidence }: { run: HarnessRun; onFinding: (finding: NonNullable<HarnessRun["result"]>["findings"][number]) => void; onEvidence: () => void }) {
  const { system, human, agent, businessBlocked } = projectTaskResponsibility(run);
  const renderItem = (item: ResponsibilityItem) => <li key={item.id} data-responsibility={item.kind}><strong>{item.title}</strong><p>{item.reason}</p>{item.kind === "missing" ? <small>需要补充真实材料，不是选择一个猜测答案。</small> : item.finding ? <button type="button" onClick={() => onFinding(item.finding!)}>{item.kind === "judgment" ? "查看问题与选项" : "核对原文"}</button> : ["source_choice", "judgment"].includes(item.kind) ? <button type="button" onClick={onEvidence}>查看待决依据</button> : null}</li>;
  const waiting = run.status === "waiting_input" || run.control_state === "paused";
  if (!system.length && !human.length && !agent.length && !businessBlocked) return null;
  return <section className="task-responsibility" aria-label="本次人机分工">
    <header><h3>这次怎么分工</h3></header>
    {businessBlocked && <p className="responsibility-veto">业务规则尚未通过。文件生成不代表可以执行业务动作。</p>}
    <div className="responsibility-columns">
      <div className="responsibility-system"><h4>系统已处理 <span>{system.length} 项分析</span></h4>{system.length ? <><ul>{system.slice(0, 2).map(renderItem)}</ul>{system.length > 2 && <details><summary>其余 {system.length - 2} 项已采用分析</summary><ul>{system.slice(2).map(renderItem)}</ul></details>}<small>已有可定位原文；仍不等于业务正确性或外部执行已获批准。</small></> : <p>{businessBlocked ? "先处理未通过的业务条件，不显示自动放行。" : "尚无可展示的已采用、已定位分析。"}</p>}</div>
      {human.length > 0 && <div className="responsibility-human"><h4>需要你参与 <span>{human.length} 项</span></h4><ul>{human.map(renderItem)}</ul></div>}
    </div>
    {agent.length > 0 && <details className="responsibility-agent" open={waiting}><summary>Agent 尚未完成的工作 · {agent.length} 项</summary><ul>{agent.map(renderItem)}</ul></details>}
  </section>;
}

export function TaskBranches({ items, selectedId, currentId, disabled, onSelect }: {
  items: { run_id: string; run_sequence: number; instruction: string; status: string }[];
  selectedId: string; currentId: string; disabled: boolean; onSelect: (id: string) => void;
}) {
  const navRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const nav = navRef.current;
    if (!nav) return;
    const revealCurrent = () => {
      const selected = nav.querySelector<HTMLElement>('[aria-current="page"]');
      if (!selected) return;
      const item = selected.getBoundingClientRect(), bounds = nav.getBoundingClientRect();
      if (item.left < bounds.left) nav.scrollLeft += item.left - bounds.left;
      else if (item.right > bounds.right) nav.scrollLeft += item.right - bounds.right;
    };
    revealCurrent();
    const observer = new ResizeObserver(revealCurrent);
    observer.observe(nav);
    return () => observer.disconnect();
  }, [selectedId, items.length]);
  if (items.length < 2) return null;
  return <section className="task-branches" aria-label="任务内分支"><header><IconGitBranch/><b>任务内分支</b><span>同一任务，保留每段结果</span></header>
    <nav ref={navRef} aria-label="切换任务分支">{items.map(item => <button key={item.run_id} disabled={disabled} aria-current={selectedId === item.run_id ? "page" : undefined} onClick={() => onSelect(item.run_id)}><small>{item.run_sequence === 1 ? "初始处理" : `后续分支 ${item.run_sequence - 1}`}{item.run_id === currentId ? " · 当前" : " · 历史"}</small><strong>{officeTaskTitle(item.instruction) || `第 ${item.run_sequence} 段处理`}</strong></button>)}</nav>
  </section>;
}
