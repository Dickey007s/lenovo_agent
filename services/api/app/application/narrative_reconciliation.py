"""Reconcile model narrative against server-verified structured outcomes.

The verified outcome remains authoritative.  This module only decides whether a
parsed, citation-scoped model narrative may be adopted, shown as supplemental, or
retained as a rejected audit draft.  It never verifies open-ended semantic quality.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from packages.contracts.harness_models import (
    AgentControlLoopEffectReceipt,
    AgentControlLoopNarrativeConflict,
    AgentControlLoopNarrativeReconciliation,
)


_CONTROL_WHITESPACE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+")
_SPACE = re.compile(r"\s+")
_PRIORITY = re.compile(r"\bP([0-4])\b", re.IGNORECASE)
_PRIORITY_COUNT = re.compile(r"\bP([0-4])\s*(?:=|:|：)?\s*(\d+)\b", re.IGNORECASE)
_GROUP_COUNT = re.compile(r"(?:共|形成|得到|包含|汇总为)\s*(\d+)\s*(?:个|条)?(?:问题)?(?:组|组合)")
_ROW_COUNT = re.compile(r"(\d+)\s*行")
_LIMITED_COVERAGE = re.compile(
    r"(?:本次|当前|此次).{0,18}(?:分析|结论).{0,24}(?:仅|只|基于).{0,24}?(\d+)\s*行"
    r"|(?:仅|只)(?:展示|读取|提供|分析)?\s*前?\s*(\d+)\s*行.{0,30}(?:样本|分析|结论|覆盖不确定)"
    r"|前\s*(\d+)\s*行.{0,30}(?:样本|分析|结论|覆盖不确定)"
)
_UNSUPPORTED_SOLUTION = re.compile(
    r"(?:建议|应当|应该|应|需要|立即|优先).{0,90}"
    r"(?:新增|增加|拆分|改为|调整|引入|实现|校验|提示|确认|弹窗|缓存|预加载|异步|路由|重试)"
)
_APPROVAL_HEDGE = re.compile(r"(?:草案|待.{0,12}(?:批准|补充|确认|复核)|未批准|仅供参考|不作为当前结论)")
_REDUNDANT_WORK = re.compile(r"(?:全部|全量|完整|重新).{0,24}(?:统计|分析|覆盖|计算|排序)")
_FINAL_PRIORITY = re.compile(
    r"(?:列为|调整为|改为|降为|最终(?:为|列为)?|建议(?:为|列为)?)\s*(P[0-4])",
    re.IGNORECASE,
)


def _safe_text(value: object, *, limit: int = 500) -> str:
    text = _SPACE.sub(" ", _CONTROL_WHITESPACE.sub(" ", str(value))).strip()
    return text[:limit] or "未提供可展示文字"


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:12]}"


def _outcome_revision(outcome: dict[str, Any]) -> str:
    encoded = json.dumps(
        outcome, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"outcome-rev-{hashlib.sha256(encoded).hexdigest()[:16]}"


def build_verified_effect_context(
    receipt: AgentControlLoopEffectReceipt | None,
) -> dict[str, Any] | None:
    """Project a compact authoritative context for the Analyst.

    DR-0052 initially admits the full-log UX prioritization outcome.  The envelope
    is intentionally generic so later deterministic outcomes can add their own
    compact projector without changing the Analyst or reconciliation protocol.
    """

    if receipt is None or receipt.status != "passed" or receipt.ux_prioritization_outcome is None:
        return None
    outcome = receipt.ux_prioritization_outcome
    outcome_dump = outcome.model_dump(mode="json")
    matrix: dict[str, str] = {}
    for group in outcome.groups:
        if group.priority is None or group.frequency == "边界待确认":
            continue
        key = f"{group.frequency}|{group.severity}"
        previous = matrix.get(key)
        if previous is None:
            matrix[key] = group.priority
        elif previous != group.priority:
            matrix.pop(key, None)
    groups = [
        {
            "group_id": group.group_id,
            "page": group.page_name,
            "operation": group.operation,
            "pain": group.pain_type,
            "severity": group.severity,
            "frequency": group.frequency,
            "priority": group.priority,
            "scenario_count": group.scenario_count,
            "denominator": group.denominator,
        }
        for group in outcome.groups
    ]
    return {
        "authority": "server_verified_deterministic_outcome",
        "outcome_type": "ux_prioritization_outcome",
        "outcome_revision": _outcome_revision(outcome_dump),
        "effect_receipt_id": receipt.receipt_id,
        "instruction": (
            "以下 facts 是服务端从批准原始字节全量复算并通过 Artifact Verifier 的当前事实。"
            "files 中的 bounded Preview 只用于逐字引用，不得用其行数覆盖或降级这些事实。"
        ),
        "facts": {
            "status": outcome.status,
            "source_row_count": outcome.source_row_count,
            "analyzed_row_count": outcome.analyzed_row_count,
            "included_pain_row_count": outcome.included_pain_row_count,
            "excluded_no_pain_count": outcome.excluded_no_pain_count,
            "success_with_pain_count": outcome.success_with_pain_count,
            "group_count": outcome.group_count,
            "priority_counts": dict(outcome.priority_counts),
            "duplicate_group_count": outcome.duplicate_group_count,
            "duplicate_extra_count": outcome.duplicate_extra_count,
            "unmapped_count": outcome.unmapped_count,
            "uncovered_spec_count": outcome.uncovered_spec_count,
            "rule_conflict_count": len(outcome.rule_conflicts),
            "suggestion_status": outcome.suggestion_status,
            "priority_matrix": matrix,
            "groups": groups,
        },
    }


def _narrative_fields(result: object) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = [("summary", _safe_text(getattr(result, "summary")))]
    for index, finding in enumerate(getattr(result, "findings")):
        for name in ("title", "detail", "fact_summary", "impact"):
            value = getattr(finding, name, None)
            if value:
                fields.append((f"findings[{index}].{name}", _safe_text(value)))
    for index, follow_up in enumerate(getattr(result, "follow_ups")):
        fields.append((f"follow_ups[{index}]", _safe_text(follow_up)))
    return fields


def _sentences(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"[。！？!?；;\n]+", text) if item.strip()]


def _operation_token(operation: str) -> str:
    token = operation
    for removable in ("点击", "按钮", "操作", "进行", "选择"):
        token = token.replace(removable, "")
    return token.strip()


def _conflict(
    *,
    run_id: str,
    round_number: int,
    kind: str,
    path: str,
    excerpt: str,
    outcome_path: str,
    expected: object,
    observed: object,
    severity: str = "error",
) -> AgentControlLoopNarrativeConflict:
    expected_text = _safe_text(expected)
    observed_text = _safe_text(observed)
    return AgentControlLoopNarrativeConflict(
        conflict_id=_stable_id(
            "narrative-conflict",
            run_id,
            round_number,
            kind,
            path,
            expected_text,
            observed_text,
        ),
        kind=kind,
        narrative_path=path,
        narrative_excerpt=_safe_text(excerpt),
        outcome_path=outcome_path,
        expected=expected_text,
        observed=observed_text,
        severity=severity,
    )


def reconcile_narrative(
    *,
    run_id: str,
    round_number: int,
    result: object,
    context_used: dict[str, Any] | None,
    current_context: dict[str, Any] | None,
    checked_at: datetime | None = None,
) -> AgentControlLoopNarrativeReconciliation:
    """Return a deterministic adoption receipt for one parsed model result."""

    now = checked_at or datetime.now(timezone.utc)
    if context_used is None:
        return AgentControlLoopNarrativeReconciliation(
            reconciliation_id=_stable_id(
                "narrative-reconciliation", run_id, round_number, "not_applicable"
            ),
            round_number=round_number,
            status="not_applicable",
            authority="model_only",
            model_disposition="adopted",
            model_returned=True,
            message="当前任务没有可对账的服务端确定性成果；模型结果仍需人工复核。",
            checked_at=now,
        )

    expected_revision = str(context_used.get("outcome_revision") or "")
    current_revision = str((current_context or {}).get("outcome_revision") or "")
    effect_receipt_id = str(context_used.get("effect_receipt_id") or "") or None
    if not current_context or expected_revision != current_revision:
        conflict = _conflict(
            run_id=run_id,
            round_number=round_number,
            kind="outcome_revision_mismatch",
            path="verified_effect_context.outcome_revision",
            excerpt="模型返回期间，服务端确定性成果版本已经变化。",
            outcome_path="outcome_revision",
            expected=expected_revision or "缺少版本",
            observed=current_revision or "当前版本不可用",
        )
        return AgentControlLoopNarrativeReconciliation(
            reconciliation_id=_stable_id(
                "narrative-reconciliation", run_id, round_number, "stale", expected_revision
            ),
            round_number=round_number,
            status="stale",
            authority="deterministic_outcome",
            model_disposition="rejected",
            outcome_revision=expected_revision or None,
            effect_receipt_id=effect_receipt_id,
            model_returned=True,
            conflicts=[conflict],
            message="模型说明对应的确定性事实版本已过期，未采用。",
            checked_at=now,
        )

    facts = context_used.get("facts")
    if not isinstance(facts, dict):
        raise ValueError("verified effect context facts are missing")
    source_count = int(facts.get("source_row_count") or 0)
    analyzed_count = int(facts.get("analyzed_row_count") or 0)
    group_count = int(facts.get("group_count") or 0)
    priority_counts = {
        str(key): int(value)
        for key, value in dict(facts.get("priority_counts") or {}).items()
    }
    matrix = {
        str(key): str(value) for key, value in dict(facts.get("priority_matrix") or {}).items()
    }
    groups = [item for item in list(facts.get("groups") or []) if isinstance(item, dict)]
    suggestion_status = str(facts.get("suggestion_status") or "")
    conflicts: list[AgentControlLoopNarrativeConflict] = []
    conflict_keys: set[tuple[str, str, str]] = set()
    comparable_claim_count = 0

    def add_conflict(item: AgentControlLoopNarrativeConflict) -> None:
        key = (item.kind, item.narrative_path, item.observed)
        if key not in conflict_keys:
            conflict_keys.add(key)
            conflicts.append(item)

    for path, text in _narrative_fields(result):
        row_numbers = [int(value) for value in _ROW_COUNT.findall(text)]
        for value in row_numbers:
            if value in {source_count, analyzed_count}:
                comparable_claim_count += 1
        limited_match = _LIMITED_COVERAGE.search(text)
        if limited_match:
            limited_value = int(next(value for value in limited_match.groups() if value))
            if limited_value < analyzed_count:
                add_conflict(
                    _conflict(
                        run_id=run_id,
                        round_number=round_number,
                        kind="incomplete_coverage",
                        path=path,
                        excerpt=text,
                        outcome_path="ux_prioritization_outcome.analyzed_row_count",
                        expected=f"已由服务端全量复算 {analyzed_count}/{source_count} 行",
                        observed=f"模型把当前分析限定为 {limited_value} 行",
                    )
                )

        for match in _GROUP_COUNT.finditer(text):
            observed_group_count = int(match.group(1))
            comparable_claim_count += 1
            if observed_group_count != group_count:
                add_conflict(
                    _conflict(
                        run_id=run_id,
                        round_number=round_number,
                        kind="outcome_count_mismatch",
                        path=path,
                        excerpt=text,
                        outcome_path="ux_prioritization_outcome.group_count",
                        expected=group_count,
                        observed=observed_group_count,
                    )
                )

        for priority_label, raw_count in _PRIORITY_COUNT.findall(text):
            label = f"P{priority_label}"
            if label not in priority_counts:
                continue
            observed_count = int(raw_count)
            comparable_claim_count += 1
            if observed_count != priority_counts[label]:
                add_conflict(
                    _conflict(
                        run_id=run_id,
                        round_number=round_number,
                        kind="outcome_count_mismatch",
                        path=path,
                        excerpt=text,
                        outcome_path=f"ux_prioritization_outcome.priority_counts.{label}",
                        expected=priority_counts[label],
                        observed=observed_count,
                        )
                )

        field_severities = {
            label for label in ("严重", "中等", "轻微") if label in text
        }
        field_frequencies = {
            label for label in ("高频", "中频", "低频") if label in text
        }
        field_final_priorities = _FINAL_PRIORITY.findall(text)
        if (
            len(field_severities) == 1
            and len(field_frequencies) == 1
            and field_final_priorities
        ):
            severity = next(iter(field_severities))
            frequency = next(iter(field_frequencies))
            expected_priority = matrix.get(f"{frequency}|{severity}")
            observed_priority = field_final_priorities[-1].upper()
            if expected_priority:
                comparable_claim_count += 1
                if observed_priority != expected_priority:
                    add_conflict(
                        _conflict(
                            run_id=run_id,
                            round_number=round_number,
                            kind="priority_mismatch",
                            path=path,
                            excerpt=text,
                            outcome_path=(
                                "ux_prioritization_outcome.priority_matrix."
                                f"{frequency}|{severity}"
                            ),
                            expected=expected_priority,
                            observed=observed_priority,
                        )
                    )

        for sentence in _sentences(text):
            priorities = {f"P{value}" for value in _PRIORITY.findall(sentence)}
            final_priority_matches = _FINAL_PRIORITY.findall(sentence)
            observed_final_priority = (
                final_priority_matches[-1].upper()
                if final_priority_matches
                else next(iter(priorities))
                if len(priorities) == 1
                else None
            )
            severity = next(
                (label for label in ("严重", "中等", "轻微") if label in sentence), None
            )
            frequency = next(
                (label for label in ("高频", "中频", "低频") if label in sentence), None
            )
            if severity and frequency and observed_final_priority:
                expected_priority = matrix.get(f"{frequency}|{severity}")
                if expected_priority:
                    comparable_claim_count += 1
                    if observed_final_priority != expected_priority:
                        add_conflict(
                            _conflict(
                                run_id=run_id,
                                round_number=round_number,
                                kind="priority_mismatch",
                                path=path,
                                excerpt=sentence,
                                outcome_path=(
                                    "ux_prioritization_outcome.priority_matrix."
                                    f"{frequency}|{severity}"
                                ),
                                expected=expected_priority,
                                observed=observed_final_priority,
                            )
                        )
            if observed_final_priority:
                for group in groups:
                    page = str(group.get("page") or "")
                    operation = _operation_token(str(group.get("operation") or ""))
                    pain = str(group.get("pain") or "")
                    if not page or page not in sentence or not operation or operation not in sentence:
                        continue
                    if pain and pain not in sentence and not (severity and frequency):
                        continue
                    expected_priority = str(group.get("priority") or "")
                    if not expected_priority:
                        continue
                    comparable_claim_count += 1
                    if observed_final_priority != expected_priority:
                        add_conflict(
                            _conflict(
                                run_id=run_id,
                                round_number=round_number,
                                kind="priority_mismatch",
                                path=path,
                                excerpt=sentence,
                                outcome_path=(
                                    "ux_prioritization_outcome.groups."
                                    f"{group.get('group_id')}.priority"
                                ),
                                expected=expected_priority,
                                observed=observed_final_priority,
                            )
                        )
                    break
            if (
                suggestion_status == "no_approved_solution_source"
                and _UNSUPPORTED_SOLUTION.search(sentence)
                and not _APPROVAL_HEDGE.search(sentence)
            ):
                add_conflict(
                    _conflict(
                        run_id=run_id,
                        round_number=round_number,
                        kind="unsupported_solution_claim",
                        path=path,
                        excerpt=sentence,
                        outcome_path="ux_prioritization_outcome.suggestion_status",
                        expected="没有批准的具体方案来源；只能显示待 UX 负责人补充/批准的模板",
                        observed="模型把具体优化动作写成当前结论或建议",
                    )
                )

        if path.startswith("follow_ups[") and str(source_count) in text:
            if _REDUNDANT_WORK.search(text) or (
                any(token in text for token in ("统计", "分析", "覆盖", "计算", "排序"))
                and any(token in text for token in ("全部", "全量", "完整", "重新"))
            ):
                add_conflict(
                    _conflict(
                        run_id=run_id,
                        round_number=round_number,
                        kind="redundant_completed_work",
                        path=path,
                        excerpt=text,
                        outcome_path="ux_prioritization_outcome.analyzed_row_count",
                        expected=f"{analyzed_count}/{source_count} 行已经完成全量复算",
                        observed="模型要求再次完成已经验证的全量计算",
                    )
                )

    if conflicts:
        status = "contradictory"
        disposition = "rejected"
        message = (
            f"成果已完成，模型说明发现 {len(conflicts)} 项与服务端全量复算不一致，"
            "因此未采用；当前以服务端确定性成果为准。"
        )
    elif comparable_claim_count:
        status = "consistent"
        disposition = "adopted"
        message = "模型说明已与当前结构化确定性事实完成对账，可以作为补充解释展示。"
    else:
        status = "partial"
        disposition = "supplemental"
        message = (
            "模型说明没有提供足够的可比较事实，只作补充草稿；当前结论仍以服务端确定性成果为准。"
        )

    reconciliation_id = _stable_id(
        "narrative-reconciliation",
        run_id,
        round_number,
        expected_revision,
        status,
        *[item.conflict_id for item in conflicts],
    )
    return AgentControlLoopNarrativeReconciliation(
        reconciliation_id=reconciliation_id,
        round_number=round_number,
        status=status,
        authority="deterministic_outcome",
        model_disposition=disposition,
        outcome_revision=expected_revision,
        effect_receipt_id=effect_receipt_id,
        model_returned=True,
        comparable_claim_count=comparable_claim_count,
        conflicts=conflicts,
        message=message,
        checked_at=now,
    )
