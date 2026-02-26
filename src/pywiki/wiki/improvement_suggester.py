"""
文档改进建议生成器
分析文档缺失和改进点
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pywiki.wiki.quality_scorer import QualityScorer, DocQualityReport


@dataclass
class ImprovementSuggestion:
    """改进建议"""
    category: str
    priority: str
    title: str
    description: str
    file_path: Optional[Path] = None
    action: str = ""
    impact: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "file_path": str(self.file_path) if self.file_path else None,
            "action": self.action,
            "impact": self.impact,
            "metadata": self.metadata,
        }


@dataclass
class ImprovementReport:
    """改进报告"""
    total_suggestions: int
    by_category: dict[str, int]
    by_priority: dict[str, int]
    suggestions: list[ImprovementSuggestion] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_suggestions": self.total_suggestions,
            "by_category": self.by_category,
            "by_priority": self.by_priority,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "generated_at": self.generated_at.isoformat(),
        }


class ImprovementSuggester:
    """
    文档改进建议生成器
    分析文档并生成改进建议
    """

    CATEGORIES = {
        "missing_doc": "缺失文档",
        "incomplete": "内容不完整",
        "outdated": "内容过时",
        "structure": "结构问题",
        "example": "缺少示例",
        "readability": "可读性问题",
        "link": "链接问题",
    }

    PRIORITIES = {
        "critical": "紧急",
        "high": "高",
        "medium": "中",
        "low": "低",
    }

    def __init__(
        self,
        project_path: Path,
        wiki_dir: Optional[Path] = None,
    ):
        self.project_path = Path(project_path)
        self.wiki_dir = wiki_dir or self.project_path / ".python-wiki" / "repowiki"
        self.quality_scorer = QualityScorer(project_path, wiki_dir)

    def analyze(self) -> ImprovementReport:
        """
        分析并生成改进建议

        Returns:
            改进报告
        """
        suggestions = []

        suggestions.extend(self._analyze_missing_docs())
        suggestions.extend(self._analyze_quality_issues())
        suggestions.extend(self._analyze_structure_issues())

        suggestions.sort(key=lambda x: self._priority_order(x.priority), reverse=True)

        by_category: dict[str, int] = {}
        by_priority: dict[str, int] = {}

        for s in suggestions:
            by_category[s.category] = by_category.get(s.category, 0) + 1
            by_priority[s.priority] = by_priority.get(s.priority, 0) + 1

        return ImprovementReport(
            total_suggestions=len(suggestions),
            by_category=by_category,
            by_priority=by_priority,
            suggestions=suggestions,
        )

    def _analyze_missing_docs(self) -> list[ImprovementSuggestion]:
        """分析缺失的文档"""
        suggestions = []

        code_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".java"}
        skip_patterns = [
            "node_modules", "venv", ".venv", "__pycache__",
            ".git", "dist", "build", ".tox", "tests", "test",
        ]

        for ext in code_extensions:
            for code_file in self.project_path.rglob(f"*{ext}"):
                if any(p in str(code_file) for p in skip_patterns):
                    continue

                doc_file = self._find_doc_file(code_file)
                if doc_file is None:
                    suggestions.append(ImprovementSuggestion(
                        category="missing_doc",
                        priority="high",
                        title=f"缺少文档: {code_file.name}",
                        description=f"代码文件 {code_file.relative_to(self.project_path)} 没有对应的文档",
                        file_path=code_file,
                        action=f"为 {code_file.stem} 创建文档",
                        impact="提高代码可维护性和可读性",
                        metadata={
                            "code_file": str(code_file),
                            "suggested_doc_name": f"{code_file.stem}.md",
                        },
                    ))

        return suggestions

    def _analyze_quality_issues(self) -> list[ImprovementSuggestion]:
        """分析质量问题"""
        suggestions = []

        quality_reports = self.quality_scorer.score_all_documents()

        for report in quality_reports:
            if report.score.overall < 0.4:
                suggestions.append(ImprovementSuggestion(
                    category="incomplete",
                    priority="critical",
                    title=f"文档质量过低: {report.file_path.name}",
                    description=f"文档整体得分 {report.score.overall:.2f}，需要全面改进",
                    file_path=report.file_path,
                    action="重写或大幅改进文档内容",
                    impact="显著提高文档质量",
                    metadata={"score": report.score.to_dict()},
                ))

            elif report.score.overall < 0.6:
                suggestions.append(ImprovementSuggestion(
                    category="incomplete",
                    priority="high",
                    title=f"文档需要改进: {report.file_path.name}",
                    description=f"文档整体得分 {report.score.overall:.2f}",
                    file_path=report.file_path,
                    action="根据建议改进文档内容",
                    impact="提高文档质量",
                    metadata={"score": report.score.to_dict()},
                ))

            for issue in report.issues:
                priority = "medium"
                if "过短" in issue or "缺少主标题" in issue:
                    priority = "high"

                suggestions.append(ImprovementSuggestion(
                    category=self._categorize_issue(issue),
                    priority=priority,
                    title=issue,
                    description=f"在 {report.file_path.name} 中发现: {issue}",
                    file_path=report.file_path,
                    action=self._suggest_action(issue),
                    impact="改善文档质量",
                ))

            if report.score.examples < 0.4:
                suggestions.append(ImprovementSuggestion(
                    category="example",
                    priority="medium",
                    title=f"缺少示例: {report.file_path.name}",
                    description="文档缺少代码示例和使用说明",
                    file_path=report.file_path,
                    action="添加代码示例和使用场景说明",
                    impact="提高文档实用性",
                ))

            if report.score.timeliness < 0.5:
                suggestions.append(ImprovementSuggestion(
                    category="outdated",
                    priority="high",
                    title=f"文档可能过时: {report.file_path.name}",
                    description="文档较长时间未更新，可能需要同步最新代码变更",
                    file_path=report.file_path,
                    action="检查代码变更并更新文档",
                    impact="确保文档与代码同步",
                ))

        return suggestions

    def _analyze_structure_issues(self) -> list[ImprovementSuggestion]:
        """分析结构问题"""
        suggestions = []

        for doc_path in self.wiki_dir.rglob("*.md"):
            content = doc_path.read_text(encoding="utf-8")

            import re

            headers = re.findall(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE)

            if not headers:
                suggestions.append(ImprovementSuggestion(
                    category="structure",
                    priority="high",
                    title=f"缺少标题结构: {doc_path.name}",
                    description="文档没有任何标题，难以导航",
                    file_path=doc_path,
                    action="添加主标题和章节标题",
                    impact="改善文档可读性",
                ))

            elif len(headers) == 1:
                suggestions.append(ImprovementSuggestion(
                    category="structure",
                    priority="medium",
                    title=f"缺少章节划分: {doc_path.name}",
                    description="文档只有一个标题，建议添加章节",
                    file_path=doc_path,
                    action="添加子标题划分内容",
                    impact="改善文档结构",
                ))

            toc_keywords = ["目录", "Table of Contents", "TOC"]
            has_toc = any(kw in content for kw in toc_keywords)

            if len(headers) > 5 and not has_toc:
                suggestions.append(ImprovementSuggestion(
                    category="structure",
                    priority="low",
                    title=f"建议添加目录: {doc_path.name}",
                    description="文档章节较多，建议添加目录",
                    file_path=doc_path,
                    action="在文档开头添加目录",
                    impact="方便快速导航",
                ))

        return suggestions

    def _find_doc_file(self, code_file: Path) -> Optional[Path]:
        """查找代码文件对应的文档"""
        doc_name = code_file.stem + ".md"

        doc_path = self.wiki_dir / doc_name
        if doc_path.exists():
            return doc_path

        relative_path = code_file.relative_to(self.project_path)
        doc_path = self.wiki_dir / relative_path.parent / doc_name
        if doc_path.exists():
            return doc_path

        return None

    def _categorize_issue(self, issue: str) -> str:
        """将问题分类"""
        if "示例" in issue or "代码" in issue:
            return "example"
        elif "标题" in issue or "章节" in issue:
            return "structure"
        elif "链接" in issue:
            return "link"
        elif "过短" in issue or "缺少" in issue:
            return "incomplete"
        else:
            return "readability"

    def _suggest_action(self, issue: str) -> str:
        """建议行动"""
        actions = {
            "文档内容过短": "扩充文档内容，添加更多细节",
            "缺少主标题": "在文档开头添加 # 主标题",
            "缺少章节标题": "使用 ## 添加章节划分",
            "包含待办标记": "处理并移除 TODO/FIXME 标记",
            "缺少代码示例": "添加代码块展示用法",
            "缺少参数说明": "添加参数表格说明",
        }

        for key, action in actions.items():
            if key in issue:
                return action

        return "根据具体问题进行改进"

    def _priority_order(self, priority: str) -> int:
        """优先级排序"""
        order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return order.get(priority, 0)

    def get_suggestions_for_file(self, file_path: Path) -> list[ImprovementSuggestion]:
        """获取特定文件的改进建议"""
        report = self.analyze()
        return [s for s in report.suggestions if s.file_path == file_path]

    def get_high_priority_suggestions(self, limit: int = 10) -> list[ImprovementSuggestion]:
        """获取高优先级建议"""
        report = self.analyze()
        high_priority = [
            s for s in report.suggestions
            if s.priority in ("critical", "high")
        ]
        return high_priority[:limit]
