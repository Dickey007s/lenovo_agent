import asyncio
import hashlib
import json
import shutil
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from packages.contracts import Demo2WorkerSpec
from services.api.app.api.routes import router
from services.api.app.application.demo2_cockpit import Demo2CockpitService
from services.api.app.application.demo2_execution import (
    Demo2ExecutionService,
    Demo2WorkerDraft,
)
from services.api.app.application.demo_source_catalog import DemoSourceCatalog, DemoSourceError


class FakeWorker:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def run(self, spec: Demo2WorkerSpec, sources):
        self.calls.append(spec.role)
        return Demo2WorkerDraft(
            summary=f"fake summary for {spec.role}",
            key_points=[source.document_id for source in sources],
        )


class ChangedSourceCatalog(DemoSourceCatalog):
    def require_unchanged(self, expected):
        raise DemoSourceError("演示资料在执行期间发生变化")


class FailingWorker:
    async def run(self, spec: Demo2WorkerSpec, sources):
        if spec.role == "revenue_analyst":
            await asyncio.sleep(0.01)
            raise RuntimeError("injected worker failure")
        await asyncio.sleep(1)
        return Demo2WorkerDraft(
            summary=f"late summary for {spec.role}",
            key_points=[source.document_id for source in sources],
        )


def build_test_app(
    worker=None,
    *,
    source_catalog: DemoSourceCatalog | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    cockpit = Demo2CockpitService()
    app.state.demo2_cockpit_service = cockpit
    app.state.demo2_execution_service = Demo2ExecutionService(
        cockpit,
        source_catalog=source_catalog,
        worker_agent=worker or FakeWorker(),
    )
    return app


def build_changed_source_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    cockpit = Demo2CockpitService()
    app.state.demo2_cockpit_service = cockpit
    app.state.demo2_execution_service = Demo2ExecutionService(
        cockpit,
        source_catalog=ChangedSourceCatalog(),
        worker_agent=FakeWorker(),
    )
    return app


def _variant_source_catalog(tmp_path: Path) -> DemoSourceCatalog:
    root = tmp_path / "customer-a"
    shutil.copytree(DemoSourceCatalog.default_root(), root)
    changes = {
        "crm/customer-a-revenue-close-v3.csv": (",2400,", ",2450,"),
        "forecast/customer-a-revenue-forecast-v2.csv": (",2680,", ",2790,"),
    }
    for relative_path, (before, after) in changes.items():
        path = root / relative_path
        path.write_text(path.read_text(encoding="utf-8").replace(before, after), encoding="utf-8")
    project_path = root / "project/customer-a-weekly-status-v5.json"
    project = json.loads(project_path.read_text(encoding="utf-8"))
    project["milestone_variance_days"] = 9
    project["risk_summary"] = "资源切换导致交付里程碑延期风险。"
    project_path.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for document in manifest["documents"]:
        path = root / document["relative_path"]
        document["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return DemoSourceCatalog(root)


async def _select_adaptive(client: AsyncClient, user_id: str = "execution-user") -> dict:
    response = await client.post(
        "/v1/demo2/work-items/customer_a_operating_review/route",
        headers={"X-User-Id": user_id},
        json={
            "mode": "adaptive_swarm",
            "expected_version": 1,
            "idempotency_key": "demo2-execution-route",
        },
    )
    assert response.status_code == 200
    assert response.json()["item"]["selected_mode"] == "adaptive_swarm"
    return response.json()["item"]


async def _wait_for_terminal(client: AsyncClient, user_id: str) -> dict:
    for _ in range(100):
        response = await client.get(
            "/v1/demo2/work-items/customer_a_operating_review/execution",
            headers={"X-User-Id": user_id},
        )
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"completed", "failed", "cancelled"}:
            return payload
        await asyncio.sleep(0)
    raise AssertionError("Demo 2 execution did not reach a terminal state")


async def test_demo2_adaptive_swarm_runs_workers_replans_and_returns_receipt() -> None:
    fake = FakeWorker()
    app = build_test_app(fake)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        item = await _select_adaptive(client)
        start = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/execution",
            headers={"X-User-Id": "execution-user"},
            json={
                "expected_version": item["version"],
                "idempotency_key": "demo2-execution-start",
                "max_workers": 3,
            },
        )
        assert start.status_code == 202
        assert start.json()["execution"]["status"] == "queued"
        assert start.json()["execution"]["source_document_ids"]
        terminal = await _wait_for_terminal(client, "execution-user")
        cockpit = await client.get(
            "/v1/demo2/work-items/customer_a_operating_review",
            headers={"X-User-Id": "execution-user"},
        )

    assert terminal["status"] == "completed"
    assert len(fake.calls) == 4
    assert {worker["status"] for worker in terminal["worker_runs"]} == {"completed"}
    assert all(
        worker["processing"] == {
            "path": "deterministic",
            "kind": "deterministic",
            "label": "确定性演示 Worker",
            "model_called": False,
            "model": None,
            "elapsed_ms": worker["processing"]["elapsed_ms"],
            "output_used": "deterministic",
            "fallback_reason": None,
        }
        for worker in terminal["worker_runs"]
    )
    assert {worker["trigger"] for worker in terminal["worker_runs"]} == {
        "initial_plan",
        "dynamic_replan",
    }
    assert len(terminal["artifacts"]) == 5
    assert terminal["receipt"]["external_side_effect"] == "none"
    assert terminal["receipt"]["final_artifact_version_id"]
    event_types = [event["event_type"] for event in terminal["events"]]
    assert event_types[0] == "EXECUTION_QUEUED"
    assert "DYNAMIC_REPLAN" in event_types
    assert "WORKER_ADDED" in event_types
    assert event_types[-1] == "EXECUTION_COMPLETED"
    assert [event["sequence"] for event in terminal["events"]] == list(
        range(1, terminal["last_event_sequence"] + 1)
    )
    assert cockpit.status_code == 200
    assert cockpit.json()["execution_status"] == "completed"
    assert cockpit.json()["execution_id"] == terminal["execution_id"]


