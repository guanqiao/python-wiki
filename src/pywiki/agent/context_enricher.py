"""
上下文增强器
为 Agent 提供丰富的上下文信息
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from pywiki.memory.memory_manager import MemoryManager
from pywiki.insights.tech_stack_analyzer import TechStackAnalyzer, TechStackAnalysis
from pywiki.knowledge.implicit_knowledge import ImplicitKnowledgeExtractor


@dataclass
class EnrichedContext:
    query: str
    project_context: dict = field(default_factory=dict)
    memory_context: dict = field(default_factory=dict)
    tech_stack_context: dict = field(default_factory=dict)
    knowledge_context: dict = field(default_factory=dict)
    relevant_files: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class ContextEnricher:
    """上下文增强器"""

    def __init__(
        self,
        project_path: Path,
        memory_manager: Optional[MemoryManager] = None,
    ):
        self.project_path = project_path
        self.memory_manager = memory_manager

        self._tech_analyzer = TechStackAnalyzer()
        self._knowledge_extractor = ImplicitKnowledgeExtractor()
        self._tech_stack: Optional[TechStackAnalysis] = None

    def enrich(self, query: str, max_tokens: int = 4000) -> EnrichedContext:
        """增强上下文"""
        context = EnrichedContext(query=query)

        context.project_context = self._get_project_context()

        if self.memory_manager:
            context.memory_context = self.memory_manager.get_all_context()

        context.tech_stack_context = self._get_tech_stack_context()

        context.knowledge_context = self._get_knowledge_context(query)

        context.relevant_files = self._find_relevant_files(query)

        context.suggestions = self._generate_suggestions(query, context)

        return context

    def _get_project_context(self) -> dict:
        """获取项目上下文"""
        return {
            "project_path": str(self.project_path),
            "project_name": self.project_path.name,
        }

    def _get_tech_stack_context(self) -> dict:
        """获取技术栈上下文"""
        if self._tech_stack is None:
            self._tech_stack = self._tech_analyzer.analyze_project(self.project_path)

        return {
            "frameworks": [f.name for f in self._tech_stack.frameworks],
            "databases": [d.name for d in self._tech_stack.databases],
            "libraries": [l.name for l in self._tech_stack.libraries[:10]],
            "summary": self._tech_stack.summary,
        }

    def _get_knowledge_context(self, query: str) -> dict:
        """获取知识上下文"""
        return {
            "implicit_knowledge": [],
            "design_decisions": [],
        }

    def _find_relevant_files(self, query: str) -> list[str]:
        """查找相关文件"""
        relevant = []
        query_lower = query.lower()

        keywords = self._extract_keywords(query)

        for py_file in self.project_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8").lower()
                match_count = sum(1 for kw in keywords if kw in content)

                if match_count > 0:
                    relevant.append((str(py_file.relative_to(self.project_path)), match_count))
            except Exception:
                continue

        relevant.sort(key=lambda x: x[1], reverse=True)
        return [f[0] for f in relevant[:10]]

    def _extract_keywords(self, query: str) -> list[str]:
        """提取关键词"""
        import re

        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "shall", "can", "need", "dare", "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by", "from", "as", "into", "through", "during", "before", "after", "above", "below", "between", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "just", "and", "but", "if", "or", "because", "until", "while", "this", "that", "these", "those", "what", "which", "who", "whom"}

        words = re.findall(r"\b\w+\b", query.lower())
        return [w for w in words if w not in stop_words and len(w) > 2]

    def _generate_suggestions(self, query: str, context: EnrichedContext) -> list[str]:
        """生成建议"""
        suggestions = []

        if context.relevant_files:
            suggestions.append(f"建议查看文件: {context.relevant_files[0]}")

        if context.tech_stack_context.get("frameworks"):
            frameworks = context.tech_stack_context["frameworks"]
            suggestions.append(f"项目使用框架: {', '.join(frameworks)}")

        if context.memory_context.get("project"):
            suggestions.append("已有项目相关的记忆信息可供参考")

        return suggestions

    def get_context_summary(self, context: EnrichedContext) -> str:
        """获取上下文摘要"""
        parts = []

        parts.append(f"项目: {context.project_context.get('project_name', 'Unknown')}")

        if context.tech_stack_context.get("frameworks"):
            parts.append(f"框架: {', '.join(context.tech_stack_context['frameworks'])}")

        if context.relevant_files:
            parts.append(f"相关文件: {len(context.relevant_files)} 个")

        if context.memory_context.get("project"):
            parts.append("记忆: 已加载项目记忆")

        return " | ".join(parts)

    def format_for_prompt(self, context: EnrichedContext, max_length: int = 2000) -> str:
        """格式化为 Prompt"""
        lines = []

        lines.append("## 项目上下文")
        lines.append(f"项目路径: {context.project_context.get('project_path', '')}")
        lines.append("")

        if context.tech_stack_context.get("frameworks"):
            lines.append("## 技术栈")
            lines.append(f"框架: {', '.join(context.tech_stack_context['frameworks'])}")
            if context.tech_stack_context.get("databases"):
                lines.append(f"数据库: {', '.join(context.tech_stack_context['databases'])}")
            lines.append("")

        if context.memory_context.get("global") or context.memory_context.get("project"):
            lines.append("## 记忆信息")
            if context.memory_context.get("global"):
                lines.append("全局偏好:")
                for key, value in list(context.memory_context["global"].items())[:5]:
                    lines.append(f"  - {key}: {value}")
            if context.memory_context.get("project"):
                lines.append("项目记忆:")
                for key, value in list(context.memory_context["project"].items())[:5]:
                    lines.append(f"  - {key}: {value}")
            lines.append("")

        if context.relevant_files:
            lines.append("## 相关文件")
            for f in context.relevant_files[:5]:
                lines.append(f"  - {f}")
            lines.append("")

        result = "\n".join(lines)
        if len(result) > max_length:
            result = result[:max_length] + "\n... (已截断)"

        return result
