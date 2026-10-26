"""Record the actual bounded model payload, independently of file verification."""

from typing import Any

from packages.contracts.harness_models import AgentControlLoopInputCoverage


def model_input_coverage(files: list[dict[str, Any]]) -> list[AgentControlLoopInputCoverage]:
    result = []
    for file in files:
        rows, text = file.get("rows"), file.get("text")
        if isinstance(rows, list) and (rows or file.get("kind") == "table"):
            count = len(rows)
            total = file.get("total_rows")
            total = total if isinstance(total, int) and total >= count else None
            unit = "rows"
            bounded = bool(file.get("truncated")) or total is None or count < total
        elif isinstance(text, str):
            count = len(text)
            bounded = bool(file.get("truncated"))
            total = None if bounded else count
            unit = "characters"
        else:
            count, total, unit, bounded = 0, None, "metadata", True
        result.append(AgentControlLoopInputCoverage(
            file_ref=str(file["file_ref"]), unit=unit, provided_count=count,
            total_count=total, bounded=bounded,
        ))
    return result
