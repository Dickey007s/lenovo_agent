"""Real SQL regression: complete aggregate cleanup must not touch another owner."""

import os
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from services.api.app.application.harness_storage import PostgresHarnessStateStore
from tests.postgres_helpers import HARNESS_TABLES, cleanup_postgres_owner

DATABASE_DSN = os.getenv("TEST_DATABASE_DSN", "").strip()
pytestmark = pytest.mark.skipif(not DATABASE_DSN, reason="TEST_DATABASE_DSN is required")

# Deliberately minimal raw rows: this test checks teardown, not model validation.
ROWS = {
    "harness_run_state": {"run_id": "run", "snapshot": "{}"},
    "harness_artifact_version": {
        "run_id": "run", "artifact_id": "artifact", "version": 1,
        "payload_digest": "digest", "payload": "{}",
    },
    "harness_task_commit": {
        "run_id": "run", "commit_id": "commit", "payload_digest": "digest", "payload": "{}",
    },
    "harness_idempotency": {
        "kind": "start", "idempotency_key": "key", "digest": "digest", "result": "{}",
    },
    "harness_task_ledger": {"task_id": "task", "task_version": 1, "payload": "{}"},
    "harness_task_ledger_receipt": {
        "idempotency_key": "key", "digest": "digest", "payload": "{}",
    },
    "harness_work_unit": {
        "task_id": "task", "run_id": "run", "work_unit_id": "unit", "version": 1,
        "payload": "{}",
    },
    "harness_contribution": {
        "run_id": "run", "contribution_id": "contribution", "payload_digest": "digest",
        "payload": "{}",
    },
}


async def test_cleanup_removes_all_ledgers_and_preserves_other_owner() -> None:
    owners = [f"postgres-cleanup-{uuid4().hex}" for _ in range(2)]
    store = PostgresHarnessStateStore(DATABASE_DSN)
    await store.setup()
    assert set(ROWS) == set(HARNESS_TABLES)
    try:
        async with await psycopg.AsyncConnection.connect(DATABASE_DSN) as connection:
            for owner in owners:
                for table, fields in ROWS.items():
                    values = {"owner_id": owner, **fields}
                    await connection.execute(
                        sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                            sql.Identifier(table),
                            sql.SQL(", ").join(map(sql.Identifier, values)),
                            sql.SQL(", ").join(sql.Placeholder() for _ in values),
                        ),
                        tuple(values.values()),
                    )
        await cleanup_postgres_owner(DATABASE_DSN, owners[0])
        # Repeated cleanup must be safe, including after a partially completed start.
        await cleanup_postgres_owner(DATABASE_DSN, owners[0])
        async with await psycopg.AsyncConnection.connect(DATABASE_DSN) as connection:
            for table in HARNESS_TABLES:
                for owner, expected in zip(owners, (0, 1), strict=True):
                    cursor = await connection.execute(
                        sql.SQL("SELECT count(*) FROM {} WHERE owner_id = %s").format(
                            sql.Identifier(table)
                        ),
                        (owner,),
                    )
                    assert await cursor.fetchone() == (expected,), (table, owner)
    finally:
        await store.close()
        for owner in owners:
            await cleanup_postgres_owner(DATABASE_DSN, owner)
