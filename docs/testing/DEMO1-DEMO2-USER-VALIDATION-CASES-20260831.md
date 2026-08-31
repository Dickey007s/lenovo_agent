# Demo 1/2 用户试用与验收用例（2026-08-31）

固定正例、反例和失败注入合同见
[`DEMO1-DEMO2-FIXED-SCENARIO-GATES-20260831`](DEMO1-DEMO2-FIXED-SCENARIO-GATES-20260831.md)。
本文件保留用户自行操作步骤；固定场景门负责工程可重复性，两者不能相互替代。

## 先说清两种验证

1. **确定性工程验证**使用 Playwright mock API 和 Python Fixture，不调用付费 Provider。
   它最适合你先确认按钮、时间线、拓扑说明、Worker 回执、字号和移动端是否符合设计。
2. **真实本地试用**使用当前 Workspace 与已配置模型。Planner/Analyst 是非确定性的，未必
   每次都生成相同 Branch 或 adaptive route；它用于观察真实链路，不能替代固定自动化门。

两者都不能证明业务结果正确或用户体验已改善。源文件保持只读，成果写入隔离 Run
Workspace；不要为了制造 source revision 场景去手改 FORTE manifest 或 96 份公开输入。

## A. 最快可重复的 UI 用例

在仓库根目录运行：

```powershell
pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts --grep "Demo 1 shows a durable task timeline"
pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts --grep "Demo 2 requires confirmation"
```

### A1. Demo 1 预期画面

- 终态 Run 上出现“继续未完成任务”，并解释不能原地无限运行。
- 点击后请求 `/v1/harness/runs/{run_id}/continue`，body 只带被选 `branch_id`、
  `expected_version`、幂等键和可选新预算/指令，不带客户端猜测的文件范围。
- 页面切到“任务持续链 · Run 2”，显示同一 Task、新 Run、基线成果和本分支批准来源。
- parent 请求失败时仍保留旧 Run；只有收到合法 child Snapshot 后才重置 SSE 游标。
- 新增面板正文可读，桌面与 390 px 不产生页面级横向滚动。

### A2. Demo 2 预期画面

- 先显示“已准入受限只读 Workers”、路线理由、工作包/独立分支/来源/剩余预算事实。
- “确认并启动只读 Worker”之前没有 Worker 回执；点击后出现“实际 Worker 回执”。
- 第一波最多三个 Worker；依赖满足后才出现“继续下一批只读 Worker”。
- 页面显示“已合入/待核对/失败”而不是多个 Agent 聊天窗口；390 px 无页面级横向滚动。

## B. Python 合同与负向用例

```powershell
uv run pytest -q tests/unit/test_demo2_runtime.py
uv run pytest -q tests/integration/test_postgres_demo1_demo2.py
```

第二条只有设置真实 `TEST_DATABASE_DSN` 时才执行；没有 DSN 会显示 3 个 skip，这不是通过。

| ID | 要验证的事实 | 操作/Fixture | 预期结果 |
| --- | --- | --- | --- |
| D1-01 | 同 Task、新 Run、只续一条 Branch | terminal parent + 选择 waiting Branch | `task_id` 相同，`run_id` 改变，`run_sequence+1`，child refs 精确等于所选 Branch 范围 |
| D1-02 | 旧成果不可变 | 续办前后比较 parent Snapshot、Artifact/Commit digest | parent bytes/版本不变，child 只记录 base pointer |
| D1-03 | CAS/幂等/Owner | 重复 key、旧 version、其他 Owner | 重复 key 重放同一 child；旧 version 冲突且零新增；越权失败且不泄露对象 |
| D1-04 | 来源变化公开 | current Workspace revision 与 parent 不同 | public `source_revision_changed=true`，`recheck_file_refs` 精确，前台显示来源变化提示 |
| D1-05 | PostgreSQL restart | 配置 DSN 后创建 child、关闭 Runtime、重建 | lineage/幂等回执/成果指针一致，不自动重放中断模型调用 |
| D2-01 | 保守路线 | 单 Branch、同职能同结构、风险门、roots>3 或预算不足 | `single_controller`/`fixed_workflow`，不出现 Worker 执行事实 |
| D2-02 | adaptive 先确认 | 2–3 条跨职能独立 Branch，预算充足、只读 | admission 等待确认；确认前模型调用/Worker 数不增加 |
| D2-03 | 依赖波次 | 5 单元 DAG：3 roots + 2 dependents | 第一波最多 3；后两项只在依赖完成后 ready |
| D2-04 | partial failure | 2 adopted + 1 exception/ambiguous | adopted 贡献进入统一成果，问题 Branch 等待/失败，不清空其他成果 |
| D2-05 | 采用门 | 无 Anchor、越 Branch refs、叙事对账拒绝 | `output_used=false`，不进入 `SharedArtifactMerge` |
| D2-06 | 不静默截断 | Worker 返回 11 条合法 findings | Artifact/公共结果保留 11 条；协议治理上限为 96，不再固定只取 3 条 |
| D2-07 | restart 不重放 | 配置 DSN，保存 adopted receipt 或中断已预留 Worker | adopted 记录重启后保留；中断 Worker 不自动执行 |

