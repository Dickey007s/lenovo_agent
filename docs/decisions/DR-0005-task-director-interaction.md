# DR-0005：用 Task Director 把长任务的编排、决策与恢复带到前台

| 字段 | 内容 |
| --- | --- |
| Decision ID | `DR-0005` |
| Owner | Office Agent 项目组 |
| Date | 2026-08-11 |
| Status | `Verified` |
| Scope | Demo 1 Tasks 主视图、Decision Inbox、Agent 对话切换、工件历史防误读与移动端决策路径 |
| Depends on | `DR-0001`、`DR-0002`、`DR-0004`、现有 `TaskSnapshot` / Control / SSE 协议 |

## 1. 用户场景与问题

目标用户仍是准备客户 A 经营会材料的项目负责人或客户经理。任务启动后，用户需要快速判断当前阶段、三个交付分支各自进展、哪个分支被证据阻塞、现有工件能否提交，以及此刻自己必须做什么；发生断线、冲突解决或工件换版后，还要能确认当前看到的是不是最新服务端事实。

既有 Runtime 已经能显示这些事实，但长期任务明细被压缩在通用 Agent 对话旁的窄面板中。冲突证据和决定动作分居工作区与 Runtime，用户需要跨区域来回寻找；通用聊天记录又长期占据主要空间。工件 mutation 后若仍停留在旧版本，历史内容还可能与当前 Branch head 并列出现而缺少足够强的区分。

本轮完成条件是：Tasks 默认进入第一类 Task Director 工作区；左侧用编排画布集中呈现阶段、分支、工件、验证、冲突和 Commit，右侧默认只放需要用户处理的 Decision Inbox，同时允许切回 Agent 对话；移动端阻塞摘要可到达决策区；用户主动查看旧版本时有明确历史标识，mutation 后默认跟随新的 Branch head。所有业务结论必须继续来自服务端 Snapshot，不能为匹配参考图伪造进度、恢复或执行结果。

## 2. 来源与依据

| Source ID | 类型 | 支持的判断 | 局限 |
| --- | --- | --- | --- |
| `USER-FEEDBACK-20260811-INTERACTION-01` | Stakeholder 用户反馈与方向选择 | 前台设计与用户交互应成为一等推进目标；选择第二个 Task Director 方向 | 不是目标用户研究或效果证据 |
| `DESIGN-REFERENCE-TASK-DIRECTOR-OPTION2-20260811` | 选中视觉参考 | 支持编排画布、Decision Inbox、工作台密度和状态色的信息层级 | 不是运行截图；图中的时间、进度和动作不能直接视为产品事实 |
| `USER-FEEDBACK-20260810-01/02` | 治理要求与 0716-v2 会后反馈 | 每次推进必须同时说明前台影响、后端事实、场景与来源 | 不指定具体布局，也不证明该布局有效 |
| `FRONTEND-E2E-DEMO1-PR4-20260810`、`POSTGRES-BACKED-API-RESTART-DEMO1-PR5-20260811` | 既有运行证据 | 证明当前 TaskSnapshot 主路径、工件工作区和断线对账事实可供新前台复用 | 不验证本轮新布局、历史防误读或用户价值 |
| `TASK-DIRECTOR-INTERACTION-DEMO1-PR6-20260811` | 源码、自动化、浏览器与截图证据 | 证明固定 Fixture 的新布局、既有控制、历史版本区分与被测响应式路径 | 不证明真实 Connector、通用后台 Loop 或用户价值 |
| `TASK-DIRECTOR-DESIGN-QA-20260811` | 参考图与实现视觉复审 | 两轮比较关闭历史混淆、移动阶段轨、裁切与原始协议词等 P1/P2，最终无 P0/P1/P2 | 视觉通过不等于目标用户更快或更正确地决策 |

完整登记见 [`SOURCE_REGISTER.md`](SOURCE_REGISTER.md)。

## 3. 决策与取舍

