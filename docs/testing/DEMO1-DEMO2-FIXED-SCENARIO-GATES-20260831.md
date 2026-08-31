# Demo 1/2 固定场景门（2026-08-31）

- 状态：`Limited Verified`；固定 Fixture/Runtime/API 与既有浏览器门已通过，
  PostgreSQL、Provider 和用户研究仍开放
- 用户来源：`USER-FEEDBACK-20260831-DEMO1-DEMO2-FIXED-SCENARIO-HARDENING`
- 决策：`DR-0053`
- 场景：`SCENARIO-038`、`SCENARIO-039`
- Evidence：
  [`DR-0053-DEMO1-DEMO2-FIXED-SCENARIO-GATES-EVIDENCE-20260831`](../evidence/DR-0053-DEMO1-DEMO2-FIXED-SCENARIO-GATES-EVIDENCE-20260831.md)

## 1. 为什么先做固定场景门

[OpenAI Agents SDK Testing](https://openai.github.io/openai-agents-python/testing/)
把应用拥有的编排、工具、guardrail、retry、streaming 和 session 行为与外部模型、
网络和 Provider 行为分开测试，并提供不发起真实模型请求的确定性 Fixture。它支持
本阶段先锁定本项目拥有的 Task/Branch/Admission/Worker/Artifact 合同，再单独运行
真实 Provider 集成；不证明本项目采用相同 SDK，也不证明 Fixture 通过等于模型效果。

三组场景共享同一公开 API 和 Runtime，不注册 Demo 私有端点，不通过 Prompt 关键词
切换执行器。每组都必须同时断言用户看到的输出和 Snapshot/Event 权威事实。

## 2. FSG-D1：同一 Task 只继续一条未完成工作线

### 触发与用户动作

- parent Run 已终态，至少有一条完成 Branch、一条未完成 Branch 和 v1
  ArtifactVersion/TaskCommit。
- 用户在旧 Run 选择未完成 Branch，点击“继续未完成任务”。

### Agent 路径与后端事实

1. 浏览器只提交 `branch_id`、`expected_version`、幂等键和可选 instruction/budget。
2. `/v1/harness/runs/{run_id}/continue` 校验 Owner、version、Branch 归属和当前
   Workspace revision。
3. child 使用相同 `task_id`、新 `run_id`、`run_sequence+1`，记录
   `parent_run_id/carried_branch_id/base_artifact_version/base_task_commit`。
4. child 首轮范围精确等于所选 Branch 的 missing 或批准 refs；instruction 不能扩展。
5. 来源版本未变化仍保守重核批准 refs；变化时额外公开
   `source_revision_changed=true`。

### 前台输出

- “任务持续链 · Run 2”、旧成果基线、精确批准来源和“旧采用事实不会直接沿用”。
- 来源变化时显示“来源版本已变化”；390 px 仍可读且无页面级横向滚动。
- parent 失败响应或 child 不合法时继续保留 parent UI，不能提前重置 SSE 游标。

### 必须注入的失败

- 旧 expected version、错误 Owner、完成 Branch、同幂等键不同请求、instruction 试图
  扩 scope、Catalog 完整性失败。
- 每个失败必须零新增 child/Event/Artifact/Commit，且不泄露其他 Owner 对象。

## 3. FSG-D2A：跨职能五工作包的受限 adaptive 路线

### 触发与用户动作

- 五个 validated WorkUnit/Branch，三条独立 roots、两条依赖后继，来源跨职能，
  预算充足，`external_action=none`。
- 用户先审查路线理由，再明确确认启动只读 Worker。

### Agent 路径与后端事实

1. 服务端产生 `mode=adaptive_readonly_workers` 和结构化 `reasons[]`。
2. Planner 已为计划和准入输入留下调用回执；用户确认前 Worker/Analyst Worker 调用
   为零，等待确认不得新增模型调用。确认携带 expected version、幂等键和 ready
   Branch。
3. 第一波最多三个进程内只读 Worker；第二波只在依赖完成后进入
   `ready_branch_ids`。
4. 注入至少两个 adopted 与一个 failed/ambiguous。返回不等于采用；只有批准 refs、
   Evidence Anchor 和叙事对账通过的 Contribution 可以合入。
5. 合入形成新的普通 append-only ArtifactVersion/TaskCommit，v1 和其他 adopted
   Contribution 保持不变。

### 前台输出

- 路线理由、预算、确认边界、工作包依赖、实际 Worker 回执和统一成果。
- 显示“已调用/已返回/已采用”差异以及单项失败影响，不显示多个 Agent 聊天窗口。
- 下一波只显示服务端 ready 工作包；390 px 无页面级横向滚动。

### 必须注入的失败

- 未确认、旧 version、重复 Branch、预算不足、越 Branch 来源、无 Anchor、Worker
  exception。失败不得静默启动额外 Worker 或清空其他贡献。

## 4. FSG-D2B：三期财务必须保持固定流程

### 触发与用户动作

- 三期同结构、同职能财务来源，目标是生成未付统计、未收统计和跨期核对说明。
- 即使 instruction 出现“多个 Agent”或“并行”，用户也不直接拥有拓扑决定权。

### Agent 路径与后端事实

1. 冻结来源结构和 validated plan 后，Admission 必须为 `fixed_workflow`。
2. 不产生 `worker_returned`、Worker receipt 或隐藏 Worker 模型预算消耗。
3. 未付统计和未收统计分别汇总三期，不是一时期一个成果；跨期说明单独解释口径、
   异常与人工复核边界。

### 前台输出

- 明确说明同结构、同职能、顺序合并为何不值得启动 Worker。
- 三个成果卡分别说明涵盖期间、统计口径、用途、记录数与来源，不用“未采用”代替
  路线解释。

## 5. 证明层级

| 层级 | 本阶段动作 | 可以证明 | 不能证明 |
| --- | --- | --- | --- |
| 确定性场景门 | 固定 Fixture + 真实 Runtime/API/UI | 本项目拥有的状态、准入、范围、采用和前台投影 | 真实模型选择、业务质量 |
| PostgreSQL | 设置真实 `TEST_DATABASE_DSN` 后运行同一合同 | 顺序重启持久化与不重放 | 多实例 lease、HA |
| Provider | 单独授权后运行固定公开任务 | 真实 Planner/Analyst 链路和一次结果 | 稳定质量、ROI |
| 用户研究 | 目标用户完成任务并回答理解问题 | 被测用户的理解、恢复步数和控制感 | 普遍体验提升 |

## 6. 完成门

- 三组场景均有聚焦 Python/API 门；Demo 1 与 Demo 2 至少各有一条浏览器门。
- 每个场景记录 instruction、Fixture 来源、Snapshot/Event、前台输出、失败边界和
  运行命令；测试通过后再把本文件状态改为 `Limited Verified`。
- 自动化结果追加到新 Evidence，不覆盖 `DR-0053` 既有 manifest 或历史红灯。
- 真实 PostgreSQL、Provider 和用户研究未运行时继续单独标红，不得由 Fixture 代替。

本轮聚焦 Python/Runtime 门为 `3 passed`；连同相关 Runtime 回归为 `68 passed`，定向
浏览器门为 `2 passed`。精确命令、提交和不能证明的边界见上方 Evidence。
