"""Build TC-04 from the complete real FORTE evaluation-platform project."""

from __future__ import annotations

import ast
import difflib
import hashlib
import json
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class EvaluationPlatformBuild:
    archive_files: dict[str, bytes | str]
    report: bytes
    checks: tuple[tuple[str, str, bool, str], ...]
    source_file_count: int
    test_count: int
    coverage_percent: float
    baseline_ms: int
    compile_ms: int
    test_ms: int
    execution_ok: bool
    changed_files: tuple[str, ...]
    changed_source_coverage: tuple[tuple[str, float], ...]
    source_tree_digest: str
    test_suites: tuple[dict[str, object], ...]


def _render_case_module(
    imports: str,
    class_declaration: str,
    cases: tuple[tuple[str, str], ...],
    *,
    asynchronous: bool = False,
) -> str:
    """Render named, inspectable unittest cases into the downloadable project."""

    keyword = "async def" if asynchronous else "def"
    methods = []
    for name, body in cases:
        rendered_body = textwrap.indent(textwrap.dedent(body).strip(), " " * 8)
        methods.append(f"    {keyword} test_{name}(self):\n{rendered_body}")
    return (
        textwrap.dedent(imports).strip()
        + f"\n\n\nclass {class_declaration}:\n"
        + "\n\n".join(methods)
        + "\n"
    )


TEST_HELPERS = textwrap.dedent(
    r'''
    import tempfile
    import unittest
    from pathlib import Path

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.database import Base
    from app.models import Dataset, DatasetItem, Experiment, Model


    class DatabaseTestCase(unittest.IsolatedAsyncioTestCase):
        async def asyncSetUp(self):
            self._temporary_directory = tempfile.TemporaryDirectory(prefix="eval-platform-tests-")
            database_path = Path(self._temporary_directory.name) / "test.db"
            self.engine = create_async_engine(
                f"sqlite+aiosqlite:///{database_path.as_posix()}",
                connect_args={"check_same_thread": False},
            )
            self.Session = async_sessionmaker(self.engine, expire_on_commit=False)
            async with self.engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)

        async def asyncTearDown(self):
            await self.engine.dispose()
            self._temporary_directory.cleanup()

        async def add_model(self, session, *, status="ACTIVE", name="model-a"):
            model = Model(
                name=name,
                model_type="LLM",
                version="v1.0.0",
                endpoint_url="https://model.invalid/evaluate",
                status=status,
                created_by="tester",
            )
            session.add(model)
            await session.flush()
            return model

        async def add_dataset(self, session, *, name="dataset-a", item_count=0):
            dataset = Dataset(
                name=name,
                version="v1.0.0",
                item_count=item_count,
                created_by="tester",
            )
            session.add(dataset)
            await session.flush()
            return dataset

        async def add_item(self, session, dataset, *, seq, input_text="input"):
            item = DatasetItem(
                dataset_id=dataset.id,
                seq=seq,
                input_text=input_text,
                expected_output="expected",
            )
            session.add(item)
            await session.flush()
            return item

        async def _item_for_engine(self):
            async with self.Session() as session:
                dataset = await self.add_dataset(session)
                item = await self.add_item(session, dataset, seq=1, input_text="question")
                await session.commit()
                session.expunge(item)
                return item

        async def add_experiment(
            self,
            session,
            model,
            dataset,
            *,
            status="RUNNING",
            concurrency=2,
        ):
            experiment = Experiment(
                name="experiment-a",
                model_id=model.id,
                dataset_id=dataset.id,
                concurrency=concurrency,
                timeout_seconds=10,
                status=status,
                created_by="tester",
            )
            session.add(experiment)
            await session.flush()
            return experiment
    '''
).strip() + "\n"


MODEL_SERVICE_TESTS = textwrap.dedent(
    r'''
    from app.schemas.model import ModelCreate
    from app.services import model_service
    from app.utils.response import AppException, ErrorCode
    from tests.helpers import DatabaseTestCase


    class ModelServiceTests(DatabaseTestCase):
        async def test_delete_rejects_running_experiment(self):
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                await self.add_experiment(session, model, dataset, status="RUNNING")
                await session.commit()
                with self.assertRaises(AppException) as caught:
                    await model_service.delete_model(session, model.id, "reviewer")
                self.assertEqual(caught.exception.code, ErrorCode.OPERATION_NOT_ALLOWED)

        async def test_delete_allows_completed_experiment(self):
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                await self.add_experiment(session, model, dataset, status="COMPLETED")
                await session.commit()
                await model_service.delete_model(session, model.id, "reviewer")
                self.assertIsNotNone(model.deleted_at)

        async def test_create_model_encrypts_and_masks_api_key(self):
            async with self.Session() as session:
                response = await model_service.create_model(
                    session,
                    ModelCreate(
                        name="secured",
                        model_type="LLM",
                        version="v1.2.3",
                        api_key="top-secret",
                    ),
                    "reviewer",
                )
                self.assertTrue(response.api_key_masked.endswith("cret"))
                self.assertNotIn("top-secret", response.api_key_masked)

        async def test_get_model_missing_raises_not_found(self):
            async with self.Session() as session:
                with self.assertRaises(AppException) as caught:
                    await model_service.get_model(session, 999)
                self.assertEqual(caught.exception.code, ErrorCode.NOT_FOUND)

        async def test_list_models_filters_and_paginates_real_rows(self):
            async with self.Session() as session:
                await self.add_model(session, name="alpha")
                await self.add_model(session, name="beta")
                await session.commit()
                items, total = await model_service.list_models(
                    session, name="alp", page=1, page_size=1
                )
                self.assertEqual(total, 1)
                self.assertEqual([item.name for item in items], ["alpha"])
    '''
).strip() + "\n"


DATASET_SERVICE_TESTS = textwrap.dedent(
    r'''
    import json
    from unittest.mock import patch

    from sqlalchemy import select

    from app.models.dataset_item import DatasetItem
    from app.services import dataset_service
    from app.utils.response import AppException, ErrorCode
    from tests.helpers import DatabaseTestCase


    class DatasetServiceTests(DatabaseTestCase):
        async def test_append_uses_next_sequence_after_current_maximum(self):
            async with self.Session() as session:
                dataset = await self.add_dataset(session, item_count=1)
                await self.add_item(session, dataset, seq=7)
                await session.commit()
                payload = json.dumps(
                    [{"input": "next-a"}, {"input": "next-b"}]
                ).encode()
                result = await dataset_service.import_dataset_items(
                    session, dataset.id, payload, "append", "reviewer"
                )
                rows = (
                    await session.execute(
                        select(DatasetItem)
                        .where(DatasetItem.dataset_id == dataset.id)
                        .order_by(DatasetItem.seq)
                    )
                ).scalars().all()
                self.assertEqual([row.seq for row in rows], [7, 8, 9])
                self.assertEqual(result["total_count"], 3)

        async def test_overwrite_restarts_sequence_at_one(self):
            async with self.Session() as session:
                dataset = await self.add_dataset(session, item_count=1)
                await self.add_item(session, dataset, seq=9)
                await session.commit()
                payload = json.dumps(
                    [{"input": "first"}, {"input": "second"}]
                ).encode()
                await dataset_service.import_dataset_items(
                    session, dataset.id, payload, "overwrite", "reviewer"
                )
                rows = (
                    await session.execute(
                        select(DatasetItem)
                        .where(DatasetItem.dataset_id == dataset.id)
                        .order_by(DatasetItem.seq)
                    )
                ).scalars().all()
                self.assertEqual([row.seq for row in rows], [1, 2])

        async def test_invalid_json_is_reported_as_file_format_error(self):
            with self.assertRaises(AppException) as caught:
                dataset_service._parse_json_file(b"{broken")
            self.assertEqual(caught.exception.code, ErrorCode.FILE_FORMAT_ERROR)

        async def test_file_size_limit_is_checked_before_database_read(self):
            async with self.Session() as session:
                with patch.object(dataset_service.settings, "max_upload_size", 3):
                    with self.assertRaises(AppException) as caught:
                        await dataset_service.import_dataset_items(
                            session, 1, b"1234", "append", "reviewer"
                        )
                self.assertEqual(caught.exception.code, ErrorCode.FILE_TOO_LARGE)

        async def test_delete_dataset_rejects_running_experiment(self):
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                await self.add_experiment(session, model, dataset, status="RUNNING")
                await session.commit()
                with self.assertRaises(AppException) as caught:
                    await dataset_service.delete_dataset(session, dataset.id, "reviewer")
                self.assertEqual(caught.exception.code, ErrorCode.OPERATION_NOT_ALLOWED)

        async def test_get_dataset_items_uses_real_order_and_page(self):
            async with self.Session() as session:
                dataset = await self.add_dataset(session, item_count=3)
                for seq in (3, 1, 2):
                    await self.add_item(session, dataset, seq=seq, input_text=f"input-{seq}")
                await session.commit()
                items, total = await dataset_service.get_dataset_items(
                    session, dataset.id, page=2, page_size=2
                )
                self.assertEqual(total, 3)
                self.assertEqual([item.seq for item in items], [3])
    '''
).strip() + "\n"


