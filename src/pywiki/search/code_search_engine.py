"""
高性能代码搜索引擎
支持大规模代码库的快速检索
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import re
from concurrent.futures import ThreadPoolExecutor
import hashlib


@dataclass
class SearchResult:
    file_path: str
    line_number: int
    content: str
    context: list[str] = field(default_factory=list)
    score: float = 1.0
    match_type: str = "exact"
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchIndex:
    file_hashes: dict[str, str] = field(default_factory=dict)
    symbol_index: dict[str, list[str]] = field(default_factory=dict)
    content_index: dict[str, list[str]] = field(default_factory=dict)
    last_updated: Optional[str] = None


class CodeSearchEngine:
    """高性能代码搜索引擎"""

    def __init__(
        self,
        project_path: Path,
        max_workers: int = 4,
        cache_dir: Optional[Path] = None,
    ):
        self.project_path = project_path
        self.max_workers = max_workers
        self.cache_dir = cache_dir or project_path / ".pywiki" / "search_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._index: SearchIndex = SearchIndex()
        self._file_cache: dict[str, list[str]] = {}

    def build_index(self) -> None:
        """构建搜索索引"""
        python_files = list(self.project_path.rglob("*.py"))

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(self._index_file, python_files))

        for file_path, content_lines, symbols in results:
            rel_path = str(file_path.relative_to(self.project_path))
            self._index.file_hashes[rel_path] = self._compute_hash(content_lines)
            self._file_cache[rel_path] = content_lines

            for symbol in symbols:
                if symbol not in self._index.symbol_index:
                    self._index.symbol_index[symbol] = []
                self._index.symbol_index[symbol].append(rel_path)

    def _index_file(self, file_path: Path) -> tuple[Path, list[str], list[str]]:
        """索引单个文件"""
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            symbols = self._extract_symbols(content)

            return (file_path, lines, symbols)
        except Exception:
            return (file_path, [], [])

    def _extract_symbols(self, content: str) -> list[str]:
        """提取符号"""
        symbols = []

        class_pattern = r"^\s*class\s+(\w+)"
        for match in re.finditer(class_pattern, content, re.MULTILINE):
            symbols.append(match.group(1))

        func_pattern = r"^\s*def\s+(\w+)"
        for match in re.finditer(func_pattern, content, re.MULTILINE):
            symbols.append(match.group(1))

        return symbols

    def _compute_hash(self, lines: list[str]) -> str:
        """计算文件哈希"""
        content = "\n".join(lines)
        return hashlib.md5(content.encode()).hexdigest()

    def search(
        self,
        query: str,
        search_type: str = "all",
        max_results: int = 50,
        context_lines: int = 3,
    ) -> list[SearchResult]:
        """执行搜索"""
        results = []

        if search_type in ("all", "symbol"):
            results.extend(self._search_symbols(query))

        if search_type in ("all", "content"):
            results.extend(self._search_content(query, context_lines))

        results.sort(key=lambda r: r.score, reverse=True)

        return results[:max_results]

    def _search_symbols(self, query: str) -> list[SearchResult]:
        """搜索符号"""
        results = []
        query_lower = query.lower()

        for symbol, files in self._index.symbol_index.items():
            if query_lower in symbol.lower():
                score = 1.0 if query_lower == symbol.lower() else 0.8

                for file_path in files:
                    lines = self._file_cache.get(file_path, [])
                    line_num = self._find_symbol_line(lines, symbol)

                    results.append(SearchResult(
                        file_path=file_path,
                        line_number=line_num,
                        content=symbol,
                        score=score,
                        match_type="symbol",
                        metadata={"symbol_type": "class" if symbol[0].isupper() else "function"},
                    ))

        return results

    def _search_content(self, query: str, context_lines: int) -> list[SearchResult]:
        """搜索内容"""
        results = []
        query_lower = query.lower()

        for file_path, lines in self._file_cache.items():
            for i, line in enumerate(lines):
                if query_lower in line.lower():
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)
                    context = lines[start:end]

                    results.append(SearchResult(
                        file_path=file_path,
                        line_number=i + 1,
                        content=line.strip(),
                        context=context,
                        score=0.6,
                        match_type="content",
                    ))

        return results

    def _find_symbol_line(self, lines: list[str], symbol: str) -> int:
        """查找符号所在行"""
        for i, line in enumerate(lines):
            if f"class {symbol}" in line or f"def {symbol}" in line:
                return i + 1
        return 0

    def search_regex(
        self,
        pattern: str,
        max_results: int = 50,
    ) -> list[SearchResult]:
        """正则表达式搜索"""
        results = []

        try:
            regex = re.compile(pattern)
        except re.error:
            return results

        for file_path, lines in self._file_cache.items():
            for i, line in enumerate(lines):
                if regex.search(line):
                    results.append(SearchResult(
                        file_path=file_path,
                        line_number=i + 1,
                        content=line.strip(),
                        score=1.0,
                        match_type="regex",
                    ))

        return results[:max_results]

    def search_by_type(
        self,
        symbol_type: str,
        max_results: int = 50,
    ) -> list[SearchResult]:
        """按类型搜索"""
        results = []

        for file_path, lines in self._file_cache.items():
            for i, line in enumerate(lines):
                if symbol_type == "class" and line.strip().startswith("class "):
                    match = re.search(r"class\s+(\w+)", line)
                    if match:
                        results.append(SearchResult(
                            file_path=file_path,
                            line_number=i + 1,
                            content=match.group(1),
                            match_type="class",
                        ))
                elif symbol_type == "function" and line.strip().startswith("def "):
                    match = re.search(r"def\s+(\w+)", line)
                    if match:
                        results.append(SearchResult(
                            file_path=file_path,
                            line_number=i + 1,
                            content=match.group(1),
                            match_type="function",
                        ))
                elif symbol_type == "import" and ("import " in line or "from " in line):
                    results.append(SearchResult(
                        file_path=file_path,
                        line_number=i + 1,
                        content=line.strip(),
                        match_type="import",
                    ))

        return results[:max_results]

    def get_file_content(self, file_path: str) -> Optional[list[str]]:
        """获取文件内容"""
        return self._file_cache.get(file_path)

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "indexed_files": len(self._file_cache),
            "total_symbols": len(self._index.symbol_index),
            "cache_size_mb": sum(
                len("\n".join(lines)) for lines in self._file_cache.values()
            ) / (1024 * 1024),
        }

    def clear_cache(self) -> None:
        """清除缓存"""
        self._file_cache.clear()
        self._index = SearchIndex()
