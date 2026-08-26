# 以办公文件夹为中心的 Office Agent：技术对比、场景来源与交互影响

## 1. 文档用途

这是后续汇报长期保留的中文研究与设计记录。它把技术架构连接到用户流程
和前台输出，并严格区分：

- 官方产品事实；
- 论文或工程实践启发；
- Stakeholder 需求；
- 当前实现与运行证据；
- 尚未验证的设计假设。

状态：`Research and design record`。下列产品事实绑定到指定来源和访问日期；
关于易用性、信任、速度或用户价值的相对判断，在完成目标用户研究前一律为
`Draft`。

> 2026-08-26 竞争事实修订：本文保留为 Workspace-first 交互来源记录，不再作为当前
> 竞品能力上限。OpenAI 已将 Codex 明确扩展到报告、表格、演示文稿、合同、研究与跨职能
> 知识工作；Microsoft 365 Copilot、NotebookLM（当前官方帮助页重定向为 Gemini Notebook）、
> ChatGPT deep research 和 Claude Research 也覆盖多来源研究与引用。当前能力底线、可证伪
> 差异候选和八个同场挑战以
> [`COMPETITIVE-WHITE-SPACE-AND-FALSIFIABLE-DIFFERENTIATORS-20260826`](COMPETITIVE-WHITE-SPACE-AND-FALSIFIABLE-DIFFERENTIATORS-20260826.md)
> 为准。本文后文的产品定位只解释交互来源，不能用于“竞品不能做”的结论。

## 2. 来源台账

