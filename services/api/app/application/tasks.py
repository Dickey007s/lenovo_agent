from __future__ import annotations

import asyncio
import hashlib
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Any
from uuid import uuid4

from packages.contracts import (
    ArtifactVersion,
    BranchSnapshot,
    ConflictRecord,
    ConflictResolutionOption,
    ControlEvent,
    DeliverableSpec,
    ImpactChange,
    ImpactReceipt,
    ResolutionImpact,
    TaskBudget,
    TaskBudgetSnapshot,
    TaskCommit,
    TaskContract,
    TaskContractDraft,
    TaskControlCommand,
    TaskEvent,
    TaskEventType,
    TaskError,
    TaskArtifactBinding,
    TaskSnapshot,
    TaskStageRecord,
    TaskStage,
    VerificationCheck,
    VerificationReport,
)
from packages.contracts.hashing import canonical_hash
from services.api.app.application.task_storage import (
    StoredTask,
    TaskStore,
    TaskStoreConflictError,
)
from services.api.app.application.task_stage_agent import (
    DeterministicTaskStageAgent,
    TaskStageAct,
    TaskStageActRequest,
    TaskStageAgent,
    TaskStageContract,
    TaskStageDeliverable,
    TaskStagePlan,
    TaskStagePlanRequest,
    TaskStageSourceAlias,
    TaskStageTrustedFact,
)


runtime_logger = logging.getLogger("uvicorn.error")


def _task_stage_model_attempted(stage_agent: Any) -> bool:
    return bool(getattr(stage_agent, "base_url", "") and getattr(stage_agent, "api_key", ""))


def _log_task_stage(stage: str, stage_agent: Any, elapsed_seconds: float, origin: str) -> None:
    runtime_logger.info(
        "task_stage_processing stage=%s model_called=%s accepted_model_output=%s model=%s elapsed_ms=%d origin=%s",
        stage,
        _task_stage_model_attempted(stage_agent),
        origin == "model",
        getattr(stage_agent, "model", "none"),
        max(0, round(elapsed_seconds * 1000)),
        origin,
    )


class TaskNotFoundError(LookupError):
    pass


class TaskCreateConflictError(RuntimeError):
    pass


class TaskMutationConflictError(RuntimeError):
    pass


class TaskTransitionError(TaskMutationConflictError):
    pass


@dataclass(frozen=True)
class TaskEventSpec:
    event_type: TaskEventType
    payload: dict[str, Any]
    branch_id: str | None = None
    artifact_version_id: str | None = None
    control_event_id: str | None = None
    idempotent: bool = False


def demo1_contract_draft() -> TaskContractDraft:
    return TaskContractDraft(
        title="客户 A 经营汇报",
        objective="形成带来源、版本和验证记录的经营分析、风险页和客户回复草稿。",
        source_scope=[
            "fixture:mail/customer-a:2026-06-15",
            "fixture:crm/customer-a:official-revenue-v3",
            "fixture:forecast/customer-a:revenue-v2",
            "fixture:project/customer-a:weekly-v5",
        ],
        allowed_capabilities=[
            "mail.search",
            "crm.customer.read",
            "document.draft",
            "email.draft",
        ],
        deliverables=[
            DeliverableSpec(
                deliverable_id="operating-analysis",
                title="经营分析",
                kind="analysis",
                completion_criteria=[
                    "关键经营事实均绑定允许来源。",
                    "收入使用正式口径并说明预测差异。",
                ],
            ),
            DeliverableSpec(
                deliverable_id="risk-brief",
                title="风险页",
                kind="risk_brief",
                completion_criteria=[
                    "风险项绑定项目来源。",
                    "未解决冲突不得进入最终版本。",
                ],
            ),
            DeliverableSpec(
                deliverable_id="reply-draft",
                title="客户回复草稿",
                kind="reply_draft",
                completion_criteria=[
                    "正文与已验证经营事实一致。",
                    "草稿不触发真实外部发送。",
                ],
            ),
        ],
        completion_criteria=[
            "三个必需交付物均通过验证。",
            "不存在未解决冲突。",
            "最终提交包含工件版本、验证报告和 state hash。",
        ],
        budget=TaskBudget(max_steps=12, max_tool_calls=30, max_runtime_seconds=3_600),
        deadline_at=None,
    )


