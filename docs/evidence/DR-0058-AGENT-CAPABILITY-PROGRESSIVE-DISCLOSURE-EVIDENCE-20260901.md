# DR-0058：Agent 能力页四层渐进披露工程 Evidence

- 日期：2026-09-01
- 状态：`Limited Verified`
- 决策：[`DR-0058`](../decisions/DR-0058-progressive-disclosure-agent-capability-page.md)
- 场景：[`SCENARIO-045`](../scenarios/SCENARIO-045-progressive-agent-capability-review.md)
- 测试合同：[`AGENT-CAPABILITY-PROGRESSIVE-DISCLOSURE-GATES-20260901`](../testing/AGENT-CAPABILITY-PROGRESSIVE-DISCLOSURE-GATES-20260901.md)
- 初版实现：Luna 分支 `656edfd` 至 `4c1ce50`；`master` 等价集成 `2673fe4` 至 `f0a281c`
- 视觉重构：Luna 分支 `6901299` 至 `8b51be5`；`master` 等价集成 `58b4958` 至 `4916fcb`
- Adaptive 执行工作面：Luna 分支 `db3f197`、`cbb2017`、`085c26e`；`master` 等价集成
  `09e246b`、`fbf142c`、`fe0878f`

## 1. 本轮证明了什么

`/agent-capabilities` 仍读取同一个 selected Task/Run/Snapshot，但不再默认同时展开完整
Agent Control Loop 与 Adaptive Swarm 工作台：

1. 默认“执行进展”只显示当前状态、主要待办、Branch 完成/等待摘要和当前成果版本；
2. “查看完整执行记录”才显示既有 LoopView、Task lineage、Round/Branch、控制和历史；
3. “协作方式”先显示服务端实际 route；Adaptive 正例以左侧四阶段、中央真实 WorkUnit
   DAG、右侧当前影响和底部协作结果呈现，工作包明细、来源范围和执行回执默认折叠；
4. 证据审查页把 Finding/Resolution 翻译为“系统发现、影响、你要做什么、会保留、不会
   做”，但确认请求仍携带服务端要求的版本、幂等、DecisionRequest 和来源修订字段。

能力 tab 支持 `aria-selected/aria-controls/aria-labelledby`、roving `tabindex` 和左右方向键。
`#adaptive-swarm` 直接刷新仍落在协作方式；历史 Run 仍只读且不连接历史 SSE。

## 2. 工程门

| 门 | 结果 | 能证明 | 不能证明 |
| --- | --- | --- | --- |
| 四层与恢复定向 Playwright | `7 passed` | tab、disclosure、Fixed 反例、历史 Run、真实审查入口和新恢复文案在 Fixture 中成立 | Provider 输出、业务正确性或用户理解 |
| 最终全量 Playwright | `77 passed` | Workspace、预览、现有 15 个场景、Loop/Swarm 与移动端回归未被本轮改坏 | 浏览器和网络的生产稳定性 |
| Adaptive 执行工作面定向 Playwright | `9 passed` | 3 root + 2 dependent、2 条真实依赖、局部阻塞影响、Fixed 反例、历史只读和 390 px overflow 在 Fixture 中成立 | 真实 Provider 的拓扑选择、分布式调度或用户理解 |
| Adaptive 执行工作面全量 Playwright | `80 passed` | 新工作面未破坏既有 Workspace、预览、Loop、场景与移动端浏览器门 | 生产稳定性、任务质量或业务收益 |
| 截图捕获定向门 | `4 passed` | 初版五张图片和视觉重构补充四张图片均来自固定公共 Fixture，不是概念图 | 真实 Provider 或真实用户运行 |
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

### 3.1 视觉重构补充截图

以下图片保留初版截图，不覆盖历史 Evidence。它们绑定 `master` 的 `4916fcb`，证明本轮
大幅收敛默认密度、提高可读字号、统一固定流程文案，并把组织视图改为四阶段与三组按需
明细。它们仍是受控 Fixture，不是真实 Provider、生产 Run 或用户研究。

