from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import psycopg
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class StoredRun:
    snapshot: dict
    submitted_evidence: dict


class RunStore(Protocol):
    async def setup(self) -> None: ...

    async def save(self, snapshot: dict, submitted_evidence: dict) -> None: ...

    async def load_all(self) -> list[StoredRun]: ...


class WorkspaceStore(Protocol):
    async def setup(self) -> None: ...

    async def load(self, user_id: str) -> list[dict]: ...

    async def save(self, user_id: str, artifact: dict) -> None: ...


class InMemoryWorkspaceStore:
    def __init__(self) -> None:
        self._artifacts: dict[tuple[str, str], dict] = {}

    async def setup(self) -> None:
        return None

    async def load(self, user_id: str) -> list[dict]:
        return [
            artifact
            for (owner, _), artifact in self._artifacts.items()
            if owner == user_id
        ]

    async def save(self, user_id: str, artifact: dict) -> None:
        self._artifacts[(user_id, artifact["kind"])] = artifact


class InMemoryRunStore:
    async def setup(self) -> None:
        return None

    async def save(self, snapshot: dict, submitted_evidence: dict) -> None:
        return None

    async def load_all(self) -> list[StoredRun]:
        return []


class PostgresRunStore:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    async def setup(self) -> None:
        async with await psycopg.AsyncConnection.connect(self.dsn) as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL UNIQUE,
                    action_id TEXT NOT NULL UNIQUE,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    snapshot JSONB NOT NULL,
                    submitted_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            await connection.execute(
                "CREATE INDEX IF NOT EXISTS runs_user_updated_idx ON runs(user_id, updated_at DESC)"
            )

    async def save(self, snapshot: dict, submitted_evidence: dict) -> None:
        async with await psycopg.AsyncConnection.connect(self.dsn) as connection:
            await connection.execute(
                """
                INSERT INTO runs (
                    run_id, trace_id, action_id, user_id, status, snapshot,
                    submitted_evidence, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    snapshot = EXCLUDED.snapshot,
                    submitted_evidence = EXCLUDED.submitted_evidence,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    snapshot["run_id"],
                    snapshot["trace_id"],
                    snapshot["action"]["action_id"],
                    snapshot["user_id"],
                    snapshot["status"],
                    Jsonb(snapshot),
                    Jsonb(submitted_evidence),
                    snapshot["created_at"],
                    snapshot["updated_at"],
                ),
            )

    async def load_all(self) -> list[StoredRun]:
        async with await psycopg.AsyncConnection.connect(self.dsn) as connection:
            rows = await (
                await connection.execute(
                    "SELECT snapshot, submitted_evidence FROM runs ORDER BY created_at"
                )
            ).fetchall()
        return [StoredRun(snapshot=row[0], submitted_evidence=row[1]) for row in rows]


class PostgresWorkspaceStore:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    async def setup(self) -> None:
        async with await psycopg.AsyncConnection.connect(self.dsn) as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workspace_artifacts (
                    user_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    artifact_id TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    artifact JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    PRIMARY KEY (user_id, kind)
                )
                """
            )
            await connection.execute(
                "CREATE INDEX IF NOT EXISTS workspace_artifacts_updated_idx "
                "ON workspace_artifacts(user_id, updated_at DESC)"
            )

    async def load(self, user_id: str) -> list[dict]:
        async with await psycopg.AsyncConnection.connect(self.dsn) as connection:
            rows = await (
                await connection.execute(
                    "SELECT artifact FROM workspace_artifacts "
                    "WHERE user_id = %s ORDER BY kind",
                    (user_id,),
                )
            ).fetchall()
        return [row[0] for row in rows]

    async def save(self, user_id: str, artifact: dict) -> None:
        async with await psycopg.AsyncConnection.connect(self.dsn) as connection:
            await connection.execute(
                """
                INSERT INTO workspace_artifacts (
                    user_id, kind, artifact_id, title, artifact, updated_at
                ) VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (user_id, kind) DO UPDATE SET
                    artifact_id = EXCLUDED.artifact_id,
                    title = EXCLUDED.title,
                    artifact = EXCLUDED.artifact,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    user_id,
                    artifact["kind"],
                    artifact["artifact_id"],
                    artifact["title"],
                    Jsonb(artifact),
                ),
            )
