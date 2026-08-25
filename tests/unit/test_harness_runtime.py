from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from packages.contracts.harness_models import AgentControlLoopControlRequest

from services.api.app.application.harness_runtime import (
    HarnessConflictError,
    HarnessFinding,
    HarnessModelError,
    HarnessPlanCandidate,
    HarnessPlanCandidateUnit,
    HarnessPlanUnit,
    HarnessRunStart,
    HarnessRuntime,
    HarnessTaskResult,
    build_harness_runtime,
)
from services.api.app.main import create_app


REF_ONE = "forte-1111111111111111"
REF_TWO = "forte-2222222222222222"


class FakeCatalog:
    def __init__(self, *, broken: bool = False) -> None:
        self.broken = broken
        self.files = [
            {
                "file_ref": REF_ONE,
                "folder_id": "forte-folder-111111111111",
                "path": "Finance-018/input/2025.csv",
                "role": "input",
                "mime": "text/csv",
                "size": 12,
                "sha256": "a" * 64,
                "display_label": "2025 往来明细.csv",
                "display_group": "财务管理",
                "display_path": "财务管理/2025 往来明细.csv",
                "display_summary": "CSV 表格 · 12 B",
            },
            {
                "file_ref": REF_TWO,
                "folder_id": "forte-folder-111111111111",
                "path": "Finance-018/input/2026.txt",
                "role": "input",
                "mime": "text/plain",
                "size": 12,
                "sha256": "b" * 64,
                "display_label": "2026 复核说明.txt",
                "display_group": "财务管理",
                "display_path": "财务管理/2026 复核说明.txt",
                "display_summary": "文本文件 · 12 B",
            },
        ]

    def public_workspace(self) -> dict[str, object]:
        if self.broken:
            raise RuntimeError("manifest failed")
        return {
            "workspace_id": "forte-public-office",
            "title": "FORTE 公开办公资料库",
            "dataset_label": "公开办公基准数据 · FORTE",
            "dataset_version": "固定版本 · 345c1ec",
            "source_label": "AGI-Eval-Official/FORTE 公开 demo inputs",
            "license": "Apache-2.0",
            "data_boundary": "只读公开输入",
            "file_count": 2,
            "folder_count": 1,
            "previewable_file_count": 2,
            "folders": [
                {
                    "folder_id": "forte-folder-111111111111",
                    "display_label": "财务管理",
                    "display_summary": "跨期间往来资料",
                    "availability": "local_input_bundle",
                    "external_dependency_label": None,
                    "file_count": 2,
                    "total_bytes": 24,
                    "files": [
                        {
                            key: value
                            for key, value in item.items()
                            if key
                            in {
                                "file_ref",
                                "folder_id",
                                "display_label",
                                "display_group",
                                "display_path",
                                "display_summary",
                            }
                        }
                        | {
                            "extension": "CSV" if index == 0 else "TXT",
                            "mime": item["mime"],
                            "size": item["size"],
                            "preview_kind": "table" if index == 0 else "text",
                            "preview_available": True,
                        }
                        for index, item in enumerate(self.files)
                    ],
                }
            ],
        }

    def internal_workspace(self) -> dict[str, object]:
        if self.broken:
            raise RuntimeError("manifest failed")
        return {
            "workspace_id": "forte-public-office",
            "title": "FORTE 公开办公资料库",
            "allowlisted_tools": [
                "file.read",
                "table.inspect",
                "artifact.write",
                "evidence.verify",
            ],
            "allowed_side_effects": ["none", "run_workspace_write"],
            "deliverables": ["带文件引用的初步分析结果"],
            "data_boundary": "只读所选公开输入",
            "human_gate_summary": "模型结果必须由用户复核",
            "files": self.files,
        }

    def public_file(self, file_ref: str) -> dict[str, object]:
        if file_ref not in {REF_ONE, REF_TWO}:
            raise KeyError(file_ref)
        return {
            "workspace_id": "forte-public-office",
            "file_ref": file_ref,
            "folder_id": "forte-folder-111111111111",
            "display_label": "2025 往来明细.csv" if file_ref == REF_ONE else "2026 复核说明.txt",
            "display_group": "财务管理",
            "display_path": "财务管理/文件",
            "display_summary": "公开办公输入",
            "mime": "text/csv" if file_ref == REF_ONE else "text/plain",
            "size": 12,
            "kind": "table" if file_ref == REF_ONE else "text",
            "columns": ["客商", "余额"] if file_ref == REF_ONE else [],
            "rows": [{"row_number": 2, "values": ["A", "100"]}] if file_ref == REF_ONE else [],
            "total_rows": 1 if file_ref == REF_ONE else None,
            "text": None if file_ref == REF_ONE else "复核说明",
            "truncated": False,
            "security": {
                "integrity_verified": True,
                "read_only": True,
                "active_content_executed": False,
                "external_resources_loaded": False,
                "notes": ["已核对"],
            },
        }

    def agent_file_inputs(self, file_refs: list[str]) -> list[dict[str, object]]:
        return [
            {
                "file_ref": file_ref,
                "display_label": next(item["display_label"] for item in self.files if item["file_ref"] == file_ref),
                "kind": "table" if file_ref == REF_ONE else "text",
                "text": "复核说明" if file_ref == REF_TWO else None,
            }
            for file_ref in file_refs
        ]


