"""
混合检索系统
结合向量检索和 BM25 关键词检索
"""

import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.schema import Document

from pywiki.search.engine import SearchQuery, SearchResult, IndexLevel


@dataclass
class BM25Config:
    k1: float = 1.5
    b: float = 0.75
    epsilon: float = 0.25


@dataclass
class DocumentInfo:
    doc_id: str
    content: str
    tokens: list[str]
    doc_len: int
    metadata: dict[str, Any] = field(default_factory=dict)


class BM25Index:
    """
    BM25 关键词索引
    实现经典的 BM25 排序算法
    """

    def __init__(self, config: Optional[BM25Config] = None):
        self.config = config or BM25Config()
        self._documents: dict[str, DocumentInfo] = {}
        self._doc_freqs: dict[str, int] = defaultdict(int)
        self._term_freqs: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._avg_doc_len: float = 0.0
        self._doc_count: int = 0

    def _tokenize(self, text: str) -> list[str]:
        """简单分词"""
        text = text.lower()
        tokens = []
        current_token = []
        for char in text:
            if char.isalnum() or char == "_":
                current_token.append(char)
            else:
                if current_token:
                    tokens.append("".join(current_token))
                    current_token = []
        if current_token:
            tokens.append("".join(current_token))
        return tokens

    def add_document(self, doc_id: str, content: str, metadata: Optional[dict] = None) -> None:
        """添加文档"""
        tokens = self._tokenize(content)
        doc_len = len(tokens)

        self._documents[doc_id] = DocumentInfo(
            doc_id=doc_id,
            content=content,
            tokens=tokens,
            doc_len=doc_len,
            metadata=metadata or {},
        )

        term_freqs: dict[str, int] = defaultdict(int)
        for token in tokens:
            term_freqs[token] += 1

        for term, freq in term_freqs.items():
            self._term_freqs[doc_id][term] = freq
            self._doc_freqs[term] += 1

        self._doc_count += 1
        total_len = sum(d.doc_len for d in self._documents.values())
        self._avg_doc_len = total_len / self._doc_count

    def remove_document(self, doc_id: str) -> bool:
        """移除文档"""
        if doc_id not in self._documents:
            return False

        doc = self._documents[doc_id]
        for token in set(doc.tokens):
            if token in self._doc_freqs:
                self._doc_freqs[token] -= 1
                if self._doc_freqs[token] <= 0:
                    del self._doc_freqs[token]

        if doc_id in self._term_freqs:
            del self._term_freqs[doc_id]

        del self._documents[doc_id]
        self._doc_count -= 1

        if self._doc_count > 0:
            total_len = sum(d.doc_len for d in self._documents.values())
            self._avg_doc_len = total_len / self._doc_count
        else:
            self._avg_doc_len = 0.0

        return True

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float, dict]]:
        """
        BM25 搜索

        Returns:
            list of (doc_id, score, metadata)
        """
        query_tokens = self._tokenize(query)
        scores: dict[str, float] = defaultdict(float)

        idf_cache: dict[str, float] = {}
        for token in query_tokens:
            if token not in idf_cache:
                df = self._doc_freqs.get(token, 0)
                if df > 0:
                    idf = math.log(
                        (self._doc_count - df + 0.5) / (df + 0.5) + 1
                    )
                else:
                    idf = 0.0
                idf_cache[token] = idf

        for doc_id, doc in self._documents.items():
            score = 0.0
            for token in query_tokens:
                if token not in self._term_freqs[doc_id]:
                    continue

                tf = self._term_freqs[doc_id][token]
                idf = idf_cache.get(token, 0.0)

                numerator = tf * (self.config.k1 + 1)
                denominator = tf + self.config.k1 * (
                    1 - self.config.b + self.config.b * doc.doc_len / max(self._avg_doc_len, 1)
                )

                score += idf * numerator / denominator

            if score > 0:
                scores[doc_id] = score

        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [
            (doc_id, score, self._documents[doc_id].metadata)
            for doc_id, score in sorted_results[:top_k]
        ]

    def clear(self) -> None:
        """清空索引"""
        self._documents.clear()
        self._doc_freqs.clear()
        self._term_freqs.clear()
        self._avg_doc_len = 0.0
        self._doc_count = 0

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "doc_count": self._doc_count,
            "avg_doc_len": self._avg_doc_len,
            "vocabulary_size": len(self._doc_freqs),
        }


