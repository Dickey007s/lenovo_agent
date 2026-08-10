from __future__ import annotations

import asyncio
import hashlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from time import monotonic
from uuid import uuid4

from packages.contracts import (
    BranchSnapshot,
    DeliverableSpec,
    TaskBudget,
    TaskContract,
    TaskContractDraft,
    TaskEvent,
    TaskSnapshot,
)
from packages.contracts.hashing import canonical_hash
from services.api.app.application.task_storage import (
    StoredTask,
    TaskStore,
    TaskStoreConflictError,
)


class TaskNotFoundError(LookupError):
    pass


class TaskCreateConflictError(RuntimeError):
    pass


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
        deadline_at=datetime(2026, 8, 10, 10, 0, tzinfo=UTC),
    )


class TaskService:
    def __init__(self, store: TaskStore, poll_interval_seconds: float = 0.5) -> None:
        self.store = store
        self.poll_interval_seconds = poll_interval_seconds

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
            await self.store.create(
                snapshot.model_dump(mode="json"), event.model_dump(mode="json")
            )
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

    async def create_demo1(self, owner_id: str) -> TaskSnapshot:
        return await self.create(
            demo1_contract_draft(),
            owner_id,
            idempotency_key=f"demo1-customer-a:{owner_id}",
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
