"""
Wiki 存储服务
"""

import hashlib
import json
from pathlib import Path
from typing import Optional

from pywiki.config.models import Language


class WikiStorage:
    """Wiki 文档存储服务"""

    def __init__(
        self,
        output_dir: Path,
        language: Language = Language.ZH,
    ):
        self.output_dir = output_dir
        if isinstance(language, str):
            self.language = Language(language)
        else:
            self.language = language
        self.language_dir = output_dir / self.language.value
        self.history_dir = output_dir / ".history"
        self.index_file = output_dir / ".index.json"

        self._ensure_directories()
        self._index: dict = self._load_index()

    def _ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.language_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> dict:
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"documents": {}, "last_updated": None}

    def _save_index(self) -> None:
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self._index, f, indent=2, ensure_ascii=False)

    def get_module_path(self, module_name: str) -> Path:
        """获取模块文档路径"""
        return self.language_dir / "modules" / f"{module_name.replace('.', '/')}.md"

    async def save_document(self, doc_path: Path, content: str) -> None:
        """保存文档"""
        doc_path.parent.mkdir(parents=True, exist_ok=True)

        if doc_path.exists():
            old_content = doc_path.read_text(encoding="utf-8")
            if old_content != content:
                self._save_history(doc_path, old_content)

        doc_path.write_text(content, encoding="utf-8")

        content_hash = hashlib.md5(content.encode()).hexdigest()
        self._index["documents"][str(doc_path.relative_to(self.output_dir))] = {
            "hash": content_hash,
            "updated_at": str(doc_path.stat().st_mtime),
        }
        self._save_index()

    def _save_history(self, doc_path: Path, content: str) -> None:
        """保存历史版本"""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        history_file = self.history_dir / f"{doc_path.stem}_{timestamp}.md"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        history_file.write_text(content, encoding="utf-8")

    def get_document(self, doc_path: Path) -> Optional[str]:
        """获取文档内容"""
        if doc_path.exists():
            return doc_path.read_text(encoding="utf-8")
        return None

    def delete_document(self, doc_path: Path) -> bool:
        """删除文档"""
        if doc_path.exists():
            doc_path.unlink()
            rel_path = str(doc_path.relative_to(self.output_dir))
            if rel_path in self._index["documents"]:
                del self._index["documents"][rel_path]
                self._save_index()
            return True
        return False

    def list_documents(self) -> list[Path]:
        """列出所有文档"""
        documents = []
        for md_file in self.language_dir.rglob("*.md"):
            documents.append(md_file)
        return documents

    def search(self, query: str) -> list[dict]:
        """搜索文档内容"""
        results = []
        query_lower = query.lower()

        for doc_path in self.list_documents():
            content = self.get_document(doc_path)
            if content and query_lower in content.lower():
                lines = content.split("\n")
                matches = []
                for i, line in enumerate(lines):
                    if query_lower in line.lower():
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)
                        context = "\n".join(lines[start:end])
                        matches.append({
                            "line": i + 1,
                            "context": context,
                        })

                results.append({
                    "path": str(doc_path.relative_to(self.output_dir)),
                    "matches": matches,
                })

        return results

    def get_document_hash(self, doc_path: Path) -> Optional[str]:
        """获取文档哈希"""
        rel_path = str(doc_path.relative_to(self.output_dir))
        if rel_path in self._index["documents"]:
            return self._index["documents"][rel_path].get("hash")
        return None

    def is_document_changed(self, doc_path: Path, content: str) -> bool:
        """检查文档是否已更改"""
        current_hash = hashlib.md5(content.encode()).hexdigest()
        stored_hash = self.get_document_hash(doc_path)
        return current_hash != stored_hash
