"""
文档生成 Agent
协调各文档生成器，通过 AI Agent 自动生成项目文档
"""

import asyncio
import time
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
from pywiki.generators.docs.implicit_knowledge_generator import ImplicitKnowledgeGenerator
from pywiki.generators.docs.test_coverage_generator import TestCoverageGenerator
from pywiki.generators.docs.code_quality_generator import CodeQualityGenerator
from pywiki.generators.docs.technical_design_spec_generator import TechnicalDesignSpecGenerator
from pywiki.config.models import Language
from pywiki.monitor.logger import logger


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
    skipped_docs: list[str] = field(default_factory=list)
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
        self._cache_enabled: bool = True
        self._max_concurrent: int = 5
        self._language: Language = Language.ZH
        logger.debug("DocumentationAgent 初始化完成")

    def get_system_prompt(self) -> str:
        if self._language == Language.ZH:
            return """# 角色定义
你是一位资深的技术文档撰写专家，精通多种编程语言和软件架构，擅长将复杂的代码逻辑转化为清晰易懂的文档。

# 核心职责
1. **代码分析**: 深入理解项目结构、模块关系、API设计
2. **信息提取**: 识别关键功能、设计决策、技术亮点
3. **文档撰写**: 生成结构清晰、内容准确的技术文档
4. **质量把控**: 确保文档的完整性、准确性和可读性

# 文档写作规范
- **结构化**: 使用标题层级组织内容，逻辑清晰
- **准确性**: 基于代码事实，避免模糊表述
- **完整性**: 覆盖所有重要模块和接口
- **可读性**: 使用简洁明了的语言，适当使用代码示例
- **一致性**: 术语使用统一，格式风格一致

# 输出格式要求
- 使用标准 Markdown 格式
- 代码块标注语言类型
- 表格用于展示结构化数据
- 列表用于枚举和步骤说明

请务必使用中文回答。"""
        else:
            return """# Role Definition
You are a senior technical documentation expert, proficient in multiple programming languages and software architectures, skilled at transforming complex code logic into clear and understandable documentation.

# Core Responsibilities
1. **Code Analysis**: Deep understanding of project structure, module relationships, API design
2. **Information Extraction**: Identify key features, design decisions, technical highlights
3. **Documentation Writing**: Generate well-structured, accurate technical documentation
4. **Quality Control**: Ensure completeness, accuracy, and readability of documentation

# Documentation Writing Standards
- **Structured**: Use heading levels to organize content with clear logic
- **Accurate**: Based on code facts, avoid vague statements
- **Complete**: Cover all important modules and interfaces
- **Readable**: Use concise language with appropriate code examples
- **Consistent**: Unified terminology and formatting style

# Output Format Requirements
- Use standard Markdown format
- Code blocks with language type annotation
- Tables for structured data
- Lists for enumeration and step-by-step instructions

Please respond in English."""

    def register_progress_callback(self, callback: Callable[[DocGenerationProgress], None]) -> None:
        """注册进度回调"""
        self._progress_callback = callback

    def _notify_progress(self) -> None:
        """通知进度更新"""
        if self._progress_callback:
            self._progress_callback(self._progress)

    def set_cache_enabled(self, enabled: bool) -> None:
        """设置是否启用缓存"""
        self._cache_enabled = enabled

    def set_max_concurrent(self, max_concurrent: int) -> None:
        """设置最大并发数"""
        self._max_concurrent = max_concurrent

    async def execute(self, context: AgentContext) -> AgentResult:
        """执行文档生成"""
        logger.info(f"DocumentationAgent 开始执行: project={context.project_name}")
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
            self._language = language
            llm_client = context.metadata.get("llm_client") or self.llm_client
            incremental = context.metadata.get("incremental", False)

            logger.info(f"文档生成参数: types={[d.value for d in doc_types]}, language={language}, incremental={incremental}")

            self._progress.status = DocGenerationStatus.GENERATING
            self._progress.total_docs = len(doc_types)
            self._notify_progress()

            results = await self._generate_all_docs(
                context=context,
                doc_types=doc_types,
                output_dir=output_dir,
                language=language,
                llm_client=llm_client,
                incremental=incremental,
            )

            self._progress.status = DocGenerationStatus.COMPLETED
            self._progress.end_time = datetime.now()
            self._notify_progress()

            duration = (self._progress.end_time - self._progress.start_time).total_seconds()

            logger.info(
                f"DocumentationAgent 执行完成: "
                f"成功={len(results.generated_files)}, 失败={len(results.failed_docs)}, "
                f"跳过={len(results.skipped_docs)}, 耗时={duration:.2f}s"
            )

            self._record_execution(context, AgentResult.success_result(
                data={
                    "generated_files": [str(p) for p in results.generated_files],
                    "failed_docs": results.failed_docs,
                    "skipped_docs": results.skipped_docs,
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
                    "skipped_docs": results.skipped_docs,
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

            logger.log_exception(f"DocumentationAgent 执行失败: {context.project_name}", e)

            self.status = "error"
            return AgentResult.error_result(f"文档生成失败: {str(e)}")

    async def _generate_single_doc(
        self,
        doc_type: DocType,
        generator: Any,
        context: AgentContext,
        output_path: Path,
        language: Language,
        llm_client: Any,
        incremental: bool = False,
    ) -> tuple[DocType, Optional[Path], Optional[str], bool]:
        """生成单个文档，返回 (doc_type, file_path, error, skipped)"""
        start_time = time.time()
        logger.info(f"开始生成文档: {doc_type.value}")
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
                file_path = doc_context.get_output_path(doc_type)
                
                if incremental and self._cache_enabled:
                    if not doc_context.needs_regeneration(doc_type, doc_result.content):
                        duration_ms = (time.time() - start_time) * 1000
                        logger.info(f"文档未变更，跳过写入: {doc_type.value}, 耗时={duration_ms:.0f}ms")
                        return (doc_type, file_path, None, True)
                
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(doc_result.content, encoding="utf-8")
                
                if self._cache_enabled:
                    content_hash = doc_context.compute_content_hash(doc_result.content)
                    doc_context.save_cached_hash(doc_type, content_hash)
                
                duration_ms = (time.time() - start_time) * 1000
                content_length = len(doc_result.content) if doc_result.content else 0
                logger.info(f"文档生成成功: {doc_type.value} -> {file_path}, 耗时={duration_ms:.0f}ms, 内容长度={content_length}")
                return (doc_type, file_path, None, False)
            else:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(f"文档生成失败: {doc_type.value} - {doc_result.message}, 耗时={duration_ms:.0f}ms")
                return (doc_type, None, doc_result.message, False)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.log_exception(f"文档生成异常: {doc_type.value}, 耗时={duration_ms:.0f}ms", e)
            return (doc_type, None, str(e), False)

    async def _generate_all_docs(
        self,
        context: AgentContext,
        doc_types: list[DocType],
        output_dir: Path,
        language: Language,
        llm_client: Any,
        incremental: bool = False,
    ) -> DocGenerationResult:
        """并发生成所有文档"""
        start_time = time.time()
        result = DocGenerationResult(success=True)
        
        output_path = output_dir / language.value
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"开始批量生成文档: 类型数={len(doc_types)}, 并发数={self._max_concurrent}, 输出路径={output_path}")
        generators = self._get_generators(language)

        semaphore = asyncio.Semaphore(self._max_concurrent)

        async def generate_with_semaphore(doc_type: DocType) -> tuple[DocType, Optional[Path], Optional[str], bool]:
            async with semaphore:
                self._progress.current_doc = doc_type.value
                self._notify_progress()
                
                generator = generators.get(doc_type)
                if not generator:
                    logger.warning(f"未找到文档生成器: {doc_type.value}")
                    return (doc_type, None, f"未找到生成器: {doc_type.value}", False)
                
                return await self._generate_single_doc(
                    doc_type, generator, context, output_path, language, llm_client, incremental
                )

        tasks = [generate_with_semaphore(doc_type) for doc_type in doc_types]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, res in enumerate(results):
            doc_type = doc_types[i]
            if isinstance(res, Exception):
                result.failed_docs.append(doc_type.value)
                self._progress.errors.append(f"{doc_type.value}: {str(res)}")
                logger.error(f"文档生成异常: {doc_type.value} - {res}")
            else:
                doc_type_result, file_path, error, skipped = res
                if file_path:
                    if skipped:
                        result.skipped_docs.append(doc_type_result.value)
                    else:
                        result.generated_files.append(file_path)
                    self._progress.completed_docs.append(doc_type_result.value)
                else:
                    result.failed_docs.append(doc_type_result.value)
                    if error:
                        self._progress.errors.append(f"{doc_type_result.value}: {error}")
            
            self._notify_progress()

        result.success = len(result.generated_files) > 0 or len(result.skipped_docs) > 0
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"批量文档生成完成: 成功={len(result.generated_files)}, "
            f"失败={len(result.failed_docs)}, 跳过={len(result.skipped_docs)}, "
            f"总耗时={duration_ms:.0f}ms"
        )
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
            DocType.IMPLICIT_KNOWLEDGE: ImplicitKnowledgeGenerator(language=language),
            DocType.TEST_COVERAGE: TestCoverageGenerator(language=language),
            DocType.CODE_QUALITY: CodeQualityGenerator(language=language),
            DocType.TECHNICAL_DESIGN_SPEC: TechnicalDesignSpecGenerator(language=language),
        }

    async def generate_single_doc(
        self,
        context: AgentContext,
        doc_type: DocType,
        language: Language = Language.ZH,
    ) -> AgentResult:
        """生成单个文档"""
        start_time = time.time()
        logger.info(f"生成单个文档开始: type={doc_type.value}, project={context.project_name}")
        generators = self._get_generators(language)
        generator = generators.get(doc_type)

        if not generator:
            logger.error(f"未知的文档类型: {doc_type.value}")
            return AgentResult.error_result(f"未知的文档类型: {doc_type}")

        output_dir = context.metadata.get("output_dir", Path(".python-wiki/repowiki"))
        output_path = output_dir / language.value
        output_path.mkdir(parents=True, exist_ok=True)

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
                file_path = doc_context.get_output_path(doc_type)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(doc_result.content, encoding="utf-8")
                
                if self._cache_enabled:
                    content_hash = doc_context.compute_content_hash(doc_result.content)
                    doc_context.save_cached_hash(doc_type, content_hash)
                
                duration_ms = (time.time() - start_time) * 1000
                content_length = len(doc_result.content) if doc_result.content else 0
                logger.info(f"单个文档生成成功: {doc_type.value} -> {file_path}, 耗时={duration_ms:.0f}ms, 内容长度={content_length}")

                return AgentResult.success_result(
                    data={"file_path": str(file_path), "content": doc_result.content},
                    message=f"成功生成 {doc_type.value} 文档",
                    confidence=0.9,
                )
            else:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(f"单个文档生成失败: {doc_type.value} - {doc_result.message}, 耗时={duration_ms:.0f}ms")
                return AgentResult.error_result(doc_result.message)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.log_exception(f"生成文档异常: {doc_type.value}, 耗时={duration_ms:.0f}ms", e)
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
            {"type": DocType.IMPLICIT_KNOWLEDGE.value, "description": "隐性知识文档"},
            {"type": DocType.TEST_COVERAGE.value, "description": "测试覆盖分析"},
            {"type": DocType.CODE_QUALITY.value, "description": "代码质量分析"},
            {"type": DocType.TECHNICAL_DESIGN_SPEC.value, "description": "技术设计规范（综合文档）"},
        ]

    def get_progress(self) -> DocGenerationProgress:
        """获取当前进度"""
        return self._progress

    async def generate_incremental(
        self,
        context: AgentContext,
        changed_files: list[str],
        language: Language = Language.ZH,
    ) -> AgentResult:
        """增量生成文档
        
        Args:
            context: Agent 上下文
            changed_files: 变更的文件列表
            language: 文档语言
        """
        start_time = time.time()
        logger.info(f"增量文档生成开始: 变更文件数={len(changed_files)}")
        
        affected_doc_types = self._analyze_affected_docs(changed_files)
        logger.info(f"受影响的文档类型: {[d.value for d in affected_doc_types]}")
        
        if not affected_doc_types:
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"没有需要更新的文档, 耗时={duration_ms:.0f}ms")
            return AgentResult.success_result(
                data={"updated_docs": []},
                message="没有需要更新的文档",
                confidence=1.0,
            )
        
        context.metadata["doc_types"] = affected_doc_types
        context.metadata["incremental"] = True
        
        result = await self.execute(context)
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"增量文档生成完成: 耗时={duration_ms:.0f}ms")
        return result

    def _analyze_affected_docs(self, changed_files: list[str]) -> list[DocType]:
        """分析受影响的文档类型"""
        affected = set()
        
        for file_path in changed_files:
            file_lower = file_path.lower()
            
            if any(ext in file_lower for ext in [".py", ".java", ".ts", ".tsx", ".js"]):
                affected.add(DocType.OVERVIEW)
                affected.add(DocType.API)
                affected.add(DocType.MODULE)
                affected.add(DocType.ARCHITECTURE)
                affected.add(DocType.IMPLICIT_KNOWLEDGE)
                affected.add(DocType.CODE_QUALITY)
            
            if "test" in file_lower:
                affected.add(DocType.TEST_COVERAGE)
            
            if any(name in file_lower for name in ["config", "settings", ".env"]):
                affected.add(DocType.CONFIGURATION)
            
            if any(name in file_lower for name in ["requirements", "pom.xml", "package.json", "build.gradle"]):
                affected.add(DocType.DEPENDENCIES)
                affected.add(DocType.TECH_STACK)
            
            if any(name in file_lower for name in ["readme", "contributing", "changelog"]):
                affected.add(DocType.DEVELOPMENT)
            
            if any(name in file_lower for name in ["model", "schema", "entity", "migration"]):
                affected.add(DocType.DATABASE)
        
        return list(affected)
