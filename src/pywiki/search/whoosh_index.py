"""
Whoosh 全文索引
本地全文搜索引擎
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from whoosh import index
from whoosh.analysis import StemmingAnalyzer, SimpleAnalyzer
from whoosh.fields import ID, TEXT, KEYWORD, NUMERIC, DATETIME, Schema
from whoosh.qparser import QueryParser, MultifieldParser, OrGroup
from whoosh.query import Every, Term
from whoosh.searching import Results
from whoosh.writing import AsyncWriter


@dataclass
class SearchResult:
    doc_id: str
    title: str
    content: str
    score: float
    file_path: str
    doc_type: str
    highlights: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "content": self.content,
            "score": self.score,
            "file_path": self.file_path,
            "doc_type": self.doc_type,
            "highlights": self.highlights,
            "metadata": self.metadata,
        }


class WhooshIndex:
    """
    Whoosh 全文索引
    提供本地全文搜索能力
    """

    DEFAULT_SCHEMA = Schema(
        doc_id=ID(stored=True, unique=True),
        title=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        content=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        file_path=ID(stored=True),
        doc_type=KEYWORD(stored=True),
        language=KEYWORD(stored=True),
        tags=KEYWORD(stored=True),
        importance=NUMERIC(stored=True, numtype=float),
        created_at=DATETIME(stored=True),
        updated_at=DATETIME(stored=True),
    )

    def __init__(
        self,
        index_dir: Path,
        schema: Optional[Schema] = None,
        language: str = "en",
    ):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self.schema = schema or self.DEFAULT_SCHEMA
        self.language = language

        self._index: Optional[index.Index] = None
        self._initialize_index()

    def _initialize_index(self) -> None:
        """初始化索引"""
        if index.exists_in(str(self.index_dir)):
            self._index = index.open_dir(str(self.index_dir))
        else:
            self._index = index.create_in(str(self.index_dir), self.schema)

    @property
    def ix(self) -> index.Index:
        """获取索引实例"""
        if self._index is None:
            self._initialize_index()
        return self._index

    def add_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        file_path: str = "",
        doc_type: str = "document",
        tags: Optional[list[str]] = None,
        importance: float = 0.5,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        添加文档到索引

        Args:
            doc_id: 文档ID
            title: 标题
            content: 内容
            file_path: 文件路径
            doc_type: 文档类型
            tags: 标签列表
            importance: 重要性
            metadata: 元数据
        """
        now = datetime.now()

        writer = self.ix.writer()
        try:
            writer.update_document(
                doc_id=doc_id,
                title=title,
                content=content,
                file_path=file_path,
                doc_type=doc_type,
                language=self.language,
                tags=",".join(tags or []),
                importance=importance,
                created_at=now,
                updated_at=now,
            )
            writer.commit()
        except Exception:
            writer.cancel()
            raise

    def add_documents_batch(
        self,
        documents: list[dict[str, Any]],
    ) -> int:
        """
        批量添加文档

        Args:
            documents: 文档列表

        Returns:
            成功添加的文档数量
        """
        count = 0
        writer = AsyncWriter(self.ix)

        try:
            for doc in documents:
                now = datetime.now()

                writer.update_document(
                    doc_id=doc.get("doc_id", ""),
                    title=doc.get("title", ""),
                    content=doc.get("content", ""),
                    file_path=doc.get("file_path", ""),
                    doc_type=doc.get("doc_type", "document"),
                    language=self.language,
                    tags=",".join(doc.get("tags", [])),
                    importance=doc.get("importance", 0.5),
                    created_at=now,
                    updated_at=now,
                )
                count += 1

            writer.commit()
        except Exception:
            writer.cancel()
            raise

        return count

    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        writer = self.ix.writer()
        try:
            writer.delete_by_term("doc_id", doc_id)
            writer.commit()
            return True
        except Exception:
            writer.cancel()
            return False

    def search(
        self,
        query: str,
        fields: Optional[list[str]] = None,
        limit: int = 10,
        doc_type: Optional[str] = None,
        min_importance: float = 0.0,
    ) -> list[SearchResult]:
        """
        搜索文档

        Args:
            query: 查询字符串
            fields: 搜索字段列表
            limit: 返回结果数量
            doc_type: 文档类型过滤
            min_importance: 最小重要性

        Returns:
            搜索结果列表
        """
        with self.ix.searcher() as searcher:
            if fields:
                parser = MultifieldParser(fields, self.schema, group=OrGroup)
            else:
                parser = QueryParser("content", self.schema)

            q = parser.parse(query) if query else Every()

            filters = []
            if doc_type:
                filters.append(Term("doc_type", doc_type))

            if filters:
                from whoosh.searching import Results
                results = searcher.search(q, limit=limit * 2, filter=lambda doc: all(
                    doc.get("doc_type") == doc_type for _ in [1]
                ) if doc_type else True)
            else:
                results = searcher.search(q, limit=limit * 2)

            search_results = []
            for hit in results:
                if hit.get("importance", 0.5) < min_importance:
                    continue

                highlights = []
                if query:
                    highlights = hit.highlights("content", top=3)

                search_results.append(SearchResult(
                    doc_id=hit.get("doc_id", ""),
                    title=hit.get("title", ""),
                    content=hit.get("content", ""),
                    score=hit.score,
                    file_path=hit.get("file_path", ""),
                    doc_type=hit.get("doc_type", ""),
                    highlights=highlights,
                    metadata={
                        "tags": hit.get("tags", "").split(",") if hit.get("tags") else [],
                        "importance": hit.get("importance", 0.5),
                    },
                ))

                if len(search_results) >= limit:
                    break

            return search_results

    def search_by_field(
        self,
        field_name: str,
        field_value: str,
        limit: int = 10,
    ) -> list[SearchResult]:
        """按字段搜索"""
        with self.ix.searcher() as searcher:
            q = Term(field_name, field_value)
            results = searcher.search(q, limit=limit)

            return [
                SearchResult(
                    doc_id=hit.get("doc_id", ""),
                    title=hit.get("title", ""),
                    content=hit.get("content", ""),
                    score=hit.score,
                    file_path=hit.get("file_path", ""),
                    doc_type=hit.get("doc_type", ""),
                )
                for hit in results
            ]

    def get_document(self, doc_id: str) -> Optional[dict[str, Any]]:
        """获取单个文档"""
        with self.ix.searcher() as searcher:
            doc = searcher.document(doc_id=doc_id)
            return doc

    def get_all_doc_ids(self) -> list[str]:
        """获取所有文档ID"""
        with self.ix.searcher() as searcher:
            return [doc["doc_id"] for doc in searcher.all_stored_fields()]

    def get_document_count(self) -> int:
        """获取文档数量"""
        return self.ix.doc_count()

    def optimize(self) -> None:
        """优化索引"""
        self.ix.optimize()

    def clear(self) -> None:
        """清空索引"""
        writer = self.ix.writer()
        try:
            writer.delete_by_query(Every())
            writer.commit()
        except Exception:
            writer.cancel()

    def get_stats(self) -> dict[str, Any]:
        """获取索引统计"""
        return {
            "doc_count": self.ix.doc_count(),
            "index_size_mb": sum(
                f.stat().st_size
                for f in self.index_dir.iterdir()
                if f.is_file()
            ) / (1024 * 1024),
            "last_modified": datetime.fromtimestamp(
                self.index_dir.stat().st_mtime
            ).isoformat(),
        }


