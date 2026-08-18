# Demo 1 来源与新一轮语义修订证据（2026-08-11）

| 字段 | 内容 |
| --- | --- |
| 状态 | 工程范围 `Verified`；用户理解结论仍为 `Draft` |
| 触发来源 | `USER-FEEDBACK-20260811-ROUND-AND-SOURCE-03`；原图 [`user-feedback-20260811-source-and-new-round-ambiguity.png`](assets/user-feedback-20260811-source-and-new-round-ambiguity.png)，SHA-256 `D72498921E712117E82A827B015EBDBAE374F284EBD7CAEA2E7851DCA256B613` |
| 决策 | `DR-0004`、`DR-0005` |
| 场景 | 用户在邮件工作区看到后台经营汇报，或在终态开始下一轮 |
| 不证明 | 目标用户已理解、真实 Connector、历史轮次选择、通用后台 Agent Loop |

## 1. 验证问题

1. 非 Tasks 工作区是否只显示后台任务摘要和前往 Tasks 的入口，而不复刻冲突决定与分支控制？
2. 固定 Demo 1 来源是否明确标为演示数据，且原始 `fixture:` / 未知内部标识不进入普通业务 DOM？
3. 终态“开始新一轮汇报”是否创建独立 Task 并立即启动，旧 Task 仍保留？

## 2. 前台输出与服务端事实

| 前台输出 | 服务端或客户端事实 | 验证边界 |
| --- | --- | --- |
| Mail 中的“后台任务”摘要、当前状态、处理阶段和“前往处理” | 同一 `TaskSnapshot.contract/status/phase`；按钮只切换 `activeView=tasks` | 不产生 Task Control，不宣告后台进度 |
| “演示数据 · CRM 正式收入记录（v3）”等来源标签 | 服务端仍保留 `source_refs[]`；客户端固定 allowlist 投影标签并使用序号 DOM key | 原始 ID 不进入普通业务 DOM；不是服务端数据删除或真实 Connector |
| “开始新一轮汇报” | 新 round key 调用 create，随后以新 Task Snapshot 调用 start | 不是 reset/reopen 旧 Task；固定路径启动后通常进入 `waiting_input / verify` |
| 上一轮记录保留 | `GET /v1/tasks` 同时包含新旧 Task，旧 Task/Artifact/Event/Commit 不 mutation | 当前没有历史轮次选择入口 |

## 3. 自动化结果

完整浏览器 E2E 命令：

```powershell
corepack.cmd pnpm --dir apps/web exec playwright test
```

结果：`12 passed (44.5s)`。

覆盖本轮问题的断言包括：

- 切到 Mail 后不存在 `.task-runtime-panel`，只显示当前经营汇报摘要和“前往处理”；无 Task 时按 loading、connecting、reconnecting、synced 区分读取/连接/恢复/可开始事实，不提前宣告“没有任务”。点击“前往处理”后回到 Tasks，并把焦点移到待确认标题。
- 冲突卡的折叠标题为“查看演示数据来源”；E2E 实际展开后断言两条演示标签可见。已知来源投影带“演示数据”前缀，页面不包含 `fixture:`；未知 URL、路径、凭据形态和内部标识继续 fail closed。
- 终态点击“开始新一轮汇报”后 create/start 各按幂等语义执行；E2E 断言新一轮只产生 1 次 start，新 Task 进入 `waiting_input`，上一轮仍为 committed 且保留 7 个 ArtifactVersion。

自动化证明指定 DOM 与服务端事实和调用序列一致，不证明真人无需解释就能理解这些语义。

同一最终代码状态的其他封口结果：

- `uv run pytest -q`：`58 passed, 1 skipped (3.08s)`；skip 仍是未配置 opt-in PostgreSQL 维护库 DSN。
- `uv run ruff check .`：通过。
- `pnpm --dir apps/web lint`：通过。
- `pnpm --dir apps/web build`：通过。

## 4. 截图证据

| 文件 | 尺寸 | 字节 | SHA-256 | 证明范围 |
| --- | ---: | ---: | --- | --- |
| [`dr-0005-mail-background-task-1440.png`](screenshots/dr-0005-mail-background-task-1440.png) | `1440 x 900` | `120695` | `AF701F7E12AE5AFFCD2A24D41556487EEEFCE7026870AEFEC790711620DE6EFF` | Mail 只显示后台汇报摘要、状态、阶段和“前往处理”，没有冲突卡或分支控制 |

截图不证明按钮调用、新旧 Task 持久语义、DOM 中没有隐藏原始 ID，亦不证明用户理解；这些分别依赖自动化、服务端列表断言和后续无引导研究。

## 5. 当前边界

- 历史 PR 6 evidence 保持原样；本文件只记录后续反馈触发的修订。
- `DR-0005` 继续为 `Draft`。至少 5 名接近目标角色参与者的无引导形成性测试尚未运行。
- 服务端保留多个 Task，但前端尚无历史轮次选择器；“旧轮次保留”不能写成“用户可自由切换历史轮次”。
- 固定 Demo 1 的金额、邮件、CRM、预测表和项目周报仍是演示数据，不是真实企业记录。
