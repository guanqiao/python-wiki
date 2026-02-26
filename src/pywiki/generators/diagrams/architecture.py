"""
架构图生成器
"""

from typing import Any, Optional

from pywiki.generators.diagrams.base import BaseDiagramGenerator


class ArchitectureDiagramGenerator(BaseDiagramGenerator):
    """
    生成系统架构图
    
    示例输出:
    graph TB
        subgraph Frontend
            UI[用户界面]
            API[API 网关]
        end
        subgraph Backend
            Auth[认证服务]
            Business[业务逻辑]
            DB[(数据库)]
        end
        UI --> API
        API --> Auth
        Auth --> Business
        Business --> DB
    """

    def generate(self, data: dict, title: Optional[str] = None) -> str:
        layers = data.get("layers", [])
        connections = data.get("connections", [])

        lines = ["graph TB"]

        if title:
            lines.append(f"    %% {title}")

        for layer in layers:
            layer_name = layer.get("name", "Layer")
            components = layer.get("components", [])

            lines.append(f"    subgraph {self.sanitize_id(layer_name)}")
            lines.append(f"        {layer_name}")

            for comp in components:
                comp_name = comp.get("name", "Component")
                comp_type = comp.get("type", "node")
                comp_id = self.sanitize_id(comp_name)

                if comp_type == "database":
                    lines.append(f"        {comp_id}[({comp_name})]")
                elif comp_type == "queue":
                    lines.append(f"        {comp_id}>{{{comp_name}}}")
                elif comp_type == "subroutine":
                    lines.append(f"        {comp_id}[{comp_name}]")
                else:
                    lines.append(f"        {comp_id}[{comp_name}]")

            lines.append("    end")

        for conn in connections:
            source = self.sanitize_id(conn.get("source", ""))
            target = self.sanitize_id(conn.get("target", ""))
            label = conn.get("label", "")

            if source and target:
                if label:
                    lines.append(f"    {source} -->|{label}| {target}")
                else:
                    lines.append(f"    {source} --> {target}")

        return self.wrap_mermaid("\n".join(lines))

    def generate_from_modules(self, modules: list[dict]) -> str:
        """从模块信息生成架构图"""
        layers = []
        connections = []

        layer_map = {
            "ui": {"name": "Frontend", "components": []},
            "api": {"name": "API Layer", "components": []},
            "service": {"name": "Service Layer", "components": []},
            "repository": {"name": "Data Access", "components": []},
            "model": {"name": "Data Models", "components": []},
            "util": {"name": "Utilities", "components": []},
        }

        for module in modules:
            name = module.get("name", "")
            module_type = self._detect_module_type(name)

            if module_type in layer_map:
                layer_map[module_type]["components"].append({
                    "name": name,
                    "type": "node"
                })

        layers = [layer for layer in layer_map.values() if layer["components"]]

        for i in range(len(layers) - 1):
            for comp1 in layers[i]["components"]:
                for comp2 in layers[i + 1]["components"]:
                    connections.append({
                        "source": comp1["name"],
                        "target": comp2["name"]
                    })

        return self.generate({"layers": layers, "connections": connections})

    def _detect_module_type(self, name: str) -> str:
        name_lower = name.lower()
        if any(x in name_lower for x in ["ui", "view", "frontend", "web"]):
            return "ui"
        elif any(x in name_lower for x in ["api", "controller", "router", "endpoint"]):
            return "api"
        elif any(x in name_lower for x in ["service", "handler", "manager"]):
            return "service"
        elif any(x in name_lower for x in ["repo", "dao", "repository", "store"]):
            return "repository"
        elif any(x in name_lower for x in ["model", "entity", "schema", "domain"]):
            return "model"
        else:
            return "util"
