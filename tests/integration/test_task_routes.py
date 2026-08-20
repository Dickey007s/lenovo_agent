from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from services.api.app.api.routes import router
from services.api.app.application.task_storage import InMemoryTaskStore
from services.api.app.application.tasks import TaskService, demo1_contract_draft


def build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.task_service = TaskService(InMemoryTaskStore())
    app.state.task_store_backend = "memory"
    app.state.checkpoint_backend = "memory"
    return app


async def test_demo1_task_routes_return_server_snapshot_and_enforce_owner() -> None:
    app = build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created_response = await client.post(
            "/v1/demo1/tasks", headers={"X-User-Id": "user_1"}
        )
        assert created_response.status_code == 201
        created = created_response.json()
        assert created["owner_id"] == "user_1"
        assert created["status"] == "ready"
        assert created["last_event_sequence"] == 1

        listed = await client.get("/v1/tasks", headers={"X-User-Id": "user_1"})
        assert listed.status_code == 200
        assert [item["task_id"] for item in listed.json()] == [created["task_id"]]

        fetched = await client.get(
            f"/v1/tasks/{created['task_id']}", headers={"X-User-Id": "user_1"}
        )
        assert fetched.status_code == 200
        assert fetched.json() == created

        hidden = await client.get(
            f"/v1/tasks/{created['task_id']}", headers={"X-User-Id": "user_2"}
        )
        assert hidden.status_code == 404


async def test_demo1_route_can_create_repeatable_rounds_without_losing_idempotency() -> None:
    app = build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first_headers = {
            "X-User-Id": "user_1",
            "Idempotency-Key": "demo1-round-001",
        }
        first = await client.post("/v1/demo1/tasks", headers=first_headers)
        replay = await client.post("/v1/demo1/tasks", headers=first_headers)
        second = await client.post(
            "/v1/demo1/tasks",
            headers={
                "X-User-Id": "user_1",
                "Idempotency-Key": "demo1-round-002",
            },
        )

        assert first.status_code == 201
        assert replay.status_code == 201
        assert second.status_code == 201
        assert replay.json()["task_id"] == first.json()["task_id"]
        assert second.json()["task_id"] != first.json()["task_id"]

        listed = await client.get("/v1/tasks", headers={"X-User-Id": "user_1"})
        assert listed.status_code == 200
        assert {item["task_id"] for item in listed.json()} == {
            first.json()["task_id"],
            second.json()["task_id"],
        }


async def test_demo1_route_rejects_key_reused_by_generic_route_for_different_contract() -> None:
    app = build_test_app()
    payload = demo1_contract_draft().model_dump(mode="json") | {
        "objective": "A different contract objective."
    }
    headers = {
        "X-User-Id": "user_1",
        "Idempotency-Key": "cross-route-create-001",
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/v1/tasks", json=payload, headers=headers)
        conflict = await client.post("/v1/demo1/tasks", headers=headers)

    assert created.status_code == 201
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "幂等键已用于不同任务契约"


async def test_task_create_route_forbids_server_fields_and_honors_idempotency() -> None:
    app = build_test_app()
    payload = demo1_contract_draft().model_dump(mode="json")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        invalid = await client.post(
            "/v1/tasks",
            json=payload | {"task_id": "client_owned", "status": "committed"},
            headers={"X-User-Id": "user_1"},
        )
        assert invalid.status_code == 422

        headers = {"X-User-Id": "user_1", "Idempotency-Key": "create-route-001"}
        first = await client.post("/v1/tasks", json=payload, headers=headers)
        second = await client.post("/v1/tasks", json=payload, headers=headers)
        assert first.status_code == 201
        assert second.status_code == 201
        assert second.json()["task_id"] == first.json()["task_id"]

        changed = payload | {"objective": "A different contract objective."}
        conflict = await client.post("/v1/tasks", json=changed, headers=headers)
        assert conflict.status_code == 409


async def test_health_exposes_task_store_backend() -> None:
    app = build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/health")

    assert response.status_code == 200
    assert response.json()["task_store"] == "memory"


async def test_task_start_and_control_routes_return_server_truth() -> None:
    app = build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created_response = await client.post("/v1/demo1/tasks", headers={"X-User-Id": "user_1"})
        created = created_response.json()
        start_body = {
            "expected_task_version": created["version"],
            "idempotency_key": "route-start-001",
        }
        started_response = await client.post(
            f"/v1/tasks/{created['task_id']}/start",
            json=start_body,
            headers={"X-User-Id": "user_1"},
        )
        assert started_response.status_code == 200
        started = started_response.json()
        assert started["status"] == "running"
        assert started["phase"] == "observe"
        assert started["stage_records"][-1]["phase"] == "observe"

        replay = await client.post(
            f"/v1/tasks/{created['task_id']}/start",
            json=start_body,
            headers={"X-User-Id": "user_1"},
        )
        assert replay.status_code == 200
        assert replay.json() == started

        stale_advance = await client.post(
            f"/v1/tasks/{created['task_id']}/advance",
            json={
                "expected_task_version": created["version"],
                "idempotency_key": "route-stale-advance-001",
            },
            headers={"X-User-Id": "user_1"},
        )
        assert stale_advance.status_code == 409

        waiting = started
        for index in range(4):
            advanced_response = await client.post(
                f"/v1/tasks/{created['task_id']}/advance",
                json={
                    "expected_task_version": waiting["version"],
                    "idempotency_key": f"route-advance-{index}",
                },
                headers={"X-User-Id": "user_1"},
            )
            assert advanced_response.status_code == 200
            waiting = advanced_response.json()
        assert waiting["status"] == "waiting_input"
        assert waiting["phase"] == "verify"
        assert [item["status"] for item in waiting["branches"]].count("waiting_evidence") == 1

        branch = next(item for item in waiting["branches"] if item["status"] == "waiting_evidence")
        resolved_response = await client.post(
            f"/v1/tasks/{created['task_id']}/controls",
            json={
                "kind": "resolve_evidence",
                "branch_id": branch["branch_id"],
                "resolution_option_id": "use-official-crm-revenue",
                "selected_source_ref": "fixture:crm/customer-a:official-revenue-v3",
                "expected_task_version": waiting["version"],
                "idempotency_key": "route-resolve-001",
            },
            headers={"X-User-Id": "user_1"},
        )
        assert resolved_response.status_code == 200
        assert resolved_response.json()["status"] == "committed"
        assert resolved_response.json()["last_commit"]["state_hash"].startswith("sha256:")


async def test_task_mutation_routes_reject_owner_stale_version_and_invalid_shape() -> None:
    app = build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = (await client.post("/v1/demo1/tasks", headers={"X-User-Id": "user_1"})).json()
        missing = await client.post(
            f"/v1/tasks/{created['task_id']}/start",
            json={"expected_task_version": 1, "idempotency_key": "wrong-owner-001"},
            headers={"X-User-Id": "user_2"},
        )
        assert missing.status_code == 404

        stale = await client.post(
            f"/v1/tasks/{created['task_id']}/start",
            json={"expected_task_version": 2, "idempotency_key": "stale-route-001"},
            headers={"X-User-Id": "user_1"},
        )
        assert stale.status_code == 409

        invalid = await client.post(
            f"/v1/tasks/{created['task_id']}/controls",
            json={
                "kind": "steer",
                "expected_task_version": 1,
                "idempotency_key": "invalid-route-001",
                "server_owned_status": "committed",
            },
            headers={"X-User-Id": "user_1"},
        )
        assert invalid.status_code == 422
