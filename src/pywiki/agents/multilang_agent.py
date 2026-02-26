"""
多语言分析 Agent
统一分析多语言项目，提供跨语言视图和调用链追踪
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from pywiki.agents.base import BaseAgent, AgentContext, AgentResult, AgentPriority
from pywiki.parsers.factory import ParserFactory


@dataclass
class CrossLanguageCall:
    """跨语言调用"""
    caller_language: str
    caller_location: str
    callee_language: str
    callee_location: str
    call_type: str
    confidence: float = 0.0


@dataclass
class UnifiedEntity:
    """统一实体表示"""
    name: str
    entity_type: str
    language: str
    location: str
    properties: dict[str, Any] = field(default_factory=dict)
    relationships: list[dict] = field(default_factory=list)


class MultilangAgent(BaseAgent):
    """多语言分析 Agent"""
    
    name = "multilang_agent"
    description = "多语言分析专家 - 统一分析 Python/TypeScript/Java 项目，提供跨语言视图"
    priority = AgentPriority.MEDIUM
    
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._parser_factory = ParserFactory()
        self._language_extensions = {
            "python": [".py", ".pyi"],
            "typescript": [".ts", ".tsx", ".js", ".jsx", ".mjs"],
            "java": [".java"],
        }
    
    def get_system_prompt(self) -> str:
        return """你是一个多语言代码分析专家。
你的任务是：
1. 分析多语言项目的代码结构
2. 识别跨语言的调用关系
3. 发现 API 契约和接口定义
4. 提供统一的项目视图

