> **资料库现行口径（2026-06-08 修正）：** 本副本已按“自主等级修正版”统一为 `L0→AL5、L1→AL4、L2→AL3、L3→AL2、L4→AL1、L5→AL0`。原始 2026-06-03 文件仍保留在历史归档中。

# 办公 Agent 风险等级识别与人机共驾核心技术方案（本周汇报融合版）

**项目方向：** 企业个人办公与移动办公 Agent Demo 设计  
**适用范围：** 系统总体技术方案、跨端任务接续、风险等级识别、人机接管边界、隐私保护、Risk Lens、Agent 工程实现  
**目标阶段：** 第二阶段 Demo 设计与实现  
**本周汇报口径：** 把上次会议要求补充的三个重点，不作为孤立章节，而是融入整体系统实现链路中说明。

---

## 0. 本周汇报核心结论

本周汇报建议不要只讲“我们补了几张表”，而是讲清楚一个完整系统已经如何落地：

> **办公 Agent 通过 Context Adapter 获取授权上下文，通过 ActionSpec Parser 理解用户意图，通过风险示例库和 Qwen API 生成风险建议，通过规则引擎确定最终边界，通过 Human Gate 把决策转成用户可见、可确认、可拒绝、可审计的交互。**

这条主线同时回答上次会议提出的三个重点：

1. **跨端任务接续的显示策略差异**：同一个任务在 PC、手机、返回 PC 三个阶段展示不同粒度的信息。
2. **风险等级与人机接管边界**：L0-L5 风险等级对应 AL0-AL5 共驾等级和不同 Human Gate。
3. **用户隐私保护机制**：密码、验证码、密钥和敏感信息不进入模型；权限检查、脱敏、折叠展示和审计脱敏贯穿全链路。

本方案不是训练一个“更会自动执行的 Agent”，而是构建一个“更会判断边界的 Risk Gate”。Agent 负责理解、生成和准备；Risk Gate 负责判断、拦截和接管；企业规则永远是最终边界。

---

## 1. 背景与问题定义

当前项目已经形成三条 Demo 主线：

- **跨设备任务连续性**：PC → 手机 → PC，解决工作状态不中断。
- **多任务编排**：邮件、OA、CRM、项目系统、日历等任务统一聚合、排序和并行准备。
- **可信执行与风险治理**：Agent 能做事以后，必须明确什么时候自动、什么时候草稿、什么时候确认、什么时候拒绝。

其中第三条“可信执行与风险治理”是重点中的重点。它不是简单做一张 L1-L5 表，而是要把办公 Agent 的每个动作都转成可判断、可解释、可审计、可接管的结构化决策。

当前项目约束如下：

- 没有现成的企业办公风险等级数据集。
- 当前阶段没有条件做大规模微调。
- Demo 计划通过 API 调用通义千问 / Qwen 这类大模型。
- 已有 Demo 报告中，模型主要承担文本生成和轻量结构化提取，真实风险裁决由 Harness、规则和 Human Gate 完成。
- 后续需要扩展到更多办公动作，而不是只覆盖“格式统一、摘要、内部任务、外发、价格承诺”五个样例。

因此，本方案建议把风险治理系统做成一个 **动作级 Risk Gate**，而不是让通用 Agent 自由判断能不能执行。

---

## 2. 本周汇报建议结构

建议汇报时按下面顺序讲：

1. **先讲总体系统怎么跑起来。** 说明办公 Agent 不是一个聊天框，而是一个由上下文、动作解析、风险判断、人机接管和审计组成的系统。
2. **再讲跨端接续怎么落地。** 说明 PC、手机、返回 PC 的显示策略差异，不是简单同步屏幕，而是按设备能力和风险展示不同信息。
3. **再讲风险识别怎么落地。** 说明没有数据集、不微调的情况下，如何用 ActionSpec、风险示例库、Qwen API 和规则引擎完成泛化判断。
4. **再讲人机共驾怎么落地。** 说明 L0-L5 风险如何对应不同 Human Gate，决策怎样影响用户。
5. **最后讲隐私保护怎么贯穿。** 说明密码、验证码、敏感数据、外部内容和移动端展示如何被保护。

一句汇报总纲可以这样说：

> **这周我们把 Demo 从“功能演示”推进到“系统方案落地”：同一个办公 Agent 在跨端接续、多任务编排和风险治理中使用同一套技术链路；低风险让 Agent 快，高风险让 Agent 停，敏感信息不让模型碰。**

---

## 3. 总体技术架构

### 3.1 运行链路

```text
用户输入 / 点击 / 语音 / 设备切换
  ↓
UserEvent 标准化
  ↓
Context Adapter 上下文适配
  ↓
Privacy & Permission Guard 权限与隐私过滤
  ↓
Intent Parser 意图识别
  ↓
ActionSpec Parser 动作结构化
  ↓
Example Retriever 办公风险示例检索
  ↓
Qwen / LLM Risk Judge 风险建议
  ↓
Rule Engine 硬规则与风险下限
  ↓
Decision Fusion 决策融合
  ↓
Human Gate 人机共驾接管
  ↓
PanelSpec 输出界面
  ↓
Tool Executor / Simulator 工具执行或模拟执行
  ↓
Audit Logger 审计记录
  ↓
Feedback Loop 反馈回流与样本库更新
```

这个链路的重点是：模型不直接“放行动作”，模型只产生候选结构和风险建议；真正决定能不能执行的是规则引擎、权限策略和 Human Gate。

### 3.2 模块职责

| 模块 | 核心职责 | 输出 |
|---|---|---|
| Context Adapter | 提取授权上下文 | ContextPacket |
| Privacy Guard | 脱敏与权限过滤 | SafeContext |
| Intent Parser | 理解用户目标 | IntentFrame |
| ActionSpec Parser | 结构化动作 | ActionSpec |
| Example Retriever | 检索相似样例 | RiskExamples |
| Qwen Risk Judge | 给出风险建议 | ModelRiskSuggestion |
| Rule Engine | 计算硬门槛 | RuleHits |
| Decision Fusion | 合并最终风险 | RiskDecision |
| Human Gate | 控制用户接管 | GateState |
| Panel Renderer | 输出界面卡片 | PanelSpec |
| Tool Executor | 执行或模拟执行 | ToolResult |
| Audit Logger | 记录高风险动作 | AuditEvent |

### 3.3 模型边界

Demo 继续沿用现有设计报告中的思路：远程语言模型按 `qwen3.5-27b` 能力范围使用。实际实现时可通过 Qwen API 调用，也可以根据成本和性能替换为后续 Qwen 版本。

模型负责：

- 意图理解。
- ActionSpec 候选抽取。
- 相似示例归纳。
- 风险建议。
- 草稿生成。
- 风险解释文案。

模型不负责：

- 最终风险裁决。
- 企业策略覆盖。
- 权限放行。
- 真实业务执行。
- 自动外发。
- 自动审批。
- 自动付款。
- 自动修改权限。
- 读取密码、验证码、密钥。

---

## 4. 跨端任务接续显示策略差异：PC → 手机 → PC

### 4.1 设计原则

跨端任务接续不是把 PC 页面原封不动同步到手机，而是把同一个办公任务拆成三种设备阶段的不同展示策略。

