"""Owner-scoped teardown for disposable PostgreSQL integration fixtures."""

from __future__ import annotations

import re

import psycopg
from psycopg import sql

# Delete dependent ledgers before their Run. Keep this list aligned with setup().
HARNESS_TABLES = (
    "harness_contribution",
    "harness_work_unit",
    "harness_task_ledger_receipt",
    "harness_task_ledger",
    "harness_idempotency",
    "harness_task_commit",
    "harness_artifact_version",
    "harness_run_state",
)


async def cleanup_postgres_owner(dsn: str, owner: str) -> None:
    """Atomically remove only one uniquely named test owner's complete aggregate."""
    if not dsn.strip() or not re.fullmatch(
        r"(?:postgres|task-ledger)-[a-z0-9-]+-[0-9a-f]{32}", owner
    ):
        raise ValueError("Cleanup requires a DSN and a UUID-suffixed PostgreSQL test owner")
    async with await psycopg.AsyncConnection.connect(dsn) as connection:
        async with connection.cursor() as cursor:
            for table in HARNESS_TABLES:
                await cursor.execute(
                    sql.SQL("DELETE FROM {} WHERE owner_id = %s").format(sql.Identifier(table)),
                    (owner,),
                )
