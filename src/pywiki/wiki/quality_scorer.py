"""
文档质量评分器
评估文档的完整性、可读性和时效性
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional


@dataclass
class QualityScore:
    """质量评分"""
    completeness: float
    readability: float
    timeliness: float
    structure: float
    examples: float
    overall: float
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "completeness": round(self.completeness, 2),
            "readability": round(self.readability, 2),
            "timeliness": round(self.timeliness, 2),
            "structure": round(self.structure, 2),
            "examples": round(self.examples, 2),
            "overall": round(self.overall, 2),
            "details": self.details,
        }


@dataclass
class DocQualityReport:
    """文档质量报告"""
    file_path: Path
    score: QualityScore
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    analyzed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": str(self.file_path),
            "score": self.score.to_dict(),
            "issues": self.issues,
            "suggestions": self.suggestions,
            "analyzed_at": self.analyzed_at.isoformat(),
        }


class QualityScorer:
    """
    文档质量评分器
    评估文档的多个维度
    """

    REQUIRED_SECTIONS = [
        "description",
        "usage",
        "parameters",
        "returns",
        "examples",
    ]

    def __init__(
        self,
        project_path: Path,
        wiki_dir: Optional[Path] = None,
    ):
        self.project_path = Path(project_path)
        self.wiki_dir = wiki_dir or self.project_path / ".python-wiki" / "repowiki"

    def score_document(self, doc_path: Path) -> DocQualityReport:
        """
        评估单个文档

        Args:
            doc_path: 文档路径

        Returns:
            文档质量报告
        """
        if not doc_path.exists():
            return DocQualityReport(
                file_path=doc_path,
                score=QualityScore(0, 0, 0, 0, 0, 0),
                issues=["文档不存在"],
            )

        content = doc_path.read_text(encoding="utf-8")

        completeness = self._score_completeness(content)
        readability = self._score_readability(content)
        timeliness = self._score_timeliness(doc_path)
        structure = self._score_structure(content)
        examples = self._score_examples(content)

        overall = (
            completeness * 0.3 +
            readability * 0.2 +
            timeliness * 0.15 +
            structure * 0.2 +
            examples * 0.15
        )

        issues = self._find_issues(content)
        suggestions = self._generate_suggestions(content, {
            "completeness": completeness,
            "readability": readability,
            "timeliness": timeliness,
            "structure": structure,
            "examples": examples,
        })

        return DocQualityReport(
            file_path=doc_path,
            score=QualityScore(
                completeness=completeness,
                readability=readability,
                timeliness=timeliness,
                structure=structure,
                examples=examples,
                overall=overall,
                details=self._get_details(content),
            ),
            issues=issues,
            suggestions=suggestions,
        )

    def score_all_documents(self) -> list[DocQualityReport]:
        """评估所有文档"""
        reports = []

        for doc_path in self.wiki_dir.rglob("*.md"):
            report = self.score_document(doc_path)
            reports.append(report)

        return reports

    def _score_completeness(self, content: str) -> float:
        """评分完整性"""
        score = 0.0

        if len(content) > 100:
            score += 0.2

        if re.search(r"^#\s+.+", content, re.MULTILINE):
            score += 0.15

        if re.search(r"^##\s+.+", content, re.MULTILINE):
            score += 0.15

        if re.search(r"(参数|Parameters|Args|Arguments)", content, re.IGNORECASE):
            score += 0.1

        if re.search(r"(返回|Returns|Return)", content, re.IGNORECASE):
            score += 0.1

        if re.search(r"(示例|Example|Usage)", content, re.IGNORECASE):
            score += 0.1

        if re.search(r"(说明|Description|Overview)", content, re.IGNORECASE):
            score += 0.1

        if re.search(r"(注意|Note|Warning|Caution)", content, re.IGNORECASE):
            score += 0.05

        if re.search(r"(参见|See Also|Related)", content, re.IGNORECASE):
            score += 0.05

        return min(score, 1.0)

    def _score_readability(self, content: str) -> float:
        """评分可读性"""
        score = 0.0

        lines = content.split("\n")
        non_empty_lines = [l for l in lines if l.strip()]

        if non_empty_lines:
            avg_line_length = sum(len(l) for l in non_empty_lines) / len(non_empty_lines)
            if avg_line_length < 100:
                score += 0.2
            elif avg_line_length < 150:
                score += 0.1

        paragraph_count = len(re.split(r"\n\s*\n", content))
        if paragraph_count > 1:
            score += 0.15

        list_count = len(re.findall(r"^\s*[-*+]\s+", content, re.MULTILINE))
        if list_count > 0:
            score += 0.15

        link_count = len(re.findall(r"\[.+?\]\(.+?\)", content))
        if link_count > 0:
            score += 0.1

        emphasis_count = len(re.findall(r"\*\*.+?\*\*|__.+?__", content))
        if emphasis_count > 0:
            score += 0.1

        code_block_count = len(re.findall(r"```", content)) // 2
        inline_code_count = len(re.findall(r"`[^`]+`", content))
        if code_block_count > 0 or inline_code_count > 0:
            score += 0.2

        header_count = len(re.findall(r"^#{1,6}\s+", content, re.MULTILINE))
        if header_count > 0:
            score += 0.1

        return min(score, 1.0)

    def _score_timeliness(self, doc_path: Path) -> float:
        """评分时效性"""
        try:
            stat = doc_path.stat()
            modified_time = datetime.fromtimestamp(stat.st_mtime)
            age_days = (datetime.now() - modified_time).days

            if age_days <= 7:
                return 1.0
            elif age_days <= 30:
                return 0.8
            elif age_days <= 90:
                return 0.6
            elif age_days <= 180:
                return 0.4
            else:
                return 0.2
        except Exception:
            return 0.5

    def _score_structure(self, content: str) -> float:
        """评分结构"""
        score = 0.0

        headers = re.findall(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE)

        if headers:
            score += 0.2

            levels = [len(h[0]) for h in headers]
            if min(levels) == 1:
                score += 0.15

            if len(set(levels)) > 1:
                score += 0.15

            if len(headers) >= 3:
                score += 0.2

            toc_keywords = ["目录", "Table of Contents", "TOC", "Contents"]
            if any(kw in content for kw in toc_keywords):
                score += 0.1

        if re.search(r"^---\s*$", content, re.MULTILINE):
            score += 0.1

        if re.search(r"^\*\*.+\*\*:\s*", content, re.MULTILINE):
            score += 0.1

        return min(score, 1.0)

    def _score_examples(self, content: str) -> float:
        """评分示例"""
        score = 0.0

        code_blocks = re.findall(r"```(\w*)\n(.*?)```", content, re.DOTALL)

        if code_blocks:
            score += 0.3

            languages = set(cb[0] for cb in code_blocks if cb[0])
            if len(languages) > 1:
                score += 0.1

            for lang, code in code_blocks:
                if len(code.strip()) > 50:
                    score += 0.1
                    break

        inline_code = re.findall(r"`([^`]+)`", content)
        if len(inline_code) > 3:
            score += 0.2

        example_sections = re.findall(
            r"(?:示例|Example|Usage).*?(?=##|$)",
            content,
            re.IGNORECASE | re.DOTALL,
        )
        if example_sections:
            score += 0.2

        return min(score, 1.0)

    def _find_issues(self, content: str) -> list[str]:
        """发现问题"""
        issues = []

        if len(content) < 50:
            issues.append("文档内容过短")

        if not re.search(r"^#\s+.+", content, re.MULTILINE):
            issues.append("缺少主标题")

        if not re.search(r"^##\s+.+", content, re.MULTILINE):
            issues.append("缺少章节标题")

        if "TODO" in content or "FIXME" in content:
            issues.append("包含待办标记")

        if not re.search(r"```", content):
            issues.append("缺少代码示例")

        if len(content.split("\n")) > 50:
            if not re.search(r"(参数|Parameters|Args)", content, re.IGNORECASE):
                issues.append("缺少参数说明")

        broken_links = re.findall(r"\[.+?\]\(\s*\)", content)
        if broken_links:
            issues.append(f"存在 {len(broken_links)} 个空链接")

        return issues

    def _generate_suggestions(
        self,
        content: str,
        scores: dict[str, float],
    ) -> list[str]:
        """生成改进建议"""
        suggestions = []

        if scores["completeness"] < 0.6:
            suggestions.append("添加更多必要章节（描述、参数、返回值、示例）")

        if scores["readability"] < 0.6:
            suggestions.append("优化段落结构，添加列表和代码块")

        if scores["timeliness"] < 0.6:
            suggestions.append("更新文档以反映最新变更")

        if scores["structure"] < 0.6:
            suggestions.append("添加章节标题，改善文档层次结构")

        if scores["examples"] < 0.6:
            suggestions.append("添加代码示例和使用说明")

        if not suggestions:
            suggestions.append("文档质量良好，继续保持")

        return suggestions

    def _get_details(self, content: str) -> dict[str, Any]:
        """获取详细信息"""
        return {
            "char_count": len(content),
            "line_count": len(content.split("\n")),
            "word_count": len(content.split()),
            "header_count": len(re.findall(r"^#{1,6}\s+", content, re.MULTILINE)),
            "code_block_count": len(re.findall(r"```", content)) // 2,
            "link_count": len(re.findall(r"\[.+?\]\(.+?\)", content)),
            "list_item_count": len(re.findall(r"^\s*[-*+]\s+", content, re.MULTILINE)),
        }

    def get_quality_summary(self) -> dict[str, Any]:
        """获取质量摘要"""
        reports = self.score_all_documents()

        if not reports:
            return {
                "total_documents": 0,
                "avg_score": 0,
                "quality_distribution": {},
            }

        scores = [r.score.overall for r in reports]
        avg_score = sum(scores) / len(scores)

        distribution = {
            "excellent": sum(1 for s in scores if s >= 0.8),
            "good": sum(1 for s in scores if 0.6 <= s < 0.8),
            "fair": sum(1 for s in scores if 0.4 <= s < 0.6),
            "poor": sum(1 for s in scores if s < 0.4),
        }

        all_issues = []
        for r in reports:
            all_issues.extend(r.issues)

        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        return {
            "total_documents": len(reports),
            "avg_score": round(avg_score, 2),
            "quality_distribution": distribution,
            "common_issues": sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5],
        }
