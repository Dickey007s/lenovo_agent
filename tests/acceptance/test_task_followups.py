"""Follow-up work keeps server Task identity, not just a visual grouping."""

import httpx
import pytest
from pydantic import ValidationError

from services.api.app.api.harness_routes import get_harness_runtime
from services.api.app.application.harness_runtime import HarnessContinuationRequest, HarnessRunStart, HarnessRuntime
from services.api.app.main import create_app
from tests.unit.test_harness_runtime import FakeCatalog, FakePlanner, FakeAnalyst
from tests.acceptance.test_demo1_demo2_fixed_scenarios import _wait_for


@pytest.mark.parametrize("extra", [
    {}, {"purpose": "follow_up"},
    {"purpose": "follow_up", "instruction": "   "},
    {"purpose": "follow_up", "instruction": "整理表格", "branch_id": "branch-111111111111"},
])
def test_continuation_requires_unambiguous_target(extra):
    with pytest.raises(ValidationError):
        HarnessContinuationRequest(idempotency_key="followup-validation", expected_version=1, expected_task_version=1, **extra)


@pytest.mark.asyncio
async def test_followup_http_retains_task_history_replays_and_rejects_stale_or_foreign_parent():
    planner = FakePlanner()
    runtime = HarnessRuntime(FakeCatalog(), planner, FakeAnalyst())
    app = create_app()
    app.dependency_overrides[get_harness_runtime] = lambda: runtime
    try:
        start = await runtime.start("owner", HarnessRunStart(
            instruction="核对表格账目", output_preference="analysis_only", idempotency_key="followup-parent",
            loop={"max_rounds": 1, "max_files_per_round": 1, "max_model_calls": 4, "deadline_seconds": 120}))
        parent = await _wait_for(runtime, "owner", start.run.run_id, lambda r: r.status in {"completed", "stopped", "failed"})
        assert parent.status == "completed"
        before = parent.model_dump(mode="json")
        body = dict(purpose="follow_up", instruction="把当前账目整理成待核对清单", expected_version=parent.version,
                    expected_task_version=parent.task_version, idempotency_key="followup-child")
        url = f"/v1/harness/runs/{parent.run_id}/continue"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers={"X-User-Id": "owner"}) as client:
            assert (await client.post(url, json=body, headers={"X-User-Id": "someone-else"})).status_code == 404
            response = await client.post(url, json=body)
            assert response.status_code == 202, response.text
            child = response.json()["run"]
            assert child["task_id"] == parent.task_id
            assert child["run_id"] != parent.run_id
            assert child["parent_run_id"] == parent.run_id
            assert child["run_sequence"] == 2
            assert child["contract"]["output_policy"] == "analysis_only"
            assert child["carried_branch_id"] is None
            assert child["recheck_file_refs"] == []  # New goal is planned again, not fabricated evidence inheritance.
            assert child["base_artifact_version"] == 1
            repeated = await client.post(url, json=body)
            assert repeated.status_code == 202
            assert repeated.json()["replayed"]
            assert repeated.json()["run"]["run_id"] == child["run_id"]
            assert (await client.post(url, json={**body, "instruction": "换一个任务要求"})).status_code == 409
            assert (await client.post(url, json={**body, "idempotency_key": "other-followup"})).status_code == 409
            task = (await client.get(f"/v1/harness/tasks/{parent.task_id}")).json()
            assert task["goal"] == parent.instruction
            assert task["current_run_id"] == child["run_id"]
            assert len(task["lineage"]) == 2
            assert task["lineage"][1]["instruction"] == body["instruction"]
            done = await _wait_for(runtime, "owner", child["run_id"], lambda r: r.status in {"completed", "stopped", "failed"})
            assert done.status == "completed"
            assert parent.instruction in done.rounds[0].question
            assert body["instruction"] in done.rounds[0].question
            assert "不是已验证的证据" in done.rounds[0].question
            public = (await client.get(f"/v1/harness/runs/{done.run_id}")).json()
            assert public["rounds"][0]["question"] == body["instruction"]
            assert "original_goal" not in str(public)
            assert "previous_request" not in str(public)
            assert "以下 JSON 仅作任务背景" not in str(public)
            assert "核对表格账目" in str(planner.workspace)
        assert (await runtime.get("owner", parent.run_id)).model_dump(mode="json") == before
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_active_run_cannot_be_forked_by_followup():
    from tests.unit.test_harness_runtime import BlockingAnalyst
    analyst = BlockingAnalyst()
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), analyst)
    app = create_app()
    app.dependency_overrides[get_harness_runtime] = lambda: runtime
    try:
        started = await runtime.start("owner", HarnessRunStart(instruction="先核对表格", idempotency_key="active-parent"))
        await analyst.started.wait()
        parent = await runtime.get("owner", started.run.run_id)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"/v1/harness/runs/{parent.run_id}/continue", headers={"X-User-Id": "owner"}, json={
                "purpose": "follow_up", "instruction": "再整理清单", "expected_version": parent.version,
                "expected_task_version": parent.task_version, "idempotency_key": "active-child"})
            assert response.status_code == 409
        assert (await runtime.get_task("owner", parent.task_id)).run_sequence == 1
    finally:
        analyst.release.set()
        await runtime.close()
