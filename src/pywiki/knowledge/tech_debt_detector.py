"""
技术债务检测器
检测代码中的技术债务、代码异味和潜在问题
"""

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from pywiki.knowledge.implicit_extractor import (
    BaseKnowledgeExtractor,
    ExtractionContext,
    ImplicitKnowledge,
    KnowledgeType,
    KnowledgePriority,
)
from pywiki.parsers.types import ModuleInfo, ClassInfo, FunctionInfo


@dataclass
class CodeSmell:
    name: str
    category: str
    description: str
    severity: str
    suggestion: str


CODE_SMELLS: dict[str, CodeSmell] = {
    "long_method": CodeSmell(
        name="Long Method",
        category="complexity",
        description="方法过长，难以理解和维护",
        severity="medium",
        suggestion="将方法拆分为更小的、职责单一的方法",
    ),
    "large_class": CodeSmell(
        name="Large Class",
        category="complexity",
        description="类过大，承担了过多职责",
        severity="high",
        suggestion="应用单一职责原则，将类拆分",
    ),
    "long_parameter_list": CodeSmell(
        name="Long Parameter List",
        category="complexity",
        description="参数列表过长，调用困难",
        severity="medium",
        suggestion="使用参数对象或构建者模式",
    ),
    "duplicate_code": CodeSmell(
        name="Duplicate Code",
        category="redundancy",
        description="存在重复代码",
        severity="high",
        suggestion="提取公共方法或使用继承",
    ),
    "dead_code": CodeSmell(
        name="Dead Code",
        category="redundancy",
        description="存在未使用的代码",
        severity="low",
        suggestion="删除未使用的代码",
    ),
    "magic_number": CodeSmell(
        name="Magic Number",
        category="readability",
        description="存在魔法数字，缺乏语义",
        severity="low",
        suggestion="将数字提取为常量并命名",
    ),
    "deep_nesting": CodeSmell(
        name="Deep Nesting",
        category="complexity",
        description="嵌套层级过深",
        severity="medium",
        suggestion="使用提前返回或提取方法",
    ),
    "complex_condition": CodeSmell(
        name="Complex Condition",
        category="complexity",
        description="条件表达式过于复杂",
        severity="medium",
        suggestion="提取条件为有意义的方法",
    ),
    "god_class": CodeSmell(
        name="God Class",
        category="design",
        description="上帝类，知道太多、做太多",
        severity="critical",
        suggestion="拆分职责，遵循单一职责原则",
    ),
    "feature_envy": CodeSmell(
        name="Feature Envy",
        category="design",
        description="方法过度访问其他类的数据",
        severity="medium",
        suggestion="将方法移动到数据所在的类",
    ),
}

THRESHOLDS = {
    "method_lines": 50,
    "method_params": 5,
    "class_methods": 20,
    "class_properties": 15,
    "nesting_depth": 4,
    "cyclomatic_complexity": 10,
}


