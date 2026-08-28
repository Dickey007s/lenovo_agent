from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import threading
import zipfile
from pathlib import Path

import httpx
import pytest

from packages.contracts.harness_models import (
    AgentControlLoopArtifactCheck,
    AgentControlLoopFindingDecisionOption,
    AgentControlLoopFindingReview,
)
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
from services.api.app.api.harness_routes import stream_harness_events
from services.api.app.application.scenario_effects import (
    GeneratedOfficeArtifact,
    ScenarioEffectExecution,
    ScenarioEffectEngine,
    ScenarioEffectError,
)
from services.api.app.main import create_app


FORTE_ROOT = Path(__file__).resolve().parents[2] / "demo-enterprise-data" / "forte"
ONBOARDING_LABEL = "3月20日-4月20日入职时间表.csv"
ONBOARDING_INSTRUCTION = (
    "根据入职时间表和分配规则，生成 3 月 20 日至 4 月 20 日的入职资产匹配表。"
)
TC04_INSTRUCTION = (
    "为评测平台补充单元测试，覆盖 Service、执行引擎和工具类；"
    "真实运行测试，修复失败，并给出覆盖率与修改文件。"
)
TC12_INSTRUCTION = "为三个看板工具模块编写 Vitest，修复源码并真实运行测试。"
TC11_INSTRUCTION = "综合 PRD、上线配置、功能测试和兼容测试，给出上线结论与改进计划。"


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


class WaitingPlanner:
    model = "deepseek-v4-pro"

    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def plan(self, *, scenario, files):
        self.started.set()
        await self.release.wait()
        raise AssertionError("the close lifecycle test must cancel the pending plan")


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


class DashboardPlanner:
    model = "deepseek-v4-pro"

    async def plan(self, *, scenario, files):
        source = next(
            item
            for item in files
            if str(item["display_path"]).endswith(
                "dashboard-toolkit/src/utils/metricsCalculator.js"
            )
        )
        return HarnessPlanCandidate(
            summary="核对真实看板工具源码并形成隔离修复包",
            selection_reason="增长率源码可用于形成一条可定位的模型分析；确定性效果门另行冻结完整 11 文件项目。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="read-dashboard-source",
                    title="读取看板工具源码",
                    objective="核对增长率实现并为确定性修复提供分析上下文",
                    input_file_refs=[source["file_ref"]],
                    tool="file.read",
                )
            ],
        )


class DashboardAnalyst:
    model = "deepseek-v4-pro"

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        source = files[0]
        return HarnessTaskResult(
            summary="已定位增长率实现；真实测试、修复和覆盖率由服务端固定 TC-12 效果门执行。",
            findings=[
                HarnessFinding(
                    plan_unit_id=plan.units[0].unit_id,
                    title="增长率实现使用了报告期值作分母",
                    detail="固定测试将先复现该业务红灯，再在隔离副本中修复。",
                    file_refs=[source["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=source["file_ref"],
                            role="observed",
                            label="增长率原实现",
                            quote="return ((newValue - oldValue) / newValue) * 100",
                        )
                    ],
                )
            ],
            follow_ups=[],
            review_required=True,
        )


class ReleaseReadinessPlanner:
    model = "deepseek-v4-pro"

    async def plan(self, *, scenario, files):
        source = next(item for item in files if item["display_label"] == "PRD_v2.5.md")
        return HarnessPlanCandidate(
            summary="读取发布规则并形成可复核的上线判断",
            selection_reason="PRD 定义正式上线条件；固定 TC-11 效果门会另行冻结四份批准资料并逐项复算。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="read-release-rules",
                    title="读取 PRD 上线规则",
                    objective="核对功能全集、优先级和正式上线条件",
                    input_file_refs=[source["file_ref"]],
                    tool="file.read",
                )
            ],
        )


