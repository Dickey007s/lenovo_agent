# 资料库离线浏览器验收

日期：2026-09-11。用户已批准 Playwright 自动化回归；验证新研究库，不访问旧沙盘被拒绝的 URL。

## 范围

`apps/web/e2e/copilot-research-library.spec.ts` 在 Edge 中分别打开本地 `index.html`，
视口 1440×1000 与 390×844；上下文离线，2 项浏览器用例通过。
每项覆盖来源数量、论文筛选、无结果、清除、关键词搜索、来源详情/链接地址、
Escape 关闭与焦点返回、键盘切换、Demo 筛选、核验账本、页面/弹窗无横向溢出。
未点击外部网站，测试期间无 HTTP 请求、无 pageerror 或 console error。

## 抓到的问题

1. 输入框失焦触发重复渲染，移除正在点击的详情/清除按钮。修复后首次点击即响应。
2. 规则流程的副标题落入图标窄列，出现竖排。图标容器跨行、说明置于文字列；补单行高度断言。

脚本选择器曾误把包装 label 当作精确名字，改用真实无障碍树中的 combobox 名称。
这属于测试定位修正，不是削弱来源数量或交互断言。

## 截图

- [桌面来源库](screenshots/library-1440.png)
- [手机来源库](screenshots/library-390.png)
- [桌面详情](screenshots/detail-1440.png)
- [手机详情](screenshots/detail-390.png)
- [桌面规则映射](screenshots/mapping-1440.png)
- [手机规则映射](screenshots/mapping-390.png)
- [桌面账本](screenshots/ledger-1440.png)
- [手机账本](screenshots/ledger-390.png)

这不是外部来源在线可用性复测，也不是 Runtime、框架集成、论文结果复现或目标用户研究。
来源核验在研究阶段通过 web 单独完成；61 项 Node VM 检查另见 `verification.json`。
