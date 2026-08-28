# DR-0039：TC-10 流程设计成果与真实执行边界

- 状态：Implemented，真实 Provider 与本地完整门已通过，等待 PR 门收尾
- 日期：2026-08-28
- Source：`USER-FEEDBACK-20260828-TC10-DESIGN-VERSUS-EXECUTION`
- Scenario：`SCENARIO-025`

## 决策

1. TC-10 仍是 Workspace-first 通用 Agent 命中的一个固定本地适配器，不增加 Scenario 选择器。
2. 下载 DOCX 首部必须说明文档回答什么、采用《专业性说明.md》的哪些规则、实际执行边界和采用前人工复核责任；正文保留完整流程边和六类终态。
3. Run Workspace Artifact 增加可选、服务端拥有的 `deliverable_type`、`key_outputs`、`review_guidance`、`execution_summary`。这些字段是固定适配器事实，不是模型自由叙述。
4. 成果区在文件列表前显示“这次实际发生了什么”；TC-10 明确写出只生成 DOCX，文档中的拨号/CRM 是流程节点，不是执行回执。禁止副作用继续来自 EffectReceipt。
5. 即使 Run 已形成成果但没有 `brief`，页面末尾仍用同一 Artifact 事实形成“本次任务结语”，显示确定性检查数量和人工复核原因。

## 前后端事实

| 前台 | 服务端事实 | 不允许推断 |
| --- | --- | --- |
| 流程设计 DOCX | Artifact `deliverable_type`、`media_type`、下载字节 | 已执行外呼 |
| 采用专业说明 | Artifact `statistic_basis`、`source_file_refs` | 规则是当前生产制度 |
| 六类终态 | Artifact `key_outputs[]`、`check-outbound-terminals` | 任意外呼流程完整 |
| 没有拨号/CRM/短信 | Artifact `execution_summary`、EffectReceipt `prohibited_side_effects[]/external_action=none` | Connector 曾被调用后回滚 |
| 仍需人工复核 | Artifact `review_guidance/review_required` | 自动化替代业务或合规批准 |

## 备选方案

- 只修改卡片文案：拒绝。客户端会从场景名猜事实，无法与 Snapshot 对齐。
- 只展开 EffectReceipt：拒绝。用户仍需阅读技术回执才能理解最重要边界。
- 把 TC-10 改成真实拨号演示：拒绝。当前没有授权、Connector、Permit 和生产身份边界。

## 验证门

- 后端必须解析真实下载 DOCX 并独立核对 13 项 Gate。
- live gate 必须校验下载字节的 DOCX ZIP/XML、唯一 START 和必需正文锚点，不能只相信 Snapshot 检查数量。
- E2E 必须看到成果类型、采用依据、六类终态、人工复核原因、显眼未执行边界和任务结语。
- 390 px 不得出现页面级横向溢出；截图只证明被测渲染，不证明用户理解。
