"""
LLM 图表生成器
使用 LLM 生成高阶架构图
"""

import json
from typing import TYPE_CHECKING, Any

from pywiki.generators.diagrams.flowchart import FlowchartGenerator
from pywiki.generators.diagrams.sequence import SequenceDiagramGenerator
from pywiki.generators.diagrams.class_diagram import ClassDiagramGenerator
from pywiki.generators.diagrams.state import StateDiagramGenerator
from pywiki.generators.diagrams.component import ComponentDiagramGenerator

from ..analyzers import ModuleFilter

if TYPE_CHECKING:
    from pywiki.generators.docs.base import DocGeneratorContext


class LLMDiagramGenerator:
    """LLM 图表生成器"""

    def __init__(
        self,
        flowchart_gen: FlowchartGenerator,
        sequence_gen: SequenceDiagramGenerator,
        class_diagram_gen: ClassDiagramGenerator,
        state_diagram_gen: StateDiagramGenerator,
        component_diagram_gen: ComponentDiagramGenerator,
    ):
        self.flowchart_gen = flowchart_gen
        self.sequence_gen = sequence_gen
        self.class_diagram_gen = class_diagram_gen
        self.state_diagram_gen = state_diagram_gen
        self.component_diagram_gen = component_diagram_gen

    async def generate_all(self, context: "DocGeneratorContext", llm_client: Any) -> dict[str, str]:
        """生成所有 LLM 增强图表"""
        return {
            "flowchart": await self._generate_flowchart(context, llm_client),
            "sequence_diagram": await self._generate_sequence_diagram(context, llm_client),
            "class_diagram": await self._generate_class_diagram(context, llm_client),
            "state_diagram": await self._generate_state_diagram(context, llm_client),
            "component_diagram": await self._generate_component_diagram(context, llm_client),
        }

    async def _generate_flowchart(self, context: "DocGeneratorContext", llm_client: Any) -> str:
        """生成业务流程图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""

        module_info = self._extract_module_info(context)

        system_prompt = "你是一名资深架构师，擅长从代码中抽象出业务流程和系统流程。"

        prompt = f"""分析以下项目代码结构，识别核心业务场景，生成业务流程图数据。

项目: {context.project_name}
模块数: {len(module_info)}

模块信息:
```json
{json.dumps(module_info, ensure_ascii=False, indent=2)}
```

