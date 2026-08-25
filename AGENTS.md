# Office Agent V0.2 · Agent Handoff

这是当前产品基线。开始修改、分析或制作汇报前，依次读取：

1. `README.md`：唯一产品入口、能力边界和验收口径。
2. `docs/ARCHITECTURE.md`：当前分层、信任边界和八模块成熟度。
3. `docs/WORKSPACE_AND_STREAMING.md`：工作现场、恢复和 SSE 语义。
4. `docs/GOVERNANCE_AND_ACTIONS.md`：当前计划治理与尚未接入的执行治理。
5. `docs/API.md`：唯一公开路由与协议。
6. `docs/contracts/UI_SERVER_FACT_MATRIX.md`：每个前台状态的服务端事实。
7. `docs/PRESENTATION_BRIEF.md`：汇报叙事和不可夸大边界。
8. `docs/DECISION_AND_REPORTING_GOVERNANCE.md`：每个决策、PR、Demo 和汇报必须满足的硬门槛。
9. FORTE、数据预览、只读分析与统一 Harness 变更再读 `docs/decisions/DR-0016-public-workspace-agent-harness.md`、`DR-0017-single-forte-worksite-and-legacy-retirement.md`、`DR-0018-forte-data-workbench-and-verifiable-trace.md`、`DR-0019-capability-composed-agent-runtime.md`、`DR-0020-server-owned-plan-policy-compilation.md`、`DR-0021-forte-public-suite-expansion.md`、`docs/testing/FORTE-PUBLIC-OFFICE-TASK-TEST-CASES-20260825.md`、`docs/scenarios/SCENARIO-004-*.md` 至 `SCENARIO-007-*.md`、对应 Source/Evidence 和 `docs/decisions/RETIREMENT_REGISTER.md`。

源码永远高于文档。行为或叙事变化后必须同步 living docs、Decision、Scenario、Source、Evidence 和 UI—服务端事实映射，不能只改 README。

## 当前产品事实

- 根页面是唯一 FORTE 工作现场；旧邮件、文档、报价、任务、日历、报销、CRM、审计和固定 Demo 入口已从当前产品树退役。
- 当前 OpenAPI 只有 7 个 path：health、Scenario list/detail、Scenario file preview、Run start/get/events。
- Demo 1/2/3 只是通用能力的验收视角，不是三套 Runtime。公共、内部与 Planner Scenario 契约不得使用 `demo_id` 或 `experience_policy` 分流；统一使用 `work_profile.task_topology/orchestration/control_requirements/current_runtime_scope`。
- Demo 1 对应“单任务拆解 + 有界循环 + 证据/人工暂停”；Demo 2 对应“多任务自组织 + 自适应调度 + 共享工件收敛”；Demo 3 是可叠加到两种拓扑的 Risk Gate，不是第三种编排引擎。
- 当前 `current_runtime_scope` 固定为 `read_only_analysis`。不得把 Catalog 中的目标 `bounded_loop` / `adaptive_swarm` 配置、前端动画或 Demo 名称表述为执行已经发生。
- FORTE 固定上游 commit `345c1ec1487139db9dd319787fa9405ba85d1869`、顶层 MIT。`public-suite-manifest.json` 记录官方公开的 15 个职业示例、96 个 input、111 个 task/input 文件和 `1780445` bytes；当前产品 `manifest.json` 仍只 allowlist 三个场景、11 个原始文件和 `115352` bytes。下载不等于 Runtime 支持，禁止把待适配任务显示为可运行。
- raw `task.md` 只作 provenance；公共预览和 Analyst 输入由 Catalog 重新校验并安全投影。公共 API/DOM/Analyst 不得出现原始 `task_instruction`、rubric、solution、grading、绝对路径或完整 hash。
- 每个文件使用稳定的 `file_ref`。用户可以选择当前 Scenario 中的文件并提交自己的 `instruction`；服务端必须拒绝重复、畸形、未知或跨 Scenario 引用。
- 当前成功路径调用两次 `deepseek-v4-pro`：Planner 生成工作图，Analyst 读取安全预览生成引用结果。两次 `called/output_used/elapsed_ms` 必须分别显示；配置模型名或动画不是调用事实。
- Planner 只提出业务工作意图，不能拥有 `side_effect`、写入范围或 human gate 等策略事实。服务端必须先把候选编译为允许的操作语义，再做确定性校验；普通 UI 只显示业务标签和可恢复错误，不得暴露 raw tool/effect 枚举。
- 模型回执固定区分 `未调用`、`已采用`、`校验未通过`。已知失败或完成后的重新运行是新命令并使用新幂等键；只有启动结果未知且命令签名不变时复用原键。
- 当前纵切可到 `completed`：八个有序事件、结果引用范围校验、`review_required=true`。这只表示初步只读响应已形成并通过结构/引用/边界检查，不表示结论正确；没有 Scheduler/Worker、Tool Gateway 调用、ArtifactVersion/Commit、审批、Permit、Connector 或外部副作用。
- Harness Run、事件和幂等记录仅在单 API 进程 memory 中；重启不恢复。`X-User-Id` 是未签名的演示 Owner 占位。
- Catalog 完整性失败必须 fail closed 并返回受控 503；前端必须区分服务不可达、Catalog 暂不可用和 Catalog 完整性失败，并提供自动与显式恢复。
- “事件流实时”只在当前 SSE 已连接时显示；API 健康但无活动流只能显示“服务可用”。
- `completed` 的业务标签只能显示“初步结果已形成”，不得写成任务正确、质量通过、企业流程完成、工件已提交或外部动作成功。结果只校验 `file_ref` 属于所选集合，不证明语义、穷举完整性或算术正确；Finance-018 已保留确定性负向回归作为边界证据。
- E2E 与三张 DR-0018 截图是工程代理，不是用户研究。running 图来自第二次真实运行；result 图来自既有真实 Snapshot 的浏览器 POST replay，不是第三次模型调用或产品历史恢复。页面是否更清晰、用户理解和价值仍为 `Draft`。
- 历史 Decision/Evidence 的旧数字仍可审计，但不再描述当前 UI、API、数据或验收套件；以 `RETIREMENT_REGISTER.md` 为准。

