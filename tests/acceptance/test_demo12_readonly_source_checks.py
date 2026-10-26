"""Replay actual adopted numeric errors through the public Worker execution path."""

import json
from pathlib import Path

import pytest

from services.api.app.application.benchmark_workspace_catalog import BenchmarkWorkspaceCatalog
from services.api.app.application.benchmark_scenario_catalog import BenchmarkScenarioError
from services.api.app.application.harness_runtime import (
    HarnessFinding, HarnessPlanCandidate, HarnessRunStart, HarnessRuntime, HarnessTaskResult,
)
from services.api.app.application.collaboration_review import DependencyAssessmentDraft
from services.api.app.application.model_input_coverage import model_input_coverage
from tests.acceptance.test_demo1_demo2_fixed_scenarios import _wait_for


ROOT = Path(__file__).resolve().parents[2]
REPLAY = ROOT / "docs/reports/demo12-outcomes-20260922/live/swarm_readonly-154403/snapshot.json"


def saved_run():
    return json.loads(REPLAY.read_text(encoding="utf-8"))


async def admitted(runtime):
    start = await runtime.start("reliability", HarnessRunStart(
        instruction="只读核对产品、搜索、交互和下游结果，不生成文件。",
        output_preference="analysis_only", idempotency_key="source-count-replay-start",
        loop={"max_rounds": 2, "max_files_per_round": 10, "max_model_calls": 8, "deadline_seconds": 120},
    ))
    run = await _wait_for(runtime, "reliability", start.run.run_id,
                          lambda item: item.status in {"waiting_input", "completed", "failed"})
    assert run.status == "waiting_input", run.validation_errors
    assert run.contract.output_policy == "analysis_only"
    return run


class ReplayPlanner:
    model = "offline-saved-plan"

    async def plan(self, **kwargs):
        plan = saved_run()["plan"]
        return HarnessPlanCandidate.model_validate({
            "summary": plan["summary"], "selection_reason": plan["selection_reason"],
            "units": [{key: value for key, value in unit.items() if key != "side_effect"}
                      for unit in plan["units"]],
        })


class ReplayAnalyst:
    model = "offline-saved-finding"

    def __init__(self, index):
        self.index = index
        self.calls = 0

    async def analyze(self, **kwargs):
        self.calls += 1
        original = saved_run()["artifact_versions"][0]["findings"][self.index]
        finding = {key: original[key] for key in (
            "plan_unit_id", "title", "detail", "fact_summary", "impact", "file_refs",
        )}
        finding["evidence_quotes"] = [{
            "file_ref": item["file_ref"], "role": item["role"], "label": item["label"],
            "quote": item["query_excerpt"],
        } for item in original["evidence_resolutions"]]
        return HarnessTaskResult(summary="产品来源核对结果，仍需业务复核。",
                                 findings=[HarnessFinding.model_validate(finding)])


@pytest.mark.asyncio
@pytest.mark.parametrize("index", [0, 1], ids=["p0-six-instead-of-seven", "header-counted-as-record"])
async def test_saved_wrong_numeric_contribution_cannot_be_adopted(index):
    analyst = ReplayAnalyst(index)
    runtime = HarnessRuntime(BenchmarkWorkspaceCatalog(ROOT / "demo-enterprise-data/forte"),
                             ReplayPlanner(), analyst)
    try:
        waiting = await admitted(runtime)
        branch = next(item for item in waiting.branches if item.unit_id == "u_product_mgmt_review")
        result = await runtime.execute_admitted_workers_from_branches(
            "reliability", waiting.run_id, branch_ids=[branch.branch_id],
            expected_version=waiting.version, idempotency_key="replay-wrong-count", user_confirmed=True,
        )
        receipt = result.worker_runs[0]
        assert receipt.model_called
        assert not receipt.output_used, receipt.model_dump(mode="json")
        assert "数字" in receipt.error
        assert not result.artifact_versions
        assert not result.workspace_artifacts and not result.effect_receipts
        assert analyst.calls == 1  # Numeric conflict is not a structural retry.
        assert all(item.gate_status != "adopted" for item in result.contributions)
    finally:
        await runtime.close()


def test_selected_ux_sheet_supplies_all_rows_and_keeps_them_reviewable():
    catalog = BenchmarkWorkspaceCatalog(ROOT / "demo-enterprise-data/forte")
    ref = saved_run()["plan"]["units"][2]["input_file_refs"][1]
    preview = catalog.public_file(ref)
    payload = catalog.agent_file_inputs([ref])[0]
    assert len(preview["rows"]) == preview["total_rows"] == 212
    assert len(payload["rows"]) == payload["total_rows"] == 212
    assert not payload["truncated"]
    assert payload["rows"] == preview["rows"]
    assert not model_input_coverage([payload])[0].bounded