EXPERIMENT_SERVICE_TESTS = textwrap.dedent(
    r'''
    from unittest.mock import AsyncMock, patch

    from app.engine.evaluation_engine import evaluation_engine
    from app.models.experiment_result import ExperimentResult
    from app.schemas.experiment import ExperimentCreate
    from app.services import experiment_service
    from app.utils.response import AppException, ErrorCode
    from tests.helpers import DatabaseTestCase


    class ExperimentServiceTests(DatabaseTestCase):
        async def test_create_experiment_commits_and_starts_real_engine_contract(self):
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                await session.commit()
                with patch.object(
                    evaluation_engine, "start", new_callable=AsyncMock
                ) as start:
                    response = await experiment_service.create_experiment(
                        session,
                        ExperimentCreate(
                            name="real-evaluation",
                            model_id=model.id,
                            dataset_id=dataset.id,
                            concurrency=3,
                            timeout_seconds=15,
                        ),
                        "reviewer",
                    )
                start.assert_awaited_once_with(response.id)
                self.assertEqual(response.status, "RUNNING")

        async def test_create_experiment_rejects_disabled_model(self):
            async with self.Session() as session:
                model = await self.add_model(session, status="DISABLED")
                dataset = await self.add_dataset(session)
                await session.commit()
                with self.assertRaises(AppException) as caught:
                    await experiment_service.create_experiment(
                        session,
                        ExperimentCreate(
                            name="blocked",
                            model_id=model.id,
                            dataset_id=dataset.id,
                        ),
                        "reviewer",
                    )
                self.assertEqual(caught.exception.code, ErrorCode.OPERATION_NOT_ALLOWED)

        async def test_create_experiment_rejects_missing_dataset(self):
            async with self.Session() as session:
                model = await self.add_model(session)
                await session.commit()
                with self.assertRaises(AppException) as caught:
                    await experiment_service.create_experiment(
                        session,
                        ExperimentCreate(name="missing", model_id=model.id, dataset_id=999),
                        "reviewer",
                    )
                self.assertEqual(caught.exception.code, ErrorCode.NOT_FOUND)

        async def test_detail_reads_statistics_and_result_page(self):
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session, item_count=1)
                item = await self.add_item(session, dataset, seq=1)
                experiment = await self.add_experiment(
                    session, model, dataset, status="COMPLETED"
                )
                experiment.total_count = 1
                experiment.success_count = 1
                experiment.failed_count = 0
                experiment.p99_ms = 12
                session.add(
                    ExperimentResult(
                        experiment_id=experiment.id,
                        dataset_item_id=item.id,
                        seq=1,
                        input_text="input",
                        expected_output="expected",
                        actual_output="actual",
                        response_time_ms=12,
                        status="SUCCESS",
                    )
                )
                await session.commit()
                detail = await experiment_service.get_experiment_detail(
                    session, experiment.id
                )
                self.assertEqual(detail["statistics"]["p99_ms"], 12)
                self.assertEqual(detail["results"]["items"][0]["actual_output"], "actual")

        async def test_cancel_rejects_non_running_experiment(self):
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                experiment = await self.add_experiment(
                    session, model, dataset, status="COMPLETED"
                )
                await session.commit()
                with self.assertRaises(AppException) as caught:
                    await experiment_service.cancel_experiment(
                        session, experiment.id, "reviewer"
                    )
                self.assertEqual(caught.exception.code, ErrorCode.OPERATION_NOT_ALLOWED)
    '''
).strip() + "\n"


ENGINE_TESTS = textwrap.dedent(
    r'''
    import asyncio
    from unittest.mock import AsyncMock, patch

    import httpx
    from sqlalchemy import func, select

    from app.engine.evaluation_engine import EvaluationEngine
    from app.models.experiment_result import ExperimentResult
    from app.models.dataset_item import DatasetItem
    from tests.helpers import DatabaseTestCase


    class EvaluationEngineTests(DatabaseTestCase):
        def build_item(self):
            return DatasetItem(
                id=1,
                dataset_id=1,
                seq=1,
                input_text="question",
                expected_output="answer",
            )

        async def test_missing_endpoint_returns_failed_result_without_http(self):
            engine = EvaluationEngine()
            experiment = type("ExperimentStub", (), {"id": 1, "timeout_seconds": 5})()
            result = await engine._evaluate_single_item(
                experiment, self.build_item(), None, None
            )
            self.assertEqual(result.status, "FAILED")
            self.assertIn("URL", result.error_message)

        async def test_mock_http_success_uses_real_engine_method(self):
            engine = EvaluationEngine()
            experiment = type("ExperimentStub", (), {"id": 1, "timeout_seconds": 5})()
            transport = httpx.MockTransport(
                lambda request: httpx.Response(200, json={"output": "done"}, request=request)
            )
            real_client = httpx.AsyncClient
            with patch(
                "app.engine.evaluation_engine.httpx.AsyncClient",
                side_effect=lambda **kwargs: real_client(transport=transport, **kwargs),
            ):
                result = await engine._evaluate_single_item(
                    experiment, self.build_item(), "https://model.invalid/run", "secret"
                )
            self.assertEqual(result.status, "SUCCESS")
            self.assertEqual(result.actual_output, "done")

        async def test_mock_http_status_error_is_bounded(self):
            engine = EvaluationEngine()
            experiment = type("ExperimentStub", (), {"id": 1, "timeout_seconds": 5})()
            transport = httpx.MockTransport(
                lambda request: httpx.Response(503, text="down", request=request)
            )
            real_client = httpx.AsyncClient
            with patch(
                "app.engine.evaluation_engine.httpx.AsyncClient",
                side_effect=lambda **kwargs: real_client(transport=transport, **kwargs),
            ):
                result = await engine._evaluate_single_item(
                    experiment, self.build_item(), "https://model.invalid/run", None
                )
            self.assertEqual(result.status, "FAILED")
            self.assertIn("503", result.error_message)

        async def test_mock_http_timeout_is_bounded(self):
            engine = EvaluationEngine()
            experiment = type("ExperimentStub", (), {"id": 1, "timeout_seconds": 5})()

            def timeout(request):
                raise httpx.ReadTimeout("timeout", request=request)

            transport = httpx.MockTransport(timeout)
            real_client = httpx.AsyncClient
            with patch(
                "app.engine.evaluation_engine.httpx.AsyncClient",
                side_effect=lambda **kwargs: real_client(transport=transport, **kwargs),
            ):
                result = await engine._evaluate_single_item(
                    experiment, self.build_item(), "https://model.invalid/run", None
                )
            self.assertEqual(result.status, "FAILED")
            self.assertEqual(result.error_message, "请求超时")

        async def test_execute_never_exceeds_experiment_concurrency(self):
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session, item_count=5)
                items = [
                    await self.add_item(session, dataset, seq=index)
                    for index in range(1, 6)
                ]
                experiment = await self.add_experiment(
                    session, model, dataset, status="RUNNING", concurrency=2
                )
                await session.commit()
                active = 0
                maximum_active = 0

                async def evaluate(**kwargs):
                    nonlocal active, maximum_active
                    active += 1
                    maximum_active = max(maximum_active, active)
                    await asyncio.sleep(0.01)
                    active -= 1
                    item = kwargs["item"]
                    return ExperimentResult(
                        experiment_id=experiment.id,
                        dataset_item_id=item.id,
                        seq=item.seq,
                        input_text=item.input_text,
                        expected_output=item.expected_output,
                        actual_output="ok",
                        response_time_ms=5,
                        status="SUCCESS",
                    )

                engine = EvaluationEngine()
                with patch.object(
                    engine, "_load_dataset_items", new=AsyncMock(return_value=items)
                ), patch.object(
                    engine, "_evaluate_single_item", new=AsyncMock(side_effect=evaluate)
                ):
                    await engine._execute(session, experiment.id)
                count = (
                    await session.execute(select(func.count()).select_from(ExperimentResult))
                ).scalar_one()
                self.assertLessEqual(maximum_active, 2)
                self.assertEqual(count, 5)

        async def test_finalize_two_samples_uses_nearest_rank_p99(self):
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                experiment = await self.add_experiment(session, model, dataset)
                await session.commit()
                results = [
                    ExperimentResult(
                        experiment_id=experiment.id,
                        dataset_item_id=index,
                        seq=index,
                        input_text="input",
                        status="SUCCESS",
                        response_time_ms=value,
                    )
                    for index, value in enumerate((10, 99), start=1)
                ]
                await EvaluationEngine()._finalize(session, experiment.id, results)
                await session.refresh(experiment)
                self.assertEqual(experiment.p99_ms, 99)

        async def test_finalize_one_sample_keeps_its_latency(self):
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                experiment = await self.add_experiment(session, model, dataset)
                await session.commit()
                result = ExperimentResult(
                    experiment_id=experiment.id,
                    dataset_item_id=1,
                    seq=1,
                    input_text="input",
                    status="SUCCESS",
                    response_time_ms=17,
                )
                await EvaluationEngine()._finalize(session, experiment.id, [result])
                await session.refresh(experiment)
                self.assertEqual(experiment.p99_ms, 17)
    '''
).strip() + "\n"


UTILS_TESTS = textwrap.dedent(
    r'''
    from sqlalchemy import func, select
    from pydantic import ValidationError

    from app.models.audit_log import AuditLog
    from app.models.model import Model
    from app.utils.audit import record_audit_log
    from app.utils.crypto import ApiKeyCrypto
    from app.utils.pagination import PageParams, PageResult
    from app.utils.response import ApiResponse
    from tests.helpers import DatabaseTestCase


    class UtilityTests(DatabaseTestCase):
        def test_page_params_compute_offset_and_limit(self):
            params = PageParams(page=3, page_size=25)
            self.assertEqual((params.offset, params.limit), (50, 25))

        def test_page_params_reject_zero_page(self):
            with self.assertRaises(ValidationError):
                PageParams(page=0)

        def test_page_params_reject_more_than_one_hundred_rows(self):
            with self.assertRaises(ValidationError):
                PageParams(page_size=101)

        def test_page_result_preserves_real_items(self):
            result = PageResult[int].create([1, 2], 2, 1, 20)
            self.assertEqual(result.model_dump()["items"], [1, 2])

        def test_crypto_round_trip_and_mask(self):
            crypto = ApiKeyCrypto(b"x" * 32)
            encrypted = crypto.encrypt("abcdef1234")
            self.assertEqual(crypto.decrypt(encrypted), "abcdef1234")
            self.assertEqual(crypto.mask("abcdef1234"), "******1234")

        def test_crypto_rejects_invalid_key_length(self):
            with self.assertRaises(ValueError):
                ApiKeyCrypto(b"short")

        def test_api_response_success_and_error_keep_contract(self):
            self.assertEqual(ApiResponse.success({"ok": True}).code, 0)
            error = ApiResponse.error(40001, "bad")
            self.assertEqual((error.code, error.data), (40001, None))

        async def test_audit_log_is_written_to_real_session(self):
            async with self.Session() as session:
                await record_audit_log(
                    session, "tester", "CREATE", "model", 9, {"name": "m"}
                )
                await session.commit()
                count = (
                    await session.execute(select(func.count()).select_from(AuditLog))
                ).scalar_one()
                self.assertEqual(count, 1)

        async def test_rollback_is_isolated_from_a_new_session(self):
            async with self.Session() as first:
                first.add(
                    Model(
                        name="rolled-back",
                        model_type="LLM",
                        status="ACTIVE",
                        created_by="tester",
                    )
                )
                await first.flush()
                await first.rollback()
            async with self.Session() as second:
                count = (
                    await second.execute(select(func.count()).select_from(Model))
                ).scalar_one()
                self.assertEqual(count, 0)
    '''
).strip() + "\n"


