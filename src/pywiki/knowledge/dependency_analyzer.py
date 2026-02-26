"""
深层依赖分析器
分析模块间的深层依赖关系
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pywiki.parsers.types import ModuleInfo, DependencyInfo


class DependencyType(str, Enum):
    IMPORT = "import"
    INHERITANCE = "inheritance"
    COMPOSITION = "composition"
    USAGE = "usage"
    IMPLEMENTATION = "implementation"


class DependencyStrength(str, Enum):
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"


@dataclass
class DeepDependency:
    source: str
    target: str
    dependency_type: DependencyType
    strength: DependencyStrength
    description: str
    evidence: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    is_circular: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyGraph:
    nodes: list[str] = field(default_factory=list)
    edges: list[DeepDependency] = field(default_factory=list)
    circular_dependencies: list[list[str]] = field(default_factory=list)
    hot_spots: list[str] = field(default_factory=list)
    isolated_modules: list[str] = field(default_factory=list)


class DeepDependencyAnalyzer:
    """深层依赖分析器"""

    def __init__(self):
        self._stdlib_modules = self._load_stdlib_modules()

    def analyze_modules(self, modules: list[ModuleInfo]) -> DependencyGraph:
        """分析模块间的依赖关系"""
        graph = DependencyGraph()

        for module in modules:
            graph.nodes.append(module.name)

            for dep in self._analyze_module_dependencies(module):
                graph.edges.append(dep)

        graph.circular_dependencies = self._detect_circular_dependencies(graph)
        graph.hot_spots = self._identify_hot_spots(graph)
        graph.isolated_modules = self._identify_isolated_modules(graph)

        return graph

    def _analyze_module_dependencies(self, module: ModuleInfo) -> list[DeepDependency]:
        """分析单个模块的依赖"""
        dependencies = []

        for imp in module.imports:
            dep = self._analyze_import_dependency(module.name, imp)
            if dep:
                dependencies.append(dep)

        for cls in module.classes:
            for base in cls.bases:
                dep = self._analyze_inheritance_dependency(module.name, cls.name, base)
                if dep:
                    dependencies.append(dep)

        return dependencies

    def _analyze_import_dependency(self, module_name: str, imp) -> Optional[DeepDependency]:
        """分析导入依赖"""
        target_module = imp.module.split(".")[0]

        if target_module in self._stdlib_modules:
            return None

        if target_module.startswith("_"):
            return None

        strength = self._determine_import_strength(imp)

        return DeepDependency(
            source=module_name,
            target=target_module,
            dependency_type=DependencyType.IMPORT,
            strength=strength,
            description=f"{module_name} 导入了 {target_module}",
            evidence=[f"import {imp.module}"],
            locations=[f"{module_name}:{imp.line}"],
        )

    def _analyze_inheritance_dependency(
        self,
        module_name: str,
        class_name: str,
        base: str
    ) -> Optional[DeepDependency]:
        """分析继承依赖"""
        if base in ("object", "ABC", "Enum", "Exception"):
            return None

        return DeepDependency(
            source=module_name,
            target=base,
            dependency_type=DependencyType.INHERITANCE,
            strength=DependencyStrength.STRONG,
            description=f"{class_name} 继承自 {base}",
            evidence=[f"class {class_name}({base})"],
            locations=[module_name],
        )

    def _determine_import_strength(self, imp) -> DependencyStrength:
        """确定导入强度"""
        module_name = imp.module.lower()

        strong_indicators = ["core", "base", "model", "service", "repository"]
        if any(indicator in module_name for indicator in strong_indicators):
            return DependencyStrength.STRONG

        weak_indicators = ["util", "helper", "constant", "config"]
        if any(indicator in module_name for indicator in weak_indicators):
            return DependencyStrength.WEAK

        return DependencyStrength.MEDIUM

    def _detect_circular_dependencies(self, graph: DependencyGraph) -> list[list[str]]:
        """检测循环依赖"""
        circular = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: list[str]) -> None:
            visited.add(node)
            rec_stack.add(node)

            for edge in graph.edges:
                if edge.source == node:
                    neighbor = edge.target
                    if neighbor not in visited:
                        dfs(neighbor, path + [node])
                    elif neighbor in rec_stack:
                        cycle_start = path.index(neighbor) if neighbor in path else 0
                        cycle = path[cycle_start:] + [node, neighbor]
                        if len(cycle) > 2:
                            circular.append(cycle)

            rec_stack.remove(node)

        for node in graph.nodes:
            if node not in visited:
                dfs(node, [])

        unique_circular = []
        seen_cycles = set()
        for cycle in circular:
            cycle_key = tuple(sorted(cycle))
            if cycle_key not in seen_cycles:
                seen_cycles.add(cycle_key)
                unique_circular.append(cycle)

        return unique_circular

    def _identify_hot_spots(self, graph: DependencyGraph) -> list[str]:
        """识别热点模块（被依赖最多的模块）"""
        incoming_count: dict[str, int] = {}

        for edge in graph.edges:
            incoming_count[edge.target] = incoming_count.get(edge.target, 0) + 1

        sorted_modules = sorted(
            incoming_count.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [module for module, count in sorted_modules[:10] if count > 3]

    def _identify_isolated_modules(self, graph: DependencyGraph) -> list[str]:
        """识别孤立模块"""
        connected_modules = set()

        for edge in graph.edges:
            connected_modules.add(edge.source)
            connected_modules.add(edge.target)

        return [node for node in graph.nodes if node not in connected_modules]

    def analyze_dependency_impact(
        self,
        module_name: str,
        graph: DependencyGraph
    ) -> dict:
        """分析模块变更的影响"""
        impact = {
            "module": module_name,
            "direct_dependents": [],
            "indirect_dependents": [],
            "total_impact": 0,
            "risk_level": "low",
        }

        for edge in graph.edges:
            if edge.target == module_name:
                impact["direct_dependents"].append(edge.source)

        visited = set(impact["direct_dependents"])
        queue = list(impact["direct_dependents"])

        while queue:
            current = queue.pop(0)
            for edge in graph.edges:
                if edge.target == current and edge.source not in visited:
                    impact["indirect_dependents"].append(edge.source)
                    visited.add(edge.source)
                    queue.append(edge.source)

        impact["total_impact"] = len(impact["direct_dependents"]) + len(impact["indirect_dependents"])

        if impact["total_impact"] > 10:
            impact["risk_level"] = "high"
        elif impact["total_impact"] > 5:
            impact["risk_level"] = "medium"

        return impact

    def generate_dependency_report(self, graph: DependencyGraph) -> dict:
        """生成依赖报告"""
        report = {
            "summary": {
                "total_modules": len(graph.nodes),
                "total_dependencies": len(graph.edges),
                "circular_dependencies_count": len(graph.circular_dependencies),
                "hot_spots_count": len(graph.hot_spots),
                "isolated_modules_count": len(graph.isolated_modules),
            },
            "circular_dependencies": [
                {"cycle": cycle, "severity": "high"}
                for cycle in graph.circular_dependencies
            ],
            "hot_spots": [
                {
                    "module": module,
                    "description": "被多个模块依赖，变更需谨慎",
                }
                for module in graph.hot_spots
            ],
            "isolated_modules": [
                {
                    "module": module,
                    "description": "没有依赖关系，可能是独立功能或需要检查",
                }
                for module in graph.isolated_modules
            ],
            "dependency_strength": self._analyze_dependency_strength(graph),
            "recommendations": self._generate_recommendations(graph),
        }

        return report

    def _analyze_dependency_strength(self, graph: DependencyGraph) -> dict:
        """分析依赖强度分布"""
        strength_count = {
            DependencyStrength.STRONG: 0,
            DependencyStrength.MEDIUM: 0,
            DependencyStrength.WEAK: 0,
        }

        for edge in graph.edges:
            strength_count[edge.strength] = strength_count.get(edge.strength, 0) + 1

        return {
            "strong": strength_count[DependencyStrength.STRONG],
            "medium": strength_count[DependencyStrength.MEDIUM],
            "weak": strength_count[DependencyStrength.WEAK],
        }

    def _generate_recommendations(self, graph: DependencyGraph) -> list[dict]:
        """生成改进建议"""
        recommendations = []

        if graph.circular_dependencies:
            recommendations.append({
                "type": "circular_dependency",
                "priority": "high",
                "description": f"发现 {len(graph.circular_dependencies)} 个循环依赖",
                "suggestion": "考虑使用依赖注入或接口抽象来打破循环依赖",
            })

        if graph.hot_spots:
            recommendations.append({
                "type": "hot_spot",
                "priority": "medium",
                "description": f"发现 {len(graph.hot_spots)} 个热点模块",
                "suggestion": "热点模块变更影响大，建议增加测试覆盖和文档",
            })

        if graph.isolated_modules:
            recommendations.append({
                "type": "isolated_module",
                "priority": "low",
                "description": f"发现 {len(graph.isolated_modules)} 个孤立模块",
                "suggestion": "检查孤立模块是否应该被使用或删除",
            })

        return recommendations

    def _load_stdlib_modules(self) -> set:
        """加载标准库模块列表"""
        return {
            "os", "sys", "re", "json", "io", "abc", "collections", "itertools",
            "functools", "typing", "datetime", "time", "pathlib", "hashlib",
            "logging", "argparse", "subprocess", "threading", "multiprocessing",
            "asyncio", "socket", "http", "urllib", "email", "html", "xml",
            "sqlite3", "csv", "configparser", "tempfile", "shutil", "copy",
            "pickle", "struct", "codecs", "unicodedata", "string", "textwrap",
            "difflib", "math", "random", "statistics", "decimal", "fractions",
            "numbers", "array", "weakref", "types", "copy", "pprint", "reprlib",
            "enum", "graphlib", "operator", "contextlib", "dataclasses",
            "unittest", "doctest", "trace", "traceback", "gc", "inspect",
            "dis", "dataclasses", "warnings", "contextlib", "concurrent",
        }
