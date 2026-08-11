# HTTP API 与 SSE 事件

本文记录 V0.1 与 Demo 1 PR 4 实际使用的 FastAPI 接口。运行后以 <http://localhost:8010/docs> 的 OpenAPI 页面和 `services/api/app/api/routes.py` 为最终事实来源。PR 4 没有增加工件专用 API；交付物工作区读取现有 `TaskSnapshot`。

## 1. 约定

- Base URL：`http://localhost:8010/v1`
- JSON：请求和普通响应均使用 UTF-8 JSON。
- SSE：流式接口返回 `text/event-stream`，并设置 `Cache-Control: no-cache`、`X-Accel-Buffering: no`。
- 身份头：`X-User-Id`，默认 `demo_user`。
- 角色头：`X-User-Roles`，英文逗号分隔，默认 `current_user`；前端 Demo 使用 `current_user,sales_manager`。
- Task 创建幂等头：`Idempotency-Key`，可选，长度 8-160。它作用于当前 Owner 的 `POST /tasks` 或 `POST /demo1/tasks`；后者用不同 key 区分独立汇报轮次。该 header 不会授权读取其他用户任务。
- Task mutation：`start` 和 `controls` 在 JSON body 中携带 `expected_task_version` 与 `idempotency_key`。版本过期或同一 key 被用于不同命令时返回 409。

上述身份头没有签名，只是 P0 占位。生产环境必须在 API 边界替换为经过验证的 SSO/JWT，并从可信身份声明映射角色。

```powershell
$base = "http://localhost:8010/v1"
$headers = @{
  "X-User-Id" = "demo_user"
  "X-User-Roles" = "current_user,sales_manager"
}
```

## 2. 接口总览

### 2.1 健康与工作区对话

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/health` | 返回服务、模型名、checkpoint backend 和 `task_store` backend |
| POST | `/threads` | 为当前用户创建内存对话 Thread |
| GET | `/threads/{thread_id}` | 读取 Thread、Message 和关联 Artifact |
| POST | `/threads/{thread_id}/messages/stream` | 提交消息并流式返回对话、工作区和动作事件 |
| POST | `/threads/{thread_id}/runs/{run_id}/continue/stream` | 动作状态变化后由 Agent 流式反馈结果 |
| GET | `/workspace` | 读取当前用户全部活动 WorkspaceArtifact |
| POST | `/workspace/mail/new` | 创建新的空白邮件 Artifact |
| PUT | `/workspace/{kind}` | 保存某类工作区当前内容 |
| PUT | `/threads/{thread_id}/artifacts/{artifact_id}` | 更新 Thread 关联 Artifact；保留用于兼容对话产物 |

`kind` 仅允许：`mail`、`document`、`quote`、`tasks`、`calendar`、`expense`、`crm`。

### 2.2 Demo 1 Task

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/demo1/tasks` | 为当前用户幂等创建固定客户 A Task Contract；可用 `Idempotency-Key` 区分独立汇报轮次 |
| POST | `/tasks` | 从 `TaskContractDraft` 创建服务端 Task；可带 `Idempotency-Key` |
| GET | `/tasks` | 按更新时间倒序列出当前 Owner 的 TaskSnapshot |
| GET | `/tasks/{task_id}` | 读取当前 Owner 的单个 TaskSnapshot |
| POST | `/tasks/{task_id}/start` | 启动固定 Demo 1 Fixture 状态转换 |
| POST | `/tasks/{task_id}/controls` | 提交任务或分支控制命令 |
| GET | `/tasks/{task_id}/events?after={sequence}` | 回放并订阅该 Task 的有序事件 SSE |

Task ID、Owner、契约版本、任务状态、分支状态、事件序号和时间均由服务端生成。客户端不能在 `TaskContractDraft` 中提交这些字段；多余字段返回 422。其他 Owner 的 Task 不会通过列表暴露，按 ID 读取或订阅时统一返回 404。

