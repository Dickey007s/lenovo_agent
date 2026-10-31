"""Offline stand-ins for the planner and analyst, used by the demo-mode switch.

They plug into the same Run pipeline as the real model clients, so plan
validation, evidence anchoring, human gates and the workflow tree all run for
real. Only the two model calls are replaced by deterministic rules:

* the planner splits the instruction into numbered items (or per-file groups),
  binds each to the files it names, and records items with no named source as
  "missing source";
* the analyst quotes the best-matching line / table row of those files, and
  raises a human decision when the item itself says the owner must decide.

Everything written here is labelled as a demo simulation; it is not analysis.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from services.api.app.application.collaboration_review import DependencyAssessmentDraft
from services.api.app.application.harness_runtime import (
    HarnessAnalystDecisionOptionDraft,
    HarnessAnalystFindingDraft,
    HarnessAnalystFindingReviewDraft,
    HarnessAnalystResultDraft,
    HarnessEvidenceQuote,
    HarnessModelError,
    HarnessPlan,
    HarnessPlanCandidate,
    HarnessPlanCandidateUnit,
    HarnessRequirementCoverage,
    HarnessRuntime,
    HarnessTaskResult,
)

SIMULATED_MODEL = "演示模拟"
PLAN_DELAY_SECONDS = 1.0
ANALYSIS_DELAY_SECONDS = 1.6

_ITEM = re.compile(r"^\s*(\d{1,2})\s*[\.、．]\s*(.+?)\s*$")
_SPLIT_MARKERS = ("分别", "分主题", "各自")
_OWNER_DECISION = re.compile(r"负责人(?:来)?决定|不要自行裁决|需要?人(?:来)?确认|需要负责人")
_DEPENDS_ON_ALL = re.compile(r"以上.{0,6}(?:都|均)?完成|汇总|之后再")
# The runtime wraps a follow-up as "<background JSON>\n本次后续要求：\n<what the user chose>".
_FOLLOW_UP_MARK = "\n本次后续要求：\n"


def _stem(label: str) -> str:
    return label.rsplit(".", 1)[0] if "." in label else label


def _mentions(text: str, label: str) -> bool:
    stem = _stem(label)
    if label in text or stem in text:
        return True
    # "外卖商户BD岗位" is how people write "外卖商户BD岗位JD.docx".
    return len(stem) >= 8 and stem[:-2] in text


def _grams(text: str, size: int = 3) -> set[str]:
    squeezed = re.sub(r"[\s，。；：、,.;:()（）《》【】\[\]\"“”|]+", "", text)
    return {squeezed[i : i + size] for i in range(max(0, len(squeezed) - size + 1))}


def _clause(text: str, limit: int = 30) -> str:
    cleaned = re.sub(r"^(阅读|从)", "", text.strip())
    head = re.split(r"[，。；,;\n]", cleaned, maxsplit=1)[0].strip() or cleaned.strip()
    if head.startswith("《"):
        head = "核对" + head
    return head[:limit]


def _missing_title(text: str) -> str:
    match = re.search(r"([一-龥A-Za-z0-9]{0,6}(?:回单|凭证|合同|发票|协议|证明|单据|报告))", text)
    return f"缺少来源：{match.group(1).lstrip('的那笔款来对和与及')}" if match else f"缺少来源：{_clause(text, 14)}"


class SimulatedPlanner:
    model = SIMULATED_MODEL

    async def plan(
        self, *, scenario: dict[str, Any], files: list[dict[str, Any]]
    ) -> HarnessPlanCandidate:
        await asyncio.sleep(PLAN_DELAY_SECONDS)
        instruction = str(scenario.get("task_instruction") or scenario.get("goal") or "")
        if _FOLLOW_UP_MARK in instruction:
            return self._plan_follow_up(instruction, files)
        labels = {str(item["file_ref"]): str(item.get("display_label", "")) for item in files}

        def named(text: str) -> list[str]:
            return [ref for ref, label in labels.items() if label and _mentions(text, label)]

        expected = HarnessRuntime._explicit_business_requirement_count(instruction)
        items: list[tuple[int, str]] = []
        if expected:
            for line in instruction.splitlines():
                match = _ITEM.match(line)
                if match and int(match.group(1)) == len(items) + 1:
                    items.append((int(match.group(1)), match.group(2)))
            if len(items) != expected:
                items = []
        units: list[HarnessPlanCandidateUnit] = []
        coverage: list[HarnessRequirementCoverage] = []

        if items:
            planned: list[HarnessPlanCandidateUnit] = []
            for index, text in items:
                refs = named(text)
                depends = bool(_DEPENDS_ON_ALL.search(text)) and bool(planned)
                title = _clause(re.split(r"[，,]", text, maxsplit=1)[-1]) if depends else _clause(text)
                if depends:
                    # A summary step reads what the earlier steps read.
                    refs = list(dict.fromkeys(ref for unit in planned for ref in unit.input_file_refs))
                if not refs:
                    coverage.append(
                        HarnessRequirementCoverage(
                            requirement_index=index,
                            title=_missing_title(text),
                            objective=text[:1000],
                            status="uncovered",
                            reason="资料库里没有找到这一项要求对应的来源文件，需要你补充材料。",
                        )
                    )
                    continue
                unit = HarnessPlanCandidateUnit(
                    unit_id=f"u{index}",
                    title=title,
                    objective=text[:1000],
                    input_file_refs=refs,
                    depends_on=[item.unit_id for item in planned] if depends else [],
                    tool="evidence.verify",
                )
                planned.append(unit)
                coverage.append(
                    HarnessRequirementCoverage(
                        requirement_index=index,
                        title=unit.title,
                        objective=unit.objective,
                        status="planned",
                        unit_id=unit.unit_id,
                        reason="按要求编号单独成一项工作。",
                    )
                )
            units = planned
        else:
            refs = list(dict.fromkeys(named(instruction)))
            if not refs:
                # No file is named: fall back to the closest descriptions.
                want = _grams(instruction)
                scored = sorted(
                    (
                        (len(want & _grams(str(item.get("display_label", "")) + str(item.get("display_summary", "")))), str(item["file_ref"]))
                        for item in files
                    ),
                    reverse=True,
                )
                refs = [ref for score, ref in scored[:2] if score >= 2]
            if not refs:
                raise HarnessModelError(
                    "演示模拟没有找到可用的文件，请在任务里用《文件名》指明资料",
                    called=False,
                    model=SIMULATED_MODEL,
                )
            if len(refs) > 1 and any(marker in instruction for marker in _SPLIT_MARKERS):
                for index, ref in enumerate(refs, start=1):
                    units.append(
                        HarnessPlanCandidateUnit(
                            unit_id=f"u{index}",
                            title=f"核对《{_stem(labels[ref])}》"[:60],
                            objective=instruction[:1000],
                            input_file_refs=[ref],
                            tool="evidence.verify",
                        )
                    )
            else:
                units.append(
                    HarnessPlanCandidateUnit(
                        unit_id="u1",
                        title=_clause(instruction.splitlines()[0] if instruction.strip() else instruction),
                        objective=instruction[:1000],
                        input_file_refs=refs,
                        tool="evidence.verify",
                    )
                )
        if not units:
            raise HarnessModelError(
                "演示模拟没有找到任何一项有来源的工作，请在任务里用《文件名》指明资料",
                called=False,
                model=SIMULATED_MODEL,
            )
        return HarnessPlanCandidate(
            summary=f"演示模拟：把任务拆成 {len(units)} 项只读核对。",
            selection_reason="演示模拟按任务里写明的文件名和编号拆分，没有调用模型。",
            units=units,
            requirement_coverage=coverage,
        )


    @staticmethod
    def _plan_follow_up(instruction: str, files: list[dict[str, Any]]) -> HarnessPlanCandidate:
        """A follow-up only does what the person just chose, on the files the original task named."""
        background, request = instruction.split(_FOLLOW_UP_MARK, 1)
        request = request.strip()
        refs = [
            str(item["file_ref"])
            for item in files
            if item.get("display_label") and _mentions(background, str(item["display_label"]))
        ]
        if not refs:
            raise HarnessModelError(
                "演示模拟找不到原任务用到的文件，无法继续后续处理",
                called=False,
                model=SIMULATED_MODEL,
            )
        # The first line is the chosen path; the rest is the decision record the UI appends.
        goal = request.splitlines()[0].strip() or request
        unit = HarnessPlanCandidateUnit(
            unit_id="u1",
            title=goal[:60],
            objective=goal[:1000],
            input_file_refs=list(dict.fromkeys(refs))[:4],
            tool="evidence.verify",
        )
        return HarnessPlanCandidate(
            summary="演示模拟：按你刚才的决定继续，只整理现规则允许的内容。",
            selection_reason="演示模拟沿用原任务点名的文件，没有调用模型。",
            units=[unit],
            requirement_coverage=[],
        )


class SimulatedAnalyst:
    model = SIMULATED_MODEL

    async def analyze(
        self,
        *,
        instruction: str,
        plan: HarnessPlan,
        files: list[dict[str, Any]],
        validation_feedback: str | None = None,
        dependency_context: list[dict[str, Any]] | None = None,
        **_ignored: Any,
    ) -> HarnessTaskResult:
        await asyncio.sleep(ANALYSIS_DELAY_SECONDS)
        by_ref = {str(item["file_ref"]): item for item in files}
        findings: list[HarnessAnalystFindingDraft] = []
        assessments: list[DependencyAssessmentDraft] = []
        for unit in plan.units:
            refs = [ref for ref in unit.input_file_refs if ref in by_ref]
            if not refs:
                continue
            if dependency_context:
                for position, parent in enumerate(dependency_context):
                    scope = [ref for ref in parent.get("source_file_refs", []) if ref in by_ref] or refs
                    findings.append(self._finding(unit.unit_id, unit.objective, [by_ref[ref] for ref in scope[:4]], "上游成果在原文中重新核对"))
                    assessments.append(
                        DependencyAssessmentDraft(
                            contribution_id=str(parent["contribution_id"]),
                            verdict="supported",
                            explanation="演示模拟：已回到原文重新引用对应片段。",
                            finding_indices=[len(findings) - 1],
                        )
                    )
                continue
            # One finding per group of up to 4 files, quoting every file, so no source is left unchecked.
            for start in range(0, len(refs), 4):
                findings.append(
                    self._finding(unit.unit_id, unit.objective, [by_ref[ref] for ref in refs[start : start + 4]], None)
                )
        if not findings:
            raise HarnessModelError("演示模拟没有可分析的文件", called=False, model=SIMULATED_MODEL)
        draft = HarnessAnalystResultDraft(
            summary="演示模拟：已逐项摘出相关原文，以下内容不是模型分析，仍需你核对。",
            findings=findings,
            dependency_assessments=assessments,
        )
        return draft.to_task_result()

    def _finding(
        self, unit_id: str, objective: str, sources: list[dict[str, Any]], title_override: str | None
    ) -> HarnessAnalystFindingDraft:
        source = sources[0]
        label = "、".join(_stem(str(item.get("display_label", "资料"))) for item in sources[:2]) if len(sources) > 1 else str(source.get("display_label", "资料"))
        quotes = [self._quote(item, objective) for item in sources]
        quote = quotes[0]
        decision = bool(_OWNER_DECISION.search(objective))
        return HarnessAnalystFindingDraft(
            plan_unit_id=unit_id,
            title=(f"需要负责人决定：{_stem(label)}" if decision else title_override or f"已摘出《{_stem(label)}》的相关原文")[:200],
            detail=(
                f"演示模拟：从《{label}》里选出与「{_clause(objective, 40)}」最接近的一段原文，供你点开核对。"
                "这是按关键词匹配出来的，不代表已经判断对错。"
            ),
            fact_summary=f"原文：{quote[:120]}",
            impact="仅整理页面内容，不修改任何文件。" if not decision else "在负责人决定之前，不会开通、变更或发送任何内容。",
            file_refs=[str(item["file_ref"]) for item in sources],
            evidence_quotes=[
                HarnessEvidenceQuote(
                    file_ref=str(item["file_ref"]),
                    role="observed" if not decision else "contradiction",
                    label=f"匹配到的原文 · {_stem(str(item.get('display_label', '资料')))}"[:120],
                    quote=text,
                )
                for item, text in zip(sources, quotes)
            ],
            review=self._review(label) if decision else None,
        )

    @staticmethod
    def _review(label: str) -> HarnessAnalystFindingReviewDraft:
        return HarnessAnalystFindingReviewDraft(
            question="维持现规则，还是整理变更申请？",
            why_human=f"《{_stem(label)}》里有明确备注与本次要求冲突。这是对既有规则的例外，按约定必须由负责人决定，系统不自行裁决。",
            options=[
                HarnessAnalystDecisionOptionDraft(
                    option_id="A",
                    label="维持现规则",
                    meaning="按原文里已写明的规则办理，不做例外。",
                    agent_next_step="只整理现规则允许的内容，不再提例外。",
                    next_instruction="维持现规则，只整理现规则允许的内容",
                ),
                HarnessAnalystDecisionOptionDraft(
                    option_id="B",
                    label="整理变更申请",
                    meaning="把例外整理成一份申请草稿，交负责人走审批。",
                    agent_next_step="只起草申请，不执行任何开通或变更。",
                    next_instruction="整理一份变更申请草稿，交负责人审批",
                ),
            ],
            recommended_option_id="A",
            recommendation_reason="没有负责人明确同意之前，保持现规则最稳妥。",
            after_confirmation="按你选的路径继续，只在页面整理，不执行任何开通。",
        )

    @staticmethod
    def _quote(source: dict[str, Any], objective: str) -> str:
        want = _grams(objective)
        if source.get("kind") == "table":
            best: tuple[int, str] | None = None
            for row in source.get("rows") or []:
                if not isinstance(row, dict) or not isinstance(row.get("values"), list):
                    continue
                joined = " ".join(" | ".join(str(v) for v in row["values"]).split())
                if len(joined) < 4:
                    continue
                score = len(want & _grams(joined))
                if best is None or score > best[0]:
                    best = (score, joined[:500])
            if best:
                return best[1]
        text = str(source.get("text") or "")
        lines = [line.strip() for line in text.splitlines()]
        usable = [line for line in lines if 6 <= len(line) <= 300 and text.count(line) == 1]
        if usable:
            return max(usable, key=lambda line: (len(want & _grams(line)), len(line) >= 12))
        fallback = " ".join(text.split())[:200]
        if len(fallback) >= 4:
            return fallback
        raise HarnessModelError("演示模拟在这份文件里找不到可引用的原文", called=False, model=SIMULATED_MODEL)
