# PostgreSQL 测试隔离修复与 Demo3 本地预览

日期：2026-09-23。修复基线：`7cbe736`。范围：测试清理、CI 验证范围和本地预览，不改产品协议或 Runtime。

## 来源与失败记录

来源 ID：`USER-FEEDBACK-20260923-CI-FIX-AND-DEMO3-PREVIEW`。
用户提供 PostgreSQL Actions 失败截图，并授权：“修复推送吧，另外部署当前demo给我看看，让我自己测试一下demo3”。
该反馈支持修复、推送和本地试用，不授权对外部署、真实发件或业务系统操作。

合并提交的 [Actions 35450314217](https://github.com/Dickey007s/lenovo_agent/actions/runs/35450314217) 为 1 passed、12 failed。
此前主分支 `9a4bbbf` 的 [Actions 34802858489](https://github.com/Dickey007s/lenovo_agent/actions/runs/34802858489) 也为 1 passed、12 failed。
两次日志均出现“任务台账指向不存在的 Run”。合并时未检查远程失败结果，不能以本地跳过数据库测试代替 PostgreSQL 验证。

第一项测试的 finally 只清理旧四张表，删除 Run 后遗留 Task 台账。后续 Runtime.setup 加载全库并检查 Task/Run 关系，因此拒绝启动。
Demo 1/2 和 Task Ledger 测试的旧清理也遗漏 WorkUnit/Contribution。

## 修复与设计取舍

三组测试共用 `tests/postgres_helpers.py`，在同一事务中清理该测试 Owner 的八张表；即使 start 未返回 run_id，也按已分配的 Owner 清理。
Owner 必须符合现有测试前缀及 UUID 后缀，SQL 值参数化、表名来自固定清单。不清空整库，不修改其他 Owner，不放宽 Runtime 完整性检查。

新增单元检查约束清理清单与建表代码一致，验证非法 Owner、空 DSN 和事务/参数绑定。
新增真实 SQL 回归向八张表分别写入两个测试 Owner，核对重复清理后目标 Owner 为零、另一 Owner 全部保留。
CI 在同一 PostgreSQL 17 服务中运行 Control Loop、Task Ledger、Demo 1/2 和新增清理回归，不再只运行旧的 13 项。

这沿用现有 Task/Run 与 WorkUnit 台账决策，不新增产品决策或 UI 状态。所有界面仍以 Snapshot、Task current pointer、version 和幂等回执为准。

## 验证记录

新增清理单元检查 7 passed；reporting governance 4 passed；Ruff、TypeScript 和 Next.js 生产构建通过。
主工作台与 Demo3 浏览器组合门为 112 passed（5.2 分钟），包括 11 项连接真实本地 FastAPI 的事项检查。
Python 全量回归为 482 passed、24 skipped（457.70 秒）。真实 PostgreSQL 结果以修复提交对应 Actions 为准；本地没有设置 TEST_DATABASE_DSN，24 个跳过项不计作通过。

## 本地试用

前端：`http://localhost:3000`。API：`http://localhost:8010`。
启动后的 `/v1/health` 为 `status=ok`、`checkpoint=memory`、`task_store=memory`；前端返回 HTTP 200，浏览器已打开“办理事项”，显示六类操作。

可在“新建任务 → 办理事项”试用默认的“整理个人文本”，随后测试草稿编辑、暂缓找回、材料分歧人工选择和测试发件确认。
期望结果是服务端版本化的事项记录，不是真实业务动作；API 离线或冲突必须显示错误，不能用界面动画当作成功证据。
当前进程重启会丢失记录；本轮没有调用真实 Provider、配置持久数据库或开展目标用户研究。
