import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.responses import StreamingResponse

from packages.agent_runtime import AgentWorkflow, WorkflowCallbacks
from packages.audit import InMemoryAuditLog
from packages.authorization import AuthorizationError, AuthorizationService, PermitKeyPair
from packages.tool_gateway import GatewayError, ToolGateway
from packages.contracts import TaskContractDraft, TaskControlCommand, TaskSnapshot
from services.api.app.application.llm import (
    AutoDLActionParser,
    ModelConfigurationError,
    ModelOutputError,
)
from services.api.app.application.demo3 import Demo3Scenario, get_scenario, list_scenarios
from services.api.app.application.evidence_catalog import (
    EvidenceRequirementDefinition,
    list_evidence_requirements,
)
from services.api.app.application.runs import (
    ActionNotFoundError,
    RunNotFoundError,
    RunService,
    RunSnapshot,
)
from services.api.app.application.storage import InMemoryRunStore, RunStore
from services.api.app.application.tasks import (
    TaskCreateConflictError,
    TaskMutationConflictError,
    TaskNotFoundError,
    TaskService,
    TaskTransitionError,
)
from services.api.app.application.conversation_models import ConversationThread, WorkspaceArtifact
from services.api.app.application.conversations import (
    ConversationNotFoundError,
    ConversationService,
    WorkspaceChangedError,
)
from services.api.app.application.quote_calculator import QuoteCalculationError
from services.api.app.config import get_settings


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateRunRequest(StrictRequest):
    message: str = Field(min_length=1, max_length=10_000)


class SendConversationMessageRequest(StrictRequest):
    message: str = Field(min_length=1, max_length=10_000)
    active_view: Literal["mail", "document", "quote", "tasks", "calendar", "expense", "crm", "audit"] | None = None
    workspace_context: dict | None = None
    workspace_artifact_id: str | None = None
    workspace_revision: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def require_workspace_revision(self):
        if self.workspace_context is not None and (
            self.workspace_artifact_id is None or self.workspace_revision is None
        ):
            raise ValueError(
                "workspace_context requires workspace_artifact_id and workspace_revision"
            )
        return self


class UpdateArtifactRequest(StrictRequest):
    content: dict
    title: str | None = None


class SaveWorkspaceArtifactRequest(UpdateArtifactRequest):
    expected_artifact_id: str
    expected_revision: int = Field(ge=1)


class EvidenceInput(StrictRequest):
    values: dict[str, str]


class ApprovalInput(StrictRequest):
    approver_role: str
    decision: Literal["approved", "rejected"]


class StartTaskRequest(StrictRequest):
    expected_task_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=160)


class CurrentUser(StrictRequest):
    user_id: str
    roles: set[str]


def build_run_service(
    checkpointer: BaseCheckpointSaver,
    run_store: RunStore | None = None,
    audit_log: InMemoryAuditLog | None = None,
) -> RunService:
    settings = get_settings()
    parser = AutoDLActionParser(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout=settings.llm_timeout_seconds,
        thinking_mode=settings.llm_thinking_mode,
    )
    if settings.permit_private_key_path and settings.permit_public_key_path:
        key_pair = PermitKeyPair.from_pem_files(
            settings.permit_private_key_path, settings.permit_public_key_path
        )
    else:
        # Safe development default: restart invalidates all outstanding permits.
        key_pair = PermitKeyPair.generate()
    authorization_service = AuthorizationService(key_pair, settings.permit_ttl_seconds)
    tool_gateway = ToolGateway(key_pair.public_key, settings.policy_version)
    service = RunService(
        parser=parser,
        policy_version=settings.policy_version,
        authorization_service=authorization_service,
        tool_gateway=tool_gateway,
        run_store=run_store or InMemoryRunStore(),
        audit_log=audit_log or InMemoryAuditLog(),
    )
    workflow = AgentWorkflow(
        callbacks=WorkflowCallbacks(
            evaluate=service.workflow_evaluate,
            execute=service.workflow_execute,
            panel=service.workflow_panel,
        ),
        checkpointer=checkpointer,
    )
    service.attach_workflow(workflow)
    return service


def get_run_service(request: Request) -> RunService:
    return request.app.state.run_service


def get_conversation_service(request: Request) -> ConversationService:
    return request.app.state.conversation_service


def get_task_service(request: Request) -> TaskService:
    return request.app.state.task_service


def current_user(
    x_user_id: Annotated[str, Header()] = "demo_user",
    x_user_roles: Annotated[str, Header()] = "current_user",
) -> CurrentUser:
    # P0 placeholder. Production must replace this with verified SSO/JWT identity.
    return CurrentUser(
        user_id=x_user_id,
        roles={role.strip() for role in x_user_roles.split(",") if role.strip()},
    )


router = APIRouter(prefix="/v1")


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "model": settings.llm_model,
        "checkpoint": request.app.state.checkpoint_backend,
        "task_store": request.app.state.task_store_backend,
    }


