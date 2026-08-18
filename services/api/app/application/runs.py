from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from packages.contracts import (
    ActionCandidate,
    ApprovalRecord,
    CapabilityDecision,
    ControlPlan,
    EvidenceRecord,
    PolicyEffect,
    PermitMetadata,
    ProposedActionSpec,
    RiskAssessment,
    TaskArtifactBinding,
    ToolExecutionResult,
)
from packages.authorization import AuthorizationError, AuthorizationService
from packages.authorization.service import tool_arguments
from packages.agent_runtime import AgentWorkflow
from packages.audit import InMemoryAuditLog
from packages.contracts.hashing import canonical_hash
from packages.contracts.models import PanelSpec
from packages.evidence import MockEvidenceResolver
from packages.risk_core import assess_risk, build_control_plan, evaluate_policies
from packages.tool_gateway import GatewayError, ToolGateway
from services.api.app.application.llm import AutoDLActionParser
from services.api.app.application.storage import InMemoryRunStore, RunStore


class RunNotFoundError(LookupError):
    pass


class ActionNotFoundError(LookupError):
    pass


class RunCreateConflictError(RuntimeError):
    pass


class RunSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    trace_id: str
    thread_id: str
    user_id: str
    user_message: str
    creation_idempotency_key: str | None = None
    creation_digest: str | None = None
    trusted_context: dict = Field(default_factory=lambda: {"device": {"managed": True}})
    status: str
    action: ProposedActionSpec
    risk: RiskAssessment
    policy_effects: list[PolicyEffect]
    evidence: dict[str, EvidenceRecord]
    approvals: list[ApprovalRecord] = Field(default_factory=list)
    control_plan: ControlPlan
    permit: PermitMetadata | None = None
    tool_result: ToolExecutionResult | None = None
    created_at: datetime
    updated_at: datetime


