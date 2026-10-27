# DR-0072 统一工作台整合记录

- 日期：2026-10-07；状态：Limited Verified，限统一入口、已测试的迟到响应隔离与兼容共存。最终组合浏览器 149 项、末次 TS/build 均通过；Worker 决定恢复桥未完成。
- Decision：[DR-0072](../decisions/DR-0072-unified-workbench-and-response-ownership.md)。
- Scenario：[SCENARIO-059](../scenarios/SCENARIO-059-switch-workbench-without-stale-responses.md)。
- Source：[用户要求与范围](../sources/USER-FEEDBACK-20261007-unified-workbench.md)。
- 远程基线与当前 HEAD：`fa974ae`；工作分支 `codex/demo123-integration`。当前增量未提交，备份 stash 保留未 drop。
- 本地备份对象：`8215e2e439406ce385d5f2f3d94e3664f0ef0f0d`；原 424 个未跟踪文件路径均仍存在。原 master 指针未移动，集成分支已快进接入队友四次提交，随后恢复本地工作。

## 场景与来源

本轮组合远程六类 Demo3 单步事项与本地 DR-0064 至 DR-0069 的 Loop/Swarm 优化。不同分支的旧测试仍只证明原版本，本文件不把历史通过数量加总成集成通过。

先前 git merge-file 预检报告 11 处冲突文件；实际 stash apply 产生 8 个冲突文件，两者是不同检查，不混写。文档侧五份冲突文件保留两边独立增量，不用一侧覆盖另一侧。

## 编号迁移

| 记录 | 远程此前编号 | 本轮当前编号 | 说明 |
| --- | --- | --- | --- |
| 单步事项边界 | DR-0064（更早 Demo3 分支为 DR-0053） | [DR-0070](../decisions/DR-0070-single-action-boundary-workbench.md) | 本地 DR-0064 来源可靠性不变 |
| 草稿编辑与人工判断 | DR-0065（更早为 DR-0054） | [DR-0071](../decisions/DR-0071-demo3-editable-drafts-and-human-judgment.md) | 本地 DR-0065 输出/交接不变 |
| 单步事项场景 | SCENARIO-051 | [SCENARIO-057](../scenarios/SCENARIO-057-single-action-boundary-workbench.md) | 本地 051 不变 |
| 材料判断与找回 | SCENARIO-052 | [SCENARIO-058](../scenarios/SCENARIO-058-demo3-human-judgment-and-return.md) | 本地 052 不变 |

历史 Evidence 文件名、原编号叙述、提交及测试数字保留；只将相对链接指向迁移后的实际文件。本轮迁移是文档消歧，不是重新实现、重新验证或撤回历史结果。

## 前台交互影响与后端事实映射

根页与能力页空白新任务均提供“分析资料 / 办理事项”。选中 office_action Run 时使用原事项界面，隐藏不适用的 Loop/成果入口；原历史 tasklist 保留。每个事项请求绑定发起 sessionGeneration，成功、错误与 409 刷新均需匹配；父层再次拒绝旧会话回执。初始化 restoreLatestRun 同样检查代次；局部“办理另一件事项”通过 readRef 失效旧读取。相关代码在原 HarnessWorkbench 与 OfficeActionWorkbench，不新建产品。前台保护不等于后端取消、批准或执行；最终组合门通过范围见下表。

## 验证账本

