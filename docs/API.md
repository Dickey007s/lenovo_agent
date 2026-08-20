# HTTP API 与 SSE 事件

本文记录 V0.1、Demo 1、`DR-0006` 报价核算、`DR-0007` Task 工件动作桥与 `DR-0008` Demo 2 Admission 纵切实际使用的 FastAPI 接口。运行后以 <http://localhost:8010/docs> 的 OpenAPI 页面和 `services/api/app/api/routes.py` 为最终事实来源。Demo 2 当前只提供固定工作队列、路由解释和路由选择，不启动 Worker 或外部动作。

## 1. 约定

- Base URL：`http://localhost:8010/v1`
- JSON：请求和普通响应均使用 UTF-8 JSON。
- SSE：流式接口返回 `text/event-stream`，并设置 `Cache-Control: no-cache`、`X-Accel-Buffering: no`。
- 身份头：`X-User-Id`，默认 `demo_user`。
- 角色头：`X-User-Roles`，英文逗号分隔，默认 `current_user`；前端 Demo 使用 `current_user,sales_manager`。
- Task 创建幂等头：`Idempotency-Key`，可选，长度 8-160。它作用于当前 Owner 的 `POST /tasks` 或 `POST /demo1/tasks`；后者用不同 key 区分独立汇报轮次。该 header 不会授权读取其他用户任务。
- Task 工件动作幂等头：`POST /tasks/{task_id}/artifacts/{artifact_version_id}/actions/email-send` 必须带 `Idempotency-Key`，长度 8-160。相同用户、相同 key 与完全相同的动作事实返回同一 Run；相同 key 对应不同工件事实时返回 409。
- Task mutation：`start` 和 `controls` 在 JSON body 中携带 `expected_task_version` 与 `idempotency_key`。版本过期或同一 key 被用于不同命令时返回 409。
- Workspace revision token：显式提交 `workspace_context` 时同时提交 `workspace_artifact_id + workspace_revision`；保存 `PUT /workspace/{kind}` 时提交 `expected_artifact_id + expected_revision`。这两个字段是当前活动 Artifact 的乐观并发 token，不是权限凭据。

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
| POST | `/tasks/{task_id}/start` | 仅进入 v2 `running / observe` |
| POST | `/tasks/{task_id}/advance` | 以一个 expected version + idempotency key 完成一个当前阶段 |
| POST | `/tasks/{task_id}/controls` | 提交任务或分支控制命令 |
| POST | `/tasks/{task_id}/artifacts/{artifact_version_id}/actions/email-send` | 将已提交、已通过验证的客户回复草稿准备为绑定版本的治理 Run；不会直接发送 |
| GET | `/tasks/{task_id}/events?after={sequence}` | 回放并订阅该 Task 的有序事件 SSE |

Task ID、Owner、契约版本、任务状态、分支状态、事件序号和时间均由服务端生成。客户端不能在 `TaskContractDraft` 中提交这些字段；多余字段返回 422。其他 Owner 的 Task 不会通过列表暴露，按 ID 读取或订阅时统一返回 404。

### 2.3 Demo 2 智能工作驾驶舱

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/demo2/cockpit` | 读取当前 Owner 的四项固定演示工作、Admission 建议和路由状态 |
| GET | `/demo2/work-items/{work_item_id}` | 读取当前 Owner 的单个固定演示工作项 |
| POST | `/demo2/work-items/{work_item_id}/route` | 以预期版本和幂等键记录本次执行方式；不启动实际执行 |

Demo 2 当前服务端为进程内 memory。API 重启后路由选择会回到固定初始状态；没有 SSE、数据库恢复、Worker 生命周期或跨实例通知。四项工作在每个 Owner 的独立固定队列中生成，普通 UI 只显示“演示数据”业务标签，不显示内部来源 ID。

### 2.4 场景、治理与审计

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
  "workspace_artifact_id": "artifact_demo_mail",
  "workspace_revision": 3,
  "workspace_context": {
    "to": ["client-a@example.com"],
    "cc": [],
    "subject": "项目 Alpha 方案确认",
    "body": "尊敬的客户 A：",
    "attachments": []
  }
}
```

