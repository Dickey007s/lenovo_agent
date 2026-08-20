# Demo 1 Agent 影响预演与变化回执证据

| 字段 | 内容 |
| --- | --- |
| Evidence ID | `DEMO1-AGENT-IMPACT-PREVIEW-20260820` |
| Decision | [`DR-0010`](../decisions/DR-0010-visible-agent-impact.md) |
| Scenario | [`SCENARIO-001`](../scenarios/SCENARIO-001-customer-a-durable-report.md) |
| Status | `Verified`（限定工程范围） |
| Implementation | `258861f` |
| Pull request | [#16](https://github.com/Dickey007s/lenovo_agent/pull/16) |

## 1. 待证明的工程事实

- 固定收入口径冲突由服务端提供唯一可执行 `resolution_option_id` 和结构化预期影响；普通 UI 不推断来源角色或结果。
- 提交前 Decision Inbox 展示经营分析、客户回复草稿、风险页与外部发送的逐项 `before → after`。
- 服务端应用决定后，`ControlEvent.impact_receipt` 记录实际新增工件版本、验证记录、Commit、任务版本和外部副作用边界。
- 完成态回执只由实际 receipt 触发；刷新 Snapshot 后仍可恢复，不用 Toast 或动画代替服务端事实。
- 客户回复仍为草稿且未发送；任何后续发送仍进入受治理 Action 链路。

## 2. 当前运行记录

| 验证项 | 命令或证据 | 当前结果 |
| --- | --- | --- |
| 协议与 Task Runtime 聚焦测试 | `uv run pytest -q tests/unit/test_task_contracts.py tests/integration/test_task_runtime.py` | `17 passed (0.46s)` |
| 聚焦 Ruff | `uv run ruff check packages/contracts/task_models.py services/api/app/application/tasks.py tests/unit/test_task_contracts.py tests/integration/test_task_runtime.py` | passed |
| Frontend lint | `corepack.cmd pnpm --dir apps/web lint` | passed |
| 浏览器主路径 | `corepack.cmd pnpm --dir apps/web test:e2e --grep "the first task path exposes"` | `1 passed (18.8s)` |
| Python 全量 | `uv run pytest -q` | `139 passed, 1 skipped (4.74s)` |
| Browser E2E 全量 | `corepack.cmd pnpm --dir apps/web test:e2e` | `35 passed (1.9m)` |
| 全量 Ruff | `uv run ruff check .` | passed |
| Frontend lint / build | `corepack.cmd pnpm --dir apps/web lint`；`corepack.cmd pnpm --dir apps/web build` | passed |
| Governance | `uv run pytest -q tests/unit/test_reporting_governance.py` | `4 passed (0.02s)` |
| Diff check | `git diff --check` | passed（仅 Windows 换行提示） |

## 3. 视觉证据

| 文件 | 尺寸 / 字节 | SHA-256 | 说明 |
| --- | --- | --- | --- |
| [`demo1-impact-preview-desktop.png`](screenshots/demo1-impact-preview-desktop.png) | `1487 x 1058` / `159354` | `DDB3ED0748DD8A790C8DE5A48ADA16DB171D8D0A9C75F01B9C38BC0D6BC18957` | 决定前：逐项影响预演、唯一主动作、外部发送边界 |
| [`demo1-impact-receipt-desktop.png`](screenshots/demo1-impact-receipt-desktop.png) | `1487 x 1058` / `162435` | `CD36144390D561993FB63F19D8DCA2A1961CFAF50C5AC9958E6175CA25A52749` | 决定后：实际变化回执、核对、保持项与未发送边界 |
| [`demo1-impact-preview-mobile.png`](screenshots/demo1-impact-preview-mobile.png) | `390 x 2712` / `142375` | `AD052FD5A93DB1E1601328CE5B32894F0E7E71718FBC65D0B2FA5DA3477A033C` | 移动端自然流、无横向溢出、关键动作不被遮挡 |

## 4. 当前边界

本证据只覆盖固定客户 A Fixture 的一个服务端批准选项。它不证明 Agent 对真实 Connector、副作用、非确定性工具或多个复杂选项的影响可以准确预演；也不证明用户理解、信任或决策质量已改善。`expected_impact` 是预期，`impact_receipt` 才是应用事实，两者不得混用。目标用户研究未运行，因此对外只能称为限定工程范围的交互与协议证据。
