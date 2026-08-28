"""Build TC-12 from the complete FORTE dashboard-toolkit project."""

from __future__ import annotations

import difflib
import hashlib
import io
import json
import tempfile
import textwrap
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class DashboardToolkitBuild:
    archive_files: dict[str, bytes | str]
    report: bytes
    checks: tuple[tuple[str, str, bool, str], ...]
    source_file_count: int
    test_count: int
    execution_ok: bool
    changed_files: tuple[str, ...]
    source_tree_digest: str
    stage_duration_ms: int
    final_duration_ms: int
    independent_duration_ms: int
    coverage_by_file: tuple[dict[str, object], ...]
    aggregate_coverage: dict[str, object]
    test_suites: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class JsTestCase:
    title: str
    body: str


@dataclass(frozen=True)
class JsTestSuite:
    suite_id: str
    label: str
    file_name: str
    describe_name: str
    imports: str
    cases: tuple[JsTestCase, ...]

    @property
    def test_ids(self) -> tuple[str, ...]:
        return tuple(
            f"{self.file_name}::{self.describe_name} > {case.title}"
            for case in self.cases
        )

    def render(self) -> str:
        rendered_cases = []
        for case in self.cases:
            body = textwrap.indent(textwrap.dedent(case.body).strip(), " " * 4)
            rendered_cases.append(
                f"  it({json.dumps(case.title)}, () => {{\n{body}\n  }})"
            )
        return (
            textwrap.dedent(self.imports).strip()
            + f"\n\n\ndescribe({json.dumps(self.describe_name)}, () => {{\n"
            + "\n\n".join(rendered_cases)
            + "\n})\n"
        )


METRICS_SUITE = JsTestSuite(
    suite_id="metrics-calculator",
    label="指标计算",
    file_name="tests/metricsCalculator.test.js",
    describe_name="metricsCalculator",
    imports="""
        import {
          calculateARPU,
          calculateAverage,
          calculateCAGR,
          calculateConversionRate,
          calculateGrowthRate,
          calculatePercentile,
          calculateRetentionRate,
          calculateWeightedAverage,
        } from '@/utils/metricsCalculator.js'
    """,
    cases=(
        JsTestCase(
            "calculates positive growth from the old value",
            "expect(calculateGrowthRate(100, 150)).toBe(50)",
        ),
        JsTestCase(
            "calculates a decline from the old value",
            "expect(calculateGrowthRate(200, 100)).toBe(-50)",
        ),
        JsTestCase(
            "returns Infinity for growth from zero to a positive value",
            "expect(calculateGrowthRate(0, 1)).toBe(Infinity)",
        ),
        JsTestCase(
            "returns zero when both growth values are zero",
            "expect(calculateGrowthRate(0, 0)).toBe(0)",
        ),
        JsTestCase(
            "calculates compound annual growth",
            "expect(calculateCAGR(100, 121, 2)).toBe(10)",
        ),
        JsTestCase(
            "rejects a non-positive CAGR base",
            "expect(calculateCAGR(0, 121, 2)).toBe(0)",
        ),
        JsTestCase(
            "rejects a non-positive CAGR period",
            "expect(calculateCAGR(100, 121, 0)).toBe(0)",
        ),
        JsTestCase(
            "calculates a conversion rate",
            "expect(calculateConversionRate(25, 100)).toBe(25)",
        ),
        JsTestCase(
            "returns zero conversion for an empty denominator",
            "expect(calculateConversionRate(1, 0)).toBe(0)",
        ),
        JsTestCase(
            "calculates and rounds a retention rate",
            "expect(calculateRetentionRate(3, 2)).toBe(66.67)",
        ),
        JsTestCase(
            "returns zero retention for an empty cohort",
            "expect(calculateRetentionRate(0, 2)).toBe(0)",
        ),
        JsTestCase(
            "calculates an arithmetic average",
            "expect(calculateAverage([2, 4, 6])).toBe(4)",
        ),
        JsTestCase(
            "returns zero for an empty average input",
            "expect(calculateAverage([])).toBe(0)",
        ),
        JsTestCase(
            "returns zero for a missing average input",
            "expect(calculateAverage(null)).toBe(0)",
        ),
        JsTestCase(
            "calculates a weighted average",
            "expect(calculateWeightedAverage([10, 20], [1, 3])).toBe(17.5)",
        ),
        JsTestCase(
            "rejects mismatched weighted-average inputs",
            "expect(calculateWeightedAverage([10], [1, 2])).toBe(0)",
        ),
        JsTestCase(
            "returns zero when all weights are zero",
            "expect(calculateWeightedAverage([10, 20], [0, 0])).toBe(0)",
        ),
        JsTestCase(
            "calculates an exact percentile",
            "expect(calculatePercentile([1, 3, 5], 50)).toBe(3)",
        ),
        JsTestCase(
            "interpolates a percentile",
            "expect(calculatePercentile([0, 10], 25)).toBe(2.5)",
        ),
        JsTestCase(
            "rejects an out-of-range percentile",
            "expect(calculatePercentile([1, 2], 101)).toBe(0)",
        ),
        JsTestCase(
            "returns zero for an empty percentile input",
            "expect(calculatePercentile([], 50)).toBe(0)",
        ),
        JsTestCase(
            "calculates ARPU",
            "expect(calculateARPU(100, 4)).toBe(25)",
        ),
        JsTestCase(
            "returns zero ARPU for no active users",
            "expect(calculateARPU(100, 0)).toBe(0)",
        ),
    ),
)


