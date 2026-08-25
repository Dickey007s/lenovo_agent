# Office Agent V0.2 agent handoff

这是当前产品基线。修改、分析或制作汇报前依次读取：

1. `README.md`：唯一产品入口、能力边界和验收口径。
2. `docs/ARCHITECTURE.md`：当前分层、信任边界和八模块成熟度。
3. `docs/WORKSPACE_AND_STREAMING.md`：文件夹、预览、前端交互和 SSE。
4. `docs/API.md`：当前六路径公开协议。
5. `docs/contracts/UI_SERVER_FACT_MATRIX.md`：每个 UI 状态的服务端事实。
6. `docs/PRESENTATION_BRIEF.md`：汇报叙事和禁止夸大的结论；制作会议/PPT 主讲稿时再读 `docs/reports/OFFICE-AGENT-DETAILED-CHINESE-REPORT-20260825.md`。
7. `docs/DECISION_AND_REPORTING_GOVERNANCE.md`：方案、PR、Demo、汇报的硬门槛。
8. 当前 whole-folder 变更再读 `docs/decisions/DR-0022-workspace-folder-and-arbitrary-task-contract.md`、`docs/scenarios/SCENARIO-008-whole-folder-office-workspace.md`、`docs/research/WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825.md`、`docs/testing/FORTE-PUBLIC-OFFICE-TASK-TEST-CASES-20260825.md` 与对应 Evidence/Source。
9. 修改 Agent Control Loop、文件夹自主研究、预算/停止、暂停/调整方向或 Durable State 时，再读 `docs/research/AGENT-CONTROL-LOOP-IMPLEMENTATION-AUDIT-20260825.md`、`docs/decisions/DR-0023-agent-control-loop.md` 与对应 Source/Scenario。对外和设计文档统一称 `Agent Control Loop`；Workspace 是循环处理的办公资料环境，不另立 `Workspace Research Loop` 或 `Research Loop` 产品名称。当前约 `30%` 只表示按目标模块等权得到的架构成熟度估计；现行 Runtime 仍是单次只读分析流水，不得表述为完整长期 Loop。

源码永远高于文档。行为或叙事变化后必须同步 living docs、Decision、Scenario、
Source、Evidence 和 UI-server fact mapping，不能只更新 README。

## 当前产品事实

- 根页面是唯一 FORTE 办公资料库。产品没有注册 Scenario/Demo 选择器；旧邮件、文档、报价、任务、日历、报销、CRM、审计和固定 Customer A 入口均已退休。
- 当前 OpenAPI 只有六个 path：health、whole workspace、workspace file preview、Run start/get/events。旧 `/v1/harness/scenarios*` 不挂载。
- FORTE 固定 commit `345c1ec1487139db9dd319787fa9405ba85d1869`。`public-suite-manifest.json` 是当前只读清单：15 个公开任务目录、96 个 input、111 个 task/input 文件、`1780445` bytes。官方完整 benchmark 报告 180 条，但公开仓库只提供每职业一个 demo；不得声称拿到未公开 165 条。
- `task.md` 只作 provenance，不能进入普通 UI、Analyst 输入或成为隐藏默认任务。用户必须自己写 `instruction` 并显式选择 1-20 个 `file_ref`。
- 用户可自由搜索、查看和跨目录选择文件。当前 96/96 输入可 bounded preview：XLSX/CSV、PDF、DOCX、TXT/Markdown/JSON/log/code。预览前必须校验 allowlist relative path、size、SHA-256、非 symlink、archive/format bounds；不得执行 macro/script 或加载 external resources。
- 公共 API/DOM/模型输入不得暴露 raw task/rubric/solution、绝对/内部路径、完整 hash、Prompt、CoT、raw provider response、密钥或内部 validator/effect 字符串。
- 当前成功路径真实调用 Planner 和 Analyst。`called/output_used/elapsed_ms` 必须分开显示；动画和配置模型名不是调用证据。`未采用` 表示模型已返回但服务端校验拒绝，不是未调用。
- Planner 只提出业务意图。服务端拥有 source scope、side effect、human gate、unit/dependency/tool/source validation。`run_workspace_write` 在当前仅表示逻辑本轮结果，不证明 Artifact/File 写入。
- 每个 finding 必须引用冻结选择集内的 `file_ref`，引用按钮能回开对应安全预览。这只证明 membership，不证明 entailment、穷举或算术正确。
- 当前可到 `completed` v9/seq8，代表 schema/ref/read-only checks 通过且 `review_required=true`；不代表任务正确、质量通过、Artifact Commit、Tool/Worker/Connector 或外部动作发生。
- Snapshot 是状态权威，SSE 是有序变更投影。浏览器只单调应用 version/sequence，nonterminal 断线用 GET + `after=N`，terminal event 后 final GET。
- Run、事件和幂等记录仅在单 API 进程 memory；重启不恢复。`X-User-Id` 是未签名演示 Owner。
- Catalog/preview 完整性失败必须 fail closed。前台区分 API 离线、workspace integrity failure、file preview failure 和 Run failure，不得填充静态假数据。
- Demo 1/2/3 只是通用能力的验收镜头：Demo 1 是单任务有界循环，Demo 2 是多任务自组织，Demo 3 是跨两种拓扑的 Risk Gate。当前产品没有实现这些 target executors，不得因 Demo 名或目标 profile 宣称已执行。
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

当前实现模块 1-4、模块 7 的受限 read-only Result/citation 子集，以及模块 8 的
memory event/idempotency 子集。模块 5-6、immutable Artifact/Commit、durable
checkpoint、Risk/Evidence/Approval/Permit 和 Connector 均是目标架构。

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
