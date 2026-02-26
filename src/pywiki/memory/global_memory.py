
"""
全局记忆管理
存储用户级别的偏好和设置
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import uuid

from pywiki.memory.memory_entry import MemoryEntry, MemoryScope, MemoryCategory


class GlobalMemory:
    """全局记忆管理器"""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".pywiki" / "memory"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.storage_file = self.storage_dir / "global_memory.json"
        self._memories: dict[str, MemoryEntry] = {}
        self._load()

    def _load(self) -&gt; None:
        if self.storage_file.exists():
            with open(self.storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for entry_data in data.get("memories", []):
                entry = MemoryEntry.from_dict(entry_data)
                self._memories[entry.id] = entry

    def _save(self) -&gt; None:
        data = {
            "memories": [m.to_dict() for m in self._memories.values()],
            "updated_at": datetime.now().isoformat(),
        }
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def remember(
        self,
        key: str,
        value: Any,
        category: MemoryCategory = MemoryCategory.PREFERENCE,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -&gt; MemoryEntry:
        """记录全局记忆"""
        existing = self._find_by_key(key)
        if existing:
            existing.update(value, description)
            self._save()
            return existing

        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            scope=MemoryScope.GLOBAL,
            category=category,
            key=key,
            value=value,
            description=description,
            tags=tags or [],
        )

        self._memories[entry.id] = entry
        self._save()
        return entry

    def recall(self, key: str) -&gt; Optional[Any]:
        """回忆全局记忆"""
        entry = self._find_by_key(key)
        if entry:
            entry.access()
            self._save()
            return entry.value
        return None

    def recall_entry(self, key: str) -&gt; Optional[MemoryEntry]:
        """回忆记忆条目"""
        entry = self._find_by_key(key)
        if entry:
            entry.access()
            self._save()
        return entry

    def forget(self, key: str) -&gt; bool:
        """遗忘全局记忆"""
        entry = self._find_by_key(key)
        if entry:
            del self._memories[entry.id]
            self._save()
            return True
        return False

    def list_memories(
        self,
        category: Optional[MemoryCategory] = None,
        tags: Optional[list[str]] = None,
    ) -&gt; list[MemoryEntry]:
        """列出记忆"""
        memories = list(self._memories.values())

        if category:
            memories = [m for m in memories if m.category == category]

        if tags:
            memories = [m for m in memories if any(t in m.tags for t in tags)]

        return sorted(memories, key=lambda m: m.updated_at, reverse=True)

    def search(self, query: str) -&gt; list[MemoryEntry]:
        """搜索记忆"""
        query_lower = query.lower()
        results = []

        for entry in self._memories.values():
            if (
                query_lower in entry.key.lower()
                or query_lower in str(entry.value).lower()
                or (entry.description and query_lower in entry.description.lower())
            ):
                results.append(entry)

        return sorted(results, key=lambda m: m.access_count, reverse=True)

    def _find_by_key(self, key: str) -&gt; Optional[MemoryEntry]:
        for entry in self._memories.values():
            if entry.key == key:
                return entry
        return None

    def get_coding_style(self) -&gt; dict:
        """获取编码风格偏好"""
        style_memories = self.list_memories(category=MemoryCategory.CODING_STYLE)
        return {m.key: m.value for m in style_memories}

    def get_tech_preferences(self) -&gt; dict:
        """获取技术栈偏好"""
        tech_memories = self.list_memories(category=MemoryCategory.TECH_STACK)
        return {m.key: m.value for m in tech_memories}

    def set_coding_style(self, style_name: str, value: Any) -&gt; None:
        """设置编码风格偏好"""
        self.remember(
            f"style.{style_name}",
            value,
            category=MemoryCategory.CODING_STYLE,
            description=f"编码风格偏好: {style_name}",
            tags=["coding_style", "preference"],
        )

    def set_tech_preference(self, tech_name: str, value: Any) -&gt; None:
        """设置技术栈偏好"""
        self.remember(
            f"tech.{tech_name}",
            value,
            category=MemoryCategory.TECH_STACK,
            description=f"技术栈偏好: {tech_name}",
            tags=["tech_stack", "preference"],
        )

    def export_memories(self) -&gt; dict:
        """导出所有记忆"""
        return {
            "memories": [m.to_dict() for m in self._memories.values()],
            "exported_at": datetime.now().isoformat(),
        }

    def import_memories(self, data: dict) -&gt; int:
        """导入记忆"""
        count = 0
        for entry_data in data.get("memories", []):
            entry = MemoryEntry.from_dict(entry_data)
            if entry.id not in self._memories:
                self._memories[entry.id] = entry
                count += 1
        self._save()
        return count

    def clear(self) -&gt; None:
        """清除所有记忆"""
        self._memories.clear()
        self._save()
