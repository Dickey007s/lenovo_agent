# Office Agent V0.1

> V0.1 定稿基线，2026-07-14。一个以办公工作区为主体、由 Agent 协助编辑，并对副作用动作实施确定性治理与人工确认的 P0 原型。

最新阶段的目标架构、最终讲稿、交互原型和 0716 汇报原件见 [`docs/final-reference/`](docs/final-reference/README.md)。这些材料用于后续版本转向参考，不改变本页描述的 V0.1 已实现边界。

## 项目定位

本项目不是“把聊天框放进办公软件”，而是在邮件、文档、报价表、任务、日历、报销和 CRM 等既有工作区之上增加 Agent 辅助层：用户可以独立编辑和保存，Agent 能读取当前未保存内容并直接修改工作区；只有涉及发送、系统写入或外部影响时，系统才创建受控动作，执行风险评估、证据校验、人工审批和一次性授权。

V0.1 重点验证三件事：

1. **工作区与对话解耦**：左侧是可独立操作的办公工作区，右侧是持续存在的 Agent 对话；切换视图不会丢失对话。
2. **模型负责理解，代码负责治理**：LLM 生成自然语言、工作区草稿和业务候选字段；风险等级、策略、证据、审批、Permit 和工具执行全部由服务端确定性逻辑决定。
3. **人工确认是自动化链路的一部分**：受控动作不会停在“请确认”的文字提示，而是通过可交互确认卡完成补证据、逐角色审批、最终授权，再把 Simulator 结果返回给 Agent 闭环回应。

所有产生副作用的工具当前均为 **Simulator**，不会发送真实邮件、写入真实日历、CRM、OA 或任务系统。

## V0.1 已实现能力

### 办公工作区

| 视图 | 当前能力 |
| --- | --- |
| 邮件 | 空白编辑器、新邮件入口、收件人/抄送/主题/正文/附件编辑、保存、Agent 渐进式写入、受控发送 |
| 文档 | 分章节编辑、Agent 生成会议纪要或周报、来源与修改记录 |
| 报价表 | 类 Excel 行列编辑、折扣底线提示、金额汇总、导入入口占位 |
| 任务 | “指挥台 / 共享工件 / 待办”三种模式；Task Director 展示服务端阶段、分支、工件、验证、冲突和 Commit，待办保留可编辑看板 |
| 日历 | 全宽月历一级视图、日期格内嵌日程条目、点击进入当日安排、新建与编辑、受控创建邀请 |
| 报销 | 报销单与发票核查、异常提示、受控发起补件请求 |
| CRM | 商机阶段和下一步编辑、受控更新商机 |
| 审计 | Run 事件流、Trace、审批、Permit 与 Simulator 执行记录 |

工作区按用户持久化到 PostgreSQL。当前每种视图维护一个活动 `WorkspaceArtifact`；邮件“新邮件”会创建新的空白活动 Artifact，并解除上一封邮件的动作绑定。V0.1 尚未实现收件箱、草稿箱和多文档列表。

### Agent 与实时交互

- OpenAI-compatible LLM 负责多轮对话、通识问答、工作区草稿和 `ActionCandidate` 生成。
- `ConversationPlan` 与 `ActionCandidate` 使用 Pydantic 严格校验；网关不支持 JSON mode 时自动回退到 Schema Prompt，并最多执行一次结构修复。
- 对话使用 SSE 流式输出；工作区更新使用 `artifact.stream.started → artifact.delta → artifact.updated` 增量协议。
- 邮件正文按文本块呈现打字效果；文档章节、任务、报价和日历项目按项出现，并显示轻量“Agent 正在编辑”状态。
- 普通非敏感通识问题走直接问答路径，避免误复用上一轮办公动作；企业内部事实仍只能来自受信上下文。
- 风险等级和判断规则只在确认前的 Agent 回复中出现一次；执行完成后只反馈成功、失败或拒绝结果。

### 治理与执行闭环

