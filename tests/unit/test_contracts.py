from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from packages.contracts import ActionCandidate
from packages.contracts.harness_models import (
    AgentControlLoopEffectReceipt,
    AgentControlLoopWorkspaceArtifact,
)


def test_action_candidate_forbids_trusted_fields_and_unknown_properties() -> None:
    with pytest.raises(ValidationError):
        ActionCandidate.model_validate(
            {
                "action_type": "send_email",
                "capability": "email.send",
                "target_scope": "external_customer",
                "state_change_type": "external_effect",
                "reversibility": "low",
                "actor_id": "model_must_not_set_this",
            }
        )


def test_workspace_artifact_and_effect_receipt_round_trip_all_workspace_sources() -> None:
    source_refs = [f"file-ref-{index:02d}" for index in range(46)]
    now = datetime.now(timezone.utc)
    artifact = AgentControlLoopWorkspaceArtifact.model_validate(
        {
            "artifact_id": "workspace-artifact-123456789abc",
            "capability_id": "office-evaluation-platform-fix",
            "scenario_id": "TC-04",
            "title": "评测平台修复包",
            "file_name": "评测平台真实修复包.zip",
            "media_type": "application/zip",
            "size": 1024,
            "round_number": 1,
            "source_file_refs": source_refs,
            "validator_id": "validator-evaluation-platform-project-v2",
            "verifier_status": "passed",
            "checks": [
                {
                    "check_id": "check-full-project-copy",
                    "label": "完整项目副本",
                    "passed": True,
                    "detail": "44 个 source-code 文件均在隔离副本中。",
                }
            ],
            "summary": "完整副本、真实测试与修复 diff。",
            "self_test": {
                "instruction": "在隔离副本运行真实测试。",
                "expected_files": ["evaluation-platform/test-manifest.json"],
                "commands": ["python run_self_test.py"],
                "expected_checks": ["声明与 collected IDs 一致"],
                "failure_signals": ["命令非零"],
                "test_manifest_file": "evaluation-platform/test-manifest.json",
                "test_manifest_matches_collected": True,
                "test_suites": [
                    {
                        "suite_id": "model-service",
                        "label": "模型 Service",
                        "test_files": ["tests/test_model_service.py"],
                        "test_count": 1,
                        "test_ids": [
                            "test_model_service.ModelServiceTests.test_delete_rejects_running_experiment"
                        ],
                    }
                ],
            },
            "download_path": "/v1/harness/runs/run-1/artifacts/artifact-1",
            "created_at": now,
        }
    )
    receipt = AgentControlLoopEffectReceipt.model_validate(
        {
            "receipt_id": "effect-receipt-123456789abc",
            "capability_id": "office-evaluation-platform-fix",
            "scenario_id": "TC-04",
            "status": "passed",
            "state": "冻结完整项目输入。",
            "action": "测试并修复隔离副本。",
            "observation": "117 项真实测试通过。",
            "cost": "0 次额外模型调用。",
            "result": "生成可下载修复包和报告。",
            "source_file_refs": source_refs,
            "artifact_ids": [artifact.artifact_id],
            "created_at": now,
        }
    )

    artifact_round_trip = AgentControlLoopWorkspaceArtifact.model_validate_json(
        artifact.model_dump_json()
    )
    receipt_round_trip = AgentControlLoopEffectReceipt.model_validate_json(
        receipt.model_dump_json()
    )
    assert artifact_round_trip.source_file_refs == source_refs
    assert artifact_round_trip.self_test is not None
    assert artifact_round_trip.self_test.test_manifest_matches_collected is True
    assert artifact_round_trip.self_test.test_suites[0].test_count == 1
    assert receipt_round_trip.source_file_refs == source_refs
    assert (
        AgentControlLoopWorkspaceArtifact.model_json_schema()["properties"]
        ["source_file_refs"]["maxItems"]
        == 96
    )
    assert (
        AgentControlLoopEffectReceipt.model_json_schema()["properties"]
        ["source_file_refs"]["maxItems"]
        == 96
    )


