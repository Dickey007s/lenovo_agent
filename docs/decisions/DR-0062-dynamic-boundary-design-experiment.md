# DR-0062：动态边界与有界授权的离线设计对照

## 2026-09-12 产品方向纠正

来源：[用户要求在原系统整合](../sources/USER-FEEDBACK-20260912-integrate-copilot-in-existing-system.md)。本记录描述的独立原型只作为辅助研究材料保留，不是 Demo3 的产品交付形态。目标是在原 `/` 与 `/agent-capabilities` 中改进人机共驾，保留 Agent Control Loop、Adaptive Swarm 和同一 Task/Run/Snapshot，不能另起一套界面替代原系统。

前台目标是原有进展、协作与证据核对中的具体介入/继续流程；后端优先复用现有 Branch、DecisionRequest 与历史版本合同，超出合同的权限或外部动作另行评审。当前尚未完成新共驾交互的系统整合，不能把离线 model.js 或其测试作为权威执行证据。立即交付 [简短进展汇总](../reports/DEMO3-COPILOT-PROGRESS-BRIEF-20260912.md)，本轮不新增 HTML、不改 Runtime。下文旧记录保留其实际时间线，状态继续为 Draft。

## 元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Draft`，不是已经批准的产品策略或风险引擎 |
| 日期 | 2026-09-11 |
| 用户来源 | [USER-FEEDBACK-20260911-DYNAMIC-BOUNDARY-NOT-FIXED-LEVELS](../sources/USER-FEEDBACK-20260911-dynamic-boundary-not-fixed-levels.md) |
| 场景 | [SCENARIO-049](../scenarios/SCENARIO-049-dynamic-boundary-handoff-design.md) |
| 设计附件 | [HTML](../reports/copilot-boundary-design-20260911/index.html)、[设计详稿](../reports/copilot-boundary-design-20260911/design.md) |
| 研究来源 | [增量来源台账](../reports/copilot-boundary-design-20260911/research/sources.json) |
| Evidence | [DR-0062 Evidence](../evidence/DR-0062-DYNAMIC-BOUNDARY-DESIGN-EVIDENCE-20260911.md)、[本次验证](../reports/copilot-boundary-design-20260911/verification.md) |

## 场景与来源

办公人员把周报整理和交付委派给 Agent。任务中既有可保留副本的内部工作，也有外发、口径歧义、超权限承诺、版本变化、过期决定和执行结果未知。用户要求不被旧六级设计约束；历史 L0-L5 仅说明曾考虑过哪些交互，不作为新规则输入。

文献、官方工程文档与本项目推导分别记账。Intelligent AI Delegation 是框架提案；Anthropic 自治使用报告是观察性材料；Permission Policies 的模拟办公实验是关键反例，不能从少提示推出更安全，也不能从一次完整界面对比否定所有有界授权设计。具体日期、链接、阅读范围、实验限制保存在来源台账。

## 前台交互影响

候选方案为“有界授权 + 异常停靠”，与逐动作确认、粗粒度常驻规则比较。不是对任意操作开放的自动模式。

- 首屏为白底办公工作面：左侧合成情境，中央任务/保留分支/当前问题/预览/动作，右侧当前边界与可操作的情境变化。
- 不用 L0-L5 或 R0-R3 算出一个总分。分别呈现授权范围、内容依据、影响与可逆性、决定有效性、动作回执。
- 确认必须有明确对象且无预选；确认、提交、回执分开。5 分钟只是便于过期测试的示例参数，没有实证或政策阈值含义。
- 版本、对象或策略变化要求重新核对。结果未知优先查同一动作，不提供再次提交；取消也不能伪装成已经撤回。
- 内容澄清只更新模拟内容草稿；不授予外发权限。权限禁令只能阻止或降级，不能靠确认覆盖。
- 主动接管/延后撤销未用确认；交还控制不等于重新批准。A/B 成果固定保留只是情境输入，不是实际 Runtime 执行证据。
- 研究视图保留反证、适用边界和对照计划；验收视图提供操作和失败判据，不假装已有用户效果数据。

## 后端事实映射