PC 端适合展示完整上下文、文档位置、证据链和编辑入口。手机端适合展示轻量摘要、待核实点、个人备注入口和隐私折叠。返回 PC 后适合展示恢复面板、版本校验、移动端备注和草稿插入建议。

一句话表达：

> **PC 负责深度编辑，手机负责轻量接续，返回 PC 负责恢复和确认。**

### 4.2 三阶段显示策略

| 阶段 | 展示目标 | 核心组件 | 默认风险 |
|---|---|---|---|
| PC 离开前 | 保存状态 | 任务快照侧栏 | L1-L2 |
| 手机继续 | 轻量查看 | 继续卡片 | L2-L3 |
| 返回 PC | 恢复编辑 | 恢复面板 | L1-L3 |

#### PC 离开前：完整上下文与保存入口

PC 端展示重点是“我现在在做什么、做到哪里、用到了哪些材料”。此时屏幕大、编辑能力强，适合展示较完整的任务上下文。

展示内容包括：

- 当前任务名称。
- 当前文档或 PPT 名称。
- 当前编辑位置。
- 相关邮件、CRM、项目周报等来源。
- 待核实点。
- 是否包含敏感字段。
- “稍后继续”按钮。
- “清除快照”按钮。

PC 端不需要过度压缩信息，但仍需要遵守权限过滤。用户没有权限访问的材料不能进入 ContextPacket，更不能进入模型上下文。

#### 手机继续：轻量摘要与隐私折叠

手机端展示重点是“我刚才在做什么、现在能补充什么”。手机屏幕小，使用场景可能在会议间隙、走廊、通勤或公共空间，所以默认展示更谨慎。

展示内容包括：

- 任务标题。
- 当前进度短摘要。
- 不超过 3 条待核实点。
- 个人备注入口。
- 稍后提醒入口。
- 敏感信息折叠状态。
- 一键隐藏按钮。

手机端默认不展示：

- 客户报价细节。
- 合同条款全文。
- 员工个人信息。
- 财务明细。
- 大段原文。
- 完整附件预览。
- 高风险执行按钮。

手机端可以做：

- 添加个人备注。
- 设置提醒。
- 查看脱敏摘要。
- 确认低风险个人操作。

手机端不应默认做：

- 对外发送。
- 审批通过。
- 合同确认。
- 付款审批。
- 权限变更。
- 覆盖正式文档。

#### 返回 PC：恢复面板与草稿插入

返回 PC 后展示重点是“是否恢复、如何恢复、哪些移动端内容进入草稿”。此时 Agent 不应自动把手机备注写进正文，而应先展示恢复面板。

恢复面板展示内容包括：

- 上次编辑位置。
- 快照时间。
- 当前文档版本。
- 版本校验结果。
- 手机端新增备注。
- 建议插入位置。
- 待核实点。
- 可执行选项。

用户可选动作包括：

- 继续上次任务。
- 插入为草稿。
- 只保留备注。
- 忽略移动端内容。
- 清除快照。

如果文档版本不一致，系统必须先提示冲突，不能自动插入。

### 4.3 跨端状态机

```text
PC_observing
  ↓ 用户点击“稍后继续”
snapshot_saved
  ↓ 生成手机继续卡片
mobile_card_ready
  ↓ 用户添加个人备注
mobile_note_saved
  ↓ 用户返回 PC
pc_restore_available
  ↓ 版本校验通过
restore_panel_ready
  ↓ 用户确认插入为草稿
draft_inserted
```

异常分支：

```text
pc_restore_available
  ↓ 版本校验失败
version_conflict
  ↓ 用户选择查看差异 / 放弃恢复 / 只保留备注
manual_resolution
```

### 4.4 数据协议：TaskSnapshot

```json
{
  "snapshot_id": "snap_q3_001",
  "task_id": "task_q3_report",
  "device_from": "pc",
  "created_at": "2026-05-28T10:00:00+08:00",
  "active_object": {
    "object_id": "doc_q3_report",
    "title": "季度经营分析报告.docx",
    "position": "第 3 部分：渠道转化下降原因",
    "version": "v3"
  },
  "related_sources": [
    "crm_q3_summary",
    "mail_customer_feedback",
    "project_weekly"
  ],
  "verification_points": [
    "核实 Q3 新客转化率统计口径",
    "核实华东区渠道结构变化"
  ],
  "sensitivity_summary": {
    "has_sensitive_fields": true,
    "data_classes": ["business_data", "customer_data"],
    "mobile_default_collapsed": true
  }
}
```

### 4.5 数据协议：MobileContinueCard

```json
{
  "panel_type": "mobile_continue_card",
  "task_id": "task_q3_report",
  "title": "继续：季度经营分析报告",
  "short_progress": "写到第 3 部分：渠道转化下降原因",
  "safe_summary": "正在核实渠道转化下降的原因。",
  "verification_points_count": 2,
  "sensitive_display": "collapsed",
  "available_actions": [
    "add_private_note",
    "set_reminder",
    "hide_card"
  ],
  "blocked_actions": [
    "send_external",
    "approve",
    "overwrite_document"
  ]
}
```

### 4.6 数据协议：RestorePanel

```json
{
  "panel_type": "restore_panel",
  "snapshot_id": "snap_q3_001",
  "version_check": "matched",
  "restore_position": "第 3 部分第 2 段后",
  "mobile_notes": [
    {
      "note_id": "note_001",
      "visibility": "private",
      "content_preview": "渠道下降可能和代理商调整有关"
    }
  ],
  "suggested_actions": [
    "insert_as_draft",
    "keep_as_note",
    "ignore",
    "clear_snapshot"
  ],
  "risk_hint": {
    "insert_as_draft": "L3",
    "keep_as_note": "L1",
    "clear_snapshot": "L1"
  }
}
```

### 4.7 跨端策略与隐私的关系

跨端接续必须和隐私机制绑定。尤其是手机端，应默认做以下处理：

- 敏感字段折叠。
- 长文本摘要化。
- 附件不默认展开。
- 客户、财务、人事信息脱敏。
- L3 及以上动作增强确认。
- 公共网络或未托管设备降低展示粒度。
- 一键隐藏继续卡片。

这样才能把“移动办公”定义为安全的轻量接续，而不是高风险动作的移动端放大器。

---

## 5. 核心数据协议

### 5.1 UserEvent

```json
{
  "event_id": "evt_0001",
  "type": "voice_transcript",
  "device": "pc",
  "raw_input": "把汇报发给客户",
  "selected_object_ids": ["ppt_client_report"],
  "timestamp": "2026-05-28T10:00:00+08:00"
}
```

### 5.2 ContextPacket

```json
{
  "context_id": "ctx_client_report",
  "device": "pc",
  "current_task": {
    "task_id": "task_client_report",
    "title": "客户项目汇报"
  },
  "active_object": {
    "object_id": "ppt_client_report",
    "title": "客户A_项目汇报_v3.pptx",
    "version": "v3",
    "sensitivity": "customer_confidential"
  },
  "related_contents": [
    "mail_customer_a",
    "crm_customer_a",
    "project_alpha_weekly"
  ],
  "sensitive_fields": [
    "客户信息",
    "项目风险",
    "报价区间"
  ],
  "permission_summary": {
    "can_read": true,
    "can_draft": true,
    "can_send_external": false
  }
}
```

