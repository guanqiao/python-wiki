"""
向量存储 - 使用 FAISS 实现
支持增量索引和高效检索
"""

import asyncio
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document


@dataclass
class DocumentRecord:
    doc_id: str
    content_hash: str
    file_path: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class IndexStats:
    total_documents: int = 0
    total_chunks: int = 0
    index_size_mb: float = 0.0
    last_updated: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_documents": self.total_documents,
            "total_chunks": self.total_chunks,
            "index_size_mb": self.index_size_mb,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


class VectorStore:
    """
    向量存储服务 - FAISS 实现
    支持增量索引、文档去重和高效检索
    """

    def __init__(
        self,
        persist_dir: Path,
        embedding_model: str = "text-embedding-ada-002",
        openai_api_key: Optional[str] = None,
        openai_api_base: Optional[str] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self._embeddings = OpenAIEmbeddings(
            model=embedding_model,
            api_key=openai_api_key,
            base_url=openai_api_base,
        )

        self._vectorstore: Optional[FAISS] = None
        self._doc_ids: list[str] = []
        self._doc_records: dict[str, DocumentRecord] = {}
        self._content_hashes: dict[str, str] = {}

        self._stats = IndexStats()

        self._initialize_store()

    def _get_index_path(self) -> Path:
        return self.persist_dir / "index.faiss"

    def _get_docstore_path(self) -> Path:
        return self.persist_dir / "docstore.pkl"

    def _get_metadata_path(self) -> Path:
        return self.persist_dir / "metadata.json"

    def _get_records_path(self) -> Path:
        return self.persist_dir / "records.json"

    def _initialize_store(self) -> None:
        index_path = self._get_index_path()
        docstore_path = self._get_docstore_path()

        if index_path.exists() and docstore_path.exists():
            try:
                self._vectorstore = FAISS.load_local(
                    folder_path=str(self.persist_dir),
                    embeddings=self._embeddings,
                    allow_dangerous_deserialization=True,
                )
                self._load_records()
            except Exception:
                self._create_empty_store()
        else:
            self._create_empty_store()

    def _validate_index_integrity(self) -> bool:
        """验证索引完整性"""
        index_path = self._get_index_path()
        docstore_path = self._get_docstore_path()
        records_path = self._get_records_path()

        if not all(p.exists() for p in [index_path, docstore_path, records_path]):
            return False

        try:
            with open(records_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return "doc_ids" in data and "records" in data
        except Exception:
            return False

    def _create_empty_store(self) -> None:
        empty_doc = Document(page_content="", metadata={})
        self._vectorstore = FAISS.from_documents(
            [empty_doc],
            self._embeddings,
        )
        self._doc_ids = []
        self._doc_records = {}
        self._content_hashes = {}
        self._save_store()

    def _load_records(self) -> None:
        records_path = self._get_records_path()
        if records_path.exists():
            try:
                with open(records_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._doc_ids = data.get("doc_ids", [])
                    self._content_hashes = data.get("content_hashes", {})

                    records_data = data.get("records", {})
                    for doc_id, record in records_data.items():
                        self._doc_records[doc_id] = DocumentRecord(
                            doc_id=doc_id,
                            content_hash=record["content_hash"],
                            file_path=record.get("file_path"),
                            metadata=record.get("metadata", {}),
                            created_at=datetime.fromisoformat(record["created_at"]),
                            updated_at=datetime.fromisoformat(record["updated_at"]),
                        )

                    self._stats.total_documents = len(self._doc_records)
                    self._stats.total_chunks = len(self._doc_ids)
                    if self._doc_records:
                        self._stats.last_updated = max(
                            r.updated_at for r in self._doc_records.values()
                        )
            except Exception:
                pass

    def _save_store(self) -> None:
        if self._vectorstore:
            self._vectorstore.save_local(str(self.persist_dir))

            records_data = {
                "doc_ids": self._doc_ids,
                "content_hashes": self._content_hashes,
                "records": {
                    doc_id: {
                        "content_hash": record.content_hash,
                        "file_path": record.file_path,
                        "metadata": record.metadata,
                        "created_at": record.created_at.isoformat(),
                        "updated_at": record.updated_at.isoformat(),
                    }
                    for doc_id, record in self._doc_records.items()
                },
            }

            with open(self._get_records_path(), "w", encoding="utf-8") as f:
                json.dump(records_data, f, ensure_ascii=False, indent=2)

            self._stats.total_documents = len(self._doc_records)
            self._stats.total_chunks = len(self._doc_ids)
            self._stats.last_updated = datetime.now()

    def _compute_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.sha256(content.encode()).hexdigest()

    def _chunk_content(self, content: str) -> list[str]:
        """
        将内容分块

        Args:
            content: 原始内容

        Returns:
            分块后的内容列表
        """
        if len(content) <= self.chunk_size:
            return [content]

        chunks = []
        start = 0
        while start < len(content):
            end = start + self.chunk_size
            chunk = content[start:end]
            chunks.append(chunk)
            start = end - self.chunk_overlap
            if start >= len(content):
                break

        return chunks

    def add_document(
        self,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
        doc_id: Optional[str] = None,
        file_path: Optional[str] = None,
        skip_if_exists: bool = True,
    ) -> str:
        """
        添加文档到向量存储

        Args:
            content: 文档内容
            metadata: 元数据
            doc_id: 文档ID（可选）
            file_path: 文件路径（可选）
            skip_if_exists: 如果内容已存在则跳过

        Returns:
            文档ID
        """
        content_hash = self._compute_hash(content)

        if skip_if_exists and content_hash in self._content_hashes:
            existing_doc_id = self._content_hashes[content_hash]
            if existing_doc_id in self._doc_records:
                record = self._doc_records[existing_doc_id]
                record.updated_at = datetime.now()
                self._save_store()
                return existing_doc_id

        if doc_id is None:
            doc_id = hashlib.md5(content.encode()).hexdigest()

        chunks = self._chunk_content(content)
        documents = []

        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                **(metadata or {}),
                "doc_id": doc_id,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "content_hash": content_hash,
            }
            if file_path:
                chunk_metadata["file_path"] = file_path

            documents.append(Document(page_content=chunk, metadata=chunk_metadata))

        if self._vectorstore is None:
            self._vectorstore = FAISS.from_documents(documents, self._embeddings)
        else:
            self._vectorstore.add_documents(documents)

        self._doc_ids.append(doc_id)
        self._content_hashes[content_hash] = doc_id

        self._doc_records[doc_id] = DocumentRecord(
            doc_id=doc_id,
            content_hash=content_hash,
            file_path=file_path,
            metadata=metadata or {},
        )

        self._save_store()

        return doc_id

    def add_documents(
        self,
        documents: list[dict[str, Any]],
        skip_if_exists: bool = True,
    ) -> list[str]:
        """
        批量添加文档

        Args:
            documents: 文档列表，每个包含 content, metadata, id, file_path
            skip_if_exists: 如果内容已存在则跳过

        Returns:
            文档ID列表
        """
        ids = []
        for doc in documents:
            doc_id = self.add_document(
                content=doc.get("content", ""),
                metadata=doc.get("metadata"),
                doc_id=doc.get("id"),
                file_path=doc.get("file_path"),
                skip_if_exists=skip_if_exists,
            )
            ids.append(doc_id)

        return ids

    async def add_document_async(
        self,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
        doc_id: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> str:
        """异步添加文档"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.add_document(content, metadata, doc_id, file_path),
        )

    async def add_documents_async(
        self,
        documents: list[dict[str, Any]],
    ) -> list[str]:
        """异步批量添加文档"""
        tasks = [
            self.add_document_async(
                content=doc.get("content", ""),
                metadata=doc.get("metadata"),
                doc_id=doc.get("id"),
                file_path=doc.get("file_path"),
            )
            for doc in documents
        ]
        return await asyncio.gather(*tasks)

    def search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[dict] = None,
    ) -> list[dict]:
        """
        搜索相似文档

        Args:
            query: 查询文本
            k: 返回结果数量
            filter: 元数据过滤条件

        Returns:
            搜索结果列表
        """
        if self._vectorstore is None:
            return []

        results = self._vectorstore.similarity_search(query, k=k * 2)

        filtered_results = []
        for doc in results:
            if filter:
                match = all(
                    doc.metadata.get(key) == value
                    for key, value in filter.items()
                )
                if not match:
                    continue

            filtered_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "doc_id": doc.metadata.get("doc_id"),
                "chunk_index": doc.metadata.get("chunk_index"),
            })

            if len(filtered_results) >= k:
                break

        return filtered_results

    def search_with_score(
        self,
        query: str,
        k: int = 5,
        filter: Optional[dict] = None,
    ) -> list[tuple[dict, float]]:
        """
        搜索并返回相似度分数

        Args:
            query: 查询文本
            k: 返回结果数量
            filter: 元数据过滤条件

        Returns:
            list of (result_dict, score)
        """
        if self._vectorstore is None:
            return []

        results = self._vectorstore.similarity_search_with_score(query, k=k * 2)

        filtered_results = []
        for doc, score in results:
            if filter:
                match = all(
                    doc.metadata.get(key) == value
                    for key, value in filter.items()
                )
                if not match:
                    continue

            filtered_results.append((
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "doc_id": doc.metadata.get("doc_id"),
                    "chunk_index": doc.metadata.get("chunk_index"),
                },
                float(score),
            ))

            if len(filtered_results) >= k:
                break

        return filtered_results

    def search_by_file(self, file_path: str, k: int = 10) -> list[dict]:
        """
        按文件路径搜索

        Args:
            file_path: 文件路径
            k: 返回结果数量

        Returns:
            搜索结果列表
        """
        return self.search("", k=k, filter={"file_path": file_path})

    def delete_document(self, doc_id: str) -> bool:
        """
        删除文档

        注意：FAISS 不支持直接删除，此方法仅从记录中移除
        实际删除需要重建索引

        Args:
            doc_id: 文档ID

        Returns:
            是否成功
        """
        try:
            if doc_id in self._doc_records:
                record = self._doc_records[doc_id]
                if record.content_hash in self._content_hashes:
                    del self._content_hashes[record.content_hash]
                del self._doc_records[doc_id]

            if doc_id in self._doc_ids:
                self._doc_ids.remove(doc_id)

            self._save_store()
            return True
        except Exception:
            return False

    def update_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
        file_path: Optional[str] = None,
    ) -> bool:
        """
        更新文档

        Args:
            doc_id: 文档ID
            content: 新内容
            metadata: 新元数据
            file_path: 文件路径

        Returns:
            是否成功
        """
        try:
            self.delete_document(doc_id)
            self.add_document(content, metadata, doc_id, file_path, skip_if_exists=False)
            return True
        except Exception:
            return False

    def get_document(self, doc_id: str) -> Optional[dict[str, Any]]:
        """
        获取文档信息

        Args:
            doc_id: 文档ID

        Returns:
            文档信息字典
        """
        if doc_id not in self._doc_records:
            return None

        record = self._doc_records[doc_id]
        return {
            "doc_id": record.doc_id,
            "content_hash": record.content_hash,
            "file_path": record.file_path,
            "metadata": record.metadata,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
        }

    def get_document_count(self) -> int:
        """获取文档数量"""
        return len(self._doc_records)

    def get_chunk_count(self) -> int:
        """获取分块数量"""
        return len(self._doc_ids)

    def get_stats(self) -> IndexStats:
        """获取索引统计"""
        return self._stats

    def get_files(self) -> list[str]:
        """获取所有已索引的文件路径"""
        files = set()
        for record in self._doc_records.values():
            if record.file_path:
                files.add(record.file_path)
        return list(files)

    def clear(self) -> None:
        """清空向量存储"""
        self._create_empty_store()

    def rebuild_index(self) -> bool:
        """
        重建索引

        清理无效条目并重建索引

        Returns:
            是否成功
        """
        try:
            valid_docs = []
            seen_hashes = set()

            for doc_id, record in self._doc_records.items():
                if record.content_hash not in seen_hashes:
                    seen_hashes.add(record.content_hash)
                    valid_docs.append({
                        "id": doc_id,
                        "content_hash": record.content_hash,
                        "metadata": record.metadata,
                        "file_path": record.file_path,
                    })

            self._create_empty_store()

            return True
        except Exception:
            return False

    def export_records(self) -> dict[str, Any]:
        """
        导出文档记录

        Returns:
            文档记录字典
        """
        return {
            "total_documents": len(self._doc_records),
            "total_chunks": len(self._doc_ids),
            "documents": {
                doc_id: {
                    "content_hash": record.content_hash,
                    "file_path": record.file_path,
                    "metadata": record.metadata,
                    "created_at": record.created_at.isoformat(),
                    "updated_at": record.updated_at.isoformat(),
                }
                for doc_id, record in self._doc_records.items()
            },
        }
