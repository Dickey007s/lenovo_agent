# DR-0001：场景、来源、前台与后端事实硬门槛

| 字段 | 内容 |
| --- | --- |
| Decision ID | `DR-0001` |
| Owner | Office Agent 项目组 |
| Date | 2026-08-10 |
| Status | `Verified` |

## 用户场景与问题

项目组在每次架构决策、功能推进、Demo 和阶段汇报中，需要同时回答后台技术如何改变用户体验，以及设计判断从何而来。此前仓库虽已描述目标架构和静态交互，但没有仓库级门槛强制每个决策留下场景、来源、前台影响和后端事实映射，容易出现后台方案先行、前台后补、来源无法追溯或静态页面冒充运行事实。

完成条件是：后续 Agent 和成员进入仓库即可看到同一套强制规则、模板和状态门槛；缺少任一必填项的内容不能进入完成结论。

关键异常包括：只有技术描述、只有界面稿、只有来源列表、UI 状态无服务端依据、静态原型被描述为已实现、测试未运行却写成通过。

## 来源与依据

- `USER-FEEDBACK-20260810-01`：用户在 2026-08-10 的当前 Codex 任务中明确要求把三项要求“写死”：每次汇报、决策和推进都必须考虑前台展示与交互；每个 UI 状态必须对应后端事实；场景与来源必须留痕。完整登记见 [`SOURCE_REGISTER.md`](SOURCE_REGISTER.md)。
- 仓库现状：`docs/TARGET_ARCHITECTURE.md` 已有前后端对齐原则，`docs/prototypes/README.md` 明确静态原型不证明 Runtime 已实现，但此前没有统一完成门槛和必填记录模板。

## 决策与备选

采用仓库级强制治理，而不是仅在一次回复、会议纪要或汇报模板中添加提醒：

1. `AGENTS.md` 将规则列为后续 Agent 的硬门槛；
2. `DECISION_AND_REPORTING_GOVERNANCE.md` 定义状态、必填字段、三张记录表和完成门槛；
3. `PRESENTATION_BRIEF.md` 禁止不完整内容进入汇报结论；
4. `TARGET_ARCHITECTURE.md` 要求架构推进同步维护留痕；
5. 自动化测试防止关键入口和强制字段被无意删除。

未采用“仅增加一段提示”，因为它无法约束 PR、Demo、实现状态和后续 Agent。未采用“只建来源库”，因为来源本身不能建立技术、后端状态与用户交互之间的映射。

## 后端事实

这是一项项目治理决策，不新增 Runtime API 或业务状态。当前权威事实为：

- 规则正文：`docs/DECISION_AND_REPORTING_GOVERNANCE.md`；
- Agent 入口：`AGENTS.md`；
- 汇报入口：`docs/PRESENTATION_BRIEF.md`；
- 架构入口：`docs/TARGET_ARCHITECTURE.md`；
- 防回退验证：`tests/unit/test_reporting_governance.py`。

未来具体 UI 状态仍必须映射到实际服务端实体、字段、版本、`Snapshot` 或有序 SSE 事件；本决策不能替代具体功能的协议记录。

## 前台输出

后续汇报和评审中，每个决策单元必须让读者直接看到：用户场景、来源依据、技术决策、服务端事实、前台状态与动作、验证结果和限制。失败、等待、冲突和恢复必须进入交互说明。

默认隐藏原始 Prompt、思维链、Worker 内部对话、密钥、底层堆栈和无决策价值的日志；展示与用户判断相关的目标、状态、来源、版本、影响范围、预算、冲突、验证结果、待确认动作和 Trace 摘要。

## 验证与边界

- `uv run pytest -q`：31 passed；
- `uv run ruff check .`：通过；
- `pnpm --dir apps/web lint`：通过；
- `pnpm --dir apps/web build`：通过；
- `git diff --check`：通过。

`Verified` 只表示治理规则、入口、首条来源记录和防回退测试已经落地，不表示未来所有决策天然合规。每个后续决策仍需独立建立记录并通过门槛。
