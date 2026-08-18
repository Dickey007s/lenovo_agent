from langgraph.checkpoint.memory import InMemorySaver
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from packages.agent_runtime import AgentWorkflow, WorkflowCallbacks
from packages.authorization import AuthorizationService, PermitKeyPair
from packages.contracts import ActionCandidate, TaskArtifactBinding, TaskControlCommand
from packages.tool_gateway import ToolGateway
from services.api.app.application.runs import RunService
from services.api.app.application.conversations import ConversationService
from services.api.app.application.storage import InMemoryWorkspaceStore
from services.api.app.application.task_storage import InMemoryTaskStore
from services.api.app.application.tasks import TaskService
from services.api.app.api.routes import build_run_service, router


OFFICIAL_SOURCE = "fixture:crm/customer-a:official-revenue-v3"


class UnusedParser:
    async def parse(self, message: str) -> ActionCandidate:
        raise AssertionError("Task artifact bridge must not call the LLM parser")


async def _committed_reply(
    task_service: TaskService,
) -> tuple[TaskArtifactBinding, dict[str, object]]:
    created = await task_service.create_demo1("user_1")
    waiting = await task_service.start(
        created.task_id,
        "user_1",
        expected_task_version=created.version,
        idempotency_key="bridge-start-001",
    )
    branch = next(item for item in waiting.branches if item.status == "waiting_evidence")
    committed = await task_service.control(
        created.task_id,
        "user_1",
        TaskControlCommand(
            kind="resolve_evidence",
            branch_id=branch.branch_id,
            selected_source_ref=OFFICIAL_SOURCE,
            expected_task_version=waiting.version,
            idempotency_key="bridge-resolve-001",
        ),
    )
    reply = next(
        item
        for item in committed.artifact_versions
        if item.artifact_version_id
        in (committed.last_commit.artifact_version_ids if committed.last_commit else [])
        and item.kind == "reply_draft"
    )
    task, artifact, report = await task_service.get_committed_artifact(
        committed.task_id, reply.artifact_version_id, "user_1"
    )
    assert task.last_commit is not None
    return (
        TaskArtifactBinding(
            task_id=task.task_id,
            task_version=task.version,
            commit_id=task.last_commit.commit_id,
            commit_state_hash=task.last_commit.state_hash,
            artifact_id=artifact.artifact_id,
            artifact_version_id=artifact.artifact_version_id,
            artifact_version=artifact.version,
            artifact_content_digest=artifact.content_digest,
            deliverable_id=artifact.deliverable_id,
            verification_report_id=report.report_id,
        ),
        artifact.content,
    )


async def test_verified_task_artifact_reaches_demo3_gate_and_simulator() -> None:
    task_service = TaskService(InMemoryTaskStore())
    binding, content = await _committed_reply(task_service)
    keys = PermitKeyPair.generate()
    run_service = RunService(
        parser=UnusedParser(),  # type: ignore[arg-type]
        policy_version="test-v1",
        authorization_service=AuthorizationService(keys),
        tool_gateway=ToolGateway(keys.public_key, "test-v1"),
    )
    run_service.attach_task_artifact_validator(task_service.validate_action_binding)
    workflow = AgentWorkflow(
        WorkflowCallbacks(
            evaluate=run_service.workflow_evaluate,
            execute=run_service.workflow_execute,
            panel=run_service.workflow_panel,
        ),
        InMemorySaver(),
    )
    run_service.attach_workflow(workflow)
    candidate = ActionCandidate(
        action_type="send_email",
        capability="email.send",
        target_scope="external_customer",
        recipients=["customer@example.com"],
        data_classes=["customer_data", "financial", "project_risk"],
        state_change_type="external_effect",
        reversibility="low",
        parameters={"subject": content["subject"], "body": content["body"]},
    )
    kwargs = {
        "message": "准备发送已核对客户回复",
        "user_id": "user_1",
        "thread_id": "chat_bridge",
        "trusted_context": {"device": {"managed": True}},
        "task_artifact_binding": binding,
        "creation_idempotency_key": "bridge-create-001",
    }
    run = await run_service.create_from_candidate(candidate, **kwargs)
    replay = await run_service.create_from_candidate(candidate, **kwargs)

    assert replay.run_id == run.run_id
    assert run.status == "WAITING_APPROVAL"
    assert run.risk.risk_level == "L4"
    assert run.action.task_artifact_binding == binding
    assert run.action.recipients == ["customer@example.com"]
    assert run.control_plan.required_approvals == ["current_user"]
    assert run.evidence["recipient_identity"].status == "satisfied"
    assert run.evidence["dlp_result"].status == "satisfied"

    run = await run_service.submit_approval(
        run.action.action_id, "current_user", "approved", "user_1"
    )
    assert run.status == "READY_TO_AUTHORIZE"
    run = await run_service.authorize_and_execute(run.action.action_id, "user_1")
    assert run.status == "EXECUTED"
    assert run.tool_result is not None
    assert run.tool_result.simulator == "email_simulator"
    assert run.tool_result.output["simulated"] is True
    assert run.tool_result.output["accepted_recipients"] == ["customer@example.com"]
    assert run.tool_result.output["subject"] == content["subject"]

    events = await run_service.audit_history(run.trace_id, "user_1")
    assert [event.event_type for event in events][-2:] == [
        "PERMIT_ISSUED",
        "TOOL_EXECUTED",
    ]
    assert events[0].payload["task_artifact_version_id"] == binding.artifact_version_id


