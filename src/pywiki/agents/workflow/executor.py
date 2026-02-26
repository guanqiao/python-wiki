"""
工作流执行器
提供并行执行、重试和错误处理
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from pywiki.agents.workflow.task_graph import (
    TaskGraph,
    TaskNode,
    TaskStatus,
)
from pywiki.agents.workflow.orchestrator import (
    WorkflowContext,
    WorkflowResult,
    WorkflowStatus,
)


@dataclass
class ExecutionConfig:
    max_workers: int = 4
    default_timeout: float = 300.0
    retry_delay: float = 1.0
    enable_parallel: bool = True


@dataclass
class ExecutionMetrics:
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    total_time_ms: float = 0.0
    avg_task_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "skipped_tasks": self.skipped_tasks,
            "total_time_ms": self.total_time_ms,
            "avg_task_time_ms": self.avg_task_time_ms,
        }


class WorkflowExecutor:
    """
    工作流执行器
    支持并行执行、重试和错误处理
    """

    def __init__(
        self,
        config: Optional[ExecutionConfig] = None,
        on_progress: Optional[Callable[[ExecutionMetrics], None]] = None,
    ):
        self.config = config or ExecutionConfig()
        self.on_progress = on_progress

        self._metrics = ExecutionMetrics()
        self._thread_pool: Optional[ThreadPoolExecutor] = None
        self._running = False

    async def execute(
        self,
        graph: TaskGraph,
        context: Optional[WorkflowContext] = None,
    ) -> WorkflowResult:
        """
        执行任务图

        Args:
            graph: 任务图
            context: 执行上下文

        Returns:
            执行结果
        """
        start_time = datetime.now()
        context = context or WorkflowContext()

        self._metrics = ExecutionMetrics(total_tasks=len(graph))
        self._running = True

        result = WorkflowResult(
            workflow_id=context.workflow_id,
            status=WorkflowStatus.RUNNING,
            started_at=start_time,
        )

        try:
            if self.config.enable_parallel:
                await self._execute_parallel(graph, context, result)
            else:
                await self._execute_sequential(graph, context, result)

            result.status = WorkflowStatus.COMPLETED

        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.errors.append(str(e))

        finally:
            self._running = False
            end_time = datetime.now()
            result.completed_at = end_time

            self._metrics.total_time_ms = (end_time - start_time).total_seconds() * 1000
            if self._metrics.completed_tasks > 0:
                self._metrics.avg_task_time_ms = (
                    self._metrics.total_time_ms / self._metrics.completed_tasks
                )

            self._notify_progress()

        return result

    async def _execute_parallel(
        self,
        graph: TaskGraph,
        context: WorkflowContext,
        result: WorkflowResult,
    ) -> None:
        """并行执行"""
        semaphore = asyncio.Semaphore(self.config.max_workers)
        running_tasks: dict[str, asyncio.Task] = {}

        while self._running:
            ready_nodes = [
                n for n in graph.get_ready_nodes()
                if n.id not in running_tasks
            ]

            for node in ready_nodes:
                task = asyncio.create_task(
                    self._execute_node_with_semaphore(node, context, semaphore)
                )
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
                    node = graph.get_node(node_id)
                    if node:
                        if node.status == TaskStatus.COMPLETED:
                            self._metrics.completed_tasks += 1
                            result.task_results[node_id] = node.result
                        elif node.status == TaskStatus.FAILED:
                            self._metrics.failed_tasks += 1
                            if node.error:
                                result.errors.append(f"{node.name}: {node.error}")
                        elif node.status == TaskStatus.SKIPPED:
                            self._metrics.skipped_tasks += 1

                    del running_tasks[node_id]

            self._notify_progress()

    async def _execute_sequential(
        self,
        graph: TaskGraph,
        context: WorkflowContext,
        result: WorkflowResult,
    ) -> None:
        """顺序执行"""
        sorted_nodes = graph.topological_sort()

        for node in sorted_nodes:
            if not self._running:
                break

            await self._execute_node(node, context)

            if node.status == TaskStatus.COMPLETED:
                self._metrics.completed_tasks += 1
                result.task_results[node.id] = node.result
            elif node.status == TaskStatus.FAILED:
                self._metrics.failed_tasks += 1
                if node.error:
                    result.errors.append(f"{node.name}: {node.error}")
            elif node.status == TaskStatus.SKIPPED:
                self._metrics.skipped_tasks += 1

            self._notify_progress()

    async def _execute_node_with_semaphore(
        self,
        node: TaskNode,
        context: WorkflowContext,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """带信号量的节点执行"""
        async with semaphore:
            await self._execute_node(node, context)

    async def _execute_node(
        self,
        node: TaskNode,
        context: WorkflowContext,
    ) -> None:
        """执行单个节点"""
        node.status = TaskStatus.RUNNING
        node.started_at = datetime.now()

        try:
            if node.executor is None:
                raise ValueError(f"No executor for node {node.name}")

            if asyncio.iscoroutinefunction(node.executor):
                result = await asyncio.wait_for(
                    node.executor(context, node),
                    timeout=node.timeout,
                )
            else:
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: node.executor(context, node),
                    ),
                    timeout=node.timeout,
                )

            node.result = result
            node.status = TaskStatus.COMPLETED

        except asyncio.TimeoutError:
            await self._handle_retry(node, context, TimeoutError(f"Timeout after {node.timeout}s"))

        except Exception as e:
            await self._handle_retry(node, context, e)

        finally:
            node.completed_at = datetime.now()

    async def _handle_retry(
        self,
        node: TaskNode,
        context: WorkflowContext,
        error: Exception,
    ) -> None:
        """处理重试"""
        if node.retry_count < node.max_retries:
            node.retry_count += 1
            await asyncio.sleep(self.config.retry_delay * node.retry_count)
            await self._execute_node(node, context)
        else:
            node.status = TaskStatus.FAILED
            node.error = str(error)

    def stop(self) -> None:
        """停止执行"""
        self._running = False

    def _notify_progress(self) -> None:
        """通知进度更新"""
        if self.on_progress:
            self.on_progress(self._metrics)

    @property
    def metrics(self) -> ExecutionMetrics:
        return self._metrics

    @property
    def is_running(self) -> bool:
        return self._running


class TaskExecutorBuilder:
    """
    任务执行器构建器
    用于创建常见的任务执行器
    """

    @staticmethod
    def create_agent_executor(agent: Any, method_name: str = "execute") -> Callable:
        """创建 Agent 执行器"""
        async def executor(context: WorkflowContext, node: TaskNode) -> Any:
            method = getattr(agent, method_name)
            if asyncio.iscoroutinefunction(method):
                return await method(context.agent_context or context)
            return method(context.agent_context or context)
        return executor

    @staticmethod
    def create_function_executor(func: Callable) -> Callable:
        """创建函数执行器"""
        async def executor(context: WorkflowContext, node: TaskNode) -> Any:
            if asyncio.iscoroutinefunction(func):
                return await func(context, node)
            return func(context, node)
        return executor

    @staticmethod
    def create_conditional_executor(
        condition: Callable[[WorkflowContext, TaskNode], bool],
        true_executor: Callable,
        false_executor: Optional[Callable] = None,
    ) -> Callable:
        """创建条件执行器"""
        async def executor(context: WorkflowContext, node: TaskNode) -> Any:
            if condition(context, node):
                if asyncio.iscoroutinefunction(true_executor):
                    return await true_executor(context, node)
                return true_executor(context, node)
            elif false_executor:
                if asyncio.iscoroutinefunction(false_executor):
                    return await false_executor(context, node)
                return false_executor(context, node)
            return None
        return executor

    @staticmethod
    def create_parallel_executor(
        executors: list[Callable],
        merge_results: bool = False,
    ) -> Callable:
        """创建并行执行器"""
        async def executor(context: WorkflowContext, node: TaskNode) -> Any:
            tasks = [
                exec(context, node) if asyncio.iscoroutinefunction(exec)
                else asyncio.get_event_loop().run_in_executor(None, lambda e=exec: e(context, node))
                for exec in executors
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            if merge_results:
                merged = {}
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        merged[f"task_{i}"] = {"error": str(result)}
                    else:
                        merged[f"task_{i}"] = result
                return merged

            return results
        return executor
