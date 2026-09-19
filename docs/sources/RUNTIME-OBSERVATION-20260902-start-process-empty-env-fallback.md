# Runtime 观测：Windows 后台进程未可靠继承空数据库变量

- 日期：2026-09-02，Asia/Shanghai
- 类型：本机启动失败复现与修复验证
- 适用决策：`DR-0027` 2026-09-02 更正

## 观测

在无可用 Docker、启动 PowerShell 未显式提供 `DATABASE_DSN`、仓库 `.env` 仍含历史数据库
配置时，`start-demo.ps1` 已进入 memory 分支并把父进程变量设为空字符串。但 Windows
`Start-Process` 启动的 API 仍从 `.env` 读取到历史配置，最终以
`psycopg.errors.ConnectionTimeout: connection timeout expired` 结束启动。

这说明“父进程设置空环境变量”不足以在该启动链中稳定表达显式覆盖。日志和本记录均未保存
连接串、模型 Key 或其他秘密值。

## 修复后事实

- 启动器在 fallback 分支设置非空 `STATE_STORE_MODE=memory`；
- Runtime 在该模式下无条件选择进程内 Store，即使 Settings 同时读到历史 `DATABASE_DSN`；
- `STATE_STORE_MODE=postgres` 没有 DSN 时 fail closed；默认 `auto` 保持原有 DSN 自动选择；
- 同一机器重新运行启动器后，API health 返回 `status=ok`、`checkpoint=memory`、
  `task_store=memory`，Web `/agent-capabilities` 返回 HTTP 200。

## 边界

这是一个 Windows 本机进程环境与 Settings 优先级回归，不证明 PostgreSQL 可用、跨进程恢复、
生产部署可靠性或 Agent 任务质量。memory 模式下再次重启 API 仍会丢失 Run 状态。
