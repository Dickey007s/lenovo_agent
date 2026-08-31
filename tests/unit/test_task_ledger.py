"""Task-ledger V1 contract tests.

These tests exercise the aggregate boundary used by HarnessRuntime rather
than treating the task index as a second best-effort database.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx
import pytest
from pydantic import ValidationError

from services.api.app.api.harness_routes import get_harness_runtime
from services.api.app.application.harness_runtime import (
    AgentControlLoopControlRequest,
    HarnessContinuationRequest,
    HarnessConflictError,
    HarnessError,
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
from tests.unit.test_harness_runtime import wait_status, wait_terminal


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


async def _stopped_parent(runtime: HarnessRuntime, owner: str, key: str):
    started = await runtime.start(
        owner,
        HarnessRunStart(
            idempotency_key=key,
            instruction="读取批准资料并保留任务时间线",
        ),
    )
    waiting = await wait_status(runtime, owner, started.run.run_id, "waiting_input")
    await runtime.control(
        owner,
        started.run.run_id,
        AgentControlLoopControlRequest(command="stop", idempotency_key=f"{key}-stop", expected_version=waiting.version),
    )
    return await wait_terminal(runtime, owner, started.run.run_id)


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
async def test_task_get_reads_persisted_current_child_across_runtime_instances() -> None:
    owner = "ledger-cross-runtime-owner"
    store = InMemoryHarnessStateStore()
    writer = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst(), state_store=store)
    reader = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst(), state_store=store)
    try:
        parent = await _stopped_parent(writer, owner, "ledger-cross-runtime-start-0001")
        branch = next(item for item in parent.branches if item.status != "completed")
        child = await writer.continue_unfinished_task(
            owner, parent.run_id, branch.branch_id,
            idempotency_key="ledger-cross-runtime-child-0001",
            expected_version=parent.version, expected_task_version=parent.task_version,
        )
        task = await reader.get_task(owner, parent.task_id)
        assert task.current_run_id == child.run.run_id
        assert task.task_version == child.run.task_version
    finally:
        await reader.close()
        await writer.close()


@pytest.mark.asyncio
async def test_task_endpoint_reads_persisted_current_run_when_process_cache_is_missing() -> None:
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
        assert response.status_code == 200
        assert response.json()["current_run_id"] == started.run.run_id
    finally:
        app.dependency_overrides.clear()
        await runtime.close()


@pytest.mark.asyncio
async def test_task_endpoint_fails_closed_when_task_store_read_raises() -> None:
    owner = "ledger-store-error-owner"
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst())
    started = await runtime.start(
        owner,
        HarnessRunStart(
            idempotency_key="ledger-store-error-start-0001",
            instruction="读取批准资料并保留任务时间线",
            loop={"max_rounds": 1, "max_files_per_round": 1, "max_model_calls": 2, "deadline_seconds": 60},
        ),
    )
    async def broken_task_read(owner_id: str, task_id: str):
        raise ValueError("database unavailable")

    runtime.state_store.get_task_aggregate = broken_task_read  # type: ignore[method-assign]
    app = create_app()
    app.dependency_overrides[get_harness_runtime] = lambda: runtime
    try:
        with pytest.raises(Exception, match="台账 Run 读取"):
            await runtime.get_task(owner, started.run.task_id)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                f"/v1/harness/tasks/{started.run.task_id}", headers={"X-User-Id": owner}
            )
        assert response.status_code == 503
    finally:
        app.dependency_overrides.clear()
        await runtime.close()


@pytest.mark.asyncio
async def test_task_get_does_not_backfill_when_legacy_run_has_no_task_record() -> None:
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst())
    started = await runtime.start(
        "ledger-no-backfill-owner",
        HarnessRunStart(
            idempotency_key="ledger-no-backfill-start-0001",
            instruction="读取批准资料并保留任务时间线",
            loop={"max_rounds": 1, "max_files_per_round": 1, "max_model_calls": 2, "deadline_seconds": 60},
        ),
    )
    try:
        async with runtime._lock:
            runtime.state_store._tasks.pop(("ledger-no-backfill-owner", started.run.task_id), None)
        with pytest.raises(Exception, match="台账"):
            await runtime.get_task("ledger-no-backfill-owner", started.run.task_id)
        assert await runtime.state_store.get_task_record("ledger-no-backfill-owner", started.run.task_id) is None
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_continuation_requires_explicit_task_version() -> None:
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst())
    started = await runtime.start(
        "ledger-version-owner",
        HarnessRunStart(
            idempotency_key="ledger-version-start-0001",
            instruction="读取批准资料并保留任务时间线",
            loop={"max_rounds": 1, "max_files_per_round": 1, "max_model_calls": 2, "deadline_seconds": 60},
        ),
    )
    try:
        with pytest.raises(TypeError):
            await runtime.continue_unfinished_task(
                "ledger-version-owner",
                started.run.run_id,
                "branch-aaaaaaaaaaaa",
                idempotency_key="ledger-version-child-0001",
                expected_version=started.run.version,
            )
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_runtime_sibling_cas_replay_and_stale_inputs_are_atomic() -> None:
    owner = "ledger-sibling-owner"
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst())
    try:
        parent = await _stopped_parent(runtime, owner, "ledger-sibling-start-0001")
        branch = next(item for item in parent.branches if item.status != "completed")
        parent_before = parent.model_dump_json()
        key_a = "ledger-sibling-child-a"
        key_b = "ledger-sibling-child-b"
        instruction_a = "第一份续办"
        instruction_b = "第二份续办"

        async def continue_with(key: str, instruction: str):
            try:
                return await runtime.continue_unfinished_task(
                    owner, parent.run_id, branch.branch_id,
                    idempotency_key=key, expected_version=parent.version,
                    expected_task_version=parent.task_version, instruction=instruction,
                )
            except HarnessConflictError as exc:
                return exc

        outcomes = await asyncio.gather(
            continue_with(key_a, instruction_a), continue_with(key_b, instruction_b)
        )
        winners = [item for item in outcomes if not isinstance(item, HarnessConflictError)]
        assert len(winners) == 1
        winner = winners[0]
        child = winner.run
        assert sum(isinstance(item, HarnessConflictError) for item in outcomes) == 1
        assert (await runtime.get(owner, parent.run_id)).model_dump_json() == parent_before
        runs = [item for item in await runtime.state_store.load_runs() if item.owner_id == owner]
        assert len(runs) == 2
        task = await runtime.state_store.get_task_record(owner, parent.task_id)
        assert task is not None and task.current_run_id == child.run_id

        replay = await runtime.continue_unfinished_task(
            owner, parent.run_id, branch.branch_id,
            idempotency_key=key_a if outcomes[0] is winner else key_b,
            expected_version=parent.version, expected_task_version=parent.task_version,
            instruction=instruction_a if outcomes[0] is winner else instruction_b,
        )
        assert replay.run.run_id == child.run_id
        assert len([item for item in await runtime.state_store.load_runs() if item.owner_id == owner]) == 2

        for call in (
            dict(idempotency_key="ledger-sibling-different", expected_task_version=parent.task_version, instruction="冲突内容"),
            dict(idempotency_key=key_a if outcomes[0] is winner else key_b, expected_task_version=2, instruction="冲突内容"),
        ):
            with pytest.raises(HarnessConflictError):
                await runtime.continue_unfinished_task(
                    owner, parent.run_id, branch.branch_id,
                    expected_version=parent.version, **call,
                )
        with pytest.raises(HarnessError):
            await runtime.continue_unfinished_task(
                owner, child.run_id, branch.branch_id, idempotency_key="ledger-stale-run",
                expected_version=parent.version, expected_task_version=parent.task_version,
            )
        with pytest.raises(HarnessConflictError):
            await runtime.continue_unfinished_task(
                owner, parent.run_id, branch.branch_id, idempotency_key="ledger-stale-task",
                expected_version=parent.version, expected_task_version=99,
            )
        with pytest.raises(HarnessConflictError):
            await runtime.continue_unfinished_task(
                owner, parent.run_id, branch.branch_id, idempotency_key="ledger-historical",
                expected_version=parent.version, expected_task_version=2,
            )
        with pytest.raises(HarnessError):
            await runtime.continue_unfinished_task(
                "other-owner", parent.run_id, branch.branch_id, idempotency_key="ledger-owner",
                expected_version=parent.version, expected_task_version=parent.task_version,
            )
        assert len([item for item in await runtime.state_store.load_runs() if item.owner_id == owner]) == 2
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_http_task_ledger_validation_and_continuation_failure_are_503_or_422() -> None:
    owner = "ledger-http-owner"
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst())
    parent = await _stopped_parent(runtime, owner, "ledger-http-start-0001")
    branch = next(item for item in parent.branches if item.status != "completed")
    app = create_app()
    app.dependency_overrides[get_harness_runtime] = lambda: runtime
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            missing = await client.post(
                f"/v1/harness/runs/{parent.run_id}/continue", headers={"X-User-Id": owner},
                json={"branch_id": branch.branch_id, "idempotency_key": "ledger-http-missing", "expected_version": parent.version},
            )
            assert missing.status_code == 422
            task_record = await runtime.state_store.get_task_record(owner, parent.task_id)
            assert task_record is not None
            runtime.state_store._tasks.pop((owner, parent.task_id), None)
            missing_task = await client.get(f"/v1/harness/tasks/{parent.task_id}", headers={"X-User-Id": owner})
            assert missing_task.status_code == 503
            runtime.state_store._tasks[(owner, parent.task_id)] = task_record
            async def fail_commit(*args, **kwargs):
                raise HarnessError("aggregate unavailable")
            runtime.state_store.commit_task_transition = fail_commit  # type: ignore[method-assign]
            before_runs = await runtime.state_store.load_runs()
            before_idempotency = await runtime.state_store.load_idempotency()
            failed = await client.post(
                f"/v1/harness/runs/{parent.run_id}/continue", headers={"X-User-Id": owner},
                json={"branch_id": branch.branch_id, "idempotency_key": "ledger-http-failure", "expected_version": parent.version, "expected_task_version": parent.task_version},
            )
            assert failed.status_code == 503
            assert await runtime.state_store.load_runs() == before_runs
            assert await runtime.state_store.load_idempotency() == before_idempotency
    finally:
        app.dependency_overrides.clear()
        await runtime.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["duplicate_sequence", "broken_parent", "pointer_mismatch", "root_parent"])
async def test_setup_rejects_broken_task_lineage_without_backfill(case: str) -> None:
    owner = f"ledger-setup-{case}"
    store = InMemoryHarnessStateStore()
    first = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst(), state_store=store)
    parent = await _stopped_parent(first, owner, f"ledger-setup-start-{case}")
    try:
        if case == "pointer_mismatch":
            task = await store.get_task_record(owner, parent.task_id)
            assert task is not None
            store._tasks[(owner, parent.task_id)] = task.model_copy(update={"current_run_id": "harness:ffffffffffffffffffffffffffffffff"})
        elif case == "root_parent":
            stored = store._runs[(owner, parent.run_id)]
            snapshot = dict(stored.snapshot)
            snapshot["parent_run_id"] = "harness:ffffffffffffffffffffffffffffffff"
            store._runs[(owner, parent.run_id)] = StoredHarnessRun(owner_id=owner, run_id=parent.run_id, snapshot=snapshot, resume_status=stored.resume_status)
        else:
            stored = store._runs[(owner, parent.run_id)]
            snapshot = dict(stored.snapshot)
            run_id = "harness:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
            snapshot.update({"run_id": run_id, "version": 1, "run_sequence": 1 if case == "duplicate_sequence" else 2, "task_version": 1 if case == "duplicate_sequence" else 2, "parent_run_id": None if case == "duplicate_sequence" else "harness:ffffffffffffffffffffffffffffffff"})
            store._runs[(owner, run_id)] = StoredHarnessRun(owner_id=owner, run_id=run_id, snapshot=snapshot, resume_status=stored.resume_status)
        restored = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst(), state_store=store)
        with pytest.raises(HarnessError):
            await restored.setup()
        await restored.close()
    finally:
        await first.close()


@pytest.mark.asyncio
async def test_task_lineage_truncates_101_runs_but_keeps_current() -> None:
    owner = "ledger-lineage-101"
    store = InMemoryHarnessStateStore()
    first = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst(), state_store=store)
    parent = await _stopped_parent(first, owner, "ledger-lineage-101-start")
    try:
        previous = parent.run_id
        latest = parent.run_id
        for sequence in range(2, 102):
            run_id = f"harness:{sequence:032x}"
            stored = store._runs[(owner, parent.run_id)]
            snapshot = dict(stored.snapshot)
            snapshot.update({"run_id": run_id, "version": 1, "run_sequence": sequence, "task_version": sequence, "parent_run_id": previous})
            store._runs[(owner, run_id)] = StoredHarnessRun(owner_id=owner, run_id=run_id, snapshot=snapshot, resume_status=stored.resume_status)
            previous = run_id
            latest = run_id
        task = await store.get_task_record(owner, parent.task_id)
        assert task is not None
        store._tasks[(owner, parent.task_id)] = task.model_copy(update={"current_run_id": latest, "task_version": 101, "run_sequence": 101, "parent_run_id": f"harness:{100:032x}"})
        restored = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst(), state_store=store)
        await restored.setup()
        payload = await restored.get_task(owner, parent.task_id)
        assert payload.lineage_total == 101
        assert payload.lineage_truncated is True
        assert len(payload.lineage) == 100
        assert payload.lineage[-1].run_id == latest
        await restored.close()
    finally:
        await first.close()


@pytest.mark.asyncio
async def test_setup_is_the_only_legacy_task_backfill_point() -> None:
    store = InMemoryHarnessStateStore()
    first = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst(), state_store=store)
    started = await first.start(
        "legacy-setup-owner",
        HarnessRunStart(
            idempotency_key="legacy-setup-start-0001",
            instruction="读取批准资料并保留任务时间线",
            loop={"max_rounds": 1, "max_files_per_round": 1, "max_model_calls": 2, "deadline_seconds": 60},
        ),
    )
    try:
        async with store._lock:
            store._tasks.pop(("legacy-setup-owner", started.run.task_id), None)
            stored = store._runs[("legacy-setup-owner", started.run.run_id)]
            legacy_snapshot = dict(stored.snapshot)
            legacy_snapshot.pop("task_version", None)
            store._runs[("legacy-setup-owner", started.run.run_id)] = StoredHarnessRun(
                owner_id=stored.owner_id,
                run_id=stored.run_id,
                snapshot=legacy_snapshot,
                resume_status=stored.resume_status,
            )
        restored = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst(), state_store=store)
        await restored.setup()
        task = await store.get_task_record("legacy-setup-owner", started.run.task_id)
        assert task is not None
        assert task.task_version == started.run.run_sequence
        assert (await restored.get("legacy-setup-owner", started.run.run_id)).task_version == started.run.run_sequence
        await restored.close()
    finally:
        await first.close()


@pytest.mark.asyncio
async def test_legacy_backfill_rejects_root_with_parent() -> None:
    store = InMemoryHarnessStateStore()
    first = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst(), state_store=store)
    started = await first.start(
        "legacy-root-owner",
        HarnessRunStart(
            idempotency_key="legacy-root-start-0001",
            instruction="读取批准资料并保留任务时间线",
        ),
    )
    try:
        async with store._lock:
            store._tasks.pop(("legacy-root-owner", started.run.task_id), None)
            stored = store._runs[("legacy-root-owner", started.run.run_id)]
            legacy_snapshot = dict(stored.snapshot)
            legacy_snapshot.pop("task_version", None)
            legacy_snapshot["parent_run_id"] = "harness:ffffffffffffffffffffffffffffffff"
            store._runs[("legacy-root-owner", started.run.run_id)] = StoredHarnessRun(
                owner_id=stored.owner_id,
                run_id=stored.run_id,
                snapshot=legacy_snapshot,
                resume_status=stored.resume_status,
            )
        restored = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst(), state_store=store)
        with pytest.raises(HarnessError, match="根节点"):
            await restored.setup()
        assert await store.get_task_record("legacy-root-owner", started.run.task_id) is None
        await restored.close()
    finally:
        await first.close()


def test_task_record_rejects_unsanitized_or_invalid_identity() -> None:
    with pytest.raises(ValidationError):
        _task(run_id="not-a-run")
