from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.api.app.application.sre_diagnosis_effect import (
    EXPECTED_DISPLAY_PATH,
    EXPECTED_FILE_NAME,
    EXPECTED_FILE_REF,
    SOURCE_LOGICAL_ID,
    SRESourceInput,
    build_sre_diagnosis,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "demo-enterprise-data" / "forte" / "sre-010" / "input" / "log.txt"
MANIFEST_DIR = ROOT / "docs" / "evidence" / "manifests"


def _payload(content: bytes, variant: str) -> dict:
    source = SRESourceInput(
        logical_id=SOURCE_LOGICAL_ID,
        file_name=EXPECTED_FILE_NAME,
        display_path=EXPECTED_DISPLAY_PATH,
        file_ref=EXPECTED_FILE_REF,
        content=content,
        declared_size=len(content),
        allowlist_verified=True,
    )
    build = build_sre_diagnosis(source)
    return {
        "schema_version": "tc14-public-sre-diagnosis.v1",
        "variant": variant,
        "source": {
            "logical_id": SOURCE_LOGICAL_ID,
            "file_name": EXPECTED_FILE_NAME,
            "display_path": EXPECTED_DISPLAY_PATH,
            "file_ref": EXPECTED_FILE_REF,
        },
        "checks": [
            {
                "check_id": item.check_id,
                "label": item.label,
                "passed": item.passed,
                "detail": item.detail,
            }
            for item in build.checks
        ],
        "sre_diagnosis_outcome": build.outcome.model_dump(mode="json"),
    }


def manifests() -> dict[Path, dict]:
    canonical = SOURCE_PATH.read_bytes()
    dynamic_text = canonical.decode("utf-8").replace(
        "节点总数: 10",
        "节点总数: 11",
        1,
    ).replace(
        "峰值 4800/s（正常基线 600/s，激增 8 倍）",
        "峰值 5600/s（正常基线 700/s，激增 8 倍）",
        1,
    )
    return {
        MANIFEST_DIR / "tc14-public-sre-diagnosis-outcome-20260829.json": _payload(
            canonical, "canonical"
        ),
        MANIFEST_DIR / "tc14-public-sre-diagnosis-outcome-dynamic-20260829.json": _payload(
            dynamic_text.encode("utf-8"), "node-count-reconciled-and-query-qps-updated"
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
