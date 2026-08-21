# 企业演示资料研究：结构借鉴与仿真文件边界

| 字段 | 内容 |
| --- | --- |
| Research ID | `ENTERPRISE-DEMO-DATA-RESEARCH-20260820` |
| 状态 | Ready（研究登记）；不等于真实企业数据接入 |
| 目的 | 为 Demo 1 的文件形态、字段语义、历史记录与当前操作冲突提供可追溯的公开依据 |
| 使用范围 | 只借鉴公开样例的结构、角色和业务语义；仓库中的文件由项目生成，不能表述为 Lenovo、客户或生产数据 |

## 公开依据

| Source ID | 类型与精确引用 | 支持的判断 | 局限与本项目取舍 |
| --- | --- | --- | --- |
| `MICROSOFT-ADVENTUREWORKS-SCHEMA` | 官方源码与 README：[microsoft/sql-server-samples AdventureWorks](https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/adventure-works)；README 说明 AdventureWorks 是 OLTP 样例，AdventureWorksDW 是数据仓库样例。访问：2026-08-20 | 企业销售、客户、订单、产品和分析数据通常由多类实体和版本化记录组成，适合借鉴客户标识、期间、记录状态等字段形态 | Microsoft 样例数据库；不代表本项目客户、不作为运行时输入；其数据被明确作为样例/虚构内容，本项目不复制数据库记录或备份 |
| `MICROSOFT-POWERBI-CUSTOMER-PROFITABILITY` | 官方教程：[Customer Profitability sample for Power BI](https://learn.microsoft.com/en-us/power-bi/create-reports/sample-customer-profitability)；页面说明样例包含 dashboard、report、semantic model，关注业务单元、产品、客户、收入、预算和利润，并提供 PBIX/Excel 形式。访问：2026-08-20 | 经营汇报应把客户、收入、预算/预测、利润或差异作为可解释的业务字段，而不是只显示一段模型文本；Excel/报表导出是合理的演示文件形态 | 页面说明该样例由 obviEnce 制作并提供匿名/行业样例语境；不能当作 Lenovo 或当前客户事实；本项目只借鉴字段语义，不打包其工作簿 |
| `MICROSOFT-POWERBI-SAMPLE-DATASETS` | 官方样例总览：[What are Power BI samples](https://learn.microsoft.com/en-us/power-bi/create-reports/sample-datasets)；页面说明可下载 PBIX、XLSX、SQL 样例并要求遵守样例数据归属和使用说明。访问：2026-08-20 | 演示资料可采用可检查的文件、工作簿和数据库导出，而不是不可追溯的代码常量；数据性质、来源和使用限制应登记 | 官方页面明确样例仅用于演示 Power BI 功能，工作簿及数据有归属/免责声明；本项目不把公开样例复制进企业事实链，也不宣称取得生产授权 |
| `MICROSOFT-DYNAMICS-SAMPLE-DATA` | 官方文档：[Add or remove sample data](https://learn.microsoft.com/en-us/power-platform/admin/add-remove-sample-data)；文档说明 Dynamics 365/Power Platform 可安装样例数据用于学习且不要与生产数据关联；销售样例的记录类型见 [Explore the sales accelerator with sample data](https://learn.microsoft.com/en-us/dynamics365/sales/manage-sample-data)。访问：2026-08-20 | CRM/销售场景可以包含 account、contact、opportunity、product、price list 等具备所有者和状态的记录；演示环境应与生产数据隔离 | 这是产品样例数据使用说明，不是本项目的真实 CRM Connector，也不能证明当前场景有 Dynamics 数据；本项目只借鉴实体/状态语义 |

## 研究结论

1. Demo 1 应从“代码常量之间的冲突”改为“允许目录中的历史文件快照与当前业务操作之间的冲突”。
2. 文件形态优先采用 CSV/JSON/EML 等可审阅的企业导出与归档文件；是否使用 XLSX 不应成为真实性的唯一标准。
3. 每个文件必须有 manifest allowlist、相对路径、解析器、记录时间、责任角色、语义类型和 SHA-256；解析后的业务事实才可进入 Task Runtime。
4. 公开依据只支持结构和业务语义。仓库文件必须标记 `project_generated_simulation`，不能写作“真实企业数据库”“真实 CRM”或 Lenovo 数据。
5. 历史文件事实和本轮当前操作必须分开建模。Conflict 应同时说明目标字段、当前尝试写入的值、当前操作使用的字段，以及为什么不能自动覆盖历史口径。

## 选型与未采用方案

- 采用：小型、可读、可哈希的仿真文件包，保留四份 Demo 1 来源的跨系统角色和时间差。
- 不采用：直接下载并提交 AdventureWorks/Power BI 大型数据库或工作簿；这会扩大版权、体积和语义错配风险，也无法证明与 Lenovo 业务相同。
- 不采用：连接真实 CRM、邮箱或数据库；当前身份、权限、Connector、副作用和恢复证据均不足以支持该结论。
