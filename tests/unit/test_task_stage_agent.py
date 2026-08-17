from __future__ import annotations

import json

import httpx
import pytest
from pydantic import ValidationError

from services.api.app.application.task_stage_agent import (
    AutoDLTaskStageAgent,
    DeterministicTaskStageAgent,
    TaskStageAct,
    TaskStageActRequest,
    TaskStageContract,
    TaskStageDeliverable,
    TaskStagePlanRequest,
    TaskStageSourceAlias,
    TaskStageTrustedFact,
    TaskStageConfigurationError,
)


def _plan_request() -> TaskStagePlanRequest:
    return TaskStagePlanRequest(
        contract=TaskStageContract(
            title="客户 A 经营汇报",
            objective="形成带来源的经营分析、风险页和客户回复草稿。",
            completion_criteria=["三个交付物均通过服务端验证"],
        ),
        deliverables=[
            TaskStageDeliverable(
                deliverable_id="operating-analysis",
                title="经营分析",
                kind="analysis",
                completion_criteria=["收入口径待确认时不得自动选择"],
            ),
            TaskStageDeliverable(
                deliverable_id="risk-brief",
                title="风险页",
                kind="risk_brief",
                completion_criteria=["风险项绑定项目周报"],
            ),
            TaskStageDeliverable(
                deliverable_id="reply-draft",
                title="客户回复草稿",
                kind="reply_draft",
                completion_criteria=["不触发外部发送"],
            ),
        ],
        source_aliases=[
            TaskStageSourceAlias(alias="crm_official", label="CRM 正式收入"),
            TaskStageSourceAlias(alias="forecast", label="收入预测表"),
        ],
        trusted_facts=[
            TaskStageTrustedFact(
                fact_key="official_revenue_wan",
                source_alias="crm_official",
                value=2400,
            ),
            TaskStageTrustedFact(
                fact_key="forecast_revenue_wan", source_alias="forecast", value=2680
            ),
        ],
    )


def _act_request() -> TaskStageActRequest:
    plan = DeterministicTaskStageAgent().plan_template(_plan_request())
    request = _plan_request()
    return TaskStageActRequest(
        contract=request.contract,
        deliverables=request.deliverables,
        source_aliases=request.source_aliases,
        trusted_facts=request.trusted_facts,
        work_packages=plan.work_packages,
    )


class _Response:
    def __init__(self, payload, status_code: int = 200, text: str = "") -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = text or json.dumps(payload)

    def json(self):
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://test/chat/completions")
            raise httpx.HTTPStatusError(self.text, request=request, response=self)


class _Client:
    def __init__(self, responses: list[_Response], calls: list[dict]) -> None:
        self.responses = responses
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url: str, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def _completion(content: dict) -> _Response:
    return _Response({"choices": [{"message": {"content": json.dumps(content)}}]})


def test_adapter_is_locked_to_deepseek_v4_pro() -> None:
    with pytest.raises(TaskStageConfigurationError, match="deepseek-v4-pro"):
        AutoDLTaskStageAgent(base_url="http://model", api_key="secret", model="other-model")


@pytest.mark.asyncio
async def test_no_configuration_is_explicit_template_fallback() -> None:
    agent = AutoDLTaskStageAgent(base_url="", api_key="")

    result = await agent.plan(_plan_request())

    assert result.origin == "template_fallback"
    assert set(result.model_dump()) == {"summary", "work_packages"}
    assert {item.deliverable_id for item in result.work_packages} == {
        "operating-analysis",
        "risk-brief",
        "reply-draft",
    }
    assert agent.last_error == "configuration_missing"


def test_plan_rejects_unknown_input_fields_and_fact_aliases() -> None:
    with pytest.raises(ValidationError):
        TaskStagePlanRequest.model_validate(_plan_request().model_dump() | {"task_id": "forbidden"})

    payload = _plan_request().model_dump()
    payload["trusted_facts"][0]["source_alias"] = "unknown"
    with pytest.raises(ValidationError, match="unknown source alias"):
        TaskStagePlanRequest.model_validate(payload)


@pytest.mark.asyncio
async def test_schema_repair_is_one_turn_and_never_accepts_wrong_deliverable_ids(monkeypatch) -> None:
    calls: list[dict] = []
    responses = [
        _completion(
            {
                "summary": "模型草稿",
                "work_packages": [{"deliverable_id": "forged", "approach": "越权"}],
                "status": "committed",
            }
        ),
        _completion(
            {
                "summary": "模型草稿",
                "work_packages": [{"deliverable_id": "forged", "approach": "仍然越权"}],
            }
        ),
    ]
    monkeypatch.setattr(
        "httpx.AsyncClient", lambda **_: _Client(responses, calls)
    )
    agent = AutoDLTaskStageAgent(base_url="http://model", api_key="secret")

    result = await agent.plan(_plan_request())

    assert result.origin == "template_fallback"
    assert len(calls) == 2
    assert "ValidationError" in calls[1]["json"]["messages"][-1]["content"]
    assert "committed" not in calls[1]["json"]["messages"][-1]["content"]


@pytest.mark.asyncio
async def test_response_format_compatibility_retry_keeps_strict_schema(monkeypatch) -> None:
    calls: list[dict] = []
    valid = DeterministicTaskStageAgent.plan_template(_plan_request()).model_dump()
    responses = [
        _Response({"error": "response_format unsupported"}, 400, "response_format unsupported"),
        _completion(valid),
    ]
    monkeypatch.setattr(
        "httpx.AsyncClient", lambda **_: _Client(responses, calls)
    )
    agent = AutoDLTaskStageAgent(base_url="http://model", api_key="secret")

    result = await agent.plan(_plan_request())

    assert result.origin == "model"
    assert len(calls) == 2
    assert "response_format" in calls[0]["json"]
    assert "response_format" not in calls[1]["json"]


@pytest.mark.asyncio
async def test_plan_text_outside_safe_template_repairs_then_falls_back(monkeypatch) -> None:
    calls: list[dict] = []
    unsafe = {
        "summary": "<think>内部推理</think> status=committed fixture:crm/customer-a",
        "work_packages": [
            {
                "deliverable_id": item.deliverable_id,
                "approach": f"展示内部 ID 后完成 {item.title}",
            }
            for item in _plan_request().deliverables
        ],
    }
    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda **_: _Client([_completion(unsafe), _completion(unsafe)], calls),
    )
    agent = AutoDLTaskStageAgent(base_url="http://model", api_key="secret")

    result = await agent.plan(_plan_request())

    assert result.origin == "template_fallback"
    assert result.model_dump() == DeterministicTaskStageAgent.plan_template(
        _plan_request()
    ).model_dump()
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_act_forbids_status_and_falls_back(monkeypatch) -> None:
    calls: list[dict] = []
    invalid = {
        "risk_summary": "风险",
        "risk_mitigation": "缓解",
        "reply_subject": "主题",
        "reply_body": "正文",
        "status": "verified",
    }
    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda **_: _Client([_completion(invalid), _completion(invalid)], calls),
    )
    agent = AutoDLTaskStageAgent(base_url="http://model", api_key="secret")

    result = await agent.act(_act_request())

    assert isinstance(result, TaskStageAct)
    assert result.origin == "template_fallback"
    assert set(result.model_dump()) == {
        "risk_summary",
        "risk_mitigation",
        "reply_subject",
        "reply_body",
    }
