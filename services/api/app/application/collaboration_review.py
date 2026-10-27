"""Evidence-linked handoff assessments, not a semantic truth verifier."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from packages.contracts.harness_models import AgentControlLoopEvidenceAnchor


WorkerRole = Literal["source_analysis", "dependency_review", "synthesis_review"]


class DependencyAssessmentDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contribution_id: str = Field(min_length=1, max_length=160)
    verdict: Literal["supported", "conflict", "insufficient"]
    explanation: str = Field(min_length=1, max_length=500)
    finding_indices: list[StrictInt] = Field(default_factory=list, max_length=6)


class DependencyAssessment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    contribution_id: str = Field(min_length=1, max_length=160)
    verdict: Literal["supported", "conflict", "insufficient"]
    explanation: str = Field(min_length=1, max_length=500)
    finding_ids: tuple[str, ...] = ()
    evidence_anchors: tuple[AgentControlLoopEvidenceAnchor, ...] = ()


def worker_role(parent_count: int) -> WorkerRole:
    return "source_analysis" if parent_count == 0 else "dependency_review" if parent_count == 1 else "synthesis_review"


def worker_duty(parent_count: int) -> str:
    if not parent_count:
        return "职责：独立来源分析。只根据批准原文形成发现；dependency_assessments 必须为空。"
    return (
        ("职责：交叉核对前序结论。" if parent_count == 1 else "职责：核对并综合多份前序结论。")
        + "逐一检查 dependency_context，不得把前序摘要当作证据。对每个 contribution_id 返回且只返回一条 "
        "dependency_assessments：verdict 为 supported、conflict 或 insufficient，explanation 简述依据，"
        "finding_indices 指向本次 findings 的从 0 开始序号。supported/conflict 必须关联具有前序来源原文引用的 finding；"
        "资料不足用 insufficient。冲突必须保留，不得为通过检查而改成 supported。"
    )


def validate_dependency_assessments(drafts, contexts, candidate_findings, resolved_findings):
    """Bind model judgments to exact parents and independently located evidence."""
    expected = {item.contribution_id: item for item in contexts}
    if len(drafts) != len(expected) or {item.contribution_id for item in drafts} != set(expected):
        raise ValueError("每份前序成果必须且只能核对一次，不能漏项或引用其他贡献。")
    resolved = {item.finding_id: item for item in resolved_findings}
    assessments = []
    for draft in drafts:
        if len(set(draft.finding_indices)) != len(draft.finding_indices) or any(
            index < 0 or index >= len(candidate_findings) for index in draft.finding_indices
        ):
            raise ValueError("交叉核对引用了不存在或重复的发现序号。")
        ids = [candidate_findings[index].finding_id for index in draft.finding_indices]
        if any(finding_id not in resolved for finding_id in ids):
            raise ValueError("交叉核对引用的发现尚未通过原文定位。")
        parent_refs = set(expected[draft.contribution_id].source_file_refs)
        anchors = tuple(anchor for finding_id in ids for anchor in resolved[finding_id].evidence_anchors
                        if anchor.file_ref in parent_refs)
        if draft.verdict != "insufficient" and not anchors:
            raise ValueError("支持或冲突判断必须有该前序成果来源的可定位引用。")
        assessments.append(DependencyAssessment(contribution_id=draft.contribution_id, verdict=draft.verdict,
                                               explanation=draft.explanation, finding_ids=tuple(ids), evidence_anchors=anchors))
    return tuple(assessments)