- 严格协议：`ActionCandidate`、`ProposedActionSpec`、`RiskAssessment`、`PolicyEffect`、`EvidenceRecord`、`ControlPlan`、`ApprovalRecord`、`PermitMetadata`、`ToolExecutionResult`。
- Risk Engine 根据影响范围、数据类别、可逆性和信息完整度计算 L0-L4；L5 仅用于受限能力、受限执行或凭据暴露。
- Policy Engine 对外发邮件、外部日历邀请、内部系统写入、报价数据、非受管设备和受限能力应用确定性规则。
- Evidence Resolver 模拟企业通讯录、文件哈希、DLP、CRM 报价库、日历、项目、OA 和 CRM 权限校验。
- LangGraph `interrupt/resume` 覆盖补证据、人工审批和最终授权三个 Gate。
- Ed25519 JWT Permit 绑定用户、capability、动作哈希、参数哈希、策略版本、审批、有效期、单次使用和幂等键。
- Tool Gateway 校验签名、过期、主体、capability、参数、策略版本和重放后，才允许调用 Simulator。
- 已端到端注册 5 个执行 capability：`email.send`、`task.create`、`calendar.invite`、`crm.opportunity.update`、`expense.request_evidence`。
- 工作区内容在动作绑定后发生变化时，旧 Action 会被作废，不能用旧审批执行新参数。
- Run、工作区、审计事件和 LangGraph checkpoint 可持久化并在服务重启后恢复。

### Demo 1 Task Director、交付物与恢复闭环（PR 4-6）

- `TaskService` 从严格的 `TaskContractDraft` 创建服务端拥有的 `TaskContract`、`TaskSnapshot`、三个初始 `BranchSnapshot` 和首条 `TASK_CREATED`。新任务仍从 `ready / contract` 开始。
- 完成、失败或取消后的 Demo 1 会在右上角显示“再次演示”；每一轮通过新的 `Idempotency-Key` 创建独立 Task，刷新后仍可开始下一轮，旧 Task、工件和 Commit 历史不会被重置或覆盖。
- `POST /v1/tasks/{task_id}/start` 对固定客户 A Fixture 执行一次确定性状态转换：产生 Observe、Plan、Act、Verify 事件，追加 ArtifactVersion 和 VerificationReport，并把 2,400 万元正式口径与 2,680 万元预测口径的冲突限制在经营分析分支。该路径不调用 LLM，也不读取真实邮箱、CRM、预测表或项目系统。
- `POST /v1/tasks/{task_id}/controls` 接受带 `expected_task_version` 和 `idempotency_key` 的 Steer、Pause、Resume、Take over、Return control 与 Resolve evidence。分支控制只有在服务端返回新 Snapshot 后才显示为已应用；Steer 当前只进入 `accepted` 时，前端只显示“方向指令已记录，等待后续循环应用”。
- `TaskStore` 的内存与 PostgreSQL 实现包含 Snapshot、TaskEvent 和 ArtifactVersion 的 mutation 路径。`start` 和 `resolve_evidence` 会在写入前校验预计步骤、工具调用、运行时长和截止时间，超限时拒绝 mutation。PR 5 已用 PostgreSQL 16.14 隔离数据库和三个顺序 API 进程验证 v2/v3 Snapshot 恢复、原幂等响应重放，以及 Event/ArtifactVersion/Commit 零新增。
- Tasks 默认进入左侧 Task Director：头部事实摘要、Observe/Plan/Act/Verify/Commit 阶段轨和三个 Branch 泳道都来自同一 `TaskSnapshot`；右侧默认 Decision Inbox，只突出 open Conflict 和现有服务端控制，也可切回持续存在的 Agent 对话。视觉阶段、连接线和颜色不构成新的后台进度事实。
- 每个分支 head 可直接打开“共享工件”。该工作区从同一 Snapshot 显示当前版本、验证、冲突、结构化内容、折叠来源与检查、完整 lineage 以及最终 Commit/state hash；默认在 mutation 后跟随新 head，用户主动查看旧版本时显示明确历史 banner 和返回当前版本动作。
- Tasks 保留“待办”模式，原手工待办编辑流程没有被长期任务 UI 替换。PR 4 对 `analysis/risk_brief/reply_draft` 使用字段 allowlist，未知 kind/字段默认隐藏；PR 5 让冲突与交付物复用同一 `source_ref` 投影，只放行契约中的四个已知 Demo 1 Fixture 引用，其他标识显示隐藏占位。这是前端第二道防线，不代表服务端数据删除，也不是通用字段安全保证。
- Decision Inbox 的收入冲突主动作仍提交 `resolve_evidence` 并采用契约内 CRM 正式来源；“准备补证指令”只填充 Steer，提交后也只显示“已记录，等待后续循环应用”。新布局没有新增后端协议、控制种类或真实 Connector。
- Task SSE 只用于发现新事件并触发 Snapshot 对账；同步标记只表示客户端传输状态，不代表后台仍在执行。未知 mutation 会在当前标签页保存原 key、intent 与预期版本。浏览器 E2E 已覆盖 start 请求发送前 abort、reload、同 key 对账和无重复工件；PR 5 的 system Edge 运行还覆盖同页 API 进程停止、控制禁用、顶部与 Task 面板一致显示恢复中，以及新进程启动后的 Snapshot 对账。尚未覆盖请求已到服务端但响应丢失或断线期间产生新事件的 `after` 回放。
- Action Gate 打开时保留 Active Task Bar；TaskRuntimePanel 仍挂载以保留未提交 Steer 草稿，但通过 CSS 视觉隐藏并退出交互，Task Runtime 与 Task Bar 操作均不可用。Gate 使用独立网格行，收起后把该行缩至 58px。Action Gate 仍沿用独立 `RunService → Risk/Policy/Evidence/Approval/Permit → Gateway` 链路；Task Artifact 尚未绑定 Action 版本和失效规则。

