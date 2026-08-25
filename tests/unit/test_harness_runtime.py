from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from services.api.app.application.harness_runtime import (
    HarnessConflictError,
    HarnessFinding,
    HarnessPlan,
    HarnessPlanUnit,
    HarnessPlanError,
    HarnessModelError,
    OpenAICompatibleHarnessPlanner,
    HarnessRunStart,
    HarnessRuntime,
    HarnessTaskResult,
)
from services.api.app.main import create_app


class FakeCatalog:
    def __init__(self):
        self.scenario = {
            "scenario_id": "finance-018",
            "title": "跨期往来核查",
            "selection_reason": "任务要求核对三个期间的原始往来明细",
            "allowlisted_tools": ["spreadsheet.read", "document.draft"],
            "files": [
                {"path": "Finance-018/input/2025.xlsx", "role": "input", "mime": "xlsx", "size": 12, "sha256": "a" * 64},
                {"path": "Finance-018/input/2026.xlsx", "role": "input", "mime": "xlsx", "size": 12, "sha256": "b" * 64},
            ],
        }

    def list_scenarios(self):
        return [self.scenario]

    def get_scenario(self, scenario_id):
        if scenario_id != self.scenario["scenario_id"]:
            raise KeyError(scenario_id)
        return self.scenario


class FakePlanner:
    model = "deepseek-v4-pro"

    def __init__(self, invalid: str | None = None):
        self.invalid = invalid
        self.calls = 0

    async def plan(self, *, scenario, files):
        self.calls += 1
        if self.invalid == "path":
            file_ref = "forte-0000000000000000"
        else:
            file_ref = files[0]["file_ref"]
        depends = [] if self.invalid != "cycle" else ["u2"]
        return HarnessPlan(
            summary=f"动态计划 {self.calls}",
            units=[
                HarnessPlanUnit(unit_id="u1", title="读取明细", objective="读取文件", input_file_refs=[file_ref], tool="spreadsheet.read", depends_on=depends),
                HarnessPlanUnit(unit_id="u2", title="形成摘要", objective="形成摘要", input_file_refs=[files[-1]["file_ref"]], tool="document.draft", depends_on=["u1"]),
            ],
        )


class CapturingPlanner(FakePlanner):
    def __init__(self):
        super().__init__()
        self.scenario = None
        self.files = None

    async def plan(self, *, scenario, files):
        self.scenario = scenario
        self.files = files
        return await super().plan(scenario=scenario, files=files)


class FakeAnalyst:
    model = "deepseek-v4-pro"

    def __init__(self, invalid_reference: bool = False):
        self.invalid_reference = invalid_reference
        self.instruction = None
        self.files = None

    async def analyze(self, *, instruction, plan, files):
        self.instruction = instruction
        self.files = files
        file_ref = "forte-0000000000000000" if self.invalid_reference else files[0]["file_ref"]
        return HarnessTaskResult(
            summary="只读核查完成",
            findings=[
                HarnessFinding(
                    title="发现一项待关注事实",
                    detail="该结论来自所选公开文件。",
                    file_refs=[file_ref],
                )
            ],
            follow_ups=["请人工复核业务口径"],
            review_required=True,
        )


async def wait_terminal(runtime: HarnessRuntime, owner: str, run_id: str):
    for _ in range(100):
        snapshot = await runtime.get(owner, run_id)
        if snapshot.status in {"ready_to_execute", "completed", "failed"}:
            return snapshot
        await asyncio.sleep(0)
    raise AssertionError("harness run did not reach a terminal planning state")


@pytest.mark.asyncio
async def test_dynamic_plan_has_model_receipt_and_ready_boundary():
    planner = FakePlanner()
    runtime = HarnessRuntime(FakeCatalog(), planner)
    result = await runtime.start("alice", HarnessRunStart(scenario_id="finance-018", idempotency_key="dynamic-plan-1"))
    snapshot = await wait_terminal(runtime, "alice", result.run.run_id)
    assert snapshot.status == "ready_to_execute"
    assert snapshot.plan is not None and snapshot.plan.summary == "动态计划 1"
    assert snapshot.model_receipt is not None and snapshot.model_receipt.output_used is True
    assert snapshot.source_documents[0]["path"].endswith("2025.xlsx")
    assert [event.event_name for event in snapshot.events] == [
        "workspace_index", "planning_started", "planning_completed",
        "plan_validation", "ready_to_execute",
    ]
    assert snapshot.last_event_sequence == snapshot.events[-1].sequence == 5
    assert snapshot.events[-1].details["execution_started"] is False