@router.post(
    "/demo1/tasks",
    response_model=TaskSnapshot,
    status_code=status.HTTP_201_CREATED,
)
async def create_demo1_task(
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", min_length=8, max_length=160)
    ] = None,
) -> TaskSnapshot:
    try:
        return await service.create_demo1(
            user.user_id, idempotency_key=idempotency_key
        )
    except TaskCreateConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/tasks", response_model=TaskSnapshot, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskContractDraft,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", min_length=8, max_length=160)
    ] = None,
) -> TaskSnapshot:
    try:
        return await service.create(
            body, user.user_id, idempotency_key=idempotency_key
        )
    except TaskCreateConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/tasks", response_model=list[TaskSnapshot])
async def list_tasks(
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> list[TaskSnapshot]:
    return await service.list(user.user_id)


@router.get("/tasks/{task_id}", response_model=TaskSnapshot)
async def get_task(
    task_id: str,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskSnapshot:
    try:
        return await service.get(task_id, user.user_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="任务不存在") from exc


@router.post("/tasks/{task_id}/start", response_model=TaskSnapshot)
async def start_task(
    task_id: str,
    body: StartTaskRequest,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskSnapshot:
    try:
        return await service.start(
            task_id,
            user.user_id,
            expected_task_version=body.expected_task_version,
            idempotency_key=body.idempotency_key,
        )
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="任务不存在") from exc
    except (TaskMutationConflictError, TaskTransitionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/controls", response_model=TaskSnapshot)
async def control_task(
    task_id: str,
    body: TaskControlCommand,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskSnapshot:
    try:
        return await service.control(task_id, user.user_id, body)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="任务不存在") from exc
    except (TaskMutationConflictError, TaskTransitionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/tasks/{task_id}/events")
async def stream_task_events(
    task_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
    after: Annotated[int, Query(ge=0)] = 0,
) -> StreamingResponse:
    try:
        await service.get(task_id, user.user_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="任务不存在") from exc

    async def event_source():
        async for event in service.event_stream(task_id, user.user_id, after):
            if await request.is_disconnected():
                break
            if event is None:
                yield ": heartbeat\n\n"
            else:
                yield (
                    f"id: {event.sequence}\n"
                    f"event: {event.event_type}\n"
                    f"data: {event.model_dump_json()}\n\n"
                )

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/threads", response_model=ConversationThread, status_code=status.HTTP_201_CREATED)
async def create_thread(
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationThread:
    return await service.create_thread(user.user_id)


@router.get("/threads/{thread_id}", response_model=ConversationThread)
async def get_thread(
    thread_id: str,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationThread:
    try:
        return await service.get_thread(thread_id, user.user_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="对话不存在") from exc


@router.post("/threads/{thread_id}/messages/stream")
async def stream_conversation_message(
    thread_id: str,
    body: SendConversationMessageRequest,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> StreamingResponse:
    try:
        await service.get_thread(thread_id, user.user_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="对话不存在") from exc

    async def event_source():
        try:
            async for event in service.stream_message(
                thread_id,
                body.message,
                user.user_id,
                active_view=body.active_view,
                workspace_context=body.workspace_context,
                expected_artifact_id=body.workspace_artifact_id,
                expected_revision=body.workspace_revision,
            ):
                event_type = event.get("type", "message")
                yield f"event: {event_type}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
        except (ModelConfigurationError, ModelOutputError) as exc:
            payload = json.dumps(
                {"type": "error", "detail": str(exc)}, ensure_ascii=False
            )
            yield f"event: error\ndata: {payload}\n\n"
        except Exception:
            payload = json.dumps(
                {"type": "error", "detail": "办公 Agent 暂时无法完成处理，请稍后重试"},
                ensure_ascii=False,
            )
            yield f"event: error\ndata: {payload}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/threads/{thread_id}/runs/{run_id}/continue/stream")
async def continue_conversation_after_action(
    thread_id: str,
    run_id: str,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> StreamingResponse:
    async def event_source():
        try:
            async for event in service.stream_action_result(
                thread_id, run_id, user.user_id
            ):
                event_type = event.get("type", "message")
                yield f"event: {event_type}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
        except (ModelConfigurationError, ModelOutputError, ValueError) as exc:
            payload = json.dumps({"type": "error", "detail": str(exc)}, ensure_ascii=False)
            yield f"event: error\ndata: {payload}\n\n"
        except Exception:
            payload = json.dumps(
                {
                    "type": "error",
                    "detail": "Agent 暂时无法读取执行结果，请重试",
                },
                ensure_ascii=False,
            )
            yield f"event: error\ndata: {payload}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/workspace", response_model=list[WorkspaceArtifact])
async def get_workspace(
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> list[WorkspaceArtifact]:
    return await service.get_workspace(user.user_id)


@router.post("/workspace/mail/new", response_model=WorkspaceArtifact)
async def start_new_mail(
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> WorkspaceArtifact:
    try:
        return await service.start_new_mail(user.user_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="邮件工作区不存在") from exc


@router.put("/workspace/{kind}", response_model=WorkspaceArtifact)
async def save_workspace_artifact(
    kind: Literal["mail", "document", "quote", "tasks", "calendar", "expense", "crm"],
    body: SaveWorkspaceArtifactRequest,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> WorkspaceArtifact:
    try:
        return await service.save_workspace_artifact(
            kind,
            body.content,
            user.user_id,
            title=body.title,
            expected_artifact_id=body.expected_artifact_id,
            expected_revision=body.expected_revision,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="工作区不存在") from exc
    except QuoteCalculationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except WorkspaceChangedError as exc:
        raise HTTPException(
            status_code=409,
            detail="工作区已在其他窗口更新；当前修改未覆盖新版本，请重新载入后再试",
        ) from exc


@router.put(
    "/threads/{thread_id}/artifacts/{artifact_id}", response_model=WorkspaceArtifact
)
async def update_artifact(
    thread_id: str,
    artifact_id: str,
    body: UpdateArtifactRequest,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> WorkspaceArtifact:
    try:
        return await service.update_artifact(
            thread_id, artifact_id, body.content, user.user_id
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="对话或生成物不存在") from exc
    except QuoteCalculationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/demo3/scenarios", response_model=list[Demo3Scenario])
async def demo3_scenarios() -> list[Demo3Scenario]:
    return list_scenarios()


@router.get(
    "/evidence/requirements", response_model=list[EvidenceRequirementDefinition]
)
async def evidence_requirements() -> list[EvidenceRequirementDefinition]:
    return list_evidence_requirements()


@router.post(
    "/demo3/scenarios/{scenario_id}/runs",
    response_model=RunSnapshot,
    status_code=status.HTTP_201_CREATED,
)
async def create_demo3_run(
    scenario_id: str,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[RunService, Depends(get_run_service)],
) -> RunSnapshot:
    try:
        scenario = get_scenario(scenario_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Demo 3 场景不存在") from exc
    context = scenario.trusted_context | {"user": {"id": user.user_id}}
    return await service.create_from_candidate(
        scenario.candidate,
        message=scenario.title,
        user_id=user.user_id,
        trusted_context=context,
    )


@router.post("/runs", response_model=RunSnapshot, status_code=status.HTTP_201_CREATED)
async def create_run(
    request: CreateRunRequest,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[RunService, Depends(get_run_service)],
) -> RunSnapshot:
    try:
        return await service.create(request.message, user.user_id)
    except ModelConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ModelOutputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/runs/{run_id}", response_model=RunSnapshot)
async def get_run(
    run_id: str,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[RunService, Depends(get_run_service)],
) -> RunSnapshot:
    try:
        return await service.get(run_id, user.user_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="运行不存在") from exc


@router.get("/runs/{run_id}/workflow")
async def get_workflow_state(
    run_id: str,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[RunService, Depends(get_run_service)],
) -> dict:
    try:
        return await service.workflow_state(run_id, user.user_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="运行不存在") from exc


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[RunService, Depends(get_run_service)],
    after: int = 0,
) -> StreamingResponse:
    async def event_source():
        try:
            async for event in service.event_stream(run_id, user.user_id, after):
                if await request.is_disconnected():
                    break
                if event is None:
                    yield ": heartbeat\n\n"
                else:
                    yield (
                        f"id: {event.sequence}\n"
                        f"event: {event.event_type}\n"
                        f"data: {event.model_dump_json()}\n\n"
                    )
        except RunNotFoundError:
            yield "event: error\ndata: {\"detail\":\"运行不存在\"}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/audit/{trace_id}")
async def get_audit_timeline(
    trace_id: str,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[RunService, Depends(get_run_service)],
) -> list:
    try:
        return await service.audit_history(trace_id, user.user_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="审计轨迹不存在") from exc


@router.post("/actions/{action_id}/evidence", response_model=RunSnapshot)
async def submit_evidence(
    action_id: str,
    request: EvidenceInput,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[RunService, Depends(get_run_service)],
) -> RunSnapshot:
    try:
        return await service.submit_evidence(action_id, request.values, user.user_id)
    except ActionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="动作不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/actions/{action_id}/approvals", response_model=RunSnapshot)
async def submit_approval(
    action_id: str,
    request: ApprovalInput,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[RunService, Depends(get_run_service)],
) -> RunSnapshot:
    if request.approver_role not in user.roles:
        raise HTTPException(status_code=403, detail="当前用户不具备该审批角色")
    try:
        return await service.submit_approval(
            action_id, request.approver_role, request.decision, user.user_id
        )
    except ActionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="动作不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/actions/{action_id}/authorize", response_model=RunSnapshot)
async def authorize_action(
    action_id: str,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[RunService, Depends(get_run_service)],
) -> RunSnapshot:
    try:
        return await service.authorize_and_execute(action_id, user.user_id)
    except ActionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="动作不存在") from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except GatewayError as exc:
        raise HTTPException(
            status_code=409, detail={"code": exc.code, "message": str(exc)}
        ) from exc


@router.post("/demo3/actions/{action_id}/tamper-check")
async def demo3_tamper_check(
    action_id: str,
    user: Annotated[CurrentUser, Depends(current_user)],
    service: Annotated[RunService, Depends(get_run_service)],
) -> dict:
    try:
        return await service.demonstrate_parameter_tamper(action_id, user.user_id)
    except ActionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="动作不存在") from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
