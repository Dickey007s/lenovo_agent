"""Bounded, source-linked proposals for additional read-only work."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AdaptiveAddition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=120)
    objective: str = Field(min_length=3, max_length=700)
    reason: str = Field(min_length=3, max_length=400)
    trigger_finding_ids: list[str] = Field(min_length=1, max_length=6)
    parent_unit_ids: list[str] = Field(min_length=1, max_length=6)
    input_file_refs: list[str] = Field(min_length=1, max_length=24)


class AdaptiveReviewProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=3, max_length=500)
    additions: list[AdaptiveAddition] = Field(default_factory=list, max_length=2)


class AdaptiveReviewRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str
    status: Literal["reviewing", "expanded", "unchanged", "blocked", "discarded"]
    reason: str
    called: bool = False
    output_used: bool = False
    elapsed_ms: int = 0
    created_at: datetime
    after_wave: int = Field(default=1, ge=1, le=12)
    origin: Literal["worker_wave", "single_agent"] = "worker_wave"
    added_branch_ids: list[str] = Field(default_factory=list)
    trigger_finding_ids: list[str] = Field(default_factory=list)
    additions: list[AdaptiveAddition] = Field(default_factory=list)


def validate_additions(proposal, plan, findings, completed_unit_ids, used_triggers, remaining_calls):
    """Validate provenance and bounded DAG extension, not semantic truth."""
    allowed_refs = {ref for unit in plan.units for ref in unit.input_file_refs}
    by_unit = {unit.unit_id: unit for unit in plan.units}
    by_finding = {finding.finding_id: finding for finding in findings}
    objectives = {unit.objective.strip() for unit in plan.units}
    if len(plan.units) + len(proposal.additions) > 12 or len(proposal.additions) > remaining_calls:
        raise ValueError("新增工作超过工作包或调用预算")
    for addition in proposal.additions:
        parents = set(addition.parent_unit_ids)
        triggers = set(addition.trigger_finding_ids)
        refs = set(addition.input_file_refs)
        if not parents.issubset(completed_unit_ids) or not parents.issubset(by_unit):
            raise ValueError("新增工作依赖未采用或未知结果")
        if not triggers.issubset(by_finding) or triggers.intersection(used_triggers):
            raise ValueError("新增工作没有新的已定位发现依据")
        if not refs.issubset(allowed_refs):
            raise ValueError("新增工作不能扩大本轮批准来源")
        parent_refs = {ref for uid in parents for ref in by_unit[uid].input_file_refs}
        if not parent_refs.issubset(refs):
            raise ValueError("新增工作缺少前序原文")
        for fid in triggers:
            finding = by_finding[fid]
            if finding.plan_unit_id not in parents or not finding.evidence_anchors:
                raise ValueError("触发发现与前序来源不一致")
            if finding.review and finding.review.requires_human_decision:
                raise ValueError("人工判断不能通过增派 Agent 自动处理")
        if addition.objective.strip() in objectives:
            raise ValueError("不能重复已经计划的工作")
        objectives.add(addition.objective.strip())
        used_triggers = used_triggers | triggers
