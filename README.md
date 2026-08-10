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
| 任务 | 任务卡编辑、新建、优先级与状态维护、受控创建内部任务 |
| 日历 | 月视图、日程红点、按日展开全部日程、新建与编辑、受控创建邀请 |
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

## 技术架构

```mermaid
flowchart LR
    UI["Next.js 工作区 + Agent 对话"]
    API["FastAPI Conversation / Run API"]
    LLM["OpenAI-compatible LLM"]
    CONTRACT["Pydantic Contracts"]
    GOVERN["Risk + Policy + Evidence + ControlPlan"]
    GRAPH["LangGraph Human-in-the-loop"]
    AUTH["Ed25519 Authorization Service"]
    GATEWAY["Tool Gateway"]
    SIM["Email / Office Simulators"]
    PG["PostgreSQL + LangGraph Checkpoint"]

    UI <-->|"REST + SSE"| API
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

## 目录结构

```text
apps/web/                         Next.js 16 + React 19 前端
packages/contracts/               领域协议与哈希
packages/risk_core/               风险、策略和 ControlPlan
packages/evidence/                确定性 Mock Evidence Resolver
packages/agent_runtime/           LangGraph interrupt/resume 工作流
packages/authorization/           Ed25519 Permit 签发
packages/tool_gateway/            Permit 校验与工具路由
packages/audit/                   内存/PostgreSQL 审计日志
services/api/app/application/     ConversationService、RunService、LLM 适配器
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

V0.1 定稿时共有 22 项自动化测试。测试不调用真实 LLM，不消耗模型额度。

## 数据、身份与安全边界

- `X-User-Id` 与 `X-User-Roles` 只是 V0.1 Demo 身份头，默认前端使用 `demo_user` 和 `current_user,sales_manager`；生产环境必须替换为经过验证的 SSO/JWT。
- 内部邮箱、CRM、报价、OA、知识库和日历内容均为确定性 Demo Fixture，不是真实企业数据。
- 未配置 Permit PEM 文件时，服务启动会生成进程级 Ed25519 密钥；重启后旧 Permit 失效。
- 所有副作用工具均为 Simulator；UI 中的“发送成功”“创建成功”只代表 Simulator 成功。
- 对话 Thread/Message 当前保存在 API 进程内存中，重启后丢失；Workspace、Run、Audit 和 LangGraph checkpoint 在配置 PostgreSQL 时可恢复。
- 当前没有 Alembic 迁移、生产级 RBAC、真实 Connector、后台任务队列、分布式 Permit 重放存储和多实例一致性保障。

## V0.1 验收结论

V0.1 已形成可演示的完整闭环：**用户或 Agent 编辑工作区 → Agent 提议动作 → 服务端评估风险与策略 → 系统取证/人工审批 → 用户最终授权 → Permit 约束执行 → Simulator 返回结果 → Agent 完成对话闭环 → 审计可追溯**。

后续版本应优先替换身份、Connector 和持久化边界，而不是把更多决策权交给模型。V0.1 的核心资产是可验证的治理链路与工作区协同范式，而不是真实办公系统覆盖率。
