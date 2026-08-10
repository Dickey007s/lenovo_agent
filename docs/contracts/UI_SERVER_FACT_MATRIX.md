# Demo 1 UI—服务端事实矩阵

> 状态：`Ready`。PR 3 已接入固定 Fixture 的 Branch、Conflict、Control 与最近 Commit；完整 Artifact Workspace、异常恢复、Task/Action 绑定和用户价值验证仍是后续目标。

## 1. 组件映射

| UI 状态或组件 | 用户含义 | 服务端权威字段 | Snapshot / SSE | 允许动作 | 失败与恢复 | 默认隐藏 |
| --- | --- | --- | --- | --- | --- | --- |
| Active Task Bar（已实现） | 当前服务端 Task 及客户端是否与 Snapshot 对账 | `TaskSnapshot.task_id/status/phase/version/contract.title/contract.objective/budget`；`sync_state` 仅是客户端传输状态 | 初始 `GET /tasks`；mutation 响应；Task SSE 触发 `GET /tasks/{id}` 对账 | 创建或查看 Demo 1 Task；Action Gate 打开时按钮禁用 | 初始化失败降级为 Task offline；SSE 错误进入 reconnecting 并优先重连当前 Task ID | Prompt、内部调度、幂等键、完整 Task JSON |
| Branch Status List（PR 3 已实现） | 哪些固定分支等待、暂停、接管或已提交 | `branches[].status/version/pause_reason/artifact_heads/issue_ids` | Snapshot、`BRANCH_STATUS_CHANGED` | Pause、Resume、Take over、Return control | 单分支错误只影响该行；版本过期后刷新 Snapshot | Worker 对话、内部计划文本 |
| Conflict Card（PR 3 已实现） | 哪个 Fixture 事实冲突、影响哪个分支、可选依据是什么 | `conflicts[].status/subject/summary/source_refs/candidate_values` | Snapshot、`CONFLICT_OPENED`、`CONFLICT_RESOLVED` | 采用固定 CRM 正式来源、Pause、Take over；候选值与 source_ref 默认折叠 | 只有服务端返回 resolved 后才移除；请求失败先对账 | 未授权来源正文、原始检索日志 |
| Task Artifact Workspace（目标） | 当前交付物版本、来源和验证结果 | `artifact_versions[]`、`verification_reports[]`、`branches[].artifact_heads` | `ARTIFACT_VERSION_CREATED`、`VERIFICATION_RECORDED`、`CHECKPOINT_COMMITTED` | 查看来源、版本历史、人工接管后编辑 | candidate/failed 不能显示为完成；旧 head 只读 | 原始模型上下文、完整工具参数 |
| Task Control（PR 3 部分实现） | 用户能否记录方向指令、暂停或接管固定分支 | `TaskSnapshot.version`、`controls[]`、Branch status、服务端允许转换 | `CONTROL_ACCEPTED`；分支控制另有 `CONTROL_APPLIED` | Steer、Pause branch、Resume、Take over、Return control | pending mutation 将原 key、intent 和预期版本写入当前标签页 `sessionStorage` 并冻结新控制；offline/reconnecting 时可同 key 对账，重放确认后再 GET 最新 Snapshot；`409` 后刷新并提示复核 | idempotency key、权限哈希 |
| Stream Health Badge（已并入 Task Bar） | 浏览器是否能读取并对账服务端 Snapshot | 客户端 `last_sequence/sync_state`，不属于业务状态 | EventSource open/error、新 TaskEvent、对账 GET | offline 可手动重新连接，reconnecting/pending 可立即对账；未同步时禁止 Task Control | 自动重连；优先 GET 当前 Task ID，连接后重新 GET Snapshot | 网络栈和内部重试日志 |
| Verified Commit Summary（PR 3 最薄实现） | 服务端是否已生成最近 Commit | `last_commit.summary/committed_at/state_hash/artifact_version_ids/verification_report_ids` | Snapshot、`CHECKPOINT_COMMITTED`、`TASK_COMMITTED` | 当前只查看摘要 | 没有服务端 Commit 时不得出现完成；引用与 hash 已有内存回归，PostgreSQL 待验 | 原始 Trace payload、签名和密钥 |
| Task Error Banner（部分实现） | mutation 是否被拒绝、过期或结果待确认 | HTTP 状态、重新 GET 的 Snapshot version；`last_error` 完整路径尚未实现 | mutation 响应与 Snapshot 对账 | 复核后重新提交 | `5xx` 只显示结果待确认；不凭客户端异常宣告失败 | 堆栈、内部服务地址、敏感参数 |
| Action Gate Tray | 某个副作用动作是否可执行 | 现有 `RunSnapshot.risk/control_plan/permit/tool_result` | 现有 Run API/SSE | 补证据、审批、Authorize | Gate 使用独立网格行；Task 面板保持挂载以保留草稿，但视觉隐藏、不可交互，Task Bar 操作也禁用；收起后行高缩至 58px；Artifact/Action 失效尚未绑定 | Permit token、策略内部秘密 |

PR 3 UI 展示的是固定 Demo 1 的服务端状态，不是通用 Agent 执行器。不存在于 Snapshot/TaskEvent 的进度、验证、控制或完成事实仍不得由前端文案、颜色或 Toast 补造。

## 2. 状态文案与颜色不是事实

前端可把服务端枚举翻译为中文，但不能改变语义：

