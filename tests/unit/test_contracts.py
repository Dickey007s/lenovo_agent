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
