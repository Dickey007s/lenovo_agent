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


IdempotencyKind = Literal["start", "control"]


def _clone(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


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

    async def commit(
        self,
        run: StoredHarnessRun,
        idempotency: StoredHarnessIdempotency | None = None,
        artifact_version: StoredHarnessArtifactVersion | None = None,
        task_commit: StoredHarnessTaskCommit | None = None,
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

    async def close(self) -> None:
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
        table: Literal["harness_artifact_version", "harness_task_commit"],
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
