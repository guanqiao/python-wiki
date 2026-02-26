"""
C4 架构模型图表生成器
支持 System Context、Container、Component、Code 四层架构图
"""

from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from pywiki.generators.diagrams.base import BaseDiagramGenerator


class C4Level(str, Enum):
    """C4 模型层级"""
    CONTEXT = "context"      # 系统上下文
    CONTAINER = "container"  # 容器
    COMPONENT = "component"  # 组件
    CODE = "code"           # 代码


@dataclass
class C4Person:
    """C4 人员/角色"""
    id: str
    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class C4System:
    """C4 系统"""
    id: str
    name: str
    description: str = ""
    system_type: str = "system"  # system, external_system
    tags: list[str] = field(default_factory=list)


@dataclass
class C4Container:
    """C4 容器"""
    id: str
    name: str
    description: str = ""
    container_type: str = "web"  # web, api, database, queue, mobile, spa
    technology: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class C4Component:
    """C4 组件"""
    id: str
    name: str
    description: str = ""
    component_type: str = "service"  # service, controller, repository, entity
    technology: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class C4Relationship:
    """C4 关系"""
    source: str
    target: str
    description: str = ""
    technology: str = ""


class C4ContextDiagramGenerator(BaseDiagramGenerator):
    """
    C4 系统上下文图生成器
    展示系统与外部用户、系统的关系
    """

    def generate(
        self,
        data: dict,
        title: Optional[str] = None
    ) -> str:
        """
        生成 C4 上下文图
        
        Args:
            data: 包含以下字段:
                - system: 当前系统信息 {"id": "", "name": "", "description": ""}
                - users: 用户/角色列表 [{"id": "", "name": "", "description": ""}]
                - external_systems: 外部系统列表 [{"id": "", "name": "", "description": ""}]
                - relationships: 关系列表 [{"source": "", "target": "", "description": ""}]
            title: 图表标题
        """
        system = data.get("system", {})
        users = data.get("users", [])
        external_systems = data.get("external_systems", [])
        relationships = data.get("relationships", [])

        lines = ["graph TB"]

        if title:
            lines.append(f"    %% {title}")
            lines.append(f"    %% C4 Context Diagram")

        # 添加当前系统（核心）
        sys_id = self.sanitize_id(system.get("id", "System"))
        sys_name = system.get("name", "System")
        sys_desc = system.get("description", "")
        lines.append(f"    {sys_id}[({sys_name}<br/><small>{sys_desc}</small>)]")
        lines.append(f"    style {sys_id} fill:#1168bd,stroke:#0b4884,color:#fff")

        # 添加用户/角色
        for user in users:
            user_id = self.sanitize_id(user.get("id", ""))
            user_name = user.get("name", "")
            user_desc = user.get("description", "")
            if user_id and user_name:
                lines.append(f"    {user_id}[/\"{user_name}<br/><small>{user_desc}</small>\"/]")
                lines.append(f"    style {user_id} fill:#08427b,stroke:#052e56,color:#fff")

        # 添加外部系统
        for ext in external_systems:
            ext_id = self.sanitize_id(ext.get("id", ""))
            ext_name = ext.get("name", "")
            ext_desc = ext.get("description", "")
            if ext_id and ext_name:
                lines.append(f"    {ext_id}[({ext_name}<br/><small>{ext_desc}</small>)]")
                lines.append(f"    style {ext_id} fill:#999,stroke:#666,color:#fff")

        # 添加关系
        for rel in relationships:
            source = self.sanitize_id(rel.get("source", ""))
            target = self.sanitize_id(rel.get("target", ""))
            desc = rel.get("description", "")
            if source and target:
                if desc:
                    lines.append(f"    {source} -->|\"{desc}\"| {target}")
                else:
                    lines.append(f"    {source} --> {target}")

        return self.wrap_mermaid("\n".join(lines))

    def generate_from_project(
        self,
        project_name: str,
        description: str = "",
        users: Optional[list[dict]] = None,
        external_deps: Optional[list[dict]] = None,
    ) -> str:
        """从项目信息自动生成上下文图"""
        data = {
            "system": {
                "id": "main_system",
                "name": project_name,
                "description": description or "Main Application",
            },
            "users": users or [
                {"id": "user", "name": "User", "description": "End User"},
            ],
            "external_systems": external_deps or [],
            "relationships": [],
        }

        # 自动构建关系
        for user in data["users"]:
            data["relationships"].append({
                "source": user["id"],
                "target": "main_system",
                "description": "Uses",
            })

        for ext in data["external_systems"]:
            data["relationships"].append({
                "source": "main_system",
                "target": ext["id"],
                "description": "Calls",
            })

        return self.generate(data, f"{project_name} - System Context")


