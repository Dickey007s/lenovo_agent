const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const V = require('./research-view.js');
const read = file=>JSON.parse(fs.readFileSync(path.join(__dirname,file),'utf8'));
const sources=['papers.json','engineering.json'].flatMap(file=>read(`research/followup-20260912/${file}`).sources);
const old=[...read('../copilot-research-library-20260911/sources.json').sources,...read('research/sources.json').sources];
const normalize=value=>value.toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');

test('incremental research has unique identifiers and does not recount prior work',()=>{
  assert.ok(sources.length>=7&&sources.length<=9);
  assert.equal(new Set(sources.map(s=>s.id)).size,sources.length);
  assert.equal(new Set(sources.map(s=>normalize(s.title))).size,sources.length);
  for(const s of sources) {
    assert.ok(!old.some(o=>normalize(o.title)===normalize(s.title)||o.url===s.url),s.id);
    assert.ok(Array.isArray(s.authors)&&s.authors.length>0);
    for(const key of ['title','url','date','type','method','read_scope','source_claim','design_inference','testable_counterexample']) assert.ok(typeof s[key]==='string'&&s[key].length>0,`${s.id} ${key}`);
    assert.equal(new URL(s.url).protocol,'https:');
    assert.ok(Array.isArray(s.limitations)&&s.limitations.length>0);
    assert.ok([1,2,3].includes(s.priority));
    assert.equal(s.verified_at,'2026-09-12');
  }
});
test('generated display data is exactly the canonical research data',()=>{
  const context={window:{}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'followup-data.js'),'utf8'),context);
  assert.deepEqual(JSON.parse(JSON.stringify(context.window.BOUNDARY_FOLLOWUP.sources)),sources);
});
test('paper and official filters partition the sources without hiding entries',()=>{
  const papers=V.select(sources,'paper'),official=V.select(sources,'official');
  assert.equal(papers.length+official.length,sources.length);
  assert.equal(official.length,3);
  assert.ok(papers.every(s=>!s.type.startsWith('official_')));
});
test('search matches Chinese design questions as well as English titles, case-insensitively',()=>{
  assert.equal(V.select(sources,'all','   MAGENTIC-UI  ')[0].id,'E01');
  assert.ok(V.select(sources,'all','委派').some(s=>s.id==='E02'));
  assert.equal(V.select(sources,'paper','magentic-ui').length,0);
});
test('empty result and clearing query preserve source data',()=>{
  const before=JSON.stringify(sources);
  assert.equal(V.select(sources,'all','nonexistent-765432').length,0);
  assert.equal(V.select(sources,'all','').length,sources.length);
  assert.equal(JSON.stringify(sources),before);
});
test('reading priorities are ordered, with papers first within a priority',()=>{
  const sorted=V.select(sources);
  for(let i=1;i<sorted.length;i++) assert.ok(sorted[i].priority>=sorted[i-1].priority);
  for(const p of [1,2,3]) {
    const group=sorted.filter(s=>s.priority===p), firstOfficial=group.findIndex(s=>s.type.startsWith('official_'));
    if(firstOfficial>=0) assert.ok(group.slice(firstOfficial).every(s=>s.type.startsWith('official_')));
  }
});
test('visible research keeps source claims separate from product hypotheses and limits',()=>{
  const app=fs.readFileSync(path.join(__dirname,'app.js'),'utf8');
  assert.ok(app.includes('escape(s.source_claim)'));
  assert.ok(app.includes('escape(s.design_inference)'));
  assert.ok(app.includes('escape(s.testable_counterexample)'));
  assert.ok(app.includes('escape(s.limitations.join'));
  assert.ok(app.includes('escape(s.method)'));
  assert.ok(app.includes('escape(s.date_note)'));
  assert.ok(app.includes('项目推论 · 待验证'));
});
test('every declared icon, including presenter actions, exists after the build',()=>{
  const context={window:{}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'icons.js'),'utf8'),context);
  for(const file of ['index.html','app.js','model.js','presenter.js']) {
    const code=fs.readFileSync(path.join(__dirname,file),'utf8');
    for(const match of code.matchAll(/Icon[A-Z][A-Za-z]+/g)) assert.ok(context.window.BOUNDARY_ICONS[match[0]],`${file} ${match[0]}`);
  }
});
