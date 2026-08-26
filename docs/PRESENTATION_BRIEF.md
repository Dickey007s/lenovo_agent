# Office Agent V0.2 中文汇报卡片

本文件记录面向会议、PPT 和产品评审的中文表述。英文只保留产品名、
接口名、协议字段和原始来源标题。

## 1. 一句话定位

我们不是在制作三套写死的 Demo，而是在建设一个通用 Office Agent
Harness：它从可检查的办公文件出发，让用户明确控制数据范围，看见
Agent 如何在完整资料库中自主寻找证据、实际调用和校验了什么，并能从
每条结论返回来源、由人确认下一步任务。

## 2. 汇报硬门槛

每个架构、Demo 或产品结论必须同时回答：

1. 用户是谁，在什么办公场景下触发，异常路径是什么；
2. 设计来源是什么，Source ID、日期或版本、支持判断和局限是什么；
3. 与主流方案相比，技术侧重点有什么不同；
4. 这种技术差异怎样改变用户交互流程；
5. 前台显示什么状态、提供什么动作、如何反馈和恢复；
6. 每个 UI 状态由哪个后端事实产生，哪些内部细节默认隐藏；
7. 当前 Evidence 状态是什么，还有哪些结论只能标为 `Draft`。

完整门槛遵循
[`DECISION_AND_REPORTING_GOVERNANCE.md`](DECISION_AND_REPORTING_GOVERNANCE.md)。
汇报必须同时保留“场景与来源”“前台交互影响”“后端事实映射”和
“验证与边界”。研究来源包见
[`WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825`](research/WORKSPACE-CENTRIC-OFFICE-AGENT-INTERACTION-AND-SOURCES-20260825.md)。
Agent Control Loop 的逐模块历史基线、当前三轮只读纵切和后续缺口见
[`AGENT-CONTROL-LOOP-IMPLEMENTATION-AUDIT-20260825`](research/AGENT-CONTROL-LOOP-IMPLEMENTATION-AUDIT-20260825.md)。
完整的项目化讲稿、七个办公场景、七个图示区和 17 页 PPT 结构见
[`OFFICE-AGENT-DETAILED-CHINESE-REPORT-20260825`](reports/OFFICE-AGENT-DETAILED-CHINESE-REPORT-20260825.md)。

## 3. PPT 页面卡片

| 页码 | 中文结论 | 建议画面 | 证据与边界 |
| --- | --- | --- | --- |
| 1 | Office Agent 从一个统一办公资料库开始，而不是从 Demo 或职业按钮开始 | 当前文件管理器工作台截图 | `DR-0024`；公开基准数据，不是真实企业网盘 |
| 2 | 真正的问题不是缺少聊天框，而是上下文不可见、执行过程不可核对 | 旧流程与文件夹优先流程对比 | Stakeholder 反馈，不是用户研究 |
| 3 | 一个 Runtime、八个通用模块、三种验收视角 | 分层架构图；Demo 1/2 加跨拓扑 Demo 3 | 当前能力与目标能力必须用不同颜色 |
| 4 | 会话、工具、Subagent 和人工审查已经是主流基线 | OpenClaw、Codex、Claude Code 官方资料对比 | 官方文档研究，不是竞品实测 |
| 5 | 用户给目标，Agent 负责从整库找证据，但选择过程必须可见、可限、可复核 | 浏览 -> 下达目标 -> Agent 选证据 -> 观察 -> 引用 -> 复核 | 实现侧重点差异，不是优越性结论 |
| 6 | 固定公开数据版本，让演示中的每份材料都能被现场检查 | 15 个文件夹、96 份文件、格式分布 | FORTE 固定 commit；不是真实企业数据 |
| 7 | 安全预览把“Agent 读了什么”变成可见契约 | CSV/PDF/DOCX/TXT 预览拼图和安全说明 | 路径、大小、hash、符号链接和解析器测试 |
| 8 | Harness 把模型调用、内容采用和服务端校验分开 | 事件与模型回执时序 | Snapshot/Receipt 事实；不展示思维链 |
| 9 | 引用不是装饰，而是返回证据的导航动作 | 结果引用重新打开来源文件 | 只证明引用范围，不证明语义正确 |
| 10 | Agent Control Loop 会把计划变成可核对任务分支；证据不足时，人只选择一条分支继续 | 任务分支现场、分支 Evidence Gate、成果 v1→v2 与恢复轨迹 | 只读、最多三轮、顺序 Controller；Branch 不等于并行 Worker |
| 11 | Demo 2 验收多任务自组织、动态调度和共享工件汇聚 | Worker、依赖与动态重排图 | 目标设计；当前产品没有通用 Worker Runtime |
| 12 | Demo 3 对单任务和多任务统一施加风险与动作控制 | 影响预演 -> 证据 -> 审批 -> Permit -> 回执 | 目标设计；当前没有真实外部动作 |
| 13 | 当前已经证明工程链路，但也保留模型结果出错的负面证据 | 自动化、截图与 Finance 算术偏差并列 | `completed` 不等于结论正确 |
| 14 | 历史审计的约 30% 已升级为可见、可选分支、可恢复成果的只读 Loop；下一步转向可写隔离工件、确定性验证和多 Worker | Branch/Artifact 当前纵切与 Demo 2 目标架构叠加图 | `30%` 只代表历史基线；当前 [`DR-0026`](decisions/DR-0026-selective-branch-and-immutable-artifact-history.md) 仍是限定范围工程证据 |

