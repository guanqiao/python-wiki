"""
架构图生成器
支持多种架构风格的自动识别和智能生成
"""

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from pywiki.generators.diagrams.base import BaseDiagramGenerator


class ArchitectureStyle(str, Enum):
    """架构风格枚举"""
    LAYERED = "layered"
    MICROSERVICE = "microservice"
    MONOLITHIC = "monolithic"
    EVENT_DRIVEN = "event_driven"
    CQRS = "cqrs"
    HEXAGONAL = "hexagonal"
    PLUGIN = "plugin"
    PIPELINE = "pipeline"


class ComponentType(str, Enum):
    """组件类型枚举"""
    API = "api"
    SERVICE = "service"
    REPOSITORY = "repository"
    MODEL = "model"
    CONTROLLER = "controller"
    HANDLER = "handler"
    QUEUE = "queue"
    DATABASE = "database"
    CACHE = "cache"
    GATEWAY = "gateway"
    EXTERNAL = "external"
    UTIL = "util"
    CONFIG = "config"
    DOMAIN = "domain"
    INFRASTRUCTURE = "infrastructure"


@dataclass
class ArchitectureComponent:
    """架构组件"""
    id: str
    name: str
    component_type: ComponentType
    layer: str = ""
    description: str = ""
    technology: str = ""
    dependencies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class ArchitectureLayer:
    """架构层"""
    name: str
    description: str = ""
    components: list[ArchitectureComponent] = field(default_factory=list)
    color: str = "#4A90D9"