MODEL_SERVICE_MATRIX_TESTS = _render_case_module(
    r'''
    from datetime import datetime

    from sqlalchemy import func, select

    from app.models import Experiment, Model
    from app.models.audit_log import AuditLog
    from app.schemas.model import ModelCreate, ModelUpdate
    from app.services import model_service
    from app.utils.response import AppException, ErrorCode
    from tests.helpers import DatabaseTestCase
    ''',
    "ModelServiceBusinessMatrixTests(DatabaseTestCase)",
    (
        (
            "create_without_api_key_keeps_storage_empty",
            '''
            async with self.Session() as session:
                response = await model_service.create_model(
                    session,
                    ModelCreate(name="no-key", model_type="OTHER", version="v2.1.0"),
                    "alice",
                )
                stored = await session.get(Model, response.id)
                self.assertIsNone(response.api_key_masked)
                self.assertIsNone(stored.api_key_enc)
                self.assertEqual(stored.created_by, "alice")
            ''',
        ),
        (
            "duplicate_active_name_is_rejected",
            '''
            async with self.Session() as session:
                await model_service.create_model(
                    session, ModelCreate(name="duplicate", model_type="LLM"), "alice"
                )
                with self.assertRaises(AppException) as caught:
                    await model_service.create_model(
                        session, ModelCreate(name="duplicate", model_type="OTHER"), "bob"
                    )
                self.assertEqual(caught.exception.code, ErrorCode.NAME_EXISTS)
            ''',
        ),
        (
            "get_existing_model_returns_real_row",
            '''
            async with self.Session() as session:
                model = await self.add_model(session, name="existing")
                await session.commit()
                loaded = await model_service.get_model(session, model.id)
                self.assertEqual((loaded.id, loaded.name), (model.id, "existing"))
            ''',
        ),
        (
            "update_all_mutable_fields_and_encrypt_key",
            '''
            async with self.Session() as session:
                model = await self.add_model(session, name="mutable")
                await session.commit()
                response = await model_service.update_model(
                    session,
                    model.id,
                    ModelUpdate(
                        model_type="CLASSIFICATION",
                        version="v2.3.4",
                        description="reviewed",
                        endpoint_url="https://changed.invalid",
                        api_key="replacement-key",
                        status="DISABLED",
                    ),
                    "reviewer",
                )
                self.assertEqual(response.model_type, "CLASSIFICATION")
                self.assertEqual(response.version, "v2.3.4")
                self.assertEqual(response.status, "DISABLED")
                self.assertTrue(response.api_key_masked.endswith("-key"))
            ''',
        ),
        (
            "partial_update_preserves_untouched_business_fields",
            '''
            async with self.Session() as session:
                model = await self.add_model(session, name="partial")
                await session.commit()
                response = await model_service.update_model(
                    session, model.id, ModelUpdate(description="only this"), "reviewer"
                )
                self.assertEqual(response.name, "partial")
                self.assertEqual(response.model_type, "LLM")
                self.assertEqual(response.version, "v1.0.0")
                self.assertEqual(response.description, "only this")
            ''',
        ),
        (
            "list_applies_type_and_status_filters_together",
            '''
            async with self.Session() as session:
                session.add_all([
                    Model(name="active-llm", model_type="LLM", status="ACTIVE", created_by="t"),
                    Model(name="disabled-llm", model_type="LLM", status="DISABLED", created_by="t"),
                    Model(name="active-other", model_type="OTHER", status="ACTIVE", created_by="t"),
                ])
                await session.commit()
                rows, total = await model_service.list_models(
                    session, model_type="LLM", status="ACTIVE"
                )
                self.assertEqual(total, 1)
                self.assertEqual([row.name for row in rows], ["active-llm"])
            ''',
        ),
        (
            "list_excludes_soft_deleted_rows",
            '''
            async with self.Session() as session:
                visible = await self.add_model(session, name="visible")
                hidden = await self.add_model(session, name="hidden")
                hidden.deleted_at = datetime.utcnow()
                await session.commit()
                rows, total = await model_service.list_models(session)
                self.assertEqual(total, 1)
                self.assertEqual([row.id for row in rows], [visible.id])
            ''',
        ),
        (
            "second_page_respects_page_size",
            '''
            async with self.Session() as session:
                for name in ("page-a", "page-b", "page-c"):
                    await self.add_model(session, name=name)
                await session.commit()
                rows, total = await model_service.list_models(session, page=2, page_size=2)
                self.assertEqual(total, 3)
                self.assertEqual(len(rows), 1)
            ''',
        ),
        (
            "delete_without_running_experiment_writes_audit_log",
            '''
            async with self.Session() as session:
                model = await self.add_model(session, name="retired")
                await session.commit()
                await model_service.delete_model(session, model.id, "owner")
                count = (
                    await session.execute(
                        select(func.count()).select_from(AuditLog).where(AuditLog.action == "DELETE")
                    )
                ).scalar_one()
                self.assertIsNotNone(model.deleted_at)
                self.assertEqual(count, 1)
            ''',
        ),
        (
            "detail_limits_recent_history_to_ten_experiments",
            '''
            async with self.Session() as session:
                model = await self.add_model(session, name="history")
                dataset = await self.add_dataset(session)
                for index in range(12):
                    experiment = Experiment(
                        name=f"history-{index}", model_id=model.id, dataset_id=dataset.id,
                        concurrency=1, timeout_seconds=5, status="COMPLETED", created_by="t",
                    )
                    session.add(experiment)
                await session.commit()
                detail = await model_service.get_model_with_experiments(session, model.id)
                self.assertEqual(detail["name"], "history")
                self.assertEqual(len(detail["recent_experiments"]), 10)
            ''',
        ),
    ),
    asynchronous=True,
)


DATASET_SERVICE_MATRIX_TESTS = _render_case_module(
    r'''
    from datetime import datetime

    from sqlalchemy import func, select

    from app.models import Dataset, Experiment
    from app.models.audit_log import AuditLog
    from app.schemas.dataset import DatasetCreate, DatasetUpdate
    from app.services import dataset_service
    from app.utils.response import AppException, ErrorCode
    from tests.helpers import DatabaseTestCase
    ''',
    "DatasetServiceBusinessMatrixTests(DatabaseTestCase)",
    (
        (
            "create_initializes_zero_count_and_audit",
            '''
            async with self.Session() as session:
                response = await dataset_service.create_dataset(
                    session,
                    DatasetCreate(name="fresh", version="v1.2.0", description="new"),
                    "alice",
                )
                count = (await session.execute(select(func.count()).select_from(AuditLog))).scalar_one()
                self.assertEqual(response.item_count, 0)
                self.assertEqual(response.created_by, "alice")
                self.assertEqual(count, 1)
            ''',
        ),
        (
            "duplicate_active_name_is_rejected",
            '''
            async with self.Session() as session:
                await dataset_service.create_dataset(
                    session, DatasetCreate(name="duplicate"), "alice"
                )
                with self.assertRaises(AppException) as caught:
                    await dataset_service.create_dataset(
                        session, DatasetCreate(name="duplicate"), "bob"
                    )
                self.assertEqual(caught.exception.code, ErrorCode.NAME_EXISTS)
            ''',
        ),
        (
            "get_existing_dataset_returns_real_row",
            '''
            async with self.Session() as session:
                dataset = await self.add_dataset(session, name="existing")
                await session.commit()
                loaded = await dataset_service.get_dataset(session, dataset.id)
                self.assertEqual((loaded.id, loaded.name), (dataset.id, "existing"))
            ''',
        ),
        (
            "get_missing_dataset_raises_not_found",
            '''
            async with self.Session() as session:
                with self.assertRaises(AppException) as caught:
                    await dataset_service.get_dataset(session, 404)
                self.assertEqual(caught.exception.code, ErrorCode.NOT_FOUND)
            ''',
        ),
        (
            "list_filters_name_and_hides_deleted_rows",
            '''
            async with self.Session() as session:
                kept = await self.add_dataset(session, name="quality-alpha")
                hidden = await self.add_dataset(session, name="quality-hidden")
                await self.add_dataset(session, name="other")
                hidden.deleted_at = datetime.utcnow()
                await session.commit()
                rows, total = await dataset_service.list_datasets(session, name="quality")
                self.assertEqual(total, 1)
                self.assertEqual([row.id for row in rows], [kept.id])
            ''',
        ),
        (
            "update_changes_name_version_and_description",
            '''
            async with self.Session() as session:
                dataset = await self.add_dataset(session, name="before")
                await session.commit()
                response = await dataset_service.update_dataset(
                    session,
                    dataset.id,
                    DatasetUpdate(name="after", version="v2.0.0", description="reviewed"),
                    "reviewer",
                )
                self.assertEqual((response.name, response.version), ("after", "v2.0.0"))
                self.assertEqual(response.description, "reviewed")
            ''',
        ),
        (
            "rename_to_existing_name_is_rejected",
            '''
            async with self.Session() as session:
                first = await self.add_dataset(session, name="first")
                await self.add_dataset(session, name="taken")
                await session.commit()
                with self.assertRaises(AppException) as caught:
                    await dataset_service.update_dataset(
                        session, first.id, DatasetUpdate(name="taken"), "reviewer"
                    )
                self.assertEqual(caught.exception.code, ErrorCode.NAME_EXISTS)
            ''',
        ),
        (
            "delete_without_running_experiment_soft_deletes",
            '''
            async with self.Session() as session:
                dataset = await self.add_dataset(session, name="retired")
                await session.commit()
                await dataset_service.delete_dataset(session, dataset.id, "owner")
                self.assertIsNotNone(dataset.deleted_at)
                self.assertEqual(dataset.updated_by, "owner")
            ''',
        ),
        (
            "completed_experiment_does_not_block_dataset_delete",
            '''
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session, name="completed-only")
                await self.add_experiment(session, model, dataset, status="COMPLETED")
                await session.commit()
                await dataset_service.delete_dataset(session, dataset.id, "owner")
                self.assertIsNotNone(dataset.deleted_at)
            ''',
        ),
        (
            "detail_limits_recent_history_to_ten_experiments",
            '''
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session, name="history")
                for index in range(12):
                    session.add(Experiment(
                        name=f"dataset-history-{index}", model_id=model.id,
                        dataset_id=dataset.id, concurrency=1, timeout_seconds=5,
                        status="COMPLETED", created_by="t",
                    ))
                await session.commit()
                detail = await dataset_service.get_dataset_with_experiments(session, dataset.id)
                self.assertEqual(detail["name"], "history")
                self.assertEqual(len(detail["recent_experiments"]), 10)
            ''',
        ),
    ),
    asynchronous=True,
)


