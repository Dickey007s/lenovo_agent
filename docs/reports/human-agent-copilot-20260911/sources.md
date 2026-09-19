# 来源与事实台账

本包局部 Source ID；正式登记由主线集成处理。检索/源码读取日期：2026-09-11。

## 用户来源

### S-USER-MEETING

- 类别：stakeholder feedback，当前用户请求中的会议反馈。
- 原始关键表述：“人机共驾边界规则的系统化”“不同风险等级与接管方式的对应关系”“多场景/多边界类型的任务演示”“三个Demo完成后……新一轮调研”。
- 支持：本轮应产出结构化边界规则、案例和可视化评审材料，并明确后续技术回溯门。
- 不支持：已验证目标用户痛点、规则具有行业代表性或完整技术回溯已经完成。

### S-USER-UI

- 类别：用户提交的五张 UI 参考图，当前请求。
- 本目录保留图片 5 的原样副本 [reference-evidence.png](reference-evidence.png)，大小 `1,561,536` bytes。
- 私有来源核对 SHA-256：`c4d2e0abe1bb2435899e2d351ee91e32a91adc3b396bfec1156a58bcacbcb23b`。
- 直接可见：任务进展、执行记录、协作方式、原因/影响/保留项、并列候选位置与主次动作。
- 设计推断：用渐进披露避免把完整 Loop、拓扑和证据审查强行挤在一屏；候选不默认选中遵循当前 DR-0034，而不把参考图中的已选状态复制为初始默认。
- 不支持：图中虚构时间、行号、模型调用次数和状态为当前运行事实；参考图的可理解性已经经过用户研究。

## 当前代码与正式文档

读取时 HEAD：`8a5e01567ad89a24a6aac8ac8d58c438409c1346`。引用是当时工作树读取结果，不声称整棵工作树干净，也不把本轮未重跑的历史测试算成本轮验证。

### S-LOCAL-DECISION

- [HarnessRuntime](../../../services/api/app/application/harness_runtime.py)：`_decision_control_locked`，读取时从第 2973 行开始。
- [合同](../../../packages/contracts/harness_models.py)：`AgentControlLoopDecisionRecord`、`AgentControlLoopDecisionRequest`，读取时从第 445/475 行开始。
- [DR-0032](../../decisions/DR-0032-persistent-decision-and-local-recovery.md)、[DR-0033](../../decisions/DR-0033-closable-review-and-branch-lanes.md)、[DR-0034](../../decisions/DR-0034-one-action-recovery-and-explicit-source-choice.md)。
- 已读代码可支持：绑定 DecisionRequest/Finding/Resolution/Branch；接受候选必须带来源 revision、合法候选；服务端重读来源并重算候选；记录不同 decision_action；接受位置仅在 waiting Run 调度目标 Branch；决定固定无外部动作。
- 现有文档可支持：关闭先退出，defer 失败不锁住 UI；候选不预选；retry-only 不强迫补写内容。
- 不支持：通用 Permit、独立 Decision 数据库账本、多实例 lease、法律有效审批或任意业务正确性。

### S-LOCAL-RECOVERY

- [README](../../../README.md)、[ARCHITECTURE](../../ARCHITECTURE.md)、[WORKSPACE_AND_STREAMING](../../WORKSPACE_AND_STREAMING.md)、[API](../../API.md)。
- [DR-0059](../../decisions/DR-0059-explicit-requirement-accounting-and-bounded-analysis-recovery.md)、[DR-0031](../../decisions/DR-0031-active-budget-and-agent-owned-gap-recovery.md)。
- 当前默认预算与终态路径以最新 README/API/源码为准。DR-0031 的历史 `1200/3000` 与独立新 Task 表述不用于当前预算和同 Task child Run 结论。
- 支持：调用/采用分离、一次受控修复、Agent 自有缺口、局部暂停、active 时间冻结和有界续办。
- 不支持：无限重试、硬取消在途 HTTP、恢复一定提高分析质量。

### S-LOCAL-LINEAGE