1. Tasks 使用专用的 Task Director 组合，而不是把长期任务继续作为通用聊天旁的附属面板。它仍保持“工作区在左、Agent 在右”的产品结构，只是右侧默认呈现更紧迫的 Decision Inbox，并允许用户随时切换到 Agent 对话。
2. 左侧编排画布不是第二套任务状态机。标题、目标、版本、任务阶段、预算、分支、工件 head、验证、冲突和 Commit 全部由现有 `TaskSnapshot` 投影；阶段色、布局、图标和展开状态只是表达。
3. Decision Inbox 只提升已经存在的服务端动作。收入冲突的主动作继续提交 `resolve_evidence` 并选择契约内 CRM 正式来源；“准备补证指令”只把文字放入方向输入，真正提交后也仅显示 `steer=accepted`、等待后续循环应用。
4. 工件选择区分 `follow_head` 与 `pinned_history`。默认跟随 Branch head；用户主动选择非 head 版本时显示“正在查看历史版本”，并提供返回当前版本的动作。mutation 后不能让旧内容静默冒充当前版本。
5. 移动端采用纵向编排和可到达的决策路径，不把桌面泳道强行缩成不可读缩略图；页面本身不得产生横向溢出。
6. 本轮不新增后端协议、Task 状态、控制种类或真实 Connector，也不把同步/传输状态写成 Task 业务进度。

未采用继续扩张原窄 Runtime，因为它会延续证据与动作分离、业务状态截断和聊天占据主空间的问题。未采用纯静态大屏，因为它无法处理控制、历史版本和断线恢复，也违反服务端事实门槛。未采用完整内部 Trace/Worker 会话作为主视图，因为这些信息会增加认知负担并暴露不应前台展示的实现细节。

## 4. 前台输出与交互

| 区域 | 用户看见什么 | 用户可做什么 | 反馈与恢复 | 默认隐藏 |
| --- | --- | --- | --- | --- |
| Task 头部与事实摘要 | 标题、目标、Task version、状态、已验证分支数、Loop step、同步/传输状态和待决策数 | 刷新、创建或再次演示、切换指挥台/共享工件/待办 | 未同步时显示重新对账；终态新建不覆盖旧 Task | Task ID 的内部用法、幂等键、DSN、网络重试日志 |
| 编排画布 | Observe/Plan/Act/Verify/Commit 阶段；每个 Branch 的契约、交付、head、验证/冲突和汇聚条件 | 打开服务端 head 工件 | 没有 head/report/Commit 时明确显示等待，不补造完成比例 | Prompt、思维链、Worker 对话、完整 Trace JSON |
| Decision Inbox | 只显示当前 open Conflict、正式/候选口径、来源摘要和相关分支控制 | 采用正式口径、查看工件、准备并提交补证 Steer、暂停或接管分支 | mutation 提交中冻结重复动作；只有新 Snapshot 才改变业务状态；Steer 明示待应用 | 原始检索日志、未知或敏感来源、权限哈希 |
| Agent 模式 | 既有 Conversation 历史、输入和 Action Gate | 切回通用对话并继续既有办公协作 | 切换不重建 Conversation；Action Gate 继续使用原确定性治理链 | CoT、Prompt、Permit token 和工具秘密 |
| 共享工件 | Branch head、版本、验证、内容、来源、lineage 与 Commit | 选择版本或返回当前 head | 历史版本显示强提醒；默认 mutation 后跟随新 head | 未在 kind allowlist 中的字段与非安全 source ref |
| 移动端 | 纵向事实摘要、分支状态和阻塞摘要 | 从“查看决策”跳到 Decision Inbox | 无横向页面溢出；控制仍服从同步和 pending 状态 | 桌面专用密度和装饰性连接信息 |

## 5. 后端事实映射

完整逐项映射见 [`UI_SERVER_FACT_MATRIX.md`](../contracts/UI_SERVER_FACT_MATRIX.md)。本轮没有新增 API；关键映射为：

