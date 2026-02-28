"""
多语言分析 Agent
统一分析多语言项目，提供跨语言视图和调用链追踪
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from pywiki.agents.base import BaseAgent, AgentContext, AgentResult, AgentPriority
from pywiki.analysis.package_analyzer import (
    PackageAnalyzer,
    SubPackageInfo,
    PackageDependency,
    ArchitectureLayer,
    PackageMetric,
)
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
        self._package_analyzer = PackageAnalyzer(parser_factory=self._parser_factory)
        self._language_extensions = {
            "python": [".py", ".pyi"],
            "typescript": [".ts", ".tsx", ".js", ".jsx", ".mjs"],
            "java": [".java"],
        }
    
    def get_system_prompt(self) -> str:
        return """# 角色定义
你是一位多语言代码分析专家，精通Python、TypeScript/JavaScript、Java等主流编程语言，擅长分析跨语言项目、多子包架构和API契约。

# 核心能力
1. **多语言分析**: 统一分析不同编程语言的代码结构
2. **跨语言调用识别**: 发现前后端、服务间的API调用关系
3. **API契约发现**: 识别REST、gRPC、GraphQL等API定义
4. **统一视图生成**: 提供跨语言的统一项目视图
5. **多子包分析**: 分析大型项目的子包结构、依赖关系和架构分层
6. **包边界检测**: 识别违反架构分层原则的调用

# 支持的语言
- **Python**: FastAPI、Flask、Django等框架
- **TypeScript/JavaScript**: Express、NestJS、React等框架
- **Java**: Spring Boot、MyBatis等框架
- **其他**: Go、Rust等（基础支持）

# 分析方法
## 跨语言调用识别
- HTTP客户端调用 → 服务端API端点
- 前端组件 → 后端服务接口
- 数据模型 → 数据库Schema

## API契约识别
- REST API: 路由装饰器、Controller注解
- gRPC: .proto文件定义
- GraphQL: Schema定义、Resolver实现

## 多子包分析
- 自动检测项目中的子包/模块结构
- 分析每个子包的职责和边界
- 检测子包间的依赖关系和耦合度
- 识别分层架构模式（如 Controller-Service-Repository）
- 发现违反包边界原则的调用

## 架构层识别
- **表示层(presentation)**: UI、Controller、API端点
- **业务层(business)**: Service、UseCase、Domain逻辑
- **数据层(data)**: Repository、DAO、Model、Entity
- **基础设施层(infrastructure)**: Config、Util、Common

# 分析类型
- `full`: 完整分析
- `structure`: 项目结构分析（含子包）
- `cross_calls`: 跨语言/跨包调用分析
- `api_contracts`: API契约分析
- `unified_view`: 统一视图（含层次化）
- `subpackages`: 子包结构分析
- `package_deps`: 包依赖分析
- `package_boundaries`: 包边界分析
- `package_metrics`: 包级别指标计算
- `architecture_layers`: 架构分层分析

# 输出规范
- 使用JSON格式输出结构化结果
- 跨语言调用包含：调用方语言、调用位置、被调用方语言、被调用位置、调用类型
- API契约包含：类型、语言、位置、框架
- 统一实体包含：名称、类型、语言、位置、属性
- 子包信息包含：名称、路径、语言、文件数、类数、函数数、导出符号、架构层提示
- 包依赖包含：源包、目标包、依赖类型、依赖强度
- 包指标包含：稳定性、抽象度、距离、耦合度、内聚性