class FakePlanner:
    model = "deepseek-v4-pro"

    def __init__(self, invalid: str | None = None) -> None:
        self.invalid = invalid
        self.calls = 0
        self.workspace: dict[str, object] | None = None
        self.files: list[dict[str, object]] | None = None

    async def plan(self, *, scenario, files):
        self.calls += 1
        self.workspace = scenario
        self.files = files
        if self.invalid == "model":
            raise HarnessModelError("bad model output", called=True, elapsed_ms=12)
        first_ref = "forte-0000000000000000" if self.invalid == "reference" else files[0]["file_ref"]
        second_tool = "action.preview" if self.invalid == "external" else "artifact.write"
        return HarnessPlanCandidate(
            summary=f"围绕 {files[0]['file_ref']} 的动态计划 {self.calls}",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="u1",
                    title="读取资料",
                    objective="读取所选文件",
                    input_file_refs=[first_ref],
                    tool="file.read",
                ),
                HarnessPlanCandidateUnit(
                    unit_id="u2",
                    title="形成结果",
                    objective="形成可引用的初步分析",
                    input_file_refs=[files[-1]["file_ref"]],
                    depends_on=["u1"],
                    tool=second_tool,
                    artifact_name="analysis-result" if second_tool == "artifact.write" else None,
                    artifact_type="analysis" if second_tool == "artifact.write" else None,
                ),
            ],
        )


class BlockingPlanner(FakePlanner):
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def plan(self, *, scenario, files):
        self.started.set()
        await self.release.wait()
        return await super().plan(scenario=scenario, files=files)


class RepairablePlanner(FakePlanner):
    async def plan(self, *, scenario, files):
        self.invalid = "reference" if self.calls == 0 else None
        return await super().plan(scenario=scenario, files=files)


class FakeAnalyst:
    model = "deepseek-v4-pro"

    def __init__(self, invalid_reference: bool = False) -> None:
        self.invalid_reference = invalid_reference
        self.instruction: str | None = None

    async def analyze(self, *, instruction, plan, files):
        self.instruction = instruction
        file_ref = "forte-0000000000000000" if self.invalid_reference else files[0]["file_ref"]
        return HarnessTaskResult(
            summary=f"{file_ref} 只读核查完成",
            findings=[
                HarnessFinding(
                    title="发现一项待复核事实",
                    detail="该结论来自所选公开文件。",
                    file_refs=[file_ref],
                )
            ],
            follow_ups=["请人工复核业务口径"],
            review_required=True,
        )


def start_request(**updates) -> HarnessRunStart:
    payload = {
        "workspace_id": "forte-public-office",
        "idempotency_key": "workspace-run-0001",
        "instruction": "核对所选资料中的跨期余额变化",
        "selected_file_refs": [REF_ONE, REF_TWO],
    }
    payload.update(updates)
    return HarnessRunStart(**payload)


