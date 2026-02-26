"""
设计动机分析器
从代码结构推断设计意图和动机
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
class DesignPattern:
    name: str
    category: str
    indicators: list[str]
    motivation: str
    benefits: list[str]
    drawbacks: list[str]


DESIGN_PATTERNS: dict[str, DesignPattern] = {
    "singleton": DesignPattern(
        name="Singleton",
        category="creational",
        indicators=["_instance", "__new__", "get_instance", "getInstance"],
        motivation="确保类只有一个实例，并提供全局访问点",
        benefits=["全局唯一实例", "延迟初始化", "减少资源消耗"],
        drawbacks=["难以测试", "可能成为瓶颈", "隐藏依赖关系"],
    ),
    "factory": DesignPattern(
        name="Factory Method",
        category="creational",
        indicators=["create_", "factory", "make_", "build_"],
        motivation="将对象的创建逻辑封装起来，使创建过程灵活可扩展",
        benefits=["封装创建逻辑", "易于扩展", "解耦客户端和具体类"],
        drawbacks=["增加代码量", "可能过度设计"],
    ),
    "builder": DesignPattern(
        name="Builder",
        category="creational",
        indicators=["build", "with_", "set_", "fluent"],
        motivation="分步构建复杂对象，使构建过程清晰可控",
        benefits=["分步构建", "链式调用", "参数验证"],
        drawbacks=["增加代码量", "需要创建Builder类"],
    ),
    "observer": DesignPattern(
        name="Observer",
        category="behavioral",
        indicators=["subscribe", "notify", "emit", "observer", "listener"],
        motivation="实现对象间的一对多依赖，当状态变化时通知所有依赖者",
        benefits=["松耦合", "动态订阅", "广播通信"],
        drawbacks=["可能导致内存泄漏", "调试困难"],
    ),
    "strategy": DesignPattern(
        name="Strategy",
        category="behavioral",
        indicators=["strategy", "algorithm", "execute", "policy"],
        motivation="定义一系列算法，使它们可以互换",
        benefits=["算法可互换", "易于扩展", "消除条件语句"],
        drawbacks=["客户端需要知道所有策略", "增加对象数量"],
    ),
    "decorator": DesignPattern(
        name="Decorator",
        category="structural",
        indicators=["decorator", "wrapper", "_wrapped", "_component"],
        motivation="动态地给对象添加额外功能",
        benefits=["动态添加功能", "遵循开闭原则", "灵活组合"],
        drawbacks=["增加复杂度", "可能产生很多小对象"],
    ),
    "adapter": DesignPattern(
        name="Adapter",
        category="structural",
        indicators=["adapter", "wrapper", "convert"],
        motivation="使不兼容的接口能够协同工作",
        benefits=["接口兼容", "复用现有类", "解耦"],
        drawbacks=["增加间接层", "可能影响性能"],
    ),
    "facade": DesignPattern(
        name="Facade",
        category="structural",
        indicators=["facade", "service", "manager"],
        motivation="为复杂子系统提供简化的接口",
        benefits=["简化接口", "降低耦合", "分层设计"],
        drawbacks=["可能成为上帝对象", "隐藏功能"],
    ),
}


class DesignMotivationExtractor(BaseKnowledgeExtractor):
    """
    设计动机提取器
    分析代码结构，推断设计意图
    """

    @property
    def knowledge_type(self) -> KnowledgeType:
        return KnowledgeType.DESIGN_DECISION

    def extract(self, context: ExtractionContext) -> list[ImplicitKnowledge]:
        """提取设计动机"""
        knowledge = []

        if context.class_info:
            knowledge.extend(self._extract_from_class(context))

        if context.module_info:
            knowledge.extend(self._extract_from_module(context))

        if context.code_content:
            knowledge.extend(self._extract_from_code(context))

        return knowledge

    def _extract_from_class(self, context: ExtractionContext) -> list[ImplicitKnowledge]:
        """从类提取设计动机"""
        knowledge = []
        cls = context.class_info

        for pattern_name, pattern in DESIGN_PATTERNS.items():
            detected = self._detect_pattern_in_class(cls, pattern)
            if detected:
                knowledge.append(ImplicitKnowledge(
                    knowledge_type=KnowledgeType.DESIGN_DECISION,
                    title=f"使用 {pattern.name} 设计模式",
                    description=f"{cls.name} 实现了 {pattern.name} 模式。{pattern.motivation}",
                    location=cls.full_name,
                    evidence=detected["evidence"],
                    confidence=detected["confidence"],
                    priority=KnowledgePriority.MEDIUM,
                    impact=self._generate_impact(pattern),
                    recommendation=self._generate_recommendation(pattern, cls),
                    metadata={
                        "pattern_name": pattern.name,
                        "pattern_category": pattern.category,
                        "benefits": pattern.benefits,
                        "drawbacks": pattern.drawbacks,
                    },
                ))

        if cls.is_abstract or any("ABC" in base for base in cls.bases):
            knowledge.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title=f"{cls.name} 是抽象基类",
                description=f"{cls.name} 被设计为抽象基类，定义了子类必须实现的接口。",
                location=cls.full_name,
                evidence=[f"继承自: {', '.join(cls.bases)}"],
                confidence=0.9,
                priority=KnowledgePriority.MEDIUM,
                impact="定义了类型层次结构和契约",
                recommendation="确保所有抽象方法都有明确的文档说明",
            ))

        if len(cls.bases) > 1:
            knowledge.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title=f"{cls.name} 使用多重继承",
                description=f"{cls.name} 继承自多个基类: {', '.join(cls.bases)}",
                location=cls.full_name,
                evidence=[f"基类: {base}" for base in cls.bases],
                confidence=0.95,
                priority=KnowledgePriority.HIGH,
                impact="可能引入复杂性和菱形继承问题",
                recommendation="考虑使用组合代替多重继承，或使用 Mixin 模式",
            ))

        return knowledge

    def _extract_from_module(self, context: ExtractionContext) -> list[ImplicitKnowledge]:
        """从模块提取设计动机"""
        knowledge = []
        module = context.module_info

        factory_functions = [
            f for f in module.functions
            if any(kw in f.name.lower() for kw in ["create", "make", "build", "factory"])
        ]

        if factory_functions:
            knowledge.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title="模块级工厂函数",
                description=f"模块包含 {len(factory_functions)} 个工厂函数，用于封装对象创建逻辑。",
                location=module.name,
                evidence=[f"工厂函数: {f.name}" for f in factory_functions[:5]],
                confidence=0.8,
                priority=KnowledgePriority.MEDIUM,
                impact="封装创建逻辑，提高灵活性",
                recommendation="考虑是否需要将这些函数组织为工厂类",
            ))

        if len(module.classes) > 10:
            knowledge.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title="大型模块",
                description=f"模块包含 {len(module.classes)} 个类，可能需要拆分。",
                location=module.name,
                evidence=[f"类数量: {len(module.classes)}"],
                confidence=0.7,
                priority=KnowledgePriority.LOW,
                impact="可能影响代码可维护性",
                recommendation="考虑按职责拆分为多个模块",
            ))

        return knowledge

    def _extract_from_code(self, context: ExtractionContext) -> list[ImplicitKnowledge]:
        """从代码内容提取设计动机"""
        knowledge = []
        code = context.code_content

        todo_patterns = re.findall(r'#\s*(TODO|FIXME|HACK|XXX):?\s*(.+)', code, re.IGNORECASE)
        for marker, comment in todo_patterns:
            priority = KnowledgePriority.HIGH if marker.upper() in ("FIXME", "XXX") else KnowledgePriority.MEDIUM
            knowledge.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.TECH_DEBT,
                title=f"{marker} 标记: {comment[:50]}",
                description=f"代码中存在 {marker} 标记，表明需要后续处理。",
                location=context.project_path.name,
                evidence=[f"{marker}: {comment}"],
                confidence=0.95,
                priority=priority,
                impact="可能存在待解决的问题或优化点",
                recommendation="及时处理标记的问题",
            ))

        deprecated_patterns = re.findall(r'@deprecated|deprecated\s*[:=]', code, re.IGNORECASE)
        if deprecated_patterns:
            knowledge.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title="存在废弃的代码",
                description="代码中存在废弃标记，表明有即将移除的功能。",
                location=context.project_path.name,
                evidence=[f"发现 {len(deprecated_patterns)} 处废弃标记"],
                confidence=0.9,
                priority=KnowledgePriority.HIGH,
                impact="需要关注迁移路径",
                recommendation="更新文档，提供迁移指南",
            ))

        return knowledge

    def _detect_pattern_in_class(
        self,
        cls: ClassInfo,
        pattern: DesignPattern,
    ) -> Optional[dict[str, Any]]:
        """检测类是否使用了特定设计模式"""
        evidence = []
        match_count = 0

        class_name_lower = cls.name.lower()

        for indicator in pattern.indicators:
            if indicator.lower() in class_name_lower:
                evidence.append(f"类名包含 '{indicator}'")
                match_count += 1

        for method in cls.methods:
            method_name_lower = method.name.lower()
            for indicator in pattern.indicators:
                if indicator.lower() in method_name_lower:
                    evidence.append(f"方法 '{method.name}' 包含 '{indicator}'")
                    match_count += 0.5

        for prop in cls.properties:
            prop_name_lower = prop.name.lower()
            for indicator in pattern.indicators:
                if indicator.lower() in prop_name_lower:
                    evidence.append(f"属性 '{prop.name}' 包含 '{indicator}'")
                    match_count += 0.5

        for var in cls.class_variables:
            var_name_lower = var.name.lower()
            for indicator in pattern.indicators:
                if indicator.lower() in var_name_lower:
                    evidence.append(f"类变量 '{var.name}' 包含 '{indicator}'")
                    match_count += 1

        if match_count >= 1:
            return {
                "evidence": evidence[:5],
                "confidence": min(match_count / 3, 1.0),
            }

        return None

    def _generate_impact(self, pattern: DesignPattern) -> str:
        """生成影响描述"""
        benefits = ", ".join(pattern.benefits[:2])
        drawbacks = ", ".join(pattern.drawbacks[:1])
        return f"优点: {benefits}。潜在问题: {drawbacks}。"

    def _generate_recommendation(self, pattern: DesignPattern, cls: ClassInfo) -> str:
        """生成建议"""
        if pattern.category == "creational":
            return f"确保 {cls.name} 的创建逻辑符合单一职责原则。"
        elif pattern.category == "behavioral":
            return f"注意 {cls.name} 中观察者/策略的生命周期管理。"
        else:
            return f"保持 {cls.name} 的接口简洁，避免过度复杂化。"