@pytest.mark.asyncio
async def test_custom_instruction_selected_files_and_read_only_result_complete():
    planner = CapturingPlanner()
    analyst = FakeAnalyst()
    runtime = HarnessRuntime(FakeCatalog(), planner, analyst)
    first_ref = runtime._stable_file_ref(
        "finance-018", "Finance-018/input/2025.xlsx"
    )
    request = HarnessRunStart(
        scenario_id="finance-018",
        idempotency_key="custom-read-only-1",
        instruction="只核对 2025 文件中仍有余额的客商",
        selected_file_refs=[first_ref],
    )

    started = await runtime.start("alice", request)
    snapshot = await wait_terminal(runtime, "alice", started.run.run_id)

    assert snapshot.status == "completed"
    assert snapshot.instruction_source == "user"
    assert snapshot.instruction == request.instruction
    assert planner.scenario["task_instruction"] == request.instruction
    assert "input_dir" not in planner.scenario
    assert [item["file_ref"] for item in planner.files] == [first_ref]
    assert all("path" not in item and "sha256" not in item for item in planner.files)
    assert analyst.instruction == request.instruction
    assert analyst.files == [
        {
            "file_ref": first_ref,
            "display_label": "公开办公输入文件",
            "display_summary": "公开办公输入文件",
        }
    ]
    assert snapshot.analysis_receipt and snapshot.analysis_receipt.output_used is True
    assert snapshot.result and snapshot.result.findings[0].file_refs == [first_ref]
    assert [event.event_name for event in snapshot.events] == [
        "workspace_index",
        "planning_started",
        "planning_completed",
        "plan_validation",
        "analysis_started",
        "analysis_completed",
        "result_validation",
        "task_completed",
    ]
    public = runtime.public_snapshot(snapshot).model_dump(mode="json")
    serialized = json.dumps(public, ensure_ascii=False)
    assert request.instruction in serialized
    assert "Finance-018/input" not in serialized
    assert "sha256" not in serialized


@pytest.mark.asyncio
async def test_custom_file_selection_and_result_citations_fail_closed():
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst(True))
    unknown_ref = "forte-0000000000000000"
    started = await runtime.start(
        "alice",
        HarnessRunStart(
            scenario_id="finance-018",
            idempotency_key="unknown-selection-1",
            instruction="核对所选文件",
            selected_file_refs=[unknown_ref],
        ),
    )
    snapshot = await wait_terminal(runtime, "alice", started.run.run_id)
    assert snapshot.status == "failed"
    assert "所选文件不属于" in snapshot.validation_errors[0]

    valid_ref = runtime._stable_file_ref(
        "finance-018", "Finance-018/input/2025.xlsx"
    )
    started = await runtime.start(
        "alice",
        HarnessRunStart(
            scenario_id="finance-018",
            idempotency_key="invalid-citation-1",
            instruction="核对所选文件",
            selected_file_refs=[valid_ref],
        ),
    )
    snapshot = await wait_terminal(runtime, "alice", started.run.run_id)
    assert snapshot.status == "failed"
    assert "未选择的文件" in snapshot.validation_errors[0]
    assert snapshot.result is None


@pytest.mark.asyncio
async def test_invalid_path_fails_closed_without_execution():
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner("path"))
    result = await runtime.start("alice", HarnessRunStart(scenario_id="finance-018", idempotency_key="invalid-path-1"))
    snapshot = await wait_terminal(runtime, "alice", result.run.run_id)
    assert snapshot.status == "failed"
    assert snapshot.plan is None
    assert snapshot.model_receipt is not None and snapshot.model_receipt.output_used is False
    assert snapshot.events[-1].event_name == "harness_failed"
    assert snapshot.events[-1].details["execution_started"] is False


