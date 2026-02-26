"""
组件图生成器
"""

from typing import Any, Optional

from pywiki.generators.diagrams.base import BaseDiagramGenerator


class ComponentDiagramGenerator(BaseDiagramGenerator):
    """
    生成组件图
    
    示例输出:
    graph TB
        subgraph Frontend
            UI[UI Components]
            State[State Management]
        end
        subgraph Backend
            API[API Layer]
            Service[Service Layer]
            Repo[Repository Layer]
        end
        subgraph External
            DB[(Database)]
            Cache[(Cache)]
        end
        UI --> State
        UI --> API
        API --> Service
        Service --> Repo
        Repo --> DB
        Service --> Cache
    """

    def generate(self, data: dict, title: Optional[str] = None) -> str:
        components = data.get("components", [])
        connections = data.get("connections", [])
        groups = data.get("groups", [])

        lines = ["graph TB"]

        if title:
            lines.append(f"    %% {title}")

        for group in groups:
            group_name = group.get("name", "")
            group_components = group.get("components", [])

            lines.append(f"    subgraph {self.sanitize_id(group_name)}")
            lines.append(f"        {group_name}")

            for comp_name in group_components:
                comp = next((c for c in components if c.get("name") == comp_name), None)
                if comp:
                    comp_id = self.sanitize_id(comp_name)
                    comp_type = comp.get("type", "component")
                    comp_label = comp.get("label", comp_name)

                    if comp_type == "database":
                        lines.append(f"        {comp_id}[({comp_label})]")
                    elif comp_type == "queue":
                        lines.append(f"        {comp_id}>{{{comp_label}}}")
                    elif comp_type == "interface":
                        lines.append(f"        {comp_id}[({comp_label})]")
                    else:
                        lines.append(f"        {comp_id}[{comp_label}]")

            lines.append("    end")

        for comp in components:
            comp_name = comp.get("name", "")
            if not any(comp_name in g.get("components", []) for g in groups):
                comp_id = self.sanitize_id(comp_name)
                comp_type = comp.get("type", "component")
                comp_label = comp.get("label", comp_name)

                if comp_type == "database":
                    lines.append(f"    {comp_id}[({comp_label})]")
                elif comp_type == "queue":
                    lines.append(f"    {comp_id}>{{{comp_label}}}")
                else:
                    lines.append(f"    {comp_id}[{comp_label}]")

        for conn in connections:
            source = self.sanitize_id(conn.get("source", ""))
            target = self.sanitize_id(conn.get("target", ""))
            label = conn.get("label", "")
            conn_type = conn.get("type", "sync")

            arrow = self._get_arrow(conn_type)

            if source and target:
                if label:
                    lines.append(f"    {source} {arrow}|{label}| {target}")
                else:
                    lines.append(f"    {source} {arrow} {target}")

        return self.wrap_mermaid("\n".join(lines))

    def _get_arrow(self, conn_type: str) -> str:
        arrows = {
            "sync": "-->",
            "async": "-.->",
            "bidirectional": "---",
            "dependency": "-..->",
        }
        return arrows.get(conn_type, "-->")

    def generate_from_modules(self, modules: list[dict]) -> str:
        """从模块信息生成组件图"""
        components = []
        connections = []
        groups = []

        group_map = {}

        for module in modules:
            name = module.get("name", "")
            module_type = self._detect_component_type(name)
            dependencies = module.get("dependencies", [])

            components.append({
                "name": name,
                "type": "component",
                "label": name
            })

            if module_type not in group_map:
                group_map[module_type] = []
            group_map[module_type].append(name)

            for dep in dependencies:
                connections.append({
                    "source": name,
                    "target": dep,
                    "type": "sync"
                })

        for group_name, group_components in group_map.items():
            groups.append({
                "name": group_name,
                "components": group_components
            })

        return self.generate({
            "components": components,
            "connections": connections,
            "groups": groups
        })

    def _detect_component_type(self, name: str) -> str:
        name_lower = name.lower()
        if any(x in name_lower for x in ["ui", "view", "component", "page"]):
            return "Frontend"
        elif any(x in name_lower for x in ["api", "controller", "router", "endpoint"]):
            return "API Layer"
        elif any(x in name_lower for x in ["service", "handler", "manager"]):
            return "Service Layer"
        elif any(x in name_lower for x in ["repo", "dao", "repository", "store"]):
            return "Data Access"
        elif any(x in name_lower for x in ["model", "entity", "schema"]):
            return "Data Models"
        elif any(x in name_lower for x in ["util", "helper", "common"]):
            return "Utilities"
        else:
            return "Core"

    def generate_microservices(self, services: list[dict]) -> str:
        """生成微服务架构组件图"""
        components = []
        connections = []
        groups = []

        components.append({
            "name": "Gateway",
            "type": "interface",
            "label": "API Gateway"
        })

        components.append({
            "name": "MessageQueue",
            "type": "queue",
            "label": "Message Queue"
        })

        for service in services:
            name = service.get("name", "")
            components.append({
                "name": name,
                "type": "component",
                "label": name
            })

            connections.append({
                "source": "Gateway",
                "target": name,
                "type": "sync"
            })

            if service.get("uses_queue"):
                connections.append({
                    "source": name,
                    "target": "MessageQueue",
                    "type": "async"
                })

            db_name = f"{name}_DB"
            components.append({
                "name": db_name,
                "type": "database",
                "label": f"{name} DB"
            })
            connections.append({
                "source": name,
                "target": db_name,
                "type": "sync"
            })

            for dep in service.get("dependencies", []):
                connections.append({
                    "source": name,
                    "target": dep,
                    "type": "async",
                    "label": "calls"
                })

        groups.append({
            "name": "Services",
            "components": [s.get("name", "") for s in services]
        })

        return self.generate({
            "components": components,
            "connections": connections,
            "groups": groups
        })
