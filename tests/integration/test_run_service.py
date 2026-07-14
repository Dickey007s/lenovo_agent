import pytest

from packages.contracts import ActionCandidate
from packages.authorization import AuthorizationService, PermitKeyPair
from packages.authorization import AuthorizationError
from packages.agent_runtime import AgentWorkflow, WorkflowCallbacks
from packages.tool_gateway import ToolGateway
from langgraph.checkpoint.memory import InMemorySaver
from services.api.app.application.runs import RunService


class FakeParser:
    async def parse(self, message: str) -> ActionCandidate:
        return ActionCandidate(
            action_type="send_email",
            capability="email.send",
            target_scope="external_customer",
            recipients=["client@example.com"],
            resources=["quote.pdf"],
            data_classes=["pricing"],
            state_change_type="external_effect",
            reversibility="low",
        )


async def test_evidence_and_approvals_recompute_the_plan() -> None:
    keys = PermitKeyPair.generate()
    service = RunService(
        parser=FakeParser(),  # type: ignore[arg-type]
        policy_version="test-v1",
        authorization_service=AuthorizationService(keys),
        tool_gateway=ToolGateway(keys.public_key, "test-v1"),
    )
    run = await service.create("把报价发给客户", "user_1")

    assert run.status == "WAITING_EVIDENCE"
    assert set(run.control_plan.missing_requirements) == {
        "pricing_source",
    }

    run = await service.submit_evidence(
        run.action.action_id,
        {
            "pricing_source": "crm:quote/991:v3",
        },
        "user_1",
    )
    assert run.status == "WAITING_APPROVAL"

    run = await service.submit_approval(
        run.action.action_id, "current_user", "approved", "user_1"
    )
    assert run.status == "WAITING_APPROVAL"

    run = await service.submit_approval(
        run.action.action_id, "sales_manager", "approved", "user_1"
    )
    assert run.status == "READY_TO_AUTHORIZE"
    assert run.control_plan.capabilities["email.send"].verdict == "allow"

    run = await service.authorize_and_execute(run.action.action_id, "user_1")
    assert run.status == "EXECUTED"
    assert run.permit is not None
    assert run.tool_result is not None
    assert run.tool_result.output["simulated"] is True


async def test_langgraph_interrupts_and_resumes_each_gate() -> None:
    keys = PermitKeyPair.generate()
    service = RunService(
        parser=FakeParser(),  # type: ignore[arg-type]
        policy_version="test-v1",
        authorization_service=AuthorizationService(keys),
        tool_gateway=ToolGateway(keys.public_key, "test-v1"),
    )
    workflow = AgentWorkflow(
        WorkflowCallbacks(
            evaluate=service.workflow_evaluate,
            execute=service.workflow_execute,
            panel=service.workflow_panel,
        ),
        InMemorySaver(),
    )
    service.attach_workflow(workflow)

    run = await service.create("把报价发给客户", "user_1")
    graph_state = await service.workflow_state(run.run_id, "user_1")
    assert run.status == "WAITING_EVIDENCE"
    assert graph_state["next"] == ["human_gate"]
    assert graph_state["interrupts"][0]["kind"] == "evidence_submitted"

    run = await service.submit_evidence(
        run.action.action_id,
        {
            "pricing_source": "crm:quote/991:v3",
        },
        "user_1",
    )
    graph_state = await service.workflow_state(run.run_id, "user_1")
    assert run.status == "WAITING_APPROVAL"
    assert graph_state["interrupts"][0]["kind"] == "approval_submitted"

    for role in ("current_user", "sales_manager"):
        run = await service.submit_approval(
            run.action.action_id, role, "approved", f"approver_{role}"
        )
    graph_state = await service.workflow_state(run.run_id, "user_1")
    assert run.status == "READY_TO_AUTHORIZE"
    assert graph_state["interrupts"][0]["kind"] == "authorization_requested"

    run = await service.authorize_and_execute(run.action.action_id, "user_1")
    graph_state = await service.workflow_state(run.run_id, "user_1")
    assert run.status == "EXECUTED"
    assert graph_state["next"] == []
    assert graph_state["interrupts"] == []
    audit = await service.audit_history(run.trace_id, "user_1")
    event_types = [event.event_type for event in audit]
    assert event_types[:2] == ["RUN_CREATED", "ACTION_PARSED"]
    assert "PERMIT_ISSUED" in event_types
    assert event_types[-1] == "TOOL_EXECUTED"
    assert "token" not in "".join(event.model_dump_json() for event in audit).lower()


async def test_artifact_edit_invalidates_old_action_server_side() -> None:
    keys = PermitKeyPair.generate()
    service = RunService(
        parser=FakeParser(),  # type: ignore[arg-type]
        policy_version="test-v1",
        authorization_service=AuthorizationService(keys),
        tool_gateway=ToolGateway(keys.public_key, "test-v1"),
    )
    run = await service.create("把报价发给客户", "user_1")
    run = await service.submit_evidence(
        run.action.action_id, {"pricing_source": "crm:quote/991:v3"}, "user_1"
    )
    for role in ("current_user", "sales_manager"):
        run = await service.submit_approval(
            run.action.action_id, role, "approved", f"approver_{role}"
        )
    assert run.status == "READY_TO_AUTHORIZE"

    invalidated = await service.invalidate_action(run.action.action_id, "user_1")
    assert invalidated.status == "FAILED"
    assert "ARTIFACT_CONTENT_CHANGED" in invalidated.control_plan.reason_codes
    with pytest.raises(AuthorizationError, match="已作废"):
        await service.authorize_and_execute(run.action.action_id, "user_1")
