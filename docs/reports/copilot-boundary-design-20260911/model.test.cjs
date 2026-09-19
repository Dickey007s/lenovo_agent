const test = require('node:test');
const assert = require('node:assert/strict');
const M = require('./model.js');
const apply = (s,...actions) => actions.reduce(M.reduce,s);
const consent = s => apply(s,{type:'ack',value:true},{type:'approve'});

test('all eight cases have the intended initial boundary',() => {
  const expected = {send:'confirm',draft:'draft',evidence:'clarify',forbidden:'denied',changed:'confirm',expired:'confirm',unknown:'unknown',takeover:'paused'};
  assert.equal(M.cases.length,8);
  for (const c of M.cases) assert.equal(M.decision(M.initial(c.id)).code,expected[c.id]);
});
test('no preselection and no implicit approval',() => {
  const s = M.initial('send'); assert.equal(s.acknowledged,false); assert.equal(s.approval,null);
  const denied = M.reduce(s,{type:'approve'}); assert.equal(denied.approval,null); assert.equal(denied.attempts,0);
  const evidence = M.initial('evidence'); assert.equal(evidence.choice,''); assert.equal(M.reduce(evidence,{type:'resolve'}).evidence,'ambiguous');
});
test('acknowledgment, approval, execution, receipt are separate states',() => {
  const s = consent(M.initial()); assert.equal(M.decision(s).code,'ready'); assert.equal(s.attempts,0); assert.equal(s.receipt,'none');
  const done = M.reduce(s,{type:'execute'}); assert.equal(done.attempts,1); assert.equal(done.receipt,'confirmed');
  assert.equal(M.reduce(done,{type:'execute'}).attempts,1);
  assert.equal(M.approved(done),false);
});
for (const field of ['file','recipient','policy']) test(`${field} change invalidates prior decision and clears acknowledgment`,() => {
  const s = M.reduce(consent(M.initial()),{type:'mutate',field});
  assert.equal(M.approved(s),false); assert.equal(s.acknowledged,false); assert.equal(M.decision(s).code,'confirm');
  assert.equal(M.reduce(s,{type:'execute'}).attempts,0);
});
test('expiry checked at submit; waiting never silently extends grant',() => {
  let s = consent(M.initial()); s.clock = s.approval.expires;
  assert.equal(M.approved(s),false); assert.equal(M.reduce(s,{type:'execute'}).attempts,0);
  s = M.reduce(s,{type:'expire'}); assert.equal(s.approval.expires,5);
});
test('changing recipient away and back cannot revive a superseded approval',() => {
  const s = apply(consent(M.initial()),{type:'mutate',field:'recipient'},{type:'mutate',field:'recipient'});
  assert.equal(s.recipient,'client@example.com');
  assert.equal(M.approved(s),false);
  assert.equal(M.reduce(s,{type:'execute'}).attempts,0);
});
test('context binding includes action kind and external scope',() => {
  const s = consent(M.initial());
  assert.equal(M.approved({...s,kind:'delete'}),false);
  assert.equal(M.approved({...s,external:false}),false);
  assert.equal(M.approved({...s,caseId:'another-action'}),false);
});
test('permission denial cannot be bypassed by an approval field',() => {
  const s = consent(M.initial()); s.permission = 'denied';
  assert.equal(M.decision(s).code,'denied'); assert.equal(M.reduce(s,{type:'execute'}).attempts,0);
  const forbidden = apply(M.initial('forbidden'),{type:'ack',value:true},{type:'approve'},{type:'execute'});
  assert.equal(forbidden.approval,null); assert.equal(forbidden.attempts,0);
});
test('unknown or missing permission fails closed',() => {
  const s = consent(M.initial()); delete s.permission;
  assert.equal(M.decision(s).code,'denied'); assert.equal(M.reduce(s,{type:'execute'}).attempts,0);
});
test('draft downgrade preserves denied permission, not blanket authorization',() => {
  const s = M.reduce(M.initial('forbidden'),{type:'fallback'});
  assert.equal(s.permission,'denied'); assert.equal(s.external,true); assert.equal(s.approval,null);
  assert.equal(M.reduce(s,{type:'execute'}).attempts,0);
});
for (const choice of ['all','guided']) test(`${choice} clarification updates only draft, no action approval`,() => {
  const s = apply(M.initial('evidence'),{type:'select',value:choice},{type:'resolve'});
  assert.equal(s.evidence,'ready'); assert.equal(s.revision,3); assert.equal(s.choice,choice);
  assert.equal(s.approval,null); assert.equal(s.attempts,0); assert.equal(s.external,false);
});
test('invalid evidence choice is not accepted',() => {
  const s = apply(M.initial('evidence'),{type:'select',value:'invented'},{type:'resolve'});
  assert.equal(s.choice,''); assert.equal(s.evidence,'ambiguous');
});

