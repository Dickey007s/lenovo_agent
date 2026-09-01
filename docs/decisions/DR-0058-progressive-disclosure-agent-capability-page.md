# DR-0058：Agent 能力页四层渐进披露

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`；四层前台纵切已过工程门，体验效果仍为 `Draft` |
| 日期 | 2026-09-01 |
| 用户来源 | `USER-FEEDBACK-20260901-PROGRESSIVE-AGENT-CAPABILITY-PAGE` |
| 研究输入 | `PROGRESSIVE-DISCLOSURE-AND-ACCESSIBLE-TABS-20260901`、`HAI-MIXED-INITIATIVE-RESEARCH-20260830` |
| 前置决策 | `DR-0053`、`DR-0054`、`DR-0055`、`DR-0057` |
| 场景 | [`SCENARIO-045`](../scenarios/SCENARIO-045-progressive-agent-capability-review.md) |
| 测试合同 | [`AGENT-CAPABILITY-PROGRESSIVE-DISCLOSURE-GATES-20260901`](../testing/AGENT-CAPABILITY-PROGRESSIVE-DISCLOSURE-GATES-20260901.md) |
| Evidence | [`DR-0058-AGENT-CAPABILITY-PROGRESSIVE-DISCLOSURE-EVIDENCE-20260901`](../evidence/DR-0058-AGENT-CAPABILITY-PROGRESSIVE-DISCLOSURE-EVIDENCE-20260901.md) |

## 1. 问题

`DR-0057` 正确划分了 Workspace、Agent 能力页与未来智能工作驾驶舱，但首版能力页把
Loop 与 Adaptive Swarm 两块完整运行面左右并排。用户进入后同时面对 Round、Branch、
Evidence、Artifact、WorkUnit、Worker 和 Contribution，虽然字段真实，却无法快速判断
“现在是否需要我做什么”。

问题不是缺少信息，而是默认层级没有区分任务判断、过程追溯和协议审计。继续压缩字号或
增加卡片只会让页面更乱。

## 2. 决策

`/agent-capabilities` 保持单一 Task/Run/Snapshot，但改成四层渐进披露。默认层只显示用户
当前必须理解和处置的内容，过程和协议事实按需进入下一层。

### 2.1 第一层：任务进展

默认选中“执行进展”。首屏依次显示：

1. 当前 Task、Run、连接与历史只读身份；
2. 由真实状态确定性映射的简化阶段；
3. 至多一个当前主要待办；
4. Branch 完成/等待摘要；
5. 当前 ArtifactVersion 与保留边界。

“执行进展”和“协作方式”使用一级 segmented tabs，不再同时展开。任务会话历史改为按需
打开，不形成永久左栏。无 DecisionRequest 时不生成待办，`completed` 仍需人工复核。

### 2.2 第二层：完整执行记录

用户主动进入后才显示 Round 导航、Branch 记录、局部恢复和 ArtifactVersion 历史。
默认仅展开当前 Round 或异常 Branch；服务端事件、模型回执和后端字段继续折叠。

版本历史可以显示当前服务端摘要。没有可靠差异计算时不得提供假“版本比较”。

### 2.3 第三层：协作方式

“协作方式”从同一 Snapshot 投影 TopologyAdmission、WorkUnit 依赖、Contribution 返回/
采用和当前 Artifact。它先回答为什么选择当前 route，再形成一个可扫读的执行工作面：
左侧阶段轨说明准入、工作包、贡献汇合与成果进度；中央根据 `work_units[].depends_on`
动态排布根工作包和依赖工作包；右侧只显示由 waiting/blocked WorkUnit、等待中的
Contribution、DecisionRequest 或 Evidence Gap 推导出的当前影响；底部汇总返回、采用、
待确认和 Artifact 版本。Worker 回执与采用依据继续默认折叠。

Adaptive 正例必须显示“受限只读 Worker、单进程、每波最多 3 个”；Fixed Workflow 或
Single Controller 只显示真实准入结论，不填充假 WorkUnit。

### 2.4 第四层：确认结论依据

每次只处理一个 open DecisionRequest。页面用普通语言解释：系统发现什么、影响什么、
用户要做什么、哪些成果保留、系统不会做什么。候选必须来自服务端 packet，并通过安全
preview 按真实定位类型回开原文。

选择候选后才允许 accept；请求继续携带 `expected_version`、`idempotency_key`、
`decision_request_id` 和公开 `source_revision`。前端不得猜位置、放宽 stale/rejected 或
把局部恢复写成整条任务重跑。

## 3. 研究与实践依据

- Nielsen Norman Group 的 [Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/)
  建议首层保留核心功能、把低频高级内容延后，同时警告超过两层的连续嵌套容易让用户
  迷失。因此本方案不是要求用户依次穿过四层：默认进展分别直达执行记录、协作方式或
  原文核对，每条路径最多一次展开或一次专注跳转。
- Microsoft Research 的
  [Guidelines for Human-AI Interaction](https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/)
  支持在交互中说明系统能力、状态与后果，并提供纠错和控制；它不证明本项目的具体文案
  或页面一定有效。
- Horvitz 的
  [Principles of Mixed-Initiative User Interfaces](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/11/chi99horvitz.pdf)
  把“行动、询问用户、保持不打扰”视作不确定性下不同选择；本项目据此只在服务端形成
  open DecisionRequest 时突出人工待办，而不把所有 Evidence gap 都当成用户问题。
- W3C WAI-ARIA APG 的 [Tabs](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/) 和
  [Disclosure](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/) 约束 tab/panel 关联、
  `aria-selected/aria-controls/aria-labelledby`、方向键和展开状态。它们是可访问性实现依据，
  不是产品效果研究。

以上来源均不是本项目目标用户研究。四层信息架构仍需形成性走查验证。

## 4. 技术差异与交互后果

本次没有发明新的 Agent Runtime，而是改变同一服务端事实的呈现顺序：

| 技术事实 | 旧交互后果 | 新交互后果 |
| --- | --- | --- |
| Snapshot 同时包含 Loop 与 Swarm 事实 | 两块完整面同屏竞争注意力 | 同一 Run 下标签切换，身份不变 |
| Branch/DecisionRequest 是局部状态 | 用户先看到大量分支与协议术语 | 默认只看到一个可处置问题，完整记录按需查看 |
| ArtifactVersion append-only | 版本卡和过程混在一起 | 首屏只显示当前成果，历史进入第二层 |
| WorkUnit/Contribution 返回与采用分离 | Worker 明细占据主视图，依赖关系难以扫读 | 第三层用真实 DAG、当前影响和成果条先解释协作，回执折叠 |
| Evidence candidate 由服务端定位 | “缺引用/重试分支”难以理解 | 第四层直接选择真实原文位置并说明后果 |

这只是产品假设。不能由设计图或自动化宣称理解、效率或信任已经改善。

## 5. 前台与服务端事实

| 前台内容 | 服务端权威 | 当前边界 |
| --- | --- | --- |
| 当前/历史 Run | Task current pointer、Run list、Snapshot status/version | 最近记录不是无限 Task list |
| 简化阶段 | rounds、branches、status 与 terminal result 的确定性映射 | 阶段不是模型 CoT，也不证明业务正确 |
| 当前主要待办 | open `decision_requests`、waiting Branch | 多待办需稳定排序，不得丢弃 |
| 已完成/等待摘要 | `branches[]` 与 Evidence Gate | 完成只表示服务端记录通过当前门 |
| 当前成果 | `artifact_versions[]`、TaskCommit | 逻辑成果不冒充写回办公文件 |
| 协作拓扑 | `topology_admission/work_units/contributions` | 单进程受限只读 Worker |
| 原文选择 | DecisionRequest candidates、安全 preview、EvidenceResolution | 定位证明 location/membership，不证明 entailment |

## 6. 明确不做

- 不新增公开 API、Scenario selector 或 Demo 入口；
- 不硬编码概念图中的任务、日期、行号、来源数或工作包；
- 不实现或伪造智能工作驾驶舱、分布式 Worker、Tool Gateway 或外部动作；
- 不用前端文案覆盖 Snapshot 权威状态；
- 不把 Image2 概念图登记为运行截图或用户研究。

## 7. `Limited Verified` 结果

默认执行进展、按需完整记录、协作 tab、Worker disclosure、证据审查、history/current、
Fixed 反例、hash 刷新、键盘 tab、桌面/390 px 和全量回归已经通过工程门。实现集成到
`master` 的 `2673fe4` 至 `f0a281c`，测试与截图见 DR-0058 Evidence。

随后视觉重构集成到 `master` 的 `58b4958` 至 `4916fcb`：它移除旧 Worker 工作台整块
嵌套和重复摘要，统一为“执行进展/协作方式”两条主路径；协作方式按服务端实际路线显示
任务准入、工作包、贡献汇合、核验与成果，并把工作包、来源和执行回执分别折叠。固定
流程和 Adaptive Swarm 的受控 Fixture、1440/390 截图与最终 `77 passed` 见同一 Evidence。

Stakeholder 随后指出上述协作页仍只是摘要，不能清楚看出概念图中的 Adaptive Swarm
空间关系。第二次收敛由 Luna 分支 `db3f197`、`cbb2017`、`085c26e` 实现，并等价集成为
`master` 的 `09e246b`、`fbf142c`、`fe0878f`。Adaptive 正例现在显示任务/Run 上下文、
左侧阶段轨、真实 WorkUnit DAG、右侧当前影响和底部协作结果；Fixed/Single 仍不绘制假
DAG。定向 `9 passed`、全量 Playwright `80 passed`、Web lint/build/diff-check 和新增
1440/390 运行截图见同一 Evidence。

这只证明被测公共 Snapshot 映射和交互状态成立。真实 Provider、PostgreSQL 本轮复跑与
目标用户走查未执行，不能把本次状态写成体验改善或生产验证。