## 4. 现场演示卡片

1. 直接打开 `/`，进入“办公资料库”。
2. 像文件管理器一样搜索、按类型筛选并预览任意文件；强调浏览不会限制 Agent 范围。
3. 不勾选文件，只输入一个现场提出的新目标，并设置轮次、每轮文件、模型调用和 deadline 上限。
4. 启动 Loop，指出合同已冻结完整 96 文件索引；Planner 与 Analyst 的独立模型回执才是调用事实。
5. 展示 Agent 本轮选择了哪些文件、为什么选择，以及服务端如何把超预算候选限制在本轮上限内。
6. 在 Evidence Gate 停下来，检查哪些 Branch 已完成、哪些缺证，再只点一条“继续此分支”；强调未选分支仍保留，下一轮只能补核该分支的缺失证据。
7. 展示成果简报从 v1 到 v2；再恢复 v1，说明系统只新增一条 TaskCommit、当前指针改变，v2 与原文件都没有被覆盖。
8. 点击结论引用返回来源文件，再展示最多四条下一步建议；只有点击“确认并启动”才创建新 Loop。

演示不要从八模块架构图开始。先让观众看到数据、任务、轨迹和证据闭环，
再解释支撑它的架构。

## 5. 主流方案对比卡片

### OpenClaw

- 官方资料重点：自托管 Gateway、Channel、Session、Routing、Tool 和主机执行审批。
- 我们的侧重点：把一个服务端拥有的办公资料库、Agent 选证据的理由和引用放到第一屏。
- 交互影响：用户可以先检查数据，但不必先完成检索；提交目标后再监督 Agent 如何缩小范围。

### Codex App

- 官方资料重点：并行项目任务、Worktree、变更审查、Skill 和 Automation 审查队列。
- 我们的侧重点：办公文件是只读业务证据，计划与结果需要回到 Agent 实际采用的文件核对。
- 交互影响：用户主要审查业务结论和引用，而不是代码 Diff 或 Worktree。

### Claude Code

- 官方资料重点：项目目录上下文、Agent/Tool Loop、Subagent、Permission Mode 和多种开发界面。
- 我们的侧重点：模型可检索完整安全索引，但每轮正文访问由服务端预算和校验约束，不能静默读取所有内容。
- 交互影响：用户少做一次手工范围选择，改为在执行中查看“选了什么、为什么选、是否被采用”。

### ReAct 与当前 Office Agent

- ReAct 启发：以 Reasoning、Action、Observation 交替组织执行轨迹。
- 当前落地：普通前台只展示模型调用、业务操作、服务端校验、回执和引用，不暴露私有思维链。
- 用户流程：浏览 -> 下达目标 -> Agent 自主选证据 -> 查看轨迹 -> 打开引用 -> 确认下一步。

不能表述为“竞品没有这些能力”或“本方案优于竞品”。官方文档不是受控竞品测试，
引用页面没有提及某项能力，也不能证明产品绝对不具备它。

## 6. 技术差异到交互影响卡片