### 2.3 场景、治理与审计

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/demo3/scenarios` | 列出 4 个确定性治理场景 |
| GET | `/evidence/requirements` | 列出证据要求、输入类型与说明 |
| POST | `/demo3/scenarios/{scenario_id}/runs` | 从固定场景创建 Run，不调用 LLM |
| POST | `/runs` | 从自然语言解析 ActionCandidate 并创建 Run |
| GET | `/runs/{run_id}` | 读取 RunSnapshot |
| GET | `/runs/{run_id}/workflow` | 读取 LangGraph workflow 状态 |
| GET | `/runs/{run_id}/events?after={sequence}` | 订阅带序号的 Run 审计 SSE |
| GET | `/audit/{trace_id}` | 读取完整审计时间线 |
| POST | `/actions/{action_id}/evidence` | 提交缺失证据值并重新评估 |
| POST | `/actions/{action_id}/approvals` | 以当前用户拥有的角色批准或拒绝 |
| POST | `/actions/{action_id}/authorize` | 最终授权、签发 Permit 并调用 Gateway |
| POST | `/demo3/actions/{action_id}/tamper-check` | 演示参数被篡改时 Gateway 拒绝执行 |

## 3. 主要请求与示例

### 3.1 创建并读取对话

```powershell
$thread = Invoke-RestMethod -Method Post -Uri "$base/threads" -Headers $headers
$thread.thread_id
Invoke-RestMethod -Method Get -Uri "$base/threads/$($thread.thread_id)" -Headers $headers
```

`ConversationThread` 主要字段：`thread_id`、`user_id`、`title`、`messages[]`、`artifacts[]`、`created_at`、`updated_at`。

### 3.2 发送 Agent 消息

```json
{
  "message": "读取当前邮件草稿，补全正文并准备发送",
  "active_view": "mail",
  "workspace_context": {
    "to": ["client-a@example.com"],
    "cc": [],
    "subject": "项目 Alpha 方案确认",
    "body": "尊敬的客户 A：",
    "attachments": []
  }
}
```

PowerShell 中可用 `curl.exe -N` 直接观察 SSE：

```powershell
$body = @{
  message = "读取当前邮件草稿，补全正文并准备发送"
  active_view = "mail"
  workspace_context = @{
    to = @("client-a@example.com")
    cc = @()
    subject = "项目 Alpha 方案确认"
    body = "尊敬的客户 A："
    attachments = @()
  }
} | ConvertTo-Json -Depth 8 -Compress

curl.exe -N -X POST "$base/threads/$($thread.thread_id)/messages/stream" `
  -H "Content-Type: application/json" `
  -H "X-User-Id: demo_user" `
  -H "X-User-Roles: current_user,sales_manager" `
  --data-binary $body
```

### 3.3 保存工作区与新邮件

保存请求采用严格模型，不允许多余顶层字段：

```json
{
  "title": "客户 A 方案确认",
  "content": {
    "to": ["client-a@example.com"],
    "cc": [],
    "subject": "项目 Alpha 方案确认",
    "body": "邮件正文",
    "attachments": []
  }
}
```

```powershell
Invoke-RestMethod -Method Put -Uri "$base/workspace/mail" `
  -Headers $headers -ContentType "application/json" `
  -Body ($mail | ConvertTo-Json -Depth 8)