| Source ID | 类型与精确来源 | 版本/日期 | 支持的判断 | 局限 |
| --- | --- | --- | --- | --- |
| `OPENCLAW-OFFICIAL-20260825` | [OpenClaw overview](https://docs.openclaw.ai/)、[runtime architecture](https://docs.openclaw.ai/agent-runtime-architecture)、[exec approvals](https://docs.openclaw.ai/tools/exec-approvals) | 2026-08-25 访问 | 官方材料描述自托管 Gateway、Session/Route、内置或插件 Harness、Tool 和主机执行审批 | 不证明其没有办公文件证据交互，也不证明本项目优于它 |
| `OPENAI-CODEX-APP-20260202` | OpenAI，[Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/) | 2026-02-02 | 官方材料描述并行 Agent Task、Worktree、变更审查、Skill 和 Automation 审查队列 | 面向软件开发，不是直接办公任务基准 |
| `CLAUDE-CODE-OFFICIAL-20260825` | Anthropic，[How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)、[subagents](https://code.claude.com/docs/en/sub-agents)、[permissions](https://code.claude.com/docs/en/permissions) | 2026-08-25 访问 | 官方材料描述项目目录上下文、Tool Loop、Subagent、Permission 和多种界面 | 面向代码与项目工作流，不能证明本项目的易用性 |
| `REACT-ICLR-2023` | Yao 等，[ReAct](https://arxiv.org/abs/2210.03629) | ICLR 2023，arXiv v3 | Reasoning、Action、Observation 交替可用于组织 Agent 轨迹 | 不直接给出持久状态、办公文件 UI、策略编译或引用控制 |
| `FORTE-PINNED-20260825` | [AGI-Eval-Official/FORTE](https://github.com/AGI-Eval-Official/FORTE)，commit `345c1ec1487139db9dd319787fa9405ba85d1869` | 2026-08-25 固定 | 公开办公基准覆盖 15 类职业，公开仓库每类提供一个 Demo | 公开基准不是真实企业生产数据库或用户研究 |
| `USER-FEEDBACK-20260825-WHOLE-FOLDER-14` | [Stakeholder 反馈](../sources/USER-FEEDBACK-20260825-14-folder-workspace-and-interaction-reporting.md) | 2026-08-25 | 要求完整文件夹浏览、文件信息、四类格式预览/控制和汇报留痕 | 单一 Stakeholder，不代表目标用户研究 |
| `USER-FEEDBACK-20260825-WHOLE-WORKSPACE-18` | [Stakeholder 反馈](../sources/USER-FEEDBACK-20260825-18-autonomous-whole-folder-research.md) | 2026-08-25 | 要求把 FORTE 资料呈现为一个可自由浏览的文件仓库；用户只描述目标，由 Agent 自主选证据、循环研究并提出下一步任务 | 单一 Stakeholder，不证明自主选证据的质量、效率或用户价值 |

## 3. 主流方案差异及其交互后果

这里比较的是官方材料中的设计侧重点，不是排他性能力声明。OpenClaw、
Codex 和 Claude Code 仍在持续迭代，也可以扩展。本文不声称它们无法实现
下列任何模式。

| 方案 | 官方材料中的主要交互对象 | 强调的设计能力 | 本项目刻意强调的差异 | 对用户流程的影响 |
| --- | --- | --- | --- | --- |
| OpenClaw | Message、Session、Channel、Gateway | 常驻多 Channel Agent、路由、工具和主机审批 | 把服务端拥有的完整办公资料仓库、Agent 逐轮选证据及来源引用放到交互主路径 | 用户先浏览资料与说明目标，再监督 Agent 为什么读这些文件，而不是从消息 Channel 开始 |
| Codex App | 项目 Task、Worktree、审查队列 | 并行软件任务、隔离改动和结果审查 | 公开办公文件是只读证据；Agent 自主检索，计划与结论必须回到具体业务文件核对 | 用户审查业务结论、选证据理由和引用，而不是代码 Diff 或 Worktree |
| Claude Code | 项目目录、Terminal/IDE Agent Loop | 广泛项目上下文、Tool、Subagent、Permission 和 Checkpoint | 服务端先建立安全完整索引，再按每轮预算向模型开放有限文件正文；控制不依赖用户替 Agent 选文件 | 用户少做一次机械范围选择，改为监督逐轮证据选择、预算和下一步推进 |
| ReAct 类 Agent | Reasoning、Action、Observation 轨迹 | 通过环境反馈迭代更新计划 | 普通 UI 展示调用、业务操作、校验和回执，不展示思维链 | 用户能看见什么被调用、采用和拒绝，同时避免暴露私有推理 |
| 当前 Office Agent | 完整资料仓库、用户目标、逐轮证据、Run Snapshot、引用与下一步建议 | 以来源为先的 Agent Control Loop 与服务端策略 | 一个文件管理器承载任意原创任务；Agent 自主找材料，Demo 只作为能力验收视角 | 浏览 -> 下达目标 -> 观察选证据与路径 -> 复核结果 -> 人确认下一轮 |

## 4. 为什么架构会改变界面

### 4.1 服务端拥有文件目录

**技术差异：** 文件身份、manifest 完整性、格式解析和安全投影由服务端拥有，
而不是由浏览器根据文件名猜测，也不是由模型生成。

**前台影响：** 用户看到普通文件夹树、文件类型、大小、行数或页数及安全说明。
完整性失败与网络失败分开显示；路径和 hash 只进入审计层。

### 4.2 整库合同与逐轮自主证据

**技术差异：** 每个 Run 冻结完整安全索引。Planner 可以读取全库公共元信息，
但服务端按每轮文件预算编译计划；Analyst 只能读取本轮经服务端批准的正文，
计划或结果引用超出冻结集合时确定性拒绝。

**前台影响：** 用户不再替 Agent 勾选文件。轨迹会解释本轮采用哪些文件、为何
采用；结果引用仍可回到原文件。控制权从“手动准备上下文”转成“监督选证据、
限制预算并确认是否继续下一轮”。

### 4.3 模型意图与确定性策略编译分离

**技术差异：** 模型只提出业务意图；服务端编译 effect/gate 策略，并校验依赖、
工具、来源和引用。

**前台影响：** “模型已调用”“内容已采用”“服务端已校验”分别展示。模型已经
返回但校验不通过时，前台显示“未采用”，不会伪装成成功步骤或模糊网络错误。

### 4.4 有序事件与权威 Snapshot

**技术差异：** named SSE 解释进度，Run Snapshot 是状态权威；sequence 用于
断线恢复，前端不得补造进度。

**前台影响：** 用户看到业务轨迹、调用耗时回执、重连状态和最终对账。
单纯动画永远不能证明模型调用或任务完成。

### 4.5 结果中的原位证据

**技术差异：** 每项 Finding 必须引用一个或多个已冻结文件。文件集合成员关系
可以确定性校验，但语义正确性不能仅靠引用验证。

**前台影响：** 引用是可操作按钮，而不是脚注装饰。点击后返回同一个安全预览。
终态仍标记“待复核”，因为引用范围正确弱于事实蕴含或数值正确。

## 5. 具体办公场景

| 场景 | 触发条件 | Demo 验收视角 | 人的角色 | 完成证据 |
| --- | --- | --- | --- | --- |
| 跨期财务核对 | 三个期间工作簿需要比较 | Demo 1 单任务有界循环 | 决定有歧义的会计口径并复核总额 | 选定 Sheet、确定性总额、引用行、人工确认输出 |
| 入职物资匹配 | 人员 CSV 需要匹配 PDF 制度 | Demo 1 加证据暂停 | 解决缺失或冲突的分配规则 | 匹配表、异常清单、规则引用 |
| 简历与 JD 对比 | 两份岗位说明和多份候选人材料 | Demo 2 多任务组织 | 保留招聘决定权并审查敏感信息 | 候选人证据、跨 Worker 一致性、人工回执 |
| 上线准备核对 | PRD、配置和测试报告存在冲突 | Demo 2 自适应汇聚 | 决定未解决的上线冲突 | Worker 图、冲突汇聚、被引用报告集合 |
| 故障诊断 | 日志需要整理时间线和修复建议 | Demo 1 加 Demo 3 Risk Gate | 任何真实命令都需要人批准；当前保持只读 | 日志行引用、动作建议、明确未执行回执 |
| 外部 SQL 或定时 Web 任务 | 没有本地输入，需要 Connector | Demo 3 能力边界 | 批准范围、凭据和副作用 | 当前预期结果是确定性能力阻断 |

15 类任务测试目录见
[`FORTE-PUBLIC-OFFICE-TASK-TEST-CASES-20260825`](../testing/FORTE-PUBLIC-OFFICE-TASK-TEST-CASES-20260825.md)。

## 6. 纳入产品的人机交互方向

1. **混合主动的数据范围控制**：Agent 在完整安全索引中自主选证据，服务端限制
   每轮读取预算；新任务和高影响范围扩张必须由人确认。
2. **渐进披露**：先展示文件和结果摘要；安全、校验和详细轨迹可展开，但不占据
   第一注意层。
3. **不暴露思维链的可理解执行**：展示调用、操作、校验、回执和引用，不展示
   私有推理文本。
4. **把来源变成导航**：引用返回准确文件预览，让复核成为主路径而不是附加说明。
5. **可恢复协作**：幂等启动、单调 Snapshot 和 SSE resume，避免重试时静默创建
   第二任务或回退状态。
6. **与拓扑无关的通用能力**：Workspace、Source、Policy、Event 和 Evidence
   组件同时服务单任务、Swarm 和受控动作；Demo 名称不是能力开关。
7. **不确定性下保留人的权力**：Schema/Policy 失败时安全停止；语义或数值不确定
   显示为待复核工作，不藏在完成动画后面。

## 7. 前台输出契约

| 状态 | 用户看到什么 | 服务端事实来源 | 默认隐藏 |
| --- | --- | --- | --- |
| 文件库可用 | 文件夹/文件数量和可搜索树 | 校验后的 Workspace 公共投影 | benchmark 任务、rubric、solution、原始 manifest |
| 文件打开 | 元信息、安全预览和安全说明 | 完整性校验后的文件预览接口 | 完整二进制、宏、外部加载、路径、hash |
| 任务草稿 | 用户目标和可调循环预算 | 浏览器草稿 | 不声称服务端已接受或已选定证据 |
| 任务已接受 | 整库索引已冻结和第一条轨迹 | POST Run 响应与 seq 1 | 主文案隐藏内部 Run ID、路径与 hash |
| 本轮选证据 | 文件业务标签、选择理由和数量 | 服务端编译后的 `input_file_refs` 与公开元信息 | 未采用文件正文、Prompt 与内部检索分数 |
| 模型运行或返回 | 模型名、耗时、已采用或未采用 | Model Receipt | Prompt、思维链、原始返回 |
| 计划已接受 | 可读的有序工作计划 | 服务端编译并校验的 Plan | 原始 effect/gate 标识 |
| 结果可复核 | 初步结论、引用按钮、复核提醒及 Agent 下一步建议 | 引用属于冻结 `file_ref` 的校验结果；建议属于终态 Snapshot | 正确性、外部动作或建议已执行的声明 |
| 人确认下一轮 | “确认并启动”与新 Run 状态 | 独立 POST Run 的新 `run_id` 与幂等键 | 不把建议卡冒充后台自动执行 |
| 事件流中断 | 重连中和重试入口 | Transport 事实与最后 sequence | 补造的进度 |
| 完整性异常 | 明确的来源异常与安全停止 | Catalog 控制的 503 | 部分或陈旧目录 |

## 8. 当前实现事实与未验证假设

### 已实现并有工程证据

- 一个包含 15 个文件夹、96 份文件的公开 Workspace；
- XLSX/CSV、PDF、DOCX、TXT/代码的有界预览；
- manifest、大小、hash、路径、符号链接、压缩结构和 active content 控制；
- 完整资料仓库的统一文件管理器、搜索与安全预览；
- 用户只提交原创目标；Agent 读取全库公共索引并自主选择逐轮证据；
- 服务端按轮次限制文件正文、编译计划、校验模型回执、有序事件和引用；
- 终态产生最多四项下一步建议，人确认后才启动独立新 Run；
- 只读结果和“没有外部副作用”边界。

### 尚未证明

- 用户理解文件夹优先流程是否快于旧 Scenario UI；
- Agent 自主选证据是否提高任务成功率，或会不会漏掉关键文件；
- “确认下一轮”的交互是否在控制感与操作成本之间达到合适平衡；
- 引用是否提高校准后的信任或错误发现率；
- 模型是否能正确完成全部 15 类 FORTE 任务；
- 持久化恢复、分布式 Worker、真实文件写入或 Connector；
- 生产身份、企业数据策略和代表性用户价值。

## 9. 后续汇报检查表

从本文产生的每一页 PPT 或 Demo 结论都必须包含：

- 一个具体用户场景和异常路径；
- 一个精确 Source ID 及其局限；
- 技术差异以及由此产生的用户流程变化；
- 前台可见状态、动作、反馈和恢复方式；
- 对应后端事实与默认隐藏的内部细节；
- 当前 Evidence 状态和它不能支持的结论。