class C4ContainerDiagramGenerator(BaseDiagramGenerator):
    """
    C4 容器图生成器
    展示系统内部的应用/服务/数据库等容器
    """

    CONTAINER_STYLES = {
        "web": {"shape": "[", "fill": "#438dd5", "stroke": "#2e6299"},
        "api": {"shape": "[", "fill": "#438dd5", "stroke": "#2e6299"},
        "spa": {"shape": "[", "fill": "#438dd5", "stroke": "#2e6299"},
        "mobile": {"shape": "[", "fill": "#438dd5", "stroke": "#2e6299"},
        "database": {"shape": "[(", "fill": "#438dd5", "stroke": "#2e6299"},
        "queue": {"shape": "{", "fill": "#438dd5", "stroke": "#2e6299"},
        "external": {"shape": "[", "fill": "#999", "stroke": "#666"},
    }

    def generate(
        self,
        data: dict,
        title: Optional[str] = None
    ) -> str:
        """
        生成 C4 容器图
        
        Args:
            data: 包含以下字段:
                - system_name: 系统名称
                - containers: 容器列表 [{"id": "", "name": "", "description": "", "type": "", "technology": ""}]
                - external_systems: 外部系统列表
                - relationships: 关系列表 [{"source": "", "target": "", "description": "", "technology": ""}]
        """
        system_name = data.get("system_name", "System")
        containers = data.get("containers", [])
        external_systems = data.get("external_systems", [])
        relationships = data.get("relationships", [])

        lines = ["graph TB"]

        if title:
            lines.append(f"    %% {title}")
            lines.append(f"    %% C4 Container Diagram")

        lines.append(f"    subgraph {self.sanitize_id(system_name)}[\"{system_name}\"]")

        # 添加容器
        for container in containers:
            cid = self.sanitize_id(container.get("id", ""))
            name = container.get("name", "")
            desc = container.get("description", "")
            ctype = container.get("type", "web")
            tech = container.get("technology", "")

            if cid and name:
                label = f"{name}"
                if tech:
                    label += f"<br/>[{tech}]"
                if desc:
                    label += f"<br/><small>{desc}</small>"

                style = self.CONTAINER_STYLES.get(ctype, self.CONTAINER_STYLES["web"])
                shape_open = style["shape"]
                shape_close = "]" if shape_open == "[" else ")]" if shape_open == "[(" else "}"

                lines.append(f"        {cid}{shape_open}\"{label}\"{shape_close}")

        lines.append("    end")

        # 添加外部系统
        for ext in external_systems:
            ext_id = self.sanitize_id(ext.get("id", ""))
            ext_name = ext.get("name", "")
            ext_desc = ext.get("description", "")
            if ext_id and ext_name:
                lines.append(f"    {ext_id}[\"{ext_name}<br/><small>{ext_desc}</small>\"]")
                lines.append(f"    style {ext_id} fill:#999,stroke:#666")

        # 添加关系
        for rel in relationships:
            source = self.sanitize_id(rel.get("source", ""))
            target = self.sanitize_id(rel.get("target", ""))
            desc = rel.get("description", "")
            tech = rel.get("technology", "")

            if source and target:
                label = desc
                if tech:
                    label = f"{desc}<br/>[{tech}]" if desc else f"[{tech}]"

                if label:
                    lines.append(f"    {source} -->|\"{label}\"| {target}")
                else:
                    lines.append(f"    {source} --> {target}")

        return self.wrap_mermaid("\n".join(lines))

    def generate_from_modules(
        self,
        project_name: str,
        modules: list[dict],
    ) -> str:
        """从模块信息自动生成容器图"""
        containers = []
        relationships = []

        # 映射模块到容器类型
        for module in modules:
            name = module.get("name", "")
            if not name:
                continue

            container_type = self._detect_container_type(name)
            technology = self._detect_technology(name, module)

            containers.append({
                "id": name.replace(".", "_"),
                "name": name.split(".")[-1] if "." in name else name,
                "description": module.get("description", ""),
                "type": container_type,
                "technology": technology,
            })

        # 基于命名约定推断关系
        for i, c1 in enumerate(containers):
            for c2 in containers[i+1:]:
                if self._should_connect(c1, c2):
                    relationships.append({
                        "source": c1["id"],
                        "target": c2["id"],
                        "description": "Uses",
                    })

        data = {
            "system_name": project_name,
            "containers": containers,
            "external_systems": [],
            "relationships": relationships,
        }

        return self.generate(data, f"{project_name} - Container Diagram")

    def _detect_container_type(self, name: str) -> str:
        """检测容器类型"""
        name_lower = name.lower()
        if any(x in name_lower for x in ["db", "database", "store", "redis", "mongo"]):
            return "database"
        elif any(x in name_lower for x in ["queue", "mq", "kafka", "rabbit"]):
            return "queue"
        elif any(x in name_lower for x in ["api", "gateway", "router"]):
            return "api"
        elif any(x in name_lower for x in ["web", "ui", "frontend", "static"]):
            return "web"
        else:
            return "web"

    def _detect_technology(self, name: str, module: dict) -> str:
        """检测技术栈"""
        imports = module.get("imports", [])
        techs = []

        for imp in imports:
            module_name = imp.get("module", "").lower()
            if "fastapi" in module_name:
                techs.append("FastAPI")
            elif "flask" in module_name:
                techs.append("Flask")
            elif "django" in module_name:
                techs.append("Django")
            elif "sqlalchemy" in module_name:
                techs.append("SQLAlchemy")
            elif "pydantic" in module_name:
                techs.append("Pydantic")
            elif "redis" in module_name:
                techs.append("Redis")

        return ", ".join(set(techs)) if techs else "Python"

    def _should_connect(self, c1: dict, c2: dict) -> bool:
        """判断两个容器是否应该连接"""
        name1 = c1["name"].lower()
        name2 = c2["name"].lower()

        # 服务层依赖数据层
        if "service" in name1 and any(x in name2 for x in ["repo", "db", "dao"]):
            return True
        # API 层依赖服务层
        if any(x in name1 for x in ["api", "controller"]) and "service" in name2:
            return True

        return False