Invoke-RestMethod -Method Post -Uri "$base/workspace/mail/new" -Headers $headers
```

保存已绑定动作的 Artifact 会让旧动作失效，并返回 `requires_recheck=true`。`mail/new` 返回新的空白 Artifact，不是清空旧对象后复用其动作 ID。

### 3.4 创建、启动与控制 Demo 1 Task

固定 Demo 1 创建入口不需要请求体。前端每次显式开始新一轮汇报时发送新的 `Idempotency-Key`；同一轮重试复用同一个 key，因此不会重复创建，下一轮换 key 后会保留旧 Task 并创建新的 `ready / contract` Task。创建 key 重放返回该 Task 当前已持久化的 Snapshot，不回退到最初 `ready` 响应；这与 start/control mutation 返回“首次 mutation 结果”的幂等语义不同。为了兼容旧客户端，不传 header 时仍使用每个 Owner 的稳定默认键：

```powershell
$roundHeaders = $headers.Clone()
$roundHeaders["Idempotency-Key"] = "demo1-round-20260810-001"
$task = Invoke-RestMethod -Method Post -Uri "$base/demo1/tasks" -Headers $roundHeaders
$task.task_id
Invoke-RestMethod -Method Get -Uri "$base/tasks/$($task.task_id)" -Headers $headers
```

完成一轮后，把 key 改为新的轮次值会创建另一项独立 Task。相同 Owner+key 始终定位同一 Task 并返回其当前持久化 Snapshot；不同 key 生成不同 Task ID。当前 Web 的“开始新一轮汇报”是客户端组合动作：先调用本接口创建新 Task，再以新 Task 的版本调用 `/tasks/{task_id}/start`，固定路径通常直接返回 `waiting_input / verify`。它不会把旧 Task 重置为 `ready`。Task 列表按更新时间倒序返回，前端刷新时优先恢复未终止 Task，否则显示最近终态 Task；列表虽然保留多轮 Snapshot，当前 Web 尚无历史轮次选择入口。

也可以提交严格的 `TaskContractDraft`。下面只展示最小结构，实际字段和限制以 `packages/contracts/task_models.py` 为准：

```json
{
  "title": "客户 A 经营汇报",
  "objective": "形成带来源、版本和验证记录的经营分析。",
  "source_scope": ["fixture:crm/customer-a:official-revenue-v3"],
  "allowed_capabilities": ["crm.customer.read", "document.draft"],
  "deliverables": [
    {
      "deliverable_id": "operating-analysis",
      "title": "经营分析",
      "kind": "analysis",
      "completion_criteria": ["关键事实绑定允许来源。"]
    }
  ],
  "completion_criteria": ["必需交付物通过验证。"],
  "budget": {
    "max_steps": 12,
    "max_tool_calls": 30,
    "max_runtime_seconds": 3600
  },
  "deadline_at": null
}
```

```powershell
$taskHeaders = $headers.Clone()
$taskHeaders["Idempotency-Key"] = "customer-a-report-001"
Invoke-RestMethod -Method Post -Uri "$base/tasks" `
  -Headers $taskHeaders -ContentType "application/json" `
  -Body ($draft | ConvertTo-Json -Depth 10)
```

同一 Owner 使用相同 key 重放相同契约时仍返回 201 和已存在 Task 的当前持久化 Snapshot，不增加第二条 `TASK_CREATED`；相同 key 改用于不同契约返回 409。不传 key 时每次请求都会创建新的 Task。

创建后的状态为：`TaskSnapshot.status=ready`、`phase=contract`、`version=1`、`last_event_sequence=1`，每个交付物对应一个 `queued` Branch。`artifact_versions`、`verification_reports`、`conflicts`、`controls` 均为空，`last_commit=null`。

启动请求：

```json
{
  "expected_task_version": 1,
  "idempotency_key": "start-demo1-001"
}
```

```powershell
$start = @{
  expected_task_version = $task.version
  idempotency_key = "start-demo1-001"
} | ConvertTo-Json
$task = Invoke-RestMethod -Method Post -Uri "$base/tasks/$($task.task_id)/start" `
  -Headers $headers -ContentType "application/json" -Body $start
```

当前 `start` 仅物化固定客户 A Fixture，不调用 LLM 或真实 Connector。它在一次服务端 mutation 中追加阶段事件、五个 ArtifactVersion、三个 VerificationReport 和一个收入冲突；最终 Snapshot 进入 `waiting_input / verify`，只有经营分析分支为 `waiting_evidence`，另外两个固定分支为 `committed`。这些阶段事件在事务提交后才可见，不能解释成浏览器观察到了一个持续后台进程。

控制请求统一提交到 `/tasks/{task_id}/controls`：

```json
{
  "kind": "resolve_evidence",
  "branch_id": "branch_...",
  "selected_source_ref": "fixture:crm/customer-a:official-revenue-v3",
  "expected_task_version": 2,
  "idempotency_key": "resolve-demo1-001"
}
```

