"""Source-derived SRE-010 incident review artifacts and independent verifier.

The fixed adapter parses only the approved offline log. It never opens a
network connection, never runs a command, and never treats a proposed command
as an execution receipt. Observations, conflicts, hypotheses, and proposals are
kept as separate server-owned facts.
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
from dataclasses import dataclass

from packages.contracts.harness_models import (
    AgentControlLoopSREActionProposal,
    AgentControlLoopSREDiagnosisOutcome,
    AgentControlLoopSREHypothesis,
    AgentControlLoopSREObservation,
    AgentControlLoopSRESourceConflict,
)


SOURCE_LOGICAL_ID = "sre-010-log"
EXPECTED_FILE_NAME = "log.txt"
EXPECTED_DISPLAY_PATH = "可靠性工程/log.txt"
EXPECTED_FILE_REF = "forte-df5ae9b9a1273380"

ELASTIC_NODE_ROLES = "https://www.elastic.co/guide/en/elasticsearch/reference/7.10/modules-node.html"
ELASTIC_REROUTE = "https://www.elastic.co/guide/en/elasticsearch/reference/7.10/cluster-reroute.html"
ELASTIC_ALLOCATION = "https://www.elastic.co/guide/en/elasticsearch/reference/7.10/modules-cluster.html"
ELASTIC_INDEX_MODULES = "https://www.elastic.co/guide/en/elasticsearch/reference/7.10/index-modules.html"
ELASTIC_CLEAR_CACHE = "https://www.elastic.co/guide/en/elasticsearch/reference/7.10/indices-clearcache.html"
ELASTIC_ALLOCATION_EXPLAIN = "https://www.elastic.co/guide/en/elasticsearch/reference/7.10/cluster-allocation-explain.html"
REFERENCE_BOUNDARY = (
    "Elasticsearch 7.10 官方文档仅用于解释 API 语义，访问日期 2026-08-29；"
    "不证明这些操作已获得当前现场批准，也不证明目标集群状态与日志相同。"
)
EXECUTION_BOUNDARY = (
    "这是固定公开日志的离线事故复盘与止损提案，不是在线监控、根因定论或命令执行回执。"
    "没有连接 Elasticsearch，没有执行 HTTP/ES 命令，也没有实施业务降级。"
)
TARGET_RATIONALE = (
    "日志中的 10.1.1.1 是 dedicated master，不能据此选择为客户端协调入口；"
    "所有 Elasticsearch 提案都等待 SRE 提供非 dedicated-master 的批准协调入口。"
)

LEDGER_HEADERS = (
    "记录类型",
    "记录ID",
    "状态",
    "标题或陈述",
    "来源位置",
    "原文",
    "结构化字段",
    "支持或冲突A",
    "反证或冲突B",
    "风险等级",
    "目标状态",
    "前置条件",
    "回滚或停止条件",
    "执行后验证",
    "官方参考",
    "需审批",
    "已执行",
)


class SREDiagnosisValidationError(ValueError):
    """The fixed SRE-010 source or generated artifact contract is invalid."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class SRESourceInput:
    logical_id: str
    file_name: str
    display_path: str
    file_ref: str
    content: bytes
    declared_size: int
    allowlist_verified: bool


@dataclass(frozen=True)
class SREArtifactCheck:
    check_id: str
    label: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class SREDiagnosisBuild:
    report_markdown: bytes
    ledger_csv: bytes
    outcome: AgentControlLoopSREDiagnosisOutcome
    checks: tuple[SREArtifactCheck, ...]


@dataclass(frozen=True)
class _Line:
    number: int
    text: str

    @property
    def locator(self) -> str:
        return f"log.txt:L{self.number}"


def build_sre_diagnosis(source: SRESourceInput) -> SREDiagnosisBuild:
    outcome = analyze_sre_source(source)
    report = _render_markdown(outcome)
    ledger = _render_ledger(outcome)
    checks = verify_sre_artifacts(source, report_markdown=report, ledger_csv=ledger)
    return SREDiagnosisBuild(
        report_markdown=report,
        ledger_csv=ledger,
        outcome=outcome,
        checks=checks,
    )