async def wait_terminal(runtime: HarnessRuntime, owner: str, run_id: str):
    for _ in range(200):
        snapshot = await runtime.get(owner, run_id)
        if snapshot.status in {"ready_to_execute", "completed", "stopped", "failed"}:
            return snapshot
        await asyncio.sleep(0)
    raise AssertionError("harness run did not reach a terminal state")


@pytest.mark.asyncio
async def test_user_task_runs_over_selected_workspace_files() -> None:
    planner = FakePlanner()
    analyst = FakeAnalyst()
    runtime = HarnessRuntime(FakeCatalog(), planner, analyst)

    started = await runtime.start("alice", start_request())
    snapshot = await wait_terminal(runtime, "alice", started.run.run_id)

    assert snapshot.workspace_id == "forte-public-office"
    assert snapshot.instruction_source == "user"
    assert snapshot.status == "completed"
    assert snapshot.contract.goal == snapshot.instruction
    assert planner.calls == 2
    assert planner.workspace and planner.workspace["control_loop"]["round_number"] == 2
    assert planner.files and all("path" not in item and "sha256" not in item for item in planner.files)
    assert snapshot.plan and snapshot.plan.units[-1].side_effect == "run_workspace_write"
    assert snapshot.model_receipt and snapshot.model_receipt.output_used
    assert snapshot.analysis_receipt and snapshot.analysis_receipt.output_used
    assert snapshot.result and snapshot.result.findings[0].file_refs == [REF_ONE]
    public = runtime.public_snapshot(snapshot)
    assert public.plan and REF_ONE not in public.plan.summary
    assert "2026 复核说明.txt" in public.plan.summary
    assert public.rounds[0].plan
    assert "2025 往来明细.csv" in str(public.rounds[0].plan["summary"])
    assert public.result and REF_ONE not in public.result.summary
    assert snapshot.brief and snapshot.brief.outcome == "completed"
    assert snapshot.budget.rounds_used == 2
    assert snapshot.budget.model_calls_used == 4
    assert len(snapshot.rounds) == 2
    assert snapshot.rounds[0].next_step
    assert snapshot.rounds[0].next_step.decision == "next_round"
    assert snapshot.rounds[0].evidence_gaps
    assert snapshot.rounds[1].next_step
    assert snapshot.rounds[1].next_step.decision == "completed"
    event_names = [event.event_name for event in snapshot.events]
    assert event_names.count("round_started") == 2
    assert event_names.count("evidence_gate") == 2
    assert event_names[-1] == "loop_committed"


@pytest.mark.asyncio
async def test_rejected_plan_is_repaired_once_within_the_same_budget() -> None:
    planner = RepairablePlanner()
    runtime = HarnessRuntime(FakeCatalog(), planner, FakeAnalyst())
    started = await runtime.start(
        "alice",
        start_request(
            idempotency_key="repair-plan-0001",
            selected_file_refs=[REF_ONE],
            loop={
                "max_rounds": 1,
                "max_files_per_round": 1,
                "max_model_calls": 3,
                "deadline_seconds": 120,
            },
        ),
    )

    snapshot = await wait_terminal(runtime, "alice", started.run.run_id)
    public = runtime.public_snapshot(snapshot)

    assert snapshot.status == "completed"
    assert planner.calls == 2
    assert snapshot.budget.model_calls_used == 3
    assert [event.event_name for event in snapshot.events].count(
        "plan_validation_rejected"
    ) == 1
    rejected = next(
        event
        for event in public.events
        if event.event_name == "plan_validation_rejected"
    )
    assert rejected.message == "候选计划未通过服务端校验，未采用；正在进行预算内的受控重试。"
    assert rejected.details.get("reason") == "本轮未通过服务端安全校验，且未发生外部动作。请重新运行。"
    assert "forte-0000000000000000" not in json.dumps(
        rejected.model_dump(mode="json"), ensure_ascii=False
    )


