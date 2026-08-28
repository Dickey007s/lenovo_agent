from __future__ import annotations

import asyncio
import csv
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from packages.contracts.harness_models import AgentControlLoopControlRequest
from services.api.app.application.harness_runtime import HarnessRuntime
from services.api.app.application.harness_storage import PostgresHarnessStateStore
from services.api.app.application.benchmark_workspace_catalog import (
    BenchmarkWorkspaceCatalog,
)
from services.api.app.application.run_workspace_artifact_store import (
    RunWorkspaceArtifactStore,
)
from services.api.app.application.scenario_effects import ScenarioEffectEngine
from tests.unit.test_scenario_effect_runtime import (
    CandidateReviewAnalyst,
    CandidateReviewPlanner,
    DashboardAnalyst,
    DashboardPlanner,
    FinanceReconciliationAnalyst,
    FinanceReconciliationPlanner,
    FORTE_ROOT,
    TC05_INSTRUCTION,
    TC06_INSTRUCTION,
    TC07_INSTRUCTION,
    TC10_INSTRUCTION,
    ONBOARDING_INSTRUCTION,
    TC11_INSTRUCTION,
    TC12_INSTRUCTION,
    LegalDelegationAnalyst,
    LegalDelegationPlanner,
    OnboardingAnalyst,
    OnboardingPlanner,
    OutboundFlowAnalyst,
    OutboundFlowPlanner,
    ReleaseReadinessAnalyst,
    ReleaseReadinessPlanner,
)
from tests.unit.test_harness_runtime import (
    AmbiguousCatalog,
    BlockingPlanner,
    FakeAnalyst,
    FakeCatalog,
    FakePlanner,
    MixedEvidenceAnalyst,
    confirm_evidence_gate,
    start_request,
    wait_status,
    wait_terminal,
)


DATABASE_DSN = os.getenv("TEST_DATABASE_DSN", "").strip()
pytestmark = pytest.mark.skipif(
    not DATABASE_DSN,
    reason="TEST_DATABASE_DSN is required for real PostgreSQL restart validation",
)


async def wait_for_effect_run(
    runtime: HarnessRuntime,
    owner: str,
    run_id: str,
    *,
    timeout_seconds: float = 60,
):
    """Wait in wall-clock time for a threaded deterministic effect to settle."""

    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds
    while loop.time() < deadline:
        snapshot = await asyncio.wait_for(runtime.get(owner, run_id), timeout=2)
        if snapshot.status in {"ready_to_execute", "completed", "stopped", "failed"}:
            return snapshot
        await asyncio.sleep(0.05)
    raise AssertionError("harness effect run did not settle before the deadline")


@pytest.mark.asyncio
async def test_postgres_restart_preserves_verified_run_workspace_artifact(
    tmp_path: Path,
) -> None:
    owner = f"postgres-workspace-artifact-{uuid4().hex}"
    run_id = ""
    runtimes: list[HarnessRuntime] = []
    workspace_root = tmp_path / "run-workspaces"
    try:
        first = HarnessRuntime(
            BenchmarkWorkspaceCatalog(FORTE_ROOT),
            OnboardingPlanner(),
            OnboardingAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
            effect_engine=ScenarioEffectEngine(),
            artifact_store=RunWorkspaceArtifactStore(workspace_root),
        )
        runtimes.append(first)
        await first.setup()
        started = await first.start(
            owner,
            start_request(
                idempotency_key=f"postgres-workspace-start-{uuid4().hex}",
                instruction=ONBOARDING_INSTRUCTION,
            ),
        )
        run_id = started.run.run_id
        terminal = await wait_terminal(first, owner, run_id)
        assert terminal.status == "completed"
        assert terminal.effect_receipts[0].status == "passed"
        assert terminal.workspace_artifacts[0].verifier_status == "passed"
        artifact_id = terminal.workspace_artifacts[0].artifact_id
        _, original_content = await first.get_workspace_artifact(
            owner, run_id, artifact_id
        )
        await first.close()

        second = HarnessRuntime(
            BenchmarkWorkspaceCatalog(FORTE_ROOT),
            OnboardingPlanner(),
            OnboardingAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
            effect_engine=ScenarioEffectEngine(),
            artifact_store=RunWorkspaceArtifactStore(workspace_root),
        )
        runtimes.append(second)
        await second.setup()
        restored = await second.get(owner, run_id)
        assert restored.status == "completed"
        assert restored.effect_receipts[0].status == "passed"
        assert restored.workspace_artifacts[0].artifact_id == artifact_id
        metadata, restored_content = await second.get_workspace_artifact(
            owner, run_id, artifact_id
        )
        assert restored_content == original_content
        assert metadata.original_inputs_modified is False
        assert metadata.external_action == "none"
        assert "content_sha256" not in second.public_snapshot(restored).model_dump_json()
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


