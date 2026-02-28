"""
隐形知识挖掘 Agent
基于 LLM 的智能分析，从代码中提取隐含的架构决策、设计模式、业务规则
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from pywiki.agents.base import BaseAgent, AgentContext, AgentResult, AgentPriority
from pywiki.insights.pattern_detector import DesignPatternDetector, DetectedPattern
from pywiki.knowledge.implicit_knowledge import ImplicitKnowledgeExtractor, ImplicitKnowledge, KnowledgeType
from pywiki.parsers.factory import ParserFactory


@dataclass
class KnowledgeInsight:
    """知识洞察"""
    category: str
    title: str
    description: str
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    suggestions: list[str] = field(default_factory=list)
    related_files: list[str] = field(default_factory=list)


class ImplicitKnowledgeAgent(BaseAgent):
    """隐形知识挖掘 Agent"""
    
    name = "implicit_knowledge_agent"
    description = "隐形知识挖掘专家 - 从代码中提取设计决策、架构模式、业务规则等隐性知识"
    priority = AgentPriority.HIGH
    
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._pattern_detector = DesignPatternDetector()
        self._knowledge_extractor = ImplicitKnowledgeExtractor()
        self._parser_factory = ParserFactory()
    
    def get_system_prompt(self) -> str:
        return """# 角色定义
你是一位资深的软件架构师和代码分析专家，擅长从代码中挖掘隐性知识，洞察设计意图和架构决策。

# 核心任务
从代码中提取以下类型的隐性知识：

## 1. 设计决策
- 为什么选择某种设计方式
- 技术选型的考量因素
- 架构风格的决策依据

## 2. 架构模式
- 使用的架构风格（分层、微服务、事件驱动等）
- 设计模式的应用（单例、工厂、观察者等）
- 模块间的协作方式

## 3. 业务规则
- 隐含在代码中的业务逻辑
- 数据验证和约束条件
- 业务流程和工作流

## 4. 技术债务
- 需要改进的代码问题
- 潜在的性能瓶颈
- 可维护性风险点

## 5. 性能考量
- 性能优化相关的决策
- 缓存策略
- 并发处理方式

## 6. 安全考量
- 安全相关的实现细节
- 权限控制机制
- 数据保护措施

# 置信度评估标准
- **0.9-1.0**: 有明确代码证据，逻辑清晰
- **0.7-0.9**: 有较强证据支持，推理合理
- **0.5-0.7**: 有一定证据，但存在其他解释可能
- **0.3-0.5**: 证据较弱，仅为推测
- **0.0-0.3**: 几乎无证据，纯猜测

# 输出规范
- 使用JSON格式输出
- 每条知识包含：类别、标题、描述、证据列表、置信度、建议
- 证据需引用具体代码位置或内容
- 建议应具有可操作性

