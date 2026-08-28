from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from packages.contracts.harness_models import (
    AgentControlLoopControlRequest,
    AgentControlLoopFindingDecisionOption,
    AgentControlLoopFindingReview,
    AgentControlLoopOptions,
)

from services.api.app.application.harness_runtime import (
    HarnessConflictError,
    HarnessEvidenceQuote,
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
from services.api.app.application.harness_storage import (
    InMemoryHarnessStateStore,
    StoredHarnessArtifactVersion,
    StoredHarnessIdempotency,
    StoredHarnessRun,
)
from services.api.app.main import create_app


REF_ONE = "forte-1111111111111111"
REF_TWO = "forte-2222222222222222"
REF_THREE = "forte-3333333333333333"


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
            "data_boundary": "只读整个公开资料库；每轮由 Agent 自主检索相关文件",
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
                "columns": ["客商", "余额"] if file_ref == REF_ONE else [],
                "rows": [{"row_number": 2, "values": ["A", "100"]}] if file_ref == REF_ONE else [],
                "text": None if file_ref == REF_ONE else "复核说明" if file_ref == REF_TWO else "无关法务说明",
            }
            for file_ref in file_refs
        ]


class FakeCatalogWithDistractor(FakeCatalog):
    def __init__(self) -> None:
        super().__init__()
        self.files.append(
            {
                "file_ref": REF_THREE,
                "folder_id": "forte-folder-333333333333",
                "path": "Legal-003/input/unrelated.txt",
                "role": "input",
                "mime": "text/plain",
                "size": 12,
                "sha256": "c" * 64,
                "display_label": "无关法务说明.txt",
                "display_group": "法务",
                "display_path": "法务/无关法务说明.txt",
                "display_summary": "文本文件 · 12 B",
            }
        )


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
        max_files = scenario.get("control_loop", {}).get("max_files_this_round", len(files))
        selected = files[:max_files]
        first_ref = "forte-0000000000000000" if self.invalid == "reference" else selected[0]["file_ref"]
        second_tool = "action.preview" if self.invalid == "external" else "artifact.write"
        return HarnessPlanCandidate(
            summary=f"围绕 {files[0]['file_ref']} 的动态计划 {self.calls}",
            selection_reason="根据任务中的跨期余额关键词选择最相关的文件。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="u1",
                    title="读取资料",
                    objective="读取 Agent 自主选择的相关文件",
                    input_file_refs=[first_ref],
                    tool="file.read",
                ),
                HarnessPlanCandidateUnit(
                    unit_id="u2",
                    title="形成结果",
                    objective="形成可引用的初步分析",
                    input_file_refs=[selected[-1]["file_ref"]],
                    depends_on=["u1"],
                    tool=second_tool,
                    artifact_name="analysis-result" if second_tool == "artifact.write" else None,
                    artifact_type="analysis" if second_tool == "artifact.write" else None,
                ),
            ],
        )


class MultiBranchPlanner(FakePlanner):
    def __init__(self) -> None:
        super().__init__()
        self.file_ref_history: list[list[str]] = []

    async def plan(self, *, scenario, files):
        self.calls += 1
        self.workspace = scenario
        self.files = files
        refs = [str(item["file_ref"]) for item in files]
        self.file_ref_history.append(refs)
        if self.calls == 1:
            return HarnessPlanCandidate(
                summary="把跨期资料拆成三个可独立核对的分支",
                selection_reason="三个文件分别承载独立证据。",
                units=[
                    HarnessPlanCandidateUnit(
                        unit_id="base",
                        title="核对基础明细",
                        objective="核对第一份基础资料",
                        input_file_refs=[refs[0]],
                        tool="file.read",
                    ),
                    HarnessPlanCandidateUnit(
                        unit_id="review",
                        title="核对复核说明",
                        objective="核对第二份复核资料",
                        input_file_refs=[refs[1]],
                        depends_on=["base"],
                        tool="evidence.verify",
                    ),
                    HarnessPlanCandidateUnit(
                        unit_id="legal",
                        title="核对法务说明",
                        objective="核对第三份法务资料",
                        input_file_refs=[refs[2]],
                        depends_on=["base"],
                        tool="artifact.write",
                        artifact_name="branch-result",
                        artifact_type="evidence",
                    ),
                ],
            )
        return HarnessPlanCandidate(
            summary="只继续用户确认的证据分支",
            selection_reason="服务端已把本轮范围限制为所选分支的缺口。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id=f"recheck-{self.calls}",
                    title="继续核对所选分支",
                    objective="补齐所选分支缺少的引用",
                    input_file_refs=[refs[0]],
                    tool="evidence.verify",
                )
            ],
        )


class FiveBranchPlanner(FakePlanner):
    """Five independent units intentionally share one of two source files."""

    async def plan(self, *, scenario, files):
        self.calls += 1
        self.workspace = scenario
        self.files = files
        available = {str(item["file_ref"]) for item in files}
        if available == {REF_TWO}:
            units = [
                HarnessPlanCandidateUnit(
                    unit_id="u5",
                    title="核对复核说明",
                    objective="定位复核说明中的关键记录",
                    input_file_refs=[REF_TWO],
                    tool="evidence.verify",
                )
            ]
        else:
            units = [
                HarnessPlanCandidateUnit(
                    unit_id=f"u{index}",
                    title=f"核对事实 {index}",
                    objective="核对一条可追溯办公事实",
                    input_file_refs=[REF_ONE],
                    tool="file.read",
                )
                for index in range(1, 5)
            ] + [
                HarnessPlanCandidateUnit(
                    unit_id="u5",
                    title="核对复核说明",
                    objective="定位复核说明中的关键记录",
                    input_file_refs=[REF_TWO],
                    tool="evidence.verify",
                )
            ]
        return HarnessPlanCandidate(
            summary="把资料库核对拆成五个独立证据分支",
            selection_reason="每个事实由一个独立计划单元负责，便于局部恢复。",
            units=units,
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

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        self.instruction = instruction
        file_ref = "forte-0000000000000000" if self.invalid_reference else files[0]["file_ref"]
        plan_unit_id = plan.units[0].unit_id if plan.units else "u1"
        return HarnessTaskResult(
            summary=f"{file_ref} 只读核查完成",
            findings=[
                HarnessFinding(
                    plan_unit_id=plan_unit_id,
                    title="发现一项待复核事实",
                    detail="该结论来自 Agent 自主选择的公开文件。",
                    file_refs=[file_ref],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=file_ref,
                            role="support",
                            label="本轮直接依据",
                            quote="A | 100" if file_ref == REF_ONE else "复核说明" if file_ref == REF_TWO else "无关法务说明",
                        )
                    ],
                )
            ],
            follow_ups=["请人工复核业务口径"],
            review_required=True,
        )


class BlockingAnalyst(FakeAnalyst):
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        self.started.set()
        await self.release.wait()
        return await super().analyze(
            instruction=instruction,
            plan=plan,
            files=files,
            validation_feedback=validation_feedback,
        )


class RepairableAnalyst(FakeAnalyst):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0
        self.feedback: list[str | None] = []

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        self.calls += 1
        self.feedback.append(validation_feedback)
        result = await super().analyze(
            instruction=instruction,
            plan=plan,
            files=files,
            validation_feedback=validation_feedback,
        )
        if self.calls != 1:
            return result
        finding = result.findings[0].model_copy(
            update={
                "evidence_quotes": [
                    HarnessEvidenceQuote(
                        file_ref=result.findings[0].file_refs[0],
                        role="support",
                        label="无法定位的短句",
                        quote="preview does not contain this quote",
                    )
                ]
            }
        )
        return result.model_copy(update={"findings": [finding]})


class AlwaysUnlocatableAnalyst(FakeAnalyst):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        self.calls += 1
        result = await super().analyze(
            instruction=instruction,
            plan=plan,
            files=files,
            validation_feedback=validation_feedback,
        )
        finding = result.findings[0].model_copy(
            update={
                "evidence_quotes": [
                    HarnessEvidenceQuote(
                        file_ref=result.findings[0].file_refs[0],
                        role="support",
                        label="无法定位的候选原文",
                        quote="preview never contains this unique sentence",
                    )
                ]
            }
        )
        return result.model_copy(update={"findings": [finding]})