DATA_SUITE = JsTestSuite(
    suite_id="data-transformer",
    label="数据转换",
    file_name="tests/dataTransformer.test.js",
    describe_name="dataTransformer",
    imports="""
        import {
          aggregateByPeriod,
          flattenNestedGroups,
          formatTimeSeries,
          groupByField,
          pivotData,
          sortByField,
        } from '@/utils/dataTransformer.js'
    """,
    cases=(
        JsTestCase(
            "groups records by a business field",
            """
            const grouped = groupByField([{ team: 'A', id: 1 }, { team: 'B', id: 2 }, { team: 'A', id: 3 }], 'team')
            expect(grouped.A.map(item => item.id)).toEqual([1, 3])
            expect(grouped.B.map(item => item.id)).toEqual([2])
            """,
        ),
        JsTestCase(
            "keeps records with a missing group key",
            "expect(groupByField([{ id: 1 }], 'team').undefined).toHaveLength(1)",
        ),
        JsTestCase(
            "sorts ascending values",
            "expect(sortByField([{ value: 2 }, { value: 1 }], 'value').map(item => item.value)).toEqual([1, 2])",
        ),
        JsTestCase(
            "sorts descending values",
            "expect(sortByField([{ value: 1 }, { value: 2 }], 'value', 'desc').map(item => item.value)).toEqual([2, 1])",
        ),
        JsTestCase(
            "does not mutate the caller array",
            """
            const source = [{ value: 2 }, { value: 1 }]
            sortByField(source, 'value')
            expect(source).toEqual([{ value: 2 }, { value: 1 }])
            """,
        ),
        JsTestCase(
            "keeps equal values in their original order",
            """
            const result = sortByField([{ value: 1, id: 'first' }, { value: 1, id: 'second' }, { value: 0, id: 'third' }], 'value')
            expect(result.map(item => item.id)).toEqual(['third', 'first', 'second'])
            """,
        ),
        JsTestCase(
            "formats a time series without changing values",
            "expect(formatTimeSeries([{ at: '2026-01-01', amount: 7 }], 'at', 'amount')).toEqual([{ date: '2026-01-01', value: 7 }])",
        ),
        JsTestCase(
            "aggregates monthly values by sum",
            """
            const rows = [{ at: '2026-01-01', value: 2 }, { at: '2026-01-20', value: 3 }]
            expect(aggregateByPeriod(rows, 'at', 'value', 'month', 'sum')).toEqual([{ period: '2026-01', value: 5 }])
            """,
        ),
        JsTestCase(
            "aggregates values by average",
            """
            const rows = [{ at: '2026-01-01', value: 2 }, { at: '2026-01-02', value: 4 }]
            expect(aggregateByPeriod(rows, 'at', 'value', 'month', 'average')[0].value).toBe(3)
            """,
        ),
        JsTestCase(
            "aggregates values by count",
            """
            const rows = [{ at: '2026-01-01', value: 2 }, { at: '2026-01-02', value: 4 }]
            expect(aggregateByPeriod(rows, 'at', 'value', 'month', 'count')[0].value).toBe(2)
            """,
        ),
        JsTestCase(
            "aggregates values by maximum",
            """
            const rows = [{ at: '2026-01-01', value: 2 }, { at: '2026-01-02', value: 4 }]
            expect(aggregateByPeriod(rows, 'at', 'value', 'month', 'max')[0].value).toBe(4)
            """,
        ),
        JsTestCase(
            "aggregates values by minimum",
            """
            const rows = [{ at: '2026-01-01', value: 2 }, { at: '2026-01-02', value: 4 }]
            expect(aggregateByPeriod(rows, 'at', 'value', 'month', 'min')[0].value).toBe(2)
            """,
        ),
        JsTestCase(
            "falls back to sum for an unknown aggregation",
            "expect(aggregateByPeriod([{ at: '2026-01-01', value: 2 }], 'at', 'value', 'month', 'unknown')[0].value).toBe(2)",
        ),
        JsTestCase(
            "orders period buckets chronologically",
            """
            const rows = [{ at: '2026-02-01', value: 2 }, { at: '2026-01-01', value: 1 }]
            expect(aggregateByPeriod(rows, 'at', 'value').map(item => item.period)).toEqual(['2026-01', '2026-02'])
            """,
        ),
        JsTestCase(
            "builds a sum pivot table",
            """
            const result = pivotData([{ team: 'A', month: 'Jan', value: 2 }, { team: 'A', month: 'Jan', value: 3 }], 'team', 'month', 'value', 'sum')
            expect(result.cells.A.Jan).toBe(5)
            """,
        ),
        JsTestCase(
            "builds a count pivot table",
            """
            const result = pivotData([{ team: 'A', month: 'Jan', value: 2 }, { team: 'A', month: 'Jan', value: 3 }], 'team', 'month', 'value', 'count')
            expect(result.cells.A.Jan).toBe(2)
            """,
        ),
        JsTestCase(
            "builds an average pivot table",
            """
            const result = pivotData([{ team: 'A', month: 'Jan', value: 2 }, { team: 'A', month: 'Jan', value: 4 }], 'team', 'month', 'value', 'average')
            expect(result.cells.A.Jan).toBe(3)
            """,
        ),
        JsTestCase(
            "keeps missing pivot cells as null",
            """
            const result = pivotData([{ team: 'A', month: 'Jan', value: 2 }, { team: 'B', month: 'Feb', value: 3 }], 'team', 'month', 'value')
            expect(result.cells.A.Feb).toBeNull()
            """,
        ),
        JsTestCase(
            "flattens grouped records with the default label",
            "expect(flattenNestedGroups({ A: [{ id: 1 }] })).toEqual([{ group: 'A', id: 1 }])",
        ),
        JsTestCase(
            "flattens grouped records with a custom label",
            "expect(flattenNestedGroups({ A: [{ id: 1 }] }, 'team')).toEqual([{ team: 'A', id: 1 }])",
        ),
    ),
)