def test_start_requires_user_instruction_and_selected_files() -> None:
    with pytest.raises(ValidationError):
        HarnessRunStart(idempotency_key="missing-inputs")
    with pytest.raises(ValidationError):
        start_request(selected_file_refs=[])
    with pytest.raises(ValidationError):
        start_request(instruction="  ")
    with pytest.raises(ValidationError):
        start_request(selected_file_refs=[REF_ONE] * 2)


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["reference", "external", "model"])
async def test_invalid_model_plan_fails_closed(invalid: str) -> None:
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(invalid=invalid), FakeAnalyst())
    started = await runtime.start("alice", start_request(idempotency_key=f"invalid-{invalid}-0001"))
    snapshot = await wait_terminal(runtime, "alice", started.run.run_id)

    assert snapshot.status == "failed"
    assert snapshot.result is None
    assert snapshot.events[-1].event_name == "harness_failed"
    assert snapshot.events[-1].details["execution_started"] is False
    assert runtime.public_snapshot(snapshot).validation_errors


@pytest.mark.asyncio
async def test_invalid_result_citation_fails_closed() -> None:
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst(invalid_reference=True))
    started = await runtime.start("alice", start_request(idempotency_key="invalid-result-0001"))
    snapshot = await wait_terminal(runtime, "alice", started.run.run_id)

    assert snapshot.status == "failed"
    assert snapshot.result is None
    assert snapshot.analysis_receipt and not snapshot.analysis_receipt.output_used


@pytest.mark.asyncio
async def test_unknown_selected_file_fails_without_leaking_reference() -> None:
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner())
    started = await runtime.start(
        "alice",
        start_request(
            idempotency_key="unknown-file-0001",
            selected_file_refs=["forte-0000000000000000"],
        ),
    )
    snapshot = await wait_terminal(runtime, "alice", started.run.run_id)
    public = runtime.public_snapshot(snapshot).model_dump(mode="json")

    assert public["status"] == "failed"
    assert "0000000000000000" not in json.dumps(public, ensure_ascii=False)


@pytest.mark.asyncio
async def test_idempotent_start_replays_first_result_and_rejects_different_command() -> None:
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner())
    request = start_request(idempotency_key="same-command-0001")

    first = await runtime.start("alice", request)
    replay = await runtime.start("alice", request)

    assert replay.replayed is True
    assert replay.run.run_id == first.run.run_id
    with pytest.raises(HarnessConflictError):
        await runtime.start(
            "alice",
            request.model_copy(update={"instruction": "另一项办公任务"}),
        )


@pytest.mark.asyncio
async def test_owner_cannot_read_another_users_run() -> None:
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner())
    started = await runtime.start("alice", start_request(idempotency_key="owner-run-0001"))
    with pytest.raises(Exception, match="不存在"):
        await runtime.get("bob", started.run.run_id)


@pytest.mark.asyncio
async def test_loop_stops_at_budget_boundary_with_explicit_evidence_gap() -> None:
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst())
    started = await runtime.start(
        "alice",
        start_request(
            idempotency_key="budget-stop-0001",
            loop={
                "max_rounds": 1,
                "max_files_per_round": 4,
                "max_model_calls": 2,
                "deadline_seconds": 120,
            },
        ),
    )

    snapshot = await wait_terminal(runtime, "alice", started.run.run_id)

    assert snapshot.status == "stopped"
    assert snapshot.brief and snapshot.brief.outcome == "bounded"
    assert snapshot.brief.unresolved_gaps
    assert snapshot.rounds[0].next_step
    assert snapshot.rounds[0].next_step.decision == "budget_exhausted"
    assert snapshot.events[-1].event_name == "loop_budget_stopped"


