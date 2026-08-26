from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import psycopg
import pytest

from packages.contracts.harness_models import AgentControlLoopControlRequest
from services.api.app.application.harness_runtime import HarnessRuntime
from services.api.app.application.harness_storage import PostgresHarnessStateStore
from tests.unit.test_harness_runtime import (
    BlockingPlanner,
    FakeAnalyst,
    FakeCatalog,
    FakePlanner,
    confirm_evidence_gate,
    start_request,
    wait_terminal,
)


DATABASE_DSN = os.getenv("TEST_DATABASE_DSN", "").strip()
pytestmark = pytest.mark.skipif(
    not DATABASE_DSN,
    reason="TEST_DATABASE_DSN is required for real PostgreSQL restart validation",
)


@pytest.mark.asyncio
async def test_postgres_recovers_loop_artifacts_commits_and_restore_pointer() -> None:
    owner = f"postgres-restart-{uuid4().hex}"
    run_id = ""
    runtimes: list[HarnessRuntime] = []
    try:
        blocking = BlockingPlanner()
        first = HarnessRuntime(
            FakeCatalog(),
            blocking,
            FakeAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(first)
        await first.setup()
        request = start_request(
            idempotency_key=f"postgres-start-{uuid4().hex}",
        )
        started = await first.start(owner, request)
        run_id = started.run.run_id
        await asyncio.wait_for(blocking.started.wait(), timeout=3)
        await first.close()

        second = HarnessRuntime(
            FakeCatalog(),
            FakePlanner(),
            FakeAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(second)
        await second.setup()
        recovered = await second.get(owner, run_id)
        assert recovered.status == "paused"
        assert recovered.events[-1].event_name == "checkpoint_recovered"
        await second.control(
            owner,
            run_id,
            AgentControlLoopControlRequest(
                command="resume",
                idempotency_key=f"postgres-resume-{uuid4().hex}",
                expected_version=recovered.version,
            ),
        )
        await confirm_evidence_gate(
            second,
            owner,
            run_id,
            f"postgres-gate-{uuid4().hex}",
        )
        terminal = await wait_terminal(second, owner, run_id)
        assert terminal.status == "completed"
        assert terminal.last_commit and terminal.last_commit.artifact_version == 2
        await second.close()

        third_store = PostgresHarnessStateStore(DATABASE_DSN)
        third = HarnessRuntime(
            FakeCatalog(), FakePlanner(), FakeAnalyst(), third_store
        )
        runtimes.append(third)
        await third.setup()
        after_restart = await third.get(owner, run_id)
        assert after_restart.status == "completed"
        assert len(await third_store.load_artifact_versions(owner, run_id)) == 2
        assert len(await third_store.load_task_commits(owner, run_id)) == 1
        restored = await third.control(
            owner,
            run_id,
            AgentControlLoopControlRequest(
                command="rollback",
                artifact_version=1,
                idempotency_key=f"postgres-rollback-{uuid4().hex}",
                expected_version=after_restart.version,
            ),
        )
        assert restored.run.last_commit
        assert restored.run.last_commit.artifact_version == 1
        await third.close()

        fourth = HarnessRuntime(
            FakeCatalog(),
            FakePlanner(),
            FakeAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(fourth)
        await fourth.setup()
        final = await fourth.get(owner, run_id)
        assert final.last_commit and final.last_commit.artifact_version == 1
        assert len(final.commits) == 2
    finally:
        for runtime in reversed(runtimes):
            await runtime.close()
        if DATABASE_DSN and run_id:
            async with await psycopg.AsyncConnection.connect(DATABASE_DSN) as connection:
                async with connection.cursor() as cursor:
                    for table in (
                        "harness_idempotency",
                        "harness_task_commit",
                        "harness_artifact_version",
                        "harness_run_state",
                    ):
                        await cursor.execute(
                            f"DELETE FROM {table} WHERE owner_id = %s",  # nosec B608
                            (owner,),
                        )