def test_business_gate_outcome_round_trips_on_artifact_and_effect_receipt() -> None:
    now = datetime.now(timezone.utc)
    outcome = {
        "outcome_id": "business-outcome-release-readiness",
        "status": "failed",
        "decision": "不得上线",
        "summary": "4/4 条正式上线条件未通过。",
        "total_gate_count": 1,
        "failed_gate_count": 1,
        "gates": [
            {
                "gate_id": "business-gate-p0-tested",
                "label": "P0 功能提测率",
                "passed": False,
                "numerator": 5,
                "denominator": 7,
                "operator": ">=",
                "threshold": 100,
                "actual": 71.4,
                "unit": "percent",
                "formula": "已提测 P0 / 全部 P0",
                "source_rule": "PRD 上线条件。",
                "result": "5/7 = 71.4%。",
            }
        ],
        "auxiliary_metrics": [],
        "records": [
            {
                "record_id": "F01",
                "title": "安全审核开关",
                "module": "内容安全审核模块",
                "priority": "P0",
                "owner": "王磊",
                "configuration_status": "已提测",
                "test_status": "通过",
                "test_reason": "无",
                "total_cases": 12,
                "passed_cases": 12,
                "compatibility_issue_count": 0,
                "compatibility_issue_environments": [],
                "rules_hit": [],
                "base_risk_level": "none",
                "compatibility_risk_level": "none",
                "final_risk_level": "none",
                "affected_gate_ids": [],
                "source_locations": ["PRD_v2.5.md 第 1 行"],
                "remediation_action": "保留证据并复核。",
                "exit_condition": "正式上线 Gate 均满足。",
            }
        ],
    }
    artifact = AgentControlLoopWorkspaceArtifact.model_validate(
        {
            "artifact_id": "workspace-artifact-abcdef123456",
            "capability_id": "office-release-readiness",
            "scenario_id": "TC-11",
            "title": "上线合规与风险报告",
            "file_name": "上线合规与风险报告.docx",
            "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "size": 1024,
            "round_number": 1,
            "source_file_refs": ["file-ref-01"],
            "validator_id": "validator-release-readiness-v2",
            "verifier_status": "passed",
            "checks": [
                {
                    "check_id": "check-release-source-contract",
                    "label": "来源合同",
                    "passed": True,
                    "detail": "四份来源通过结构校验。",
                }
            ],
            "summary": "文件结构与公式通过检查，业务 Gate 未通过。",
            "business_gate_outcome": outcome,
            "download_path": "/v1/harness/runs/run-1/artifacts/artifact-1",
            "created_at": now,
        }
    )
    receipt = AgentControlLoopEffectReceipt.model_validate(
        {
            "receipt_id": "effect-receipt-abcdef123456",
            "capability_id": "office-release-readiness",
            "scenario_id": "TC-11",
            "status": "passed",
            "state": "冻结四份来源。",
            "action": "生成报告与台账。",
            "observation": "确定性检查通过，业务 Gate 未通过。",
            "cost": "0 次额外模型调用。",
            "result": "不得上线。",
            "source_file_refs": ["file-ref-01"],
            "artifact_ids": [artifact.artifact_id],
            "business_gate_outcome": outcome,
            "created_at": now,
        }
    )

    restored_artifact = AgentControlLoopWorkspaceArtifact.model_validate_json(
        artifact.model_dump_json()
    )
    restored_receipt = AgentControlLoopEffectReceipt.model_validate_json(
        receipt.model_dump_json()
    )
    assert restored_artifact.business_gate_outcome is not None
    assert restored_artifact.business_gate_outcome.failed_gate_count == 1
    assert restored_receipt.business_gate_outcome is not None
    assert restored_receipt.business_gate_outcome.decision == "不得上线"


