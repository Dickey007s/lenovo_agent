# Demo 2 路由影响预演与服务端选择回执工程证据

| 字段 | 内容 |
| --- | --- |
| Evidence ID | `DEMO2-ROUTE-IMPACT-EVIDENCE-20260820` |
| Decision | [`DR-0011`](../decisions/DR-0011-demo2-route-impact.md) |
| Scenario | [`SCENARIO-002`](../scenarios/SCENARIO-002-demo2-explainable-admission.md) |
| Status | `Verified`（限定工程范围） |
| Scope | 固定 Demo 2 客户 A 的服务端路由影响预览、跨区域即时影响地图、选择回执、刷新恢复和未执行边界 |

## 1. 待证明的工程事实

- 每个 `RouteProfile` 的工作组织影响来自服务端 `impact_preview`，前端不根据模式名称补造任务分配、人工介入或外部动作语义。
- 用户切换允许模式时，左侧影响地图同步变化，右侧保留推荐、选择与主操作；确认前不提交服务端 mutation。
- 服务端应用选择后产生独立 `RouteSelectionReceipt`，记录 cockpit/item 版本前后、选择来源、范围、规则预测与实际记录变化。
- 预演与回执都明确 `not_started → not_started` 和 `external_side_effect=none`；选择 Adaptive Swarm 不等于创建协作单元或访问真实业务系统。
- 回执进入 `WorkItemSnapshot`、连续历史和幂等结果，同一 API 进程内 GET、页面刷新和相同 key 重放能恢复同一事实；同模式重复和缺路由事实均 409 且不增加版本，409 保留本地选择且不显示成功回执。

## 2. 当前运行记录

| 验证项 | 命令或证据 | 当前结果 |
| --- | --- | --- |
| Demo 2 协议与服务聚焦测试 | `uv run pytest -q tests/unit/test_demo2_models.py tests/integration/test_demo2_cockpit.py` | `11 passed (1.53s)` |
| 聚焦 Ruff | `uv run ruff check packages/contracts/demo2_models.py packages/contracts/__init__.py services/api/app/application/demo2_cockpit.py tests/unit/test_demo2_models.py tests/integration/test_demo2_cockpit.py` | passed |
| Demo 2 浏览器 | `corepack.cmd pnpm --dir apps/web test:e2e --grep "Demo 2"` | `5 passed (15.8s)` |
| Python 全量 | `uv run pytest -q` | `144 passed, 1 skipped (3.60s)` |
| Browser E2E 全量 | `corepack.cmd pnpm --dir apps/web test:e2e` | `35 passed (2.2m)` |
| Ruff / Frontend lint / build | `uv run ruff check .`；`corepack.cmd pnpm --dir apps/web lint`；`corepack.cmd pnpm --dir apps/web build` | passed |
| Governance / diff check | `uv run pytest -q tests/unit/test_reporting_governance.py`；`git diff --check` | passed |

聚焦浏览器验证了：服务端队列与预览、Fixed Workflow 切换时左侧影响地图即时变化、桌面确认按钮位于视口且未被遮挡、确认 body、服务端回执、页面刷新恢复、再次改选预演、409 草稿保留、390px 无页面横向溢出与可见操作目标至少 44px。移动端默认收起推荐依据和完整路线比较，需要时再展开，以优先保留影响预演与主操作。自动化不证明真实用户理解或路线优劣。

## 3. 视觉证据

| 文件 | 尺寸 / 字节 | SHA-256 | 说明 |
| --- | --- | --- | --- |
| [`demo2-route-impact-preview-desktop.png`](screenshots/demo2-route-impact-preview-desktop.png) | `1280 x 720` / 162721 bytes | `8283F5E490C127E104DA55821D0DC5D7C494730B427E4EF1018EE108EBFBCEEA` | 桌面选择前：右侧模式选择驱动左侧工作组织影响地图；主操作在首屏可见 |
| [`demo2-route-selection-receipt-desktop.png`](screenshots/demo2-route-selection-receipt-desktop.png) | `1280 x 720` / 143552 bytes | `C5122661F1FDC0DE40BE5BB0CD574EBF096E74ACD0222AD7DBC7DBB2E8589412` | 桌面选择后：左侧“选择后的影响”与右侧唯一权威回执，仍未执行 |
| [`demo2-route-impact-preview-mobile.png`](screenshots/demo2-route-impact-preview-mobile.png) | `390 x 2667` / 165923 bytes | `C2493ED372576A933739518328D149D68C8E84C1F247F0227499C8BFCD7C7004` | 390px 自然纵向影响地图、首要确认动作与可展开支持细节 |

截图使用固定演示数据，不包含真实客户、真实 Connector、真实 Worker、Key 或生产凭据。它们是运行和视觉证据，不是用户研究。

## 4. 协议与事实断言

| 事实 | 证据 |
| --- | --- |
| 旧 Snapshot 兼容 | `impact_preview` 与 receipt 缺失时仍可读取；只有 latest receipt 的旧快照会归一化为一条历史 |
| 影响由服务端拥有 | 所有路由 profile 返回至少六项业务影响；前端只投影 `changes[]` |
| 推荐与覆盖可区分 | 推荐模式回执为 `selection_source=admission`；其他允许模式为 `user_override + this_run` |
| 选择不是执行 | preview 与 receipt 都固定 `execution_status_before/after=not_started`、`external_side_effect=none` |
| 回执可恢复 | mutation 后 GET 返回同一 receipt；相同幂等 key 重放不新增版本或回执 |
| 历史连续且无假变化 | 再次改选保存真实上一模式并连续追加；同一模式用新 key 重复确认返回 409、版本不变 |
| 缺事实 fail-closed | 缺 route profile 或 impact preview 时返回 409，cockpit/item 版本均不增加 |
| 冲突不伪成功 | stale version 和非法模式不生成 receipt；浏览器保留草稿并重新读取 |

## 5. 当前边界

本证据不支持“Adaptive Swarm 已启动”“动态创建了多个 Agent/Worker”“真实连接邮件/CRM”“降低成本或缩短时延”“用户已经理解或更信任系统”等结论。`forecast` 是固定演示策略预测；服务端仍为单进程 memory，没有 Demo 2 SSE、PostgreSQL Store、Shared Artifact Workspace、Verifier、执行循环或跨进程恢复。

## 6. 交付封口

- 实现提交：`db461ec`
- PR：[#17](https://github.com/Dickey007s/lenovo_agent/pull/17)
- 完整回归：Python `144 passed, 1 skipped`；Browser `35 passed`；Ruff、frontend lint/build、governance 与 diff-check 均通过
- 用户研究：未运行；至少 5 人无引导形成性测试留待后续
