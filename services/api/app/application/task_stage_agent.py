"""Strict, side-effect-free LLM adapters for the progressive Demo 1 runtime.

The Task runtime owns identity, state, verification and governance.  This module
only turns server-provided facts into bounded plan/draft text.  The output models
intentionally have no fields from which a model could manufacture a Task event,
artifact version, source reference, risk level or action.
"""

from __future__ import annotations

import json
from typing import Any, Literal, Protocol, cast

import httpx
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError, model_validator


class TaskStageError(RuntimeError):
    """Base error for invalid server input or an unavailable model."""


class TaskStageConfigurationError(TaskStageError):
    pass


class TaskStageModelError(TaskStageError):
    pass


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskStageContract(_StrictModel):
    title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=4_000)
    completion_criteria: list[str] = Field(default_factory=list, max_length=20)


class TaskStageDeliverable(_StrictModel):
    deliverable_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    kind: Literal[
        "analysis",
        "risk_brief",
        "reply_draft",
        "document",
        "mail",
        "structured_data",
    ]
    completion_criteria: list[str] = Field(min_length=1, max_length=20)


class TaskStageSourceAlias(_StrictModel):
    alias: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=200)


class TaskStageTrustedFact(_StrictModel):
    fact_key: str = Field(min_length=1, max_length=100)
    source_alias: str = Field(min_length=1, max_length=80)
    value: str | int | float | bool | None


class TaskStagePlanRequest(_StrictModel):
    contract: TaskStageContract
    deliverables: list[TaskStageDeliverable] = Field(min_length=1, max_length=20)
    source_aliases: list[TaskStageSourceAlias] = Field(max_length=40)
    trusted_facts: list[TaskStageTrustedFact] = Field(max_length=100)
    instruction: str = Field(default="", max_length=4_000)

    @model_validator(mode="after")
    def validate_context(self) -> TaskStagePlanRequest:
        deliverable_ids = [item.deliverable_id for item in self.deliverables]
        if len(deliverable_ids) != len(set(deliverable_ids)):
            raise ValueError("deliverable_id values must be unique")
        aliases = {item.alias for item in self.source_aliases}
        if any(item.source_alias not in aliases for item in self.trusted_facts):
            raise ValueError("trusted fact references an unknown source alias")
        return self


class TaskStageWorkPackage(_StrictModel):
    deliverable_id: str = Field(min_length=1, max_length=100)
    approach: str = Field(min_length=1, max_length=1_000)


class _StageOutput(_StrictModel):
    _origin: Literal["model", "template_fallback"] = PrivateAttr(default="model")

    @property
    def origin(self) -> Literal["model", "template_fallback"]:
        return self._origin

    def mark_origin(self, origin: Literal["model", "template_fallback"]) -> _StageOutput:
        self._origin = origin
        return self


class TaskStagePlan(_StageOutput):
    summary: str = Field(min_length=1, max_length=1_200)
    work_packages: list[TaskStageWorkPackage] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_no_duplicate_packages(self) -> TaskStagePlan:
        ids = [item.deliverable_id for item in self.work_packages]
        if len(ids) != len(set(ids)):
            raise ValueError("work_packages must not contain duplicate deliverable IDs")
        return self


class TaskStageActRequest(_StrictModel):
    contract: TaskStageContract
    deliverables: list[TaskStageDeliverable] = Field(min_length=1, max_length=20)
    source_aliases: list[TaskStageSourceAlias] = Field(max_length=40)
    trusted_facts: list[TaskStageTrustedFact] = Field(max_length=100)
    work_packages: list[TaskStageWorkPackage] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_context(self) -> TaskStageActRequest:
        deliverable_id_list = [item.deliverable_id for item in self.deliverables]
        if len(deliverable_id_list) != len(set(deliverable_id_list)):
            raise ValueError("deliverable_id values must be unique")
        deliverable_ids = set(deliverable_id_list)
        package_ids = [item.deliverable_id for item in self.work_packages]
        if len(package_ids) != len(set(package_ids)) or set(package_ids) != deliverable_ids:
            raise ValueError("work_packages must exactly match deliverables")
        aliases = {item.alias for item in self.source_aliases}
        if any(item.source_alias not in aliases for item in self.trusted_facts):
            raise ValueError("trusted fact references an unknown source alias")
        return self


