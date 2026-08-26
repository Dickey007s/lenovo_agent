# 可恢复 Evidence Gate 与成果演进 Evidence

> 生命周期：本 Evidence 绑定 [PR #30](https://github.com/Dickey007s/lenovo_agent/pull/30)，
> 已合并为 `8c55422`。其中 `59 passed`、Runtime `22 passed`、浏览器 `12 passed` 和
> “无本轮真实 PostgreSQL”均是该提交生命周期内的历史观测。现行分支级 Gate、独立
> append-only 成果记录和真实 PostgreSQL PR 门见
> [`DEMO1-BRANCH-ARTIFACT-CONTROL-20260826`](DEMO1-BRANCH-ARTIFACT-CONTROL-EVIDENCE-20260826.md)。

> 状态：`Limited Verified`。只证明固定 FORTE、单 Runtime、最多三轮、只读
> Control Loop 的自动化路径。PostgreSQL 代码路径已实现，但本机缺少 Docker/
> PostgreSQL，尚无本轮真实数据库进程重启运行证据。

## 1. 本轮主张

本 Evidence 验证：证据不足时服务端会在下一轮前进入 `waiting_input`；用户确认前
不会继续调用模型；逐轮结果形成可见逻辑版本；浏览器刷新可恢复同一 Run；共享
StateStore 的顺序 Runtime 能回滚未完成轮次、追加恢复事件并等待用户显式 resume。

它不证明语义/数值正确、远端 HTTP 调用取消、独立不可变 Artifact、跨实例并发、
真实 Tool Gateway、Connector、外部动作、生产身份或用户价值。

## 2. 实现位置

| 事实 | 实现 |
| --- | --- |
| StateStore 与 PostgreSQL 事务 | `services/api/app/application/harness_storage.py` |
| 恢复、人工 Evidence Gate、逻辑版本/Commit | `services/api/app/application/harness_runtime.py` |
| Run 列表与公开协议 | `services/api/app/api/harness_routes.py`、`packages/contracts/harness_models.py` |
| 刷新恢复、确认继续、成果演进 | `apps/web/app/harness-workbench.tsx`、`apps/web/app/styles.css` |
| Runtime 恢复与幂等回归 | `tests/unit/test_harness_runtime.py` |
| 前台确认/刷新/响应式回归 | `apps/web/e2e/harness-workbench.spec.ts` |

## 3. 自动化观测

| 检查 | 结果 | 能证明什么 | 不能证明什么 |
| --- | --- | --- | --- |
| `uv run pytest -q` | `59 passed in 14.40s` | Python 合同、Runtime、安全读取和恢复模拟通过 | 真实数据库/模型质量/用户价值 |
| Runtime 聚焦 | `22 passed in 1.13s` | Evidence Gate、补证范围、控制、恢复、Artifacts 与 HTTP 投影 | 多实例竞争和真实 PostgreSQL |
| `pnpm --dir apps/web lint` | 通过 | TypeScript 类型检查通过 | 浏览器行为与视觉质量 |
| `pnpm --dir apps/web build` | 通过 | Next.js 生产构建成功 | 生产部署和运行稳定性 |
| Harness Playwright | `12 passed in 24.9s` | 文件管理器、确认 Gate、刷新恢复、引用、移动 390px 路径 | 真实用户理解和真实模型调用 |

关键恢复测试先让 Planner 阻塞，再关闭第一个 Runtime。第二个 Runtime 使用同一个
Store 恢复后满足：`status=paused`、未完成轮次被移除、Planner 调用数仍为 0、末事件
为 `checkpoint_recovered`；用户 resume 后再进入模型路径并最终 Commit。

关键前台测试满足：Evidence Gate 出现时控制请求数为 0；点击“确认并继续核对”后才
出现唯一 `resume`；页面 reload 后仍显示同一个非终态 Run 和原指令。

新增方向漂移回归在资料库中放入一个无关文件：第一轮缺口为 `REF_TWO`，用户确认后
第二轮 Planner 可见输入和 `round.input_file_refs` 都只能是 `REF_TWO`；干扰文件不能
进入补证轮，`round_started.details.evidence_recheck=true`。

## 4. 真实模型运行观测

| Run | 输入与观测 | 结果 | 能证明什么 | 不能证明什么 |
| --- | --- | --- | --- | --- |
| `harness:2fc502f942214fa49c5b0d3df0693cdc` | 自由整库研究；Planner `10289ms`、Analyst `20622ms` | 1 轮、4 份引用通过、`v1:committed`、总 `30964ms` | 两次真实 `deepseek-v4-pro` 调用、采用回执、Gate 与 Commit 串联发生 | 结论正确、普遍延迟或用户价值 |
| `harness:3fbd34493b0744d5b2c2fe80d62433d7` | 定向要求首轮 4 份只引用 2 份；Gate 后人工 resume | 2 轮、第二轮输入严格等于 2 份缺失证据、`v1:draft → v2:committed`、4 次调用、总 `76341ms` | 真实模型路径中等待、确认、补证范围约束和成果演进发生 | 未展示的文件都不相关、语义真值或交互更优 |

修复前的探索 Run `harness:793300f0c50e4b789eb9d153c07dd60a` 暴露了负面证据：
首轮确认后，第二轮 Planner 改选无关法务文件，最终 `status=stopped`。这促成服务端把
补证轮锁定为上一 Gate candidates；修复后由上表第二个 Run 与自动化共同验证。

## 5. PostgreSQL 与本机运行边界

- 配置 `DATABASE_DSN` 时，`harness_run_state` 保存 Snapshot/resume status，
  `harness_idempotency` 保存 start/control receipt；命令 receipt 与 Snapshot 在同一
  PostgreSQL transaction 中提交。
- 本地 `start-demo.ps1` 会优先检测 Docker/PostgreSQL；不可用时明确 warning 并将
  `DATABASE_DSN` 置空，health 返回 `checkpoint=memory/task_store=memory`。
- 2026-08-26 当前机器运行采用 memory fallback。这个 live 服务不能作为跨进程恢复
  证据；不能用旧 Demo 1 PostgreSQL Evidence 替代当前 Harness 的新验证。

## 6. 前台事实与边界

- “等待人工输入”来自 Snapshot `status=waiting_input`，不是客户端计时。
- “确认并继续核对”只有收到服务端 resume Snapshot 后才切换状态。
- 补证轮只允许上一 Gate 展示的缺失证据；轨迹用 `evidence_recheck=true` 区分补核与新探索。
- “服务端检查点已恢复”只在 `checkpoint_recovered` 事件存在时显示。
- “成果 vN”来自 `artifact_versions[]`；“已提交”来自 `last_commit`。
- 逻辑版本不会修改 FORTE 原文件，也不证明 `artifact.write` 工具执行。
- 结果、版本和 Commit 始终要求人工复核。

## 7. 绑定

- 工作分支：`codex/durable-agent-control-loop-20260825`
- 实现提交：`edd393a`（`feat: make the agent control loop recoverable and human-gated`）
- Pull Request：[#30 Agent Control Loop：可恢复证据门与成果演进](https://github.com/Dickey007s/lenovo_agent/pull/30)