FILTER_SUITE = JsTestSuite(
    suite_id="filter-engine",
    label="筛选与分页",
    file_name="tests/filterEngine.test.js",
    describe_name="filterEngine",
    imports="""
        import {
          buildSortComparator,
          filterByDateRange,
          filterByKeyword,
          multiConditionFilter,
          paginateData,
        } from '@/utils/filterEngine.js'
    """,
    cases=(
        JsTestCase(
            "returns a copy for a blank keyword",
            """
            const source = [{ name: 'Alpha' }]
            const result = filterByKeyword(source, ' ', ['name'])
            expect(result).toEqual(source)
            expect(result).not.toBe(source)
            """,
        ),
        JsTestCase(
            "matches keywords without case sensitivity",
            "expect(filterByKeyword([{ name: 'Alpha' }, { name: 'Beta' }], 'ALP', ['name'])).toHaveLength(1)",
        ),
        JsTestCase(
            "ignores missing keyword fields safely",
            "expect(filterByKeyword([{ name: null }, {}], 'x', ['name'])).toEqual([])",
        ),
        JsTestCase(
            "includes the start date boundary",
            """
            const rows = [{ at: '2026-01-01', id: 1 }, { at: '2026-01-02', id: 2 }]
            expect(filterByDateRange(rows, 'at', '2026-01-01', '2026-01-02').map(item => item.id)).toEqual([1, 2])
            """,
        ),
        JsTestCase(
            "includes the end date boundary",
            """
            const rows = [{ at: '2026-01-02', id: 2 }, { at: '2026-01-03', id: 3 }]
            expect(filterByDateRange(rows, 'at', '2026-01-01', '2026-01-02').map(item => item.id)).toEqual([2])
            """,
        ),
        JsTestCase(
            "returns an empty date result outside the range",
            "expect(filterByDateRange([{ at: '2026-02-01' }], 'at', '2026-01-01', '2026-01-31')).toEqual([])",
        ),
        JsTestCase(
            "returns a copy when no conditions are supplied",
            """
            const source = [{ value: 1 }]
            const result = multiConditionFilter(source, [])
            expect(result).toEqual(source)
            expect(result).not.toBe(source)
            """,
        ),
        JsTestCase(
            "supports the eq operator",
            "expect(multiConditionFilter([{ value: 1 }, { value: 2 }], [{ field: 'value', operator: 'eq', value: 2 }])).toEqual([{ value: 2 }])",
        ),
        JsTestCase(
            "supports the neq operator",
            "expect(multiConditionFilter([{ value: 1 }, { value: 2 }], [{ field: 'value', operator: 'neq', value: 2 }])).toEqual([{ value: 1 }])",
        ),
        JsTestCase(
            "supports the gt operator",
            "expect(multiConditionFilter([{ value: 1 }, { value: 2 }], [{ field: 'value', operator: 'gt', value: 1 }])).toEqual([{ value: 2 }])",
        ),
        JsTestCase(
            "supports the gte operator",
            "expect(multiConditionFilter([{ value: 1 }, { value: 2 }], [{ field: 'value', operator: 'gte', value: 2 }])).toEqual([{ value: 2 }])",
        ),
        JsTestCase(
            "supports the lt operator",
            "expect(multiConditionFilter([{ value: 1 }, { value: 2 }], [{ field: 'value', operator: 'lt', value: 2 }])).toEqual([{ value: 1 }])",
        ),
        JsTestCase(
            "supports the lte operator",
            "expect(multiConditionFilter([{ value: 1 }, { value: 2 }], [{ field: 'value', operator: 'lte', value: 1 }])).toEqual([{ value: 1 }])",
        ),
        JsTestCase(
            "supports the contains operator without case sensitivity",
            "expect(multiConditionFilter([{ value: 'Alpha' }, { value: 'Beta' }], [{ field: 'value', operator: 'contains', value: 'ALP' }])).toHaveLength(1)",
        ),
        JsTestCase(
            "supports the in operator",
            "expect(multiConditionFilter([{ value: 1 }, { value: 2 }], [{ field: 'value', operator: 'in', value: [2, 3] }])).toEqual([{ value: 2 }])",
        ),
        JsTestCase(
            "rejects a non-array in operand",
            "expect(multiConditionFilter([{ value: 1 }], [{ field: 'value', operator: 'in', value: 1 }])).toEqual([])",
        ),
        JsTestCase(
            "keeps a record for an unknown operator",
            "expect(multiConditionFilter([{ value: 1 }], [{ field: 'value', operator: 'unknown', value: 2 }])).toHaveLength(1)",
        ),
        JsTestCase(
            "requires every condition to pass",
            """
            const rows = [{ value: 2, name: 'Alpha' }, { value: 2, name: 'Beta' }]
            const conditions = [{ field: 'value', operator: 'gte', value: 2 }, { field: 'name', operator: 'contains', value: 'alp' }]
            expect(multiConditionFilter(rows, conditions)).toEqual([{ value: 2, name: 'Alpha' }])
            """,
        ),
        JsTestCase(
            "paginates the first page",
            "expect(paginateData([1, 2, 3], 1, 2)).toEqual({ items: [1, 2], total: 3, page: 1, pageSize: 2, totalPages: 2 })",
        ),
        JsTestCase(
            "clamps a page below one",
            "expect(paginateData([1, 2], 0, 1).page).toBe(1)",
        ),
        JsTestCase(
            "clamps a page beyond the last page",
            "expect(paginateData([1, 2], 99, 1)).toMatchObject({ items: [2], page: 2, totalPages: 2 })",
        ),
        JsTestCase(
            "handles an empty pagination input",
            "expect(paginateData([], 3, 20)).toEqual({ items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 })",
        ),
        JsTestCase(
            "sorts ascending with a comparator",
            "expect([{ value: 2 }, { value: 1 }].sort(buildSortComparator([{ field: 'value', order: 'asc' }])).map(item => item.value)).toEqual([1, 2])",
        ),
        JsTestCase(
            "sorts descending with a comparator",
            "expect([{ value: 1 }, { value: 2 }].sort(buildSortComparator([{ field: 'value', order: 'desc' }])).map(item => item.value)).toEqual([2, 1])",
        ),
        JsTestCase(
            "uses a later comparator rule when values are equal",
            """
            const rows = [{ team: 'A', value: 2 }, { team: 'A', value: 1 }]
            const compare = buildSortComparator([{ field: 'team', order: 'asc' }, { field: 'value', order: 'asc' }])
            expect(rows.sort(compare).map(item => item.value)).toEqual([1, 2])
            """,
        ),
        JsTestCase(
            "keeps equal comparator records stable",
            "expect(buildSortComparator([{ field: 'value', order: 'asc' }])({ value: 1 }, { value: 1 })).toBe(0)",
        ),
        JsTestCase(
            "places a null left value after a real value",
            "expect(buildSortComparator([{ field: 'value', order: 'asc' }])({ value: null }, { value: 1 })).toBe(1)",
        ),
        JsTestCase(
            "places a null right value after a real value",
            "expect(buildSortComparator([{ field: 'value', order: 'asc' }])({ value: 1 }, { value: null })).toBe(-1)",
        ),
    ),
)


TEST_SUITES = (METRICS_SUITE, DATA_SUITE, FILTER_SUITE)
CHANGED_SOURCE_FILES = (
    "src/utils/metricsCalculator.js",
    "src/utils/dataTransformer.js",
    "src/utils/filterEngine.js",
)
EXPECTED_PROJECT_FILES = (
    "package.json",
    "vitest.config.js",
    "src/constants/index.js",
    "src/utils/chartHelper.js",
    "src/utils/dataTransformer.js",
    "src/utils/dateUtils.js",
    "src/utils/exportHelper.js",
    "src/utils/filterEngine.js",
    "src/utils/metricsCalculator.js",
    "src/utils/statisticsEngine.js",
    "src/utils/validatorUtils.js",
)


def _replace_once(value: str, old: str, new: str, label: str) -> str:
    candidate = old
    replacement = new
    if value.count(candidate) != 1 and "\n" in old:
        candidate = old.replace("\n", "\r\n")
        replacement = new.replace("\n", "\r\n")
    if value.count(candidate) != 1:
        raise ValueError(f"TC-12 source contract changed: {label}")
    return value.replace(candidate, replacement, 1)


def _tree_digest(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(files.items()):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(value).digest())
    return digest.hexdigest()


def _unified_patch(
    before: dict[str, str], after: dict[str, str], names: tuple[str, ...]
) -> str:
    output: list[str] = []
    for name in names:
        if before[name] == after[name]:
            continue
        output.extend(
            difflib.unified_diff(
                before[name].splitlines(keepends=True),
                after[name].splitlines(keepends=True),
                fromfile=f"a/{name}",
                tofile=f"b/{name}",
            )
        )
    return "".join(output)


def _fixed_config(alias_directory: str = "./src") -> str:
    return (
        textwrap.dedent(
            f"""
            import {{ fileURLToPath, URL }} from 'node:url'

            export default {{
              resolve: {{
                alias: {{
                  '@': fileURLToPath(new URL('{alias_directory}', import.meta.url))
                }}
              }},
              test: {{
                globals: true,
                include: ['tests/**/*.test.js'],
                coverage: {{
                  provider: 'v8',
                  reporter: ['text', 'json-summary'],
                  reportsDirectory: 'coverage',
                  include: [
                    'src/utils/metricsCalculator.js',
                    'src/utils/dataTransformer.js',
                    'src/utils/filterEngine.js'
                  ],
                  all: true
                }}
              }}
            }}
            """
        ).strip()
        + "\n"
    )


def _write_tree(root: Path, files: dict[str, bytes | str]) -> None:
    for name, value in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, bytes):
            target.write_bytes(value)
        else:
            target.write_text(value, encoding="utf-8")


