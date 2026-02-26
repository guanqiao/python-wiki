
"""
Search Memory 工具
"""
from typing import Any, Optional, List, Dict
from pathlib import Path
from dataclasses import dataclass, asdict
import json


@dataclass
class MemoryItem:
    """记忆项"""
    id: str
    content: str
    metadata: Dict[str, Any]
    timestamp: str
    importance: float = 0.5
    access_count: int = 0


class SearchMemoryTool:
    """Search Memory 工具 - 用于深层次代码库感知"""

    def __init__(
        self,
        storage_path: Path,
        vector_store=None,
        llm_client=None,
    ):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.vector_store = vector_store
        self.llm_client = llm_client
        self._memories: Dict[str, MemoryItem] = {}
        self._load_memories()

    def _get_memories_path(self) -> Path:
        return self.storage_path / "search_memories.json"

    def _load_memories(self) -> None:
        memories_path = self._get_memories_path()
        if memories_path.exists():
            try:
                with open(memories_path, "r", encoding="utf-8") as f:
                    data_list = json.load(f)
                    self._memories = {
                        d["id"]: MemoryItem(**d)
                        for d in data_list
                    }
            except Exception:
                self._memories = {}
        else:
            self._memories = {}

    def _save_memories(self) -> None:
        memories_path = self._get_memories_path()
        data_list = [asdict(mem) for mem in self._memories.values()]
        with open(memories_path, "w", encoding="utf-8") as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)

    def add_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        memory_id: Optional[str] = None,
    ) -> MemoryItem:
        """
        添加记忆
        
        Args:
            content: 记忆内容
            metadata: 元数据
            importance: 重要性 (0.0-1.0)
            memory_id: 记忆 ID，可选
            
        Returns:
            MemoryItem 对象
        """
        from datetime import datetime
        
        mem_id = memory_id or f"MEM-{len(self._memories) + 1:06d}"
        memory = MemoryItem(
            id=mem_id,
            content=content,
            metadata=metadata or {},
            timestamp=datetime.now().isoformat(),
            importance=importance,
            access_count=0,
        )
        
        self._memories[mem_id] = memory
        
        if self.vector_store:
            self.vector_store.add_document(
                content=content,
                metadata={**metadata, "memory_id": mem_id, "importance": importance},
                doc_id=mem_id,
            )
        
        self._save_memories()
        return memory

    def get_memory(self, memory_id: str) -> Optional[MemoryItem]:
        """获取记忆"""
        memory = self._memories.get(memory_id)
        if memory:
            memory.access_count += 1
            self._save_memories()
        return memory

    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        if memory_id in self._memories:
            del self._memories[memory_id]
            
            if self.vector_store:
                try:
                    self.vector_store.delete_document(memory_id)
                except Exception:
                    pass
            
            self._save_memories()
            return True
        return False

    def search_memories(
        self,
        query: str,
        top_k: int = 10,
        min_importance: float = 0.0,
    ) -> List[MemoryItem]:
        """
        搜索记忆
        
        Args:
            query: 搜索查询
            top_k: 返回结果数量
            min_importance: 最小重要性
            
        Returns:
            记忆项列表
        """
        results = []
        
        if self.vector_store:
            try:
                vector_results = self.vector_store.search(query, k=top_k * 2)
                
                for result in vector_results:
                    mem_id = result.get("metadata", {}).get("memory_id")
                    if mem_id and mem_id in self._memories:
                        memory = self._memories[mem_id]
                        if memory.importance >= min_importance:
                            memory.access_count += 1
                            results.append(memory)
            except Exception:
                pass
        
        if not results:
            query_lower = query.lower()
            for memory in self._memories.values():
                if memory.importance >= min_importance:
                    if query_lower in memory.content.lower():
                        memory.access_count += 1
                        results.append(memory)
        
        results.sort(key=lambda x: (x.importance, x.access_count), reverse=True)
        self._save_memories()
        return results[:top_k]

    def get_recent_memories(self, limit: int = 20) -> List[MemoryItem]:
        """获取最近的记忆"""
        memories = sorted(
            self._memories.values(),
            key=lambda x: x.timestamp,
            reverse=True
        )
        return memories[:limit]

    def get_important_memories(self, limit: int = 20) -> List[MemoryItem]:
        """获取重要的记忆"""
        memories = sorted(
            self._memories.values(),
            key=lambda x: (x.importance, x.access_count),
            reverse=True
        )
        return memories[:limit]

    def update_importance(self, memory_id: str, importance: float) -> bool:
        """更新记忆重要性"""
        memory = self._memories.get(memory_id)
        if memory:
            memory.importance = max(0.0, min(1.0, importance))
            self._save_memories()
            return True
        return False

    def get_context_for_query(
        self,
        query: str,
        max_memories: int = 5,
    ) -> str:
        """
        为查询获取相关上下文
        
        Args:
            query: 查询内容
            max_memories: 最大记忆数量
            
        Returns:
            上下文字符串
        """
        memories = self.search_memories(query, top_k=max_memories)
        
        if not memories:
            return ""
        
        context_parts = []
        for i, memory in enumerate(memories):
            context_parts.append(
                f"[记忆 {i+1} (重要性: {memory.importance:.2f}, 访问次数: {memory.access_count})]\n"
                f"{memory.content}"
            )
        
        return "\n\n".join(context_parts)

    def list_all_memories(self) -> List[MemoryItem]:
        """列出所有记忆"""
        return list(self._memories.values())

    def clear_memories(self) -> None:
        """清空所有记忆"""
        self._memories.clear()
        
        if self.vector_store:
            try:
                self.vector_store.clear()
            except Exception:
                pass
        
        self._save_memories()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_memories": len(self._memories),
            "avg_importance": sum(m.importance for m in self._memories.values()) / max(len(self._memories), 1),
            "total_accesses": sum(m.access_count for m in self._memories.values()),
        }
