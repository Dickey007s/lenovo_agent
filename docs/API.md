# HTTP API 与 SSE 事件

本文记录 V0.1 实际暴露的 FastAPI 接口。运行后以 <http://localhost:8010/docs> 的 OpenAPI 页面和 `services/api/app/api/routes.py` 为最终事实来源。

## 1. 约定

- Base URL：`http://localhost:8010/v1`
- JSON：请求和普通响应均使用 UTF-8 JSON。
- SSE：流式接口返回 `text/event-stream`，并设置 `Cache-Control: no-cache`、`X-Accel-Buffering: no`。
- 身份头：`X-User-Id`，默认 `demo_user`。
- 角色头：`X-User-Roles`，英文逗号分隔，默认 `current_user`；前端 Demo 使用 `current_user,sales_manager`。

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
| GET | `/health` | 返回服务、模型名和 checkpoint backend |
| POST | `/threads` | 为当前用户创建内存对话 Thread |
| GET | `/threads/{thread_id}` | 读取 Thread、Message 和关联 Artifact |
| POST | `/threads/{thread_id}/messages/stream` | 提交消息并流式返回对话、工作区和动作事件 |
| POST | `/threads/{thread_id}/runs/{run_id}/continue/stream` | 动作状态变化后由 Agent 流式反馈结果 |
| GET | `/workspace` | 读取当前用户全部活动 WorkspaceArtifact |
| POST | `/workspace/mail/new` | 创建新的空白邮件 Artifact |
| PUT | `/workspace/{kind}` | 保存某类工作区当前内容 |
| PUT | `/threads/{thread_id}/artifacts/{artifact_id}` | 更新 Thread 关联 Artifact；保留用于兼容对话产物 |

`kind` 仅允许：`mail`、`document`、`quote`、`tasks`、`calendar`、`expense`、`crm`。

### 2.2 场景、治理与审计

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

### 3.4 直接创建治理 Run

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

### 3.5 补证据、审批和最终授权

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

## 6. 错误语义

| 状态码 | 含义 |
| --- | --- |
| 403 | 当前身份不拥有提交的审批角色 |
| 404 | Thread、Artifact、Run、Action、Scenario 或 Trace 不存在，或不属于当前用户 |
| 409 | 授权条件未满足、动作已失效、Permit/Gateway 拒绝 |
| 422 | 请求 Schema、证据值或模型结构化输出无效 |
| 503 | LLM endpoint、Key 或模型配置不可用 |

SSE 在响应已经开始后无法再改变 HTTP 状态码，因此流内错误使用 `event: error` 和 `detail`。客户端应同时处理 HTTP 错误与流内错误。

## 7. 兼容性规则

- 请求模型均 `extra="forbid"`；新增顶层字段会破坏旧服务端，协议变更需同步前端和文档。
- V0.1 没有公开版本协商；`/v1` 是唯一 API 版本。
- `ActionCandidate`、Permit claims 和哈希规则是安全边界，不能由前端自行构造并绕过 RunService。
- 文档示例中的邮箱、报价号、用户和 Key 全部是演示值。
