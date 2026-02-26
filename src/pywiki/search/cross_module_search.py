"""
跨模块搜索器
支持跨模块的语义理解和搜索
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from pywiki.search.code_search_engine import CodeSearchEngine, SearchResult
from pywiki.search.semantic_indexer import SemanticIndexer


@dataclass
class CrossModuleResult:
    query: str
    direct_matches: list[SearchResult] = field(default_factory=list)
    related_modules: list[str] = field(default_factory=list)
    dependency_matches: list[SearchResult] = field(default_factory=list)
    usage_examples: list[dict] = field(default_factory=list)
    summary: str = ""


class CrossModuleSearcher:
    """跨模块搜索器"""

    def __init__(
        self,
        project_path: Path,
        code_engine: Optional[CodeSearchEngine] = None,
        semantic_indexer: Optional[SemanticIndexer] = None,
    ):
        self.project_path = project_path
        self.code_engine = code_engine or CodeSearchEngine(project_path)
        self.semantic_indexer = semantic_indexer or SemanticIndexer(
            project_path / ".pywiki" / "semantic_index"
        )

        self._module_dependencies: dict[str, list[str]] = {}
        self._module_usages: dict[str, list[str]] = {}

    def build_cross_module_index(self) -> None:
        """构建跨模块索引"""
        self.code_engine.build_index()

        self._analyze_module_dependencies()
        self._analyze_module_usages()

    def _analyze_module_dependencies(self) -> None:
        """分析模块依赖"""
        for file_path, lines in self.code_engine._file_cache.items():
            module_name = self._file_to_module(file_path)
            dependencies = []

            for line in lines:
                if line.strip().startswith("import ") or line.strip().startswith("from "):
                    dep = self._extract_import_module(line)
                    if dep:
                        dependencies.append(dep)

            self._module_dependencies[module_name] = dependencies

    def _analyze_module_usages(self) -> None:
        """分析模块使用情况"""
        for module, deps in self._module_dependencies.items():
            for dep in deps:
                if dep not in self._module_usages:
                    self._module_usages[dep] = []
                if module not in self._module_usages[dep]:
                    self._module_usages[dep].append(module)

    def _file_to_module(self, file_path: str) -> str:
        """文件路径转模块名"""
        return file_path.replace("/", ".").replace("\\", ".").replace(".py", "")

    def _extract_import_module(self, line: str) -> Optional[str]:
        """提取导入模块"""
        import re

        patterns = [
            r"^import\s+(\w+)",
            r"^from\s+(\w+(?:\.\w+)*)",
        ]

        for pattern in patterns:
            match = re.match(pattern, line.strip())
            if match:
                return match.group(1)

        return None

    def search(
        self,
        query: str,
        include_related: bool = True,
        include_usages: bool = True,
        max_results: int = 20,
    ) -> CrossModuleResult:
        """跨模块搜索"""
        result = CrossModuleResult(query=query)

        result.direct_matches = self.code_engine.search(
            query,
            max_results=max_results,
        )

        if include_related:
            result.related_modules = self._find_related_modules(query)
            result.dependency_matches = self._search_dependencies(query, result.related_modules)

        if include_usages:
            result.usage_examples = self._find_usage_examples(query)

        result.summary = self._generate_summary(result)

        return result

    def _find_related_modules(self, query: str) -> list[str]:
        """查找相关模块"""
        related = set()

        for symbol, files in self.code_engine._index.symbol_index.items():
            if query.lower() in symbol.lower():
                for file_path in files:
                    module = self._file_to_module(file_path)
                    related.add(module)

                    if module in self._module_dependencies:
                        for dep in self._module_dependencies[module]:
                            related.add(dep)

        return list(related)[:10]

    def _search_dependencies(
        self,
        query: str,
        modules: list[str],
    ) -> list[SearchResult]:
        """搜索依赖模块"""
        results = []

        for module in modules:
            file_path = self._module_to_file(module)
            if file_path and file_path in self.code_engine._file_cache:
                lines = self.code_engine._file_cache[file_path]
                for i, line in enumerate(lines):
                    if query.lower() in line.lower():
                        results.append(SearchResult(
                            file_path=file_path,
                            line_number=i + 1,
                            content=line.strip(),
                            match_type="dependency",
                        ))

        return results[:10]

    def _module_to_file(self, module: str) -> Optional[str]:
        """模块名转文件路径"""
        file_path = module.replace(".", "/") + ".py"
        if file_path in self.code_engine._file_cache:
            return file_path

        init_path = module.replace(".", "/") + "/__init__.py"
        if init_path in self.code_engine._file_cache:
            return init_path

        return None

    def _find_usage_examples(self, query: str) -> list[dict]:
        """查找使用示例"""
        examples = []

        for symbol, files in self.code_engine._index.symbol_index.items():
            if query.lower() in symbol.lower():
                for file_path in files:
                    lines = self.code_engine._file_cache.get(file_path, [])
                    usage = self._extract_usage_context(lines, symbol)
                    if usage:
                        examples.append({
                            "symbol": symbol,
                            "file": file_path,
                            "context": usage,
                        })

        return examples[:5]

    def _extract_usage_context(self, lines: list[str], symbol: str) -> Optional[str]:
        """提取使用上下文"""
        for i, line in enumerate(lines):
            if symbol in line and not line.strip().startswith("class ") and not line.strip().startswith("def "):
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                return "\n".join(lines[start:end])
        return None

    def _generate_summary(self, result: CrossModuleResult) -> str:
        """生成摘要"""
        parts = []

        if result.direct_matches:
            parts.append(f"找到 {len(result.direct_matches)} 个直接匹配")

        if result.related_modules:
            parts.append(f"涉及 {len(result.related_modules)} 个相关模块")

        if result.usage_examples:
            parts.append(f"发现 {len(result.usage_examples)} 个使用示例")

        return "，".join(parts) if parts else "未找到匹配结果"

    def get_module_overview(self, module_name: str) -> dict:
        """获取模块概览"""
        file_path = self._module_to_file(module_name)
        if not file_path:
            return {}

        lines = self.code_engine._file_cache.get(file_path, [])

        return {
            "module": module_name,
            "file_path": file_path,
            "line_count": len(lines),
            "dependencies": self._module_dependencies.get(module_name, []),
            "used_by": self._module_usages.get(module_name, []),
            "symbols": self._extract_module_symbols(file_path),
        }

    def _extract_module_symbols(self, file_path: str) -> dict:
        """提取模块符号"""
        symbols = {
            "classes": [],
            "functions": [],
            "imports": [],
        }

        lines = self.code_engine._file_cache.get(file_path, [])
        for line in lines:
            if line.strip().startswith("class "):
                import re
                match = re.search(r"class\s+(\w+)", line)
                if match:
                    symbols["classes"].append(match.group(1))
            elif line.strip().startswith("def "):
                import re
                match = re.search(r"def\s+(\w+)", line)
                if match:
                    symbols["functions"].append(match.group(1))
            elif "import " in line or "from " in line:
                symbols["imports"].append(line.strip())

        return symbols

    def find_call_chain(
        self,
        start_symbol: str,
        end_symbol: str,
        max_depth: int = 5,
    ) -> list[list[str]]:
        """查找调用链"""
        chains = []
        visited = set()

        def dfs(current: str, path: list[str], depth: int) -> None:
            if depth > max_depth:
                return

            if current in visited:
                return

            visited.add(current)
            path.append(current)

            if current == end_symbol:
                chains.append(path.copy())
                visited.remove(current)
                return

            callers = self._find_callers(current)
            for caller in callers:
                dfs(caller, path, depth + 1)

            path.pop()
            visited.remove(current)

        dfs(start_symbol, [], 0)
        return chains

    def _find_callers(self, symbol: str) -> list[str]:
        """查找调用者"""
        callers = []

        for file_path, lines in self.code_engine._file_cache.items():
            for i, line in enumerate(lines):
                if symbol in line and not line.strip().startswith("def " + symbol):
                    func_match = None
                    for j in range(i, -1, -1):
                        import re
                        match = re.match(r"^\s*def\s+(\w+)", lines[j])
                        if match:
                            func_match = match.group(1)
                            break

                    if func_match:
                        callers.append(f"{self._file_to_module(file_path)}.{func_match}")

        return list(set(callers))[:10]
