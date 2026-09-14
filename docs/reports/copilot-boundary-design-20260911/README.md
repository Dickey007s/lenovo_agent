# 人机共驾：动态边界设计实验

2026-09-11，独立 `Draft`。不受历史 L0-L5 或 R0-R3 分类约束；不会放宽当前产品权限。

## 交付入口

- [2026-09-12 共驾调研推荐](research/followup-20260912/recommendations.md)：6 篇增量论文、3 篇官方实践，按共同参与、有效监督和检查时机组织；HTML“研究与方案”页同步提供分类、搜索与证据限制。

- [2026-09-12 理解风险与修复](usability-review-20260912.md)、[非诱导用户测试协议](comprehension-protocol.md)：区别程序一致性与真实用户理解，尚未收集参与者答案。

- [HTML 工作台](index.html)：8 种合成情境、作用范围、具体动作预览、模拟控制、版本/过期/丢回执变化、研究对照及验收用例。
- [设计说明](design.md)：动态边界维度、三个 Demo 的关系、用户试验方案和未实现协议。
- [研究发现](research/findings.md)、[增量来源台账](research/sources.json)：原始论文/官方博客与文档链接，日期、实际读取范围、反证与限制。
- [实际验证](verification.md)：状态检查、浏览器结果、截图和未测内容。
- [DR-0062](../../decisions/DR-0062-dynamic-boundary-design-experiment.md)、[SCENARIO-049](../../scenarios/SCENARIO-049-dynamic-boundary-handoff-design.md)。

直接打开 HTML 即可，不需要服务。页面仅加载本目录静态文件，没有网络请求、CDN、远程字体、模型或数据库。所有审批、提交、回执都明确标识为模拟，真实外部动作始终为 0。外部论文链接只有主动点击才访问外站。

## 实现与测试

`model.js` 是离线情境状态转换，不是 Runtime 授权实现；不能拷贝进后端当成安全边界。`presenter.js` 把状态转成业务文案与按钮，`app.js` 使用这一投影渲染本地模拟。`build.cjs` 从项目已有 Tabler 图标库生成本地图标，从 `research/presentation.json` 生成原有摘要，从 `research/followup-20260912/{papers,engineering}.json` 生成新增推荐数据。`research-view.js` 只对本地资料分类、搜索和排序；这些展示均不取代完整来源台账。

```powershell
node docs/reports/copilot-boundary-design-20260911/build.cjs
node --test docs/reports/copilot-boundary-design-20260911/model.test.cjs docs/reports/copilot-boundary-design-20260911/presenter.test.cjs docs/reports/copilot-boundary-design-20260911/research.test.cjs
node docs/reports/copilot-boundary-design-20260911/verify.cjs
uv run pytest tests/unit/test_reporting_governance.py -q
```

浏览器套件保存在 `apps/web/playwright.boundary.config.ts`，不启动 Web/API 服务。目前页面受 Browser URL policy 限制，不可作为替代浏览器绕过访问；允许的浏览器环境恢复后再复验。旧截图仅保留为历史记录，不覆盖成新的验证证据。

验证限制：初版 3 项浏览器检查通过；随后内置 Browser 拒绝新 HTML 的本地导航，未绕过。最后补丁为 22 项模型测试通过与源码检查通过，新增浏览器断言未执行；不可把初版截图/结果当作最终补丁已复验。

上段为 2026-09-11 时间线。2026-09-12 又追加状态/文案契约与异常查询测试，结果以 [最新验证小节](verification.md#2026-09-12-理解一致性迭代) 为准；最终页面与目标用户理解仍未验收。

## 本轮不做的事

不把“提示更少”当成功，不把一个预印本的结果泛化为所有委派形式；不把新界面写成目标用户效果已验证；不修改当前真实工作台、旧参考原件或既有 Task/Run/API 合同。原项目的内容完整性开放问题仍然保留。
