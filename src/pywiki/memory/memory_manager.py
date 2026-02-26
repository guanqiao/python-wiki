
"""
记忆管理器
统一管理全局记忆和项目记忆
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pywiki.memory.memory_entry import MemoryEntry, MemoryScope, MemoryCategory
from pywiki.memory.global_memory import GlobalMemory
from pywiki.memory.project_memory import ProjectMemory


class MemoryManager:
    """记忆管理器 - 统一管理双层记忆系统"""

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
    ):
        self.storage_dir = storage_dir or Path.home() / ".pywiki" / "memory"
        self.global_memory = GlobalMemory(self.storage_dir)
        self._project_memories: dict[str, ProjectMemory] = {}
        self._current_project: Optional[str] = None

    def set_current_project(self, project_name: str, project_path: Path) -&gt; ProjectMemory:
        """设置当前项目"""
        self._current_project = project_name
        if project_name not in self._project_memories:
            self._project_memories[project_name] = ProjectMemory(project_name, project_path)
        return self._project_memories[project_name]

    def get_current_project_memory(self) -&gt; Optional[ProjectMemory]:
        """获取当前项目记忆"""
        if self._current_project:
            return self._project_memories.get(self._current_project)
        return None

    def remember(
        self,
        key: str,
        value: Any,
        scope: MemoryScope = MemoryScope.GLOBAL,
        category: MemoryCategory = MemoryCategory.PREFERENCE,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -&gt; MemoryEntry:
        """记录记忆"""
        if scope == MemoryScope.GLOBAL:
            return self.global_memory.remember(key, value, category, description, tags)
        else:
            project_memory = self.get_current_project_memory()
            if project_memory:
                return project_memory.remember(key, value, category, description, tags)
            raise ValueError("No current project set for project-scoped memory")

    def recall(
        self,
        key: str,
        scope: Optional[MemoryScope] = None,
    ) -&gt; Optional[Any]:
        """回忆记忆 - 项目记忆优先"""
        if scope == MemoryScope.GLOBAL:
            return self.global_memory.recall(key)
        elif scope == MemoryScope.PROJECT:
            project_memory = self.get_current_project_memory()
            if project_memory:
                return project_memory.recall(key)
            return None
        else:
            project_memory = self.get_current_project_memory()
            if project_memory:
                value = project_memory.recall(key)
                if value is not None:
                    return value
            return self.global_memory.recall(key)

    def recall_entry(
        self,
        key: str,
        scope: Optional[MemoryScope] = None,
    ) -&gt; Optional[MemoryEntry]:
        """回忆记忆条目"""
        if scope == MemoryScope.GLOBAL:
            return self.global_memory.recall_entry(key)
        elif scope == MemoryScope.PROJECT:
            project_memory = self.get_current_project_memory()
            if project_memory:
                return project_memory.recall_entry(key)
            return None
        else:
            project_memory = self.get_current_project_memory()
            if project_memory:
                entry = project_memory.recall_entry(key)
                if entry:
                    return entry
            return self.global_memory.recall_entry(key)

    def forget(
        self,
        key: str,
        scope: Optional[MemoryScope] = None,
    ) -&gt; bool:
        """遗忘记忆"""
        if scope == MemoryScope.GLOBAL:
            return self.global_memory.forget(key)
        elif scope == MemoryScope.PROJECT:
            project_memory = self.get_current_project_memory()
            if project_memory:
                return project_memory.forget(key)
            return False
        else:
            project_memory = self.get_current_project_memory()
            if project_memory and project_memory.forget(key):
                return True
            return self.global_memory.forget(key)

    def search(
        self,
        query: str,
        scope: Optional[MemoryScope] = None,
    ) -&gt; list[MemoryEntry]:
        """搜索记忆"""
        if scope == MemoryScope.GLOBAL:
            return self.global_memory.search(query)
        elif scope == MemoryScope.PROJECT:
            project_memory = self.get_current_project_memory()
            if project_memory:
                return project_memory.search(query)
            return []
        else:
            results = []
            project_memory = self.get_current_project_memory()
            if project_memory:
                results.extend(project_memory.search(query))
            results.extend(self.global_memory.search(query))
            return results

    def get_all_context(self) -&gt; dict:
        """获取所有上下文记忆"""
        context = {
            "global": {},
            "project": {},
        }

        for entry in self.global_memory.list_memories():
            context["global"][entry.key] = entry.value

        project_memory = self.get_current_project_memory()
        if project_memory:
            for entry in project_memory.list_memories():
                context["project"][entry.key] = entry.value

        return context

    def get_merged_preferences(self) -&gt; dict:
        """获取合并后的偏好（项目优先）"""
        preferences = {}

        for entry in self.global_memory.list_memories():
            preferences[entry.key] = entry.value

        project_memory = self.get_current_project_memory()
        if project_memory:
            for entry in project_memory.list_memories():
                preferences[entry.key] = entry.value

        return preferences

    def get_coding_style(self) -&gt; dict:
        """获取编码风格（合并全局和项目）"""
        global_style = self.global_memory.get_coding_style()
        project_memory = self.get_current_project_memory()

        if project_memory:
            project_style = {}
            for entry in project_memory.list_memories(category=MemoryCategory.CODING_STYLE):
                project_style[entry.key] = entry.value
            global_style.update(project_style)

        return global_style

    def get_tech_stack(self) -&gt; dict:
        """获取技术栈信息"""
        tech_stack = {}

        for entry in self.global_memory.list_memories(category=MemoryCategory.TECH_STACK):
            tech_stack[entry.key] = entry.value

        project_memory = self.get_current_project_memory()
        if project_memory:
            for entry in project_memory.list_memories(category=MemoryCategory.TECH_STACK):
                tech_stack[entry.key] = entry.value

        return tech_stack

    def learn_from_interaction(
        self,
        interaction_type: str,
        content: dict,
    ) -&gt; Optional[MemoryEntry]:
        """从交互中学习"""
        if interaction_type == "code_style":
            return self._learn_code_style(content)
        elif interaction_type == "tech_choice":
            return self._learn_tech_choice(content)
        elif interaction_type == "problem_solution":
            return self._learn_problem_solution(content)
        elif interaction_type == "preference":
            return self._learn_preference(content)
        return None

    def _learn_code_style(self, content: dict) -&gt; MemoryEntry:
        """学习编码风格"""
        style_name = content.get("name", "")
        style_value = content.get("value")
        scope = MemoryScope.GLOBAL

        if content.get("project_specific"):
            scope = MemoryScope.PROJECT

        return self.remember(
            f"style.{style_name}",
            style_value,
            scope=scope,
            category=MemoryCategory.CODING_STYLE,
            description=f"编码风格偏好: {style_name}",
            tags=["coding_style", "learned"],
        )

    def _learn_tech_choice(self, content: dict) -&gt; MemoryEntry:
        """学习技术选择"""
        tech_name = content.get("name", "")
        tech_value = content.get("value")
        reason = content.get("reason", "")

        return self.remember(
            f"tech.{tech_name}",
            {"choice": tech_value, "reason": reason},
            scope=MemoryScope.PROJECT,
            category=MemoryCategory.TECH_STACK,
            description=f"技术选择: {tech_name}",
            tags=["tech_stack", "learned"],
        )

    def _learn_problem_solution(self, content: dict) -&gt; Optional[MemoryEntry]:
        """学习问题解决方案"""
        project_memory = self.get_current_project_memory()
        if not project_memory:
            return None

        return project_memory.record_problem_solution(
            problem=content.get("problem", ""),
            solution=content.get("solution", ""),
            context=content.get("context"),
        )

    def _learn_preference(self, content: dict) -&gt; MemoryEntry:
        """学习偏好"""
        key = content.get("key", "")
        value = content.get("value")
        scope = MemoryScope.GLOBAL if content.get("global", True) else MemoryScope.PROJECT

        return self.remember(
            key,
            value,
            scope=scope,
            category=MemoryCategory.PREFERENCE,
            description=content.get("description"),
            tags=content.get("tags", []),
        )

    def export_all(self) -&gt; dict:
        """导出所有记忆"""
        data = {
            "global": self.global_memory.export_memories(),
            "projects": {},
        }

        for project_name, project_memory in self._project_memories.items():
            data["projects"][project_name] = project_memory.export_memories()

        return data

    def import_all(self, data: dict) -&gt; dict:
        """导入记忆"""
        result = {
            "global": 0,
            "projects": {},
        }

        if "global" in data:
            result["global"] = self.global_memory.import_memories(data["global"])

        if "projects" in data:
            for project_name, project_data in data["projects"].items():
                if project_name in self._project_memories:
                    count = self._project_memories[project_name].import_memories(project_data)
                    result["projects"][project_name] = count

        return result

    def get_statistics(self) -&gt; dict:
        """获取记忆统计"""
        stats = {
            "global": {
                "total": len(self.global_memory.list_memories()),
                "by_category": {},
            },
            "current_project": None,
        }

        for entry in self.global_memory.list_memories():
            cat = entry.category.value
            stats["global"]["by_category"][cat] = stats["global"]["by_category"].get(cat, 0) + 1

        project_memory = self.get_current_project_memory()
        if project_memory:
            summary = project_memory.get_summary()
            stats["current_project"] = summary

        return stats
