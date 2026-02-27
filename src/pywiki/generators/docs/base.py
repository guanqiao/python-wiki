"""
文档生成器基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, Template

from pywiki.config.models import Language
from pywiki.parsers.types import ModuleInfo, ParseResult


class DocType(str, Enum):
    """文档类型"""
    OVERVIEW = "overview"
    TECH_STACK = "tech-stack"
    API = "api"
    ARCHITECTURE = "architecture"
    MODULE = "module"
    DATABASE = "database"
    CONFIGURATION = "configuration"
    DEVELOPMENT = "development"
    DEPENDENCIES = "dependencies"
    TSD = "tsd"


@dataclass
class DocGeneratorResult:
    """文档生成结果"""
    doc_type: DocType
    content: str
    file_path: Path
    success: bool = True
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_type": self.doc_type.value,
            "file_path": str(self.file_path),
            "success": self.success,
            "message": self.message,
            "metadata": self.metadata,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class DocGeneratorContext:
    """文档生成上下文"""
    project_path: Path
    project_name: str
    parse_result: Optional[ParseResult] = None
    language: Language = Language.ZH
    output_dir: Path = Path(".python-wiki/repowiki")
    template_dir: Optional[Path] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    project_language: str = "python"

    def detect_project_language(self) -> str:
        """检测项目主要编程语言"""
        if not self.project_path:
            return "python"
        
        language_scores = {
            "python": 0,
            "java": 0,
            "typescript": 0,
        }
        
        python_files = list(self.project_path.rglob("*.py"))
        python_files = [f for f in python_files if "__pycache__" not in str(f)]
        language_scores["python"] = len(python_files)
        
        java_files = list(self.project_path.rglob("*.java"))
        language_scores["java"] = len(java_files)
        
        ts_files = list(self.project_path.rglob("*.ts")) + list(self.project_path.rglob("*.tsx"))
        ts_files = [f for f in ts_files if "node_modules" not in str(f)]
        language_scores["typescript"] = len(ts_files)
        
        if (self.project_path / "pom.xml").exists() or (self.project_path / "build.gradle").exists():
            language_scores["java"] += 100
        
        if (self.project_path / "package.json").exists():
            language_scores["typescript"] += 100
        
        if (self.project_path / "pyproject.toml").exists() or (self.project_path / "setup.py").exists():
            language_scores["python"] += 100
        
        if max(language_scores.values()) == 0:
            return "python"
        
        return max(language_scores.items(), key=lambda x: x[1])[0]

    def get_output_path(self, doc_type: DocType) -> Path:
        """获取文档输出路径"""
        path_map = {
            DocType.OVERVIEW: self.output_dir / "overview.md",
            DocType.TECH_STACK: self.output_dir / "tech-stack.md",
            DocType.API: self.output_dir / "api" / "index.md",
            DocType.ARCHITECTURE: self.output_dir / "architecture" / "system-architecture.md",
            DocType.MODULE: self.output_dir / "modules" / "index.md",
            DocType.DATABASE: self.output_dir / "database" / "schema.md",
            DocType.CONFIGURATION: self.output_dir / "configuration" / "environment.md",
            DocType.DEVELOPMENT: self.output_dir / "development" / "getting-started.md",
            DocType.DEPENDENCIES: self.output_dir / "dependencies" / "external.md",
            DocType.TSD: self.output_dir / "tsd" / "design-decisions.md",
        }
        return path_map.get(doc_type, self.output_dir / f"{doc_type.value}.md")


class BaseDocGenerator(ABC):
    """文档生成器基类"""

    doc_type: DocType = DocType.OVERVIEW
    template_name: str = "base.md.j2"

    def __init__(
        self,
        language: Language = Language.ZH,
        template_dir: Optional[Path] = None,
    ):
        self.language = language
        self.template_dir = template_dir or self._get_default_template_dir()
        self._env: Optional[Environment] = None
        self._init_labels()

    def _get_default_template_dir(self) -> Path:
        """获取默认模板目录"""
        return Path(__file__).parent / "templates"

    def _init_labels(self) -> None:
        """初始化标签"""
        if self.language == Language.ZH:
            self.labels = {
                "overview": "概述",
                "description": "描述",
                "modules": "模块",
                "classes": "类",
                "functions": "函数",
                "properties": "属性",
                "methods": "方法",
                "parameters": "参数",
                "returns": "返回值",
                "raises": "异常",
                "example": "示例",
                "inheritance": "继承关系",
                "dependencies": "依赖",
                "type": "类型",
                "default": "默认值",
                "visibility": "可见性",
                "architecture": "架构",
                "api_reference": "API 参考",
                "table_of_contents": "目录",
                "tech_stack": "技术栈",
                "external_dependencies": "外部依赖",
                "internal_dependencies": "内部依赖",
                "configuration": "配置",
                "environment": "环境",
                "development": "开发",
                "database": "数据库",
                "design_decisions": "设计决策",
                "tech_debt": "技术债务",
                "version": "版本",
                "license": "许可证",
                "author": "作者",
                "created_at": "创建时间",
                "updated_at": "更新时间",
            }
        else:
            self.labels = {
                "overview": "Overview",
                "description": "Description",
                "modules": "Modules",
                "classes": "Classes",
                "functions": "Functions",
                "properties": "Properties",
                "methods": "Methods",
                "parameters": "Parameters",
                "returns": "Returns",
                "raises": "Raises",
                "example": "Example",
                "inheritance": "Inheritance",
                "dependencies": "Dependencies",
                "type": "Type",
                "default": "Default",
                "visibility": "Visibility",
                "architecture": "Architecture",
                "api_reference": "API Reference",
                "table_of_contents": "Table of Contents",
                "tech_stack": "Tech Stack",
                "external_dependencies": "External Dependencies",
                "internal_dependencies": "Internal Dependencies",
                "configuration": "Configuration",
                "environment": "Environment",
                "development": "Development",
                "database": "Database",
                "design_decisions": "Design Decisions",
                "tech_debt": "Technical Debt",
                "version": "Version",
                "license": "License",
                "author": "Author",
                "created_at": "Created At",
                "updated_at": "Updated At",
            }

    def _get_template_env(self) -> Environment:
        """获取 Jinja2 环境"""
        if self._env is None:
            self._env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=False,
                trim_blocks=True,
                lstrip_blocks=True,
            )
        return self._env

    def get_template(self) -> Template:
        """获取模板"""
        env = self._get_template_env()
        try:
            return env.get_template(self.template_name)
        except Exception:
            return self._get_fallback_template()

    def _get_fallback_template(self) -> Template:
        """获取备用模板"""
        env = Environment()
        return env.from_string("{{ content }}")

    @abstractmethod
    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成文档"""
        pass

    def render_template(self, **kwargs: Any) -> str:
        """渲染模板"""
        template = self.get_template()
        return template.render(labels=self.labels, **kwargs)

    async def generate_with_llm(
        self,
        prompt: str,
        llm_client: Any,
        system_prompt: Optional[str] = None,
    ) -> str:
        """使用 LLM 增强文档内容"""
        if not llm_client:
            return ""
        
        try:
            if system_prompt:
                return await llm_client.agenerate(prompt, system_prompt=system_prompt)
            return await llm_client.agenerate(prompt)
        except Exception:
            return ""

    def create_result(
        self,
        content: str,
        context: DocGeneratorContext,
        success: bool = True,
        message: str = "",
        metadata: Optional[dict] = None,
    ) -> DocGeneratorResult:
        """创建生成结果"""
        return DocGeneratorResult(
            doc_type=self.doc_type,
            content=content,
            file_path=context.get_output_path(self.doc_type),
            success=success,
            message=message,
            metadata=metadata or {},
        )
