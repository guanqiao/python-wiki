"""
全局记忆管理
存储用户级别的偏好、编码风格和技术栈偏好
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pywiki.memory.base import BaseMemory


@dataclass
class UserPreference:
    key: str
    value: Any
    category: str = "general"
    confidence: float = 1.0
    source: str = "explicit"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "access_count": self.access_count,
        }


@dataclass
class CodingStyle:
    indent_style: str = "space"
    indent_size: int = 4
    quote_style: str = "double"
    naming_convention: str = "snake_case"
    max_line_length: int = 100
    docstring_style: str = "google"
    import_order: str = "isort"
    type_hints: bool = True
    preferences: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "indent_style": self.indent_style,
            "indent_size": self.indent_size,
            "quote_style": self.quote_style,
            "naming_convention": self.naming_convention,
            "max_line_length": self.max_line_length,
            "docstring_style": self.docstring_style,
            "import_order": self.import_order,
            "type_hints": self.type_hints,
            "preferences": self.preferences,
        }


@dataclass
class TechStackPreference:
    language: str
    frameworks: list[str] = field(default_factory=list)
    libraries: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    version_preferences: dict[str, str] = field(default_factory=dict)
    expertise_level: str = "intermediate"
    last_used: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "frameworks": self.frameworks,
            "libraries": self.libraries,
            "tools": self.tools,
            "version_preferences": self.version_preferences,
            "expertise_level": self.expertise_level,
            "last_used": self.last_used.isoformat(),
        }


class GlobalMemory(BaseMemory):
    """
    全局记忆管理器
    存储用户级别的偏好和知识
    """

    def __init__(self, storage_path: Optional[Path] = None):
        super().__init__(storage_path or Path.home() / ".pywiki" / "global_memory")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._preferences: dict[str, UserPreference] = {}
        self._coding_style = CodingStyle()
        self._tech_stack: dict[str, TechStackPreference] = {}
        self._knowledge_base: dict[str, Any] = {}

        self._load()

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典"""
        return {
            "preferences": {k: v.to_dict() for k, v in self._preferences.items()},
            "coding_style": self._coding_style.to_dict(),
            "tech_stack": {k: v.to_dict() for k, v in self._tech_stack.items()},
            "knowledge": self._knowledge_base,
        }

    def from_dict(self, data: dict[str, Any]) -> "GlobalMemory":
        """从字典反序列化"""
        if "preferences" in data:
            for key, pref_data in data["preferences"].items():
                self._preferences[key] = UserPreference(
                    key=pref_data["key"],
                    value=pref_data["value"],
                    category=pref_data.get("category", "general"),
                    confidence=pref_data.get("confidence", 1.0),
                    source=pref_data.get("source", "explicit"),
                    created_at=datetime.fromisoformat(pref_data["created_at"]),
                    updated_at=datetime.fromisoformat(pref_data["updated_at"]),
                    access_count=pref_data.get("access_count", 0),
                )

        if "coding_style" in data:
            style_data = data["coding_style"]
            self._coding_style = CodingStyle(
                indent_style=style_data.get("indent_style", "space"),
                indent_size=style_data.get("indent_size", 4),
                quote_style=style_data.get("quote_style", "double"),
                naming_convention=style_data.get("naming_convention", "snake_case"),
                max_line_length=style_data.get("max_line_length", 100),
                docstring_style=style_data.get("docstring_style", "google"),
                import_order=style_data.get("import_order", "isort"),
                type_hints=style_data.get("type_hints", True),
                preferences=style_data.get("preferences", {}),
            )

        if "tech_stack" in data:
            for lang, ts_data in data["tech_stack"].items():
                self._tech_stack[lang] = TechStackPreference(
                    language=ts_data["language"],
                    frameworks=ts_data.get("frameworks", []),
                    libraries=ts_data.get("libraries", []),
                    tools=ts_data.get("tools", []),
                    version_preferences=ts_data.get("version_preferences", {}),
                    expertise_level=ts_data.get("expertise_level", "intermediate"),
                    last_used=datetime.fromisoformat(ts_data["last_used"])
                    if ts_data.get("last_used") else datetime.now(),
                )

        if "knowledge" in data:
            self._knowledge_base = data["knowledge"]

        return self

    def _get_preferences_path(self) -> Path:
        return self.storage_path / "preferences.json"

    def _get_style_path(self) -> Path:
        return self.storage_path / "coding_style.json"

    def _get_tech_stack_path(self) -> Path:
        return self.storage_path / "tech_stack.json"

    def _get_knowledge_path(self) -> Path:
        return self.storage_path / "knowledge.json"

    def _load(self) -> None:
        """加载全局记忆"""
        self._load_preferences()
        self._load_coding_style()
        self._load_tech_stack()
        self._load_knowledge()

    def _load_preferences(self) -> None:
        """加载偏好设置"""
        path = self._get_preferences_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, pref_data in data.items():
                        self._preferences[key] = UserPreference(
                            key=pref_data["key"],
                            value=pref_data["value"],
                            category=pref_data.get("category", "general"),
                            confidence=pref_data.get("confidence", 1.0),
                            source=pref_data.get("source", "explicit"),
                            created_at=datetime.fromisoformat(pref_data["created_at"]),
                            updated_at=datetime.fromisoformat(pref_data["updated_at"]),
                            access_count=pref_data.get("access_count", 0),
                        )
            except Exception:
                pass

    def _load_coding_style(self) -> None:
        """加载编码风格"""
        path = self._get_style_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._coding_style = CodingStyle(
                        indent_style=data.get("indent_style", "space"),
                        indent_size=data.get("indent_size", 4),
                        quote_style=data.get("quote_style", "double"),
                        naming_convention=data.get("naming_convention", "snake_case"),
                        max_line_length=data.get("max_line_length", 100),
                        docstring_style=data.get("docstring_style", "google"),
                        import_order=data.get("import_order", "isort"),
                        type_hints=data.get("type_hints", True),
                        preferences=data.get("preferences", {}),
                    )
            except Exception:
                pass

    def _load_tech_stack(self) -> None:
        """加载技术栈偏好"""
        path = self._get_tech_stack_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for lang, ts_data in data.items():
                        self._tech_stack[lang] = TechStackPreference(
                            language=ts_data["language"],
                            frameworks=ts_data.get("frameworks", []),
                            libraries=ts_data.get("libraries", []),
                            tools=ts_data.get("tools", []),
                            version_preferences=ts_data.get("version_preferences", {}),
                            expertise_level=ts_data.get("expertise_level", "intermediate"),
                            last_used=datetime.fromisoformat(ts_data["last_used"])
                            if ts_data.get("last_used") else datetime.now(),
                        )
            except Exception:
                pass

    def _load_knowledge(self) -> None:
        """加载知识库"""
        path = self._get_knowledge_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._knowledge_base = json.load(f)
            except Exception:
                pass

    def _save_preferences(self) -> None:
        """保存偏好设置"""
        path = self._get_preferences_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {k: v.to_dict() for k, v in self._preferences.items()},
                f,
                ensure_ascii=False,
                indent=2,
            )

    def _save_coding_style(self) -> None:
        """保存编码风格"""
        path = self._get_style_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._coding_style.to_dict(), f, ensure_ascii=False, indent=2)

    def _save_tech_stack(self) -> None:
        """保存技术栈偏好"""
        path = self._get_tech_stack_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {k: v.to_dict() for k, v in self._tech_stack.items()},
                f,
                ensure_ascii=False,
                indent=2,
            )

    def _save_knowledge(self) -> None:
        """保存知识库"""
        path = self._get_knowledge_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._knowledge_base, f, ensure_ascii=False, indent=2)

    def set_preference(
        self,
        key: str,
        value: Any,
        category: str = "general",
        source: str = "explicit",
        confidence: float = 1.0,
    ) -> None:
        """
        设置偏好

        Args:
            key: 偏好键
            value: 偏好值
            category: 分类
            source: 来源（explicit/learned/inferred）
            confidence: 置信度
        """
        now = datetime.now()
        if key in self._preferences:
            pref = self._preferences[key]
            pref.value = value
            pref.updated_at = now
            pref.confidence = confidence
            pref.source = source
        else:
            self._preferences[key] = UserPreference(
                key=key,
                value=value,
                category=category,
                source=source,
                confidence=confidence,
                created_at=now,
                updated_at=now,
            )
        self._save_preferences()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """获取偏好"""
        if key in self._preferences:
            pref = self._preferences[key]
            pref.access_count += 1
            self._save_preferences()
            return pref.value
        return default

    def get_all_preferences(self, category: Optional[str] = None) -> dict[str, Any]:
        """获取所有偏好"""
        if category:
            return {
                k: v.value for k, v in self._preferences.items()
                if v.category == category
            }
        return {k: v.value for k, v in self._preferences.items()}

    def update_coding_style(self, **kwargs: Any) -> None:
        """更新编码风格"""
        for key, value in kwargs.items():
            if hasattr(self._coding_style, key):
                setattr(self._coding_style, key, value)
            else:
                self._coding_style.preferences[key] = value
        self._save_coding_style()

    def get_coding_style(self) -> CodingStyle:
        """获取编码风格"""
        return self._coding_style

    def update_tech_stack(
        self,
        language: str,
        frameworks: Optional[list[str]] = None,
        libraries: Optional[list[str]] = None,
        tools: Optional[list[str]] = None,
        expertise_level: Optional[str] = None,
    ) -> None:
        """更新技术栈偏好"""
        if language in self._tech_stack:
            ts = self._tech_stack[language]
            if frameworks:
                ts.frameworks = list(set(ts.frameworks + frameworks))
            if libraries:
                ts.libraries = list(set(ts.libraries + libraries))
            if tools:
                ts.tools = list(set(ts.tools + tools))
            if expertise_level:
                ts.expertise_level = expertise_level
            ts.last_used = datetime.now()
        else:
            self._tech_stack[language] = TechStackPreference(
                language=language,
                frameworks=frameworks or [],
                libraries=libraries or [],
                tools=tools or [],
                expertise_level=expertise_level or "intermediate",
            )
        self._save_tech_stack()

    def get_tech_stack(self, language: Optional[str] = None) -> dict[str, Any]:
        """获取技术栈偏好"""
        if language:
            if language in self._tech_stack:
                return self._tech_stack[language].to_dict()
            return {}
        return {k: v.to_dict() for k, v in self._tech_stack.items()}

    def get_preferred_languages(self) -> list[str]:
        """获取偏好的语言列表（按使用时间排序）"""
        sorted_ts = sorted(
            self._tech_stack.items(),
            key=lambda x: x[1].last_used,
            reverse=True,
        )
        return [lang for lang, _ in sorted_ts]

    def add_knowledge(self, key: str, value: Any) -> None:
        """添加知识"""
        self._knowledge_base[key] = {
            "value": value,
            "created_at": datetime.now().isoformat(),
        }
        self._save_knowledge()

    def get_knowledge(self, key: str, default: Any = None) -> Any:
        """获取知识"""
        if key in self._knowledge_base:
            return self._knowledge_base[key]["value"]
        return default

    def get_all_knowledge(self) -> dict[str, Any]:
        """获取所有知识"""
        return {
            k: v["value"] for k, v in self._knowledge_base.items()
        }

    def export(self) -> dict[str, Any]:
        """导出全局记忆"""
        return {
            "preferences": {k: v.to_dict() for k, v in self._preferences.items()},
            "coding_style": self._coding_style.to_dict(),
            "tech_stack": {k: v.to_dict() for k, v in self._tech_stack.items()},
            "knowledge": self._knowledge_base,
            "exported_at": datetime.now().isoformat(),
        }

    def import_data(self, data: dict[str, Any]) -> None:
        """导入全局记忆"""
        if "preferences" in data:
            for key, pref_data in data["preferences"].items():
                self._preferences[key] = UserPreference(
                    key=pref_data["key"],
                    value=pref_data["value"],
                    category=pref_data.get("category", "general"),
                    confidence=pref_data.get("confidence", 1.0),
                    source=pref_data.get("source", "explicit"),
                    created_at=datetime.fromisoformat(pref_data["created_at"]),
                    updated_at=datetime.fromisoformat(pref_data["updated_at"]),
                    access_count=pref_data.get("access_count", 0),
                )
            self._save_preferences()

        if "coding_style" in data:
            style_data = data["coding_style"]
            self._coding_style = CodingStyle(
                indent_style=style_data.get("indent_style", "space"),
                indent_size=style_data.get("indent_size", 4),
                quote_style=style_data.get("quote_style", "double"),
                naming_convention=style_data.get("naming_convention", "snake_case"),
                max_line_length=style_data.get("max_line_length", 100),
                docstring_style=style_data.get("docstring_style", "google"),
                import_order=style_data.get("import_order", "isort"),
                type_hints=style_data.get("type_hints", True),
                preferences=style_data.get("preferences", {}),
            )
            self._save_coding_style()

        if "tech_stack" in data:
            for lang, ts_data in data["tech_stack"].items():
                self._tech_stack[lang] = TechStackPreference(
                    language=ts_data["language"],
                    frameworks=ts_data.get("frameworks", []),
                    libraries=ts_data.get("libraries", []),
                    tools=ts_data.get("tools", []),
                    version_preferences=ts_data.get("version_preferences", {}),
                    expertise_level=ts_data.get("expertise_level", "intermediate"),
                    last_used=datetime.fromisoformat(ts_data["last_used"])
                    if ts_data.get("last_used") else datetime.now(),
                )
            self._save_tech_stack()

        if "knowledge" in data:
            self._knowledge_base = data["knowledge"]
            self._save_knowledge()

    def clear(self) -> None:
        """清空全局记忆"""
        self._preferences.clear()
        self._coding_style = CodingStyle()
        self._tech_stack.clear()
        self._knowledge_base.clear()

        self._save_preferences()
        self._save_coding_style()
        self._save_tech_stack()
        self._save_knowledge()
