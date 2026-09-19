# 验证记录

日期：2026-09-11。范围：本目录的离线设计包。所有沙盘操作都是模拟意向，不是 Runtime Evidence。

## 实际执行

- `node generate-icons.cjs`：从仓库现有 `@tabler/icons-react 3.46.0` 机械生成 28 个本地图标。第一次相对路径层级错误，修正后成功；未安装依赖。
- `node --check app.js`、`node --check cases.js`、`node --check icons.js`：全部通过。
- `node verify.cjs`：初次 36 项源级检查通过；增加文本空白与 PostCSS 语法检查后 **38 项通过**。该脚本只用 Node VM 与轻量占位 document 检查源码逻辑和生成的标记字符串，不是浏览器 DOM、Playwright 或页面渲染。
- 参考图复制后校验：`1,561,536` bytes，SHA-256 与 [来源台账](sources.md) 一致。
- 增加机器清单链接时，首次检查发现清单尚未生成，未报通过；随后改为先写 `running` 清单，全部检查通过后才更新为 `passed`。最终完整复跑 38 项通过。

## 浏览器边界

本轮按 Browser skill 初始化内置浏览器，直接打开本目录 `file://` URL 时被浏览器 URL 安全策略拒绝；工具明确禁止通过其他协议、浏览器或间接执行绕过该拒绝。因此没有改用临时 localhost 服务器、CDP 或独立 Playwright 绕过。

尚未验证：桌面/390px 真实浏览器布局、截图、实际 radio/select/keyboard 行为、原生 dialog 焦点、浏览器下载、CSP 在各浏览器的真实效果、页面级横向溢出。CSS 包含响应式规则，但不能据此声称视觉已验收。

本包仍可由用户在本机直接打开两个 HTML；没有启动服务器或公网部署。

## 不在本轮验证范围

- 真实 Provider、Planner/Analyst 质量、预算消耗、服务端 DecisionRecord、Task/Run/Worker 或 PostgreSQL 恢复。
- 真实业务批准、目标用户理解/错批率、完整行业技术回溯、Connector 与任何外部动作。
- 仓库全量 Python/Playwright 工程门。本包不修改运行时代码，历史测试数字没有重新计入本轮。

## 最终检查结果

**38 项源级检查通过**，机器可读清单见 [source-check-results.json](source-check-results.json)。CSS 使用仓库已有 PostCSS 成功解析；新文本逐文件无末尾空白或冲突标记。

初次 36 项覆盖：8 案例完整性；证据/权限独立；候选无预选；无选择不能确认；重复提交抑制；本地意向标签；409/断网/过期不假绿且可退出；过期清空选择；刷新/重置；初始业务口径门；人工接管不执行；预算续办不伪造 Run；Agent 自有恢复不强迫输入；Worker 候选；成果/业务分离；筛选/空态；转义；无网络 API；两页 CSP 声明；离线资源；HTML/Markdown 本地链接；Tabler 图标；原图大小。

`git diff --check -- docs/reports/human-agent-copilot-20260911` 返回成功，但目录为新文件时该命令不覆盖未跟踪内容，因此另在源级脚本中逐一检查新文本的末尾空白与冲突标记。任何“通过”只限明确列出的范围，不作为视觉或后端验收。
