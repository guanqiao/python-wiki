"""
向量存储 - 使用 FAISS 实现
"""

import hashlib
import json
import pickle
from pathlib import Path
from typing import Any, Optional

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.schema import Document


class VectorStore:
    """向量存储服务 - FAISS 实现"""

    def __init__(
        self,
        persist_dir: Path,
        embedding_model: str = "text-embedding-ada-002",
        openai_api_key: Optional[str] = None,
        openai_api_base: Optional[str] = None,
    ):
        self.persist_dir = persist_dir
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self._embeddings = OpenAIEmbeddings(
            model=embedding_model,
            openai_api_key=openai_api_key,
            openai_api_base=openai_api_base,
        )

        self._vectorstore: Optional[FAISS] = None
        self._doc_ids: list[str] = []
        self._initialize_store()

    def _get_index_path(self) -> Path:
        return self.persist_dir / "index.faiss"

    def _get_docstore_path(self) -> Path:
        return self.persist_dir / "docstore.pkl"

    def _get_metadata_path(self) -> Path:
        return self.persist_dir / "metadata.json"

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
                metadata_path = self._get_metadata_path()
                if metadata_path.exists():
                    with open(metadata_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self._doc_ids = data.get("doc_ids", [])
            except Exception:
                self._create_empty_store()
        else:
            self._create_empty_store()

    def _create_empty_store(self) -> None:
        empty_doc = Document(page_content="", metadata={})
        self._vectorstore = FAISS.from_documents(
            [empty_doc],
            self._embeddings,
        )
        self._doc_ids = []
        self._save_store()

    def _save_store(self) -> None:
        if self._vectorstore:
            self._vectorstore.save_local(str(self.persist_dir))
            with open(self._get_metadata_path(), "w", encoding="utf-8") as f:
                json.dump({"doc_ids": self._doc_ids}, f)

    def add_document(
        self,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
        doc_id: Optional[str] = None,
    ) -> str:
        """添加文档到向量存储"""
        if doc_id is None:
            doc_id = hashlib.md5(content.encode()).hexdigest()

        document = Document(
            page_content=content,
            metadata=metadata or {},
        )

        if self._vectorstore is None:
            self._vectorstore = FAISS.from_documents([document], self._embeddings)
        else:
            self._vectorstore.add_documents([document])

        self._doc_ids.append(doc_id)
        self._save_store()

        return doc_id

    def add_documents(
        self,
        documents: list[dict[str, Any]],
    ) -> list[str]:
        """批量添加文档"""
        docs = []
        ids = []

        for doc in documents:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            doc_id = doc.get("id") or hashlib.md5(content.encode()).hexdigest()

            docs.append(Document(page_content=content, metadata=metadata))
            ids.append(doc_id)

        if self._vectorstore is None:
            self._vectorstore = FAISS.from_documents(docs, self._embeddings)
        else:
            self._vectorstore.add_documents(docs)

        self._doc_ids.extend(ids)
        self._save_store()

        return ids

    def search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[dict] = None,
    ) -> list[dict]:
        """搜索相似文档"""
        if self._vectorstore is None:
            return []

        results = self._vectorstore.similarity_search(query, k=k)

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": getattr(doc, "score", None),
            }
            for doc in results
        ]

    def search_with_score(
        self,
        query: str,
        k: int = 5,
    ) -> list[tuple[dict, float]]:
        """搜索并返回相似度分数"""
        if self._vectorstore is None:
            return []

        results = self._vectorstore.similarity_search_with_score(query, k=k)

        return [
            (
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                },
                float(score),
            )
            for doc, score in results
        ]

    def delete_document(self, doc_id: str) -> bool:
        """删除文档 - FAISS 不支持直接删除，需要重建索引"""
        try:
            if doc_id in self._doc_ids:
                self._doc_ids.remove(doc_id)
                return True
            return False
        except Exception:
            return False

    def update_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """更新文档"""
        try:
            self.delete_document(doc_id)
            self.add_document(content, metadata, doc_id)
            return True
        except Exception:
            return False

    def get_document_count(self) -> int:
        """获取文档数量"""
        return len(self._doc_ids)

    def clear(self) -> None:
        """清空向量存储"""
        self._create_empty_store()