这仍是固定 Fixture 的同步纵切，不是通用后台调度器或真实 Connector。`start` 在一次 mutation 中物化阶段 Trace，浏览器在事务提交后才看到结果；人工编辑后产生新版本、预算/截止时间拒绝后的完整恢复 UI、单分支失败、服务端已提交但响应丢失、断线期间事件回放、数据库进程重启、已有库迁移、多实例通知和 Task Artifact → Action 失效绑定仍待验证。Task 恢复也不等于 Conversation 恢复，Thread/Message 仍在 API 内存中。证据见 PR 3 Runtime、PR 4 浏览器与 [`PR 5 PostgreSQL-backed API 重启证据`](docs/evidence/DEMO1-PR5-POSTGRES-BACKED-API-RESTART-EVIDENCE.md)。

## 技术架构

```mermaid
flowchart LR
    UI["Next.js 工作区 + Agent 对话"]
    API["FastAPI Conversation / Run / Task API"]
    TASK["TaskService + TaskStore"]
    LLM["OpenAI-compatible LLM"]
    CONTRACT["Pydantic Contracts"]
    GOVERN["Risk + Policy + Evidence + ControlPlan"]
    GRAPH["LangGraph Human-in-the-loop"]
    AUTH["Ed25519 Authorization Service"]
    GATEWAY["Tool Gateway"]
    SIM["Email / Office Simulators"]
    PG["PostgreSQL + LangGraph Checkpoint"]

    UI <-->|"REST + SSE"| API
    API --> TASK
    TASK <--> PG
    API --> LLM
    LLM --> CONTRACT
    CONTRACT --> GOVERN
    GOVERN --> GRAPH
    GRAPH --> AUTH
    AUTH --> GATEWAY
    GATEWAY --> SIM
    API <--> PG
```

核心依赖方向是：**LLM 输出候选业务事实 → 严格协议校验 → 确定性治理 → 人工 Gate → 一次性授权 → Gateway 校验 → Simulator**。模型不能直接签发 Permit、改变风险等级、伪造证据或调用工具。

详细说明见：

