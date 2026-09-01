# Demo 1 / Demo 2 分层工作面验收门

- 日期：2026-09-01
- 状态：`Limited Verified`（工程范围）；形成性用户走查未运行
- 决策：`DR-0056`
- 场景：`SCENARIO-043`
- Evidence：[`DR-0056-DEMO1-DEMO2-SEPARATED-WORKSPACES-EVIDENCE-20260901`](../evidence/DR-0056-DEMO1-DEMO2-SEPARATED-WORKSPACES-EVIDENCE-20260901.md)
- 测试原则：所有前台状态必须来自公开 API/Snapshot；Fixture 不冒充真实 Provider；
  自动化不冒充用户研究

## 一、用户可直接试的用例

### TC-SEP-01：两条任务成为两个会话

1. 输入入职资产匹配表任务并运行。
2. 回到输入区，新建跨职能风险与待办简报任务并运行。
3. 打开“任务会话”。

预期：出现两个独立会话卡；标题分别来自两条 instruction；切换卡片时各自 Run、结果、
证据和状态恢复，不互相覆盖。刷新页面后仍能从服务端 recent Runs 找回，不依赖当前浏览器
tab 的临时状态。

### TC-SEP-02：同一 Task 的 Run 1 / Run 2 留在同一会话

1. 在入职资产任务的终态 Run 中选择一条未完成 Branch 继续。
2. 系统创建 child Run 后打开任务会话。
3. 在该会话中依次点击 Run 1 和 Run 2。

预期：只有一个会话；内部显示 Run 1、Run 2。Run 1 显示“历史只读”，旧成果与证据仍
可看，但控制、续办和 Worker 确认不可操作；Run 2 显示“当前”。

### TC-SEP-03：历史 Run 不接收当前 SSE

1. 打开仍在运行的 current Run，确认状态会实时更新。
2. 切到同 Task 的历史 Run。
3. 让 current Run 产生新事件或完成。

预期：历史 Run 页面不被新事件覆盖，也不出现状态倒退；切回 current 后先 GET 最新
Snapshot，再从最新 sequence 连接 SSE。

### TC-SEP-04：Demo 1 主页面保持时间维重点

打开入职资产任务。

预期：主页面优先显示 Task Contract、Round、Branch、Evidence Gate、ArtifactVersion 和
Run lineage；不再平铺完整 Worker/WorkUnit/Contribution 台账。若存在拓扑事实，只显示
紧凑协作摘要和工作台入口。

### TC-SEP-05：Adaptive Swarm 工作台正例

输入：

> 请分别核对产品上线、搜索 Agent 运行和用户交互三条工作线中最需要人工处理的风险与
> 证据，形成一份跨职能风险与待办简报。按工作包列出已核对来源、关键发现、缺口、受
> 影响下游和下一步；先独立核对，再统一收敛。不要修改源文件，不要执行代码，不调用
> 外部系统。

预期：当服务端 mode 为 `adaptive_readonly_workers` 时，主页面显式出现“Adaptive Swarm”
和“打开 Adaptive Swarm 工作台”。全屏工作台显示：

- 当前有限实现：受限只读 Worker；
- 3 个根工作包、2 个依赖工作包；
- 产品 4、算法 3、交互 3 共 10 个真实 FORTE 来源；
- 用户确认前零 Worker 调用；
- Worker 的 `called/output_used/elapsed_ms` 回执；
- Contribution 的 adopted/waiting/rejected/failed；
- 逻辑 ArtifactVersion v1、v2，且 v1 仍可回看；
- 没有真实下载工件时显示“尚未生成 DOCX/CSV 下载文件”。

### TC-SEP-06：搜索分支歧义只阻断下游

使用固定 `TripleAmbiguous` Fixture 或等价服务端测试，使搜索 Agent quote 出现三个候选。

预期：搜索工作包 waiting，依赖它的统一待办 blocked；产品上线和用户交互根工作包保留，
产品/交互 dependent 可继续，已有 v1 不被覆盖。工作台清楚显示“停在哪里、影响谁、保留
了什么”，主页面不把整个任务标成失败。

### TC-SEP-07：非 Adaptive 路线不伪造 Worker

输入三期同结构财务核对任务，或使用 `fixed_workflow` Fixture。

