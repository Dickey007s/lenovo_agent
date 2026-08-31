# SCENARIO-042：跨职能风险与待办简报的两波只读收敛

- 状态：`Draft`；场景合同与用户试用步骤已固定，源码/浏览器验收由独立开发任务执行中
- 日期：2026-08-31
- 决策：`DR-0055`
- 用户来源：`USER-FEEDBACK-20260831-DEMO2-INPUT-PROCESS-OUTPUT`
- 研究来源：OpenAI Agents SDK、Anthropic、A2A 1.0.0、Microsoft HAI 官方资料

## 1. 为什么选这个场景

07-16 的 Demo 2 不是“同时打开很多 Agent 对话”，而是智能工作驾驶舱面对多个工作信号
时，先解释任务优先级和执行路线，再把真正可独立核对的复杂工作交给受限 Worker，最后
只返回一个统一成果与待办入口。

当前产品尚未接入邮件、CRM、项目和日历 Connector，也没有完整的多任务驾驶舱。因此
本场景从 07-16 流程中截取已经具备后端事实的一段：用户选定一个跨职能任务后，系统如何
决定是否并行、怎样让三个工作包独立核对、怎样保留局部成果，以及怎样把结果收敛成一个
可审查的逻辑简报。未实现的上游信息聚合和 Connector 不会被截图或 Fixture 冒充。

## 2. 用户、触发与完成条件

- 用户：需要在一次管理复核中同时掌握产品上线、搜索 Agent 运行和用户交互风险，但不想
  管理多个 Agent 会话的产品负责人、项目负责人或研发经理。
- 触发：在 FORTE Workspace-first 资料库输入下面的普通办公指令；浏览器不提交隐藏
  `selected_file_refs`，服务端冻结 15 个目录、96 份输入的整库索引。
- 完成条件：三个独立根工作包和两个依赖工作包均有业务名称、批准来源、实际调用回执、
  Contribution 采用状态和 Evidence Anchor；第一波形成 v1，第二波只追加 v2；任一根
  工作包异常只阻塞依赖它的下游，兄弟成果和 v1 不被覆盖。

建议用户输入：

> 请分别核对产品上线、搜索 Agent 运行和用户交互三条工作线中最需要人工处理的风险与
> 证据，形成一份跨职能风险与待办简报。按工作包列出已核对来源、关键发现、缺口、受
> 影响下游和下一步；先独立核对，再统一收敛。不要修改源文件，不要执行代码，不调用
> 外部系统。

## 3. 输入是什么

固定自动化只使用 FORTE 公开 revision
`345c1ec1487139db9dd319787fa9405ba85d1869` 中十份真实输入的安全 Preview 形状。真实
Provider 运行仍由 Planner 在冻结整库索引中自主选择，不保证每次恰好选择这十份。

| 工作线 | 固定验收输入 | 输入作用 | 明确禁止的混用 |
| --- | --- | --- | --- |
| 产品上线 | `PRD_v2.5.md`、`上线配置清单.xlsx`、`功能测试报告.xlsx`、`线上兼容环境测试报告.xlsx` | 核对正式上线条件、配置、功能测试与兼容证据 | 不把算法或交互资料中的数字当作 AIPilot Console 的上线指标 |
| 搜索 Agent 运行 | `workflow.py`、`tools.py`、`search_agent.log` | 核对固定流程、工具边界和实际运行记录之间的风险 | 不执行代码，不把日志观察冒充生产系统当前状态 |
| 用户交互 | `交互行为痛点及优化规则.md`、`用户交互行为日志.xlsx`、`页面级交互规范.docx` | 核对交互痛点、规则和页面规范的来源关系 | 不把模型说明替代全量日志覆盖或用户研究 |

页面首先应显示系统实际批准的文件名和工作线。若 Planner 选出的来源不足以证明跨职能，
或把三条工作线混成一个不可分分支，`TopologyAdmission` 必须选择固定流程或单 Controller，
而不是为了演示强制并行。

## 4. 过程是什么

### 4.1 路线判断

服务端只读取 validated plan 的结构事实：工作包数量、独立根分支、依赖、来源
`display_group`、只读/人工门事实以及剩余模型调用和时间预算。三个根分支分别来自产品
管理、算法研发和用户体验，且 `external_action=none` 时，才可以建议
`adaptive_readonly_workers`。前台说明为什么值得并行、每波上限和当前只读边界；用户
确认前不得出现 Worker 调用或伪回执。

### 4.2 五个工作包

| 波次 | 业务工作包 | 批准输入 | 依赖 | 预期贡献 |
| --- | --- | --- | --- | --- |
| 第一波 | 产品上线 Gate 核对 | 产品上线四份资料 | 无 | Gate、测试/兼容缺口及来源位置，不作正式上线决定 |
| 第一波 | 搜索 Agent 运行风险核对 | `workflow.py`、`tools.py`、`search_agent.log` | 无 | 架构、工具和运行记录之间的风险与缺口，不执行代码 |
| 第一波 | 用户交互证据核对 | 交互规则、日志和页面规范 | 无 | 痛点、规则、规范之间可定位的证据与未覆盖项 |
| 第二波 | 产品影响与交互优先级核对 | 前两类已批准来源的受控并集 | 产品上线 Gate、用户交互证据 | 只比较影响和紧急度，不改写根工作包事实 |
| 第二波 | 搜索 Agent 风险与统一待办核对 | 搜索 Agent 批准来源及已采用贡献 | 搜索 Agent 运行风险 | 把运行风险变成待人工复核项，不把建议说成已执行 |

每个 Worker 返回先追加不可变 Contribution，再由服务端检查 Branch 来源范围、Evidence
Anchor、状态和适用的叙事/确定性对账。`model_called=true` 只证明发生调用；只有
`output_used=true` 且 Gate adopted 的 Finding 才进入当前成果。浏览器不从 Worker 文案
猜测来源，也不按返回先后决定谁覆盖谁。