class FreeTextSideEffectPlanner:
    model = "deepseek-v4-pro"

    async def plan(self, *, scenario, files):
        # Simulates the JSON parser rejecting the model's free-text side_effect.
        try:
            HarnessPlanUnit(
                unit_id="u", title="write", objective="write", input_file_refs=[files[0]["file_ref"]],
                tool="artifact.write", side_effect="write Finance-018/input/out.csv",
            )
        except ValidationError as exc:
            raise HarnessModelError("invalid side_effect", called=True, elapsed_ms=3) from exc
        raise AssertionError("unreachable")


@pytest.mark.asyncio
async def test_model_returning_free_text_side_effect_is_not_marked_used():
    runtime = HarnessRuntime(FakeCatalog(), FreeTextSideEffectPlanner())
    result = await runtime.start("alice", HarnessRunStart(scenario_id="finance-018", idempotency_key="free-side-effect-1"))
    snapshot = await wait_terminal(runtime, "alice", result.run.run_id)
    assert snapshot.status == "failed"
    assert snapshot.model_receipt and snapshot.model_receipt.called is True
    assert snapshot.model_receipt.output_used is False
    assert [event.event_name for event in snapshot.events][-2:] == ["planning_completed", "harness_failed"]


class UnscopedArtifactPlanner:
    model = "deepseek-v4-pro"

    async def plan(self, *, scenario, files):
        return HarnessPlan(
            summary="读取资料并形成核对结果",
            units=[
                HarnessPlanUnit(
                    unit_id="read",
                    title="读取资料",
                    objective="读取所选公开文件",
                    input_file_refs=[files[0]["file_ref"]],
                    tool="spreadsheet.read",
                ),
                HarnessPlanUnit(
                    unit_id="result",
                    title="形成核对结果",
                    objective="整理本轮只读分析结果",
                    input_file_refs=[files[0]["file_ref"]],
                    depends_on=["read"],
                    tool="artifact.write",
                ),
            ],
        )


@pytest.mark.asyncio
async def test_runtime_compiles_artifact_write_scope_instead_of_trusting_the_model():
    catalog = FakeCatalog()
    catalog.scenario = catalog.scenario | {
        "allowlisted_tools": ["spreadsheet.read", "artifact.write"],
        "allowed_side_effects": ["none", "run_workspace_write"],
    }
    runtime = HarnessRuntime(catalog, UnscopedArtifactPlanner())

    started = await runtime.start(
        "alice",
        HarnessRunStart(
            scenario_id="finance-018",
            idempotency_key="server-owned-artifact-scope-1",
        ),
    )
    snapshot = await wait_terminal(runtime, "alice", started.run.run_id)

    assert snapshot.status == "ready_to_execute"
    assert snapshot.plan is not None
    assert snapshot.plan.units[0].side_effect == "none"
    assert snapshot.plan.units[1].side_effect == "run_workspace_write"
    assert snapshot.plan.units[1].artifact_name == "run-result-2"
    assert snapshot.plan.units[1].artifact_type == "analysis"
    assert snapshot.model_receipt is not None
    assert snapshot.model_receipt.output_used is True


@pytest.mark.asyncio
async def test_public_failure_projection_hides_internal_effect_contract_names():
    class UnknownToolPlanner:
        model = "deepseek-v4-pro"

        async def plan(self, *, scenario, files):
            return HarnessPlan(
                summary="形成结果",
                units=[
                    HarnessPlanUnit(
                        unit_id="result",
                        title="形成结果",
                        objective="整理本轮结果",
                        input_file_refs=[files[0]["file_ref"]],
                        tool="shell.exec",
                    )
                ],
            )

    catalog = FakeCatalog()
    catalog.scenario = catalog.scenario | {
        "allowlisted_tools": ["artifact.write"],
        "allowed_side_effects": ["none", "run_workspace_write"],
    }
    runtime = HarnessRuntime(catalog, UnknownToolPlanner())
    started = await runtime.start(
        "alice",
        HarnessRunStart(
            scenario_id="finance-018",
            idempotency_key="safe-public-plan-error-1",
        ),
    )
    snapshot = await wait_terminal(runtime, "alice", started.run.run_id)
    public = runtime.public_snapshot(snapshot)
    serialized = public.model_dump_json()

    assert snapshot.status == "failed"
    assert "未允许的工具" in snapshot.validation_errors[0]
    assert public.validation_errors == [
        "规划使用了当前任务范围外的资料或能力，系统已安全停止。请重新规划。"
    ]
    assert "shell.exec" not in serialized


