# Office Agent V0.1 关键页规划

视觉统一规则：全部输出为 16:9 横版；沿用参考图的华南理工大学校标、校名字样和蓝色渐变顶部；正文使用白底、深蓝主色、浅蓝描边卡片、线性图标、编号圆点和清晰箭头。页面不做封面或目录，只保留可以直接讲解的核心内容。Demo 截图保持原始界面比例与像素信息，不把 Simulator 描述成真实办公系统写入。

讲解链路：先说明为什么是 workspace-first，再解释人机共编的双流交互；随后进入“模型理解、代码治理”的总体架构；再依次拆解 ActionSpec、风险与策略、Human Gate、Permit 与 Gateway；最后用邮件和日历两个可运行 Demo 收束，并用真实工程范围与边界总结。

## 01 核心范式：Workspace-first Agent

副标题：工作区是主角，Agent 是协作层。

版式：中间放产品总览截图，围绕左侧工作区、右侧对话和底部治理折叠区做三处标注。底部用一句结论收束。

要点：用户无需 Agent 也能编辑与保存；Agent 读取浏览器中的未保存内容；切换 7 类工作区时对话持续存在。

结论：从“聊天里给答案”升级为“在业务对象上共同完成”。

## 02 人机共编：两个流同步推进

副标题：对话在流，工作产物也在流。

版式：上半区是 `用户消息 → ConversationPlan → 最终 Artifact → SSE 增量呈现`；下半区是三张卡片，分别解释未保存上下文、工作区渐进写入、来源/权限/修改记录。

准确边界：服务端先保存最终一致的 WorkspaceArtifact，再发送 `artifact.stream.started → artifact.delta → artifact.updated`；动画不是逐 token 数据库存储。

## 03 总体架构：模型理解，代码治理

副标题：把创造性与控制面分开。

版式：主链从 `Workspace + Chat` 依次经过 `ConversationService`、`LLM`、`Pydantic Contracts`、`Risk / Policy / Evidence`、`LangGraph Human Gate`、`Ed25519 Permit`、`Tool Gateway`、`Simulator`；底部左右分栏展示信任边界。

模型可产生：自然语言、ArtifactDraft、ActionCandidate。确定性服务产生：风险、策略、证据、审批状态、Permit、执行结果与审计事件。

结论：模型没有直接调用副作用工具的入口。

## 04 ActionSpec：把意图变成可校验动作

副标题：自然语言不直接授权，先形成结构化业务事实。

版式：中心 ActionSpec，周围十个字段；右侧展示 `send_email / email.send` 示例；底部展示三个实现原则。

关键字段：`action_type`、`capability`、`target_scope`、`recipients`、`resources`、`data_classes`、`state_change_type`、`reversibility`、`missing_slots`、`parameters` 与 `source_refs`。

实现原则：Pydantic `extra=forbid`；服务端补充 trace、action hash 与 idempotency key；后续风险、策略、审批、Permit 和工具参数全部绑定 ProposedActionSpec。

## 05 风险分级：普通高风险可审，L5 直接拒绝

副标题：不是“外部动作一律 L5”。

版式：左侧是普通风险累计，中央是 L0-L5 色阶，右侧是 L5 硬触发；下方给出外发报价邮件案例。

普通因子：外部目标 +2、公开发布 +2、敏感数据 +1、低可逆 +1、缺字段 +1；普通业务累计封顶 L4。L5 仅由公开泄露凭据、受限 capability、`restricted_execution` 触发，并由策略直接 deny。

案例：外发报价邮件可为 L4，通过批准报价来源、当前用户确认和销售经理审批继续处理。

## 06 Human Gate：确认是流程节点

副标题：补证据 → 分角色审批 → 最终授权 → 自动继续。

版式：左侧状态机 `WAITING_EVIDENCE → WAITING_APPROVAL → READY_TO_AUTHORIZE → EXECUTED`，侧支为 `DENIED / FAILED`；右侧嵌入真实确认卡截图。

要点：确认卡是非模态 tray，不遮挡历史消息；每次 resume 重新评估风险、策略、证据和 ControlPlan；确认后继续执行，再由 Agent 根据 Simulator 结果收尾。

## 07 一次性执行许可：只批准这一次动作

副标题：不是放开工具权限，而是给当前动作一张短时、单次的通行证。

版式：用三张大卡片依次说明“绑定当前内容 → 签发一次性许可 → 执行前再次核对”。隐藏哈希、策略版本、幂等键等实现字段，只保留操作人、动作、目标/资源和参数四类观众可理解的信息；许可强调仅限当前动作、短时有效、只能使用一次。

对比示例：批准内容为“客户 A + 报价 V3”，执行内容不变则核对一致并允许执行；收件人或附件被替换则立即拦截。

结论：人工批准绑定的是具体内容，不是给工具一张长期通行证。

## 08 Demo ①：邮件共编到受控发送

副标题：从工作区草稿，到确认卡，再到结果回到 Agent。

版式：左右并排使用邮件撰写中和确认卡两张真实截图，中间用编号箭头串联。

步骤：读取当前草稿 → 渐进写入主题与正文 → 提议 `email.send` → 补证据/审批 → 一次性 Permit → Email Simulator → Agent 返回结果。

边界：演示中的“发送成功”仅代表 Simulator 成功，不是真实邮箱投递。

## 09 Demo ②：月历中创建受控邀请

副标题：日历是一级工作区，外部影响仍走同一治理链。

版式：左右并排使用创建前和确认卡两张真实截图；下方用四步链路概括。

步骤：读取现有日程 → 在工作区生成会议 → 提议 `calendar.invite` → 当前用户确认 → Calendar Simulator → Agent 收尾。

## 10 V0.1 已验证的工程闭环

副标题：先验证治理范式，再替换真实连接器。

版式：上方六个大数字，中间是一条完整闭环，底部分为“当前边界”和“下一步”。

真实数字：7 类可编辑工作区、25 类 ActionCandidate、5 个端到端 Simulator capability、8 类 Evidence requirement、4 个确定性治理场景、22 项自动化测试。

当前边界：副作用工具全部是 Simulator；Thread/Message 和 Permit replay set 仍在进程内存；身份头是 P0 占位；无真实企业 Connector。

下一步：SSO/RBAC → Connector SDK 与沙箱 → 对话和 replay 持久化 → 多实例一致性与任务队列 → 评测与可观测性。