### 5.3 SafeContext

SafeContext 是进入模型之前的安全上下文。它已经完成权限过滤、敏感字段遮挡和来源标注。

```json
{
  "safe_context_id": "safe_ctx_001",
  "source_context_id": "ctx_client_report",
  "allowed_sources": [
    "mail_customer_a",
    "project_alpha_weekly"
  ],
  "blocked_sources": [
    {
      "source_id": "crm_customer_price_detail",
      "reason": "permission_denied"
    }
  ],
  "redacted_fields": [
    {
      "field": "pricing_range",
      "replacement": "<REDACTED:PRICING_DATA>"
    }
  ],
  "model_input_policy": {
    "allow_raw_text": false,
    "allow_sensitive_values": false,
    "allow_source_refs": true
  }
}
```

### 5.4 ActionSpec

ActionSpec 是风险判断的中心对象。

```json
{
  "action_id": "act_send_client_report",
  "raw_intent": "把汇报发给客户",
  "action_type": "send_email_external",
  "target_system": "email",
  "target_scope": "external_customer",
  "recipients": ["client-a@example.com"],
  "objects": ["客户A_项目汇报_v3.pdf"],
  "data_classes": ["customer_data", "project_risk"],
  "state_change": true,
  "state_change_type": "external_message_sent",
  "reversibility": "low",
  "device": {
    "type": "pc",
    "managed_device": true,
    "network": "trusted"
  },
  "missing_slots": [],
  "user_role": "project_manager",
  "policy_floor": "L4"
}
```

### 5.5 RiskDecision

```json
{
  "action_id": "act_send_client_report",
  "final_risk_level": "L4",
  "risk_score": 78,
  "autonomy_level": "AL1",
  "decision": "risk_lens_strong_confirm",
  "required_gate": "risk_lens",
  "can_override": true,
  "requires_audit": true,
  "rule_hits": [
    "EXTERNAL_SEND_REQUIRES_L4",
    "SENSITIVE_ATTACHMENT_REQUIRES_REVIEW"
  ],
  "model_suggestion": {
    "risk_level": "L4",
    "confidence": 0.86
  },
  "reason_codes": [
    "EXTERNAL_RECIPIENT",
    "CUSTOMER_DATA",
    "LOW_REVERSIBILITY"
  ]
}
```

### 5.6 PanelSpec

PanelSpec 是决策影响用户的关键协议。所有 Agent UI 都由 PanelSpec 渲染，模型不直接生成界面。

```json
{
  "panel_type": "risk_lens",
  "title": "外发客户汇报需要强确认",
  "risk_level": "L4",
  "sections": [
    {"label": "动作", "value": "发送邮件"},
    {"label": "对象", "value": "外部客户 A"},
    {"label": "附件", "value": "客户A_项目汇报_v3.pdf"},
    {"label": "敏感内容", "value": "客户信息、项目风险"},
    {"label": "可撤销性", "value": "低"}
  ],
  "actions": [
    {"action": "confirm", "label": "确认发送"},
    {"action": "modify", "label": "修改邮件"},
    {"action": "cancel", "label": "取消"}
  ]
}
```

### 5.7 AuditEvent

```json
{
  "audit_id": "audit_0001",
  "action_id": "act_send_client_report",
  "user_id_hash": "user_hash_001",
  "risk_level": "L4",
  "decision": "risk_lens_strong_confirm",
  "user_action": "confirmed",
  "policy_hits": ["EXTERNAL_SEND_REQUIRES_L4"],
  "tool_result": "simulated_success",
  "timestamp": "2026-05-28T10:05:00+08:00"
}
```

---

## 6. 办公风险示例库设计

### 6.1 为什么需要示例库

因为项目没有微调条件，也没有现成办公风险数据集，所以需要用工程方式把大量办公样例提供给模型。

示例库的作用是：

- 让模型知道 L1-L5 的边界长什么样。
- 让模型理解不同办公动作的风险差异。
- 让模型在遇到新指令时参考相似场景。
- 让风险解释有一致的 reason code。
- 为后续评测和可能的分类器训练积累数据。

### 6.2 示例库不是原始数据仓库

不建议保存真实邮件、合同、薪资、客户报价全文。示例库保存脱敏后的结构化样本。

一条样本应包含：

```json
{
  "example_id": "risk_ex_0001",
  "category": "email_external",
  "user_intent": "把这个报价发给客户",
  "action_spec": {
    "action_type": "send_email_external",
    "target_scope": "external_customer",
    "data_classes": ["pricing", "customer_data"],
    "state_change": true,
    "reversibility": "low",
    "device_type": "mobile",
    "missing_slots": ["attachment_version"]
  },
  "label_risk_level": "L4",
  "label_risk_score": 82,
  "label_autonomy_level": "AL1",
  "label_decision": "risk_lens_strong_confirm",
  "reason_codes": [
    "EXTERNAL_RECIPIENT",
    "PRICING_DATA",
    "LOW_REVERSIBILITY",
    "MOBILE_CONTEXT",
    "MISSING_CRITICAL_SLOT"
  ],
  "allowed_actions": [
    "draft_email",
    "preview_attachment",
    "open_approval_flow"
  ],
  "blocked_actions": [
    "auto_send",
    "auto_commit_discount"
  ]
}
```

### 6.3 示例库分类

P0 阶段至少覆盖以下类别：

| 类别 | 典型动作 | 风险范围 |
|---|---|---|
| 文档编辑 | 摘要、插入、覆盖 | L1-L3 |
| 邮件/IM | 草稿、内部、外发 | L2-L4 |
| 日程会议 | 查询、创建、邀请 | L1-L4 |
| 项目任务 | 创建、改状态 | L2-L4 |
| CRM | 备注、商机、导出 | L2-L5 |
| OA/财务 | 核查、审批、付款 | L2-L5 |
| HR | 面试、薪资、Offer | L3-L5 |
| 法务合同 | 摘要、条款、签署 | L3-L5 |
| 权限安全 | 申请、变更、重置 | L3-L5 |
| 移动办公 | 快照、确认、外发 | L2-L5 |

### 6.4 示例检索策略

示例检索不应只按自然语言相似度，而要多字段混合检索。

推荐检索权重：

```text
action_type 相同：+40
数据类型 data_classes 重合：+25
目标范围 target_scope 相同：+15
状态变化 state_change 相同：+10
可撤销性 reversibility 相近：+5
自然语言意图相似：+5
```

检索结果组合建议：

- Top 3：最相似动作。
- Top 2：同类高风险样例。
- Top 1：边界灰区样例。
- Top 1：企业硬规则样例。

这样可以避免模型只学习低风险样例，导致高风险漏判。

---

## 7. 风险等级体系

### 7.1 L0-L5 定义

| 等级 | 判断重点 | 默认处理 |
|---|---|---|
| L0 | 无业务影响 | 后台自动 |
| L1 | 个人可见、可撤销 | 自动+撤销 |
| L2 | 内容生成、不写系统 | 草稿+来源 |
| L3 | 内部状态变化 | 预览确认 |
| L4 | 外部影响或敏感数据 | Risk Lens |
| L5 | 不可逆或受限动作 | 拒绝转人工 |

### 7.2 量化分数

