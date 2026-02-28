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
                "endpoints": [],
                "openapi": {},
            }
            
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
                description=f"{context.project_name} {self.labels.get('api_reference', 'API Reference')}",
                endpoints=api_data["endpoints"],
                openapi=api_data["openapi"],
                api_overview=api_data.get("api_overview", ""),
                authentication=api_data.get("authentication", ""),
                rate_limiting=api_data.get("rate_limiting", ""),
                common_headers=api_data.get("common_headers", {}),
                error_handling=api_data.get("error_handling", ""),
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message=self.labels.get("api_doc_success", "API documentation generated successfully"),
                metadata={
                    "endpoint_count": len(api_data["endpoints"]),
                },
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"{self.labels.get('generation_failed', 'Generation failed')}: {str(e)}",
            )

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
        """提取 Python REST API 端点
        
        只识别真正的 API 提供者：
        - FastAPI/Flask 路由装饰器 (@app.get, @router.post, @route)
        - APIRouter 类
        """
        endpoints = []
        
        if not context.parse_result or not context.parse_result.modules:
            return endpoints
        
        http_methods = ["get", "post", "put", "delete", "patch", "head", "options"]
        api_decorators = ["APIRouter", "Router", "Blueprint", "route"]
        
        for module in context.parse_result.modules:
            for cls in module.classes:
                is_api_class = False
                class_base_path = ""
                
                for decorator in getattr(cls, 'decorators', []):
                    for api_dec in api_decorators:
                        if api_dec in decorator:
                            is_api_class = True
                            match = re.search(r'prefix\s*=\s*["\']([^"\']+)["\']', decorator)
                            if match:
                                class_base_path = match.group(1)
                            break
                
                has_http_methods = False
                for method in cls.methods:
                    endpoint = self._parse_python_endpoint(method, class_base_path, f"{module.name}.{cls.name}")
                    if endpoint:
                        endpoints.append(endpoint)
                        has_http_methods = True
                
                if has_http_methods:
                    is_api_class = True
                
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
        """提取 Java REST API 端点
        
        只识别真正的 API 提供者：
        - Spring REST Controller (@RestController, @Controller)
        - Dubbo Service (@DubboService, @Service)
        - Feign Client (@FeignClient)
        """
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
        
        api_class_markers = [
            "Spring Controller",
            "Dubbo:",
            "Feign Client",
            "@RestController",
            "@Controller",
            "@DubboService",
            "@FeignClient",
        ]
        
        for module in context.parse_result.modules:
            for cls in module.classes:
                cls_docstring = cls.docstring or ""
                
                is_api_class = any(marker in cls_docstring for marker in api_class_markers)
                
                if not is_api_class:
                    continue
                
                class_base_path = ""
                class_consumes = []
                class_produces = []
                api_type = "REST"
                
                if "Route:" in cls_docstring:
                    match = re.search(r'Route:\s*([^\s|]+)', cls_docstring)
                    if match:
                        class_base_path = match.group(1)
                if "Consumes:" in cls_docstring:
                    match = re.search(r'Consumes:\s*([^|]+)', cls_docstring)
                    if match:
                        class_consumes = [c.strip() for c in match.group(1).split(",")]
                if "Produces:" in cls_docstring:
                    match = re.search(r'Produces:\s*([^|]+)', cls_docstring)
                    if match:
                        class_produces = [p.strip() for p in match.group(1).split(",")]
                
                if "Dubbo:" in cls_docstring:
                    api_type = "Dubbo"
                elif "Feign Client" in cls_docstring:
                    api_type = "Feign"
                
                for method in cls.methods:
                    endpoint_info = self._parse_java_method_endpoint(
                        method, cls, module, class_base_path, 
                        class_consumes, class_produces, spring_annotations, api_type
                    )
                    if endpoint_info:
                        endpoints.append(endpoint_info)
        
        return endpoints[:100]

    def _parse_java_method_endpoint(
        self,
        method,
        cls,
        module,
        class_base_path: str,
        class_consumes: list,
        class_produces: list,
        spring_annotations: dict,
        api_type: str = "REST",
    ) -> Optional[dict[str, Any]]:
        """解析Java方法端点"""
        method_docstring = method.docstring or ""
        
        http_method = None
        path = None
        consumes = list(class_consumes)
        produces = list(class_produces)
        
        for ann_name, default_method in spring_annotations.items():
            if f"Route:" in method_docstring or ann_name.lower().replace("mapping", "") in method_docstring.lower():
                if "Method:" in method_docstring:
                    match = re.search(r'Method:\s*(\w+)', method_docstring)
                    if match:
                        http_method = match.group(1).upper()
                
                if "Route:" in method_docstring:
                    match = re.search(r'Route:\s*([^\s|]+)', method_docstring)
                    if match:
                        path = match.group(1)
                
                if "Consumes:" in method_docstring:
                    match = re.search(r'Consumes:\s*([^|]+)', method_docstring)
                    if match:
                        consumes = [c.strip() for c in match.group(1).split(",")]
                
                if "Produces:" in method_docstring:
                    match = re.search(r'Produces:\s*([^|]+)', method_docstring)
                    if match:
                        produces = [p.strip() for p in match.group(1).split(",")]
                
                if not http_method:
                    if default_method:
                        http_method = default_method
                    else:
                        http_method = "GET"
                
                if not path:
                    path = "/"
                
                break
        
        if not http_method:
            return None
        
        full_path = f"{class_base_path}{path}" if class_base_path and path else path or "/"
        
        parameters = self._extract_java_method_parameters(method)
        
        security = None
        if "Security:" in method_docstring:
            match = re.search(r'Security:\s*([^|]+)', method_docstring)
            if match:
                security = match.group(1).strip()
        
        description = method_docstring.split("\n")[0] if method_docstring else ""
        for prefix in ["Route:", "Method:", "Consumes:", "Produces:", "Security:"]:
            description = re.sub(rf'{prefix}\s*[^\|]+\s*\|?\s*', '', description)
        description = description.strip()
        
        return {
            "path": full_path,
            "method": http_method,
            "handler": method.name,
            "location": f"{module.name}.{cls.name}",
            "description": description,
            "parameters": parameters,
            "return_type": method.return_type or "void",
            "consumes": consumes,
            "produces": produces,
            "security": security,
            "tags": [cls.name.replace("Controller", "").replace("Resource", "")],
            "api_type": api_type,
        }

    def _extract_java_method_parameters(self, method) -> list[dict[str, Any]]:
        """提取Java方法参数信息"""
        parameters = []
        
        for param in method.parameters:
            param_info = {
                "name": param.name,
                "type": param.type_hint or "Object",
                "required": True,
                "in": "query",
                "description": "",
            }
            
            if param.description:
                desc = param.description
                if "RequestParam" in desc:
                    param_info["in"] = "query"
                elif "PathVariable" in desc:
                    param_info["in"] = "path"
                elif "RequestBody" in desc:
                    param_info["in"] = "body"
                elif "RequestHeader" in desc:
                    param_info["in"] = "header"
                elif "CookieValue" in desc:
                    param_info["in"] = "cookie"
                
                required_match = re.search(r'required\s*=\s*(true|false)', desc)
                if required_match:
                    param_info["required"] = required_match.group(1).lower() == "true"
                
                default_match = re.search(r'defaultValue\s*=\s*["\']([^"\']+)["\']', desc)
                if default_match:
                    param_info["default"] = default_match.group(1)
                    param_info["required"] = False
                
                name_match = re.search(r'(?:name|value)\s*=\s*["\']([^"\']+)["\']', desc)
                if name_match:
                    param_info["name"] = name_match.group(1)
            
            if param.name not in ["request", "response", "principal", "authentication"]:
                parameters.append(param_info)
        
        return parameters

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
            "tags": [],
        }
        
        tags_set = set()
        
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
            
            if endpoint.get("tags"):
                path_item["tags"] = endpoint["tags"]
                tags_set.update(endpoint["tags"])
            
            if endpoint.get("consumes"):
                path_item["requestBody"] = {
                    "content": {
                        ct: {"schema": {"type": "object"}}
                        for ct in endpoint["consumes"]
                    }
                }
            
            if endpoint.get("produces"):
                for code, response in path_item["responses"].items():
                    response["content"] = {
                        ct: response["content"].get("application/json", {"schema": {"type": "object"}})
                        for ct in endpoint["produces"]
                    }
            
            if endpoint.get("security"):
                path_item["security"] = [{endpoint["security"]: []}]
            
            if endpoint.get("parameters"):
                path_item["parameters"] = []
                request_body_params = []
                
                for param in endpoint["parameters"]:
                    if param.get("in") == "body":
                        request_body_params.append(param)
                    else:
                        path_item["parameters"].append({
                            "name": param.get("name", ""),
                            "in": param.get("in", "query"),
                            "required": param.get("required", False),
                            "description": param.get("description", ""),
                            "schema": {"type": self._map_type_to_openapi(param.get("type", "string"))},
                        })
                
                if request_body_params and "requestBody" not in path_item:
                    path_item["requestBody"] = {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        p["name"]: {"type": self._map_type_to_openapi(p.get("type", "object"))}
                                        for p in request_body_params
                                    }
                                }
                            }
                        }
                    }
            
            openapi["paths"][path][method] = path_item
        
        for tag in tags_set:
            openapi["tags"].append({"name": tag})
        
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
            system_prompt = self._get_system_prompt()
            
            if self.language == Language.ZH:
                prompt = f"""# 任务
为 API 端点生成专业的文档说明。

# API 数据
- **项目名称**: {context.project_name}
- **端点数量**: {len(endpoints)}
- **主要端点**: {[e['path'] for e in endpoints[:5]]}

# 输出要求
请以 JSON 格式返回以下字段：
{{
    "api_overview": "API 整体描述（包含API定位、主要功能、设计理念）",
    "authentication": "认证方式说明（如JWT、OAuth2、API Key等）",
    "rate_limiting": "限流策略说明（如QPS限制、熔断机制等）",
    "common_headers": {{"Header-Name": "请求头说明"}},
    "error_handling": "错误处理机制说明（错误码、错误响应格式）"
}}

# 质量标准
- 描述需基于端点特征推断，符合RESTful规范
- 认证方式需根据端点路径和参数合理推测
- 限流和错误处理需符合业界最佳实践

请务必使用中文回答。"""
            else:
                prompt = f"""# Task
Generate professional documentation for API endpoints.

# API Data
- **Project Name**: {context.project_name}
- **Endpoint Count**: {len(endpoints)}
- **Main Endpoints**: {[e['path'] for e in endpoints[:5]]}

# Output Requirements
Please return the following fields in JSON format:
{{
    "api_overview": "API overall description (including positioning, main functions, design philosophy)",
    "authentication": "Authentication method description (e.g., JWT, OAuth2, API Key)",
    "rate_limiting": "Rate limiting strategy description (e.g., QPS limits, circuit breaker)",
    "common_headers": {{"Header-Name": "header description"}},
    "error_handling": "Error handling mechanism description (error codes, error response format)"
}}

# Quality Standards
- Description should be inferred from endpoint characteristics, following RESTful conventions
- Authentication method should be reasonably inferred from endpoint paths and parameters
- Rate limiting and error handling should follow industry best practices

Please respond in English."""

            try:
                response = await llm_client.agenerate(prompt, system_prompt=system_prompt)
                start = response.find("{")
                end = response.rfind("}")
                if start != -1 and end != -1:
                    result = json.loads(response[start:end+1])
                    enhanced.update(result)
            except Exception:
                pass

        return enhanced