| 技术选择 | 用户流程变化 | 前台输出 | 后端事实 |
| --- | --- | --- | --- |
| 服务端拥有完整文件目录 | 用户可以先浏览再提问 | 文件夹、文件信息、可用状态 | `GET /v1/harness/workspace` |
| 整库合同 + 每轮自主选证据 | 用户不用先猜文件，但能监督 Agent 缩小范围 | 96 文件统一检索、本轮文件与选择理由 | `scope_mode`、`allowed_file_refs`、`round.input_file_refs` |
| 有界格式适配器 | 不执行文件也能检查证据 | 表格/文档预览和安全说明 | 文件预览路由与完整性校验 |
| 模型之后还有策略编译器 | 模型不能静默决定副作用 | “模型已调用”与“计划已校验”分开 | Model Receipt 与服务端 Plan |
| 有序事件加权威 Snapshot | 进度和恢复依据事实 | 轨迹、重连中、最终对账 | named SSE 与 Run Snapshot |
| 引用范围校验 | 复核不离开 Agent 本轮采用的资料 | 引用按钮重新打开来源 | 结果 `file_refs` 属于本轮批准范围 |
| 终态仍要求复核 | 完成不等于正确 | “模型初步结论 · 待复核” | `review_required=true` |
| 服务端 Evidence Gate | 验证结果可决定继续还是停止 | 本轮缺口、下一轮目的、剩余预算 | `rounds[].evidence_gaps` 与 `next_step` |
| 轮次间人工证据门 | 证据不足时由人决定是否继续花预算 | “确认并继续核对”、调整方向或停止 | `status=waiting_input`、`control_state=paused`、resume 回执 |
| 服务端任务 Branch | 用户不用把整组缺口一次性全放行，可只推进一条工作线 | 分支状态、依赖、资料/缺口数量、“继续此分支” | `branches[]`、`candidate_branch_ids`、`active_branch_id`、带 `branch_id` 的 resume |
| 版本化人工控制 | 用户不必只能等待模型跑完 | 暂停、继续、调整下一轮、结束并保留 | `ControlEvent`、expected version、幂等回执 |
| Snapshot 持久化与安全恢复 | 刷新/进程重启不必把已完成轮次当作丢失 | “检查点已恢复”、原轮次/预算/版本、显式继续 | PostgreSQL `HarnessStateStore`、`checkpoint_recovered` |
| 独立不可变成果记录 | 用户看见每轮成果，提交不再通过改写版本表达 | 简报 v1/v2、草稿/已核对、当前版本指针 | append-only `ArtifactVersion`、独立 `TaskCommit` |
| 受控成果恢复 | 用户可以恢复旧简报且不丢掉新版 | “恢复”、当前 vN、“已恢复历史成果版本” | rollback ControlEvent、新 TaskCommit、`artifact_version_restored` |
| 有界候选修复 | 模型返回未通过时不会静默采用 | `未采用` 与预算内重试 | `plan_validation_rejected`、模型调用计数 |
| 人工确认下一步 | Agent 建议不会自动扩张任务 | 最多四条建议与“确认并启动” | 终态 `follow_ups` + 新 Run POST |

## 7. 当前证据卡片

`DR-0022` 是历史手工选文件基线；`DR-0023/24` 证明整库只读 Loop；
`DR-0025` 是整组补证与 Snapshot 内成果版本的已合并历史基线；`DR-0026`
记录当前分支选择、独立不可变成果与恢复：

- 完整 Python：`63 passed, 1 skipped`；聚焦 Runtime：`26 passed`；
- Harness 浏览器：`13 passed`；Ruff、lint 与 build 通过；最终 Evidence 记录完整时长；
- PR #31 的 PostgreSQL 17.11 workflow `1 passed in 1.84s`，四个顺序 Runtime 覆盖中断、恢复完成、历史版本恢复和再次读取当前指针；这不是多实例高可用；
- 两条等待分支可逐条继续，未选分支保持等待；ArtifactVersion 与 TaskCommit 分表 append-only，恢复只新增 Commit；
- 两张确定性浏览器图分别展示“继续此分支”与“恢复 v1”；它们证明 UI/服务端字段映射，不是真实模型运行；
- 最终截图绑定的真实浏览器运行：整库冻结 96 份索引，Agent 自主选择并核对 3 份文件，2 次 `deepseek-v4-pro` 调用，形成 5 条发现和 4 条待确认建议；
- 3 张最终文件管理器/建议截图及 SHA-256 写入 Evidence；1440px 与 390px 无页面横向溢出；
- 实现提交 [`2b8e58c`](https://github.com/Dickey007s/lenovo_agent/commit/2b8e58c161df02d4f2c09bc2692db76d075f2ae2)；
- PR #25-#31 已合并到 `master`；`DR-0026` 由 [PR #31](https://github.com/Dickey007s/lenovo_agent/pull/31) 合并为 `697e38b`，PostgreSQL 门已通过。

`DR-0023` 的历史数字仍只证明当时的手工范围版本。当前最终数字必须取自
[`AUTONOMOUS-WHOLE-WORKSPACE-RESEARCH-20260825`](evidence/AUTONOMOUS-WHOLE-WORKSPACE-RESEARCH-EVIDENCE-20260825.md)，
不得把旧版 PPT 或历史 Evidence 当作当前 UI/API 事实。

## 8. 禁止对外表述

- “已经下载 FORTE 未公开的完整 180 条任务”；
- “FORTE 公开文件是真实 Lenovo 或客户企业数据”；
- “15 类 FORTE 任务已经全部解决”；
- “有引用就证明结论或数字正确”；
- “计划里出现操作，就说明工具或文件写入已经发生”；
- “当前三轮只读 Loop 已等同完整 Demo 1 Durable Runtime，或 Demo 2/3 已全部完成”；
- “内存 Snapshot 具备跨进程持久化或多实例高可用”；
- “PostgreSQL Snapshot 恢复等于在途模型调用可续跑、跨实例调度或多实例高可用”；
- “独立 append-only 逻辑 ArtifactVersion/TaskCommit 等于真实办公文件写入、源文件回滚或 Tool Gateway 动作”；
- “Branch 状态与逐条继续等于多个 Worker 已并行、自组织或动态调度”；
- “Evidence Gate 已验证语义真值、数值正确性或业务完整性”；
- 在没有用户研究时声称“新界面更清晰、更可信或效率更高”。
