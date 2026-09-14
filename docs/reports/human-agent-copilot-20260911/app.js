"use strict";

const app = document.getElementById("app");
const cases = window.COPILOT_CASES;
const states = new Map(cases.map(item => [item.id, { selected: null, closed: false, handled: false, fault: "none", version: 1, stale: false, recommendation: false, records: [] }]));
const sessionRecords = [];
const reviewChecks = new Set();
let activeView = "sandbox";
let activeCase = "B01";
let libraryRisk = "all";
let libraryMaturity = "all";
let librarySearch = "";

function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
}
function icon(name) { return window.COPILOT_ICONS[name] || ""; }
function hydrateIcons() { document.querySelectorAll("[data-icon]").forEach(node => { node.innerHTML = icon(node.dataset.icon); }); }
function tag(text, color = "") { return `<span class="tag ${color}">${escapeHTML(text)}</span>`; }
function selectedCase() { return cases.find(item => item.id === activeCase); }
function riskColor(risk) { return ({ R0: "green", R1: "blue", R2: "amber", R3: "red" })[risk]; }
function announce(message) {
  const node = document.getElementById("announcement");
  node.textContent = message;
  node.hidden = !message;
}
function record(item, action, outcome) {
  const entry = { case_id: item.id, action, outcome, at: new Date().toISOString(), simulated: true, runtime_connected: false, external_action: "none", source: "browser-design-sandbox" };
  sessionRecords.push(entry);
  states.get(item.id).records.push(entry);
}
function switchView(view) {
  activeView = view;
  document.querySelectorAll("[data-view]").forEach(button => {
    button.classList.toggle("active", button.dataset.view === view);
    button.setAttribute("aria-current", button.dataset.view === view ? "page" : "false");
  });
  announce("");
  render();
}
function openCase(id) {
  activeCase = id;
  switchView("sandbox");
}
function actionLabel(item, state) {
  if (state.handled) return "已记录演练意向";
  if (state.stale) return "先刷新示例候选";
  return item.action;
}
function renderSandbox() {
  const item = selectedCase();
  const state = states.get(item.id);
  const summary = `<aside class="decision-summary"><h2>为什么需要你参与</h2>
    <div class="why-item"><span class="step-number">1</span><div><h3>触发了什么边界</h3><p>${escapeHTML(item.reason)}</p></div></div>
    <div class="why-item"><span class="step-number">2</span><div><h3>只影响什么</h3><p>${escapeHTML(item.impact)}</p></div></div>
    <div class="why-item"><span class="step-number">3</span><div><h3>由谁决定下一步</h3><p>${escapeHTML(item.role)}：${escapeHTML(item.next)}。</p></div></div>
    <div class="retained"><h3 class="check-heading">${icon("IconCircleCheck")}系统会保留</h3><ul class="clean">${item.retained.map(text => `<li>${icon("IconCheck")}${escapeHTML(text)}</li>`).join("")}</ul>
    <h3 class="check-heading warn">${icon("IconCircleOff")}系统不会做</h3><ul class="clean warn">${item.prohibited.map(text => `<li>${icon("IconMinus")}${escapeHTML(text)}</li>`).join("")}</ul></div></aside>`;
  const candidates = item.candidates.map((candidate, index) => `<article class="candidate ${state.selected === index ? "selected" : ""}">
    <div class="candidate-head">${item.mode === "choice" ? `<label class="candidate-label"><input type="radio" name="candidate" value="${index}" ${state.selected === index ? "checked" : ""} ${state.handled || state.stale ? "disabled" : ""}><span>${escapeHTML(candidate.label)}</span></label>` : `<strong class="candidate-label">${escapeHTML(candidate.label)}</strong>`}
    <button class="outline-button small-button" data-preview="${index}">${icon("IconFileSearch")}查看示例原文</button></div>
    <div class="source-name">${icon("IconFileText")}${escapeHTML(candidate.file)}</div>
    <div class="excerpt"><small>${escapeHTML(candidate.context)}</small>${item.mode === "choice" ? `<mark>${escapeHTML(candidate.excerpt)}</mark>` : escapeHTML(candidate.excerpt)}</div>
    <p class="candidate-note">${escapeHTML(candidate.note)}</p></article>`).join("");
  const evidence = `<section class="evidence-area"><div class="evidence-heading"><h2>${item.mode === "choice" ? "选择当前结论的依据" : item.mode === "handoff" ? "保留材料，阻断执行" : "确认后续处理范围"}</h2>${tag("虚构案例", "blue")}</div>
    <div class="gate-facts"><div><small>证据状态</small><strong>${escapeHTML(state.stale ? "示例来源已过期，旧选择无效" : item.evidence)}</strong></div><div><small>动作权限</small><strong>${escapeHTML(item.permission)}</strong></div></div>
    ${candidates}
    ${item.id === "B02" ? `<button class="text-button" id="show-recommendation" ${state.selected === null ? "disabled" : ""}>${icon("IconBulb")}对照 Agent 建议</button>${state.recommendation ? `<div class="recommendation">演示建议：保留冲突，先核查是否存在获批例外。建议不是批准证据，最终业务判断由负责人承担。</div>` : ""}` : ""}
    <div class="consequence">${icon("IconInfoCircle")}<span>${state.handled ? "已记录本地演练意向，未发送任何 Runtime 请求；不代表真实决定已入账、分支已恢复或动作已执行。" : `${escapeHTML(item.next)}。本页按钮仅改变沙盘，不产生真实服务端回执。`}</span></div>
    <div class="actions"><button class="secondary-button" id="defer-case">${icon("IconClock")}暂不处理</button><button class="primary-button" id="confirm-case" ${state.handled || state.stale || (item.mode === "choice" && state.selected === null) ? "disabled" : ""}>${icon(item.mode === "handoff" ? "IconUserCheck" : "IconCheck")}${escapeHTML(actionLabel(item, state))}</button></div>
    <details class="authority"><summary>事实映射与验收边界</summary><p><strong>${escapeHTML(item.rule)} · ${escapeHTML(item.refs)}</strong></p><p><code>${escapeHTML(item.mapping)}</code></p><p>${escapeHTML(item.acceptance)}</p><p>案例文本、文件名、行号、状态与本地日志均为明确标注的设计样例，不是当前运行证据。</p></details></section>`;
  const closed = `<section class="deferred-state">${tag("审查面已退出") }<h2>暂不处理，已有成果仍保留</h2><p>本地沙盘已关闭这项核对。${state.fault === "none" ? "暂缓意向只记在当前页面，不代表 Runtime 已写入 DecisionRecord。" : "异常演练：暂缓回执未确认，但退出不受阻。不能显示已成功入账。"}</p><button class="primary-button" id="reopen-case">${icon("IconArrowLeft")}返回这项核对</button></section>`;
  app.innerHTML = `<div class="shell"><div class="page-title"><div><h1>人机共驾边界演练</h1><p>同一任务里，该继续的继续；需要人判断的，只交出那一项。</p></div><div class="title-right">${tag("8 个结构化案例")}${tag("外部动作 0", "green")}</div></div>
    <div class="sandbox-layout"><aside class="case-rail"><h2>边界案例</h2><div class="case-scroll">${cases.map(entry => `<button class="case-item ${entry.id === item.id ? "active" : ""}" data-case="${entry.id}" ${entry.id === item.id ? 'aria-current="true"' : ""}>${icon(entry.icon)}<span><strong>${escapeHTML(entry.title)}</strong><small>${entry.id} · ${escapeHTML(entry.group)}</small></span></button>`).join("")}</div><div class="rail-meta">当前聚焦<br><strong>${escapeHTML(item.topology)}</strong><br><br>案例用于方案评审。<br>真实运行以 Snapshot 为准。</div></aside>
    <div class="main-stage"><div class="task-line"><h2>${escapeHTML(item.title)}</h2><div class="tags">${tag(`${item.risk} · ${item.handling}`, riskColor(item.risk))}${tag(item.maturity, item.maturity === "已有有限基础" ? "green" : "amber")}</div></div>
    <div class="branch-strip"><div class="stage">${icon("IconCircleCheck")}<div><strong>已有结果保留</strong><small>无关分支不重做</small></div></div><span class="arrow">${icon("IconArrowRight")}</span><div class="stage wait">${icon("IconClock")}<div><strong>${escapeHTML(item.branch)}</strong><small>${state.handled ? "演练意向已记录" : state.closed ? "暂不处理" : "等待当前处置"}</small></div></div><span class="arrow">${icon("IconArrowRight")}</span><div class="stage last">${icon("IconFiles")}<div><strong>后续成果</strong><small>以新的权威回执为准</small></div></div></div>
    ${state.closed ? closed : `<div class="decision-layout">${summary}${evidence}</div>`}
    <div class="fault-row"><label>${icon("IconFlask")}异常演练<select id="fault-mode" aria-label="异常演练"><option value="none" ${state.fault === "none" ? "selected" : ""}>无异常</option><option value="conflict" ${state.fault === "conflict" ? "selected" : ""}>版本冲突 · 409</option><option value="offline" ${state.fault === "offline" ? "selected" : ""}>网络中断 · 结果未知</option><option value="stale" ${state.fault === "stale" ? "selected" : ""}>来源版本已变化</option></select></label><button id="refresh-case" class="text-button">${icon("IconRefresh")}刷新示例状态</button><button id="reset-case" class="text-button">${icon("IconRotate")}重置此案例</button></div>
    <section class="receipt-list"><h3>本地演练记录 ${tag("非服务端回执")}</h3>${state.records.length ? state.records.slice(-5).map(entry => `<div class="receipt"><time>${new Date(entry.at).toLocaleTimeString("zh-CN", { hour12: false })}</time><span>${escapeHTML(entry.outcome)}</span></div>`).join("") : '<p class="empty-receipt">尚未提交处置意向。打开原文、切换视图不发起执行。</p>'}</section></div></div></div>`;
  app.querySelectorAll("[data-case]").forEach(button => button.addEventListener("click", () => openCase(button.dataset.case)));
  app.querySelectorAll('input[name="candidate"]').forEach(input => input.addEventListener("change", () => { state.selected = Number(input.value); render(); }));
  app.querySelectorAll("[data-preview]").forEach(button => button.addEventListener("click", () => showPreview(item.candidates[Number(button.dataset.preview)])));
  document.getElementById("confirm-case")?.addEventListener("click", confirmCase);
  document.getElementById("defer-case")?.addEventListener("click", deferCase);
  document.getElementById("reopen-case")?.addEventListener("click", () => { state.closed = false; announce(""); render(); });
  document.getElementById("show-recommendation")?.addEventListener("click", () => { state.recommendation = !state.recommendation; render(); });
  document.getElementById("fault-mode").addEventListener("change", event => { state.fault = event.target.value; });
  document.getElementById("refresh-case").addEventListener("click", () => { state.fault = "none"; state.stale = false; state.selected = null; state.handled = false; state.version += 1; record(item, "refresh-simulation", "已刷新示例状态，旧选择清空；没有读取 Runtime。"); announce("示例版本已更新，请重新选择；没有真实网络请求。"); render(); });
  document.getElementById("reset-case").addEventListener("click", () => { state.fault = "none"; state.stale = false; state.selected = null; state.handled = false; state.closed = false; state.recommendation = false; record(item, "reset-simulation", "重置当前案例，旧演练记录保留。"); announce(""); render(); });
}
function confirmCase() {
  const item = selectedCase();
  const state = states.get(item.id);
  if (state.handled || state.stale || (item.mode === "choice" && state.selected === null)) return;
  if (state.fault !== "none") {
    const message = ({ conflict: "异常演练：版本冲突，未记录为成功；请刷新示例状态后重试。", offline: "异常演练：网络中断，结果未知；未显示已确认。真实重试应复用同一次命令的幂等键。", stale: "异常演练：来源版本已变化，旧候选失效；必须刷新并重新选择。" })[state.fault];
    if (state.fault === "stale") { state.selected = null; state.stale = true; }
    record(item, "simulated-rejected-or-unknown", message);
    announce(message);
    render();
    return;
  }
  state.handled = true;
  const outcome = item.mode === "handoff" ? "仅记录人工接管意向（沙盘）；未发通知、未建立审批、外部动作仍未执行。" : item.id === "B05" ? "仅记录同 Task child Run 续办意向（沙盘）；未创建真实 Run，旧成果未改变。" : item.mode === "retry" ? "仅记录目标分支重试意向（沙盘）；尚无模型调用或采用结果。" : item.mode === "ack" ? "仅记录已查看业务条件（沙盘）；业务 Gate 仍未通过，没有批准发布。" : `仅记录候选 ${state.selected + 1} 的选择意向（沙盘）；未写入 DecisionRecord，未执行后续动作。`;
  record(item, "local-intent-only", outcome);
  announce(outcome);
  render();
}
function deferCase() {
  const item = selectedCase();
  const state = states.get(item.id);
  state.closed = true;
  const message = state.fault === "none" ? "已退出审查，本地记录暂缓意向；不代表服务端已入账。" : "已退出审查。异常演练：暂缓回执未确认，不能记为成功；退出不受阻。";
  record(item, "local-close", message);
  announce(message);
  render();
}
function showPreview(candidate) {
  document.getElementById("preview-title").textContent = candidate.file;
  document.getElementById("preview-content").innerHTML = `${tag("虚构示例 · 不是服务端安全 Preview", "amber")}<p>${escapeHTML(candidate.label)}</p><div class="excerpt"><small>${escapeHTML(candidate.context)}</small>${escapeHTML(candidate.excerpt)}</div><p>${escapeHTML(candidate.note)}</p>`;
  document.getElementById("preview-dialog").showModal();
}
function renderMatrix() {
  const risks = [
    ["R0", "范围内自主推进", "批准范围内、低影响、可检查的只读步骤。无未解决阻断，不要求逐步弹窗。"],
    ["R1", "最小局部确认", "位置歧义、可恢复输出失败、预算续办。停在最小分支，明确保留项。"],
    ["R2", "有责任人的判断", "业务规则冲突、对外动作或敏感影响。证据、审批资格和实际权限分别判断。"],
    ["R3", "阻断并专业接管", "高影响、难逆转或关键条件未知。保留检查材料，禁止模型或通用确认覆盖硬门。"]
  ];
  app.innerHTML = `<div class="shell"><div class="page-title"><div><h1>边界规则矩阵</h1><p>风险决定审查强度；证据决定能否采用；权限决定能否行动。三个问题不能合成一个分数。</p></div>${tag("R0–R3 为本方案候选分级", "blue")}</div>
    <section class="panel-band"><div class="rule-grid">${risks.map(([risk,title,description]) => `<div class="rule-cell">${tag(risk,riskColor(risk))}<h3>${title}</h3><p>${description}</p></div>`).join("")}</div><p class="matrix-note">R0 是对照路径。R1–R3 是设计分类，不是当前 Runtime 的通用风险引擎，也不是法律或行业合规等级。关键条件未知时不默认降级。</p></section>
    <section class="panel-band"><h2>按硬约束顺序判定，不平均风险</h2><div class="table-wrap"><table><thead><tr><th>顺序</th><th>要回答的问题</th><th>不满足时</th><th>人能做什么</th><th>不能被什么覆盖</th></tr></thead><tbody>
    <tr><td>1 · 权限</td><td>范围、目标、Connector、身份是否允许？</td><td><strong>阻断执行</strong></td><td>转交授权流程或缩小任务</td><td>用户意愿、文件通过、模型置信度</td></tr>
    <tr><td>2 · 影响</td><td>是否高影响、敏感、难逆转？</td><td>升级专业责任人，审查条件</td><td>说明影响、备份、失败后处置</td><td>多个低风险维度的平均值</td></tr>
    <tr><td>3 · 证据</td><td>来源新鲜、位置明确、规则无冲突？</td><td>不采用受影响候选</td><td>选位置、核口径或补授权来源</td><td>多数 Worker 同意、强语气</td></tr>
    <tr><td>4 · 运行</td><td>预算、版本与当前 Task 指针有效？</td><td>暂停、刷新或显式 child Run</td><td>批准一条恢复，不静默加预算</td><td>重试按钮、浏览器计时动画</td></tr>
    <tr><td>5 · 回执</td><td>有对应的服务端决定与动作结果吗？</td><td>保持请求中、未知或未执行</td><td>对账同一幂等命令或人工调查</td><td>点击成功、已批准、拟执行</td></tr></tbody></table></div></section>
    <section class="panel-band"><h2>规则到案例和服务端事实</h2><div class="table-wrap"><table><thead><tr><th>规则</th><th>边界类型</th><th>接管方式</th><th>最小作用范围</th><th>当前边界</th><th>案例</th></tr></thead><tbody>${cases.map(item => `<tr><td>${item.rule}</td><td>${escapeHTML(item.group)}</td><td>${tag(item.handling,riskColor(item.risk))}</td><td>${escapeHTML(item.branch)}</td><td>${escapeHTML(item.maturity)}</td><td><button class="text-button" data-case="${item.id}">${item.id}${icon("IconArrowUpRight")}</button></td></tr>`).join("")}</tbody></table></div></section>
    <section class="panel-band"><h2>不是所有“确认”都授予执行权</h2><div class="rule-grid"><div class="rule-cell"><h3>选择证据</h3><p>人在多个真实原文位置中选择一处。位置选择不证明语义真伪。</p></div><div class="rule-cell"><h3>确定业务口径</h3><p>人对冲突、例外与影响作出判断。不因此修改外部业务系统。</p></div><div class="rule-cell"><h3>授权有限执行</h3><p>目标设计需要服务端权限、目标、范围、有效期与幂等回执。目前没有外部执行。</p></div><div class="rule-cell"><h3>确认执行结果</h3><p>只能在真实动作回执后核对效果。批准、请求与成功始终分开。</p></div></div></section></div>`;
  app.querySelectorAll("[data-case]").forEach(button => button.addEventListener("click", () => openCase(button.dataset.case)));
}
function renderLibrary() {
  const visible = cases.filter(item => (libraryRisk === "all" || item.risk === libraryRisk) && (libraryMaturity === "all" || item.maturity === libraryMaturity) && `${item.id}${item.title}${item.group}${item.role}${item.trigger}`.toLowerCase().includes(librarySearch.toLowerCase()));
  app.innerHTML = `<div class="shell"><div class="page-title"><div><h1>结构化边界案例库</h1><p>每个案例都有业务触发、责任人、停止范围、保留成果、后续动作与验收条件。</p></div>${tag(`${visible.length} / ${cases.length} 个案例`)}</div>
    <div class="filters"><label>${icon("IconSearch")}<input id="case-search" type="search" placeholder="搜索场景或责任人" value="${escapeHTML(librarySearch)}" aria-label="搜索案例"></label><label>分级<select id="risk-filter"><option value="all">全部风险</option>${["R1","R2","R3"].map(value => `<option ${libraryRisk === value ? "selected" : ""}>${value}</option>`).join("")}</select></label><label>落地范围<select id="maturity-filter"><option value="all">全部状态</option>${["已有有限基础","外部动作未接入","设计候选"].map(value => `<option ${libraryMaturity === value ? "selected" : ""}>${value}</option>`).join("")}</select></label></div>
    <div class="case-grid">${visible.length ? visible.map(item => `<article class="library-card"><header>${tag(`${item.id} · ${item.group}`)}${tag(item.risk,riskColor(item.risk))}</header><h3>${escapeHTML(item.title)}</h3><p>${escapeHTML(item.trigger)}</p><div class="card-foot"><small>${escapeHTML(item.role)}<br>${escapeHTML(item.maturity)}</small><button class="outline-button" data-case="${item.id}">打开案例${icon("IconArrowRight")}</button></div></article>`).join("") : '<div class="empty-list">没有匹配的案例。<br><button class="text-button" id="clear-filters">清除筛选</button></div>'}</div></div>`;
  document.getElementById("case-search").addEventListener("input", event => { const cursor = event.target.selectionStart; librarySearch = event.target.value; renderLibrary(); const input = document.getElementById("case-search"); input.focus(); input.setSelectionRange(cursor,cursor); });
  document.getElementById("risk-filter").addEventListener("change", event => { libraryRisk = event.target.value; renderLibrary(); });
  document.getElementById("maturity-filter").addEventListener("change", event => { libraryMaturity = event.target.value; renderLibrary(); });
  document.getElementById("clear-filters")?.addEventListener("click", () => { libraryRisk = "all"; libraryMaturity = "all"; librarySearch = ""; renderLibrary(); });
  app.querySelectorAll("[data-case]").forEach(button => button.addEventListener("click", () => openCase(button.dataset.case)));
}
const checklist = [
  ["边界说得清", "能区分证据位置、业务判断、动作授权与执行结果。"],
  ["只交出必要的一项", "说明停哪条分支、依赖影响、哪些成果仍保留。"],
  ["不同边界的动作不同", "歧义先选择；Agent 输出失败只需重试；缺权限只能阻断或转交。"],
  ["异常不会假绿", "409、来源过期、断网不显示已成功入账；审查始终可退出。"],
  ["同一套 Runtime 事实", "Demo 1/2 不另建状态机，Demo 3 复用 Task / Branch / Decision / Artifact。"],
  ["声明与证据匹配", "分开写设计沙盘、固定自动化、真实 Provider 和用户研究。"],
  ["外部动作边界成立", "当前保持 external_action=none，通用 Permit 与 Connector 不伪造。"],
  ["技术回溯有明确触发", "三个 Demo 验收后，固定版本、场景与配置，开展新一轮官方来源和同场测试。"]
];
function renderReview() {
  app.innerHTML = `<div class="shell"><div class="page-title"><div><h1>下次会议：评什么，怎么验</h1><p>本轮产物是可讨论的边界设计，不把方案评审提前写成产品能力完成。</p></div><a class="outline-button" href="report.html">${icon("IconPresentation")}会议简报</a></div>
    <div class="metric-band"><div class="metric"><strong>8</strong><small>多场景边界案例</small></div><div class="metric"><strong>4</strong><small>处理强度候选层级</small></div><div class="metric"><strong>3</strong><small>定向核对的官方来源</small></div><div class="metric"><strong>0</strong><small>真实外部动作 / 模型调用</small></div></div>
    <div class="review-layout"><section><h2>方案评审检查单 ${tag(`${reviewChecks.size} / ${checklist.length} 人工勾选`)}</h2><p class="matrix-note">本页勾选只保存在当前页面；它是评审草稿，不是测试结果或批准回执。</p><div class="checklist">${checklist.map(([title,description],index) => `<label><input type="checkbox" data-check="${index}" ${reviewChecks.has(index) ? "checked" : ""}><span><strong>${title}</strong><small>${description}</small></span></label>`).join("")}</div></section>
    <section><h2>设计落地顺序</h2><ol class="roadmap"><li><h3>本轮：建立边界语言 ${tag("已产出", "green")}</h3><p>交互沙盘、八案例、规则矩阵、参考手册。所有演练数据明确标注。</p></li><li><h3>下一门：接入现有真实状态 ${tag("待实施", "amber")}</h3><p>先复用证据选择、受限重试、child Run 和局部 Contribution 处置，不加通用外部执行。</p></li><li><h3>再一门：负例和目标用户验证 ${tag("待执行", "amber")}</h3><p>同内容与任务对照，观察能否判断影响、保留项和下一步；记录错批、错选与恢复失败。</p></li><li><h3>三 Demo 后：技术时效性回溯 ${tag("未启动", "amber")}</h3><p>冻结 Demo 验收版本后 7 个工作日内启动定向调研。官方变更记录、同场挑战与替换判断分别归档。</p></li></ol>
    <h2>本轮来源核对</h2><div class="references"><a href="https://airc.nist.gov/airmf-resources/airmf/5-sec-core/" target="_blank" rel="noreferrer">NIST AI RMF：情境、责任与风险治理 ${icon("IconArrowUpRight")}</a><a href="https://www.microsoft.com/en-us/research/?p=564561" target="_blank" rel="noreferrer">Microsoft Research：人机交互设计准则 ${icon("IconArrowUpRight")}</a><a href="https://docs.langchain.com/oss/python/langgraph/interrupts" target="_blank" rel="noreferrer">LangGraph：中断、持久化和幂等边界 ${icon("IconArrowUpRight")}</a></div><p class="matrix-note">检索日期：2026-09-11。只支持设计依据，不是竞品实测，也不是完整行业最新技术调研。</p></section></div></div>`;
  app.querySelectorAll("[data-check]").forEach(input => input.addEventListener("change", () => { const index = Number(input.dataset.check); if(input.checked) reviewChecks.add(index); else reviewChecks.delete(index); renderReview(); }));
}
function render() {
  ({ sandbox: renderSandbox, matrix: renderMatrix, library: renderLibrary, review: renderReview })[activeView]();
  hydrateIcons();
}
document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => switchView(button.dataset.view)));
document.getElementById("close-preview").addEventListener("click", () => document.getElementById("preview-dialog").close());
document.addEventListener("keydown", event => {
  if (event.key === "Escape" && !document.getElementById("preview-dialog").open && activeView === "sandbox" && !states.get(activeCase).closed) deferCase();
});
document.getElementById("export-session").addEventListener("click", () => {
  const payload = { schema: "copilot-design-sandbox-v1", generated_at: new Date().toISOString(), simulated: true, runtime_connected: false, external_action: "none", model_calls: 0, review_checklist: [...reviewChecks].map(index => checklist[index][0]), records: sessionRecords };
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "copilot-sandbox-session.json";
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
render();
