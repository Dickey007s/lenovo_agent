# Office Agent V0.2 agent handoff

这是当前产品基线。修改、分析或制作汇报前依次读取：

1. `README.md`：唯一产品入口、能力边界和验收口径。
2. `docs/ARCHITECTURE.md`：当前分层、信任边界和八模块成熟度。
3. `docs/WORKSPACE_AND_STREAMING.md`：文件夹、预览、前端交互和 SSE。
4. `docs/API.md`：当前八路径公开协议。
5. `docs/contracts/UI_SERVER_FACT_MATRIX.md`：每个 UI 状态的服务端事实。
6. `docs/PRESENTATION_BRIEF.md`：汇报叙事和禁止夸大的结论；制作会议/PPT 主讲稿时再读 `docs/reports/OFFICE-AGENT-DETAILED-CHINESE-REPORT-20260825.md` 与 `docs/research/COMPETITIVE-WHITE-SPACE-AND-FALSIFIABLE-DIFFERENTIATORS-20260826.md`。整库、引用、暂停、恢复和知识工作是主流基线，不得写成独占；未完成固定配置同场实测前，只能称“原生保证差异”或“可证伪候选”。
7. `docs/DECISION_AND_REPORTING_GOVERNANCE.md`：方案、PR、Demo、汇报的硬门槛。
8. 当前整库文件管理器、自主检索和原文定位变更再读 `docs/decisions/DR-0024-autonomous-whole-workspace-research.md`、`docs/decisions/DR-0028-hierarchical-workspace-and-evidence-review.md`、`docs/decisions/DR-0029-server-verified-evidence-anchors.md`、`docs/scenarios/SCENARIO-010-autonomous-whole-workspace-research.md`、`docs/scenarios/SCENARIO-014-inspect-agent-issue-in-context.md`、`docs/scenarios/SCENARIO-015-pinpoint-and-compare-agent-evidence.md`、`docs/research/WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825.md`、`docs/testing/FORTE-PUBLIC-OFFICE-TASK-TEST-CASES-20260825.md` 与对应 Evidence/Source。`DR-0022` 的客户端手工 `selected_file_refs` 已由 `DR-0024` 取代，但其公开数据、安全预览与来源边界继续有效。
9. 修改 Agent Control Loop、文件夹自主研究、预算/停止、分支控制、成果恢复或 Durable State 时，再读 `docs/research/AGENT-CONTROL-LOOP-IMPLEMENTATION-AUDIT-20260825.md`、`docs/decisions/DR-0023-agent-control-loop.md`、`docs/decisions/DR-0024-autonomous-whole-workspace-research.md`、`docs/decisions/DR-0026-selective-branch-and-immutable-artifact-history.md`、`docs/decisions/DR-0031-active-budget-and-agent-owned-gap-recovery.md`、`docs/scenarios/SCENARIO-012-selective-branch-and-artifact-restore.md`、`docs/scenarios/SCENARIO-017-resume-agent-owned-evidence-gap.md` 与对应 Evidence/Source；`DR-0025` 只作整组补证和 Snapshot 内成果的历史基线。对外和设计文档统一称 `Agent Control Loop`；Workspace 是循环处理的办公资料环境，不另立 `Workspace Research Loop` 或 `Research Loop` 产品名称。历史约 `30%` 只表示实现 `8364b1e` 之前的架构成熟度基线；现行 Runtime 默认 12 轮、上限 24 轮，已有顺序单 Controller、服务端 Branch、分支级 Evidence Gate、独立 append-only 逻辑 ArtifactVersion/TaskCommit、历史成果恢复、12 个固定本地确定性办公能力的隔离 Run Workspace Artifact/Verifier，以及可选 PostgreSQL 重启恢复，但任意办公写入、生产安全沙箱、多实例协调、多 Worker 与外部动作仍未实现。

DR-0032 additionally governs EvidenceResolution source revisions, DecisionRequest/
DecisionRecord persistence and Finding/Branch-local restart recovery. Read
`docs/decisions/DR-0032-persistent-decision-and-local-recovery.md`,
`docs/scenarios/SCENARIO-018-persistent-decision-and-local-recovery.md` and its
Evidence before changing those paths. Snapshot JSONB persistence is not an
independent decision ledger or multi-instance CAS; report the real PostgreSQL gate
and any skipped condition explicitly.