风险分数用于排序和解释，不替代硬门槛。

| 等级 | 分数区间 | 含义 |
|---|---|---|
| L0 | 0-9 | 后台维护 |
| L1 | 10-24 | 低风险 |
| L2 | 25-44 | 草稿摘要 |
| L3 | 45-64 | 内部写入 |
| L4 | 65-84 | 外发敏感 |
| L5 | 85-100 | 受限不可逆 |

### 7.3 风险计算公式

```text
final_risk_level = max(
  action_type_floor,
  data_sensitivity_floor,
  target_scope_floor,
  state_change_floor,
  reversibility_floor,
  permission_floor,
  enterprise_policy_floor,
  model_risk_suggestion
)

if has_missing_critical_slots:
  final_risk_level = max(final_risk_level, L3)

if device == mobile and final_risk_level >= L3:
  strengthen_confirmation = true

if permission_denied or policy_forbidden:
  final_risk_level = L5
```

### 7.4 决策融合伪代码

```python
RISK_ORDER = ["L0", "L1", "L2", "L3", "L4", "L5"]


def max_level(*levels):
    return max(levels, key=lambda x: RISK_ORDER.index(x))


def decide_risk(action_spec, context, rule_hits, model_suggestion):
    floors = [
        evaluate_action_floor(action_spec),
        evaluate_data_floor(action_spec.data_classes),
        evaluate_scope_floor(action_spec.target_scope),
        evaluate_state_change_floor(action_spec),
        evaluate_reversibility_floor(action_spec.reversibility),
        evaluate_permission_floor(context.permission_summary),
        evaluate_policy_floor(action_spec),
        model_suggestion.risk_level_suggestion,
    ]

    final_level = max_level(*floors)

    if has_missing_critical_slots(action_spec):
        final_level = max_level(final_level, "L3")

    if is_policy_forbidden(rule_hits):
        final_level = "L5"

    if action_spec.device.type == "mobile" and final_level in ["L3", "L4"]:
        confirmation_mode = "enhanced"
    else:
        confirmation_mode = "normal"

    decision = map_level_to_gate(final_level, action_spec, context, confirmation_mode)

    return RiskDecision(
        final_risk_level=final_level,
        decision=decision.name,
        required_gate=decision.gate,
        autonomy_level=decision.autonomy_level,
        reason_codes=merge_reason_codes(rule_hits, model_suggestion),
        requires_audit=final_level in ["L3", "L4", "L5"]
    )
```

---

## 8. 风险等级与人机接管边界对应关系

### 8.1 设计原则

人机共驾不是简单地“自动/手动”二选一，而是根据风险等级动态分配控制权。

低风险场景，Agent 可以自动处理，并提供撤销。中风险场景，Agent 生成草稿或预览，由用户采纳。高风险场景，Agent 必须停下，把动作、对象、数据、影响和规则展示给用户。极高风险场景，Agent 不能执行，只能转人工。

### 8.2 共驾等级 AL0-AL5

这里的 AL0-AL5 表示控制权分配，不表示危险程度。

| 共驾等级 | Agent 角色 | 用户角色 | 适用风险 |
|---|---|---|---|
| AL0 | 不执行 | 全人工 | L5 |
| AL1 | 风险建议/强监督 | 强确认或取消 | L4 |
| AL2 | 准备动作 | 预览确认后执行 | L3 |
| AL3 | 生成草稿 | 审核采纳 | L2 |
| AL4 | 自动可撤销 | 事后撤销 | L1 |
| AL5 | 后台维护 | 设置管理 | L0 |

### 8.3 风险等级与接管边界大表

| 风险 | 技术判断 | 接管边界 | UI |
|---|---|---|---|
| L0 | 无影响 | 不打扰 | 后台日志 |
| L1 | 可撤销 | 自动执行 | Toast |
| L2 | 不写系统 | 草稿为止 | 草稿卡 |
| L3 | 内部写入 | 确认执行 | 确认卡 |
| L4 | 外发敏感 | 强确认 | Risk Lens |
| L5 | 受限不可逆 | 拒绝执行 | 拒绝卡 |

每一级的详细解释如下。

#### L0：后台自动

适用于无业务影响的系统维护动作，例如索引更新、状态同步心跳、缓存刷新。用户默认不感知，但可以在设置和日志中查看。

#### L1：自动执行，可撤销

适用于个人可见、可撤销、影响范围小的动作，例如格式整理、保存任务快照、个人备注保存。执行后必须提供撤销入口。

#### L2：生成草稿，不改变系统状态

适用于摘要、邮件草稿、PPT 草稿、待办建议等动作。Agent 可以生成内容，但不能替用户发送、提交或写入正式系统。

#### L3：预览确认后执行

适用于创建内部任务、插入草稿、更新内部备注等动作。Agent 可以准备动作，但执行前必须展示预览，并等待用户确认。

#### L4：Risk Lens 强确认

适用于对外发送、敏感附件、CRM 状态更新、正式提交等动作。Agent 必须展示动作、对象、数据、可撤销性、证据来源和策略命中。

#### L5：拒绝自动执行，转人工

适用于付款、合同签署、权限变更、价格承诺、薪资查询、异常审批强行通过、批量删除等动作。Agent 只能解释原因，并提供人工流程入口。

### 8.4 Human Gate 状态机

```text
not_required
  ↓
preview_ready
  ↓
waiting_confirm
  ↓           ↓           ↓
confirmed   modified    cancelled
  ↓
simulated_done

clarifying
  ↓
waiting_user_input
  ↓
reparse_action

rejected_to_manual
  ↓
manual_flow_opened / cancelled
```

### 8.5 接管触发规则

| 触发信号 | 处理 |
|---|---|
| 外部收件人 | 至少 L4 |
| 报价信息 | 至少 L4 |
| 价格承诺 | L5 |
| 合同签署 | L5 |
| 权限变更 | L5 |
| 付款操作 | L5 |
| HR 薪资 | L5 |
| 关键槽位缺失 | 先澄清 |
| 手机端 L3+ | 增强确认 |
| 权限不足 | 拒绝 |
| 策略禁止 | 拒绝 |

### 8.6 接管如何影响用户

风险决策必须直接影响 UI，而不是只停留在后端日志里。

```text
RiskDecision
  ↓
Human Gate
  ↓
PanelSpec
  ↓
用户看到 Toast / 草稿卡 / 确认卡 / Risk Lens / 拒绝卡
  ↓
用户确认 / 修改 / 取消 / 转人工
  ↓
Tool Executor 或 Audit Logger
```

示例：

```json
{
  "final_risk_level": "L4",
  "autonomy_level": "AL1",
  "decision": "risk_lens_strong_confirm",
  "required_gate": "risk_lens",
  "available_user_actions": [
    "confirm",
    "modify",
    "cancel"
  ]
}
```

---

## 9. 风险规则库设计

### 9.1 规则表示

```json
{
  "rule_id": "external_send_requires_l4",
  "name": "对外发送至少 L4",
  "condition": {
    "action_type_in": ["send_email_external", "share_file_external"],
    "target_scope_in": ["external_customer", "supplier", "public"]
  },
  "risk_floor": "L4",
  "decision_hint": "risk_lens_strong_confirm",
  "reason_code": "EXTERNAL_SEND",
  "can_override": true
}
```