EXPERIMENT_SERVICE_MATRIX_TESTS = _render_case_module(
    r'''
    from datetime import datetime
    from unittest.mock import patch

    from app.engine.evaluation_engine import evaluation_engine
    from app.models import ExperimentResult
    from app.services import experiment_service
    from app.utils.response import AppException, ErrorCode
    from tests.helpers import DatabaseTestCase
    ''',
    "ExperimentServiceBusinessMatrixTests(DatabaseTestCase)",
    (
        (
            "list_filters_by_name",
            '''
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                await self.add_experiment(session, model, dataset, status="COMPLETED")
                second = await self.add_experiment(session, model, dataset, status="FAILED")
                second.name = "target-experiment"
                await session.commit()
                rows, total = await experiment_service.list_experiments(session, name="target")
                self.assertEqual(total, 1)
                self.assertEqual(rows[0]["name"], "target-experiment")
            ''',
        ),
        (
            "list_filters_by_status",
            '''
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                await self.add_experiment(session, model, dataset, status="RUNNING")
                await self.add_experiment(session, model, dataset, status="COMPLETED")
                await session.commit()
                rows, total = await experiment_service.list_experiments(session, status="RUNNING")
                self.assertEqual(total, 1)
                self.assertEqual(rows[0]["status"], "RUNNING")
            ''',
        ),
        (
            "list_marks_soft_deleted_model_and_dataset",
            '''
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                await self.add_experiment(session, model, dataset, status="COMPLETED")
                model.deleted_at = datetime.utcnow()
                dataset.deleted_at = datetime.utcnow()
                await session.commit()
                rows, total = await experiment_service.list_experiments(session)
                self.assertEqual(total, 1)
                self.assertTrue(rows[0]["model_deleted"])
                self.assertTrue(rows[0]["dataset_deleted"])
            ''',
        ),
        (
            "get_existing_experiment_returns_real_row",
            '''
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                experiment = await self.add_experiment(session, model, dataset, status="PENDING")
                await session.commit()
                loaded = await experiment_service.get_experiment(session, experiment.id)
                self.assertEqual((loaded.id, loaded.status), (experiment.id, "PENDING"))
            ''',
        ),
        (
            "get_missing_experiment_raises_not_found",
            '''
            async with self.Session() as session:
                with self.assertRaises(AppException) as caught:
                    await experiment_service.get_experiment(session, 404)
                self.assertEqual(caught.exception.code, ErrorCode.NOT_FOUND)
            ''',
        ),
        (
            "detail_filters_failed_results_and_pages",
            '''
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                items = [await self.add_item(session, dataset, seq=i) for i in range(1, 4)]
                experiment = await self.add_experiment(session, model, dataset, status="COMPLETED")
                for item, status in zip(items, ("SUCCESS", "FAILED", "FAILED")):
                    session.add(ExperimentResult(
                        experiment_id=experiment.id, dataset_item_id=item.id, seq=item.seq,
                        input_text=item.input_text, status=status,
                        error_message="failed" if status == "FAILED" else None,
                    ))
                await session.commit()
                detail = await experiment_service.get_experiment_detail(
                    session, experiment.id, page=2, page_size=1, result_status="FAILED"
                )
                self.assertEqual(detail["results"]["total"], 2)
                self.assertEqual(detail["results"]["items"][0]["seq"], 3)
            ''',
        ),
        (
            "results_filter_success_preserves_snapshot_fields",
            '''
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                item = await self.add_item(session, dataset, seq=4, input_text="snapshot-input")
                experiment = await self.add_experiment(session, model, dataset, status="COMPLETED")
                session.add(ExperimentResult(
                    experiment_id=experiment.id, dataset_item_id=item.id, seq=4,
                    input_text="snapshot-input", expected_output="expected",
                    actual_output="actual", response_time_ms=8, status="SUCCESS",
                ))
                await session.commit()
                rows, total = await experiment_service.get_experiment_results(
                    session, experiment.id, result_status="SUCCESS"
                )
                self.assertEqual(total, 1)
                self.assertEqual(rows[0]["actual_output"], "actual")
            ''',
        ),
        (
            "export_orders_results_by_sequence",
            '''
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                items = [await self.add_item(session, dataset, seq=i) for i in (2, 1)]
                experiment = await self.add_experiment(session, model, dataset, status="COMPLETED")
                for item in items:
                    session.add(ExperimentResult(
                        experiment_id=experiment.id, dataset_item_id=item.id, seq=item.seq,
                        input_text=item.input_text, status="SUCCESS",
                    ))
                await session.commit()
                rows = await experiment_service.export_experiment_results(session, experiment.id)
                self.assertEqual([row["seq"] for row in rows], [1, 2])
            ''',
        ),
        (
            "cancel_registered_running_task_returns_cancelled_receipt",
            '''
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                experiment = await self.add_experiment(session, model, dataset, status="RUNNING")
                await session.commit()
                with patch.object(evaluation_engine, "cancel", return_value=True) as cancel:
                    receipt = await experiment_service.cancel_experiment(
                        session, experiment.id, "reviewer"
                    )
                cancel.assert_called_once_with(experiment.id)
                self.assertEqual(receipt["status"], "CANCELLED")
            ''',
        ),
        (
            "cancel_unregistered_running_task_forces_database_status",
            '''
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                experiment = await self.add_experiment(session, model, dataset, status="RUNNING")
                await session.commit()
                with patch.object(evaluation_engine, "cancel", return_value=False):
                    receipt = await experiment_service.cancel_experiment(
                        session, experiment.id, "reviewer"
                    )
                self.assertEqual(receipt["status"], "CANCELLED")
                self.assertEqual(experiment.status, "CANCELLED")
                self.assertIsNotNone(experiment.completed_at)
            ''',
        ),
    ),
    asynchronous=True,
)


