import pytest

from packages.authorization import AuthorizationError, AuthorizationService, PermitKeyPair
from packages.authorization.service import tool_arguments
from packages.contracts import CapabilityDecision, ControlPlan
from packages.contracts.hashing import canonical_hash
from packages.contracts.models import PanelSpec
from packages.tool_gateway import GatewayError, ToolGateway
from tests.unit.test_risk import make_action


def ready_plan():
    action = make_action(data_classes=[])
    plan = ControlPlan(
        action_id=action.action_id,
        action_hash=canonical_hash(action),
        risk_level="L2",
        status="READY_TO_AUTHORIZE",
        capabilities={"email.send": CapabilityDecision(verdict="allow")},
        panel=PanelSpec(type="preview", message="ready"),
        policy_version="test-v1",
    )
    return action, plan


async def test_valid_permit_executes_once_and_replay_is_rejected() -> None:
    keys = PermitKeyPair.generate()
    authorization = AuthorizationService(keys)
    gateway = ToolGateway(keys.public_key, "test-v1")
    action, plan = ready_plan()
    permit = authorization.issue(action, plan, [])

    result = await gateway.execute(
        action.capability,
        tool_arguments(action),
        permit.token,
        action.actor_id,
        plan.action_hash,
    )
    assert result.status == "succeeded"
    assert result.output["simulated"] is True

    with pytest.raises(GatewayError, match="已经使用") as caught:
        await gateway.execute(
            action.capability,
            tool_arguments(action),
            permit.token,
            action.actor_id,
            plan.action_hash,
        )
    assert caught.value.code == "PERMIT_REPLAYED"


async def test_parameter_change_invalidates_permit() -> None:
    keys = PermitKeyPair.generate()
    authorization = AuthorizationService(keys)
    gateway = ToolGateway(keys.public_key, "test-v1")
    action, plan = ready_plan()
    permit = authorization.issue(action, plan, [])
    changed = tool_arguments(action) | {"recipients": ["attacker@example.com"]}

    with pytest.raises(GatewayError) as caught:
        await gateway.execute(
            action.capability, changed, permit.token, action.actor_id, plan.action_hash
        )
    assert caught.value.code == "PARAMETER_HASH_MISMATCH"


async def test_expired_permit_is_rejected() -> None:
    keys = PermitKeyPair.generate()
    authorization = AuthorizationService(keys, ttl_seconds=-1)
    gateway = ToolGateway(keys.public_key, "test-v1")
    action, plan = ready_plan()
    permit = authorization.issue(action, plan, [])

    with pytest.raises(GatewayError) as caught:
        await gateway.execute(
            action.capability,
            tool_arguments(action),
            permit.token,
            action.actor_id,
            plan.action_hash,
        )
    assert caught.value.code == "PERMIT_EXPIRED"


async def test_missing_or_tampered_permit_is_rejected() -> None:
    keys = PermitKeyPair.generate()
    gateway = ToolGateway(keys.public_key, "test-v1")
    action, plan = ready_plan()

    for token in ("", "not-a-jwt", "ey.fake.signature"):
        with pytest.raises(GatewayError) as caught:
            await gateway.execute(
                action.capability,
                tool_arguments(action),
                token,
                action.actor_id,
                plan.action_hash,
            )
        assert caught.value.code == "PERMIT_INVALID"


def test_non_ready_plan_cannot_receive_permit() -> None:
    keys = PermitKeyPair.generate()
    action, plan = ready_plan()
    waiting = plan.model_copy(
        update={
            "status": "WAITING_APPROVAL",
            "panel": {"type": "approval", "message": "waiting"},
        }
    )

    with pytest.raises(AuthorizationError):
        AuthorizationService(keys).issue(action, waiting, [])