`workspace_context` 是可选字段：省略或传 `null` 时，服务端使用已保存的活动 WorkspaceArtifact，此时不要求 revision token；显式传入对象时，表示浏览器当前未保存的视图，必须同时带当前 `workspace_artifact_id` 和 `workspace_revision`，缺任一字段返回 422。对于 `active_view="quote"`，显式 `{}` 不会回退到已保存报价，而是按无效当前上下文 fail closed。

报价上下文使用字段级信任边界。服务端保留 `quote_id`、`customer`、`currency`、`approved_floor`、每行 `unit_price`、`sources` 和既有审批事实；只从当前上下文接收等长行列表中的 `name`、`qty`、`discount` 以及顶层 `valid_until`。客户端提供的 `subtotal`、`total` 或服务端所有字段会被忽略，服务端按行重新规范化。行数不一致、字段缺失、比例越界或金额超限时，核算/处理路径拒绝猜测。

当活动视图为报价且消息属于核算、复算、最低折后比例检查或来源追问时，ConversationService 不调用 LLM 计算数值，而是用确定性 Decimal 计算器生成回复，再通过同一 Conversation SSE 发送。包含“写入、修改、保存、发送、创建、导入”等动作词的请求不会被该快捷路由截获，仍进入既有规划和治理路径。基线结果为标准总价 272000 元、折后总价 253400 元、优惠金额 18600 元、综合折后比例 93.16%（约 9.32 折）、优惠率 6.84%。

`ChatMessage.processing` 记录本次回答的处理来源：`deterministic_formula`、`language_model` 或 `policy_engine`，并带可读 `label`、真实 `elapsed_ms` 与可选 `model`。它只描述生成该条回答的服务端路径，不是思维链、任务总时长或供应商 SLA。模型路径在真实 HTTP 等待前发送 `assistant.status(status=model_call)`；服务端日志同时记录 `path/model_called/model/elapsed_ms/thread_id/active_view`，不记录消息正文或 Key。不得为了“像 AI”人为延迟确定性路径。

PowerShell 中可用 `curl.exe -N` 直接观察 SSE：