ENGINE_MATRIX_TESTS = _render_case_module(
    r'''
    import asyncio
    from unittest.mock import AsyncMock, patch

    import httpx

    from app.engine import evaluation_engine as engine_module
    from app.engine.evaluation_engine import EvaluationEngine
    from app.models import ExperimentResult
    from tests.helpers import DatabaseTestCase
    ''',
    "EvaluationEngineBusinessMatrixTests(DatabaseTestCase)",
    (
        (
            "cancel_unknown_task_returns_false",
            '''
            engine_module._running_tasks.clear()
            self.assertFalse(EvaluationEngine().cancel(999))
            ''',
        ),
        (
            "cancel_completed_task_returns_false",
            '''
            task = asyncio.create_task(asyncio.sleep(0))
            await task
            engine_module._running_tasks[7] = task
            try:
                self.assertFalse(EvaluationEngine().cancel(7))
            finally:
                engine_module._running_tasks.clear()
            ''',
        ),
        (
            "cancel_live_task_requests_cancellation",
            '''
            task = asyncio.create_task(asyncio.sleep(30))
            engine_module._running_tasks[8] = task
            try:
                self.assertTrue(EvaluationEngine().cancel(8))
                with self.assertRaises(asyncio.CancelledError):
                    await task
            finally:
                engine_module._running_tasks.clear()
            ''',
        ),
        (
            "start_registers_named_task_then_callback_removes_it",
            '''
            gate = asyncio.Event()
            engine = EvaluationEngine()

            async def bounded_run(experiment_id):
                self.assertEqual(experiment_id, 9)
                await gate.wait()

            with patch.object(engine, "_run", side_effect=bounded_run):
                await engine.start(9)
                task = engine_module._running_tasks[9]
                self.assertEqual(task.get_name(), "eval_experiment_9")
                gate.set()
                await task
                await asyncio.sleep(0)
            self.assertNotIn(9, engine_module._running_tasks)
            ''',
        ),
        (
            "json_without_output_falls_back_to_response_text",
            '''
            engine = EvaluationEngine()
            item = await self._item_for_engine()
            experiment = type("ExperimentStub", (), {"id": 1, "timeout_seconds": 5})()
            transport = httpx.MockTransport(
                lambda request: httpx.Response(200, json={"message": "ok"}, request=request)
            )
            real_client = httpx.AsyncClient
            with patch(
                "app.engine.evaluation_engine.httpx.AsyncClient",
                side_effect=lambda **kwargs: real_client(transport=transport, **kwargs),
            ):
                result = await engine._evaluate_single_item(
                    experiment, item, "https://model.invalid/run", None
                )
            self.assertIn('"message":"ok"', result.actual_output.replace(" ", ""))
            ''',
        ),
        (
            "null_output_is_preserved_as_none",
            '''
            engine = EvaluationEngine()
            item = await self._item_for_engine()
            experiment = type("ExperimentStub", (), {"id": 1, "timeout_seconds": 5})()
            transport = httpx.MockTransport(
                lambda request: httpx.Response(200, json={"output": None}, request=request)
            )
            real_client = httpx.AsyncClient
            with patch(
                "app.engine.evaluation_engine.httpx.AsyncClient",
                side_effect=lambda **kwargs: real_client(transport=transport, **kwargs),
            ):
                result = await engine._evaluate_single_item(
                    experiment, item, "https://model.invalid/run", None
                )
            self.assertIsNone(result.actual_output)
            self.assertEqual(result.status, "SUCCESS")
            ''',
        ),
        (
            "api_key_becomes_bearer_header_in_mock_request",
            '''
            observed = {}

            def respond(request):
                observed["authorization"] = request.headers.get("Authorization")
                return httpx.Response(200, json={"output": "ok"}, request=request)

            engine = EvaluationEngine()
            item = await self._item_for_engine()
            experiment = type("ExperimentStub", (), {"id": 1, "timeout_seconds": 5})()
            transport = httpx.MockTransport(respond)
            real_client = httpx.AsyncClient
            with patch(
                "app.engine.evaluation_engine.httpx.AsyncClient",
                side_effect=lambda **kwargs: real_client(transport=transport, **kwargs),
            ):
                await engine._evaluate_single_item(
                    experiment, item, "https://model.invalid/run", "secret"
                )
            self.assertEqual(observed["authorization"], "Bearer secret")
            ''',
        ),
        (
            "unexpected_mock_transport_error_becomes_failed_result",
            '''
            def fail(request):
                raise ValueError("malformed response")

            engine = EvaluationEngine()
            item = await self._item_for_engine()
            experiment = type("ExperimentStub", (), {"id": 1, "timeout_seconds": 5})()
            transport = httpx.MockTransport(fail)
            real_client = httpx.AsyncClient
            with patch(
                "app.engine.evaluation_engine.httpx.AsyncClient",
                side_effect=lambda **kwargs: real_client(transport=transport, **kwargs),
            ):
                result = await engine._evaluate_single_item(
                    experiment, item, "https://model.invalid/run", None
                )
            self.assertEqual(result.status, "FAILED")
            self.assertEqual(result.error_message, "malformed response")
            ''',
        ),
        (
            "finalize_mixed_results_counts_failures_and_percentiles",
            '''
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                experiment = await self.add_experiment(session, model, dataset, status="RUNNING")
                await session.commit()
                results = [
                    ExperimentResult(
                        experiment_id=experiment.id, dataset_item_id=index, seq=index,
                        input_text="input", status="SUCCESS", response_time_ms=value,
                    )
                    for index, value in enumerate((10, 20, 30, 40), start=1)
                ]
                results.append(ValueError("worker failed"))
                await EvaluationEngine()._finalize(session, experiment.id, results)
                await session.refresh(experiment)
                self.assertEqual((experiment.total_count, experiment.success_count), (5, 4))
                self.assertEqual(experiment.failed_count, 1)
                self.assertEqual(experiment.avg_response_ms, 25)
                self.assertEqual(experiment.p99_ms, 40)
            ''',
        ),
        (
            "finalize_empty_results_completes_with_null_latencies",
            '''
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                experiment = await self.add_experiment(session, model, dataset, status="RUNNING")
                await session.commit()
                await EvaluationEngine()._finalize(session, experiment.id, [])
                await session.refresh(experiment)
                self.assertEqual(experiment.status, "COMPLETED")
                self.assertEqual((experiment.total_count, experiment.success_count), (0, 0))
                self.assertIsNone(experiment.p99_ms)
            ''',
        ),
        (
            "execute_missing_experiment_returns_without_writes",
            '''
            async with self.Session() as session:
                await EvaluationEngine()._execute(session, 999)
                self.assertEqual(len(session.new), 0)
            ''',
        ),
        (
            "execute_missing_model_marks_experiment_failed",
            '''
            async with self.Session() as session:
                dataset = await self.add_dataset(session)
                from app.models import Experiment
                experiment = Experiment(
                    name="orphan-model", model_id=999, dataset_id=dataset.id,
                    concurrency=1, timeout_seconds=5, status="RUNNING", created_by="t",
                )
                session.add(experiment)
                await session.commit()
                await EvaluationEngine()._execute(session, experiment.id)
                await session.refresh(experiment)
                self.assertEqual(experiment.status, "FAILED")
                self.assertIsNotNone(experiment.completed_at)
            ''',
        ),
        (
            "execute_empty_dataset_completes_without_http",
            '''
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session, item_count=0)
                experiment = await self.add_experiment(session, model, dataset, status="RUNNING")
                await session.commit()
                await EvaluationEngine()._execute(session, experiment.id)
                await session.refresh(experiment)
                self.assertEqual(experiment.status, "COMPLETED")
                self.assertEqual((experiment.total_count, experiment.success_count), (0, 0))
            ''',
        ),
        (
            "load_dataset_items_returns_sequence_order",
            '''
            async with self.Session() as session:
                dataset = await self.add_dataset(session, item_count=3)
                for seq in (3, 1, 2):
                    await self.add_item(session, dataset, seq=seq, input_text=f"item-{seq}")
                await session.commit()
                rows = await EvaluationEngine()._load_dataset_items(session, dataset.id)
                self.assertEqual([row.seq for row in rows], [1, 2, 3])
            ''',
        ),
        (
            "update_status_running_does_not_set_completion_time",
            '''
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                experiment = await self.add_experiment(session, model, dataset, status="PENDING")
                await session.commit()
                await EvaluationEngine()._update_status(
                    session, experiment.id, engine_module.ExperimentStatus.RUNNING
                )
                await session.refresh(experiment)
                self.assertEqual(experiment.status, "RUNNING")
                self.assertIsNone(experiment.completed_at)
            ''',
        ),
        (
            "update_status_cancelled_sets_completion_time",
            '''
            async with self.Session() as session:
                model = await self.add_model(session)
                dataset = await self.add_dataset(session)
                experiment = await self.add_experiment(session, model, dataset, status="RUNNING")
                await session.commit()
                await EvaluationEngine()._update_status(
                    session, experiment.id, engine_module.ExperimentStatus.CANCELLED
                )
                await session.refresh(experiment)
                self.assertEqual(experiment.status, "CANCELLED")
                self.assertIsNotNone(experiment.completed_at)
            ''',
        ),
    ),
    asynchronous=True,
)


