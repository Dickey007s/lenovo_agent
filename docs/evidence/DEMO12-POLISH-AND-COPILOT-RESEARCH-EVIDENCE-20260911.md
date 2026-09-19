# Demo 1/2 交互打磨与人机共驾研究 Evidence

日期：2026-09-11。当前脏工作区上的限定增量，未提交或发布。
来源：[用户要求](../sources/USER-FEEDBACK-20260911-ui-polish-and-copilot-research.md)；
Decision：DR-0061；Scenario：SCENARIO-048。

## 1. 实现范围

- 任务标题可以展开完整 `contract.goal`，开合不发请求。
- 空任务提供完整书写区，显示已加载的真实资料数量；提交前不创建 Task。
- 分支栏依实际数量分配宽度；普通控制栏不悬浮遮挡成果。
- 证据页确认区固定可见，未选禁用、预览不选择、错误就近显示；底部和顶部留出滚动空间。
- 新增研究资料库的离线搜索、筛选、排序、来源详情和规则映射。

没有修改 Runtime、API、Provider、审批权限、来源范围或数据库合同。
现存后端未提交变更不是这次 UI 打磨的实现证据。

## 2. 主动发现与纠正

| 问题 | 发现方式 | 修正与验证 |
| --- | --- | --- |
| 长目标在两行后不可完整阅读 | 当前历史任务实际页面 | 原生 disclosure；1280/390 px 回归 |
| 确认按钮位于首屏外 | 当前真实页面 1280×720 DOM 测量 | 按钮由 y=907–953 改为 662–706 |
| 新的普通浮动控制栏遮住成果 | 用户参考与当前 1672 px 截图一起比较 | 普通控制栏恢复正常文档流；证据页单独固定 |
| 固定证据条拦截“取消待决”点击 | 全量回归红灯与失败截图 | 覆盖旧 review grid，改自然文档流并留底部空间；1280/390 px 真实点击回归 |
| 新资料库搜索失焦时第一次点按钮丢失 | 离线浏览器搜索 → 清除筛选红灯 | input 只处理搜索，change 只处理下拉；不重复替换点击目标 |
| 规则流程说明挤成竖排 | 研究库桌面截图人工观察 | 图标容器跨行，说明固定在文字列；单行高度断言 |

另有测试自身修订：空 Run 的旧 CSS 数量断言改为输入为空且启动禁用；不同视口的取消测试
使用独立浏览器上下文，避免复用旧会话。没有删掉取消测试或以强制点击绕过遮挡。
移动截图先回到页首，避免桌面焦点/滚动位置在切换视口后污染取景。

## 3. 实际验证

- 生产构建通过：`NEXT_DIST_DIR=dist/validation pnpm --dir apps/web build`，与真实预览的 `.next` 隔离。
- 报告源码/数据/Node VM：`node docs/reports/copilot-research-library-20260911/verify.cjs`，61 passed。
- 报告离线浏览器：1440×1000、390×844，2 passed；搜索、空结果恢复、详情、Escape/焦点、规则筛选、账本、无网络请求和无错误。
- 治理单测：`uv run pytest tests/unit/test_reporting_governance.py -q`，4 passed。
- 最终全量浏览器：96 passed，3.4 分钟，94 项主应用 + 2 项新研究库；同时重拍最终截图。
- TypeScript lint、`git diff --check` 通过。测试与构建临时生成的 route 类型路径已恢复到正常预览目录。

截图：[工作台](../reports/demo12-polish-20260911/screenshots/)、
[资料库](../reports/copilot-research-library-20260911/screenshots/)。
`live-*.jpg` 来自真实本地服务中的历史任务或空白草稿；其他主应用截图来自受控 API。
实际界面仍显示 3 次既有模型调用，本轮没有新增付费模型调用。关闭核对只写既有 defer，不批准候选。

## 4. 研究证据

[来源 JSON](../reports/copilot-research-library-20260911/sources.json) 记录 18 项不同来源：10 篇论文/预印本、
8 项官方文档/文章/报告。研究子任务通过 web 实际打开至少一个原始页面、摘要或 PDF，逐项注明读取范围。
根任务另核验 Nature 2024 元分析与 Microsoft Appropriate Reliance 原始页面，明确人类增强与超越最佳单方的区别。
网页中的 7 条规则是设计推导，不是论文原句或已验证产品效果。

S08 全文抓取失败，只核验摘要与官方解读；没有提供未经核验的 PDF 下载入口。
源码脚本不执行联网核验，也不能仅凭 `verified_at` 字段证明来源已读。
旧 Demo3 沙盘曾遭 Browser URL policy 拒绝；本轮没有打开、代理或改用另一浏览器访问那个资源。
新研究库为独立文件，使用用户已批准的 Playwright 回归工具离线验证。

## 5. 未解决范围

Q-01 模型日志输入截断、摘要范围未限定仍开放，本轮未修复；引用位置可见不代表全文覆盖或结论正确。
无新增真实 Provider、PostgreSQL 重启、真实多 Worker、目标用户研究或业务效果实验。
没有测试所有浏览器/设备、屏幕阅读器、200% 缩放或所有外部网站跳转。
Demo3 与风险分层仍为 Draft，定向资料库不替代三个 Demo 完成后的完整技术时效性回溯。

## 6. 同日补充：项目语境回溯

依据用户后续要求，新增 [项目定位回溯](../reports/copilot-research-library-20260911/project-positioning.md)，
并在研究简报、研究 README 与本轮用户 Source 中建立入口。原会后摘要的 Demo3 定位为全链路风险分级与动作控制；
v5 讲稿 P21/P22 与原始 HTML 明确 L0-L5 和时间、组织、动作三个控制维度。
此前另拟的 R0-R3 不替代该历史基线；信任、解释和证据核验改作支撑动作治理的辅助研究。

本补充未更改原始材料、18 项来源台账、网页代码、Runtime 或现行 API/Decision/Scenario/UI-server 合同。
不将历史设计或旧 risk/gateway 模块文件的存在提升为当前已挂载能力。

实际检查：

- v5 Markdown 与原始 HTML 的 SHA-256 均与 `docs/final-reference/README.md` 一致。
- 四份新增/修订研究与 Source Markdown 中的 21 个本地链接目标均存在。
- `uv run pytest tests/unit/test_reporting_governance.py -q`：4 passed。
- 本补充没有重新运行浏览器 E2E、联网来源核验、Provider 或外部动作；上文 96 项浏览器结果属于此前 UI 修改的验证，不能记作本次重跑。
