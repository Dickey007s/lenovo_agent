from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from packages.contracts import (
    ActionCandidate,
    ActionExecutionReceipt,
    ActionImpactPreview,
    ApprovalRecord,
    CapabilityDecision,
    ControlPlan,
    EvidenceRecord,
    ImpactItem,
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


RunStatus = Literal[
    "DENIED",
    "WAITING_EVIDENCE",
    "WAITING_APPROVAL",
    "READY_TO_AUTHORIZE",
    "AUTHORIZED",
    "EXECUTED",
    "FAILED",
]


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
    status: RunStatus
    action: ProposedActionSpec
    risk: RiskAssessment
    policy_effects: list[PolicyEffect]
    evidence: dict[str, EvidenceRecord]
    approvals: list[ApprovalRecord] = Field(default_factory=list)
    control_plan: ControlPlan
    impact_preview: ActionImpactPreview | None = None
    permit: PermitMetadata | None = None
    tool_result: ToolExecutionResult | None = None
    execution_receipt: ActionExecutionReceipt | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_action_artifacts(self) -> "RunSnapshot":
        if self.status != self.control_plan.status:
            raise ValueError("run status does not match control plan status")
        expected_hash = self.control_plan.action_hash
        if self.impact_preview is not None:
            if self.impact_preview.action_id != self.action.action_id:
                raise ValueError("impact preview action_id does not match action")
            if self.impact_preview.action_hash != expected_hash:
                raise ValueError("impact preview action_hash does not match control plan")
        if self.execution_receipt is not None:
            if self.status not in {"EXECUTED", "DENIED", "FAILED"}:
                raise ValueError("execution receipt requires a terminal run")
            if self.execution_receipt.action_id != self.action.action_id:
                raise ValueError("execution receipt action_id does not match action")
            if self.execution_receipt.action_hash != expected_hash:
                raise ValueError("execution receipt action_hash does not match control plan")
            expected_status = {
                "EXECUTED": "succeeded",
                "DENIED": "denied",
            }.get(self.status)
            if expected_status is not None and self.execution_receipt.status != expected_status:
                raise ValueError("execution receipt status does not match run status")
            if self.status == "FAILED" and self.execution_receipt.status not in {"failed", "unknown"}:
                raise ValueError("failed run requires failed or unknown receipt")
            if self.impact_preview is not None:
                preview_items = {
                    (item.item_id, item.change_kind) for item in self.impact_preview.items
                }
                receipt_items = {
                    (item.item_id, item.change_kind) for item in self.execution_receipt.items
                }
                if preview_items != receipt_items:
                    raise ValueError("execution receipt impact items do not match preview")
        return self


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
        self._execution_locks: dict[str, asyncio.Lock] = {}
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
        if task_artifact_binding is not None:
            if self._task_artifact_validator is None:
                raise RunCreateConflictError(
                    "Task Artifact 绑定校验器未配置，不能创建动作"
                )
            try:
                await self._task_artifact_validator(task_artifact_binding, user_id)
            except (LookupError, RuntimeError, ValueError) as exc:
                raise RunCreateConflictError(
                    "绑定成果已变化或不可用，不能创建动作"
                ) from exc
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
            impact_preview=self._build_impact_preview(action, plan, now),
            created_at=now,
            updated_at=now,
        )
        if plan.status == "DENIED":
            snapshot = snapshot.model_copy(
                update={
                    "execution_receipt": self._build_execution_receipt(
                        snapshot,
                        status="denied",
                        observed_at=now,
                        external_side_effect="none",
                        error_code=(plan.reason_codes[0] if plan.reason_codes else "POLICY_DENIED"),
                        failure_stage="policy",
                    )
                }
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
        self._require_non_terminal(snapshot)
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
        snapshot = self._by_action(action_id, approver_id)
        self._require_non_terminal(snapshot)
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
        lock = self._execution_locks.setdefault(action_id, asyncio.Lock())
        async with lock:
            snapshot = self._by_action(action_id, user_id)
            # A completed execution is the durable result of this command. Do
            # not issue a fresh permit merely because the client retried.
            if snapshot.status == "EXECUTED":
                return snapshot
            if snapshot.status in {"DENIED", "FAILED"}:
                if "ARTIFACT_CONTENT_CHANGED" in snapshot.control_plan.reason_codes:
                    raise AuthorizationError("生成内容已修改，旧 Action 和 Permit 已作废")
                raise AuthorizationError("ControlPlan 尚未达到 READY_TO_AUTHORIZE")
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
            if snapshot.status != "READY_TO_AUTHORIZE":
                raise AuthorizationError("ControlPlan 尚未达到 READY_TO_AUTHORIZE")
            return await self._issue_and_execute(snapshot)

    async def demonstrate_parameter_tamper(self, action_id: str, user_id: str) -> dict:
        snapshot = self._by_action(action_id, user_id)
        self._require_non_terminal(snapshot)
        if self.authorization_service is None or self.tool_gateway is None:
            raise RuntimeError("Authorization Service 或 Tool Gateway 未配置")
        snapshot = await self._reevaluate(snapshot)
        if snapshot.status != "READY_TO_AUTHORIZE":
            raise AuthorizationError("ControlPlan 尚未达到 READY_TO_AUTHORIZE")
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
                "execution_receipt": self._build_execution_receipt(
                    snapshot,
                    status="failed",
                    observed_at=datetime.now(UTC),
                    external_side_effect="none",
                    error_code="ARTIFACT_CONTENT_CHANGED",
                    failure_stage="binding",
                ),
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
        try:
            result = await self.tool_gateway.execute(
                capability=snapshot.action.capability,
                arguments=tool_arguments(snapshot.action),
                permit_token=issued.token,
                subject=snapshot.user_id,
                action_hash=snapshot.control_plan.action_hash,
            )
        except GatewayError as exc:
            await self._record_execution_failure(
                snapshot,
                issued.metadata,
                error_code=exc.code,
                failure_stage="gateway",
                receipt_status="failed",
                external_side_effect="none",
                panel_message="Gateway 在进入 Simulator 前拒绝了动作。",
            )
            raise
        except Exception as exc:
            # A simulator timeout/error does not prove that no side effect
            # occurred. Persist an unknown outcome before returning a safe error.
            await self._record_execution_failure(
                snapshot,
                issued.metadata,
                error_code="SIMULATOR_EXECUTION_UNKNOWN",
                failure_stage="simulator",
                receipt_status="unknown",
                external_side_effect="unknown",
                panel_message="Simulator 执行结果未知，请读取服务端回执后再决定是否重试。",
            )
            raise GatewayError(
                "SIMULATOR_EXECUTION_UNKNOWN",
                "Simulator 执行结果未知，请先读取回执再决定是否重试",
            ) from exc
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
                "execution_receipt": self._build_execution_receipt(
                    snapshot,
                    status="succeeded",
                    observed_at=result.executed_at,
                    result=result,
                    permit_id=issued.metadata.permit_id,
                    external_side_effect="simulator_only",
                ),
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
        if binding is None:
            return
        if self._task_artifact_validator is None:
            await self.invalidate_action(snapshot.action.action_id, snapshot.user_id)
            raise ValueError("Task Artifact 绑定校验器未配置，旧动作不能继续")
        try:
            await self._task_artifact_validator(binding, snapshot.user_id)
        except (LookupError, RuntimeError, ValueError) as exc:
            await self.invalidate_action(snapshot.action.action_id, snapshot.user_id)
            raise ValueError(
                "绑定成果已经变化，旧动作已作废；请从当前成果重新准备"
            ) from exc

    async def _record_execution_failure(
        self,
        snapshot: RunSnapshot,
        permit: PermitMetadata,
        *,
        error_code: str,
        failure_stage: Literal["binding", "policy", "authorization", "gateway", "simulator"],
        receipt_status: Literal["failed", "unknown"],
        external_side_effect: Literal["none", "simulator_only", "external", "unknown"],
        panel_message: str,
    ) -> RunSnapshot:
        failed_plan = snapshot.control_plan.model_copy(
            update={
                "status": "FAILED",
                "panel": PanelSpec(
                    type="error",
                    message=panel_message,
                ),
                "reason_codes": [
                    *snapshot.control_plan.reason_codes,
                    "ACTION_EXECUTION_FAILED",
                ],
            }
        )
        observed_at = datetime.now(UTC)
        updated = snapshot.model_copy(
            update={
                "status": "FAILED",
                "control_plan": failed_plan,
                "permit": permit,
                "execution_receipt": self._build_execution_receipt(
                    snapshot,
                    status=receipt_status,
                    observed_at=observed_at,
                    permit_id=permit.permit_id,
                    external_side_effect=external_side_effect,
                    error_code=error_code,
                    failure_stage=failure_stage,
                ),
                "updated_at": observed_at,
            }
        )
        async with self._lock:
            self._runs[snapshot.run_id] = updated
        await self._persist(updated)
        await self._audit(
            updated,
            "TOOL_FAILED",
            {
                "permit_id": permit.permit_id,
                "error_code": error_code,
                "failure_stage": failure_stage,
                "external_side_effect": external_side_effect,
            },
        )
        return updated

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

    @staticmethod
    def _impact_items(
        action: ProposedActionSpec,
        *,
        actual: bool = False,
        execution_id: str | None = None,
        unknown: bool = False,
    ) -> list[ImpactItem]:
        executor_label = {
            "email.send": "演示邮件工具",
            "task.create": "演示任务工具",
            "calendar.invite": "演示日历工具",
            "crm.opportunity.update": "演示 CRM 工具",
            "expense.request_evidence": "演示报销工具",
        }.get(action.capability, "受控演示工具")
        connector_label = {
            "email.send": "真实邮箱未连接",
            "calendar.invite": "真实日历未连接",
            "crm.opportunity.update": "真实 CRM 未连接",
            "task.create": "真实项目系统未连接",
            "expense.request_evidence": "真实 OA 未连接",
        }.get(action.capability, "真实外部系统未连接")
        action_label = {
            "email.send": "发送外部邮件",
            "task.create": "创建内部任务",
            "calendar.invite": "创建日历邀请",
            "crm.opportunity.update": "更新 CRM 机会",
            "expense.request_evidence": "请求报销凭证",
        }.get(action.capability, "受控办公动作")
        if action.task_artifact_binding is not None:
            preserved_label = "已核对客户回复成果"
            preserved_before = "当前已核对客户回复成果"
        else:
            preserved_label = "动作范围外内容"
            preserved_before = "当前动作范围外的业务内容"
        if unknown:
            change_after = "执行结果未知，必须先对账再重试"
        elif actual and execution_id:
            change_after = "演示工具已接受本次受控动作"
        elif actual:
            change_after = "未执行"
        else:
            change_after = f"确认后交给{executor_label}"
        return [
            ImpactItem(
                item_id="target-change",
                change_kind="will_change",
                label=action_label,
                before="尚未执行",
                after=change_after,
            ),
            ImpactItem(
                item_id="binding-recheck",
                change_kind="will_recheck",
                label="执行前治理核对",
                before="尚未核对",
                after="成果版本、目标身份、可信依据、策略约束与确认记录",
            ),
            ImpactItem(
                item_id="task-preserved",
                change_kind="unchanged",
                label=preserved_label,
                before=preserved_before,
                after="保持不变",
            ),
            ImpactItem(
                item_id="real-connector-not-called",
                change_kind="no_external_action",
                label=connector_label,
                before="未调用",
                after="不会写入真实外部系统",
            ),
        ]

    @classmethod
    def _build_impact_preview(
        cls,
        action: ProposedActionSpec,
        plan: ControlPlan,
        generated_at: datetime,
    ) -> ActionImpactPreview:
        executor = {
            "email.send": "email_simulator",
            "task.create": "office_action_simulator",
            "calendar.invite": "office_action_simulator",
            "crm.opportunity.update": "office_action_simulator",
            "expense.request_evidence": "office_action_simulator",
        }.get(action.capability)
        return ActionImpactPreview(
            preview_id=f"preview_{plan.action_hash[7:31]}",
            action_id=action.action_id,
            action_hash=plan.action_hash,
            policy_version=plan.policy_version,
            items=cls._impact_items(action),
            executor=executor,
            external_side_effect="none",
            generated_at=generated_at,
            task_artifact_binding=action.task_artifact_binding,
        )

    @classmethod
    def _build_execution_receipt(
        cls,
        snapshot: RunSnapshot,
        *,
        status: Literal["succeeded", "denied", "failed", "unknown"],
        observed_at: datetime,
        result: ToolExecutionResult | None = None,
        permit_id: str | None = None,
        external_side_effect: Literal["none", "simulator_only", "external", "unknown"],
        error_code: str | None = None,
        failure_stage: Literal["binding", "policy", "authorization", "gateway", "simulator"] | None = None,
        retryable: bool = False,
    ) -> ActionExecutionReceipt:
        unknown = status == "unknown"
        return ActionExecutionReceipt(
            receipt_id=f"receipt_{canonical_hash({'action_id': snapshot.action.action_id, 'status': status, 'execution_id': result.execution_id if result else None, 'error_code': error_code})[7:31]}",
            action_id=snapshot.action.action_id,
            action_hash=snapshot.control_plan.action_hash,
            status=status,
            items=cls._impact_items(
                snapshot.action,
                actual=True,
                execution_id=result.execution_id if result else None,
                unknown=unknown,
            ),
            execution_id=result.execution_id if result else None,
            permit_id=permit_id,
            simulator=result.simulator if result else None,
            external_side_effect=external_side_effect,
            error_code=error_code,
            failure_stage=failure_stage,
            retryable=retryable,
            observed_at=observed_at,
        )

    @staticmethod
    def _require_non_terminal(snapshot: RunSnapshot) -> None:
        if snapshot.status in {"EXECUTED", "DENIED", "FAILED"}:
            raise ValueError(f"动作已进入终态 {snapshot.status}，不能继续修改")

    async def _reevaluate(self, snapshot: RunSnapshot) -> RunSnapshot:
        risk, effects, evidence, plan = await self._evaluate(
            snapshot.action, snapshot.approvals, snapshot.trusted_context
        )
        now = datetime.now(UTC)
        preview = self._build_impact_preview(snapshot.action, plan, now)
        updated = snapshot.model_copy(
            update={
                "risk": risk,
                "policy_effects": effects,
                "evidence": evidence,
                "control_plan": plan,
                "status": plan.status,
                "impact_preview": preview,
                "execution_receipt": None,
                "updated_at": now,
            }
        )
        if plan.status == "DENIED":
            updated = updated.model_copy(
                update={
                    "execution_receipt": self._build_execution_receipt(
                        updated,
                        status="denied",
                        observed_at=now,
                        external_side_effect="none",
                        error_code=(plan.reason_codes[0] if plan.reason_codes else "POLICY_DENIED"),
                        failure_stage="policy",
                    )
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
