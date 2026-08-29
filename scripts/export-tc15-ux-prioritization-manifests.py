from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.api.app.application.ux_prioritization_effect import (
    BEHAVIOR_LOGICAL_ID,
    EXPECTED_DISPLAY_PATHS,
    EXPECTED_FILE_NAMES,
    EXPECTED_FILE_REFS,
    RULES_LOGICAL_ID,
    SOURCE_ORDER,
    SPEC_LOGICAL_ID,
    UXSourceInput,
    build_ux_prioritization,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "demo-enterprise-data" / "forte" / "uiux-021" / "input"
MANIFEST_DIR = ROOT / "docs" / "evidence" / "manifests"


def _sources(rule_content: bytes | None = None) -> tuple[UXSourceInput, ...]:
    contents = {
        BEHAVIOR_LOGICAL_ID: (SOURCE_ROOT / EXPECTED_FILE_NAMES[BEHAVIOR_LOGICAL_ID]).read_bytes(),
        RULES_LOGICAL_ID: rule_content
        if rule_content is not None
        else (SOURCE_ROOT / EXPECTED_FILE_NAMES[RULES_LOGICAL_ID]).read_bytes(),
        SPEC_LOGICAL_ID: (SOURCE_ROOT / EXPECTED_FILE_NAMES[SPEC_LOGICAL_ID]).read_bytes(),
    }
    return tuple(
        UXSourceInput(
            logical_id=logical_id,
            file_name=EXPECTED_FILE_NAMES[logical_id],
            display_path=EXPECTED_DISPLAY_PATHS[logical_id],
            file_ref=EXPECTED_FILE_REFS[logical_id],
            content=contents[logical_id],
            declared_size=len(contents[logical_id]),
            allowlist_verified=True,
        )
        for logical_id in SOURCE_ORDER
    )


def _payload(sources: tuple[UXSourceInput, ...], variant: str) -> dict:
    build = build_ux_prioritization(sources)
    return {
        "schema_version": "tc15-public-ux-prioritization.v1",
        "variant": variant,
        "sources": [
            {
                "logical_id": item.logical_id,
                "file_name": item.file_name,
                "display_path": item.display_path,
                "file_ref": item.file_ref,
            }
            for item in sources
        ],
        "checks": [
            {
                "check_id": item.check_id,
                "label": item.label,
                "passed": item.passed,
                "detail": item.detail,
            }
            for item in build.checks
        ],
        "ux_prioritization_outcome": build.analysis.outcome.model_dump(mode="json"),
    }


def manifests() -> dict[Path, dict]:
    canonical_sources = _sources()
    rules = next(item for item in canonical_sources if item.logical_id == RULES_LOGICAL_ID)
    text = rules.content.decode("utf-8-sig")
    for old, new in (
        ("单场景操作占比 ≥ 5%", "单场景操作占比 ≥ 9%"),
        ("结果 ≥ 5% 即为高频", "结果 ≥ 9% 即为高频"),
        ("3% ≤ 单场景操作占比 < 5%", "3% ≤ 单场景操作占比 < 9%"),
        ("(3%, 5%)", "(3%, 9%)"),
    ):
        if old not in text:
            raise RuntimeError(f"TC-15 dynamic fixture token missing: {old}")
        text = text.replace(old, new, 1)
    dynamic_sources = _sources(text.encode("utf-8"))
    return {
        MANIFEST_DIR / "tc15-public-ux-prioritization-outcome-20260829.json": _payload(
            canonical_sources, "canonical"
        ),
        MANIFEST_DIR
        / "tc15-public-ux-prioritization-outcome-threshold-20260829.json": _payload(
            dynamic_sources, "high-frequency-threshold-9-percent"
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