class ReleaseReadinessAnalyst:
    model = "deepseek-v4-pro"

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        source = files[0]
        return HarnessTaskResult(
            summary="已读取 PRD 上线规则；四份资料的交叉表校验、风险推导和 Gate 复算由服务端固定 TC-11 效果门完成。",
            findings=[
                HarnessFinding(
                    plan_unit_id=plan.units[0].unit_id,
                    title="本批次处于待上线审核状态",
                    detail="PRD 将当前文档状态标记为待上线审核，需要结合配置、功能测试和兼容测试复核。",
                    file_refs=[source["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=source["file_ref"],
                            role="observed",
                            label="PRD 文档状态",
                            quote="| 文档状态 | 待上线审核 |",
                        )
                    ],
                )
            ],
            follow_ups=[],
            review_required=True,
        )


class NoisyOnboardingPlanner:
    model = "deepseek-v4-pro"

    async def plan(self, *, scenario, files):
        schedule = next(
            item for item in files if item["display_label"] == ONBOARDING_LABEL
        )
        rules = next(
            item
            for item in files
            if item["display_label"] == "入职物资权限软件分配.pdf"
        )
        return HarnessPlanCandidate(
            summary="读取名单、规则并生成入职资产匹配表",
            selection_reason="名单与分配规则共同决定日期范围内的匹配结果。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="read-schedule",
                    title="读取入职时间表",
                    objective="筛选日期范围内的员工",
                    input_file_refs=[schedule["file_ref"]],
                    tool="table.inspect",
                ),
                HarnessPlanCandidateUnit(
                    unit_id="read-rules",
                    title="读取入职物资权限软件分配规则",
                    objective="核对岗位分类、优先级与备注覆盖规则",
                    input_file_refs=[rules["file_ref"]],
                    tool="file.read",
                ),
                HarnessPlanCandidateUnit(
                    unit_id="generate-assets",
                    title="生成入职资产匹配表",
                    objective="按时间表与规则形成可下载成果",
                    input_file_refs=[schedule["file_ref"], rules["file_ref"]],
                    depends_on=["read-schedule", "read-rules"],
                    tool="evidence.verify",
                ),
            ],
        )