## C. 在真实页面上自己试

启动：

```powershell
.\scripts\start-demo.ps1
```

打开 `http://localhost:3000`。先确认 `/v1/health` 中的 `checkpoint/task_store`：如果是
`memory`，进程重启后不恢复；只有页面与 health 明确显示 PostgreSQL 才测试跨进程恢复。

### C1. Demo 1：跨 Run 继续未完成工作线

建议输入：

> 核对三期资料中仍未确认的往来差异，保留已核对成果；如果证据不足，只暂停受影响的工作线，不修改源文件，也不执行外部动作。

1. 让 Run 正常推进到 `waiting_input`，或在已有成果后点击“结束并保留现有结果”。
2. 在终态/恢复区查看每条 Branch 的批准来源和缺口，选一条点击“继续未完成任务”。
3. 检查 child 时间线是否为 Run 2、是否只列该 Branch 的来源、旧成果是否仍可打开。
4. 不要只看最终文字；同时核对 `/v1/harness/runs/{run_id}` 的 `task_id`、
   `parent_run_id`、`carried_branch_id`、`recheck_file_refs` 和 Artifact/Commit 历史。

若没有 waiting Branch，页面不应为了 Demo 强行显示续办按钮；这说明本次真实计划没有触发
该路径，不是功能失败。请用 A/B 的固定 Fixture 验协议，再换任务观察真实 Planner。

### C2. Demo 2 正向：跨职能只读上线核对

建议输入：

> 分别核对算法研发、法务和质量保障目录中与发布准备有关的资料，形成一份统一的只读上线核对简报；说明各工作包依赖和缺口，不修改文件，不调用外部系统。

1. 查看路线说明是否来自实际 validated plan，而不是因为 Prompt 写了“多个 Agent”。
2. 若系统推荐 adaptive route，先确认此时还没有 Worker 回执，再点击确认。
3. 核对每个 Worker 的批准来源、`model_called`、`output_used`、耗时和 outcome。
4. 若一项失败，确认其他 adopted 项和旧 Artifact 仍在；不要把 partial 成果当作全部正确。

真实 Provider 可能保守地产生单 Branch 或同职能来源，从而选择 single/fixed route。前台应
如实解释，不应为了展示多 Worker 伪造并行。

### C3. Demo 2 反向：三期财务固定流程

建议输入：

> 核对三期往来明细，生成未付统计、未收统计和跨期核对说明，并判断是否存在僵尸账款；三期结果分别汇总到上述三个成果中，不修改源文件。

预期：同结构、同职能、顺序合并占主导时推荐 `fixed_workflow`。未付统计和未收统计各自
汇总三期，不是一时期一个成果；跨期核对说明解释口径与异常。路线卡应说明为什么没有
启动多个 Worker，而不是仅显示“未采用”。

## D. 你试用时记录什么

每次保留：任务输入、开始时间、Run/Task 时间线截图、所选 Branch、路线理由、实际 Worker
回执、下载成果、Evidence 回开位置、health task store 和失败/停顿后的恢复动作。业务内容
是否正确需人工对照源文件；自动化通过只能证明协议和被测交互状态。
