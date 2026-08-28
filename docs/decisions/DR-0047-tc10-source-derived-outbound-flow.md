# DR-0047：TC-10 来源推导外呼流程图与四层审批边界

- 状态：Accepted；来源合同、规则账本、可遍历状态图、独立 DOCX Verifier、前台四层事实与 PostgreSQL 顺序恢复已落地，最终工程门见对应 Evidence
- 日期：2026-08-29
- Source：`USER-FEEDBACK-20260829-TC10-SOURCE-DERIVED-OUTBOUND-FLOW`
- Scenario：`SCENARIO-033`

## 决策

1. TC-10 继续由 Workspace-first 普通指令触发，不增加 Scenario 选择器。固定适配器只允许 `Operations-008` 的 `运营管理/专业性说明.md`，并绑定逻辑 ID、文件名、展示路径、allowlist、声明大小、file ref 和冻结字节。
2. 服务端从批准 Markdown 的安全行号解析规范性要求。每条原子要求保留 `rule_id/group/locator/excerpt/parameters/expected_action/coverage_state`；生产成功条件不得写死当前规则数量。
3. sections II-IV 中未知、重复、冲突、非法或无法映射的规范性要求不得静默忽略。可识别的新转人工触发会动态加入规则、守卫和路径；无法支持的规范或不可达终态使结果转红。
4. 图使用稳定 node、edge、guard、terminal ID。唯一 START、无悬空边、全节点可达、非终态有出边、所有路径最终到达终态、来源终态可达和关键顺序均由服务端验证。
5. 当前来源要求先确认身份，再告知录音与来意，最后进入欠款引导。第三方只允许转告或禁呼，身份无法确认不得进入欠款话术；时段不合规与频次达限使用不同状态。
6. `拨号`、`写 CRM`、`短信提醒`、`禁呼名单` 和 `转人工` 都只是未来流程节点。本轮只在隔离 Run Workspace 生成设计 DOCX，`external_action=none`。
7. DOCX 必须包含来源规则账本、节点表、边表、守卫表、终态表、覆盖矩阵和完整性摘要。Verifier 重新读取批准 Markdown，并独立解析生成后的 DOCX 表格逐字段核对。
8. `outbound_flow_outcome` 同时写入 Artifact 和 EffectReceipt，并随 Snapshot 持久化。前台分别投影确定性文件/图检查、规则覆盖与缺口、最终审批、真实动作。
9. 来源只笼统列出监管与内部制度，没有版本、批准主体或外部 Registry 回执。因此系统不得声称最新监管合规、正式法律意见或流程已批准。
10. 原 FORTE 输入保持只读；生成后 Runtime 重新读取 Catalog 字节确认未修改。

## 前后端事实

| 前台 | 服务端事实 | 不允许推断 |
| --- | --- | --- |
| 这是流程设计，不是拨号、CRM/短信执行，也不是法律意见 | `outbound_flow_outcome.status=approval_required`、`legal_opinion=false`、`external_action=none` | 已外呼、已写系统或已取得法律意见 |
| 来源、DOCX 和图结构通过或失败 | Artifact `verifier_status/checks[]`、EffectReceipt `status`、`graph_integrity` | 业务已批准或规则是最新监管版本 |
| N/N 条规则覆盖、M/M 个终态可达 | outcome 的动态 counts、`rules[]/terminals[]` | 数量必须固定为 34、7 或历史 13 项 |
| 展开规则的原文位置与映射 ID | `rules[].locator/excerpt/mapped_*_ids/coverage_state` | 浏览器自行解析 Markdown 或推断映射 |
| 最终合规审批尚未发生 | `human_approval_required=true`、`decision` | Artifact 绿灯等于可以投入生产 |
| 拨号、CRM、短信、禁呼写入和转人工均未发生 | Artifact/EffectReceipt `external_action=none` 与禁止副作用 | 文档中的动作节点是执行回执 |

## 拒绝的替代方案

- 写死 flow/terminal 后用同一列表验证：拒绝。规则和图必须从批准来源重新推导。
- 把每次来源变动都当成格式错误：拒绝。合法参数或已支持规则变化必须动态改变图；仅冲突、未知或无路径规则转红。
- 用历史 `13/13` 盖住来源规则覆盖：拒绝。检查清单验证文件和图结构，业务覆盖数量由来源账本动态给出。
- 把流程节点当作真实动作：拒绝。没有 Connector、Permit 或外部回执。
- 因来源写了监管名称就声称最新法律合规：拒绝。来源没有版本与批准主体。

## 验证门

- 当前来源动态得到 15 组、34 条原子要求、31 个节点、36 条边、7 个守卫和 7 个可达终态；这些只属于固定来源当前版本。
- 禁呼时间、频次、录音保存年限和重拨间隔变异分别改变对应参数，其他图身份保持稳定。
- 一致修改身份/录音顺序可改变图；只改一处造成冲突必须 fail closed。
- 新增可识别高龄/重病转人工规则会增加规则、守卫和边；未知规范或无路径终态不得通过。
- DOCX 损坏，缺/多/改边，顺序、终态、rule ref 或 locator 篡改均转红。
- 真实 PostgreSQL 重启后 Artifact、EffectReceipt、outcome 与下载字节一致；这只证明顺序 Runtime 恢复。
- 1440 px 三栏和 390 px 单栏覆盖 canonical、动态来源变体和 Verifier failure；自动化与截图不证明用户理解或生产合规。
