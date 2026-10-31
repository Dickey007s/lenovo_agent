"""Meeting minutes -> to-do list. Read-only: it proposes, the user confirms."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from services.api.app.application.minutes_splitter import (
    MAX_MINUTES_CHARS,
    MinutesSplit,
    MinutesSplitError,
    split_minutes,
)
from services.api.app.config import get_settings

router = APIRouter(prefix="/v1/harness/minutes", tags=["minutes"])


class MinutesSplitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minutes: str = Field(min_length=1, max_length=MAX_MINUTES_CHARS + 1000)
    # Demo mode: split by rules only, no model call.
    simulated: bool = False


@router.post("/split", response_model=MinutesSplit)
async def split(request: MinutesSplitRequest) -> MinutesSplit:
    settings = get_settings()
    try:
        return await split_minutes(
            request.minutes,
            base_url="" if request.simulated else settings.llm_base_url,
            api_key="" if request.simulated else settings.llm_api_key,
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
        )
    except MinutesSplitError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
