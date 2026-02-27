"""
API 文档生成器
支持 REST API 端点检测、OpenAPI 兼容文档生成
"""

import json
import re
from dataclasses import dataclass, field
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


@dataclass
class APIEndpoint:
    """API 端点"""
    path: str
    method: str
    handler: str
    description: str = ""
    parameters: list[dict] = field(default_factory=list)
    request_body: Optional[dict] = None
    responses: dict[int, dict] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    deprecated: bool = False


@dataclass
class APIGroup:
    """API 分组"""
    name: str
    description: str
    endpoints: list[APIEndpoint] = field(default_factory=list)
    base_path: str = ""


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
            project_language = context.project_language or context.detect_project_language()
            
            api_data = {
                "modules": [],
                "endpoints": [],
                "openapi": {},
            }
            
            api_data["modules"] = self._extract_api_modules(context)
            api_data["endpoints"] = self._extract_rest_endpoints(context, project_language)
            api_data["openapi"] = self._generate_openapi_spec(context, api_data["endpoints"], project_language)
            
            if context.metadata.get("llm_client"):
                enhanced_data = await self._enhance_with_llm(
                    context,
                    api_data,
                    context.metadata["llm_client"]
                )
                api_data.update(enhanced_data)

            content = self.render_template(
                description=f"{context.project_name} API 文档",
                modules=api_data["modules"],
                endpoints=api_data["endpoints"],
                openapi=api_data["openapi"],
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message="API 文档生成成功",
                metadata={
                    "module_count": len(api_data["modules"]),
                    "endpoint_count": len(api_data["endpoints"]),
                },
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
                        "properties": [],
                    }

                    for prop in cls.properties:
                        api_class["properties"].append({
                            "name": prop.name,
                            "type": prop.type_hint or "Any",
                            "visibility": prop.visibility,
                        })

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
                                "is_async": method.is_async if hasattr(method, 'is_async') else False,
                            }
                            api_class["methods"].append(api_method)

                    if api_class["methods"] or api_class["properties"]:
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
                            "is_async": func.is_async if hasattr(func, 'is_async') else False,
                        }
                        api_module["functions"].append(api_func)

                if api_module["classes"] or api_module["functions"]:
                    api_modules.append(api_module)

        return api_modules[:20]

    def _extract_rest_endpoints(self, context: DocGeneratorContext, project_language: str) -> list[dict[str, Any]]:
        """提取 REST API 端点"""
        endpoints = []
        
        if project_language == "java":
            endpoints = self._extract_java_endpoints(context)
        elif project_language == "typescript":
            endpoints = self._extract_typescript_endpoints(context)
        else:
            endpoints = self._extract_python_endpoints(context)
        
        return endpoints

    def _extract_python_endpoints(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取 Python REST API 端点"""
        endpoints = []
        
        if not context.parse_result or not context.parse_result.modules:
            return endpoints
        
        http_methods = ["get", "post", "put", "delete", "patch", "head", "options"]
        
        for module in context.parse_result.modules:
            for cls in module.classes:
                class_endpoints = []
                class_base_path = ""
                
                for decorator in getattr(cls, 'decorators', []):
                    if "APIRouter" in decorator or "Router" in decorator:
                        match = re.search(r'prefix\s*=\s*["\']([^"\']+)["\']', decorator)
                        if match:
                            class_base_path = match.group(1)
                
                for method in cls.methods:
                    endpoint = self._parse_python_endpoint(method, class_base_path, f"{module.name}.{cls.name}")
                    if endpoint:
                        class_endpoints.append(endpoint)
                
                endpoints.extend(class_endpoints)
            
            for func in module.functions:
                endpoint = self._parse_python_endpoint(func, "", f"{module.name}")
                if endpoint:
                    endpoints.append(endpoint)
        
        return endpoints[:50]

    def _parse_python_endpoint(self, func_or_method: Any, base_path: str, location: str) -> Optional[dict[str, Any]]:
        """解析 Python 端点"""
        http_methods = ["get", "post", "put", "delete", "patch", "head", "options"]
        
        decorators = getattr(func_or_method, 'decorators', [])
        if not decorators and hasattr(func_or_method, 'docstring'):
            docstring = func_or_method.docstring or ""
            if any(f"@{method}" in docstring.lower() for method in http_methods):
                decorators = [docstring]
        
        for decorator in decorators:
            decorator_lower = decorator.lower()
            for method in http_methods:
                if f"@{method}" in decorator_lower or f"@app.{method}" in decorator_lower or f"@router.{method}" in decorator_lower:
                    path_match = re.search(rf'{method}\s*\(\s*["\']([^"\']+)["\']', decorator)
                    path = path_match.group(1) if path_match else "/"
                    
                    full_path = f"{base_path}{path}" if base_path else path
                    
                    return {
                        "path": full_path,
                        "method": method.upper(),
                        "handler": func_or_method.name,
                        "location": location,
                        "description": func_or_method.docstring.split("\n")[0] if func_or_method.docstring else "",
                        "parameters": self._extract_endpoint_parameters(func_or_method),
                        "return_type": func_or_method.return_type or "Any",
                    }
        
        return None

    def _extract_endpoint_parameters(self, func_or_method: Any) -> list[dict[str, str]]:
        """提取端点参数"""
        parameters = []
        
        for param in func_or_method.parameters:
            if param.name in ["self", "cls", "request", "response"]:
                continue
            
            param_info = {
                "name": param.name,
                "type": param.type_hint or "Any",
                "required": param.default_value is None,
                "default": param.default_value,
                "in": "query",
            }
            
            if param.type_hint:
                if "Path" in param.type_hint or "path" in param.name.lower():
                    param_info["in"] = "path"
                elif "Body" in param.type_hint or "body" in param.name.lower():
                    param_info["in"] = "body"
                elif "Header" in param.type_hint or "header" in param.name.lower():
                    param_info["in"] = "header"
                elif "Cookie" in param.type_hint or "cookie" in param.name.lower():
                    param_info["in"] = "cookie"
            
            parameters.append(param_info)
        
        return parameters

    def _extract_java_endpoints(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取 Java REST API 端点"""
        endpoints = []
        
        if not context.parse_result or not context.parse_result.modules:
            return endpoints
        
        spring_annotations = {
            "GetMapping": "GET",
            "PostMapping": "POST",
            "PutMapping": "PUT",
            "DeleteMapping": "DELETE",
            "PatchMapping": "PATCH",
            "RequestMapping": None,
        }
        
        for module in context.parse_result.modules:
            for cls in module.classes:
                class_base_path = ""
                
                for annotation in getattr(cls, 'annotations', []):
                    if "RequestMapping" in annotation:
                        match = re.search(r'value\s*=\s*["\']([^"\']+)["\']', annotation)
                        if match:
                            class_base_path = match.group(1)
                
                for method in cls.methods:
                    for annotation in getattr(method, 'annotations', []):
                        for annotation_name, http_method in spring_annotations.items():
                            if annotation_name in annotation:
                                path_match = re.search(r'value\s*=\s*["\']([^"\']+)["\']', annotation)
                                path = path_match.group(1) if path_match else "/"
                                
                                full_path = f"{class_base_path}{path}" if class_base_path else path
                                
                                if annotation_name == "RequestMapping" and http_method is None:
                                    method_match = re.search(r'method\s*=\s*RequestMethod\.(\w+)', annotation)
                                    http_method = method_match.group(1) if method_match else "GET"
                                
                                endpoints.append({
                                    "path": full_path,
                                    "method": http_method if http_method else "GET",
                                    "handler": method.name,
                                    "location": f"{module.name}.{cls.name}",
                                    "description": method.docstring.split("\n")[0] if method.docstring else "",
                                    "parameters": [],
                                    "return_type": method.return_type or "void",
                                })
                                break
        
        return endpoints[:50]

    def _extract_typescript_endpoints(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取 TypeScript REST API 端点"""
        endpoints = []
        
        if not context.parse_result or not context.parse_result.modules:
            return endpoints
        
        http_methods = ["get", "post", "put", "delete", "patch"]
        
        for module in context.parse_result.modules:
            for func in module.functions:
                func_lower = func.name.lower()
                for method in http_methods:
                    if func_lower.startswith(method) or func_lower == method:
                        endpoints.append({
                            "path": f"/{func.name}",
                            "method": method.upper(),
                            "handler": func.name,
                            "location": module.name,
                            "description": func.docstring.split("\n")[0] if func.docstring else "",
                            "parameters": [{"name": p.name, "type": p.type_hint or "any"} for p in func.parameters],
                            "return_type": func.return_type or "any",
                        })
                        break
            
            for cls in module.classes:
                for method in cls.methods:
                    method_lower = method.name.lower()
                    for http_method in http_methods:
                        if method_lower.startswith(http_method) or method_lower == http_method:
                            endpoints.append({
                                "path": f"/{method.name}",
                                "method": http_method.upper(),
                                "handler": f"{cls.name}.{method.name}",
                                "location": f"{module.name}.{cls.name}",
                                "description": method.docstring.split("\n")[0] if method.docstring else "",
                                "parameters": [{"name": p.name, "type": p.type_hint or "any"} for p in method.parameters],
                                "return_type": method.return_type or "any",
                            })
                            break
        
        return endpoints[:50]

    def _generate_openapi_spec(self, context: DocGeneratorContext, endpoints: list[dict], project_language: str) -> dict[str, Any]:
        """生成 OpenAPI 规范"""
        openapi = {
            "openapi": "3.0.0",
            "info": {
                "title": context.project_name,
                "version": "1.0.0",
                "description": f"{context.project_name} API 文档",
            },
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {},
            },
        }
        
        for endpoint in endpoints:
            path = endpoint["path"]
            method = endpoint["method"].lower()
            
            if path not in openapi["paths"]:
                openapi["paths"][path] = {}
            
            path_item = {
                "summary": endpoint.get("description", ""),
                "operationId": endpoint.get("handler", ""),
                "responses": {
                    "200": {
                        "description": "成功响应",
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"}
                            }
                        }
                    }
                },
            }
            
            if endpoint.get("parameters"):
                path_item["parameters"] = []
                for param in endpoint["parameters"]:
                    path_item["parameters"].append({
                        "name": param.get("name", ""),
                        "in": param.get("in", "query"),
                        "required": param.get("required", False),
                        "schema": {"type": self._map_type_to_openapi(param.get("type", "string"))},
                    })
            
            openapi["paths"][path][method] = path_item
        
        return openapi

    def _map_type_to_openapi(self, type_str: str) -> str:
        """将类型映射到 OpenAPI 类型"""
        type_mapping = {
            "str": "string",
            "string": "string",
            "int": "integer",
            "integer": "integer",
            "float": "number",
            "bool": "boolean",
            "boolean": "boolean",
            "list": "array",
            "dict": "object",
            "any": "object",
        }
        
        type_lower = type_str.lower().replace("optional[", "").replace("]", "")
        return type_mapping.get(type_lower, "string")

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        api_data: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强 API 文档"""
        import json

        enhanced = {}

        endpoints = api_data.get("endpoints", [])
        if endpoints:
            prompt = f"""为以下 API 端点生成更详细的文档：

项目: {context.project_name}
端点数量: {len(endpoints)}
主要端点: {[e['path'] for e in endpoints[:5]]}

请以 JSON 格式返回：
{{
    "api_overview": "API 整体描述",
    "authentication": "认证方式说明",
    "rate_limiting": "限流说明",
    "common_headers": {{"Header-Name": "说明"}},
    "error_handling": "错误处理说明"
}}
"""

            try:
                response = await llm_client.agenerate(prompt)
                start = response.find("{")
                end = response.rfind("}")
                if start != -1 and end != -1:
                    result = json.loads(response[start:end+1])
                    enhanced.update(result)
            except Exception:
                pass

        return enhanced