| 门 | 本轮结果 | 回执位置/边界 |
| --- | --- | --- |
| 文档冲突与编号/相对链接 | passed | README/AGENTS/docs 无冲突标记；Decision/Scenario 目录各自无重复编号；19 份相关 Markdown 的 682 条本地链接存在，未验证锚点语义或外网可达 |
| 文档治理与空白检查 | 4 passed；diff check passed | `pytest tests/unit/test_reporting_governance.py -q`；`git diff --check -- README.md AGENTS.md docs` 无错误，仅 Windows 换行提示 |
| 后端定向 | 131 passed | `outputs/integration-20261007/backend-targeted.xml`；不与全量简单相加 |
| 后端全量 | 571 passed, 26 skipped；321.28 秒 | `outputs/integration-20261007/backend-full.xml`；26 个真实 PG 条件测试因无 TEST_DATABASE_DSN 跳过 |
| 新增同 Owner 共存门 | 单独 2 passed | `outputs/review-20261007/demo123-shared-runtime.xml`；验证 Loop/Swarm 成果不被事项改变、无额外模型调用、幂等合同并存；加入时全量已收集，不宣称单次 573 |
| 后端最终重跑（包含新增两项） | 573 passed, 26 skipped；控制台 304.48 秒、XML 304.395 秒 | `outputs/integration-20261007/backend-final.xml`；这是完整单次执行，不是把历史数字相加 |
| Ruff | 最终全库 `ruff check .` passed | 合并漏掉 psycopg import 已补；不表示真实 PG 测试已跑 |
| 浏览器第一轮全目录 | 144 passed / 3 failed | `outputs/integration-20261007/browser-full.xml`；失败保留，下文说明修复 |
| 浏览器第二轮全目录 | 147 passed | `outputs/integration-20261007/browser-final.xml`；尚不含随后新增的两项导航竞态 |
| 新增导航竞态负例 | 2 failed | `outputs/integration-20261007/browser-navigation-red.xml`；初始化旧任务恢复覆盖新事项、旧核对结果关闭新草稿 |
| 导航竞态修复定向 | 2 passed | `outputs/integration-20261007/browser-navigation-green.xml`；真实 API 响应加人工延迟，无模型调用 |
| 最终组合浏览器门 | 完整单次 149 passed；约 7.1 分钟，XML 426.410984 秒 | `outputs/integration-20261007/browser-release.xml`；failures/errors/skipped 均为 0，不是把 147 与单独 2 相加 |
| TypeScript / webpack build | 最后修复后 `pnpm lint`（tsc --noEmit）及 `pnpm exec next build --webpack` 通过 | Next 16.2.10；compile 3.9 秒、TS 7.5 秒；路由 `/`、`/agent-capabilities` |
| 最终 diff check | passed | `git diff --check` 无错误，仅 Windows CRLF 提示 |
| 1920 / 390 px 截图 | 已捕获；action-1920、judgment-1920、judgment-390 已人工核看 | `outputs/integration-20261007/screenshots/`；1920 桌面无页面横向溢出，390 材料纵向排列；不证明用户收益 |
| 真实 Provider / 新 PostgreSQL / 目标用户 | 未执行 | 不借历史回执宣称新增保证 |

### 浏览器首轮反例与修复

第一次全目录回归为 144 passed / 3 failed，保留 `outputs/integration-20261007/browser-full.xml` 和
`outputs/integration-20261007/first-browser-failures/` 的截图、trace、错误上下文。
新增模式按钮在手机上只有 40px 高，被原有 44px 点击区域验收拦住；已修为 44px，不放宽测试。
另外两项来自未改动的旧独立 HTML 原型：结果预览断言误用了选项标签文字；移动测试没有先聚焦
下拉框就断言焦点保持。仅校正测试的实际正文和操作前提，保留 92% 的样本口径、禁止外发和焦点
断言，不修改原型 HTML 或历史成果。修复后的最终回归另列，不覆盖首轮失败。

单步响应隔离也适用于迟到成功、409/500、显式打开历史和分析/事项切换。原 Loop 的控制、Worker
派发、continuation 和 current-task 读取补齐同类发起代次校验，旧错误不污染新上下文。
不因切换视图取消后端执行，也不声称每一种网络竞态都穷举验证。

### 147 项通过之后的新反例

`office-navigation-races.spec.ts` 再现两条此前未覆盖路径：初始化的旧 Task GET 在用户创建并完成新事项后迟到，可能替换新事项及 active-run 指针；已完成事项的“核对最新状态”在“办理另一件事项”后返回，可能关闭尚未提交的新草稿。
两项先红后绿，分别补 restoreLatestRun 的 session generation 校验和局部 newItem 的 readRef 失效。随后完整单次 149 项组合门通过；定向结果与全量结果分别保存，不删除或覆盖红灯 XML。

