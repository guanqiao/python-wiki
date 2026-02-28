"""
部署架构图生成器
生成系统部署架构图，包括容器、节点、网络拓扑等
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from pywiki.generators.diagrams.base import BaseDiagramGenerator


class NodeType(str, Enum):
    """节点类型"""
    SERVER = "server"
    CONTAINER = "container"
    POD = "pod"
    LOAD_BALANCER = "load_balancer"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    STORAGE = "storage"
    CDN = "cdn"
    DNS = "dns"
    FIREWALL = "firewall"
    REVERSE_PROXY = "reverse_proxy"


class Environment(str, Enum):
    """部署环境"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DeploymentNode:
    """部署节点"""
    id: str
    name: str
    node_type: NodeType
    environment: Environment = Environment.PRODUCTION
    ip: str = ""
    port: Optional[int] = None
    description: str = ""
    technology: str = ""
    resources: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


@dataclass
class NetworkConnection:
    """网络连接"""
    source: str
    target: str
    protocol: str = "TCP"
    port: Optional[int] = None
    description: str = ""
    is_secure: bool = True


class DeploymentDiagramGenerator(BaseDiagramGenerator):
    """
    部署架构图生成器
    
    支持:
    - 多种节点类型（服务器、容器、Pod、数据库等）
    - 网络拓扑和连接关系
    - 多环境部署视图
    - Kubernetes 部署图
    - Docker Compose 部署图
    """

    NODE_COLORS = {
        NodeType.SERVER: "#607D8B",
        NodeType.CONTAINER: "#2196F3",
        NodeType.POD: "#9C27B0",
        NodeType.LOAD_BALANCER: "#E91E63",
        NodeType.DATABASE: "#4CAF50",
        NodeType.CACHE: "#FF9800",
        NodeType.QUEUE: "#9C27B0",
        NodeType.STORAGE: "#795548",
        NodeType.CDN: "#00BCD4",
        NodeType.DNS: "#3F51B5",
        NodeType.FIREWALL: "#F44336",
        NodeType.REVERSE_PROXY: "#FF5722",
    }

    NODE_SHAPES = {
        NodeType.SERVER: "[",
        NodeType.CONTAINER: "[",
        NodeType.POD: "[",
        NodeType.LOAD_BALANCER: "[",
        NodeType.DATABASE: "[(",
        NodeType.CACHE: "[(",
        NodeType.QUEUE: "{",
        NodeType.STORAGE: "[(",
        NodeType.CDN: "[",
        NodeType.DNS: "[",
        NodeType.FIREWALL: "[",
        NodeType.REVERSE_PROXY: "[",
    }

    def generate(
        self,
        data: dict,
        title: Optional[str] = None,
        environment: Optional[Environment] = None,
    ) -> str:
        """
        生成部署架构图
        
        Args:
            data: 包含以下字段:
                - nodes: 节点列表 [{"id": "", "name": "", "type": "", "environment": ""}]
                - connections: 连接列表 [{"source": "", "target": "", "protocol": "", "port": ""}]
                - clusters: 集群/分组列表 [{"name": "", "nodes": []}]
                - environment: 部署环境
            title: 图表标题
            environment: 部署环境过滤
        """
        nodes = data.get("nodes", [])
        connections = data.get("connections", [])
        clusters = data.get("clusters", [])
        env = environment or data.get("environment", Environment.PRODUCTION)

        lines = ["graph TB"]

        if title:
            lines.append(f"    %% {title}")
            lines.append(f"    %% Environment: {env.value if isinstance(env, Environment) else env}")

        lines.append("    Internet[/\"Internet\"]")
        lines.append("    style Internet fill:#E3F2FD,stroke:#1976D2")

        dns_nodes = [n for n in nodes if n.get("type") == "dns"]
        cdn_nodes = [n for n in nodes if n.get("type") == "cdn"]
        firewall_nodes = [n for n in nodes if n.get("type") == "firewall"]
        lb_nodes = [n for n in nodes if n.get("type") == "load_balancer"]
        proxy_nodes = [n for n in nodes if n.get("type") == "reverse_proxy"]
        server_nodes = [n for n in nodes if n.get("type") == "server"]
        container_nodes = [n for n in nodes if n.get("type") == "container"]
        pod_nodes = [n for n in nodes if n.get("type") == "pod"]
        db_nodes = [n for n in nodes if n.get("type") == "database"]
        cache_nodes = [n for n in nodes if n.get("type") == "cache"]
        queue_nodes = [n for n in nodes if n.get("type") == "queue"]
        storage_nodes = [n for n in nodes if n.get("type") == "storage"]

        prev_layer = "Internet"

        if dns_nodes:
            lines.append("    subgraph dns_layer[\"DNS Layer\"]")
            for dns in dns_nodes:
                dns_id = self.sanitize_id(dns.get("id", dns.get("name", "")))
                lines.append(f"        {dns_id}[\"{dns.get('name', 'DNS')}\"]")
                lines.append(f"        style {dns_id} fill:{self.NODE_COLORS[NodeType.DNS]},stroke:#303F9F,color:#fff")
            lines.append("    end")
            for dns in dns_nodes:
                dns_id = self.sanitize_id(dns.get("id", dns.get("name", "")))
                lines.append(f"    {prev_layer} -->|\"DNS Query\"| {dns_id}")
            prev_layer = "dns_layer"

        if cdn_nodes:
            lines.append("    subgraph cdn_layer[\"CDN Layer\"]")
            for cdn in cdn_nodes:
                cdn_id = self.sanitize_id(cdn.get("id", cdn.get("name", "")))
                lines.append(f"        {cdn_id}[\"{cdn.get('name', 'CDN')}\"]")
                lines.append(f"        style {cdn_id} fill:{self.NODE_COLORS[NodeType.CDN]},stroke:#0097A7,color:#fff")
            lines.append("    end")

        if firewall_nodes:
            lines.append("    subgraph firewall_layer[\"Firewall / Security\"]")
            for fw in firewall_nodes:
                fw_id = self.sanitize_id(fw.get("id", fw.get("name", "")))
                lines.append(f"        {fw_id}[\"{fw.get('name', 'Firewall')}\"]")
                lines.append(f"        style {fw_id} fill:{self.NODE_COLORS[NodeType.FIREWALL]},stroke:#D32F2F,color:#fff")
            lines.append("    end")
            for fw in firewall_nodes:
                fw_id = self.sanitize_id(fw.get("id", fw.get("name", "")))
                lines.append(f"    {prev_layer} -->|\"Filter\"| {fw_id}")
            prev_layer = "firewall_layer"

        if lb_nodes:
            lines.append("    subgraph lb_layer[\"Load Balancer\"]")
            for lb in lb_nodes:
                lb_id = self.sanitize_id(lb.get("id", lb.get("name", "")))
                lb_tech = lb.get("technology", "")
                label = lb.get("name", "Load Balancer")
                if lb_tech:
                    label += f"<br/>[{lb_tech}]"
                lines.append(f"        {lb_id}[\"{label}\"]")
                lines.append(f"        style {lb_id} fill:{self.NODE_COLORS[NodeType.LOAD_BALANCER]},stroke:#C2185B,color:#fff")
            lines.append("    end")
            for lb in lb_nodes:
                lb_id = self.sanitize_id(lb.get("id", lb.get("name", "")))
                lines.append(f"    {prev_layer} -->|\"Route\"| {lb_id}")
            prev_layer = "lb_layer"

        if proxy_nodes:
            lines.append("    subgraph proxy_layer[\"Reverse Proxy\"]")
            for proxy in proxy_nodes:
                proxy_id = self.sanitize_id(proxy.get("id", proxy.get("name", "")))
                proxy_tech = proxy.get("technology", "Nginx")
                lines.append(f"        {proxy_id}[\"{proxy.get('name', 'Proxy')}<br/>[{proxy_tech}]\"]")
                lines.append(f"        style {proxy_id} fill:{self.NODE_COLORS[NodeType.REVERSE_PROXY]},stroke:#E64A19,color:#fff")
            lines.append("    end")

        if clusters:
            for cluster in clusters:
                cluster_name = cluster.get("name", "Cluster")
                cluster_nodes = cluster.get("nodes", [])
                
                lines.append(f"    subgraph {self.sanitize_id(cluster_name)}[\"{cluster_name}\"]")
                
                for node_id in cluster_nodes:
                    node = next((n for n in nodes if n.get("id") == node_id or n.get("name") == node_id), None)
                    if node:
                        n_id = self.sanitize_id(node.get("id", node.get("name", "")))
                        n_name = node.get("name", "Node")
                        n_type = node.get("type", "server")
                        color = self.NODE_COLORS.get(NodeType(n_type), "#607D8B")
                        
                        lines.append(f"        {n_id}[\"{n_name}\"]")
                        lines.append(f"        style {n_id} fill:{color},stroke:{color[:-2]}AA,color:#fff")
                
                lines.append("    end")
        else:
            if server_nodes or container_nodes or pod_nodes:
                lines.append("    subgraph app_layer[\"Application Layer\"]")
                
                for server in server_nodes:
                    s_id = self.sanitize_id(server.get("id", server.get("name", "")))
                    lines.append(f"        {s_id}[\"{server.get('name', 'Server')}\"]")
                    lines.append(f"        style {s_id} fill:{self.NODE_COLORS[NodeType.SERVER]},stroke:#455A64,color:#fff")
                
                for container in container_nodes:
                    c_id = self.sanitize_id(container.get("id", container.get("name", "")))
                    c_tech = container.get("technology", "Docker")
                    lines.append(f"        {c_id}[\"{container.get('name', 'Container')}<br/>[{c_tech}]\"]")
                    lines.append(f"        style {c_id} fill:{self.NODE_COLORS[NodeType.CONTAINER]},stroke:#1976D2,color:#fff")
                
                for pod in pod_nodes:
                    p_id = self.sanitize_id(pod.get("id", pod.get("name", "")))
                    lines.append(f"        {p_id}[\"{pod.get('name', 'Pod')}\"]")
                    lines.append(f"        style {p_id} fill:{self.NODE_COLORS[NodeType.POD]},stroke:#7B1FA2,color:#fff")
                
                lines.append("    end")

        if db_nodes:
            lines.append("    subgraph db_layer[\"Database Layer\"]")
            for db in db_nodes:
                db_id = self.sanitize_id(db.get("id", db.get("name", "")))
                db_tech = db.get("technology", "PostgreSQL")
                lines.append(f"        {db_id}[(\"{db.get('name', 'Database')}<br/>[{db_tech}]\")]")
                lines.append(f"        style {db_id} fill:{self.NODE_COLORS[NodeType.DATABASE]},stroke:#388E3C,color:#fff")
            lines.append("    end")

        if cache_nodes:
            lines.append("    subgraph cache_layer[\"Cache Layer\"]")
            for cache in cache_nodes:
                cache_id = self.sanitize_id(cache.get("id", cache.get("name", "")))
                cache_tech = cache.get("technology", "Redis")
                lines.append(f"        {cache_id}[(\"{cache.get('name', 'Cache')}<br/>[{cache_tech}]\")]")
                lines.append(f"        style {cache_id} fill:{self.NODE_COLORS[NodeType.CACHE]},stroke:#F57C00,color:#fff")
            lines.append("    end")

        if queue_nodes:
            lines.append("    subgraph queue_layer[\"Message Queue\"]")
            for queue in queue_nodes:
                q_id = self.sanitize_id(queue.get("id", queue.get("name", "")))
                q_tech = queue.get("technology", "Kafka")
                lines.append(f"        {q_id}{{\"{queue.get('name', 'Queue')}<br/>[{q_tech}]\"}}")
                lines.append(f"        style {q_id} fill:{self.NODE_COLORS[NodeType.QUEUE]},stroke:#7B1FA2,color:#fff")
            lines.append("    end")

        if storage_nodes:
            lines.append("    subgraph storage_layer[\"Storage\"]")
            for storage in storage_nodes:
                s_id = self.sanitize_id(storage.get("id", storage.get("name", "")))
                lines.append(f"        {s_id}[(\"{storage.get('name', 'Storage')}\")]")
                lines.append(f"        style {s_id} fill:{self.NODE_COLORS[NodeType.STORAGE]},stroke:#5D4037,color:#fff")
            lines.append("    end")

        for conn in connections:
            source = self.sanitize_id(conn.get("source", ""))
            target = self.sanitize_id(conn.get("target", ""))
            protocol = conn.get("protocol", "TCP")
            port = conn.get("port")
            desc = conn.get("description", "")
            
            if source and target:
                label = desc
                if port:
                    label = f"{protocol}:{port}" if not desc else f"{desc} ({protocol}:{port})"
                elif protocol and not desc:
                    label = protocol
                
                if label:
                    lines.append(f"    {source} -->|\"{label}\"| {target}")
                else:
                    lines.append(f"    {source} --> {target}")

        return self.wrap_mermaid("\n".join(lines))

    def generate_kubernetes(
        self,
        k8s_config: dict,
        title: Optional[str] = None,
    ) -> str:
        """
        生成 Kubernetes 部署架构图
        
        Args:
            k8s_config: Kubernetes 配置，包含:
                - namespace: 命名空间
                - deployments: 部署列表
                - services: 服务列表
                - ingresses: Ingress 列表
                - configmaps: ConfigMap 列表
                - secrets: Secret 列表
                - pvcs: PersistentVolumeClaim 列表
            title: 图表标题
        """
        lines = ["graph TB"]

        if title:
            lines.append(f"    %% {title}")
            lines.append("    %% Kubernetes Deployment")

        namespace = k8s_config.get("namespace", "default")
        deployments = k8s_config.get("deployments", [])
        services = k8s_config.get("services", [])
        ingresses = k8s_config.get("ingresses", [])
        configmaps = k8s_config.get("configmaps", [])
        secrets = k8s_config.get("secrets", [])
        pvcs = k8s_config.get("pvcs", [])

        lines.append("    User[/\"User\"]")
        lines.append("    style User fill:#1565C0,stroke:#0D47A1,color:#fff")

        if ingresses:
            lines.append(f"    subgraph ingress_layer[\"Ingress\"]")
            for ing in ingresses:
                ing_id = self.sanitize_id(ing.get("name", "ingress"))
                ing_host = ing.get("host", "")
                lines.append(f"        {ing_id}[\"{ing.get('name', 'Ingress')}<br/>{ing_host}\"]")
                lines.append(f"        style {ing_id} fill:#E91E63,stroke:#C2185B,color:#fff")
            lines.append("    end")
            lines.append("    User --> ingress_layer")

        lines.append(f"    subgraph ns_{namespace}[\"Namespace: {namespace}\"]")

        if services:
            lines.append("        subgraph services[\"Services\"]")
            for svc in services:
                svc_id = self.sanitize_id(svc.get("name", "service"))
                svc_type = svc.get("type", "ClusterIP")
                svc_port = svc.get("port", "")
                label = svc.get("name", "Service")
                if svc_port:
                    label += f":{svc_port}"
                lines.append(f"            {svc_id}[\"{label}<br/>({svc_type})\"]")
                lines.append(f"            style {svc_id} fill:#2196F3,stroke:#1976D2,color:#fff")
            lines.append("        end")

        if deployments:
            lines.append("        subgraph pods[\"Deployments / Pods\"]")
            for dep in deployments:
                dep_id = self.sanitize_id(dep.get("name", "deployment"))
                replicas = dep.get("replicas", 1)
                image = dep.get("image", "")
                label = dep.get("name", "Deployment")
                if replicas > 1:
                    label += f" (x{replicas})"
                lines.append(f"            {dep_id}[\"{label}<br/><small>{image}</small>\"]")
                lines.append(f"            style {dep_id} fill:#9C27B0,stroke:#7B1FA2,color:#fff")
            lines.append("        end")

        if configmaps:
            lines.append("        subgraph configs[\"ConfigMaps\"]")
            for cm in configmaps:
                cm_id = self.sanitize_id(cm.get("name", "configmap"))
                lines.append(f"            {cm_id}[[\"{cm.get('name', 'ConfigMap')}\"]]")
                lines.append(f"            style {cm_id} fill:#607D8B,stroke:#455A64,color:#fff")
            lines.append("        end")

        if secrets:
            lines.append("        subgraph secrets_layer[\"Secrets\"]")
            for secret in secrets:
                s_id = self.sanitize_id(secret.get("name", "secret"))
                lines.append(f"            {s_id}[[\"{secret.get('name', 'Secret')}\"]]")
                lines.append(f"            style {s_id} fill:#F44336,stroke:#D32F2F,color:#fff")
            lines.append("        end")

        if pvcs:
            lines.append("        subgraph storage[\"PersistentVolumes\"]")
            for pvc in pvcs:
                pvc_id = self.sanitize_id(pvc.get("name", "pvc"))
                size = pvc.get("size", "")
                lines.append(f"            {pvc_id}[(\"{pvc.get('name', 'PVC')}<br/>{size}\")]")
                lines.append(f"            style {pvc_id} fill:#4CAF50,stroke:#388E3C,color:#fff")
            lines.append("        end")

        lines.append("    end")

        for svc in services:
            svc_id = self.sanitize_id(svc.get("name", "service"))
            svc_selector = svc.get("selector", "")
            if svc_selector:
                dep = next((d for d in deployments if svc_selector in d.get("name", "")), None)
                if dep:
                    dep_id = self.sanitize_id(dep.get("name", "deployment"))
                    lines.append(f"    {svc_id} --> {dep_id}")

        for ing in ingresses:
            ing_id = self.sanitize_id(ing.get("name", "ingress"))
            backend = ing.get("backend", "")
            if backend:
                svc_id = self.sanitize_id(backend)
                lines.append(f"    {ing_id} --> {svc_id}")

        return self.wrap_mermaid("\n".join(lines))

    def generate_docker_compose(
        self,
        compose_config: dict,
        title: Optional[str] = None,
    ) -> str:
        """
        生成 Docker Compose 部署架构图
        
        Args:
            compose_config: Docker Compose 配置
            title: 图表标题
        """
        lines = ["graph TB"]

        if title:
            lines.append(f"    %% {title}")
            lines.append("    %% Docker Compose Deployment")

        services = compose_config.get("services", [])
        networks = compose_config.get("networks", [])
        volumes = compose_config.get("volumes", [])

        lines.append("    subgraph docker_host[\"Docker Host\"]")

        if services:
            for svc in services:
                svc_id = self.sanitize_id(svc.get("name", "service"))
                svc_image = svc.get("image", "")
                svc_ports = svc.get("ports", [])
                svc_depends = svc.get("depends_on", [])
                
                ports_str = ", ".join(svc_ports) if svc_ports else ""
                label = svc.get("name", "Service")
                if svc_image:
                    label += f"<br/><small>{svc_image}</small>"
                if ports_str:
                    label += f"<br/>Ports: {ports_str}"
                
                lines.append(f"        {svc_id}[\"{label}\"]")
                
                svc_type = self._detect_service_type_from_image(svc_image)
                color = self.NODE_COLORS.get(svc_type, "#2196F3")
                lines.append(f"        style {svc_id} fill:{color},stroke:{color[:-2]}AA,color:#fff")

        lines.append("    end")

        if volumes:
            lines.append("    subgraph vol_layer[\"Volumes\"]")
            for vol in volumes:
                vol_id = self.sanitize_id(vol.get("name", "volume"))
                lines.append(f"        {vol_id}[(\"{vol.get('name', 'Volume')}\")]")
                lines.append(f"        style {vol_id} fill:#795548,stroke:#5D4037,color:#fff")
            lines.append("    end")

        for svc in services:
            svc_id = self.sanitize_id(svc.get("name", "service"))
            svc_depends = svc.get("depends_on", [])
            svc_volumes = svc.get("volumes", [])
            
            for dep in svc_depends:
                dep_id = self.sanitize_id(dep)
                lines.append(f"    {svc_id} -->|\"depends\"| {dep_id}")
            
            for vol_mount in svc_volumes:
                if isinstance(vol_mount, str) and ":" in vol_mount:
                    vol_name = vol_mount.split(":")[0]
                    vol_id = self.sanitize_id(vol_name)
                    lines.append(f"    {svc_id} -->|\"mount\"| {vol_id}")

        return self.wrap_mermaid("\n".join(lines))

    def generate_cloud_architecture(
        self,
        cloud_config: dict,
        title: Optional[str] = None,
    ) -> str:
        """
        生成云架构部署图
        
        Args:
            cloud_config: 云配置，包含:
                - provider: 云提供商 (AWS/GCP/Azure)
                - regions: 区域配置
                - vpcs: VPC 配置
                - resources: 资源列表
            title: 图表标题
        """
        lines = ["graph TB"]

        if title:
            lines.append(f"    %% {title}")

        provider = cloud_config.get("provider", "AWS")
        regions = cloud_config.get("regions", [])
        resources = cloud_config.get("resources", [])

        lines.append("    Internet[/\"Internet\"]")
        lines.append("    style Internet fill:#E3F2FD,stroke:#1976D2")

        provider_colors = {
            "AWS": "#FF9900",
            "GCP": "#4285F4",
            "Azure": "#0089D6",
        }
        provider_color = provider_colors.get(provider, "#607D8B")

        lines.append(f"    subgraph cloud[\"{provider} Cloud\"]")
        lines.append(f"    style cloud fill:{provider_color}20,stroke:{provider_color}")

        for region in regions:
            region_name = region.get("name", "Region")
            vpcs = region.get("vpcs", [])
            
            lines.append(f"        subgraph {self.sanitize_id(region_name)}[\"{region_name}\"]")
            
            for vpc in vpcs:
                vpc_name = vpc.get("name", "VPC")
                vpc_cidr = vpc.get("cidr", "")
                subnets = vpc.get("subnets", [])
                
                lines.append(f"            subgraph {self.sanitize_id(vpc_name)}[\"{vpc_name}<br/>{vpc_cidr}\"]")
                
                for subnet in subnets:
                    subnet_name = subnet.get("name", "Subnet")
                    subnet_resources = subnet.get("resources", [])
                    
                    lines.append(f"                subgraph {self.sanitize_id(subnet_name)}[\"{subnet_name}\"]")
                    
                    for res_id in subnet_resources:
                        res = next((r for r in resources if r.get("id") == res_id), None)
                        if res:
                            r_id = self.sanitize_id(res.get("id", res.get("name", "")))
                            r_name = res.get("name", "Resource")
                            r_type = res.get("type", "instance")
                            lines.append(f"                    {r_id}[\"{r_name}<br/>({r_type})\"]")
                    
                    lines.append("                end")
                
                lines.append("            end")
            
            lines.append("        end")

        lines.append("    end")

        lines.append("    Internet --> cloud")

        return self.wrap_mermaid("\n".join(lines))

    def _detect_service_type_from_image(self, image: str) -> NodeType:
        """从镜像名称检测服务类型"""
        if not image:
            return NodeType.CONTAINER
        
        image_lower = image.lower()
        
        if any(kw in image_lower for kw in ["nginx", "apache", "traefik", "caddy"]):
            return NodeType.REVERSE_PROXY
        elif any(kw in image_lower for kw in ["mysql", "postgres", "mongo", "redis", "mariadb"]):
            return NodeType.DATABASE
        elif any(kw in image_lower for kw in ["redis", "memcached"]):
            return NodeType.CACHE
        elif any(kw in image_lower for kw in ["kafka", "rabbitmq", "activemq"]):
            return NodeType.QUEUE
        else:
            return NodeType.CONTAINER
