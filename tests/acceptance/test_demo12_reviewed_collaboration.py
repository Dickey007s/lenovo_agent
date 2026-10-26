"""Bounded repairs, handoff disagreements and explicit output agreements."""

from collections import Counter

import httpx
import pytest
from pydantic import ValidationError
from packages.contracts.harness_models import AgentControlLoopControlRequest

from services.api.app.api.harness_routes import get_harness_runtime
from services.api.app.application.harness_runtime import (
    HarnessModelError, HarnessPlanCandidate, HarnessPlanCandidateUnit, HarnessRunStart, HarnessRuntime,
)
from services.api.app.main import create_app
from tests.acceptance.test_demo12_output_and_dependencies import ContextAnalyst, wave
from tests.acceptance.test_demo12_worker_reliability import admitted
from tests.acceptance.test_demo1_demo2_fixed_scenarios import FiveUnitFailurePlanner, _ten_file_cross_function_catalog, _wait_for
from tests.unit.test_harness_runtime import FakeAnalyst


def test_output_choice_conflict_requires_clarification_before_a_run_exists():
    with pytest.raises(ValidationError, match="输出选择与任务中的禁文件要求冲突"):
        HarnessRunStart(instruction="不要生成文件，仅分析上线风险。", idempotency_key="output-conflict",
                        output_preference="workspace_files_allowed")
    legacy = HarnessRunStart(instruction="核对上线风险", idempotency_key="legacy-output")
    assert "output_preference" not in legacy.model_dump(mode="json")


@pytest.mark.asyncio
async def test_explicit_analysis_only_does_not_need_a_prohibition_prompt():
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), FiveUnitFailurePlanner(), ContextAnalyst())
    try:
        started = await runtime.start("reliability", HarnessRunStart(
            instruction="核对上线风险", idempotency_key="explicit-output-choice", output_preference="analysis_only"))
        assert started.run.contract.output_policy == "analysis_only"
        assert started.run.contract.collaboration_protocol == "reviewed_handoffs_v1"
    finally:
        await runtime.close()


class RepairAnalyst(ContextAnalyst):
    def __init__(self, failure="invalid_schema", always=False):
        super().__init__()
        self.counts = Counter()
        self.failure = failure
        self.always = always
        self.target = None
        self.feedback = []

    async def analyze(self, **kwargs):
        unit = kwargs["plan"].units[0].unit_id
        self.target = self.target or unit
        self.counts[unit] += 1
        self.feedback.append(kwargs.get("validation_feedback"))
        if unit == self.target and (self.always or self.counts[unit] == 1):
            raise HarnessModelError("controlled bad output", called=True, failure_kind=self.failure)
        return await super().analyze(**kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["invalid_json", "invalid_schema", "output_truncated"])
async def test_repairs_only_one_worker_once_and_accounts_for_extra_call(failure):
    analyst = RepairAnalyst(failure)
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), FiveUnitFailurePlanner(), analyst)
    try:
        first = await wave(runtime, await admitted(runtime), "one-local-repair")
        assert sorted(analyst.counts.values()) == [1, 1, 2]
        assert first.budget.model_calls_used == 5  # planner + 3 roots + 1 repair
        assert all(item.gate_status == "adopted" for item in first.contributions)
        assert sum(item.repair_count for item in first.worker_runs) == 1
        assert all(item.work_role == "source_analysis" for item in first.worker_runs)
        repairs = [item for item in first.events if item.event_name == "worker_repair_requested"]
        assert len(repairs) == 1 and repairs[0].details["failure_kind"] == failure
        assert any("仅修复当前工作包" in (item or "") for item in analyst.feedback)
    finally:
        await runtime.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure,expected", [("invalid_schema", 2), ("provider_timeout", 1), ("provider_response", 1)])
