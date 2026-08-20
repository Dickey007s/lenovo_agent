import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from packages.contracts import WorkItemSnapshot
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
    assert all(
        profile["impact_preview"] is not None
        for item in payload["items"]
        for profile in item["route_profiles"]
    )
    customer_profiles = payload["items"][0]["route_profiles"]
    assert {profile["mode"] for profile in customer_profiles} == {
        "single_agent",
        "fixed_workflow",
        "adaptive_swarm",
    }
    assert all(
        profile["impact_preview"]["execution_status_after"] == "not_started"
        and any(
            change["change_kind"] == "no_external_action"
            for change in profile["impact_preview"]["changes"]
        )
        for profile in customer_profiles
    )
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
    receipt = first.json()["item"]["selection_receipt"]
    assert receipt["receipt_id"].startswith("route-receipt:")
    assert receipt["from_cockpit_version"] == 1
    assert receipt["to_cockpit_version"] == 2
    assert receipt["from_item_version"] == 1
    assert receipt["to_item_version"] == 2
    assert receipt["selected_mode"] == "single_agent"
    assert receipt["selection_source"] == "user_override"
    assert receipt["override_scope"] == "this_run"
    assert receipt["execution_status_before"] == "not_started"
    assert receipt["execution_status_after"] == "not_started"
    assert receipt["external_side_effect"] == "none"
    assert any(change["aspect"] == "work_allocation" for change in receipt["changes"])
    assert any(change["aspect"] == "external_action" for change in receipt["changes"])
    assert different.status_code == 409
    assert cockpit.status_code == 200
    assert cockpit.json()["version"] == 2
    selected = cockpit.json()["items"][0]
    assert selected["selected_mode"] == "single_agent"
    assert selected["version"] == 2
    assert selected["execution_status"] == "not_started"
    assert selected["selection_receipt"] == receipt
    assert selected["selection_receipts"] == [receipt]
    legacy_payload = dict(selected)
    legacy_payload.pop("selection_receipts")
    legacy = WorkItemSnapshot.model_validate(legacy_payload)
    assert legacy.selection_receipts == [legacy.selection_receipt]


async def test_demo2_second_route_selection_records_actual_before_and_history() -> None:
    app = build_test_app()
    headers = {"X-User-Id": "user_1"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/route",
            headers=headers,
            json={
                "mode": "single_agent",
                "expected_version": 1,
                "idempotency_key": "demo2-route-first",
            },
        )
        second = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/route",
            headers=headers,
            json={
                "mode": "fixed_workflow",
                "expected_version": 2,
                "idempotency_key": "demo2-route-second",
            },
        )
        repeated = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/route",
            headers=headers,
            json={
                "mode": "fixed_workflow",
                "expected_version": 3,
                "idempotency_key": "demo2-route-same-mode",
            },
        )
        cockpit = await client.get("/v1/demo2/cockpit", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    item = second.json()["item"]
    assert item["version"] == 3
    assert item["selected_mode"] == "fixed_workflow"
    route_change = next(
        change
        for change in item["selection_receipt"]["changes"]
        if change["aspect"] == "route_decision"
    )
    assert route_change["before"] == "已记录为单 Agent"
    assert route_change["after"] == "已记录为固定流程"
    assert len(item["selection_receipts"]) == 2
    assert [receipt["selected_mode"] for receipt in item["selection_receipts"]] == [
        "single_agent",
        "fixed_workflow",
    ]
    assert repeated.status_code == 409
    assert cockpit.json()["version"] == 3
    assert cockpit.json()["items"][0]["version"] == 3

    invalid_history = dict(item)
    invalid_history["selection_receipts"] = list(reversed(item["selection_receipts"]))
    with pytest.raises(ValidationError):
        WorkItemSnapshot.model_validate(invalid_history)


@pytest.mark.parametrize("missing", ["profile", "preview"])
async def test_demo2_route_fails_closed_when_route_facts_are_missing(missing: str) -> None:
    app = build_test_app()
    service = app.state.demo2_cockpit_service
    cockpit = await service.get_cockpit("user_1")
    item = cockpit.items[0]
    profiles = list(item.route_profiles)
    if missing == "profile":
        profiles = [profile for profile in profiles if profile.mode != "single_agent"]
    else:
        profiles = [
            profile.model_copy(update={"impact_preview": None}) if profile.mode == "single_agent" else profile
            for profile in profiles
        ]
    cockpit.items[0] = item.model_copy(update={"route_profiles": profiles})
    service._cockpits["user_1"] = cockpit

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/demo2/work-items/customer_a_operating_review/route",
            headers={"X-User-Id": "user_1"},
            json={
                "mode": "single_agent",
                "expected_version": 1,
                "idempotency_key": f"demo2-route-missing-{missing}",
            },
        )
        after = await client.get("/v1/demo2/cockpit", headers={"X-User-Id": "user_1"})

    assert response.status_code == 409
    assert after.json()["version"] == 1
    assert after.json()["items"][0]["version"] == 1


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
    assert response.json()["item"]["selection_receipt"]["selection_source"] == "admission"
    assert response.json()["item"]["selection_receipt"]["override_scope"] is None


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
    assert hidden.json()["selection_receipt"] is None
    assert hidden.json()["selection_receipts"] == []


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
