from __future__ import annotations

import asyncio
import os
from pathlib import Path
from uuid import uuid4

import pytest

from tests.postgres_helpers import cleanup_postgres_owner

from packages.contracts.harness_models import (
    AgentControlLoopArtifactFinding,
    AgentControlLoopControlRequest,
)
from services.api.app.application.harness_runtime import (
    HarnessConflictError,
    HarnessPlanCandidate,
    HarnessPlanCandidateUnit,
    HarnessRunStart,
    HarnessRuntime,
)
from services.api.app.application.harness_storage import PostgresHarnessStateStore
from services.api.app.application.readonly_workers import (
    ReadonlyWorkerContribution,
    ReadonlyWorkerRequest,
)
from tests.unit.test_harness_runtime import (
    AlwaysUnlocatableAnalyst,
    FakeAnalyst,
    FakeCatalog,
    FakePlanner,
)
from tests.unit.test_demo2_runtime import _cross_function_catalog


DATABASE_DSN = os.getenv("TEST_DATABASE_DSN", "").strip()
pytestmark = pytest.mark.skipif(
    not DATABASE_DSN,
    reason="TEST_DATABASE_DSN is required for real PostgreSQL Demo 1/2 restart validation",
)


async def _wait_for_status(runtime: HarnessRuntime, owner: str, run_id: str, statuses: set[str]):
    deadline = asyncio.get_running_loop().time() + 30
    while asyncio.get_running_loop().time() < deadline:
        snapshot = await runtime.get(owner, run_id)
        if snapshot.status in statuses:
            return snapshot
        await asyncio.sleep(0.05)
    raise AssertionError(f"run did not reach {statuses}")


async def _cleanup(owner: str) -> None:
    await cleanup_postgres_owner(DATABASE_DSN, owner)


@pytest.mark.asyncio
async def test_postgres_demo1_continuation_lineage_cas_and_restart(tmp_path: Path) -> None:
    """A continuation is a same-task child and survives a store restart without rewriting its parent."""

    owner = f"postgres-demo1-{uuid4().hex}"
    runtimes: list[HarnessRuntime] = []
    parent_id = ""
    try:
        first = HarnessRuntime(
            FakeCatalog(),
            FakePlanner(),
            AlwaysUnlocatableAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(first)
        await first.setup()
        started = await first.start(
            owner,
            HarnessRunStart(
                idempotency_key=f"demo1-parent-{uuid4().hex}",
                instruction="保留一个待核对分支",
                loop={"max_rounds": 1, "max_files_per_round": 2, "max_model_calls": 4, "deadline_seconds": 60},
            ),
        )
        parent_id = started.run.run_id
        parent = await _wait_for_status(first, owner, parent_id, {"stopped", "waiting_input"})
        if parent.status == "waiting_input":
            stopped = await first.control(
                owner,
                parent_id,
                AgentControlLoopControlRequest(
                    command="stop",
                    expected_version=parent.version,
                    idempotency_key=f"demo1-stop-{uuid4().hex}",
                ),
            )
            parent = await _wait_for_status(first, owner, parent_id, {"stopped"})
            assert stopped.run.run_id == parent_id
        branch = next(item for item in parent.branches if item.status != "completed")
        parent_dump = parent.model_dump(mode="json")
        child_idem = f"demo1-child-{uuid4().hex}"
        child = await first.continue_unfinished_task(
            owner,
            parent_id,
            branch.branch_id,
            idempotency_key=child_idem,
            expected_version=parent.version,
            expected_task_version=parent.task_version,
        )
        assert child.run.task_id == parent.task_id
        assert child.run.parent_run_id == parent_id
        assert child.run.run_sequence == parent.run_sequence + 1
        assert child.run.carried_branch_id == branch.branch_id
        assert set(child.run.recheck_file_refs) == set(branch.missing_file_refs or branch.input_file_refs)
        await first.close()
        runtimes.clear()

        second = HarnessRuntime(
            FakeCatalog(),
            FakePlanner(),
            AlwaysUnlocatableAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(second)
        await second.setup()
        restored_parent = await second.get(owner, parent_id)
        restored_child = await second.get(owner, child.run.run_id)
        assert restored_parent.model_dump(mode="json") == parent_dump
        assert restored_child.task_id == parent.task_id
        assert restored_child.parent_run_id == parent_id
        replay = await second.continue_unfinished_task(
            owner,
            parent_id,
            branch.branch_id,
            idempotency_key=child_idem,
            expected_version=parent.version,
            expected_task_version=parent.task_version,
        )
        assert replay.replayed is True
        assert replay.run.run_id == child.run.run_id
        with pytest.raises(Exception, match="版本"):
            await second.continue_unfinished_task(
                owner,
                parent_id,
                branch.branch_id,
                idempotency_key=f"demo1-old-version-{uuid4().hex}",
                expected_version=parent.version - 1,
                expected_task_version=parent.task_version,
            )
        with pytest.raises(Exception):
            await second.continue_unfinished_task(
                "different-owner",
                parent_id,
                branch.branch_id,
                idempotency_key=f"demo1-owner-{uuid4().hex}",
                expected_version=parent.version,
                expected_task_version=parent.task_version,
            )
    finally:
        for runtime in reversed(runtimes):
            await runtime.close()
        if DATABASE_DSN:
            await _cleanup(owner)


class TwoUnitPlanner:
    model = "test-planner"

    async def plan(self, *, scenario, files):
        refs = [str(item["file_ref"]) for item in files[:2]]
        return HarnessPlanCandidate(
            summary="两个跨职能只读工作包",
            selection_reason="来源结构允许受限并行",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id=f"unit-{index}",
                    title=f"工作包 {index}",
                    objective=f"核对来源 {index}",
                    input_file_refs=[ref],
                    tool="file.read",
                )
                for index, ref in enumerate(refs, 1)
            ],
        )