| 截图 | 尺寸 / bytes / SHA-256 | 被测事实 |
| --- | --- | --- |
| [视觉重构：执行进展](screenshots/dr-0058-visual-redesign-progress-1440.png) | `1440 x 1100` / `59759` / `BB56D2F46947BC9415CD97FD2298C2D8C07F1B3D2BC929E0400C8CF87120AF07` | 当前任务、服务端继续/人工待办和成果版本在首屏分开；完整记录未展开 |
| [视觉重构：固定流程](screenshots/dr-0058-visual-redesign-fixed-1440.png) | `1440 x 1100` / `83882` / `ED2712BE5982BD76B45E36E33C0205DED0372E195BF6872DAACC061B4FC58F03` | 固定流程被服务端选中；任务已准入、工作包处理中，贡献与成果等待前置；零 Worker 回执 |
| [视觉重构：Adaptive Swarm](screenshots/dr-0058-visual-redesign-adaptive-1440.png) | `1440 x 1100` / `87049` / `407D1316430A5332F99D9C9DBC1D602D26485639FD3AED880F8C1F5D4276D881` | Adaptive route、5 个工作包、3 个已汇合贡献、1 个成果版本与显式下一批操作来自同一 Fixture Snapshot |
| [视觉重构：固定流程 390 px](screenshots/dr-0058-visual-redesign-fixed-390.png) | `390 x 1358` / `75893` / `EEB0A8F651F3440EB1416E2407442F4D0A956E97F0BB74805F66E3A2D3958F1F` | 线路、阶段和三项 disclosure 在移动宽度无页面横向溢出 |

视觉重构后的 capability 定向门为 `4 passed`，最终完整
`harness-workbench.spec.ts` 为 `77 passed`，Web lint、production build 与
`git diff --check` 通过。Python、Ruff、Provider 和 PostgreSQL 没有因纯前端收尾重跑；
本文件第二节的 Python/Ruff 数值仍是初版同日基线，不能改写为本提交的新证据。

### 3.2 Adaptive 执行工作面补充截图

Stakeholder 对视觉重构截图复核后指出：原协作页仍主要是路线卡、阶段摘要和 disclosure，
没有把 WorkUnit 的空间依赖、当前影响与成果汇合做成接近概念参考的执行工作面。下列截图
绑定 `master` 的 `fe0878f`，保留旧图而不覆盖历史 Evidence。

| 截图 | 尺寸 / bytes / SHA-256 | 被测事实 |
| --- | --- | --- |
| [Adaptive 执行工作面](screenshots/dr-0058-adaptive-execution-workspace-1440.png) | `1440 x 1100` / `113640` / `2C806D823717FD7C4ABD6C9367C526F417B7E1145EB321B564BEC8EAE1954084` | 同一 Fixture Snapshot 投影任务/Run、左侧阶段轨、5 个 WorkUnit、2 条依赖、右侧影响与 Artifact v1；3 个已采用贡献与后续工作包并存 |
| [Adaptive 执行工作面 390 px](screenshots/dr-0058-adaptive-execution-workspace-390.png) | `390 x 2563` / `135019` / `B3B30FEBF84BA7EBAB0EEC381BFDFE354DADF880ABE4559624B39F6538F844A6` | 移动端把 DAG 降级为带“根/依赖 N”标签的纵向列表，当前影响移到主区之后且无页面横向溢出 |

本次定向门为 `9 passed`，最终完整 `harness-workbench.spec.ts` 为 `80 passed`；Web lint、
production build 与 `git diff --check` 通过。未重跑 Python、Ruff、Provider 或 PostgreSQL。
截图仍是 controlled fixture，不能证明 Runtime 在任意真实任务中一定选择 Adaptive route，
也不能证明用户理解、效率、信任或业务结果改善。

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