def analyze_sre_source(source: SRESourceInput) -> AgentControlLoopSREDiagnosisOutcome:
    _validate_source_contract(source)
    lines = _decode_lines(source.content)
    by_number = {line.number: line for line in lines}
    _validate_sections(lines)

    observations: list[AgentControlLoopSREObservation] = []
    observed_lines: set[int] = set()

    def add(
        observation_id: str,
        category: str,
        line_numbers: int | tuple[int, ...],
        statement: str,
        **fields: object,
    ) -> AgentControlLoopSREObservation:
        numbers = (line_numbers,) if isinstance(line_numbers, int) else line_numbers
        missing = [number for number in numbers if number not in by_number]
        if missing:
            raise SREDiagnosisValidationError(
                "source-line", f"日志缺少用于结构化事实的行：{missing}"
            )
        observed_lines.update(numbers)
        excerpt = "\n".join(by_number[number].text for number in numbers)
        locator = (
            by_number[numbers[0]].locator
            if len(numbers) == 1
            else f"log.txt:L{numbers[0]}-L{numbers[-1]}"
        )
        item = AgentControlLoopSREObservation(
            observation_id=f"sre-observation-{observation_id}",
            category=category,
            statement=statement,
            source_file_ref=source.file_ref,
            locator=locator,
            excerpt=excerpt,
            fields={key: _stringify(value) for key, value in fields.items()},
        )
        observations.append(item)
        return item

    alert_line, alert_match = _unique_line_match(lines, r"^告警ID:\s*(\S+)$", "alert-id")
    alert_id = alert_match.group(1)
    occurred_line, occurred_match = _unique_line_match(lines, r"^发生时间:\s*(\S+)", "occurred-at")
    occurred_at = occurred_match.group(1)
    duration_line, duration_match = _unique_line_match(lines, r"^持续时间:\s*(.+)$", "duration")
    duration = duration_match.group(1)
    affected_line, affected = _unique_line_match(
        lines,
        r"^受影响资源:\s*cluster:\s*([^,]+),\s*indices:\s*\[([^]]+)\]$",
        "affected-resources",
    )
    cluster_name = affected.group(1).strip()
    indices = tuple(item.strip() for item in affected.group(2).split(",") if item.strip())
    if not indices or len(indices) != len(set(indices)):
        raise SREDiagnosisValidationError("indices", "受影响索引为空或重复。")
    add("alert", "metadata", alert_line.number, f"告警 {alert_id}", alert_id=alert_id)
    add("time", "metadata", occurred_line.number, f"告警发生于 {occurred_at}", occurred_at=occurred_at)
    add("duration", "metadata", duration_line.number, duration, duration=duration)
    affected_obs = add(
        "affected-resources",
        "cluster",
        affected_line.number,
        f"受影响集群 {cluster_name}，索引 {len(indices)} 个。",
        cluster=cluster_name,
        indices=",".join(indices),
    )

    metric_patterns = {
        "query_qps": r"query_qps: 峰值 ([0-9.]+)/s（正常基线 ([0-9.]+)/s，激增 ([0-9.]+) 倍）",
        "write_qps": r"index_qps: 峰值 ([0-9.]+)/s（正常基线 ([0-9.]+)/s，激增 ([0-9.]+) 倍）",
        "cpu": r"cpu\.busy: 峰值 ([0-9.]+)%（阈值 ([0-9.]+)%.*?([0-9]+) 个 data",
        "disk_io": r"disk\.io\.util/device=max: 峰值 ([0-9.]+)%（阈值 ([0-9.]+)%",
        "heap": r"heap_used_percent: 峰值 ([0-9.]+)%（阈值 ([0-9.]+)%",
        "young_gc": r"young\.collection_count\.perMin: 峰值 ([0-9.]+) 次/min（阈值 ([0-9.]+) 次/min）",
        "old_gc": r"old\.collection_count\.perMin: 峰值 ([0-9.]+) 次/min（阈值 ([0-9.]+) 次/min）",
        "old_gc_time": r"old\.collection_time_in_millis\.perMin: 峰值 ([0-9.]+)ms/min（阈值 ([0-9.]+)ms/min）",
        "search_latency": r"query_time_in_millis\.avg: 峰值 ([0-9.]+)ms（正常 < ([0-9.]+)ms）",
        "index_latency": r"index_time_in_millis\.avg: 峰值 ([0-9.]+)ms（正常 < ([0-9.]+)ms）",
        "write_rejected": r"write\.rejected\.perMin: 峰值 ([0-9.]+)/min",
        "search_rejected": r"search\.rejected\.perMin: 峰值 ([0-9.]+)/min",
    }
    metrics: dict[str, float] = {}
    metric_observations: dict[str, AgentControlLoopSREObservation] = {}
    for key, pattern in metric_patterns.items():
        line, match = _unique_line_match(lines, pattern, f"metric-{key}")
        values = [_finite_number(value, f"metric-{key}") for value in match.groups()]
        metrics[key] = values[0]
        if key in {"query_qps", "write_qps"}:
            peak, baseline, stated_multiplier = values
            if baseline <= 0 or not math.isclose(peak / baseline, stated_multiplier, rel_tol=1e-6):
                raise SREDiagnosisValidationError(
                    "metric-multiplier", f"{key} 峰值、基线与倍数不一致。"
                )
            metrics[f"{key}_baseline"] = baseline
            metrics[f"{key}_multiplier"] = stated_multiplier
        metric_observations[key] = add(
            f"metric-{key.replace('_', '-')}",
            "metric",
            line.number,
            line.text.strip(" -"),
            **{f"value_{index + 1}": value for index, value in enumerate(values)},
        )

    deploy_line, deploy_match = _unique_line_match(lines, r"^集群名称:\s*(\S+)$", "deploy-cluster")
    deploy_cluster = deploy_match.group(1)
    version_line, version_match = _unique_line_match(lines, r"^集群版本:\s*Elasticsearch\s+([0-9.]+)$", "version")
    version = version_match.group(1)
    node_total_line, node_total_match = _unique_line_match(lines, r"^节点总数:\s*([0-9]+)$", "node-total")
    declared_nodes = int(node_total_match.group(1))
    if deploy_cluster != cluster_name:
        raise SREDiagnosisValidationError("cluster-conflict", "告警与部署信息的集群名称冲突。")
    add("cluster-name", "cluster", deploy_line.number, f"集群名称 {deploy_cluster}", cluster=deploy_cluster)
    add("cluster-version", "cluster", version_line.number, f"Elasticsearch {version}", version=version)
    declared_obs = add(
        "declared-node-count", "cluster", node_total_line.number, f"部署区声明节点总数 {declared_nodes}。", count=declared_nodes
    )

    node_pattern = re.compile(
        r"^\s*-\s*(es-node-[0-9]+)\s+\((\d+\.\d+\.\d+\.\d+)\):\s*"
        r"roles=\[([^]]+)]\s+机型=(\S+)\s+机房=(\S+)$"
    )
    nodes: list[dict[str, str]] = []
    node_observations: list[AgentControlLoopSREObservation] = []
    for line in lines:
        match = node_pattern.match(line.text)
        if not match:
            continue
        name, ip, role, model, dc = match.groups()
        if name in {item["name"] for item in nodes} or ip in {item["ip"] for item in nodes}:
            raise SREDiagnosisValidationError("duplicate-node", f"节点名称或 IP 重复：{name}/{ip}")
        item = {"name": name, "ip": ip, "role": role, "model": model, "dc": dc}
        nodes.append(item)
        node_observations.append(
            add(
                f"node-{name}",
                "node",
                line.number,
                f"{name} 角色 {role}，IP {ip}。",
                **item,
            )
        )
    if not nodes:
        raise SREDiagnosisValidationError("nodes", "节点清单为空。")
    role_line, role_match = _unique_line_match(
        lines, r"共\s*([0-9]+)\s*master\s*\+\s*([0-9]+)\s*data", "role-summary"
    )
    declared_master, declared_data = map(int, role_match.groups())
    role_obs = add(
        "role-summary",
        "cluster",
        role_line.number,
        f"角色汇总声明 {declared_master} master + {declared_data} data。",
        master=declared_master,
        data=declared_data,
    )
    actual_master = sum(item["role"] == "master" for item in nodes)
    actual_data = sum(item["role"] == "data" for item in nodes)

    index_pattern = re.compile(
        r"^\s*-\s*([^:]+):\s*主分片=([0-9]+),\s*副本=([0-9]+),\s*单分片大小约\s*([0-9.]+)GB$"
    )
    index_configs: list[dict[str, object]] = []
    for line in lines:
        match = index_pattern.match(line.text)
        if not match:
            continue
        name, primaries, replicas, size_gb = match.groups()
        if name.strip() in {item["name"] for item in index_configs}:
            raise SREDiagnosisValidationError("duplicate-index", f"索引配置重复：{name.strip()}")
        item = {
            "name": name.strip(),
            "primaries": int(primaries),
            "replicas": int(replicas),
            "shard_size_gb": _finite_number(size_gb, "index-size"),
        }
        index_configs.append(item)
        add(
            f"index-{_slug(name)}",
            "cluster",
            line.number,
            f"索引 {name.strip()}：{primaries} 主分片，{replicas} 副本。",
            name=name.strip(),
            primaries=primaries,
            replicas=replicas,
            shard_size_gb=size_gb,
        )
    if tuple(item["name"] for item in index_configs) != indices:
        raise SREDiagnosisValidationError("index-set", "告警索引与索引配置集合或顺序不一致。")

    health_line, health = _unique_line_match(
        lines,
        r"^\d+\s+\S+\s+(\S+)\s+(\w+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+"
        r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+\S+\s+([0-9.]+)%$",
        "cat-health-row",
    )
    (
        health_cluster,
        health_status,
        health_nodes,
        health_data_nodes,
        health_shards,
        health_primaries,
        health_relocating,
        health_initializing,
        health_unassigned,
        health_pending,
        active_percent,
    ) = health.groups()
    if health_cluster != cluster_name:
        raise SREDiagnosisValidationError("health-cluster", "health 行的集群名不一致。")
    health_obs = add(
        "health",
        "health",
        health_line.number,
        f"00:38 集群 {health_status}，节点 {health_nodes}，UNASSIGNED {health_unassigned}。",
        status=health_status,
        node_total=health_nodes,
        node_data=health_data_nodes,
        shards=health_shards,
        primaries=health_primaries,
        relocating=health_relocating,
        initializing=health_initializing,
        unassigned=health_unassigned,
        pending=health_pending,
        active_percent=active_percent,
    )
    health_node_count = int(health_nodes)
    health_unassigned_count = int(health_unassigned)

    cat_node_pattern = re.compile(
        r"^(es-node-[0-9]+)\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+)\s+(\d+)\s+"
        r"([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([*-])\s+([md])$"
    )
    cat_nodes: list[dict[str, object]] = []
    for line in lines:
        match = cat_node_pattern.match(line.text)
        if not match:
            continue
        name, ip, cpu, heap, disk, disk_io, load, master_mark, role_mark = match.groups()
        item = {
            "name": name,
            "ip": ip,
            "cpu": int(cpu),
            "heap": int(heap),
            "disk_used": _finite_number(disk, "cat-node-disk"),
            "disk_io": _finite_number(disk_io, "cat-node-io"),
            "load": _finite_number(load, "cat-node-load"),
            "master_mark": master_mark,
            "role": "master" if role_mark == "m" else "data",
        }
        cat_nodes.append(item)
        add(
            f"cat-node-{name}",
            "node",
            line.number,
            f"{name} CPU {cpu}% / heap {heap}% / disk {disk}% / IO {disk_io}%。",
            **item,
        )
    if len(cat_nodes) != len(nodes) or {item["name"] for item in cat_nodes} != {
        item["name"] for item in nodes
    }:
        raise SREDiagnosisValidationError("cat-node-set", "部署节点清单与 cat nodes 集合不一致。")
    if any(
        next(item for item in nodes if item["name"] == cat["name"])["role"] != cat["role"]
        for cat in cat_nodes
    ):
        raise SREDiagnosisValidationError("node-role-conflict", "节点角色在部署区和 cat nodes 中冲突。")
    data_cat_nodes = [item for item in cat_nodes if item["role"] == "data"]

    thread_pattern = re.compile(r"^(es-node-[0-9]+)\s+(write|search)\s+(\d+)\s+(\d+)\s+(\d+)$")
    thread_rows: list[dict[str, object]] = []
    for line in lines:
        match = thread_pattern.match(line.text)
        if not match:
            continue
        node, pool, active, queue, rejected = match.groups()
        item = {
            "node": node,
            "pool": pool,
            "active": int(active),
            "queue": int(queue),
            "rejected": int(rejected),
        }
        thread_rows.append(item)
        add(
            f"thread-{node}-{pool}",
            "thread_pool",
            line.number,
            f"{node} {pool} active={active} queue={queue} rejected={rejected}。",
            **item,
        )
    if not thread_rows or len({(item["node"], item["pool"]) for item in thread_rows}) != len(thread_rows):
        raise SREDiagnosisValidationError("thread-pool", "thread pool 表为空或存在重复键。")

    shard_pattern = re.compile(
        r"^([^\s]+)\s+(\d+)\s+([pr])\s+(STARTED|UNASSIGNED)\s+(.+)$"
    )
    shard_rows: list[dict[str, object]] = []
    for line in lines:
        match = shard_pattern.match(line.text)
        if not match:
            continue
        index_name, shard, prirep, state, node = match.groups()
        item = {
            "index": index_name,
            "shard": int(shard),
            "prirep": prirep,
            "state": state,
            "node": node.strip(),
        }
        key = (index_name, int(shard), prirep)
        if key in {(row["index"], row["shard"], row["prirep"]) for row in shard_rows}:
            raise SREDiagnosisValidationError("duplicate-shard", f"分片行重复：{key}")
        shard_rows.append(item)
        add(
            f"shard-{_slug(index_name)}-{shard}-{prirep}",
            "shard",
            line.number,
            f"{index_name} shard {shard} {prirep} = {state}。",
            **item,
        )
    if not shard_rows:
        raise SREDiagnosisValidationError("shards", "cat shards 明细为空。")
    detail_unassigned = sum(item["state"] == "UNASSIGNED" for item in shard_rows)
    detail_primaries = sum(item["prirep"] == "p" for item in shard_rows)

    allocation_line, allocation_match = _unique_line_match(
        lines,
        r'^\s*"allocate_explanation":\s*"(.+)"$',
        "allocation-explanation",
    )
    allocation_text = allocation_match.group(1)
    disk_threshold_match = re.search(r"above\s+([0-9.]+)%\s+threshold", allocation_text)
    if not disk_threshold_match:
        raise SREDiagnosisValidationError("allocation-threshold", "allocation explain 缺少磁盘阈值。")
    allocation_threshold = _finite_number(disk_threshold_match.group(1), "allocation-threshold")
    allocation_reason_line, allocation_reason_match = _unique_line_match(lines, r'^\s*"reason":\s*"([A-Z_]+)"', "allocation-reason")
    allocation_reason = allocation_reason_match.group(1)
    allocation_status_line, allocation_status_match = _unique_line_match(
        lines, r'^\s*"last_allocation_status":\s*"([^\"]+)"', "allocation-status"
    )
    allocation_status = allocation_status_match.group(1)
    can_allocate_line, can_allocate_match = _unique_line_match(lines, r'^\s*"can_allocate":\s*"([^\"]+)"', "can-allocate")
    can_allocate = can_allocate_match.group(1)
    allocation_numbers = tuple(
        range(
            min(allocation_reason_line.number, allocation_status_line.number, can_allocate_line.number),
            allocation_line.number + 1,
        )
    )
    allocation_obs = add(
        "allocation-explain",
        "allocation",
        allocation_numbers,
        f"allocation explain：{allocation_reason} / {allocation_status} / {can_allocate}，并称磁盘高于 {allocation_threshold}%。",
        reason=allocation_reason,
        last_status=allocation_status,
        can_allocate=can_allocate,
        disk_threshold=allocation_threshold,
    )
    # The block excerpt is useful evidence, but consuming every line would hide an
    # unknown normative or diagnostic fragment inserted between known JSON fields.
    # Leave non-core lines available to the unclassified-observation pass below.
    allocation_core_numbers = {
        allocation_reason_line.number,
        allocation_status_line.number,
        can_allocate_line.number,
        allocation_line.number,
    }
    observed_lines.difference_update(set(allocation_numbers) - allocation_core_numbers)

    event_specs = (
        ("transport-timeout", "recovery", "timeout waiting for", "传输响应超时"),
        ("transport-restored", "recovery", "connection restored", "传输重试后恢复"),
        ("gc", "gc", "JvmGcMonitorService", "GC 事件"),
        ("queue-rejected", "queue", "queue capacity reached", "线程池队列拒绝"),
        ("search-slow", "slow_query", "SearchSlowLog", "搜索慢日志"),
        ("index-slow", "slow_query", "IndexingSlowLog", "写入慢日志"),
        ("snapshot-failed", "side_event", "failed to create snapshot", "快照创建失败"),
        ("snapshot-cleanup", "recovery", "snapshot deleted successfully", "快照失败后的清理完成"),
        ("circuit-open", "side_event", "CircuitBreakingException", "熔断器触发"),
        ("circuit-reset", "recovery", "circuit breaker reset", "熔断器复位"),
        ("shard-lock-failed", "side_event", "failed to obtain shard lock", "分片锁获取失败"),
        ("shard-lock-success", "recovery", "shard lock obtained successfully", "分片锁重试成功"),
        ("license", "side_event", "license will expire", "License 到期提醒"),
    )
    event_counts: dict[str, int] = {}
    for prefix, category, token, label in event_specs:
        matching = [line for line in lines if token.lower() in line.text.lower()]
        event_counts[prefix] = len(matching)
        for index, line in enumerate(matching, 1):
            add(
                f"event-{prefix}-{index}",
                category,
                line.number,
                f"{label}：{line.text[:300]}",
                event_type=prefix,
            )

    query_evidence: list[AgentControlLoopSREObservation] = []
    for line in lines:
        flags = []
        if re.search(r'"from":\s*[1-9][0-9]*', line.text):
            flags.append("deep_pagination")
        if '"aggs"' in line.text or '"terms"' in line.text or '"date_histogram"' in line.text:
            flags.append("aggregation")
        if not flags:
            continue
        query_evidence.append(
            add(
                f"query-{line.number}",
                "query",
                line.number,
                f"查询形态包含：{','.join(flags)}。",
                flags=",".join(flags),
            )
        )

    known_nonempty = observed_lines | {
        line.number
        for line in lines
        if (
            not line.text.strip()
            or set(line.text.strip()) == {"="}
            or line.text.startswith("[") and "日志片段" in line.text
            or line.text in {
                "[系统告警元数据]",
                "告警指标:",
                "节点角色分布:",
                "索引配置:",
                "GET /_cat/health?v",
                "GET /_cat/nodes?v&h=name,ip,cpu,heap.percent,disk.used_percent,disk.io.util,load_1m,master,node.role",
                "GET /_cat/thread_pool/write,search?v&h=node_name,name,active,queue,rejected",
                "GET /_cat/shards?v&h=index,shard,prirep,state,node&s=state",
                "GET /_cluster/settings",
                "GET /_nodes/stats/thread_pool?filter_path=nodes.*.name,nodes.*.thread_pool.write,nodes.*.thread_pool.search",
                "GET /_cluster/allocation/explain",
                "{",
                "}",
                "\"persistent\": {}",
                "\"transient\": {}",
                "\"nodes\": {",
                "\"node-04-id\": {",
                "\"name\": \"es-node-04\"",
                "\"thread_pool\": {",
            }
            or re.match(r"^(epoch|name\s+ip|node_name\s+name|index\s+shard)", line.text)
            or re.match(r"^\s*\"(index|shard|primary|current_state|at|details)\"", line.text)
            or re.match(r"^\s*\"(write|search)\":\s*\{", line.text)
            or line.text.startswith("org.elasticsearch")
            or line.text.startswith("    at ")
        )
    }
    for line in lines:
        if line.number in known_nonempty or not line.text.strip():
            continue
        observations.append(
            AgentControlLoopSREObservation(
                observation_id=f"sre-observation-unclassified-{line.number}",
                category="unclassified",
                statement="固定适配器未分类的日志片段，需要 SRE 人工判断。",
                source_file_ref=source.file_ref,
                locator=line.locator,
                excerpt=line.text,
                fields={},
                status="unclassified",
            )
        )

    conflicts: list[AgentControlLoopSRESourceConflict] = []
    listed_obs_ids = [item.observation_id for item in node_observations]
    if len(nodes) != declared_nodes or declared_nodes != declared_master + declared_data or health_node_count != declared_nodes:
        conflicts.append(
            AgentControlLoopSRESourceConflict(
                conflict_id="sre-conflict-node-count",
                title="节点总数口径冲突",
                statement=(
                    f"部署区声明 {declared_nodes} 个，逐行列出 {len(nodes)} 个，角色汇总为 "
                    f"{declared_master}+{declared_data}={declared_master + declared_data} 个，health 为 {health_node_count} 个。"
                ),
                side_a_observation_ids=[declared_obs.observation_id],
                side_b_observation_ids=[*listed_obs_ids, role_obs.observation_id, health_obs.observation_id],
                locators=[declared_obs.locator, f"log.txt:L{min(item.number for item in lines if node_pattern.match(item.text))}-L{max(item.number for item in lines if node_pattern.match(item.text))}", health_obs.locator],
                impact="节点容量口径不一致，不能据此确定容量缺口或变更范围。",
                status="open",
            )
        )
    if health_unassigned_count != detail_unassigned:
        conflicts.append(
            AgentControlLoopSRESourceConflict(
                conflict_id="sre-conflict-unassigned-count",
                title="UNASSIGNED 分片计数冲突",
                statement=f"health 报告 {health_unassigned_count}，cat shards 明细仅列出 {detail_unassigned}。",
                side_a_observation_ids=[health_obs.observation_id],
                side_b_observation_ids=[
                    item.observation_id for item in observations if item.category == "shard"
                ],
                locators=[health_obs.locator, f"log.txt:L{min(item.number for item in lines if shard_pattern.match(item.text))}-L{max(item.number for item in lines if shard_pattern.match(item.text))}"],
                impact="必须先确认诊断输出是否为完整快照，不能把 48 直接当作已逐项定位的副本数。",
                status="open",
            )
        )
    max_disk_used = max(float(item["disk_used"]) for item in data_cat_nodes)
    if max_disk_used < allocation_threshold and "high disk usage" in allocation_text:
        conflicts.append(
            AgentControlLoopSRESourceConflict(
                conflict_id="sre-conflict-disk-threshold",
                title="磁盘使用率解释冲突",
                statement=(
                    f"cat nodes 的 data 节点 disk.used 为 {min(float(item['disk_used']) for item in data_cat_nodes):.1f}%"
                    f"-{max_disk_used:.1f}%，allocation explain 却称高于 {allocation_threshold:.1f}% 阈值。"
                ),
                side_a_observation_ids=[
                    item.observation_id
                    for item in observations
                    if item.observation_id.startswith("sre-observation-cat-node-")
                ],
                side_b_observation_ids=[allocation_obs.observation_id],
                locators=[f"log.txt:L{min(item.number for item in lines if cat_node_pattern.match(item.text))}-L{max(item.number for item in lines if cat_node_pattern.match(item.text))}", allocation_obs.locator],
                impact="磁盘容量是否阻塞分配仍待实时只读预检，不能直接修改 allocation setting。",
                status="open",
            )
        )

    support_categories = {"metric", "gc", "queue", "slow_query", "query"}
    main_support = [
        item for item in observations if item.category in support_categories and item.status == "observed"
    ]
    counter_items = [allocation_obs, *[item for item in observations if item.fields.get("event_type") == "transport-restored"]]
    confidence = "medium" if {item.category for item in main_support} >= {"metric", "gc", "queue", "slow_query"} else "low"
    hypotheses = [
        AgentControlLoopSREHypothesis(
            hypothesis_id="sre-hypothesis-capacity-query-amplification",
            statement=(
                "QPS 激增、data 节点资源饱和、GC/队列拒绝/慢查询并发出现，"
                "支持容量与查询形态共同放大的假设；这不是已证明的单一因果结论。"
            ),
            confidence=confidence,
            supporting_observation_ids=[item.observation_id for item in main_support],
            supporting_locators=[item.locator for item in main_support],
            counter_evidence_ids=[item.observation_id for item in counter_items],
            counter_evidence_locators=[item.locator for item in counter_items],
            limitations=[
                "只有离线日志片段，没有实时 metrics、完整查询采样或配置变更史。",
                "NODE_LEFT 与三组来源冲突可能改变容量和分片解释。",
                "相关事件同时出现不等于单一因果关系已证。",
            ],
        ),
        AgentControlLoopSREHypothesis(
            hypothesis_id="sre-hypothesis-node-left-allocation",
            statement="NODE_LEFT 与 allocation throttled 支持副本恢复受阻的次级假设，但磁盘口径冲突使具体阻塞原因待核实。",
            confidence="low",
            supporting_observation_ids=[allocation_obs.observation_id, health_obs.observation_id],
            supporting_locators=[allocation_obs.locator, health_obs.locator],
            counter_evidence_ids=[
                item.observation_id
                for item in observations
                if item.observation_id.startswith("sre-observation-cat-node-")
            ],
            counter_evidence_locators=[
                item.locator
                for item in observations
                if item.observation_id.startswith("sre-observation-cat-node-")
            ],
            limitations=["日志没有批准入口、实时 allocation decision 或节点离线原因。"],
        ),
    ]

    source_ids = list(dict.fromkeys(item.observation_id for item in main_support))
    endpoint = "{approved_non_master_endpoint}"
    action_proposals = [
        _command_proposal(
            "read-cluster-settings",
            "read_only_preflight",
            "读取集群设置与默认值",
            "low",
            f"GET {endpoint}/_cluster/settings?include_defaults=true&flat_settings=true",
            ["SRE 提供并批准非 dedicated-master 的协调入口", "只读权限已确认"],
            "只读请求无需回滚；若入口或权限不匹配立即停止。",
            ["保存 settings 响应与时间戳", "核对 allocation.enable 当前值而非猜测"],
            ELASTIC_ALLOCATION,
            source_ids,
        ),
        _command_proposal(
            "read-allocation-explain",
            "read_only_preflight",
            "重新读取 allocation explain",
            "low",
            f"POST {endpoint}/_cluster/allocation/explain?include_yes_decisions=true&include_disk_info=true\n"
            '{"index":"' + str(index_configs[0]["name"]) + '","shard":0,"primary":false}',
            ["SRE 选定仍为 UNASSIGNED 的分片", "只读权限已确认"],
            "只读请求无需回滚；返回结构或分片状态变化时停止后续写提案。",
            ["核对 reason、deciders、disk info 与当前节点状态", "与日志冲突逐项对照"],
            ELASTIC_ALLOCATION_EXPLAIN,
            [health_obs.observation_id, allocation_obs.observation_id],
        ),
        _command_proposal(
            "read-health-nodes-pools",
            "read_only_preflight",
            "读取 health、nodes 与 thread pools",
            "low",
            f"GET {endpoint}/_cluster/health\nGET {endpoint}/_cat/nodes?v\nGET {endpoint}/_cat/thread_pool/write,search?v",
            ["SRE 提供批准入口", "只读权限与采样窗口已确认"],
            "只读请求无需回滚；任何超时或权限异常即停止。",
            ["复核节点数、角色、资源、queue 和 rejected", "记录与离线日志的差异"],
            ELASTIC_NODE_ROLES,
            source_ids,
        ),
        _command_proposal(
            "read-node-stats",
            "read_only_preflight",
            "读取 fielddata、熔断器与恢复状态",
            "low",
            f"GET {endpoint}/_nodes/stats/indices/fielddata,breaker,thread_pool\nGET {endpoint}/_cat/recovery?v",
            ["SRE 提供批准入口", "只读权限已确认"],
            "只读请求无需回滚；响应过大或影响监控时停止。",
            ["判断是否存在 fielddata 证据", "核对 circuit breaker 与 shard recovery"],
            ELASTIC_CLEAR_CACHE,
            source_ids,
        ),
        _command_proposal(
            "read-refresh-settings",
            "read_only_preflight",
            "读取当前 refresh 设置",
            "low",
            f"GET {endpoint}/" + ",".join(indices) + "/_settings?flat_settings=true&include_defaults=true",
            ["SRE 提供批准入口", "只读权限已确认"],
            "只读请求无需回滚；索引集合变化时重新冻结范围。",
            ["逐索引保存 index.refresh_interval 原值", "向业务确认新鲜度 SLA"],
            ELASTIC_INDEX_MODULES,
            [affected_obs.observation_id, *[item.observation_id for item in query_evidence]],
        ),
        _command_proposal(
            "retry-failed",
            "write_change",
            "条件式重试失败分片",
            "high",
            f"POST {endpoint}/_cluster/reroute?retry_failed=true&dry_run=true&explain=true",
            [
                "根因已修复并确认失败重试计数",
                "allocation explain 与 dry_run/explain 已由 SRE 审核",
                "变更审批已通过",
            ],
            "若 dry-run 显示非预期移动、集群负载恶化或失败数增加，停止且不执行真实 reroute。",
            ["复核 UNASSIGNED 数与 allocation deciders", "观察 CPU/heap/IO/queue/rejected"],
            ELASTIC_REROUTE,
            [health_obs.observation_id, allocation_obs.observation_id],
        ),
        _command_proposal(
            "refresh-interval",
            "write_change",
            "条件式调整指定索引 refresh interval",
            "high",
            f"PUT {endpoint}/" + ",".join(indices) + '/_settings\n{"index":{"refresh_interval":"{approved_value}"}}',
            [
                "已读取每个索引当前值",
                "业务新鲜度 SLA 与批准值已确认",
                "精确回滚原值已记录",
                "变更审批已通过",
            ],
            "逐索引恢复本次预检记录的原 refresh_interval；若 SLA 或写入延迟恶化立即回滚。",
            ["复核 refresh、indexing latency、search latency 与业务新鲜度"],
            ELASTIC_INDEX_MODULES,
            [affected_obs.observation_id, metric_observations["index_latency"].observation_id],
        ),
        _command_proposal(
            "fielddata-cache",
            "write_change",
            "有 fielddata 证据时仅清理指定索引字段缓存",
            "high",
            f"POST {endpoint}/{{approved_index}}/_cache/clear?fielddata=true&fields={{approved_fields}}",
            [
                "nodes stats 已证明具体索引/字段的 fielddata 压力",
                "manage 权限、影响和变更审批已确认",
                "禁止省略索引或 fields 范围",
            ],
            "缓存清理不可恢复；如无充分 fielddata 证据、范围不明确或查询延迟恶化则不执行/立即停止。",
            ["复核 fielddata bytes、breaker、GC 与查询延迟", "确认未清理全局缓存"],
            ELASTIC_CLEAR_CACHE,
            [
                item.observation_id
                for item in observations
                if item.fields.get("event_type") in {"circuit-open", "circuit-reset"}
            ],
        ),
    ]
    business_mitigations = [
        _business_proposal(
            "limit-query-qps",
            "按已观测正常基线申请查询侧限流",
            f"申请把查询流量逐步压到日志基线 {metrics['query_qps_baseline']:g}/s，观察后再放量。",
            [metric_observations["query_qps"].observation_id],
        ),
        _business_proposal(
            "limit-write-qps",
            "按已观测正常基线申请写入侧限流",
            f"申请把写入流量逐步压到日志基线 {metrics['write_qps_baseline']:g}/s，观察后再放量。",
            [metric_observations["write_qps"].observation_id],
        ),
        _business_proposal(
            "degrade-expensive-query",
            "暂停深分页与重聚合查询",
            "申请暂停或降级日志已出现的深分页和重聚合查询，并由业务负责人确认影响范围。",
            [item.observation_id for item in query_evidence],
        ),
    ]

    timeline = [
        f"{item.locator} {item.statement}"
        for item in observations
        if item.category in {"metadata", "recovery", "side_event"}
    ]
    cluster_facts = {
        "alert_id": alert_id,
        "occurred_at": occurred_at,
        "duration": duration,
        "cluster": cluster_name,
        "version": version,
        "indices": list(indices),
        "health_status": health_status,
        "health_shards": int(health_shards),
        "health_primaries": int(health_primaries),
        "health_unassigned": health_unassigned_count,
        "detail_rows": len(shard_rows),
        "detail_primaries": detail_primaries,
        "detail_unassigned": detail_unassigned,
    }
    node_facts = {
        "declared_count": declared_nodes,
        "listed_count": len(nodes),
        "listed_master_count": actual_master,
        "listed_data_count": actual_data,
        "declared_master_count": declared_master,
        "declared_data_count": declared_data,
        "health_count": health_node_count,
        "health_data_count": int(health_data_nodes),
        "dedicated_master_ips": [item["ip"] for item in nodes if item["role"] == "master"],
        "data_ips": [item["ip"] for item in nodes if item["role"] == "data"],
        "data_cpu_range": _range([float(item["cpu"]) for item in data_cat_nodes]),
        "data_heap_range": _range([float(item["heap"]) for item in data_cat_nodes]),
        "data_disk_used_range": _range([float(item["disk_used"]) for item in data_cat_nodes]),
        "data_disk_io_range": _range([float(item["disk_io"]) for item in data_cat_nodes]),
    }
    metric_facts = {
        **metrics,
        "gc_event_count": event_counts["gc"],
        "search_slow_count": event_counts["search-slow"],
        "index_slow_count": event_counts["index-slow"],
        "queue_warning_count": event_counts["queue-rejected"],
        "transport_timeout_count": event_counts["transport-timeout"],
        "transport_recovered_count": event_counts["transport-restored"],
        "circuit_reset_count": event_counts["circuit-reset"],
        "shard_lock_retry_success_count": event_counts["shard-lock-success"],
        "snapshot_failure_count": event_counts["snapshot-failed"],
        "snapshot_cleanup_count": event_counts["snapshot-cleanup"],
        "query_evidence_count": len(query_evidence),
    }
    unclassified_count = sum(item.status == "unclassified" for item in observations)
    summary = (
        f"从 {len(lines)} 行批准日志解析 {len(observations)} 条观察、{len(conflicts)} 组来源冲突、"
        f"{len(hypotheses)} 个有边界假设和 {len(action_proposals)} 个 ES 条件式提案；"
        f"目标入口仍为 unresolved，另有 {len(business_mitigations)} 个业务止损提案，均未执行。"
    )
    return AgentControlLoopSREDiagnosisOutcome(
        outcome_id="sre-diagnosis-outcome-sre-010",
        status="incident_review_required",
        decision=(
            "日志事实与成果结构已由服务端重算；三组来源冲突、根因假设、批准入口和所有动作仍需 SRE 复核。"
            "不得把本成果当作生产变更批准或执行回执。"
        ),
        summary=summary,
        source_line_count=len(lines),
        cluster_facts=cluster_facts,
        node_facts=node_facts,
        metric_facts=metric_facts,
        timeline=timeline,
        observation_count=len(observations),
        conflict_count=len(conflicts),
        hypothesis_count=len(hypotheses),
        proposal_count=len(action_proposals),
        business_mitigation_count=len(business_mitigations),
        unclassified_count=unclassified_count,
        observations=observations,
        source_conflicts=conflicts,
        hypotheses=hypotheses,
        action_proposals=action_proposals,
        business_mitigations=business_mitigations,
    )