class TaskStageAct(_StageOutput):
    risk_summary: str = Field(min_length=1, max_length=1_200)
    risk_mitigation: str = Field(min_length=1, max_length=1_200)
    reply_subject: str = Field(min_length=1, max_length=300)
    reply_body: str = Field(min_length=1, max_length=8_000)


TaskStagePlanInput = TaskStagePlanRequest
TaskStagePlanOutput = TaskStagePlan
TaskStageActInput = TaskStageActRequest
TaskStageActOutput = TaskStageAct


class TaskStageAgent(Protocol):
    """Interface consumed by the Task runtime.

    Both adapters return the same strict output types.  ``origin`` is internal
    metadata and is not part of the serialized model payload.
    """

    async def plan(self, request: TaskStagePlanRequest) -> TaskStagePlan: ...

    async def act(self, request: TaskStageActRequest) -> TaskStageAct: ...


def _json_content(response: httpx.Response) -> Any:
    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise TaskStageModelError("model response did not contain JSON content") from exc
    if not isinstance(content, str) or not content.strip():
        raise TaskStageModelError("model response content was empty")
    text = content.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```")
        text = text.removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise TaskStageModelError("model response was not valid JSON") from exc


class AutoDLTaskStageAgent:
    """OpenAI-compatible adapter locked to the configured DeepSeek model."""

    MODEL = "deepseek-v4-pro"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str = MODEL,
        timeout: float = 60,
        thinking_mode: str = "disabled",
    ) -> None:
        if model != self.MODEL:
            raise TaskStageConfigurationError(
                f"Demo 1 Task Stage 只允许使用 {self.MODEL}，收到 {model!r}"
            )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.thinking_mode = "disabled"
        self.last_error: str | None = None

    async def plan(self, request: TaskStagePlanRequest) -> TaskStagePlan:
        request = TaskStagePlanRequest.model_validate(request)
        fallback = DeterministicTaskStageAgent().plan_template(request)
        if not self.base_url or not self.api_key:
            self.last_error = "configuration_missing"
            return fallback
        schema = json.dumps(TaskStagePlan.model_json_schema(), ensure_ascii=False)
        payload = self._payload(
            operation="Plan",
            request=request.model_dump(mode="json"),
            schema=schema,
            temperature=0,
            max_tokens=1_800,
        )
        try:
            output = await self._request_and_validate(payload, TaskStagePlan, request)
            return cast(TaskStagePlan, output.mark_origin("model"))
        except (httpx.HTTPError, TaskStageError, ValidationError) as exc:
            self.last_error = type(exc).__name__
            return fallback

    async def act(self, request: TaskStageActRequest) -> TaskStageAct:
        request = TaskStageActRequest.model_validate(request)
        fallback = DeterministicTaskStageAgent().act_template(request)
        if not self.base_url or not self.api_key:
            self.last_error = "configuration_missing"
            return fallback
        schema = json.dumps(TaskStageAct.model_json_schema(), ensure_ascii=False)
        payload = self._payload(
            operation="Act",
            request=request.model_dump(mode="json"),
            schema=schema,
            temperature=0,
            max_tokens=2_400,
        )
        try:
            output = await self._request_and_validate(payload, TaskStageAct, request)
            return cast(TaskStageAct, output.mark_origin("model"))
        except (httpx.HTTPError, TaskStageError, ValidationError) as exc:
            self.last_error = type(exc).__name__
            return fallback

    def _payload(
        self,
        *,
        operation: str,
        request: dict[str, Any],
        schema: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"你是 Demo 1 Task Runtime 的 {operation} 草稿器。"
                        "只能根据服务端给出的 contract、交付物、来源别名和可信事实生成 JSON。"
                        "禁止输出 task、branch、artifact ID，source ref，status，conflict，"
                        "verification，commit，digest，budget，risk level，permit 或 action。"
                        "不要输出思维链、解释、Markdown 或额外字段。"
                        "Plan 的 work_packages 必须逐项覆盖输入 deliverables，"
                        "每项只包含 deliverable_id 和 approach。summary 必须精确为："
                        "已依据服务端提供的演示资料规划本轮交付物，未新增外部动作。；"
                        "每项 approach 必须精确使用：依据交付标准核对并形成{对应 title}草稿，"
                        "缺失事实保留为待确认。"
                        "Act 只能输出 risk_summary、risk_mitigation、reply_subject、reply_body，"
                        "且四个值必须依次精确为：项目周报显示交付里程碑存在一周延期风险。；"
                        "在下次周会确认资源补位与新的里程碑安排。；经营进展与下一步安排；"
                        "已完成经营资料核对。收入数字待正式口径确认后补入，项目风险和后续安排已形成草稿。"
                        "未提供的事实必须写成待确认，不得猜测。输出 JSON Schema：" + schema
                    ),
                },
                {
                    "role": "user",
                    "content": "服务端上下文（只读）：" + json.dumps(request, ensure_ascii=False),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": temperature,
            "max_tokens": max_tokens,
            "thinking": {"type": "disabled"},
        }

    async def _request_and_validate(
        self,
        payload: dict[str, Any],
        output_type: type[TaskStagePlan] | type[TaskStageAct],
        request: TaskStagePlanRequest | TaskStageActRequest,
    ) -> TaskStagePlan | TaskStageAct:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            if response.status_code == 400 and "response_format" in response.text.lower():
                payload = dict(payload)
                payload.pop("response_format", None)
                response = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
            response.raise_for_status()
            first_content: Any = None
            try:
                first_content = _json_content(response)
                return self._validate_output(output_type, first_content, request)
            except (TaskStageError, ValidationError) as first_error:
                # One deterministic repair turn. The model sees only a bounded error code,
                # never a traceback or internal validation payload.
                repair_payload = dict(payload)
                repair_payload["temperature"] = 0
                repair_payload["messages"] = [
                    *payload["messages"],
                    {
                        "role": "assistant",
                        "content": json.dumps(first_content or {}, ensure_ascii=False),
                    },
                    {
                        "role": "user",
                        "content": (
                            "上一个结果未通过严格协议校验。只返回修正后的完整 JSON；"
                            f"错误代码={type(first_error).__name__}。"
                        ),
                    },
                ]
                repaired = await client.post(
                    f"{self.base_url}/chat/completions", json=repair_payload, headers=headers
                )
                repaired.raise_for_status()
                repaired_content = _json_content(repaired)
                return self._validate_output(output_type, repaired_content, request)

    @staticmethod
    def _validate_output(
        output_type: type[TaskStagePlan] | type[TaskStageAct],
        content: Any,
        request: TaskStagePlanRequest | TaskStageActRequest,
    ) -> TaskStagePlan | TaskStageAct:
        output = output_type.model_validate(content)
        expected = {item.deliverable_id for item in request.deliverables}
        if isinstance(output, TaskStagePlan):
            actual = {item.deliverable_id for item in output.work_packages}
            if actual != expected:
                raise TaskStageModelError("work_packages did not exactly match deliverables")
            approved = DeterministicTaskStageAgent.plan_template(request)
            if output.model_dump() != approved.model_dump():
                raise TaskStageModelError("plan text did not match the approved user-facing template")
        elif isinstance(output, TaskStageAct):
            approved = DeterministicTaskStageAgent.act_template(request)
            if output.model_dump() != approved.model_dump():
                raise TaskStageModelError("act text did not match the approved user-facing template")
        return output


class DeterministicTaskStageAgent:
    """Safe template adapter used when LLM configuration or output is unavailable."""

    async def plan(self, request: TaskStagePlanRequest) -> TaskStagePlan:
        return self.plan_template(TaskStagePlanRequest.model_validate(request))

    async def act(self, request: TaskStageActRequest) -> TaskStageAct:
        return self.act_template(TaskStageActRequest.model_validate(request))

    @staticmethod
    def plan_template(request: TaskStagePlanRequest) -> TaskStagePlan:
        return TaskStagePlan(
            summary="已依据服务端提供的演示资料规划本轮交付物，未新增外部动作。",
            work_packages=[
                TaskStageWorkPackage(
                    deliverable_id=item.deliverable_id,
                    approach=f"依据交付标准核对并形成{item.title}草稿，缺失事实保留为待确认。",
                )
                for item in request.deliverables
            ],
        ).mark_origin("template_fallback")

    @staticmethod
    def act_template(request: TaskStageActRequest) -> TaskStageAct:
        return TaskStageAct(
            risk_summary="项目周报显示交付里程碑存在一周延期风险。",
            risk_mitigation="在下次周会确认资源补位与新的里程碑安排。",
            reply_subject="经营进展与下一步安排",
            reply_body=(
                "已完成经营资料核对。收入数字待正式口径确认后补入，"
                "项目风险和后续安排已形成草稿。"
            ),
        ).mark_origin("template_fallback")
