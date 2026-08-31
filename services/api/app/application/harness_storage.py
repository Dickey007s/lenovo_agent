"""Durable state and append-only result storage for the Agent Control Loop.

The runtime remains the state-machine owner. This adapter only makes accepted
snapshots, idempotency receipts, artifact versions and task commits survive
process restarts.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import psycopg
from psycopg.types.json import Jsonb
from services.api.app.application.task_ledger import (
    TaskLedgerConflict,
    TaskLedgerReceipt,
    TaskRecord,
)
from services.api.app.application.workunit_ledger import (
    ContributionRecord,
    WorkUnitRecord,
    contribution_digest,
)


IdempotencyKind = Literal["start", "control"]


def _clone(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _validate_ledger_append(previous: dict[str, Any] | None, current: dict[str, Any]) -> None:
    """Reject deletion or mutation of immutable Contribution rows at storage boundary."""
    if previous is None:
        return
    old_rows = {str(item.get("contribution_id")): item for item in previous.get("contributions", [])}
    new_rows = {str(item.get("contribution_id")): item for item in current.get("contributions", [])}
    if not old_rows.keys() <= new_rows.keys():
        raise RuntimeError("append-only Contribution Ledger cannot delete rows")
    for key, old in old_rows.items():
        if old != new_rows[key]:
            raise RuntimeError("immutable Contribution conflict")
    attempts: set[tuple[str, int]] = set()
    for row in new_rows.values():
        attempt_key = (str(row.get("work_unit_id")), int(row.get("attempt", 0)))
        if attempt_key in attempts:
            raise RuntimeError("duplicate WorkUnit contribution attempt")
        attempts.add(attempt_key)
    old_units = {str(item.get("work_unit_id")): item for item in previous.get("work_units", [])}
    new_units = {str(item.get("work_unit_id")): item for item in current.get("work_units", [])}
    for key, old in old_units.items():
        new = new_units.get(key)
        if new is None or int(new.get("version", 0)) < int(old.get("version", 0)):
            raise RuntimeError("WorkUnit version cannot move backwards")
        if new != old and int(new.get("version", 0)) == int(old.get("version", 0)):
            raise RuntimeError("WorkUnit version CAS failed")


@dataclass(frozen=True)
class StoredHarnessRun:
    owner_id: str
    run_id: str
    snapshot: dict[str, Any]
    resume_status: str | None = None


@dataclass(frozen=True)
class StoredHarnessIdempotency:
    owner_id: str
    kind: IdempotencyKind
    idempotency_key: str
    digest: str
    result: dict[str, Any]


@dataclass(frozen=True)
class StoredHarnessArtifactVersion:
    owner_id: str
    run_id: str
    artifact_id: str
    version: int
    payload_digest: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class StoredHarnessTaskCommit:
    owner_id: str
    run_id: str
    commit_id: str
    payload_digest: str
    payload: dict[str, Any]


class HarnessStateStore(Protocol):
    backend_name: str

    async def setup(self) -> None: ...

    async def close(self) -> None: ...

    async def load_runs(self) -> list[StoredHarnessRun]: ...

    async def load_idempotency(self) -> list[StoredHarnessIdempotency]: ...

    async def load_artifact_versions(
        self, owner_id: str, run_id: str
    ) -> list[StoredHarnessArtifactVersion]: ...

    async def load_task_commits(
        self, owner_id: str, run_id: str
    ) -> list[StoredHarnessTaskCommit]: ...

    async def load_work_units(self, owner_id: str, run_id: str) -> list[WorkUnitRecord]: ...

    async def load_contributions(self, owner_id: str, run_id: str) -> list[ContributionRecord]: ...

    async def commit(
        self,
        run: StoredHarnessRun,
        idempotency: StoredHarnessIdempotency | None = None,
        artifact_version: StoredHarnessArtifactVersion | None = None,
        task_commit: StoredHarnessTaskCommit | None = None,
    ) -> StoredHarnessIdempotency | None: ...

    async def load_task_records(self) -> list[TaskRecord]: ...

    async def get_task_record(self, owner_id: str, task_id: str) -> TaskRecord | None: ...

    async def get_task_aggregate(
        self, owner_id: str, task_id: str
    ) -> tuple[TaskRecord | None, list[StoredHarnessRun]]: ...

    async def create_task_record(self, task: TaskRecord) -> TaskRecord: ...

    async def commit_task_transition(
        self,
        run: StoredHarnessRun,
        task: TaskRecord,
        *,
        expected_task_version: int | None = None,
        expected_parent_run_id: str | None = None,
        expected_parent_version: int | None = None,
        task_receipt: TaskLedgerReceipt | None = None,
        task_digest: str | None = None,
        idempotency: StoredHarnessIdempotency | None = None,
    ) -> StoredHarnessIdempotency | None: ...


class InMemoryHarnessStateStore:
    """Process-local adapter that also supports restart tests via shared instances."""

    backend_name = "memory"

    def __init__(self) -> None:
        self._runs: dict[tuple[str, str], StoredHarnessRun] = {}
        self._idempotency: dict[
            tuple[str, IdempotencyKind, str], StoredHarnessIdempotency
        ] = {}
        self._artifact_versions: dict[
            tuple[str, str, str, int], StoredHarnessArtifactVersion
        ] = {}
        self._task_commits: dict[
            tuple[str, str, str], StoredHarnessTaskCommit
        ] = {}
        self._tasks: dict[tuple[str, str], TaskRecord] = {}
        self._task_receipts: dict[tuple[str, str], tuple[str, TaskLedgerReceipt]] = {}
        self._lock = asyncio.Lock()

    async def setup(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def load_runs(self) -> list[StoredHarnessRun]:
        async with self._lock:
            return [
                StoredHarnessRun(
                    owner_id=item.owner_id,
                    run_id=item.run_id,
                    snapshot=_clone(item.snapshot),
                    resume_status=item.resume_status,
                )
                for item in self._runs.values()
            ]

    async def load_idempotency(self) -> list[StoredHarnessIdempotency]:
        async with self._lock:
            return [
                StoredHarnessIdempotency(
                    owner_id=item.owner_id,
                    kind=item.kind,
                    idempotency_key=item.idempotency_key,
                    digest=item.digest,
                    result=_clone(item.result),
                )
                for item in self._idempotency.values()
            ]

    async def load_artifact_versions(
        self, owner_id: str, run_id: str
    ) -> list[StoredHarnessArtifactVersion]:
        async with self._lock:
            return [
                StoredHarnessArtifactVersion(
                    owner_id=item.owner_id,
                    run_id=item.run_id,
                    artifact_id=item.artifact_id,
                    version=item.version,
                    payload_digest=item.payload_digest,
                    payload=_clone(item.payload),
                )
                for item in self._artifact_versions.values()
                if item.owner_id == owner_id and item.run_id == run_id
            ]

    async def load_task_commits(
        self, owner_id: str, run_id: str
    ) -> list[StoredHarnessTaskCommit]:
        async with self._lock:
            return [
                StoredHarnessTaskCommit(
                    owner_id=item.owner_id,
                    run_id=item.run_id,
                    commit_id=item.commit_id,
                    payload_digest=item.payload_digest,
                    payload=_clone(item.payload),
                )
                for item in self._task_commits.values()
                if item.owner_id == owner_id and item.run_id == run_id
            ]

    async def load_work_units(self, owner_id: str, run_id: str) -> list[WorkUnitRecord]:
        async with self._lock:
            run = self._runs.get((owner_id, run_id))
            return [
                WorkUnitRecord.model_validate(item)
                for item in (run.snapshot.get("work_units", []) if run else [])
            ]

    async def load_contributions(self, owner_id: str, run_id: str) -> list[ContributionRecord]:
        async with self._lock:
            run = self._runs.get((owner_id, run_id))
            return [
                ContributionRecord.model_validate(item)
                for item in (run.snapshot.get("contributions", []) if run else [])
            ]

    async def commit(
        self,
        run: StoredHarnessRun,
        idempotency: StoredHarnessIdempotency | None = None,
        artifact_version: StoredHarnessArtifactVersion | None = None,
        task_commit: StoredHarnessTaskCommit | None = None,
    ) -> StoredHarnessIdempotency | None:
        async with self._lock:
            idempotency_key: tuple[str, IdempotencyKind, str] | None = None
            if idempotency is not None:
                idempotency_key = (
                    idempotency.owner_id,
                    idempotency.kind,
                    idempotency.idempotency_key,
                )
                existing = self._idempotency.get(idempotency_key)
                if existing is not None:
                    return StoredHarnessIdempotency(
                        owner_id=existing.owner_id,
                        kind=existing.kind,
                        idempotency_key=existing.idempotency_key,
                        digest=existing.digest,
                        result=_clone(existing.result),
                    )
            artifact_key: tuple[str, str, str, int] | None = None
            if artifact_version is not None:
                artifact_key = (
                    artifact_version.owner_id,
                    artifact_version.run_id,
                    artifact_version.artifact_id,
                    artifact_version.version,
                )
                existing_artifact = self._artifact_versions.get(artifact_key)
                if (
                    existing_artifact is not None
                    and existing_artifact.payload_digest
                    != artifact_version.payload_digest
                ):
                    raise RuntimeError("immutable artifact version conflict")
            commit_key: tuple[str, str, str] | None = None
            if task_commit is not None:
                commit_key = (
                    task_commit.owner_id,
                    task_commit.run_id,
                    task_commit.commit_id,
                )
                existing_commit = self._task_commits.get(commit_key)
                if (
                    existing_commit is not None
                    and existing_commit.payload_digest != task_commit.payload_digest
                ):
                    raise RuntimeError("immutable task commit conflict")

            previous_run = self._runs.get((run.owner_id, run.run_id))
            if run.snapshot.get("owner_id") not in {None, run.owner_id}:
                raise RuntimeError("Run owner scope mismatch")
            _validate_ledger_append(
                previous_run.snapshot if previous_run is not None else None,
                run.snapshot,
            )

            if idempotency is not None and idempotency_key is not None:
                self._idempotency[idempotency_key] = StoredHarnessIdempotency(
                    owner_id=idempotency.owner_id,
                    kind=idempotency.kind,
                    idempotency_key=idempotency.idempotency_key,
                    digest=idempotency.digest,
                    result=_clone(idempotency.result),
                )
            if artifact_version is not None and artifact_key is not None:
                self._artifact_versions.setdefault(
                    artifact_key,
                    StoredHarnessArtifactVersion(
                        owner_id=artifact_version.owner_id,
                        run_id=artifact_version.run_id,
                        artifact_id=artifact_version.artifact_id,
                        version=artifact_version.version,
                        payload_digest=artifact_version.payload_digest,
                        payload=_clone(artifact_version.payload),
                    ),
                )
            if task_commit is not None and commit_key is not None:
                self._task_commits.setdefault(
                    commit_key,
                    StoredHarnessTaskCommit(
                        owner_id=task_commit.owner_id,
                        run_id=task_commit.run_id,
                        commit_id=task_commit.commit_id,
                        payload_digest=task_commit.payload_digest,
                        payload=_clone(task_commit.payload),
                    ),
                )
            self._runs[(run.owner_id, run.run_id)] = StoredHarnessRun(
                owner_id=run.owner_id,
                run_id=run.run_id,
                snapshot=_clone(run.snapshot),
                resume_status=run.resume_status,
            )
            return None

    async def load_task_records(self) -> list[TaskRecord]:
        async with self._lock:
            return [item.model_copy(deep=True) for item in self._tasks.values()]

    async def get_task_record(self, owner_id: str, task_id: str) -> TaskRecord | None:
        async with self._lock:
            item = self._tasks.get((owner_id, task_id))
            return item.model_copy(deep=True) if item else None

    async def get_task_aggregate(
        self, owner_id: str, task_id: str
    ) -> tuple[TaskRecord | None, list[StoredHarnessRun]]:
        async with self._lock:
            item = self._tasks.get((owner_id, task_id))
            runs = [
                StoredHarnessRun(
                    owner_id=run.owner_id,
                    run_id=run.run_id,
                    snapshot=_clone(run.snapshot),
                    resume_status=run.resume_status,
                )
                for (candidate_owner, _), run in self._runs.items()
                if candidate_owner == owner_id and run.snapshot.get("task_id") == task_id
            ]
            return (item.model_copy(deep=True) if item else None), runs

    async def create_task_record(self, task: TaskRecord) -> TaskRecord:
        async with self._lock:
            key = (task.owner_id, task.task_id)
            current = self._tasks.get(key)
            if current is not None:
                if current.model_dump(mode="json") != task.model_dump(mode="json"):
                    raise TaskLedgerConflict("task identity conflict")
                return current.model_copy(deep=True)
            self._tasks[key] = task.model_copy(deep=True)
            return task.model_copy(deep=True)

    async def commit_task_transition(
        self,
        run: StoredHarnessRun,
        task: TaskRecord,
        *,
        expected_task_version: int | None = None,
        expected_parent_run_id: str | None = None,
        expected_parent_version: int | None = None,
        task_receipt: TaskLedgerReceipt | None = None,
        task_digest: str | None = None,
        idempotency: StoredHarnessIdempotency | None = None,
    ) -> StoredHarnessIdempotency | None:
        """Atomically persist run, task pointer and receipts under one lock."""
        async with self._lock:
            idem_key = None
            if idempotency is not None:
                idem_key = (idempotency.owner_id, idempotency.kind, idempotency.idempotency_key)
                previous = self._idempotency.get(idem_key)
                if previous is not None:
                    if previous.digest != idempotency.digest:
                        raise TaskLedgerConflict("idempotency command conflict")
                    return previous
            task_key = (task.owner_id, task.task_id)
            if expected_parent_run_id is not None:
                parent = self._runs.get((run.owner_id, expected_parent_run_id))
                if parent is None or parent.snapshot.get("version") != expected_parent_version:
                    raise TaskLedgerConflict("parent Run version CAS failed")
            if (run.owner_id, run.run_id) in self._runs:
                raise TaskLedgerConflict("run_id 已存在")
            current_task = self._tasks.get(task_key)
            if expected_task_version is None:
                if current_task is not None and current_task.model_dump(mode="json") != task.model_dump(mode="json"):
                    raise TaskLedgerConflict("task already exists with different identity")
            else:
                if current_task is None or current_task.task_version != expected_task_version:
                    raise TaskLedgerConflict("task version CAS failed")
                if task.task_version != expected_task_version + 1:
                    raise TaskLedgerConflict("task version must increment by one")
                if task_receipt is not None:
                    receipt_key = (task.owner_id, task_receipt.idempotency_key)
                    previous_receipt = self._task_receipts.get(receipt_key)
                    if previous_receipt is not None:
                        if previous_receipt[0] != (task_digest or ""):
                            raise TaskLedgerConflict("task receipt idempotency conflict")
                        return idempotency
            if idempotency is not None and idem_key is not None:
                self._idempotency[idem_key] = idempotency
            self._tasks[task_key] = task.model_copy(deep=True)
            if task_receipt is not None:
                self._task_receipts[(task.owner_id, task_receipt.idempotency_key)] = (
                    task_digest or "",
                    task_receipt.model_copy(deep=True),
                )
            self._runs[(run.owner_id, run.run_id)] = StoredHarnessRun(
                owner_id=run.owner_id,
                run_id=run.run_id,
                snapshot=_clone(run.snapshot),
                resume_status=run.resume_status,
            )
            return None


class PostgresHarnessStateStore:
    """PostgreSQL-backed snapshots and command receipts."""

    backend_name = "postgres"

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    async def setup(self) -> None:
        async with await psycopg.AsyncConnection.connect(self._dsn) as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS harness_run_state (
                        owner_id TEXT NOT NULL,
                        run_id TEXT NOT NULL,
                        snapshot JSONB NOT NULL,
                        resume_status TEXT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (owner_id, run_id)
                    )
                    """
                )
                await cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS harness_artifact_version (
                        owner_id TEXT NOT NULL,
                        run_id TEXT NOT NULL,
                        artifact_id TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        payload_digest TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (owner_id, run_id, artifact_id, version)
                    )
                    """
                )
                await cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS harness_task_commit (
                        owner_id TEXT NOT NULL,
                        run_id TEXT NOT NULL,
                        commit_id TEXT NOT NULL,
                        payload_digest TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (owner_id, run_id, commit_id)
                    )
                    """
                )
                await cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS harness_idempotency (
                        owner_id TEXT NOT NULL,
                        kind TEXT NOT NULL CHECK (kind IN ('start', 'control')),
                        idempotency_key TEXT NOT NULL,
                        digest TEXT NOT NULL,
                        result JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (owner_id, kind, idempotency_key)
                    )
                    """
                )
                await cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS harness_task_ledger (
                        owner_id TEXT NOT NULL,
                        task_id TEXT NOT NULL,
                        task_version INTEGER NOT NULL,
                        payload JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (owner_id, task_id)
                    )
                    """
                )
                await cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS harness_task_ledger_receipt (
                        owner_id TEXT NOT NULL,
                        idempotency_key TEXT NOT NULL,
                        digest TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (owner_id, idempotency_key)
                    )
                    """
                )
                await cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS harness_work_unit (
                        owner_id TEXT NOT NULL,
                        task_id TEXT NOT NULL,
                        run_id TEXT NOT NULL,
                        work_unit_id TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        payload JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (owner_id, run_id, work_unit_id)
                    )
                    """
                )
                await cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS harness_contribution (
                        owner_id TEXT NOT NULL,
                        run_id TEXT NOT NULL,
                        contribution_id TEXT NOT NULL,
                        payload_digest TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (owner_id, run_id, contribution_id)
                    )
                    """
                )
                await cursor.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS harness_contribution_attempt_unique
                    ON harness_contribution(owner_id, run_id,
                        (payload->>'work_unit_id'), ((payload->>'attempt')::INTEGER))
                    """
                )

    async def close(self) -> None:
        return None

    async def load_task_records(self) -> list[TaskRecord]:
        async with await psycopg.AsyncConnection.connect(self._dsn) as connection:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT payload FROM harness_task_ledger ORDER BY updated_at ASC")
                rows = await cursor.fetchall()
        return [TaskRecord.model_validate(dict(row[0])) for row in rows]

    async def get_task_record(self, owner_id: str, task_id: str) -> TaskRecord | None:
        async with await psycopg.AsyncConnection.connect(self._dsn) as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT payload FROM harness_task_ledger WHERE owner_id=%s AND task_id=%s",
                    (owner_id, task_id),
                )
                row = await cursor.fetchone()
        return TaskRecord.model_validate(dict(row[0])) if row else None

    async def get_task_aggregate(
        self, owner_id: str, task_id: str
    ) -> tuple[TaskRecord | None, list[StoredHarnessRun]]:
        async with await psycopg.AsyncConnection.connect(self._dsn) as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT payload FROM harness_task_ledger WHERE owner_id=%s AND task_id=%s",
                    (owner_id, task_id),
                )
                task_row = await cursor.fetchone()
                await cursor.execute(
                    "SELECT owner_id, run_id, snapshot, resume_status FROM harness_run_state WHERE owner_id=%s AND snapshot->>'task_id'=%s ORDER BY updated_at ASC",
                    (owner_id, task_id),
                )
                run_rows = await cursor.fetchall()
        task = TaskRecord.model_validate(dict(task_row[0])) if task_row else None
        runs = [
            StoredHarnessRun(owner_id=str(row[0]), run_id=str(row[1]), snapshot=dict(row[2]), resume_status=row[3])
            for row in run_rows
        ]
        return task, runs

    async def create_task_record(self, task: TaskRecord) -> TaskRecord:
        async with await psycopg.AsyncConnection.connect(self._dsn) as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO harness_task_ledger(owner_id,task_id,task_version,payload) VALUES (%s,%s,%s,%s) ON CONFLICT (owner_id,task_id) DO NOTHING",
                    (task.owner_id, task.task_id, task.task_version, Jsonb(task.model_dump(mode="json"))),
                )
        existing = await self.get_task_record(task.owner_id, task.task_id)
        if existing is None:
            raise TaskLedgerConflict("task create failed")
        return existing

    async def commit_task_transition(
        self,
        run: StoredHarnessRun,
        task: TaskRecord,
        *,
        expected_task_version: int | None = None,
        expected_parent_run_id: str | None = None,
        expected_parent_version: int | None = None,
        task_receipt: TaskLedgerReceipt | None = None,
        task_digest: str | None = None,
        idempotency: StoredHarnessIdempotency | None = None,
    ) -> StoredHarnessIdempotency | None:
        """Persist task and child Run in one PostgreSQL transaction."""
        async with await psycopg.AsyncConnection.connect(self._dsn) as connection:
            async with connection.cursor() as cursor:
                if idempotency is not None:
                    await cursor.execute(
                        "INSERT INTO harness_idempotency(owner_id,kind,idempotency_key,digest,result) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (owner_id,kind,idempotency_key) DO NOTHING RETURNING idempotency_key",
                        (idempotency.owner_id, idempotency.kind, idempotency.idempotency_key, idempotency.digest, Jsonb(idempotency.result)),
                    )
                    claimed = await cursor.fetchone()
                    if claimed is None:
                        await cursor.execute(
                            "SELECT digest, result FROM harness_idempotency WHERE owner_id=%s AND kind=%s AND idempotency_key=%s",
                            (idempotency.owner_id, idempotency.kind, idempotency.idempotency_key),
                        )
                        previous = await cursor.fetchone()
                        if previous is None or str(previous[0]) != idempotency.digest:
                            raise TaskLedgerConflict("idempotency command conflict")
                        return StoredHarnessIdempotency(
                            owner_id=idempotency.owner_id,
                            kind=idempotency.kind,
                            idempotency_key=idempotency.idempotency_key,
                            digest=str(previous[0]),
                            result=dict(previous[1]),
                        )
                if expected_parent_run_id is not None:
                    await cursor.execute(
                        "SELECT snapshot->'version' FROM harness_run_state WHERE owner_id=%s AND run_id=%s FOR UPDATE",
                        (run.owner_id, expected_parent_run_id),
                    )
                    parent = await cursor.fetchone()
                    raw_parent_version = parent[0] if parent is not None else None
                    parent_version = (
                        raw_parent_version
                        if isinstance(raw_parent_version, int) and not isinstance(raw_parent_version, bool)
                        else None
                    )
                    if parent_version is None or parent_version != expected_parent_version:
                        raise TaskLedgerConflict("parent Run version CAS failed")
                if expected_task_version is None:
                    await cursor.execute(
                        "INSERT INTO harness_task_ledger(owner_id,task_id,task_version,payload) VALUES (%s,%s,%s,%s) ON CONFLICT (owner_id,task_id) DO NOTHING RETURNING task_id",
                        (task.owner_id, task.task_id, task.task_version, Jsonb(task.model_dump(mode="json"))),
                    )
                    if await cursor.fetchone() is None:
                        await cursor.execute(
                            "SELECT payload FROM harness_task_ledger WHERE owner_id=%s AND task_id=%s",
                            (task.owner_id, task.task_id),
                        )
                        existing = await cursor.fetchone()
                        if existing is None or dict(existing[0]) != task.model_dump(mode="json"):
                            raise TaskLedgerConflict("task already exists with different identity")
                else:
                    if task.task_version != expected_task_version + 1:
                        raise TaskLedgerConflict("task version must increment by one")
                    await cursor.execute(
                        "UPDATE harness_task_ledger SET task_version=%s,payload=%s,updated_at=NOW() WHERE owner_id=%s AND task_id=%s AND task_version=%s RETURNING task_id",
                        (task.task_version, Jsonb(task.model_dump(mode="json")), task.owner_id, task.task_id, expected_task_version),
                    )
                    if await cursor.fetchone() is None:
                        raise TaskLedgerConflict("task version CAS failed")
                if task_receipt is not None:
                    await cursor.execute(
                        "SELECT digest FROM harness_task_ledger_receipt WHERE owner_id=%s AND idempotency_key=%s FOR UPDATE",
                        (task.owner_id, task_receipt.idempotency_key),
                    )
                    prior_receipt = await cursor.fetchone()
                    if prior_receipt is not None and str(prior_receipt[0]) != (task_digest or ""):
                        raise TaskLedgerConflict("task receipt idempotency conflict")
                    await cursor.execute(
                        "INSERT INTO harness_task_ledger_receipt(owner_id,idempotency_key,digest,payload) VALUES (%s,%s,%s,%s) ON CONFLICT (owner_id,idempotency_key) DO NOTHING",
                        (task.owner_id, task_receipt.idempotency_key, task_digest or "", Jsonb(task_receipt.model_dump(mode="json"))),
                    )
                await cursor.execute(
                    "INSERT INTO harness_run_state(owner_id,run_id,snapshot,resume_status,updated_at) VALUES (%s,%s,%s,%s,NOW()) ON CONFLICT (owner_id,run_id) DO NOTHING RETURNING run_id",
                    (run.owner_id, run.run_id, Jsonb(run.snapshot), run.resume_status),
                )
                if await cursor.fetchone() is None:
                    raise TaskLedgerConflict("run_id 已存在")
        return None

    async def load_runs(self) -> list[StoredHarnessRun]:
        async with await psycopg.AsyncConnection.connect(self._dsn) as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT owner_id, run_id, snapshot, resume_status
                    FROM harness_run_state
                    ORDER BY updated_at ASC
                    """
                )
                rows = await cursor.fetchall()
        return [
            StoredHarnessRun(
                owner_id=str(owner_id),
                run_id=str(run_id),
                snapshot=dict(snapshot),
                resume_status=str(resume_status) if resume_status else None,
            )
            for owner_id, run_id, snapshot, resume_status in rows
        ]

    async def load_idempotency(self) -> list[StoredHarnessIdempotency]:
        async with await psycopg.AsyncConnection.connect(self._dsn) as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT owner_id, kind, idempotency_key, digest, result
                    FROM harness_idempotency
                    ORDER BY created_at ASC
                    """
                )
                rows = await cursor.fetchall()
        return [
            StoredHarnessIdempotency(
                owner_id=str(owner_id),
                kind=kind,
                idempotency_key=str(idempotency_key),
                digest=str(digest),
                result=dict(result),
            )
            for owner_id, kind, idempotency_key, digest, result in rows
        ]

    async def load_artifact_versions(
        self, owner_id: str, run_id: str
    ) -> list[StoredHarnessArtifactVersion]:
        async with await psycopg.AsyncConnection.connect(self._dsn) as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT owner_id, run_id, artifact_id, version,
                           payload_digest, payload
                    FROM harness_artifact_version
                    WHERE owner_id = %s AND run_id = %s
                    ORDER BY version ASC
                    """,
                    (owner_id, run_id),
                )
                rows = await cursor.fetchall()
        return [
            StoredHarnessArtifactVersion(
                owner_id=str(row_owner),
                run_id=str(row_run),
                artifact_id=str(artifact_id),
                version=int(version),
                payload_digest=str(payload_digest),
                payload=dict(payload),
            )
            for row_owner, row_run, artifact_id, version, payload_digest, payload in rows
        ]

    async def load_task_commits(
        self, owner_id: str, run_id: str
    ) -> list[StoredHarnessTaskCommit]:
        async with await psycopg.AsyncConnection.connect(self._dsn) as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT owner_id, run_id, commit_id, payload_digest, payload
                    FROM harness_task_commit
                    WHERE owner_id = %s AND run_id = %s
                    ORDER BY created_at ASC
                    """,
                    (owner_id, run_id),
                )
                rows = await cursor.fetchall()
        return [
            StoredHarnessTaskCommit(
                owner_id=str(row_owner),
                run_id=str(row_run),
                commit_id=str(commit_id),
                payload_digest=str(payload_digest),
                payload=dict(payload),
            )
            for row_owner, row_run, commit_id, payload_digest, payload in rows
        ]

    async def load_work_units(self, owner_id: str, run_id: str) -> list[WorkUnitRecord]:
        async with await psycopg.AsyncConnection.connect(self._dsn) as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT payload FROM harness_work_unit WHERE owner_id=%s AND run_id=%s ORDER BY work_unit_id",
                    (owner_id, run_id),
                )
                rows = await cursor.fetchall()
        return [WorkUnitRecord.model_validate(dict(row[0])) for row in rows]

    async def load_contributions(self, owner_id: str, run_id: str) -> list[ContributionRecord]:
        async with await psycopg.AsyncConnection.connect(self._dsn) as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT payload FROM harness_contribution WHERE owner_id=%s AND run_id=%s ORDER BY created_at, contribution_id",
                    (owner_id, run_id),
                )
                rows = await cursor.fetchall()
        return [ContributionRecord.model_validate(dict(row[0])) for row in rows]

    async def commit(
        self,
        run: StoredHarnessRun,
        idempotency: StoredHarnessIdempotency | None = None,
        artifact_version: StoredHarnessArtifactVersion | None = None,
        task_commit: StoredHarnessTaskCommit | None = None,
    ) -> StoredHarnessIdempotency | None:
        async with await psycopg.AsyncConnection.connect(self._dsn) as connection:
            async with connection.cursor() as cursor:
                if idempotency is not None:
                    await cursor.execute(
                        """
                        INSERT INTO harness_idempotency (
                            owner_id, kind, idempotency_key, digest, result
                        ) VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (owner_id, kind, idempotency_key) DO NOTHING
                        RETURNING idempotency_key
                        """,
                        (
                            idempotency.owner_id,
                            idempotency.kind,
                            idempotency.idempotency_key,
                            idempotency.digest,
                            Jsonb(idempotency.result),
                        ),
                    )
                    inserted = await cursor.fetchone()
                    if inserted is None:
                        await cursor.execute(
                            """
                            SELECT digest, result
                            FROM harness_idempotency
                            WHERE owner_id = %s AND kind = %s AND idempotency_key = %s
                            """,
                            (
                                idempotency.owner_id,
                                idempotency.kind,
                                idempotency.idempotency_key,
                            ),
                        )
                        row = await cursor.fetchone()
                        if row is None:
                            raise RuntimeError("idempotency record disappeared")
                        digest, result = row
                        return StoredHarnessIdempotency(
                            owner_id=idempotency.owner_id,
                            kind=idempotency.kind,
                            idempotency_key=idempotency.idempotency_key,
                            digest=str(digest),
                            result=dict(result),
                        )
                if artifact_version is not None:
                    await self._insert_immutable(
                        cursor,
                        table="harness_artifact_version",
                        key_columns=("owner_id", "run_id", "artifact_id", "version"),
                        key_values=(
                            artifact_version.owner_id,
                            artifact_version.run_id,
                            artifact_version.artifact_id,
                            artifact_version.version,
                        ),
                        payload_digest=artifact_version.payload_digest,
                        payload=artifact_version.payload,
                    )
                if task_commit is not None:
                    await self._insert_immutable(
                        cursor,
                        table="harness_task_commit",
                        key_columns=("owner_id", "run_id", "commit_id"),
                        key_values=(
                            task_commit.owner_id,
                            task_commit.run_id,
                            task_commit.commit_id,
                        ),
                        payload_digest=task_commit.payload_digest,
                        payload=task_commit.payload,
                    )
                for work_unit in run.snapshot.get("work_units", []):
                    await cursor.execute(
                        "SELECT version, payload FROM harness_work_unit WHERE owner_id=%s AND run_id=%s AND work_unit_id=%s FOR UPDATE",
                        (run.owner_id, run.run_id, work_unit["work_unit_id"]),
                    )
                    previous = await cursor.fetchone()
                    if previous is not None:
                        if int(previous[0]) > int(work_unit["version"]):
                            raise RuntimeError("WorkUnit version cannot move backwards")
                        if int(previous[0]) == int(work_unit["version"]) and dict(previous[1]) != work_unit:
                            raise RuntimeError("WorkUnit version CAS failed")
                    await cursor.execute(
                        """
                        INSERT INTO harness_work_unit(owner_id,task_id,run_id,work_unit_id,version,payload,updated_at)
                        VALUES (%s,%s,%s,%s,%s,%s,NOW())
                        ON CONFLICT (owner_id,run_id,work_unit_id) DO UPDATE SET
                            task_id=EXCLUDED.task_id, version=EXCLUDED.version,
                            payload=EXCLUDED.payload, updated_at=NOW()
                        """,
                        (
                            run.owner_id,
                            run.snapshot.get("task_id", ""),
                            run.run_id,
                            work_unit["work_unit_id"],
                            work_unit["version"],
                            Jsonb(work_unit),
                        ),
                    )
                for contribution in run.snapshot.get("contributions", []):
                    await self._insert_immutable(
                        cursor,
                        table="harness_contribution",
                        key_columns=("owner_id", "run_id", "contribution_id"),
                        key_values=(run.owner_id, run.run_id, contribution["contribution_id"]),
                        payload_digest=contribution_digest(ContributionRecord.model_validate(contribution)),
                        payload=contribution,
                    )
                await cursor.execute(
                    """
                    INSERT INTO harness_run_state (
                        owner_id, run_id, snapshot, resume_status, updated_at
                    ) VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (owner_id, run_id) DO UPDATE SET
                        snapshot = EXCLUDED.snapshot,
                        resume_status = EXCLUDED.resume_status,
                        updated_at = NOW()
                    """,
                    (
                        run.owner_id,
                        run.run_id,
                        Jsonb(run.snapshot),
                        run.resume_status,
                    ),
                )
        return None

    @staticmethod
    async def _insert_immutable(
        cursor: psycopg.AsyncCursor[Any],
        *,
        table: Literal[
            "harness_artifact_version", "harness_task_commit", "harness_contribution"
        ],
        key_columns: tuple[str, ...],
        key_values: tuple[Any, ...],
        payload_digest: str,
        payload: dict[str, Any],
    ) -> None:
        columns = ", ".join((*key_columns, "payload_digest", "payload"))
        placeholders = ", ".join(["%s"] * (len(key_values) + 2))
        conflict = ", ".join(key_columns)
        await cursor.execute(
            f"""
            INSERT INTO {table} ({columns})
            VALUES ({placeholders})
            ON CONFLICT ({conflict}) DO NOTHING
            RETURNING payload_digest
            """,  # nosec B608 - table and columns are fixed Literals above.
            (*key_values, payload_digest, Jsonb(payload)),
        )
        inserted = await cursor.fetchone()
        if inserted is not None:
            return
        predicate = " AND ".join(f"{column} = %s" for column in key_columns)
        await cursor.execute(
            f"SELECT payload_digest FROM {table} WHERE {predicate}",  # nosec B608
            key_values,
        )
        row = await cursor.fetchone()
        if row is None or str(row[0]) != payload_digest:
            raise RuntimeError(f"immutable {table} conflict")
