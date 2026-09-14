/* Business-language projection of synthetic state, not a second policy engine. */
(function (root) {
  const M = typeof module !== 'undefined' ? require('./model.js') : root.BoundaryDesign;
  const basis = {
    all: { label: '全部样本', result: '全部样本的任务完成率为 80%（40/50）；测试时未提供引导。' },
    guided: { label: '引导后样本', result: '完成引导后的任务完成率为 92%（46/50）；不代表未经引导的表现。' }
  };
  function present(s) {
    const d = M.decision(s);
    const confirmation = s.approval;
    const reviewed = confirmation?.reviewed;
    const changes = [];
    if (reviewed && reviewed.file !== s.file) changes.push(['附件', reviewed.file, s.file]);
    if (reviewed && reviewed.recipient !== s.recipient) changes.push(['收件人', reviewed.recipient, s.recipient]);
    if (reviewed && reviewed.policyRevision !== s.policyRevision) changes.push(['授权规则', `版本 ${reviewed.policyRevision}`, `版本 ${s.policyRevision}`]);
    const action = (id, label, icon, disabled = false) => ({ id, label, icon, disabled });
    const cancel = action('cancel','取消这次发送','IconX');
    const defer = action('defer','稍后决定','IconClock');
    let title, reason, next, actions = [];
    switch (d.code) {
      case 'confirm':
        title = '发送前，请核对附件和收件人';
        reason = '这份周报准备发给客户，需要你确认本次收件人和附件。';
        if (confirmation) {
          title = '这次发送需要重新确认';
          reason = changes.length ? `${changes.map(c=>c[0]).join('、')}已改变，上次确认不适用于这次发送。`
            : confirmation.revoked ? '上次确认已撤销。即使对象改回原值，或让 Agent 继续，也需要重新确认。'
            : s.clock >= confirmation.expires ? '上次确认已过期，期间没有发送。需要你重新核对。'
            : '本次动作与上次确认不一致，需要重新核对。';
        }
        next = s.acknowledged ? '确认后仍未发送；下一步才可演示发送。' : '先勾选下方收件人和附件，才能确认。确认本身不会发送邮件。';
        actions = [action('approve','确认附件和收件人（演示）','IconCheck',!s.acknowledged), defer, action('pause','暂停，交给我处理','IconHandStop')];
        break;
      case 'ready':
        title = '已确认，但还没有发送';
        reason = `本次确认只适用于 ${s.recipient} 和 ${s.file}，只能使用一次。`;
        next = '下一步演示一次发送；不会发送真实邮件。更换附件或收件人后，需重新确认。';
        actions = [action('execute','演示发送一次','IconSend'),action('pause','暂停，交给我处理','IconHandStop'),cancel];
        break;
      case 'unknown':
        title = '不确定是否发送成功';
        reason = '演示中已尝试发送一次，但没有可靠结果。邮件可能已经发出，再发一次可能重复。';
        next = '只核查刚才那一次发送，不重新发送。查不到记录或查询失败，都不能当作未发送。';
        actions = [action('reconcile','核查刚才的发送结果','IconReceipt'),action('execute','不能重复发送','IconLock',true)];
        break;
      case 'done':
        title = '演示发送成功'; reason = '演示记录确认已发送一次，没有重复发送。真实邮件没有发出。';
        next = '本次演示已结束，草稿和其他成果仍保留。'; break;
      case 'clarify':
        title = '这份周报要报告哪种完成率？';
        reason = '80% 和 92% 来自不同测试条件，不能互相替代。请决定这次周报采用哪种条件。';
        next = s.choice ? `将“${basis[s.choice].label}”的数字和条件写入 v3 草稿；保留 v2，不发送邮件。` : '先选择一项。采用后只更新周报草稿，不发送邮件。';
        actions = [action('resolve','用所选数据更新草稿（演示）','IconCheck',!s.choice),defer]; break;
      case 'denied':
        title = '这份周报不能发送：折扣承诺未获授权';
        reason = '草稿含未获授权的折扣承诺。确认收件人也不能代替折扣审批。';
        next = '可以留下内部草稿，交由有权人员审查；本页不会提交审批或取得发送权限。';
        actions = [action('fallback','仅保留内部草稿','IconFileText'),cancel]; break;
      case 'paused':
        title = '已暂停，等你决定是否继续';
        reason = 'Agent 不再继续处理这一步；已有草稿、产品核对和风险分析保留。';
        next = s.external ? '让 Agent 继续后，仍需重新确认附件和收件人，不会自动发送。' : '让 Agent 继续后，仍需选择本次统计条件，不会自动采用数据。';
        actions = [action('return','让 Agent 继续处理','IconArrowBackUp'),action('cancel',s.external?'取消这次发送':'取消本次处理','IconX')]; break;
      case 'deferred':
        title = '已留待稍后决定'; reason = '你还没有批准这一步。等待不会自动变成同意，已有成果仍保留。';
        next = s.kind === 'evidence' ? '重新打开后仍需选择并采用数据；不会因稍后处理而更新草稿。' : '重新打开后仍需确认；不会自动发送。';
        actions = [action('reopen','返回待处理项','IconArrowBackUp'),action('cancel',s.external?'取消这次发送':'取消本次处理','IconX')]; break;
      case 'cancelled':
        title = s.external ? '这次发送已取消' : '本次数据处理已取消';
        reason = s.external ? '取消发生在发送前，演示中没有发出邮件；不是撤回已发送邮件。' : '没有采用新数据，现有草稿保持不变。';
        next = '草稿、产品核对和风险分析保留，不删除原始资料。'; break;
      case 'draft':
        title = s.fallback ? '内部草稿已保留，仍不能发送' : s.kind === 'evidence' ? '数据已写入 v3 草稿，尚未发送' : '周报副本已整理，尚未发送';
        reason = s.fallback ? '折扣承诺仍未获授权；留下草稿不等于批准承诺。' : s.kind === 'evidence' ? basis[s.choice]?.result : '已完成演示中的副本排版，原件没有改动。';
        next = '当前步骤结束。未授予发送权限，也没有写入业务系统。'; break;
    }
    return {
      code: d.code, tone: d.tone, title, reason, next, actions, changes,
      currentFile: s.file,
      currentResult: s.evidence !== 'ready' ? '周报草稿 · 数据待确定' : s.fallback ? '内部草稿 · 承诺待审查' : '周报草稿已保留',
      sendStatus: {none:'尚未发送',unknown:'是否成功尚不确定',confirmed:'演示已发送一次'}[s.receipt],
      realStatus: '真实邮件：未发送',
      basisResult: s.kind === 'evidence' && s.localDone ? basis[s.choice]?.result : '',
      expiry: confirmation && M.approved(s) ? `本次确认剩余 ${Math.max(0,confirmation.expires-s.clock)} 分钟（演示时间）` : '',
      history: s.kind === 'evidence' && s.localDone ? '当前 v3 草稿；历史 v2 草稿仍保留' : '产品核对、风险分析和已有草稿保留'
    };
  }
  const api = { present, basis };
  if (typeof module !== 'undefined') module.exports = api;
  else root.BoundaryPresenter = api;
})(typeof window !== 'undefined' ? window : this);