预期：工作台显示“本次未启动 Adaptive Swarm”和服务端原因；实际路线高亮 Fixed
Workflow；Worker/Contribution 为空，不出现假 Wave、假回执或假 v1/v2。

### TC-SEP-08：弹窗可访问与移动端

在 1440 px 和 390 px 打开/关闭工作台。

预期：

- `Escape` 可关闭，关闭后焦点回到入口；
- 背景不能误操作；
- 正文、事实、回执 computed font-size 为 13-14 px，辅助文字至少 12 px；
- 无页面或 dialog 横向溢出，无标题、文件名、按钮遮挡；
- 移动端改为单列，不压缩成不可读多栏。

## 二、自动化门

### 1. API / 状态门

- recent Run list 只返回当前 Owner，前台按 `task_id` 稳定分组；两个相同 instruction、不同
  Task 不得被合并。
- Task GET 失败或 pointer 不一致时 fail closed，不按 `updated_at` 猜 current。
- 历史 Run 切换关闭旧 EventSource；只有 selected=current 且非终态时建立 SSE。
- 同 Run 只单调应用 version/sequence；切换 Run 后才允许计数从较小值重新开始。
- continuation 仍保持 parent Run + Task 双版本 CAS，不能因会话 UI 放宽协议。

### 2. Demo 1 浏览器门

- 两 Task 两会话；一 Task 两 Run；刷新恢复；历史只读；打开 current。
- 控制命令、Branch continuation、Worker confirmation 不出现在历史 Run。
- 主 Loop 的 Evidence review、安全 Preview、Artifact history 和 15/96 Workspace 回归通过。

### 3. Demo 2 浏览器门

- Adaptive 摘要与全屏 dialog 显示真实 `topology_admission`。
- 10 个来源、3 root + 2 dependent、确认门、Worker receipt、Contribution 与 v1/v2 均来自
  Fixture Snapshot，而不是前端常量。
- `single_controller`、`fixed_workflow` 和无 admission 三个空态无伪 Worker。
- ambiguous、rejected、failed、checkpoint-recovered 各自显示不同影响。
- Evidence Anchor 可回开文件/表格行；浏览器不从 Finding 文案猜定位。

### 4. 隐私门

DOM、可访问名称和公共 JSON 不得出现：

- `owner_id`、raw `work_unit_id`/`branch_id` 作为主标签；
- source revision、reservation/idempotency digest、完整 hash、绝对路径；
- Prompt、CoT、raw Provider response、内部 validator/effect 表达式；
- raw task/rubric/solution。

### 5. 工程门

```powershell
uv run pytest -q
uv run ruff check .
pnpm --dir apps/web lint
pnpm --dir apps/web build
pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts
git diff --check
```

真实 PostgreSQL 只有配置独立 `TEST_DATABASE_DSN` 并实际运行后才能标通过；没有 DSN 的
skip 必须单列。真实 Provider 也必须另留 Run manifest，不能由 mock E2E 代替。

## 三、形成性用户走查

工程门通过后，仍需至少 5 名目标用户分别完成：

1. 找回上一条入职资产任务并打开 Run 1；
2. 判断 Run 1 与 Run 2 哪个是当前任务；
3. 解释为什么跨职能任务进入或没有进入 Adaptive Swarm；
4. 指出搜索分支失败影响了哪个下游，以及哪些成果仍保留；
5. 判断 v1/v2 是逻辑成果还是可下载办公文件。

记录任务完成率、错误点击、口述困惑点和完成时间。未完成这一步前，不得写“界面更清楚、
降低认知负担、提高信任或效率”。

## 四、2026-09-01 工程验收结果

- 会话隔离、历史只读、current Run SSE 重连、Adaptive 工作台和 Fixed Workflow 反例的
  定向浏览器门：`4 passed`；同轮生成桌面与 390 px 截图。
- 全量 Playwright：`73 passed`；全量 Python：`418 passed, 23 skipped`；Ruff、前端
  TypeScript lint、Next.js production build、汇报治理测试、变更 Markdown 链接检查和
  `git diff --check` 通过。
- 本轮未运行真实 Provider、独立 PostgreSQL 或五人形成性走查；Fixture 截图不能替代这些
  证据，也不能证明界面已经更易理解。
