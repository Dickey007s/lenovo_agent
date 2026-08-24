from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Protocol
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError

from packages.contracts import (
    Demo2ExecutionSnapshot,
    Demo2ExecutionStartRequest,
    Demo2ExecutionStartResult,
    Demo2WorkerSpec,
    ExecutionReceipt,
    SharedArtifactVersion,
    SwarmEvent,
    TaskSourceDocument,
    WorkerProcessing,
)
from packages.contracts.hashing import canonical_hash
from services.api.app.application.demo2_cockpit import (
    Demo2CockpitService,
    Demo2NotFoundError,
)
from services.api.app.application.demo_source_catalog import (
    DEMO1_FORECAST_REVENUE_SOURCE,
    DEMO1_MAIL_SOURCE,
    DEMO1_OFFICIAL_REVENUE_SOURCE,
    DEMO1_PROJECT_SOURCE,
    Demo1SourcePackage,
    DemoSourceCatalog,
    DemoSourceError,
)


runtime_logger = logging.getLogger("uvicorn.error")


class Demo2ExecutionError(RuntimeError):
    pass


class Demo2ExecutionConflictError(Demo2ExecutionError):
    pass


class Demo2ExecutionNotFoundError(Demo2ExecutionError):
    pass


class Demo2ExecutionSourceError(Demo2ExecutionError):
    pass


class Demo2WorkerFactMismatchError(ValueError):
    pass