class AmbiguousCatalog(FakeCatalog):
    def agent_file_inputs(self, file_refs: list[str]) -> list[dict[str, object]]:
        inputs = super().agent_file_inputs(file_refs)
        for item in inputs:
            if item["file_ref"] == REF_TWO:
                item["text"] = "复核说明\n其他内容\n复核说明"
        return inputs


class TripleAmbiguousCatalog(AmbiguousCatalog):
    def agent_file_inputs(self, file_refs: list[str]) -> list[dict[str, object]]:
        inputs = super().agent_file_inputs(file_refs)
        for item in inputs:
            if item["file_ref"] == REF_TWO:
                item["text"] = "复核说明\n其他内容\n复核说明\n附加说明\n复核说明"
        return inputs


class MixedEvidenceAnalyst(FakeAnalyst):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        self.calls += 1
        return HarnessTaskResult(
            summary="一条发现可核对，另一条需要消歧",
            findings=[
                HarnessFinding(
                    plan_unit_id="u1",
                    title="已定位的财务事实",
                    detail="表格中的余额行可以唯一定位。",
                    fact_summary="客商 A 的余额记录为 100。",
                    file_refs=[REF_ONE],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=REF_ONE,
                            role="support",
                            label="唯一余额行",
                            quote="A | 100",
                        )
                    ],
                ),
                HarnessFinding(
                    plan_unit_id="u2",
                    title="复核说明位置不唯一",
                    detail="相同短句在文件中出现两次。",
                    fact_summary="Agent 引用了复核说明，但位置不唯一。",
                    impact="需要确认具体段落后才能继续该分支。",
                    file_refs=[REF_TWO],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=REF_TWO,
                            role="contradiction",
                            label="重复复核说明",
                            quote="复核说明",
                        )
                    ],
                ),
            ],
            review_required=True,
        )


class FiveFindingAnalyst(FakeAnalyst):
    """Four exact findings plus one three-way ambiguous finding, then repair."""

    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        self.calls += 1
        refs = {str(item["file_ref"]) for item in files}
        if refs == {REF_TWO} and self.calls >= 3:
            return HarnessTaskResult(
                summary="第五个分支已补齐唯一定位",
                findings=[
                    HarnessFinding(
                        plan_unit_id="u5",
                        title="复核说明已唯一定位",
                        detail="补核后使用唯一的附加说明作为证据。",
                        file_refs=[REF_TWO],
                        evidence_quotes=[
                            HarnessEvidenceQuote(
                                file_ref=REF_TWO,
                                role="support",
                                label="唯一附加说明",
                                quote="附加说明",
                            )
                        ],
                    )
                ],
                review_required=True,
            )

        findings = [
            HarnessFinding(
                plan_unit_id=f"u{index}",
                title=f"已定位事实 {index}",
                detail="表格中的余额记录可以唯一定位。",
                file_refs=[REF_ONE],
                evidence_quotes=[
                    HarnessEvidenceQuote(
                        file_ref=REF_ONE,
                        role="support",
                        label="唯一余额行",
                        quote="A | 100",
                    )
                ],
            )
            for index in range(1, 5)
        ]
        findings.append(
            HarnessFinding(
                plan_unit_id="u5",
                title="复核说明位置不唯一",
                detail="相同短句在文件中出现三次。",
                impact="需要确认具体段落后才能继续该分支。",
                file_refs=[REF_TWO],
                evidence_quotes=[
                    HarnessEvidenceQuote(
                        file_ref=REF_TWO,
                        role="contradiction",
                        label="重复复核说明",
                        quote="复核说明",
                    )
                ],
            )
        )
        return HarnessTaskResult(
            summary="四条发现可核对，另一条需要消歧",
            findings=findings,
            review_required=True,
        )


class HumanDecisionAnalyst(FakeAnalyst):
    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        result = await super().analyze(
            instruction=instruction,
            plan=plan,
            files=files,
            validation_feedback=validation_feedback,
        )
        review = AgentControlLoopFindingReview(
            requires_human_decision=True,
            question="是否以当前文件作为后续核对口径？",
            why_human="两个业务口径需要责任人选择。",
            options=[
                AgentControlLoopFindingDecisionOption(
                    option_id="A",
                    label="采用当前口径",
                    meaning="以当前文件继续只读核对。",
                    agent_next_step="创建一条独立只读任务。",
                    next_instruction="按当前文件口径继续核对并保留引用。",
                ),
                AgentControlLoopFindingDecisionOption(
                    option_id="B",
                    label="暂不采用",
                    meaning="保留现有结果并补充来源。",
                    agent_next_step="创建一条补充来源任务。",
                    next_instruction="先寻找补充来源，再重新判断当前口径。",
                ),
            ],
            recommended_option_id="A",
            recommendation_reason="当前文件可唯一定位。",
            after_confirmation="决定将先写入当前任务回执。",
        )
        finding = result.findings[0].model_copy(
            update={
                "evidence_quotes": [
                    quote.model_copy(update={"role": "contradiction"})
                    for quote in result.findings[0].evidence_quotes
                ],
                "review": review,
            }
        )
        return result.model_copy(update={"findings": [finding]})


class RepairableStructureAnalyst(FakeAnalyst):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0
        self.feedback: list[str | None] = []

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        self.calls += 1
        self.feedback.append(validation_feedback)
        if self.calls == 1:
            raise HarnessModelError(
                "模型未返回合法的只读分析结果",
                called=True,
                elapsed_ms=10,
                model=self.model,
            )
        return await super().analyze(
            instruction=instruction,
            plan=plan,
            files=files,
            validation_feedback=validation_feedback,
        )


class AlwaysMalformedStructureAnalyst(FakeAnalyst):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0
        self.feedback: list[str | None] = []

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        self.calls += 1
        self.feedback.append(validation_feedback)
        raise HarnessModelError(
            "模型未返回合法的只读分析结果",
            called=True,
            elapsed_ms=10,
            model=self.model,
        )


def start_request(**updates) -> HarnessRunStart:
    payload = {
        "workspace_id": "forte-public-office",
        "idempotency_key": "workspace-run-0001",
        "instruction": "研究整个资料库中的跨期余额变化",
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


async def wait_status(
    runtime: HarnessRuntime, owner: str, run_id: str, expected: str
):
    for _ in range(300):
        snapshot = await runtime.get(owner, run_id)
        if snapshot.status == expected:
            return snapshot
        await asyncio.sleep(0)
    raise AssertionError(f"harness run did not reach {expected}")


async def confirm_evidence_gate(
    runtime: HarnessRuntime, owner: str, run_id: str, key: str
):
    waiting = await wait_status(runtime, owner, run_id, "waiting_input")
    return await runtime.control(
        owner,
        run_id,
        AgentControlLoopControlRequest(
            command="resume",
            idempotency_key=key,
            expected_version=waiting.version,
        ),
    )


def test_default_complete_task_budget_and_server_bounds() -> None:
    defaults = AgentControlLoopOptions()
    assert defaults.max_rounds == 12
    assert defaults.max_files_per_round == 16
    assert defaults.max_model_calls == 30
    assert defaults.deadline_seconds == 7_200

    maximum = AgentControlLoopOptions(
        max_rounds=24,
        max_files_per_round=24,
        max_model_calls=60,
        deadline_seconds=14_400,
    )
    assert maximum.max_rounds == 24
    assert maximum.max_files_per_round == 24
    assert maximum.max_model_calls == 60
    assert maximum.deadline_seconds == 14_400

    for invalid in (
        {"max_rounds": 25},
        {"max_files_per_round": 25},
        {"max_model_calls": 61},
        {"deadline_seconds": 14_401},
    ):
        with pytest.raises(ValidationError):
            AgentControlLoopOptions(**invalid)


@pytest.mark.asyncio
async def test_waiting_for_human_does_not_spend_active_deadline() -> None:
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst())
    started = await runtime.start(
        "alice",
        start_request(idempotency_key="active-deadline-wait-0001"),
    )
    waiting = await wait_status(runtime, "alice", started.run.run_id, "waiting_input")
    internal = runtime._runs[("alice", started.run.run_id)]

    assert internal.active_since_perf is None
    frozen_elapsed = waiting.budget.elapsed_ms
    await asyncio.sleep(0.02)
    assert runtime._budget_with_elapsed(internal).elapsed_ms == frozen_elapsed

    await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="stop",
            idempotency_key="active-deadline-wait-stop-0001",
            expected_version=waiting.version,
        ),
    )
    terminal = await wait_terminal(runtime, "alice", started.run.run_id)
    assert terminal.status == "stopped"


