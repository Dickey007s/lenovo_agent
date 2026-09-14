# SCENARIO-049：周报交付中的动态边界与接管

状态：`Draft`。独立研究原型情境，不注册为产品 Scenario。

2026-09-12 产品方向纠正：上句只描述已存在的离线研究材料，不代表未来产品要独立建设。按 [最新反馈](../sources/USER-FEEDBACK-20260912-integrate-copilot-in-existing-system.md)，Demo3 交付必须整合到原任务进展、协作和证据核对界面，保留 Loop 与 Adaptive Swarm。当前先交付 [汇报简稿](../reports/DEMO3-COPILOT-PROGRESS-BRIEF-20260912.md)，尚无本轮集成验收证据。

| 字段 | 内容 |
| --- | --- |
| 目标用户 | 负责项目周报与客户沟通的办公人员；案例角色和资料为合成 |
| 触发 | 内部整理结束，准备对外提交；或任务中发生依据、授权、版本、回执变化 |
| 当前痛点 | 所有异常都用“确认继续”会混淆内容判断、权限与执行；用户也可能机械批准 |
| 目标 | 让人明确决定对象、影响、允许范围与恢复方式，同时避免未获授权动作 |
| 完成条件 | 每个边界可解释且可退出；确认不等于执行；未知结果不重放；其他成果保留 |
| 顺利路径 | 核对具体范围 → 显式确认 → 仍未提交 → 提交前再验证 → 模拟回执，真实动作 0 |
| 异常路径 | 歧义须选择口径；越权不显示授权入口；版本/策略变化或过期使旧确认失效；丢回执先查询；主动接管撤销未用确认 |
| 来源 | USER-FEEDBACK-20260911-DYNAMIC-BOUNDARY-NOT-FIXED-LEVELS、动态边界增量研究；不是代表性用户研究 |
| 前台影响 | 同屏预览与范围，按问题给不同动作；情境变化在折叠面板中；无默认选择 |
| 后端事实 | 当前没有后端，见 DR-0062 的“本地模拟字段 → 将来服务端权威”表；不伪造 owner/CAS/持久回执 |
| 验证与边界 | [离线验证](../reports/copilot-boundary-design-20260911/verification.md)；不证明生产安全、用户效果或当前 Runtime 能力 |

八条可操作验收路径见 [HTML 验收视图](../reports/copilot-boundary-design-20260911/index.html) 和 [设计说明](../reports/copilot-boundary-design-20260911/design.md)。

2026-09-12 补充：用户需能区分“已确认但没发送”“尝试发送但结果未知”“只更新数据草稿”。查询失败或无记录不得被显示为未发送，内部留档不得被误认为删除了未获批承诺。当前稿与历史稿须各自标识。形成性用户任务 U1-U5 见 [协议与判定](../reports/copilot-boundary-design-20260911/comprehension-protocol.md)，目前没有参与者数据，完成条件仍未经过用户验证。

同日研究增量：[推荐阅读与 Demo 映射](../reports/copilot-boundary-design-20260911/research/followup-20260912/recommendations.md) 补共同计划、参与反效果和检查时机；[五组成对用例](../reports/copilot-boundary-design-20260911/research/followup-20260912/design-pairs.md) 要求同时记录误放行、误阻塞、完成情况与总成本。共同计划编辑、真实依赖传播与权限委派尚未实现，不增加已完成情境计数。