- [DR-0053](../../decisions/DR-0053-durable-task-lineage-and-explainable-topology-admission.md)、[DR-0054](../../decisions/DR-0054-durable-task-ledger-and-current-run-cas.md)、[DR-0055](../../decisions/DR-0055-durable-workunit-and-contribution-ledger.md)。
- [HarnessRuntime](../../../services/api/app/application/harness_runtime.py) continuation / Worker / contribution 路径；本轮通过源码检索定位并结合最新入口文档核对。
- 支持：单 Task 的跨 Run 指针、Run/Task 两种版本边界、Branch 绑定 WorkUnit、不可变候选、显式受限 Worker、已返回不等于已采用。
- 不支持：远程 Worker、跨 Task 智能驾驶舱、分布式 lease、并行收益或本轮 PostgreSQL 复测通过。

### S-LOCAL-EFFECT

- [DR-0043](../../decisions/DR-0043-tc11-derived-release-gates.md)、[DR-0049](../../decisions/DR-0049-tc13-source-derived-customer-segmentation.md)、[DR-0050](../../decisions/DR-0050-tc14-source-derived-sre-incident-review.md)、[DR-0052](../../decisions/DR-0052-authoritative-outcome-and-narrative-reconciliation.md)。
- [合同](../../../packages/contracts/harness_models.py) 的 Artifact/EffectReceipt `sre_diagnosis_outcome` 字段，以及 [scenario_effects.py](../../../services/api/app/application/scenario_effects.py) 的 outcome 投影检索结果。
- 支持：固定能力中文件/业务/运行/真实动作分离；离线 SRE 提案 `approval_required`、`executed=false`；CRM 等外部动作未接入。
- 不支持：任意业务 Gate 或通用生产变更审批；本轮重新生成真实文件；连接 Elasticsearch 或执行 ES/HTTP 命令。

### S-LOCAL-GOVERNANCE

- [治理规则](../../DECISION_AND_REPORTING_GOVERNANCE.md)、[UI-server fact matrix](../../contracts/UI_SERVER_FACT_MATRIX.md)、[汇报口径](../../PRESENTATION_BRIEF.md)。
- 支持：每项主张必须有场景与来源、前台影响、后端事实、验证边界；Draft 不冒充实现；点击不是入账；官方文档不是竞品实测；位置不是语义证明。

## 官方定向来源

下列为 2026-09-11 通过联网检索取得的官方页面，页面抓取结果中阅读了相关段落。未固定完整网页快照；不承诺其后页面不变化。只作定向设计依据，不是完整行业技术回溯。

### S-NIST

- 类别：官方风险治理资料；[NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)，AI RMF 1.0（2023），GOVERN 3.2 / MEASURE 2.9 等。
- 支持：明确人机配置和监督责任；结合使用情境解释输出，并记录治理过程。
- 本包的 R0–R3、优先硬门和具体案例是项目设计推导，不是照搬 NIST 的规定等级。
- 不支持：本项目已符合某项法律、标准或已获得认证；NIST 为本案例提供了固定审批阈值。

### S-HAI

- 类别：Microsoft Research 官方研究总结；[Guidelines for human-AI interaction design](https://www.microsoft.com/en-us/research/?p=564561)，2019 研究工作；第 8/9/10/11/16 条。
- 支持：退出与纠错应便捷；不确定时缩小服务；解释行为原因和用户动作后果。
- 本包据此推导“一个问题一个动作”和“先退出再尽力 defer”，该具体交互仍需本项目用户验证。
- 不支持：本界面已提高效率、信任或准确率；默认三秒理解或满足普遍人群。

### S-LANGGRAPH

- 类别：官方框架文档；[LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)，2026-09-11 可见文档；`Rules of interrupts` 与 `Side effects called before interrupt must be idempotent`。
- 支持：中断依赖 checkpoint；恢复可能重跑节点前段，因此副作用需要隔离与幂等设计。
- 对本包的启发：确认、执行与结果必须分离，不能把恢复理解成任意在途调用无条件续接。
- 不支持：本项目使用 LangGraph、等同其 checkpoint 语义、已经实现外部执行幂等或竞品不具备局部恢复。

## 对外表达限制

可以说：已经制作人机边界设计沙盘，并基于当前有限合同整理出可复用的规则和案例。

不能说：Demo 3 通用风险引擎已经完成；全部业务都能自动判断风险；人确认以后即可执行外部动作；已经完成完整行业最新技术调研；页面模拟就是服务端 Evidence。
