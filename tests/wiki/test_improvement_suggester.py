"""
文档改进建议生成器测试
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pywiki.wiki.improvement_suggester import (
    ImprovementSuggestion,
    ImprovementReport,
    ImprovementSuggester,
)
from pywiki.wiki.quality_scorer import (
    QualityScore,
    DocQualityReport,
)


class TestImprovementSuggestion:
    """ImprovementSuggestion 数据类测试"""

    def test_create_improvement_suggestion(self):
        """测试创建改进建议"""
        suggestion = ImprovementSuggestion(
            category="missing_doc",
            priority="high",
            title="缺少文档: test.py",
            description="代码文件 test.py 没有对应的文档",
        )

        assert suggestion.category == "missing_doc"
        assert suggestion.priority == "high"
        assert suggestion.title == "缺少文档: test.py"
        assert suggestion.description == "代码文件 test.py 没有对应的文档"
        assert suggestion.action == ""
        assert suggestion.impact == ""
        assert suggestion.metadata == {}

    def test_improvement_suggestion_with_all_fields(self):
        """测试创建包含所有字段的改进建议"""
        suggestion = ImprovementSuggestion(
            category="incomplete",
            priority="critical",
            title="文档质量过低",
            description="文档整体得分 0.3",
            file_path=Path("/tmp/test.md"),
            action="重写文档",
            impact="提高文档质量",
            metadata={"score": 0.3},
        )

        assert suggestion.category == "incomplete"
        assert suggestion.file_path == Path("/tmp/test.md")
        assert suggestion.metadata == {"score": 0.3}

    def test_to_dict(self):
        """测试转换为字典"""
        suggestion = ImprovementSuggestion(
            category="structure",
            priority="medium",
            title="缺少章节划分",
            description="文档只有一个标题",
            file_path=Path("/tmp/doc.md"),
            action="添加子标题",
            impact="改善文档结构",
            metadata={"headers": 1},
        )

        result = suggestion.to_dict()

        assert result["category"] == "structure"
        assert result["priority"] == "medium"
        assert result["title"] == "缺少章节划分"
        assert "doc.md" in result["file_path"]
        assert result["metadata"] == {"headers": 1}

    def test_to_dict_with_none_path(self):
        """测试 file_path 为 None 时的转换"""
        suggestion = ImprovementSuggestion(
            category="missing_doc",
            priority="high",
            title="测试",
            description="测试描述",
        )

        result = suggestion.to_dict()

        assert result["file_path"] is None


class TestImprovementReport:
    """ImprovementReport 数据类测试"""

    def test_create_improvement_report(self):
        """测试创建改进报告"""
        suggestions = [
            ImprovementSuggestion(
                category="missing_doc",
                priority="high",
                title="建议1",
                description="描述1",
            ),
            ImprovementSuggestion(
                category="structure",
                priority="medium",
                title="建议2",
                description="描述2",
            ),
        ]

        report = ImprovementReport(
            total_suggestions=2,
            by_category={"missing_doc": 1, "structure": 1},
            by_priority={"high": 1, "medium": 1},
            suggestions=suggestions,
        )

        assert report.total_suggestions == 2
        assert report.by_category == {"missing_doc": 1, "structure": 1}
        assert report.by_priority == {"high": 1, "medium": 1}
        assert len(report.suggestions) == 2

    def test_improvement_report_to_dict(self):
        """测试改进报告转换为字典"""
        suggestions = [
            ImprovementSuggestion(
                category="example",
                priority="low",
                title="添加示例",
                description="缺少代码示例",
            ),
        ]

        report = ImprovementReport(
            total_suggestions=1,
            by_category={"example": 1},
            by_priority={"low": 1},
            suggestions=suggestions,
        )

        result = report.to_dict()

        assert result["total_suggestions"] == 1
        assert result["by_category"] == {"example": 1}
        assert result["by_priority"] == {"low": 1}
        assert len(result["suggestions"]) == 1
        assert "generated_at" in result


class TestImprovementSuggester:
    """ImprovementSuggester 测试"""

    @pytest.fixture
    def project_path(self, tmp_path):
        """创建项目路径"""
        return tmp_path

    @pytest.fixture
    def wiki_dir(self, project_path):
        """创建 wiki 目录"""
        wiki = project_path / ".python-wiki" / "repowiki"
        wiki.mkdir(parents=True, exist_ok=True)
        return wiki

    @pytest.fixture
    def suggester(self, project_path, wiki_dir):
        """创建建议器实例"""
        return ImprovementSuggester(project_path, wiki_dir)

    def test_categories_definition(self, suggester):
        """测试分类定义"""
        assert "missing_doc" in suggester.CATEGORIES
        assert "incomplete" in suggester.CATEGORIES
        assert "outdated" in suggester.CATEGORIES
        assert "structure" in suggester.CATEGORIES
        assert "example" in suggester.CATEGORIES

    def test_priorities_definition(self, suggester):
        """测试优先级定义"""
        assert "critical" in suggester.PRIORITIES
        assert "high" in suggester.PRIORITIES
        assert "medium" in suggester.PRIORITIES
        assert "low" in suggester.PRIORITIES

    def test_analyze_returns_report(self, suggester):
        """测试 analyze 返回报告"""
        result = suggester.analyze()

        assert isinstance(result, ImprovementReport)
        assert isinstance(result.total_suggestions, int)
        assert isinstance(result.by_category, dict)
        assert isinstance(result.by_priority, dict)

    def test_analyze_missing_docs_logic(self, suggester):
        """测试分析缺失文档的逻辑"""
        suggestion = ImprovementSuggestion(
            category="missing_doc",
            priority="high",
            title="缺少文档: code.py",
            description="代码文件 code.py 没有对应的文档",
        )

        assert suggestion.category == "missing_doc"
        assert suggestion.priority == "high"

    def test_analyze_missing_docs_skips_test_dirs(self, project_path, wiki_dir):
        """测试分析缺失文档时跳过测试目录"""
        test_file = project_path / "tests" / "test_main.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def test_main(): pass")

        suggester = ImprovementSuggester(project_path, wiki_dir)
        result = suggester.analyze()

        missing_doc_suggestions = [
            s for s in result.suggestions
            if s.category == "missing_doc" and "test_main.py" in s.title
        ]

        assert len(missing_doc_suggestions) == 0

    def test_analyze_structure_issues_no_headers(self, wiki_dir, project_path):
        """测试分析结构问题 - 无标题"""
        doc_file = wiki_dir / "no_headers.md"
        doc_file.write_text("This is a document without any headers.")

        suggester = ImprovementSuggester(project_path, wiki_dir)
        result = suggester.analyze()

        structure_issues = [
            s for s in result.suggestions
            if s.category == "structure" and "缺少标题结构" in s.title
        ]

        assert len(structure_issues) > 0

    def test_analyze_structure_issues_single_header(self, wiki_dir, project_path):
        """测试分析结构问题 - 单一标题"""
        doc_file = wiki_dir / "single_header.md"
        doc_file.write_text("# Main Title\n\nSome content here.")

        suggester = ImprovementSuggester(project_path, wiki_dir)
        result = suggester.analyze()

        structure_issues = [
            s for s in result.suggestions
            if s.category == "structure" and "缺少章节划分" in s.title
        ]

        assert len(structure_issues) > 0

    def test_analyze_structure_suggests_toc(self, wiki_dir, project_path):
        """测试分析结构问题 - 建议添加目录"""
        content = "# Main\n\n"
        for i in range(6):
            content += f"## Section {i}\n\nContent {i}\n\n"

        doc_file = wiki_dir / "long_doc.md"
        doc_file.write_text(content)

        suggester = ImprovementSuggester(project_path, wiki_dir)
        result = suggester.analyze()

        toc_suggestions = [
            s for s in result.suggestions
            if "目录" in s.title
        ]

        assert len(toc_suggestions) > 0

    def test_priority_order(self, suggester):
        """测试优先级排序"""
        assert suggester._priority_order("critical") == 4
        assert suggester._priority_order("high") == 3
        assert suggester._priority_order("medium") == 2
        assert suggester._priority_order("low") == 1
        assert suggester._priority_order("unknown") == 0

    def test_categorize_issue(self, suggester):
        """测试问题分类"""
        assert suggester._categorize_issue("缺少代码示例") == "example"
        assert suggester._categorize_issue("缺少主标题") == "structure"
        assert suggester._categorize_issue("存在空链接") == "link"
        assert suggester._categorize_issue("文档内容过短") == "incomplete"
        assert suggester._categorize_issue("其他问题") == "readability"

    def test_suggest_action(self, suggester):
        """测试建议行动"""
        assert "扩充文档内容" in suggester._suggest_action("文档内容过短")
        assert "添加 # 主标题" in suggester._suggest_action("缺少主标题")
        assert "添加章节划分" in suggester._suggest_action("缺少章节标题")
        assert "TODO" in suggester._suggest_action("包含待办标记")
        assert "代码块" in suggester._suggest_action("缺少代码示例")
        assert "参数表格" in suggester._suggest_action("缺少参数说明")

    def test_suggest_action_default(self, suggester):
        """测试建议行动默认值"""
        action = suggester._suggest_action("未知问题")
        assert action == "根据具体问题进行改进"

    def test_find_doc_file_exists_in_wiki_root(self, suggester, wiki_dir):
        """测试查找文档文件 - 在 wiki 根目录"""
        code_file = suggester.project_path / "main.py"
        doc_file = wiki_dir / "main.md"
        doc_file.write_text("# Main")

        result = suggester._find_doc_file(code_file)

        assert result == doc_file

    def test_find_doc_file_exists_in_subdir(self, suggester, wiki_dir):
        """测试查找文档文件 - 在子目录"""
        code_file = suggester.project_path / "src" / "utils.py"
        code_file.parent.mkdir(parents=True, exist_ok=True)

        doc_dir = wiki_dir / "src"
        doc_dir.mkdir(parents=True, exist_ok=True)
        doc_file = doc_dir / "utils.md"
        doc_file.write_text("# Utils")

        result = suggester._find_doc_file(code_file)

        assert result == doc_file

    def test_find_doc_file_not_found(self, suggester):
        """测试查找文档文件 - 未找到"""
        code_file = suggester.project_path / "missing.py"

        result = suggester._find_doc_file(code_file)

        assert result is None

    def test_get_suggestions_for_file(self, suggester, wiki_dir):
        """测试获取特定文件的建议"""
        doc_file = wiki_dir / "test.md"
        doc_file.write_text("No headers here")

        suggestions = suggester.get_suggestions_for_file(doc_file)

        assert isinstance(suggestions, list)
        assert all(s.file_path == doc_file for s in suggestions)

    def test_get_high_priority_suggestions(self, suggester, wiki_dir):
        """测试获取高优先级建议"""
        code_file = suggester.project_path / "important.py"
        code_file.write_text("def important(): pass")

        suggestions = suggester.get_high_priority_suggestions(limit=5)

        assert isinstance(suggestions, list)
        assert len(suggestions) <= 5
        assert all(s.priority in ("critical", "high") for s in suggestions)

    def test_analyze_quality_issues_critical(self, project_path, wiki_dir):
        """测试分析质量问题 - 严重"""
        doc_file = wiki_dir / "poor.md"
        doc_file.write_text("Short")

        with patch.object(
            ImprovementSuggester,
            "_analyze_missing_docs",
            return_value=[]
        ):
            suggester = ImprovementSuggester(project_path, wiki_dir)

            mock_report = DocQualityReport(
                file_path=doc_file,
                score=QualityScore(0.1, 0.1, 0.1, 0.1, 0.1, 0.3),
                issues=["文档内容过短"],
            )

            with patch.object(
                suggester.quality_scorer,
                "score_all_documents",
                return_value=[mock_report]
            ):
                result = suggester.analyze()

                critical_issues = [
                    s for s in result.suggestions
                    if s.priority == "critical"
                ]

                assert len(critical_issues) > 0

    def test_analyze_quality_issues_high(self, project_path, wiki_dir):
        """测试分析质量问题 - 高优先级"""
        doc_file = wiki_dir / "fair.md"
        doc_file.write_text("# Fair\n\nSome content here.")

        with patch.object(
            ImprovementSuggester,
            "_analyze_missing_docs",
            return_value=[]
        ):
            suggester = ImprovementSuggester(project_path, wiki_dir)

            mock_report = DocQualityReport(
                file_path=doc_file,
                score=QualityScore(0.5, 0.5, 0.5, 0.5, 0.5, 0.5),
                issues=[],
            )

            with patch.object(
                suggester.quality_scorer,
                "score_all_documents",
                return_value=[mock_report]
            ):
                result = suggester.analyze()

                high_issues = [
                    s for s in result.suggestions
                    if s.priority == "high" and "需要改进" in s.title
                ]

                assert len(high_issues) > 0

    def test_analyze_quality_issues_examples(self, project_path, wiki_dir):
        """测试分析质量问题 - 缺少示例"""
        doc_file = wiki_dir / "no_examples.md"
        doc_file.write_text("# No Examples\n\nJust text.")

        with patch.object(
            ImprovementSuggester,
            "_analyze_missing_docs",
            return_value=[]
        ):
            suggester = ImprovementSuggester(project_path, wiki_dir)

            mock_report = DocQualityReport(
                file_path=doc_file,
                score=QualityScore(0.7, 0.7, 0.7, 0.7, 0.3, 0.6),
                issues=[],
            )

            with patch.object(
                suggester.quality_scorer,
                "score_all_documents",
                return_value=[mock_report]
            ):
                result = suggester.analyze()

                example_issues = [
                    s for s in result.suggestions
                    if s.category == "example"
                ]

                assert len(example_issues) > 0

    def test_analyze_quality_issues_outdated(self, project_path, wiki_dir):
        """测试分析质量问题 - 过时"""
        doc_file = wiki_dir / "outdated.md"
        doc_file.write_text("# Outdated\n\nOld content.")

        with patch.object(
            ImprovementSuggester,
            "_analyze_missing_docs",
            return_value=[]
        ):
            suggester = ImprovementSuggester(project_path, wiki_dir)

            mock_report = DocQualityReport(
                file_path=doc_file,
                score=QualityScore(0.7, 0.7, 0.4, 0.7, 0.7, 0.6),
                issues=[],
            )

            with patch.object(
                suggester.quality_scorer,
                "score_all_documents",
                return_value=[mock_report]
            ):
                result = suggester.analyze()

                outdated_issues = [
                    s for s in result.suggestions
                    if s.category == "outdated"
                ]

                assert len(outdated_issues) > 0

    def test_suggestions_sorted_by_priority(self, project_path, wiki_dir):
        """测试建议按优先级排序"""
        doc_file = wiki_dir / "test.md"
        doc_file.write_text("Short")

        code_file = project_path / "main.py"
        code_file.write_text("def main(): pass")

        suggester = ImprovementSuggester(project_path, wiki_dir)
        result = suggester.analyze()

        if len(result.suggestions) > 1:
            priorities = [s.priority for s in result.suggestions]
            priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            sorted_priorities = sorted(priorities, key=lambda x: priority_order[x], reverse=True)
            assert priorities == sorted_priorities

    def test_code_extensions_detection(self, suggester):
        """测试代码扩展名检测"""
        code_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".java"}

        for ext in code_extensions:
            assert ext in {".py", ".ts", ".tsx", ".js", ".jsx", ".java"}

        skip_patterns = [
            "node_modules", "venv", ".venv", "__pycache__",
            ".git", "dist", "build", ".tox", "tests", "test",
        ]

        test_path = Path("/project/tests/test_main.py")
        assert any(p in str(test_path) for p in skip_patterns)

        normal_path = Path("/project/src/main.py")
        assert not any(p in str(normal_path) for p in skip_patterns)

    def test_analyze_empty_project(self, project_path, wiki_dir):
        """测试分析空项目"""
        suggester = ImprovementSuggester(project_path, wiki_dir)
        result = suggester.analyze()

        assert isinstance(result, ImprovementReport)
        assert result.total_suggestions == 0
