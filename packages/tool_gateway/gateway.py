from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from packages.authorization.service import hash_tool_parameters
from packages.contracts import ToolExecutionResult
from simulators import EmailSimulator, OfficeActionSimulator


class GatewayError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ToolGateway:
    def __init__(self, public_key: Ed25519PublicKey, active_policy_version: str) -> None:
        self.public_key = public_key
        self.active_policy_version = active_policy_version
        self._used_permits: set[str] = set()
        self._email = EmailSimulator()
        self._office = OfficeActionSimulator()

    async def execute(
        self,
        capability: str,
        arguments: dict,
        permit_token: str,
        subject: str,
        action_hash: str,
    ) -> ToolExecutionResult:
        try:
            claims = jwt.decode(
                permit_token,
                self.public_key,
                algorithms=["EdDSA"],
                options={"require": ["exp", "iat", "jti", "sub"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise GatewayError("PERMIT_EXPIRED", "执行许可已过期") from exc
        except jwt.InvalidTokenError as exc:
            raise GatewayError("PERMIT_INVALID", "执行许可签名或声明无效") from exc

        self._require_equal("SUBJECT_MISMATCH", claims["sub"], subject)
        self._require_equal("CAPABILITY_MISMATCH", claims["capability"], capability)
        self._require_equal("ACTION_HASH_MISMATCH", claims["action_hash"], action_hash)
        self._require_equal(
            "PARAMETER_HASH_MISMATCH",
            claims["parameter_hashes"],
            hash_tool_parameters(arguments),
        )
        self._require_equal(
            "POLICY_VERSION_STALE", claims["policy_version"], self.active_policy_version
        )

        permit_id = claims["jti"]
        idempotency_key = claims["idempotency_key"]
        if permit_id in self._used_permits:
            raise GatewayError("PERMIT_REPLAYED", "执行许可已经使用")
        if claims.get("max_uses") != 1:
            raise GatewayError("PERMIT_INVALID", "P0 只接受单次许可")

        if capability == "email.send":
            simulator = self._email.name
            output = await self._email.send(arguments)
        elif capability in {
            "task.create",
            "calendar.invite",
            "crm.opportunity.update",
            "expense.request_evidence",
        }:
            simulator = self._office.name
            output = await self._office.execute(capability, arguments)
        else:
            raise GatewayError("CAPABILITY_NOT_REGISTERED", "未注册对应 Simulator")
        result = ToolExecutionResult(
            execution_id=f"exec_{uuid4().hex}",
            capability=capability,
            status="succeeded",
            simulator=simulator,
            idempotency_key=idempotency_key,
            output=output,
            executed_at=datetime.now(UTC),
        )
        self._used_permits.add(permit_id)
        return result

    @staticmethod
    def _require_equal(code: str, actual: object, expected: object) -> None:
        if actual != expected:
            raise GatewayError(code, code)
