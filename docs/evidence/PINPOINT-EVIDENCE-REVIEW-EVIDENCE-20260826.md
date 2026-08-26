# PINPOINT-EVIDENCE-REVIEW-20260826

## 状态

`Limited Verified`，覆盖服务端 Evidence Anchor 解析、公共 Snapshot 映射、确定性浏览器交互
和一次真实 Provider 纵向运行；不升级为语义正确或用户价值证据。

## 变更与可观察事实

- `HarnessFinding` 接收模型逐字引用候选；Runtime 只在本轮 Analyst 实际收到的安全内容中
  唯一匹配，生成公开 `AgentControlLoopEvidenceAnchor`，随后清除模型候选。
- Anchor 随 Round Result 和 append-only 逻辑 ArtifactVersion 保存；恢复历史成果时保留 Anchor。
- 新 Finding 没有至少一处已解析 Anchor 时，服务端不采用分析结果。
- 首次定位失败时，Runtime 在同一预算内最多允许一次新的 Analyst 调用，并把拒绝与重试写入
  有序 Trace；第二次仍失败则 fail closed。
- 问题审查页新增编号证据链、证据角色、文件与位置提示、短摘录、跨文件跳转、文本行/表格行
  高亮和无 Anchor 的诚实退化状态。

## 证据账本

| Evidence | 结果 | 能证明 | 不能证明 |
| --- | --- | --- | --- |
| 用户负例截图 `dr-0029-before-unlocated-evidence.png` | 已登记 | 旧审查页只到文件级，用户仍需手工查找 | 新交互有效 |
| `uv run pytest -q` | `67 passed, 1 skipped` | 唯一文本/表格定位、歧义拒绝、有界 Analyst 修复、Anchor 传播及既有 Runtime 回归 | 模型语义正确 |
| `uv run ruff check .` | 通过 | Python 静态规范 | 运行时行为 |
| `pnpm --dir apps/web lint` / `build` | 通过 | TypeScript 与生产构建 | 浏览器交互正确 |
| Playwright | `13 passed` | 证据角色、点击切换、跨文件高亮、移动路径和既有工作流 | 真实 Provider 输出或用户价值 |
| [PR #35](https://github.com/Dickey007s/lenovo_agent/pull/35) / [PostgreSQL job](https://github.com/Dickey007s/lenovo_agent/actions/runs/32944740436/job/98102969157) | 实现 `0c2af7e`、merge `98b8add`、远端门通过 | 变更已进入统一 `master`，既有 PostgreSQL restart gate 未回归 | 本地 memory Run 获得数据库持久化 |
| `dr-0029-pinpoint-evidence-review.png` | 已捕获 | 固定 Snapshot 下“设计预期”证据的视觉状态 | 真实模型调用、可用性提升 |
| `dr-0029-observed-source-highlight.png` | 已捕获 | 点击“实际观测”后跨文件定位与高亮 | 用户理解或语义成立 |
| live `deepseek-v4-pro` Run | 完成 2 轮、4 次调用、4 份文件、23 处 Anchor | Provider 返回逐字候选并被服务端定位采用，人工确认一条 Branch 后继续完成 | Finding 正确、生产稳定或普遍质量 |
| live 负例 Run | 修复前第 1 轮、2 次调用后，因短引用不能唯一定位而失败 | fail-closed 生效，并直接促成有界修复设计 | 修复一定成功；原 Snapshot 已随 memory 重启丢失 |

脱敏运行事实见
[`dr-0029-pinpoint-evidence-live-run.json`](manifests/dr-0029-pinpoint-evidence-live-run.json)。

## 事实边界

- 文本行号属于安全提取/有界预览；PDF/DOCX 不是原生版面坐标。
- 表格 Anchor 当前到行，未验证单元格语义、公式或计算。
- 原文唯一匹配只证明该片段存在于批准内容，不证明它支持 Finding。
- 截图与自动化不是用户研究；“更清晰”仍为待验证设计假设。
- 当前演示使用进程内存状态；完成 Run 在 API 重启后不可恢复，manifest 是本次运行的脱敏
  证据记录，不是可查询的 Durable State。