def test_legal_review_outcome_round_trips_with_all_six_documents() -> None:
    now = datetime.now(timezone.utc)
    rule_ids = [
        *(f"R{index:02d}" for index in range(1, 7)),
        *(f"M{index:02d}" for index in range(1, 10)),
        *(f"L{index:02d}" for index in range(1, 7)),
    ]
    documents = []
    for document_index in range(1, 7):
        document_id = f"DOC-{document_index:02d}"
        documents.append(
            {
                "document_id": document_id,
                "document_name": f"委托书{document_index}.docx",
                "source_file_ref": f"file-ref-{document_index:02d}",
                "highest_triggered_level": "high",
                "triggered_count": 1,
                "unverifiable_count": 1,
                "signing_evidence_status": "absent",
                "summary": "签署栏为空，仍需法务复核。",
                "assessments": [
                    {
                        "assessment_id": f"legal-assessment-doc-{document_index:02d}-{rule_id.lower()}",
                        "rule_id": rule_id,
                        "rule_name": f"规则 {rule_id}",
                        "rule_level": "high" if rule_id.startswith("R") else "medium" if rule_id.startswith("M") else "low",
                        "status": "triggered" if rule_id == "R05" else "unverifiable" if rule_id == "M02" else "not_triggered",
                        "source_locator": "P8",
                        "excerpt": "委托人签名：",
                        "fact": "签署栏为空。",
                        "judgment": "按来源规则核查。",
                        "reason": "来源足以判断或明确资料不足。",
                        "owner": "法务负责人",
                        "remediation_action": "补充并核验材料。",
                        "exit_condition": "材料可由法务独立核验。",
                    }
                    for rule_id in rule_ids
                ],
            }
        )
    legal_outcome = {
        "outcome_id": "legal-review-outcome-legal-020",
        "status": "review_required",
        "decision": "不得据此签署，必须法务复核",
        "summary": "六份文件均有高风险或关键资料不足。",
        "document_count": 6,
        "rule_count": 21,
        "assessment_count": 126,
        "high_risk_document_count": 6,
        "medium_risk_document_count": 0,
        "low_risk_document_count": 0,
        "no_trigger_document_count": 0,
        "critical_unverifiable_count": 6,
        "signing_evidence_count": 0,
        "human_review_required": True,
        "signing_status": "evidence_incomplete",
        "documents": documents,
    }
    business_outcome = {
        "outcome_id": "business-outcome-legal-delegation-review",
        "outcome_kind": "legal_delegation_review",
        "status": "failed",
        "decision": "不得据此签署，必须法务复核",
        "summary": "3/3 条法务判断条件未通过。",
        "total_gate_count": 3,
        "failed_gate_count": 3,
        "gates": [],
        "auxiliary_metrics": [],
        "records": [],
    }
    common = {
        "capability_id": "office-legal-delegation-review",
        "scenario_id": "TC-07",
        "source_file_refs": [f"file-ref-{index:02d}" for index in range(1, 8)],
        "business_gate_outcome": business_outcome,
        "legal_review_outcome": legal_outcome,
        "created_at": now,
    }
    artifact = AgentControlLoopWorkspaceArtifact.model_validate(
        {
            **common,
            "artifact_id": "workspace-artifact-fedcba654321",
            "title": "授权委托书逐项核查台账",
            "file_name": "授权委托书逐项核查台账.csv",
            "media_type": "text/csv",
            "size": 4096,
            "round_number": 1,
            "validator_id": "validator-legal-delegation-v2",
            "verifier_status": "passed",
            "checks": [
                {
                    "check_id": "check-legal-assessment-coverage",
                    "label": "126 条逐项核查",
                    "passed": True,
                    "detail": "六份文件逐项覆盖全部 21 条来源规则。",
                }
            ],
            "summary": "结构通过核验，法务 Gate 未通过。",
            "download_path": "/v1/harness/runs/run-1/artifacts/artifact-1",
        }
    )
    receipt = AgentControlLoopEffectReceipt.model_validate(
        {
            **common,
            "receipt_id": "effect-receipt-fedcba654321",
            "status": "passed",
            "state": "冻结七份来源。",
            "action": "生成报告与台账。",
            "observation": "文件结构通过，法务 Gate 未通过。",
            "cost": "0 次额外模型调用。",
            "result": "不得据此签署。",
            "artifact_ids": [artifact.artifact_id],
        }
    )

    restored_artifact = AgentControlLoopWorkspaceArtifact.model_validate_json(
        artifact.model_dump_json()
    )
    restored_receipt = AgentControlLoopEffectReceipt.model_validate_json(
        receipt.model_dump_json()
    )
    assert restored_artifact.legal_review_outcome is not None
    assert len(restored_artifact.legal_review_outcome.documents) == 6
    assert len(restored_artifact.legal_review_outcome.documents[0].assessments) == 21
    assert restored_artifact.business_gate_outcome is not None
    assert restored_artifact.business_gate_outcome.outcome_kind == "legal_delegation_review"
    assert restored_receipt.legal_review_outcome is not None
    assert restored_receipt.legal_review_outcome.assessment_count == 126


