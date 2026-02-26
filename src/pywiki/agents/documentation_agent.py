"""
文档生成 Agent
协调各文档生成器，通过 AI Agent 自动生成项目文档
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from pywiki.agents.base import BaseAgent, AgentContext, AgentResult, AgentPriority
from pywiki.generators.docs.base import DocType, DocGeneratorContext
from pywiki.generators.docs.overview_generator import OverviewGenerator
from pywiki.generators.docs.techstack_generator import TechStackGenerator
from pywiki.generators.docs.api_generator import APIGenerator
from pywiki.generators.docs.architecture_generator import ArchitectureDocGenerator
from pywiki.generators.docs.module_generator import ModuleGenerator
from pywiki.generators.docs.dependencies_generator import DependenciesGenerator
from pywiki.generators.docs.config_generator import ConfigGenerator
from pywiki.generators.docs.development_generator import DevelopmentGenerator
from pywiki.generators.docs.database_generator import DatabaseGenerator
from pywiki.generators.docs.tsd_generator import TSDGenerator
from pywiki.config.models import Language


class DocGenerationStatus(str, Enum):
    """文档生成状态"""
    IDLE = "idle"
    PREPARING = "preparing"
    GENERATING = "generating"
    SAVING = "saving"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class DocGenerationProgress:
    """文档生成进度"""
    status: DocGenerationStatus = DocGenerationStatus.IDLE
    current_doc: str = ""
    completed_docs: list[str] = field(default_factory=list)
    total_docs: int = 0
    errors: list[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@dataclass
class DocGenerationResult:
    """文档生成结果"""
    success: bool
    generated_files: list[Path] = field(default_factory=list)
    failed_docs: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    error: Optional[str] = None


class DocumentationAgent(BaseAgent):
    """文档生成 Agent
    
    协调各文档生成器，自动生成项目文档
    对标 Qoder Wiki 的文档生成能力
    """

    name = "documentation_agent"
    description = "文档生成专家 - 自动生成项目概述、技术栈、API、架构等文档"
    priority = AgentPriority.HIGH

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._generators: dict[DocType, BaseAgent] = {}
        self._progress = DocGenerationProgress()
        self._progress_callback: Optional[Callable[[DocGenerationProgress], None]] = None

    def get_system_prompt(self) -> str:
        return """你是一个专业的技术文档撰写专家。
你的任务是：
1. 分析项目代码结构
2. 生成清晰、准确的技术文档
3. 提取关键信息并组织成易读的格式
4. 确保文档的完整性和准确性

