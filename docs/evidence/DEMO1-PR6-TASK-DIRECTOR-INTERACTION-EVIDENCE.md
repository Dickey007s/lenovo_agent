# Demo 1 PR 6 Task Director 交互证据

| 字段 | 内容 |
| --- | --- |
| Evidence ID | `TASK-DIRECTOR-INTERACTION-DEMO1-PR6-20260811` |
| Date | 2026-08-11 |
| Status | `Verified` |
| Baseline commit | `a47cb28` |
| Decision | [`DR-0005`](../decisions/DR-0005-task-director-interaction.md) |
| Scope | 固定客户 A Fixture 的 Task Director、Decision Inbox、Agent 切换、历史版本防误读与响应式布局 |

> 本记录冻结 `a47cb28` 的原 PR 6 工程基线，`Verified` 仅指当时固定 Fixture 的投影、控制和被测布局，不再描述当前源码。2026-08-11 的 Stakeholder 试用反馈指出产品用途仍不清楚，`DR-0005` 已重新进入 `Draft`；当前首屏、下一步、决策后果、完成成果、恢复和移动端的工程代理验收见 [`DEMO1-PR6-USABILITY-COMPREHENSION-AUDIT-20260811.md`](DEMO1-PR6-USABILITY-COMPREHENSION-AUDIT-20260811.md)。

## 1. 参考与可追溯性

Stakeholder 选择的第二个交互方向已作为不可变参考保存：

| 资产 | 尺寸 | SHA-256 | 能支持什么 | 不能支持什么 |
| --- | --- | --- | --- | --- |
| [`assets/dr-0005-task-director-option2-reference.png`](assets/dr-0005-task-director-option2-reference.png) | `1487 x 1058` | `BB8B6F16C65FF0FBF0F5F3838D3BB7E8ED9CD249B07578A7B0B9970E12794E40` | 选中布局、密度、Decision Inbox 位置和状态色方向 | 不是运行截图；不证明实现一致、可用性或任何后台事实 |

方向选择原文见 [`USER-FEEDBACK-20260811-03`](../sources/USER-FEEDBACK-20260811-03-task-director.md)；当前“有点看不懂这个是要做什么”的问题反馈见 [`USER-FEEDBACK-20260811-04`](../sources/USER-FEEDBACK-20260811-04-usability-comprehension.md)。后者是 Stakeholder feedback，不是用户研究。

## 2. 源码实现事实

以下内容是 `a47cb28` 基线经当时源码、真实本地浏览器和自动化回归交叉检查的历史事实：

| 前台能力 | 服务端或客户端事实 | 实现位置 | 当前边界 |
| --- | --- | --- | --- |
| Task Director 头部、事实摘要、阶段与 Branch 泳道 | `TaskSnapshot.contract/status/phase/version/budget/branches/artifact_versions/verification_reports/conflicts/last_commit` | `apps/web/app/task-director-studio.tsx`、`apps/web/app/page.tsx` | 阶段颜色与布局是 UI 表达；没有新增任务进度事实 |
| Decision Inbox | open `ConflictRecord`、Branch 状态、当前 Snapshot version；`resolve_evidence` / branch control / `steer` | `apps/web/app/task-director-studio.tsx` | 补证按钮只准备文字；Steer 提交后仍为待后续循环应用 |
| Decision / Agent 模式切换 | 客户端右侧模式；既有 Conversation 与 Action Gate | `apps/web/app/page.tsx` | 切换模式不代表 Task 或 Conversation 状态变化 |
| 共享工件历史防误读 | Branch `artifact_heads`、ArtifactVersion lineage；客户端 `follow_head/pinned_history` | `apps/web/app/task-artifact-workspace.tsx`、`apps/web/app/page.tsx` | 人工编辑创建新 ArtifactVersion 仍未实现 |
| 移动端决策入口 | open Conflict 数量与客户端锚点滚动 | `apps/web/app/task-director-studio.tsx`、`apps/web/app/styles.css` | 被测 `390 x 844` CSS 视口无页面横向溢出，关键可见 Task 操作不小于 44px；不代表所有设备 |
| Snapshot 单调应用 | 当前 Snapshot 的 `version/last_event_sequence` 与客户端已观察 SSE 序号下限 | `apps/web/app/page.tsx` | 旧 GET 不覆盖较新 Snapshot；Snapshot 未覆盖已观察 SSE 时保持重新对账，不伪标已同步 |

本轮没有修改 Task API、Pydantic Task 协议、Risk/Policy/Permit 或 Simulator。业务完成、风险和执行成功仍不能由前端推断。

## 3. 运行验证

