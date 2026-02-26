"""
变更检测器
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class ChangeType(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"


@dataclass
class FileChange:
    path: Path
    change_type: ChangeType
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class ChangeDetector:
    """文件变更检测器"""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_file = cache_dir / "snapshot.json"
        self._snapshot: dict = self._load_snapshot()

    def _load_snapshot(self) -> dict:
        if self.snapshot_file.exists():
            with open(self.snapshot_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"files": {}, "last_scan": None}

    def _save_snapshot(self) -> None:
        with open(self.snapshot_file, "w", encoding="utf-8") as f:
            json.dump(self._snapshot, f, indent=2)

    def compute_hash(self, file_path: Path) -> str:
        """计算文件哈希"""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def scan_directory(
        self,
        directory: Path,
        extensions: Optional[list[str]] = None,
        exclude_patterns: Optional[list[str]] = None,
    ) -> list[FileChange]:
        """扫描目录检测变更"""
        changes = []
        current_files: dict[str, str] = {}

        extensions = extensions or [".py"]
        exclude_patterns = exclude_patterns or []

        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in extensions:
                continue

            if any(pattern in str(file_path) for pattern in exclude_patterns):
                continue

            rel_path = str(file_path.relative_to(directory))
            file_hash = self.compute_hash(file_path)
            current_files[rel_path] = file_hash

            if rel_path not in self._snapshot["files"]:
                changes.append(FileChange(
                    path=file_path,
                    change_type=ChangeType.ADDED,
                    new_hash=file_hash,
                ))
            elif self._snapshot["files"][rel_path] != file_hash:
                changes.append(FileChange(
                    path=file_path,
                    change_type=ChangeType.MODIFIED,
                    old_hash=self._snapshot["files"][rel_path],
                    new_hash=file_hash,
                ))

        for rel_path in set(self._snapshot["files"].keys()) - set(current_files.keys()):
            changes.append(FileChange(
                path=directory / rel_path,
                change_type=ChangeType.DELETED,
                old_hash=self._snapshot["files"][rel_path],
            ))

        self._snapshot["files"] = current_files
        self._snapshot["last_scan"] = datetime.now().isoformat()
        self._save_snapshot()

        return changes

    def get_file_hash(self, file_path: Path, base_dir: Path) -> Optional[str]:
        """获取文件的缓存哈希"""
        rel_path = str(file_path.relative_to(base_dir))
        return self._snapshot["files"].get(rel_path)

    def is_file_changed(self, file_path: Path, base_dir: Path) -> bool:
        """检查文件是否已变更"""
        cached_hash = self.get_file_hash(file_path, base_dir)
        if not cached_hash:
            return True

        current_hash = self.compute_hash(file_path)
        return cached_hash != current_hash

    def update_file_hash(self, file_path: Path, base_dir: Path) -> None:
        """更新文件哈希"""
        rel_path = str(file_path.relative_to(base_dir))
        self._snapshot["files"][rel_path] = self.compute_hash(file_path)
        self._save_snapshot()

    def get_changed_files(
        self,
        directory: Path,
        since: Optional[datetime] = None,
    ) -> list[Path]:
        """获取自某时间以来变更的文件"""
        changes = self.scan_directory(directory)
        changed_files = []

        for change in changes:
            if change.change_type != ChangeType.DELETED:
                changed_files.append(change.path)

        return changed_files

    def clear_snapshot(self) -> None:
        """清除快照"""
        self._snapshot = {"files": {}, "last_scan": None}
        self._save_snapshot()
