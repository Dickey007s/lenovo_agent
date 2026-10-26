# DR-0087 任务内分支与首轮说明验证

日期：2026-10-24；实现为未提交工作树，HEAD 基线 fa974ae。无新 PR。
状态：Limited Verified。本地单进程、memory API；未做 PostgreSQL 新合同重启验证或目标用户研究。
关联：DR-0087 / SCENARIO-074 / USER-FEEDBACK-20261024-TASK-BRANCHES。

## 自动验证

- 后端定向组合127项通过：同任务 follow-up 参数、原子指针、父记录不变、双版本、Owner、重复回执、活动 Run 拒绝、原目标上下文，以及已有 Demo1/2/Worker 合同。
- Playwright 定向29项通过：包含1586/390任务内切换与丢回执重试、开始前说明、旧补证文案与继续协议、已有协作/依据和真实固定规则 Demo3 API。Demo1/2 浏览器测试使用受控回执，不能作为真实模型成功率。
- TypeScript `tsc --noEmit` 通过；`git diff --check` 通过（已有文件 CRLF 提示不是错误）。
- 没有跑完整所有历史浏览器套件；不声称全库回归。

```powershell
.venv/Scripts/python.exe -m pytest tests/acceptance/test_task_followups.py tests/acceptance/test_automatic_readonly.py tests/acceptance/test_demo12_output_and_dependencies.py tests/acceptance/test_demo12_reviewed_collaboration.py tests/acceptance/test_demo1_demo2_fixed_scenarios.py tests/unit/test_harness_runtime.py tests/unit/test_workunit_ledger.py tests/acceptance/test_demo12_worker_reliability.py tests/unit/test_reporting_governance.py -q
```

```powershell
pnpm exec playwright test e2e/harness-workbench.spec.ts e2e/office-actions.spec.ts --config playwright.integration.config.ts --grep 'unified reference|real API:|keeps 2 evidence choices|Agent capabilities route distinguishes|Task Ledger success|ambiguous Worker without a decision|Agent capabilities route exposes a real review|keeps table-location|continues a scoped|requests a same-task' --reporter list
```

浏览器命令目录为 apps/web；未设置覆盖历史报告截图的环境变量。新任务截图位于 outputs/task-journey-20261024。
首次新增浏览器测试的 fixture 未带 Task 身份、glob 未匹配嵌套 continue 路径，已修正；旧恢复文案断言已随合同更新。

## 真实模型运行

使用原配置 Provider/deepseek-v4-pro，通过网页真实提交；地址3010/API8010，未调用 Demo 私有入口。
以下 completed 只表示服务端只读 Loop 合同完成，不代表任务每个业务要求都满足。

| 记录 | run_id | 调用数 | 观察 |
| --- | --- | --- | --- |
| 首次 Word | harness:46767bf329a34aa58b641a567d4e2d26 | 2 | 形成招聘来源分析 |
| 首次 Excel | harness:be35e7f4e9124358a734b9a48929b8d5 | 2 | 账目分析 |
| 首次入职 | harness:bdd53f9d37554d60af46b300bed63e08 | 2 | 自然语言只读未被策略识别，产生不符合样例期望的 CSV；不作为成功 |
| 首次后续 | harness:9de81c92dab94a4aacf50050f413a283 | 3 | 同 Task 成立，但无原目标背景，漂移到法务/销售/体验检查表；不作为语义成功 |
| 复测 Word | harness:a632e551ac1843fb88d097580e2ff3c1 | 2 | analysis_only；提取两项必备条件并定位原文 |
| 复测 Excel | harness:f8a6fd0c5253489eb9f5b73cf08e37c4 | 2 | analysis_only；余额150万、本期借方20万、期末170万，保留凭证需求 |
| 复测入职 | harness:4b9a0aa2253048d78174434d25231aff | 2 | analysis_only；识别吴嘉木日期/岗位与不开通研发权限的个人例外 |
| 复测后续 | harness:0424a0c8b4fe4659bb233797cf54b33f | 3 | 原主题为招聘；待协作授权后人工改回单主控。保留 JD 引用，另一条表格引用无法定位而暂停 |

复测三个初始 Run 均未产生 workspace_artifacts；它们是页面分析，不是导出 Word/Excel 成果。
复测后续 Task 为 task-7d37fad2cc4a，parent 为 Word Run a632…；只 POST /continue，不 POST /runs。parentUnchanged=true，GET Task 显示两段历史。
复测后续初次仅1次规划调用而等待授权；后人工切回单主控，最终共3次调用，waiting_input，不是 completed。
原始回执与错误样例保留在 outputs/task-journey-20261024；修复后在 retest 子目录；API 重启前公共记录已归档，没有伪造重放。

## 视觉与可用性走查

- 输入阶段：三个普通任务可点选，预期文件可打开，目标可编辑；未提交不调用模型。
- 首轮：显示真实选源、步骤、输入状态；完成/暂停后折叠首轮详情，当前待办不被长说明压住。
- 后续：原业务标题、初始处理、后续分支同屏；历史只读；当前待办和保留成果可见。
- 实际页面1680/390无文档横向溢出、无 pageerror；分支导航自身允许横向滚动。
- screenshots：retest/word-input.png、word-plan.png、excel-evidence.png、onboarding-evidence.png、followup-final-1680.png、followup-final-390.png。
- 收尾补查：手机分支条会将当前项滚入可见区域；未知回执时禁止改选另一条建议。对应两项桌面/手机回归再次验证。
- HTML 汇报使用内嵌原截图；1680/390宽度无文档溢出，图片均正常载入，无 pageerror，记录在 report-checks.json。
- `followup-checks.json` 保存请求、Task lineage、父记录不变及浏览器检查。`followup-final.json` 保存人工切回单主控后的真实暂停状态。

## 尚未解决的能力边界

- 模型输出完整性仍不足：复测 Word 结果仅有两项必备条件，未完整展开加分项；入职结果未完整列出硬件物资。不将这些记录称为完整招聘表/完整入职清单交付。
- 语义缺源与引用定位不足不同：本次后续暂停的直接原因是候选 quote 无法定位，不能宣称系统严格证明了缺失业务材料。
- 上下文帮助保持原主题，但没有自动的跨主题语义验收器；引用定位不证明推理充分。
- 同任务阶段是线性续办，不是任意历史节点多分叉并发；当前只允许终态续办。
- 无新增规划后人工审批 Gate，无私有思维链展示，无外部权限开通、采购、付款或录用动作。
- memory预览重启不保留在线历史；同页未知回执可重试，跨刷新命令恢复未实现。