### 9.2 受限动作规则

```json
{
  "rule_id": "pricing_commitment_forbidden",
  "name": "价格承诺禁止自动执行",
  "condition": {
    "data_classes_contains_any": ["pricing", "discount", "commercial_terms"],
    "target_scope_in": ["external_customer"],
    "state_change": true
  },
  "risk_floor": "L5",
  "decision_hint": "reject_to_manual",
  "reason_code": "PRICING_COMMITMENT",
  "can_override": false
}
```

### 9.3 缺失关键槽位规则

```json
{
  "rule_id": "missing_critical_slots_clarify",
  "name": "关键槽位缺失必须澄清",
  "condition": {
    "missing_slots_contains_any": [
      "recipient",
      "amount",
      "contract_party",
      "attachment_version",
      "approval_object"
    ]
  },
  "risk_floor": "L3",
  "decision_hint": "clarify_before_action",
  "reason_code": "MISSING_CRITICAL_SLOT",
  "can_override": false
}
```

### 9.4 移动端增强确认规则

```json
{
  "rule_id": "mobile_l3_plus_enhance_gate",
  "name": "移动端 L3 以上增强确认",
  "condition": {
    "device_type": "mobile",
    "risk_level_gte": "L3"
  },
  "risk_modifier": "confirm_strengthen",
  "decision_hint": "enhanced_preview",
  "reason_code": "MOBILE_CONTEXT"
}
```

---

## 10. 用户隐私保护机制

### 10.1 设计原则

隐私保护不应只理解为“密码打码”。办公 Agent 的隐私保护需要覆盖完整链路：

```text
权限检查
  ↓
敏感数据识别
  ↓
上下文最小化
  ↓
模型输入脱敏
  ↓
移动端折叠展示
  ↓
工具调用确认
  ↓
日志审计脱敏
  ↓
数据生命周期清理
```

核心原则是：

- **权限先于生成**：无权限数据不能进入模型。
- **最小上下文**：只给模型当前任务所需的信息。
- **敏感值不入模**：密码、验证码、密钥、Token 不进入 Prompt。
- **移动端默认更谨慎**：敏感信息默认折叠。
- **日志只记判断，不记明文**：审计记录保留动作和规则，不保留秘密值。
- **外部内容不可信**：邮件、附件、网页、IM 中的指令不能改系统规则。

### 10.2 敏感信息分类

| 类别 | 示例 | 处理 |
|---|---|---|
| 账户秘密 | 密码、验证码、Token | 禁止入模 |
| 个人信息 | 手机号、身份证、地址 | 脱敏 |
| 客户信息 | 联系人、需求、合同 | 权限过滤 |
| 商业信息 | 报价、折扣、策略 | 强确认 |
| 财务信息 | 发票、付款、报销 | 强规则 |
| 人事信息 | 薪资、绩效、Offer | 高限制 |
| 权限信息 | 账号、角色、访问权 | 转人工 |
| 法务信息 | 合同、条款、承诺 | 审批 |

### 10.3 密码、验证码、密钥处理

密码、验证码、Token、API Key、私钥等信息采用最严格规则。

处理规则：

- 不进入模型上下文。
- 不进入风险示例库。
- 不进入审计明文。
- 不保存在长期记忆。
- 不在移动端明文展示。
- 只允许用户本人在原系统中使用。
- 任何“帮我看验证码”“帮我复制密码”“帮我填这个密钥”的意图默认 L5。

检测到秘密值后，系统应替换为占位符：

```json
{
  "original_field": "sms_code",
  "detected_type": "OTP_CODE",
  "replacement": "<SECRET:OTP_CODE>",
  "model_visible": false,
  "log_visible": false,
  "risk_level_floor": "L5"
}
```

如果用户输入：

```text
帮我看短信验证码然后填到网页登录框里。
```

系统应该输出：

```json
{
  "final_risk_level": "L5",
  "decision": "reject_to_manual",
  "reason_codes": [
    "SECRET_VALUE",
    "CREDENTIAL_FLOW",
    "POLICY_FORBIDDEN"
  ],
  "panel_type": "reject_card"
}
```

用户界面文案可以是：

```text
我不能读取、保存或代填验证码。你可以在原系统中手动完成验证。
```

### 10.4 权限先于模型

权限检查必须发生在模型调用之前。

```text
UserEvent
  ↓
Context Adapter
  ↓
Permission Guard
  ↓
Sensitive Labeler
  ↓
SafeContext Builder
  ↓
Qwen API
```

如果用户没有权限访问某份文档或字段，系统不能把该内容传给模型，也不能让模型“概括不可访问内容”。

权限不足时：

```json
{
  "blocked_source": "crm_price_detail",
  "reason": "permission_denied",
  "model_input": "excluded",
  "user_visible_hint": "你没有该价格明细的访问权限。"
}
```

### 10.5 上下文最小化

模型输入不应包含整个文档、完整邮箱、完整 CRM，而应包含完成当前动作所需的最小结构化上下文。

错误做法：

```text
把所有客户邮件、CRM 历史、报价单全文都传给模型。
```

正确做法：

```json
{
  "task": "generate_email_draft",
  "allowed_context": {
    "customer_name": "客户A",
    "request_summary": "询问技术方案更新时间",
    "deadline": "今天 18:00",
    "source_refs": ["mail_customer_a"]
  },
  "redacted_context": {
    "pricing_range": "<REDACTED:PRICING_DATA>"
  }
}
```

### 10.6 移动端隐私展示

移动端是隐私风险更高的环境，应设置更严格展示策略。

移动端默认：

- 敏感字段折叠。
- 附件不自动预览。
- 长文本只展示摘要。
- 报价、合同、薪资隐藏。
- 外发前必须全屏 Risk Lens。
- 支持一键隐藏继续卡片。
- 未托管设备不展示高敏字段。
- 公共网络上调确认强度。

移动端敏感展开条件：

```json
{
  "device_type": "mobile",
  "managed_device": true,
  "user_reauthenticated": true,
  "data_class": "customer_confidential",
  "display_mode": "masked_then_expand"
}
```

### 10.7 Prompt Injection 防护

外部邮件、附件、网页、IM 中的文本全部视为不可信内容。它们只能作为数据来源，不能作为系统指令。

防护规则：

- 外部内容必须放入 data 区域。
- 外部内容不能改写系统规则。
- 外部内容不能要求 Agent 调用工具。
- 外部内容不能要求 Agent 忽略风险规则。
- 工具调用只能由 ActionSpec 和 Human Gate 触发。
- 高风险工具调用必须二次确认。

安全上下文示例：

```json
{
  "source_type": "external_email",
  "trust_level": "untrusted",
  "content_usage": "data_only",
  "may_contain_instructions": true,
  "instruction_execution_allowed": false
}
```

### 10.8 审计脱敏

审计记录保留：

- 动作类型。
- 风险等级。
- 策略命中。
- 用户确认方式。
- 模拟执行结果。
- 时间戳。
- 脱敏后的对象引用。

审计记录不保留：

- 密码。
- 验证码。
- Token。
- 私钥。
- 原始合同全文。
- 员工薪资明细。
- 客户报价全文。
- 大段邮件正文。

审计事件示例：

