"""
高性能代码检索引擎
支持 10万+ 文件项目的高效检索
对标 Qoder 的代码检索能力
"""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from collections import defaultdict
import asyncio
from concurrent.futures import ThreadPoolExecutor

from pywiki.parsers.models import ModuleInfo, ClassInfo, FunctionInfo


@dataclass
class SearchIndex:
    """搜索索引"""
    file_index: dict[str, dict] = field(default_factory=dict)  # 文件级索引
    symbol_index: dict[str, list[str]] = field(default_factory=dict)  # 符号索引
    content_index: dict[str, list[str]] = field(default_factory=dict)  # 内容索引
    import_index: dict[str, list[str]] = field(default_factory=dict)  # 导入索引


@dataclass
class SearchResult:
    """搜索结果"""
    file_path: str
    line_number: int
    content: str
    match_type: str  # exact, partial, fuzzy
    score: float
    context: dict[str, Any] = field(default_factory=dict)


class CodeSearchEngine:
    """
    高性能代码检索引擎
    
    特性：
    - 分层索引结构
    - 增量索引更新
    - 多线程并行处理
    - 缓存机制
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path(".python-wiki/cache/search")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index = SearchIndex()
        self._executor = ThreadPoolExecutor(max_workers=8)
        self._cache = {}

    async def build_index(
        self,
        modules: list[ModuleInfo],
        incremental: bool = True,
    ) -> None:
        """
        构建搜索索引
        
        Args:
            modules: 模块列表
            incremental: 是否增量更新
        """
        if not incremental:
            self.index = SearchIndex()

        # 并行处理模块
        tasks = []
        for module in modules:
            task = self._index_module(module)
            tasks.append(task)

        await asyncio.gather(*tasks)

        # 保存索引
        await self._save_index()

    async def _index_module(self, module: ModuleInfo) -> None:
        """索引单个模块"""
        module_path = module.path

        # 文件级索引
        self.index.file_index[module_path] = {
            "name": module.name,
            "docstring": module.docstring or "",
            "class_count": len(module.classes),
            "function_count": len(module.functions),
        }

        # 符号索引
        for cls in module.classes:
            symbol_key = f"class:{cls.name}"
            if symbol_key not in self.index.symbol_index:
                self.index.symbol_index[symbol_key] = []
            self.index.symbol_index[symbol_key].append(module_path)

            # 类方法
            for method in cls.methods:
                method_key = f"method:{cls.name}.{method.name}"
                if method_key not in self.index.symbol_index:
                    self.index.symbol_index[method_key] = []
                self.index.symbol_index[method_key].append(module_path)

        for func in module.functions:
            symbol_key = f"function:{func.name}"
            if symbol_key not in self.index.symbol_index:
                self.index.symbol_index[symbol_key] = []
            self.index.symbol_index[symbol_key].append(module_path)

        # 导入索引
        for imp in module.imports:
            import_key = imp.module
            if import_key not in self.index.import_index:
                self.index.import_index[import_key] = []
            self.index.import_index[import_key].append(module_path)

        # 内容索引（简化版：只索引关键内容）
        content_tokens = self._tokenize(module.docstring or "")
        for token in content_tokens:
            if token not in self.index.content_index:
                self.index.content_index[token] = []
            if module_path not in self.index.content_index[token]:
                self.index.content_index[token].append(module_path)

    def _tokenize(self, text: str) -> list[str]:
        """分词"""
        import re
        # 提取单词和标识符
        tokens = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', text.lower())
        # 过滤常见词
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                      'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                      'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                      'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                      'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                      'through', 'during', 'before', 'after', 'above', 'below',
                      'between', 'under', 'and', 'but', 'or', 'yet', 'so', 'if',
                      'because', 'although', 'though', 'while', 'where', 'when',
                      'that', 'which', 'who', 'whom', 'whose', 'what', 'this',
                      'these', 'those', 'i', 'me', 'my', 'myself', 'we', 'our',
                      'you', 'your', 'he', 'him', 'his', 'she', 'her', 'it',
                      'its', 'they', 'them', 'their', 'return', 'def', 'class',
                      'import', 'from', 'as', 'if', 'else', 'elif', 'for',
                      'while', 'try', 'except', 'finally', 'with', 'lambda'}
        return [t for t in tokens if t not in stop_words and len(t) > 2]

    async def search(
        self,
        query: str,
        search_type: str = "all",
        limit: int = 20,
    ) -> list[SearchResult]:
        """
        搜索代码
        
        Args:
            query: 搜索查询
            search_type: 搜索类型 (all, symbol, content, file)
            limit: 返回结果数量限制
            
        Returns:
            搜索结果列表
        """
        results = []
        query_lower = query.lower()

        if search_type in ["all", "symbol"]:
            # 符号搜索
            symbol_results = self._search_symbols(query_lower)
            results.extend(symbol_results)

        if search_type in ["all", "file"]:
            # 文件名搜索
            file_results = self._search_files(query_lower)
            results.extend(file_results)

        if search_type in ["all", "content"]:
            # 内容搜索
            content_results = self._search_content(query_lower)
            results.extend(content_results)

        # 去重和排序
        seen = set()
        unique_results = []
        for r in sorted(results, key=lambda x: x.score, reverse=True):
            key = (r.file_path, r.line_number)
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
                if len(unique_results) >= limit:
                    break

        return unique_results

    def _search_symbols(self, query: str) -> list[SearchResult]:
        """搜索符号"""
        results = []

        for symbol_key, file_paths in self.index.symbol_index.items():
            symbol_name = symbol_key.split(":", 1)[-1]
            score = self._calculate_similarity(query, symbol_name.lower())

            if score > 0.5:
                for file_path in file_paths[:5]:  # 限制每个符号的结果数
                    results.append(SearchResult(
                        file_path=file_path,
                        line_number=0,
                        content=symbol_name,
                        match_type="symbol",
                        score=score,
                        context={"symbol_type": symbol_key.split(":")[0]},
                    ))

        return results

    def _search_files(self, query: str) -> list[SearchResult]:
        """搜索文件"""
        results = []

        for file_path, info in self.index.file_index.items():
            file_name = info["name"].lower()
            score = self._calculate_similarity(query, file_name)

            if score > 0.5:
                results.append(SearchResult(
                    file_path=file_path,
                    line_number=0,
                    content=info["name"],
                    match_type="file",
                    score=score,
                    context={"docstring": info.get("docstring", "")},
                ))

        return results

    def _search_content(self, query: str) -> list[SearchResult]:
        """搜索内容"""
        results = []
        query_tokens = self._tokenize(query)

        for token in query_tokens:
            if token in self.index.content_index:
                for file_path in self.index.content_index[token][:10]:
                    results.append(SearchResult(
                        file_path=file_path,
                        line_number=0,
                        content=token,
                        match_type="content",
                        score=0.6,
                    ))

        return results

    def _calculate_similarity(self, query: str, target: str) -> float:
        """计算相似度分数"""
        if query == target:
            return 1.0
        if query in target:
            return 0.8
        if target in query:
            return 0.6

        # 计算编辑距离相似度
        from difflib import SequenceMatcher
        return SequenceMatcher(None, query, target).ratio()

    async def _save_index(self) -> None:
        """保存索引到缓存"""
        index_file = self.cache_dir / "search_index.json"
        index_data = {
            "file_index": self.index.file_index,
            "symbol_index": self.index.symbol_index,
            "content_index": {k: v[:100] for k, v in self.index.content_index.items()},  # 限制大小
            "import_index": self.index.import_index,
        }

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self._executor,
            lambda: index_file.write_text(json.dumps(index_data), encoding="utf-8")
        )

    async def load_index(self) -> bool:
        """从缓存加载索引"""
        index_file = self.cache_dir / "search_index.json"

        if not index_file.exists():
            return False

        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                self._executor,
                lambda: json.loads(index_file.read_text(encoding="utf-8"))
            )

            self.index = SearchIndex(
                file_index=data.get("file_index", {}),
                symbol_index=data.get("symbol_index", {}),
                content_index=data.get("content_index", {}),
                import_index=data.get("import_index", {}),
            )
            return True
        except Exception:
            return False

    def find_references(self, symbol_name: str) -> list[str]:
        """
        查找符号引用
        
        Args:
            symbol_name: 符号名称
            
        Returns:
            引用该符号的文件列表
        """
        results = []

        # 在导入索引中查找
        for import_key, file_paths in self.index.import_index.items():
            if symbol_name.lower() in import_key.lower():
                results.extend(file_paths)

        return list(set(results))

    def find_dependencies(self, file_path: str) -> dict[str, list[str]]:
        """
        查找文件依赖
        
        Args:
            file_path: 文件路径
            
        Returns:
            依赖信息字典
        """
        return {
            "imports": self.index.import_index.get(file_path, []),
            "imported_by": [
                fp for fp, imports in self.index.import_index.items()
                if file_path in imports
            ],
        }


class SemanticCodeSearch:
    """
    语义代码搜索
    基于代码嵌入的语义相似度搜索
    """

    def __init__(self, model_name: str = "codebert-base"):
        self.model_name = model_name
        self._embeddings = {}
        self._model = None

    async def encode(self, code: str) -> list[float]:
        """将代码编码为向量"""
        # 简化实现：使用哈希作为伪嵌入
        # 实际实现应使用 CodeBERT 等模型
        hash_val = hashlib.md5(code.encode()).hexdigest()
        embedding = [int(hash_val[i:i+2], 16) / 255.0 for i in range(0, 32, 2)]
        return embedding

    async def search_similar(
        self,
        query: str,
        code_snippets: list[str],
        top_k: int = 5,
    ) -> list[tuple[str, float]]:
        """
        搜索相似代码
        
        Args:
            query: 查询代码
            code_snippets: 代码片段列表
            top_k: 返回前 K 个结果
            
        Returns:
            (代码片段, 相似度) 列表
        """
        query_embedding = await self.encode(query)

        similarities = []
        for snippet in code_snippets:
            snippet_embedding = await self.encode(snippet)
            similarity = self._cosine_similarity(query_embedding, snippet_embedding)
            similarities.append((snippet, similarity))

        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_k]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """计算余弦相似度"""
        import math
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)
