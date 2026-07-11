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


我生成时用了两类来源：

第一类是你们已有的三个 Demo 主线：跨端任务接续、多任务驾驶舱、动态风险边界与 Risk Lens。会议记录里下次会议重点正好要求补充 PC→手机→PC 显示策略、风险等级与人机接管边界、隐私保护机制，并且第二阶段要进入 Agent Demo 设计实现。 你们的需求分析也明确了跨端任务接续里“电脑深度编辑、手机轻量查看与备注、返回电脑恢复为草稿”的闭环。 风险治理部分也强调 Auto Mode 是动作级决策，不是“全权限自动化”，Risk Lens 要展示动作、对象、数据、状态变化、可撤销性、当前环境和企业策略。

第二类是公开资料里的 agentic AI 风险和数据保护思路。我参考了 OWASP Agentic Applications Top 10 中关于 agent 会“plan, act, make decisions across complex workflows”的安全风险框架，以及其中列出的 goal hijack、tool misuse、identity/privilege abuse、memory/context poisoning、human-agent trust exploitation 等风险类型。第二类是公开资料里的 agentic AI 风险和数据保护思路。我参考了 OWASP Agentic Applications Top 10 中关于 agent 会“plan, act, make decisions across complex workflows”的安全风险框架，以及其中列出的 goal hijack、tool misuse、identity/privilege abuse、memory/context poisoning、human-agent trust exploitation 等风险类型。 同时参考了 NIST AI RMF 对 AI 风险管理的框架化思路，Microsoft Purview sensitivity labels 对组织数据分类和保护的思路，以及 OpenAI Structured Outputs 对 JSON Schema/结构化输出的实现方式。 同时参考了 NIST AI RMF 对 AI 风险管理的框架化思路，Microsoft Purview sensitivity labels 对组织数据分类和保护的思路，以及 OpenAI Structured Outputs 对 JSON Schema/结构化输出的实现方式。

我没有直接从网上复制真实数据，而是做了三层组合：

第一层，直接结合你们三个 Demo：

Demo 1：PC → 手机 → PC 任务接续
Demo 2：多任务驾驶舱
Demo 3：风险治理 / Risk Lens

例如 task_snapshots.json 里包含：例如 task_snapshots.json 里包含：

{
  "snapshot_id": "snap_q3_report_001",
  "demo": "demo1_context_continuity",
  "task_id": "task_q3_report",
  "pc_state": {
    "document": "季度经营分析报告.docx",
    "position": "第3部分：渠道转化下降原因",
    "verification_points": [
      "核实Q3新客转化率统计口径",
      "核实华东区渠道结构变化"
    ]
  },
  "mobile_card": {
    "title": "继续：季度经营分析报告",
    "summary": "写到渠道转化下降原因；待核实2项",
    "sensitive_collapsed": true
  }
}

第二层，扩展常见办公动作矩阵：

文档/PPT
邮件/IM
会议/日程
项目任务
CRM/客户
OA/报销
合同/报价
权限/安全
HR/人事
移动端特殊场景

第三层，把公开 agentic AI 风险转写成办公 Agent 场景，例如：

公开风险启发	转写成办公 Agent 样例
Prompt injection / goal hijackPrompt injection / goal hijack 提示词注入 / 目标劫持	客户邮件里含隐藏指令，诱导 Agent 外发内部材料
Tool misuse	Agent 误用财务工具导出敏感明细
Identity privilege abuse	低权限用户借高权限 Agent 发起付款/权限动作
Memory/context poisoning	让 Agent 以后默认按最低折扣报价
Human-agent trust exploitation	“AI 判断没问题”诱导用户审批付款
Unexpected code execution	执行附件里的自动修复脚本

这些不是生产案例，只是 Demo 评测样例，用来证明 Risk Engine 能在高风险动作前停下来。

你可以怎么在周会里讲

你可以这样说：

本周我们把办公 Agent 的风险识别从概念方案落成了一套 P0 Demo fixture。它不依赖真实企业系统，也不需要真实用户数据，而是通过 JSON 文件模拟上下文、任务快照、风险规则、隐私规则、风险样例、Prompt 模板、评测用例和审计日志。

这套 fixture 既覆盖了我们自己的三个 Demo：跨端任务接续、多任务驾驶舱、动态风险边界，也吸收了公开 agentic AI 安全风险中的典型模式，如工具误用、权限滥用、上下文污染、提示注入和人机信任滥用。这套 fixture 既覆盖了我们自己的三个 Demo：跨端任务接续、多任务驾驶舱、动态风险边界，也吸收了公开 agentic AI 安全风险中的典型模式，如工具误用、权限滥用、上下文污染、提示注入和人机信任滥用。

P0 阶段的目标不是训练模型，而是验证链路：用户输入 → ActionSpec → Harness 校验 → Risk Engine 查规则 → Human Gate 展示确认/强确认/拒绝 → Audit Logger 留痕。后续 P1 再把 risk_examples.json 扩展成更大的示例库，用于 few-shot 检索和 LLM Judge 辅助判断。