@pytest.mark.asyncio
async def test_pause_steer_resume_applies_at_safe_points_and_replays_control() -> None:
    planner = BlockingPlanner()
    runtime = HarnessRuntime(FakeCatalog(), planner, FakeAnalyst())
    started = await runtime.start(
        "alice", start_request(idempotency_key="controlled-loop-0001")
    )
    await asyncio.wait_for(planner.started.wait(), timeout=1)
    current = await runtime.get("alice", started.run.run_id)

    pause_request = AgentControlLoopControlRequest(
        command="pause",
        idempotency_key="pause-control-0001",
        expected_version=current.version,
    )
    pause = await runtime.control("alice", started.run.run_id, pause_request)
    steer = await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="steer",
            idempotency_key="steer-control-0001",
            expected_version=pause.run.version,
            instruction="下一轮优先核对尚未被引用的复核说明",
        ),
    )
    assert steer.run.control_state == "pause_requested"
    planner.release.set()

    for _ in range(200):
        paused = await runtime.get("alice", started.run.run_id)
        if paused.status == "paused":
            break
        await asyncio.sleep(0)
    else:
        raise AssertionError("loop did not pause at a safe point")

    replay = await runtime.control("alice", started.run.run_id, pause_request)
    assert replay.replayed is True
    assert replay.run.control_state == "pause_requested"
    resumed = await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="resume",
            idempotency_key="resume-control-0001",
            expected_version=paused.version,
        ),
    )
    assert resumed.run.control_state == "running"
    terminal = await wait_terminal(runtime, "alice", started.run.run_id)

    assert terminal.status == "completed"
    assert terminal.rounds[1].steer_instruction == "下一轮优先核对尚未被引用的复核说明"
    assert any(
        event.event_name == "control_steer_applied" for event in terminal.events
    )
    pause_event = next(
        item for item in terminal.control_events if item.command == "pause"
    )
    assert pause_event.status == "applied"


@pytest.mark.asyncio
async def test_user_stop_preserves_partial_trace_and_no_external_action() -> None:
    planner = BlockingPlanner()
    runtime = HarnessRuntime(FakeCatalog(), planner, FakeAnalyst())
    started = await runtime.start(
        "alice", start_request(idempotency_key="stop-loop-0001")
    )
    await asyncio.wait_for(planner.started.wait(), timeout=1)
    current = await runtime.get("alice", started.run.run_id)
    await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="stop",
            idempotency_key="stop-control-0001",
            expected_version=current.version,
        ),
    )
    planner.release.set()

    terminal = await wait_terminal(runtime, "alice", started.run.run_id)

    assert terminal.status == "stopped"
    assert terminal.control_state == "stopped"
    assert terminal.brief and terminal.brief.outcome == "user_stopped"
    assert terminal.brief.external_action == "none"
    assert terminal.events[-1].event_name == "loop_stopped"


def test_public_workspace_and_file_projection_have_no_internal_metadata() -> None:
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner())
    workspace = runtime.get_workspace()
    preview = runtime.get_file_preview(REF_ONE)
    serialized = json.dumps({"workspace": workspace, "preview": preview}, ensure_ascii=False)

    assert workspace["file_count"] == 2
    assert "Finance-018/input" not in serialized
    assert "sha256" not in serialized
    with pytest.raises(Exception, match="不存在"):
        runtime.get_file_preview("forte-0000000000000000")


@pytest.mark.asyncio
async def test_http_contract_exposes_one_workspace_not_scenarios() -> None:
    app = create_app()
    app.state.harness_runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst())
    transport = httpx.ASGITransport(app=app)
    headers = {"X-User-Id": "alice"}
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        workspace = await client.get("/v1/harness/workspace", headers=headers)
        preview = await client.get(f"/v1/harness/workspace/files/{REF_ONE}", headers=headers)
        retired = await client.get("/v1/harness/scenarios", headers=headers)
        started = await client.post(
            "/v1/harness/runs",
            headers=headers,
            json=start_request(idempotency_key="route-start-0001").model_dump(),
        )

        assert workspace.status_code == 200 and workspace.json()["folder_count"] == 1
        assert preview.status_code == 200 and preview.json()["security"]["read_only"] is True
        assert retired.status_code == 404
        assert started.status_code == 202
        run_id = started.json()["run"]["run_id"]
        for _ in range(200):
            current = await client.get(f"/v1/harness/runs/{run_id}", headers=headers)
            if current.json()["status"] == "completed":
                break
            await asyncio.sleep(0)
        events = await client.get(f"/v1/harness/runs/{run_id}/events", headers=headers)

    assert current.json()["workspace_id"] == "forte-public-office"
    assert "event: loop_committed" in events.text
    assert "Finance-018/input" not in events.text
    openapi_paths = set(app.openapi()["paths"])
    assert "/v1/harness/workspace" in openapi_paths
    assert "/v1/harness/runs/{run_id}/controls" in openapi_paths
    assert not any("scenarios" in path for path in openapi_paths)


