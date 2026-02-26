"""
数据流图生成器
分析代码中的数据流转，生成数据流图 (DFD)
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum

from pywiki.generators.diagrams.base import BaseDiagramGenerator


class DataFlowNodeType(str, Enum):
    """数据流节点类型"""
    EXTERNAL_ENTITY = "external_entity"  # 外部实体（用户、外部系统）
    PROCESS = "process"                   # 处理过程
    DATA_STORE = "data_store"            # 数据存储
    DATA_FLOW = "data_flow"              # 数据流


@dataclass
class DataFlowNode:
    """数据流节点"""
    id: str
    name: str
    node_type: DataFlowNodeType
    description: str = ""
    parent_id: Optional[str] = None  # 用于分层 DFD


@dataclass
class DataFlow:
    """数据流"""
    id: str
    source: str
    target: str
    data_name: str  # 流动的数据名称
    description: str = ""


@dataclass
class DataFlowDiagram:
    """数据流图"""
    name: str
    level: int = 0  # DFD 层级（0-3）
    nodes: list[DataFlowNode] = field(default_factory=list)
    flows: list[DataFlow] = field(default_factory=list)
    sub_diagrams: list["DataFlowDiagram"] = field(default_factory=list)


class DataFlowDiagramGenerator(BaseDiagramGenerator):
    """
    数据流图生成器
    支持 DFD Level 0-3
    """

    def generate(
        self,
        data: dict,
        title: Optional[str] = None,
    ) -> str:
        """
        生成数据流图
        
        Args:
            data: 包含以下字段:
                - nodes: 节点列表 [{"id": "", "name": "", "type": "", "description": ""}]
                - flows: 数据流列表 [{"id": "", "source": "", "target": "", "data_name": ""}]
            title: 图表标题
        """
        nodes = data.get("nodes", [])
        flows = data.get("flows", [])

        lines = ["graph LR"]

        if title:
            lines.append(f"    %% {title}")
            lines.append(f"    %% Data Flow Diagram")

        # 添加节点定义
        for node in nodes:
            node_id = self.sanitize_id(node.get("id", ""))
            name = node.get("name", "")
            node_type = node.get("type", "process")
            description = node.get("description", "")

            if not node_id or not name:
                continue

            label = name
            if description:
                label += f"<br/><small>{description}</small>"

            # 根据类型使用不同形状
            if node_type == DataFlowNodeType.EXTERNAL_ENTITY.value:
                # 外部实体：矩形
                lines.append(f"    {node_id}[\"{label}\"]")
                lines.append(f"    style {node_id} fill:#e1f5fe,stroke:#01579b")
            elif node_type == DataFlowNodeType.PROCESS.value:
                # 处理过程：圆角矩形
                lines.append(f"    {node_id}({label})")
                lines.append(f"    style {node_id} fill:#fff3e0,stroke:#e65100")
            elif node_type == DataFlowNodeType.DATA_STORE.value:
                # 数据存储：开口矩形
                lines.append(f"    {node_id}[[\"{label}\"]]")
                lines.append(f"    style {node_id} fill:#f3e5f5,stroke:#4a148c")

        # 添加数据流
        for flow in flows:
            source = self.sanitize_id(flow.get("source", ""))
            target = self.sanitize_id(flow.get("target", ""))
            data_name = flow.get("data_name", "")

            if source and target:
                if data_name:
                    lines.append(f"    {source} -->|\"{data_name}\"| {target}")
                else:
                    lines.append(f"    {source} --> {target}")

        return self.wrap_mermaid("\n".join(lines))

    def generate_level0(
        self,
        system_name: str,
        external_entities: list[dict],
        data_flows: list[dict],
    ) -> str:
        """
        生成 DFD Level 0（上下文图）
        
        Args:
            system_name: 系统名称
            external_entities: 外部实体列表
            data_flows: 数据流列表
        """
        system_id = "system"

        nodes = [
            {
                "id": system_id,
                "name": system_name,
                "type": DataFlowNodeType.PROCESS.value,
                "description": "Main System",
            }
        ]

        for entity in external_entities:
            nodes.append({
                "id": entity.get("id", ""),
                "name": entity.get("name", ""),
                "type": DataFlowNodeType.EXTERNAL_ENTITY.value,
                "description": entity.get("description", ""),
            })

        flows = []
        for flow in data_flows:
            flows.append({
                "source": flow.get("source", ""),
                "target": flow.get("target", ""),
                "data_name": flow.get("data", ""),
            })

        return self.generate(
            {"nodes": nodes, "flows": flows},
            f"{system_name} - Level 0 DFD (Context)"
        )

    def generate_from_function(
        self,
        func_info: dict,
        module_name: str = "",
    ) -> str:
        """
        从函数信息生成数据流图
        
        分析函数的参数、返回值和内部数据流
        """
        func_name = func_info.get("name", "function")
        parameters = func_info.get("parameters", [])
        return_type = func_info.get("return_type", "")

        nodes = []
        flows = []

        # 函数本身作为处理过程
        func_id = self.sanitize_id(func_name)
        nodes.append({
            "id": func_id,
            "name": func_name,
            "type": DataFlowNodeType.PROCESS.value,
            "description": func_info.get("docstring", "")[:50] if func_info.get("docstring") else "",
        })

        # 参数作为输入
        for i, param in enumerate(parameters):
            param_name = param.get("name", f"param_{i}")
            param_type = param.get("type_hint", "")

            param_id = f"input_{param_name}"
            nodes.append({
                "id": param_id,
                "name": param_name,
                "type": DataFlowNodeType.EXTERNAL_ENTITY.value,
                "description": param_type,
            })
            flows.append({
                "source": param_id,
                "target": func_id,
                "data_name": param_name,
            })

        # 返回值作为输出
        if return_type:
            output_id = "output_result"
            nodes.append({
                "id": output_id,
                "name": "Result",
                "type": DataFlowNodeType.EXTERNAL_ENTITY.value,
                "description": return_type,
            })
            flows.append({
                "source": func_id,
                "target": output_id,
                "data_name": "result",
            })

        return self.generate(
            {"nodes": nodes, "flows": flows},
            f"{func_name} - Data Flow"
        )

    def generate_from_module(
        self,
        module_info: dict,
    ) -> str:
        """
        从模块信息生成数据流图
        
        分析模块内的数据流转
        """
        module_name = module_info.get("name", "module")
        functions = module_info.get("functions", [])
        classes = module_info.get("classes", [])

        nodes = []
        flows = []
        process_ids = []

        # 模块入口
        module_id = self.sanitize_id(module_name)
        nodes.append({
            "id": module_id,
            "name": module_name,
            "type": DataFlowNodeType.EXTERNAL_ENTITY.value,
            "description": "Module Entry",
        })

        # 类作为数据存储
        for cls in classes:
            cls_name = cls.get("name", "")
            if not cls_name:
                continue

            cls_id = f"store_{cls_name}"
            nodes.append({
                "id": cls_id,
                "name": cls_name,
                "type": DataFlowNodeType.DATA_STORE.value,
                "description": "Data Model",
            })

        # 函数作为处理过程
        for func in functions[:10]:  # 限制数量
            func_name = func.get("name", "")
            if not func_name or func_name.startswith("_"):
                continue

            func_id = f"proc_{func_name}"
            process_ids.append(func_id)
            nodes.append({
                "id": func_id,
                "name": func_name,
                "type": DataFlowNodeType.PROCESS.value,
                "description": "",
            })

            # 连接到模块入口
            flows.append({
                "source": module_id,
                "target": func_id,
                "data_name": "call",
            })

        # 处理过程之间的连接（基于命名约定）
        for i, proc1 in enumerate(process_ids):
            for proc2 in process_ids[i+1:]:
                # 简单的启发式：如果名称相关则连接
                name1 = proc1.replace("proc_", "")
                name2 = proc2.replace("proc_", "")

                if self._are_related(name1, name2):
                    flows.append({
                        "source": proc1,
                        "target": proc2,
                        "data_name": "data",
                    })

        return self.generate(
            {"nodes": nodes, "flows": flows},
            f"{module_name} - Module Data Flow"
        )

    def _are_related(self, name1: str, name2: str) -> bool:
        """判断两个名称是否相关"""
        name1_lower = name1.lower()
        name2_lower = name2.lower()

        # 前缀匹配
        if name1_lower.startswith(name2_lower) or name2_lower.startswith(name1_lower):
            return True

        # 常见模式
        patterns = [
            ("get", "fetch"),
            ("create", "add"),
            ("update", "modify"),
            ("delete", "remove"),
            ("validate", "check"),
            ("parse", "process"),
        ]

        for p1, p2 in patterns:
            if (p1 in name1_lower and p2 in name2_lower) or (p2 in name1_lower and p1 in name2_lower):
                return True

        return False

    def generate_database_flow(
        self,
        tables: list[dict],
        operations: list[dict],
    ) -> str:
        """
        生成数据库数据流图
        
        Args:
            tables: 表列表 [{"name": "", "description": ""}]
            operations: 操作列表 [{"name": "", "table": "", "type": "read/write"}]
        """
        nodes = []
        flows = []

        # 用户/应用
        nodes.append({
            "id": "application",
            "name": "Application",
            "type": DataFlowNodeType.EXTERNAL_ENTITY.value,
            "description": "",
        })

        # 表作为数据存储
        for table in tables:
            table_name = table.get("name", "")
            if not table_name:
                continue

            table_id = f"table_{table_name}"
            nodes.append({
                "id": table_id,
                "name": table_name,
                "type": DataFlowNodeType.DATA_STORE.value,
                "description": table.get("description", ""),
            })

        # 操作作为处理过程
        for op in operations:
            op_name = op.get("name", "")
            table_name = op.get("table", "")
            op_type = op.get("type", "read")

            if not op_name or not table_name:
                continue

            op_id = f"op_{op_name}"
            nodes.append({
                "id": op_id,
                "name": op_name,
                "type": DataFlowNodeType.PROCESS.value,
                "description": f"{op_type} operation",
            })

            # 连接到应用
            flows.append({
                "source": "application",
                "target": op_id,
                "data_name": "request",
            })

            # 连接到表
            table_id = f"table_{table_name}"
            if op_type == "read":
                flows.append({
                    "source": table_id,
                    "target": op_id,
                    "data_name": "data",
                })
            else:
                flows.append({
                    "source": op_id,
                    "target": table_id,
                    "data_name": "data",
                })

        return self.generate(
            {"nodes": nodes, "flows": flows},
            "Database Data Flow"
        )

    def generate_api_flow(
        self,
        endpoints: list[dict],
    ) -> str:
        """
        生成 API 数据流图
        
        Args:
            endpoints: 端点列表 [{"path": "", "method": "", "input": "", "output": ""}]
        """
        nodes = []
        flows = []

        # 客户端
        nodes.append({
            "id": "client",
            "name": "Client",
            "type": DataFlowNodeType.EXTERNAL_ENTITY.value,
            "description": "API Consumer",
        })

        # API Gateway
        nodes.append({
            "id": "gateway",
            "name": "API Gateway",
            "type": DataFlowNodeType.PROCESS.value,
            "description": "Request Router",
        })

        flows.append({
            "source": "client",
            "target": "gateway",
            "data_name": "HTTP Request",
        })

        # 端点处理
        for endpoint in endpoints:
            path = endpoint.get("path", "")
            method = endpoint.get("method", "GET")

            if not path:
                continue

            endpoint_id = f"ep_{method.lower()}_{path.replace('/', '_')}"
            endpoint_name = f"{method.upper()} {path}"

            nodes.append({
                "id": endpoint_id,
                "name": endpoint_name,
                "type": DataFlowNodeType.PROCESS.value,
                "description": "",
            })

            flows.append({
                "source": "gateway",
                "target": endpoint_id,
                "data_name": "route",
            })

            # 响应流
            flows.append({
                "source": endpoint_id,
                "target": "gateway",
                "data_name": endpoint.get("output", "response"),
            })

        flows.append({
            "source": "gateway",
            "target": "client",
            "data_name": "HTTP Response",
        })

        return self.generate(
            {"nodes": nodes, "flows": flows},
            "API Data Flow"
        )
