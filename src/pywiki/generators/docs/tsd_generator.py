"""
TSD (Technical Specification Document) 技术设计文档生成器
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
from pywiki.knowledge.design_decision import DesignDecisionAnalyzer
from pywiki.knowledge.tech_debt_detector import TechDebtDetector
from pywiki.insights.pattern_detector import DesignPatternDetector


class TSDGenerator(BaseDocGenerator):
    """TSD 技术设计文档生成器"""

    doc_type = DocType.TSD
    template_name = "tsd.md.j2"

    def __init__(
        self,
        language: Language = Language.ZH,
        template_dir: Optional[Path] = None,
    ):
        super().__init__(language, template_dir)

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成 TSD 文档"""
        try:
            tsd_data = await self._extract_tsd_data(context)
            
            if context.metadata.get("llm_client"):
                enhanced_data = await self._enhance_with_llm(
                    context,
                    tsd_data,
                    context.metadata["llm_client"]
                )
                tsd_data.update(enhanced_data)

            content = self.render_template(
                description=f"{context.project_name} 技术设计文档",
                design_decisions=tsd_data.get("design_decisions", []),
                tech_debt=tsd_data.get("tech_debt", []),
                patterns=tsd_data.get("patterns", []),
                implicit_knowledge=tsd_data.get("implicit_knowledge", []),
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message="TSD 文档生成成功",
                metadata={"tsd_data": tsd_data.get("summary", {})},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"生成失败: {str(e)}",
            )

    async def _extract_tsd_data(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取 TSD 数据"""
        tsd_data = {
            "design_decisions": [],
            "tech_debt": [],
            "patterns": [],
            "implicit_knowledge": [],
            "summary": {},
        }

        tsd_data["design_decisions"] = self._extract_design_decisions(context)
        tsd_data["tech_debt"] = self._extract_tech_debt(context)
        tsd_data["patterns"] = self._extract_patterns(context)
        tsd_data["implicit_knowledge"] = self._extract_implicit_knowledge(context)

        tsd_data["summary"] = {
            "design_decisions_count": len(tsd_data["design_decisions"]),
            "tech_debt_count": len(tsd_data["tech_debt"]),
            "patterns_count": len(tsd_data["patterns"]),
            "implicit_knowledge_count": len(tsd_data["implicit_knowledge"]),
        }

        return tsd_data

    def _extract_design_decisions(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取设计决策"""
        decisions = []

        try:
            analyzer = DesignDecisionAnalyzer()
            if context.parse_result and context.parse_result.modules:
                extracted = analyzer.analyze(context.parse_result.modules)
                decisions.extend([
                    {
                        "title": d.title,
                        "description": d.description,
                        "category": d.category.value if hasattr(d.category, 'value') else str(d.category),
                        "rationale": d.rationale,
                        "impact": d.impact,
                        "confidence": d.confidence,
                    }
                    for d in extracted
                ])
                decisions = decisions[:10]
        except Exception:
            pass

        if not decisions:
            decisions = self._extract_design_decisions_from_code(context)

        return decisions

    def _extract_design_decisions_from_code(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """从代码中提取设计决策"""
        decisions = []

        decision_keywords = [
            ("TODO", "待办事项"),
            ("FIXME", "需要修复"),
            ("HACK", "临时解决方案"),
            ("NOTE", "注意"),
            ("XXX", "警告"),
        ]

        if context.parse_result and context.parse_result.modules:
            for module in context.parse_result.modules:
                for cls in module.classes:
                    if cls.docstring:
                        for keyword, label in decision_keywords:
                            if keyword in cls.docstring:
                                decisions.append({
                                    "title": f"{cls.name} - {label}",
                                    "status": "open",
                                    "date": "",
                                    "decider": "",
                                    "context": module.name,
                                    "decision": cls.docstring.split("\n")[0],
                                    "consequences": "",
                                })

        return decisions[:10]

    def _extract_tech_debt(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取技术债务"""
        debts = []

        try:
            detector = TechDebtDetector()
            if context.parse_result and context.parse_result.modules:
                detected = detector.detect(context.parse_result.modules)
                debts = [
                    {
                        "name": d.name,
                        "severity": d.severity,
                        "location": d.location,
                        "description": d.description,
                        "suggestion": d.suggestion,
                    }
                    for d in detected[:15]
                ]
        except Exception:
            pass

        if not debts:
            debts = self._detect_simple_tech_debt(context)

        return debts

    def _detect_simple_tech_debt(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """简单检测技术债务"""
        debts = []

        debt_patterns = [
            ("TODO", "low", "待办事项"),
            ("FIXME", "high", "需要修复"),
            ("HACK", "medium", "临时解决方案"),
            ("deprecated", "medium", "已弃用"),
        ]

        if context.parse_result and context.parse_result.modules:
            for module in context.parse_result.modules:
                for cls in module.classes:
                    if cls.docstring:
                        doc_lower = cls.docstring.lower()
                        for pattern, severity, label in debt_patterns:
                            if pattern.lower() in doc_lower:
                                debts.append({
                                    "name": f"{cls.name} - {label}",
                                    "severity": severity,
                                    "location": f"{module.name}.{cls.name}",
                                    "description": cls.docstring.split("\n")[0][:100],
                                    "suggestion": "建议处理此技术债务",
                                })
                                break

                for func in module.functions:
                    if func.docstring:
                        doc_lower = func.docstring.lower()
                        for pattern, severity, label in debt_patterns:
                            if pattern.lower() in doc_lower:
                                debts.append({
                                    "name": f"{func.name} - {label}",
                                    "severity": severity,
                                    "location": f"{module.name}.{func.name}",
                                    "description": func.docstring.split("\n")[0][:100],
                                    "suggestion": "建议处理此技术债务",
                                })
                                break

        return debts[:15]

    def _extract_patterns(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取设计模式"""
        patterns = []

        try:
            detector = DesignPatternDetector()
            if context.parse_result and context.parse_result.modules:
                for module in context.parse_result.modules:
                    detected = detector.detect_from_module(module)
                    patterns.extend([
                        {
                            "name": p.pattern_name,
                            "type": p.category.value if hasattr(p.category, 'value') else str(p.category),
                            "location": p.location,
                            "description": p.description,
                            "participants": p.participants,
                        }
                        for p in detected
                    ])
                patterns = patterns[:10]
        except Exception:
            pass

        if not patterns:
            patterns = self._detect_simple_patterns(context)

        return patterns

    def _detect_simple_patterns(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """简单检测设计模式"""
        patterns = []

        pattern_indicators = {
            "Singleton": ["_instance", "get_instance", "__new__"],
            "Factory": ["factory", "create_", "build_"],
            "Builder": ["builder", "with_", "build()"],
            "Observer": ["observer", "subscribe", "notify", "listener"],
            "Strategy": ["strategy", "execute", "algorithm"],
            "Decorator": ["decorator", "wrapper", "__wrap__"],
            "Repository": ["repository", "find_", "save_", "delete_"],
            "Service": ["service", "process_", "handle_"],
        }

        if context.parse_result and context.parse_result.modules:
            for module in context.parse_result.modules:
                for cls in module.classes:
                    cls_lower = cls.name.lower()
                    method_names = [m.name.lower() for m in cls.methods]
                    
                    for pattern_name, indicators in pattern_indicators.items():
                        if any(ind in cls_lower for ind in indicators):
                            patterns.append({
                                "name": pattern_name,
                                "type": "structural" if pattern_name in ["Decorator", "Adapter", "Facade"] else "behavioral",
                                "location": f"{module.name}.{cls.name}",
                                "description": f"检测到 {pattern_name} 模式",
                                "participants": [cls.name],
                            })
                            break
                        
                        if any(any(ind in m for ind in indicators) for m in method_names):
                            patterns.append({
                                "name": pattern_name,
                                "type": "structural" if pattern_name in ["Decorator", "Adapter", "Facade"] else "behavioral",
                                "location": f"{module.name}.{cls.name}",
                                "description": f"检测到 {pattern_name} 模式特征",
                                "participants": [cls.name],
                            })
                            break

        return patterns[:10]

    def _extract_implicit_knowledge(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取隐式知识"""
        knowledge = []

        try:
            from pywiki.knowledge.implicit_knowledge import ImplicitKnowledgeExtractor
            extractor = ImplicitKnowledgeExtractor()
            if context.parse_result and context.parse_result.modules:
                for module in context.parse_result.modules:
                    extracted = extractor.extract_from_module(module)
                    knowledge.extend([
                        {
                            "title": k.title,
                            "category": k.category.value if hasattr(k.category, 'value') else str(k.category),
                            "source": k.source,
                            "content": k.content,
                        }
                        for k in extracted
                    ])
                knowledge = knowledge[:10]
        except Exception:
            pass

        if not knowledge:
            knowledge = self._extract_simple_implicit_knowledge(context)

        return knowledge

    def _extract_simple_implicit_knowledge(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """简单提取隐式知识"""
        knowledge = []

        if context.parse_result and context.parse_result.modules:
            for module in context.parse_result.modules:
                if module.docstring and len(module.docstring) > 50:
                    knowledge.append({
                        "title": f"{module.name} 设计意图",
                        "category": "设计意图",
                        "source": module.name,
                        "content": module.docstring.split("\n")[0],
                    })

                for cls in module.classes:
                    if cls.docstring and len(cls.docstring) > 50:
                        if "because" in cls.docstring.lower() or "因为" in cls.docstring:
                            knowledge.append({
                                "title": f"{cls.name} 设计原因",
                                "category": "设计决策",
                                "source": f"{module.name}.{cls.name}",
                                "content": cls.docstring.split("\n")[0],
                            })

        return knowledge[:10]

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        tsd_data: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强 TSD 文档"""
        import json

        enhanced = {}

        prompt = f"""基于以下技术设计信息，提供深入分析：

项目: {context.project_name}
设计决策数量: {len(tsd_data.get('design_decisions', []))}
技术债务数量: {len(tsd_data.get('tech_debt', []))}
设计模式数量: {len(tsd_data.get('patterns', []))}

请以 JSON 格式返回：
{{
    "architecture_quality": "架构质量评估（好/中/差）",
    "tech_debt_priority": ["优先处理的技术债务1", "优先处理的技术债务2"],
    "pattern_recommendations": ["设计模式建议1", "设计模式建议2"],
    "improvement_roadmap": ["改进路线图1", "改进路线图2"]
}}
"""

        try:
            response = await llm_client.agenerate(prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                result = json.loads(response[start:end+1])
                enhanced["architecture_quality"] = result.get("architecture_quality", "")
                enhanced["tech_debt_priority"] = result.get("tech_debt_priority", [])
                enhanced["pattern_recommendations"] = result.get("pattern_recommendations", [])
                enhanced["improvement_roadmap"] = result.get("improvement_roadmap", [])
        except Exception:
            pass

        return enhanced