DR-0033 governs review exit and Evidence Gap presentation. Read
`docs/decisions/DR-0033-closable-review-and-branch-lanes.md` and
`docs/scenarios/SCENARIO-019-close-review-and-handle-one-branch.md` before changing
these paths. A review must close immediately even when its best-effort `defer`
receipt gets 409 or a transport error; the error remains visible and must not be
presented as recorded. Evidence Gaps must be projected as Branch lanes joining
Branch, current material, Evidence Gate and next action by server-owned IDs, not
as a flat pill list and not as proof of parallel Workers.

DR-0034 governs waiting-Branch action hierarchy. Read
`docs/decisions/DR-0034-one-action-recovery-and-explicit-source-choice.md` and
`docs/scenarios/SCENARIO-020-retry-or-select-one-source.md` before changing these
paths. Retry-only Branches must put one explicit recommended action first, state
that file edits and input are unnecessary, and keep optional clues/audit details
collapsed. Ambiguous EvidenceResolution must say how many real positions require
one human choice, never preselect a candidate and keep accept disabled until a
choice exists. Opening either surface must not call a model or spend next-round
budget; terminal Runs must create a new task rather than pretend to resume.

DR-0035 governs Scenario Effect Gate and real run-workspace files. Read
`docs/decisions/DR-0035-scenario-effect-gate-and-run-workspace-artifacts.md`,
`docs/scenarios/SCENARIO-021-verifiable-office-artifact-effect.md`,
`docs/evidence/SCENARIO-EFFECT-GATE-20260827.md` and
`docs/reports/SCENARIO-EFFECT-GATE-LEDGER-20260827.md` before changing budget,
deterministic office adapters, Artifact download or effect claims. Model call,
model adoption, deterministic Artifact verification and Run terminal status are
separate facts. A verified Artifact survives a later rejected Analyst response.

DR-0036 governs verified-outcome versus audit-location presentation and the TC-01
PDF-layout boundary. Read
`docs/decisions/DR-0036-outcome-first-and-layout-tolerant-evidence.md` and
`docs/scenarios/SCENARIO-022-verified-outcome-and-audit-location.md` before changing
text-anchor normalization, instruction-date filtering, human Gate admission or a
verified Artifact plus waiting Evidence Gap UI. Strict matching remains first;
layout normalization still requires one unique Preview location. A passed Artifact
must appear before audit gaps, and grouping requires both the same candidate sources
and the same failure detail; it is only a browser projection, not a merge of server
Branches or proof that the Run completed.

源码永远高于文档。行为或叙事变化后必须同步 living docs、Decision、Scenario、
Source、Evidence 和 UI-server fact mapping，不能只更新 README。

## 当前产品事实

