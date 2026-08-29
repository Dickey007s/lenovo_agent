# USER-FEEDBACK-20260829-TC14-SOURCE-DERIVED-SRE-DIAGNOSIS

## 来源

- 类型：Stakeholder 场景审计、交互验收与工程验收边界
- 日期：2026-08-29，Asia/Shanghai
- 场景：FORTE 固定 `SRE-010`，从公开 `log.txt` 生成离线事故复盘、观察台账和条件式止损提案
- 状态：已记录；实现结论由 `DR-0050` 与对应 Evidence 单独验证

## 问题定位

历史 `_sre_diagnosis` 只从日志提取少量 IP，其余 QPS、资源区间、GC/慢查询、48 个 UNASSIGNED、根因、命令和业务措施由生产代码写死，再用相同字符串检查自己。它不能证明来源合法变化会进入结果，也忽略了日志内部的节点、分片和磁盘口径冲突。旧命令还把 dedicated master `10.1.1.1` 当目标，容易让用户把提案误解为批准或执行回执。

Stakeholder 要求把 TC-14 改为来源推导的固定纵切：

1. 严格绑定一份批准日志，逐行保留 observation 与 locator；未知关键片段不得静默消失。
2. Observation 与 Hypothesis 分开；假设必须保留支持、反证和局限，不把同时出现写成已证因果。
3. 三组来源冲突必须被前台显式保留。确定性通过只表示冲突被识别，不表示数据一致。
4. 所有动作必须是安全结构化 proposal，含风险、target、前置、回滚、验证、官方参考、approval required 与 executed false。
5. 不得猜 dedicated master 为 endpoint。没有批准入口时 target 必须 unresolved，不能执行任何 ES/HTTP 命令。
6. Markdown 与 CSV 必须被独立重读验证；动态指标/冲突变化应进入成果，篡改或结构错误必须转红。
7. 前台分开来源与工件验证、观察与冲突、假设/提案待 SRE 复核，以及真实命令和业务止损全部未发生。

## 完成条件

- 当前批准来源动态得到日志行数、节点/角色、指标、恢复事件、冲突、假设和提案；这些只作为当前版本观测，不进入生产 success 常量。
- 合法指标、节点、分片或证据变异只改变受影响事实；错误来源与工件篡改 fail closed。
- 两份成果可下载并独立解析；PostgreSQL 重启后 Snapshot、Artifact、EffectReceipt 与 `sre_diagnosis_outcome` 一致。
- 1440 px 和 390 px 前台显示四层事实、来源 locator、反证和未执行边界，且无横向溢出。

## 局限

这是单一 Stakeholder 的形成性验收，不是 SRE 用户研究、生产事故审批或在线验证。固定 `SRE-010` 适配器不连接集群、不执行命令、不实施业务降级，也不构成通用日志诊断、Connector、多 Worker 或生产安全沙箱。