class TechDebtDetector(BaseKnowledgeExtractor):
    """
    技术债务检测器
    检测代码异味、复杂度问题和技术债务
    """

    @property
    def knowledge_type(self) -> KnowledgeType:
        return KnowledgeType.TECH_DEBT

    def extract(self, context: ExtractionContext) -> list[ImplicitKnowledge]:
        """提取技术债务"""
        knowledge = []

        if context.class_info:
            knowledge.extend(self._detect_class_smells(context))

        if context.module_info:
            knowledge.extend(self._detect_module_smells(context))

        if context.code_content:
            knowledge.extend(self._detect_code_smells(context))

        return knowledge

    def _detect_class_smells(self, context: ExtractionContext) -> list[ImplicitKnowledge]:
        """检测类级别的代码异味"""
        knowledge = []
        cls = context.class_info

        if len(cls.methods) > THRESHOLDS["class_methods"]:
            knowledge.append(self._create_smell_knowledge(
                smell=CODE_SMELLS["large_class"],
                location=cls.full_name,
                evidence=[f"方法数量: {len(cls.methods)} (阈值: {THRESHOLDS['class_methods']})"],
                confidence=0.9,
            ))

        if len(cls.properties) > THRESHOLDS["class_properties"]:
            knowledge.append(self._create_smell_knowledge(
                smell=CODE_SMELLS["large_class"],
                location=cls.full_name,
                evidence=[f"属性数量: {len(cls.properties)} (阈值: {THRESHOLDS['class_properties']})"],
                confidence=0.85,
            ))

        total_methods = len(cls.methods)
        if total_methods > 15:
            public_methods = len([m for m in cls.methods if not m.name.startswith("_")])
            if public_methods > 10:
                knowledge.append(self._create_smell_knowledge(
                    smell=CODE_SMELLS["god_class"],
                    location=cls.full_name,
                    evidence=[
                        f"公共方法: {public_methods}",
                        f"总方法: {total_methods}",
                    ],
                    confidence=0.75,
                    priority=KnowledgePriority.HIGH,
                ))

        for method in cls.methods:
            method_smells = self._detect_method_smells(method, cls.full_name)
            knowledge.extend(method_smells)

        return knowledge

    def _detect_method_smells(
        self,
        method: FunctionInfo,
        class_name: str,
    ) -> list[ImplicitKnowledge]:
        """检测方法级别的代码异味"""
        knowledge = []

        if len(method.parameters) > THRESHOLDS["method_params"]:
            knowledge.append(self._create_smell_knowledge(
                smell=CODE_SMELLS["long_parameter_list"],
                location=f"{class_name}.{method.name}",
                evidence=[
                    f"参数数量: {len(method.parameters)} (阈值: {THRESHOLDS['method_params']})",
                    f"参数: {', '.join(method.parameters[:10])}",
                ],
                confidence=0.9,
            ))

        return knowledge

    def _detect_module_smells(self, context: ExtractionContext) -> list[ImplicitKnowledge]:
        """检测模块级别的代码异味"""
        knowledge = []
        module = context.module_info

        if len(module.classes) > 20:
            knowledge.append(self._create_smell_knowledge(
                smell=CodeSmell(
                    name="Large Module",
                    category="complexity",
                    description="模块包含过多类",
                    severity="medium",
                    suggestion="考虑拆分模块",
                ),
                location=module.name,
                evidence=[f"类数量: {len(module.classes)}"],
                confidence=0.8,
            ))

        if len(module.functions) > 30:
            knowledge.append(self._create_smell_knowledge(
                smell=CodeSmell(
                    name="Many Functions",
                    category="complexity",
                    description="模块包含过多独立函数",
                    severity="low",
                    suggestion="考虑将函数组织到类中",
                ),
                location=module.name,
                evidence=[f"函数数量: {len(module.functions)}"],
                confidence=0.7,
            ))

        return knowledge

    def _detect_code_smells(self, context: ExtractionContext) -> list[ImplicitKnowledge]:
        """从代码内容检测代码异味"""
        knowledge = []
        code = context.code_content

        lines = code.split("\n")

        magic_numbers = re.findall(r'\b(\d{2,})\b(?!\s*[):,\]])', code)
        magic_numbers = [n for n in magic_numbers if n not in ("0", "1", "100", "1000")]
        if len(magic_numbers) > 5:
            knowledge.append(self._create_smell_knowledge(
                smell=CODE_SMELLS["magic_number"],
                location=context.project_path.name,
                evidence=[f"发现 {len(magic_numbers)} 个魔法数字"],
                confidence=0.6,
            ))

        todo_count = len(re.findall(r'#\s*TODO', code, re.IGNORECASE))
        fixme_count = len(re.findall(r'#\s*FIXME', code, re.IGNORECASE))
        hack_count = len(re.findall(r'#\s*HACK', code, re.IGNORECASE))

        if todo_count + fixme_count + hack_count > 3:
            knowledge.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.TECH_DEBT,
                title="存在多处待处理标记",
                description=f"代码中存在 {todo_count} 个 TODO, {fixme_count} 个 FIXME, {hack_count} 个 HACK 标记。",
                location=context.project_path.name,
                evidence=[
                    f"TODO: {todo_count}",
                    f"FIXME: {fixme_count}",
                    f"HACK: {hack_count}",
                ],
                confidence=0.95,
                priority=KnowledgePriority.HIGH if fixme_count > 0 else KnowledgePriority.MEDIUM,
                impact="可能存在未解决的技术债务",
                recommendation="优先处理 FIXME 标记，定期清理 TODO",
            ))

        max_nesting = self._calculate_max_nesting(code)
        if max_nesting > THRESHOLDS["nesting_depth"]:
            knowledge.append(self._create_smell_knowledge(
                smell=CODE_SMELLS["deep_nesting"],
                location=context.project_path.name,
                evidence=[f"最大嵌套深度: {max_nesting} (阈值: {THRESHOLDS['nesting_depth']})"],
                confidence=0.85,
            ))

        commented_code = self._detect_commented_code(code)
        if commented_code:
            knowledge.append(self._create_smell_knowledge(
                smell=CODE_SMELLS["dead_code"],
                location=context.project_path.name,
                evidence=[f"发现 {len(commented_code)} 处可能被注释的代码"],
                confidence=0.7,
            ))

        return knowledge

    def _calculate_max_nesting(self, code: str) -> int:
        """计算最大嵌套深度"""
        max_depth = 0
        current_depth = 0

        for char in code:
            if char == '{':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == '}':
                current_depth = max(0, current_depth - 1)

        for line in code.split("\n"):
            indent = len(line) - len(line.lstrip())
            depth = indent // 4
            max_depth = max(max_depth, depth)

        return max_depth

    def _detect_commented_code(self, code: str) -> list[str]:
        """检测被注释的代码"""
        commented_code = []

        code_patterns = [
            r'#\s*(def|class|if|for|while|return|import|from)\s',
            r'#\s*\w+\s*[=:]\s*',
            r'#\s*\w+\([^)]*\)',
        ]

        for pattern in code_patterns:
            matches = re.findall(pattern, code)
            commented_code.extend(matches)

        return commented_code

    def _create_smell_knowledge(
        self,
        smell: CodeSmell,
        location: str,
        evidence: list[str],
        confidence: float,
        priority: Optional[KnowledgePriority] = None,
    ) -> ImplicitKnowledge:
        """创建代码异味知识"""
        priority_map = {
            "low": KnowledgePriority.LOW,
            "medium": KnowledgePriority.MEDIUM,
            "high": KnowledgePriority.HIGH,
            "critical": KnowledgePriority.CRITICAL,
        }

        return ImplicitKnowledge(
            knowledge_type=KnowledgeType.CODE_SMELL,
            title=f"代码异味: {smell.name}",
            description=smell.description,
            location=location,
            evidence=evidence,
            confidence=confidence,
            priority=priority or priority_map.get(smell.severity, KnowledgePriority.MEDIUM),
            impact=f"影响代码可维护性和可读性",
            recommendation=smell.suggestion,
            metadata={
                "smell_name": smell.name,
                "smell_category": smell.category,
                "severity": smell.severity,
            },
        )

    def calculate_technical_debt_score(
        self,
        knowledge_list: list[ImplicitKnowledge],
    ) -> dict[str, Any]:
        """
        计算技术债务分数

        Args:
            knowledge_list: 检测到的知识列表

        Returns:
            技术债务评估报告
        """
        debt_items = [
            k for k in knowledge_list
            if k.knowledge_type in (KnowledgeType.TECH_DEBT, KnowledgeType.CODE_SMELL)
        ]

        severity_weights = {
            KnowledgePriority.LOW: 1,
            KnowledgePriority.MEDIUM: 3,
            KnowledgePriority.HIGH: 5,
            KnowledgePriority.CRITICAL: 10,
        }

        total_score = sum(
            severity_weights.get(k.priority, 1) * k.confidence
            for k in debt_items
        )

        by_severity: dict[str, int] = {}
        by_type: dict[str, int] = {}

        for k in debt_items:
            severity_key = k.priority.value
            by_severity[severity_key] = by_severity.get(severity_key, 0) + 1

            type_key = k.metadata.get("smell_name", k.knowledge_type.value)
            by_type[type_key] = by_type.get(type_key, 0) + 1

        return {
            "total_score": round(total_score, 2),
            "total_items": len(debt_items),
            "by_severity": by_severity,
            "by_type": by_type,
            "health_score": max(0, 100 - total_score),
            "recommendation": self._generate_debt_recommendation(total_score),
        }

    def _generate_debt_recommendation(self, score: float) -> str:
        """生成债务建议"""
        if score < 10:
            return "代码质量良好，继续保持。"
        elif score < 30:
            return "存在少量技术债务，建议在迭代中逐步处理。"
        elif score < 50:
            return "技术债务较多，建议安排专项时间进行重构。"
        else:
            return "技术债务严重，建议立即制定重构计划并优先处理。"
