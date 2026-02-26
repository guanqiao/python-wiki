"""
流程图生成器
"""

from typing import Any, Optional

from pywiki.generators.diagrams.base import BaseDiagramGenerator


class FlowchartGenerator(BaseDiagramGenerator):
    """
    生成流程图
    
    示例输出:
    flowchart TD
        A[开始] --> B{用户认证}
        B -->|成功| C[加载数据]
        B -->|失败| D[显示错误]
        C --> E[渲染页面]
        E --> F[结束]
        D --> F
    """

    def generate(self, data: dict, title: Optional[str] = None) -> str:
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        direction = data.get("direction", "TD")

        lines = [f"flowchart {direction}"]

        if title:
            lines.append(f"    %% {title}")

        for node in nodes:
            node_id = self.sanitize_id(node.get("id", ""))
            node_label = self.sanitize_label(node.get("label", ""))
            node_type = node.get("type", "node")

            if node_type == "decision":
                lines.append(f"    {node_id}{{{node_label}}}")
            elif node_type == "start":
                lines.append(f"    {node_id}([{node_label}])")
            elif node_type == "end":
                lines.append(f"    {node_id}([{node_label}])")
            elif node_type == "subroutine":
                lines.append(f"    {node_id}[[{node_label}]]")
            elif node_type == "database":
                lines.append(f"    {node_id}[({node_label})]")
            else:
                lines.append(f"    {node_id}[{node_label}]")

        for edge in edges:
            source = self.sanitize_id(edge.get("source", ""))
            target = self.sanitize_id(edge.get("target", ""))
            label = edge.get("label", "")

            if source and target:
                if label:
                    lines.append(f"    {source} -->|{label}| {target}")
                else:
                    lines.append(f"    {source} --> {target}")

        return self.wrap_mermaid("\n".join(lines))

    def generate_from_function(self, func_info: dict) -> str:
        """从函数信息生成流程图"""
        nodes = []
        edges = []

        nodes.append({"id": "start", "label": "开始", "type": "start"})

        name = func_info.get("name", "函数")
        nodes.append({"id": "func", "label": name, "type": "node"})
        edges.append({"source": "start", "target": "func"})

        params = func_info.get("parameters", [])
        if params:
            param_node = "params"
            param_labels = [p.get("name", "") for p in params]
            nodes.append({
                "id": param_node,
                "label": f"参数: {', '.join(param_labels)}",
                "type": "node"
            })
            edges.append({"source": "func", "target": param_node})

        returns = func_info.get("return_type")
        if returns:
            return_node = "return"
            nodes.append({
                "id": return_node,
                "label": f"返回: {returns}",
                "type": "node"
            })
            if params:
                edges.append({"source": "params", "target": return_node})
            else:
                edges.append({"source": "func", "target": return_node})

        nodes.append({"id": "end", "label": "结束", "type": "end"})

        last_node = "return" if returns else ("params" if params else "func")
        edges.append({"source": last_node, "target": "end"})

        return self.generate({
            "nodes": nodes,
            "edges": edges,
            "direction": "TD"
        })

    def generate_business_flow(self, steps: list[dict]) -> str:
        """生成业务流程图"""
        nodes = []
        edges = []

        nodes.append({"id": "start", "label": "开始", "type": "start"})

        prev_id = "start"
        for i, step in enumerate(steps):
            step_id = f"step_{i}"
            step_label = step.get("name", f"步骤 {i + 1}")
            step_type = step.get("type", "node")

            if step.get("condition"):
                step_type = "decision"

            nodes.append({"id": step_id, "label": step_label, "type": step_type})

            condition = step.get("condition")
            if condition:
                edges.append({
                    "source": prev_id,
                    "target": step_id,
                    "label": condition
                })
            else:
                edges.append({"source": prev_id, "target": step_id})

            if step.get("next_on_true"):
                edges.append({
                    "source": step_id,
                    "target": f"step_{i + 1}",
                    "label": "是"
                })
            if step.get("next_on_false"):
                edges.append({
                    "source": step_id,
                    "target": step.get("next_on_false"),
                    "label": "否"
                })

            prev_id = step_id

        nodes.append({"id": "end", "label": "结束", "type": "end"})
        edges.append({"source": prev_id, "target": "end"})

        return self.generate({"nodes": nodes, "edges": edges, "direction": "TD"})
