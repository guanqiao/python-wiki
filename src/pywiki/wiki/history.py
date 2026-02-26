"""
Wiki 版本历史
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class WikiHistory:
    """Wiki 文档版本历史管理"""

    def __init__(self, history_dir: Path):
        self.history_dir = history_dir
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self._history_file = history_dir / "history.json"
        self._history: dict = self._load_history()

    def _load_history(self) -> dict:
        if self._history_file.exists():
            with open(self._history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"versions": {}}

    def _save_history(self) -> None:
        with open(self._history_file, "w", encoding="utf-8") as f:
            json.dump(self._history, f, indent=2, ensure_ascii=False)

    def record_version(
        self,
        doc_path: Path,
        content: str,
        message: str = "",
        author: str = "system",
    ) -> str:
        """记录新版本"""
        from hashlib import md5

        content_hash = md5(content.encode()).hexdigest()
        timestamp = datetime.now().isoformat()
        version_id = f"v_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        doc_key = str(doc_path)
        if doc_key not in self._history["versions"]:
            self._history["versions"][doc_key] = []

        version = {
            "id": version_id,
            "timestamp": timestamp,
            "hash": content_hash,
            "message": message,
            "author": author,
        }

        self._history["versions"][doc_key].append(version)
        self._save_history()

        version_file = self.history_dir / f"{version_id}.md"
        version_file.write_text(content, encoding="utf-8")

        return version_id

    def get_history(self, doc_path: Path) -> list[dict]:
        """获取文档历史"""
        doc_key = str(doc_path)
        return self._history["versions"].get(doc_key, [])

    def get_version(self, version_id: str) -> Optional[str]:
        """获取特定版本内容"""
        version_file = self.history_dir / f"{version_id}.md"
        if version_file.exists():
            return version_file.read_text(encoding="utf-8")
        return None

    def restore_version(self, doc_path: Path, version_id: str) -> bool:
        """恢复到特定版本"""
        content = self.get_version(version_id)
        if content:
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            doc_path.write_text(content, encoding="utf-8")
            return True
        return False

    def compare_versions(
        self,
        version_id1: str,
        version_id2: str
    ) -> dict:
        """比较两个版本"""
        content1 = self.get_version(version_id1)
        content2 = self.get_version(version_id2)

        if not content1 or not content2:
            return {"error": "Version not found"}

        lines1 = content1.split("\n")
        lines2 = content2.split("\n")

        diff = []
        max_lines = max(len(lines1), len(lines2))

        for i in range(max_lines):
            line1 = lines1[i] if i < len(lines1) else None
            line2 = lines2[i] if i < len(lines2) else None

            if line1 != line2:
                diff.append({
                    "line": i + 1,
                    "old": line1,
                    "new": line2,
                })

        return {
            "version1": version_id1,
            "version2": version_id2,
            "diff": diff,
        }

    def cleanup_old_versions(self, keep_count: int = 10) -> int:
        """清理旧版本，保留最近的 N 个"""
        deleted_count = 0

        for doc_key, versions in self._history["versions"].items():
            if len(versions) > keep_count:
                versions_to_delete = versions[:-keep_count]
                for version in versions_to_delete:
                    version_file = self.history_dir / f"{version['id']}.md"
                    if version_file.exists():
                        version_file.unlink()
                        deleted_count += 1

                self._history["versions"][doc_key] = versions[-keep_count:]

        self._save_history()
        return deleted_count