支持 Python、TypeScript/JavaScript、Java 等语言。"""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """执行多语言分析"""
        self.status = "running"
        
        try:
            analysis_type = context.metadata.get("analysis_type", "full")
            
            if analysis_type == "full":
                result = await self._full_analysis(context)
            elif analysis_type == "structure":
                result = await self._structure_analysis(context)
            elif analysis_type == "cross_calls":
                result = await self._cross_call_analysis(context)
            elif analysis_type == "api_contracts":
                result = await self._api_contract_analysis(context)
            elif analysis_type == "unified_view":
                result = await self._unified_view_analysis(context)
            else:
                result = AgentResult.error_result(f"未知分析类型: {analysis_type}")
            
            self._record_execution(context, result)
            self.status = "completed"
            return result
            
        except Exception as e:
            self.status = "error"
            return AgentResult.error_result(f"多语言分析失败: {str(e)}")
    
    async def _full_analysis(self, context: AgentContext) -> AgentResult:
        """完整多语言分析"""
        structure_result = await self._structure_analysis(context)
        cross_calls_result = await self._cross_call_analysis(context)
        api_contracts_result = await self._api_contract_analysis(context)
        
        unified_entities = []
        if self.llm_client:
            unified_entities = await self._generate_unified_model(context)
        
        return AgentResult.success_result(
            data={
                "structure": structure_result.data,
                "cross_calls": cross_calls_result.data,
                "api_contracts": api_contracts_result.data,
                "unified_entities": unified_entities,
            },
            message="完成多语言项目分析",
            confidence=0.85,
        )
    
    async def _structure_analysis(self, context: AgentContext) -> AgentResult:
        """分析项目结构"""
        if not context.project_path:
            return AgentResult.error_result("未指定项目路径")
        
        language_stats = {}
        
        for language, extensions in self._language_extensions.items():
            files = []
            for ext in extensions:
                files.extend(context.project_path.rglob(f"*{ext}"))
            
            files = [f for f in files if "__pycache__" not in str(f) and "node_modules" not in str(f)]
            
            total_lines = 0
            for file_path in files[:100]:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    total_lines += len(content.splitlines())
                except Exception:
                    pass
            
            language_stats[language] = {
                "file_count": len(files),
                "total_lines": total_lines,
                "extensions": extensions,
            }
        
        dominant_language = max(
            language_stats.items(),
            key=lambda x: x[1]["file_count"]
        )[0]
        
        return AgentResult.success_result(
            data={
                "languages": language_stats,
                "dominant_language": dominant_language,
                "is_multilang": sum(1 for s in language_stats.values() if s["file_count"] > 0) > 1,
            },
            message=f"项目主要使用 {dominant_language}",
            confidence=0.9,
        )
    
    async def _cross_call_analysis(self, context: AgentContext) -> AgentResult:
        """分析跨语言调用"""
        cross_calls = []
        
        if not context.project_path:
            return AgentResult.error_result("未指定项目路径")
        
        api_definitions = self._find_api_definitions(context.project_path)
        api_clients = self._find_api_clients(context.project_path)
        
        for client in api_clients:
            for api_def in api_definitions:
                if self._is_matching_api(client, api_def):
                    cross_calls.append(CrossLanguageCall(
                        caller_language=client["language"],
                        caller_location=client["location"],
                        callee_language=api_def["language"],
                        callee_location=api_def["location"],
                        call_type="api_call",
                        confidence=0.8,
                    ))
        
        return AgentResult.success_result(
            data={
                "cross_calls": [
                    {
                        "caller_language": c.caller_language,
                        "caller_location": c.caller_location,
                        "callee_language": c.callee_language,
                        "callee_location": c.callee_location,
                        "call_type": c.call_type,
                        "confidence": c.confidence,
                    }
                    for c in cross_calls
                ],
                "total_calls": len(cross_calls),
            },
            message=f"发现 {len(cross_calls)} 个跨语言调用",
            confidence=0.75,
        )
    
    async def _api_contract_analysis(self, context: AgentContext) -> AgentResult:
        """分析 API 契约"""
        contracts = []
        
        if not context.project_path:
            return AgentResult.error_result("未指定项目路径")
        
        rest_apis = self._find_rest_apis(context.project_path)
        grpc_apis = self._find_grpc_apis(context.project_path)
        graphql_apis = self._find_graphql_apis(context.project_path)
        
        contracts.extend(rest_apis)
        contracts.extend(grpc_apis)
        contracts.extend(graphql_apis)
        
        return AgentResult.success_result(
            data={
                "contracts": contracts,
                "by_type": {
                    "rest": len(rest_apis),
                    "grpc": len(grpc_apis),
                    "graphql": len(graphql_apis),
                },
            },
            message=f"发现 {len(contracts)} 个 API 契约",
            confidence=0.8,
        )
    
    async def _unified_view_analysis(self, context: AgentContext) -> AgentResult:
        """生成统一视图"""
        entities = []
        
        if not context.project_path:
            return AgentResult.error_result("未指定项目路径")
        
        for language, extensions in self._language_extensions.items():
            for ext in extensions:
                for file_path in context.project_path.rglob(f"*{ext}"):
                    if "__pycache__" in str(file_path) or "node_modules" in str(file_path):
                        continue
                    
                    parser = self._parser_factory.get_parser(file_path)
                    if parser:
                        try:
                            module = parser.parse_file(file_path)
                            if module:
                                for cls in module.classes:
                                    entities.append(UnifiedEntity(
                                        name=cls.name,
                                        entity_type="class",
                                        language=language,
                                        location=str(file_path),
                                        properties={
                                            "bases": cls.bases,
                                            "methods_count": len(cls.methods),
                                            "properties_count": len(cls.properties),
                                        },
                                    ))
                                
                                for func in module.functions:
                                    entities.append(UnifiedEntity(
                                        name=func.name,
                                        entity_type="function",
                                        language=language,
                                        location=str(file_path),
                                        properties={
                                            "is_async": func.is_async,
                                            "parameters_count": len(func.parameters),
                                        },
                                    ))
                        except Exception:
                            pass
        
        return AgentResult.success_result(
            data={
                "entities": [
                    {
                        "name": e.name,
                        "type": e.entity_type,
                        "language": e.language,
                        "location": e.location,
                        "properties": e.properties,
                    }
                    for e in entities[:100]
                ],
                "total_entities": len(entities),
                "by_language": self._count_by_language(entities),
                "by_type": self._count_by_type(entities),
            },
            message=f"统一视图包含 {len(entities)} 个实体",
            confidence=0.85,
        )
    
    async def _generate_unified_model(self, context: AgentContext) -> list[dict]:
        """生成统一模型"""
        entities = []
        
        if not self.llm_client:
            return entities
        
        structure_result = await self._structure_analysis(context)
        if not structure_result.data:
            return entities
        
        languages = structure_result.data.get("languages", {})
        
        prompt = f"""基于以下多语言项目结构，生成统一的概念模型：

