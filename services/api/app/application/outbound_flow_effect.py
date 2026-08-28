"""Source-derived Operations-008 outbound-flow design and independent verifier."""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Iterable
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from packages.contracts.harness_models import (
    AgentControlLoopOutboundEdge,
    AgentControlLoopOutboundFlowOutcome,
    AgentControlLoopOutboundGraphIntegrity,
    AgentControlLoopOutboundGuard,
    AgentControlLoopOutboundNode,
    AgentControlLoopOutboundRule,
    AgentControlLoopOutboundRuleParameter,
    AgentControlLoopOutboundTerminal,
)


class OutboundFlowValidationError(ValueError):
    """The fixed Operations-008 source or generated DOCX is not trustworthy."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class OutboundSourceInput:
    logical_id: str
    file_name: str
    display_path: str
    file_ref: str
    content: bytes
    declared_size: int
    allowlist_verified: bool


@dataclass(frozen=True)
class OutboundVerifierCheck:
    check_id: str
    label: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class OutboundFlowBuild:
    report_docx: bytes
    outcome: AgentControlLoopOutboundFlowOutcome
    checks: tuple[OutboundVerifierCheck, ...]


@dataclass(frozen=True)
class _SourceLine:
    number: int
    text: str
    section: str

    @property
    def locator(self) -> str:
        return f"专业性说明.md:L{self.number}"


@dataclass(frozen=True)
class _RuleDraft:
    rule_id: str
    group: str
    line: _SourceLine
    parameters: tuple[AgentControlLoopOutboundRuleParameter, ...]
    expected_relation: str
    expected_action: str
    mapping_key: str
    coverage_state: str = "covered"


SOURCE_LOGICAL_ID = "operations-008-professional-guidance"
EXPECTED_FILE_NAME = "专业性说明.md"
EXPECTED_DISPLAY_PATH = "运营管理/专业性说明.md"
EXPECTED_FILE_REF = "forte-ba23e986a9c7e8d8"

GROUP_ORDER = (
    "TIME",
    "FREQ",
    "RECORD",
    "IDENTITY",
    "THIRD_PARTY",
    "PROHIBIT",
    "CONNECT",
    "PTP",
    "SOFT",
    "HARD",
    "DISPUTE",
    "INVALID",
    "TERMINAL",
    "PAYMENT",
    "REDIAL",
)

SOURCE_TERMINAL_LABELS = (
    "PTP登记",
    "转人工跟进",
    "安排重拨",
    "停止外呼（达上限）",
    "加入禁呼名单",
    "案件升级",
)

NO_EXECUTION_BOUNDARY = (
    "这是流程设计，不是拨号、CRM/短信执行，也不是法律意见。"
    "文档中的拨号、CRM、短信提醒、禁呼写入和转人工均是未来受控节点；"
    "本次 external_action=none。"
)
SOURCE_LIMITATION = (
    "批准来源仅笼统提及监管机构，没有制度版本、批准主体或当前有效性证明；"
    "本成果不能作为最新监管验证或法律意见。"
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"


def build_outbound_flow(source: OutboundSourceInput) -> OutboundFlowBuild:
    """Build a flow DOCX and then independently reparse source and artifact bytes."""

    outcome = analyze_outbound_source(source)
    report = _report_docx(outcome, source)
    checks = verify_outbound_flow_artifact(source, report)
    return OutboundFlowBuild(report_docx=report, outcome=outcome, checks=checks)


def analyze_outbound_source(source: OutboundSourceInput) -> AgentControlLoopOutboundFlowOutcome:
    _validate_source_contract(source)
    lines = _source_lines(source.content)
    drafts, parameters, order_relation, terminal_labels = _parse_rules(lines)
    graph = _build_graph(drafts, parameters, order_relation, terminal_labels)
    rules = _materialize_rules(drafts, source.file_ref, graph[5])
    integrity = _graph_integrity(
        rules,
        nodes=graph[0],
        edges=graph[1],
        guards=graph[2],
        terminals=graph[3],
        order_relation=order_relation,
    )
    covered = sum(rule.coverage_state == "covered" for rule in rules)
    unsupported = sum(rule.coverage_state == "unsupported" for rule in rules)
    conflicts = sum(rule.coverage_state == "conflict" for rule in rules)
    integrity_ok = all(integrity.model_dump().values())
    status = "approval_required" if integrity_ok and not unsupported and not conflicts else "invalid"
    reachable_terminal_count = _reachable_terminal_count(graph[0], graph[1], graph[3])
    decision = (
        "来源规则和流程图结构已由服务端重算，仍需业务与合规负责人批准；真实外呼及系统写入均未发生。"
        if status == "approval_required"
        else "规则覆盖或流程图完整性未通过，当前设计不得提交审批或用于外呼。"
    )
    return AgentControlLoopOutboundFlowOutcome(
        outcome_id="outbound-flow-outcome-operations-008",
        status=status,
        decision=decision,
        summary=(
            f"从批准 Markdown 推导 {len({rule.group for rule in rules})} 组、{len(rules)} 条原子要求；"
            f"构建 {len(graph[0])} 个节点、{len(graph[1])} 条边和 {len(graph[3])} 个终态，"
            f"可达终态 {reachable_terminal_count}/{len(graph[3])}。"
        ),
        source_rule_group_count=len({rule.group for rule in rules}),
        atomic_requirement_count=len(rules),
        covered_count=covered,
        unsupported_count=unsupported,
        conflict_count=conflicts,
        node_count=len(graph[0]),
        edge_count=len(graph[1]),
        guard_count=len(graph[2]),
        terminal_count=len(graph[3]),
        reachable_terminal_count=reachable_terminal_count,
        parameters=list(parameters),
        rules=list(rules),
        nodes=list(graph[0]),
        edges=list(graph[1]),
        guards=list(graph[2]),
        terminals=list(graph[3]),
        graph_integrity=integrity,
    )


def verify_outbound_flow_artifact(
    source: OutboundSourceInput,
    report_docx: bytes,
) -> tuple[OutboundVerifierCheck, ...]:
    """Recompute expected facts from source and compare them with parsed DOCX tables."""

    expected = analyze_outbound_source(source)
    valid, text, tables, parse_detail = _parse_generated_docx(report_docx)
    expected_tables = _outcome_tables(expected)
    table_labels = (
        "来源规则账本",
        "流程节点表",
        "边与守卫表",
        "守卫参数表",
        "终态表",
        "完整性摘要",
    )
    table_results: list[bool] = []
    for index, expected_table in enumerate(expected_tables):
        table_results.append(valid and len(tables) > index and tables[index] == expected_table)
    boundary_ok = all(
        token in text
        for token in (
            NO_EXECUTION_BOUNDARY,
            SOURCE_LIMITATION,
            source.display_path,
            source.file_ref,
            "最终合规审批未发生",
            "原始 Operations-008 文件未修改",
        )
    )
    integrity_values = expected.graph_integrity.model_dump()
    checks = [
        _check(
            "check-outbound-source-contract-v2",
            "批准来源合同",
            valid and source.allowlist_verified,
            f"{source.display_path} 的逻辑 ID、file_ref、声明大小和冻结字节已校验；{parse_detail}",
        ),
    ]
    for label, passed in zip(table_labels, table_results, strict=True):
        slug = {
            "来源规则账本": "rule-ledger",
            "流程节点表": "nodes",
            "边与守卫表": "edges",
            "守卫参数表": "guards",
            "终态表": "terminals",
            "完整性摘要": "integrity-summary",
        }[label]
        checks.append(
            _check(
                f"check-outbound-{slug}-v2",
                label,
                passed,
                f"DOCX 中的{label}必须与批准 Markdown 的服务端重算结果逐字段一致。",
            )
        )
    checks.extend(
        (
            _check(
                "check-outbound-graph-integrity-v2",
                "流程图可遍历且终态可达",
                valid and all(integrity_values.values()),
                (
                    f"节点 {expected.node_count}、边 {expected.edge_count}、终态 "
                    f"{expected.reachable_terminal_count}/{expected.terminal_count} 可达；"
                    "无 dangling edge，所有节点均可到达终态。"
                ),
            ),
            _check(
                "check-outbound-critical-order-v2",
                "身份、告知与欠款信息顺序",
                valid and expected.graph_integrity.critical_order_valid,
                "顺序由来源重算；当前批准版本要求先确认身份，再告知录音与来意，最后进入欠款引导。",
            ),
            _check(
                "check-outbound-rule-coverage-v2",
                "全部规范性要求均有图映射",
                valid
                and expected.covered_count == expected.atomic_requirement_count
                and expected.unsupported_count == 0
                and expected.conflict_count == 0,
                (
                    f"{expected.covered_count}/{expected.atomic_requirement_count} 条原子要求已绑定节点、边、"
                    "守卫或终态；未知或冲突规则不得静默忽略。"
                ),
            ),
            _check(
                "check-outbound-boundary-v2",
                "审批、法律与执行边界",
                valid and boundary_ok,
                "DOCX 明确仅为固定 Operations-008 流程设计，不是法律意见，也没有拨号或写入外部系统。",
            ),
        )
    )
    return tuple(checks)


def _validate_source_contract(source: OutboundSourceInput) -> None:
    expected = {
        "logical_id": SOURCE_LOGICAL_ID,
        "file_name": EXPECTED_FILE_NAME,
        "display_path": EXPECTED_DISPLAY_PATH,
        "file_ref": EXPECTED_FILE_REF,
    }
    for field, value in expected.items():
        if getattr(source, field) != value:
            raise OutboundFlowValidationError(
                "outbound_source_identity",
                f"Operations-008 来源 {field} 不匹配：{getattr(source, field)!r}",
            )
    if not source.allowlist_verified:
        raise OutboundFlowValidationError("outbound_source_allowlist", "来源未通过 allowlist 校验")
    if not source.content or source.declared_size <= 0:
        raise OutboundFlowValidationError("outbound_source_empty", "批准 Markdown 为空")
    if source.declared_size != len(source.content):
        raise OutboundFlowValidationError("outbound_source_size", "声明大小与冻结字节不一致")
    if b"\x00" in source.content:
        raise OutboundFlowValidationError("outbound_source_binary", "批准 Markdown 包含二进制 NUL")
    try:
        text = source.content.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise OutboundFlowValidationError("outbound_source_encoding", "批准 Markdown 不是合法 UTF-8") from exc
    if "# 信用卡 M1 逾期 AI 外呼催收流程" not in text:
        raise OutboundFlowValidationError("outbound_source_truncated", "批准 Markdown 标题或正文被截断")


def _source_lines(content: bytes) -> tuple[_SourceLine, ...]:
    section = ""
    result: list[_SourceLine] = []
    for number, raw in enumerate(content.decode("utf-8").splitlines(), start=1):
        text = raw.strip()
        if text.startswith("## 二、"):
            section = "regulatory"
        elif text.startswith("## 三、"):
            section = "branches"
        elif text.startswith("## 四、"):
            section = "behavior"
        result.append(_SourceLine(number=number, text=text, section=section))
    return tuple(result)


_KNOWN_FRAGMENT_TOKENS: dict[str, tuple[tuple[str, ...], ...]] = {
    "time": (("严禁拨打", "拨号前判断"),),
    "freq": (
        ("每日拨打不得超过", "小时内不得超过"),
        ("达到上限后停止当日外呼",),
    ),
    "record": (
        ("全程录音", "至少保存"),
        ("必须告知", "录音"),
    ),
    "third": (
        ("接通后必须", "接听"),
        ("只能请其转告", "严禁透露欠款金额"),
        ("第三方", "不再联系", "禁呼名单"),
    ),
    "prohibit": (
        ("严禁威胁", "恐吓", "辱骂"),
        ("M1", "不得使用", "法律行动"),
    ),
    "unconnected": (("无人接听", "关机空号", "主动拒接", "重拨队列"),),
    "connected": (("本人接听", "非本人接听"),),
    "ptp": (("承诺金额", "承诺日期", "短信提醒"),),
    "soft": (("分期方案", "后续跟进"),),
    "hard": (("案件升级", "人工或法务处理"),),
    "dispute": (("必须转人工", "不得自行处理"),),
    "invalid": (("记录", "今日已拨次数判断", "安排重拨"),),
    "terminals": (("PTP登记", "转人工跟进", "安排重拨", "案件升级"),),
    "identity": (
        ("接通后第一步", "询问是否本人"),
        ("确认是本人", "催收话术"),
        ("非本人只请转告",),
        ("无法确认", "结束通话"),
    ),
    "intro": (("自我介绍", "告知录音", "说明来电目的", "欠款金额"),),
    "payment": (("逾期天数", "最低还款额", "APP/网银/柜台", "分期方案"),),
    "force_human": (("投诉", "情绪持续激动", "必须立即转人工"),),
    "redial": (
        ("未接通后查询今日已拨次数", "间隔至少", "重拨"),
        ("已达上限", "今日完成", "次日重新评估"),
    ),
}


def _split_rule_fragments(line: _SourceLine, prefix: str = "") -> tuple[_SourceLine, ...]:
    text = line.text[len(prefix) :].strip() if prefix and line.text.startswith(prefix) else line.text
    parts = [item.strip() for item in re.split(r"(?<=[。！？；;])\s*", text) if item.strip()]
    return tuple(_SourceLine(number=line.number, text=item, section=line.section) for item in parts)


def _unconsumed_selected_fragments(
    selected: dict[str, _SourceLine], selectors: dict[str, str]
) -> tuple[_SourceLine, ...]:
    remaining: list[_SourceLine] = []
    for key, line in selected.items():
        patterns = _KNOWN_FRAGMENT_TOKENS[key]
        consumed = [False] * len(patterns)
        for fragment in _split_rule_fragments(line, selectors[key]):
            matches = [
                index
                for index, tokens in enumerate(patterns)
                if all(token in fragment.text for token in tokens)
            ]
            if len(matches) == 1 and not consumed[matches[0]]:
                consumed[matches[0]] = True
                continue
            remaining.append(fragment)
        if not all(consumed):
            missing = [str(index + 1) for index, value in enumerate(consumed) if not value]
            raise OutboundFlowValidationError(
                "outbound_required_semantics",
                f"{line.locator} 的 {key} 规则存在未消费的必需片段：{','.join(missing)}",
            )
    return tuple(remaining)


def _is_supported_extra_human_trigger(fragment: _SourceLine) -> bool:
    text = fragment.text
    if "必须" not in text or "转人工" not in text:
        return False
    return bool(
        re.search(r"高龄|重病|重大疾病|严重疾病", text)
        or re.match(r"^\*\*[^*]*转人工触发条件\*\*：", text)
    )


def _raise_residual_conflict(
    fragments: Iterable[_SourceLine],
    *,
    order_relation: str,
    start: str,
    end: str,
    daily_max: int,
    hourly_window: int,
    hourly_max: int,
) -> None:
    for fragment in fragments:
        text = fragment.text
        if "接通后第一步" in text and "录音" in text:
            relation = (
                "recording_before_identity"
                if re.search(r"接通后第一步.*(?:先)?(?:告知)?录音", text)
                else "identity_before_recording"
            )
            if relation != order_relation:
                raise OutboundFlowValidationError(
                    "outbound_identity_order_conflict",
                    f"{fragment.locator} 新增片段与已解析的身份/录音顺序相互冲突：{text}",
                )
        time_match = re.search(
            r"每日\s*(\d{1,2}):(\d{2})\s*至次日\s*(\d{1,2}):(\d{2})\s*严禁拨打",
            text,
        )
        if time_match:
            observed_start = _clock(time_match.group(1), time_match.group(2), fragment)
            observed_end = _clock(time_match.group(3), time_match.group(4), fragment)
            if (observed_start, observed_end) != (start, end):
                raise OutboundFlowValidationError(
                    "outbound_time_conflict",
                    f"{fragment.locator} 新增片段与禁呼时段冲突：{text}",
                )
        daily_match = re.search(r"每日拨打不得超过\s*(\d+)\s*次", text)
        hourly_match = re.search(r"(\d+)小时内不得超过\s*(\d+)\s*次", text)
        if daily_match or hourly_match:
            observed_daily = int(daily_match.group(1)) if daily_match else daily_max
            observed_window = int(hourly_match.group(1)) if hourly_match else hourly_window
            observed_hourly = int(hourly_match.group(2)) if hourly_match else hourly_max
            if (observed_daily, observed_window, observed_hourly) != (
                daily_max,
                hourly_window,
                hourly_max,
            ):
                raise OutboundFlowValidationError(
                    "outbound_frequency_conflict",
                    f"{fragment.locator} 新增片段与外呼频次参数冲突：{text}",
                )


def _parse_rules(
    lines: tuple[_SourceLine, ...],
) -> tuple[
    tuple[_RuleDraft, ...],
    tuple[AgentControlLoopOutboundRuleParameter, ...],
    str,
    tuple[str, ...],
]:
    required_sections = {
        "regulatory": "## 二、监管合规约束",
        "branches": "## 三、业务分支标准",
        "behavior": "## 四、关键节点的 AI 行为说明",
    }
    for heading in required_sections.values():
        if sum(line.text == heading for line in lines) != 1:
            raise OutboundFlowValidationError("outbound_section_contract", f"缺少或重复章节：{heading}")

    selectors = {
        "time": "**外呼时间**：",
        "freq": "**外呼频次**：",
        "record": "**录音存证**：",
        "third": "**第三方限制**：",
        "prohibit": "**禁止行为**：",
        "unconnected": "- 未接通：",
        "connected": "- 接通：",
        "ptp": "- **承诺还款（PTP）**：",
        "soft": "- **软拒绝**：",
        "hard": "- **硬拒绝**：",
        "dispute": "- **投诉/异议**：",
        "invalid": "- **无效通话**：",
        "terminals": "每条路径必须落到以下状态之一：",
        "identity": "**身份确认**：",
        "intro": "**开场告知**：",
        "payment": "**还款引导**：",
        "force_human": "**强制转人工触发条件**：",
        "redial": "**重拨调度**：",
    }
    selected = {key: _unique_prefix(lines, prefix) for key, prefix in selectors.items()}
    recognized_numbers = {line.number for line in selected.values()}

    time_match = _required_match(
        r"每日\s*(\d{1,2}):(\d{2})\s*至次日\s*(\d{1,2}):(\d{2})\s*严禁拨打",
        selected["time"],
        "outbound_time_format",
    )
    start = _clock(time_match.group(1), time_match.group(2), selected["time"])
    end = _clock(time_match.group(3), time_match.group(4), selected["time"])
    if start == end or "拨号前判断" not in selected["time"].text:
        raise OutboundFlowValidationError("outbound_time_invalid", "禁呼时间或拨号前 Gate 无效")

    freq_match = _required_match(
        r"每日拨打不得超过\s*(\d+)\s*次，\s*(\d+)小时内不得超过\s*(\d+)\s*次",
        selected["freq"],
        "outbound_frequency_format",
    )
    daily_max = _positive_int(freq_match.group(1), "outbound_daily_frequency")
    hourly_window = _positive_int(freq_match.group(2), "outbound_hourly_window")
    hourly_max = _positive_int(freq_match.group(3), "outbound_hourly_frequency")
    if "达到上限后停止当日外呼" not in selected["freq"].text:
        raise OutboundFlowValidationError("outbound_frequency_stop", "频次规则缺少达限停止语义")

    record_match = _required_match(
        r"全程录音，至少保存\s*(\d+)\s*年",
        selected["record"],
        "outbound_recording_format",
    )
    retention_years = _positive_int(record_match.group(1), "outbound_recording_retention")
    if "必须告知" not in selected["record"].text:
        raise OutboundFlowValidationError("outbound_recording_notice", "录音规则缺少告知要求")

    emotion_match = _required_match(
        r"情绪持续激动超过\s*(\d+)\s*秒",
        selected["force_human"],
        "outbound_emotion_threshold",
    )
    emotion_seconds = _positive_int(emotion_match.group(1), "outbound_emotion_threshold")
    redial_match = _required_match(
        r"间隔至少\s*(\d+)\s*小时后重拨",
        selected["redial"],
        "outbound_redial_interval",
    )
    redial_hours = _positive_int(redial_match.group(1), "outbound_redial_interval")

    terminal_text = selected["terminals"].text.split("：", 1)[1].rstrip("。")
    terminal_labels = tuple(item.strip() for item in terminal_text.split("、") if item.strip())
    if len(terminal_labels) != len(set(terminal_labels)) or not terminal_labels:
        raise OutboundFlowValidationError("outbound_terminal_duplicate", "终态列表为空或包含重复项")
    if not set(SOURCE_TERMINAL_LABELS).issubset(terminal_labels):
        missing = sorted(set(SOURCE_TERMINAL_LABELS) - set(terminal_labels))
        raise OutboundFlowValidationError(
            "outbound_terminal_missing",
            f"来源缺少当前业务分支需要的终态：{'、'.join(missing)}",
        )

    order_relation = _parse_order_relation(selected)
    _validate_required_phrases(selected)

    residual_fragments = list(_unconsumed_selected_fragments(selected, selectors))
    residual_fragments.extend(
        fragment
        for line in lines
        if line.section in {"regulatory", "branches", "behavior"}
        and _is_normative_line(line)
        and line.number not in recognized_numbers
        for fragment in _split_rule_fragments(line)
    )
    _raise_residual_conflict(
        residual_fragments,
        order_relation=order_relation,
        start=start,
        end=end,
        daily_max=daily_max,
        hourly_window=hourly_window,
        hourly_max=hourly_max,
    )
    extra_triggers = [
        fragment
        for fragment in residual_fragments
        if _is_supported_extra_human_trigger(fragment)
    ]
    extra_trigger_keys = {(item.number, item.text) for item in extra_triggers}
    unknown = [
        fragment
        for fragment in residual_fragments
        if (fragment.number, fragment.text) not in extra_trigger_keys
    ]
    if unknown:
        sample = "；".join(f"L{fragment.number} {fragment.text}" for fragment in unknown[:3])
        raise OutboundFlowValidationError(
            "outbound_unsupported_rule",
            f"发现适配器不认识的规范性要求，不能静默忽略：{sample}",
        )

    parameters = (
        _parameter("prohibited_start", start),
        _parameter("prohibited_end", end),
        _parameter("daily_call_max", str(daily_max), "次/日"),
        _parameter("hourly_window", str(hourly_window), "小时"),
        _parameter("hourly_call_max", str(hourly_max), "次/窗口"),
        _parameter("recording_retention", str(retention_years), "年"),
        _parameter("emotion_transfer_threshold", str(emotion_seconds), "秒"),
        _parameter("redial_min_interval", str(redial_hours), "小时"),
        _parameter("source_terminal_count", str(len(terminal_labels)), "个"),
        _parameter("identity_recording_order", order_relation),
    )
    param = {item.name: item for item in parameters}
    drafts: list[_RuleDraft] = []

    def add(
        group: str,
        ordinal: int,
        line_key: str,
        relation: str,
        action: str,
        mapping_key: str,
        *parameter_names: str,
        coverage_state: str = "covered",
    ) -> None:
        drafts.append(
            _RuleDraft(
                rule_id=f"OUT-{group}-{ordinal:02d}",
                group=group,
                line=selected[line_key],
                parameters=tuple(param[name] for name in parameter_names),
                expected_relation=relation,
                expected_action=action,
                mapping_key=mapping_key,
                coverage_state=coverage_state,
            )
        )

    add("TIME", 1, "time", "当前时刻不得落入禁呼窗口", "在 future dial 前阻断禁呼时段", "time-window", "prohibited_start", "prohibited_end")
    add("TIME", 2, "time", "TIME Gate 必须早于 future dial", "先校验时段，再允许未来拨号节点", "time-before-dial")
    add("FREQ", 1, "freq", "同一客户每日次数不得超过来源上限", "达日上限后停止当日外呼", "daily-limit", "daily_call_max")
    add("FREQ", 2, "freq", "窗口内次数不得超过来源上限", "达小时窗口上限后停止当日外呼", "hourly-limit", "hourly_window", "hourly_call_max")
    add("FREQ", 3, "freq", "任一频次上限命中即停止", "进入频次达限终态", "frequency-stop")
    add("RECORD", 1, "record", "每通电话全程录音并按来源年限保存", "在本人通话节点标明录音及保留要求", "recording-retention", "recording_retention")
    add("RECORD", 2, "record", "通话中必须告知录音", "录音告知节点受身份顺序约束", "recording-notice")
    add("IDENTITY", 1, "identity", order_relation, "按来源顺序执行身份确认和录音告知", "identity-order", "identity_recording_order")
    add("IDENTITY", 2, "identity", "只有确认本人后才能进入欠款话术", "阻断非本人和身份不明路径的欠款披露", "identity-before-debt")
    add("IDENTITY", 3, "identity", "无法确认身份时结束通话", "进入身份无法确认终态", "identity-unconfirmed")
    add("THIRD_PARTY", 1, "third", "非本人只能请其转告", "进入仅转告节点", "third-party-relay")
    add("THIRD_PARTY", 2, "third", "非本人不得披露欠款金额", "第三方路径不得到达欠款引导", "third-party-no-debt")
    add("THIRD_PARTY", 3, "third", "第三方要求停止联系时必须禁呼", "进入加入禁呼名单终态", "third-party-dnc")
    add("PROHIBIT", 1, "prohibit", "禁止威胁、恐吓和辱骂", "话术守卫拒绝禁止行为", "prohibited-language")
    add("PROHIBIT", 2, "prohibit", "M1 阶段不得使用法律行动话术", "话术守卫拒绝法律程序暗示", "no-legal-threat")
    add("CONNECT", 1, "unconnected", "拨号结果必须区分接通与未接通", "进入连接状态决策", "connection-branch")
    add("CONNECT", 2, "unconnected", "无人接听、关机空号或主动拒接进入频次 Gate", "记录未接通分类并判断重拨", "unconnected-retry")
    add("PTP", 1, "ptp", "承诺还款必须记录金额和日期", "在 PTP 终态前记录承诺字段", "ptp-record")
    add("PTP", 2, "ptp", "到期前短信提醒是未来受控动作", "只写入未来短信提醒节点，不发送短信", "ptp-sms")
    add("SOFT", 1, "soft", "软拒绝进入分期方案和后续跟进", "进入分期跟进节点后安排后续联系", "soft-follow-up")
    add("HARD", 1, "hard", "硬拒绝或否认债务必须升级", "进入人工或法务案件升级终态", "hard-escalation")
    add("DISPUTE", 1, "force_human", "投诉、异议及来源短语触发人工", "立即进入转人工终态", "dispute-human")
    add("DISPUTE", 2, "force_human", "情绪持续超过来源阈值触发人工", "立即进入转人工终态", "emotion-human", "emotion_transfer_threshold")
    add("INVALID", 1, "invalid", "无效通话必须记录并重新经过频次 Gate", "记录后只在未达限时安排重拨", "invalid-retry")
    for ordinal, label in enumerate(terminal_labels, start=1):
        drafts.append(
            _RuleDraft(
                rule_id=f"OUT-TERMINAL-{ordinal:02d}",
                group="TERMINAL",
                line=selected["terminals"],
                parameters=(_parameter("terminal_label", label),),
                expected_relation="每条业务路径必须进入一个来源终态",
                expected_action=f"提供可达终态：{label}",
                mapping_key=f"terminal:{label}",
                coverage_state="covered" if label in SOURCE_TERMINAL_LABELS else "unsupported",
            )
        )
    add("PAYMENT", 1, "payment", "本人确认后才可告知逾期天数和最低还款额", "进入欠款信息与最低还款额节点", "payment-details")
    add("PAYMENT", 2, "payment", "提供来源列出的还款渠道并询问近期还款或分期", "进入还款渠道与分期询问节点", "payment-options")
    add("REDIAL", 1, "redial", "未接通重拨至少间隔来源小时数", "未达限时进入未来重拨终态", "redial-interval", "redial_min_interval")
    add("REDIAL", 2, "redial", "达限标记今日完成并在次日重新评估", "频次达限终态保留次日复核动作", "redial-next-day")
    for offset, line in enumerate(extra_triggers, start=3):
        drafts.append(
            _RuleDraft(
                rule_id=f"OUT-DISPUTE-{offset:02d}",
                group="DISPUTE",
                line=line,
                parameters=(),
                expected_relation="新增来源触发条件命中时必须转人工",
                expected_action="从客户态度决策进入转人工终态",
                mapping_key=f"extra-human:{offset}",
            )
        )
    return tuple(drafts), parameters, order_relation, terminal_labels


def _parse_order_relation(selected: dict[str, _SourceLine]) -> str:
    relations: list[str] = []
    third = selected["third"].text
    identity = selected["identity"].text
    intro = selected["intro"].text
    if "先确认是否本人" in third:
        relations.append("identity_before_recording")
    elif re.search(r"先.*录音.*再.*本人", third):
        relations.append("recording_before_identity")
    else:
        raise OutboundFlowValidationError("outbound_identity_order", "第三方限制未给出身份确认顺序")
    if re.search(r"接通后第一步.*录音.*(?:再.*)?(?:身份|本人)", identity):
        relations.append("recording_before_identity")
    elif "接通后第一步" in identity and ("身份" in identity or "是否本人" in identity):
        relations.append("identity_before_recording")
    else:
        raise OutboundFlowValidationError("outbound_identity_order", "身份确认段未给出第一业务步骤")
    if "确认本人后" in intro and "告知录音" in intro:
        relations.append("identity_before_recording")
    elif re.search(r"告知录音后.*确认本人", intro):
        relations.append("recording_before_identity")
    else:
        raise OutboundFlowValidationError("outbound_identity_order", "开场告知段未给出身份与录音顺序")
    if len(set(relations)) != 1:
        raise OutboundFlowValidationError(
            "outbound_identity_order_conflict",
            "身份确认、第三方限制与开场告知对录音顺序的规定相互冲突",
        )
    return relations[0]


def _validate_required_phrases(selected: dict[str, _SourceLine]) -> None:
    requirements = {
        "third": ("只能请其转告", "严禁透露欠款金额", "加入禁呼名单"),
        "prohibit": ("严禁威胁", "不得使用\"将采取法律行动\""),
        "unconnected": ("无人接听", "关机空号", "主动拒接", "未超限则加入重拨队列"),
        "connected": ("本人接听", "非本人接听"),
        "ptp": ("承诺金额", "承诺日期", "短信提醒"),
        "soft": ("分期方案", "后续跟进"),
        "hard": ("案件升级", "转人工或法务处理"),
        "dispute": ("必须转人工", "AI 不得自行处理"),
        "invalid": ("记录", "今日已拨次数判断", "安排重拨"),
        "identity": ("确认是本人", "无法确认则结束通话"),
        "intro": ("自我介绍", "告知录音", "说明来电目的", "不得在确认身份前直接报出欠款金额"),
        "payment": ("逾期天数", "最低还款额", "APP/网银/柜台", "分期方案"),
        "force_human": ("必须立即转人工",),
        "redial": ("已达上限则标记为今日完成", "次日重新评估"),
    }
    for key, tokens in requirements.items():
        missing = [token for token in tokens if token not in selected[key].text]
        if missing:
            raise OutboundFlowValidationError(
                "outbound_required_semantics",
                f"{selected[key].locator} 缺少语义：{'、'.join(missing)}",
            )


def _build_graph(
    drafts: tuple[_RuleDraft, ...],
    parameters: tuple[AgentControlLoopOutboundRuleParameter, ...],
    order_relation: str,
    terminal_labels: tuple[str, ...],
) -> tuple[
    tuple[AgentControlLoopOutboundNode, ...],
    tuple[AgentControlLoopOutboundEdge, ...],
    tuple[AgentControlLoopOutboundGuard, ...],
    tuple[AgentControlLoopOutboundTerminal, ...],
    tuple[str, ...],
    dict[str, dict[str, tuple[str, ...]]],
]:
    rule_by_key = {draft.mapping_key: draft.rule_id for draft in drafts}

    def ids(*keys: str) -> list[str]:
        return [rule_by_key[key] for key in keys if key in rule_by_key]

    param = {item.name: item for item in parameters}
    nodes: list[AgentControlLoopOutboundNode] = []
    edges: list[AgentControlLoopOutboundEdge] = []
    guards: list[AgentControlLoopOutboundGuard] = []
    terminals: list[AgentControlLoopOutboundTerminal] = []
    mapping: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: {"nodes": [], "edges": [], "guards": [], "terminals": []}
    )

    def bind(keys: Iterable[str], kind: str, value: str) -> None:
        for key in keys:
            if key in rule_by_key:
                mapping[key][kind].append(value)

    def node(node_id: str, label: str, kind: str, *keys: str, future: bool = False) -> None:
        full_id = f"out-node-{node_id}"
        nodes.append(
            AgentControlLoopOutboundNode(
                node_id=full_id,
                label=label,
                kind=kind,
                source_rule_ids=ids(*keys),
                future_action=future,
            )
        )
        bind(keys, "nodes", full_id)

    def guard(guard_id: str, label: str, keys: tuple[str, ...], params: tuple[str, ...] = ()) -> None:
        full_id = f"out-guard-{guard_id}"
        guards.append(
            AgentControlLoopOutboundGuard(
                guard_id=full_id,
                label=label,
                parameters=[param[name] for name in params],
                source_rule_ids=ids(*keys),
            )
        )
        bind(keys, "guards", full_id)

    def edge(
        edge_id: str,
        from_id: str,
        to_id: str,
        label: str,
        keys: tuple[str, ...],
        guard_ids: tuple[str, ...] = (),
        *,
        future: bool = False,
    ) -> None:
        full_id = f"out-edge-{edge_id}"
        edges.append(
            AgentControlLoopOutboundEdge(
                edge_id=full_id,
                from_node_id=f"out-node-{from_id}",
                to_node_id=f"out-node-{to_id}",
                label=label,
                guard_ids=[f"out-guard-{item}" for item in guard_ids],
                source_rule_ids=ids(*keys),
                future_action=future,
            )
        )
        bind(keys, "edges", full_id)

    def terminal(terminal_id: str, node_id: str, label: str, key: str, source_listed: bool) -> None:
        full_id = f"out-terminal-{terminal_id}"
        terminals.append(
            AgentControlLoopOutboundTerminal(
                terminal_id=full_id,
                node_id=f"out-node-{node_id}",
                label=label,
                source_rule_ids=ids(key),
                source_listed=source_listed,
            )
        )
        bind((key,), "terminals", full_id)

    node("start", "START", "start")
    node("gate-time-window", "拨号前禁呼时段判断", "gate", "time-window", "time-before-dial")
    node("hold-until-window", "等待进入允许外呼时段", "action", "time-window", future=True)
    node("gate-pre-dial-frequency", "拨号前每日/窗口频次判断", "gate", "daily-limit", "hourly-limit", "frequency-stop")
    node("mark-daily-limit", "标记当日频次已达上限并等待次日重评", "action", "frequency-stop", "redial-next-day")
    node("future-dial", "未来拨号尝试（本次未执行）", "action", "time-before-dial", future=True)
    node("decision-connection", "判断是否接通", "decision", "connection-branch")
    node("classify-unanswered", "记录无人接听/关机空号/主动拒接", "action", "unconnected-retry")
    node("gate-post-call-frequency", "无效或未接通后的频次判断", "gate", "unconnected-retry", "invalid-retry", "daily-limit", "hourly-limit")
    node("future-redial", "安排至少来源间隔后的未来重拨", "action", "redial-interval", future=True)
    node("decision-identity", "确认是否本人接听", "decision", "identity-order", "identity-before-debt", "identity-unconfirmed")
    node("recording-notice", "告知录音并标明全程录音与保留年限", "action", "recording-retention", "recording-notice")
    node("relay-only", "非本人仅请转告且不披露欠款", "action", "third-party-relay", "third-party-no-debt")
    node("decision-third-party-stop", "第三方是否要求停止联系", "decision", "third-party-dnc")
    node("end-unconfirmed-identity", "结束身份无法确认或非本人通话", "action", "identity-unconfirmed", "third-party-relay")
    node("introduce-purpose", "自我介绍、说明来意并应用禁止话术守卫", "action", "identity-before-debt", "prohibited-language", "no-legal-threat")
    node("payment-guidance", "告知逾期/最低还款额、渠道并询问还款或分期", "action", "payment-details", "payment-options")
    node("decision-response", "判断本人态度、投诉异议与情绪状态", "decision", "ptp-record", "soft-follow-up", "hard-escalation", "dispute-human", "emotion-human")
    node("record-ptp", "记录承诺金额和日期", "action", "ptp-record")
    node("future-sms", "安排到期前短信提醒（本次未发送）", "action", "ptp-sms", future=True)
    node("installment-follow-up", "引导分期并安排后续跟进", "action", "soft-follow-up", future=True)
    node("case-escalation", "案件升级并等待人工或法务处理", "action", "hard-escalation", future=True)
    node("human-transfer", "转人工处理投诉、异议或高风险状态", "action", "dispute-human", "emotion-human", future=True)
    node("record-invalid-call", "记录立即挂断或无法沟通", "action", "invalid-retry")

    terminal_nodes = {
        "PTP登记": ("ptp", "terminal-ptp"),
        "转人工跟进": ("human", "terminal-human"),
        "安排重拨": ("redial", "terminal-redial"),
        "停止外呼（达上限）": ("limit", "terminal-limit"),
        "加入禁呼名单": ("dnc", "terminal-dnc"),
        "案件升级": ("escalation", "terminal-escalation"),
    }
    for label, (slug, node_id) in terminal_nodes.items():
        key = next(
            draft.mapping_key
            for draft in drafts
            if draft.group == "TERMINAL" and draft.parameters[0].value == label
        )
        node(node_id, label, "terminal", key)
        terminal(slug, node_id, label, key, True)
    node("terminal-identity-unconfirmed", "结束通话（身份无法确认）", "terminal", "identity-unconfirmed")
    terminals.append(
        AgentControlLoopOutboundTerminal(
            terminal_id="out-terminal-identity-unconfirmed",
            node_id="out-node-terminal-identity-unconfirmed",
            label="结束通话（身份无法确认）",
            source_rule_ids=ids("identity-unconfirmed"),
            source_listed=False,
        )
    )
    bind(("identity-unconfirmed",), "terminals", "out-terminal-identity-unconfirmed")
    for label in terminal_labels:
        if label in terminal_nodes:
            continue
        slug = hashlib.sha256(label.encode("utf-8")).hexdigest()[:10]
        key = next(
            draft.mapping_key
            for draft in drafts
            if draft.group == "TERMINAL" and draft.parameters[0].value == label
        )
        node(f"terminal-source-extra-{slug}", label, "terminal", key)
        terminal(f"source-extra-{slug}", f"terminal-source-extra-{slug}", label, key, True)

    guard("time-window", "当前时间不在来源禁呼窗口", ("time-window",), ("prohibited_start", "prohibited_end"))
    guard("frequency", "每日与窗口频次均未达到来源上限", ("daily-limit", "hourly-limit"), ("daily_call_max", "hourly_window", "hourly_call_max"))
    guard("identity", "本人/第三方/无法确认三态互斥", ("identity-order", "identity-before-debt", "identity-unconfirmed"))
    guard("third-party-stop", "第三方停止联系请求", ("third-party-dnc",))
    guard("prohibited-content", "禁止威胁、辱骂和 M1 法律行动暗示", ("prohibited-language", "no-legal-threat"))
    guard("response", "本人态度、投诉、异议、无效通话与高风险触发互斥投影", ("ptp-record", "soft-follow-up", "hard-escalation", "dispute-human", "emotion-human"), ("emotion_transfer_threshold",))
    guard("redial-interval", "未来重拨不得早于来源最小间隔", ("redial-interval",), ("redial_min_interval",))

    edge("start-time", "start", "gate-time-window", "开始后先检查时段", ("time-before-dial",))
    edge("time-denied", "gate-time-window", "hold-until-window", "处于禁呼窗口", ("time-window",), ("time-window",))
    edge("time-hold-redial", "hold-until-window", "terminal-redial", "等待允许时段后重新安排", ("time-window", "redial-interval"), future=True)
    edge("time-allowed", "gate-time-window", "gate-pre-dial-frequency", "当前时段允许", ("time-window",), ("time-window",))
    edge("pre-frequency-denied", "gate-pre-dial-frequency", "mark-daily-limit", "达到每日或窗口上限", ("daily-limit", "hourly-limit", "frequency-stop"), ("frequency",))
    edge("limit-stop", "mark-daily-limit", "terminal-limit", "停止当日外呼并次日重评", ("frequency-stop", "redial-next-day"))
    edge("pre-frequency-allowed", "gate-pre-dial-frequency", "future-dial", "未达到频次上限", ("daily-limit", "hourly-limit"), ("frequency",), future=True)
    edge("future-dial-connection", "future-dial", "decision-connection", "未来拨号返回连接状态", ("connection-branch",), future=True)
    edge("not-connected", "decision-connection", "classify-unanswered", "未接通", ("connection-branch", "unconnected-retry"))
    edge("unanswered-frequency", "classify-unanswered", "gate-post-call-frequency", "记录后检查频次", ("unconnected-retry",))
    edge("post-frequency-denied", "gate-post-call-frequency", "mark-daily-limit", "达到每日或窗口上限", ("daily-limit", "hourly-limit", "frequency-stop"), ("frequency",))
    edge("post-frequency-allowed", "gate-post-call-frequency", "future-redial", "未达到频次上限", ("unconnected-retry", "invalid-retry", "redial-interval"), ("frequency", "redial-interval"), future=True)
    edge("redial-terminal", "future-redial", "terminal-redial", "形成未来重拨安排", ("redial-interval",), future=True)

    if order_relation == "identity_before_recording":
        edge("connected-identity", "decision-connection", "decision-identity", "接通后第一业务步骤是身份确认", ("connection-branch", "identity-order"))
        self_target = "recording-notice"
        edge("identity-self", "decision-identity", self_target, "确认本人", ("identity-order", "identity-before-debt"), ("identity",))
        edge("recording-introduction", "recording-notice", "introduce-purpose", "告知录音后说明来意", ("recording-notice", "identity-order"))
    else:
        edge("connected-recording", "decision-connection", "recording-notice", "接通后先告知录音", ("connection-branch", "identity-order"))
        edge("recording-identity", "recording-notice", "decision-identity", "告知录音后确认身份", ("recording-notice", "identity-order"))
        edge("identity-self", "decision-identity", "introduce-purpose", "确认本人后说明来意", ("identity-order", "identity-before-debt"), ("identity",))
    edge("identity-unconfirmed", "decision-identity", "end-unconfirmed-identity", "无法确认身份", ("identity-unconfirmed",), ("identity",))
    edge("unconfirmed-terminal", "end-unconfirmed-identity", "terminal-identity-unconfirmed", "结束通话", ("identity-unconfirmed", "third-party-relay"))
    edge("identity-third-party", "decision-identity", "relay-only", "非本人接听", ("third-party-relay", "third-party-no-debt"), ("identity",))
    edge("relay-stop-decision", "relay-only", "decision-third-party-stop", "只请转告，不披露欠款", ("third-party-relay", "third-party-no-debt"))
    edge("third-party-dnc", "decision-third-party-stop", "terminal-dnc", "要求停止联系", ("third-party-dnc",), ("third-party-stop",), future=True)
    edge("third-party-end", "decision-third-party-stop", "end-unconfirmed-identity", "未要求停止联系，转告后结束", ("third-party-relay",), ("third-party-stop",))
    edge("introduction-payment", "introduce-purpose", "payment-guidance", "身份确认后才披露欠款并提供还款信息", ("identity-before-debt", "payment-details", "prohibited-language", "no-legal-threat"), ("prohibited-content",))
    edge("payment-response", "payment-guidance", "decision-response", "询问还款或分期意向", ("payment-options",))
    edge("response-ptp", "decision-response", "record-ptp", "承诺还款", ("ptp-record",), ("response",))
    edge("ptp-sms", "record-ptp", "future-sms", "安排未来短信提醒", ("ptp-record", "ptp-sms"), future=True)
    edge("sms-ptp-terminal", "future-sms", "terminal-ptp", "完成 PTP 登记", ("ptp-sms",), future=True)
    edge("response-soft", "decision-response", "installment-follow-up", "软拒绝或暂时困难", ("soft-follow-up",), ("response",))
    edge("soft-redial-terminal", "installment-follow-up", "terminal-redial", "安排分期沟通和后续跟进", ("soft-follow-up",), future=True)
    edge("response-hard", "decision-response", "case-escalation", "硬拒绝或否认债务", ("hard-escalation",), ("response",))
    edge("hard-escalation-terminal", "case-escalation", "terminal-escalation", "等待人工或法务处理", ("hard-escalation",), future=True)
    edge("response-dispute", "decision-response", "human-transfer", "投诉、异议或指定高风险短语", ("dispute-human",), ("response",), future=True)
    edge("response-emotion", "decision-response", "human-transfer", "情绪持续超过来源阈值", ("emotion-human",), ("response",), future=True)
    edge("human-terminal", "human-transfer", "terminal-human", "进入人工跟进", ("dispute-human", "emotion-human"), future=True)
    edge("response-invalid", "decision-response", "record-invalid-call", "立即挂断或无法沟通", ("invalid-retry",), ("response",))
    edge("invalid-frequency", "record-invalid-call", "gate-post-call-frequency", "记录后返回频次 Gate", ("invalid-retry",))
    for offset, draft in enumerate((item for item in drafts if item.mapping_key.startswith("extra-human:")), start=1):
        guard_id = f"extra-human-{offset}"
        guard(guard_id, draft.line.text, (draft.mapping_key,))
        edge(
            f"response-extra-human-{offset}",
            "decision-response",
            "human-transfer",
            draft.line.text,
            (draft.mapping_key,),
            (guard_id,),
            future=True,
        )

    frozen_mapping = {
        key: {kind: tuple(values) for kind, values in kinds.items()}
        for key, kinds in mapping.items()
    }
    return (
        tuple(nodes),
        tuple(edges),
        tuple(guards),
        tuple(terminals),
        tuple(rule_by_key.values()),
        frozen_mapping,
    )


def _materialize_rules(
    drafts: tuple[_RuleDraft, ...],
    source_file_ref: str,
    mapping: dict[str, dict[str, tuple[str, ...]]],
) -> tuple[AgentControlLoopOutboundRule, ...]:
    result: list[AgentControlLoopOutboundRule] = []
    for draft in drafts:
        item = mapping.get(draft.mapping_key, {})
        result.append(
            AgentControlLoopOutboundRule(
                rule_id=draft.rule_id,
                group=draft.group,
                source_file_ref=source_file_ref,
                locator=draft.line.locator,
                excerpt=draft.line.text,
                parameters=list(draft.parameters),
                expected_relation=draft.expected_relation,
                expected_action=draft.expected_action,
                coverage_state=draft.coverage_state,
                mapped_node_ids=list(item.get("nodes", ())),
                mapped_edge_ids=list(item.get("edges", ())),
                mapped_guard_ids=list(item.get("guards", ())),
                mapped_terminal_ids=list(item.get("terminals", ())),
            )
        )
    return tuple(result)


def _graph_integrity(
    rules: tuple[AgentControlLoopOutboundRule, ...],
    *,
    nodes: tuple[AgentControlLoopOutboundNode, ...],
    edges: tuple[AgentControlLoopOutboundEdge, ...],
    guards: tuple[AgentControlLoopOutboundGuard, ...],
    terminals: tuple[AgentControlLoopOutboundTerminal, ...],
    order_relation: str,
) -> AgentControlLoopOutboundGraphIntegrity:
    node_ids = [item.node_id for item in nodes]
    edge_ids = [item.edge_id for item in edges]
    guard_ids = [item.guard_id for item in guards]
    terminal_ids = [item.terminal_id for item in terminals]
    unique_ids = all(
        len(values) == len(set(values))
        for values in (node_ids, edge_ids, guard_ids, terminal_ids)
    )
    node_set = set(node_ids)
    guard_set = set(guard_ids)
    no_dangling = all(
        edge.from_node_id in node_set
        and edge.to_node_id in node_set
        and set(edge.guard_ids).issubset(guard_set)
        for edge in edges
    )
    start_nodes = [item.node_id for item in nodes if item.kind == "start"]
    unique_start = start_nodes == ["out-node-start"]
    reachable = _reachable_nodes("out-node-start", edges) if unique_start and no_dangling else set()
    terminal_nodes = {item.node_id for item in terminals}
    outgoing = defaultdict(set)
    reverse = defaultdict(set)
    for edge in edges:
        outgoing[edge.from_node_id].add(edge.to_node_id)
        reverse[edge.to_node_id].add(edge.from_node_id)
    every_nonterminal = all(
        node.node_id in outgoing for node in nodes if node.node_id not in terminal_nodes
    ) and all(node.node_id not in outgoing for node in nodes if node.node_id in terminal_nodes)
    can_reach_terminal = set(terminal_nodes)
    queue = deque(terminal_nodes)
    while queue:
        current = queue.popleft()
        for previous in reverse[current]:
            if previous not in can_reach_terminal:
                can_reach_terminal.add(previous)
                queue.append(previous)
    identity_to_recording = _path_exists(
        "out-node-decision-identity", "out-node-recording-notice", edges
    )
    recording_to_identity = _path_exists(
        "out-node-recording-notice", "out-node-decision-identity", edges
    )
    identity_to_payment = _path_exists(
        "out-node-decision-identity", "out-node-payment-guidance", edges
    )
    order_valid = identity_to_payment and (
        (order_relation == "identity_before_recording" and identity_to_recording and not recording_to_identity)
        or (order_relation == "recording_before_identity" and recording_to_identity and not identity_to_recording)
    )
    third_party_reachable = _reachable_nodes("out-node-relay-only", edges)
    third_party_boundary = not bool(
        third_party_reachable
        & {
            "out-node-payment-guidance",
            "out-node-decision-response",
            "out-node-record-ptp",
            "out-node-future-sms",
        }
    )
    all_rules_mapped = all(
        rule.coverage_state == "covered"
        and bool(
            rule.mapped_node_ids
            or rule.mapped_edge_ids
            or rule.mapped_guard_ids
            or rule.mapped_terminal_ids
        )
        for rule in rules
    )
    return AgentControlLoopOutboundGraphIntegrity(
        unique_start=unique_start,
        unique_ids=unique_ids,
        no_dangling_edges=no_dangling,
        all_nodes_reachable=set(node_ids) == reachable,
        all_terminals_reachable=terminal_nodes.issubset(reachable),
        every_nonterminal_has_outgoing=every_nonterminal,
        every_node_can_reach_terminal=set(node_ids).issubset(can_reach_terminal),
        critical_order_valid=order_valid,
        third_party_boundary_valid=third_party_boundary,
        all_rules_mapped=all_rules_mapped,
    )


def _reachable_nodes(start: str, edges: tuple[AgentControlLoopOutboundEdge, ...]) -> set[str]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        adjacency[edge.from_node_id].add(edge.to_node_id)
    result = {start}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for target in adjacency[current]:
            if target not in result:
                result.add(target)
                queue.append(target)
    return result


def _path_exists(start: str, target: str, edges: tuple[AgentControlLoopOutboundEdge, ...]) -> bool:
    return target in _reachable_nodes(start, edges)


def _reachable_terminal_count(
    nodes: tuple[AgentControlLoopOutboundNode, ...],
    edges: tuple[AgentControlLoopOutboundEdge, ...],
    terminals: tuple[AgentControlLoopOutboundTerminal, ...],
) -> int:
    del nodes
    reachable = _reachable_nodes("out-node-start", edges)
    return sum(item.node_id in reachable for item in terminals)


def _report_docx(
    outcome: AgentControlLoopOutboundFlowOutcome,
    source: OutboundSourceInput,
) -> bytes:
    integrity = outcome.graph_integrity
    blocks: list[tuple[str, object]] = [
        ("title", "信用卡 M1 逾期用户 AI 外呼流程设计"),
        ("body", NO_EXECUTION_BOUNDARY),
        ("body", SOURCE_LIMITATION),
        ("body", f"批准来源：{source.display_path}；file_ref={source.file_ref}；原始 Operations-008 文件未修改。"),
        ("body", "最终合规审批未发生；业务与合规负责人必须复核规则口径、话术和未来系统接入。"),
        ("heading", "一、来源规则账本"),
        ("table", _outcome_tables(outcome)[0]),
        ("heading", "二、流程节点表"),
        ("table", _outcome_tables(outcome)[1]),
        ("heading", "三、边与守卫表"),
        ("table", _outcome_tables(outcome)[2]),
        ("heading", "四、守卫参数表"),
        ("table", _outcome_tables(outcome)[3]),
        ("heading", "五、终态表"),
        ("table", _outcome_tables(outcome)[4]),
        ("heading", "六、图完整性与审批边界"),
        ("table", _outcome_tables(outcome)[5]),
        (
            "body",
            f"完整性结论：唯一 START={integrity.unique_start}；所有节点可达={integrity.all_nodes_reachable}；"
            f"终态可达={outcome.reachable_terminal_count}/{outcome.terminal_count}；"
            f"规则覆盖={outcome.covered_count}/{outcome.atomic_requirement_count}。",
        ),
    ]
    return _docx_bytes(blocks)


def _outcome_tables(outcome: AgentControlLoopOutboundFlowOutcome) -> tuple[list[list[str]], ...]:
    rule_table = [[
        "rule_id", "group", "locator", "excerpt", "parameters", "expected_relation",
        "expected_action", "coverage_state", "mapped_elements",
    ]] + [
        [
            rule.rule_id,
            rule.group,
            rule.locator,
            rule.excerpt,
            _parameter_text(rule.parameters),
            rule.expected_relation,
            rule.expected_action,
            rule.coverage_state,
            "|".join(
                [
                    *rule.mapped_node_ids,
                    *rule.mapped_edge_ids,
                    *rule.mapped_guard_ids,
                    *rule.mapped_terminal_ids,
                ]
            ),
        ]
        for rule in outcome.rules
    ]
    node_table = [["node_id", "label", "kind", "source_rule_ids", "future_action"]] + [
        [node.node_id, node.label, node.kind, "|".join(node.source_rule_ids), _bool(node.future_action)]
        for node in outcome.nodes
    ]
    edge_table = [[
        "edge_id", "from_node_id", "to_node_id", "label", "guard_ids", "source_rule_ids", "future_action",
    ]] + [
        [
            edge.edge_id,
            edge.from_node_id,
            edge.to_node_id,
            edge.label,
            "|".join(edge.guard_ids),
            "|".join(edge.source_rule_ids),
            _bool(edge.future_action),
        ]
        for edge in outcome.edges
    ]
    guard_table = [["guard_id", "label", "parameters", "source_rule_ids"]] + [
        [guard.guard_id, guard.label, _parameter_text(guard.parameters), "|".join(guard.source_rule_ids)]
        for guard in outcome.guards
    ]
    terminal_table = [["terminal_id", "node_id", "label", "source_rule_ids", "source_listed"]] + [
        [
            terminal.terminal_id,
            terminal.node_id,
            terminal.label,
            "|".join(terminal.source_rule_ids),
            _bool(terminal.source_listed),
        ]
        for terminal in outcome.terminals
    ]
    integrity_table = [["fact", "value"]] + [
        [key, _bool(bool(value))]
        for key, value in outcome.graph_integrity.model_dump().items()
    ] + [
        ["source_rule_group_count", str(outcome.source_rule_group_count)],
        ["atomic_requirement_count", str(outcome.atomic_requirement_count)],
        ["covered_count", str(outcome.covered_count)],
        ["unsupported_count", str(outcome.unsupported_count)],
        ["conflict_count", str(outcome.conflict_count)],
        ["node_count", str(outcome.node_count)],
        ["edge_count", str(outcome.edge_count)],
        ["guard_count", str(outcome.guard_count)],
        ["terminal_count", str(outcome.terminal_count)],
        ["reachable_terminal_count", str(outcome.reachable_terminal_count)],
        ["status", outcome.status],
        ["external_action", outcome.external_action],
    ]
    return rule_table, node_table, edge_table, guard_table, terminal_table, integrity_table


def _docx_bytes(blocks: list[tuple[str, object]]) -> bytes:
    def run(text: str, *, bold: bool = False, size: int = 20) -> str:
        properties = (
            f"<w:rPr>{'<w:b/>' if bold else ''}"
            f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>'
        )
        return f'<w:r>{properties}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'

    def paragraph(text: str, *, bold: bool = False, size: int = 20) -> str:
        return f"<w:p>{run(text, bold=bold, size=size)}</w:p>"

    def table(rows: list[list[str]]) -> str:
        def cell(value: str, *, header: bool = False) -> str:
            return "<w:tc><w:tcPr/><w:p>" + run(value, bold=header, size=15) + "</w:p></w:tc>"

        xml_rows = "".join(
            "<w:tr>" + "".join(cell(str(value), header=index == 0) for value in row) + "</w:tr>"
            for index, row in enumerate(rows)
        )
        return (
            "<w:tbl><w:tblPr><w:tblBorders>"
            '<w:top w:val="single" w:sz="4" w:color="999999"/>'
            '<w:left w:val="single" w:sz="4" w:color="999999"/>'
            '<w:bottom w:val="single" w:sz="4" w:color="999999"/>'
            '<w:right w:val="single" w:sz="4" w:color="999999"/>'
            '<w:insideH w:val="single" w:sz="4" w:color="BBBBBB"/>'
            '<w:insideV w:val="single" w:sz="4" w:color="BBBBBB"/>'
            "</w:tblBorders></w:tblPr>" + xml_rows + "</w:tbl>"
        )

    body: list[str] = []
    for kind, value in blocks:
        if kind == "title":
            body.append(paragraph(str(value), bold=True, size=34))
        elif kind == "heading":
            body.append(paragraph(str(value), bold=True, size=26))
        elif kind == "body":
            body.append(paragraph(str(value), size=20))
        elif kind == "table":
            body.append(table(value))  # type: ignore[arg-type]
        else:
            raise ValueError(f"unknown DOCX block: {kind}")
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W_NS}"><w:body>'
        + "".join(body)
        + '<w:sectPr><w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/>'
        '<w:pgMar w:top="540" w:right="540" w:bottom="540" w:left="540"/>'
        "</w:sectPr></w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document)
    return output.getvalue()


def _parse_generated_docx(content: bytes) -> tuple[bool, str, list[list[list[str]]], str]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = set(archive.namelist())
            if "word/document.xml" not in names:
                raise KeyError("word/document.xml")
            root = ET.fromstring(archive.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError) as exc:
        return False, "", [], f"DOCX 无法解析：{type(exc).__name__}"
    text = "\n".join(node.text or "" for node in root.iter(f"{W}t"))
    tables: list[list[list[str]]] = []
    for raw_table in root.iter(f"{W}tbl"):
        table: list[list[str]] = []
        for raw_row in raw_table.findall(f"{W}tr"):
            table.append(
                [
                    "".join(node.text or "" for node in cell.iter(f"{W}t"))
                    for cell in raw_row.findall(f"{W}tc")
                ]
            )
        tables.append(table)
    return True, text, tables, f"DOCX 可解析，共 {len(tables)} 个结构化表格"


def _unique_prefix(lines: tuple[_SourceLine, ...], prefix: str) -> _SourceLine:
    matches = [line for line in lines if line.text.startswith(prefix)]
    if len(matches) != 1:
        raise OutboundFlowValidationError(
            "outbound_rule_cardinality",
            f"规范性规则必须唯一：{prefix}，实际 {len(matches)} 条",
        )
    return matches[0]


def _required_match(pattern: str, line: _SourceLine, code: str) -> re.Match[str]:
    match = re.search(pattern, line.text)
    if match is None:
        raise OutboundFlowValidationError(code, f"{line.locator} 参数无法解析：{line.text}")
    return match


def _clock(hour: str, minute: str, line: _SourceLine) -> str:
    parsed_hour = int(hour)
    parsed_minute = int(minute)
    if not 0 <= parsed_hour <= 23 or not 0 <= parsed_minute <= 59:
        raise OutboundFlowValidationError("outbound_time_invalid", f"{line.locator} 包含非法时刻")
    return f"{parsed_hour:02d}:{parsed_minute:02d}"


def _positive_int(value: str, code: str) -> int:
    parsed = int(value)
    if parsed <= 0 or parsed > 10_000:
        raise OutboundFlowValidationError(code, f"参数必须为合理正整数：{value}")
    return parsed


def _is_normative_line(line: _SourceLine) -> bool:
    text = line.text
    if not text or text == "---" or text.startswith("##") or text.startswith("###"):
        return False
    if text.startswith("来源："):
        return False
    return text.startswith("**") or text.startswith("-") or text.startswith("每条路径")


def _parameter(name: str, value: str, unit: str | None = None) -> AgentControlLoopOutboundRuleParameter:
    return AgentControlLoopOutboundRuleParameter(name=name, value=value, unit=unit)


def _parameter_text(parameters: Iterable[AgentControlLoopOutboundRuleParameter]) -> str:
    return "；".join(
        f"{item.name}={item.value}{item.unit or ''}" for item in parameters
    )


def _bool(value: bool) -> str:
    return "true" if value else "false"


def _check(check_id: str, label: str, passed: bool, detail: str) -> OutboundVerifierCheck:
    return OutboundVerifierCheck(check_id=check_id, label=label, passed=bool(passed), detail=detail)
