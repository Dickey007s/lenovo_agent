# SCENARIO-013：本地启动时获得真实可用的状态库模式

## 场景

演示者在一台没有 Docker 的 Windows 机器上启动 Office Agent。仓库 `.env` 用于保存
模型端点配置，并可能残留一个数据库地址；当前 PowerShell 没有显式授权外部
`DATABASE_DSN`。演示者需要系统立即以 memory 模式启动，而不是先看到“回退成功”
再面对一个离线页面。

## 用户、触发与痛点

| 项目 | 内容 |
| --- | --- |
| 用户 | 本地开发者、演示者、验收人员 |
| 触发 | 执行 `.\scripts\start-demo.ps1` |
| 主要痛点 | 脚本提示与 API 实际状态库不一致，使启动等待、离线和恢复能力难以判断 |
| 异常路径 | 无 Docker、无进程级 DSN，但 `.env` 中存在不可达 DSN |

## 期望流程

1. 启动器先判断 Docker 是否可用。
2. 没有 Docker 时，只接受当前 PowerShell 进程显式传入的 `DATABASE_DSN` 作为外部 PostgreSQL 选择。
3. 两者均没有时，启动器在子进程环境中显式清空 `DATABASE_DSN`，同时保留 `.env` 中的模型配置。
4. API 启动后通过 `/v1/health` 返回真实 `checkpoint` 与 `task_store`。
5. Web 只有在 API 和页面均可访问后才报告 ready；用户可立即进入完整文件资料库。

## 前台与后台统一

| 用户看到什么 | 服务端事实 | 用户如何恢复 | 默认隐藏 |
| --- | --- | --- | --- |
| 页面可用 | Web HTTP 200 + API health `status=ok` | 重新运行启动器 | `.env` 值、DSN、Key |
| 本轮不支持重启恢复 | `checkpoint=memory`、`task_store=memory` | 显式配置 PostgreSQL 后重启 | 连接字符串、Store 内部实现 |
| 启动失败 | API/Web health 未在期限内成功 + 日志 | 检查 `.runtime` 日志和显式配置 | Provider raw response、密钥 |

## 完成条件

- 残留 `.env` DSN 不再让“memory 回退”卡在 API startup。
- 启动器、health 和文档对状态库模式的描述一致。
- 静态回归守住 fallback 中的显式清空；真实启动验证 API/Web 200。
- 不把 memory 启动成功描述为 Durable State 或 PostgreSQL 证据。

## 来源与边界

- 来源：[`RUNTIME-OBSERVATION-20260826-21`](../sources/RUNTIME-OBSERVATION-20260826-21-startup-dsn-precedence.md)。
- 该场景是运行可靠性验收，不是用户研究；它不能证明前台理解、任务质量或业务价值改善。
