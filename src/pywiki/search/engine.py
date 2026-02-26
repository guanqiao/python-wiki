"""
统一搜索引擎接口
支持语义检索、关键词检索和混合检索
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union


class SearchMode(str, Enum):
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class IndexLevel(str, Enum):
    PROJECT = "project"
    MODULE = "module"
    FILE = "file"


@dataclass
class SearchResult:
    content: str
    score: float
    source: str
    level: IndexLevel
    metadata: dict[str, Any] = field(default_factory=dict)
    highlights: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "score": self.score,
            "source": self.source,
            "level": self.level.value,
            "metadata": self.metadata,
            "highlights": self.highlights,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SearchQuery:
    query: str
    mode: SearchMode = SearchMode.HYBRID
    top_k: int = 10
    filters: dict[str, Any] = field(default_factory=dict)
    level: Optional[IndexLevel] = None
    project_name: Optional[str] = None
    module_name: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "mode": self.mode.value,
            "top_k": self.top_k,
            "filters": self.filters,
            "level": self.level.value if self.level else None,
            "project_name": self.project_name,
            "module_name": self.module_name,
        }


class BaseIndexer(ABC):
    @abstractmethod
    async def index(self, documents: list[dict[str, Any]]) -> int:
        pass

    @abstractmethod
    async def remove(self, doc_ids: list[str]) -> bool:
        pass

    @abstractmethod
    async def update(self, doc_id: str, document: dict[str, Any]) -> bool:
        pass


class BaseSearcher(ABC):
    @abstractmethod
    async def search(self, query: SearchQuery) -> list[SearchResult]:
        pass

    @abstractmethod
    async def search_batch(self, queries: list[SearchQuery]) -> list[list[SearchResult]]:
        pass


class SearchEngine(BaseSearcher):
    """
    统一搜索引擎
    整合语义检索、关键词检索和混合检索
    """

    def __init__(
        self,
        persist_dir: Path,
        openai_api_key: Optional[str] = None,
        openai_api_base: Optional[str] = None,
        embedding_model: str = "text-embedding-ada-002",
        cache_size: int = 1000,
    ):
        from pywiki.search.tiered_index import TieredIndex
        from pywiki.search.hybrid_search import HybridSearch
        from pywiki.search.cache import SearchCache

        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self._tiered_index = TieredIndex(
            persist_dir=self.persist_dir / "tiered",
            openai_api_key=openai_api_key,
            openai_api_base=openai_api_base,
            embedding_model=embedding_model,
        )

        self._hybrid_search = HybridSearch(
            persist_dir=self.persist_dir / "hybrid",
            openai_api_key=openai_api_key,
            openai_api_base=openai_api_base,
            embedding_model=embedding_model,
        )

        self._cache = SearchCache(max_size=cache_size)

        self._stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_latency_ms": 0.0,
        }

    async def index_project(
        self,
        project_path: Path,
        project_name: str,
        documents: list[dict[str, Any]],
    ) -> int:
        """
        索引项目文档

        Args:
            project_path: 项目路径
            project_name: 项目名称
            documents: 文档列表，每个文档包含 content, metadata, level 等字段

        Returns:
            索引的文档数量
        """
        indexed_count = await self._tiered_index.index_project(
            project_path, project_name, documents
        )
        await self._hybrid_search.index_documents(documents)
        return indexed_count

    async def index_module(
        self,
        project_name: str,
        module_name: str,
        documents: list[dict[str, Any]],
    ) -> int:
        """索引模块文档"""
        indexed_count = await self._tiered_index.index_module(
            project_name, module_name, documents
        )
        await self._hybrid_search.index_documents(documents)
        return indexed_count

    async def index_file(
        self,
        project_name: str,
        module_name: str,
        file_path: Path,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """索引单个文件"""
        doc_id = await self._tiered_index.index_file(
            project_name, module_name, file_path, content, metadata
        )
        await self._hybrid_search.index_documents([{
            "id": doc_id,
            "content": content,
            "metadata": metadata or {},
        }])
        return doc_id

    async def remove_project(self, project_name: str) -> bool:
        """移除项目索引"""
        await self._tiered_index.remove_project(project_name)
        await self._hybrid_search.clear()
        return True

    async def search(self, query: SearchQuery) -> list[SearchResult]:
        """
        执行搜索

        Args:
            query: 搜索查询对象

        Returns:
            搜索结果列表
        """
        import time

        start_time = time.time()
        self._stats["total_queries"] += 1

        cache_key = self._generate_cache_key(query)
        cached_result = self._cache.get(cache_key)
        if cached_result is not None:
            self._stats["cache_hits"] += 1
            return cached_result

        self._stats["cache_misses"] += 1

        if query.mode == SearchMode.HYBRID:
            results = await self._hybrid_search.search(query)
        elif query.mode == SearchMode.SEMANTIC:
            results = await self._semantic_search(query)
        else:
            results = await self._keyword_search(query)

        if query.level:
            results = [r for r in results if r.level == query.level]

        if query.project_name:
            results = [
                r for r in results
                if r.metadata.get("project_name") == query.project_name
            ]

        if query.module_name:
            results = [
                r for r in results
                if r.metadata.get("module_name") == query.module_name
            ]

        results = results[:query.top_k]

        self._cache.set(cache_key, results)

        latency_ms = (time.time() - start_time) * 1000
        self._update_latency_stats(latency_ms)

        return results

    async def search_batch(self, queries: list[SearchQuery]) -> list[list[SearchResult]]:
        """批量搜索"""
        tasks = [self.search(q) for q in queries]
        return await asyncio.gather(*tasks)

    async def _semantic_search(self, query: SearchQuery) -> list[SearchResult]:
        """语义检索"""
        return await self._tiered_index.semantic_search(
            query.query, top_k=query.top_k * 2
        )

    async def _keyword_search(self, query: SearchQuery) -> list[SearchResult]:
        """关键词检索"""
        return await self._tiered_index.keyword_search(
            query.query, top_k=query.top_k * 2
        )

    def _generate_cache_key(self, query: SearchQuery) -> str:
        """生成缓存键"""
        import hashlib

        key_data = f"{query.query}:{query.mode.value}:{query.top_k}"
        if query.level:
            key_data += f":{query.level.value}"
        if query.project_name:
            key_data += f":{query.project_name}"
        if query.module_name:
            key_data += f":{query.module_name}"

        return hashlib.md5(key_data.encode()).hexdigest()

    def _update_latency_stats(self, latency_ms: float) -> None:
        """更新延迟统计"""
        total = self._stats["total_queries"]
        current_avg = self._stats["avg_latency_ms"]
        self._stats["avg_latency_ms"] = (
            (current_avg * (total - 1) + latency_ms) / total
        )

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "cache_hit_rate": (
                self._stats["cache_hits"] / max(self._stats["total_queries"], 1)
            ),
            "cache_size": len(self._cache),
        }

    async def optimize(self) -> None:
        """优化索引"""
        await self._tiered_index.optimize()
        self._cache.clear()

    async def clear(self) -> None:
        """清空索引"""
        await self._tiered_index.clear()
        await self._hybrid_search.clear()
        self._cache.clear()
