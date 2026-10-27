"""Output restrictions and real Analyst dependency payloads without provider calls."""

import pytest

from packages.contracts.harness_models import AgentControlLoopControlRequest
from services.api.app.application.harness_runtime import HarnessConflictError, HarnessRunStart, HarnessRuntime
from services.api.app.application.output_policy import compile_output_policy
from services.api.app.application.collaboration_review import DependencyAssessmentDraft
from services.api.app.application.readonly_workers import ReadonlyWorkerRequest, ReadonlyWorkerContribution
from services.api.app.application.run_workspace_artifact_store import RunWorkspaceArtifactStore
from services.api.app.application.scenario_effects import ScenarioEffectEngine
from services.api.app.application.workunit_ledger import ContributionGateStatus
from tests.acceptance.test_demo12_worker_reliability import admitted
from tests.acceptance.test_demo1_demo2_fixed_scenarios import FiveUnitFailurePlanner, _ten_file_cross_function_catalog, _wait_for
from tests.unit.test_harness_runtime import FakeAnalyst
from tests.unit.test_scenario_effect_runtime import (
    BenchmarkWorkspaceCatalog, FORTE_ROOT, ONBOARDING_INSTRUCTION,
    OnboardingPlanner, OnboardingAnalyst, _wait_for_settled,
)


def test_empty_handoff_preserves_legacy_worker_payloads():
    request = {"worker_run_id": "worker-original", "branch_id": "branch-original",
               "goal": "original root", "source_file_refs": ["source-a"], "expected_version": 3}
    assert ReadonlyWorkerRequest.model_validate(request).model_dump(mode="json") == request
    receipt = ReadonlyWorkerContribution(worker_run_id="worker-original", branch_id="branch-original",
                                         outcome="failed", summary="original receipt", source_file_refs=("source-a",))
    old_payload = receipt.model_dump(mode="json", exclude={"input_contribution_ids"})
    assert ReadonlyWorkerContribution.model_validate(old_payload).model_dump(mode="json") == old_payload


@pytest.mark.parametrize("instruction", [
    "核对上线配置与测试，只在页面展示，不要生成报告。",
    "请分析，不需要导出 CSV 或 DOCX 文件。", "无需保存文件，只核对。",
    "仅在界面显示结论。", "Do not generate any reports.", "Analyze without exporting files.",
])
def test_no_file_policy_is_compiled_from_explicit_prohibitions(instruction):
    assert compile_output_policy(instruction) == "analysis_only"


@pytest.mark.parametrize("instruction", [
    ONBOARDING_INSTRUCTION, "不要修改原文件，生成一份新的报告。",
    "生成报告，但不要发送邮件，也不要上线。", "不得修改原始资料，导出 CSV。",
    "不要生成代码或执行代码，不改原文件；请生成报告。",
    "Do not create accounts, export a report instead.",
])
def test_source_and_external_restrictions_do_not_forbid_requested_output(instruction):
    assert compile_output_policy(instruction) == "workspace_files_allowed"


@pytest.mark.asyncio
@pytest.mark.parametrize("restricted", [True, False])
async def test_fixed_adapter_respects_output_policy_before_freeze_or_write(tmp_path, restricted):
    class TrackingEngine(ScenarioEffectEngine):
        freeze_calls = 0

        def freeze(self, *args, **kwargs):
            self.freeze_calls += 1
            return super().freeze(*args, **kwargs)

    class WritingPlanner(OnboardingPlanner):
        async def plan(self, **kwargs):
            candidate = await super().plan(**kwargs)
            candidate.units[0].tool = "artifact.write"
            return candidate

    engine = TrackingEngine()
    runtime = HarnessRuntime(BenchmarkWorkspaceCatalog(FORTE_ROOT), WritingPlanner(), OnboardingAnalyst(),
                             effect_engine=engine, artifact_store=RunWorkspaceArtifactStore(tmp_path / "artifacts"))
    try:
        started = await runtime.start("output-owner", HarnessRunStart(
            instruction=ONBOARDING_INSTRUCTION + ("但这次只在页面展示，不要生成文件。" if restricted else "不要修改原文件。"),
            idempotency_key="output-intent-test",
        ))
        result = await _wait_for_settled(runtime, "output-owner", started.run.run_id)
        assert result.status != "failed", result.validation_errors
        assert bool(result.workspace_artifacts) is not restricted
        assert bool(result.effect_receipts) is not restricted
        assert engine.freeze_calls == (0 if restricted else 1)
        if restricted:
            assert result.contract.output_policy == "analysis_only"
            assert result.plan.units[0].side_effect == "none"
            assert result.plan.units[0].artifact_name is None
            assert any(event.event_name == "office_output_suppressed" for event in result.events)
            assert not list(tmp_path.rglob("*.csv"))
        else:
            assert result.workspace_artifacts[0].verifier_status == "passed"
    finally:
        await runtime.close()