@pytest.mark.asyncio
async def test_user_task_searches_the_whole_workspace_and_selects_evidence() -> None:
    planner = FakePlanner()
    analyst = FakeAnalyst()
    runtime = HarnessRuntime(FakeCatalog(), planner, analyst)

    started = await runtime.start("alice", start_request())
    waiting = await wait_status(runtime, "alice", started.run.run_id, "waiting_input")
    assert waiting.control_state == "paused"
    assert waiting.rounds[0].next_step
    assert waiting.rounds[0].next_step.decision == "waiting_input"
    await confirm_evidence_gate(
        runtime, "alice", started.run.run_id, "evidence-confirm-0001"
    )
    snapshot = await wait_terminal(runtime, "alice", started.run.run_id)

    assert snapshot.workspace_id == "forte-public-office"
    assert snapshot.instruction_source == "user"
    assert snapshot.status == "completed"
    assert snapshot.contract.goal == snapshot.instruction
    assert snapshot.contract.scope_mode == "whole_workspace"
    assert snapshot.contract.allowed_file_refs == [REF_ONE, REF_TWO]
    assert "整个公开办公资料库" in (snapshot.selection_reason or "")
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
    assert snapshot.rounds[0].next_step.decision == "waiting_input"
    assert snapshot.rounds[0].evidence_gaps
    assert snapshot.rounds[1].next_step
    assert snapshot.rounds[1].next_step.decision == "completed"
    event_names = [event.event_name for event in snapshot.events]
    assert event_names.count("round_started") == 2
    assert event_names.count("evidence_gate") == 2
    assert event_names[-1] == "loop_committed"
    assert [item.status for item in snapshot.artifact_versions] == [
        "draft",
        "verified",
    ]
    assert snapshot.last_commit
    assert snapshot.last_commit.artifact_version == 2
    assert snapshot.commits == [snapshot.last_commit]
    assert snapshot.rounds[0].branch_ids
    assert all(item.status == "completed" for item in snapshot.branches)
    resumed_parent = next(
        item for item in snapshot.branches if item.round_number == 1 and item.unit_id == "u2"
    )
    assert snapshot.active_branch_id == resumed_parent.branch_id
    assert all(
        item.parent_branch_id == resumed_parent.branch_id
        for item in snapshot.branches
        if item.round_number == 2
    )


@pytest.mark.asyncio
async def test_analyst_repairs_unlocatable_quotes_within_the_same_budget() -> None:
    analyst = RepairableAnalyst()
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), analyst)
    started = await runtime.start(
        "alice",
        start_request(idempotency_key="analysis-anchor-repair-0001"),
    )
    await confirm_evidence_gate(
        runtime, "alice", started.run.run_id, "analysis-anchor-repair-confirm-0001"
    )
    snapshot = await wait_terminal(runtime, "alice", started.run.run_id)

    assert snapshot.status == "completed"
    assert analyst.calls == 3
    assert analyst.feedback[0] is None
    assert analyst.feedback[1] and "唯一匹配" in analyst.feedback[1]
    assert snapshot.budget.model_calls_used == 5
    assert [event.event_name for event in snapshot.events].count(
        "analysis_validation_rejected"
    ) == 1
    assert snapshot.result
    assert snapshot.result.findings[0].evidence_anchors


@pytest.mark.asyncio
async def test_unlocatable_analysis_pauses_with_an_explicit_recovery_path() -> None:
    analyst = AlwaysUnlocatableAnalyst()
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), analyst)
    started = await runtime.start(
        "alice",
        start_request(
            idempotency_key="analysis-location-recovery-0001",
            loop={
                "max_rounds": 2,
                "max_files_per_round": 2,
                "max_model_calls": 6,
                "deadline_seconds": 120,
            },
        ),
    )

    waiting = await wait_status(runtime, "alice", started.run.run_id, "waiting_input")

    assert waiting.control_state == "paused"
    assert analyst.calls == 2
    assert waiting.rounds[0].status == "completed"
    assert waiting.rounds[0].result is None
    assert waiting.rounds[0].next_step
    assert waiting.rounds[0].next_step.decision == "waiting_input"
    assert waiting.rounds[0].next_step.recovery_kind == "source_location"
    assert waiting.rounds[0].next_step.candidate_branch_ids
    assert all(branch.status == "waiting_input" for branch in waiting.branches)
    assert not any(event.event_name == "harness_failed" for event in waiting.events)
    assert "analysis_recovery_required" in [
        event.event_name for event in waiting.events
    ]
    assert waiting.validation_errors == []

    stopped = await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="stop",
            idempotency_key="analysis-location-recovery-stop-0001",
            expected_version=waiting.version,
        ),
    )
    assert stopped.run.control_state == "stop_requested"
    terminal = await wait_terminal(runtime, "alice", started.run.run_id)
    assert terminal.status == "stopped"


@pytest.mark.asyncio
async def test_decision_packet_id_and_source_revision_mismatch_do_not_change_resolution() -> None:
    runtime = HarnessRuntime(AmbiguousCatalog(), FakePlanner(), MixedEvidenceAnalyst())
    started = await runtime.start(
        "alice", start_request(idempotency_key="decision-negative-start-0001")
    )
    waiting = await wait_status(runtime, "alice", started.run.run_id, "waiting_input")
    resolution = waiting.rounds[0].next_step.evidence_resolutions[0]
    packet = waiting.decision_requests[0]
    candidate = resolution.candidates[0]

    with pytest.raises(HarnessConflictError, match="decision_request_id"):
        await runtime.control(
            "alice",
            started.run.run_id,
            AgentControlLoopControlRequest(
                command="decision",
                decision_action="accept",
                finding_id=resolution.finding_id,
                resolution_id=resolution.resolution_id,
                branch_id=resolution.branch_id,
                selected_candidate_id=candidate.candidate_id,
                source_revision=packet.source_revision,
                idempotency_key="decision-negative-missing-id-0001",
                expected_version=waiting.version,
            ),
        )

    with pytest.raises(HarnessConflictError, match="资料版本令牌不匹配"):
        await runtime.control(
            "alice",
            started.run.run_id,
            AgentControlLoopControlRequest(
                command="decision",
                decision_action="accept",
                decision_request_id=packet.decision_request_id,
                finding_id=resolution.finding_id,
                resolution_id=resolution.resolution_id,
                branch_id=resolution.branch_id,
                selected_candidate_id=candidate.candidate_id,
                source_revision="rev-0000000000000000",
                idempotency_key="decision-negative-stale-token-0001",
                expected_version=waiting.version,
            ),
        )

    unchanged = await runtime.get("alice", started.run.run_id)
    assert unchanged.version == waiting.version
    assert unchanged.rounds[0].next_step.evidence_resolutions[0].status == "ambiguous"
    assert unchanged.decision_requests[0].state == "open"
    assert not any(
        event.event_name in {"evidence_resolution_stale", "evidence_resolution_rejected"}
        for event in unchanged.events
    )
    await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="stop",
            idempotency_key="decision-negative-stop-0001",
            expected_version=unchanged.version,
        ),
    )
    await wait_terminal(runtime, "alice", started.run.run_id)


@pytest.mark.asyncio
async def test_decline_rejects_only_resolution_and_preserves_other_branch_and_v1() -> None:
    runtime = HarnessRuntime(AmbiguousCatalog(), FakePlanner(), MixedEvidenceAnalyst())
    started = await runtime.start(
        "alice", start_request(idempotency_key="decision-decline-start-0001")
    )
    waiting = await wait_status(runtime, "alice", started.run.run_id, "waiting_input")
    resolution = waiting.rounds[0].next_step.evidence_resolutions[0]
    packet = waiting.decision_requests[0]
    declined = await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="decision",
            decision_action="decline",
            decision_request_id=packet.decision_request_id,
            finding_id=resolution.finding_id,
            resolution_id=resolution.resolution_id,
            branch_id=resolution.branch_id,
            idempotency_key="decision-decline-control-0001",
            expected_version=waiting.version,
        ),
    )

    assert declined.run.status == "waiting_input"
    assert declined.run.rounds[0].next_step.evidence_resolutions[0].status == "rejected"
    assert declined.run.decision_requests[0].state == "declined"
    assert declined.run.artifact_versions == waiting.artifact_versions
    assert declined.run.branches[0].status == "completed"
    assert not any(
        event.event_name == "branch_resumed_from_checkpoint"
        for event in declined.run.events
    )
    await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="stop",
            idempotency_key="decision-decline-stop-0001",
            expected_version=declined.run.version,
        ),
    )
    await wait_terminal(runtime, "alice", started.run.run_id)


