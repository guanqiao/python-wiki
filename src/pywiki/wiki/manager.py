"""
Wiki 管理器
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from pywiki.config.models import ProjectConfig, WikiConfig
from pywiki.parsers.python import PythonParser
from pywiki.parsers.types import ModuleInfo, ParseResult
from pywiki.llm.client import LLMClient
from pywiki.generators.markdown import MarkdownGenerator
from pywiki.wiki.storage import WikiStorage
from pywiki.wiki.history import WikiHistory


class GenerationStatus(str, Enum):
    IDLE = "idle"
    SCANNING = "scanning"
    PARSING = "parsing"
    GENERATING = "generating"
    SYNCING = "syncing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class GenerationProgress:
    status: GenerationStatus = GenerationStatus.IDLE
    total_files: int = 0
    processed_files: int = 0
    current_file: str = ""
    current_stage: str = ""
    start_time: Optional[datetime] = None
    errors: list[str] = field(default_factory=list)


class WikiManager:
    """Wiki 文档管理器"""

    def __init__(
        self,
        project: ProjectConfig,
        llm_client: LLMClient,
        progress_callback: Optional[Callable[[GenerationProgress], None]] = None,
    ):
        self.project = project
        self.llm_client = llm_client
        self.wiki_config = project.wiki
        self.progress_callback = progress_callback

        self.parser = PythonParser(
            exclude_patterns=self.wiki_config.exclude_patterns,
            include_private=self.wiki_config.include_private,
        )

        self.storage = WikiStorage(
            output_dir=project.path / self.wiki_config.output_dir,
            language=self.wiki_config.language,
        )

        self.history = WikiHistory(self.storage.history_dir)
        self.generator = MarkdownGenerator(language=self.wiki_config.language)

        self._progress = GenerationProgress()
        self._parse_result: Optional[ParseResult] = None

    async def generate_full(self) -> bool:
        """生成完整 Wiki 文档"""
        self._progress = GenerationProgress(
            status=GenerationStatus.SCANNING,
            start_time=datetime.now()
        )
        self._notify_progress()

        try:
            await self._scan_project()
            await self._parse_code()
            await self._generate_documents()
            await self._sync_to_git()

            self._progress.status = GenerationStatus.COMPLETED
            self._notify_progress()
            return True

        except Exception as e:
            self._progress.status = GenerationStatus.ERROR
            self._progress.errors.append(str(e))
            self._notify_progress()
            return False

    async def generate_incremental(self, changed_files: list[Path]) -> bool:
        """增量更新 Wiki 文档"""
        self._progress = GenerationProgress(
            status=GenerationStatus.PARSING,
            start_time=datetime.now()
        )
        self._notify_progress()

        try:
            self._progress.total_files = len(changed_files)

            for i, file_path in enumerate(changed_files):
                self._progress.current_file = str(file_path)
                self._progress.processed_files = i + 1
                self._notify_progress()

                result = self.parser.parse_file(file_path)
                await self._generate_module_docs(result.modules)

            self._progress.status = GenerationStatus.COMPLETED
            self._notify_progress()
            return True

        except Exception as e:
            self._progress.status = GenerationStatus.ERROR
            self._progress.errors.append(str(e))
            self._notify_progress()
            return False

    async def _scan_project(self) -> None:
        """扫描项目文件"""
        self._progress.current_stage = "代码扫描"
        self._notify_progress()

        project_path = self.project.path
        python_files = list(project_path.rglob("*.py"))

        self._progress.total_files = len(python_files)
        self._notify_progress()

    async def _parse_code(self) -> None:
        """解析代码"""
        self._progress.status = GenerationStatus.PARSING
        self._progress.current_stage = "结构分析"
        self._notify_progress()

        self._parse_result = self.parser.parse_directory(self.project.path)

        self._progress.total_files = len(self._parse_result.modules)
        self._notify_progress()

    async def _generate_documents(self) -> None:
        """生成文档"""
        self._progress.status = GenerationStatus.GENERATING
        self._progress.current_stage = "文档生成"
        self._notify_progress()

        if not self._parse_result:
            return

        modules = self._parse_result.modules

        for i, module in enumerate(modules):
            self._progress.current_file = module.name
            self._progress.processed_files = i + 1
            self._notify_progress()

            doc_content = self.generator.generate_module_doc(module)
            doc_path = self.storage.get_module_path(module.name)
            await self.storage.save_document(doc_path, doc_content)

        if self.wiki_config.generate_diagrams:
            await self._generate_diagrams()

        await self._generate_index()

    async def _generate_diagrams(self) -> None:
        """生成图表"""
        from pywiki.generators.diagrams import (
            ArchitectureDiagramGenerator,
            ClassDiagramGenerator,
            ERDiagramGenerator,
        )

        self._progress.current_stage = "图表生成"
        self._notify_progress()

        if self._parse_result and self._parse_result.modules:
            arch_gen = ArchitectureDiagramGenerator()
            arch_diagram = arch_gen.generate_from_modules(
                [{"name": m.name} for m in self._parse_result.modules]
            )
            await self.storage.save_document(
                self.storage.output_dir / "architecture.md",
                self.generator.generate_architecture_doc(
                    "系统架构",
                    "项目架构概览",
                    arch_diagram
                )
            )

            class_gen = ClassDiagramGenerator()
            for module in self._parse_result.modules:
                for cls in module.classes:
                    class_diagram = class_gen.generate_from_class_info({
                        "name": cls.name,
                        "bases": cls.bases,
                        "properties": [{"name": p.name, "type_hint": p.type_hint} for p in cls.properties],
                        "methods": [{"name": m.name, "parameters": m.parameters} for m in cls.methods],
                    })
                    doc_path = self.storage.output_dir / "classes" / f"{cls.name}.md"
                    doc_path.parent.mkdir(parents=True, exist_ok=True)
                    await self.storage.save_document(doc_path, f"# {cls.name}\n\n{class_diagram}")

    async def _generate_index(self) -> None:
        """生成索引页"""
        if not self._parse_result:
            return

        index_content = f"""# {self.project.name} Wiki

## 目录

### 模块

"""
        for module in self._parse_result.modules:
            index_content += f"- [{module.name}](modules/{module.name.replace('.', '/')}.md)\n"

        index_content += "\n### 架构\n\n- [系统架构](architecture.md)\n"

        await self.storage.save_document(
            self.storage.output_dir / "index.md",
            index_content
        )

    async def _sync_to_git(self) -> None:
        """同步到 Git"""
        self._progress.status = GenerationStatus.SYNCING
        self._progress.current_stage = "Git 同步"
        self._notify_progress()

    def _notify_progress(self) -> None:
        if self.progress_callback:
            self.progress_callback(self._progress)

    def get_progress(self) -> GenerationProgress:
        return self._progress

    def search(self, query: str) -> list[dict]:
        """搜索 Wiki 内容"""
        return self.storage.search(query)

    def get_document(self, doc_path: Path) -> Optional[str]:
        """获取文档内容"""
        return self.storage.get_document(doc_path)

    def get_history(self, doc_path: Path) -> list[dict]:
        """获取文档历史"""
        return self.history.get_history(doc_path)
