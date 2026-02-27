"""
隐性知识文档生成器
从代码中提取隐含的架构决策、设计模式、业务规则、编码规范等
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


@dataclass
class CodingConvention:
    """编码规范"""
    category: str
    name: str
    description: str
    examples: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)


@dataclass
class ImplicitKnowledge:
    """隐性知识"""
    category: str
    title: str
    description: str
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    suggestions: list[str] = field(default_factory=list)


class ImplicitKnowledgeGenerator(BaseDocGenerator):
    """隐性知识文档生成器"""

    doc_type = DocType.TSD
    template_name = "tsd.md.j2"

    def __init__(self, language: Language = Language.ZH, template_dir: Optional[Path] = None):
        super().__init__(language, template_dir)

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成隐性知识文档"""
        try:
            knowledge_data = self._extract_implicit_knowledge(context)
            
            if context.metadata.get("llm_client"):
                enhanced_data = await self._enhance_with_llm(
                    context,
                    knowledge_data,
                    context.metadata["llm_client"]
                )
                knowledge_data.update(enhanced_data)

            content = self.render_template(
                description=f"{context.project_name} 隐性知识文档",
                design_decisions=knowledge_data.get("design_decisions", []),
                tech_debt=knowledge_data.get("tech_debt", []),
                design_patterns=knowledge_data.get("design_patterns", []),
                coding_conventions=knowledge_data.get("coding_conventions", []),
                business_rules=knowledge_data.get("business_rules", []),
                performance_considerations=knowledge_data.get("performance_considerations", []),
                security_considerations=knowledge_data.get("security_considerations", []),
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message="隐性知识文档生成成功",
                metadata={"knowledge_data": knowledge_data.get("summary", {})},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"生成失败: {str(e)}",
            )

    def _extract_implicit_knowledge(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取隐性知识"""
        knowledge_data = {
            "design_decisions": [],
            "tech_debt": [],
            "design_patterns": [],
            "coding_conventions": [],
            "business_rules": [],
            "performance_considerations": [],
            "security_considerations": [],
            "summary": {},
        }

        if not context.parse_result or not context.parse_result.modules:
            return knowledge_data

        knowledge_data["design_patterns"] = self._detect_design_patterns(context)
        knowledge_data["tech_debt"] = self._detect_tech_debt(context)
        knowledge_data["coding_conventions"] = self._detect_coding_conventions(context)
        knowledge_data["design_decisions"] = self._detect_design_decisions(context)
        knowledge_data["business_rules"] = self._detect_business_rules(context)
        knowledge_data["security_considerations"] = self._detect_security_patterns(context)
        knowledge_data["performance_considerations"] = self._detect_performance_patterns(context)

        knowledge_data["summary"] = {
            "total_patterns": len(knowledge_data["design_patterns"]),
            "total_tech_debt": len(knowledge_data["tech_debt"]),
            "total_conventions": len(knowledge_data["coding_conventions"]),
            "total_decisions": len(knowledge_data["design_decisions"]),
        }

        return knowledge_data

    def _detect_design_patterns(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """检测设计模式"""
        patterns = []
        detected = set()

        for module in context.parse_result.modules:
            for cls in module.classes:
                pattern = self._detect_class_pattern(cls, module.name)
                if pattern and pattern["name"] not in detected:
                    patterns.append(pattern)
                    detected.add(pattern["name"])

        return patterns[:20]

    def _detect_class_pattern(self, cls: Any, module_name: str) -> Optional[dict[str, Any]]:
        """检测类的设计模式"""
        class_name = cls.name.lower()
        bases = [b.lower() for b in cls.bases]
        
        if any(name in class_name for name in ["singleton", "single"]):
            return {
                "name": "Singleton",
                "description": "单例模式 - 确保类只有一个实例",
                "location": f"{module_name}.{cls.name}",
                "confidence": 0.9,
            }
        
        if any(name in class_name for name in ["factory", "builder", "creator"]):
            return {
                "name": "Factory/Builder",
                "description": "工厂/建造者模式 - 创建对象的接口",
                "location": f"{module_name}.{cls.name}",
                "confidence": 0.85,
            }
        
        if any(name in class_name for name in ["adapter", "wrapper"]):
            return {
                "name": "Adapter",
                "description": "适配器模式 - 转换接口",
                "location": f"{module_name}.{cls.name}",
                "confidence": 0.85,
            }
        
        if any(name in class_name for name in ["observer", "listener", "handler", "callback"]):
            return {
                "name": "Observer",
                "description": "观察者模式 - 事件通知机制",
                "location": f"{module_name}.{cls.name}",
                "confidence": 0.85,
            }
        
        if any(name in class_name for name in ["strategy", "policy"]):
            return {
                "name": "Strategy",
                "description": "策略模式 - 可替换的算法族",
                "location": f"{module_name}.{cls.name}",
                "confidence": 0.85,
            }
        
        if any(name in class_name for name in ["decorator", "wrapper"]):
            return {
                "name": "Decorator",
                "description": "装饰器模式 - 动态添加功能",
                "location": f"{module_name}.{cls.name}",
                "confidence": 0.85,
            }
        
        if any(name in class_name for name in ["proxy"]):
            return {
                "name": "Proxy",
                "description": "代理模式 - 控制对象访问",
                "location": f"{module_name}.{cls.name}",
                "confidence": 0.85,
            }
        
        if any(name in class_name for name in ["repository", "repo"]):
            return {
                "name": "Repository",
                "description": "仓储模式 - 数据访问抽象",
                "location": f"{module_name}.{cls.name}",
                "confidence": 0.9,
            }
        
        if any(name in class_name for name in ["service"]):
            return {
                "name": "Service Layer",
                "description": "服务层模式 - 业务逻辑封装",
                "location": f"{module_name}.{cls.name}",
                "confidence": 0.8,
            }
        
        if any(base in ["exception", "error"] for base in bases):
            return {
                "name": "Custom Exception",
                "description": "自定义异常 - 领域特定错误处理",
                "location": f"{module_name}.{cls.name}",
                "confidence": 0.95,
            }
        
        return None

    def _detect_tech_debt(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """检测技术债务"""
        tech_debt = []
        debt_patterns = {
            "TODO": {"severity": "low", "description": "待办事项"},
            "FIXME": {"severity": "medium", "description": "需要修复的问题"},
            "HACK": {"severity": "high", "description": "临时解决方案"},
            "XXX": {"severity": "high", "description": "危险代码"},
            "BUG": {"severity": "critical", "description": "已知 Bug"},
            "DEPRECATED": {"severity": "medium", "description": "已废弃代码"},
        }

        for module in context.parse_result.modules:
            if module.docstring:
                for pattern, info in debt_patterns.items():
                    if pattern in module.docstring.upper():
                        tech_debt.append({
                            "type": pattern,
                            "severity": info["severity"],
                            "description": info["description"],
                            "location": module.name,
                            "content": module.docstring[:200],
                        })

            for cls in module.classes:
                if cls.docstring:
                    for pattern, info in debt_patterns.items():
                        if pattern in cls.docstring.upper():
                            tech_debt.append({
                                "type": pattern,
                                "severity": info["severity"],
                                "description": info["description"],
                                "location": f"{module.name}.{cls.name}",
                                "content": cls.docstring[:200],
                            })

                for method in cls.methods:
                    if method.docstring:
                        for pattern, info in debt_patterns.items():
                            if pattern in method.docstring.upper():
                                tech_debt.append({
                                    "type": pattern,
                                    "severity": info["severity"],
                                    "description": info["description"],
                                    "location": f"{module.name}.{cls.name}.{method.name}",
                                    "content": method.docstring[:200],
                                })

            for func in module.functions:
                if func.docstring:
                    for pattern, info in debt_patterns.items():
                        if pattern in func.docstring.upper():
                            tech_debt.append({
                                "type": pattern,
                                "severity": info["severity"],
                                "description": info["description"],
                                "location": f"{module.name}.{func.name}",
                                "content": func.docstring[:200],
                            })

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        tech_debt.sort(key=lambda x: severity_order.get(x["severity"], 4))

        return tech_debt[:30]

    def _detect_coding_conventions(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """检测编码规范"""
        conventions = []
        
        naming_conventions = self._analyze_naming_conventions(context)
        conventions.extend(naming_conventions)
        
        docstring_conventions = self._analyze_docstring_conventions(context)
        conventions.extend(docstring_conventions)
        
        type_hint_conventions = self._analyze_type_hints(context)
        conventions.extend(type_hint_conventions)
        
        error_handling_conventions = self._analyze_error_handling(context)
        conventions.extend(error_handling_conventions)
        
        logging_conventions = self._analyze_logging_patterns(context)
        conventions.extend(logging_conventions)

        return conventions[:20]

    def _analyze_naming_conventions(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """分析命名规范"""
        conventions = []
        
        class_names = []
        function_names = []
        variable_names = []
        
        for module in context.parse_result.modules:
            for cls in module.classes:
                class_names.append(cls.name)
                for prop in cls.properties:
                    variable_names.append(prop.name)
                for method in cls.methods:
                    function_names.append(method.name)
                    for param in method.parameters:
                        variable_names.append(param.name)
            
            for func in module.functions:
                function_names.append(func.name)
                for param in func.parameters:
                    variable_names.append(param.name)
        
        if class_names:
            pascal_case_count = sum(1 for name in class_names if name[0].isupper() and '_' not in name)
            if pascal_case_count / len(class_names) > 0.8:
                conventions.append({
                    "category": "命名规范",
                    "name": "类名使用 PascalCase",
                    "description": "类名采用大驼峰命名法（PascalCase）",
                    "compliance": f"{pascal_case_count}/{len(class_names)} ({pascal_case_count/len(class_names)*100:.1f}%)",
                })
        
        if function_names:
            snake_case_count = sum(1 for name in function_names if name.islower() and ('_' in name or len(name) < 3))
            if snake_case_count / len(function_names) > 0.6:
                conventions.append({
                    "category": "命名规范",
                    "name": "函数名使用 snake_case",
                    "description": "函数名采用蛇形命名法（snake_case）",
                    "compliance": f"{snake_case_count}/{len(function_names)} ({snake_case_count/len(function_names)*100:.1f}%)",
                })
        
        private_methods = [name for name in function_names if name.startswith('_')]
        if private_methods:
            conventions.append({
                "category": "命名规范",
                "name": "私有方法使用下划线前缀",
                "description": "私有方法以单下划线开头表示内部使用",
                "compliance": f"{len(private_methods)} 个私有方法",
            })

        return conventions

    def _analyze_docstring_conventions(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """分析文档字符串规范"""
        conventions = []
        
        total_classes = 0
        documented_classes = 0
        total_functions = 0
        documented_functions = 0
        
        for module in context.parse_result.modules:
            for cls in module.classes:
                total_classes += 1
                if cls.docstring:
                    documented_classes += 1
            
            for func in module.functions:
                total_functions += 1
                if func.docstring:
                    documented_functions += 1
        
        if total_classes > 0:
            doc_rate = documented_classes / total_classes * 100
            conventions.append({
                "category": "文档规范",
                "name": "类文档字符串",
                "description": "类定义包含文档字符串说明",
                "compliance": f"{documented_classes}/{total_classes} ({doc_rate:.1f}%)",
            })
        
        if total_functions > 0:
            doc_rate = documented_functions / total_functions * 100
            conventions.append({
                "category": "文档规范",
                "name": "函数文档字符串",
                "description": "函数定义包含文档字符串说明",
                "compliance": f"{documented_functions}/{total_functions} ({doc_rate:.1f}%)",
            })

        return conventions

    def _analyze_type_hints(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """分析类型提示使用"""
        conventions = []
        
        total_functions = 0
        typed_functions = 0
        total_params = 0
        typed_params = 0
        
        for module in context.parse_result.modules:
            for func in module.functions:
                total_functions += 1
                if func.return_type:
                    typed_functions += 1
                
                for param in func.parameters:
                    total_params += 1
                    if param.type_hint:
                        typed_params += 1
            
            for cls in module.classes:
                for method in cls.methods:
                    total_functions += 1
                    if method.return_type:
                        typed_functions += 1
                    
                    for param in method.parameters:
                        total_params += 1
                        if param.type_hint:
                            typed_params += 1
        
        if total_functions > 0:
            type_rate = typed_functions / total_functions * 100
            conventions.append({
                "category": "类型提示",
                "name": "返回值类型提示",
                "description": "函数/方法声明返回值类型",
                "compliance": f"{typed_functions}/{total_functions} ({type_rate:.1f}%)",
            })
        
        if total_params > 0:
            type_rate = typed_params / total_params * 100
            conventions.append({
                "category": "类型提示",
                "name": "参数类型提示",
                "description": "函数/方法参数声明类型",
                "compliance": f"{typed_params}/{total_params} ({type_rate:.1f}%)",
            })

        return conventions

    def _analyze_error_handling(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """分析错误处理模式"""
        conventions = []
        
        custom_exceptions = 0
        try_except_count = 0
        raise_count = 0
        
        for module in context.parse_result.modules:
            for cls in module.classes:
                if "Exception" in cls.name or "Error" in cls.name:
                    custom_exceptions += 1
            
            for func in module.functions:
                if func.docstring:
                    if "raise" in func.docstring.lower() or "exception" in func.docstring.lower():
                        raise_count += 1
        
        if custom_exceptions > 0:
            conventions.append({
                "category": "错误处理",
                "name": "自定义异常类",
                "description": "项目定义了自定义异常类型",
                "compliance": f"{custom_exceptions} 个自定义异常",
            })
        
        if raise_count > 0:
            conventions.append({
                "category": "错误处理",
                "name": "异常文档化",
                "description": "函数文档中声明可能抛出的异常",
                "compliance": f"{raise_count} 个函数声明了异常",
            })

        return conventions

    def _analyze_logging_patterns(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """分析日志模式"""
        conventions = []
        
        logging_imports = 0
        logger_instances = 0
        
        for module in context.parse_result.modules:
            for imp in module.imports:
                if "logging" in imp.module or "loguru" in imp.module or "logger" in imp.module:
                    logging_imports += 1
            
            for cls in module.classes:
                for prop in cls.properties:
                    if "logger" in prop.name.lower() or "log" in prop.name.lower():
                        logger_instances += 1
        
        if logging_imports > 0:
            conventions.append({
                "category": "日志规范",
                "name": "日志框架使用",
                "description": "项目使用日志框架记录运行信息",
                "compliance": f"{logging_imports} 个模块导入日志",
            })
        
        if logger_instances > 0:
            conventions.append({
                "category": "日志规范",
                "name": "类级别日志器",
                "description": "类中定义了日志器实例",
                "compliance": f"{logger_instances} 个日志器实例",
            })

        return conventions

    def _detect_design_decisions(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """检测设计决策"""
        decisions = []
        
        async_usage = self._detect_async_usage(context)
        if async_usage:
            decisions.append(async_usage)
        
        di_usage = self._detect_dependency_injection(context)
        if di_usage:
            decisions.append(di_usage)
        
        orm_usage = self._detect_orm_usage(context)
        if orm_usage:
            decisions.append(orm_usage)
        
        config_pattern = self._detect_config_pattern(context)
        if config_pattern:
            decisions.append(config_pattern)

        return decisions

    def _detect_async_usage(self, context: DocGeneratorContext) -> Optional[dict[str, Any]]:
        """检测异步使用"""
        async_functions = 0
        total_functions = 0
        
        for module in context.parse_result.modules:
            for func in module.functions:
                total_functions += 1
                if func.is_async:
                    async_functions += 1
            
            for cls in module.classes:
                for method in cls.methods:
                    total_functions += 1
                    if hasattr(method, 'is_async') and method.is_async:
                        async_functions += 1
        
        if async_functions > 0:
            return {
                "title": "异步编程模型",
                "description": f"项目使用 async/await 进行异步编程，共 {async_functions} 个异步函数/方法",
                "rationale": "提高 I/O 密集型操作的并发处理能力",
                "impact": "需要注意异步上下文和协程调度",
                "confidence": 0.9,
            }
        
        return None

    def _detect_dependency_injection(self, context: DocGeneratorContext) -> Optional[dict[str, Any]]:
        """检测依赖注入"""
        di_indicators = ["inject", "provider", "container", "depend"]
        
        for module in context.parse_result.modules:
            for cls in module.classes:
                for base in cls.bases:
                    if any(indicator in base.lower() for indicator in di_indicators):
                        return {
                            "title": "依赖注入模式",
                            "description": "项目使用依赖注入管理组件依赖",
                            "rationale": "解耦组件，提高可测试性和可维护性",
                            "impact": "需要配置依赖容器和注入规则",
                            "confidence": 0.85,
                        }
        
        return None

    def _detect_orm_usage(self, context: DocGeneratorContext) -> Optional[dict[str, Any]]:
        """检测 ORM 使用"""
        orm_indicators = {
            "sqlalchemy": "SQLAlchemy",
            "peewee": "Peewee",
            "django.db": "Django ORM",
            "pymongo": "PyMongo",
            "prisma": "Prisma",
            "typeorm": "TypeORM",
        }
        
        for module in context.parse_result.modules:
            for imp in module.imports:
                for indicator, name in orm_indicators.items():
                    if indicator in imp.module.lower():
                        return {
                            "title": f"使用 {name} 作为 ORM",
                            "description": f"项目使用 {name} 进行数据持久化",
                            "rationale": "抽象数据库操作，提高开发效率",
                            "impact": "需要定义模型类和映射关系",
                            "confidence": 0.95,
                        }
        
        return None

    def _detect_config_pattern(self, context: DocGeneratorContext) -> Optional[dict[str, Any]]:
        """检测配置模式"""
        config_indicators = ["config", "settings", "env", "dotenv"]
        
        for module in context.parse_result.modules:
            module_lower = module.name.lower()
            if any(indicator in module_lower for indicator in config_indicators):
                return {
                    "title": "配置管理模式",
                    "description": "项目使用配置模块管理环境配置",
                    "rationale": "分离配置和代码，支持多环境部署",
                    "impact": "需要维护配置文件和环境变量",
                    "confidence": 0.8,
                }
        
        return None

    def _detect_business_rules(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """检测业务规则"""
        rules = []
        
        validation_rules = self._detect_validation_rules(context)
        rules.extend(validation_rules)
        
        auth_rules = self._detect_auth_rules(context)
        rules.extend(auth_rules)

        return rules[:10]

    def _detect_validation_rules(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """检测验证规则"""
        rules = []
        
        validation_indicators = ["validate", "validator", "check", "verify", "assert"]
        
        for module in context.parse_result.modules:
            for func in module.functions:
                if any(indicator in func.name.lower() for indicator in validation_indicators):
                    rules.append({
                        "type": "数据验证",
                        "description": f"验证函数: {func.name}",
                        "location": f"{module.name}.{func.name}",
                    })
            
            for cls in module.classes:
                if any(indicator in cls.name.lower() for indicator in validation_indicators):
                    rules.append({
                        "type": "数据验证",
                        "description": f"验证器类: {cls.name}",
                        "location": f"{module.name}.{cls.name}",
                    })
        
        return rules[:5]

    def _detect_auth_rules(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """检测认证授权规则"""
        rules = []
        
        auth_indicators = ["auth", "login", "permission", "role", "token", "session"]
        
        for module in context.parse_result.modules:
            module_lower = module.name.lower()
            if any(indicator in module_lower for indicator in auth_indicators):
                rules.append({
                    "type": "认证授权",
                    "description": f"认证模块: {module.name}",
                    "location": module.name,
                })
            
            for cls in module.classes:
                cls_lower = cls.name.lower()
                if any(indicator in cls_lower for indicator in auth_indicators):
                    rules.append({
                        "type": "认证授权",
                        "description": f"认证类: {cls.name}",
                        "location": f"{module.name}.{cls.name}",
                    })
        
        return rules[:5]

    def _detect_security_patterns(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """检测安全模式"""
        considerations = []
        
        security_indicators = {
            "password": "密码处理",
            "encrypt": "加密",
            "decrypt": "解密",
            "hash": "哈希",
            "token": "令牌验证",
            "sanitize": "输入清理",
            "escape": "输出转义",
            "csrf": "CSRF 防护",
            "xss": "XSS 防护",
            "sql": "SQL 注入防护",
        }
        
        for module in context.parse_result.modules:
            for func in module.functions:
                func_lower = func.name.lower()
                for indicator, desc in security_indicators.items():
                    if indicator in func_lower:
                        considerations.append({
                            "type": desc,
                            "description": f"安全相关函数: {func.name}",
                            "location": f"{module.name}.{func.name}",
                        })
        
        return considerations[:10]

    def _detect_performance_patterns(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """检测性能相关模式"""
        considerations = []
        
        perf_indicators = {
            "cache": "缓存",
            "memoize": "记忆化",
            "lazy": "延迟加载",
            "async": "异步处理",
            "batch": "批处理",
            "pool": "连接池",
            "throttle": "限流",
            "debounce": "防抖",
        }
        
        for module in context.parse_result.modules:
            for func in module.functions:
                func_lower = func.name.lower()
                for indicator, desc in perf_indicators.items():
                    if indicator in func_lower:
                        considerations.append({
                            "type": desc,
                            "description": f"性能优化函数: {func.name}",
                            "location": f"{module.name}.{func.name}",
                        })
            
            for cls in module.classes:
                cls_lower = cls.name.lower()
                for indicator, desc in perf_indicators.items():
                    if indicator in cls_lower:
                        considerations.append({
                            "type": desc,
                            "description": f"性能优化类: {cls.name}",
                            "location": f"{module.name}.{cls.name}",
                        })
        
        return considerations[:10]

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        knowledge_data: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强隐性知识文档"""
        enhanced = {}

        prompt = f"""基于以下隐性知识分析，提供更深入的洞察：

项目: {context.project_name}
设计模式: {[p['name'] for p in knowledge_data.get('design_patterns', [])]}
技术债务: {len(knowledge_data.get('tech_debt', []))} 项
编码规范: {len(knowledge_data.get('coding_conventions', []))} 项

请以 JSON 格式返回：
{{
    "additional_patterns": ["可能存在但未检测到的模式"],
    "architecture_insights": ["架构洞察1", "架构洞察2"],
    "improvement_suggestions": ["改进建议1", "改进建议2"],
    "knowledge_gaps": ["知识空白1", "知识空白2"]
}}
"""

        try:
            response = await llm_client.agenerate(prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                result = json.loads(response[start:end+1])
                enhanced["llm_insights"] = result
        except Exception:
            pass

        return enhanced