@pytest.mark.asyncio
async def test_unconfigured_planner_reports_not_called():
    planner = OpenAICompatibleHarnessPlanner(base_url="", api_key="")
    with pytest.raises(HarnessModelError) as raised:
        await planner.plan(scenario={}, files=[])
    assert raised.value.called is False
    assert raised.value.elapsed_ms == 0


@pytest.mark.asyncio
async def test_http_attempted_error_reports_called(monkeypatch):
    class BrokenClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            raise httpx.ConnectError("simulated connection error")

    monkeypatch.setattr("services.api.app.application.harness_runtime.httpx.AsyncClient", BrokenClient)
    planner = OpenAICompatibleHarnessPlanner(base_url="http://model.test", api_key="key")
    with pytest.raises(HarnessModelError) as raised:
        await planner.plan(scenario={}, files=[])
    assert raised.value.called is True
    assert raised.value.elapsed_ms >= 0


@pytest.mark.asyncio
async def test_runtime_preserves_model_call_fact_on_planner_error():
    class PlannerError:
        model = "deepseek-v4-pro"

        async def plan(self, *, scenario, files):
            raise HarnessModelError("invalid JSON", called=True, elapsed_ms=17, model=self.model)

    runtime = HarnessRuntime(FakeCatalog(), PlannerError())
    result = await runtime.start("alice", HarnessRunStart(scenario_id="finance-018", idempotency_key="planner-error-1"))
    snapshot = await wait_terminal(runtime, "alice", result.run.run_id)
    assert snapshot.model_receipt is not None
    assert snapshot.model_receipt.called is True
    assert snapshot.model_receipt.model == "deepseek-v4-pro"
    assert snapshot.model_receipt.elapsed_ms == 17
    assert snapshot.model_receipt.output_used is False
    assert snapshot.events[-1].details["model_called"] is True
    assert snapshot.events[-1].details["output_used"] is False


def test_plan_validator_rejects_unknown_tool_and_cycle():
    scenario = FakeCatalog().scenario
    files = HarnessRuntime._index_files(scenario)
    bad_tool = HarnessPlan(summary="x", units=[HarnessPlanUnit(unit_id="u", title="x", objective="x", input_file_refs=[files[0]["file_ref"]], tool="shell.exec")])
    with pytest.raises(HarnessPlanError, match="未允许"):
        HarnessRuntime._validate_plan(bad_tool, scenario, files)
    cyclic = HarnessPlan(summary="x", units=[
        HarnessPlanUnit(unit_id="u1", title="x", objective="x", input_file_refs=[files[0]["file_ref"]], tool="spreadsheet.read", depends_on=["u2"]),
        HarnessPlanUnit(unit_id="u2", title="y", objective="y", input_file_refs=[files[1]["file_ref"]], tool="spreadsheet.read", depends_on=["u1"]),
    ])
    with pytest.raises(HarnessPlanError, match="存在环"):
        HarnessRuntime._validate_plan(cyclic, scenario, files)


def test_plan_compiler_strips_model_artifact_metadata_from_non_write_tools():
    candidate = HarnessPlan(
        summary="核对证据",
        units=[
            HarnessPlanUnit(
                unit_id="verify",
                title="核对证据",
                objective="检查引用依据",
                input_file_refs=["forte-a0bccc1df48cc6a1"],
                tool="evidence.verify",
                artifact_name="model-proposed-evidence",
                artifact_type="evidence",
            )
        ],
    )

    compiled = HarnessRuntime._compile_plan(candidate)

    assert compiled.units[0].side_effect == "none"
    assert compiled.units[0].artifact_name is None
    assert compiled.units[0].artifact_type is None


