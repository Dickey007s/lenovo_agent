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