async def test_repeated_or_transport_failure_preserves_siblings(failure, expected):
    analyst = RepairAnalyst(failure, always=True)
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), FiveUnitFailurePlanner(), analyst)
    try:
        first = await wave(runtime, await admitted(runtime), "bounded-failure")
        assert analyst.counts[analyst.target] == expected
        assert sum(item.gate_status == "adopted" for item in first.contributions) == 2
        assert first.artifact_versions
        failed = next(item for item in first.worker_runs if not item.output_used)
        assert failed.model_called
        assert failed.repair_count == expected - 1
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_stop_then_http_continue_repairs_one_branch_without_seeding_history():
    class ScopedPlanner(FiveUnitFailurePlanner):
        async def plan(self, *, scenario, files):
            if len(files) == 10:
                return await super().plan(scenario=scenario, files=files)
            self.calls += 1
            return HarnessPlanCandidate(summary="只核对批准的失败分支", selection_reason="按续办来源核对",
                units=[HarnessPlanCandidateUnit(unit_id="root-1", title="产品上线 Gate",
                    objective="恢复目标分支", tool="file.read", input_file_refs=[item["file_ref"] for item in files])])

    class RecoveryAnalyst(RepairAnalyst):
        async def analyze(self, **kwargs):
            result = await super().analyze(**kwargs)
            if not self.always:
                findings = []
                for source in kwargs["files"]:
                    checked = await FakeAnalyst.analyze(self, instruction=kwargs["instruction"],
                                                       plan=kwargs["plan"], files=[source])
                    findings.extend(checked.findings)
                return result.model_copy(update={"findings": findings})
            return result

    planner = ScopedPlanner()
    analyst = RecoveryAnalyst(always=True)
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), planner, analyst)
    app = create_app()
    app.dependency_overrides[get_harness_runtime] = lambda: runtime
    try:
        first = await wave(runtime, await admitted(runtime), "recovery-before-stop")
        assert sorted(analyst.counts.values()) == [1, 1, 2]
        assert sum(item.gate_status == "adopted" for item in first.contributions) == 2
        assert len(first.artifact_versions) == 1 and first.last_commit is not None
        branch = next(item for item in first.branches if item.unit_id == analyst.target)
        refs = set(branch.missing_file_refs or branch.input_file_refs)
        before_counts = analyst.counts.copy()
        await runtime.control("reliability", first.run_id, AgentControlLoopControlRequest(
            command="stop", expected_version=first.version, idempotency_key="recovery-stop"))
        parent = await _wait_for(runtime, "reliability", first.run_id, lambda item: item.status == "stopped")
        parent_dump = parent.model_dump(mode="json")
        analyst.always = False
        payload = {"branch_id": branch.branch_id, "expected_version": parent.version,
                   "expected_task_version": parent.task_version, "idempotency_key": "recovery-child"}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"/v1/harness/runs/{parent.run_id}/continue",
                                         headers={"X-User-Id": "reliability"}, json=payload)
            assert response.status_code == 202, response.text
            child_id = response.json()["run"]["run_id"]
            child = await _wait_for(runtime, "reliability", child_id,
                                    lambda item: item.status in {"completed", "failed", "stopped", "waiting_input"})
            assert child.status == "completed", child.model_dump(mode="json")
            assert child.task_id == parent.task_id and child.parent_run_id == parent.run_id
            assert child.run_sequence == parent.run_sequence + 1
            assert set(child.recheck_file_refs) == refs
            assert child.base_artifact_version == first.artifact_versions[0].version
            assert child.base_task_commit == first.last_commit.commit_id
            assert {item["file_ref"] for item in analyst.inputs[-1]["files"]} == refs
            assert analyst.counts[analyst.target] == before_counts[analyst.target] + 1
            assert all(analyst.counts[unit] == count for unit, count in before_counts.items() if unit != analyst.target)
            assert (await runtime.get("reliability", parent.run_id)).model_dump(mode="json") == parent_dump
            assert len(child.artifact_versions) == 1 and child.last_commit is not None
            assert planner.calls == 2
            calls_after = analyst.counts.copy()
            replay = await client.post(f"/v1/harness/runs/{parent.run_id}/continue",
                                       headers={"X-User-Id": "reliability"}, json=payload)
            assert replay.status_code == 202 and replay.json()["run"]["run_id"] == child_id
            assert analyst.counts == calls_after
    finally:
        app.dependency_overrides.clear()
        await runtime.close()


@pytest.mark.asyncio
async def test_no_repair_beyond_model_budget():
    analyst = RepairAnalyst()
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), FiveUnitFailurePlanner(), analyst)
    try:
        initial = await admitted(runtime)
        stored = runtime._runs[("reliability", initial.run_id)]
        stored.snapshot.budget = stored.snapshot.budget.model_copy(update={"max_model_calls": 4})
        first = await wave(runtime, await runtime.get("reliability", initial.run_id), "budgeted-repair")
        assert sum(analyst.counts.values()) == 3
        assert first.budget.model_calls_used == 4
        assert sum(item.gate_status == "adopted" for item in first.contributions) == 2
        assert not any(item.repair_count for item in first.worker_runs)
    finally:
        await runtime.close()