当前固定路径允许 `steer`、`pause_branch`、`resume_branch`、`take_over`、`return_control` 和 `resolve_evidence`。分支控制返回 `ControlEvent.status=applied` 后才改变前台状态；`steer` 当前只记录为 `accepted`，没有 `applied_task_version`，也不会在本次请求内重新规划，因此只能反馈“方向指令已记录，等待后续循环应用”。`resolve_evidence` 只接受契约内的 CRM 正式收入 Fixture：服务端先追加通过验证的经营分析 v2。若解决后仍有其他 open Conflict，本次只持久化该 resolution、经营分析 v2 和其 passed VerificationReport，任务保持 `waiting_input / verify`，不生成客户回复 v3 或 `TASK_COMMITTED`；只有已经不存在其他 open Conflict 时，服务端才联动重生成并验证客户回复 v3，再为全部必需 heads 生成 Commit。

mutation 合约要求：相同 key 和相同命令返回首次 mutation 的 Snapshot，且不新增事件、ArtifactVersion 或 Commit；相同 key 被用于不同命令返回 409。内存 Store 回归已覆盖旧 key 在后续 mutation 之后仍返回原响应、Artifact lineage/head 引用、内容摘要和 Commit state hash。PR 5 又在 PostgreSQL 16.14 上跨三个顺序 API 进程验证：旧 start key 返回原 v2、旧 resolve key 返回原 v3，当前 GET 保持 v3，重放前后数据库维持 `45 events / 7 artifacts / 1 TASK_COMMITTED`。历史遗留 marker 若没有保存原 Snapshot，只在当前 Task version 仍等于 marker version 时兼容返回；发生过后续 mutation 时返回 409，而不是错误返回最新 Snapshot。

`start` 会预留 4 个 step、4 次工具调用和 1 秒运行时长，`resolve_evidence` 会预留 1 个 step 和 1 秒运行时长；预计用量超过契约预算或已到 `deadline_at` 时返回 409，且不产生 mutation。当前还没有专门的预算耗尽恢复 API 或完整前台引导。

PR 4 交付物工作区直接使用创建、读取、start、control 和 SSE 对账所返回的同一个 `TaskSnapshot`：

- `branches[].artifact_heads` 决定每个交付物的当前 head；Task 面板只会打开该映射指向的服务端版本。
- `artifact_versions[]` 提供不可变版本、`parent_version_id`、结构化 `content` 与 `source_refs`。
- `verification_reports[]` 与 `conflicts[]` 提供验证和冲突事实；来源与逐项检查在前台默认折叠。
- `last_commit` 提供 task version、工件/报告引用和 `state_hash`；缺少该字段时前台不得显示最终提交。

该工作区当前只读，没有创建、编辑或覆盖 ArtifactVersion 的路由。前端只为固定 Fixture 的 `analysis/risk_brief/reply_draft` 提供字段 allowlist，未知 kind/字段默认隐藏；Conflict Card 与 Artifact Workspace 复用同一 `source_ref` 投影，四个已知值显示为“演示数据 · 业务来源（版本）”。服务端响应仍包含原始 `source_refs` 供控制校验和审计，但普通业务 DOM 使用与原值无关的序号 key，不接收 `fixture:` 原值；其他值统一显示隐藏占位，URL、路径和凭据形态已有负例回归。这是前端第二道投影，不能替代服务端脱敏、授权或未来通用的字段可见性 Schema。即使字段名在 allowlist 中，其任意文本值仍需要服务端 display projection 承担通用安全保证。

### 3.5 直接创建治理 Run

```json
{
  "message": "把当前报价邮件发送给客户 A"
}
```

`POST /runs` 会调用配置的 LLM 解析 ActionCandidate；缺失模型配置返回 503，结构化输出无法校验返回 422。需要稳定演示和测试时，优先使用 `/demo3/scenarios/{scenario_id}/runs`。

`RunSnapshot` 包含：

```text
run_id / trace_id / thread_id / user_id / user_message / trusted_context
status / action / risk / policy_effects / evidence / approvals
control_plan / permit / tool_result / created_at / updated_at
```

### 3.6 补证据、审批和最终授权

提交证据：

