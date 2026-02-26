"""
文档滞后检测器
检测代码变更但文档未更新的情况
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from pywiki.sync.git_change_detector import GitChangeDetector, ChangeType, FileChange


@dataclass
class DocLagItem:
    """文档滞后项"""
    code_file: Path
    doc_file: Optional[Path]
    code_last_modified: datetime
    doc_last_modified: Optional[datetime]
    lag_days: int
    lag_severity: str
    code_changes: int
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code_file": str(self.code_file),
            "doc_file": str(self.doc_file) if self.doc_file else None,
            "code_last_modified": self.code_last_modified.isoformat(),
            "doc_last_modified": self.doc_last_modified.isoformat() if self.doc_last_modified else None,
            "lag_days": self.lag_days,
            "lag_severity": self.lag_severity,
            "code_changes": self.code_changes,
            "suggestions": self.suggestions,
        }


@dataclass
class DocLagReport:
    """文档滞后报告"""
    total_files: int
    lagging_files: int
    missing_docs: int
    items: list[DocLagItem] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_files": self.total_files,
            "lagging_files": self.lagging_files,
            "missing_docs": self.missing_docs,
            "items": [item.to_dict() for item in self.items],
            "generated_at": self.generated_at.isoformat(),
        }


class DocLagDetector:
    """
    文档滞后检测器
    检测代码变更但文档未更新的情况
    """

    CODE_EXTENSIONS = {
        ".py", ".ts", ".tsx", ".js", ".jsx", ".java",
        ".go", ".rs", ".cpp", ".c", ".h", ".hpp",
    }

    DOC_PATTERNS = {
        ".py": [".md", ".rst"],
        ".ts": [".md"],
        ".tsx": [".md"],
        ".js": [".md"],
        ".java": [".md"],
    }

    SEVERITY_THRESHOLDS = {
        "low": 7,
        "medium": 30,
        "high": 90,
        "critical": 180,
    }

    def __init__(
        self,
        project_path: Path,
        wiki_dir: Optional[Path] = None,
        lag_threshold_days: int = 7,
    ):
        self.project_path = Path(project_path)
        self.wiki_dir = wiki_dir or self.project_path / ".python-wiki" / "repowiki"
        self.lag_threshold_days = lag_threshold_days

        self.git_detector = GitChangeDetector(self.project_path)

    def detect_lag(
        self,
        since_commit: Optional[str] = None,
        file_patterns: Optional[list[str]] = None,
    ) -> DocLagReport:
        """
        检测文档滞后

        Args:
            since_commit: 起始 commit
            file_patterns: 文件模式过滤

        Returns:
            文档滞后报告
        """
        items = []
        total_files = 0
        lagging_count = 0
        missing_count = 0

        code_files = self._find_code_files(file_patterns)

        for code_file in code_files:
            total_files += 1

            doc_file = self._find_doc_file(code_file)

            code_modified = self._get_last_modified(code_file)
            doc_modified = self._get_last_modified(doc_file) if doc_file else None

            code_changes = self._count_code_changes(code_file, since_commit)

            if doc_file is None:
                missing_count += 1
                items.append(DocLagItem(
                    code_file=code_file,
                    doc_file=None,
                    code_last_modified=code_modified,
                    doc_last_modified=None,
                    lag_days=0,
                    lag_severity="missing",
                    code_changes=code_changes,
                    suggestions=["创建对应的文档文件"],
                ))
                continue

            if doc_modified is None:
                continue

            if code_modified > doc_modified:
                lag_delta = code_modified - doc_modified
                lag_days = lag_delta.days

                if lag_days >= self.lag_threshold_days:
                    lagging_count += 1
                    severity = self._determine_severity(lag_days)

                    suggestions = self._generate_suggestions(code_file, code_changes)

                    items.append(DocLagItem(
                        code_file=code_file,
                        doc_file=doc_file,
                        code_last_modified=code_modified,
                        doc_last_modified=doc_modified,
                        lag_days=lag_days,
                        lag_severity=severity,
                        code_changes=code_changes,
                        suggestions=suggestions,
                    ))

        items.sort(key=lambda x: x.lag_days, reverse=True)

        return DocLagReport(
            total_files=total_files,
            lagging_files=lagging_count,
            missing_docs=missing_count,
            items=items,
        )

    def detect_recent_lag(self, days: int = 7) -> DocLagReport:
        """检测最近 N 天的文档滞后"""
        since_date = datetime.now() - timedelta(days=days)

        commits = self.git_detector.get_recent_commits(limit=100)
        since_commit = None

        for commit in commits:
            if commit.timestamp < since_date:
                since_commit = commit.hash
                break

        return self.detect_lag(since_commit=since_commit)

    def _find_code_files(
        self,
        file_patterns: Optional[list[str]] = None,
    ) -> list[Path]:
        """查找代码文件"""
        files = []

        for ext in self.CODE_EXTENSIONS:
            for file_path in self.project_path.rglob(f"*{ext}"):
                if self._should_skip(file_path):
                    continue

                if file_patterns:
                    if not any(file_path.match(p) for p in file_patterns):
                        continue

                files.append(file_path)

        return files

    def _should_skip(self, file_path: Path) -> bool:
        """检查是否应该跳过"""
        skip_patterns = [
            "node_modules", "venv", ".venv", "__pycache__",
            ".git", "dist", "build", ".tox", "migrations",
            "tests", "test", ".python-wiki",
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def _find_doc_file(self, code_file: Path) -> Optional[Path]:
        """查找对应的文档文件"""
        code_ext = code_file.suffix
        doc_exts = self.DOC_PATTERNS.get(code_ext, [".md"])

        relative_path = code_file.relative_to(self.project_path)
        doc_name = code_file.stem

        for doc_ext in doc_exts:
            doc_path = self.wiki_dir / relative_path.parent / f"{doc_name}{doc_ext}"
            if doc_path.exists():
                return doc_path

            doc_path = self.wiki_dir / f"{doc_name}{doc_ext}"
            if doc_path.exists():
                return doc_path

        return None

    def _get_last_modified(self, file_path: Optional[Path]) -> Optional[datetime]:
        """获取文件最后修改时间"""
        if file_path is None or not file_path.exists():
            return None

        try:
            history = self.git_detector.get_file_history(file_path, limit=1)
            if history:
                return history[0].timestamp
        except Exception:
            pass

        return datetime.fromtimestamp(file_path.stat().st_mtime)

    def _count_code_changes(
        self,
        code_file: Path,
        since_commit: Optional[str] = None,
    ) -> int:
        """统计代码变更次数"""
        if since_commit:
            changes = self.git_detector.get_changes_since_commit(
                since_commit,
                file_patterns=[str(code_file.name)],
            )
            return len(changes)

        history = self.git_detector.get_file_history(code_file, limit=10)
        return len(history)

    def _determine_severity(self, lag_days: int) -> str:
        """确定滞后严重程度"""
        if lag_days >= self.SEVERITY_THRESHOLDS["critical"]:
            return "critical"
        elif lag_days >= self.SEVERITY_THRESHOLDS["high"]:
            return "high"
        elif lag_days >= self.SEVERITY_THRESHOLDS["medium"]:
            return "medium"
        else:
            return "low"

    def _generate_suggestions(
        self,
        code_file: Path,
        code_changes: int,
    ) -> list[str]:
        """生成改进建议"""
        suggestions = []

        if code_changes > 5:
            suggestions.append(f"代码已变更 {code_changes} 次，建议全面更新文档")

        suggestions.append(f"更新 {code_file.name} 的文档以反映最新变更")

        relative_path = code_file.relative_to(self.project_path)
        suggestions.append(f"检查文档路径: {self.wiki_dir / relative_path.parent}")

        return suggestions

    def get_doc_coverage(self) -> dict[str, Any]:
        """获取文档覆盖率"""
        code_files = self._find_code_files()
        total = len(code_files)
        documented = 0
        missing = []

        for code_file in code_files:
            doc_file = self._find_doc_file(code_file)
            if doc_file:
                documented += 1
            else:
                missing.append(str(code_file.relative_to(self.project_path)))

        return {
            "total_code_files": total,
            "documented_files": documented,
            "missing_docs": total - documented,
            "coverage_rate": documented / total if total > 0 else 0,
            "missing_files": missing[:20],
        }

    def get_lag_summary(self) -> dict[str, Any]:
        """获取滞后摘要"""
        report = self.detect_lag()

        by_severity = {}
        for item in report.items:
            severity = item.lag_severity
            by_severity[severity] = by_severity.get(severity, 0) + 1

        return {
            "total_files": report.total_files,
            "lagging_files": report.lagging_files,
            "missing_docs": report.missing_docs,
            "by_severity": by_severity,
            "avg_lag_days": sum(i.lag_days for i in report.items) / max(len(report.items), 1),
        }