@pytest.mark.asyncio
async def test_idempotency_owner_isolation_and_named_sse_replay():
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner())
    body = HarnessRunStart(scenario_id="finance-018", idempotency_key="same-key-1")
    first = await runtime.start("alice", body)
    replay = await runtime.start("alice", body)
    assert replay.replayed is True and replay.run.run_id == first.run.run_id
    with pytest.raises(HarnessConflictError):
        await runtime.start("alice", body.model_copy(update={"expected_version": 2}))
    with pytest.raises(Exception):
        await runtime.get("bob", first.run.run_id)
    snapshot = await wait_terminal(runtime, "alice", first.run.run_id)
    events = [event async for event in runtime.events("alice", first.run.run_id, after=0)]
    assert [event.event_name for event in events][-1] == "ready_to_execute"
    assert snapshot.version >= 2


def test_side_effect_contract_rejects_free_text_and_source_directory_output():
    scenario = FakeCatalog().scenario | {"allowlisted_tools": ["artifact.write"]}
    files = HarnessRuntime._index_files(scenario)
    with pytest.raises(ValidationError):
        HarnessPlanUnit(
            unit_id="u", title="x", objective="x", input_file_refs=[files[0]["file_ref"]],
            tool="artifact.write", side_effect="write Finance-018/input/out.csv",
        )
    with pytest.raises(ValidationError):
        HarnessPlanUnit(
            unit_id="u", title="x", objective="x", input_file_refs=[files[0]["file_ref"]],
            tool="artifact.write", side_effect="run_workspace_write", artifact_name="Finance-018/input/out.csv", artifact_type="summary",
        )
    invalid_mapping = HarnessPlan(
        summary="x", units=[HarnessPlanUnit(
            unit_id="u", title="x", objective="x", input_file_refs=[files[0]["file_ref"]],
            tool="artifact.write", side_effect="none", artifact_name="receivable-summary", artifact_type="summary",
        )],
    )
    with pytest.raises(HarnessPlanError, match="run_workspace_write"):
        HarnessRuntime._validate_plan(invalid_mapping, scenario, files)
    external_without_gate = HarnessPlan(
        summary="x", units=[HarnessPlanUnit(
            unit_id="u", title="x", objective="x", input_file_refs=[files[0]["file_ref"]],
            tool="file.read", side_effect="external_action",
        )],
    )
    with pytest.raises(HarnessPlanError, match="action.preview"):
        HarnessRuntime._validate_plan(external_without_gate, scenario | {"allowlisted_tools": ["file.read"]}, files)


class ThreeScenarioPlanner:
    model = "deepseek-v4-pro"

    async def plan(self, *, scenario, files):
        profile = scenario["work_profile"]
        tool = "table.inspect" if any(item["mime"].endswith("sheet") for item in files) else "file.read"
        return HarnessPlan(
            summary=f"{profile['task_topology']} dynamic plan",
            units=[HarnessPlanUnit(
                unit_id=f"{profile['task_topology']}-read", title="读取输入", objective=scenario["goal"],
                input_file_refs=[files[0]["file_ref"]], tool=tool,
            )],
        )


@pytest.mark.asyncio
async def test_real_catalog_capability_profiles_accept_dynamic_fake_plans():
    from services.api.app.application.benchmark_scenario_catalog import BenchmarkScenarioCatalog

    runtime = HarnessRuntime(BenchmarkScenarioCatalog(), ThreeScenarioPlanner())
    scenarios = runtime.list_scenarios()
    assert {item["work_profile"]["orchestration"] for item in scenarios} == {
        "bounded_loop",
        "adaptive_swarm",
    }
    for scenario in scenarios:
        result = await runtime.start("alice", HarnessRunStart(
            scenario_id=scenario["scenario_id"], idempotency_key=f"{scenario['scenario_id']}-fake-1",
        ))
        snapshot = await wait_terminal(runtime, "alice", result.run.run_id)
        assert snapshot.status == "ready_to_execute"
        assert snapshot.model_receipt and snapshot.model_receipt.output_used is True
        assert snapshot.source_documents
        assert all(
            item["path"].startswith(f"{scenario['scenario_id']}/input/")
            and item["display_label"]
            and item["display_group"]
            and item["display_summary"]
            for item in snapshot.source_documents
        )


