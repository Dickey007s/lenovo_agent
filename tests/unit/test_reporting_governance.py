from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[2]
AGENT_HANDOFF = REPOSITORY_ROOT / "AGENTS.md"
PRESENTATION_BRIEF = REPOSITORY_ROOT / "docs" / "PRESENTATION_BRIEF.md"
GOVERNANCE = REPOSITORY_ROOT / "docs" / "DECISION_AND_REPORTING_GOVERNANCE.md"
DECISION_RECORD = (
    REPOSITORY_ROOT / "docs" / "decisions" / "DR-0001-reporting-and-interaction-gates.md"
)
SOURCE_REGISTER = REPOSITORY_ROOT / "docs" / "decisions" / "SOURCE_REGISTER.md"
DEMO1_DECISION = (
    REPOSITORY_ROOT / "docs" / "decisions" / "DR-0002-bounded-durable-office-loop.md"
)
DEMO1_SCENARIO = (
    REPOSITORY_ROOT / "docs" / "scenarios" / "SCENARIO-001-customer-a-durable-report.md"
)
TASK_PROTOCOL = REPOSITORY_ROOT / "docs" / "contracts" / "TASK_RUNTIME_PROTOCOL.md"
UI_FACT_MATRIX = REPOSITORY_ROOT / "docs" / "contracts" / "UI_SERVER_FACT_MATRIX.md"


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


def test_demo1_decision_links_scenario_sources_protocol_and_ui_facts() -> None:
    decision = DEMO1_DECISION.read_text(encoding="utf-8")
    scenario = DEMO1_SCENARIO.read_text(encoding="utf-8")
    sources = SOURCE_REGISTER.read_text(encoding="utf-8")
    protocol = TASK_PROTOCOL.read_text(encoding="utf-8")
    ui_facts = UI_FACT_MATRIX.read_text(encoding="utf-8")

    assert "Status | `Ready`" in decision
    assert "SCENARIO-001" in decision
    assert "Claim Ledger" in decision
    assert "USER-FEEDBACK-20260810-02" in decision
    assert "REPO-BASELINE-84AABC9" in decision
    assert "待验证假设" in decision
    assert "设计来源 Source ID 与运行时 Fixture `source_ref`" in scenario
    assert "USER-FEEDBACK-20260810-02" in sources
    assert "TaskSnapshot" in protocol
    assert "expected_task_version" in protocol
    assert "服务端权威字段" in ui_facts
    assert "默认隐藏" in ui_facts
