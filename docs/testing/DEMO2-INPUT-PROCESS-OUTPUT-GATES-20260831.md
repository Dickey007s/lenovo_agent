# Demo 2 输入、过程与输出场景门

- 状态：`Limited Verified`；固定 Runtime/浏览器门已通过，真实 Provider、PostgreSQL
  本轮复跑与目标用户理解仍未验证
- 日期：2026-08-31
- 场景：`SCENARIO-042`
- 决策：`DR-0055`
- 用户来源：`USER-FEEDBACK-20260831-DEMO2-INPUT-PROCESS-OUTPUT`

## 1. 这组门验证什么

这组门不是继续证明抽象五单元 DAG，而是验证一个用户能复述的完整故事：输入哪些资料，
为什么分成这些工作包，用户何时确认，哪个候选进入成果，失败影响谁，最后究竟得到什么。
固定 Fixture 只验证公共合同和前台状态，不代表真实 Provider 每次都走同一路线，也不证明
业务结论正确。

## 2. 固定输入

普通用户指令：

> 请分别核对产品上线、搜索 Agent 运行和用户交互三条工作线中最需要人工处理的风险与
> 证据，形成一份跨职能风险与待办简报。按工作包列出已核对来源、关键发现、缺口、受
> 影响下游和下一步；先独立核对，再统一收敛。不要修改源文件，不要执行代码，不调用
> 外部系统。

Fixture 必须使用 FORTE 公共 Manifest 中十份真实文件的服务端 display group、label、
mime 和安全 `file_ref` 形状，不能把 `task.md`、rubric、solution、绝对路径或 raw hash
送入模型或 DOM。

## 3. 自动化用例

| ID | 输入或故障 | 过程断言 | 输出断言 |
| --- | --- | --- | --- |
| `D2-IPO-01` | 三工作线十份来源、预算充足、无副作用 | validated plan 为三 root/两 dependent；三个 root 来自不同 display group；Admission 为 `adaptive_readonly_workers` | 路线卡显示理由、来源跨度、每波上限和只读边界 |
| `D2-IPO-02` | 用户尚未确认 | WorkUnit DAG 可以存在，但 Worker handler 调用为 0，且没有伪造 returned/adopted 回执 | 页面只显示“等待确认”；可切回单 Controller |
| `D2-IPO-03` | 第一波三个合法 adopted | 先预留再调用；每条 Contribution 绑定自己的 Branch refs 与 Anchor | Artifact v1 含三个业务工作包，显示实际调用、返回和采用，不出现 raw `u1/u2` |
| `D2-IPO-04` | 第二波两个 dependent adopted | 只有依赖满足后进入 ready；稳定合并顺序；重复幂等请求零新增 | 追加 v2，v1 bytes/字段不变；显示“当前为逻辑成果版本，尚无下载文件” |
| `D2-IPO-05` | 搜索 Agent quote 多位置 | 该 Contribution waiting；产品与交互 adopted；只阻塞依赖搜索 Agent 的下游 | 部分 v1 保留；另一个合法 dependent 可继续；页面列出失败影响和唯一下一步 |
| `D2-IPO-06` | 越 Branch refs、无 Anchor、stale、篡改或对账冲突 | `model_called=true` 可保留，但 `output_used=false`；拒绝项不进入 Artifact | 显示“已返回，未进入成果”和中文原因，不把未采用说成未调用 |
| `D2-IPO-07` | 合法 Worker 返回 11 条 Findings | 合同上限为 96，不静默截断到 3 | Artifact、公共结果和前台可查看全部 11 条 |
| `D2-IPO-08` | 三期同结构财务 | Admission 为 `fixed_workflow`；无 WorkUnit/Contribution/Worker event | 三个既有成果含义清楚，不出现 Worker 确认或并行收益文案 |
| `D2-IPO-09` | Run GET 与 SSE | Snapshot/sequence 单调；终态 final GET 对账 | JSON/DOM 不含 Owner、raw revision、reservation、digest、Prompt、CoT 或 raw Provider reply |
| `D2-IPO-10` | 1440 px 与 390 px | 工作包标题、输入、依赖、回执、输出边界均可展开 | 正文约 13–14 px、辅助文字至少 12 px，无横向溢出或文字遮挡 |

## 4. 用户自己怎么试

启动：

```powershell
.\scripts\start-demo.ps1
```

打开 `http://localhost:3000`，粘贴固定输入后检查：

1. 路线卡是否先解释“为什么是单 Controller、固定流程或受限 Worker”，而不是因为指令
   中出现“分别”就直接并行。
2. 若出现受限 Worker 建议，确认前右侧实际调用和 WorkUnit 回执是否为零；确认后再观察
   第一波三个业务工作包。
3. 展开工作包，核对文件名是否分别属于产品管理、算法研发和用户体验；不同工作线的数字
   是否保持分组，没有被写成同一个产品结论。
4. 核对 `model_called`、`output_used`、耗时、Anchor 和“已返回/已采用/未进入成果”是否
   分开。不要仅凭最终段落判断。
5. 查看成果版本：v1 应只含第一波，v2 只能追加；页面应明确当前是逻辑成果，不是已下载
   的 DOCX/CSV，也没有改文件、执行代码或调用外部系统。
6. 同时保存 `/v1/harness/runs/{run_id}` 最终 GET、任务截图和健康页
   `checkpoint/task_store`。真实 Provider 若选择固定/单 Controller，应记录为真实结果，
   不为了演示重跑到出现 adaptive。

## 5. 验证命令

开发提交后至少运行：

```powershell
uv run pytest -q tests/unit/test_demo2_runtime.py
uv run pytest -q tests/acceptance/test_demo1_demo2_fixed_scenarios.py
uv run ruff check .
pnpm --dir apps/web lint
pnpm --dir apps/web build
pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts
```

配置真实 `TEST_DATABASE_DSN` 时再运行 WorkUnit/Contribution 重启门；没有 DSN 的 skip
必须原样报告。真实 Provider 只有在预算、Key 和日志路径预检完成后单独运行，Fixture、
浏览器 mock 或旧 Run 不能冒充本轮 Provider 验证。

## 6. 通过后仍不能声称

- 不能声称多 Worker 更快、更准、更便宜，或目标用户已经更容易理解；
- 不能声称产生了 `跨职能风险与待办简报.docx` 或 CSV；当前只有逻辑 ArtifactVersion；
- 不能声称不同 FORTE 项目属于同一个真实公司、产品或发布批次；
- 不能声称实现 distributed queue/lease、远端 Worker、多实例协调、Connector 或外部动作；
- 不能从官方文档未提及某个字段，推断竞品绝对没有相应能力。

## 7. 2026-08-31 实际结果

- Runtime、固定场景与治理：`35 passed in 3.11s`；
- 全量 Python：`418 passed, 23 skipped in 302.98s`；skip 不算通过；
- Ruff、Web lint、生产 build：passed；
- Demo 2 Playwright：`2 passed in 16.3s`，覆盖正向两波与搜索 Agent 歧义局部保留；
- 全量 Playwright 首次 `66 passed / 3 failed`，修复 101 份 Fixture 和默认预览回归后为
  `69 passed in 2.7m`；
- 变更 Markdown 本地链接与 `git diff --check`：passed；
- 未运行：本轮真实 Provider 与 PostgreSQL 场景复跑。

完整命令、输入集合、实现提交和结论边界见
[`Evidence`](../evidence/DR-0055-DEMO2-INPUT-PROCESS-OUTPUT-EVIDENCE-20260831.md)。
