from datetime import UTC, datetime
from typing import Any

from packages.contracts import EvidenceRecord, ProposedActionSpec
from packages.contracts.hashing import canonical_hash


APPROVED_PRICING_SOURCES = {
    "crm:quote/991:v3",
    "crm:quote/2026-demo:v1",
}


class MockEvidenceResolver:
    """Deterministic adapters for P0. User values are references, never trusted verdicts."""

    async def resolve(
        self,
        requirements: list[str],
        action: ProposedActionSpec,
        submitted: dict[str, Any] | None = None,
    ) -> dict[str, EvidenceRecord]:
        submitted = submitted or {}
        now = datetime.now(UTC)
        records: dict[str, EvidenceRecord] = {}
        for requirement in requirements:
            value = submitted.get(requirement)
            if requirement == "recipient_identity" and action.recipients:
                value = value or action.recipients[0]
            elif requirement == "attachment_hash" and action.resources:
                value = value or canonical_hash({"resources": action.resources})
            elif requirement == "dlp_result" and action.resources:
                # P0 adapter simulates invoking the DLP service. The user never
                # types a scan result or an attachment hash.
                value = "mock:dlp/passed"
            elif requirement == "pricing_source":
                source = next(
                    (ref for ref in action.source_refs if ref in APPROVED_PRICING_SOURCES),
                    None,
                )
                if value in APPROVED_PRICING_SOURCES:
                    source = value
                value = source
            elif requirement in {
                "project_write_access",
                "calendar_availability",
                "crm_write_access",
                "expense_case_access",
            }:
                value = f"mock:{requirement}/verified"

            records[requirement] = EvidenceRecord(
                requirement=requirement,
                status="satisfied" if value else "missing",
                source="mock_adapter",
                reference=str(value) if value else None,
                digest=canonical_hash({"value": str(value)}) if value else None,
                checked_at=now,
            )
        return records
