"""Isolated, append-only files produced by deterministic office tools.

The public Snapshot carries only business metadata. Paths and full digests stay
inside the API process and are revalidated whenever a file is downloaded.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile


class RunWorkspaceArtifactError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredRunWorkspaceArtifact:
    size: int
    sha256: str


class RunWorkspaceArtifactStore:
    """Writes files under a private run directory without touching FORTE inputs."""

    MAX_ARTIFACT_BYTES = 10 * 1024 * 1024
    ARTIFACT_ID = re.compile(r"^workspace-artifact-[0-9a-f]{12}$")
    SAFE_FILE_NAME = re.compile(r"^[^/\\:\x00]{1,180}$")

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def write(
        self,
        *,
        owner_id: str,
        run_id: str,
        artifact_id: str,
        file_name: str,
        content: bytes,
    ) -> StoredRunWorkspaceArtifact:
        if not self.ARTIFACT_ID.fullmatch(artifact_id):
            raise RunWorkspaceArtifactError("运行成果标识不合法")
        if not self.SAFE_FILE_NAME.fullmatch(file_name) or file_name in {".", ".."}:
            raise RunWorkspaceArtifactError("运行成果文件名不合法")
        if not content or len(content) > self.MAX_ARTIFACT_BYTES:
            raise RunWorkspaceArtifactError("运行成果大小不符合边界")

        target_dir = self._run_dir(owner_id, run_id) / artifact_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = (target_dir / file_name).resolve()
        self._require_inside(target)
        if target.exists():
            existing = target.read_bytes()
            if existing != content:
                raise RunWorkspaceArtifactError("同一成果版本不能被覆盖")
        else:
            with NamedTemporaryFile(dir=target_dir, delete=False) as handle:
                handle.write(content)
                temporary = Path(handle.name)
            try:
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
        return StoredRunWorkspaceArtifact(
            size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )

    def read(
        self,
        *,
        owner_id: str,
        run_id: str,
        artifact_id: str,
        file_name: str,
        expected_sha256: str,
    ) -> bytes:
        if not self.ARTIFACT_ID.fullmatch(artifact_id):
            raise RunWorkspaceArtifactError("运行成果标识不合法")
        if not self.SAFE_FILE_NAME.fullmatch(file_name):
            raise RunWorkspaceArtifactError("运行成果文件名不合法")
        target = (self._run_dir(owner_id, run_id) / artifact_id / file_name).resolve()
        self._require_inside(target)
        if not target.is_file() or target.is_symlink():
            raise RunWorkspaceArtifactError("运行成果文件不存在")
        content = target.read_bytes()
        if not content or len(content) > self.MAX_ARTIFACT_BYTES:
            raise RunWorkspaceArtifactError("运行成果大小不符合边界")
        digest = hashlib.sha256(content).hexdigest()
        if digest != expected_sha256:
            raise RunWorkspaceArtifactError("运行成果完整性校验失败")
        return content

    def _run_dir(self, owner_id: str, run_id: str) -> Path:
        owner_key = hashlib.sha256(owner_id.encode("utf-8")).hexdigest()[:20]
        run_key = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:20]
        target = (self.root / owner_key / run_key).resolve()
        self._require_inside(target)
        return target

    def _require_inside(self, target: Path) -> None:
        if target != self.root and self.root not in target.parents:
            raise RunWorkspaceArtifactError("运行成果路径越界")
