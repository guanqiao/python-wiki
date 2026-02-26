"""
LangGraph 节点定义
定义工作流中的各个处理节点
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pywiki.agents.langgraph.state import (
    WikiState,
    NodeStatus,
    DocumentInfo,
    AnalysisResult,
    GeneratedDoc,
    update_state_node_result,
    add_error,
)


class BaseNode(ABC):
    """节点基类"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def execute(self, state: WikiState) -> WikiState:
        """执行节点逻辑"""
        pass

    def __call__(self, state: WikiState) -> WikiState:
        """使节点可调用"""
        state = update_state_node_result(state, self.name, NodeStatus.RUNNING)
        try:
            result = asyncio.get_event_loop().run_until_complete(self.execute(state))
            return result
        except Exception as e:
            state = add_error(state, f"{self.name}: {str(e)}")
            return update_state_node_result(
                state, self.name, NodeStatus.FAILED, error=str(e)
            )


class ParseNode(BaseNode):
    """
    解析节点
    解析项目代码，提取文档信息
    """

    def __init__(self):
        super().__init__("parse")

    async def execute(self, state: WikiState) -> WikiState:
        from pywiki.parsers.factory import ParserFactory

        project_path = Path(state["project_path"])
        parser_factory = ParserFactory()
        documents: list[DocumentInfo] = []

        file_patterns = [".py", ".ts", ".tsx", ".js", ".jsx", ".java"]

        for pattern in file_patterns:
            for file_path in project_path.rglob(f"*{pattern}"):
                if self._should_skip(file_path):
                    continue

                try:
                    parser = parser_factory.get_parser(file_path)
                    result = parser.parse(file_path)

                    for cls in result.classes:
                        documents.append(DocumentInfo(
                            doc_id=f"{file_path.stem}::{cls.name}",
                            file_path=str(file_path),
                            content=cls.docstring or "",
                            doc_type="class",
                            metadata={
                                "name": cls.name,
                                "bases": cls.bases,
                                "methods": [m.name for m in cls.methods],
                            },
                        ))

                    for func in result.functions:
                        documents.append(DocumentInfo(
                            doc_id=f"{file_path.stem}::{func.name}",
                            file_path=str(file_path),
                            content=func.docstring or "",
                            doc_type="function",
                            metadata={
                                "name": func.name,
                                "parameters": func.parameters,
                                "return_type": func.return_type,
                            },
                        ))

                except Exception as e:
                    state = add_error(state, f"Parse error {file_path}: {e}")

        return update_state_node_result(
            WikiState(
                **{k: v for k, v in state.items() if k != "documents"},
                documents=documents,
            ),
            self.name,
            NodeStatus.COMPLETED,
            output={"document_count": len(documents)},
        )

    def _should_skip(self, file_path: Path) -> bool:
        skip_patterns = [
            "node_modules", "venv", ".venv", "__pycache__",
            ".git", "dist", "build", ".tox", "migrations",
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)


class AnalyzeNode(BaseNode):
    """
    分析节点
    分析代码结构，提取隐性知识
    """

    def __init__(self):
        super().__init__("analyze")

    async def execute(self, state: WikiState) -> WikiState:
        from pywiki.knowledge.implicit_extractor import ImplicitKnowledgeExtractor
        from pywiki.insights.pattern_detector import DesignPatternDetector

        project_path = Path(state["project_path"])

        pattern_detector = DesignPatternDetector()
        knowledge_extractor = ImplicitKnowledgeExtractor()

        patterns = []
        tech_debt = []
        architecture_decisions = []

        for doc in state["documents"]:
            if doc["doc_type"] == "class":
                try:
                    detected = pattern_detector.detect_patterns(
                        doc["metadata"].get("name", ""),
                        doc["metadata"].get("methods", []),
                        doc["metadata"].get("bases", []),
                    )
                    patterns.extend(detected)
                except Exception:
                    pass

        analysis = AnalysisResult(
            patterns=patterns,
            dependencies=state["context"].get("dependencies", []),
            tech_debt=tech_debt,
            architecture_decisions=architecture_decisions,
        )

        return update_state_node_result(
            WikiState(
                **{k: v for k, v in state.items() if k != "analysis"},
                analysis=analysis,
            ),
            self.name,
            NodeStatus.COMPLETED,
            output={
                "pattern_count": len(patterns),
                "tech_debt_count": len(tech_debt),
            },
        )


