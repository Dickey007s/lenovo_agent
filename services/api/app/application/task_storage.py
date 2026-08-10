from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass
from typing import Protocol

import psycopg
from psycopg.types.json import Jsonb


class TaskStoreConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredTask:
    snapshot: dict
    artifact_versions: list[dict]


class TaskStore(Protocol):
    async def setup(self) -> None: ...

    async def create(self, snapshot: dict, initial_event: dict) -> None: ...

    async def load(self, task_id: str, owner_id: str) -> StoredTask | None: ...

    async def list_for_owner(self, owner_id: str) -> list[StoredTask]: ...

    async def load_events(
        self, task_id: str, owner_id: str, after_sequence: int = 0
    ) -> list[dict]: ...


class InMemoryTaskStore:
    def __init__(self) -> None:
        self._tasks: dict[str, dict] = {}
        self._events: dict[str, list[dict]] = {}
        self._artifact_versions: dict[str, list[dict]] = {}
        self._lock = asyncio.Lock()

    async def setup(self) -> None:
        return None

    async def create(self, snapshot: dict, initial_event: dict) -> None:
        task_id = snapshot["task_id"]
        async with self._lock:
            if task_id in self._tasks:
                raise TaskStoreConflictError(f"task already exists: {task_id}")
            self._tasks[task_id] = deepcopy(snapshot)
            self._events[task_id] = [deepcopy(initial_event)]
            self._artifact_versions[task_id] = []

    async def load(self, task_id: str, owner_id: str) -> StoredTask | None:
        snapshot = self._tasks.get(task_id)
        if snapshot is None or snapshot["owner_id"] != owner_id:
            return None
        return StoredTask(
            snapshot=deepcopy(snapshot),
            artifact_versions=deepcopy(self._artifact_versions.get(task_id, [])),
        )

    async def list_for_owner(self, owner_id: str) -> list[StoredTask]:
        snapshots = [
            snapshot
            for snapshot in self._tasks.values()
            if snapshot["owner_id"] == owner_id
        ]
        snapshots.sort(key=lambda item: item["updated_at"], reverse=True)
        return [
            StoredTask(
                snapshot=deepcopy(snapshot),
                artifact_versions=deepcopy(
                    self._artifact_versions.get(snapshot["task_id"], [])
                ),
            )
            for snapshot in snapshots
        ]

    async def load_events(
        self, task_id: str, owner_id: str, after_sequence: int = 0
    ) -> list[dict]:
        snapshot = self._tasks.get(task_id)
        if snapshot is None or snapshot["owner_id"] != owner_id:
            return []
        return [
            deepcopy(event)
            for event in self._events.get(task_id, [])
            if event["sequence"] > after_sequence
        ]


