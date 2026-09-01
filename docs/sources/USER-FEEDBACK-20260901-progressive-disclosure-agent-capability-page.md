# Stakeholder 反馈：Agent 能力页改为四层渐进披露

- Source ID：`USER-FEEDBACK-20260901-PROGRESSIVE-AGENT-CAPABILITY-PAGE`
- 日期：2026-09-01，Asia/Shanghai
- 来源类型：Stakeholder 浏览器试用反馈、Image2 概念方案确认
- 关联决策：`DR-0058`

## 原始问题

Stakeholder 在实际查看 `/agent-capabilities` 后指出，当前页面把 Agent Control Loop、
Adaptive Swarm、运行事实、证据和成果同时展开，信息过多、层级混乱。先前生成的一张
“大而全”控制台概念图也没有解决这个问题。Stakeholder 要求重新设计多个界面状态，
同时判断效果能否由当前系统实现，最终确认“按四层推荐方案落地”。

## 确认的四层方案

1. 默认“任务进展”只回答做到哪一步、是否需要处理、已经留下什么成果；
2. “完整执行记录”按需展示 Round、Branch、局部恢复和 ArtifactVersion；
3. “协作方式”单独展示真实 TopologyAdmission、WorkUnit 依赖、Contribution 采用和边界；
4. “确认结论依据”把协议状态翻译成单一、可处置的原文选择任务。

Loop 与 Adaptive Swarm 仍属于同一个 Agent 能力页并使用同一 Task/Run/Snapshot，但不再
同时全部展开。未来 Demo 2 智能工作驾驶舱边界继续沿用 `DR-0057`，本次不新增驾驶舱
队列或假入口。

## 概念参考图

以下图片由 GPT Image 2 根据产品事实边界生成，只用于信息架构沟通，不是运行截图、
用户研究或实现 Evidence：

- [默认任务进展](../evidence/assets/dr-0058-progressive-overview-concept.png)：`1672 x 941`、
  `1039205` bytes、SHA-256 `FBD2E18DDB105CB4DD4BEA93C434D7A9E6774CC4171B356FBBE13464B28B33D2`；
- [完整执行记录](../evidence/assets/dr-0058-execution-record-concept.png)：`1672 x 941`、
  `981907` bytes、SHA-256 `9D3DC65671F0347C214915F5639BE45F76EA5EBD399FA1E8880520AA574F4B4B`；
- [协作方式](../evidence/assets/dr-0058-adaptive-swarm-concept.png)：`1672 x 941`、
  `1008082` bytes、SHA-256 `2B1751912101821F52C85E4056C02BA49B5B239101935E8914EA4BE6E0747BDC`；
- [确认结论依据](../evidence/assets/dr-0058-evidence-decision-concept.png)：`1672 x 941`、
  `1096842` bytes、SHA-256 `D6EC9E5F2382115458F76C09EF8CD58AEA86BDF3B8EF60C4A26192F9B35DCC73`。

图片中的日期、任务文本、行号、状态和按钮视觉都不是服务端事实。实际实现必须从公共
Snapshot、安全 preview 和 DecisionRequest 生成；例如选中候选后确认按钮必须可用，
定位标签必须按文本行、表格行或页等真实 `locator_kind` 显示。

## 第二轮视觉纠正

第一轮视觉收敛后，Stakeholder 再次对照“协作方式”概念图，指出实现仍主要由路线卡、
阶段摘要和折叠区组成，看不出 Adaptive Swarm 的工作包依赖、局部阻塞和成果汇合。该
反馈要求协作页真正形成可执行的空间结构，而不是继续换文案或颜色：左侧阶段轨、中央
真实 WorkUnit DAG、右侧当前影响和底部协作结果必须在一屏建立关系；Fixed/Single 不能
为了接近概念图而生成假 DAG。

这仍是单一 Stakeholder 的设计验收意见，不是目标用户研究。它支持“实现是否忠于已确认
信息架构”的判断，但不证明新的工作面更易懂、更高效或更值得信任。

## 支持判断与局限

该反馈支持减少默认信息密度、采用渐进披露和普通用户语言，但它仍是单一 Stakeholder
反馈。自动化和截图只能证明工程行为，不能证明目标用户理解、效率、信任或任务成功率
已经提高；四层方案在形成性用户走查前仍只可标为产品假设。
