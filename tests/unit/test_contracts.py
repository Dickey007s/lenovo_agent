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
