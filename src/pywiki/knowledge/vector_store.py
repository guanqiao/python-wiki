"""
向量存储
"""

import hashlib
from pathlib import Path
from typing import Any, Optional

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.schema import Document


class VectorStore:
    """向量存储服务"""

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

        self._vectorstore: Optional[Chroma] = None
        self._initialize_store()

    def _initialize_store(self) -> None:
        try:
            self._vectorstore = Chroma(
                persist_directory=str(self.persist_dir),
                embedding_function=self._embeddings,
            )
        except Exception:
            self._vectorstore = Chroma.from_documents(
                documents=[],
                embedding=self._embeddings,
                persist_directory=str(self.persist_dir),
            )

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

        self._vectorstore.add_documents([document], ids=[doc_id])
        self._vectorstore.persist()

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

        self._vectorstore.add_documents(docs, ids=ids)
        self._vectorstore.persist()

        return ids

    def search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[dict] = None,
    ) -> list[dict]:
        """搜索相似文档"""
        if filter:
            results = self._vectorstore.similarity_search(
                query,
                k=k,
                filter=filter,
            )
        else:
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
        results = self._vectorstore.similarity_search_with_score(query, k=k)

        return [
            (
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                },
                score,
            )
            for doc, score in results
        ]

    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        try:
            self._vectorstore.delete([doc_id])
            self._vectorstore.persist()
            return True
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
        return self._vectorstore._collection.count()

    def clear(self) -> None:
        """清空向量存储"""
        self._vectorstore.delete_collection()
        self._initialize_store()