| 验证项 | 成功标准 | 当前结果 |
| --- | --- | --- |
| 固定主路径与兼容 E2E | create/start/open conflict/resolve/Commit 继续通过；既有恢复与可重复演示不回退 | 原基线 `pnpm --dir apps/web test:e2e`：`6 passed (34.5s)` |
| Task Director 专用封口 | Decision/Agent 切换、移动决策跳转、Pause/Resume、非法 resolution 禁用、`409` 可见反馈、resolve、Commit、follow-head 与 pinned-history | 原基线专用 `Task Director keeps decisions, controls, errors, and versions understandable` 用例：`1 passed (21.6s)`；该名称是历史测试名，不是用户理解结论 |
| Snapshot 乱序 | 延迟旧 GET 不能回滚 mutation 后 v2；已接收 SSE sequence 成为应用与 `synced` 的下限 | `a late older task GET cannot roll back a newer mutation snapshot` 与 `task snapshot ordering uses the received SSE sequence as its floor` 两项回归通过 |
| 历史版本路径 | 固定查看旧版本时出现历史 banner；mutation 后默认选择新的 Branch head | 专用用例通过；历史截图显示 v1 candidate 与当前 Snapshot/新 head 的明确区分 |
| 桌面视觉 | `1487 x 1058` 中核心编排、冲突和主决策可扫描，无文字或持久控件重叠 | 冲突、Commit、历史三种状态截图与全图/局部对照已复审 |
| 移动视觉 | `390 x 844` 被测视口无页面横向 overflow；阻塞摘要能到达 Decision Inbox；关键操作目标满足项目基线 | 浏览器 DOM 测量与 `390 x 2544` full-page 截图通过 |
| 事实一致性 | 标题、状态、阶段、分支、head、验证、冲突、Commit 与 API Snapshot 一致；同步文案仅表达客户端事实 | E2E 对照 Snapshot 与 DOM 通过；不扩展到未测错误与多实例状态 |
| Python 与治理 | 完整 Python 回归包含治理测试 | `58 passed, 1 skipped (3.46s)`；skip 为未显式配置的 opt-in PostgreSQL 维护库路径 |
| 静态与生产构建 | Ruff、TypeScript lint 和 Next.js build 无错误 | `uv run ruff check .` passed；`pnpm --dir apps/web lint` passed；`pnpm --dir apps/web build` passed |
| Design QA | 根目录 `design-qa.md` 最终结果为 `passed`，P0/P1/P2 全部关闭 | [`design-qa.md`](../../design-qa.md) `final result: passed`；两轮复审后无可执行 P0/P1/P2 |

## 4. 截图与视觉对照

| 状态或对照 | 文件 | 像素尺寸 | SHA-256 |
| --- | --- | --- | --- |
| 冲突态桌面 | [`dr-0005-task-director-conflict-desktop.png`](screenshots/dr-0005-task-director-conflict-desktop.png) | `1487 x 1058` | `1B9830FB580795584FDF237D31229E904FB0ECFF0D265550E5719B35B7EFA2D3` |
| Commit 桌面 | [`dr-0005-task-director-committed-desktop.png`](screenshots/dr-0005-task-director-committed-desktop.png) | `1487 x 1058` | `D0059017E3BE7B277E4BB0E9B86E3DC965985952CD4FDB731D4C6EA2A17DBCC5` |
| 历史版本桌面 | [`dr-0005-task-director-history-desktop.png`](screenshots/dr-0005-task-director-history-desktop.png) | `1487 x 1058` | `B3F4128735B121895914B74BF8F6AF6D7F3509AB7BE50C8C2F0CB24C7120F0AE` |
| 移动端决策 full-page | [`dr-0005-task-director-decision-mobile.png`](screenshots/dr-0005-task-director-decision-mobile.png) | `390 x 2544` | `2785B1220CD621EF42BF6565D469149D27BB3376FBCE2F7567AF1F41EE85CEE2` |
| 参考与实现全图对照 | [`dr-0005-reference-implementation-comparison.png`](screenshots/dr-0005-reference-implementation-comparison.png) | `2974 x 1058` | `49DE24478445150DE5E6CAE8CC85FD24EC24E548A9106A2363C9980423DDCF79` |
| Decision Inbox 局部对照 | [`dr-0005-decision-focused-comparison.png`](screenshots/dr-0005-decision-focused-comparison.png) | `644 x 820` | `1FFD852E95B854A7D114A523651E9FF61FC9A2C54456B52097547BA917CEFB93` |
| 编排画布局部对照 | [`dr-0005-orchestration-focused-comparison.png`](screenshots/dr-0005-orchestration-focused-comparison.png) | `2080 x 650` | `C646EF9B1E5D41A027A5E0A9FB5C0DE13E87425BDC743829C3EAFDA534F6DD2A` |

复审先发现并关闭了历史 v1 与当前已解决状态混淆、移动阶段轨隐藏 Verify/Commit、移动决策区裁切、原始协议词和 hash 进入主要业务界面等 P1/P2。最终全图、编排、Decision Inbox、移动和历史版本对照均无剩余 P0/P1/P2。完整比较过程、刻意不复制的虚假恢复/时间/进度文案和残余边界见 [`design-qa.md`](../../design-qa.md)。

## 5. 事实、假设与边界

- 本轮已证明：固定 Fixture 下，新页面读取现有 Snapshot 并完成被测既有控制；历史版本有清晰状态；Snapshot 按 version、sequence 和已观察 SSE 下限单调应用；被测桌面/移动视口没有页面级横向溢出或阻塞主路径的 P0/P1/P2 视觉问题。
- 本轮不能证明：Task 在后台异步持续执行、真实 Connector 可用、响应丢失已恢复、多实例事件无缺口、人工接管可编辑工件、用户理解或效率已经提高。
- 选中参考图中的时间、恢复语句、进度数字和按钮集合不是协议；实现必须以实际 Snapshot 和现有 Control 能力为准。
- 目标用户理解度、决策时间、误读率和接管成功率需要独立可用性研究，不能用视觉相似度或 E2E 代替。
- 工程 E2E 可以证明脚本找到控件并触发预期服务端路径，但不能证明真实用户理解控件用途、预判决定后果或知道任务何时完成。后续必须进行至少 5 名接近目标角色参与者的无引导形成性任务测试；该测试当前未运行。
