"""HTTP projection for the unified Agent Harness runtime."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from starlette.responses import StreamingResponse

from services.api.app.application.harness_runtime import (
    HarnessConflictError,
    HarnessNotFoundError,
    HarnessRunStart,
    HarnessRuntime,
)

router = APIRouter(prefix="/v1/harness", tags=["harness"])


def get_harness_runtime(request: Request) -> HarnessRuntime:
    runtime = getattr(request.app.state, "harness_runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Harness runtime 尚未配置")
    return runtime


def harness_owner(x_user_id: Annotated[str, Header()] = "demo_user") -> str:
    return x_user_id


@router.get("/scenarios")
async def list_harness_scenarios(
    runtime: Annotated[HarnessRuntime, Depends(get_harness_runtime)],
):
    return {"scenarios": runtime.list_scenarios()}


@router.get("/scenarios/{scenario_id}")
async def get_harness_scenario(
    scenario_id: str,
    runtime: Annotated[HarnessRuntime, Depends(get_harness_runtime)],
):
    try:
        return runtime.get_scenario(scenario_id)
    except HarnessNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
