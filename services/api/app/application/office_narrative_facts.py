"""Bounded metric checks for already verified office files, not semantic proof."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from packages.contracts.harness_models import (
    AgentControlLoopEffectReceipt,
    AgentControlLoopWorkspaceArtifact,
)


def office_effect_facts(
    receipt: AgentControlLoopEffectReceipt,
    artifacts: list[AgentControlLoopWorkspaceArtifact],
) -> tuple[str, dict[str, Any]] | None:
    if receipt.status != "passed":
        return None
    if receipt.finance_review_outcome is not None:
        outcome = receipt.finance_review_outcome
        if outcome.status == "invalid":
            return None
        return "finance_review_outcome", outcome.model_dump(mode="json")
    if receipt.business_gate_outcome is not None:
        outcome = receipt.business_gate_outcome
        if outcome.outcome_kind != "release_readiness" or outcome.status == "invalid":
            return None
        return "business_gate_outcome", outcome.model_dump(mode="json")
    if receipt.capability_id == "office-onboarding-assets":
        approved = [
            item for item in artifacts
            if item.artifact_id in receipt.artifact_ids
            and item.capability_id == receipt.capability_id
            and item.verifier_status == "passed"
            and all(check.passed for check in item.checks)
            and item.record_count is not None
        ]
        if len(approved) == 1:
            artifact = approved[0]
            return "onboarding_file_outcome", {
                "employee_count": artifact.record_count,
                "covered_period": artifact.covered_period,
                "artifact_id": artifact.artifact_id,
                "summary": artifact.summary,
                "source_file_refs": artifact.source_file_refs,
                "external_action": "none",
            }
    return None


def metric_discrepancies(
    kind: str, facts: dict[str, Any], text: str,
) -> tuple[int, list[tuple[str, str, str]]]:
    """Check explicit current-value statements, never thresholds or arbitrary numbers.

    A non-match is unknown, not correct. The caller retains all free prose as a
    supplemental draft even when these narrow numeric comparisons agree.
    """
    rules: list[tuple[str, str, Any, Decimal]] = []
    number = r"([0-9][0-9,]*(?:\.[0-9]+)?)"
    if kind == "onboarding_file_outcome":
        rules.append((
            "employee_count",
            r"(?:共(?:识别出|筛出|有)?|筛选出|筛出|匹配(?:了)?|涵盖)\s*"
            + number + r"\s*(?:名|位|个)?(?:新)?员工",
            facts["employee_count"], Decimal(0),
        ))
    elif kind == "finance_review_outcome":
        for label, prefix in (("未付", "unpaid"), ("未收", "unreceived")):
            rules.append((
                f"{prefix}_total",
                label + r"(?:款|账款|金额)?\s*(?:合计|总额|总计)\s*(?:为|约|约为|[:：])?\s*"
                + number + r"\s*元", facts[f"{prefix}_total"], Decimal("0.01"),
            ))
            rules.append((
                f"{prefix}_count", label + r"\s*(?:共|有)?\s*" + number + r"\s*条",
                facts[f"{prefix}_count"], Decimal(0),
            ))
        rules.append((
            "candidate_count", r"(?:僵尸账款|跨期风险|启发式)?候选\s*(?:共|有|为)?\s*"
            + number + r"\s*条", facts["candidate_count"], Decimal(0),
        ))
    elif kind == "release_source_counts":
        for key, alias in (
            ("p0_features", r"P0\s*功能"),
            ("prd_features", r"PRD(?:_v[\d.]+\.md)?\s*(?:中)?\s*功能"),
        ):
            rules.append((key, alias + r"\s*(?:共|共有|总计|列出|列|仅|有|包含|合计|为|[:：]){1,2}\s*"
                          + number + r"\s*(?:项|个)(?:已提测|功能)?", facts["counts"][key], Decimal(0)))
        rules.append(("prd_features", r"PRD(?:_v[\d.]+\.md)?\s*(?:中)?\s*(?:共|共有|列出|列|有|包含){1,2}\s*"
                      + number + r"\s*(?:项|个)\s*功能", facts["counts"]["prd_features"], Decimal(0)))
        config = r"(?:上线)?配置清单(?:\.xlsx)?\s*(?:中)?\s*(?:共|共有|总计|列出|列|仅|有|包含|合计|为|[:：]){1,2}\s*"
        rules.extend([
            ("configured_features", config + number + r"\s*(?:项|个)(?!\s*(?:功能)?已提测)",
             facts["counts"]["configured_features"], Decimal(0)),
            ("submitted_features", config + number + r"\s*(?:项|个)\s*(?:功能)?已提测",
             facts["counts"]["submitted_features"], Decimal(0)),
            ("submitted_features", r"已提测功能\s*(?:共|共有|有|为|[:：])\s*" + number + r"\s*(?:项|个)",
             facts["counts"]["submitted_features"], Decimal(0)),
        ])
    elif kind == "business_gate_outcome":
        aliases = {
            "business-gate-p0-tested": r"P0\s*(?:功能)?(?:提测率|测试覆盖率)",
            "business-gate-p0-accepted": r"P0\s*已提测功能(?:测试)?(?:结论)?通过率",
            "business-gate-p1-passed": r"P1\s*(?:已提测)?(?:功能)?(?:完成率|通过率)",
        }
        for gate in facts["gates"]:
            alias = aliases.get(gate["gate_id"])
            if alias:
                rules.append((
                    f"gates.{gate['gate_id']}.actual",
                    alias + r"\s*(?:为|仅|实际为|[:：])?\s*" + number + r"\s*%",
                    gate["actual"], Decimal("0.05"),
                ))
        configured = sum(
            record["configuration_status"] != "未列入配置清单"
            for record in facts["records"]
        )
        rules.append((
            "configured_record_count",
            r"上线配置清单(?:\.xlsx)?[”\"]?\s*(?:仅列出|记录|共|共有)\s*"
            + number + r"\s*(?:个|项)(?:已提测)?功能", configured, Decimal(0),
        ))
    compared = 0
    conflicts: list[tuple[str, str, str]] = []
    for path, pattern, expected, tolerance in rules:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if kind in {"business_gate_outcome", "release_source_counts"}:
                prefix = re.split(r"[。；;！!？?\n，,]", text[:match.start()])[-1]
                suffix = re.split(r"[。；;！!？?\n，,]", text[match.end():])[0]
                if re.search(r"要求|门槛|至少|规定|目标|标准|必须|应达到|假设|例如|若|假如", prefix[-40:]) or re.match(
                    r"\s*(?:是|为)?(?:准入|上线)?(?:要求|门槛|目标|标准)", suffix
                ):
                    continue
            compared += 1
            observed = Decimal(match.group(1).replace(",", ""))
            if abs(observed - Decimal(str(expected))) > tolerance:
                conflicts.append((path, str(expected), str(observed)))
    if kind == "finance_review_outcome" and facts["candidate_count"] == 0:
        if re.search(r"(?:僵尸账款|跨期风险)候选(?:包括|包含|为)[^。；]{2,}", text):
            conflicts.append(("candidate_count", "0 条固定口径候选", "模型列出了候选对象"))
    return compared, conflicts