class PostgresTaskStore:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    async def setup(self) -> None:
        async with await psycopg.AsyncConnection.connect(self.dsn) as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_tasks (
                    task_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    version BIGINT NOT NULL,
                    snapshot JSONB NOT NULL,
                    last_event_sequence BIGINT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            await connection.execute(
                "CREATE INDEX IF NOT EXISTS agent_tasks_owner_updated_idx "
                "ON agent_tasks(owner_id, updated_at DESC)"
            )
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_task_events (
                    task_id TEXT NOT NULL REFERENCES agent_tasks(task_id) ON DELETE CASCADE,
                    sequence BIGINT NOT NULL,
                    event_id TEXT NOT NULL UNIQUE,
                    branch_id TEXT,
                    artifact_version_id TEXT,
                    control_event_id TEXT,
                    actor_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    idempotency_key TEXT,
                    event JSONB NOT NULL,
                    occurred_at TIMESTAMPTZ NOT NULL,
                    PRIMARY KEY (task_id, sequence),
                    UNIQUE (task_id, idempotency_key)
                )
                """
            )
            await connection.execute(
                "CREATE INDEX IF NOT EXISTS agent_task_events_task_sequence_idx "
                "ON agent_task_events(task_id, sequence)"
            )
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_task_artifact_versions (
                    artifact_version_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES agent_tasks(task_id) ON DELETE CASCADE,
                    branch_id TEXT NOT NULL,
                    deliverable_id TEXT NOT NULL,
                    version BIGINT NOT NULL,
                    content_digest TEXT NOT NULL,
                    artifact JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    UNIQUE (task_id, branch_id, deliverable_id, version)
                )
                """
            )

    async def create(self, snapshot: dict, initial_event: dict) -> None:
        try:
            async with await psycopg.AsyncConnection.connect(self.dsn) as connection:
                await connection.execute(
                    """
                    INSERT INTO agent_tasks (
                        task_id, owner_id, status, phase, version, snapshot,
                        last_event_sequence, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        snapshot["task_id"],
                        snapshot["owner_id"],
                        snapshot["status"],
                        snapshot["phase"],
                        snapshot["version"],
                        Jsonb(snapshot),
                        snapshot["last_event_sequence"],
                        snapshot["created_at"],
                        snapshot["updated_at"],
                    ),
                )
                await self._insert_event(connection, initial_event)
        except psycopg.errors.UniqueViolation as exc:
            raise TaskStoreConflictError(
                f"task already exists: {snapshot['task_id']}"
            ) from exc

    async def load(self, task_id: str, owner_id: str) -> StoredTask | None:
        async with await psycopg.AsyncConnection.connect(self.dsn) as connection:
            row = await (
                await connection.execute(
                    "SELECT snapshot FROM agent_tasks WHERE task_id = %s AND owner_id = %s",
                    (task_id, owner_id),
                )
            ).fetchone()
            if row is None:
                return None
            artifacts = await (
                await connection.execute(
                    """
                    SELECT artifact FROM agent_task_artifact_versions
                    WHERE task_id = %s ORDER BY branch_id, deliverable_id, version
                    """,
                    (task_id,),
                )
            ).fetchall()
        return StoredTask(snapshot=row[0], artifact_versions=[item[0] for item in artifacts])

    async def list_for_owner(self, owner_id: str) -> list[StoredTask]:
        async with await psycopg.AsyncConnection.connect(self.dsn) as connection:
            rows = await (
                await connection.execute(
                    """
                    SELECT snapshot FROM agent_tasks
                    WHERE owner_id = %s ORDER BY updated_at DESC
                    """,
                    (owner_id,),
                )
            ).fetchall()
        return [StoredTask(snapshot=row[0], artifact_versions=[]) for row in rows]

    async def load_events(
        self, task_id: str, owner_id: str, after_sequence: int = 0
    ) -> list[dict]:
        async with await psycopg.AsyncConnection.connect(self.dsn) as connection:
            rows = await (
                await connection.execute(
                    """
                    SELECT event
                    FROM agent_task_events events
                    JOIN agent_tasks tasks ON tasks.task_id = events.task_id
                    WHERE events.task_id = %s AND tasks.owner_id = %s
                      AND events.sequence > %s
                    ORDER BY events.sequence
                    """,
                    (task_id, owner_id, after_sequence),
                )
            ).fetchall()
        return [row[0] for row in rows]

    @staticmethod
    async def _insert_event(
        connection: psycopg.AsyncConnection, event: dict
    ) -> None:
        await connection.execute(
            """
            INSERT INTO agent_task_events (
                task_id, sequence, event_id, branch_id, artifact_version_id,
                control_event_id, actor_id, event_type, idempotency_key,
                event, occurred_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                event["task_id"],
                event["sequence"],
                event["event_id"],
                event.get("branch_id"),
                event.get("artifact_version_id"),
                event.get("control_event_id"),
                event["actor_id"],
                event["event_type"],
                event.get("idempotency_key"),
                Jsonb(event),
                event["occurred_at"],
            ),
        )