```powershell
$mailArtifact = Invoke-RestMethod -Method Get -Uri "$base/workspace" -Headers $headers |
  Where-Object { $_.kind -eq "mail" }
$body = @{
  message = "读取当前邮件草稿，补全正文并准备发送"
  active_view = "mail"
  workspace_artifact_id = $mailArtifact.artifact_id
  workspace_revision = $mailArtifact.revision
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
  "expected_artifact_id": "artifact_demo_mail",
  "expected_revision": 3,
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

保存成功后响应返回递增的 `revision`。服务端只在 `expected_artifact_id/revision` 与当前活动 Artifact 一致时写入；旧 token 返回 409，不覆盖新版本。当前 Web 会保留未保存草稿、重新 `GET /workspace`，并显示“查看最新版本 / 重新应用我的修改”。重新应用使用编辑起点、本地草稿和服务端最新版本做有界三方比较：不同字段修改可合并，同一字段双方都改动或行结构变化时停止自动合并并列出冲突字段。该行为不是通用多人协作或数据库级 CAS；锁与 revision 比较当前只在单个 API 进程内。

保存已绑定动作的 Artifact 会让旧动作失效，并返回 `requires_recheck=true`。`mail/new` 返回新的空白 Artifact，不是清空旧对象后复用其动作 ID。

保存 `quote` 时同样应用上述服务端字段所有权与确定性重算。相对服务端基线修改 `name/qty/discount/valid_until` 后，响应中的 `content.approval.status` 为 `needs_review`，并返回 `requires_recheck=true`；旧小计/总计不会被保存为权威值。报价字段非法时返回 422，不会持久化部分总计。

当 Conversation 规划产生 ArtifactDraft 或注册 capability 的 ActionCandidate 时，服务端不信任模型提交的 `sources`、动作参数、目标范围、数据分类、状态变化类型和可逆性。更新已有 Artifact 时保留服务端来源，新 Artifact 使用服务端默认来源；可执行动作的收件人、附件、正文和治理字段从当前 Artifact 与 capability 重新构造，`source_refs` 不接受模型自报。内容或 capability 不匹配时不创建动作。无法解析的纯文本姓名或畸形邮箱产生 `RECIPIENT_IDENTITY_UNRESOLVED`，不透明附件产生 `ATTACHMENT_DATA_CLASS_UNRESOLVED`；ControlPlan 确定性 `DENIED`，用户在 evidence 接口自报同一姓名/哈希也不能解锁。格式合法的邮箱与可按演示规则分类的报价附件仍沿正常 Evidence、Approval、Permit 与 Simulator 链路。若活动或目标 Artifact 在规划期间改变，流返回 `workspace.conflict`，不覆盖内容也不产生 `action.proposed`。

### 3.4 创建、启动与控制 Demo 1 Task

固定 Demo 1 创建入口不需要请求体。前端每次显式开始新一轮汇报时发送新的 `Idempotency-Key`；同一轮重试复用同一个 key，因此不会重复创建，下一轮换 key 后会保留旧 Task 并创建新的 `ready / contract` Task。创建 key 重放返回该 Task 当前已持久化的 Snapshot，不回退到最初 `ready` 响应；这与 start/control mutation 返回“首次 mutation 结果”的幂等语义不同。为了兼容旧客户端，不传 header 时仍使用每个 Owner 的稳定默认键：

```powershell
$roundHeaders = $headers.Clone()
$roundHeaders["Idempotency-Key"] = "demo1-round-20260810-001"
$task = Invoke-RestMethod -Method Post -Uri "$base/demo1/tasks" -Headers $roundHeaders
$task.task_id
Invoke-RestMethod -Method Get -Uri "$base/tasks/$($task.task_id)" -Headers $headers
```

完成一轮后，把 key 改为新的轮次值会创建另一项独立 Task。相同 Owner+key 始终定位同一 Task 并返回其当前持久化 Snapshot；不同 key 生成不同 Task ID。当前 Web 的“开始新一轮汇报”是客户端组合动作：先调用本接口创建新 Task，再以新 Task 的版本调用 `/tasks/{task_id}/start`，随后按 Snapshot 确认逐次调用 `/tasks/{task_id}/advance`。它不会把旧 Task 重置为 `ready`。Task 列表按更新时间倒序返回，前端刷新时优先恢复未终止 Task，否则显示最近终态 Task；列表虽然保留多轮 Snapshot，当前 Web 尚无历史轮次选择入口。

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

当前 `start` 只把 Snapshot 从 v1 `ready / contract` 推进到 v2 `running / observe`，不调用 LLM。浏览器再调用 `advance`，每次只完成当前阶段：v3 `plan`、v4 `act`、v5 `verifying / verify`、v6 `waiting_input / verify`。v6 的固定事实是 5 个 ArtifactVersion、1 个 open Conflict、2 个 passed VerificationReport；`resolve_evidence` 成功后为 v7 `committed / commit`。固定渐进路径要求完整 Demo 契约匹配，包括预算与截止时间。Plan/Act 的严格模型调用发生在 CAS 之前，只有与服务端批准模板逐字段一致的文字才可记录为 `model`，否则使用 `template_fallback`；冲突时结果丢弃，Observe/Verify/Commit 为确定性逻辑。

控制请求统一提交到 `/tasks/{task_id}/controls`：

```json
{
  "kind": "resolve_evidence",
  "branch_id": "branch_...",
  "resolution_option_id": "use-official-crm-revenue",
  "selected_source_ref": "fixture:crm/customer-a:official-revenue-v3",
  "expected_task_version": 6,
  "idempotency_key": "resolve-demo1-001"
}
```

当前固定路径允许 `steer`、`pause_branch`、`resume_branch`、`take_over`、`return_control` 和 `resolve_evidence`。分支控制返回 `ControlEvent.status=applied` 后才改变前台状态；`steer` 当前只记录为 `accepted`，没有 `applied_task_version`，也不会在本次请求内重新规划，因此只能反馈“方向指令已记录，等待后续循环应用”。当前 Conflict 还返回服务端批准的 `resolution_options[]`；前端提交其中的 `resolution_option_id` 和匹配来源。`resolve_evidence` 只接受契约内的 CRM 正式收入 Fixture：服务端先追加通过验证的经营分析 v2。若解决后仍有其他 open Conflict，本次只持久化该 resolution、经营分析 v2、passed VerificationReport 和 partial `impact_receipt`，任务保持 `waiting_input / verify`；只有已经不存在其他 open Conflict 时，服务端才联动重生成并验证客户回复 v3，生成 Commit，并在 ControlEvent 中写实际工件、验证、Commit、版本和 `external_side_effect=none` 的回执。

mutation 合约要求：相同 key 和相同命令返回首次 mutation 的 Snapshot，且不新增事件、ArtifactVersion 或 Commit；相同 key 被用于不同命令返回 409。内存 Store 回归已覆盖旧 key 在后续 mutation 之后仍返回原响应、Artifact lineage/head 引用、内容摘要和 Commit state hash。PR 5 又在 PostgreSQL 16.14 上跨三个顺序 API 进程验证：旧 start key 返回原 v2、旧 resolve key 返回原 v3，当前 GET 保持 v3，重放前后数据库维持 `45 events / 7 artifacts / 1 TASK_COMMITTED`。历史遗留 marker 若没有保存原 Snapshot，只在当前 Task version 仍等于 marker version 时兼容返回；发生过后续 mutation 时返回 409，而不是错误返回最新 Snapshot。

每次 `start/advance/resolve_evidence` 都按当前契约预留步骤、工具调用和运行时长；预计用量超过预算或已到 `deadline_at` 时返回 409 且不产生 mutation。该预算不是 token 成本，也不提供供应商账单事实。浏览器关闭不会触发后台继续执行；同进程相同 advance key 有锁保护，跨实例没有分布式 LLM lease。

PR 4 交付物工作区直接使用创建、读取、start、control 和 SSE 对账所返回的同一个 `TaskSnapshot`：

- `branches[].artifact_heads` 决定每个交付物的当前 head；Task 面板只会打开该映射指向的服务端版本。
- `artifact_versions[]` 提供不可变版本、`parent_version_id`、结构化 `content` 与 `source_refs`。
- `verification_reports[]` 与 `conflicts[]` 提供验证和冲突事实；来源与逐项检查在前台默认折叠。
- `last_commit` 提供 task version、工件/报告引用和 `state_hash`；缺少该字段时前台不得显示最终提交。

该工作区当前只读，没有创建、编辑或覆盖 ArtifactVersion 的路由。前端只为固定 Fixture 的 `analysis/risk_brief/reply_draft` 提供字段 allowlist，未知 kind/字段默认隐藏；Conflict Card 与 Artifact Workspace 复用同一 `source_ref` 投影，四个已知值显示为“演示数据 · 业务来源（版本）”。服务端响应仍包含原始 `source_refs` 供控制校验和审计，但普通业务 DOM 使用与原值无关的序号 key，不接收 `fixture:` 原值；其他值统一显示隐藏占位，URL、路径和凭据形态已有负例回归。这是前端第二道投影，不能替代服务端脱敏、授权或未来通用的字段可见性 Schema。即使字段名在 allowlist 中，其任意文本值仍需要服务端 display projection 承担通用安全保证。

### 3.5 读取 Demo 2 驾驶舱并记录本次路由

```powershell
$cockpit = Invoke-RestMethod -Method Get -Uri "$base/demo2/cockpit" -Headers $headers
$customerA = $cockpit.items | Where-Object work_item_id -eq "customer_a_operating_review"
$route = @{
  mode = "fixed_workflow"
  scope = "this_run"
  expected_version = $customerA.version
  idempotency_key = "demo2-route-example-001"
} | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri "$base/demo2/work-items/$($customerA.work_item_id)/route" `
  -Headers $headers -ContentType "application/json" -Body $route
```

