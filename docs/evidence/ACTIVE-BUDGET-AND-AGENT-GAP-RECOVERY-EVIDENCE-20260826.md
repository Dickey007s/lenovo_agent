# ACTIVE-BUDGET-AND-AGENT-GAP-RECOVERY-20260826

## 状态

`Limited Verified`。覆盖 active deadline、十倍默认时间预算、精确停止原因、Agent 自有 Gap
处置、Branch 级恢复和确定性浏览器路径；不升级为模型质量、语义正确或用户价值证据。

## 负例与根因

| Evidence | 观察 | 能证明 | 不能证明 |
| --- | --- | --- | --- |
| `user-feedback-20260826-premature-budget-stop.png` | 第 2 轮在 240 秒边界停止，6 条分支未完成 | 旧界面和预算行为触发 Stakeholder 反馈 | 扩大预算必然完成任务 |
| `user-feedback-20260826-vague-evidence-gap.png` | 只有“缺少证据”、候选文件和整表预览 | 旧页面没有说明 Agent 失败类型和直接动作 | 文件内容是否真的缺失 |
| 修复前 Runtime 源码审计 | elapsed 从 Run 建立持续按墙钟计算，waiting/pause 未冻结 | 人工等待会消耗旧 deadline | 所有历史停止都只由等待造成 |

负例截图 SHA-256：

- `user-feedback-20260826-premature-budget-stop.png`：
  `394426B87359E9FA08DDEAAC15E06EC7F6A12C4023F0EE036198CC8B6B2550A4`
- `user-feedback-20260826-vague-evidence-gap.png`：
  `87D8D8B1877B566B65C7A8525F9BE6ACCF81ABC5726DE239B42AF54C602987F6`

## 实现事实

- `AgentControlLoopOptions.deadline_seconds` 默认 `1200`，范围 `20..3000`；冻结合同和预算使用
  相同上限。
- Runtime 分离 `active_elapsed_base_ms` 与 `active_since_perf`。进入人工等待、暂停和终态时冻结；
  合法恢复时重启 active 区间。
- 模型调用与 active deadline 各自生成中文 `budget.stop_reason`。
- Gap 处置上下文由 `recovery_kind`、Branch、Gap、模型调用回执和 terminal 状态组成。
- waiting Branch 可在反馈留空时直接 resume；有反馈时先 steer 再 resume。terminal Run 只创建
  新 Run，不发送旧 Run control。
- 无 Anchor 的候选文件仍可安全预览，但明确不高亮、不要求用户改源文件。

## 验证账本

| 验证 | 结果 | 能证明 | 不能证明 |
| --- | --- | --- | --- |
| Python 完整 pytest | `75 passed, 1 skipped`；Runtime 定向 `37 passed` | 默认/上限、waiting 不消耗 active elapsed、既有预算、Branch 与其他后端路径未回归 | Provider 长任务质量 |
| Ruff 完整检查 | 通过 | Python 修改满足静态规则 | 运行交互 |
| Web lint / production build | 通过 | TypeScript、lint 与 Next.js 生产构建成立 | 浏览器行为 |
| Playwright 完整 Harness | `20 passed` | waiting Gap 可留空只重试，terminal Gap 创建新 Run，其余文件管理器/证据/控制路径未回归 | 真实用户理解 |
| `dr-0031-actionable-gap-recovery.png` | 已捕获 | 首屏显示 Agent 自有缺口、保留项、可选线索和只重试 Branch 主动作 | 下一轮一定成功 |
| `dr-0031-terminal-gap-recovery.png` | 已捕获 | terminal 状态显示创建新 Run，而非伪 resume | 新 Run 沿用旧调用 |

新界面截图 SHA-256：

- `dr-0031-actionable-gap-recovery.png`：
  `287324BD34EF7CE2F041BCB218C86981BBBCBD5B9FA544ABD711F34C0F14C758`
- `dr-0031-terminal-gap-recovery.png`：
  `B8C93DFE0456318A56DE9F27AF356EDE9F46A2CABBA9360F217B77608DEBAE48`

## 待交付补证

- 实现提交、PR 与远端 CI 结果将在推送后回填。
- 应运行一次真实 Provider 路径，验证人工等待后恢复不会因为 wall-clock 立即到达 deadline；
  该运行仍只能证明控制路径，不证明 Finding 正确。

## 事实边界

- active deadline 只在调用之间阻止新调用，不会硬取消在途 HTTP 请求。
- 扩大时间预算不扩大每轮 1 到 8 份文件、最大轮次或调用预算，也不授权工具或外部动作。
- 候选文件只证明 Agent 本轮尝试范围。无 Anchor 时没有可指给用户的确定行，不得伪造定位。
- “问题在 Agent 的交付”是结构/定位/覆盖门的责任归属，不证明 Provider、模型或源文件永久有错。
- 自动化和截图不是用户研究；新交互的理解速度、信任和业务价值仍是 `Draft`。
