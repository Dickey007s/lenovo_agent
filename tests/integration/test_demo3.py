from packages.authorization import AuthorizationService, PermitKeyPair
from packages.tool_gateway import ToolGateway
from services.api.app.application.demo3 import get_scenario, list_scenarios
from services.api.app.application.runs import RunService
from tests.integration.test_run_service import FakeParser


def make_service() -> RunService:
    keys = PermitKeyPair.generate()
    return RunService(
        parser=FakeParser(),  # type: ignore[arg-type]
        policy_version="test-v1",
        authorization_service=AuthorizationService(keys),
        tool_gateway=ToolGateway(keys.public_key, "test-v1"),
    )


async def test_demo3_four_scenarios_have_deterministic_initial_statuses() -> None:
    service = make_service()
    expected = {
        "self": "READY_TO_AUTHORIZE",
        "internal": "DENIED",
        "external": "WAITING_APPROVAL",
        "pricing": "WAITING_EVIDENCE",
    }

    assert {scenario.scenario_id for scenario in list_scenarios()} == set(expected)
    for scenario_id, status in expected.items():
        scenario = get_scenario(scenario_id)
        run = await service.create_from_candidate(
            scenario.candidate,
            scenario.title,
            "demo_user",
            scenario.trusted_context,
        )
        assert run.status == status


async def test_pricing_scenario_blocks_parameter_tamper_before_simulator() -> None:
    service = make_service()
    scenario = get_scenario("pricing")
    run = await service.create_from_candidate(
        scenario.candidate, scenario.title, "demo_user", scenario.trusted_context
    )
    evidence = {"pricing_source": "crm:quote/991:v3"}
    run = await service.submit_evidence(run.action.action_id, evidence, "demo_user")
    for role in list(run.control_plan.required_approvals):
        run = await service.submit_approval(
            run.action.action_id, role, "approved", "demo_user"
        )

    result = await service.demonstrate_parameter_tamper(
        run.action.action_id, "demo_user"
    )
    assert result == {
        "blocked": True,
        "code": "PARAMETER_HASH_MISMATCH",
        "changed_field": "recipients",
        "simulator_executed": False,
    }
    audit = await service.audit_history(run.trace_id, "demo_user")
    assert audit[-1].event_type == "TAMPER_BLOCKED"
