# Demo 1 分支控制与不可变成果历史 Evidence

> 状态：`Limited Verified`。本文件证明固定 FORTE、最多三轮、顺序单
> Controller、只读成果路径中的分支级继续、独立 append-only 成果记录与受控恢复。
> 它不证明并行 Worker、真实文件写回、多实例高可用、模型结论正确或用户价值。

## 1. 本轮主张

本轮把 Demo 1 从“整组补证、Snapshot 内版本”推进到两个可检查的服务端事实：

1. validated plan unit 会被编译为稳定 Branch。多条分支缺证时，用户可选择其中一条
   继续；下一轮只获得该分支的缺失引用，其他分支继续等待。
2. 每轮完整只读简报写入独立 append-only ArtifactVersion；最终提交或恢复只新增
   TaskCommit 并移动当前指针，不修改或删除历史 ArtifactVersion。

`rollback` 在产品文案中称“恢复历史成果版本”。它只恢复逻辑简报当前指针，FORTE
原始文件始终只读。Branch 也只是单任务内部工作单元，不等于 Demo 2 的多任务
Scheduler/Worker。

## 2. 实现位置

| 事实 | 实现 |
| --- | --- |
| Branch、ArtifactVersion、TaskCommit、rollback 契约 | `packages/contracts/harness_models.py` |
| 分支编译、分支 Gate、选择性 resume、Commit/恢复 | `services/api/app/application/harness_runtime.py` |
| memory/PostgreSQL append-only 独立记录 | `services/api/app/application/harness_storage.py` |
| 任务分支现场与不可变成果历史 | `apps/web/app/harness-workbench.tsx`、`apps/web/app/styles.css` |
| 分支/版本/幂等单元回归 | `tests/unit/test_harness_runtime.py` |
| 真实 PostgreSQL 顺序 Runtime 集成门 | `tests/integration/test_postgres_agent_control_loop.py`、`.github/workflows/postgres-restart.yml` |
| 前台分支选择与恢复回归 | `apps/web/e2e/harness-workbench.spec.ts` |

## 3. 自动化观测

| 检查 | 结果 | 能证明什么 | 不能证明什么 |
| --- | --- | --- | --- |
| `uv run pytest -q` | `63 passed, 1 skipped in 16.84s` | Python 合同、Catalog、Runtime、Store 与无数据库环境的显式 skip | 真实 PostgreSQL 服务和模型质量 |
| Runtime 聚焦 | `26 passed in 1.30s` | 两等待分支逐条继续、独立版本/Commit、恢复、幂等回放、memory 原子冲突回滚和未完成 Branch 清理 | 并发 Worker、多实例竞争 |
| `uv run ruff check .` | 通过 | Python 静态检查通过 | 运行可靠性 |
| `pnpm --dir apps/web lint` | 通过 | TypeScript 类型检查通过 | 浏览器行为与用户理解 |
| `pnpm --dir apps/web build` | 通过 | Next.js 生产构建成功 | 生产部署 |
| Harness Playwright | `13 passed in 30.3s` | 分支现场、指定分支继续、成果恢复、文件预览、SSE、390px 路径 | 真实用户理解、真实模型或数据库调用 |
| PR PostgreSQL integration | PostgreSQL 17.11，`1 passed in 1.84s` | 四个顺序 Runtime 的中断、显式恢复、独立记录、rollback 与再次启动读取 | 并发实例、lease、数据库高可用或在途 HTTP 续跑 |

