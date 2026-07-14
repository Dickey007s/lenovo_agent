from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from packages.contracts import ApprovalRecord, ControlPlan, PermitMetadata, ProposedActionSpec
from packages.contracts.hashing import canonical_hash


class AuthorizationError(RuntimeError):
    code = "AUTHORIZATION_DENIED"


@dataclass(frozen=True)
class PermitKeyPair:
    private_key: Ed25519PrivateKey
    public_key: Ed25519PublicKey

    @classmethod
    def generate(cls) -> "PermitKeyPair":
        private_key = Ed25519PrivateKey.generate()
        return cls(private_key=private_key, public_key=private_key.public_key())

    @classmethod
    def from_pem_files(cls, private_path: str, public_path: str) -> "PermitKeyPair":
        private_data = Path(private_path).read_bytes()
        public_data = Path(public_path).read_bytes()
        private_key = serialization.load_pem_private_key(private_data, password=None)
        public_key = serialization.load_pem_public_key(public_data)
        if not isinstance(private_key, Ed25519PrivateKey) or not isinstance(
            public_key, Ed25519PublicKey
        ):
            raise TypeError("Permit keys must be Ed25519 keys")
        return cls(private_key=private_key, public_key=public_key)


@dataclass(frozen=True)
class IssuedPermit:
    token: str
    metadata: PermitMetadata


def tool_arguments(action: ProposedActionSpec) -> dict:
    return {
        "recipients": action.recipients,
        "resources": action.resources,
        "source_refs": action.source_refs,
        "action_type": action.action_type,
        "parameters": action.parameters,
    }


def hash_tool_parameters(arguments: dict) -> dict[str, str]:
    return {name: canonical_hash({name: value}) for name, value in sorted(arguments.items())}


class AuthorizationService:
    def __init__(self, key_pair: PermitKeyPair, ttl_seconds: int = 300) -> None:
        self.key_pair = key_pair
        self.ttl_seconds = ttl_seconds

    def issue(
        self,
        action: ProposedActionSpec,
        plan: ControlPlan,
        approvals: list[ApprovalRecord],
    ) -> IssuedPermit:
        if plan.status != "READY_TO_AUTHORIZE":
            raise AuthorizationError("ControlPlan 尚未达到 READY_TO_AUTHORIZE")
        if canonical_hash(action) != plan.action_hash:
            raise AuthorizationError("ACTION_HASH_MISMATCH")
        decision = plan.capabilities.get(action.capability)
        if decision is None or decision.verdict != "allow":
            raise AuthorizationError("目标 capability 未被允许")

        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self.ttl_seconds)
        permit_id = f"permit_{uuid4().hex}"
        claims = {
            "sub": action.actor_id,
            "capability": action.capability,
            "action_hash": plan.action_hash,
            "parameter_hashes": hash_tool_parameters(tool_arguments(action)),
            "policy_version": plan.policy_version,
            "approval_ids": [a.approval_id for a in approvals if a.decision == "approved"],
            "max_uses": 1,
            "iat": now,
            "exp": expires_at,
            "jti": permit_id,
            "idempotency_key": action.idempotency_key,
        }
        token = jwt.encode(claims, self.key_pair.private_key, algorithm="EdDSA")
        return IssuedPermit(
            token=token,
            metadata=PermitMetadata(
                permit_id=permit_id,
                subject=action.actor_id,
                capability=action.capability,
                action_hash=plan.action_hash,
                policy_version=plan.policy_version,
                max_uses=1,
                expires_at=expires_at,
                idempotency_key=action.idempotency_key,
            ),
        )
