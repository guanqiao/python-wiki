"""
增量更新器
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from pywiki.sync.change_detector import ChangeDetector, ChangeType, FileChange
from pywiki.parsers.python import PythonParser
from pywiki.parsers.types import ModuleInfo
from pywiki.wiki.storage import WikiStorage
from pywiki.wiki.manager import WikiManager


@dataclass
class UpdateResult:
    success: bool
    updated_files: list[Path] = field(default_factory=list)
    failed_files: list[tuple[Path, str]] = field(default_factory=list)
    duration_seconds: float = 0
    error: Optional[str] = None


class IncrementalUpdater:
    """增量更新器"""

    def __init__(
        self,
        wiki_manager: WikiManager,
        change_detector: ChangeDetector,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ):
        self.wiki_manager = wiki_manager
        self.change_detector = change_detector
        self.progress_callback = progress_callback

        self.parser = PythonParser(
            exclude_patterns=wiki_manager.wiki_config.exclude_patterns,
            include_private=wiki_manager.wiki_config.include_private,
        )

    async def update(self, changes: Optional[list[FileChange]] = None) -> UpdateResult:
        """执行增量更新"""
        start_time = datetime.now()
        result = UpdateResult(success=True)

        try:
            if changes is None:
                changes = self.change_detector.scan_directory(
                    self.wiki_manager.project.path,
                    extensions=[".py"],
                    exclude_patterns=self.wiki_manager.wiki_config.exclude_patterns,
                )

            relevant_changes = [
                c for c in changes
                if c.change_type in (ChangeType.ADDED, ChangeType.MODIFIED)
            ]

            if not relevant_changes:
                return result

            total = len(relevant_changes)
            for i, change in enumerate(relevant_changes):
                if self.progress_callback:
                    progress = int((i + 1) / total * 100)
                    self.progress_callback(progress, f"更新: {change.path.name}")

                try:
                    await self._update_file(change.path)
                    result.updated_files.append(change.path)
                except Exception as e:
                    result.failed_files.append((change.path, str(e)))

            await self._update_index()

            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            result.success = len(result.failed_files) == 0

        except Exception as e:
            result.success = False
            result.error = str(e)

        return result

    async def _update_file(self, file_path: Path) -> None:
        """更新单个文件的文档"""
        parse_result = self.parser.parse_file(file_path)

        for module in parse_result.modules:
            await self._update_module_doc(module)

    async def _update_module_doc(self, module: ModuleInfo) -> None:
        """更新模块文档"""
        doc_content = self.wiki_manager.generator.generate_module_doc(module)
        doc_path = self.wiki_manager.storage.get_module_path(module.name)
        await self.wiki_manager.storage.save_document(doc_path, doc_content)

    async def _update_index(self) -> None:
        """更新索引"""
        await self.wiki_manager._generate_index()

    def analyze_impact(self, changes: list[FileChange]) -> dict[str, Any]:
        """分析变更影响"""
        impact = {
            "direct": [],
            "indirect": [],
            "affected_modules": set(),
        }

        for change in changes:
            if change.change_type == ChangeType.DELETED:
                continue

            parse_result = self.parser.parse_file(change.path)

            for module in parse_result.modules:
                impact["direct"].append({
                    "file": str(change.path),
                    "module": module.name,
                    "classes": [c.name for c in module.classes],
                    "functions": [f.name for f in module.functions],
                })

                for dep in parse_result.dependencies:
                    if dep.source == module.name:
                        impact["affected_modules"].add(dep.target)

        impact["affected_modules"] = list(impact["affected_modules"])
        return impact

    def get_outdated_docs(self) -> list[Path]:
        """获取过时的文档"""
        outdated = []

        for doc_path in self.wiki_manager.storage.list_documents():
            module_name = self._extract_module_name(doc_path)
            if not module_name:
                continue

            source_file = self._find_source_file(module_name)
            if not source_file:
                outdated.append(doc_path)
                continue

            if self.change_detector.is_file_changed(
                source_file,
                self.wiki_manager.project.path
            ):
                outdated.append(doc_path)

        return outdated

    def _extract_module_name(self, doc_path: Path) -> Optional[str]:
        """从文档路径提取模块名"""
        try:
            rel_path = doc_path.relative_to(
                self.wiki_manager.storage.language_dir / "modules"
            )
            return str(rel_path.with_suffix("")).replace("/", ".")
        except ValueError:
            return None

    def _find_source_file(self, module_name: str) -> Optional[Path]:
        """查找模块对应的源文件"""
        parts = module_name.split(".")
        project_path = self.wiki_manager.project.path

        possible_paths = [
            project_path / "/".join(parts) / "__init__.py",
            project_path / "/".join(parts[:-1]) / f"{parts[-1]}.py",
            project_path / f"{'/'.join(parts)}.py",
        ]

        for path in possible_paths:
            if path.exists():
                return path

        return None
