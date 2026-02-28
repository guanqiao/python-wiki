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
                message=self.labels.get("tsd_doc_success", "TSD documentation generated successfully"),
                metadata={"tsd_data": tsd_data.get("summary", {})},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"{self.labels.get('generation_failed', 'Generation failed')}: {str(e)}",
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

        project_language = context.project_language or context.detect_project_language()

        tsd_data["design_decisions"] = self._extract_design_decisions(context, project_language)
        tsd_data["tech_debt"] = self._extract_tech_debt(context, project_language)
        tsd_data["patterns"] = self._extract_patterns(context, project_language)
        tsd_data["implicit_knowledge"] = self._extract_implicit_knowledge(context, project_language)

        tsd_data["summary"] = {
            "design_decisions_count": len(tsd_data["design_decisions"]),
            "tech_debt_count": len(tsd_data["tech_debt"]),
            "patterns_count": len(tsd_data["patterns"]),
            "implicit_knowledge_count": len(tsd_data["implicit_knowledge"]),
            "project_language": project_language,
        }

        return tsd_data

    def _extract_design_decisions(self, context: DocGeneratorContext, project_language: str) -> list[dict[str, Any]]:
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
            decisions = self._extract_design_decisions_from_code(context, project_language)

        return decisions

    def _extract_design_decisions_from_code(self, context: DocGeneratorContext, project_language: str) -> list[dict[str, Any]]:
        """从代码中提取设计决策"""
        decisions = []

        decision_keywords = [
            ("TODO", "待办事项"),
            ("FIXME", "需要修复"),
            ("HACK", "临时解决方案"),
            ("NOTE", "注意"),
            ("XXX", "警告"),
            ("@deprecated", "已弃用"),
        ]

        if project_language == "java":
            decision_keywords.extend([
                ("@Deprecated", "已弃用"),
            ])
        elif project_language == "typescript":
            decision_keywords.extend([
                ("@deprecated", "已弃用"),
            ])

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

                    annotations = getattr(cls, 'annotations', []) or getattr(cls, 'decorators', [])
                    for annotation in annotations:
                        for keyword, label in decision_keywords:
                            if keyword in annotation:
                                decisions.append({
                                    "title": f"{cls.name} - {label}",
                                    "status": "open",
                                    "date": "",
                                    "decider": "",
                                    "context": module.name,
                                    "decision": f"注解: {annotation}",
                                    "consequences": "",
                                })

        return decisions[:10]

    def _extract_tech_debt(self, context: DocGeneratorContext, project_language: str) -> list[dict[str, Any]]:
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
            debts = self._detect_simple_tech_debt(context, project_language)

        return debts

    def _detect_simple_tech_debt(self, context: DocGeneratorContext, project_language: str) -> list[dict[str, Any]]:
        """简单检测技术债务"""
        debts = []

        debt_patterns = [
            ("TODO", "low", "待办事项"),
            ("FIXME", "high", "需要修复"),
            ("HACK", "medium", "临时解决方案"),
            ("deprecated", "medium", "已弃用"),
        ]

        if project_language == "java":
            debt_patterns.extend([
                ("@Deprecated", "high", "已弃用"),
            ])
        elif project_language == "typescript":
            debt_patterns.extend([
                ("@deprecated", "medium", "已弃用"),
            ])

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

                    annotations = getattr(cls, 'annotations', []) or getattr(cls, 'decorators', [])
                    for annotation in annotations:
                        for pattern, severity, label in debt_patterns:
                            if pattern in annotation:
                                debts.append({
                                    "name": f"{cls.name} - {label}",
                                    "severity": severity,
                                    "location": f"{module.name}.{cls.name}",
                                    "description": f"注解: {annotation}",
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

    def _extract_patterns(self, context: DocGeneratorContext, project_language: str) -> list[dict[str, Any]]:
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
            if project_language == "java":
                patterns = self._extract_java_patterns(context)
            elif project_language == "typescript":
                patterns = self._extract_typescript_patterns(context)
            else:
                patterns = self._detect_simple_patterns(context)

        return patterns

    def _extract_java_patterns(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取 Java 设计模式"""
        patterns = []

        spring_annotations = {
            "@Service": ("Service Layer", "业务服务层模式"),
            "@Repository": ("Repository", "数据访问层模式"),
            "@Controller": ("Controller", "控制器模式"),
            "@RestController": ("REST Controller", "REST 控制器模式"),
            "@Component": ("Component", "组件模式"),
            "@Configuration": ("Configuration", "配置模式"),
            "@Bean": ("Factory Method", "工厂方法模式"),
            "@Autowired": ("Dependency Injection", "依赖注入模式"),
            "@Qualifier": ("Dependency Injection", "依赖注入模式"),
        }

        jpa_annotations = {
            "@Entity": ("Active Record", "活动记录模式"),
            "@Table": ("Table Data Gateway", "表数据入口模式"),
            "@Id": ("Identity Field", "标识字段模式"),
            "@GeneratedValue": ("Identity Field", "标识字段模式"),
            "@OneToMany": ("Association Mapping", "关联映射模式"),
            "@ManyToOne": ("Association Mapping", "关联映射模式"),
            "@ManyToMany": ("Association Mapping", "关联映射模式"),
            "@OneToOne": ("Association Mapping", "关联映射模式"),
        }

        mybatis_annotations = {
            "@Mapper": ("Data Mapper", "数据映射器模式"),
            "@Select": ("Table Data Gateway", "表数据入口模式"),
            "@Insert": ("Table Data Gateway", "表数据入口模式"),
            "@Update": ("Table Data Gateway", "表数据入口模式"),
            "@Delete": ("Table Data Gateway", "表数据入口模式"),
        }

        naming_patterns = {
            "Service": ("Service Layer", "业务服务层模式"),
            "ServiceImpl": ("Service Layer", "业务服务层模式"),
            "Repository": ("Repository", "数据仓库模式"),
            "Dao": ("DAO", "数据访问对象模式"),
            "Controller": ("Controller", "控制器模式"),
            "Factory": ("Factory", "工厂模式"),
            "Builder": ("Builder", "建造者模式"),
            "Singleton": ("Singleton", "单例模式"),
            "Strategy": ("Strategy", "策略模式"),
            "Observer": ("Observer", "观察者模式"),
            "Adapter": ("Adapter", "适配器模式"),
            "Decorator": ("Decorator", "装饰器模式"),
            "Proxy": ("Proxy", "代理模式"),
            "Facade": ("Facade", "外观模式"),
            "Util": ("Utility", "工具类模式"),
            "Helper": ("Helper", "辅助类模式"),
            "Config": ("Configuration", "配置模式"),
            "Manager": ("Manager", "管理器模式"),
            "Handler": ("Handler", "处理器模式"),
            "Listener": ("Observer", "监听器模式"),
        }

        if not context.parse_result or not context.parse_result.modules:
            return patterns

        for module in context.parse_result.modules:
            for cls in module.classes:
                annotations = getattr(cls, 'annotations', []) or getattr(cls, 'decorators', [])
                detected_patterns = set()

                for annotation in annotations:
                    for ann_name, (pattern_name, description) in spring_annotations.items():
                        if ann_name in annotation and pattern_name not in detected_patterns:
                            patterns.append({
                                "name": pattern_name,
                                "type": "architectural",
                                "location": f"{module.name}.{cls.name}",
                                "description": f"{description} (通过 {ann_name} 注解)",
                                "participants": [cls.name],
                            })
                            detected_patterns.add(pattern_name)

                    for ann_name, (pattern_name, description) in jpa_annotations.items():
                        if ann_name in annotation and pattern_name not in detected_patterns:
                            patterns.append({
                                "name": pattern_name,
                                "type": "data_access",
                                "location": f"{module.name}.{cls.name}",
                                "description": f"{description} (通过 {ann_name} 注解)",
                                "participants": [cls.name],
                            })
                            detected_patterns.add(pattern_name)

                    for ann_name, (pattern_name, description) in mybatis_annotations.items():
                        if ann_name in annotation and pattern_name not in detected_patterns:
                            patterns.append({
                                "name": pattern_name,
                                "type": "data_access",
                                "location": f"{module.name}.{cls.name}",
                                "description": f"{description} (通过 {ann_name} 注解)",
                                "participants": [cls.name],
                            })
                            detected_patterns.add(pattern_name)

                for suffix, (pattern_name, description) in naming_patterns.items():
                    if cls.name.endswith(suffix) and pattern_name not in detected_patterns:
                        patterns.append({
                            "name": pattern_name,
                            "type": "structural" if suffix in ["Adapter", "Decorator", "Proxy", "Facade"] else "behavioral",
                            "location": f"{module.name}.{cls.name}",
                            "description": f"{description} (通过命名约定)",
                            "participants": [cls.name],
                        })
                        detected_patterns.add(pattern_name)

                method_names = [m.name for m in cls.methods]
                if "getInstance" in method_names or "instance" in method_names:
                    if "Singleton" not in detected_patterns:
                        patterns.append({
                            "name": "Singleton",
                            "type": "creational",
                            "location": f"{module.name}.{cls.name}",
                            "description": "单例模式 (通过 getInstance 方法)",
                            "participants": [cls.name],
                        })
                        detected_patterns.add("Singleton")

                if any(m.startswith("create") or m.startswith("build") for m in method_names):
                    if "Factory" not in detected_patterns and "Builder" not in detected_patterns:
                        patterns.append({
                            "name": "Factory/Builder",
                            "type": "creational",
                            "location": f"{module.name}.{cls.name}",
                            "description": "工厂/建造者模式 (通过 create/build 方法)",
                            "participants": [cls.name],
                        })

        return patterns[:15]

    def _extract_typescript_patterns(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取 TypeScript 设计模式"""
        patterns = []

        nestjs_decorators = {
            "@Controller": ("Controller", "控制器模式"),
            "@Service": ("Service Layer", "业务服务层模式"),
            "@Injectable": ("Dependency Injection", "依赖注入模式"),
            "@Module": ("Module", "模块模式"),
            "@Get": ("Route Handler", "路由处理器模式"),
            "@Post": ("Route Handler", "路由处理器模式"),
            "@Put": ("Route Handler", "路由处理器模式"),
            "@Delete": ("Route Handler", "路由处理器模式"),
            "@Patch": ("Route Handler", "路由处理器模式"),
            "@Body": ("Parameter Binding", "参数绑定模式"),
            "@Param": ("Parameter Binding", "参数绑定模式"),
            "@Query": ("Parameter Binding", "参数绑定模式"),
            "@Headers": ("Parameter Binding", "参数绑定模式"),
        }

        typeorm_decorators = {
            "@Entity": ("Active Record", "活动记录模式"),
            "@Table": ("Table Data Gateway", "表数据入口模式"),
            "@Column": ("Field Mapping", "字段映射模式"),
            "@PrimaryGeneratedColumn": ("Identity Field", "标识字段模式"),
            "@PrimaryColumn": ("Identity Field", "标识字段模式"),
            "@ManyToOne": ("Association Mapping", "关联映射模式"),
            "@OneToMany": ("Association Mapping", "关联映射模式"),
            "@ManyToMany": ("Association Mapping", "关联映射模式"),
            "@OneToOne": ("Association Mapping", "关联映射模式"),
            "@JoinColumn": ("Foreign Key Mapping", "外键映射模式"),
            "@JoinTable": ("Association Table", "关联表模式"),
        }

        prisma_decorators = {
            "@model": ("Active Record", "活动记录模式"),
            "@map": ("Field Mapping", "字段映射模式"),
            "@id": ("Identity Field", "标识字段模式"),
            "@default": ("Default Value", "默认值模式"),
            "@relation": ("Association Mapping", "关联映射模式"),
            "@unique": ("Unique Constraint", "唯一约束模式"),
            "@index": ("Index", "索引模式"),
        }

        naming_patterns = {
            "Service": ("Service Layer", "业务服务层模式"),
            "Controller": ("Controller", "控制器模式"),
            "Repository": ("Repository", "数据仓库模式"),
            "Factory": ("Factory", "工厂模式"),
            "Builder": ("Builder", "建造者模式"),
            "Singleton": ("Singleton", "单例模式"),
            "Strategy": ("Strategy", "策略模式"),
            "Observer": ("Observer", "观察者模式"),
            "Adapter": ("Adapter", "适配器模式"),
            "Decorator": ("Decorator", "装饰器模式"),
            "Proxy": ("Proxy", "代理模式"),
            "Facade": ("Facade", "外观模式"),
            "Middleware": ("Middleware", "中间件模式"),
            "Guard": ("Guard", "守卫模式"),
            "Interceptor": ("Interceptor", "拦截器模式"),
            "Pipe": ("Pipe", "管道模式"),
            "Filter": ("Filter", "过滤器模式"),
            "Hook": ("Hook", "钩子模式"),
            "Util": ("Utility", "工具类模式"),
            "Helper": ("Helper", "辅助类模式"),
            "Config": ("Configuration", "配置模式"),
            "Context": ("Context", "上下文模式"),
            "Provider": ("Provider", "提供者模式"),
        }

        if not context.parse_result or not context.parse_result.modules:
            return patterns

        for module in context.parse_result.modules:
            for cls in module.classes:
                decorators = getattr(cls, 'decorators', []) or getattr(cls, 'annotations', [])
                detected_patterns = set()

                for decorator in decorators:
                    for dec_name, (pattern_name, description) in nestjs_decorators.items():
                        if dec_name in decorator and pattern_name not in detected_patterns:
                            patterns.append({
                                "name": pattern_name,
                                "type": "architectural",
                                "location": f"{module.name}.{cls.name}",
                                "description": f"{description} (通过 {dec_name} 装饰器)",
                                "participants": [cls.name],
                            })
                            detected_patterns.add(pattern_name)

                    for dec_name, (pattern_name, description) in typeorm_decorators.items():
                        if dec_name in decorator and pattern_name not in detected_patterns:
                            patterns.append({
                                "name": pattern_name,
                                "type": "data_access",
                                "location": f"{module.name}.{cls.name}",
                                "description": f"{description} (通过 {dec_name} 装饰器)",
                                "participants": [cls.name],
                            })
                            detected_patterns.add(pattern_name)

                    for dec_name, (pattern_name, description) in prisma_decorators.items():
                        if dec_name in decorator and pattern_name not in detected_patterns:
                            patterns.append({
                                "name": pattern_name,
                                "type": "data_access",
                                "location": f"{module.name}.{cls.name}",
                                "description": f"{description} (通过 {dec_name} 装饰器)",
                                "participants": [cls.name],
                            })
                            detected_patterns.add(pattern_name)

                for suffix, (pattern_name, description) in naming_patterns.items():
                    if cls.name.endswith(suffix) and pattern_name not in detected_patterns:
                        patterns.append({
                            "name": pattern_name,
                            "type": "structural" if suffix in ["Adapter", "Decorator", "Proxy", "Facade"] else "behavioral",
                            "location": f"{module.name}.{cls.name}",
                            "description": f"{description} (通过命名约定)",
                            "participants": [cls.name],
                        })
                        detected_patterns.add(pattern_name)

                method_names = [m.name for m in cls.methods]
                if "getInstance" in method_names or "instance" in method_names:
                    if "Singleton" not in detected_patterns:
                        patterns.append({
                            "name": "Singleton",
                            "type": "creational",
                            "location": f"{module.name}.{cls.name}",
                            "description": "单例模式 (通过 getInstance 方法)",
                            "participants": [cls.name],
                        })
                        detected_patterns.add("Singleton")

                if any(m.startswith("create") or m.startswith("build") for m in method_names):
                    if "Factory" not in detected_patterns and "Builder" not in detected_patterns:
                        patterns.append({
                            "name": "Factory/Builder",
                            "type": "creational",
                            "location": f"{module.name}.{cls.name}",
                            "description": "工厂/建造者模式 (通过 create/build 方法)",
                            "participants": [cls.name],
                        })

            for func in module.functions:
                func_lower = func.name.lower()
                if "middleware" in func_lower:
                    patterns.append({
                        "name": "Middleware",
                        "type": "structural",
                        "location": f"{module.name}.{func.name}",
                        "description": "中间件模式 (函数式中间件)",
                        "participants": [func.name],
                    })
                elif "guard" in func_lower:
                    patterns.append({
                        "name": "Guard",
                        "type": "structural",
                        "location": f"{module.name}.{func.name}",
                        "description": "守卫模式 (函数式守卫)",
                        "participants": [func.name],
                    })
                elif "interceptor" in func_lower:
                    patterns.append({
                        "name": "Interceptor",
                        "type": "structural",
                        "location": f"{module.name}.{func.name}",
                        "description": "拦截器模式 (函数式拦截器)",
                        "participants": [func.name],
                    })

        return patterns[:15]

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

    def _extract_implicit_knowledge(self, context: DocGeneratorContext, project_language: str) -> list[dict[str, Any]]:
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
            knowledge = self._extract_simple_implicit_knowledge(context, project_language)

        return knowledge

    def _extract_simple_implicit_knowledge(self, context: DocGeneratorContext, project_language: str) -> list[dict[str, Any]]:
        """简单提取隐式知识"""
        knowledge = []

        design_keywords = {
            "python": ["because", "since", "reason", "设计", "原因", "注意", "警告", "重要"],
            "java": ["because", "since", "reason", "@deprecated", "设计", "原因", "注意", "警告", "重要", "NOTE:", "WARNING:"],
            "typescript": ["because", "since", "reason", "@deprecated", "设计", "原因", "注意", "警告", "重要", "NOTE:", "WARNING:"],
        }

        keywords = design_keywords.get(project_language, design_keywords["python"])

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
                        doc_lower = cls.docstring.lower()
                        for keyword in keywords:
                            if keyword.lower() in doc_lower:
                                knowledge.append({
                                    "title": f"{cls.name} 设计原因",
                                    "category": "设计决策",
                                    "source": f"{module.name}.{cls.name}",
                                    "content": cls.docstring.split("\n")[0],
                                })
                                break

                    annotations = getattr(cls, 'annotations', []) or getattr(cls, 'decorators', [])
                    for annotation in annotations:
                        if "@Deprecated" in annotation or "@deprecated" in annotation:
                            knowledge.append({
                                "title": f"{cls.name} 已弃用",
                                "category": "设计决策",
                                "source": f"{module.name}.{cls.name}",
                                "content": f"该类已被标记为弃用: {annotation}",
                            })

                for func in module.functions:
                    if func.docstring and len(func.docstring) > 50:
                        doc_lower = func.docstring.lower()
                        for keyword in keywords:
                            if keyword.lower() in doc_lower:
                                knowledge.append({
                                    "title": f"{func.name} 设计原因",
                                    "category": "设计决策",
                                    "source": f"{module.name}.{func.name}",
                                    "content": func.docstring.split("\n")[0],
                                })
                                break

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

        if self.language == Language.ZH:
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

请务必使用中文回答。"""
        else:
            prompt = f"""Based on the following technical design information, provide in-depth analysis:

Project: {context.project_name}
Design Decisions: {len(tsd_data.get('design_decisions', []))}
Technical Debt Items: {len(tsd_data.get('tech_debt', []))}
Design Patterns: {len(tsd_data.get('patterns', []))}

Please return in JSON format:
{{
    "architecture_quality": "Architecture quality assessment (good/medium/poor)",
    "tech_debt_priority": ["priority tech debt1", "priority tech debt2"],
    "pattern_recommendations": ["pattern recommendation1", "pattern recommendation2"],
    "improvement_roadmap": ["improvement roadmap1", "improvement roadmap2"]
}}

Please respond in English."""

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