class NoisyOnboardingAnalyst:
    model = "deepseek-v4-pro"

    def __init__(self) -> None:
        self.calls = 0

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        self.calls += 1
        schedule = next(item for item in files if item["display_label"] == ONBOARDING_LABEL)
        rules = next(
            item
            for item in files
            if item["display_label"] == "入职物资权限软件分配.pdf"
        )
        unit_ids = {unit.title: unit.unit_id for unit in plan.units}
        review = AgentControlLoopFindingReview(
            requires_human_decision=True,
            question="是否需要人工指定技术研发岗位的分类？",
            why_human="模型把已经明确的关键词优先级误判为需要用户选择。",
            options=[
                AgentControlLoopFindingDecisionOption(
                    option_id="A",
                    label="按规则归类",
                    meaning="使用文档中已经给出的关键词优先级。",
                    agent_next_step="保留当前匹配结果。",
                    next_instruction="按明确规则复核当前匹配结果。",
                ),
                AgentControlLoopFindingDecisionOption(
                    option_id="B",
                    label="另行指定",
                    meaning="由用户手工指定其他岗位分类。",
                    agent_next_step="形成另一份只读匹配建议。",
                    next_instruction="按用户指定分类形成另一份只读匹配建议。",
                ),
            ],
            recommended_option_id="A",
            recommendation_reason="规则已经明确给出分类优先级。",
            after_confirmation="只更新分析说明，不修改原文件。",
        )
        priority_quote = (
            '优先级说明：若岗位同时包含多个分类关键词（如"产品运营"、"市场研发"），'
            "以排列靠前的分类为准——技术研发 > 产品/视觉设计 > 运营/市场/职能。"
        )
        return HarnessTaskResult(
            summary="日期范围内的入职资产已匹配，另有范围外候选和多余人工门需要服务端处理。",
            findings=[
                HarnessFinding(
                    plan_unit_id=unit_ids["读取入职时间表"],
                    title="日期范围内共有九名待入职员工",
                    detail="3 月 20 日至 4 月 20 日的边界员工已保留。",
                    file_refs=[schedule["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=schedule["file_ref"],
                            role="observed",
                            label="日期上界记录",
                            quote=(
                                "林舒志 | 4月20日 (周一) | 技术研发 | "
                                "林某某 138xxxx0015 | 共享工位"
                            ),
                        )
                    ],
                ),
                HarnessFinding(
                    plan_unit_id=unit_ids["读取入职物资权限软件分配规则"],
                    title="技术研发按明确优先级归类",
                    detail="规则已经给出关键词和优先级，不需要用户再次决定。",
                    file_refs=[schedule["file_ref"], rules["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=schedule["file_ref"],
                            role="observed",
                            label="技术研发员工",
                            quote=(
                                "林舒志 | 4月20日 (周一) | 技术研发 | "
                                "林某某 138xxxx0015 | 共享工位"
                            ),
                        ),
                        HarnessEvidenceQuote(
                            file_ref=rules["file_ref"],
                            role="expected",
                            label="岗位分类优先级",
                            quote=priority_quote,
                        ),
                    ],
                    review=review,
                ),
                HarnessFinding(
                    plan_unit_id=unit_ids["生成入职资产匹配表"],
                    title="两条特殊备注均已生效",
                    detail="设计软件权限和共享工位分别覆盖默认值。",
                    file_refs=[schedule["file_ref"], rules["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=schedule["file_ref"],
                            role="observed",
                            label="多条备注员工",
                            quote=(
                                "冯子健 | 4月13日 (周一) | 设计 | "
                                "冯某某 138xxxx0018 | 不开通设计软件权限、共享工位"
                            ),
                        ),
                        HarnessEvidenceQuote(
                            file_ref=rules["file_ref"],
                            role="expected",
                            label="多条备注规则",
                            quote=(
                                '多条备注处理：若同一员工有多条备注（以顿号"、"分隔），'
                                "每条备注均须生效。"
                            ),
                        ),
                    ],
                ),
                HarnessFinding(
                    plan_unit_id=unit_ids["读取入职时间表"],
                    title="范围外岗位包含组合关键词",
                    detail="4 月 21 日和 4 月 23 日不属于当前任务范围。",
                    file_refs=[schedule["file_ref"], rules["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=schedule["file_ref"],
                            role="observed",
                            label="范围外产品运营员工",
                            quote=(
                                "姜映雪 | 4月21日 (周二) | 产品运营 | "
                                "姜某某 138xxxx0012"
                            ),
                        ),
                        HarnessEvidenceQuote(
                            file_ref=schedule["file_ref"],
                            role="observed",
                            label="范围外市场运营员工",
                            quote=(
                                "孟雨桐 | 4月23日 (周四) | 市场运营 | "
                                "孟某某 138xxxx0029"
                            ),
                        ),
                        HarnessEvidenceQuote(
                            file_ref=rules["file_ref"],
                            role="expected",
                            label="岗位分类优先级",
                            quote=priority_quote,
                        ),
                    ],
                ),
            ],
            follow_ups=[],
            review_required=True,
        )


class RejectedOnboardingAnalyst:
    model = "deepseek-v4-pro"

    async def analyze(self, **kwargs):
        raise HarnessModelError("invalid structured response", called=True, elapsed_ms=9)


class MainThreadCatalog:
    """Fails if a live catalog method leaks into the effect worker thread."""

    def __init__(self, catalog: BenchmarkWorkspaceCatalog) -> None:
        self.catalog = catalog
        self.owner_thread_id = threading.get_ident()

    def _assert_main_thread(self) -> None:
        assert threading.get_ident() == self.owner_thread_id

    def internal_workspace(self):
        self._assert_main_thread()
        return self.catalog.internal_workspace()

    def public_workspace(self):
        self._assert_main_thread()
        return self.catalog.public_workspace()

    def public_file(self, file_ref: str):
        self._assert_main_thread()
        return self.catalog.public_file(file_ref)

    def checked_input_bytes(self, file_ref: str):
        self._assert_main_thread()
        return self.catalog.checked_input_bytes(file_ref)

    def checked_input_bytes_many(self, file_refs):
        self._assert_main_thread()
        return self.catalog.checked_input_bytes_many(file_refs)


