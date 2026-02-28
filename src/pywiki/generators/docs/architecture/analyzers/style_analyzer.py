"""
架构风格分析器
检测项目的架构风格
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pywiki.generators.docs.base import DocGeneratorContext


class StyleAnalyzer:
    """架构风格分析器"""

    def __init__(self, labels: dict):
        self.labels = labels

    def analyze(self, context: "DocGeneratorContext") -> str:
        """检测架构风格"""
        if not context.parse_result or not context.parse_result.modules:
            return self.labels.get("monolithic_arch", "Monolithic Architecture")

        modules = context.parse_result.modules
        module_names = []
        for m in modules:
            if hasattr(m, "name"):
                module_names.append(m.name.lower())
            else:
                module_names.append(str(m).lower())

        if len(modules) <= 3:
            return self.labels.get("simple_script", "Simple Script / Utility")

        service_count = sum(1 for name in module_names if "service" in name)
        controller_count = sum(1 for name in module_names if any(kw in name for kw in ["controller", "api", "router", "handler"]))
        repo_count = sum(1 for name in module_names if any(kw in name for kw in ["repository", "dao", "store"]))
        event_count = sum(1 for name in module_names if any(kw in name for kw in ["event", "queue", "message", "kafka", "rabbit"]))
        command_count = sum(1 for name in module_names if "command" in name)
        query_count = sum(1 for name in module_names if "query" in name)
        adapter_count = sum(1 for name in module_names if "adapter" in name)

        if event_count > 2:
            return self.labels.get("event_driven_arch", "Event-Driven Architecture")
        if command_count > 0 and query_count > 0:
            return self.labels.get("cqrs_arch", "CQRS Architecture")
        if adapter_count > 1:
            return self.labels.get("hexagonal_arch", "Hexagonal Architecture")
        if service_count > 5 and controller_count > 2:
            return self.labels.get("microservice_arch", "Microservice Architecture")
        if controller_count > 0 and service_count > 0 and repo_count > 0:
            return self.labels.get("layered_arch", "Layered Architecture")
        if service_count > 0 or controller_count > 0:
            return self.labels.get("modular_arch", "Modular Architecture")

        return self.labels.get("monolithic_arch", "Monolithic Architecture")
