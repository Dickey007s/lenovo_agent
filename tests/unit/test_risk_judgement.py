"""Five-factor judgement replays the manual v1.1 calibration answers.

Every expectation below is copied from 人机共驾设计指导手册 v1.1 (4.3 examples,
4.7 judgement pairs) or 边界情形与接管案例库 v1.2 ("判定过程").  If the engine
drifts from the manual, these tests fail.
"""

from datetime import date

import pytest

from packages.contracts.office_actions import ActionInput
from services.api.app.application.office_action_policy import judge_action, prepare_action
from services.api.app.application.risk_judgement import (
    ActionFactors, judge, recoverability_from_undo, scope_from_counts,
)


def F(state, scope, recover, sens, auth, form="implement", **kw):
    return judge(ActionFactors(state, scope, recover, sens, auth, form, **kw))


# (case, factors, expected level, expected AL)
CASE_LIBRARY = [
    ("C00 查看同步状态", F("read_only", "none", "full", "routine", "own", "maintenance"), "L0", "AL5"),
    ("C01 整理个人草稿", F("own_content", "self", "full", "routine", "own"), "L1", "AL4"),
    ("C02 摘录草稿", F("draft", "self", "full", "routine", "own", "content"), "L2", "AL2"),
    ("C02-a 含他人报价", F("draft", "self", "full", "high", "own", "content"), "L4", "AL2"),
    ("C03 给同事建任务", F("internal_record", "internal_small", "partial", "routine", "own"), "L3", "AL3"),
    ("C04 外发报告", F("external_commit", "external", "irreversible", "controlled", "own"), "L4", "AL3"),
    ("C04 需审批未通过", F("external_commit", "external", "irreversible", "controlled", "approval_needed"), "L4", "AL2"),
    ("C04 审批已通过", F("external_commit", "external", "irreversible", "controlled", "approval_needed",
                       approval_granted=True), "L4", "AL3"),
    ("C05 越权价格承诺", F("external_commit", "external", "irreversible", "high", "forbidden"), "L5", "AL2"),
    ("C06 澄清前", F("internal_record", "external", "partial", "routine", "own", unknown={"scope"}), "L4", "AL3"),
    ("C06 澄清后", F("internal_record", "internal_small", "partial", "routine", "own"), "L3", "AL3"),
    ("C07 报销异常核查", F("draft", "self", "full", "high", "own", "content"), "L4", "AL2"),
    ("C08 附件变化重判", F("external_commit", "external", "irreversible", "routine", "own", revision=2), "L4", "AL3"),
    ("C11 内部草稿", F("draft", "self", "full", "routine", "own", "content"), "L2", "AL2"),
    ("C11 对外报告", F("external_commit", "external", "irreversible", "routine", "own"), "L4", "AL3"),
]


@pytest.mark.parametrize("name,result,level,al", CASE_LIBRARY, ids=[c[0] for c in CASE_LIBRARY])
def test_case_library_judgements(name, result, level, al):
    assert (result.risk_level, result.autonomy_level) == (level, al)
    assert len(result.factors) == 5


# Manual 4.7: (description, factors, level, AL)
PAIRS = [
    ("整理本人草稿格式", F("own_content", "self", "full", "routine", "own"), "L1", "AL4"),
    ("整理共享正式文件格式", F("own_content", scope_from_counts(internal_people=6), "partial", "routine", "own"), "L3", "AL3"),
    ("给 3 位同事各建任务", F("internal_record", scope_from_counts(internal_people=3), "partial", "routine", "own"), "L3", "AL3"),
    ("给全部门 40 人建任务", F("internal_record", scope_from_counts(internal_people=40), "partial", "routine", "own"), "L4", "AL3"),
    ("周报发给组内 5 人", F("internal_record", scope_from_counts(internal_people=5), "partial", "routine", "own"), "L3", "AL3"),
    ("同一周报发给客户", F("external_commit", scope_from_counts(external_people=1), "irreversible", "routine", "own"), "L4", "AL3"),
    ("公开资料写摘要", F("draft", "self", "full", "routine", "own", "content"), "L2", "AL2"),
    ("薪酬表写人力成本摘要", F("draft", "self", "full", "high", "own", "content"), "L4", "AL2"),
    ("删除本人草稿（回收站 30 天）", F("own_content", "self", recoverability_from_undo(undo_hours=720), "routine", "own"), "L1", "AL4"),
    ("永久删除共享文件夹 60 个文件", F("internal_record", scope_from_counts(irreversible_records=60), "irreversible", "routine", "own"), "L5", "AL2"),
    ("折扣在个人额度内", F("external_commit", "external", "irreversible", "high", "own"), "L4", "AL3"),
    ("折扣超出个人额度", F("external_commit", "external", "irreversible", "high", "forbidden"), "L5", "AL2"),
    ("外部邮件 30 秒撤消发送", F("external_commit", "external", recoverability_from_undo(undo_hours=30 / 3600), "routine", "own"), "L4", "AL3"),
]