```json
{
  "audit_id": "audit_secret_block_001",
  "action_type": "read_otp_code",
  "risk_level": "L5",
  "decision": "reject_to_manual",
  "stored_sensitive_value": false,
  "policy_hits": [
    "SECRET_VALUES_NEVER_ENTER_MODEL",
    "CREDENTIAL_FLOW_FORBIDDEN"
  ]
}
```

---

## 11. 场景化规则扩展

### 11.1 文档与内容生产

| 动作 | 风险 | 处理 |
|---|---|---|
| 格式统一 | L1 | 自动+撤销 |
| 文档摘要 | L2 | 草稿+来源 |
| 插入草稿 | L3 | 确认 |
| 删除正文 | L3-L4 | 差异预览 |
| 客户版改写 | L4 | Risk Lens |
| 涉密外发 | L5 | 转人工 |

### 11.2 邮件与 IM

| 动作 | 风险 | 处理 |
|---|---|---|
| 内部回复草稿 | L2 | 草稿 |
| 内部提醒 | L3 | 确认 |
| 客户邮件草稿 | L2-L3 | 草稿 |
| 外发客户邮件 | L4 | Risk Lens |
| 群发外部客户 | L5 | 转人工 |
| 折扣承诺 | L5 | 拒绝 |

### 11.3 日程与会议

| 动作 | 风险 | 处理 |
|---|---|---|
| 查询日程 | L1 | 自动 |
| 建议时间 | L2 | 建议 |
| 创建内部会议 | L3 | 确认 |
| 邀请客户 | L4 | 强确认 |
| 取消高管会议 | L4-L5 | 人工 |
| 自动录音 | L4-L5 | 授权 |

### 11.4 项目任务

| 动作 | 风险 | 处理 |
|---|---|---|
| 查看项目状态 | L2 | 摘要 |
| 生成待办建议 | L2 | 草稿 |
| 创建内部任务 | L3 | 确认 |
| 修改负责人 | L3 | 确认 |
| 改项目状态 | L4 | 强确认 |
| 关闭风险项 | L4 | 证据复核 |

### 11.5 CRM 与销售

| 动作 | 风险 | 处理 |
|---|---|---|
| 查询客户背景 | L2 | 摘要 |
| 写入沟通备注 | L3 | 确认 |
| 推进商机 | L4 | 强确认 |
| 导出客户列表 | L4-L5 | 审批 |
| 更新报价 | L5 | 转人工 |
| 群发客户 | L5 | 拒绝 |

### 11.6 OA、财务与采购

| 动作 | 风险 | 处理 |
|---|---|---|
| 查看审批状态 | L1 | 自动 |
| 材料检查 | L2 | 建议 |
| 通知补材料 | L3 | 确认 |
| 普通审批 | L4 | 强确认 |
| 异常审批通过 | L5 | 拒绝 |
| 付款申请 | L5 | 人工 |

### 11.7 HR、人事与隐私

| 动作 | 风险 | 处理 |
|---|---|---|
| 简历摘要 | L2-L3 | 草稿 |
| 面试安排 | L3-L4 | 确认 |
| 绩效总结 | L4 | 权限校验 |
| 薪资查询 | L5 | 拒绝 |
| 发 Offer | L5 | 人工 |
| 离职通知 | L5 | 人工 |

### 11.8 法务与合同

| 动作 | 风险 | 处理 |
|---|---|---|
| 合同摘要 | L3 | 来源标注 |
| 条款风险标注 | L3-L4 | 人工复核 |
| 修改条款 | L4 | 差异确认 |
| 发合同签署 | L5 | 审批 |
| 接受客户条款 | L5 | 拒绝 |
| 对外合规承诺 | L5 | 证据审批 |

### 11.9 权限与安全

| 动作 | 风险 | 处理 |
|---|---|---|
| 查询本人权限 | L1-L2 | 自动 |
| 申请权限 | L3 | 确认 |
| 给同事开权限 | L5 | 人工 |
| 重置他人密码 | L5 | 拒绝 |
| 读取验证码 | L5 | 禁止入模 |
| 执行脚本 | L4-L5 | 沙箱审批 |

### 11.10 移动办公特有场景

| 动作 | 风险 | 处理 |
|---|---|---|
| 查看任务快照 | L1-L2 | 折叠敏感 |
| 手机备注 | L2 | 私有保存 |
| 手机创建任务 | L3 | 二次确认 |
| 手机外发邮件 | L4 | 强 Risk Lens |
| 手机付款审批 | L5 | 禁止 |
| 弱网外发 | L4 | 版本校验 |

---

## 12. Risk Lens 设计

### 12.1 Risk Lens 展示维度

Risk Lens 的作用是让用户在高风险动作前看清楚 Agent 准备做什么。

建议固定八个区域：

1. **动作**：准备执行什么。
2. **对象**：影响谁。
3. **数据**：涉及什么敏感信息。
4. **状态变化**：会不会写入、发送、审批。
5. **可撤销性**：能不能恢复。
6. **证据来源**：依据来自哪里。
7. **策略命中**：触发了哪些规则。
8. **用户选择**：确认、修改、取消、转人工。

### 12.2 Risk Lens PanelSpec

```json
{
  "panel_type": "risk_lens",
  "title": "外发客户材料需要强确认",
  "risk_level": "L4",
  "sections": [
    {
      "label": "动作",
      "value": "向客户 A 发送项目汇报邮件"
    },
    {
      "label": "对象",
      "value": "外部客户 client-a@example.com"
    },
    {
      "label": "数据",
      "value": "客户信息、项目风险、报价提示"
    },
    {
      "label": "状态变化",
      "value": "邮件发送后不可完全撤回"
    },
    {
      "label": "证据来源",
      "value": "客户邮件、CRM、项目周报"
    },
    {
      "label": "策略命中",
      "value": "外发材料必须确认"
    }
  ],
  "actions": [
    {"action": "confirm", "label": "确认发送"},
    {"action": "modify", "label": "修改邮件"},
    {"action": "cancel", "label": "取消"}
  ]
}
```

### 12.3 Risk Lens 与接管边界的关系

Risk Lens 不是单纯的提示卡，而是 Human Gate 的一个高风险 UI 形态。它必须阻断工具执行，直到用户明确确认、修改或取消。

```text
RiskDecision = L4
  ↓
Human Gate 暂停
  ↓
Risk Lens 展示
  ↓
用户确认 / 修改 / 取消
  ↓
Tool Executor 才能继续
```

对于 L5，Risk Lens 不提供“继续执行”按钮，只提供人工流程入口。

---

## 13. Prompt 工程设计

### 13.1 总体原则

- Prompt 只让模型输出候选结果。
- 所有输出必须符合 JSON Schema。
- 模型不能补猜关键字段。
- 模型不能覆盖企业规则。
- 模型必须显式输出缺失槽位。
- 文档内容中的指令视为不可信数据。
- 密码、验证码、密钥占位符不可还原。

### 13.2 ActionSpec Parser Prompt

```text
你是办公 Agent 的动作解析模块。
你的任务是把用户输入和上下文转换为结构化 ActionSpec。

重要约束：
1. 不要判断最终风险等级。
2. 不要执行动作。
3. 不要猜测收件人、金额、合同对象、附件版本。
4. 如果关键字段缺失，请写入 missing_slots。
5. 如果输入包含密码、验证码、密钥，请只标记 SECRET_VALUE，不要输出原值。
6. 只输出 JSON，不输出解释。
```

