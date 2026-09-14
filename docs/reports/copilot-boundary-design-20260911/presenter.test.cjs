const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const M = require('./model.js');
const P = require('./presenter.js');
const apply = (s,...actions) => actions.reduce(M.reduce,s);
const consent = s => apply(s,{type:'ack',value:true},{type:'approve'});
const primary = s => P.present(s).actions[0];

for (const [id,expectedAction] of Object.entries({send:'approve',draft:undefined,evidence:'resolve',forbidden:'fallback',changed:'approve',expired:'approve',unknown:'reconcile',takeover:'return'})) {
  test(`${id}: first-screen business status and next action match the model`,()=>{
    const s = M.initial(id), p = P.present(s);
    assert.equal(p.code,M.decision(s).code);
    for(const key of ['title','reason','next','currentFile','currentResult','sendStatus','realStatus','history']) assert.ok(p[key]?.length,key);
    assert.equal(primary(s)?.id,expectedAction);
    assert.equal(p.realStatus,'真实邮件：未发送');
    assert.doesNotMatch([p.title,p.reason,p.next].join(' '),/Runtime|回执|策略|分支|Artifact|Snapshot/);
  });
}

test('confirm screen explains the disabled action and checkbox is not approval',()=>{
  const s = M.initial();
  assert.equal(primary(s).disabled,true);
  assert.match(P.present(s).next,/先勾选/);
  const checked = M.reduce(s,{type:'ack',value:true});
  assert.equal(primary(checked).id,'approve'); assert.equal(primary(checked).disabled,false);
  assert.equal(P.present(checked).sendStatus,'尚未发送'); assert.equal(checked.approval,null);
});
test('approval tells the user that sending has not happened',()=>{
  const p = P.present(consent(M.initial()));
  assert.match(p.title,/还没有发送/); assert.equal(p.sendStatus,'尚未发送');
  assert.match(p.expiry,/剩余 5 分钟/); assert.equal(p.actions[0].id,'execute');
  assert.match(p.next,/演示一次发送/); assert.match(p.next,/不会发送真实邮件/);
});
test('expiry explanation disappears after re-confirmation; initial note is not current truth',()=>{
  const s = M.initial('expired'); assert.match(P.present(s).reason,/已过期/);
  const next = P.present(consent(s));
  assert.doesNotMatch(next.reason,/过期|失效/); assert.match(next.title,/还没有发送/);
});
for(const [field,label,after] of [['file','附件','项目周报 v3.pdf'],['recipient','收件人','new-recipient@example.com'],['policy','授权规则','版本 2']]) {
  test(`${field}: show the exact old and new scope, not a generic mismatch`,()=>{
    const p = P.present(M.reduce(consent(M.initial()),{type:'mutate',field}));
    assert.equal(p.changes.length,1); assert.equal(p.changes[0][0],label); assert.equal(p.changes[0][2],after);
    assert.match(p.reason,/已改变/); assert.equal(p.actions[0].disabled,true);
  });
}
test('changed fixture compares v2 to v3; changed-back scope still explains revocation',()=>{
  assert.deepEqual(P.present(M.initial('changed')).changes,[['附件','项目周报 v2.pdf','项目周报 v3.pdf']]);
  const p = P.present(apply(consent(M.initial()),{type:'mutate',field:'recipient'},{type:'mutate',field:'recipient'}));
  assert.deepEqual(p.changes,[]); assert.match(p.reason,/改回原值/); assert.match(p.reason,/已撤销/);
});
for(const choice of ['all','guided']) test(`${choice}: actual number and qualifier survive draft generation without email permission`,()=>{
  const selected = M.reduce(M.initial('evidence'),{type:'select',value:choice});
  assert.match(P.present(selected).next,/写入 v3 草稿；保留 v2，不发送邮件/);
  const resolved = M.reduce(selected,{type:'resolve'}), p = P.present(resolved);
  assert.equal(p.currentFile,'项目周报 v3.pdf');
  assert.equal(p.basisResult,P.basis[choice].result);
  assert.match(p.title,/v3 草稿，尚未发送/); assert.match(p.history,/历史 v2/);
  assert.equal(p.sendStatus,'尚未发送'); assert.equal(p.actions.length,0);
  assert.equal(resolved.approval,null);
  assert.match(p.basisResult,choice==='all'?/80%（40\/50）.*未提供引导/:/92%（46\/50）.*不代表未经引导/);
});
test('internal fallback continues to show unapproved promise and no approval action',()=>{
  const p = P.present(M.reduce(M.initial('forbidden'),{type:'fallback'}));
  assert.match(p.title,/仍不能发送/); assert.match(p.reason,/折扣承诺仍未获授权/);
  assert.equal(p.actions.length,0); assert.equal(p.sendStatus,'尚未发送');
});
for (const result of ['unavailable','not_found']) test(`${result}: unknown is never projected as failure, cancellation or success`,()=>{
  const s = M.reduce(M.initial('unknown'),{type:'reconcile',result}), p = P.present(s);
  assert.equal(s.attempts,1); assert.match(p.title,/不确定是否发送成功/);
  assert.match(p.next,/不重新发送/); assert.match(p.next,/不能当作未发送/);
  assert.equal(p.actions.find(a=>a.id==='execute').disabled,true);
  assert.equal(p.actions.some(a=>a.id==='cancel'),false);
});
test('lookup success removes old uncertainty but still states no real email',()=>{
  const s = M.reduce(M.initial('unknown'),{type:'reconcile',result:'confirmed'}), p=P.present(s);
  assert.equal(s.attempts,1); assert.equal(p.title,'演示发送成功');
  assert.equal(p.sendStatus,'演示已发送一次'); assert.match(p.reason,/真实邮件没有发出/);
  assert.doesNotMatch(p.reason,/不确定|丢失/); assert.equal(p.actions.length,0);
});
test('pause and return describe actual available operations, never fake human editing',()=>{
  const paused=M.reduce(consent(M.initial()),{type:'pause'}), p=P.present(paused);
  assert.match(p.reason,/不再继续处理/); assert.match(p.next,/不会自动发送/);
  assert.equal(p.actions[0].label,'让 Agent 继续处理');
  const returned=M.reduce(paused,{type:'return'});
  assert.equal(primary(returned).id,'approve'); assert.equal(primary(returned).disabled,true);
  assert.equal(returned.attempts,0);
});
test('deferring a content decision does not use email-cancellation language',()=>{
  const s=M.reduce(M.initial('evidence'),{type:'defer'}), p=P.present(s);
  assert.match(p.next,/不会.*更新草稿/); assert.equal(p.actions[1].label,'取消本次处理');
  const cancelled=P.present(M.reduce(s,{type:'cancel'}));
  assert.equal(cancelled.title,'本次数据处理已取消'); assert.doesNotMatch(cancelled.reason,/撤回/);
});
test('cancelled send explains pre-send cancellation, not recall',()=>{
  const p=P.present(M.reduce(consent(M.initial()),{type:'cancel'}));
  assert.match(p.reason,/取消发生在发送前/); assert.match(p.reason,/不是撤回/);
  assert.equal(p.sendStatus,'尚未发送'); assert.equal(p.actions.length,0);
});
test('presenter does not alter authority or revive grants while reading',()=>{
  for(const c of M.cases) { const s=M.initial(c.id), before=JSON.stringify(s); P.present(s); assert.equal(JSON.stringify(s),before); }
});
test('all reachable bounded sequences keep enabled send action equal to authority',()=>{
  const actions=[{type:'ack',value:true},{type:'approve'},{type:'execute'},{type:'pause'},{type:'return'},{type:'defer'},{type:'reopen'},{type:'cancel'},{type:'fallback'},{type:'expire'},{type:'mutate',field:'file'},{type:'select',value:'all'},{type:'resolve'},{type:'reconcile',result:'not_found'}];
  for(const c of M.cases) for(const a of actions) for(const b of actions) for(const e of actions) {
    const s=apply(M.initial(c.id),a,b,e), p=P.present(s);
    assert.equal(p.actions.some(x=>x.id==='execute'&&!x.disabled),M.decision(s).code==='ready'&&M.approved(s));
    if(s.receipt==='unknown') assert.equal(p.title,'不确定是否发送成功');
    assert.equal(p.realStatus,'真实邮件：未发送');
  }
});
test('HTML uses the tested presenter and all static render targets exist',()=>{
  const html=fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
  const app=fs.readFileSync(path.join(__dirname,'app.js'),'utf8');
  assert.match(app,/d = P.present\(s\)/);
  assert.doesNotMatch(app,/escape\(s.note\)/);
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
  assert.equal(new Set(ids).size,ids.length);
  for(const m of app.matchAll(/\$\('([^']+)'\)/g)) assert.ok(ids.includes(m[1])||m[1]==='tab-workbench',m[1]);
  assert.ok(html.indexOf('src="model.js"')<html.indexOf('src="presenter.js"'));
  assert.ok(html.indexOf('src="presenter.js"')<html.indexOf('src="app.js"'));
  assert.match(html,/目标用户理解测试：未开展/);
});