- 根页面是唯一 FORTE 办公资料库。产品没有注册 Scenario/Demo 选择器；旧邮件、文档、报价、任务、日历、报销、CRM、审计和固定 Customer A 入口均已退休。
- 当前 OpenAPI 有八个 path、九个 operation：health、whole workspace、workspace file preview、Run start/list/get、Run Artifact download、control/events。旧 `/v1/harness/scenarios*` 不挂载。
- FORTE 固定 commit `345c1ec1487139db9dd319787fa9405ba85d1869`。`public-suite-manifest.json` 是当前只读清单：15 个公开任务目录、96 个 input、111 个 task/input 文件、`1780445` bytes。官方完整 benchmark 报告 180 条，但公开仓库只提供每职业一个 demo；不得声称拿到未公开 165 条。
- `task.md` 只作 provenance，不能进入普通 UI、Analyst 输入或成为隐藏默认任务。用户只需自己写 `instruction`；浏览器不得要求或提交客户端 `selected_file_refs`。
- 用户可在一个文件管理器式资料库中按服务端安全 `display_path` 逐级展开顶层目录和嵌套子目录，也可自由搜索、按类型筛选和查看文件，不按职业/角色建立产品入口。当前 96/96 输入可 bounded preview：XLSX/CSV、PDF、DOCX、TXT/Markdown/JSON/log/code。预览前必须校验 allowlist relative path、size、SHA-256、非 symlink、archive/format bounds；不得执行 macro/script 或加载 external resources。目录展开/搜索只是客户端展示状态，不改变整库 Run scope。
- 公共 API/DOM/模型输入不得暴露 raw task/rubric/solution、绝对/内部路径、完整 hash、Prompt、CoT、raw provider response、密钥或内部 validator/effect 字符串。
- 当前成功路径按轮真实调用 Planner 和 Analyst。`called/output_used/elapsed_ms` 必须分开显示；动画和配置模型名不是调用证据。`未采用` 表示模型已返回但服务端校验拒绝，不是未调用。Plan 可在同一预算内进行最多一次受控修复，拒绝与重试都必须进入有序 Trace。
- Run 创建时服务端冻结完整 allowlisted 输入索引，`scope_mode=whole_workspace`。Planner 只看到安全元数据并自主选择本轮证据；服务端拥有每轮文件预算、source scope、side effect、human gate、unit/dependency/tool/source validation。模型计划中的 `run_workspace_write` 仍只表示写入意图；只有 Snapshot `workspace_artifacts[]`、`effect_receipts[]` 和可下载 Artifact bytes 才证明当前 12 个固定本地确定性能力真的写入隔离 Run Workspace。它们不修改 FORTE 原件。
- 每个新 finding 必须引用服务端批准的本轮 `file_ref`，并至少包含一处由 Runtime 从 Analyst 逐字 quote 候选中唯一匹配得到的 `evidence_anchor`。审查页按事实/影响/人工动作拆分 Finding，把证据索引与实际安全 Preview 并排，点击后回开并高亮文本行/表格行。需要人工决断时显示互斥选项、选择后的只读下一步与反馈框；推荐项须在用户先选初始口径后再主动显示，确认只创建独立新 Run，不得声称改文件。浏览器不得从 Finding 文案猜测位置，旧成果无 Anchor 时必须明确退化为文件级核对。Gap/Branch/Finding 必须提供问题描述、轮次/业务分支和关联文件入口；无 Anchor Gap 必须称为 Agent 执行缺口，说明结构/定位/覆盖类型、尝试文件、模型调用/采用、保留项和恢复动作，不得暗示用户修改源文件或猜行号。Git 风格只表示审查记录结构，不得伪造源文件 Diff。这些位置和引用只证明 location/membership，不证明 entailment、穷举或算术正确。
- 严格文本 Anchor 无候选时可忽略安全 Preview 版面造成的空白/标点差异，但仍须唯一匹配；多位置继续 `ambiguous`，不得模糊猜测。用户指令中明确的中文月日闭区间可过滤所有已定位 `observed` 日期都在范围外的 Finding；当前不等于通用范围编译器。需要人工决断的 review 必须至少有一个 exact `contradiction` Anchor，否则降为普通复核。
- 终态 `result.follow_ups` 最多显示 4 条 Agent 下一步建议。建议不是执行事实；当前协议没有逐项引用，审查页只能把 Finding refs 并集标为本轮上下文，不得冒充直接证据。只有用户点击“确认并启动”后才创建新的独立 Run，旧 Run/结果不得被覆盖。
- 默认预算为 12 轮、每轮 16 文件、30 次模型调用和 7200 秒 active deadline；允许上限为 24/24/60/14400。`waiting_input`、显式 pause 和 terminal 状态冻结 elapsed，合法 resume 从已用 active elapsed 继续。validated plan unit 由服务端编译为稳定 Branch；Evidence Gate 按 Branch 维护已核对/缺失引用。证据不足且预算允许时进入 `waiting_input/paused`，用户只选择一条 waiting Branch 继续，下一轮范围严格等于该 Branch 的 `missing_file_refs`，其他 Branch 保持等待。合法范围内的 Analyst 原文定位或结构输出失败最多受控重试一次：可定位 Finding 可部分采用；全不可用时保留 Plan/Branch/调用事实，并以 `next_step.recovery_kind=source_location|analysis_output` 暂停最小分支；范围越权和完整性错误仍 fail closed。每个完成轮次生成独立 append-only 逻辑 evidence-brief ArtifactVersion，成功终态新增 TaskCommit 指针而不改写版本。当前固定确定性办公工具在计划校验后可生成真实隔离 Artifact 和检查回执；Analyst 未采用不会删除该成果。`completed` 仍只表示 Loop 合同通过，不自动证明模型质量、任意任务正确、原文件写入、Worker/Connector 或外部动作发生。
- passed Artifact 与 waiting audit gap 必须分开显示：成果先展示，Gap 只说明 Agent 来源位置待补充；候选来源和失败说明都相同的多个 Gap 可在浏览器合并展示，但 Snapshot Branch 不变，也不能把 Artifact 通过写成 Run `completed`。
- `pause/resume/steer/stop/rollback/decision` 必须携带 expected version 与幂等键。Branch resume 还携带 `branch_id`；rollback 还携带 `artifact_version`，只新增 TaskCommit 并恢复逻辑 Brief，不删除历史或回滚源文件。decision 把 `accept/decline/defer/cancel` 绑定到当前 DecisionRequest/Finding/Resolution/Branch；accept 证据候选还必须携带 source revision，服务端重新读取 Catalog 并重算 candidate。关闭待决页记录 defer，defer 后仍可继续最终决定；cancel 不冒充 rejected。它们不改变原文件或外部状态。pause/stop 只在模型调用之间的安全点生效；steer 只影响下一轮；deadline 阻止新调用但不硬取消在途 HTTP 请求。预算终态必须显示 `budget.stop_reason` 的具体中文原因，不得只显示 raw `budget_exhausted`；terminal Run 不得 resume，只能按 Branch 创建新 Run。
- 开放待决单以 Snapshot 顶层 `decision_requests[]` 为权威，旧轮次投影只作兼容读取。关闭或 Escape 必须先退出审查页，再尝试写入 defer；409/断网只显示非阻塞错误并刷新 Snapshot，不能把用户困在弹窗，也不能伪造回执成功。Evidence Gap 区固定使用“分支 -> 当前材料 -> Evidence Gate -> 下一步”的 Branch lane；各单元只能来自 Branch/Gap/Resolution/Decision 服务端事实，不得把可视分支解释成并行 Worker。普通可恢复 Branch 必须明确“无需核对文件，建议重试”，首屏只给一个推荐 resume 且折叠可选输入/审计；ambiguous Branch 必须明确“从 N 个原文位置中选 1 个”，不默认选择并在未选前禁用 accept。
- Snapshot 是状态权威，SSE 是有序变更投影。浏览器只单调应用 version/sequence，nonterminal 断线用 GET + `after=N`，terminal event 后 final GET。
- 配置 `DATABASE_DSN` 时，Run Snapshot、事件、start/control 幂等回执以及独立 ArtifactVersion/TaskCommit 写入 PostgreSQL；重启恢复会删除未完成轮次、追加 `checkpoint_recovered` 并暂停，绝不自动重放中断的模型调用。真实 PostgreSQL 顺序 Runtime 由 PR integration workflow 验证；这不等于多实例 lease、高可用或在途 HTTP 续跑。未配置数据库时明确使用单进程 memory 且重启不恢复。`X-User-Id` 是未签名演示 Owner。
- `start-demo.ps1` 的状态库优先级是 Docker、本轮 PowerShell 进程显式 `DATABASE_DSN`、memory。没有前两者时必须用空进程变量覆盖 `.env` 残留 DSN；模型配置仍可从 `.env` 读取。前台/汇报只以 `/v1/health.checkpoint/task_store` 判断本轮是否可恢复。
- Catalog/preview 完整性失败必须 fail closed。前台区分 API 离线、workspace integrity failure、file preview failure 和 Run failure，不得填充静态假数据。
- Demo 1/2/3 只是通用能力的验收镜头：当前顺序 Agent Control Loop 已覆盖 Demo 1 的分支推进、成果历史、局部恢复和 12 个固定本地办公效果纵切；这不等于任意办公 Artifact、生产 Tool Gateway 或多实例协调。Demo 2 多 Worker 自组织与 Demo 3 跨拓扑 Risk Gate 仍是目标能力。不得因 Demo 名或 Scenario ID 宣称未实现能力已经执行。
- 自动化和截图是工程代理，不是用户研究。界面是否更清晰、信任/效率/价值是否提升均为 `Draft`。