class TaskService:
    def __init__(
        self,
        store: TaskStore,
        poll_interval_seconds: float = 0.5,
        stage_agent: TaskStageAgent | None = None,
    ) -> None:
        self.store = store
        self.poll_interval_seconds = poll_interval_seconds
        # Library callers and tests must remain offline and deterministic. The
        # application entrypoint may explicitly inject the model-backed agent.
        self.stage_agent = stage_agent or DeterministicTaskStageAgent()
        # Prevent duplicate paid model calls for concurrent retries carrying
        # the same mutation key. Store CAS remains the cross-process guard.
        self._advance_locks: dict[tuple[str, str], asyncio.Lock] = {}

    async def create(
        self,
        draft: TaskContractDraft,
        owner_id: str,
        *,
        idempotency_key: str | None = None,
    ) -> TaskSnapshot:
        now = datetime.now(UTC)
        task_id = self._task_id(owner_id, idempotency_key)
        trace_id = f"task_trace_{uuid4().hex}"
        contract = TaskContract(
            **draft.model_dump(),
            task_id=task_id,
            owner_id=owner_id,
            created_at=now,
        )
        branches = [
            BranchSnapshot(
                branch_id=f"branch_{uuid4().hex}",
                task_id=task_id,
                title=deliverable.title,
                objective=f"完成并验证交付物：{deliverable.title}",
                deliverable_ids=[deliverable.deliverable_id],
                created_at=now,
                updated_at=now,
            )
            for deliverable in contract.deliverables
        ]
        snapshot = TaskSnapshot(
            task_id=task_id,
            trace_id=trace_id,
            owner_id=owner_id,
            contract=contract,
            branches=branches,
            last_event_sequence=1,
            created_at=now,
            updated_at=now,
        )
        event = TaskEvent(
            sequence=1,
            event_id=f"task_evt_{uuid4().hex}",
            task_id=task_id,
            trace_id=trace_id,
            task_version=snapshot.version,
            actor_id=owner_id,
            event_type="TASK_CREATED",
            idempotency_key=idempotency_key,
            payload={
                "title": contract.title,
                "contract_version": contract.contract_version,
                "deliverable_ids": [item.deliverable_id for item in contract.deliverables],
                "contract_digest": canonical_hash(contract),
            },
            occurred_at=now,
        )
        try:
            await self.store.create(snapshot.model_dump(mode="json"), event.model_dump(mode="json"))
        except TaskStoreConflictError as exc:
            existing = await self.store.load(task_id, owner_id)
            if existing is None:
                raise TaskCreateConflictError("任务创建发生冲突") from exc
            restored = self._restore(existing)
            if canonical_hash(self._draft_from_contract(restored.contract)) != canonical_hash(
                draft
            ):
                raise TaskCreateConflictError("幂等键已用于不同任务契约") from exc
            return restored
        return snapshot

    async def create_demo1(
        self,
        owner_id: str,
        *,
        idempotency_key: str | None = None,
    ) -> TaskSnapshot:
        return await self.create(
            demo1_contract_draft(),
            owner_id,
            idempotency_key=idempotency_key or f"demo1-customer-a:{owner_id}",
        )

    async def get_committed_artifact(
        self,
        task_id: str,
        artifact_version_id: str,
        owner_id: str,
    ) -> tuple[TaskSnapshot, ArtifactVersion, VerificationReport]:
        snapshot = await self.get(task_id, owner_id)
        if snapshot.status != "committed" or snapshot.last_commit is None:
            raise TaskTransitionError("任务尚未形成最终提交，不能准备外部动作")
        if artifact_version_id not in snapshot.last_commit.artifact_version_ids:
            raise TaskTransitionError("只能从最终提交中的当前成果准备动作")
        artifact = next(
            (
                item
                for item in snapshot.artifact_versions
                if item.artifact_version_id == artifact_version_id
            ),
            None,
        )
        if artifact is None:
            raise TaskTransitionError("最终提交引用的工件版本不存在")
        report = next(
            (
                item
                for item in snapshot.verification_reports
                if item.artifact_version_id == artifact_version_id
                and item.status == "passed"
                and item.report_id in snapshot.last_commit.verification_report_ids
            ),
            None,
        )
        if report is None or artifact.status != "verified":
            raise TaskTransitionError("工件尚未通过最终验证，不能准备外部动作")
        return snapshot, artifact, report

    async def validate_action_binding(
        self,
        binding: TaskArtifactBinding,
        owner_id: str,
    ) -> None:
        snapshot, artifact, report = await self.get_committed_artifact(
            binding.task_id,
            binding.artifact_version_id,
            owner_id,
        )
        commit = snapshot.last_commit
        if commit is None:
            raise TaskTransitionError("绑定成果的最终提交已不可用")
        expected = {
            "task_version": snapshot.version,
            "commit_id": commit.commit_id,
            "commit_state_hash": commit.state_hash,
            "artifact_id": artifact.artifact_id,
            "artifact_version": artifact.version,
            "artifact_content_digest": artifact.content_digest,
            "deliverable_id": artifact.deliverable_id,
            "verification_report_id": report.report_id,
        }
        actual = binding.model_dump(exclude={"task_id", "artifact_version_id"})
        if actual != expected:
            raise TaskTransitionError("绑定成果已经变化，请基于当前核对结果重新准备动作")

    async def start(
        self,
        task_id: str,
        owner_id: str,
        *,
        expected_task_version: int,
        idempotency_key: str,
    ) -> TaskSnapshot:
        command_digest = canonical_hash(
            {
                "operation": "start_demo1_stage",
                "task_id": task_id,
                "expected_task_version": expected_task_version,
            }
        )
        replay = await self._idempotent_replay(task_id, owner_id, idempotency_key, command_digest)
        if replay is not None:
            return replay

        current = await self.get(task_id, owner_id)
        self._require_version(current, expected_task_version)
        if current.status != "ready" or current.phase != "contract":
            raise TaskTransitionError("任务只能从 ready / contract 启动")
        self._require_demo1_stage_contract(current)
        self._require_execution_window(
            current,
            additional_steps=1,
            additional_tool_calls=1,
            additional_runtime_seconds=1,
        )

        now = datetime.now(UTC)
        stage = TaskStageRecord(
            phase="observe",
            status="running",
            summary="正在读取本轮允许资料",
            detail={
                "source_count": len(current.contract.source_scope),
                "source_labels": self._demo1_source_labels(),
            },
            generation_source="deterministic",
            started_at=now,
        )
        budget = self._consume_budget(
            current,
            additional_steps=1,
            additional_tool_calls=1,
            additional_runtime_seconds=1,
        )
        updated = self._updated_snapshot(
            current,
            status="running",
            phase="observe",
            stage_records=[*current.stage_records, stage],
            budget=budget,
            updated_at=now,
        )
        specs = [
            TaskEventSpec(
                "TASK_STATUS_CHANGED",
                {"from": current.status, "to": "running"},
            ),
            TaskEventSpec(
                "TASK_PHASE_CHANGED",
                {"from": current.phase, "to": "observe"},
            ),
            TaskEventSpec(
                "LOOP_STEP_STARTED",
                {"phase": "observe", "source_count": len(current.contract.source_scope)},
                idempotent=True,
            ),
            TaskEventSpec(
                "BUDGET_UPDATED",
                {
                    "steps_used": budget.steps_used,
                    "tool_calls_used": budget.tool_calls_used,
                },
            ),
        ]
        return await self._commit_mutation(
            current,
            updated,
            owner_id,
            [],
            specs,
            idempotency_key,
            command_digest,
        )

    async def advance(
        self,
        task_id: str,
        owner_id: str,
        *,
        expected_task_version: int,
        idempotency_key: str,
    ) -> TaskSnapshot:
        lock = self._advance_locks.setdefault((task_id, idempotency_key), asyncio.Lock())
        async with lock:
            return await self._advance_unlocked(
                task_id,
                owner_id,
                expected_task_version=expected_task_version,
                idempotency_key=idempotency_key,
            )

    async def _advance_unlocked(
        self,
        task_id: str,
        owner_id: str,
        *,
        expected_task_version: int,
        idempotency_key: str,
    ) -> TaskSnapshot:
        """Complete exactly one durable stage and expose its next checkpoint."""
        current = await self.get(task_id, owner_id)
        command_digest = canonical_hash(
            {
                "operation": "advance_task_stage",
                "task_id": task_id,
                "expected_task_version": expected_task_version,
            }
        )
        replay = await self._idempotent_replay(task_id, owner_id, idempotency_key, command_digest)
        if replay is not None:
            return replay
        self._require_version(current, expected_task_version)
        if current.status in {"committed", "failed", "cancelled"}:
            raise TaskTransitionError("终态任务不能继续推进")
        if current.status == "waiting_input":
            raise TaskTransitionError("任务正在等待用户处理，不能自动推进")
        if current.phase not in {"observe", "plan", "act", "verify"}:
            raise TaskTransitionError("当前任务阶段不能推进")

        try:
            if current.phase == "observe":
                self._require_execution_window(
                    current,
                    additional_steps=1,
                    additional_tool_calls=1,
                    additional_runtime_seconds=1,
                )
                updated, artifacts, specs = self._advance_observe(current)
            elif current.phase == "plan":
                self._require_execution_window(
                    current,
                    additional_steps=1,
                    additional_tool_calls=1,
                    additional_runtime_seconds=1,
                )
                started_at = monotonic()
                plan = await self.stage_agent.plan(self._build_plan_request(current))
                elapsed_seconds = monotonic() - started_at
                _log_task_stage("plan", self.stage_agent, elapsed_seconds, plan.origin)
                plan = self._validated_plan(current, plan)
                runtime_seconds = max(1, int(elapsed_seconds + 0.999))
                self._require_execution_window(
                    current,
                    additional_steps=1,
                    additional_tool_calls=1,
                    additional_runtime_seconds=runtime_seconds,
                )
                updated, artifacts, specs = self._advance_plan(
                    current, plan, runtime_seconds=runtime_seconds
                )
            elif current.phase == "act":
                self._require_execution_window(
                    current,
                    additional_steps=1,
                    additional_tool_calls=len(current.branches),
                    additional_runtime_seconds=1,
                )
                plan = self._stage_detail(current, "plan").get("plan", {})
                started_at = monotonic()
                act = await self.stage_agent.act(self._build_act_request(current, plan))
                elapsed_seconds = monotonic() - started_at
                _log_task_stage("act", self.stage_agent, elapsed_seconds, act.origin)
                runtime_seconds = max(1, int(elapsed_seconds + 0.999))
                self._require_execution_window(
                    current,
                    additional_steps=1,
                    additional_tool_calls=len(current.branches),
                    additional_runtime_seconds=runtime_seconds,
                )
                updated, artifacts, specs = self._advance_act(
                    current,
                    self._validated_act(current, act, plan),
                    runtime_seconds=runtime_seconds,
                )
            else:
                self._require_execution_window(
                    current,
                    additional_steps=1,
                    additional_tool_calls=1,
                    additional_runtime_seconds=1,
                )
                updated, artifacts, specs = self._advance_verify(current)
        except Exception as exc:
            return await self._commit_stage_failure(
                current,
                owner_id,
                idempotency_key,
                command_digest,
                exc,
            )
        return await self._commit_mutation(
            current,
            updated,
            owner_id,
            artifacts,
            specs,
            idempotency_key,
            command_digest,
        )

    async def control(
        self,
        task_id: str,
        owner_id: str,
        command: TaskControlCommand,
    ) -> TaskSnapshot:
        command_digest = canonical_hash(
            {
                "operation": "task_control",
                "task_id": task_id,
                "command": command.model_dump(mode="json"),
            }
        )
        replay = await self._idempotent_replay(
            task_id, owner_id, command.idempotency_key, command_digest
        )
        if replay is not None:
            return replay

        current = await self.get(task_id, owner_id)
        self._require_version(current, command.expected_task_version)
        if command.kind == "resolve_evidence":
            self._require_execution_window(
                current,
                additional_steps=1,
                additional_runtime_seconds=1,
            )
            updated, artifacts, specs = self._build_evidence_resolution(current, command, owner_id)
        else:
            updated, artifacts, specs = self._build_control_update(current, command, owner_id)
        return await self._commit_mutation(
            current,
            updated,
            owner_id,
            artifacts,
            specs,
            command.idempotency_key,
            command_digest,
        )

    async def get(self, task_id: str, owner_id: str) -> TaskSnapshot:
        stored = await self.store.load(task_id, owner_id)
        if stored is None:
            raise TaskNotFoundError(task_id)
        return self._restore(stored)

    async def list(self, owner_id: str) -> list[TaskSnapshot]:
        return [self._restore(item) for item in await self.store.list_for_owner(owner_id)]

    async def history(
        self, task_id: str, owner_id: str, after_sequence: int = 0
    ) -> list[TaskEvent]:
        await self.get(task_id, owner_id)
        return [
            TaskEvent.model_validate(item)
            for item in await self.store.load_events(task_id, owner_id, after_sequence)
        ]

    async def event_stream(
        self,
        task_id: str,
        owner_id: str,
        after_sequence: int = 0,
        heartbeat_seconds: float = 15,
    ) -> AsyncIterator[TaskEvent | None]:
        await self.get(task_id, owner_id)
        cursor = after_sequence
        last_emit = monotonic()
        while True:
            events = await self.history(task_id, owner_id, cursor)
            if events:
                for event in events:
                    cursor = event.sequence
                    last_emit = monotonic()
                    yield event
                continue
            if monotonic() - last_emit >= heartbeat_seconds:
                last_emit = monotonic()
                yield None
            await asyncio.sleep(self.poll_interval_seconds)

    @staticmethod
    def _require_demo1_stage_contract(current: TaskSnapshot) -> None:
        expected = demo1_contract_draft()
        if (
            current.contract.title != expected.title
            or current.contract.objective != expected.objective
            or current.contract.source_scope != expected.source_scope
            or current.contract.allowed_capabilities != expected.allowed_capabilities
            or current.contract.deliverables != expected.deliverables
            or current.contract.completion_criteria != expected.completion_criteria
            or current.contract.budget != expected.budget
            or current.contract.deadline_at != expected.deadline_at
        ):
            raise TaskTransitionError("当前渐进阶段只支持固定 Demo 1 契约与来源范围")

    @staticmethod
    def _demo1_source_labels() -> list[str]:
        return [
            "客户来信（演示数据）",
            "CRM 正式经营口径（演示数据）",
            "预测收入表（演示数据）",
            "项目周报（演示数据）",
        ]

    @staticmethod
    def _demo1_resolution_options() -> list[ConflictResolutionOption]:
        """Return the only server-approved resolution exposed by Demo 1."""
        return [
            ConflictResolutionOption(
                option_id="use-official-crm-revenue",
                kind="select_source",
                label="采用 CRM 正式口径",
                description="经营分析使用 CRM 正式收入 2400 万元，并保留预测值作为差异说明。",
                selected_source_ref="fixture:crm/customer-a:official-revenue-v3",
                expected_impact=ResolutionImpact(
                    task_status="committed",
                    task_phase="commit",
                    branch_status="committed",
                    changed_deliverable_ids=["operating-analysis", "reply-draft"],
                    creates_artifact_versions=2,
                    creates_verification_reports=2,
                    commit_created=True,
                    external_side_effect="none",
                    changes=[
                        ImpactChange(
                            change_kind="will_change",
                            label="经营分析",
                            before="待确认正式口径",
                            after="CRM 正式收入 2400 万元，并保留预测差异",
                            deliverable_ids=["operating-analysis"],
                        ),
                        ImpactChange(
                            change_kind="will_recheck",
                            label="客户回复草稿",
                            before="收入数字待正式口径确认",
                            after="按 CRM 正式口径重新核对，仍保持草稿",
                            deliverable_ids=["reply-draft"],
                        ),
                        ImpactChange(
                            change_kind="unchanged",
                            label="风险页",
                            before="已通过核对",
                            after="保持已核对状态",
                            deliverable_ids=["risk-brief"],
                        ),
                        ImpactChange(
                            change_kind="no_external_action",
                            label="外部发送",
                            before="未发送",
                            after="仍不发送",
                        ),
                    ],
                ),
            )
        ]

    @staticmethod
    def _impact_receipt(
        current: TaskSnapshot,
        *,
        to_task_version: int,
        artifacts: list[ArtifactVersion],
        reports: list[VerificationReport],
        commit_id: str | None,
        commit_created: bool,
        changes: list[ImpactChange],
        summary: str,
    ) -> ImpactReceipt:
        return ImpactReceipt(
            from_task_version=current.version,
            to_task_version=to_task_version,
            impact_status="applied",
            changed_artifact_version_ids=[item.artifact_version_id for item in artifacts],
            changed_deliverable_ids=list(dict.fromkeys(item.deliverable_id for item in artifacts)),
            verification_report_ids=[item.report_id for item in reports],
            verification_status=(
                "passed"
                if commit_created and reports and all(item.status == "passed" for item in reports)
                else "partial" if reports else "not_run"
            ),
            commit_id=commit_id,
            commit_created=commit_created,
            external_side_effect="none",
            changes=changes,
            summary=summary,
        )

    @classmethod
    def _validated_plan(
        cls,
        current: TaskSnapshot,
        generated: TaskStagePlan,
    ) -> TaskStagePlan:
        """Persist only the bounded, user-facing plan vocabulary approved by the server."""
        request = cls._build_plan_request(current)
        approved = DeterministicTaskStageAgent.plan_template(request)
        if generated.model_dump() != approved.model_dump():
            return approved
        return generated

    @classmethod
    def _validated_act(
        cls,
        current: TaskSnapshot,
        generated: TaskStageAct,
        plan: dict[str, Any],
    ) -> TaskStageAct:
        """Accept only server-approved prose; model output never introduces new facts."""
        request = cls._build_act_request(current, plan)
        approved = DeterministicTaskStageAgent.act_template(request)
        if generated.model_dump() != approved.model_dump():
            return approved
        return generated

    @staticmethod
    def _stage_context(current: TaskSnapshot) -> tuple[TaskStageContract, list[TaskStageDeliverable], list[TaskStageSourceAlias], list[TaskStageTrustedFact]]:
        TaskService._require_demo1_stage_contract(current)
        contract = TaskStageContract(
            title=current.contract.title,
            objective=current.contract.objective,
            completion_criteria=current.contract.completion_criteria,
        )
        deliverables = [
            TaskStageDeliverable(
                deliverable_id=item.deliverable_id,
                title=item.title,
                kind=item.kind,
                completion_criteria=item.completion_criteria,
            )
            for item in current.contract.deliverables
        ]
        # Keep internal fixture references on the server. The model only sees
        # stable business labels and the trusted facts below refer to aliases.
        business_labels = TaskService._demo1_source_labels()
        aliases = [
            TaskStageSourceAlias(
                alias=f"source_{index}",
                label=business_labels[index - 1] if index <= len(business_labels) else "演示资料",
            )
            for index, _source in enumerate(current.contract.source_scope, start=1)
        ]
        facts: list[TaskStageTrustedFact] = []
        if len(aliases) >= 2:
            facts.append(TaskStageTrustedFact(fact_key="official_revenue_wan", source_alias="source_2", value=2400))
        if len(aliases) >= 3:
            facts.append(TaskStageTrustedFact(fact_key="forecast_revenue_wan", source_alias="source_3", value=2680))
        if len(aliases) >= 4:
            facts.append(TaskStageTrustedFact(fact_key="project_risk", source_alias="source_4", value="里程碑存在一周延期风险"))
        return contract, deliverables, aliases, facts

    @classmethod
    def _build_plan_request(cls, current: TaskSnapshot) -> TaskStagePlanRequest:
        contract, deliverables, aliases, facts = cls._stage_context(current)
        return TaskStagePlanRequest(
            contract=contract,
            deliverables=deliverables,
            source_aliases=aliases,
            trusted_facts=facts,
            instruction="仅规划契约内三份交付材料，不改变服务端身份、来源或状态。",
        )

    @classmethod
    def _build_act_request(cls, current: TaskSnapshot, plan: dict[str, Any]) -> TaskStageActRequest:
        contract, deliverables, aliases, facts = cls._stage_context(current)
        return TaskStageActRequest(
            contract=contract,
            deliverables=deliverables,
            source_aliases=aliases,
            trusted_facts=facts,
            work_packages=plan.get("work_packages", []),
        )

    def _stage_detail(self, current: TaskSnapshot, phase: TaskStage) -> dict[str, Any]:
        for record in reversed(current.stage_records):
            if record.phase == phase:
                return record.detail
        return {}

    @staticmethod
    def _replace_stage(
        current: TaskSnapshot,
        phase: TaskStage,
        record: TaskStageRecord,
        *extra: TaskStageRecord,
    ) -> list[TaskStageRecord]:
        records = list(current.stage_records)
        for index in range(len(records) - 1, -1, -1):
            if records[index].phase == phase:
                records[index] = record
                break
        else:
            records.append(record)
        records.extend(extra)
        return records

    def _advance_observe(
        self, current: TaskSnapshot
    ) -> tuple[TaskSnapshot, list[ArtifactVersion], list[TaskEventSpec]]:
        now = datetime.now(UTC)
        running = self._stage_record(current, "observe")
        observed = running.model_copy(
            update={
                "status": "completed",
                "summary": "已读取本轮允许资料",
                "detail": {
                    "source_count": len(current.contract.source_scope),
                    "source_labels": self._demo1_source_labels(),
                },
                "completed_at": now,
            }
        )
        plan = TaskStageRecord(
            phase="plan",
            status="running",
            summary="正在拆分三份交付材料",
            detail={"deliverable_ids": [item.deliverable_id for item in current.contract.deliverables]},
            generation_source="system",
            started_at=now,
        )
        budget = self._consume_budget(current, additional_steps=1, additional_tool_calls=1, additional_runtime_seconds=1)
        updated = self._updated_snapshot(
            current,
            status="running",
            phase="plan",
            stage_records=self._replace_stage(current, "observe", observed, plan),
            budget=budget,
            updated_at=now,
        )
        specs = [
            TaskEventSpec("LOOP_STEP_COMPLETED", {"phase": "observe", "source_refs": current.contract.source_scope}, idempotent=True),
            TaskEventSpec("TASK_PHASE_CHANGED", {"from": "observe", "to": "plan"}),
            TaskEventSpec("LOOP_STEP_STARTED", {"phase": "plan", "deliverable_count": len(current.contract.deliverables)}),
            TaskEventSpec("BUDGET_UPDATED", {"steps_used": budget.steps_used, "tool_calls_used": budget.tool_calls_used}),
        ]
        return updated, [], specs

    def _advance_plan(
        self,
        current: TaskSnapshot,
        plan: TaskStagePlan,
        *,
        runtime_seconds: int = 1,
    ) -> tuple[TaskSnapshot, list[ArtifactVersion], list[TaskEventSpec]]:
        expected_ids = [item.deliverable_id for item in current.contract.deliverables]
        packages = {item.deliverable_id: item for item in plan.work_packages}
        if set(packages) != set(expected_ids) or len(packages) != len(plan.work_packages):
            raise TaskTransitionError("模型规划不能改变任务交付物")
        safe_plan = {
            "deliverable_ids": expected_ids,
            "summary": plan.summary[:500],
            "work_packages": [packages[item_id].model_dump(mode="json") for item_id in expected_ids],
        }
        now = datetime.now(UTC)
        running = self._stage_record(current, "plan")
        completed = running.model_copy(
            update={
                "status": "completed",
                "summary": "已拆分三份交付材料",
                "detail": {"plan": safe_plan},
                "generation_source": plan.origin,
                "completed_at": now,
            }
        )
        act = TaskStageRecord(
            phase="act",
            status="running",
            summary="正在生成三份交付材料",
            detail={"deliverable_ids": expected_ids},
            generation_source="system",
            started_at=now,
        )
        branches = [
            branch.model_copy(update={"status": "running", "version": branch.version + 1, "updated_at": now})
            if branch.status == "queued" else branch
            for branch in current.branches
        ]
        budget = self._consume_budget(
            current,
            additional_steps=1,
            additional_tool_calls=1,
            additional_runtime_seconds=runtime_seconds,
        )
        updated = self._updated_snapshot(
            current,
            status="running",
            phase="act",
            branches=branches,
            stage_records=self._replace_stage(current, "plan", completed, act),
            budget=budget,
            updated_at=now,
        )
        specs: list[TaskEventSpec] = [
            TaskEventSpec("LOOP_STEP_COMPLETED", {"phase": "plan", "branch_count": len(branches)}, idempotent=True),
            TaskEventSpec("TASK_PHASE_CHANGED", {"from": "plan", "to": "act"}),
        ]
        specs.extend(
            TaskEventSpec("BRANCH_STATUS_CHANGED", {"from": "queued", "to": "running", "title": branch.title}, branch_id=branch.branch_id)
            for branch in current.branches
            if branch.status == "queued"
        )
        specs.extend(
            [
                TaskEventSpec("LOOP_STEP_STARTED", {"phase": "act", "deliverable_count": len(expected_ids)}),
                TaskEventSpec("BUDGET_UPDATED", {"steps_used": budget.steps_used, "tool_calls_used": budget.tool_calls_used}),
            ]
        )
        return updated, [], specs

    def _advance_act(
        self,
        current: TaskSnapshot,
        generated: TaskStageAct,
        *,
        runtime_seconds: int = 1,
    ) -> tuple[TaskSnapshot, list[ArtifactVersion], list[TaskEventSpec]]:
        now = datetime.now(UTC)
        source_refs = {
            "operating-analysis": ["fixture:crm/customer-a:official-revenue-v3", "fixture:forecast/customer-a:revenue-v2"],
            "risk-brief": ["fixture:project/customer-a:weekly-v5"],
            "reply-draft": ["fixture:mail/customer-a:2026-06-15", "fixture:project/customer-a:weekly-v5"],
        }
        artifacts: list[ArtifactVersion] = []
        for branch in current.branches:
            deliverable_id = branch.deliverable_ids[0]
            if deliverable_id == "operating-analysis":
                content = {
                    "customer": "客户 A",
                    "official_revenue_wan": 2400,
                    "forecast_revenue_wan": 2680,
                    "selected_revenue_wan": None,
                    "revenue_basis": "待确认正式口径",
                    "summary": "正式 CRM 与预测表存在收入口径冲突，需人工选择依据。",
                }
            elif deliverable_id == "risk-brief":
                content = {
                    "customer": "客户 A",
                    "risks": [{"level": "medium", "summary": generated.risk_summary, "mitigation": generated.risk_mitigation}],
                }
            elif deliverable_id == "reply-draft":
                content = {
                    "customer": "客户 A",
                    "subject": generated.reply_subject,
                    "body": generated.reply_body,
                    "send_status": "draft_only",
                }
            else:
                raise TaskTransitionError(f"不支持的交付物：{deliverable_id}")
            artifacts.append(
                self._new_artifact(
                    current,
                    branch,
                    deliverable_id,
                    1,
                    "candidate",
                    content,
                    source_refs[deliverable_id],
                    now,
                )
            )
        running = self._stage_record(current, "act")
        completed = running.model_copy(
            update={
                "status": "completed",
                "summary": "已生成三份可核对材料",
                "detail": {"artifact_count": len(artifacts)},
                "generation_source": generated.origin,
                "artifact_version_ids": [item.artifact_version_id for item in artifacts],
                "completed_at": now,
            }
        )
        verify = TaskStageRecord(
            phase="verify",
            status="running",
            summary="正在核对材料中的事实与来源",
            detail={"candidate_artifact_ids": [item.artifact_version_id for item in artifacts]},
            generation_source="deterministic",
            started_at=now,
        )
        artifact_by_branch = {item.branch_id: item for item in artifacts}
        branches = [
            branch.model_copy(
                update={
                    "artifact_heads": {
                        **branch.artifact_heads,
                        branch.deliverable_ids[0]: artifact_by_branch[branch.branch_id].artifact_version_id,
                    },
                    "updated_at": now,
                }
            )
            for branch in current.branches
        ]
        budget = self._consume_budget(
            current,
            additional_steps=1,
            additional_tool_calls=len(artifacts),
            additional_runtime_seconds=runtime_seconds,
        )
        updated = self._updated_snapshot(
            current,
            status="verifying",
            phase="verify",
            branches=branches,
            artifact_versions=[*current.artifact_versions, *artifacts],
            stage_records=self._replace_stage(current, "act", completed, verify),
            budget=budget,
            updated_at=now,
        )
        specs: list[TaskEventSpec] = [
            TaskEventSpec("LOOP_STEP_COMPLETED", {"phase": "act", "candidate_count": len(artifacts)}, idempotent=True),
            TaskEventSpec("TASK_PHASE_CHANGED", {"from": "act", "to": "verify"}),
            TaskEventSpec("TASK_STATUS_CHANGED", {"from": current.status, "to": "verifying"}),
        ]
        specs.extend(
            TaskEventSpec(
                "ARTIFACT_VERSION_CREATED",
                {"deliverable_id": item.deliverable_id, "version": item.version, "status": item.status},
                branch_id=item.branch_id,
                artifact_version_id=item.artifact_version_id,
            )
            for item in artifacts
        )
        specs.append(TaskEventSpec("LOOP_STEP_STARTED", {"phase": "verify"}))
        specs.append(TaskEventSpec("BUDGET_UPDATED", {"steps_used": budget.steps_used, "tool_calls_used": budget.tool_calls_used}))
        return updated, artifacts, specs

    def _advance_verify(
        self, current: TaskSnapshot
    ) -> tuple[TaskSnapshot, list[ArtifactVersion], list[TaskEventSpec]]:
        now = datetime.now(UTC)
        candidates = {
            item.deliverable_id: item
            for item in current.artifact_versions
            if item.version == 1 and item.status == "candidate"
        }
        operating = self._branch_for(current, "operating-analysis")
        risk = self._branch_for(current, "risk-brief")
        reply = self._branch_for(current, "reply-draft")
        if set(candidates) != {"operating-analysis", "risk-brief", "reply-draft"}:
            raise TaskTransitionError("核对阶段缺少候选工件")
        verified_risk = self._new_artifact(current, risk, "risk-brief", 2, "verified", candidates["risk-brief"].content, candidates["risk-brief"].source_refs, now, artifact_id=candidates["risk-brief"].artifact_id, parent_version_id=candidates["risk-brief"].artifact_version_id)
        verified_reply = self._new_artifact(current, reply, "reply-draft", 2, "verified", candidates["reply-draft"].content, candidates["reply-draft"].source_refs, now, artifact_id=candidates["reply-draft"].artifact_id, parent_version_id=candidates["reply-draft"].artifact_version_id)
        conflict = ConflictRecord(
            conflict_id=f"task_conflict_{uuid4().hex}",
            task_id=current.task_id,
            branch_id=operating.branch_id,
            subject="客户 A 收入口径",
            summary="CRM 正式口径为 2400 万元，预测表为 2680 万元。最终汇报必须选择并记录正式依据。",
            source_refs=["fixture:crm/customer-a:official-revenue-v3", "fixture:forecast/customer-a:revenue-v2"],
            candidate_values=["2400 万元（CRM 正式口径）", "2680 万元（预测口径）"],
            resolution_options=self._demo1_resolution_options(),
            opened_at=now,
        )
        reports = [
            VerificationReport(
                report_id=f"task_verify_{uuid4().hex}", task_id=current.task_id, branch_id=operating.branch_id,
                artifact_version_id=candidates["operating-analysis"].artifact_version_id, status="conflict",
                checks=[VerificationCheck(check_id=f"task_check_{uuid4().hex}", label="收入来源一致性", status="conflict", detail="正式 CRM 与预测表相差 280 万元，不能自动选择最终口径。", source_refs=conflict.source_refs)], checked_at=now,
            ),
            VerificationReport(
                report_id=f"task_verify_{uuid4().hex}", task_id=current.task_id, branch_id=risk.branch_id,
                artifact_version_id=verified_risk.artifact_version_id, status="passed",
                checks=[VerificationCheck(check_id=f"task_check_{uuid4().hex}", label="风险来源绑定", status="passed", detail="风险项绑定到允许范围内的项目周报版本。", source_refs=verified_risk.source_refs)], checked_at=now,
            ),
            VerificationReport(
                report_id=f"task_verify_{uuid4().hex}", task_id=current.task_id, branch_id=reply.branch_id,
                artifact_version_id=verified_reply.artifact_version_id, status="passed",
                checks=[VerificationCheck(check_id=f"task_check_{uuid4().hex}", label="草稿外部影响", status="passed", detail="回复保持为草稿，且未写入存在冲突的收入数字。", source_refs=verified_reply.source_refs)], checked_at=now,
            ),
        ]
        branches = [
            item.model_copy(update={"status": "waiting_evidence", "version": item.version + 1, "artifact_heads": {**item.artifact_heads, "operating-analysis": candidates["operating-analysis"].artifact_version_id}, "issue_ids": [conflict.conflict_id], "pause_reason": "收入来源口径冲突", "updated_at": now})
            if item.branch_id == operating.branch_id else
            item.model_copy(update={"status": "committed", "version": item.version + 1, "artifact_heads": {**item.artifact_heads, item.deliverable_ids[0]: verified_risk.artifact_version_id if item.branch_id == risk.branch_id else verified_reply.artifact_version_id}, "last_commit_id": f"task_checkpoint_{uuid4().hex}", "updated_at": now})
            for item in current.branches
        ]
        running = self._stage_record(current, "verify")
        completed = running.model_copy(update={"status": "completed", "summary": "已完成事实核对，发现一项需人工决定的冲突", "detail": {"conflict_ids": [conflict.conflict_id]}, "artifact_version_ids": [verified_risk.artifact_version_id, verified_reply.artifact_version_id], "completed_at": now})
        budget = self._consume_budget(current, additional_steps=1, additional_tool_calls=1, additional_runtime_seconds=1)
        updated = self._updated_snapshot(
            current,
            status="waiting_input",
            phase="verify",
            branches=branches,
            artifact_versions=[*current.artifact_versions, verified_risk, verified_reply],
            verification_reports=[*current.verification_reports, *reports],
            conflicts=[*current.conflicts, conflict],
            stage_records=self._replace_stage(current, "verify", completed),
            budget=budget,
            updated_at=now,
        )
        specs: list[TaskEventSpec] = [
            TaskEventSpec("LOOP_STEP_COMPLETED", {"phase": "verify", "result": "waiting_evidence", "conflict_id": conflict.conflict_id}, idempotent=True),
            TaskEventSpec("CONFLICT_OPENED", {"conflict_id": conflict.conflict_id, "subject": conflict.subject, "candidate_values": conflict.candidate_values}, branch_id=conflict.branch_id, artifact_version_id=candidates["operating-analysis"].artifact_version_id),
        ]
        specs.extend(TaskEventSpec("ARTIFACT_VERSION_CREATED", {"deliverable_id": item.deliverable_id, "version": item.version, "status": item.status}, branch_id=item.branch_id, artifact_version_id=item.artifact_version_id) for item in [verified_risk, verified_reply])
        specs.extend(TaskEventSpec("VERIFICATION_RECORDED", {"report_id": report.report_id, "status": report.status}, branch_id=report.branch_id, artifact_version_id=report.artifact_version_id) for report in reports)
        specs.extend(TaskEventSpec("BRANCH_STATUS_CHANGED", {"from": before.status, "to": after.status, "title": after.title}, branch_id=after.branch_id) for before, after in zip(current.branches, branches) if before.status != after.status)
        specs.extend([
            TaskEventSpec("BUDGET_UPDATED", {"steps_used": budget.steps_used, "tool_calls_used": budget.tool_calls_used}),
            TaskEventSpec("TASK_STATUS_CHANGED", {"from": current.status, "to": "waiting_input"}),
        ])
        return updated, [verified_risk, verified_reply], specs

    @staticmethod
    def _stage_record(current: TaskSnapshot, phase: TaskStage) -> TaskStageRecord:
        for record in reversed(current.stage_records):
            if record.phase == phase and record.status == "running":
                return record
        raise TaskTransitionError(f"缺少运行中的 {phase} 阶段记录")

    async def _commit_stage_failure(
        self,
        current: TaskSnapshot,
        owner_id: str,
        idempotency_key: str,
        command_digest: str,
        error: Exception,
    ) -> TaskSnapshot:
        now = datetime.now(UTC)
        phase = current.phase
        if phase not in {"observe", "plan", "act", "verify"}:
            raise TaskTransitionError("当前阶段不能记录失败")
        running = self._stage_record(current, phase)
        error_code = type(error).__name__
        message = "当前阶段未能安全完成，任务已停在最近确认的状态。"
        failed = running.model_copy(
            update={
                "status": "failed",
                "summary": "阶段执行失败",
                "detail": {"error_code": error_code},
                "failed_at": now,
            }
        )
        updated = self._updated_snapshot(
            current,
            status="failed",
            stage_records=self._replace_stage(current, phase, failed),
            last_error=TaskError(
                code="TASK_STAGE_FAILED",
                scope="task",
                message=message,
                recoverable=True,
                user_action="查看最近确认的阶段，并开始新一轮任务",
            ),
            updated_at=now,
        )
        specs = [
            TaskEventSpec(
                "TASK_FAILED",
                {"phase": phase, "error_code": error_code},
                idempotent=True,
            ),
            TaskEventSpec("TASK_STATUS_CHANGED", {"from": current.status, "to": "failed"}),
        ]
        return await self._commit_mutation(current, updated, owner_id, [], specs, idempotency_key, command_digest)

    def _build_started_demo1(
        self, current: TaskSnapshot
    ) -> tuple[TaskSnapshot, list[ArtifactVersion], list[TaskEventSpec]]:
        now = datetime.now(UTC)
        operating_branch = self._branch_for(current, "operating-analysis")
        risk_branch = self._branch_for(current, "risk-brief")
        reply_branch = self._branch_for(current, "reply-draft")

        operating_content = {
            "customer": "客户 A",
            "official_revenue_wan": 2400,
            "forecast_revenue_wan": 2680,
            "selected_revenue_wan": None,
            "revenue_basis": "待确认正式口径",
            "summary": "正式 CRM 与预测表存在收入口径冲突，需人工选择依据。",
        }
        risk_content = {
            "customer": "客户 A",
            "risks": [
                {
                    "level": "medium",
                    "summary": "项目周报显示交付里程碑存在一周延期风险。",
                    "mitigation": "在下次周会确认资源补位与新里程碑。",
                }
            ],
        }
        reply_content = {
            "customer": "客户 A",
            "subject": "经营进展与下一步安排",
            "body": "已完成经营资料核对。收入数字待正式口径确认后补入，项目风险和后续安排已形成草稿。",
            "send_status": "draft_only",
        }
        operating_candidate = self._new_artifact(
            current,
            operating_branch,
            "operating-analysis",
            1,
            "candidate",
            operating_content,
            [
                "fixture:crm/customer-a:official-revenue-v3",
                "fixture:forecast/customer-a:revenue-v2",
            ],
            now,
        )
        risk_candidate = self._new_artifact(
            current,
            risk_branch,
            "risk-brief",
            1,
            "candidate",
            risk_content,
            ["fixture:project/customer-a:weekly-v5"],
            now,
        )
        reply_candidate = self._new_artifact(
            current,
            reply_branch,
            "reply-draft",
            1,
            "candidate",
            reply_content,
            [
                "fixture:mail/customer-a:2026-06-15",
                "fixture:project/customer-a:weekly-v5",
            ],
            now,
        )
        risk_verified = self._new_artifact(
            current,
            risk_branch,
            "risk-brief",
            2,
            "verified",
            risk_content,
            risk_candidate.source_refs,
            now,
            artifact_id=risk_candidate.artifact_id,
            parent_version_id=risk_candidate.artifact_version_id,
        )
        reply_verified = self._new_artifact(
            current,
            reply_branch,
            "reply-draft",
            2,
            "verified",
            reply_content,
            reply_candidate.source_refs,
            now,
            artifact_id=reply_candidate.artifact_id,
            parent_version_id=reply_candidate.artifact_version_id,
        )
        artifacts = [
            operating_candidate,
            risk_candidate,
            reply_candidate,
            risk_verified,
            reply_verified,
        ]

        conflict = ConflictRecord(
            conflict_id=f"task_conflict_{uuid4().hex}",
            task_id=current.task_id,
            branch_id=operating_branch.branch_id,
            subject="客户 A 收入口径",
            summary="CRM 正式口径为 2400 万元，预测表为 2680 万元。最终汇报必须选择并记录正式依据。",
            source_refs=[
                "fixture:crm/customer-a:official-revenue-v3",
                "fixture:forecast/customer-a:revenue-v2",
            ],
            candidate_values=["2400 万元（CRM 正式口径）", "2680 万元（预测口径）"],
            resolution_options=self._demo1_resolution_options(),
            opened_at=now,
        )
        operating_report = VerificationReport(
            report_id=f"task_verify_{uuid4().hex}",
            task_id=current.task_id,
            branch_id=operating_branch.branch_id,
            artifact_version_id=operating_candidate.artifact_version_id,
            status="conflict",
            checks=[
                VerificationCheck(
                    check_id=f"task_check_{uuid4().hex}",
                    label="收入来源一致性",
                    status="conflict",
                    detail="正式 CRM 与预测表相差 280 万元，不能自动选择最终口径。",
                    source_refs=conflict.source_refs,
                )
            ],
            checked_at=now,
        )
        risk_report = VerificationReport(
            report_id=f"task_verify_{uuid4().hex}",
            task_id=current.task_id,
            branch_id=risk_branch.branch_id,
            artifact_version_id=risk_verified.artifact_version_id,
            status="passed",
            checks=[
                VerificationCheck(
                    check_id=f"task_check_{uuid4().hex}",
                    label="风险来源绑定",
                    status="passed",
                    detail="风险项绑定到允许范围内的项目周报版本。",
                    source_refs=risk_verified.source_refs,
                )
            ],
            checked_at=now,
        )
        reply_report = VerificationReport(
            report_id=f"task_verify_{uuid4().hex}",
            task_id=current.task_id,
            branch_id=reply_branch.branch_id,
            artifact_version_id=reply_verified.artifact_version_id,
            status="passed",
            checks=[
                VerificationCheck(
                    check_id=f"task_check_{uuid4().hex}",
                    label="草稿外部影响",
                    status="passed",
                    detail="回复保持为草稿，且未写入存在冲突的收入数字。",
                    source_refs=reply_verified.source_refs,
                )
            ],
            checked_at=now,
        )
        reports = [operating_report, risk_report, reply_report]
        checkpoint_id = f"task_checkpoint_{uuid4().hex}"
        branches = []
        for branch in current.branches:
            if branch.branch_id == operating_branch.branch_id:
                branches.append(
                    branch.model_copy(
                        update={
                            "status": "waiting_evidence",
                            "version": branch.version + 1,
                            "artifact_heads": {
                                **branch.artifact_heads,
                                "operating-analysis": operating_candidate.artifact_version_id,
                            },
                            "issue_ids": [*branch.issue_ids, conflict.conflict_id],
                            "pause_reason": "收入来源口径冲突",
                            "updated_at": now,
                        }
                    )
                )
            elif branch.branch_id == risk_branch.branch_id:
                branches.append(
                    branch.model_copy(
                        update={
                            "status": "committed",
                            "version": branch.version + 1,
                            "artifact_heads": {
                                **branch.artifact_heads,
                                "risk-brief": risk_verified.artifact_version_id,
                            },
                            "last_commit_id": checkpoint_id,
                            "updated_at": now,
                        }
                    )
                )
            elif branch.branch_id == reply_branch.branch_id:
                branches.append(
                    branch.model_copy(
                        update={
                            "status": "committed",
                            "version": branch.version + 1,
                            "artifact_heads": {
                                **branch.artifact_heads,
                                "reply-draft": reply_verified.artifact_version_id,
                            },
                            "last_commit_id": checkpoint_id,
                            "updated_at": now,
                        }
                    )
                )
            else:
                branches.append(branch)

        budget = self._consume_budget(
            current,
            additional_steps=4,
            additional_tool_calls=4,
            additional_runtime_seconds=1,
        )
        updated = self._updated_snapshot(
            current,
            status="waiting_input",
            phase="verify",
            branches=branches,
            artifact_versions=[*current.artifact_versions, *artifacts],
            verification_reports=[*current.verification_reports, *reports],
            conflicts=[*current.conflicts, conflict],
            budget=budget,
            updated_at=now,
        )
        specs: list[TaskEventSpec] = [
            TaskEventSpec(
                "LOOP_STEP_STARTED",
                {"phase": "observe", "source_count": len(current.contract.source_scope)},
                idempotent=True,
            ),
            TaskEventSpec("TASK_STATUS_CHANGED", {"from": "ready", "to": "running"}),
            TaskEventSpec("TASK_PHASE_CHANGED", {"from": "contract", "to": "observe"}),
            TaskEventSpec(
                "LOOP_STEP_COMPLETED",
                {"phase": "observe", "source_refs": current.contract.source_scope},
            ),
            TaskEventSpec("LOOP_STEP_STARTED", {"phase": "plan"}),
            TaskEventSpec("TASK_PHASE_CHANGED", {"from": "observe", "to": "plan"}),
        ]
        specs.extend(
            TaskEventSpec(
                "BRANCH_STATUS_CHANGED",
                {"from": branch.status, "to": "running", "title": branch.title},
                branch_id=branch.branch_id,
            )
            for branch in current.branches
        )
        specs.extend(
            [
                TaskEventSpec(
                    "LOOP_STEP_COMPLETED",
                    {"phase": "plan", "branch_count": len(current.branches)},
                ),
                TaskEventSpec("LOOP_STEP_STARTED", {"phase": "act"}),
                TaskEventSpec("TASK_PHASE_CHANGED", {"from": "plan", "to": "act"}),
            ]
        )
        specs.extend(
            TaskEventSpec(
                "ARTIFACT_VERSION_CREATED",
                {
                    "deliverable_id": artifact.deliverable_id,
                    "version": artifact.version,
                    "status": artifact.status,
                },
                branch_id=artifact.branch_id,
                artifact_version_id=artifact.artifact_version_id,
            )
            for artifact in artifacts[:3]
        )
        specs.extend(
            [
                TaskEventSpec("LOOP_STEP_COMPLETED", {"phase": "act", "candidate_count": 3}),
                TaskEventSpec("LOOP_STEP_STARTED", {"phase": "verify"}),
                TaskEventSpec("TASK_PHASE_CHANGED", {"from": "act", "to": "verify"}),
            ]
        )
        specs.extend(
            TaskEventSpec(
                "ARTIFACT_VERSION_CREATED",
                {
                    "deliverable_id": artifact.deliverable_id,
                    "version": artifact.version,
                    "status": artifact.status,
                },
                branch_id=artifact.branch_id,
                artifact_version_id=artifact.artifact_version_id,
            )
            for artifact in artifacts[3:]
        )
        specs.extend(
            TaskEventSpec(
                "VERIFICATION_RECORDED",
                {"report_id": report.report_id, "status": report.status},
                branch_id=report.branch_id,
                artifact_version_id=report.artifact_version_id,
            )
            for report in reports
        )
        specs.append(
            TaskEventSpec(
                "CONFLICT_OPENED",
                {
                    "conflict_id": conflict.conflict_id,
                    "subject": conflict.subject,
                    "candidate_values": conflict.candidate_values,
                },
                branch_id=conflict.branch_id,
                artifact_version_id=operating_candidate.artifact_version_id,
            )
        )
        final_by_id = {branch.branch_id: branch for branch in branches}
        specs.extend(
            TaskEventSpec(
                "BRANCH_STATUS_CHANGED",
                {
                    "from": "running",
                    "to": final_by_id[branch.branch_id].status,
                    "title": branch.title,
                },
                branch_id=branch.branch_id,
            )
            for branch in current.branches
        )
        specs.extend(
            [
                TaskEventSpec(
                    "CHECKPOINT_COMMITTED",
                    {
                        "checkpoint_id": checkpoint_id,
                        "committed_branch_ids": [risk_branch.branch_id, reply_branch.branch_id],
                    },
                ),
                TaskEventSpec(
                    "BUDGET_UPDATED",
                    {
                        "steps_used": budget.steps_used,
                        "tool_calls_used": budget.tool_calls_used,
                    },
                ),
                TaskEventSpec(
                    "TASK_STATUS_CHANGED",
                    {"from": "running", "to": "waiting_input"},
                ),
                TaskEventSpec(
                    "LOOP_STEP_COMPLETED",
                    {
                        "phase": "verify",
                        "result": "waiting_evidence",
                        "conflict_id": conflict.conflict_id,
                    },
                    branch_id=operating_branch.branch_id,
                ),
            ]
        )
        return updated, artifacts, specs

    def _build_evidence_resolution(
        self,
        current: TaskSnapshot,
        command: TaskControlCommand,
        actor_id: str,
    ) -> tuple[TaskSnapshot, list[ArtifactVersion], list[TaskEventSpec]]:
        if command.branch_id is None:
            raise TaskTransitionError("resolve_evidence requires branch_id")
        branch = self._branch_by_id(current, command.branch_id)
        if branch.status != "waiting_evidence":
            raise TaskTransitionError("只有 waiting_evidence 分支可以解决证据冲突")
        conflict = next(
            (
                item
                for item in current.conflicts
                if item.branch_id == branch.branch_id and item.status == "open"
            ),
            None,
        )
        if conflict is None:
            raise TaskTransitionError("该分支没有待解决冲突")
        selected_option = None
        if conflict.resolution_options and command.resolution_option_id is None:
            raise TaskTransitionError("当前冲突必须选择服务端允许的解决方案")
        if command.resolution_option_id is not None:
            selected_option = next(
                (
                    item
                    for item in conflict.resolution_options
                    if item.option_id == command.resolution_option_id
                ),
                None,
            )
            if selected_option is None or not selected_option.executable:
                raise TaskTransitionError("选择的解决方案不是服务端允许的可执行选项")
        official_source = "fixture:crm/customer-a:official-revenue-v3"
        if command.selected_source_ref != official_source:
            raise TaskTransitionError("当前任务契约要求采用 CRM 正式收入口径")
        if selected_option is not None and selected_option.selected_source_ref != command.selected_source_ref:
            raise TaskTransitionError("解决方案与来源选择不一致")
        if official_source not in current.contract.source_scope:
            raise TaskTransitionError("选择的来源不在任务允许范围内")

        deliverable_id = branch.deliverable_ids[0]
        candidate_id = branch.artifact_heads.get(deliverable_id)
        candidate = next(
            (
                item
                for item in current.artifact_versions
                if item.artifact_version_id == candidate_id
            ),
            None,
        )
        if candidate is None:
            raise TaskTransitionError("冲突分支缺少候选工件")

        now = datetime.now(UTC)
        content = {
            **candidate.content,
            "selected_revenue_wan": 2400,
            "revenue_basis": "CRM 正式口径",
            "forecast_delta_wan": 280,
            "forecast_delta_percent": 11.7,
            "summary": "汇报采用 CRM 正式收入 2400 万元，并保留预测值 2680 万元及 11.7% 差异说明。",
        }
        verified = self._new_artifact(
            current,
            branch,
            deliverable_id,
            candidate.version + 1,
            "verified",
            content,
            conflict.source_refs,
            now,
            artifact_id=candidate.artifact_id,
            parent_version_id=candidate.artifact_version_id,
        )
        report = VerificationReport(
            report_id=f"task_verify_{uuid4().hex}",
            task_id=current.task_id,
            branch_id=branch.branch_id,
            artifact_version_id=verified.artifact_version_id,
            status="passed",
            checks=[
                VerificationCheck(
                    check_id=f"task_check_{uuid4().hex}",
                    label="正式收入口径",
                    status="passed",
                    detail="最终收入使用 CRM 正式版本，并保留预测差异说明。",
                    source_refs=conflict.source_refs,
                )
            ],
            checked_at=now,
        )
        resolved_conflict = conflict.model_copy(
            update={
                "status": "resolved",
                "resolution": "采用 CRM 正式收入 2400 万元；预测 2680 万元作为差异说明保留。",
                "resolved_at": now,
            }
        )
        next_version = current.version + 1
        control_event = ControlEvent(
            **command.model_dump(),
            control_event_id=f"task_control_{uuid4().hex}",
            task_id=current.task_id,
            actor_id=actor_id,
            status="applied",
            applied_task_version=next_version,
            created_at=now,
            applied_at=now,
        )
        next_conflicts = [
            resolved_conflict if item.conflict_id == conflict.conflict_id else item
            for item in current.conflicts
        ]
        remaining_open_conflicts = [
            item for item in next_conflicts if item.status == "open"
        ]
        budget = self._consume_budget(
            current,
            additional_steps=1,
            additional_runtime_seconds=1,
        )

        if remaining_open_conflicts:
            open_ids_by_branch: dict[str, list[str]] = {}
            for open_conflict in remaining_open_conflicts:
                open_ids_by_branch.setdefault(open_conflict.branch_id, []).append(
                    open_conflict.conflict_id
                )

            branches: list[BranchSnapshot] = []
            for item in current.branches:
                open_issue_ids = open_ids_by_branch.get(item.branch_id, [])
                updates: dict[str, Any] = {}
                if item.branch_id == branch.branch_id:
                    updates["artifact_heads"] = {
                        **item.artifact_heads,
                        deliverable_id: verified.artifact_version_id,
                    }
                if open_issue_ids:
                    updates.update(
                        {
                            "status": "waiting_evidence",
                            "issue_ids": open_issue_ids,
                            "pause_reason": "仍有证据冲突待解决",
                        }
                    )
                elif item.branch_id == branch.branch_id:
                    updates.update(
                        {
                            "status": "committed",
                            "issue_ids": [],
                            "pause_reason": None,
                            "last_commit_id": f"task_checkpoint_{uuid4().hex}",
                        }
                    )
                if updates:
                    updates.update(
                        {
                            "version": item.version + 1,
                            "updated_at": now,
                        }
                    )
                    branches.append(item.model_copy(update=updates))
                else:
                    branches.append(item)

            control_event = control_event.model_copy(
                update={
                    "impact_receipt": self._impact_receipt(
                        current,
                        to_task_version=next_version,
                        artifacts=[verified],
                        reports=[report],
                        commit_id=None,
                        commit_created=False,
                        changes=[
                            ImpactChange(
                                change_kind="will_change",
                                label="经营分析",
                                before="待确认正式口径",
                                after="已采用 CRM 正式收入 2400 万元",
                                deliverable_ids=[deliverable_id],
                                artifact_version_ids=[verified.artifact_version_id],
                            ),
                            ImpactChange(
                                change_kind="unchanged",
                                label="其余待确认材料",
                                before="仍有待确认冲突",
                                after="保持待确认",
                            ),
                            ImpactChange(
                                change_kind="no_external_action",
                                label="外部发送",
                                before="未发送",
                                after="仍不发送",
                            ),
                        ],
                        summary="已应用证据决定；经营分析已更新，其余冲突仍待处理，未创建最终提交。",
                    )
                }
            )
            updated = self._updated_snapshot(
                current,
                status="waiting_input",
                phase="verify",
                branches=branches,
                artifact_versions=[*current.artifact_versions, verified],
                verification_reports=[*current.verification_reports, report],
                conflicts=next_conflicts,
                controls=[*current.controls, control_event],
                budget=budget,
                updated_at=now,
            )
            specs = [
                TaskEventSpec(
                    "CONTROL_ACCEPTED",
                    {
                        "kind": command.kind,
                        "expected_task_version": command.expected_task_version,
                    },
                    branch_id=branch.branch_id,
                    control_event_id=control_event.control_event_id,
                ),
                TaskEventSpec(
                    "CONFLICT_RESOLVED",
                    {
                        "conflict_id": conflict.conflict_id,
                        "selected_source_ref": official_source,
                    },
                    branch_id=branch.branch_id,
                    control_event_id=control_event.control_event_id,
                ),
                TaskEventSpec(
                    "ARTIFACT_VERSION_CREATED",
                    {
                        "deliverable_id": deliverable_id,
                        "version": verified.version,
                        "status": verified.status,
                    },
                    branch_id=branch.branch_id,
                    artifact_version_id=verified.artifact_version_id,
                ),
                TaskEventSpec(
                    "VERIFICATION_RECORDED",
                    {"report_id": report.report_id, "status": report.status},
                    branch_id=branch.branch_id,
                    artifact_version_id=verified.artifact_version_id,
                ),
            ]
            branches_by_id = {item.branch_id: item for item in branches}
            specs.extend(
                TaskEventSpec(
                    "BRANCH_STATUS_CHANGED",
                    {
                        "from": item.status,
                        "to": branches_by_id[item.branch_id].status,
                        "title": item.title,
                    },
                    branch_id=item.branch_id,
                )
                for item in current.branches
                if item.status != branches_by_id[item.branch_id].status
            )
            specs.extend(
                [
                    TaskEventSpec(
                        "BUDGET_UPDATED",
                        {
                            "steps_used": budget.steps_used,
                            "tool_calls_used": budget.tool_calls_used,
                        },
                    ),
                    TaskEventSpec(
                        "CONTROL_APPLIED",
                        {
                            "kind": command.kind,
                            "applied_task_version": next_version,
                            "remaining_open_conflict_ids": [
                                item.conflict_id for item in remaining_open_conflicts
                            ],
                        },
                        branch_id=branch.branch_id,
                        control_event_id=control_event.control_event_id,
                        idempotent=True,
                    ),
                ]
            )
            return updated, [verified], specs

        reply_branch = self._branch_for(current, "reply-draft")
        reply_head_id = reply_branch.artifact_heads.get("reply-draft")
        reply_head = next(
            (
                item
                for item in current.artifact_versions
                if item.artifact_version_id == reply_head_id
            ),
            None,
        )
        if reply_head is None:
            raise TaskTransitionError("客户回复分支缺少已验证草稿")
        reply_sources = list(
            dict.fromkeys([*reply_head.source_refs, *verified.source_refs])
        )
        reply_content = {
            **reply_head.content,
            "body": (
                "已完成经营资料核对。正式收入采用 CRM 口径 2400 万元；"
                "预测值为 2680 万元，差异 280 万元（11.7%）。"
                "项目风险与后续安排已更新，当前仅保留为客户回复草稿。"
            ),
            "official_revenue_wan": 2400,
            "forecast_revenue_wan": 2680,
            "forecast_delta_wan": 280,
            "forecast_delta_percent": 11.7,
            "revenue_basis": "CRM 正式口径",
            "send_status": "draft_only",
        }
        reply_verified = self._new_artifact(
            current,
            reply_branch,
            "reply-draft",
            reply_head.version + 1,
            "verified",
            reply_content,
            reply_sources,
            now,
            artifact_id=reply_head.artifact_id,
            parent_version_id=reply_head.artifact_version_id,
        )
        reply_report = VerificationReport(
            report_id=f"task_verify_{uuid4().hex}",
            task_id=current.task_id,
            branch_id=reply_branch.branch_id,
            artifact_version_id=reply_verified.artifact_version_id,
            status="passed",
            checks=[
                VerificationCheck(
                    check_id=f"task_check_{uuid4().hex}",
                    label="回复与正式经营事实一致",
                    status="passed",
                    detail=(
                        "回复已按正式 CRM 收入 2400 万元重生成，并保留"
                        "预测 2680 万元及 11.7% 差异说明。"
                    ),
                    source_refs=verified.source_refs,
                ),
                VerificationCheck(
                    check_id=f"task_check_{uuid4().hex}",
                    label="草稿外部影响",
                    status="passed",
                    detail="回复仍为草稿，未触发任何真实外部发送。",
                    source_refs=reply_head.source_refs,
                ),
            ],
            checked_at=now,
        )

        commit_id = f"task_commit_{uuid4().hex}"
        branches = []
        for item in current.branches:
            if item.branch_id == branch.branch_id:
                branches.append(
                    item.model_copy(
                        update={
                            "status": "committed",
                            "version": item.version + 1,
                            "artifact_heads": {
                                **item.artifact_heads,
                                deliverable_id: verified.artifact_version_id,
                            },
                            "issue_ids": [],
                            "pause_reason": None,
                            "last_commit_id": commit_id,
                            "updated_at": now,
                        }
                    )
                )
            elif item.branch_id == reply_branch.branch_id:
                branches.append(
                    item.model_copy(
                        update={
                            "version": item.version + 1,
                            "artifact_heads": {
                                **item.artifact_heads,
                                "reply-draft": reply_verified.artifact_version_id,
                            },
                            "last_commit_id": commit_id,
                            "updated_at": now,
                        }
                    )
                )
            else:
                branches.append(item)
        if any(item.status == "open" for item in next_conflicts):
            raise TaskTransitionError("仍有未解决冲突，不能完成任务")
        if any(item.status != "committed" for item in branches):
            raise TaskTransitionError("仍有其他分支未提交，不能完成任务")

        all_artifacts = [*current.artifact_versions, verified, reply_verified]
        artifacts_by_id = {item.artifact_version_id: item for item in all_artifacts}
        head_ids = [
            item.artifact_heads[deliverable]
            for item in branches
            for deliverable in item.deliverable_ids
        ]
        reports = [*current.verification_reports, report, reply_report]
        report_by_artifact = {
            item.artifact_version_id: item for item in reports if item.status == "passed"
        }
        if any(head_id not in report_by_artifact for head_id in head_ids):
            raise TaskTransitionError("最终工件缺少通过的验证报告")
        report_ids = [report_by_artifact[head_id].report_id for head_id in head_ids]
        state_artifacts = []
        for head_id in head_ids:
            head = artifacts_by_id.get(head_id)
            if head is None:
                raise TaskTransitionError("最终提交引用了未知工件")
            lineage = sorted(
                (item for item in all_artifacts if item.artifact_id == head.artifact_id),
                key=lambda item: item.version,
            )
            state_artifacts.append(
                {
                    "branch_id": head.branch_id,
                    "deliverable_id": head.deliverable_id,
                    "artifact_version_id": head.artifact_version_id,
                    "artifact_id": head.artifact_id,
                    "version": head.version,
                    "parent_version_id": head.parent_version_id,
                    "content_digest": head.content_digest,
                    "lineage": [
                        {
                            "artifact_version_id": item.artifact_version_id,
                            "version": item.version,
                            "parent_version_id": item.parent_version_id,
                            "content_digest": item.content_digest,
                        }
                        for item in lineage
                    ],
                }
            )
        selected_reports = [report_by_artifact[head_id] for head_id in head_ids]
        state_hash = canonical_hash(
            {
                "task_id": current.task_id,
                "task_version": next_version,
                "contract_digest": canonical_hash(current.contract),
                "artifact_heads": sorted(
                    state_artifacts,
                    key=lambda item: (item["branch_id"], item["deliverable_id"]),
                ),
                "verification_reports": [
                    item.model_dump(mode="json")
                    for item in sorted(selected_reports, key=lambda item: item.report_id)
                ],
                "resolved_conflicts": [
                    item.model_dump(mode="json")
                    for item in sorted(next_conflicts, key=lambda item: item.conflict_id)
                ],
            }
        )
        task_commit = TaskCommit(
            commit_id=commit_id,
            task_id=current.task_id,
            task_version=next_version,
            artifact_version_ids=head_ids,
            verification_report_ids=report_ids,
            state_hash=state_hash,
            summary="三个必需交付分支均已验证；收入采用正式口径并保留预测差异。",
            committed_at=now,
        )
        control_event = control_event.model_copy(
            update={
                "impact_receipt": self._impact_receipt(
                    current,
                    to_task_version=next_version,
                    artifacts=[verified, reply_verified],
                    reports=[report, reply_report],
                    commit_id=commit_id,
                    commit_created=True,
                    changes=[
                        ImpactChange(
                            change_kind="will_change",
                            label="经营分析",
                            before="待确认正式口径",
                            after="采用 CRM 正式收入 2400 万元，并保留预测差异",
                            deliverable_ids=[deliverable_id],
                            artifact_version_ids=[verified.artifact_version_id],
                        ),
                        ImpactChange(
                            change_kind="will_recheck",
                            label="客户回复草稿",
                            before="收入数字待正式口径确认",
                            after="已按正式口径重新核对，仍为草稿",
                            deliverable_ids=["reply-draft"],
                            artifact_version_ids=[reply_verified.artifact_version_id],
                        ),
                        ImpactChange(
                            change_kind="unchanged",
                            label="风险页",
                            before="已通过核对",
                            after="保持已核对状态",
                            deliverable_ids=["risk-brief"],
                        ),
                        ImpactChange(
                            change_kind="no_external_action",
                            label="外部发送",
                            before="未发送",
                            after="仍不发送",
                        ),
                    ],
                    summary="证据决定已应用；经营分析与客户回复草稿已更新并通过验证，任务已提交，未触发外部发送。",
                )
            }
        )
        updated = self._updated_snapshot(
            current,
            status="committed",
            phase="commit",
            branches=branches,
            artifact_versions=all_artifacts,
            verification_reports=reports,
            conflicts=next_conflicts,
            controls=[*current.controls, control_event],
            budget=budget,
            last_commit=task_commit,
            updated_at=now,
        )
        specs = [
            TaskEventSpec(
                "CONTROL_ACCEPTED",
                {"kind": command.kind, "expected_task_version": command.expected_task_version},
                branch_id=branch.branch_id,
                control_event_id=control_event.control_event_id,
            ),
            TaskEventSpec(
                "CONFLICT_RESOLVED",
                {
                    "conflict_id": conflict.conflict_id,
                    "selected_source_ref": official_source,
                },
                branch_id=branch.branch_id,
                control_event_id=control_event.control_event_id,
            ),
            TaskEventSpec(
                "ARTIFACT_VERSION_CREATED",
                {
                    "deliverable_id": deliverable_id,
                    "version": verified.version,
                    "status": verified.status,
                },
                branch_id=branch.branch_id,
                artifact_version_id=verified.artifact_version_id,
            ),
            TaskEventSpec(
                "VERIFICATION_RECORDED",
                {"report_id": report.report_id, "status": report.status},
                branch_id=branch.branch_id,
                artifact_version_id=verified.artifact_version_id,
            ),
            TaskEventSpec(
                "ARTIFACT_VERSION_CREATED",
                {
                    "deliverable_id": "reply-draft",
                    "version": reply_verified.version,
                    "status": reply_verified.status,
                    "reason": "evidence_resolution_dependency_update",
                },
                branch_id=reply_branch.branch_id,
                artifact_version_id=reply_verified.artifact_version_id,
            ),
            TaskEventSpec(
                "VERIFICATION_RECORDED",
                {"report_id": reply_report.report_id, "status": reply_report.status},
                branch_id=reply_branch.branch_id,
                artifact_version_id=reply_verified.artifact_version_id,
            ),
            TaskEventSpec(
                "BRANCH_STATUS_CHANGED",
                {"from": branch.status, "to": "committed", "title": branch.title},
                branch_id=branch.branch_id,
            ),
            TaskEventSpec("TASK_PHASE_CHANGED", {"from": current.phase, "to": "commit"}),
            TaskEventSpec(
                "CHECKPOINT_COMMITTED",
                {
                    "checkpoint_id": commit_id,
                    "artifact_version_ids": head_ids,
                    "state_hash": state_hash,
                },
            ),
            TaskEventSpec(
                "BUDGET_UPDATED",
                {
                    "steps_used": budget.steps_used,
                    "tool_calls_used": budget.tool_calls_used,
                },
            ),
            TaskEventSpec("TASK_STATUS_CHANGED", {"from": current.status, "to": "committed"}),
            TaskEventSpec(
                "TASK_COMMITTED",
                {
                    "commit_id": commit_id,
                    "artifact_version_ids": head_ids,
                    "verification_report_ids": report_ids,
                    "state_hash": state_hash,
                },
            ),
            TaskEventSpec(
                "CONTROL_APPLIED",
                {"kind": command.kind, "applied_task_version": next_version},
                branch_id=branch.branch_id,
                control_event_id=control_event.control_event_id,
                idempotent=True,
            ),
        ]
        return updated, [verified, reply_verified], specs

    def _build_control_update(
        self,
        current: TaskSnapshot,
        command: TaskControlCommand,
        actor_id: str,
    ) -> tuple[TaskSnapshot, list[ArtifactVersion], list[TaskEventSpec]]:
        if current.status in {"committed", "failed", "cancelled"}:
            raise TaskTransitionError("终态任务不能再提交控制命令")
        if current.phase == "contract" and command.kind != "steer":
            raise TaskTransitionError("任务启动前不能提交分支控制命令")
        now = datetime.now(UTC)
        next_version = current.version + 1
        steer_pending = command.kind == "steer"
        control_event = ControlEvent(
            **command.model_dump(),
            control_event_id=f"task_control_{uuid4().hex}",
            task_id=current.task_id,
            actor_id=actor_id,
            status="accepted" if steer_pending else "applied",
            applied_task_version=None if steer_pending else next_version,
            created_at=now,
            applied_at=None if steer_pending else now,
        )
        branches = list(current.branches)
        branch_before: BranchSnapshot | None = None
        branch_after: BranchSnapshot | None = None
        if command.kind != "steer":
            if command.branch_id is None:
                raise TaskTransitionError(f"{command.kind} requires branch_id")
            branch_before = self._branch_by_id(current, command.branch_id)
            next_status: str
            pause_reason: str | None = branch_before.pause_reason
            if command.kind == "pause_branch":
                if branch_before.status not in {
                    "queued",
                    "running",
                    "waiting_evidence",
                    "verifying",
                }:
                    raise TaskTransitionError("当前分支状态不能暂停")
                next_status = "paused"
                pause_reason = command.reason or "用户暂停"
            elif command.kind == "resume_branch":
                if branch_before.status != "paused":
                    raise TaskTransitionError("只有 paused 分支可以恢复")
                has_open_conflict = any(
                    item.branch_id == branch_before.branch_id and item.status == "open"
                    for item in current.conflicts
                )
                next_status = "waiting_evidence" if has_open_conflict else "queued"
                pause_reason = "收入来源口径冲突" if has_open_conflict else None
            elif command.kind == "take_over":
                if branch_before.status in {"committed", "failed", "cancelled"}:
                    raise TaskTransitionError("终态分支不能接管")
                next_status = "taken_over"
                pause_reason = command.reason or "用户接管"
            elif command.kind == "return_control":
                if branch_before.status != "taken_over":
                    raise TaskTransitionError("只有 taken_over 分支可以交还控制权")
                has_open_conflict = any(
                    item.branch_id == branch_before.branch_id and item.status == "open"
                    for item in current.conflicts
                )
                next_status = "waiting_evidence" if has_open_conflict else "queued"
                pause_reason = "收入来源口径冲突" if has_open_conflict else None
            else:
                raise TaskTransitionError(f"不支持的控制命令：{command.kind}")
            branch_after = branch_before.model_copy(
                update={
                    "status": next_status,
                    "version": branch_before.version + 1,
                    "pause_reason": pause_reason,
                    "updated_at": now,
                }
            )
            branches = [
                branch_after if item.branch_id == branch_before.branch_id else item
                for item in current.branches
            ]

        next_status = self._derive_task_status(branches, current.phase)
        updated = self._updated_snapshot(
            current,
            status=next_status,
            branches=branches,
            controls=[*current.controls, control_event],
            updated_at=now,
        )
        specs = [
            TaskEventSpec(
                "CONTROL_ACCEPTED",
                {
                    "kind": command.kind,
                    "expected_task_version": command.expected_task_version,
                },
                branch_id=command.branch_id,
                control_event_id=control_event.control_event_id,
                idempotent=steer_pending,
            )
        ]
        if branch_before is not None and branch_after is not None:
            specs.append(
                TaskEventSpec(
                    "BRANCH_STATUS_CHANGED",
                    {
                        "from": branch_before.status,
                        "to": branch_after.status,
                        "title": branch_before.title,
                    },
                    branch_id=branch_before.branch_id,
                    control_event_id=control_event.control_event_id,
                )
            )
        if current.status != next_status:
            specs.append(
                TaskEventSpec(
                    "TASK_STATUS_CHANGED",
                    {"from": current.status, "to": next_status},
                    control_event_id=control_event.control_event_id,
                )
            )
        if not steer_pending:
            specs.append(
                TaskEventSpec(
                    "CONTROL_APPLIED",
                    {
                        "kind": command.kind,
                        "applied_task_version": next_version,
                        "instruction": command.instruction,
                    },
                    branch_id=command.branch_id,
                    control_event_id=control_event.control_event_id,
                    idempotent=True,
                )
            )
        return updated, [], specs

    @staticmethod
    def _new_artifact(
        current: TaskSnapshot,
        branch: BranchSnapshot,
        deliverable_id: str,
        version: int,
        status: str,
        content: dict[str, Any],
        source_refs: list[str],
        created_at: datetime,
        *,
        artifact_id: str | None = None,
        parent_version_id: str | None = None,
    ) -> ArtifactVersion:
        deliverable = next(
            (
                item
                for item in current.contract.deliverables
                if item.deliverable_id == deliverable_id
            ),
            None,
        )
        if deliverable is None or deliverable_id not in branch.deliverable_ids:
            raise TaskTransitionError("分支引用了未知交付物")
        if not set(source_refs).issubset(set(current.contract.source_scope)):
            raise TaskTransitionError("工件来源超出任务允许范围")
        return ArtifactVersion.model_validate(
            {
                "artifact_version_id": f"task_artifact_ver_{uuid4().hex}",
                "artifact_id": artifact_id or f"task_artifact_{uuid4().hex}",
                "task_id": current.task_id,
                "branch_id": branch.branch_id,
                "deliverable_id": deliverable_id,
                "version": version,
                "parent_version_id": parent_version_id,
                "title": deliverable.title,
                "kind": deliverable.kind,
                "status": status,
                "content": content,
                "content_digest": canonical_hash(content),
                "source_refs": source_refs,
                "created_by": "agent",
                "created_at": created_at,
            }
        )

    @staticmethod
    def _updated_snapshot(current: TaskSnapshot, **updates: Any) -> TaskSnapshot:
        payload = current.model_dump(mode="python")
        payload.update(updates)
        payload["version"] = current.version + 1
        return TaskSnapshot.model_validate(payload)

    @staticmethod
    def _derive_task_status(branches: list[BranchSnapshot], phase: str) -> str:
        if all(branch.status == "committed" for branch in branches):
            return "committed"
        active = [
            branch
            for branch in branches
            if branch.status not in {"committed", "failed", "cancelled"}
        ]
        if any(branch.status == "waiting_evidence" for branch in active):
            return "waiting_input"
        if active and all(branch.status == "paused" for branch in active):
            return "paused"
        if active and all(branch.status == "taken_over" for branch in active):
            return "taken_over"
        if any(branch.status == "verifying" for branch in active):
            return "verifying"
        if phase == "contract" and active and all(branch.status == "queued" for branch in active):
            return "ready"
        if not active and any(branch.status == "failed" for branch in branches):
            return "failed"
        return "running"

    @staticmethod
    def _require_execution_window(
        current: TaskSnapshot,
        *,
        additional_steps: int = 0,
        additional_tool_calls: int = 0,
        additional_runtime_seconds: int = 0,
    ) -> None:
        deadline = current.contract.deadline_at
        if deadline is not None:
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=UTC)
            if datetime.now(UTC) >= deadline:
                raise TaskTransitionError("任务截止时间已到，不能继续执行")

        limit = current.contract.budget
        projected_steps = current.budget.steps_used + additional_steps
        projected_tool_calls = current.budget.tool_calls_used + additional_tool_calls
        projected_runtime = current.budget.runtime_seconds + additional_runtime_seconds
        if projected_steps > limit.max_steps:
            raise TaskTransitionError("任务步骤预算不足，不能继续执行")
        if projected_tool_calls > limit.max_tool_calls:
            raise TaskTransitionError("任务工具调用预算不足，不能继续执行")
        if projected_runtime > limit.max_runtime_seconds:
            raise TaskTransitionError("任务运行时长预算不足，不能继续执行")

    @staticmethod
    def _consume_budget(
        current: TaskSnapshot,
        *,
        additional_steps: int = 0,
        additional_tool_calls: int = 0,
        additional_runtime_seconds: int = 0,
    ) -> TaskBudgetSnapshot:
        limit = current.contract.budget
        steps_used = current.budget.steps_used + additional_steps
        tool_calls_used = current.budget.tool_calls_used + additional_tool_calls
        runtime_seconds = current.budget.runtime_seconds + additional_runtime_seconds
        return current.budget.model_copy(
            update={
                "steps_used": steps_used,
                "tool_calls_used": tool_calls_used,
                "runtime_seconds": runtime_seconds,
                "exhausted": (
                    steps_used >= limit.max_steps
                    or tool_calls_used >= limit.max_tool_calls
                    or runtime_seconds >= limit.max_runtime_seconds
                ),
            }
        )

    @staticmethod
    def _require_version(current: TaskSnapshot, expected_version: int) -> None:
        if current.version != expected_version:
            raise TaskMutationConflictError(
                f"任务版本已变化：期望 v{expected_version}，当前 v{current.version}"
            )

    @staticmethod
    def _branch_for(current: TaskSnapshot, deliverable_id: str) -> BranchSnapshot:
        branch = next(
            (item for item in current.branches if deliverable_id in item.deliverable_ids),
            None,
        )
        if branch is None:
            raise TaskTransitionError(f"缺少交付分支：{deliverable_id}")
        return branch

    @staticmethod
    def _branch_by_id(current: TaskSnapshot, branch_id: str) -> BranchSnapshot:
        branch = next((item for item in current.branches if item.branch_id == branch_id), None)
        if branch is None:
            raise TaskTransitionError("任务中不存在该分支")
        return branch

    async def _idempotent_replay(
        self,
        task_id: str,
        owner_id: str,
        idempotency_key: str,
        command_digest: str,
    ) -> TaskSnapshot | None:
        events = await self.store.load_events(task_id, owner_id, 0)
        for raw_event in events:
            event = TaskEvent.model_validate(raw_event)
            if event.idempotency_key != idempotency_key:
                continue
            if event.payload.get("command_digest") != command_digest:
                raise TaskMutationConflictError("幂等键已用于不同任务命令")
            result_snapshot = event.payload.get("result_snapshot")
            if result_snapshot is not None:
                return TaskSnapshot.model_validate(result_snapshot)
            # Legacy events did not persist the mutation response. Load only after
            # observing the marker so a concurrent PostgreSQL commit cannot yield
            # the snapshot version from before that marker.
            current = await self.get(task_id, owner_id)
            if current.version == event.task_version:
                return current
            raise TaskMutationConflictError("历史幂等记录缺少原响应，无法安全重放")
        return None

    @staticmethod
    def _materialize_events(
        current: TaskSnapshot,
        updated: TaskSnapshot,
        actor_id: str,
        specs: list[TaskEventSpec],
        idempotency_key: str,
        command_digest: str,
    ) -> list[TaskEvent]:
        if sum(spec.idempotent for spec in specs) != 1:
            raise RuntimeError("每次任务 mutation 必须且只能有一个幂等事件")
        events = []
        for offset, spec in enumerate(specs, start=1):
            payload = dict(spec.payload)
            if spec.idempotent:
                payload["command_digest"] = command_digest
                payload["result_snapshot"] = updated.model_dump(mode="json")
            events.append(
                TaskEvent(
                    sequence=current.last_event_sequence + offset,
                    event_id=f"task_evt_{uuid4().hex}",
                    task_id=current.task_id,
                    trace_id=current.trace_id,
                    task_version=updated.version,
                    branch_id=spec.branch_id,
                    artifact_version_id=spec.artifact_version_id,
                    control_event_id=spec.control_event_id,
                    actor_id=actor_id,
                    event_type=spec.event_type,
                    idempotency_key=idempotency_key if spec.idempotent else None,
                    payload=payload,
                    occurred_at=updated.updated_at,
                )
            )
        return events

    async def _commit_mutation(
        self,
        current: TaskSnapshot,
        updated: TaskSnapshot,
        actor_id: str,
        artifacts: list[ArtifactVersion],
        specs: list[TaskEventSpec],
        idempotency_key: str,
        command_digest: str,
    ) -> TaskSnapshot:
        ordered_artifacts = sorted(
            updated.artifact_versions,
            key=lambda item: (item.branch_id, item.deliverable_id, item.version),
        )
        updated = TaskSnapshot.model_validate(
            updated.model_dump(mode="python")
            | {
                "artifact_versions": ordered_artifacts,
                "last_event_sequence": current.last_event_sequence + len(specs),
            }
        )
        events = self._materialize_events(
            current,
            updated,
            actor_id,
            specs,
            idempotency_key,
            command_digest,
        )
        try:
            stored = await self.store.commit(
                current.task_id,
                actor_id,
                current.version,
                updated.model_dump(mode="json"),
                [event.model_dump(mode="json") for event in events],
                [artifact.model_dump(mode="json") for artifact in artifacts],
            )
        except TaskStoreConflictError as exc:
            replay = await self._idempotent_replay(
                current.task_id, actor_id, idempotency_key, command_digest
            )
            if replay is not None:
                return replay
            raise TaskMutationConflictError("任务已在其他端更新，请刷新后重试") from exc
        return self._restore(stored)

    @staticmethod
    def _restore(stored: StoredTask) -> TaskSnapshot:
        payload = stored.snapshot
        if stored.artifact_versions:
            payload = payload | {"artifact_versions": stored.artifact_versions}
        return TaskSnapshot.model_validate(payload)

    @staticmethod
    def _task_id(owner_id: str, idempotency_key: str | None) -> str:
        if idempotency_key is None:
            return f"task_{uuid4().hex}"
        digest = hashlib.sha256(f"{owner_id}:{idempotency_key}".encode()).hexdigest()
        return f"task_{digest[:32]}"

    @staticmethod
    def _draft_from_contract(contract: TaskContract) -> TaskContractDraft:
        return TaskContractDraft.model_validate(
            contract.model_dump(
                exclude={
                    "schema_version",
                    "task_id",
                    "owner_id",
                    "contract_version",
                    "created_at",
                }
            )
        )