@pytest.mark.asyncio
async def test_ambiguous_finding_pauses_only_its_branch_and_preserves_artifact() -> None:
    analyst = MixedEvidenceAnalyst()
    runtime = HarnessRuntime(AmbiguousCatalog(), FakePlanner(), analyst)
    started = await runtime.start(
        "alice",
        start_request(idempotency_key="ambiguous-branch-recovery-start-0001"),
    )
    waiting = await wait_status(
        runtime, "alice", started.run.run_id, "waiting_input"
    )

    assert analyst.calls == 2
    assert [item.status for item in waiting.branches] == [
        "completed",
        "waiting_input",
    ]
    assert waiting.artifact_versions
    assert waiting.artifact_versions[0].finding_count == 1
    assert waiting.artifact_versions[0].findings[0].title == "已定位的财务事实"
    assert waiting.rounds[0].result is not None
    assert len(HarnessTaskResult.model_validate(waiting.rounds[0].result).findings) == 1
    resolution = waiting.rounds[0].next_step.evidence_resolutions[0]
    assert resolution.status == "ambiguous"
    assert resolution.branch_id == waiting.branches[1].branch_id
    assert len(resolution.candidates) == 2
    assert {
        "analysis_partial_adopted",
        "evidence_disambiguation_required",
        "partial_artifact_saved",
    }.issubset({event.event_name for event in waiting.events})

    deferred_request = AgentControlLoopControlRequest(
        command="decision",
        decision_action="defer",
        decision_request_id=waiting.decision_requests[0].decision_request_id,
        finding_id=resolution.finding_id,
        resolution_id=resolution.resolution_id,
        branch_id=resolution.branch_id,
        idempotency_key="ambiguous-defer-decision-0001",
        expected_version=waiting.version,
    )
    deferred = await runtime.control(
        "alice", started.run.run_id, deferred_request
    )
    replayed = await runtime.control(
        "alice", started.run.run_id, deferred_request
    )
    assert replayed.replayed is True
    assert deferred.run.decision_records[-1].action == "defer"
    assert deferred.run.status == "waiting_input"
    assert deferred.run.artifact_versions[0] == waiting.artifact_versions[0]

    accepted = await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="decision",
            decision_action="accept",
            decision_request_id=waiting.decision_requests[0].decision_request_id,
            finding_id=resolution.finding_id,
            resolution_id=resolution.resolution_id,
            branch_id=resolution.branch_id,
                selected_candidate_id=resolution.candidates[0].candidate_id,
                source_revision=resolution.source_revision,
                feedback="采用第一处，并核对版本字段。",
            idempotency_key="ambiguous-accept-decision-0001",
            expected_version=deferred.run.version,
        ),
    )
    assert accepted.run.decision_records[-1].action == "accept"
    assert (
        accepted.run.decision_records[-1].selected_candidate_id
        == resolution.candidates[0].candidate_id
    )
    assert any(event.event_name == "decision_recorded" for event in accepted.run.events)
    assert accepted.run.events[-1].event_name == "branch_resumed_from_checkpoint"
    assert accepted.run.branches[0].status == "completed"
    assert accepted.run.artifact_versions[0] == waiting.artifact_versions[0]

    stopped = await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="stop",
            idempotency_key="ambiguous-branch-recovery-stop-0001",
            expected_version=accepted.run.version,
        ),
    )
    assert stopped.run.control_state == "stop_requested"
    terminal = await wait_terminal(runtime, "alice", started.run.run_id)
    assert terminal.status == "stopped"


@pytest.mark.asyncio
async def test_five_findings_keep_four_v1_and_append_v2_for_only_ambiguous_branch() -> None:
    analyst = FiveFindingAnalyst()
    runtime = HarnessRuntime(TripleAmbiguousCatalog(), FiveBranchPlanner(), analyst)
    started = await runtime.start(
        "alice", start_request(idempotency_key="five-finding-start-0001")
    )
    waiting = await wait_status(runtime, "alice", started.run.run_id, "waiting_input")

    resolution = waiting.rounds[0].next_step.evidence_resolutions[0]
    assert resolution.status == "ambiguous"
    assert len(resolution.candidates) == 3
    assert len(waiting.artifact_versions) == 1
    v1 = waiting.artifact_versions[0]
    assert v1.version == 1
    assert v1.finding_count == 4
    assert [branch.status for branch in waiting.branches[:5]] == [
        "completed",
        "completed",
        "completed",
        "completed",
        "waiting_input",
    ]
    packet = next(
        item
        for item in waiting.decision_requests
        if item.resolution_id == resolution.resolution_id
    )
    target_branch_id = resolution.branch_id
    assert target_branch_id
    accepted = await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="decision",
            decision_action="accept",
            decision_request_id=packet.decision_request_id,
            finding_id=resolution.finding_id,
            resolution_id=resolution.resolution_id,
            branch_id=target_branch_id,
            selected_candidate_id=resolution.candidates[0].candidate_id,
            source_revision=packet.source_revision,
            idempotency_key="five-finding-accept-0001",
            expected_version=waiting.version,
        ),
    )
    assert any(
        event.event_name == "branch_resumed_from_checkpoint"
        and event.details.get("branch_id") == target_branch_id
        for event in accepted.run.events
    )
    assert all(
        branch.status == "completed"
        for branch in accepted.run.branches[:4]
    )
    terminal = await wait_terminal(runtime, "alice", started.run.run_id)
    assert terminal.status == "completed"
    assert [item.version for item in terminal.artifact_versions] == [1, 2]
    assert terminal.artifact_versions[0] == v1
    assert terminal.artifact_versions[0].finding_count == 4
    assert terminal.artifact_versions[1].finding_count == 1
    assert all(branch.status == "completed" for branch in terminal.branches)


@pytest.mark.asyncio
async def test_terminal_finding_decision_is_versioned_before_follow_up_work() -> None:
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), HumanDecisionAnalyst())
    started = await runtime.start(
        "alice",
        start_request(idempotency_key="terminal-decision-start-0001"),
    )
    await confirm_evidence_gate(
        runtime, "alice", started.run.run_id, "terminal-decision-gate-0001"
    )
    terminal = await wait_terminal(runtime, "alice", started.run.run_id)
    assert terminal.status == "completed"
    assert terminal.result is not None
    finding = terminal.result.findings[0]
    assert finding.finding_id is not None
    assert finding.review is not None
    assert finding.review.options[0].affected_branch_ids
    assert finding.review.options[0].required_file_refs == finding.file_refs

    accepted = await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="decision",
            decision_action="accept",
            decision_request_id=terminal.decision_requests[0].decision_request_id,
            finding_id=finding.finding_id,
            branch_id=finding.affected_branch_ids[0],
            selected_option_id="A",
            feedback="先保留原文件，只形成核对清单。",
            idempotency_key="terminal-decision-accept-0001",
            expected_version=terminal.version,
        ),
    )
    assert accepted.run.status == "completed"
    assert accepted.run.version == terminal.version + 1
    assert accepted.run.decision_records[-1].selected_option_id == "A"
    assert accepted.run.decision_records[-1].external_action == "none"
    assert accepted.run.events[-1].event_name == "decision_recorded"


