# Demo 1 / Demo 2 重设计评审包

直接打开 [index.html](index.html)。无需构建和网络资源；保持本目录结构即可。

- 四视图截图可切换，并能与用户参考图对照。
- `references/` 是用户设计输入，不是运行事实。
- `screenshots/` 是实际 React 组件的受控 Playwright 渲染，不是模型成果证明。
- [Evidence](../../evidence/DR-0061-REFERENCE-ALIGNED-CAPABILITIES-EVIDENCE-20260911.md)
  记录测试范围；[视觉 QA](../../../design-qa.md) 记录比较和已知偏差。
- [人机共驾沙盘](../human-agent-copilot-20260911/index.html) 与
  [Demo 3 会议简报](../human-agent-copilot-20260911/report.html) 属于独立设计草案。

源文件检查：在仓库根目录运行
`uv run python docs/reports/demo12-redesign-20260911/verify_report.py`。
这项检查不等于报告网页的实际 DOM 或浏览器视觉验证。
