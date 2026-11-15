"""Five-factor risk judgement (人机共驾设计指导手册 v1.1, sections 4.2-4.6).

Deterministic and model-free.  Callers describe one action with five factor
values plus its action form; this module applies the fixed merge rules and
returns a :class:`RiskJudgement` that can be shown to the user and replayed in
review.  Operation kinds only supply default factor values -- the level is
always computed here, never looked up.

Merge rules (fixed order, manual 4.3):
1. restricted first  -- forbidden authority or major batch => L5
2. take highest      -- otherwise the highest factor floor
3. unknown as high   -- unknown facts are assumed at the high end and flagged
4. reason no downgrade -- urgency, trust, history never change a factor
5. per action        -- each action is judged on its own
6. recheck on change -- any change of object/content/scope/authority re-runs 1-5

Autonomy (manual 4.4): actual AL = min(level cap, action form).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from packages.contracts.risk_judgement import (
    ActionForm, Authority, AutonomyLevel, FactorFinding, FactorKey, Intervention,
    MergeRule, Recoverability, RiskJudgement, RiskLevel, Scope, Sensitivity, StateChange,
)

# ---------------------------------------------------------------- thresholds (4.6)
THRESHOLDS = {
    "internal_batch_people": 10,     # > 10 people  => internal batch (L4)
    "internal_batch_records": 20,    # > 20 records => internal batch (L4)
    "major_batch_records": 50,       # >= 50 irreversible deletes/overwrites => L5
    "major_batch_external": 100,     # >= 100 external recipients => L5
    "full_undo_hours": 24,           # undo kept >= 24h counts as fully reversible
    "strong_confirm_minutes": 30,
    "clarify_rounds": 2,
    "consistency_target": 0.85,
}

# ---------------------------------------------------------------- factor floors (4.2)
STATE_FLOOR: dict[StateChange, tuple[RiskLevel, str]] = {
    "read_only": ("L0", "只读查看"),
    "own_content": ("L1", "修改本人内容"),
    "draft": ("L2", "生成待检查的草稿或意见"),
    "internal_record": ("L3", "新建或修改内部记录、发送内部消息"),
    "external_commit": ("L4", "对外发送、正式提交、作出承诺或付款"),
}
SCOPE_FLOOR: dict[Scope, tuple[RiskLevel, str]] = {
    "none": ("L0", "只读，不计范围"),
    "self": ("L0", "仅本人"),
    "internal_small": ("L3", "内部不超过 10 人或 20 条记录"),
    "internal_batch": ("L4", "内部超过 10 人或 20 条记录"),
    "external": ("L4", "涉及外部对象"),
    "major_batch": ("L5", "重大批量"),
}
RECOVER_FLOOR: dict[Recoverability, tuple[RiskLevel, str]] = {
    "full": ("L0", "可完整撤销（入口保留不少于 24 小时）"),
    "partial": ("L3", "只能部分恢复或需他人配合"),
    "irreversible": ("L4", "不可收回"),
}
SENSITIVITY_FLOOR: dict[Sensitivity, tuple[RiskLevel, str]] = {
    "routine": ("L0", "常规业务资料"),
    "controlled": ("L3", "内部受控资料"),
    "high": ("L4", "高敏感资料"),
}
AUTHORITY_FLOOR: dict[Authority, tuple[RiskLevel, str]] = {
    "own": ("L0", "本人有权且无需审批"),
    "approval_needed": ("L4", "需要审批"),
    "forbidden": ("L5", "无权或明令禁止"),
}

FACTOR_LABELS: dict[FactorKey, str] = {
    "state_change": "状态变化",
    "scope": "影响范围",
    "recoverability": "恢复能力",
    "sensitivity": "数据敏感度",
    "authority": "权限与制度",
}

# ---------------------------------------------------------------- autonomy (4.4)
LEVEL_CAP: dict[RiskLevel, AutonomyLevel] = {
    "L0": "AL5", "L1": "AL4", "L2": "AL2", "L3": "AL3", "L4": "AL3", "L5": "AL2",
}
FORM_AL: dict[ActionForm, tuple[AutonomyLevel | None, str]] = {
    "status_only": ("AL0", "只展示状态"),
    "suggest": ("AL1", "只提出建议"),
    "content": ("AL2", "只生成内容"),
    "implement": (None, "需要实施"),        # takes the level cap
    "maintenance": ("AL5", "无业务影响的后台维护"),
}

RULE_LABELS: dict[MergeRule, str] = {
    "restricted_first": "受限优先",
    "take_highest": "就高",
    "unknown_as_high": "不明按高",
    "reason_no_downgrade": "理由不降级",
    "per_action": "逐动作定级",
    "recheck_on_change": "变化即重判",
}

INTERVENTION_ORDER: list[tuple[Intervention, str]] = [
    ("user_takeover", "用户主动接管"),
    ("restricted", "受限"),
    ("missing_info", "信息缺失"),
    ("business_judgment", "业务判断"),
    ("execution_authorization", "执行授权"),
    ("execution_exception", "执行异常"),
]

_LEVELS: list[RiskLevel] = ["L0", "L1", "L2", "L3", "L4", "L5"]
_ALS: list[AutonomyLevel] = ["AL0", "AL1", "AL2", "AL3", "AL4", "AL5"]


@dataclass
class ActionFactors:
    """One action described by the five factors (plus its form)."""

    state_change: StateChange
    scope: Scope
    recoverability: Recoverability
    sensitivity: Sensitivity
    authority: Authority
    action_form: ActionForm = "implement"
    approval_granted: bool = False
    # Factors whose value is an assumption at the high end (merge rule 3).
    unknown: set[FactorKey] = field(default_factory=set)
    basis: dict[FactorKey, str] = field(default_factory=dict)
    # Pressure signals seen in the request (urgency, trust ...). Recorded, never used.
    pressure_signals: list[str] = field(default_factory=list)
    revision: int = 1
    # Interventions present right now, in any order; sorted per manual 4.5.
    interventions: set[Intervention] = field(default_factory=set)
    intervention_details: dict[Intervention, str] = field(default_factory=dict)


def scope_from_counts(
    *, internal_people: int = 0, external_people: int = 0, records: int = 0,
    irreversible_records: int = 0, read_only: bool = False,
) -> Scope:
    """Map counted targets to a scope value using the default thresholds (4.6)."""

    if read_only:
        return "none"
    if (irreversible_records >= THRESHOLDS["major_batch_records"]
            or external_people >= THRESHOLDS["major_batch_external"]):
        return "major_batch"
    if external_people > 0:
        return "external"
    if (internal_people > THRESHOLDS["internal_batch_people"]
            or records > THRESHOLDS["internal_batch_records"]):
        return "internal_batch"
    if internal_people > 0 or records > 0:
        return "internal_small"
    return "self"


def recoverability_from_undo(*, undo_hours: float | None, needs_others: bool = False) -> Recoverability:
    """Undo windows shorter than 24h (e.g. 30s unsend) count as irreversible."""

    if undo_hours is not None and undo_hours >= THRESHOLDS["full_undo_hours"] and not needs_others:
        return "full"
    if needs_others:
        return "partial"
    return "irreversible"


def _max(levels: list[RiskLevel]) -> RiskLevel:
    return max(levels, key=_LEVELS.index)


def judge(f: ActionFactors) -> RiskJudgement:
    rows: list[tuple[FactorKey, str, tuple[RiskLevel, str]]] = [
        ("state_change", f.state_change, STATE_FLOOR[f.state_change]),
        ("scope", f.scope, SCOPE_FLOOR[f.scope]),
        ("recoverability", f.recoverability, RECOVER_FLOOR[f.recoverability]),
        ("sensitivity", f.sensitivity, SENSITIVITY_FLOOR[f.sensitivity]),
        ("authority", f.authority, AUTHORITY_FLOOR[f.authority]),
    ]
    rules: list[MergeRule] = []
    notes: list[str] = []

    restricted = f.authority == "forbidden" or f.scope == "major_batch"
    if restricted:
        level: RiskLevel = "L5"
        rules.append("restricted_first")
        notes.append("受限优先：" + ("权限与制度为无权或明令禁止" if f.authority == "forbidden" else "影响范围达到重大批量")
                     + "，直接判为 L5，其余因子不再参与。")
    else:
        level = _max([floor for _, _, (floor, _) in rows])
        rules.append("take_highest")
        drivers = [FACTOR_LABELS[key] for key, _, (floor, _) in rows if floor == level]
        notes.append(f"就高：取各因子下限中最高的 {level}（由{'、'.join(drivers)}决定）。")
    if f.unknown:
        rules.append("unknown_as_high")
        notes.append("不明按高：" + "、".join(FACTOR_LABELS[k] for k in sorted(f.unknown))
                     + "尚未确定，按可能的较高值判定；补齐后按事实重判。")
    if f.pressure_signals:
        rules.append("reason_no_downgrade")
        notes.append("理由不降级：请求中出现「" + "、".join(f.pressure_signals[:3])
                     + "」，不改变任何因子取值。")
    if f.revision > 1:
        rules.append("recheck_on_change")
        notes.append(f"变化即重判：第 {f.revision} 版内容重新判定，原确认失效。")

    cap = LEVEL_CAP[level]
    if level == "L4" and f.authority == "approval_needed" and not f.approval_granted:
        cap = "AL2"
        notes.append("需要审批的 L4 动作，审批通过前停在 AL2。")
    form_al, form_label = FORM_AL[f.action_form]
    actual = cap if form_al is None else min(cap, form_al, key=_ALS.index)

    findings = [
        FactorFinding(
            key=key, label=FACTOR_LABELS[key], value=value, value_label=value_label, floor=floor,
            assumed=key in f.unknown, basis=f.basis.get(key, "")[:300],
            drives_level=(floor == level) or (restricted and floor == "L5"),
        )
        for key, value, (floor, value_label) in rows
    ]

    ordered = [(kind, label) for kind, label in INTERVENTION_ORDER if kind in f.interventions]
    first = ordered[0] if ordered else None
    follow_ups = [
        label + (f"：{f.intervention_details[kind]}" if f.intervention_details.get(kind) else "")
        for kind, label in ordered[1:]
    ]
    return RiskJudgement(
        factors=findings,
        rules_applied=rules,
        rule_notes=notes[:8],
        risk_level=level,
        autonomy_cap=cap,
        action_form=f.action_form,
        action_form_label=form_label,
        autonomy_level=actual,
        intervention=first[0] if first else None,
        intervention_label=(
            first[1] + (f"：{f.intervention_details[first[0]]}" if f.intervention_details.get(first[0]) else "")
        ) if first else None,
        follow_ups=follow_ups[:5],
    )


# ---------------------------------------------------------------- text signals
# Keyword lists are a demo-grade stand-in for an organisation's data
# classification; they only ever raise a factor, never lower it.
HIGH_SENSITIVE_WORDS = (
    "薪酬", "薪资", "工资", "月薪", "年薪", "身份证", "银行卡", "银行账号", "财务凭证", "发票",
    "报价", "折扣", "底价", "价格", "机密",
)
CONTROLLED_WORDS = ("合同", "客户名单", "未公开", "排期", "方案草案", "内部受控")
FORBIDDEN_WORDS = ("最低折扣", "最低价承诺", "无须审批", "保底")
PRESSURE_WORDS = ("很急", "着急", "赶时间", "马上", "以后不用问", "信任你", "熟人", "直接发")


def sensitivity_of(*texts: str) -> tuple[Sensitivity, str]:
    joined = "".join(texts)
    hits = [w for w in HIGH_SENSITIVE_WORDS if w in joined]
    if hits:
        return "high", "内容含" + "、".join(hits[:3]) + "，属于高敏感资料。"
    hits = [w for w in CONTROLLED_WORDS if w in joined]
    if hits:
        return "controlled", "内容含" + "、".join(hits[:3]) + "，属于内部受控资料。"
    return "routine", "未发现组织标注的敏感字段，按常规业务资料。"


def forbidden_terms(*texts: str) -> list[str]:
    joined = "".join(texts)
    return [w for w in FORBIDDEN_WORDS if w in joined]


def pressure_of(*texts: str) -> list[str]:
    joined = "".join(texts)
    return [w for w in PRESSURE_WORDS if w in joined]
