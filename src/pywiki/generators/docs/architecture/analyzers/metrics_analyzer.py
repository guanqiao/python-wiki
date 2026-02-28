"""
质量指标分析器
计算架构质量指标
"""

from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pywiki.generators.docs.base import DocGeneratorContext


class MetricsAnalyzer:
    """质量指标分析器"""

    def analyze(self, context: "DocGeneratorContext") -> dict[str, Any]:
        """计算架构质量指标"""
        metrics = {
            "coupling": {"value": 0, "level": "unknown", "description": ""},
            "cohesion": {"value": 0, "level": "unknown", "description": ""},
            "dependency_depth": {"value": 0, "level": "unknown", "description": ""},
            "module_count": 0,
            "class_count": 0,
            "function_count": 0,
            "avg_methods_per_class": 0,
            "avg_functions_per_module": 0,
        }

        if not context.parse_result or not context.parse_result.modules:
            return metrics

        modules = context.parse_result.modules
        metrics["module_count"] = len(modules)

        total_classes = 0
        total_functions = 0
        total_methods = 0
        total_imports = 0
        import_counts: dict[str, int] = defaultdict(int)

        for module in modules:
            class_count = len(module.classes) if module.classes else 0
            func_count = len(module.functions) if module.functions else 0

            total_classes += class_count
            total_functions += func_count

            # 统计类中的方法
            for cls in (module.classes or []):
                method_count = len(cls.methods) if cls.methods else 0
                total_methods += method_count
                # 将方法也计入总函数数
                total_functions += method_count

            for imp in (module.imports or []):
                if not imp.module.startswith("."):
                    base = imp.module.split(".")[0]
                    import_counts[base] += 1
                    total_imports += 1

        metrics["class_count"] = total_classes
        # 总函数数 = 顶层函数 + 类方法
        metrics["function_count"] = total_functions

        if total_classes > 0:
            metrics["avg_methods_per_class"] = round(total_methods / total_classes, 1)

        if len(modules) > 0:
            metrics["avg_functions_per_module"] = round(total_functions / len(modules), 1)

        if len(modules) > 1:
            unique_imports = len(import_counts)
            coupling_ratio = unique_imports / len(modules)

            if coupling_ratio < 0.3:
                metrics["coupling"] = {"value": round(coupling_ratio * 100, 1), "level": "low", "description": "模块间耦合度较低，架构清晰"}
            elif coupling_ratio < 0.6:
                metrics["coupling"] = {"value": round(coupling_ratio * 100, 1), "level": "medium", "description": "模块间存在适度耦合"}
            else:
                metrics["coupling"] = {"value": round(coupling_ratio * 100, 1), "level": "high", "description": "模块间耦合度较高，建议重构"}

        if total_classes > 0 and total_methods > 0:
            avg_methods = total_methods / total_classes
            if avg_methods > 10:
                metrics["cohesion"] = {"value": round(avg_methods, 1), "level": "low", "description": "类可能职责过多，内聚性较低"}
            elif avg_methods > 5:
                metrics["cohesion"] = {"value": round(avg_methods, 1), "level": "medium", "description": "类内聚性适中"}
            else:
                metrics["cohesion"] = {"value": round(avg_methods, 1), "level": "high", "description": "类职责单一，内聚性较好"}

        max_depth = 0
        for module in modules:
            depth = module.name.count(".")
            max_depth = max(max_depth, depth)

        metrics["dependency_depth"] = {"value": max_depth, "level": "ok" if max_depth < 4 else "deep", "description": f"最大依赖深度 {max_depth} 层"}

        return metrics