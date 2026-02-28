"""
分层架构分析器
分析项目的分层结构
"""

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from .module_filter import ModuleFilter

if TYPE_CHECKING:
    from pywiki.generators.docs.base import DocGeneratorContext


class LayerAnalyzer:
    """分层架构分析器"""

    def __init__(self, labels: dict):
        self.labels = labels

    def analyze(self, context: "DocGeneratorContext", project_language: str) -> list[dict[str, Any]]:
        """分析分层架构"""
        layers = []

        if not context.parse_result or not context.parse_result.modules:
            return layers

        filtered_modules = ModuleFilter.filter_project_modules(
            context.parse_result.modules,
            context.project_name
        )

        if not filtered_modules:
            return layers

        layer_patterns = self._get_layer_patterns(project_language)

        layer_modules: dict[str, list] = defaultdict(list)
        assigned_modules = set()

        for module in filtered_modules:
            module_lower = module.name.lower()

            matched = False
            for layer_name, layer_info in layer_patterns.items():
                if any(kw in module_lower for kw in layer_info["keywords"]):
                    layer_modules[layer_name].append(module)
                    assigned_modules.add(module.name)
                    matched = True
                    break

            if not matched:
                for cls in (module.classes or []):
                    annotations = getattr(cls, 'annotations', []) or getattr(cls, 'decorators', [])
                    class_lower = cls.name.lower()

                    for layer_name, layer_info in layer_patterns.items():
                        layer_keywords = layer_info.get("keywords", [])
                        layer_annotations = layer_info.get("annotations", []) or layer_info.get("decorators", [])

                        if any(kw in class_lower for kw in layer_keywords):
                            layer_modules[layer_name].append(module)
                            assigned_modules.add(module.name)
                            matched = True
                            break

                        for annotation in annotations:
                            if any(ann in annotation for ann in layer_annotations):
                                layer_modules[layer_name].append(module)
                                assigned_modules.add(module.name)
                                matched = True
                                break

                        if matched:
                            break

                    if matched:
                        break

        # 处理未分配的模块
        for module in filtered_modules:
            if module.name not in assigned_modules:
                if module.classes:
                    has_entity = any(
                        "Model" in c.name or "Entity" in c.name or "DTO" in c.name or "Dto" in c.name
                        for c in module.classes
                    )
                    has_service = any("Service" in c.name for c in module.classes)
                    has_controller = any("Controller" in c.name for c in module.classes)

                    if has_controller:
                        layer_modules["表现层"].append(module)
                    elif has_entity:
                        layer_modules["数据层"].append(module)
                    elif has_service:
                        layer_modules["业务层"].append(module)
                    else:
                        layer_modules["基础设施层"].append(module)

        # 构建结果
        for layer_name, layer_info in layer_patterns.items():
            modules = layer_modules.get(layer_name, [])
            if modules:
                components = []
                for module in modules[:8]:
                    class_count = len(module.classes) if module.classes else 0
                    func_count = len(module.functions) if module.functions else 0

                    components.append({
                        "name": module.name.split(".")[-1],
                        "full_name": module.name,
                        "responsibility": module.docstring.split("\n")[0] if module.docstring else "",
                        "class_count": class_count,
                        "func_count": func_count,
                    })

                layers.append({
                    "name": layer_name,
                    "description": layer_info["description"],
                    "component_count": len(modules),
                    "components": components,
                })

        return layers

    def _get_layer_patterns(self, project_language: str) -> dict:
        """获取分层模式定义"""
        base_patterns = {
            self.labels.get("presentation_layer", "Presentation Layer"): {
                "keywords": ["api", "controller", "view", "handler", "endpoint", "route", "router", "http", "rest", "graphql", "web"],
                "description": self.labels.get("presentation_desc", "Handles external requests, responsible for data display and user interaction"),
            },
            self.labels.get("business_layer", "Business Layer"): {
                "keywords": ["service", "business", "domain", "usecase", "application", "logic", "manager", "processor"],
                "description": self.labels.get("business_desc", "Implements core business logic and business rules"),
            },
            self.labels.get("data_layer", "Data Layer"): {
                "keywords": ["repository", "dao", "model", "entity", "data", "persistence", "store", "mapper", "schema"],
                "description": self.labels.get("data_desc", "Responsible for data persistence and data access"),
            },
            self.labels.get("infrastructure_layer", "Infrastructure Layer"): {
                "keywords": ["infrastructure", "config", "util", "common", "helper", "lib", "core", "base", "foundation"],
                "description": self.labels.get("infrastructure_desc", "Provides technical support and infrastructure services"),
            },
            self.labels.get("proxy_layer", "Proxy Layer"): {
                "keywords": ["agent", "broker", "proxy", "client", "adapter", "connector"],
                "description": self.labels.get("proxy_desc", "Responsible for interacting and integrating with external systems"),
            },
        }

        java_patterns = {
            self.labels.get("presentation_layer", "Presentation Layer"): {
                "keywords": ["controller", "restcontroller", "handler", "endpoint", "api", "web", "servlet", "filter"],
                "annotations": ["@Controller", "@RestController", "@RequestMapping", "@GetMapping", "@PostMapping"],
                "description": self.labels.get("java_presentation_desc", "Handles HTTP requests, responsible for API endpoints and web interface"),
            },
            self.labels.get("business_layer", "Business Layer"): {
                "keywords": ["service", "serviceimpl", "business", "domain", "usecase", "manager", "processor", "facade"],
                "annotations": ["@Service", "@Transactional", "@Component"],
                "description": self.labels.get("business_desc", "Implements core business logic and business rules"),
            },
            self.labels.get("data_layer", "Data Layer"): {
                "keywords": ["repository", "dao", "mapper", "entity", "model", "persistence", "jpa", "crud"],
                "annotations": ["@Repository", "@Entity", "@Table", "@Mapper"],
                "description": self.labels.get("data_desc", "Responsible for data persistence and data access"),
            },
            self.labels.get("infrastructure_layer", "Infrastructure Layer"): {
                "keywords": ["config", "configuration", "util", "common", "helper", "exception", "aspect", "interceptor"],
                "annotations": ["@Configuration", "@Component", "@Aspect", "@Bean"],
                "description": self.labels.get("infrastructure_desc", "Provides technical support and infrastructure services"),
            },
            self.labels.get("dto_layer", "DTO Layer"): {
                "keywords": ["dto", "vo", "request", "response", "form", "command", "query"],
                "annotations": [],
                "description": self.labels.get("dto_desc", "Data Transfer Objects for inter-layer data transfer"),
            },
        }

        typescript_patterns = {
            self.labels.get("presentation_layer", "Presentation Layer"): {
                "keywords": ["controller", "handler", "endpoint", "api", "route", "resolver", "gateway"],
                "decorators": ["@Controller", "@Get", "@Post", "@Put", "@Delete", "@Patch", "@Resolver"],
                "description": self.labels.get("ts_presentation_desc", "Handles HTTP requests and GraphQL resolvers"),
            },
            self.labels.get("business_layer", "Business Layer"): {
                "keywords": ["service", "business", "domain", "usecase", "manager", "processor", "provider"],
                "decorators": ["@Service", "@Injectable", "@Provider"],
                "description": self.labels.get("business_desc", "Implements core business logic and business rules"),
            },
            self.labels.get("data_layer", "Data Layer"): {
                "keywords": ["repository", "dao", "mapper", "entity", "model", "schema", "prisma", "typeorm"],
                "decorators": ["@Entity", "@Repository", "@EntityRepository"],
                "description": self.labels.get("data_desc", "Responsible for data persistence and data access"),
            },
            self.labels.get("infrastructure_layer", "Infrastructure Layer"): {
                "keywords": ["config", "module", "middleware", "guard", "interceptor", "filter", "pipe", "util", "common"],
                "decorators": ["@Module", "@Middleware", "@UseGuards", "@UseInterceptors", "@UsePipes"],
                "description": self.labels.get("infrastructure_desc", "Provides technical support and infrastructure services"),
            },
            self.labels.get("dto_layer", "DTO Layer"): {
                "keywords": ["dto", "vo", "input", "output", "request", "response", "interface", "type"],
                "decorators": [],
                "description": self.labels.get("ts_dto_desc", "Data Transfer Objects and type definitions"),
            },
        }

        if project_language == "java":
            return java_patterns
        elif project_language == "typescript":
            return typescript_patterns

        return base_patterns