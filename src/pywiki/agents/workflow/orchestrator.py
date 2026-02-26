"""
工作流编排器
协调多个 Agent 和任务的执行
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

from pywiki.agents.workflow.task_graph import (
    TaskGraph,
    TaskNode,
    TaskStatus,
    TaskPriority,
)
from pywiki.agents.base import BaseAgent, AgentContext, AgentResult


class WorkflowStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowResult:
    workflow_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    task_results: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "task_results": self.task_results,
            "errors": self.errors,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowContext:
    workflow_id: str = field(default_factory=lambda: str(uuid4()))
    variables: dict[str, Any] = field(default_factory=dict)
    shared_data: dict[str, Any] = field(default_factory=dict)
    agent_context: Optional[AgentContext] = None

    def set(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def share(self, key: str, value: Any) -> None:
        self.shared_data[key] = value

    def get_shared(self, key: str, default: Any = None) -> Any:
        return self.shared_data.get(key, default)


class WorkflowOrchestrator:
    """
    工作流编排器
    管理 DAG 任务图的执行
    """

    def __init__(
        self,
        max_concurrent_tasks: int = 5,
        default_timeout: float = 300.0,
        on_task_complete: Optional[Callable[[TaskNode, Any], None]] = None,
        on_task_error: Optional[Callable[[TaskNode, Exception], None]] = None,
        on_workflow_complete: Optional[Callable[[WorkflowResult], None]] = None,
    ):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.default_timeout = default_timeout

        self._on_task_complete = on_task_complete
        self._on_task_error = on_task_error
        self._on_workflow_complete = on_workflow_complete

        self._status = WorkflowStatus.IDLE
        self._current_graph: Optional[TaskGraph] = None
        self._context: Optional[WorkflowContext] = None
        self._result: Optional[WorkflowResult] = None

        self._agents: dict[str, BaseAgent] = {}
        self._task_executors: dict[str, Callable] = {}

        self._semaphore: Optional[asyncio.Semaphore] = None
        self._cancel_event = asyncio.Event()

    def register_agent(self, name: str, agent: BaseAgent) -> None:
        """注册 Agent"""
        self._agents[name] = agent

    def unregister_agent(self, name: str) -> bool:
        """注销 Agent"""
        if name in self._agents:
            del self._agents[name]
            return True
        return False

    def register_executor(self, name: str, executor: Callable) -> None:
        """注册任务执行器"""
        self._task_executors[name] = executor

    def create_workflow(self, name: str = "default") -> TaskGraph:
        """创建新的工作流"""
        return TaskGraph(name=name)

    async def execute(
        self,
        graph: TaskGraph,
        context: Optional[WorkflowContext] = None,
    ) -> WorkflowResult:
        """
        执行工作流

        Args:
            graph: 任务图
            context: 执行上下文

        Returns:
            工作流结果
        """
        errors = graph.validate()
        if errors:
            raise ValueError(f"Invalid task graph: {errors}")

        self._current_graph = graph
        self._context = context or WorkflowContext()
        self._status = WorkflowStatus.RUNNING
        self._cancel_event.clear()

        self._result = WorkflowResult(
            workflow_id=self._context.workflow_id,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now(),
        )

        self._semaphore = asyncio.Semaphore(self.max_concurrent_tasks)

        try:
            await self._execute_graph(graph)

            if self._cancel_event.is_set():
                self._result.status = WorkflowStatus.CANCELLED
            elif any(n.status == TaskStatus.FAILED for n in graph):
                self._result.status = WorkflowStatus.FAILED
            else:
                self._result.status = WorkflowStatus.COMPLETED

        except Exception as e:
            self._result.status = WorkflowStatus.FAILED
            self._result.errors.append(str(e))

        finally:
            self._result.completed_at = datetime.now()
            self._status = self._result.status

            for node in graph:
                if node.result is not None:
                    self._result.task_results[node.id] = node.result
                if node.error:
                    self._result.errors.append(f"{node.name}: {node.error}")

            if self._on_workflow_complete:
                self._on_workflow_complete(self._result)

        return self._result

    async def _execute_graph(self, graph: TaskGraph) -> None:
        """执行任务图"""
        running_tasks: dict[str, asyncio.Task] = {}

        while True:
            if self._cancel_event.is_set():
                for task in running_tasks.values():
                    task.cancel()
                break

            ready_nodes = graph.get_ready_nodes()

            for node in ready_nodes:
                if node.id not in running_tasks:
                    task = asyncio.create_task(self._execute_node(node))
                    running_tasks[node.id] = task

            if not running_tasks:
                break

            done, _ = await asyncio.wait(
                running_tasks.values(),
                return_when=asyncio.FIRST_COMPLETED,
            )

            for completed_task in done:
                node_id = None
                for nid, task in running_tasks.items():
                    if task == completed_task:
                        node_id = nid
                        break

                if node_id:
                    del running_tasks[node_id]

            await asyncio.sleep(0.1)

    async def _execute_node(self, node: TaskNode) -> None:
        """执行单个节点"""
        async with self._semaphore:
            node.status = TaskStatus.RUNNING
            node.started_at = datetime.now()

            try:
                executor = self._get_executor(node)

                if asyncio.iscoroutinefunction(executor):
                    result = await asyncio.wait_for(
                        executor(self._context, node),
                        timeout=node.timeout,
                    )
                else:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: executor(self._context, node),
                    )

                node.result = result
                node.status = TaskStatus.COMPLETED
                node.completed_at = datetime.now()

                if self._on_task_complete:
                    self._on_task_complete(node, result)

            except asyncio.TimeoutError:
                node.status = TaskStatus.FAILED
                node.error = f"Task timed out after {node.timeout} seconds"
                self._handle_node_error(node, TimeoutError(node.error))

            except asyncio.CancelledError:
                node.status = TaskStatus.CANCELLED
                node.error = "Task was cancelled"

            except Exception as e:
                if node.retry_count < node.max_retries:
                    node.retry_count += 1
                    node.status = TaskStatus.PENDING
                    await asyncio.sleep(1)
                    await self._execute_node(node)
                else:
                    node.status = TaskStatus.FAILED
                    node.error = str(e)
                    self._handle_node_error(node, e)

    def _get_executor(self, node: TaskNode) -> Callable:
        """获取节点执行器"""
        if node.executor:
            return node.executor

        agent_name = node.metadata.get("agent")
        if agent_name and agent_name in self._agents:
            agent = self._agents[agent_name]
            return lambda ctx, n: agent.execute(ctx.agent_context or AgentContext())

        executor_name = node.metadata.get("executor")
        if executor_name and executor_name in self._task_executors:
            return self._task_executors[executor_name]

        raise ValueError(f"No executor found for node {node.name}")

    def _handle_node_error(self, node: TaskNode, error: Exception) -> None:
        """处理节点错误"""
        if self._on_task_error:
            self._on_task_error(node, error)

    def pause(self) -> None:
        """暂停工作流"""
        if self._status == WorkflowStatus.RUNNING:
            self._status = WorkflowStatus.PAUSED

    def resume(self) -> None:
        """恢复工作流"""
        if self._status == WorkflowStatus.PAUSED:
            self._status = WorkflowStatus.RUNNING

    def cancel(self) -> None:
        """取消工作流"""
        self._cancel_event.set()

    @property
    def status(self) -> WorkflowStatus:
        return self._status

    @property
    def result(self) -> Optional[WorkflowResult]:
        return self._result

    def get_progress(self) -> dict[str, Any]:
        """获取执行进度"""
        if not self._current_graph:
            return {"status": self._status.value, "progress": 0}

        graph = self._current_graph
        total = len(graph)
        completed = sum(1 for n in graph if n.status == TaskStatus.COMPLETED)
        running = sum(1 for n in graph if n.status == TaskStatus.RUNNING)
        failed = sum(1 for n in graph if n.status == TaskStatus.FAILED)

        return {
            "status": self._status.value,
            "total_tasks": total,
            "completed": completed,
            "running": running,
            "failed": failed,
            "progress": (completed / total * 100) if total > 0 else 0,
        }