请提供准确的多语言和多子包分析结果。"""
    
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
            elif analysis_type == "subpackages":
                result = await self._analyze_package_structure(context)
            elif analysis_type == "package_deps":
                result = await self._analyze_package_dependencies(context)
            elif analysis_type == "package_boundaries":
                result = await self._analyze_package_boundaries(context)
            elif analysis_type == "package_metrics":
                result = await self._calculate_package_metrics(context)
            elif analysis_type == "architecture_layers":
                result = await self._analyze_package_boundaries(context)
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
            for file_path in files[:500]:
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
        
        subpackages = self._detect_subpackages(context.project_path)
        
        package_tree = self._build_package_tree(subpackages) if subpackages else {}
        
        layer_distribution = self._analyze_layer_distribution(subpackages) if subpackages else {}
        
        return AgentResult.success_result(
            data={
                "languages": language_stats,
                "dominant_language": dominant_language,
                "is_multilang": sum(1 for s in language_stats.values() if s["file_count"] > 0) > 1,
                "subpackages": [
                    {
                        "name": sp.name,
                        "path": sp.path,
                        "language": sp.language,
                        "file_count": sp.file_count,
                        "layer_hint": sp.layer_hint,
                    }
                    for sp in subpackages[:50]
                ],
                "total_subpackages": len(subpackages),
                "package_tree": package_tree,
                "layer_distribution": layer_distribution,
            },
            message=f"项目主要使用 {dominant_language}，包含 {len(subpackages)} 个子包",
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
        
        subpackages = self._detect_subpackages(context.project_path)
        package_names = {sp.name for sp in subpackages}
        
        package_cross_calls = []
        
        for sp in subpackages:
            for imp_module in sp.imports_from:
                matched_package = self._find_matching_package(imp_module, package_names)
                
                if matched_package and matched_package != sp.name:
                    matched_sp = next((s for s in subpackages if s.name == matched_package), None)
                    
                    if matched_sp and matched_sp.language != sp.language:
                        package_cross_calls.append({
                            "caller_package": sp.name,
                            "caller_language": sp.language,
                            "callee_package": matched_package,
                            "callee_language": matched_sp.language,
                            "import_module": imp_module,
                            "call_type": "cross_package_import",
                        })
        
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
                "package_cross_calls": package_cross_calls,
                "total_package_cross_calls": len(package_cross_calls),
            },
            message=f"发现 {len(cross_calls)} 个跨语言调用，{len(package_cross_calls)} 个跨包调用",
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
        
        subpackages = self._detect_subpackages(context.project_path)
        layers = self._detect_layered_architecture(subpackages)
        
        hierarchical_view = self._build_hierarchical_view(subpackages, entities)
        
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
                    for e in entities[:200]
                ],
                "total_entities": len(entities),
                "by_language": self._count_by_language(entities),
                "by_type": self._count_by_type(entities),
                "hierarchical_view": hierarchical_view,
                "layers": [
                    {
                        "name": layer.name,
                        "packages": layer.packages,
                        "description": layer.description,
                    }
                    for layer in layers
                ],
                "subpackages_summary": [
                    {
                        "name": sp.name,
                        "language": sp.language,
                        "layer_hint": sp.layer_hint,
                        "class_count": sp.class_count,
                        "function_count": sp.function_count,
                    }
                    for sp in subpackages[:30]
                ],
            },
            message=f"统一视图包含 {len(entities)} 个实体，{len(subpackages)} 个子包，{len(layers)} 个架构层",
            confidence=0.85,
        )
    
    def _build_hierarchical_view(
        self, 
        subpackages: list[SubPackageInfo], 
        entities: list[UnifiedEntity]
    ) -> dict:
        """构建层次化视图"""
        view = {
            "layers": {},
            "packages": {},
        }
        
        for sp in subpackages:
            if sp.layer_hint:
                if sp.layer_hint not in view["layers"]:
                    view["layers"][sp.layer_hint] = {
                        "packages": [],
                        "total_classes": 0,
                        "total_functions": 0,
                    }
                view["layers"][sp.layer_hint]["packages"].append(sp.name)
                view["layers"][sp.layer_hint]["total_classes"] += sp.class_count
                view["layers"][sp.layer_hint]["total_functions"] += sp.function_count
            
            view["packages"][sp.name] = {
                "language": sp.language,
                "layer": sp.layer_hint or "unknown",
                "file_count": sp.file_count,
                "class_count": sp.class_count,
                "function_count": sp.function_count,
                "exports": sp.exports[:10],
            }
        
        return view
    
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
    
    def _detect_subpackages(self, project_path: Path) -> list[SubPackageInfo]:
        """检测项目中的子包"""
        return self._package_analyzer.detect_subpackages(project_path)
    
    async def _analyze_package_structure(self, context: AgentContext) -> AgentResult:
        """分析包结构"""
        if not context.project_path:
            return AgentResult.error_result("未指定项目路径")
        
        subpackages = self._detect_subpackages(context.project_path)
        
        if not subpackages:
            return AgentResult.success_result(
                data={"subpackages": [], "total": 0},
                message="未检测到子包结构",
                confidence=0.9,
            )
        
        package_tree = self._package_analyzer.build_package_tree(subpackages)
        layer_distribution = self._package_analyzer.analyze_layer_distribution(subpackages)
        
        return AgentResult.success_result(
            data={
                "subpackages": [
                    {
                        "name": sp.name,
                        "path": sp.path,
                        "language": sp.language,
                        "file_count": sp.file_count,
                        "class_count": sp.class_count,
                        "function_count": sp.function_count,
                        "exports": sp.exports[:20],
                        "imports_from": sp.imports_from[:10],
                        "layer_hint": sp.layer_hint,
                    }
                    for sp in subpackages
                ],
                "total": len(subpackages),
                "package_tree": package_tree,
                "layer_distribution": layer_distribution,
            },
            message=f"检测到 {len(subpackages)} 个子包",
            confidence=0.85,
        )
    
    async def _analyze_package_dependencies(self, context: AgentContext) -> AgentResult:
        """分析包间依赖"""
        if not context.project_path:
            return AgentResult.error_result("未指定项目路径")
        
        subpackages = self._detect_subpackages(context.project_path)
        dependencies = self._package_analyzer.analyze_package_dependencies(subpackages)
        circular_deps = self._package_analyzer.detect_circular_dependencies(dependencies)
        
        dependency_matrix = {}
        for dep in dependencies:
            if dep.source_package not in dependency_matrix:
                dependency_matrix[dep.source_package] = []
            dependency_matrix[dep.source_package].append(f"{dep.source_package}->{dep.target_package}")
        
        return AgentResult.success_result(
            data={
                "dependencies": [
                    {
                        "source": d.source_package,
                        "target": d.target_package,
                        "type": d.dependency_type,
                        "strength": d.strength,
                        "location_count": len(d.locations),
                    }
                    for d in dependencies
                ],
                "dependency_matrix": dependency_matrix,
                "circular_dependencies": circular_deps,
                "total_dependencies": len(dependencies),
            },
            message=f"发现 {len(dependencies)} 个包间依赖，{len(circular_deps)} 个循环依赖",
            confidence=0.8,
        )
    
    async def _analyze_package_boundaries(self, context: AgentContext) -> AgentResult:
        """分析包边界"""
        if not context.project_path:
            return AgentResult.error_result("未指定项目路径")
        
        subpackages = self._detect_subpackages(context.project_path)
        layers = self._package_analyzer.detect_layered_architecture(subpackages)
        violations = self._package_analyzer.analyze_package_boundaries(subpackages, layers)
        
        return AgentResult.success_result(
            data={
                "layers": [
                    {
                        "name": layer.name,
                        "packages": layer.packages,
                        "description": layer.description,
                        "allowed_dependencies": layer.allowed_dependencies,
                    }
                    for layer in layers
                ],
                "violations": violations,
                "total_violations": len(violations),
            },
            message=f"检测到 {len(layers)} 个架构层，{len(violations)} 个边界违规",
            confidence=0.75,
        )
    
    async def _calculate_package_metrics(self, context: AgentContext) -> AgentResult:
        """计算包级别指标"""
        if not context.project_path:
            return AgentResult.error_result("未指定项目路径")
        
        subpackages = self._detect_subpackages(context.project_path)
        metrics = self._package_analyzer.calculate_package_metrics(subpackages)
        
        return AgentResult.success_result(
            data={
                "metrics": [
                    {
                        "package": m.package_name,
                        "stability": m.stability,
                        "abstractness": m.abstractness,
                        "distance": m.distance,
                        "coupling": m.coupling,
                        "cohesion": m.cohesion,
                    }
                    for m in metrics
                ],
                "summary": {
                    "avg_stability": sum(m.stability for m in metrics) / len(metrics) if metrics else 0,
                    "avg_cohesion": sum(m.cohesion for m in metrics) / len(metrics) if metrics else 0,
                    "high_coupling_packages": [m.package_name for m in metrics if m.coupling > 0.7],
                    "unstable_packages": [m.package_name for m in metrics if m.stability < 0.3],
                },
            },
            message=f"计算了 {len(metrics)} 个包的指标",
            confidence=0.8,
        )