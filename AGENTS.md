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
9. FORTE 与统一 Harness 变更再读 `docs/decisions/DR-0016-public-workspace-agent-harness.md`、`docs/decisions/DR-0017-single-forte-worksite-and-legacy-retirement.md`、`docs/scenarios/SCENARIO-004-*.md` 至 `SCENARIO-007-*.md`、对应 Source/Evidence 和 `docs/decisions/RETIREMENT_REGISTER.md`。

源码永远高于文档。行为或叙事变化后必须同步 living docs、Decision、Scenario、Source、Evidence 和 UI—服务端事实映射，不能只改 README。

## 当前产品事实

- 根页面是唯一 FORTE 工作现场；旧邮件、文档、报价、任务、日历、报销、CRM、审计和固定 Demo 入口已从当前产品树退役。
- 当前 OpenAPI 只有 6 个 path：health、Scenario list/detail、Run start/get/events。
- FORTE 固定上游 commit `345c1ec1487139db9dd319787fa9405ba85d1869`、顶层 MIT、11 个原始文件、`115352` bytes。任务和输入文件按原字节保留并标记为 binary，禁止 Git 换行归一化改变哈希。
- raw `task.md` 只作 provenance；净化后的 Planner context 只在服务端内部使用。公共 API/DOM 不得出现 `task_instruction`、rubric、solution、grading、绝对路径或完整 hash。
- 真实模型调用、模型输出采用、服务端校验通过是三个独立事实，分别依据 `HarnessModelReceipt.called`、`output_used` 和 Snapshot/Event。
- 当前纵切只到 `ready_to_execute`。没有执行命令、Scheduler/Worker、工具调用、Artifact 写入/验证/Commit、审批、Permit、Connector 或外部副作用。
- Harness Run、事件和幂等记录仅在单 API 进程 memory 中；重启不恢复。`X-User-Id` 是未签名的演示 Owner 占位。
- Catalog 完整性失败必须 fail closed 并返回受控 503；前端必须区分服务不可达、Catalog 暂不可用和 Catalog 完整性失败，并提供自动与显式恢复。
- “事件流实时”只在当前 SSE 已连接时显示；API 健康但无活动流只能显示“服务可用”。
- `ready_to_execute` 只能显示“计划已就绪，尚未执行”，不得写成任务完成、工件生成或外部动作成功。
- E2E 是工程代理，不是截图审查或用户研究。当前没有 DR-0017 最终界面的独立新截图；用户理解和价值仍为 `Draft`。
- 历史 Decision/Evidence 的旧数字仍可审计，但不再描述当前 UI、API、数据或验收套件；以 `RETIREMENT_REGISTER.md` 为准。

## 八个统一模块

后续设计、代码和汇报只能使用这一套名称：

1. Scenario Pack & Workspace Catalog
2. Task Contract
3. Planner
4. Admission & Plan Validator
5. Scheduler & Worker Manager
6. Tool Gateway
7. Artifact Workspace & Verifier
8. Checkpoint, Event & Governance Control

当前只实现模块 1-4 的规划纵切和模块 8 的 memory 事件/控制子集；模块 5-7、持久化和执行治理仍是目标架构。

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