- [系统架构与技术路线](docs/ARCHITECTURE.md)
- [ActionSpec、风险、策略与授权](docs/GOVERNANCE_AND_ACTIONS.md)
- [工作区、对话与流式协议](docs/WORKSPACE_AND_STREAMING.md)
- [HTTP API 与 SSE 事件](docs/API.md)
- [演示脚本与 Presentation Brief](docs/PRESENTATION_BRIEF.md)
- [Loop、Swarm 与统一 Agent Runtime 目标架构](docs/TARGET_ARCHITECTURE.md)
- [决策、推进与汇报治理](docs/DECISION_AND_REPORTING_GOVERNANCE.md)
- [Demo 1 Task Runtime 协议](docs/contracts/TASK_RUNTIME_PROTOCOL.md)
- [Demo 1 UI—服务端事实矩阵](docs/contracts/UI_SERVER_FACT_MATRIX.md)
- [Demo 1 场景与决策记录](docs/scenarios/SCENARIO-001-customer-a-durable-report.md)
- [Demo 1 PR 3 运行证据与边界](docs/evidence/DEMO1-PR3-RUNTIME-EVIDENCE.md)
- [Demo 1 PR 4 前端与 E2E 证据](docs/evidence/DEMO1-PR4-FRONTEND-E2E-EVIDENCE.md)
- [Demo 1 PR 5 PostgreSQL-backed API 重启证据](docs/evidence/DEMO1-PR5-POSTGRES-BACKED-API-RESTART-EVIDENCE.md)
- [LLM API 连通性证据](docs/evidence/LLM-API-SMOKE-EVIDENCE-20260811.md)
- [前端视觉同步与 Demo 1 兼容决策](docs/decisions/DR-0003-frontend-visual-refresh-sync.md)
- [前端视觉同步与兼容证据](docs/evidence/DR-0003-FRONTEND-VISUAL-SYNC-EVIDENCE.md)
- [Demo 1 可重复演示决策](docs/decisions/DR-0004-repeatable-demo1-rounds.md)
- [Task Director 交互决策](docs/decisions/DR-0005-task-director-interaction.md)
- [Task Director 交互证据](docs/evidence/DEMO1-PR6-TASK-DIRECTOR-INTERACTION-EVIDENCE.md)

## 目录结构

```text
apps/web/                         Next.js 16 + React 19 前端
packages/contracts/               动作与 Task Runtime 协议、哈希
packages/risk_core/               风险、策略和 ControlPlan
packages/evidence/                确定性 Mock Evidence Resolver
packages/agent_runtime/           LangGraph interrupt/resume 工作流
packages/authorization/           Ed25519 Permit 签发
packages/tool_gateway/            Permit 校验与工具路由
packages/audit/                   内存/PostgreSQL 审计日志
services/api/app/application/     ConversationService、RunService、TaskService 与存储适配器
services/api/app/api/             FastAPI 路由
simulators/                       邮件与办公动作 Simulator
tests/                            单元与集成测试
docs/                             架构、治理、协议、API 和演示资料
```

## 本地运行

### 环境要求

