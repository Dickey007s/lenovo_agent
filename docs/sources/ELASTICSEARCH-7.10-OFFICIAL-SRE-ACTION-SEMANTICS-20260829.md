# ELASTICSEARCH-7.10-OFFICIAL-SRE-ACTION-SEMANTICS-20260829

## 来源与用途

- 发布者：Elastic
- 版本：Elasticsearch Guide 7.10；页面已明确停止更新
- 访问日期：2026-08-29
- 用途：限定 TC-14 中节点角色、reroute、allocation、refresh、cache clear 与 allocation explain 的 API 语义和风险文案
- 不支持的推断：这些页面不证明当前日志来自真实生产集群，不批准任何 endpoint、参数或变更，也不证明提案已执行

## 官方页面

1. [Node roles](https://www.elastic.co/guide/en/elasticsearch/reference/7.10/modules-node.html)：7.10 文档说明 dedicated master 应聚焦集群管理，较好实践是不把它用作客户端搜索/索引协调入口。
2. [Cluster reroute API](https://www.elastic.co/guide/en/elasticsearch/reference/7.10/cluster-reroute.html)：说明 reroute 会改变分片分配，需要 `manage` cluster privilege；支持 `dry_run`、`explain`，`retry_failed` 只在问题修复后重试一轮。
3. [Cluster-level shard allocation settings](https://www.elastic.co/guide/en/elasticsearch/reference/7.10/modules-cluster.html)：说明 shard allocation 与动态 allocation settings 的语义，不能据此断言现场应该写入 `allocation.enable=all`。
4. [Index modules](https://www.elastic.co/guide/en/elasticsearch/reference/7.10/index-modules.html)：用于解释 index-level refresh 等设置；TC-14 必须先读取当前值和业务 SLA，并保存精确 rollback 原值。
5. [Clear cache API](https://www.elastic.co/guide/en/elasticsearch/reference/7.10/indices-clearcache.html)：用于解释 cache clear 的权限与目标语义；TC-14 只允许 index-scoped 条件式提案，且要有 fielddata stats 支持。
6. [Cluster allocation explain API](https://www.elastic.co/guide/en/elasticsearch/reference/7.10/cluster-allocation-explain.html)：用于只读预检分片为何未分配；它不证明日志中的 allocation explanation 与当前集群一致。

## 版本边界

Elastic 页面明确提示 7.10 文档不再更新。这里选择 7.10 是因为固定公开日志自述 Elasticsearch 7.10.2；若进入真实生产处置，必须重新核验实际版本、当前官方文档、权限、目标、审批与回滚，而不是复用本 Evidence。