class GenerateNode(BaseNode):
    """
    生成节点
    生成 Wiki 文档
    """

    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__("generate")
        self.output_dir = output_dir

    async def execute(self, state: WikiState) -> WikiState:
        from pywiki.generators.markdown import MarkdownGenerator

        output_dir = self.output_dir or Path(state["project_path"]) / ".python-wiki" / "repowiki"
        output_dir.mkdir(parents=True, exist_ok=True)

        generator = MarkdownGenerator(output_dir=output_dir)
        generated_docs: list[GeneratedDoc] = []

        for doc in state["documents"]:
            try:
                content = generator.generate_class_doc(
                    doc["metadata"].get("name", ""),
                    doc["metadata"],
                    doc["content"],
                )

                doc_path = output_dir / f"{doc['doc_id'].replace('::', '_')}.md"
                generated_docs.append(GeneratedDoc(
                    doc_id=doc["doc_id"],
                    title=doc["metadata"].get("name", ""),
                    content=content,
                    doc_type=doc["doc_type"],
                    file_path=str(doc_path),
                ))

            except Exception as e:
                state = add_error(state, f"Generate error {doc['doc_id']}: {e}")

        for doc in generated_docs:
            doc_path = Path(doc["file_path"])
            doc_path.write_text(doc["content"], encoding="utf-8")

        return update_state_node_result(
            WikiState(
                **{k: v for k, v in state.items() if k != "generated_docs"},
                generated_docs=generated_docs,
            ),
            self.name,
            NodeStatus.COMPLETED,
            output={"doc_count": len(generated_docs)},
        )


class ValidateNode(BaseNode):
    """
    验证节点
    验证生成的文档质量
    """

    def __init__(self):
        super().__init__("validate")

    async def execute(self, state: WikiState) -> WikiState:
        validation_results = []
        total_score = 0.0

        for doc in state["generated_docs"]:
            score = self._calculate_doc_score(doc)
            validation_results.append({
                "doc_id": doc["doc_id"],
                "score": score,
                "issues": self._find_issues(doc),
            })
            total_score += score

        avg_score = total_score / max(len(state["generated_docs"]), 1)

        return update_state_node_result(
            state,
            self.name,
            NodeStatus.COMPLETED,
            output={
                "avg_score": avg_score,
                "validation_results": validation_results,
            },
        )

    def _calculate_doc_score(self, doc: GeneratedDoc) -> float:
        score = 0.0

        if doc["title"]:
            score += 0.2

        if doc["content"] and len(doc["content"]) > 100:
            score += 0.3

        if "## " in doc["content"]:
            score += 0.2

        if "```" in doc["content"]:
            score += 0.15

        if len(doc["content"]) > 500:
            score += 0.15

        return min(score, 1.0)

    def _find_issues(self, doc: GeneratedDoc) -> list[str]:
        issues = []

        if not doc["title"]:
            issues.append("Missing title")

        if not doc["content"] or len(doc["content"]) < 50:
            issues.append("Content too short")

        if "TODO" in doc["content"]:
            issues.append("Contains TODO markers")

        return issues


async def parse_node(state: WikiState) -> WikiState:
    """解析节点函数"""
    node = ParseNode()
    return await node.execute(state)


async def analyze_node(state: WikiState) -> WikiState:
    """分析节点函数"""
    node = AnalyzeNode()
    return await node.execute(state)


async def generate_node(state: WikiState) -> WikiState:
    """生成节点函数"""
    node = GenerateNode()
    return await node.execute(state)


async def validate_node(state: WikiState) -> WikiState:
    """验证节点函数"""
    node = ValidateNode()
    return await node.execute(state)