UTILITY_BOUNDARY_TESTS = _render_case_module(
    r'''
    import json
    import unittest

    from pydantic import ValidationError

    from app.schemas.dataset import DatasetCreate
    from app.schemas.experiment import ExperimentCreate
    from app.schemas.model import ModelCreate, ModelUpdate
    from app.services import dataset_service
    from app.utils.crypto import ApiKeyCrypto
    from app.utils.pagination import PageParams, PageResult
    ''',
    "SchemaAndUtilityBoundaryTests(unittest.TestCase)",
    (
        ("model_type_llm_is_accepted", 'self.assertEqual(ModelCreate(name="m", model_type="LLM").model_type, "LLM")'),
        ("model_type_classification_is_accepted", 'self.assertEqual(ModelCreate(name="m", model_type="CLASSIFICATION").model_type, "CLASSIFICATION")'),
        ("model_type_regression_is_accepted", 'self.assertEqual(ModelCreate(name="m", model_type="REGRESSION").model_type, "REGRESSION")'),
        ("model_type_other_is_accepted", 'self.assertEqual(ModelCreate(name="m", model_type="OTHER").model_type, "OTHER")'),
        ("model_type_chat_is_rejected", 'with self.assertRaises(ValidationError):\n    ModelCreate(name="m", model_type="CHAT")'),
        ("model_type_empty_is_rejected", 'with self.assertRaises(ValidationError):\n    ModelCreate(name="m", model_type="")'),
        ("model_type_lowercase_llm_is_rejected", 'with self.assertRaises(ValidationError):\n    ModelCreate(name="m", model_type="llm")'),
        ("model_type_numeric_text_is_rejected", 'with self.assertRaises(ValidationError):\n    ModelCreate(name="m", model_type="123")'),
        ("model_version_semver_is_accepted", 'self.assertEqual(ModelCreate(name="m", model_type="LLM", version="v10.20.30").version, "v10.20.30")'),
        ("model_version_none_is_accepted", 'self.assertIsNone(ModelCreate(name="m", model_type="LLM", version=None).version)'),
        ("model_version_missing_prefix_is_rejected", 'with self.assertRaises(ValidationError):\n    ModelCreate(name="m", model_type="LLM", version="1.2.3")'),
        ("model_version_prerelease_is_rejected", 'with self.assertRaises(ValidationError):\n    ModelCreate(name="m", model_type="LLM", version="v1.2.3-rc1")'),
        ("model_update_active_status_is_accepted", 'self.assertEqual(ModelUpdate(status="ACTIVE").status, "ACTIVE")'),
        ("model_update_disabled_status_is_accepted", 'self.assertEqual(ModelUpdate(status="DISABLED").status, "DISABLED")'),
        ("model_update_pending_status_is_rejected", 'with self.assertRaises(ValidationError):\n    ModelUpdate(status="PENDING")'),
        ("model_update_lowercase_status_is_rejected", 'with self.assertRaises(ValidationError):\n    ModelUpdate(status="active")'),
        ("dataset_version_semver_is_accepted", 'self.assertEqual(DatasetCreate(name="d", version="v0.0.1").version, "v0.0.1")'),
        ("dataset_version_none_is_accepted", 'self.assertIsNone(DatasetCreate(name="d").version)'),
        ("dataset_version_missing_patch_is_rejected", 'with self.assertRaises(ValidationError):\n    DatasetCreate(name="d", version="v1.2")'),
        ("dataset_version_suffix_is_rejected", 'with self.assertRaises(ValidationError):\n    DatasetCreate(name="d", version="v1.2.3-beta")'),
        ("experiment_concurrency_one_is_accepted", 'self.assertEqual(ExperimentCreate(name="e", model_id=1, dataset_id=1, concurrency=1).concurrency, 1)'),
        ("experiment_concurrency_twenty_is_accepted", 'self.assertEqual(ExperimentCreate(name="e", model_id=1, dataset_id=1, concurrency=20).concurrency, 20)'),
        ("experiment_concurrency_zero_is_rejected", 'with self.assertRaises(ValidationError):\n    ExperimentCreate(name="e", model_id=1, dataset_id=1, concurrency=0)'),
        ("experiment_concurrency_twenty_one_is_rejected", 'with self.assertRaises(ValidationError):\n    ExperimentCreate(name="e", model_id=1, dataset_id=1, concurrency=21)'),
        ("experiment_timeout_five_is_accepted", 'self.assertEqual(ExperimentCreate(name="e", model_id=1, dataset_id=1, timeout_seconds=5).timeout_seconds, 5)'),
        ("experiment_timeout_three_hundred_is_accepted", 'self.assertEqual(ExperimentCreate(name="e", model_id=1, dataset_id=1, timeout_seconds=300).timeout_seconds, 300)'),
        ("parse_empty_array_is_valid", 'self.assertEqual(dataset_service._parse_json_file(b"[]"), [])'),
        ("parse_unicode_input_is_preserved", 'payload = json.dumps([{"input": "你好", "expected_output": "世界"}], ensure_ascii=False).encode()\nself.assertEqual(dataset_service._parse_json_file(payload)[0]["input"], "你好")'),
        ("parse_non_array_is_rejected", 'with self.assertRaises(Exception) as caught:\n    dataset_service._parse_json_file(b"{}")\nself.assertIn("数组", str(caught.exception))'),
        ("parse_missing_input_is_rejected", 'with self.assertRaises(Exception) as caught:\n    dataset_service._parse_json_file(b"[{}]")\nself.assertIn("input", str(caught.exception))'),
        ("parse_numeric_input_is_rejected", 'with self.assertRaises(Exception) as caught:\n    dataset_service._parse_json_file(b"[{\\"input\\": 7}]")\nself.assertIn("字符串", str(caught.exception))'),
        ("crypto_mask_empty_is_empty", 'self.assertEqual(ApiKeyCrypto.mask(""), "")'),
        ("crypto_mask_four_characters_is_fixed", 'self.assertEqual(ApiKeyCrypto.mask("abcd"), "****")'),
        ("crypto_mask_short_value_is_fixed", 'self.assertEqual(ApiKeyCrypto.mask("xy"), "****")'),
        ("crypto_mask_long_value_keeps_last_four", 'self.assertEqual(ApiKeyCrypto.mask("abcdefgh"), "****efgh")'),
        ("pagination_first_page_has_zero_offset", 'self.assertEqual(PageParams(page=1, page_size=1).offset, 0)'),
        ("pagination_hundred_rows_is_allowed", 'self.assertEqual(PageParams(page=1, page_size=100).limit, 100)'),
        ("pagination_zero_page_size_is_rejected", 'with self.assertRaises(ValidationError):\n    PageParams(page_size=0)'),
        ("page_result_keeps_business_total", 'result = PageResult[str].create(["a"], total=7, page=2, page_size=1)\nself.assertEqual((result.total, result.page, result.items), (7, 2, ["a"]))'),
    ),
)


RUNNER = textwrap.dedent(
    r'''
    import json
    import os
    import platform
    import socket
    import sys
    import unittest
    import coverage
    from io import StringIO
    from pathlib import Path


    ROOT = Path(__file__).resolve().parent
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))


    def flatten(suite):
        for item in suite:
            if isinstance(item, unittest.TestSuite):
                yield from flatten(item)
            else:
                yield item


    class RecordingResult(unittest.TextTestResult):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.passed_ids = []

        def addSuccess(self, test):
            super().addSuccess(test)
            self.passed_ids.append(test.id())


    manifest = json.loads((ROOT / "test-manifest.json").read_text(encoding="utf-8"))
    stream = StringIO()
    runner = unittest.TextTestRunner(
        stream=stream, verbosity=2, resultclass=RecordingResult
    )
    coverage_run = coverage.Coverage(
        source=["app.services", "app.engine", "app.utils"],
        data_file=None,
    )
    original_connect = socket.socket.connect


    def blocked_connect(self, address):
        host = address[0] if isinstance(address, tuple) and address else None
        if host in {"127.0.0.1", "::1", "localhost"}:
            return original_connect(self, address)
        raise RuntimeError(
            "non-loopback direct network access is blocked in the fixed TC-04 test runner"
        )


    collected_ids = []


    def discover_and_run():
        global collected_ids
        suite = unittest.defaultTestLoader.discover("tests")
        collected_ids = sorted(test.id() for test in flatten(suite))
        return runner.run(suite)


    socket.socket.connect = blocked_connect
    try:
        coverage_run.start()
        result = discover_and_run()
    finally:
        coverage_run.stop()
        socket.socket.connect = original_connect

    target_paths = sorted(
        [*Path("app/services").glob("*.py"), Path("app/engine/evaluation_engine.py"),
         *Path("app/utils").glob("*.py")]
    )
    target_paths = [path for path in target_paths if path.name != "__init__.py"]
    coverage_files = []
    total_statements = 0
    total_covered = 0
    for relative_path in target_paths:
        absolute_path = relative_path.resolve()
        _, statements, _, missing, _ = coverage_run.analysis2(str(absolute_path))
        covered = len(statements) - len(missing)
        total_statements += len(statements)
        total_covered += covered
        coverage_files.append(
            {
                "file": relative_path.as_posix(),
                "statements": len(statements),
                "covered_statements": covered,
                "percent": round(100 * covered / max(1, len(statements)), 1),
            }
        )

    failure_ids = sorted(test.id() for test, _ in result.failures)
    error_ids = sorted(test.id() for test, _ in result.errors)
    skipped_ids = sorted(test.id() for test, _ in result.skipped)
    manifest_consistent = collected_ids == sorted(manifest["declared_test_ids"])
    output = stream.getvalue().replace(str(ROOT), "<run-workspace>")
    payload = {
        "schema_version": "tc04-real-project-test-result.v1",
        "python": platform.python_version(),
        "command": "python run_self_test.py",
        "collected": len(collected_ids),
        "passed": len(result.passed_ids),
        "failed": len(failure_ids),
        "errors": len(error_ids),
        "skipped": len(skipped_ids),
        "declared_test_ids": sorted(manifest["declared_test_ids"]),
        "collected_test_ids": collected_ids,
        "passed_test_ids": sorted(result.passed_ids),
        "failed_test_ids": failure_ids,
        "error_test_ids": error_ids,
        "skipped_test_ids": skipped_ids,
        "manifest_consistent": manifest_consistent,
        "coverage": {
            "method": "coverage.py statement coverage over real app.services/app.engine/app.utils modules",
            "files": coverage_files,
            "total_statements": total_statements,
            "covered_statements": total_covered,
            "percent": round(100 * total_covered / max(1, total_statements), 1),
        },
        "network": {
            "non_loopback_socket_connect_blocked_in_process": True,
            "loopback_allowed_for_asyncio": True,
            "real_model_endpoint_called": False,
            "http_tests_use_mock_transport": True,
            "os_level_isolation": False,
        },
        "output": output[-30000:],
        "status": "passed"
        if result.wasSuccessful() and manifest_consistent
        else "failed",
    }
    (ROOT / "test-results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("TC04_TEST_RESULT=" + json.dumps(payload, ensure_ascii=False))
    raise SystemExit(0 if payload["status"] == "passed" else 1)
    '''
).strip() + "\n"


TEST_FILES = {
    "tests/__init__.py": "",
    "tests/helpers.py": TEST_HELPERS,
    "tests/test_model_service.py": MODEL_SERVICE_TESTS,
    "tests/test_model_service_matrix.py": MODEL_SERVICE_MATRIX_TESTS,
    "tests/test_dataset_service.py": DATASET_SERVICE_TESTS,
    "tests/test_dataset_service_matrix.py": DATASET_SERVICE_MATRIX_TESTS,
    "tests/test_experiment_service.py": EXPERIMENT_SERVICE_TESTS,
    "tests/test_experiment_service_matrix.py": EXPERIMENT_SERVICE_MATRIX_TESTS,
    "tests/test_evaluation_engine.py": ENGINE_TESTS,
    "tests/test_evaluation_engine_matrix.py": ENGINE_MATRIX_TESTS,
    "tests/test_utils.py": UTILS_TESTS,
    "tests/test_utils_boundaries.py": UTILITY_BOUNDARY_TESTS,
}


TEST_CATEGORIES = (
    {
        "id": "model-service",
        "label": "模型 Service",
        "module": "test_model_service",
        "modules": ["test_model_service", "test_model_service_matrix"],
        "targets": ["app.services.model_service"],
    },
    {
        "id": "dataset-service",
        "label": "数据集 Service",
        "module": "test_dataset_service",
        "modules": ["test_dataset_service", "test_dataset_service_matrix"],
        "targets": ["app.services.dataset_service"],
    },
    {
        "id": "experiment-service",
        "label": "实验 Service",
        "module": "test_experiment_service",
        "modules": ["test_experiment_service", "test_experiment_service_matrix"],
        "targets": ["app.services.experiment_service"],
    },
    {
        "id": "evaluation-engine",
        "label": "执行引擎",
        "module": "test_evaluation_engine",
        "modules": ["test_evaluation_engine", "test_evaluation_engine_matrix"],
        "targets": ["app.engine.evaluation_engine"],
    },
    {
        "id": "utilities",
        "label": "工具类与事务",
        "module": "test_utils",
        "modules": ["test_utils", "test_utils_boundaries"],
        "targets": ["app.utils.*", "SQLAlchemy AsyncSession"],
    },
)