@pytest.mark.asyncio
async def test_postgres_restart_preserves_tc12_real_vitest_artifacts(
    tmp_path: Path,
) -> None:
    owner = f"postgres-tc12-vitest-{uuid4().hex}"
    run_id = ""
    runtimes: list[HarnessRuntime] = []
    workspace_root = tmp_path / "tc12-run-workspaces"
    try:
        first = HarnessRuntime(
            BenchmarkWorkspaceCatalog(FORTE_ROOT),
            DashboardPlanner(),
            DashboardAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
            effect_engine=ScenarioEffectEngine(),
            artifact_store=RunWorkspaceArtifactStore(workspace_root),
        )
        runtimes.append(first)
        await first.setup()
        started = await first.start(
            owner,
            start_request(
                idempotency_key=f"postgres-tc12-start-{uuid4().hex}",
                instruction=TC12_INSTRUCTION,
            ),
        )
        run_id = started.run.run_id
        terminal = None
        for _ in range(600):
            candidate = await first.get(owner, run_id)
            if candidate.status in {"completed", "stopped", "failed"}:
                terminal = candidate
                break
            await asyncio.sleep(0.05)
        assert terminal is not None and terminal.status == "completed"
        assert terminal.effect_receipts[0].status == "passed"
        assert terminal.effect_receipts[0].scenario_id == "TC-12"
        assert len(terminal.workspace_artifacts) == 2
        package = next(
            item
            for item in terminal.workspace_artifacts
            if item.file_name == "看板工具库修复包.zip"
        )
        assert package.verifier_status == "passed"
        assert package.self_test is not None
        assert sum(
            suite.test_count for suite in package.self_test.test_suites
        ) == 71
        _, original_content = await first.get_workspace_artifact(
            owner, run_id, package.artifact_id
        )
        await first.close()

        second = HarnessRuntime(
            BenchmarkWorkspaceCatalog(FORTE_ROOT),
            DashboardPlanner(),
            DashboardAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
            effect_engine=ScenarioEffectEngine(),
            artifact_store=RunWorkspaceArtifactStore(workspace_root),
        )
        runtimes.append(second)
        await second.setup()
        restored = await second.get(owner, run_id)
        assert restored.status == "completed"
        assert restored.effect_receipts[0].scenario_id == "TC-12"
        restored_package = next(
            item
            for item in restored.workspace_artifacts
            if item.artifact_id == package.artifact_id
        )
        assert restored_package.self_test is not None
        assert restored_package.self_test.test_manifest_matches_collected is True
        _, restored_content = await second.get_workspace_artifact(
            owner, run_id, package.artifact_id
        )
        assert restored_content == original_content
        assert "content_sha256" not in second.public_snapshot(
            restored
        ).model_dump_json()
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


@pytest.mark.asyncio
async def test_postgres_restart_preserves_tc11_artifacts_and_business_gates(
    tmp_path: Path,
) -> None:
    owner = f"postgres-tc11-release-{uuid4().hex}"
    run_id = ""
    runtimes: list[HarnessRuntime] = []
    workspace_root = tmp_path / "tc11-run-workspaces"
    try:
        first = HarnessRuntime(
            BenchmarkWorkspaceCatalog(FORTE_ROOT),
            ReleaseReadinessPlanner(),
            ReleaseReadinessAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
            effect_engine=ScenarioEffectEngine(),
            artifact_store=RunWorkspaceArtifactStore(workspace_root),
        )
        runtimes.append(first)
        await first.setup()
        started = await first.start(
            owner,
            start_request(
                idempotency_key=f"postgres-tc11-start-{uuid4().hex}",
                instruction=TC11_INSTRUCTION,
            ),
        )
        run_id = started.run.run_id
        terminal = await wait_for_effect_run(first, owner, run_id)
        assert terminal.status == "completed"
        assert terminal.effect_receipts[0].status == "passed"
        outcome = terminal.effect_receipts[0].business_gate_outcome
        assert outcome is not None
        assert outcome.status == "failed"
        assert outcome.decision == "不得上线"
        assert outcome.failed_gate_count == 4
        assert len(outcome.records) == 18
        assert len(terminal.workspace_artifacts) == 2
        originals: dict[str, bytes] = {}
        for artifact in terminal.workspace_artifacts:
            assert artifact.verifier_status == "passed"
            assert artifact.business_gate_outcome == outcome
            _, originals[artifact.file_name] = await first.get_workspace_artifact(
                owner, run_id, artifact.artifact_id
            )
        await first.close()

        second = HarnessRuntime(
            BenchmarkWorkspaceCatalog(FORTE_ROOT),
            ReleaseReadinessPlanner(),
            ReleaseReadinessAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
            effect_engine=ScenarioEffectEngine(),
            artifact_store=RunWorkspaceArtifactStore(workspace_root),
        )
        runtimes.append(second)
        await second.setup()
        restored = await second.get(owner, run_id)
        restored_outcome = restored.effect_receipts[0].business_gate_outcome
        assert restored_outcome == outcome
        assert len(restored.workspace_artifacts) == 2
        restored_by_name = {
            item.file_name: item for item in restored.workspace_artifacts
        }
        for file_name, content in originals.items():
            artifact = restored_by_name[file_name]
            assert artifact.business_gate_outcome == outcome
            _, restored_content = await second.get_workspace_artifact(
                owner, run_id, artifact.artifact_id
            )
            assert restored_content == content

        with zipfile.ZipFile(
            io.BytesIO(originals["上线合规与风险报告.docx"])
        ) as package:
            document = package.read("word/document.xml").decode("utf-8")
        assert document.count("<w:tbl>") >= 6
        assert "上线结论：不得上线" in document
        rows = list(
            csv.DictReader(
                io.StringIO(
                    originals["上线功能风险逐项台账.csv"].decode("utf-8-sig")
                )
            )
        )
        assert len(rows) == 18
        assert "content_sha256" not in second.public_snapshot(
            restored
        ).model_dump_json()
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


@pytest.mark.asyncio
async def test_postgres_restart_preserves_tc06_candidate_outcome_and_three_artifacts(
    tmp_path: Path,
) -> None:
    owner = f"postgres-tc06-candidate-{uuid4().hex}"
    run_id = ""
    runtimes: list[HarnessRuntime] = []
    workspace_root = tmp_path / "tc06-run-workspaces"
    try:
        first = HarnessRuntime(
            BenchmarkWorkspaceCatalog(FORTE_ROOT),
            CandidateReviewPlanner(),
            CandidateReviewAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
            effect_engine=ScenarioEffectEngine(),
            artifact_store=RunWorkspaceArtifactStore(workspace_root),
        )
        runtimes.append(first)
        await first.setup()
        started = await first.start(
            owner,
            start_request(
                idempotency_key=f"postgres-tc06-start-{uuid4().hex}",
                instruction=TC06_INSTRUCTION,
            ),
        )
        run_id = started.run.run_id
        terminal = await wait_for_effect_run(first, owner, run_id)
        assert terminal.status == "completed"
        assert len(terminal.workspace_artifacts) == 3
        receipt = terminal.effect_receipts[0]
        assert receipt.status == "passed"
        assert receipt.scenario_id == "TC-06"
        assert receipt.candidate_review_outcome is not None
        outcome = receipt.candidate_review_outcome
        assert outcome.status == "review_required"
        assert outcome.assessment_count == 110
        assert (
            outcome.met_count,
            outcome.not_met_count,
            outcome.unverifiable_count,
            outcome.human_exception_count,
        ) == (32, 6, 71, 1)

        originals: dict[str, bytes] = {}
        for artifact in terminal.workspace_artifacts:
            assert artifact.verifier_status == "passed"
            assert artifact.candidate_review_outcome == outcome
            _, originals[artifact.file_name] = await first.get_workspace_artifact(
                owner, run_id, artifact.artifact_id
            )
        await first.close()

        second = HarnessRuntime(
            BenchmarkWorkspaceCatalog(FORTE_ROOT),
            CandidateReviewPlanner(),
            CandidateReviewAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
            effect_engine=ScenarioEffectEngine(),
            artifact_store=RunWorkspaceArtifactStore(workspace_root),
        )
        runtimes.append(second)
        await second.setup()
        restored = await second.get(owner, run_id)
        restored_receipt = restored.effect_receipts[0]
        assert restored_receipt.candidate_review_outcome == outcome
        assert len(restored.workspace_artifacts) == 3
        restored_by_name = {
            item.file_name: item for item in restored.workspace_artifacts
        }
        for file_name, content in originals.items():
            artifact = restored_by_name[file_name]
            assert artifact.candidate_review_outcome == outcome
            _, restored_content = await second.get_workspace_artifact(
                owner, run_id, artifact.artifact_id
            )
            assert restored_content == content

        for report_name in (
            "外卖商户BD岗位辅助筛选报告.docx",
            "文本评测岗位辅助筛选报告.docx",
        ):
            with zipfile.ZipFile(io.BytesIO(originals[report_name])) as package:
                document = package.read("word/document.xml").decode("utf-8")
            assert document.count("<w:tbl>") >= 8
            assert "不是录用或淘汰决定" in document
        rows = list(
            csv.DictReader(
                io.StringIO(
                    originals["候选人岗位条件逐项台账.csv"].decode("utf-8-sig")
                )
            )
        )
        assert len(rows) == 110
        assert len({(row["岗位ID"], row["候选人ID"], row["条件ID"]) for row in rows}) == 110
        public_snapshot = second.public_snapshot(restored)
        public_json = public_snapshot.model_dump_json()
        assert "content_sha256" not in public_json
        candidate_projection = json.dumps(
            {
                "artifacts": [
                    {
                        "summary": artifact.summary,
                        "key_outputs": artifact.key_outputs,
                        "review_guidance": artifact.review_guidance,
                        "execution_summary": artifact.execution_summary,
                        "candidate_review_outcome": (
                            artifact.candidate_review_outcome.model_dump(mode="json")
                            if artifact.candidate_review_outcome
                            else None
                        ),
                    }
                    for artifact in public_snapshot.workspace_artifacts
                ],
                "receipts": [
                    {
                        "observation": receipt.observation,
                        "result": receipt.result,
                        "candidate_review_outcome": (
                            receipt.candidate_review_outcome.model_dump(mode="json")
                            if receipt.candidate_review_outcome
                            else None
                        ),
                    }
                    for receipt in public_snapshot.effect_receipts
                ],
            },
            ensure_ascii=False,
        )
        assert not re.search(r"(?<!\d)1[3-9]\d{9}(?!\d)", candidate_projection)
        assert not re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            candidate_projection,
        )
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


@pytest.mark.asyncio
async def test_postgres_restart_preserves_tc05_finance_outcome_and_three_artifacts(
    tmp_path: Path,
) -> None:
    owner = f"postgres-tc05-finance-{uuid4().hex}"
    run_id = ""
    runtimes: list[HarnessRuntime] = []
    workspace_root = tmp_path / "tc05-run-workspaces"
    try:
        first = HarnessRuntime(
            BenchmarkWorkspaceCatalog(FORTE_ROOT),
            FinanceReconciliationPlanner(),
            FinanceReconciliationAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
            effect_engine=ScenarioEffectEngine(),
            artifact_store=RunWorkspaceArtifactStore(workspace_root),
        )
        runtimes.append(first)
        await first.setup()
        started = await first.start(
            owner,
            start_request(
                idempotency_key=f"postgres-tc05-start-{uuid4().hex}",
                instruction=TC05_INSTRUCTION,
            ),
        )
        run_id = started.run.run_id
        terminal = await wait_for_effect_run(first, owner, run_id)
        assert terminal.status == "completed"
        assert len(terminal.workspace_artifacts) == 3
        receipt = terminal.effect_receipts[0]
        assert receipt.status == "passed"
        assert receipt.scenario_id == "TC-05"
        assert receipt.finance_review_outcome is not None
        outcome = receipt.finance_review_outcome
        assert outcome.status == "review_required"
        assert (outcome.unpaid_count, outcome.unreceived_count, outcome.candidate_count) == (
            31,
            2,
            0,
        )
        assert outcome.unpaid_total == "3984606.46"
        assert outcome.unreceived_total == "4992891.47"
        assert outcome.original_inputs_modified is False

        originals: dict[str, bytes] = {}
        for artifact in terminal.workspace_artifacts:
            assert artifact.verifier_status == "passed"
            assert artifact.finance_review_outcome == outcome
            _, originals[artifact.file_name] = await first.get_workspace_artifact(
                owner, run_id, artifact.artifact_id
            )
        await first.close()

        second = HarnessRuntime(
            BenchmarkWorkspaceCatalog(FORTE_ROOT),
            FinanceReconciliationPlanner(),
            FinanceReconciliationAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
            effect_engine=ScenarioEffectEngine(),
            artifact_store=RunWorkspaceArtifactStore(workspace_root),
        )
        runtimes.append(second)
        await second.setup()
        restored = await second.get(owner, run_id)
        restored_receipt = restored.effect_receipts[0]
        assert restored_receipt.finance_review_outcome == outcome
        assert len(restored.workspace_artifacts) == 3
        restored_by_name = {
            item.file_name: item for item in restored.workspace_artifacts
        }
        for file_name, content in originals.items():
            artifact = restored_by_name[file_name]
            assert artifact.finance_review_outcome == outcome
            _, restored_content = await second.get_workspace_artifact(
                owner, run_id, artifact.artifact_id
            )
            assert restored_content == content

        unpaid_rows = list(
            csv.DictReader(io.StringIO(originals["未付统计.csv"].decode("utf-8-sig")))
        )
        unreceived_rows = list(
            csv.DictReader(io.StringIO(originals["未收统计.csv"].decode("utf-8-sig")))
        )
        assert len(unpaid_rows) == 31
        assert len(unreceived_rows) == 2
        assert "跨期僵尸账款候选：0 条" in originals["跨期核对说明.md"].decode(
            "utf-8"
        )
        public_snapshot = second.public_snapshot(restored)
        public_json = public_snapshot.model_dump_json()
        assert "content_sha256" not in public_json
        assert public_snapshot.effect_receipts[0].finance_review_outcome == outcome
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


