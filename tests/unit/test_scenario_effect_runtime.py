from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import httpx
import pytest

from services.api.app.application.benchmark_workspace_catalog import (
    BenchmarkWorkspaceCatalog,
)
from services.api.app.application.harness_runtime import (
    HarnessEvidenceQuote,
    HarnessFinding,
    HarnessModelError,
    HarnessPlanCandidate,
    HarnessPlanCandidateUnit,
    HarnessPlanError,
    HarnessRunStart,
    HarnessRuntime,
    HarnessTaskResult,
)
from services.api.app.application.run_workspace_artifact_store import (
    RunWorkspaceArtifactStore,
)
from services.api.app.application.scenario_effects import ScenarioEffectEngine
from services.api.app.main import create_app


FORTE_ROOT = Path(__file__).resolve().parents[2] / "demo-enterprise-data" / "forte"
ONBOARDING_LABEL = "3月20日-4月20日入职时间表.csv"
ONBOARDING_INSTRUCTION = (
    "根据入职时间表和分配规则，生成 3 月 20 日至 4 月 20 日的入职资产匹配表。"
)


class OnboardingPlanner:
    model = "deepseek-v4-pro"

    async def plan(self, *, scenario, files):
        selected = next(item for item in files if item["display_label"] == ONBOARDING_LABEL)
        return HarnessPlanCandidate(
            summary="读取入职名单并形成可复核结果",
            selection_reason="入职时间表直接承载日期、岗位和备注事实。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="onboarding-input",
                    title="核对入职名单",
                    objective="核对日期范围内的入职员工",
                    input_file_refs=[selected["file_ref"]],
                    tool="table.inspect",
                )
            ],
        )


class OnboardingAnalyst:
    model = "deepseek-v4-pro"

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        source = files[0]
        assert source["display_label"] == ONBOARDING_LABEL
        return HarnessTaskResult(
            summary="入职时间表已只读核对，确定性工具将生成资产匹配表。",
            findings=[
                HarnessFinding(
                    plan_unit_id=plan.units[0].unit_id,
                    title="日期范围内存在待入职员工",
                    detail="时间表包含需要进行资产匹配的入职记录。",
                    file_refs=[source["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=source["file_ref"],
                            role="observed",
                            label="一条可唯一定位的入职记录",
                            quote="王子涵 | 3月23日 (周一) | 设计",
                        )
                    ],
                )
            ],
            follow_ups=[],
            review_required=True,
        )


class RejectedOnboardingAnalyst:
    model = "deepseek-v4-pro"

    async def analyze(self, **kwargs):
        raise HarnessModelError("invalid structured response", called=True, elapsed_ms=9)


def _forte_digests() -> dict[str, str]:
    return {
        item.relative_to(FORTE_ROOT).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in FORTE_ROOT.rglob("*")
        if item.is_file()
    }


async def _wait_for_effect(runtime: HarnessRuntime, owner: str, run_id: str):
    for _ in range(500):
        snapshot = await runtime.get(owner, run_id)
        if snapshot.effect_receipts:
            return snapshot
        await asyncio.sleep(0)
    raise AssertionError("scenario effect was not recorded")


async def _wait_for_settled(runtime: HarnessRuntime, owner: str, run_id: str):
    for _ in range(1_000):
        snapshot = await runtime.get(owner, run_id)
        if snapshot.status in {"waiting_input", "completed", "stopped", "failed"}:
            return snapshot
        await asyncio.sleep(0)
    raise AssertionError("run did not settle")


@pytest.mark.asyncio
async def test_runtime_writes_downloadable_verified_artifact_without_touching_forte(
    tmp_path: Path,
) -> None:
    before = _forte_digests()
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        OnboardingPlanner(),
        OnboardingAnalyst(),
        effect_engine=ScenarioEffectEngine(),
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    started = await runtime.start(
        "alice",
        HarnessRunStart(
            idempotency_key="scenario-effect-runtime-onboarding-0001",
            instruction=ONBOARDING_INSTRUCTION,
        ),
    )
    snapshot = await _wait_for_effect(runtime, "alice", started.run.run_id)

    assert snapshot.effect_receipts[0].status == "passed"
    assert snapshot.effect_receipts[0].scenario_id == "TC-01"
    assert len(snapshot.workspace_artifacts) == 1
    record = snapshot.workspace_artifacts[0]
    assert record.file_name == "入职资产匹配表.csv"
    assert record.verifier_status == "passed"
    assert all(check.passed for check in record.checks)
    assert record.original_inputs_modified is False
    assert record.external_action == "none"
    assert _forte_digests() == before

    public = runtime.public_snapshot(snapshot)
    serialized = public.model_dump_json()
    assert "content_sha256" not in serialized
    assert record.content_sha256 not in serialized
    assert public.workspace_artifacts[0].download_path.endswith(record.artifact_id)

    metadata, content = await runtime.get_workspace_artifact(
        "alice", snapshot.run_id, record.artifact_id
    )
    assert metadata.file_name == "入职资产匹配表.csv"
    assert content.startswith(b"\xef\xbb\xbf")
    assert "紧急联系人" not in content.decode("utf-8-sig")
    with pytest.raises(Exception):
        await runtime.get_workspace_artifact("bob", snapshot.run_id, record.artifact_id)

    event_names = [item.event_name for item in snapshot.events]
    assert "deterministic_office_tool_started" in event_names
    assert "run_workspace_artifact_written" in event_names
    assert "deterministic_verification_completed" in event_names

    app = create_app()
    app.state.harness_runtime = runtime
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            record.download_path,
            headers={"X-User-Id": "alice"},
        )
        denied = await client.get(
            record.download_path,
            headers={"X-User-Id": "bob"},
        )
    assert response.status_code == 200
    assert response.content == content
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert denied.status_code == 404
    json.dumps(public.model_dump(mode="json"), ensure_ascii=False)


