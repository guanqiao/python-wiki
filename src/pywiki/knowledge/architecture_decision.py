"""
架构决策记录（ADR）自动提取
从代码和提交历史中提取架构决策
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pywiki.knowledge.implicit_extractor import (
    BaseKnowledgeExtractor,
    ExtractionContext,
    ImplicitKnowledge,
    KnowledgeType,
    KnowledgePriority,
)
from pywiki.parsers.types import ModuleInfo, ClassInfo


@dataclass
class ArchitectureDecision:
    id: str
    title: str
    status: str
    context: str
    decision: str
    consequences: str
    alternatives: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "context": self.context,
            "decision": self.decision,
            "consequences": self.consequences,
            "alternatives": self.alternatives,
            "created_at": self.created_at.isoformat(),
        }


ADR_PATTERNS = {
    "dependency": {
        "keywords": ["import", "from", "require", "depends"],
        "decision_type": "依赖选择",
    },
    "architecture": {
        "keywords": ["layer", "module", "service", "component", "architecture"],
        "decision_type": "架构设计",
    },
    "data_storage": {
        "keywords": ["database", "storage", "cache", "persistence", "orm"],
        "decision_type": "数据存储",
    },
    "api_design": {
        "keywords": ["api", "endpoint", "rest", "graphql", "interface"],
        "decision_type": "API 设计",
    },
    "security": {
        "keywords": ["auth", "security", "encrypt", "token", "permission"],
        "decision_type": "安全设计",
    },
    "performance": {
        "keywords": ["cache", "async", "concurrent", "optimize", "performance"],
        "decision_type": "性能优化",
    },
}


class ArchitectureDecisionExtractor(BaseKnowledgeExtractor):
    """
    架构决策提取器
    从代码结构和注释中提取架构决策
    """

    def __init__(self):
        self._decision_counter = 0

    @property
    def knowledge_type(self) -> KnowledgeType:
        return KnowledgeType.DESIGN_DECISION

    def extract(self, context: ExtractionContext) -> list[ImplicitKnowledge]:
        """提取架构决策"""
        knowledge = []

        if context.module_info:
            knowledge.extend(self._extract_from_module(context))

        if context.code_content:
            knowledge.extend(self._extract_from_code(context))

        if context.commit_messages:
            knowledge.extend(self._extract_from_commits(context))

        return knowledge

    def _extract_from_module(self, context: ExtractionContext) -> list[ImplicitKnowledge]:
        """从模块提取架构决策"""
        knowledge = []
        module = context.module_info

        imports = self._analyze_imports(module)
        if imports["external"]:
            knowledge.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title=f"模块 {module.name} 的外部依赖决策",
                description=f"模块选择了特定的外部依赖来实现功能。",
                location=module.name,
                evidence=[f"依赖: {dep}" for dep in imports["external"][:10]],
                confidence=0.8,
                priority=KnowledgePriority.MEDIUM,
                impact="影响项目的依赖管理和可维护性",
                recommendation="定期审查依赖的版本和安全性",
                metadata={
                    "decision_type": "dependency",
                    "external_deps": imports["external"],
                    "internal_deps": imports["internal"],
                },
            ))

        layer_info = self._detect_architecture_layer(module)
        if layer_info:
            knowledge.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.ARCHITECTURE_PATTERN,
                title=f"模块属于 {layer_info['layer']} 层",
                description=layer_info["description"],
                location=module.name,
                evidence=layer_info["evidence"],
                confidence=layer_info["confidence"],
                priority=KnowledgePriority.MEDIUM,
                impact=layer_info["impact"],
                recommendation="遵循分层架构原则，保持层间依赖单向",
            ))

        return knowledge

    def _extract_from_code(self, context: ExtractionContext) -> list[ImplicitKnowledge]:
        """从代码内容提取架构决策"""
        knowledge = []
        code = context.code_content

        adr_comments = self._extract_adr_comments(code)
        for adr in adr_comments:
            knowledge.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title=adr["title"],
                description=adr["decision"],
                location=context.project_path.name,
                evidence=adr["evidence"],
                confidence=0.9,
                priority=KnowledgePriority.HIGH,
                impact=adr.get("consequences", ""),
                recommendation="将此决策记录到正式的 ADR 文档中",
                metadata={
                    "adr_id": adr.get("id"),
                    "status": adr.get("status", "accepted"),
                },
            ))

        config_decisions = self._extract_config_decisions(code)
        for decision in config_decisions:
            knowledge.append(ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title=f"配置决策: {decision['name']}",
                description=decision["description"],
                location=context.project_path.name,
                evidence=[f"{decision['name']} = {decision['value']}"],
                confidence=0.85,
                priority=KnowledgePriority.MEDIUM,
                impact="影响系统行为和性能",
                recommendation="确保配置有合理的默认值和文档",
            ))

        return knowledge

    def _extract_from_commits(self, context: ExtractionContext) -> list[ImplicitKnowledge]:
        """从提交消息提取架构决策"""
        knowledge = []

        for message in context.commit_messages:
            decision = self._parse_commit_for_decision(message)
            if decision:
                knowledge.append(ImplicitKnowledge(
                    knowledge_type=KnowledgeType.DESIGN_DECISION,
                    title=decision["title"],
                    description=decision["description"],
                    location=context.project_path.name,
                    evidence=[f"Commit: {message[:100]}"],
                    confidence=0.7,
                    priority=KnowledgePriority.MEDIUM,
                    impact=decision.get("impact", ""),
                    recommendation="考虑将重要的架构决策记录到 ADR 文档",
                ))

        return knowledge

    def _analyze_imports(self, module: ModuleInfo) -> dict[str, list[str]]:
        """分析模块的导入"""
        external = []
        internal = []

        for imp in module.imports:
            if imp.startswith(("pywiki", ".")):
                internal.append(imp)
            else:
                external.append(imp)

        return {"external": external, "internal": internal}

    def _detect_architecture_layer(self, module: ModuleInfo) -> Optional[dict[str, Any]]:
        """检测模块所属的架构层"""
        module_name_lower = module.name.lower()

        layers = {
            "presentation": {
                "keywords": ["view", "controller", "api", "route", "handler", "endpoint"],
                "description": "表示层：处理用户交互和请求路由",
                "impact": "负责接收请求和返回响应",
            },
            "business": {
                "keywords": ["service", "business", "domain", "usecase", "manager"],
                "description": "业务层：实现核心业务逻辑",
                "impact": "包含核心业务规则和流程",
            },
            "data": {
                "keywords": ["repository", "dao", "model", "entity", "storage", "db"],
                "description": "数据层：处理数据持久化",
                "impact": "负责数据存储和检索",
            },
            "infrastructure": {
                "keywords": ["config", "util", "helper", "common", "infrastructure"],
                "description": "基础设施层：提供通用功能支持",
                "impact": "提供横切关注点的实现",
            },
        }

        for layer_name, layer_info in layers.items():
            for keyword in layer_info["keywords"]:
                if keyword in module_name_lower:
                    return {
                        "layer": layer_name,
                        "description": layer_info["description"],
                        "evidence": [f"模块名包含 '{keyword}'"],
                        "confidence": 0.7,
                        "impact": layer_info["impact"],
                    }

        return None

    def _extract_adr_comments(self, code: str) -> list[dict[str, Any]]:
        """从代码注释中提取 ADR"""
        adrs = []

        adr_pattern = re.compile(
            r'#\s*ADR[-:]?\s*(\d+)?:?\s*(.+?)(?:\n#\s*(.+?))*',
            re.IGNORECASE | re.MULTILINE
        )

        for match in adr_pattern.finditer(code):
            adr_id = match.group(1) or f"ADR-{self._decision_counter}"
            self._decision_counter += 1

            title = match.group(2).strip()
            details = match.group(3) or ""

            adrs.append({
                "id": adr_id,
                "title": title[:100],
                "decision": details or title,
                "evidence": [f"ADR 注释: {title[:50]}"],
                "status": "accepted",
            })

        decision_pattern = re.compile(
            r'#\s*(?:DECISION|DECIDE|ARCHITECTURAL):?\s*(.+)',
            re.IGNORECASE
        )

        for match in decision_pattern.finditer(code):
            decision_text = match.group(1).strip()
            adrs.append({
                "id": f"ADR-{self._decision_counter}",
                "title": decision_text[:100],
                "decision": decision_text,
                "evidence": [f"决策注释: {decision_text[:50]}"],
                "status": "accepted",
            })
            self._decision_counter += 1

        return adrs

    def _extract_config_decisions(self, code: str) -> list[dict[str, Any]]:
        """提取配置决策"""
        decisions = []

        config_pattern = re.compile(
            r'(\w+)\s*[:=]\s*(.+?)(?:\s*#\s*(.+))?$',
            re.MULTILINE
        )

        important_configs = [
            "timeout", "max_", "min_", "cache", "buffer", "pool",
            "limit", "size", "threshold", "interval",
        ]

        for match in config_pattern.finditer(code):
            name = match.group(1)
            value = match.group(2)
            comment = match.group(3) or ""

            if any(cfg in name.lower() for cfg in important_configs):
                decisions.append({
                    "name": name,
                    "value": value[:50],
                    "description": comment or f"配置项 {name}",
                })

        return decisions[:10]

    def _parse_commit_for_decision(self, message: str) -> Optional[dict[str, Any]]:
        """从提交消息解析架构决策"""
        decision_keywords = [
            "refactor", "architect", "design", "migrate", "replace",
            "implement", "change", "update", "remove", "deprecate",
        ]

        message_lower = message.lower()
        if not any(kw in message_lower for kw in decision_keywords):
            return None

        title = message.split("\n")[0][:100]

        return {
            "title": f"提交决策: {title}",
            "description": message,
            "impact": "通过代码变更体现的架构决策",
        }

    def generate_adr_document(
        self,
        knowledge: ImplicitKnowledge,
    ) -> ArchitectureDecision:
        """从隐性知识生成 ADR 文档"""
        self._decision_counter += 1

        return ArchitectureDecision(
            id=f"ADR-{self._decision_counter:04d}",
            title=knowledge.title,
            status="accepted",
            context=knowledge.location,
            decision=knowledge.description,
            consequences=knowledge.impact,
            alternatives=[],
        )
