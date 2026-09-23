import inspect
import re
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from services.api.app.application.harness_storage import PostgresHarnessStateStore
from tests.postgres_helpers import HARNESS_TABLES, cleanup_postgres_owner


def test_cleanup_covers_every_harness_table() -> None:
    schema = inspect.getsource(PostgresHarnessStateStore.setup)
    tables = re.findall(r"CREATE TABLE IF NOT EXISTS (harness_\w+)", schema)
    assert set(HARNESS_TABLES) == set(tables)
    assert len(HARNESS_TABLES) == len(set(HARNESS_TABLES))
    assert HARNESS_TABLES[-1] == "harness_run_state"


@pytest.mark.parametrize("owner", ["", "demo_user", "postgres-test", "postgres-x-' OR 1=1"])
async def test_cleanup_rejects_non_fixture_owners_before_connecting(owner: str) -> None:
    with patch("tests.postgres_helpers.psycopg.AsyncConnection.connect") as connect:
        with pytest.raises(ValueError):
            await cleanup_postgres_owner("postgresql://test", owner)
        connect.assert_not_called()


async def test_cleanup_rejects_empty_dsn() -> None:
    with pytest.raises(ValueError):
        await cleanup_postgres_owner(" ", f"postgres-cleanup-{uuid4().hex}")


async def test_cleanup_uses_one_transaction_and_owner_parameter() -> None:
    owner = f"postgres-cleanup-{uuid4().hex}"
    connection = AsyncMock()
    connection.__aenter__.return_value = connection
    cursor = AsyncMock()
    connection.cursor = lambda: cursor
    cursor.__aenter__.return_value = cursor
    with patch(
        "tests.postgres_helpers.psycopg.AsyncConnection.connect",
        new=AsyncMock(return_value=connection),
    ) as connect:
        await cleanup_postgres_owner("postgresql://test", owner)
    connect.assert_awaited_once_with("postgresql://test")
    assert cursor.execute.await_count == len(HARNESS_TABLES)
    for table, call in zip(HARNESS_TABLES, cursor.execute.await_args_list, strict=True):
        assert call.args[0].as_string() == f'DELETE FROM "{table}" WHERE owner_id = %s'
        assert call.args[1] == (owner,)
    connection.__aexit__.assert_awaited_once_with(None, None, None)
