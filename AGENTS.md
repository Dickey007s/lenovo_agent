# Office Agent V0.1 · Agent Handoff

这是 V0.1 定稿基线。后续 Agent 开始修改、分析或制作汇报前，按以下顺序读取：

1. `README.md`：产品定位、能力边界、运行与验收结论。
2. `docs/ARCHITECTURE.md`：分层、信任边界、持久化和调用链。
3. `docs/WORKSPACE_AND_STREAMING.md`：工作区模型、前端交互和 SSE。
4. `docs/GOVERNANCE_AND_ACTIONS.md`：ActionSpec、风险、策略、证据、审批、Permit。
5. `docs/API.md`：真实路由、请求和事件协议。
6. `docs/PRESENTATION_BRIEF.md`：对外叙事、演示路径和不可夸大的边界。

源码永远高于文档。行为变更后必须同步相关文档；不要只改 README 的宣传描述。关键实现路径：

```text
apps/web/app/page.tsx                         前端状态、工作区、对话和确认卡
apps/web/app/styles.css                       布局、滚动、动效和视觉
services/api/app/api/routes.py                HTTP 与 SSE API
services/api/app/application/conversations.py 对话、上下文、Artifact 与流式事件
services/api/app/application/llm.py           OpenAI-compatible 适配与结构校验
services/api/app/application/runs.py          治理 Run 和执行编排
packages/contracts/models.py                  安全边界协议
packages/risk_core/                           风险、策略和 ControlPlan
packages/evidence/                            Mock Evidence Resolver
packages/agent_runtime/workflow.py             LangGraph interrupt/resume
packages/authorization/service.py             Ed25519 Permit
packages/tool_gateway/gateway.py               Permit 校验与工具注册
simulators/                                   非真实副作用工具
tests/                                        单元与端到端回归
```

必须保留的产品与安全不变量：

- 工作区在左、Agent 在右；双方独立滚动，中间可拖动，切换工作区不重建对话。
- 用户可以独立编辑和保存；Agent 接收活动视图与未保存的 `workspace_context`。
- 人工确认使用对话底部非模态 tray，不恢复独立审批页，也不完全遮挡消息区。
- 动作确认后必须继续执行并由 Agent 返回结果，前端不能硬编码“已完成”。
- LLM 只生成自然语言、ArtifactDraft 与 ActionCandidate；Risk、Policy、Evidence、Approval、Permit 和工具执行由确定性代码决定。
- 风险规则不能退化为“所有外部动作都是 L5”。普通累计最高 L4；L5 仅由受限能力、受限执行或凭据公开等硬条件触发。
- 风险判断在确认前的 Agent 文本中只输出一次；确认卡可保留结构化风险，最终结果不重复风险段落。
- Artifact 绑定动作后若内容改变，旧 Action 必须失效；不能复用旧审批或 Permit。
- `email.send` 等执行结果当前全部来自 Simulator。不得在文档、UI 或汇报中表述为真实邮件、CRM、日历或 OA 写入。
- 25 类 ActionCandidate 是协议目录，不代表全部可执行；当前只有 5 个 capability 注册了端到端 Simulator。

技术约束：Python 固定 `>=3.12,<3.13`；前端使用 Next.js 16、React 19 和 TypeScript；API 使用 FastAPI；持久化使用 PostgreSQL 16；LLM 调用 OpenAI-compatible `/chat/completions`。不要提交 `.env`、真实 Key、真实客户信息或生产凭据。

修改前先搜索现有模式，保持局部改动，不做无关重构。涉及协议时同步检查前端类型、Pydantic 模型、RunService、测试和文档。涉及风险与授权时必须补回归测试，不能只依靠 UI 手测。

提交或交付前运行：

```powershell
uv run pytest -q
uv run ruff check .
pnpm --dir apps/web lint
pnpm --dir apps/web build
```

本地启动与停止：

```powershell
.\start-demo.ps1
.\stop-demo.ps1
```

默认地址为前端 `http://localhost:3000`、API `http://localhost:8010`、OpenAPI `http://localhost:8010/docs`。若运行结果与本文档不一致，以源码和命令输出为准，并修正文档。

与用户沟通时使用中文直接回答，不复述问题；优先使用连续短段落，减少不必要的标题、列表和空行。
