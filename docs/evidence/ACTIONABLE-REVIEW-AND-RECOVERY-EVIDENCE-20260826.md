# ACTIONABLE-REVIEW-AND-RECOVERY-20260826

## 状态

`Limited Verified`。覆盖结构化问题处置、服务端原文定位、有界 Analyst 修复、部分结果保留、
Branch 恢复和确定性浏览器交互；不升级为语义正确、推荐质量或用户价值证据。
实现提交 [`dbd6469`](https://github.com/Dickey007s/lenovo_agent/commit/dbd6469)，交付见
[PR #37](https://github.com/Dickey007s/lenovo_agent/pull/37)。

## 变更与可观察事实

- Finding 可以分别携带短事实、影响和人工决断包；公共投影会清理内部引用与路径。
- 每个证据卡显示真实文件、服务端位置和逐字摘录；右侧 Preview 是同一安全文件内容，并按
  Anchor 高亮实际位置。
- `accept/decline/defer` 先以 expected version 与幂等键写入 DecisionRecord；关闭待决页记录
  `defer`。接受业务选项后浏览器才创建新的独立只读 Run；旧成果和原文件不变。
- 合法范围内无法唯一定位时，Runtime 最多重试一次；有可采用 Finding 时保留它们，没有时
  暂停受影响 Branch 并给出恢复类型。`ambiguous` 保留真实候选位置，用户确认后只重跑绑定
  Branch；结构输出失败使用同样的有界恢复，不再默认成为死路。
- 安全范围违规、文件完整性失败仍 fail closed；恢复设计没有降低信任边界。

## 证据账本

| Evidence | 结果 | 能证明 | 不能证明 |
| --- | --- | --- | --- |
| 两张 Stakeholder 负例截图 | 已登记 | 旧审查页仍难理解，旧失败页没有下一动作 | 新交互有效 |
| Python 单测 | `35 passed`（Runtime 定向）；`73 passed, 1 skipped`（整库） | 一条 Finding 失败时保留其他 Finding/Branch/Artifact、三种位置状态、版本化决定、预算与安全边界 | 真实模型质量 |
| Ruff / Web lint / build | 通过 | 静态契约与生产构建成立 | 浏览器操作或运行语义 |
| Playwright | `19 passed` | 处置单、文件高亮、接受/暂缓回执、反馈、新 Run、候选消歧、只恢复目标 Branch、重连恢复与历史失败恢复 | 用户理解和业务价值 |
| `dr-0030-actionable-finding-evidence.png` | 已捕获 | 事实/影响/人工动作与真实文件位置在同一视图 | 结论正确 |
| `dr-0030-actionable-finding-review.png` | 已捕获 | 互斥选项、推荐理由、反馈和确认动作可操作 | 推荐合理、文件已修改 |
| `dr-0030-decision-receipt.png` | 已捕获 | 关闭待决页会记录暂缓，Snapshot 回开后可见版本化回执 | 人工决定正确或业务批准完成 |
| `dr-0030-evidence-disambiguation.png` | 已捕获 | 同一逐字片段的多个服务端候选可比较并选择 | 候选位置蕴含 Finding |
| `dr-0030-evidence-disambiguation-action.png` | 已捕获 | 选择后明确显示影响 Branch、已保留内容、重跑范围和无外部动作 | 实际模型结果或用户价值 |
| `dr-0030-source-location-recovery.png` | 已捕获 | “已保留/未采用/未发生”与最小 Branch 恢复入口存在 | 真实 Provider 一定可恢复 |
| `dr-0030-legacy-failure-recovery.png` | 已捕获 | 历史 terminal failure 有明确新 Run 路径 | 旧调用被续跑 |
| live Run `harness:55fda5f836fa4e478948f837e38f653a` | 2 轮、5 次模型调用、4 份文件通过引用核对、最终 bounded stop | 真实 Provider 触发 Branch 等待、原文定位拒绝、自动重试、采用和预算停止 | Finding 语义正确或生产稳定 |

脱敏运行事实见
[`dr-0030-actionable-review-live-run.json`](manifests/dr-0030-actionable-review-live-run.json)。

新交互截图 SHA-256：`dr-0030-evidence-disambiguation.png` 为
`F3CF8418CA34DF40387BC0DFEEE393073FBD51857AB50FA496468D76B6B33CE1`；
`dr-0030-evidence-disambiguation-action.png` 为
`9F664BC957E5848CFFD7973FEB92F213A073BC8181DC2CE08A6A5D933DD8C154`；
`dr-0030-decision-receipt.png` 为
`F7D422892607C050AD0839D6A0C370623A20C57B83027AB50DC10927E2E7C8CE`。

## 事实边界

- Evidence Anchor 的唯一匹配只证明片段存在于本轮批准内容，不证明片段蕴含 Finding。
- `analysis_partial_adopted` 证明服务端只保留可定位 Finding，不公开被拒候选原文。
- `exact/ambiguous/unavailable` 只证明本轮安全 Preview 的位置匹配结果；`stale/rejected` 是
  预留契约状态，当前 Resolver 不会产生。
- “Agent 推荐”是模型候选，不是策略引擎、审批人或确定性最优决策。
- DecisionRecord 证明人的 accept/decline/defer 已被服务端接收，不证明审批正确。接受业务
  选项才创建新 Run；当前不会写入 XLSX/DOCX、提交工单或调用外部系统。
- 当前本地 live Run 使用 memory 状态，API 重启后不能作为 Durable State 查询。