async def test_changed_task_binding_invalidates_prepared_action() -> None:
    task_service = TaskService(InMemoryTaskStore())
    binding, content = await _committed_reply(task_service)
    keys = PermitKeyPair.generate()
    run_service = RunService(
        parser=UnusedParser(),  # type: ignore[arg-type]
        policy_version="test-v1",
        authorization_service=AuthorizationService(keys),
        tool_gateway=ToolGateway(keys.public_key, "test-v1"),
    )

    async def reject_changed_binding(_: TaskArtifactBinding, __: str) -> None:
        raise ValueError("changed")

    run_service.attach_task_artifact_validator(reject_changed_binding)
    run = await run_service.create_from_candidate(
        ActionCandidate(
            action_type="send_email",
            capability="email.send",
            target_scope="external_customer",
            recipients=["customer@example.com"],
            data_classes=["financial"],
            state_change_type="external_effect",
            reversibility="low",
            parameters={"subject": content["subject"], "body": content["body"]},
        ),
        message="准备发送已核对客户回复",
        user_id="user_1",
        thread_id="chat_bridge",
        task_artifact_binding=binding,
    )

    try:
        await run_service.submit_approval(
            run.action.action_id, "current_user", "approved", "user_1"
        )
    except ValueError as exc:
        assert "旧动作已作废" in str(exc)
    else:
        raise AssertionError("changed Task binding must fail closed")
    invalidated = await run_service.get(run.run_id, "user_1")
    assert invalidated.status == "FAILED"
    assert "ARTIFACT_CONTENT_CHANGED" in invalidated.control_plan.reason_codes


async def test_task_artifact_action_route_binds_thread_and_replays_prepare_key() -> None:
    task_service = TaskService(InMemoryTaskStore())
    binding, _ = await _committed_reply(task_service)
    run_service = build_run_service(InMemorySaver())
    run_service.attach_task_artifact_validator(task_service.validate_action_binding)
    workspace_store = InMemoryWorkspaceStore()
    await workspace_store.setup()
    conversation_service = ConversationService(
        run_service.parser,
        run_service,
        workspace_store,
    )
    thread = await conversation_service.create_thread("user_1")
    app = FastAPI()
    app.include_router(router)
    app.state.task_service = task_service
    app.state.run_service = run_service
    app.state.conversation_service = conversation_service
    app.state.task_store_backend = "memory"
    app.state.checkpoint_backend = "memory"

    url = (
        f"/v1/tasks/{binding.task_id}/artifacts/"
        f"{binding.artifact_version_id}/actions/email-send"
    )
    headers = {
        "X-User-Id": "user_1",
        "X-User-Roles": "current_user",
        "Idempotency-Key": "task-action-route-001",
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post(url, json={"thread_id": thread.thread_id}, headers=headers)
        replay = await client.post(url, json={"thread_id": thread.thread_id}, headers=headers)

    assert first.status_code == 201
    assert replay.status_code == 201
    created = first.json()
    assert replay.json()["run_id"] == created["run_id"]
    assert created["thread_id"] == thread.thread_id
    assert created["status"] == "WAITING_APPROVAL"
    assert created["action"]["recipients"] == ["customer@example.com"]
    assert created["action"]["source_refs"] == []
    assert (
        created["action"]["task_artifact_binding"]["artifact_version_id"]
        == binding.artifact_version_id
    )
