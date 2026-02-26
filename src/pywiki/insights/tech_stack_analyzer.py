"""
技术栈分析器
分析项目使用的技术栈
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pywiki.parsers.types import ModuleInfo


class TechCategory(str, Enum):
    FRAMEWORK = "framework"
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    TESTING = "testing"
    ORM = "orm"
    VALIDATION = "validation"
    HTTP_CLIENT = "http_client"
    ASYNC = "async"
    SECURITY = "security"
    LOGGING = "logging"
    CONFIG = "config"
    TASK_QUEUE = "task_queue"
    MONITORING = "monitoring"
    CLOUD = "cloud"


@dataclass
class TechComponent:
    name: str
    category: TechCategory
    version: Optional[str] = None
    description: str = ""
    usage_locations: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


@dataclass
class TechStackAnalysis:
    components: list[TechComponent] = field(default_factory=list)
    frameworks: list[TechComponent] = field(default_factory=list)
    databases: list[TechComponent] = field(default_factory=list)
    libraries: list[TechComponent] = field(default_factory=list)
    tools: list[TechComponent] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


class TechStackAnalyzer:
    """技术栈分析器"""

    def __init__(self):
        self._tech_database = self._load_tech_database()

    def analyze_project(self, project_path: Path) -> TechStackAnalysis:
        """分析项目技术栈"""
        analysis = TechStackAnalysis()

        analysis.components = self._detect_from_imports(project_path)
        analysis.components.extend(self._detect_from_config_files(project_path))

        for component in analysis.components:
            if component.category == TechCategory.FRAMEWORK:
                analysis.frameworks.append(component)
            elif component.category == TechCategory.DATABASE:
                analysis.databases.append(component)
            elif component.category in (TechCategory.ORM, TechCategory.VALIDATION, TechCategory.HTTP_CLIENT):
                analysis.libraries.append(component)
            else:
                analysis.tools.append(component)

        analysis.summary = self._generate_summary(analysis)

        return analysis

    def analyze_module(self, module: ModuleInfo) -> list[TechComponent]:
        """从模块分析技术栈"""
        components = []

        for imp in module.imports:
            component = self._identify_component(imp.module)
            if component:
                component.usage_locations.append(module.name)
                components.append(component)

        return components

    def _detect_from_imports(self, project_path: Path) -> list[TechComponent]:
        """从导入语句检测技术栈"""
        components = []
        detected_names = set()

        for py_file in project_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                import_lines = self._extract_imports(content)

                for module_name in import_lines:
                    component = self._identify_component(module_name)
                    if component and component.name not in detected_names:
                        detected_names.add(component.name)
                        component.usage_locations.append(str(py_file.relative_to(project_path)))
                        components.append(component)
            except Exception:
                continue

        return components

    def _detect_from_config_files(self, project_path: Path) -> list[TechComponent]:
        """从配置文件检测技术栈"""
        components = []

        config_files = {
            "pyproject.toml": self._parse_pyproject,
            "requirements.txt": self._parse_requirements,
            "setup.py": self._parse_setup,
            "Pipfile": self._parse_pipfile,
            "poetry.lock": self._parse_poetry_lock,
        }

        for config_name, parser in config_files.items():
            config_path = project_path / config_name
            if config_path.exists():
                try:
                    parsed = parser(config_path)
                    for name, version in parsed.items():
                        component = self._identify_component(name)
                        if component:
                            component.version = version
                            component.config_files.append(config_name)
                            components.append(component)
                except Exception:
                    continue

        return components

    def _extract_imports(self, content: str) -> list[str]:
        """提取导入语句"""
        imports = []
        import re

        patterns = [
            r"^import\s+(\w+)",
            r"^from\s+(\w+)",
        ]

        for line in content.split("\n"):
            for pattern in patterns:
                match = re.match(pattern, line.strip())
                if match:
                    imports.append(match.group(1))

        return imports

    def _identify_component(self, module_name: str) -> Optional[TechComponent]:
        """识别技术组件"""
        base_module = module_name.split(".")[0].lower()

        if base_module in self._tech_database:
            info = self._tech_database[base_module]
            return TechComponent(
                name=info["name"],
                category=TechCategory(info["category"]),
                description=info.get("description", ""),
            )

        return None

    def _parse_pyproject(self, file_path: Path) -> dict:
        """解析 pyproject.toml"""
        try:
            import tomllib
            with open(file_path, "rb") as f:
                data = tomllib.load(f)

            deps = {}
            if "project" in data and "dependencies" in data["project"]:
                for dep in data["project"]["dependencies"]:
                    name, version = self._parse_dependency_string(dep)
                    if name:
                        deps[name] = version

            if "tool" in data and "poetry" in data["tool"]:
                for dep_name, dep_info in data["tool"]["poetry"].get("dependencies", {}).items():
                    if isinstance(dep_info, str):
                        deps[dep_name.lower()] = dep_info
                    elif isinstance(dep_info, dict) and "version" in dep_info:
                        deps[dep_name.lower()] = dep_info["version"]

            return deps
        except Exception:
            return {}

    def _parse_requirements(self, file_path: Path) -> dict:
        """解析 requirements.txt"""
        deps = {}
        for line in file_path.read_text().split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                name, version = self._parse_dependency_string(line)
                if name:
                    deps[name] = version
        return deps

    def _parse_setup(self, file_path: Path) -> dict:
        """解析 setup.py"""
        return {}

    def _parse_pipfile(self, file_path: Path) -> dict:
        """解析 Pipfile"""
        return {}

    def _parse_poetry_lock(self, file_path: Path) -> dict:
        """解析 poetry.lock"""
        return {}

    def _parse_dependency_string(self, dep_str: str) -> tuple[str, Optional[str]]:
        """解析依赖字符串"""
        import re

        match = re.match(r"^([a-zA-Z0-9_-]+)\s*([<>=!~]+\s*[\d.]+)?", dep_str.strip())
        if match:
            name = match.group(1).lower()
            version = match.group(2).strip() if match.group(2) else None
            return name, version
        return "", None

    def _generate_summary(self, analysis: TechStackAnalysis) -> dict:
        """生成摘要"""
        return {
            "total_components": len(analysis.components),
            "frameworks_count": len(analysis.frameworks),
            "databases_count": len(analysis.databases),
            "libraries_count": len(analysis.libraries),
            "tools_count": len(analysis.tools),
            "primary_framework": analysis.frameworks[0].name if analysis.frameworks else None,
            "primary_database": analysis.databases[0].name if analysis.databases else None,
        }

    def _load_tech_database(self) -> dict:
        """加载技术数据库"""
        return {
            "flask": {"name": "Flask", "category": "framework", "description": "轻量级 Web 框架"},
            "django": {"name": "Django", "category": "framework", "description": "全功能 Web 框架"},
            "fastapi": {"name": "FastAPI", "category": "framework", "description": "高性能异步 API 框架"},
            "starlette": {"name": "Starlette", "category": "framework", "description": "轻量级 ASGI 框架"},
            "tornado": {"name": "Tornado", "category": "framework", "description": "异步 Web 框架"},
            "aiohttp": {"name": "AIOHTTP", "category": "framework", "description": "异步 HTTP 客户端/服务器"},

            "sqlalchemy": {"name": "SQLAlchemy", "category": "orm", "description": "Python ORM"},
            "django.db": {"name": "Django ORM", "category": "orm", "description": "Django 内置 ORM"},
            "peewee": {"name": "Peewee", "category": "orm", "description": "轻量级 ORM"},
            "tortoise": {"name": "Tortoise ORM", "category": "orm", "description": "异步 ORM"},
            "mongoengine": {"name": "MongoEngine", "category": "orm", "description": "MongoDB ODM"},

            "pymongo": {"name": "PyMongo", "category": "database", "description": "MongoDB 驱动"},
            "redis": {"name": "Redis", "category": "cache", "description": "Redis 客户端"},
            "aioredis": {"name": "AIORedis", "category": "cache", "description": "异步 Redis 客户端"},
            "psycopg": {"name": "Psycopg", "category": "database", "description": "PostgreSQL 适配器"},
            "mysql": {"name": "MySQL Connector", "category": "database", "description": "MySQL 连接器"},
            "sqlite": {"name": "SQLite", "category": "database", "description": "SQLite 数据库"},

            "celery": {"name": "Celery", "category": "task_queue", "description": "分布式任务队列"},
            "dramatiq": {"name": "Dramatiq", "category": "task_queue", "description": "任务队列"},
            "huey": {"name": "Huey", "category": "task_queue", "description": "轻量级任务队列"},
            "rq": {"name": "RQ", "category": "task_queue", "description": "Redis 队列"},

            "kafka": {"name": "Kafka", "category": "message_queue", "description": "Kafka 客户端"},
            "pika": {"name": "Pika", "category": "message_queue", "description": "RabbitMQ 客户端"},
            "aio_pika": {"name": "AIO Pika", "category": "message_queue", "description": "异步 RabbitMQ"},

            "pytest": {"name": "Pytest", "category": "testing", "description": "测试框架"},
            "unittest": {"name": "Unittest", "category": "testing", "description": "内置测试框架"},
            "nose": {"name": "Nose", "category": "testing", "description": "测试框架"},
            "hypothesis": {"name": "Hypothesis", "category": "testing", "description": "属性测试"},

            "pydantic": {"name": "Pydantic", "category": "validation", "description": "数据验证"},
            "marshmallow": {"name": "Marshmallow", "category": "validation", "description": "对象序列化"},
            "cerberus": {"name": "Cerberus", "category": "validation", "description": "数据验证"},

            "requests": {"name": "Requests", "category": "http_client", "description": "HTTP 客户端"},
            "httpx": {"name": "HTTPX", "category": "http_client", "description": "异步 HTTP 客户端"},
            "urllib3": {"name": "urllib3", "category": "http_client", "description": "HTTP 库"},

            "asyncio": {"name": "Asyncio", "category": "async", "description": "异步 IO"},
            "trio": {"name": "Trio", "category": "async", "description": "异步框架"},

            "cryptography": {"name": "Cryptography", "category": "security", "description": "加密库"},
            "passlib": {"name": "Passlib", "category": "security", "description": "密码哈希"},
            "jwt": {"name": "PyJWT", "category": "security", "description": "JWT 处理"},
            "authlib": {"name": "Authlib", "category": "security", "description": "认证库"},

            "logging": {"name": "Logging", "category": "logging", "description": "日志模块"},
            "loguru": {"name": "Loguru", "category": "logging", "description": "日志库"},
            "structlog": {"name": "Structlog", "category": "logging", "description": "结构化日志"},

            "pyyaml": {"name": "PyYAML", "category": "config", "description": "YAML 解析"},
            "toml": {"name": "TOML", "category": "config", "description": "TOML 解析"},
            "dynaconf": {"name": "Dynaconf", "category": "config", "description": "配置管理"},
            "python-dotenv": {"name": "Python-dotenv", "category": "config", "description": "环境变量"},

            "prometheus": {"name": "Prometheus", "category": "monitoring", "description": "监控"},
            "sentry": {"name": "Sentry", "category": "monitoring", "description": "错误追踪"},
            "opentelemetry": {"name": "OpenTelemetry", "category": "monitoring", "description": "可观测性"},

            "boto3": {"name": "Boto3", "category": "cloud", "description": "AWS SDK"},
            "google.cloud": {"name": "Google Cloud", "category": "cloud", "description": "GCP SDK"},
            "azure": {"name": "Azure SDK", "category": "cloud", "description": "Azure SDK"},
        }

    def generate_tech_report(self, analysis: TechStackAnalysis) -> dict:
        """生成技术栈报告"""
        return {
            "summary": analysis.summary,
            "frameworks": [
                {"name": f.name, "description": f.description, "version": f.version}
                for f in analysis.frameworks
            ],
            "databases": [
                {"name": d.name, "description": d.description}
                for d in analysis.databases
            ],
            "libraries": [
                {"name": l.name, "category": l.category.value, "description": l.description}
                for l in analysis.libraries
            ],
            "tools": [
                {"name": t.name, "category": t.category.value, "description": t.description}
                for t in analysis.tools
            ],
        }
