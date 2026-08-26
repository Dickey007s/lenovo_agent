# 本地启动状态库优先级 Evidence（2026-08-26）

## 结论

状态：`Limited Verified`。在本机没有 Docker、当前 PowerShell 未显式设置
`DATABASE_DSN`、仓库 `.env` 仍含数据库配置的条件下，修复后的启动器成功让 API
进入 memory，并启动 Web。该结果证明本地 fallback 与 health 事实一致，不证明
PostgreSQL 恢复或生产部署可靠性。

## 失败观测

- 修复前启动器输出 memory warning，但 API 日志停在 `Waiting for application startup.`。
- 45 秒后启动失败；根因是 fallback 没有覆盖 `.env` 中的 DSN。
- 记录只核对变量是否存在，没有读取或保存 DSN/Key 的值。

## 修复与服务端事实

- `scripts/start-demo.ps1` 在无 Docker、无进程级显式 DSN 时写入 `$env:DATABASE_DSN = ""`。
- API health：`status=ok`、`model=deepseek-v4-pro`、`checkpoint=memory`、`task_store=memory`。
- Web 根页面返回 HTTP 200；API 日志进入 `Application startup complete.`；Next.js 进入 `Ready`。
- `.env` 文件没有被修改，模型配置仍由现有 Settings 读取。

## 自动化

- 聚焦 launcher 静态回归：`1 passed in 0.02s`。
- Python 全量：`64 passed, 1 skipped in 15.03s`；跳过项仍是本机没有
  `TEST_DATABASE_DSN` 的真实 PostgreSQL integration test。
- Ruff：`All checks passed!`。
- 实现提交：`3d902cf`；[PR #33](https://github.com/Dickey007s/lenovo_agent/pull/33)。
- 远端 PostgreSQL CI 的运行链接与结果待完成后绑定；此前 PR #31 的真实 PostgreSQL
  证据不被本轮 memory 启动替代。

## 能证明什么

- fallback 选择与 API 实际 Store 一致。
- 残留 `.env` 数据库项不会再让本轮 memory 启动卡死。
- 用户可以进入资料库；health 可明确说明本轮不能跨 API 重启恢复。

## 不能证明什么

- 不证明 PostgreSQL、跨进程恢复、多实例、高可用或故障转移。
- 不证明模型回答正确、Agent Control Loop 完整或用户价值。
- 不是用户研究；页面可访问不等于交互已经被用户理解。