响应为 `RouteSelectionResult`，其中 `cockpit_version` 与 `cockpit_last_event_sequence` 是服务端提交后的驾驶舱聚合版本，`item` 是新的 `WorkItemSnapshot`。前端不得用工作项版本自行推算驾驶舱版本。接受服务端推荐时 `selection_source="admission"`；选择其他允许方式时为 `selection_source="user_override"` 且 `override_scope="this_run"`。两种情况都保持 `execution_status="not_started"`。相同 Owner、工作项、幂等键和命令返回原结果；相同 key 对应不同命令、`expected_version` 过期、选择不在 `allowed_modes` 内、用新 key 重复确认当前模式或对应 route profile/impact preview 缺失时返回 409，版本不增加。

每个 `RouteProfile` 可以携带服务端 `impact_preview`：`changes[]` 依次描述工作分配、协调与等待、人工介入、规则预测、执行边界和外部动作边界；`execution_status_before/after` 当前均为 `not_started`，`external_side_effect="none"`。旧 Snapshot 缺失该字段时仍可读取，但新选择若没有对应 preview，服务端拒绝 mutation，前端也不得自行补造影响。

选择成功后的 `RouteSelectionResult.item.selection_receipt` 是最新独立服务端事实，`selection_receipts[]` 按 cockpit/item 版本连续保留当前 memory Snapshot 内的改选历史；只有 latest receipt 的旧 Snapshot 会归一化为一条历史。回执包含版本前后、最终模式、`selection_source`、`override_scope`、固定规则预测和实际记录的 `changes[]`。它证明路由选择已应用，不证明 Agent、协作单元或外部动作已启动；相同幂等命令重放返回同一 receipt，随后 GET 在同一 API 进程内读回同一 receipt。