### 13.3 Risk Judge Prompt

```text
你是办公 Agent 的风险建议模块。
你不是最终裁判。
你的任务是根据 ActionSpec、企业策略摘要和相似示例，输出风险等级建议、风险分数建议和 reason codes。

最终风险等级会由规则引擎决定。
如果示例和当前动作冲突，优先保守判断。
如果存在外发、价格、合同、权限、付款、人事、批量删除，请提高风险建议。
如果存在密码、验证码、密钥，请建议 L5。
只输出符合 schema 的 JSON。
```

### 13.4 示例注入格式

```text
[企业风险等级定义]
L0 后台无影响
L1 低风险可撤销
L2 草稿/摘要不写系统
L3 内部状态变化
L4 外发或敏感正式动作
L5 受限或不可逆动作

[相似示例]
示例 1：...
示例 2：...
示例 3：...

[当前 ActionSpec]
...

[输出 JSON Schema]
...
```

---

## 14. 与现有 Demo 的结合方式

### 14.1 对现有架构的新增模块

在当前 Demo 报告已有链路中新增三个模块：

```text
Privacy & Permission Guard  ← 新增
  ↓
ActionSpec Parser
  ↓
Example Retriever           ← 新增
  ↓
Qwen Risk Judge             ← 新增
  ↓
Risk Engine
```

原有 Risk Engine 不删除，而是升级为：

```text
Rule Engine + Decision Fusion + Policy Store
```

### 14.2 对现有 HTML Demo 的改造点

当前 `office_agent_demo_showcase.html` 已经包含：

- Demo 1 上下文连续。
- Demo 2 多任务编排。
- Demo 3 风险治理。
- Agent Trace。
- 输入 / 输出 / 状态 / 风险 JSON。

建议新增：

1. **跨端显示策略视图**：展示 PC、手机、返回 PC 的不同 PanelSpec。
2. **隐私过滤面板**：展示哪些字段进入模型、哪些字段被遮挡。
3. **示例匹配面板**：展示本次风险判断参考了哪些样例。
4. **规则命中面板**：展示命中的 rule_id。
5. **模型建议面板**：展示 Qwen 输出的风险建议。
6. **最终决策面板**：展示规则与模型融合结果。
7. **Human Gate 状态**：展示等待确认、已确认、已拒绝等状态。

### 14.3 Demo 1 的升级镜头

原镜头：

```text
PC 任务快照 → 手机继续卡片 → 手机备注 → 返回 PC 恢复 → 插入草稿
```

升级后镜头：

```text
PC 完整上下文
  ↓
生成 TaskSnapshot
  ↓
Privacy Guard 生成手机安全摘要
  ↓
手机 Continue Card 折叠敏感字段
  ↓
返回 PC 版本校验
  ↓
Restore Panel 显示备注和插入建议
  ↓
L3 确认后插入草稿
```

### 14.4 Demo 3 的升级镜头

原镜头：

```text
L1 自动格式 → L2 摘要 → L3 内部任务 → L4 外发 → L5 拒绝
```

升级后镜头：

```text
用户指令
  ↓
ActionSpec 生成
  ↓
相似示例检索
  ↓
Qwen 风险建议
  ↓
规则命中
  ↓
最终 RiskDecision
  ↓
Human Gate UI
  ↓
审计时间线
```

这样能让会议中大家看到“不只是一个风险表”，而是一个可落地的 Agent 工程链路。

---

## 15. API 与工程接口

### 15.1 后端接口

#### POST /agent/event

接收用户事件，返回 Agent 面板。

```json
{
  "event": "UserEvent",
  "context_mode": "mock_dom"
}
```

#### POST /context/safe

返回经过权限和隐私处理后的 SafeContext。

```json
{
  "user_event": "evt_0001",
  "context_packet": "ctx_0001"
}
```

#### POST /risk/parse

返回 ActionSpec。

```json
{
  "user_event": "evt_0001",
  "safe_context": "safe_ctx_0001"
}
```

#### POST /risk/decide

返回 RiskDecision。

```json
{
  "action_spec": "act_0001",
  "safe_context": "safe_ctx_0001"
}
```

#### POST /gate/confirm

用户确认、修改或取消。

```json
{
  "action_id": "act_0001",
  "gate_action": "confirm"
}
```

#### GET /audit/timeline

返回审计时间线。

### 15.2 前端状态

```json
{
  "session_state": "waiting_user",
  "branch_state": {
    "task_customer_mail": "draft_ready",
    "task_expense": "suspended"
  },
  "gate_state": {
    "act_send_customer_mail": "waiting_confirm"
  },
  "privacy_state": {
    "mobile_sensitive_collapsed": true,
    "secret_values_excluded": true
  }
}
```

### 15.3 本地 Demo 存储

P0 阶段可以全部用 JSON 文件实现：

```text
fixtures/
  mock_contexts.json
  task_snapshots.json
  risk_examples.json
  policy_rules.json
  privacy_rules.json
  prompt_templates.json
  eval_cases.json
  audit_log.json
```

P1 阶段再引入向量数据库：

```text
risk_examples.json
  ↓ embedding
vector_store/faiss 或 chroma
  ↓ top_k retrieve
prompt assembler
```

---

## 16. 评测与验收指标

### 16.1 风险评测集

P0 阶段建议准备 300-500 条样本，覆盖：

- L0-L5 各等级。
- 十类办公动作。
- 移动端与 PC 端。
- 关键槽位缺失。
- 外部收件人与内部收件人。
- 敏感附件与普通附件。
- 权限不足。
- 企业策略禁止。
- Prompt injection 样例。
- 密码、验证码、Token 样例。
- 跨端任务接续样例。

### 16.2 核心指标

| 指标 | 目标 |
|---|---|
| L4/L5 漏判率 | 0 |
| L5 越权执行率 | 0 |
| L3-L5 审计覆盖率 | 100% |
| 关键槽位澄清率 | ≥99% |
| 规则命中一致率 | 100% |
| 高风险召回率 | ≥99% |
| 低风险打扰率 | ≤10% |
| 模型失败回退率 | 100% 可用 |
| 密码入模率 | 0 |
| 验证码入模率 | 0 |
| 移动端敏感默认折叠率 | 100% |
| Risk Lens 可理解率 | 用户测试验证 |

### 16.3 测试类型

1. **单元测试**：每条规则输入 ActionSpec 后返回正确 floor。
2. **集成测试**：用户输入经完整链路得到正确 PanelSpec。
3. **回放测试**：固定 Demo 输入输出稳定。
4. **红队测试**：邮件、附件、网页中的恶意指令不能越权。
5. **移动端测试**：L3+ 动作必须增强确认。
6. **隐私测试**：密码、验证码、密钥不能进入模型和日志。
7. **跨端测试**：PC、手机、返回 PC 的展示策略正确。
8. **失败测试**：模型超时、JSON 非法、字段缺失时可回退。

---

## 17. 实施路线图

### P0：Demo 可演示版本

目标：不微调，先跑通核心链路。

范围：

