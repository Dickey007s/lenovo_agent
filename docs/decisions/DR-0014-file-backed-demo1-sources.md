# DR-0014：用文件驱动的仿真企业资料替代 Demo 1 代码常量

| 字段 | 内容 |
| --- | --- |
| Decision ID | `DR-0014` |
| Owner | Office Agent 项目组 |
| Date | 2026-08-20 |
| Status | Verified（限定工程范围） |
| Scope | Demo 1 客户 A 经营汇报的文件来源、来源快照、收入冲突与前台证据卡 |
| Depends on | `DR-0002`、`DR-0005`、`DR-0009`、`DR-0013` |

## 1. 场景与问题

目标用户是准备客户经营会材料的客户经理或项目负责人。经营会临近时，用户要把历史财务关账记录、当前销售预测、项目周报和客户邮件汇总成经营分析、风险页和客户回复草稿。当前 Demo 1 只在代码中生成 `fixture:` 来源和 2,400/2,680 万两个常量，用户看不到历史文件、记录时间、字段口径，也无法理解“当前操作为何与旧文件冲突”。

完成条件是：仓库中存在可复查的仿真文件；服务端只读取 manifest allowlist 中的文件并校验哈希；Task 创建时冻结解析后的来源快照；Verify 生成包含当前操作上下文的 Conflict；前台显示文件名、系统、记录时间、字段值和 before/after 影响；来源损坏或发生变化时不猜测、不继续。

关键异常路径包括：文件缺失、路径越界、符号链接、大小越界、manifest 不一致、哈希变化、CSV/EML/JSON 解析失败、旧 Task 运行期间文件变化和前端加载旧 Snapshot。以上路径均必须保持 fail closed，并提示基于当前文件开始新一轮任务。

## 2. 来源与依据

| Source ID | 类型 | 支持的判断 | 局限 |
| --- | --- | --- | --- |
| `USER-FEEDBACK-20260820-06` | Stakeholder feedback | 用户明确要求真实文件形态、历史文件与当前操作冲突 | 单一反馈，不是目标用户研究；不证明新场景有效 |
| `ENTERPRISE-DEMO-DATA-RESEARCH-20260820` | 官方资料研究登记 | 支持采用企业实体、工作簿/导出文件、记录状态和样例数据隔离边界 | 只借鉴结构和业务语义，不证明 Lenovo 或客户事实 |
| `MICROSOFT-ADVENTUREWORKS-SCHEMA` | Microsoft 官方源码/README | 支持客户、销售、订单、期间和记录状态等企业数据结构语义 | 不作为本项目运行时数据，不复制其记录 |
| `MICROSOFT-POWERBI-CUSTOMER-PROFITABILITY` | Microsoft Learn 官方教程 | 支持收入、预算、客户利润和报表/Excel 导出作为经营分析语义 | 样例由第三方制作，不代表本项目客户或生产数据 |
| `MICROSOFT-POWERBI-SAMPLE-DATASETS` | Microsoft Learn 官方样例总览 | 支持可下载、可检查的演示文件和数据性质/归属留痕 | 不直接提交公开工作簿，不把样例写成企业事实 |
| `MICROSOFT-DYNAMICS-SAMPLE-DATA` | Microsoft Learn 官方文档 | 支持 CRM 销售实体、记录状态和演示/生产隔离边界 | 不代表真实 Dynamics Connector 或生产身份 |

精确链接、访问日期、支持范围和局限见 [`ENTERPRISE-DEMO-DATA-RESEARCH-20260820`](../research/ENTERPRISE-DEMO-DATA-RESEARCH-20260820.md)。

## 3. 决策

采用仓库内 `demo-enterprise-data/customer-a/` 的项目生成仿真文件包。`manifest.json` 是唯一 allowlist，文件使用相对路径和 SHA-256；`DemoSourceCatalog` 只使用声明的结构化解析器。当前四个稳定 `fixture:` 引用保留为服务端控制和审计用 opaque ID，不进入普通业务 DOM。

数据链路固定为：

