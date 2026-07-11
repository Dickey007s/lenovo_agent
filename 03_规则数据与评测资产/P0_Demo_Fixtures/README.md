# 办公 Agent P0 Demo JSON Fixtures

生成日期：2026-06-04

这是一套用于 **办公 Agent 风险等级识别与人机共驾 P0 Demo** 的 JSON fixture 包。它不依赖真实企业系统，也不包含真实用户数据。样例基于三个 Demo 主线人工构造，并参考公开资料中的 agentic AI 风险、AI 风险管理、敏感标签与结构化输出思路。

## 文件说明

- `fixtures/mock_contexts.json`：模拟办公上下文，包括 PC/手机设备、用户角色、文档、邮件、CRM、OA、权限、合同等对象。
- `fixtures/task_snapshots.json`：模拟 PC → 手机 → PC 任务接续快照，以及多任务驾驶舱确认队列。
- `fixtures/risk_examples.json`：风险示例库，共 95 条，覆盖三条 Demo 主线、办公动作矩阵和公开 agentic 风险改写样例。
- `fixtures/policy_rules.json`：Risk Engine 规则配置，包括各类 `floor`、硬门槛、Human Gate 映射和 reason code。
- `fixtures/privacy_rules.json`：密码、验证码、客户、报价、财务、人事、合同等敏感信息处理规则。
- `fixtures/prompt_templates.json`：ActionSpec Parser、Risk Judge、解释生成、隐私过滤等 Prompt 模板。
- `fixtures/eval_cases.json`：P0 回放评测样本，用来测试规则引擎是否输出预期风险等级。
- `fixtures/audit_log.json`：模拟审计日志，用于 Demo 审计时间线展示。
- `schemas/action_spec.schema.json`：ActionSpec JSON Schema，可用于 Harness 校验模型输出。
- `references.json`：本 fixture 包参考的公开资料。

## 使用方式建议

P0 Demo 的最小链路：

```text
UserEvent + mock_contexts.json
→ LLM 生成候选 ActionSpec
→ Harness 用 schemas/action_spec.schema.json 校验
→ Risk Engine 读取 policy_rules.json 计算 final_risk_level
→ Human Gate 生成确认卡 / Risk Lens / 拒绝卡
→ L3-L5 写入 audit_log.json
```

P0 阶段可以先不使用 `model_risk_suggestion`，完全用 `policy_rules.json` 的规则计算风险。P1 再用 `risk_examples.json` 做 Example Retriever + LLM Judge 的 few-shot 辅助判断。

## 重要边界

- 这些 JSON 是 Demo fixture，不是生产策略。
- 所有邮箱、姓名、客户、金额、文件名均为模拟数据。
- 公开资料只提供风险类型启发，具体 L0-L5 风险等级由本项目 Demo 规则人工定义。
