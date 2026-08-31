"""HTTP projection for the unified Agent Harness runtime."""

from __future__ import annotations

import json
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from starlette.responses import Response, StreamingResponse

from packages.contracts.harness_models import AgentControlLoopControlRequest

from services.api.app.application.harness_runtime import (
    HarnessConflictError,
    HarnessError,
    HarnessNotFoundError,
    HarnessRunStart,
    HarnessContinuationRequest,
    HarnessReadonlyWorkersRequest,
    HarnessRuntime,
)
from services.api.app.application.benchmark_scenario_catalog import BenchmarkScenarioError
from services.api.app.config import get_settings

router = APIRouter(prefix="/v1/harness", tags=["harness"])
health_router = APIRouter(prefix="/v1", tags=["health"])


def get_harness_runtime(request: Request) -> HarnessRuntime:
    runtime = getattr(request.app.state, "harness_runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Harness runtime 尚未配置")
    return runtime


def harness_owner(x_user_id: Annotated[str, Header()] = "demo_user") -> str:
    return x_user_id


@health_router.get("/health")
async def health(request: Request) -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "model": settings.llm_model,
        "checkpoint": getattr(request.app.state, "checkpoint_backend", "memory"),
        "task_store": getattr(request.app.state, "task_store_backend", "memory"),
    }


@router.get("/workspace")
async def get_harness_workspace(
    runtime: Annotated[HarnessRuntime, Depends(get_harness_runtime)],
):
    try:
        return runtime.get_workspace()
    except (BenchmarkScenarioError, HarnessError) as exc:
        raise HTTPException(status_code=503, detail="办公资料库完整性校验失败") from exc


@router.get("/workspace/files/{file_ref}")
async def get_harness_file_preview(
    file_ref: str,
    runtime: Annotated[HarnessRuntime, Depends(get_harness_runtime)],
):
    try:
        return runtime.get_file_preview(file_ref)
    except HarnessNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (BenchmarkScenarioError, HarnessError) as exc:
        raise HTTPException(status_code=503, detail="公开文件完整性校验失败") from exc


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
async def start_harness_run(
    body: HarnessRunStart,
    owner_id: Annotated[str, Depends(harness_owner)],
    runtime: Annotated[HarnessRuntime, Depends(get_harness_runtime)],
):
    try:
        result = await runtime.start(owner_id, body)
        return runtime.public_start_result(result)
    except HarnessNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HarnessConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (BenchmarkScenarioError, HarnessError) as exc:
        raise HTTPException(status_code=503, detail="办公资料库完整性校验失败") from exc


@router.post("/runs/{run_id}/continue", status_code=status.HTTP_202_ACCEPTED)
async def continue_harness_task(
    run_id: str,
    body: HarnessContinuationRequest,
    owner_id: Annotated[str, Depends(harness_owner)],
    runtime: Annotated[HarnessRuntime, Depends(get_harness_runtime)],
):
    """Create a new Run for exactly one unfinished Branch of a terminal task."""
    try:
        result = await runtime.continue_unfinished_task(
            owner_id,
            run_id,
            body.branch_id,
            idempotency_key=body.idempotency_key,
            expected_version=body.expected_version,
            expected_task_version=body.expected_task_version,
            instruction=body.instruction,
            loop=body.loop,
        )
        return runtime.public_start_result(result)
    except HarnessNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HarnessConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/tasks/{task_id}")
async def get_harness_task(
    task_id: str,
    owner_id: Annotated[str, Depends(harness_owner)],
    runtime: Annotated[HarnessRuntime, Depends(get_harness_runtime)],
):
    """Return only the caller's server-owned task pointer."""
    try:
        # owner_id is an authorization input, not public task content.
        return (await runtime.get_task(owner_id, task_id)).model_dump(
            mode="json", exclude={"owner_id"}
        )
    except HarnessNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HarnessError as exc:
        raise HTTPException(status_code=503, detail="任务台账完整性暂时无法确认") from exc


