from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from packages.contracts import TaskSourceDocument, TaskSourceFact


DEMO1_MAIL_SOURCE = "fixture:mail/customer-a:2026-06-15"
DEMO1_OFFICIAL_REVENUE_SOURCE = "fixture:crm/customer-a:official-revenue-v3"
DEMO1_FORECAST_REVENUE_SOURCE = "fixture:forecast/customer-a:revenue-v2"
DEMO1_PROJECT_SOURCE = "fixture:project/customer-a:weekly-v5"
DEMO1_SOURCE_REFS = (
    DEMO1_MAIL_SOURCE,
    DEMO1_OFFICIAL_REVENUE_SOURCE,
    DEMO1_FORECAST_REVENUE_SOURCE,
    DEMO1_PROJECT_SOURCE,
)


class DemoSourceError(RuntimeError):
    pass


class _ManifestBasis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=160)
    url: str = Field(min_length=1, max_length=1_000)
    supports: str = Field(min_length=1, max_length=1_000)
    limitation: str = Field(min_length=1, max_length=1_000)


class _ManifestDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_ref: str = Field(min_length=1, max_length=500)
    document_id: str = Field(min_length=1, max_length=160)
    relative_path: str = Field(min_length=1, max_length=500)
    display_name: str = Field(min_length=1, max_length=240)
    system_label: str = Field(min_length=1, max_length=200)
    semantic_type: Literal[
        "request_context", "historical_actual", "forecast", "project_risk"
    ]
    record_status: str = Field(min_length=1, max_length=120)
    recorded_at: str = Field(min_length=1, max_length=80)
    owner_role: str = Field(min_length=1, max_length=120)
    parser: Literal[
        "eml", "crm_revenue_csv", "forecast_revenue_csv", "project_status_json"
    ]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class _Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    dataset_id: str = Field(min_length=1, max_length=160)
    content_nature: Literal["project_generated_simulation"]
    customer_label: str = Field(min_length=1, max_length=200)
    public_basis: list[_ManifestBasis] = Field(min_length=1, max_length=10)
    documents: list[_ManifestDocument] = Field(min_length=1, max_length=20)


@dataclass(frozen=True)
class Demo1SourcePackage:
    dataset_id: str
    customer_label: str
    documents: tuple[TaskSourceDocument, ...]

    def document(self, source_ref: str) -> TaskSourceDocument:
        for item in self.documents:
            if item.source_ref == source_ref:
                return item
        raise DemoSourceError("演示资料缺少任务契约要求的来源")

    def fact(self, source_ref: str, field: str) -> str:
        document = self.document(source_ref)
        for item in document.facts:
            if item.field == field:
                return item.value
        raise DemoSourceError("演示资料缺少任务运行所需字段")