@pytest.mark.asyncio
async def test_malformed_analysis_is_retried_before_requesting_user_recovery() -> None:
    analyst = RepairableStructureAnalyst()
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), analyst)
    started = await runtime.start(
        "alice",
        start_request(idempotency_key="analysis-structure-repair-0001"),
    )
    await confirm_evidence_gate(
        runtime, "alice", started.run.run_id, "analysis-structure-confirm-0001"
    )
    snapshot = await wait_terminal(runtime, "alice", started.run.run_id)

    assert snapshot.status == "completed"
    assert analyst.calls == 3
    assert analyst.feedback[0] is None
    assert analyst.feedback[1] and "严格 JSON" in analyst.feedback[1]
    assert snapshot.budget.model_calls_used == 5
    assert [event.event_name for event in snapshot.events].count(
        "analysis_structure_rejected"
    ) == 1
    assert snapshot.result


@pytest.mark.asyncio
async def test_repeated_malformed_analysis_pauses_with_a_recovery_path() -> None:
    analyst = AlwaysMalformedStructureAnalyst()
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), analyst)
    started = await runtime.start(
        "alice",
        start_request(
            idempotency_key="analysis-structure-recovery-0001",
            loop={
                "max_rounds": 2,
                "max_files_per_round": 2,
                "max_model_calls": 6,
                "deadline_seconds": 120,
            },
        ),
    )

    waiting = await wait_status(runtime, "alice", started.run.run_id, "waiting_input")

    assert waiting.control_state == "paused"
    assert analyst.calls == 2
    assert analyst.feedback[0] is None
    assert analyst.feedback[1] and "严格 JSON" in analyst.feedback[1]
    assert waiting.rounds[0].status == "completed"
    assert waiting.rounds[0].result is None
    assert waiting.rounds[0].next_step
    assert waiting.rounds[0].next_step.recovery_kind == "analysis_output"
    assert waiting.validation_errors == []
    assert [event.event_name for event in waiting.events].count(
        "analysis_structure_rejected"
    ) == 2

    await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="stop",
            idempotency_key="analysis-structure-recovery-stop-0001",
            expected_version=waiting.version,
        ),
    )
    terminal = await wait_terminal(runtime, "alice", started.run.run_id)
    assert terminal.status == "stopped"


@pytest.mark.asyncio
async def test_confirmed_evidence_round_cannot_drift_to_unrelated_files() -> None:
    planner = FakePlanner()
    runtime = HarnessRuntime(FakeCatalogWithDistractor(), planner, FakeAnalyst())
    started = await runtime.start(
        "alice",
        start_request(
            idempotency_key="evidence-scope-0001",
            loop={
                "max_rounds": 2,
                "max_files_per_round": 2,
                "max_model_calls": 4,
                "deadline_seconds": 120,
            },
        ),
    )

    waiting = await wait_status(runtime, "alice", started.run.run_id, "waiting_input")
    assert waiting.rounds[0].next_step
    assert waiting.rounds[0].next_step.candidate_file_refs == [REF_TWO]
    await confirm_evidence_gate(
        runtime, "alice", started.run.run_id, "evidence-scope-confirm-0001"
    )
    snapshot = await wait_terminal(runtime, "alice", started.run.run_id)

    assert snapshot.status == "completed"
    assert snapshot.rounds[1].input_file_refs == [REF_TWO]
    assert planner.files and [item["file_ref"] for item in planner.files] == [REF_TWO]
    assert planner.workspace
    assert planner.workspace["control_loop"]["evidence_recheck"] is True
    second_round_event = [
        event for event in snapshot.events if event.event_name == "round_started"
    ][1]
    assert second_round_event.details["evidence_recheck"] is True


@pytest.mark.asyncio
async def test_user_can_continue_one_waiting_branch_without_spending_other_branch() -> None:
    planner = MultiBranchPlanner()
    runtime = HarnessRuntime(FakeCatalogWithDistractor(), planner, FakeAnalyst())
    started = await runtime.start(
        "alice",
        start_request(
            idempotency_key="branch-local-start-0001",
            loop={
                "max_rounds": 3,
                "max_files_per_round": 3,
                "max_model_calls": 6,
                "deadline_seconds": 120,
            },
        ),
    )

    first_wait = await wait_status(
        runtime, "alice", started.run.run_id, "waiting_input"
    )
    waiting = [item for item in first_wait.branches if item.status == "waiting_input"]
    assert {tuple(item.missing_file_refs) for item in waiting} == {
        (REF_TWO,),
        (REF_THREE,),
    }
    legal_branch = next(item for item in waiting if item.missing_file_refs == [REF_THREE])
    await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="resume",
            branch_id=legal_branch.branch_id,
            idempotency_key="branch-local-legal-0001",
            expected_version=first_wait.version,
        ),
    )

    second_wait = await wait_status(
        runtime, "alice", started.run.run_id, "waiting_input"
    )
    assert planner.file_ref_history[1] == [REF_THREE]
    still_waiting = [
        item for item in second_wait.branches if item.status == "waiting_input"
    ]
    assert len(still_waiting) == 1
    assert still_waiting[0].missing_file_refs == [REF_TWO]
    await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="resume",
            branch_id=still_waiting[0].branch_id,
            idempotency_key="branch-local-review-0001",
            expected_version=second_wait.version,
        ),
    )
    terminal = await wait_terminal(runtime, "alice", started.run.run_id)

    assert terminal.status == "completed"
    assert planner.file_ref_history[2] == [REF_TWO]
    assert all(item.status == "completed" for item in terminal.branches)
    resume_controls = [
        item for item in terminal.control_events if item.command == "resume"
    ]
    assert [item.branch_id for item in resume_controls] == [
        legal_branch.branch_id,
        still_waiting[0].branch_id,
    ]


@pytest.mark.asyncio
async def test_rejected_plan_is_repaired_once_within_the_same_budget() -> None:
    planner = RepairablePlanner()
    runtime = HarnessRuntime(FakeCatalog(), planner, FakeAnalyst())
    started = await runtime.start(
        "alice",
        start_request(
            idempotency_key="repair-plan-0001",
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


def test_start_requires_only_a_user_instruction_and_rejects_client_file_scope() -> None:
    with pytest.raises(ValidationError):
        HarnessRunStart(idempotency_key="missing-inputs")
    with pytest.raises(ValidationError):
        start_request(instruction="  ")
    with pytest.raises(ValidationError):
        start_request(selected_file_refs=[REF_ONE])


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
    assert snapshot.events[-1].details["output_used"] is False
    assert runtime.public_snapshot(snapshot).validation_errors


@pytest.mark.asyncio
async def test_invalid_result_citation_fails_closed() -> None:
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst(invalid_reference=True))
    started = await runtime.start("alice", start_request(idempotency_key="invalid-result-0001"))
    snapshot = await wait_terminal(runtime, "alice", started.run.run_id)

    assert snapshot.status == "failed"
    assert snapshot.result is None
    assert snapshot.analysis_receipt and not snapshot.analysis_receipt.output_used
    assert snapshot.events[-1].details["output_used"] is False


@pytest.mark.asyncio
async def test_start_freezes_the_complete_server_owned_workspace_scope() -> None:
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst())
    started = await runtime.start(
        "alice",
        start_request(
            idempotency_key="whole-workspace-0001",
            loop={
                "max_rounds": 1,
                "max_files_per_round": 1,
                "max_model_calls": 2,
                "deadline_seconds": 120,
            },
        ),
    )
    snapshot = await wait_terminal(runtime, "alice", started.run.run_id)

    assert snapshot.contract.allowed_file_refs == [REF_ONE, REF_TWO]
    assert [item["file_ref"] for item in snapshot.source_documents] == [
        REF_ONE,
        REF_TWO,
    ]


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
    assert snapshot.budget.stop_reason == "模型调用预算已耗尽"
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
    await confirm_evidence_gate(
        runtime, "alice", started.run.run_id, "gate-after-pause-0001"
    )
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
            json=start_request(
                idempotency_key="route-start-0001",
                loop={
                    "max_rounds": 1,
                    "max_files_per_round": 1,
                    "max_model_calls": 2,
                    "deadline_seconds": 120,
                },
            ).model_dump(),
        )

        assert workspace.status_code == 200 and workspace.json()["folder_count"] == 1
        assert preview.status_code == 200 and preview.json()["security"]["read_only"] is True
        assert retired.status_code == 404
        assert started.status_code == 202
        recent = await client.get("/v1/harness/runs?limit=5", headers=headers)
        assert recent.status_code == 200
        assert recent.json()["runs"][0]["run_id"] == started.json()["run"]["run_id"]
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

    await confirm_evidence_gate(
        runtime, "alice", run_id, "route-gate-confirm-0001"
    )
    terminal = await wait_terminal(runtime, "alice", run_id)
    assert terminal.status == "completed"
    assert [item.command for item in terminal.control_events] == [
        "pause",
        "resume",
        "resume",
    ]


