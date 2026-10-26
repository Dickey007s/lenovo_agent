"""Work decomposition is not an instruction to create one Agent per item."""

import json

import httpx
import pytest
from pydantic import ValidationError

from services.api.app.application.execution_approach import ExecutionApproach, load_skills, skill_catalog
from services.api.app.application.harness_runtime import (
    HarnessRuntime, HarnessPlanCandidate, HarnessModelError,
    OpenAICompatibleHarnessAnalyst,
)
from services.api.app.application.topology_admission import admit_topology
from tests.acceptance.test_adaptive_progress import AdaptivePlanner, start
from tests.acceptance.test_demo1_demo2_fixed_scenarios import _ten_file_cross_function_catalog, _wait_for
from tests.unit.test_harness_runtime import FakeAnalyst


class PrimaryPlanner(AdaptivePlanner):
    async def plan(self, **kwargs):
        plan = await super().plan(**kwargs)
        return plan.model_copy(update={"units": [u.model_copy(update={"input_file_refs": u.input_file_refs[:1]}) for u in plan.units[:2]], "execution_approach": ExecutionApproach(
            reason="两个短清单可在同一上下文整理，无需隔离分析。"), "skill_ids": ["source_extract"]})


class PrimaryAnalyst(FakeAnalyst):
    def __init__(self):
        super().__init__()
        self.plans = []

    async def analyze(self, *, instruction, plan, files, **kwargs):
        self.plans.append(plan)
        findings = []
        for unit in plan.units:
            result = await super().analyze(instruction=instruction, plan=plan.model_copy(update={"units": [unit]}),
                files=[f for f in files if f["file_ref"] in unit.input_file_refs])
            findings.extend(f.model_copy(update={"plan_unit_id": unit.unit_id}) for f in result.findings)
        return result.model_copy(update={"findings": findings})


@pytest.mark.asyncio
async def test_two_work_items_use_one_primary_analysis_without_losing_branches():
    planner, analyst = PrimaryPlanner("none"), PrimaryAnalyst()
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), planner, analyst)
    try:
        started = await start(runtime)
        final = await _wait_for(runtime, "adaptive", started.run.run_id,
                                lambda s: s.status in {"completed", "waiting_input", "failed"} and s.analysis_receipt is not None)
        assert final.status == "completed", final.validation_errors
        assert len(final.plan.units) == len(final.branches) == 2
        assert len(analyst.plans) == 1
        assert all(b.status == "completed" for b in final.branches)
        assert final.budget.model_calls_used == 2
        assert not final.worker_runs
        assert not planner.contexts  # Multi-unit primary expansion is not yet implemented.
        assert final.topology_admission.mode == "single_controller"
        public = runtime.public_snapshot(final)
        assert public.plan.skill_ids == ["source_extract"]
        assert "procedure" not in public.model_dump_json()
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_delegation_proposal_still_passes_server_gates():
    candidate = await PrimaryPlanner().plan(scenario={}, files=_ten_file_cross_function_catalog().files)
    plan = HarnessRuntime._compile_plan(candidate).model_copy(update={"execution_approach": ExecutionApproach(
                           mode="delegate", benefit="parallel_depth", reason="各分支需独立深入核对。")})
    facts = {ref: {"display_group": str(i)} for i, unit in enumerate(plan.units) for ref in unit.input_file_refs}
    def admit(p=plan, calls=8, automatic=True):
        return admit_topology(p, remaining_model_calls=calls, remaining_time_seconds=100,
                              source_facts=facts, allow_adaptive_waves=automatic)
    assert admit().mode == "adaptive_readonly_workers"
    assert admit(calls=1).mode == "fixed_workflow"
    unsafe = plan.model_copy(update={"units": [u.model_copy(update={"requires_human_gate": True}) for u in plan.units]})
    assert admit(unsafe).mode == "fixed_workflow"
    primary = plan.model_copy(update={"execution_approach": ExecutionApproach()})
    assert admit(primary).mode == "single_controller"
    assert admit(primary, automatic=False).mode == "adaptive_readonly_workers"
    no_benefit = plan.model_copy(update={"execution_approach": ExecutionApproach(mode="delegate")})
    assert admit(no_benefit).mode == "single_controller"


def test_skills_are_allowlisted_and_progressively_loaded():
    assert all("procedure" not in item for item in skill_catalog())
    loaded = load_skills(["source_extract", "source_extract"])
    assert len(loaded) == 1 and loaded[0]["procedure"]
    with pytest.raises(ValidationError) as error:
        HarnessPlanCandidate.model_validate({"summary": "x", "units": [{
            "unit_id": "extract", "title": "Extract", "objective": "Extract approved text",
            "input_file_refs": ["source-a"], "tool": "file.read",
        }], "skill_ids": ["arbitrary_shell"]})
    assert any(item["loc"] == ("skill_ids", 0) for item in error.value.errors())


@pytest.mark.asyncio
async def test_builtin_analyst_payload_loads_only_selected_procedures(monkeypatch):
    candidate = await PrimaryPlanner().plan(scenario={}, files=_ten_file_cross_function_catalog().files)
    plan = HarnessRuntime._compile_plan(candidate)
    captured = []
    original = httpx.AsyncClient
    def receive(request):
        captured.append(json.loads(request.content))
        return httpx.Response(503, text="controlled test")
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(receive)))
    analyst = OpenAICompatibleHarnessAnalyst(base_url="https://example.invalid/v1", api_key="test-only")
    with pytest.raises(HarnessModelError):
        await analyst.analyze(instruction="整理清单", plan=plan, files=[])
    body = json.loads(captured[0]["messages"][1]["content"])
    assert [s["id"] for s in body["loaded_skills"]] == ["source_extract"]
    assert body["loaded_skills"][0]["procedure"]