class RunService:
    """P0 application service. Persistence is intentionally replaceable by PostgreSQL later."""

    def __init__(
        self,
        parser: AutoDLActionParser,
        policy_version: str,
        evidence_resolver: MockEvidenceResolver | None = None,
        authorization_service: AuthorizationService | None = None,
        tool_gateway: ToolGateway | None = None,
        audit_log: InMemoryAuditLog | None = None,
        run_store: RunStore | None = None,
    ) -> None:
        self.parser = parser
        self.policy_version = policy_version
        self.evidence_resolver = evidence_resolver or MockEvidenceResolver()
        self.authorization_service = authorization_service
        self.tool_gateway = tool_gateway
        self.audit_log = audit_log or InMemoryAuditLog()
        self.run_store = run_store or InMemoryRunStore()
        self._runs: dict[str, RunSnapshot] = {}
        self._action_to_run: dict[str, str] = {}
        self._submitted_evidence: dict[str, dict[str, Any]] = {}
        self._invalidated_actions: set[str] = set()
        self._creation_to_run: dict[tuple[str, str], str] = {}
        self._task_artifact_validator: Callable[
            [TaskArtifactBinding, str], Awaitable[None]
        ] | None = None
        self._lock = asyncio.Lock()
        self.workflow: AgentWorkflow | None = None

    def attach_workflow(self, workflow: AgentWorkflow) -> None:
        self.workflow = workflow

    def attach_task_artifact_validator(
        self,
        validator: Callable[[TaskArtifactBinding, str], Awaitable[None]],
    ) -> None:
        self._task_artifact_validator = validator

    async def restore(self) -> None:
        for stored in await self.run_store.load_all():
            snapshot = RunSnapshot.model_validate(stored.snapshot)
            self._runs[snapshot.run_id] = snapshot
            self._action_to_run[snapshot.action.action_id] = snapshot.run_id
            if snapshot.creation_idempotency_key:
                self._creation_to_run[(snapshot.user_id, snapshot.creation_idempotency_key)] = (
                    snapshot.run_id
                )
            self._submitted_evidence[snapshot.action.action_id] = stored.submitted_evidence

    async def create(
        self, message: str, user_id: str, thread_id: str | None = None
    ) -> RunSnapshot:
        candidate = await self.parser.parse(message)
        return await self.create_from_candidate(
            candidate,
            message=message,
            user_id=user_id,
            thread_id=thread_id,
        )

    async def create_from_candidate(
        self,
        candidate: ActionCandidate,
        message: str,
        user_id: str,
        trusted_context: dict | None = None,
        thread_id: str | None = None,
        task_artifact_binding: TaskArtifactBinding | None = None,
        creation_idempotency_key: str | None = None,
    ) -> RunSnapshot:
        trusted_context = trusted_context or {
            "device": {"managed": True},
            "user": {"id": user_id},
        }
        creation_digest = canonical_hash(
            {
                "candidate": candidate.model_dump(mode="json"),
                "message": message,
                "thread_id": thread_id,
                "task_artifact_binding": (
                    task_artifact_binding.model_dump(mode="json")
                    if task_artifact_binding
                    else None
                ),
            }
        )
        if creation_idempotency_key:
            async with self._lock:
                existing_run_id = self._creation_to_run.get(
                    (user_id, creation_idempotency_key)
                )
                if existing_run_id:
                    existing = self._runs[existing_run_id]
                    if existing.creation_digest != creation_digest:
                        raise RunCreateConflictError("幂等键已用于不同动作")
                    return existing

        now = datetime.now(UTC)
        run_id = f"run_{uuid4().hex}"
        trace_id = f"tr_{uuid4().hex}"
        action_id = f"act_{uuid4().hex}"
        action = ProposedActionSpec(
            **candidate.model_dump(),
            trace_id=trace_id,
            action_id=action_id,
            actor_id=user_id,
            payload_digest=canonical_hash(
                {
                    "candidate": candidate.model_dump(mode="json"),
                    "task_artifact_binding": (
                        task_artifact_binding.model_dump(mode="json")
                        if task_artifact_binding
                        else None
                    ),
                }
            ),
            idempotency_key=f"execute_{action_id}",
            task_artifact_binding=task_artifact_binding,
        )
        risk, effects, evidence, plan = await self._evaluate(
            action, approvals=[], trusted_context=trusted_context
        )
        snapshot = RunSnapshot(
            run_id=run_id,
            trace_id=trace_id,
            thread_id=thread_id or f"thread_{uuid4().hex}",
            user_id=user_id,
            user_message=message,
            creation_idempotency_key=creation_idempotency_key,
            creation_digest=creation_digest,
            trusted_context=trusted_context,
            status=plan.status,
            action=action,
            risk=risk,
            policy_effects=effects,
            evidence=evidence,
            control_plan=plan,
            created_at=now,
            updated_at=now,
        )
        async with self._lock:
            if creation_idempotency_key:
                existing_run_id = self._creation_to_run.get(
                    (user_id, creation_idempotency_key)
                )
                if existing_run_id:
                    existing = self._runs[existing_run_id]
                    if existing.creation_digest != creation_digest:
                        raise RunCreateConflictError("幂等键已用于不同动作")
                    return existing
            self._runs[run_id] = snapshot
            self._action_to_run[action_id] = run_id
            if creation_idempotency_key:
                self._creation_to_run[(user_id, creation_idempotency_key)] = run_id
        await self._persist(snapshot)
        await self._audit(
            snapshot,
            "RUN_CREATED",
            {
                "thread_id": snapshot.thread_id,
                "task_artifact_version_id": (
                    task_artifact_binding.artifact_version_id
                    if task_artifact_binding
                    else None
                ),
            },
        )
        await self._audit(
            snapshot,
            "ACTION_PARSED",
            {
                "action_type": action.action_type,
                "capability": action.capability,
                "target_scope": action.target_scope,
                "payload_digest": action.payload_digest,
            },
        )
        if self.workflow is not None:
            await self.workflow.start(run_id, self._workflow_checkpoint_id(snapshot))
        return self._runs[run_id]

    async def get(self, run_id: str, user_id: str) -> RunSnapshot:
        snapshot = self._runs.get(run_id)
        if snapshot is None or snapshot.user_id != user_id:
            raise RunNotFoundError(run_id)
        return snapshot

    async def submit_evidence(
        self, action_id: str, values: dict[str, str], user_id: str
    ) -> RunSnapshot:
        snapshot = self._by_action(action_id, user_id)
        await self._ensure_task_artifact_current(snapshot)
        if action_id in self._invalidated_actions or "ARTIFACT_CONTENT_CHANGED" in snapshot.control_plan.reason_codes:
            raise ValueError("生成内容已修改，请基于新版本重新提交动作")
        allowed = {
            requirement
            for effect in snapshot.policy_effects
            for requirement in effect.required_evidence
        }
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"未知证据项：{', '.join(sorted(unknown))}")
        self._submitted_evidence.setdefault(action_id, {}).update(values)
        await self._persist(snapshot)
        await self._audit(
            snapshot,
            "EVIDENCE_SUBMITTED",
            {"requirements": sorted(values)},
            actor_id=user_id,
        )
        if self.workflow is not None:
            await self.workflow.resume(
                self._workflow_checkpoint_id(snapshot), "evidence_submitted"
            )
            return self._runs[snapshot.run_id]
        return await self._reevaluate(snapshot)

    async def submit_approval(
        self,
        action_id: str,
        approver_role: str,
        decision: str,
        approver_id: str,
    ) -> RunSnapshot:
        snapshot = self._find_action(action_id)
        await self._ensure_task_artifact_current(snapshot)
        if action_id in self._invalidated_actions or "ARTIFACT_CONTENT_CHANGED" in snapshot.control_plan.reason_codes:
            raise ValueError("生成内容已修改，旧动作不能继续审批")
        allowed_roles = {
            role for effect in snapshot.policy_effects for role in effect.required_approvals
        }
        if approver_role not in allowed_roles:
            raise ValueError("该动作不需要此角色审批")
        approval = ApprovalRecord(
            approval_id=f"approval_{uuid4().hex}",
            action_id=action_id,
            approver_role=approver_role,
            approver_id=approver_id,
            decision=decision,
            created_at=datetime.now(UTC),
        )
        approvals = [a for a in snapshot.approvals if a.approver_role != approver_role]
        approvals.append(approval)
        snapshot = snapshot.model_copy(update={"approvals": approvals})
        async with self._lock:
            self._runs[snapshot.run_id] = snapshot
        await self._persist(snapshot)
        await self._audit(
            snapshot,
            "APPROVAL_RECORDED",
            {"role": approver_role, "decision": decision, "approval_id": approval.approval_id},
            actor_id=approver_id,
        )
        if self.workflow is not None:
            await self.workflow.resume(
                self._workflow_checkpoint_id(snapshot), "approval_submitted"
            )
            return self._runs[snapshot.run_id]
        return await self._reevaluate(snapshot)

    async def authorize_and_execute(self, action_id: str, user_id: str) -> RunSnapshot:
        snapshot = self._by_action(action_id, user_id)
        try:
            await self._ensure_task_artifact_current(snapshot)
        except ValueError as exc:
            raise AuthorizationError(str(exc)) from exc
        if action_id in self._invalidated_actions or "ARTIFACT_CONTENT_CHANGED" in snapshot.control_plan.reason_codes:
            raise AuthorizationError("生成内容已修改，旧 Action 和 Permit 已作废")
        if self.authorization_service is None or self.tool_gateway is None:
            raise RuntimeError("Authorization Service 或 Tool Gateway 未配置")

        if self.workflow is not None:
            await self.workflow.resume(
                self._workflow_checkpoint_id(snapshot), "authorization_requested"
            )
            return self._runs[snapshot.run_id]

        # Non-LangGraph fallback used by isolated unit/integration tests.
        snapshot = await self._reevaluate(snapshot)
        return await self._issue_and_execute(snapshot)

    async def demonstrate_parameter_tamper(self, action_id: str, user_id: str) -> dict:
        snapshot = self._by_action(action_id, user_id)
        if self.authorization_service is None or self.tool_gateway is None:
            raise RuntimeError("Authorization Service 或 Tool Gateway 未配置")
        snapshot = await self._reevaluate(snapshot)
        issued = self.authorization_service.issue(
            snapshot.action, snapshot.control_plan, snapshot.approvals
        )
        changed_arguments = tool_arguments(snapshot.action) | {
            "recipients": ["tampered-recipient@example.com"]
        }
        try:
            await self.tool_gateway.execute(
                capability=snapshot.action.capability,
                arguments=changed_arguments,
                permit_token=issued.token,
                subject=snapshot.user_id,
                action_hash=snapshot.control_plan.action_hash,
            )
        except GatewayError as exc:
            await self._audit(
                snapshot,
                "TAMPER_BLOCKED",
                {"code": exc.code, "changed_field": "recipients"},
            )
            return {
                "blocked": True,
                "code": exc.code,
                "changed_field": "recipients",
                "simulator_executed": False,
            }
        raise RuntimeError("参数篡改未被 Gateway 拦截")

    async def invalidate_action(self, action_id: str, user_id: str) -> RunSnapshot:
        snapshot = self._by_action(action_id, user_id)
        if snapshot.status in {"EXECUTED", "DENIED", "FAILED"}:
            return snapshot
        if action_id in self._invalidated_actions:
            return snapshot
        self._invalidated_actions.add(action_id)
        invalid_plan = snapshot.control_plan.model_copy(
            update={
                "status": "FAILED",
                "panel": PanelSpec(
                    type="error",
                    message="关联生成物已修改，旧动作摘要和审批链已作废。",
                ),
                "reason_codes": [
                    *snapshot.control_plan.reason_codes,
                    "ARTIFACT_CONTENT_CHANGED",
                ],
            }
        )
        updated = snapshot.model_copy(
            update={
                "status": "FAILED",
                "control_plan": invalid_plan,
                "updated_at": datetime.now(UTC),
            }
        )
        async with self._lock:
            self._runs[snapshot.run_id] = updated
        await self._persist(updated)
        await self._audit(
            updated,
            "ACTION_INVALIDATED",
            {"reason": "artifact_content_changed"},
            actor_id=user_id,
        )
        return updated

    async def workflow_state(self, run_id: str, user_id: str) -> dict:
        snapshot = await self.get(run_id, user_id)
        if self.workflow is None:
            return {"values": {"run_id": run_id, "status": snapshot.status}, "next": []}
        return await self.workflow.state(self._workflow_checkpoint_id(snapshot))

    async def audit_history(self, trace_id: str, user_id: str) -> list:
        snapshot = next(
            (
                run
                for run in self._runs.values()
                if run.trace_id == trace_id and run.user_id == user_id
            ),
            None,
        )
        if snapshot is None:
            raise RunNotFoundError(trace_id)
        return await self.audit_log.history(snapshot.run_id)

    async def event_stream(self, run_id: str, user_id: str, after_sequence: int = 0):
        await self.get(run_id, user_id)
        async for event in self.audit_log.stream(run_id, after_sequence):
            yield event

    async def workflow_evaluate(self, run_id: str) -> str:
        snapshot = self._runs[run_id]
        updated = await self._reevaluate(snapshot)
        await self._audit(
            updated,
            "CONTROL_PLAN_UPDATED",
            {
                "status": updated.status,
                "risk_level": updated.risk.risk_level,
                "missing_requirements": updated.control_plan.missing_requirements,
                "required_approvals": updated.control_plan.required_approvals,
            },
        )
        return updated.status

    def workflow_panel(self, run_id: str) -> dict:
        return self._runs[run_id].control_plan.panel.model_dump(mode="json")

    async def workflow_execute(self, run_id: str) -> str:
        snapshot = self._runs[run_id]
        updated = await self._issue_and_execute(snapshot)
        return updated.status

    async def _issue_and_execute(self, snapshot: RunSnapshot) -> RunSnapshot:
        try:
            await self._ensure_task_artifact_current(snapshot)
        except ValueError as exc:
            raise AuthorizationError(str(exc)) from exc
        if self.authorization_service is None or self.tool_gateway is None:
            raise RuntimeError("Authorization Service 或 Tool Gateway 未配置")
        issued = self.authorization_service.issue(
            snapshot.action, snapshot.control_plan, snapshot.approvals
        )
        await self._audit(
            snapshot,
            "PERMIT_ISSUED",
            {
                "permit_id": issued.metadata.permit_id,
                "capability": issued.metadata.capability,
                "expires_at": issued.metadata.expires_at.isoformat(),
            },
        )
        result = await self.tool_gateway.execute(
            capability=snapshot.action.capability,
            arguments=tool_arguments(snapshot.action),
            permit_token=issued.token,
            subject=snapshot.user_id,
            action_hash=snapshot.control_plan.action_hash,
        )
        executed_plan = snapshot.control_plan.model_copy(
            update={
                "status": "EXECUTED",
                "panel": PanelSpec(type="result", message="工具已通过 Simulator 执行。"),
            }
        )
        updated = snapshot.model_copy(
            update={
                "status": "EXECUTED",
                "control_plan": executed_plan,
                "permit": issued.metadata,
                "tool_result": result,
                "updated_at": datetime.now(UTC),
            }
        )
        async with self._lock:
            self._runs[snapshot.run_id] = updated
        await self._persist(updated)
        await self._audit(
            updated,
            "TOOL_EXECUTED",
            {
                "execution_id": result.execution_id,
                "capability": result.capability,
                "simulator": result.simulator,
                "status": result.status,
            },
        )
        return updated

    async def _ensure_task_artifact_current(self, snapshot: RunSnapshot) -> None:
        binding = snapshot.action.task_artifact_binding
        if binding is None or self._task_artifact_validator is None:
            return
        try:
            await self._task_artifact_validator(binding, snapshot.user_id)
        except (LookupError, RuntimeError, ValueError) as exc:
            await self.invalidate_action(snapshot.action.action_id, snapshot.user_id)
            raise ValueError(
                "绑定成果已经变化，旧动作已作废；请从当前成果重新准备"
            ) from exc

    async def _audit(
        self,
        snapshot: RunSnapshot,
        event_type: str,
        payload: dict,
        actor_id: str | None = None,
    ) -> None:
        await self.audit_log.append(
            run_id=snapshot.run_id,
            trace_id=snapshot.trace_id,
            action_id=snapshot.action.action_id,
            actor_id=actor_id or snapshot.user_id,
            event_type=event_type,
            payload=payload,
        )

    def _by_action(self, action_id: str, user_id: str) -> RunSnapshot:
        snapshot = self._find_action(action_id)
        if snapshot.user_id != user_id:
            raise ActionNotFoundError(action_id)
        return snapshot

    def _find_action(self, action_id: str) -> RunSnapshot:
        run_id = self._action_to_run.get(action_id)
        if run_id is None:
            raise ActionNotFoundError(action_id)
        return self._runs[run_id]

    @staticmethod
    def _workflow_checkpoint_id(snapshot: RunSnapshot) -> str:
        # A conversation can own more than one governed run. Keep the real
        # conversation binding on the snapshot while isolating graph state per run.
        return f"{snapshot.thread_id}:{snapshot.run_id}"

    async def _reevaluate(self, snapshot: RunSnapshot) -> RunSnapshot:
        risk, effects, evidence, plan = await self._evaluate(
            snapshot.action, snapshot.approvals, snapshot.trusted_context
        )
        updated = snapshot.model_copy(
            update={
                "risk": risk,
                "policy_effects": effects,
                "evidence": evidence,
                "control_plan": plan,
                "status": plan.status,
                "updated_at": datetime.now(UTC),
            }
        )
        async with self._lock:
            self._runs[snapshot.run_id] = updated
        await self._persist(updated)
        return updated

    async def _persist(self, snapshot: RunSnapshot) -> None:
        await self.run_store.save(
            snapshot.model_dump(mode="json"),
            self._submitted_evidence.get(snapshot.action.action_id, {}),
        )

    async def _evaluate(
        self,
        action: ProposedActionSpec,
        approvals: list[ApprovalRecord],
        trusted_context: dict,
    ) -> tuple[RiskAssessment, list[PolicyEffect], dict[str, EvidenceRecord], ControlPlan]:
        risk = assess_risk(action)
        effects = evaluate_policies(action, risk, trusted_context)
        unresolved_reason_codes: list[str] = []
        if "recipient_identity" in action.missing_slots:
            unresolved_reason_codes.append("RECIPIENT_IDENTITY_UNRESOLVED")
        if any(
            slot.startswith("attachment_data_class:")
            for slot in action.missing_slots
        ):
            unresolved_reason_codes.append("ATTACHMENT_DATA_CLASS_UNRESOLVED")
        if unresolved_reason_codes:
            effects.append(
                PolicyEffect(
                    policy_id="unresolved_action_context_v1",
                    capability_effects={
                        action.capability: CapabilityDecision(verdict="deny")
                    },
                    reason_codes=unresolved_reason_codes,
                )
            )
        requirements = list(
            dict.fromkeys(req for effect in effects for req in effect.required_evidence)
        )
        evidence = await self.evidence_resolver.resolve(
            requirements, action, self._submitted_evidence.get(action.action_id)
        )
        plan = build_control_plan(
            action, risk, effects, evidence, approvals, self.policy_version
        )
        return risk, effects, evidence, plan