@pytest.mark.asyncio
async def test_capability_side_effect_allowlist_is_per_business_scenario():
    from services.api.app.application.benchmark_scenario_catalog import BenchmarkScenarioCatalog

    class ActionPlanner:
        model = "deepseek-v4-pro"

        async def plan(self, *, scenario, files):
            return HarnessPlan(
                summary="candidate action",
                units=[HarnessPlanUnit(
                    unit_id="candidate", title="动作候选", objective="需要确认的受控动作",
                    input_file_refs=[files[0]["file_ref"]], tool="action.preview",
                )],
            )

    runtime = HarnessRuntime(BenchmarkScenarioCatalog(), ActionPlanner())
    for scenario_id in ("Finance-018", "pm-014"):
        result = await runtime.start("alice", HarnessRunStart(
            scenario_id=scenario_id, idempotency_key=f"action-{scenario_id}-1",
        ))
        snapshot = await wait_terminal(runtime, "alice", result.run.run_id)
        assert snapshot.status == "failed"
        assert "未允许的工具" in snapshot.validation_errors[0]

    result = await runtime.start(
        "alice",
        HarnessRunStart(scenario_id="Operations-008", idempotency_key="action-operations-1"),
    )
    snapshot = await wait_terminal(runtime, "alice", result.run.run_id)
    assert snapshot.status == "ready_to_execute"
    assert snapshot.plan and snapshot.plan.units[0].requires_human_gate is True
    assert snapshot.plan.units[0].side_effect == "external_action"
    assert snapshot.events[-1].details["execution_started"] is False


@pytest.mark.asyncio
async def test_public_route_returns_contract_not_planner_context():
    from services.api.app.application.benchmark_scenario_catalog import BenchmarkScenarioCatalog

    app = create_app()
    app.state.harness_runtime = HarnessRuntime(BenchmarkScenarioCatalog(), ThreeScenarioPlanner())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/harness/scenarios")
    assert response.status_code == 200
    payload = response.json()["scenarios"]
    assert {item["work_profile"]["task_topology"] for item in payload} == {
        "single_task",
        "multi_task",
    }
    for item in payload:
        serialized = json.dumps(item, ensure_ascii=False)
        assert "demo_id" not in serialized
        assert "experience_policy" not in serialized
        assert "task_instruction" not in serialized
        assert "/workspace/input" not in serialized
        assert "不要问我" not in serialized
        assert "rubrics" not in serialized
        assert "solution_files" not in serialized
        assert "345c1ec1487139db9dd319787fa9405ba85d1869" not in serialized
        assert all("path" not in file and "sha256" not in file for file in item["files"])


@pytest.mark.asyncio
async def test_public_file_preview_route_returns_real_content_without_raw_metadata():
    from services.api.app.application.benchmark_scenario_catalog import BenchmarkScenarioCatalog

    app = create_app()
    app.state.harness_runtime = HarnessRuntime(BenchmarkScenarioCatalog(), ThreeScenarioPlanner())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        listed = await client.get("/v1/harness/scenarios")
        finance = next(
            item for item in listed.json()["scenarios"] if item["scenario_id"] == "Finance-018"
        )
        file_ref = finance["files"][0]["file_ref"]
        preview = await client.get(f"/v1/harness/scenarios/Finance-018/files/{file_ref}")
        missing = await client.get(
            "/v1/harness/scenarios/Finance-018/files/forte-0000000000000000"
        )

    assert preview.status_code == 200
    payload = preview.json()
    assert payload["kind"] == "table"
    assert payload["columns"][:3] == ["科目名称", "客商名称", "方向"]
    assert "黄杉文化传播有限公司" in payload["rows"][0]["values"][1]
    serialized = preview.text
    assert "Finance-018/input" not in serialized
    assert "sha256" not in serialized
    assert "task_instruction" not in serialized
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_main_mounts_only_harness_and_health_routes():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert health.json()["task_store"] == "memory"
        for retired_path in (
            "/v1/workspace",
            "/v1/threads",
            "/v1/tasks",
            "/v1/demo2/cockpit",
            "/v1/demo3/scenarios",
        ):
            response = await client.get(retired_path)
            assert response.status_code == 404


@pytest.mark.asyncio
async def test_catalog_integrity_failure_is_exposed_as_503():
    from services.api.app.application.benchmark_scenario_catalog import BenchmarkScenarioError

    class BrokenRuntime:
        def list_scenarios(self):
            raise BenchmarkScenarioError("tampered")

    app = create_app()
    app.state.harness_runtime = BrokenRuntime()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/harness/scenarios")
    assert response.status_code == 503
    assert response.json()["detail"] == "场景目录完整性校验失败"


