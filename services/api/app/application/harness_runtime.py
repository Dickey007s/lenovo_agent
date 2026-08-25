"""Unified, file-backed Agent Harness runtime.

The runtime supports a bounded read-only workspace task: it freezes public
FORTE inputs, asks one model call for a validated plan, and asks a second model
call for a cited answer over safe file previews.  It never executes external
actions or exposes benchmark task instructions, paths, hashes, or hidden
reasoning to the foreground.
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
    units: list[HarnessPlanCandidateUnit] = Field(min_length=1, max_length=12)


class HarnessPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1_000)
    units: list[HarnessPlanUnit] = Field(min_length=1, max_length=12)


class HarnessModelReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    called: bool
    model: str
    elapsed_ms: int = Field(ge=0)
    output_used: bool


class HarnessFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=240)
    detail: str = Field(min_length=1, max_length=2_000)
    file_refs: list[str] = Field(min_length=1, max_length=100)


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
    selected_file_refs: list[str] = Field(min_length=1, max_length=20)

    @field_validator("instruction")
    @classmethod
    def validate_instruction(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3 or any(ord(character) < 32 and character not in "\n\t" for character in normalized):
            raise ValueError("instruction contains invalid content")
        return normalized

    @field_validator("selected_file_refs")
    @classmethod
    def validate_file_refs(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("selected_file_refs contains duplicates")
        if any(not re.fullmatch(r"forte-[0-9a-f]{16}", item) for item in value):
            raise ValueError("selected_file_refs contains an invalid reference")
        return value


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
            "你是企业办公 Agent Harness 的规划器。根据公开办公任务和文件索引生成最小可执行 DAG。"
            "只输出一个符合 JSON Schema 的 JSON 对象。只能引用 files 中出现的 file_ref；tool 必须来自 allowlisted_tools；"
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
            "只能完成只读分析，不得声称发送、写入、审批或调用外部系统。"
            "不要输出思维链、内部推理、Prompt、工具日志或 Markdown 代码围栏。"
            "结论存在不确定性时直接写入 summary 或 follow_ups，review_required 必须为 true。"
            "只输出符合 JSON Schema 的 JSON 对象。JSON Schema：" + schema
        )
        user = json.dumps(
            {
                "instruction": instruction,
                "validated_plan": plan.model_dump(mode="json"),
                "files": files,
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


@dataclass(frozen=True)
class _IdempotentStart:
    digest: str
    result: HarnessRunStartResult


class HarnessRuntime:
    """One owner/version/idempotent in-memory run store with named SSE events."""

    ALLOWED_STATUSES = {
        "queued",
        "indexing",
        "planning",
        "validating",
        "ready_to_execute",
        "analyzing",
        "verifying",
        "completed",
        "failed",
    }
    MAX_UNITS = 12

    def __init__(
        self,
        catalog: HarnessWorkspaceCatalog,
        planner: HarnessPlanner,
        analyst: HarnessAnalyst | None = None,
    ) -> None:
        self.catalog = catalog
        self.planner = planner
        self.analyst = analyst
        self._runs: dict[tuple[str, str], _Run] = {}
        self._idempotent: dict[tuple[str, str], _IdempotentStart] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

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
            snapshot = HarnessRunSnapshot(
                run_id=run_id,
                owner_id=owner_id,
                workspace_id=request.workspace_id,
                status="queued",
                version=request.expected_version, created_at=now, updated_at=now,
                instruction=instruction,
                instruction_source="user",
            )
            current = _Run(snapshot, asyncio.Condition())
            self._runs[(owner_id, run_id)] = current
            result = HarnessRunStartResult(run=snapshot)
            self._idempotent[idem_key] = _IdempotentStart(digest, result)
            task = asyncio.create_task(
                self._run(
                    owner_id,
                    run_id,
                    workspace,
                    instruction,
                    request.selected_file_refs,
                )
            )
            self._tasks[run_id] = task
            task.add_done_callback(lambda done, rid=run_id: self._tasks.pop(rid, None))
            return result.model_copy(deep=True)

    async def get(self, owner_id: str, run_id: str) -> HarnessRunSnapshot:
        async with self._lock:
            run = self._runs.get((owner_id, run_id))
            if run is None:
                raise HarnessNotFoundError("Harness run 不存在")
            return run.snapshot.model_copy(deep=True)

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
        public_plan = None
        if snapshot.plan is not None:
            public_plan = PublicHarnessPlan(
                summary=self._project_business_text(snapshot.plan.summary, ref_to_label),
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
                    for unit in snapshot.plan.units
                ],
            )
        public_result = None
        if snapshot.result is not None:
            public_result = HarnessTaskResult(
                summary=self._project_business_text(snapshot.result.summary, ref_to_label),
                findings=[
                    HarnessFinding(
                        title=self._project_business_text(finding.title, ref_to_label),
                        detail=self._project_business_text(finding.detail, ref_to_label),
                        file_refs=finding.file_refs,
                    )
                    for finding in snapshot.result.findings
                ],
                follow_ups=[
                    self._project_business_text(item, ref_to_label)
                    for item in snapshot.result.follow_ups
                ],
                review_required=True,
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
            plan=public_plan,
            model_receipt=snapshot.model_receipt,
            analysis_receipt=snapshot.analysis_receipt,
            result=public_result,
            validation_errors=[
                self._public_failure_message(error) for error in snapshot.validation_errors
            ],
            events=public_events,
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
        elif event.event_name == "harness_failed":
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
        if "所选文件不属于" in reason or "办公资料库没有可用输入文件" in reason:
            return "所选资料当前不可用，系统已安全停止。请重新选择资料后再运行。"
        if "分析结果引用了未选择的文件" in reason:
            return "分析结果引用了本轮范围外的资料，系统未采用该结果。请重新运行。"
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
                terminal = current.status in {"ready_to_execute", "completed", "failed"}
                condition = run.condition
            for event in pending:
                sequence = event.sequence
                yield event
            if terminal:
                return
            async with condition:
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
        selected_file_refs: list[str],
    ) -> None:
        try:
            files = self._index_files(workspace, selected_file_refs)
            selection_reason = f"用户从完整办公资料库中选择了 {len(files)} 份公开文件"
            await self._set_source_documents(
                owner_id, run_id, files, selection_reason
            )
            await self._transition(owner_id, run_id, "indexing", "workspace_index", "已读取并冻结所选文件索引。", {
                "files": files, "reason": selection_reason,
            })
            await self._transition(owner_id, run_id, "planning", "planning_started", "正在根据文件索引生成工作计划。", {})
            started = perf_counter()
            try:
                candidate = await self.planner.plan(
                    scenario=self._planner_workspace(workspace, instruction),
                    files=self._planner_files(files),
                )
                plan = self._compile_plan(candidate)
            except HarnessModelError as exc:
                elapsed = exc.elapsed_ms or max(0, round((perf_counter() - started) * 1000))
                receipt = HarnessModelReceipt(
                    called=exc.called,
                    model=exc.model,
                    elapsed_ms=elapsed,
                    output_used=False,
                )
                await self._set_model_receipt(owner_id, run_id, receipt)
                await self._transition(
                    owner_id,
                    run_id,
                    "planning",
                    "planning_completed",
                    "模型返回的计划未通过结构校验，未采用模型输出。",
                    {
                        "model": receipt.model,
                        "elapsed_ms": receipt.elapsed_ms,
                        "model_called": receipt.called,
                        "output_used": False,
                    },
                )
                raise
            except Exception:
                elapsed = max(0, round((perf_counter() - started) * 1000))
                receipt = HarnessModelReceipt(
                    called=False,
                    model=getattr(self.planner, "model", self.MODEL),
                    elapsed_ms=elapsed,
                    output_used=False,
                )
                await self._set_model_receipt(owner_id, run_id, receipt)
                await self._transition(
                    owner_id,
                    run_id,
                    "planning",
                    "planning_completed",
                    "规划器未返回可用计划，未采用模型输出。",
                    {
                        "model": receipt.model,
                        "elapsed_ms": receipt.elapsed_ms,
                        "model_called": receipt.called,
                        "output_used": False,
                    },
                )
                raise
            elapsed = max(0, round((perf_counter() - started) * 1000))
            receipt = HarnessModelReceipt(called=True, model=getattr(self.planner, "model", self.MODEL), elapsed_ms=elapsed, output_used=False)
            await self._set_model_receipt(owner_id, run_id, receipt)
            await self._transition(owner_id, run_id, "planning", "planning_completed", "模型计划已返回，等待服务端校验。", {
                "model": receipt.model,
                "elapsed_ms": receipt.elapsed_ms,
                "model_called": receipt.called,
                "output_used": False,
            })
            self._validate_plan(plan, workspace, files)
            await self._set_plan(owner_id, run_id, plan)
            await self._set_model_receipt(owner_id, run_id, receipt.model_copy(update={"output_used": True}))
            await self._transition(owner_id, run_id, "validating", "plan_validation", "计划通过路径、工具、依赖与人工确认校验。", {
                "unit_count": len(plan.units),
                "execution_started": False,
                "model_called": receipt.called,
                "output_used": True,
            })
            if self.analyst is None:
                await self._transition(owner_id, run_id, "ready_to_execute", "ready_to_execute", "计划已就绪，等待用户确认后才可进入执行。", {
                    "execution_started": False,
                    "model_called": receipt.called,
                    "output_used": True,
                })
                return

            await self._transition(
                owner_id,
                run_id,
                "analyzing",
                "analysis_started",
                "正在读取所选公开文件并执行只读分析。",
                {
                    "file_count": len(files),
                    "external_action": False,
                },
            )
            analysis_inputs = self._analysis_inputs(files)
            analysis_started = perf_counter()
            try:
                result = await self.analyst.analyze(
                    instruction=instruction,
                    plan=plan,
                    files=analysis_inputs,
                )
            except HarnessModelError as exc:
                elapsed = exc.elapsed_ms or max(
                    0, round((perf_counter() - analysis_started) * 1000)
                )
                analysis_receipt = HarnessModelReceipt(
                    called=exc.called,
                    model=exc.model,
                    elapsed_ms=elapsed,
                    output_used=False,
                )
                await self._set_analysis_receipt(
                    owner_id, run_id, analysis_receipt
                )
                await self._transition(
                    owner_id,
                    run_id,
                    "analyzing",
                    "analysis_completed",
                    "模型返回的分析结果未通过结构校验，未采用模型输出。",
                    {
                        "model": analysis_receipt.model,
                        "elapsed_ms": analysis_receipt.elapsed_ms,
                        "model_called": analysis_receipt.called,
                        "output_used": False,
                    },
                )
                raise
            elapsed = max(
                0, round((perf_counter() - analysis_started) * 1000)
            )
            analysis_receipt = HarnessModelReceipt(
                called=True,
                model=getattr(self.analyst, "model", self.MODEL),
                elapsed_ms=elapsed,
                output_used=False,
            )
            await self._set_analysis_receipt(owner_id, run_id, analysis_receipt)
            await self._transition(
                owner_id,
                run_id,
                "analyzing",
                "analysis_completed",
                "只读分析结果已返回，等待服务端核对文件引用。",
                {
                    "model": analysis_receipt.model,
                    "elapsed_ms": analysis_receipt.elapsed_ms,
                    "model_called": True,
                    "output_used": False,
                },
            )
            self._validate_result(result, files)
            await self._set_result(owner_id, run_id, result)
            await self._set_analysis_receipt(
                owner_id,
                run_id,
                analysis_receipt.model_copy(update={"output_used": True}),
            )
            await self._transition(
                owner_id,
                run_id,
                "verifying",
                "result_validation",
                "结果已通过所选文件引用与只读边界校验。",
                {
                    "finding_count": len(result.findings),
                    "external_action": False,
                    "output_used": True,
                },
            )
            await self._transition(
                owner_id,
                run_id,
                "completed",
                "task_completed",
                "本轮只读分析已完成，结果等待用户复核。",
                {
                    "finding_count": len(result.findings),
                    "review_required": True,
                    "external_action": False,
                },
            )
        except Exception as exc:
            runtime_logger.warning("harness_run_failed run_id=%s error=%s", run_id, type(exc).__name__)
            await self._fail(owner_id, run_id, str(exc)[:500])

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
    def _planner_workspace(
        workspace: dict[str, Any], instruction: str
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
        }

    @staticmethod
    def _planner_files(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "file_ref": item["file_ref"],
                "display_label": item.get("display_label", "公开办公输入文件"),
                "display_group": item.get("display_group", "公开办公输入"),
                "display_summary": item.get("display_summary", "公开办公输入文件"),
                "mime": item.get("mime", "application/octet-stream"),
            }
            for item in files
        ]

    @staticmethod
    def _index_files(
        workspace: dict[str, Any], selected_file_refs: list[str]
    ) -> list[dict[str, Any]]:
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
                            "display_summary",
                        )
                        if key in item
                    },
                }
            )
        if not available:
            raise HarnessPlanError("办公资料库没有可用输入文件")
        selected_by_ref = {item["file_ref"]: item for item in available}
        unknown = set(selected_file_refs) - set(selected_by_ref)
        if unknown:
            raise HarnessPlanError("所选文件不属于当前办公资料库")
        return [selected_by_ref[file_ref] for file_ref in selected_file_refs]

    @staticmethod
    def _validate_result(
        result: HarnessTaskResult, files: list[dict[str, Any]]
    ) -> None:
        allowed_refs = {str(item["file_ref"]) for item in files}
        for finding in result.findings:
            if not set(finding.file_refs).issubset(allowed_refs):
                raise HarnessPlanError("分析结果引用了未选择的文件")

    @staticmethod
    def _compile_plan(candidate: HarnessPlanCandidate | HarnessPlan) -> HarnessPlan:
        """Compile model intent into server-owned effect and gate policy."""

        units: list[HarnessPlanUnit] = []
        for index, candidate_unit in enumerate(candidate.units, start=1):
            payload = candidate_unit.model_dump(exclude={"side_effect"})
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
        return HarnessPlan(summary=candidate.summary, units=units)

    @classmethod
    def _validate_plan(cls, plan: HarnessPlan, workspace: dict[str, Any], files: list[dict[str, Any]]) -> None:
        allowed_refs = {str(item["file_ref"]) for item in files}
        allowed_tools = set(workspace.get("allowlisted_tools", []))
        allowed_effects = set(workspace.get("allowed_side_effects", ["none", "run_workspace_write"]))
        if not allowed_tools:
            raise HarnessPlanError("办公资料库没有工具 allowlist")
        ids = [unit.unit_id for unit in plan.units]
        if len(ids) != len(set(ids)):
            raise HarnessPlanError("工作单元 ID 重复")
        graph: dict[str, list[str]] = {unit.unit_id: list(unit.depends_on) for unit in plan.units}
        for unit in plan.units:
            unknown_refs = set(unit.input_file_refs) - allowed_refs
            if unknown_refs:
                raise HarnessPlanError("计划引用了未选择的公开文件")
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
                }
            )
            condition = run.condition
        async with condition:
            condition.notify_all()

    async def _set_model_receipt(self, owner_id: str, run_id: str, receipt: HarnessModelReceipt) -> None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            run.snapshot = run.snapshot.model_copy(update={"model_receipt": receipt, "updated_at": datetime.now(timezone.utc)})

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

    async def _set_result(
        self, owner_id: str, run_id: str, result: HarnessTaskResult
    ) -> None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            run.snapshot = run.snapshot.model_copy(
                update={"result": result, "updated_at": datetime.now(timezone.utc)}
            )

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

    async def _set_plan(self, owner_id: str, run_id: str, plan: HarnessPlan) -> None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            run.snapshot = run.snapshot.model_copy(update={"plan": plan, "updated_at": datetime.now(timezone.utc)})

    async def _fail(self, owner_id: str, run_id: str, reason: str) -> None:
        async with self._lock:
            run = self._require_run(owner_id, run_id)
            run.snapshot = run.snapshot.model_copy(
                update={"validation_errors": [reason], "updated_at": datetime.now(timezone.utc)}
            )
            receipt = run.snapshot.model_receipt
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
    )