def _tree_digest(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name, content in sorted(files.items()):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()


def _replace_once(value: str, old: str, new: str, file_name: str) -> str:
    if value.count(old) != 1:
        raise ValueError(f"TC-04 patch precondition failed for {file_name}")
    return value.replace(old, new, 1)


def _declared_test_ids() -> tuple[str, ...]:
    declared: list[str] = []
    for name, content in TEST_FILES.items():
        if not name.startswith("tests/test_"):
            continue
        module = name.removeprefix("tests/")[:-3].replace("/", ".")
        tree = ast.parse(content)
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith(
                    "test_"
                ):
                    declared.append(f"{module}.{node.name}.{item.name}")
    return tuple(sorted(declared))


def _category_manifest(test_ids: tuple[str, ...]) -> list[dict[str, object]]:
    categories: list[dict[str, object]] = []
    for category in TEST_CATEGORIES:
        prefixes = tuple(f"{module}." for module in category["modules"])
        category_test_ids = [
            test_id for test_id in test_ids if test_id.startswith(prefixes)
        ]
        categories.append(
            {
                "id": category["id"],
                "label": category["label"],
                "modules": list(category["modules"]),
                "targets": list(category["targets"]),
                "test_count": len(category_test_ids),
                "test_ids": category_test_ids,
            }
        )
    return categories


def _unified_diff(original: str, revised: str, file_name: str) -> str:
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            revised.splitlines(keepends=True),
            fromfile=f"a/{file_name}",
            tofile=f"b/{file_name}",
        )
    )


def _read_result(root: Path) -> dict[str, object]:
    result_path = root / "test-results.json"
    if not result_path.exists():
        return {}
    return json.loads(result_path.read_text(encoding="utf-8"))


