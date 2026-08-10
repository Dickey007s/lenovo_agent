from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass
from typing import Protocol

import psycopg
from psycopg.types.json import Jsonb

from packages.contracts.hashing import canonical_hash


class TaskStoreConflictError(RuntimeError):
    pass


class TaskStoreNotFoundError(LookupError):
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

    async def commit(
        self,
        task_id: str,
        owner_id: str,
        expected_version: int,
        snapshot: dict,
        events: list[dict],
        artifact_versions: list[dict],
    ) -> StoredTask: ...


def _validate_commit(
    *,
    task_id: str,
    owner_id: str,
    expected_version: int,
    current_snapshot: dict,
    snapshot: dict,
    events: list[dict],
    artifact_versions: list[dict],
    existing_artifact_versions: list[dict],
) -> None:
    if current_snapshot.get("owner_id") != owner_id:
        raise TaskStoreNotFoundError(task_id)
    if current_snapshot.get("task_id") != task_id:
        raise TaskStoreConflictError("stored task identity is inconsistent")
    if current_snapshot.get("version") != expected_version:
        raise TaskStoreConflictError(
            f"task version conflict: expected {expected_version}, "
            f"found {current_snapshot.get('version')}"
        )
    if snapshot.get("task_id") != task_id or snapshot.get("owner_id") != owner_id:
        raise TaskStoreConflictError("updated task identity does not match stored task")
    if snapshot.get("version") != expected_version + 1:
        raise TaskStoreConflictError(f"updated task version must be {expected_version + 1}")

    if not events:
        raise TaskStoreConflictError("a task commit must contain at least one event")
    current_sequence = current_snapshot.get("last_event_sequence")
    if not isinstance(current_sequence, int):
        raise TaskStoreConflictError("stored task event sequence is invalid")
    expected_sequences = list(range(current_sequence + 1, current_sequence + len(events) + 1))
    actual_sequences = [event.get("sequence") for event in events]
    if actual_sequences != expected_sequences:
        raise TaskStoreConflictError("task event sequences must be contiguous")
    if any(event.get("task_id") != task_id for event in events):
        raise TaskStoreConflictError("task event identity does not match task")
    if snapshot.get("last_event_sequence") != expected_sequences[-1]:
        raise TaskStoreConflictError("snapshot last_event_sequence does not match committed events")

    existing_ids = {artifact["artifact_version_id"] for artifact in existing_artifact_versions}
    existing_coordinates = {
        (artifact["branch_id"], artifact["deliverable_id"], artifact["version"])
        for artifact in existing_artifact_versions
    }
    new_ids: set[str] = set()
    new_coordinates: set[tuple[str, str, int]] = set()
    for artifact in artifact_versions:
        if artifact.get("task_id") != task_id:
            raise TaskStoreConflictError("artifact task_id does not match task")
        artifact_version_id = artifact.get("artifact_version_id")
        branch_id = artifact.get("branch_id")
        deliverable_id = artifact.get("deliverable_id")
        version = artifact.get("version")
        if not isinstance(artifact_version_id, str) or not artifact_version_id:
            raise TaskStoreConflictError("artifact version id is invalid")
        if not isinstance(branch_id, str) or not branch_id:
            raise TaskStoreConflictError("artifact branch id is invalid")
        if not isinstance(deliverable_id, str) or not deliverable_id:
            raise TaskStoreConflictError("artifact deliverable id is invalid")
        if not isinstance(version, int) or version < 1:
            raise TaskStoreConflictError("artifact version is invalid")
        coordinate = (branch_id, deliverable_id, version)
        if artifact_version_id in existing_ids or artifact_version_id in new_ids:
            raise TaskStoreConflictError(f"artifact version already exists: {artifact_version_id}")
        if coordinate in existing_coordinates or coordinate in new_coordinates:
            raise TaskStoreConflictError("artifact branch/deliverable/version already exists")
        new_ids.add(artifact_version_id)
        new_coordinates.add(coordinate)

    all_artifacts = [*existing_artifact_versions, *artifact_versions]
    artifacts_by_id: dict[str, dict] = {}
    lineage_coordinates: dict[str, tuple[str, str]] = {}
    coordinate_artifact_ids: dict[tuple[str, str], str] = {}
    lineages: dict[str, list[dict]] = {}
    for artifact in all_artifacts:
        artifact_version_id = artifact.get("artifact_version_id")
        artifact_id = artifact.get("artifact_id")
        branch_id = artifact.get("branch_id")
        deliverable_id = artifact.get("deliverable_id")
        version = artifact.get("version")
        if not isinstance(artifact_version_id, str) or not artifact_version_id:
            raise TaskStoreConflictError("artifact version id is invalid")
        if not isinstance(artifact_id, str) or not artifact_id:
            raise TaskStoreConflictError("artifact id is invalid")
        if not isinstance(branch_id, str) or not branch_id:
            raise TaskStoreConflictError("artifact branch id is invalid")
        if not isinstance(deliverable_id, str) or not deliverable_id:
            raise TaskStoreConflictError("artifact deliverable id is invalid")
        if not isinstance(version, int) or version < 1:
            raise TaskStoreConflictError("artifact version is invalid")
        if artifact.get("task_id") != task_id:
            raise TaskStoreConflictError("artifact task_id does not match task")
        if artifact.get("content_digest") != canonical_hash(artifact.get("content", {})):
            raise TaskStoreConflictError("artifact content digest does not match content")
        if artifact_version_id in artifacts_by_id:
            raise TaskStoreConflictError(
                f"artifact version already exists: {artifact_version_id}"
            )
        coordinate = (branch_id, deliverable_id)
        previous_coordinate = lineage_coordinates.setdefault(artifact_id, coordinate)
        if previous_coordinate != coordinate:
            raise TaskStoreConflictError("artifact lineage changed branch or deliverable")
        previous_artifact_id = coordinate_artifact_ids.setdefault(coordinate, artifact_id)
        if previous_artifact_id != artifact_id:
            raise TaskStoreConflictError(
                "branch deliverable contains multiple artifact lineages"
            )
        artifacts_by_id[artifact_version_id] = artifact
        lineages.setdefault(artifact_id, []).append(artifact)

    for lineage in lineages.values():
        lineage.sort(key=lambda item: item["version"])
        parent_version_id = None
        for expected_artifact_version, artifact in enumerate(lineage, start=1):
            if artifact.get("version") != expected_artifact_version:
                raise TaskStoreConflictError("artifact versions must be contiguous")
            if artifact.get("parent_version_id") != parent_version_id:
                raise TaskStoreConflictError("artifact parent version does not match head")
            parent_version_id = artifact["artifact_version_id"]

    snapshot_artifacts = snapshot.get("artifact_versions")
    if not isinstance(snapshot_artifacts, list):
        raise TaskStoreConflictError("snapshot artifact history is invalid")
    if any(not isinstance(artifact, dict) for artifact in snapshot_artifacts):
        raise TaskStoreConflictError("snapshot artifact history is invalid")
    snapshot_artifacts_by_id = {
        artifact.get("artifact_version_id"): artifact for artifact in snapshot_artifacts
    }
    if len(snapshot_artifacts_by_id) != len(snapshot_artifacts):
        raise TaskStoreConflictError("snapshot artifact history contains duplicate ids")
    if set(snapshot_artifacts_by_id) != set(artifacts_by_id):
        raise TaskStoreConflictError("snapshot artifact history does not match store")
    if any(
        snapshot_artifacts_by_id[artifact_id] != artifact
        for artifact_id, artifact in artifacts_by_id.items()
    ):
        raise TaskStoreConflictError("snapshot attempted to mutate artifact history")

    branches = snapshot.get("branches")
    if not isinstance(branches, list):
        raise TaskStoreConflictError("snapshot branches are invalid")
    latest_by_coordinate = {
        coordinate: max(
            (
                artifact
                for artifact in all_artifacts
                if (artifact["branch_id"], artifact["deliverable_id"]) == coordinate
            ),
            key=lambda item: item["version"],
        )
        for coordinate in coordinate_artifact_ids
    }
    seen_branch_ids: set[str] = set()
    seen_head_coordinates: set[tuple[str, str]] = set()
    for branch in branches:
        if not isinstance(branch, dict):
            raise TaskStoreConflictError("snapshot branches are invalid")
        branch_id = branch.get("branch_id")
        if not isinstance(branch_id, str) or not branch_id or branch_id in seen_branch_ids:
            raise TaskStoreConflictError("snapshot branch id is invalid")
        seen_branch_ids.add(branch_id)
        if branch.get("task_id") != task_id:
            raise TaskStoreConflictError("snapshot branch task_id does not match task")
        deliverable_ids = branch.get("deliverable_ids")
        if not isinstance(deliverable_ids, list) or any(
            not isinstance(deliverable_id, str) or not deliverable_id
            for deliverable_id in deliverable_ids
        ):
            raise TaskStoreConflictError("snapshot branch deliverables are invalid")
        heads = branch.get("artifact_heads", {})
        if not isinstance(heads, dict):
            raise TaskStoreConflictError("branch artifact heads are invalid")
        for deliverable_id, artifact_version_id in heads.items():
            if deliverable_id not in deliverable_ids:
                raise TaskStoreConflictError("branch head references an undeclared deliverable")
            artifact = artifacts_by_id.get(artifact_version_id)
            if artifact is None:
                raise TaskStoreConflictError("branch head references an unknown artifact")
            coordinate = (branch_id, deliverable_id)
            seen_head_coordinates.add(coordinate)
            if (artifact["branch_id"], artifact["deliverable_id"]) != coordinate:
                raise TaskStoreConflictError("branch head references another deliverable")
            if latest_by_coordinate.get(coordinate) != artifact:
                raise TaskStoreConflictError("branch head is not the latest artifact version")
    if set(latest_by_coordinate) != seen_head_coordinates:
        raise TaskStoreConflictError("snapshot is missing an artifact lineage head")


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
            snapshot for snapshot in self._tasks.values() if snapshot["owner_id"] == owner_id
        ]
        snapshots.sort(key=lambda item: item["updated_at"], reverse=True)
        return [
            StoredTask(
                snapshot=deepcopy(snapshot),
                artifact_versions=deepcopy(self._artifact_versions.get(snapshot["task_id"], [])),
            )
            for snapshot in snapshots
        ]

    async def load_events(self, task_id: str, owner_id: str, after_sequence: int = 0) -> list[dict]:
        snapshot = self._tasks.get(task_id)
        if snapshot is None or snapshot["owner_id"] != owner_id:
            return []
        return [
            deepcopy(event)
            for event in self._events.get(task_id, [])
            if event["sequence"] > after_sequence
        ]

    async def commit(
        self,
        task_id: str,
        owner_id: str,
        expected_version: int,
        snapshot: dict,
        events: list[dict],
        artifact_versions: list[dict],
    ) -> StoredTask:
        async with self._lock:
            current_snapshot = self._tasks.get(task_id)
            if current_snapshot is None or current_snapshot.get("owner_id") != owner_id:
                raise TaskStoreNotFoundError(task_id)
            current_events = self._events.get(task_id, [])
            current_artifacts = self._artifact_versions.get(task_id, [])
            stored_event_ids = {
                event["event_id"] for task_events in self._events.values() for event in task_events
            }
            new_event_ids = [event.get("event_id") for event in events]
            if len(new_event_ids) != len(set(new_event_ids)) or any(
                event_id in stored_event_ids for event_id in new_event_ids
            ):
                raise TaskStoreConflictError("task event id already exists")
            stored_idempotency_keys = {
                event["idempotency_key"]
                for event in current_events
                if event.get("idempotency_key") is not None
            }
            new_idempotency_keys = [
                event["idempotency_key"]
                for event in events
                if event.get("idempotency_key") is not None
            ]
            if len(new_idempotency_keys) != len(set(new_idempotency_keys)) or any(
                key in stored_idempotency_keys for key in new_idempotency_keys
            ):
                raise TaskStoreConflictError("task event idempotency key already exists")
            stored_artifact_ids = {
                artifact["artifact_version_id"]
                for task_artifacts in self._artifact_versions.values()
                for artifact in task_artifacts
            }
            if any(
                artifact.get("artifact_version_id") in stored_artifact_ids
                for artifact in artifact_versions
            ):
                raise TaskStoreConflictError("artifact version id already exists")
            _validate_commit(
                task_id=task_id,
                owner_id=owner_id,
                expected_version=expected_version,
                current_snapshot=current_snapshot,
                snapshot=snapshot,
                events=events,
                artifact_versions=artifact_versions,
                existing_artifact_versions=current_artifacts,
            )

            updated_snapshot = deepcopy(snapshot)
            updated_events = [*deepcopy(current_events), *deepcopy(events)]
            updated_artifacts = [
                *deepcopy(current_artifacts),
                *deepcopy(artifact_versions),
            ]
            updated_artifacts.sort(
                key=lambda item: (
                    item["branch_id"],
                    item["deliverable_id"],
                    item["version"],
                )
            )
            self._tasks[task_id] = updated_snapshot
            self._events[task_id] = updated_events
            self._artifact_versions[task_id] = updated_artifacts
            return StoredTask(
                snapshot=deepcopy(updated_snapshot),
                artifact_versions=deepcopy(updated_artifacts),
            )


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
            raise TaskStoreConflictError(f"task already exists: {snapshot['task_id']}") from exc

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

    async def load_events(self, task_id: str, owner_id: str, after_sequence: int = 0) -> list[dict]:
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

    async def commit(
        self,
        task_id: str,
        owner_id: str,
        expected_version: int,
        snapshot: dict,
        events: list[dict],
        artifact_versions: list[dict],
    ) -> StoredTask:
        try:
            async with await psycopg.AsyncConnection.connect(self.dsn) as connection:
                row = await (
                    await connection.execute(
                        """
                        SELECT owner_id, version, last_event_sequence, snapshot
                        FROM agent_tasks
                        WHERE task_id = %s
                        FOR UPDATE
                        """,
                        (task_id,),
                    )
                ).fetchone()
                if row is None or row[0] != owner_id:
                    raise TaskStoreNotFoundError(task_id)
                if row[3].get("version") != row[1] or row[3].get("last_event_sequence") != row[2]:
                    raise TaskStoreConflictError("stored task columns do not match its snapshot")

                artifact_rows = await (
                    await connection.execute(
                        """
                        SELECT artifact
                        FROM agent_task_artifact_versions
                        WHERE task_id = %s
                        ORDER BY branch_id, deliverable_id, version
                        """,
                        (task_id,),
                    )
                ).fetchall()
                existing_artifacts = [item[0] for item in artifact_rows]
                _validate_commit(
                    task_id=task_id,
                    owner_id=owner_id,
                    expected_version=expected_version,
                    current_snapshot=row[3],
                    snapshot=snapshot,
                    events=events,
                    artifact_versions=artifact_versions,
                    existing_artifact_versions=existing_artifacts,
                )

                for artifact in artifact_versions:
                    await self._insert_artifact_version(connection, artifact)
                for event in events:
                    await self._insert_event(connection, event)
                await connection.execute(
                    """
                    UPDATE agent_tasks
                    SET status = %s,
                        phase = %s,
                        version = %s,
                        snapshot = %s,
                        last_event_sequence = %s,
                        updated_at = %s
                    WHERE task_id = %s AND owner_id = %s
                    """,
                    (
                        snapshot["status"],
                        snapshot["phase"],
                        snapshot["version"],
                        Jsonb(snapshot),
                        snapshot["last_event_sequence"],
                        snapshot["updated_at"],
                        task_id,
                        owner_id,
                    ),
                )
                committed_rows = await (
                    await connection.execute(
                        """
                        SELECT artifact
                        FROM agent_task_artifact_versions
                        WHERE task_id = %s
                        ORDER BY branch_id, deliverable_id, version
                        """,
                        (task_id,),
                    )
                ).fetchall()
                stored = StoredTask(
                    snapshot=deepcopy(snapshot),
                    artifact_versions=deepcopy([item[0] for item in committed_rows]),
                )
            return stored
        except psycopg.errors.UniqueViolation as exc:
            raise TaskStoreConflictError("task commit conflicts with stored data") from exc

    @staticmethod
    async def _insert_artifact_version(connection: psycopg.AsyncConnection, artifact: dict) -> None:
        await connection.execute(
            """
            INSERT INTO agent_task_artifact_versions (
                artifact_version_id, task_id, branch_id, deliverable_id,
                version, content_digest, artifact, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                artifact["artifact_version_id"],
                artifact["task_id"],
                artifact["branch_id"],
                artifact["deliverable_id"],
                artifact["version"],
                artifact["content_digest"],
                Jsonb(artifact),
                artifact["created_at"],
            ),
        )

    @staticmethod
    async def _insert_event(connection: psycopg.AsyncConnection, event: dict) -> None:
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