## 用户三步自测

截图补充：[事项桌面](../../outputs/integration-20261007/screenshots/action-1920.png)、[材料判断桌面](../../outputs/integration-20261007/screenshots/judgment-1920.png)、[材料判断窄屏](../../outputs/integration-20261007/screenshots/judgment-390.png)。桌面中心工作区独立滚动，fullPage 图不代表所有事项内容同时可见；[底部人工操作](../../outputs/integration-20261007/screenshots/human-controls.png)单独展示确认区。

1. **找到原入口。** 打开已启动系统的 `/`，点“新建任务”，切换“分析资料 / 办理事项”；再到 `/agent-capabilities` 重复。预期两处都是原工作台，事项不出现假的 Loop/Worker 执行进度；只切换模式不创建任务或调用模型。若另开一套 Demo 页面或切换就开始执行，判失败。
2. **记录一个明确的人类判断。** “办理事项”选“核对材料分歧”，标题填“评审截止日期核对”，事项内容填“材料 A：周五提交”，第二份材料填“材料 B：周一提交”，点“开始办理”。先不选择，确认“记录这次判断”不可用；选“采用材料 A”，理由填“本次按已确认的周五截止要求准备”，再记录。预期看到“你的判断已记录”，两份材料仍在；不发送邮件、不启动 Worker。若未选择就提交、原文被覆盖或声称业务审批完成，判失败。
3. **保留新草稿与旧结果。** 完成事项后点“办理另一件事项”，标题填“尚未提交的新备忘”，内容填“周三核对交付材料”；确认草稿可编辑。返回原历史打开刚才判断记录，核对结果仍在；查看既有研究任务的执行记录/协作后返回，原成果不变。若普通查看发起执行、旧结果丢失或新草稿突然被旧响应替换，判失败。网络迟到部分已另用自动化注入测试，普通人工操作不能证明所有竞态。

三步是可重复的用户验收方法；对应工程路径已在事项/整合浏览器测试验证，不冒充真人理解研究。初始化恢复与局部新草稿两条竞态的实际结果见上表。

## 可操作验收

1. 输入材料 A“周五提交”、材料 B“周一提交”，建立材料对照事项；未选且理由为空时不能记录判断。显式选择并填写理由只保存测试判断，不发邮件、不触发 Worker。
2. 打开既有研究任务，分别查看执行记录和协作，再返回进展；查看不产生模型或控制 POST，原成果和状态不变。
3. 注入旧任务 GET/list 延迟，切换到新建草稿或其他允许切换的上下文，再释放响应；新视图不被旧响应覆盖。旧命令响应的相关限制与覆盖按实际测试补录。
4. 现有未知结果重试、幂等和版本冲突路径不得退化；失败不得显示记录成功。

上述工程路径由已记录的真实 API 事项测试、受控界面回归及导航延迟测试分别覆盖；最终组合回归另列。未覆盖的网络状态或业务场景不得由这些用例外推为通过。

## 未闭合与禁止外推

Worker ambiguous 回执仍不等于可提交的人类决定。结构化候选持久化、目标 Worker 新 attempt、BLOCKED 依赖解除及下游再次显式派发是下一独立纵切，本轮不承诺完成。无真实外部动作、企业审批、分布式 Worker、通用语义验证或用户收益声明。

## 本地演示启动边界

已启动原 `http://localhost:3000` 开发入口，页面 GET 返回 200；后端 `http://127.0.0.1:8010/v1/health` 返回 `status=ok`、`checkpoint=memory`、`task_store=memory`。显式使用 `STATE_STORE_MODE=memory`，不修改或迁移已有 PostgreSQL 数据。仅启动开发服务不预先调用模型，配置模型名不是调用证据。
memory 中本次新建任务会随后端服务重启丢失，不能称为持久恢复；不影响已有 PostgreSQL 内的数据。健康回执只证明本次启动就绪，不证明模型可用或业务任务完成。启动进程为 API 14280、Web 27528，日志位于 `.runtime/integration-api.*.log` 与 `.runtime/integration-web.*.log`。
