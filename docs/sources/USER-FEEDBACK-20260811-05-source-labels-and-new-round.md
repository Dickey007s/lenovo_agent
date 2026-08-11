# USER-FEEDBACK-20260811-05：来源标识与新一轮语义不清

## 1. 来源

本记录来自 2026-08-11（Asia/Shanghai）当前 Codex 协作任务中的 Stakeholder 原始反馈。反馈附带当前运行页面截图，并明确询问：

> “这些是什么意思，还有这个再次演示是什么意思，是把当前的状态设置为能启动某个demo演示的状态吗”

截图中被指出的内容包括收入冲突卡内的原始 `fixture:` 来源标识，以及终态入口“再次演示”。原图已留存在 [`user-feedback-20260811-source-and-new-round-ambiguity.png`](../evidence/assets/user-feedback-20260811-source-and-new-round-ambiguity.png)：`1415 x 939`、225659 bytes、SHA-256 `D72498921E712117E82A827B015EBDBAE374F284EBD7CAEA2E7851DCA256B613`。来源类型登记为 **Stakeholder feedback**。这是项目决策者对当前可运行原型的直接理解反馈，不是目标用户访谈、可用性实验或统计性用户研究。

## 2. 支持的判断

- 普通业务界面直接展示 `fixture:crm/...`、`fixture:forecast/...` 等内部来源标识，不能帮助用户判断来源性质和业务含义；固定 Demo 1 应显示“演示数据”及可读的业务来源名称，原始标识不进入 DOM。
- “再次演示”没有说明它是重置旧状态、恢复到可启动状态，还是创建新任务，动作语义存在歧义。
- 终态入口应统一为“开始新一轮汇报”：前端创建一个新的独立 Task 并立即启动，旧 Task、工件、事件和 Commit 保留，不重置或覆盖上一轮。
- 非 Tasks 工作区不应继续承载冲突决定和分支控制；只显示后台任务摘要和前往 Tasks 的入口，避免用户在编辑邮件时误把技术控制面当作当前工作内容。

## 3. 局限

该反馈足以确认两处可理解性问题并约束当前修订，但不能证明修订后的标签、跨工作区摘要或新一轮入口已被目标用户理解。自动化只能验证 DOM、动作调用和服务端事实一致；至少 5 名接近目标角色参与者的无引导形成性测试仍未完成。

当前后端会保留多个 TaskSnapshot，前端却还没有历史轮次选择入口。因而“旧轮次保留”只表示数据和审计记录未被覆盖，不表示用户已经可以在界面中自由切换任意历史轮次。

## 4. 关联项

- Source ID：`USER-FEEDBACK-20260811-ROUND-AND-SOURCE-03`
- Decision：`DR-0004`、`DR-0005`
- UI 事实矩阵：[`UI_SERVER_FACT_MATRIX.md`](../contracts/UI_SERVER_FACT_MATRIX.md)