```text
仿真文件
  -> manifest allowlist / relative-path / size / symlink / SHA-256
  -> CSV/JSON/EML 结构化解析
  -> TaskSourceDocument + TaskSourceFact
  -> TaskSnapshot.source_documents 冻结
  -> ConflictOperationContext + ConflictRecord
  -> 前台文件证据卡与影响预演
```

当前 Demo 1 冲突语义为：财务历史关账文件中的 `recognized_revenue=2400 万元` 与销售预测文件中的 `forecast_revenue=2680 万元` 都是合法记录，但当前经营汇报操作试图把预测字段当作已实现收入。Agent 不自动覆盖已关账口径，而是把操作字段、尝试值、历史文件和推荐的正式来源一并交给用户决定。

不采用直接接入真实 CRM/邮箱/数据库，也不把 Microsoft 样例文件直接提交到仓库。该决策不扩大到真实 Connector、实时数据库、真实 Lenovo 数据或生产客户身份。

## 4. 后端事实与状态语义

- `TaskSnapshot.source_documents[]` 是创建时冻结的服务端来源快照，包含 `document_id/display_name/relative_path/system_label/semantic_type/record_status/recorded_at/owner_role/content_digest/facts[]`。
- `ConflictRecord.operation_context` 是当前业务操作事实，包含 `operation_label/target_field/attempted_value/attempted_source_field/mismatch_reason`。
- `source_refs[]` 仍用于服务端契约、控制校验和审计；`source_documents[]` 提供可解释文件事实；前台只投影后者的安全业务字段。
- 创建 Demo 1、start、advance、resolve 前应校验来源快照仍符合任务契约；文件变化时拒绝继续，不能产生猜测 Artifact、Verification 或 Commit。
- `TaskCommit.state_hash` 必须覆盖来源快照摘要或 digest，保证完成证据与所依据的文件版本绑定。
- `TASK_CREATED` 记录来源文档 digest；已有旧 Snapshot 缺少 `source_documents` 时只允许兼容读取，不能把缺失字段补成文件事实。

## 5. 前台交互影响

Conflict Card 不再只展示“演示数据 · CRM 正式收入记录”，而展示：文件显示名、相对演示目录、系统标签、记录时间、责任角色、记录状态、字段名和业务值。卡片同时显示“当前操作正在尝试写入什么字段/值”，并用 before → attempted/after 行解释冲突。

用户可以展开文件证据、查看相关工件、接受服务端批准的正式口径或补充依据。提交前仍只显示 `expected_impact`；只有新 Snapshot/`ControlEvent.impact_receipt` 返回后，才显示实际变化。文件读取失败、哈希变化或来源投影缺失时，前台显示“演示资料待核验/请开始新一轮任务”，不隐藏为成功，也不使用旧金额回退。

默认隐藏原始 `fixture:` ID、绝对本机路径、完整哈希、Prompt、思维链、解析日志、密钥和无决策价值的底层 Trace。文件内容只显示服务端 allowlist 解析出的业务字段，不渲染任意原始文件正文。

## 6. 验证与边界

本决策的实现证据已按限定工程范围封口：

- [x] `DemoSourceCatalog` 单元测试：manifest、路径、大小、符号链接、哈希和结构化解析异常。
- [x] Task Runtime 回归：来源快照、操作上下文、文件变化 fail closed 和 state hash 绑定。
- [x] API/TypeScript 协议同步与未知字段/路径/内部 ID 的 DOM fail-closed 回归。
- [x] 浏览器 E2E：文件证据卡、字段差异、桌面/移动布局和截图 hash。
- [x] 运行记录：Python `166 passed, 1 skipped`、浏览器 `38 passed`，Ruff、前端 lint/build 和 diff-check 通过。
- [x] Evidence 已绑定实现 `5b07702`、[PR #21](https://github.com/Dickey007s/lenovo_agent/pull/21)、测试数字与截图。

该决策仍不得表述为真实企业数据接入或已验证用户价值；只能表述为“文件驱动的项目生成仿真 Demo 1 纵切”。详细证据见 [`DEMO1-FILE-BACKED-SOURCES-20260820`](../evidence/DEMO1-FILE-BACKED-SOURCES-EVIDENCE-20260820.md)。
