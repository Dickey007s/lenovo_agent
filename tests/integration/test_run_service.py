import pytest
from pydantic import ValidationError

from packages.contracts import ActionCandidate
from packages.contracts import ImpactItem
from packages.contracts import TaskArtifactBinding
from packages.authorization import AuthorizationService, PermitKeyPair
from packages.authorization import AuthorizationError
from packages.tool_gateway import GatewayError
from packages.agent_runtime import AgentWorkflow, WorkflowCallbacks
from packages.tool_gateway import ToolGateway
from langgraph.checkpoint.memory import InMemorySaver
from services.api.app.application.runs import (
    ActionNotFoundError,
    RunCreateConflictError,
    RunService,
)


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
            run.action.action_id, role, "approved", "user_1"
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
            run.action.action_id, role, "approved", "user_1"
        )
    assert run.status == "READY_TO_AUTHORIZE"

    invalidated = await service.invalidate_action(run.action.action_id, "user_1")
    assert invalidated.status == "FAILED"
    assert "ARTIFACT_CONTENT_CHANGED" in invalidated.control_plan.reason_codes
    with pytest.raises(AuthorizationError, match="已作废"):
        await service.authorize_and_execute(run.action.action_id, "user_1")


async def _ready_run(service: RunService):
    run = await service.create("把报价发给客户", "user_1")
    run = await service.submit_evidence(
        run.action.action_id, {"pricing_source": "crm:quote/991:v3"}, "user_1"
    )
    for role in ("current_user", "sales_manager"):
        run = await service.submit_approval(
            run.action.action_id, role, "approved", "user_1"
        )
    assert run.status == "READY_TO_AUTHORIZE"
    return run


def test_impact_item_identity_cannot_be_relabelled() -> None:
    with pytest.raises(ValidationError, match="impact item id does not match"):
        ImpactItem(
            item_id="target-change",
            change_kind="unchanged",
            label="malformed impact item",
        )


async def test_action_preview_has_stable_four_item_contract_and_terminal_replay() -> None:
    keys = PermitKeyPair.generate()
    service = RunService(
        parser=FakeParser(),
        policy_version="test-v1",
        authorization_service=AuthorizationService(keys),
        tool_gateway=ToolGateway(keys.public_key, "test-v1"),
    )
    run = await _ready_run(service)
    assert run.impact_preview is not None
    assert {(item.item_id, item.change_kind) for item in run.impact_preview.items} == {
        ("target-change", "will_change"),
        ("binding-recheck", "will_recheck"),
        ("task-preserved", "unchanged"),
        ("real-connector-not-called", "no_external_action"),
    }

    executed = await service.authorize_and_execute(run.action.action_id, "user_1")
    replay = await service.authorize_and_execute(run.action.action_id, "user_1")
    assert executed.status == "EXECUTED"
    assert replay == executed
    audit = await service.audit_history(run.trace_id, "user_1")
    assert [event.event_type for event in audit].count("TOOL_EXECUTED") == 1
    assert executed.execution_receipt is not None
    assert executed.execution_receipt.status == "succeeded"
    rendered_items = " ".join(
        f"{item.label} {item.before or ''} {item.after or ''}"
        for item in executed.execution_receipt.items
    )
    assert executed.execution_receipt.execution_id is not None
    assert executed.execution_receipt.execution_id not in rendered_items
    assert "email.send" not in rendered_items
    assert "Permit" not in rendered_items


async def test_terminal_runs_reject_evidence_and_approval_mutations() -> None:
    keys = PermitKeyPair.generate()
    service = RunService(
        parser=FakeParser(),
        policy_version="test-v1",
        authorization_service=AuthorizationService(keys),
        tool_gateway=ToolGateway(keys.public_key, "test-v1"),
    )
    run = await _ready_run(service)
    run = await service.authorize_and_execute(run.action.action_id, "user_1")
    with pytest.raises(ValueError, match="终态"):
        await service.submit_evidence(
            run.action.action_id, {"pricing_source": "crm:quote/991:v3"}, "user_1"
        )
    with pytest.raises(ValueError, match="终态"):
        await service.submit_approval(
            run.action.action_id, "current_user", "approved", "user_1"
        )


