"""
数据流图生成器
"""
from typing import TYPE_CHECKING, Any

from pywiki.generators.diagrams.architecture import ArchitectureDiagramGenerator

if TYPE_CHECKING:
    from pywiki.generators.docs.base import DocGeneratorContext


class DataFlowDiagramGenerator:
    """数据流图生成器"""

    def __init__(self, arch_diagram_gen: ArchitectureDiagramGenerator):
        self.arch_diagram_gen = arch_diagram_gen

    def generate(self, context: "DocGeneratorContext", filter_modules_func, labels: dict) -> str:
        """生成数据流图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""

        filtered_modules = filter_modules_func(
            context.parse_result.modules,
            context.project_name
        )

        if not filtered_modules:
            return ""

        modules = filtered_modules[:15]

        nodes = []
        flows = []

        nodes.append({
            "id": "client",
            "name": "Client",
            "type": "external_entity",
            "description": labels.get("external_client", "External Client"),
        })

        api_nodes = []
        service_nodes = []
        data_nodes = []

        for module in modules:
            module_name = module.name if hasattr(module, "name") else str(module)
            name_lower = module_name.lower()
            display_name = self._extract_display_name(module_name)
            node_id = self._sanitize_id(module_name)

            if any(kw in name_lower for kw in ["api", "controller", "router", "handler", "endpoint"]):
                nodes.append({
                    "id": node_id,
                    "name": display_name,
                    "type": "process",
                    "description": labels.get("api_entry", "API Entry"),
                })
                api_nodes.append(node_id)
                flows.append({
                    "source": "client",
                    "target": node_id,
                    "data_name": "HTTP Request",
                })
            elif any(kw in name_lower for kw in ["service", "manager", "processor"]):
                nodes.append({
                    "id": node_id,
                    "name": display_name,
                    "type": "process",
                    "description": labels.get("business_processing", "Business Processing"),
                })
                service_nodes.append(node_id)
            elif any(kw in name_lower for kw in ["repository", "dao", "store", "db", "database"]):
                nodes.append({
                    "id": node_id,
                    "name": display_name,
                    "type": "data_store",
                    "description": labels.get("data_storage", "Data Storage"),
                })
                data_nodes.append(node_id)

        if not api_nodes and not service_nodes and not data_nodes:
            for module in modules[:5]:
                module_name = module.name if hasattr(module, "name") else str(module)
                display_name = self._extract_display_name(module_name)
                node_id = self._sanitize_id(module_name)

                nodes.append({
                    "id": node_id,
                    "name": display_name,
                    "type": "process",
                    "description": "Processing",
                })
                flows.append({
                    "source": "client",
                    "target": node_id,
                    "data_name": "Input",
                })

        for api_id in api_nodes:
            for svc_id in service_nodes:
                flows.append({
                    "source": api_id,
                    "target": svc_id,
                    "data_name": labels.get("request", "Request"),
                })

        for svc_id in service_nodes:
            for data_id in data_nodes:
                flows.append({
                    "source": svc_id,
                    "target": data_id,
                    "data_name": labels.get("data_operation", "Data Operation"),
                })

        data = {"nodes": nodes[:12], "flows": flows[:20]}

        lines = ["graph LR"]
        for node in data["nodes"]:
            node_id = node.get("id", "")
            name = node.get("name", "")
            node_type = node.get("type", "process")

            if node_type == "external_entity":
                lines.append(f'    {node_id}["{name}"]')
                lines.append(f"    style {node_id} fill:#e1f5fe,stroke:#01579b")
            elif node_type == "process":
                lines.append(f'    {node_id}("{name}")')
                lines.append(f"    style {node_id} fill:#fff3e0,stroke:#e65100")
            elif node_type == "data_store":
                lines.append(f'    {node_id}[["{name}"]]')
                lines.append(f"    style {node_id} fill:#f3e5f5,stroke:#4a148c")

        for flow in data["flows"]:
            source = flow.get("source", "")
            target = flow.get("target", "")
            data_name = flow.get("data_name", "")
            if source and target:
                lines.append(f'    {source} -->|"{data_name}"| {target}')

        return self.arch_diagram_gen.wrap_mermaid("\n".join(lines))

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

    def _sanitize_id(self, name: str) -> str:
        """将名称转换为有效的 Mermaid ID"""
        return self.arch_diagram_gen.sanitize_id(name)
