"""
隐性知识提取模块
从代码中提取设计决策、架构考量和技术债务等隐性知识
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pywiki.parsers.types import ModuleInfo, ClassInfo, FunctionInfo


class KnowledgeType(str, Enum):
    DESIGN_DECISION = "design_decision"
    ARCHITECTURE_PATTERN = "architecture_pattern"
    TECH_DEBT = "tech_debt"
    CODE_SMELL = "code_smell"
    BEST_PRACTICE = "best_practice"
    ANTI_PATTERN = "anti_pattern"
    TRADE_OFF = "trade_off"
    CONSTRAINT = "constraint"


class KnowledgePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ImplicitKnowledge:
    knowledge_type: KnowledgeType
    title: str
    description: str
    location: str
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    priority: KnowledgePriority = KnowledgePriority.MEDIUM
    impact: str = ""
    recommendation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "knowledge_type": self.knowledge_type.value,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "priority": self.priority.value,
            "impact": self.impact,
            "recommendation": self.recommendation,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ExtractionContext:
    project_path: Path
    module_info: Optional[ModuleInfo] = None
    class_info: Optional[ClassInfo] = None
    function_info: Optional[FunctionInfo] = None
    code_content: str = ""
    commit_messages: list[str] = field(default_factory=list)
    related_files: list[Path] = field(default_factory=list)


class BaseKnowledgeExtractor(ABC):
    """隐性知识提取器基类"""

    @property
    @abstractmethod
    def knowledge_type(self) -> KnowledgeType:
        pass

    @abstractmethod
    def extract(self, context: ExtractionContext) -> list[ImplicitKnowledge]:
        pass

    def _calculate_confidence(self, evidence_count: int, max_evidence: int = 5) -> float:
        """计算置信度"""
        return min(evidence_count / max_evidence, 1.0)


class ImplicitKnowledgeExtractor:
    """
    隐性知识提取器
    整合多种知识提取器，提供统一的提取接口
    """

    def __init__(self):
        from pywiki.knowledge.design_motivation import DesignMotivationExtractor
        from pywiki.knowledge.architecture_decision import ArchitectureDecisionExtractor
        from pywiki.knowledge.tech_debt_detector import TechDebtDetector

        self._extractors: list[BaseKnowledgeExtractor] = [
            DesignMotivationExtractor(),
            ArchitectureDecisionExtractor(),
            TechDebtDetector(),
        ]

        self._knowledge_cache: dict[str, list[ImplicitKnowledge]] = {}

    def add_extractor(self, extractor: BaseKnowledgeExtractor) -> None:
        """添加提取器"""
        self._extractors.append(extractor)

    def remove_extractor(self, knowledge_type: KnowledgeType) -> bool:
        """移除提取器"""
        for i, extractor in enumerate(self._extractors):
            if extractor.knowledge_type == knowledge_type:
                self._extractors.pop(i)
                return True
        return False

    def extract_from_module(
        self,
        project_path: Path,
        module: ModuleInfo,
        code_content: str = "",
        commit_messages: Optional[list[str]] = None,
    ) -> list[ImplicitKnowledge]:
        """
        从模块提取隐性知识

        Args:
            project_path: 项目路径
            module: 模块信息
            code_content: 代码内容
            commit_messages: 提交消息列表

        Returns:
            隐性知识列表
        """
        context = ExtractionContext(
            project_path=project_path,
            module_info=module,
            code_content=code_content,
            commit_messages=commit_messages or [],
        )

        all_knowledge = []

        for extractor in self._extractors:
            try:
                knowledge = extractor.extract(context)
                all_knowledge.extend(knowledge)
            except Exception:
                continue

        for cls in module.classes:
            class_knowledge = self.extract_from_class(
                project_path, cls, module, code_content
            )
            all_knowledge.extend(class_knowledge)

        return all_knowledge

    def extract_from_class(
        self,
        project_path: Path,
        cls: ClassInfo,
        module: Optional[ModuleInfo] = None,
        code_content: str = "",
    ) -> list[ImplicitKnowledge]:
        """从类提取隐性知识"""
        context = ExtractionContext(
            project_path=project_path,
            module_info=module,
            class_info=cls,
            code_content=code_content,
        )

        all_knowledge = []

        for extractor in self._extractors:
            try:
                knowledge = extractor.extract(context)
                all_knowledge.extend(knowledge)
            except Exception:
                continue

        return all_knowledge

    def extract_from_code(
        self,
        project_path: Path,
        code_content: str,
        file_path: Optional[Path] = None,
    ) -> list[ImplicitKnowledge]:
        """
        从代码内容提取隐性知识

        Args:
            project_path: 项目路径
            code_content: 代码内容
            file_path: 文件路径

        Returns:
            隐性知识列表
        """
        context = ExtractionContext(
            project_path=project_path,
            code_content=code_content,
        )

        all_knowledge = []

        for extractor in self._extractors:
            try:
                knowledge = extractor.extract(context)
                all_knowledge.extend(knowledge)
            except Exception:
                continue

        return all_knowledge

    def get_knowledge_by_type(
        self,
        knowledge_list: list[ImplicitKnowledge],
        knowledge_type: KnowledgeType,
    ) -> list[ImplicitKnowledge]:
        """按类型筛选知识"""
        return [k for k in knowledge_list if k.knowledge_type == knowledge_type]

    def get_knowledge_by_priority(
        self,
        knowledge_list: list[ImplicitKnowledge],
        min_priority: KnowledgePriority = KnowledgePriority.MEDIUM,
    ) -> list[ImplicitKnowledge]:
        """按优先级筛选知识"""
        priority_order = {
            KnowledgePriority.LOW: 0,
            KnowledgePriority.MEDIUM: 1,
            KnowledgePriority.HIGH: 2,
            KnowledgePriority.CRITICAL: 3,
        }
        min_level = priority_order[min_priority]
        return [
            k for k in knowledge_list
            if priority_order[k.priority] >= min_level
        ]

    def get_high_confidence_knowledge(
        self,
        knowledge_list: list[ImplicitKnowledge],
        min_confidence: float = 0.7,
    ) -> list[ImplicitKnowledge]:
        """获取高置信度知识"""
        return [k for k in knowledge_list if k.confidence >= min_confidence]

    def generate_report(
        self,
        knowledge_list: list[ImplicitKnowledge],
    ) -> dict[str, Any]:
        """
        生成知识报告

        Args:
            knowledge_list: 隐性知识列表

        Returns:
            报告字典
        """
        by_type: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        high_confidence_count = 0

        for k in knowledge_list:
            type_key = k.knowledge_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

            priority_key = k.priority.value
            by_priority[priority_key] = by_priority.get(priority_key, 0) + 1

            if k.confidence >= 0.7:
                high_confidence_count += 1

        return {
            "total_knowledge": len(knowledge_list),
            "by_type": by_type,
            "by_priority": by_priority,
            "high_confidence_count": high_confidence_count,
            "knowledge": [k.to_dict() for k in knowledge_list],
        }

    def clear_cache(self) -> None:
        """清空缓存"""
        self._knowledge_cache.clear()