test('resolved basis cannot silently change after a draft was produced',() => {
  const resolved = apply(M.initial('evidence'),{type:'select',value:'all'},{type:'resolve'});
  const next = M.reduce(resolved,{type:'select',value:'guided'});
  assert.equal(next.choice,'all');
  assert.equal(next.revision,resolved.revision);
});

test('an unsuccessful status lookup never means not sent and never resubmits',() => {
  for (const result of ['unavailable','not_found','unexpected']) {
    const s = M.reduce(M.initial('unknown'),{type:'reconcile',result});
    assert.equal(s.receipt,'unknown');
    assert.equal(s.attempts,1);
    assert.equal(M.reduce(s,{type:'execute'}).attempts,1);
    assert.ok(s.notice.length>0);
  }
});

test('unsupported scope edit must not invalidate a valid confirmation',() => {
  const s = consent(M.initial());
  const next = M.reduce(s,{type:'mutate',field:'unrecognized'});
  assert.equal(M.approved(next),true);
  assert.deepEqual(next.events,s.events);
});
test('lost receipt freezes retries, cancel and range edits; reconciliation never resubmits',() => {
  const s = apply(consent(M.initial()),{type:'failNext',value:true},{type:'execute'});
  assert.equal(s.receipt,'unknown'); assert.equal(s.attempts,1);
  for (const action of [{type:'execute'},{type:'cancel'},{type:'defer'},{type:'mutate',field:'file'}]) {
    const next = M.reduce(s,action); assert.equal(next.receipt,'unknown'); assert.equal(next.attempts,1); assert.equal(next.revision,s.revision);
  }
  const checked = M.reduce(s,{type:'reconcile'}); assert.equal(checked.receipt,'confirmed'); assert.equal(checked.attempts,1);
});
test('takeover revokes unused consent; return is not approval',() => {
  const s = apply(consent(M.initial()),{type:'pause'},{type:'return'});
  assert.equal(M.approved(s),false); assert.equal(M.decision(s).code,'confirm'); assert.equal(s.attempts,0);
});
test('takeover cannot conceal an uncertain external effect',() => {
  const s = M.reduce(M.initial('unknown'),{type:'pause'});
  assert.equal(M.decision(s).code,'unknown'); assert.equal(s.attempts,1);
});
test('defer is not approval; reopening leaves waiting decision',() => {
  const s = apply(consent(M.initial()),{type:'defer'},{type:'reopen'});
  assert.equal(M.decision(s).code,'confirm'); assert.equal(M.approved(s),false);
});
test('cancellation before execution is terminal and has no submission',() => {
  const s = apply(consent(M.initial()),{type:'cancel'},{type:'execute'});
  assert.equal(s.cancelled,true); assert.equal(s.receipt,'none'); assert.equal(s.attempts,0);
  assert.equal(M.approved(s),false);
});
test('reducer is immutable, journal ordering and scenario reset are deterministic',() => {
  const s = M.initial(), original = JSON.stringify(s); consent(s); assert.equal(JSON.stringify(s),original);
  const changed = apply(consent(s),{type:'mutate',field:'file'},{type:'expire'});
  assert.deepEqual(changed.events.map(e=>e.sequence),changed.events.map((_,i)=>i+1));
  assert.deepEqual(M.reduce(changed,{type:'reset'}),s);
});
test('bounded adversarial transitions never allow duplicate simulated execution',() => {
  const actions = [{type:'ack',value:true},{type:'approve'},{type:'execute'},{type:'pause'},{type:'return'},{type:'defer'},{type:'reopen'},{type:'cancel'},{type:'fallback'},{type:'expire'},{type:'mutate',field:'recipient'},{type:'reconcile'}];
  for (const c of M.cases) for (const first of actions) for (const second of actions) for (const third of actions) {
    const s = apply(M.initial(c.id),first,second,third); assert.ok(s.attempts<=1); if(c.id==='forbidden') assert.equal(s.attempts,0);
  }
});
