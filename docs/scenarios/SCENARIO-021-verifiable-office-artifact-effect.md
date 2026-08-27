# SCENARIO-021：从整库任务到可下载、可验证的办公成果

## 场景记录

| 字段 | 内容 |
| --- | --- |
| 目标用户 | 在公开办公资料库中完成核对、分析、文档或代码任务的知识工作者；以及负责判断演示是否真实的方案负责人 |
| 触发 | 用户在一个文件夹里写下任务，不预选文件，也不选择 Demo |
| 当前痛点 | “模型说完成了”“有引用”“Run completed”都不能证明 CSV、DOCX、Markdown 或代码测试结果正确；失败的 Analyst 文案还可能让已完成计算不可见 |
| 目标 | Agent 自主选择资料并调用被批准的确定性办公能力，生成隔离成果文件；数值、字段、排序、规则或测试由代码复核；用户能下载和查看回执 |
| 完成条件 | Artifact 文件真实存在、可下载、逐项检查全通过、原始 FORTE 未修改、外部动作仍为 none；模型调用/采用和 Run 终态另行显示 |
| 来源 | `USER-FEEDBACK-20260827-SCENARIO-EFFECT-GATE`、FORTE 固定公开输入、`DR-0035` |
| 证据状态 | `Limited Verified`，限当前 12 个本地能力与 3 个外部阻断场景 |

## 正常路径

1. 用户浏览完整文件夹，也可以不打开任何文件，直接写任务。
2. 服务端冻结 96 个允许 refs 和 12/16/30/7200 默认预算。
3. `deepseek-v4-pro` Planner 选择本轮资料，服务端编译并校验计划。
4. 确定性办公工具读取 Catalog 允许的原始字节，只在隔离 Run Workspace 写文件。
5. Verifier 对字段、数值、排序、规则或测试回执逐项复核并写入 Snapshot。
6. Analyst 形成可解释 Finding；它是否被采用不改写已经验证的工具回执。
7. 前台显示成果、检查数、下载、模型采用状态和 Control Loop 分支状态。
8. 用户下载成果或继续处理等待分支；不会修改 FORTE 原件或执行外部动作。

## 异常路径

- **模型 JSON/引用未采用**：保留 Artifact/EffectReceipt；只把分析说明标为未采用或待恢复。
- **确定性检查失败**：Artifact 保留但标为 failed，不能显示“验证通过”。
- **原始文件漂移/越界**：Catalog fail closed，不运行工具。
- **下载跨 Owner/篡改**：404 或 503，不返回文件。
- **SQL/Web/Scheduler 未授权**：Receipt 为 `blocked_external_boundary`，零 Artifact、零外部动作。
- **预算耗尽**：保留已写 Artifact 和既有分支；terminal Run 不能伪装原地 resume。
- **API 重启**：PostgreSQL 恢复 Snapshot 中 Artifact/Receipt 元数据，稳定 Run Workspace 恢复文件；中断模型调用不重放。

## 前台影响

- 首屏仍是文件管理器和自由任务，不增加场景卡或角色入口。
- 真成果和 Agent 解释分区显示：一个回答“做出了什么”，另一个回答“模型如何解释”。
- 检查默认显示通过数，逐项内容和 EffectReceipt 渐进展开。
- 外部边界用明确中文解释缺少什么、没有发生什么，不用动画模拟工具执行。
- 移动端成果名、检查数和下载按钮保持可见且无横向溢出。

## 后端事实

`workspace_artifacts[]`、`effect_receipts[]`、`model_receipt`、`analysis_receipt`、`budget`、`branches[]` 和有序 events 分别拥有自己的事实；Snapshot 是权威。下载请求不改变 Snapshot。Run start/control 继续使用 Owner、expected version 和幂等键。

## 不支持的推断

- 不能从当前固定适配器推导任意办公任务已经泛化。
- 不能从 E2E 推导用户三秒内理解、信任提升或效率提升。
- 不能从代码测试回执推导生产沙箱安全。
- 不能从 `blocked_external_boundary` 推导外部 Connector 已实现。
