"""
文档生成器基类
"""

import hashlib
import json
import time
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
from pywiki.monitor.logger import logger


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

    @property
    def dependencies(self) -> list["DocType"]:
        """获取该文档类型的依赖（需要先生成的文档）"""
        DOC_DEPENDENCIES: dict["DocType", list["DocType"]] = {
            DocType.TECHNICAL_DESIGN_SPEC: [
                DocType.OVERVIEW,
                DocType.ARCHITECTURE,
                DocType.API,
                DocType.DEPENDENCIES,
                DocType.TECH_STACK,
            ],
            DocType.CODE_QUALITY: [
                DocType.MODULE,
                DocType.ARCHITECTURE,
            ],
            DocType.TEST_COVERAGE: [
                DocType.MODULE,
            ],
            DocType.IMPLICIT_KNOWLEDGE: [
                DocType.MODULE,
                DocType.ARCHITECTURE,
            ],
        }
        return DOC_DEPENDENCIES.get(self, [])


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
    package_analysis: Optional[dict[str, Any]] = None
    _package_analyzer: Any = field(default=None, repr=False)

    def detect_project_language(self) -> str:
        """检测项目主要编程语言"""
        if not self.project_path:
            return "python"
        
        EXCLUDE_DIRS = {
            "__pycache__",
            "node_modules",
            "target",
            "build",
            ".gradle",
            ".mvn",
            ".python-wiki",
            ".venv",
            "venv",
            "env",
            ".env",
            "dist",
            "out",
            ".idea",
            ".vscode",
            ".git",
            ".tox",
            ".pytest_cache",
            ".mypy_cache",
            "site-packages",
        }
        
        def should_exclude(path: Path) -> bool:
            return any(excluded in path.parts for excluded in EXCLUDE_DIRS)
        
        language_scores = {
            "python": 0,
            "java": 0,
            "typescript": 0,
        }
        
        python_files = [f for f in self.project_path.rglob("*.py") if not should_exclude(f)]
        language_scores["python"] = len(python_files)
        
        java_files = [f for f in self.project_path.rglob("*.java") if not should_exclude(f)]
        language_scores["java"] = len(java_files)
        
        ts_files = [f for f in self.project_path.rglob("*.ts") if not should_exclude(f)]
        ts_files += [f for f in self.project_path.rglob("*.tsx") if not should_exclude(f)]
        language_scores["typescript"] = len(ts_files)
        
        if (self.project_path / "pom.xml").exists():
            language_scores["java"] += 1000
        if (self.project_path / "build.gradle").exists() or (self.project_path / "build.gradle.kts").exists():
            language_scores["java"] += 1000
        
        if (self.project_path / "package.json").exists():
            language_scores["typescript"] += 500
        
        if (self.project_path / "pyproject.toml").exists() or (self.project_path / "setup.py").exists():
            language_scores["python"] += 500
        
        if (self.project_path / "src" / "main" / "java").exists():
            language_scores["java"] += 200
        if (self.project_path / "src" / "main" / "kotlin").exists():
            language_scores["java"] += 100
        
        if (self.project_path / "src" / "main" / "ts").exists():
            language_scores["typescript"] += 100
        
        if max(language_scores.values()) == 0:
            if (self.project_path / "pom.xml").exists() or (self.project_path / "build.gradle").exists():
                return "java"
            if (self.project_path / "package.json").exists():
                return "typescript"
            return "python"
        
        return max(language_scores.items(), key=lambda x: x[1])[0]

    def get_package_analysis(self) -> dict[str, Any]:
        """获取包分析结果（按需计算并缓存）"""
        if self.package_analysis is not None:
            return self.package_analysis
        
        if self._package_analyzer is None:
            from pywiki.analysis.package_analyzer import PackageAnalyzer
            self._package_analyzer = PackageAnalyzer()
        
        self.package_analysis = self._package_analyzer.get_full_analysis(self.project_path)
        return self.package_analysis

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
                "async_support": "异步编程支持",
                "dataclass_support": "数据类支持",
                "context_manager_support": "上下文管理器支持",
                "iterator_support": "迭代器支持",
                "decorator_pattern": "装饰器模式",
                "property_accessor": "属性访问器",
                "classmethod_support": "类方法支持",
                "staticmethod_support": "静态方法支持",
                "caching_decorator": "缓存装饰器",
                "retry_mechanism": "重试机制",
                "project_documentation": "项目文档",
                "module_documentation": "模块文档",
                "module_dependencies": "模块依赖关系",
                "metrics": "指标",
                "count": "数量",
                "async_functions_methods": "异步函数/方法",
                "statistics": "统计",
                "more_classes": "... 等 {} 个类",
                "attributes": "属性",
                "contains_modules": "包含 {} 个模块",
                "defined_classes": "定义了 {} 个类",
                "provided_functions": "提供了 {} 个函数",
                "web_frameworks": "Web框架",
                "databases_tech": "数据库",
                "http_clients": "HTTP客户端",
                "testing": "测试",
                "data_processing": "数据处理",
                "machine_learning": "机器学习",
                "cli_tools": "CLI",
                "validation": "验证",
                "logging_tech": "日志",
                "config_tech": "配置",
                "gui_frameworks": "GUI",
                "n_classes": "{} 个类",
                "n_functions": "{} 个函数",
                "n_methods": "{} 方法",
                "n_properties": "{} 属性",
                "more_n_classes": "... 等 {} 个类",
                "more_n_functions": "... 等 {} 个函数",
                "external_deps": "外部依赖",
                "doc_generated_at": "文档生成时间",
                "class_label": "类",
                "function_label": "函数",
                "monolithic_arch": "单体架构",
                "event_driven_arch": "事件驱动架构",
                "cqrs_arch": "CQRS 架构",
                "hexagonal_arch": "六边形架构",
                "microservice_arch": "微服务架构",
                "layered_arch": "分层架构",
                "system_arch": "系统架构",
                "package_deps": "包依赖关系",
                "external_client": "外部客户端",
                "api_entry": "API 入口",
                "business_processing": "业务处理",
                "data_storage": "数据存储",
                "overview_success": "项目概述文档生成成功",
                "module_doc_success": "模块文档生成成功",
                "generation_failed": "生成失败",
                "request": "请求",
                "data_operation": "数据操作",
                "api_doc_success": "API 文档生成成功",
                "database_doc_success": "数据库文档生成成功",
                "config_doc_success": "配置文档生成成功",
                "dependencies_doc_success": "依赖文档生成成功",
                "development_doc_success": "开发指南文档生成成功",
                "techstack_doc_success": "技术栈文档生成成功",
                "architecture_doc_success": "架构文档生成成功",
                "code_quality_doc_success": "代码质量分析文档生成成功",
                "test_coverage_doc_success": "测试覆盖分析文档生成成功",
                "implicit_knowledge_doc_success": "隐性知识文档生成成功",
                "tsd_doc_success": "TSD 文档生成成功",
                "tds_doc_success": "Technical Design Specification 文档生成成功",
                "quest_doc_success": "Quest 设计文档生成成功",
                "adr_not_detected": "未检测到架构决策",
                "adr_generated": "成功生成 {} 个 ADR",
                "other": "其他",
                "utilities": "工具",
                "async_tech": "异步",
                "microservices": "微服务",
                "message_queue": "消息队列",
                "caching": "缓存",
                "monitoring": "监控",
                "build_tools": "构建工具",
                "frontend_frameworks": "前端框架",
                "ui_libraries": "UI组件库",
                "state_management": "状态管理",
                "api_docs": "API文档",
                "presentation_layer": "表现层",
                "business_layer": "业务层",
                "data_layer": "数据层",
                "infrastructure_layer": "基础设施层",
                "proxy_layer": "代理层",
                "dto_layer": "DTO层",
                "presentation_desc": "处理外部请求，负责数据展示和用户交互",
                "business_desc": "实现核心业务逻辑和业务规则",
                "data_desc": "负责数据持久化和数据访问",
                "infrastructure_desc": "提供技术支持和基础设施服务",
                "proxy_desc": "负责与外部系统交互和集成",
                "dto_desc": "数据传输对象，用于层间数据传递",
                "java_presentation_desc": "处理 HTTP 请求，负责 API 端点和 Web 界面",
                "ts_presentation_desc": "处理 HTTP 请求和 GraphQL 解析器",
                "ts_dto_desc": "数据传输对象和类型定义",
                "orm_frameworks": "ORM框架",
                "json_processing": "JSON处理",
                "type_checking": "类型检查",
                "code_quality": "代码质量",
                "backend_frameworks": "后端框架",
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
                "async_support": "Async Programming Support",
                "dataclass_support": "Dataclass Support",
                "context_manager_support": "Context Manager Support",
                "iterator_support": "Iterator Support",
                "decorator_pattern": "Decorator Pattern",
                "property_accessor": "Property Accessor",
                "classmethod_support": "Classmethod Support",
                "staticmethod_support": "Staticmethod Support",
                "caching_decorator": "Caching Decorator",
                "retry_mechanism": "Retry Mechanism",
                "project_documentation": "Project Documentation",
                "module_documentation": "Module Documentation",
                "module_dependencies": "Module Dependencies",
                "metrics": "Metrics",
                "count": "Count",
                "async_functions_methods": "Async Functions/Methods",
                "statistics": "Statistics",
                "more_classes": "... and {} more classes",
                "attributes": "Attributes",
                "contains_modules": "Contains {} modules",
                "defined_classes": "Defines {} classes",
                "provided_functions": "Provides {} functions",
                "web_frameworks": "Web Frameworks",
                "databases_tech": "Databases",
                "http_clients": "HTTP Clients",
                "testing": "Testing",
                "data_processing": "Data Processing",
                "machine_learning": "Machine Learning",
                "cli_tools": "CLI",
                "validation": "Validation",
                "logging_tech": "Logging",
                "config_tech": "Configuration",
                "gui_frameworks": "GUI",
                "n_classes": "{} classes",
                "n_functions": "{} functions",
                "n_methods": "{} methods",
                "n_properties": "{} properties",
                "more_n_classes": "... and {} more classes",
                "more_n_functions": "... and {} more functions",
                "external_deps": "External Dependencies",
                "doc_generated_at": "Document generated at",
                "class_label": "Class",
                "function_label": "Function",
                "monolithic_arch": "Monolithic Architecture",
                "event_driven_arch": "Event-Driven Architecture",
                "cqrs_arch": "CQRS Architecture",
                "hexagonal_arch": "Hexagonal Architecture",
                "microservice_arch": "Microservice Architecture",
                "layered_arch": "Layered Architecture",
                "system_arch": "System Architecture",
                "package_deps": "Package Dependencies",
                "external_client": "External Client",
                "api_entry": "API Entry",
                "business_processing": "Business Processing",
                "data_storage": "Data Storage",
                "overview_success": "Overview document generated successfully",
                "module_doc_success": "Module documentation generated successfully",
                "generation_failed": "Generation failed",
                "request": "Request",
                "data_operation": "Data Operation",
                "api_doc_success": "API documentation generated successfully",
                "database_doc_success": "Database documentation generated successfully",
                "config_doc_success": "Configuration documentation generated successfully",
                "dependencies_doc_success": "Dependencies documentation generated successfully",
                "development_doc_success": "Development guide generated successfully",
                "techstack_doc_success": "Tech stack documentation generated successfully",
                "architecture_doc_success": "Architecture documentation generated successfully",
                "code_quality_doc_success": "Code quality analysis generated successfully",
                "test_coverage_doc_success": "Test coverage analysis generated successfully",
                "implicit_knowledge_doc_success": "Implicit knowledge documentation generated successfully",
                "tsd_doc_success": "TSD documentation generated successfully",
                "tds_doc_success": "Technical Design Specification generated successfully",
                "quest_doc_success": "Quest design document generated successfully",
                "adr_not_detected": "No architecture decisions detected",
                "adr_generated": "Successfully generated {} ADRs",
                "other": "Other",
                "utilities": "Utilities",
                "async_tech": "Async",
                "microservices": "Microservices",
                "message_queue": "Message Queue",
                "caching": "Caching",
                "monitoring": "Monitoring",
                "build_tools": "Build Tools",
                "frontend_frameworks": "Frontend Frameworks",
                "ui_libraries": "UI Libraries",
                "state_management": "State Management",
                "api_docs": "API Docs",
                "presentation_layer": "Presentation Layer",
                "business_layer": "Business Layer",
                "data_layer": "Data Layer",
                "infrastructure_layer": "Infrastructure Layer",
                "proxy_layer": "Proxy Layer",
                "dto_layer": "DTO Layer",
                "presentation_desc": "Handles external requests, responsible for data display and user interaction",
                "business_desc": "Implements core business logic and business rules",
                "data_desc": "Responsible for data persistence and data access",
                "infrastructure_desc": "Provides technical support and infrastructure services",
                "proxy_desc": "Responsible for interacting and integrating with external systems",
                "dto_desc": "Data Transfer Objects for inter-layer data transfer",
                "java_presentation_desc": "Handles HTTP requests, responsible for API endpoints and web interface",
                "ts_presentation_desc": "Handles HTTP requests and GraphQL resolvers",
                "ts_dto_desc": "Data Transfer Objects and type definitions",
                "orm_frameworks": "ORM Frameworks",
                "json_processing": "JSON Processing",
                "type_checking": "Type Checking",
                "code_quality": "Code Quality",
                "backend_frameworks": "Backend Frameworks",
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

    def _get_language_instruction(self) -> str:
        """获取语言指令"""
        if self.language == Language.ZH:
            return "请务必使用中文回答。"
        else:
            return "Please respond in English."

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        if self.language == Language.ZH:
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

    async def generate_with_llm(
        self,
        prompt: str,
        llm_client: Any,
        system_prompt: Optional[str] = None,
    ) -> str:
        """使用 LLM 增强文档内容"""
        if not llm_client:
            logger.debug("generate_with_llm: LLM 客户端未配置，跳过")
            return ""
        
        if system_prompt is None:
            system_prompt = self._get_system_prompt()
        
        start_time = time.time()
        prompt_length = len(prompt) if prompt else 0
        logger.info(f"LLM 增强开始: prompt_length={prompt_length}, has_system_prompt={bool(system_prompt)}")
        
        try:
            if system_prompt:
                result = await llm_client.agenerate(prompt, system_prompt=system_prompt)
            else:
                result = await llm_client.agenerate(prompt)
            
            duration_ms = (time.time() - start_time) * 1000
            result_length = len(result) if result else 0
            logger.info(f"LLM 增强完成: 耗时={duration_ms:.0f}ms, result_length={result_length}")
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"LLM 增强失败: 耗时={duration_ms:.0f}ms, 错误={str(e)}")
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