def verify_sre_artifacts(
    source: SRESourceInput,
    *,
    report_markdown: bytes,
    ledger_csv: bytes,
) -> tuple[SREArtifactCheck, ...]:
    """Re-read the approved source, then independently parse both final artifacts."""

    expected = analyze_sre_source(source)
    expected_report = _render_markdown(expected)
    expected_rows = _ledger_rows(expected)
    csv_valid, actual_rows, csv_detail = _parse_ledger(ledger_csv)
    markdown_valid, markdown_facts, markdown_detail = _parse_markdown(report_markdown)
    observation_ids = [item.observation_id for item in expected.observations]
    conflict_ids = [item.conflict_id for item in expected.source_conflicts]
    hypothesis_ids = [item.hypothesis_id for item in expected.hypotheses]
    proposal_ids = [item.proposal_id for item in (*expected.action_proposals, *expected.business_mitigations)]
    locators = {item.locator for item in expected.observations}
    report_text = str(markdown_facts.get("text") or "")
    safety_tokens = (
        EXECUTION_BOUNDARY,
        TARGET_RATIONALE,
        REFERENCE_BOUNDARY,
        "approval_required=true",
        "executed=false",
        "external_action=none",
    )
    checks = (
        _check(
            "check-sre-source-contract-v2",
            "唯一批准日志合同",
            source.allowlist_verified,
            "SRE-010 的 logical ID、文件名、展示路径、file_ref、声明大小、UTF-8 字节与章节完整性已校验。",
        ),
        _check(
            "check-sre-observations-v2",
            "观察由原始日志动态重算",
            markdown_valid and markdown_facts.get("observations") == observation_ids,
            f"报告必须逐项列出 {len(observation_ids)} 条来源观察；{markdown_detail}",
        ),
        _check(
            "check-sre-conflicts-v2",
            "来源冲突被完整保留",
            markdown_valid and markdown_facts.get("conflicts") == conflict_ids,
            f"报告必须保留 {len(conflict_ids)} 组动态冲突，不能写成数据一致。",
        ),
        _check(
            "check-sre-hypotheses-v2",
            "假设与观察事实分离",
            markdown_valid and markdown_facts.get("hypotheses") == hypothesis_ids,
            "每个假设必须保留支持、反证、置信度和局限，不能把相关性写成已证因果。",
        ),
        _check(
            "check-sre-proposals-v2",
            "动作提案保持审批与未执行状态",
            markdown_valid and markdown_facts.get("proposals") == proposal_ids,
            "所有 ES 与业务提案必须逐项列出风险、未解析目标、前置、回滚、验证、审批和未执行回执。",
        ),
        _check(
            "check-sre-ledger-v2",
            "观察与动作台账可独立解析",
            csv_valid and actual_rows == expected_rows,
            f"CSV 必须逐字段覆盖观察、冲突、假设和提案且无缺行、重复行或状态漂移；{csv_detail}",
        ),
        _check(
            "check-sre-locators-v2",
            "日志原文位置可回开",
            markdown_valid and locators.issubset(set(markdown_facts.get("locators") or [])),
            f"成果必须保留 {len(locators)} 个服务端日志 locator。",
        ),
        _check(
            "check-sre-dynamic-metrics-v2",
            "指标与事件数量由来源复算",
            markdown_valid and markdown_facts.get("metric_facts") == expected.metric_facts,
            "QPS、节点、资源、GC、慢查询、拒绝、分片和恢复事件不得使用旧固定常量。",
        ),
        _check(
            "check-sre-target-v2",
            "dedicated master 未被当作建议目标",
            TARGET_RATIONALE in report_text
            and all(item.target_status != "unresolved" or "10.1.1.1:9200" not in (item.command_template or "") for item in expected.action_proposals),
            "日志中的 dedicated master 只作为来源事实；所有 ES proposal 等待批准的非 master 协调入口。",
        ),
        _check(
            "check-sre-official-references-v2",
            "官方 API 参考与现场批准分离",
            all(
                reference in report_text
                for reference in (
                    ELASTIC_NODE_ROLES,
                    ELASTIC_REROUTE,
                    ELASTIC_ALLOCATION,
                    ELASTIC_INDEX_MODULES,
                    ELASTIC_CLEAR_CACHE,
                )
            ) and REFERENCE_BOUNDARY in report_text,
            "官方文档只解释 Elasticsearch 7.10 API 语义，不作为当前现场执行批准。",
        ),
        _check(
            "check-sre-no-execution-v2",
            "无命令或业务降级执行",
            all(token in report_text for token in safety_tokens)
            and all(item.approval_required and not item.executed for item in (*expected.action_proposals, *expected.business_mitigations)),
            "Adapter 只生成本地 Markdown/CSV；没有连接集群、发送 HTTP、执行 ES 命令或实施业务限流。",
        ),
        _check(
            "check-sre-canonical-bytes-v2",
            "两份成果为来源重算后的规范字节",
            report_markdown == expected_report and csv_valid and actual_rows == expected_rows,
            "Verifier 重新读取批准日志并解析最终 Markdown/CSV；任一数字、locator、冲突、证据或安全字段变化均转红。",
        ),
    )
    return checks


