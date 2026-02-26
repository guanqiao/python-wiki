"""
编码风格学习器
从代码中自动学习和识别编码风格
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from pywiki.memory.global_memory import CodingStyle, GlobalMemory


@dataclass
class StyleObservation:
    feature: str
    value: Any
    count: int = 1
    files: list[str] = field(default_factory=list)


class StyleLearner:
    """
    编码风格学习器
    从代码中分析并学习编码风格偏好
    """

    def __init__(self, global_memory: Optional[GlobalMemory] = None):
        self.global_memory = global_memory or GlobalMemory()
        self._observations: dict[str, StyleObservation] = {}

    def analyze_file(self, file_path: Path, content: Optional[str] = None) -> dict[str, Any]:
        """
        分析单个文件的编码风格

        Args:
            file_path: 文件路径
            content: 文件内容（可选，如果不提供则从文件读取）

        Returns:
            分析结果
        """
        if content is None:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                return {}

        result = {
            "file_path": str(file_path),
            "indent_style": self._detect_indent_style(content),
            "indent_size": self._detect_indent_size(content),
            "quote_style": self._detect_quote_style(content),
            "naming_convention": self._detect_naming_convention(content),
            "max_line_length": self._detect_max_line_length(content),
            "docstring_style": self._detect_docstring_style(content),
            "type_hints": self._detect_type_hints(content),
            "import_style": self._detect_import_style(content),
        }

        self._record_observations(result, str(file_path))

        return result

    def analyze_project(self, project_path: Path, max_files: int = 100) -> CodingStyle:
        """
        分析整个项目的编码风格

        Args:
            project_path: 项目路径
            max_files: 最大分析文件数

        Returns:
            学习到的编码风格
        """
        self._observations.clear()

        file_count = 0
        for ext in [".py", ".ts", ".js", ".java"]:
            for file_path in project_path.rglob(f"*{ext}"):
                if file_count >= max_files:
                    break

                if self._should_skip(file_path):
                    continue

                self.analyze_file(file_path)
                file_count += 1

            if file_count >= max_files:
                break

        style = self._aggregate_style()
        self.global_memory.update_coding_style(**style.to_dict())

        return style

    def _should_skip(self, file_path: Path) -> bool:
        """检查是否应该跳过文件"""
        skip_patterns = [
            "node_modules", "venv", ".venv", "__pycache__",
            ".git", "dist", "build", ".tox", "migrations",
        ]
        for pattern in skip_patterns:
            if pattern in str(file_path):
                return True
        return False

    def _detect_indent_style(self, content: str) -> str:
        """检测缩进风格"""
        lines = content.split("\n")
        space_indents = 0
        tab_indents = 0

        for line in lines:
            if line.startswith(" "):
                space_indents += 1
            elif line.startswith("\t"):
                tab_indents += 1

        return "space" if space_indents >= tab_indents else "tab"

    def _detect_indent_size(self, content: str) -> int:
        """检测缩进大小"""
        lines = content.split("\n")
        indent_sizes = []

        for line in lines:
            if line.startswith(" "):
                spaces = len(line) - len(line.lstrip(" "))
                if spaces > 0:
                    indent_sizes.append(spaces)

        if not indent_sizes:
            return 4

        counter = Counter(indent_sizes)
        most_common = counter.most_common(5)

        for size, _ in most_common:
            if size in (2, 4, 8):
                return size

        return 4

    def _detect_quote_style(self, content: str) -> str:
        """检测引号风格"""
        single_quotes = content.count("'")
        double_quotes = content.count('"')

        return "double" if double_quotes >= single_quotes else "single"

    def _detect_naming_convention(self, content: str) -> str:
        """检测命名约定"""
        snake_case = len(re.findall(r'\b[a-z][a-z0-9]*_[a-z0-9_]*\b', content))
        camel_case = len(re.findall(r'\b[a-z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*\b', content))
        pascal_case = len(re.findall(r'\b[A-Z][a-zA-Z0-9]*\b', content))

        conventions = {
            "snake_case": snake_case,
            "camelCase": camel_case,
            "PascalCase": pascal_case,
        }

        return max(conventions, key=conventions.get)

    def _detect_max_line_length(self, content: str) -> int:
        """检测最大行长度"""
        lines = content.split("\n")
        lengths = [len(line) for line in lines if line.strip()]

        if not lengths:
            return 100

        sorted_lengths = sorted(lengths, reverse=True)
        top_10_percent = sorted_lengths[:max(1, len(sorted_lengths) // 10)]

        return int(sum(top_10_percent) / len(top_10_percent))

    def _detect_docstring_style(self, content: str) -> str:
        """检测文档字符串风格"""
        google_patterns = [
            r'Args:\s*\n\s+\w+:',
            r'Returns:\s*\n\s+',
            r'Raises:\s*\n\s+',
        ]

        numpy_patterns = [
            r'Parameters\s*\n\s+-+',
            r'Returns\s*\n\s+-+',
        ]

        sphinx_patterns = [
            r':param\s+\w+:',
            r':type\s+\w+:',
            r':return:',
            r':rtype:',
        ]

        google_count = sum(len(re.findall(p, content)) for p in google_patterns)
        numpy_count = sum(len(re.findall(p, content)) for p in numpy_patterns)
        sphinx_count = sum(len(re.findall(p, content)) for p in sphinx_patterns)

        styles = {
            "google": google_count,
            "numpy": numpy_count,
            "sphinx": sphinx_count,
        }

        if max(styles.values()) == 0:
            return "google"

        return max(styles, key=styles.get)

    def _detect_type_hints(self, content: str) -> bool:
        """检测是否使用类型提示"""
        type_hint_patterns = [
            r'def\s+\w+\s*\([^)]*\)\s*->\s*\w+',
            r':\s*(str|int|float|bool|list|dict|set|tuple|Optional|Union|Any)',
            r'from\s+typing\s+import',
        ]

        matches = sum(len(re.findall(p, content)) for p in type_hint_patterns)

        return matches >= 3

    def _detect_import_style(self, content: str) -> str:
        """检测导入风格"""
        if re.search(r'from\s+\S+\s+import\s+\(', content):
            return "multi_line"

        isort_pattern = re.search(
            r'^(import\s+\S+\n)+\n+(from\s+\S+\s+import\s+\S+\n)+',
            content,
            re.MULTILINE,
        )

        if isort_pattern:
            return "isort"

        return "standard"

    def _record_observations(self, result: dict[str, Any], file_path: str) -> None:
        """记录观察结果"""
        for feature, value in result.items():
            if feature == "file_path":
                continue

            key = f"{feature}:{value}"
            if key in self._observations:
                obs = self._observations[key]
                obs.count += 1
                if file_path not in obs.files:
                    obs.files.append(file_path)
            else:
                self._observations[key] = StyleObservation(
                    feature=feature,
                    value=value,
                    count=1,
                    files=[file_path],
                )

    def _aggregate_style(self) -> CodingStyle:
        """聚合风格观察结果"""
        feature_votes: dict[str, Counter] = {}

        for key, obs in self._observations.items():
            if obs.feature not in feature_votes:
                feature_votes[obs.feature] = Counter()
            feature_votes[obs.feature][obs.value] += obs.count

        def get_winner(feature: str, default: Any) -> Any:
            if feature in feature_votes:
                counter = feature_votes[feature]
                if counter:
                    return counter.most_common(1)[0][0]
            return default

        return CodingStyle(
            indent_style=get_winner("indent_style", "space"),
            indent_size=get_winner("indent_size", 4),
            quote_style=get_winner("quote_style", "double"),
            naming_convention=get_winner("naming_convention", "snake_case"),
            max_line_length=get_winner("max_line_length", 100),
            docstring_style=get_winner("docstring_style", "google"),
            import_order=get_winner("import_style", "isort"),
            type_hints=get_winner("type_hints", True),
        )

    def get_observations(self) -> dict[str, StyleObservation]:
        """获取所有观察结果"""
        return self._observations.copy()

    def clear_observations(self) -> None:
        """清空观察结果"""
        self._observations.clear()