class DisagreementAnalyst(ContextAnalyst):
    def __init__(self, verdict):
        super().__init__()
        self.verdict = verdict

    async def analyze(self, **kwargs):
        result = await super().analyze(**kwargs)
        if result.dependency_assessments:
            result.dependency_assessments[0] = result.dependency_assessments[0].model_copy(update={
                "verdict": self.verdict, "explanation": "前序结论与当前来源口径不同，保留两者供人工复核。"})
        return result


@pytest.mark.asyncio
async def test_real_ambiguous_quote_never_triggers_automatic_repair(monkeypatch):
    catalog = _ten_file_cross_function_catalog()
    original = catalog.agent_file_inputs
    target = catalog.files[0]["file_ref"]

    def duplicated(refs):
        return [{**item, "text": "无关法务说明\n无关法务说明"} if item["file_ref"] == target else item
                for item in original(refs)]

    monkeypatch.setattr(catalog, "agent_file_inputs", duplicated)
    analyst = ContextAnalyst()
    runtime = HarnessRuntime(catalog, FiveUnitFailurePlanner(), analyst)
    try:
        first = await wave(runtime, await admitted(runtime), "ambiguous-no-repair")
        assert len(analyst.inputs) == 3
        assert sum(item.gate_status == "adopted" for item in first.contributions) == 2
        assert any(item.outcome == "ambiguous" for item in first.worker_runs)
        assert not any(item.repair_count for item in first.worker_runs)
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_stop_at_repair_boundary_prevents_new_call():
    class StopAnalyst(RepairAnalyst):
        async def analyze(self, **kwargs):
            try:
                return await super().analyze(**kwargs)
            except HarnessModelError:
                current = await runtime.get("reliability", run_id)
                await runtime.control("reliability", run_id, AgentControlLoopControlRequest(
                    command="stop", expected_version=current.version, idempotency_key="stop-before-repair"))
                raise

    analyst = StopAnalyst()
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), FiveUnitFailurePlanner(), analyst)
    try:
        waiting = await admitted(runtime)
        run_id = waiting.run_id
        final = await wave(runtime, waiting, "stopped-repair-wave")
        assert analyst.counts[analyst.target] == 1
        assert not any(item.repair_count for item in final.worker_runs)
        assert final.budget.model_calls_used == 4
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_missing_handoff_review_cannot_pass_after_one_structure_repair():
    class MissingReviewAnalyst(ContextAnalyst):
        async def analyze(self, **kwargs):
            result = await super().analyze(**kwargs)
            return result.model_copy(update={"dependency_assessments": []})

    analyst = MissingReviewAnalyst()
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), FiveUnitFailurePlanner(), analyst)
    try:
        first = await wave(runtime, await admitted(runtime), "missing-review-roots")
        second = await wave(runtime, first, "missing-review-downstream")
        assert len(analyst.inputs) == 7
        assert all(item.repair_count == 1 and not item.output_used for item in second.worker_runs[3:])
        assert second.artifact_versions == first.artifact_versions
    finally:
        await runtime.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("verdict", ["conflict", "insufficient"])
async def test_disagreement_is_not_auto_repaired_or_merged_and_parents_survive(verdict):
    analyst = DisagreementAnalyst(verdict)
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), FiveUnitFailurePlanner(), analyst)
    try:
        first = await wave(runtime, await admitted(runtime), "disagreement-roots")
        saved = [item.model_dump(mode="json") for item in first.artifact_versions]
        second = await wave(runtime, first, "disagreement-review")
        assert len(analyst.inputs) == 5
        assert second.status == "waiting_input"
        assert [item.model_dump(mode="json") for item in second.artifact_versions] == saved
        assert all(item.gate_status == "adopted" for item in second.contributions[:3])
        assert all(item.gate_status == "rejected" for item in second.contributions[3:])
        for worker in second.worker_runs[3:]:
            assert worker.work_role in {"dependency_review", "synthesis_review"}
            assert worker.dependency_assessments[0].verdict == verdict
            assert worker.dependency_assessments[0].evidence_anchors
            assert not worker.output_used and not worker.repair_count
        replay = await wave(runtime, first, "disagreement-review")
        assert replay.model_dump(mode="json") == second.model_dump(mode="json")
    finally:
        await runtime.close()
