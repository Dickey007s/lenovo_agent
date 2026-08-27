from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.api.app.application.benchmark_workspace_catalog import (
    BenchmarkWorkspaceCatalog,
)
from services.api.app.application.scenario_effects import (
    SCENARIO_EFFECT_SPECS,
    ScenarioEffectEngine,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FORTE_ROOT = REPO_ROOT / "demo-enterprise-data" / "forte"


def _input_tree_digest() -> str:
    digest = hashlib.sha256()
    files = sorted(
        path
        for path in FORTE_ROOT.rglob("*")
        if path.is_file() and "input" in path.relative_to(FORTE_ROOT).parts
    )
    for path in files:
        digest.update(path.relative_to(FORTE_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def build_gate_manifest(*, phase: str, evidence_file: str) -> dict[str, Any]:
    catalog = BenchmarkWorkspaceCatalog(FORTE_ROOT)
    engine = ScenarioEffectEngine()
    before = _input_tree_digest()
    scenarios: list[dict[str, Any]] = []
    for spec in SCENARIO_EFFECT_SPECS:
        execution = engine.execute(spec.instruction, catalog)
        if execution is None:
            raise RuntimeError(f"{spec.scenario_id} 未匹配到效果适配器")
        artifacts = [
            {
                "file_name": artifact.file_name,
                "media_type": artifact.media_type,
                "size": len(artifact.content),
                "validator_id": artifact.validator_id,
                "verifier_status": artifact.verifier_status,
                "checks": [check.model_dump(mode="json") for check in artifact.checks],
            }
            for artifact in execution.artifacts
        ]
        scenarios.append(
            {
                "scenario_id": spec.scenario_id,
                "capability_id": spec.capability_id,
                "title": spec.title,
                "instruction": spec.instruction,
                "input_facts": [
                    {"folder": folder, "file": label}
                    for folder, label in spec.source_labels
                ],
                "expected_artifacts": list(spec.expected_artifacts),
                "deterministic_validator": spec.deterministic_validator,
                "frontend_effect": spec.frontend_effect,
                "snapshot_event_receipt": list(spec.snapshot_facts),
                "prohibited_side_effects": list(spec.prohibited_side_effects),
                "expected_lifecycle": spec.lifecycle,
                "actual_status": execution.status,
                "state_action_observation_cost_result": {
                    "state": execution.state,
                    "action": execution.action,
                    "observation": execution.observation,
                    "cost": execution.cost,
                    "result": execution.result,
                },
                "source_file_refs": list(execution.source_file_refs),
                "artifacts": artifacts,
                "effect_gate_passed": bool(artifacts)
                and execution.status == "passed"
                and all(
                    check["passed"]
                    for artifact in artifacts
                    for check in artifact["checks"]
                ),
                "evidence_file": evidence_file,
            }
        )
    after = _input_tree_digest()
    if before != after:
        raise RuntimeError("Scenario Effect Gate 修改了 FORTE 原始输入")
    counts: dict[str, int] = {}
    for item in scenarios:
        counts[item["actual_status"]] = counts.get(item["actual_status"], 0) + 1
    return {
        "schema_version": "scenario-effect-gate-run.v1",
        "phase": phase,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "name": "FORTE public demo inputs",
            "source_commit": "345c1ec1487139db9dd319787fa9405ba85d1869",
            "input_tree_sha256": before,
            "original_inputs_modified": False,
        },
        "summary": counts,
        "scenarios": scenarios,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic Scenario Effect Gate")
    parser.add_argument("--phase", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    try:
        evidence_file = output.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        evidence_file = output.name
    manifest = build_gate_manifest(phase=args.phase, evidence_file=evidence_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