class DemoSourceCatalog:
    """Read and freeze the allowlisted file package used by Demo 1."""

    MAX_FILE_BYTES = 256 * 1024

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or self.default_root()).resolve()

    @staticmethod
    def default_root() -> Path:
        return Path(__file__).resolve().parents[4] / "demo-enterprise-data" / "customer-a"

    def load_demo1(self) -> Demo1SourcePackage:
        manifest_path = self.root / "manifest.json"
        manifest_bytes = self._read_bounded_file(manifest_path)
        try:
            manifest = _Manifest.model_validate_json(manifest_bytes)
        except (ValidationError, ValueError) as exc:
            raise DemoSourceError("演示资料索引不符合协议") from exc

        source_refs = [item.source_ref for item in manifest.documents]
        if len(source_refs) != len(set(source_refs)) or set(source_refs) != set(
            DEMO1_SOURCE_REFS
        ):
            raise DemoSourceError("演示资料索引与 Demo 1 来源范围不一致")

        documents: list[TaskSourceDocument] = []
        for entry in manifest.documents:
            path = self._safe_document_path(entry.relative_path)
            raw = self._read_bounded_file(path)
            digest = hashlib.sha256(raw).hexdigest()
            if digest != entry.sha256:
                raise DemoSourceError("演示资料完整性校验失败")
            facts = self._parse_facts(entry.parser, raw)
            documents.append(
                TaskSourceDocument(
                    source_ref=entry.source_ref,
                    document_id=entry.document_id,
                    display_name=entry.display_name,
                    relative_path=entry.relative_path,
                    system_label=entry.system_label,
                    semantic_type=entry.semantic_type,
                    record_status=entry.record_status,
                    recorded_at=entry.recorded_at,
                    owner_role=entry.owner_role,
                    content_digest=f"sha256:{digest}",
                    facts=facts,
                )
            )
        return Demo1SourcePackage(
            dataset_id=manifest.dataset_id,
            customer_label=manifest.customer_label,
            documents=tuple(documents),
        )

    def require_unchanged(self, expected: list[TaskSourceDocument]) -> Demo1SourcePackage:
        current = self.load_demo1()
        expected_by_ref = {item.source_ref: item for item in expected}
        current_by_ref = {item.source_ref: item for item in current.documents}
        if expected_by_ref != current_by_ref:
            raise DemoSourceError("演示资料在任务运行期间发生变化，请开始新一轮任务")
        return current

    def _safe_document_path(self, relative_path: str) -> Path:
        normalized = relative_path.replace("\\", "/")
        if normalized.startswith("/") or ":" in normalized or ".." in normalized.split("/"):
            raise DemoSourceError("演示资料索引包含不安全路径")
        candidate = self.root
        for part in Path(normalized).parts:
            candidate = candidate / part
            if candidate.is_symlink():
                raise DemoSourceError("演示资料不能使用符号链接")
        path = candidate.resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise DemoSourceError("演示资料路径超出允许目录") from exc
        return path

    def _read_bounded_file(self, path: Path) -> bytes:
        if not path.is_file() or path.is_symlink():
            raise DemoSourceError("演示资料文件不存在或不可读取")
        size = path.stat().st_size
        if size <= 0 or size > self.MAX_FILE_BYTES:
            raise DemoSourceError("演示资料文件大小不符合限制")
        try:
            return path.read_bytes()
        except OSError as exc:
            raise DemoSourceError("演示资料文件读取失败") from exc

    def _parse_facts(self, parser: str, raw: bytes) -> list[TaskSourceFact]:
        try:
            if parser == "crm_revenue_csv":
                return self._parse_revenue_csv(raw, forecast=False)
            if parser == "forecast_revenue_csv":
                return self._parse_revenue_csv(raw, forecast=True)
            if parser == "project_status_json":
                return self._parse_project_status(raw)
            if parser == "eml":
                return self._parse_mail(raw)
        except (UnicodeDecodeError, csv.Error, json.JSONDecodeError, InvalidOperation) as exc:
            raise DemoSourceError("演示资料内容无法按声明格式解析") from exc
        raise DemoSourceError("演示资料使用了未允许的解析器")

    @staticmethod
    def _parse_revenue_csv(raw: bytes, *, forecast: bool) -> list[TaskSourceFact]:
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        if len(rows) != 1:
            raise DemoSourceError("演示收入文件必须包含唯一目标记录")
        row = rows[0]
        metric = "forecast_revenue" if forecast else "recognized_revenue"
        status_field = "forecast_status" if forecast else "record_status"
        expected_status = "active" if forecast else "closed"
        if (
            row.get("account_id") != "CUST-A-042"
            or row.get("metric") != metric
            or row.get(status_field) != expected_status
            or row.get("currency") != "CNY"
        ):
            raise DemoSourceError("演示收入记录的身份、口径或状态不符合场景")
        amount = Decimal(row.get("amount_wan", ""))
        if not amount.is_finite() or amount <= 0 or amount != amount.to_integral_value():
            raise DemoSourceError("演示收入金额必须是正整数万元")
        amount_text = str(int(amount))
        record_id_field = "forecast_id" if forecast else "record_id"
        period_field = "forecast_period" if forecast else "period"
        record_id = row.get(record_id_field, "").strip()
        period = row.get(period_field, "").strip()
        if not record_id or not period:
            raise DemoSourceError("演示收入记录缺少记录编号或期间")
        return [
            TaskSourceFact(
                field=record_id_field,
                label="记录编号",
                value=record_id,
                display_value=record_id,
            ),
            TaskSourceFact(
                field=period_field,
                label="所属期间",
                value=period,
                display_value=period,
            ),
            TaskSourceFact(
                field=metric,
                label="预测收入" if forecast else "已实现收入",
                value=amount_text,
                display_value=f"{amount_text} 万元",
            ),
            TaskSourceFact(
                field=status_field,
                label="记录状态",
                value=expected_status,
                display_value="预测中" if forecast else "已关账",
            ),
        ]

    @staticmethod
    def _parse_project_status(raw: bytes) -> list[TaskSourceFact]:
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("account_id") != "CUST-A-042":
            raise DemoSourceError("项目周报缺少目标客户记录")
        risk_summary = payload.get("risk_summary")
        mitigation = payload.get("mitigation")
        variance = payload.get("milestone_variance_days")
        if not isinstance(risk_summary, str) or not isinstance(mitigation, str):
            raise DemoSourceError("项目周报缺少风险说明")
        if not isinstance(variance, int) or isinstance(variance, bool) or variance < 0:
            raise DemoSourceError("项目周报里程碑偏差无效")
        return [
            TaskSourceFact(
                field="risk_summary",
                label="项目风险",
                value=risk_summary,
                display_value=risk_summary,
            ),
            TaskSourceFact(
                field="mitigation",
                label="建议动作",
                value=mitigation,
                display_value=mitigation,
            ),
            TaskSourceFact(
                field="milestone_variance_days",
                label="里程碑偏差",
                value=str(variance),
                display_value=f"{variance} 天",
            ),
        ]

    @staticmethod
    def _parse_mail(raw: bytes) -> list[TaskSourceFact]:
        message = BytesParser(policy=policy.default).parsebytes(raw)
        subject = str(message.get("Subject", "")).strip()
        body = message.get_body(preferencelist=("plain",))
        content = body.get_content().strip() if body is not None else ""
        if not subject or not content or "财务已关账记录" not in content:
            raise DemoSourceError("客户请求邮件缺少场景约束")
        return [
            TaskSourceFact(
                field="subject",
                label="邮件主题",
                value=subject,
                display_value=subject,
            ),
            TaskSourceFact(
                field="revenue_instruction",
                label="收入口径要求",
                value="finance_close_required",
                display_value="收入以财务已关账记录为正式口径",
            ),
        ]