class Demo2WorkerDraft(BaseModel):
    """Only business text may come from a worker adapter."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=600)
    key_points: list[str] = Field(min_length=1, max_length=8)
    _origin: str = PrivateAttr(default="deterministic")
    _model_called: bool = PrivateAttr(default=False)
    _fallback_reason: str | None = PrivateAttr(default=None)

    @property
    def origin(self) -> str:
        return self._origin

    @property
    def model_called(self) -> bool:
        return self._model_called

    @property
    def fallback_reason(self) -> str | None:
        return self._fallback_reason

    def mark_processing(
        self,
        *,
        origin: str,
        model_called: bool,
        fallback_reason: str | None = None,
    ) -> Demo2WorkerDraft:
        self._origin = origin
        self._model_called = model_called
        self._fallback_reason = fallback_reason
        return self


class Demo2WorkerAgent(Protocol):
    async def run(
        self, spec: Demo2WorkerSpec, sources: list[TaskSourceDocument]
    ) -> Demo2WorkerDraft: ...


class DeterministicDemo2WorkerAgent:
    """Safe fallback used by tests and when the model is not configured."""

    async def run(
        self, spec: Demo2WorkerSpec, sources: list[TaskSourceDocument]
    ) -> Demo2WorkerDraft:
        facts = {fact.field: fact.display_value for doc in sources for fact in doc.facts}
        if spec.role == "revenue_analyst":
            return Demo2WorkerDraft(
                summary="财务月结与销售预测存在口径差异，需要把预测与已实现收入分开呈现。",
                key_points=[
                    f"已实现收入：{facts.get('recognized_revenue', '待核对')}",
                    f"销售预测：{facts.get('forecast_revenue', '待核对')}",
                ],
            )
        if spec.role == "project_risk_analyst":
            return Demo2WorkerDraft(
                summary="项目周报显示当前交付存在延期风险，建议在汇报中单独呈现。",
                key_points=[
                    f"里程碑偏差：{facts.get('milestone_variance_days', '待核对')}",
                    facts.get("risk_summary", "风险事实待核对"),
                ],
            )
        if spec.role == "request_context_analyst":
            return Demo2WorkerDraft(
                summary="客户请求要求以财务关账口径汇报，并在内部核对完成前只保留回复草稿。",
                key_points=[
                    facts.get("revenue_instruction", "收入口径待核对"),
                    "客户回复在内部核对完成前保持为草稿。",
                ],
            )
        return Demo2WorkerDraft(
            summary="已完成收入口径核验，汇报可同时保留关账事实与预测展望。",
            key_points=[
                f"正式口径：{facts.get('recognized_revenue', '待核对')}",
                f"展望口径：{facts.get('forecast_revenue', '待核对')}",
                "未触发任何外部动作。",
            ],
        )


class DeepSeekDemo2WorkerAgent:
    """OpenAI-compatible worker adapter locked to the configured DeepSeek model.

    The adapter receives server-owned facts and returns business text only. The
    execution service still owns worker identity, source bindings and status.
    """

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
            raise ValueError(f"Demo 2 只允许使用 {self.MODEL}")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.fallback = DeterministicDemo2WorkerAgent()

    async def run(
        self, spec: Demo2WorkerSpec, sources: list[TaskSourceDocument]
    ) -> Demo2WorkerDraft:
        approved = await self.fallback.run(spec, sources)
        if not self.base_url or not self.api_key:
            return approved.mark_processing(
                origin="template_fallback",
                model_called=False,
                fallback_reason="configuration_missing",
            )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是企业经营汇报中的受限资料分析 Worker。只能根据服务端资料生成业务摘要。"
                        "只能输出 JSON，字段必须是 summary 和 key_points；不要生成来源 ID、状态、任务 ID、"
                        "风险等级、动作、外部写入或任何内部推理。不能改写数字口径。"
                        "输出必须逐字段等于 approved_business_text，否则服务端会拒绝并使用安全模板。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "worker_role": spec.role,
                            "objective": spec.objective,
                            "approved_business_text": approved.model_dump(),
                            "facts": [
                                {
                                    "field": fact.field,
                                    "label": fact.label,
                                    "display_value": fact.display_value,
                                }
                                for source in sources
                                for fact in source.facts
                            ],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "max_tokens": 900,
            "thinking": {"type": "disabled"},
        }
        model_called = False
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                model_called = True
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if response.status_code == 400 and "response_format" in response.text.lower():
                    payload.pop("response_format", None)
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                    )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                if not isinstance(content, str):
                    raise ValueError("model content is not text")
                candidate = Demo2WorkerDraft.model_validate(
                    json.loads(content.strip().strip("`"))
                )
                if candidate.model_dump() != approved.model_dump():
                    raise Demo2WorkerFactMismatchError(
                        "model business text changed approved file-backed facts"
                    )
                return candidate.mark_processing(origin="model", model_called=True)
        except (
            httpx.HTTPError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            runtime_logger.warning(
                "demo2_worker_model_fallback model=%s worker_role=%s",
                self.model,
                spec.role,
            )
            return approved.mark_processing(
                origin="template_fallback",
                model_called=model_called,
                fallback_reason=type(exc).__name__,
            )


@dataclass(frozen=True)
class _IdempotentStart:
    command_digest: str
    result: Demo2ExecutionStartResult


class Demo2ExecutionService:
    """Controlled, file-backed Demo 2 execution slice.

    Runtime state is intentionally memory-backed. A browser disconnect does not
    stop the background task, while process restart discards it.
    """

    backend = "memory"
    MAX_WORKER_RUNS = 4

    def __init__(
        self,
        cockpit_service: Demo2CockpitService,
        *,
        source_catalog: DemoSourceCatalog | None = None,
        worker_agent: Demo2WorkerAgent | None = None,
    ) -> None:
        self.cockpit_service = cockpit_service
        self.source_catalog = source_catalog or DemoSourceCatalog()
        self.worker_agent = worker_agent or DeterministicDemo2WorkerAgent()
        self._executions: dict[tuple[str, str], Demo2ExecutionSnapshot] = {}
        self._source_snapshots: dict[tuple[str, str], tuple[TaskSourceDocument, ...]] = {}
        self._idempotent: dict[tuple[str, str, str], _IdempotentStart] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._conditions: dict[str, asyncio.Condition] = {}
        self._lock = asyncio.Lock()

    async def setup(self) -> None:
        return None

    async def start_execution(
        self,
        work_item_id: str,
        owner_id: str,
        request: Demo2ExecutionStartRequest,
    ) -> Demo2ExecutionStartResult:
        command_digest = canonical_hash(
            {
                "operation": "demo2_execution_start",
                "work_item_id": work_item_id,
                "expected_version": request.expected_version,
                "max_workers": request.max_workers,
            }
        )
        key = (owner_id, work_item_id, request.idempotency_key)
        async with self._lock:
            replay = self._idempotent.get(key)
            if replay is not None:
                if replay.command_digest != command_digest:
                    raise Demo2ExecutionConflictError("幂等键已用于不同执行命令")
                return replay.result.model_copy(update={"replayed": True}, deep=True)
            item = await self.cockpit_service.get_work_item(work_item_id, owner_id)
            if item.version != request.expected_version:
                raise Demo2ExecutionConflictError(
                    f"工作项版本冲突：期望 {request.expected_version}，当前为 {item.version}"
                )
            if item.selected_mode != "adaptive_swarm":
                raise Demo2ExecutionConflictError("只有确认自适应协作群组后才能启动执行")
            if request.max_workers != 3:
                raise Demo2ExecutionConflictError("当前固定演示纵切只允许 3 个并行工作单元")
            existing = self._executions.get((owner_id, work_item_id))
            if existing is not None:
                raise Demo2ExecutionConflictError("本次工作已经启动执行，不能重复创建")
            try:
                package = self.source_catalog.load_demo1()
            except DemoSourceError as exc:
                raise Demo2ExecutionSourceError(str(exc)) from exc
            execution_id = f"demo2-exec:{uuid4().hex}"
            workers = self._initial_workers(work_item_id, package)
            snapshot = Demo2ExecutionSnapshot(
                execution_id=execution_id,
                owner_id=owner_id,
                work_item_id=work_item_id,
                status="queued",
                version=1,
                last_event_sequence=0,
                source_document_ids=[doc.document_id for doc in package.documents],
                worker_runs=workers,
                budget_max_workers=request.max_workers,
                budget_max_worker_runs=self.MAX_WORKER_RUNS,
            )
            self._executions[(owner_id, work_item_id)] = snapshot
            self._source_snapshots[(owner_id, work_item_id)] = package.documents
            self._conditions[execution_id] = asyncio.Condition()

        projected_item = await self.cockpit_service.update_execution_state(
            work_item_id=work_item_id,
            owner_id=owner_id,
            execution_id=execution_id,
            status="queued",
            event_type="EXECUTION_QUEUED",
        )
        await self._append_event(
            owner_id,
            work_item_id,
            event_type="EXECUTION_QUEUED",
            status="queued",
            message="执行已排队，服务端将按受限工作单元推进。",
            details={"worker_count": str(len(workers)), "external_action": "none"},
        )
        async with self._lock:
            snapshot = self._get_execution_unlocked(owner_id, work_item_id)
            result = Demo2ExecutionStartResult(item=projected_item, execution=snapshot)
            self._idempotent[key] = _IdempotentStart(command_digest, result)
            task = asyncio.create_task(self._run_execution(owner_id, work_item_id))
            self._tasks[execution_id] = task
            task.add_done_callback(lambda done: self._tasks.pop(execution_id, None))
        return result.model_copy(deep=True)

    async def get_execution(self, work_item_id: str, owner_id: str) -> Demo2ExecutionSnapshot:
        async with self._lock:
            try:
                return self._get_execution_unlocked(owner_id, work_item_id).model_copy(deep=True)
            except Demo2ExecutionNotFoundError:
                raise

    async def event_stream(
        self,
        work_item_id: str,
        owner_id: str,
        after: int = 0,
    ):
        sequence = after
        while True:
            async with self._lock:
                current = self._get_execution_unlocked(owner_id, work_item_id)
                events = [event for event in current.events if event.sequence > sequence]
                condition = self._conditions[current.execution_id]
                terminal_event = {
                    "completed": "EXECUTION_COMPLETED",
                    "failed": "EXECUTION_FAILED",
                    "cancelled": "EXECUTION_CANCELLED",
                }.get(current.status)
                terminal = bool(
                    terminal_event
                    and current.events
                    and current.events[-1].event_type == terminal_event
                )
            for event in events:
                sequence = event.sequence
                yield event
            if terminal:
                return
            async with condition:
                try:
                    await asyncio.wait_for(condition.wait(), timeout=15)
                except TimeoutError:
                    yield None

    async def _run_execution(self, owner_id: str, work_item_id: str) -> None:
        execution = await self.get_execution(work_item_id, owner_id)
        try:
            await self._transition(owner_id, work_item_id, "running", "EXECUTION_STARTED")
            package = self.source_catalog.require_unchanged(
                list(self._source_snapshots[(owner_id, work_item_id)])
            )
            # Initial three workers run concurrently; all source bindings are server-owned.
            initial = [worker for worker in execution.worker_runs if worker.trigger == "initial_plan"]
            await self._run_worker_group(owner_id, work_item_id, initial, package)
            if self._revenue_conflict(package):
                await self._append_event(
                    owner_id,
                    work_item_id,
                    event_type="DYNAMIC_REPLAN",
                    status="running",
                    message="文件事实发现收入口径冲突，动态增派口径核验工作单元。",
                    details={"reason": "recognized_revenue_vs_forecast_revenue"},
                )
                reconciliation = self._reconciliation_worker(work_item_id, package)
                async with self._lock:
                    current = self._get_execution_unlocked(owner_id, work_item_id)
                    self._replace_execution(
                        current.model_copy(update={"worker_runs": [*current.worker_runs, reconciliation]})
                    , owner_id, work_item_id)
                await self._append_event(
                    owner_id,
                    work_item_id,
                    event_type="WORKER_ADDED",
                    status="running",
                    worker_run_id=reconciliation.worker_run_id,
                    message="已增派收入口径核验工作单元，依赖前三项事实分析。",
                    details={"trigger": "dynamic_replan", "external_action": "none"},
                )
                await self._run_worker(owner_id, work_item_id, reconciliation, package)
            await self._transition(owner_id, work_item_id, "verifying", "EXECUTION_VERIFYING")
            await self._verify_and_complete(owner_id, work_item_id, package)
        except (DemoSourceError, Demo2ExecutionError, Demo2NotFoundError) as exc:
            runtime_logger.warning("demo2_execution_failed work_item_id=%s error=%s", work_item_id, exc)
            await self._fail_execution(owner_id, work_item_id, "source_or_runtime_error")
        except Exception:
            runtime_logger.exception("demo2_execution_unexpected_failure work_item_id=%s", work_item_id)
            await self._fail_execution(owner_id, work_item_id, "unexpected_runtime_error")

    async def _run_worker_group(
        self,
        owner_id: str,
        work_item_id: str,
        workers: list[Demo2WorkerSpec],
        package: Demo1SourcePackage,
    ) -> None:
        tasks = [
            asyncio.create_task(self._run_worker(owner_id, work_item_id, worker, package))
            for worker in workers
        ]
        try:
            await asyncio.gather(*tasks)
        except Exception:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

    async def _run_worker(
        self,
        owner_id: str,
        work_item_id: str,
        worker: Demo2WorkerSpec,
        package: Demo1SourcePackage,
    ) -> None:
        await self._set_worker_status(owner_id, work_item_id, worker.worker_run_id, "running")
        try:
            package = self.source_catalog.require_unchanged(
                list(self._source_snapshots[(owner_id, work_item_id)])
            )
            source_docs = [
                package.document(source_ref)
                for source_ref in self._source_refs_for_worker(worker, package)
            ]
            started_at = perf_counter()
            draft = await self.worker_agent.run(worker, source_docs)
            if not isinstance(draft, Demo2WorkerDraft):
                draft = Demo2WorkerDraft.model_validate(draft)
            artifact = self._artifact_for_worker(worker, draft, source_docs)
            processing = self._processing_for_draft(
                draft,
                elapsed_ms=max(0, round((perf_counter() - started_at) * 1000)),
            )
            await self._complete_worker(
                owner_id,
                work_item_id,
                worker.worker_run_id,
                artifact,
                processing,
            )
        except asyncio.CancelledError:
            if await self._worker_has_status(
                owner_id, work_item_id, worker.worker_run_id, "completed"
            ):
                return
            await self._set_worker_status(
                owner_id,
                work_item_id,
                worker.worker_run_id,
                "cancelled",
                error_code="cancelled_due_to_peer_failure",
            )
            raise
        except Exception as exc:
            await self._set_worker_status(
                owner_id,
                work_item_id,
                worker.worker_run_id,
                "failed",
                error_code=self._worker_error_code(exc),
            )
            raise

    async def _worker_has_status(
        self,
        owner_id: str,
        work_item_id: str,
        worker_run_id: str,
        status: str,
    ) -> bool:
        async with self._lock:
            execution = self._get_execution_unlocked(owner_id, work_item_id)
            return any(
                worker.worker_run_id == worker_run_id and worker.status == status
                for worker in execution.worker_runs
            )

    async def _complete_worker(
        self,
        owner_id: str,
        work_item_id: str,
        worker_run_id: str,
        artifact: SharedArtifactVersion,
        processing: WorkerProcessing,
    ) -> None:
        async with self._lock:
            execution = self._get_execution_unlocked(owner_id, work_item_id)
            if execution.status in {"failed", "cancelled"}:
                raise asyncio.CancelledError
            now = _now()
            workers: list[Demo2WorkerSpec] = []
            target: Demo2WorkerSpec | None = None
            for worker in execution.worker_runs:
                if worker.worker_run_id != worker_run_id:
                    workers.append(worker)
                    continue
                if worker.status != "running":
                    raise Demo2ExecutionConflictError(
                        "工作单元不在可提交工件的运行状态"
                    )
                target = worker.model_copy(
                    update={
                        "status": "completed",
                        "completed_at": now,
                        "artifact_version_id": artifact.artifact_version_id,
                        "processing": processing,
                        "error_code": None,
                    }
                )
                workers.append(target)
            if target is None:
                raise Demo2ExecutionNotFoundError(worker_run_id)
            event = SwarmEvent(
                execution_id=execution.execution_id,
                sequence=execution.last_event_sequence + 1,
                event_type="WORKER_COMPLETED",
                occurred_at=now,
                status="running",
                worker_run_id=worker_run_id,
                artifact_version_id=artifact.artifact_version_id,
                message="工作单元已产出共享工件版本。",
                details={"worker_status": "completed", "external_action": "none"},
            )
            self._replace_execution(
                execution.model_copy(
                    update={
                        "worker_runs": workers,
                        "artifacts": [*execution.artifacts, artifact],
                        "version": execution.version + 1,
                        "last_event_sequence": event.sequence,
                        "events": [*execution.events, event],
                    }
                ),
                owner_id,
                work_item_id,
            )
            condition = self._conditions[execution.execution_id]
        async with condition:
            condition.notify_all()

    async def _verify_and_complete(
        self, owner_id: str, work_item_id: str, package: Demo1SourcePackage
    ) -> None:
        self.source_catalog.require_unchanged(list(package.documents))
        async with self._lock:
            execution = self._get_execution_unlocked(owner_id, work_item_id)
            workers = list(execution.worker_runs)
            if any(worker.status != "completed" for worker in workers):
                raise Demo2ExecutionError("存在未完成的工作单元")
            artifacts = list(execution.artifacts)
            if len(artifacts) < 4:
                raise Demo2ExecutionError("共享工件包缺少受限工作单元结果")
            final_sources = [doc.document_id for doc in package.documents]
            recognized_revenue = self._display_fact(
                package, DEMO1_OFFICIAL_REVENUE_SOURCE, "recognized_revenue"
            )
            forecast_revenue = self._display_fact(
                package, DEMO1_FORECAST_REVENUE_SOURCE, "forecast_revenue"
            )
            risk_summary = self._display_fact(
                package, DEMO1_PROJECT_SOURCE, "risk_summary"
            )
            variance = self._display_fact(
                package, DEMO1_PROJECT_SOURCE, "milestone_variance_days"
            )
            revenue_instruction = self._display_fact(
                package, DEMO1_MAIL_SOURCE, "revenue_instruction"
            )
            final_content = {
                "revenue_basis": (
                    f"财务已关账收入 {recognized_revenue}；销售预测 {forecast_revenue}仅作为展望。"
                ),
                "project_risk": f"项目周报显示{risk_summary}；里程碑偏差 {variance}。",
                "request_constraint": f"客户请求要求{revenue_instruction}，回复保持草稿。",
                "worker_count": str(len(workers)),
                "external_action": "none",
            }
            final_artifact = self._final_artifact(final_sources, final_content, len(artifacts) + 1)
            artifacts.append(final_artifact)
            now = _now()
            receipt = ExecutionReceipt(
                receipt_id=f"demo2-receipt:{uuid4().hex}",
                execution_id=execution.execution_id,
                work_item_id=work_item_id,
                status="completed",
                worker_run_ids=[worker.worker_run_id for worker in workers],
                artifact_version_ids=[artifact.artifact_version_id for artifact in artifacts],
                final_artifact_version_id=final_artifact.artifact_version_id,
                started_at=execution.events[0].occurred_at if execution.events else now,
                completed_at=now,
                summary="已完成四个受限工作单元并生成共享汇报工件包，未触发外部动作。",
            )
            updated = execution.model_copy(
                update={
                    "status": "completed",
                    "version": execution.version + 1,
                    "artifacts": artifacts,
                    "receipt": receipt,
                }
            )
            self._replace_execution(updated, owner_id, work_item_id)
        await self._append_event(
            owner_id,
            work_item_id,
            event_type="ARTIFACT_VERIFIED",
            status="verifying",
            artifact_version_id=final_artifact.artifact_version_id,
            message="共享汇报工件包已通过服务端事实核验。",
            details={"artifact_count": str(len(artifacts)), "external_action": "none"},
        )
        await self._append_event(
            owner_id,
            work_item_id,
            event_type="EXECUTION_COMPLETED",
            status="completed",
            artifact_version_id=final_artifact.artifact_version_id,
            message="自适应协作群组已完成本次汇报准备，未调用外部连接器。",
            details={"receipt_id": receipt.receipt_id, "external_action": "none"},
        )
        await self.cockpit_service.update_execution_state(
            work_item_id=work_item_id,
            owner_id=owner_id,
            execution_id=execution.execution_id,
            status="completed",
            event_type="EXECUTION_COMPLETED",
        )

    async def _fail_execution(self, owner_id: str, work_item_id: str, error_code: str) -> None:
        try:
            async with self._lock:
                execution = self._get_execution_unlocked(owner_id, work_item_id)
                if execution.status in {"completed", "failed", "cancelled"}:
                    return
                updated = execution.model_copy(update={"status": "failed", "version": execution.version + 1})
                self._replace_execution(updated, owner_id, work_item_id)
            await self._append_event(
                owner_id,
                work_item_id,
                event_type="EXECUTION_FAILED",
                status="failed",
                message="执行因资料完整性或运行时错误停止，未生成可确认的完成回执。",
                details={"error_code": error_code, "external_action": "none"},
            )
            await self.cockpit_service.update_execution_state(
                work_item_id=work_item_id,
                owner_id=owner_id,
                execution_id=execution.execution_id,
                status="failed",
                event_type="EXECUTION_FAILED",
            )
        except Demo2ExecutionNotFoundError:
            return

    async def _transition(
        self, owner_id: str, work_item_id: str, status: str, event_type: str
    ) -> None:
        execution = await self.get_execution(work_item_id, owner_id)
        await self._append_event(
            owner_id,
            work_item_id,
            event_type=event_type,
            status=status,
            message={
                "running": "执行已启动，受限工作单元正在读取演示资料。",
                "verifying": "工作单元结果已形成，服务端正在核验共享工件包。",
            }.get(status, "执行状态已更新。"),
            details={"external_action": "none"},
        )
        async with self._lock:
            current = self._get_execution_unlocked(owner_id, work_item_id)
            self._replace_execution(
                current.model_copy(update={"status": status, "version": current.version + 1}),
                owner_id,
                work_item_id,
            )
        await self.cockpit_service.update_execution_state(
            work_item_id=work_item_id,
            owner_id=owner_id,
            execution_id=execution.execution_id,
            status=status,
            event_type=event_type,
        )

    async def _set_worker_status(
        self,
        owner_id: str,
        work_item_id: str,
        worker_run_id: str,
        status: str,
        *,
        artifact_version_id: str | None = None,
        processing: WorkerProcessing | None = None,
        error_code: str | None = None,
    ) -> None:
        async with self._lock:
            execution = self._get_execution_unlocked(owner_id, work_item_id)
            if execution.status in {"failed", "cancelled"}:
                return
            now = _now()
            workers = []
            target: Demo2WorkerSpec | None = None
            for worker in execution.worker_runs:
                if worker.worker_run_id != worker_run_id:
                    workers.append(worker)
                    continue
                target = worker.model_copy(
                    update={
                        "status": status,
                        "started_at": (
                            worker.started_at or now
                            if status == "running"
                            else worker.started_at
                        ),
                        "completed_at": now if status in {"completed", "failed", "cancelled"} else worker.completed_at,
                        "artifact_version_id": artifact_version_id or worker.artifact_version_id,
                        "processing": processing or worker.processing,
                        "error_code": error_code,
                    }
                )
                workers.append(target)
            if target is None:
                raise Demo2ExecutionNotFoundError(worker_run_id)
            self._replace_execution(
                execution.model_copy(update={"worker_runs": workers, "version": execution.version + 1}),
                owner_id,
                work_item_id,
            )
        event_type = {
            "running": "WORKER_STARTED",
            "completed": "WORKER_COMPLETED",
            "failed": "WORKER_FAILED",
            "cancelled": "WORKER_CANCELLED",
        }[status]
        message = {
            "running": "工作单元已开始处理受限资料。",
            "completed": "工作单元已产出共享工件版本。",
            "failed": "工作单元处理失败，服务端已停止采用其结果。",
            "cancelled": "工作单元因同组失败被取消，未采用晚到结果。",
        }[status]
        details = {"worker_status": status, "external_action": "none"}
        if error_code is not None:
            details["error_code"] = error_code
        await self._append_event(
            owner_id,
            work_item_id,
            event_type=event_type,
            status="running",
            worker_run_id=worker_run_id,
            artifact_version_id=artifact_version_id,
            message=message,
            details=details,
        )

    async def _append_event(
        self,
        owner_id: str,
        work_item_id: str,
        *,
        event_type: str,
        status: str,
        message: str,
        worker_run_id: str | None = None,
        artifact_version_id: str | None = None,
        details: dict[str, str] | None = None,
    ) -> SwarmEvent:
        async with self._lock:
            execution = self._get_execution_unlocked(owner_id, work_item_id)
            event = SwarmEvent(
                execution_id=execution.execution_id,
                sequence=execution.last_event_sequence + 1,
                event_type=event_type,
                occurred_at=_now(),
                status=status,
                worker_run_id=worker_run_id,
                artifact_version_id=artifact_version_id,
                message=message,
                details=details or {},
            )
            self._replace_execution(
                execution.model_copy(
                    update={
                        "last_event_sequence": event.sequence,
                        "events": [*execution.events, event],
                    }
                ),
                owner_id,
                work_item_id,
            )
            condition = self._conditions[execution.execution_id]
        async with condition:
            condition.notify_all()
        return event

    def _get_execution_unlocked(self, owner_id: str, work_item_id: str) -> Demo2ExecutionSnapshot:
        execution = self._executions.get((owner_id, work_item_id))
        if execution is None:
            raise Demo2ExecutionNotFoundError("执行不存在")
        return execution

    def _replace_execution(
        self, snapshot: Demo2ExecutionSnapshot, owner_id: str, work_item_id: str
    ) -> None:
        self._executions[(owner_id, work_item_id)] = snapshot

    @staticmethod
    def _initial_workers(work_item_id: str, package: Demo1SourcePackage) -> list[Demo2WorkerSpec]:
        doc = {item.semantic_type: item.document_id for item in package.documents}
        return [
            Demo2WorkerSpec(
                worker_run_id=f"worker:{work_item_id}:revenue",
                work_item_id=work_item_id,
                role="revenue_analyst",
                label="收入事实核对",
                objective="核对财务已实现收入与销售预测，保持两种口径分离。",
                source_document_ids=[doc["historical_actual"], doc["forecast"]],
            ),
            Demo2WorkerSpec(
                worker_run_id=f"worker:{work_item_id}:risk",
                work_item_id=work_item_id,
                role="project_risk_analyst",
                label="项目风险提取",
                objective="从项目周报提取延期风险和缓解安排。",
                source_document_ids=[doc["project_risk"]],
            ),
            Demo2WorkerSpec(
                worker_run_id=f"worker:{work_item_id}:request",
                work_item_id=work_item_id,
                role="request_context_analyst",
                label="客户要求核对",
                objective="核对客户对收入口径和回复草稿的明确约束。",
                source_document_ids=[doc["request_context"]],
            ),
        ]

    @staticmethod
    def _reconciliation_worker(work_item_id: str, package: Demo1SourcePackage) -> Demo2WorkerSpec:
        ids = [
            package.document(DEMO1_OFFICIAL_REVENUE_SOURCE).document_id,
            package.document(DEMO1_FORECAST_REVENUE_SOURCE).document_id,
            package.document(DEMO1_MAIL_SOURCE).document_id,
        ]
        return Demo2WorkerSpec(
            worker_run_id=f"worker:{work_item_id}:reconcile",
            work_item_id=work_item_id,
            role="reconciliation_analyst",
            label="收入口径核验",
            objective="依据冲突文件确认正式口径与预测展望的呈现边界。",
            depends_on=[
                f"worker:{work_item_id}:revenue",
                f"worker:{work_item_id}:risk",
                f"worker:{work_item_id}:request",
            ],
            source_document_ids=ids,
            trigger="dynamic_replan",
        )

    @staticmethod
    def _source_refs_for_worker(
        worker: Demo2WorkerSpec, package: Demo1SourcePackage
    ) -> list[str]:
        by_id = {doc.document_id: doc.source_ref for doc in package.documents}
        try:
            return [by_id[doc_id] for doc_id in worker.source_document_ids]
        except KeyError as exc:
            raise Demo2ExecutionSourceError("工作单元引用了未知演示资料") from exc

    @staticmethod
    def _revenue_conflict(package: Demo1SourcePackage) -> bool:
        actual = package.fact(DEMO1_OFFICIAL_REVENUE_SOURCE, "recognized_revenue")
        forecast = package.fact(DEMO1_FORECAST_REVENUE_SOURCE, "forecast_revenue")
        return actual != forecast

    @staticmethod
    def _display_fact(
        package: Demo1SourcePackage,
        source_ref: str,
        field: str,
    ) -> str:
        for fact in package.document(source_ref).facts:
            if fact.field == field:
                return fact.display_value
        raise Demo2ExecutionSourceError("共享工件缺少服务端已冻结事实")

    @staticmethod
    def _worker_error_code(exc: Exception) -> str:
        if isinstance(exc, DemoSourceError):
            return "source_integrity_error"
        if isinstance(exc, ValidationError):
            return "invalid_worker_output"
        if isinstance(exc, Demo2ExecutionError):
            return "worker_contract_error"
        return "worker_runtime_error"

    @staticmethod
    def _artifact_for_worker(
        worker: Demo2WorkerSpec,
        draft: Demo2WorkerDraft,
        sources: list[TaskSourceDocument],
    ) -> SharedArtifactVersion:
        content = {"summary": draft.summary, "key_points": " | ".join(draft.key_points)}
        digest = _digest(content)
        return SharedArtifactVersion(
            artifact_version_id=f"artifact-version:{uuid4().hex}",
            artifact_id=f"artifact:{worker.work_item_id}:{worker.role}",
            version=1,
            title=worker.label,
            kind="worker_finding",
            status="validated",
            produced_by_worker_run_id=worker.worker_run_id,
            source_document_ids=[source.document_id for source in sources],
            content=content,
            content_digest=digest,
            created_at=_now(),
        )

    @staticmethod
    def _processing_for_draft(
        draft: Demo2WorkerDraft, *, elapsed_ms: int
    ) -> WorkerProcessing:
        if draft.model_called:
            label = "模型 Worker" if draft.origin == "model" else "模型调用后使用安全回退"
            return WorkerProcessing(
                path="language_model",
                kind="language_model",
                label=label,
                model_called=True,
                model=DeepSeekDemo2WorkerAgent.MODEL,
                elapsed_ms=elapsed_ms,
                output_used="model" if draft.origin == "model" else "template_fallback",
                fallback_reason=draft.fallback_reason,
            )
        return WorkerProcessing(
            path="deterministic",
            kind="deterministic",
            label=(
                "确定性安全回退"
                if draft.origin == "template_fallback"
                else "确定性演示 Worker"
            ),
            model_called=False,
            model=None,
            elapsed_ms=elapsed_ms,
            output_used=(
                "template_fallback"
                if draft.origin == "template_fallback"
                else "deterministic"
            ),
            fallback_reason=draft.fallback_reason,
        )

    @staticmethod
    def _final_artifact(
        source_document_ids: list[str], content: dict[str, str], version: int
    ) -> SharedArtifactVersion:
        return SharedArtifactVersion(
            artifact_version_id=f"artifact-version:{uuid4().hex}",
            artifact_id="artifact:customer_a_operating_review:report",
            version=version,
            title="客户 A 经营汇报共享工件包",
            kind="verified_report_bundle",
            status="validated",
            source_document_ids=source_document_ids,
            content=content,
            content_digest=_digest(content),
            created_at=_now(),
        )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _digest(value: dict[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"
