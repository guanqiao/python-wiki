"""
依赖分析器
分析模块依赖关系、循环依赖、热点模块等
"""

from collections import defaultdict
from typing import TYPE_CHECKING, Any, Optional

from .module_filter import ModuleFilter

if TYPE_CHECKING:
    from pywiki.generators.docs.base import DocGeneratorContext


class DependencyAnalyzer:
    """依赖分析器"""

    def __init__(self, labels: dict):
        self.labels = labels

    def analyze_external(self, context: "DocGeneratorContext") -> list[dict[str, Any]]:
        """分析外部依赖"""
        if not context.parse_result or not context.parse_result.modules:
            return []

        dep_counts: dict[str, dict] = defaultdict(lambda: {"count": 0, "category": "other"})

        for module in context.parse_result.modules:
            if hasattr(module, "imports") and module.imports:
                for imp in module.imports:
                    imp_module = imp.module if hasattr(imp, "module") else str(imp)
                    base = imp_module.split(".")[0]

                    if base in ModuleFilter.STANDARD_LIBS:
                        continue

                    if base not in dep_counts:
                        category = ModuleFilter.get_external_category(imp_module)
                        dep_counts[base]["category"] = category

                    dep_counts[base]["count"] += 1

        sorted_deps = sorted(dep_counts.items(), key=lambda x: x[1]["count"], reverse=True)[:15]

        return [
            {
                "name": name,
                "count": info["count"],
                "category": info["category"],
            }
            for name, info in sorted_deps
        ]

    def detect_circular(self, context: "DocGeneratorContext") -> list[dict[str, Any]]:
        """检测循环依赖"""
        circular = []

        if not context.parse_result or not context.parse_result.modules:
            return circular

        module_names = {m.name for m in context.parse_result.modules}
        dependencies: dict[str, set] = defaultdict(set)

        for module in context.parse_result.modules:
            for imp in module.imports:
                if imp.module in module_names or imp.module.startswith("."):
                    target = imp.module if imp.module in module_names else module.name.rsplit(".", 1)[0] + imp.module
                    if target in module_names:
                        dependencies[module.name].add(target)

        def find_cycle(start: str, current: str, path: list, visited: set) -> Optional[list]:
            if current in visited:
                if current == start and len(path) > 1:
                    return path
                return None

            visited.add(current)
            path.append(current)

            for dep in dependencies.get(current, []):
                result = find_cycle(start, dep, path.copy(), visited.copy())
                if result:
                    return result

            return None

        found_cycles = set()
        for module in context.parse_result.modules:
            cycle = find_cycle(module.name, module.name, [], set())
            if cycle:
                cycle_key = "->".join(sorted(cycle))
                if cycle_key not in found_cycles:
                    found_cycles.add(cycle_key)
                    circular.append({
                        "cycle": cycle,
                        "severity": "high" if len(cycle) <= 3 else "medium",
                        "description": f"循环依赖: {' -> '.join(cycle)}",
                    })

        return circular[:5]

    def detect_hot_spots(self, context: "DocGeneratorContext") -> list[dict[str, Any]]:
        """检测热点模块（被大量依赖的模块）"""
        hot_spots = []

        if not context.parse_result or not context.parse_result.modules:
            return hot_spots

        incoming_counts: dict[str, int] = defaultdict(int)
        outgoing_counts: dict[str, int] = defaultdict(int)
        module_names = {m.name for m in context.parse_result.modules}

        for module in context.parse_result.modules:
            for imp in module.imports:
                if imp.module in module_names:
                    incoming_counts[imp.module] += 1
                    outgoing_counts[module.name] += 1

        for module in context.parse_result.modules:
            incoming = incoming_counts.get(module.name, 0)
            outgoing = outgoing_counts.get(module.name, 0)

            if incoming > 3 or outgoing > 5:
                hot_spots.append({
                    "name": module.name,
                    "incoming": incoming,
                    "outgoing": outgoing,
                    "total": incoming + outgoing,
                    "risk": "high" if incoming > 5 else "medium",
                    "description": f"被 {incoming} 个模块依赖，依赖 {outgoing} 个模块",
                })

        hot_spots.sort(key=lambda x: x["total"], reverse=True)
        return hot_spots[:10]