async def test_demo2_execution_start_is_idempotent_and_owner_isolated() -> None:
    app = build_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        item = await _select_adaptive(client, "owner-a")
        body = {
            "expected_version": item["version"],
            "idempotency_key": "demo2-execution-replay",
            "max_workers": 3,
        }
        first = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/execution",
            headers={"X-User-Id": "owner-a"},
            json=body,
        )
        replay = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/execution",
            headers={"X-User-Id": "owner-a"},
            json=body,
        )
        other = await client.get(
            "/v1/demo2/work-items/customer_a_operating_review/execution",
            headers={"X-User-Id": "owner-b"},
        )
        duplicate = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/execution",
            headers={"X-User-Id": "owner-a"},
                json={**body, "idempotency_key": "demo2-execution-second"},
        )
        terminal = await _wait_for_terminal(client, "owner-a")

    assert first.status_code == 202
    assert replay.status_code == 202
    assert first.json()["replayed"] is False
    assert replay.json()["replayed"] is True
    assert replay.json()["item"] == first.json()["item"]
    assert replay.json()["execution"] == first.json()["execution"]
    assert replay.json()["execution"]["last_event_sequence"] == 1
    assert [event["event_type"] for event in terminal["events"]].count(
        "EXECUTION_QUEUED"
    ) == 1
    assert [event["event_type"] for event in terminal["events"]].count(
        "EXECUTION_STARTED"
    ) == 1
    assert other.status_code == 404
    assert duplicate.status_code == 409


async def test_demo2_execution_sse_replays_ordered_events_after_completion() -> None:
    app = build_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        item = await _select_adaptive(client, "sse-user")
        start = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/execution",
            headers={"X-User-Id": "sse-user"},
            json={
                "expected_version": item["version"],
                "idempotency_key": "demo2-execution-sse",
            },
        )
        assert start.status_code == 202
        terminal = await _wait_for_terminal(client, "sse-user")
        response = await client.get(
            "/v1/demo2/work-items/customer_a_operating_review/execution/events?after=0",
            headers={"X-User-Id": "sse-user"},
        )
        alias_response = await client.get(
            "/v1/demo2/work-items/customer_a_operating_review/execution/stream"
            f"?after=0&execution_id={terminal['execution_id']}",
            headers={"X-User-Id": "sse-user"},
        )

    for stream_response in (response, alias_response):
        assert stream_response.status_code == 200
        assert stream_response.headers["content-type"].startswith("text/event-stream")
        assert "event: EXECUTION_QUEUED" in stream_response.text
        assert "event: DYNAMIC_REPLAN" in stream_response.text
        assert "event: EXECUTION_COMPLETED" in stream_response.text
        assert stream_response.text.count("event: ") == terminal["last_event_sequence"]
        assert stream_response.text.count("data: ") == terminal["last_event_sequence"]
        frames = [
            frame
            for frame in stream_response.text.split("\n\n")
            if "data: " in frame
        ]
        assert len(frames) == terminal["last_event_sequence"]
        assert all("event: " in frame for frame in frames)