def _validate_source_contract(source: SRESourceInput) -> None:
    if source.logical_id != SOURCE_LOGICAL_ID:
        raise SREDiagnosisValidationError("logical-id", "SRE-010 来源 logical ID 不正确。")
    if source.file_name != EXPECTED_FILE_NAME:
        raise SREDiagnosisValidationError("file-name", "SRE-010 来源文件名不正确。")
    if source.display_path != EXPECTED_DISPLAY_PATH:
        raise SREDiagnosisValidationError("display-path", "SRE-010 来源展示路径不正确。")
    if source.file_ref != EXPECTED_FILE_REF:
        raise SREDiagnosisValidationError("file-ref", "SRE-010 来源 file_ref 不正确。")
    if not source.allowlist_verified:
        raise SREDiagnosisValidationError("allowlist", "SRE-010 来源未通过服务端 allowlist。")
    if not source.content:
        raise SREDiagnosisValidationError("empty", "SRE-010 日志为空。")
    if source.declared_size != len(source.content):
        raise SREDiagnosisValidationError("declared-size", "SRE-010 声明大小与冻结字节不一致。")


def _decode_lines(content: bytes) -> tuple[_Line, ...]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SREDiagnosisValidationError("encoding", "SRE-010 日志必须是有效 UTF-8 文本。") from exc
    if "\x00" in text:
        raise SREDiagnosisValidationError("binary", "SRE-010 日志包含 NUL 或二进制内容。")
    control_count = sum(ord(character) < 32 and character not in "\r\n\t" for character in text)
    if control_count:
        raise SREDiagnosisValidationError("control", "SRE-010 日志包含不允许的控制字符。")
    lines = tuple(_Line(index, value.rstrip("\r")) for index, value in enumerate(text.splitlines(), 1))
    if len(lines) < 100 or not lines[-1].text.strip().endswith("}"):
        raise SREDiagnosisValidationError("truncated", "SRE-010 日志疑似截断或关键尾段缺失。")
    return lines


