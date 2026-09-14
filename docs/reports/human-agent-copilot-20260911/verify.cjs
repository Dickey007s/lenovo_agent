"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { createRequire } = require("node:module");

const root = __dirname;
const source = file => fs.readFileSync(path.join(root, file), "utf8");
let passed = 0;
const checks = [];
fs.writeFileSync(path.join(root,"source-check-results.json"), JSON.stringify({ suite: "copilot-design-source-checks", status: "running", passed: 0 }, null, 2) + "\n", "utf8");
function test(name, fn) {
  fn();
  passed += 1;
  checks.push({ name, status: "passed" });
  console.log(`PASS ${String(passed).padStart(2, "0")} ${name}`);
}

// This source-level harness is deliberately not a browser or DOM renderer.
function harness() {
  const nodes = new Map();
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, { innerHTML: "", textContent: "", hidden: true, open: false, value: "", dataset: {}, callbacks: {}, querySelectorAll: () => [], addEventListener(name, callback) { this.callbacks[name] = callback; }, showModal() { this.open = true; }, close() { this.open = false; }, classList: { toggle() {} } });
    return nodes.get(id);
  }
  const document = { getElementById: node, querySelectorAll: () => [], addEventListener() {} };
  const context = vm.createContext({ window: {}, document, Date, Map, Set, console, setTimeout: () => {} });
  for (const file of ["icons.js", "cases.js", "app.js"]) vm.runInContext(source(file), context, { filename: file });
  return { run: script => vm.runInContext(script, context), node };
}
const h = harness();
const fixtures = h.run("cases");
test("eight cases and unique IDs", () => { assert.equal(fixtures.length, 8); assert.equal(new Set(fixtures.map(item => item.id)).size, 8); });
test("case contract includes user, trigger, authority and acceptance", () => { for (const item of fixtures) for (const key of ["role","trigger","reason","impact","retained","prohibited","evidence","permission","branch","next","mapping","acceptance","refs"]) assert.ok(item[key], `${item.id}.${key}`); });
test("cases have both independent evidence and permission facts", () => { for (const item of fixtures) assert.notEqual(item.evidence, item.permission); });
test("all choice cases have at least two candidates", () => { for (const item of fixtures.filter(item => item.mode === "choice")) assert.ok(item.candidates.length >= 2); });
test("initial candidate is not preselected", () => assert.equal(h.run("states.get('B01').selected"), null));
test("initial confirm is disabled in generated markup", () => assert.match(h.node("app").innerHTML, /id="confirm-case" disabled/));
test("unselected confirmation writes no local record", () => { h.run("confirmCase()"); assert.equal(h.run("sessionRecords.length"), 0); });
test("selection records local intent, never a Runtime receipt", () => { h.run("states.get('B01').selected=1;confirmCase()"); assert.equal(h.run("sessionRecords.length"), 1); assert.equal(h.run("sessionRecords[0].simulated"), true); assert.equal(h.run("sessionRecords[0].runtime_connected"), false); assert.equal(h.run("sessionRecords[0].external_action"), "none"); });
test("duplicate confirmation is ignored", () => { h.run("confirmCase()"); assert.equal(h.run("sessionRecords.length"), 1); });
for (const fault of ["conflict", "offline", "stale"]) {
  test(`${fault} does not mark success`, () => { const t = harness(); t.run(`states.get('B01').selected=0;states.get('B01').fault='${fault}';confirmCase()`); assert.equal(t.run("states.get('B01').handled"), false); assert.equal(t.run("sessionRecords[0].action"), "simulated-rejected-or-unknown"); });
  test(`${fault} cannot prevent review exit`, () => { const t = harness(); t.run(`states.get('B01').fault='${fault}';deferCase()`); assert.equal(t.run("states.get('B01').closed"), true); assert.match(t.node("app").innerHTML, /暂缓回执未确认/); });
}
test("stale source clears old candidate and blocks new acceptance", () => { const t = harness(); t.run("states.get('B01').selected=0;states.get('B01').fault='stale';confirmCase()"); assert.equal(t.run("states.get('B01').selected"), null); assert.equal(t.run("states.get('B01').stale"), true); assert.match(t.node("app").innerHTML, /id="confirm-case" disabled/); });
test("refresh clears candidate and records no Runtime activity", () => { const t = harness(); t.run("states.get('B01').selected=1"); t.node("refresh-case").callbacks.click(); assert.equal(t.run("states.get('B01').selected"), null); assert.equal(t.run("states.get('B01').version"), 2); assert.equal(t.run("sessionRecords[0].runtime_connected"), false); });
test("reset preserves old local records", () => { const t = harness(); t.run("states.get('B01').selected=0;confirmCase()"); t.node("reset-case").callbacks.click(); assert.equal(t.run("sessionRecords.length"), 2); assert.equal(t.run("states.get('B01').handled"), false); });
test("business recommendation is disabled before an initial choice", () => { const t = harness(); t.run("openCase('B02')"); assert.match(t.node("app").innerHTML, /id="show-recommendation" disabled/); });
test("business recommendation enabled after initial choice", () => { const t = harness(); t.run("openCase('B02');states.get('B02').selected=0;render()"); assert.doesNotMatch(t.node("app").innerHTML, /id="show-recommendation" disabled/); });
for (const id of ["B03", "B04"]) test(`${id} records handoff only, not execution`, () => { const t = harness(); t.run(`openCase('${id}');confirmCase()`); assert.match(t.run("sessionRecords[0].outcome"), /未建立审批/); assert.equal(t.run("sessionRecords[0].external_action"), "none"); });
test("budget continuation does not claim to create a Run", () => { const t = harness(); t.run("openCase('B05');confirmCase()"); assert.match(t.run("sessionRecords[0].outcome"), /未创建真实 Run/); });
test("Agent-owned retry does not require input", () => { const t = harness(); t.run("openCase('B06')"); assert.doesNotMatch(t.node("app").innerHTML, /<textarea/); assert.doesNotMatch(t.node("app").innerHTML, /id="confirm-case" disabled/); t.run("confirmCase()"); assert.match(t.run("sessionRecords[0].outcome"), /尚无模型调用/); });
test("partial Worker case requires explicit choice", () => { const t = harness(); t.run("openCase('B07');confirmCase()"); assert.equal(t.run("sessionRecords.length"), 0); });
test("file acknowledgment does not approve business Gate", () => { const t = harness(); t.run("openCase('B08');confirmCase()"); assert.match(t.run("sessionRecords[0].outcome"), /业务 Gate 仍未通过/); });
test("library risk filter selects R3 alone", () => { const t = harness(); t.run("libraryRisk='R3';renderLibrary()"); assert.match(t.node("app").innerHTML, /高影响、不可逆操作/); assert.doesNotMatch(t.node("app").innerHTML, /同一句话有两处原文/); });
test("library supports explicit empty state", () => { const t = harness(); t.run("librarySearch='no-match-000';renderLibrary()"); assert.match(t.node("app").innerHTML, /没有匹配的案例/); });
test("HTML escaping prevents source text injecting markup", () => assert.equal(h.run("escapeHTML('<script>')"), "&lt;script&gt;"));
test("no application network or provider calls", () => assert.doesNotMatch(source("app.js"), /\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\b|\bEventSource\b|\bsendBeacon\b/));
test("CSP blocks network connections on both pages", () => { for (const file of ["index.html", "report.html"]) assert.match(source(file), /connect-src 'none'/); });
test("no external scripts, styles or media dependencies", () => { for (const file of ["index.html", "report.html"]) assert.doesNotMatch(source(file), /(?:src|href)=["']https?:[^"']+\.(?:js|css|png|jpg|svg)/); });
test("local HTML references resolve", () => { for (const file of ["index.html", "report.html"]) for (const match of source(file).matchAll(/(?:href|src)="([^"#]+)"/g)) if (!/^https?:/.test(match[1])) assert.ok(fs.existsSync(path.resolve(root,match[1])), `${file}: ${match[1]}`); });
test("Markdown local links resolve", () => { for (const file of ["README.md", "guide.md", "sources.md", "verification.md"]) for (const match of source(file).matchAll(/\]\(([^)]+)\)/g)) if (!/^https?:/.test(match[1])) assert.ok(fs.existsSync(path.resolve(root,match[1])), `${file}: ${match[1]}`); });
test("Tabler icon assets have all requested symbols", () => { for (const name of source("app.js").matchAll(/icon\("([A-Za-z0-9]+)"\)/g)) assert.ok(h.run(`window.COPILOT_ICONS['${name[1]}']`),name[1]); });
test("design source image exists with expected original size", () => assert.equal(fs.statSync(path.join(root,"reference-evidence.png")).size,1561536));
test("new text artifacts contain no trailing whitespace or conflict markers", () => { for (const file of fs.readdirSync(root).filter(name => /\.(html|css|js|cjs|md)$/.test(name))) { const text = source(file); assert.doesNotMatch(text, /[\t ]+\r?$/m, file); assert.doesNotMatch(text, /^(?:<<<<<<<|=======|>>>>>>>)(?: |$)/m, file); } });
test("responsive CSS parses with repository PostCSS", () => { const requireWeb = createRequire(path.resolve(root,"../../../apps/web/package.json")); const requireNext = createRequire(requireWeb.resolve("next/package.json")); requireNext("postcss").parse(source("styles.css")); });
fs.writeFileSync(path.join(root,"source-check-results.json"), JSON.stringify({ generated_at: new Date().toISOString(), suite: "copilot-design-source-checks", status: "passed", scope: "Node VM source logic, markup strings, static assets and PostCSS syntax only", passed, browser_rendering_verified: false, runtime_verified: false, external_action: "none", checks }, null, 2) + "\n", "utf8");
console.log(`\n${passed} source-level checks passed. No browser, Runtime, Provider, database or external action was executed.`);
