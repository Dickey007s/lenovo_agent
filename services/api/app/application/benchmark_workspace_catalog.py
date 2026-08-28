"""Fail-closed catalog for the complete pinned FORTE public office folder.

The catalog verifies every imported task and input byte from the public-suite
manifest, but exposes only the 96 input files. Benchmark task prompts, rubrics,
solutions, raw paths and hashes never cross the public API boundary.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree as ET

from pydantic import ValidationError
from pypdf import PdfReader

from packages.contracts.harness_models import (
    BenchmarkFileEntry,
    BenchmarkFilePreview,
    BenchmarkManifest,
    BenchmarkPreviewRow,
    BenchmarkPreviewSecurity,
    BenchmarkPublicSuiteTask,
    BenchmarkPublicWorkspace,
)
from services.api.app.application.benchmark_scenario_catalog import (
    BenchmarkScenarioCatalog,
    BenchmarkScenarioError,
)


@dataclass(frozen=True)
class WorkspaceFileIndex:
    task_id: str
    category: str
    path: str
    input_dir: str
    mime: str
    size: int
    sha256: str


@dataclass(frozen=True)
class WorkspaceFolderIndex:
    task_id: str
    category: str
    availability: str
    external_dependency: str | None
    files: tuple[WorkspaceFileIndex, ...]


class BenchmarkWorkspaceCatalog(BenchmarkScenarioCatalog):
    """One workspace tree over all allowlisted FORTE public demo inputs."""

    WORKSPACE_ID = "forte-public-office"
    MAX_ARCHIVE_ENTRIES = 400
    MAX_ARCHIVE_EXPANDED_BYTES = 60 * 1024 * 1024
    MAX_PREVIEW_TEXT = 30_000
    MAX_AGENT_TEXT_PER_FILE = 12_000
    MAX_AGENT_CONTEXT_BYTES = 120_000
    TEXT_SUFFIXES = {
        ".md",
        ".txt",
        ".log",
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".json",
        ".css",
        ".html",
        ".sh",
    }
    CATEGORY_LABELS = {
        "administration": ("行政办公", "入职安排与办公资源资料"),
        "algorithm": ("算法研发", "算法工作流、配置与运行日志"),
        "ba": ("商业分析", "需要外部数据服务的分析任务"),
        "dev": ("研发交付", "需求、技术设计与应用源码"),
        "Finance": ("财务管理", "跨期间往来明细与账款资料"),
        "hr": ("人力招聘", "岗位说明与候选人简历"),
        "Legal": ("法务", "授权委托书与风控校验规则"),
        "Marketing": ("市场营销", "广告监测与识别规则"),
        "Misc": ("综合办公", "需要网页与计划任务的数据源"),
        "Operations": ("运营管理", "运营流程与合规说明"),
        "pm": ("产品管理", "需求、配置与上线测试资料"),
        "qa": ("质量保障", "测试工具源码与配置"),
        "sales": ("销售运营", "客户调研与分层策略资料"),
        "sre": ("可靠性工程", "服务运行日志"),
        "uiux": ("用户体验", "交互规范、行为日志与优化规则"),
    }
    EXTERNAL_DEPENDENCY_LABELS = {
        "remote_datasette": "需要远程数据查询服务，当前本地工作区未接入",
        "web_and_cron": "需要网页采集与计划任务，当前本地工作区未接入",
    }

    def load(self) -> tuple[BenchmarkManifest, tuple[WorkspaceFolderIndex, ...]]:
        manifest = self._load_public_manifest()
        self._validate_manifest_totals(manifest)
        declared: set[str] = {"public-suite-manifest.json", "manifest.json", "README.md", "THIRD_PARTY_LICENSE.txt"}
        folders: list[WorkspaceFolderIndex] = []
        seen_task_ids: set[str] = set()
        seen_paths: set[str] = set()

        for task in manifest.tasks:
            if task.task_id in seen_task_ids:
                raise BenchmarkScenarioError("FORTE 公开目录包含重复资料夹")
            seen_task_ids.add(task.task_id)
            self._validate_task(task)
            entries = [task.task_file, *task.input_files]
            indexed: list[WorkspaceFileIndex] = []
            for entry in entries:
                if entry.path in seen_paths:
                    raise BenchmarkScenarioError("FORTE 公开清单包含重复文件")
                seen_paths.add(entry.path)
                declared.add(entry.path)
                self._read_checked(self._safe_path(entry.path), entry)
                if entry.role == "input":
                    if task.input_dir is None:
                        raise BenchmarkScenarioError("无本地输入的资料夹不能声明输入文件")
                    indexed.append(
                        WorkspaceFileIndex(
                            task_id=task.task_id,
                            category=task.category,
                            path=entry.path,
                            input_dir=task.input_dir,
                            mime=entry.mime,
                            size=entry.size,
                            sha256=entry.sha256,
                        )
                    )
            folders.append(
                WorkspaceFolderIndex(
                    task_id=task.task_id,
                    category=task.category,
                    availability=task.availability,
                    external_dependency=task.external_dependency,
                    files=tuple(indexed),
                )
            )

        self._reject_undeclared_tree_files(declared)
        return manifest, tuple(folders)

    def public_workspace(self) -> dict[str, Any]:
        manifest, folders = self.load()
        public_folders = []
        previewable = 0
        file_count = 0
        for folder in folders:
            files = [self._public_file_entry(manifest, item) for item in folder.files]
            file_count += len(files)
            previewable += sum(1 for item in files if item["preview_available"])
            label, summary = self._category_projection(folder.category)
            public_folders.append(
                {
                    "folder_id": self._folder_id(folder.task_id),
                    "display_label": label,
                    "display_summary": summary,
                    "availability": folder.availability,
                    "external_dependency_label": self.EXTERNAL_DEPENDENCY_LABELS.get(
                        folder.external_dependency or ""
                    ),
                    "file_count": len(files),
                    "total_bytes": sum(item.size for item in folder.files),
                    "files": files,
                }
            )
        return BenchmarkPublicWorkspace(
            title="FORTE 公开办公资料库",
            dataset_label="公开办公基准数据 · FORTE",
            dataset_version=f"固定版本 · {manifest.source_commit[:7]}",
            source_label="AGI-Eval-Official/FORTE 公开 demo inputs",
            license=manifest.license,
            data_boundary=(
                "只读访问清单内公开输入文件；不暴露任务答案、评分规则、评测参考内容、"
                "本机路径或文件哈希，不连接真实企业系统。"
            ),
            file_count=file_count,
            folder_count=len(public_folders),
            previewable_file_count=previewable,
            folders=public_folders,
        ).model_dump(mode="json")

    def internal_workspace(self) -> dict[str, Any]:
        manifest, folders = self.load()
        files: list[dict[str, Any]] = []
        for folder in folders:
            for item in folder.files:
                public = self._public_file_entry(manifest, item)
                files.append(
                    {
                        **public,
                        "path": item.path,
                        "role": "input",
                        "sha256": item.sha256,
                    }
                )
        return {
            "workspace_id": self.WORKSPACE_ID,
            "title": "FORTE 公开办公资料库",
            "goal": "根据用户目标自主检索整个公开办公资料库，完成可引用、可复核的只读任务。",
            "dataset_label": "公开办公基准数据 · FORTE",
            "dataset_version": manifest.source_commit,
            "selection_reason": "Agent 面向完整 FORTE 公开输入目录自主检索相关文件",
            "allowlisted_tools": [
                "file.read",
                "table.inspect",
                "artifact.write",
                "evidence.verify",
            ],
            "allowed_side_effects": ["none", "run_workspace_write"],
            "deliverables": ["带文件引用的初步分析结果"],
            "data_boundary": "只读完整公开输入目录；每轮仅向模型提供受预算约束的相关文件，不执行外部动作。",
            "human_gate_summary": "模型结果必须由用户复核，任何外部动作不在当前 Runtime 范围内。",
            "files": files,
        }

    def public_file(self, file_ref: str) -> dict[str, Any]:
        manifest, folders = self.load()
        item = self._find_file(manifest, folders, file_ref)
        entry = BenchmarkFileEntry(
            path=item.path,
            sha256=item.sha256,
            size=item.size,
            mime=item.mime,
            role="input",
        )
        raw = self._read_checked(self._safe_path(item.path), entry)
        common = {
            **self._public_file_entry(manifest, item),
            "workspace_id": self.WORKSPACE_ID,
            "security": BenchmarkPreviewSecurity(
                notes=[
                    "清单、大小与 SHA-256 已在服务端核对",
                    "仅提取预览文本或单元格，不执行宏、脚本或外部资源",
                ]
            ),
        }
        common.pop("extension", None)
        common.pop("preview_kind", None)
        common.pop("preview_available", None)
        suffix = Path(item.path).suffix.lower()
        if suffix == ".xlsx":
            payload = self._preview_xlsx(raw)
            return BenchmarkFilePreview(**common, kind="table", **payload).model_dump(mode="json")
        if suffix == ".csv":
            payload = self._preview_csv(raw)
            return BenchmarkFilePreview(**common, kind="table", **payload).model_dump(mode="json")
        if suffix == ".docx":
            text, truncated, notes = self._preview_docx(raw)
            common["security"] = BenchmarkPreviewSecurity(notes=[*common["security"].notes, *notes])
            return BenchmarkFilePreview(
                **common, kind="document", text=text, truncated=truncated
            ).model_dump(mode="json")
        if suffix == ".pdf":
            text, page_count, truncated, notes = self._preview_pdf(raw)
            common["security"] = BenchmarkPreviewSecurity(notes=[*common["security"].notes, *notes])
            return BenchmarkFilePreview(
                **common,
                kind="pdf",
                text=text,
                page_count=page_count,
                truncated=truncated,
            ).model_dump(mode="json")
        if suffix in self.TEXT_SUFFIXES:
            text, truncated = self._preview_text(raw)
            return BenchmarkFilePreview(
                **common, kind="text", text=text, truncated=truncated
            ).model_dump(mode="json")
        return BenchmarkFilePreview(
            **common,
            kind="unavailable",
            text="此文件已通过完整性校验，但当前没有安全预览器。",
        ).model_dump(mode="json")

    def checked_input_bytes(self, file_ref: str) -> bytes:
        """Return one allowlisted input after the same path, size and digest checks.

        This is an internal capability for bounded run-workspace tools. It is not
        mounted as a download API and must never be used for ``task.md`` or
        benchmark solution material.
        """

        manifest, folders = self.load()
        item = self._find_file(manifest, folders, file_ref)
        entry = BenchmarkFileEntry(
            path=item.path,
            sha256=item.sha256,
            size=item.size,
            mime=item.mime,
            role="input",
        )
        return self._read_checked(self._safe_path(item.path), entry)

    def checked_input_bytes_many(self, file_refs: list[str] | tuple[str, ...]) -> dict[str, bytes]:
        """Verify one immutable batch after loading the allowlist exactly once."""

        manifest, folders = self.load()
        results: dict[str, bytes] = {}
        for file_ref in dict.fromkeys(file_refs):
            item = self._find_file(manifest, folders, file_ref)
            entry = BenchmarkFileEntry(
                path=item.path,
                sha256=item.sha256,
                size=item.size,
                mime=item.mime,
                role="input",
            )
            results[file_ref] = self._read_checked(self._safe_path(item.path), entry)
        return results

    def agent_file_inputs(self, file_refs: list[str]) -> list[dict[str, Any]]:
        """Bound the material passed to the model independently of UI previews."""
        results: list[dict[str, Any]] = []
        used = 0
        for file_ref in file_refs:
            preview = self.public_file(file_ref)
            payload = {
                key: value
                for key, value in preview.items()
                if key
                in {
                    "file_ref",
                    "display_label",
                    "display_group",
                    "display_summary",
                    "kind",
                    "sheet_name",
                    "columns",
                    "rows",
                    "total_rows",
                    "text",
                    "page_count",
                    "truncated",
                }
            }
            if isinstance(payload.get("text"), str):
                text = payload["text"][: self.MAX_AGENT_TEXT_PER_FILE]
                payload["text"] = text
                payload["truncated"] = bool(payload.get("truncated")) or len(text) < len(preview.get("text") or "")
            if isinstance(payload.get("rows"), list):
                payload["rows"] = payload["rows"][:60]
            encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            if used + len(encoded) > self.MAX_AGENT_CONTEXT_BYTES:
                raise BenchmarkScenarioError("Agent 本轮选择的文件内容超过安全上下文上限，请缩小本轮证据范围后重试")
            used += len(encoded)
            results.append(payload)
        return results

    def _load_public_manifest(self) -> BenchmarkManifest:
        path = self.root / "public-suite-manifest.json"
        if not path.is_file() or path.is_symlink():
            raise BenchmarkScenarioError("FORTE 公开目录清单不存在或不可读取")
        raw = path.read_bytes()
        if not raw or len(raw) > self.MAX_MANIFEST_BYTES:
            raise BenchmarkScenarioError("FORTE 公开目录清单大小不符合限制")
        try:
            return BenchmarkManifest.model_validate_json(raw)
        except (ValidationError, ValueError) as exc:
            raise BenchmarkScenarioError("FORTE 公开目录清单不符合协议") from exc

    @staticmethod
    def _validate_manifest_totals(manifest: BenchmarkManifest) -> None:
        input_files = [entry for task in manifest.tasks for entry in task.input_files]
        task_files = [task.task_file for task in manifest.tasks]
        scope = manifest.scope
        if len(manifest.tasks) != scope.public_demo_task_count:
            raise BenchmarkScenarioError("FORTE 公开目录任务数量不一致")
        if len(input_files) != scope.input_file_count:
            raise BenchmarkScenarioError("FORTE 公开目录文件数量不一致")
        if len(task_files) != scope.task_instruction_file_count:
            raise BenchmarkScenarioError("FORTE 任务说明数量不一致")
        if sum(item.size for item in input_files) != scope.input_bytes:
            raise BenchmarkScenarioError("FORTE 公开输入总大小不一致")
        if sum(item.size for item in task_files) != scope.task_instruction_bytes:
            raise BenchmarkScenarioError("FORTE 任务说明总大小不一致")

    @staticmethod
    def _validate_task(task: BenchmarkPublicSuiteTask) -> None:
        if task.task_file.path != f"{task.task_id}/task.md" or task.task_file.role != "task_instruction":
            raise BenchmarkScenarioError("FORTE 任务说明路径不符合固定布局")
        if task.input_file_count != len(task.input_files):
            raise BenchmarkScenarioError("FORTE 资料夹文件数量不一致")
        if task.input_bytes != sum(item.size for item in task.input_files):
            raise BenchmarkScenarioError("FORTE 资料夹文件大小不一致")
        if task.availability == "local_input_bundle":
            if not task.input_dir or not task.input_files:
                raise BenchmarkScenarioError("本地资料夹缺少输入目录或文件")
        elif task.input_dir is not None or task.input_files:
            raise BenchmarkScenarioError("外部依赖资料夹不能伪装成本地输入")
        if task.input_dir:
            prefix = f"{task.input_dir}/"
            if any(item.role != "input" or not item.path.startswith(prefix) for item in task.input_files):
                raise BenchmarkScenarioError("FORTE 输入文件超出所属资料夹")

    def _reject_undeclared_tree_files(self, declared: set[str]) -> None:
        for path in self.root.rglob("*"):
            if path.is_symlink():
                raise BenchmarkScenarioError("FORTE 公开目录不得包含符号链接")
            if path.is_file():
                relative = path.relative_to(self.root).as_posix()
                if relative not in declared:
                    raise BenchmarkScenarioError("FORTE 公开目录包含清单未声明的文件")

    @classmethod
    def _category_projection(cls, category: str) -> tuple[str, str]:
        return cls.CATEGORY_LABELS.get(category, (category, "FORTE 公开办公输入资料"))

    @staticmethod
    def _folder_id(task_id: str) -> str:
        return f"forte-folder-{hashlib.sha256(task_id.encode('utf-8')).hexdigest()[:12]}"

    @staticmethod
    def _file_ref(source_commit: str, path: str) -> str:
        digest = hashlib.sha256(f"{source_commit}:{path}".encode("utf-8")).hexdigest()
        return f"forte-{digest[:16]}"

    def _public_file_entry(self, manifest: BenchmarkManifest, item: WorkspaceFileIndex) -> dict[str, Any]:
        group, _ = self._category_projection(item.category)
        relative = PurePosixPath(item.path).relative_to(PurePosixPath(item.input_dir))
        display_path = "/".join((group, *relative.parts))
        suffix = Path(item.path).suffix.lower()
        kind = self._preview_kind(suffix)
        return {
            "file_ref": self._file_ref(manifest.source_commit, item.path),
            "folder_id": self._folder_id(item.task_id),
            "display_label": Path(item.path).name,
            "display_group": group,
            "display_path": display_path,
            "display_summary": self._display_summary_for_suffix(suffix, item.size),
            "extension": suffix.lstrip(".").upper() or "FILE",
            "mime": item.mime,
            "size": item.size,
            "preview_kind": kind,
            "preview_available": kind != "unavailable",
        }

    @classmethod
    def _preview_kind(cls, suffix: str) -> str:
        if suffix in {".xlsx", ".csv"}:
            return "table"
        if suffix == ".docx":
            return "document"
        if suffix == ".pdf":
            return "pdf"
        if suffix in cls.TEXT_SUFFIXES:
            return "text"
        return "unavailable"

    @staticmethod
    def _display_summary_for_suffix(suffix: str, size: int) -> str:
        labels = {
            ".xlsx": "Excel 表格",
            ".csv": "CSV 表格",
            ".docx": "Word 文档",
            ".pdf": "PDF 文档",
            ".md": "Markdown 文档",
            ".txt": "文本文件",
            ".log": "运行日志",
            ".py": "Python 源码",
            ".js": "JavaScript 源码",
            ".ts": "TypeScript 源码",
            ".tsx": "React TypeScript 源码",
            ".json": "JSON 配置",
            ".css": "样式表",
            ".html": "HTML 文档",
            ".sh": "Shell 脚本",
        }
        return f"{labels.get(suffix, '办公文件')} · {BenchmarkWorkspaceCatalog._format_size(size)}"

    @staticmethod
    def _format_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"

    def _find_file(
        self,
        manifest: BenchmarkManifest,
        folders: tuple[WorkspaceFolderIndex, ...],
        file_ref: str,
    ) -> WorkspaceFileIndex:
        for folder in folders:
            for item in folder.files:
                if self._file_ref(manifest.source_commit, item.path) == file_ref:
                    return item
        raise KeyError(file_ref)

    def _preview_csv(self, raw: bytes) -> dict[str, Any]:
        text, _ = self._decode_text(raw)
        reader = csv.reader(io.StringIO(text))
        all_rows: list[list[str]] = []
        for index, row in enumerate(reader):
            if index > 20_000:
                raise BenchmarkScenarioError("CSV 行数超过安全预览上限")
            all_rows.append([self._safe_cell(value) for value in row[:30]])
        if not all_rows:
            return {"columns": [], "rows": [], "total_rows": 0, "truncated": False}
        columns = all_rows[0]
        data = all_rows[1:]
        rows = [
            BenchmarkPreviewRow(row_number=index + 2, values=row)
            for index, row in enumerate(data[:120])
        ]
        return {
            "columns": columns,
            "rows": rows,
            "total_rows": len(data),
            "truncated": len(data) > len(rows),
        }

    def _preview_docx(self, raw: bytes) -> tuple[str, bool, list[str]]:
        if not zipfile.is_zipfile(io.BytesIO(raw)):
            raise BenchmarkScenarioError("Word 文档容器无效")
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = archive.namelist()
            self._validate_archive(names, archive)
            lower_names = {name.lower() for name in names}
            if any("vbaproject.bin" in name for name in lower_names):
                raise BenchmarkScenarioError("Word 文档包含不允许的宏内容")
            if "word/document.xml" not in names:
                raise BenchmarkScenarioError("Word 文档缺少正文")
            external = False
            relationship_files = [
                name
                for name in names
                if name == "_rels/.rels"
                or (name.startswith("word/_rels/") and name.endswith(".rels"))
            ]
            for name in relationship_files:
                try:
                    root = ET.fromstring(archive.read(name))
                except ET.ParseError as exc:
                    raise BenchmarkScenarioError("Word 文档关系清单无效") from exc
                if any(node.attrib.get("TargetMode") == "External" for node in root):
                    external = True
            root = ET.fromstring(archive.read("word/document.xml"))
            namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
            paragraphs: list[str] = []
            for paragraph in root.iter(f"{namespace}p"):
                value = "".join(node.text or "" for node in paragraph.iter(f"{namespace}t")).strip()
                if value:
                    paragraphs.append(value)
            text = "\n".join(paragraphs)
            truncated = len(text) > self.MAX_PREVIEW_TEXT
            notes = ["Word 宏不会执行"]
            if external:
                notes.append("检测到外部链接，但预览未加载任何外部资源")
            return text[: self.MAX_PREVIEW_TEXT], truncated, notes

    def _preview_pdf(self, raw: bytes) -> tuple[str, int, bool, list[str]]:
        try:
            reader = PdfReader(io.BytesIO(raw), strict=False)
            if reader.is_encrypted and reader.decrypt("") == 0:
                raise BenchmarkScenarioError("PDF 已加密，无法安全预览")
            page_count = len(reader.pages)
            if page_count > 200:
                raise BenchmarkScenarioError("PDF 页数超过安全预览上限")
            chunks: list[str] = []
            for page in reader.pages:
                chunks.append(page.extract_text() or "")
                if sum(len(chunk) for chunk in chunks) >= self.MAX_PREVIEW_TEXT:
                    break
            text = "\n\n".join(chunk.strip() for chunk in chunks if chunk.strip())
            truncated = len(text) > self.MAX_PREVIEW_TEXT or len(chunks) < page_count
            return (
                text[: self.MAX_PREVIEW_TEXT] or "此 PDF 没有可提取的文本层。",
                page_count,
                truncated,
                ["仅提取 PDF 文本层；链接、附件、脚本与表单动作不会执行"],
            )
        except BenchmarkScenarioError:
            raise
        except Exception as exc:
            raise BenchmarkScenarioError("PDF 安全预览解析失败") from exc

    def _preview_text(self, raw: bytes) -> tuple[str, bool]:
        text, _ = self._decode_text(raw)
        if "\x00" in text:
            raise BenchmarkScenarioError("文本文件包含二进制内容")
        text = "".join(character for character in text if ord(character) >= 32 or character in "\n\r\t")
        return text[: self.MAX_PREVIEW_TEXT], len(text) > self.MAX_PREVIEW_TEXT

    @staticmethod
    def _decode_text(raw: bytes) -> tuple[str, str]:
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return raw.decode(encoding), encoding
            except UnicodeDecodeError:
                continue
        raise BenchmarkScenarioError("文本文件编码不受支持")

    def _validate_archive(self, names: list[str], archive: zipfile.ZipFile) -> None:
        if len(names) > self.MAX_ARCHIVE_ENTRIES:
            raise BenchmarkScenarioError("Office 文档包含过多内部条目")
        expanded = 0
        for info in archive.infolist():
            normalized = info.filename.replace("\\", "/")
            if normalized.startswith("/") or ".." in normalized.split("/"):
                raise BenchmarkScenarioError("Office 文档包含不安全内部路径")
            expanded += info.file_size
            if expanded > self.MAX_ARCHIVE_EXPANDED_BYTES:
                raise BenchmarkScenarioError("Office 文档解压大小超过安全上限")

    @staticmethod
    def _safe_cell(value: Any) -> str:
        text = "" if value is None else str(value)
        text = "".join(character for character in text if ord(character) >= 32 or character in "\n\t")
        return re.sub(r"\s+", " ", text).strip()[:2_000]
