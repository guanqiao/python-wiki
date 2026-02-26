"""
搜索缓存系统
LRU 缓存实现
"""

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, Optional

from pywiki.search.engine import SearchResult


@dataclass
class CacheEntry:
    key: str
    results: list[SearchResult]
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    def touch(self) -> None:
        self.access_count += 1
        self.last_accessed = time.time()


class SearchCache:
    """
    LRU 搜索缓存
    线程安全的缓存实现
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()

        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }

    def _generate_key(self, query: str, **kwargs) -> str:
        """生成缓存键"""
        key_data = f"{query}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, key: str) -> Optional[list[SearchResult]]:
        """
        获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存的结果列表，如果不存在或过期则返回 None
        """
        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None

            entry = self._cache[key]

            if self._is_expired(entry):
                del self._cache[key]
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                return None

            self._cache.move_to_end(key)
            entry.touch()
            self._stats["hits"] += 1

            return entry.results

    def set(self, key: str, results: list[SearchResult]) -> None:
        """
        设置缓存

        Args:
            key: 缓存键
            results: 搜索结果列表
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]

            if len(self._cache) >= self.max_size:
                self._evict()

            self._cache[key] = CacheEntry(
                key=key,
                results=results,
            )

    def _is_expired(self, entry: CacheEntry) -> bool:
        """检查是否过期"""
        return (time.time() - entry.created_at) > self.ttl_seconds

    def _evict(self) -> None:
        """淘汰最久未使用的条目"""
        if self._cache:
            self._cache.popitem(last=False)
            self._stats["evictions"] += 1

    def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def invalidate_pattern(self, pattern: str) -> int:
        """
        使匹配模式的缓存失效

        Args:
            pattern: 键的模式（前缀匹配）

        Returns:
            删除的条目数
        """
        count = 0
        with self._lock:
            keys_to_delete = [
                k for k in self._cache.keys()
                if k.startswith(pattern)
            ]
            for key in keys_to_delete:
                del self._cache[key]
                count += 1
        return count

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / max(total_requests, 1)

        return {
            **self._stats,
            "size": len(self._cache),
            "max_size": self.max_size,
            "hit_rate": hit_rate,
            "ttl_seconds": self.ttl_seconds,
        }

    def cleanup_expired(self) -> int:
        """
        清理过期条目

        Returns:
            清理的条目数
        """
        count = 0
        with self._lock:
            keys_to_delete = [
                k for k, v in self._cache.items()
                if self._is_expired(v)
            ]
            for key in keys_to_delete:
                del self._cache[key]
                count += 1
                self._stats["expirations"] += 1
        return count

    def get_top_queries(self, n: int = 10) -> list[tuple[str, int]]:
        """
        获取最常访问的查询

        Args:
            n: 返回的数量

        Returns:
            list of (key, access_count)
        """
        with self._lock:
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].access_count,
                reverse=True,
            )
            return [(k, v.access_count) for k, v in sorted_entries[:n]]

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, key: str) -> bool:
        with self._lock:
            if key not in self._cache:
                return False
            return not self._is_expired(self._cache[key])


class MultiLevelCache:
    """
    多级缓存
    L1: 内存缓存（快速）
    L2: 持久化缓存（较大）
    """

    def __init__(
        self,
        l1_size: int = 100,
        l2_size: int = 1000,
        ttl_seconds: int = 3600,
    ):
        self._l1 = SearchCache(max_size=l1_size, ttl_seconds=ttl_seconds)
        self._l2 = SearchCache(max_size=l2_size, ttl_seconds=ttl_seconds * 2)

    def get(self, key: str) -> Optional[list[SearchResult]]:
        result = self._l1.get(key)
        if result is not None:
            return result

        result = self._l2.get(key)
        if result is not None:
            self._l1.set(key, result)
            return result

        return None

    def set(self, key: str, results: list[SearchResult]) -> None:
        self._l1.set(key, results)
        self._l2.set(key, results)

    def clear(self) -> None:
        self._l1.clear()
        self._l2.clear()

    def get_stats(self) -> dict[str, Any]:
        return {
            "l1": self._l1.get_stats(),
            "l2": self._l2.get_stats(),
        }
