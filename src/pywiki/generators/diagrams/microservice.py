"""
微服务架构图生成器
生成微服务架构风格的系统架构图
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from pywiki.generators.diagrams.base import BaseDiagramGenerator


class ServiceType(str, Enum):
    """服务类型"""
    API_GATEWAY = "api_gateway"
    SERVICE = "service"
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    SERVICE_REGISTRY = "service_registry"
    CONFIG_SERVER = "config_server"
    LOAD_BALANCER = "load_balancer"
    EXTERNAL = "external"


class CommunicationPattern(str, Enum):
    """通信模式"""
    SYNC_HTTP = "sync_http"
    SYNC_GRPC = "sync_grpc"
    ASYNC_MESSAGE = "async_message"
    EVENT = "event"


@dataclass
class MicroserviceNode:
    """微服务节点"""
    id: str
    name: str
    service_type: ServiceType
    description: str = ""
    technology: str = ""
    port: Optional[int] = None
    health_check: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class ServiceConnection:
    """服务连接"""
    source: str
    target: str
    pattern: CommunicationPattern = CommunicationPattern.SYNC_HTTP
    description: str = ""
    protocol: str = ""


class MicroserviceDiagramGenerator(BaseDiagramGenerator):
    """
    微服务架构图生成器
    
    支持:
    - API 网关、服务、数据库、消息队列等组件
    - 同步/异步通信模式可视化
    - 服务发现和配置中心
    - 自动从项目结构推断微服务架构
    """

    SERVICE_COLORS = {
        ServiceType.API_GATEWAY: "#E91E63",
        ServiceType.SERVICE: "#2196F3",
        ServiceType.DATABASE: "#4CAF50",
        ServiceType.CACHE: "#FF9800",
        ServiceType.MESSAGE_QUEUE: "#9C27B0",
        ServiceType.SERVICE_REGISTRY: "#00BCD4",
        ServiceType.CONFIG_SERVER: "#795548",
        ServiceType.LOAD_BALANCER: "#607D8B",
        ServiceType.EXTERNAL: "#9E9E9E",
    }

    SERVICE_SHAPES = {
        ServiceType.API_GATEWAY: "[",
        ServiceType.SERVICE: "[",
        ServiceType.DATABASE: "[(",
        ServiceType.CACHE: "[(",
        ServiceType.MESSAGE_QUEUE: "{",
        ServiceType.SERVICE_REGISTRY: "[",
        ServiceType.CONFIG_SERVER: "[",
        ServiceType.LOAD_BALANCER: "[",
        ServiceType.EXTERNAL: "[",
    }

    def generate(
        self,
        data: dict,
        title: Optional[str] = None,
    ) -> str:
        """
        生成微服务架构图
        
        Args:
            data: 包含以下字段:
                - services: 服务列表 [{"id": "", "name": "", "type": "", "description": ""}]
                - connections: 连接列表 [{"source": "", "target": "", "pattern": "", "description": ""}]
                - gateways: API 网关列表
                - databases: 数据库列表
                - queues: 消息队列列表
                - external_systems: 外部系统列表
            title: 图表标题
        """
        services = data.get("services", [])
        connections = data.get("connections", [])
        gateways = data.get("gateways", [])
        databases = data.get("databases", [])
        queues = data.get("queues", [])
        caches = data.get("caches", [])
        external_systems = data.get("external_systems", [])
        service_registry = data.get("service_registry")
        config_server = data.get("config_server")

        lines = ["graph TB"]

        if title:
            lines.append(f"    %% {title}")
            lines.append("    %% Microservice Architecture")

        lines.append("    Client[/\"Client\"]")
        lines.append("    style Client fill:#1565C0,stroke:#0D47A1,color:#fff")

        if gateways:
            lines.append("    subgraph gateway_layer[\"API Gateway Layer\"]")
            for gw in gateways:
                gw_id = self.sanitize_id(gw.get("id", gw.get("name", "")))
                gw_name = gw.get("name", "API Gateway")
                gw_tech = gw.get("technology", "")
                label = gw_name
                if gw_tech:
                    label += f"<br/>[{gw_tech}]"
                lines.append(f"        {gw_id}[\"{label}\"]")
                lines.append(f"        style {gw_id} fill:{self.SERVICE_COLORS[ServiceType.API_GATEWAY]},stroke:#C2185B,color:#fff")
            lines.append("    end")

            for gw in gateways:
                gw_id = self.sanitize_id(gw.get("id", gw.get("name", "")))
                lines.append(f"    Client -->|\"HTTP/HTTPS\"| {gw_id}")

        if service_registry:
            sr_id = self.sanitize_id(service_registry.get("id", "service_registry"))
            sr_name = service_registry.get("name", "Service Registry")
            sr_tech = service_registry.get("technology", "Eureka/Consul")
            lines.append(f"    {sr_id}[\"{sr_name}<br/>[{sr_tech}]\"]")
            lines.append(f"    style {sr_id} fill:{self.SERVICE_COLORS[ServiceType.SERVICE_REGISTRY]},stroke:#0097A7,color:#fff")

        if config_server:
            cs_id = self.sanitize_id(config_server.get("id", "config_server"))
            cs_name = config_server.get("name", "Config Server")
            cs_tech = config_server.get("technology", "Spring Cloud Config")
            lines.append(f"    {cs_id}[\"{cs_name}<br/>[{cs_tech}]\"]")
            lines.append(f"    style {cs_id} fill:{self.SERVICE_COLORS[ServiceType.CONFIG_SERVER]},stroke:#5D4037,color:#fff")

        if services:
            lines.append("    subgraph services_layer[\"Microservices\"]")
            for svc in services:
                svc_id = self.sanitize_id(svc.get("id", svc.get("name", "")))
                svc_name = svc.get("name", "Service")
                svc_desc = svc.get("description", "")
                svc_tech = svc.get("technology", "")
                
                label = svc_name
                if svc_tech:
                    label += f"<br/>[{svc_tech}]"
                if svc_desc:
                    label += f"<br/><small>{svc_desc[:30]}</small>"
                
                lines.append(f"        {svc_id}[\"{label}\"]")
                lines.append(f"        style {svc_id} fill:{self.SERVICE_COLORS[ServiceType.SERVICE]},stroke:#1976D2,color:#fff")
            lines.append("    end")

        if queues:
            lines.append("    subgraph messaging_layer[\"Message Queue\"]")
            for q in queues:
                q_id = self.sanitize_id(q.get("id", q.get("name", "")))
                q_name = q.get("name", "Message Queue")
                q_tech = q.get("technology", "Kafka/RabbitMQ")
                lines.append(f"        {q_id}{{\"{q_name}<br/>[{q_tech}]\"}}")
                lines.append(f"        style {q_id} fill:{self.SERVICE_COLORS[ServiceType.MESSAGE_QUEUE]},stroke:#7B1FA2,color:#fff")
            lines.append("    end")

        if databases:
            lines.append("    subgraph data_layer[\"Databases\"]")
            for db in databases:
                db_id = self.sanitize_id(db.get("id", db.get("name", "")))
                db_name = db.get("name", "Database")
                db_tech = db.get("technology", "PostgreSQL/MySQL")
                lines.append(f"        {db_id}[(\"{db_name}<br/>[{db_tech}]\")]")
                lines.append(f"        style {db_id} fill:{self.SERVICE_COLORS[ServiceType.DATABASE]},stroke:#388E3C,color:#fff")
            lines.append("    end")

        if caches:
            lines.append("    subgraph cache_layer[\"Cache Layer\"]")
            for cache in caches:
                cache_id = self.sanitize_id(cache.get("id", cache.get("name", "")))
                cache_name = cache.get("name", "Cache")
                cache_tech = cache.get("technology", "Redis")
                lines.append(f"        {cache_id}[(\"{cache_name}<br/>[{cache_tech}]\")]")
                lines.append(f"        style {cache_id} fill:{self.SERVICE_COLORS[ServiceType.CACHE]},stroke:#F57C00,color:#fff")
            lines.append("    end")

        if external_systems:
            lines.append("    subgraph external_layer[\"External Systems\"]")
            for ext in external_systems:
                ext_id = self.sanitize_id(ext.get("id", ext.get("name", "")))
                ext_name = ext.get("name", "External")
                lines.append(f"        {ext_id}[\"{ext_name}\"]")
                lines.append(f"        style {ext_id} fill:{self.SERVICE_COLORS[ServiceType.EXTERNAL]},stroke:#757575,color:#fff")
            lines.append("    end")

        for conn in connections:
            source = self.sanitize_id(conn.get("source", ""))
            target = self.sanitize_id(conn.get("target", ""))
            pattern = conn.get("pattern", "sync_http")
            desc = conn.get("description", "")
            
            if source and target:
                arrow = self._get_arrow_for_pattern(pattern)
                if desc:
                    lines.append(f"    {source} {arrow}|\"{desc}\"| {target}")
                else:
                    label = self._get_pattern_label(pattern)
                    if label:
                        lines.append(f"    {source} {arrow}|\"{label}\"| {target}")
                    else:
                        lines.append(f"    {source} {arrow} {target}")

        return self.wrap_mermaid("\n".join(lines))

    def generate_from_project_structure(
        self,
        project_info: dict,
        title: Optional[str] = None,
    ) -> str:
        """
        从项目结构自动生成微服务架构图
        
        Args:
            project_info: 项目信息，包含:
                - name: 项目名称
                - services: 服务模块列表
                - databases: 数据库配置
                - message_queues: 消息队列配置
            title: 图表标题
        """
        services = []
        connections = []
        gateways = []
        databases = []
        queues = []
        caches = []
        external_systems = []

        service_modules = project_info.get("services", [])
        
        for svc in service_modules:
            svc_name = svc.get("name", "")
            svc_type = self._detect_service_type(svc_name)
            
            node = {
                "id": self.sanitize_id(svc_name),
                "name": svc_name,
                "type": svc_type.value if isinstance(svc_type, ServiceType) else svc_type,
                "description": svc.get("description", ""),
                "technology": svc.get("technology", ""),
            }

            if svc_type == ServiceType.API_GATEWAY:
                gateways.append(node)
            elif svc_type == ServiceType.SERVICE:
                services.append(node)
            elif svc_type == ServiceType.DATABASE:
                databases.append(node)
            elif svc_type == ServiceType.CACHE:
                caches.append(node)
            elif svc_type == ServiceType.MESSAGE_QUEUE:
                queues.append(node)
            elif svc_type == ServiceType.EXTERNAL:
                external_systems.append(node)
            else:
                services.append(node)

            if svc.get("dependencies"):
                for dep in svc.get("dependencies", []):
                    connections.append({
                        "source": self.sanitize_id(svc_name),
                        "target": self.sanitize_id(dep),
                        "pattern": "sync_http",
                    })

        if project_info.get("databases"):
            for db in project_info.get("databases", []):
                databases.append({
                    "id": self.sanitize_id(db.get("name", "db")),
                    "name": db.get("name", "Database"),
                    "technology": db.get("technology", ""),
                })

        if project_info.get("message_queues"):
            for mq in project_info.get("message_queues", []):
                queues.append({
                    "id": self.sanitize_id(mq.get("name", "queue")),
                    "name": mq.get("name", "Message Queue"),
                    "technology": mq.get("technology", ""),
                })

        data = {
            "services": services,
            "connections": connections,
            "gateways": gateways,
            "databases": databases,
            "queues": queues,
            "caches": caches,
            "external_systems": external_systems,
            "service_registry": project_info.get("service_registry"),
            "config_server": project_info.get("config_server"),
        }

        return self.generate(data, title or f"{project_info.get('name', 'Project')} Microservice Architecture")

    def generate_service_mesh(
        self,
        services: list[dict],
        mesh_config: Optional[dict] = None,
        title: Optional[str] = None,
    ) -> str:
        """
        生成服务网格架构图
        
        Args:
            services: 服务列表
            mesh_config: 服务网格配置（如 Istio）
            title: 图表标题
        """
        lines = ["graph TB"]

        if title:
            lines.append(f"    %% {title}")
            lines.append("    %% Service Mesh Architecture")

        lines.append("    Client[/\"Client\"]")

        mesh_name = mesh_config.get("name", "Istio") if mesh_config else "Istio"
        
        lines.append(f"    subgraph mesh[\"Service Mesh ({mesh_name})\"]")
        lines.append("    style mesh fill:#E8EAF6,stroke:#3F51B5,stroke-width:2px")

        for svc in services:
            svc_id = self.sanitize_id(svc.get("id", svc.get("name", "")))
            svc_name = svc.get("name", "Service")
            
            lines.append(f"        subgraph {svc_id}_pod[\"{svc_name}\"]")
            lines.append(f"        {svc_id}[\"App\"]")
            lines.append(f"        {svc_id}_proxy[\"Sidecar Proxy\"]")
            lines.append(f"        {svc_id} <--> {svc_id}_proxy")
            lines.append("        end")
            lines.append(f"        style {svc_id} fill:#2196F3,stroke:#1976D2,color:#fff")
            lines.append(f"        style {svc_id}_proxy fill:#9C27B0,stroke:#7B1FA2,color:#fff")

        lines.append("    end")

        lines.append("    Client --> mesh")

        for i, svc in enumerate(services):
            svc_id = self.sanitize_id(svc.get("id", svc.get("name", "")))
            if i == 0:
                lines.append(f"    Client -->|\"via Gateway\"| {svc_id}_proxy")

        return self.wrap_mermaid("\n".join(lines))

    def generate_event_sourcing(
        self,
        services: list[dict],
        event_store: dict,
        title: Optional[str] = None,
    ) -> str:
        """
        生成事件溯源架构图
        
        Args:
            services: 服务列表
            event_store: 事件存储配置
            title: 图表标题
        """
        lines = ["graph LR"]

        if title:
            lines.append(f"    %% {title}")
            lines.append("    %% Event Sourcing Architecture")

        lines.append("    Client[/\"Client\"]")

        es_id = self.sanitize_id(event_store.get("id", "event_store"))
        es_name = event_store.get("name", "Event Store")
        es_tech = event_store.get("technology", "Kafka/EventStore")
        
        lines.append(f"    {es_id}[(\"{es_name}<br/>[{es_tech}]\")]")
        lines.append(f"    style {es_id} fill:#9C27B0,stroke:#7B1FA2,color:#fff")

        command_services = []
        query_services = []

        for svc in services:
            svc_name = svc.get("name", "").lower()
            if "command" in svc_name or "write" in svc_name:
                command_services.append(svc)
            elif "query" in svc_name or "read" in svc_name:
                query_services.append(svc)
            else:
                command_services.append(svc)

        if command_services:
            lines.append("    subgraph cmd_side[\"Command Side\"]")
            for svc in command_services:
                svc_id = self.sanitize_id(svc.get("id", svc.get("name", "")))
                lines.append(f"        {svc_id}[\"{svc.get('name', 'Service')}\"]")
                lines.append(f"        style {svc_id} fill:#E91E63,stroke:#C2185B,color:#fff")
            lines.append("    end")

        if query_services:
            lines.append("    subgraph query_side[\"Query Side\"]")
            for svc in query_services:
                svc_id = self.sanitize_id(svc.get("id", svc.get("name", "")))
                lines.append(f"        {svc_id}[\"{svc.get('name', 'Service')}\"]")
                lines.append(f"        style {svc_id} fill:#4CAF50,stroke:#388E3C,color:#fff")
            lines.append("    end")

        lines.append("    Client --> cmd_side")
        lines.append("    Client --> query_side")

        for svc in command_services:
            svc_id = self.sanitize_id(svc.get("id", svc.get("name", "")))
            lines.append(f"    {svc_id} -->|\"emit events\"| {es_id}")

        for svc in query_services:
            svc_id = self.sanitize_id(svc.get("id", svc.get("name", "")))
            lines.append(f"    {es_id} -->|\"subscribe\"| {svc_id}")

        return self.wrap_mermaid("\n".join(lines))

    def _detect_service_type(self, name: str) -> ServiceType:
        """检测服务类型"""
        name_lower = name.lower()
        
        if any(kw in name_lower for kw in ["gateway", "api-gateway", "apigateway"]):
            return ServiceType.API_GATEWAY
        elif any(kw in name_lower for kw in ["db", "database", "mysql", "postgres", "mongo"]):
            return ServiceType.DATABASE
        elif any(kw in name_lower for kw in ["cache", "redis", "memcached"]):
            return ServiceType.CACHE
        elif any(kw in name_lower for kw in ["queue", "kafka", "rabbitmq", "mq", "message"]):
            return ServiceType.MESSAGE_QUEUE
        elif any(kw in name_lower for kw in ["registry", "eureka", "consul", "discovery"]):
            return ServiceType.SERVICE_REGISTRY
        elif any(kw in name_lower for kw in ["config", "configuration"]):
            return ServiceType.CONFIG_SERVER
        elif any(kw in name_lower for kw in ["loadbalancer", "load-balancer", "lb"]):
            return ServiceType.LOAD_BALANCER
        elif any(kw in name_lower for kw in ["external", "third-party", "thirdparty"]):
            return ServiceType.EXTERNAL
        else:
            return ServiceType.SERVICE

    def _get_arrow_for_pattern(self, pattern: str) -> str:
        """获取通信模式对应的箭头"""
        arrows = {
            "sync_http": "-->",
            "sync_grpc": "==>",
            "async_message": "-.->",
            "event": "-..->",
        }
        return arrows.get(pattern, "-->")

    def _get_pattern_label(self, pattern: str) -> str:
        """获取通信模式标签"""
        labels = {
            "sync_http": "HTTP",
            "sync_grpc": "gRPC",
            "async_message": "Message",
            "event": "Event",
        }
        return labels.get(pattern, "")
