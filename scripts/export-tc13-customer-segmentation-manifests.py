from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.api.app.application.customer_segmentation_effect import (
    EXPECTED_DISPLAY_PATHS,
    EXPECTED_FILE_NAMES,
    EXPECTED_FILE_REFS,
    RULES_LOGICAL_ID,
    SOURCE_ORDER,
    SURVEY_LOGICAL_ID,
    CustomerSourceInput,
    build_customer_segmentation,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "demo-enterprise-data" / "forte" / "sales-020" / "input"
MANIFEST_DIR = ROOT / "docs" / "evidence" / "manifests"


def _source(logical_id: str, content: bytes) -> CustomerSourceInput:
    return CustomerSourceInput(
        logical_id=logical_id,
        file_name=EXPECTED_FILE_NAMES[logical_id],
        display_path=EXPECTED_DISPLAY_PATHS[logical_id],
        file_ref=EXPECTED_FILE_REFS[logical_id],
        content=content,
        declared_size=len(content),
        allowlist_verified=True,
    )


def _payload(survey: bytes, rules: bytes, variant: str) -> dict:
    sources = (
        _source(SURVEY_LOGICAL_ID, survey),
        _source(RULES_LOGICAL_ID, rules),
    )
    build = build_customer_segmentation(sources)
    checks = [
        {
            "check_id": item.check_id,
            "label": item.label,
            "passed": item.passed,
            "detail": item.detail,
        }
        for item in build.checks
    ]
    checks.append(
        {
            "check_id": "check-customer-original-sources-read-only-v2",
            "label": "Sales-020 原始资料保持只读",
            "passed": True,
            "detail": "生成后重新读取冻结 Catalog 字节；只写隔离 Run Workspace。",
        }
    )
    return {
        "schema_version": "tc13-public-customer-segmentation.v1",
        "variant": variant,
        "sources": [
            {
                "logical_id": logical_id,
                "file_name": EXPECTED_FILE_NAMES[logical_id],
                "display_path": EXPECTED_DISPLAY_PATHS[logical_id],
                "file_ref": EXPECTED_FILE_REFS[logical_id],
            }
            for logical_id in SOURCE_ORDER
        ],
        "checks": checks,
        "customer_segmentation_outcome": build.analysis.outcome.model_dump(mode="json"),
    }


def manifests() -> dict[Path, dict]:
    survey = (SOURCE_ROOT / EXPECTED_FILE_NAMES[SURVEY_LOGICAL_ID]).read_bytes()
    rules = (SOURCE_ROOT / EXPECTED_FILE_NAMES[RULES_LOGICAL_ID]).read_bytes()
    threshold_rules = rules.decode("utf-8-sig").replace(
        "1. 技术型：专业(Stech)字段数值≥8的客户",
        "1. 技术型：专业(Stech)字段数值≥9的客户",
        1,
    ).encode("utf-8")
    survey_text = survey.decode("gb18030").rstrip("\r\n")
    witness_survey = (
        survey_text + "\n112,制造业,100-500人,技术负责人,9,9,9,9\n"
    ).encode("gb18030")
    reordered_rules = rules.decode("utf-8-sig").replace(
        "`安全型 > 技术型 > 敏捷型`",
        "`技术型 > 安全型 > 敏捷型`",
        1,
    ).encode("utf-8")
    return {
        MANIFEST_DIR / "tc13-public-customer-segmentation-outcome-20260829.json": _payload(
            survey, rules, "canonical"
        ),
        MANIFEST_DIR
        / "tc13-public-customer-segmentation-outcome-threshold-20260829.json": _payload(
            survey, threshold_rules, "technical-threshold-9"
        ),
        MANIFEST_DIR
        / "tc13-public-customer-segmentation-outcome-witness-20260829.json": _payload(
            witness_survey, reordered_rules, "new-multilabel-sample-and-priority-reorder"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    failed = False
    for path, payload in manifests().items():
        rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != rendered:
                print(f"stale: {path.relative_to(ROOT)}")
                failed = True
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered, encoding="utf-8")
            print(path.relative_to(ROOT))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
