# Office Agent V0.1 · Presentation Brief

本文用于后续 Agent 生成汇报材料。内容只陈述 V0.1 已实现且可由代码或演示验证的事实；制作 PPT 前应以当前 README、源码和自动化测试再次核对。

## 1. 一句话叙事

Office Agent V0.1 把 AI 放在可独立工作的邮件、文档、报价、任务、日历、报销和 CRM 工作区旁边：模型负责理解与辅助编辑，确定性服务负责风险、证据、审批、授权和工具执行，从而让“会做事的 Agent”保持可控、可确认、可追溯。

## 2. 核心价值

本版本要证明的不是“接了多少办公系统”，而是三种可复用能力：

1. **协同方式**：Agent 不只在聊天框回答，而是读取用户正在编辑的内容，并以渐进动效写回工作区。
2. **自动化边界**：草稿和查询可低摩擦完成，真实副作用必须经过 ActionSpec、Risk、Policy、Evidence、Approval、Permit 与 Gateway。
3. **可审计闭环**：用户确认后不是前端直接宣布完成，而是继续运行工具，再由 Agent 根据执行结果回复。

## 3. 可用于封面或摘要的数字

| 指标 | V0.1 实际值 | 代码依据 |
| --- | ---: | --- |
| 办公工作区 | 7 类 | `WorkspaceArtifact.kind` |
| ActionSpec 候选动作 | 25 类 | `packages/contracts/models.py` |
| 端到端 Simulator capability | 5 个 | `simulators/` 与 Tool Gateway 注册 |
| Evidence requirement | 8 类 | `application/evidence_catalog.py` |
| 确定性治理演示场景 | 4 个 | `application/demo3.py` |
| 自动化测试 | 22 项 | `uv run pytest -q` 的定稿结果 |

7 类工作区为邮件、文档、报价表、任务、日历、报销和 CRM；审计是独立观察视图，不计入可编辑 WorkspaceArtifact。

## 4. 建议的 10 页汇报结构

### 第 1 页：为什么需要 Workspace-first Agent

表达重点：传统聊天机器人把结果留在对话里，用户还要复制、核验、切系统；本项目让工作区保持主位，Agent 是协作层。

建议画面：全屏产品总览，左侧工作区、右侧 Agent、底部非模态确认卡。不要使用早期版本“对话在左、审批在右”的截图。

### 第 2 页：产品交互范式

展示：工具栏切换七类工作区；对话不消失；分隔条可拖动；双方独立滚动；来源/权限/修改记录在底部折叠区。

关键措辞：用户可以独立编辑和保存，Agent 能读取浏览器中尚未保存的活动内容。

### 第 3 页：Agent 如何真正进入工作流

展示：从空白邮件开始，请 Agent 撰写，主题和正文渐进出现；或者从月历选择日期后让 Agent 创建邀请。

关键措辞：流式不仅发生在对话气泡，也发生在业务产物；数据库保存最终 Artifact，动画只是增量呈现。

### 第 4 页：模型与治理的职责分离

使用下图：

```mermaid
flowchart LR
    M["LLM：意图、文本、候选业务字段"] --> V["Pydantic 严格校验"]
    V --> G["确定性 Risk / Policy / Evidence"]
    G --> H["Human-in-the-loop"]
    H --> P["Ed25519 单次 Permit"]
    P --> T["Gateway 校验"]
    T --> S["Simulator"]
```

关键措辞：模型不能自己决定风险、审批是否通过、证据是否可信，也不能直接调用副作用工具。

### 第 5 页：风险分级不是“什么都是 L5”

展示普通累积分级与硬触发的区别：外部联系人、敏感数据、低可逆和字段缺失增加风险，普通累积最高 L4；只有受限 capability、受限执行或公开泄露凭据等硬条件进入 L5。

可用案例：外发普通客户邮件通常需要确认但不必是 L5；外发报价及低可逆因素可到 L4；付款、签约、权限变更、凭据读取和批量删除直接拒绝。

### 第 6 页：人工确认是流程节点，不是文字提示

