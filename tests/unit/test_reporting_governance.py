from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[2]
AGENT_HANDOFF = REPOSITORY_ROOT / "AGENTS.md"
PRESENTATION_BRIEF = REPOSITORY_ROOT / "docs" / "PRESENTATION_BRIEF.md"
GOVERNANCE = REPOSITORY_ROOT / "docs" / "DECISION_AND_REPORTING_GOVERNANCE.md"
DECISION_RECORD = (
    REPOSITORY_ROOT / "docs" / "decisions" / "DR-0001-reporting-and-interaction-gates.md"
)
SOURCE_REGISTER = REPOSITORY_ROOT / "docs" / "decisions" / "SOURCE_REGISTER.md"


def test_reporting_governance_is_required_by_agent_and_presentation_guidance() -> None:
    for path in (AGENT_HANDOFF, PRESENTATION_BRIEF):
        content = path.read_text(encoding="utf-8")
        assert "DECISION_AND_REPORTING_GOVERNANCE.md" in content
        assert "场景与来源" in content
        assert "前台" in content
        assert "后端事实" in content


def test_reporting_governance_defines_hard_gates_and_audit_tables() -> None:
    content = GOVERNANCE.read_text(encoding="utf-8")

    for required in (
        "场景与来源",
        "前台交互影响",
        "后端事实映射",
        "验证与边界",
        "UI—服务端事实映射",
        "来源台账",
        "Draft",
        "Ready",
        "Verified",
        "Rejected",
    ):
        assert required in content


def test_first_governance_decision_and_user_source_are_traceable() -> None:
    decision = DECISION_RECORD.read_text(encoding="utf-8")
    sources = SOURCE_REGISTER.read_text(encoding="utf-8")

    assert "DR-0001" in decision
    assert "USER-FEEDBACK-20260810-01" in decision
    assert "Status | `Verified`" in decision
    assert "USER-FEEDBACK-20260810-01" in sources
    assert "前台交互影响" in sources
    assert "UI—后端事实映射" in sources
