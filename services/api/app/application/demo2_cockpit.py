from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from time import perf_counter

from packages.contracts import (
    AdmissionForecast,
    AdmissionReason,
    AdmissionRecommendation,
    RouteImpactChange,
    RouteImpactPreview,
    RouteProfile,
    RouteSelectionRequest,
    RouteSelectionProcessing,
    RouteSelectionReceipt,
    RouteSelectionResult,
    WorkCockpitSnapshot,
    WorkItemFacts,
    WorkItemSnapshot,
)
from packages.contracts.hashing import canonical_hash


runtime_logger = logging.getLogger("uvicorn.error")


class Demo2NotFoundError(LookupError):
    pass


class Demo2ConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class _IdempotentResult:
    command_digest: str
    result: RouteSelectionResult


class Demo2CockpitService:
    """Deterministic Demo 2 admission slice; it does not start execution."""

    backend = "memory"
    policy_version = "demo2-routing-v1"

    def __init__(self) -> None:
        self._cockpits: dict[str, WorkCockpitSnapshot] = {}
        self._idempotent: dict[tuple[str, str, str], _IdempotentResult] = {}
        self._lock = asyncio.Lock()

    async def setup(self) -> None:
        return None

    async def get_cockpit(self, owner_id: str) -> WorkCockpitSnapshot:
        async with self._lock:
            cockpit = self._cockpits.setdefault(owner_id, self._new_cockpit(owner_id))
            return cockpit.model_copy(deep=True)

    async def get_work_item(self, work_item_id: str, owner_id: str) -> WorkItemSnapshot:
        cockpit = await self.get_cockpit(owner_id)
        for item in cockpit.items:
            if item.work_item_id == work_item_id:
                return item
        raise Demo2NotFoundError(work_item_id)

    async def select_route(
        self,
        work_item_id: str,
        owner_id: str,
        request: RouteSelectionRequest,
    ) -> RouteSelectionResult:
        started_at = perf_counter()
        command_digest = canonical_hash(
            {
                "operation": "demo2_route_selection",
                "work_item_id": work_item_id,
                "mode": request.mode,
                "scope": request.scope,
                "expected_version": request.expected_version,
            }
        )
        key = (owner_id, work_item_id, request.idempotency_key)
        async with self._lock:
            replay = self._idempotent.get(key)
            if replay is not None:
                if replay.command_digest != command_digest:
                    raise Demo2ConflictError("幂等键已用于不同路由命令")
                runtime_logger.info(
                    "demo2_route_selection path=policy_engine model_called=false elapsed_ms=%d replay=true work_item_id=%s",
                    max(0, round((perf_counter() - started_at) * 1000)),
                    work_item_id,
                )
                return replay.result.model_copy(deep=True)

            cockpit = self._cockpits.setdefault(owner_id, self._new_cockpit(owner_id))
            index = next(
                (
                    index
                    for index, item in enumerate(cockpit.items)
                    if item.work_item_id == work_item_id
                ),
                None,
            )
            if index is None:
                raise Demo2NotFoundError(work_item_id)
            current = cockpit.items[index]
            if current.version != request.expected_version:
                raise Demo2ConflictError(
                    f"工作项版本冲突：期望 {request.expected_version}，当前为 {current.version}"
                )
            if len(current.allowed_modes) == 1:
                raise Demo2ConflictError("该工作项的执行方式由 Admission 固定，本轮无需重复选择")
            if request.mode not in current.allowed_modes:
                raise Demo2ConflictError("该工作项不支持所选执行方式")
            if current.selected_mode == request.mode:
                raise Demo2ConflictError("该工作项已记录为当前执行方式，无需重复确认")
            selection_source = (
                "admission"
                if request.mode == current.recommendation.mode
                else "user_override"
            )
            selected_profile = next(
                (
                    profile
                    for profile in current.route_profiles
                    if profile.mode == request.mode
                ),
                None,
            )
            if selected_profile is None:
                raise Demo2ConflictError("该执行方式缺少服务端路由事实")
            impact_preview = selected_profile.impact_preview
            if impact_preview is None:
                raise Demo2ConflictError("该执行方式缺少服务端影响预演，当前不能确认")
            next_cockpit_version = cockpit.version + 1
            next_item_version = current.version + 1
            receipt_seed = {
                "owner_id": owner_id,
                "work_item_id": work_item_id,
                "from_cockpit_version": cockpit.version,
                "to_cockpit_version": next_cockpit_version,
                "from_item_version": current.version,
                "to_item_version": next_item_version,
                "mode": request.mode,
                "selection_source": selection_source,
                "scope": request.scope,
            }
            previous_profile = next(
                (
                    profile
                    for profile in current.route_profiles
                    if profile.mode == current.selected_mode
                ),
                None,
            )
            receipt = RouteSelectionReceipt(
                receipt_id=f"route-receipt:{canonical_hash(receipt_seed)[7:31]}",
                from_cockpit_version=cockpit.version,
                to_cockpit_version=next_cockpit_version,
                from_item_version=current.version,
                to_item_version=next_item_version,
                selected_mode=request.mode,
                selection_source=selection_source,
                override_scope=request.scope if selection_source == "user_override" else None,
                forecast=selected_profile.forecast,
                changes=self._receipt_changes(
                    selected_profile,
                    previous_label=previous_profile.label if previous_profile else None,
                ),
                processing=RouteSelectionProcessing(
                    elapsed_ms=max(0, round((perf_counter() - started_at) * 1000)),
                ),
                summary=(
                    f"服务端已记录本次使用{selected_profile.label}；"
                    "执行仍未启动，也未创建实际协作单元或触发外部动作。"
                ),
            )

            updated = current.model_copy(
                update={
                    "admission_status": "route_selected",
                    "selected_mode": request.mode,
                    "selection_source": selection_source,
                    "override_scope": request.scope if selection_source == "user_override" else None,
                    "selection_receipt": receipt,
                    "selection_receipts": [*current.selection_receipts, receipt],
                    "version": next_item_version,
                    "last_event_sequence": current.last_event_sequence + 1,
                    "last_event_type": "ROUTE_SELECTED",
                }
            )
            items = list(cockpit.items)
            items[index] = updated
            updated_cockpit = cockpit.model_copy(
                update={
                    "version": next_cockpit_version,
                    "last_event_sequence": cockpit.last_event_sequence + 1,
                    "items": items,
                }
            )
            self._cockpits[owner_id] = updated_cockpit
            result = RouteSelectionResult(
                cockpit_version=updated_cockpit.version,
                cockpit_last_event_sequence=updated_cockpit.last_event_sequence,
                item=updated,
            )
            self._idempotent[key] = _IdempotentResult(command_digest, result)
            runtime_logger.info(
                "demo2_route_selection path=policy_engine model_called=false elapsed_ms=%d replay=false work_item_id=%s",
                max(0, round((perf_counter() - started_at) * 1000)),
                work_item_id,
            )
            return result.model_copy(deep=True)

    @classmethod
    def _new_cockpit(cls, owner_id: str) -> WorkCockpitSnapshot:
        return WorkCockpitSnapshot(
            owner_id=owner_id,
            backend=cls.backend,
            version=1,
            last_event_sequence=4,
            items=[
                cls._item_customer_a(owner_id),
                cls._item_supplier_reply(owner_id),
                cls._item_weekly_report(owner_id),
                cls._item_expense_anomaly(owner_id),
            ],
        )

    @classmethod
    def _item_customer_a(cls, owner_id: str) -> WorkItemSnapshot:
        recommendation = AdmissionRecommendation(
            mode="adaptive_swarm",
            summary="高价值、多来源且可并行，建议进入受限协作评估。",
            reasons=[
                AdmissionReason(factor="value", label="业务价值", detail="该汇报影响客户经营会，业务影响较高。"),
                AdmissionReason(factor="breadth", label="资料广度", detail="需要汇总邮件、CRM、项目周报和日历四类资料。"),
                AdmissionReason(factor="parallelism", label="并行空间", detail="客户事实、项目风险和依赖整理可拆成三个工作包。"),
                AdmissionReason(factor="deadline", label="截止压力", detail="今日截止，串行执行的等待成本较高。"),
                AdmissionReason(factor="budget", label="预算边界", detail="当前预算允许设置上限后进行受限并行。"),
            ],
            forecast=AdmissionForecast(estimated_tool_calls=30, estimated_runtime_seconds=900, max_workers=3),
            policy_version=cls.policy_version,
        )
        return WorkItemSnapshot(
            work_item_id="customer_a_operating_review",
            owner_id=owner_id,
            title="客户 A 经营汇报",
            objective="汇总经营事实、项目风险并形成可核对的汇报包。",
            business_status="attention",
            priority=94,
            facts=WorkItemFacts(
                value_band="high",
                breadth=4,
                parallelism=3,
                deadline_pressure="high",
                risk_band="medium",
                budget_band="approved",
                source_labels=["邮件", "CRM", "项目周报", "日历"],
            ),
            allowed_modes=["single_agent", "fixed_workflow", "adaptive_swarm"],
            route_profiles=cls._customer_route_profiles(recommendation),
            recommendation=recommendation,
        )

    @classmethod
    def _customer_route_profiles(cls, recommendation: AdmissionRecommendation) -> list[RouteProfile]:
        return [
            RouteProfile(
                mode="adaptive_swarm",
                label="自适应协作群组",
                summary="按工作包受限并行，适合高广度复杂任务。",
                forecast=recommendation.forecast,
                tradeoff="覆盖速度更好，但需要协调多个工作包；本轮仅记录路由，不会启动实际并行执行。",
                candidate_only=True,
                impact_preview=cls._route_impact_preview(
                    "adaptive_swarm",
                    recommendation.forecast,
                ),
            ),
            RouteProfile(
                mode="single_agent",
                label="单 Agent",
                summary="由一个 Agent 串行完成计划与草稿。",
                forecast=AdmissionForecast(estimated_tool_calls=12, estimated_runtime_seconds=600, max_workers=1),
                tradeoff="协调成本更低，但复杂资料的完成时间和覆盖度可能下降。",
                impact_preview=cls._route_impact_preview(
                    "single_agent",
                    AdmissionForecast(estimated_tool_calls=12, estimated_runtime_seconds=600, max_workers=1),
                ),
            ),
            RouteProfile(
                mode="fixed_workflow",
                label="固定流程",
                summary="按预设步骤执行，结果更可预测。",
                forecast=AdmissionForecast(estimated_tool_calls=15, estimated_runtime_seconds=720, max_workers=1),
                tradeoff="稳定性较好，但对临时分支和新问题的适应性较弱。",
                impact_preview=cls._route_impact_preview(
                    "fixed_workflow",
                    AdmissionForecast(estimated_tool_calls=15, estimated_runtime_seconds=720, max_workers=1),
                ),
            ),
        ]

    @classmethod
    def _route_impact_preview(
        cls,
        mode: str,
        forecast: AdmissionForecast,
    ) -> RouteImpactPreview:
        shapes = {
            "adaptive_swarm": (
                "三个受限工作包可并行准备，最终仍需统一汇总核对。",
                "允许受限并行与工作包协调，不创建实际协作单元。",
                "关键节点需要用户确认，最终结果仍需复核。",
            ),
            "single_agent": (
                "一个 Agent 串行处理全部资料和草稿。",
                "不拆分协作单元，资料按顺序进入同一上下文。",
                "在结果形成后由用户统一确认。",
            ),
            "fixed_workflow": (
                "一个固定步骤序列处理资料、核对和汇总。",
                "按预设检查点推进，不根据新问题动态拆分。",
                "在固定检查点和最终结果处由用户复核。",
            ),
            "tool_call": (
                "一个受限工具读取当前异常所需的最小证据。",
                "只处理当前核查点，不创建额外协作单元。",
                "证据不足时停下并由用户补充或确认。",
            ),
        }
        allocation, coordination, human_control = shapes[mode]
        forecast_text = (
            f"约 {round(forecast.estimated_runtime_seconds / 60)} 分钟、"
            f"最多 {forecast.estimated_tool_calls} 次工具调用、"
            f"并行上限 {forecast.max_workers} 个单元。"
        )
        return RouteImpactPreview(
            summary="选择前先查看工作如何组织、在哪里等待，以及哪些动作不会发生。",
            changes=[
                RouteImpactChange(
                    change_kind="change",
                    aspect="work_allocation",
                    label="任务怎么分配",
                    before="本次工作组织方式尚未确定",
                    after=allocation,
                ),
                RouteImpactChange(
                    change_kind="change",
                    aspect="coordination",
                    label="并行与等待",
                    before="尚未记录本次协调方式",
                    after=coordination,
                ),
                RouteImpactChange(
                    change_kind="change",
                    aspect="human_control",
                    label="什么时候需要你",
                    before="确认节点尚未记录",
                    after=human_control,
                ),
                RouteImpactChange(
                    change_kind="change",
                    aspect="policy_forecast",
                    label="演示策略预测",
                    before="尚未绑定本次执行方式",
                    after=forecast_text,
                    detail="固定规则预测，不是实测耗时、账单、节省比例或生产 SLA。",
                ),
                RouteImpactChange(
                    change_kind="preserve",
                    aspect="execution_boundary",
                    label="执行状态",
                    before="尚未启动",
                    after="选择后仍未启动，只记录本次路由。",
                ),
                RouteImpactChange(
                    change_kind="no_external_action",
                    aspect="external_action",
                    label="不会发生",
                    before="未触发外部动作",
                    after="不会发送邮件、写入 CRM，也不会创建实际协作单元或访问真实业务系统。",
                ),
            ],
        )

    @classmethod
    def _receipt_changes(
        cls,
        profile: RouteProfile,
        *,
        previous_label: str | None,
    ) -> list[RouteImpactChange]:
        preview = profile.impact_preview
        if preview is None:
            return []
        route_change = RouteImpactChange(
            change_kind="change",
            aspect="route_decision",
            label="本次执行方式",
            before=f"已记录为{previous_label}" if previous_label else "等待选择",
            after=f"已记录为{profile.label}",
            detail="这里只记录路由决定，不代表执行已经开始。",
        )
        return [route_change, *preview.changes]

    @classmethod
    def _item_supplier_reply(cls, owner_id: str) -> WorkItemSnapshot:
        return cls._fixed_item(
            owner_id,
            "supplier_reply",
            "供应商邮件回复",
            "基于已知上下文生成一版待审邮件草稿。",
            "ready",
            82,
            WorkItemFacts(
                value_band="medium",
                breadth=1,
                parallelism=1,
                deadline_pressure="medium",
                risk_band="medium",
                budget_band="tight",
                source_labels=["邮件"],
            ),
            AdmissionRecommendation(
                mode="single_agent",
                summary="上下文集中，单 Agent 生成草稿即可。",
                reasons=[
                    AdmissionReason(factor="breadth", label="资料广度", detail="主要依赖单一邮件线程。"),
                    AdmissionReason(factor="parallelism", label="并行空间", detail="没有足够独立工作包支撑协作。"),
                    AdmissionReason(factor="budget", label="预算边界", detail="单 Agent 可以减少不必要的协调开销。"),
                ],
                forecast=AdmissionForecast(estimated_tool_calls=4, estimated_runtime_seconds=120, max_workers=1),
                policy_version=cls.policy_version,
            ),
        )

    @classmethod
    def _item_weekly_report(cls, owner_id: str) -> WorkItemSnapshot:
        return cls._fixed_item(
            owner_id,
            "weekly_report",
            "周报格式统一",
            "按固定模板整理本周进展并输出标准格式。",
            "ready",
            74,
            WorkItemFacts(
                value_band="medium",
                breadth=2,
                parallelism=1,
                deadline_pressure="medium",
                risk_band="low",
                budget_band="tight",
                source_labels=["项目周报", "文档模板"],
            ),
            AdmissionRecommendation(
                mode="fixed_workflow",
                summary="规则稳定、重复性高，固定流程更可预测。",
                reasons=[
                    AdmissionReason(factor="breadth", label="资料广度", detail="输入范围有限且字段结构稳定。"),
                    AdmissionReason(factor="risk", label="风险边界", detail="格式整理风险低，不需要动态协作。"),
                    AdmissionReason(factor="budget", label="预算边界", detail="固定流程的成本和时延更可控。"),
                ],
                forecast=AdmissionForecast(estimated_tool_calls=6, estimated_runtime_seconds=180, max_workers=1),
                policy_version=cls.policy_version,
            ),
        )

    @classmethod
    def _item_expense_anomaly(cls, owner_id: str) -> WorkItemSnapshot:
        return cls._fixed_item(
            owner_id,
            "expense_anomaly",
            "报销异常核查",
            "先读取异常记录并定位需要补充的证据。",
            "waiting",
            69,
            WorkItemFacts(
                value_band="low",
                breadth=2,
                parallelism=1,
                deadline_pressure="low",
                risk_band="high",
                budget_band="tight",
                source_labels=["报销记录"],
            ),
            AdmissionRecommendation(
                mode="tool_call",
                summary="先查证据，不应在证据不足时扩大执行范围。",
                reasons=[
                    AdmissionReason(factor="risk", label="风险边界", detail="涉及报销凭据，先以受限读取核查为主。"),
                    AdmissionReason(factor="parallelism", label="并行空间", detail="当前只有一个待核查异常。"),
                    AdmissionReason(factor="budget", label="预算边界", detail="单次工具读取足够，不需要 Agent 协调。"),
                ],
                forecast=AdmissionForecast(estimated_tool_calls=2, estimated_runtime_seconds=60, max_workers=1),
                policy_version=cls.policy_version,
            ),
        )

    @staticmethod
    def _fixed_item(
        owner_id: str,
        work_item_id: str,
        title: str,
        objective: str,
        business_status: str,
        priority: int,
        facts: WorkItemFacts,
        recommendation: AdmissionRecommendation,
    ) -> WorkItemSnapshot:
        return WorkItemSnapshot(
            work_item_id=work_item_id,
            owner_id=owner_id,
            title=title,
            objective=objective,
            business_status=business_status,
            priority=priority,
            facts=facts,
            allowed_modes=[recommendation.mode],
            route_profiles=[
                RouteProfile(
                    mode=recommendation.mode,
                    label={
                        "tool_call": "Tool Call",
                        "single_agent": "Single Agent",
                        "fixed_workflow": "Fixed Workflow",
                        "adaptive_swarm": "Adaptive Swarm",
                    }[recommendation.mode],
                    summary=recommendation.summary,
                    forecast=recommendation.forecast,
                    tradeoff="固定路由，不进入本轮人工覆盖。",
                    impact_preview=Demo2CockpitService._route_impact_preview(
                        recommendation.mode,
                        recommendation.forecast,
                    ),
                )
            ],
            admission_status="route_selected",
            selected_mode=recommendation.mode,
            selection_source="admission",
            recommendation=recommendation,
        )
