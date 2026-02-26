"""
项目特定记忆管理
存储项目级别的架构、业务规则、团队约定等
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import uuid

from pywiki.memory.memory_entry import MemoryEntry, MemoryScope, MemoryCategory


class ProjectMemory:
    """项目特定记忆管理器"""

    def __init__(self, project_name: str, project_path: Path):
        self.project_name = project_name
        self.project_path = project_path
        self.storage_dir = project_path / ".pywiki" / "memory"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.storage_file = self.storage_dir / "project_memory.json"
        self._memories: dict[str, MemoryEntry] = {}
        self._load()

    def _load(self) -> None:
        if self.storage_file.exists():
            with open(self.storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for entry_data in data.get("memories", []):
                entry = MemoryEntry.from_dict(entry_data)
                self._memories[entry.id] = entry

    def _save(self) -> None:
        data = {
            "project_name": self.project_name,
            "memories": [m.to_dict() for m in self._memories.values()],
            "updated_at": datetime.now().isoformat(),
        }
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def remember(
        self,
        key: str,
        value: Any,
        category: MemoryCategory = MemoryCategory.BUSINESS_RULE,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        source: str = "user",
    ) -> MemoryEntry:
        """记录项目记忆"""
        existing = self._find_by_key(key)
        if existing:
            existing.update(value, description)
            self._save()
            return existing

        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            scope=MemoryScope.PROJECT,
            category=category,
            key=key,
            value=value,
            description=description,
            project_name=self.project_name,
            tags=tags or [],
            source=source,
        )

        self._memories[entry.id] = entry
        self._save()
        return entry

    def recall(self, key: str) -> Optional[Any]:
        """回忆项目记忆"""
        entry = self._find_by_key(key)
        if entry:
            entry.access()
            self._save()
            return entry.value
        return None

    def recall_entry(self, key: str) -> Optional[MemoryEntry]:
        """回忆记忆条目"""
        entry = self._find_by_key(key)
        if entry:
            entry.access()
            self._save()
        return entry

    def forget(self, key: str) -> bool:
        """遗忘项目记忆"""
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
    ) -> list[MemoryEntry]:
        """列出项目记忆"""
        memories = list(self._memories.values())

        if category:
            memories = [m for m in memories if m.category == category]

        if tags:
            memories = [m for m in memories if any(t in m.tags for t in tags)]

        return sorted(memories, key=lambda m: m.updated_at, reverse=True)

    def search(self, query: str) -> list[MemoryEntry]:
        """搜索项目记忆"""
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

    def _find_by_key(self, key: str) -> Optional[MemoryEntry]:
        for entry in self._memories.values():
            if entry.key == key:
                return entry
        return None

    def get_architecture_info(self) -> dict:
        """获取架构信息"""
        arch_memories = self.list_memories(category=MemoryCategory.ARCHITECTURE)
        return {m.key: m.value for m in arch_memories}

    def get_business_rules(self) -> dict:
        """获取业务规则"""
        rule_memories = self.list_memories(category=MemoryCategory.BUSINESS_RULE)
        return {m.key: m.value for m in rule_memories}

    def get_team_guidelines(self) -> dict:
        """获取团队约定"""
        guideline_memories = self.list_memories(category=MemoryCategory.TEAM_GUIDELINE)
        return {m.key: m.value for m in guideline_memories}

    def set_architecture_info(self, key: str, value: Any, description: Optional[str] = None) -> None:
        """设置架构信息"""
        self.remember(
            f"arch.{key}",
            value,
            category=MemoryCategory.ARCHITECTURE,
            description=description,
            tags=["architecture"],
        )

    def set_business_rule(self, key: str, value: Any, description: Optional[str] = None) -> None:
        """设置业务规则"""
        self.remember(
            f"rule.{key}",
            value,
            category=MemoryCategory.BUSINESS_RULE,
            description=description,
            tags=["business_rule"],
        )

    def set_team_guideline(self, key: str, value: Any, description: Optional[str] = None) -> None:
        """设置团队约定"""
        self.remember(
            f"guideline.{key}",
            value,
            category=MemoryCategory.TEAM_GUIDELINE,
            description=description,
            tags=["team_guideline"],
        )

    def record_problem_solution(
        self,
        problem: str,
        solution: str,
        context: Optional[str] = None,
    ) -> MemoryEntry:
        """记录问题解决方案"""
        return self.remember(
            f"solution.{problem}",
            {
                "problem": problem,
                "solution": solution,
                "context": context,
            },
            category=MemoryCategory.PROBLEM_SOLUTION,
            description=f"问题: {problem}",
            tags=["problem", "solution"],
            source="interaction",
        )

    def find_similar_solutions(self, problem: str) -> list[MemoryEntry]:
        """查找类似问题的解决方案"""
        solutions = self.list_memories(category=MemoryCategory.PROBLEM_SOLUTION)
        problem_lower = problem.lower()

        similar = []
        for entry in solutions:
            if problem_lower in entry.key.lower() or problem_lower in str(entry.value).lower():
                similar.append(entry)

        return similar

    def export_memories(self) -> dict:
        """导出项目记忆"""
        return {
            "project_name": self.project_name,
            "memories": [m.to_dict() for m in self._memories.values()],
            "exported_at": datetime.now().isoformat(),
        }

    def import_memories(self, data: dict) -> int:
        """导入项目记忆"""
        count = 0
        for entry_data in data.get("memories", []):
            entry = MemoryEntry.from_dict(entry_data)
            if entry.id not in self._memories:
                self._memories[entry.id] = entry
                count += 1
        self._save()
        return count

    def clear(self) -> None:
        """清除所有项目记忆"""
        self._memories.clear()
        self._save()

    def get_summary(self) -> dict:
        """获取记忆摘要"""
        categories = {}
        for entry in self._memories.values():
            cat = entry.category.value
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "project_name": self.project_name,
            "total_memories": len(self._memories),
            "by_category": categories,
            "last_updated": max(
                (m.updated_at for m in self._memories.values()),
                default=datetime.now()
            ).isoformat(),
        }
