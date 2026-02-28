"""
文档生成器基类
"""

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, Template

from pywiki.config.models import Language
from pywiki.parsers.types import ModuleInfo, ParseResult
from pywiki.wiki.structure import DocCategory


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
    DEPLOYMENT = "deployment"
    TSD = "tsd"
    IMPLICIT_KNOWLEDGE = "implicit-knowledge"
    TEST_COVERAGE = "test-coverage"
    CODE_QUALITY = "code-quality"
    TECHNICAL_DESIGN_SPEC = "technical-design-spec"


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
        DOC_TYPE_TO_CATEGORY = {
            DocType.OVERVIEW: (DocCategory.OVERVIEW, "README.md"),
            DocType.TECH_STACK: (DocCategory.OVERVIEW, "tech-stack.md"),
            DocType.API: (DocCategory.API, "index.md"),
            DocType.ARCHITECTURE: (DocCategory.ARCHITECTURE, "system-architecture.md"),
            DocType.MODULE: (DocCategory.MODULES, "index.md"),
            DocType.DATABASE: (DocCategory.DATABASE, "schema.md"),
            DocType.CONFIGURATION: (DocCategory.CONFIGURATION, "environment.md"),
            DocType.DEVELOPMENT: (DocCategory.DEVELOPMENT, "getting-started.md"),
            DocType.DEPENDENCIES: (DocCategory.DEPENDENCIES, "external.md"),
            DocType.DEPLOYMENT: (DocCategory.CONFIGURATION, "deployment.md"),
            DocType.TSD: (DocCategory.DESIGN_DECISIONS, "design-decisions.md"),
            DocType.IMPLICIT_KNOWLEDGE: (DocCategory.OVERVIEW, "implicit-knowledge.md"),
            DocType.TEST_COVERAGE: (DocCategory.DEVELOPMENT, "test-coverage.md"),
            DocType.CODE_QUALITY: (DocCategory.DEVELOPMENT, "code-quality.md"),
            DocType.TECHNICAL_DESIGN_SPEC: (DocCategory.DESIGN_DECISIONS, "technical-design-spec.md"),
        }
        
        mapping = DOC_TYPE_TO_CATEGORY.get(doc_type)
        if mapping:
            category, filename = mapping
            return self.output_dir / category.value / filename
        
        return self.output_dir / f"{doc_type.value}.md"
    
    def get_cache_path(self) -> Path:
        """获取缓存目录路径"""
        return self.output_dir / ".cache"
    
    def compute_content_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def load_cached_hash(self, doc_type: DocType) -> Optional[str]:
        """加载缓存的哈希值"""
        cache_path = self.get_cache_path() / f"{doc_type.value}.hash"
        if cache_path.exists():
            return cache_path.read_text().strip()
        return None
    
    def save_cached_hash(self, doc_type: DocType, content_hash: str) -> None:
        """保存内容哈希到缓存"""
        cache_path = self.get_cache_path() / f"{doc_type.value}.hash"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(content_hash)
    
    def needs_regeneration(self, doc_type: DocType, new_content: str) -> bool:
        """检查文档是否需要重新生成"""
        output_path = self.get_output_path(doc_type)
        
        if not output_path.exists():
            return True
        
        cached_hash = self.load_cached_hash(doc_type)
        if cached_hash is None:
            return True
        
        new_hash = self.compute_content_hash(new_content)
        return cached_hash != new_hash
    
    def get_changed_modules(self, old_parse_result: Optional[ParseResult], new_parse_result: ParseResult) -> set[str]:
        """获取变更的模块"""
        if old_parse_result is None:
            return {m.name for m in new_parse_result.modules}
        
        old_modules = {m.name: m for m in old_parse_result.modules}
        new_modules = {m.name: m for m in new_parse_result.modules}
        
        changed = set()
        
        for name in new_modules:
            if name not in old_modules:
                changed.add(name)
            else:
                old_module = old_modules[name]
                new_module = new_modules[name]
                
                if self._module_changed(old_module, new_module):
                    changed.add(name)
        
        for name in old_modules:
            if name not in new_modules:
                changed.add(name)
        
        return changed
    
    def _module_changed(self, old_module: ModuleInfo, new_module: ModuleInfo) -> bool:
        """检查模块是否变更"""
        if len(old_module.classes) != len(new_module.classes):
            return True
        if len(old_module.functions) != len(new_module.functions):
            return True
        
        old_class_names = {c.name for c in old_module.classes}
        new_class_names = {c.name for c in new_module.classes}
        if old_class_names != new_class_names:
            return True
        
        old_func_names = {f.name for f in old_module.functions}
        new_func_names = {f.name for f in new_module.functions}
        if old_func_names != new_func_names:
            return True
        
        return False


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
                "technical_design_spec": "技术设计规范",
                "features": "功能特性",
                "category": "类别",
                "technology": "技术",
                "module": "模块",
                "frameworks": "框架",
                "databases": "数据库",
                "core_libraries": "核心库",
                "tools": "工具",
                "language_distribution": "语言分布",
                "language": "语言",
                "files": "文件数",
                "percentage": "占比",
                "name": "名称",
                "document_info": "文档信息",
                "project_name": "项目名称",
                "document_type": "文档类型",
                "generation_tool": "生成工具",
                "executive_summary": "执行摘要",
                "project_overview": "项目概述",
                "system_architecture": "系统架构设计",
                "tech_stack_selection": "技术栈选型",
                "api_design": "API设计规范",
                "data_model_design": "数据模型设计",
                "dependency_management": "依赖管理",
                "config_management": "配置管理",
                "development_guide": "开发指南",
                "code_analysis": "代码分析",
                "security_design": "安全设计",
                "performance_design": "性能设计",
                "deployment_architecture": "部署架构",
                "appendix": "附录",
                "key_decisions": "关键技术决策",
                "risk_assessment": "风险评估",
                "improvement_roadmap": "改进路线图",
                "compliance_notes": "合规性说明",
                "project_intro": "项目简介",
                "module_list": "模块列表",
                "code_statistics": "代码统计",
                "module_count": "模块数",
                "class_count": "类数",
                "function_count": "函数数",
                "method_count": "方法数",
                "architecture_desc": "架构描述",
                "architecture_layers": "架构分层",
                "architecture_diagrams": "架构图表",
                "quality_metrics": "质量指标",
                "recommendations": "建议",
                "primary_language": "主要编程语言",
                "tech_categories": "技术分类",
                "api_overview": "API概述",
                "api_endpoints": "API端点列表",
                "api_modules": "API模块",
                "handler": "处理器",
                "data_model_overview": "数据模型概述",
                "tables_entities": "数据表/实体列表",
                "er_diagram": "ER图",
                "dependency_overview": "依赖概述",
                "config_overview": "配置概述",
                "environment_variables": "环境变量",
                "development_overview": "开发概述",
                "prerequisites": "前置条件",
                "design_decisions_overview": "设计决策概述",
                "design_decisions_list": "设计决策列表",
                "status": "状态",
                "date": "日期",
                "context": "背景",
                "decision": "决策",
                "consequences": "影响",
                "severity": "严重程度",
                "location": "位置",
                "suggestion": "建议",
                "design_patterns": "设计模式",
                "code_quality": "代码质量",
                "test_coverage": "测试覆盖",
                "implicit_knowledge": "隐性知识",
                "security_considerations": "安全考虑",
                "security_recommendations": "安全建议",
                "async_operations": "异步操作",
                "caching_strategy": "缓存策略",
                "performance_recommendations": "性能优化建议",
                "containerization": "容器化",
                "deployment_recommendations": "部署建议",
                "glossary": "术语表",
                "term": "术语",
                "definition": "定义",
                "references": "参考资料",
                "changelog": "变更日志",
                "generation_notes": "文档生成说明",
                "document_end": "文档结束",
                "deployment_guide": "部署指南",
                "deployment_architecture_title": "部署架构",
                "environment_config": "环境配置",
                "deployment_process": "部署流程",
                "container_deployment": "容器化部署",
                "cicd_config": "CI/CD 配置",
                "monitoring_logging": "监控与日志",
                "backup_recovery": "备份与恢复",
                "troubleshooting": "故障排查",
                "security_config": "安全配置",
                "scaling": "扩缩容",
                "rollback_strategy": "回滚策略",
                "best_practices": "最佳实践",
                "variable_name": "变量名",
                "required": "必需",
                "yes": "是",
                "no": "否",
                "service_list": "服务列表",
                "service_name": "服务名",
                "image": "镜像",
                "ports": "端口",
                "common_commands": "常用命令",
                "resource_list": "资源清单",
                "resource_type": "资源类型",
                "file": "文件",
                "pipeline": "流水线",
                "stages": "阶段",
                "triggers": "触发条件",
                "secret_config": "密钥配置",
                "secret_name": "密钥名",
                "monitoring_metrics": "监控指标",
                "log_config": "日志配置",
                "log_format": "日志格式",
                "log_output": "输出位置",
                "log_level": "日志级别",
                "alert_config": "告警配置",
                "backup_strategy": "备份策略",
                "backup_schedule": "备份周期",
                "backup_commands": "备份命令",
                "restore_commands": "恢复命令",
                "symptom": "症状",
                "cause": "原因",
                "solution": "解决方案",
                "secrets_management": "密钥管理",
                "network_policies": "网络策略",
                "ssl_tls_config": "SSL/TLS 配置",
                "horizontal_scaling": "水平扩展",
                "vertical_scaling": "垂直扩展",
                "auto_scaling": "自动扩缩容",
                "dockerfile_location": "Dockerfile 位置",
                "build_image": "构建镜像",
                "run_container": "运行容器",
                "exposed_ports": "暴露端口",
                "config_file": "配置文件",
                "config_dir": "配置目录",
                "platform": "平台",
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
                "technical_design_spec": "Technical Design Specification",
                "features": "Features",
                "category": "Category",
                "technology": "Technology",
                "module": "Module",
                "frameworks": "Frameworks",
                "databases": "Databases",
                "core_libraries": "Core Libraries",
                "tools": "Tools",
                "language_distribution": "Language Distribution",
                "language": "Language",
                "files": "Files",
                "percentage": "Percentage",
                "name": "Name",
                "document_info": "Document Information",
                "project_name": "Project Name",
                "document_type": "Document Type",
                "generation_tool": "Generation Tool",
                "executive_summary": "Executive Summary",
                "project_overview": "Project Overview",
                "system_architecture": "System Architecture",
                "tech_stack_selection": "Tech Stack Selection",
                "api_design": "API Design",
                "data_model_design": "Data Model Design",
                "dependency_management": "Dependency Management",
                "config_management": "Configuration Management",
                "development_guide": "Development Guide",
                "code_analysis": "Code Analysis",
                "security_design": "Security Design",
                "performance_design": "Performance Design",
                "deployment_architecture": "Deployment Architecture",
                "appendix": "Appendix",
                "key_decisions": "Key Technical Decisions",
                "risk_assessment": "Risk Assessment",
                "improvement_roadmap": "Improvement Roadmap",
                "compliance_notes": "Compliance Notes",
                "project_intro": "Project Introduction",
                "module_list": "Module List",
                "code_statistics": "Code Statistics",
                "module_count": "Modules",
                "class_count": "Classes",
                "function_count": "Functions",
                "method_count": "Methods",
                "architecture_desc": "Architecture Description",
                "architecture_layers": "Architecture Layers",
                "architecture_diagrams": "Architecture Diagrams",
                "quality_metrics": "Quality Metrics",
                "recommendations": "Recommendations",
                "primary_language": "Primary Programming Language",
                "tech_categories": "Technology Categories",
                "api_overview": "API Overview",
                "api_endpoints": "API Endpoints",
                "api_modules": "API Modules",
                "handler": "Handler",
                "data_model_overview": "Data Model Overview",
                "tables_entities": "Tables/Entities",
                "er_diagram": "ER Diagram",
                "dependency_overview": "Dependency Overview",
                "config_overview": "Configuration Overview",
                "environment_variables": "Environment Variables",
                "development_overview": "Development Overview",
                "prerequisites": "Prerequisites",
                "design_decisions_overview": "Design Decisions Overview",
                "design_decisions_list": "Design Decisions List",
                "status": "Status",
                "date": "Date",
                "context": "Context",
                "decision": "Decision",
                "consequences": "Consequences",
                "severity": "Severity",
                "location": "Location",
                "suggestion": "Suggestion",
                "design_patterns": "Design Patterns",
                "code_quality": "Code Quality",
                "test_coverage": "Test Coverage",
                "implicit_knowledge": "Implicit Knowledge",
                "security_considerations": "Security Considerations",
                "security_recommendations": "Security Recommendations",
                "async_operations": "Asynchronous Operations",
                "caching_strategy": "Caching Strategy",
                "performance_recommendations": "Performance Recommendations",
                "containerization": "Containerization",
                "deployment_recommendations": "Deployment Recommendations",
                "glossary": "Glossary",
                "term": "Term",
                "definition": "Definition",
                "references": "References",
                "changelog": "Changelog",
                "generation_notes": "Document Generation Notes",
                "document_end": "End of Document",
                "deployment_guide": "Deployment Guide",
                "deployment_architecture_title": "Deployment Architecture",
                "environment_config": "Environment Configuration",
                "deployment_process": "Deployment Process",
                "container_deployment": "Containerization",
                "cicd_config": "CI/CD Configuration",
                "monitoring_logging": "Monitoring & Logging",
                "backup_recovery": "Backup & Recovery",
                "troubleshooting": "Troubleshooting",
                "security_config": "Security Configuration",
                "scaling": "Scaling",
                "rollback_strategy": "Rollback Strategy",
                "best_practices": "Best Practices",
                "variable_name": "Variable Name",
                "required": "Required",
                "yes": "Yes",
                "no": "No",
                "service_list": "Service List",
                "service_name": "Service Name",
                "image": "Image",
                "ports": "Ports",
                "common_commands": "Common Commands",
                "resource_list": "Resource List",
                "resource_type": "Resource Type",
                "file": "File",
                "pipeline": "Pipeline",
                "stages": "Stages",
                "triggers": "Triggers",
                "secret_config": "Secret Configuration",
                "secret_name": "Secret Name",
                "monitoring_metrics": "Monitoring Metrics",
                "log_config": "Log Configuration",
                "log_format": "Log Format",
                "log_output": "Output Location",
                "log_level": "Log Level",
                "alert_config": "Alert Configuration",
                "backup_strategy": "Backup Strategy",
                "backup_schedule": "Backup Schedule",
                "backup_commands": "Backup Commands",
                "restore_commands": "Restore Commands",
                "symptom": "Symptom",
                "cause": "Cause",
                "solution": "Solution",
                "secrets_management": "Secrets Management",
                "network_policies": "Network Policies",
                "ssl_tls_config": "SSL/TLS Configuration",
                "horizontal_scaling": "Horizontal Scaling",
                "vertical_scaling": "Vertical Scaling",
                "auto_scaling": "Auto Scaling",
                "dockerfile_location": "Dockerfile Location",
                "build_image": "Build Image",
                "run_container": "Run Container",
                "exposed_ports": "Exposed Ports",
                "config_file": "Config File",
                "config_dir": "Config Directory",
                "platform": "Platform",
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
