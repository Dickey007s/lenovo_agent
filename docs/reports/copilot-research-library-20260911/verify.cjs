"use strict";
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const { createRequire } = require("node:module");
const root = __dirname;
const read = name => fs.readFileSync(path.join(root, name), "utf8");
const data = JSON.parse(read("sources.json"));
const checks = [];
const reportPath = path.join(root, "verification.json");
const report = { status: "running", checked_at: new Date().toISOString(), scope: "Local source, data schema and Node VM presentation checks only", browser: "not_run_by_this_script", runtime: "not_run", provider_calls: 0, external_actions: 0, source_urls_rechecked: false, checks };
fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + "\n");
function test(name, fn) {
  try { fn(); checks.push({ name, status: "passed" }); }
  catch (error) { checks.push({ name, status: "failed", detail: String(error.message) }); }
}
test("18 unique source records and original URLs", () => {
  assert.equal(data.sources.length, 18);
  assert.equal(new Set(data.sources.map(source => source.id)).size, 18);
  assert.equal(new Set(data.sources.map(source => source.url)).size, 18);
});
test("At least six papers and four official non-paper records", () => {
  assert.equal(data.sources.filter(source => source.type === "paper").length, 10);
  assert.equal(data.sources.filter(source => source.type !== "paper").length, 8);
  assert.equal(data.sources.filter(source => source.type === "docs").length, 4);
});
for (const source of data.sources) {
  test(`${source.id}: required provenance, constraints and three Demo implications`, () => {
    for (const key of ["id", "title", "authors", "institution", "date_note", "type", "publication", "evidence_kind", "conclusion", "method", "strength", "locator", "read_scope", "verified_at", "verification_method"]) assert.ok(typeof source[key] === "string" && source[key].trim(), key);
    assert.ok(source.limits.length >= 2);
    assert.ok(source.topics.length && source.topics.every(topic => data.topics.includes(topic)));
    assert.deepEqual(Object.keys(source.implications), ["Demo1", "Demo2", "Demo3"]);
    assert.equal(source.verified_at, "2026-09-11");
    assert.ok(source.year === null || (Number.isInteger(source.year) && source.year >= 1999 && source.year <= 2026));
    for (const key of ["url", "pdf_url", "companion_url"]) {
      if (!source[key]) continue;
      const url = new URL(source[key]);
      assert.equal(url.protocol, "https:");
      assert.equal(url.username + url.password, "");
      assert.equal(url.search, "");
    }
  });
}
test("Six requested themes have coverage", () => {
  assert.equal(data.topics.length, 6);
  for (const topic of data.topics) assert.ok(data.sources.some(source => source.topics.includes(topic)));
});
test("2024, 2025 and 2026 sources plus classic works", () => {
  for (const year of [1999, 2002, 2019, 2024, 2025, 2026]) assert.ok(data.sources.some(source => source.year === year));
});
test("Rolling docs have no fabricated publication date", () => {
  for (const id of ["S10", "S11"]) {
    const source = data.sources.find(item => item.id === id);
    assert.equal(source.date, null);
    assert.equal(source.year, null);
  }
});
test("Ethics full-text limitation and excluded source stay explicit", () => {
  assert.equal(data.sources.find(source => source.id === "S08").pdf_url, null);
  assert.match(data.sources.find(source => source.id === "S08").read_scope, /全文未核验/);
  assert.equal(data.excluded_or_limited.length, 3);
});
test("New experimental sources explicitly remain preprints", () => {
  for (const id of ["S09", "S17"]) assert.match(data.sources.find(source => source.id === id).publication, /预印本/);
});
test("Seven design rules have valid references and non-verified statuses", () => {
  assert.equal(data.rules.length, 7);
  for (const rule of data.rules) {
    assert.ok(rule.name && rule.proposal && rule.acceptance && rule.status);
    assert.ok(rule.sources.length >= 2 && rule.sources.every(id => data.sources.some(source => source.id === id)));
    assert.ok(rule.demos.every(demo => ["Demo1", "Demo2", "Demo3"].includes(demo)));
  }
});
for (const file of ["app.js", "icons.js", "sources-data.js", "build.cjs", "verify.cjs"]) {
  test(`${file}: JavaScript syntax`, () => new vm.Script(read(file), { filename: file }));
}
test("Generated data is identical to sources.json", () => {
  const context = { window: {} };
  vm.runInNewContext(read("sources-data.js"), context);
  assert.deepEqual(JSON.parse(JSON.stringify(context.window.COPILOT_LIBRARY)), data);
});
test("Stylesheet parses using repository PostCSS", () => {
  const requireWeb = createRequire(path.resolve(root, "../../../apps/web/package.json"));
  const requireNext = createRequire(requireWeb.resolve("next/package.json"));
  requireNext("postcss").parse(read("styles.css"));
});
test("HTML loads only local CSS and script assets", () => {
  const html = read("index.html");
  assert.ok(!/<iframe|<object|<embed|<base\b/i.test(html));
  for (const match of html.matchAll(/(?:src|href)="([^"]+)"/g)) {
    const target = match[1];
    if (target.startsWith("#")) continue;
    assert.ok(!/^(https?:)?\/\//i.test(target), target);
    assert.ok(fs.existsSync(path.resolve(root, target)), target);
  }
});
test("CSP denies connections, frames, forms and remote font loading", () => {
  const html = read("index.html");
  for (const value of ["default-src 'none'", "connect-src 'none'", "frame-src 'none'", "form-action 'none'", "font-src 'none'", "object-src 'none'"]) assert.ok(html.includes(value));
});
test("UI source has no network or Runtime connection APIs", () => {
  const code = read("app.js");
  assert.ok(!/\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon)\b/.test(code));
  assert.ok(!/https?:\/\//.test(read("styles.css")));
  assert.ok(!/@import/.test(read("styles.css")));
  assert.ok(!/<img[^>]+src=["']https?:/i.test(read("index.html")));
});
test("Text files have no trailing whitespace or merge markers", () => {
  for (const name of fs.readdirSync(root).filter(name => /\.(html|css|js|cjs|json|md)$/.test(name))) {
    const text = read(name);
    assert.ok(!/^(?:<{7}|={7}|>{7})/m.test(text), name);
    assert.ok(!/[\t ]+$/m.test(text), name);
  }
});
test("Local icon set and license exist", () => {
  const context = { window: {} };
  vm.runInNewContext(read("icons.js"), context);
  assert.equal(Object.keys(context.window.LIBRARY_ICONS).length, 15);
  assert.ok(Object.values(context.window.LIBRARY_ICONS).every(value => value.startsWith("<svg") && !/<script|https?:/i.test(value.replace(/http:\/\/www\.w3\.org\/2000\/svg/g, ""))));
  assert.match(read("TABLER-LICENSE"), /MIT License/);
});

// This minimal event/element harness deliberately does not claim browser DOM behavior.
const elements = new Map();
class Element {
  constructor(id) { this.id = id; this.value = id === "sort" ? "reading" : ""; this.innerHTML = ""; this.textContent = ""; this.hidden = false; this.listeners = {}; this.attributes = {}; this.dataset = {}; this.isConnected = true; this.tabIndex = 0; }
  addEventListener(type, fn) { this.listeners[type] = fn; }
  setAttribute(key, value) { this.attributes[key] = value; }
  focus() { this.focused = true; }
  showModal() { this.open = true; }
  close() { this.open = false; if (this.listeners.close) this.listeners.close(); }
}
function element(id) { if (!elements.has(id)) elements.set(id, new Element(id)); return elements.get(id); }
const document = { getElementById: element, querySelectorAll: () => [], querySelector: element, listeners: {}, addEventListener(type, fn) { this.listeners[type] = fn; } };
const context = { window: {}, document, URL };
vm.createContext(context);
vm.runInContext(read("sources-data.js"), context);
vm.runInContext(read("icons.js"), context);
vm.runInContext(read("app.js"), context);
const view = context.window.LibraryView;
test("Initial render contains all 18 source rows", () => {
  assert.equal((element("results").innerHTML.match(/class="source-row"/g) || []).length, 18);
  assert.equal(element("result-count").textContent, "18 / 18 项");
});
test("Default reading sequence starts at classic foundations", () => {
  assert.deepEqual(Array.from(view.selectSources({}).slice(0, 3), source => source.id), ["S01", "S02", "S03"]);
});
test("Search accepts Chinese and case-insensitive multi-term English", () => {
  assert.ok(view.selectSources({ query: "认知" }).some(source => source.id === "S04"));
  assert.deepEqual(Array.from(view.selectSources({ query: "HORVITZ initiative" }), source => source.id), ["S01"]);
});
test("Impossible search gives zero results", () => assert.equal(view.selectSources({ query: "zzzz-no-such-source-99999" }).length, 0));
for (const topic of data.topics) {
  test(`Topic filter: ${topic}`, () => {
    const result = view.selectSources({ topic });
    assert.ok(result.length && result.every(source => source.topics.includes(topic)));
  });
}
test("Topic and type filters use intersection, not union", () => {
  const result = view.selectSources({ topic: "拒绝与延后", type: "docs" });
  assert.deepEqual(Array.from(result, source => source.id).sort(), ["S11", "S12"]);
});
test("Year sorting leaves undated docs at the end", () => {
  for (const sort of ["newest", "oldest"]) assert.ok(view.selectSources({ sort }).slice(-2).every(source => source.year === null));
  assert.equal(view.selectSources({ sort: "newest" })[0].year, 2026);
  assert.equal(view.selectSources({ sort: "oldest" })[0].year, 1999);
});
test("Details expose methods, limits, three Demos and verification date", () => {
  for (const source of data.sources) {
    const markup = view.detailMarkup(source);
    for (const text of [source.method, source.limits[0], source.read_scope, source.verified_at, "Demo1", "Demo2", "Demo3", "设计推导"]) assert.ok(markup.includes(view.escape(text)), source.id + ": " + text);
  }
});
test("HTML escaping protects titles and fields", () => {
  const source = { ...data.sources[0], short_title: '<img src=x onerror="alert(1)">' };
  const html = view.sourceRow(source) + view.detailMarkup(source);
  assert.ok(!html.includes("<img"));
  assert.ok(html.includes("&lt;img"));
});
test("Unsafe protocols never become source hyperlinks", () => {
  for (const url of ["javascript:alert(1)", "data:text/html,unsafe", "file:///secret", "http://example.org"]) assert.equal(view.safeUrl(url), "");
  assert.equal(view.safeUrl("https://arxiv.org/abs/2501.10909"), "https://arxiv.org/abs/2501.10909");
});
test("External source links carry noopener and noreferrer", () => {
  const links = [...view.detailMarkup(data.sources[0]).matchAll(/<a\b[^>]*>/g)].map(match => match[0]);
  assert.ok(links.length >= 2 && links.every(tag => tag.includes('target="_blank"') && tag.includes('rel="noopener noreferrer"')));
});
test("Demo mapping filters only applicable rules", () => {
  for (const demo of ["Demo1", "Demo2", "Demo3"]) {
    const markup = view.rulesMarkup(demo);
    for (const rule of data.rules) assert.equal(markup.includes(`<span>${rule.id}</span>`), rule.demos.includes(demo));
  }
});
test("Filter event renders empty result and reset restores all", () => {
  element("query").value = "zzzz-no-such-source-99999";
  element("filters").listeners.input({ target: element("query") });
  assert.ok(element("results").innerHTML.includes("没有匹配的来源"));
  element("filters").listeners.reset({ preventDefault() {} });
  assert.equal(element("result-count").textContent, "18 / 18 项");
});
test("Search blur preserves rendered buttons while select changes rerender", () => {
  element("results").innerHTML = "existing-render";
  element("filters").listeners.change({ target: element("query") });
  assert.equal(element("results").innerHTML, "existing-render");
  element("filters").listeners.change({ target: element("type") });
  assert.ok(element("results").innerHTML.includes("source-row"));
});
test("Tab events project aria and hidden states", () => {
  const trigger = new Element("tab-mapping"); trigger.dataset.view = "mapping";
  document.listeners.click({ target: { closest(selector) { return selector === "[data-view]" ? trigger : null; } } });
  assert.equal(element("panel-library").hidden, true);
  assert.equal(element("panel-mapping").hidden, false);
  assert.equal(element("tab-mapping").attributes["aria-selected"], "true");
});
test("Detail click/close event handlers restore trigger focus in harness", () => {
  const trigger = new Element("source-trigger"); trigger.dataset.source = "S09";
  document.listeners.click({ target: { closest(selector) { return selector === "[data-source]" ? trigger : null; } } });
  assert.equal(element("source-dialog").open, true);
  assert.ok(element("detail-body").innerHTML.includes("2601.18033"));
  element("close-detail").listeners.click();
  assert.equal(element("source-dialog").open, false);
  assert.equal(trigger.focused, true);
});
test("Responsive constraints exist without viewport-scaled font or gradients", () => {
  const css = read("styles.css");
  assert.match(css, /@media \(max-width: 600px\)/);
  assert.match(css, /100dvh/);
  assert.ok(!/font-size:[^;]*(?:vw|vh|clamp)/.test(css));
  assert.ok(!/gradient\(/.test(css));
});
test("Narrative preserves Draft, coverage failure and evaluation boundary", () => {
  const research = read("research.md");
  for (const text of ["Demo3 仍是 Draft", "external_action=none", "内容完整性失败", "本轮没有修复", "不是 PRISMA", "未完成会议要求"]) assert.ok(research.includes(text), text);
});
report.status = checks.every(check => check.status === "passed") ? "passed" : "failed";
report.passed = checks.filter(check => check.status === "passed").length;
report.failed = checks.filter(check => check.status === "failed").length;
report.note = "Passing asserts only the checks listed. Web opening was performed separately by the research agent; browser pixels, native dialog behavior, source correctness and Runtime are not validated here.";
fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + "\n");
for (const check of checks.filter(check => check.status === "failed")) console.error(check.name + ": " + check.detail);
console.log(`${report.passed} passed, ${report.failed} failed. Source/VM checks only; no browser or Runtime execution.`);
process.exitCode = report.failed ? 1 : 0;
