"""
架构洞见 Agent
深度分析架构，提供健康度评估、可视化建议和优化建议
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from pywiki.agents.base import BaseAgent, AgentContext, AgentResult, AgentPriority
from pywiki.parsers.factory import ParserFactory


@dataclass
class ArchitectureMetric:
    """架构指标"""
    name: str
    score: float
    description: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArchitectureInsight:
    """架构洞察"""
    category: str
    title: str
    description: str
    severity: str
    suggestions: list[str] = field(default_factory=list)
    affected_files: list[str] = field(default_factory=list)


class ArchitectureAgent(BaseAgent):
    """架构洞见 Agent"""
    
    name = "architecture_agent"
    description = "架构分析专家 - 深度分析架构健康度，提供可视化建议和优化方案"
    priority = AgentPriority.HIGH
    
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._parser_factory = ParserFactory()
        self._module_cache: dict[str, Any] = {}
    
    def get_system_prompt(self) -> str:
        return """你是一个资深的软件架构师。
你的任务是：
1. 分析项目架构健康度
2. 识别架构问题和改进机会
3. 提供架构可视化建议
4. 推荐最佳实践和重构方案

请提供专业的架构分析和建议。"""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """执行架构分析"""
        self.status = "running"
        
        try:
            analysis_type = context.metadata.get("analysis_type", "full")
            
            if analysis_type == "full":
                result = await self._full_analysis(context)
            elif analysis_type == "health":
                result = await self._health_analysis(context)
            elif analysis_type == "dependencies":
                result = await self._dependency_analysis(context)
            elif analysis_type == "visualization":
                result = await self._visualization_analysis(context)
            elif analysis_type == "recommendations":
                result = await self._recommendations_analysis(context)
            else:
                result = AgentResult.error_result(f"未知分析类型: {analysis_type}")
            
            self._record_execution(context, result)
            self.status = "completed"
            return result
            
        except Exception as e:
            self.status = "error"
            return AgentResult.error_result(f"架构分析失败: {str(e)}")
    
    async def _full_analysis(self, context: AgentContext) -> AgentResult:
        """完整架构分析"""
        health_result = await self._health_analysis(context)
        dependency_result = await self._dependency_analysis(context)
        
        insights = []
        if health_result.data and "insights" in health_result.data:
            insights.extend(health_result.data["insights"])
        
        metrics = {}
        if health_result.data and "metrics" in health_result.data:
            metrics = health_result.data["metrics"]
        
        dependencies = {}
        if dependency_result.data:
            dependencies = dependency_result.data
        
        overall_score = sum(m["score"] for m in metrics.values()) / max(len(metrics), 1)
        
        if self.llm_client:
            llm_insights = await self._get_llm_architecture_insights(
                context, metrics, dependencies
            )
            insights.extend(llm_insights)
        
        return AgentResult.success_result(
            data={
                "overall_score": overall_score,
                "metrics": metrics,
                "dependencies": dependencies,
                "insights": insights,
                "recommendations": self._generate_recommendations(insights, metrics),
            },
            message=f"架构健康度评分: {overall_score:.2f}/1.0",
            confidence=0.85,
        )
    
    async def _health_analysis(self, context: AgentContext) -> AgentResult:
        """健康度分析"""
        modules = await self._load_project_modules(context)
        
        metrics = {}
        insights = []
        
        modularity_metric = self._calculate_modularity(modules)
        metrics["modularity"] = {
            "score": modularity_metric.score,
            "description": modularity_metric.description,
            "details": modularity_metric.details,
        }
        
        coupling_metric = self._calculate_coupling(modules)
        metrics["coupling"] = {
            "score": coupling_metric.score,
            "description": coupling_metric.description,
            "details": coupling_metric.details,
        }
        
        if coupling_metric.score < 0.5:
            insights.append(ArchitectureInsight(
                category="coupling",
                title="高耦合度",
                description="模块间耦合度过高，建议降低依赖",
                severity="high",
                suggestions=[
                    "使用依赖注入",
                    "引入接口抽象",
                    "考虑事件驱动架构",
                ],
            ))
        
        cohesion_metric = self._calculate_cohesion(modules)
        metrics["cohesion"] = {
            "score": cohesion_metric.score,
            "description": cohesion_metric.description,
            "details": cohesion_metric.details,
        }
        
        complexity_metric = self._calculate_complexity(modules)
        metrics["complexity"] = {
            "score": complexity_metric.score,
            "description": complexity_metric.description,
            "details": complexity_metric.details,
        }
        
        if complexity_metric.score < 0.4:
            insights.append(ArchitectureInsight(
                category="complexity",
                title="复杂度过高",
                description="部分模块复杂度过高，难以维护",
                severity="medium",
                suggestions=[
                    "拆分大型类",
                    "提取公共逻辑",
                    "简化条件分支",
                ],
            ))
        
        testability_metric = self._calculate_testability(modules)
        metrics["testability"] = {
            "score": testability_metric.score,
            "description": testability_metric.description,
            "details": testability_metric.details,
        }
        
        return AgentResult.success_result(
            data={
                "metrics": metrics,
                "insights": [
                    {
                        "category": i.category,
                        "title": i.title,
                        "description": i.description,
                        "severity": i.severity,
                        "suggestions": i.suggestions,
                    }
                    for i in insights
                ],
            },
            message=f"分析了 {len(modules)} 个模块的健康度",
            confidence=0.8,
        )
    
    async def _dependency_analysis(self, context: AgentContext) -> AgentResult:
        """依赖分析"""
        modules = await self._load_project_modules(context)
        
        dependencies = {
            "internal": {},
            "external": {},
            "circular": [],
        }
        
        for module in modules:
            module_deps = {
                "imports": [],
                "imported_by": [],
            }
            
            for imp in module.imports:
                if imp.module.startswith(".") or imp.module.startswith(module.name.split(".")[0]):
                    module_deps["imports"].append(imp.module)
                else:
                    if imp.module not in dependencies["external"]:
                        dependencies["external"][imp.module] = []
                    dependencies["external"][imp.module].append(module.name)
            
            dependencies["internal"][module.name] = module_deps
        
        circular_deps = self._detect_circular_dependencies(dependencies["internal"])
        dependencies["circular"] = circular_deps
        
        return AgentResult.success_result(
            data=dependencies,
            message=f"发现 {len(dependencies['external'])} 个外部依赖，{len(circular_deps)} 个循环依赖",
            confidence=0.85,
        )
    
    async def _visualization_analysis(self, context: AgentContext) -> AgentResult:
        """可视化分析"""
        modules = await self._load_project_modules(context)
        
        visualizations = {
            "c4_context": self._generate_c4_context(context),
            "c4_container": self._generate_c4_container(modules),
            "c4_component": self._generate_c4_component(modules),
            "dependency_graph": self._generate_dependency_graph(modules),
        }
        
        if self.llm_client:
            enhanced_diagrams = await self._enhance_diagrams_with_llm(context, modules)
            visualizations.update(enhanced_diagrams)
        
        return AgentResult.success_result(
            data=visualizations,
            message="生成了架构可视化图表",
            confidence=0.8,
        )
    
    async def _recommendations_analysis(self, context: AgentContext) -> AgentResult:
        """推荐分析"""
        health_result = await self._health_analysis(context)
        
        insights = health_result.data.get("insights", []) if health_result.data else []
        metrics = health_result.data.get("metrics", {}) if health_result.data else {}
        
        recommendations = self._generate_recommendations_from_insights(insights, metrics)
        
        if self.llm_client:
            llm_recommendations = await self._get_llm_recommendations(context, metrics)
            recommendations.extend(llm_recommendations)
        
        return AgentResult.success_result(
            data={
                "recommendations": recommendations,
                "priority_order": self._prioritize_recommendations(recommendations),
            },
            message=f"生成 {len(recommendations)} 条架构建议",
            confidence=0.8,
        )
    
    async def _load_project_modules(self, context: AgentContext) -> list[Any]:
        """加载项目模块"""
        modules = []
        
        if not context.project_path:
            return modules
        
        source_dirs = ["src", "lib", "app", context.project_path.name]
        
        for source_dir in source_dirs:
            src_path = context.project_path / source_dir
            if src_path.exists():
                for file_path in src_path.rglob("*.py"):
                    if "__pycache__" in str(file_path):
                        continue
                    
                    parser = self._parser_factory.get_parser(file_path)
                    if parser:
                        try:
                            module = parser.parse_file(file_path)
                            if module:
                                modules.append(module)
                        except Exception:
                            pass
        
        return modules
    
    def _calculate_modularity(self, modules: list[Any]) -> ArchitectureMetric:
        """计算模块化程度"""
        if not modules:
            return ArchitectureMetric("modularity", 0.0, "无模块")
        
        total_classes = sum(len(m.classes) for m in modules)
        avg_classes_per_module = total_classes / len(modules)
        
        score = max(0.0, 1.0 - (avg_classes_per_module - 5) / 20)
        
        return ArchitectureMetric(
            name="modularity",
            score=score,
            description=f"平均每个模块 {avg_classes_per_module:.1f} 个类",
            details={
                "total_modules": len(modules),
                "total_classes": total_classes,
                "avg_classes_per_module": avg_classes_per_module,
            },
        )
    
    def _calculate_coupling(self, modules: list[Any]) -> ArchitectureMetric:
        """计算耦合度"""
        if not modules:
            return ArchitectureMetric("coupling", 0.0, "无模块")
        
        total_imports = sum(len(m.imports) for m in modules)
        unique_imports = len(set(
            imp.module for m in modules for imp in m.imports
        ))
        
        if total_imports == 0:
            score = 1.0
        else:
            score = unique_imports / total_imports
        
        return ArchitectureMetric(
            name="coupling",
            score=score,
            description=f"共 {total_imports} 个导入，{unique_imports} 个唯一依赖",
            details={
                "total_imports": total_imports,
                "unique_imports": unique_imports,
            },
        )
    
    def _calculate_cohesion(self, modules: list[Any]) -> ArchitectureMetric:
        """计算内聚性"""
        if not modules:
            return ArchitectureMetric("cohesion", 0.0, "无模块")
        
        cohesion_scores = []
        for module in modules:
            if len(module.classes) > 1:
                related_classes = 0
                for cls in module.classes:
                    for other in module.classes:
                        if cls != other:
                            if any(base in other.bases for base in cls.bases):
                                related_classes += 1
                
                module_cohesion = related_classes / (len(module.classes) * (len(module.classes) - 1))
                cohesion_scores.append(module_cohesion)
        
        avg_cohesion = sum(cohesion_scores) / max(len(cohesion_scores), 1)
        
        return ArchitectureMetric(
            name="cohesion",
            score=avg_cohesion,
            description=f"平均内聚性: {avg_cohesion:.2f}",
            details={
                "module_count": len(cohesion_scores),
                "avg_cohesion": avg_cohesion,
            },
        )
    
    def _calculate_complexity(self, modules: list[Any]) -> ArchitectureMetric:
        """计算复杂度"""
        if not modules:
            return ArchitectureMetric("complexity", 0.0, "无模块")
        
        complex_classes = 0
        total_classes = 0
        
        for module in modules:
            for cls in module.classes:
                total_classes += 1
                method_count = len(cls.methods)
                if method_count > 10:
                    complex_classes += 1
        
        if total_classes == 0:
            score = 1.0
        else:
            score = 1.0 - (complex_classes / total_classes)
        
        return ArchitectureMetric(
            name="complexity",
            score=score,
            description=f"{complex_classes}/{total_classes} 个复杂类",
            details={
                "complex_classes": complex_classes,
                "total_classes": total_classes,
            },
        )
    
    def _calculate_testability(self, modules: list[Any]) -> ArchitectureMetric:
        """计算可测试性"""
        if not modules:
            return ArchitectureMetric("testability", 0.0, "无模块")
        
        testable_features = 0
        total_features = 0
        
        for module in modules:
            for func in module.functions:
                total_features += 1
                if len(func.parameters) <= 3:
                    testable_features += 1
            
            for cls in module.classes:
                for method in cls.methods:
                    total_features += 1
                    if not method.is_async and len(method.parameters) <= 3:
                        testable_features += 1
        
        if total_features == 0:
            score = 1.0
        else:
            score = testable_features / total_features
        
        return ArchitectureMetric(
            name="testability",
            score=score,
            description=f"{testable_features}/{total_features} 个可测试特性",
            details={
                "testable_features": testable_features,
                "total_features": total_features,
            },
        )
    
    def _detect_circular_dependencies(self, internal_deps: dict) -> list[list[str]]:
        """检测循环依赖"""
        circular = []
        visited = set()
        
        def dfs(node: str, path: list[str]):
            if node in path:
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                if cycle not in circular:
                    circular.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            deps = internal_deps.get(node, {}).get("imports", [])
            for dep in deps:
                if dep in internal_deps:
                    dfs(dep, path.copy())
        
        for module in internal_deps:
            dfs(module, [])
        
        return circular
    
    def _generate_c4_context(self, context: AgentContext) -> dict:
        """生成 C4 上下文图"""
        return {
            "type": "C4_Context",
            "title": f"{context.project_name or 'Project'} System Context",
            "elements": [
                {
                    "type": "System",
                    "name": context.project_name or "System",
                    "description": "主要系统",
                },
                {
                    "type": "User",
                    "name": "User",
                    "description": "系统用户",
                },
            ],
        }
    
    def _generate_c4_container(self, modules: list[Any]) -> dict:
        """生成 C4 容器图"""
        containers = []
        
        for module in modules[:10]:
            containers.append({
                "type": "Container",
                "name": module.name,
                "description": f"包含 {len(module.classes)} 个类",
                "technology": "Python",
            })
        
        return {
            "type": "C4_Container",
            "title": "Container Diagram",
            "elements": containers,
        }
    
    def _generate_c4_component(self, modules: list[Any]) -> dict:
        """生成 C4 组件图"""
        components = []
        
        for module in modules[:5]:
            for cls in module.classes[:5]:
                components.append({
                    "type": "Component",
                    "name": cls.name,
                    "description": f"类: {cls.name}",
                })
        
        return {
            "type": "C4_Component",
            "title": "Component Diagram",
            "elements": components,
        }
    
    def _generate_dependency_graph(self, modules: list[Any]) -> dict:
        """生成依赖关系图"""
        nodes = []
        edges = []
        
        for module in modules:
            nodes.append({
                "id": module.name,
                "label": module.name,
                "type": "module",
            })
            
            for imp in module.imports:
                if not imp.module.startswith("."):
                    edges.append({
                        "from": module.name,
                        "to": imp.module,
                        "type": "import",
                    })
        
        return {
            "type": "dependency_graph",
            "nodes": nodes,
            "edges": edges,
        }
    
    async def _get_llm_architecture_insights(
        self,
        context: AgentContext,
        metrics: dict,
        dependencies: dict
    ) -> list[ArchitectureInsight]:
        """使用 LLM 获取架构洞察"""
        insights = []
        
        prompt = f"""基于以下架构指标，提供架构洞察：

