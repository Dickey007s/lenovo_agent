# DR-0025：可恢复检查点、人工证据门与成果演进

> 生命周期：本决策已随 [PR #30](https://github.com/Dickey007s/lenovo_agent/pull/30)
> 合并为 `8c55422`，保留为整组补证和 Snapshot 内逻辑版本的历史基线。2026-08-26
> 起，分支级继续、独立 append-only ArtifactVersion/TaskCommit 与受控恢复的当前事实
> 由 [`DR-0026`](DR-0026-selective-branch-and-immutable-artifact-history.md) 替代。

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`，仅限固定 FORTE、最多三轮、单 Runtime 只读路径与本决策列出的恢复测试 |
| 日期 | 2026-08-26 |
| 触发来源 | [`USER-FEEDBACK-20260826-19`](../sources/USER-FEEDBACK-20260826-19-durable-evidence-gate-artifact-evolution.md)、`USER-FEEDBACK-20260825-CONTROL-LOOP-16` |
| 场景 | [`SCENARIO-011`](../scenarios/SCENARIO-011-recover-and-confirm-evidence-round.md) |
| Evidence | [`DURABLE-EVIDENCE-GATE-ARTIFACT-EVOLUTION-20260826`](../evidence/DURABLE-EVIDENCE-GATE-ARTIFACT-EVOLUTION-EVIDENCE-20260826.md) |
| 延续 | `DR-0023` 的通用 Agent Control Loop 与 `DR-0024` 的整库自主检索 |

## 问题定位

整库 Control Loop 已能真实调用 Planner/Analyst、分轮核对和接受控制，但有三个断点：

1. 证据不足且预算允许时，服务端自动进入下一轮。用户看得到结果，却不能在下一次模型调用前决定是否值得继续。
2. 浏览器刷新只依赖当前 React 状态；API 重启后 Run、事件和幂等回执消失。界面上的“恢复”只能证明 SSE 重连，不能证明任务恢复。
3. 每轮结果只留在 `rounds[]` 和最终 Brief 中。用户看不到 Agent 如何把一版草稿逐轮补证为最终成果。
4. 首次真实模型冒烟发现：用户确认补证后，Planner 仍可能从整库改选无关文件；这会把“继续核对这两个缺口”错误地变成一次新探索，并使已通过的第二轮最终落为预算停止。

## 决策

1. Evidence Gate 发现可补证缺口且预算允许时，输出 `next_step.decision=waiting_input`，同时把 Run 置为 `status=waiting_input/control_state=paused`。
2. 前台显示缺口、下一轮目的和“确认并继续核对”。只有 versioned、idempotent `resume` 回执返回后，下一轮才能开始。确认后的补证轮由服务端限定为上一轮 `candidate_file_refs`，Plan Validator 要求计划覆盖全部待核对文件，不能悄悄换成无关资料。用户仍可先 `steer` 或直接 `stop`。
3. 引入 `HarnessStateStore`。没有 `DATABASE_DSN` 时使用 memory；配置 PostgreSQL 时，Snapshot 与 start/control 幂等回执在同一事务中写入。
4. API 启动恢复非终态 Run 时，仅保留已完成轮次，追加 `checkpoint_recovered`，暂停在安全点；绝不自动重放中断的模型调用。
5. 浏览器用 session 中的 Run id 做 GET 对账；本地没有 id 时，用 Owner-scoped `GET /v1/harness/runs` 找最近非终态 Run，再从权威 sequence 恢复 SSE。
6. 每个完成轮次生成一个逻辑 `evidence_brief` 版本。存在缺口时为 `draft`，无缺口时为 `verified`；最终成功 Gate 将最新版本标为 `committed` 并记录 `last_commit`。
7. 逻辑版本和 Commit 只表示 Run 内只读成果演进，不声称独立不可变存储、源文件写入、Tool Gateway 或外部动作。

## 技术差异及其交互后果

| 技术差异 | 原流程 | 当前流程 | 前台具体输出 |
| --- | --- | --- | --- |
| 服务端轮次间暂停 | 缺口存在时自动花下一轮预算 | 人先决定是否继续 | 缺口、下一轮目的、确认继续、调整方向、停止 |
| 补证范围由服务端继承 | 模型可在确认后重新选题 | 下一轮只能核对用户刚确认的缺失证据 | 轨迹明确显示“核对上轮尚未覆盖的证据”，成果 v2 延续 v1 |
| Snapshot/回执持久化 | 进程重启后 Run 消失 | PostgreSQL 可恢复到最后完成轮次 | “服务端检查点已恢复”、保留轮次/预算/轨迹、继续按钮 |
| 不重放在途调用 | 恢复语义不存在 | 中断轮次回滚，明确等待人恢复 | 不把动画或旧回执当作调用重新发生 |
| 逐轮逻辑成果版本 | 只看到轮次和最终总结 | 每轮形成 v1/v2/v3 | 草稿、已核对、已提交及引用数量 |
| Owner 最近 Run 列表 | 只能知道当前内存变量 | 可发现服务器上的非终态任务 | 刷新后回到同一任务，而不是伪造新任务 |

## 前后台统一事实

| UI 状态 | 服务端事实 | 用户动作 | 隐藏细节 |
| --- | --- | --- | --- |
| 等待你确认 | `status=waiting_input`、`control_state=paused`、Gate event | resume / steer / stop | 内部策略枚举、Prompt、CoT |
| 补核上一轮证据 | `round_started.details.evidence_recheck=true`，本轮 refs 等于上轮 Gate candidates | 查看执行轨迹和 v1→v2 | 文件排名、Prompt、CoT |
| 检查点已恢复 | `checkpoint_recovered` event | 检查轨迹后 resume | 数据库表名、DSN、内部 Snapshot JSON |
| 成果 vN | `artifact_versions[N-1]` | 查看轮次与引用 | 内部 digest、模型原始响应 |
| 已提交 | `last_commit` + `loop_committed` | 人工复核或启动下一任务 | 不存在的文件写入/外部执行事实 |
| 恢复失败 | Run 404 或 backend=`memory` 后进程重启 | 新建 Run 或配置数据库 | 不填充静态成功状态 |

## 验证与边界

- 单元测试模拟共享 StateStore 的两个顺序 Runtime：第一个在 Planner 阻塞时关闭；第二个恢复为 paused、删除未完成轮次、零自动模型调用，用户 resume 后完成。
- 浏览器测试覆盖 Evidence Gate 在确认前零控制调用、确认后 resume，以及页面刷新恢复同一 Run。
- 自动化回归加入无关文件干扰项，验证确认后的第二轮输入严格等于上一轮缺口，不会漂移到干扰文件。
- 真实 `deepseek-v4-pro` 定向冒烟首轮读取 4 份、引用 2 份，人工 resume 后第二轮只读取缺失的 2 份，最终形成 `v1:draft → v2:committed`；这证明调用与范围约束发生，不证明结论语义正确。
- PostgreSQL 适配器建立真实表和事务逻辑；当前机器没有 Docker/PostgreSQL，因此本轮没有新增真实数据库进程重启证据。旧 Demo 1 PostgreSQL 证据不能自动迁移为当前 Harness 的运行证据。
- `close()` 取消进程内 asyncio task，但不能证明远端供应商已经取消收到的 HTTP 请求。
- 没有跨实例 lease、通知、CAS 调度或独立 Artifact 表；不能称生产级 Durable Runtime。
- 自动化不是用户研究；理解、信任、效率和业务质量仍为 `Draft`。
