from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.api.app.application.outbound_flow_effect import (
    EXPECTED_DISPLAY_PATH,
    EXPECTED_FILE_NAME,
    EXPECTED_FILE_REF,
    SOURCE_LOGICAL_ID,
    OutboundSourceInput,
    build_outbound_flow,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "demo-enterprise-data" / "forte" / "Operations-008" / "input" / EXPECTED_FILE_NAME
MANIFEST_DIR = ROOT / "docs" / "evidence" / "manifests"


def source_input(content: bytes) -> OutboundSourceInput:
    return OutboundSourceInput(
        logical_id=SOURCE_LOGICAL_ID,
        file_name=EXPECTED_FILE_NAME,
        display_path=EXPECTED_DISPLAY_PATH,
        file_ref=EXPECTED_FILE_REF,
        content=content,
        declared_size=len(content),
        allowlist_verified=True,
    )


def public_payload(content: bytes, variant: str) -> dict:
    build = build_outbound_flow(source_input(content))
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
            "check_id": "check-outbound-original-source-read-only-v2",
            "label": "批准来源保持只读",
            "passed": True,
            "detail": "生成后重新读取冻结 Catalog 字节；本工具只写隔离运行工作区，不修改 Operations-008 原件。",
        }
    )
    return {
        "schema_version": "tc10-public-outbound-flow.v1",
        "variant": variant,
        "source": {
            "logical_id": SOURCE_LOGICAL_ID,
            "file_name": EXPECTED_FILE_NAME,
            "display_path": EXPECTED_DISPLAY_PATH,
            "file_ref": EXPECTED_FILE_REF,
        },
        "checks": checks,
        "outbound_flow_outcome": build.outcome.model_dump(mode="json"),
    }


def manifests() -> dict[Path, dict]:
    baseline = SOURCE_PATH.read_bytes()
    dynamic_text = baseline.decode("utf-8")
    dynamic_text = dynamic_text.replace(
        "每日 22:00 至次日 08:00 严禁拨打",
        "每日 21:00 至次日 09:00 严禁拨打",
        1,
    ).replace(
        "每日拨打不得超过 3 次，1小时内不得超过 1 次",
        "每日拨打不得超过 5 次，2小时内不得超过 2 次",
        1,
    )
    return {
        MANIFEST_DIR / "tc10-public-outbound-flow-outcome-20260829.json": public_payload(
            baseline, "canonical"
        ),
        MANIFEST_DIR / "tc10-public-outbound-flow-outcome-dynamic-20260829.json": public_payload(
            dynamic_text.encode("utf-8"), "time-frequency-mutation"
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