指标:
{json.dumps(metrics, indent=2, default=str)}

依赖:
外部依赖数: {len(dependencies.get('external', {}))}
循环依赖: {len(dependencies.get('circular', []))}

请分析并提供架构洞察，JSON 格式:
{{
    "insights": [
        {{
            "category": "类别",
            "title": "标题",
            "description": "描述",
            "severity": "high/medium/low",
            "suggestions": ["建议1", "建议2"]
        }}
    ]
}}
"""
        
        try:
            response = await self.call_llm(prompt)
            parsed = json.loads(self._extract_json(response))
            
            for insight_data in parsed.get("insights", []):
                insights.append(ArchitectureInsight(
                    category=insight_data.get("category", "general"),
                    title=insight_data.get("title", ""),
                    description=insight_data.get("description", ""),
                    severity=insight_data.get("severity", "low"),
                    suggestions=insight_data.get("suggestions", []),
                ))
        except Exception:
            pass
        
        return insights
    
    async def _enhance_diagrams_with_llm(
        self,
        context: AgentContext,
        modules: list[Any]
    ) -> dict:
        """使用 LLM 增强图表"""
        return {}
    
    async def _get_llm_recommendations(
        self,
        context: AgentContext,
        metrics: dict
    ) -> list[dict]:
        """使用 LLM 获取推荐"""
        recommendations = []
        
        prompt = f"""基于以下架构指标，提供改进建议：

