"""Export the public TC-11 business Gate facts used by UI evidence fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from services.api.app.application.benchmark_workspace_catalog import (
    BenchmarkWorkspaceCatalog,
)
from services.api.app.application.release_readiness_effect import (
    build_release_readiness,
)
from services.api.app.application.scenario_effects import (
    SCENARIO_EFFECT_SPECS,
    ScenarioEffectEngine,
)


ROOT = Path(__file__).resolve().parents[1]
TARGET = (
    ROOT
    / "docs"
    / "evidence"
    / "manifests"
    / "tc11-business-gate-outcome-20260828.json"
)


def main() -> None:
    catalog = BenchmarkWorkspaceCatalog(ROOT / "demo-enterprise-data" / "forte")
    spec = next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == "TC-11")
    previews = ScenarioEffectEngine._previews(catalog, spec)
    build = build_release_readiness(previews)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(
        json.dumps(build.outcome.model_dump(mode="json"), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(TARGET)


if __name__ == "__main__":
    main()
