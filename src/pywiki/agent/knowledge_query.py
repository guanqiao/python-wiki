"""
知识查询接口
提供统一的知识查询接口
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pywiki.wiki.storage import WikiStorage
from pywiki.knowledge.vector_store import VectorStore
from pywiki.knowledge.search import KnowledgeSearcher
from pywiki.memory.memory_manager import MemoryManager


class QueryType(str, Enum):
    CODE = "code"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"
    BUSINESS_LOGIC = "business_logic"
    DEPENDENCY = "dependency"
    ALL = "all"


@dataclass
class QueryResult:
    query: str
    query_type: QueryType
    results: list[dict] = field(default_factory=list)
    summary: str = ""
    confidence: float = 0.0
    sources: list[str] = field(default_factory=list)
    follow_up_questions: list[str] = field(default_factory=list)


class KnowledgeQuery:
    """知识查询接口"""

    def __init__(
        self,
        wiki_storage: Optional[WikiStorage] = None,
        vector_store: Optional[VectorStore] = None,
        memory_manager: Optional[MemoryManager] = None,
    ):
        self.wiki_storage = wiki_storage
        self.vector_store = vector_store
        self.memory_manager = memory_manager

        if vector_store:
            self.knowledge_searcher = KnowledgeSearcher(vector_store)
        else:
            self.knowledge_searcher = None

    def query(
        self,
        question: str,
        query_type: QueryType = QueryType.ALL,
        top_k: int = 10,
    ) -> QueryResult:
        """执行知识查询"""
        results = []

        if self.wiki_storage:
            wiki_results = self._search_wiki(question, query_type, top_k)
            results.extend(wiki_results)

        if self.vector_store:
            vector_results = self._search_vector(question, query_type, top_k)
            results.extend(vector_results)

        if self.memory_manager:
            memory_results = self._search_memory(question, top_k)
            results.extend(memory_results)

        results = self._rank_results(results, question)
        results = results[:top_k]

        summary = self._generate_summary(results)
        confidence = self._calculate_confidence(results)
        sources = self._extract_sources(results)
        follow_up = self._generate_follow_up_questions(question, results)

        return QueryResult(
            query=question,
            query_type=query_type,
            results=results,
            summary=summary,
            confidence=confidence,
            sources=sources,
            follow_up_questions=follow_up,
        )

    def _search_wiki(
        self,
        question: str,
        query_type: QueryType,
        top_k: int,
    ) -> list[dict]:
        """搜索 Wiki 文档"""
        if not self.wiki_storage:
            return []

        results = []
        wiki_results = self.wiki_storage.search(question)

        for result in wiki_results[:top_k]:
            for match in result.get("matches", []):
                results.append({
                    "content": match.get("context", ""),
                    "source": result.get("path", ""),
                    "type": "wiki",
                    "line": match.get("line", 0),
                })

        return results

    def _search_vector(
        self,
        question: str,
        query_type: QueryType,
        top_k: int,
    ) -> list[dict]:
        """搜索向量存储"""
        if not self.vector_store:
            return []

        filter_dict = None
        if query_type != QueryType.ALL:
            filter_dict = {"type": query_type.value}

        results = self.vector_store.search(question, k=top_k, filter=filter_dict)

        return [
            {
                "content": r.get("content", ""),
                "source": r.get("metadata", {}).get("source", ""),
                "type": "vector",
                "metadata": r.get("metadata", {}),
            }
            for r in results
        ]

    def _search_memory(self, question: str, top_k: int) -> list[dict]:
        """搜索记忆"""
        if not self.memory_manager:
            return []

        results = []
        memory_results = self.memory_manager.search(question)

        for entry in memory_results[:top_k]:
            results.append({
                "content": f"{entry.key}: {entry.value}",
                "source": f"memory:{entry.scope.value}",
                "type": "memory",
                "category": entry.category.value,
            })

        return results

    def _rank_results(self, results: list[dict], question: str) -> list[dict]:
        """对结果排序"""
        question_lower = question.lower()
        question_words = set(question_lower.split())

        def score_result(result: dict) -> float:
            content = result.get("content", "").lower()
            score = 0.0

            for word in question_words:
                if word in content:
                    score += 1.0

            if question_lower in content:
                score += 5.0

            result_type = result.get("type", "")
            if result_type == "wiki":
                score += 2.0
            elif result_type == "memory":
                score += 1.5

            return score

        return sorted(results, key=score_result, reverse=True)

    def _generate_summary(self, results: list[dict]) -> str:
        """生成摘要"""
        if not results:
            return "未找到相关信息"

        if len(results) == 1:
            return f"找到 1 个相关结果"

        return f"找到 {len(results)} 个相关结果"

    def _calculate_confidence(self, results: list[dict]) -> float:
        """计算置信度"""
        if not results:
            return 0.0

        return min(len(results) / 5.0, 1.0)

    def _extract_sources(self, results: list[dict]) -> list[str]:
        """提取来源"""
        sources = []

        for result in results:
            source = result.get("source", "")
            if source and source not in sources:
                sources.append(source)

        return sources[:10]

    def _generate_follow_up_questions(
        self,
        question: str,
        results: list[dict],
    ) -> list[str]:
        """生成后续问题"""
        follow_up = []

        if not results:
            follow_up.append("您是否需要更具体的搜索条件？")
            return follow_up

        if "how" in question.lower():
            follow_up.append("您是否想了解实现细节？")
        elif "what" in question.lower():
            follow_up.append("您是否想了解具体的使用方式？")
        elif "why" in question.lower():
            follow_up.append("您是否想了解替代方案？")

        if len(results) > 3:
            follow_up.append("您是否需要更精确的结果？")

        return follow_up[:3]

    def get_code_context(self, symbol: str) -> Optional[dict]:
        """获取代码上下文"""
        result = self.query(f"symbol:{symbol}", QueryType.CODE, top_k=5)

        if result.results:
            return {
                "symbol": symbol,
                "context": result.results[0].get("content", ""),
                "source": result.results[0].get("source", ""),
            }

        return None

    def get_architecture_overview(self) -> dict:
        """获取架构概览"""
        result = self.query("architecture overview", QueryType.ARCHITECTURE, top_k=10)

        return {
            "summary": result.summary,
            "components": [r.get("content", "")[:200] for r in result.results[:5]],
            "sources": result.sources,
        }

    def get_dependencies(self, module: str) -> dict:
        """获取依赖关系"""
        result = self.query(f"dependencies of {module}", QueryType.DEPENDENCY, top_k=10)

        return {
            "module": module,
            "dependencies": result.results,
            "sources": result.sources,
        }