- Windows 10/11（启动脚本按 PowerShell 编写）
- Python 3.12、[uv](https://docs.astral.sh/uv/)
- Node.js、pnpm/Corepack
- Docker Desktop（PostgreSQL 16）

复制配置并填写实际的 OpenAI-compatible 推理地址和 Key：

```powershell
Copy-Item .env.example .env
```

```dotenv
LLM_BASE_URL=https://your-openai-compatible-endpoint.example/v1
LLM_API_KEY=replace_me
LLM_MODEL=deepseek-v4-pro
LLM_THINKING_MODE=disabled
DATABASE_DSN=postgresql://agent:agent@127.0.0.1:5432/office_agent
LANGGRAPH_CHECKPOINT_DSN=postgresql://agent:agent@127.0.0.1:5432/office_agent
```

不要把真实 Key 提交到仓库。`LLM_BASE_URL` 必须指向模型推理服务，项目调用 `${LLM_BASE_URL}/chat/completions`。

Windows 推荐直接运行：

```powershell
.\scripts\start-demo.ps1
```

脚本会检查 Docker Desktop、启动 PostgreSQL、FastAPI 和 Next.js：

- 前端：<http://localhost:3000>
- API：<http://localhost:8010>
- OpenAPI：<http://localhost:8010/docs>
- 健康检查：<http://localhost:8010/v1/health>

停止服务：

```powershell
.\scripts\stop-demo.ps1
```

也可以分别启动：

```powershell
uv sync
uv run python -m services.api.run

pnpm --dir apps/web install
pnpm --dir apps/web dev
```

## 验证

```powershell
uv run pytest -q
uv run ruff check .
pnpm --dir apps/web lint
pnpm --dir apps/web build
```

V0.1 定稿基线和 Demo 1 各 PR 的实际验证结果记录在 [`DR-0002`](docs/decisions/DR-0002-bounded-durable-office-loop.md) 及对应 evidence。PR 3 封口验证为全量 Python `56 passed`；PR 4 的 system Edge E2E 为 `2 passed (18.4s)`。PR 5 与前端视觉刷新/可重复演示合并后的封口回归为：PostgreSQL 16.14 opt-in 系统测试 `1 passed (9.78s)`，system Edge suite `3 passed (17.0s)`，完整 Python `58 passed, 1 skipped (2.00s)`。PR 6 Task Director 的最终全量浏览器 E2E 为 `6 passed (34.5s)`，专用截图封口用例为 `1 passed (21.6s)`，完整 Python 为 `58 passed, 1 skipped (3.46s)`，Ruff、前端 lint、生产构建和治理测试通过；[`design-qa.md`](design-qa.md) 最终为 `passed`，无剩余 P0/P1/P2。新增两项乱序回归防止旧 GET 覆盖较新 Snapshot 或把未追上已观察 SSE 的页面伪标为已同步。这只证明固定 Fixture 的前台投影和被测交互，不证明用户理解、效率或决策质量已经改善。固定 Demo 1 Task 测试不调用真实 LLM；独立 LLM smoke 只验证 `deepseek-v4-pro` 通用问答与 Conversation SSE 连通性。

## 数据、身份与安全边界

- `X-User-Id` 与 `X-User-Roles` 只是 V0.1 Demo 身份头，默认前端使用 `demo_user` 和 `current_user,sales_manager`；生产环境必须替换为经过验证的 SSO/JWT。
- 内部邮箱、CRM、报价、OA、知识库和日历内容均为确定性 Demo Fixture，不是真实企业数据。
- 未配置 Permit PEM 文件时，服务启动会生成进程级 Ed25519 密钥；重启后旧 Permit 失效。
- 所有副作用工具均为 Simulator；UI 中的“发送成功”“创建成功”只代表 Simulator 成功。
- 对话 Thread/Message 当前保存在 API 进程内存中，重启后丢失；Workspace、Run、Audit 和 LangGraph checkpoint 在配置 PostgreSQL 时可恢复。
- Task 在未配置数据库时同样只保存在 API 进程内存中；Demo 1 mutation 会写 Snapshot、TaskEvent 和 ArtifactVersion。配置 PostgreSQL 后对应表为 `agent_tasks`、`agent_task_events` 和 `agent_task_artifact_versions`。本机 PostgreSQL 16.14 已验证同一数据库上的顺序 API 进程恢复；该结论不覆盖数据库重启/崩溃、多实例并发、迁移或 Conversation Thread/Message。
- 当前没有 Alembic 迁移、生产级 RBAC、真实 Connector、后台任务队列、分布式 Permit 重放存储、Task 跨实例通知和多实例一致性保障。

## V0.1 验收结论

V0.1 已形成可演示的完整闭环：**用户或 Agent 编辑工作区 → Agent 提议动作 → 服务端评估风险与策略 → 系统取证/人工审批 → 用户最终授权 → Permit 约束执行 → Simulator 返回结果 → Agent 完成对话闭环 → 审计可追溯**。

后续版本应优先替换身份、Connector 和持久化边界，而不是把更多决策权交给模型。V0.1 的核心资产是可验证的治理链路与工作区协同范式，而不是真实办公系统覆盖率。