## 八个统一模块

后续设计、代码和汇报只使用以下名称：

1. Workspace Catalog & Safe Preview
2. Task Contract
3. Planner
4. Admission, Policy Compiler & Plan Validator
5. Scheduler & Worker Manager
6. Tool Gateway
7. Artifact Workspace & Verifier
8. Checkpoint, Event & Governance Control

当前实现模块 1-4、模块 5 的有界单 Loop Controller 子集、模块 6 的 12 个固定本地确定性办公适配器子集、模块 7 的受限 read-only
Result/citation/服务端 Preview Evidence Anchor/Branch Evidence Gate/独立 append-only 逻辑 ArtifactVersion/TaskCommit、隔离 Run Workspace 文件/确定性 Verifier 与恢复子集，
以及模块 8 的 Snapshot、event、branch/rollback control、idempotency 和可选 PostgreSQL
restart-recovery 子集。分布式 Scheduler/Worker、模块 6 的真实 Tool Gateway、可写办公
源文件、通用语义 Verifier、多实例协调、Risk/Evidence/Approval/Permit 和 Connector
均是目标架构。

## 关键路径

```text
apps/web/app/page.tsx
apps/web/app/harness-workbench.tsx
apps/web/app/styles.css
services/api/app/main.py
services/api/app/api/harness_routes.py
services/api/app/application/benchmark_workspace_catalog.py
services/api/app/application/harness_runtime.py
packages/contracts/harness_models.py
demo-enterprise-data/forte/public-suite-manifest.json
tests/unit/test_benchmark_scenario_catalog.py
tests/unit/test_harness_runtime.py
apps/web/e2e/harness-workbench.spec.ts
```

