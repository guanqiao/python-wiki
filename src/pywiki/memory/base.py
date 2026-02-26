"""
Memory 模块基类
提供统一的内存管理接口
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class BaseMemory(ABC):
    """
    内存基类
    提供统一的序列化和持久化接口
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path
        if storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """序列化为字典"""
        pass

    @abstractmethod
    def from_dict(self, data: dict[str, Any]) -> "BaseMemory":
        """从字典反序列化"""
        pass

    def save(self, file_path: Optional[Path] = None) -> None:
        """
        保存到文件

        Args:
            file_path: 保存路径，默认使用 storage_path
        """
        path = file_path or self._get_default_save_path()
        if path is None:
            return

        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "type": self.__class__.__name__,
            "saved_at": datetime.now().isoformat(),
            "data": self.to_dict(),
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, file_path: Optional[Path] = None) -> bool:
        """
        从文件加载

        Args:
            file_path: 加载路径，默认使用 storage_path

        Returns:
            是否成功加载
        """
        path = file_path or self._get_default_save_path()
        if path is None or not path.exists():
            return False

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "data" in data:
                self.from_dict(data["data"])
                return True

            return False
        except Exception:
            return False

    def _get_default_save_path(self) -> Optional[Path]:
        """获取默认保存路径"""
        if self.storage_path:
            return self.storage_path / f"{self.__class__.__name__.lower()}.json"
        return None

    @staticmethod
    def _serialize_datetime(value: Optional[datetime]) -> Optional[str]:
        """序列化 datetime"""
        if value is None:
            return None
        return value.isoformat()

    @staticmethod
    def _deserialize_datetime(value: Optional[str]) -> Optional[datetime]:
        """反序列化 datetime"""
        if value is None:
            return None
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None

    @staticmethod
    def _serialize_path(value: Optional[Path]) -> Optional[str]:
        """序列化 Path"""
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _deserialize_path(value: Optional[str]) -> Optional[Path]:
        """反序列化 Path"""
        if value is None:
            return None
        return Path(value)

    def clear(self) -> None:
        """清空内存"""
        pass

    def export(self) -> dict[str, Any]:
        """导出内存内容"""
        return {
            "type": self.__class__.__name__,
            "exported_at": datetime.now().isoformat(),
            "data": self.to_dict(),
        }

    def import_data(self, data: dict[str, Any]) -> None:
        """导入内存内容"""
        if "data" in data:
            self.from_dict(data["data"])


class MemoryRegistry:
    """
    内存注册表
    统一管理多个内存实例
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path
        self._memories: dict[str, BaseMemory] = {}

    def register(self, name: str, memory: BaseMemory) -> None:
        """注册内存实例"""
        self._memories[name] = memory

    def unregister(self, name: str) -> bool:
        """注销内存实例"""
        if name in self._memories:
            del self._memories[name]
            return True
        return False

    def get(self, name: str) -> Optional[BaseMemory]:
        """获取内存实例"""
        return self._memories.get(name)

    def save_all(self) -> None:
        """保存所有内存"""
        for memory in self._memories.values():
            memory.save()

    def load_all(self) -> None:
        """加载所有内存"""
        for memory in self._memories.values():
            memory.load()

    def clear_all(self) -> None:
        """清空所有内存"""
        for memory in self._memories.values():
            memory.clear()

    def export_all(self) -> dict[str, Any]:
        """导出所有内存"""
        return {
            name: memory.export()
            for name, memory in self._memories.items()
        }
