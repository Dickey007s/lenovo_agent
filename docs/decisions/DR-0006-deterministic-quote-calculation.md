# DR-0006：报价数值由确定性投影核算，模型只解释结果

| 字段 | 内容 |
| --- | --- |
| Decision ID | `DR-0006` |
| Owner | Office Agent 项目组 |
| Date | 2026-08-11 |
| Status | `Verified`（仅限固定演示报价、当前公式、revision/request epoch 协议、Artifact/Action/Thread 绑定和被测前台恢复；非生产计价或用户研究结论） |
| Scope | 报价行编辑与核算、数值/来源问答、保存复核、版本/晚到结果恢复，以及报价进入受控动作时的信任边界 |
| Depends on | `DR-0001`、`WorkspaceArtifact(kind=quote)`、Conversation SSE |

## 1. 用户场景与问题

目标用户是正在核对客户报价的销售、客户经理或报价审批人。用户在当前报价表中查看或修改行项目后，会直接询问“总折扣多少”“再算一次”“数据从哪里来”。原路径把这类问题归入通用问答，只把历史消息和当前时间交给模型，已经组装的活动工作区没有进入回答；模型因此生成了与屏幕不同的 2000000 元、1770000 元和 88.5%，追问来源后又把 253400 元同时当作原价和折后价。

完成条件是：当前屏幕、保存内容和 Agent 数值回答使用同一组行级事实；基线三行重算结果为标准总价 272000 元、折后总价 253400 元、优惠金额 18600 元、综合折后比例 93.16%（约 9.32 折）、优惠率 6.84%；所有行的折后比例均不低于 88%（8.8 折）底线。用户修改数量或折后比例后，行小计、四项汇总、底线状态和 Agent 回答必须一起变化。

关键异常路径包括：字段缺失或非法、比例越界、过多行、金额超出安全范围、当前行数与服务端报价版本不一致、显式空 `workspace_context`、旧行小计/总计不一致，以及用户要求把总价写入邮件或发送报价。前六类必须 fail closed；旧合计必须被忽略并重算；写入或发送属于业务动作，不能被核算问答路由截获。

## 2. 来源与依据

| Source ID | 类型 | 精确引用 | 支持判断 | 局限 |
| --- | --- | --- | --- | --- |
| `USER-FEEDBACK-20260811-QUOTE-CALCULATION-04` | Stakeholder feedback | [`USER-FEEDBACK-20260811-06-quote-calculation-grounding.md`](../sources/USER-FEEDBACK-20260811-06-quote-calculation-grounding.md) 及两张原始截图 | 原 Agent 数值和来源回答与当前工作台冲突，需要建立单一核算事实链 | 单一 Stakeholder 反馈，不是目标用户研究，也不覆盖真实报价规则 |
| `SOURCE-QUOTE-CALCULATOR-20260811` | 源码事实 | 实现提交 `2f9866f + fe865bd`：`services/api/app/application/quote_calculator.py`、`services/api/app/application/conversations.py`、`services/api/app/application/runs.py`、`packages/evidence/mock.py`、`apps/web/app/quote-calculator.ts`、`apps/web/app/page.tsx` | 服务端 Decimal 与前端 BigInt 核算；revision/request epoch 冲突保护；Artifact 来源、Action/Thread 绑定与 unresolved-context deny | 只描述当前提交，不能证明真实 CRM、生产财务精度或多实例一致性 |
| `QUOTE-WORKSPACE-DETERMINISTIC-CALCULATION-20260811` | 自动化、运行与截图证据 | [`QUOTE-WORKSPACE-DETERMINISTIC-CALCULATION-EVIDENCE-20260811.md`](../evidence/QUOTE-WORKSPACE-DETERMINISTIC-CALCULATION-EVIDENCE-20260811.md) | 覆盖基线、编辑、舍入、越界、空上下文、字段所有权、来源回答、revision 冲突、恶意 Action/source、结果重放和浏览器 UI | 不替代真实用户研究、真实 Connector、复杂计价或数据库/多实例 CAS 验证 |

## 3. 决策与备选

采用“双端确定性计算、服务端信任边界、模型只解释”的方案：

