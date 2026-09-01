# DR-0058：Agent 能力页四层渐进披露工程 Evidence

- 日期：2026-09-01
- 状态：`Limited Verified`
- 决策：[`DR-0058`](../decisions/DR-0058-progressive-disclosure-agent-capability-page.md)
- 场景：[`SCENARIO-045`](../scenarios/SCENARIO-045-progressive-agent-capability-review.md)
- 测试合同：[`AGENT-CAPABILITY-PROGRESSIVE-DISCLOSURE-GATES-20260901`](../testing/AGENT-CAPABILITY-PROGRESSIVE-DISCLOSURE-GATES-20260901.md)
- 实现：Luna 分支 `656edfd` 至 `4c1ce50`；`master` 等价集成 `2673fe4` 至 `f0a281c`

## 1. 本轮证明了什么

`/agent-capabilities` 仍读取同一个 selected Task/Run/Snapshot，但不再默认同时展开完整
Agent Control Loop 与 Adaptive Swarm 工作台：

1. 默认“执行进展”只显示当前状态、主要待办、Branch 完成/等待摘要和当前成果版本；
2. “查看完整执行记录”才显示既有 LoopView、Task lineage、Round/Branch、控制和历史；
3. “协作方式”先显示服务端实际 route、WorkUnit/Contribution 与成果摘要，完整 Worker
   工作台默认折叠；
4. 证据审查页把 Finding/Resolution 翻译为“系统发现、影响、你要做什么、会保留、不会
   做”，但确认请求仍携带服务端要求的版本、幂等、DecisionRequest 和来源修订字段。

能力 tab 支持 `aria-selected/aria-controls/aria-labelledby`、roving `tabindex` 和左右方向键。
`#adaptive-swarm` 直接刷新仍落在协作方式；历史 Run 仍只读且不连接历史 SSE。

## 2. 工程门

| 门 | 结果 | 能证明 | 不能证明 |
| --- | --- | --- | --- |
| 四层与恢复定向 Playwright | `7 passed` | tab、disclosure、Fixed 反例、历史 Run、真实审查入口和新恢复文案在 Fixture 中成立 | Provider 输出、业务正确性或用户理解 |
| 最终全量 Playwright | `77 passed` | Workspace、预览、现有 15 个场景、Loop/Swarm 与移动端回归未被本轮改坏 | 浏览器和网络的生产稳定性 |
| 截图捕获定向门 | `4 passed` | 下列五张图片来自最终代码的固定公共 Fixture，不是概念图 | 真实 Provider 或真实用户运行 |
| Web lint / TypeScript | 通过 | TypeScript 静态门通过 | 运行期业务语义 |
| Web production build | 通过 | Next.js `/` 与 `/agent-capabilities` 可生产构建 | 部署、SLA 或线上性能 |
| 全量 Python | `418 passed, 23 skipped`，`277.87s` | UI 集成后现有 Runtime/合同 Python 回归保持 | 被 skip 的 PostgreSQL/环境集成 |
| Ruff | `All checks passed!` | Python 静态门保持 | 前台体验 |
| 汇报治理 | `4 passed` | 本轮 Decision/Scenario/Source/Evidence 关系满足现有治理测试 | 文档结论天然正确 |
| `git diff --check` 与变更 Markdown 相对链接 | 通过 | 无 whitespace error，本轮相对文件链接存在 | 外部网页未来可用性 |

全量浏览器第一次在 `f6bd73d` 暴露两个真实回归：页面标题为“让 Agent 重新查找结论
依据”，操作按钮为“让 Agent 重新查找依据”，导致两个可访问名称定位失败，结果为
`75 passed, 2 failed`。`9b2b85e` 统一标题，`4c1ce50` 保留旧 Run 新建任务的不同动作语义；
随后相同全量门为 `77 passed`。失败记录没有被删除或冒充成功。

## 3. 运行截图

| 截图 | 尺寸 / bytes / SHA-256 | 被测事实 |
| --- | --- | --- |
| [默认任务进展](screenshots/dr-0058-agent-capabilities-progress.png) | `1440 x 1100` / `59682` / `49AF7A8866962A5229B8AAC064CD3E45EC5D6D45C96B927D56F85B8D1C7B32D8` | 首屏只有执行摘要，完整执行记录和协作方式未展开 |
| [完整执行记录](screenshots/dr-0058-agent-capabilities-execution-record.png) | `1440 x 1100` / `100878` / `D413524DC2DEF45F983DC06B34C7F0A807FE47B080C5835E6514D669711775E4` | disclosure 打开后可见 Task lineage 与服务端拓扑准入 |
| [协作方式](screenshots/dr-0058-agent-capabilities-collaboration.png) | `1440 x 1100` / `107594` / `6EDAAD36D33ACF95A8A3187BD02ECA63A20E1E93233B79153D35383329955A62` | 同一 Run 的 Adaptive route、五个 WorkUnit、三根分支和真实来源投影 |
| [协作方式 390 px](screenshots/dr-0058-agent-capabilities-collaboration-390.png) | `390 x 1866` / `110185` / `948082F4438A9E1E2861D7BF6BA786667BB2F85306AB9F2F1A5979323873D010` | 标签、摘要与工作包在移动宽度无页面横向溢出 |
| [确认结论依据](screenshots/dr-0058-agent-capabilities-evidence-review.png) | `1440 x 1100` / `132685` / `FC31B09A1F81D676FB0EA8714ACDACCB49FBFCFEF0915B5264E8AD810B6D80E8` | 五段用户解释、安全 Preview、真实定位和结果保留边界同屏 |

截图中的任务内容、状态、来源数量和工作包来自确定性 Fixture，只证明 UI 对公共 Snapshot
字段的映射。四张 `docs/evidence/assets/dr-0058-*-concept.png` 是 GPT Image 2 设计参考，未
列入运行截图，也不参与工程结论。

## 4. 用户流程与后端事实对照

| 用户动作 | 前台反馈 | 后端事实 |
| --- | --- | --- |
| 打开能力页 | 默认进入执行进展 | 同一 selected Run Snapshot；没有另起 Runtime |
| 查看待办 | 首个可处置项与剩余数量；`deferred` 显示“已暂缓，仍可处理” | open/deferred DecisionRequest 的稳定投影；不是 Gap 总数 |
| 展开完整记录 | 显示 Round、Branch、历史成果和控制 | 复用既有 LoopView；控制仍受 Run version 与幂等约束 |
| 切换协作方式 | 显示实际 route 与采用摘要 | `topology_admission/work_units/worker_runs/contributions` |
| 展开 Worker 记录 | 显示批准来源、依赖、返回与采用 | Worker returned 与 Contribution adopted 继续分开 |
| 核对原文 | 选择候选后才能确认 | 服务端 packet、safe Preview、candidate membership 与 source revision |

## 5. 剩余边界

- 本轮只改变前台信息顺序与文案，没有新增 API、Planner、Worker、Tool 或外部动作；
- Adaptive Worker 仍是单 API 进程内、每波最多三个的受限只读实现；
- ArtifactVersion 仍可能只是逻辑成果，不自动代表 DOCX/XLSX 写回；
- Evidence Anchor 证明位置和成员关系，不证明结论语义、穷举或数值正确；
- 本轮没有真实 Provider、PostgreSQL 复跑、目标用户走查、竞品同场测试或业务收益验证；
- 07-16 Demo 2 智能工作驾驶舱仍未实现，能力页不是驾驶舱替代品；
- 自动化与截图不能支持“更容易理解、更高效、更可信”这类体验结论，相关判断保持 `Draft`。
