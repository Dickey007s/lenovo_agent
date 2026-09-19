"""Typed single-action contracts shared by the workbench and runtime."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ActionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal[
        "format_text", "extract_excerpt", "create_task", "send_message", "restricted_action",
        "compare_materials",
    ]
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(default="", max_length=5000)
    target: str = Field(default="", max_length=120)
    due_date: date | None = None
    source_ref: str | None = Field(default=None, pattern=r"^forte-[0-9a-f]{16}$")
    alternative_content: str = Field(default="", max_length=5000)

    @field_validator("title", "content", "target", "alternative_content")
    @classmethod
    def valid_text(cls, value: str) -> str:
        if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
            raise ValueError("文字包含不可显示的控制字符")
        return value

    @model_validator(mode="after")
    def comparison_scope(self):
        if self.alternative_content and self.operation != "compare_materials":
            raise ValueError("只有材料对照事项可以提交第二份材料")
        return self


class ActionReceipt(BaseModel):
    record_id: str
    kind: Literal["text_copy", "excerpt_draft", "test_task", "test_message", "decision_note"]
    content: str
    target: str
    created_at: datetime
    undone_at: datetime | None = None
    external_action: Literal["none"] = "none"


class ActionHistory(BaseModel):
    revision: int
    event: str
    message: str
    at: datetime
    input: ActionInput
    content_snapshot: str | None = None


class ActionDecision(BaseModel):
    option: Literal["first", "second"]
    rationale: str
    selected_content: str
    at: datetime


class OfficeAction(BaseModel):
    action_id: str
    revision: int = 1
    policy_version: Literal["office-actions.test.v1", "office-actions.test.v2"] = "office-actions.test.v2"
    input: ActionInput
    status: Literal[
        "needs_input", "awaiting_confirmation", "deferred", "draft_ready",
        "executed", "denied", "cancelled", "undone", "stale", "awaiting_decision", "decided",
    ]
    risk_level: Literal["L1", "L2", "L3", "L4", "L5"]
    autonomy_level: Literal["AL1", "AL2", "AL3", "AL4"]
    mode: str
    reason: str
    missing_fields: list[str] = Field(default_factory=list)
    required_checks: list[str] = Field(default_factory=list)
    target_label: str
    before: str
    preview: str
    source_label: str | None = None
    source_excerpt: str | None = None
    impact: str
    reversibility: str
    result_message: str
    receipt: ActionReceipt | None = None
    decision: ActionDecision | None = None
    history: list[ActionHistory] = Field(default_factory=list, max_length=60)
    execution_environment: Literal["isolated_test_records"] = "isolated_test_records"
    external_action: Literal["none"] = "none"
    model_called: Literal[False] = False


class OfficeActionControl(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: Literal["confirm", "revise", "defer", "cancel", "undo", "edit_draft", "record_decision"]
    expected_version: int = Field(ge=1)
    action_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=160)
    replacement: ActionInput | None = None
    reviewed_fields: list[Literal["target", "content", "impact"]] = Field(
        default_factory=list, max_length=3
    )
    edited_content: str | None = Field(default=None, min_length=1, max_length=5000)
    selected_option: Literal["first", "second"] | None = None
    rationale: str = Field(default="", max_length=1000)

    @field_validator("edited_content", "rationale")
    @classmethod
    def valid_control_text(cls, value: str | None) -> str | None:
        return ActionInput.valid_text(value) if value is not None else None

    @model_validator(mode="after")
    def fields_match_command(self):
        if self.command == "edit_draft":
            if not self.edited_content or not self.edited_content.strip():
                raise ValueError("请填写草稿内容")
        elif self.edited_content is not None:
            raise ValueError("只有编辑草稿可以提交草稿正文")
        if self.command == "record_decision":
            if self.selected_option is None or not self.rationale.strip():
                raise ValueError("请明确选择材料并说明判断理由")
        elif self.selected_option is not None or self.rationale:
            raise ValueError("只有记录判断可以提交选择和理由")
        if self.replacement is not None and self.command != "revise":
            raise ValueError("只有修改操作可以替换输入")
        if self.reviewed_fields and self.command != "confirm":
            raise ValueError("核对项只用于当前动作的确认")
        return self
