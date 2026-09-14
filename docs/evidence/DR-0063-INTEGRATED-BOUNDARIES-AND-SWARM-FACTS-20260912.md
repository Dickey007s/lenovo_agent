# DR-0063：原系统边界解释与协作事实验证

日期：2026-09-12。决策：[DR-0063](../decisions/DR-0063-integrated-copilot-boundaries-and-swarm-facts.md)；场景：[SCENARIO-050](../scenarios/SCENARIO-050-understand-boundaries-and-worker-adoption.md)。

## 本轮实际改动

- 原能力进展页增加只读、来源选择、待决不完整、Worker 用量、局部恢复和业务 Gate 的事实解释。不新增操作或权限。
- 原协作页前置准入、Worker called/output_used、Contribution 采用/拒绝/等待数。
- 准入预算注明“准入时”，不把已保存的 Admission 值写成实时调用余额。
- 修正单主控被归入固定流程的文案；ready 工作包明确尚未派发；确认资料取本批 ready Branch。
- 截图发现依赖横线重合成公共总线的歧义，改为独立曲线；局部失败 Fixture 的 WorkUnit 与 Branch 依赖先作一致性修正。
- 新增纯函数测试和原有产品 Playwright 内的 7 个边界用例。没有把独立研究 HTML 接入产品，没有新建 Demo 选择器。

## 实际验证与限制

| 检查 | 本轮结果 | 能证明的范围 |
| --- | --- | --- |
| `vitest run tests/capability-boundaries.test.ts --maxWorkers=1 --minWorkers=1` | 13 passed，最终复跑 9 ms 测试时间 | 状态解释、复合边界、历史只读、终态/失败、无事实变更 |
| `uv run pytest tests/unit/test_demo2_runtime.py -q` | 22 passed，1.80 秒 | 既有受限 Runtime 准入、来源/采用/局部处理合同的单元回归 |
| 原产品 Playwright 文件 | 最终全量 101 passed，4.1 分钟；首次全量 101 passed，3.8 分钟 | 原工作面、证据、成果、Task、协作状态的受控 API 回归 |
| 新增边界 Playwright | 最终定向与截图 7 passed，20.8 秒 | 2/3 候选、恢复、缺失待决、业务 Gate、单主控、部分采用、曲线、准入预算时间口径及尺寸 |
| `pnpm --dir apps/web exec tsc --noEmit` | 通过 | 类型检查，不替代浏览器或后端验收 |
| `uv run pytest tests/unit/test_reporting_governance.py -q` | 4 passed，0.06 秒 | 既有文档治理检查；不是新增文档全部事实证明 |
| `git diff --check` | 通过，仅既有 CRLF 提示 | 已跟踪 diff 格式检查 |
| 原服务启动 | `scripts/start-demo.ps1` 完成；3000 Web、8010 API，health=ok、checkpoint/task_store=memory | 服务可启动；本轮没有付费 Provider 调用，memory 重启不恢复 |
| Codex 内置浏览器 | 原旧页签 reload 被工具拒绝，目标为历史连接失败页的 `data:text/html` URL；未继续访问该错误页或改用其他方法取其内容 | 不记录为内置浏览器实测通过。下列截图来自用户先前授权的原产品 Playwright 套件，不来自该错误页 |

未执行本轮真实 Provider 办公任务、PostgreSQL 联合恢复、竞品同场对照、真实外部动作或目标用户研究。原系统套件不包括独立研究 HTML 的测试文件，未通过代理/新地址重放被阻止的研究页。

## 红灯与最终收尾

首次新增定向用例为 3 passed / 3 failed：单主控测试误写不存在的 `single` 协议值；等待文案断言与实际标签不同；恢复 Fixture 继承了缺 Resolution 的顶层待决，因此不应期待普通重试说明。修正前两项；把第三项拆为“确实无待决的普通恢复”和“待决资料不完整”两个用例，保留缺失资料不可确认的负向验收。随后 7 项通过，不把测试资料修正说成后端修复。

曲线调整后的全量出现 100 passed / 1 failed：旧 UI 测试把依赖线路径写死为正交 `V/H/V`，与曲线改动冲突；来源/目标 ID、依赖数量和箭头语义断言保留，仅更新几何形状断言。随后边界 + 同级导航定向 8 passed（26.4 秒），最终原产品文件全量 101 passed（4.1 分钟）。预算注明准入时取值后的定向与截图收尾 7 passed（20.8 秒），并加入准入时预算标签断言；四张最终截图已刷新。纯函数 13 项、类型检查、治理 4 项及 scoped diff-check 均通过。六份新研究/简稿/Decision/Scenario/Evidence 的 48 个相对链接存在性检查为零缺失。

## 原组件截图

截图均为真实 React 组件加载受控公共 Snapshot；数字与结果由测试 Fixture 提供，不是本轮真实模型成果。桌面 1440 px，移动 390 px；移动 DAG 在内部横向浏览，页面本身无横向溢出。

- [进展与边界，1440](screenshots/dr-0063-fixture-boundaries-1440.png)
- [进展与边界，390](screenshots/dr-0063-fixture-boundaries-390.png)
- [部分采用协作，1440](screenshots/dr-0063-fixture-swarm-1440.png)
- [部分采用协作，390](screenshots/dr-0063-fixture-swarm-390.png)

研究与指南见 [八案例](../research/DEMO3-BOUNDARY-RULES-AND-CASES-20260912.md)、[蜂群机制](../research/DEMO2-SWARM-MECHANISM-AND-DIFFERENTIATION-20260912.md)。前者为子 Agent 定向研究交付，仅修改该 Markdown；本轮逐项检查其案例和范围，没有宣称进行系统综述或论文实验复现。

## 未闭合项

Q-01 长文本输入截断/覆盖仍开放。UX 规则批准、真实身份/职责、外发授权和 Connector 回执未知后的对账均未实现。曲线改善不等于普通用户一定看得懂依赖图；用户理解和收益必须独立测量。当前交付只可称“原系统首部分边界解释整合与研究案例初稿”，不能称 Demo3 全部完成或蜂群创新已经被证明。
