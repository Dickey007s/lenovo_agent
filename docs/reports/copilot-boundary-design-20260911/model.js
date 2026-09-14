/* Offline design model only. This is not the product's authorization engine. */
(function (root) {
  const cases = [
    { id: 'send', name: '对外发送', subtitle: '确认一个具体动作', category: '动作边界', icon: 'IconSend', note: '周报已经形成。外发前，需要你核对对象与内容。', kind: 'send', recipient: 'client@example.com', file: '项目周报 v2.pdf', permission: 'allowed', evidence: 'ready', external: true },
    { id: 'draft', name: '授权内整理', subtitle: '不为每个步骤打断', category: '自主推进', icon: 'IconFileText', note: '已在授权范围内完成副本排版，原件保持不变。', kind: 'draft', recipient: '本地草稿区', file: '项目周报 v2.pdf', permission: 'allowed', evidence: 'ready', external: false },
    { id: 'evidence', name: '依据有歧义', subtitle: '澄清，不是授权', category: '知识边界', icon: 'IconFileSearch', note: '任务完成率存在两种统计范围，需要确定本次汇报的口径。', kind: 'evidence', recipient: '本地草稿区', file: '项目周报 v2.pdf', permission: 'allowed', evidence: 'ambiguous', external: false },
    { id: 'forbidden', name: '承诺超出权限', subtitle: '确认不能覆盖禁令', category: '权限边界', icon: 'IconLock', note: '新增折扣承诺超出当前任务授权。不得通过普通确认放行。', kind: 'send', recipient: 'client@example.com', file: '含折扣承诺的周报.pdf', permission: 'denied', evidence: 'ready', external: true },
    { id: 'changed', name: '确认后内容变化', subtitle: '旧决定必须失效', category: '范围边界', icon: 'IconGitCompare', note: '曾确认 v2 周报。现在附件内容改变，原确认不再适用。', kind: 'send', recipient: 'client@example.com', file: '项目周报 v3.pdf', permission: 'allowed', evidence: 'ready', external: true },
    { id: 'expired', name: '确认已过期', subtitle: '沉默不等于续期', category: '时间边界', icon: 'IconClock', note: '本次确认的模拟有效期已结束。未提交，也不会自动续期。', kind: 'send', recipient: 'client@example.com', file: '项目周报 v2.pdf', permission: 'allowed', evidence: 'ready', external: true },
    { id: 'unknown', name: '提交回执丢失', subtitle: '先查状态，不盲重试', category: '执行边界', icon: 'IconReceipt', note: '模拟提交后没有收到可靠回执。不能推断成功，也不能推断未执行。', kind: 'send', recipient: 'client@example.com', file: '项目周报 v2.pdf', permission: 'allowed', evidence: 'ready', external: true },
    { id: 'takeover', name: '人主动接管', subtitle: '保留成果，收回控制', category: '控制边界', icon: 'IconHandStop', note: '用户暂停了交付分支。内容与分析成果保留，机器不自行恢复。', kind: 'send', recipient: 'client@example.com', file: '项目周报 v2.pdf', permission: 'allowed', evidence: 'ready', external: true }
  ];
  const copy = value => JSON.parse(JSON.stringify(value));
  function fingerprint(s) {
    return JSON.stringify([s.caseId, s.kind, s.recipient, s.file, s.revision, s.policyRevision, s.external]);
  }
  function approved(s) {
    return Boolean(s.approval && s.receipt === 'none' && s.approval.scope === fingerprint(s) && s.clock < s.approval.expires && !s.approval.revoked);
  }
  function event(s, message) {
    s.events.push({ sequence: s.events.length + 1, minute: s.clock, message });
  }
  function grant(s) {
    s.approval = { scope: fingerprint(s), revision: s.revision, expires: s.clock + 5, revoked: false,
      reviewed: { recipient: s.recipient, file: s.file, policyRevision: s.policyRevision } };
  }
  function initial(id = 'send') {
    const c = cases.find(item => item.id === id) || cases[0];
    const s = { ...copy(c), caseId: c.id, revision: 2, policyRevision: 1, clock: 0, approval: null, acknowledged: false, choice: '', receipt: 'none', attempts: 0, paused: false, deferred: false, cancelled: false, fallback: false, localDone: false, failNext: false, notice: '', events: [] };
    event(s, '载入独立演示情境；原件、真实任务与外部系统均未改变');
    if (id === 'draft') { s.localDone = true; event(s, '模拟：已授权的草稿副本整理完成，无逐步审批'); }
    if (id === 'changed') s.file = '项目周报 v2.pdf';
    if (['changed', 'expired', 'unknown'].includes(id)) { grant(s); event(s, '模拟：记录仅适用于 v2 与当前收件人的单次确认'); }
    if (id === 'changed') { s.revision = 3; s.file = '项目周报 v3.pdf'; event(s, '附件版本改变，旧确认失效'); }
    if (id === 'expired') { s.clock = 6; event(s, '模拟时间前进 6 分钟，超过 5 分钟示例有效期'); }
    if (id === 'unknown') { s.receipt = 'unknown'; s.attempts = 1; event(s, '模拟：已提交一次，但回执丢失，冻结重复提交'); }
    if (id === 'takeover') { s.paused = true; event(s, '用户主动收回交付分支控制权'); }
    return s;
  }
  function decision(s) {
    if (s.receipt === 'unknown') return { code: 'unknown', tone: 'amber', title: '提交结果未知', text: '先查询同一次动作的回执。暂停或取消都不能抹去可能已发生的影响。' };
    if (s.receipt === 'confirmed') return { code: 'done', tone: 'green', title: '模拟回执已核对', text: '同一动作只记录一次模拟提交。真实邮件未发送。' };
    if (s.cancelled) return { code: 'cancelled', tone: 'neutral', title: '本次动作已取消', text: '周报草稿与其他分支成果保留，不再提交本次动作。' };
    if (s.paused) return { code: 'paused', tone: 'blue', title: '交付分支由你接管', text: '机器暂停此分支。交还控制也不等于批准外发。' };
    if (s.deferred) return { code: 'deferred', tone: 'neutral', title: '此项已延后', text: '没有记录批准，不会因等待时间变长而自动放行。' };
    if (s.fallback) return { code: 'draft', tone: 'green', title: '已保留内部草稿', text: '外发被阻止。内部草稿也不是正式承诺或业务审批。' };
    if (s.permission !== 'allowed') return { code: 'denied', tone: 'red', title: '当前授权不允许此动作', text: '超出授权的承诺不能靠用户确认覆盖。可以保留草稿，交由有权人员处理。' };
    if (s.evidence !== 'ready') return { code: 'clarify', tone: 'amber', title: '先确定统计口径', text: '这是内容判断，不是外发授权。两种口径都保留来源说明。' };
    if (s.localDone) return { code: 'draft', tone: 'green', title: '已在授权范围内完成', text: '只整理草稿副本，保留原件。没有逐步确认，也没有外发。' };
    if (s.external && !approved(s)) return { code: 'confirm', tone: 'amber', title: s.approval ? '需要重新确认当前范围' : '外发前需要你确认', text: s.approval ? '附件、对象、策略或有效期不再匹配。旧决定不能复用。' : '本次只允许向一个收件人提交这一版附件，不扩展到未来动作。' };
    return { code: 'ready', tone: 'blue', title: '已确认，尚未提交', text: '确认与执行是两件事。提交前还要再次检查对象、版本与有效期。' };
  }
  function reduce(input, action) {
    const s = copy(input);
    const d = decision(s);
    s.notice = '';
    const refuse = message => { s.notice = message; return s; };
    if (action.type === 'reset') return initial(s.caseId);
    if (action.type === 'ack') { s.acknowledged = Boolean(action.value); return s; }
    if (action.type === 'select') {
      if (d.code !== 'clarify') return refuse('当前不在选择口径阶段，已生成草稿的口径保持不变。');
      s.choice = ['all', 'guided'].includes(action.value) ? action.value : ''; return s;
    }
    if (action.type === 'failNext') { s.failNext = Boolean(action.value); return s; }
    if (action.type === 'approve') {
      if (d.code !== 'confirm' || !s.acknowledged) return refuse('尚未明确核对当前范围，不能记录确认。');
      grant(s); s.acknowledged = false; event(s, '模拟：确认当前对象与版本，仅一次，5 分钟内有效；尚未提交');
    } else if (action.type === 'execute') {
      if (d.code !== 'ready' || !approved(s)) return refuse('当前条件不允许提交；没有新增执行尝试。');
      s.attempts += 1; s.receipt = s.failNext ? 'unknown' : 'confirmed';
      event(s, s.failNext ? '模拟：一次提交后回执丢失；重复提交已锁定' : '模拟：一次提交并收到确认回执；真实外部动作仍为 0');
    } else if (action.type === 'reconcile') {
      if (d.code !== 'unknown') return refuse('当前没有待查的未知回执。');
      if ((action.result ?? 'confirmed') !== 'confirmed') {
        const message = action.result === 'not_found'
          ? '没有查到发送记录，但这不能证明未发送。仍不确定是否成功，请勿重复发送。'
          : '这次查询未能取得可靠结果。仍不确定是否发送成功，请勿重复发送。';
        event(s, `模拟：${message}`); return refuse(message);
      }
      s.receipt = 'confirmed'; event(s, '模拟：查询同一动作确认已有回执，没有再次提交');
    } else if (action.type === 'resolve') {
      if (d.code !== 'clarify' || !s.choice) return refuse('请先选择本次采用的统计口径。');
      s.evidence = 'ready'; s.revision += 1; s.localDone = true; s.file = '项目周报 v3.pdf';
      event(s, `模拟：采用${s.choice === 'all' ? '全部样本' : '引导后样本'}口径，只更新当前内容分支；没有外发授权`);
    } else if (action.type === 'mutate') {
      if (['unknown', 'done', 'cancelled'].includes(d.code)) return refuse('先处理当前动作状态；已提交动作不能被改写。');
      if (!['recipient', 'file', 'policy'].includes(action.field)) return refuse('不支持的范围变化；本次确认保持不变。');
      if (action.field === 'recipient') s.recipient = s.recipient === 'client@example.com' ? 'new-recipient@example.com' : 'client@example.com';
      if (action.field === 'file') { s.revision += 1; s.file = `项目周报 v${s.revision}.pdf`; }
      if (action.field === 'policy') s.policyRevision += 1;
      if (s.approval) s.approval.revoked = true;
      s.acknowledged = false; event(s, '模拟：动作范围或策略改变，需要重新核对；不会自动扩大授权');
    } else if (action.type === 'expire') {
      s.clock += 6; s.acknowledged = false; event(s, '模拟时间前进 6 分钟；过期决定不再有效');
    } else if (action.type === 'pause') {
      if (['done', 'cancelled'].includes(d.code)) return refuse('动作已经结束，不会伪造暂停或撤回。');
      s.paused = true; s.acknowledged = false; if (s.approval) s.approval.revoked = true;
      event(s, '模拟：收回交付分支控制权；撤销未使用确认，保留 A/B 成果');
    } else if (action.type === 'return') {
      if (!s.paused) return refuse('当前不在人接管状态。');
      s.paused = false; event(s, '模拟：交还此分支控制，不代表批准外发');
    } else if (action.type === 'defer') {
      if (['unknown', 'done', 'cancelled'].includes(d.code)) return refuse('未知回执必须先核对，已结束动作不能再延后。');
      s.deferred = true; s.acknowledged = false; if (s.approval) s.approval.revoked = true; event(s, '模拟：延后此项，没有批准');
    } else if (action.type === 'reopen') {
      s.deferred = false; event(s, '重新打开待处理项；未自动批准');
    } else if (action.type === 'cancel') {
      if (['unknown', 'done'].includes(d.code)) return refuse('不能把可能已执行或已确认的动作伪装成取消成功。');
      s.cancelled = true; s.acknowledged = false; if (s.approval) s.approval.revoked = true;
      event(s, '模拟：取消未提交动作，撤销未用确认并保留所有草稿');
    } else if (action.type === 'fallback') {
      if (d.code !== 'denied') return refuse('此降级只适用于当前受阻动作。');
      s.fallback = true; event(s, '模拟：只保留内部草稿，仍未取得业务承诺授权');
    }
    return s;
  }
  const api = { cases, initial, reduce, decision, approved, fingerprint };
  if (typeof module !== 'undefined') module.exports = api;
  else root.BoundaryDesign = api;
})(typeof window !== 'undefined' ? window : this);
