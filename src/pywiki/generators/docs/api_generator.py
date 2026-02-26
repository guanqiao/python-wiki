"""
API 文档生成器
"""

from pathlib import Path
from typing import Any, Optional

from pywiki.generators.docs.base import (
    BaseDocGenerator,
    DocGeneratorContext,
    DocGeneratorResult,
    DocType,
)
from pywiki.config.models import Language
from pywiki.parsers.types import ModuleInfo


class APIGenerator(BaseDocGenerator):
    """API 文档生成器"""

    doc_type = DocType.API
    template_name = "api.md.j2"

    def __init__(
        self,
        language: Language = Language.ZH,
        template_dir: Optional[Path] = None,
    ):
        super().__init__(language, template_dir)

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成 API 文档"""
        try:
            api_modules = self._extract_api_modules(context)
            
            if context.metadata.get("llm_client"):
                enhanced_modules = await self._enhance_with_llm(
                    context,
                    api_modules,
                    context.metadata["llm_client"]
                )
                if enhanced_modules:
                    api_modules = enhanced_modules

            content = self.render_template(
                description=f"{context.project_name} API 文档",
                modules=api_modules,
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message="API 文档生成成功",
                metadata={"module_count": len(api_modules)},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"生成失败: {str(e)}",
            )

    def _extract_api_modules(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取 API 相关模块"""
        api_modules = []

        if not context.parse_result or not context.parse_result.modules:
            return api_modules

        api_keywords = [
            "api", "rest", "controller", "handler", "endpoint", 
            "route", "view", "resource", "service"
        ]

        for module in context.parse_result.modules:
            module_name_lower = module.name.lower()
            
            if any(kw in module_name_lower for kw in api_keywords):
                api_module = {
                    "name": module.name,
                    "path": module.name.replace(".", "/"),
                    "description": module.docstring.split("\n")[0] if module.docstring else "",
                    "classes": [],
                    "functions": [],
                }

                for cls in module.classes:
                    api_class = {
                        "name": cls.name,
                        "bases": cls.bases,
                        "description": cls.docstring.split("\n")[0] if cls.docstring else "",
                        "methods": [],
                    }

                    for method in cls.methods:
                        if not method.name.startswith("_"):
                            api_method = {
                                "name": method.name,
                                "params": ", ".join([
                                    f"{p.name}: {p.type_hint or 'Any'}"
                                    for p in method.parameters
                                ]),
                                "return_type": method.return_type or "None",
                                "description": method.docstring.split("\n")[0] if method.docstring else "",
                            }
                            api_class["methods"].append(api_method)

                    if api_class["methods"]:
                        api_module["classes"].append(api_class)

                for func in module.functions:
                    if not func.name.startswith("_"):
                        api_func = {
                            "name": func.name,
                            "params": ", ".join([
                                f"{p.name}: {p.type_hint or 'Any'}"
                                for p in func.parameters
                            ]),
                            "return_type": func.return_type or "None",
                            "description": func.docstring.split("\n")[0] if func.docstring else "",
                        }
                        api_module["functions"].append(api_func)

                if api_module["classes"] or api_module["functions"]:
                    api_modules.append(api_module)

        return api_modules[:20]

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        api_modules: list[dict[str, Any]],
        llm_client: Any,
    ) -> Optional[list[dict[str, Any]]]:
        """使用 LLM 增强 API 文档"""
        import json

        enhanced_modules = []

        for module in api_modules[:5]:
            prompt = f"""为以下 API 模块生成更详细的描述：

模块名: {module['name']}
类: {[c['name'] for c in module['classes']]}
函数: {[f['name'] for f in module['functions']]}

请以 JSON 格式返回：
{{
    "enhanced_description": "更详细的模块描述",
    "usage_example": "使用示例代码",
    "common_use_cases": ["用例1", "用例2"]
}}
"""

            try:
                response = await llm_client.agenerate(prompt)
                start = response.find("{")
                end = response.rfind("}")
                if start != -1 and end != -1:
                    result = json.loads(response[start:end+1])
                    
                    if result.get("enhanced_description"):
                        module["description"] = result["enhanced_description"]
                    if result.get("usage_example"):
                        module["usage_example"] = result["usage_example"]
                    if result.get("common_use_cases"):
                        module["common_use_cases"] = result["common_use_cases"]

            except Exception:
                pass

            enhanced_modules.append(module)

        return enhanced_modules
