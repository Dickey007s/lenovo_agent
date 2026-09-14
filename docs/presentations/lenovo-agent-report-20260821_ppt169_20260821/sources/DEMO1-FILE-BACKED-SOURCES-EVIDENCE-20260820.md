# Demo 1 文件驱动来源证据

| 字段 | 内容 |
| --- | --- |
| Evidence ID | `DEMO1-FILE-BACKED-SOURCES-20260820` |
| Decision | [`DR-0014`](../decisions/DR-0014-file-backed-demo1-sources.md) |
| Status | `Verified`（限定工程范围） |
| Scope | `demo-enterprise-data/customer-a`、manifest、来源快照、操作上下文、Conflict 文件证据卡 |
| Implementation | `5b07702`；[PR #21](https://github.com/Dickey007s/lenovo_agent/pull/21)（堆叠于 PR #20） |

## 验证问题

1. 仓库中的四份仿真文件是否能被 manifest allowlist 和 SHA-256 完整校验？
2. Task 创建后，`TaskSnapshot.source_documents[]` 是否冻结了文件元数据、字段事实和 digest？
3. 当前收入操作与历史关账/当前预测文件的口径冲突是否由服务端 `ConflictOperationContext` 产生？
4. 文件缺失、哈希变化、路径越界和解析失败时，是否不产生猜测 Artifact、Verification 或 Commit？
5. 前台是否展示文件名、相对路径、系统、记录时间、字段值和操作差异，同时不把 `fixture:` ID、绝对路径和内部日志带入 DOM？

## 证据登记表

| 证据 | 命令/路径 | 结果 | 说明 |
| --- | --- | --- | --- |
| 仿真文件清单 | `demo-enterprise-data/customer-a/manifest.json` | 通过 | manifest 与四份业务文件的字节数/SHA-256 见下表；`.gitattributes` 固定 LF，避免 Windows checkout 改变摘要 |
| 来源目录与 HTTP fail-closed | `tests/unit/test_demo_source_catalog.py`、`tests/integration/test_task_routes.py` | 通过 | 覆盖缺失文件、哈希变化、路径越界、非法语义、NaN/Infinity/负数/小数金额与 API `503` |
| Task Runtime 回归 | `tests/integration/test_task_file_sources.py`、`tests/integration/test_task_runtime.py` | 通过 | 四份来源冻结进 Snapshot；冲突字段来自文件；运行期间文件变化保持 v1/ready；state hash 绑定来源快照 |
| API/协议检查 | `packages/contracts/task_models.py`、`apps/web/app/task-types.ts`、API 响应 | 通过 | Python/TypeScript 同步 `source_documents` 与 `operation_context`；创建响应返回四个相对路径 |
| 前台桌面 | 完整 Playwright 与 [`dr-0014-demo1-file-backed-conflict-1440.png`](screenshots/dr-0014-demo1-file-backed-conflict-1440.png) | 通过 | `1440 x 900`，167389 bytes，SHA-256 `712388429270750371EBBF7C30C39145BE88A85177400B88614AD3C6B29A5AD0` |
| 前台移动 | 完整 Playwright 与 [`dr-0014-demo1-file-backed-conflict-mobile-390.png`](screenshots/dr-0014-demo1-file-backed-conflict-mobile-390.png) | 通过 | `390 x 844`，50582 bytes，SHA-256 `1F6C8C0ACC5DF06DCE360D09E8F88DB34E00B4A1B4A6395FB25FD5C4C869CB6B`；页面级关键容器无横向溢出 |
| 全量质量门槛 | `uv run pytest -q`、`uv run ruff check .`、`pnpm --dir apps/web lint`、`pnpm --dir apps/web build`、完整 Playwright | 通过 | Python `166 passed, 1 skipped (6.17s)`；浏览器 `38 passed (2.3m)`；聚焦主路径 `1 passed (22.8s)`；Ruff、TypeScript lint、Next production build、diff-check 通过 |

## 文件清单与摘要

| 相对路径 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `manifest.json` | 3240 | `BCCE84CE6F23FDD828AEBEDA26774D3A989810390156219D43071F3EE1948E15` |
| `crm/customer-a-revenue-close-v3.csv` | 284 | `D49D186D9BCBA18891EB8A26DD646FABB3F948ECF65FCFF247D846B0BE1459FB` |
| `forecast/customer-a-revenue-forecast-v2.csv` | 289 | `A69E47AB1BC181D492048ACA0CFC93C5E0C26F8D8A1C47DC44FFF2AE154EB268` |
| `mail/customer-a-status-request-2026-06-15.eml` | 596 | `0F0DA46C204F82EB3155660D4A0839227D4DBEF5258CC145BC1C19783AA8C5F2` |
| `project/customer-a-weekly-status-v5.json` | 382 | `0B91166767F5AECD45492813FF39FBAFD5B0311F546D8BF0A83FC457BBBDF9CD` |

## 不可夸大边界

- 这些文件是 `project_generated_simulation`，不是 Lenovo、真实客户或真实企业数据库文件。
- Microsoft AdventureWorks、Power BI 和 Dynamics 文档只提供公开结构/业务语义依据，不是本项目运行时来源。
- 当前没有真实 CRM、邮箱、ERP、数据库或外部 Connector 读取；文件读取由本地 allowlist catalog 完成。
- 自动化和截图不证明文件冲突交互改善了用户理解、效率或决策质量。

## 结论

限定工程范围内，Demo 1 已从“代码常量产生冲突”升级为“仓库仿真文件经完整性校验和结构化解析后产生可追溯冲突”。该结论不外推到真实企业数据、真实 Connector、生产正确性或用户价值。
