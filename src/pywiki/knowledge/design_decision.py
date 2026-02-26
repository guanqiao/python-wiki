"""
设计决策分析器
深入分析代码中的设计决策及其原因
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from pywiki.parsers.types import ModuleInfo, ClassInfo, FunctionInfo


class DecisionCategory(str, Enum):
    ARCHITECTURE = "architecture"
    FRAMEWORK = "framework"
    PATTERN = "pattern"
    DATA_STRUCTURE = "data_structure"
    ALGORITHM = "algorithm"
    ERROR_HANDLING = "error_handling"
    TESTING = "testing"
    PERFORMANCE = "performance"
    SECURITY = "security"


@dataclass
class DesignDecision:
    category: DecisionCategory
    title: str
    description: str
    rationale: str
    trade_offs: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    impact: str = "medium"
    confidence: float = 0.0
    location: Optional[str] = None
    evidence: list[str] = field(default_factory=list)


class DesignDecisionAnalyzer:
    """设计决策分析器"""

    def __init__(self):
        self._decision_rules = self._load_decision_rules()

    def analyze_module(self, module: ModuleInfo) -> list[DesignDecision]:
        """分析模块级别的设计决策"""
        decisions = []

        decisions.extend(self._analyze_architecture_decisions(module))
        decisions.extend(self._analyze_framework_decisions(module))
        decisions.extend(self._analyze_error_handling_decisions(module))
        decisions.extend(self._analyze_testing_decisions(module))

        return decisions

    def analyze_class(self, cls: ClassInfo) -> list[DesignDecision]:
        """分析类级别的设计决策"""
        decisions = []

        decisions.extend(self._analyze_inheritance_decisions(cls))
        decisions.extend(self._analyze_pattern_decisions(cls))
        decisions.extend(self._analyze_data_structure_decisions(cls))

        return decisions

    def analyze_function(self, func: FunctionInfo) -> list[DesignDecision]:
        """分析函数级别的设计决策"""
        decisions = []

        decisions.extend(self._analyze_algorithm_decisions(func))
        decisions.extend(self._analyze_performance_decisions(func))
        decisions.extend(self._analyze_security_decisions(func))

        return decisions

    def _analyze_architecture_decisions(self, module: ModuleInfo) -> list[DesignDecision]:
        """分析架构决策"""
        decisions = []

        layer_indicators = {
            "controller": ("控制器层", "处理 HTTP 请求和响应", ["路由定义", "参数验证", "响应格式化"]),
            "service": ("服务层", "封装业务逻辑", ["事务管理", "业务规则", "跨模块协调"]),
            "repository": ("数据访问层", "抽象数据持久化", ["CRUD 操作", "查询封装", "缓存策略"]),
            "model": ("数据模型层", "定义数据结构", ["字段定义", "验证规则", "关系映射"]),
        }

        module_name_lower = module.name.lower()
        for keyword, (layer_name, purpose, responsibilities) in layer_indicators.items():
            if keyword in module_name_lower:
                decisions.append(DesignDecision(
                    category=DecisionCategory.ARCHITECTURE,
                    title=f"分层架构: {layer_name}",
                    description=f"模块 {module.name} 被设计为 {layer_name}",
                    rationale=f"{purpose}，遵循关注点分离原则",
                    trade_offs=[
                        "增加了代码层次，可能增加复杂度",
                        "提高了可维护性和可测试性",
                    ],
                    alternatives=["可以使用更扁平的结构", "可以考虑 CQRS 模式"],
                    impact="high",
                    confidence=0.8,
                    location=module.name,
                    evidence=[f"模块名称包含 '{keyword}'"],
                ))

        return decisions

    def _analyze_framework_decisions(self, module: ModuleInfo) -> list[DesignDecision]:
        """分析框架选择决策"""
        decisions = []

        framework_analysis = {
            "fastapi": {
                "rationale": "高性能异步框架，适合构建现代 API 服务",
                "trade_offs": ["学习曲线较陡", "生态相对较小", "性能优异"],
                "alternatives": ["Flask (更简单)", "Django (更全面)"],
            },
            "django": {
                "rationale": "全功能框架，适合快速开发和大型项目",
                "trade_offs": ["较重，性能一般", "功能全面，开发效率高"],
                "alternatives": ["FastAPI (更现代)", "Flask (更轻量)"],
            },
            "flask": {
                "rationale": "轻量级框架，灵活可控",
                "trade_offs": ["需要自己选择组件", "灵活性高", "适合中小项目"],
                "alternatives": ["FastAPI (异步)", "Django (全功能)"],
            },
            "sqlalchemy": {
                "rationale": "强大的 ORM，支持多种数据库",
                "trade_offs": ["学习曲线陡峭", "功能强大灵活"],
                "alternatives": ["Django ORM (更简单)", "Tortoise ORM (异步)"],
            },
        }

        for imp in module.imports:
            module_name = imp.module.split(".")[0].lower()
            if module_name in framework_analysis:
                info = framework_analysis[module_name]
                decisions.append(DesignDecision(
                    category=DecisionCategory.FRAMEWORK,
                    title=f"框架选择: {module_name}",
                    description=f"项目选择了 {module_name} 框架",
                    rationale=info["rationale"],
                    trade_offs=info["trade_offs"],
                    alternatives=info["alternatives"],
                    impact="high",
                    confidence=0.9,
                    location=module.name,
                    evidence=[f"导入: {imp.module}"],
                ))

        return decisions

    def _analyze_error_handling_decisions(self, module: ModuleInfo) -> list[DesignDecision]:
        """分析错误处理决策"""
        decisions = []

        has_custom_exceptions = any(
            any("Exception" in base for base in cls.bases)
            for cls in module.classes
        )

        if has_custom_exceptions:
            decisions.append(DesignDecision(
                category=DecisionCategory.ERROR_HANDLING,
                title="自定义异常体系",
                description="项目定义了自定义异常类",
                rationale="提供更精确的错误信息和处理逻辑，便于业务错误区分",
                trade_offs=[
                    "增加了代码量",
                    "提高了错误处理的精确性",
                    "便于错误追踪和日志记录",
                ],
                alternatives=["使用标准异常", "使用错误码"],
                impact="medium",
                confidence=0.85,
                location=module.name,
                evidence=["发现自定义异常类"],
            ))

        return decisions

    def _analyze_testing_decisions(self, module: ModuleInfo) -> list[DesignDecision]:
        """分析测试决策"""
        decisions = []

        test_indicators = ["test", "spec", "mock", "fixture"]
        module_name_lower = module.name.lower()

        if any(indicator in module_name_lower for indicator in test_indicators):
            decisions.append(DesignDecision(
                category=DecisionCategory.TESTING,
                title="测试策略",
                description="项目包含测试代码",
                rationale="确保代码质量和可维护性，支持持续集成",
                trade_offs=[
                    "增加开发时间",
                    "提高代码质量和信心",
                    "支持重构和演进",
                ],
                alternatives=["手动测试", "无测试"],
                impact="medium",
                confidence=0.8,
                location=module.name,
                evidence=["模块名称包含测试相关关键词"],
            ))

        return decisions

    def _analyze_inheritance_decisions(self, cls: ClassInfo) -> list[DesignDecision]:
        """分析继承决策"""
        decisions = []

        if len(cls.bases) > 1:
            decisions.append(DesignDecision(
                category=DecisionCategory.PATTERN,
                title=f"多重继承: {cls.name}",
                description=f"{cls.name} 使用了多重继承",
                rationale="组合多个类的功能，实现代码复用",
                trade_offs=[
                    "可能导致方法解析顺序(MRO)问题",
                    "增加代码复杂度",
                    "提高代码复用性",
                ],
                alternatives=["使用组合替代继承", "使用 Mixin 模式"],
                impact="medium",
                confidence=0.85,
                location=cls.full_name,
                evidence=[f"继承自: {', '.join(cls.bases)}"],
            ))

        if cls.is_abstract:
            decisions.append(DesignDecision(
                category=DecisionCategory.PATTERN,
                title=f"抽象基类: {cls.name}",
                description=f"{cls.name} 被设计为抽象基类",
                rationale="定义接口规范，强制子类实现特定方法",
                trade_offs=[
                    "增加了类的层次结构",
                    "提高了代码的规范性和一致性",
                ],
                alternatives=["使用 Protocol (类型提示)", "使用普通类"],
                impact="medium",
                confidence=0.9,
                location=cls.full_name,
                evidence=["包含抽象方法"],
            ))

        return decisions

    def _analyze_pattern_decisions(self, cls: ClassInfo) -> list[DesignDecision]:
        """分析设计模式决策"""
        decisions = []

        if cls.is_dataclass:
            decisions.append(DesignDecision(
                category=DecisionCategory.PATTERN,
                title=f"数据类模式: {cls.name}",
                description=f"{cls.name} 使用 @dataclass 装饰器",
                rationale="简化数据类的定义，自动生成常用方法",
                trade_offs=[
                    "减少了样板代码",
                    "适合纯数据类",
                    "不适合复杂业务逻辑",
                ],
                alternatives=["使用普通类", "使用 NamedTuple", "使用 Pydantic Model"],
                impact="low",
                confidence=0.95,
                location=cls.full_name,
                evidence=["使用了 @dataclass 装饰器"],
            ))

        return decisions

    def _analyze_data_structure_decisions(self, cls: ClassInfo) -> list[DesignDecision]:
        """分析数据结构决策"""
        decisions = []

        if cls.is_enum:
            decisions.append(DesignDecision(
                category=DecisionCategory.DATA_STRUCTURE,
                title=f"枚举类型: {cls.name}",
                description=f"{cls.name} 是枚举类型",
                rationale="定义一组相关的常量值，提供类型安全和可读性",
                trade_offs=[
                    "限制了值的范围",
                    "提高了代码可读性",
                    "支持迭代和比较",
                ],
                alternatives=["使用常量", "使用字典"],
                impact="low",
                confidence=0.95,
                location=cls.full_name,
                evidence=["继承自 Enum"],
            ))

        return decisions

    def _analyze_algorithm_decisions(self, func: FunctionInfo) -> list[DesignDecision]:
        """分析算法决策"""
        decisions = []

        if func.is_async:
            decisions.append(DesignDecision(
                category=DecisionCategory.ALGORITHM,
                title=f"异步处理: {func.name}",
                description=f"{func.name} 使用异步处理",
                rationale="提高 I/O 密集型操作的并发性能",
                trade_offs=[
                    "增加了代码复杂度",
                    "需要异步上下文",
                    "提高了并发性能",
                ],
                alternatives=["同步处理", "多线程"],
                impact="medium",
                confidence=0.9,
                location=func.full_name,
                evidence=["使用 async def 定义"],
            ))

        return decisions

    def _analyze_performance_decisions(self, func: FunctionInfo) -> list[DesignDecision]:
        """分析性能决策"""
        decisions = []

        perf_decorators = ["lru_cache", "cache", "cached_property", "functools.cache"]
        for decorator in func.decorators:
            if any(p in decorator.lower() for p in perf_decorators):
                decisions.append(DesignDecision(
                    category=DecisionCategory.PERFORMANCE,
                    title=f"缓存策略: {func.name}",
                    description=f"{func.name} 使用了缓存",
                    rationale="减少重复计算，提高性能",
                    trade_offs=[
                        "增加了内存使用",
                        "需要考虑缓存失效",
                        "显著提高重复调用性能",
                    ],
                    alternatives=["无缓存", "手动缓存", "Redis 缓存"],
                    impact="medium",
                    confidence=0.85,
                    location=func.full_name,
                    evidence=[f"使用装饰器: {decorator}"],
                ))

        return decisions

    def _analyze_security_decisions(self, func: FunctionInfo) -> list[DesignDecision]:
        """分析安全决策"""
        decisions = []

        security_indicators = {
            "hash": ("哈希处理", "对敏感数据进行哈希处理"),
            "encrypt": ("加密处理", "对敏感数据进行加密"),
            "decrypt": ("解密处理", "解密加密数据"),
            "validate": ("数据验证", "验证输入数据的有效性"),
            "sanitize": ("数据清理", "清理输入数据防止注入攻击"),
        }

        func_name_lower = func.name.lower()
        for keyword, (title, description) in security_indicators.items():
            if keyword in func_name_lower:
                decisions.append(DesignDecision(
                    category=DecisionCategory.SECURITY,
                    title=f"安全措施: {title}",
                    description=f"{func.name} 涉及 {description}",
                    rationale="保护敏感数据和系统安全",
                    trade_offs=[
                        "增加了处理开销",
                        "提高了安全性",
                        "需要正确实现",
                    ],
                    alternatives=["无安全措施", "使用第三方库"],
                    impact="high",
                    confidence=0.8,
                    location=func.full_name,
                    evidence=[f"函数名包含 '{keyword}'"],
                ))
                break

        return decisions

    def _load_decision_rules(self) -> dict:
        """加载决策规则"""
        return {
            "architecture": {
                "layered": ["controller", "service", "repository", "model"],
                "hexagonal": ["port", "adapter", "domain"],
                "microservice": ["api", "handler", "processor"],
            },
            "patterns": {
                "creational": ["factory", "builder", "singleton", "prototype"],
                "structural": ["adapter", "decorator", "facade", "proxy"],
                "behavioral": ["observer", "strategy", "command", "state"],
            },
        }
