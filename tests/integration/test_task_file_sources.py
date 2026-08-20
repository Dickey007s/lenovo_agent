from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from services.api.app.application.demo_source_catalog import DemoSourceCatalog
from services.api.app.application.task_storage import InMemoryTaskStore
from services.api.app.application.tasks import TaskService, TaskTransitionError


async def _advance_to_waiting(service: TaskService, task_id: str) -> object:
    snapshot = await service.start(
        task_id,
        "user_1",
        expected_task_version=1,
        idempotency_key="file-backed-start",
    )
    for index in range(4):
        snapshot = await service.advance(
            task_id,
            "user_1",
            expected_task_version=snapshot.version,
            idempotency_key=f"file-backed-advance-{index}",
        )
    return snapshot


async def test_demo1_conflict_is_derived_from_frozen_file_documents() -> None:
    service = TaskService(InMemoryTaskStore())
    created = await service.create_demo1("user_1", idempotency_key="file-source-demo")

    assert len(created.source_documents) == 4
    assert {item.relative_path for item in created.source_documents} == {
        "mail/customer-a-status-request-2026-06-15.eml",
        "crm/customer-a-revenue-close-v3.csv",
        "forecast/customer-a-revenue-forecast-v2.csv",
        "project/customer-a-weekly-status-v5.json",
    }

    waiting = await _advance_to_waiting(service, created.task_id)
    conflict = waiting.conflicts[0]
    assert conflict.candidate_values == [
        "2400 万元（已关账收入）",
        "2680 万元（销售预测）",
    ]
    assert conflict.operation_context is not None
    assert conflict.operation_context.target_field == "经营分析.已实现收入"
    assert conflict.operation_context.attempted_source_field == "forecast_revenue"
    assert "预测字段写入已实现收入" in conflict.operation_context.mismatch_reason


async def test_demo1_rejects_source_file_changed_after_task_creation(
    tmp_path: Path,
) -> None:
    source_root = DemoSourceCatalog.default_root()
    test_root = tmp_path / "customer-a"
    shutil.copytree(source_root, test_root)
    service = TaskService(
        InMemoryTaskStore(), source_catalog=DemoSourceCatalog(test_root)
    )
    created = await service.create_demo1("user_1", idempotency_key="file-change-demo")
    forecast = test_root / "forecast" / "customer-a-revenue-forecast-v2.csv"
    forecast.write_text(
        forecast.read_text(encoding="utf-8").replace("2680", "2690"),
        encoding="utf-8",
    )

    with pytest.raises(TaskTransitionError, match="文件已变化或校验失败"):
        await service.start(
            created.task_id,
            "user_1",
            expected_task_version=created.version,
            idempotency_key="changed-file-start",
        )

    restored = await service.get(created.task_id, "user_1")
    assert restored.version == 1
    assert restored.status == "ready"