- ActionSpec Parser。
- Privacy & Permission Guard。
- 跨端 TaskSnapshot。
- 规则引擎。
- 少量风险示例库。
- Qwen API 风险建议。
- Risk Lens。
- Human Gate。
- 审计时间线。

交付物：

- `task_snapshots.json`。
- `risk_examples.json`。
- `policy_rules.json`。
- `privacy_rules.json`。
- `prompt_templates.json`。
- Demo 1 跨端显示策略升级。
- Demo 3 风险治理升级。
- 300 条评测样本。

### P1：场景扩展版本

目标：覆盖更多办公场景。

范围：

- 向量检索示例库。
- 十类办公风险规则。
- 更多 Human Gate UI。
- 移动端隐私状态。
- 用户反馈回流。
- 审计回放。

交付物：

- 1000 条结构化样本。
- 规则管理页面概念稿。
- 隐私策略配置概念稿。
- 更多边界场景演示。

### P2：分类器增强版本

目标：当数据足够后再考虑训练专用 Risk Classifier。

范围：

- LightGBM / XGBoost 或小模型分类器。
- 与 LLM Judge 交叉验证。
- 策略回放评估。
- 长期审计与漂移监控。

注意：即使 P2 引入分类器，企业硬规则仍是最终边界。

---

## 18. 本周汇报话术

### 18.1 开场话术

> 上次会议提出的重点是跨端显示策略、风险等级与人机接管边界、用户隐私保护机制。我们这周没有把这三点做成孤立补充，而是把它们融入整体办公 Agent 系统链路中。现在的方案是：Agent 通过 Context Adapter 拿到上下文，通过 ActionSpec 识别用户到底要做什么，通过示例库和 Qwen API 形成风险建议，通过规则引擎和 Human Gate 决定什么时候自动、什么时候草稿、什么时候确认、什么时候拒绝，并在整个过程中对密码、验证码和敏感信息做权限过滤与脱敏。

### 18.2 跨端部分话术

> 跨端接续不是把 PC 原样搬到手机，而是同一个任务在不同设备展示不同粒度。PC 展示完整上下文和编辑入口；手机只展示轻量摘要、待核实点和个人备注，敏感字段默认折叠；返回 PC 后再做版本校验、恢复面板和草稿插入确认。这样既保证移动办公不断点，也避免手机端变成高风险操作入口。

### 18.3 风险接管部分话术

> 风险等级不是模型拍脑袋判断，而是动作级判断。系统先把用户意图结构化成 ActionSpec，再结合办公示例库、Qwen 风险建议、企业规则和权限策略做融合。最终 L0-L5 风险会映射到不同 Human Gate：L1 自动可撤销，L2 只生成草稿，L3 确认执行，L4 Risk Lens 强确认，L5 拒绝并转人工。

### 18.4 隐私部分话术

> 隐私保护不是简单打码，而是从权限检查开始。无权限数据不进入模型，密码、验证码、Token、密钥不进入 Prompt、不进入日志、不进入记忆。移动端默认折叠敏感字段，外部邮件和附件中的文本都只作为数据，不允许它们改变 Agent 的系统指令或工具调用规则。

### 18.5 总结话术

> 最终我们不是要做一个全自动办公 Agent，而是一个动作级共驾 Agent。低风险让 Agent 快，高风险让 Agent 停；模型负责理解和生成，规则负责边界和兜底，用户在关键节点接管，系统全程留痕。

---

## 19. 最终方案表述

可以在报告或会议中使用这一段作为总结：

> 风险等级识别不建议完全依赖通用大模型直接判断，而应采用“规则硬门槛 + 结构化动作表示 + 办公风险示例库 + Qwen API 风险建议 + Human Gate 人机接管”的混合方案。系统首先通过 LLM 将用户意图解析为 ActionSpec，包括动作类型、目标对象、数据类别、状态变化、可逆性、设备环境、关键槽位和企业策略标签；随后由规则引擎根据外发、审批、付款、合同、权限、人事、财务等硬门槛设定最低风险等级；对于未被硬规则完全覆盖的灰区动作，再由 Qwen Risk Judge 结合相似办公示例输出风险等级建议、执行策略和 reason codes；最终决策取企业硬门槛、规则评分和模型建议中的更保守结果。跨端接续、隐私保护和人机接管都通过 PanelSpec 与 Human Gate 进入用户界面，使风险决策真正影响用户操作。

更简洁的版本：

> **低风险让 Agent 快，高风险让 Agent 停，敏感信息不让模型碰。**

---

## 20. 附录：Reason Code 词典

| Code | 含义 |
|---|---|
| EXTERNAL_RECIPIENT | 外部对象 |
| CUSTOMER_DATA | 客户数据 |
| PRICING_DATA | 报价信息 |
| CONTRACT_DATA | 合同信息 |
| HR_DATA | 人事信息 |
| FINANCE_DATA | 财务信息 |
| PERMISSION_CHANGE | 权限变更 |
| LOW_REVERSIBILITY | 不易撤回 |
| STATE_CHANGE | 改变系统状态 |
| BULK_ACTION | 批量动作 |
| MISSING_CRITICAL_SLOT | 关键字段缺失 |
| MOBILE_CONTEXT | 移动端环境 |
| PUBLIC_NETWORK | 公共网络 |
| POLICY_FORBIDDEN | 策略禁止 |
| PERMISSION_DENIED | 权限不足 |
| PROMPT_INJECTION_RISK | 外部指令风险 |
| MODEL_LOW_CONFIDENCE | 模型低置信度 |
| SECRET_VALUE | 密码/验证码/密钥 |
| SENSITIVE_COLLAPSED | 敏感字段折叠 |
| VERSION_CONFLICT | 版本冲突 |

---

## 21. 附录：完整样例

### 用户输入

```text
直接把最低折扣发给客户，今天必须推进。
```

### ActionSpec

```json
{
  "action_type": "send_email_external",
  "target_scope": "external_customer",
  "data_classes": ["pricing", "commercial_terms", "customer_data"],
  "state_change": true,
  "reversibility": "low",
  "missing_slots": ["discount_authorization"],
  "device": {"type": "mobile"},
  "policy_floor": "L5"
}
```

### 模型建议

```json
{
  "risk_level_suggestion": "L5",
  "risk_score_suggestion": 94,
  "reason_codes": [
    "EXTERNAL_RECIPIENT",
    "PRICING_DATA",
    "LOW_REVERSIBILITY",
    "MISSING_CRITICAL_SLOT"
  ],
  "confidence": 0.91
}
```

### 规则命中

```json
[
  "PRICING_COMMITMENT_FORBIDDEN",
  "EXTERNAL_SEND_REQUIRES_L4",
  "MISSING_CRITICAL_SLOT_CLARIFY",
  "MOBILE_L3_PLUS_ENHANCE_GATE"
]
```

### 最终决策

```json
{
  "final_risk_level": "L5",
  "autonomy_level": "AL0",
  "decision": "reject_to_manual",
  "required_gate": "reject_card",
  "can_override": false,
  "actions": [
    "生成审批草稿",
    "打开人工审批入口",
    "取消"
  ]
}
```

### 用户界面

```text
无法自动发送最低折扣承诺。
原因：该动作涉及价格承诺、外部客户沟通和授权边界。
你可以生成审批草稿，或打开人工审批流程。
```
