# DR-0088 人机分工实测记录

日期：2026-10-24；未提交工作树，HEAD 基线 fa974ae。
Decision：[DR-0088](../decisions/DR-0088-evidence-based-human-agent-division.md)。
Source：[用户要求](../sources/USER-FEEDBACK-20261024-human-agent-division.md)。
Scenario：[SCENARIO-075](../scenarios/SCENARIO-075-distinguish-system-work-human-judgment-and-repair.md)。

## 真实 Provider 结果

环境：http://localhost:3010/ + 独立 API 8010，memory 状态库。deepseek-v4-pro；每项最多2轮/6调用，analysis_only。没有密钥或私有思维链写入汇报。

| 阶段 | Run | 调用 | 实际结果 |
| --- | --- | --- | --- |
| 首测明确规则 | harness:25efcf4dbb9b440f907a0e48742a1e20 | 2 | completed，直接整理吴嘉木权限，无业务待决 |
| 首测缺回单 | harness:e8b203fd1fc1496f852b53207c8f50c5 | 2 | waiting_input，误选三期往来表，只有背景引用的缺源说明被早期 UI 误计为已处理 |
| 首测例外变更 | harness:4a8ae29e3ad34443a8abc125f6c0769d | 2 | completed，通用软件清单与人工取舍分开 |
| 复测明确规则 | harness:7e6255124fdc4464b40224ec456ecf91 | 2 | completed，1项系统分析、0项人工待决 |
| 复测缺回单 | harness:b0358291ad664f6a857c1512e804c46f | 2 | completed，1项有依据的余额分析、1项 uncovered 要求，列表显示待补资料 |
| 复测例外变更 | harness:7c2901fad9f24a23bd81620f706b9809 | 2 | completed，1项系统分析、1项人工待决 |
| 明确选择后续办 | harness:43a8e34d89dd466ab16674aa76d79a95 | 2 | 同 task-ed376c021306、parent指向前项；completed，清单不含GitHub Enterprise |
| 保留可演示待决 | harness:1efe754a540b48e082e5ffd0bda44b2d | 2 | completed但仍有1项人工待决；只浏览未提交决定 |

合计8次真实运行、16次模型调用。Loop completed 不等于业务任务全部完成，特别是缺回单和仍待人选择的两项。
API 重启前首测公开 Snapshot 已存档；复测后的在线历史仍在独立 memory 服务，重启会清空，不冒充持久化。

## 发现与修正

1. 首测财务任务把三期往来账作为银行回单的替代候选。模型没有说已经到账，但它没有正确用缺源要求表达。加强 Planner 来源类型指导后，复测公开 Plan 出现 uncovered，余额分析继续完成。此为单样例提示改进，不是确定性来源语义校验。
2. 早期分工投影仅凭 Anchor 把未完成工作项和纯 context 引用算作已处理。修正为工作项完成、非背景引用、无未决、无业务否决才入列；不从标题关键词猜分类。
3. 截图脚本曾在 API 终态而页面 SSE 尚未收敛时抓到过渡画面。最终脚本重新载入真实 Run，断言两栏数量后再截图；初始快照保留，不当作最终 UI 验证。
4. 自动回归首次未切回任务页，后续移动回归未展开隐藏导航，均为测试定位问题。修正为按用户路径切换/展开，不降低断言。

## 人的选择确实回交给 Agent

`review-task-responsibility.cjs` 在三项浏览过程中确认没有 POST；打开审核页后无默认选项，接受按钮禁用。
随后明确选择 A“维持现规则”：原 Run 记录 accept/A，再通过 /continue 创建同 Task 的 child Run；原结果保留，新结果读取两份原资料并排除研发软件。
浏览和确认的 POST 记录、原 Run 决定、child Snapshot 在 `outputs/task-responsibility-20261024/final/`。这是只读分析续办，不是真实权限开通或业务审批。

## 截图与可复现脚本

- 原始首测：`outputs/task-responsibility-20261024/*.json`。
- 提示修正后的复测：`outputs/task-responsibility-20261024/retest/`。
- 最终界面断言、1680/390截图、交接：`outputs/task-responsibility-20261024/final/`。
- 另一次真实待决及已加载原文的选项截图：`outputs/task-responsibility-20261024/pending/review/`。
- 三组任务：`node scripts/exercise-task-responsibility.cjs <新输出目录>`，第三参数可为 rule/missing/judgment。
- 浏览与一次明确只读选择：`node scripts/review-task-responsibility.cjs`；它会对指定复测 Run 接受A，不能当作无副作用截图脚本重复跑。
- `--inspect-pending` 只浏览 pending 目录对应记录，不提交决定。所有案例预设点击本身不调用模型。

真实三组最终页的桌面/手机共6种组合没有页面横向溢出、没有 pageerror。已人工查看桌面分工、移动布局和真实决定页；来源预览加载完成后才保留最终选项截图。
图文报告：`docs/reports/task-responsibility-20261024/index.html`，5张真实截图内嵌；1680/390两种宽度均已检查图像加载、横向溢出和脚本错误，全部通过。

## 自动化

后端定向：78 passed，覆盖原范围/逐项要求、同 Task 续办、自动只读策略、Worker可靠性与汇报治理。

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_harness_runtime.py tests/acceptance/test_task_followups.py tests/acceptance/test_automatic_readonly.py tests/acceptance/test_demo12_worker_reliability.py tests/unit/test_reporting_governance.py -q
```

Web：TypeScript检查通过。最终定向回归 38 passed (1.8m)，其中6项纯投影测试、32项浏览器交互。未运行全库历史回归。

```powershell
pnpm exec playwright test e2e/task-responsibility.spec.ts e2e/harness-workbench.spec.ts e2e/office-actions.spec.ts --config playwright.integration.config.ts --grep 'responsibility|unified reference|real API:|keeps 2 evidence choices|Agent capabilities route distinguishes|Task Ledger success|ambiguous Worker without a decision|Agent capabilities route exposes a real review|keeps table-location|continues a scoped|requests a same-task' --reporter list
```

此命令中的6项是纯投影断言，其余是浏览器交互；Demo1/2回归使用受控回执，Demo3项使用固定规则真实API。均不能替代上表的真实模型运行，也不是全量回归。

## 不声称的能力

没有置信度校准、通用判断准确率、任意缺源自动发现、上传回单后闭环、真实账号开通/采购/支付或用户体验量化研究。技术补证的受限自动重试沿用已有Runtime，本轮没有新增无限重试或主动忽略人工门。
复测缺源成功不掩盖首测误选；Model narrative和引用定位不证明财务事实完整。UI分析条目计数不是业务要求总数。