**本原型没有后端事实，不能接入当前 API 作为授权器。** 所有事实来自本地 `model.js` 合成状态。网络 CSP 的 `connect-src 'none'` 防止页面连接 Runtime；这不是生产安全隔离证明。

| 离线字段 | 演示含义 | 将来所需权威，当前未实现 |
| --- | --- | --- |
| `permission` | 固定情境的授权允许/拒绝 | 经身份与组织政策检查的服务端决定 |
| `evidence/choice` | 合成统计口径及本地选择 | 当前证据合同扩展，不得挪用外发批准语义 |
| `approval.scope/expires/revoked` | 绑定动作/对象/版本/策略与模拟时间 | 服务端签发/存储、鉴权、失效、消费与版本竞争控制 |
| `receipt/attempts` | 固定成功或未知回执模拟 | Connector 的幂等键、独立回执与对账机制 |
| `paused/deferred` | 暂停或未决定；不自动续期 | 权威控制事件与安全点生效事实 |
| `events[]` | 本页内存序列 | 持久审计与可追溯真实执行事件 |

当前 `/agent-capabilities`、Task/Run/Snapshot、Worker 派发、DecisionRequest 与 API 不变；没有新增 Endpoint、Permit、Connector、Worker Runtime 或数据库表。

## 验证与边界

实际结果以链接的 verification 为准。状态单测和独立 Playwright 验证离线交互，不验证真实外部授权、安全性、恢复、多实例或用户理解。本原型没有真实模型调用，不修改业务文件。

下一阶段必须完成：服务端协议/威胁模型评审、单独实现与端到端验证，再进行固定任务的目标用户对照。预先确定误放行、误拒绝、包括配置的总耗时、恢复正确性和负担指标；不得在观察数据后补定成功标准。

## 2026-09-12：理解一致性迭代

- 场景与来源：[USER-FEEDBACK-20260912-USER-COMPREHENSION-AND-TESTING](../sources/USER-FEEDBACK-20260912-user-comprehension-and-testing.md) 要求考虑用户能否看懂；两位 Agent 源码走查不是目标用户研究。
- 前台交互影响：把当前成果、邮件状态、需要处理的原因、操作后果分开；附件/收件人变化显示前后值；选数据后显示数字和条件、当前 v3 与保留 v2；越权草稿持续警告；窄屏情境选择改用原生下拉，暂停不冒充人工编辑。
- 后端事实映射：仍无后端。`presenter.js` 只投影 `model.js`；`approval.reviewed` 留存演示确认的对象，`reconcile.result` 是人工配置的查询结果 fixture，不是 Connector 回执。查询失败/无记录均保留未知，禁止重发。已采用口径不可被另一个 `select` 静默改变，未知变更字段不能制造确认失效。
- 验证与边界：新增状态/业务文案测试、[形成性理解测试协议](../reports/copilot-boundary-design-20260911/comprehension-protocol.md) 和空白记录表。新结果以 verification 的日期小节为准；浏览器策略限制未解除，最终视觉/交互与真实用户理解没有验收，保持 `Draft`。

## 2026-09-12：共同参与与有效监督的研究增量

- 场景与来源：[委派调研请求](../sources/USER-FEEDBACK-20260912-delegated-copilot-research.md) 与 [6 篇论文、3 篇官方实践](../reports/copilot-boundary-design-20260911/research/followup-20260912/recommendations.md)。优先研究共同计划、错误修正与检查时机，保留“参与可能改坏正确方案”的反例，不回到固定等级。
- 前台交互影响：研究视图增加阅读顺序、论文/官方实践筛选、搜索、方法与限制展开。操作原型仍为原有八情境；[成对设计用例](../reports/copilot-boundary-design-20260911/research/followup-20260912/design-pairs.md) 只是待实施对照，没有伪装成已通过的测试。
- 后端事实映射：新增 JSON 台账与本地筛选纯函数，不引入服务端权威、共同计划 Runtime 或权限引擎；研究优先级不是风险等级。
- 验证与边界：新数据、筛选、排序与图标覆盖列入 Node 检查，结果另记 verification。定向读取不冒充全文精读；真人理解、最终浏览器、外部动作和论文复现仍未验证。
