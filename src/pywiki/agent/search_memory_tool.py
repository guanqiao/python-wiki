"""
Search Memory 工具
Agent 可通过此工具查询 Wiki 知识库
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from pywiki.knowledge.vector_store import VectorStore
from pywiki.knowledge.search import KnowledgeSearcher
from pywiki.wiki.storage import WikiStorage


@dataclass
class SearchMemoryResult:
    query: str
    results: list[dict] = field(default_factory=list)
    context: str = ""
    sources: list[str] = field(default_factory=list)
    confidence: float = 0.0


class SearchMemoryTool:
    """Search Memory 工具 - Agent 可通过此工具查询 Wiki 知识库"""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        wiki_storage: Optional[WikiStorage] = None,
        knowledge_searcher: Optional[KnowledgeSearcher] = None,
    ):
        self.vector_store = vector_store
        self.wiki_storage = wiki_storage
        self.knowledge_searcher = knowledge_searcher

    def search(
        self,
        query: str,
        top_k: int = 5,
        search_type: str = "hybrid",
    ) -> SearchMemoryResult:
        """搜索知识库"""
        results = []

        if search_type in ("semantic", "hybrid") and self.vector_store:
            semantic_results = self.vector_store.search(query, k=top_k)
            results.extend(semantic_results)

        if search_type in ("keyword", "hybrid") and self.wiki_storage:
            keyword_results = self.wiki_storage.search(query)
            for result in keyword_results[:top_k]:
                results.append({
                    "content": result.get("matches", [{}])[0].get("context", "") if result.get("matches") else "",
                    "metadata": {"source": result.get("path", ""), "type": "wiki"},
                })

        if search_type == "hybrid":
            results = self._deduplicate_results(results)

        context = self._build_context(results)
        sources = self._extract_sources(results)
        confidence = self._calculate_confidence(results)

        return SearchMemoryResult(
            query=query,
            results=results[:top_k],
            context=context,
            sources=sources,
            confidence=confidence,
        )

    def _deduplicate_results(self, results: list[dict]) -> list[dict]:
        """去重结果"""
        seen = set()
        unique = []

        for result in results:
            content = result.get("content", "")
            content_hash = hash(content[:100])
            if content_hash not in seen:
                seen.add(content_hash)
                unique.append(result)

        return unique

    def _build_context(self, results: list[dict]) -> str:
        """构建上下文"""
        contexts = []

        for i, result in enumerate(results[:5], 1):
            content = result.get("content", "")
            source = result.get("metadata", {}).get("source", "unknown")

            contexts.append(f"[{i}] 来源: {source}\n{content[:500]}")

        return "\n\n".join(contexts)

    def _extract_sources(self, results: list[dict]) -> list[str]:
        """提取来源"""
        sources = []

        for result in results:
            metadata = result.get("metadata", {})
            source = metadata.get("source", "")
            if source and source not in sources:
                sources.append(source)

        return sources

    def _calculate_confidence(self, results: list[dict]) -> float:
        """计算置信度"""
        if not results:
            return 0.0

        scores = []
        for result in results:
            if "score" in result:
                scores.append(result["score"])

        if scores:
            return sum(scores) / len(scores)

        return 0.5 if results else 0.0

    def ask(
        self,
        question: str,
        context_limit: int = 3000,
    ) -> str:
        """基于知识库回答问题"""
        result = self.search(question, top_k=5)

        if not result.results:
            return "抱歉，在知识库中没有找到相关信息。"

        context = result.context[:context_limit]

        return f"""基于知识库找到以下相关信息：

{context}

来源: {', '.join(result.sources) if result.sources else '知识库'}
置信度: {result.confidence:.2f}
"""

    def get_tool_definition(self) -> dict:
        """获取工具定义（用于 Agent 集成）"""
        return {
            "name": "search_memory",
            "description": "搜索 Wiki 知识库，查找代码、文档、架构等相关信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询，可以是代码符号、功能描述或问题",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回结果数量",
                        "default": 5,
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["semantic", "keyword", "hybrid"],
                        "description": "搜索类型",
                        "default": "hybrid",
                    },
                },
                "required": ["query"],
            },
        }

    def execute(self, parameters: dict) -> dict:
        """执行工具调用"""
        query = parameters.get("query", "")
        top_k = parameters.get("top_k", 5)
        search_type = parameters.get("search_type", "hybrid")

        result = self.search(query, top_k, search_type)

        return {
            "query": result.query,
            "results": result.results,
            "context": result.context,
            "sources": result.sources,
            "confidence": result.confidence,
        }
