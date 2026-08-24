"""Fail-closed catalog for public benchmark task workspaces.

This adapter deliberately indexes only the imported task instruction and input
files.  It never discovers or reads FORTE ``solution/``, rubric, or skill
material, so benchmark answers cannot leak into a running harness.
"""

from __future__ import annotations

import hashlib
import io
import posixpath
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from pydantic import ValidationError

from packages.contracts.harness_models import (
    BenchmarkFileEntry,
    BenchmarkManifest,
    BenchmarkPublicScenario,
    BenchmarkTaskEntry,
)


class BenchmarkScenarioError(RuntimeError):
    """Raised when the benchmark package cannot be trusted or indexed."""


@dataclass(frozen=True)
class BenchmarkFileIndex:
    path: str
    role: str
    mime: str
    size: int
    sha256: str
    summary: dict[str, Any]
    provenance_only: bool


@dataclass(frozen=True)
class BenchmarkScenario:
    task_id: str
    category: str
    input_dir: str
    files: tuple[BenchmarkFileIndex, ...]
    projection: dict[str, Any]

    def file(self, path: str) -> BenchmarkFileIndex:
        for item in self.files:
            if item.path == path:
                return item
        raise BenchmarkScenarioError("公开基准任务文件不在 allowlist 中")


class BenchmarkScenarioCatalog:
    """Validate and index the vendored FORTE input folders."""

    MAX_MANIFEST_BYTES = 1 * 1024 * 1024
    MAX_FILE_BYTES = 10 * 1024 * 1024
    _XML_NS = {
        "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    }

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or self.default_root()).resolve()

    @staticmethod
    def default_root() -> Path:
        return Path(__file__).resolve().parents[4] / "demo-enterprise-data" / "forte"

    def load(self) -> tuple[BenchmarkManifest, tuple[BenchmarkScenario, ...]]:
        manifest = self._load_manifest()
        self._validate_task_ids(manifest.tasks)
        declared: set[str] = set()
        scenarios: list[BenchmarkScenario] = []
        for task in manifest.tasks:
            indexes: list[BenchmarkFileIndex] = []
            for entry in task.files:
                if entry.path in declared:
                    raise BenchmarkScenarioError("公开基准 manifest 包含重复文件")
                declared.add(entry.path)
                self._validate_entry_scope(task, entry)
                path = self._safe_path(entry.path)
                raw = self._read_checked(path, entry)
                indexes.append(
                    BenchmarkFileIndex(
                        path=entry.path,
                        role=entry.role,
                        mime=entry.mime,
                        size=entry.size,
                        sha256=entry.sha256,
                        summary=self._summarize(entry.path, entry.role, raw),
                        provenance_only=entry.role == "task_instruction",
                    )
                )
            self._reject_undeclared_task_files(task, declared)
            scenarios.append(
                BenchmarkScenario(
                    task_id=task.task_id,
                    category=task.category,
                    input_dir=task.input_dir,
                    files=tuple(indexes),
                    projection=self._scenario_projection(manifest, task, indexes),
                )
            )
        return manifest, tuple(scenarios)

    def task(self, task_id: str) -> BenchmarkScenario:
        _, scenarios = self.load()
        for scenario in scenarios:
            if scenario.task_id == task_id:
                return scenario
        raise KeyError(task_id)

    def public_scenarios(self) -> list[dict[str, Any]]:
        """Return only the business contract safe for the foreground UI."""
        _, scenarios = self.load()
        return [self._public_scenario(item).model_dump(mode="json") for item in scenarios]

    def public_task(self, task_id: str) -> dict[str, Any]:
        return self._public_scenario(self.task(task_id)).model_dump(mode="json")

    def internal_task(self, task_id: str) -> dict[str, Any]:
        """Return planner-only context; never use this for the public API."""
        scenario = self.task(task_id)
        projection = scenario.projection
        files: list[dict[str, Any]] = []
        for item in scenario.files:
            if item.role != "input" or item.provenance_only:
                continue
            files.append(
                {
                    "path": item.path,
                    "role": item.role,
                    "mime": item.mime,
                    "size": item.size,
                    "sha256": item.sha256,
                    "summary": item.summary,
                    "display_label": self._display_label(scenario.task_id, item.path),
                    "display_group": self._display_group(scenario.task_id, item.path),
                    "display_summary": self._display_summary(item),
                }
            )
        return {
            "scenario_id": scenario.task_id,
            **projection,
            "allowlisted_tools": projection["allowed_tools"],
            "files": files,
        }

    @staticmethod
    def _public_scenario(scenario: BenchmarkScenario) -> BenchmarkPublicScenario:
        projection = scenario.projection
        files = [
            item
            for item in scenario.files
            if item.role == "input" and not item.provenance_only
        ]
        display_files = [
            {
                "display_label": BenchmarkScenarioCatalog._display_label(
                    scenario.task_id, item.path
                ),
                "display_group": BenchmarkScenarioCatalog._display_group(
                    scenario.task_id, item.path
                ),
                "display_summary": BenchmarkScenarioCatalog._display_summary(item),
            }
            for item in files
        ]
        return BenchmarkPublicScenario(
            scenario_id=scenario.task_id,
            demo_id=projection["demo_id"],
            title=projection["title"],
            goal=projection["goal"],
            deliverables=projection["deliverables"],
            data_boundary=projection["data_boundary"],
            human_gate_summary=projection["human_gate_summary"],
            allowed_capabilities=projection["allowed_capabilities"],
            dataset_label=projection["dataset_label"],
            dataset_version=f"FORTE 公开版本 · {str(projection['dataset_version'])[:7]}",
            experience_policy=projection["experience_policy"],
            files=display_files,
        )

    @staticmethod
    def _display_label(task_id: str, path: str) -> str:
        labels = {
            "Finance-018": {
                "2025往来明细-上半年.xlsx": "2025 年上半年往来明细",
                "2025往来明细-下半年.xlsx": "2025 年下半年往来明细",
                "2026往来明细.xlsx": "2026 年往来明细",
            },
            "pm-014": {
                "上线配置清单.xlsx": "上线配置清单",
                "功能测试报告.xlsx": "功能测试报告",
                "线上兼容环境测试报告.xlsx": "线上兼容环境测试报告",
                "PRD_v2.5.md": "产品需求文档 v2.5",
            },
            "Operations-008": {"专业性说明.md": "外呼合规规则说明"},
        }
        return labels.get(task_id, {}).get(Path(path).name, "公开办公输入文件")

    @staticmethod
    def _display_group(task_id: str, path: str) -> str:
        if task_id == "Finance-018":
            return "财务往来"
        if task_id == "pm-014":
            return "版本上线资料"
        return "运营合规资料"

    @staticmethod
    def _display_summary(item: BenchmarkFileIndex) -> str:
        summary = item.summary
        if summary.get("kind") == "xlsx":
            sheets = summary.get("sheets", [])
            sheet_summaries = []
            for sheet in sheets[:3]:
                name = str(sheet.get("name", "未命名工作表"))[:40]
                dimension = str(sheet.get("dimension", "范围待核对"))[:40]
                headers = [str(header)[:24] for header in sheet.get("headers", [])[:5] if header]
                columns = f"，列：{'、'.join(headers)}" if headers else ""
                sheet_summaries.append(f"{name}（{dimension}{columns}）")
            detail = "；".join(sheet_summaries)
            return f"Excel 表格，共 {len(sheets)} 个工作表" + (f"；{detail}" if detail else "")
        if summary.get("kind") == "markdown":
            return f"Markdown 业务说明，包含 {summary.get('heading_count', 0)} 个标题"
        return "公开办公输入文件"

    def _load_manifest(self) -> BenchmarkManifest:
        path = self.root / "manifest.json"
        if not path.is_file() or path.is_symlink():
            raise BenchmarkScenarioError("公开基准 manifest 不存在或不可读取")
        raw = path.read_bytes()
        if len(raw) <= 0 or len(raw) > self.MAX_MANIFEST_BYTES:
            raise BenchmarkScenarioError("公开基准 manifest 大小不符合限制")
        try:
            return BenchmarkManifest.model_validate_json(raw)
        except (ValidationError, ValueError) as exc:
            raise BenchmarkScenarioError("公开基准 manifest 不符合协议") from exc

    @staticmethod
    def _validate_task_ids(tasks: list[BenchmarkTaskEntry]) -> None:
        ids = [task.task_id for task in tasks]
        if len(ids) != len(set(ids)):
            raise BenchmarkScenarioError("公开基准 manifest 包含重复任务")
        dirs = [task.input_dir for task in tasks]
        if len(dirs) != len(set(dirs)):
            raise BenchmarkScenarioError("公开基准 manifest 包含重复输入目录")

    @staticmethod
    def _scenario_projection(
        manifest: BenchmarkManifest,
        task: BenchmarkTaskEntry,
        files: list[BenchmarkFileIndex],
    ) -> dict[str, Any]:
        instruction = next(
            (
                item.summary.get("planner_instruction")
                for item in files
                if item.role == "task_instruction"
            ),
            None,
        )
        if not isinstance(instruction, str) or not instruction:
            raise BenchmarkScenarioError("任务缺少可供 Harness 使用的 Prompt")
        policy = {
            "Finance-018": {
                "demo_id": "demo1",
                "title": "跨期间财务证据任务",
                "goal": "汇总三个期间的欠款与未收余额，核查是否存在连续三期未变的僵尸账款。",
                "experience_policy": "durable_task",
                "deliverables": ["欠款与未收摘要", "僵尸账款核查结论", "可追溯证据工件"],
                "data_boundary": "只读取三期往来明细，结果写入本轮受控工作区，不调用外部系统。",
                "human_gate_summary": "形成财务摘要后，由用户确认是否进入后续汇报或业务动作。",
                "allowed_capabilities": ["读取表格", "核对跨期余额", "生成分析工件", "验证证据"],
                "allowed_tools": ["file.read", "table.inspect", "artifact.write", "evidence.verify"],
                "allowed_side_effects": ["none", "run_workspace_write"],
            },
            "pm-014": {
                "demo_id": "demo2",
                "title": "版本上线合规协作任务",
                "goal": "联合核对 PRD、配置、功能测试和兼容测试资料，形成可追溯的上线结论与改进计划。",
                "experience_policy": "adaptive_team",
                "deliverables": ["上线结论", "测试覆盖与通过率核对", "风险分级", "上线改进计划"],
                "data_boundary": "只读取 PRD、上线配置、功能测试与兼容测试资料，结果写入本轮受控工作区。",
                "human_gate_summary": "上线结论和改进计划形成后，由用户确认，不自动发布或修改线上系统。",
                "allowed_capabilities": ["读取表格", "核对测试覆盖", "比较版本要求", "生成审查工件", "验证证据"],
                "allowed_tools": ["file.read", "table.inspect", "artifact.write", "evidence.verify"],
                "allowed_side_effects": ["none", "run_workspace_write"],
            },
            "Operations-008": {
                "demo_id": "demo3",
                "title": "受约束的运营流程设计任务",
                "goal": "依据外呼合规规则设计闭环流程，明确人工升级、停止外呼和禁呼等动作边界。",
                "experience_policy": "governed_action",
                "deliverables": ["合规外呼流程草案", "人工升级路径", "终态与动作边界清单"],
                "data_boundary": "只读取公开的外呼合规规则说明，结果写入本轮受控工作区，不拨打电话或写入名单。",
                "human_gate_summary": "任何外部动作前必须由用户确认，当前仅生成受控流程草案。",
                "allowed_capabilities": ["读取规则", "核对动作边界", "生成流程工件", "验证证据"],
                "allowed_tools": ["file.read", "artifact.write", "evidence.verify", "action.preview"],
                "allowed_side_effects": ["none", "run_workspace_write", "external_action"],
            },
        }.get(task.task_id)
        if policy is None:
            raise BenchmarkScenarioError("未注册的公开基准任务不能进入三 Demo Harness")
        return {
            "demo_id": policy["demo_id"],
            "title": policy["title"],
            "goal": policy["goal"],
            "dataset_label": "公开办公基准数据 · FORTE",
            "dataset_version": manifest.source_commit,
            "experience_policy": policy["experience_policy"],
            "selection_reason": "按公开任务说明冻结 allowlisted input 文件",
            "allowed_tools": policy["allowed_tools"],
            "allowed_side_effects": policy["allowed_side_effects"],
            "task_instruction": instruction,
            "deliverables": policy["deliverables"],
            "data_boundary": policy["data_boundary"],
            "human_gate_summary": policy["human_gate_summary"],
            "allowed_capabilities": policy["allowed_capabilities"],
        }

    @staticmethod
    def _validate_entry_scope(task: BenchmarkTaskEntry, entry: BenchmarkFileEntry) -> None:
        task_prefix = f"{task.task_id}/"
        if not entry.path.startswith(task_prefix):
            raise BenchmarkScenarioError("公开基准文件不属于声明的任务目录")
        if entry.role == "task_instruction" and entry.path != f"{task.task_id}/task.md":
            raise BenchmarkScenarioError("任务说明文件路径不符合固定布局")
        if entry.role == "input" and not entry.path.startswith(f"{task.input_dir}/"):
            raise BenchmarkScenarioError("输入文件不属于声明的 input 目录")

    def _reject_undeclared_task_files(
        self, task: BenchmarkTaskEntry, declared: set[str]
    ) -> None:
        task_root = self._safe_path(f"{task.task_id}")
        if not task_root.is_dir() or task_root.is_symlink():
            raise BenchmarkScenarioError("公开基准任务目录不存在或使用符号链接")
        for path in task_root.rglob("*"):
            if path.is_symlink():
                raise BenchmarkScenarioError("公开基准任务不得包含符号链接")
            if path.is_file():
                relative = path.relative_to(self.root).as_posix()
                if relative not in declared:
                    raise BenchmarkScenarioError("公开基准任务包含 manifest 未声明的文件")

    def _safe_path(self, relative_path: str) -> Path:
        normalized = relative_path.replace("\\", "/")
        if (
            normalized != relative_path
            or not normalized
            or normalized.startswith("/")
            or "\x00" in normalized
            or ":" in normalized
            or ".." in normalized.split("/")
            or any(not part for part in normalized.split("/"))
        ):
            raise BenchmarkScenarioError("公开基准 manifest 包含不安全路径")
        candidate = self.root
        for part in Path(normalized).parts:
            candidate /= part
            if candidate.is_symlink():
                raise BenchmarkScenarioError("公开基准文件不能使用符号链接")
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise BenchmarkScenarioError("公开基准路径超出允许目录") from exc
        return resolved

    def _read_checked(self, path: Path, entry: BenchmarkFileEntry) -> bytes:
        if not path.is_file() or path.is_symlink():
            raise BenchmarkScenarioError("公开基准文件不存在或不可读取")
        size = path.stat().st_size
        if size <= 0 or size > self.MAX_FILE_BYTES or size != entry.size:
            raise BenchmarkScenarioError("公开基准文件大小校验失败")
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise BenchmarkScenarioError("公开基准文件读取失败") from exc
        if hashlib.sha256(raw).hexdigest() != entry.sha256:
            raise BenchmarkScenarioError("公开基准文件完整性校验失败")
        return raw

    def _summarize(self, path: str, role: str, raw: bytes) -> dict[str, Any]:
        suffix = Path(path).suffix.lower()
        if suffix == ".md":
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise BenchmarkScenarioError("公开基准 Markdown 不是 UTF-8") from exc
            headings = [
                line.lstrip("#").strip()
                for line in text.splitlines()
                if line.startswith("#")
            ]
            summary: dict[str, Any] = {
                "kind": "markdown",
                "role": role,
                "bytes": len(raw),
                "heading_count": len(headings),
                "headings": headings[:12],
            }
            if role == "task_instruction":
                summary["provenance_only"] = True
                summary["planner_instruction"] = self._planner_instruction(text)
            return summary
        if suffix == ".xlsx":
            return self._summarize_xlsx(raw)
        raise BenchmarkScenarioError("公开基准文件使用了未允许的解析器")

    @staticmethod
    def _planner_instruction(text: str) -> str:
        """Extract only the task prompt; front matter and grading are provenance."""
        start_marker = "## Prompt"
        end_marker = "## Grading Criteria"
        start = text.find(start_marker)
        if start < 0:
            raise BenchmarkScenarioError("任务说明缺少 Prompt 区段")
        start += len(start_marker)
        end = text.find(end_marker, start)
        if end < 0:
            raise BenchmarkScenarioError("任务说明缺少 Grading Criteria 边界")
        prompt = text[start:end].strip()
        forbidden = ("solution_files", "rubrics:", "标准答案", "rubric_file_paths")
        if any(token in prompt for token in forbidden):
            raise BenchmarkScenarioError("任务 Prompt 包含不应进入 Harness 的评测元数据")
        # FORTE prompts use an evaluator workspace path for outputs. Keep the
        # business instruction, but never leak that path into the public API or
        # planner context; artifact names are governed by the Harness contract.
        return re.sub(r"/workspace/(?:input|solution)/", "本轮受控工作区/", prompt)

    def _summarize_xlsx(self, raw: bytes) -> dict[str, Any]:
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                names = archive.namelist()
                self._validate_xlsx_parts(names)
                workbook = ET.fromstring(archive.read("xl/workbook.xml"))
                relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
                relation_map = {
                    item.attrib.get("Id"): item.attrib.get("Target")
                    for item in relationships
                }
                shared = self._read_shared_strings(archive, names)
                sheets: list[dict[str, Any]] = []
                for sheet in workbook.findall("m:sheets/m:sheet", self._XML_NS):
                    rid = sheet.attrib.get("{%s}id" % self._XML_NS["r"])
                    target = relation_map.get(rid)
                    if not target or target.startswith("/") or ".." in target.split("/"):
                        raise BenchmarkScenarioError("XLSX 工作表关系不安全")
                    sheet_name = posixpath.normpath(posixpath.join("xl", target))
                    if not sheet_name.startswith("xl/") or sheet_name not in names:
                        raise BenchmarkScenarioError("XLSX 工作表关系无效")
                    tree = ET.fromstring(archive.read(sheet_name))
                    dimension = tree.find("m:dimension", self._XML_NS)
                    first_row = tree.find("m:sheetData/m:row", self._XML_NS)
                    headers = []
                    if first_row is not None:
                        for cell in first_row.findall("m:c", self._XML_NS):
                            headers.append(self._cell_value(cell, shared))
                    sheets.append(
                        {
                            "name": sheet.attrib.get("name", ""),
                            "state": sheet.attrib.get("state", "visible"),
                            "dimension": dimension.attrib.get("ref") if dimension is not None else None,
                            "headers": headers[:30],
                        }
                    )
                return {
                    "kind": "xlsx",
                    "sheet_count": len(sheets),
                    "sheets": sheets,
                    "has_formulas": self._has_formulas(archive, names),
                    "has_macros": any(name.lower().endswith("vbaproject.bin") for name in names),
                    "has_external_links": any(
                        "externallink" in name.lower() for name in names
                    ),
                }
        except (KeyError, ET.ParseError, ValueError, zipfile.BadZipFile) as exc:
            raise BenchmarkScenarioError("公开基准 XLSX 无法按只读结构解析") from exc

    @staticmethod
    def _validate_xlsx_parts(names: list[str]) -> None:
        if any(name.startswith("/") or ".." in name.split("/") for name in names):
            raise BenchmarkScenarioError("XLSX 压缩包包含不安全路径")
        if "xl/workbook.xml" not in names or "xl/_rels/workbook.xml.rels" not in names:
            raise BenchmarkScenarioError("XLSX 缺少工作簿关系")

    def _read_shared_strings(self, archive: zipfile.ZipFile, names: list[str]) -> list[str]:
        if "xl/sharedStrings.xml" not in names:
            return []
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        return [
            "".join(text.text or "" for text in item.findall(".//m:t", self._XML_NS))
            for item in root.findall("m:si", self._XML_NS)
        ]

    def _has_formulas(self, archive: zipfile.ZipFile, names: list[str]) -> bool:
        for name in names:
            if not name.startswith("xl/worksheets/") or not name.endswith(".xml"):
                continue
            root = ET.fromstring(archive.read(name))
            if root.findall(".//m:f", self._XML_NS):
                return True
        return False

    def _cell_value(self, cell: ET.Element, shared: list[str]) -> str | None:
        value = cell.find("m:v", self._XML_NS)
        cell_type = cell.attrib.get("t")
        if cell_type == "inlineStr":
            return "".join(text.text or "" for text in cell.findall(".//m:t", self._XML_NS))
        if value is None:
            return None
        if cell_type == "s":
            try:
                return shared[int(value.text or "")]
            except (ValueError, IndexError) as exc:
                raise BenchmarkScenarioError("XLSX shared string 索引无效") from exc
        return value.text
