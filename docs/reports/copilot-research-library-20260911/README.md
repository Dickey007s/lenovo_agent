# 人机共驾研究资料库

日期：2026-09-11。独立研究附件，不修改当前产品合同，不接入 Runtime。

## 入口

- [后续动态边界设计](../copilot-boundary-design-20260911/index.html)：依据用户新要求，不受旧等级约束，补充定向研究、反证、8 类可操作情境和对照验证计划。
- [项目定位回溯](project-positioning.md)：先读。基于旧会后反馈、v5 讲稿与原型，明确业务动作控制主线及原有 L0-L5，区分此前另拟的 R0-R3。
- [浏览资料库](index.html)：18 项来源的搜索、主题/类型筛选、排序、原文入口、详情与 7 条规则到 Demo 映射。
- [研究简报](research.md)：研究主线、矛盾与限制、评审门和后续技术回溯。
- [来源台账](sources.json)：唯一人工编辑的数据源，含 10 篇论文/预印本、8 项官方文档/文章/报告。
- [检查记录](verification.json)：源码级验证结果，不代表真实浏览器或 Runtime 通过。
- [浏览器验收与截图](browser-verification.md)：独立记录桌面/移动离线交互及修复的问题。
- [此前 Demo3 沙盘](../human-agent-copilot-20260911/index.html)：仍为 Draft，与本次研究附件分离。

## 运行与构建

`index.html` 及本目录文件一同保留即可直接从本地打开，无需开发服务器。网页仅使用本地 CSS、JS 与 Tabler 图标；无 CDN、远程字体、iframe、网络请求或模型调用。只有点击明确的来源链接才访问外站。

`sources-data.js` 由 JSON 生成，避免 `file://` 读取 JSON 的跨域限制。修改元数据后在仓库已安装 web 依赖的环境运行：

```powershell
node docs/reports/copilot-research-library-20260911/build.cjs
node docs/reports/copilot-research-library-20260911/verify.cjs
```

构建读取项目现有 `react`、`react-dom/server` 和 `@tabler/icons-react`，只向本目录写入派生数据、图标及许可证。浏览已构建页面不需要这些依赖。检查脚本只测试本地数据/代码，**不执行联网来源复核**，也不把 `verified_at` 字段本身当作联网证据。

## 证据口径

每项来源已通过本轮 web 工具实际打开至少一个原始页面、摘要或 PDF；详情中注明读取范围。S08 只核验摘要和作者官方解读，全文未核验。论文/页面日期与检索日分开；滚动文档不补造发布日期。

元分析不把 human augmentation 写成超过最佳单方的 synergy；不将创作子组方向性点估计写成显著收益。两个计划/分步审阅预印本不推定已通过同行评审。研究观察与所有 Demo 建议明确分离。历史项目方案使用 L0-L5；此前 R0-R3 仅是新拟草稿，不能替代历史方案，详见项目定位回溯。

构建成功，最终 `verify.cjs` 为 **61 passed / 0 failed**，覆盖数据字段、来源分类、派生文件一致性、筛选/空结果/排序、详情转义、Demo 映射、事件处理模拟、离线资源与 CSS 语法。这里不把 Node VM 模拟称作真实浏览器测试。

研究子任务最初只验证源码；主任务随后补做独立 Playwright 离线浏览器验收，1440/390 px **2 passed**，并修复搜索失焦导致首次点击丢失和流程副标题竖排。详情/Escape/焦点、筛选、规则映射及无横向溢出均纳入。未运行 Runtime、Provider、框架审批样例或用户实验，未逐项点击外站复测。此前独立沙盘的本地导航曾被 Browser URL policy 拒绝，本轮没有绕过或重访该资源；此处测试的是新建研究库。

## 文件

`index.html` / `styles.css` / `app.js` 是手工页面代码；`sources.json` 是结构化研究记录；`sources-data.js` / `icons.js` / `TABLER-LICENSE` 为构建产物；`build.cjs` / `verify.cjs` 是构建与验证脚本；`verification.json` 为验证产物。未下载论文全文或外部网页资产。

论文题名、摘要页与原文的版权仍属其作者/出版机构；本库提供简要中文归纳与链接，不重新分发正文。图标依照附带 MIT 许可证使用。