def _validate_sections(lines: tuple[_Line, ...]) -> None:
    headings = [line.text for line in lines if line.text.startswith("[") and line.text.endswith("]")]
    required = ["[系统告警元数据]", *[f"[日志片段 {index}:" for index in range(1, 10)]]
    if headings.count("[系统告警元数据]") != 1:
        raise SREDiagnosisValidationError("section", "系统告警元数据章节缺失或重复。")
    for prefix in required[1:]:
        if sum(item.startswith(prefix) for item in headings) != 1:
            raise SREDiagnosisValidationError("section", f"关键日志章节缺失或重复：{prefix}")


def _unique_line_match(
    lines: tuple[_Line, ...], pattern: str, code: str
) -> tuple[_Line, re.Match[str]]:
    regex = re.compile(pattern)
    matches = [(line, match) for line in lines if (match := regex.search(line.text))]
    if len(matches) != 1:
        raise SREDiagnosisValidationError(code, f"日志字段 {code} 必须唯一，实际 {len(matches)}。")
    return matches[0]


def _unique_match(lines: tuple[_Line, ...], pattern: str, code: str) -> re.Match[str]:
    return _unique_line_match(lines, pattern, code)[1]


def _unique_group(lines: tuple[_Line, ...], pattern: str, code: str) -> str:
    return _unique_match(lines, pattern, code).group(1).strip()


