"""Task-ledger V1 contract tests.

These tests exercise the aggregate boundary used by HarnessRuntime rather
than treating the task index as a second best-effort database.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
from pydantic import ValidationError

from services.api.app.api.harness_routes import get_harness_runtime
from services.api.app.application.harness_runtime import (
    HarnessContinuationRequest,
    HarnessRunStart,
    HarnessRuntime,
)
from services.api.app.application.harness_storage import (
    InMemoryHarnessStateStore,
    StoredHarnessIdempotency,
    StoredHarnessRun,
)
from services.api.app.application.task_ledger import TaskLedgerConflict, TaskRecord
from services.api.app.main import create_app
from tests.unit.test_harness_runtime import FakeAnalyst, FakeCatalog, FakePlanner


def _task(*, task_version: int = 1, run_id: str = "harness:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa") -> TaskRecord:
    now = datetime.now(timezone.utc)
    return TaskRecord(
        task_id="task-aaaaaaaaaaaa",
        owner_id="ledger-owner",
        task_version=task_version,
        workspace_id="forte-public-office",
        workspace_revision="forte-rev-1",
        current_run_id=run_id,
        run_sequence=task_version,
        created_at=now,
        updated_at=now,
    )


def _stored_run(run_id: str) -> StoredHarnessRun:
    return StoredHarnessRun(
        owner_id="ledger-owner",
        run_id=run_id,
        snapshot={"run_id": run_id, "task_id": "task-aaaaaaaaaaaa"},
    )


def _idem(key: str, run_id: str) -> StoredHarnessIdempotency:
    return StoredHarnessIdempotency(
        owner_id="ledger-owner",
        kind="start",
        idempotency_key=key,
        digest=f"digest-{key}",
        result={"run": {"run_id": run_id}},
    )


@pytest.mark.asyncio
async def test_initial_and_cas_failure_leave_no_orphan_run_or_receipt() -> None:
    store = InMemoryHarnessStateStore()
    await store.setup()
    first = _stored_run("harness:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    task = _task()
    await store.commit_task_transition(first, task, idempotency=_idem("start-0001", first.run_id))

    child = _stored_run("harness:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
    with pytest.raises(TaskLedgerConflict, match="CAS"):
        await store.commit_task_transition(
            child,
            _task(task_version=2, run_id=child.run_id),
            expected_task_version=99,
            idempotency=_idem("continue-0001", child.run_id),
        )

    assert [item.run_id for item in await store.load_runs()] == [first.run_id]
    assert await store.get_task_record("ledger-owner", task.task_id) == task
    assert [item.idempotency_key for item in await store.load_idempotency()] == ["start-0001"]


@pytest.mark.asyncio
async def test_task_id_collision_is_rejected_before_new_run_or_idempotency() -> None:
    store = InMemoryHarnessStateStore()
    await store.commit_task_transition(
        _stored_run("harness:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
        _task(),
        idempotency=_idem("start-0001", "harness:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
    )
    second = _stored_run("harness:cccccccccccccccccccccccccccccccc")
    with pytest.raises(TaskLedgerConflict, match="identity"):
        await store.commit_task_transition(
            second,
            _task(run_id=second.run_id),
            idempotency=_idem("start-0002", second.run_id),
        )
    assert [item.run_id for item in await store.load_runs()] == [
        "harness:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    ]
    assert [item.idempotency_key for item in await store.load_idempotency()] == ["start-0001"]


@pytest.mark.asyncio
async def test_run_id_collision_is_rejected_without_overwriting_snapshot() -> None:
    store = InMemoryHarnessStateStore()
    run = _stored_run("harness:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    task = _task()
    await store.commit_task_transition(run, task, idempotency=_idem("start-0001", run.run_id))
    with pytest.raises(TaskLedgerConflict, match="run_id"):
        await store.commit_task_transition(
            run,
            task,
            idempotency=_idem("start-0002", run.run_id),
        )
    assert [item.idempotency_key for item in await store.load_idempotency()] == ["start-0001"]


def test_public_continuation_requires_task_version_and_sanitizes_owner() -> None:
    schema = HarnessContinuationRequest.model_json_schema()
    assert "expected_task_version" in schema["required"]


@pytest.mark.asyncio
async def test_task_endpoint_is_owner_scoped_and_does_not_expose_owner_id() -> None:
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst())
    task_instruction = "读取批准资料并保留任务时间线"
    started = await runtime.start(
        "ledger-owner",
        HarnessRunStart(
            idempotency_key="ledger-endpoint-start-0001",
            instruction=task_instruction,
            loop={"max_rounds": 1, "max_files_per_round": 1, "max_model_calls": 2, "deadline_seconds": 60},
        ),
    )
    task_id = started.run.task_id
    app = create_app()
    app.dependency_overrides[get_harness_runtime] = lambda: runtime
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                f"/v1/harness/tasks/{task_id}",
                headers={"X-User-Id": "ledger-owner"},
            )
            forbidden = await client.get(
                f"/v1/harness/tasks/{task_id}",
                headers={"X-User-Id": "other-owner"},
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["task_id"] == task_id
        assert payload["task_version"] == 1
        assert "owner_id" not in payload
        assert forbidden.status_code == 404
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_task_endpoint_derives_current_run_and_lineage_from_runtime_start() -> None:
    owner = "ledger-runtime-owner"
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst())
    started = await runtime.start(
        owner,
        HarnessRunStart(
            idempotency_key="ledger-runtime-start-0001",
            instruction="读取批准资料并保留任务时间线",
            loop={"max_rounds": 1, "max_files_per_round": 1, "max_model_calls": 2, "deadline_seconds": 60},
        ),
    )
    app = create_app()
    app.dependency_overrides[get_harness_runtime] = lambda: runtime
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                f"/v1/harness/tasks/{started.run.task_id}",
                headers={"X-User-Id": owner},
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["current_run_id"] == started.run.run_id
        assert payload["lineage"][0]["run_id"] == started.run.run_id
        assert payload["lineage_total"] == 1
        assert "owner_id" not in payload
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_task_endpoint_fails_closed_when_current_run_pointer_is_missing() -> None:
    owner = "ledger-integrity-owner"
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst())
    started = await runtime.start(
        owner,
        HarnessRunStart(
            idempotency_key="ledger-integrity-start-0001",
            instruction="读取批准资料并保留任务时间线",
            loop={"max_rounds": 1, "max_files_per_round": 1, "max_model_calls": 2, "deadline_seconds": 60},
        ),
    )
    app = create_app()
    app.dependency_overrides[get_harness_runtime] = lambda: runtime
    try:
        async with runtime._lock:
            runtime._runs.pop((owner, started.run.run_id))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                f"/v1/harness/tasks/{started.run.task_id}",
                headers={"X-User-Id": owner},
            )
        assert response.status_code == 503
    finally:
        app.dependency_overrides.clear()
        await runtime.close()


def test_task_record_rejects_unsanitized_or_invalid_identity() -> None:
    with pytest.raises(ValidationError):
        _task(run_id="not-a-run")
