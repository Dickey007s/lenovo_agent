import pytest
from pydantic import ValidationError

from packages.contracts import RouteSelectionRequest


def test_route_selection_request_is_strict_and_bounded() -> None:
    request = RouteSelectionRequest(
        mode="adaptive_swarm",
        expected_version=1,
        idempotency_key="demo2-route-001",
    )
    assert request.scope == "this_run"

    with pytest.raises(ValidationError):
        RouteSelectionRequest(
            mode="adaptive_swarm",
            expected_version=1,
            idempotency_key="demo2-route-001",
            worker_count=5,
        )

    with pytest.raises(ValidationError):
        RouteSelectionRequest(
            mode="unknown",
            expected_version=1,
            idempotency_key="demo2-route-001",
        )