旧 `benchmark_scenario_catalog.py` 仅可作为安全读取 helper 或历史兼容层；不得重新
挂载 Scenario API。Generic risk/authorization/tool gateway/simulator 可以保留为未来
构件，只要未被当前 app/runtime 接入就不能称为现行能力。

## 治理硬门槛

每个方案、实现项、PR、Demo 和汇报结论必须同时记录：

- 场景与来源：目标用户、触发、痛点、完成条件、异常路径，以及 Source ID、日期/版本、支持判断和局限。
- 技术差异与交互影响：不能只列功能；必须说明差异如何改变用户流程。
- 前台输出：用户看到什么、能做什么、等待/失败如何恢复、哪些细节隐藏。
- 后端事实：每个 UI 状态映射到 Snapshot/field/event、Owner、version 和 idempotency。
- 验证与边界：自动化、运行、截图、竞品来源或用户研究分别能和不能证明什么。

任一项缺失只能标 `Draft`。官方竞品资料不是竞品实测，不得声称竞品“做不到”。
自动化不能替代用户研究。

## 技术与验证

Python `>=3.12,<3.13`；Next.js 16、React 19、TypeScript；FastAPI；
OpenAI-compatible `/chat/completions`。不要提交 `.env`、Key、生产凭据或真实客户信息。

提交或交付前运行：

```powershell
uv run pytest -q
uv run ruff check .
pnpm --dir apps/web lint
pnpm --dir apps/web build
pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts
```

本地启动与停止：

```powershell
.\scripts\start-demo.ps1
.\scripts\stop-demo.ps1
```

默认前端 `http://localhost:3000`、API `http://localhost:8010`、OpenAPI
`http://localhost:8010/docs`。若运行结果与文档不一致，以源码为准并修正文档。

与用户沟通时中文直接回答，优先连续短段落。汇报必须把技术差异落到用户交互影响，
并明确当前事实、目标设计和历史证据的生命周期。面向用户、会议和 PPT 的汇报简报、
页面卡片、场景说明与研究结论必须以中文为主；英文只保留产品名、接口/协议标识和
原始来源标题。内部代码契约可以使用英文，但不能把英文技术稿直接当作对用户汇报稿。
