"""Focused PostgreSQL contract checks for the Task Ledger aggregate."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
import pytest

from services.api.app.application.harness_storage import (
    PostgresHarnessStateStore,
    StoredHarnessIdempotency,
    StoredHarnessRun,
)
from services.api.app.application.task_ledger import (
    TaskLedgerConflict,
    TaskLedgerReceipt,
    TaskRecord,
)


DATABASE_DSN = os.getenv("TEST_DATABASE_DSN", "").strip()
pytestmark = pytest.mark.skipif(
    not DATABASE_DSN,
    reason="TEST_DATABASE_DSN is required for Task Ledger PostgreSQL integration",
)


def _task(owner: str, *, version: int = 1, run_id: str | None = None) -> TaskRecord:
    now = datetime.now(timezone.utc)
    return TaskRecord(
        task_id="task-aaaaaaaaaaaa",
        owner_id=owner,
        task_version=version,
        workspace_id="forte-public-office",
        workspace_revision="forte-rev-1",
        current_run_id=run_id or f"harness:{uuid4().hex}",
        run_sequence=version,
        parent_run_id=None,
        created_at=now,
        updated_at=now,
    )


def _run(owner: str, task: TaskRecord, *, run_id: str | None = None, parent_run_id: str | None = None) -> StoredHarnessRun:
    run_id = run_id or task.current_run_id
    return StoredHarnessRun(
        owner_id=owner,
        run_id=run_id,
        snapshot={
            "run_id": run_id,
            "task_id": task.task_id,
            "task_version": task.task_version,
            "run_sequence": task.run_sequence,
            "parent_run_id": parent_run_id,
            "owner_id": owner,
            "version": 1,
        },
    )


def _idem(owner: str, key: str, digest: str, run: StoredHarnessRun) -> StoredHarnessIdempotency:
    return StoredHarnessIdempotency(
        owner_id=owner,
        kind="start",
        idempotency_key=key,
        digest=digest,
        result={"run": run.snapshot},
    )


async def _cleanup(owner: str) -> None:
    async with await psycopg.AsyncConnection.connect(DATABASE_DSN) as connection:
        async with connection.cursor() as cursor:
            for table in (
                "harness_task_ledger_receipt",
                "harness_task_ledger",
                "harness_idempotency",
                "harness_task_commit",
                "harness_artifact_version",
                "harness_run_state",
            ):
                await cursor.execute(f"DELETE FROM {table} WHERE owner_id = %s", (owner,))  # nosec B608


@pytest.mark.asyncio
async def test_task_ledger_initial_and_restart() -> None:
    owner = f"task-ledger-restart-{uuid4().hex}"
    store = PostgresHarnessStateStore(DATABASE_DSN)
    try:
        await store.setup()
        task = _task(owner)
        run = _run(owner, task)
        await store.commit_task_transition(run, task, idempotency=_idem(owner, "ledger-start-0001", "digest-1", run))
        await store.close()

        restored = PostgresHarnessStateStore(DATABASE_DSN)
        await restored.setup()
        assert await restored.get_task_record(owner, task.task_id) == task
        assert [item.run_id for item in await restored.load_runs() if item.owner_id == owner] == [run.run_id]
        await restored.close()
    finally:
        await _cleanup(owner)


@pytest.mark.asyncio
async def test_task_ledger_two_stores_claim_initial_idempotency_before_task_write() -> None:
    """Concurrent initial starts must not leave the losing random Task orphaned."""
    owner = f"task-ledger-initial-race-{uuid4().hex}"
    store_a = PostgresHarnessStateStore(DATABASE_DSN)
    store_b = PostgresHarnessStateStore(DATABASE_DSN)
    try:
        await store_a.setup()
        await store_b.setup()
        task_a = _task(owner)
        task_b = _task(owner)
        run_a = _run(owner, task_a)
        run_b = _run(owner, task_b)
        key = "ledger-initial-race"
        outcomes = await asyncio.gather(
            store_a.commit_task_transition(run_a, task_a, idempotency=_idem(owner, key, "same-digest", run_a)),
            store_b.commit_task_transition(run_b, task_b, idempotency=_idem(owner, key, "same-digest", run_b)),
            return_exceptions=True,
        )
        assert all(not isinstance(item, Exception) for item in outcomes)
        replays = [item for item in outcomes if isinstance(item, StoredHarnessIdempotency)]
        assert len(replays) == 1
        restored = PostgresHarnessStateStore(DATABASE_DSN)
        await restored.setup()
        try:
            tasks = [item for item in await restored.load_task_records() if item.owner_id == owner]
            runs = [item for item in await restored.load_runs() if item.owner_id == owner]
            idempotency = [item for item in await restored.load_idempotency() if item.owner_id == owner]
            assert len(tasks) == 1
            assert len(runs) == 1
            assert len([item for item in idempotency if item.idempotency_key == key]) == 1
            assert replays[0].result["run"]["run_id"] == runs[0].run_id
            assert runs[0].run_id == tasks[0].current_run_id
        finally:
            await restored.close()
    finally:
        await store_a.close()
        await store_b.close()
        await _cleanup(owner)


@pytest.mark.asyncio
async def test_task_ledger_initial_idempotency_digest_conflict_has_no_orphan() -> None:
    owner = f"task-ledger-initial-digest-{uuid4().hex}"
    store_a = PostgresHarnessStateStore(DATABASE_DSN)
    store_b = PostgresHarnessStateStore(DATABASE_DSN)
    try:
        await store_a.setup()
        await store_b.setup()
        task_a = _task(owner)
        task_b = _task(owner)
        run_a = _run(owner, task_a)
        run_b = _run(owner, task_b)
        key = "ledger-initial-digest"
        outcomes = await asyncio.gather(
            store_a.commit_task_transition(run_a, task_a, idempotency=_idem(owner, key, "digest-a", run_a)),
            store_b.commit_task_transition(run_b, task_b, idempotency=_idem(owner, key, "digest-b", run_b)),
            return_exceptions=True,
        )
        assert sum(isinstance(item, TaskLedgerConflict) for item in outcomes) == 1
        restored = PostgresHarnessStateStore(DATABASE_DSN)
        await restored.setup()
        try:
            assert len([item for item in await restored.load_runs() if item.owner_id == owner]) == 1
            assert len([item for item in await restored.load_idempotency() if item.owner_id == owner and item.idempotency_key == key]) == 1
            tasks = [item for item in await restored.load_task_records() if item.owner_id == owner]
            assert len(tasks) == 1
            runs = [item for item in await restored.load_runs() if item.owner_id == owner]
            assert len(runs) == 1
            assert runs[0].run_id == tasks[0].current_run_id
        finally:
            await restored.close()
    finally:
        await store_a.close()
        await store_b.close()
        await _cleanup(owner)


@pytest.mark.asyncio
async def test_task_ledger_sibling_cas_and_same_idempotency_replay() -> None:
    owner = f"task-ledger-race-{uuid4().hex}"
    store = PostgresHarnessStateStore(DATABASE_DSN)
    try:
        await store.setup()
        initial = _task(owner)
        initial_run = _run(owner, initial)
        await store.commit_task_transition(initial_run, initial, idempotency=_idem(owner, "ledger-race-start", "digest-start", initial_run))

        children = [_task(owner, version=2) for _ in range(2)]
        children[1] = children[1].model_copy(update={"current_run_id": f"harness:{uuid4().hex}"})
        child_runs = [_run(owner, child, parent_run_id=initial.current_run_id) for child in children]

        async def transition(child: TaskRecord, child_run: StoredHarnessRun, key: str):
            receipt = TaskLedgerReceipt(
                task_id=child.task_id,
                owner_id=owner,
                idempotency_key=key,
                from_task_version=1,
                to_task_version=2,
                child_run_id=child_run.run_id,
                parent_run_id=initial.current_run_id,
                created_at=datetime.now(timezone.utc),
            )
            return await store.commit_task_transition(
                child_run,
                child,
                expected_task_version=1,
                task_receipt=receipt,
                task_digest=key,
                idempotency=_idem(owner, key, key, child_run),
            )

        outcomes = await asyncio.gather(
            transition(children[0], child_runs[0], "ledger-race-child-1"),
            transition(children[1], child_runs[1], "ledger-race-child-2"),
            return_exceptions=True,
        )
        assert sum(isinstance(item, TaskLedgerConflict) for item in outcomes) == 1
        assert len([item for item in await store.load_runs() if item.owner_id == owner]) == 2

        winner = next(child for child, outcome in zip(child_runs, outcomes, strict=True) if not isinstance(outcome, Exception))
        replay = await store.commit_task_transition(
            winner,
            children[0] if winner is child_runs[0] else children[1],
            expected_task_version=1,
            idempotency=_idem(owner, "ledger-race-child-1" if winner is child_runs[0] else "ledger-race-child-2", "ledger-race-child-1" if winner is child_runs[0] else "ledger-race-child-2", winner),
        )
        assert replay is not None
        with pytest.raises(TaskLedgerConflict):
            await store.commit_task_transition(
                winner,
                children[0] if winner is child_runs[0] else children[1],
                expected_task_version=1,
                idempotency=_idem(owner, replay.idempotency_key, "different-payload", winner),
            )
    finally:
        await store.close()
        await _cleanup(owner)


@pytest.mark.asyncio
async def test_task_ledger_stale_parent_version_rolls_back_continuation() -> None:
    owner = f"task-ledger-parent-cas-{uuid4().hex}"
    store = PostgresHarnessStateStore(DATABASE_DSN)
    try:
        await store.setup()
        initial = _task(owner)
        initial_run = _run(owner, initial)
        await store.commit_task_transition(initial_run, initial)
        before_tasks = await store.load_task_records()
        before_runs = await store.load_runs()
        child = _task(owner, version=2).model_copy(update={"parent_run_id": initial.current_run_id})
        with pytest.raises(TaskLedgerConflict, match="parent Run version"):
            await store.commit_task_transition(
                _run(owner, child, parent_run_id=initial.current_run_id), child,
                expected_task_version=1, expected_parent_run_id=initial.current_run_id,
                expected_parent_version=999,
            )
        assert await store.load_task_records() == before_tasks
        assert await store.load_runs() == before_runs

        malformed_versions = (
            "jsonb_set(snapshot, '{version}', 'null'::jsonb, true)",
            "jsonb_set(snapshot, '{version}', to_jsonb('not-an-integer'::text), true)",
            "snapshot - 'version'",
        )
        for index, expression in enumerate(malformed_versions, start=1):
            async with await psycopg.AsyncConnection.connect(DATABASE_DSN) as connection:
                async with connection.cursor() as cursor:
                    await cursor.execute(
                        f"UPDATE harness_run_state SET snapshot = {expression} "
                        "WHERE owner_id = %s AND run_id = %s",  # nosec B608
                        (owner, initial.current_run_id),
                    )
            before_tasks = await store.load_task_records()
            before_runs = await store.load_runs()
            before_idempotency = await store.load_idempotency()
            malformed_child = _task(owner, version=2)
            malformed_child = malformed_child.model_copy(
                update={"parent_run_id": initial.current_run_id}
            )
            with pytest.raises(TaskLedgerConflict, match="parent Run version"):
                await store.commit_task_transition(
                    _run(owner, malformed_child, parent_run_id=initial.current_run_id),
                    malformed_child,
                    expected_task_version=1,
                    expected_parent_run_id=initial.current_run_id,
                    expected_parent_version=1,
                    idempotency=_idem(
                        owner,
                        f"ledger-malformed-parent-{index}",
                        f"malformed-parent-{index}",
                        _run(owner, malformed_child, parent_run_id=initial.current_run_id),
                    ),
                )
            assert await store.load_task_records() == before_tasks
            assert await store.load_runs() == before_runs
            assert await store.load_idempotency() == before_idempotency
    finally:
        await store.close()
        await _cleanup(owner)


@pytest.mark.asyncio
async def test_task_ledger_transaction_rollback_leaves_no_orphan() -> None:
    owner = f"task-ledger-rollback-{uuid4().hex}"
    store = PostgresHarnessStateStore(DATABASE_DSN)
    try:
        await store.setup()
        initial = _task(owner)
        initial_run = _run(owner, initial)
        await store.commit_task_transition(initial_run, initial)
        child = _task(owner, version=2)
        with pytest.raises(TaskLedgerConflict, match="run_id"):
            await store.commit_task_transition(
                _run(owner, child, run_id=initial_run.run_id, parent_run_id=initial.current_run_id),
                child,
                expected_task_version=1,
                idempotency=_idem(owner, "ledger-rollback-child", "rollback", initial_run),
            )
        assert (await store.get_task_record(owner, initial.task_id)).task_version == 1
        assert len([item for item in await store.load_runs() if item.owner_id == owner]) == 1
        assert not [item for item in await store.load_idempotency() if item.owner_id == owner and item.idempotency_key == "ledger-rollback-child"]
    finally:
        await store.close()
        await _cleanup(owner)


@pytest.mark.asyncio
async def test_task_ledger_current_and_lineage_survive_restart() -> None:
    owner = f"task-ledger-lineage-{uuid4().hex}"
    store = PostgresHarnessStateStore(DATABASE_DSN)
    try:
        await store.setup()
        initial = _task(owner)
        initial_run = _run(owner, initial)
        await store.commit_task_transition(initial_run, initial)
        child = _task(owner, version=2)
        child = child.model_copy(update={"parent_run_id": initial.current_run_id})
        child_run = _run(owner, child, parent_run_id=initial.current_run_id)
        await store.commit_task_transition(
            child_run,
            child,
            expected_task_version=1,
            task_receipt=TaskLedgerReceipt(
                task_id=child.task_id,
                owner_id=owner,
                idempotency_key="ledger-lineage-child",
                from_task_version=1,
                to_task_version=2,
                child_run_id=child_run.run_id,
                parent_run_id=initial.current_run_id,
                created_at=datetime.now(timezone.utc),
            ),
            task_digest="lineage-child",
            expected_parent_run_id=initial.current_run_id,
            expected_parent_version=1,
        )
        await store.close()
        restored = PostgresHarnessStateStore(DATABASE_DSN)
        await restored.setup()
        current = await restored.get_task_record(owner, initial.task_id)
        assert current is not None and current.current_run_id == child_run.run_id and current.run_sequence == 2
        assert [item.run_id for item in await restored.load_runs() if item.owner_id == owner] == [initial_run.run_id, child_run.run_id]
        await restored.close()
    finally:
        await _cleanup(owner)
