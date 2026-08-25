"""Durable JSON state storage for the Agent Control Loop.

The runtime remains the state-machine owner. This adapter only makes accepted
snapshots and idempotency receipts survive process restarts.
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


class HarnessStateStore(Protocol):
    backend_name: str

    async def setup(self) -> None: ...

    async def close(self) -> None: ...

    async def load_runs(self) -> list[StoredHarnessRun]: ...

    async def load_idempotency(self) -> list[StoredHarnessIdempotency]: ...

    async def commit(
        self,
        run: StoredHarnessRun,
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

    async def commit(
        self,
        run: StoredHarnessRun,
        idempotency: StoredHarnessIdempotency | None = None,
    ) -> StoredHarnessIdempotency | None:
        async with self._lock:
            if idempotency is not None:
                key = (
                    idempotency.owner_id,
                    idempotency.kind,
                    idempotency.idempotency_key,
                )
                existing = self._idempotency.get(key)
                if existing is not None:
                    return StoredHarnessIdempotency(
                        owner_id=existing.owner_id,
                        kind=existing.kind,
                        idempotency_key=existing.idempotency_key,
                        digest=existing.digest,
                        result=_clone(existing.result),
                    )
                self._idempotency[key] = StoredHarnessIdempotency(
                    owner_id=idempotency.owner_id,
                    kind=idempotency.kind,
                    idempotency_key=idempotency.idempotency_key,
                    digest=idempotency.digest,
                    result=_clone(idempotency.result),
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

    async def commit(
        self,
        run: StoredHarnessRun,
        idempotency: StoredHarnessIdempotency | None = None,
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