class BlockingScenarioEffectEngine(ScenarioEffectEngine):
    def __init__(self, owner_thread_id: int) -> None:
        self.owner_thread_id = owner_thread_id
        self.started = threading.Event()
        self.release = threading.Event()
        self.execute_calls = 0
        self.worker_thread_id: int | None = None

    def execute(self, instruction, catalog):
        self.execute_calls += 1
        self.worker_thread_id = threading.get_ident()
        assert self.worker_thread_id != self.owner_thread_id
        self.started.set()
        if not self.release.wait(timeout=5):
            raise ScenarioEffectError("controlled blocking probe timed out")
        spec = self.match(instruction)
        assert spec is not None and spec.scenario_id == "TC-04"
        source_refs = tuple(catalog.input_bytes)
        check = AgentControlLoopArtifactCheck(
            check_id="check-tc04-responsive-probe",
            label="受控 TC-04 工作线程只生成一次成果",
            passed=True,
            detail="该探针只验证调度、响应性与去重，不替代真实 117 项效果门。",
        )
        artifact = GeneratedOfficeArtifact(
            title="TC-04 受控响应探针",
            file_name="tc04-responsive-probe.md",
            media_type="text/markdown",
            content=b"tc04 responsive probe\n",
            source_file_refs=source_refs,
            validator_id="validator-tc04-responsive-probe-v1",
            checks=(check,),
            summary="受控阻塞释放后只写入一次测试成果。",
        )
        return ScenarioEffectExecution(
            scenario_id=spec.scenario_id,
            capability_id=spec.capability_id,
            status="passed",
            state="frozen_tc04_probe",
            action="run_in_worker_thread",
            observation="health、Run GET 与 SSE 在阻塞期间仍可响应",
            cost="一次受控工作线程",
            result="只生成一次探针成果",
            source_file_refs=source_refs,
            artifacts=(artifact,),
            prohibited_side_effects=spec.prohibited_side_effects,
        )