def build_real_evaluation_platform_fix(
    sources: dict[str, bytes],
    run_command: Callable[..., tuple[int, str, int]],
) -> EvaluationPlatformBuild:
    """Copy the full project, test the real modules, patch, and re-run."""

    required = {
        "app/services/model_service.py",
        "app/services/dataset_service.py",
        "app/services/experiment_service.py",
        "app/engine/evaluation_engine.py",
        "app/utils/pagination.py",
        "app/utils/response.py",
        "requirements.txt",
        "frontend/package.json",
    }
    missing = sorted(required - set(sources))
    if missing:
        raise ValueError(f"missing TC-04 project files: {missing}")

    source_tree_digest = _tree_digest(sources)
    source_text = {
        name: content.decode("utf-8", errors="strict")
        for name, content in sources.items()
        if name.endswith((".py", ".md", ".txt", ".json", ".sh", ".ts", ".tsx", ".css", ".html"))
    }
    patched = dict(sources)
    changed_files = (
        "app/services/model_service.py",
        "app/services/dataset_service.py",
        "app/engine/evaluation_engine.py",
    )
    revised_model = _replace_once(
        source_text[changed_files[0]],
        "Experiment.status == ExperimentStatus.COMPLETED,",
        "Experiment.status == ExperimentStatus.RUNNING,",
        changed_files[0],
    )
    revised_dataset = _replace_once(
        source_text[changed_files[1]],
        "start_seq = max_seq",
        "start_seq = max_seq + 1",
        changed_files[1],
    )
    engine_newline = "\r\n" if "\r\n" in source_text[changed_files[2]] else "\n"
    revised_engine = _replace_once(
        source_text[changed_files[2]],
        f"import statistics{engine_newline}",
        f"import statistics{engine_newline}import math{engine_newline}",
        changed_files[2],
    )
    revised_engine = _replace_once(
        revised_engine,
        "p99_ms = sorted_times[int(n * 0.99) - 1]",
        "p99_ms = sorted_times[min(n - 1, math.ceil(n * 0.99) - 1)]",
        changed_files[2],
    )
    patched[changed_files[0]] = revised_model.encode("utf-8")
    patched[changed_files[1]] = revised_dataset.encode("utf-8")
    patched[changed_files[2]] = revised_engine.encode("utf-8")
    patch = "".join(
        _unified_diff(source_text[name], patched[name].decode("utf-8"), name)
        for name in changed_files
    )

    declared_test_ids = _declared_test_ids()
    manifest = {
        "schema_version": "tc04-real-project-test-manifest.v1",
        "source_project": "dev-015/input/source-code",
        "source_file_count": len(sources),
        "source_tree_digest": source_tree_digest,
        "declared_test_ids": list(declared_test_ids),
        "categories": _category_manifest(declared_test_ids),
        "required_behaviors": [
            "normal",
            "error",
            "boundary",
            "async",
            "mock_http",
            "concurrency_limit",
            "transaction_and_session_isolation",
        ],
    }

    import tempfile

    with tempfile.TemporaryDirectory(prefix="office-agent-tc04-") as directory:
        root = Path(directory) / "evaluation-platform"
        for name, content in sources.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        for name, content in TEST_FILES.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        (root / "test-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (root / "run_self_test.py").write_text(RUNNER, encoding="utf-8")

        baseline_rc, baseline_output, baseline_ms = run_command(
            [sys.executable, "run_self_test.py"], cwd=root, timeout_seconds=120
        )
        baseline_result = _read_result(root)
        baseline_result_bytes = json.dumps(
            baseline_result, ensure_ascii=False, indent=2
        ).encode("utf-8") + b"\n"

        for name in changed_files:
            (root / name).write_bytes(patched[name])
        compile_rc, compile_output, compile_ms = run_command(
            [sys.executable, "-m", "compileall", "-q", "app", "tests", "run_self_test.py"],
            cwd=root,
            timeout_seconds=120,
        )
        test_rc, test_output, test_ms = run_command(
            [sys.executable, "run_self_test.py"], cwd=root, timeout_seconds=120
        )
        final_result = _read_result(root)

    baseline_failures = set(baseline_result.get("failed_test_ids", [])) | set(
        baseline_result.get("error_test_ids", [])
    )
    expected_red_ids = {
        "test_model_service.ModelServiceTests.test_delete_rejects_running_experiment",
        "test_model_service.ModelServiceTests.test_delete_allows_completed_experiment",
        "test_dataset_service.DatasetServiceTests.test_append_uses_next_sequence_after_current_maximum",
        "test_evaluation_engine.EvaluationEngineTests.test_finalize_two_samples_uses_nearest_rank_p99",
        "test_evaluation_engine_matrix.EvaluationEngineBusinessMatrixTests.test_finalize_mixed_results_counts_failures_and_percentiles",
    }
    collected_ids = tuple(final_result.get("collected_test_ids", []))
    coverage = final_result.get("coverage", {})
    coverage_files = coverage.get("files", []) if isinstance(coverage, dict) else []
    coverage_percent = float(coverage.get("percent", 0)) if isinstance(coverage, dict) else 0.0
    covered_paths = {item.get("file") for item in coverage_files if isinstance(item, dict)}
    coverage_by_path = {
        str(item.get("file")): float(item.get("percent", 0))
        for item in coverage_files
        if isinstance(item, dict)
    }
    changed_source_coverage = {
        path: coverage_by_path.get(path, 0.0) for path in changed_files
    }
    changed_source_coverage_ok = all(
        percent >= 80.0 for percent in changed_source_coverage.values()
    )
    required_coverage = {
        "app/services/model_service.py",
        "app/services/dataset_service.py",
        "app/services/experiment_service.py",
        "app/engine/evaluation_engine.py",
        "app/utils/crypto.py",
        "app/utils/pagination.py",
        "app/utils/response.py",
    }
    manifest_consistent = (
        tuple(sorted(collected_ids)) == declared_test_ids
        and final_result.get("manifest_consistent") is True
    )
    execution_ok = (
        compile_rc == 0
        and test_rc == 0
        and final_result.get("status") == "passed"
        and not final_result.get("failed")
        and not final_result.get("errors")
        and manifest_consistent
    )
    baseline_red = baseline_rc != 0 and expected_red_ids <= baseline_failures

    changes = {
        "schema_version": "tc04-evaluation-platform-changes.v2",
        "source_project": "dev-015/input/source-code",
        "source_file_count": len(sources),
        "source_tree_digest": source_tree_digest,
        "modified_files": list(changed_files),
        "added_test_files": sorted(TEST_FILES),
        "baseline_expected_failures": sorted(expected_red_ids),
        "baseline_observed_failures": sorted(baseline_failures),
        "final_test_count": len(collected_ids),
        "final_coverage_percent": coverage_percent,
        "changed_source_coverage_percent": changed_source_coverage,
        "source_input_modified": False,
        "frontend_scripts_executed": False,
        "dependency_install_executed": False,
        "real_model_endpoint_called": False,
        "automatic_pr_created": False,
    }
    category_summary = "、".join(
        f"{category['label']} {category['test_count']} 项"
        for category in manifest["categories"]
    )
    changed_coverage_summary = "；".join(
        f"`{path}` {percent:.1f}%"
        for path, percent in changed_source_coverage.items()
    )
    self_test = textwrap.dedent(
        f"""
        # TC-04 自测卡

        **输入**：为评测平台补充单元测试，覆盖 Service、执行引擎和工具类；
        真实运行测试，修复失败，并给出覆盖率与修改文件。

        **预期成果**：`评测平台真实修复包.zip` 和 `TC-04真实测试报告.md`。
        ZIP 展开后是完整 `dev-015/input/source-code` 副本，不是另造的合同模块。

        先进入本仓库受控的 `uv` 环境，或一个已经具备 `requirements.txt` 与
        `requirements-test.txt` 依赖的 Python 3.12 环境。本轮命令不会联网安装依赖。

        **下载后命令**：

        ```bash
        python -m compileall -q app tests run_self_test.py
        python run_self_test.py
        ```

        **应看到**：当前 {len(declared_test_ids)} 个互不等价的测试 ID 与
        `test-manifest.json` 完全一致，0 failure、0 error；报告分别列出模型 Service、
        数据集 Service、实验 Service、执行引擎、工具类与事务五类对象。本次真实源码
        汇总语句覆盖率为 {coverage_percent:.1f}%；三份变更源码逐文件覆盖率为：
        {changed_coverage_summary}，均须不低于 80%。

        **关键回归**：运行中实验阻止模型删除；已完成实验不阻止删除；追加导入从
        最大序号下一位开始；两个样本的 P99 取较慢样本；HTTP 只用 MockTransport；
        并发不超过实验配置；回滚不会泄漏到新 Session。

        **失败信号**：命令非 0、声明和收集 ID 不一致、任一真实模块未出现在覆盖率、
        三份变更源码任一低于 80%、测试访问真实模型端点、ZIP 缺完整前后端项目，
        或 FORTE 原始输入 digest 变化。
        任一出现都不要人工合并。
        """
    ).strip() + "\n"
    modification_note = textwrap.dedent(
        f"""
        # dev-015 评测平台隔离副本修复说明

        本包完整复制了 FORTE `dev-015/input/source-code` 的 {len(sources)} 个文件，
        包含 FastAPI/SQLAlchemy/SQLite 后端与 React 前端。修改只发生在隔离 Run
        Workspace 副本，原资料没有被覆盖。

        1. `model_service.py`：删除模型时只应阻止 `RUNNING` 实验。旧代码反而检查
           `COMPLETED`，会放过正在使用的模型，又错误阻止历史完成记录。
        2. `dataset_service.py`：追加导入从 `max_seq + 1` 开始，避免第一条新数据重复
           已存在序号，造成排序和结果关联歧义。
        3. `evaluation_engine.py`：P99 使用最近秩并把索引限制在 `n - 1`，两个样本时
           不再错误返回较快样本。

        `changes.patch` 是三处真实源码的 unified diff。测试直接导入 `app.services.*`、
        `app.engine.evaluation_engine` 和 `app.utils.*`，没有 `contracts.py` 替身。
        """
    ).strip() + "\n"
    report = textwrap.dedent(
        f"""
        # TC-04 真实评测平台测试报告

        ## 结论

        {f'完整真实副本已修复，{len(collected_ids)} 项测试全部通过。' if execution_ok else '真实副本测试未通过，成果保持红灯，不应合并。'}
        测试对象是 dev-015 的真实 Service、执行引擎和工具模块；不是替身合同函数。

        ## 失败先于修复

        未修改副本先运行同一测试清单，退出码 {baseline_rc}，观察到
        {len(baseline_failures)} 个失败/错误；覆盖三类真实缺陷的五个回归
        {'全部红灯' if baseline_red else '未完整出现，需继续调查'}。失败明细保存在
        `baseline-test-results.json`，没有删除旧的 false-green 证据。

        ## 修复后真实命令

        - Python：{final_result.get('python', 'unknown')}。
        - 编译：`python -m compileall -q app tests run_self_test.py`，退出码 {compile_rc}，
          {compile_ms} ms。
        - 测试：`python run_self_test.py`，退出码 {test_rc}，{test_ms} ms。
        - 结果：collected {final_result.get('collected', 0)}，passed
          {final_result.get('passed', 0)}，failed {final_result.get('failed', 0)}，
          errors {final_result.get('errors', 0)}，skipped {final_result.get('skipped', 0)}。
        - 三份变更源码逐文件覆盖率：{changed_coverage_summary}，门槛均为 80%。
        - 选定 Service/Engine/Utils 汇总语句覆盖率：{coverage_percent:.1f}%；
          该汇总数字不替代逐文件门，完整明细在 `test-results.json`。

        ## 五类测试

        本轮共 {len(declared_test_ids)} 项，按 manifest 展开为：{category_summary}。
        每个 case 都有独立 ID、具体输入与业务断言。

        - 模型 Service：删除状态、创建加密、更新、软删除、筛选分页和历史上限。
        - 数据集 Service：追加/覆盖导入、格式/大小错误、重命名、删除约束和条目分页。
        - 实验 Service：创建与后台启动、关联资源、详情过滤、导出和取消边界。
        - 执行引擎：Mock HTTP、任务注册/取消、并发上限、空集、状态更新和 P99 小样本。
        - 工具类与事务：Schema 边界、分页、加密、响应、审计日志和 Session 回滚隔离。

        ## 安全与人工合并

        固定测试进程不继承提供商凭据或代理，并在 Python 进程内允许 asyncio 所需的
        loopback、阻断非 loopback 的 `socket.connect`；HTTP 测试只用
        `httpx.MockTransport`。这不是 OS 级断网、
        生产多租户沙箱或完整真实外部 HTTP 集成。本轮没有安装依赖、运行前端脚本、
        调用真实模型 endpoint 或自动创建 PR。FORTE 原始源码：未修改；全部修改只在
        隔离 Run Workspace 副本内。下载后应先看 diff、按自测卡复跑，再由人工审查并合并。
        """
    ).strip() + "\n"

    archive_files: dict[str, bytes | str] = {
        f"evaluation-platform/{name}": content for name, content in patched.items()
    }
    archive_files.update(
        {f"evaluation-platform/{name}": content for name, content in TEST_FILES.items()}
    )
    archive_files.update(
        {
            "evaluation-platform/run_self_test.py": RUNNER,
            "evaluation-platform/requirements-test.txt": (
                "-r requirements.txt\ncoverage>=7.6,<8\n"
            ),
            "evaluation-platform/test-manifest.json": json.dumps(
                manifest, ensure_ascii=False, indent=2
            )
            + "\n",
            "evaluation-platform/test-results.json": json.dumps(
                final_result, ensure_ascii=False, indent=2
            )
            + "\n",
            "evaluation-platform/baseline-test-results.json": baseline_result_bytes,
            "evaluation-platform/changes.patch": patch,
            "evaluation-platform/changes.json": json.dumps(
                changes, ensure_ascii=False, indent=2
            )
            + "\n",
            "evaluation-platform/修复说明.md": modification_note,
            "evaluation-platform/TC-04自测卡.md": self_test,
            "evaluation-platform/test-report.md": report,
        }
    )

    categories_present = all(
        any(
            test_id.startswith(tuple(f"{module}." for module in category["modules"]))
            for test_id in declared_test_ids
        )
        for category in TEST_CATEGORIES
    )
    checks = (
        (
            "check-eval-full-copy",
            "完整复制真实评测平台",
            len(sources) == 44 and required <= set(sources),
            f"隔离副本包含 source-code 全部 {len(sources)} 个前后端文件。",
        ),
        (
            "check-eval-baseline-red",
            "同一测试先复现真实缺陷",
            baseline_red,
            f"未修复副本退出码 {baseline_rc}，覆盖三类缺陷的五个目标回归均先出现红灯。",
        ),
        (
            "check-eval-real-diff",
            "三处真实源码可审查",
            all(f"a/{name}" in patch and f"b/{name}" in patch for name in changed_files),
            "模型删除、追加序号和 P99 均有 unified diff。",
        ),
        (
            "check-eval-five-test-areas",
            "五类真实对象均有测试",
            categories_present,
            "模型/数据集/实验 Service、执行引擎、工具与事务均有独立测试文件。",
        ),
        (
            "check-eval-compile",
            "完整后端与测试可编译",
            compile_rc == 0,
            compile_output or "compileall 无错误输出。",
        ),
        (
            "check-eval-test-manifest",
            "声明与实际测试 ID 一致",
            manifest_consistent,
            f"声明并收集 {len(declared_test_ids)} 个具名测试；集合完全一致。",
        ),
        (
            "check-eval-real-tests",
            "真实项目测试零失败",
            execution_ok,
            f"退出码 {test_rc}；{final_result.get('passed', 0)}/{len(declared_test_ids)} 通过，"
            f"{final_result.get('failed', 0)} 失败，{final_result.get('errors', 0)} 错误。",
        ),
        (
            "check-eval-changed-source-coverage",
            "三份变更源码逐文件覆盖率均不低于 80%",
            changed_source_coverage_ok,
            "；".join(
                f"{path} {percent:.1f}%"
                for path, percent in changed_source_coverage.items()
            ),
        ),
        (
            "check-eval-aggregate-coverage",
            "选定真实模块汇总覆盖率单独列示",
            required_coverage <= covered_paths,
            f"app.services/app.engine/app.utils 汇总语句覆盖率 {coverage_percent:.1f}%；"
            "该数字不替代三份变更文件的逐文件门。",
        ),
        (
            "check-eval-mock-http",
            "外部 HTTP 只使用 Mock",
            "httpx.MockTransport" in ENGINE_TESTS and execution_ok,
            "真实引擎方法处理成功、503 与超时；没有调用真实模型 endpoint。",
        ),
        (
            "check-eval-review-package",
            "下载包可独立复跑与人工合并",
            bool(patch) and bool(final_result) and bool(self_test),
            "完整副本、diff、测试清单、双阶段回执、报告与自测卡均在 ZIP 中。",
        ),
    )
    return EvaluationPlatformBuild(
        archive_files=archive_files,
        report=report.encode("utf-8"),
        checks=checks,
        source_file_count=len(sources),
        test_count=len(collected_ids),
        coverage_percent=coverage_percent,
        baseline_ms=baseline_ms,
        compile_ms=compile_ms,
        test_ms=test_ms,
        execution_ok=execution_ok,
        changed_files=changed_files,
        changed_source_coverage=tuple(changed_source_coverage.items()),
        source_tree_digest=source_tree_digest,
        test_suites=tuple(manifest["categories"]),
    )
