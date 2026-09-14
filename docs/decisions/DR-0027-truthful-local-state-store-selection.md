# DR-0027：本地启动状态库选择必须与 API 事实一致

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`，2026-09-02 已修正 Windows `Start-Process` 空变量继承回归；限 Windows 本地启动器与当前单 API 进程 |
| 日期 | 2026-08-26；2026-09-02 更正 |
| 触发来源 | [`RUNTIME-OBSERVATION-20260826-21`](../sources/RUNTIME-OBSERVATION-20260826-21-startup-dsn-precedence.md)、[`RUNTIME-OBSERVATION-20260902-START-PROCESS-EMPTY-ENV-FALLBACK`](../sources/RUNTIME-OBSERVATION-20260902-start-process-empty-env-fallback.md) |
| 场景 | [`SCENARIO-013`](../scenarios/SCENARIO-013-truthful-local-state-store-fallback.md) |
| Evidence | [`START-DEMO-DSN-PRECEDENCE-EVIDENCE-20260826`](../evidence/START-DEMO-DSN-PRECEDENCE-EVIDENCE-20260826.md) |
| 影响范围 | `scripts/start-demo.ps1`、本地运行说明、UI—服务端事实矩阵 |

## 问题定位

启动器已经能在 Docker 不可用时接受一个显式外部 PostgreSQL DSN，但该改动漏掉了
memory 分支中的环境覆盖。结果是脚本依据当前 PowerShell 环境判断“没有 DSN”，
API 却依据 `.env` 读到另一个 DSN。用户看到的不是可解释的 memory 边界，而是一个
长时间等待后离线的页面。

## 决策

1. 本地启动器按固定优先级选择状态库：可用 Docker、当前 PowerShell 显式 `DATABASE_DSN`、memory。
2. 进入 memory 分支时必须在 API 子进程环境中写入非空
   `STATE_STORE_MODE=memory`，由 Runtime 明确忽略 `.env` 中的残留 DSN；不修改
   `.env` 文件。历史“写入空 `DATABASE_DSN`”在 Windows `Start-Process` 下不可靠，
   已被本规则取代。
3. 模型端点、模型 Key、模型名等其他 Settings 继续按原逻辑从 `.env` 读取。
4. 启动成功与恢复能力的最终事实来自 `/v1/health.status/checkpoint/task_store`，启动器提示只是操作反馈。
5. 不在普通 UI、日志 Evidence 或文档中记录 DSN、Key 和其他秘密值。

## 技术差异及其交互后果

| 技术差异 | 修复前交互 | 修复后交互 | 前台输出影响 |
| --- | --- | --- | --- |
| 启动器与 Settings 同一优先级 | 脚本说 memory，API 仍尝试 `.env` 数据库 | 非空模式变量强制 Runtime 选择 memory | 页面不再因假回退而离线 |
| health 作为最终事实 | 用户只能猜是否具备恢复 | 可核对 memory/PostgreSQL | 汇报不再把配置或动画当 Durable 证据 |
| 不修改 `.env` | 用户可能担心模型 API 配置被清空 | 只覆盖当前子进程数据库变量 | 已配置模型仍可真实调用 |

## 前后台事实与隐藏边界

| UI/操作状态 | 后端事实 | Owner/版本 | 隐藏内容 |
| --- | --- | --- | --- |
| 可进入资料库 | Web 200 + health `status=ok` | 当前 API 进程 | `.env`、DSN、Key |
| memory 模式 | health `checkpoint=memory/task_store=memory` | 当前 API 进程生命周期 | Store 对象与内部记录 |
| 可恢复模式 | health 返回 PostgreSQL-backed 状态 | StateStore/数据库记录版本 | 凭据、连接串、数据库行 |
| 启动超时 | health 未就绪 + `.runtime` 日志 | 启动器 deadline | 不向页面暴露内部异常堆栈 |

## 验证与边界

- Python 回归确认 fallback 在 warning 前设置一次 `STATE_STORE_MODE=memory`，Runtime
  可在同时存在历史 DSN 时强制 memory，并拒绝缺 DSN 的显式 postgres 模式。
- 同一台机器保留 `.env`、无 Docker、无进程级 DSN 时，真实启动 API/Web 成功；health 明确返回 memory。
- PR 回归覆盖 Python/Ruff；此前完整前端 E2E 与 PostgreSQL integration 证据不被本修复替代。
- PR #33 的 PostgreSQL 17.11 job 通过：`1 passed in 1.88s`；该门只证明既有顺序 Runtime 数据库路径未回归。
- 本决策不证明 PostgreSQL 高可用、多实例 lease、跨机器启动、用户理解或 Agent 任务质量。

## 2026-09-02 更正说明

原实现 `3d902cf` 与 PR #33 的历史 Evidence 保留，但“空环境变量一定覆盖 `.env`”这一机制性
结论被新的真实失败推翻。当前权威做法是 `STATE_STORE_MODE=auto|memory|postgres`；本轮实际
启动与 health 事实记录在更新后的 Evidence 中。
