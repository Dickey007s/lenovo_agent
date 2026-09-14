const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {createRequire} = require('node:module');
const root = __dirname;
let count = 0;
const check = (condition, message) => { assert.ok(condition,message); count++; };
const ledger = JSON.parse(fs.readFileSync(path.join(root,'research','sources.json'),'utf8'));
const previous = JSON.parse(fs.readFileSync(path.join(root,'../copilot-research-library-20260911/sources.json'),'utf8'));
check(ledger.sources.length===8,'8 incremental research entries');
check(new Set(ledger.sources.map(s=>s.id)).size===8,'unique IDs');
for(const s of ledger.sources) {
  check(!previous.sources.some(p=>p.url===s.url || p.title===s.title),`${s.id} not duplicate`);
  check(s.verified_at==='2026-09-11',`${s.id} access date`);
  for(const key of ['url','title','authors','read_scope','source_claim','method','limitations','design_inference','publication_status']) check(Boolean(s[key]?.length),`${s.id} ${key}`);
  check(new URL(s.url).protocol==='https:',`${s.id} original HTTPS link`);
}
const context = {window:{}};
vm.runInNewContext(fs.readFileSync(path.join(root,'research-data.js'),'utf8'),context);
check(context.window.BOUNDARY_RESEARCH.sources.length===8,'generated research row count');
for(const row of context.window.BOUNDARY_RESEARCH.sources) {
  const s = ledger.sources.find(s=>s.id===row.id);
  check(row.url===s.url && row.title===s.title,`${row.id} canonical metadata`);
}
const html = fs.readFileSync(path.join(root,'index.html'),'utf8');
check(html.includes("connect-src 'none'"),'network disconnected');
check(!/<(?:iframe|object|embed)\b/i.test(html),'no embedded remote surfaces');
check(!/\son\w+\s*=/i.test(html),'no inline event handlers');
for(const match of html.matchAll(/(?:src|href)="([^"]+)"/g)) {
  const link = match[1];
  if (/^https:/.test(link) || link.startsWith('#')) continue;
  check(fs.existsSync(path.resolve(root,link)),`local asset/link exists: ${link}`);
}
const app = fs.readFileSync(path.join(root,'app.js'),'utf8');
check(!/\b(fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(/.test(app),'no network calls in app');
check(app.includes('escape(s.title)') && app.includes('escape(s.recipient)'),'dynamic text escaped');
const requireWeb = createRequire(path.resolve(root,'../../../apps/web/package.json'));
const requireNext = createRequire(requireWeb.resolve('next/package.json'));
requireNext('postcss').parse(fs.readFileSync(path.join(root,'styles.css'),'utf8'));
count++;
const report = {checked_at:new Date().toISOString(),checks_passed:count,scope:'Local research data, generated metadata, assets and source syntax only',browser:'not_run_by_this_script',runtime:'not_run',source_urls_rechecked:false};
fs.writeFileSync(path.join(root,'static-verification.json'),JSON.stringify(report,null,2)+'\n');
console.log(`${count} source/data assertions passed. No browser, network or Runtime executed.`);
