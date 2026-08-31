# WorkUnit / Contribution Ledger V1 验收门

- 日期：2026-08-31
- 决策：`DR-0055`
- 场景：`SCENARIO-041`
- 状态：`Draft`；以下是待执行合同，不是通过记录

## 1. 合同与权威关系

- `work_unit_id == branch_id`，每个 Worker WorkUnit 恰好对应一条合法 Branch。
- Branch 继续拥有目标、依赖、批准来源和 Evidence Gate；WorkUnit 只拥有执行状态。
- WorkUnit 状态迁移非法时 fail closed；浏览器字段不能推进服务端状态。
- Contribution ID、attempt 和公开 ID 稳定；Owner、raw digest/hash、Prompt、CoT、raw
  Provider response 不进入公共 API/DOM。

## 2. 预留、返回与收敛

- 模型调用前原子持久化 reservation、attempt、预算、Run/WorkUnit version、幂等回执和
  `worker_wave_reserved`。
- 同幂等键同 payload replay 零新增；不同 payload 409 且零预算/事件/候选变化。
- 每次返回只追加一条 Contribution；重复提交不新增 ArtifactVersion。
- `model_called`、`returned`、`output_used/adopted` 独立，可由 Snapshot 与 named SSE 对账。
- Merge 按服务端 WorkUnit/Branch 顺序稳定，与客户端 `branch_ids` 顺序无关。

## 3. 固定场景

1. 五单元 DAG：三个 root 第一波，两个 dependent 第二波；5/5 adopted，Artifact v1/v2。
2. 两 adopted、一 ambiguous：已采用兄弟项和 v1 保留，仅相关下游 blocked。
3. 安全拒绝：越 Branch 来源、无 Anchor、重复 quote、stale revision、候选篡改和对账
   冲突不进入 Artifact，拒绝记录保留。
4. 三期同结构财务反例：Admission 为 `fixed_workflow`；无 Worker WorkUnit、Contribution
   或 Worker named event。

## 4. 持久化与故障

- Memory 与 PostgreSQL adapter 对 owner scope、version CAS、幂等和 append-only 语义一致。
- 事务注入失败时无孤立 Contribution、半更新 Artifact/Commit 或扣预算无 reservation。
- PostgreSQL 重启保留 WorkUnit/Contribution；`reserved/running` 不自动重放 Provider，
  而是进入可审查失败/需处理状态。
- 没有 `TEST_DATABASE_DSN` 时测试必须明确 skip；collect/skip 不得写成真实 PG 通过。
- 跨 Owner、orphan Branch、旧 version 和破损持久记录全部 fail closed。

## 5. 公共 API、SSE 与前台

- OpenAPI 继续保持现有公开路径，不增加 Demo/WorkUnit CRUD。
- Run GET/Snapshot 返回脱敏 WorkUnit/Contribution；Task GET 只返回 current/lineage 摘要。
- named SSE sequence 单调；断线 GET + after 恢复后与最终 Snapshot 一致。
- 前台显示业务工作包、依赖、返回/采用分离、原因、来源/Anchor、ArtifactVersion 和部分
  可用提示；不显示 Worker 聊天墙。
- 1440 px 与 390 px 无横向溢出；正文 13–14 px，辅助文字至少 12 px。

## 6. 必跑命令

```powershell
uv run pytest -q tests/unit/test_demo2_runtime.py
uv run pytest -q tests/acceptance/test_demo1_demo2_fixed_scenarios.py
uv run pytest -q tests/integration -k "work_unit or contribution or demo2_worker"
uv run ruff check .
pnpm --dir apps/web lint
pnpm --dir apps/web build
pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts
uv run pytest -q
```

真实 PostgreSQL 命令必须设置隔离测试 DSN，记录 PostgreSQL 版本、通过/跳过数和停止清理
状态；不得打印凭据。真实 Provider 未经单独授权不运行。

## 7. 结论门

只有源码、定向/全量测试、真实 PG 门、浏览器和最终公共事实都通过，才能把本纵切标为
`Limited Verified`。缺真实 PG 时必须写“Memory/API/browser 已验证，PostgreSQL 未验证”；
缺 Provider 和目标用户研究时不得宣称生产 durability、多 Worker 收益或交互价值改善。
