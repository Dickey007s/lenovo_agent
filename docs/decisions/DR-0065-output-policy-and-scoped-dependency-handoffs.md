# DR-0065：输出限制与有来源边界的前序成果传递

| 字段 | 内容 |
| --- | --- |
| 状态 | Limited Verified，精确范围与失败见 Evidence |
| 日期 | 2026-09-21 |
| 来源 | USER-FEEDBACK-20260921-CONTINUE-DEMO12；RUNTIME-20260921-OUTPUT-HANDOFF |
| 前置 | DR-0035 / DR-0053 / DR-0054 / DR-0055 / DR-0064 |
| 场景 | [SCENARIO-052](../scenarios/SCENARIO-052-readonly-analysis-and-versioned-handoffs.md) |
| 证据 | [本轮验证](../evidence/DR-0065-OUTPUT-HANDOFF-20260921.md) |

## 场景与来源

[用户持续优化要求](../sources/USER-FEEDBACK-20260921-continue-demo12.md) 是本轮授权，
不是用户研究。上一轮真实只读请求仍触发上线文件生成器；源码也显示依赖图仅约束调度，
下游并未明确收到前序采用内容。需要修的是实际任务行为，而不是另画一张协作图。

## 前台交互影响

原任务进展在服务端确认 `analysis_only` 时展示“仅页面分析”。原协作页增加“前序成果传递”，
显示前序业务名称、版本、下游工作包及其采用状态。无调用回执时不画传递，无字段的历史记录
不补造。失败或待核对仍保留已采用成果；现有恢复入口、空波次禁用、历史只读和版本控制不变。
不公开 Owner、来源哈希、内部 Prompt 或模型原始响应；查看不触发模型调用。

## 后端事实映射

1. 服务端在新 Run 开始时编译有界中英文明示禁文件语句，冻结 `contract.output_policy`。
   `analysis_only` 在 adapter freeze/write 之前生效；Plan 的 artifact.write 降为只读验证。
   仍保存分析和逻辑版本。继续同一 Task 不得放宽父 Run 限制，历史文件不删除。
2. 仅公共 Worker 派发路径构造直接前序上下文：采用的摘要、Contribution ID、Branch ID、
   Artifact version 与 approved refs。当前实现不传全部 Findings 或完整推理。
3. 在预算预留前检查 Owner/Task/Run、父 Branch/WorkUnit 完成采用、模型 called/output_used、
   不变贡献、成果版本存在、来源 revision、下游批准范围覆盖。任一缺失或过期拒绝整波。
4. 摘要作为不可信模型上下文进入 Analyst payload，不是新的授权或原文证据；引用仍须来自
   下游批准文件，经现有 Anchor/Evidence/适用叙事对账门，才可合入新的正常成果版本。
5. WorkUnit `input_contribution_ids` 是预留输入，Contribution 同名字段是实际 called 请求
   所带输入。字段由服务端请求派生，不能相信模型自己声明。已调用不等于采用或正确。
6. 空字段不写入旧 WorkUnit/Contribution/request 的序列化 payload，保留历史 hash、CAS 和
   幂等摘要。没有删除旧行或放松不可变校验；非空输入变更仍被视为内容变更。
7. 空 `branch_ids` 的幂等重试恢复原波次，而不是改派下一波。已完成回放返回原事实，不消耗
   模型预算；新的派发仍执行当前来源版本验证。

## 验证与边界

源码尚未提交，无新 PR。自动化、PostgreSQL 与两次真实 Provider 结果分别记入 Evidence。
真实蜂群是 3 个根工作包后执行 2 个下游，4 份贡献采用、1 份定位待核对；不能说全部完成。
只读任务没有生成文件不代表分析正确，结构化交接不证明模型真实利用了摘要或优于单 Agent。
没有新增 API path、自由 Agent 对话、协商、分布式调度、任意文件写入或外部办公动作。
自然语言输出限制仅覆盖明确短语；不支持任意否定、引用消歧、角色授权或运行中权限编译。
Demo3 接入、全文续读、业务语义验证和目标用户理解测试仍未完成。
