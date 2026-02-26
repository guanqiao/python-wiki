"""
架构决策记录 (ADR) 文档生成器
生成符合标准的 ADR 文档
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
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
class ADRRecord:
    """架构决策记录"""
    number: int
    title: str
    status: str  # proposed, accepted, deprecated, superseded
    context: str
    decision: str
    consequences: str
    alternatives: list[str] = field(default_factory=list)
    related_decisions: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    author: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "status": self.status,
            "context": self.context,
            "decision": self.decision,
            "consequences": self.consequences,
            "alternatives": self.alternatives,
            "related_decisions": self.related_decisions,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "author": self.author,
        }


class ADRGenerator(BaseDocGenerator):
    """
    架构决策记录文档生成器
    
    生成符合 Markdown ADR (MADR) 标准的架构决策记录
    """

    doc_type = DocType.TSD
    template_name = "adr.md.j2"

    def __init__(self, language: Language = Language.ZH, template_dir: Optional[Path] = None):
        super().__init__(language, template_dir)
        self._adr_counter = 0

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成 ADR 文档"""
        try:
            # 从解析结果中提取架构决策
            decisions = self._extract_decisions(context)

            if not decisions:
                return self.create_result(
                    content="",
                    context=context,
                    success=False,
                    message="未检测到架构决策",
                )

            # 生成 ADR 索引文档
            index_content = self._generate_adr_index(decisions)

            # 生成单个 ADR 文档
            adr_files = []
            for decision in decisions:
                adr_content = self._generate_single_adr(decision, context)
                adr_path = context.get_output_path(self.doc_type).parent / f"adr-{decision.number:04d}.md"
                adr_files.append((adr_path, adr_content))

            # 合并所有内容
            full_content = index_content + "\n\n" + "\n".join(
                [f"<!-- ADR-{d.number:04d}: {d.title} -->" for d in decisions]
            )

            result = self.create_result(
                content=full_content,
                context=context,
                success=True,
                message=f"成功生成 {len(decisions)} 个 ADR",
                metadata={
                    "adr_count": len(decisions),
                    "adr_files": [str(p) for p, _ in adr_files],
                },
            )

            # 保存单个 ADR 文件
            for adr_path, adr_content in adr_files:
                adr_path.parent.mkdir(parents=True, exist_ok=True)
                adr_path.write_text(adr_content, encoding="utf-8")

            return result

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"生成失败: {str(e)}",
            )

    def _extract_decisions(self, context: DocGeneratorContext) -> list[ADRRecord]:
        """从项目代码中提取架构决策"""
        decisions = []

        parse_result = context.parse_result
        if not parse_result:
            return decisions

        # 分析框架选择决策
        framework_decision = self._detect_framework_decision(parse_result)
        if framework_decision:
            decisions.append(framework_decision)

        # 分析架构模式决策
        architecture_decision = self._detect_architecture_decision(parse_result)
        if architecture_decision:
            decisions.append(architecture_decision)

        # 分析数据库选择决策
        database_decision = self._detect_database_decision(parse_result)
        if database_decision:
            decisions.append(database_decision)

        # 分析关键设计决策
        design_decisions = self._detect_design_decisions(parse_result)
        decisions.extend(design_decisions)

        return decisions

    def _detect_framework_decision(self, parse_result) -> Optional[ADRRecord]:
        """检测框架选择决策"""
        frameworks = {
            "fastapi": {
                "name": "FastAPI",
                "description": "现代、高性能的 Python Web 框架",
                "pros": ["异步支持", "自动 API 文档", "类型提示"],
                "cons": ["相对较新", "生态系统较小"],
            },
            "flask": {
                "name": "Flask",
                "description": "轻量级 Python Web 框架",
                "pros": ["简单灵活", "丰富的扩展", "成熟的生态"],
                "cons": ["需要手动配置", "异步支持有限"],
            },
            "django": {
                "name": "Django",
                "description": "全功能 Python Web 框架",
                "pros": ["功能完整", "ORM 强大", "管理后台"],
                "cons": ["较重", "学习曲线陡峭"],
            },
        }

        detected_framework = None
        for module in parse_result.modules:
            for imp in module.imports:
                module_name = imp.module.split(".")[0].lower()
                if module_name in frameworks:
                    detected_framework = frameworks[module_name]
                    break
            if detected_framework:
                break

        if not detected_framework:
            return None

        self._adr_counter += 1

        if self.language == Language.ZH:
            return ADRRecord(
                number=self._adr_counter,
                title=f"使用 {detected_framework['name']} 作为 Web 框架",
                status="accepted",
                context="项目需要选择一个合适的 Web 框架来构建 API 服务。",
                decision=f"选择 {detected_framework['name']} 作为项目的 Web 框架。{detected_framework['description']}",
                consequences=f"优点: {', '.join(detected_framework['pros'])}。缺点: {', '.join(detected_framework['cons'])}",
                alternatives=[f.name for f in frameworks.values() if f["name"] != detected_framework["name"]],
            )
        else:
            return ADRRecord(
                number=self._adr_counter,
                title=f"Use {detected_framework['name']} as Web Framework",
                status="accepted",
                context="The project needs to select an appropriate web framework for building API services.",
                decision=f"Choose {detected_framework['name']} as the web framework. {detected_framework['description']}",
                consequences=f"Pros: {', '.join(detected_framework['pros'])}. Cons: {', '.join(detected_framework['cons'])}",
                alternatives=[f.name for f in frameworks.values() if f["name"] != detected_framework["name"]],
            )

    def _detect_architecture_decision(self, parse_result) -> Optional[ADRRecord]:
        """检测架构模式决策"""
        layers = {"controller": 0, "service": 0, "repository": 0, "model": 0}

        for module in parse_result.modules:
            name_lower = module.name.lower()
            for layer in layers:
                if layer in name_lower:
                    layers[layer] += 1

        # 如果检测到分层架构
        if sum(1 for v in layers.values() if v > 0) >= 2:
            self._adr_counter += 1

            if self.language == Language.ZH:
                return ADRRecord(
                    number=self._adr_counter,
                    title="采用分层架构模式",
                    status="accepted",
                    context="项目需要清晰的代码组织和职责分离。",
                    decision="采用分层架构，将代码分为表示层、业务层和数据层。",
                    consequences="优点: 职责清晰、易于测试、便于维护。缺点: 增加了一定的复杂性。",
                    alternatives=["微服务架构", "六边形架构", "洋葱架构"],
                )
            else:
                return ADRRecord(
                    number=self._adr_counter,
                    title="Adopt Layered Architecture Pattern",
                    status="accepted",
                    context="The project needs clear code organization and separation of concerns.",
                    decision="Adopt layered architecture, dividing code into presentation, business, and data layers.",
                    consequences="Pros: Clear responsibilities, easy to test, maintainable. Cons: Adds some complexity.",
                    alternatives=["Microservices", "Hexagonal Architecture", "Onion Architecture"],
                )

        return None

    def _detect_database_decision(self, parse_result) -> Optional[ADRRecord]:
        """检测数据库选择决策"""
        databases = {
            "sqlalchemy": ("SQLAlchemy ORM", "关系型数据库"),
            "pymongo": ("MongoDB", "文档型数据库"),
            "redis": ("Redis", "键值存储"),
            "sqlite": ("SQLite", "嵌入式数据库"),
        }

        detected_db = None
        for module in parse_result.modules:
            for imp in module.imports:
                module_name = imp.module.split(".")[0].lower()
                if module_name in databases:
                    detected_db = databases[module_name]
                    break
            if detected_db:
                break

        if not detected_db:
            return None

        self._adr_counter += 1

        if self.language == Language.ZH:
            return ADRRecord(
                number=self._adr_counter,
                title=f"使用 {detected_db[0]} 作为数据存储方案",
                status="accepted",
                context=f"项目需要选择合适的数据存储方案来满足{detected_db[1]}的需求。",
                decision=f"选择 {detected_db[0]} 作为数据存储方案。",
                consequences="影响数据访问层的设计和实现。",
                alternatives=["其他 ORM 框架", "原生 SQL"],
            )
        else:
            return ADRRecord(
                number=self._adr_counter,
                title=f"Use {detected_db[0]} as Data Storage Solution",
                status="accepted",
                context=f"The project needs to select an appropriate data storage solution for {detected_db[1]} requirements.",
                decision=f"Choose {detected_db[0]} as the data storage solution.",
                consequences="Impacts the design and implementation of the data access layer.",
                alternatives=["Other ORM frameworks", "Raw SQL"],
            )

    def _detect_design_decisions(self, parse_result) -> list[ADRRecord]:
        """检测其他设计决策"""
        decisions = []

        # 检测是否使用依赖注入
        has_di = False
        for module in parse_result.modules:
            for cls in module.classes:
                if any("inject" in base.lower() or "provider" in base.lower() for base in cls.bases):
                    has_di = True
                    break

        if has_di:
            self._adr_counter += 1
            if self.language == Language.ZH:
                decisions.append(ADRRecord(
                    number=self._adr_counter,
                    title="使用依赖注入模式",
                    status="accepted",
                    context="需要管理组件之间的依赖关系。",
                    decision="采用依赖注入模式来解耦组件。",
                    consequences="提高代码的可测试性和可维护性。",
                    alternatives=["服务定位器模式", "工厂模式"],
                ))
            else:
                decisions.append(ADRRecord(
                    number=self._adr_counter,
                    title="Use Dependency Injection Pattern",
                    status="accepted",
                    context="Need to manage dependencies between components.",
                    decision="Adopt dependency injection pattern to decouple components.",
                    consequences="Improves code testability and maintainability.",
                    alternatives=["Service Locator", "Factory Pattern"],
                ))

        # 检测异步使用
        has_async = False
        for module in parse_result.modules:
            for func in module.functions:
                if func.is_async:
                    has_async = True
                    break

        if has_async:
            self._adr_counter += 1
            if self.language == Language.ZH:
                decisions.append(ADRRecord(
                    number=self._adr_counter,
                    title="使用异步编程模型",
                    status="accepted",
                    context="需要处理 I/O 密集型操作以提高性能。",
                    decision="在适当的地方使用 async/await 进行异步编程。",
                    consequences="提高并发处理能力，但需要小心处理异步上下文。",
                    alternatives=["同步编程", "多线程"],
                ))
            else:
                decisions.append(ADRRecord(
                    number=self._adr_counter,
                    title="Use Asynchronous Programming Model",
                    status="accepted",
                    context="Need to handle I/O-bound operations for better performance.",
                    decision="Use async/await for asynchronous programming where appropriate.",
                    consequences="Improves concurrency but requires careful handling of async context.",
                    alternatives=["Synchronous programming", "Multi-threading"],
                ))

        return decisions

    def _generate_adr_index(self, decisions: list[ADRRecord]) -> str:
        """生成 ADR 索引文档"""
        if self.language == Language.ZH:
            lines = [
                "# 架构决策记录 (ADR)",
                "",
                "本文档记录了项目的重要架构决策。",
                "",
                "## ADR 列表",
                "",
            ]

            for decision in decisions:
                status_icon = {
                    "accepted": "✅",
                    "proposed": "📝",
                    "deprecated": "⚠️",
                    "superseded": "🔄",
                }.get(decision.status, "❓")

                lines.append(f"- {status_icon} [ADR-{decision.number:04d}: {decision.title}](./adr-{decision.number:04d}.md)")

            lines.extend([
                "",
                "## 状态说明",
                "",
                "- ✅ accepted: 已接受的决策",
                "- 📝 proposed: 提议中的决策",
                "- ⚠️ deprecated: 已废弃的决策",
                "- 🔄 superseded: 已被替代的决策",
            ])
        else:
            lines = [
                "# Architecture Decision Records (ADR)",
                "",
                "This document records important architectural decisions for the project.",
                "",
                "## ADR List",
                "",
            ]

            for decision in decisions:
                status_icon = {
                    "accepted": "✅",
                    "proposed": "📝",
                    "deprecated": "⚠️",
                    "superseded": "🔄",
                }.get(decision.status, "❓")

                lines.append(f"- {status_icon} [ADR-{decision.number:04d}: {decision.title}](./adr-{decision.number:04d}.md)")

            lines.extend([
                "",
                "## Status Legend",
                "",
                "- ✅ accepted: Accepted decision",
                "- 📝 proposed: Proposed decision",
                "- ⚠️ deprecated: Deprecated decision",
                "- 🔄 superseded: Superseded decision",
            ])

        return "\n".join(lines)

    def _generate_single_adr(self, decision: ADRRecord, context: DocGeneratorContext) -> str:
        """生成单个 ADR 文档"""
        if self.language == Language.ZH:
            lines = [
                f"# ADR-{decision.number:04d}: {decision.title}",
                "",
                f"**状态**: {decision.status}",
                f"**创建日期**: {decision.created_at.strftime('%Y-%m-%d')}",
                "",
                "## 背景",
                "",
                decision.context,
                "",
                "## 决策",
                "",
                decision.decision,
                "",
                "## 后果",
                "",
                decision.consequences,
                "",
            ]

            if decision.alternatives:
                lines.extend([
                    "## 备选方案",
                    "",
                ])
                for alt in decision.alternatives:
                    lines.append(f"- {alt}")
                lines.append("")

            if decision.related_decisions:
                lines.extend([
                    "## 相关决策",
                    "",
                ])
                for related in decision.related_decisions:
                    lines.append(f"- {related}")
                lines.append("")

            lines.extend([
                "---",
                "",
                "*此文档由 Python Wiki 自动生成*",
            ])
        else:
            lines = [
                f"# ADR-{decision.number:04d}: {decision.title}",
                "",
                f"**Status**: {decision.status}",
                f"**Created**: {decision.created_at.strftime('%Y-%m-%d')}",
                "",
                "## Context",
                "",
                decision.context,
                "",
                "## Decision",
                "",
                decision.decision,
                "",
                "## Consequences",
                "",
                decision.consequences,
                "",
            ]

            if decision.alternatives:
                lines.extend([
                    "## Alternatives",
                    "",
                ])
                for alt in decision.alternatives:
                    lines.append(f"- {alt}")
                lines.append("")

            if decision.related_decisions:
                lines.extend([
                    "## Related Decisions",
                    "",
                ])
                for related in decision.related_decisions:
                    lines.append(f"- {related}")
                lines.append("")

            lines.extend([
                "---",
                "",
                "*This document is auto-generated by Python Wiki*",
            ])

        return "\n".join(lines)