| 服务端状态 | 建议中文 | 用户可做什么 | 禁止推断 |
| --- | --- | --- | --- |
| Task `running` | 任务运行中 | 查看分支、Steer、暂停或接管 | 不能按动画估算完成比例 |
| Task `waiting_input` | 等待你的决定 | 处理冲突或接管 | 不能把单分支等待写成整任务失败 |
| Task `paused` | 已暂停 | Resume 或 Take over | 不能声称后台仍在执行 |
| Task `taken_over` | 由你接管 | 当前只能归还控制 | PR 3 尚无人工编辑并创建新 ArtifactVersion 的闭环 |
| Task `verifying` | 正在验证 | 查看候选工件，等待结果 | candidate 不能显示已完成 |
| Task `committed` | 已验证并提交 | 查看 Commit、工件和 Trace 摘要 | 必须同时存在服务端 Commit 事实 |
| Branch `waiting_evidence` | 此分支等待依据 | 解决冲突、Pause 或 Take over | 其他分支状态保持独立 |
| Branch `failed` | 此分支失败 | 查看原因、从 Commit 恢复或接管 | 不自动覆盖为整个 Task failed |

颜色、图标、进度条、动效、Toast 和按钮 disabled 状态都是 UI 表达，不能成为风险、预算、验证、执行或完成的权威来源。

## 3. 控制提交时序（PR 3 当前）

```mermaid
sequenceDiagram
    participant U as 用户
    participant UI as Web
    participant API as Task API
    participant S as TaskService
    participant DB as Durable Store

    U->>UI: Steer / Pause / Take over
    UI->>API: command + expected_task_version + idempotency_key
    UI-->>U: 显示“正在提交”，业务状态不变
    API->>S: 校验身份、状态转换、版本与幂等
    S->>DB: 原子写 Snapshot + ControlEvent + TaskEvent
    DB-->>S: commit
    S-->>UI: 新 TaskSnapshot
    alt 分支控制已应用
        S-->>UI: 新 Snapshot + CONTROL_APPLIED
        UI-->>U: 按服务端版本更新状态
    else Steer 仅被接受
        S-->>UI: 新 Snapshot + CONTROL_ACCEPTED
        UI-->>U: 显示“已记录，等待后续循环应用”
    end
```

服务端返回 `409` 时，UI 必须读取最新 Snapshot，并让用户看到哪些字段发生变化；不得用旧 version 自动重试含义可能已经改变的命令。PR 3 当前会显示已刷新到的 version，但字段级变更摘要和重新应用入口仍未完成。

## 4. 断线、过期与恢复

1. **断线**：显示“更新暂时中断，以最后确认状态为准”；保留最后确认 Snapshot，停止模拟进度，禁用新的控制提交。固定 PR 3 路径没有可据此声称仍在推进的后台 worker。
2. **重连**：使用 `after=last_sequence` 回放，随后 GET Snapshot；重复事件按 `task_id + sequence` 去重。
3. **序号缺口**：若下一事件不是 `last_sequence + 1`，立即标记 `reconciling` 并以 Snapshot 覆盖本地投影。
4. **旧版本**：`409` 后不改变业务状态，展示服务端当前 version、变更摘要和重新应用入口。
5. **身份过期**：`401/403` 后转只读，保留未提交 Steer 文本但不自动重放。
6. **服务重启**：这是 PostgreSQL 模式的待验收目标。内存模式只在同一 Store 对象存活时可恢复，进程退出后数据丢失。
7. **请求超时/5xx**：先显示“结果待确认”，把原 key、intent 和预期版本保存在当前标签页；offline/reconnecting 时允许同 key 确认首次结果，再 GET 最新 Snapshot，不能直接用历史幂等响应覆盖当前状态。reload 后入口始终可达仍待 E2E。

当前 EventSource 只通过 `after` 查询参数传递游标，不使用 `Last-Event-ID`；服务端轮询 TaskStore，没有跨实例通知总线。PR 3 前端会在连接打开或收到事件后重新 GET Snapshot，在连接错误后自动重试，并对 mutation 409/未知结果重新读取 Snapshot；pending mutation 数据可从同一标签页的 `sessionStorage` 恢复，但其对账入口在 reload 后始终可达尚未证明。序号缺口、身份过期、完整失败恢复、刷新恢复和进程重启仍未完成浏览器 E2E。

## 5. 实现与验证责任

| PR | 前台最小输出 | 后端事实 | 必须提供的证据 |
| --- | --- | --- | --- |
| PR 1 | 只定义 TypeScript 类型与本矩阵，不宣称页面已实现 | Pydantic 目标协议 | 严格 Schema 测试、TypeScript 编译 |
| PR 2 | 已实现真实 Task Bar、同步状态和 Snapshot 读取 | 已实现 Store、创建/读取 API、Owner scope、创建幂等和 `TASK_CREATED` SSE | 当前自动化覆盖内存 Store 恢复、Owner 隔离、创建幂等和游标；PostgreSQL 重启、多实例通知与浏览器 E2E 仍未验证 |
| PR 3 | 已实现固定 Fixture 的最薄 Branch/Conflict/Control/Commit；Action Gate 打开时视觉隐藏明细并保留草稿 | 单次 start/resolve mutation、Verifier、ControlEvent、ArtifactVersion | 已有内存引用/hash/幂等测试、桌面/移动冲突截图和桌面提交态截图；PostgreSQL 重启和完整浏览器恢复仍待补 |
| PR 4 | 完整 Task Artifact Workspace、异常与移动端闭环 | 所有状态追到 Snapshot/SSE | 浏览器端到端、断线恢复、桌面/移动截图；用户研究仍单独标待办 |