class C4ComponentDiagramGenerator(BaseDiagramGenerator):
    """
    C4 组件图生成器
    展示容器内部的组件结构
    """

    def generate(
        self,
        data: dict,
        title: Optional[str] = None
    ) -> str:
        """
        生成 C4 组件图
        
        Args:
            data: 包含以下字段:
                - container_name: 容器名称
                - components: 组件列表 [{"id": "", "name": "", "description": "", "type": "", "technology": ""}]
                - relationships: 关系列表
        """
        container_name = data.get("container_name", "Container")
        components = data.get("components", [])
        relationships = data.get("relationships", [])

        lines = ["graph TB"]

        if title:
            lines.append(f"    %% {title}")
            lines.append(f"    %% C4 Component Diagram")

        lines.append(f"    subgraph {self.sanitize_id(container_name)}[\"{container_name}\"]")

        # 添加组件
        for comp in components:
            cid = self.sanitize_id(comp.get("id", ""))
            name = comp.get("name", "")
            desc = comp.get("description", "")
            ctype = comp.get("type", "service")
            tech = comp.get("technology", "")

            if cid and name:
                label = f"{name}"
                if tech:
                    label += f"<br/>[{tech}]"
                if desc:
                    label += f"<br/><small>{desc}</small>"

                lines.append(f"        {cid}[\"{label}\"]")
                lines.append(f"        style {cid} fill:#85bbf0,stroke:#5d96c9")

        lines.append("    end")

        # 添加关系
        for rel in relationships:
            source = self.sanitize_id(rel.get("source", ""))
            target = self.sanitize_id(rel.get("target", ""))
            desc = rel.get("description", "")

            if source and target:
                if desc:
                    lines.append(f"    {source} -->|\"{desc}\"| {target}")
                else:
                    lines.append(f"    {source} --> {target}")

        return self.wrap_mermaid("\n".join(lines))

    def generate_from_module(self, module: dict) -> str:
        """从单个模块生成组件图"""
        classes = module.get("classes", [])
        functions = module.get("functions", [])

        components = []
        relationships = []

        # 类作为组件
        for cls in classes:
            cls_name = cls.get("name", "")
            if not cls_name:
                continue

            ctype = self._detect_component_type(cls)
            components.append({
                "id": f"comp_{cls_name}",
                "name": cls_name,
                "description": cls.get("docstring", "")[:50] if cls.get("docstring") else "",
                "type": ctype,
                "technology": "Python Class",
            })

            # 检测继承关系
            bases = cls.get("bases", [])
            for base in bases:
                relationships.append({
                    "source": f"comp_{cls_name}",
                    "target": f"comp_{base}" if f"comp_{base}" in [c["id"] for c in components] else base,
                    "description": "extends",
                })

        # 函数作为组件（仅主要函数）
        for func in functions[:10]:  # 限制数量
            func_name = func.get("name", "")
            if not func_name or func_name.startswith("_"):
                continue

            components.append({
                "id": f"func_{func_name}",
                "name": func_name,
                "description": "Function",
                "type": "function",
                "technology": "Python Function",
            })

        data = {
            "container_name": module.get("name", "Module"),
            "components": components,
            "relationships": relationships,
        }

        return self.generate(data, f"{module.get('name', 'Module')} - Components")

    def _detect_component_type(self, cls: dict) -> str:
        """检测组件类型"""
        name = cls.get("name", "").lower()
        bases = [b.lower() for b in cls.get("bases", [])]

        if any(x in name for x in ["controller", "handler", "router"]):
            return "controller"
        elif any(x in name for x in ["service", "manager", "provider"]):
            return "service"
        elif any(x in name for x in ["repository", "repo", "dao"]):
            return "repository"
        elif any(x in name for x in ["model", "entity", "schema"]):
            return "entity"
        elif "abc" in bases or "abstract" in name:
            return "interface"
        else:
            return "service"