class ArchitectureDiagramGenerator(BaseDiagramGenerator):
    """
    增强的架构图生成器
    
    支持:
    - 多种架构风格自动识别
    - 智能组件聚类和布局
    - 自定义样式主题
    - 从代码解析结果自动生成
    """

    LAYER_COLORS = {
        "presentation": "#4CAF50",
        "api": "#2196F3",
        "application": "#9C27B0",
        "service": "#9C27B0",
        "domain": "#FF9800",
        "business": "#FF9800",
        "infrastructure": "#607D8B",
        "data": "#795548",
        "persistence": "#795548",
    }

    COMPONENT_SHAPES = {
        ComponentType.API: "[",
        ComponentType.SERVICE: "[",
        ComponentType.REPOSITORY: "[(",
        ComponentType.MODEL: "[",
        ComponentType.CONTROLLER: "[",
        ComponentType.HANDLER: "[",
        ComponentType.QUEUE: "{",
        ComponentType.DATABASE: "[(",
        ComponentType.CACHE: "[(",
        ComponentType.GATEWAY: "[",
        ComponentType.EXTERNAL: "[",
        ComponentType.UTIL: "[",
        ComponentType.CONFIG: "[",
        ComponentType.DOMAIN: "[",
        ComponentType.INFRASTRUCTURE: "[",
    }

    LAYER_PATTERNS = {
        "presentation": {
            "keywords": ["ui", "view", "frontend", "web", "page", "component", "widget", "template"],
            "component_types": [ComponentType.CONTROLLER, ComponentType.HANDLER],
        },
        "api": {
            "keywords": ["api", "router", "endpoint", "controller", "handler", "gateway", "rest", "graphql"],
            "component_types": [ComponentType.API, ComponentType.GATEWAY, ComponentType.CONTROLLER],
        },
        "application": {
            "keywords": ["application", "app", "usecase", "use_case", "command", "query", "handler"],
            "component_types": [ComponentType.HANDLER, ComponentType.SERVICE],
        },
        "service": {
            "keywords": ["service", "manager", "processor", "executor", "worker"],
            "component_types": [ComponentType.SERVICE],
        },
        "domain": {
            "keywords": ["domain", "entity", "model", "aggregate", "value_object", "vo"],
            "component_types": [ComponentType.DOMAIN, ComponentType.MODEL],
        },
        "infrastructure": {
            "keywords": ["infrastructure", "infra", "adapter", "client", "external", "config", "util", "common", "helper"],
            "component_types": [ComponentType.INFRASTRUCTURE, ComponentType.UTIL, ComponentType.CONFIG],
        },
        "persistence": {
            "keywords": ["repository", "dao", "store", "persistence", "db", "database", "mapper", "schema"],
            "component_types": [ComponentType.REPOSITORY, ComponentType.DATABASE],
        },
    }

    def __init__(self, theme: str = "default"):
        self.theme = theme
        self.layers: list[ArchitectureLayer] = []
        self.components: list[ArchitectureComponent] = []
        self.relationships: list[tuple[str, str, str]] = []

    def generate(
        self,
        data: dict,
        title: Optional[str] = None,
        style: Optional[ArchitectureStyle] = None,
    ) -> str:
        """
        生成架构图
        
        Args:
            data: 包含以下字段:
                - layers: 层级列表 [{"name": "", "components": []}]
                - components: 组件列表 [{"id": "", "name": "", "type": "", "layer": ""}]
                - connections: 连接列表 [{"source": "", "target": "", "label": ""}]
                - style: 架构风格
            title: 图表标题
            style: 架构风格（可选，会自动从数据推断）
        """
        layers = data.get("layers", [])
        components = data.get("components", [])
        connections = data.get("connections", [])
        detected_style = style or data.get("style") or self._detect_style(data)

        lines = ["graph TB"]

        if title:
            lines.append(f"    %% {title}")
            lines.append(f"    %% Architecture Style: {detected_style.value if isinstance(detected_style, ArchitectureStyle) else detected_style}")

        if detected_style == ArchitectureStyle.MICROSERVICE:
            return self._generate_microservice_diagram(data, title)
        elif detected_style == ArchitectureStyle.EVENT_DRIVEN:
            return self._generate_event_driven_diagram(data, title)
        elif detected_style == ArchitectureStyle.HEXAGONAL:
            return self._generate_hexagonal_diagram(data, title)
        elif detected_style == ArchitectureStyle.CQRS:
            return self._generate_cqrs_diagram(data, title)

        if layers:
            for layer in layers:
                layer_name = layer.get("name", "Layer")
                layer_components = layer.get("components", [])
                layer_id = self.sanitize_id(layer_name)
                color = self.LAYER_COLORS.get(layer_name.lower(), "#4A90D9")

                lines.append(f"    subgraph {layer_id}_group[\"{layer_name}\"]")
                lines.append(f"    style {layer_id}_group fill:{color}20,stroke:{color},stroke-width:2px")

                for comp in layer_components:
                    comp_id = self.sanitize_id(comp.get("id", comp.get("name", "")))
                    comp_name = comp.get("name", "")
                    comp_type = comp.get("type", "service")
                    comp_desc = comp.get("description", "")

                    shape = self._get_shape_for_type(comp_type)
                    label = comp_name
                    if comp_desc:
                        label += f"<br/><small>{comp_desc[:30]}</small>"

                    lines.append(f"        {comp_id}{shape}\"{label}\"{self._get_close_shape(shape)}")
                    lines.append(f"        style {comp_id} fill:{color},stroke:{color}")

                lines.append("    end")
        else:
            for comp in components:
                comp_id = self.sanitize_id(comp.get("id", comp.get("name", "")))
                comp_name = comp.get("name", "")
                comp_type = comp.get("type", "service")
                comp_desc = comp.get("description", "")

                shape = self._get_shape_for_type(comp_type)
                label = comp_name
                if comp_desc:
                    label += f"<br/><small>{comp_desc[:30]}</small>"

                lines.append(f"    {comp_id}{shape}\"{label}\"{self._get_close_shape(shape)}")

        for conn in connections:
            source = self.sanitize_id(conn.get("source", ""))
            target = self.sanitize_id(conn.get("target", ""))
            label = conn.get("label", "")
            conn_type = conn.get("type", "sync")

            if source and target:
                arrow = self._get_arrow_for_connection(conn_type)
                if label:
                    lines.append(f"    {source} {arrow}|\"{label}\"| {target}")
                else:
                    lines.append(f"    {source} {arrow} {target}")

        return self.wrap_mermaid("\n".join(lines))

    def generate_from_parse_result(
        self,
        parse_result: Any,
        project_name: str = "Project",
        title: Optional[str] = None,
    ) -> str:
        """
        从代码解析结果自动生成架构图
        
        Args:
            parse_result: 代码解析结果，包含 modules 信息
            project_name: 项目名称
            title: 图表标题
        """
        if not parse_result or not hasattr(parse_result, "modules"):
            return self.generate({"layers": [], "components": [], "connections": []}, title)

        modules = parse_result.modules
        layers_dict: dict[str, list[dict]] = defaultdict(list)
        components = []
        connections = []
        module_layer_map: dict[str, str] = {}

        for module in modules:
            module_name = module.name if hasattr(module, "name") else str(module)
            layer = self._detect_layer_for_module(module_name)
            module_layer_map[module_name] = layer

            comp_type = self._detect_component_type(module)
            comp_id = self.sanitize_id(module_name)

            component = {
                "id": comp_id,
                "name": module_name.split(".")[-1],
                "type": comp_type.value if isinstance(comp_type, ComponentType) else comp_type,
                "layer": layer,
                "description": module.docstring[:50] if hasattr(module, "docstring") and module.docstring else "",
            }

            layers_dict[layer].append(component)
            components.append(component)

            if hasattr(module, "imports") and module.imports:
                for imp in module.imports:
                    imp_module = imp.module if hasattr(imp, "module") else str(imp)
                    if imp_module in module_layer_map:
                        source_layer = module_layer_map[imp_module]
                        if source_layer != layer:
                            connections.append({
                                "source": self.sanitize_id(imp_module),
                                "target": comp_id,
                                "label": "",
                                "type": "sync",
                            })

        layers = [
            {"name": layer_name, "components": comps}
            for layer_name, comps in sorted(layers_dict.items(), key=lambda x: self._layer_order(x[0]))
        ]

        style = self._detect_architecture_style(modules, layers_dict)

        data = {
            "layers": layers,
            "components": components,
            "connections": self._deduplicate_connections(connections),
            "style": style,
        }

        return self.generate(data, title or f"{project_name} Architecture")

    def _detect_layer_for_module(self, module_name: str) -> str:
        """检测模块所属层级"""
        name_lower = module_name.lower()
        
        for layer_name, pattern in self.LAYER_PATTERNS.items():
            if any(kw in name_lower for kw in pattern["keywords"]):
                return layer_name
        
        parts = module_name.split(".")
        if len(parts) > 1:
            first_part = parts[0].lower()
            for layer_name, pattern in self.LAYER_PATTERNS.items():
                if any(kw in first_part for kw in pattern["keywords"]):
                    return layer_name
        
        return "infrastructure"

    def _detect_component_type(self, module: Any) -> str:
        """检测组件类型"""
        module_name = module.name if hasattr(module, "name") else str(module)
        name_lower = module_name.lower()

        if any(kw in name_lower for kw in ["api", "router", "endpoint", "rest", "graphql"]):
            return ComponentType.API.value
        elif any(kw in name_lower for kw in ["controller", "handler"]):
            return ComponentType.CONTROLLER.value
        elif any(kw in name_lower for kw in ["service", "manager", "processor"]):
            return ComponentType.SERVICE.value
        elif any(kw in name_lower for kw in ["repository", "dao", "store", "mapper"]):
            return ComponentType.REPOSITORY.value
        elif any(kw in name_lower for kw in ["model", "entity", "domain", "schema"]):
            return ComponentType.MODEL.value
        elif any(kw in name_lower for kw in ["queue", "mq", "kafka", "rabbit"]):
            return ComponentType.QUEUE.value
        elif any(kw in name_lower for kw in ["db", "database", "redis", "cache"]):
            return ComponentType.DATABASE.value
        elif any(kw in name_lower for kw in ["gateway", "proxy"]):
            return ComponentType.GATEWAY.value
        else:
            return ComponentType.UTIL.value

    def _detect_architecture_style(
        self,
        modules: list,
        layers_dict: dict[str, list],
    ) -> ArchitectureStyle:
        """检测架构风格"""
        layer_names = set(layers_dict.keys())
        
        if "api" in layer_names and "service" in layer_names and "persistence" in layer_names:
            return ArchitectureStyle.LAYERED
        
        service_count = sum(1 for m in modules if "service" in (m.name if hasattr(m, "name") else str(m)).lower())
        if service_count > 5:
            return ArchitectureStyle.MICROSERVICE
        
        queue_count = sum(1 for m in modules if any(kw in (m.name if hasattr(m, "name") else str(m)).lower() for kw in ["queue", "event", "message", "kafka", "rabbit"]))
        if queue_count > 0:
            return ArchitectureStyle.EVENT_DRIVEN
        
        command_count = sum(1 for m in modules if "command" in (m.name if hasattr(m, "name") else str(m)).lower())
        query_count = sum(1 for m in modules if "query" in (m.name if hasattr(m, "name") else str(m)).lower())
        if command_count > 0 and query_count > 0:
            return ArchitectureStyle.CQRS
        
        adapter_count = sum(1 for m in modules if "adapter" in (m.name if hasattr(m, "name") else str(m)).lower())
        port_count = sum(1 for m in modules if "port" in (m.name if hasattr(m, "name") else str(m)).lower())
        if adapter_count > 0 or port_count > 0:
            return ArchitectureStyle.HEXAGONAL
        
        return ArchitectureStyle.MONOLITHIC

    def _detect_style(self, data: dict) -> ArchitectureStyle:
        """从数据检测架构风格"""
        layers = data.get("layers", [])
        components = data.get("components", [])
        connections = data.get("connections", [])

        layer_names = [l.get("name", "").lower() for l in layers]

        if any("event" in ln or "queue" in ln for ln in layer_names):
            return ArchitectureStyle.EVENT_DRIVEN
        
        if any("command" in ln for ln in layer_names) and any("query" in ln for ln in layer_names):
            return ArchitectureStyle.CQRS
        
        if any("adapter" in c.get("type", "").lower() for c in components):
            return ArchitectureStyle.HEXAGONAL

        if len([l for l in layers if l.get("components")]) >= 3:
            return ArchitectureStyle.LAYERED

        return ArchitectureStyle.MONOLITHIC

    def _generate_microservice_diagram(self, data: dict, title: Optional[str]) -> str:
        """生成微服务架构图"""
        lines = ["graph TB"]

        if title:
            lines.append(f"    %% {title}")
            lines.append("    %% Microservice Architecture")

        components = data.get("components", [])
        connections = data.get("connections", [])

        services = [c for c in components if c.get("type") in ["service", "api"]]
        databases = [c for c in components if c.get("type") in ["database", "repository"]]
        queues = [c for c in components if c.get("type") == "queue"]
        gateways = [c for c in components if c.get("type") == "gateway"]

        if gateways:
            lines.append("    subgraph gateway_layer[\"API Gateway\"]")
            for gw in gateways:
                gw_id = self.sanitize_id(gw.get("id", gw.get("name", "")))
                lines.append(f"        {gw_id}[\"{gw.get('name', '')}\"]")
                lines.append(f"        style {gw_id} fill:#E91E63,stroke:#C2185B,color:#fff")
            lines.append("    end")

        if services:
            lines.append("    subgraph services[\"Microservices\"]")
            for svc in services:
                svc_id = self.sanitize_id(svc.get("id", svc.get("name", "")))
                lines.append(f"        {svc_id}[\"{svc.get('name', '')}\"]")
                lines.append(f"        style {svc_id} fill:#2196F3,stroke:#1976D2,color:#fff")
            lines.append("    end")

        if queues:
            lines.append("    subgraph messaging[\"Message Queue\"]")
            for q in queues:
                q_id = self.sanitize_id(q.get("id", q.get("name", "")))
                lines.append(f"        {q_id}{{\"{q.get('name', '')}\"}}")
                lines.append(f"        style {q_id} fill:#FF9800,stroke:#F57C00,color:#fff")
            lines.append("    end")

        if databases:
            lines.append("    subgraph data_layer[\"Data Layer\"]")
            for db in databases:
                db_id = self.sanitize_id(db.get("id", db.get("name", "")))
                lines.append(f"        {db_id}[(\"{db.get('name', '')}\")]")
                lines.append(f"        style {db_id} fill:#4CAF50,stroke:#388E3C,color:#fff")
            lines.append("    end")

        for conn in connections:
            source = self.sanitize_id(conn.get("source", ""))
            target = self.sanitize_id(conn.get("target", ""))
            label = conn.get("label", "")
            if source and target:
                if label:
                    lines.append(f"    {source} -->|\"{label}\"| {target}")
                else:
                    lines.append(f"    {source} --> {target}")

        return self.wrap_mermaid("\n".join(lines))

    def _generate_event_driven_diagram(self, data: dict, title: Optional[str]) -> str:
        """生成事件驱动架构图"""
        lines = ["graph LR"]

        if title:
            lines.append(f"    %% {title}")
            lines.append("    %% Event-Driven Architecture")

        components = data.get("components", [])
        connections = data.get("connections", [])

        producers = []
        consumers = []
        event_bus = None
        queues = []

        for comp in components:
            comp_type = comp.get("type", "")
            if comp_type == "queue":
                queues.append(comp)
            elif "producer" in comp.get("name", "").lower():
                producers.append(comp)
            elif "consumer" in comp.get("name", "").lower():
                consumers.append(comp)
            else:
                if "service" in comp_type or "api" in comp_type:
                    producers.append(comp)
                else:
                    consumers.append(comp)

        if queues:
            event_bus = queues[0]
            eb_id = self.sanitize_id(event_bus.get("id", event_bus.get("name", "")))
            lines.append(f"    {eb_id}{{\"{event_bus.get('name', 'Event Bus')}\"}}")
            lines.append(f"    style {eb_id} fill:#FF9800,stroke:#F57C00,color:#fff")

        if producers:
            lines.append("    subgraph producers[\"Event Producers\"]")
            for prod in producers:
                prod_id = self.sanitize_id(prod.get("id", prod.get("name", "")))
                lines.append(f"        {prod_id}[\"{prod.get('name', '')}\"]")
                lines.append(f"        style {prod_id} fill:#2196F3,stroke:#1976D2,color:#fff")
            lines.append("    end")

        if consumers:
            lines.append("    subgraph consumers[\"Event Consumers\"]")
            for cons in consumers:
                cons_id = self.sanitize_id(cons.get("id", cons.get("name", "")))
                lines.append(f"        {cons_id}[\"{cons.get('name', '')}\"]")
                lines.append(f"        style {cons_id} fill:#4CAF50,stroke:#388E3C,color:#fff")
            lines.append("    end")

        if event_bus:
            eb_id = self.sanitize_id(event_bus.get("id", event_bus.get("name", "")))
            for prod in producers:
                prod_id = self.sanitize_id(prod.get("id", prod.get("name", "")))
                lines.append(f"    {prod_id} -->|\"publish\"| {eb_id}")
            for cons in consumers:
                cons_id = self.sanitize_id(cons.get("id", cons.get("name", "")))
                lines.append(f"    {eb_id} -->|\"consume\"| {cons_id}")

        return self.wrap_mermaid("\n".join(lines))

    def _generate_hexagonal_diagram(self, data: dict, title: Optional[str]) -> str:
        """生成六边形架构图"""
        lines = ["graph TB"]

        if title:
            lines.append(f"    %% {title}")
            lines.append("    %% Hexagonal Architecture")

        components = data.get("components", [])
        connections = data.get("connections", [])

        domain_comps = []
        ports = []
        adapters = []

        for comp in components:
            comp_type = comp.get("type", "").lower()
            name_lower = comp.get("name", "").lower()
            
            if "port" in name_lower:
                ports.append(comp)
            elif "adapter" in name_lower or "adapter" in comp_type:
                adapters.append(comp)
            elif comp_type in ["domain", "model", "entity", "service"]:
                domain_comps.append(comp)
            else:
                domain_comps.append(comp)

        if domain_comps:
            lines.append("    subgraph domain[\"Domain Core\"]")
            for comp in domain_comps:
                comp_id = self.sanitize_id(comp.get("id", comp.get("name", "")))
                lines.append(f"        {comp_id}[\"{comp.get('name', '')}\"]")
                lines.append(f"        style {comp_id} fill:#9C27B0,stroke:#7B1FA2,color:#fff")
            lines.append("    end")

        if ports:
            lines.append("    subgraph ports_layer[\"Ports\"]")
            for port in ports:
                port_id = self.sanitize_id(port.get("id", port.get("name", "")))
                lines.append(f"        {port_id}[[\"{port.get('name', '')}\"]]")
                lines.append(f"        style {port_id} fill:#FF9800,stroke:#F57C00,color:#fff")
            lines.append("    end")

        if adapters:
            lines.append("    subgraph adapters_layer[\"Adapters\"]")
            for adapter in adapters:
                adapter_id = self.sanitize_id(adapter.get("id", adapter.get("name", "")))
                lines.append(f"        {adapter_id}[\"{adapter.get('name', '')}\"]")
                lines.append(f"        style {adapter_id} fill:#607D8B,stroke:#455A64,color:#fff")
            lines.append("    end")

        for conn in connections:
            source = self.sanitize_id(conn.get("source", ""))
            target = self.sanitize_id(conn.get("target", ""))
            label = conn.get("label", "")
            if source and target:
                if label:
                    lines.append(f"    {source} -->|\"{label}\"| {target}")
                else:
                    lines.append(f"    {source} --> {target}")

        return self.wrap_mermaid("\n".join(lines))

    def _generate_cqrs_diagram(self, data: dict, title: Optional[str]) -> str:
        """生成 CQRS 架构图"""
        lines = ["graph TB"]

        if title:
            lines.append(f"    %% {title}")
            lines.append("    %% CQRS Architecture")

        components = data.get("components", [])
        connections = data.get("connections", [])

        commands = []
        queries = []
        command_handlers = []
        query_handlers = []
        write_db = None
        read_db = None

        for comp in components:
            name_lower = comp.get("name", "").lower()
            comp_type = comp.get("type", "")
            
            if "command" in name_lower and "handler" not in name_lower:
                commands.append(comp)
            elif "query" in name_lower and "handler" not in name_lower:
                queries.append(comp)
            elif "command_handler" in name_lower or "commandhandler" in name_lower:
                command_handlers.append(comp)
            elif "query_handler" in name_lower or "queryhandler" in name_lower:
                query_handlers.append(comp)
            elif comp_type == "database":
                if not write_db:
                    write_db = comp
                else:
                    read_db = comp

        lines.append("    Client[/\"Client\"]")
        lines.append("    style Client fill:#2196F3,stroke:#1976D2,color:#fff")

        if commands:
            lines.append("    subgraph cmd_side[\"Command Side\"]")
            for cmd in commands:
                cmd_id = self.sanitize_id(cmd.get("id", cmd.get("name", "")))
                lines.append(f"        {cmd_id}[\"{cmd.get('name', '')}\"]")
                lines.append(f"        style {cmd_id} fill:#E91E63,stroke:#C2185B,color:#fff")
            for ch in command_handlers:
                ch_id = self.sanitize_id(ch.get("id", ch.get("name", "")))
                lines.append(f"        {ch_id}[\"{ch.get('name', '')}\"]")
                lines.append(f"        style {ch_id} fill:#F44336,stroke:#D32F2F,color:#fff")
            lines.append("    end")

        if queries:
            lines.append("    subgraph query_side[\"Query Side\"]")
            for q in queries:
                q_id = self.sanitize_id(q.get("id", q.get("name", "")))
                lines.append(f"        {q_id}[\"{q.get('name', '')}\"]")
                lines.append(f"        style {q_id} fill:#4CAF50,stroke:#388E3C,color:#fff")
            for qh in query_handlers:
                qh_id = self.sanitize_id(qh.get("id", qh.get("name", "")))
                lines.append(f"        {qh_id}[\"{qh.get('name', '')}\"]")
                lines.append(f"        style {qh_id} fill:#8BC34A,stroke:#689F38,color:#fff")
            lines.append("    end")

        if write_db:
            wdb_id = self.sanitize_id(write_db.get("id", write_db.get("name", "")))
            lines.append(f"    {wdb_id}[(\"Write DB\")]")
            lines.append(f"    style {wdb_id} fill:#FF5722,stroke:#E64A19,color:#fff")

        if read_db:
            rdb_id = self.sanitize_id(read_db.get("id", read_db.get("name", "")))
            lines.append(f"    {rdb_id}[(\"Read DB\")]")
            lines.append(f"    style {rdb_id} fill:#00BCD4,stroke:#0097A7,color:#fff")

        lines.append("    Client -->|\"Command\"| cmd_side")
        lines.append("    Client -->|\"Query\"| query_side")

        return self.wrap_mermaid("\n".join(lines))

    def _get_shape_for_type(self, comp_type: str) -> str:
        """获取组件类型对应的形状"""
        type_map = {
            "database": "[(",
            "queue": "{",
            "cache": "[(",
            "repository": "[(",
            "external": "[",
            "api": "[",
            "service": "[",
            "controller": "[",
            "handler": "[",
            "model": "[",
            "gateway": "[",
            "util": "[",
            "config": "[",
            "domain": "[",
            "infrastructure": "[",
        }
        return type_map.get(comp_type.lower(), "[")

    def _get_close_shape(self, shape: str) -> str:
        """获取形状的闭合符号"""
        if shape == "[(":
            return ")]"
        elif shape == "{":
            return "}"
        elif shape == "[[":
            return "]]"
        elif shape == "[__":
            return "__]"
        elif shape == "[_":
            return "_]"
        else:
            return "]"

    def _get_arrow_for_connection(self, conn_type: str) -> str:
        """获取连接类型对应的箭头"""
        arrows = {
            "sync": "-->",
            "async": "-.->",
            "event": "-..->",
            "data": "==>",
            "dependency": "..>",
        }
        return arrows.get(conn_type, "-->")

    def _layer_order(self, layer_name: str) -> int:
        """获取层级排序权重"""
        order = {
            "presentation": 1,
            "api": 2,
            "gateway": 2,
            "application": 3,
            "service": 4,
            "domain": 5,
            "business": 5,
            "persistence": 6,
            "data": 6,
            "infrastructure": 7,
        }
        return order.get(layer_name.lower(), 10)

    def _deduplicate_connections(self, connections: list[dict]) -> list[dict]:
        """去重连接"""
        seen = set()
        result = []
        for conn in connections:
            key = (conn.get("source", ""), conn.get("target", ""))
            if key not in seen:
                seen.add(key)
                result.append(conn)
        return result

    def generate_from_modules(self, modules: list[dict]) -> str:
        """从模块信息生成架构图（兼容旧接口）"""
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
                    "id": self.sanitize_id(name),
                    "name": name.split(".")[-1] if "." in name else name,
                    "type": "service",
                })

        layers = [layer for layer in layer_map.values() if layer["components"]]

        for i in range(len(layers) - 1):
            for comp1 in layers[i]["components"]:
                for comp2 in layers[i + 1]["components"]:
                    connections.append({
                        "source": comp1["id"],
                        "target": comp2["id"],
                    })

        return self.generate({"layers": layers, "connections": connections})

    def _detect_module_type(self, name: str) -> str:
        """检测模块类型"""
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