def test_candidate_review_outcome_round_trips_without_becoming_a_hiring_decision() -> None:
    now = datetime.now(timezone.utc)
    assessment = {
        "assessment_id": "candidate-assessment-text-evaluation-cand-02-ai-experience",
        "role_id": "text_evaluation",
        "candidate_id": "CAND-02",
        "candidate_name": "孙博文",
        "condition_id": "TEXT-REQ-AI-EXPERIENCE",
        "condition_type": "required",
        "condition_label": "AI 评测或开发经历",
        "jd_source_file_ref": "jd-text-ref",
        "jd_locator": "非空行 8",
        "jd_excerpt": "必要项：1 年以上 AI 相关评测或开发工作经验",
        "resume_source_file_ref": "resume-sun-ref",
        "resume_locator": "第 1 页 · 非空行 9",
        "resume_excerpt": "算法工程师（8 个月）",
        "resume_evidence_present": True,
        "status": "not_met",
        "fact": "可复算 AI 相关经历为 8 个月。",
        "judgment": "来源显示存在明确条件缺口；这仍不是自动淘汰决定。",
        "reason": "低于 JD 的 12 个月必要门槛。",
        "owner": "招聘负责人",
        "review_action": "核对是否有未写入简历的补充经历。",
        "exit_condition": "招聘负责人记录人工处置。",
    }
    outcome = {
        "outcome_id": "candidate-review-outcome-hr-001",
        "status": "review_required",
        "decision": "这是人工复核建议，不是录用或淘汰决定。",
        "summary": "1 个岗位、1 名候选人、1 条来源推导条件。",
        "role_count": 1,
        "candidate_count": 1,
        "review_count": 1,
        "assessment_count": 1,
        "met_count": 0,
        "not_met_count": 1,
        "unverifiable_count": 0,
        "human_exception_count": 0,
        "recommended_for_human_review_count": 0,
        "explicit_hard_gap_count": 1,
        "insufficient_evidence_count": 0,
        "exception_review_required_count": 0,
        "human_review_required": True,
        "fairness_evaluated": False,
        "reviews": [
            {
                "review_id": "candidate-review-text-evaluation-cand-02",
                "role_id": "text_evaluation",
                "role_name": "文本评测",
                "jd_source_file_ref": "jd-text-ref",
                "candidate_id": "CAND-02",
                "candidate_name": "孙博文",
                "resume_source_file_ref": "resume-sun-ref",
                "recommendation": "explicit_hard_gap",
                "condition_count": 1,
                "met_count": 0,
                "not_met_count": 1,
                "unverifiable_count": 0,
                "human_exception_count": 0,
                "summary": "存在明确硬条件缺口，但不作自动淘汰。",
                "assessments": [assessment],
            }
        ],
    }
    common = {
        "capability_id": "office-candidate-review",
        "scenario_id": "TC-06",
        "source_file_refs": ["jd-text-ref", "resume-sun-ref"],
        "candidate_review_outcome": outcome,
        "created_at": now,
    }
    artifact = AgentControlLoopWorkspaceArtifact.model_validate(
        {
            **common,
            "artifact_id": "workspace-artifact-a1b2c3d4e5f6",
            "title": "候选人岗位条件逐项台账",
            "file_name": "候选人岗位条件逐项台账.csv",
            "media_type": "text/csv",
            "size": 2048,
            "round_number": 1,
            "validator_id": "validator-candidate-review-v2",
            "verifier_status": "passed",
            "checks": [
                {
                    "check_id": "check-candidate-dynamic-outcome",
                    "label": "四态与建议动态汇总",
                    "passed": True,
                    "detail": "逐条件来源重算与成果一致。",
                }
            ],
            "summary": "一条条件记录可独立复算。",
            "download_path": "/v1/harness/runs/run-1/artifacts/artifact-1",
        }
    )
    receipt = AgentControlLoopEffectReceipt.model_validate(
        {
            **common,
            "receipt_id": "effect-receipt-a1b2c3d4e5f6",
            "status": "passed",
            "state": "冻结批准来源。",
            "action": "生成辅助筛选报告与台账。",
            "observation": "确定性检查通过，最终 HR 决定仍待人工处理。",
            "cost": "0 次额外模型调用。",
            "result": "不作自动录用或淘汰。",
            "artifact_ids": [artifact.artifact_id],
        }
    )

    restored_artifact = AgentControlLoopWorkspaceArtifact.model_validate_json(
        artifact.model_dump_json()
    )
    restored_receipt = AgentControlLoopEffectReceipt.model_validate_json(
        receipt.model_dump_json()
    )
    assert restored_artifact.candidate_review_outcome is not None
    assert restored_artifact.candidate_review_outcome.reviews[0].assessments[0].status == "not_met"
    assert restored_receipt.candidate_review_outcome is not None
    assert restored_receipt.candidate_review_outcome.human_review_required is True
    assert restored_receipt.candidate_review_outcome.fairness_evaluated is False