class C4CodeDiagramGenerator(BaseDiagramGenerator):
    """
    C4 代码图生成器
    展示类/接口级别的代码结构（UML 类图风格）
    """

    def generate(
        self,
        data: dict,
        title: Optional[str] = None
    ) -> str:
        """
        生成 C4 代码图（类图）
        
        Args:
            data: 包含以下字段:
                - classes: 类列表 [{"name": "", "attributes": [], "methods": [], "stereotype": ""}]
                - relationships: 关系列表 [{"source": "", "target": "", "type": ""}]
        """
        classes = data.get("classes", [])
        relationships = data.get("relationships", [])

        lines = ["classDiagram"]

        if title:
            lines.append(f"    %% {title}")
            lines.append(f"    %% C4 Code Diagram (Class Diagram)")

        # 添加类定义
        for cls in classes:
            name = cls.get("name", "")
            if not name:
                continue

            attrs = cls.get("attributes", [])
            methods = cls.get("methods", [])
            stereotype = cls.get("stereotype", "")

            lines.append(f"    class {name}")

            if stereotype:
                lines.append(f"    <<{stereotype}>> {name}")

            for attr in attrs:
                attr_name = attr.get("name", "")
                attr_type = attr.get("type", "")
                visibility = attr.get("visibility", "public")
                vis_symbol = {"public": "+", "private": "-", "protected": "#"}.get(visibility, "+")

                if attr_name:
                    if attr_type:
                        lines.append(f"    {name} : {vis_symbol}{attr_name} {attr_type}")
                    else:
                        lines.append(f"    {name} : {vis_symbol}{attr_name}")

            for method in methods:
                method_name = method.get("name", "")
                params = method.get("parameters", [])
                return_type = method.get("return_type", "")
                visibility = method.get("visibility", "public")
                vis_symbol = {"public": "+", "private": "-", "protected": "#"}.get(visibility, "+")

                if method_name:
                    param_str = ", ".join([p.get("name", "") for p in params])
                    if return_type:
                        lines.append(f"    {name} : {vis_symbol}{method_name}({param_str}) {return_type}")
                    else:
                        lines.append(f"    {name} : {vis_symbol}{method_name}({param_str})")

        # 添加关系
        for rel in relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_type = rel.get("type", "association")

            if source and target:
                if rel_type == "inheritance":
                    lines.append(f"    {source} --|> {target}")
                elif rel_type == "composition":
                    lines.append(f"    {source} --* {target}")
                elif rel_type == "aggregation":
                    lines.append(f"    {source} --o {target}")
                elif rel_type == "dependency":
                    lines.append(f"    {source} ..> {target}")
                else:
                    lines.append(f"    {source} --> {target}")

        return self.wrap_mermaid("\n".join(lines))

    def generate_from_class_info(self, classes: list[dict]) -> str:
        """从类信息生成代码图"""
        class_defs = []
        relationships = []

        for cls in classes:
            cls_name = cls.get("name", "")
            if not cls_name:
                continue

            # 提取属性
            properties = cls.get("properties", [])
            attrs = []
            for prop in properties:
                attrs.append({
                    "name": prop.get("name", ""),
                    "type": prop.get("type_hint", ""),
                    "visibility": prop.get("visibility", "public"),
                })

            # 提取方法
            methods = cls.get("methods", [])
            method_defs = []
            for method in methods:
                method_defs.append({
                    "name": method.get("name", ""),
                    "parameters": method.get("parameters", []),
                    "return_type": method.get("return_type", ""),
                    "visibility": "public",
                })

            # 检测继承关系
            bases = cls.get("bases", [])
            for base in bases:
                if base not in ["object", "BaseModel", "ABC"]:
                    relationships.append({
                        "source": cls_name,
                        "target": base,
                        "type": "inheritance",
                    })

            class_defs.append({
                "name": cls_name,
                "attributes": attrs,
                "methods": method_defs,
                "stereotype": "",
            })

        data = {
            "classes": class_defs,
            "relationships": relationships,
        }

        return self.generate(data, "Code Level Diagram")


class C4DiagramGenerator:
    """
    C4 图表统一生成器
    提供所有四层架构图的生成能力
    """

    def __init__(self):
        self.context_gen = C4ContextDiagramGenerator()
        self.container_gen = C4ContainerDiagramGenerator()
        self.component_gen = C4ComponentDiagramGenerator()
        self.code_gen = C4CodeDiagramGenerator()

    def generate_all_levels(
        self,
        project_info: dict,
    ) -> dict[str, str]:
        """
        生成所有四层 C4 图表
        
        Returns:
            包含四个层级图表的字典
        """
        return {
            "context": self.context_gen.generate_from_project(
                project_info.get("name", "Project"),
                project_info.get("description", ""),
                project_info.get("users", []),
                project_info.get("external_systems", []),
            ),
            "container": self.container_gen.generate_from_modules(
                project_info.get("name", "Project"),
                project_info.get("modules", []),
            ),
            "component": "",  # 需要针对特定容器生成
            "code": "",  # 需要针对特定类生成
        }
