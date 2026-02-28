"""
设计模式检测器
自动检测代码中使用的设计模式
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from pywiki.parsers.types import ModuleInfo, ClassInfo, FunctionInfo


class PatternCategory(str, Enum):
    CREATIONAL = "creational"
    STRUCTURAL = "structural"
    BEHAVIORAL = "behavioral"
    ARCHITECTURAL = "architectural"


@dataclass
class DetectedPattern:
    pattern_name: str
    category: PatternCategory
    description: str
    location: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    participants: list[str] = field(default_factory=list)
    benefits: list[str] = field(default_factory=list)
    drawbacks: list[str] = field(default_factory=list)


class DesignPatternDetector:
    """设计模式检测器"""

    def __init__(self):
        self._pattern_rules = self._load_pattern_rules()

    def detect_from_module(self, module: ModuleInfo) -> list[DetectedPattern]:
        """从模块检测设计模式"""
        patterns = []

        patterns.extend(self._detect_creational_patterns(module))
        patterns.extend(self._detect_structural_patterns(module))
        patterns.extend(self._detect_behavioral_patterns(module))

        return patterns

    def detect_from_class(self, cls: ClassInfo) -> list[DetectedPattern]:
        """从类检测设计模式"""
        patterns = []

        patterns.extend(self._detect_singleton(cls))
        patterns.extend(self._detect_factory(cls))
        patterns.extend(self._detect_builder(cls))
        patterns.extend(self._detect_observer(cls))
        patterns.extend(self._detect_strategy(cls))
        patterns.extend(self._detect_decorator_pattern(cls))

        return patterns

    def _detect_creational_patterns(self, module: ModuleInfo) -> list[DetectedPattern]:
        """检测创建型模式"""
        patterns = []

        for cls in module.classes:
            class_patterns = self.detect_from_class(cls)
            for p in class_patterns:
                if p.category == PatternCategory.CREATIONAL:
                    patterns.append(p)

        factory_funcs = [f for f in module.functions if self._is_factory_function(f)]
        if factory_funcs:
            patterns.append(DetectedPattern(
                pattern_name="Factory Method",
                category=PatternCategory.CREATIONAL,
                description="使用函数创建对象，封装创建逻辑",
                location=module.name,
                confidence=0.7,
                evidence=[f"工厂函数: {f.name}" for f in factory_funcs[:3]],
                participants=[f.name for f in factory_funcs],
                benefits=["封装创建逻辑", "易于扩展"],
                drawbacks=["可能增加代码量"],
            ))

        return patterns

    def _detect_structural_patterns(self, module: ModuleInfo) -> list[DetectedPattern]:
        """检测结构型模式"""
        patterns = []

        for cls in module.classes:
            if self._is_adapter_pattern(cls):
                patterns.append(DetectedPattern(
                    pattern_name="Adapter",
                    category=PatternCategory.STRUCTURAL,
                    description=f"{cls.name} 可能是适配器，转换接口",
                    location=cls.full_name,
                    confidence=0.6,
                    evidence=["类名包含 Adapter", "包装其他类"],
                    participants=[cls.name],
                    benefits=["接口兼容", "复用现有类"],
                ))

            if self._is_facade_pattern(cls, module):
                patterns.append(DetectedPattern(
                    pattern_name="Facade",
                    category=PatternCategory.STRUCTURAL,
                    description=f"{cls.name} 可能是外观模式，提供简化接口",
                    location=cls.full_name,
                    confidence=0.6,
                    evidence=["类名包含 Facade", "委托给多个类"],
                    participants=[cls.name],
                    benefits=["简化接口", "降低耦合"],
                ))

        return patterns

    def _detect_behavioral_patterns(self, module: ModuleInfo) -> list[DetectedPattern]:
        """检测行为型模式"""
        patterns = []

        observer_classes = []
        for cls in module.classes:
            if self._is_observer_pattern(cls):
                observer_classes.append(cls)

        if observer_classes:
            patterns.append(DetectedPattern(
                pattern_name="Observer",
                category=PatternCategory.BEHAVIORAL,
                description="检测到观察者模式，实现事件订阅机制",
                location=module.name,
                confidence=0.7,
                evidence=[f"观察者类: {c.name}" for c in observer_classes[:3]],
                participants=[c.name for c in observer_classes],
                benefits=["松耦合", "动态订阅"],
                drawbacks=["可能导致内存泄漏"],
            ))

        strategy_classes = []
        for cls in module.classes:
            if self._is_strategy_pattern(cls):
                strategy_classes.append(cls)

        if strategy_classes:
            patterns.append(DetectedPattern(
                pattern_name="Strategy",
                category=PatternCategory.BEHAVIORAL,
                description="检测到策略模式，封装可互换的算法",
                location=module.name,
                confidence=0.7,
                evidence=[f"策略类: {c.name}" for c in strategy_classes[:3]],
                participants=[c.name for c in strategy_classes],
                benefits=["算法可互换", "易于扩展"],
                drawbacks=["客户端需要知道所有策略"],
            ))

        return patterns

    def _detect_singleton(self, cls: ClassInfo) -> list[DetectedPattern]:
        """检测单例模式"""
        patterns = []

        has_instance = any("_instance" in v.name for v in cls.class_variables)
        has_new = any(m.name == "__new__" for m in cls.methods)
        has_get_instance = any(m.name in ("get_instance", "instance", "getInstance") for m in cls.methods)

        if has_instance or has_new or has_get_instance:
            patterns.append(DetectedPattern(
                pattern_name="Singleton",
                category=PatternCategory.CREATIONAL,
                description=f"{cls.name} 实现了单例模式",
                location=cls.full_name,
                confidence=0.8 if (has_instance and (has_new or has_get_instance)) else 0.6,
                evidence=[
                    "包含 _instance 类变量" if has_instance else "",
                    "重写 __new__ 方法" if has_new else "",
                    "包含 get_instance 方法" if has_get_instance else "",
                ],
                participants=[cls.name],
                benefits=["全局唯一实例", "延迟初始化"],
                drawbacks=["难以测试", "可能成为瓶颈"],
            ))

        return patterns

    def _detect_factory(self, cls: ClassInfo) -> list[DetectedPattern]:
        """检测工厂模式"""
        patterns = []

        factory_methods = [m for m in cls.methods if self._is_factory_method(m)]
        if factory_methods:
            patterns.append(DetectedPattern(
                pattern_name="Factory Method",
                category=PatternCategory.CREATIONAL,
                description=f"{cls.name} 包含工厂方法",
                location=cls.full_name,
                confidence=0.75,
                evidence=[f"工厂方法: {m.name}" for m in factory_methods],
                participants=[cls.name],
                benefits=["封装创建逻辑", "支持扩展"],
                drawbacks=["可能增加复杂度"],
            ))

        return patterns

    def _detect_builder(self, cls: ClassInfo) -> list[DetectedPattern]:
        """检测构建者模式"""
        patterns = []

        has_build = any(m.name == "build" for m in cls.methods)
        fluent_methods = [m for m in cls.methods if self._is_fluent_method(m)]

        if has_build and len(fluent_methods) >= 2:
            patterns.append(DetectedPattern(
                pattern_name="Builder",
                category=PatternCategory.CREATIONAL,
                description=f"{cls.name} 实现了构建者模式",
                location=cls.full_name,
                confidence=0.8,
                evidence=[
                    "包含 build 方法",
                    f"包含 {len(fluent_methods)} 个链式方法",
                ],
                participants=[cls.name],
                benefits=["分步构建复杂对象", "链式调用"],
                drawbacks=["增加代码量"],
            ))

        return patterns

    def _detect_observer(self, cls: ClassInfo) -> list[DetectedPattern]:
        """检测观察者模式"""
        patterns = []

        has_subscribe = any(m.name in ("subscribe", "attach", "add_observer") for m in cls.methods)
        has_notify = any(m.name in ("notify", "emit", "dispatch") for m in cls.methods)
        has_unsubscribe = any(m.name in ("unsubscribe", "detach", "remove_observer") for m in cls.methods)

        if has_subscribe and has_notify:
            patterns.append(DetectedPattern(
                pattern_name="Observer",
                category=PatternCategory.BEHAVIORAL,
                description=f"{cls.name} 实现了观察者模式",
                location=cls.full_name,
                confidence=0.8,
                evidence=[
                    "包含订阅方法" if has_subscribe else "",
                    "包含通知方法" if has_notify else "",
                    "包含取消订阅方法" if has_unsubscribe else "",
                ],
                participants=[cls.name],
                benefits=["松耦合", "动态订阅"],
                drawbacks=["可能导致内存泄漏"],
            ))

        return patterns

    def _detect_strategy(self, cls: ClassInfo) -> list[DetectedPattern]:
        """检测策略模式"""
        patterns = []

        if cls.is_abstract or any("ABC" in base for base in cls.bases):
            concrete_implementations = len([m for m in cls.methods if not m.is_abstract])
            if concrete_implementations >= 2:
                patterns.append(DetectedPattern(
                    pattern_name="Strategy",
                    category=PatternCategory.BEHAVIORAL,
                    description=f"{cls.name} 可能是策略接口",
                    location=cls.full_name,
                    confidence=0.6,
                    evidence=["抽象类/接口", f"包含 {concrete_implementations} 个方法"],
                    participants=[cls.name],
                    benefits=["算法可互换", "易于扩展"],
                ))

        return patterns

    def _detect_decorator_pattern(self, cls: ClassInfo) -> list[DetectedPattern]:
        """检测装饰器模式"""
        patterns = []

        has_same_interface = any(base == cls.name.replace("Decorator", "").replace("Wrapper", "") for base in cls.bases)
        has_wrapped = any("_wrapped" in v.name or "_component" in v.name for v in cls.properties)
        delegates_methods = len([m for m in cls.methods if "self._wrapped" in str(m) or "self._component" in str(m)])

        if (has_same_interface or has_wrapped) and cls.name.endswith(("Decorator", "Wrapper")):
            patterns.append(DetectedPattern(
                pattern_name="Decorator",
                category=PatternCategory.STRUCTURAL,
                description=f"{cls.name} 实现了装饰器模式",
                location=cls.full_name,
                confidence=0.75,
                evidence=["类名包含 Decorator/Wrapper", "包装其他对象"],
                participants=[cls.name],
                benefits=["动态添加功能", "遵循开闭原则"],
                drawbacks=["增加复杂度"],
            ))

        return patterns

    def _is_factory_function(self, func: FunctionInfo) -> bool:
        """检查是否是工厂函数"""
        factory_keywords = ["create", "make", "build", "factory", "get_instance"]
        return any(kw in func.name.lower() for kw in factory_keywords)

    def _is_factory_method(self, method) -> bool:
        """检查是否是工厂方法"""
        factory_keywords = ["create", "make", "build", "factory"]
        return any(kw in method.name.lower() for kw in factory_keywords)

    def _is_fluent_method(self, method) -> bool:
        """检查是否是链式方法"""
        return method.return_type in ("self", "Self") or "self" in str(method.return_type or "")

    def _is_adapter_pattern(self, cls: ClassInfo) -> bool:
        """检查是否是适配器模式"""
        adapter_keywords = ["adapter", "wrapper", "proxy"]
        return any(kw in cls.name.lower() for kw in adapter_keywords)

    def _is_facade_pattern(self, cls: ClassInfo, module: ModuleInfo) -> bool:
        """检查是否是外观模式"""
        facade_keywords = ["facade", "service"]
        if any(kw in cls.name.lower() for kw in facade_keywords):
            return len(cls.methods) > 3
        return False

    def _is_observer_pattern(self, cls: ClassInfo) -> bool:
        """检查是否是观察者模式"""
        observer_keywords = ["observer", "listener", "subscriber", "handler"]
        subject_keywords = ["subject", "observable", "emitter", "publisher"]

        cls_name_lower = cls.name.lower()
        return any(kw in cls_name_lower for kw in observer_keywords + subject_keywords)

    def _is_strategy_pattern(self, cls: ClassInfo) -> bool:
        """检查是否是策略模式"""
        strategy_keywords = ["strategy", "policy", "algorithm"]
        cls_name_lower = cls.name.lower()
        return any(kw in cls_name_lower for kw in strategy_keywords)

    def _load_pattern_rules(self) -> dict:
        """加载模式规则"""
        return {
            "creational": {
                "singleton": {
                    "indicators": ["_instance", "__new__", "get_instance"],
                    "required": 2,
                },
                "factory": {
                    "indicators": ["create", "factory", "make"],
                    "required": 1,
                },
                "builder": {
                    "indicators": ["build", "with_", "set_"],
                    "required": 2,
                },
            },
            "structural": {
                "adapter": {
                    "indicators": ["adapter", "wrapper"],
                    "required": 1,
                },
                "decorator": {
                    "indicators": ["decorator", "wrapper", "_wrapped"],
                    "required": 2,
                },
                "facade": {
                    "indicators": ["facade", "service"],
                    "required": 1,
                },
            },
            "behavioral": {
                "observer": {
                    "indicators": ["observer", "subscribe", "notify"],
                    "required": 2,
                },
                "strategy": {
                    "indicators": ["strategy", "execute", "algorithm"],
                    "required": 1,
                },
                "command": {
                    "indicators": ["command", "execute", "undo"],
                    "required": 2,
                },
            },
        }

    def generate_pattern_report(self, patterns: list[DetectedPattern]) -> dict:
        """生成模式报告"""
        report = {
            "total_patterns": len(patterns),
            "by_category": {},
            "patterns": [],
        }

        for pattern in patterns:
            cat = pattern.category.value
            report["by_category"][cat] = report["by_category"].get(cat, 0) + 1

            report["patterns"].append({
                "name": pattern.pattern_name,
                "category": pattern.category.value,
                "location": pattern.location,
                "confidence": pattern.confidence,
                "description": pattern.description,
            })

        return report
    
    def detect_architecture_patterns(
        self,
        subpackages: list[Any],
        layers: Optional[list[Any]] = None
    ) -> list[DetectedPattern]:
        """检测包级别的架构模式
        
        Args:
            subpackages: 子包信息列表
            layers: 架构层列表（可选）
            
        Returns:
            检测到的架构模式列表
        """
        patterns = []
        
        if not subpackages:
            return patterns
        
        patterns.extend(self._detect_layered_architecture_pattern(subpackages, layers))
        patterns.extend(self._detect_microservice_pattern(subpackages))
        patterns.extend(self._detect_hexagonal_architecture(subpackages))
        patterns.extend(self._detect_mvc_pattern(subpackages))
        patterns.extend(self._detect_repository_pattern(subpackages))
        
        return patterns
    
    def _detect_layered_architecture_pattern(
        self,
        subpackages: list[Any],
        layers: Optional[list[Any]] = None
    ) -> list[DetectedPattern]:
        """检测分层架构模式"""
        patterns = []
        
        layer_indicators = {
            "presentation": ["controller", "api", "view", "ui", "handler", "endpoint", "route"],
            "business": ["service", "domain", "usecase", "logic", "manager", "processor"],
            "data": ["repository", "dao", "model", "entity", "data", "store", "persistence"],
            "infrastructure": ["config", "util", "common", "infrastructure", "shared"],
        }
        
        detected_layers = set()
        for sp in subpackages:
            name_lower = sp.name.lower() if hasattr(sp, 'name') else str(sp).lower()
            for layer, indicators in layer_indicators.items():
                for indicator in indicators:
                    if indicator in name_lower:
                        detected_layers.add(layer)
                        break
        
        if len(detected_layers) >= 2:
            patterns.append(DetectedPattern(
                pattern_name="Layered Architecture",
                category=PatternCategory.ARCHITECTURAL,
                description=f"检测到分层架构，包含 {len(detected_layers)} 个层: {', '.join(detected_layers)}",
                location="project",
                confidence=0.8 if len(detected_layers) >= 3 else 0.6,
                evidence=[f"检测到层: {layer}" for layer in detected_layers],
                benefits=[
                    "关注点分离",
                    "易于理解和维护",
                    "便于测试",
                ],
                drawbacks=[
                    "可能导致层间耦合",
                    "简单场景可能过度设计",
                ],
            ))
        
        return patterns
    
    def _detect_microservice_pattern(self, subpackages: list[Any]) -> list[DetectedPattern]:
        """检测微服务架构模式"""
        patterns = []
        
        service_indicators = ["service", "api", "gateway", "proxy", "client"]
        service_packages = []
        
        for sp in subpackages:
            name_lower = sp.name.lower() if hasattr(sp, 'name') else str(sp).lower()
            for indicator in service_indicators:
                if indicator in name_lower:
                    service_packages.append(sp.name if hasattr(sp, 'name') else str(sp))
                    break
        
        if len(service_packages) >= 3:
            patterns.append(DetectedPattern(
                pattern_name="Microservice Architecture",
                category=PatternCategory.ARCHITECTURAL,
                description=f"检测到可能的微服务架构，包含 {len(service_packages)} 个服务相关包",
                location="project",
                confidence=0.6,
                evidence=[f"服务包: {name}" for name in service_packages[:5]],
                benefits=[
                    "独立部署和扩展",
                    "技术栈灵活",
                    "团队自治",
                ],
                drawbacks=[
                    "分布式系统复杂性",
                    "服务间通信开销",
                    "运维成本增加",
                ],
            ))
        
        return patterns
    
    def _detect_hexagonal_architecture(self, subpackages: list[Any]) -> list[DetectedPattern]:
        """检测六边形架构（端口与适配器）"""
        patterns = []
        
        hexagonal_indicators = {
            "core": ["domain", "core", "application"],
            "ports": ["port", "interface", "contract"],
            "adapters": ["adapter", "infrastructure", "persistence", "repository"],
        }
        
        detected_components = set()
        for sp in subpackages:
            name_lower = sp.name.lower() if hasattr(sp, 'name') else str(sp).lower()
            for component, indicators in hexagonal_indicators.items():
                for indicator in indicators:
                    if indicator in name_lower:
                        detected_components.add(component)
                        break
        
        if len(detected_components) >= 2:
            patterns.append(DetectedPattern(
                pattern_name="Hexagonal Architecture",
                category=PatternCategory.ARCHITECTURAL,
                description="检测到六边形架构模式（端口与适配器）",
                location="project",
                confidence=0.7,
                evidence=[f"组件: {comp}" for comp in detected_components],
                benefits=[
                    "核心业务逻辑与技术细节解耦",
                    "易于测试",
                    "便于替换基础设施",
                ],
                drawbacks=[
                    "增加抽象层",
                    "学习曲线较陡",
                ],
            ))
        
        return patterns
    
    def _detect_mvc_pattern(self, subpackages: list[Any]) -> list[DetectedPattern]:
        """检测 MVC 架构模式"""
        patterns = []
        
        mvc_indicators = {
            "model": ["model", "entity", "domain"],
            "view": ["view", "template", "ui", "component"],
            "controller": ["controller", "handler", "route"],
        }
        
        detected_components = set()
        for sp in subpackages:
            name_lower = sp.name.lower() if hasattr(sp, 'name') else str(sp).lower()
            for component, indicators in mvc_indicators.items():
                for indicator in indicators:
                    if indicator in name_lower:
                        detected_components.add(component)
                        break
        
        if len(detected_components) == 3:
            patterns.append(DetectedPattern(
                pattern_name="MVC Architecture",
                category=PatternCategory.ARCHITECTURAL,
                description="检测到 MVC（Model-View-Controller）架构模式",
                location="project",
                confidence=0.8,
                evidence=[f"组件: {comp}" for comp in detected_components],
                benefits=[
                    "关注点分离",
                    "易于维护和测试",
                    "并行开发",
                ],
                drawbacks=[
                    "控制器可能变得臃肿",
                    "视图和模型可能耦合",
                ],
            ))
        
        return patterns
    
    def _detect_repository_pattern(self, subpackages: list[Any]) -> list[DetectedPattern]:
        """检测仓储模式"""
        patterns = []
        
        repository_packages = []
        for sp in subpackages:
            name_lower = sp.name.lower() if hasattr(sp, 'name') else str(sp).lower()
            if "repository" in name_lower or "repo" in name_lower:
                repository_packages.append(sp.name if hasattr(sp, 'name') else str(sp))
        
        if repository_packages:
            patterns.append(DetectedPattern(
                pattern_name="Repository Pattern",
                category=PatternCategory.ARCHITECTURAL,
                description=f"检测到仓储模式，包含 {len(repository_packages)} 个仓储包",
                location="project",
                confidence=0.85,
                evidence=[f"仓储包: {name}" for name in repository_packages[:5]],
                benefits=[
                    "数据访问逻辑集中",
                    "易于单元测试",
                    "业务逻辑与数据访问解耦",
                ],
                drawbacks=[
                    "可能增加抽象层",
                    "简单查询可能过度设计",
                ],
            ))
        
        return patterns
