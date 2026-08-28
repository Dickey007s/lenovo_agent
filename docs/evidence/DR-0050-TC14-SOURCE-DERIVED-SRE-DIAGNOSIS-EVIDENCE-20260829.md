# DR-0050 TC-14 来源推导 SRE 复盘 Evidence

## 当前结论

`Draft`，仅待 PR/远端 PostgreSQL 门与最终合并 SHA。固定 SRE-010 纵切的严格来源合同、动态观察/冲突/假设/提案、两份成果独立复核、真实 `deepseek-v4-pro`、本地 PostgreSQL 进程重启、完整本地工程门和前台截图均已通过；在远端门完成前仍不标 `Limited Verified`。

## 历史基线为何不足

历史 `_sre_diagnosis` 只提取 IP，其余 QPS、资源区间、GC/慢查询、48 个 UNASSIGNED、根因、三条 ES 命令和业务措施由生产代码写死，再检查同一批字符串。它无法证明来源变化会进入成果，且静默忽略节点、分片和磁盘口径冲突；旧目标还错误偏向 dedicated master `10.1.1.1`。历史 Evidence 与旧 Run 保留，不被本次实现反向改写。

## 来源推导与当前固定事实

- 来源合同只允许 `可靠性工程/log.txt`，绑定逻辑 ID、filename、display path、allowlist、声明大小、file ref 与冻结字节。
- 当前日志 232 行、3 个索引、11 个列出节点（3 master/8 data）；查询和写入 QPS 都是日志基线的 8 倍。
- 当前动态识别三组来源冲突：节点总数、UNASSIGNED 明细、磁盘阈值。冲突被写入 outcome/Markdown/CSV，不能被 deterministic green 覆盖。
- 当前假设保留支持、反证与局限；`NODE_LEFT`、来源冲突和恢复事件不会被吞成单一因果。
- ES proposal target 全部 `unresolved`；business mitigation target `not_applicable`。所有 proposal 都是 `approval_required=true`、`executed=false`，`resolved_target_count=0`、`external_action=none`。
- `sre_diagnosis_outcome.status=incident_review_required`。两份工件只在隔离 Run Workspace 写入，原日志不修改。

## 已通过的可证伪门

- QPS/baseline 合法变异进入 outcome、报告和台账；不一致的倍数 fail closed。
- 节点数或 shard 计数被来源修正后，只消除对应冲突；删除 GC 事件会降低主假设置信度。
- 未知异常片段进入 `unclassified/manual_review`；空、二进制、截断、错来源、非法数字和关键章节破坏失败。
- Markdown/CSV 的冲突 ID、观察文本等被篡改后独立 Verifier 转红。
- 静态扫描确认固定适配器不导入 `requests/httpx/socket/subprocess`，不包含 `Invoke-WebRequest`、`os.system` 或 `subprocess.run`。
- 运行探针替换 `socket.socket.connect` 与 `socket.create_connection` 为 fail-fast，完整构建与 12 项 Verifier 仍通过且连接尝试为 0。
- 公共前台 manifest 由同一来源推导模块生成；canonical 和节点/QPS 动态变体不在浏览器另写答案。

## 真实 Run、下载与重启

- Run：`harness:fe527536c857404f88f46d9a68b09397`；Owner header：`X-User-Id: tc14-live-owner-20260829`；start idempotency key：`scenario-effect-live-tc-14-07efa6cb2aca4496adcbb2385754d267`。
- 服务：`deepseek-v4-pro`、`checkpoint=postgres`、`task_store=postgres`。Planner `called=true/output_used=true/13212 ms`；Analyst `called=true/output_used=true/25960 ms`。
- Run 为 `waiting_input`，不是 `completed`：确定性成果已经通过，额外模型审计分支仍待处理。两组事实分开保留。
- EffectReceipt `passed`；两份 Artifact 共享 12 个唯一检查，`12/12` 通过。报告 `67698` bytes、SHA-256 `819e59c1d84af64609622d28d88282417a22214a0dc84808f2f55fe2d756d4c0`；台账 `90359` bytes、SHA-256 `253580d289e5d59b5a75f409b95983bb6983dc1cb10fa18ba111c756cc50d356`。
- 下载后独立重读批准日志、Markdown 与 183 行唯一 CSV 台账：167 observation、3 conflict、2 hypothesis、11 proposal，12 项再次通过。原日志仍匹配固定 manifest 的 size/hash。
- 停止并重新启动 API 后，以同一 Owner GET 同一 Run；Snapshot、EffectReceipt、`sre_diagnosis_outcome`、两份 Artifact 大小和 SHA 全部一致。这里只证明顺序 Runtime 恢复，不证明在途调用续跑或多实例安全。
- 证据清单：[`tc14-live-scenario-effect-20260829.json`](manifests/tc14-live-scenario-effect-20260829.json)、[`tc14-live-artifacts-before-restart-20260829.json`](manifests/tc14-live-artifacts-before-restart-20260829.json)、[`tc14-live-artifacts-after-restart-20260829.json`](manifests/tc14-live-artifacts-after-restart-20260829.json)。

## 当前工程门

- TC-14 来源模块（含静态扫描与 socket 运行探针）：`20 passed`。
- TC-14 来源/Scenario/Runtime/Contract 定向集合：`69 passed, 8 deselected`。
- 真实本地 PostgreSQL TC-14 顺序恢复门：`1 passed, 10 deselected`。
- `$env:TEST_DATABASE_DSN=...; uv run pytest -q`：`329 passed in 343.63s`。
- `uv run ruff check .`、公共 manifest `--check`、`pnpm --dir apps/web lint` 与 `pnpm --dir apps/web build` 均通过。
- 全量浏览器：`57 passed`；其中 TC-14 canonical、动态节点/QPS 和 Verifier failure 为 `3 passed`。

## 前台证据

- 1440×1100 完整三栏截图：[`tc14-sre-diagnosis-desktop.png`](screenshots/tc14-sre-diagnosis-desktop.png)。可靠性工程目录只展示批准 `log.txt`，中央显示四层事实、三组冲突和未解析目标，右侧保留 Control Loop 回执。
- 390×844 单栏截图：[`tc14-sre-diagnosis-mobile.png`](screenshots/tc14-sre-diagnosis-mobile.png)。长中文、指标和状态无页面级横向溢出。
- 尺寸、bytes、SHA 与捕获方式：[`tc14-ui-screenshots-20260829.json`](manifests/tc14-ui-screenshots-20260829.json)。截图是受控 E2E 投影，不是用户研究。

## 待补证据

- PR、远端 PostgreSQL workflow、最终合并 SHA 与最新 master 服务恢复。其余本地/真实 Run 门已闭合。

## 不能支持的结论

当前只覆盖固定 SRE-010 的离线事故复盘与条件式建议适配器。它不是在线监控、根因确定器、真实 Elasticsearch Connector、命令执行器、生产变更审批或通用日志诊断系统；也不证明提案对任何真实集群安全有效，不含多 Worker、多实例协调或用户研究。