@router.get("/runs")
async def list_harness_runs(
    owner_id: Annotated[str, Depends(harness_owner)],
    runtime: Annotated[HarnessRuntime, Depends(get_harness_runtime)],
    limit: int = Query(default=10, ge=1, le=20),
):
    snapshots = await runtime.list(owner_id)
    return {"runs": [runtime.public_snapshot(item) for item in snapshots[:limit]]}


@router.post("/runs/{run_id}/workers", status_code=status.HTTP_202_ACCEPTED)
async def execute_harness_workers(
    run_id: str,
    body: HarnessReadonlyWorkersRequest,
    owner_id: Annotated[str, Depends(harness_owner)],
    runtime: Annotated[HarnessRuntime, Depends(get_harness_runtime)],
):
    """Execute explicitly confirmed, admitted read-only Branch workers."""
    try:
        snapshot = await runtime.execute_admitted_workers_from_branches(
            owner_id,
            run_id,
            branch_ids=body.branch_ids,
            expected_version=body.expected_version,
            idempotency_key=body.idempotency_key,
            user_confirmed=body.confirmed,
        )
        return runtime.public_snapshot(snapshot)
    except HarnessNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HarnessConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/runs/{run_id}")
async def get_harness_run(
    run_id: str,
    owner_id: Annotated[str, Depends(harness_owner)],
    runtime: Annotated[HarnessRuntime, Depends(get_harness_runtime)],
):
    try:
        snapshot = await runtime.get(owner_id, run_id)
        return runtime.public_snapshot(snapshot)
    except HarnessNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/artifacts/{artifact_id}")
async def get_harness_run_artifact(
    run_id: str,
    artifact_id: str,
    owner_id: Annotated[str, Depends(harness_owner)],
    runtime: Annotated[HarnessRuntime, Depends(get_harness_runtime)],
):
    try:
        artifact, content = await runtime.get_workspace_artifact(
            owner_id, run_id, artifact_id
        )
    except HarnessNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HarnessError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type=artifact.media_type,
        headers={
            "Content-Disposition": (
                "attachment; filename*=UTF-8''" + quote(artifact.file_name)
            ),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/runs/{run_id}/controls", status_code=status.HTTP_202_ACCEPTED)
async def control_harness_run(
    run_id: str,
    body: AgentControlLoopControlRequest,
    owner_id: Annotated[str, Depends(harness_owner)],
    runtime: Annotated[HarnessRuntime, Depends(get_harness_runtime)],
):
    try:
        result = await runtime.control(owner_id, run_id, body)
        return runtime.public_control_result(result)
    except HarnessNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HarnessConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/runs/{run_id}/events")
async def stream_harness_events(
    run_id: str,
    owner_id: Annotated[str, Depends(harness_owner)],
    runtime: Annotated[HarnessRuntime, Depends(get_harness_runtime)],
    after: int = Query(default=0, ge=0),
):
    # Validate the owner/run before creating the streaming response.  Errors
    # raised inside the generator would otherwise become an empty HTTP 200
    # stream, which hides both missing and unauthorized runs from clients.
    try:
        await runtime.get(owner_id, run_id)
    except HarnessNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def body():
        try:
            async for event in runtime.events(owner_id, run_id, after):
                if event is None:
                    yield ": heartbeat\n\n"
                    continue
                snapshot = await runtime.get(owner_id, run_id)
                event = runtime.public_event(event, snapshot)
                yield (
                    f"id: {event.sequence}\n"
                    f"event: {event.event_name}\n"
                    f"data: {json.dumps(event.model_dump(mode='json'), ensure_ascii=False)}\n\n"
                )
        except HarnessNotFoundError:
            # A missing owner/run is not a stream-level success.  There is no
            # safe event to fabricate, so close the stream after the HTTP layer
            # has already accepted the request.
            return

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