1. 服务端以 `Decimal` 和 `ROUND_HALF_UP` 按行计算 `qty × unit_price`，先将标准行金额舍入到分，再乘 `discount` 并将折后行金额舍入到分；总计由行金额求和。前端用整数分和 `BigInt` 实现同一顺序与舍入规则。
2. 服务端拥有 `quote_id`、`customer`、`currency`、`approved_floor`、每行 `unit_price` 和 `sources`。当前用户可编辑 `name`、`qty`、`discount`、`valid_until`；客户端提交的 `subtotal`、`total`、审批状态和上述服务端字段都不能成为核算事实。
3. 报价核算、复算、底线检查和来源追问由确定性意图路由处理，通过 Conversation SSE 返回可读解释；写入、修改、保存、发送、创建或导入等动作词会退出该快捷路由，继续既有业务规划与治理路径。
4. 非法或不完整输入不显示部分总计，也不回退到旧值。保存后的服务端内容写回规范化小计和总计；相对基线发生可编辑字段变化时设置 `approval.status=needs_review` 与 `requires_recheck=true`。
5. 同一 Thread 的消息流串行更新，避免两个并发回答用旧 Thread 覆盖彼此；这不改变 Conversation 仍为进程内存状态的边界。
6. 显式未保存上下文携带 `workspace_artifact_id/workspace_revision`，保存携带 `expected_artifact_id/expected_revision`。过期保存返回 409；流式处理遇到过期或规划期间 Artifact 变化时发出 `workspace.conflict`，不写回也不创建动作。Web 保留草稿并提供查看最新或有界三方重应用，同字段双改拒绝自动合并。若用户在请求等待期间继续编辑，晚到 Agent Artifact 也以请求时版本为 base 应用同一规则。
7. 模型提交的 Artifact `sources` 和可执行 Action 参数/治理元数据不是权威事实。已有 Artifact 保留服务端来源，新 Artifact 使用服务端默认来源；注册 capability 从当前 Artifact 重建收件人、附件、正文、目标范围、数据分类、状态变化、可逆性与 Artifact revision，内容不匹配时 fail closed。纯文本收件人身份未解析或附件类别不明时确定性 deny，Action 自身值和用户自报姓名/哈希不能充当可信 evidence。
8. Conversation 创建的 Run 绑定真实 Thread，LangGraph checkpoint 另以 `thread_id:run_id` 隔离；跨 Thread continuation 即使同一用户也拒绝。动作终态结果说明暂时失败时可以重试；成功后同一 API 进程重放同一 `message.completed`，前端按 `message_id` upsert，避免重复结果。

未采用让 LLM 继续计算，因为数值正确性无法靠 Prompt 稳定保证，且历史消息会污染当前工作区事实。未采用信任客户端 `subtotal/total`，因为它们可能过期或被篡改。未采用只修复 Agent 回答而保留前端浮点计算，因为这样仍会在舍入、编辑和异常输入上产生两套结果。未采用只依赖服务端保存后再显示，因为用户需要核对尚未保存的当前编辑值。

## 4. 后端事实与状态转换

| 事实或状态 | 权威来源 | 转换与语义 |
| --- | --- | --- |
| 报价基线身份、币种、底线、标准价、来源 | 当前用户的 `WorkspaceArtifact(kind=quote)` 服务端内容和 `sources` | `workspace_context` 不能覆盖；行数不一致即拒绝核算 |
| 当前可核算编辑值 | 浏览器显式发送的 `workspace_context.items[].name/qty/discount` 与 `valid_until`，合并到服务端基线 | 仅用于本次未保存视图；显式 `{}` 不回退到旧报价 |
| 行小计与四项汇总 | 服务端 `calculate_quote`；前端同公式只做即时投影 | 旧 `subtotal/total` 被忽略；非法输入时聚合值为空，不显示部分结果 |
| Agent 核算或来源回答 | `ConversationService` 对确定性意图调用 `render_quote_answer` | 依次发出 `message.created`、`assistant.status`、`message.started`、`assistant.delta`、`message.completed`；模型不生成数值 |
| 已保存但待复核 | `WorkspaceArtifact.content.approval.status=needs_review`、`requires_recheck=true` | `PUT /workspace/quote` 成功后持久化；若绑定旧 Action 则继续使其失效 |
| 输入错误 | 服务端 `QuoteCalculationError` 或前端计算器错误数组 | 保存返回 422；对话明确拒绝猜测；前端显示“核算暂停”和“待核对” |
| Workspace 版本 | `WorkspaceArtifact.artifact_id/revision` | 显式上下文与保存均携带当前 token；保存成功 revision +1，旧 token 不覆盖最新内容 |
| 版本冲突 | 保存 HTTP 409；Conversation SSE `workspace.conflict.latest_artifact` | 前端保留草稿并读取最新；只重应用相对 base 的本地独有修改，同字段双改/行结构变化交给用户 |
| Artifact 来源与可执行动作 | 服务端现有/默认 `sources`；`_bind_action_to_artifact` 与确定性 unresolved-context policy 输出 | 模型 source/payload/治理元数据不能直接执行；不匹配或竞态不创建 Run；未解析收件人/附件类别直接 deny，自报 evidence 不能解锁 |
| 动作结果送达 | `RunSnapshot.thread_id`、终态 Run 与进程内 `(thread_id, run_id) → completed message` | continue 先校验真实 Thread；首次成功写 Thread，重试重放同一消息与 `action.closed`，前端 upsert；跨 Thread 拒绝 |
| 请求等待期本地编辑 | 前端请求时 Artifact/edit token、本地草稿和晚到服务端 Artifact | 不同字段自动保留双方改动并保持 dirty；同字段双改进入 conflict，不直接接受晚到 `artifact.updated` |