@pytest.mark.asyncio
async def test_http_workspace_integrity_failure_is_503() -> None:
    app = create_app()
    app.state.harness_runtime = HarnessRuntime(FakeCatalog(broken=True), FakePlanner())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/harness/workspace")

    assert response.status_code == 503
    assert response.json()["detail"] == "办公资料库完整性校验失败"


@pytest.mark.asyncio
async def test_checkpoint_restore_pauses_without_replaying_interrupted_model_call() -> None:
    store = InMemoryHarnessStateStore()
    blocking_planner = BlockingPlanner()
    first_runtime = HarnessRuntime(
        FakeCatalog(), blocking_planner, FakeAnalyst(), store
    )
    await first_runtime.setup()
    request = start_request(idempotency_key="durable-start-0001")
    started = await first_runtime.start("alice", request)
    await asyncio.wait_for(blocking_planner.started.wait(), timeout=1)
    await first_runtime.close()

    recovered_planner = FakePlanner()
    recovered_runtime = HarnessRuntime(
        FakeCatalog(), recovered_planner, FakeAnalyst(), store
    )
    await recovered_runtime.setup()
    recovered = await recovered_runtime.get("alice", started.run.run_id)

    assert recovered.status == "paused"
    assert recovered.control_state == "paused"
    assert recovered.rounds == []
    assert recovered_planner.calls == 0
    assert recovered.events[-1].event_name == "checkpoint_recovered"
    assert (await recovered_runtime.list("alice"))[0].run_id == started.run.run_id
    replay = await recovered_runtime.start("alice", request)
    assert replay.replayed is True
    assert replay.run.run_id == started.run.run_id

    await recovered_runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="resume",
            idempotency_key="durable-resume-0001",
            expected_version=recovered.version,
        ),
    )
    await confirm_evidence_gate(
        recovered_runtime,
        "alice",
        started.run.run_id,
        "durable-evidence-confirm-0001",
    )
    terminal = await wait_terminal(
        recovered_runtime, "alice", started.run.run_id
    )

    assert terminal.status == "completed"
    assert recovered_planner.calls == 2
    assert terminal.last_commit is not None
    await recovered_runtime.close()


@pytest.mark.asyncio
async def test_checkpoint_restore_discards_branches_from_an_interrupted_round() -> None:
    store = InMemoryHarnessStateStore()
    blocking_analyst = BlockingAnalyst()
    first_runtime = HarnessRuntime(
        FakeCatalog(), FakePlanner(), blocking_analyst, store
    )
    await first_runtime.setup()
    started = await first_runtime.start(
        "alice", start_request(idempotency_key="branch-recovery-start-0001")
    )
    await asyncio.wait_for(blocking_analyst.started.wait(), timeout=1)
    interrupted = await first_runtime.get("alice", started.run.run_id)
    assert interrupted.rounds[-1].status == "running"
    assert interrupted.branches
    await first_runtime.close()

    recovered_runtime = HarnessRuntime(
        FakeCatalog(), FakePlanner(), FakeAnalyst(), store
    )
    await recovered_runtime.setup()
    recovered = await recovered_runtime.get("alice", started.run.run_id)

    assert recovered.status == "paused"
    assert recovered.rounds == []
    assert recovered.branches == []
    assert recovered.active_branch_id is None
    await recovered_runtime.close()


@pytest.mark.asyncio
async def test_artifact_versions_are_append_only_and_restore_moves_only_commit_pointer() -> None:
    store = InMemoryHarnessStateStore()
    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), FakeAnalyst(), store)
    await runtime.setup()
    started = await runtime.start(
        "alice", start_request(idempotency_key="artifact-history-start-0001")
    )
    await confirm_evidence_gate(
        runtime, "alice", started.run.run_id, "artifact-history-gate-0001"
    )
    terminal = await wait_terminal(runtime, "alice", started.run.run_id)

    stored_versions = await store.load_artifact_versions(
        "alice", started.run.run_id
    )
    stored_commits = await store.load_task_commits("alice", started.run.run_id)
    assert [item.version for item in stored_versions] == [1, 2]
    assert len(stored_commits) == 1
    assert terminal.last_commit and terminal.last_commit.artifact_version == 2

    rollback_request = AgentControlLoopControlRequest(
        command="rollback",
        artifact_version=1,
        idempotency_key="artifact-history-rollback-0001",
        expected_version=terminal.version,
    )
    restored = await runtime.control(
        "alice", started.run.run_id, rollback_request
    )

    assert restored.run.status == "completed"
    assert restored.run.last_commit
    assert restored.run.last_commit.operation == "rollback"
    assert restored.run.last_commit.artifact_version == 1
    assert restored.run.last_commit.parent_commit_id == terminal.last_commit.commit_id
    assert restored.run.result
    assert restored.run.result.summary == terminal.artifact_versions[0].summary
    assert restored.run.events[-1].event_name == "artifact_version_restored"
    assert len(await store.load_artifact_versions("alice", started.run.run_id)) == 2
    assert len(await store.load_task_commits("alice", started.run.run_id)) == 2

    replay = await runtime.control("alice", started.run.run_id, rollback_request)
    assert replay.replayed is True
    restored_latest = await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="rollback",
            artifact_version=2,
            idempotency_key="artifact-history-restore-latest-0001",
            expected_version=restored.run.version,
        ),
    )
    assert restored_latest.run.last_commit
    assert restored_latest.run.last_commit.artifact_version == 2
    assert len(restored_latest.run.commits) == 3
    assert len(await store.load_task_commits("alice", started.run.run_id)) == 3
    await runtime.close()


@pytest.mark.asyncio
async def test_memory_store_rejects_immutable_conflict_without_partial_commit() -> None:
    store = InMemoryHarnessStateStore()
    await store.setup()
    original_run = StoredHarnessRun(
        owner_id="alice",
        run_id="harness:atomic",
        snapshot={"version": 1},
        resume_status=None,
    )
    original_artifact = StoredHarnessArtifactVersion(
        owner_id="alice",
        run_id=original_run.run_id,
        artifact_id="artifact-atomic000001",
        version=1,
        payload_digest="digest-one",
        payload={"summary": "original"},
    )
    await store.commit(original_run, artifact_version=original_artifact)

    with pytest.raises(RuntimeError, match="immutable artifact version conflict"):
        await store.commit(
            StoredHarnessRun(
                owner_id="alice",
                run_id=original_run.run_id,
                snapshot={"version": 2},
                resume_status=None,
            ),
            idempotency=StoredHarnessIdempotency(
                owner_id="alice",
                kind="control",
                idempotency_key="atomic-conflict-key",
                digest="command-digest",
                result={"version": 2},
            ),
            artifact_version=StoredHarnessArtifactVersion(
                owner_id="alice",
                run_id=original_run.run_id,
                artifact_id=original_artifact.artifact_id,
                version=1,
                payload_digest="digest-two",
                payload={"summary": "mutated"},
            ),
        )

    assert (await store.load_runs())[0].snapshot == {"version": 1}
    assert await store.load_idempotency() == []
    assert (await store.load_artifact_versions("alice", original_run.run_id))[
        0
    ].payload_digest == "digest-one"


def test_production_builder_uses_complete_workspace_catalog(monkeypatch) -> None:
    class Settings:
        llm_base_url = "https://example.invalid/v1"
        llm_api_key = "test-key"
        llm_model = "deepseek-v4-pro"
        llm_timeout_seconds = 10
        database_dsn = ""

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