class FailingScenarioEffectEngine(ScenarioEffectEngine):
    def execute(self, instruction, catalog):
        raise ScenarioEffectError("controlled effect failure")


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
    try:
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
            await runtime.get_workspace_artifact(
                "bob", snapshot.run_id, record.artifact_id
            )

        event_names = [item.event_name for item in snapshot.events]
        assert "deterministic_office_tool_started" in event_names
        assert "run_workspace_artifact_written" in event_names
        assert "deterministic_verification_completed" in event_names

        app = create_app()
        app.state.harness_runtime = runtime
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
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
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_tc11_runtime_persists_verified_files_and_failed_business_gates(
    tmp_path: Path,
) -> None:
    before = _forte_digests()
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        ReleaseReadinessPlanner(),
        ReleaseReadinessAnalyst(),
        effect_engine=ScenarioEffectEngine(),
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    try:
        started = await runtime.start(
            "release-owner",
            HarnessRunStart(
                idempotency_key="tc11-derived-release-runtime-0001",
                instruction=TC11_INSTRUCTION,
            ),
        )
        snapshot = None
        for _ in range(1_000):
            candidate = await runtime.get(
                "release-owner", started.run.run_id
            )
            if candidate.status in {"waiting_input", "completed", "stopped", "failed"}:
                snapshot = candidate
                break
            await asyncio.sleep(0.01)
        assert snapshot is not None

        assert snapshot.status == "completed"
        assert len(snapshot.workspace_artifacts) == 2
        assert snapshot.effect_receipts[0].status == "passed"
        outcome = snapshot.effect_receipts[0].business_gate_outcome
        assert outcome is not None
        assert outcome.status == "failed"
        assert outcome.decision == "不得上线"
        assert outcome.failed_gate_count == outcome.total_gate_count == 4
        assert [gate.actual for gate in outcome.gates] == [71.4, 80.0, 40.0, 4.0]
        assert len(outcome.records) == 18
        assert sum(item.final_risk_level == "severe" for item in outcome.records) == 4
        assert sum(item.final_risk_level == "major" for item in outcome.records) == 2
        assert sum(item.final_risk_level == "minor" for item in outcome.records) == 2
        assert all(
            item.business_gate_outcome == outcome
            for item in snapshot.workspace_artifacts
        )
        assert all(
            item.verifier_status == "passed"
            for item in snapshot.workspace_artifacts
        )
        assert all(
            check.passed
            for item in snapshot.workspace_artifacts
            for check in item.checks
        )

        by_name = {item.file_name: item for item in snapshot.workspace_artifacts}
        _, report = await runtime.get_workspace_artifact(
            "release-owner",
            snapshot.run_id,
            by_name["上线合规与风险报告.docx"].artifact_id,
        )
        with zipfile.ZipFile(io.BytesIO(report)) as package:
            document = package.read("word/document.xml").decode("utf-8")
        assert document.count("<w:tbl>") >= 6
        assert "上线结论：不得上线" in document

        _, ledger = await runtime.get_workspace_artifact(
            "release-owner",
            snapshot.run_id,
            by_name["上线功能风险逐项台账.csv"].artifact_id,
        )
        ledger_rows = list(csv.DictReader(io.StringIO(ledger.decode("utf-8-sig"))))
        assert len(ledger_rows) == 18
        assert sum(item["最终等级"] == "严重" for item in ledger_rows) == 4
        assert _forte_digests() == before

        public = runtime.public_snapshot(snapshot).model_dump(mode="json")
        public_outcome = public["effect_receipts"][0]["business_gate_outcome"]
        assert public_outcome["decision"] == "不得上线"
        assert len(public_outcome["records"]) == 18
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_runtime_close_cancels_and_awaits_pending_run_task() -> None:
    planner = WaitingPlanner()
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        planner,
        OnboardingAnalyst(),
    )
    closed = False
    try:
        started = await runtime.start(
            "alice",
            HarnessRunStart(
                idempotency_key="runtime-close-pending-task-0001",
                instruction=ONBOARDING_INSTRUCTION,
            ),
        )
        await asyncio.wait_for(planner.started.wait(), timeout=1)
        run_task = runtime._tasks[started.run.run_id]
        assert run_task.get_coro().__qualname__ == "HarnessRuntime._run"
        assert not run_task.done()

        await runtime.close()
        closed = True
        await asyncio.sleep(0)

        assert run_task.done()
        assert run_task.cancelled()
        assert started.run.run_id not in runtime._tasks
    finally:
        planner.release.set()
        if not closed:
            await runtime.close()


@pytest.mark.asyncio
async def test_blocking_effect_keeps_health_run_get_and_sse_responsive(
    tmp_path: Path,
) -> None:
    catalog = MainThreadCatalog(BenchmarkWorkspaceCatalog(FORTE_ROOT))
    engine = BlockingScenarioEffectEngine(catalog.owner_thread_id)
    runtime = HarnessRuntime(
        catalog,
        OnboardingPlanner(),
        OnboardingAnalyst(),
        effect_engine=engine,
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    app = create_app()
    app.state.harness_runtime = runtime
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/harness/runs",
                headers={"X-User-Id": "alice"},
                json={
                    "idempotency_key": "scenario-effect-responsive-0001",
                    "instruction": TC04_INSTRUCTION,
                },
            )
            assert response.status_code == 202
            run_id = response.json()["run"]["run_id"]

            for _ in range(200):
                if engine.started.is_set():
                    break
                await asyncio.sleep(0.01)
            assert engine.started.is_set()

            health = await asyncio.wait_for(client.get("/v1/health"), timeout=1)
            current = await asyncio.wait_for(
                client.get(
                    f"/v1/harness/runs/{run_id}",
                    headers={"X-User-Id": "alice"},
                ),
                timeout=1,
            )
            assert health.status_code == 200
            assert current.status_code == 200
            snapshot = await runtime.get("alice", run_id)
            start_events = [
                event
                for event in snapshot.events
                if event.event_name == "deterministic_office_tool_started"
            ]
            assert len(start_events) == 1
            assert start_events[0].details["scenario_id"] == "TC-04"
            assert start_events[0].details["frozen_source_file_count"] == 46
            assert start_events[0].details["progress_percent"] is None
            assert not snapshot.workspace_artifacts

            stream = await stream_harness_events(
                run_id=run_id,
                owner_id="alice",
                runtime=runtime,
                after=start_events[0].sequence - 1,
            )
            chunk = await asyncio.wait_for(anext(stream.body_iterator), timeout=1)
            if isinstance(chunk, bytes):
                chunk = chunk.decode("utf-8")
            assert "event: deterministic_office_tool_started" in chunk
            await stream.body_iterator.aclose()

            await asyncio.wait_for(
                runtime._apply_scenario_effect("alice", run_id, round_number=1),
                timeout=1,
            )
            assert engine.execute_calls == 1

            engine.release.set()
            settled = await _wait_for_settled(runtime, "alice", run_id)
            assert settled.effect_receipts[0].status == "passed"
            assert settled.effect_receipts[0].scenario_id == "TC-04"
            assert len(settled.workspace_artifacts) == 1
            assert len(
                [
                    event
                    for event in settled.events
                    if event.event_name == "deterministic_office_tool_started"
                ]
            ) == 1
            assert engine.execute_calls == 1
    finally:
        engine.release.set()
        await runtime.close()


