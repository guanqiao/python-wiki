"""
记忆优先级处理器
管理记忆的优先级、衰减和访问排序
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional


class MemoryPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    ARCHIVED = "archived"


@dataclass
class MemoryItem:
    key: str
    value: Any
    priority: MemoryPriority = MemoryPriority.NORMAL
    importance: float = 1.0
    access_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    tags: list[str] = field(default_factory=list)
    source: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "priority": self.priority.value,
            "importance": self.importance,
            "access_count": self.access_count,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "tags": self.tags,
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass
class PrioritizationConfig:
    decay_rate: float = 0.1
    access_boost: float = 0.2
    importance_weight: float = 0.4
    recency_weight: float = 0.3
    access_weight: float = 0.3
    archive_threshold: float = 0.1
    critical_threshold: float = 0.8


class MemoryPrioritizer:
    """
    记忆优先级处理器
    管理记忆的优先级、衰减和排序
    """

    def __init__(self, config: Optional[PrioritizationConfig] = None):
        self.config = config or PrioritizationConfig()
        self._memories: dict[str, MemoryItem] = {}

    def add_memory(
        self,
        key: str,
        value: Any,
        priority: MemoryPriority = MemoryPriority.NORMAL,
        importance: float = 1.0,
        tags: Optional[list[str]] = None,
        source: str = "unknown",
        ttl_hours: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> MemoryItem:
        """
        添加记忆

        Args:
            key: 记忆键
            value: 记忆值
            priority: 优先级
            importance: 重要性（0-1）
            tags: 标签列表
            source: 来源
            ttl_hours: 存活时间（小时）
            metadata: 元数据

        Returns:
            创建的记忆项
        """
        now = datetime.now()
        expires_at = None
        if ttl_hours:
            expires_at = now + timedelta(hours=ttl_hours)

        item = MemoryItem(
            key=key,
            value=value,
            priority=priority,
            importance=importance,
            tags=tags or [],
            source=source,
            expires_at=expires_at,
            metadata=metadata or {},
        )

        self._memories[key] = item
        return item

    def get_memory(self, key: str) -> Optional[MemoryItem]:
        """获取记忆并更新访问信息"""
        if key not in self._memories:
            return None

        item = self._memories[key]

        if item.expires_at and datetime.now() > item.expires_at:
            del self._memories[key]
            return None

        item.access_count += 1
        item.last_accessed = datetime.now()

        item.importance = min(1.0, item.importance + self.config.access_boost)

        return item

    def update_priority(self, key: str, priority: MemoryPriority) -> bool:
        """更新优先级"""
        if key not in self._memories:
            return False

        self._memories[key].priority = priority
        return True

    def update_importance(self, key: str, importance: float) -> bool:
        """更新重要性"""
        if key not in self._memories:
            return False

        self._memories[key].importance = max(0.0, min(1.0, importance))
        return True

    def calculate_score(self, item: MemoryItem) -> float:
        """
        计算记忆的综合得分

        Args:
            item: 记忆项

        Returns:
            综合得分（0-1）
        """
        now = datetime.now()

        age_hours = (now - item.created_at).total_seconds() / 3600
        recency_score = math.exp(-self.config.decay_rate * age_hours)

        access_score = min(1.0, item.access_count / 10)

        priority_scores = {
            MemoryPriority.CRITICAL: 1.0,
            MemoryPriority.HIGH: 0.8,
            MemoryPriority.NORMAL: 0.5,
            MemoryPriority.LOW: 0.3,
            MemoryPriority.ARCHIVED: 0.1,
        }
        priority_score = priority_scores.get(item.priority, 0.5)

        score = (
            self.config.importance_weight * item.importance +
            self.config.recency_weight * recency_score +
            self.config.access_weight * access_score
        ) * priority_score

        return min(1.0, score)

    def get_sorted_memories(
        self,
        limit: int = 100,
        min_score: float = 0.0,
        tags: Optional[list[str]] = None,
        priority: Optional[MemoryPriority] = None,
    ) -> list[MemoryItem]:
        """
        获取排序后的记忆

        Args:
            limit: 返回数量限制
            min_score: 最小得分
            tags: 过滤标签
            priority: 过滤优先级

        Returns:
            排序后的记忆列表
        """
        items = list(self._memories.values())

        if tags:
            items = [
                item for item in items
                if any(tag in item.tags for tag in tags)
            ]

        if priority:
            items = [item for item in items if item.priority == priority]

        items_with_scores = [
            (item, self.calculate_score(item))
            for item in items
        ]

        items_with_scores = [
            (item, score) for item, score in items_with_scores
            if score >= min_score
        ]

        items_with_scores.sort(key=lambda x: x[1], reverse=True)

        return [item for item, _ in items_with_scores[:limit]]

    def apply_decay(self) -> int:
        """
        应用衰减

        Returns:
            衰减后的记忆数量
        """
        now = datetime.now()
        keys_to_remove = []

        for key, item in self._memories.items():
            if item.expires_at and now > item.expires_at:
                keys_to_remove.append(key)
                continue

            hours_since_access = (now - item.last_accessed).total_seconds() / 3600
            decay = math.exp(-self.config.decay_rate * hours_since_access)
            item.importance = max(0.0, item.importance * decay)

            if item.importance < self.config.archive_threshold:
                if item.priority != MemoryPriority.ARCHIVED:
                    item.priority = MemoryPriority.ARCHIVED

        for key in keys_to_remove:
            del self._memories[key]

        return len(self._memories)

    def promote_memories(self, threshold: float = 0.8) -> int:
        """
        提升高得分记忆的优先级

        Args:
            threshold: 提升阈值

        Returns:
            提升的记忆数量
        """
        promoted = 0

        for item in self._memories.values():
            score = self.calculate_score(item)

            if score >= threshold and item.priority not in (
                MemoryPriority.CRITICAL,
                MemoryPriority.HIGH,
            ):
                if item.priority == MemoryPriority.ARCHIVED:
                    item.priority = MemoryPriority.NORMAL
                elif item.priority == MemoryPriority.LOW:
                    item.priority = MemoryPriority.NORMAL
                elif item.priority == MemoryPriority.NORMAL:
                    item.priority = MemoryPriority.HIGH
                promoted += 1

        return promoted

    def cleanup_expired(self) -> int:
        """
        清理过期记忆

        Returns:
            清理的记忆数量
        """
        now = datetime.now()
        expired_keys = [
            key for key, item in self._memories.items()
            if item.expires_at and now > item.expires_at
        ]

        for key in expired_keys:
            del self._memories[key]

        return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        priority_counts: dict[str, int] = {}
        total_importance = 0.0
        total_access = 0

        for item in self._memories.values():
            priority_key = item.priority.value
            priority_counts[priority_key] = priority_counts.get(priority_key, 0) + 1
            total_importance += item.importance
            total_access += item.access_count

        count = len(self._memories)

        return {
            "total_memories": count,
            "by_priority": priority_counts,
            "avg_importance": total_importance / count if count > 0 else 0,
            "total_access_count": total_access,
            "avg_access_count": total_access / count if count > 0 else 0,
        }

    def export_memories(self) -> list[dict[str, Any]]:
        """导出所有记忆"""
        return [item.to_dict() for item in self._memories.values()]

    def clear(self) -> None:
        """清空所有记忆"""
        self._memories.clear()