展示确认卡的状态变化：`WAITING_EVIDENCE → WAITING_APPROVAL → READY_TO_AUTHORIZE → EXECUTED`。

关键措辞：卡片不完全遮挡对话；用户仍可继续交流；批准后系统继续执行，最终结果由 Agent 回答。风险说明在确认前文本中只出现一次，卡片保留结构化字段便于操作。

### 第 7 页：Permit 和参数绑定

展示 Permit 绑定 subject、capability、action hash、参数哈希、policy version、approval ids、TTL、单次使用和 idempotency key。

可用演示：对 `pricing` 场景完成前置条件后运行 tamper-check，证明更换收件人或附件时 Gateway 拦截，而不是“已批准就任意执行”。

### 第 8 页：可追溯与可恢复

展示审计视图中的 `RUN_CREATED`、`ACTION_PARSED`、`CONTROL_PLAN_UPDATED`、`APPROVAL_RECORDED`、`PERMIT_ISSUED`、`TOOL_EXECUTED`。

准确边界：配置 PostgreSQL 时，Workspace、Run、Audit 与 LangGraph checkpoint 可恢复；Conversation Thread/Message 和 Permit replay set 当前仍在进程内存中。

### 第 9 页：V0.1 工程实现

展示技术栈：Next.js 16、React 19、TypeScript；FastAPI、Pydantic、LangGraph；PostgreSQL 16；Ed25519 JWT；OpenAI-compatible LLM；SSE 双流。

强调两个流：Conversation SSE 服务文字与工作区增量，Run SSE 服务有序审计与确认卡刷新。

### 第 10 页：阶段结论与下一步

阶段结论：V0.1 已验证 workspace-first、人机共编、确定性治理、人工 Gate、最小权限 Permit、Simulator 执行与 Agent 结果闭环。

下一步优先级：真实 SSO/RBAC → Connector SDK 与沙箱 → 对话和 replay 持久化 → 多实例一致性/任务队列 → 历史版本和多人协同 → 评测与可观测性。不要把“增加更多模型自治权”列为首要路线。

## 5. 推荐演示流程

### 流程 A：从空白邮件到 Agent 共编

1. 打开邮件工作区，点击“新邮件”，确认收件人、主题和正文为空。
2. 在右侧输入：“根据客户 A 最新来信和已批准报价，起草一封方案确认邮件，先不要发送。”
3. 观察 Agent 状态、对话流式输出和邮件字段渐进写入。
4. 展开底部“上下文与治理”，展示邮箱、CRM 和报价库来源，以及权限和修改记录。
5. 手动再改一行并保存，说明用户与 Agent 在同一业务对象上协作，而不是复制聊天文本。

演示点：workspace-first、未保存上下文、来源可见、流式 Artifact、独立保存。

### 流程 B：外发报价邮件治理闭环

1. 基于当前邮件要求 Agent “保存并发送”。
2. Agent 在文本中说明风险等级、简要规则、所需 capability 和确认条件。
3. 底部确认卡显示结构化风险、证据状态和角色审批；对话仍可滚动和继续输入。
4. 选择已批准报价来源并完成 `current_user`、`sales_manager` 确认。
5. 点击最终执行；展示 Permit、Simulator 执行和 Agent 最终“发送成功”回复。
6. 打开审计视图，按事件序列解释整个闭环。

演示点：L4 而非泛化 L5、自动取证、逐角色审批、一次性授权、结果回到 Agent、单次风险说明。

### 流程 C：月历与受控邀请

1. 打开日历，展示标准月视图和有日程日期的红点/高亮。
2. 点击 7 月 14 日，以动效展开当日全部日程。
3. 让 Agent “明天下午 3 点安排一小时报价会议，并邀请外部客户”。
4. 观察日历工作区被更新以及外部邀请的确认卡。
5. 确认后展示 `calendar.invite` Simulator 结果和 Agent 收尾。

演示点：真实日历一级界面、按日浏览、Agent 编辑工作区、外部影响受控。

### 可选流程 D：参数篡改拦截