def test_server_resolves_model_quotes_to_exact_preview_locations() -> None:
    result = HarnessTaskResult(
        summary="发现设计预期与运行记录不一致",
        findings=[
            HarnessFinding(
                title="新闻搜索未按设计触发",
                detail="代码要求新闻意图进入专用搜索，但日志没有发生该调用。",
                file_refs=[REF_ONE, REF_TWO],
                evidence_quotes=[
                    HarnessEvidenceQuote(
                        file_ref=REF_ONE,
                        role="expected",
                        label="设计预期",
                        quote="intent=news | route=web_search_news",
                    ),
                    HarnessEvidenceQuote(
                        file_ref=REF_TWO,
                        role="observed",
                        label="实际观测",
                        quote="web_search_news_called=false",
                    ),
                ],
            )
        ],
        review_required=True,
    )
    files = [
        {
            "file_ref": REF_ONE,
            "kind": "table",
            "columns": ["intent", "route"],
            "rows": [
                {
                    "row_number": 7,
                    "values": ["intent=news", "route=web_search_news"],
                }
            ],
        },
        {
            "file_ref": REF_TWO,
            "kind": "text",
            "text": "request started\nintent=factual\nweb_search_news_called=false\nrequest ended",
        },
    ]

    resolution = HarnessRuntime._resolve_evidence_anchors(result, files)

    assert resolution.result
    assert resolution.rejected_finding_count == 0
    resolved = resolution.result
    anchors = resolved.findings[0].evidence_anchors
    assert [(item.locator_kind, item.start, item.end) for item in anchors] == [
        ("table_rows", 7, 7),
        ("text_lines", 3, 3),
    ]
    assert resolved.findings[0].evidence_quotes == []
    assert "web_search_news_called=false" in anchors[1].excerpt


def test_text_anchor_tolerates_pdf_layout_line_wrap_without_guessing() -> None:
    quote = (
        '优先级说明：若岗位同时包含多个分类关键词（如"产品运营"、"市场研发"），'
        "以排列靠前的分类为准——技术研发 > 产品/视觉设计 > 运营/市场/职能。"
    )
    text = (
        '优先级说明：若岗位同时包含多个分类关键词（如"产品运营"、"市场研发"），'
        "以排列靠前的分类为准——技术\n"
        "研发 > 产品/视觉设计 > 运营/市场/职能。"
    )

    candidates = HarnessRuntime._resolve_text_anchor_candidates(
        file_ref=REF_TWO,
        role="expected",
        label="岗位分类优先级",
        quote=quote,
        text=text,
    )

    assert len(candidates) == 1
    assert candidates[0].start == 1
    assert candidates[0].end == 2
    assert "技术\n研发" in candidates[0].excerpt


def test_pdf_layout_fallback_keeps_repeated_matches_ambiguous() -> None:
    text = (
        "岗位优先级：技术\n研发 > 产品视觉设计 > 运营市场职能。\n"
        "附录岗位优先级：技术\n研发 > 产品视觉设计 > 运营市场职能。"
    )

    candidates = HarnessRuntime._resolve_text_anchor_candidates(
        file_ref=REF_TWO,
        role="expected",
        label="重复岗位优先级",
        quote="岗位优先级：技术研发 > 产品视觉设计 > 运营市场职能。",
        text=text,
    )

    assert len(candidates) == 2
    assert [(candidate.start, candidate.end) for candidate in candidates] == [(1, 2), (3, 4)]


def test_date_scope_filters_irrelevant_finding_and_suppresses_unproven_gate() -> None:
    review = AgentControlLoopFindingReview(
        requires_human_decision=True,
        question="是否需要人工指定岗位分类？",
        why_human="模型认为关键词分类需要人工选择。",
        options=[
            AgentControlLoopFindingDecisionOption(
                option_id="A",
                label="按关键词归类",
                meaning="使用规则中的关键词和优先级。",
                agent_next_step="保留当前映射。",
                next_instruction="按明确规则复核当前映射。",
            ),
            AgentControlLoopFindingDecisionOption(
                option_id="B",
                label="另行指定",
                meaning="由用户指定其他分类。",
                agent_next_step="形成另一份映射建议。",
                next_instruction="按用户指定分类形成映射建议。",
            ),
        ],
        recommended_option_id="A",
        recommendation_reason="规则已经给出优先级。",
        after_confirmation="只更新分析说明。",
    )
    result = HarnessTaskResult(
        summary="核对岗位分类",
        findings=[
            HarnessFinding(
                title="范围外的产品运营记录",
                detail="该员工不在本次日期范围内。",
                file_refs=[REF_ONE],
                evidence_quotes=[
                    HarnessEvidenceQuote(
                        file_ref=REF_ONE,
                        role="observed",
                        label="范围外记录",
                        quote="姜映雪 | 4月21日 (周二) | 产品运营",
                    )
                ],
            ),
            HarnessFinding(
                title="技术研发按关键词归类",
                detail="规则已明确关键词与优先级。",
                file_refs=[REF_ONE, REF_TWO],
                evidence_quotes=[
                    HarnessEvidenceQuote(
                        file_ref=REF_ONE,
                        role="observed",
                        label="范围内记录",
                        quote="林舒志 | 4月20日 (周一) | 技术研发",
                    ),
                    HarnessEvidenceQuote(
                        file_ref=REF_TWO,
                        role="expected",
                        label="分类规则",
                        quote="技术研发 > 产品/视觉设计 > 运营/市场/职能",
                    ),
                ],
                review=review,
            ),
        ],
        review_required=True,
    )
    files = [
        {
            "file_ref": REF_ONE,
            "kind": "table",
            "columns": ["姓名", "入职日期", "岗位系列"],
            "rows": [
                {"row_number": 13, "values": ["姜映雪", "4月21日 (周二)", "产品运营"]},
                {"row_number": 16, "values": ["林舒志", "4月20日 (周一)", "技术研发"]},
            ],
        },
        {
            "file_ref": REF_TWO,
            "kind": "text",
            "text": "优先级：技术\n研发 > 产品/视觉设计 > 运营/市场/职能",
        },
    ]

    resolution = HarnessRuntime._resolve_evidence_anchors(
        result,
        files,
        instruction="生成 3 月 20 日至 4 月 20 日的入职资产匹配表。",
    )

    assert resolution.result is not None
    assert [item.title for item in resolution.result.findings] == [
        "技术研发按关键词归类"
    ]
    assert resolution.out_of_scope_finding_count == 1
    assert resolution.downgraded_review_count == 1
    assert resolution.result.findings[0].review is None
    assert resolution.evidence_resolutions == ()


def test_server_omits_a_finding_without_a_unique_preview_location() -> None:
    result = HarnessTaskResult(
        summary="候选结论",
        findings=[
            HarnessFinding(
                title="重复片段无法唯一定位",
                detail="相同文本在多个位置出现。",
                file_refs=[REF_TWO],
                evidence_quotes=[
                    HarnessEvidenceQuote(
                        file_ref=REF_TWO,
                        role="support",
                        label="重复片段",
                        quote="same value",
                    )
                ],
            )
        ],
        review_required=True,
    )

    resolution = HarnessRuntime._resolve_evidence_anchors(
        result,
        [
            {
                "file_ref": REF_TWO,
                "kind": "text",
                "text": "same value\nother\nsame value",
            }
        ],
    )

    assert resolution.result is None
    assert resolution.rejected_finding_count == 1
    assert resolution.rejected_file_refs == (REF_TWO,)
    assert len(resolution.evidence_resolutions) == 1
    assert resolution.evidence_resolutions[0].status == "ambiguous"
    assert len(resolution.evidence_resolutions[0].candidates) == 2


def test_server_salvages_locatable_findings_without_publishing_unlocated_ones() -> None:
    result = HarnessTaskResult(
        summary="同时包含可核对与不可核对候选",
        findings=[
            HarnessFinding(
                title="可定位",
                detail="该发现有唯一原文。",
                file_refs=[REF_TWO],
                evidence_quotes=[
                    HarnessEvidenceQuote(
                        file_ref=REF_TWO,
                        role="support",
                        label="唯一片段",
                        quote="unique evidence",
                    )
                ],
            ),
            HarnessFinding(
                title="不可定位",
                detail="该发现引用重复原文。",
                file_refs=[REF_TWO],
                evidence_quotes=[
                    HarnessEvidenceQuote(
                        file_ref=REF_TWO,
                        role="support",
                        label="重复片段",
                        quote="same value",
                    )
                ],
            ),
        ],
        review_required=True,
    )

    resolution = HarnessRuntime._resolve_evidence_anchors(
        result,
        [
            {
                "file_ref": REF_TWO,
                "kind": "text",
                "text": "unique evidence\nsame value\nother\nsame value",
            }
        ],
    )

    assert resolution.result
    assert [finding.title for finding in resolution.result.findings] == ["可定位"]
    assert resolution.rejected_finding_count == 1
    assert resolution.evidence_resolutions[0].status == "ambiguous"


