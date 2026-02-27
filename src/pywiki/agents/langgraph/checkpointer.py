"""
LangGraph 状态持久化
支持工作流状态的保存和恢复
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.base import Checkpoint


class WikiCheckpointer(BaseCheckpointSaver):
    """
    Wiki 工作流检查点保存器
    将工作流状态持久化到文件系统
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".pywiki" / "checkpoints"
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_checkpoint_path(self, thread_id: str) -> Path:
        return self.storage_path / f"{thread_id}.json"

    def _get_metadata_path(self, thread_id: str) -> Path:
        return self.storage_path / f"{thread_id}_meta.json"

    def put(
        self,
        config: dict[str, Any],
        checkpoint: Checkpoint,
        metadata: Optional[dict[str, Any]] = None,
        new_versions: Optional[dict[str, Any]] = None,
    ) -> None:
        """保存检查点"""
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint_path = self._get_checkpoint_path(thread_id)

        checkpoint_data = {
            "thread_id": thread_id,
            "timestamp": datetime.now().isoformat(),
            "checkpoint": self._serialize_checkpoint(checkpoint),
        }

        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

        if metadata:
            metadata_path = self._get_metadata_path(thread_id)
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

    def get(self, config: dict[str, Any]) -> Optional[Checkpoint]:
        """加载检查点"""
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint_path = self._get_checkpoint_path(thread_id)

        if not checkpoint_path.exists():
            return None

        try:
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return self._deserialize_checkpoint(data.get("checkpoint", {}))
        except Exception:
            return None

    def get_tuple(self, config: dict[str, Any]) -> Optional[tuple[Checkpoint, dict[str, Any]]]:
        """获取检查点和元数据"""
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint = self.get(config)
        if checkpoint is None:
            return None
        
        metadata = self.load_metadata(thread_id)
        return (checkpoint, metadata or {})

    def put_writes(
        self,
        config: dict[str, Any],
        writes: list[tuple[str, Any]],
        task_id: str,
    ) -> None:
        """写入待处理的写入操作"""
        pass

    def load_metadata(self, thread_id: str) -> Optional[dict[str, Any]]:
        """加载元数据"""
        metadata_path = self._get_metadata_path(thread_id)

        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def delete(self, thread_id: str) -> bool:
        """删除检查点"""
        checkpoint_path = self._get_checkpoint_path(thread_id)
        metadata_path = self._get_metadata_path(thread_id)

        deleted = False

        if checkpoint_path.exists():
            checkpoint_path.unlink()
            deleted = True

        if metadata_path.exists():
            metadata_path.unlink()
            deleted = True

        return deleted

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """列出所有检查点"""
        checkpoints = []

        for path in self.storage_path.glob("*.json"):
            if path.stem.endswith("_meta"):
                continue

            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                checkpoints.append({
                    "thread_id": data.get("thread_id", path.stem),
                    "timestamp": data.get("timestamp"),
                    "path": str(path),
                })
            except Exception:
                continue

        return sorted(checkpoints, key=lambda x: x.get("timestamp", ""), reverse=True)

    def _serialize_checkpoint(self, checkpoint: Checkpoint) -> dict[str, Any]:
        """序列化检查点"""
        result = {}

        for key, value in checkpoint.items():
            if isinstance(value, datetime):
                result[key] = {"__type__": "datetime", "value": value.isoformat()}
            elif isinstance(value, Path):
                result[key] = {"__type__": "path", "value": str(value)}
            elif isinstance(value, (list, dict)):
                result[key] = value
            else:
                result[key] = value

        return result

    def _deserialize_checkpoint(self, data: dict[str, Any]) -> Checkpoint:
        """反序列化检查点"""
        result = {}

        for key, value in data.items():
            if isinstance(value, dict) and "__type__" in value:
                if value["__type__"] == "datetime":
                    result[key] = datetime.fromisoformat(value["value"])
                elif value["__type__"] == "path":
                    result[key] = Path(value["value"])
                else:
                    result[key] = value.get("value")
            else:
                result[key] = value

        return result

    def get_latest_checkpoint(self) -> Optional[dict[str, Any]]:
        """获取最新的检查点"""
        checkpoints = self.list_checkpoints()
        if checkpoints:
            return checkpoints[0]
        return None

    def cleanup_old_checkpoints(self, max_age_days: int = 30) -> int:
        """清理旧检查点"""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=max_age_days)
        cleaned = 0

        for checkpoint in self.list_checkpoints():
            if checkpoint.get("timestamp"):
                timestamp = datetime.fromisoformat(checkpoint["timestamp"])
                if timestamp < cutoff:
                    self.delete(checkpoint["thread_id"])
                    cleaned += 1

        return cleaned


class MemoryCheckpointer(BaseCheckpointSaver):
    """
    内存检查点保存器
    用于测试和临时存储
    """

    def __init__(self):
        self._checkpoints: dict[str, Checkpoint] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def put(
        self,
        config: dict[str, Any],
        checkpoint: Checkpoint,
        metadata: Optional[dict[str, Any]] = None,
        new_versions: Optional[dict[str, Any]] = None,
    ) -> None:
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        self._checkpoints[thread_id] = checkpoint

        if metadata:
            self._metadata[thread_id] = metadata

    def get(self, config: dict[str, Any]) -> Optional[Checkpoint]:
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        return self._checkpoints.get(thread_id)

    def get_tuple(self, config: dict[str, Any]) -> Optional[tuple[Checkpoint, dict[str, Any]]]:
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint = self._checkpoints.get(thread_id)
        if checkpoint is None:
            return None
        return (checkpoint, self._metadata.get(thread_id, {}))

    def put_writes(
        self,
        config: dict[str, Any],
        writes: list[tuple[str, Any]],
        task_id: str,
    ) -> None:
        pass

    def load_metadata(self, thread_id: str) -> Optional[dict[str, Any]]:
        return self._metadata.get(thread_id)

    def delete(self, thread_id: str) -> bool:
        if thread_id in self._checkpoints:
            del self._checkpoints[thread_id]
            self._metadata.pop(thread_id, None)
            return True
        return False

    def list_checkpoints(self) -> list[str]:
        return list(self._checkpoints.keys())

    def clear(self) -> None:
        self._checkpoints.clear()
        self._metadata.clear()
