# Office Agent V0.2 中文汇报卡片

本文件记录面向会议、PPT 和产品评审的中文表述。英文只保留产品名、
接口名、协议字段和原始来源标题。

## 1. 一句话定位

我们不是在制作三套写死的 Demo，而是在建设一个通用 Office Agent
Harness：它从可检查的办公文件出发，让用户明确控制数据范围，看见
Agent 实际调用、采用和校验了什么，并能从每条结论返回同一份来源证据。

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
| 1 | Office Agent 从一个办公文件夹开始，而不是从 Demo 按钮开始 | 当前完整工作台截图 | `DR-0022`；公开基准数据，不是真实企业网盘 |
| 2 | 真正的问题不是缺少聊天框，而是上下文不可见、执行过程不可核对 | 旧流程与文件夹优先流程对比 | Stakeholder 反馈，不是用户研究 |
| 3 | 一个 Runtime、八个通用模块、三种验收视角 | 分层架构图；Demo 1/2 加跨拓扑 Demo 3 | 当前能力与目标能力必须用不同颜色 |
| 4 | 会话、工具、Subagent 和人工审查已经是主流基线 | OpenClaw、Codex、Claude Code 官方资料对比 | 官方文档研究，不是竞品实测 |
| 5 | 我们刻意把办公证据范围放到交互主路径 | 浏览 -> 预览 -> 选择 -> 下达任务 -> 观察 -> 引用 -> 复核 | 实现侧重点差异，不是优越性结论 |
| 6 | 固定公开数据版本，让演示中的每份材料都能被现场检查 | 15 个文件夹、96 份文件、格式分布 | FORTE 固定 commit；不是真实企业数据 |
| 7 | 安全预览把“Agent 读了什么”变成可见契约 | CSV/PDF/DOCX/TXT 预览拼图和安全说明 | 路径、大小、hash、符号链接和解析器测试 |
| 8 | Harness 把模型调用、内容采用和服务端校验分开 | 事件与模型回执时序 | Snapshot/Receipt 事实；不展示思维链 |
| 9 | 引用不是装饰，而是返回证据的导航动作 | 结果引用重新打开来源文件 | 只证明引用范围，不证明语义正确 |
| 10 | Agent Control Loop 已能分轮推进、核对证据并在安全点接受控制 | 两轮真实运行、Evidence Gate 与 pause/steer/stop 截图 | 只读、最多三轮、单进程 memory；不是 Durable Runtime |
| 11 | Demo 2 验收多任务自组织、动态调度和共享工件汇聚 | Worker、依赖与动态重排图 | 目标设计；当前产品没有通用 Worker Runtime |
| 12 | Demo 3 对单任务和多任务统一施加风险与动作控制 | 影响预演 -> 证据 -> 审批 -> Permit -> 回执 | 目标设计；当前没有真实外部动作 |
| 13 | 当前已经证明工程链路，但也保留模型结果出错的负面证据 | 自动化、截图与 Finance 算术偏差并列 | `completed` 不等于结论正确 |
| 14 | 历史审计的约 30% 已升级为可见、可停、可核验的只读 Loop；下一步补 Durable Artifact/Checkpoint | 当前 Loop 与目标 Durable State 叠加图 | `30%` 只代表实现前历史架构估计；当前 [`DR-0023`](decisions/DR-0023-agent-control-loop.md) 为限定范围 `Limited Verified` |

## 4. 现场演示卡片

1. 直接打开 `/`，进入“办公资料库”。
2. 展开不同业务文件夹；在调用模型前查看文件类型、大小和安全预览。
3. 从多个文件夹选择资料，输入一个现场提出的新任务，并设置轮次、每轮文件、模型调用和 deadline 上限。
4. 启动 Loop，指出活动合同已冻结；Planner 与 Analyst 的独立模型回执才是调用事实，动画本身不是。
5. 展示候选计划 `未采用` 后的一次预算内修复，再展示服务端校验后的计划。
6. 在第一轮 Evidence Gate 解释为什么继续；演示 pause/steer/resume 或 stop 在安全点生效。
7. 点击最终简报的引用返回来源文件，以“只读、待复核、没有外部动作”结束。

演示不要从八模块架构图开始。先让观众看到数据、任务、轨迹和证据闭环，
再解释支撑它的架构。

## 5. 主流方案对比卡片

### OpenClaw

- 官方资料重点：自托管 Gateway、Channel、Session、Routing、Tool 和主机执行审批。
- 我们的侧重点：把一个服务端拥有的办公文件夹、任务级文件范围和证据引用放到第一屏。
- 交互影响：用户先检查数据和范围，再提交任务，而不是先从消息 Channel 开始。

### Codex App

- 官方资料重点：并行项目任务、Worktree、变更审查、Skill 和 Automation 审查队列。
- 我们的侧重点：办公文件是只读业务证据，计划与结果需要回到用户选择的文件核对。
- 交互影响：用户主要审查业务结论和引用，而不是代码 Diff 或 Worktree。