@pytest.mark.asyncio
async def test_postgres_restart_preserves_tc10_outbound_flow_outcome_and_docx(
    tmp_path: Path,
) -> None:
    owner = f"postgres-tc10-outbound-{uuid4().hex}"
    run_id = ""
    runtimes: list[HarnessRuntime] = []
    workspace_root = tmp_path / "tc10-run-workspaces"
    try:
        first = HarnessRuntime(
            BenchmarkWorkspaceCatalog(FORTE_ROOT),
            OutboundFlowPlanner(),
            OutboundFlowAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
            effect_engine=ScenarioEffectEngine(),
            artifact_store=RunWorkspaceArtifactStore(workspace_root),
        )
        runtimes.append(first)
        await first.setup()
        started = await first.start(
            owner,
            start_request(
                idempotency_key=f"postgres-tc10-start-{uuid4().hex}",
                instruction=TC10_INSTRUCTION,
            ),
        )
        run_id = started.run.run_id
        terminal = await wait_for_effect_run(first, owner, run_id)
        assert terminal.status == "completed"
        assert len(terminal.workspace_artifacts) == 1
        receipt = terminal.effect_receipts[0]
        assert receipt.status == "passed"
        assert receipt.scenario_id == "TC-10"
        assert receipt.outbound_flow_outcome is not None
        outcome = receipt.outbound_flow_outcome
        assert outcome.status == "approval_required"
        assert outcome.atomic_requirement_count == len(outcome.rules)
        assert outcome.covered_count == outcome.atomic_requirement_count
        assert outcome.unsupported_count == outcome.conflict_count == 0
        assert outcome.reachable_terminal_count == outcome.terminal_count
        assert all(outcome.graph_integrity.model_dump().values())

        artifact = terminal.workspace_artifacts[0]
        assert artifact.verifier_status == "passed"
        assert artifact.outbound_flow_outcome == outcome
        _, original_docx = await first.get_workspace_artifact(
            owner, run_id, artifact.artifact_id
        )
        with zipfile.ZipFile(io.BytesIO(original_docx)) as package:
            document = package.read("word/document.xml").decode("utf-8")
        assert document.count("<w:tbl>") >= 6
        assert "来源规则账本" in document
        assert "最终合规审批未发生" in document
        await first.close()

        second = HarnessRuntime(
            BenchmarkWorkspaceCatalog(FORTE_ROOT),
            OutboundFlowPlanner(),
            OutboundFlowAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
            effect_engine=ScenarioEffectEngine(),
            artifact_store=RunWorkspaceArtifactStore(workspace_root),
        )
        runtimes.append(second)
        await second.setup()
        restored = await second.get(owner, run_id)
        assert restored.effect_receipts[0].outbound_flow_outcome == outcome
        assert len(restored.workspace_artifacts) == 1
        restored_artifact = restored.workspace_artifacts[0]
        assert restored_artifact.outbound_flow_outcome == outcome
        _, restored_docx = await second.get_workspace_artifact(
            owner, run_id, restored_artifact.artifact_id
        )
        assert restored_docx == original_docx

        public_snapshot = second.public_snapshot(restored)
        public_json = public_snapshot.model_dump_json()
        assert "content_sha256" not in public_json
        assert public_snapshot.effect_receipts[0].outbound_flow_outcome == outcome
        assert public_snapshot.effect_receipts[0].external_action == "none"
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


