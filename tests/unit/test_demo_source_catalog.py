from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from services.api.app.application.demo_source_catalog import (
    DEMO1_FORECAST_REVENUE_SOURCE,
    DEMO1_OFFICIAL_REVENUE_SOURCE,
    DemoSourceCatalog,
    DemoSourceError,
)


def test_demo_source_catalog_reads_file_backed_business_facts() -> None:
    package = DemoSourceCatalog().load_demo1()

    assert package.dataset_id == "customer-a-reporting-demo-20260820"
    assert len(package.documents) == 4
    assert package.fact(DEMO1_OFFICIAL_REVENUE_SOURCE, "recognized_revenue") == "2400"
    assert package.fact(DEMO1_FORECAST_REVENUE_SOURCE, "forecast_revenue") == "2680"

    official = package.document(DEMO1_OFFICIAL_REVENUE_SOURCE)
    forecast = package.document(DEMO1_FORECAST_REVENUE_SOURCE)
    assert official.relative_path == "crm/customer-a-revenue-close-v3.csv"
    assert official.record_status == "已关账"
    assert official.content_digest.startswith("sha256:")
    assert forecast.relative_path == "forecast/customer-a-revenue-forecast-v2.csv"
    assert forecast.record_status == "预测中"


def test_demo_source_catalog_rejects_changed_file(tmp_path: Path) -> None:
    source_root = DemoSourceCatalog.default_root()
    test_root = tmp_path / "customer-a"
    shutil.copytree(source_root, test_root)
    catalog = DemoSourceCatalog(test_root)
    original = catalog.load_demo1()

    forecast = test_root / "forecast" / "customer-a-revenue-forecast-v2.csv"
    forecast.write_text(
        forecast.read_text(encoding="utf-8").replace("2680", "2690"),
        encoding="utf-8",
    )

    with pytest.raises(DemoSourceError, match="完整性校验失败"):
        catalog.require_unchanged(list(original.documents))


def test_demo_source_catalog_rejects_missing_file(tmp_path: Path) -> None:
    source_root = DemoSourceCatalog.default_root()
    test_root = tmp_path / "customer-a"
    shutil.copytree(source_root, test_root)
    (test_root / "crm" / "customer-a-revenue-close-v3.csv").unlink()

    with pytest.raises(DemoSourceError, match="不存在或不可读取"):
        DemoSourceCatalog(test_root).load_demo1()


def test_demo_source_catalog_rejects_path_traversal(tmp_path: Path) -> None:
    source_root = DemoSourceCatalog.default_root()
    test_root = tmp_path / "customer-a"
    shutil.copytree(source_root, test_root)
    manifest_path = test_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["documents"][0]["relative_path"] = "../outside.eml"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(DemoSourceError, match="不安全路径"):
        DemoSourceCatalog(test_root).load_demo1()


def test_demo_source_catalog_rejects_invalid_revenue_semantics(tmp_path: Path) -> None:
    source_root = DemoSourceCatalog.default_root()
    test_root = tmp_path / "customer-a"
    shutil.copytree(source_root, test_root)
    official_path = test_root / "crm" / "customer-a-revenue-close-v3.csv"
    official_path.write_text(
        official_path.read_text(encoding="utf-8").replace(
            "recognized_revenue", "forecast_revenue"
        ),
        encoding="utf-8",
    )
    manifest_path = test_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["documents"][1]["sha256"] = hashlib.sha256(
        official_path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(DemoSourceError, match="口径或状态"):
        DemoSourceCatalog(test_root).load_demo1()


@pytest.mark.parametrize("invalid_amount", ["NaN", "Infinity", "-1", "24.5"])
def test_demo_source_catalog_rejects_invalid_revenue_amount(
    tmp_path: Path,
    invalid_amount: str,
) -> None:
    source_root = DemoSourceCatalog.default_root()
    test_root = tmp_path / "customer-a"
    shutil.copytree(source_root, test_root)
    official_path = test_root / "crm" / "customer-a-revenue-close-v3.csv"
    official_path.write_text(
        official_path.read_text(encoding="utf-8").replace("2400", invalid_amount),
        encoding="utf-8",
    )
    manifest_path = test_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["documents"][1]["sha256"] = hashlib.sha256(
        official_path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(DemoSourceError, match="正整数万元"):
        DemoSourceCatalog(test_root).load_demo1()