def test_server_compiler_bounds_model_file_selection_and_repairs_dependencies() -> None:
    third_ref = "forte-3333333333333333"
    candidate = HarnessPlanCandidate(
        summary="研究整个资料库",
        selection_reason="模型按业务相关性依次选择三份资料。",
        units=[
            HarnessPlanCandidateUnit(
                unit_id="read-one",
                title="读取一",
                objective="读取第一份资料",
                input_file_refs=[REF_ONE],
                tool="file.read",
            ),
            HarnessPlanCandidateUnit(
                unit_id="read-two",
                title="读取二",
                objective="读取第二份资料",
                input_file_refs=[REF_TWO],
                tool="file.read",
            ),
            HarnessPlanCandidateUnit(
                unit_id="read-three",
                title="读取三",
                objective="读取第三份资料",
                input_file_refs=[third_ref],
                tool="file.read",
            ),
            HarnessPlanCandidateUnit(
                unit_id="write",
                title="形成结果",
                objective="形成本轮结果",
                input_file_refs=[REF_ONE, REF_TWO, third_ref],
                depends_on=["read-one", "read-two", "read-three"],
                tool="artifact.write",
            ),
        ],
    )

    plan = HarnessRuntime._compile_plan(candidate, max_file_refs=2)

    assert [unit.unit_id for unit in plan.units] == ["read-one", "read-two", "write"]
    assert plan.units[-1].input_file_refs == [REF_ONE, REF_TWO]
    assert plan.units[-1].depends_on == ["read-one", "read-two"]
    assert "服务端按每轮最多 2 份文件" in plan.selection_reason


def test_unquoted_finding_creates_unavailable_resolution_instead_of_silent_drop() -> None:
    result = HarnessTaskResult(
        summary="没有逐字引用的发现",
        findings=[
            HarnessFinding(
                title="缺少原文",
                detail="模型只返回了摘要，没有返回可核对片段。",
                file_refs=[REF_TWO],
                evidence_quotes=[],
            )
        ],
        review_required=True,
    )
    resolution = HarnessRuntime._resolve_evidence_anchors(
        result,
        [{"file_ref": REF_TWO, "kind": "text", "text": "复核说明"}],
    )
    assert resolution.result is None
    assert resolution.evidence_resolutions[0].status == "unavailable"
    assert resolution.evidence_resolutions[0].label == "模型未提供逐字引用"


@pytest.mark.asyncio
async def test_decision_packet_round_trip_and_public_projection_hide_raw_tokens() -> None:
    runtime = HarnessRuntime(AmbiguousCatalog(), FakePlanner(), MixedEvidenceAnalyst())
    started = await runtime.start(
        "alice", start_request(idempotency_key="decision-packet-start-0001")
    )
    waiting = await wait_status(runtime, "alice", started.run.run_id, "waiting_input")
    assert waiting.decision_requests
    packet = waiting.decision_requests[0]
    assert packet.state == "open"
    assert packet.run_id == waiting.run_id
    restored = type(packet).model_validate(packet.model_dump(mode="json"))
    assert restored.decision_request_id == packet.decision_request_id
    public = runtime.public_snapshot(waiting)
    public_packet = public.decision_requests[0]
    assert public_packet.source_revision.startswith("rev-")
    assert public_packet.candidates[0].candidate_digest == ""
    assert public_packet.candidates[0].source_revision.startswith("rev-")
    await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="stop",
            idempotency_key="decision-packet-stop-0001",
            expected_version=waiting.version,
        ),
    )
    await wait_terminal(runtime, "alice", started.run.run_id)


@pytest.mark.asyncio
async def test_tampered_candidate_marks_resolution_rejected_without_resuming_run() -> None:
    runtime = HarnessRuntime(AmbiguousCatalog(), FakePlanner(), MixedEvidenceAnalyst())
    started = await runtime.start(
        "alice", start_request(idempotency_key="tamper-candidate-start-0001")
    )
    waiting = await wait_status(runtime, "alice", started.run.run_id, "waiting_input")
    resolution = waiting.rounds[0].next_step.evidence_resolutions[0]
    with pytest.raises(HarnessConflictError, match="候选位置不属于"):
        await runtime.control(
            "alice",
            started.run.run_id,
            AgentControlLoopControlRequest(
                command="decision",
                decision_action="accept",
                decision_request_id=waiting.decision_requests[0].decision_request_id,
                finding_id=resolution.finding_id,
                resolution_id=resolution.resolution_id,
                branch_id=resolution.branch_id,
                selected_candidate_id="candidate-000000000000",
                source_revision=resolution.source_revision,
                idempotency_key="tamper-candidate-control-0001",
                expected_version=waiting.version,
            ),
        )
    changed = await runtime.get("alice", started.run.run_id)
    assert changed.rounds[0].next_step.evidence_resolutions[0].status == "rejected"
    assert changed.events[-1].event_name == "evidence_resolution_rejected"
    await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="stop",
            idempotency_key="tamper-candidate-stop-0001",
            expected_version=changed.version,
        ),
    )
    await wait_terminal(runtime, "alice", started.run.run_id)


@pytest.mark.asyncio
async def test_stale_revision_is_actionable_and_cancel_closes_packet_without_rejecting_fact() -> None:
    runtime = HarnessRuntime(AmbiguousCatalog(), FakePlanner(), MixedEvidenceAnalyst())
    started = await runtime.start(
        "alice", start_request(idempotency_key="stale-revision-start-0001")
    )
    waiting = await wait_status(runtime, "alice", started.run.run_id, "waiting_input")
    resolution = waiting.rounds[0].next_step.evidence_resolutions[0]
    runtime.catalog.files[1]["sha256"] = "c" * 64
    with pytest.raises(HarnessConflictError, match="版本已经变化"):
        await runtime.control(
            "alice",
            started.run.run_id,
            AgentControlLoopControlRequest(
                command="decision",
                decision_action="accept",
                decision_request_id=waiting.decision_requests[0].decision_request_id,
                finding_id=resolution.finding_id,
                resolution_id=resolution.resolution_id,
                branch_id=resolution.branch_id,
                selected_candidate_id=resolution.candidates[0].candidate_id,
                source_revision="rev-0000000000000000",
                idempotency_key="stale-revision-control-0001",
                expected_version=waiting.version,
            ),
        )
    changed = await runtime.get("alice", started.run.run_id)
    assert changed.rounds[0].next_step.evidence_resolutions[0].status == "stale"
    assert changed.events[-1].event_name == "evidence_resolution_stale"
    await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="stop",
            idempotency_key="stale-revision-stop-0001",
            expected_version=changed.version,
        ),
    )
    await wait_terminal(runtime, "alice", started.run.run_id)


@pytest.mark.asyncio
async def test_cancel_keeps_ambiguous_resolution_but_closes_decision_packet() -> None:
    runtime = HarnessRuntime(AmbiguousCatalog(), FakePlanner(), MixedEvidenceAnalyst())
    started = await runtime.start(
        "alice", start_request(idempotency_key="cancel-decision-start-0001")
    )
    waiting = await wait_status(runtime, "alice", started.run.run_id, "waiting_input")
    resolution = waiting.rounds[0].next_step.evidence_resolutions[0]
    cancelled = await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="decision",
            decision_action="cancel",
            decision_request_id=waiting.decision_requests[0].decision_request_id,
            finding_id=resolution.finding_id,
            resolution_id=resolution.resolution_id,
            branch_id=resolution.branch_id,
            idempotency_key="cancel-decision-control-0001",
            expected_version=waiting.version,
        ),
    )
    assert cancelled.run.rounds[0].next_step.evidence_resolutions[0].status == "ambiguous"
    assert cancelled.run.decision_requests[0].state == "cancelled"
    assert cancelled.run.decision_records[-1].effect == "cancelled"
    await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="stop",
            idempotency_key="cancel-decision-stop-0001",
            expected_version=cancelled.run.version,
        ),
    )
    await wait_terminal(runtime, "alice", started.run.run_id)