@pytest.mark.asyncio
async def test_postgres_restart_preserves_tc07_legal_review_and_artifacts(
    tmp_path: Path,
) -> None:
    owner = f"postgres-tc07-legal-{uuid4().hex}"
    run_id = ""
    runtimes: list[HarnessRuntime] = []
    workspace_root = tmp_path / "tc07-run-workspaces"
    try:
        first = HarnessRuntime(
            BenchmarkWorkspaceCatalog(FORTE_ROOT),
            LegalDelegationPlanner(),
            LegalDelegationAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
            effect_engine=ScenarioEffectEngine(),
            artifact_store=RunWorkspaceArtifactStore(workspace_root),
        )
        runtimes.append(first)
        await first.setup()
        started = await first.start(
            owner,
            start_request(
                idempotency_key=f"postgres-tc07-start-{uuid4().hex}",
                instruction=TC07_INSTRUCTION,
            ),
        )
        run_id = started.run.run_id
        terminal = await wait_for_effect_run(first, owner, run_id)
        assert terminal.status == "completed"
        assert len(terminal.workspace_artifacts) == 2
        receipt = terminal.effect_receipts[0]
        assert receipt.status == "passed"
        assert receipt.scenario_id == "TC-07"
        assert receipt.business_gate_outcome is not None
        assert receipt.business_gate_outcome.outcome_kind == "legal_delegation_review"
        assert receipt.business_gate_outcome.failed_gate_count == 3
        assert receipt.legal_review_outcome is not None
        assert receipt.legal_review_outcome.status == "review_required"
        assert receipt.legal_review_outcome.assessment_count == 126
        assert receipt.legal_review_outcome.high_risk_document_count == 6
        assert receipt.legal_review_outcome.critical_unverifiable_count == 11

        originals: dict[str, bytes] = {}
        for artifact in terminal.workspace_artifacts:
            assert artifact.verifier_status == "passed"
            assert artifact.legal_review_outcome == receipt.legal_review_outcome
            _, originals[artifact.file_name] = await first.get_workspace_artifact(
                owner, run_id, artifact.artifact_id
            )
        await first.close()

        second = HarnessRuntime(
            BenchmarkWorkspaceCatalog(FORTE_ROOT),
            LegalDelegationPlanner(),
            LegalDelegationAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
            effect_engine=ScenarioEffectEngine(),
            artifact_store=RunWorkspaceArtifactStore(workspace_root),
        )
        runtimes.append(second)
        await second.setup()
        restored = await second.get(owner, run_id)
        restored_receipt = restored.effect_receipts[0]
        assert restored_receipt.business_gate_outcome == receipt.business_gate_outcome
        assert restored_receipt.legal_review_outcome == receipt.legal_review_outcome
        restored_by_name = {
            item.file_name: item for item in restored.workspace_artifacts
        }
        for file_name, content in originals.items():
            artifact = restored_by_name[file_name]
            assert artifact.legal_review_outcome == receipt.legal_review_outcome
            _, restored_content = await second.get_workspace_artifact(
                owner, run_id, artifact.artifact_id
            )
            assert restored_content == content

        with zipfile.ZipFile(
            io.BytesIO(originals["授权委托书风控报告.docx"])
        ) as package:
            document = package.read("word/document.xml").decode("utf-8")
        assert document.count("<w:tbl>") >= 8
        assert "不得据此签署，必须法务复核" in document
        assert "R05" in document
        rows = list(
            csv.DictReader(
                io.StringIO(
                    originals["授权委托书逐项核查台账.csv"].decode("utf-8-sig")
                )
            )
        )
        assert len(rows) == 126
        assert sum(
            row["规则ID"] == "R05" and row["状态"] == "triggered"
            for row in rows
        ) == 6
        assert sum(
            row["规则ID"] == "M03" and row["状态"] == "unverifiable"
            for row in rows
        ) == 5
        assert "content_sha256" not in second.public_snapshot(
            restored
        ).model_dump_json()
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


class TripleAmbiguousCatalog(AmbiguousCatalog):
    """Keep three identical excerpts so the test cannot pass by picking one at random."""

    def agent_file_inputs(self, file_refs: list[str]) -> list[dict[str, object]]:
        inputs = super().agent_file_inputs(file_refs)
        for item in inputs:
            if item["file_ref"] == "forte-2222222222222222":
                item["text"] = "复核说明\n其他内容\n复核说明\n附加说明\n复核说明"
        return inputs


class PostgresRecoveryAnalyst(MixedEvidenceAnalyst):
    """Return the ambiguous quote until the resumed branch gets a clean quote."""

    total_calls = 0

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        type(self).total_calls += 1
        result = await super().analyze(
            instruction=instruction,
            plan=plan,
            files=files,
            validation_feedback=validation_feedback,
        )
        if type(self).total_calls < 3:
            return result
        finding = result.findings[1].model_copy(
            update={
                "evidence_quotes": [
                    result.findings[1].evidence_quotes[0].model_copy(
                        update={"quote": "附加说明"}
                    )
                ]
            }
        )
        return result.model_copy(update={"findings": [finding]})