class HybridSearch:
    """
    混合检索系统
    结合向量检索和 BM25 检索
    """

    def __init__(
        self,
        persist_dir: Path,
        openai_api_key: Optional[str] = None,
        openai_api_base: Optional[str] = None,
        embedding_model: str = "text-embedding-ada-002",
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4,
    ):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight

        self._embeddings = OpenAIEmbeddings(
            model=embedding_model,
            openai_api_key=openai_api_key,
            openai_api_base=openai_api_base,
        )

        self._vector_index: Optional[FAISS] = None
        self._bm25_index = BM25Index()
        self._doc_metadata: dict[str, dict[str, Any]] = {}

        self._initialize()

    def _initialize(self) -> None:
        """初始化索引"""
        vector_path = self.persist_dir / "vector"
        if vector_path.exists():
            try:
                self._vector_index = FAISS.load_local(
                    folder_path=str(vector_path),
                    embeddings=self._embeddings,
                    allow_dangerous_deserialization=True,
                )
            except Exception:
                pass

        metadata_path = self.persist_dir / "metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    self._doc_metadata = json.load(f)
            except Exception:
                pass

    def _save_metadata(self) -> None:
        """保存元数据"""
        metadata_path = self.persist_dir / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(self._doc_metadata, f, ensure_ascii=False, indent=2)

    async def index_documents(self, documents: list[dict[str, Any]]) -> int:
        """
        索引文档

        Args:
            documents: 文档列表，每个包含 id, content, metadata

        Returns:
            索引的文档数量
        """
        docs = []
        indexed_count = 0

        for doc in documents:
            content = doc.get("content", "")
            doc_id = doc.get("id") or hashlib.md5(content.encode()).hexdigest()
            metadata = doc.get("metadata", {})

            docs.append(Document(page_content=content, metadata={**metadata, "doc_id": doc_id}))
            self._doc_metadata[doc_id] = metadata

            self._bm25_index.add_document(doc_id, content, metadata)
            indexed_count += 1

        if docs:
            if self._vector_index is None:
                self._vector_index = FAISS.from_documents(docs, self._embeddings)
            else:
                self._vector_index.add_documents(docs)

            vector_path = self.persist_dir / "vector"
            self._vector_index.save_local(str(vector_path))

        self._save_metadata()
        return indexed_count

    async def search(self, query: SearchQuery) -> list[SearchResult]:
        """
        混合搜索

        Args:
            query: 搜索查询

        Returns:
            搜索结果列表
        """
        semantic_results = await self._semantic_search(query.query, query.top_k * 2)
        keyword_results = await self._keyword_search(query.query, query.top_k * 2)

        merged = self._merge_results(semantic_results, keyword_results)

        return merged[:query.top_k]

    async def _semantic_search(self, query: str, top_k: int) -> list[tuple[str, float, dict]]:
        """向量检索"""
        if self._vector_index is None:
            return []

        results = self._vector_index.similarity_search_with_score(query, k=top_k)
        return [
            (
                doc.metadata.get("doc_id", ""),
                float(score),
                doc.metadata,
            )
            for doc, score in results
        ]

    async def _keyword_search(self, query: str, top_k: int) -> list[tuple[str, float, dict]]:
        """关键词检索"""
        return self._bm25_index.search(query, top_k)

    def _merge_results(
        self,
        semantic_results: list[tuple[str, float, dict]],
        keyword_results: list[tuple[str, float, dict]],
    ) -> list[SearchResult]:
        """
        合并检索结果
        使用倒数排名融合（RRF）算法
        """
        k = 60

        rrf_scores: dict[str, float] = defaultdict(float)
        doc_info: dict[str, tuple[float, float, dict]] = {}

        for rank, (doc_id, score, metadata) in enumerate(semantic_results, 1):
            rrf_scores[doc_id] += self.semantic_weight / (k + rank)
            if doc_id not in doc_info:
                doc_info[doc_id] = (score, 0.0, metadata)
            else:
                old_semantic, old_keyword, old_meta = doc_info[doc_id]
                doc_info[doc_id] = (score, old_keyword, old_meta)

        for rank, (doc_id, score, metadata) in enumerate(keyword_results, 1):
            rrf_scores[doc_id] += self.keyword_weight / (k + rank)
            if doc_id not in doc_info:
                doc_info[doc_id] = (0.0, score, metadata)
            else:
                old_semantic, old_keyword, old_meta = doc_info[doc_id]
                doc_info[doc_id] = (old_semantic, score, old_meta)

        merged = []
        for doc_id, rrf_score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
            semantic_score, keyword_score, metadata = doc_info[doc_id]
            content = self._bm25_index._documents.get(doc_id, DocumentInfo(
                doc_id=doc_id, content="", tokens=[], doc_len=0
            )).content

            merged.append(SearchResult(
                content=content,
                score=rrf_score,
                source=metadata.get("file_path", metadata.get("project_name", "")),
                level=IndexLevel(metadata.get("level", "file")),
                metadata={
                    **metadata,
                    "semantic_score": semantic_score,
                    "keyword_score": keyword_score,
                },
            ))

        return merged

    async def remove_document(self, doc_id: str) -> bool:
        """移除文档"""
        self._bm25_index.remove_document(doc_id)
        if doc_id in self._doc_metadata:
            del self._doc_metadata[doc_id]
        self._save_metadata()
        return True

    async def clear(self) -> None:
        """清空索引"""
        self._vector_index = None
        self._bm25_index.clear()
        self._doc_metadata.clear()
        self._save_metadata()

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "bm25": self._bm25_index.get_stats(),
            "doc_count": len(self._doc_metadata),
            "semantic_weight": self.semantic_weight,
            "keyword_weight": self.keyword_weight,
        }