返回 JSON 格式:
{{
    "title": "流程图标题",
    "nodes": [
        {{"id": "node1", "label": "开始", "type": "start"}},
        {{"id": "node2", "label": "处理", "type": "node"}},
        {{"id": "node3", "label": "判断", "type": "decision"}}
    ],
    "edges": [
        {{"source": "node1", "target": "node2", "label": ""}}
    ],
    "direction": "TD"
}}"""

        try:
            response = await llm_client.agenerate(prompt, system_prompt=system_prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(response[start:end+1])
                return self.flowchart_gen.generate(data)
        except Exception:
            pass

        return ""

    async def _generate_sequence_diagram(self, context: "DocGeneratorContext", llm_client: Any) -> str:
        """生成交互序列图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""

        module_info = self._extract_module_info(context, include_deps=True)

        system_prompt = "你是一名资深架构师，擅长分析系统组件间的交互关系。"

        prompt = f"""分析以下项目结构，识别关键交互场景，生成序列图数据。

项目: {context.project_name}

模块信息:
```json
{json.dumps(module_info, ensure_ascii=False, indent=2)}
```

返回 JSON 格式:
{{
    "title": "序列图标题",
    "participants": [
        {{"name": "User", "type": "actor"}},
        {{"name": "API", "type": "participant"}}
    ],
    "messages": [
        {{"source": "User", "target": "API", "content": "请求", "type": "sync"}}
    ]
}}"""

        try:
            response = await llm_client.agenerate(prompt, system_prompt=system_prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(response[start:end+1])
                return self.sequence_gen.generate(data)
        except Exception:
            pass

        return ""

    async def _generate_class_diagram(self, context: "DocGeneratorContext", llm_client: Any) -> str:
        """生成领域模型类图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""

        class_info = self._extract_class_info(context)

        system_prompt = "你是一名资深架构师，擅长领域驱动设计。"

        prompt = f"""分析以下类定义，识别领域模型，生成类图数据。

项目: {context.project_name}
类数: {len(class_info)}

类信息:
```json
{json.dumps(class_info, ensure_ascii=False, indent=2)}
```

返回 JSON 格式:
{{
    "title": "领域模型",
    "classes": [
        {{
            "name": "User",
            "attributes": [{{"name": "id", "type": "int", "visibility": "public"}}],
            "methods": [{{"name": "login", "visibility": "public"}}]
        }}
    ],
    "relationships": [
        {{"source": "User", "target": "Order", "type": "association", "label": "places"}}
    ]
}}"""

        try:
            response = await llm_client.agenerate(prompt, system_prompt=system_prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(response[start:end+1])
                return self.class_diagram_gen.generate(data)
        except Exception:
            pass

        return ""

    async def _generate_state_diagram(self, context: "DocGeneratorContext", llm_client: Any) -> str:
        """生成状态转移图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""

        state_candidates = self._extract_state_candidates(context)

        system_prompt = "你是一名资深架构师，擅长状态机建模。"

        prompt = f"""分析以下状态候选信息，识别业务实体生命周期，生成状态图数据。

项目: {context.project_name}

状态候选:
```json
{json.dumps(state_candidates, ensure_ascii=False, indent=2)}
```

返回 JSON 格式:
{{
    "title": "订单状态机",
    "states": [
        {{"name": "Pending", "description": "待处理"}},
        {{"name": "Completed", "description": "已完成"}}
    ],
    "transitions": [
        {{"source": "[*]", "target": "Pending", "event": "create"}},
        {{"source": "Pending", "target": "Completed", "event": "complete"}}
    ]
}}"""

        try:
            response = await llm_client.agenerate(prompt, system_prompt=system_prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(response[start:end+1])
                return self.state_diagram_gen.generate(data)
        except Exception:
            pass

        return ""

    async def _generate_component_diagram(self, context: "DocGeneratorContext", llm_client: Any) -> str:
        """生成组件架构图"""
        if not context.parse_result or not context.parse_result.modules:
            return ""

        module_info = self._extract_module_info(context, include_deps=True, limit=25)

        system_prompt = "你是一名资深架构师，擅长组件化设计。"

        prompt = f"""分析以下模块结构，抽象出系统组件架构，生成组件图数据。

项目: {context.project_name}
模块数: {len(module_info)}

模块信息:
```json
{json.dumps(module_info, ensure_ascii=False, indent=2)}
```

返回 JSON 格式:
{{
    "title": "系统组件架构",
    "components": [
        {{"name": "WebApp", "type": "component", "label": "Web Application"}},
        {{"name": "Database", "type": "database", "label": "Database"}}
    ],
    "connections": [
        {{"source": "WebApp", "target": "Database", "type": "sync", "label": "SQL"}}
    ],
    "groups": [
        {{"name": "Frontend", "components": ["WebApp"]}}
    ]
}}"""

        try:
            response = await llm_client.agenerate(prompt, system_prompt=system_prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(response[start:end+1])
                return self.component_diagram_gen.generate(data)
        except Exception:
            pass

        return ""

    def _extract_module_info(self, context: "DocGeneratorContext", include_deps: bool = False, limit: int = 20) -> list:
        """提取模块信息"""
        module_info = []
        filtered_modules = ModuleFilter.filter_project_modules(
            context.parse_result.modules, context.project_name
        )

        for module in filtered_modules[:limit]:
            classes = []
            if hasattr(module, 'classes') and module.classes:
                for cls in module.classes[:5]:
                    methods = [m.name for m in cls.methods[:3]] if hasattr(cls, 'methods') and cls.methods else []
                    classes.append({"name": cls.name, "methods": methods})

            functions = []
            if hasattr(module, 'functions') and module.functions:
                functions = [f.name for f in module.functions[:3]]

            info = {
                "name": module.name if hasattr(module, 'name') else str(module),
                "classes": classes,
                "functions": functions,
            }

            if include_deps and hasattr(module, 'imports') and module.imports:
                deps = []
                for imp in module.imports:
                    imp_module = imp.module if hasattr(imp, 'module') else str(imp)
                    if any(m.name == imp_module or imp_module.startswith(m.name + ".") for m in filtered_modules[:limit]):
                        deps.append(imp_module.split(".")[0])
                info["dependencies"] = list(set(deps))[:5]

            module_info.append(info)

        return module_info

    def _extract_class_info(self, context: "DocGeneratorContext") -> list:
        """提取类信息"""
        class_info = []
        filtered_modules = ModuleFilter.filter_project_modules(
            context.parse_result.modules, context.project_name
        )

        for module in filtered_modules[:15]:
            if hasattr(module, 'classes') and module.classes:
                for cls in module.classes[:5]:
                    attributes = []
                    if hasattr(cls, 'properties') and cls.properties:
                        for prop in cls.properties[:4]:
                            attributes.append({
                                "name": prop.name,
                                "type": getattr(prop, 'type_hint', ''),
                                "visibility": getattr(prop, 'visibility', 'public')
                            })

                    methods = []
                    if hasattr(cls, 'methods') and cls.methods:
                        for method in cls.methods[:3]:
                            methods.append({
                                "name": method.name,
                                "visibility": getattr(method, 'visibility', 'public')
                            })

                    class_info.append({
                        "name": cls.name,
                        "module": module.name if hasattr(module, 'name') else str(module),
                        "attributes": attributes,
                        "methods": methods,
                        "bases": getattr(cls, 'bases', [])[:2],
                        "is_abstract": getattr(cls, 'is_abstract', False),
                    })

        return class_info

    def _extract_state_candidates(self, context: "DocGeneratorContext") -> list:
        """提取状态候选"""
        state_candidates = []
        filtered_modules = ModuleFilter.filter_project_modules(
            context.parse_result.modules, context.project_name
        )

        for module in filtered_modules[:20]:
            if hasattr(module, 'classes') and module.classes:
                for cls in module.classes:
                    name_lower = cls.name.lower()
                    if any(kw in name_lower for kw in ['state', 'status', 'phase', 'stage', 'mode']):
                        values = []
                        if hasattr(cls, 'properties') and cls.properties:
                            values = [p.name for p in cls.properties[:6]]
                        state_candidates.append({
                            "type": "enum/class",
                            "name": cls.name,
                            "values": values,
                        })

                    if hasattr(cls, 'properties') and cls.properties:
                        for prop in cls.properties:
                            prop_name_lower = prop.name.lower()
                            if any(kw in prop_name_lower for kw in ['state', 'status']):
                                state_candidates.append({
                                    "type": "field",
                                    "class": cls.name,
                                    "field": prop.name,
                                })

        return state_candidates