@pytest.mark.asyncio
async def test_verified_artifact_survives_rejected_analyst_output(tmp_path: Path) -> None:
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        OnboardingPlanner(),
        RejectedOnboardingAnalyst(),
        effect_engine=ScenarioEffectEngine(),
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    started = await runtime.start(
        "alice",
        HarnessRunStart(
            idempotency_key="scenario-effect-runtime-rejected-analysis-0001",
            instruction=ONBOARDING_INSTRUCTION,
        ),
    )
    snapshot = await _wait_for_settled(runtime, "alice", started.run.run_id)

    assert snapshot.analysis_receipt is not None
    assert snapshot.analysis_receipt.called is True
    assert snapshot.analysis_receipt.output_used is False
    assert snapshot.effect_receipts[0].status == "passed"
    assert snapshot.workspace_artifacts[0].verifier_status == "passed"
    assert snapshot.workspace_artifacts[0].original_inputs_modified is False
    assert [item.event_name for item in snapshot.events].index(
        "deterministic_verification_completed"
    ) < [item.event_name for item in snapshot.events].index(
        "analysis_structure_rejected"
    )


def test_scope_validator_rebinds_only_a_uniquely_implied_plan_unit() -> None:
    workspace = BenchmarkWorkspaceCatalog(FORTE_ROOT).public_workspace()
    files = [item for folder in workspace["folders"] for item in folder["files"]]
    schedule_ref = next(
        item["file_ref"] for item in files if item["display_label"] == ONBOARDING_LABEL
    )
    rules_ref = next(
        item["file_ref"]
        for item in files
        if item["display_label"] == "入职物资权限软件分配.pdf"
    )
    plan = HarnessRuntime._compile_plan(
        HarnessPlanCandidate(
            summary="核对入职资料",
            selection_reason="两份资料共同决定匹配结果。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="read-schedule",
                    title="读取名单",
                    objective="读取名单",
                    input_file_refs=[schedule_ref],
                    tool="table.inspect",
                ),
                HarnessPlanCandidateUnit(
                    unit_id="read-rules",
                    title="读取规则",
                    objective="读取规则",
                    input_file_refs=[rules_ref],
                    tool="file.read",
                ),
                HarnessPlanCandidateUnit(
                    unit_id="compare",
                    title="交叉匹配",
                    objective="交叉匹配",
                    input_file_refs=[schedule_ref, rules_ref],
                    tool="evidence.verify",
                ),
            ],
        )
    )
    finding = HarnessFinding(
        plan_unit_id="read-schedule",
        title="需要联合核对",
        detail="结论同时使用名单和规则。",
        file_refs=[schedule_ref, rules_ref],
        evidence_quotes=[
            HarnessEvidenceQuote(
                file_ref=schedule_ref,
                role="observed",
                label="名单",
                quote="王子涵 | 3月23日 (周一) | 设计",
            )
        ],
    )
    result = HarnessTaskResult(
        summary="联合核对",
        findings=[finding],
        follow_ups=[],
        review_required=True,
    )

    normalized = HarnessRuntime._validate_candidate_result_scope(
        result,
        [{"file_ref": schedule_ref}, {"file_ref": rules_ref}],
        plan,
    )
    assert normalized.findings[0].plan_unit_id == "compare"

    ambiguous = result.model_copy(
        update={
            "findings": [
                finding.model_copy(
                    update={"plan_unit_id": None, "file_refs": [schedule_ref]}
                )
            ]
        }
    )
    with pytest.raises(HarnessPlanError, match="共享资料"):
        HarnessRuntime._validate_candidate_result_scope(
            ambiguous,
            [{"file_ref": schedule_ref}, {"file_ref": rules_ref}],
            plan,
        )
