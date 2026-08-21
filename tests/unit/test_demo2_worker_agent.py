import json

from packages.contracts import Demo2WorkerSpec
from services.api.app.application.demo2_execution import (
    DeepSeekDemo2WorkerAgent,
    DeterministicDemo2WorkerAgent,
    Demo2ExecutionService,
)
from services.api.app.application.demo_source_catalog import DemoSourceCatalog


class _Response:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self):
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _Client:
    def __init__(self, responses: list[_Response], calls: list[dict]) -> None:
        self.responses = responses
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def post(self, url: str, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.responses.pop(0)


def _worker_and_sources():
    package = DemoSourceCatalog().load_demo1()
    sources = [
        package.document("fixture:crm/customer-a:official-revenue-v3"),
        package.document("fixture:forecast/customer-a:revenue-v2"),
    ]
    worker = Demo2WorkerSpec(
        worker_run_id="worker:test:revenue",
        work_item_id="customer_a_operating_review",
        role="revenue_analyst",
        label="收入事实核对",
        objective="核对收入事实",
        source_document_ids=[source.document_id for source in sources],
    )
    return worker, sources


async def test_demo2_worker_records_successful_model_processing(monkeypatch) -> None:
    worker, sources = _worker_and_sources()
    approved = await DeterministicDemo2WorkerAgent().run(worker, sources)
    calls: list[dict] = []
    response = _Response(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            approved.model_dump(),
                            ensure_ascii=False,
                        )
                    }
                }
            ]
        }
    )
    monkeypatch.setattr(
        "services.api.app.application.demo2_execution.httpx.AsyncClient",
        lambda **_: _Client([response], calls),
    )
    agent = DeepSeekDemo2WorkerAgent(base_url="http://model", api_key="secret")

    draft = await agent.run(worker, sources)
    processing = Demo2ExecutionService._processing_for_draft(draft, elapsed_ms=17)

    assert len(calls) == 1
    assert draft.origin == "model"
    assert processing.model_dump() == {
        "path": "language_model",
        "kind": "language_model",
        "label": "模型 Worker",
        "model_called": True,
        "model": "deepseek-v4-pro",
        "elapsed_ms": 17,
        "output_used": "model",
        "fallback_reason": None,
    }


async def test_demo2_worker_records_model_failure_and_fallback(monkeypatch) -> None:
    calls: list[dict] = []
    response = _Response(
        {"choices": [{"message": {"content": "not-json"}}]}
    )
    monkeypatch.setattr(
        "services.api.app.application.demo2_execution.httpx.AsyncClient",
        lambda **_: _Client([response], calls),
    )
    agent = DeepSeekDemo2WorkerAgent(base_url="http://model", api_key="secret")
    worker, sources = _worker_and_sources()

    draft = await agent.run(worker, sources)
    processing = Demo2ExecutionService._processing_for_draft(draft, elapsed_ms=21)

    assert len(calls) == 1
    assert draft.origin == "template_fallback"
    assert processing.path == "language_model"
    assert processing.model_called is True
    assert processing.model == "deepseek-v4-pro"
    assert processing.output_used == "template_fallback"
    assert processing.fallback_reason == "JSONDecodeError"


async def test_demo2_worker_rejects_fact_drift_and_uses_safe_template(monkeypatch) -> None:
    calls: list[dict] = []
    response = _Response(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "summary": "财务月结与预测完全一致。",
                                "key_points": ["已实现收入：9999 万元", "销售预测：9999 万元"],
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ]
        }
    )
    monkeypatch.setattr(
        "services.api.app.application.demo2_execution.httpx.AsyncClient",
        lambda **_: _Client([response], calls),
    )
    agent = DeepSeekDemo2WorkerAgent(base_url="http://model", api_key="secret")
    worker, sources = _worker_and_sources()

    draft = await agent.run(worker, sources)
    processing = Demo2ExecutionService._processing_for_draft(draft, elapsed_ms=13)

    assert len(calls) == 1
    assert "2400 万元" in draft.key_points[0]
    assert "2680 万元" in draft.key_points[1]
    assert draft.origin == "template_fallback"
    assert processing.path == "language_model"
    assert processing.output_used == "template_fallback"
    assert processing.fallback_reason == "Demo2WorkerFactMismatchError"


async def test_demo2_worker_records_missing_configuration_as_deterministic_fallback() -> None:
    agent = DeepSeekDemo2WorkerAgent(base_url="", api_key="")
    worker, sources = _worker_and_sources()

    draft = await agent.run(worker, sources)
    processing = Demo2ExecutionService._processing_for_draft(draft, elapsed_ms=1)

    assert processing.path == "deterministic"
    assert processing.model_called is False
    assert processing.model is None
    assert processing.output_used == "template_fallback"
    assert processing.fallback_reason == "configuration_missing"
