(() => {
  const M = window.BoundaryDesign;
  const P = window.BoundaryPresenter;
  let state = M.initial();
  const $ = id => document.getElementById(id);
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
  const icon = name => window.BOUNDARY_ICONS[name] || '';
  const btn = (action, text, name, cls = '', disabled = false) => `<button data-action="${action}" aria-describedby="action-effect" class="${cls}" ${disabled ? 'disabled' : ''}>${icon(name)}${escape(text)}</button>`;
  function send(action) { state = M.reduce(state, action); render(); }
  function render() {
    const focus = document.activeElement?.id;
    const focusedCase = document.activeElement?.dataset?.case;
    const focusedAction = document.activeElement?.dataset?.action;
    const s = state, d = P.present(s);
    const names = {send:'周报准备发送',draft:'副本整理完成',evidence:'两种完成率',forbidden:'折扣承诺未获批',changed:'附件已换成新版',expired:'上次确认已过期',unknown:'不确定是否发出',takeover:'已暂停，人工处理'};
    $('case-list').innerHTML = M.cases.map(c => `<button data-case="${c.id}" aria-current="${c.id === s.caseId}">${icon(c.icon)}<span><strong>${names[c.id]}</strong><small>${c.subtitle}</small></span></button>`).join('');
    $('case-picker').innerHTML = M.cases.map(c=>`<option value="${c.id}" ${c.id===s.caseId?'selected':''}>${names[c.id]}</option>`).join('');
    $('decision-band').className = `decision-band ${d.tone}`;
    $('decision-title').textContent = d.title;
    $('decision-text').textContent = d.reason;
    $('decision-icon').innerHTML = icon({green:'IconCircleCheck',amber:'IconAlertCircle',red:'IconLock',blue:'IconHandStop',neutral:'IconClock'}[d.tone]);
    $('boundary-kind').textContent = '当前需要处理的事';
    $('branch-label').innerHTML = `${s.kind === 'evidence' ? '周报数据核对' : '周报交付'}<small>${d.code === 'done' ? '演示已结束' : '只处理这一步'}</small>`;
    $('outcome-summary').innerHTML = `<div><dt>当前成果（演示）</dt><dd>${escape(d.currentFile)}<small>${escape(d.currentResult)}</small></dd></div><div><dt>邮件状态</dt><dd>${escape(d.sendStatus)}<small>${escape(d.realStatus)}</small></dd></div>`;
    $('scope-change').hidden = d.code !== 'confirm' || !d.changes.length;
    $('scope-change').innerHTML = `<h3>与上次确认相比</h3><table><thead><tr><th>变动项</th><th>上次确认</th><th>这次待确认</th></tr></thead><tbody>${d.changes.map(([field,before,after])=>`<tr><th>${escape(field)}</th><td>${escape(before)}</td><td>${escape(after)}</td></tr>`).join('')}</tbody></table>`;
    $('preview-title').textContent = s.kind === 'evidence' && !s.localDone ? '可供选择的周报数据' : s.localDone || s.fallback ? '当前草稿内容' : '邮件草稿';
    if (s.kind === 'evidence' && !s.localDone) {
      $('preview').innerHTML = `<fieldset class="basis-options" ${d.code !== 'clarify' ? 'disabled' : ''}><legend>本次周报采用哪组数据？</legend><label class="candidate"><input type="radio" name="basis" value="all" ${s.choice === 'all' ? 'checked' : ''}><span><strong>全部样本 · 完成率 80%（40/50）</strong><p>合成测试记录 / 表 1：测试时未提供引导，包括首次使用者。</p></span></label><label class="candidate"><input type="radio" name="basis" value="guided" ${s.choice === 'guided' ? 'checked' : ''}><span><strong>引导后样本 · 完成率 92%（46/50）</strong><p>合成测试记录 / 表 2：另一组样本完成引导后测试，不能省略“引导后”的限定。</p></span></label></fieldset><div class="annotation">两组均为虚构演示数据，不是本产品用户研究结果。选择后只更新草稿。</div>`;
    } else if (s.localDone || s.fallback) {
      $('preview').innerHTML = `<div class="result-summary">${icon('IconFileCheck')}<h3>${escape(s.file)}</h3><p>${escape(d.basisResult || (s.fallback ? '未删除草稿中的折扣承诺；承诺尚未获批，仅供内部审查，不可发送给客户。' : '产品上线核对与项目风险分析已排入周报副本，原始资料未改动。'))}</p><div class="file-line">${icon('IconFiles')}当前草稿 <small>未发送 · 未写业务系统</small></div></div><div class="annotation">${escape(d.history)}。仅展示演示内容，没有创建真实文件。</div>`;
    } else {
      $('preview').innerHTML = `<dl class="mail-meta"><div><dt>收件人</dt><dd>${escape(s.recipient)}</dd></div><div><dt>主题</dt><dd>项目本周进展与待决事项</dd></div></dl><div class="mail-body"><h4>项目周报</h4><p>您好，附件为本周项目进展与待决事项，供您查阅。</p><p>${s.permission === 'denied' ? '注意：附件包含未获批准的折扣承诺，不可对外发送。' : '附件包含产品上线核对与风险分析，不包括原始明细或其他客户资料。'}</p><div class="file-line">${icon('IconFileTypePdf')}${escape(s.file)}</div></div><div class="annotation">这是虚构邮件草稿。核对附件或收件人不代表已发送，也不保证内容正确。</div>`;
    }
    const ack = d.code === 'confirm' ? `<label class="checkbox"><input id="ack" type="checkbox" ${s.acknowledged ? 'checked' : ''}>我已核对：仅向 ${escape(s.recipient)} 发送 ${escape(s.file)}，不含其他资料。</label>` : '';
    $('actions').innerHTML = `<p id="action-effect" class="action-caption">${escape(d.next)}</p>${ack}<div class="action-row">${d.actions.map((a,i)=>btn(a.id,a.label,a.icon,i===0?'primary':'',a.disabled)).join('')}</div>`;
    $('approval-expiry').textContent = d.expiry;
    $('notice').textContent = s.notice;
    const authority = s.permission === 'denied' ? '未获授权 · 禁止外发承诺' : s.external ? '可以准备内容；外发须具体确认' : '仅允许内部草稿副本';
    const approval = s.receipt !== 'none' ? '已用于本次模拟提交，不能重复使用' : M.approved(s) ? `有效至模拟第 ${s.approval.expires} 分钟 · 单次` : s.approval ? '已失效或已收回，不能复用' : '尚未记录；没有默认批准';
    const receipt = {none:'尚未提交',unknown:'结果未知，禁止重复提交',confirmed:'模拟已核对；真实未发送'}[s.receipt];
    const facts = [['发送权限',authority,s.permission === 'denied' ? 'danger' : ''],['周报数据',s.kind === 'evidence' ? s.localDone ? `已采用${P.basis[s.choice].label}，仅更新草稿` : s.choice ? '已选，尚未写入草稿' : '两种测试条件，尚未选择' : '演示数据，不代表内容已验证',''],['影响范围',s.external ? '仅本次客户邮件；不能保证发送后可撤回' : '仅周报副本，原件保留',''],['发送确认',s.external ? approval : '本例不申请发送权限',''],['邮件状态',receipt,s.receipt === 'unknown' ? 'warning' : '']];
    $('boundary-facts').innerHTML = facts.map(([label,value,cls]) => `<div><dt>${label}</dt><dd class="${cls}">${escape(value)}</dd></div>`).join('');
    $('event-count').textContent = `${s.events.length} 条`;
    $('events').innerHTML = s.events.map(e => `<li><time>+${e.minute} 分钟</time> · ${escape(e.message)}</li>`).join('');
    $('attempts').textContent = s.attempts;
    $('preserved-copy').textContent = d.history;
    $('fail-next').checked = s.failNext;
    document.querySelectorAll('[data-change], #fail-next').forEach(el => el.disabled = !s.external || ['done','unknown','cancelled','draft'].includes(d.code));
    if (focus && $(focus)) $(focus).focus({preventScroll:true});
    else if (focusedCase) document.querySelector(`[data-case="${focusedCase}"]`)?.focus({preventScroll:true});
    else if (focusedAction) {
      const same = document.querySelector(`[data-action="${focusedAction}"]:not(:disabled)`);
      (same || $('decision-title')).focus({preventScroll:true});
    }
  }
  const testCases = [
    ['send','确认不等于已执行','勾选附件和收件人，再确认；此时发送尝试必须仍为 0。随后演示发送一次。','确认后就出现发送成功，或同一动作能发送两次。'],
    ['changed','附件变化后旧决定失效','比较上次 v2 与本次 v3，重新确认，再展开测试设置更新附件版本。','旧确认继续有效，发送按钮仍可用。'],
    ['expired','过期不自动续期','重新确认，再模拟经过 6 分钟。','等待被当作默许，或过期动作仍可提交。'],
    ['unknown','查询失败也不能重复发送','展开测试设置，将核查结果分别设为查询失败、没有查到记录、查到已发送，逐次核查。','前两种结果出现发送成功；核查让尝试数从 1 增加到 2；或把未知写成未发送。'],
    ['forbidden','权限禁令不被确认绕过','检查没有外发确认入口，仅保留内部草稿。','草稿降级后出现真实外发权限。'],
    ['evidence','内容澄清不授予动作权限','不选时采用按钮禁用；选择一个口径并采用。','默认预选、混用两种统计范围，或因此批准外发。'],
    ['takeover','继续处理不等于授权发送','选择“让 Agent 继续处理”，观察邮件仍未发送，确认仍需勾选。','暂停删除其他成果，或继续处理后自动发送。'],
    ['draft','授权内推进不制造审批','打开情境，查看草稿已形成、原件保留、真实动作 0。','无意义地要求逐步批准，或把模拟成果当真实写入。']
  ];
  function showTab(name) {
    for (const tab of document.querySelectorAll('[role=tab]')) { const active = tab.dataset.tab === name; tab.setAttribute('aria-selected',String(active)); tab.tabIndex = active ? 0 : -1; $(tab.dataset.tab).hidden = !active; }
  }
  document.addEventListener('click', e => {
    const target = e.target.closest('button'); if (!target || target.disabled) return;
    if (target.dataset.tab) showTab(target.dataset.tab);
    if (target.dataset.case) { state = M.initial(target.dataset.case); $('query-result').value = 'confirmed'; render(); }
    if (target.dataset.action) send({type:target.dataset.action,result:target.dataset.action === 'reconcile' ? $('query-result').value : undefined});
    if (target.dataset.change) send({type:'mutate',field:target.dataset.change});
    if (target.dataset.try) { state = M.initial(target.dataset.try); $('query-result').value = 'confirmed'; showTab('workbench'); render(); $('tab-workbench').focus(); window.scrollTo({top:0,behavior:'instant'}); }
    if (target.id === 'reset') { $('query-result').value = 'confirmed'; send({type:'reset'}); }
    if (target.id === 'expire') send({type:'expire'});
  });
  document.addEventListener('change', e => {
    if (e.target.id === 'case-picker') { state = M.initial(e.target.value); $('query-result').value = 'confirmed'; render(); }
    if (e.target.id === 'ack') send({type:'ack',value:e.target.checked});
    if (e.target.name === 'basis') { const value = e.target.value; send({type:'select',value}); document.querySelector(`input[name="basis"][value="${value}"]`)?.focus({preventScroll:true}); }
    if (e.target.id === 'fail-next') send({type:'failNext',value:e.target.checked});
  });
  document.querySelector('.tabs').addEventListener('keydown', e => {
    const tabs = [...document.querySelectorAll('[role=tab]')], at = tabs.indexOf(e.target);
    if (at < 0 || !['ArrowRight','ArrowLeft','Home','End'].includes(e.key)) return;
    e.preventDefault(); const next = e.key === 'Home' ? 0 : e.key === 'End' ? tabs.length-1 : (at+(e.key === 'ArrowRight' ? 1 : -1)+tabs.length)%tabs.length;
    showTab(tabs[next].dataset.tab); tabs[next].focus();
  });
  $('test-list').innerHTML = testCases.map(([id,title,steps,fail],i) => `<article class="test-row"><span class="test-number">${String(i+1).padStart(2,'0')}</span><div><h3>${title}</h3><p>${steps}</p><p class="fail">失败判据：${fail}</p></div><button data-try="${id}">打开用例${icon('IconArrowUpRight')}</button></article>`).join('');
  const questions = [
    ['send','确认之后','完成第一次确认后，现在发生了哪些事？接下来你会做什么？','应区分确认与发送；演示尝试仍为 0，真实邮件未发出。'],
    ['unknown','看不到发送结果','你认为任务进行到了哪一步？你会怎样处理，为什么？','不能认定未发出或失败；先核查同一次发送，查询失败也不能重发。'],
    ['evidence','选择周报数据','采用其中一组数据后，哪些内容变了？哪些事情还没有完成？','说出具体百分比及测试条件；当前 v3、保留 v2；未批准发送。'],
    ['forbidden','保留内部草稿','留下这份草稿后，你会怎样使用它？还需要谁做什么？','未经批准的承诺仍在；仅内部审查，不认为已删掉问题或获得发送权限。'],
    ['takeover','暂停之后','想让任务继续，你会怎么做？你预计系统接下来会怎样？','继续处理不是发送授权；没有人工处理完成或其他分析被删除的事实。']
  ];
  $('comprehension-list').innerHTML = questions.map(([id,title,question,rubric],i)=>`<article class="comprehension-row"><span class="test-number">U${i+1}</span><div><h3>${title}</h3><p>${question}</p><details><summary>主持人判定点 · 提问前不展示</summary><p>${rubric}</p></details></div><button data-try="${id}">打开情境${icon('IconArrowUpRight')}</button></article>`).join('');
  const sources = window.BOUNDARY_RESEARCH?.sources || [];
  $('source-list').innerHTML = sources.map(s => `<article class="source-row"><div class="source-id">${escape(s.id)}<br>${escape(s.date || s.published_at || '滚动文档')}<br>${escape(s.type)}</div><div><h4>${escape(s.title)}</h4><p>${escape(s.observation)}</p><a href="${escape(s.url)}" target="_blank" rel="noopener noreferrer">原始来源${icon('IconArrowUpRight')}</a></div><div><p><strong>设计启发：</strong>${escape(s.implication)}</p><small>边界：${escape(s.limitation)}</small></div></article>`).join('');
  function renderFollowup() {
    const items=window.BoundaryResearchView.select(window.BOUNDARY_FOLLOWUP.sources,$('followup-filter').value,$('followup-search').value);
    $('followup-count').textContent=`${items.length} 项资料`;
    $('followup-empty').hidden=items.length>0;
    $('followup-source-list').innerHTML=items.map(s=>`<article class="followup-source"><div class="reading-meta"><span>${escape(s.id)}</span><span>${s.priority===1?'优先精读':s.priority===2?'专题补充':'拓展阅读'}</span><span>${s.type.startsWith('official_')?'官方实践':'论文'}</span><span>${escape(s.date)}</span></div><h3><a href="${escape(s.url)}" target="_blank" rel="noopener noreferrer">${escape(s.title)}${icon('IconArrowUpRight')}</a></h3><p>${escape(s.why_read || s.priority_reason || s.design_inference)}</p><details><summary>来源发现、设计推论与待测反例</summary><dl><div><dt>作者与版本</dt><dd>${escape(s.authors.join(', '))}${s.date_note?`<br>${escape(s.date_note)}`:''}</dd></div><div><dt>方法与样本</dt><dd>${escape(s.method)}</dd></div><div><dt>原文支持</dt><dd>${escape(s.source_claim)}</dd></div><div><dt>项目推论 · 待验证</dt><dd>${escape(s.design_inference)}</dd></div><div><dt>建议测试</dt><dd>${escape(s.testable_counterexample)}</dd></div><div><dt>不能外推</dt><dd>${escape(s.limitations.join(' '))}</dd></div><div><dt>实际阅读范围</dt><dd>${escape(s.read_scope)}</dd></div></dl></details></article>`).join('');
  }
  $('followup-filter').addEventListener('change',renderFollowup);
  $('followup-search').addEventListener('input',renderFollowup);
  renderFollowup();
  document.querySelectorAll('[data-icon]').forEach(el => el.innerHTML = icon(el.dataset.icon));
  render();
})();