@pytest.mark.asyncio
async def test_postgres_restarts_with_pending_decision_and_resumes_only_target_branch() -> None:
    """A real PostgreSQL gate for DR-0032's pending decision and local recovery path."""

    owner = f"postgres-decision-{uuid4().hex}"
    run_id = ""
    runtimes: list[HarnessRuntime] = []
    PostgresRecoveryAnalyst.total_calls = 0
    try:
        first = HarnessRuntime(
            TripleAmbiguousCatalog(),
            FakePlanner(),
            PostgresRecoveryAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(first)
        await first.setup()
        started = await first.start(
            owner,
            start_request(idempotency_key=f"decision-start-{uuid4().hex}"),
        )
        run_id = started.run.run_id
        waiting = await wait_status(first, owner, run_id, "waiting_input")
        resolution = waiting.rounds[0].next_step.evidence_resolutions[0]
        assert resolution.status == "ambiguous"
        assert len(resolution.candidates) == 3
        assert waiting.artifact_versions
        assert waiting.artifact_versions[0].version == 1
        assert waiting.branches[0].status == "completed"
        requests = getattr(waiting, "decision_requests", ())
        assert requests, "pending DecisionRequest must be in the authoritative Snapshot"
        assert requests[0].state == "open"
        await first.close()
        # The resumed provider call represents the post-decision clean locator;
        # seed the deterministic fixture past its two ambiguous attempts.
        PostgresRecoveryAnalyst.total_calls = 2

        second = HarnessRuntime(
            TripleAmbiguousCatalog(),
            FakePlanner(),
            PostgresRecoveryAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(second)
        await second.setup()
        restored = await second.get(owner, run_id)
        assert restored.status == "waiting_input"
        restored_resolution = restored.rounds[0].next_step.evidence_resolutions[0]
        assert restored_resolution.status == "ambiguous"
        assert {item.candidate_id for item in restored_resolution.candidates} == {
            item.candidate_id for item in resolution.candidates
        }
        restored_requests = getattr(restored, "decision_requests", ())
        assert restored_requests and restored_requests[0].state == "open"

        public_restored = second.public_snapshot(restored)
        public_request = public_restored.decision_requests[0]

        selected = restored_resolution.candidates[0].candidate_id
        decision = await second.control(
            owner,
            run_id,
            AgentControlLoopControlRequest(
                command="decision",
                decision_action="accept",
                decision_request_id=public_request.decision_request_id,
                finding_id=restored_resolution.finding_id,
                resolution_id=restored_resolution.resolution_id,
                branch_id=restored_resolution.branch_id,
                selected_candidate_id=selected,
                source_revision=public_request.source_revision,
                expected_version=restored.version,
                idempotency_key=f"decision-accept-{uuid4().hex}",
            ),
        )
        assert decision.run.decision_records[-1].action == "accept"
        assert decision.run.decision_records[-1].selected_candidate_id == selected
        target_branch_id = restored_resolution.branch_id
        assert target_branch_id
        assert all(
            branch.status == "completed"
            for branch in decision.run.branches
            if branch.branch_id != target_branch_id
        )

        terminal = await wait_terminal(second, owner, run_id)
        assert terminal.status == "completed"
        assert terminal.last_commit and terminal.last_commit.artifact_version == 2
        assert [item.version for item in terminal.artifact_versions] == [1, 2]
        assert all(item.status == "completed" for item in terminal.branches)
        assert any(
            event.event_name == "branch_resumed_from_checkpoint"
            and event.details.get("branch_id") == target_branch_id
            for event in terminal.events
        )

        await second.close()
        third = HarnessRuntime(
            TripleAmbiguousCatalog(),
            FakePlanner(),
            PostgresRecoveryAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(third)
        await third.setup()
        final = await third.get(owner, run_id)
        assert final.status == "completed"
        assert [item.version for item in final.artifact_versions] == [1, 2]
        assert len(final.decision_records) == 1
        final_resolution = final.rounds[0].next_step.evidence_resolutions[0]
        assert final_resolution.resolution_id == resolution.resolution_id
        assert final_resolution.status == "exact"
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