```json
{
  "values": {
    "recipient_identity": "client-a@example.com",
    "attachment_hash": "sha256:demo",
    "dlp_result": "pass"
  }
}
```

```powershell
Invoke-RestMethod -Method Post -Uri "$base/actions/$actionId/evidence" `
  -Headers $headers -ContentType "application/json" `
  -Body (@{ values = @{ recipient_identity = "client-a@example.com" } } |
    ConvertTo-Json -Depth 5)
```

提交审批：

```json
{
  "approver_role": "sales_manager",
  "decision": "approved"
}
```

服务端会验证 `approver_role` 是否存在于 `X-User-Roles`；缺少角色返回 403。拒绝决策会进入拒绝/终止状态，不能继续授权。

最终执行不带请求体：

```powershell
Invoke-RestMethod -Method Post -Uri "$base/actions/$actionId/authorize" -Headers $headers
```

前置条件不足、Permit 无法签发或 Gateway 校验失败返回 409。成功响应中的 `tool_result.simulator` 明确指出被调用的是 Simulator。

## 4. Conversation SSE

Conversation SSE 的事件集：

| event/type | 说明 |
| --- | --- |
| `message.created` | 已接受用户消息 |
| `assistant.status` | Agent 正在规划或继续执行的短状态 |
| `message.started` | 新建流式 Agent 消息 |
| `assistant.delta` | 追加 Agent 文本片段 |
| `message.completed` | Agent 消息终态 |
| `artifact.stream.started` | 工作区渐进更新开始 |
| `artifact.delta` | 工作区字段或列表项增量 |
| `artifact.updated` | WorkspaceArtifact 最终终态 |
| `ui.focus` | 建议前端聚焦的工作区 |
| `action.proposed` | 已创建 Run，打开人工确认卡 |
| `action.closed` | Run 已执行、拒绝或结束 |
| `error` | 当前流处理失败 |

示例帧：

```text
event: assistant.delta
data: {"type":"assistant.delta","message_id":"msg_xxx","delta":"正在准备邮件正文"}

event: action.proposed
data: {"type":"action.proposed","run":{...RunSnapshot...}}

```

客户端必须按空行分帧，不能假设一次网络读取正好对应一个事件。接到 `message.completed` 或 `artifact.updated` 时，应以完整服务端对象校准本地增量状态。

## 5. Run 审计 SSE

`GET /runs/{run_id}/events?after=0` 是另一条带顺序号的 SSE，用于确认卡和审计视图。事件格式：

```text
id: 168
event: CONTROL_PLAN_UPDATED
data: {"sequence":168,"event_id":"...","run_id":"...","trace_id":"...",...}

```

当前事件类型：

- `RUN_CREATED`
- `ACTION_PARSED`
- `EVIDENCE_SUBMITTED`
- `APPROVAL_RECORDED`
- `CONTROL_PLAN_UPDATED`
- `ACTION_INVALIDATED`
- `PERMIT_ISSUED`
- `TOOL_EXECUTED`
- `TAMPER_BLOCKED`

没有新事件时服务端发送 `: heartbeat` 注释。断线重连时把最后接收的 `sequence` 作为 `after`，只读取后续事件。审计流属于运行事实，不等同于 Conversation SSE 的视觉增量。

## 6. Task SSE

`GET /tasks/{task_id}/events?after=0` 先验证当前 Owner，再通过 Store 轮询回放 `sequence > after` 的事件。创建时先产生 `TASK_CREATED`；固定 Demo 1 start 和 control mutation 还会产生下列已注册事件：

- `TASK_STATUS_CHANGED`、`TASK_PHASE_CHANGED`、`TASK_COMMITTED`
- `LOOP_STEP_STARTED`、`LOOP_STEP_COMPLETED`、`BUDGET_UPDATED`
- `BRANCH_STATUS_CHANGED`
- `ARTIFACT_VERSION_CREATED`、`VERIFICATION_RECORDED`、`CHECKPOINT_COMMITTED`
- `CONFLICT_OPENED`、`CONFLICT_RESOLVED`
- `CONTROL_ACCEPTED`、`CONTROL_APPLIED`

