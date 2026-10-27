# DR-0095 Evidence：统一演示工作区与分层展示

日期：2026-10-26。工作树未提交；来源、场景与决定见 DR-0095。

## 实现范围

- Demo2：指令、调用与预算折叠；默认一条结果摘要，其余结果展开。错误和未完成内容保留。
- 协作图：没有新增工作的原因按需查看；实际 Agent 数量、工作状态及调整结果保留。
- Demo3：统一表单、状态条、来源对照及结果区；偏好收起、最近事项后置，人工确认合同不变。
- 根页：补充隐藏工作区的 `[hidden]` 显示约束，修复 `display:block` 导致 Demo2 总览下方泄露空依据面板；桌面和手机均有断言。

## 定向回归

- `pnpm --dir apps/web exec tsc --noEmit`：通过。
- 本轮定向 Playwright 合计 23 项通过：7 项 harness 工作台检查，以及 16 项 office-actions / copilot-principles 检查。
- 首次事项回归为 12 通过、4 失败，不能报告首次全绿。两个手机入口在水合前调用 isVisible，跳过导航展开；一个断言匹配旧编辑文案；一个仍点击旧“任务会话”入口及隐藏重复标题。
- 修正后事项相关 16 项通过。手机入口显式等待导航，历史路径使用当前“历史记录”入口，仍保留打开历史及进入能力页不触发 POST 的断言。
- 新用例检查表单同行、无多余外框、偏好默认折叠且调整不 POST、390px 不溢出、完成结果不重复进入状态条、刷新图标有可读名称。
- 没有重跑全部后端或全部浏览器测试；23 项不能外推为全仓库回归通过。

## 真实固定规则走查

通过当前 3000 页面调用实际 8000 API，无模型调用，无外部动作。
发件未勾选时不可确认，L4 依据默认展开，暂缓可保存；材料对照无预选，选择加理由后生成判断记录；摘录编辑形成第 2 版，原文保持不变。
390px 无横向溢出，走查捕获 0 页面异常。截图位于 `outputs/unified-polish-20261026/demo3/`：
`after-draft.png`、`after-confirmation.png`、`after-confirmation-mobile.png`、`after-comparison.png`、`after-excerpt.png`、`after-edited-excerpt.png`、`after-decision.png`。
这些是固定规则实际 API 证据，不是模型语义判断或企业审批证据。

## 模型重跑与截图时机

第一批记录位于 `outputs/showcase-live-20261026`，以下为已读取的实际 Snapshot，不先认定均适合最终展示：

| 记录 | Run ID | 运行状态 | 模型调用 | 说明 |
| --- | --- | --- | ---: | --- |
| rule.json | harness:796ff3d333fc4e7f8e94c157bb546a40 | completed | 2 | 明确权限规则分析 |
| missing.json | harness:8a8802532b49451ca0bac07dfa356dec | waiting_input | 3 | 等待不等于业务成功 |
| handoff.json | harness:b73456332f58431b935737537a4bb314 | completed | 2 | 是否形成实际人工交接需单独核对 |
| batch-task-1.json | harness:9d11244c224f4c5e8d1c3c993b0c9371 | completed | 5 | 3 个 Worker 回执，3 份采用 |
| batch-task-2.json | harness:6f892c3e408440aeb7cd955c3cadfa48 | completed | 2 | 单控制器路径 |
| batch-task-3.json | harness:3b2e9cf1c8dd4788a8f44d54de94e173 | completed | 2 | 单控制器路径 |

同目录 draft/send/judgment 为实际固定规则事项，调用均为 0；分别为 draft_ready、executed、decided。executed 仅指测试发件记录，不是发出邮件。

首批 `swarm-3.png` 出现左列表已完成、主区仍在协调检查的不同步画面。已核对：主区是第 16 个 adaptive_review_started 事件，最终 Snapshot 为 version17 / sequence28 / completed，工作项均 adopted。
列表独立每 3 秒读取，主区经事件通知后读取 Snapshot；二者可短暂不同步。未发现本案 Worker 终态事件误关流的证据，不能仅凭一张截图断言事件流永久卡住。
只读重新打开相同 Run 后，主区显示“可复核”“本次未新增工作”和 3 个“成果已采用”，0 POST。
截图工具改为等待主区真实终态和协调检查结束，不再仅等待某句“等待模型返回”消失。第二批 `verified-refresh` 三项均完成，主区和台账一致后重新截图；三份贡献均 adopted，没有新增工作。

## 最终展示验收

原网页 `docs/showcase/office-agent-20261024/index.html` 已更新，保留左右布局和大图交互。原目录副本保存在 `outputs/showcase-archive-before-unify-20261026`。
本轮捕获脚本共 12 个模型 Run、31 次模型调用；选入展示的是 7 个模型 Run、17 次调用，另有 3 个零模型调用的固定规则事项。Demo2 总览和分工页共享同组任务，不重复计数。这是人工筛选的固定案例，不是完成率统计。
完整去重台账与截图 SHA-256 见 `outputs/showcase-live-20261026/capture-audit.json`；网页也附同名记录。

| 展示内容 | 本次事实 | 来源 |
| --- | --- | --- |
| 明确规则 | 个人备注和覆盖规则均有定位；形成软件清单分析 | rule.json |
| 缺到账回单 | 保留 1 条账面分析，1 项 uncovered；未证明到账 | missing-repeat/missing.json |
| 人工交接 | 明确选择维持规则后，父子 Run 同属 task-a7a9727e1e8b；2+2 次调用 | handoff-repeat/handoff.json / handoff-child.json |
| 多任务 | 三项分别形成 4、2、1 条分析，调用 5、2、2 次 | verified-refresh/batch-task-1..3.json |
| 自适应分工 | 三个 Worker 的贡献均采用；执行后判断不新增 | verified-refresh/batch-task-1.json |
| 草稿、确认、判断 | 编辑形成新版本；修改清空旧确认；选项和理由生成判断记录 | draft.json / send.json / judgment.json |

首次 missing 的账面引用也未通过，因此不用于展示“已保留账面成果”；首次 handoff 没有形成结构化人工选项，因此不用于展示交接。两次原 Snapshot 都保留。再次提交同一示例后才得到上表结果，未修改 Runtime 强制通过。
已逐条阅读入选 Demo2 的原文定位：保留入职备注、岗位条件“优秀者可放宽”及账面空白贷方，不推断收款。Demo1 交接选择 A，仅整理清单；未选择的模型选项 B 使用“批准例外”字样，但其后续合同仅为申请草稿，不能据此声称例外已经获批。此语义措辞仍需后续治理，本轮不冒充已解决。

网页验证覆盖 1920、1440、768、390 宽度，共 124 次案例步骤检查；31 张图均为 1920×1200。验证前进后退、页签键盘切换、原尺寸放大、Escape 焦点恢复和缺图重试；0 页面异常、0 外网请求。证据：`outputs/showcase-live-20261026/validation/validation.json`。

## 待补与限制

- 入选案例已核对分析内容、来源与人工停点；completed 不能替代业务验收。
- 未证明真实动态扩编、最优分工、通用语义正确性或用户体验指标提升。
- PPT 仍单独按附件模板处理，本文不声明 PPT 或全部交付完成。