async def test_demo2_execution_requires_adaptive_swarm_and_fail_closes_on_source_error() -> None:
    app = build_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        route = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/route",
            headers={"X-User-Id": "guard-user"},
            json={
                "mode": "single_agent",
                "expected_version": 1,
                "idempotency_key": "demo2-execution-guard-route",
            },
        )
        denied = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/execution",
            headers={"X-User-Id": "guard-user"},
            json={
                "expected_version": route.json()["item"]["version"],
                "idempotency_key": "demo2-execution-guard-start",
            },
        )

    assert denied.status_code == 409


async def test_demo2_execution_fails_closed_when_frozen_files_change() -> None:
    app = build_changed_source_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        item = await _select_adaptive(client, "changed-source-user")
        start = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/execution",
            headers={"X-User-Id": "changed-source-user"},
            json={
                "expected_version": item["version"],
                "idempotency_key": "demo2-execution-changed-source",
            },
        )
        terminal = await _wait_for_terminal(client, "changed-source-user")

    assert start.status_code == 202
    assert terminal["status"] == "failed"
    assert terminal["receipt"] is None
    assert terminal["events"][-1]["event_type"] == "EXECUTION_FAILED"


async def test_demo2_final_bundle_is_derived_from_variant_file_facts(tmp_path: Path) -> None:
    app = build_test_app(source_catalog=_variant_source_catalog(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        item = await _select_adaptive(client, "variant-source-user")
        start = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/execution",
            headers={"X-User-Id": "variant-source-user"},
            json={
                "expected_version": item["version"],
                "idempotency_key": "demo2-execution-variant-source",
            },
        )
        terminal = await _wait_for_terminal(client, "variant-source-user")

    assert start.status_code == 202
    assert terminal["status"] == "completed"
    final = next(
        artifact
        for artifact in terminal["artifacts"]
        if artifact["kind"] == "verified_report_bundle"
    )
    assert "2450 万元" in final["content"]["revenue_basis"]
    assert "2790 万元" in final["content"]["revenue_basis"]
    assert "资源切换导致交付里程碑延期风险" in final["content"]["project_risk"]
    assert "9 天" in final["content"]["project_risk"]
    assert "2400 万元" not in final["content"]["revenue_basis"]
    assert "7 天" not in final["content"]["project_risk"]


async def test_demo2_worker_failure_cancels_siblings_without_late_completion() -> None:
    app = build_test_app(FailingWorker())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        item = await _select_adaptive(client, "worker-failure-user")
        start = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/execution",
            headers={"X-User-Id": "worker-failure-user"},
            json={
                "expected_version": item["version"],
                "idempotency_key": "demo2-execution-worker-failure",
            },
        )
        terminal = await _wait_for_terminal(client, "worker-failure-user")
        await asyncio.sleep(0.02)
        stable = await client.get(
            "/v1/demo2/work-items/customer_a_operating_review/execution",
            headers={"X-User-Id": "worker-failure-user"},
        )

    assert start.status_code == 202
    assert terminal["status"] == "failed"
    workers = {worker["role"]: worker for worker in terminal["worker_runs"]}
    assert workers["revenue_analyst"]["status"] == "failed"
    assert workers["revenue_analyst"]["error_code"] == "worker_runtime_error"
    assert workers["project_risk_analyst"]["status"] == "cancelled"
    assert workers["request_context_analyst"]["status"] == "cancelled"
    assert all(
        worker["error_code"] in {"worker_runtime_error", "cancelled_due_to_peer_failure"}
        for worker in workers.values()
    )
    event_types = [event["event_type"] for event in terminal["events"]]
    assert "WORKER_FAILED" in event_types
    assert event_types.count("WORKER_CANCELLED") == 2
    assert event_types[-1] == "EXECUTION_FAILED"
    assert stable.json()["last_event_sequence"] == terminal["last_event_sequence"]
    assert stable.json()["events"][-1]["event_type"] == "EXECUTION_FAILED"