使用 `pricing` 固定场景完成证据与审批，再调用 `/v1/demo3/actions/{action_id}/tamper-check`。展示 `TAMPER_BLOCKED`，说明 Permit 绑定具体参数而非只绑定“允许发邮件”。

## 6. 建议截图与视觉素材

- 产品总览：1280×720 或 16:9，完整显示工作区、拖动分隔和 Agent。
- 邮件共编：空白态一张、渐进写入中一张、确认卡一张。
- 日历：月视图和某日展开态。
- 确认卡：优先展示 L4 报价案例，确保风险、规则、证据、审批和执行按钮同时可读。
- 审计：截取从 `RUN_CREATED` 到 `TOOL_EXECUTED` 的连续事件。
- 架构图：直接根据 `docs/ARCHITECTURE.md` 的 Mermaid 重绘，避免在一页堆满类名。

截图前清理旧 Thread 与旧 Workspace 数据，统一浏览器缩放为 100%，窗口最大化，并使用不含真实个人或企业信息的 Demo 地址。

## 7. 可说与不可说

### 可以明确陈述

- “实现了 OpenAI-compatible 模型驱动的真实对话与结构化规划。”
- “实现了 7 类可编辑办公工作区和 SSE 流式人机协作。”
- “实现了确定性风险/策略/证据/审批/Permit/Gateway 闭环。”
- “实现了 5 个 Simulator capability 的端到端受控执行。”
- “配置 PostgreSQL 时可持久化 Workspace、Run、Audit 与 checkpoint。”

### 不可夸大

- 不说“已经接入并发送真实企业邮件”；当前是 Email Simulator。
- 不说“已经连接真实 CRM、OA、知识库和日历”；当前是 Fixture/Mock Resolver。
- 不说“已经具备生产级权限系统”；身份头是 P0 占位。
- 不说“所有 ActionSpec 都能执行”；25 类是协议目录，只有 5 个 capability 注册了端到端 Simulator。
- 不说“全量会话长期保存”；Thread/Message 重启后丢失。
- 不说“L5 操作经审批可以执行”；当前策略对受限能力和 L5 直接 deny。
- 不把前端打字动效描述成模型 token 直接写数据库；数据库保存的是最终 Artifact。

## 8. 常见问答

**为什么不用 LLM 直接判断风险？**  风险和权限属于可验证控制面，需要稳定、可测试和可审计；LLM 只提供业务候选事实。

**既然要确认，Agent 还自动化吗？**  草稿、查询、取证和低风险准备由 Agent 自动完成；确认只出现在产生外部影响或系统写入的最小边界，批准后链路自动继续。

**为什么最终只是 Simulator？**  V0.1 先验证治理协议和产品交互。真实 Connector 可替换工具适配器，而不改变上层 ActionSpec、Permit 和审计模型。

**如何避免审批后参数被替换？**  Permit 同时绑定动作哈希与逐参数哈希，Gateway 在调用工具前重新计算并比对。

**现在最大的生产化缺口是什么？**  真实身份和 Connector、分布式 replay/幂等、Conversation 持久化、后台任务、多实例一致性和生产评测。

## 9. 术语表

| 术语 | 含义 |
| --- | --- |
| WorkspaceArtifact | 用户或 Agent 正在编辑的持久化办公产物 |
| ActionCandidate | LLM 只能填写的候选业务事实 |
| ProposedActionSpec | 服务端补齐身份、Trace、哈希和幂等键后的动作 |
| RiskAssessment | 确定性风险等级、维度和 reason code |
| PolicyEffect | 策略对 capability 的 allow/blocked/deny 及前置条件 |
| EvidenceRecord | 由受信系统解析的证据状态与摘要 |
| ControlPlan | 当前动作的统一控制状态和 UI 面板规格 |
| ApprovalRecord | 与 Action 和角色绑定的人工决策记录 |
| Permit | 短时、单次、参数绑定的 Ed25519 JWT 授权票据 |
| Tool Gateway | Permit 校验、重放保护和工具路由边界 |
| Simulator | 不接触真实办公系统的副作用模拟器 |
