"""
LangGraph 状态定义
使用 TypedDict 定义工作流状态
"""

from enum import Enum
from typing import Annotated, Any, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DocumentInfo(TypedDict):
    doc_id: str
    file_path: str
    content: str
    doc_type: str
    metadata: dict[str, Any]


class AnalysisResult(TypedDict):
    patterns: list[dict[str, Any]]
    dependencies: list[str]
    tech_debt: list[dict[str, Any]]
    architecture_decisions: list[dict[str, Any]]


class GeneratedDoc(TypedDict):
    doc_id: str
    title: str
    content: str
    doc_type: str
    file_path: str


class NodeResult(TypedDict):
    node_name: str
    status: NodeStatus
    started_at: Optional[str]
    completed_at: Optional[str]
    error: Optional[str]
    output: dict[str, Any]


class WikiState(TypedDict):
    """
    Wiki 生成工作流状态
    
    Attributes:
        messages: 消息列表，用于 LLM 交互
        project_path: 项目路径
        documents: 解析后的文档列表
        analysis: 分析结果
        generated_docs: 生成的文档
        current_node: 当前执行的节点
        node_results: 各节点的执行结果
        errors: 错误列表
        context: 额外的上下文信息
    """
    messages: Annotated[list, add_messages]
    project_path: str
    documents: list[DocumentInfo]
    analysis: AnalysisResult
    generated_docs: list[GeneratedDoc]
    current_node: str
    node_results: list[NodeResult]
    errors: list[str]
    context: dict[str, Any]


def create_initial_state(project_path: str) -> WikiState:
    """创建初始状态"""
    return WikiState(
        messages=[],
        project_path=project_path,
        documents=[],
        analysis=AnalysisResult(
            patterns=[],
            dependencies=[],
            tech_debt=[],
            architecture_decisions=[],
        ),
        generated_docs=[],
        current_node="",
        node_results=[],
        errors=[],
        context={},
    )


def update_state_node_result(
    state: WikiState,
    node_name: str,
    status: NodeStatus,
    output: Optional[dict[str, Any]] = None,
    error: Optional[str] = None,
) -> WikiState:
    """更新节点执行结果"""
    from datetime import datetime

    result = NodeResult(
        node_name=node_name,
        status=status,
        started_at=datetime.now().isoformat() if status == NodeStatus.RUNNING else None,
        completed_at=datetime.now().isoformat() if status in (NodeStatus.COMPLETED, NodeStatus.FAILED) else None,
        error=error,
        output=output or {},
    )

    new_results = [r for r in state["node_results"] if r["node_name"] != node_name]
    new_results.append(result)

    return WikiState(
        **{k: v for k, v in state.items() if k != "node_results"},
        node_results=new_results,
        current_node=node_name,
    )


def add_error(state: WikiState, error: str) -> WikiState:
    """添加错误"""
    return WikiState(
        **{k: v for k, v in state.items() if k != "errors"},
        errors=[*state["errors"], error],
    )
