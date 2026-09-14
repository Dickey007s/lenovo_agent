# Demo 3 人机共驾设计包

日期：2026-09-11。设计状态：`Draft`。当前产品事实以根 README、现行源码和正式 Evidence 为准。

## 打开方式

- [交互沙盘](index.html)：8 案例、原文选择、处理方式、409/断网/来源过期演练、规则矩阵、案例筛选和评审检查单。
- [会议简报](report.html)：给下次会议使用的独立可视化说明，支持浏览器打印。
- [人机共驾指导手册](guide.md)：规则、责任、场景、交互模式、验收和分阶段实施。
- [来源台账](sources.md)：用户参考、本地源码和三项官方资料，以及不能推出的结论。
- [验证记录](verification.md)：本次实际执行的检查及未验证范围。

两个 HTML 都可直接打开，不需要服务器、构建工具、API 密钥或联网。`icons.js` 使用仓库已安装的 Tabler 图标生成；图标与参考图均在本目录，保留离线可打开性。其再生成脚本为 `generate-icons.cjs`，只有再生成时才需要仓库前端依赖。

## 边界

本目录是与当前产品隔离的设计与汇报附件，不是 `/agent-capabilities` 的替代入口，不新增产品 Scenario/Demo 选择器。案例文本、行号、状态与文件名均为虚构设计样例；引用的用户参考图也不是本轮实现证据。

沙盘按钮只记录当前页面的本地意向，刷新会重置。导出的 JSON 强制携带 `simulated=true`、`runtime_connected=false`、`external_action=none` 和 `model_calls=0`。没有网络请求、真实 DecisionRecord、Task/Run、预算消费或业务动作。

本轮没有修改 Runtime、公开 API 或数据库。R0–R3 是候选设计分类，不是当前通用风险引擎。外部 Permit、Connector、双人审批与生产执行仍未实现。官方资料只构成本轮定向设计来源，不代表已完成“三个 Demo 完成后”的完整行业技术回溯。

## 文件

`cases.js` 保存结构化案例；`app.js` 负责纯本地演练；`styles.css` 为两份网页提供响应式样式。`generate-icons.cjs` 仅从已有 Tabler 包机械生成图标，未安装新依赖。`reference-evidence.png` 为用户参考图 5 的原样副本。

设计对应的 Decision/Scenario/Source/UI fact 候选记录保存在 [guide.md](guide.md) 与 [sources.md](sources.md)，尚未授予正式编号或写入共享 living docs；由主线集成时按统一治理登记。
