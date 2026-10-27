# DR-0073 工作区减法验证

日期：2026-10-08；状态：Limited Verified，仅下述固定范围。

## 场景与来源

[用户授权](../sources/USER-FEEDBACK-20261008-focused-workspace.md)、[Decision](../decisions/DR-0073-focused-workspace-disclosure.md)、[Scenario](../scenarios/SCENARIO-060-focus-task-and-inspect-context.md)。
在原工作树修改前端及测试/文档，不覆盖已有修改，不复制 nanoMuse 源码。

## 前台交互影响与后端事实映射

过程记录默认收起；目录按上下文展开；已提交研究任务编辑区收起，保留目标/状态与既有待办、成果和错误。
Snapshot 是权威；显示切换不发业务 POST、不关闭 SSE、不改变任务或整库来源。

## 验证账本

| 门 | 结果 | 回执与边界 |
| --- | --- | --- |
| 初次定向浏览器 | 2 passed / 4 failed | `outputs/ui-focus-20261008/targeted.xml`；三项新测试误用完成 Fixture 断言待办，一项旧测试未打开新增过程入口 |
| 修正后定向 | 4 passed | `outputs/ui-focus-20261008/targeted-fixed.xml`；正确使用 waiting Fixture，先展开再检查调用明细，保留原断言 |
| 首次全量浏览器 | 144 passed / 8 failed | `outputs/ui-focus-20261008/browser-full.xml`；发现日志隐藏连带隐藏重要回执、设置折叠后的旧断言，以及文件浏览测试与历史恢复竞争 |
| 中间定向修复 | 8 passed / 3 failed | `outputs/ui-focus-20261008/targeted-regression-fixed.xml`；缺少图标 import 导致重要回执崩溃，已补齐；不是最终通过证据 |
| 最终全量浏览器 | 152 passed，0 failed / skipped | `outputs/ui-focus-20261008/browser-final.xml`，408.9 秒；原产品、事项与历史 HTML 的组合回归，不是业务正确率 |
| TypeScript / build / 治理 | 全部通过；治理 4 passed | `pnpm lint`、`next build --webpack`、`tests/unit/test_reporting_governance.py`；构建输出保留在本次 outputs，自动生成的配置路径已清理 |
| 截图 | 已逐张核看 1920 / 1280 / 390 | `outputs/ui-focus-20261008/screenshots/` 中 focused-waiting、live-draft 以及 judgment；未覆盖历史报告图片 |
| 原 3000 页面冒烟 | 桌面/手机均通过 | 独立浏览器上下文新建草稿、打开/关闭过程区；0 POST、0 pageerror、无横向溢出；API 健康，保留原 memory 服务和用户任务 |
| Provider / PostgreSQL / 真人研究 | 未执行 | 不声称模型质量、持久恢复或用户效率提升 |

## 手动自测

1. `/` 新建任务，目录搜索后收起再展开，搜索条件保留；输入草稿不变。
2. 办理事项选择“核对材料分歧”；未选择时不能记录判断，两份材料和理由仍在主区。
3. 顶栏打开过程记录，再关闭，焦点回到入口；查看不产生执行。原 Agent 能力入口不变。
4. 已有研究任务展开“任务要求与运行设置”，核对目标与预算，再收起；待办仍走原控件。

## 回归发现与修复

- 将数字/叙事拒绝、失败与成果恢复回执放回主区，保留服务器消息和原失败恢复控件。不能用“全部藏到日志”换取简洁。
- 仅对有意折叠的设置与调用明细调整测试操作：先展开再验证，未删除禁用、原文、预算或调用事实断言。
- 实际资料预览测试先进入新任务草稿，排除同一临时 API 上上个事项的自动恢复；仍检查 212 行、最后一行可见、零 POST 与无溢出。
- 截图发现手机端多一个入口后“任务会话”落入 44px 图标列，已改自然换行并增加按钮尺寸断言。
- 过程区打开移入焦点，Escape/关闭回到入口；桌面和手机均验证。查看/收起不新增业务请求。

## 未完成

不是整个 nanoMuse 风格改造，不统一业务权限，不补 Worker 歧义恢复闭环。
原研究任务的完整执行记录仍较长，本轮只压缩辅助区域，不声称完成整个页面的信息架构重构。

## 复跑与工作树

- 分支 `codex/demo123-integration`，基线 `fa974ae339c9c4d97d0505eb3eef3e8a81e8ca11` 加既有本地改动与本轮改动，尚未提交或推送。
- 浏览器：在 `apps/web` 运行 `pnpm exec playwright test --config playwright.integration.config.ts --reporter=line,junit`，JUnit 输出指定本次目录；系统 Edge，1 worker，临时 8011 / 3011，API 为 memory 且模型密钥为空。
- 原 3000 冒烟仅查看和本地草稿切换；真实模型、外部动作、数据库和目标用户实验未运行。
- `git diff --check` 通过；仅存在工作树既有的 CRLF 提示。