请提供详细的分析，包括证据和置信度评分。"""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """执行隐形知识挖掘"""
        self.status = "running"
        
        try:
            insights = []
            
            if context.file_path:
                file_insights = await self._analyze_file(context.file_path)
                insights.extend(file_insights)
            
            if context.project_path:
                project_insights = await self._analyze_project(context.project_path)
                insights.extend(project_insights)
            
            if context.module_info:
                module_insights = self._analyze_module(context.module_info)
                insights.extend(module_insights)
            
            if context.query:
                query_insights = await self._answer_query(context.query, insights)
                insights.extend(query_insights)
            
            result = self._aggregate_results(insights)
            
            self._record_execution(context, result)
            self.status = "completed"
            
            return result
            
        except Exception as e:
            self.status = "error"
            return AgentResult.error_result(f"分析失败: {str(e)}")
    
    async def _analyze_file(self, file_path: Path) -> list[KnowledgeInsight]:
        """分析单个文件"""
        insights = []
        
        parser = self._parser_factory.get_parser(file_path)
        if not parser:
            return insights
        
        try:
            module_info = parser.parse_file(file_path)
            if not module_info:
                return insights
            
            module_insights = self._analyze_module(module_info)
            insights.extend(module_insights)
            
            if self.llm_client:
                llm_insights = await self._llm_enhanced_analysis(module_info, file_path)
                insights.extend(llm_insights)
            
        except Exception as e:
            insights.append(KnowledgeInsight(
                category="error",
                title="解析错误",
                description=f"无法解析文件 {file_path}: {str(e)}",
                confidence=0.0,
            ))
        
        return insights
    
    async def _analyze_project(self, project_path: Path) -> list[KnowledgeInsight]:
        """分析整个项目"""
        insights = []
        
        config_files = self._find_config_files(project_path)
        for config_file in config_files:
            config_insights = self._analyze_config_file(config_file)
            insights.extend(config_insights)
        
        dependency_insights = self._analyze_dependencies(project_path)
        insights.extend(dependency_insights)
        
        if self.llm_client:
            architecture_insights = await self._analyze_architecture_with_llm(project_path)
            insights.extend(architecture_insights)
        
        return insights
    
    def _analyze_module(self, module_info: Any) -> list[KnowledgeInsight]:
        """分析模块信息"""
        insights = []
        
        patterns = self._pattern_detector.detect_from_module(module_info)
        for pattern in patterns:
            insights.append(self._pattern_to_insight(pattern))
        
        knowledge_list = self._knowledge_extractor.extract_from_module(module_info)
        for knowledge in knowledge_list:
            insights.append(self._knowledge_to_insight(knowledge))
        
        for cls in module_info.classes:
            class_patterns = self._pattern_detector.detect_from_class(cls)
            for pattern in class_patterns:
                insights.append(self._pattern_to_insight(pattern))
            
            class_knowledge = self._knowledge_extractor.extract_from_class(cls)
            for knowledge in class_knowledge:
                insights.append(self._knowledge_to_insight(knowledge))
        
        for func in module_info.functions:
            func_knowledge = self._knowledge_extractor.extract_from_function(func)
            for knowledge in func_knowledge:
                insights.append(self._knowledge_to_insight(knowledge))
        
        return insights
    
    async def _llm_enhanced_analysis(
        self,
        module_info: Any,
        file_path: Path
    ) -> list[KnowledgeInsight]:
        """使用 LLM 增强分析"""
        insights = []
        
        code_summary = self._generate_code_summary(module_info)
        
        prompt = f"""分析以下代码文件，提取隐性知识：

文件: {file_path}
模块: {module_info.name}

代码摘要:
{code_summary}

请分析并返回 JSON 格式结果:
{{
    "design_decisions": [
        {{
            "title": "决策标题",
            "description": "详细描述",
            "evidence": ["证据1", "证据2"],
            "confidence": 0.85,
            "suggestions": ["建议1"]
        }}
    ],
    "architecture_patterns": [...],
    "business_rules": [...],
    "tech_debts": [...]
}}
"""
        
        try:
            response = await self.call_llm(prompt)
            parsed = json.loads(self._extract_json(response))
            
            for category, items in parsed.items():
                for item in items:
                    insights.append(KnowledgeInsight(
                        category=category,
                        title=item.get("title", ""),
                        description=item.get("description", ""),
                        evidence=item.get("evidence", []),
                        confidence=item.get("confidence", 0.5),
                        suggestions=item.get("suggestions", []),
                        related_files=[str(file_path)],
                    ))
        
        except Exception as e:
            pass
        
        return insights
    
    async def _analyze_architecture_with_llm(self, project_path: Path) -> list[KnowledgeInsight]:
        """使用 LLM 分析架构"""
        insights = []
        
        structure = self._get_project_structure(project_path)
        
        prompt = f"""分析以下项目结构，识别架构模式和设计决策：

项目路径: {project_path}

目录结构:
{structure}

