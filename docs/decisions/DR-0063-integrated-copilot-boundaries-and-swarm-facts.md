# DR-0063：原系统内的共驾边界解释与协作事实

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`，仅既有合同的前端投影；最终范围见 Evidence |
| 日期 | 2026-09-12 |
| 用户来源 | [边界、案例和蜂群差异要求](../sources/USER-FEEDBACK-20260912-boundary-cases-and-swarm-differentiation.md) |
| 前置 | DR-0032/0033/0034/0038/0043/0053/0055/0061/0062 |
| 场景 | [SCENARIO-050](../scenarios/SCENARIO-050-understand-boundaries-and-worker-adoption.md) |
| Evidence | [DR-0063 Evidence](../evidence/DR-0063-INTEGRATED-BOUNDARIES-AND-SWARM-FACTS-20260912.md) |
| 研究 | [八案例指导稿](../research/DEMO3-BOUNDARY-RULES-AND-CASES-20260912.md)、[蜂群机制与差异](../research/DEMO2-SWARM-MECHANISM-AND-DIFFERENTIATION-20260912.md) |

## 场景与来源

Demo1 管时间连续性，Demo2 管组织与贡献，Demo3 管参与理由、决策权限与后果。暂停/继续是底层机制，不足以定义人机边界。研究把证据、后果、权限、版本、回执分开；定性后果标签仅用于案例评审，不是已接入的风险分数或授权引擎。

## 前台交互影响

1. 原 `CapabilityProgress` 增加“人机共驾边界”，用 Agent / 你 / 动作限制说明既有状态，不新建页面或按钮。
2. 来源多候选、普通人工判断、待决资料不完整、Worker 本批确认、分支恢复、业务 Gate 未通过分别解释，可同时存在。历史只读优先；没有待决不自动表示任务成功。
3. 不把“选原文”“允许一次只读计算”写成业务审批。终态来源选择只记录决定，同 Task continuation 仍是独立动作。
4. 原 `CollaborationOverview` 前置准入、Worker 调用/采用、贡献候选的采用/拒绝/等待；零回执不从图推断实际调用。单主控和固定流程分别说明。
5. 进展页 ready 工作包明确“就绪，尚未派发”，确认范围的文件来自本批 ready Branch，而非另一条 waiting Branch。
6. 依赖线使用分别连接起终节点的曲线，避免多个正交路径重合成虚假的共用总线。准入预算明确是准入时取值，不冒充实时余额。

## 后端事实映射

投影函数 `projectCopilotBoundaries` 不调用工具、不改 Snapshot、不创建授权。采用顶层待决与已解析的可操作 Resolution、Branch、当前 Round ready IDs、TopologyAdmission、BusinessGateOutcome。规则只组织已有事实的解释，权限仍由既有服务端合同决定。

`worker_runs` 按回执计数，不冒充唯一 Agent 数或累计所有历史贡献；`contributions` 独立按 gate_status 计数，不把同一 attempt 的两份台账相加。来源与位置校验不证明语义/业务/全文覆盖。

完整映射见 [UI-server fact matrix](../contracts/UI_SERVER_FACT_MATRIX.md)。API path、operation、数据库与 Worker Runtime 均不变；不新增 Demo/Scenario 选择器。

## 验证与边界

前端纯函数、原系统 Playwright、1440/390 px 截图、类型检查与 Demo2 Runtime 单元门分开记账。研究、测试 Fixture、真实模型任务、数据库恢复和目标用户理解不可互相替代。

本轮没有实现长文续读/覆盖门、规则批准、外发授权、组织角色、Connector 执行/未知回执对账。DR-0062 离线实验未因本次解释层而成为产品执行引擎；完整 Demo3 多场景闭环仍待逐项落地，不能报告“Demo3 全部整合完成”。

## 可证伪价值

期待用户更准确区分执行问题、依据选择与业务许可，但尚未通过真人研究。蜂群工程差异候选是来源约束准入、贡献采用、局部恢复及长期成果历史的组合，未完成同预算竞品对照，不称新算法或性能领先。
