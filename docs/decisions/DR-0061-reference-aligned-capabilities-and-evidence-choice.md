# DR-0061：参考图驱动的能力页重设计与明确证据选择

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`；范围和最终工程门见 Evidence |
| 日期 | 2026-09-11 |
| 用户来源 | [USER-FEEDBACK-20260911-DEMO12-REFERENCE-UI-AND-COPILOT-BOUNDARIES](../sources/USER-FEEDBACK-20260911-demo12-reference-ui-and-copilot-boundaries.md) |
| 前置决策 | DR-0032、DR-0033、DR-0034、DR-0053、DR-0055、DR-0058、DR-0059、DR-0060 |
| 场景 | [SCENARIO-048](../scenarios/SCENARIO-048-review-progress-collaboration-and-evidence-choice.md) |
| Evidence | [DR-0061-EVIDENCE](../evidence/DR-0061-REFERENCE-ALIGNED-CAPABILITIES-EVIDENCE-20260911.md) |
| 视觉核查 | [design-qa.md](../../design-qa.md) |

## 1. 决策与前台交互影响

`/agent-capabilities` 不新增 Runtime。保留同一 Task / Run / Snapshot 的两个同级能力维度，
改为白底、浅灰分隔、蓝色主要操作、绿色保留成果与橙色局部待确认的办公界面。

1. 默认任务进展：五个阶段分别根据本轮来源、Plan、采用回执、Evidence Gate、Artifact 取事实。
2. 执行记录：按轮查看分支、资料、阶段、成果与回执；完整协议放在额外 disclosure 中。
3. 协作方式：WorkUnit DAG、实际依赖箭头、局部影响与 contribution adoption；不硬编码三条业务分支。
4. 专注核对：候选原文单选、无默认项、显式确认；查看原文不等于选中候选。
5. 全局操作：任务历史、新任务草稿、暂停、下一轮调整、停止并保留、成果与版本历史复用既有控制协议。

## 2. 后端事实映射

| 前台事实 | 权威 | 不允许的推断 |
| --- | --- | --- |
| Run 当前/历史 | Task current pointer | 不从最近列表顺序推断当前 Run；未知时禁用写操作 |
| 阶段完成 | 当前 Round 各独立字段 | Artifact 存在不等于分析采用或 Gate 通过 |
| 分支保留 | `branches[].status/verified_file_refs` | 不从动画或上一轮视觉推断完成 |
| 工作包连接 | `work_units[].depends_on` 与稳定 ID | 不造展示连线，不证明分布式或并发执行 |
| 证据选择 | 顶层 `decision_requests[]` + 精确 `resolution_id` | 同 Finding 的多个 Resolution 不合并；旧嵌套副本不覆盖顶层来源版本 |
| 来源过期 | `decision_requests[].state=stale` | 不归一化成 pending，不继续要求确认过期候选 |
| 确认结果 | 控制响应与刷新 Snapshot | 响应丢失是结果未知，不断言未写入 |
| 终态选择 | `decision` 的记录回执 | 不承诺原地续跑；仍需单 Branch `/continue` 创建 child Run |

## 3. 恢复与可访问性

关闭或 Escape 先退出核对页，再 best-effort defer；失败留在工作面，不把用户困在页内。
候选用原生 radio；未选时禁用 accept；预览按钮不改变选择。焦点在对话框内循环。
分支 action 使用服务端 ID；终态 Run 只能通过既有 continuation，其他分支与不可变成果保留。
工作包保持固定尺寸，窄屏在图内横向浏览，页面不横向溢出。
切换能力视图、执行记录或 Run 时回到工作面顶部，保留可见的当前任务和返回入口。

## 4. 非目标和汇报口径

本轮未新增 API、数据库迁移、模型 Provider、通用办公写入、生产身份或分布式 Worker。
Demo 3 的 [独立人机共驾设计包](../reports/human-agent-copilot-20260911/index.html) 为 `Draft`：
R0-R3、8 个案例、交接和异常演练均不构成 Runtime 风险引擎或真实审批。
完整行业技术回溯、真实 Provider / PostgreSQL 联合演示、目标用户研究仍需独立验收。

## 5. 主动验收修订

根据 [新增用户验收要求](../sources/USER-FEEDBACK-20260911-self-testing-and-acceptance-cases.md)，
每次交付包含可复制输入、操作、预期与失败判据，实际 UI 与受控自动化分开记账。
新任务操作显式回到输入面，不能依赖 Run ID 变化；证据候选前展示服务端待核对判断，明确尚未确认。
不改变 start/control/decision 协议、无默认候选或来源权限。

[本次 Evidence](../evidence/DEMO12-SELF-TEST-ACCEPTANCE-EVIDENCE-20260911.md) 记录两个 UI 修复及真实单分支运行。
运行发现模型输入截断导致未限定范围的摘要，内容完整性未通过；不将该运行外推为 Provider 整体质量或业务成功。

## 6. 可达性与视觉打磨

[后续用户要求](../sources/USER-FEEDBACK-20260911-ui-polish-and-copilot-research.md) 对应长任务目标全文 disclosure、
完整草稿输入区、分支自适应列宽与固定证据操作条。目标只来自 `run.contract.goal`，资料数量只来自已加载 files，
选择状态只来自当前 candidate ID；所有动作仍复用既有版本/幂等/待决合同，不新增 Runtime。
主运行控制保持正常流，避免盖住成果。固定证据条为正文留足底部空间，错误不藏在屏幕之外。
[验证、截图与用例](../reports/demo12-polish-20260911/README.md) 分开记录视觉可达性与未解决语义覆盖。

## 7. 人机共驾研究补充

[18 项原始来源库](../reports/copilot-research-library-20260911/index.html) 将论文观察、框架工程合同与本项目推导分开。
7 条规则映射覆盖可转移主动权、可退出决定、证据/权限分轴、降低核验成本、明确恢复范围、
部分协作保留及效果对照。它们支持下一轮设计评审，不修改本 Decision 的服务端合同。
不能把人机增强等同超过最佳单方，不能把审批原语等同安全保证，也不能从页面更清楚推出业务效果。
该库是定向研究，不替代三个 Demo 完成后的固定配置技术回溯和目标用户验证。