同一线程内消息串行化、Workspace 锁、revision 比较和结果重放只保证当前 API 进程中的顺序与缓存语义，不提供数据库原子 CAS、多实例锁、跨进程队列、SSE 游标恢复或 Thread 持久化。前端即时投影不是新的审批或服务端业务状态；只有保存响应可以宣布 `needs_review` 已持久化。

## 5. 前台输出与隐藏边界

报价工作台显示客户、报价编号、有效期和“最低折后比例”，表格显示项目、数量、标准价、“折后比例 %”和重算小计；底部固定显示标准总价、优惠金额与优惠率、综合折后比例与折数、折后总计，以及底线/待复核状态。这样把“93.16% 是折后价格比例”和“6.84% 是优惠率”明确区分，避免把 88% 底线误读成总优惠。

用户可以直接编辑项目名、数量、折后比例和有效期，未保存编辑立即重算并可被 Agent 读取；可以使用“核算综合折后比例”“检查最低折后比例”“说明数据来源”入口。输入不合法时，行外聚合值统一显示“待核对”，状态区说明首个错误，Agent 明确不使用历史金额；用户修正字段后可恢复核算。保存修改后前台显示等待重新复核，不能继续展示基线已批准的含义。

保存或 Agent 处理发现版本过期时，页面显示“工作区已有更新”，当前草稿不被丢弃。用户可查看服务端最新版本，或把仅在本地修改且服务端未同时修改的字段重新应用后复核保存；同字段双改会列出具体字段并停止自动合并。用户在等待 Agent 时继续编辑也采用相同保护：不同字段显示“Agent 已更新并保留了你的修改”，同字段则保留输入并要求处理冲突。动作已到终态但结果说明未确认送达时，输入区上方提供“重新读取结果”，重放不会新增第二条完成消息；结果不能跨 Conversation Thread 写入。

普通界面与回答不展示服务端内部缓存、原始 Prompt、思维链、Thread 锁、Decimal/BigInt 中间值、底层堆栈或真实凭据。来源只显示“演示数据”与业务标签；不得写成已访问真实 CRM。报价 ID、客户、币种、最低折后比例和标准价可以作为当前演示报价的业务事实展示，但不能由浏览器覆盖。

## 6. 验证与边界

独立证据记录见 [`QUOTE-WORKSPACE-DETERMINISTIC-CALCULATION-EVIDENCE-20260811.md`](../evidence/QUOTE-WORKSPACE-DETERMINISTIC-CALCULATION-EVIDENCE-20260811.md)。实现提交 `2f9866f + fe865bd` 的封口结果为：全量 Python `105 passed, 1 skipped (2.63s)`；报价/Conversation 聚焦 `51 passed (1.55s)`；报价浏览器 `14 passed (23.5s)`；完整浏览器 `26 passed (59.6s)`；Ruff、前端 lint 与 Next.js build 通过。稳定桌面截图为 `1440 x 900`、164869 bytes、SHA-256 `3BDA0E2F2C5E34F0624349E26D977D37F5B5FA1D1169AD9D72EFDD41D14F69ED`。

因此本决策在固定演示报价、当前公式、服务端字段所有权、revision/晚到结果冲突恢复、Artifact/Action/Thread 绑定和被测浏览器路径内为 `Verified`。未解析收件人/附件采用固定演示 deny，不等于已接入企业通讯录或内容分类。它不覆盖税费、汇率、阶梯价、套餐依赖、真实审批制度、真实 Connector、生产并发、数据库 CAS、多实例一致性、报价专用移动截图或目标用户可用性；工具执行仍全部来自 Simulator。

## 7. 关联项

- Source：`USER-FEEDBACK-20260811-QUOTE-CALCULATION-04`
- Evidence：`QUOTE-WORKSPACE-DETERMINISTIC-CALCULATION-20260811`
- API：`POST /v1/threads/{thread_id}/messages/stream`、`PUT /v1/workspace/quote`
- 代码：`services/api/app/application/quote_calculator.py`、`services/api/app/application/conversations.py`、`apps/web/app/quote-calculator.ts`、`apps/web/app/page.tsx`
- PR：[`#11`](https://github.com/Dickey007s/lenovo_agent/pull/11)