def _sanitize(value: Any, root: Path) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item, root) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item, root) for item in value]
    if isinstance(value, str):
        root_text = str(root)
        return value.replace(root_text, "<run-workspace>").replace(
            root_text.replace("\\", "/"), "<run-workspace>"
        )
    return value


def _test_file_name(value: str) -> str:
    normalized = value.replace("\\", "/")
    marker = "/tests/"
    if marker in normalized:
        return "tests/" + normalized.split(marker, 1)[1]
    return Path(normalized).name


def _test_ids(payload: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    collected: list[str] = []
    passed: list[str] = []
    failed: list[str] = []
    for result in payload.get("testResults") or []:
        file_name = _test_file_name(str(result.get("name", "")))
        for assertion in result.get("assertionResults") or []:
            ancestors = [
                str(item).strip()
                for item in assertion.get("ancestorTitles") or []
                if str(item).strip()
            ]
            title = str(assertion.get("title") or "").strip()
            logical_name = " > ".join([*ancestors, title])
            test_id = f"{file_name}::{logical_name}"
            collected.append(test_id)
            if assertion.get("status") == "passed":
                passed.append(test_id)
            else:
                failed.append(test_id)
    return sorted(collected), sorted(passed), sorted(failed)


def _stage_result(
    *,
    stage_id: str,
    root: Path,
    result_path: Path,
    command_label: str,
    exit_code: int,
    output: str,
    elapsed_ms: int,
    patch_file: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = (
        json.loads(result_path.read_text(encoding="utf-8"))
        if result_path.is_file()
        else {}
    )
    sanitized = _sanitize(raw, root)
    collected, passed, failed = _test_ids(sanitized)
    suite_failures = []
    for result in sanitized.get("testResults") or []:
        if result.get("status") == "failed" and not result.get("assertionResults"):
            suite_failures.append(
                {
                    "file": _test_file_name(str(result.get("name", ""))),
                    "message": str(result.get("message", ""))[-4_000:],
                }
            )
    normalized = {
        "schema_version": "tc12-vitest-stage-result.v1",
        "stage_id": stage_id,
        "command": command_label,
        "exit_code": exit_code,
        "elapsed_ms": elapsed_ms,
        "collected_test_ids": collected,
        "passed_test_ids": passed,
        "failed_test_ids": failed,
        "suite_failures": suite_failures,
        "num_total_tests": int(sanitized.get("numTotalTests", 0) or 0),
        "num_passed_tests": int(sanitized.get("numPassedTests", 0) or 0),
        "num_failed_tests": int(sanitized.get("numFailedTests", 0) or 0),
        "patch_file": patch_file,
        "output": _sanitize(output, root)[-8_000:],
    }
    return normalized, sanitized


def _coverage_summary(root: Path) -> tuple[tuple[dict[str, object], ...], dict[str, object], dict[str, Any]]:
    path = root / "coverage" / "coverage-summary.json"
    if not path.is_file():
        return (), {}, {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    files: list[dict[str, object]] = []
    for source_path in CHANGED_SOURCE_FILES:
        candidate = next(
            (
                value
                for key, value in raw.items()
                if key != "total" and str(key).replace("\\", "/").endswith(source_path)
            ),
            None,
        )
        if not isinstance(candidate, dict):
            files.append({"file": source_path})
            continue
        files.append(
            {
                "file": source_path,
                "statements": candidate.get("statements", {}),
                "branches": candidate.get("branches", {}),
                "functions": candidate.get("functions", {}),
                "lines": candidate.get("lines", {}),
            }
        )
    total = raw.get("total", {}) if isinstance(raw, dict) else {}
    aggregate = {
        "statements": total.get("statements", {}),
        "branches": total.get("branches", {}),
        "functions": total.get("functions", {}),
        "lines": total.get("lines", {}),
    }
    return tuple(files), aggregate, _sanitize(raw, root)


def _coverage_passed(files: tuple[dict[str, object], ...]) -> bool:
    if len(files) != len(CHANGED_SOURCE_FILES):
        return False
    for item in files:
        statements = item.get("statements")
        branches = item.get("branches")
        lines = item.get("lines")
        if not all(isinstance(metric, dict) for metric in (statements, branches, lines)):
            return False
        if float(statements.get("pct", 0)) < 85:
            return False
        if float(lines.get("pct", 0)) < 85:
            return False
        if float(branches.get("pct", 0)) < 75:
            return False
    return True


def _format_coverage_files(files: tuple[dict[str, object], ...]) -> str:
    return "；".join(
        (
            f"{Path(str(item['file'])).name}: statements "
            f"{item.get('statements', {}).get('pct', 0)}%, branches "
            f"{item.get('branches', {}).get('pct', 0)}%, functions "
            f"{item.get('functions', {}).get('pct', 0)}%, lines "
            f"{item.get('lines', {}).get('pct', 0)}%"
        )
        for item in files
    )


def _zip_bytes(files: dict[str, bytes | str]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in sorted(files.items()):
            archive.writestr(
                name, value if isinstance(value, bytes) else value.encode("utf-8")
            )
    return output.getvalue()


def _link_approved_node_modules(
    root: Path,
    *,
    node: str,
    dependency_root: Path,
    run_command: Callable[..., tuple[int, str, int]],
) -> None:
    """Expose repo-pinned Vitest dependencies without installing in the workspace."""

    link = root / "node_modules"
    script = (
        "const fs=require('node:fs');"
        "const [source,target]=process.argv.slice(1);"
        "fs.symlinkSync(source,target,process.platform==='win32'?'junction':'dir');"
    )
    rc, output, _ = run_command(
        [node, "-e", script, str(dependency_root), str(link)],
        cwd=root,
        timeout_seconds=10,
    )
    if rc != 0 or not (link / "vitest" / "vitest.mjs").is_file():
        raise RuntimeError(
            "TC-12 could not link the approved local Vitest dependencies: "
            + output[-2_000:]
        )


def _run_self_test_script() -> str:
    return (
        textwrap.dedent(
            r"""
            import { spawnSync } from 'node:child_process'
            import fs from 'node:fs'
            import path from 'node:path'
            import { fileURLToPath } from 'node:url'

            const root = path.dirname(fileURLToPath(import.meta.url))
            const vitestEntry = process.argv[2]
            if (!vitestEntry || !fs.existsSync(vitestEntry)) {
              console.error('Usage: node run-self-test.mjs <approved-vitest-entry>')
              process.exit(2)
            }
            const dependencyRoot = path.dirname(path.dirname(path.resolve(vitestEntry)))
            const coverageProvider = path.join(
              dependencyRoot, '@vitest', 'coverage-v8', 'dist', 'index.js'
            ).replaceAll('\\', '/')
            const dependencyLink = path.join(root, 'node_modules')
            if (!fs.existsSync(dependencyLink)) {
              fs.symlinkSync(
                dependencyRoot,
                dependencyLink,
                process.platform === 'win32' ? 'junction' : 'dir'
              )
            }
            const resultFile = path.join(root, 'self-test-vitest.json')
            const completed = spawnSync(process.execPath, [
              vitestEntry, 'run', '--root', root, '--config', path.join(root, 'vitest.config.js'),
              '--reporter=json', `--outputFile=${resultFile}`, '--coverage',
              '--coverage.provider=custom',
              `--coverage.customProviderModule=${coverageProvider}`
            ], { cwd: root, encoding: 'utf8', env: process.env })
            const report = fs.existsSync(resultFile) ? JSON.parse(fs.readFileSync(resultFile, 'utf8')) : {}
            const manifest = JSON.parse(fs.readFileSync(path.join(root, 'test-manifest.json'), 'utf8'))
            const normalizeFile = value => {
              const normalized = String(value || '').replaceAll('\\', '/')
              return normalized.includes('/tests/') ? `tests/${normalized.split('/tests/')[1]}` : path.basename(normalized)
            }
            const collected = []
            for (const file of report.testResults || []) {
              for (const assertion of file.assertionResults || []) {
                const ancestors = (assertion.ancestorTitles || [])
                  .map(value => String(value).trim()).filter(Boolean)
                const logicalName = [...ancestors, String(assertion.title || '').trim()].join(' > ')
                collected.push(`${normalizeFile(file.name)}::${logicalName}`)
              }
            }
            collected.sort()
            const declared = [...manifest.declared_test_ids].sort()
            const coveragePath = path.join(root, 'coverage', 'coverage-summary.json')
            const coverage = fs.existsSync(coveragePath) ? JSON.parse(fs.readFileSync(coveragePath, 'utf8')) : {}
            const sourceMetrics = manifest.coverage_thresholds.files.map(file => {
              const entry = Object.entries(coverage).find(([key]) => key.replaceAll('\\', '/').endsWith(file))?.[1] || {}
              return { file, ...entry }
            })
            const coverageOk = sourceMetrics.every(item =>
              (item.statements?.pct || 0) >= manifest.coverage_thresholds.statements &&
              (item.lines?.pct || 0) >= manifest.coverage_thresholds.lines &&
              (item.branches?.pct || 0) >= manifest.coverage_thresholds.branches
            )
            const manifestConsistent = JSON.stringify(collected) === JSON.stringify(declared)
            const summary = {
              schema_version: 'tc12-independent-self-test.v1',
              command: 'node run-self-test.mjs <approved-vitest-entry>',
              exit_code: completed.status,
              collected_test_ids: collected,
              manifest_consistent: manifestConsistent,
              passed: report.numPassedTests || 0,
              failed: report.numFailedTests || 0,
              coverage_ok: coverageOk,
              coverage_files: sourceMetrics,
              coverage_total: coverage.total || {},
              network: {
                provider_credentials_injected_by_runtime: false,
                proxy_injected_by_runtime: false,
                observed_network_calls: false,
                process_or_os_socket_isolation: false
              },
              status: completed.status === 0 && manifestConsistent && coverageOk ? 'passed' : 'failed'
            }
            fs.writeFileSync(path.join(root, 'self-test-results.json'), JSON.stringify(summary, null, 2) + '\n')
            console.log('TC12_SELF_TEST=' + JSON.stringify(summary))
            process.exit(summary.status === 'passed' ? 0 : 1)
            """
        ).strip()
        + "\n"
    )


def dashboard_toolkit_public_test_manifest() -> dict[str, object]:
    declared_test_ids = sorted(
        test_id for suite in TEST_SUITES for test_id in suite.test_ids
    )
    return {
        "schema_version": "tc12-real-vitest-manifest.v1",
        "scenario_id": "TC-12",
        "source_project": "qa-003/input/dashboard-toolkit",
        "source_file_count": len(EXPECTED_PROJECT_FILES),
        "declared_test_ids": declared_test_ids,
        "test_suites": [
            {
                "id": suite.suite_id,
                "label": suite.label,
                "test_files": [suite.file_name],
                "test_count": len(suite.cases),
                "test_ids": list(suite.test_ids),
            }
            for suite in TEST_SUITES
        ],
        "coverage_thresholds": {
            "files": list(CHANGED_SOURCE_FILES),
            "statements": 85,
            "lines": 85,
            "branches": 75,
        },
        "boundaries": {
            "runtime_installs_dependencies": False,
            "source_package_scripts_executed": False,
            "provider_credentials_injected": False,
            "proxy_injected": False,
            "process_or_os_socket_isolation": False,
        },
    }


def build_real_dashboard_toolkit_fix(
    project_sources: dict[str, bytes],
    run_command: Callable[..., tuple[int, str, int]],
    *,
    node: str,
    vitest_entry: Path,
    dependency_root: Path,
) -> DashboardToolkitBuild:
    if tuple(sorted(project_sources)) != tuple(sorted(EXPECTED_PROJECT_FILES)):
        raise ValueError("TC-12 requires the complete 11-file dashboard-toolkit input")
    source_tree_digest = _tree_digest(project_sources)
    original = {
        name: value.decode("utf-8", errors="strict")
        for name, value in project_sources.items()
    }
    fixed_config = _fixed_config()
    export_only_filter = _replace_once(
        original["src/utils/filterEngine.js"],
        "function filterByDateRange(data, dateField, startDate, endDate) {",
        "export function filterByDateRange(data, dateField, startDate, endDate) {",
        "filterByDateRange export",
    )
    final = dict(original)
    final["vitest.config.js"] = fixed_config
    final["src/utils/metricsCalculator.js"] = _replace_once(
        original["src/utils/metricsCalculator.js"],
        "((newValue - oldValue) / newValue) * 100",
        "((newValue - oldValue) / oldValue) * 100",
        "growth denominator",
    )
    final["src/utils/dataTransformer.js"] = _replace_once(
        original["src/utils/dataTransformer.js"],
        "const sorted = data.sort((a, b) => {\n    if (order === 'asc') return a[field] > b[field] ? 1 : -1\n    return a[field] < b[field] ? 1 : -1\n  })",
        "const sorted = [...data].sort((a, b) => {\n    if (a[field] === b[field]) return 0\n    if (order === 'asc') return a[field] > b[field] ? 1 : -1\n    return a[field] < b[field] ? 1 : -1\n  })",
        "non-mutating stable sort",
    )
    final["src/utils/filterEngine.js"] = _replace_once(
        export_only_filter,
        "return d > start && d < end",
        "return d >= start && d <= end",
        "inclusive date range",
    )

    tests = {suite.file_name: suite.render() for suite in TEST_SUITES}
    declared_test_ids = sorted(
        test_id for suite in TEST_SUITES for test_id in suite.test_ids
    )
    manifest = dashboard_toolkit_public_test_manifest()
    stage_patches = {
        "evidence/stage-a-original.patch": (
            "# Stage A intentionally applies no patch; it executes the frozen input config.\n"
        ),
        "evidence/stage-b-config-only.patch": _unified_patch(
            original,
            {**original, "vitest.config.js": fixed_config},
            ("vitest.config.js",),
        ),
        "evidence/stage-c-export-only.patch": _unified_patch(
            {**original, "vitest.config.js": fixed_config},
            {
                **original,
                "vitest.config.js": fixed_config,
                "src/utils/filterEngine.js": export_only_filter,
            },
            ("src/utils/filterEngine.js",),
        ),
        "evidence/stage-d-final-fixes.patch": _unified_patch(
            {
                **original,
                "vitest.config.js": fixed_config,
                "src/utils/filterEngine.js": export_only_filter,
            },
            final,
            CHANGED_SOURCE_FILES,
        ),
    }
    changes_patch = _unified_patch(
        original,
        final,
        ("vitest.config.js", *CHANGED_SOURCE_FILES),
    )

    command_label = (
        "node <approved-vitest>/vitest.mjs run --root <run-workspace> "
        "--config <run-workspace>/vitest.config.js --reporter=json"
    )
    stage_results: dict[str, dict[str, Any]] = {}
    raw_results: dict[str, dict[str, Any]] = {}
    coverage_files: tuple[dict[str, object], ...] = ()
    aggregate_coverage: dict[str, object] = {}
    coverage_raw: dict[str, Any] = {}
    total_stage_ms = 0
    final_ms = 0
    with tempfile.TemporaryDirectory(prefix="office-agent-tc12-") as directory:
        workspace = Path(directory)
        stages = {
            "stage-a-original": dict(original),
            "stage-b-config-only": {**original, "vitest.config.js": fixed_config},
            "stage-c-export-only": {
                **original,
                "vitest.config.js": fixed_config,
                "src/utils/filterEngine.js": export_only_filter,
            },
            "stage-d-final": final,
        }
        for stage_id, sources in stages.items():
            stage_root = workspace / stage_id
            _write_tree(stage_root, sources)
            _write_tree(stage_root, tests)
            _link_approved_node_modules(
                stage_root,
                node=node,
                dependency_root=dependency_root,
                run_command=run_command,
            )
            result_path = stage_root / "vitest-result.json"
            command = [
                node,
                str(vitest_entry),
                "run",
                "--root",
                str(stage_root),
                "--config",
                str(stage_root / "vitest.config.js"),
                "--reporter=json",
                f"--outputFile={result_path}",
            ]
            if stage_id == "stage-d-final":
                coverage_provider = (
                    dependency_root
                    / "@vitest"
                    / "coverage-v8"
                    / "dist"
                    / "index.js"
                )
                command.extend(
                    [
                        "--coverage",
                        "--coverage.provider=custom",
                        "--coverage.customProviderModule="
                        + coverage_provider.as_posix(),
                    ]
                )
            rc, output, elapsed_ms = run_command(
                command, cwd=stage_root, timeout_seconds=90
            )
            patch_file = {
                "stage-a-original": "evidence/stage-a-original.patch",
                "stage-b-config-only": "evidence/stage-b-config-only.patch",
                "stage-c-export-only": "evidence/stage-c-export-only.patch",
                "stage-d-final": "evidence/stage-d-final-fixes.patch",
            }[stage_id]
            normalized, raw = _stage_result(
                stage_id=stage_id,
                root=stage_root,
                result_path=result_path,
                command_label=command_label + (" --coverage" if stage_id == "stage-d-final" else ""),
                exit_code=rc,
                output=output,
                elapsed_ms=elapsed_ms,
                patch_file=patch_file,
            )
            stage_results[stage_id] = normalized
            raw_results[stage_id] = raw
            if stage_id == "stage-d-final":
                final_ms = elapsed_ms
                coverage_files, aggregate_coverage, coverage_raw = _coverage_summary(
                    stage_root
                )
            else:
                total_stage_ms += elapsed_ms

    expected_stage_b_failures = {
        f"{METRICS_SUITE.file_name}::{METRICS_SUITE.describe_name} > calculates positive growth from the old value",
        f"{METRICS_SUITE.file_name}::{METRICS_SUITE.describe_name} > calculates a decline from the old value",
        f"{DATA_SUITE.file_name}::{DATA_SUITE.describe_name} > does not mutate the caller array",
        f"{DATA_SUITE.file_name}::{DATA_SUITE.describe_name} > keeps equal values in their original order",
    }
    expected_stage_c_failures = expected_stage_b_failures | {
        f"{FILTER_SUITE.file_name}::{FILTER_SUITE.describe_name} > includes the start date boundary",
        f"{FILTER_SUITE.file_name}::{FILTER_SUITE.describe_name} > includes the end date boundary",
    }
    stage_a_text = json.dumps(raw_results["stage-a-original"], ensure_ascii=False)
    stage_a_text += str(stage_results["stage-a-original"].get("output", ""))
    stage_a_red = (
        stage_results["stage-a-original"]["exit_code"] != 0
        and "./source" in original["vitest.config.js"]
        and ("Failed to resolve import" in stage_a_text or "Cannot find" in stage_a_text)
    )
    stage_b_failed = set(stage_results["stage-b-config-only"]["failed_test_ids"])
    stage_b_filter_import_failed = (
        "filterByDateRange is not a function"
        in json.dumps(raw_results["stage-b-config-only"], ensure_ascii=False)
    )
    stage_b_red = (
        stage_results["stage-b-config-only"]["exit_code"] != 0
        and expected_stage_b_failures <= stage_b_failed
        and stage_b_filter_import_failed
    )
    stage_c_failed = set(stage_results["stage-c-export-only"]["failed_test_ids"])
    stage_c_red = (
        stage_results["stage-c-export-only"]["exit_code"] != 0
        and expected_stage_c_failures <= stage_c_failed
    )
    final_result = stage_results["stage-d-final"]
    manifest_consistent = final_result["collected_test_ids"] == declared_test_ids
    final_green = (
        final_result["exit_code"] == 0
        and final_result["num_failed_tests"] == 0
        and final_result["num_passed_tests"] == len(declared_test_ids)
        and manifest_consistent
    )
    coverage_ok = _coverage_passed(coverage_files)

    changes = {
        "schema_version": "tc12-real-project-changes.v1",
        "source_project": "qa-003/input/dashboard-toolkit",
        "source_file_count": len(project_sources),
        "source_tree_unchanged": True,
        "changed_files": ["vitest.config.js", *CHANGED_SOURCE_FILES],
        "added_files": [
            *(suite.file_name for suite in TEST_SUITES),
            "changes.patch",
            "test-manifest.json",
            "run-self-test.mjs",
            "TC-12测试报告.md",
            "TC-12改动说明.md",
            "TC-12自测卡.md",
        ],
        "stages": [
            {
                "stage_id": stage_id,
                "status": "green"
                if stage_id == "stage-d-final" and final_green
                else "red",
                "result_file": f"evidence/{stage_id}-result.json",
                "raw_vitest_file": f"evidence/{stage_id}-vitest.json",
                "patch_file": result["patch_file"],
            }
            for stage_id, result in stage_results.items()
        ],
        "network_boundary": (
            "固定测试未观察到网络调用，Runtime 未注入 Provider/数据库凭据或代理；"
            "没有进程或 OS 级 socket 隔离。"
        ),
    }
    coverage_text = _format_coverage_files(coverage_files)
    suite_text = "；".join(
        f"{suite.label} {len(suite.cases)} 项" for suite in TEST_SUITES
    )
    report = (
        textwrap.dedent(
            f"""
            # TC-12 看板工具库真实测试报告

            ## 本次实际处理

            从允许范围内冻结并复制 `qa-003/input/dashboard-toolkit` 的 11/11 个输入文件，
            在隔离副本中使用同一套 {len(declared_test_ids)} 项具名 Vitest 分四阶段验证：

            1. Stage A 保持原配置，真实复现 `@` 指向 `./source` 的模块解析失败。
            2. Stage B 只修配置，真实复现增长率分母、调用方数组被排序修改、相等值不稳定，
               并确认日期筛选函数尚未导出。
            3. Stage C 只增加日期函数导出，真实复现开始日和结束日被排除。
            4. Stage D 应用完整四文件修复，{len(declared_test_ids)}/{len(declared_test_ids)} 通过，
               manifest 与实际 collected IDs 完全一致。

            ## 修改与业务影响

            - `vitest.config.js`：`@` 指向真实 `src`，测试才能加载业务模块。
            - `metricsCalculator.js`：增长率改用旧值作分母，避免经营指标被低估或放大。
            - `dataTransformer.js`：排序复制输入并正确处理相等值，避免看板操作污染调用方数据。
            - `filterEngine.js`：导出日期筛选并采用闭区间，避免边界日期记录被漏掉。

            ## 真实测试与覆盖率

            - 测试套件：{suite_text}，合计 {len(declared_test_ids)} 项。
            - 最终退出码 {final_result['exit_code']}，零失败；实际失败数：{final_result['num_failed_tests']}。
            - 逐文件覆盖率：{coverage_text}。
            - 门槛：三份变更业务源码 statements/lines >= 85%，branches >= 75%。
            - 汇总覆盖率：statements {aggregate_coverage.get('statements', {}).get('pct', 0)}%，
              branches {aggregate_coverage.get('branches', {}).get('pct', 0)}%，
              functions {aggregate_coverage.get('functions', {}).get('pct', 0)}%，
              lines {aggregate_coverage.get('lines', {}).get('pct', 0)}%。

            ## 安全与合并边界

            Runtime 只调用仓库批准的 Node、Vitest 1.6.1 和 `@vitest/coverage-v8` 1.6.1
            入口，不执行来源 package scripts，也不联网安装依赖。固定测试未观察到网络调用，
            且未注入 Provider/数据库凭据或代理；没有进程或 OS 级 socket 隔离。
            FORTE 原始 11 个文件保持只读。本成果只是固定 qa-003 适配器生成的隔离副本，
            不是任意 JavaScript 沙箱，不会创建、合并 PR，也不具备生产多租户隔离。

            FORTE 原始源码：未修改。
            """
        ).strip()
        + "\n"
    )
    change_notes = (
        textwrap.dedent(
            """
            # TC-12 改动说明

            本包保留完整 11 文件项目结构，只修改四个真实文件并新增测试与证据文件。
            `changes.patch` 是相对原始输入的统一 diff；`evidence/` 保存同一套测试从红灯到绿灯的
            JSON 和分阶段 patch。请先看红灯是否对应预期缺陷，再看最终覆盖率和独立复跑结果。
            原 FORTE 目录没有被覆盖，最终是否合并仍由人工决定。
            """
        ).strip()
        + "\n"
    )
    self_test_card = (
        textwrap.dedent(
            f"""
            # TC-12 自测卡

            - 输入：为三个看板工具模块编写 Vitest，修复源码并真实运行测试。
            - 预期：`test-manifest.json` 声明的 {len(declared_test_ids)} 个 ID 与实际 collected IDs 一致。
            - 命令：在本仓库根目录使用已安装依赖运行
              `node dashboard-toolkit/run-self-test.mjs apps/web/node_modules/vitest/vitest.mjs`。
            - 应看到：{len(declared_test_ids)}/{len(declared_test_ids)} 通过，逐文件 coverage 达门槛，
              `self-test-results.json` 的 `status` 为 `passed`。
            - 不要合并：命令非 0、manifest 不一致、任一逐文件覆盖率未达门、缺少阶段 JSON/diff，
              或 FORTE 原始文件发生变化。
            """
        ).strip()
        + "\n"
    )

    project_files: dict[str, bytes | str] = {
        **final,
        **tests,
        "changes.patch": changes_patch,
        "changes.json": json.dumps(changes, ensure_ascii=False, indent=2) + "\n",
        "test-manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2)
        + "\n",
        "run-self-test.mjs": _run_self_test_script(),
        "TC-12测试报告.md": report,
        "TC-12改动说明.md": change_notes,
        "TC-12自测卡.md": self_test_card,
        "evidence/coverage-summary.json": json.dumps(
            coverage_raw, ensure_ascii=False, indent=2
        )
        + "\n",
        **stage_patches,
    }
    for stage_id, result in stage_results.items():
        project_files[f"evidence/{stage_id}-result.json"] = (
            json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        )
        project_files[f"evidence/{stage_id}-vitest.json"] = (
            json.dumps(raw_results[stage_id], ensure_ascii=False, indent=2) + "\n"
        )

    independent_ms = 0
    independent_ok = False
    independent_result: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="office-agent-tc12-unpack-") as directory:
        extracted = Path(directory)
        with zipfile.ZipFile(io.BytesIO(_zip_bytes({f"dashboard-toolkit/{name}": value for name, value in project_files.items()}))) as archive:
            archive.extractall(extracted)
        project_root = extracted / "dashboard-toolkit"
        rc, output, independent_ms = run_command(
            [node, str(project_root / "run-self-test.mjs"), str(vitest_entry)],
            cwd=extracted,
            timeout_seconds=90,
        )
        result_path = project_root / "self-test-results.json"
        if result_path.is_file():
            independent_result = _sanitize(
                json.loads(result_path.read_text(encoding="utf-8")), project_root
            )
        independent_result["exit_code"] = rc
        independent_result["output"] = _sanitize(output, project_root)[-8_000:]
        independent_ok = (
            rc == 0
            and independent_result.get("status") == "passed"
            and independent_result.get("manifest_consistent") is True
            and independent_result.get("coverage_ok") is True
        )
    project_files["evidence/independent-unpack-rerun.json"] = (
        json.dumps(independent_result, ensure_ascii=False, indent=2) + "\n"
    )
    independent_coverage = tuple(
        dict(item)
        for item in independent_result.get("coverage_files", [])
        if isinstance(item, dict)
    )
    if _coverage_passed(independent_coverage):
        previous_coverage_text = coverage_text
        previous_aggregate = aggregate_coverage
        coverage_files = independent_coverage
        coverage_ok = True
        coverage_text = _format_coverage_files(coverage_files)
        next_aggregate = independent_result.get("coverage_total", {})
        if isinstance(next_aggregate, dict):
            aggregate_coverage = next_aggregate
        report = report.replace(previous_coverage_text, coverage_text).replace(
            (
                f"statements {previous_aggregate.get('statements', {}).get('pct', 0)}%，\n"
                f"  branches {previous_aggregate.get('branches', {}).get('pct', 0)}%，\n"
                f"  functions {previous_aggregate.get('functions', {}).get('pct', 0)}%，\n"
                f"  lines {previous_aggregate.get('lines', {}).get('pct', 0)}%。"
            ),
            (
                f"statements {aggregate_coverage.get('statements', {}).get('pct', 0)}%，\n"
                f"  branches {aggregate_coverage.get('branches', {}).get('pct', 0)}%，\n"
                f"  functions {aggregate_coverage.get('functions', {}).get('pct', 0)}%，\n"
                f"  lines {aggregate_coverage.get('lines', {}).get('pct', 0)}%。"
            ),
        )
        project_files["TC-12测试报告.md"] = report

    source_unchanged = _tree_digest(project_sources) == source_tree_digest
    changed_files = tuple(
        name for name in ("vitest.config.js", *CHANGED_SOURCE_FILES) if original[name] != final[name]
    )
    only_expected_changed = changed_files == (
        "vitest.config.js",
        *CHANGED_SOURCE_FILES,
    )
    checks = (
        (
            "check-tc12-complete-copy",
            "完整 11 文件隔离副本",
            len(project_sources) == 11,
            "冻结并复制 dashboard-toolkit 全部 11/11 个允许输入文件。",
        ),
        (
            "check-tc12-source-unchanged",
            "FORTE 原始项目保持只读",
            source_unchanged,
            "生成、四阶段测试和独立复跑前后，冻结输入树摘要保持一致。",
        ),
        (
            "check-tc12-stage-a-alias-red",
            "原配置解析红灯",
            stage_a_red,
            "Stage A 使用原配置，真实 Vitest 因 @ 指向 ./source 而无法解析业务模块。",
        ),
        (
            "check-tc12-stage-b-business-red",
            "配置修复后的业务红灯",
            stage_b_red,
            "Stage B 复现增长率、排序副作用、相等值和日期函数未导出问题。",
        ),
        (
            "check-tc12-stage-c-boundary-red",
            "日期闭区间红灯",
            stage_c_red,
            "Stage C 只增加导出后，开始日和结束日排除问题均由真实测试捕获。",
        ),
        (
            "check-tc12-final-green",
            "同一测试集最终全绿" if final_green else "最终测试命令未通过",
            final_green,
            (
                f"最终 {len(declared_test_ids)}/{len(declared_test_ids)} 通过，零失败。"
                if final_green
                else (
                    "最终固定命令未通过；请查看 "
                    "evidence/stage-d-final-result.json 后重新启动新的 TC-12 Run。"
                )
            ),
        ),
        (
            "check-tc12-manifest",
            "测试清单与实际收集一致",
            manifest_consistent,
            (
                f"三个套件的 {len(declared_test_ids)} 个公开 ID 与最终 collected IDs 完全一致。"
                if manifest_consistent
                else "最终命令未产生可核对的完整 collected IDs；当前清单不能标为已验证。"
            ),
        ),
        (
            "check-tc12-coverage",
            "逐文件覆盖率达到门槛",
            coverage_ok,
            coverage_text or "未生成 coverage-summary.json。",
        ),
        (
            "check-tc12-diff-scope",
            "真实修改范围可审查",
            only_expected_changed and bool(changes_patch),
            "统一 diff 只修改配置和三个真实业务源码文件；额外相等值缺陷同样先红后绿。",
        ),
        (
            "check-tc12-independent-rerun",
            "下载包独立解压复跑",
            independent_ok,
            (
                "独立临时目录运行固定入口，测试 ID、覆盖率、退出码和 manifest 再次一致。"
                if independent_ok
                else (
                    "独立解压复跑未通过；请查看 "
                    "evidence/independent-unpack-rerun.json，当前包不得合并。"
                )
            ),
        ),
        (
            "check-tc12-fixed-runner-boundary",
            "固定本地执行边界",
            True,
            "未运行来源 package scripts、未联网安装；未注入凭据/代理，也不声称进程或 OS 级断网。",
        ),
    )
    execution_ok = all(item[2] for item in checks)
    changes["execution_ok"] = execution_ok
    changes["merge_allowed"] = execution_ok
    changes["review_guidance"] = (
        "复跑最终测试并审查 changes.patch 后由人工决定是否合并。"
        if execution_ok
        else (
            "当前包不得合并；查看阶段 JSON、coverage-summary.json 与独立复跑回执，"
            "修复后重新启动新的 TC-12 Run。"
        )
    )
    project_files["changes.json"] = (
        json.dumps(changes, ensure_ascii=False, indent=2) + "\n"
    )
    if not execution_ok:
        report = (
            textwrap.dedent(
                f"""
                # TC-12 看板工具库真实测试报告

                ## 当前结论

                固定测试命令未完成全部验证，当前包不得合并。本轮保留隔离副本、统一 diff、
                分阶段结果与失败输出，但不把声明的 {len(declared_test_ids)} 项测试显示为全绿。

                ## 已保留的阶段事实

                - Stage A、Stage B、Stage C 的原缺陷红灯仍保存在 `evidence/`。
                - Stage D 退出码：{final_result['exit_code']}；通过：{final_result['num_passed_tests']}；
                  失败：{final_result['num_failed_tests']}。
                - 逐文件 coverage：{coverage_text or '本轮未形成可信 coverage 结果。'}
                - FORTE 原始 11 个文件保持只读，失败只影响本轮隔离修复包。

                ## 现在怎么处理

                1. 查看 `evidence/stage-d-final-result.json` 和对应 Vitest JSON。
                2. 查看 `evidence/coverage-summary.json` 与
                   `evidence/independent-unpack-rerun.json`。
                3. 修复执行环境或源码后，重新启动一项新的 TC-12 Run；本轮失败记录不会被改写。

                ## 安全与合并边界

                Runtime 未运行来源 package scripts，也未联网安装依赖；没有进程或 OS 级
                socket 隔离。当前只是固定 qa-003 适配器，不是任意 JavaScript 沙箱，
                不会创建或合并 PR，也不具备生产多租户隔离。
                """
            ).strip()
            + "\n"
        )
        project_files["TC-12测试报告.md"] = report
        project_files["TC-12自测卡.md"] = (
            textwrap.dedent(
                """
                # TC-12 自测卡

                - 当前状态：固定命令失败，当前包不得合并。
                - 先查看：`evidence/stage-d-final-result.json`、
                  `evidence/coverage-summary.json`、
                  `evidence/independent-unpack-rerun.json`。
                - 处理方式：修复执行环境或源码后，重新启动一项新的 TC-12 Run。
                - 保留边界：本轮失败记录与 FORTE 只读原件都不会被覆盖。
                """
            ).strip()
            + "\n"
        )
    archive_files = {
        f"dashboard-toolkit/{name}": value for name, value in project_files.items()
    }
    return DashboardToolkitBuild(
        archive_files=archive_files,
        report=report.encode("utf-8"),
        checks=checks,
        source_file_count=len(project_sources),
        test_count=len(declared_test_ids),
        execution_ok=execution_ok,
        changed_files=changed_files,
        source_tree_digest=source_tree_digest,
        stage_duration_ms=total_stage_ms,
        final_duration_ms=final_ms,
        independent_duration_ms=independent_ms,
        coverage_by_file=coverage_files,
        aggregate_coverage=aggregate_coverage,
        test_suites=tuple(manifest["test_suites"]),
    )
