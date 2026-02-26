"""
语义索引器
基于向量嵌入的语义搜索
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import hashlib
import json


@dataclass
class SemanticDocument:
    id: str
    content: str
    embedding: Optional[list[float]] = None
    metadata: dict = field(default_factory=dict)


class SemanticIndexer:
    """语义索引器"""

    def __init__(
        self,
        index_dir: Path,
        embedding_model: Optional[str] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self._documents: dict[str, SemanticDocument] = {}
        self._embeddings_cache: dict[str, list[float]] = {}
        self._index_file = index_dir / "semantic_index.json"

        self._load_index()

    def _load_index(self) -> None:
        """加载索引"""
        if self._index_file.exists():
            with open(self._index_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for doc_data in data.get("documents", []):
                doc = SemanticDocument(
                    id=doc_data["id"],
                    content=doc_data["content"],
                    embedding=doc_data.get("embedding"),
                    metadata=doc_data.get("metadata", {}),
                )
                self._documents[doc.id] = doc

    def _save_index(self) -> None:
        """保存索引"""
        data = {
            "documents": [
                {
                    "id": doc.id,
                    "content": doc.content,
                    "embedding": doc.embedding,
                    "metadata": doc.metadata,
                }
                for doc in self._documents.values()
            ]
        }

        with open(self._index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def index_document(
        self,
        content: str,
        metadata: Optional[dict] = None,
        doc_id: Optional[str] = None,
    ) -> str:
        """索引文档"""
        if doc_id is None:
            doc_id = hashlib.md5(content.encode()).hexdigest()

        chunks = self._chunk_content(content)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            doc = SemanticDocument(
                id=chunk_id,
                content=chunk,
                metadata={
                    **(metadata or {}),
                    "parent_id": doc_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            )
            self._documents[chunk_id] = doc

        self._save_index()
        return doc_id

    def index_code(
        self,
        code: str,
        file_path: str,
        symbols: Optional[list[dict]] = None,
    ) -> list[str]:
        """索引代码"""
        doc_ids = []

        doc_id = self.index_document(
            content=code,
            metadata={
                "type": "code",
                "file_path": file_path,
            },
        )
        doc_ids.append(doc_id)

        if symbols:
            for symbol in symbols:
                symbol_content = self._format_symbol_content(symbol)
                symbol_id = self.index_document(
                    content=symbol_content,
                    metadata={
                        "type": "symbol",
                        "file_path": file_path,
                        "symbol_name": symbol.get("name"),
                        "symbol_type": symbol.get("type"),
                    },
                )
                doc_ids.append(symbol_id)

        return doc_ids

    def _format_symbol_content(self, symbol: dict) -> str:
        """格式化符号内容"""
        lines = []

        symbol_type = symbol.get("type", "unknown")
        name = symbol.get("name", "")
        docstring = symbol.get("docstring", "")

        lines.append(f"{symbol_type}: {name}")
        if docstring:
            lines.append(f"Description: {docstring}")

        if symbol_type == "function":
            params = symbol.get("parameters", [])
            if params:
                param_str = ", ".join(p.get("name", "") for p in params)
                lines.append(f"Parameters: {param_str}")

            return_type = symbol.get("return_type")
            if return_type:
                lines.append(f"Returns: {return_type}")

        elif symbol_type == "class":
            bases = symbol.get("bases", [])
            if bases:
                lines.append(f"Inherits from: {', '.join(bases)}")

            methods = symbol.get("methods", [])
            if methods:
                lines.append(f"Methods: {', '.join(m.get('name', '') for m in methods)}")

        return "\n".join(lines)

    def _chunk_content(self, content: str) -> list[str]:
        """分块内容"""
        words = content.split()
        chunks = []

        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunks.append(" ".join(chunk_words))

        return chunks if chunks else [content]

    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_type: Optional[str] = None,
    ) -> list[tuple[SemanticDocument, float]]:
        """语义搜索"""
        results = []

        query_lower = query.lower()
        query_words = set(query_lower.split())

        for doc in self._documents.values():
            if filter_type and doc.metadata.get("type") != filter_type:
                continue

            score = self._compute_similarity(query, doc.content)
            if score > 0:
                results.append((doc, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _compute_similarity(self, query: str, content: str) -> float:
        """计算相似度"""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())

        if not query_words or not content_words:
            return 0.0

        intersection = query_words & content_words
        union = query_words | content_words

        jaccard = len(intersection) / len(union) if union else 0

        coverage = len(intersection) / len(query_words) if query_words else 0

        return 0.6 * jaccard + 0.4 * coverage

    def remove_document(self, doc_id: str) -> bool:
        """移除文档"""
        keys_to_remove = [
            k for k in self._documents.keys()
            if k == doc_id or k.startswith(f"{doc_id}_chunk_")
        ]

        for key in keys_to_remove:
            del self._documents[key]

        if keys_to_remove:
            self._save_index()
            return True
        return False

    def get_document(self, doc_id: str) -> Optional[SemanticDocument]:
        """获取文档"""
        return self._documents.get(doc_id)

    def get_statistics(self) -> dict:
        """获取统计信息"""
        types = {}
        for doc in self._documents.values():
            doc_type = doc.metadata.get("type", "unknown")
            types[doc_type] = types.get(doc_type, 0) + 1

        return {
            "total_documents": len(self._documents),
            "by_type": types,
        }

    def clear(self) -> None:
        """清除索引"""
        self._documents.clear()
        self._save_index()
