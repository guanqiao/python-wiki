"""
分层索引系统
支持项目/模块/文件三级索引
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
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.schema import Document

from pywiki.search.engine import IndexLevel, SearchResult


@dataclass
class IndexEntry:
    doc_id: str
    content: str
    level: IndexLevel
    project_name: str
    module_name: Optional[str] = None
    file_path: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class IndexStats:
    total_documents: int = 0
    project_count: int = 0
    module_count: int = 0
    file_count: int = 0
    last_indexed: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_documents": self.total_documents,
            "project_count": self.project_count,
            "module_count": self.module_count,
            "file_count": self.file_count,
            "last_indexed": self.last_indexed.isoformat() if self.last_indexed else None,
        }


class TieredIndex:
    """
    分层索引系统
    支持项目级、模块级、文件级三级索引
    """

    def __init__(
        self,
        persist_dir: Path,
        openai_api_key: Optional[str] = None,
        openai_api_base: Optional[str] = None,
        embedding_model: str = "text-embedding-ada-002",
    ):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self._embeddings = OpenAIEmbeddings(
            model=embedding_model,
            openai_api_key=openai_api_key,
            openai_api_base=openai_api_base,
        )

        self._project_index: dict[str, FAISS] = {}
        self._module_index: dict[str, FAISS] = {}
        self._file_index: Optional[FAISS] = None

        self._entries: dict[str, IndexEntry] = {}
        self._project_entries: dict[str, list[str]] = defaultdict(list)
        self._module_entries: dict[str, list[str]] = defaultdict(list)

        self._stats = IndexStats()

        self._initialize()

    def _initialize(self) -> None:
        """初始化索引"""
        self._load_entries()
        self._load_indexes()

    def _get_entries_path(self) -> Path:
        return self.persist_dir / "entries.json"

    def _get_project_index_dir(self, project_name: str) -> Path:
        safe_name = self._safe_name(project_name)
        return self.persist_dir / "projects" / safe_name

    def _get_module_index_dir(self, project_name: str, module_name: str) -> Path:
        safe_project = self._safe_name(project_name)
        safe_module = self._safe_name(module_name)
        return self.persist_dir / "modules" / safe_project / safe_module

    def _get_file_index_dir(self) -> Path:
        return self.persist_dir / "files"

    @staticmethod
    def _safe_name(name: str) -> str:
        return name.replace("/", "_").replace("\\", "_").replace(":", "_")

    def _load_entries(self) -> None:
        """加载条目元数据"""
        entries_path = self._get_entries_path()
        if entries_path.exists():
            try:
                with open(entries_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for doc_id, entry_data in data.get("entries", {}).items():
                        entry_data["created_at"] = datetime.fromisoformat(entry_data["created_at"])
                        entry_data["updated_at"] = datetime.fromisoformat(entry_data["updated_at"])
                        entry_data["level"] = IndexLevel(entry_data["level"])
                        self._entries[doc_id] = IndexEntry(**entry_data)

                    self._project_entries = defaultdict(list, data.get("projects", {}))
                    self._module_entries = defaultdict(list, data.get("modules", {}))

                    self._stats.total_documents = len(self._entries)
                    self._stats.project_count = len(self._project_entries)
                    self._stats.module_count = len(self._module_entries)
                    self._stats.file_count = sum(
                        1 for e in self._entries.values() if e.level == IndexLevel.FILE
                    )
            except Exception:
                pass

    def _save_entries(self) -> None:
        """保存条目元数据"""
        entries_path = self._get_entries_path()
        data = {
            "entries": {
                doc_id: {
                    **{
                        k: v if not isinstance(v, IndexLevel) else v.value
                        for k, v in entry.__dict__.items()
                        if k not in ("created_at", "updated_at")
                    },
                    "created_at": entry.created_at.isoformat(),
                    "updated_at": entry.updated_at.isoformat(),
                }
                for doc_id, entry in self._entries.items()
            },
            "projects": dict(self._project_entries),
            "modules": dict(self._module_entries),
        }
        with open(entries_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_indexes(self) -> None:
        """加载索引"""
        projects_dir = self.persist_dir / "projects"
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if project_dir.is_dir():
                    try:
                        self._project_index[project_dir.name] = FAISS.load_local(
                            folder_path=str(project_dir),
                            embeddings=self._embeddings,
                            allow_dangerous_deserialization=True,
                        )
                    except Exception:
                        pass

        modules_dir = self.persist_dir / "modules"
        if modules_dir.exists():
            for project_dir in modules_dir.iterdir():
                if project_dir.is_dir():
                    for module_dir in project_dir.iterdir():
                        if module_dir.is_dir():
                            try:
                                key = f"{project_dir.name}_{module_dir.name}"
                                self._module_index[key] = FAISS.load_local(
                                    folder_path=str(module_dir),
                                    embeddings=self._embeddings,
                                    allow_dangerous_deserialization=True,
                                )
                            except Exception:
                                pass

        file_index_dir = self._get_file_index_dir()
        if file_index_dir.exists():
            try:
                self._file_index = FAISS.load_local(
                    folder_path=str(file_index_dir),
                    embeddings=self._embeddings,
                    allow_dangerous_deserialization=True,
                )
            except Exception:
                pass

    def _create_empty_index(self) -> FAISS:
        """创建空索引"""
        empty_doc = Document(page_content="", metadata={})
        return FAISS.from_documents([empty_doc], self._embeddings)

    def _save_index(self, index: FAISS, path: Path) -> None:
        """保存索引"""
        path.mkdir(parents=True, exist_ok=True)
        index.save_local(str(path))

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
            documents: 文档列表

        Returns:
            索引的文档数量
        """
        indexed_count = 0
        docs_by_level: dict[IndexLevel, list[Document]] = defaultdict(list)

        for doc in documents:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            level_str = doc.get("level", "file")
            level = IndexLevel(level_str) if isinstance(level_str, str) else level_str

            doc_id = doc.get("id") or hashlib.md5(content.encode()).hexdigest()

            entry = IndexEntry(
                doc_id=doc_id,
                content=content,
                level=level,
                project_name=project_name,
                module_name=metadata.get("module_name"),
                file_path=metadata.get("file_path"),
                metadata=metadata,
            )
            self._entries[doc_id] = entry

            if level == IndexLevel.PROJECT:
                self._project_entries[project_name].append(doc_id)
            elif level == IndexLevel.MODULE:
                module_name = metadata.get("module_name", "default")
                self._module_entries[f"{project_name}_{module_name}"].append(doc_id)

            document = Document(page_content=content, metadata={**metadata, "doc_id": doc_id})
            docs_by_level[level].append(document)
            indexed_count += 1

        if docs_by_level[IndexLevel.PROJECT]:
            project_docs = docs_by_level[IndexLevel.PROJECT]
            if project_name in self._project_index:
                self._project_index[project_name].add_documents(project_docs)
            else:
                self._project_index[project_name] = FAISS.from_documents(
                    project_docs, self._embeddings
                )
            self._save_index(
                self._project_index[project_name],
                self._get_project_index_dir(project_name),
            )

        if docs_by_level[IndexLevel.MODULE]:
            module_docs: dict[str, list[Document]] = defaultdict(list)
            for doc in docs_by_level[IndexLevel.MODULE]:
                module_name = doc.metadata.get("module_name", "default")
                module_docs[module_name].append(doc)

            for module_name, docs in module_docs.items():
                key = f"{self._safe_name(project_name)}_{self._safe_name(module_name)}"
                if key in self._module_index:
                    self._module_index[key].add_documents(docs)
                else:
                    self._module_index[key] = FAISS.from_documents(docs, self._embeddings)
                self._save_index(
                    self._module_index[key],
                    self._get_module_index_dir(project_name, module_name),
                )

        if docs_by_level[IndexLevel.FILE]:
            file_docs = docs_by_level[IndexLevel.FILE]
            if self._file_index is None:
                self._file_index = FAISS.from_documents(file_docs, self._embeddings)
            else:
                self._file_index.add_documents(file_docs)
            self._save_index(self._file_index, self._get_file_index_dir())

        self._stats.total_documents = len(self._entries)
        self._stats.project_count = len(self._project_index)
        self._stats.module_count = len(self._module_index)
        self._stats.file_count = sum(
            1 for e in self._entries.values() if e.level == IndexLevel.FILE
        )
        self._stats.last_indexed = datetime.now()

        self._save_entries()

        return indexed_count

    async def index_module(
        self,
        project_name: str,
        module_name: str,
        documents: list[dict[str, Any]],
    ) -> int:
        """索引模块文档"""
        return await self.index_project(
            Path("."), project_name, documents
        )

    async def index_file(
        self,
        project_name: str,
        module_name: str,
        file_path: Path,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """索引单个文件"""
        doc_id = hashlib.md5(content.encode()).hexdigest()

        documents = [{
            "id": doc_id,
            "content": content,
            "level": "file",
            "metadata": {
                **(metadata or {}),
                "project_name": project_name,
                "module_name": module_name,
                "file_path": str(file_path),
            },
        }]

        await self.index_project(Path("."), project_name, documents)
        return doc_id

    async def remove_project(self, project_name: str) -> bool:
        """移除项目索引"""
        safe_name = self._safe_name(project_name)

        if safe_name in self._project_index:
            del self._project_index[safe_name]

        project_dir = self._get_project_index_dir(project_name)
        if project_dir.exists():
            import shutil
            shutil.rmtree(project_dir)

        for doc_id in self._project_entries.get(safe_name, []):
            if doc_id in self._entries:
                del self._entries[doc_id]

        if safe_name in self._project_entries:
            del self._project_entries[safe_name]

        keys_to_remove = [
            k for k in self._module_index.keys()
            if k.startswith(f"{safe_name}_")
        ]
        for key in keys_to_remove:
            del self._module_index[key]

        self._save_entries()
        return True

    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        level: Optional[IndexLevel] = None,
        project_name: Optional[str] = None,
    ) -> list[SearchResult]:
        """语义检索"""
        results = []

        if project_name:
            safe_name = self._safe_name(project_name)
            if safe_name in self._project_index:
                project_results = self._project_index[safe_name].similarity_search_with_score(
                    query, k=top_k
                )
                for doc, score in project_results:
                    doc_id = doc.metadata.get("doc_id", "")
                    entry = self._entries.get(doc_id)
                    if entry:
                        results.append(SearchResult(
                            content=doc.page_content,
                            score=float(score),
                            source=entry.file_path or entry.project_name,
                            level=entry.level,
                            metadata=entry.metadata,
                        ))
        else:
            if self._file_index:
                file_results = self._file_index.similarity_search_with_score(query, k=top_k)
                for doc, score in file_results:
                    doc_id = doc.metadata.get("doc_id", "")
                    entry = self._entries.get(doc_id)
                    if entry:
                        if level and entry.level != level:
                            continue
                        results.append(SearchResult(
                            content=doc.page_content,
                            score=float(score),
                            source=entry.file_path or entry.project_name,
                            level=entry.level,
                            metadata=entry.metadata,
                        ))

        results.sort(key=lambda x: x.score)
        return results[:top_k]

    async def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        level: Optional[IndexLevel] = None,
    ) -> list[SearchResult]:
        """关键词检索（基于简单的文本匹配）"""
        results = []
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        for entry in self._entries.values():
            if level and entry.level != level:
                continue

            content_lower = entry.content.lower()
            content_terms = set(content_lower.split())

            overlap = len(query_terms & content_terms)
            if overlap > 0:
                score = overlap / len(query_terms)
                results.append(SearchResult(
                    content=entry.content,
                    score=score,
                    source=entry.file_path or entry.project_name,
                    level=entry.level,
                    metadata=entry.metadata,
                ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    async def optimize(self) -> None:
        """优化索引"""
        pass

    async def clear(self) -> None:
        """清空索引"""
        self._project_index.clear()
        self._module_index.clear()
        self._file_index = None
        self._entries.clear()
        self._project_entries.clear()
        self._module_entries.clear()
        self._stats = IndexStats()
        self._save_entries()

    def get_stats(self) -> IndexStats:
        """获取索引统计"""
        return self._stats

    def get_project_names(self) -> list[str]:
        """获取所有项目名称"""
        return list(self._project_entries.keys())

    def get_module_names(self, project_name: str) -> list[str]:
        """获取项目的所有模块名称"""
        safe_name = self._safe_name(project_name)
        prefix = f"{safe_name}_"
        return [
            k[len(prefix):] for k in self._module_entries.keys()
            if k.startswith(prefix)
        ]
