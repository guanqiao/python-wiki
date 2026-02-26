"""
搜索引擎测试
"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pywiki.search.engine import (
    SearchEngine,
    SearchQuery,
    SearchMode,
    SearchResult,
    IndexLevel,
)
from pywiki.search.cache import SearchCache, MultiLevelCache
from pywiki.search.hybrid_search import BM25Index, HybridSearch


@pytest.fixture
def search_engine(tmp_path: Path) -> SearchEngine:
    return SearchEngine(
        persist_dir=tmp_path / "search_index",
        openai_api_key="test-key",
        openai_api_base="https://api.openai.com/v1",
    )


@pytest.fixture
def search_cache() -> SearchCache:
    return SearchCache(max_size=100, ttl_seconds=3600)


class TestSearchQuery:
    """SearchQuery 测试"""

    def test_create_query(self):
        query = SearchQuery(
            query="test query",
            mode=SearchMode.HYBRID,
            top_k=10,
        )

        assert query.query == "test query"
        assert query.mode == SearchMode.HYBRID
        assert query.top_k == 10

    def test_to_dict(self):
        query = SearchQuery(
            query="test",
            mode=SearchMode.SEMANTIC,
            top_k=5,
            project_name="test_project",
        )

        result = query.to_dict()

        assert result["query"] == "test"
        assert result["mode"] == "semantic"
        assert result["project_name"] == "test_project"


class TestSearchResult:
    """SearchResult 测试"""

    def test_create_result(self):
        result = SearchResult(
            content="Test content",
            score=0.95,
            source="test.py",
            level=IndexLevel.FILE,
        )

        assert result.content == "Test content"
        assert result.score == 0.95
        assert result.level == IndexLevel.FILE

    def test_to_dict(self):
        result = SearchResult(
            content="Test",
            score=0.8,
            source="test.py",
            level=IndexLevel.MODULE,
            metadata={"key": "value"},
        )

        data = result.to_dict()

        assert data["content"] == "Test"
        assert data["score"] == 0.8
        assert data["level"] == "module"


class TestSearchCache:
    """SearchCache 测试"""

    def test_set_and_get(self, search_cache: SearchCache):
        key = "test_key"
        results = [
            SearchResult(
                content="Result 1",
                score=0.9,
                source="test.py",
                level=IndexLevel.FILE,
            )
        ]

        search_cache.set(key, results)
        retrieved = search_cache.get(key)

        assert retrieved is not None
        assert len(retrieved) == 1
        assert retrieved[0].content == "Result 1"

    def test_cache_miss(self, search_cache: SearchCache):
        result = search_cache.get("nonexistent_key")
        assert result is None

    def test_cache_stats(self, search_cache: SearchCache):
        key = "test"
        results = [SearchResult(
            content="Test",
            score=1.0,
            source="test.py",
            level=IndexLevel.FILE,
        )]

        search_cache.set(key, results)
        search_cache.get(key)
        search_cache.get("miss")

        stats = search_cache.get_stats()

        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1

    def test_cache_clear(self, search_cache: SearchCache):
        search_cache.set("key", [])
        search_cache.clear()

        assert len(search_cache) == 0


class TestMultiLevelCache:
    """MultiLevelCache 测试"""

    def test_l1_cache_hit(self):
        cache = MultiLevelCache(l1_size=10, l2_size=100)
        results = [SearchResult(
            content="Test",
            score=1.0,
            source="test.py",
            level=IndexLevel.FILE,
        )]

        cache.set("key", results)
        retrieved = cache.get("key")

        assert retrieved is not None

    def test_l2_cache_fallback(self):
        cache = MultiLevelCache(l1_size=1, l2_size=10)
        results = [SearchResult(
            content="Test",
            score=1.0,
            source="test.py",
            level=IndexLevel.FILE,
        )]

        cache.set("key1", results)
        cache.set("key2", results)

        assert cache.get("key1") is not None
        assert cache.get("key2") is not None


class TestBM25Index:
    """BM25Index 测试"""

    def test_add_document(self):
        index = BM25Index()
        index.add_document("doc1", "This is a test document", {"source": "test.py"})

        assert index._doc_count == 1

    def test_search(self):
        index = BM25Index()
        index.add_document("doc1", "Python is a programming language", {})
        index.add_document("doc2", "JavaScript is also a programming language", {})
        index.add_document("doc3", "The weather is nice today", {})

        results = index.search("programming language", top_k=2)

        assert len(results) == 2
        assert results[0][0] in ("doc1", "doc2")

    def test_remove_document(self):
        index = BM25Index()
        index.add_document("doc1", "Test content", {})

        success = index.remove_document("doc1")

        assert success
        assert index._doc_count == 0

    def test_clear(self):
        index = BM25Index()
        index.add_document("doc1", "Test", {})
        index.add_document("doc2", "Test", {})

        index.clear()

        assert index._doc_count == 0


class TestSearchEngine:
    """SearchEngine 测试"""

    def test_init(self, search_engine: SearchEngine):
        assert search_engine.persist_dir.exists()

    @pytest.mark.asyncio
    async def test_search_empty(self, search_engine: SearchEngine):
        query = SearchQuery(
            query="test",
            mode=SearchMode.KEYWORD,
            top_k=10,
        )

        results = await search_engine.search(query)

        assert isinstance(results, list)

    def test_get_stats(self, search_engine: SearchEngine):
        stats = search_engine.get_stats()

        assert "total_queries" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats

    @pytest.mark.asyncio
    async def test_clear(self, search_engine: SearchEngine):
        await search_engine.clear()

        assert search_engine.get_stats()["total_queries"] == 0