class ChineseWhooshIndex(WhooshIndex):
    """
    中文全文索引
    支持中文分词
    """

    def __init__(
        self,
        index_dir: Path,
        schema: Optional[Schema] = None,
    ):
        super().__init__(index_dir, schema, language="zh")

    DEFAULT_SCHEMA = Schema(
        doc_id=ID(stored=True, unique=True),
        title=TEXT(stored=True, analyzer=SimpleAnalyzer()),
        content=TEXT(stored=True, analyzer=SimpleAnalyzer()),
        file_path=ID(stored=True),
        doc_type=KEYWORD(stored=True),
        language=KEYWORD(stored=True),
        tags=KEYWORD(stored=True),
        importance=NUMERIC(stored=True, numtype=float),
        created_at=DATETIME(stored=True),
        updated_at=DATETIME(stored=True),
    )


class HybridIndex:
    """
    混合索引
    结合 Whoosh 全文索引和向量索引
    """

    def __init__(
        self,
        whoosh_index: WhooshIndex,
        vector_store: Any,
        text_weight: float = 0.4,
        vector_weight: float = 0.6,
    ):
        self.whoosh_index = whoosh_index
        self.vector_store = vector_store
        self.text_weight = text_weight
        self.vector_weight = vector_weight

    def add_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """添加文档到混合索引"""
        self.whoosh_index.add_document(
            doc_id=doc_id,
            title=title,
            content=content,
            **(metadata or {}),
        )

        self.vector_store.add_document(
            content=content,
            metadata={"doc_id": doc_id, "title": title, **(metadata or {})},
            doc_id=doc_id,
        )

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[SearchResult]:
        """混合搜索"""
        text_results = self.whoosh_index.search(query, limit=limit * 2)

        vector_results = self.vector_store.search_with_score(query, k=limit * 2)

        merged = self._merge_results(text_results, vector_results)

        return merged[:limit]

    def _merge_results(
        self,
        text_results: list[SearchResult],
        vector_results: list[tuple],
    ) -> list[SearchResult]:
        """合并结果"""
        k = 60
        scores: dict[str, float] = {}
        results: dict[str, SearchResult] = {}

        for rank, result in enumerate(text_results, 1):
            doc_id = result.doc_id
            scores[doc_id] = scores.get(doc_id, 0) + self.text_weight / (k + rank)
            results[doc_id] = result

        for rank, (result_dict, score) in enumerate(vector_results, 1):
            doc_id = result_dict.get("doc_id", result_dict.get("metadata", {}).get("doc_id", ""))
            if doc_id:
                scores[doc_id] = scores.get(doc_id, 0) + self.vector_weight / (k + rank)

                if doc_id not in results:
                    results[doc_id] = SearchResult(
                        doc_id=doc_id,
                        title=result_dict.get("metadata", {}).get("title", ""),
                        content=result_dict.get("content", ""),
                        score=score,
                        file_path=result_dict.get("metadata", {}).get("file_path", ""),
                        doc_type=result_dict.get("metadata", {}).get("doc_type", ""),
                    )

        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [results[doc_id] for doc_id in sorted_ids if doc_id in results]
