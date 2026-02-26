"""
记忆条目定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class MemoryScope(str, Enum):
    GLOBAL = "global"
    PROJECT = "project"


class MemoryCategory(str, Enum):
    CODING_STYLE = "coding_style"
    TECH_STACK = "tech_stack"
    PREFERENCE = "preference"
    BUSINESS_RULE = "business_rule"
    ARCHITECTURE = "architecture"
    CONVENTION = "convention"
    PROBLEM_SOLUTION = "problem_solution"
    TEAM_GUIDELINE = "team_guideline"


@dataclass
class MemoryEntry:
    id: str
    scope: MemoryScope
    category: MemoryCategory
    key: str
    value: Any
    description: Optional[str] = None
    project_name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    confidence: float = 1.0
    source: str = "user"
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def access(self) -> None:
        self.access_count += 1
        self.last_accessed = datetime.now()

    def update(self, value: Any, description: Optional[str] = None) -> None:
        self.value = value
        if description:
            self.description = description
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "scope": self.scope.value,
            "category": self.category.value,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "project_name": self.project_name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "confidence": self.confidence,
            "source": self.source,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryEntry":
        return cls(
            id=data["id"],
            scope=MemoryScope(data["scope"]),
            category=MemoryCategory(data["category"]),
            key=data["key"],
            value=data["value"],
            description=data.get("description"),
            project_name=data.get("project_name"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None,
            confidence=data.get("confidence", 1.0),
            source=data.get("source", "user"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )
