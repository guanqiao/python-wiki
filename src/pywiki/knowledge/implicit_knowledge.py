"""
隐性知识提取器
从代码中提取隐性知识，包括设计决策、架构考量、技术债务等
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pywiki.parsers.types import ModuleInfo, ClassInfo, FunctionInfo


class KnowledgeType(str, Enum):
    DESIGN_DECISION = "design_decision"
    ARCHITECTURE_PATTERN = "architecture_pattern"
    TECH_DEBT = "tech_debt"
    DEPENDENCY_REASON = "dependency_reason"
    CODING_CONVENTION = "coding_convention"
    BUSINESS_LOGIC = "business_logic"
    PERFORMANCE_CONSIDERATION = "performance_consideration"
    SECURITY_CONSIDERATION = "security_consideration"


@dataclass
class ImplicitKnowledge:
    knowledge_type: KnowledgeType
    title: str
    description: str
    evidence: list[str] = field(default_factory=list)
    location: Optional[str] = None
    confidence: float = 0.0
    suggestions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ImplicitKnowledgeExtractor:
    """隐性知识提取器"""

    def __init__(self):
        self._design_patterns = self._load_design_patterns()
        self._architecture_patterns = self._load_architecture_patterns()
        self._convention_rules = self._load_convention_rules()

    def extract_from_module(self, module: ModuleInfo) -> list[ImplicitKnowledge]:
        """从模块中提取隐性知识"""
        knowledge_list = []

        knowledge_list.extend(self._extract_design_decisions(module))
        knowledge_list.extend(self._extract_architecture_patterns(module))
        knowledge_list.extend(self._extract_coding_conventions(module))
        knowledge_list.extend(self._extract_business_logic(module))

        return knowledge_list

    def extract_from_class(self, cls: ClassInfo) -> list[ImplicitKnowledge]:
        """从类中提取隐性知识"""
        knowledge_list = []

        knowledge_list.extend(self._extract_class_design_decisions(cls))
        knowledge_list.extend(self._extract_class_patterns(cls))
        knowledge_list.extend(self._extract_class_responsibilities(cls))

        return knowledge_list

    def extract_from_function(self, func: FunctionInfo) -> list[ImplicitKnowledge]:
        """从函数中提取隐性知识"""
        knowledge_list = []

        knowledge_list.extend(self._extract_function_design_decisions(func))
        knowledge_list.extend(self._extract_performance_considerations(func))
        knowledge_list.extend(self._extract_security_considerations(func))

        return knowledge_list

    def _extract_design_decisions(self, module: ModuleInfo) -> list[ImplicitKnowledge]:
        """提取设计决策"""
        decisions = []

        if module.imports:
            framework_decisions = self._analyze_framework_choices(module.imports)
            decisions.extend(framework_decisions)

        if module.classes:
            inheritance_decisions = self._analyze_inheritance_decisions(module.classes)
            decisions.extend(inheritance_decisions)

        return decisions

    def _analyze_framework_choices(self, imports: list) -> list[ImplicitKnowledge]:
        """分析框架选择决策"""
        decisions = []
        framework_hints = {
            "flask": "选择了轻量级框架 Flask，适合中小型项目和微服务架构",
            "django": "选择了全功能框架 Django，适合快速开发和大型项目",
            "fastapi": "选择了高性能异步框架 FastAPI，适合 API 服务和高并发场景",
            "sqlalchemy": "选择了 SQLAlchemy ORM，提供了灵活的数据库抽象层",
            "pydantic": "使用 Pydantic 进行数据验证，确保类型安全和数据完整性",
            "pytest": "使用 pytest 作为测试框架，支持丰富的插件生态",
            "celery": "使用 Celery 处理异步任务，支持分布式任务队列",
            "redis": "使用 Redis 作为缓存/消息队列，提升系统性能",
        }

        for imp in imports:
            module_name = imp.module.split(".")[0].lower()
            if module_name in framework_hints:
                decisions.append(ImplicitKnowledge(
                    knowledge_type=KnowledgeType.DESIGN_DECISION,
                    title=f"框架选择: {module_name}",
                    description=framework_hints[module_name],
                    evidence=[f"导入: {imp.module}"],
                    confidence=0.9,
                ))

        return decisions

    def _analyze_inheritance_decisions(self, classes: list[ClassInfo]) -> list[ImplicitKnowledge]:
        """分析继承决策"""
        decisions = []

        for cls in classes:
            if cls.bases:
                if any("ABC" in base or "Abstract" in base for base in cls.bases):
                    decisions.append(ImplicitKnowledge(
                        knowledge_type=KnowledgeType.DESIGN_DECISION,
                        title=f"抽象类设计: {cls.name}",
                        description=f"{cls.name} 被设计为抽象类，定义了接口规范，支持多态和扩展",
                        evidence=[f"继承自: {', '.join(cls.bases)}"],
                        location=cls.full_name,
                        confidence=0.85,
                    ))

                if any("Exception" in base for base in cls.bases):
                    decisions.append(ImplicitKnowledge(
                        knowledge_type=KnowledgeType.DESIGN_DECISION,
                        title=f"自定义异常: {cls.name}",
                        description=f"{cls.name} 是自定义异常类，用于业务错误处理",
                        evidence=[f"继承自: {', '.join(cls.bases)}"],
                        location=cls.full_name,
                        confidence=0.9,
                    ))

        return decisions

    def _extract_architecture_patterns(self, module: ModuleInfo) -> list[ImplicitKnowledge]:
        """提取架构模式"""
        patterns = []
        module_name_lower = module.name.lower()

        pattern_indicators = {
            "service": ("服务层模式", "实现了业务逻辑分离，服务层负责业务规则和事务管理"),
            "repository": ("仓储模式", "实现了数据访问抽象，分离业务逻辑和数据持久化"),
            "controller": ("控制器模式", "实现了请求处理和响应逻辑，遵循 MVC 架构"),
            "model": ("模型模式", "定义了数据结构和业务实体"),
            "handler": ("处理器模式", "实现了请求/事件处理逻辑"),
            "middleware": ("中间件模式", "实现了请求预处理和后处理逻辑"),
            "factory": ("工厂模式", "实现了对象创建的封装和解耦"),
            "builder": ("构建者模式", "实现了复杂对象的分步构建"),
            "singleton": ("单例模式", "确保类只有一个实例"),
            "observer": ("观察者模式", "实现了事件订阅和通知机制"),
        }

        for keyword, (pattern_name, description) in pattern_indicators.items():
            if keyword in module_name_lower:
                patterns.append(ImplicitKnowledge(
                    knowledge_type=KnowledgeType.ARCHITECTURE_PATTERN,
                    title=f"架构模式: {pattern_name}",
                    description=description,
                    evidence=[f"模块名称包含 '{keyword}'"],
                    location=module.name,
                    confidence=0.7,
                ))

        return patterns

    def _extract_coding_conventions(self, module: ModuleInfo) -> list[ImplicitKnowledge]:
        """提取编码规范"""
        conventions = []

        naming_styles = self._analyze_naming_styles(module)
        if naming_styles:
            conventions.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.CODING_CONVENTION,
                title="命名规范",
                description=f"项目采用 {naming_styles} 命名风格",
                evidence=self._collect_naming_evidence(module),
                confidence=0.8,
            ))

        docstring_style = self._analyze_docstring_style(module)
        if docstring_style:
            conventions.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.CODING_CONVENTION,
                title="文档字符串风格",
                description=f"使用 {docstring_style} 风格的文档字符串",
                evidence=self._collect_docstring_evidence(module),
                confidence=0.75,
            ))

        return conventions

    def _analyze_naming_styles(self, module: ModuleInfo) -> Optional[str]:
        """分析命名风格"""
        snake_case_count = 0
        camel_case_count = 0

        for func in module.functions:
            if "_" in func.name and func.name.islower():
                snake_case_count += 1
            elif func.name[0].islower() and not "_" in func.name:
                camel_case_count += 1

        for cls in module.classes:
            if cls.name[0].isupper():
                camel_case_count += 1

        if snake_case_count > camel_case_count:
            return "snake_case (Python PEP 8)"
        elif camel_case_count > 0:
            return "mixed (camelCase/PascalCase)"

        return None

    def _analyze_docstring_style(self, module: ModuleInfo) -> Optional[str]:
        """分析文档字符串风格"""
        google_style = 0
        numpy_style = 0
        sphinx_style = 0

        for func in module.functions:
            if func.docstring:
                if "Args:" in func.docstring or "Returns:" in func.docstring:
                    google_style += 1
                if "Parameters" in func.docstring and "----------" in func.docstring:
                    numpy_style += 1
                if ":param " in func.docstring or ":return:" in func.docstring:
                    sphinx_style += 1

        if google_style >= numpy_style and google_style >= sphinx_style:
            return "Google Style" if google_style > 0 else None
        elif numpy_style >= sphinx_style:
            return "NumPy Style"
        else:
            return "Sphinx Style" if sphinx_style > 0 else None

    def _collect_naming_evidence(self, module: ModuleInfo) -> list[str]:
        """收集命名证据"""
        evidence = []
        for func in module.functions[:5]:
            evidence.append(f"函数: {func.name}")
        for cls in module.classes[:5]:
            evidence.append(f"类: {cls.name}")
        return evidence

    def _collect_docstring_evidence(self, module: ModuleInfo) -> list[str]:
        """收集文档字符串证据"""
        evidence = []
        for func in module.functions:
            if func.docstring:
                evidence.append(f"{func.name}: {func.docstring[:50]}...")
                if len(evidence) >= 3:
                    break
        return evidence

    def _extract_business_logic(self, module: ModuleInfo) -> list[ImplicitKnowledge]:
        """提取业务逻辑"""
        business_knowledge = []

        business_keywords = {
            "user": "用户管理",
            "order": "订单处理",
            "payment": "支付功能",
            "product": "产品管理",
            "cart": "购物车",
            "auth": "认证授权",
            "login": "登录功能",
            "register": "注册功能",
            "email": "邮件服务",
            "notification": "通知服务",
            "report": "报表功能",
            "analytics": "数据分析",
            "search": "搜索功能",
            "upload": "上传功能",
            "download": "下载功能",
        }

        module_name_lower = module.name.lower()
        for keyword, business_name in business_keywords.items():
            if keyword in module_name_lower:
                business_knowledge.append(ImplicitKnowledge(
                    knowledge_type=KnowledgeType.BUSINESS_LOGIC,
                    title=f"业务模块: {business_name}",
                    description=f"该模块涉及 {business_name} 相关的业务逻辑",
                    evidence=[f"模块名称包含 '{keyword}'"],
                    location=module.name,
                    confidence=0.8,
                ))

        return business_knowledge

    def _extract_class_design_decisions(self, cls: ClassInfo) -> list[ImplicitKnowledge]:
        """提取类级别的设计决策"""
        decisions = []

        if cls.is_dataclass:
            decisions.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title=f"数据类设计: {cls.name}",
                description=f"{cls.name} 使用 @dataclass 装饰器，简化了数据类的定义，自动生成 __init__、__repr__ 等方法",
                evidence=["使用了 @dataclass 装饰器"],
                location=cls.full_name,
                confidence=0.95,
            ))

        if cls.is_enum:
            decisions.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title=f"枚举类型: {cls.name}",
                description=f"{cls.name} 是枚举类型，用于定义一组相关的常量值",
                evidence=["继承自 Enum"],
                location=cls.full_name,
                confidence=0.95,
            ))

        if cls.is_abstract:
            decisions.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title=f"抽象基类: {cls.name}",
                description=f"{cls.name} 是抽象基类，定义了接口规范，子类必须实现抽象方法",
                evidence=["包含抽象方法"],
                location=cls.full_name,
                confidence=0.9,
            ))

        return decisions

    def _extract_class_patterns(self, cls: ClassInfo) -> list[ImplicitKnowledge]:
        """提取类级别的设计模式"""
        patterns = []

        if self._is_singleton_pattern(cls):
            patterns.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.ARCHITECTURE_PATTERN,
                title=f"单例模式: {cls.name}",
                description=f"{cls.name} 实现了单例模式，确保全局只有一个实例",
                evidence=["包含 _instance 类变量", "私有 __init__ 或 __new__ 方法"],
                location=cls.full_name,
                confidence=0.8,
            ))

        if self._is_factory_pattern(cls):
            patterns.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.ARCHITECTURE_PATTERN,
                title=f"工厂模式: {cls.name}",
                description=f"{cls.name} 实现了工厂模式，封装了对象创建逻辑",
                evidence=["包含 create/build 方法"],
                location=cls.full_name,
                confidence=0.75,
            ))

        if self._is_builder_pattern(cls):
            patterns.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.ARCHITECTURE_PATTERN,
                title=f"构建者模式: {cls.name}",
                description=f"{cls.name} 实现了构建者模式，支持链式调用构建复杂对象",
                evidence=["返回 self 的方法", "build 方法"],
                location=cls.full_name,
                confidence=0.75,
            ))

        return patterns

    def _is_singleton_pattern(self, cls: ClassInfo) -> bool:
        """检查是否是单例模式"""
        has_instance_var = any("_instance" in v.name for v in cls.class_variables)
        has_new_method = any(m.name == "__new__" for m in cls.methods)
        return has_instance_var or has_new_method

    def _is_factory_pattern(self, cls: ClassInfo) -> bool:
        """检查是否是工厂模式"""
        factory_methods = ["create", "build", "make", "factory", "get_instance"]
        return any(
            any(fm in m.name.lower() for fm in factory_methods)
            for m in cls.methods
        )

    def _is_builder_pattern(self, cls: ClassInfo) -> bool:
        """检查是否是构建者模式"""
        has_build_method = any(m.name == "build" for m in cls.methods)
        has_fluent_methods = any(
            m.return_type == cls.name or "self" in str(m.return_type or "")
            for m in cls.methods
        )
        return has_build_method and has_fluent_methods

    def _extract_class_responsibilities(self, cls: ClassInfo) -> list[ImplicitKnowledge]:
        """提取类的职责"""
        responsibilities = []

        method_count = len(cls.methods)
        property_count = len(cls.properties)

        if method_count > 15:
            responsibilities.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title=f"可能的职责过重: {cls.name}",
                description=f"{cls.name} 包含 {method_count} 个方法，可能违反单一职责原则",
                evidence=[f"方法数量: {method_count}"],
                location=cls.full_name,
                confidence=0.6,
                suggestions=["考虑将类拆分为多个更小的类"],
            ))

        if property_count > 10:
            responsibilities.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title=f"属性过多: {cls.name}",
                description=f"{cls.name} 包含 {property_count} 个属性，可能表示数据类过于复杂",
                evidence=[f"属性数量: {property_count}"],
                location=cls.full_name,
                confidence=0.6,
                suggestions=["考虑使用组合或嵌套数据结构"],
            ))

        return responsibilities

    def _extract_function_design_decisions(self, func: FunctionInfo) -> list[ImplicitKnowledge]:
        """提取函数级别的设计决策"""
        decisions = []

        if func.is_async:
            decisions.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title=f"异步函数: {func.name}",
                description=f"{func.name} 是异步函数，用于 I/O 密集型操作，提高并发性能",
                evidence=["使用 async def 定义"],
                location=func.full_name,
                confidence=0.9,
            ))

        if len(func.parameters) > 5:
            decisions.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title=f"参数过多: {func.name}",
                description=f"{func.name} 有 {len(func.parameters)} 个参数，可能需要重构",
                evidence=[f"参数数量: {len(func.parameters)}"],
                location=func.full_name,
                confidence=0.7,
                suggestions=["考虑使用配置对象或字典参数"],
            ))

        return decisions

    def _extract_performance_considerations(self, func: FunctionInfo) -> list[ImplicitKnowledge]:
        """提取性能考量"""
        considerations = []

        perf_keywords = ["cache", "memoize", "lazy", "async", "concurrent", "parallel", "batch"]
        for keyword in perf_keywords:
            if keyword in func.name.lower():
                considerations.append(ImplicitKnowledge(
                    knowledge_type=KnowledgeType.PERFORMANCE_CONSIDERATION,
                    title=f"性能优化: {func.name}",
                    description=f"{func.name} 涉及性能优化策略: {keyword}",
                    evidence=[f"函数名包含 '{keyword}'"],
                    location=func.full_name,
                    confidence=0.7,
                ))
                break

        return considerations

    def _extract_security_considerations(self, func: FunctionInfo) -> list[ImplicitKnowledge]:
        """提取安全考量"""
        considerations = []

        security_keywords = ["auth", "login", "password", "token", "encrypt", "decrypt", "hash", "validate", "sanitize"]
        for keyword in security_keywords:
            if keyword in func.name.lower():
                considerations.append(ImplicitKnowledge(
                    knowledge_type=KnowledgeType.SECURITY_CONSIDERATION,
                    title=f"安全相关: {func.name}",
                    description=f"{func.name} 涉及安全敏感操作: {keyword}",
                    evidence=[f"函数名包含 '{keyword}'"],
                    location=func.full_name,
                    confidence=0.8,
                    suggestions=["确保正确处理敏感数据", "添加适当的日志和审计"],
                ))
                break

        return considerations

    def _load_design_patterns(self) -> dict:
        """加载设计模式定义"""
        return {
            "creational": ["singleton", "factory", "builder", "prototype"],
            "structural": ["adapter", "decorator", "facade", "proxy", "composite"],
            "behavioral": ["observer", "strategy", "command", "state", "template"],
        }

    def _load_architecture_patterns(self) -> dict:
        """加载架构模式定义"""
        return {
            "layered": ["controller", "service", "repository", "model"],
            "microservice": ["api", "handler", "processor", "consumer"],
            "event_driven": ["event", "listener", "publisher", "subscriber"],
        }

    def _load_convention_rules(self) -> dict:
        """加载编码规范规则"""
        return {
            "naming": {
                "class": "PascalCase",
                "function": "snake_case",
                "constant": "UPPER_SNAKE_CASE",
                "private": "_leading_underscore",
            },
            "docstring": {
                "module": "顶部三引号",
                "class": "类定义后三引号",
                "function": "函数定义后三引号",
            },
        }
