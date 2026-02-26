"""
文档质量评分器测试
"""

import sys
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pywiki.wiki.quality_scorer import (
    QualityScore,
    DocQualityReport,
    QualityScorer,
)


class TestQualityScore:
    """QualityScore 数据类测试"""

    def test_create_quality_score(self):
        """测试创建质量评分"""
        score = QualityScore(
            completeness=0.8,
            readability=0.7,
            timeliness=0.9,
            structure=0.6,
            examples=0.5,
            overall=0.7,
        )

        assert score.completeness == 0.8
        assert score.readability == 0.7
        assert score.timeliness == 0.9
        assert score.structure == 0.6
        assert score.examples == 0.5
        assert score.overall == 0.7

    def test_quality_score_to_dict(self):
        """测试质量评分转换为字典"""
        score = QualityScore(
            completeness=0.85,
            readability=0.75,
            timeliness=0.95,
            structure=0.65,
            examples=0.55,
            overall=0.75,
            details={"char_count": 1000},
        )

        result = score.to_dict()

        assert result["completeness"] == 0.85
        assert result["readability"] == 0.75
        assert result["timeliness"] == 0.95
        assert result["structure"] == 0.65
        assert result["examples"] == 0.55
        assert result["overall"] == 0.75
        assert result["details"] == {"char_count": 1000}

    def test_quality_score_rounding(self):
        """测试质量评分四舍五入"""
        score = QualityScore(
            completeness=0.856789,
            readability=0.754321,
            timeliness=0.912345,
            structure=0.654321,
            examples=0.556789,
            overall=0.749999,
        )

        result = score.to_dict()

        assert result["completeness"] == 0.86
        assert result["readability"] == 0.75
        assert result["timeliness"] == 0.91


class TestDocQualityReport:
    """DocQualityReport 数据类测试"""

    def test_create_doc_quality_report(self):
        """测试创建文档质量报告"""
        doc_path = Path("/tmp/test.md")
        score = QualityScore(0.8, 0.7, 0.9, 0.6, 0.5, 0.7)

        report = DocQualityReport(
            file_path=doc_path,
            score=score,
            issues=["缺少主标题"],
            suggestions=["添加主标题"],
        )

        assert report.file_path == doc_path
        assert report.score == score
        assert report.issues == ["缺少主标题"]
        assert report.suggestions == ["添加主标题"]

    def test_doc_quality_report_to_dict(self):
        """测试文档质量报告转换为字典"""
        doc_path = Path("/tmp/test.md")
        score = QualityScore(0.8, 0.7, 0.9, 0.6, 0.5, 0.7)

        report = DocQualityReport(
            file_path=doc_path,
            score=score,
            issues=["缺少主标题"],
            suggestions=["添加主标题"],
        )

        result = report.to_dict()

        assert "test.md" in result["file_path"]
        assert result["score"]["overall"] == 0.7
        assert result["issues"] == ["缺少主标题"]
        assert result["suggestions"] == ["添加主标题"]
        assert "analyzed_at" in result

    def test_doc_quality_report_default_values(self):
        """测试文档质量报告默认值"""
        doc_path = Path("/tmp/test.md")
        score = QualityScore(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)

        report = DocQualityReport(file_path=doc_path, score=score)

        assert report.issues == []
        assert report.suggestions == []
        assert isinstance(report.analyzed_at, datetime)