def test_search_sources_tail_is_present_and_byte_budget_still_enforced(monkeypatch):
    catalog = BenchmarkWorkspaceCatalog(ROOT / "demo-enterprise-data/forte")
    refs = saved_run()["plan"]["units"][1]["input_file_refs"]
    files = catalog.agent_file_inputs(refs)
    assert all(not item.bounded for item in model_input_coverage(files))
    for file in files:
        assert file["text"] == catalog.public_file(file["file_ref"])["text"]
    monkeypatch.setattr(catalog, "MAX_AGENT_CONTEXT_BYTES", 100)
    with pytest.raises(BenchmarkScenarioError, match="安全上下文上限"):
        catalog.agent_file_inputs(refs)


class LocatedAnalyst:
    model = "offline-located-counts-and-parents"

    def __init__(self, wrong_product=False):
        self.wrong_product = wrong_product
        self.inputs = []

    async def analyze(self, *, plan, files, dependency_context=None, readonly_context=None, **kwargs):
        self.inputs.append({"unit": plan.units[0].unit_id, "parents": dependency_context or [],
                            "counts": readonly_context})
        if self.wrong_product and plan.units[0].unit_id == "u_product_mgmt_review":
            return await ReplayAnalyst(0).analyze()
        scopes = [item["source_file_refs"] for item in dependency_context or []] or [[item["file_ref"] for item in files]]
        findings = []
        for index, refs in enumerate(scopes):
            source = next(item for item in files if item["file_ref"] in refs and item.get("text"))
            quote = next(line.strip() for line in source["text"].splitlines()
                         if 12 <= len(line.strip()) <= 300 and source["text"].count(line.strip()) == 1)
            findings.append(HarnessFinding(
                plan_unit_id=plan.units[0].unit_id, title=f"依据第 {index + 1} 份原文核对", detail="仅说明来源规则，实际结论仍需业务复核。",
                file_refs=[item["file_ref"] for item in files],
                evidence_quotes=[{"file_ref": source["file_ref"], "role": "context", "label": "来源", "quote": quote}],
            ))
        summary = "批准范围的来源已核对，仍需业务复核。"
        if readonly_context:
            counts = readonly_context["counts"]
            summary = f"P0 功能共 {counts['p0_features']} 项。配置清单仅 {counts['submitted_features']} 项已提测。"
        return HarnessTaskResult(summary=summary, findings=findings, dependency_assessments=[
            DependencyAssessmentDraft(contribution_id=item["contribution_id"], verdict="supported",
                                      explanation="受控用例重新引用批准原文。", finding_indices=[index])
            for index, item in enumerate(dependency_context or [])
        ])


@pytest.mark.asyncio
@pytest.mark.parametrize("wrong_product", [False, True])
async def test_real_source_two_waves_preserve_siblings_and_block_wrong_parent(wrong_product):
    analyst = LocatedAnalyst(wrong_product)
    runtime = HarnessRuntime(BenchmarkWorkspaceCatalog(ROOT / "demo-enterprise-data/forte"), ReplayPlanner(), analyst)
    async def wave(current, key):
        return await runtime.execute_admitted_workers_from_branches(
            "reliability", current.run_id, branch_ids=[], expected_version=current.version,
            idempotency_key=key, user_confirmed=True,
        )
    try:
        first = await wave(await admitted(runtime), "source-roots")
        assert sum(item.output_used for item in first.worker_runs) == (2 if wrong_product else 3)
        previous = first.artifact_versions[0].model_dump(mode="json")
        second = await wave(first, "source-dependent")
        assert second.artifact_versions[0].model_dump(mode="json") == previous
        assert not second.workspace_artifacts and not second.effect_receipts
        assert len(analyst.inputs) == (4 if wrong_product else 5)
        assert analyst.inputs[0]["counts"]["counts"]["p0_features"] == 7
        assert len(analyst.inputs[3]["parents"]) >= 1
        if wrong_product:
            assert not any(item["unit"] == "u_product_ux_compare" for item in analyst.inputs)
            assert second.status == "waiting_input"
        else:
            assert second.status == "completed"
            assert all(item.output_used for item in second.worker_runs)
            assert sum(len(item.dependency_assessments) for item in second.worker_runs) == 3
        before_calls = len(analyst.inputs)
        replay = await wave(first, "source-dependent")
        assert replay.model_dump(mode="json") == second.model_dump(mode="json")
        assert len(analyst.inputs) == before_calls
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_single_controller_numeric_failure_also_withheld_without_retry():
    class SinglePlanner(ReplayPlanner):
        async def plan(self, **kwargs):
            candidate = await super().plan(**kwargs)
            return candidate.model_copy(update={"units": candidate.units[:1]})
    analyst = ReplayAnalyst(1)
    runtime = HarnessRuntime(BenchmarkWorkspaceCatalog(ROOT / "demo-enterprise-data/forte"), SinglePlanner(), analyst)
    try:
        run = await admitted(runtime)
        assert analyst.calls == 1
        assert not any(item.findings for item in run.artifact_versions) and not run.result
        assert run.analysis_receipt.called and not run.analysis_receipt.output_used
        assert not run.workspace_artifacts and not run.effect_receipts
        assert any(event.details.get("failure_kind") == "source_numeric_conflict" for event in run.events)
    finally:
        await runtime.close()