@pytest.mark.asyncio
async def test_effect_failure_emits_ordered_failure_fact_without_artifact(
    tmp_path: Path,
) -> None:
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        OnboardingPlanner(),
        OnboardingAnalyst(),
        effect_engine=FailingScenarioEffectEngine(),
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    try:
        started = await runtime.start(
            "alice",
            HarnessRunStart(
                idempotency_key="scenario-effect-failure-event-0001",
                instruction=ONBOARDING_INSTRUCTION,
            ),
        )
        settled = await _wait_for_settled(runtime, "alice", started.run.run_id)

        assert settled.status == "failed"
        assert not settled.workspace_artifacts
        assert not settled.effect_receipts
        names = [event.event_name for event in settled.events]
        assert names.index("deterministic_office_tool_started") < names.index(
            "scenario_effect_failed"
        )
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_tc01_verified_artifact_is_not_blocked_by_pdf_layout_or_scope_noise(
    tmp_path: Path,
) -> None:
    analyst = NoisyOnboardingAnalyst()
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        NoisyOnboardingPlanner(),
        analyst,
        effect_engine=ScenarioEffectEngine(),
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    try:
        started = await runtime.start(
            "alice",
            HarnessRunStart(
                idempotency_key="tc01-layout-scope-regression-0001",
                instruction=ONBOARDING_INSTRUCTION,
            ),
        )
        snapshot = await _wait_for_settled(runtime, "alice", started.run.run_id)

        assert snapshot.status == "completed"
        assert analyst.calls == 1
        assert len(snapshot.workspace_artifacts) == 1
        assert snapshot.workspace_artifacts[0].verifier_status == "passed"
        assert len(snapshot.workspace_artifacts[0].checks) == 5
        assert all(check.passed for check in snapshot.workspace_artifacts[0].checks)
        assert snapshot.effect_receipts[0].status == "passed"
        assert all(branch.status == "completed" for branch in snapshot.branches)
        assert all(not round_item.evidence_gaps for round_item in snapshot.rounds)
        assert not snapshot.decision_requests
        assert snapshot.result is not None
        assert len(snapshot.result.findings) == 3
        assert all(
            "范围外" not in finding.title for finding in snapshot.result.findings
        )
        assert all(finding.review is None for finding in snapshot.result.findings)
        event_names = [event.event_name for event in snapshot.events]
        assert "analysis_scope_filtered" in event_names
        assert "decision_gate_suppressed" in event_names
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_verified_artifact_survives_rejected_analyst_output(tmp_path: Path) -> None:
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        OnboardingPlanner(),
        RejectedOnboardingAnalyst(),
        effect_engine=ScenarioEffectEngine(),
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    try:
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
    finally:
        await runtime.close()


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