指标:
{json.dumps(metrics, indent=2, default=str)}

请提供具体的架构改进建议，JSON 格式:
{{
    "recommendations": [
        {{
            "title": "建议标题",
            "description": "详细描述",
            "priority": "high/medium/low",
            "effort": "high/medium/low",
            "impact": "high/medium/low"
        }}
    ]
}}
"""
        
        try:
            response = await self.call_llm(prompt)
            parsed = json.loads(self._extract_json(response))
            recommendations = parsed.get("recommendations", [])
        except Exception:
            pass
        
        return recommendations
    
    def _generate_recommendations(
        self,
        insights: list[ArchitectureInsight],
        metrics: dict
    ) -> list[dict]:
        """生成推荐"""
        recommendations = []
        
        for insight in insights:
            if isinstance(insight, dict):
                recommendations.append({
                    "title": insight.get("title", ""),
                    "description": insight.get("description", ""),
                    "severity": insight.get("severity", "low"),
                    "suggestions": insight.get("suggestions", []),
                })
            else:
                recommendations.append({
                    "title": insight.title,
                    "description": insight.description,
                    "severity": insight.severity,
                    "suggestions": insight.suggestions,
                })
        
        return recommendations
    
    def _generate_recommendations_from_insights(
        self,
        insights: list[dict],
        metrics: dict
    ) -> list[dict]:
        """从洞察生成推荐"""
        recommendations = []
        
        for insight in insights:
            recommendations.append({
                "title": insight.get("title", ""),
                "description": insight.get("description", ""),
                "priority": insight.get("severity", "low"),
                "suggestions": insight.get("suggestions", []),
            })
        
        return recommendations
    
    def _prioritize_recommendations(self, recommendations: list[dict]) -> list[str]:
        """优先排序推荐"""
        priority_order = {"high": 0, "medium": 1, "low": 2}
        
        sorted_recs = sorted(
            recommendations,
            key=lambda x: priority_order.get(x.get("priority", "low"), 3)
        )
        
        return [r.get("title", "") for r in sorted_recs]