### Claude Code

- 官方资料重点：项目目录上下文、Agent/Tool Loop、Subagent、Permission Mode 和多种开发界面。
- 我们的侧重点：模型不能静默获得整个工作区权限；用户明确选择文件，服务端再校验计划。
- 交互影响：执行前增加一次可见的数据范围确认，减少隐藏上下文扩张。

### ReAct 与当前 Office Agent

- ReAct 启发：以 Reasoning、Action、Observation 交替组织执行轨迹。
- 当前落地：普通前台只展示模型调用、业务操作、服务端校验、回执和引用，不暴露私有思维链。
- 用户流程：浏览 -> 预览 -> 选择 -> 下达任务 -> 查看轨迹 -> 打开引用 -> 人工复核。

不能表述为“竞品没有这些能力”或“本方案优于竞品”。官方文档不是受控竞品测试，
引用页面没有提及某项能力，也不能证明产品绝对不具备它。

## 6. 技术差异到交互影响卡片

| 技术选择 | 用户流程变化 | 前台输出 | 后端事实 |
| --- | --- | --- | --- |
| 服务端拥有完整文件目录 | 用户可以先浏览再提问 | 文件夹、文件信息、可用状态 | `GET /v1/harness/workspace` |
| 显式选择 `file_ref` | 用户拥有本轮上下文边界 | 选择标签、数量、可移除范围 | Run 冻结的 `selected_file_refs` |
| 有界格式适配器 | 不执行文件也能检查证据 | 表格/文档预览和安全说明 | 文件预览路由与完整性校验 |
| 模型之后还有策略编译器 | 模型不能静默决定副作用 | “模型已调用”与“计划已校验”分开 | Model Receipt 与服务端 Plan |
| 有序事件加权威 Snapshot | 进度和恢复依据事实 | 轨迹、重连中、最终对账 | named SSE 与 Run Snapshot |
| 引用范围校验 | 复核不离开本轮资料 | 引用按钮重新打开来源 | 结果 `file_refs` 属于冻结范围 |
| 终态仍要求复核 | 完成不等于正确 | “模型初步结论 · 待复核” | `review_required=true` |
| 服务端 Evidence Gate | 验证结果可决定继续还是停止 | 本轮缺口、下一轮目的、剩余预算 | `rounds[].evidence_gaps` 与 `next_step` |
| 版本化人工控制 | 用户不必只能等待模型跑完 | 暂停、继续、调整下一轮、结束并保留 | `ControlEvent`、expected version、幂等回执 |
| 有界候选修复 | 模型返回未通过时不会静默采用 | `未采用` 与预算内重试 | `plan_validation_rejected`、模型调用计数 |

## 7. 当前证据卡片

`DR-0022` 证明文件夹工作现场基线；`DR-0023` 在此基础上新增限定范围的
Agent Control Loop `Limited Verified`：

- 完整 Python：`56 passed in 13.56s`；聚焦 Runtime：`19 passed in 0.95s`；
- Harness 浏览器：`9 passed in 21.7s`；Ruff、lint、build 与 diff-check 通过；
- 真实浏览器运行：2 轮、8 份文件、5 次模型调用、21 条事件、`71461 ms`；
- 第一轮候选计划被拒绝，最多一次预算内修复后通过；第二轮形成只读简报；
- 6 张桌面/移动截图及 SHA-256 绑定 manifest；390px 无页面横向溢出；
- 实现提交 [`8364b1e`](https://github.com/Dickey007s/lenovo_agent/commit/8364b1e403ce11c928683f28eb106ce218029315)；
- 当前交付 [PR #28](https://github.com/Dickey007s/lenovo_agent/pull/28) 为开放状态，不能表述为已经合并。

最终数字必须取自
[`AGENT-CONTROL-LOOP-BOUNDED-READONLY-20260825`](evidence/AGENT-CONTROL-LOOP-BOUNDED-READONLY-EVIDENCE-20260825.md)，
不得沿用旧版 PPT 或历史 Evidence。

## 8. 禁止对外表述

- “已经下载 FORTE 未公开的完整 180 条任务”；
- “FORTE 公开文件是真实 Lenovo 或客户企业数据”；
- “15 类 FORTE 任务已经全部解决”；
- “有引用就证明结论或数字正确”；
- “计划里出现操作，就说明工具或文件写入已经发生”；
- “当前三轮只读 Loop 已等同完整 Demo 1 Durable Runtime，或 Demo 2/3 已全部完成”；
- “内存 Snapshot 具备跨进程持久化或多实例高可用”；
- “Evidence Gate 已验证语义真值、数值正确性或业务完整性”；
- 在没有用户研究时声称“新界面更清晰、更可信或效率更高”。