- 标题、目标、版本、任务状态、阶段和预算来自 `TaskSnapshot.contract`、`version`、`status`、`phase` 与 `budget`。
- 分支泳道来自 `branches[]`；交付定义来自 `contract.deliverables[]`；最新工件来自 `branches[].artifact_heads` 与 `artifact_versions[]`；验证、冲突和提交分别来自 `verification_reports[]`、`conflicts[]` 与 `last_commit`。
- “等待你的决定”只在存在 open Conflict 或服务端任务状态要求输入时出现；任务完成只在 `last_commit` 和终态 Snapshot 支持时出现。
- `taskSyncState`、`taskTransportState`、右侧模式、工作区模式和工件选择模式是客户端交互事实，不是 Task 业务字段。它们只能描述浏览器是否已对账、当前显示哪个视图以及用户是否固定查看历史版本。
- 同一 Task 的 Snapshot 只在 `version` 不低于当前版本、`last_event_sequence` 不低于当前 Snapshot 与已观察 SSE sequence floor 时应用；否则保留较新事实并保持重新对账，不能被乱序旧 GET 回滚或伪标 `synced`。
- `resolve_evidence`、Pause、Resume、Take over、Return control 和 Steer 继续携带 `expected_task_version` 与幂等键。业务状态只在服务端返回新 Snapshot 后改变；`steer` 当前只产生 `CONTROL_ACCEPTED`。

## 6. 失败、等待与安全边界

- SSE 或 GET 不可用时保留最后确认 Snapshot，显示“正在重新对账”，禁用新 Task Control；不能把传输中断写成任务失败，也不能声称后台仍在运行。
- `409` 后读取最新 Snapshot并要求用户复核，不基于旧版本自动重放含义可能已变化的控制。
- open Conflict 未解决时只标记受影响 Branch，其他分支的状态继续以各自 Snapshot 为准。
- 用户查看历史版本时必须显示当前 head 版本与返回动作；历史 candidate 不能以布局、颜色或文案冒充已验证 head。
- 未知 Artifact 字段和非安全 `source_ref` 继续 fail closed。Task Director 不展示原始 Prompt、思维链、Worker 内部对话、密钥、JWT/Permit、底层日志或无决策价值的内部调度。
- `email.send` 等仍是 Simulator；Task Director 展示客户回复草稿或 Commit 不代表真实邮件、CRM、日历或 OA 写入。

## 7. 验证与当前状态

本决策已通过固定 Fixture 的工程验收：最终全量浏览器 E2E `6 passed (34.5s)`，专用 Task Director 截图封口用例 `1 passed (21.6s)`；完整 Python `58 passed, 1 skipped (3.46s)`，Ruff、前端 lint 和生产构建通过。新增两项 Snapshot 乱序回归，防止旧 GET 覆盖较新事实或在未追上已观察 SSE 序号时伪标 `synced`。桌面 `1487 x 1058`、移动 `390 x 844` CSS 视口及历史版本状态均有哈希截图；[`design-qa.md`](../../design-qa.md) 最终为 `passed`，两轮复审后无剩余 P0/P1/P2。逐项结果与截图哈希见 [`DEMO1-PR6-TASK-DIRECTOR-INTERACTION-EVIDENCE.md`](../evidence/DEMO1-PR6-TASK-DIRECTOR-INTERACTION-EVIDENCE.md)。

即使工程验收全部通过，也只能证明固定 Fixture 的页面投影与控制路径。`H-001/H-004` 及“Decision Inbox 降低查找成本”“历史标识降低误读”仍需目标用户任务测试，不能在 PR 完成后自动写成体验提升结论。

## 8. 关联项

- 场景：[`SCENARIO-001`](../scenarios/SCENARIO-001-customer-a-durable-report.md)
- 事实矩阵：[`UI_SERVER_FACT_MATRIX.md`](../contracts/UI_SERVER_FACT_MATRIX.md)
- 用户反馈原文：[`USER-FEEDBACK-20260811-03`](../sources/USER-FEEDBACK-20260811-03-task-director.md)
- 选中参考图：[`dr-0005-task-director-option2-reference.png`](../evidence/assets/dr-0005-task-director-option2-reference.png)
- 运行与视觉证据：[`DEMO1-PR6-TASK-DIRECTOR-INTERACTION-EVIDENCE.md`](../evidence/DEMO1-PR6-TASK-DIRECTOR-INTERACTION-EVIDENCE.md)
- Design QA：[`design-qa.md`](../../design-qa.md)
