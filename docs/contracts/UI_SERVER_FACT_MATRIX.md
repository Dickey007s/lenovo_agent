# Demo 1 UI—服务端事实矩阵

> 状态：`Ready`。矩阵规定前台能展示什么以及事实来自哪里；当前 PR 不证明这些 UI 已经接入。

## 1. 组件映射

| UI 状态或组件 | 用户含义 | 服务端权威字段 | Snapshot / SSE | 允许动作 | 失败与恢复 | 默认隐藏 |
| --- | --- | --- | --- | --- | --- | --- |
| Active Task Bar | 正在处理哪个目标、处于哪个阶段 | `TaskSnapshot.task_id/status/phase/version/contract.objective/budget/last_commit` | 初始 GET；`TASK_STATUS_CHANGED`、`TASK_PHASE_CHANGED`、`BUDGET_UPDATED`、`CHECKPOINT_COMMITTED` | 打开任务详情、查看最近 Commit | 断线时保持最后确认值并显示“状态可能已变化” | Prompt、内部调度、幂等键 |
| Branch Status List | 哪些分支运行、等待、暂停、失败或已提交 | `branches[].status/version/pause_reason/artifact_heads/issue_ids` | `BRANCH_STATUS_CHANGED` | Pause、Resume、Take over、Return control | 单分支错误只影响该行；版本过期后刷新 Snapshot | Worker 对话、内部计划文本 |
| Conflict Card | 哪个事实冲突、影响哪个分支、可选依据是什么 | `conflicts[].status/subject/summary/source_refs/candidate_values` | `CONFLICT_OPENED`、`CONFLICT_RESOLVED` | Resolve evidence、Take over | 提交后保持 open，直到服务端 resolved；失败显示可理解原因 | 未授权来源正文、原始检索日志 |
| Task Artifact Workspace | 当前交付物版本、来源和验证结果 | `artifact_versions[]`、`verification_reports[]`、`branches[].artifact_heads` | `ARTIFACT_VERSION_CREATED`、`VERIFICATION_RECORDED`、`CHECKPOINT_COMMITTED` | 查看来源、版本历史、人工接管后编辑 | candidate/failed 不能显示为完成；旧 head 只读 | 原始模型上下文、完整工具参数 |
| Task Control Bar | 用户能否纠偏、暂停或接管 | `TaskSnapshot.version`、Branch status、服务端允许转换 | `CONTROL_ACCEPTED/APPLIED/REJECTED` | Steer、Pause branch、Resume、Take over、Return control | mutation 带 version/key；`409` 时展示新版本并要求用户复核 | idempotency key、权限哈希 |
| Stream Health Badge | 当前页面是否持续收到服务端更新 | 客户端 `last_sequence/sync_state`，不属于业务状态 | heartbeat、断开、重连；对账 GET | 手动重连 | 断线禁用控制但保留未发送文本；回放后以 Snapshot 对账 | 网络栈和内部重试日志 |
| Verified Commit Summary | 哪些工件构成最终结果及如何验证 | `last_commit.state_hash/artifact_version_ids/verification_report_ids` | `CHECKPOINT_COMMITTED`、`TASK_COMMITTED` | 查看 Trace 摘要、打开工件 | 没有 Commit 或有 open conflict 时不得出现完成 | 原始 Trace payload、签名和密钥 |
| Task Error Banner | 哪一层失败、是否可恢复、用户下一步是什么 | `last_error.code/scope/recoverable/user_action` | `TASK_FAILED` 或最新 Snapshot | 重试、缩小范围、接管、返回上个 Commit | `5xx` 先标记“结果待确认”并按幂等键查询，不直接宣告失败 | 堆栈、内部服务地址、敏感参数 |
| Action Gate Tray | 某个真实副作用动作是否可执行 | 现有 `RunSnapshot.risk/control_plan/permit/tool_result` | 现有 Run API/SSE | 补证据、审批、Authorize | 与 Task Control 分离；旧 Action 继续遵守失效和 Permit 规则 | Permit token、策略内部秘密 |

## 2. 状态文案与颜色不是事实

前端可把服务端枚举翻译为中文，但不能改变语义：

| 服务端状态 | 建议中文 | 用户可做什么 | 禁止推断 |
| --- | --- | --- | --- |
| Task `running` | 任务运行中 | 查看分支、Steer、暂停或接管 | 不能按动画估算完成比例 |
| Task `waiting_input` | 等待你的决定 | 处理冲突或接管 | 不能把单分支等待写成整任务失败 |
| Task `paused` | 已暂停 | Resume 或 Take over | 不能声称后台仍在执行 |
| Task `taken_over` | 由你接管 | 编辑新版本或归还控制 | Agent 不得继续写受控分支 |
| Task `verifying` | 正在验证 | 查看候选工件，等待结果 | candidate 不能显示已完成 |
| Task `committed` | 已验证并提交 | 查看 Commit、工件和 Trace 摘要 | 必须同时存在服务端 Commit 事实 |
| Branch `waiting_evidence` | 此分支等待依据 | 解决冲突、Pause 或 Take over | 其他分支状态保持独立 |
| Branch `failed` | 此分支失败 | 查看原因、从 Commit 恢复或接管 | 不自动覆盖为整个 Task failed |

颜色、图标、进度条、动效、Toast 和按钮 disabled 状态都是 UI 表达，不能成为风险、预算、验证、执行或完成的权威来源。

## 3. 控制提交时序

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
    S-->>UI: CONTROL_APPLIED SSE
    UI-->>U: 按服务端版本更新状态
```

服务端返回 `409` 时，UI 必须读取最新 Snapshot，并让用户看到哪些字段发生变化；不得用旧 version 自动重试含义可能已经改变的命令。

## 4. 断线、过期与恢复

1. **断线**：显示“更新暂时中断，任务可能仍在后台运行”；保留最后确认 Snapshot，停止模拟进度，禁用新的控制提交。
2. **重连**：使用 `after=last_sequence` 回放，随后 GET Snapshot；重复事件按 `task_id + sequence` 去重。
3. **序号缺口**：若下一事件不是 `last_sequence + 1`，立即标记 `reconciling` 并以 Snapshot 覆盖本地投影。
4. **旧版本**：`409` 后不改变业务状态，展示服务端当前 version、变更摘要和重新应用入口。
5. **身份过期**：`401/403` 后转只读，保留未提交 Steer 文本但不自动重放。
6. **服务重启**：从稳定 Task ID 恢复 Snapshot，不创建新 Task，不重播工作区打字动画。
7. **请求超时/5xx**：先显示“结果待确认”，用 idempotency key 或 Snapshot 查询结果后再决定是否允许重试。

## 5. 实现与验证责任

| PR | 前台最小输出 | 后端事实 | 必须提供的证据 |
| --- | --- | --- | --- |
| PR 1 | 只定义 TypeScript 类型与本矩阵，不宣称页面已实现 | Pydantic 目标协议 | 严格 Schema 测试、TypeScript 编译 |
| PR 2 | 真实 Task Bar、同步状态和 Snapshot 读取 | Store、Task API、有序 SSE | 恢复/隔离/SSE 测试、桌面截图 |
| PR 3 | 最薄 Branch/Conflict/Control 交互 | Loop、Verifier、ControlEvent、幂等恢复 | 分支隔离、过期版本、重复命令、重启恢复和控制截图 |
| PR 4 | 完整 Task Artifact Workspace、异常与移动端闭环 | 所有状态追到 Snapshot/SSE | 浏览器端到端、断线恢复、桌面/移动截图；用户研究仍单独标待办 |