@pytest.mark.asyncio
async def test_postgres_demo2_worker_artifact_receipt_restart_without_replay() -> None:
    """Committed Worker contributions and idempotency survive restart; setup never replays them."""

    owner = f"postgres-demo2-{uuid4().hex}"
    runtimes: list[HarnessRuntime] = []
    run_id = ""
    try:
        first = HarnessRuntime(
            _cross_function_catalog(),
            TwoUnitPlanner(),
            FakeAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(first)
        await first.setup()
        started = await first.start(
            owner,
            HarnessRunStart(
                idempotency_key=f"demo2-start-{uuid4().hex}",
                instruction="核对两个独立来源",
                loop={"max_rounds": 1, "max_files_per_round": 2, "max_model_calls": 4, "deadline_seconds": 60},
            ),
        )
        run_id = started.run.run_id
        waiting = await _wait_for_status(first, owner, run_id, {"waiting_input"})
        assert waiting.topology_admission and waiting.topology_admission.mode == "adaptive_readonly_workers"
        branches = [item for item in waiting.branches if item.status == "running"]
        assert len(branches) == 2
        idem = f"demo2-workers-{uuid4().hex}"

        async def handler(request: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
            return ReadonlyWorkerContribution(
                worker_run_id=request.worker_run_id,
                branch_id=request.branch_id,
                outcome="adopted",
                summary="已核对来源",
                source_file_refs=request.source_file_refs,
                evidence_anchors=("line:1",),
                model_called=True,
                output_used=True,
                findings=(
                    AgentControlLoopArtifactFinding(
                        finding_id=f"finding-{request.branch_id[-12:]}",
                        plan_unit_id=next(item.unit_id for item in branches if item.branch_id == request.branch_id),
                        affected_branch_ids=[request.branch_id],
                        title="可审查来源事实",
                        detail="贡献已通过分支来源门。",
                        file_refs=list(request.source_file_refs),
                    ),
                ),
            )

        requests = [
            ReadonlyWorkerRequest(
                worker_run_id=f"worker-{index}",
                branch_id=branch.branch_id,
                goal=branch.objective,
                source_file_refs=tuple(branch.input_file_refs),
                expected_version=waiting.version,
            )
            for index, branch in enumerate(branches, 1)
        ]
        committed = await first.execute_admitted_readonly_workers(
            owner,
            run_id,
            expected_version=waiting.version,
            idempotency_key=idem,
            worker_requests=requests,
            handler=handler,
            user_confirmed=True,
        )
        assert len(committed.worker_runs) == 2
        assert committed.artifact_versions and committed.artifact_versions[-1].findings
        await first.close()
        runtimes.clear()

        second = HarnessRuntime(
            _cross_function_catalog(),
            TwoUnitPlanner(),
            FakeAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(second)
        await second.setup()
        restored = await second.get(owner, run_id)
        assert len(restored.worker_runs) == 2
        assert restored.worker_idempotency.get(idem)
        assert restored.artifact_versions[-1].finding_count == 2
        assert not getattr(second, "_tasks", {})
        replay = await second.execute_admitted_readonly_workers(
            owner,
            run_id,
            expected_version=committed.version,
            idempotency_key=idem,
            worker_requests=requests,
            handler=handler,
            user_confirmed=True,
        )
        assert len(replay.worker_runs) == 2
        assert len(replay.artifact_versions) == len(restored.artifact_versions)
    finally:
        for runtime in reversed(runtimes):
            await runtime.close()
        if DATABASE_DSN:
            await _cleanup(owner)


@pytest.mark.asyncio
async def test_postgres_demo2_interrupted_worker_reservation_is_not_replayed() -> None:
    """A persisted pre-dispatch reservation does not auto-run after restart."""

    owner = f"postgres-demo2-interrupted-{uuid4().hex}"
    runtimes: list[HarnessRuntime] = []
    run_id = ""
    try:
        first = HarnessRuntime(
            _cross_function_catalog(),
            TwoUnitPlanner(),
            FakeAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(first)
        await first.setup()
        started = await first.start(
            owner,
            HarnessRunStart(
                idempotency_key=f"demo2-interrupted-start-{uuid4().hex}",
                instruction="核对两个独立来源",
                loop={"max_rounds": 1, "max_files_per_round": 2, "max_model_calls": 4, "deadline_seconds": 60},
            ),
        )
        run_id = started.run.run_id
        waiting = await _wait_for_status(first, owner, run_id, {"waiting_input"})
        branch = next(item for item in waiting.branches if item.status == "running")
        request = ReadonlyWorkerRequest(
            worker_run_id="worker-interrupted",
            branch_id=branch.branch_id,
            goal=branch.objective,
            source_file_refs=tuple(branch.input_file_refs),
            expected_version=waiting.version,
        )
        entered = asyncio.Event()

        async def blocking_handler(_request: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
            entered.set()
            await asyncio.Future()
            raise AssertionError("unreachable")

        task = asyncio.create_task(
            first.execute_admitted_readonly_workers(
                owner,
                run_id,
                expected_version=waiting.version,
                idempotency_key="demo2-interrupted-workers-0001",
                worker_requests=[request],
                handler=blocking_handler,
                user_confirmed=True,
            )
        )
        await asyncio.wait_for(entered.wait(), timeout=10)
        reserved = await first.get(owner, run_id)
        assert reserved.budget.model_calls_used == waiting.budget.model_calls_used + 1
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await first.close()
        runtimes.clear()

        second = HarnessRuntime(
            _cross_function_catalog(),
            TwoUnitPlanner(),
            FakeAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(second)
        await second.setup()
        restored = await second.get(owner, run_id)
        assert restored.budget.model_calls_used == reserved.budget.model_calls_used
        assert restored.worker_runs == []
        assert not getattr(second, "_tasks", {})
        assert {item.branch_id for item in restored.work_units} == {
            item.branch_id for item in restored.branches
        }
        assert all(
            item.approved_file_refs
            == next(branch for branch in restored.branches if branch.branch_id == item.branch_id).input_file_refs
            for item in restored.work_units
        )

        # A byte-for-byte replay of the original command reaches the durable
        # reservation and is rejected as an interrupted attempt, not reported
        # as a successful replay.
        before_replay = (await second.get(owner, run_id)).model_dump(mode="json")
        with pytest.raises(HarnessConflictError, match="不会自动重放"):
            await second.execute_admitted_readonly_workers(
                owner,
                run_id,
                expected_version=waiting.version,
                idempotency_key="demo2-interrupted-workers-0001",
                worker_requests=[request],
                handler=blocking_handler,
                user_confirmed=True,
            )
        assert (await second.get(owner, run_id)).model_dump(mode="json") == before_replay

        # Changing expected_version changes the command payload and must be a
        # normal idempotency conflict, also without mutating the snapshot.
        with pytest.raises(HarnessConflictError, match="不同 Worker 命令"):
            await second.execute_admitted_readonly_workers(
                owner,
                run_id,
                expected_version=restored.version,
                idempotency_key="demo2-interrupted-workers-0001",
                worker_requests=[request.model_copy(update={"expected_version": restored.version})],
                handler=blocking_handler,
                user_confirmed=True,
            )
        assert (await second.get(owner, run_id)).model_dump(mode="json") == before_replay

        async def recovery_handler(retry_request: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
            branch_after_recovery = next(
                item for item in (await second.get(owner, run_id)).branches
                if item.branch_id == retry_request.branch_id
            )
            finding = AgentControlLoopArtifactFinding(
                finding_id="finding-checkpoint-retry",
                plan_unit_id=branch_after_recovery.unit_id,
                affected_branch_ids=[retry_request.branch_id],
                title="检查点恢复后的显式重试",
                detail="新的幂等键触发一次明确的只读重试。",
                file_refs=list(retry_request.source_file_refs),
            )
            return ReadonlyWorkerContribution(
                worker_run_id=retry_request.worker_run_id,
                branch_id=retry_request.branch_id,
                outcome="adopted",
                summary="检查点恢复后的只读结果已通过服务端核对。",
                source_file_refs=retry_request.source_file_refs,
                evidence_anchors=("line:1",),
                model_called=True,
                output_used=True,
                elapsed_ms=1,
                findings=(finding,),
            )

        restored_branch = next(
            item for item in restored.branches if item.branch_id == request.branch_id
        )
        retry_request = ReadonlyWorkerRequest(
            worker_run_id="worker-checkpoint-retry",
            branch_id=restored_branch.branch_id,
            goal=restored_branch.objective,
            source_file_refs=tuple(restored_branch.input_file_refs),
            expected_version=restored.version,
        )
        retried = await second.execute_admitted_readonly_workers(
            owner,
            run_id,
            expected_version=restored.version,
            idempotency_key="demo2-interrupted-workers-retry-0001",
            worker_requests=[retry_request],
            handler=recovery_handler,
            user_confirmed=True,
        )
        assert retried.contributions[-1].worker_run_id == "worker-checkpoint-retry"
        assert retried.contributions[-1].attempt == 2
        retried_unit = next(item for item in retried.work_units if item.branch_id == request.branch_id)
        assert retried_unit.attempt == 2
    finally:
        for runtime in reversed(runtimes):
            await runtime.close()
        if DATABASE_DSN:
            await _cleanup(owner)