该 POST 走确定性 `policy_engine`，不调用 LLM。前台主动作因此使用“记录本轮方式”，而不是“执行”；服务端 runtime log 记录 `model_called=false` 与实际毫秒耗时。未来只有新增真实启动协议、执行事件和 Worker/Connector 事实后，才能出现“启动协作”动作。

`route_profiles[].forecast` 只有 `estimated_tool_calls`、`estimated_runtime_seconds` 和 `max_workers` 三个固定规则预测字段。它们不是模型账单、实际耗时、生产 SLA 或已经创建的 Worker 数。

### 3.6 从已验证 Task 工件准备治理 Run

```powershell
$prepareHeaders = $headers.Clone()
$prepareHeaders["Idempotency-Key"] = "task-action-$([guid]::NewGuid())"
$body = @{ thread_id = $thread.thread_id } | ConvertTo-Json

$run = Invoke-RestMethod -Method Post `
  -Uri "$base/tasks/$taskId/artifacts/$artifactVersionId/actions/email-send" `
  -Headers $prepareHeaders -ContentType "application/json" -Body $body
```

该接口只接受当前 Owner 的 `committed` Task 中、被 `last_commit.artifact_version_ids` 引用且具有 `passed` VerificationReport 的 `reply_draft`。它根据服务端工件主题和正文构建固定演示邮件动作，并在 `ProposedActionSpec.task_artifact_binding` 中绑定：

```text
task_id / task_version / commit_id / commit_state_hash
artifact_id / artifact_version_id / artifact_version / artifact_content_digest
deliverable_id / verification_report_id
```

响应是 `RunSnapshot`，通常为 L4 外部动作并进入人工审批，不表示已经发送。前台在准备成功后打开 Action Gate，说明绑定成果、目标、为什么需要确认，以及拒绝不会改变已提交 Task。审批和最终授权前，RunService 会重新读取 Task 并核对全部绑定事实；Task、Commit、工件摘要或验证事实不一致时旧 Run 失效。拒绝、授权失败或 Simulator 执行失败都不会回滚或改写 Task Commit。

该接口不调用 LLM 生成收件人、主题或正文；收件人固定为演示地址 `customer@example.com`。当前没有真实联系人选择、附件映射、批量发送或真实 Connector。客户端只在请求结果未知时复用同一准备 key；收到确定成功或确定 4xx 后清除 key，下一次用户意图使用新 key。