@pytest.mark.parametrize("name,result,level,al", PAIRS, ids=[p[0] for p in PAIRS])
def test_manual_judgement_pairs(name, result, level, al):
    assert (result.risk_level, result.autonomy_level) == (level, al)


def test_restricted_first_ignores_other_factors():
    result = F("read_only", "self", "full", "routine", "forbidden", "suggest")
    assert result.risk_level == "L5" and result.rules_applied[0] == "restricted_first"


def test_unknown_is_flagged_and_reason_never_downgrades():
    result = F("internal_record", "external", "partial", "routine", "own",
               unknown={"scope"}, pressure_signals=["很急"])
    assert {"unknown_as_high", "reason_no_downgrade"} <= set(result.rules_applied)
    assert [f.assumed for f in result.factors if f.key == "scope"] == [True]
    calm = F("internal_record", "external", "partial", "routine", "own", unknown={"scope"})
    assert calm.risk_level == result.risk_level


def test_intervention_order_asks_one_thing_at_a_time():
    result = F("external_commit", "external", "irreversible", "routine", "own",
               interventions={"execution_authorization", "missing_info", "business_judgment"})
    assert result.intervention == "missing_info"
    assert [item.split("：")[0] for item in result.follow_ups] == ["业务判断", "执行授权"]


def test_thresholds():
    assert scope_from_counts(internal_people=10) == "internal_small"
    assert scope_from_counts(internal_people=11) == "internal_batch"
    assert scope_from_counts(records=21) == "internal_batch"
    assert scope_from_counts(external_people=99) == "external"
    assert scope_from_counts(external_people=100) == "major_batch"
    assert scope_from_counts(irreversible_records=49) == "self"
    assert recoverability_from_undo(undo_hours=24) == "full"
    assert recoverability_from_undo(undo_hours=1, needs_others=True) == "partial"


def _action(**kw):
    return ActionInput(**{"operation": "send_message", "title": "接口说明", "content": "请查收接口说明。", **kw})


def test_policy_c06_ambiguous_contact_is_l4_then_l3_after_clarification():
    before = prepare_action(_action(operation="create_task", target="", due_date=date(2026, 11, 30)))
    assert before.status == "needs_input" and before.risk_level == "L4"
    assert before.judgement.intervention == "missing_info"
    assert before.judgement.follow_ups == ["执行授权：强确认"]
    after = prepare_action(_action(operation="create_task", target="wang-engineering",
                                   due_date=date(2026, 11, 30)), previous=before)
    assert after.risk_level == "L3" and after.status == "awaiting_confirmation"
    assert "recheck_on_change" in after.judgement.rules_applied
    assert after.judgement.intervention_label == "执行授权：普通确认"


def test_policy_internal_vs_external_message():
    internal = prepare_action(_action(target="wang-delivery"))
    external = prepare_action(_action(target="wang-supplier"))
    assert (internal.risk_level, internal.required_checks) == ("L3", [])
    assert (external.risk_level, external.required_checks) == ("L4", ["target", "content", "impact"])


def test_policy_sensitive_content_raises_level_and_urgency_does_not_lower_it():
    salary = prepare_action(_action(target="wang-delivery", content="附上本月薪酬明细，很急。"))
    assert salary.risk_level == "L4"
    assert "reason_no_downgrade" in salary.judgement.rules_applied


def test_judge_action_is_deterministic():
    data = _action(target="client-review")
    assert judge_action(data, missing=[]) == judge_action(data, missing=[])
