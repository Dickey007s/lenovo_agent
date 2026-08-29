# SCENARIO-035：从固定公开日志形成可复核事故观察与止损提案

## 用户与触发

- 用户：需要先看清离线日志事实、数据冲突、根因假设和安全前置，再决定是否进入生产处置的 SRE。
- 触发：输入“分析双十一 Elasticsearch 日志，给出根因与两个层面的紧急止损建议。”
- 痛点：旧实现把指标、根因、48 个分片和三条命令写死，再检查同一批字符串；合法来源变化后可能假绿或假红，也容易把命令草案误读成已执行回执。

## 主路径

1. Planner 在整库冻结索引中自主选择证据；固定 TC-14 效果门另行冻结批准 `log.txt` 原始字节。
2. 服务端校验逻辑身份、路径、allowlist、大小与结构，逐行生成 Observation 和 locator。
3. 服务端保留日志内部冲突；Hypothesis 明确支持、反证和局限，不把相关性写成已证因果。
4. 服务端生成只读预检、条件式写提案与业务止损提案；所有 ES target 未解析、需审批、未执行。
5. Runtime 在隔离 Run Workspace 生成 Markdown 与 CSV；Verifier 重读日志并重新解析两份最终 bytes。
6. 前台先说明这不是在线监控或命令回执，再分开显示确定性检查、观察/冲突、假设/提案复核和全部动作未发生；用户可展开 locator、反证、前置、回滚与验证。

## 当前固定输入事实

- 当前批准日志 232 行，涉及 3 个索引；逐行列出 11 个节点，3 master、8 data。
- 查询与写入 QPS 都显示为基线的 8 倍；日志含 5 条搜索慢日志、1 条写入慢日志、3 次 transport timeout 后恢复、1 次 circuit reset、1 次 shard-lock 重试成功和一次 snapshot failure 后 cleanup。
- 日志内部存在三组开放冲突：节点总数 `10/11/11`，health UNASSIGNED `48` 对 shard 明细 `24`，data 节点磁盘 `53.9%-56.1%` 对 allocation explain `>85%`。
- 日志中的 `10.1.1.1` 属于 dedicated master；当前没有批准的非 dedicated-master 协调入口。
- 本轮不连接 Elasticsearch，不执行 HTTP/ES 命令，不实施限流、查询降级或其他业务动作，也不修改 FORTE 原件。

## 异常路径

- 缺失、额外、错路径、空、二进制、截断、重复关键章节或非法数字：来源合同失败。
- 未识别日志片段：保留为 `unclassified/manual_review`；若破坏关键结构则 fail closed。
- 合法 QPS、节点、角色、索引或分片变化：动态更新观察、冲突、假设和成果，不与固定答案比较。
- 报告或台账的数字、locator、冲突、支持/反证、风险、目标、回滚、官方参考或执行边界被篡改：独立 Verifier 转红。
- Planner/Analyst 另有安全校验失败：确定性 Artifact/Effect 作为独立事实保留，Run 状态不得冒充完成。

## 完成条件

- 两份工件可下载并独立解析，Observation/Conflict/Hypothesis/Proposal 账本守恒。
- 三组冲突与未解析 endpoint 可见；所有提案保持 approval required、executed false。
- 原日志字节不变，`external_action=none`。
- PostgreSQL 重启后 Snapshot、Artifact、EffectReceipt 与 outcome 保持一致。

## 来源与边界

- 数据来源：FORTE 固定 revision `345c1ec1487139db9dd319787fa9405ba85d1869` 的 `sre-010/input/log.txt`。
- 交互来源：`USER-FEEDBACK-20260829-TC14-SOURCE-DERIVED-SRE-DIAGNOSIS`。
- API 语义来源：`ELASTICSEARCH-7.10-OFFICIAL-SRE-ACTION-SEMANTICS-20260829`。
- 当前只是固定 `SRE-010` 离线复盘与条件式建议适配器，不是在线监控、根因确定器、Elasticsearch Connector、命令执行器、生产变更审批、多 Worker 或用户研究。