请分析:
1. 项目采用的架构风格（如：分层架构、微服务、MVC等）
2. 模块划分原则和边界
3. 技术栈选择的原因
4. 可能的设计模式
5. 潜在的架构问题

返回 JSON 格式:
{{
    "architecture_style": "架构风格名称",
    "style_confidence": 0.85,
    "key_decisions": [...],
    "patterns": [...],
    "concerns": [...]
}}
"""
        
        try:
            response = await self.call_llm(prompt)
            parsed = json.loads(self._extract_json(response))
            
            if "architecture_style" in parsed:
                insights.append(KnowledgeInsight(
                    category="architecture_style",
                    title=f"架构风格: {parsed['architecture_style']}",
                    description=f"项目采用 {parsed['architecture_style']} 架构风格",
                    confidence=parsed.get("style_confidence", 0.5),
                ))
            
            for decision in parsed.get("key_decisions", []):
                insights.append(KnowledgeInsight(
                    category="design_decision",
                    title=decision.get("title", ""),
                    description=decision.get("description", ""),
                    evidence=decision.get("evidence", []),
                    confidence=decision.get("confidence", 0.5),
                ))
        
        except Exception:
            pass
        
        return insights
    
    async def _answer_query(self, query: str, existing_insights: list[KnowledgeInsight]) -> list[KnowledgeInsight]:
        """回答特定查询"""
        insights = []
        
        if not self.llm_client:
            return insights
        
        context = "\n".join([
            f"- {i.category}: {i.title} ({i.confidence:.2f})"
            for i in existing_insights[:10]
        ])
        
        prompt = f"""基于以下已发现的隐性知识，回答用户查询：

已发现的知识:
{context}

用户查询: {query}