class ContextAnalyst(FakeAnalyst):
    def __init__(self):
        super().__init__()
        self.inputs = []

    async def analyze(self, *, instruction, plan, files, validation_feedback=None,
                      verified_effect_context=None, dependency_context=None):
        self.inputs.append({"unit": plan.units[0].unit_id, "context": dependency_context or [], "files": files})
        result = await super().analyze(instruction=instruction, plan=plan, files=files)
        findings = list(result.findings)
        assessments = []
        for context in dependency_context or []:
            source = next(item for item in files if item["file_ref"] in context["source_file_refs"])
            evidence = await super().analyze(instruction=instruction, plan=plan, files=[source])
            assessments.append(DependencyAssessmentDraft(contribution_id=context["contribution_id"],
                verdict="supported", explanation="固定测试按批准来源核对。", finding_indices=[len(findings)]))
            findings.extend(evidence.findings)
        return result.model_copy(update={"summary": f"已核对 {plan.units[0].title} 的批准来源，仍需业务复核。",
                                         "findings": findings, "dependency_assessments": assessments})


async def wave(runtime, current, key, branch_ids=None):
    return await runtime.execute_admitted_workers_from_branches(
        "reliability", current.run_id, branch_ids=branch_ids or [], expected_version=current.version,
        idempotency_key=key, user_confirmed=True,
    )


@pytest.mark.asyncio
async def test_two_waves_supply_only_direct_adopted_parents_and_keep_v1_immutable():
    analyst = ContextAnalyst()
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), FiveUnitFailurePlanner(), analyst)
    try:
        waiting = await admitted(runtime)
        first = await wave(runtime, waiting, "context-roots")
        assert len(first.contributions) == 3
        assert all(item.gate_status == "adopted" for item in first.contributions)
        v1 = first.artifact_versions[0].model_dump(mode="json")
        roots = {item.branch_id: item for item in first.contributions}
        second = await wave(runtime, first, "context-downstream")
        assert second.status == "completed"
        assert len(second.contributions) == 5
        assert second.artifact_versions[0].model_dump(mode="json") == v1
        assert [item.version for item in second.artifact_versions] == [1, 2]
        assert not any(item["context"] for item in analyst.inputs[:3])
        for record in analyst.inputs[3:]:
            branch = next(item for item in second.branches if item.unit_id == record["unit"])
            assert {item["branch_id"] for item in record["context"]} == set(branch.depends_on)
            assert {item["contribution_id"] for item in record["context"]} == {roots[bid].contribution_id for bid in branch.depends_on}
            assert all(item["summary"] == roots[item["branch_id"]].summary for item in record["context"])
            assert all(set(item["source_file_refs"]).issubset(branch.input_file_refs) for item in record["context"])
            receipt = next(item for item in second.contributions if item.branch_id == branch.branch_id)
            assert set(receipt.input_contribution_ids) == {item["contribution_id"] for item in record["context"]}
        replay = await wave(runtime, first, "context-downstream")
        assert replay.model_dump(mode="json") == second.model_dump(mode="json")
        assert len(analyst.inputs) == 5
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_legacy_dependent_wave_replay_keeps_original_digest_and_does_not_call(monkeypatch):
    analyst = ContextAnalyst()
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), FiveUnitFailurePlanner(), analyst)
    try:
        first = await wave(runtime, await admitted(runtime), "legacy-roots")
        build_context = runtime._worker_dependency_context
        monkeypatch.setattr(runtime, "_worker_dependency_context", lambda *args, **kwargs: ())
        legacy = await wave(runtime, first, "legacy-downstream")
        assert legacy.status == "completed"
        assert not any(item.input_contribution_ids for item in legacy.contributions)
        monkeypatch.setattr(runtime, "_worker_dependency_context", build_context)
        runtime._worker_idempotent.clear()
        replay = await wave(runtime, first, "legacy-downstream")
        assert replay.model_dump(mode="json") == legacy.model_dump(mode="json")
        assert len(analyst.inputs) == 5
        with pytest.raises(HarnessConflictError, match="不同 Worker 命令"):
            await wave(runtime, first.model_copy(update={"version": first.version + 1}), "legacy-downstream")
        assert len(analyst.inputs) == 5
    finally:
        await runtime.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["unadopted", "uncalled", "wrong_owner", "missing_version", "outside_scope", "catalog_changed", "missing_parent"])
