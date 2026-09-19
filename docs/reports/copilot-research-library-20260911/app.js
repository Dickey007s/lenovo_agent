(function () {
  "use strict";
  const data = window.COPILOT_LIBRARY;
  const types = { paper: "论文 / 预印本", docs: "官方规范 / 文档", blog: "官方博客 / 议程", report: "官方研究报告" };
  const readingOrder = ["S01", "S02", "S03", "S18", "S04", "S05", "S06", "S07", "S17", "S09", "S08", "S13", "S10", "S11", "S12", "S14", "S15", "S16"];
  const escape = value => String(value ?? "").replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
  const icon = name => window.LIBRARY_ICONS[name] || "";
  const byId = id => data.sources.find(source => source.id === id);
  const dateLabel = source => source.date || "滚动文档";
  const safeUrl = value => {
    try { const parsed = new URL(value); return parsed.protocol === "https:" ? parsed.href : ""; }
    catch { return ""; }
  };
  function link(url, label, className = "") {
    const href = safeUrl(url);
    return href ? `<a class="${escape(className)}" href="${escape(href)}" target="_blank" rel="noopener noreferrer">${escape(label)} ${icon("IconArrowUpRight")}</a>` : "";
  }
  function selectSources(filters) {
    const terms = (filters.query || "").trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    const result = data.sources.filter(source => {
      const text = [source.id, source.title, source.short_title, source.authors, source.institution, source.conclusion, source.method, source.publication, ...source.topics, ...source.limits, ...Object.values(source.implications)].join(" ").toLocaleLowerCase();
      return (!filters.topic || source.topics.includes(filters.topic)) && (!filters.type || source.type === filters.type) && terms.every(term => text.includes(term));
    });
    result.sort((a, b) => {
      if (filters.sort === "newest") return (b.year ?? -1) - (a.year ?? -1) || a.id.localeCompare(b.id);
      if (filters.sort === "oldest") return (a.year ?? 9999) - (b.year ?? 9999) || a.id.localeCompare(b.id);
      return readingOrder.indexOf(a.id) - readingOrder.indexOf(b.id);
    });
    return result;
  }
  function sourceRow(source) {
    return `<article class="source-row"><div class="source-index"><span>${escape(source.id)}</span>${icon(source.type === "paper" ? "IconFileText" : "IconBooks")}</div><div class="source-summary"><div class="source-meta"><span class="type-label ${escape(source.type)}">${escape(types[source.type])}</span><span>${escape(dateLabel(source))}</span><span>${escape(source.evidence_kind)}</span></div><button type="button" class="source-title" data-source="${escape(source.id)}">${escape(source.short_title)}</button><p class="original-title" lang="en">${escape(source.title)}</p><p class="conclusion">${escape(source.conclusion)}</p><div class="topic-list">${source.topics.map(topic => `<span>${escape(topic)}</span>`).join("")}</div></div><div class="source-actions"><button type="button" class="detail-button" data-source="${escape(source.id)}">研究详情 ${icon("IconArrowRight")}</button>${link(source.url, "原始来源")}${source.pdf_url ? link(source.pdf_url, "PDF") : ""}</div></article>`;
  }
  function detailMarkup(source) {
    return `<div class="source-meta"><span class="type-label ${escape(source.type)}">${escape(types[source.type])}</span><span>${escape(dateLabel(source))}</span></div><h2 id="detail-title">${escape(source.short_title)}</h2><p class="detail-original" lang="en">${escape(source.title)}</p><p class="author">${escape(source.authors)}<br>${escape(source.institution)} · ${escape(source.publication)}</p><div class="detail-links">${link(source.url, "打开原始来源", "primary-link")}${source.pdf_url ? link(source.pdf_url, "原文 PDF") : ""}${source.companion_url ? link(source.companion_url, "作者官方解读") : ""}</div><section class="detail-section"><h3>研究观察</h3><p class="key-finding">${escape(source.conclusion)}</p><dl><dt>方法</dt><dd>${escape(source.method)}</dd><dt>证据性质</dt><dd>${escape(source.evidence_kind)}。${escape(source.strength)}</dd><dt>限制</dt><dd><ul>${source.limits.map(item => `<li>${escape(item)}</li>`).join("")}</ul></dd></dl></section><section class="detail-section"><h3>对本项目的启发 <span class="design-label">设计推导</span></h3><div class="demo-implications">${Object.entries(source.implications).map(([demo, value]) => `<div><b>${escape(demo)}</b><p>${escape(value)}</p></div>`).join("")}</div></section><section class="detail-section provenance"><h3>来源核验</h3><dl><dt>定位</dt><dd>${escape(source.locator)}</dd><dt>日期依据</dt><dd>${escape(source.date_note)}</dd><dt>已读范围</dt><dd>${escape(source.read_scope)}</dd><dt>核验方式</dt><dd>${escape(source.verification_method)} · ${escape(source.verified_at)}</dd></dl></section>`;
  }
  function rulesMarkup(demo) {
    return data.rules.filter(rule => !demo || rule.demos.includes(demo)).map(rule => `<article class="rule-row"><div class="rule-title"><span>${escape(rule.id)}</span><h3>${escape(rule.name)}</h3><div>${rule.demos.map(item => `<b>${escape(item)}</b>`).join("")}</div></div><div class="rule-content"><p>${escape(rule.proposal)}</p><p class="rule-status">${escape(rule.status)}</p><dl><dt>验收问题</dt><dd>${escape(rule.acceptance)}</dd></dl><div class="rule-sources"><span>研究依据</span>${rule.sources.map(id => `<button type="button" data-source="${id}" title="${escape(byId(id).title)}">${id} ${escape(byId(id).short_title)}</button>`).join("")}</div></div></article>`).join("");
  }
  // Export only deterministic presentation helpers for source-level verification.
  window.LibraryView = { escape, safeUrl, selectSources, sourceRow, detailMarkup, rulesMarkup };
  const $ = id => document.getElementById(id);
  document.querySelectorAll("[data-icon]").forEach(element => { element.innerHTML = icon(element.dataset.icon); });
  $("metrics").innerHTML = `<div><strong>${data.sources.length}</strong><span>已打开的原始来源</span></div><div><strong>${data.sources.filter(source => source.type === "paper").length}</strong><span>论文，含预印本</span></div><div><strong>${data.sources.filter(source => source.type !== "paper").length}</strong><span>官方文档 / 文章 / 报告</span></div><div><strong>${data.rules.length}</strong><span>可验收交互推导</span></div>`;
  $("topic").innerHTML += data.topics.map(topic => `<option>${escape(topic)}</option>`).join("");
  function renderResults() {
    const result = selectSources({ query: $("query").value, topic: $("topic").value, type: $("type").value, sort: $("sort").value });
    $("result-count").textContent = `${result.length} / ${data.sources.length} 项`;
    $("results").innerHTML = result.length ? result.map(sourceRow).join("") : `<div class="empty-state">${icon("IconFileSearch")}<h3>没有匹配的来源</h3><button type="button" id="empty-reset">清除筛选</button></div>`;
  }
  function resetFilters() { $("query").value = ""; $("topic").value = ""; $("type").value = ""; $("sort").value = "reading"; renderResults(); }
  $("filters").addEventListener("submit", event => event.preventDefault());
  $("filters").addEventListener("input", event => { if (event.target === $("query")) renderResults(); });
  // A second render on search blur would detach the button being clicked.
  $("filters").addEventListener("change", event => { if (event.target !== $("query")) renderResults(); });
  $("filters").addEventListener("reset", event => { event.preventDefault(); resetFilters(); });
  function setView(view, focus = false) {
    ["library", "mapping", "method"].forEach(name => {
      const selected = name === view;
      $("tab-" + name).setAttribute("aria-selected", String(selected));
      $("tab-" + name).tabIndex = selected ? 0 : -1;
      $("panel-" + name).hidden = !selected;
    });
    if (focus) $("tab-" + view).focus();
  }
  document.querySelector(".view-tabs").addEventListener("keydown", event => {
    const tabs = ["library", "mapping", "method"];
    const current = tabs.indexOf(event.target.dataset.view);
    if (current < 0) return;
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (step || event.key === "Home" || event.key === "End") {
      event.preventDefault();
      setView(tabs[event.key === "Home" ? 0 : event.key === "End" ? 2 : (current + step + tabs.length) % tabs.length], true);
    }
  });
  let detailTrigger = null;
  document.addEventListener("click", event => {
    const sourceButton = event.target.closest("[data-source]");
    if (sourceButton) {
      const source = byId(sourceButton.dataset.source);
      if (!source) return;
      detailTrigger = sourceButton;
      $("detail-id").textContent = source.id + " / 来源详情";
      $("detail-body").innerHTML = detailMarkup(source);
      $("source-dialog").showModal();
      $("source-dialog").scrollTop = 0;
      $("close-detail").focus();
    }
    const viewButton = event.target.closest("[data-view]");
    if (viewButton) setView(viewButton.dataset.view);
    if (event.target.closest("#empty-reset")) { resetFilters(); $("query").focus(); }
  });
  $("close-detail").addEventListener("click", () => $("source-dialog").close());
  $("source-dialog").addEventListener("close", () => { if (detailTrigger && detailTrigger.isConnected) detailTrigger.focus(); });
  $("demo-filter").addEventListener("change", () => { $("rules").innerHTML = rulesMarkup($("demo-filter").value); });
  $("rules").innerHTML = rulesMarkup("");
  $("ledger").innerHTML = data.sources.map(source => `<tr><th><button type="button" class="ledger-source" data-source="${source.id}">${source.id}<br>${escape(source.short_title)}</button></th><td>${escape(source.date_note)}</td><td>${escape(source.read_scope)}</td><td class="date-cell">${escape(source.verified_at)}</td></tr>`).join("");
  $("limitations").innerHTML = data.excluded_or_limited.map(item => `<article class="limitation"><h4>${escape(item.title)}</h4><p>${escape(item.reason)}</p></article>`).join("");
  renderResults();
})();