## 八个统一模块

后续设计、代码和汇报只能使用这一套名称：

1. Scenario Pack & Workspace Catalog
2. Task Contract
3. Planner
4. Admission, Policy Compiler & Plan Validator
5. Scheduler & Worker Manager
6. Tool Gateway
7. Artifact Workspace & Verifier
8. Checkpoint, Event & Governance Control

当前实现模块 1-4、模块 7 的受限 Snapshot Result/引用校验子集，以及模块 8 的 memory 事件/幂等子集；模块 5-6、版本化 Artifact/Commit、持久化和外部动作治理仍是目标架构。

## 关键路径

```text
apps/web/app/page.tsx
apps/web/app/harness-workbench.tsx
apps/web/app/styles.css
services/api/app/main.py
services/api/app/api/harness_routes.py
services/api/app/application/benchmark_scenario_catalog.py
services/api/app/application/harness_runtime.py
packages/contracts/harness_models.py
demo-enterprise-data/forte/manifest.json
tests/unit/test_benchmark_scenario_catalog.py
tests/unit/test_harness_runtime.py
apps/web/e2e/harness-workbench.spec.ts
```

Generic risk、authorization、tool gateway 和 simulator 包可以保留为未来构件；只要没有被当前路由和 Runtime 接入，就不能称为当前能力。

## 治理硬门槛

每个方案、实现项、PR、Demo 和汇报结论必须同时记录：

- 场景与来源：目标用户、触发、痛点、完成条件、异常路径，以及可追溯 Source ID、日期/版本、支持判断和局限。
- 前台交互影响：用户看到什么、能做什么、等待/失败如何恢复、哪些内部细节隐藏。
- 后端事实映射：每个 UI 状态对应的 Snapshot/字段/有序事件、版本、Owner 和幂等语义。
- 验证与边界：自动化、运行工件、截图或用户研究的证据类型，以及不能推出的结论。

任一项缺失只能标 `Draft`。官方竞品资料不是竞品实测；不能声称竞品“做不到”。自动化不能替代用户研究。

## 技术与验证

Python 固定 `>=3.12,<3.13`；前端使用 Next.js 16、React 19 和 TypeScript；API 使用 FastAPI；LLM 使用 OpenAI-compatible `/chat/completions`。不要提交 `.env`、Key、生产凭据或真实客户信息。

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

默认地址为前端 `http://localhost:3000`、API `http://localhost:8010`、OpenAPI `http://localhost:8010/docs`。若运行结果与文档不一致，以源码和命令输出为准，并修正文档。

与用户沟通时使用中文直接回答，优先连续短段落。汇报必须把技术差异落到用户交互影响，并明确当前事实、目标设计和历史证据的生命周期。
