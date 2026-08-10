from copy import deepcopy

import pytest

from services.api.app.application.task_storage import InMemoryTaskStore
from services.api.app.application.tasks import (
    TaskCreateConflictError,
    TaskNotFoundError,
    TaskService,
    demo1_contract_draft,
)


async def test_demo1_task_creation_is_server_owned_and_traceable() -> None:
    service = TaskService(InMemoryTaskStore(), poll_interval_seconds=0)
    snapshot = await service.create_demo1("user_1")

    assert snapshot.owner_id == "user_1"
    assert snapshot.contract.title == "客户 A 经营汇报"
    assert snapshot.status == "ready"
    assert snapshot.phase == "contract"
    assert snapshot.version == 1
    assert snapshot.last_event_sequence == 1
    assert len(snapshot.branches) == 3
    assert {item.status for item in snapshot.branches} == {"queued"}
    assert {
        item.deliverable_id for item in snapshot.contract.deliverables
    } == {"operating-analysis", "risk-brief", "reply-draft"}

    events = await service.history(snapshot.task_id, "user_1")
    assert [event.event_type for event in events] == ["TASK_CREATED"]
    assert events[0].payload["contract_digest"].startswith("sha256:")


async def test_create_is_idempotent_and_rejects_key_reuse_for_another_contract() -> None:
    store = InMemoryTaskStore()
    service = TaskService(store)
    draft = demo1_contract_draft()

    first = await service.create(draft, "user_1", idempotency_key="create-task-001")
    second = await service.create(draft, "user_1", idempotency_key="create-task-001")
    assert second == first
    assert len(await service.history(first.task_id, "user_1")) == 1

    changed = draft.model_copy(update={"objective": "A different objective."})
    with pytest.raises(TaskCreateConflictError, match="幂等键"):
        await service.create(changed, "user_1", idempotency_key="create-task-001")


async def test_task_store_is_owner_scoped_and_returns_defensive_copies() -> None:
    store = InMemoryTaskStore()
    service = TaskService(store)
    snapshot = await service.create_demo1("user_1")

    stored = await store.load(snapshot.task_id, "user_1")
    assert stored is not None
    changed = deepcopy(stored.snapshot)
    changed["status"] = "committed"
    stored.snapshot["status"] = "failed"

    restored = await service.get(snapshot.task_id, "user_1")
    assert restored.status == "ready"
    assert changed["status"] == "committed"
    assert await service.list("user_2") == []
    with pytest.raises(TaskNotFoundError):
        await service.get(snapshot.task_id, "user_2")


async def test_new_service_instance_recovers_same_snapshot_and_event_cursor() -> None:
    store = InMemoryTaskStore()
    first_service = TaskService(store)
    created = await first_service.create_demo1("user_1")

    restored_service = TaskService(store, poll_interval_seconds=0)
    restored = await restored_service.get(created.task_id, "user_1")
    assert restored == created
    assert await restored_service.history(created.task_id, "user_1", after_sequence=1) == []

    stream = restored_service.event_stream(
        created.task_id, "user_1", after_sequence=0, heartbeat_seconds=0
    )
    first_event = await anext(stream)
    assert first_event is not None
    assert first_event.sequence == 1
    await stream.aclose()

    heartbeat_stream = restored_service.event_stream(
        created.task_id, "user_1", after_sequence=1, heartbeat_seconds=0
    )
    assert await anext(heartbeat_stream) is None
    await heartbeat_stream.aclose()