语言统计:
{json.dumps(languages, indent=2)}

请识别：
1. 跨语言的共享概念
2. 领域实体
3. 服务边界
4. 数据流

返回 JSON 格式:
{{
    "entities": [
        {{
            "name": "实体名称",
            "type": "entity/service/dto",
            "languages": ["python", "typescript"],
            "description": "描述"
        }}
    ]
}}
"""
        
        try:
            response = await self.call_llm(prompt)
            parsed = json.loads(self._extract_json(response))
            entities = parsed.get("entities", [])
        except Exception:
            pass
        
        return entities
    
    def _find_api_definitions(self, project_path: Path) -> list[dict]:
        """查找 API 定义"""
        apis = []
        
        for file_path in project_path.rglob("*.py"):
            if "__pycache__" in str(file_path):
                continue
            
            try:
                content = file_path.read_text(encoding="utf-8")
                
                if "@app.get(" in content or "@app.post(" in content:
                    apis.append({
                        "language": "python",
                        "location": str(file_path),
                        "type": "fastapi",
                    })
                
                if "@RestController" in content or "@RequestMapping" in content:
                    apis.append({
                        "language": "java",
                        "location": str(file_path),
                        "type": "spring",
                    })
            
            except Exception:
                pass
        
        return apis
    
    def _find_api_clients(self, project_path: Path) -> list[dict]:
        """查找 API 客户端"""
        clients = []
        
        for file_path in project_path.rglob("*.ts"):
            if "node_modules" in str(file_path):
                continue
            
            try:
                content = file_path.read_text(encoding="utf-8")
                
                if "fetch(" in content or "axios" in content or "httpClient" in content:
                    clients.append({
                        "language": "typescript",
                        "location": str(file_path),
                        "type": "http_client",
                    })
            
            except Exception:
                pass
        
        return clients
    
    def _is_matching_api(self, client: dict, api_def: dict) -> bool:
        """检查客户端和 API 是否匹配"""
        return client["language"] != api_def["language"]
    
    def _find_rest_apis(self, project_path: Path) -> list[dict]:
        """查找 REST API"""
        apis = []
        
        for file_path in project_path.rglob("*.py"):
            if "__pycache__" in str(file_path):
                continue
            
            try:
                content = file_path.read_text(encoding="utf-8")
                
                http_methods = ["@app.get", "@app.post", "@app.put", "@app.delete", "@app.patch"]
                for method in http_methods:
                    if method in content:
                        apis.append({
                            "type": "rest",
                            "language": "python",
                            "location": str(file_path),
                            "framework": "fastapi" if "FastAPI" in content else "flask",
                        })
                        break
            
            except Exception:
                pass
        
        return apis
    
    def _find_grpc_apis(self, project_path: Path) -> list[dict]:
        """查找 gRPC API"""
        apis = []
        
        for proto_file in project_path.rglob("*.proto"):
            apis.append({
                "type": "grpc",
                "language": "protobuf",
                "location": str(proto_file),
            })
        
        return apis
    
    def _find_graphql_apis(self, project_path: Path) -> list[dict]:
        """查找 GraphQL API"""
        apis = []
        
        for gql_file in project_path.rglob("*.graphql"):
            apis.append({
                "type": "graphql",
                "language": "graphql",
                "location": str(gql_file),
            })
        
        for py_file in project_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                if "graphene" in content or "ariadne" in content or "strawberry" in content:
                    apis.append({
                        "type": "graphql",
                        "language": "python",
                        "location": str(py_file),
                    })
            except Exception:
                pass
        
        return apis
    
    def _count_by_language(self, entities: list[UnifiedEntity]) -> dict[str, int]:
        """按语言统计"""
        counts = {}
        for entity in entities:
            counts[entity.language] = counts.get(entity.language, 0) + 1
        return counts
    
    def _count_by_type(self, entities: list[UnifiedEntity]) -> dict[str, int]:
        """按类型统计"""
        counts = {}
        for entity in entities:
            counts[entity.entity_type] = counts.get(entity.entity_type, 0) + 1
        return counts