@pytest.mark.asyncio
async def test_harness_routes_asgi_snapshot_and_named_sse():
    app = create_app()
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner())
    app.state.harness_runtime = runtime
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        listed = await client.get("/v1/harness/scenarios")
        assert listed.status_code == 200
        started = await client.post(
            "/v1/harness/runs", headers={"X-User-Id": "alice"},
            json={"scenario_id": "finance-018", "idempotency_key": "route-test-1"},
        )
        assert started.status_code == 202
        started_text = started.text
        assert "Finance-018/input/2025.xlsx" not in started_text
        assert "sha256" not in started_text
        assert "task_instruction" not in started_text
        run_id = started.json()["run"]["run_id"]
        snapshot = await wait_terminal(runtime, "alice", run_id)
        fetched = await client.get(f"/v1/harness/runs/{run_id}", headers={"X-User-Id": "alice"})
        assert fetched.status_code == 200
        assert fetched.json()["last_event_sequence"] == snapshot.last_event_sequence
        fetched_text = fetched.text
        assert "Finance-018/input/2025.xlsx" not in fetched_text
        assert "sha256" not in fetched_text
        assert "task_instruction" not in fetched_text
        assert "forte-" in fetched_text
        assert "input_paths" not in fetched_text
        assert "input_file_refs" in fetched_text
        stream = await client.get(f"/v1/harness/runs/{run_id}/events?after=0", headers={"X-User-Id": "alice"})
        assert stream.status_code == 200
        assert "event: workspace_index" in stream.text
        assert "event: ready_to_execute" in stream.text
        assert "Finance-018/input/2025.xlsx" not in stream.text
        assert "sha256" not in stream.text
        assert "task_instruction" not in stream.text
        assert "forte-" in stream.text


@pytest.mark.asyncio
async def test_harness_sse_missing_or_wrong_owner_returns_404():
    app = create_app()
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner())
    app.state.harness_runtime = runtime
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        missing = await client.get(
            "/v1/harness/runs/not-a-run/events?after=0",
            headers={"X-User-Id": "alice"},
        )
        assert missing.status_code == 404

        started = await client.post(
            "/v1/harness/runs",
            headers={"X-User-Id": "alice"},
            json={"scenario_id": "finance-018", "idempotency_key": "sse-owner-test-1"},
        )
        assert started.status_code == 202
        run_id = started.json()["run"]["run_id"]
        wrong_owner = await client.get(
            f"/v1/harness/runs/{run_id}/events?after=0",
            headers={"X-User-Id": "bob"},
        )
        assert wrong_owner.status_code == 404


@pytest.mark.asyncio
async def test_real_catalog_run_projection_hides_raw_file_metadata():
    from services.api.app.application.benchmark_scenario_catalog import BenchmarkScenarioCatalog

    app = create_app()
    runtime = HarnessRuntime(BenchmarkScenarioCatalog(), ThreeScenarioPlanner())
    app.state.harness_runtime = runtime
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        started = await client.post(
            "/v1/harness/runs", headers={"X-User-Id": "alice"},
            json={"scenario_id": "Finance-018", "idempotency_key": "real-route-projection-1"},
        )
        assert started.status_code == 202
        run_id = started.json()["run"]["run_id"]
        await wait_terminal(runtime, "alice", run_id)
        fetched = await client.get(f"/v1/harness/runs/{run_id}", headers={"X-User-Id": "alice"})
        assert fetched.status_code == 200
        payload = fetched.json()
        serialized = fetched.text
        assert "2026往来明细.xlsx" not in serialized
        assert "Finance-018/input" not in serialized
        assert "sha256" not in serialized
        assert '"summary":{"kind"' not in serialized
        assert "task_instruction" not in serialized
        assert "rubric" not in serialized.lower()
        assert "solution" not in serialized.lower()
        assert payload["source_documents"][0]["file_ref"].startswith("forte-")
        assert payload["plan"]["units"][0]["input_file_refs"] == [
            payload["source_documents"][0]["file_ref"]
        ]
