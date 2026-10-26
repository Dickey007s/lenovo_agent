# DR-0074 执行记录减法验证

日期：2026-10-08；状态：Limited Verified，限下述工程与固定浏览器范围。

## 场景与来源

[授权](../sources/USER-FEEDBACK-20261008-execution-detail.md)、[Decision](../decisions/DR-0074-execution-detail-disclosure.md)、[Scenario](../scenarios/SCENARIO-061-inspect-execution-without-detail-wall.md)。
基于 `codex/demo123-integration` / `fa974ae339c9c4d97d0505eb3eef3e8a81e8ca11` 加既有未提交改动；本轮未提交或推送。

## 前台交互影响与后端事实映射

原资料库的处理历史、材料、全部完成分支和版本列表按需展开。续办/来源变化/只读/Task 错误、
未完成分支、业务 Gate、模型输入范围和人工控制保持原投影。无后端业务改动。

## 验证与边界

| 门 | 结果 | 回执 |
| --- | --- | --- |
| 定向浏览器 | 11 passed | `outputs/execution-focus-20261008/targeted.xml`，36 秒 |
| 最终组合浏览器 | 156 passed，0 failed / skipped | `outputs/execution-focus-20261008/browser-full.xml`，6.9 分钟；临时 8011 / 3011，模型密钥为空，memory；不是业务正确率 |
| TypeScript | passed | `pnpm lint` |
| build | passed | `next build --webpack`；临时 dist 产物移入本次 outputs，清理其自动添加的配置路径 |
| 治理 | 4 passed | `tests/unit/test_reporting_governance.py` |
| 截图 | 已核看等待/完成两态的桌面及手机四张 | `outputs/execution-focus-20261008/screenshots/` |
| 原服务 | 页面 200，API healthy / memory | 不重启用户服务，不提交真实模型任务 |
| Provider / PostgreSQL / 目标用户研究 | 未运行 | 无新增模型质量、持久恢复或用户收益证据 |

新测试覆盖 1920/390px、等待/完成、待办与停止按钮保留、折叠内容键盘可达、零额外控制/启动请求、
无 pageerror 与横向溢出。旧恢复用例先展开版本再执行原断言，未删掉恢复/原文检查。

## 手动自测

1. 原资料库提交一项任务，保留当前成果和待处理分支，预算始终可见。
2. 展开“本轮过程与材料”核对来源，再收起；不触发重新执行。
3. 展开“成果版本”，选择历史版本恢复；检查主区回执、当前版本与旧版本保留。
4. 打开续办、历史 Run 或 Task 查询失败的记录，时间线与恢复动作不能默认隐藏。

本轮不新增 Worker 人工恢复，不改变单步事项；完整复杂任务效果与真人理解仍需单独验收。

复跑：在 `apps/web` 设置 `PLAYWRIGHT_JUNIT_OUTPUT_FILE` 指向本轮回执目录，运行
`pnpm exec playwright test --config playwright.integration.config.ts --reporter=line,junit`。
系统 Edge、1 worker；156 项总计 416.4 秒。`git diff --check` 通过，CRLF 警告不计作业务错误。
