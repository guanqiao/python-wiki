"""
任务图定义
DAG（有向无环图）结构用于任务编排
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4


class TaskStatus(str, Enum):
    PENDING = "pending"
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskNode:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    executor: Optional[Callable] = None
    dependencies: list[str] = field(default_factory=list)
    timeout: float = 300.0
    retry_count: int = 0
    max_retries: int = 3
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TaskNode):
            return self.id == other.id
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


@dataclass
class TaskEdge:
    source_id: str
    target_id: str
    condition: Optional[Callable[[Any], bool]] = None
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "label": self.label,
        }


class TaskGraph:
    """
    任务图
    支持依赖关系、条件分支和并行执行
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._nodes: dict[str, TaskNode] = {}
        self._edges: list[TaskEdge] = []
        self._entry_nodes: list[str] = []
        self._exit_nodes: list[str] = []

    def add_node(
        self,
        name: str,
        executor: Optional[Callable] = None,
        description: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: float = 300.0,
        max_retries: int = 3,
        metadata: Optional[dict] = None,
    ) -> TaskNode:
        """
        添加任务节点

        Args:
            name: 任务名称
            executor: 执行函数
            description: 任务描述
            priority: 优先级
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            metadata: 元数据

        Returns:
            创建的任务节点
        """
        node = TaskNode(
            name=name,
            executor=executor,
            description=description,
            priority=priority,
            timeout=timeout,
            max_retries=max_retries,
            metadata=metadata or {},
        )
        self._nodes[node.id] = node
        return node

    def add_node_instance(self, node: TaskNode) -> TaskNode:
        """添加已创建的节点实例"""
        self._nodes[node.id] = node
        return node

    def add_edge(
        self,
        source: str | TaskNode,
        target: str | TaskNode,
        condition: Optional[Callable[[Any], bool]] = None,
        label: str = "",
    ) -> TaskEdge:
        """
        添加边（依赖关系）

        Args:
            source: 源节点（ID 或节点对象）
            target: 目标节点（ID 或节点对象）
            condition: 条件函数
            label: 边标签

        Returns:
            创建的边
        """
        source_id = source.id if isinstance(source, TaskNode) else source
        target_id = target.id if isinstance(target, TaskNode) else target

        if source_id not in self._nodes:
            raise ValueError(f"Source node {source_id} not found")
        if target_id not in self._nodes:
            raise ValueError(f"Target node {target_id} not found")

        edge = TaskEdge(
            source_id=source_id,
            target_id=target_id,
            condition=condition,
            label=label,
        )
        self._edges.append(edge)

        target_node = self._nodes[target_id]
        if source_id not in target_node.dependencies:
            target_node.dependencies.append(source_id)

        self._update_entry_exit_nodes()

        return edge

    def add_dependency(
        self,
        task: str | TaskNode,
        depends_on: str | TaskNode,
    ) -> None:
        """添加依赖关系"""
        self.add_edge(depends_on, task)

    def _update_entry_exit_nodes(self) -> None:
        """更新入口和出口节点"""
        all_targets = {e.target_id for e in self._edges}
        all_sources = {e.source_id for e in self._edges}

        self._entry_nodes = [
            node_id for node_id in self._nodes
            if node_id not in all_targets
        ]

        self._exit_nodes = [
            node_id for node_id in self._nodes
            if node_id not in all_sources
        ]

    def get_node(self, node_id: str) -> Optional[TaskNode]:
        """获取节点"""
        return self._nodes.get(node_id)

    def get_node_by_name(self, name: str) -> Optional[TaskNode]:
        """按名称获取节点"""
        for node in self._nodes.values():
            if node.name == name:
                return node
        return None

    def get_dependencies(self, node_id: str) -> list[TaskNode]:
        """获取节点的依赖"""
        node = self._nodes.get(node_id)
        if not node:
            return []
        return [self._nodes[dep_id] for dep_id in node.dependencies if dep_id in self._nodes]

    def get_dependents(self, node_id: str) -> list[TaskNode]:
        """获取依赖于此节点的节点"""
        dependents = []
        for edge in self._edges:
            if edge.source_id == node_id:
                target = self._nodes.get(edge.target_id)
                if target:
                    dependents.append(target)
        return dependents

    def get_entry_nodes(self) -> list[TaskNode]:
        """获取入口节点（无依赖的节点）"""
        return [self._nodes[nid] for nid in self._entry_nodes if nid in self._nodes]

    def get_exit_nodes(self) -> list[TaskNode]:
        """获取出口节点（无后续的节点）"""
        return [self._nodes[nid] for nid in self._exit_nodes if nid in self._nodes]

    def get_ready_nodes(self) -> list[TaskNode]:
        """获取可执行的节点（依赖已完成）"""
        ready = []
        for node in self._nodes.values():
            if node.status != TaskStatus.PENDING:
                continue

            dependencies_met = all(
                self._nodes.get(dep_id, TaskNode()).status == TaskStatus.COMPLETED
                for dep_id in node.dependencies
                if dep_id in self._nodes
            )

            if dependencies_met:
                ready.append(node)

        return ready

    def topological_sort(self) -> list[TaskNode]:
        """拓扑排序"""
        in_degree = {node_id: 0 for node_id in self._nodes}

        for edge in self._edges:
            if edge.target_id in in_degree:
                in_degree[edge.target_id] += 1

        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(self._nodes[node_id])

            for edge in self._edges:
                if edge.source_id == node_id:
                    target_id = edge.target_id
                    if target_id in in_degree:
                        in_degree[target_id] -= 1
                        if in_degree[target_id] == 0:
                            queue.append(target_id)

        return result

    def is_dag(self) -> bool:
        """检查是否为 DAG（无环）"""
        try:
            self.topological_sort()
            return True
        except Exception:
            return False

    def validate(self) -> list[str]:
        """
        验证任务图

        Returns:
            错误消息列表
        """
        errors = []

        if not self.is_dag():
            errors.append("Graph contains cycles")

        for node in self._nodes.values():
            for dep_id in node.dependencies:
                if dep_id not in self._nodes:
                    errors.append(f"Node {node.id} has invalid dependency {dep_id}")

        for node in self._nodes.values():
            if node.executor is None and node.status == TaskStatus.PENDING:
                errors.append(f"Node {node.id} ({node.name}) has no executor")

        return errors

    def reset(self) -> None:
        """重置所有节点状态"""
        for node in self._nodes.values():
            node.status = TaskStatus.PENDING
            node.result = None
            node.error = None
            node.started_at = None
            node.completed_at = None
            node.retry_count = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "nodes": [node.to_dict() for node in self._nodes.values()],
            "edges": [edge.to_dict() for edge in self._edges],
            "entry_nodes": self._entry_nodes,
            "exit_nodes": self._exit_nodes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskGraph":
        """从字典创建"""
        graph = cls(name=data.get("name", "default"))

        for node_data in data.get("nodes", []):
            node = TaskNode(
                id=node_data["id"],
                name=node_data["name"],
                description=node_data.get("description", ""),
                status=TaskStatus(node_data.get("status", "pending")),
                priority=TaskPriority(node_data.get("priority", "normal")),
                dependencies=node_data.get("dependencies", []),
                timeout=node_data.get("timeout", 300.0),
                retry_count=node_data.get("retry_count", 0),
                max_retries=node_data.get("max_retries", 3),
                metadata=node_data.get("metadata", {}),
            )
            graph._nodes[node.id] = node

        for edge_data in data.get("edges", []):
            edge = TaskEdge(
                source_id=edge_data["source_id"],
                target_id=edge_data["target_id"],
                label=edge_data.get("label", ""),
            )
            graph._edges.append(edge)

        graph._update_entry_exit_nodes()
        return graph

    def __len__(self) -> int:
        return len(self._nodes)

    def __iter__(self):
        return iter(self._nodes.values())

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._nodes