async def test_cross_user_approval_cannot_mutate_another_owner_run() -> None:
    keys = PermitKeyPair.generate()
    service = RunService(
        parser=FakeParser(),
        policy_version="test-v1",
        authorization_service=AuthorizationService(keys),
        tool_gateway=ToolGateway(keys.public_key, "test-v1"),
    )
    run = await service.create("把报价发给客户", "owner_1")
    with pytest.raises(ActionNotFoundError):
        await service.submit_approval(
            run.action.action_id, "current_user", "approved", "other_user"
        )
    unchanged = await service.get(run.run_id, "owner_1")
    assert unchanged.approvals == []


class FailingGateway:
    async def execute(self, **_: object):
        raise GatewayError("SIMULATOR_DOWN", "simulator unavailable")


async def test_gateway_failure_persists_unknown_failed_receipt() -> None:
    keys = PermitKeyPair.generate()
    service = RunService(
        parser=FakeParser(),
        policy_version="test-v1",
        authorization_service=AuthorizationService(keys),
        tool_gateway=FailingGateway(),  # type: ignore[arg-type]
    )
    run = await _ready_run(service)
    with pytest.raises(GatewayError, match="simulator unavailable"):
        await service.authorize_and_execute(run.action.action_id, "user_1")
    failed = await service.get(run.run_id, "user_1")
    assert failed.status == "FAILED"
    assert failed.execution_receipt is not None
    assert failed.execution_receipt.status == "failed"
    assert failed.execution_receipt.external_side_effect == "none"
    assert failed.execution_receipt.error_code == "SIMULATOR_DOWN"


class FailingSimulatorGateway:
    async def execute(self, **_: object):
        raise RuntimeError("simulator timed out")


async def test_simulator_failure_persists_unknown_receipt() -> None:
    keys = PermitKeyPair.generate()
    service = RunService(
        parser=FakeParser(),
        policy_version="test-v1",
        authorization_service=AuthorizationService(keys),
        tool_gateway=FailingSimulatorGateway(),  # type: ignore[arg-type]
    )
    run = await _ready_run(service)
    with pytest.raises(GatewayError, match="结果未知"):
        await service.authorize_and_execute(run.action.action_id, "user_1")
    failed = await service.get(run.run_id, "user_1")
    assert failed.status == "FAILED"
    assert failed.execution_receipt is not None
    assert failed.execution_receipt.status == "unknown"
    assert failed.execution_receipt.external_side_effect == "unknown"
    assert failed.execution_receipt.error_code == "SIMULATOR_EXECUTION_UNKNOWN"


async def test_bound_action_without_validator_fails_closed() -> None:
    keys = PermitKeyPair.generate()
    service = RunService(
        parser=FakeParser(),
        policy_version="test-v1",
        authorization_service=AuthorizationService(keys),
        tool_gateway=ToolGateway(keys.public_key, "test-v1"),
    )
    binding = TaskArtifactBinding(
        task_id="task-1",
        task_version=1,
        commit_id="commit-1",
        commit_state_hash="sha256:" + "a" * 64,
        artifact_id="artifact-1",
        artifact_version_id="artifact-version-1",
        artifact_version=1,
        artifact_content_digest="sha256:" + "b" * 64,
        deliverable_id="reply-draft",
        verification_report_id="report-1",
    )
    with pytest.raises(RunCreateConflictError, match="校验器未配置"):
        await service.create_from_candidate(
            ActionCandidate(
                action_type="send_email",
                capability="email.send",
                target_scope="external_customer",
                recipients=["client@example.com"],
                data_classes=["customer_data"],
                state_change_type="external_effect",
                reversibility="low",
            ),
            message="准备发送",
            user_id="user_1",
            task_artifact_binding=binding,
        )