@pytest.mark.asyncio
async def test_http_control_route_pauses_replays_and_resumes_same_loop() -> None:
    planner = BlockingPlanner()
    runtime = HarnessRuntime(FakeCatalog(), planner, FakeAnalyst())
    app = create_app()
    app.state.harness_runtime = runtime
    transport = httpx.ASGITransport(app=app)
    headers = {"X-User-Id": "alice"}
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        started = await client.post(
            "/v1/harness/runs",
            headers=headers,
            json=start_request(idempotency_key="route-control-start-0001").model_dump(),
        )
        run_id = started.json()["run"]["run_id"]
        await asyncio.wait_for(planner.started.wait(), timeout=1)
        current = await client.get(f"/v1/harness/runs/{run_id}", headers=headers)
        pause_body = {
            "command": "pause",
            "idempotency_key": "route-pause-control-0001",
            "expected_version": current.json()["version"],
        }
        paused = await client.post(
            f"/v1/harness/runs/{run_id}/controls",
            headers=headers,
            json=pause_body,
        )
        replay = await client.post(
            f"/v1/harness/runs/{run_id}/controls",
            headers=headers,
            json=pause_body,
        )
        hidden = await client.post(
            f"/v1/harness/runs/{run_id}/controls",
            headers={"X-User-Id": "bob"},
            json=pause_body,
        )

        assert paused.status_code == 202
        assert paused.json()["run"]["control_state"] == "pause_requested"
        assert replay.status_code == 202 and replay.json()["replayed"] is True
        assert hidden.status_code == 404

        planner.release.set()
        for _ in range(200):
            current = await client.get(f"/v1/harness/runs/{run_id}", headers=headers)
            if current.json()["control_state"] == "paused":
                break
            await asyncio.sleep(0)
        assert current.json()["control_state"] == "paused"

        resumed = await client.post(
            f"/v1/harness/runs/{run_id}/controls",
            headers=headers,
            json={
                "command": "resume",
                "idempotency_key": "route-resume-control-0001",
                "expected_version": current.json()["version"],
            },
        )
        assert resumed.status_code == 202
        assert resumed.json()["run"]["control_state"] == "running"

    terminal = await wait_terminal(runtime, "alice", run_id)
    assert terminal.status == "completed"
    assert [item.command for item in terminal.control_events] == ["pause", "resume"]


@pytest.mark.asyncio
async def test_http_workspace_integrity_failure_is_503() -> None:
    app = create_app()
    app.state.harness_runtime = HarnessRuntime(FakeCatalog(broken=True), FakePlanner())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/harness/workspace")

    assert response.status_code == 503
    assert response.json()["detail"] == "办公资料库完整性校验失败"


def test_production_builder_uses_complete_workspace_catalog(monkeypatch) -> None:
    class Settings:
        llm_base_url = "https://example.invalid/v1"
        llm_api_key = "test-key"
        llm_model = "deepseek-v4-pro"
        llm_timeout_seconds = 10

    runtime = build_harness_runtime(Settings())
    workspace = runtime.get_workspace()

    assert workspace["workspace_id"] == "forte-public-office"
    assert workspace["folder_count"] == 15
    assert workspace["file_count"] == 96


def test_server_compiler_owns_artifact_write_effect() -> None:
    candidate = HarnessPlanCandidate(
        summary="形成结果",
        units=[
            HarnessPlanCandidateUnit(
                unit_id="u1",
                title="写入结果",
                objective="写入本轮工作区",
                input_file_refs=[REF_ONE],
                tool="artifact.write",
            )
        ],
    )

    plan = HarnessRuntime._compile_plan(candidate)

    assert plan.units == [
        HarnessPlanUnit(
            unit_id="u1",
            title="写入结果",
            objective="写入本轮工作区",
            input_file_refs=[REF_ONE],
            tool="artifact.write",
            side_effect="run_workspace_write",
            artifact_name="run-result-1",
            artifact_type="analysis",
        )
    ]
