from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from services.api.app.api.routes import router
from services.api.app.application.demo2_cockpit import Demo2CockpitService


def build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.demo2_cockpit_service = Demo2CockpitService()
    return app


async def test_demo2_cockpit_returns_four_server_recommendations_without_fixture_ids() -> None:
    app = build_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/demo2/cockpit", headers={"X-User-Id": "user_1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["backend"] == "memory"
    assert [item["recommendation"]["mode"] for item in payload["items"]] == [
        "adaptive_swarm",
        "single_agent",
        "fixed_workflow",
        "tool_call",
    ]
    assert all(item["execution_status"] == "not_started" for item in payload["items"])
    assert "fixture:" not in response.text


async def test_demo2_customer_route_is_versioned_and_idempotent() -> None:
    app = build_test_app()
    headers = {"X-User-Id": "user_1"}
    body = {
        "mode": "single_agent",
        "expected_version": 1,
        "idempotency_key": "demo2-route-001",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/route",
            headers=headers,
            json=body,
        )
        replay = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/route",
            headers=headers,
            json=body,
        )
        different = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/route",
            headers=headers,
            json={**body, "mode": "fixed_workflow"},
        )
        cockpit = await client.get("/v1/demo2/cockpit", headers=headers)

    assert first.status_code == 200
    assert replay.status_code == 200
    assert first.json() == replay.json()
    assert first.json()["cockpit_version"] == 2
    assert first.json()["cockpit_last_event_sequence"] == 5
    assert first.json()["item"]["selected_mode"] == "single_agent"
    assert first.json()["item"]["selection_source"] == "user_override"
    assert first.json()["item"]["override_scope"] == "this_run"
    assert first.json()["item"]["execution_status"] == "not_started"
    assert first.json()["item"]["version"] == 2
    assert different.status_code == 409
    assert cockpit.status_code == 200
    assert cockpit.json()["version"] == 2
    selected = cockpit.json()["items"][0]
    assert selected["selected_mode"] == "single_agent"
    assert selected["version"] == 2
    assert selected["execution_status"] == "not_started"


async def test_demo2_recommendation_selection_is_not_reported_as_override() -> None:
    app = build_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/route",
            headers={"X-User-Id": "user_1"},
            json={
                "mode": "adaptive_swarm",
                "expected_version": 1,
                "idempotency_key": "demo2-route-recommendation",
            },
        )

    assert response.status_code == 200
    assert response.json()["item"]["selection_source"] == "admission"
    assert response.json()["item"]["override_scope"] is None


async def test_demo2_route_rejects_stale_version_fixed_items_and_other_owners() -> None:
    app = build_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        stale = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/route",
            headers={"X-User-Id": "user_1"},
            json={
                "mode": "adaptive_swarm",
                "expected_version": 99,
                "idempotency_key": "demo2-route-stale",
            },
        )
        fixed = await client.post(
            "/v1/demo2/work-items/weekly_report/route",
            headers={"X-User-Id": "user_1"},
            json={
                "mode": "fixed_workflow",
                "expected_version": 1,
                "idempotency_key": "demo2-route-fixed",
            },
        )
        hidden = await client.get(
            "/v1/demo2/work-items/customer_a_operating_review",
            headers={"X-User-Id": "user_2"},
        )

    assert stale.status_code == 409
    assert fixed.status_code == 409
    assert hidden.status_code == 200
    assert hidden.json()["owner_id"] == "user_2"


async def test_demo2_route_body_rejects_unknown_fields() -> None:
    app = build_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/route",
            headers={"X-User-Id": "user_1"},
            json={
                "mode": "adaptive_swarm",
                "expected_version": 1,
                "idempotency_key": "demo2-route-extra",
                "max_workers": 99,
            },
        )

    assert response.status_code == 422