本地没有 PostgreSQL 服务，所以本地全量中的集成测试按 `TEST_DATABASE_DSN` 显式跳过；
这项 skip 不是通过。真实数据库证据来自 PR #31 的
[GitHub Actions job](https://github.com/Dickey007s/lenovo_agent/actions/runs/32926860106/job/98051424823)，
服务端实际报告 PostgreSQL `17.11`，绑定实现提交 `95ab752`。

## 4. 分支级事实

定向 Runtime 回归构造两个 `waiting_input` Branch：

- 用户先选择缺少 `REF_THREE` 的分支，下一轮输入严格等于 `REF_THREE`；
- 另一条缺少 `REF_TWO` 的分支仍为 `waiting_input`，没有被静默消耗；
- 下一次用户再选择该分支，ControlEvent 与 `active_branch_id` 均指向服务端 Branch；
- 如果进程中断发生在分析中，恢复会同时移除未完成 Round 及其 Branch，不留下孤立任务卡；
- Branch ID、状态、缺失引用和依赖由服务端产生，模型与浏览器都不能自行写入。

![分支级 Evidence Gate：完成分支保留，缺证分支由人选择继续](screenshots/dr-0026-branch-control.png)

该图来自确定性 Playwright fixture，用于证明 DOM、动作和服务端字段映射，不是一次真实
模型运行截图。PNG `18165` bytes，SHA-256
`77847E567A61C5973B828B25DD303AE8D4C0D8E7463138EEF7501FBFE85F7F85`。

## 5. 成果版本与恢复事实

定向 Store/Runtime 回归依次形成两个独立 ArtifactVersion 和一个初始 TaskCommit，随后：

1. 恢复 v1，新增 `operation=rollback` 的 TaskCommit；
2. 用相同幂等键重放，版本与 Commit 数量不增加；
3. 用新命令恢复 v2，再新增一条 TaskCommit；
4. 两个 ArtifactVersion 均仍存在，payload digest 不变；
5. Snapshot 的 `last_commit` 只是当前指针，恢复不会改写 FORTE 源文件。

![恢复 v1 后仍保留 v2 与全部提交记录](screenshots/dr-0026-artifact-restore.png)

该图同样来自确定性 Playwright fixture。PNG `13926` bytes，SHA-256
`0264CAB3EBA609EC10EDEE87758EEE345A36C6C152A8E6610E5C190344038CAD`。

## 6. PostgreSQL 重启门

集成测试使用同一真实 PostgreSQL 数据库上的四个顺序 Runtime：

1. 第一个 Runtime 在模型调用中断；
2. 第二个恢复最后完成检查点、显式 resume 并提交；
3. 第三个重新读取独立 ArtifactVersion/TaskCommit，并恢复历史版本；
4. 第四个再次启动，核对恢复后的当前 Commit 指针与全部历史记录。

该门已在 PR #31 通过：`1 passed in 1.84s`。它验证进程间持久化与 append-only 语义，
不验证同时运行的多个实例、lease、通知、远端 HTTP 硬取消或数据库高可用。

## 7. 前台事实与隐藏边界

- “任务分支现场”来自 `snapshot.branches[]`，不是浏览器重新解释模型 plan。
- “继续此分支”只有收到带 `branch_id` 的 resume 回执后才算发生。
- “当前 vN”来自 `last_commit.artifact_version`；版本卡来自独立 ArtifactVersion 投影。
- “已恢复历史成果版本”来自 `artifact_version_restored` 与 rollback TaskCommit。
- 普通 UI 隐藏内部 Branch 生成、完整 digest、数据库行、Prompt、思维链、raw provider
  response 和内部工具/策略标识。
- `completed` 仍只证明 schema、引用范围、只读边界和 Branch/Artifact 记录校验通过，
  不证明语义、穷举、算术、源文件写入或外部动作正确。

## 8. 绑定

- 工作分支：`codex/demo1-branch-artifact-control-20260826`
- Decision：[`DR-0026`](../decisions/DR-0026-selective-branch-and-immutable-artifact-history.md)
- Scenario：[`SCENARIO-012`](../scenarios/SCENARIO-012-selective-branch-and-artifact-restore.md)
- Source：[`USER-FEEDBACK-20260826-20`](../sources/USER-FEEDBACK-20260826-20-demo1-branch-artifact-completion.md)
- 实现提交：`95ab752`（`feat: add branch-level control and immutable result history`）
- Pull Request：[#31 Demo 1：分支级继续与不可变成果历史](https://github.com/Dickey007s/lenovo_agent/pull/31)
- PostgreSQL workflow：[run `32926860106` / job `98051424823`](https://github.com/Dickey007s/lenovo_agent/actions/runs/32926860106/job/98051424823)，PostgreSQL 17.11，`1 passed in 1.84s`
