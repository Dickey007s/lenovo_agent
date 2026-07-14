from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from packages.contracts import AuditEvent


class InMemoryAuditLog:
    def __init__(self) -> None:
        self._events: dict[str, list[AuditEvent]] = defaultdict(list)
        self._subscribers: dict[str, set[asyncio.Queue[AuditEvent]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def append(
        self,
        *,
        run_id: str,
        trace_id: str,
        actor_id: str,
        event_type: str,
        action_id: str | None = None,
        payload: dict | None = None,
    ) -> AuditEvent:
        async with self._lock:
            event = AuditEvent(
                sequence=len(self._events[run_id]) + 1,
                event_id=f"evt_{uuid4().hex}",
                run_id=run_id,
                trace_id=trace_id,
                action_id=action_id,
                actor_id=actor_id,
                event_type=event_type,
                payload=payload or {},
                occurred_at=datetime.now(UTC),
            )
            self._events[run_id].append(event)
            subscribers = list(self._subscribers[run_id])
        for queue in subscribers:
            queue.put_nowait(event)
        return event

    async def setup(self) -> None:
        return None

    async def history(self, run_id: str) -> list[AuditEvent]:
        return list(self._events.get(run_id, []))

    async def stream(
        self, run_id: str, after_sequence: int = 0
    ) -> AsyncIterator[AuditEvent | None]:
        for event in await self.history(run_id):
            if event.sequence > after_sequence:
                yield event
        queue: asyncio.Queue[AuditEvent] = asyncio.Queue()
        self._subscribers[run_id].add(queue)
        try:
            while True:
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield None
        finally:
            self._subscribers[run_id].discard(queue)


class PostgresAuditLog(InMemoryAuditLog):
    def __init__(self, dsn: str) -> None:
        super().__init__()
        self.dsn = dsn

    async def setup(self) -> None:
        async with await psycopg.AsyncConnection.connect(self.dsn) as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    sequence BIGSERIAL PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                    trace_id TEXT NOT NULL,
                    action_id TEXT,
                    actor_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                    occurred_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            await connection.execute(
                "CREATE INDEX IF NOT EXISTS audit_trace_sequence_idx "
                "ON audit_events(trace_id, sequence)"
            )

    async def append(
        self,
        *,
        run_id: str,
        trace_id: str,
        actor_id: str,
        event_type: str,
        action_id: str | None = None,
        payload: dict | None = None,
    ) -> AuditEvent:
        event_id = f"evt_{uuid4().hex}"
        occurred_at = datetime.now(UTC)
        async with await psycopg.AsyncConnection.connect(self.dsn) as connection:
            row = await (
                await connection.execute(
                    """
                    INSERT INTO audit_events (
                        event_id, run_id, trace_id, action_id, actor_id,
                        event_type, payload, occurred_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING sequence
                    """,
                    (
                        event_id,
                        run_id,
                        trace_id,
                        action_id,
                        actor_id,
                        event_type,
                        Jsonb(payload or {}),
                        occurred_at,
                    ),
                )
            ).fetchone()
        event = AuditEvent(
            sequence=row[0],
            event_id=event_id,
            run_id=run_id,
            trace_id=trace_id,
            action_id=action_id,
            actor_id=actor_id,
            event_type=event_type,
            payload=payload or {},
            occurred_at=occurred_at,
        )
        for queue in list(self._subscribers[run_id]):
            queue.put_nowait(event)
        return event

    async def history(self, run_id: str) -> list[AuditEvent]:
        async with await psycopg.AsyncConnection.connect(self.dsn) as connection:
            rows = await (
                await connection.execute(
                    """
                    SELECT sequence, event_id, run_id, trace_id, action_id,
                           actor_id, event_type, payload, occurred_at
                    FROM audit_events WHERE run_id = %s ORDER BY sequence
                    """,
                    (run_id,),
                )
            ).fetchall()
        return [
            AuditEvent(
                sequence=row[0],
                event_id=row[1],
                run_id=row[2],
                trace_id=row[3],
                action_id=row[4],
                actor_id=row[5],
                event_type=row[6],
                payload=row[7],
                occurred_at=row[8],
            )
            for row in rows
        ]
