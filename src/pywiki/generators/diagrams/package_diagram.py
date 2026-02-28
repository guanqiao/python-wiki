"""
包依赖图生成器
生成模块/包级别的依赖关系图，支持循环依赖检测和可视化
"""

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from pywiki.generators.diagrams.base import BaseDiagramGenerator


class DependencyType(str, Enum):
    """依赖类型"""
    IMPORT = "import"
    FROM_IMPORT = "from_import"
    RELATIVE = "relative"
    EXTERNAL = "external"
    STANDARD = "standard"


class PackageType(str, Enum):
    """包类型"""
    PACKAGE = "package"
    MODULE = "module"
    EXTERNAL = "external"
    STANDARD = "standard"


@dataclass
class PackageNode:
    """包节点"""
    id: str
    name: str
    package_type: PackageType
    description: str = ""
    file_count: int = 0
    class_count: int = 0
    function_count: int = 0
    tags: list[str] = field(default_factory=list)


@dataclass
class DependencyEdge:
    """依赖边"""
    source: str
    target: str
    dependency_type: DependencyType = DependencyType.IMPORT
    count: int = 1
    is_circular: bool = False


class PackageDiagramGenerator(BaseDiagramGenerator):
    """
    包依赖图生成器
    
    支持:
    - 模块/包级别依赖关系可视化
    - 循环依赖检测和高亮
    - 外部依赖和标准库区分
    - 依赖深度分析
    - 热点模块识别
    """

    PACKAGE_COLORS = {
        PackageType.PACKAGE: "#2196F3",
        PackageType.MODULE: "#4CAF50",
        PackageType.EXTERNAL: "#FF9800",
        PackageType.STANDARD: "#9E9E9E",
    }

    CIRCULAR_COLOR = "#F44336"
    HOTSPOT_COLOR = "#E91E63"

    STANDARD_LIBS = {
        "typing", "os", "sys", "json", "pathlib", "asyncio", "abc",
        "dataclasses", "collections", "functools", "itertools", "re",
        "logging", "time", "datetime", "copy", "enum", "io", "warnings",
        "contextlib", "threading", "multiprocessing", "concurrent",
        "subprocess", "shutil", "tempfile", "hashlib", "hmac", "secrets",
        "argparse", "configparser", "traceback", "inspect", "dis",
        "unittest", "pytest", "mock", "socket", "ssl", "http", "urllib",
        "email", "html", "xml", "csv", "sqlite3", "heapq", "bisect",
        "array", "weakref", "types", "numbers", "math", "random",
        "statistics", "decimal", "fractions", "operator", "pickle",
        "shelve", "dbm", "gzip", "bz2", "lzma", "zipfile", "tarfile",
    }

    def __init__(self):
        self.packages: dict[str, PackageNode] = {}
        self.dependencies: list[DependencyEdge] = []
        self.circular_dependencies: list[list[str]] = []
        self.hotspots: list[str] = []

    def generate(
        self,
        data: dict,
        title: Optional[str] = None,
        show_circular: bool = True,
        show_external: bool = True,
    ) -> str:
        """
        生成包依赖图
        
        Args:
            data: 包含以下字段:
                - packages: 包列表 [{"id": "", "name": "", "type": ""}]
                - dependencies: 依赖列表 [{"source": "", "target": "", "type": ""}]
                - circular: 循环依赖列表
                - hotspots: 热点模块列表
            title: 图表标题
            show_circular: 是否高亮循环依赖
            show_external: 是否显示外部依赖
        """
        packages = data.get("packages", [])
        dependencies = data.get("dependencies", [])
        circular = data.get("circular", [])
        hotspots = data.get("hotspots", [])

        lines = ["graph LR"]

        if title:
            lines.append(f"    %% {title}")
            lines.append("    %% Package Dependency Diagram")

        internal_packages = [p for p in packages if p.get("type") in ["package", "module"]]
        external_packages = [p for p in packages if p.get("type") == "external"]
        standard_packages = [p for p in packages if p.get("type") == "standard"]

        if internal_packages:
            lines.append("    subgraph internal[\"Internal Packages\"]")
            for pkg in internal_packages:
                pkg_id = self.sanitize_id(pkg.get("id", pkg.get("name", "")))
                pkg_name = pkg.get("name", "Package")
                pkg_desc = pkg.get("description", "")
                
                is_hotspot = pkg.get("id", pkg.get("name", "")) in hotspots
                color = self.HOTSPOT_COLOR if is_hotspot else self.PACKAGE_COLORS.get(
                    PackageType(pkg.get("type", "package")), "#2196F3"
                )
                
                label = pkg_name
                if pkg_desc:
                    label += f"<br/><small>{pkg_desc[:30]}</small>"
                
                lines.append(f"        {pkg_id}[\"{label}\"]")
                lines.append(f"        style {pkg_id} fill:{color},stroke:{color[:-2]}AA,color:#fff")
            lines.append("    end")

        if show_external and external_packages:
            lines.append("    subgraph external[\"External Dependencies\"]")
            for pkg in external_packages[:15]:
                pkg_id = self.sanitize_id(pkg.get("id", pkg.get("name", "")))
                pkg_name = pkg.get("name", "External")
                lines.append(f"        {pkg_id}[\"{pkg_name}\"]")
                lines.append(f"        style {pkg_id} fill:{self.PACKAGE_COLORS[PackageType.EXTERNAL]},stroke:#F57C00,color:#fff")
            lines.append("    end")

        if show_external and standard_packages:
            lines.append("    subgraph standard[\"Standard Library\"]")
            for pkg in standard_packages[:10]:
                pkg_id = self.sanitize_id(pkg.get("id", pkg.get("name", "")))
                pkg_name = pkg.get("name", "Standard")
                lines.append(f"        {pkg_id}[\"{pkg_name}\"]")
                lines.append(f"        style {pkg_id} fill:{self.PACKAGE_COLORS[PackageType.STANDARD]},stroke:#757575,color:#fff")
            lines.append("    end")

        circular_edges = set()
        if circular:
            for cycle in circular:
                for i in range(len(cycle)):
                    source = cycle[i]
                    target = cycle[(i + 1) % len(cycle)]
                    circular_edges.add((source, target))

        for dep in dependencies:
            source = self.sanitize_id(dep.get("source", ""))
            target = self.sanitize_id(dep.get("target", ""))
            dep_type = dep.get("type", "import")
            count = dep.get("count", 1)
            
            if not source or not target:
                continue
            
            is_circular = (dep.get("source", ""), dep.get("target", "")) in circular_edges
            
            if is_circular and show_circular:
                lines.append(f"    {source} -.->|\"{dep_type}\"| {target}")
                lines.append(f"    linkStyle {len(lines) - 1} stroke:{self.CIRCULAR_COLOR},stroke-width:3px")
            else:
                label = f"{dep_type}"
                if count > 1:
                    label += f" ({count})"
                lines.append(f"    {source} -->|\"{label}\"| {target}")

        return self.wrap_mermaid("\n".join(lines))

    def generate_from_parse_result(
        self,
        parse_result: Any,
        project_name: str = "Project",
        title: Optional[str] = None,
    ) -> str:
        """
        从代码解析结果生成包依赖图
        
        Args:
            parse_result: 代码解析结果
            project_name: 项目名称
            title: 图表标题
        """
        if not parse_result or not hasattr(parse_result, "modules"):
            return self.generate({"packages": [], "dependencies": []}, title)

        modules = parse_result.modules
        packages_dict: dict[str, dict] = {}
        dependencies_dict: dict[tuple[str, str], dict] = defaultdict(lambda: {"count": 0, "type": "import"})
        module_names = set()

        for module in modules:
            module_name = module.name if hasattr(module, "name") else str(module)
            module_names.add(module_name)
            
            top_package = self._extract_top_package(module_name)
            
            if top_package not in packages_dict:
                packages_dict[top_package] = {
                    "id": top_package,
                    "name": self._extract_display_name(top_package),
                    "type": "package",
                    "description": "",
                    "file_count": 0,
                    "class_count": 0,
                    "function_count": 0,
                }
            
            packages_dict[top_package]["file_count"] += 1
            if hasattr(module, "classes") and module.classes:
                packages_dict[top_package]["class_count"] += len(module.classes)
            if hasattr(module, "functions") and module.functions:
                packages_dict[top_package]["function_count"] += len(module.functions)

            if hasattr(module, "imports") and module.imports:
                for imp in module.imports:
                    if not hasattr(imp, "module"):
                        continue
                    imp_module = imp.module
                    
                    if imp_module.startswith("."):
                        dep_type = "relative"
                        parts = module_name.replace("\\", "/").replace("/", ".").split(".")
                        if len(parts) > 1:
                            base = module_name.rsplit(".", 1)[0] if "." in module_name else module_name
                            imp_module = f"{base}{imp_module}"
                    else:
                        dep_type = "import"
                    
                    imp_top = self._extract_top_package(imp_module)
                    
                    if imp_top in module_names or any(self._extract_top_package(m) == imp_top for m in module_names):
                        key = (top_package, imp_top)
                        dependencies_dict[key]["count"] += 1
                        dependencies_dict[key]["type"] = dep_type
                    elif imp_top in self.STANDARD_LIBS:
                        if imp_top not in packages_dict:
                            packages_dict[imp_top] = {
                                "id": imp_top,
                                "name": imp_top,
                                "type": "standard",
                            }
                        key = (top_package, imp_top)
                        dependencies_dict[key]["count"] += 1
                        dependencies_dict[key]["type"] = "standard"
                    else:
                        if imp_top not in packages_dict:
                            packages_dict[imp_top] = {
                                "id": imp_top,
                                "name": imp_top,
                                "type": "external",
                            }
                        key = (top_package, imp_top)
                        dependencies_dict[key]["count"] += 1
                        dependencies_dict[key]["type"] = "external"

        dependencies = [
            {
                "source": src,
                "target": tgt,
                "type": info["type"],
                "count": info["count"],
            }
            for (src, tgt), info in dependencies_dict.items()
        ]

        circular = self._detect_circular_dependencies(dependencies)

        hotspots = self._detect_hotspots(packages_dict, dependencies)

        data = {
            "packages": list(packages_dict.values()),
            "dependencies": dependencies,
            "circular": circular,
            "hotspots": hotspots,
        }

        return self.generate(data, title or f"{project_name} Package Dependencies")
    
    def _extract_top_package(self, module_name: str) -> str:
        """从模块名提取顶层包名"""
        import re
        
        if re.match(r'^[A-Za-z]:[\\/]', module_name) or module_name.startswith('/') or module_name.startswith('\\'):
            parts = re.split(r'[\\/]', module_name)
            meaningful_parts = [p for p in parts if p and p != '.' and p != '..' and not re.match(r'^[A-Za-z]:$', p)]
            if meaningful_parts:
                return meaningful_parts[0]
        
        if '.' in module_name:
            return module_name.split(".")[0]
        
        return module_name
    
    def _extract_display_name(self, name: str) -> str:
        """提取显示名称"""
        import re
        
        if re.match(r'^[A-Za-z]:[\\/]', name) or name.startswith('/') or name.startswith('\\'):
            parts = re.split(r'[\\/]', name)
            meaningful_parts = [p for p in parts if p and p != '.' and p != '..' and not re.match(r'^[A-Za-z]:$', p)]
            if meaningful_parts:
                return meaningful_parts[-1].replace('.py', '').replace('.java', '').replace('.ts', '')
        
        if '.' in name:
            return name.split('.')[-1]
        
        return name

    def generate_dependency_matrix(
        self,
        packages: list[dict],
        dependencies: list[dict],
        title: Optional[str] = None,
    ) -> str:
        """
        生成依赖矩阵图
        
        Args:
            packages: 包列表
            dependencies: 依赖列表
            title: 图表标题
        """
        lines = ["graph TB"]

        if title:
            lines.append(f"    %% {title}")
            lines.append("    %% Dependency Matrix")

        pkg_names = [p.get("name", p.get("id", "")) for p in packages]
        pkg_ids = [self.sanitize_id(name) for name in pkg_names]

        dep_matrix: dict[tuple[int, int], int] = defaultdict(int)
        for dep in dependencies:
            source = dep.get("source", "")
            target = dep.get("target", "")
            count = dep.get("count", 1)
            
            try:
                src_idx = pkg_names.index(source)
                tgt_idx = pkg_names.index(target)
                dep_matrix[(src_idx, tgt_idx)] += count
            except ValueError:
                pass

        lines.append("    subgraph matrix[\"Dependency Matrix\"]")
        
        header = " | ".join([""] + pkg_names)
        lines.append(f"        %% {header}")

        for i, pkg_name in enumerate(pkg_names):
            row = [pkg_name]
            for j, _ in enumerate(pkg_names):
                if i == j:
                    row.append("-")
                else:
                    count = dep_matrix.get((i, j), 0)
                    row.append(str(count) if count > 0 else "0")
            lines.append(f"        %% {' | '.join(row)}")

        lines.append("    end")

        for i, (pkg_id, pkg_name) in enumerate(zip(pkg_ids, pkg_names)):
            lines.append(f"    {pkg_id}[\"{pkg_name}\"]")

        for (i, j), count in dep_matrix.items():
            if count > 0:
                src_id = pkg_ids[i]
                tgt_id = pkg_ids[j]
                lines.append(f"    {src_id} -->|\"{count}\"| {tgt_id}")

        return self.wrap_mermaid("\n".join(lines))

    def generate_layered_dependency(
        self,
        packages: list[dict],
        dependencies: list[dict],
        layers: list[str],
        title: Optional[str] = None,
    ) -> str:
        """
        生成分层依赖图
        
        Args:
            packages: 包列表
            dependencies: 依赖列表
            layers: 层级定义 [{"name": "", "packages": []}]
            title: 图表标题
        """
        lines = ["graph TB"]

        if title:
            lines.append(f"    %% {title}")
            lines.append("    %% Layered Dependency Diagram")

        layer_packages: dict[str, list] = defaultdict(list)
        for pkg in packages:
            pkg_name = pkg.get("name", pkg.get("id", ""))
            for layer in layers:
                if pkg_name in layer.get("packages", []) or any(
                    pkg_name.startswith(p) for p in layer.get("packages", [])
                ):
                    layer_packages[layer.get("name", "Layer")].append(pkg)
                    break
            else:
                layer_packages["Other"].append(pkg)

        layer_order = [l.get("name", "Layer") for l in layers] + ["Other"]
        layer_colors = ["#4CAF50", "#2196F3", "#9C27B0", "#FF9800", "#607D8B"]

        for i, layer_name in enumerate(layer_order):
            pkgs = layer_packages.get(layer_name, [])
            if not pkgs:
                continue
            
            color = layer_colors[i % len(layer_colors)]
            layer_id = self.sanitize_id(layer_name)
            
            lines.append(f"    subgraph {layer_id}[\"{layer_name}\"]")
            lines.append(f"    style {layer_id} fill:{color}20,stroke:{color}")
            
            for pkg in pkgs:
                pkg_id = self.sanitize_id(pkg.get("id", pkg.get("name", "")))
                pkg_name = pkg.get("name", "Package")
                lines.append(f"        {pkg_id}[\"{pkg_name}\"]")
                lines.append(f"        style {pkg_id} fill:{color},stroke:{color}")
            
            lines.append("    end")

        for dep in dependencies:
            source = self.sanitize_id(dep.get("source", ""))
            target = self.sanitize_id(dep.get("target", ""))
            dep_type = dep.get("type", "import")
            
            if source and target:
                lines.append(f"    {source} -->|\"{dep_type}\"| {target}")

        return self.wrap_mermaid("\n".join(lines))

    def analyze_dependencies(
        self,
        packages: list[dict],
        dependencies: list[dict],
    ) -> dict[str, Any]:
        """
        分析依赖关系
        
        Returns:
            包含以下内容的分析结果:
            - circular_dependencies: 循环依赖
            - hotspots: 热点模块
            - depth: 依赖深度
            - coupling: 耦合度分析
        """
        circular = self._detect_circular_dependencies(dependencies)
        hotspots = self._detect_hotspots({p.get("id", p.get("name", "")): p for p in packages}, dependencies)
        depth = self._calculate_dependency_depth(packages, dependencies)
        coupling = self._analyze_coupling(packages, dependencies)

        return {
            "circular_dependencies": circular,
            "hotspots": hotspots,
            "depth": depth,
            "coupling": coupling,
        }

    def _detect_circular_dependencies(self, dependencies: list[dict]) -> list[list[str]]:
        """检测循环依赖"""
        graph: dict[str, set] = defaultdict(set)
        
        for dep in dependencies:
            source = dep.get("source", "")
            target = dep.get("target", "")
            if source and target:
                graph[source].add(target)

        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: list) -> Optional[list]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    result = dfs(neighbor, path.copy())
                    if result:
                        return result
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]

            rec_stack.remove(node)
            return None

        for node in list(graph.keys()):
            if node not in visited:
                cycle = dfs(node, [])
                if cycle:
                    cycle_key = "->".join(sorted(cycle))
                    if not any("->".join(sorted(c)) == cycle_key for c in cycles):
                        cycles.append(cycle)

        return cycles[:10]

    def _detect_hotspots(
        self,
        packages: dict,
        dependencies: list[dict],
    ) -> list[str]:
        """检测热点模块"""
        incoming: dict[str, int] = defaultdict(int)
        outgoing: dict[str, int] = defaultdict(int)

        for dep in dependencies:
            source = dep.get("source", "")
            target = dep.get("target", "")
            if source:
                outgoing[source] += 1
            if target:
                incoming[target] += 1

        hotspots = []
        for pkg_id in packages:
            total = incoming.get(pkg_id, 0) + outgoing.get(pkg_id, 0)
            if total > 5:
                hotspots.append(pkg_id)

        return sorted(hotspots, key=lambda x: incoming.get(x, 0) + outgoing.get(x, 0), reverse=True)[:10]

    def _calculate_dependency_depth(
        self,
        packages: list[dict],
        dependencies: list[dict],
    ) -> dict[str, int]:
        """计算依赖深度"""
        graph: dict[str, set] = defaultdict(set)
        for dep in dependencies:
            source = dep.get("source", "")
            target = dep.get("target", "")
            if source and target:
                graph[source].add(target)

        depths: dict[str, int] = {}

        def get_depth(node: str, visited: set) -> int:
            if node in depths:
                return depths[node]
            if node in visited:
                return 0

            visited.add(node)
            if not graph.get(node):
                depths[node] = 0
                return 0

            max_child_depth = max(get_depth(child, visited.copy()) for child in graph[node])
            depths[node] = max_child_depth + 1
            return depths[node]

        for pkg in packages:
            pkg_id = pkg.get("id", pkg.get("name", ""))
            get_depth(pkg_id, set())

        return depths

    def _analyze_coupling(
        self,
        packages: list[dict],
        dependencies: list[dict],
    ) -> dict[str, Any]:
        """分析耦合度"""
        afferent: dict[str, int] = defaultdict(int)
        efferent: dict[str, int] = defaultdict(int)

        for dep in dependencies:
            source = dep.get("source", "")
            target = dep.get("target", "")
            if source:
                efferent[source] += 1
            if target:
                afferent[target] += 1

        total_packages = len(packages)
        coupling_analysis = {}

        for pkg in packages:
            pkg_id = pkg.get("id", pkg.get("name", ""))
            afferent_count = afferent.get(pkg_id, 0)
            efferent_count = efferent.get(pkg_id, 0)

            if total_packages > 1:
                instability = efferent_count / (afferent_count + efferent_count) if (afferent_count + efferent_count) > 0 else 0
            else:
                instability = 0

            coupling_analysis[pkg_id] = {
                "afferent_coupling": afferent_count,
                "efferent_coupling": efferent_count,
                "instability": round(instability, 2),
                "abstractness": 0,
            }

        return coupling_analysis