def test_finance_review_outcome_round_trips_without_becoming_an_accounting_action() -> None:
    now = datetime.now(timezone.utc)
    outcome = {
        "outcome_id": "finance-review-outcome-finance-018",
        "status": "review_required",
        "decision": "发现 1 条跨期风险候选，最终由财务复核。",
        "summary": "2026 期末未付 31 条、未收 2 条，跨三期候选 1 条。",
        "period_ids": ["2025_h1", "2025_h2", "2026"],
        "unpaid_count": 31,
        "unpaid_total": "3984606.46",
        "unreceived_count": 2,
        "unreceived_total": "4992891.47",
        "candidate_count": 1,
        "candidates": [
            {
                "candidate_id": "finance-candidate-123456789abc",
                "key": "其他应收款\\其他应收往来 / 绵阳长城发展融资担保有限公司",
                "subject": "其他应收款\\其他应收往来",
                "customer": "绵阳长城发展融资担保有限公司",
                "sources": [
                    {
                        "period_id": period_id,
                        "period_label": period_label,
                        "source_file_ref": f"finance-{period_id}",
                        "file_name": file_name,
                        "sheet_name": "Sheet1",
                        "row_number": 3,
                        "locator": "Sheet1!A3:J3",
                        "direction": "借",
                        "ending_balance": "1500000",
                    }
                    for period_id, period_label, file_name in (
                        ("2025_h1", "2025 年上半年", "2025往来明细-上半年.xlsx"),
                        ("2025_h2", "2025 年下半年", "2025往来明细-下半年.xlsx"),
                        ("2026", "2026 年", "2026往来明细.xlsx"),
                    )
                ],
                "review_action": "核对期间内发生额、账龄、币种、主体和核销记录。",
                "exit_condition": "财务负责人记录候选是否继续处置及依据。",
            }
        ],
        "method": "同一科目和客商在三个期间均为正数借方期末余额且金额完全相同。",
        "limitations": ["不检查期间内发生额。", "不支持多主体或多币种。"],
        "human_review_required": True,
        "original_inputs_modified": False,
        "external_action": "none",
    }
    common = {
        "capability_id": "office-finance-reconciliation",
        "scenario_id": "TC-05",
        "source_file_refs": ["finance-2025-h1", "finance-2025-h2", "finance-2026"],
        "finance_review_outcome": outcome,
        "created_at": now,
    }
    artifact = AgentControlLoopWorkspaceArtifact.model_validate(
        {
            **common,
            "artifact_id": "workspace-artifact-123456789abc",
            "title": "三期僵尸账款候选核对说明",
            "file_name": "跨期核对说明.md",
            "media_type": "text/markdown",
            "size": 2048,
            "round_number": 1,
            "validator_id": "validator-finance-reconciliation-v2",
            "verifier_status": "passed",
            "checks": [
                {
                    "check_id": "check-finance-zombie",
                    "label": "候选枚举与来源重算一致",
                    "passed": True,
                    "detail": "1 条候选与三个期间批准来源逐项一致。",
                }
            ],
            "summary": "发现 1 条候选，需财务复核。",
            "download_path": "/v1/harness/runs/run-1/artifacts/artifact-1",
        }
    )
    receipt = AgentControlLoopEffectReceipt.model_validate(
        {
            **common,
            "receipt_id": "effect-receipt-123456789abc",
            "status": "passed",
            "state": "冻结并重读三个期间的批准来源。",
            "action": "生成两份 2026 期末明细和一份三期候选说明。",
            "observation": "来源、金额、候选枚举和成果结构通过确定性复核。",
            "cost": "0 次额外模型调用。",
            "result": "候选仍需财务复核，没有发生会计动作。",
            "artifact_ids": [artifact.artifact_id],
        }
    )

    restored_artifact = AgentControlLoopWorkspaceArtifact.model_validate_json(
        artifact.model_dump_json()
    )
    restored_receipt = AgentControlLoopEffectReceipt.model_validate_json(
        receipt.model_dump_json()
    )
    assert restored_artifact.finance_review_outcome is not None
    assert restored_artifact.finance_review_outcome.candidate_count == 1
    assert restored_artifact.finance_review_outcome.candidates[0].sources[2].period_id == "2026"
    assert restored_receipt.finance_review_outcome == restored_artifact.finance_review_outcome
    assert restored_receipt.finance_review_outcome.original_inputs_modified is False
    assert restored_receipt.finance_review_outcome.external_action == "none"


