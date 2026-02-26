"""
技术债务检测器
检测代码中的技术债务和潜在问题
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from pywiki.parsers.types import ModuleInfo, ClassInfo, FunctionInfo


class DebtSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DebtCategory(str, Enum):
    CODE_SMELL = "code_smell"
    DUPLICATION = "duplication"
    COMPLEXITY = "complexity"
    COUPLING = "coupling"
    COHESION = "cohesion"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    PERFORMANCE = "performance"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"


@dataclass
class TechDebt:
    category: DebtCategory
    severity: DebtSeverity
    title: str
    description: str
    location: str
    evidence: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    effort_estimate: str = "medium"
    impact: str = "medium"
    metadata: dict[str, Any] = field(default_factory=dict)


class TechDebtDetector:
    """技术债务检测器"""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self._thresholds = self._load_thresholds()

    def detect_from_module(self, module: ModuleInfo) -> list[TechDebt]:
        """从模块检测技术债务"""
        debts = []

        debts.extend(self._detect_documentation_debt(module))
        debts.extend(self._detect_complexity_debt(module))
        debts.extend(self._detect_coupling_debt(module))

        for cls in module.classes:
            debts.extend(self._detect_from_class(cls))

        for func in module.functions:
            debts.extend(self._detect_from_function(func))

        return debts

    def detect_from_class(self, cls: ClassInfo) -> list[TechDebt]:
        """从类检测技术债务"""
        return self._detect_from_class(cls)

    def detect_from_function(self, func: FunctionInfo) -> list[TechDebt]:
        """从函数检测技术债务"""
        return self._detect_from_function(func)

    def _detect_from_class(self, cls: ClassInfo) -> list[TechDebt]:
        """从类检测技术债务"""
        debts = []

        debts.extend(self._detect_god_class(cls))
        debts.extend(self._detect_data_class(cls))
        debts.extend(self._detect_refused_bequest(cls))
        debts.extend(self._detect_inappropriate_intimacy(cls))
        debts.extend(self._detect_lazy_class(cls))
        debts.extend(self._detect_documentation_debt_class(cls))

        return debts

    def _detect_from_function(self, func: FunctionInfo) -> list[TechDebt]:
        """从函数检测技术债务"""
        debts = []

        debts.extend(self._detect_long_method(func))
        debts.extend(self._detect_parameter_list(func))
        debts.extend(self._detect_feature_envy(func))
        debts.extend(self._detect_primitive_obsession(func))
        debts.extend(self._detect_documentation_debt_function(func))

        return debts

    def _detect_documentation_debt(self, module: ModuleInfo) -> list[TechDebt]:
        """检测文档债务"""
        debts = []

        if not module.docstring:
            debts.append(TechDebt(
                category=DebtCategory.DOCUMENTATION,
                severity=DebtSeverity.LOW,
                title=f"缺少模块文档: {module.name}",
                description="模块缺少文档字符串，影响代码可读性和可维护性",
                location=module.name,
                evidence=["模块没有 docstring"],
                suggestions=["添加模块级别的文档字符串，描述模块的用途和主要功能"],
                effort_estimate="low",
                impact="low",
            ))

        undocumented_classes = [cls for cls in module.classes if not cls.docstring]
        if undocumented_classes:
            debts.append(TechDebt(
                category=DebtCategory.DOCUMENTATION,
                severity=DebtSeverity.LOW,
                title=f"缺少类文档: {module.name}",
                description=f"{len(undocumented_classes)} 个类缺少文档字符串",
                location=module.name,
                evidence=[f"类 {cls.name} 缺少 docstring" for cls in undocumented_classes[:5]],
                suggestions=["为每个公共类添加文档字符串"],
                effort_estimate="medium",
                impact="low",
            ))

        undocumented_functions = [f for f in module.functions if not f.docstring]
        if undocumented_functions:
            debts.append(TechDebt(
                category=DebtCategory.DOCUMENTATION,
                severity=DebtSeverity.INFO,
                title=f"缺少函数文档: {module.name}",
                description=f"{len(undocumented_functions)} 个函数缺少文档字符串",
                location=module.name,
                evidence=[f"函数 {f.name} 缺少 docstring" for f in undocumented_functions[:5]],
                suggestions=["为公共函数添加文档字符串"],
                effort_estimate="medium",
                impact="low",
            ))

        return debts

    def _detect_complexity_debt(self, module: ModuleInfo) -> list[TechDebt]:
        """检测复杂度债务"""
        debts = []

        total_methods = sum(len(cls.methods) for cls in module.classes)
        total_functions = len(module.functions)
        total_classes = len(module.classes)

        if total_classes > self._thresholds["max_classes_per_module"]:
            debts.append(TechDebt(
                category=DebtCategory.COMPLEXITY,
                severity=DebtSeverity.MEDIUM,
                title=f"模块过大: {module.name}",
                description=f"模块包含 {total_classes} 个类，超过建议的最大值 {self._thresholds['max_classes_per_module']}",
                location=module.name,
                evidence=[f"类数量: {total_classes}"],
                suggestions=["考虑将模块拆分为多个更小的模块"],
                effort_estimate="high",
                impact="medium",
            ))

        return debts

    def _detect_coupling_debt(self, module: ModuleInfo) -> list[TechDebt]:
        """检测耦合债务"""
        debts = []

        import_count = len(module.imports)
        if import_count > self._thresholds["max_imports"]:
            debts.append(TechDebt(
                category=DebtCategory.COUPLING,
                severity=DebtSeverity.MEDIUM,
                title=f"导入过多: {module.name}",
                description=f"模块有 {import_count} 个导入，可能表示高耦合",
                location=module.name,
                evidence=[f"导入数量: {import_count}"],
                suggestions=["检查是否可以减少依赖", "考虑使用依赖注入"],
                effort_estimate="medium",
                impact="medium",
            ))

        return debts

    def _detect_god_class(self, cls: ClassInfo) -> list[TechDebt]:
        """检测上帝类"""
        debts = []

        method_count = len(cls.methods)
        property_count = len(cls.properties) + len(cls.class_variables)

        if method_count > self._thresholds["max_methods_per_class"]:
            debts.append(TechDebt(
                category=DebtCategory.COMPLEXITY,
                severity=DebtSeverity.HIGH,
                title=f"上帝类: {cls.name}",
                description=f"类有 {method_count} 个方法，可能违反单一职责原则",
                location=cls.full_name,
                evidence=[f"方法数量: {method_count}"],
                suggestions=[
                    "将类拆分为多个更小的类",
                    "识别不同的职责并分离",
                    "使用组合替代继承",
                ],
                effort_estimate="high",
                impact="high",
            ))

        if property_count > self._thresholds["max_properties_per_class"]:
            debts.append(TechDebt(
                category=DebtCategory.COHESION,
                severity=DebtSeverity.MEDIUM,
                title=f"属性过多: {cls.name}",
                description=f"类有 {property_count} 个属性，可能表示低内聚",
                location=cls.full_name,
                evidence=[f"属性数量: {property_count}"],
                suggestions=["考虑将相关属性分组为嵌套对象"],
                effort_estimate="medium",
                impact="medium",
            ))

        return debts

    def _detect_data_class(self, cls: ClassInfo) -> list[TechDebt]:
        """检测数据类"""
        debts = []

        if cls.methods and not cls.is_dataclass:
            getter_setter_count = sum(
                1 for m in cls.methods
                if m.name.startswith("get_") or m.name.startswith("set_")
            )

            if getter_setter_count > len(cls.methods) * 0.8:
                debts.append(TechDebt(
                    category=DebtCategory.CODE_SMELL,
                    severity=DebtSeverity.LOW,
                    title=f"数据类: {cls.name}",
                    description="类主要是 getter/setter 方法，可能应该使用 @dataclass",
                    location=cls.full_name,
                    evidence=[f"getter/setter 比例: {getter_setter_count}/{len(cls.methods)}"],
                    suggestions=["考虑使用 @dataclass 装饰器", "考虑使用 Pydantic Model"],
                    effort_estimate="low",
                    impact="low",
                ))

        return debts

    def _detect_refused_bequest(self, cls: ClassInfo) -> list[TechDebt]:
        """检测拒绝继承"""
        debts = []

        if cls.bases:
            overridden_methods = set()
            for method in cls.methods:
                if not method.name.startswith("_"):
                    overridden_methods.add(method.name)

            if len(overridden_methods) == 0 and len(cls.bases) > 0:
                debts.append(TechDebt(
                    category=DebtCategory.CODE_SMELL,
                    severity=DebtSeverity.LOW,
                    title=f"拒绝继承: {cls.name}",
                    description="类继承自父类但没有添加或覆盖任何方法",
                    location=cls.full_name,
                    evidence=[f"继承自: {', '.join(cls.bases)}"],
                    suggestions=["检查继承关系是否必要", "考虑使用组合替代继承"],
                    effort_estimate="low",
                    impact="low",
                ))

        return debts

    def _detect_inappropriate_intimacy(self, cls: ClassInfo) -> list[TechDebt]:
        """检测不当亲密"""
        debts = []

        private_access_count = sum(
            1 for m in cls.methods
            for p in m.parameters
            if p.name.startswith("_") and p.name != "self"
        )

        if private_access_count > 0:
            debts.append(TechDebt(
                category=DebtCategory.COUPLING,
                severity=DebtSeverity.MEDIUM,
                title=f"不当亲密: {cls.name}",
                description="类的方法访问了其他类的私有成员",
                location=cls.full_name,
                evidence=[f"私有成员访问次数: {private_access_count}"],
                suggestions=["重构以减少类之间的耦合", "考虑使用公共接口"],
                effort_estimate="medium",
                impact="medium",
            ))

        return debts

    def _detect_lazy_class(self, cls: ClassInfo) -> list[TechDebt]:
        """检测懒惰类"""
        debts = []

        if len(cls.methods) <= 2 and len(cls.properties) <= 3 and not cls.bases:
            debts.append(TechDebt(
                category=DebtCategory.CODE_SMELL,
                severity=DebtSeverity.INFO,
                title=f"懒惰类: {cls.name}",
                description="类功能很少，可能应该被合并或删除",
                location=cls.full_name,
                evidence=[f"方法数量: {len(cls.methods)}", f"属性数量: {len(cls.properties)}"],
                suggestions=["考虑将功能合并到相关类中", "检查类是否还有存在的必要"],
                effort_estimate="low",
                impact="low",
            ))

        return debts

    def _detect_long_method(self, func: FunctionInfo) -> list[TechDebt]:
        """检测长方法"""
        debts = []

        line_count = func.line_end - func.line_start if func.line_end and func.line_start else 0

        if line_count > self._thresholds["max_lines_per_method"]:
            debts.append(TechDebt(
                category=DebtCategory.COMPLEXITY,
                severity=DebtSeverity.MEDIUM,
                title=f"长方法: {func.name}",
                description=f"方法有 {line_count} 行，超过建议的最大值 {self._thresholds['max_lines_per_method']}",
                location=func.full_name,
                evidence=[f"行数: {line_count}"],
                suggestions=[
                    "将方法拆分为多个更小的方法",
                    "提取重复代码为独立方法",
                    "使用提取方法重构",
                ],
                effort_estimate="medium",
                impact="medium",
            ))

        return debts

    def _detect_parameter_list(self, func: FunctionInfo) -> list[TechDebt]:
        """检测参数列表过长"""
        debts = []

        param_count = len(func.parameters)
        if param_count > self._thresholds["max_parameters"]:
            debts.append(TechDebt(
                category=DebtCategory.CODE_SMELL,
                severity=DebtSeverity.MEDIUM,
                title=f"参数过多: {func.name}",
                description=f"方法有 {param_count} 个参数，超过建议的最大值 {self._thresholds['max_parameters']}",
                location=func.full_name,
                evidence=[f"参数数量: {param_count}"],
                suggestions=[
                    "使用配置对象封装相关参数",
                    "使用构建者模式",
                    "考虑是否可以拆分方法",
                ],
                effort_estimate="medium",
                impact="medium",
            ))

        return debts

    def _detect_feature_envy(self, func: FunctionInfo) -> list[TechDebt]:
        """检测特性嫉妒"""
        debts = []

        non_self_params = [p for p in func.parameters if p.name != "self"]
        if len(non_self_params) > 0:
            other_type_params = [p for p in non_self_params if p.type_hint and p.type_hint != "str"]
            if len(other_type_params) >= 2:
                debts.append(TechDebt(
                    category=DebtCategory.CODE_SMELL,
                    severity=DebtSeverity.LOW,
                    title=f"特性嫉妒: {func.name}",
                    description="方法过多地使用了其他类的数据",
                    location=func.full_name,
                    evidence=[f"非基本类型参数: {len(other_type_params)}"],
                    suggestions=["考虑将方法移动到数据所在的类"],
                    effort_estimate="medium",
                    impact="low",
                ))

        return debts

    def _detect_primitive_obsession(self, func: FunctionInfo) -> list[TechDebt]:
        """检测基本类型偏执"""
        debts = []

        primitive_params = [
            p for p in func.parameters
            if p.type_hint in ("str", "int", "float", "bool")
        ]

        if len(primitive_params) > 3:
            debts.append(TechDebt(
                category=DebtCategory.CODE_SMELL,
                severity=DebtSeverity.LOW,
                title=f"基本类型偏执: {func.name}",
                description="方法使用了过多的基本类型参数",
                location=func.full_name,
                evidence=[f"基本类型参数数量: {len(primitive_params)}"],
                suggestions=["考虑使用值对象或数据类封装相关参数"],
                effort_estimate="medium",
                impact="low",
            ))

        return debts

    def _detect_documentation_debt_class(self, cls: ClassInfo) -> list[TechDebt]:
        """检测类的文档债务"""
        debts = []

        if not cls.docstring:
            debts.append(TechDebt(
                category=DebtCategory.DOCUMENTATION,
                severity=DebtSeverity.LOW,
                title=f"缺少类文档: {cls.name}",
                description="类缺少文档字符串",
                location=cls.full_name,
                evidence=["类没有 docstring"],
                suggestions=["添加类级别的文档字符串"],
                effort_estimate="low",
                impact="low",
            ))

        undocumented_methods = [m for m in cls.methods if not m.docstring]
        if undocumented_methods:
            debts.append(TechDebt(
                category=DebtCategory.DOCUMENTATION,
                severity=DebtSeverity.INFO,
                title=f"缺少方法文档: {cls.name}",
                description=f"{len(undocumented_methods)} 个方法缺少文档",
                location=cls.full_name,
                evidence=[f"方法 {m.name} 缺少 docstring" for m in undocumented_methods[:3]],
                suggestions=["为公共方法添加文档字符串"],
                effort_estimate="medium",
                impact="low",
            ))

        return debts

    def _detect_documentation_debt_function(self, func: FunctionInfo) -> list[TechDebt]:
        """检测函数的文档债务"""
        debts = []

        if not func.docstring:
            debts.append(TechDebt(
                category=DebtCategory.DOCUMENTATION,
                severity=DebtSeverity.INFO,
                title=f"缺少函数文档: {func.name}",
                description="函数缺少文档字符串",
                location=func.full_name,
                evidence=["函数没有 docstring"],
                suggestions=["添加函数文档字符串，描述参数、返回值和功能"],
                effort_estimate="low",
                impact="low",
            ))

        return debts

    def _load_thresholds(self) -> dict:
        """加载阈值配置"""
        return {
            "max_lines_per_method": 50,
            "max_parameters": 5,
            "max_methods_per_class": 15,
            "max_properties_per_class": 10,
            "max_classes_per_module": 20,
            "max_imports": 20,
            "max_cyclomatic_complexity": 10,
        }

    def generate_debt_report(self, debts: list[TechDebt]) -> dict:
        """生成技术债务报告"""
        report = {
            "total_debts": len(debts),
            "by_severity": {},
            "by_category": {},
            "critical_debts": [],
            "high_priority_debts": [],
            "summary": {},
        }

        for debt in debts:
            severity = debt.severity.value
            category = debt.category.value

            report["by_severity"][severity] = report["by_severity"].get(severity, 0) + 1
            report["by_category"][category] = report["by_category"].get(category, 0) + 1

            if debt.severity == DebtSeverity.CRITICAL:
                report["critical_debts"].append({
                    "title": debt.title,
                    "location": debt.location,
                    "description": debt.description,
                })
            elif debt.severity == DebtSeverity.HIGH:
                report["high_priority_debts"].append({
                    "title": debt.title,
                    "location": debt.location,
                    "description": debt.description,
                })

        report["summary"] = {
            "health_score": self._calculate_health_score(debts),
            "estimated_effort": self._estimate_total_effort(debts),
        }

        return report

    def _calculate_health_score(self, debts: list[TechDebt]) -> float:
        """计算代码健康分数"""
        if not debts:
            return 100.0

        severity_weights = {
            DebtSeverity.CRITICAL: 25,
            DebtSeverity.HIGH: 15,
            DebtSeverity.MEDIUM: 8,
            DebtSeverity.LOW: 3,
            DebtSeverity.INFO: 1,
        }

        total_penalty = sum(severity_weights.get(d.severity, 1) for d in debts)
        score = max(0, 100 - total_penalty)

        return round(score, 1)

    def _estimate_total_effort(self, debts: list[TechDebt]) -> dict:
        """估算总工作量"""
        effort_map = {"low": 1, "medium": 3, "high": 8}

        total_points = sum(
            effort_map.get(d.effort_estimate, 3)
            for d in debts
        )

        return {
            "story_points": total_points,
            "estimated_days": round(total_points / 3, 1),
        }