### 4.3 版本收敛

第一波三个根工作包全部 adopted 后形成 `ArtifactVersion v1`。两个依赖工作包进入 ready，
第二波完成后追加 v2；v1、每条 Contribution、attempt 和 TaskCommit 继续可审查。当前
Runtime 的统一成果标题应说明它是“跨职能只读核对简报”或等价中文业务名称，而不是
只显示内部 `u1/u2` 或一堵 Worker 聊天记录。

## 5. 输出是什么

### 5.1 当前真实输出

当前可交付的是一个可在页面审查和恢复的逻辑成果版本，不是下载文件：

- v1：三条根工作线已采用的 Finding、批准来源、Anchor 和仍待处理的下游；
- v2：在 v1 基础上追加两条优先级/待办收敛结果；
- WorkUnit 台账：业务名称、依赖、状态、attempt、批准来源和失败影响；
- Contribution 台账：已返回、已采用、等待或拒绝，以及 `model_called/output_used/elapsed_ms`；
- 边界回执：未修改源文件、未执行代码、未调用外部系统，结论仍需人工复核。

前台必须直接写明“当前为逻辑成果版本，可审查和恢复；尚未生成 DOCX/CSV 下载文件”。
这避免用户把 `ArtifactVersion` 误解为已经存在于运行工作区的办公文件。

### 5.2 尚未实现的后续输出

后续可以由服务器拥有的确定性 renderer 从 adopted Contribution 生成
`跨职能风险与待办简报.docx` 和 `工作包贡献台账.csv`，再由独立 Verifier 重读来源与
成果。该 renderer、文件合同和下载验收尚未实现，当前文档不把它列为本场景完成条件。

## 6. 失败与停顿怎样呈现

### 6.1 搜索 Agent 来源位置歧义

- 触发：搜索 Agent Worker 的逐字 quote 在批准文件中有多个位置，或没有唯一 Anchor。
- 服务端：该 Contribution 为 waiting/ambiguous，不进入成果；产品上线与用户交互两个
  根工作包仍 adopted，并形成部分 v1。
- 依赖：产品影响与交互优先级工作包可继续；依赖搜索 Agent 的统一待办工作包 blocked。
- 前台：显示“已有 2 项进入成果，搜索 Agent 工作包需核对原文位置”，并列出受影响
  下游；不显示整项任务失败，也不清空 v1。
- 当前边界：首版没有 Worker 专属 `DecisionRequest`，不得声称用户点一次候选后就能
  续跑远端 Worker。

### 6.2 候选被服务端拒绝

越 Branch 来源、缺 Anchor、来源 revision 变化、候选篡改或叙事与权威事实冲突时，保留
“模型已返回”的回执，但显示“未进入成果”和中文原因。拒绝项不得改变已采用兄弟项和
旧版本；Catalog/Preview 完整性失败仍必须整条路径 fail closed。

### 6.3 同结构三期财务反例

三份往来明细同目录、同结构、强顺序依赖，应继续选择 `fixed_workflow`，输出未付统计、
未收统计和跨期说明；不创建 Worker/Contribution。这个反例证明 Demo 2 的核心包含
“不该并行时不并行”，而不是把任何多文件任务变成 Swarm。

## 7. 技术差异怎样改变用户流程

主流方案已经提供 manager/handoff、并行 subagent、Task、Artifact 和流式状态。本项目
不声称竞品做不到，而把可证伪差异收敛为办公交付合同：路线由服务端结构事实准入；每个
Worker 只能使用 Branch 批准来源；返回与采用分开；统一成果 append-only；局部失败必须
说明受影响下游。

这把用户流程从“自己开三个对话、复制结果、猜哪个可信”改为“看路线理由并确认一次、
只处理例外、审查一个带来源与版本的统一成果”。是否真的降低认知负担仍要通过目标用户
研究验证，自动化和截图不能证明。

## 8. 研究依据与局限

- [OpenAI Agents SDK: Agent orchestration](https://openai.github.io/openai-agents-python/multi_agent/)
  区分 LLM 编排与代码编排，并指出并行适用于互不依赖的任务。它支持本场景用服务端 DAG
  控制并行，不证明本项目的实现更好。
- [Anthropic: How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
  报告 breadth-first 独立方向适合多 Agent，同时说明协调复杂度、强依赖不适配和明显的
  Token 成本。文中数值属于其内部系统与评测，不能外推到本项目。
- [A2A Protocol specification 1.0.0](https://a2a-protocol.org/latest/specification/)
  把 Task、Message、Artifact、按序更新和不暴露内部思考的协作模型分开。本项目只借鉴
  对象边界，不宣称兼容 A2A。
- [Microsoft Research: Guidelines for Human-AI Interaction](https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/)
  提供 18 条 HAI 指南并经过 49 名设计从业者、20 个产品的多轮评估。它支持显示能力
  边界、状态、后果和纠错入口，不证明本场景 UI 已经通过用户研究。

## 9. 当前边界

- 当前 Worker 是当前 API 进程内、每波最多三个的只读 Analyst Worker，不是 distributed
  queue、lease、远端 Worker 或递归 Swarm。
- Fixture 可固定输入、DAG 和异常；真实 Provider 可能选择单 Controller 或固定流程，
  前台必须如实显示，不能为了演示伪造 adaptive route。
- Anchor 证明位置和批准来源 membership，不证明语义、穷举、算术或业务正确。
- 当前没有下载版跨职能简报、真实 Connector、源文件写回、代码执行或外部动作。
- 用户理解、信任、速度、成本和业务质量均仍为 `Draft`，需要形成性用户研究。