def _finite_number(raw: str, code: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise SREDiagnosisValidationError(code, f"日志数字无效：{raw}") from exc
    if not math.isfinite(value) or value < 0:
        raise SREDiagnosisValidationError(code, f"日志数字必须是非负有限值：{raw}")
    return value


def _command_proposal(
    suffix: str,
    kind: str,
    title: str,
    risk: str,
    command: str,
    preconditions: list[str],
    rollback: str,
    verify_after: list[str],
    reference: str,
    source_ids: list[str],
) -> AgentControlLoopSREActionProposal:
    return AgentControlLoopSREActionProposal(
        proposal_id=f"sre-proposal-{suffix}",
        kind=kind,
        title=title,
        risk_level=risk,
        command_template=command,
        target_status="unresolved",
        target_rationale=TARGET_RATIONALE,
        preconditions=preconditions,
        rollback=rollback,
        verify_after=verify_after,
        official_reference=f"{reference} (Elasticsearch 7.10; accessed 2026-08-29)",
        source_observation_ids=list(dict.fromkeys(source_ids)),
    )


def _business_proposal(
    suffix: str,
    title: str,
    action_text: str,
    source_ids: list[str],
) -> AgentControlLoopSREActionProposal:
    return AgentControlLoopSREActionProposal(
        proposal_id=f"sre-proposal-{suffix}",
        kind="business_mitigation",
        title=title,
        risk_level="medium",
        action_text=action_text,
        target_status="not_applicable",
        target_rationale="这是业务侧止损提案，不使用 Elasticsearch endpoint。",
        preconditions=["业务负责人确认影响范围与回退标准", "SRE 提供观察窗口与放量门槛"],
        rollback="按审批记录恢复原流量或查询能力；若错误率或收入指标恶化立即停止。",
        verify_after=["观察请求量、错误率、延迟和业务关键指标", "记录批准人与实际执行系统回执"],
        source_observation_ids=list(dict.fromkeys(source_ids)),
    )


def _render_markdown(outcome: AgentControlLoopSREDiagnosisOutcome) -> bytes:
    lines = [
        "# ES 故障诊断与止损建议",
        "",
        EXECUTION_BOUNDARY,
        "",
        f"> {outcome.decision}",
        "",
        "## 来源概览",
        f"- 来源行数：{outcome.source_line_count}",
        f"- 集群：{outcome.cluster_facts.get('cluster')}",
        f"- 版本：Elasticsearch {outcome.cluster_facts.get('version')}",
        f"- 索引：{', '.join(outcome.cluster_facts.get('indices') or [])}",
        f"- 观察：{outcome.observation_count}；来源冲突：{outcome.conflict_count}；未分类：{outcome.unclassified_count}",
        "",
        "## 时间线与观察",
        "| 观察ID | 类别 | 来源位置 | 观察事实 | 原文 |",
        "| --- | --- | --- | --- | --- |",
        *[
            f"| {item.observation_id} | {item.category} | {item.locator} | {_md(item.statement)} | {_md(item.excerpt)} |"
            for item in outcome.observations
        ],
        "",
        "## 来源冲突",
        "| 冲突ID | 状态 | 冲突事实 | 两端观察 | 来源位置 | 影响 |",
        "| --- | --- | --- | --- | --- | --- |",
        *[
            f"| {item.conflict_id} | {item.status} | {_md(item.statement)} | "
            f"{_md(','.join(item.side_a_observation_ids))} ↔ {_md(','.join(item.side_b_observation_ids))} | "
            f"{_md(','.join(item.locators))} | {_md(item.impact)} |"
            for item in outcome.source_conflicts
        ],
        "",
        "## 根因假设与反证",
        *[
            "\n".join(
                (
                    f"### {item.hypothesis_id}",
                    f"- 置信度：{item.confidence}",
                    f"- 假设：{item.statement}",
                    f"- 支持观察：{', '.join(item.supporting_observation_ids)}",
                    f"- 支持位置：{', '.join(item.supporting_locators)}",
                    f"- 反证/待核实：{', '.join(item.counter_evidence_ids)}",
                    f"- 反证位置：{', '.join(item.counter_evidence_locators)}",
                    f"- 局限：{'；'.join(item.limitations)}",
                )
            )
            for item in outcome.hypotheses
        ],
        "",
        "## 只读预检与条件式写提案",
        TARGET_RATIONALE,
        "",
        *[
            "\n".join(
                (
                    f"### {item.proposal_id}｜{item.title}",
                    f"- 类型：{item.kind}；风险：{item.risk_level}；目标：{item.target_status}",
                    f"- 目标理由：{item.target_rationale}",
                    f"- 提案模板（未执行）：`{_md(item.command_template or '')}`",
                    f"- 前置：{'；'.join(item.preconditions)}",
                    f"- 回滚/停止：{item.rollback}",
                    f"- 执行后验证：{'；'.join(item.verify_after)}",
                    f"- 官方参考：{item.official_reference or '无'}",
                    "- approval_required=true；executed=false",
                )
            )
            for item in outcome.action_proposals
        ],
        "",
        "## 业务止损提案",
        *[
            "\n".join(
                (
                    f"### {item.proposal_id}｜{item.title}",
                    f"- 风险：{item.risk_level}",
                    f"- 提案：{item.action_text}",
                    f"- 前置：{'；'.join(item.preconditions)}",
                    f"- 回滚/停止：{item.rollback}",
                    f"- 验证：{'；'.join(item.verify_after)}",
                    "- approval_required=true；executed=false",
                )
            )
            for item in outcome.business_mitigations
        ],
        "",
        "## 动态结构化指标",
        f"```json\n{json.dumps(outcome.metric_facts, ensure_ascii=False, sort_keys=True)}\n```",
        "",
        "## 审批与未执行边界",
        REFERENCE_BOUNDARY,
        "",
        "- resolved_target_count=0",
        "- original_inputs_modified=false",
        "- external_action=none",
        "- 根因、命令目标、变更参数和业务止损均待 SRE/业务负责人复核与审批。",
    ]
    return "\n".join(lines).encode("utf-8")


def _render_ledger(outcome: AgentControlLoopSREDiagnosisOutcome) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(LEDGER_HEADERS)
    writer.writerows(_ledger_rows(outcome))
    return output.getvalue().encode("utf-8-sig")


def _ledger_rows(outcome: AgentControlLoopSREDiagnosisOutcome) -> list[list[str]]:
    rows: list[list[str]] = []
    for item in outcome.observations:
        rows.append(
            [
                "observation",
                item.observation_id,
                item.status,
                item.statement,
                item.locator,
                item.excerpt,
                json.dumps(item.fields, ensure_ascii=False, sort_keys=True),
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )
    for item in outcome.source_conflicts:
        rows.append(
            [
                "conflict",
                item.conflict_id,
                item.status,
                f"{item.title}：{item.statement}",
                ",".join(item.locators),
                "",
                json.dumps({"impact": item.impact}, ensure_ascii=False, sort_keys=True),
                ",".join(item.side_a_observation_ids),
                ",".join(item.side_b_observation_ids),
                "",
                "",
                "",
                item.impact,
                "",
                "",
                "",
                "",
            ]
        )
    for item in outcome.hypotheses:
        rows.append(
            [
                "hypothesis",
                item.hypothesis_id,
                item.confidence,
                item.statement,
                ",".join(item.supporting_locators + item.counter_evidence_locators),
                "",
                json.dumps({"limitations": item.limitations}, ensure_ascii=False, sort_keys=True),
                ",".join(item.supporting_observation_ids),
                ",".join(item.counter_evidence_ids),
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )
    for item in (*outcome.action_proposals, *outcome.business_mitigations):
        rows.append(
            [
                "proposal",
                item.proposal_id,
                item.kind,
                f"{item.title}：{item.command_template or item.action_text}",
                "",
                "",
                json.dumps({"source_observation_ids": item.source_observation_ids}, ensure_ascii=False, sort_keys=True),
                ",".join(item.source_observation_ids),
                "",
                item.risk_level,
                item.target_status,
                "；".join(item.preconditions),
                item.rollback,
                "；".join(item.verify_after),
                item.official_reference or "",
                "true",
                "false",
            ]
        )
    return rows


def _parse_ledger(content: bytes) -> tuple[bool, list[list[str]], str]:
    try:
        text = content.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except (UnicodeError, csv.Error) as exc:
        return False, [], f"CSV 解析失败：{type(exc).__name__}"
    if not rows or tuple(rows[0]) != LEDGER_HEADERS:
        return False, [], "CSV 表头不符合固定协议。"
    body = rows[1:]
    if any(len(row) != len(LEDGER_HEADERS) for row in body):
        return False, [], "CSV 存在列数不一致。"
    ids = [row[1] for row in body]
    if not all(ids) or len(ids) != len(set(ids)):
        return False, [], "CSV 记录 ID 为空或重复。"
    return True, body, f"解析 {len(body)} 行唯一台账。"


def _parse_markdown(content: bytes) -> tuple[bool, dict[str, object], str]:
    try:
        text = content.decode("utf-8")
    except UnicodeError as exc:
        return False, {}, f"Markdown 编码无效：{type(exc).__name__}"
    required_sections = (
        "## 来源概览",
        "## 时间线与观察",
        "## 来源冲突",
        "## 根因假设与反证",
        "## 只读预检与条件式写提案",
        "## 业务止损提案",
        "## 审批与未执行边界",
    )
    if any(text.count(section) != 1 for section in required_sections):
        return False, {"text": text}, "Markdown 必需章节缺失或重复。"
    metric_match = re.search(r"## 动态结构化指标\n```json\n(.+)\n```", text)
    if not metric_match:
        return False, {"text": text}, "Markdown 缺少结构化指标 JSON。"
    try:
        metric_facts = json.loads(metric_match.group(1))
    except json.JSONDecodeError:
        return False, {"text": text}, "Markdown 指标 JSON 损坏。"
    return True, {
        "text": text,
        "observations": re.findall(r"\| (sre-observation-[a-z0-9-]+) \|", text),
        "conflicts": re.findall(r"\| (sre-conflict-[a-z0-9-]+) \|", text),
        "hypotheses": re.findall(r"^### (sre-hypothesis-[a-z0-9-]+)$", text, re.MULTILINE),
        "proposals": re.findall(r"^### (sre-proposal-[a-z0-9-]+)｜", text, re.MULTILINE),
        "locators": set(re.findall(r"log\.txt:L[0-9]+(?:-L[0-9]+)?", text)),
        "metric_facts": metric_facts,
    }, "Markdown 结构可解析。"


def _check(check_id: str, label: str, passed: bool, detail: str) -> SREArtifactCheck:
    return SREArtifactCheck(check_id=check_id, label=label, passed=passed, detail=detail)


def _range(values: list[float]) -> dict[str, float]:
    return {"min": min(values), "max": max(values)}


def _slug(value: object) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return normalized or "item"


def _stringify(value: object) -> str:
    if isinstance(value, float):
        return f"{value:g}"
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _md(value: str) -> str:
    return value.replace("|", "\\|").replace("\r", " ").replace("\n", "<br>")