def test_customer_segmentation_outcome_round_trips_without_becoming_a_sales_action() -> None:
    now = datetime.now(timezone.utc)
    outcome = {
        "outcome_id": "customer-segmentation-outcome-sales-020",
        "status": "sales_review_required",
        "decision": "清洗与画像已重算，重复口径和策略草案仍需销售负责人批准。",
        "summary": "2 行公开样本，1 条分类、1 条精确重复。",
        "source_row_count": 2,
        "unique_payload_count": 1,
        "duplicate_count": 1,
        "classified_count": 1,
        "unclassified_count": 0,
        "excluded_count": 1,
        "profile_counts": {"技术型": 1, "安全型": 0, "敏捷型": 0},
        "parameters": {
            "parsing_encoding": "gb18030",
            "missing_score_default": 0,
            "chinese_number_domain": "零至十，对应整数 0..10",
            "profile_thresholds": {"技术型": 8, "安全型": 8, "敏捷型": 8},
            "profile_priority": ["安全型", "技术型", "敏捷型"],
            "duplicate_policy": "exact_non_id_payload",
        },
        "rules": [
            {
                "rule_id": "SEG-PROFILE-TECH",
                "category": "classification",
                "source_file_ref": "sales-rules-ref",
                "locator": "客户分类画像与差异化销售策略生成规则.md:L12",
                "excerpt": "技术型：专业评分达到来源阈值。",
                "parameters": ["threshold=8"],
            }
        ],
        "samples": [
            {
                "sample_id": "101",
                "source_file_ref": "sales-survey-ref",
                "source_row": 2,
                "source_locator": "客户画像调研问卷.csv:row=2",
                "industry": "金融科技",
                "company_size": "500-1000人",
                "respondent_role": "技术架构师",
                "raw_scores": {"tech": "9", "safe": "7", "budget": "6", "easy": "2"},
                "cleaned_scores": {"tech": 9, "safe": 7, "budget": 6, "easy": 2},
                "transformations": [],
                "matched_profiles": ["技术型"],
                "priority_applied": False,
                "final_label": "技术型",
                "exclusion_reason": None,
                "duplicate_of": None,
                "rule_refs": ["SEG-PROFILE-TECH"],
            },
            {
                "sample_id": "111",
                "source_file_ref": "sales-survey-ref",
                "source_row": 3,
                "source_locator": "客户画像调研问卷.csv:row=3",
                "industry": "金融科技",
                "company_size": "500-1000人",
                "respondent_role": "技术架构师",
                "raw_scores": {"tech": "9", "safe": "7", "budget": "6", "easy": "2"},
                "cleaned_scores": {"tech": 9, "safe": 7, "budget": 6, "easy": 2},
                "transformations": [],
                "matched_profiles": ["技术型"],
                "priority_applied": False,
                "final_label": None,
                "exclusion_reason": "exact_duplicate",
                "duplicate_of": "101",
                "rule_refs": ["SEG-PROFILE-TECH"],
            },
        ],
        "duplicate_policy_assumption": "exact_non_id_payload",
        "policy_assumption_review_required": True,
        "priority_witness_count": 0,
        "strategy_evidence_status": "no_approved_strategy_source",
        "human_review_required": True,
        "original_inputs_modified": False,
        "external_action": "none",
    }
    common = {
        "capability_id": "office-customer-segmentation",
        "scenario_id": "TC-13",
        "source_file_refs": ["sales-survey-ref", "sales-rules-ref"],
        "customer_segmentation_outcome": outcome,
        "created_at": now,
    }
    artifact = AgentControlLoopWorkspaceArtifact.model_validate(
        {
            **common,
            "artifact_id": "workspace-artifact-abcdef123456",
            "title": "公开样本画像清洗与策略草案",
            "file_name": "客户画像及销售策略.md",
            "media_type": "text/markdown",
            "size": 2048,
            "round_number": 1,
            "validator_id": "validator-customer-segmentation-v2",
            "verifier_status": "passed",
            "checks": [
                {
                    "check_id": "check-customer-ledger-v2",
                    "label": "逐样本台账来源重算一致",
                    "passed": True,
                    "detail": "两行样本和重复关系一致。",
                }
            ],
            "summary": "清洗与画像通过，销售策略仍待批准。",
            "download_path": "/v1/harness/runs/run-1/artifacts/customer-1",
        }
    )
    receipt = AgentControlLoopEffectReceipt.model_validate(
        {
            **common,
            "receipt_id": "effect-receipt-abcdef123456",
            "status": "passed",
            "state": "冻结问卷与规则。",
            "action": "重算清洗、画像并生成 Markdown 与 CSV。",
            "observation": "来源、台账和报告结构通过确定性复核。",
            "cost": "0 次额外模型调用。",
            "result": "策略仍待批准，没有发生客户动作。",
            "artifact_ids": [artifact.artifact_id],
        }
    )

    restored_artifact = AgentControlLoopWorkspaceArtifact.model_validate_json(
        artifact.model_dump_json()
    )
    restored_receipt = AgentControlLoopEffectReceipt.model_validate_json(
        receipt.model_dump_json()
    )
    assert restored_artifact.customer_segmentation_outcome is not None
    assert restored_artifact.customer_segmentation_outcome.duplicate_count == 1
    assert restored_artifact.customer_segmentation_outcome.priority_witness_count == 0
    assert restored_receipt.customer_segmentation_outcome == (
        restored_artifact.customer_segmentation_outcome
    )
    assert restored_receipt.customer_segmentation_outcome.external_action == "none"


