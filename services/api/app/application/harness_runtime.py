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
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Literal, Protocol
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from packages.contracts.harness_models import (
    AgentControlLoopArtifactVersion,
    AgentControlLoopArtifactFinding,
    AgentControlLoopBranch,
    AgentControlLoopBrief,
    AgentControlLoopBudget,
    AgentControlLoopCommit,
    AgentControlLoopContract,
    AgentControlLoopControlEvent,
    AgentControlLoopControlRequest,
    AgentControlLoopDecisionRecord,
    AgentControlLoopEvidenceAnchor,
    AgentControlLoopEvidenceCandidate,
    AgentControlLoopEvidenceGap,
    AgentControlLoopEvidenceResolution,
    AgentControlLoopFindingReview,
    AgentControlLoopNextStep,
    AgentControlLoopOptions,
    AgentControlLoopRound,
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
    role: Literal[
        "expected", "observed", "support", "contradiction", "context"
    ]
    label: str = Field(min_length=1, max_length=120)
    quote: str = Field(min_length=4, max_length=600)


class HarnessFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str | None = Field(
        default=None, pattern=r"^finding-[0-9a-f]{12}$"
    )
    affected_branch_ids: list[str] = Field(default_factory=list, max_length=12)
    title: str = Field(min_length=1, max_length=240)
    detail: str = Field(min_length=1, max_length=2_000)
    fact_summary: str | None = Field(default=None, max_length=500)
    impact: str | None = Field(default=None, max_length=500)
    file_refs: list[str] = Field(min_length=1, max_length=100)
    evidence_quotes: list[HarnessEvidenceQuote] = Field(
        default_factory=list, max_length=6
    )
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
    findings: list[HarnessFinding] = Field(min_length=1, max_length=10)
    follow_ups: list[str] = Field(default_factory=list, max_length=8)
    review_required: Literal[True] = True


class HarnessEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int = Field(ge=1)
    event_name: str = Field(min_length=1, max_length=120)
    occurred_at: datetime
    status: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=500)
    details: dict[str, Any] = Field(default_factory=dict)


class HarnessRunSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
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
    rounds: list[AgentControlLoopRound] = Field(default_factory=list, max_length=3)
    current_round: int = Field(default=0, ge=0, le=3)
    control_state: Literal[
        "running",
        "pause_requested",
        "paused",
        "stop_requested",
        "stopped",
    ] = "running"
    control_events: list[AgentControlLoopControlEvent] = Field(
        default_factory=list, max_length=100
    )
    decision_records: list[AgentControlLoopDecisionRecord] = Field(
        default_factory=list, max_length=100
    )
    branches: list[AgentControlLoopBranch] = Field(default_factory=list, max_length=36)
    active_branch_id: str | None = Field(
        default=None, pattern=r"^branch-[0-9a-f]{12}$"
    )
    artifact_versions: list[AgentControlLoopArtifactVersion] = Field(
        default_factory=list, max_length=3
    )
    commits: list[AgentControlLoopCommit] = Field(default_factory=list, max_length=20)
    last_commit: AgentControlLoopCommit | None = None
    brief: AgentControlLoopBrief | None = None
    plan: HarnessPlan | None = None
    model_receipt: HarnessModelReceipt | None = None
    analysis_receipt: HarnessModelReceipt | None = None
    result: HarnessTaskResult | None = None
    validation_errors: list[str] = Field(default_factory=list)
    events: list[HarnessEvent] = Field(default_factory=list)


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
        if len(normalized) < 3 or any(ord(character) < 32 and character not in "\n\t" for character in normalized):
            raise ValueError("instruction contains invalid content")
        return normalized

class HarnessRunStartResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run: HarnessRunSnapshot
    replayed: bool = False


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
    branches: list[AgentControlLoopBranch]
    active_branch_id: str | None
    artifact_versions: list[AgentControlLoopArtifactVersion]
    commits: list[AgentControlLoopCommit]
    last_commit: AgentControlLoopCommit | None
    brief: AgentControlLoopBrief | None
    plan: PublicHarnessPlan | None
    model_receipt: HarnessModelReceipt | None
    analysis_receipt: HarnessModelReceipt | None
    result: HarnessTaskResult | None
    validation_errors: list[str]
    events: list[HarnessEvent]


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

    def __init__(self, *, base_url: str, api_key: str, model: str = MODEL, timeout: float = 60) -> None:
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
                response = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                if response.status_code == 400 and "response_format" in response.text.lower():
                    payload.pop("response_format", None)
                    request_started = True
                    response = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("model content is not text")
            content = content.strip()
            if content.startswith("```"):
                content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return HarnessPlanCandidate.model_validate(json.loads(content))
        except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as exc:
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
            "每个 finding 只描述一个可处置问题。title 应是短标题；fact_summary 用不超过两句话说明发生了什么；impact 单独说明不处理的影响，"
            "不要把多个冲突、推测和建议塞进同一长段 detail。"
            "每个 finding.evidence_quotes 必须给出 1 到 6 个可在对应文件中逐字找到的短片段，至少精确定位一处依据；"
            "role 用 expected 表示设计或规则预期，用 observed 表示实际记录，用 support 表示支持结论，用 contradiction 表示冲突，用 context 表示上下文。"
            "表格 quote 应组合足以唯一定位一行的连续单元格文本；文本 quote 应选可唯一定位的连续原文，不得改写。"
            "finding.evidence_anchors 必须返回空数组；位置、行号和展示摘录由服务端验证原文后生成。"
            "每个 finding.review 必须说明是否需要人作业务决定。存在 contradiction 时 requires_human_decision 必须为 true，"
            "提供 2 到 3 个 A/B/C 选项、推荐项、推荐理由，以及用户确认后 Agent 将执行的下一步。"
            "每个 option.next_instruction 必须是一条可作为新只读 Control Loop 目标的完整指令；只能核对资料、形成修改建议或待办，不能声称直接改文件。"
            "若不需要人决策，也要说明 question、why_human、recommendation_reason 和 after_confirmation，options 可为空。"
            "若 validation_feedback 非空，上一候选未通过原文定位；保持原任务不变，并改用更长、只出现一次的连续原文重新生成全部 findings。"
            "只能完成只读分析，不得声称发送、写入、审批或调用外部系统。"
            "不要输出思维链、内部推理、Prompt、工具日志或 Markdown 代码围栏。"
            "结论存在不确定性时直接写入 summary。follow_ups 应给出 1 到 4 条基于当前证据、可由用户确认后作为新任务启动的具体推进建议，"
            "不要写成泛化的‘请人工复核’。review_required 必须为 true。"
            "只输出符合 JSON Schema 的 JSON 对象。JSON Schema：" + schema
        )
        user = json.dumps(
            {
                "instruction": instruction,
                "validated_plan": plan.model_dump(mode="json"),
                "files": files,
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
            "max_tokens": 4_000,
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
                    content.removeprefix("```json")
                    .removeprefix("```")
                    .removesuffix("```")
                    .strip()
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
    started_at_perf: float
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
    ) -> None:
        self.catalog = catalog
        self.planner = planner
        self.analyst = analyst
        self.state_store = state_store or InMemoryHarnessStateStore()
        self._runs: dict[tuple[str, str], _Run] = {}
        self._idempotent: dict[tuple[str, str], _IdempotentStart] = {}
        self._control_idempotent: dict[
            tuple[str, str], _IdempotentControl
        ] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    @property
    def backend_name(self) -> str:
        return self.state_store.backend_name

    async def setup(self) -> None:
        """Restore snapshots, but never replay an interrupted model call automatically."""

        await self.state_store.setup()
        now = datetime.now(timezone.utc)
        terminal_statuses = {"ready_to_execute", "completed", "stopped", "failed"}
        async with self._lock:
            for record in await self.state_store.load_runs():
                snapshot = HarnessRunSnapshot.model_validate(record.snapshot)
                resume_status = record.resume_status
                if snapshot.status not in terminal_statuses:
                    completed_rounds = [
                        item for item in snapshot.rounds if item.status == "completed"
                    ]
                    completed_round_numbers = {
                        item.round_number for item in completed_rounds
                    }
                    recovered_branches = [
                        item
                        for item in snapshot.branches
                        if item.round_number in completed_round_numbers
                    ]
                    recovered_branch_ids = {
                        item.branch_id for item in recovered_branches
                    }
                    recovered_status = (
                        "waiting_input"
                        if snapshot.status == "waiting_input"
                        else "paused"
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
                            "version": snapshot.version + 1,
                            "updated_at": now,
                        }
                    )
                    resume_status = "planning"
                elapsed_seconds = snapshot.budget.elapsed_ms / 1000
                run = _Run(
                    snapshot=snapshot,
                    condition=asyncio.Condition(),
                    started_at_perf=perf_counter() - elapsed_seconds,
                    resume_status=resume_status,
                )
                self._runs[(record.owner_id, record.run_id)] = run
                if snapshot.status not in terminal_statuses:
                    await self._persist_locked(run)

            for record in await self.state_store.load_idempotency():
                if record.kind == "start":
                    self._idempotent[(record.owner_id, record.idempotency_key)] = (
                        _IdempotentStart(
                            digest=record.digest,
                            result=HarnessRunStartResult.model_validate(record.result),
                        )
                    )
                else:
                    self._control_idempotent[
                        (record.owner_id, record.idempotency_key)
                    ] = _IdempotentControl(
                        digest=record.digest,
                        result=HarnessControlResult.model_validate(record.result),
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
            json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
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

    def get_internal_workspace(self) -> dict[str, Any]:
        try:
            return self.catalog.internal_workspace()
        except Exception as exc:
            raise HarnessError("FORTE 办公资料库暂时无法读取") from exc

    async def start(self, owner_id: str, request: HarnessRunStart) -> HarnessRunStartResult:
        workspace = self.get_internal_workspace()
        if workspace.get("workspace_id") != request.workspace_id:
            raise HarnessNotFoundError("办公资料库不存在")
        instruction = request.instruction
        workspace_files = self._index_files(workspace)
        digest = hashlib.sha256(
            json.dumps(request.model_dump(), ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        idem_key = (owner_id, request.idempotency_key)
        async with self._lock:
            replay = self._idempotent.get(idem_key)
            if replay is not None:
                if replay.digest != digest:
                    raise HarnessConflictError("幂等键已用于不同 Harness 命令")
                return replay.result.model_copy(update={"replayed": True}, deep=True)
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
            )
            budget = AgentControlLoopBudget(
                max_rounds=contract.max_rounds,
                max_files_per_round=contract.max_files_per_round,
                max_model_calls=contract.max_model_calls,
                deadline_seconds=contract.deadline_seconds,
            )
            snapshot = HarnessRunSnapshot(
                run_id=run_id,
                owner_id=owner_id,
                workspace_id=request.workspace_id,
                status="queued",
                version=request.expected_version, created_at=now, updated_at=now,
                instruction=instruction,
                instruction_source="user",
                contract=contract,
                budget=budget,
            )
            current = _Run(snapshot, asyncio.Condition(), perf_counter())
            result = HarnessRunStartResult(run=snapshot)
            existing = await self._persist_locked(
                current,
                StoredHarnessIdempotency(
                    owner_id=owner_id,
                    kind="start",
                    idempotency_key=request.idempotency_key,
                    digest=digest,
                    result=result.model_dump(mode="json"),
                ),
            )
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
            if snapshot.status in {"ready_to_execute", "completed", "stopped", "failed"}:
                raise HarnessConflictError("当前任务已经结束，不能再提交控制命令")

            command = request.command
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
                    item
                    for item in snapshot.branches
                    if item.status == "waiting_input"
                ]
                if request.branch_id is not None:
                    selected_branch = next(
                        (
                            item
                            for item in waiting_branches
                            if item.branch_id == request.branch_id
                        ),
                        None,
                    )
                    if selected_branch is None:
                        raise HarnessConflictError("该分支已经完成或不属于当前任务")
                elif waiting_branches:
                    selected_branch = waiting_branches[0]
                selected_branch_id = (
                    selected_branch.branch_id if selected_branch else None
                )

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
            run.snapshot = snapshot.model_copy(
                update={
                    "status": next_status,
                    "control_state": next_state,
                    "control_events": [*snapshot.control_events, control_event],
                    "active_branch_id": selected_branch_id,
                    "events": events,
                    "last_event_sequence": last_event_sequence,
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
            should_schedule = command == "resume" and run_id not in self._tasks
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
            raise HarnessConflictError("人工决策必须说明接受、否决或暂缓")
        if request.artifact_version is not None or request.instruction is not None:
            raise HarnessConflictError("人工决策不接受成果版本或方向字段")
        if request.finding_id is None and request.resolution_id is None:
            raise HarnessConflictError("人工决策必须绑定一条发现或证据定位")

        findings = self._snapshot_findings(snapshot)
        finding = next(
            (
                item
                for item in findings
                if item.finding_id == request.finding_id
            ),
            None,
        )
        resolutions = self._snapshot_evidence_resolutions(snapshot)
        resolution = next(
            (
                item
                for item in resolutions
                if item.resolution_id == request.resolution_id
            ),
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

        if request.decision_action == "accept":
            if resolution is not None:
                candidate_ids = {
                    item.candidate_id for item in resolution.candidates
                }
                if request.selected_candidate_id not in candidate_ids:
                    raise HarnessConflictError("请选择该证据定位中的一个候选位置")
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

        affected_branch_ids = (
            [resolution.branch_id]
            if resolution is not None and resolution.branch_id
            else finding.affected_branch_ids
            if finding is not None
            else []
        )
        branch_id = request.branch_id or (
            affected_branch_ids[0] if affected_branch_ids else None
        )
        if (
            request.branch_id is not None
            and affected_branch_ids
            and request.branch_id not in affected_branch_ids
        ):
            raise HarnessConflictError("人工决策不能绑定到无关分支")

        now = datetime.now(timezone.utc)
        next_version = snapshot.version + 1
        decision_id = f"decision-{uuid4().hex[:12]}"
        record = AgentControlLoopDecisionRecord(
            decision_id=decision_id,
            action=request.decision_action,
            finding_id=finding_id,
            resolution_id=resolution.resolution_id if resolution else None,
            branch_id=branch_id,
            selected_option_id=request.selected_option_id,
            selected_candidate_id=request.selected_candidate_id,
            feedback=request.feedback,
            recorded_at=now,
            accepted_task_version=next_version,
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
        run.snapshot = snapshot.model_copy(
            update={
                "decision_records": [*snapshot.decision_records, record],
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
        if request.branch_id is not None or request.instruction is not None or any(
            value is not None
            for value in (
                request.decision_action,
                request.finding_id,
                request.resolution_id,
                request.selected_option_id,
                request.selected_candidate_id,
                request.feedback,
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

        stored_versions = await self.state_store.load_artifact_versions(
            owner_id, snapshot.run_id
        )
        stored = next(
            (
                item
                for item in stored_versions
                if item.artifact_id == target.artifact_id
                and item.version == target.version
            ),
            None,
        )
        target_payload = target.model_dump(mode="json")
        if stored is None or stored.payload_digest != self._payload_digest(
            target_payload
        ):
            raise HarnessConflictError("成果版本的不可变记录不完整，已拒绝恢复")

        now = datetime.now(timezone.utc)
        next_version = snapshot.version + 1
        commit_id = "commit-" + hashlib.sha256(
            (
                f"{snapshot.run_id}:rollback:{snapshot.last_commit.commit_id}:"
                f"{target.artifact_id}:{target.version}"
            ).encode("utf-8")
        ).hexdigest()[:12]
        task_commit = AgentControlLoopCommit(
            commit_id=commit_id,
            artifact_id=target.artifact_id,
            artifact_version=target.version,
            operation="rollback",
            parent_commit_id=snapshot.last_commit.commit_id,
            summary=(
                f"已将当前任务简报恢复为 v{target.version}；历史版本均保留，"
                "原始办公文件未修改。"
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
        self._control_idempotent[idempotency_key] = _IdempotentControl(
            digest=digest, result=result
        )
        return result.model_copy(deep=True)

    def public_start_result(self, result: HarnessRunStartResult) -> PublicHarnessRunStartResult:
        return PublicHarnessRunStartResult(
            run=self.public_snapshot(result.run),
            replayed=result.replayed,
        )

    def public_snapshot(self, snapshot: HarnessRunSnapshot) -> PublicHarnessRunSnapshot:
        ref_to_label = {
            str(document.get("file_ref")): str(
                document.get("display_label", "所选公开办公文件")
            )
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
            self._public_round(round_snapshot, ref_to_label)
            for round_snapshot in snapshot.rounds
        ]
        public_brief = self._public_brief(snapshot.brief, ref_to_label)
        public_artifacts = [
            item.model_copy(
                update={
                    "summary": self._project_business_text(
                        item.summary, ref_to_label
                    ),
                    "findings": [
                        finding.model_copy(
                            update={
                                "title": self._project_business_text(
                                    finding.title, ref_to_label
                                ),
                                "detail": self._project_business_text(
                                    finding.detail, ref_to_label
                                ),
                                "fact_summary": self._project_business_text(
                                    finding.fact_summary, ref_to_label
                                )
                                if finding.fact_summary
                                else None,
                                "impact": self._project_business_text(
                                    finding.impact, ref_to_label
                                )
                                if finding.impact
                                else None,
                                "evidence_resolutions": [
                                    self._public_evidence_resolution(
                                        resolution, ref_to_label
                                    )
                                    for resolution in finding.evidence_resolutions
                                ],
                                "review": self._public_finding_review(
                                    finding.review, ref_to_label
                                ),
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
                                "label": self._project_business_text(
                                    gap.label, ref_to_label
                                ),
                                "detail": self._project_business_text(
                                    gap.detail, ref_to_label
                                ),
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
                    "objective": self._project_business_text(
                        item.objective, ref_to_label
                    ),
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
        return PublicHarnessRunSnapshot(
            run_id=snapshot.run_id,
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
            decision_records=snapshot.decision_records,
            branches=public_branches,
            active_branch_id=snapshot.active_branch_id,
            artifact_versions=public_artifacts,
            commits=snapshot.commits,
            last_commit=snapshot.last_commit,
            brief=public_brief,
            plan=public_plan,
            model_receipt=snapshot.model_receipt,
            analysis_receipt=snapshot.analysis_receipt,
            result=public_result,
            validation_errors=[
                self._public_failure_message(error) for error in snapshot.validation_errors
            ],
            events=public_events,
        )

    def public_control_result(
        self, result: HarnessControlResult
    ) -> PublicHarnessControlResult:
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
            selection_reason=self._project_business_text(
                plan.selection_reason, ref_to_label
            ),
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
                    affected_branch_ids=finding.affected_branch_ids,
                    title=self._project_business_text(finding.title, ref_to_label),
                    detail=self._project_business_text(finding.detail, ref_to_label),
                    fact_summary=self._project_business_text(
                        finding.fact_summary, ref_to_label
                    )
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
                self._project_business_text(item, ref_to_label)
                for item in result.follow_ups
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
                "why_human": self._project_business_text(
                    review.why_human, ref_to_label
                ),
                "recommendation_reason": self._project_business_text(
                    review.recommendation_reason, ref_to_label
                ),
                "after_confirmation": self._project_business_text(
                    review.after_confirmation, ref_to_label
                ),
                "options": [
                    option.model_copy(
                        update={
                            "label": self._project_business_text(
                                option.label, ref_to_label
                            ),
                            "meaning": self._project_business_text(
                                option.meaning, ref_to_label
                            ),
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
                "fact_summary": self._project_business_text(
                    resolution.fact_summary, ref_to_label
                )
                if resolution.fact_summary
                else None,
                "impact": self._project_business_text(
                    resolution.impact, ref_to_label
                )
                if resolution.impact
                else None,
                "query_excerpt": self._project_business_text(
                    resolution.query_excerpt, ref_to_label
                ),
                "reason": self._project_business_text(
                    resolution.reason, ref_to_label
                ),
                "candidates": [
                    candidate.model_copy(
                        update={
                            "excerpt": self._project_business_text(
                                candidate.excerpt, ref_to_label
                            )
                        }
                    )
                    for candidate in resolution.candidates
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
                "question": self._project_business_text(
                    round_snapshot.question, ref_to_label
                ),
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
                            "label": self._project_business_text(
                                gap.label, ref_to_label
                            ),
                            "detail": self._project_business_text(
                                gap.detail, ref_to_label
                            ),
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
            for marker in ("artifact.write", "run_workspace_write", "artifact_name", "artifact_type")
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
                    if latest.status in {
                        "ready_to_execute",
                        "completed",
                        "stopped",
                        "failed",
                    } or latest.last_event_sequence > sequence:
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
                await self._set_source_documents(
                    owner_id, run_id, files, selection_reason
                )
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
                for follow_up in HarnessTaskResult.model_validate(
                    round_snapshot.result
                ).follow_ups
            ]
            next_question = instruction
            evidence_recheck_refs: set[str] = set()
            target_branch_id = recovered.active_branch_id
            if recovered.rounds and recovered.rounds[-1].next_step:
                recovered_next_step = recovered.rounds[-1].next_step
                next_question = recovered_next_step.next_question or instruction
                if recovered_next_step.decision == "waiting_input":
                    target_branch = self._branch_by_id(
                        recovered.branches, target_branch_id
                    )
                    evidence_recheck_refs = set(
                        target_branch.missing_file_refs
                        if target_branch
                        else recovered_next_step.candidate_file_refs
                    )
            terminal_decision = "completed"

            contract = recovered.contract
            first_round = len(recovered.rounds) + 1
            for round_number in range(first_round, contract.max_rounds + 1):
                await self._safe_point(owner_id, run_id)
                all_remaining = [
                    item
                    for item in files
                    if str(item["file_ref"]) not in set(verified_refs)
                ]
                remaining = (
                    [
                        item
                        for item in all_remaining
                        if str(item["file_ref"]) in evidence_recheck_refs
                    ]
                    if evidence_recheck_refs
                    else all_remaining
                )
                if not remaining:
                    break

                steer = await self._consume_pending_steer(owner_id, run_id)
                question = (
                    f"{next_question}\n本轮方向调整：{steer}"
                    if steer
                    else next_question
                )
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
                round_files = [
                    item for item in remaining if str(item["file_ref"]) in round_refs
                ]
                branch_ids = await self._set_plan(
                    owner_id,
                    run_id,
                    plan,
                    round_number=round_number,
                    parent_branch_id=target_branch_id,
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
                await self._safe_point(owner_id, run_id)

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

                await self._update_round(
                    owner_id, run_id, round_number, phase="act"
                )
                analysis_files = self._analysis_inputs(round_files)
                result: HarnessTaskResult | None = None
                analysis_receipt: HarnessModelReceipt | None = None
                validation_feedback: str | None = None
                best_result: HarnessTaskResult | None = None
                best_receipt: HarnessModelReceipt | None = None
                best_rejected_count = 0
                best_evidence_resolutions: list[
                    AgentControlLoopEvidenceResolution
                ] = []
                pending_evidence_resolutions: list[
                    AgentControlLoopEvidenceResolution
                ] = []
                omitted_finding_count = 0
                recovery_kind: Literal["source_location", "analysis_output"] = (
                    "source_location"
                )
                for analysis_attempt in (1, 2):
                    try:
                        candidate, candidate_receipt = await self._invoke_analyst(
                            owner_id=owner_id,
                            run_id=run_id,
                            round_number=round_number,
                            instruction=question,
                            plan=plan,
                            files=analysis_files,
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
                        self._validate_candidate_result_scope(candidate, round_files)
                        resolution = self._resolve_evidence_anchors(
                            candidate, analysis_files
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
                    if resolution.result is not None and (
                        best_result is None
                        or len(resolution.result.findings) > len(best_result.findings)
                    ):
                        best_result = resolution.result
                        best_receipt = candidate_receipt
                        best_rejected_count = resolution.rejected_finding_count
                        best_evidence_resolutions = list(
                            resolution.evidence_resolutions
                        )
                    elif resolution.result is None:
                        pending_evidence_resolutions = list(
                            resolution.evidence_resolutions
                        )
                    if resolution.result is not None and not resolution.rejected_finding_count:
                        result = resolution.result
                        analysis_receipt = candidate_receipt
                        pending_evidence_resolutions = list(
                            resolution.evidence_resolutions
                        )
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
                        },
                    )
                    if analysis_attempt == 1:
                        validation_feedback = (
                            "上一候选有 Finding 没有任何 quote 能在对应文件中唯一匹配。"
                            "请保留任务目标并重新生成全部 findings；每条至少选择一段更长、连续、只出现一次的原文，"
                            "表格请组合能唯一定位整行的关键单元格，不要复用日志中的重复短句。"
                        )
                        continue
                    result = best_result
                    analysis_receipt = best_receipt
                    omitted_finding_count = best_rejected_count
                    pending_evidence_resolutions = best_evidence_resolutions

                if result is None or analysis_receipt is None:
                    branches = await self._reconcile_branches(
                        owner_id,
                        run_id,
                        verified_refs=verified_refs,
                        through_round=round_number,
                    )
                    waiting_branches = [
                        item for item in branches if item.status == "waiting_input"
                    ]
                    pending_evidence_resolutions = (
                        self._bind_evidence_resolutions_to_branches(
                            pending_evidence_resolutions, branches
                        )
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
                        candidate_branch_ids=[
                            item.branch_id for item in waiting_branches
                        ],
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
                        target_branch = self._branch_by_id(
                            resumed.branches, target_branch_id
                        )
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

                if omitted_finding_count:
                    await self._transition(
                        owner_id,
                        run_id,
                        "analyzing",
                        "analysis_partial_adopted",
                        (
                            f"服务端采用 {len(result.findings)} 条可唯一定位的发现，"
                            f"省略 {omitted_finding_count} 条无法核对的候选内容。"
                        ),
                        {
                            "round_number": round_number,
                            "adopted_finding_count": len(result.findings),
                            "omitted_finding_count": omitted_finding_count,
                            "output_used": True,
                        },
                    )
                adopted_analysis = analysis_receipt.model_copy(
                    update={"output_used": True}
                )
                binding_snapshot = await self.get(owner_id, run_id)
                result = self._bind_result_to_branches(
                    result,
                    binding_snapshot.branches,
                    estimated_additional_rounds=max(
                        0, contract.max_rounds - round_number
                    ),
                )
                pending_evidence_resolutions = (
                    self._bind_evidence_resolutions_to_branches(
                        pending_evidence_resolutions,
                        binding_snapshot.branches,
                    )
                )
                await self._set_analysis_receipt(
                    owner_id, run_id, adopted_analysis
                )
                await self._update_round(
                    owner_id,
                    run_id,
                    round_number,
                    phase="act",
                    analysis_receipt=adopted_analysis.model_dump(mode="json"),
                )
                round_verified = self._result_file_refs(result, round_files)
                unresolved_file_refs = {
                    item.file_ref
                    for item in pending_evidence_resolutions
                    if item.status != "exact"
                }
                round_verified = [
                    item
                    for item in round_verified
                    if item not in unresolved_file_refs
                ]
                for file_ref in round_verified:
                    if file_ref not in verified_refs:
                        verified_refs.append(file_ref)
                all_findings.extend(result.findings)
                all_follow_ups.extend(result.follow_ups)
                await self._update_round(
                    owner_id,
                    run_id,
                    round_number,
                    phase="verify",
                    result=result.model_dump(mode="json"),
                    analysis_receipt=adopted_analysis.model_dump(mode="json"),
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
                    "服务端已核对本轮结论的文件引用、原文定位与只读边界。",
                    {
                        "round_number": round_number,
                        "finding_count": len(result.findings),
                        "verified_file_count": len(round_verified),
                        "evidence_anchor_count": sum(
                            len(finding.evidence_anchors)
                            for finding in result.findings
                        ),
                        "omitted_finding_count": omitted_finding_count,
                        "output_used": True,
                    },
                )
                await self._safe_point(owner_id, run_id)

                waiting_branches = [
                    item for item in branches if item.status == "waiting_input"
                ]
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
                    reason = "所有任务分支的证据均已核对，完成条件已满足。"
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
                    candidate_branch_ids=[
                        item.branch_id for item in waiting_branches
                    ],
                    recovery_kind=(
                        "source_location"
                        if pending_evidence_resolutions
                        else None
                    ),
                    evidence_resolutions=pending_evidence_resolutions[:20],
                )
                if any(
                    item.status == "ambiguous"
                    for item in pending_evidence_resolutions
                ):
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
                if any(
                    finding.review
                    and finding.review.requires_human_decision
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
                            "pending_resolution_count": len(
                                pending_evidence_resolutions
                            ),
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
                    target_branch = self._branch_by_id(
                        resumed.branches, target_branch_id
                    )
                    evidence_recheck_refs = set(
                        target_branch.missing_file_refs
                        if target_branch
                        else next_step.candidate_file_refs
                    )
                    next_question = (
                        f"继续核对“{target_branch.title}”分支缺少的证据，"
                        "检查是否改变已有结论。"
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
                verified_refs=self._snapshot_verified_refs(
                    await self.get(owner_id, run_id)
                ),
                decision="user_stopped",
            )
        except HarnessBudgetExhausted:
            snapshot = await self.get(owner_id, run_id)
            await self._finalize_loop(
                owner_id,
                run_id,
                findings=self._snapshot_findings(snapshot),
                follow_ups=[],
                verified_refs=self._snapshot_verified_refs(snapshot),
                decision="budget_exhausted",
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
            run.snapshot = snapshot.model_copy(
                update={
                    "status": "waiting_input",
                    "control_state": "paused",
                    "events": [*snapshot.events, event],
                    "last_event_sequence": event.sequence,
                    "version": snapshot.version + 1,
                    "budget": self._budget_with_elapsed(run),
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
                snapshot = run.snapshot.model_copy(
                    update={"budget": self._budget_with_elapsed(run)}
                )
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
                    latest_state = self._require_run(
                        owner_id, run_id
                    ).snapshot.control_state
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

    async def _consume_pending_steer(
        self, owner_id: str, run_id: str
    ) -> str | None:
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
            instruction = "；".join(
                item.instruction for item in pending if item.instruction
            )
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
            budget = self._budget_with_elapsed(run).model_copy(
                update={"rounds_used": round_number}
            )
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
                    elapsed_ms=exc.elapsed_ms
                    or max(0, round((perf_counter() - started) * 1000)),
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
            if (
                budget.model_calls_used >= budget.max_model_calls
                or budget.elapsed_ms >= budget.deadline_seconds * 1000
            ):
                raise HarnessBudgetExhausted("模型调用或时间预算已经耗尽")
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
            rounds = [
                item.model_copy(update=updates)
                if item.round_number == round_number
                else item
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
            artifact_id = "artifact-" + hashlib.sha256(
                f"{run_id}:evidence-brief".encode("utf-8")
            ).hexdigest()[:12]
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
                source_file_refs=round_snapshot.verified_file_refs,
                finding_count=len(result.findings) if result else 0,
                parent_version=version - 1 if version > 1 else None,
                created_at=datetime.now(timezone.utc),
            )
            run.snapshot = snapshot.model_copy(
                update={
                    "artifact_versions": [*snapshot.artifact_versions, artifact],
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            await self._persist_locked(run, artifact_version=artifact)

    async def _set_verified_count(
        self, owner_id: str, run_id: str, count: int
    ) -> None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            budget = self._budget_with_elapsed(run).model_copy(
                update={"files_verified": count}
            )
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
    def _plan_file_refs(
        plan: HarnessPlan, files: list[dict[str, Any]]
    ) -> list[str]:
        referenced = {
            file_ref for unit in plan.units for file_ref in unit.input_file_refs
        }
        ordered = [
            str(item["file_ref"])
            for item in files
            if str(item["file_ref"]) in referenced
        ]
        if not ordered:
            raise HarnessPlanError("本轮计划没有引用任何允许文件")
        return ordered

    @staticmethod
    def _result_file_refs(
        result: HarnessTaskResult, files: list[dict[str, Any]]
    ) -> list[str]:
        anchored = {
            anchor.file_ref
            for finding in result.findings
            for anchor in finding.evidence_anchors
        }
        unresolved = {
            resolution.file_ref
            for finding in result.findings
            for resolution in finding.evidence_resolutions
            if resolution.status != "exact"
        }
        verified = anchored - unresolved
        return [
            str(item["file_ref"])
            for item in files
            if str(item["file_ref"]) in verified
        ]

    @staticmethod
    def _matching_branch_ids(
        file_refs: list[str], branches: list[AgentControlLoopBranch]
    ) -> list[str]:
        referenced = set(file_refs)
        ranked = sorted(
            (
                (len(referenced.intersection(branch.input_file_refs)), branch)
                for branch in branches
            ),
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
            branch_ids = cls._matching_branch_ids(finding.file_refs, branches)[:12]
            resolutions = [
                item.model_copy(
                    update={
                        "branch_id": next(
                            (
                                branch_id
                                for branch_id in branch_ids
                                if item.file_ref
                                in next(
                                    branch.input_file_refs
                                    for branch in branches
                                    if branch.branch_id == branch_id
                                )
                            ),
                            branch_ids[0] if branch_ids else None,
                        )
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
            branch_ids = cls._matching_branch_ids([resolution.file_ref], branches)
            bound.append(
                resolution.model_copy(
                    update={"branch_id": branch_ids[0] if branch_ids else None}
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
                f"{branch.branch_id}:{','.join(branch.missing_file_refs)}".encode(
                    "utf-8"
                )
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
                branch_verified = [
                    item for item in branch.input_file_refs if item in verified
                ]
                missing = [
                    item for item in branch.input_file_refs if item not in verified
                ]
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
            run.snapshot = run.snapshot.model_copy(
                update={"branches": branches, "updated_at": now}
            )
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
        waiting_branches = [
            item for item in snapshot.branches if item.status == "waiting_input"
        ]
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
        unique_follow_ups = list(
            dict.fromkeys([*follow_ups, *(gap.label for gap in gaps)])
        )

        if decision == "completed" and not gaps:
            outcome: Literal["completed", "bounded", "user_stopped"] = "completed"
            status = "completed"
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
            stop_reason = "轮次、模型调用或时间预算已耗尽"
            event_name = "loop_budget_stopped"
            message = "Agent Control Loop 已在预算边界停止，并保留未完成项。"

        brief = AgentControlLoopBrief(
            outcome=outcome,
            summary=summary,
            verified_file_refs=verified_refs,
            unresolved_gaps=gaps,
            rounds_completed=len(
                [item for item in snapshot.rounds if item.status == "completed"]
            ),
        )
        result = None
        if unique_findings:
            result = HarnessTaskResult(
                summary=summary,
                findings=unique_findings[:10],
                follow_ups=unique_follow_ups[:4],
                review_required=True,
            )

        async with self._lock:
            run = self._require_run(owner_id, run_id)
            current = run.snapshot
            rounds = list(current.rounds)
            if rounds and rounds[-1].status == "running":
                fallback_step = AgentControlLoopNextStep(
                    decision="user_stopped"
                    if decision == "user_stopped"
                    else "budget_exhausted",
                    reason=stop_reason or message,
                    candidate_file_refs=[
                        str(item.get("file_ref")) for item in unresolved_files
                    ][:20],
                    candidate_branch_ids=[
                        item.branch_id for item in waiting_branches
                    ],
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
            budget = self._budget_with_elapsed(run).model_copy(
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
                    item.model_copy(
                        update={"status": "stopped", "updated_at": now}
                    )
                    if item.status in {"running", "waiting_input"}
                    else item
                    for item in branches
                ]
            if status == "completed" and artifact_versions:
                final_artifact = artifact_versions[-1]
                commit_id = "commit-" + hashlib.sha256(
                    (
                        f"{run_id}:{final_artifact.artifact_id}:"
                        f"{final_artifact.version}:{summary}"
                    ).encode("utf-8")
                ).hexdigest()[:12]
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
                "external_action": False,
            },
        )

    @staticmethod
    def _snapshot_findings(snapshot: HarnessRunSnapshot) -> list[HarnessFinding]:
        findings: list[HarnessFinding] = []
        for round_snapshot in snapshot.rounds:
            if round_snapshot.result:
                findings.extend(
                    HarnessTaskResult.model_validate(round_snapshot.result).findings
                )
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

    async def _mark_current_round_failed(
        self, owner_id: str, run_id: str
    ) -> None:
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
                    item.model_copy(
                        update={"status": "failed", "updated_at": now}
                    )
                    if item.round_number == current_round
                    and item.status == "running"
                    else item
                    for item in run.snapshot.branches
                ]
                run.snapshot = run.snapshot.model_copy(
                    update={"rounds": rounds, "branches": branches}
                )
                await self._persist_locked(run)

    @staticmethod
    def _budget_with_elapsed(run: _Run) -> AgentControlLoopBudget:
        return run.snapshot.budget.model_copy(
            update={
                "elapsed_ms": max(
                    0, round((perf_counter() - run.started_at_perf) * 1000)
                )
            }
        )

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

    async def _invoke_analyst(
        self,
        *,
        owner_id: str,
        run_id: str,
        round_number: int,
        instruction: str,
        plan: HarnessPlan,
        files: list[dict[str, Any]],
        attempt: int,
        validation_feedback: str | None,
    ) -> tuple[HarnessTaskResult, HarnessModelReceipt]:
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
            result = await self.analyst.analyze(
                instruction=instruction,
                plan=plan,
                files=files,
                validation_feedback=validation_feedback,
            )
        except HarnessModelError as exc:
            receipt = HarnessModelReceipt(
                called=exc.called,
                model=exc.model,
                elapsed_ms=exc.elapsed_ms
                or max(0, round((perf_counter() - analysis_started) * 1000)),
                output_used=False,
            )
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
                "display_path": item.get("display_path", item.get("display_label", "公开办公输入文件")),
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

    @classmethod
    def _resolve_text_anchor_candidates(
        cls,
        *,
        file_ref: str,
        role: Literal[
            "expected", "observed", "support", "contradiction", "context"
        ],
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
        anchors: list[AgentControlLoopEvidenceAnchor] = []
        seen_ranges: set[tuple[int, int]] = set()
        for position in positions[:6]:
            start = line_map[position]
            end = line_map[position + len(normalized_quote) - 1]
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
        role: Literal[
            "expected", "observed", "support", "contradiction", "context"
        ],
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

    @classmethod
    def _resolve_evidence_anchors(
        cls,
        result: HarnessTaskResult,
        files: list[dict[str, Any]],
    ) -> _EvidenceResolution:
        files_by_ref = {str(item.get("file_ref")): item for item in files}
        resolved_findings: list[HarnessFinding] = []
        evidence_resolutions: list[AgentControlLoopEvidenceResolution] = []
        rejected_finding_count = 0
        rejected_file_refs: list[str] = []
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
                        candidate_id=cls._evidence_candidate_id(
                            resolution_id, match
                        ),
                        file_ref=match.file_ref,
                        locator_kind=match.locator_kind,
                        start=match.start,
                        end=match.end,
                        excerpt=match.excerpt,
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
                        f"同一片段在安全预览中匹配到 {len(matches)} 个位置，"
                        "服务端不能替用户选择。"
                    )
                else:
                    status = "unavailable"
                    reason = "服务端在本轮安全预览中没有找到可核对的位置。"
                finding_resolutions.append(
                    AgentControlLoopEvidenceResolution(
                        resolution_id=resolution_id,
                        finding_id=finding_id,
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
                    )
                )
            unresolved = [
                item for item in finding_resolutions if item.status != "exact"
            ]
            evidence_resolutions.extend(unresolved)
            if not anchors:
                rejected_finding_count += 1
                for file_ref in finding.file_refs:
                    if file_ref in files_by_ref and file_ref not in rejected_file_refs:
                        rejected_file_refs.append(file_ref)
                continue
            resolved_findings.append(
                finding.model_copy(
                    update={
                        "finding_id": finding_id,
                        "evidence_quotes": [],
                        "evidence_anchors": anchors,
                        "evidence_resolutions": finding_resolutions,
                    }
                )
            )
        resolved_result = (
            result.model_copy(update={"findings": resolved_findings})
            if resolved_findings
            else None
        )
        return _EvidenceResolution(
            result=resolved_result,
            rejected_finding_count=rejected_finding_count,
            rejected_file_refs=tuple(rejected_file_refs),
            evidence_resolutions=tuple(evidence_resolutions),
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
    def _evidence_candidate_id(
        resolution_id: str, anchor: AgentControlLoopEvidenceAnchor
    ) -> str:
        digest = hashlib.sha256(
            (
                f"{resolution_id}:{anchor.file_ref}:{anchor.locator_kind}:"
                f"{anchor.start}:{anchor.end}:{anchor.excerpt}"
            ).encode("utf-8")
        ).hexdigest()
        return f"candidate-{digest[:12]}"

    @staticmethod
    def _validate_candidate_result_scope(
        result: HarnessTaskResult, files: list[dict[str, Any]]
    ) -> None:
        """Reject out-of-scope model references before attempting location repair."""

        allowed_refs = {str(item["file_ref"]) for item in files}
        for finding in result.findings:
            if not set(finding.file_refs).issubset(allowed_refs):
                raise HarnessPlanError("分析结果引用了本轮计划之外的文件")
            if any(
                quote.file_ref not in finding.file_refs
                or quote.file_ref not in allowed_refs
                for quote in finding.evidence_quotes
            ):
                raise HarnessPlanError("分析结果的逐字引用超出本轮允许范围")

    @staticmethod
    def _validate_result(
        result: HarnessTaskResult, files: list[dict[str, Any]]
    ) -> None:
        allowed_refs = {str(item["file_ref"]) for item in files}
        for finding in result.findings:
            if not set(finding.file_refs).issubset(allowed_refs):
                raise HarnessPlanError("分析结果引用了本轮计划之外的文件")
            if not finding.evidence_anchors:
                raise HarnessPlanError("分析结果缺少服务端已定位的证据锚点")
            if any(
                anchor.file_ref not in finding.file_refs
                or anchor.file_ref not in allowed_refs
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
                dependency
                for dependency in payload["depends_on"]
                if dependency in kept_ids
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
        allowed_effects = set(workspace.get("allowed_side_effects", ["none", "run_workspace_write"]))
        if not allowed_tools:
            raise HarnessPlanError("办公资料库没有工具 allowlist")
        ids = [unit.unit_id for unit in plan.units]
        if len(ids) != len(set(ids)):
            raise HarnessPlanError("工作单元 ID 重复")
        referenced_refs = {
            file_ref for unit in plan.units for file_ref in unit.input_file_refs
        }
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
                    raise HarnessPlanError("artifact.write 必须声明受控 artifact_name 和 artifact_type")
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

    async def _transition(self, owner_id: str, run_id: str, status: str, name: str, message: str, details: dict[str, Any]) -> None:
        if status not in self.ALLOWED_STATUSES:
            raise HarnessConflictError(f"未知 Harness 状态: {status}")
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            now = datetime.now(timezone.utc)
            event = HarnessEvent(sequence=len(run.snapshot.events) + 1, event_name=name, occurred_at=now, status=status, message=message, details=details)
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

    async def _set_model_receipt(self, owner_id: str, run_id: str, receipt: HarnessModelReceipt) -> None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            run.snapshot = run.snapshot.model_copy(update={"model_receipt": receipt, "updated_at": datetime.now(timezone.utc)})
            await self._persist_locked(run)

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

    async def _set_result(
        self, owner_id: str, run_id: str, result: HarnessTaskResult
    ) -> None:
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
        return next(
            (item for item in branches if item.branch_id == branch_id), None
        )

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
            + hashlib.sha256(
                f"{run_id}:{round_number}:{unit.unit_id}".encode("utf-8")
            ).hexdigest()[:12]
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
                status="running",
                requires_human_gate=unit.requires_human_gate,
                created_at=now,
                updated_at=now,
            )
            for unit in plan.units
        ]

    async def _fail(self, owner_id: str, run_id: str, reason: str) -> None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            run.snapshot = run.snapshot.model_copy(
                update={"validation_errors": [reason], "updated_at": datetime.now(timezone.utc)}
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
    )
