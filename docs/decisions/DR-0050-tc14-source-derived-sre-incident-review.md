# DR-0050：TC-14 来源推导 SRE 复盘、冲突保留与未执行提案

- 状态：Draft；来源合同、动态解析、两份工件独立 Verifier 与前台四层事实已实现，真实 Provider/PostgreSQL/PR 证据待本分支收口
- 日期：2026-08-29
- Source：`USER-FEEDBACK-20260829-TC14-SOURCE-DERIVED-SRE-DIAGNOSIS`
- Scenario：`SCENARIO-035`

## 决策

1. TC-14 仍由 Workspace-first 普通指令触发，不增加 Scenario 选择器。固定适配器只允许 `sre-010/input/log.txt`，并绑定逻辑 ID、文件名、展示路径、allowlist、声明大小、file ref 和冻结字节。
2. 服务端从批准日志逐行解析告警、集群、节点、QPS、资源、GC、慢查询、队列拒绝、health、thread pool、shard、allocation、查询形态和恢复事件。未知片段进入 `unclassified/manual_review`，结构损坏或关键数字非法则 fail closed。
3. `Observation` 只陈述日志事实；`Hypothesis` 必须列支持、反证与局限。当前主假设只能说容量与查询形态共同放大得到来源支持，不能把同时出现写成已证因果。
4. 当前日志内部至少有节点总数、UNASSIGNED 分片数和磁盘阈值三组冲突。确定性绿灯只证明冲突被完整识别并写入成果，不证明日志数据一致。
5. 所有 `ActionProposal` 固定为 `approval_required=true`、`executed=false`。日志中的 `10.1.1.1` 是 dedicated master，不得自动当作客户端 endpoint；ES 提案的 target 必须保持 `unresolved`。
6. 第一层只读预检、条件式写提案和业务止损都只是提案。`retry_failed` 先要求根因修复与 dry-run/explain；refresh 必须先读原值与 SLA；cache clear 必须 index-scoped 且由 stats 支持。
7. 两份工件为 `ES故障诊断与止损建议.md` 和 `SRE事故观察与动作台账.csv`。Verifier 重读批准日志，再独立解析最终 Markdown/CSV，核对观察、冲突、假设、支持/反证、提案安全字段、官方参考和未执行边界。
8. `sre_diagnosis_outcome` 同时进入 Artifact、EffectReceipt、Snapshot/API 和 PostgreSQL。前台分别显示确定性验证、观察与冲突、假设/提案待复核、真实命令与业务动作未发生。
9. Elasticsearch 7.10 官方文档只解释 API/节点语义。它不能证明当前现场状态、目标入口、参数、审批或执行安全。
10. 原 FORTE 日志保持只读，`external_action=none`。`completed` 只说明 Loop 与确定性工件合同通过，不表示根因确定、提案获批或止损已执行。

## 前后端事实

| 前台 | 服务端事实 | 不允许推断 |
| --- | --- | --- |
| 这是离线事故复盘与止损提案 | `sre_diagnosis_outcome.status=incident_review_required` | 在线监控或根因定论 |
| 两份成果确定性通过或失败 | Artifact `verifier_status/checks[]`、EffectReceipt `status` | 建议适合生产现场 |
| 三组来源冲突 | `source_conflicts[]` 与双端 locator | 冲突已经解决 |
| 假设、支持、反证和局限 | `hypotheses[]` | 同时出现等于因果已证 |
| endpoint 尚未确定 | `resolved_target_count=0`、ES proposal `target_status=unresolved` | dedicated master 可作生产入口 |
| 所有动作未发生 | proposal `executed=false`、`external_action=none` | ES 命令、限流或降级已经执行 |

## 拒绝的替代方案

- 写死 QPS、48 个 UNASSIGNED、命令或固定检查字符串后自证：拒绝。合法来源变化必须动态进入 outcome、工件与前台。
- 用同一份生成内存对象证明 Markdown/CSV：拒绝。最终 bytes 必须被重新解析。
- 把 `10.1.1.1` 填入命令：拒绝。来源明确它属于 dedicated master，且没有批准协调入口。
- 把官方 API 文档当现场变更批准：拒绝。文档只说明语义和权限/风险边界。
- 用 Artifact 绿灯覆盖冲突、假设不确定性或未执行状态：拒绝。四层事实必须并列。

## 验证门

- canonical 动态解析 232 行日志、三组来源冲突和全部未执行提案；数值只作为当前来源观测，不进入生产 success 常量。
- QPS、节点、分片、索引、慢查询或来源冲突的合法变异更新受影响字段；证据删除会降低假设支持。
- 空、损坏、截断、重复关键章节、非法数字、错来源以及 Markdown/CSV 篡改 fail closed。
- 静态扫描与运行门不得连接 Elasticsearch、curl、Invoke-WebRequest 或执行生成的命令。
- PostgreSQL 重启后 Artifact、EffectReceipt、outcome 与下载字节一致；只证明顺序 Runtime 恢复。
- 1440 px 三栏和 390 px 单栏覆盖 canonical、动态冲突/指标和 Verifier failure；自动化与截图不证明用户理解或生产安全。
