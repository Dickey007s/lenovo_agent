from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from packages.contracts import ActionCandidate


class StrictConversationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


WorkspaceView = Literal[
    "approval",
    "mail",
    "document",
    "quote",
    "tasks",
    "calendar",
    "expense",
    "crm",
    "audit",
]


class SourceReference(StrictConversationModel):
    source_id: str
    label: str
    system: str
    excerpt: str = ""
    permission: str = "只读"
    updated_at: str = ""


class ArtifactDraft(StrictConversationModel):
    kind: Literal["mail", "document", "quote", "tasks", "calendar", "expense", "crm"]
    title: str
    content: dict[str, Any] = Field(default_factory=dict)
    sources: list[SourceReference] = Field(default_factory=list)


class ConversationPlan(StrictConversationModel):
    assistant_response: str
    focus_view: WorkspaceView = "approval"
    action: ActionCandidate | None = None
    artifact: ArtifactDraft | None = None


class ChatMessage(StrictConversationModel):
    message_id: str
    role: Literal["user", "assistant"]
    content: str
    status: Literal["streaming", "completed", "failed"] = "completed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkspaceArtifact(StrictConversationModel):
    artifact_id: str
    revision: int = Field(default=1, ge=1)
    kind: Literal["mail", "document", "quote", "tasks", "calendar", "expense", "crm"]
    title: str
    content: dict[str, Any] = Field(default_factory=dict)
    sources: list[SourceReference] = Field(default_factory=list)
    linked_action_id: str | None = None
    linked_run_id: str | None = None
    requires_recheck: bool = False
    change_history: list[dict[str, str]] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ConversationThread(StrictConversationModel):
    thread_id: str
    user_id: str
    title: str = "新对话"
    messages: list[ChatMessage] = Field(default_factory=list)
    artifacts: list[WorkspaceArtifact] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
