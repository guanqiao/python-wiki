"""
业务逻辑分析器
分析代码中的业务逻辑
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from pywiki.parsers.types import ModuleInfo, ClassInfo, FunctionInfo


class BusinessDomain(str, Enum):
    USER_MANAGEMENT = "user_management"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    ORDER_PROCESSING = "order_processing"
    PAYMENT = "payment"
    INVENTORY = "inventory"
    NOTIFICATION = "notification"
    REPORTING = "reporting"
    SEARCH = "search"
    FILE_MANAGEMENT = "file_management"
    SCHEDULING = "scheduling"
    MESSAGING = "messaging"
    ANALYTICS = "analytics"
    CONTENT_MANAGEMENT = "content_management"
    E_COMMERCE = "e_commerce"


@dataclass
class BusinessEntity:
    name: str
    domain: BusinessDomain
    description: str
    attributes: list[str] = field(default_factory=list)
    operations: list[str] = field(default_factory=list)
    location: str = ""


@dataclass
class BusinessRule:
    name: str
    domain: BusinessDomain
    description: str
    conditions: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    location: str = ""


@dataclass
class BusinessFlow:
    name: str
    domain: BusinessDomain
    steps: list[str] = field(default_factory=list)
    participants: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    location: str = ""


class BusinessLogicAnalyzer:
    """业务逻辑分析器"""

    def __init__(self):
        self._domain_keywords = self._load_domain_keywords()

    def analyze_module(self, module: ModuleInfo) -> dict:
        """分析模块的业务逻辑"""
        result = {
            "entities": [],
            "rules": [],
            "flows": [],
            "domain": None,
        }

        domain = self._detect_domain(module)
        if domain:
            result["domain"] = domain.value

        for cls in module.classes:
            entity = self._extract_business_entity(cls, domain)
            if entity:
                result["entities"].append(entity)

        for func in module.functions:
            rule = self._extract_business_rule(func, domain)
            if rule:
                result["rules"].append(rule)

        return result

    def _detect_domain(self, module: ModuleInfo) -> Optional[BusinessDomain]:
        """检测业务领域"""
        module_name_lower = module.name.lower()

        for domain, keywords in self._domain_keywords.items():
            for keyword in keywords:
                if keyword in module_name_lower:
                    return domain

        for imp in module.imports:
            for domain, keywords in self._domain_keywords.items():
                for keyword in keywords:
                    if keyword in imp.module.lower():
                        return domain

        for cls in module.classes:
            cls_name_lower = cls.name.lower()
            for domain, keywords in self._domain_keywords.items():
                for keyword in keywords:
                    if keyword in cls_name_lower:
                        return domain

        return None

    def _extract_business_entity(
        self,
        cls: ClassInfo,
        domain: Optional[BusinessDomain]
    ) -> Optional[BusinessEntity]:
        """提取业务实体"""
        entity_indicators = ["model", "entity", "schema", "dto", "vo"]

        is_entity = any(
            indicator in cls.name.lower()
            for indicator in entity_indicators
        )

        if not is_entity and not cls.is_dataclass:
            return None

        attributes = [p.name for p in cls.properties]
        operations = [m.name for m in cls.methods if not m.name.startswith("_")]

        return BusinessEntity(
            name=cls.name,
            domain=domain or BusinessDomain.CONTENT_MANAGEMENT,
            description=cls.docstring or f"业务实体: {cls.name}",
            attributes=attributes,
            operations=operations,
            location=cls.full_name,
        )

    def _extract_business_rule(
        self,
        func: FunctionInfo,
        domain: Optional[BusinessDomain]
    ) -> Optional[BusinessRule]:
        """提取业务规则"""
        rule_indicators = ["validate", "check", "verify", "ensure", "assert", "rule"]

        is_rule = any(
            indicator in func.name.lower()
            for indicator in rule_indicators
        )

        if not is_rule:
            return None

        conditions = []
        actions = []

        if func.docstring:
            if "if" in func.docstring.lower():
                conditions.append(func.docstring)
            if "then" in func.docstring.lower() or "should" in func.docstring.lower():
                actions.append(func.docstring)

        return BusinessRule(
            name=func.name,
            domain=domain or BusinessDomain.CONTENT_MANAGEMENT,
            description=func.docstring or f"业务规则: {func.name}",
            conditions=conditions,
            actions=actions,
            location=func.full_name,
        )

    def extract_business_flows(self, modules: list[ModuleInfo]) -> list[BusinessFlow]:
        """提取业务流程"""
        flows = []

        for module in modules:
            for cls in module.classes:
                if self._is_service_class(cls):
                    flow = self._extract_flow_from_service(cls)
                    if flow:
                        flows.append(flow)

        return flows

    def _is_service_class(self, cls: ClassInfo) -> bool:
        """检查是否是服务类"""
        service_indicators = ["service", "handler", "manager", "processor", "controller"]
        return any(indicator in cls.name.lower() for indicator in service_indicators)

    def _extract_flow_from_service(self, cls: ClassInfo) -> Optional[BusinessFlow]:
        """从服务类提取业务流程"""
        if len(cls.methods) < 2:
            return None

        steps = []
        for method in cls.methods:
            if not method.name.startswith("_"):
                steps.append(method.name)

        if len(steps) < 2:
            return None

        return BusinessFlow(
            name=f"{cls.name} Flow",
            domain=BusinessDomain.CONTENT_MANAGEMENT,
            steps=steps,
            participants=[cls.name],
            location=cls.full_name,
        )

    def _load_domain_keywords(self) -> dict[BusinessDomain, list[str]]:
        """加载领域关键词"""
        return {
            BusinessDomain.USER_MANAGEMENT: ["user", "account", "profile", "member"],
            BusinessDomain.AUTHENTICATION: ["auth", "login", "signin", "token", "session"],
            BusinessDomain.AUTHORIZATION: ["permission", "role", "access", "privilege"],
            BusinessDomain.ORDER_PROCESSING: ["order", "checkout", "cart", "purchase"],
            BusinessDomain.PAYMENT: ["payment", "billing", "invoice", "transaction", "checkout"],
            BusinessDomain.INVENTORY: ["inventory", "stock", "warehouse", "product"],
            BusinessDomain.NOTIFICATION: ["notification", "alert", "email", "sms", "push"],
            BusinessDomain.REPORTING: ["report", "analytics", "dashboard", "metrics"],
            BusinessDomain.SEARCH: ["search", "query", "filter", "index"],
            BusinessDomain.FILE_MANAGEMENT: ["file", "upload", "download", "storage", "document"],
            BusinessDomain.SCHEDULING: ["schedule", "calendar", "appointment", "booking"],
            BusinessDomain.MESSAGING: ["message", "chat", "conversation", "communication"],
            BusinessDomain.ANALYTICS: ["analytics", "tracking", "statistics", "insight"],
            BusinessDomain.CONTENT_MANAGEMENT: ["content", "article", "post", "page", "media"],
            BusinessDomain.E_COMMERCE: ["shop", "store", "product", "catalog", "category"],
        }

    def generate_business_report(self, analysis_results: list[dict]) -> dict:
        """生成业务逻辑报告"""
        report = {
            "domains": {},
            "entities": [],
            "rules": [],
            "flows": [],
        }

        for result in analysis_results:
            if result.get("domain"):
                domain = result["domain"]
                report["domains"][domain] = report["domains"].get(domain, 0) + 1

            report["entities"].extend([
                {"name": e.name, "domain": e.domain.value, "description": e.description}
                for e in result.get("entities", [])
            ])

            report["rules"].extend([
                {"name": r.name, "domain": r.domain.value, "description": r.description}
                for r in result.get("rules", [])
            ])

        return report