请生成高质量的技术文档。"""

    def register_progress_callback(self, callback: Callable[[DocGenerationProgress], None]) -> None:
        """注册进度回调"""
        self._progress_callback = callback

    def _notify_progress(self) -> None:
        """通知进度更新"""
        if self._progress_callback:
            self._progress_callback(self._progress)

    async def execute(self, context: AgentContext) -> AgentResult:
        """执行文档生成"""
        self.status = "running"
        self._progress = DocGenerationProgress(
            status=DocGenerationStatus.PREPARING,
            start_time=datetime.now()
        )
        self._notify_progress()

        try:
            doc_types = context.metadata.get("doc_types", list(DocType))
            output_dir = context.metadata.get("output_dir", Path(".python-wiki/repowiki"))
            language = context.metadata.get("language", Language.ZH)
            llm_client = context.metadata.get("llm_client") or self.llm_client

            self._progress.status = DocGenerationStatus.GENERATING
            self._progress.total_docs = len(doc_types)
            self._notify_progress()

            results = await self._generate_all_docs(
                context=context,
                doc_types=doc_types,
                output_dir=output_dir,
                language=language,
                llm_client=llm_client,
            )

            self._progress.status = DocGenerationStatus.COMPLETED
            self._progress.end_time = datetime.now()
            self._notify_progress()

            duration = (self._progress.end_time - self._progress.start_time).total_seconds()

            self._record_execution(context, AgentResult.success_result(
                data={
                    "generated_files": [str(p) for p in results.generated_files],
                    "failed_docs": results.failed_docs,
                    "duration_seconds": duration,
                },
                message=f"成功生成 {len(results.generated_files)} 个文档",
                confidence=0.9,
            ))

            self.status = "completed"
            return AgentResult.success_result(
                data={
                    "generated_files": [str(p) for p in results.generated_files],
                    "failed_docs": results.failed_docs,
                    "duration_seconds": duration,
                },
                message=f"成功生成 {len(results.generated_files)} 个文档",
                confidence=0.9,
            )

        except Exception as e:
            self._progress.status = DocGenerationStatus.ERROR
            self._progress.errors.append(str(e))
            self._progress.end_time = datetime.now()
            self._notify_progress()

            self.status = "error"
            return AgentResult.error_result(f"文档生成失败: {str(e)}")

    async def _generate_all_docs(
        self,
        context: AgentContext,
        doc_types: list[DocType],
        output_dir: Path,
        language: Language,
        llm_client: Any,
    ) -> DocGenerationResult:
        """生成所有文档"""
        result = DocGenerationResult(success=True)
        output_path = context.project_path / output_dir if context.project_path else Path(output_dir)

        generators = self._get_generators(language)

        for doc_type in doc_types:
            self._progress.current_doc = doc_type.value
            self._notify_progress()

            generator = generators.get(doc_type)
            if not generator:
                continue

            try:
                doc_context = DocGeneratorContext(
                    project_path=context.project_path or Path("."),
                    project_name=context.project_name or "project",
                    parse_result=context.metadata.get("parse_result"),
                    language=language,
                    output_dir=output_path,
                    metadata={"llm_client": llm_client},
                )

                doc_result = await generator.generate(doc_context)

                if doc_result.success:
                    file_path = output_path / doc_result.file_path.name
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(doc_result.content, encoding="utf-8")
                    result.generated_files.append(file_path)
                    self._progress.completed_docs.append(doc_type.value)
                else:
                    result.failed_docs.append(doc_type.value)
                    self._progress.errors.append(f"{doc_type.value}: {doc_result.message}")

            except Exception as e:
                result.failed_docs.append(doc_type.value)
                self._progress.errors.append(f"{doc_type.value}: {str(e)}")

            self._notify_progress()

        result.success = len(result.generated_files) > 0
        return result

    def _get_generators(self, language: Language) -> dict[DocType, Any]:
        """获取文档生成器"""
        return {
            DocType.OVERVIEW: OverviewGenerator(language=language),
            DocType.TECH_STACK: TechStackGenerator(language=language),
            DocType.API: APIGenerator(language=language),
            DocType.ARCHITECTURE: ArchitectureDocGenerator(language=language),
            DocType.MODULE: ModuleGenerator(language=language),
            DocType.DEPENDENCIES: DependenciesGenerator(language=language),
            DocType.CONFIGURATION: ConfigGenerator(language=language),
            DocType.DEVELOPMENT: DevelopmentGenerator(language=language),
            DocType.DATABASE: DatabaseGenerator(language=language),
            DocType.TSD: TSDGenerator(language=language),
        }

    async def generate_single_doc(
        self,
        context: AgentContext,
        doc_type: DocType,
        language: Language = Language.ZH,
    ) -> AgentResult:
        """生成单个文档"""
        generators = self._get_generators(language)
        generator = generators.get(doc_type)

        if not generator:
            return AgentResult.error_result(f"未知的文档类型: {doc_type}")

        output_dir = context.metadata.get("output_dir", Path(".python-wiki/repowiki"))
        output_path = context.project_path / output_dir if context.project_path else Path(output_dir)

        doc_context = DocGeneratorContext(
            project_path=context.project_path or Path("."),
            project_name=context.project_name or "project",
            parse_result=context.metadata.get("parse_result"),
            language=language,
            output_dir=output_path,
            metadata={"llm_client": self.llm_client},
        )

        try:
            doc_result = await generator.generate(doc_context)

            if doc_result.success:
                file_path = output_path / doc_result.file_path.name
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(doc_result.content, encoding="utf-8")

                return AgentResult.success_result(
                    data={"file_path": str(file_path), "content": doc_result.content},
                    message=f"成功生成 {doc_type.value} 文档",
                    confidence=0.9,
                )
            else:
                return AgentResult.error_result(doc_result.message)

        except Exception as e:
            return AgentResult.error_result(f"生成失败: {str(e)}")

    def get_supported_doc_types(self) -> list[dict[str, str]]:
        """获取支持的文档类型"""
        return [
            {"type": DocType.OVERVIEW.value, "description": "项目概述文档"},
            {"type": DocType.TECH_STACK.value, "description": "技术栈文档"},
            {"type": DocType.API.value, "description": "API 文档"},
            {"type": DocType.ARCHITECTURE.value, "description": "架构文档"},
            {"type": DocType.MODULE.value, "description": "模块文档"},
            {"type": DocType.DEPENDENCIES.value, "description": "依赖文档"},
            {"type": DocType.CONFIGURATION.value, "description": "配置文档"},
            {"type": DocType.DEVELOPMENT.value, "description": "开发指南"},
            {"type": DocType.DATABASE.value, "description": "数据库文档"},
            {"type": DocType.TSD.value, "description": "技术设计文档"},
        ]

    def get_progress(self) -> DocGenerationProgress:
        """获取当前进度"""
        return self._progress