class TestQualityScorer:
    """QualityScorer 测试"""

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
    def scorer(self, project_path, wiki_dir):
        """创建评分器实例"""
        return QualityScorer(project_path, wiki_dir)

    def test_required_sections_definition(self, scorer):
        """测试必要章节定义"""
        assert "description" in scorer.REQUIRED_SECTIONS
        assert "usage" in scorer.REQUIRED_SECTIONS
        assert "parameters" in scorer.REQUIRED_SECTIONS
        assert "returns" in scorer.REQUIRED_SECTIONS
        assert "examples" in scorer.REQUIRED_SECTIONS

    def test_score_document_nonexistent(self, scorer, tmp_path):
        """测试评分不存在的文档"""
        doc_path = tmp_path / "nonexistent.md"

        report = scorer.score_document(doc_path)

        assert report.score.overall == 0
        assert "文档不存在" in report.issues

    def test_score_document_minimal(self, wiki_dir, project_path):
        """测试评分最小文档"""
        doc_path = wiki_dir / "minimal.md"
        doc_path.write_text("Short")

        scorer = QualityScorer(project_path, wiki_dir)
        report = scorer.score_document(doc_path)

        assert isinstance(report, DocQualityReport)
        assert report.score.overall >= 0
        assert "文档内容过短" in report.issues

    def test_score_document_complete(self, wiki_dir, project_path):
        """测试评分完整文档"""
        content = """# API Document

## Description

This is a sample API document.

## Parameters

- `name`: Name parameter
- `value`: Value parameter

## Returns

Returns the result.

## Example

```python
result = api.call("test")
```

## Note

Please use with caution.
"""
        doc_path = wiki_dir / "complete.md"
        doc_path.write_text(content, encoding="utf-8")

        scorer = QualityScorer(project_path, wiki_dir)
        report = scorer.score_document(doc_path)

        assert report.score.completeness > 0.5
        assert report.score.structure > 0.3
        assert report.score.examples > 0.3

    def test_score_all_documents(self, wiki_dir, project_path):
        """测试评分所有文档"""
        (wiki_dir / "doc1.md").write_text("# Doc1\n\nContent 1")
        (wiki_dir / "doc2.md").write_text("# Doc2\n\nContent 2")

        scorer = QualityScorer(project_path, wiki_dir)
        reports = scorer.score_all_documents()

        assert len(reports) == 2
        assert all(isinstance(r, DocQualityReport) for r in reports)

    def test_score_all_documents_empty(self, wiki_dir, project_path):
        """测试评分空目录"""
        scorer = QualityScorer(project_path, wiki_dir)
        reports = scorer.score_all_documents()

        assert len(reports) == 0

    def test_score_completeness_short_content(self, scorer):
        """测试完整性评分 - 短内容"""
        score = scorer._score_completeness("Short")
        assert score < 0.3

    def test_score_completeness_with_headers(self, scorer):
        """测试完整性评分 - 有标题"""
        content = "# Main Title\n\n## Section\n\nSome content here."
        score = scorer._score_completeness(content)

        assert score >= 0.3

    def test_score_completeness_with_parameters(self, scorer):
        """测试完整性评分 - 有参数说明"""
        content = "# API\n\n## 参数\n\n- param1: 参数1"
        score = scorer._score_completeness(content)

        assert score >= 0.1

    def test_score_completeness_with_examples(self, scorer):
        """测试完整性评分 - 有示例"""
        content = "# API\n\n## 示例\n\n```python\npass\n```"
        score = scorer._score_completeness(content)

        assert score >= 0.1

    def test_score_completeness_max_score(self, scorer):
        """测试完整性评分 - 最高分"""
        content = """# Title

## 描述
Description here.

## 参数
Parameters here.

## 返回
Returns here.

## 示例
Example here.

## 注意
Note here.

## 参见
See also here.
"""
        score = scorer._score_completeness(content)

        assert score <= 1.0

    def test_score_readability_short_lines(self, scorer):
        """测试可读性评分 - 短行"""
        content = "Short line.\nAnother short line.\nThird line."
        score = scorer._score_readability(content)

        assert score >= 0.1

    def test_score_readability_with_lists(self, scorer):
        """测试可读性评分 - 有列表"""
        content = "# Title\n\n- Item 1\n- Item 2\n- Item 3"
        score = scorer._score_readability(content)

        assert score >= 0.1

    def test_score_readability_with_links(self, scorer):
        """测试可读性评分 - 有链接"""
        content = "See [documentation](docs.md) for details."
        score = scorer._score_readability(content)

        assert score >= 0.1

    def test_score_readability_with_code(self, scorer):
        """测试可读性评分 - 有代码"""
        content = "Use `print()` function.\n\n```python\nprint('hello')\n```"
        score = scorer._score_readability(content)

        assert score >= 0.2

    def test_score_readability_max_score(self, scorer):
        """测试可读性评分 - 最高分限制"""
        content = "# Title\n\nShort line.\n\n- List item\n\n[Link](url)\n\n**Bold**\n\n`code`\n\n```\ncode block\n```"
        score = scorer._score_readability(content)

        assert score <= 1.0

    def test_score_timeliness_recent(self, wiki_dir, project_path):
        """测试时效性评分 - 最近修改"""
        doc_path = wiki_dir / "recent.md"
        doc_path.write_text("Recent content")

        scorer = QualityScorer(project_path, wiki_dir)
        score = scorer._score_timeliness(doc_path)

        assert score == 1.0

    def test_score_timeliness_old(self, wiki_dir, project_path):
        """测试时效性评分 - 旧文件"""
        doc_path = wiki_dir / "old.md"
        doc_path.write_text("Old content")

        old_time = datetime.now() - timedelta(days=200)
        import os
        os.utime(doc_path, (old_time.timestamp(), old_time.timestamp()))

        scorer = QualityScorer(project_path, wiki_dir)
        score = scorer._score_timeliness(doc_path)

        assert score <= 0.4

    def test_score_structure_no_headers(self, scorer):
        """测试结构评分 - 无标题"""
        content = "Just plain text without headers."
        score = scorer._score_structure(content)

        assert score == 0.0

    def test_score_structure_with_main_header(self, scorer):
        """测试结构评分 - 有主标题"""
        content = "# Main Title\n\nContent here."
        score = scorer._score_structure(content)

        assert score >= 0.2

    def test_score_structure_with_multiple_levels(self, scorer):
        """测试结构评分 - 多级标题"""
        content = "# Main\n\n## Section\n\n### Subsection\n\nContent."
        score = scorer._score_structure(content)

        assert score >= 0.4

    def test_score_structure_with_toc(self, scorer):
        """测试结构评分 - 有目录"""
        content = "# Main\n\n## 目录\n\n- [Section 1](#section-1)\n\n## Section 1\n\nContent."
        score = scorer._score_structure(content)

        assert score >= 0.1

    def test_score_examples_no_code(self, scorer):
        """测试示例评分 - 无代码"""
        content = "Hello world this is plain text without anything special."
        score = scorer._score_examples(content)

        assert score < 0.1

    def test_score_examples_with_code_block(self, scorer):
        """测试示例评分 - 有代码块"""
        content = "# API\n\n```python\nprint('hello')\n```"
        score = scorer._score_examples(content)

        assert score >= 0.3

    def test_score_examples_with_inline_code(self, scorer):
        """测试示例评分 - 有内联代码"""
        content = "Use `print()` and `input()` and `open()` and `close()` functions."
        score = scorer._score_examples(content)

        assert score >= 0.1

    def test_score_examples_with_example_section(self, scorer):
        """测试示例评分 - 有示例章节"""
        content = "# API\n\n## 示例\n\nSome example content here."
        score = scorer._score_examples(content)

        assert score >= 0.2

    def test_find_issues_short_content(self, scorer):
        """测试发现问题 - 短内容"""
        issues = scorer._find_issues("Short")

        assert "文档内容过短" in issues

    def test_find_issues_no_main_header(self, scorer):
        """测试发现问题 - 无主标题"""
        content = "## Section\n\nContent without main header."
        issues = scorer._find_issues(content)

        assert "缺少主标题" in issues

    def test_find_issues_no_section_headers(self, scorer):
        """测试发现问题 - 无章节标题"""
        content = "# Main\n\nJust content without sections."
        issues = scorer._find_issues(content)

        assert "缺少章节标题" in issues

    def test_find_issues_with_todo(self, scorer):
        """测试发现问题 - 有 TODO"""
        content = "# Main\n\nTODO: implement this later."
        issues = scorer._find_issues(content)

        assert "包含待办标记" in issues

    def test_find_issues_no_code_examples(self, scorer):
        """测试发现问题 - 无代码示例"""
        content = "# Main\n\n## Section\n\nJust text."
        issues = scorer._find_issues(content)

        assert "缺少代码示例" in issues

    def test_find_issues_broken_links(self, scorer):
        """测试发现问题 - 空链接"""
        content = "# Main\n\n[Empty link]()"
        issues = scorer._find_issues(content)

        assert any("空链接" in issue for issue in issues)

    def test_find_issues_no_parameters(self, scorer):
        """测试发现问题 - 长文档无参数说明"""
        lines = ["# Main", ""] + ["Content line." for _ in range(60)]
        content = "\n".join(lines)
        issues = scorer._find_issues(content)

        assert "缺少参数说明" in issues

    def test_generate_suggestions_low_completeness(self, scorer):
        """测试生成建议 - 低完整性"""
        scores = {"completeness": 0.4, "readability": 0.8, "timeliness": 0.8, "structure": 0.8, "examples": 0.8}
        suggestions = scorer._generate_suggestions("", scores)

        assert any("必要章节" in s for s in suggestions)

    def test_generate_suggestions_low_readability(self, scorer):
        """测试生成建议 - 低可读性"""
        scores = {"completeness": 0.8, "readability": 0.4, "timeliness": 0.8, "structure": 0.8, "examples": 0.8}
        suggestions = scorer._generate_suggestions("", scores)

        assert any("段落结构" in s for s in suggestions)

    def test_generate_suggestions_low_timeliness(self, scorer):
        """测试生成建议 - 低时效性"""
        scores = {"completeness": 0.8, "readability": 0.8, "timeliness": 0.4, "structure": 0.8, "examples": 0.8}
        suggestions = scorer._generate_suggestions("", scores)

        assert any("更新文档" in s for s in suggestions)

    def test_generate_suggestions_low_structure(self, scorer):
        """测试生成建议 - 低结构"""
        scores = {"completeness": 0.8, "readability": 0.8, "timeliness": 0.8, "structure": 0.4, "examples": 0.8}
        suggestions = scorer._generate_suggestions("", scores)

        assert any("章节标题" in s for s in suggestions)

    def test_generate_suggestions_low_examples(self, scorer):
        """测试生成建议 - 低示例"""
        scores = {"completeness": 0.8, "readability": 0.8, "timeliness": 0.8, "structure": 0.8, "examples": 0.4}
        suggestions = scorer._generate_suggestions("", scores)

        assert any("代码示例" in s for s in suggestions)

    def test_generate_suggestions_good_quality(self, scorer):
        """测试生成建议 - 良好质量"""
        scores = {"completeness": 0.9, "readability": 0.9, "timeliness": 0.9, "structure": 0.9, "examples": 0.9}
        suggestions = scorer._generate_suggestions("", scores)

        assert "文档质量良好" in suggestions[0]

    def test_get_details(self, scorer):
        """测试获取详细信息"""
        content = "# Main\n\nParagraph.\n\n- Item 1\n- Item 2\n\n[Link](url)\n\n`code`"
        details = scorer._get_details(content)

        assert details["char_count"] == len(content)
        assert details["line_count"] > 0
        assert details["word_count"] > 0
        assert details["header_count"] == 1
        assert details["list_item_count"] == 2
        assert details["link_count"] == 1

    def test_get_quality_summary_empty(self, wiki_dir, project_path):
        """测试获取质量摘要 - 空目录"""
        scorer = QualityScorer(project_path, wiki_dir)
        summary = scorer.get_quality_summary()

        assert summary["total_documents"] == 0
        assert summary["avg_score"] == 0
        assert summary["quality_distribution"] == {}

    def test_get_quality_summary_with_documents(self, wiki_dir, project_path):
        """测试获取质量摘要 - 有文档"""
        (wiki_dir / "good.md").write_text("# Good\n\n## Section\n\nContent with `code`.\n\n```python\npass\n```")
        (wiki_dir / "poor.md").write_text("Short")

        scorer = QualityScorer(project_path, wiki_dir)
        summary = scorer.get_quality_summary()

        assert summary["total_documents"] == 2
        assert 0 <= summary["avg_score"] <= 1
        assert "quality_distribution" in summary
        assert "common_issues" in summary

    def test_overall_score_calculation(self, wiki_dir, project_path):
        """测试总体得分计算"""
        content = """# API Document

## Description
This is a complete API document.

## Parameters
- param1: Parameter 1

## Returns
Returns the result.

## Example
```python
api.call()
```
"""
        doc_path = wiki_dir / "test.md"
        doc_path.write_text(content, encoding="utf-8")

        scorer = QualityScorer(project_path, wiki_dir)
        report = scorer.score_document(doc_path)

        expected_overall = (
            report.score.completeness * 0.3 +
            report.score.readability * 0.2 +
            report.score.timeliness * 0.15 +
            report.score.structure * 0.2 +
            report.score.examples * 0.15
        )

        assert abs(report.score.overall - expected_overall) < 0.01