async def test_invalid_dependency_never_spends_budget_or_changes_the_run(fault):
    analyst = ContextAnalyst()
    catalog = _ten_file_cross_function_catalog()
    runtime = HarnessRuntime(catalog, FiveUnitFailurePlanner(), analyst)
    try:
        first = await wave(runtime, await admitted(runtime), "dependency-negative-roots")
        branch = next(item for item in first.branches if item.unit_id == "dependent-blocked")
        stored = runtime._runs[("reliability", first.run_id)]
        parent = next(item for item in first.contributions if item.branch_id == branch.depends_on[0])
        updates = {"unadopted": {"gate_status": ContributionGateStatus.WAITING},
                   "uncalled": {"model_receipt": parent.model_receipt.model_copy(update={"called": False})},
                   "wrong_owner": {"owner_id": "someone-else"},
                   "missing_version": {"artifact_version": 24}}
        if fault in updates:
            stored.snapshot.contributions = [item.model_copy(update=updates[fault]) if item.contribution_id == parent.contribution_id else item
                                            for item in first.contributions]
        elif fault == "outside_scope":
            stored.snapshot.branches = [item.model_copy(update={"input_file_refs": item.input_file_refs[:1]})
                                        if item.branch_id == branch.branch_id else item for item in first.branches]
        elif fault == "missing_parent":
            stored.snapshot.branches = [item for item in first.branches if item.branch_id != branch.depends_on[0]]
        else:
            catalog.revision = "changed-catalog"
        before = (await runtime.get("reliability", first.run_id)).model_dump(mode="json")
        with pytest.raises(HarnessConflictError):
            await wave(runtime, first, "dependency-negative-downstream", [branch.branch_id])
        assert (await runtime.get("reliability", first.run_id)).model_dump(mode="json") == before
        assert len(analyst.inputs) == 3
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_continuation_cannot_drop_parent_no_file_policy():
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), FiveUnitFailurePlanner(), ContextAnalyst())
    try:
        started = await runtime.start("reliability", HarnessRunStart(
            instruction="只在页面展示五项核查，不要生成文件。", idempotency_key="readonly-parent",
        ))
        waiting = await _wait_for(runtime, "reliability", started.run.run_id, lambda item: item.status == "waiting_input")
        await runtime.control("reliability", waiting.run_id, AgentControlLoopControlRequest(
            command="stop", expected_version=waiting.version, idempotency_key="readonly-stop",
        ))
        stopped = await _wait_for(runtime, "reliability", waiting.run_id, lambda item: item.status == "stopped")
        child = await runtime.continue_unfinished_task(
            "reliability", stopped.run_id, branch_id=stopped.branches[0].branch_id,
            expected_version=stopped.version, expected_task_version=stopped.task_version,
            idempotency_key="readonly-child", instruction="现在生成报告。",
        )
        assert child.run.contract.output_policy == "analysis_only"
    finally:
        await runtime.close()
