# 运行观察：本地启动状态库选择与实际 API 不一致

## 来源元数据

| 字段 | 内容 |
| --- | --- |
| Source ID | `RUNTIME-OBSERVATION-20260826-21` |
| 日期 | 2026-08-26，Asia/Shanghai |
| 类型 | 本地真实运行、日志与配置存在性检查 |
| 触发 | 合并 Demo 1 Branch/Artifact 能力后，按交付门槛重新运行 `start-demo.ps1` |
| 敏感信息处理 | 只记录变量是否存在与服务状态，不记录 `.env` 的值、数据库地址、模型 Key 或 Provider 响应 |

## 可复核观察

1. 机器没有可用 Docker，启动进程也没有显式 `DATABASE_DSN`。
2. 仓库本地 `.env` 含有非空 `DATABASE_DSN`，但该地址对应的数据库当前不可用。
3. 修复前启动器提示将回退 memory，却没有写入空的进程环境变量；Pydantic Settings 随后继续从 `.env` 读取 DSN。
4. API 日志停在 `Waiting for application startup.`，45 秒后启动器超时，前台因此表现为离线。
5. 在无 Docker、无显式外部 DSN 的分支恢复 `$env:DATABASE_DSN = ""` 后，API 与 Web 均成功启动；health 返回 `checkpoint=memory`、`task_store=memory`。

## 支持判断

本地 Demo 启动器必须把“状态库选择”变成确定、可核对的启动契约。脚本提示、API
实际 Settings 与前台恢复能力必须一致；否则用户会把配置问题误判为 Agent 场景或
模型能力失败。

## 局限

- 这是单台 Windows 开发机上的真实故障，不是目标用户研究或生产可用性验证。
- memory 成功启动不证明 PostgreSQL 恢复；真实数据库证据仍来自 PR #31 的 PostgreSQL integration job。
- 本记录不证明 `.env` 中任何数据库地址无效，只证明本轮启动时不可用于该机器。
