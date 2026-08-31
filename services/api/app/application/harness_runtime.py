"""Unified, file-backed Agent Harness runtime.

The runtime supports a bounded read-only Agent Control Loop: it freezes public
FORTE inputs, plans and analyzes in evidence-gated rounds, and may retry one
rejected plan while the frozen model-call budget allows it. It never executes
external actions or exposes benchmark task instructions, paths, hashes, or
hidden reasoning to the foreground.
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Literal, Protocol
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError, field_validator

from packages.contracts.harness_models import (
    AgentControlLoopArtifactVersion,
    AgentControlLoopArtifactFinding,
    AgentControlLoopEffectReceipt,
    AgentControlLoopBranch,
    AgentControlLoopBrief,
    AgentControlLoopBudget,
    AgentControlLoopCommit,
    AgentControlLoopContract,
    AgentControlLoopControlEvent,
    AgentControlLoopControlRequest,
    AgentControlLoopDecisionRecord,
    AgentControlLoopDecisionRequest,
    AgentControlLoopEvidenceAnchor,
    AgentControlLoopEvidenceCandidate,
    AgentControlLoopEvidenceGap,
    AgentControlLoopEvidenceResolution,
    AgentControlLoopFindingReview,
    AgentControlLoopNarrativeReconciliation,
    AgentControlLoopNextStep,
    AgentControlLoopOptions,
    AgentControlLoopRound,
    AgentControlLoopWorkspaceArtifact,
)
from services.api.app.application.run_workspace_artifact_store import (
    RunWorkspaceArtifactError,
    RunWorkspaceArtifactStore,
)
from services.api.app.application.scenario_effects import (
    ScenarioEffectEngine,
    ScenarioEffectExecution,
    summarize_artifact_check_groups,
)
from services.api.app.application.narrative_reconciliation import (
    build_verified_effect_context,
    reconcile_narrative,
)
from services.api.app.application.topology_admission import TopologyAdmission
from services.api.app.application.readonly_workers import (
    ReadonlyWorkerContribution,
    SharedArtifactMerge,
)
from services.api.app.application.workunit_ledger import (
    ContributionRecord,
    ContributionGateStatus,
    WorkUnitState,
    WorkUnitRecord,
    WorkerModelReceipt,
    public_contribution,
    public_work_unit,
)
from services.api.app.application.harness_storage import (
    HarnessStateStore,
    InMemoryHarnessStateStore,
    PostgresHarnessStateStore,
    StoredHarnessArtifactVersion,
    StoredHarnessIdempotency,
    StoredHarnessRun,
    StoredHarnessTaskCommit,
)
from services.api.app.application.task_ledger import (
    TaskLedgerConflict,
    TaskLedgerReceipt,
    TaskRecord,
)

runtime_logger = logging.getLogger("uvicorn.error")


class HarnessError(RuntimeError):
    pass


class HarnessNotFoundError(HarnessError):
    pass


class HarnessConflictError(HarnessError):
    pass


class HarnessPlanError(HarnessError):
    pass


class HarnessModelError(HarnessError):
    def __init__(
        self,
        message: str,
        *,
        called: bool = False,
        elapsed_ms: int = 0,
        model: str = "deepseek-v4-pro",
    ) -> None:
        super().__init__(message)
        self.called = called
        self.elapsed_ms = max(0, elapsed_ms)
        self.model = model


class HarnessStopped(HarnessError):
    """Internal signal raised after a user stop reaches a safe point."""


class HarnessBudgetExhausted(HarnessError):
    """Internal signal raised when another bounded model call is not allowed."""


HarnessSideEffect = Literal["none", "run_workspace_write", "external_action"]
HarnessArtifactType = Literal["analysis", "summary", "draft", "evidence"]


class HarnessPlanUnit(BaseModel):
    """Model-owned text and intent; identity and status remain server-owned."""

    model_config = ConfigDict(extra="forbid")

    unit_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=240)
    objective: str = Field(min_length=1, max_length=1_000)
    input_file_refs: list[str] = Field(min_length=1, max_length=100)
    depends_on: list[str] = Field(default_factory=list, max_length=100)
    tool: str = Field(min_length=1, max_length=120)
    requires_human_gate: bool = False
    side_effect: HarnessSideEffect = "none"
    artifact_name: str | None = Field(default=None, min_length=1, max_length=120)
    artifact_type: HarnessArtifactType | None = None

    @field_validator("unit_id", "tool", "side_effect")
    @classmethod
    def no_control_chars(cls, value: str) -> str:
        if any(ord(ch) < 32 for ch in value):
            raise ValueError("control characters are not allowed")
        return value

    @field_validator("artifact_name")
    @classmethod
    def artifact_name_is_server_safe(cls, value: str | None) -> str | None:
        if value is None:
            return None
        # Artifact names are logical names in the run workspace, never paths.
        if any(token in value for token in ("/", "\\", ":", "..")) or any(
            ord(ch) < 32 for ch in value
        ):
            raise ValueError("artifact_name must be a logical name, not a file path")
        return value


class HarnessPlanCandidateUnit(BaseModel):
    """Model-owned work intent before server policy compilation."""

    model_config = ConfigDict(extra="forbid")

    unit_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=240)
    objective: str = Field(min_length=1, max_length=1_000)
    input_file_refs: list[str] = Field(min_length=1, max_length=100)
    depends_on: list[str] = Field(default_factory=list, max_length=100)
    tool: str = Field(min_length=1, max_length=120)
    requires_human_gate: bool = False
    artifact_name: str | None = Field(default=None, min_length=1, max_length=120)
    artifact_type: HarnessArtifactType | None = None

    @field_validator("unit_id", "tool")
    @classmethod
    def no_control_chars(cls, value: str) -> str:
        if any(ord(ch) < 32 for ch in value):
            raise ValueError("control characters are not allowed")
        return value

    @field_validator("artifact_name")
    @classmethod
    def artifact_name_is_server_safe(cls, value: str | None) -> str | None:
        return HarnessPlanUnit.artifact_name_is_server_safe(value)


class HarnessPlanCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1_000)
    selection_reason: str = Field(
        default="根据任务目标选择最相关的最小证据集合。",
        min_length=1,
        max_length=1_000,
    )
    units: list[HarnessPlanCandidateUnit] = Field(min_length=1, max_length=12)


class HarnessPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1_000)
    selection_reason: str = Field(min_length=1, max_length=1_000)
    units: list[HarnessPlanUnit] = Field(min_length=1, max_length=12)


class HarnessModelReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    called: bool
    model: str
    elapsed_ms: int = Field(ge=0)
    output_used: bool


class HarnessEvidenceQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_ref: str
    role: Literal["expected", "observed", "support", "contradiction", "context"]
    label: str = Field(min_length=1, max_length=120)
    quote: str = Field(min_length=4, max_length=600)


class HarnessFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str | None = Field(default=None, pattern=r"^finding-[0-9a-f]{12}$")
    plan_unit_id: str | None = Field(default=None, min_length=1, max_length=120)
    affected_branch_ids: list[str] = Field(default_factory=list, max_length=12)
    title: str = Field(min_length=1, max_length=240)
    detail: str = Field(min_length=1, max_length=2_000)
    fact_summary: str | None = Field(default=None, max_length=500)
    impact: str | None = Field(default=None, max_length=500)
    file_refs: list[str] = Field(min_length=1, max_length=100)
    evidence_quotes: list[HarnessEvidenceQuote] = Field(default_factory=list, max_length=6)
    evidence_anchors: list[AgentControlLoopEvidenceAnchor] = Field(
        default_factory=list, max_length=6
    )
    evidence_resolutions: list[AgentControlLoopEvidenceResolution] = Field(
        default_factory=list, max_length=6
    )
    review: AgentControlLoopFindingReview | None = None


class HarnessTaskResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=3_000)
    findings: list[HarnessFinding] = Field(min_length=1, max_length=96)
    follow_ups: list[str] = Field(default_factory=list, max_length=8)
    review_required: Literal[True] = True


class HarnessNarrativeAuditDraft(BaseModel):
    """Private parsed model draft retained for audit, never projected publicly."""

    model_config = ConfigDict(extra="forbid")

    round_number: int = Field(ge=1, le=24)
    outcome_revision: str | None = Field(default=None, max_length=80)
    result: HarnessTaskResult
    reconciliation: AgentControlLoopNarrativeReconciliation
    recorded_at: datetime


class HarnessEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int = Field(ge=1)
    event_name: str = Field(min_length=1, max_length=120)
    occurred_at: datetime
    status: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=500)
    details: dict[str, Any] = Field(default_factory=dict)


class HarnessWorkspaceArtifactRecord(AgentControlLoopWorkspaceArtifact):
    """Private persisted record; the full digest never enters the public projection."""

    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class HarnessRunSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    task_id: str = Field(default="task-000000000000", pattern=r"^task-[0-9a-f]{12}$")
    task_version: int = Field(default=1, ge=1)
    run_sequence: int = Field(default=1, ge=1, le=10_000)
    parent_run_id: str | None = Field(default=None, pattern=r"^harness:[0-9a-f]{32}$")
    continuation_reason: str | None = Field(default=None, max_length=240)
    carried_branch_id: str | None = Field(default=None, pattern=r"^branch-[0-9a-f]{12}$")
    base_artifact_version: int | None = Field(default=None, ge=1, le=24)
    base_task_commit: str | None = Field(default=None, pattern=r"^commit-[0-9a-f]{12}$")
    workspace_revision: str = Field(default="unknown", min_length=1, max_length=120)
    recheck_file_refs: list[str] = Field(default_factory=list, max_length=24)
    source_revision_changed: bool = False
    owner_id: str
    workspace_id: Literal["forte-public-office"] = "forte-public-office"
    status: str
    version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime
    last_event_sequence: int = Field(default=0, ge=0)
    source_documents: list[dict[str, Any]] = Field(default_factory=list)
    selection_reason: str | None = None
    instruction: str = Field(min_length=1, max_length=2_000)
    instruction_source: Literal["user"] = "user"
    contract: AgentControlLoopContract
    budget: AgentControlLoopBudget
    rounds: list[AgentControlLoopRound] = Field(default_factory=list, max_length=24)
    current_round: int = Field(default=0, ge=0, le=24)
    control_state: Literal[
        "running",
        "pause_requested",
        "paused",
        "stop_requested",
        "stopped",
    ] = "running"
    control_events: list[AgentControlLoopControlEvent] = Field(default_factory=list, max_length=100)
    decision_records: list[AgentControlLoopDecisionRecord] = Field(
        default_factory=list, max_length=100
    )
    decision_requests: list[AgentControlLoopDecisionRequest] = Field(
        default_factory=list, max_length=100
    )
    branches: list[AgentControlLoopBranch] = Field(default_factory=list, max_length=36)
    active_branch_id: str | None = Field(default=None, pattern=r"^branch-[0-9a-f]{12}$")
    artifact_versions: list[AgentControlLoopArtifactVersion] = Field(
        default_factory=list, max_length=24
    )
    workspace_artifacts: list[HarnessWorkspaceArtifactRecord] = Field(
        default_factory=list, max_length=24
    )
    effect_receipts: list[AgentControlLoopEffectReceipt] = Field(
        default_factory=list, max_length=15
    )
    commits: list[AgentControlLoopCommit] = Field(default_factory=list, max_length=20)
    last_commit: AgentControlLoopCommit | None = None
    brief: AgentControlLoopBrief | None = None
    plan: HarnessPlan | None = None
    model_receipt: HarnessModelReceipt | None = None
    analysis_receipt: HarnessModelReceipt | None = None
    result: HarnessTaskResult | None = None
    narrative_reconciliation: AgentControlLoopNarrativeReconciliation | None = None
    narrative_audit_drafts: list[HarnessNarrativeAuditDraft] = Field(
        default_factory=list, max_length=24
    )
    validation_errors: list[str] = Field(default_factory=list)
    events: list[HarnessEvent] = Field(default_factory=list)
    # Demo 2 is projected into the same unified Run cockpit.  Admission is a
    # server fact; worker execution remains explicitly confirmed and bounded.
    topology_admission: TopologyAdmission | None = None
    worker_runs: list[ReadonlyWorkerContribution] = Field(default_factory=list, max_length=36)
    shared_artifacts: list[SharedArtifactMerge] = Field(default_factory=list, max_length=24)
    worker_idempotency: dict[str, str] = Field(default_factory=dict, max_length=12)
    # These are the durable execution ledger projection.  Branch remains the
    # authority for plan, dependency and evidence-gate facts.
    work_units: list[WorkUnitRecord] = Field(default_factory=list, max_length=36)
    contributions: list[ContributionRecord] = Field(default_factory=list, max_length=96)


class HarnessRunStart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: Literal["forte-public-office"] = "forte-public-office"
    idempotency_key: str = Field(min_length=8, max_length=160)
    expected_version: int = Field(default=1, ge=1)
    instruction: str = Field(min_length=3, max_length=2_000)
    loop: AgentControlLoopOptions = Field(default_factory=AgentControlLoopOptions)

    @field_validator("instruction")
    @classmethod
    def validate_instruction(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3 or any(
            ord(character) < 32 and character not in "\n\t" for character in normalized
        ):
            raise ValueError("instruction contains invalid content")
        return normalized


class HarnessRunStartResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run: HarnessRunSnapshot
    replayed: bool = False


class HarnessContinuationRequest(BaseModel):
    """Owner command for a terminal Run's one-Branch continuation."""

    model_config = ConfigDict(extra="forbid")

    branch_id: str = Field(pattern=r"^branch-[0-9a-f]{12}$")
    idempotency_key: str = Field(min_length=8, max_length=160)
    expected_version: int = Field(ge=1)
    expected_task_version: StrictInt = Field(ge=1)
    instruction: str | None = Field(default=None, min_length=3, max_length=2_000)
    loop: AgentControlLoopOptions | None = None


class HarnessReadonlyWorkersRequest(BaseModel):
    """Explicit cockpit confirmation for at most three admitted Branches."""

    model_config = ConfigDict(extra="forbid")

    # Optional for the cockpit: the Scheduler's ready_branch_ids are the
    # authority when the client does not provide an explicit subset.
    branch_ids: list[str] = Field(default_factory=list, max_length=3)
    idempotency_key: str = Field(min_length=8, max_length=160)
    expected_version: int = Field(ge=1)
    confirmed: bool = False


class PublicHarnessPlanUnit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_id: str
    title: str
    objective: str
    input_file_refs: list[str]
    depends_on: list[str]
    tool: str
    requires_human_gate: bool
    side_effect: HarnessSideEffect
    artifact_name: str | None = None
    artifact_type: HarnessArtifactType | None = None


class PublicHarnessPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    selection_reason: str
    units: list[PublicHarnessPlanUnit]


class PublicHarnessRunSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    task_id: str = "task-000000000000"
    task_version: int = 1
    run_sequence: int = 1
    parent_run_id: str | None = None
    continuation_reason: str | None = None
    carried_branch_id: str | None = None
    base_artifact_version: int | None = None
    base_task_commit: str | None = None
    workspace_revision: str = "unknown"
    recheck_file_refs: list[str] = Field(default_factory=list, max_length=24)
    source_revision_changed: bool = False
    owner_id: str
    workspace_id: Literal["forte-public-office"]
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    last_event_sequence: int
    source_documents: list[dict[str, Any]]
    selection_reason: str | None
    instruction: str
    instruction_source: Literal["user"]
    contract: AgentControlLoopContract
    budget: AgentControlLoopBudget
    rounds: list[AgentControlLoopRound]
    current_round: int
    control_state: str
    control_events: list[AgentControlLoopControlEvent]
    decision_records: list[AgentControlLoopDecisionRecord]
    decision_requests: list[AgentControlLoopDecisionRequest]
    branches: list[AgentControlLoopBranch]
    active_branch_id: str | None
    artifact_versions: list[AgentControlLoopArtifactVersion]
    workspace_artifacts: list[AgentControlLoopWorkspaceArtifact]
    effect_receipts: list[AgentControlLoopEffectReceipt]
    commits: list[AgentControlLoopCommit]
    last_commit: AgentControlLoopCommit | None
    brief: AgentControlLoopBrief | None
    plan: PublicHarnessPlan | None
    model_receipt: HarnessModelReceipt | None
    analysis_receipt: HarnessModelReceipt | None
    result: HarnessTaskResult | None
    narrative_reconciliation: AgentControlLoopNarrativeReconciliation | None
    validation_errors: list[str]
    events: list[HarnessEvent]
    topology_admission: TopologyAdmission | None = None
    worker_runs: list[ReadonlyWorkerContribution] = Field(default_factory=list, max_length=36)
    shared_artifacts: list[SharedArtifactMerge] = Field(default_factory=list, max_length=24)
    work_units: list[dict[str, Any]] = Field(default_factory=list, max_length=36)
    contributions: list[dict[str, Any]] = Field(default_factory=list, max_length=96)


class PublicHarnessTaskLineageItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    run_sequence: int
    parent_run_id: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class PublicHarnessTaskSnapshot(BaseModel):
    """Owner-scoped task projection derived from the current Run snapshot."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    task_version: int
    current_run_id: str
    run_sequence: int
    parent_run_id: str | None
    workspace_revision: str
    status: str
    created_at: datetime
    updated_at: datetime
    current_artifact_id: str | None
    current_artifact_version: int | None
    current_commit_id: str | None
    lineage: list[PublicHarnessTaskLineageItem] = Field(default_factory=list, max_length=100)
    lineage_total: int = Field(default=0, ge=0)
    lineage_truncated: bool = False


class PublicHarnessRunStartResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run: PublicHarnessRunSnapshot
    replayed: bool = False


class HarnessControlResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run: HarnessRunSnapshot
    replayed: bool = False


class PublicHarnessControlResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run: PublicHarnessRunSnapshot
    replayed: bool = False


class HarnessWorkspaceCatalog(Protocol):
    """Small adapter boundary used by the runtime and easy to fake in tests."""

    def public_workspace(self) -> dict[str, Any]: ...

    def internal_workspace(self) -> dict[str, Any]: ...

    def public_file(self, file_ref: str) -> dict[str, Any]: ...

    def agent_file_inputs(self, file_refs: list[str]) -> list[dict[str, Any]]: ...


class HarnessPlanner(Protocol):
    async def plan(
        self, *, scenario: dict[str, Any], files: list[dict[str, Any]]
    ) -> HarnessPlanCandidate | HarnessPlan: ...


class HarnessAnalyst(Protocol):
    async def analyze(
        self,
        *,
        instruction: str,
        plan: HarnessPlan,
        files: list[dict[str, Any]],
        validation_feedback: str | None = None,
    ) -> HarnessTaskResult: ...


class OpenAICompatibleHarnessPlanner:
    """Strict JSON planner. It never receives server-owned IDs as writable fields."""

    MODEL = "deepseek-v4-pro"

    def __init__(
        self, *, base_url: str, api_key: str, model: str = MODEL, timeout: float = 60
    ) -> None:
        if model != self.MODEL:
            raise ValueError(f"Harness 只允许使用 {self.MODEL}")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def plan(
        self, *, scenario: dict[str, Any], files: list[dict[str, Any]]
    ) -> HarnessPlanCandidate:
        if not self.base_url or not self.api_key:
            raise HarnessModelError(
                "LLM_BASE_URL 和 LLM_API_KEY 尚未配置",
                called=False,
                model=self.model,
            )
        schema = json.dumps(HarnessPlanCandidate.model_json_schema(), ensure_ascii=False)
        system = (
            "你是企业办公 Agent Control Loop 的规划器。用户给出目标后，你要先研究整个公开办公资料库索引，"
            "再自主选择本轮最相关的最小证据集合并生成可执行 DAG。"
            "只输出一个符合 JSON Schema 的 JSON 对象。只能引用 files 中出现的 file_ref；tool 必须来自 allowlisted_tools；"
            "每轮引用的不同文件数不得超过 scenario.control_loop.max_files_this_round；优先选择最能回答当前问题的最小证据集合。"
            "如果 scenario.control_loop.validation_feedback 非空，必须先按反馈修正；文件数超限时只保留优先级最高的文件。"
            "如果 scenario.control_loop.evidence_recheck 为 true，files 中全部文件都是用户已确认继续核对的缺失证据，计划必须全部覆盖。"
            "selection_reason 必须用业务语言说明为什么选择这些文件，以及它们与目标的关系。"
            "输入文件永远只读，禁止猜测或输出源文件路径、哈希或任意本地路径。"
            "读取文件使用 file.read/table.inspect/evidence.verify；生成结果使用 artifact.write。可以提供不含路径的逻辑 artifact_name 与 artifact_type；缺省时由服务端生成。"
            "只选择工作意图和 tool，不得输出 side_effect；写入范围、外部动作范围与强制人工确认由服务端根据能力确定。"
            "action.preview 只能表示待审查的外部动作候选，本阶段不执行任何工具。不得生成身份、来源、状态、执行结果、Permit 或隐藏推理。"
            "禁止输出 Markdown、代码围栏或额外字段。JSON Schema：" + schema
        )
        user = json.dumps({"scenario": scenario, "files": files}, ensure_ascii=False)
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "max_tokens": 3_000,
            "thinking": {"type": "disabled"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        started = perf_counter()
        request_started = False
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                request_started = True
                response = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
                if response.status_code == 400 and "response_format" in response.text.lower():
                    payload.pop("response_format", None)
                    request_started = True
                    response = await client.post(
                        f"{self.base_url}/chat/completions", json=payload, headers=headers
                    )
                response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("model content is not text")
            content = content.strip()
            if content.startswith("```"):
                content = (
                    content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                )
            return HarnessPlanCandidate.model_validate(json.loads(content))
        except (
            httpx.HTTPError,
            KeyError,
            IndexError,
            TypeError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise HarnessModelError(
                "模型未返回合法的 Harness DAG JSON",
                called=request_started,
                elapsed_ms=round((perf_counter() - started) * 1000),
                model=self.model,
            ) from exc


class OpenAICompatibleHarnessAnalyst:
    """Cited read-only analyst over server-projected public file contents."""

    MODEL = "deepseek-v4-pro"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str = MODEL,
        timeout: float = 60,
    ) -> None:
        if model != self.MODEL:
            raise ValueError(f"Harness 只允许使用 {self.MODEL}")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def analyze(
        self,
        *,
        instruction: str,
        plan: HarnessPlan,
        files: list[dict[str, Any]],
        verified_effect_context: dict[str, Any] | None = None,
        validation_feedback: str | None = None,
    ) -> HarnessTaskResult:
        if not self.base_url or not self.api_key:
            raise HarnessModelError(
                "LLM_BASE_URL 和 LLM_API_KEY 尚未配置",
                called=False,
                model=self.model,
            )
        schema = json.dumps(HarnessTaskResult.model_json_schema(), ensure_ascii=False)
        system = (
            "你是企业办公数据分析 Agent。只根据用户指令、已通过校验的计划和 files 中的公开办公数据回答。"
            "每个 finding 必须引用 files 中真实存在的 file_ref；不允许引用路径、哈希、任务标准答案或未提供的数据。"
            "每个 finding.plan_unit_id 必须填写 validated_plan.units 中直接产生该发现的 unit_id；"
            "即使多个任务单元共享同一文件，也不能省略或猜测所属单元。"
            "每个 finding 只描述一个可处置问题。title 应是短标题；fact_summary 用不超过两句话说明发生了什么；impact 单独说明不处理的影响，"
            "不要把多个冲突、推测和建议塞进同一长段 detail。"
            "每个 finding.evidence_quotes 必须给出 1 到 6 个可在对应文件中逐字找到的短片段，至少精确定位一处依据；"
            "role 用 expected 表示设计或规则预期，用 observed 表示实际记录，用 support 表示支持结论，用 contradiction 表示冲突，用 context 表示上下文。"
            "表格 quote 应组合足以唯一定位一行的连续单元格文本；文本 quote 应选可唯一定位的连续原文，不得改写。"
            "必须服从用户目标中的日期、对象、部门、版本和其他筛选条件；筛选范围外的记录不得作为 finding 或人工决策。"
            "finding.evidence_anchors 必须返回空数组；位置、行号和展示摘录由服务端验证原文后生成。"
            "只有存在真实业务冲突且必须由人选择口径时才输出 finding.review；其余情况必须省略 review。"
            "若规则已明确给出关键词、优先级或覆盖关系，不得把按规则即可确定的结果升级为人工决策。"
            "存在 contradiction 时 requires_human_decision 必须为 true，提供 2 个 A/B 互斥选项、推荐项、推荐理由，"
            "以及用户确认后 Agent 将执行的下一步。"
            "每个 option.next_instruction 必须是一条可作为新只读 Control Loop 目标的完整指令；只能核对资料、形成修改建议或待办，不能声称直接改文件。"
            "若 validation_feedback 非空，上一候选未通过原文定位；保持原任务不变，并改用更长、只出现一次的连续原文重新生成全部 findings。"
            "若 verified_effect_context 非空，其中 facts 是服务端从批准原始字节全量复算并通过 Artifact Verifier 的当前权威事实；"
            "files 中的 bounded Preview 只用于逐字引用，不得以 Preview 行数否定、覆盖或降低 facts，"
            "不得把已经完成的全量计算再次列为 follow_up，也不得把 facts 标注为缺少样本。"
            "当 facts.suggestion_status 表示没有批准的具体方案来源时，只能说明待业务负责人补充或批准，"
            "不得把自拟具体方案写成当前结论。"
            "只能完成只读分析，不得声称发送、写入、审批或调用外部系统。"
            "不要输出思维链、内部推理、Prompt、工具日志或 Markdown 代码围栏。"
            "覆盖通过范围内所有有业务意义的 findings；遵守服务端 schema 与本轮预算上限，不要为了截断而省略任何发现。没有必要时不要输出默认值字段。"
            "每条 finding 只输出 plan_unit_id、title、detail、fact_summary、impact、file_refs、evidence_quotes，"
            "仅在人必须决策时再加 review；不要输出 finding_id、affected_branch_ids、evidence_anchors 或 evidence_resolutions。"
            "结论存在不确定性时直接写入 summary。follow_ups 应给出基于当前证据、可由用户确认后作为新任务启动的具体推进建议，"
            "不要写成泛化的‘请人工复核’。review_required 必须为 true。"
            "只输出符合 JSON Schema 的 JSON 对象。JSON Schema：" + schema
        )
        user = json.dumps(
            {
                "instruction": instruction,
                "validated_plan": plan.model_dump(mode="json"),
                "files": files,
                "verified_effect_context": verified_effect_context,
                "validation_feedback": validation_feedback,
            },
            ensure_ascii=False,
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "max_tokens": 5_000,
            "thinking": {"type": "disabled"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        started = perf_counter()
        request_started = False
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                request_started = True
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if response.status_code == 400 and "response_format" in response.text.lower():
                    payload.pop("response_format", None)
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                    )
                response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("model content is not text")
            content = content.strip()
            if content.startswith("```"):
                content = (
                    content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                )
            return HarnessTaskResult.model_validate(json.loads(content))
        except (
            httpx.HTTPError,
            KeyError,
            IndexError,
            TypeError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise HarnessModelError(
                "模型未返回合法的只读分析结果",
                called=request_started,
                elapsed_ms=round((perf_counter() - started) * 1000),
                model=self.model,
            ) from exc


@dataclass
class _Run:
    snapshot: HarnessRunSnapshot
    condition: asyncio.Condition
    active_elapsed_base_ms: int = 0
    active_since_perf: float | None = None
    resume_status: str | None = None


@dataclass(frozen=True)
class _IdempotentStart:
    digest: str
    result: HarnessRunStartResult


@dataclass(frozen=True)
class _IdempotentControl:
    digest: str
    result: HarnessControlResult


@dataclass(frozen=True)
class _EvidenceResolution:
    result: HarnessTaskResult | None
    rejected_finding_count: int
    rejected_file_refs: tuple[str, ...]
    evidence_resolutions: tuple[AgentControlLoopEvidenceResolution, ...]
    out_of_scope_finding_count: int = 0
    downgraded_review_count: int = 0


class HarnessRuntime:
    """Owner/version/idempotent Agent Control Loop with durable snapshot support."""

    ALLOWED_STATUSES = {
        "queued",
        "indexing",
        "planning",
        "validating",
        "ready_to_execute",
        "analyzing",
        "verifying",
        "waiting_input",
        "paused",
        "completed",
        "stopped",
        "failed",
    }
    MAX_UNITS = 12

    def __init__(
        self,
        catalog: HarnessWorkspaceCatalog,
        planner: HarnessPlanner,
        analyst: HarnessAnalyst | None = None,
        state_store: HarnessStateStore | None = None,
        effect_engine: ScenarioEffectEngine | None = None,
        artifact_store: RunWorkspaceArtifactStore | None = None,
    ) -> None:
        self.catalog = catalog
        self.planner = planner
        self.analyst = analyst
        self.state_store = state_store or InMemoryHarnessStateStore()
        # HarnessStateStore is the sole aggregate boundary for the task
        # ledger, Run snapshot and command receipts.
        self.effect_engine = effect_engine
        self.artifact_store = artifact_store
        self._runs: dict[tuple[str, str], _Run] = {}
        self._idempotent: dict[tuple[str, str], _IdempotentStart] = {}
        self._control_idempotent: dict[tuple[str, str], _IdempotentControl] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._effect_inflight: set[tuple[str, str, str]] = set()
        self._lock = asyncio.Lock()

    @property
    def backend_name(self) -> str:
        return self.state_store.backend_name

    async def setup(self) -> None:
        """Restore snapshots, but never replay an interrupted model call automatically."""

        await self.state_store.setup()
        now = datetime.now(timezone.utc)
        terminal_statuses = {"ready_to_execute", "completed", "stopped", "failed"}
        stored_runs = await self.state_store.load_runs()
        # Snapshots written before Task Ledger V1 did not carry task_version.
        # Upgrade that field only while restoring durable state; request paths
        # must never synthesize or repair a missing ledger entry.
        normalized_runs: list[tuple[StoredHarnessRun, bool]] = []
        for record in stored_runs:
            raw_snapshot = record.snapshot
            snapshot = HarnessRunSnapshot.model_validate(raw_snapshot)
            migrated = "task_version" not in raw_snapshot
            if migrated:
                snapshot = snapshot.model_copy(update={"task_version": snapshot.run_sequence})
            if record.owner_id != snapshot.owner_id:
                raise HarnessError("持久化 Run owner 与快照不一致")
            normalized_runs.append(
                (
                    StoredHarnessRun(
                        owner_id=record.owner_id,
                        run_id=record.run_id,
                        snapshot=snapshot.model_dump(mode="json"),
                        resume_status=record.resume_status,
                    ),
                    migrated,
                )
            )
        stored_runs = [record for record, _ in normalized_runs]
        migrated_run_ids = {
            (record.owner_id, record.run_id)
            for record, migrated in normalized_runs
            if migrated
        }
        stored_task_records = (
            await self.state_store.load_task_records()
            if hasattr(self.state_store, "load_task_records")
            else []
        )
        existing_task_keys = {
            (item.owner_id, item.task_id) for item in stored_task_records
        }
        runs_by_task: dict[tuple[str, str], list[HarnessRunSnapshot]] = {}
        for stored in stored_runs:
            snapshot = HarnessRunSnapshot.model_validate(stored.snapshot)
            if stored.run_id != snapshot.run_id:
                raise HarnessError("持久化 Run 主键与快照不一致")
            runs_by_task.setdefault((stored.owner_id, snapshot.task_id), []).append(snapshot)
        for task in stored_task_records:
            task_runs = sorted(
                runs_by_task.get((task.owner_id, task.task_id), []),
                key=lambda item: item.run_sequence,
            )
            if not task_runs:
                raise HarnessError("任务台账指向不存在的 Run")
            sequences = [item.run_sequence for item in task_runs]
            task_versions = [item.task_version for item in task_runs]
            if sequences != list(range(1, len(sequences) + 1)):
                raise HarnessError("任务台账的 Run sequence 不连续")
            if task_versions != sequences:
                raise HarnessError("任务台账的 task_version 与 Run sequence 不一致")
            if task_runs[0].run_sequence != 1 or task_runs[0].parent_run_id is not None:
                raise HarnessError("任务台账 Run 根节点不一致")
            current = task_runs[-1]
            if (
                current.run_id != task.current_run_id
                or current.task_id != task.task_id
                or current.owner_id != task.owner_id
                or current.task_version != task.task_version
                or current.run_sequence != task.run_sequence
                or current.parent_run_id != task.parent_run_id
            ):
                raise HarnessError("任务台账 current Run 指针不一致")
            for previous, following in zip(task_runs, task_runs[1:], strict=False):
                if following.parent_run_id != previous.run_id:
                    raise HarnessError("任务台账 Run lineage 不连续")
        for key, task_runs in runs_by_task.items():
            if key in existing_task_keys:
                continue
            ordered = sorted(task_runs, key=lambda item: item.run_sequence)
            if [item.run_sequence for item in ordered] != list(range(1, len(ordered) + 1)):
                raise HarnessError("无法安全回填任务台账：Run sequence 不连续")
            if [item.task_version for item in ordered] != [item.run_sequence for item in ordered]:
                raise HarnessError("无法安全回填任务台账：task_version 与 Run sequence 不一致")
            if ordered[0].run_sequence != 1 or ordered[0].parent_run_id is not None:
                raise HarnessError("无法安全回填任务台账：Run 根节点不一致")
            for previous, following in zip(ordered, ordered[1:], strict=False):
                if following.parent_run_id != previous.run_id:
                    raise HarnessError("无法安全回填任务台账：Run lineage 不连续")
        backfill_by_task: dict[tuple[str, str], StoredHarnessRun] = {}
        for stored in stored_runs:
            snapshot = HarnessRunSnapshot.model_validate(stored.snapshot)
            key = (stored.owner_id, snapshot.task_id)
            previous = backfill_by_task.get(key)
            if previous is None:
                backfill_by_task[key] = stored
                continue
            previous_snapshot = HarnessRunSnapshot.model_validate(previous.snapshot)
            if snapshot.run_sequence == previous_snapshot.run_sequence:
                raise HarnessError(
                    "无法安全回填任务台账：同一任务存在重复 run_sequence"
                )
            if snapshot.run_sequence > previous_snapshot.run_sequence:
                backfill_by_task[key] = stored
        async with self._lock:
            for record in stored_runs:
                snapshot = HarnessRunSnapshot.model_validate(record.snapshot)
                resume_status = record.resume_status
                if snapshot.status not in terminal_statuses:
                    recovered_work_units = []
                    for work_unit in snapshot.work_units:
                        if work_unit.state in {WorkUnitState.RESERVED, WorkUnitState.RUNNING}:
                            recovered_work_units.append(
                                work_unit.transition(
                                    WorkUnitState.FAILED,
                                    error="checkpoint recovery stopped an in-flight Worker; automatic replay disabled",
                                )
                            )
                        else:
                            recovered_work_units.append(work_unit)
                    completed_rounds = [
                        item for item in snapshot.rounds if item.status == "completed"
                    ]
                    completed_round_numbers = {item.round_number for item in completed_rounds}
                    recovered_branches = [
                        item
                        for item in snapshot.branches
                        if item.round_number in completed_round_numbers
                    ]
                    recovered_branch_ids = {item.branch_id for item in recovered_branches}
                    recovered_status = (
                        "waiting_input" if snapshot.status == "waiting_input" else "paused"
                    )
                    event = HarnessEvent(
                        sequence=snapshot.last_event_sequence + 1,
                        event_name="checkpoint_recovered",
                        occurred_at=now,
                        status=recovered_status,
                        message=(
                            "已从持久化检查点恢复；未完成的模型调用不会自动重放，"
                            "请确认后从安全点继续。"
                        ),
                        details={
                            "completed_rounds": len(completed_rounds),
                            "automatic_model_replay": False,
                            "in_flight_work_units": [
                                item.work_unit_id
                                for item in snapshot.work_units
                                if item.state in {WorkUnitState.RESERVED, WorkUnitState.RUNNING}
                            ],
                        },
                    )
                    last_round = completed_rounds[-1] if completed_rounds else None
                    snapshot = snapshot.model_copy(
                        update={
                            "status": recovered_status,
                            "control_state": "paused",
                            "rounds": completed_rounds,
                            "branches": recovered_branches,
                            "active_branch_id": snapshot.active_branch_id
                            if snapshot.active_branch_id in recovered_branch_ids
                            else None,
                            "current_round": len(completed_rounds),
                            "plan": HarnessPlan.model_validate(last_round.plan)
                            if last_round and last_round.plan
                            else None,
                            "model_receipt": HarnessModelReceipt.model_validate(
                                last_round.model_receipt
                            )
                            if last_round and last_round.model_receipt
                            else None,
                            "analysis_receipt": HarnessModelReceipt.model_validate(
                                last_round.analysis_receipt
                            )
                            if last_round and last_round.analysis_receipt
                            else None,
                            "events": [*snapshot.events, event],
                            "last_event_sequence": event.sequence,
                            "work_units": recovered_work_units,
                            "version": snapshot.version + 1,
                            "updated_at": now,
                        }
                    )
                    resume_status = "planning"
                run = _Run(
                    snapshot=snapshot,
                    condition=asyncio.Condition(),
                    active_elapsed_base_ms=snapshot.budget.elapsed_ms,
                    active_since_perf=None,
                    resume_status=resume_status,
                )
                self._runs[(record.owner_id, record.run_id)] = run
                # Conservative backfill for snapshots created before the
                # task ledger existed.  This is the only migration point.
                if (
                    (record.owner_id, snapshot.task_id) not in existing_task_keys
                    and backfill_by_task.get((record.owner_id, snapshot.task_id))
                    is record
                ):
                    await self._task_create(self._task_record_from_snapshot(snapshot))
                if snapshot.status not in terminal_statuses or (record.owner_id, record.run_id) in migrated_run_ids:
                    await self._persist_locked(run)

            for record in await self.state_store.load_idempotency():
                if record.kind == "start":
                    self._idempotent[(record.owner_id, record.idempotency_key)] = _IdempotentStart(
                        digest=record.digest,
                        result=HarnessRunStartResult.model_validate(record.result),
                    )
                else:
                    self._control_idempotent[(record.owner_id, record.idempotency_key)] = (
                        _IdempotentControl(
                            digest=record.digest,
                            result=HarnessControlResult.model_validate(record.result),
                        )
                    )

    async def close(self) -> None:
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await self.state_store.close()

    async def list(self, owner_id: str) -> list[HarnessRunSnapshot]:
        async with self._lock:
            snapshots = [
                run.snapshot.model_copy(deep=True)
                for (candidate_owner, _), run in self._runs.items()
                if candidate_owner == owner_id
            ]
        return sorted(snapshots, key=lambda item: item.updated_at, reverse=True)

    async def _task_get(self, owner_id: str, task_id: str) -> TaskRecord | None:
        try:
            value = await self.state_store.get_task_record(owner_id, task_id)
            return TaskRecord.model_validate(value) if value is not None else None
        except Exception as exc:
            raise HarnessError("任务台账读取失败") from exc

    async def _task_create(self, task: TaskRecord) -> TaskRecord:
        return await self.state_store.create_task_record(task)

    async def _persist_locked(
        self,
        run: _Run,
        idempotency: StoredHarnessIdempotency | None = None,
        artifact_version: AgentControlLoopArtifactVersion | None = None,
        task_commit: AgentControlLoopCommit | None = None,
    ) -> StoredHarnessIdempotency | None:
        stored_artifact = None
        if artifact_version is not None:
            payload = artifact_version.model_dump(mode="json")
            stored_artifact = StoredHarnessArtifactVersion(
                owner_id=run.snapshot.owner_id,
                run_id=run.snapshot.run_id,
                artifact_id=artifact_version.artifact_id,
                version=artifact_version.version,
                payload_digest=self._payload_digest(payload),
                payload=payload,
            )
        stored_commit = None
        if task_commit is not None:
            payload = task_commit.model_dump(mode="json")
            stored_commit = StoredHarnessTaskCommit(
                owner_id=run.snapshot.owner_id,
                run_id=run.snapshot.run_id,
                commit_id=task_commit.commit_id,
                payload_digest=self._payload_digest(payload),
                payload=payload,
            )
        return await self.state_store.commit(
            StoredHarnessRun(
                owner_id=run.snapshot.owner_id,
                run_id=run.snapshot.run_id,
                snapshot=run.snapshot.model_dump(mode="json"),
                resume_status=run.resume_status,
            ),
            idempotency,
            stored_artifact,
            stored_commit,
        )

    @staticmethod
    def _payload_digest(payload: dict[str, Any]) -> str:
        return hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()

    def _schedule_run(
        self,
        owner_id: str,
        run_id: str,
        workspace: dict[str, Any],
        instruction: str,
    ) -> None:
        active = self._tasks.get(run_id)
        if active is not None and not active.done():
            return
        task = asyncio.create_task(self._run(owner_id, run_id, workspace, instruction))
        self._tasks[run_id] = task
        task.add_done_callback(lambda done, rid=run_id: self._tasks.pop(rid, None))

    def get_workspace(self) -> dict[str, Any]:
        try:
            return self.catalog.public_workspace()
        except Exception as exc:
            raise HarnessError("FORTE 办公资料库暂时无法读取") from exc

    def get_file_preview(self, file_ref: str) -> dict[str, Any]:
        try:
            return self.catalog.public_file(file_ref)
        except KeyError as exc:
            raise HarnessNotFoundError("文件不存在") from exc

    async def get_workspace_artifact(
        self, owner_id: str, run_id: str, artifact_id: str
    ) -> tuple[AgentControlLoopWorkspaceArtifact, bytes]:
        snapshot = await self.get(owner_id, run_id)
        record = next(
            (item for item in snapshot.workspace_artifacts if item.artifact_id == artifact_id),
            None,
        )
        if record is None:
            raise HarnessNotFoundError("运行成果不存在")
        if self.artifact_store is None:
            raise HarnessError("运行成果存储尚未配置")
        try:
            content = self.artifact_store.read(
                owner_id=owner_id,
                run_id=run_id,
                artifact_id=record.artifact_id,
                file_name=record.file_name,
                expected_sha256=record.content_sha256,
            )
        except RunWorkspaceArtifactError as exc:
            raise HarnessError(str(exc)) from exc
        public = AgentControlLoopWorkspaceArtifact.model_validate(
            record.model_dump(exclude={"content_sha256"})
        )
        return public, content

    def get_internal_workspace(self) -> dict[str, Any]:
        try:
            return self.catalog.internal_workspace()
        except Exception as exc:
            raise HarnessError("FORTE 办公资料库暂时无法读取") from exc

    async def start(
        self,
        owner_id: str,
        request: HarnessRunStart,
        *,
        _task_id: str | None = None,
        _parent_run_id: str | None = None,
        _continuation_reason: str | None = None,
        _carried_branch_id: str | None = None,
        _base_artifact_version: int | None = None,
        _base_task_commit: str | None = None,
        _parent_expected_version: int | None = None,
        _expected_task_version: int | None = None,
    ) -> HarnessRunStartResult:
        workspace = self.get_internal_workspace()
        if workspace.get("workspace_id") != request.workspace_id:
            raise HarnessNotFoundError("办公资料库不存在")
        current_workspace_revision = str(
            workspace.get("dataset_version", "forte-public-office")
        )
        instruction = request.instruction
        workspace_files = self._index_files(workspace)
        digest = hashlib.sha256(
            json.dumps(
                {
                    "request": request.model_dump(),
                    "parent_run_id": _parent_run_id,
                    "carried_branch_id": _carried_branch_id,
                    "base_artifact_version": _base_artifact_version,
                    "base_task_commit": _base_task_commit,
                    "parent_expected_version": _parent_expected_version,
                    "expected_task_version": _expected_task_version,
                    "continuation_reason": _continuation_reason,
                    "workspace_revision": current_workspace_revision,
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        idem_key = (owner_id, request.idempotency_key)
        async with self._lock:
            replay = self._idempotent.get(idem_key)
            if replay is not None:
                if replay.digest != digest:
                    raise HarnessConflictError("幂等键已用于不同 Harness 命令")
                return replay.result.model_copy(update={"replayed": True}, deep=True)
            parent: HarnessRunSnapshot | None = None
            carried_branch: AgentControlLoopBranch | None = None
            source_revision_changed = False
            task_record: TaskRecord | None = None
            if _parent_run_id is not None:
                parent_run = self._runs.get((owner_id, _parent_run_id))
                if parent_run is None:
                    raise HarnessNotFoundError("续办的旧任务不存在")
                parent = parent_run.snapshot
                if (
                    _parent_expected_version is not None
                    and parent.version != _parent_expected_version
                ):
                    raise HarnessConflictError("旧任务版本已更新，请刷新后重试")
                if parent.status not in {"stopped", "failed", "completed"}:
                    raise HarnessConflictError("只有已停止或已结束任务可以继续未完成任务")
                source_revision_changed = parent.workspace_revision != current_workspace_revision
                task_record = await self._task_get(owner_id, parent.task_id)
                if task_record is None:
                    raise HarnessError("任务台账不可读取")
                if _expected_task_version is None:
                    raise HarnessConflictError("续办必须提供 task 版本")
                if task_record.task_version != _expected_task_version:
                    raise HarnessConflictError("task 版本已更新，请刷新后重试")
                if (
                    task_record.current_run_id != parent.run_id
                    or task_record.run_sequence != parent.run_sequence
                    or task_record.owner_id != owner_id
                ):
                    raise HarnessConflictError("旧 Run 不是该任务当前指针，请刷新任务时间线")
                if _task_id is not None and _task_id != parent.task_id:
                    raise HarnessConflictError("续办任务的 task_id 与旧任务不一致")
                if _carried_branch_id is None:
                    raise HarnessConflictError("继续未完成任务必须指定一个未完成分支")
                carried_branch = next(
                    (item for item in parent.branches if item.branch_id == _carried_branch_id),
                    None,
                )
                if carried_branch is None or carried_branch.status in {"completed"}:
                    raise HarnessConflictError("只能续办旧任务中尚未完成的分支")
                if _base_artifact_version is not None and not any(
                    item.version == _base_artifact_version for item in parent.artifact_versions
                ):
                    raise HarnessConflictError("续办引用的成果版本不存在")
                if _base_task_commit is not None and not any(
                    item.commit_id == _base_task_commit for item in parent.commits
                ):
                    raise HarnessConflictError("续办引用的任务提交不存在")
                # Branch objective is the authoritative carried goal.  User
                # text remains an optional command input, never a replacement.
                instruction = carried_branch.objective
            task_id = _task_id or (parent.task_id if parent else f"task-{uuid4().hex[:12]}")
            task_version = task_record.task_version + 1 if task_record else 1
            run_sequence = task_record.run_sequence + 1 if task_record else 1
            run_id = f"harness:{uuid4().hex}"
            now = datetime.now(timezone.utc)
            contract = AgentControlLoopContract(
                goal=instruction,
                allowed_file_refs=[str(item["file_ref"]) for item in workspace_files],
                completion_criteria=[
                    "Agent 从整个资料库索引中自主选择与目标相关的最小证据集合",
                    "所有结论都引用本轮实际读取且通过服务端校验的公开文件",
                    "输出待用户确认的下一步任务、停止原因与剩余缺口，且不发生外部动作",
                ],
                max_rounds=request.loop.max_rounds,
                max_files_per_round=request.loop.max_files_per_round,
                max_model_calls=request.loop.max_model_calls,
                deadline_seconds=request.loop.deadline_seconds,
                task_id=task_id,
                run_sequence=run_sequence,
                parent_run_id=parent.run_id if parent else None,
                continuation_reason=(
                    _continuation_reason or "继续未完成任务"
                    if parent
                    else None
                ),
                carried_branch_id=carried_branch.branch_id if carried_branch else None,
                base_artifact_version=_base_artifact_version if parent else None,
                base_task_commit=_base_task_commit if parent else None,
                workspace_revision=current_workspace_revision,
                # A continuation starts with the carried Branch's approved
                # missing/input refs; it never lets a free-form instruction
                # widen the first round back to the whole catalog.
                recheck_file_refs=(
                    list(carried_branch.missing_file_refs or carried_branch.input_file_refs)
                    if carried_branch
                    else []
                ),
                source_revision_changed=source_revision_changed,
            )
            budget = AgentControlLoopBudget(
                max_rounds=contract.max_rounds,
                max_files_per_round=contract.max_files_per_round,
                max_model_calls=contract.max_model_calls,
                deadline_seconds=contract.deadline_seconds,
            )
            snapshot = HarnessRunSnapshot(
                run_id=run_id,
                task_id=task_id,
                task_version=task_version,
                run_sequence=run_sequence,
                parent_run_id=parent.run_id if parent else None,
                continuation_reason=(_continuation_reason or "继续未完成任务") if parent else None,
                carried_branch_id=carried_branch.branch_id if carried_branch else None,
                base_artifact_version=_base_artifact_version if parent else None,
                base_task_commit=_base_task_commit if parent else None,
                workspace_revision=current_workspace_revision,
                recheck_file_refs=(
                    list(carried_branch.missing_file_refs or carried_branch.input_file_refs)
                    if carried_branch
                    else []
                ),
                source_revision_changed=source_revision_changed,
                owner_id=owner_id,
                workspace_id=request.workspace_id,
                status="queued",
                version=request.expected_version,
                created_at=now,
                updated_at=now,
                instruction=instruction,
                instruction_source="user",
                contract=contract,
                budget=budget,
            )
            current = _Run(
                snapshot=snapshot,
                condition=asyncio.Condition(),
                active_since_perf=perf_counter(),
            )
            result = HarnessRunStartResult(run=snapshot)
            start_idempotency = StoredHarnessIdempotency(
                owner_id=owner_id,
                kind="start",
                idempotency_key=request.idempotency_key,
                digest=digest,
                result=result.model_dump(mode="json"),
            )
            child_task = None
            task_receipt = None
            task_digest = None
            if task_record is not None:
                child_task = task_record.model_copy(
                    update={
                        "task_version": task_version,
                        "current_run_id": run_id,
                        "workspace_revision": snapshot.workspace_revision,
                        "run_sequence": snapshot.run_sequence,
                        "parent_run_id": parent.run_id,
                        "updated_at": now,
                    }
                )
                task_receipt = TaskLedgerReceipt(
                    task_id=task_id,
                    owner_id=owner_id,
                    idempotency_key=request.idempotency_key,
                    from_task_version=task_record.task_version,
                    to_task_version=task_version,
                    child_run_id=run_id,
                    parent_run_id=parent.run_id,
                    recheck_file_refs=list(snapshot.recheck_file_refs),
                    created_at=now,
                )
                # Bind the append-only receipt to the complete continuation
                # command, not merely its parent and branch.  This prevents
                # replaying one idempotency key with a different payload or
                # expected version.
                task_digest = digest
            try:
                # Initial creation and continuation are one state-store
                # aggregate commit: run, task CAS, and receipts either all
                # become visible or none of them do.
                if child_task is not None and task_receipt is not None:
                    existing = await self.state_store.commit_task_transition(
                        StoredHarnessRun(
                            owner_id=owner_id,
                            run_id=run_id,
                            snapshot=snapshot.model_dump(mode="json"),
                            resume_status=current.resume_status,
                        ),
                        child_task,
                        expected_task_version=task_record.task_version,
                        expected_parent_run_id=parent.run_id,
                        expected_parent_version=_parent_expected_version,
                        task_receipt=task_receipt,
                        task_digest=task_digest,
                        idempotency=start_idempotency,
                    )
                else:
                    existing = await self.state_store.commit_task_transition(
                        StoredHarnessRun(
                            owner_id=owner_id,
                            run_id=run_id,
                            snapshot=snapshot.model_dump(mode="json"),
                            resume_status=current.resume_status,
                        ),
                        self._task_record_from_snapshot(snapshot),
                        idempotency=start_idempotency,
                    )
            except TaskLedgerConflict as exc:
                raise HarnessConflictError(str(exc)) from exc
            except Exception as exc:
                raise HarnessError("任务台账事务提交失败") from exc
            if existing is not None:
                if existing.digest != digest:
                    raise HarnessConflictError("幂等键已用于不同 Harness 命令")
                restored = HarnessRunStartResult.model_validate(existing.result)
                return restored.model_copy(update={"replayed": True}, deep=True)
            self._runs[(owner_id, run_id)] = current
            self._idempotent[idem_key] = _IdempotentStart(digest, result)
            self._schedule_run(owner_id, run_id, workspace, instruction)
            return result.model_copy(deep=True)

    async def get(self, owner_id: str, run_id: str) -> HarnessRunSnapshot:
        async with self._lock:
            run = self._runs.get((owner_id, run_id))
            if run is None:
                raise HarnessNotFoundError("Harness run 不存在")
            return run.snapshot.model_copy(deep=True)

    @staticmethod
    def _task_record_from_snapshot(snapshot: HarnessRunSnapshot) -> TaskRecord:
        return TaskRecord(
            task_id=snapshot.task_id,
            owner_id=snapshot.owner_id,
            task_version=snapshot.task_version,
            workspace_id=snapshot.workspace_id,
            workspace_revision=snapshot.workspace_revision,
            current_run_id=snapshot.run_id,
            run_sequence=snapshot.run_sequence,
            parent_run_id=snapshot.parent_run_id,
            created_at=snapshot.created_at,
            updated_at=snapshot.updated_at,
        )

    async def get_task(self, owner_id: str, task_id: str) -> PublicHarnessTaskSnapshot:
        """Return a sanitized owner-scoped task pointer."""
        try:
            record, stored_runs = await self.state_store.get_task_aggregate(owner_id, task_id)
            record = TaskRecord.model_validate(record) if record is not None else None
            task_snapshots = []
            for item in stored_runs:
                if item.owner_id != owner_id:
                    continue
                snapshot = HarnessRunSnapshot.model_validate(item.snapshot)
                if snapshot.owner_id != owner_id:
                    raise HarnessError("任务台账 Run owner 不一致")
                if snapshot.task_id == task_id:
                    task_snapshots.append(snapshot)
        except Exception as exc:
            if isinstance(exc, HarnessError):
                raise
            raise HarnessError("任务台账 Run 读取失败") from exc
        if record is None:
            candidates = [item for item in task_snapshots if item.task_id == task_id]
            if not candidates:
                raise HarnessNotFoundError("任务不存在")
            # Legacy records are migrated during setup only.  A GET must not
            # mutate the ledger, and a Run without its Task is an integrity
            # failure rather than a synthetic pointer.
            raise HarnessError("任务台账不可读取")
        if record.owner_id != owner_id:
            raise HarnessError("任务台账 owner 不一致")
        snapshots = [item for item in task_snapshots if item.task_id == task_id]
        snapshot = next((item for item in snapshots if item.run_id == record.current_run_id), None)
        if snapshot is None:
            raise HarnessError("任务台账 current Run 不可读取")
        if (
            snapshot.task_id != record.task_id
            or snapshot.owner_id != record.owner_id
            or snapshot.task_version != record.task_version
            or snapshot.run_sequence != record.run_sequence
            or snapshot.workspace_id != record.workspace_id
            or snapshot.workspace_revision != record.workspace_revision
        ):
            raise HarnessError("任务台账 current Run 身份不一致")
        artifact = snapshot.artifact_versions[-1] if snapshot.artifact_versions else None
        lineage = [
            PublicHarnessTaskLineageItem(
                run_id=item.run_id,
                run_sequence=item.run_sequence,
                parent_run_id=item.parent_run_id,
                status=item.status,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in snapshots
        ]
        lineage.sort(key=lambda item: item.run_sequence)
        lineage_total = len(lineage)
        lineage_truncated = lineage_total > 100
        return PublicHarnessTaskSnapshot(
            task_id=record.task_id,
            task_version=record.task_version,
            current_run_id=snapshot.run_id,
            run_sequence=snapshot.run_sequence,
            parent_run_id=snapshot.parent_run_id,
            workspace_revision=snapshot.workspace_revision,
            status=snapshot.status,
            created_at=snapshot.created_at,
            updated_at=snapshot.updated_at,
            current_artifact_id=artifact.artifact_id if artifact else None,
            current_artifact_version=artifact.version if artifact else None,
            current_commit_id=snapshot.last_commit.commit_id if snapshot.last_commit else None,
            lineage=lineage[-100:],
            lineage_total=lineage_total,
            lineage_truncated=lineage_truncated,
        )

    async def continue_unfinished_task(
        self,
        owner_id: str,
        run_id: str,
        branch_id: str,
        *,
        idempotency_key: str,
        expected_version: int,
        expected_task_version: int,
        instruction: str | None = None,
        loop: AgentControlLoopOptions | None = None,
    ) -> HarnessRunStartResult:
        """Create a new Run for one unfinished Branch of a terminal Run.

        This is intentionally implemented as a start command, not a resume:
        the old Run and its immutable result history remain untouched.
        """
        old = await self.get(owner_id, run_id)
        if isinstance(expected_task_version, bool) or not isinstance(expected_task_version, int):
            raise HarnessConflictError("续办必须提供有效的 task 版本")
        if old.version != expected_version:
            raise HarnessConflictError("任务版本已更新，请刷新后重试")
        branch = next((item for item in old.branches if item.branch_id == branch_id), None)
        if branch is None or branch.status == "completed":
            raise HarnessConflictError("只能继续一个尚未完成的任务分支")
        return await self.start(
            owner_id,
            HarnessRunStart(
                idempotency_key=idempotency_key,
                expected_version=1,
                instruction=instruction or branch.objective,
                loop=loop or AgentControlLoopOptions(
                    max_rounds=old.contract.max_rounds,
                    max_files_per_round=old.contract.max_files_per_round,
                    max_model_calls=old.contract.max_model_calls,
                    deadline_seconds=old.contract.deadline_seconds,
                ),
            ),
            _task_id=old.task_id,
            _parent_run_id=old.run_id,
            _continuation_reason="继续未完成任务",
            _carried_branch_id=branch.branch_id,
            _base_artifact_version=(old.artifact_versions[-1].version if old.artifact_versions else None),
            _base_task_commit=old.last_commit.commit_id if old.last_commit else None,
            _parent_expected_version=expected_version,
            _expected_task_version=expected_task_version,
        )

    async def execute_admitted_readonly_workers(
        self,
        owner_id: str,
        run_id: str,
        *,
        expected_version: int,
        idempotency_key: str,
        worker_requests: list[Any],
        handler: Any,
        user_confirmed: bool,
    ) -> HarnessRunSnapshot:
        """Run explicitly confirmed branch-scoped Workers and merge partial results.

        This method is deliberately separate from the Planner path: admission
        never dispatches work, and only this explicit receipt can do so.
        """
        from services.api.app.application.readonly_workers import (
            execute_readonly_workers,
            merge_adopted_contributions,
        )

        if not user_confirmed:
            raise HarnessConflictError("启动只读 Worker 前必须由用户明确确认")
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            snapshot = run.snapshot
            if snapshot.status in {"completed", "failed", "stopped"}:
                raise HarnessConflictError("终态 Run 不能追加 Worker；请创建新的任务")
            if snapshot.version != expected_version:
                raise HarnessConflictError("任务版本已更新，请刷新后重试")
            admission = snapshot.topology_admission or {}
            admission_mode = admission.mode if isinstance(admission, TopologyAdmission) else admission.get("mode")
            if admission_mode != "adaptive_readonly_workers":
                raise HarnessConflictError("当前拓扑未获准启动只读 Worker")
            if len(worker_requests) < 1 or len(worker_requests) > 3:
                raise HarnessConflictError("只读 Worker 数量必须在 1 到 3 之间")
            if len({item.branch_id for item in worker_requests}) != len(worker_requests):
                raise HarnessConflictError("同一批 Worker 不能重复派发同一分支")
            if any(item.expected_version != expected_version for item in worker_requests):
                raise HarnessConflictError("Worker 请求版本与当前任务不一致")
            digest = hashlib.sha256(
                json.dumps(
                    [item.model_dump(mode="json") for item in worker_requests],
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            previous = getattr(self, "_worker_idempotent", {}).get((owner_id, run_id, idempotency_key))
            if previous is not None:
                previous_digest, previous_snapshot = previous
                if previous_digest != digest:
                    raise HarnessConflictError("幂等键已用于不同 Worker 命令")
                return previous_snapshot.model_copy(deep=True)
            durable_digest = snapshot.worker_idempotency.get(idempotency_key)
            if durable_digest is not None:
                if durable_digest != digest:
                    raise HarnessConflictError("幂等键已用于不同 Worker 命令")
                return snapshot.model_copy(deep=True)
            branch_refs = {item.branch_id: set(item.input_file_refs) for item in snapshot.branches}
            branches_by_id = {item.branch_id: item for item in snapshot.branches}
            for item in worker_requests:
                if item.branch_id not in branch_refs or set(item.source_file_refs) - branch_refs[item.branch_id]:
                    raise HarnessConflictError("Worker 只能读取自己 Branch 的批准来源")
                branch = branches_by_id[item.branch_id]
                if branch.status != "running":
                    raise HarnessConflictError("只能派发服务端标记为 ready 的 Branch")
                if any(
                    dependency_branch.status != "completed"
                    for dependency_id in branch.depends_on
                    if (dependency_branch := branches_by_id.get(dependency_id)) is not None
                ):
                    raise HarnessConflictError("只能派发依赖已完成的 ready Branch；下游分支仍被阻塞")
            budget = self._budget_with_elapsed(run)
            if budget.model_calls_used + len(worker_requests) > budget.max_model_calls:
                raise HarnessConflictError("剩余模型调用预算不足，未派发任何 Worker")
            # Create the execution ledger only for the explicitly admitted
            # adaptive topology.  The Branch remains the authority for the
            # approved refs and dependency graph; WorkUnit is just its
            # versioned execution pointer.
            now = datetime.now(timezone.utc)
            work_units = list(snapshot.work_units)
            work_unit_by_branch = {item.branch_id: item for item in work_units}
            for request in worker_requests:
                branch = branches_by_id[request.branch_id]
                work_unit = work_unit_by_branch.get(request.branch_id)
                if work_unit is None:
                    work_unit = WorkUnitRecord(
                        owner_id=owner_id,
                        task_id=snapshot.task_id,
                        run_id=run_id,
                        work_unit_id=branch.branch_id,
                        branch_id=branch.branch_id,
                        unit_id=branch.unit_id,
                        depends_on=list(branch.depends_on),
                        approved_file_refs=list(branch.input_file_refs),
                        state=WorkUnitState.READY,
                    )
                elif set(work_unit.approved_file_refs) != set(branch.input_file_refs):
                    raise HarnessConflictError("WorkUnit 批准来源与 Branch 不一致")
                if work_unit.state == WorkUnitState.PENDING:
                    work_unit = work_unit.transition(WorkUnitState.READY)
                if work_unit.state not in {WorkUnitState.READY, WorkUnitState.WAITING}:
                    raise HarnessConflictError("该 WorkUnit 已有在途或终态尝试")
                work_unit = work_unit.transition(WorkUnitState.RESERVED).model_copy(
                    update={
                        "attempt": work_unit.attempt + 1,
                        "reservation_id": f"worker-wave-{idempotency_key}",
                    }
                )
                work_unit = work_unit.transition(WorkUnitState.RUNNING)
                work_unit_by_branch[request.branch_id] = work_unit
            work_units = [
                work_unit_by_branch.get(item.branch_id, item) for item in work_units
            ]
            for request in worker_requests:
                if request.branch_id not in {item.branch_id for item in work_units}:
                    work_units.append(work_unit_by_branch[request.branch_id])
            reservation_events = [
                HarnessEvent(
                    sequence=snapshot.last_event_sequence + 1,
                    event_name="worker_wave_reserved",
                    occurred_at=now,
                    status="analyzing",
                    message="已为获准的 WorkUnit 持久化 Worker 波次预留。",
                    details={"work_unit_ids": [item.branch_id for item in worker_requests], "external_action": False},
                ),
                HarnessEvent(
                    sequence=snapshot.last_event_sequence + 2,
                    event_name="work_unit_started",
                    occurred_at=now,
                    status="analyzing",
                    message="WorkUnit 已进入只读执行。",
                    details={"work_unit_ids": [item.branch_id for item in worker_requests], "external_action": False},
                ),
            ]
            run.snapshot = run.snapshot.model_copy(
                update={
                    "budget": budget.model_copy(
                        update={"model_calls_used": budget.model_calls_used + len(worker_requests)}
                    ),
                    # Reserve the calls as a versioned state transition.  A
                    # second dispatch carrying the same expected_version must
                    # fail before it can start another set of workers.
                    "version": run.snapshot.version + 1,
                    "updated_at": now,
                    "work_units": work_units,
                    "events": [*snapshot.events, *reservation_events],
                    "last_event_sequence": reservation_events[-1].sequence,
                }
            )
            await self._persist_locked(run)

        contributions = await execute_readonly_workers(worker_requests, handler, max_workers=3)
        merged = merge_adopted_contributions(contributions, version=1)
        now = datetime.now(timezone.utc)
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            # Worker model receipts append ordered events and therefore bump
            # the Run version while they are in flight.  The user CAS was
            # checked before dispatch; only a version regression is invalid.
            if run.snapshot.version < expected_version:
                raise HarnessConflictError("任务版本已更新，Worker 结果未合入")
            artifact: AgentControlLoopArtifactVersion | None = None
            task_commit: AgentControlLoopCommit | None = None
            artifact_versions = list(run.snapshot.artifact_versions)
            commits = list(run.snapshot.commits)
            last_commit = run.snapshot.last_commit
            work_units = list(run.snapshot.work_units)
            work_unit_by_branch = {item.branch_id: item for item in work_units}
            contribution_by_branch = {item.branch_id: item for item in contributions}
            adopted_worker_ids = set(merged.adopted_worker_run_ids)
            adopted_artifact_version = (
                len(artifact_versions) + 1
                if adopted_worker_ids and len(artifact_versions) < 24
                else None
            )
            contribution_records: list[ContributionRecord] = []
            for contribution in contributions:
                work_unit = work_unit_by_branch.get(contribution.branch_id)
                if work_unit is None or work_unit.state != WorkUnitState.RUNNING:
                    raise HarnessConflictError("Worker 返回时 WorkUnit 不在 running 状态")
                anchors: list[AgentControlLoopEvidenceAnchor] = []
                seen_anchor_keys: set[tuple[str, str, int, int]] = set()
                for finding in contribution.findings:
                    for anchor in finding.evidence_anchors:
                        key = (anchor.file_ref, anchor.locator_kind, anchor.start, anchor.end)
                        if key not in seen_anchor_keys:
                            anchors.append(anchor)
                            seen_anchor_keys.add(key)
                if contribution.worker_run_id in adopted_worker_ids:
                    gate_status = ContributionGateStatus.ADOPTED
                    gate_reason = "来源范围与 Anchor 已通过服务端采用门。"
                    next_state = WorkUnitState.ADOPTED
                elif contribution.outcome == "failed":
                    gate_status = ContributionGateStatus.FAILED
                    gate_reason = contribution.error or "Worker 执行失败。"
                    next_state = WorkUnitState.FAILED
                elif contribution.outcome == "ambiguous":
                    gate_status = ContributionGateStatus.WAITING
                    gate_reason = "结果已返回，但原文位置不明确，等待用户核对。"
                    next_state = WorkUnitState.WAITING
                else:
                    gate_status = ContributionGateStatus.REJECTED
                    gate_reason = contribution.error or "贡献未通过服务端采用门。"
                    next_state = WorkUnitState.REJECTED
                contribution_record = ContributionRecord(
                    owner_id=owner_id,
                    task_id=run.snapshot.task_id,
                    run_id=run_id,
                    work_unit_id=contribution.branch_id,
                    branch_id=contribution.branch_id,
                    attempt=work_unit.attempt,
                    worker_run_id=contribution.worker_run_id,
                    run_source_revision=run.snapshot.workspace_revision,
                    catalog_source_revision=str(getattr(self.catalog, "revision", "forte-public-catalog")),
                    approved_file_refs=tuple(work_unit.approved_file_refs),
                    evidence_anchors=tuple(anchors),
                    model_receipt=WorkerModelReceipt(
                        called=contribution.model_called,
                        output_used=contribution.output_used,
                        elapsed_ms=contribution.elapsed_ms,
                    ),
                    gate_status=gate_status,
                    gate_reason=gate_reason,
                    artifact_version=adopted_artifact_version if gate_status == ContributionGateStatus.ADOPTED else None,
                    summary=contribution.summary,
                )
                contribution_records.append(contribution_record)
                updated_work_unit = work_unit.transition(WorkUnitState.RETURNED, error=contribution.error)
                updated_work_unit = updated_work_unit.model_copy(
                    update={"latest_contribution_id": contribution_record.contribution_id}
                )
                updated_work_unit = updated_work_unit.transition(next_state, error=contribution.error)
                work_unit_by_branch[contribution.branch_id] = updated_work_unit
            work_units = [work_unit_by_branch.get(item.branch_id, item) for item in work_units]
            for item in contribution_records:
                if item.branch_id not in {unit.branch_id for unit in work_units}:
                    work_units.append(work_unit_by_branch[item.branch_id])
            prior_findings = artifact_versions[-1].findings if artifact_versions else []
            finding_by_id = {finding.finding_id: finding for finding in prior_findings}
            artifact_findings = [
                finding
                for contribution in merged.adopted_contributions
                for finding in contribution.findings
            ]
            for finding in artifact_findings:
                finding_by_id[finding.finding_id] = finding
            artifact_findings = list(finding_by_id.values())
            branch_by_id = {branch.branch_id: branch for branch in run.snapshot.branches}
            updated_by_id: dict[str, AgentControlLoopBranch] = {}
            updated_branches: list[AgentControlLoopBranch] = []
            for branch in run.snapshot.branches:
                contribution = contribution_by_branch.get(branch.branch_id)
                if contribution is not None:
                    adopted = contribution.worker_run_id in adopted_worker_ids
                    updated = branch.model_copy(
                        update={
                            "status": "completed" if adopted else "waiting_input",
                            "verified_file_refs": sorted(
                                set(branch.verified_file_refs)
                                | (set(contribution.source_file_refs) if adopted else set())
                            )[:24],
                            "missing_file_refs": [] if adopted else list(contribution.source_file_refs),
                            "updated_at": now,
                        }
                    )
                    updated_branches.append(updated)
                    updated_by_id[updated.branch_id] = updated
                    continue
                dependencies = [
                    updated_by_id.get(item, branch_by_id[item])
                    for item in branch.depends_on
                    if item in branch_by_id
                ]
                if branch.status in {"pending", "blocked", "running"}:
                    if any(item.status in {"failed", "blocked", "waiting_input"} for item in dependencies):
                        updated = branch.model_copy(update={"status": "blocked", "updated_at": now})
                    elif all(item.status == "completed" for item in dependencies):
                        updated = branch.model_copy(update={"status": "running", "updated_at": now})
                    else:
                        updated = branch.model_copy(update={"status": "pending", "updated_at": now})
                    updated_branches.append(updated)
                    updated_by_id[updated.branch_id] = updated
                else:
                    updated_branches.append(branch)
                    updated_by_id[branch.branch_id] = branch
            all_branches_completed = bool(updated_branches) and all(
                branch.status == "completed" for branch in updated_branches
            )
            branch_state = {branch.branch_id: branch for branch in updated_branches}
            ready_branch_ids = [
                branch.branch_id
                for branch in updated_branches
                if branch.status == "running"
                and all(
                    branch_state.get(dependency_id) is not None
                    and branch_state[dependency_id].status == "completed"
                    for dependency_id in branch.depends_on
                )
            ]
            next_step = None
            if not all_branches_completed:
                waiting_file_refs = [
                    ref
                    for contribution in contributions
                    if contribution.outcome != "adopted"
                    for ref in contribution.source_file_refs
                ]
                next_step = AgentControlLoopNextStep(
                    decision="waiting_input",
                    reason=(
                        "本批贡献已合入，下一批 ready Branch 已就绪；失败或位置不明确的分支保持暂停。"
                        if ready_branch_ids
                        else "部分 Worker 已合入，其余分支因失败或原文位置不明确而暂停。"
                    ),
                    candidate_file_refs=waiting_file_refs[:20],
                    candidate_branch_ids=(
                        list(merged.waiting_branch_ids) + ready_branch_ids
                    )[:36],
                    ready_branch_ids=ready_branch_ids[:36],
                )
            worker_result = None
            if artifact_findings:
                worker_result = HarnessTaskResult(
                    summary="只读 Worker 已返回并通过服务端来源核对的部分结果。",
                    findings=[HarnessFinding.model_validate(item.model_dump(mode="json")) for item in artifact_findings],
                    follow_ups=["继续处理仍在等待的分支。"] if not all_branches_completed else [],
                )
            if merged.adopted_contributions and len(artifact_versions) < 24:
                artifact_version = len(artifact_versions) + 1
                artifact_id = (
                    artifact_versions[-1].artifact_id
                    if artifact_versions
                    else "artifact-"
                    + hashlib.sha256(f"{run_id}:evidence-brief".encode("utf-8")).hexdigest()[:12]
                )
                source_refs = sorted(
                    {
                        ref
                        for prior in artifact_versions
                        for ref in prior.source_file_refs
                    }
                    | {
                        ref
                        for item in merged.adopted_contributions
                        for ref in item.source_file_refs
                    }
                )
                artifact = AgentControlLoopArtifactVersion(
                    artifact_id=artifact_id,
                    version=artifact_version,
                    title="只读 Worker 合入简报",
                    status="committed",
                    round_number=(run.snapshot.rounds[-1].round_number if run.snapshot.rounds else 1),
                    summary=(
                        f"服务端仅合入 {len(merged.adopted_contributions)} 条通过来源定位的只读 Worker 贡献；"
                        "其余分支仍保持待处理。"
                    ),
                    findings=artifact_findings,
                    finding_count=len(artifact_findings),
                    source_file_refs=source_refs,
                    parent_version=artifact_versions[-1].version if artifact_versions else None,
                    created_at=now,
                )
                commit_id = "commit-" + hashlib.sha256(
                    f"{run_id}:worker:{artifact.artifact_id}:{artifact.version}".encode("utf-8")
                ).hexdigest()[:12]
                task_commit = AgentControlLoopCommit(
                    commit_id=commit_id,
                    artifact_id=artifact.artifact_id,
                    artifact_version=artifact.version,
                    operation="commit",
                    parent_commit_id=last_commit.commit_id if last_commit else None,
                    summary="已将通过来源与 Anchor 核对的只读 Worker 贡献写入逻辑成果版本。",
                    committed_at=now,
                )
                artifact_versions.append(artifact)
                commits.append(task_commit)
                last_commit = task_commit
                # Keep the append-only worker merge receipt aligned with the
                # actual normal ArtifactVersion it records.
                merged = merged.model_copy(
                    update={"artifact_id": artifact.artifact_id, "version": artifact.version}
                )
            run.snapshot = run.snapshot.model_copy(
                update={
                    "worker_runs": [*run.snapshot.worker_runs, *contributions],
                    "shared_artifacts": [*run.snapshot.shared_artifacts, merged],
                    "work_units": work_units,
                    "contributions": [*run.snapshot.contributions, *contribution_records],
                    "artifact_versions": artifact_versions,
                    "commits": commits,
                    "last_commit": last_commit,
                    "branches": updated_branches,
                    "result": worker_result,
                    "rounds": [
                        item.model_copy(
                            update={
                                "status": "completed",
                                "phase": "commit",
                                "result": worker_result.model_dump(mode="json") if worker_result else None,
                                "next_step": next_step,
                                "completed_at": now,
                            }
                        )
                        if item.round_number == run.snapshot.current_round
                        else item
                        for item in run.snapshot.rounds
                    ],
                    "status": "completed" if all_branches_completed else "waiting_input",
                    "worker_idempotency": {
                        **run.snapshot.worker_idempotency,
                        idempotency_key: digest,
                    },
                    "updated_at": now,
                    "version": run.snapshot.version + 1,
                }
            )
            await self._persist_locked(
                run,
                artifact_version=artifact,
                task_commit=task_commit,
            )
            if not hasattr(self, "_worker_idempotent"):
                self._worker_idempotent = {}
            self._worker_idempotent[(owner_id, run_id, idempotency_key)] = (
                digest,
                run.snapshot.model_copy(deep=True),
            )
            current_status = run.snapshot.status
        # Keep a per-worker ordered receipt in the same event stream as the
        # group merge.  A reconnecting cockpit can therefore show which
        # Branch failed without treating the whole batch as failed.
        for contribution in contributions:
            await self._transition(
                owner_id,
                run_id,
                current_status,
                "worker_returned",
                contribution.summary,
                {
                    "worker_run_id": contribution.worker_run_id,
                    "branch_id": contribution.branch_id,
                    "outcome": contribution.outcome,
                    "model_called": contribution.model_called,
                    "output_used": contribution.output_used,
                    "external_action": False,
                },
            )
            ledger_record = next(
                item for item in contribution_records if item.worker_run_id == contribution.worker_run_id
            )
            await self._transition(
                owner_id,
                run_id,
                current_status,
                "contribution_recorded",
                "Worker 结果已写入不可变 Contribution Ledger。",
                {
                    "contribution_id": ledger_record.contribution_id,
                    "work_unit_id": ledger_record.work_unit_id,
                    "gate_status": ledger_record.gate_status,
                    "artifact_version": ledger_record.artifact_version,
                    "external_action": False,
                },
            )
            if contribution.outcome == "failed":
                await self._transition(
                    owner_id,
                    run_id,
                    current_status,
                    "work_unit_failed",
                    "WorkUnit 执行失败，相关下游依赖保持阻塞。",
                    {
                        "work_unit_id": contribution.branch_id,
                        "contribution_id": ledger_record.contribution_id,
                        "external_action": False,
                    },
                )
            disposition_event = (
                "contribution_adopted"
                if contribution.worker_run_id in merged.adopted_worker_run_ids
                else "contribution_waiting"
                if contribution.outcome == "ambiguous"
                else "contribution_rejected"
            )
            await self._transition(
                owner_id,
                run_id,
                current_status,
                disposition_event,
                contribution.summary,
                {
                    "worker_run_id": contribution.worker_run_id,
                    "branch_id": contribution.branch_id,
                    "outcome": contribution.outcome,
                    "external_action": False,
                },
            )
        await self._transition(
            owner_id,
            run_id,
            current_status,
            "topology_workers_completed",
            "已收到只读 Worker 回执；仅通过来源定位的贡献进入共享成果，其余分支保留待处理。",
            {
                "worker_count": len(contributions),
                "adopted_count": len(merged.adopted_worker_run_ids),
                "waiting_branch_count": len(merged.waiting_branch_ids),
                "external_action": False,
            },
        )
        await self._transition(
            owner_id,
            run_id,
            current_status,
            "worker_wave_committed",
            "本批 WorkUnit 与 Contribution 已完成服务端提交。",
            {
                "work_unit_count": len(contributions),
                "contribution_count": len(contribution_records),
                "artifact_version": merged.version if merged.adopted_worker_run_ids else None,
                "external_action": False,
            },
        )
        latest = await self.get(owner_id, run_id)
        if hasattr(self, "_worker_idempotent"):
            self._worker_idempotent[(owner_id, run_id, idempotency_key)] = (
                digest,
                latest.model_copy(deep=True),
            )
        return latest

    async def execute_admitted_workers_from_branches(
        self,
        owner_id: str,
        run_id: str,
        *,
        branch_ids: list[str],
        expected_version: int,
        idempotency_key: str,
        user_confirmed: bool,
    ) -> HarnessRunSnapshot:
        """Provider-backed worker vertical using only each Branch's sources."""
        from services.api.app.application.readonly_workers import (
            ReadonlyWorkerContribution,
            ReadonlyWorkerRequest,
        )

        snapshot = await self.get(owner_id, run_id)
        if self.analyst is None:
            raise HarnessConflictError("只读 Worker 分析器尚未配置")
        if not branch_ids:
            latest_step = snapshot.rounds[-1].next_step if snapshot.rounds else None
            branch_ids = list(latest_step.ready_branch_ids) if latest_step else []
            if not branch_ids:
                branch_ids = [item.branch_id for item in snapshot.branches if item.status == "running"]
            branch_ids = branch_ids[:3]
        branches = [self._branch_by_id(snapshot.branches, item) for item in branch_ids]
        if any(item is None for item in branches):
            raise HarnessConflictError("Worker 分支不存在")
        requests = [
            ReadonlyWorkerRequest(
                worker_run_id=(
                    "worker-"
                    + hashlib.sha256(f"{idempotency_key}:{item.branch_id}".encode()).hexdigest()[:12]
                ),
                branch_id=item.branch_id,
                goal=item.objective,
                source_file_refs=tuple(item.input_file_refs),
                expected_version=expected_version,
            )
            for item in branches
            if item is not None
        ]

        async def handler(request: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
            started = perf_counter()
            current = await self.get(owner_id, run_id)
            branch = self._branch_by_id(current.branches, request.branch_id)
            unit = next(
                (item for item in (current.plan.units if current.plan else []) if item.unit_id == branch.unit_id),
                None,
            ) if branch else None
            if branch is None or unit is None:
                raise HarnessPlanError("worker branch has no validated plan unit")
            files = self.catalog.agent_file_inputs(list(request.source_file_refs))
            candidate, _worker_receipt = await self._invoke_analyst(
                owner_id=owner_id,
                run_id=run_id,
                round_number=branch.round_number,
                instruction=request.goal,
                plan=HarnessPlan(summary=unit.objective, selection_reason="服务端 Branch 目标", units=[unit]),
                files=files,
                verified_effect_context=None,
                attempt=1,
                validation_feedback=None,
                reserve_model_call=False,
                record_round_receipt=False,
            )
            candidate = self._validate_candidate_result_scope(
                candidate,
                files,
                HarnessPlan(summary=unit.objective, selection_reason="服务端 Branch 目标", units=[unit]),
            )
            resolution = self._resolve_evidence_anchors(
                candidate,
                files,
                {str(item["file_ref"]): self._source_revision(item) for item in files},
                request.goal,
            )
            adopted = resolution.result is not None and not resolution.evidence_resolutions
            reconciliation = reconcile_narrative(
                run_id=run_id,
                round_number=branch.round_number,
                result=resolution.result,
                context_used=None,
                current_context=None,
                checked_at=datetime.now(timezone.utc),
            )
            anchors = tuple(
                f"{anchor.file_ref}:{anchor.locator_kind}:{anchor.start}-{anchor.end}"
                for finding in (resolution.result.findings if resolution.result else [])
                for anchor in finding.evidence_anchors
            )
            artifact_findings = tuple(
                AgentControlLoopArtifactFinding(
                    finding_id=finding.finding_id,
                    plan_unit_id=finding.plan_unit_id,
                    affected_branch_ids=finding.affected_branch_ids or [branch.branch_id],
                    title=finding.title,
                    detail=finding.detail,
                    fact_summary=finding.fact_summary,
                    impact=finding.impact,
                    file_refs=finding.file_refs,
                    evidence_anchors=finding.evidence_anchors,
                    evidence_resolutions=finding.evidence_resolutions,
                    review=finding.review,
                )
                for finding in (resolution.result.findings if resolution.result else [])
            )
            return ReadonlyWorkerContribution(
                worker_run_id=request.worker_run_id,
                branch_id=request.branch_id,
                outcome="adopted" if adopted else "ambiguous",
                summary=(resolution.result.summary if resolution.result else "原文位置仍需人工核对"),
                source_file_refs=request.source_file_refs,
                evidence_anchors=anchors,
                model_called=_worker_receipt.called,
                output_used=adopted,
                elapsed_ms=_worker_receipt.elapsed_ms or int((perf_counter() - started) * 1000),
                narrative_reconciliation=reconciliation,
                findings=artifact_findings,
            )

        return await self.execute_admitted_readonly_workers(
            owner_id,
            run_id,
            expected_version=expected_version,
            idempotency_key=idempotency_key,
            worker_requests=requests,
            handler=handler,
            user_confirmed=user_confirmed,
        )

    async def control(
        self,
        owner_id: str,
        run_id: str,
        request: AgentControlLoopControlRequest,
    ) -> HarnessControlResult:
        digest = hashlib.sha256(
            json.dumps(
                {"run_id": run_id, **request.model_dump()},
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        idempotency_key = (owner_id, request.idempotency_key)
        async with self._lock:
            replay = self._control_idempotent.get(idempotency_key)
            if replay is not None:
                if replay.digest != digest:
                    raise HarnessConflictError("幂等键已用于不同控制命令")
                return replay.result.model_copy(update={"replayed": True}, deep=True)

            run = self._require_run(owner_id, run_id)
            snapshot = run.snapshot
            if snapshot.version != request.expected_version:
                raise HarnessConflictError(
                    f"任务版本已更新，当前为 v{snapshot.version}，请刷新后重试"
                )
            if request.command == "rollback":
                return await self._rollback_control_locked(
                    owner_id,
                    run,
                    request,
                    digest=digest,
                    idempotency_key=idempotency_key,
                )
            if request.command == "decision":
                return await self._decision_control_locked(
                    owner_id,
                    run,
                    request,
                    digest=digest,
                    idempotency_key=idempotency_key,
                )
            if snapshot.status in {"ready_to_execute", "completed", "stopped", "failed"} and request.command != "topology_override":
                raise HarnessConflictError("当前任务已经结束，不能再提交控制命令")

            command = request.command
            if command == "topology_override":
                admission = snapshot.topology_admission
                if snapshot.status != "waiting_input" or admission is None:
                    raise HarnessConflictError("当前任务没有等待拓扑确认")
                if admission.mode != "adaptive_readonly_workers":
                    raise HarnessConflictError("当前任务无需切换保守拓扑")
                if request.topology_mode != "single_controller":
                    raise HarnessConflictError("只允许切回 single_controller")
            elif request.topology_mode is not None:
                raise HarnessConflictError("只有拓扑切换命令可以携带 topology_mode")
            if command == "pause" and snapshot.control_state != "running":
                raise HarnessConflictError("当前任务已经处于暂停或停止流程")
            if command == "resume" and snapshot.control_state not in {
                "pause_requested",
                "paused",
            }:
                raise HarnessConflictError("当前任务没有处于可恢复的暂停状态")
            if command == "steer" and request.instruction is None:
                raise HarnessConflictError("调整方向必须提供一条明确指令")
            if request.branch_id is not None and command != "resume":
                raise HarnessConflictError("只有继续命令可以指定待核对分支")
            if request.artifact_version is not None:
                raise HarnessConflictError("只有成果版本恢复命令可以指定版本")
            if any(
                value is not None
                for value in (
                    request.decision_action,
                    request.decision_request_id,
                    request.finding_id,
                    request.resolution_id,
                    request.selected_option_id,
                    request.selected_candidate_id,
                    request.feedback,
                )
            ):
                raise HarnessConflictError("只有人工决策命令可以携带决策字段")

            selected_branch_id = snapshot.active_branch_id
            selected_branch: AgentControlLoopBranch | None = None
            if command == "resume" and snapshot.status == "waiting_input":
                waiting_branches = [
                    item for item in snapshot.branches if item.status == "waiting_input"
                ]
                if request.branch_id is not None:
                    selected_branch = next(
                        (item for item in waiting_branches if item.branch_id == request.branch_id),
                        None,
                    )
                    if selected_branch is None:
                        raise HarnessConflictError("该分支已经完成或不属于当前任务")
                elif waiting_branches:
                    selected_branch = waiting_branches[0]
                selected_branch_id = selected_branch.branch_id if selected_branch else None

            now = datetime.now(timezone.utc)
            control_id = f"control-{uuid4().hex[:12]}"
            next_version = snapshot.version + 1
            control_status: Literal["accepted", "applied", "rejected"] = "accepted"
            applied_version: int | None = None
            next_state = snapshot.control_state
            next_status = snapshot.status
            event_name = f"control_{command}_recorded"
            message = "控制命令已记录，将在下一个安全点处理。"

            if command == "pause":
                next_state = "pause_requested"
                message = "暂停请求已记录；当前模型调用结束后将在安全点暂停。"
            elif command == "resume":
                next_state = "running"
                control_status = "applied"
                applied_version = next_version
                if snapshot.control_state == "paused":
                    next_status = run.resume_status or "planning"
                    self._resume_active_budget(run)
                message = (
                    f"已确认继续“{selected_branch.title}”分支，将只核对该分支缺少的证据。"
                    if selected_branch
                    else "Agent Control Loop 已恢复，将从安全点继续。"
                )
            elif command == "steer":
                message = "方向指令已记录，将应用于下一轮规划。"
            elif command == "stop":
                next_state = "stop_requested"
                message = "停止请求已记录；系统会保留已核对结果并在安全点结束。"
            elif command == "topology_override":
                # Downgrading is an in-place, user-approved route choice. Keep
                # the same Run/Task lineage and schedule its conservative
                # controller path instead of creating a new task.
                next_state = "running"
                next_status = "planning"
                control_status = "applied"
                applied_version = next_version
                message = "已按用户选择切回单 Controller；同一任务将从已保存计划继续，未调用只读 Worker。"

            control_event = AgentControlLoopControlEvent(
                control_id=control_id,
                command=command,
                branch_id=selected_branch_id if command == "resume" else None,
                instruction=request.instruction,
                accepted_at=now,
                accepted_task_version=next_version,
                applied_task_version=applied_version,
                status=control_status,
            )
            event = HarnessEvent(
                sequence=snapshot.last_event_sequence + 1,
                event_name=event_name,
                occurred_at=now,
                status=next_status,
                message=message,
                details={
                    "command": command,
                    "control_id": control_id,
                    "branch_id": selected_branch_id,
                    "applied": control_status == "applied",
                },
            )
            events = [*snapshot.events, event]
            last_event_sequence = event.sequence
            if (
                command == "resume"
                and selected_branch is not None
                and snapshot.rounds
                and snapshot.rounds[-1].next_step is not None
                and (
                    snapshot.rounds[-1].next_step.recovery_kind is not None
                    or snapshot.rounds[-1].next_step.evidence_resolutions
                )
            ):
                resumed_event = HarnessEvent(
                    sequence=event.sequence + 1,
                    event_name="branch_resumed_from_checkpoint",
                    occurred_at=now,
                    status=next_status,
                    message=(
                        f"已从检查点只恢复“{selected_branch.title}”分支；"
                        "其他分支和成果版本保持不变。"
                    ),
                    details={
                        "branch_id": selected_branch.branch_id,
                        "external_action": False,
                    },
                )
                events.append(resumed_event)
                last_event_sequence = resumed_event.sequence
            snapshot_updates: dict[str, Any] = {
                    "status": next_status,
                    "control_state": next_state,
                    "control_events": [*snapshot.control_events, control_event],
                    "active_branch_id": selected_branch_id,
                    "events": events,
                    "last_event_sequence": last_event_sequence,
                    "version": next_version,
                    "updated_at": now,
                }
            if command == "topology_override" and snapshot.topology_admission is not None:
                snapshot_updates["topology_admission"] = snapshot.topology_admission.model_copy(
                    update={
                        "mode": "single_controller",
                        "user_confirmation_required": False,
                        "reasons": [
                            *snapshot.topology_admission.reasons,
                            "用户在执行前选择切回单 Controller；本次不调用只读 Worker。",
                        ][:8],
                    }
                )
            run.snapshot = snapshot.model_copy(update=snapshot_updates)
            result = HarnessControlResult(run=run.snapshot.model_copy(deep=True))
            existing = await self._persist_locked(
                run,
                StoredHarnessIdempotency(
                    owner_id=owner_id,
                    kind="control",
                    idempotency_key=request.idempotency_key,
                    digest=digest,
                    result=result.model_dump(mode="json"),
                ),
            )
            if existing is not None:
                if existing.digest != digest:
                    run.snapshot = snapshot
                    raise HarnessConflictError("幂等键已用于不同控制命令")
                restored = HarnessControlResult.model_validate(existing.result)
                run.snapshot = restored.run.model_copy(deep=True)
                return restored.model_copy(update={"replayed": True}, deep=True)
            self._control_idempotent[idempotency_key] = _IdempotentControl(
                digest=digest, result=result
            )
            condition = run.condition
            should_schedule = command in {"resume", "topology_override"} and run_id not in self._tasks
        async with condition:
            condition.notify_all()
        if should_schedule:
            self._schedule_run(
                owner_id,
                run_id,
                self.get_internal_workspace(),
                result.run.instruction,
            )
        return result.model_copy(deep=True)

    async def _decision_control_locked(
        self,
        owner_id: str,
        run: _Run,
        request: AgentControlLoopControlRequest,
        *,
        digest: str,
        idempotency_key: tuple[str, str],
    ) -> HarnessControlResult:
        snapshot = run.snapshot
        if snapshot.status == "failed":
            raise HarnessConflictError("失败任务没有可绑定的人工决策事实")
        if request.decision_action is None:
            raise HarnessConflictError("人工决策必须说明接受、否决、暂缓或取消")
        if request.artifact_version is not None or request.instruction is not None:
            raise HarnessConflictError("人工决策不接受成果版本或方向字段")
        if request.finding_id is None and request.resolution_id is None:
            raise HarnessConflictError("人工决策必须绑定一条发现或证据定位")

        findings = self._snapshot_findings(snapshot)
        finding = next(
            (item for item in findings if item.finding_id == request.finding_id),
            None,
        )
        resolutions = self._snapshot_evidence_resolutions(snapshot)
        resolution = next(
            (item for item in resolutions if item.resolution_id == request.resolution_id),
            None,
        )
        if resolution is not None:
            if request.finding_id not in {None, resolution.finding_id}:
                raise HarnessConflictError("证据定位与发现不属于同一条记录")
            finding_id = resolution.finding_id
        elif finding is not None:
            finding_id = finding.finding_id
        else:
            raise HarnessConflictError("目标发现或证据定位已经不存在")
        if finding_id is None:
            raise HarnessConflictError("旧结果缺少可审计的发现标识，请重新核对")

        packet = next(
            (
                item
                for item in snapshot.decision_requests
                if item.resolution_id == (resolution.resolution_id if resolution else None)
                and item.finding_id == finding_id
            ),
            None,
        )
        if packet is not None:
            if packet.decision_request_id != request.decision_request_id:
                raise HarnessConflictError("该发现已有人工决策单，必须引用 decision_request_id")
            if packet.state not in {"open", "deferred"}:
                raise HarnessConflictError("人工决策单已经关闭")
        elif request.decision_request_id is not None:
            raise HarnessConflictError("人工决策单已经不存在或不属于当前发现")

        async def reject_resolution(message: str, status: Literal["stale", "rejected"]) -> None:
            if resolution is not None:
                now = datetime.now(timezone.utc)
                updated = self._update_resolution_in_snapshot(
                    snapshot,
                    resolution.resolution_id,
                    {"status": status},
                )
                event = HarnessEvent(
                    sequence=updated.last_event_sequence + 1,
                    event_name=(
                        "evidence_resolution_stale"
                        if status == "stale"
                        else "evidence_resolution_rejected"
                    ),
                    occurred_at=now,
                    status=updated.status,
                    message=message,
                    details={
                        "resolution_id": resolution.resolution_id,
                        "status": status,
                        "external_action": False,
                    },
                )
                run.snapshot = updated.model_copy(
                    update={
                        "events": [*updated.events, event],
                        "last_event_sequence": event.sequence,
                        "version": updated.version + 1,
                        "updated_at": now,
                    }
                )
                await self._persist_locked(run)
            raise HarnessConflictError(message)

        if request.decision_action == "accept":
            if resolution is not None:
                if resolution.status not in {"ambiguous", "unavailable"}:
                    raise HarnessConflictError("该证据定位已经不是待决状态")
                if not request.source_revision:
                    raise HarnessConflictError("接受证据候选必须携带资料版本令牌")
                candidate_ids = {item.candidate_id for item in resolution.candidates}
                if request.selected_candidate_id not in candidate_ids:
                    await reject_resolution(
                        "候选位置不属于服务端决策单，已拒绝本次选择", "rejected"
                    )
                selected_candidate = next(
                    item
                    for item in resolution.candidates
                    if item.candidate_id == request.selected_candidate_id
                )
                expected_revision = resolution.source_revision
                supplied_revision = request.source_revision
                # Re-read the current allowlisted preview and require the same
                # server-owned candidate to still exist. A persisted quote is
                # not sufficient proof after the source revision changes.
                current_file = next(
                    (
                        item
                        for item in self.get_internal_workspace().get("files", [])
                        if str(item.get("file_ref")) == selected_candidate.file_ref
                    ),
                    None,
                )
                if current_file is None:
                    await reject_resolution("证据候选对应的资料已经不可用，已标记为 stale", "stale")
                current_revision = self._source_revision(current_file)
                if current_revision != expected_revision:
                    await reject_resolution(
                        "证据候选对应的资料版本已经变化，已标记为 stale", "stale"
                    )
                if supplied_revision not in {
                    expected_revision,
                    self._public_source_revision(expected_revision),
                }:
                    raise HarnessConflictError("资料版本令牌不匹配，请刷新后重试")
                refreshed = self._analysis_inputs([current_file])
                current_payload = refreshed[0] if refreshed else {}
                if current_payload.get("kind") == "table":
                    current_matches = self._resolve_table_anchor_candidates(
                        file_ref=selected_candidate.file_ref,
                        role=resolution.role,
                        label=resolution.label,
                        quote=selected_candidate.excerpt,
                        columns=list(current_payload.get("columns") or []),
                        rows=list(current_payload.get("rows") or []),
                    )
                else:
                    current_matches = self._resolve_text_anchor_candidates(
                        file_ref=selected_candidate.file_ref,
                        role=resolution.role,
                        label=resolution.label,
                        quote=selected_candidate.excerpt,
                        text=str(current_payload.get("text") or ""),
                    )
                refreshed_match = next(
                    (
                        match
                        for match in current_matches
                        if match.start == selected_candidate.start
                        and match.end == selected_candidate.end
                        and match.excerpt == selected_candidate.excerpt
                    ),
                    None,
                )
                if refreshed_match is None:
                    await reject_resolution(
                        "证据候选在当前资料中已无法唯一定位，已标记为 stale", "stale"
                    )
                refreshed_id = self._evidence_candidate_id(
                    resolution.resolution_id, refreshed_match
                )
                if refreshed_id != selected_candidate.candidate_id:
                    await reject_resolution("证据候选标识已变化，已拒绝本次篡改选择", "rejected")
                expected_digest = self._candidate_digest(
                    resolution_id=resolution.resolution_id,
                    file_ref=selected_candidate.file_ref,
                    locator_kind=selected_candidate.locator_kind,
                    start=selected_candidate.start,
                    end=selected_candidate.end,
                    excerpt=selected_candidate.excerpt,
                    source_revision=expected_revision,
                )
                supplied_digest = request.candidate_digest
                if supplied_digest and supplied_digest not in {
                    expected_digest,
                    self._public_candidate_digest(expected_digest),
                }:
                    raise HarnessConflictError("证据候选校验摘要不匹配")
                if request.selected_option_id is not None:
                    raise HarnessConflictError("证据位置选择不能同时提交业务选项")
            else:
                option_ids = {
                    item.option_id
                    for item in (finding.review.options if finding and finding.review else [])
                }
                if request.selected_option_id not in option_ids:
                    raise HarnessConflictError("请选择该发现中的一个处理口径")
                if request.selected_candidate_id is not None:
                    raise HarnessConflictError("业务口径选择不能同时提交证据候选")
        elif any(
            value is not None
            for value in (
                request.selected_option_id,
                request.selected_candidate_id,
            )
        ):
            raise HarnessConflictError("否决或暂缓不接受已选候选")

        if resolution is not None and resolution.affected_branch_ids:
            affected_branch_ids = resolution.affected_branch_ids
        elif resolution is not None and resolution.branch_id:
            affected_branch_ids = [resolution.branch_id]
        elif finding is not None:
            affected_branch_ids = finding.affected_branch_ids
        else:
            affected_branch_ids = []
        if resolution is not None and len(affected_branch_ids) > 1 and request.branch_id is None:
            raise HarnessConflictError("共享资料同时属于多个分支，请明确选择要恢复的分支")
        branch_id = request.branch_id or (affected_branch_ids[0] if affected_branch_ids else None)
        if (
            request.branch_id is not None
            and affected_branch_ids
            and request.branch_id not in affected_branch_ids
        ):
            raise HarnessConflictError("人工决策不能绑定到无关分支")

        now = datetime.now(timezone.utc)
        next_version = snapshot.version + 1
        decision_id = f"decision-{uuid4().hex[:12]}"
        effect: Literal["branch_resumed", "preserved", "deferred", "cancelled", "none"] = {
            "accept": "branch_resumed" if snapshot.status == "waiting_input" else "preserved",
            "decline": "preserved",
            "defer": "deferred",
            "cancel": "cancelled",
        }[request.decision_action]
        candidate_digest = None
        if resolution is not None and request.selected_candidate_id is not None:
            candidate_digest = next(
                item.candidate_digest
                for item in resolution.candidates
                if item.candidate_id == request.selected_candidate_id
            )
        resolution_updates: dict[str, Any] = {
            "decision_status": {
                "accept": "accepted",
                "decline": "declined",
                "defer": "deferred",
                "cancel": "cancelled",
            }[request.decision_action],
        }
        if request.decision_action == "accept" and resolution is not None:
            resolution_updates.update(
                {
                    "status": "exact",
                    "selected_candidate_id": request.selected_candidate_id,
                }
            )
        elif request.decision_action == "decline" and resolution is not None:
            resolution_updates["status"] = "rejected"
        record = AgentControlLoopDecisionRecord(
            decision_id=decision_id,
            decision_request_id=packet.decision_request_id if packet else None,
            action=request.decision_action,
            finding_id=finding_id,
            resolution_id=resolution.resolution_id if resolution else None,
            branch_id=branch_id,
            selected_option_id=request.selected_option_id,
            selected_candidate_id=request.selected_candidate_id,
            feedback=request.feedback,
            recorded_at=now,
            source_revision=resolution.source_revision if resolution else "",
            candidate_digest=candidate_digest,
            expected_version=snapshot.version,
            idempotency_key=request.idempotency_key,
            idempotency_ref=self._public_idempotency_ref(request.idempotency_key),
            accepted_task_version=next_version,
            applied_task_version=next_version,
            affected_branch_ids=affected_branch_ids,
            required_file_refs=[resolution.file_ref] if resolution else finding.file_refs,
            effect=effect,
        )
        control_id = f"control-{uuid4().hex[:12]}"
        control_event = AgentControlLoopControlEvent(
            control_id=control_id,
            command="decision",
            branch_id=branch_id,
            instruction=request.feedback,
            accepted_at=now,
            accepted_task_version=next_version,
            applied_task_version=next_version,
            status="applied",
        )
        action_label = {
            "accept": "已接受",
            "decline": "已否决",
            "defer": "已暂缓",
            "cancel": "已取消",
        }[request.decision_action]
        event = HarnessEvent(
            sequence=snapshot.last_event_sequence + 1,
            event_name="decision_recorded",
            occurred_at=now,
            status=snapshot.status,
            message=f"人工决定{action_label}并已写入版本化回执；尚未发生外部动作。",
            details={
                "decision_id": decision_id,
                "action": request.decision_action,
                "finding_id": finding_id,
                "resolution_id": resolution.resolution_id if resolution else None,
                "branch_id": branch_id,
                "external_action": False,
            },
        )
        updated_snapshot = snapshot.model_copy(
            update={
                "decision_records": [*snapshot.decision_records, record],
                "control_events": [*snapshot.control_events, control_event],
                "events": [*snapshot.events, event],
                "last_event_sequence": event.sequence,
                "version": next_version,
                "updated_at": now,
            }
        )
        if resolution is not None or packet is not None:
            updated_snapshot = self._update_resolution_in_snapshot(
                updated_snapshot,
                resolution.resolution_id if resolution is not None else None,
                resolution_updates,
                finding_id=finding_id,
            )
        should_schedule = (
            request.decision_action == "accept"
            and resolution is not None
            and snapshot.status == "waiting_input"
            and branch_id is not None
        )
        if should_schedule:
            updated_snapshot = updated_snapshot.model_copy(
                update={
                    "status": "planning",
                    "control_state": "running",
                    "active_branch_id": branch_id,
                }
            )
            resumed_event = HarnessEvent(
                sequence=updated_snapshot.last_event_sequence + 1,
                event_name="branch_resumed_from_checkpoint",
                occurred_at=now,
                status="planning",
                message="已从检查点只恢复目标分支；其他分支和成果版本保持不变。",
                details={"branch_id": branch_id, "external_action": False},
            )
            updated_snapshot = updated_snapshot.model_copy(
                update={
                    "events": [*updated_snapshot.events, resumed_event],
                    "last_event_sequence": resumed_event.sequence,
                }
            )
        run.snapshot = updated_snapshot
        result = HarnessControlResult(run=run.snapshot.model_copy(deep=True))
        existing = await self._persist_locked(
            run,
            StoredHarnessIdempotency(
                owner_id=owner_id,
                kind="control",
                idempotency_key=request.idempotency_key,
                digest=digest,
                result=result.model_dump(mode="json"),
            ),
        )
        if existing is not None:
            if existing.digest != digest:
                run.snapshot = snapshot
                raise HarnessConflictError("幂等键已用于不同控制命令")
            restored = HarnessControlResult.model_validate(existing.result)
            run.snapshot = restored.run.model_copy(deep=True)
            return restored.model_copy(update={"replayed": True}, deep=True)
        self._control_idempotent[idempotency_key] = _IdempotentControl(digest=digest, result=result)
        condition = run.condition
        needs_new_task = should_schedule and run.snapshot.run_id not in self._tasks
        if should_schedule:
            self._resume_active_budget(run)
            if needs_new_task:
                self._schedule_run(
                    owner_id,
                    run.snapshot.run_id,
                    self.get_internal_workspace(),
                    run.snapshot.instruction,
                )
            async with condition:
                condition.notify_all()
        return result.model_copy(deep=True)

    async def _rollback_control_locked(
        self,
        owner_id: str,
        run: _Run,
        request: AgentControlLoopControlRequest,
        *,
        digest: str,
        idempotency_key: tuple[str, str],
    ) -> HarnessControlResult:
        snapshot = run.snapshot
        if snapshot.status != "completed" or snapshot.last_commit is None:
            raise HarnessConflictError("只有已提交的任务简报可以恢复历史版本")
        if request.artifact_version is None:
            raise HarnessConflictError("恢复成果版本时必须指定目标版本")
        if (
            request.branch_id is not None
            or request.instruction is not None
            or any(
                value is not None
                for value in (
                    request.decision_action,
                    request.finding_id,
                    request.resolution_id,
                    request.selected_option_id,
                    request.selected_candidate_id,
                    request.feedback,
                )
            )
        ):
            raise HarnessConflictError("成果版本恢复不接受分支或方向指令")
        if len(snapshot.commits) >= 20:
            raise HarnessConflictError("成果提交记录已达上限，请启动新的独立任务")
        target = next(
            (
                item
                for item in snapshot.artifact_versions
                if item.version == request.artifact_version
            ),
            None,
        )
        if target is None:
            raise HarnessConflictError("目标成果版本不存在")
        if snapshot.last_commit.artifact_version == target.version:
            raise HarnessConflictError("该成果版本已经是当前版本")

        stored_versions = await self.state_store.load_artifact_versions(owner_id, snapshot.run_id)
        stored = next(
            (
                item
                for item in stored_versions
                if item.artifact_id == target.artifact_id and item.version == target.version
            ),
            None,
        )
        target_payload = target.model_dump(mode="json")
        if stored is None or stored.payload_digest != self._payload_digest(target_payload):
            raise HarnessConflictError("成果版本的不可变记录不完整，已拒绝恢复")

        now = datetime.now(timezone.utc)
        next_version = snapshot.version + 1
        commit_id = (
            "commit-"
            + hashlib.sha256(
                (
                    f"{snapshot.run_id}:rollback:{snapshot.last_commit.commit_id}:"
                    f"{target.artifact_id}:{target.version}"
                ).encode("utf-8")
            ).hexdigest()[:12]
        )
        task_commit = AgentControlLoopCommit(
            commit_id=commit_id,
            artifact_id=target.artifact_id,
            artifact_version=target.version,
            operation="rollback",
            parent_commit_id=snapshot.last_commit.commit_id,
            summary=(
                f"已将当前任务简报恢复为 v{target.version}；历史版本均保留，原始办公文件未修改。"
            ),
            committed_at=now,
        )
        control_id = f"control-{uuid4().hex[:12]}"
        control_event = AgentControlLoopControlEvent(
            control_id=control_id,
            command="rollback",
            artifact_version=target.version,
            accepted_at=now,
            accepted_task_version=next_version,
            applied_task_version=next_version,
            status="applied",
        )
        event = HarnessEvent(
            sequence=snapshot.last_event_sequence + 1,
            event_name="artifact_version_restored",
            occurred_at=now,
            status="completed",
            message=task_commit.summary,
            details={
                "artifact_version": target.version,
                "previous_artifact_version": snapshot.last_commit.artifact_version,
                "external_action": False,
            },
        )
        restored_result = (
            HarnessTaskResult(
                summary=target.summary,
                findings=[
                    HarnessFinding(
                        title=item.title,
                        detail=item.detail,
                        fact_summary=item.fact_summary,
                        impact=item.impact,
                        file_refs=item.file_refs,
                        evidence_anchors=item.evidence_anchors,
                        review=item.review,
                    )
                    for item in target.findings
                ],
                follow_ups=target.follow_ups,
                review_required=True,
            )
            if target.findings
            else None
        )
        restored_brief = AgentControlLoopBrief(
            outcome="bounded" if target.evidence_gaps else "completed",
            summary=target.summary,
            verified_file_refs=target.source_file_refs,
            unresolved_gaps=target.evidence_gaps,
            rounds_completed=target.round_number,
        )
        run.snapshot = snapshot.model_copy(
            update={
                "result": restored_result,
                "brief": restored_brief,
                "commits": [*snapshot.commits, task_commit],
                "last_commit": task_commit,
                "control_events": [*snapshot.control_events, control_event],
                "events": [*snapshot.events, event],
                "last_event_sequence": event.sequence,
                "version": next_version,
                "updated_at": now,
            }
        )
        result = HarnessControlResult(run=run.snapshot.model_copy(deep=True))
        existing = await self._persist_locked(
            run,
            StoredHarnessIdempotency(
                owner_id=owner_id,
                kind="control",
                idempotency_key=request.idempotency_key,
                digest=digest,
                result=result.model_dump(mode="json"),
            ),
            task_commit=task_commit,
        )
        if existing is not None:
            if existing.digest != digest:
                run.snapshot = snapshot
                raise HarnessConflictError("幂等键已用于不同控制命令")
            restored = HarnessControlResult.model_validate(existing.result)
            run.snapshot = restored.run.model_copy(deep=True)
            return restored.model_copy(update={"replayed": True}, deep=True)
        self._control_idempotent[idempotency_key] = _IdempotentControl(digest=digest, result=result)
        return result.model_copy(deep=True)

    def public_start_result(self, result: HarnessRunStartResult) -> PublicHarnessRunStartResult:
        return PublicHarnessRunStartResult(
            run=self.public_snapshot(result.run),
            replayed=result.replayed,
        )

    def public_snapshot(self, snapshot: HarnessRunSnapshot) -> PublicHarnessRunSnapshot:
        ref_to_label = {
            str(document.get("file_ref")): str(document.get("display_label", "所选公开办公文件"))
            for document in snapshot.source_documents
            if document.get("file_ref")
        }
        public_documents = []
        for document in snapshot.source_documents:
            public_documents.append(
                {
                    "file_ref": document.get("file_ref"),
                    "display_label": document.get("display_label", "公开办公输入文件"),
                    "display_group": document.get("display_group", "公开办公输入"),
                    "display_summary": document.get("display_summary", "公开办公输入文件"),
                }
            )
        public_plan = self._public_plan(snapshot.plan, ref_to_label)
        public_result = self._public_result(snapshot.result, ref_to_label)
        public_rounds = [
            self._public_round(round_snapshot, ref_to_label) for round_snapshot in snapshot.rounds
        ]
        public_brief = self._public_brief(snapshot.brief, ref_to_label)
        public_artifacts = [
            item.model_copy(
                update={
                    "summary": self._project_business_text(item.summary, ref_to_label),
                    "findings": [
                        finding.model_copy(
                            update={
                                "title": self._project_business_text(finding.title, ref_to_label),
                                "detail": self._project_business_text(finding.detail, ref_to_label),
                                "fact_summary": self._project_business_text(
                                    finding.fact_summary, ref_to_label
                                )
                                if finding.fact_summary
                                else None,
                                "impact": self._project_business_text(finding.impact, ref_to_label)
                                if finding.impact
                                else None,
                                "evidence_resolutions": [
                                    self._public_evidence_resolution(resolution, ref_to_label)
                                    for resolution in finding.evidence_resolutions
                                ],
                                "review": self._public_finding_review(finding.review, ref_to_label),
                            }
                        )
                        for finding in item.findings
                    ],
                    "follow_ups": [
                        self._project_business_text(follow_up, ref_to_label)
                        for follow_up in item.follow_ups
                    ],
                    "evidence_gaps": [
                        gap.model_copy(
                            update={
                                "label": self._project_business_text(gap.label, ref_to_label),
                                "detail": self._project_business_text(gap.detail, ref_to_label),
                            }
                        )
                        for gap in item.evidence_gaps
                    ],
                }
            )
            for item in snapshot.artifact_versions
        ]
        public_branches = [
            item.model_copy(
                update={
                    "title": self._project_business_text(item.title, ref_to_label),
                    "objective": self._project_business_text(item.objective, ref_to_label),
                }
            )
            for item in snapshot.branches
        ]
        public_contract = snapshot.contract.model_copy(
            update={
                "allowed_file_refs": [
                    file_ref
                    for file_ref in snapshot.contract.allowed_file_refs
                    if file_ref in ref_to_label
                ]
            }
        )
        public_events = [self.public_event(event, snapshot) for event in snapshot.events]
        public_decision_records = [
            item.model_copy(
                update={
                    "idempotency_key": None,
                    "idempotency_ref": self._public_idempotency_ref(
                        item.idempotency_key or item.idempotency_ref
                    ),
                    "source_revision": self._public_source_revision(item.source_revision)
                    if item.source_revision
                    else "",
                    "candidate_digest": None,
                }
            )
            for item in snapshot.decision_records
        ]
        public_decision_requests = [
            self._public_decision_request(item, ref_to_label, snapshot.version)
            for item in snapshot.decision_requests
        ]
        public_workspace_artifacts = [
            AgentControlLoopWorkspaceArtifact.model_validate(
                item.model_dump(exclude={"content_sha256"})
            )
            for item in snapshot.workspace_artifacts
        ]
        return PublicHarnessRunSnapshot(
            run_id=snapshot.run_id,
            task_id=snapshot.task_id,
            task_version=snapshot.task_version,
            run_sequence=snapshot.run_sequence,
            parent_run_id=snapshot.parent_run_id,
            continuation_reason=snapshot.continuation_reason,
            carried_branch_id=snapshot.carried_branch_id,
            base_artifact_version=snapshot.base_artifact_version,
            base_task_commit=snapshot.base_task_commit,
            workspace_revision=snapshot.workspace_revision,
            recheck_file_refs=snapshot.recheck_file_refs,
            source_revision_changed=snapshot.source_revision_changed,
            owner_id=snapshot.owner_id,
            workspace_id=snapshot.workspace_id,
            status=snapshot.status,
            version=snapshot.version,
            created_at=snapshot.created_at,
            updated_at=snapshot.updated_at,
            last_event_sequence=snapshot.last_event_sequence,
            source_documents=public_documents,
            selection_reason=snapshot.selection_reason,
            instruction=snapshot.instruction,
            instruction_source=snapshot.instruction_source,
            contract=public_contract,
            budget=snapshot.budget,
            rounds=public_rounds,
            current_round=snapshot.current_round,
            control_state=snapshot.control_state,
            control_events=snapshot.control_events,
            decision_records=public_decision_records,
            decision_requests=public_decision_requests,
            branches=public_branches,
            active_branch_id=snapshot.active_branch_id,
            artifact_versions=public_artifacts,
            workspace_artifacts=public_workspace_artifacts,
            effect_receipts=snapshot.effect_receipts,
            commits=snapshot.commits,
            last_commit=snapshot.last_commit,
            brief=public_brief,
            plan=public_plan,
            model_receipt=snapshot.model_receipt,
            analysis_receipt=snapshot.analysis_receipt,
            result=public_result,
            narrative_reconciliation=snapshot.narrative_reconciliation,
            validation_errors=[
                self._public_failure_message(error) for error in snapshot.validation_errors
            ],
            events=public_events,
            topology_admission=snapshot.topology_admission,
            worker_runs=snapshot.worker_runs,
            shared_artifacts=snapshot.shared_artifacts,
            work_units=[public_work_unit(item) for item in snapshot.work_units],
            contributions=[
                {
                    **public_contribution(item),
                    "summary": self._project_business_text(item.summary, ref_to_label),
                }
                for item in snapshot.contributions
            ],
        )

    def public_control_result(self, result: HarnessControlResult) -> PublicHarnessControlResult:
        return PublicHarnessControlResult(
            run=self.public_snapshot(result.run), replayed=result.replayed
        )

    def _public_plan(
        self,
        plan: HarnessPlan | None,
        ref_to_label: dict[str, str],
    ) -> PublicHarnessPlan | None:
        if plan is None:
            return None
        return PublicHarnessPlan(
            summary=self._project_business_text(plan.summary, ref_to_label),
            selection_reason=self._project_business_text(plan.selection_reason, ref_to_label),
            units=[
                PublicHarnessPlanUnit(
                    unit_id=unit.unit_id,
                    title=self._project_business_text(unit.title, ref_to_label),
                    objective=self._project_business_text(unit.objective, ref_to_label),
                    input_file_refs=unit.input_file_refs,
                    depends_on=unit.depends_on,
                    tool=unit.tool,
                    requires_human_gate=unit.requires_human_gate,
                    side_effect=unit.side_effect,
                    artifact_name=unit.artifact_name,
                    artifact_type=unit.artifact_type,
                )
                for unit in plan.units
            ],
        )

    def _public_result(
        self,
        result: HarnessTaskResult | None,
        ref_to_label: dict[str, str],
    ) -> HarnessTaskResult | None:
        if result is None:
            return None
        return HarnessTaskResult(
            summary=self._project_business_text(result.summary, ref_to_label),
            findings=[
                HarnessFinding(
                    finding_id=finding.finding_id,
                    plan_unit_id=finding.plan_unit_id,
                    affected_branch_ids=finding.affected_branch_ids,
                    title=self._project_business_text(finding.title, ref_to_label),
                    detail=self._project_business_text(finding.detail, ref_to_label),
                    fact_summary=self._project_business_text(finding.fact_summary, ref_to_label)
                    if finding.fact_summary
                    else None,
                    impact=self._project_business_text(finding.impact, ref_to_label)
                    if finding.impact
                    else None,
                    file_refs=finding.file_refs,
                    evidence_anchors=finding.evidence_anchors,
                    evidence_resolutions=[
                        self._public_evidence_resolution(item, ref_to_label)
                        for item in finding.evidence_resolutions
                    ],
                    review=self._public_finding_review(finding.review, ref_to_label),
                )
                for finding in result.findings
            ],
            follow_ups=[
                self._project_business_text(item, ref_to_label) for item in result.follow_ups
            ],
            review_required=True,
        )

    def _public_finding_review(
        self,
        review: AgentControlLoopFindingReview | None,
        ref_to_label: dict[str, str],
    ) -> AgentControlLoopFindingReview | None:
        if review is None:
            return None
        return review.model_copy(
            update={
                "question": self._project_business_text(review.question, ref_to_label),
                "why_human": self._project_business_text(review.why_human, ref_to_label),
                "recommendation_reason": self._project_business_text(
                    review.recommendation_reason, ref_to_label
                ),
                "after_confirmation": self._project_business_text(
                    review.after_confirmation, ref_to_label
                ),
                "options": [
                    option.model_copy(
                        update={
                            "label": self._project_business_text(option.label, ref_to_label),
                            "meaning": self._project_business_text(option.meaning, ref_to_label),
                            "agent_next_step": self._project_business_text(
                                option.agent_next_step, ref_to_label
                            ),
                            "next_instruction": self._project_business_text(
                                option.next_instruction, ref_to_label
                            ),
                        }
                    )
                    for option in review.options
                ],
            }
        )

    def _public_evidence_resolution(
        self,
        resolution: AgentControlLoopEvidenceResolution,
        ref_to_label: dict[str, str],
    ) -> AgentControlLoopEvidenceResolution:
        return resolution.model_copy(
            update={
                "finding_title": self._project_business_text(
                    resolution.finding_title, ref_to_label
                ),
                "fact_summary": self._project_business_text(resolution.fact_summary, ref_to_label)
                if resolution.fact_summary
                else None,
                "impact": self._project_business_text(resolution.impact, ref_to_label)
                if resolution.impact
                else None,
                "query_excerpt": self._project_business_text(
                    resolution.query_excerpt, ref_to_label
                ),
                "reason": self._project_business_text(resolution.reason, ref_to_label),
                "candidates": [
                    candidate.model_copy(
                        update={
                            "excerpt": self._project_business_text(candidate.excerpt, ref_to_label),
                            "source_revision": self._public_source_revision(
                                candidate.source_revision
                            )
                            if candidate.source_revision
                            else "",
                            "candidate_digest": "",
                        }
                    )
                    for candidate in resolution.candidates
                ],
                "source_revision": self._public_source_revision(resolution.source_revision)
                if resolution.source_revision
                else "",
            }
        )

    def _public_decision_request(
        self,
        decision_request: AgentControlLoopDecisionRequest,
        ref_to_label: dict[str, str],
        expected_version: int,
    ) -> AgentControlLoopDecisionRequest:
        return decision_request.model_copy(
            update={
                "expected_version": expected_version,
                "reason": self._project_business_text(decision_request.reason, ref_to_label),
                "consequence": self._project_business_text(
                    decision_request.consequence, ref_to_label
                ),
                "options": [
                    {
                        **option,
                        **{
                            key: self._project_business_text(str(option[key]), ref_to_label)
                            for key in (
                                "label",
                                "meaning",
                                "agent_next_step",
                                "next_instruction",
                            )
                            if key in option
                        },
                    }
                    for option in decision_request.options
                ],
                "source_revision": self._public_source_revision(decision_request.source_revision)
                if decision_request.source_revision
                else "",
                "candidates": [
                    candidate.model_copy(
                        update={
                            "excerpt": self._project_business_text(candidate.excerpt, ref_to_label),
                            "source_revision": self._public_source_revision(
                                candidate.source_revision
                            )
                            if candidate.source_revision
                            else "",
                            "candidate_digest": "",
                        }
                    )
                    for candidate in decision_request.candidates
                ],
            }
        )

    def _public_round(
        self,
        round_snapshot: AgentControlLoopRound,
        ref_to_label: dict[str, str],
    ) -> AgentControlLoopRound:
        plan = None
        if round_snapshot.plan is not None:
            plan_model = HarnessPlan.model_validate(round_snapshot.plan)
            public_plan = self._public_plan(plan_model, ref_to_label)
            plan = public_plan.model_dump(mode="json") if public_plan else None
        result = None
        if round_snapshot.result is not None:
            result_model = HarnessTaskResult.model_validate(round_snapshot.result)
            public_result = self._public_result(result_model, ref_to_label)
            result = public_result.model_dump(mode="json") if public_result else None
        gaps = [
            gap.model_copy(
                update={
                    "label": self._project_business_text(gap.label, ref_to_label),
                    "detail": self._project_business_text(gap.detail, ref_to_label),
                }
            )
            for gap in round_snapshot.evidence_gaps
        ]
        next_step = round_snapshot.next_step
        if next_step is not None:
            next_step = next_step.model_copy(
                update={
                    "reason": self._project_business_text(next_step.reason, ref_to_label),
                    "next_question": self._project_business_text(
                        next_step.next_question, ref_to_label
                    )
                    if next_step.next_question
                    else None,
                    "evidence_resolutions": [
                        self._public_evidence_resolution(item, ref_to_label)
                        for item in next_step.evidence_resolutions
                    ],
                }
            )
        return round_snapshot.model_copy(
            update={
                "question": self._project_business_text(round_snapshot.question, ref_to_label),
                "steer_instruction": self._project_business_text(
                    round_snapshot.steer_instruction, ref_to_label
                )
                if round_snapshot.steer_instruction
                else None,
                "plan": plan,
                "result": result,
                "evidence_gaps": gaps,
                "next_step": next_step,
            }
        )

    def _public_brief(
        self,
        brief: AgentControlLoopBrief | None,
        ref_to_label: dict[str, str],
    ) -> AgentControlLoopBrief | None:
        if brief is None:
            return None
        return brief.model_copy(
            update={
                "summary": self._project_business_text(brief.summary, ref_to_label),
                "unresolved_gaps": [
                    gap.model_copy(
                        update={
                            "label": self._project_business_text(gap.label, ref_to_label),
                            "detail": self._project_business_text(gap.detail, ref_to_label),
                        }
                    )
                    for gap in brief.unresolved_gaps
                ],
            }
        )

    def public_event(self, event: HarnessEvent, snapshot: HarnessRunSnapshot) -> HarnessEvent:
        path_to_ref = {
            document.get("path"): document.get("file_ref")
            for document in snapshot.source_documents
            if document.get("path")
        }
        if event.event_name == "workspace_index":
            files = []
            for document in snapshot.source_documents:
                files.append(
                    {
                        "file_ref": document.get("file_ref"),
                        "display_label": document.get("display_label", "公开办公输入文件"),
                        "display_group": document.get("display_group", "公开办公输入"),
                        "display_summary": document.get("display_summary", "公开办公输入文件"),
                    }
                )
            details = {"files": files, "reason": event.details.get("reason", "")}
        elif event.event_name in {"harness_failed", "plan_validation_rejected"}:
            details = self._sanitize_details(event.details, path_to_ref)
            if isinstance(details, dict) and "reason" in details:
                details["reason"] = self._public_failure_message(
                    str(event.details.get("reason", ""))
                )
        else:
            details = self._sanitize_details(event.details, path_to_ref)
        return event.model_copy(update={"details": details})

    @staticmethod
    def _public_failure_message(reason: str) -> str:
        if "办公资料库没有可用输入文件" in reason:
            return "办公资料库当前没有可安全读取的文件，系统已停止本轮任务。"
        if "分析结果引用了本轮计划之外的文件" in reason:
            return "分析结果引用了 Agent 本轮证据范围外的资料，系统未采用该结果。请重新运行。"
        if any(
            marker in reason
            for marker in (
                "未允许的工具",
                "未允许的副作用",
                "external_action",
                "action.preview",
            )
        ):
            return "规划使用了当前任务范围外的资料或能力，系统已安全停止。请重新规划。"
        if any(
            marker in reason
            for marker in (
                "artifact.write",
                "run_workspace_write",
                "artifact_name",
                "artifact_type",
            )
        ):
            return "规划中的成果保存信息不完整，系统已安全停止。请重新规划。"
        if "模型未返回合法" in reason or "invalid JSON" in reason:
            return "模型没有返回可用的结构化结果，本轮未继续处理。请重新运行。"
        return "本轮未通过服务端安全校验，且未发生外部动作。请重新运行。"

    @classmethod
    def _sanitize_details(cls, value: Any, path_to_ref: dict[str, str]) -> Any:
        if isinstance(value, dict):
            blocked = {"path", "input_paths", "sha256", "summary", "task_instruction", "input_dir"}
            return {
                key: cls._sanitize_details(item, path_to_ref)
                for key, item in value.items()
                if key not in blocked
            }
        if isinstance(value, list):
            return [cls._sanitize_details(item, path_to_ref) for item in value]
        if isinstance(value, str):
            return cls._redact_text(value, path_to_ref)
        return value

    @staticmethod
    def _redact_text(value: str, path_to_ref: dict[str, str]) -> str:
        redacted = value
        for path, file_ref in path_to_ref.items():
            if path:
                redacted = redacted.replace(path, file_ref)
        return (
            redacted.replace("/workspace/input", "受控工作区")
            .replace("/workspace/solution", "评测参考区")
            .replace("solution_files", "内部评测元数据")
            .replace("rubric_file_paths", "内部评测元数据")
            .replace("rubrics", "内部评测元数据")
        )

    @staticmethod
    def _project_business_text(value: str, ref_to_label: dict[str, str]) -> str:
        """Replace control references in model-authored copy with business labels."""

        projected = value
        for file_ref, label in ref_to_label.items():
            projected = projected.replace(file_ref, label)
        return re.sub(r"forte-[0-9a-f]{16}", "所选公开办公文件", projected)

    async def events(self, owner_id: str, run_id: str, after: int = 0):
        sequence = after
        while True:
            async with self._lock:
                run = self._runs.get((owner_id, run_id))
                if run is None:
                    raise HarnessNotFoundError("Harness run 不存在")
                current = run.snapshot.model_copy(deep=True)
                pending = [event for event in current.events if event.sequence > sequence]
                terminal = current.status in {
                    "ready_to_execute",
                    "completed",
                    "stopped",
                    "failed",
                }
                condition = run.condition
            for event in pending:
                sequence = event.sequence
                yield event
            if terminal:
                return
            async with condition:
                async with self._lock:
                    latest = self._require_run(owner_id, run_id).snapshot
                    if (
                        latest.status
                        in {
                            "ready_to_execute",
                            "completed",
                            "stopped",
                            "failed",
                        }
                        or latest.last_event_sequence > sequence
                    ):
                        continue
                try:
                    await asyncio.wait_for(condition.wait(), timeout=15)
                except TimeoutError:
                    yield None

    async def _run(
        self,
        owner_id: str,
        run_id: str,
        workspace: dict[str, Any],
        instruction: str,
    ) -> None:
        """Run a bounded, read-only Agent Control Loop over the whole workspace."""

        try:
            recovered = await self.get(owner_id, run_id)
            if recovered.source_documents:
                files = recovered.source_documents
            else:
                files = self._index_files(workspace)
                selection_reason = (
                    f"已冻结整个公开办公资料库的 {len(files)} 份文件索引；"
                    "Agent 将按任务目标自主检索并选择每轮证据。"
                )
                await self._set_source_documents(owner_id, run_id, files, selection_reason)
                await self._transition(
                    owner_id,
                    run_id,
                    "indexing",
                    "workspace_index",
                    "已核对并冻结整个资料库索引，Agent 将自主检索相关文件。",
                    {"files": files, "reason": selection_reason},
                )

            recovered = await self.get(owner_id, run_id)
            verified_refs = self._snapshot_verified_refs(recovered)
            all_findings = self._snapshot_findings(recovered)
            all_follow_ups = [
                follow_up
                for round_snapshot in recovered.rounds
                if round_snapshot.result
                for follow_up in HarnessTaskResult.model_validate(round_snapshot.result).follow_ups
            ]
            next_question = instruction
            evidence_recheck_refs: set[str] = set()
            target_branch_id = recovered.active_branch_id
            if recovered.recheck_file_refs:
                evidence_recheck_refs = set(recovered.recheck_file_refs)
                target_branch_id = recovered.carried_branch_id
            if recovered.rounds and recovered.rounds[-1].next_step:
                recovered_next_step = recovered.rounds[-1].next_step
                next_question = recovered_next_step.next_question or instruction
                if recovered_next_step.decision == "waiting_input":
                    target_branch = self._branch_by_id(recovered.branches, target_branch_id)
                    evidence_recheck_refs = set(
                        target_branch.missing_file_refs
                        if target_branch
                        else recovered_next_step.candidate_file_refs
                    )
            terminal_decision = "completed"

            contract = recovered.contract
            override_round = (
                recovered.rounds[-1]
                if recovered.rounds
                and recovered.rounds[-1].plan is not None
                and any(
                    event.event_name == "control_topology_override_recorded"
                    for event in recovered.events
                )
                else None
            )
            # A conservative topology choice continues the already validated
            # packet. It must not create a second Planner round.
            first_round = override_round.round_number if override_round else len(recovered.rounds) + 1
            for round_number in range(first_round, contract.max_rounds + 1):
                await self._safe_point(owner_id, run_id)
                all_remaining = [
                    item for item in files if str(item["file_ref"]) not in set(verified_refs)
                ]
                remaining = (
                    [
                        item
                        for item in all_remaining
                        if override_round is not None
                        and str(item["file_ref"]) in set(override_round.input_file_refs)
                    ]
                    if override_round is not None and round_number == override_round.round_number
                    else (
                    [
                        item
                        for item in all_remaining
                        if str(item["file_ref"]) in evidence_recheck_refs
                    ]
                    if evidence_recheck_refs
                    else all_remaining
                    )
                )
                if not remaining:
                    break

                reusing_plan = override_round is not None and round_number == override_round.round_number
                if reusing_plan:
                    question = override_round.question
                    steer = None
                    plan = HarnessPlan.model_validate(override_round.plan)
                    adopted_receipt = recovered.model_receipt or HarnessModelReceipt(
                        called=True, model=self.planner.model, elapsed_ms=0, output_used=True
                    )
                    round_refs = set(override_round.input_file_refs)
                    round_files = [item for item in remaining if str(item["file_ref"]) in round_refs]
                    branch_ids = list(override_round.branch_ids)
                else:
                    steer = await self._consume_pending_steer(owner_id, run_id)
                    question = f"{next_question}\n本轮方向调整：{steer}" if steer else next_question
                    await self._start_round(
                        owner_id,
                        run_id,
                        round_number=round_number,
                        question=question,
                        steer_instruction=steer,
                    )
                    await self._transition(
                        owner_id,
                        run_id,
                        "planning",
                        "round_started",
                        (
                            f"第 {round_number} 轮开始，正在核对上轮尚未覆盖的证据。"
                            if evidence_recheck_refs
                            else f"第 {round_number} 轮开始，正在确定本轮最小证据范围。"
                        ),
                        {
                            "round_number": round_number,
                            "remaining_file_count": len(remaining),
                            "evidence_recheck": bool(evidence_recheck_refs),
                        },
                    )
                    plan, adopted_receipt = await self._plan_with_bounded_repair(
                        owner_id,
                        run_id,
                        workspace=workspace,
                        question=question,
                        round_number=round_number,
                        remaining=remaining,
                        contract=contract,
                        steer_instruction=steer,
                        require_all_files=bool(evidence_recheck_refs),
                    )
                    round_refs = self._plan_file_refs(plan, remaining)
                    round_files = [item for item in remaining if str(item["file_ref"]) in round_refs]
                    branch_ids = await self._set_plan(
                        owner_id,
                        run_id,
                        plan,
                        round_number=round_number,
                        parent_branch_id=target_branch_id,
                    )
                if not reusing_plan:
                    await self._set_topology_admission(
                        owner_id,
                        run_id,
                        plan,
                        remaining_model_calls=max(
                            0, contract.max_model_calls - (await self.get(owner_id, run_id)).budget.model_calls_used
                        ),
                        remaining_time_seconds=max(
                            0, contract.deadline_seconds - (await self.get(owner_id, run_id)).budget.elapsed_ms // 1000
                        ),
                    )
                    await self._set_model_receipt(owner_id, run_id, adopted_receipt)
                    await self._update_round(
                        owner_id,
                        run_id,
                        round_number,
                        phase="plan",
                        input_file_refs=[str(item["file_ref"]) for item in round_files],
                        branch_ids=branch_ids,
                        plan=plan.model_dump(mode="json"),
                        model_receipt=adopted_receipt.model_dump(mode="json"),
                    )
                    await self._transition(
                        owner_id,
                        run_id,
                        "validating",
                        "plan_validation",
                        "服务端已校验本轮文件范围、工具、依赖与只读边界。",
                        {
                            "round_number": round_number,
                            "unit_count": len(plan.units),
                            "file_count": len(round_files),
                            "output_used": True,
                        },
                    )
                # Adaptive admission is a deliberately separate, user-gated
                # route. Persist the plan and validation receipt first, then
                # stop before effects or the ordinary Analyst path.
                admitted = (await self.get(owner_id, run_id)).topology_admission
                if (
                    admitted is not None
                    and admitted.mode == "adaptive_readonly_workers"
                    and admitted.user_confirmation_required
                ):
                    await self._transition(
                        owner_id,
                        run_id,
                        "waiting_input",
                        "topology_confirmation_required",
                        "拓扑已准入受限只读 Worker；等待用户明确确认后才会调用 Analyst Worker。",
                        {
                            "mode": admitted.mode,
                            "independent_branch_count": admitted.independent_branch_count,
                            "worker_limit": 3,
                            "external_action": False,
                        },
                    )
                    return
                # Deterministic office tools are admitted by the validated task
                # contract, not by the Analyst's prose.  Persist their files and
                # verifier receipts before narrative analysis so a rejected model
                # response cannot erase already completed, server-checked work.
                await self._apply_scenario_effect(owner_id, run_id, round_number=round_number)
                await self._safe_point(owner_id, run_id)
                verified_effect_context = self._verified_effect_context(
                    await self.get(owner_id, run_id)
                )

                if self.analyst is None:
                    await self._transition(
                        owner_id,
                        run_id,
                        "ready_to_execute",
                        "ready_to_execute",
                        "本轮计划已校验，但分析执行器尚未配置。",
                        {"round_number": round_number, "external_action": False},
                    )
                    return

                await self._update_round(owner_id, run_id, round_number, phase="act")
                analysis_files = self._analysis_inputs(round_files)
                result: HarnessTaskResult | None = None
                analysis_receipt: HarnessModelReceipt | None = None
                validation_feedback: str | None = None
                best_result: HarnessTaskResult | None = None
                best_receipt: HarnessModelReceipt | None = None
                best_rejected_count = 0
                best_score: tuple[int, int, int, int] | None = None
                best_out_of_scope_count = 0
                best_downgraded_review_count = 0
                best_evidence_resolutions: list[AgentControlLoopEvidenceResolution] = []
                pending_evidence_resolutions: list[AgentControlLoopEvidenceResolution] = []
                omitted_finding_count = 0
                scope_filtered_finding_count = 0
                downgraded_review_count = 0
                recovery_kind: Literal["source_location", "analysis_output"] = "source_location"
                for analysis_attempt in (1, 2):
                    try:
                        candidate, candidate_receipt = await self._invoke_analyst(
                            owner_id=owner_id,
                            run_id=run_id,
                            round_number=round_number,
                            instruction=question,
                            plan=plan,
                            files=analysis_files,
                            verified_effect_context=verified_effect_context,
                            attempt=analysis_attempt,
                            validation_feedback=validation_feedback,
                        )
                    except HarnessModelError as exc:
                        recovery_kind = "analysis_output"
                        await self._transition(
                            owner_id,
                            run_id,
                            "analyzing",
                            "analysis_structure_rejected",
                            (
                                "分析模型返回内容不符合可核对格式，正在受控重试。"
                                if analysis_attempt == 1
                                else "修复后的分析内容仍不符合可核对格式，未采用。"
                            ),
                            {
                                "round_number": round_number,
                                "attempt": analysis_attempt,
                                "model_called": exc.called,
                                "output_used": False,
                            },
                        )
                        if analysis_attempt == 1:
                            validation_feedback = (
                                "上一候选没有通过严格 JSON 结构校验。请只输出 schema 要求的 JSON，"
                                "每条 Finding 只描述一个问题；若不能生成完整 review，请省略 review，"
                                "不要添加 Markdown、解释文字或额外字段。"
                            )
                            continue
                        break
                    await self._safe_point(owner_id, run_id)
                    try:
                        original_unit_ids = [finding.plan_unit_id for finding in candidate.findings]
                        candidate = self._validate_candidate_result_scope(
                            candidate, round_files, plan
                        )
                        rebound_count = sum(
                            before != finding.plan_unit_id
                            for before, finding in zip(
                                original_unit_ids, candidate.findings, strict=True
                            )
                        )
                        if rebound_count:
                            await self._transition(
                                owner_id,
                                run_id,
                                "analyzing",
                                "analysis_scope_normalized",
                                (
                                    f"服务端根据文件范围重新绑定 {rebound_count} 条发现的任务分支；"
                                    "没有扩大本轮允许范围。"
                                ),
                                {
                                    "round_number": round_number,
                                    "attempt": analysis_attempt,
                                    "rebound_finding_count": rebound_count,
                                    "external_action": False,
                                },
                            )
                        resolution = self._resolve_evidence_anchors(
                            candidate,
                            analysis_files,
                            {
                                str(item["file_ref"]): self._source_revision(item)
                                for item in round_files
                            },
                            instruction,
                        )
                        if resolution.result is not None:
                            self._validate_result(resolution.result, round_files)
                    except HarnessPlanError as exc:
                        await self._transition(
                            owner_id,
                            run_id,
                            "analyzing",
                            "analysis_validation_rejected",
                            (
                                "候选结论缺少可唯一定位的原文，未采用。"
                                if analysis_attempt == 1
                                else "修复后的候选结论仍无法唯一定位原文，未采用。"
                            ),
                            {
                                "round_number": round_number,
                                "attempt": analysis_attempt,
                                "model": candidate_receipt.model,
                                "model_called": True,
                                "output_used": False,
                                "reason": str(exc)[:240],
                            },
                        )
                        if analysis_attempt == 2:
                            raise
                        validation_feedback = (
                            "上一候选至少有一条 Finding 没有任何 quote 能在对应文件中唯一匹配。"
                            "请重新生成全部 findings；每条至少选择一段更长、连续、只出现一次的原文，"
                            "不要复用会在日志中重复出现的短句。"
                        )
                        continue
                    if resolution.result is not None:
                        resolution_score = (
                            int(
                                not resolution.rejected_finding_count
                                and not resolution.evidence_resolutions
                            ),
                            len(resolution.result.findings),
                            -resolution.rejected_finding_count,
                            -len(resolution.evidence_resolutions),
                        )
                        if best_score is None or resolution_score > best_score:
                            best_score = resolution_score
                            best_result = resolution.result
                            best_receipt = candidate_receipt
                            best_rejected_count = resolution.rejected_finding_count
                            best_out_of_scope_count = resolution.out_of_scope_finding_count
                            best_downgraded_review_count = resolution.downgraded_review_count
                            best_evidence_resolutions = list(resolution.evidence_resolutions)
                    elif resolution.result is None:
                        pending_evidence_resolutions = list(resolution.evidence_resolutions)
                    if (
                        resolution.result is not None
                        and not resolution.rejected_finding_count
                        and not resolution.evidence_resolutions
                    ):
                        result = resolution.result
                        analysis_receipt = candidate_receipt
                        pending_evidence_resolutions = []
                        scope_filtered_finding_count = resolution.out_of_scope_finding_count
                        downgraded_review_count = resolution.downgraded_review_count
                        break
                    await self._transition(
                        owner_id,
                        run_id,
                        "analyzing",
                        "analysis_validation_rejected",
                        (
                            "候选结论中仍有部分内容无法唯一定位，正在重新定位。"
                            if analysis_attempt == 1
                            else "修复后仍有内容无法唯一定位，服务端只保留可核对部分。"
                        ),
                        {
                            "round_number": round_number,
                            "attempt": analysis_attempt,
                            "model": candidate_receipt.model,
                            "model_called": True,
                            "output_used": False,
                            "adoptable_finding_count": len(resolution.result.findings)
                            if resolution.result
                            else 0,
                            "rejected_finding_count": resolution.rejected_finding_count,
                            "pending_resolution_count": len(resolution.evidence_resolutions),
                        },
                    )
                    if analysis_attempt == 1:
                        validation_feedback = (
                            "上一候选至少有一条逐字引用无法在对应文件中唯一匹配。"
                            "请保留任务目标与筛选范围并重新生成全部 findings；每条至少选择一段更长、连续、只出现一次的原文，"
                            "表格请组合能唯一定位整行的关键单元格，不要复用日志中的重复短句。"
                        )
                        continue
                    result = best_result
                    analysis_receipt = best_receipt
                    omitted_finding_count = best_rejected_count
                    scope_filtered_finding_count = best_out_of_scope_count
                    downgraded_review_count = best_downgraded_review_count
                    pending_evidence_resolutions = best_evidence_resolutions

                if result is None or analysis_receipt is None:
                    branches = await self._reconcile_branches(
                        owner_id,
                        run_id,
                        verified_refs=verified_refs,
                        through_round=round_number,
                    )
                    waiting_branches = [item for item in branches if item.status == "waiting_input"]
                    pending_evidence_resolutions = self._bind_evidence_resolutions_to_branches(
                        pending_evidence_resolutions, branches
                    )
                    outstanding_refs = list(
                        dict.fromkeys(
                            file_ref
                            for branch in waiting_branches
                            for file_ref in branch.missing_file_refs
                        )
                    )
                    gaps = self._branch_evidence_gaps(waiting_branches)
                    can_continue = await self._can_start_another_round(
                        owner_id, run_id, round_number, bool(waiting_branches)
                    )
                    decision = "waiting_input" if can_continue else "budget_exhausted"
                    if recovery_kind == "analysis_output":
                        reason = (
                            "分析模型已经响应，但返回内容未形成服务端可核对的结构。"
                            "本轮计划、文件范围和调用记录已保留；请缩小到一个分支后继续。"
                            if can_continue
                            else "分析模型已经响应，但返回内容仍未形成可核对结构；当前预算不足以再次核对，"
                            "系统已保留计划与调用记录并安全停止。"
                        )
                    else:
                        reason = (
                            "模型已返回候选结论，但服务端无法把原文片段唯一定位到安全预览。"
                            "本轮计划、文件范围和模型调用记录已保留；请缩小到一个分支后继续。"
                            if can_continue
                            else "模型已返回候选结论，但原文仍无法唯一定位；当前预算不足以再次核对，"
                            "系统已保留计划与调用记录并安全停止。"
                        )
                    next_step = AgentControlLoopNextStep(
                        decision=decision,
                        reason=reason,
                        next_question=(
                            "只核对所选分支，用更长且唯一的原文定位关键事实；若仍无法定位，明确列出缺少的版本、字段或记录。"
                            if can_continue
                            else None
                        ),
                        candidate_file_refs=outstanding_refs[:20],
                        candidate_branch_ids=[item.branch_id for item in waiting_branches],
                        recovery_kind=recovery_kind,
                        evidence_resolutions=pending_evidence_resolutions[:20],
                    )
                    ambiguous_count = len(
                        [
                            item
                            for item in pending_evidence_resolutions
                            if item.status == "ambiguous"
                        ]
                    )
                    if ambiguous_count:
                        await self._transition(
                            owner_id,
                            run_id,
                            "analyzing",
                            "evidence_disambiguation_required",
                            (
                                f"有 {ambiguous_count} 条引用匹配到多个原文位置；"
                                "只暂停受影响分支，等待用户选择。"
                            ),
                            {
                                "round_number": round_number,
                                "resolution_ids": [
                                    item.resolution_id
                                    for item in pending_evidence_resolutions
                                    if item.status == "ambiguous"
                                ],
                                "external_action": False,
                            },
                        )
                    await self._transition(
                        owner_id,
                        run_id,
                        "analyzing",
                        "analysis_recovery_required",
                        reason,
                        {
                            "round_number": round_number,
                            "decision": decision,
                            "candidate_file_refs": next_step.candidate_file_refs,
                            "candidate_branch_ids": next_step.candidate_branch_ids,
                            "external_action": False,
                        },
                    )
                    await self._complete_round(
                        owner_id,
                        run_id,
                        round_number,
                        gaps=gaps,
                        next_step=next_step,
                    )
                    gate_details = {
                        "round_number": round_number,
                        "decision": decision,
                        "gap_count": len(gaps),
                        "candidate_file_refs": next_step.candidate_file_refs,
                        "candidate_branch_ids": next_step.candidate_branch_ids,
                        "recovery_kind": recovery_kind,
                    }
                    if decision == "waiting_input":
                        await self._wait_for_evidence_confirmation(
                            owner_id, run_id, reason, gate_details
                        )
                        resumed = await self.get(owner_id, run_id)
                        target_branch_id = resumed.active_branch_id
                        target_branch = self._branch_by_id(resumed.branches, target_branch_id)
                        evidence_recheck_refs = set(
                            target_branch.missing_file_refs
                            if target_branch
                            else next_step.candidate_file_refs
                        )
                        next_question = (
                            f"只核对‘{target_branch.title}’分支，用更长且唯一的原文定位关键事实；"
                            "若仍无法定位，明确列出缺少的版本、字段或记录。"
                            if target_branch
                            else next_step.next_question or instruction
                        )
                        continue
                    await self._transition(
                        owner_id,
                        run_id,
                        "verifying",
                        "evidence_gate",
                        reason,
                        gate_details,
                    )
                    terminal_decision = decision
                    break

                if scope_filtered_finding_count:
                    await self._transition(
                        owner_id,
                        run_id,
                        "analyzing",
                        "analysis_scope_filtered",
                        (
                            f"服务端省略 {scope_filtered_finding_count} 条超出用户筛选范围的候选发现；"
                            "这些内容不会阻塞当前任务。"
                        ),
                        {
                            "round_number": round_number,
                            "filtered_finding_count": scope_filtered_finding_count,
                            "output_used": False,
                            "external_action": False,
                        },
                    )
                if downgraded_review_count:
                    await self._transition(
                        owner_id,
                        run_id,
                        "analyzing",
                        "decision_gate_suppressed",
                        (
                            f"服务端将 {downgraded_review_count} 条缺少矛盾证据的人工决策候选降为普通复核；"
                            "明确规则不会被升级为用户阻塞。"
                        ),
                        {
                            "round_number": round_number,
                            "suppressed_review_count": downgraded_review_count,
                            "output_used": False,
                            "external_action": False,
                        },
                    )
                if omitted_finding_count:
                    await self._transition(
                        owner_id,
                        run_id,
                        "analyzing",
                        "analysis_partial_candidate",
                        (
                            f"服务端保留 {len(result.findings)} 条可唯一定位的候选发现，"
                            f"省略 {omitted_finding_count} 条无法核对的候选内容。"
                        ),
                        {
                            "round_number": round_number,
                            "candidate_finding_count": len(result.findings),
                            "omitted_finding_count": omitted_finding_count,
                            "output_used": False,
                        },
                    )
                current_effect_context = self._verified_effect_context(
                    await self.get(owner_id, run_id)
                )
                narrative_reconciliation = reconcile_narrative(
                    run_id=run_id,
                    round_number=round_number,
                    result=result,
                    context_used=verified_effect_context,
                    current_context=current_effect_context,
                )
                await self._record_narrative_reconciliation(
                    owner_id,
                    run_id,
                    round_number=round_number,
                    result=result,
                    reconciliation=narrative_reconciliation,
                )
                narrative_adopted = narrative_reconciliation.model_disposition == "adopted"
                if not narrative_adopted:
                    # Rejected or supplemental model drafts are audit-only. Their
                    # locator gaps must not reopen branches whose deterministic
                    # workspace effect has already been verified.
                    pending_evidence_resolutions = []
                adopted_analysis = analysis_receipt.model_copy(
                    update={"output_used": narrative_adopted}
                )
                await self._transition(
                    owner_id,
                    run_id,
                    "analyzing",
                    (
                        "narrative_reconciliation_rejected"
                        if narrative_reconciliation.model_disposition == "rejected"
                        else "narrative_reconciliation_completed"
                    ),
                    narrative_reconciliation.message,
                    {
                        "round_number": round_number,
                        "status": narrative_reconciliation.status,
                        "authority": narrative_reconciliation.authority,
                        "model_disposition": narrative_reconciliation.model_disposition,
                        "model_returned": True,
                        "output_used": narrative_adopted,
                        "conflict_count": len(narrative_reconciliation.conflicts),
                        "conflict_kinds": list(
                            dict.fromkeys(
                                item.kind for item in narrative_reconciliation.conflicts
                            )
                        ),
                        "external_action": False,
                    },
                )
                if narrative_adopted and omitted_finding_count:
                    await self._transition(
                        owner_id,
                        run_id,
                        "analyzing",
                        "analysis_partial_adopted",
                        (
                            f"服务端采用 {len(result.findings)} 条可核对发现，"
                            f"省略 {omitted_finding_count} 条无法核对的候选内容。"
                        ),
                        {
                            "round_number": round_number,
                            "adopted_finding_count": len(result.findings),
                            "omitted_finding_count": omitted_finding_count,
                            "output_used": True,
                            "external_action": False,
                        },
                    )
                binding_snapshot = await self.get(owner_id, run_id)
                result = self._bind_result_to_branches(
                    result,
                    binding_snapshot.branches,
                    estimated_additional_rounds=max(0, contract.max_rounds - round_number),
                )
                pending_evidence_resolutions = self._bind_evidence_resolutions_to_branches(
                    pending_evidence_resolutions,
                    binding_snapshot.branches,
                )
                await self._set_analysis_receipt(owner_id, run_id, adopted_analysis)
                await self._update_round(
                    owner_id,
                    run_id,
                    round_number,
                    phase="act",
                    analysis_receipt=adopted_analysis.model_dump(mode="json"),
                    narrative_reconciliation=narrative_reconciliation,
                )
                if narrative_adopted:
                    round_verified = self._result_file_refs(result, round_files)
                else:
                    effect_source_refs: set[str] = set()
                    if narrative_reconciliation.effect_receipt_id:
                        effect_receipt = next(
                            (
                                item
                                for item in binding_snapshot.effect_receipts
                                if item.receipt_id
                                == narrative_reconciliation.effect_receipt_id
                            ),
                            None,
                        )
                        if effect_receipt is not None and effect_receipt.status == "passed":
                            effect_source_refs.update(effect_receipt.source_file_refs)
                    round_verified = [
                        str(item["file_ref"])
                        for item in round_files
                        if str(item["file_ref"]) in effect_source_refs
                    ]
                unresolved_file_refs = {
                    item.file_ref for item in pending_evidence_resolutions if item.status != "exact"
                }
                round_verified = [
                    item for item in round_verified if item not in unresolved_file_refs
                ]
                for file_ref in round_verified:
                    if file_ref not in verified_refs:
                        verified_refs.append(file_ref)
                if narrative_adopted:
                    all_findings.extend(result.findings)
                    all_follow_ups.extend(result.follow_ups)
                await self._update_round(
                    owner_id,
                    run_id,
                    round_number,
                    phase="verify",
                    result=(result.model_dump(mode="json") if narrative_adopted else None),
                    analysis_receipt=adopted_analysis.model_dump(mode="json"),
                    narrative_reconciliation=narrative_reconciliation,
                    verified_file_refs=round_verified,
                )
                branches = await self._reconcile_branches(
                    owner_id,
                    run_id,
                    verified_refs=verified_refs,
                    through_round=round_number,
                )
                await self._set_verified_count(owner_id, run_id, len(verified_refs))
                await self._transition(
                    owner_id,
                    run_id,
                    "verifying",
                    "result_validation",
                    (
                        "服务端已核对本轮模型说明，并与确定性成果完成对账。"
                        if narrative_reconciliation.authority == "deterministic_outcome"
                        else "服务端已核对本轮结论的文件引用、原文定位与只读边界。"
                    ),
                    {
                        "round_number": round_number,
                        "finding_count": len(result.findings) if narrative_adopted else 0,
                        "model_candidate_finding_count": len(result.findings),
                        "verified_file_count": len(round_verified),
                        "evidence_anchor_count": sum(
                            len(finding.evidence_anchors) for finding in result.findings
                        ),
                        "omitted_finding_count": omitted_finding_count,
                        "output_used": narrative_adopted,
                        "narrative_reconciliation_status": narrative_reconciliation.status,
                        "model_disposition": narrative_reconciliation.model_disposition,
                    },
                )
                await self._safe_point(owner_id, run_id)

                waiting_branches = [item for item in branches if item.status == "waiting_input"]
                outstanding_refs = list(
                    dict.fromkeys(
                        file_ref
                        for branch in waiting_branches
                        for file_ref in branch.missing_file_refs
                    )
                )
                gaps = self._branch_evidence_gaps(waiting_branches)
                can_continue = await self._can_start_another_round(
                    owner_id, run_id, round_number, bool(waiting_branches)
                )
                if not waiting_branches:
                    decision = "completed"
                    reason = (
                        "成果已完成，模型说明未采用，以服务端全量复算为准。"
                        if narrative_reconciliation.model_disposition == "rejected"
                        else "成果已完成；模型说明只作补充，以服务端全量复算为准。"
                        if narrative_reconciliation.model_disposition == "supplemental"
                        else "所有任务分支的证据均已核对，完成条件已满足。"
                    )
                    next_question = ""
                elif can_continue:
                    decision = "waiting_input"
                    reason = (
                        f"仍有 {len(waiting_branches)} 个任务分支缺少可核对证据，"
                        "需要你选择一个分支，再使用一轮预算继续。"
                    )
                    next_question = (
                        "继续核对尚未被结论引用的资料，补齐证据缺口并检查是否改变已有结论。"
                    )
                else:
                    decision = "budget_exhausted"
                    reason = (
                        f"仍有 {len(waiting_branches)} 个任务分支缺少可核对证据，"
                        "但轮次、模型调用或时间预算已到边界。"
                    )
                    terminal_decision = decision
                next_step = AgentControlLoopNextStep(
                    decision=decision,
                    reason=reason,
                    next_question=next_question or None,
                    candidate_file_refs=outstanding_refs[:20],
                    candidate_branch_ids=[item.branch_id for item in waiting_branches],
                    recovery_kind=("source_location" if pending_evidence_resolutions else None),
                    evidence_resolutions=pending_evidence_resolutions[:20],
                )
                if any(item.status == "ambiguous" for item in pending_evidence_resolutions):
                    await self._transition(
                        owner_id,
                        run_id,
                        "verifying",
                        "evidence_disambiguation_required",
                        "部分引用匹配到多个位置；可核对发现与已有成果已保留，只暂停受影响分支。",
                        {
                            "round_number": round_number,
                            "resolution_ids": [
                                item.resolution_id
                                for item in pending_evidence_resolutions
                                if item.status == "ambiguous"
                            ],
                            "external_action": False,
                        },
                    )
                if narrative_adopted and any(
                    finding.review and finding.review.requires_human_decision
                    for finding in result.findings
                ):
                    await self._transition(
                        owner_id,
                        run_id,
                        "verifying",
                        "decision_requested",
                        "已形成需要人工判断的处置单；Agent 不会替用户批准或执行。",
                        {
                            "round_number": round_number,
                            "finding_ids": [
                                finding.finding_id
                                for finding in result.findings
                                if finding.finding_id
                                and finding.review
                                and finding.review.requires_human_decision
                            ],
                            "external_action": False,
                        },
                    )
                await self._complete_round(
                    owner_id,
                    run_id,
                    round_number,
                    gaps=gaps,
                    next_step=next_step,
                )
                if omitted_finding_count:
                    await self._transition(
                        owner_id,
                        run_id,
                        "verifying",
                        "partial_artifact_saved",
                        "可核对发现已写入新的只读成果版本；未定位内容保留为待处理证据状态。",
                        {
                            "round_number": round_number,
                            "adopted_finding_count": len(result.findings),
                            "pending_resolution_count": len(pending_evidence_resolutions),
                            "external_action": False,
                        },
                    )
                gate_details = {
                    "round_number": round_number,
                    "decision": decision,
                    "gap_count": len(gaps),
                    "candidate_file_refs": next_step.candidate_file_refs,
                    "candidate_branch_ids": next_step.candidate_branch_ids,
                }
                if decision == "waiting_input":
                    await self._wait_for_evidence_confirmation(
                        owner_id, run_id, reason, gate_details
                    )
                    resumed = await self.get(owner_id, run_id)
                    target_branch_id = resumed.active_branch_id
                    target_branch = self._branch_by_id(resumed.branches, target_branch_id)
                    evidence_recheck_refs = set(
                        target_branch.missing_file_refs
                        if target_branch
                        else next_step.candidate_file_refs
                    )
                    next_question = (
                        f"继续核对“{target_branch.title}”分支缺少的证据，检查是否改变已有结论。"
                        if target_branch
                        else next_question
                    )
                    continue
                await self._transition(
                    owner_id,
                    run_id,
                    "verifying",
                    "evidence_gate",
                    reason,
                    gate_details,
                )
                if decision != "next_round":
                    terminal_decision = decision
                    break

            await self._safe_point(owner_id, run_id)
            await self._finalize_loop(
                owner_id,
                run_id,
                findings=all_findings,
                follow_ups=all_follow_ups,
                verified_refs=verified_refs,
                decision=terminal_decision,
            )
        except HarnessStopped:
            await self._finalize_loop(
                owner_id,
                run_id,
                findings=self._snapshot_findings(await self.get(owner_id, run_id)),
                follow_ups=[],
                verified_refs=self._snapshot_verified_refs(await self.get(owner_id, run_id)),
                decision="user_stopped",
            )
        except HarnessBudgetExhausted as exc:
            snapshot = await self.get(owner_id, run_id)
            await self._finalize_loop(
                owner_id,
                run_id,
                findings=self._snapshot_findings(snapshot),
                follow_ups=[],
                verified_refs=self._snapshot_verified_refs(snapshot),
                decision="budget_exhausted",
                budget_reason=str(exc),
            )
        except Exception as exc:
            runtime_logger.warning(
                "harness_run_failed run_id=%s error=%s reason=%s",
                run_id,
                type(exc).__name__,
                str(exc),
            )
            await self._mark_current_round_failed(owner_id, run_id)
            await self._fail(owner_id, run_id, str(exc)[:500])

    @staticmethod
    def _verified_effect_context(snapshot: HarnessRunSnapshot) -> dict[str, Any] | None:
        for receipt in reversed(snapshot.effect_receipts):
            context = build_verified_effect_context(receipt)
            if context is not None:
                return context
        return None

    async def _record_narrative_reconciliation(
        self,
        owner_id: str,
        run_id: str,
        *,
        round_number: int,
        result: HarnessTaskResult,
        reconciliation: AgentControlLoopNarrativeReconciliation,
    ) -> None:
        draft = HarnessNarrativeAuditDraft(
            round_number=round_number,
            outcome_revision=reconciliation.outcome_revision,
            result=result,
            reconciliation=reconciliation,
            recorded_at=datetime.now(timezone.utc),
        )
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            rounds = [
                item.model_copy(update={"narrative_reconciliation": reconciliation})
                if item.round_number == round_number
                else item
                for item in run.snapshot.rounds
            ]
            drafts = [
                item
                for item in run.snapshot.narrative_audit_drafts
                if item.round_number != round_number
            ]
            drafts.append(draft)
            run.snapshot = run.snapshot.model_copy(
                update={
                    "rounds": rounds,
                    "narrative_reconciliation": reconciliation,
                    "narrative_audit_drafts": drafts[-24:],
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            await self._persist_locked(run)

    async def _apply_scenario_effect(
        self, owner_id: str, run_id: str, *, round_number: int
    ) -> None:
        """Run one deterministic office adapter without blocking the API loop."""

        if self.effect_engine is None or self.artifact_store is None:
            return
        snapshot = await self.get(owner_id, run_id)
        spec = self.effect_engine.match(snapshot.instruction)
        if spec is None:
            return
        inflight_key = (owner_id, run_id, spec.capability_id)
        async with self._lock:
            current = self._require_run(owner_id, run_id).snapshot
            if (
                any(
                    receipt.capability_id == spec.capability_id
                    for receipt in current.effect_receipts
                )
                or inflight_key in self._effect_inflight
            ):
                return
            self._effect_inflight.add(inflight_key)

        try:
            frozen = self.effect_engine.freeze(snapshot.instruction, self.catalog)
            if frozen is None:
                return
            latest = await self.get(owner_id, run_id)
            await self._transition(
                owner_id,
                run_id,
                latest.status,
                "deterministic_office_tool_started",
                (
                    "正在复制隔离副本并运行修复前、修复后真实测试；期间仍可查看资料与任务状态。"
                    if spec.scenario_id == "TC-04"
                    else "正在读取冻结资料并生成隔离工作区成果；本次不额外调用模型。"
                ),
                {
                    "capability_id": spec.capability_id,
                    "scenario_id": spec.scenario_id,
                    "frozen_source_file_count": len(frozen.source_file_refs),
                    "execution_mode": "in_process_worker_thread",
                    "progress_percent": None,
                    "external_action": False,
                },
            )
            execution = await asyncio.to_thread(
                self.effect_engine.execute,
                snapshot.instruction,
                frozen.catalog,
            )
            if execution is None:
                raise HarnessError("确定性办公工具未返回执行结果")
            if spec.scenario_id in {"TC-10", "TC-14"}:
                for file_ref in frozen.source_file_refs:
                    if (
                        self.catalog.checked_input_bytes(file_ref)
                        != frozen.catalog.checked_input_bytes(file_ref)
                    ):
                        raise HarnessError("Operations-008 原始来源在成果生成期间发生变化")
            await self._record_scenario_effect(
                owner_id,
                run_id,
                round_number=round_number,
                execution=execution,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            latest = await self.get(owner_id, run_id)
            await self._transition(
                owner_id,
                run_id,
                latest.status,
                "scenario_effect_failed",
                (
                    "隔离副本复制或真实测试未完成；未生成可验证成果，此前状态已保留。"
                    if spec.scenario_id == "TC-04"
                    else "确定性办公工具未完成；未生成可验证成果，此前状态已保留。"
                ),
                {
                    "capability_id": spec.capability_id,
                    "scenario_id": spec.scenario_id,
                    "error_type": type(exc).__name__,
                    "external_action": False,
                },
            )
            raise
        finally:
            async with self._lock:
                self._effect_inflight.discard(inflight_key)

    async def _record_scenario_effect(
        self,
        owner_id: str,
        run_id: str,
        *,
        round_number: int,
        execution: ScenarioEffectExecution,
    ) -> None:
        if self.artifact_store is None:
            raise HarnessError("运行成果存储尚未配置")
        now = datetime.now(timezone.utc)
        records: list[HarnessWorkspaceArtifactRecord] = []
        for generated in execution.artifacts:
            artifact_id = (
                "workspace-artifact-"
                + hashlib.sha256(
                    f"{run_id}:{execution.scenario_id}:{generated.file_name}:v1".encode("utf-8")
                ).hexdigest()[:12]
            )
            try:
                stored = self.artifact_store.write(
                    owner_id=owner_id,
                    run_id=run_id,
                    artifact_id=artifact_id,
                    file_name=generated.file_name,
                    content=generated.content,
                )
            except RunWorkspaceArtifactError as exc:
                raise HarnessError(str(exc)) from exc
            records.append(
                HarnessWorkspaceArtifactRecord(
                    artifact_id=artifact_id,
                    capability_id=execution.capability_id,
                    scenario_id=execution.scenario_id,
                    title=generated.title,
                    file_name=generated.file_name,
                    media_type=generated.media_type,
                    size=stored.size,
                    version=1,
                    round_number=round_number,
                    source_file_refs=list(generated.source_file_refs),
                    validator_id=generated.validator_id,
                    verifier_status=generated.verifier_status,
                    checks=list(generated.checks),
                    summary=generated.summary,
                    covered_period=generated.covered_period,
                    statistic_basis=generated.statistic_basis,
                    purpose=generated.purpose,
                    record_count=generated.record_count,
                    deliverable_type=generated.deliverable_type,
                    key_outputs=list(generated.key_outputs),
                    key_outputs_label=generated.key_outputs_label,
                    review_guidance=generated.review_guidance,
                    execution_summary=generated.execution_summary,
                    self_test=generated.self_test,
                    business_gate_outcome=generated.business_gate_outcome,
                    legal_review_outcome=generated.legal_review_outcome,
                    candidate_review_outcome=generated.candidate_review_outcome,
                    finance_review_outcome=generated.finance_review_outcome,
                    outbound_flow_outcome=generated.outbound_flow_outcome,
                    customer_segmentation_outcome=generated.customer_segmentation_outcome,
                    sre_diagnosis_outcome=generated.sre_diagnosis_outcome,
                    ux_prioritization_outcome=generated.ux_prioritization_outcome,
                    download_path=(f"/v1/harness/runs/{run_id}/artifacts/{artifact_id}"),
                    created_at=now,
                    content_sha256=stored.sha256,
                )
            )

        receipt_id = (
            "effect-receipt-"
            + hashlib.sha256(
                f"{run_id}:{execution.scenario_id}:{execution.capability_id}".encode("utf-8")
            ).hexdigest()[:12]
        )
        business_outcomes = [
            item.business_gate_outcome for item in records if item.business_gate_outcome is not None
        ]
        business_outcome = business_outcomes[0] if business_outcomes else None
        if business_outcomes and any(item != business_outcome for item in business_outcomes[1:]):
            raise HarnessError("同一效果的业务 Gate 事实不一致")
        legal_outcomes = [
            item.legal_review_outcome for item in records if item.legal_review_outcome is not None
        ]
        legal_outcome = legal_outcomes[0] if legal_outcomes else None
        if legal_outcomes and any(item != legal_outcome for item in legal_outcomes[1:]):
            raise HarnessError("同一效果的法务核查事实不一致")
        candidate_outcomes = [
            item.candidate_review_outcome
            for item in records
            if item.candidate_review_outcome is not None
        ]
        candidate_outcome = candidate_outcomes[0] if candidate_outcomes else None
        if candidate_outcomes and any(item != candidate_outcome for item in candidate_outcomes[1:]):
            raise HarnessError("同一效果的候选人辅助筛选事实不一致")
        finance_outcomes = [
            item.finance_review_outcome
            for item in records
            if item.finance_review_outcome is not None
        ]
        finance_outcome = finance_outcomes[0] if finance_outcomes else None
        if finance_outcomes and any(item != finance_outcome for item in finance_outcomes[1:]):
            raise HarnessError("同一效果的财务复核事实不一致")
        outbound_outcomes = [
            item.outbound_flow_outcome
            for item in records
            if item.outbound_flow_outcome is not None
        ]
        outbound_outcome = outbound_outcomes[0] if outbound_outcomes else None
        if outbound_outcomes and any(item != outbound_outcome for item in outbound_outcomes[1:]):
            raise HarnessError("同一效果的外呼流程覆盖事实不一致")
        customer_outcomes = [
            item.customer_segmentation_outcome
            for item in records
            if item.customer_segmentation_outcome is not None
        ]
        customer_outcome = customer_outcomes[0] if customer_outcomes else None
        if customer_outcomes and any(item != customer_outcome for item in customer_outcomes[1:]):
            raise HarnessError("同一效果的客户画像清洗事实不一致")
        sre_outcomes = [
            item.sre_diagnosis_outcome
            for item in records
            if item.sre_diagnosis_outcome is not None
        ]
        sre_outcome = sre_outcomes[0] if sre_outcomes else None
        if sre_outcomes and any(item != sre_outcome for item in sre_outcomes[1:]):
            raise HarnessError("同一效果的 SRE 离线诊断事实不一致")
        ux_outcomes = [
            item.ux_prioritization_outcome
            for item in records
            if item.ux_prioritization_outcome is not None
        ]
        ux_outcome = ux_outcomes[0] if ux_outcomes else None
        if ux_outcomes and any(item != ux_outcome for item in ux_outcomes[1:]):
            raise HarnessError("同一效果的 UX 全量优先级事实不一致")
        receipt = AgentControlLoopEffectReceipt(
            receipt_id=receipt_id,
            capability_id=execution.capability_id,
            scenario_id=execution.scenario_id,
            status=execution.status,
            state=execution.state,
            action=execution.action,
            observation=execution.observation,
            cost=execution.cost,
            result=execution.result,
            source_file_refs=list(execution.source_file_refs),
            artifact_ids=[item.artifact_id for item in records],
            prohibited_side_effects=list(execution.prohibited_side_effects),
            business_gate_outcome=business_outcome,
            legal_review_outcome=legal_outcome,
            candidate_review_outcome=candidate_outcome,
            finance_review_outcome=finance_outcome,
            outbound_flow_outcome=outbound_outcome,
            customer_segmentation_outcome=customer_outcome,
            sre_diagnosis_outcome=sre_outcome,
            ux_prioritization_outcome=ux_outcome,
            created_at=now,
        )

        async with self._lock:
            run = self._require_run(owner_id, run_id)
            snapshot = run.snapshot
            if any(
                item.capability_id == execution.capability_id for item in snapshot.effect_receipts
            ):
                return
            sequence = snapshot.last_event_sequence
            events = list(snapshot.events)
            _, unique_check_count, passed_check_count, _ = summarize_artifact_check_groups(
                record.checks for record in records
            )
            for record in records:
                sequence += 1
                events.append(
                    HarnessEvent(
                        sequence=sequence,
                        event_name="run_workspace_artifact_written",
                        occurred_at=now,
                        status=snapshot.status,
                        message=f"已在隔离运行工作区生成“{record.file_name}”。",
                        details={
                            "artifact_id": record.artifact_id,
                            "file_name": record.file_name,
                            "size": record.size,
                            "original_inputs_modified": False,
                            "external_action": False,
                        },
                    )
                )
            sequence += 1
            events.append(
                HarnessEvent(
                    sequence=sequence,
                    event_name=(
                        "deterministic_verification_completed"
                        if execution.status == "passed"
                        else "scenario_effect_bounded"
                    ),
                    occurred_at=now,
                    status=snapshot.status,
                    message=(
                        "真实成果文件已通过确定性效果门，仍需用户复核。"
                        if execution.status == "passed"
                        else execution.result
                    ),
                    details={
                        "capability_id": execution.capability_id,
                        "scenario_id": execution.scenario_id,
                        "effect_status": execution.status,
                        "artifact_count": len(records),
                        "check_count": unique_check_count,
                        "passed_check_count": passed_check_count,
                        "external_action": False,
                    },
                )
            )
            run.snapshot = snapshot.model_copy(
                update={
                    "workspace_artifacts": [
                        *snapshot.workspace_artifacts,
                        *records,
                    ],
                    "effect_receipts": [*snapshot.effect_receipts, receipt],
                    "events": events,
                    "last_event_sequence": sequence,
                    "version": snapshot.version + 1,
                    "updated_at": now,
                }
            )
            await self._persist_locked(run)
            condition = run.condition
        async with condition:
            condition.notify_all()

    async def _wait_for_evidence_confirmation(
        self,
        owner_id: str,
        run_id: str,
        reason: str,
        details: dict[str, Any],
    ) -> None:
        """Pause between rounds so missing evidence never spends budget silently."""

        async with self._lock:
            run = self._require_run(owner_id, run_id)
            snapshot = run.snapshot
            now = datetime.now(timezone.utc)
            event = HarnessEvent(
                sequence=snapshot.last_event_sequence + 1,
                event_name="evidence_gate",
                occurred_at=now,
                status="waiting_input",
                message=reason,
                details=details,
            )
            run.resume_status = "planning"
            budget = self._freeze_active_budget(run)
            next_version = snapshot.version + 1
            decision_requests = [
                packet.model_copy(update={"expected_version": next_version})
                if packet.state in {"open", "deferred"}
                else packet
                for packet in snapshot.decision_requests
            ]
            run.snapshot = snapshot.model_copy(
                update={
                    "status": "waiting_input",
                    "control_state": "paused",
                    "events": [*snapshot.events, event],
                    "last_event_sequence": event.sequence,
                    "version": next_version,
                    "decision_requests": decision_requests,
                    "budget": budget,
                    "updated_at": now,
                }
            )
            await self._persist_locked(run)
            condition = run.condition
        async with condition:
            condition.notify_all()

        while True:
            async with condition:
                async with self._lock:
                    state = self._require_run(owner_id, run_id).snapshot.control_state
                    if state == "stop_requested":
                        raise HarnessStopped("用户请求停止")
                    if state == "running":
                        return
                await condition.wait()

    async def _safe_point(self, owner_id: str, run_id: str) -> None:
        while True:
            async with self._lock:
                run = self._require_run(owner_id, run_id)
                budget = self._budget_with_elapsed(run)
                if run.snapshot.control_state == "pause_requested":
                    budget = self._freeze_active_budget(run)
                snapshot = run.snapshot.model_copy(update={"budget": budget})
                run.snapshot = snapshot
                await self._persist_locked(run)
                if snapshot.control_state == "stop_requested":
                    raise HarnessStopped("用户请求停止")
                if snapshot.control_state == "pause_requested":
                    now = datetime.now(timezone.utc)
                    next_version = snapshot.version + 1
                    run.resume_status = snapshot.status
                    controls = self._apply_control_event(
                        snapshot.control_events, "pause", next_version
                    )
                    event = HarnessEvent(
                        sequence=snapshot.last_event_sequence + 1,
                        event_name="control_paused",
                        occurred_at=now,
                        status="paused",
                        message="Agent Control Loop 已在安全点暂停。",
                        details={"applied": True},
                    )
                    run.snapshot = snapshot.model_copy(
                        update={
                            "status": "paused",
                            "control_state": "paused",
                            "control_events": controls,
                            "events": [*snapshot.events, event],
                            "last_event_sequence": event.sequence,
                            "version": next_version,
                            "updated_at": now,
                        }
                    )
                    await self._persist_locked(run)
                    condition = run.condition
                elif snapshot.control_state == "paused":
                    condition = run.condition
                else:
                    return
            async with condition:
                async with self._lock:
                    latest_state = self._require_run(owner_id, run_id).snapshot.control_state
                    if latest_state != "paused":
                        continue
                await condition.wait()

    @staticmethod
    def _apply_control_event(
        events: list[AgentControlLoopControlEvent],
        command: str,
        applied_version: int,
    ) -> list[AgentControlLoopControlEvent]:
        updated = list(events)
        for index in range(len(updated) - 1, -1, -1):
            event = updated[index]
            if (
                event.command == command
                and event.status == "accepted"
                and event.applied_task_version is None
            ):
                updated[index] = event.model_copy(
                    update={
                        "status": "applied",
                        "applied_task_version": applied_version,
                    }
                )
                break
        return updated

    async def _consume_pending_steer(self, owner_id: str, run_id: str) -> str | None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            snapshot = run.snapshot
            pending = [
                item
                for item in snapshot.control_events
                if item.command == "steer"
                and item.status == "accepted"
                and item.applied_task_version is None
                and item.instruction
            ]
            if not pending:
                return None
            instruction = "；".join(item.instruction for item in pending if item.instruction)
            now = datetime.now(timezone.utc)
            next_version = snapshot.version + 1
            pending_ids = {item.control_id for item in pending}
            controls = [
                item.model_copy(
                    update={
                        "status": "applied",
                        "applied_task_version": next_version,
                    }
                )
                if item.control_id in pending_ids
                else item
                for item in snapshot.control_events
            ]
            event = HarnessEvent(
                sequence=snapshot.last_event_sequence + 1,
                event_name="control_steer_applied",
                occurred_at=now,
                status=snapshot.status,
                message="已将方向指令纳入本轮规划上下文。",
                details={"control_count": len(pending)},
            )
            run.snapshot = snapshot.model_copy(
                update={
                    "control_events": controls,
                    "events": [*snapshot.events, event],
                    "last_event_sequence": event.sequence,
                    "version": next_version,
                    "updated_at": now,
                }
            )
            await self._persist_locked(run)
            condition = run.condition
        async with condition:
            condition.notify_all()
        return instruction

    async def _start_round(
        self,
        owner_id: str,
        run_id: str,
        *,
        round_number: int,
        question: str,
        steer_instruction: str | None,
    ) -> None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            snapshot = run.snapshot
            if round_number != len(snapshot.rounds) + 1:
                raise HarnessConflictError("Agent Control Loop 轮次不连续")
            now = datetime.now(timezone.utc)
            round_snapshot = AgentControlLoopRound(
                round_number=round_number,
                status="running",
                phase="observe",
                question=question,
                steer_instruction=steer_instruction,
                started_at=now,
            )
            budget = self._budget_with_elapsed(run).model_copy(update={"rounds_used": round_number})
            run.snapshot = snapshot.model_copy(
                update={
                    "rounds": [*snapshot.rounds, round_snapshot],
                    "current_round": round_number,
                    "budget": budget,
                    "updated_at": now,
                }
            )
            await self._persist_locked(run)

    async def _plan_with_bounded_repair(
        self,
        owner_id: str,
        run_id: str,
        *,
        workspace: dict[str, Any],
        question: str,
        round_number: int,
        remaining: list[dict[str, Any]],
        contract: AgentControlLoopContract,
        steer_instruction: str | None,
        require_all_files: bool = False,
    ) -> tuple[HarnessPlan, HarnessModelReceipt]:
        """Adopt one validated plan, with at most one budgeted repair attempt."""

        validation_feedback: str | None = None
        last_error: HarnessError | None = None
        for attempt in (1, 2):
            await self._reserve_model_call(owner_id, run_id)
            await self._transition(
                owner_id,
                run_id,
                "planning",
                "planning_started",
                "规划模型正在组织本轮任务。"
                if attempt == 1
                else "上一候选计划未通过校验，正在进行一次受控重试。",
                {"round_number": round_number, "attempt": attempt},
            )
            started = perf_counter()
            try:
                candidate = await self.planner.plan(
                    scenario=self._planner_workspace(
                        workspace,
                        question,
                        round_number=round_number,
                        max_files_this_round=contract.max_files_per_round,
                        remaining_file_count=len(remaining),
                        steer_instruction=steer_instruction,
                        validation_feedback=validation_feedback,
                        evidence_recheck=require_all_files,
                    ),
                    files=self._planner_files(remaining),
                )
                plan = self._compile_plan(
                    candidate,
                    max_file_refs=contract.max_files_per_round,
                )
            except HarnessModelError as exc:
                last_error = exc
                receipt = HarnessModelReceipt(
                    called=exc.called,
                    model=exc.model,
                    elapsed_ms=exc.elapsed_ms or max(0, round((perf_counter() - started) * 1000)),
                    output_used=False,
                )
                await self._set_model_receipt(owner_id, run_id, receipt)
                await self._update_round(
                    owner_id,
                    run_id,
                    round_number,
                    phase="plan",
                    model_receipt=receipt.model_dump(mode="json"),
                )
                await self._transition(
                    owner_id,
                    run_id,
                    "planning",
                    "planning_completed",
                    "规划模型返回内容未通过结构校验，未采用。",
                    {
                        "round_number": round_number,
                        "attempt": attempt,
                        "model": receipt.model,
                        "elapsed_ms": receipt.elapsed_ms,
                        "model_called": receipt.called,
                        "output_used": False,
                    },
                )
                if attempt == 2:
                    raise
                validation_feedback = "上一候选没有返回合法 JSON，请严格按 Schema 重建本轮计划。"
                await self._transition(
                    owner_id,
                    run_id,
                    "planning",
                    "plan_validation_rejected",
                    "候选计划未通过服务端校验，未采用；正在进行预算内的受控重试。",
                    {"round_number": round_number, "attempt": attempt},
                )
                await self._safe_point(owner_id, run_id)
                continue

            receipt = HarnessModelReceipt(
                called=True,
                model=getattr(self.planner, "model", self.MODEL),
                elapsed_ms=max(0, round((perf_counter() - started) * 1000)),
                output_used=False,
            )
            await self._set_model_receipt(owner_id, run_id, receipt)
            await self._update_round(
                owner_id,
                run_id,
                round_number,
                phase="plan",
                model_receipt=receipt.model_dump(mode="json"),
            )
            await self._transition(
                owner_id,
                run_id,
                "planning",
                "planning_completed",
                "规划模型已返回候选工作图，等待服务端校验。",
                {
                    "round_number": round_number,
                    "attempt": attempt,
                    "model": receipt.model,
                    "elapsed_ms": receipt.elapsed_ms,
                    "model_called": True,
                    "output_used": False,
                },
            )
            await self._safe_point(owner_id, run_id)
            try:
                self._validate_plan(
                    plan,
                    workspace,
                    remaining,
                    max_file_refs=contract.max_files_per_round,
                    require_all_files=require_all_files,
                )
            except HarnessPlanError as exc:
                last_error = exc
                if attempt == 2:
                    raise
                validation_feedback = str(exc)
                await self._transition(
                    owner_id,
                    run_id,
                    "planning",
                    "plan_validation_rejected",
                    "候选计划未通过服务端校验，未采用；正在进行预算内的受控重试。",
                    {
                        "round_number": round_number,
                        "attempt": attempt,
                        "reason": str(exc),
                    },
                )
                await self._safe_point(owner_id, run_id)
                continue

            adopted_receipt = receipt.model_copy(update={"output_used": True})
            return plan, adopted_receipt

        raise last_error or HarnessPlanError("本轮规划未形成可采用结果")

    async def _reserve_model_call(self, owner_id: str, run_id: str) -> None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            budget = self._budget_with_elapsed(run)
            if budget.model_calls_used >= budget.max_model_calls:
                raise HarnessBudgetExhausted("模型调用预算已耗尽")
            if budget.elapsed_ms >= budget.deadline_seconds * 1000:
                raise HarnessBudgetExhausted("Agent 执行时间预算已耗尽")
            run.snapshot = run.snapshot.model_copy(
                update={
                    "budget": budget.model_copy(
                        update={"model_calls_used": budget.model_calls_used + 1}
                    ),
                    "updated_at": datetime.now(timezone.utc),
                }
            )

            await self._persist_locked(run)

    async def _update_round(
        self,
        owner_id: str,
        run_id: str,
        round_number: int,
        **updates: Any,
    ) -> None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            if (
                updates.get("phase") == "plan"
                and "plan" in updates
                and round_number == run.snapshot.current_round
                and any(event.event_name == "control_topology_override_recorded" for event in run.snapshot.events)
            ):
                return
            rounds = [
                item.model_copy(update=updates) if item.round_number == round_number else item
                for item in run.snapshot.rounds
            ]
            run.snapshot = run.snapshot.model_copy(
                update={
                    "rounds": rounds,
                    "budget": self._budget_with_elapsed(run),
                    "updated_at": datetime.now(timezone.utc),
                }
            )

            await self._persist_locked(run)

    async def _complete_round(
        self,
        owner_id: str,
        run_id: str,
        round_number: int,
        *,
        gaps: list[AgentControlLoopEvidenceGap],
        next_step: AgentControlLoopNextStep,
    ) -> None:
        await self._update_round(
            owner_id,
            run_id,
            round_number,
            status="completed",
            phase="evidence_gate",
            evidence_gaps=gaps,
            next_step=next_step,
            completed_at=datetime.now(timezone.utc),
        )
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            snapshot = run.snapshot
            round_snapshot = next(
                item for item in snapshot.rounds if item.round_number == round_number
            )
            result = (
                HarnessTaskResult.model_validate(round_snapshot.result)
                if round_snapshot.result
                else None
            )
            artifact_id = (
                "artifact-"
                + hashlib.sha256(f"{run_id}:evidence-brief".encode("utf-8")).hexdigest()[:12]
            )
            version = len(snapshot.artifact_versions) + 1
            artifact = AgentControlLoopArtifactVersion(
                artifact_id=artifact_id,
                version=version,
                title="任务证据简报",
                status="draft" if gaps else "verified",
                round_number=round_number,
                summary=result.summary if result else next_step.reason,
                findings=[
                    AgentControlLoopArtifactFinding(
                        finding_id=item.finding_id,
                        plan_unit_id=item.plan_unit_id,
                        affected_branch_ids=item.affected_branch_ids,
                        title=item.title,
                        detail=item.detail,
                        fact_summary=item.fact_summary,
                        impact=item.impact,
                        file_refs=item.file_refs,
                        evidence_anchors=item.evidence_anchors,
                        evidence_resolutions=item.evidence_resolutions,
                        review=item.review,
                    )
                    for item in result.findings
                ]
                if result
                else [],
                follow_ups=result.follow_ups[:4] if result else [],
                evidence_gaps=gaps,
                # Keep every reference that backs a retained Finding. The
                # round list is only a projection and must not drop refs that
                # are still present in the Artifact payload.
                source_file_refs=list(
                    dict.fromkeys(
                        [
                            *round_snapshot.verified_file_refs,
                            *(
                                file_ref
                                for finding in (result.findings if result else [])
                                for file_ref in finding.file_refs
                            ),
                        ]
                    )
                ),
                finding_count=len(result.findings) if result else 0,
                parent_version=version - 1 if version > 1 else None,
                created_at=datetime.now(timezone.utc),
            )
            packets = list(snapshot.decision_requests)
            current_contract = snapshot.contract
            for resolution in next_step.evidence_resolutions:
                if resolution.status == "exact":
                    continue
                request_id = (
                    "decision-request-"
                    + hashlib.sha256(
                        f"{run_id}:{resolution.resolution_id}".encode("utf-8")
                    ).hexdigest()[:12]
                )
                packet = AgentControlLoopDecisionRequest(
                    decision_request_id=request_id,
                    run_id=run_id,
                    finding_id=resolution.finding_id,
                    resolution_id=resolution.resolution_id,
                    plan_unit_id=resolution.plan_unit_id,
                    branch_id=resolution.branch_id,
                    state="open",
                    reason=(
                        f"{resolution.reason} 需要你确认原文位置；"
                        "Agent 不会把候选位置当作事实，也不会发生外部动作。"
                    ),
                    candidates=resolution.candidates,
                    source_revision=resolution.source_revision,
                    expected_version=snapshot.version,
                    affected_branch_ids=resolution.affected_branch_ids
                    or ([resolution.branch_id] if resolution.branch_id else []),
                    required_file_refs=[resolution.file_ref],
                    estimated_additional_rounds=max(0, current_contract.max_rounds - round_number),
                    consequence=(
                        "接受后只重跑受影响分支并生成新的逻辑成果版本；"
                        "不会修改原始文件、发送消息或执行外部动作。"
                    ),
                    requested_at=datetime.now(timezone.utc),
                )
                existing = next(
                    (item for item in packets if item.decision_request_id == request_id),
                    None,
                )
                if existing is None:
                    packets.append(packet)
                elif existing.state == "open":
                    packets[packets.index(existing)] = packet
            if result is not None:
                for finding in result.findings:
                    review = finding.review
                    if review is None or not review.requires_human_decision:
                        continue
                    request_id = (
                        "decision-request-"
                        + hashlib.sha256(
                            f"{run_id}:{finding.finding_id}:review".encode("utf-8")
                        ).hexdigest()[:12]
                    )
                    branch_ids = list(finding.affected_branch_ids)
                    packet = AgentControlLoopDecisionRequest(
                        decision_request_id=request_id,
                        run_id=run_id,
                        finding_id=finding.finding_id,
                        plan_unit_id=finding.plan_unit_id,
                        branch_id=branch_ids[0] if len(branch_ids) == 1 else None,
                        state="open",
                        reason=review.why_human,
                        options=[option.model_dump(mode="json") for option in review.options],
                        source_revision="",
                        expected_version=snapshot.version,
                        affected_branch_ids=branch_ids,
                        required_file_refs=finding.file_refs[:20],
                        estimated_additional_rounds=max(
                            (option.estimated_additional_rounds for option in review.options),
                            default=0,
                        ),
                        consequence=review.after_confirmation,
                        requested_at=datetime.now(timezone.utc),
                    )
                    existing = next(
                        (item for item in packets if item.decision_request_id == request_id),
                        None,
                    )
                    if existing is None:
                        packets.append(packet)
                    elif existing.state == "open":
                        packets[packets.index(existing)] = packet
            run.snapshot = snapshot.model_copy(
                update={
                    "artifact_versions": [*snapshot.artifact_versions, artifact],
                    "decision_requests": packets,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            await self._persist_locked(run, artifact_version=artifact)

    async def _set_verified_count(self, owner_id: str, run_id: str, count: int) -> None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            budget = self._budget_with_elapsed(run).model_copy(update={"files_verified": count})
            run.snapshot = run.snapshot.model_copy(
                update={"budget": budget, "updated_at": datetime.now(timezone.utc)}
            )
            await self._persist_locked(run)

    async def _can_start_another_round(
        self,
        owner_id: str,
        run_id: str,
        round_number: int,
        has_gap: bool,
    ) -> bool:
        if not has_gap:
            return False
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            budget = self._budget_with_elapsed(run)
            return (
                round_number < budget.max_rounds
                and budget.model_calls_used + 2 <= budget.max_model_calls
                and budget.elapsed_ms < budget.deadline_seconds * 1000
                and run.snapshot.control_state not in {"stop_requested", "stopped"}
            )

    @staticmethod
    def _plan_file_refs(plan: HarnessPlan, files: list[dict[str, Any]]) -> list[str]:
        referenced = {file_ref for unit in plan.units for file_ref in unit.input_file_refs}
        ordered = [str(item["file_ref"]) for item in files if str(item["file_ref"]) in referenced]
        if not ordered:
            raise HarnessPlanError("本轮计划没有引用任何允许文件")
        return ordered

    @staticmethod
    def _result_file_refs(result: HarnessTaskResult, files: list[dict[str, Any]]) -> list[str]:
        anchored = {
            anchor.file_ref for finding in result.findings for anchor in finding.evidence_anchors
        }
        unresolved = {
            resolution.file_ref
            for finding in result.findings
            for resolution in finding.evidence_resolutions
            if resolution.status != "exact"
        }
        verified = anchored - unresolved
        return [str(item["file_ref"]) for item in files if str(item["file_ref"]) in verified]

    @staticmethod
    def _matching_branch_ids(
        file_refs: list[str], branches: list[AgentControlLoopBranch]
    ) -> list[str]:
        referenced = set(file_refs)
        ranked = sorted(
            ((len(referenced.intersection(branch.input_file_refs)), branch) for branch in branches),
            key=lambda item: (-item[0], item[1].branch_id),
        )
        return [branch.branch_id for overlap, branch in ranked if overlap > 0]

    @classmethod
    def _bind_result_to_branches(
        cls,
        result: HarnessTaskResult,
        branches: list[AgentControlLoopBranch],
        *,
        estimated_additional_rounds: int,
    ) -> HarnessTaskResult:
        findings: list[HarnessFinding] = []
        for finding in result.findings:
            exact_unit_candidates = [
                branch
                for branch in branches
                if finding.plan_unit_id is not None and branch.unit_id == finding.plan_unit_id
            ]
            latest_unit_round = max(
                (branch.round_number for branch in exact_unit_candidates),
                default=None,
            )
            exact_unit_branches = [
                branch.branch_id
                for branch in exact_unit_candidates
                if branch.round_number == latest_unit_round
            ]
            branch_ids = (
                exact_unit_branches
                if exact_unit_branches
                else cls._matching_branch_ids(finding.file_refs, branches)[:12]
            )
            resolutions = [
                item.model_copy(
                    update={
                        "branch_id": branch_ids[0] if len(branch_ids) == 1 else None,
                        "affected_branch_ids": branch_ids,
                    }
                )
                for item in finding.evidence_resolutions
            ]
            review = finding.review
            if review is not None:
                review = review.model_copy(
                    update={
                        "options": [
                            option.model_copy(
                                update={
                                    "affected_branch_ids": branch_ids,
                                    "required_file_refs": finding.file_refs[:20],
                                    "estimated_additional_rounds": min(
                                        3, max(1, estimated_additional_rounds)
                                    ),
                                }
                            )
                            for option in review.options
                        ]
                    }
                )
            findings.append(
                finding.model_copy(
                    update={
                        "affected_branch_ids": branch_ids,
                        "evidence_resolutions": resolutions,
                        "review": review,
                    }
                )
            )
        return result.model_copy(update={"findings": findings})

    @classmethod
    def _bind_evidence_resolutions_to_branches(
        cls,
        resolutions: list[AgentControlLoopEvidenceResolution],
        branches: list[AgentControlLoopBranch],
    ) -> list[AgentControlLoopEvidenceResolution]:
        bound: list[AgentControlLoopEvidenceResolution] = []
        for resolution in resolutions:
            exact_unit_candidates = [
                branch
                for branch in branches
                if resolution.plan_unit_id is not None and branch.unit_id == resolution.plan_unit_id
            ]
            latest_unit_round = max(
                (branch.round_number for branch in exact_unit_candidates),
                default=None,
            )
            exact_unit_branches = [
                branch.branch_id
                for branch in exact_unit_candidates
                if branch.round_number == latest_unit_round
            ]
            branch_ids = (
                exact_unit_branches
                if exact_unit_branches
                else cls._matching_branch_ids([resolution.file_ref], branches)
            )
            bound.append(
                resolution.model_copy(
                    update={
                        "branch_id": branch_ids[0] if len(branch_ids) == 1 else None,
                        "affected_branch_ids": branch_ids,
                    }
                )
            )
        return bound

    @staticmethod
    def _evidence_gaps(
        run_id: str, outstanding: list[dict[str, Any]]
    ) -> list[AgentControlLoopEvidenceGap]:
        if not outstanding:
            return []
        refs = [str(item["file_ref"]) for item in outstanding]
        digest = hashlib.sha256(f"{run_id}:{','.join(refs)}".encode()).hexdigest()
        return [
            AgentControlLoopEvidenceGap(
                gap_id=f"gap-{digest[:12]}",
                label=f"仍有 {len(refs)} 份允许资料缺少可核对引用",
                detail="这些资料仍在用户划定范围内，但尚未进入已通过服务端引用核对的结论。",
                candidate_file_refs=refs,
            )
        ]

    @staticmethod
    def _branch_evidence_gaps(
        branches: list[AgentControlLoopBranch],
    ) -> list[AgentControlLoopEvidenceGap]:
        gaps: list[AgentControlLoopEvidenceGap] = []
        for branch in branches[:20]:
            digest = hashlib.sha256(
                f"{branch.branch_id}:{','.join(branch.missing_file_refs)}".encode("utf-8")
            ).hexdigest()
            gaps.append(
                AgentControlLoopEvidenceGap(
                    gap_id=f"gap-{digest[:12]}",
                    branch_id=branch.branch_id,
                    label=f"“{branch.title}”分支仍缺少证据",
                    detail=(
                        f"该分支还有 {len(branch.missing_file_refs)} 份已选资料"
                        "没有进入通过服务端引用核对的结论。"
                    ),
                    candidate_file_refs=branch.missing_file_refs,
                )
            )
        return gaps

    async def _reconcile_branches(
        self,
        owner_id: str,
        run_id: str,
        *,
        verified_refs: list[str],
        through_round: int,
    ) -> list[AgentControlLoopBranch]:
        verified = set(verified_refs)
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            now = datetime.now(timezone.utc)
            branches: list[AgentControlLoopBranch] = []
            for branch in run.snapshot.branches:
                if branch.status in {"failed", "stopped"}:
                    branches.append(branch)
                    continue
                branch_verified = [item for item in branch.input_file_refs if item in verified]
                missing = [item for item in branch.input_file_refs if item not in verified]
                status = branch.status
                if branch.round_number <= through_round:
                    status = "completed" if not missing else "waiting_input"
                branches.append(
                    branch.model_copy(
                        update={
                            "verified_file_refs": branch_verified,
                            "missing_file_refs": missing,
                            "status": status,
                            "updated_at": now,
                        }
                    )
                )
            run.snapshot = run.snapshot.model_copy(update={"branches": branches, "updated_at": now})
            await self._persist_locked(run)
            return [item.model_copy(deep=True) for item in branches]

    async def _finalize_loop(
        self,
        owner_id: str,
        run_id: str,
        *,
        findings: list[HarnessFinding],
        follow_ups: list[str],
        verified_refs: list[str],
        decision: str,
        budget_reason: str | None = None,
    ) -> None:
        snapshot = await self.get(owner_id, run_id)
        considered_refs = {
            file_ref
            for round_snapshot in snapshot.rounds
            for file_ref in round_snapshot.input_file_refs
        }
        unresolved_files = [
            item
            for item in snapshot.source_documents
            if str(item.get("file_ref")) in considered_refs
            and str(item.get("file_ref")) not in set(verified_refs)
        ]
        waiting_branches = [item for item in snapshot.branches if item.status == "waiting_input"]
        gaps = (
            self._branch_evidence_gaps(waiting_branches)
            if waiting_branches
            else self._evidence_gaps(run_id, unresolved_files)
        )
        unique_findings: list[HarnessFinding] = []
        finding_keys: set[str] = set()
        for finding in findings:
            key = json.dumps(finding.model_dump(), ensure_ascii=False, sort_keys=True)
            if key not in finding_keys:
                finding_keys.add(key)
                unique_findings.append(finding)
        unique_follow_ups = list(dict.fromkeys([*follow_ups, *(gap.label for gap in gaps)]))

        if decision == "completed" and not gaps:
            outcome: Literal["completed", "bounded", "user_stopped"] = "completed"
            status = "completed"
            if (
                snapshot.narrative_reconciliation is not None
                and snapshot.narrative_reconciliation.model_disposition == "rejected"
            ):
                summary = (
                    f"Agent Control Loop 完成 {len(snapshot.rounds)} 轮并保留确定性成果；"
                    "模型说明未采用，当前以服务端全量复算为准。"
                )
            elif (
                snapshot.narrative_reconciliation is not None
                and snapshot.narrative_reconciliation.model_disposition == "supplemental"
            ):
                summary = (
                    f"Agent Control Loop 完成 {len(snapshot.rounds)} 轮并保留确定性成果；"
                    "模型说明只作补充，当前以服务端全量复算为准。"
                )
            else:
                summary = (
                    f"Agent Control Loop 完成 {len(snapshot.rounds)} 轮，从整个资料库中自主选择并只读核对了 "
                    f"{len(verified_refs)} 份相关资料；已形成待用户确认的下一步建议。"
                )
            stop_reason = None
            event_name = "loop_committed"
            message = "证据门已满足，已提交可追溯的只读任务简报。"
        elif decision == "user_stopped":
            outcome = "user_stopped"
            status = "stopped"
            summary = (
                f"用户在 {len(snapshot.rounds)} 轮内停止了 Agent Control Loop；"
                f"已保留 {len(verified_refs)} 份自主选择资料的核对结果和剩余缺口。"
            )
            stop_reason = "用户在安全点停止"
            event_name = "loop_stopped"
            message = "Agent Control Loop 已按用户请求停止，已保留现有证据。"
        else:
            outcome = "bounded"
            status = "stopped"
            summary = (
                f"Agent Control Loop 到达预算边界；已核对 {len(verified_refs)} 份资料，"
                f"仍有 {len(unresolved_files)} 份本轮已选择资料需要后续处理。"
            )
            stop_reason = budget_reason or self._budget_stop_reason(snapshot.budget)
            event_name = "loop_budget_stopped"
            message = "Agent Control Loop 已在预算边界停止，并保留未完成项。"

        brief = AgentControlLoopBrief(
            outcome=outcome,
            summary=summary,
            verified_file_refs=verified_refs,
            unresolved_gaps=gaps,
            rounds_completed=len([item for item in snapshot.rounds if item.status == "completed"]),
        )
        result = None
        if unique_findings:
            result = HarnessTaskResult(
                summary=summary,
                findings=unique_findings,
                follow_ups=unique_follow_ups[:4],
                review_required=True,
            )

        async with self._lock:
            run = self._require_run(owner_id, run_id)
            current = run.snapshot
            rounds = list(current.rounds)
            if rounds and rounds[-1].status == "running":
                fallback_step = AgentControlLoopNextStep(
                    decision="user_stopped" if decision == "user_stopped" else "budget_exhausted",
                    reason=stop_reason or message,
                    candidate_file_refs=[str(item.get("file_ref")) for item in unresolved_files][
                        :20
                    ],
                    candidate_branch_ids=[item.branch_id for item in waiting_branches],
                )
                rounds[-1] = rounds[-1].model_copy(
                    update={
                        "status": "stopped",
                        "phase": "evidence_gate",
                        "evidence_gaps": gaps,
                        "next_step": fallback_step,
                        "completed_at": datetime.now(timezone.utc),
                    }
                )
            next_version = current.version + 1
            controls = current.control_events
            if decision == "user_stopped":
                controls = self._apply_control_event(controls, "stop", next_version)
            budget = self._freeze_active_budget(run).model_copy(
                update={
                    "files_verified": len(verified_refs),
                    "stop_reason": stop_reason,
                }
            )
            artifact_versions = list(current.artifact_versions)
            commits = list(current.commits)
            last_commit = current.last_commit
            new_commit: AgentControlLoopCommit | None = None
            branches = list(current.branches)
            if status == "stopped":
                now = datetime.now(timezone.utc)
                branches = [
                    item.model_copy(update={"status": "stopped", "updated_at": now})
                    if item.status in {"running", "waiting_input"}
                    else item
                    for item in branches
                ]
            if status == "completed" and artifact_versions:
                final_artifact = artifact_versions[-1]
                commit_id = (
                    "commit-"
                    + hashlib.sha256(
                        (
                            f"{run_id}:{final_artifact.artifact_id}:"
                            f"{final_artifact.version}:{summary}"
                        ).encode("utf-8")
                    ).hexdigest()[:12]
                )
                new_commit = AgentControlLoopCommit(
                    commit_id=commit_id,
                    artifact_id=final_artifact.artifact_id,
                    artifact_version=final_artifact.version,
                    operation="commit",
                    summary="已提交通过证据门的只读任务简报，仍需用户审阅。",
                    committed_at=datetime.now(timezone.utc),
                )
                commits.append(new_commit)
                last_commit = new_commit
            run.snapshot = current.model_copy(
                update={
                    "rounds": rounds,
                    "result": result,
                    "brief": brief,
                    "artifact_versions": artifact_versions,
                    "commits": commits,
                    "last_commit": last_commit,
                    "branches": branches,
                    "budget": budget,
                    "control_state": "stopped" if status == "stopped" else "running",
                    "control_events": controls,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            await self._persist_locked(run, task_commit=new_commit)
        await self._transition(
            owner_id,
            run_id,
            status,
            event_name,
            message,
            {
                "outcome": outcome,
                "rounds_completed": brief.rounds_completed,
                "verified_file_count": len(verified_refs),
                "gap_count": len(gaps),
                "stop_reason": stop_reason,
                "external_action": False,
            },
        )

    @staticmethod
    def _budget_stop_reason(budget: AgentControlLoopBudget) -> str:
        if budget.elapsed_ms >= budget.deadline_seconds * 1000:
            return "Agent 执行时间预算已耗尽"
        if budget.model_calls_used >= budget.max_model_calls:
            return "模型调用预算已耗尽"
        if budget.rounds_used >= budget.max_rounds:
            return "轮次预算已耗尽"
        return "本轮剩余预算不足以完成下一次受控调用"

    @staticmethod
    def _snapshot_findings(snapshot: HarnessRunSnapshot) -> list[HarnessFinding]:
        findings: list[HarnessFinding] = []
        for round_snapshot in snapshot.rounds:
            if round_snapshot.result:
                findings.extend(HarnessTaskResult.model_validate(round_snapshot.result).findings)
        return findings

    @staticmethod
    def _snapshot_evidence_resolutions(
        snapshot: HarnessRunSnapshot,
    ) -> list[AgentControlLoopEvidenceResolution]:
        resolutions: list[AgentControlLoopEvidenceResolution] = []
        seen: set[str] = set()
        for round_snapshot in snapshot.rounds:
            if round_snapshot.result:
                result = HarnessTaskResult.model_validate(round_snapshot.result)
                for finding in result.findings:
                    for resolution in finding.evidence_resolutions:
                        if resolution.resolution_id not in seen:
                            seen.add(resolution.resolution_id)
                            resolutions.append(resolution)
            if round_snapshot.next_step:
                for resolution in round_snapshot.next_step.evidence_resolutions:
                    if resolution.resolution_id not in seen:
                        seen.add(resolution.resolution_id)
                        resolutions.append(resolution)
        return resolutions

    @staticmethod
    def _snapshot_verified_refs(snapshot: HarnessRunSnapshot) -> list[str]:
        refs: list[str] = []
        for round_snapshot in snapshot.rounds:
            for file_ref in round_snapshot.verified_file_refs:
                if file_ref not in refs:
                    refs.append(file_ref)
        return refs

    @staticmethod
    def _update_resolution_in_snapshot(
        snapshot: HarnessRunSnapshot,
        resolution_id: str | None,
        updates: dict[str, Any],
        *,
        finding_id: str | None = None,
    ) -> HarnessRunSnapshot:
        """Update one pending resolution without rewriting other findings/branches."""

        def update_result(payload: dict[str, Any] | None) -> dict[str, Any] | None:
            if payload is None:
                return None
            result = HarnessTaskResult.model_validate(payload)
            findings = []
            for finding in result.findings:
                resolutions = [
                    resolution.model_copy(update=updates)
                    if resolution_id is not None and resolution.resolution_id == resolution_id
                    else resolution
                    for resolution in finding.evidence_resolutions
                ]
                findings.append(finding.model_copy(update={"evidence_resolutions": resolutions}))
            return result.model_copy(update={"findings": findings}).model_dump(mode="json")

        rounds: list[AgentControlLoopRound] = []
        for round_snapshot in snapshot.rounds:
            next_step = round_snapshot.next_step
            if next_step is not None:
                next_step = next_step.model_copy(
                    update={
                        "evidence_resolutions": [
                            resolution.model_copy(update=updates)
                            if resolution_id is not None
                            and resolution.resolution_id == resolution_id
                            else resolution
                            for resolution in next_step.evidence_resolutions
                        ]
                    }
                )
            rounds.append(
                round_snapshot.model_copy(
                    update={
                        "result": update_result(round_snapshot.result),
                        "next_step": next_step,
                    }
                )
            )
        top_result = snapshot.result
        if top_result is not None:
            top_result = HarnessTaskResult.model_validate(
                update_result(top_result.model_dump(mode="json"))
            )
        request_updates = []
        for packet in snapshot.decision_requests:
            if packet.resolution_id == resolution_id and (
                resolution_id is not None or packet.finding_id == finding_id
            ):
                state = {
                    "accepted": "accepted",
                    "declined": "declined",
                    "deferred": "deferred",
                    "cancelled": "cancelled",
                }.get(str(updates.get("decision_status")))
                if state is None and updates.get("status") in {"stale", "rejected"}:
                    state = str(updates["status"])
                request_updates.append(
                    packet.model_copy(
                        update={
                            "state": state or packet.state,
                            "expected_version": snapshot.version,
                            "selected_candidate_id": updates.get(
                                "selected_candidate_id", packet.selected_candidate_id
                            ),
                            "selected_option_id": updates.get(
                                "selected_option_id", packet.selected_option_id
                            ),
                        }
                    )
                )
            else:
                request_updates.append(packet)
        return snapshot.model_copy(
            update={
                "rounds": rounds,
                "result": top_result,
                "decision_requests": request_updates,
            }
        )

    async def _mark_current_round_failed(self, owner_id: str, run_id: str) -> None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            rounds = list(run.snapshot.rounds)
            if rounds and rounds[-1].status == "running":
                rounds[-1] = rounds[-1].model_copy(
                    update={
                        "status": "failed",
                        "next_step": AgentControlLoopNextStep(
                            decision="failed",
                            reason="本轮未通过服务端校验，未继续进入下一轮。",
                        ),
                        "completed_at": datetime.now(timezone.utc),
                    }
                )
                now = datetime.now(timezone.utc)
                current_round = rounds[-1].round_number
                branches = [
                    item.model_copy(update={"status": "failed", "updated_at": now})
                    if item.round_number == current_round and item.status == "running"
                    else item
                    for item in run.snapshot.branches
                ]
                run.snapshot = run.snapshot.model_copy(
                    update={"rounds": rounds, "branches": branches}
                )
                await self._persist_locked(run)

    @staticmethod
    def _budget_with_elapsed(run: _Run) -> AgentControlLoopBudget:
        active_delta_ms = (
            max(0, round((perf_counter() - run.active_since_perf) * 1000))
            if run.active_since_perf is not None
            else 0
        )
        return run.snapshot.budget.model_copy(
            update={"elapsed_ms": max(0, run.active_elapsed_base_ms + active_delta_ms)}
        )

    @classmethod
    def _freeze_active_budget(cls, run: _Run) -> AgentControlLoopBudget:
        budget = cls._budget_with_elapsed(run)
        run.active_elapsed_base_ms = budget.elapsed_ms
        run.active_since_perf = None
        return budget

    @staticmethod
    def _resume_active_budget(run: _Run) -> None:
        if run.active_since_perf is None:
            run.active_since_perf = perf_counter()

    def _analysis_inputs(self, files: list[dict[str, Any]]) -> list[dict[str, Any]]:
        method = getattr(self.catalog, "agent_file_inputs", None)
        if callable(method):
            return method([str(item["file_ref"]) for item in files])
        return [
            {
                "file_ref": item["file_ref"],
                "display_label": item.get("display_label", "公开办公输入文件"),
                "display_summary": item.get("display_summary", "公开办公输入文件"),
            }
            for item in files
        ]

    @staticmethod
    def _source_revision(file: dict[str, Any]) -> str:
        """Use the frozen catalog content digest as the source revision."""
        return str(file.get("source_revision") or file.get("sha256") or "")

    @staticmethod
    def _public_source_revision(value: str) -> str:
        """Expose a short opaque revision, never the catalog hash itself."""
        return "rev-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _public_candidate_digest(value: str) -> str:
        """Expose no candidate digest; retained for old private callers only."""
        return "cand-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _public_idempotency_ref(value: str) -> str:
        return "idem-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _candidate_digest(
        *,
        resolution_id: str,
        file_ref: str,
        locator_kind: str,
        start: int,
        end: int,
        excerpt: str,
        source_revision: str,
    ) -> str:
        payload = "|".join(
            (
                resolution_id,
                file_ref,
                locator_kind,
                str(start),
                str(end),
                excerpt,
                source_revision,
            )
        )
        return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def _invoke_analyst(
        self,
        *,
        owner_id: str,
        run_id: str,
        round_number: int,
        instruction: str,
        plan: HarnessPlan,
        files: list[dict[str, Any]],
        verified_effect_context: dict[str, Any] | None,
        attempt: int,
        validation_feedback: str | None,
        reserve_model_call: bool = True,
        record_round_receipt: bool = True,
    ) -> tuple[HarnessTaskResult, HarnessModelReceipt]:
        if reserve_model_call:
            await self._reserve_model_call(owner_id, run_id)
        await self._transition(
            owner_id,
            run_id,
            "analyzing",
            "analysis_started",
            (
                f"第 {round_number} 轮正在读取 {len(files)} 份文件并重新定位原文。"
                if attempt > 1
                else f"第 {round_number} 轮正在读取 {len(files)} 份文件并形成只读分析。"
            ),
            {
                "round_number": round_number,
                "file_count": len(files),
                "attempt": attempt,
                "external_action": False,
            },
        )
        analysis_started = perf_counter()
        try:
            analyze_kwargs: dict[str, Any] = {
                "instruction": instruction,
                "plan": plan,
                "files": files,
                "validation_feedback": validation_feedback,
            }
            analyze_parameters = inspect.signature(self.analyst.analyze).parameters.values()
            if any(
                parameter.name == "verified_effect_context"
                or parameter.kind is inspect.Parameter.VAR_KEYWORD
                for parameter in analyze_parameters
            ):
                analyze_kwargs["verified_effect_context"] = verified_effect_context
            result = await self.analyst.analyze(
                **analyze_kwargs,
            )
        except HarnessModelError as exc:
            receipt = HarnessModelReceipt(
                called=exc.called,
                model=exc.model,
                elapsed_ms=exc.elapsed_ms
                or max(0, round((perf_counter() - analysis_started) * 1000)),
                output_used=False,
            )
            if record_round_receipt:
                await self._set_analysis_receipt(owner_id, run_id, receipt)
                await self._update_round(
                    owner_id,
                    run_id,
                    round_number,
                    phase="act",
                    analysis_receipt=receipt.model_dump(mode="json"),
                )
            await self._transition(
                owner_id,
                run_id,
                "analyzing",
                "analysis_completed",
                "分析模型返回内容未通过结构校验，未采用。",
                {
                    "round_number": round_number,
                    "attempt": attempt,
                    "model": receipt.model,
                    "elapsed_ms": receipt.elapsed_ms,
                    "model_called": receipt.called,
                    "output_used": False,
                },
            )
            raise
        receipt = HarnessModelReceipt(
            called=True,
            model=getattr(self.analyst, "model", self.MODEL),
            elapsed_ms=max(0, round((perf_counter() - analysis_started) * 1000)),
            output_used=False,
        )
        if record_round_receipt:
            await self._set_analysis_receipt(owner_id, run_id, receipt)
            await self._update_round(
                owner_id,
                run_id,
                round_number,
                phase="act",
                analysis_receipt=receipt.model_dump(mode="json"),
            )
        await self._transition(
            owner_id,
            run_id,
            "analyzing",
            "analysis_completed",
            "分析模型已返回候选结论，等待服务端核对引用与原文位置。",
            {
                "round_number": round_number,
                "attempt": attempt,
                "model": receipt.model,
                "elapsed_ms": receipt.elapsed_ms,
                "model_called": True,
                "output_used": False,
            },
        )
        return result, receipt

    @staticmethod
    def _planner_workspace(
        workspace: dict[str, Any],
        instruction: str,
        *,
        round_number: int = 1,
        max_files_this_round: int = 8,
        remaining_file_count: int | None = None,
        steer_instruction: str | None = None,
        validation_feedback: str | None = None,
        evidence_recheck: bool = False,
    ) -> dict[str, Any]:
        """Expose only workspace policy and the user's current instruction."""
        return {
            "workspace_id": workspace.get("workspace_id"),
            "title": workspace.get("title"),
            "goal": instruction,
            "task_instruction": instruction,
            "deliverables": workspace.get("deliverables", []),
            "data_boundary": workspace.get("data_boundary"),
            "human_gate_summary": workspace.get("human_gate_summary"),
            "allowlisted_tools": workspace.get("allowlisted_tools", []),
            "control_loop": {
                "round_number": round_number,
                "max_files_this_round": max_files_this_round,
                "remaining_file_count": remaining_file_count,
                "steer_instruction": steer_instruction,
                "validation_feedback": validation_feedback,
                "evidence_recheck": evidence_recheck,
                "external_action": "none",
            },
        }

    @staticmethod
    def _planner_files(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "file_ref": item["file_ref"],
                "display_label": item.get("display_label", "公开办公输入文件"),
                "display_group": item.get("display_group", "公开办公输入"),
                "display_path": item.get(
                    "display_path", item.get("display_label", "公开办公输入文件")
                ),
                "display_summary": item.get("display_summary", "公开办公输入文件"),
                "mime": item.get("mime", "application/octet-stream"),
            }
            for item in files
        ]

    @staticmethod
    def _index_files(workspace: dict[str, Any]) -> list[dict[str, Any]]:
        files = workspace.get("files")
        if not isinstance(files, list) or not files:
            raise HarnessPlanError("办公资料库没有可用输入文件")
        available = []
        for item in files:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                raise HarnessPlanError("文件索引格式无效")
            if item.get("role") != "input":
                continue
            file_ref = item.get("file_ref")
            if not isinstance(file_ref, str):
                raise HarnessPlanError("文件索引缺少稳定引用")
            available.append(
                {
                    "file_ref": file_ref,
                    **{
                        key: item[key]
                        for key in (
                            "path",
                            "role",
                            "mime",
                            "size",
                            "sha256",
                            "summary",
                            "display_label",
                            "display_group",
                            "display_path",
                            "display_summary",
                        )
                        if key in item
                    },
                }
            )
        if not available:
            raise HarnessPlanError("办公资料库没有可用输入文件")
        return available

    @staticmethod
    def _normalized_evidence_text(value: str) -> str:
        return " ".join(value.split())

    @staticmethod
    def _compact_evidence_text(value: str) -> str:
        return re.sub(r"[^\w]+", "", value, flags=re.UNICODE).replace("_", "").casefold()

    @staticmethod
    def _compact_text_with_line_map(text: str) -> tuple[str, list[int], list[str]]:
        """Remove layout punctuation while preserving safe-preview line locations."""

        compact_chars: list[str] = []
        line_map: list[int] = []
        lines = text.splitlines() or [text]
        for line_number, line in enumerate(lines, start=1):
            for character in line:
                if character == "_" or not re.match(r"\w", character, re.UNICODE):
                    continue
                folded = character.casefold()
                compact_chars.extend(folded)
                line_map.extend([line_number] * len(folded))
        return "".join(compact_chars), line_map, lines

    @classmethod
    def _resolve_text_anchor_candidates(
        cls,
        *,
        file_ref: str,
        role: Literal["expected", "observed", "support", "contradiction", "context"],
        label: str,
        quote: str,
        text: str,
    ) -> list[AgentControlLoopEvidenceAnchor]:
        normalized_chars: list[str] = []
        line_map: list[int] = []
        previous_was_space = True
        lines = text.splitlines() or [text]
        for line_number, line in enumerate(lines, start=1):
            for character in line:
                if character.isspace():
                    if not previous_was_space:
                        normalized_chars.append(" ")
                        line_map.append(line_number)
                    previous_was_space = True
                    continue
                normalized_chars.append(character)
                line_map.append(line_number)
                previous_was_space = False
            if not previous_was_space:
                normalized_chars.append(" ")
                line_map.append(line_number)
                previous_was_space = True
        if normalized_chars and normalized_chars[-1] == " ":
            normalized_chars.pop()
            line_map.pop()
        normalized_text = "".join(normalized_chars)
        normalized_quote = cls._normalized_evidence_text(quote)
        if not normalized_quote:
            return []
        positions: list[int] = []
        cursor = 0
        while True:
            position = normalized_text.find(normalized_quote, cursor)
            if position < 0:
                break
            positions.append(position)
            cursor = position + 1
        position_map = line_map
        matched_length = len(normalized_quote)
        if not positions:
            compact_quote = cls._compact_evidence_text(quote)
            if len(compact_quote) >= 12:
                compact_text, compact_line_map, lines = cls._compact_text_with_line_map(text)
                cursor = 0
                while True:
                    position = compact_text.find(compact_quote, cursor)
                    if position < 0:
                        break
                    positions.append(position)
                    cursor = position + 1
                position_map = compact_line_map
                matched_length = len(compact_quote)
        anchors: list[AgentControlLoopEvidenceAnchor] = []
        seen_ranges: set[tuple[int, int]] = set()
        for position in positions[:6]:
            start = position_map[position]
            end = position_map[position + matched_length - 1]
            if (start, end) in seen_ranges:
                continue
            seen_ranges.add((start, end))
            excerpt = "\n".join(lines[start - 1 : end])[:1_200].strip()
            if not excerpt:
                continue
            anchors.append(
                AgentControlLoopEvidenceAnchor(
                    file_ref=file_ref,
                    role=role,
                    label=label,
                    locator_kind="text_lines",
                    start=start,
                    end=end,
                    excerpt=excerpt,
                )
            )
        return anchors

    @classmethod
    def _resolve_text_anchor(
        cls,
        **kwargs: Any,
    ) -> AgentControlLoopEvidenceAnchor | None:
        candidates = cls._resolve_text_anchor_candidates(**kwargs)
        return candidates[0] if len(candidates) == 1 else None

    @classmethod
    def _resolve_table_anchor_candidates(
        cls,
        *,
        file_ref: str,
        role: Literal["expected", "observed", "support", "contradiction", "context"],
        label: str,
        quote: str,
        columns: list[Any],
        rows: list[Any],
    ) -> list[AgentControlLoopEvidenceAnchor]:
        normalized_quote = cls._normalized_evidence_text(quote)
        if not normalized_quote:
            return []
        compact_quote = cls._compact_evidence_text(quote)
        matches: list[tuple[int, list[str]]] = []
        safe_columns = [str(item) for item in columns]
        for raw_row in rows:
            if not isinstance(raw_row, dict):
                continue
            row_number = raw_row.get("row_number")
            raw_values = raw_row.get("values")
            if not isinstance(row_number, int) or not isinstance(raw_values, list):
                continue
            values = [str(item) for item in raw_values]
            joined = " | ".join(values)
            named = " | ".join(
                f"{safe_columns[index] if index < len(safe_columns) and safe_columns[index] else f'列 {index + 1}'}={value}"
                for index, value in enumerate(values)
            )
            candidates = [joined, named, *values]
            exact_match = any(
                normalized_quote in cls._normalized_evidence_text(candidate)
                for candidate in candidates
            )
            compact_match = len(compact_quote) >= 8 and any(
                compact_quote in cls._compact_evidence_text(candidate)
                for candidate in (joined, named)
            )
            if exact_match or compact_match:
                matches.append((row_number, values))
        anchors: list[AgentControlLoopEvidenceAnchor] = []
        for row_number, values in matches[:6]:
            excerpt = "；".join(
                f"{safe_columns[index] if index < len(safe_columns) and safe_columns[index] else f'列 {index + 1}'}：{value}"
                for index, value in enumerate(values)
            )[:1_200].strip()
            if not excerpt:
                continue
            anchors.append(
                AgentControlLoopEvidenceAnchor(
                    file_ref=file_ref,
                    role=role,
                    label=label,
                    locator_kind="table_rows",
                    start=row_number,
                    end=row_number,
                    excerpt=excerpt,
                )
            )
        return anchors

    @classmethod
    def _resolve_table_anchor(
        cls,
        **kwargs: Any,
    ) -> AgentControlLoopEvidenceAnchor | None:
        candidates = cls._resolve_table_anchor_candidates(**kwargs)
        return candidates[0] if len(candidates) == 1 else None

    @staticmethod
    def _instruction_date_window(
        instruction: str | None,
    ) -> tuple[tuple[int, int], tuple[int, int]] | None:
        if not instruction:
            return None
        match = re.search(
            r"(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*"
            r"(?:至|到|[-~～—])\s*"
            r"(\d{1,2})\s*月\s*(\d{1,2})\s*日",
            instruction,
        )
        if not match:
            return None
        start = (int(match.group(1)), int(match.group(2)))
        end = (int(match.group(3)), int(match.group(4)))
        return (start, end) if start <= end else None

    @classmethod
    def _finding_outside_instruction_date_window(
        cls,
        finding: HarnessFinding,
        instruction: str | None,
    ) -> bool:
        window = cls._instruction_date_window(instruction)
        if window is None:
            return False
        observed_dates: list[tuple[int, int]] = []
        for anchor in finding.evidence_anchors:
            if anchor.role != "observed":
                continue
            observed_dates.extend(
                (int(month), int(day))
                for month, day in re.findall(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日", anchor.excerpt)
            )
        if not observed_dates:
            return False
        start, end = window
        return all(date < start or date > end for date in observed_dates)

    @classmethod
    def _resolve_evidence_anchors(
        cls,
        result: HarnessTaskResult,
        files: list[dict[str, Any]],
        source_revisions: dict[str, str] | None = None,
        instruction: str | None = None,
    ) -> _EvidenceResolution:
        files_by_ref = {str(item.get("file_ref")): item for item in files}
        revisions = source_revisions or {
            str(item.get("file_ref")): cls._source_revision(item) for item in files
        }
        resolved_findings: list[HarnessFinding] = []
        evidence_resolutions: list[AgentControlLoopEvidenceResolution] = []
        rejected_finding_count = 0
        rejected_file_refs: list[str] = []
        out_of_scope_finding_count = 0
        downgraded_review_count = 0
        for finding in result.findings:
            finding_id = finding.finding_id or cls._finding_id(finding)
            anchors: list[AgentControlLoopEvidenceAnchor] = []
            finding_resolutions: list[AgentControlLoopEvidenceResolution] = []
            seen: set[tuple[str, str, int, int]] = set()
            for quote_index, candidate in enumerate(finding.evidence_quotes):
                if (
                    candidate.file_ref not in finding.file_refs
                    or candidate.file_ref not in files_by_ref
                ):
                    continue
                source = files_by_ref[candidate.file_ref]
                matches: list[AgentControlLoopEvidenceAnchor] = []
                if source.get("kind") == "table":
                    matches = cls._resolve_table_anchor_candidates(
                        file_ref=candidate.file_ref,
                        role=candidate.role,
                        label=candidate.label,
                        quote=candidate.quote,
                        columns=list(source.get("columns") or []),
                        rows=list(source.get("rows") or []),
                    )
                elif isinstance(source.get("text"), str):
                    matches = cls._resolve_text_anchor_candidates(
                        file_ref=candidate.file_ref,
                        role=candidate.role,
                        label=candidate.label,
                        quote=candidate.quote,
                        text=str(source["text"]),
                    )
                resolution_id = cls._evidence_resolution_id(
                    finding_id,
                    quote_index,
                    candidate.file_ref,
                    candidate.label,
                )
                public_candidates = [
                    AgentControlLoopEvidenceCandidate(
                        candidate_id=cls._evidence_candidate_id(resolution_id, match),
                        file_ref=match.file_ref,
                        locator_kind=match.locator_kind,
                        start=match.start,
                        end=match.end,
                        excerpt=match.excerpt,
                        source_revision=revisions.get(candidate.file_ref, ""),
                        candidate_digest=cls._candidate_digest(
                            resolution_id=resolution_id,
                            file_ref=match.file_ref,
                            locator_kind=match.locator_kind,
                            start=match.start,
                            end=match.end,
                            excerpt=match.excerpt,
                            source_revision=revisions.get(candidate.file_ref, ""),
                        ),
                    )
                    for match in matches
                ]
                if len(matches) == 1:
                    status: Literal["exact", "ambiguous", "unavailable"] = "exact"
                    reason = "服务端在本轮安全预览中找到唯一匹配位置。"
                    resolved = matches[0]
                    key = (
                        resolved.file_ref,
                        resolved.locator_kind,
                        resolved.start,
                        resolved.end,
                    )
                    if key not in seen:
                        seen.add(key)
                        anchors.append(resolved)
                elif matches:
                    status = "ambiguous"
                    reason = (
                        f"同一片段在安全预览中匹配到 {len(matches)} 个位置，服务端不能替用户选择。"
                    )
                else:
                    status = "unavailable"
                    reason = "服务端在本轮安全预览中没有找到可核对的位置。"
                finding_resolutions.append(
                    AgentControlLoopEvidenceResolution(
                        resolution_id=resolution_id,
                        finding_id=finding_id,
                        plan_unit_id=finding.plan_unit_id,
                        finding_title=finding.title,
                        fact_summary=finding.fact_summary,
                        impact=finding.impact,
                        file_ref=candidate.file_ref,
                        role=candidate.role,
                        label=candidate.label,
                        query_excerpt=candidate.quote,
                        status=status,
                        reason=reason,
                        candidates=public_candidates,
                        source_revision=revisions.get(candidate.file_ref, ""),
                    )
                )
            if not finding_resolutions:
                missing_ref = finding.file_refs[0]
                resolution_id = cls._evidence_resolution_id(
                    finding_id, 0, missing_ref, "未提供逐字引用"
                )
                finding_resolutions.append(
                    AgentControlLoopEvidenceResolution(
                        resolution_id=resolution_id,
                        finding_id=finding_id,
                        plan_unit_id=finding.plan_unit_id,
                        finding_title=finding.title,
                        fact_summary=finding.fact_summary,
                        impact=finding.impact,
                        file_ref=missing_ref,
                        role="context",
                        label="模型未提供逐字引用",
                        query_excerpt="未提供逐字引用",
                        status="unavailable",
                        reason="模型没有为该发现提供可供服务端核对的逐字引用。",
                        source_revision=revisions.get(missing_ref, ""),
                    )
                )
            if not anchors:
                evidence_resolutions.extend(
                    item for item in finding_resolutions if item.status != "exact"
                )
                rejected_finding_count += 1
                for file_ref in finding.file_refs:
                    if file_ref in files_by_ref and file_ref not in rejected_file_refs:
                        rejected_file_refs.append(file_ref)
                continue
            resolved_finding = finding.model_copy(
                update={
                    "finding_id": finding_id,
                    "evidence_quotes": [],
                    "evidence_anchors": anchors,
                    "evidence_resolutions": finding_resolutions,
                }
            )
            if cls._finding_outside_instruction_date_window(resolved_finding, instruction):
                out_of_scope_finding_count += 1
                continue
            review = resolved_finding.review
            if (
                review is not None
                and review.requires_human_decision
                and not any(anchor.role == "contradiction" for anchor in anchors)
            ):
                resolved_finding = resolved_finding.model_copy(update={"review": None})
                downgraded_review_count += 1
            evidence_resolutions.extend(
                item for item in finding_resolutions if item.status != "exact"
            )
            resolved_findings.append(resolved_finding)
        resolved_result = (
            result.model_copy(update={"findings": resolved_findings}) if resolved_findings else None
        )
        return _EvidenceResolution(
            result=resolved_result,
            rejected_finding_count=rejected_finding_count,
            rejected_file_refs=tuple(rejected_file_refs),
            evidence_resolutions=tuple(evidence_resolutions),
            out_of_scope_finding_count=out_of_scope_finding_count,
            downgraded_review_count=downgraded_review_count,
        )

    @staticmethod
    def _finding_id(finding: HarnessFinding) -> str:
        digest = hashlib.sha256(
            json.dumps(
                {
                    "title": finding.title,
                    "fact_summary": finding.fact_summary,
                    "file_refs": finding.file_refs,
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return f"finding-{digest[:12]}"

    @staticmethod
    def _evidence_resolution_id(
        finding_id: str, quote_index: int, file_ref: str, label: str
    ) -> str:
        digest = hashlib.sha256(
            f"{finding_id}:{quote_index}:{file_ref}:{label}".encode("utf-8")
        ).hexdigest()
        return f"resolution-{digest[:12]}"

    @staticmethod
    def _evidence_candidate_id(resolution_id: str, anchor: AgentControlLoopEvidenceAnchor) -> str:
        digest = hashlib.sha256(
            (
                f"{resolution_id}:{anchor.file_ref}:{anchor.locator_kind}:"
                f"{anchor.start}:{anchor.end}:{anchor.excerpt}"
            ).encode("utf-8")
        ).hexdigest()
        return f"candidate-{digest[:12]}"

    @staticmethod
    def _validate_candidate_result_scope(
        result: HarnessTaskResult,
        files: list[dict[str, Any]],
        plan: HarnessPlan | None = None,
    ) -> HarnessTaskResult:
        """Validate file scope and rebind only a uniquely implied plan unit."""

        allowed_refs = {str(item["file_ref"]) for item in files}
        plan_units = {unit.unit_id: unit for unit in plan.units} if plan else {}
        normalized_findings: list[HarnessFinding] = []
        for finding in result.findings:
            if not set(finding.file_refs).issubset(allowed_refs):
                raise HarnessPlanError("分析结果引用了本轮计划之外的文件")
            if any(
                quote.file_ref not in finding.file_refs or quote.file_ref not in allowed_refs
                for quote in finding.evidence_quotes
            ):
                raise HarnessPlanError("分析结果的逐字引用超出本轮允许范围")
            if not plan:
                normalized_findings.append(finding)
                continue
            refs = set(finding.file_refs)
            bound_unit = plan_units.get(finding.plan_unit_id or "")
            if bound_unit is not None and refs.issubset(bound_unit.input_file_refs):
                normalized_findings.append(finding)
                continue
            matching_units = [unit for unit in plan.units if refs.issubset(unit.input_file_refs)]
            if len(matching_units) == 1:
                normalized_findings.append(
                    finding.model_copy(update={"plan_unit_id": matching_units[0].unit_id})
                )
                continue
            if finding.plan_unit_id is not None and bound_unit is None:
                reason = "分析结果绑定了不存在的计划单元"
            elif finding.plan_unit_id is not None:
                reason = "分析结果引用超出其绑定计划单元的文件范围"
            else:
                reason = "共享资料对应多个任务分支，Finding 必须提供 plan_unit_id"
            if len(matching_units) != 1:
                raise HarnessPlanError(reason)
        return result.model_copy(update={"findings": normalized_findings})

    @staticmethod
    def _validate_result(result: HarnessTaskResult, files: list[dict[str, Any]]) -> None:
        allowed_refs = {str(item["file_ref"]) for item in files}
        for finding in result.findings:
            if not set(finding.file_refs).issubset(allowed_refs):
                raise HarnessPlanError("分析结果引用了本轮计划之外的文件")
            if not finding.evidence_anchors:
                raise HarnessPlanError("分析结果缺少服务端已定位的证据锚点")
            if any(
                anchor.file_ref not in finding.file_refs or anchor.file_ref not in allowed_refs
                for anchor in finding.evidence_anchors
            ):
                raise HarnessPlanError("分析结果的证据锚点超出本轮允许范围")
            review = finding.review
            if review is not None:
                option_ids = [option.option_id for option in review.options]
                if len(option_ids) != len(set(option_ids)):
                    raise HarnessPlanError("分析结果包含重复的人工决策选项")
                if review.requires_human_decision and not 2 <= len(option_ids) <= 3:
                    raise HarnessPlanError("需要人工决策的发现必须提供 2 到 3 个选项")
                if (
                    review.requires_human_decision
                    and review.recommended_option_id not in option_ids
                ):
                    raise HarnessPlanError("人工决策建议没有对应的可选项")

    @staticmethod
    def _compile_plan(
        candidate: HarnessPlanCandidate | HarnessPlan,
        *,
        max_file_refs: int | None = None,
    ) -> HarnessPlan:
        """Compile model intent into server-owned scope, effect and gate policy."""

        selected_refs: set[str] = set()
        candidate_payloads: list[dict[str, Any]] = []
        budget_trimmed = False
        for candidate_unit in candidate.units:
            payload = candidate_unit.model_dump(exclude={"side_effect"})
            bounded_refs: list[str] = []
            for file_ref in payload["input_file_refs"]:
                if file_ref in selected_refs:
                    bounded_refs.append(file_ref)
                elif max_file_refs is None or len(selected_refs) < max_file_refs:
                    selected_refs.add(file_ref)
                    bounded_refs.append(file_ref)
                else:
                    budget_trimmed = True
            if not bounded_refs:
                budget_trimmed = True
                continue
            payload["input_file_refs"] = bounded_refs
            candidate_payloads.append(payload)

        kept_ids = {str(payload["unit_id"]) for payload in candidate_payloads}
        units: list[HarnessPlanUnit] = []
        for index, payload in enumerate(candidate_payloads, start=1):
            payload["depends_on"] = [
                dependency for dependency in payload["depends_on"] if dependency in kept_ids
            ]
            tool = str(payload["tool"])
            if tool == "artifact.write":
                side_effect: HarnessSideEffect = "run_workspace_write"
                payload["artifact_name"] = payload.get("artifact_name") or f"run-result-{index}"
                payload["artifact_type"] = payload.get("artifact_type") or "analysis"
            elif tool == "action.preview":
                side_effect = "external_action"
                payload["requires_human_gate"] = True
                payload["artifact_name"] = None
                payload["artifact_type"] = None
            else:
                side_effect = "none"
                payload["artifact_name"] = None
                payload["artifact_type"] = None
            units.append(HarnessPlanUnit(**payload, side_effect=side_effect))

        selection_reason = candidate.selection_reason
        if budget_trimmed and max_file_refs is not None:
            budget_note = (
                f" 服务端按每轮最多 {max_file_refs} 份文件的预算，"
                "保留了模型排序中优先级最高的证据。"
            )
            selection_reason = f"{selection_reason[: 1_000 - len(budget_note)]}{budget_note}"
        return HarnessPlan(
            summary=candidate.summary,
            selection_reason=selection_reason,
            units=units,
        )

    @classmethod
    def _validate_plan(
        cls,
        plan: HarnessPlan,
        workspace: dict[str, Any],
        files: list[dict[str, Any]],
        *,
        max_file_refs: int | None = None,
        require_all_files: bool = False,
    ) -> None:
        allowed_refs = {str(item["file_ref"]) for item in files}
        allowed_tools = set(workspace.get("allowlisted_tools", []))
        allowed_effects = set(
            workspace.get("allowed_side_effects", ["none", "run_workspace_write"])
        )
        if not allowed_tools:
            raise HarnessPlanError("办公资料库没有工具 allowlist")
        ids = [unit.unit_id for unit in plan.units]
        if len(ids) != len(set(ids)):
            raise HarnessPlanError("工作单元 ID 重复")
        referenced_refs = {file_ref for unit in plan.units for file_ref in unit.input_file_refs}
        if max_file_refs is not None and len(referenced_refs) > max_file_refs:
            raise HarnessPlanError(
                f"本轮计划引用 {len(referenced_refs)} 份文件，"
                f"超过最多 {max_file_refs} 份的 Agent Control Loop 预算"
            )
        if require_all_files and referenced_refs != allowed_refs:
            missing_count = len(allowed_refs - referenced_refs)
            raise HarnessPlanError(
                "本轮为用户已确认的证据补核，候选计划必须覆盖全部待核对文件；"
                f"当前仍缺 {missing_count} 份"
            )
        graph: dict[str, list[str]] = {unit.unit_id: list(unit.depends_on) for unit in plan.units}
        for unit in plan.units:
            unknown_refs = set(unit.input_file_refs) - allowed_refs
            if unknown_refs:
                raise HarnessPlanError("计划引用了资料库索引之外的公开文件")
            if unit.tool not in allowed_tools:
                raise HarnessPlanError(f"计划使用了未允许的工具: {unit.tool}")
            if unit.side_effect not in allowed_effects:
                raise HarnessPlanError(f"计划使用了未允许的副作用类型: {unit.side_effect}")
            if unit.tool == "artifact.write":
                if unit.side_effect != "run_workspace_write":
                    raise HarnessPlanError("artifact.write 必须映射为 run_workspace_write")
                if not unit.artifact_name or not unit.artifact_type:
                    raise HarnessPlanError(
                        "artifact.write 必须声明受控 artifact_name 和 artifact_type"
                    )
            elif unit.artifact_name is not None or unit.artifact_type is not None:
                raise HarnessPlanError("只有 artifact.write 可以声明 artifact 元数据")
            if unit.side_effect == "run_workspace_write" and unit.tool != "artifact.write":
                raise HarnessPlanError("run_workspace_write 只能由 artifact.write 产生")
            if unit.side_effect == "external_action":
                if unit.tool != "action.preview":
                    raise HarnessPlanError("external_action 只能由 action.preview 候选产生")
                if not unit.requires_human_gate:
                    raise HarnessPlanError("external_action 必须经过人工确认")
            unknown_deps = set(unit.depends_on) - set(ids)
            if unknown_deps:
                raise HarnessPlanError("计划包含未知依赖")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                raise HarnessPlanError("计划依赖存在环")
            if node in visited:
                return
            visiting.add(node)
            for dep in graph[node]:
                visit(dep)
            visiting.remove(node)
            visited.add(node)

        for node in graph:
            visit(node)

    async def _transition(
        self,
        owner_id: str,
        run_id: str,
        status: str,
        name: str,
        message: str,
        details: dict[str, Any],
    ) -> None:
        if status not in self.ALLOWED_STATUSES:
            raise HarnessConflictError(f"未知 Harness 状态: {status}")
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            if (
                name == "plan_validation"
                and run.snapshot.topology_admission is not None
                and run.snapshot.topology_admission.mode == "single_controller"
                and any(event.event_name == "control_topology_override_recorded" for event in run.snapshot.events)
            ):
                return
            now = datetime.now(timezone.utc)
            event = HarnessEvent(
                sequence=len(run.snapshot.events) + 1,
                event_name=name,
                occurred_at=now,
                status=status,
                message=message,
                details=details,
            )
            run.snapshot = run.snapshot.model_copy(
                update={
                    "status": status,
                    "updated_at": now,
                    "events": [*run.snapshot.events, event],
                    "last_event_sequence": event.sequence,
                    "version": run.snapshot.version + 1,
                    "budget": self._budget_with_elapsed(run),
                }
            )
            await self._persist_locked(run)
            condition = run.condition
        async with condition:
            condition.notify_all()

    async def _set_model_receipt(
        self, owner_id: str, run_id: str, receipt: HarnessModelReceipt
    ) -> None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            run.snapshot = run.snapshot.model_copy(
                update={"model_receipt": receipt, "updated_at": datetime.now(timezone.utc)}
            )
            await self._persist_locked(run)

    async def _set_topology_admission(
        self,
        owner_id: str,
        run_id: str,
        plan: HarnessPlan,
        *,
        remaining_model_calls: int,
        remaining_time_seconds: int,
    ) -> None:
        from services.api.app.application.topology_admission import admit_topology

        existing = await self.get(owner_id, run_id)
        if (
            existing.topology_admission is not None
            and existing.topology_admission.mode == "single_controller"
            and any(
                event.event_name == "control_topology_override_recorded"
                for event in existing.events
            )
        ):
            # The user already selected the conservative route for this
            # packet. Do not recompute adaptive admission or create another
            # confirmation gate while resuming the same round.
            return
        source_refs = sorted({ref for unit in plan.units for ref in unit.input_file_refs})
        source_facts: dict[str, dict[str, object]] = {}
        for file_ref in source_refs:
            public_file = getattr(self.catalog, "public_file", None)
            if not callable(public_file):
                # Legacy test catalogs may expose only agent-safe inputs.  In
                # that narrow compatibility case structural facts are
                # unavailable and admission stays conservative.
                continue
            try:
                preview = public_file(file_ref)
            except KeyError:
                # A legacy catalog may omit a preview row.  Do not turn a
                # missing structural hint into a broad runtime failure.
                continue
            source_facts[file_ref] = {
                key: preview.get(key)
                for key in ("display_group", "display_path", "mime", "kind", "columns")
            }
        admission = admit_topology(
            plan,
            remaining_model_calls=remaining_model_calls,
            remaining_time_seconds=remaining_time_seconds,
            source_facts=source_facts,
        )
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            run.snapshot = run.snapshot.model_copy(
                update={
                    "topology_admission": admission,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            await self._persist_locked(run)
        await self._transition(
            owner_id,
            run_id,
            "validating",
            "topology_admission",
            "服务端已根据已校验计划选择执行拓扑；准入与实际执行分开。",
            {
                "mode": admission.mode,
                "independent_branch_count": admission.independent_branch_count,
                "external_action": False,
                "user_confirmation_required": admission.user_confirmation_required,
            },
        )

    async def _set_analysis_receipt(
        self,
        owner_id: str,
        run_id: str,
        receipt: HarnessModelReceipt,
    ) -> None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            run.snapshot = run.snapshot.model_copy(
                update={
                    "analysis_receipt": receipt,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            await self._persist_locked(run)

    async def _set_result(self, owner_id: str, run_id: str, result: HarnessTaskResult) -> None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            run.snapshot = run.snapshot.model_copy(
                update={"result": result, "updated_at": datetime.now(timezone.utc)}
            )
            await self._persist_locked(run)

    async def _set_source_documents(
        self, owner_id: str, run_id: str, files: list[dict[str, Any]], reason: str
    ) -> None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            run.snapshot = run.snapshot.model_copy(
                update={
                    "source_documents": files,
                    "selection_reason": reason,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            await self._persist_locked(run)

    async def _set_plan(
        self,
        owner_id: str,
        run_id: str,
        plan: HarnessPlan,
        *,
        round_number: int,
        parent_branch_id: str | None,
    ) -> list[str]:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            now = datetime.now(timezone.utc)
            branches = self._branches_for_plan(
                run.snapshot.run_id,
                plan,
                round_number=round_number,
                parent_branch_id=parent_branch_id,
                now=now,
            )
            run.snapshot = run.snapshot.model_copy(
                update={
                    "plan": plan,
                    "branches": [*run.snapshot.branches, *branches],
                    "updated_at": now,
                }
            )
            await self._persist_locked(run)
            return [item.branch_id for item in branches]

    @staticmethod
    def _branch_by_id(
        branches: list[AgentControlLoopBranch], branch_id: str | None
    ) -> AgentControlLoopBranch | None:
        if branch_id is None:
            return None
        return next((item for item in branches if item.branch_id == branch_id), None)

    @staticmethod
    def _branches_for_plan(
        run_id: str,
        plan: HarnessPlan,
        *,
        round_number: int,
        parent_branch_id: str | None,
        now: datetime,
    ) -> list[AgentControlLoopBranch]:
        branch_ids = {
            unit.unit_id: "branch-"
            + hashlib.sha256(f"{run_id}:{round_number}:{unit.unit_id}".encode("utf-8")).hexdigest()[
                :12
            ]
            for unit in plan.units
        }
        return [
            AgentControlLoopBranch(
                branch_id=branch_ids[unit.unit_id],
                unit_id=unit.unit_id,
                round_number=round_number,
                parent_branch_id=parent_branch_id,
                title=unit.title,
                objective=unit.objective,
                depends_on=[branch_ids[item] for item in unit.depends_on],
                input_file_refs=list(dict.fromkeys(unit.input_file_refs)),
                missing_file_refs=list(dict.fromkeys(unit.input_file_refs)),
                # Only DAG roots are ready for dispatch. Dependents remain
                # pending until their predecessor MergeReceipt is adopted.
                status="pending" if unit.depends_on else "running",
                requires_human_gate=unit.requires_human_gate,
                created_at=now,
                updated_at=now,
            )
            for unit in plan.units
        ]

    async def _fail(self, owner_id: str, run_id: str, reason: str) -> None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            budget = self._freeze_active_budget(run)
            run.snapshot = run.snapshot.model_copy(
                update={
                    "validation_errors": [reason],
                    "budget": budget,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            await self._persist_locked(run)
            receipt = (
                run.snapshot.analysis_receipt
                if run.snapshot.status in {"analyzing", "verifying", "committing"}
                else run.snapshot.model_receipt
            )
        await self._transition(
            owner_id,
            run_id,
            "failed",
            "harness_failed",
            "本轮未通过服务端校验，已停止且未发生外部动作。",
            {
                "reason": reason,
                "execution_started": False,
                "model_called": bool(receipt and receipt.called),
                "output_used": bool(receipt and receipt.output_used),
            },
        )

    def _require_run(self, owner_id: str, run_id: str) -> _Run:
        run = self._runs.get((owner_id, run_id))
        if run is None:
            raise HarnessNotFoundError("Harness run 不存在")
        return run

    MODEL = "deepseek-v4-pro"


def build_harness_runtime(settings: Any | None = None) -> HarnessRuntime:
    """Construct the production adapter without coupling app startup to tests."""
    if settings is None:
        from services.api.app.config import get_settings

        settings = get_settings()
    from services.api.app.application.benchmark_workspace_catalog import (
        BenchmarkWorkspaceCatalog,
    )

    state_store: HarnessStateStore
    if settings.database_dsn:
        state_store = PostgresHarnessStateStore(settings.database_dsn)
    else:
        state_store = InMemoryHarnessStateStore()

    return HarnessRuntime(
        BenchmarkWorkspaceCatalog(),
        OpenAICompatibleHarnessPlanner(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
        ),
        OpenAICompatibleHarnessAnalyst(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
        ),
        state_store,
        ScenarioEffectEngine(),
        RunWorkspaceArtifactStore(Path.cwd() / ".runtime" / "run-workspaces"),
    )
