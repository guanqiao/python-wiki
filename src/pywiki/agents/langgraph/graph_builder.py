"""
LangGraph 图构建器
构建和配置 Wiki 生成工作流图
"""

from pathlib import Path
from typing import Any, Callable, Optional

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from pywiki.agents.langgraph.state import (
    WikiState,
    NodeStatus,
    create_initial_state,
)
from pywiki.agents.langgraph.nodes import (
    parse_node,
    analyze_node,
    generate_node,
    validate_node,
)


def should_continue(state: WikiState) -> str:
    """判断是否继续执行"""
    if state["errors"]:
        return "end"

    current = state["current_node"]

    if current == "parse":
        if not state["documents"]:
            return "end"
        return "analyze"

    if current == "analyze":
        return "generate"

    if current == "generate":
        if not state["generated_docs"]:
            return "end"
        return "validate"

    if current == "validate":
        return "end"

    return "end"


def route_by_error(state: WikiState) -> str:
    """根据错误路由"""
    if state["errors"]:
        return "end"
    return "continue"


class WikiGraphBuilder:
    """
    Wiki 工作流图构建器
    使用 LangGraph 构建复杂的 Agent 工作流
    """

    def __init__(self):
        self._nodes: dict[str, Callable] = {}
        self._edges: list[tuple[str, str]] = []
        self._conditional_edges: list[tuple[str, Callable, dict[str, str]]] = []
        self._entry_point: Optional[str] = None
        self._checkpointer: Optional[Any] = None

    def add_node(self, name: str, action: Callable) -> "WikiGraphBuilder":
        """添加节点"""
        self._nodes[name] = action
        return self

    def add_edge(self, from_node: str, to_node: str) -> "WikiGraphBuilder":
        """添加边"""
        self._edges.append((from_node, to_node))
        return self

    def add_conditional_edges(
        self,
        from_node: str,
        condition: Callable,
        paths: dict[str, str],
    ) -> "WikiGraphBuilder":
        """添加条件边"""
        self._conditional_edges.append((from_node, condition, paths))
        return self

    def set_entry_point(self, node_name: str) -> "WikiGraphBuilder":
        """设置入口点"""
        self._entry_point = node_name
        return self

    def set_checkpointer(self, checkpointer: Any) -> "WikiGraphBuilder":
        """设置检查点"""
        self._checkpointer = checkpointer
        return self

    def build(self) -> StateGraph:
        """构建图"""
        graph = StateGraph(WikiState)

        for name, action in self._nodes.items():
            graph.add_node(name, action)

        if self._entry_point:
            graph.set_entry_point(self._entry_point)

        for from_node, to_node in self._edges:
            if to_node == "END":
                graph.add_edge(from_node, END)
            else:
                graph.add_edge(from_node, to_node)

        for from_node, condition, paths in self._conditional_edges:
            mapped_paths = {
                k: END if v == "end" else v
                for k, v in paths.items()
            }
            graph.add_conditional_edges(from_node, condition, mapped_paths)

        if self._checkpointer:
            return graph.compile(checkpointer=self._checkpointer)

        return graph.compile()

    def build_with_memory(self) -> StateGraph:
        """构建带内存持久化的图"""
        memory_saver = MemorySaver()
        return self.set_checkpointer(memory_saver).build()


def build_wiki_graph(
    output_dir: Optional[Path] = None,
    with_memory: bool = True,
) -> StateGraph:
    """
    构建 Wiki 生成工作流图

    Args:
        output_dir: 输出目录
        with_memory: 是否启用内存持久化

    Returns:
        编译后的工作流图
    """
    builder = WikiGraphBuilder()

    async def parse(state: WikiState) -> WikiState:
        return await parse_node(state)

    async def analyze(state: WikiState) -> WikiState:
        return await analyze_node(state)

    async def generate(state: WikiState) -> WikiState:
        return await generate_node(state)

    async def validate(state: WikiState) -> WikiState:
        return await validate_node(state)

    builder.add_node("parse", parse)
    builder.add_node("analyze", analyze)
    builder.add_node("generate", generate)
    builder.add_node("validate", validate)

    builder.set_entry_point("parse")

    builder.add_conditional_edges(
        "parse",
        should_continue,
        {
            "analyze": "analyze",
            "end": END,
        },
    )

    builder.add_conditional_edges(
        "analyze",
        route_by_error,
        {
            "continue": "generate",
            "end": END,
        },
    )

    builder.add_conditional_edges(
        "generate",
        should_continue,
        {
            "validate": "validate",
            "end": END,
        },
    )

    builder.add_edge("validate", END)

    if with_memory:
        return builder.build_with_memory()

    return builder.build()


def create_simple_graph() -> StateGraph:
    """创建简单的工作流图（无条件分支）"""
    builder = WikiGraphBuilder()

    builder.add_node("parse", parse_node)
    builder.add_node("analyze", analyze_node)
    builder.add_node("generate", generate_node)
    builder.add_node("validate", validate_node)

    builder.set_entry_point("parse")
    builder.add_edge("parse", "analyze")
    builder.add_edge("analyze", "generate")
    builder.add_edge("generate", "validate")
    builder.add_edge("validate", END)

    return builder.build()


class WorkflowRunner:
    """工作流运行器"""

    def __init__(self, graph: Optional[StateGraph] = None):
        self.graph = graph or build_wiki_graph()

    async def run(
        self,
        project_path: str,
        thread_id: Optional[str] = None,
    ) -> WikiState:
        """
        运行工作流

        Args:
            project_path: 项目路径
            thread_id: 线程ID（用于恢复）

        Returns:
            最终状态
        """
        initial_state = create_initial_state(project_path)

        config = {}
        if thread_id:
            config["configurable"] = {"thread_id": thread_id}

        result = await self.graph.ainvoke(initial_state, config)
        return result

    async def stream(
        self,
        project_path: str,
        thread_id: Optional[str] = None,
    ):
        """
        流式运行工作流

        Yields:
            每个节点的执行结果
        """
        initial_state = create_initial_state(project_path)

        config = {}
        if thread_id:
            config["configurable"] = {"thread_id": thread_id}

        async for event in self.graph.astream(initial_state, config):
            yield event

    def get_state(self, thread_id: str) -> Optional[WikiState]:
        """获取指定线程的状态"""
        config = {"configurable": {"thread_id": thread_id}}
        try:
            return self.graph.get_state(config)
        except Exception:
            return None

    def resume(self, thread_id: str) -> WikiState:
        """恢复中断的工作流"""
        config = {"configurable": {"thread_id": thread_id}}
        return self.graph.invoke(None, config)