### 3.7 直接创建治理 Run

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
control_plan / permit / tool_result / impact_preview / execution_receipt
created_at / updated_at
```

`impact_preview` 与 `execution_receipt` 是 `DR-0012` 的服务端字段对象，分别包含 `items[]`。每个 `ImpactItem` 使用 `item_id/change_kind/label/before/after`，并固定映射 `target-change→will_change`、`binding-recheck→will_recheck`、`task-preserved→unchanged`、`real-connector-not-called→no_external_action`。前者由服务端在 Action、Risk、Policy、Evidence 和 ControlPlan 评估后生成，后者只在治理事件或 `ToolExecutionResult` 产生后生成。前端不得将 preview 复制成 receipt，也不得从按钮点击、颜色或动画推断执行结果。

### 3.8 补证据、审批和最终授权

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
| `workspace.conflict` | 请求携带的 Artifact/revision 已过期，或规划期间活动/目标 Artifact 改变；包含 `view` 与最新 `latest_artifact` |
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

报价确定性回答仍使用 `message.created → assistant.status(status=calculating) → message.started → assistant.delta* → message.completed`。事件顺序表示同一 Thread 中已接受消息和完成回答，不把客户端即时总计升级为审批或持久化事实。同一 API 进程会串行同一 Thread 的消息流以避免相互覆盖，但 Thread/Message 仍不跨进程持久化，也没有 Conversation SSE 断线游标。

`workspace.conflict` 是 SSE 已开始后的可恢复业务冲突，不等同于通用 `error`。当前 Web 保留本地输入，以事件中的最新 Artifact 提供显式查看或三方重应用；服务端随后发送一条说明“未生成或执行动作”的完成消息。即使请求发出时 revision 有效，用户也可能在等待流期间继续编辑；Web 为每次请求记录当时的 Artifact 与本地 edit token，晚到 `artifact.updated` 只在不同字段时自动三方合并，同字段双改转入相同冲突 UI。

动作达到 `EXECUTED / DENIED / FAILED` 后，`POST /threads/{thread_id}/runs/{run_id}/continue/stream` 才会生成结果说明。Conversation 创建 Run 时将真实 `thread_id` 写入 RunSnapshot；continue 要求 URL 中的 Thread 与 Run 绑定一致，即使同一用户也不能把结果续写到另一条对话。若生成说明前发生暂时失败，前端保留“重新读取结果”入口；一旦某个 `(thread_id, run_id)` 已完成，同一 API 进程内重试会重放同一个 `message.completed` 与 `action.closed`，不会再次调用模型或向 Thread 追加第二条完成消息。前端按 `message_id` upsert。该重放缓存与 Thread 一样不跨 API 进程持久化。

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

普通业务审计工作台不是原始事件查看器：前端必须把 `event_type`、`payload`、`trace`、`email_simulator`、`email.send`、`PERMIT_ISSUED` 和 `Permit` 投影为可读业务标签与服务端摘要，不得把原值渲染进普通业务 DOM。原始事件仍由 API/服务端审计保留，只有受控技术审计视图可查看。

Demo 3 Action Gate 使用 RunSnapshot 和上述有序事件投影“动作影响账本”。预演固定显示“会改变 / 会重新核对 / 保持不变 / 不会发生”；`TOOL_EXECUTED` 的结果必须标记为 Simulator 结果，不能表述为真实邮箱、CRM、OA、日历或任务系统写入。`ACTION_INVALIDATED`、`TAMPER_BLOCKED`、拒绝和 `FAILED` 都必须显示动作未产生真实外部影响，并保留已完成 Task/Artifact/Commit 不变。固定 Demo 3 工程纵切已由 Python `151 passed, 1 skipped in 3.69s`、完整浏览器 `37 passed (2.2m)`、Ruff、governance、lint 和 build 验证；视觉终验无 P0/P1。实现提交为 `9335470`，文档提交为 `34aee71`，对应 [PR #18](https://github.com/Dickey007s/lenovo_agent/pull/18)。跨进程执行幂等/Permit replay、多实例/数据库恢复、真实 Connector 和用户理解不在该结论内。

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
| 404 | Thread、Artifact、Run、Action、Scenario、Trace、Task 或 Demo 2 WorkItem 不存在，或不属于当前用户 |
| 409 | 授权条件未满足、动作已失效、Permit/Gateway 拒绝，Workspace Artifact/revision 过期，Task 或 Demo 2 WorkItem 版本过期、状态转换/路由非法、Task 工件绑定已变化，或幂等键被用于不同契约/命令/动作事实 |
| 422 | 请求 Schema、TaskContractDraft、证据值、报价当前字段或模型结构化输出无效 |
| 503 | LLM endpoint、Key 或模型配置不可用 |

SSE 在响应已经开始后无法再改变 HTTP 状态码，因此流内错误使用 `event: error` 和 `detail`。客户端应同时处理 HTTP 错误与流内错误。

## 8. 兼容性规则

- 请求模型均 `extra="forbid"`；新增顶层字段会破坏旧服务端，协议变更需同步前端和文档。
- Task Runtime 当前使用 `schema_version="1.0"`；Python 权威模型在 `packages/contracts/task_models.py`，前端镜像在 `apps/web/app/task-types.ts`。
- Demo 2 Python 权威模型在 `packages/contracts/demo2_models.py`，前端镜像在 `apps/web/app/demo2-types.ts`；当前没有公开 schema version 或持久化迁移协议。
- V0.1 没有公开版本协商；`/v1` 是唯一 API 版本。
- `ActionCandidate`、Permit claims 和哈希规则是安全边界，不能由前端自行构造并绕过 RunService。
- 文档示例中的邮箱、报价号、用户和 Key 全部是演示值。
- 报价来源回答中的 CRM/政策标签同样是固定演示数据；接口没有访问真实 CRM、CPQ 或 ERP。当前报价公式不覆盖税费、汇率、阶梯价或跨行套餐依赖。
- Workspace revision 目前不是数据库原子 compare-and-swap；多 API 实例并发写、跨实例锁和 Conversation 结果重放均未实现或验证。

Task API 当前只把上述能力暴露给固定 Demo 1 Fixture。PR 4 浏览器 E2E 覆盖创建、start、冲突、Steer accepted、resolve、Commit、交付物读取，以及 start 请求发送前 abort 后的 reload/同 key 重试。PR 5 在 PostgreSQL 16.14 和三个顺序 API 进程上验证 v2/v3 Snapshot、Artifact 和 Commit 恢复及幂等零重复；同页 system Edge 运行验证 API 停止、控制禁用、连接文案和新进程后的 GET 对账。DR-0007 进一步验证了一条窄桥：最终客户回复草稿可按 Task/Commit/Artifact/Verification 精确绑定到 `email.send` 治理 Run，批准后仍只执行 Simulator。它不等于通用 Task Artifact 动作框架，也没有验证 Task 或数据库重启后的 Run 幂等恢复、真实收件人目录、真实邮件 Connector、附件、批量动作或用户价值。Task Control 仍不能直接发送邮件或写入企业系统；副作用必须经过 RunService、Policy/Evidence/Approval、Permit 与 Tool Gateway。其他未覆盖边界仍包括请求已到服务端但响应丢失、断线期间事件回放、数据库进程故障、多实例通知和历史轮次 UI。非 Tasks 工作区是否展示决定控制、按钮叫什么以及“开始新一轮汇报”如何串联 create/start 都是客户端交互，不是新的 API 能力。自动化通过也不能证明普通用户理解这些语义。证据见 [`PR 4 Frontend E2E`](evidence/DEMO1-PR4-FRONTEND-E2E-EVIDENCE.md)、[`PR 5 PostgreSQL-backed API Restart`](evidence/DEMO1-PR5-POSTGRES-BACKED-API-RESTART-EVIDENCE.md) 与 [`DR-0007 Task Artifact Action Bridge`](evidence/DEMO1-DEMO3-TASK-ARTIFACT-ACTION-BRIDGE-EVIDENCE-20260813.md)。

## 9. Demo 1 当前渐进协议（2026-08-17）

以下覆盖旧版“start 一次物化终态”的描述：

| 请求 | 成功结果 |
| --- | --- |
| `POST /v1/demo1/tasks` | v1 `ready / contract`，无工件 |
| `POST /v1/tasks/{id}/start` | v2 `running / observe`，仅完成 Observe 入口 |
| 第一次 `advance` | v3 `running / plan` |
| 第二次 `advance` | v4 `running / act` |
| 第三次 `advance` | v5 `verifying / verify` |
| 第四次 `advance` | v6 `waiting_input / verify`，5 工件、1 open conflict、2 passed verification |
| `resolve_evidence` | v7 `committed / commit`，写入最终 `TaskCommit` |

每次 mutation 都要求 `expected_task_version` 和命令级 `idempotency_key`；成功只前进一个 version，重复 key 重放首次 Snapshot，旧 version 返回 409。Task SSE 只发现事件，客户端随后 GET Snapshot；没有后台 worker。`stage_records` 是业务 UI 的权威阶段事实，旧 Snapshot 缺失该字段时按空数组兼容读取，不自动伪造渐进过程。