def test_outbound_flow_outcome_round_trips_without_becoming_an_execution_receipt() -> None:
    now = datetime.now(timezone.utc)
    outcome = {
        "outcome_id": "outbound-flow-outcome-operations-008",
        "status": "approval_required",
        "decision": "规则与图结构已复核，仍需业务与合规负责人审批。",
        "summary": "1 条来源要求映射到一个最小测试图。",
        "source_rule_group_count": 1,
        "atomic_requirement_count": 1,
        "covered_count": 1,
        "unsupported_count": 0,
        "conflict_count": 0,
        "node_count": 1,
        "edge_count": 0,
        "guard_count": 0,
        "terminal_count": 1,
        "reachable_terminal_count": 1,
        "parameters": [],
        "rules": [
            {
                "rule_id": "OUT-TIME-01",
                "group": "TIME",
                "source_file_ref": "forte-ba23e986a9c7e8d8",
                "locator": "专业性说明.md:L22",
                "excerpt": "流程中必须在拨号前判断当前时段。",
                "parameters": [],
                "expected_relation": "拨号前检查时段",
                "expected_action": "先进入时段 Gate",
                "coverage_state": "covered",
                "mapped_node_ids": ["out-node-start"],
                "mapped_edge_ids": [],
                "mapped_guard_ids": [],
                "mapped_terminal_ids": ["out-terminal-done"],
            }
        ],
        "nodes": [
            {
                "node_id": "out-node-start",
                "label": "START",
                "kind": "start",
                "source_rule_ids": ["OUT-TIME-01"],
                "future_action": False,
            }
        ],
        "edges": [],
        "guards": [],
        "terminals": [
            {
                "terminal_id": "out-terminal-done",
                "node_id": "out-node-start",
                "label": "测试终态",
                "source_rule_ids": ["OUT-TIME-01"],
                "source_listed": True,
            }
        ],
        "graph_integrity": {
            "unique_start": True,
            "unique_ids": True,
            "no_dangling_edges": True,
            "all_nodes_reachable": True,
            "all_terminals_reachable": True,
            "every_nonterminal_has_outgoing": True,
            "every_node_can_reach_terminal": True,
            "critical_order_valid": True,
            "third_party_boundary_valid": True,
            "all_rules_mapped": True,
        },
        "human_approval_required": True,
        "legal_opinion": False,
        "original_inputs_modified": False,
        "external_action": "none",
    }
    artifact = AgentControlLoopWorkspaceArtifact.model_validate(
        {
            "artifact_id": "workspace-artifact-abcdef123456",
            "capability_id": "office-compliant-outbound-flow",
            "scenario_id": "TC-10",
            "title": "外呼流程设计",
            "file_name": "外呼流程-M1逾期用户AI外呼催收流程图.docx",
            "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "size": 1024,
            "round_number": 1,
            "source_file_refs": ["forte-ba23e986a9c7e8d8"],
            "validator_id": "validator-compliant-outbound-flow-v2",
            "verifier_status": "passed",
            "checks": [
                {
                    "check_id": "check-outbound-rule-ledger-v2",
                    "label": "来源规则账本",
                    "passed": True,
                    "detail": "来源规则与 DOCX 表格一致。",
                }
            ],
            "summary": "只生成流程设计，没有执行拨号。",
            "outbound_flow_outcome": outcome,
            "download_path": "/v1/harness/runs/run-1/artifacts/outbound-1",
            "created_at": now,
        }
    )
    receipt = AgentControlLoopEffectReceipt.model_validate(
        {
            "receipt_id": "effect-receipt-abcdef123456",
            "capability_id": "office-compliant-outbound-flow",
            "scenario_id": "TC-10",
            "status": "passed",
            "state": "批准来源已冻结。",
            "action": "生成隔离流程设计。",
            "observation": "来源规则和状态图已复核。",
            "cost": "0 次额外模型调用。",
            "result": "最终审批与外部动作均未发生。",
            "source_file_refs": ["forte-ba23e986a9c7e8d8"],
            "artifact_ids": [artifact.artifact_id],
            "prohibited_side_effects": ["不拨号", "不写 CRM", "不发送短信"],
            "outbound_flow_outcome": outcome,
            "created_at": now,
        }
    )

    restored_artifact = AgentControlLoopWorkspaceArtifact.model_validate_json(
        artifact.model_dump_json()
    )
    restored_receipt = AgentControlLoopEffectReceipt.model_validate_json(
        receipt.model_dump_json()
    )
    assert restored_artifact.outbound_flow_outcome is not None
    assert restored_receipt.outbound_flow_outcome == restored_artifact.outbound_flow_outcome
    assert restored_receipt.outbound_flow_outcome.human_approval_required is True
    assert restored_receipt.outbound_flow_outcome.legal_opinion is False
    assert restored_receipt.outbound_flow_outcome.external_action == "none"