SSE 帧格式为：

```text
id: 1
event: TASK_CREATED
data: {"sequence":1,"event_id":"task_evt_...","task_id":"task_...",...}
```

没有新事件时发送 `: heartbeat`。客户端只能通过 `after` 查询参数提交游标；当前路由不解析 `Last-Event-ID` 请求头。后台任务摘要和 Tasks 主视图收到新事件后重新 GET TaskSnapshot 对账，不把 SSE payload 自行推导成任务完成状态。

API 进程重启本身不写 `TASK_RESTORED`，也不改变 Task version 或 event sequence。PR 5 的同页浏览器路径在 EventSource error 时保留最后确认 Snapshot、禁用控制并显示恢复中；新进程可用后通过重新 GET 同一 Task 才恢复“已同步”。该路径没有在停机期间新增事件，不能扩展为 `after` 缺口回放证明。

SSE 目前由每个 API 进程轮询 TaskStore，没有 PostgreSQL `LISTEN/NOTIFY`、消息代理或跨实例广播层。共享数据库可能被不同进程轮询到，但多实例通知延迟、连接迁移和一致性均未验证，不能表述为已支持多实例实时更新。

## 7. 错误语义

| 状态码 | 含义 |
| --- | --- |
| 403 | 当前身份不拥有提交的审批角色 |
| 404 | Thread、Artifact、Run、Action、Scenario、Trace 或 Task 不存在，或不属于当前用户 |
| 409 | 授权条件未满足、动作已失效、Permit/Gateway 拒绝，或 Task 版本过期、状态转换非法、幂等键被用于不同契约/命令 |
| 422 | 请求 Schema、TaskContractDraft、证据值或模型结构化输出无效 |
| 503 | LLM endpoint、Key 或模型配置不可用 |

SSE 在响应已经开始后无法再改变 HTTP 状态码，因此流内错误使用 `event: error` 和 `detail`。客户端应同时处理 HTTP 错误与流内错误。

## 8. 兼容性规则

- 请求模型均 `extra="forbid"`；新增顶层字段会破坏旧服务端，协议变更需同步前端和文档。
- Task Runtime 当前使用 `schema_version="1.0"`；Python 权威模型在 `packages/contracts/task_models.py`，前端镜像在 `apps/web/app/task-types.ts`。
- V0.1 没有公开版本协商；`/v1` 是唯一 API 版本。
- `ActionCandidate`、Permit claims 和哈希规则是安全边界，不能由前端自行构造并绕过 RunService。
- 文档示例中的邮箱、报价号、用户和 Key 全部是演示值。

Task API 当前只把上述能力暴露给固定 Demo 1 Fixture。PR 4 浏览器 E2E 覆盖创建、start、冲突、Steer accepted、resolve、Commit、交付物读取，以及 start 请求发送前 abort 后的 reload/同 key 重试。PR 5 在 PostgreSQL 16.14 和三个顺序 API 进程上验证 v2/v3 Snapshot、Artifact 和 Commit 恢复及幂等零重复；同页 system Edge 运行验证 API 停止、控制禁用、连接文案和新进程后的 GET 对账。它仍没有覆盖请求已到服务端但响应丢失、断线期间事件回放、数据库进程故障、多实例通知或历史轮次 UI。Task Runtime 仍不是通用 LLM Agent Loop、后台队列或真实 Connector；Conversation Thread/Message 也不随 Task 恢复。副作用动作必须继续走 RunService 与 Tool Gateway，Task Control 不能直接发送邮件或写入企业系统，Task Artifact 也尚未绑定 Action 失效规则。非 Tasks 工作区是否展示决定控制、按钮叫什么以及“开始新一轮汇报”如何串联 create/start 都是客户端交互，不是新的 API 能力。自动化通过也不能证明普通用户理解这些语义。证据见 [`PR 4 Frontend E2E`](evidence/DEMO1-PR4-FRONTEND-E2E-EVIDENCE.md) 与 [`PR 5 PostgreSQL-backed API Restart`](evidence/DEMO1-PR5-POSTGRES-BACKED-API-RESTART-EVIDENCE.md)。