请提供相关的洞察和建议。"""
        
        try:
            response = await self.call_llm(prompt)
            insights.append(KnowledgeInsight(
                category="query_response",
                title=f"查询: {query[:50]}...",
                description=response,
                confidence=0.7,
            ))
        except Exception:
            pass
        
        return insights
    
    def _pattern_to_insight(self, pattern: DetectedPattern) -> KnowledgeInsight:
        """将检测到的模式转换为洞察"""
        return KnowledgeInsight(
            category=f"pattern_{pattern.category.value}",
            title=f"设计模式: {pattern.pattern_name}",
            description=pattern.description,
            evidence=pattern.evidence,
            confidence=pattern.confidence,
            benefits=pattern.benefits,
            drawbacks=pattern.drawbacks,
            related_files=[pattern.location],
        )
    
    def _knowledge_to_insight(self, knowledge: ImplicitKnowledge) -> KnowledgeInsight:
        """将隐性知识转换为洞察"""
        return KnowledgeInsight(
            category=knowledge.knowledge_type.value,
            title=knowledge.title,
            description=knowledge.description,
            evidence=knowledge.evidence,
            confidence=knowledge.confidence,
            suggestions=knowledge.suggestions,
            related_files=[knowledge.location] if knowledge.location else [],
        )
    
    def _aggregate_results(self, insights: list[KnowledgeInsight]) -> AgentResult:
        """聚合分析结果"""
        if not insights:
            return AgentResult.success_result(
                data={},
                message="未发现隐性知识",
                confidence=0.0,
            )
        
        categorized = {}
        for insight in insights:
            if insight.category not in categorized:
                categorized[insight.category] = []
            categorized[insight.category].append(insight)
        
        avg_confidence = sum(i.confidence for i in insights) / len(insights)
        
        summary = {
            "total_insights": len(insights),
            "by_category": {
                cat: len(items) for cat, items in categorized.items()
            },
            "high_confidence_insights": [
                {
                    "category": i.category,
                    "title": i.title,
                    "confidence": i.confidence,
                }
                for i in insights if i.confidence >= 0.8
            ],
            "detailed_insights": [
                {
                    "category": i.category,
                    "title": i.title,
                    "description": i.description,
                    "evidence": i.evidence,
                    "confidence": i.confidence,
                    "suggestions": i.suggestions,
                    "related_files": i.related_files,
                }
                for i in sorted(insights, key=lambda x: x.confidence, reverse=True)
            ],
        }
        
        return AgentResult.success_result(
            data=summary,
            message=f"发现 {len(insights)} 条隐性知识，平均置信度: {avg_confidence:.2f}",
            confidence=avg_confidence,
            categorized=categorized,
        )
    
    def _find_config_files(self, project_path: Path) -> list[Path]:
        """查找配置文件"""
        config_files = []
        config_patterns = [
            "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
            "package.json", "tsconfig.json", "pom.xml", "build.gradle",
            "Dockerfile", "docker-compose.yml", ".github/workflows/*.yml",
        ]
        
        for pattern in config_patterns:
            config_files.extend(project_path.glob(pattern))
        
        return config_files
    
    def _analyze_config_file(self, config_file: Path) -> list[KnowledgeInsight]:
        """分析配置文件"""
        insights = []
        
        try:
            content = config_file.read_text(encoding="utf-8")
            
            if config_file.name == "pyproject.toml":
                if "[tool.poetry]" in content:
                    insights.append(KnowledgeInsight(
                        category="tech_stack",
                        title="使用 Poetry 管理依赖",
                        description="项目使用 Poetry 作为依赖管理和打包工具",
                        evidence=[f"配置文件: {config_file}"],
                        confidence=0.95,
                    ))
            
            elif config_file.name == "package.json":
                insights.append(KnowledgeInsight(
                    category="tech_stack",
                    title="Node.js 项目",
                    description="项目使用 Node.js/npm 生态",
                    evidence=[f"配置文件: {config_file}"],
                    confidence=0.95,
                ))
        
        except Exception:
            pass
        
        return insights
    
    def _analyze_dependencies(self, project_path: Path) -> list[KnowledgeInsight]:
        """分析项目依赖"""
        insights = []
        
        framework_indicators = {
            "fastapi": ("FastAPI", "高性能异步 Web 框架"),
            "django": ("Django", "全功能 Web 框架"),
            "flask": ("Flask", "轻量级 Web 框架"),
            "spring": ("Spring Boot", "Java 企业级框架"),
            "react": ("React", "前端 UI 库"),
            "vue": ("Vue.js", "渐进式前端框架"),
            "sqlalchemy": ("SQLAlchemy", "Python ORM"),
            "mybatis": ("MyBatis", "Java 持久层框架"),
        }
        
        return insights
    
    def _generate_code_summary(self, module_info: Any) -> str:
        """生成代码摘要"""
        lines = [
            f"模块: {module_info.name}",
            f"类数量: {len(module_info.classes)}",
            f"函数数量: {len(module_info.functions)}",
            f"导入数量: {len(module_info.imports)}",
            "",
            "类:",
        ]
        
        for cls in module_info.classes[:5]:
            lines.append(f"  - {cls.name} (继承: {', '.join(cls.bases)})")
            lines.append(f"    方法: {len(cls.methods)}, 属性: {len(cls.properties)}")
        
        lines.extend(["", "主要函数:"])
        for func in module_info.functions[:5]:
            lines.append(f"  - {func.name}({len(func.parameters)} 参数)")
        
        return "\n".join(lines)
    
    def _get_project_structure(self, project_path: Path, max_depth: int = 3) -> str:
        """获取项目结构"""
        lines = []
        
        def traverse(path: Path, depth: int = 0):
            if depth > max_depth:
                return
            
            indent = "  " * depth
            for item in sorted(path.iterdir()):
                if item.name.startswith(".") and item.name not in [".github", ".vscode"]:
                    continue
                
                if item.is_dir():
                    lines.append(f"{indent}{item.name}/")
                    traverse(item, depth + 1)
                elif depth < max_depth:
                    lines.append(f"{indent}{item.name}")
        
        traverse(project_path)
        return "\n".join(lines[:100])