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
    BUILD_TOOL = "build_tool"
    FRONTEND = "frontend"
    UI_LIBRARY = "ui_library"
    STATE_MANAGEMENT = "state_management"
    TEMPLATE_ENGINE = "template_engine"
    WEBSOCKET = "websocket"
    SERIALIZATION = "serialization"


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

    def __init__(self, project_language: Optional[str] = None):
        self._tech_database = self._load_tech_database()
        self._project_language = project_language

    def analyze_project(self, project_path: Path) -> TechStackAnalysis:
        """分析项目技术栈 - 改进版，支持验证和修正"""
        analysis = TechStackAnalysis()
        self._project_path = project_path  # 保存项目路径供验证使用

        # 1. 从配置文件检测（优先级更高，信息更准确）
        config_components = self._detect_from_config_files(project_path)

        # 2. 从导入语句检测
        import_components = self._detect_from_imports(project_path)

        # 3. 从构建文件检测
        build_components = self._detect_from_build_files(project_path)

        # 合并并去重（按名称），优先保留有版本信息的组件
        all_components = {}
        for comp in config_components + import_components + build_components:
            if comp.name not in all_components:
                all_components[comp.name] = comp
            else:
                # 合并使用位置
                existing = all_components[comp.name]
                existing.usage_locations.extend(comp.usage_locations)
                existing.usage_locations = list(set(existing.usage_locations))  # 去重
                # 保留版本信息
                if comp.version and not existing.version:
                    existing.version = comp.version
                # 合并配置文件来源
                existing.config_files.extend(comp.config_files)
                existing.config_files = list(set(existing.config_files))

        analysis.components = list(all_components.values())

        # 分类组件
        for component in analysis.components:
            self._categorize_component(component, analysis)

        # 验证和修正
        self._validate_and_fix(analysis, project_path)

        analysis.summary = self._generate_summary(analysis)
        return analysis

    def _categorize_component(self, component: TechComponent, analysis: TechStackAnalysis):
        """将组件分类到对应的列表"""
        if component.category == TechCategory.FRAMEWORK:
            analysis.frameworks.append(component)
        elif component.category == TechCategory.DATABASE:
            analysis.databases.append(component)
        elif component.category in (TechCategory.ORM, TechCategory.VALIDATION, TechCategory.HTTP_CLIENT,
                                     TechCategory.FRONTEND, TechCategory.UI_LIBRARY, TechCategory.STATE_MANAGEMENT):
            analysis.libraries.append(component)
        else:
            analysis.tools.append(component)

    def _validate_and_fix(self, analysis: TechStackAnalysis, project_path: Path):
        """验证并修正技术栈分析结果"""
        # 修正1: 处理 ORM 框架冲突
        # 如果同时检测到 Hibernate 和 MyBatis，优先保留 MyBatis（可能是传递依赖）
        has_hibernate = any(c.name == "Hibernate" for c in analysis.components)
        has_mybatis = any(c.name in ["MyBatis", "MyBatis-Plus"] for c in analysis.components)

        if has_hibernate and has_mybatis:
            # 移除 Hibernate
            analysis.components = [c for c in analysis.components if c.name != "Hibernate"]
            analysis.libraries = [c for c in analysis.libraries if c.name != "Hibernate"]

        # 修正2: 验证前端框架（根据项目结构）
        self._validate_frontend_frameworks(analysis, project_path)

        # 修正3: 移除标准库（Python/Java 内置模块）
        stdlib_names = {"ABC", "Typing", "Sys", "OS", "Re", "JSON", "Time", "Datetime", "Pathlib",
                        "Collections", "Itertools", "Functools", "Dataclasses", "Enum", "Copy", "IO",
                        "Pickle", "Threading", "Multiprocessing", "Socket", "SSL", "Hashlib", "HMAC",
                        "Secrets", "UUID", "Random", "Math", "Decimal", "Fractions", "Statistics"}
        analysis.components = [c for c in analysis.components if c.name not in stdlib_names]
        analysis.libraries = [c for c in analysis.libraries if c.name not in stdlib_names]
        analysis.tools = [c for c in analysis.tools if c.name not in stdlib_names]

        # 修正4: 确保数据库连接池有正确描述
        for comp in analysis.components:
            if comp.name in ["Druid", "HikariCP"]:
                comp.description = "数据库连接池"

    def _validate_frontend_frameworks(self, analysis: TechStackAnalysis, project_path: Path):
        """验证前端框架是否真实存在"""
        frontend_indicators = {
            "Vue": ["vue.config.js", "vue.config.ts", "vite.config.ts", "nuxt.config.ts", "nuxt.config.js"],
            "React": ["react-scripts", "next.config.js", "next.config.ts", "vite.config.ts"],
            "Angular": ["angular.json"],
        }

        # 检查项目根目录和子目录
        detected_frameworks = set()
        for framework, indicators in frontend_indicators.items():
            for indicator in indicators:
                if list(project_path.rglob(indicator)):
                    detected_frameworks.add(framework)
                    break

        # 如果没有检测到前端框架配置文件，移除前端相关技术
        if not detected_frameworks:
            frontend_names = {"React", "Vue", "Angular", "Svelte", "Next.js", "Nuxt.js",
                             "Ant Design", "Element Plus", "Element UI", "Vuetify",
                             "Material UI", "Redux", "Vuex", "Pinia"}
            analysis.components = [c for c in analysis.components if c.name not in frontend_names]
            analysis.libraries = [c for c in analysis.libraries if c.name not in frontend_names]
            analysis.frameworks = [c for c in analysis.frameworks if c.name not in frontend_names]

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
                    component = self._identify_component(module_name, "python")
                    if component and component.name not in detected_names:
                        detected_names.add(component.name)
                        component.usage_locations.append(str(py_file.relative_to(project_path)))
                        components.append(component)
            except Exception:
                continue

        for java_file in project_path.rglob("*.java"):
            try:
                content = java_file.read_text(encoding="utf-8")
                imports = self._extract_java_imports(content)

                for module_name in imports:
                    component = self._identify_component(module_name, "java")
                    if component and component.name not in detected_names:
                        detected_names.add(component.name)
                        component.usage_locations.append(str(java_file.relative_to(project_path)))
                        components.append(component)
            except Exception:
                continue

        for ts_file in list(project_path.rglob("*.ts")) + list(project_path.rglob("*.tsx")):
            try:
                content = ts_file.read_text(encoding="utf-8")
                imports = self._extract_ts_imports(content)

                for module_name in imports:
                    component = self._identify_component(module_name, "typescript")
                    if component and component.name not in detected_names:
                        detected_names.add(component.name)
                        component.usage_locations.append(str(ts_file.relative_to(project_path)))
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
            "package.json": self._parse_package_json,
            "pom.xml": self._parse_pom_xml,
            "build.gradle": self._parse_build_gradle,
            "build.gradle.kts": self._parse_build_gradle,
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

    def _detect_from_build_files(self, project_path: Path) -> list[TechComponent]:
        """从构建文件检测技术栈"""
        components = []

        if (project_path / "pom.xml").exists():
            components.append(TechComponent(
                name="Maven",
                category=TechCategory.BUILD_TOOL,
                description="Java 构建工具",
                config_files=["pom.xml"]
            ))

        if (project_path / "build.gradle").exists() or (project_path / "build.gradle.kts").exists():
            components.append(TechComponent(
                name="Gradle",
                category=TechCategory.BUILD_TOOL,
                description="Java/Kotlin 构建工具",
                config_files=["build.gradle"]
            ))

        if (project_path / "package.json").exists():
            components.append(TechComponent(
                name="npm",
                category=TechCategory.BUILD_TOOL,
                description="Node.js 包管理器",
                config_files=["package.json"]
            ))

        if (project_path / "yarn.lock").exists():
            components.append(TechComponent(
                name="Yarn",
                category=TechCategory.BUILD_TOOL,
                description="Node.js 包管理器",
                config_files=["yarn.lock"]
            ))

        if (project_path / "pnpm-lock.yaml").exists():
            components.append(TechComponent(
                name="pnpm",
                category=TechCategory.BUILD_TOOL,
                description="Node.js 包管理器",
                config_files=["pnpm-lock.yaml"]
            ))

        return components

    def _extract_imports(self, content: str) -> list[str]:
        """提取 Python 导入语句"""
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

    def _extract_java_imports(self, content: str) -> list[str]:
        """提取 Java 导入语句"""
        imports = []
        import re

        pattern = r'^import\s+([\w.]+);?'
        for line in content.split("\n"):
            match = re.match(pattern, line.strip())
            if match:
                imports.append(match.group(1))

        return imports

    def _extract_ts_imports(self, content: str) -> list[str]:
        """提取 TypeScript/JavaScript 导入语句"""
        imports = []
        import re

        patterns = [
            r'^import\s+.*from\s+[\'"]([^\'"]+)[\'"]',
            r'^import\s+[\'"]([^\'"]+)[\'"]',
            r'^const\s+\w+\s*=\s*require\([\'"]([^\'"]+)[\'"]\)',
        ]

        for line in content.split("\n"):
            for pattern in patterns:
                match = re.search(pattern, line.strip())
                if match:
                    module = match.group(1)
                    if not module.startswith('.'):
                        imports.append(module)
                    break

        return imports

    def _identify_component(self, module_name: str, source_language: Optional[str] = None) -> Optional[TechComponent]:
        """识别技术组件 - 使用三级匹配策略"""
        module_lower = module_name.lower()
        effective_language = source_language or self._project_language

        # 策略1: 完整包名前缀匹配（最精确，优先）
        # 例如：com.alibaba.druid 匹配 com.alibaba.druid
        # 按包名长度降序排序，优先匹配更具体的包（如 org.springframework.boot 优先于 org.springframework）
        sorted_packages = sorted(
            [(k, v) for k, v in self._tech_database.items() if "." in k],
            key=lambda x: len(x[0]),
            reverse=True
        )
        for full_package, info in sorted_packages:
            if module_lower.startswith(full_package.lower()):
                if self._is_compatible_language(info, effective_language):
                    return TechComponent(
                        name=info["name"],
                        category=TechCategory(info["category"]),
                        description=info.get("description", ""),
                    )

        # 策略2: 基础模块名匹配（用于简单导入如 "react", "vue", "flask"）
        base_module = module_name.split(".")[0].lower()
        if base_module in self._tech_database:
            info = self._tech_database[base_module]
            if self._is_compatible_language(info, effective_language):
                return TechComponent(
                    name=info["name"],
                    category=TechCategory(info["category"]),
                    description=info.get("description", ""),
                )

        # 策略3: 部分匹配（用于复杂包名中的关键字匹配）
        # 例如：org.springframework.boot 匹配 org.springframework.boot（更长的优先）
        # 按包名长度降序排序，优先匹配更具体的包
        sorted_tech_items = sorted(
            [(k, v) for k, v in self._tech_database.items() if "." in k],
            key=lambda x: len(x[0]),
            reverse=True
        )
        for tech_key, info in sorted_tech_items:
            if tech_key in module_lower:
                if self._is_compatible_language(info, effective_language):
                    return TechComponent(
                        name=info["name"],
                        category=TechCategory(info["category"]),
                        description=info.get("description", ""),
                    )

        return None

    def _is_compatible_language(self, tech_info: dict, source_language: Optional[str] = None) -> bool:
        """检查技术是否与项目语言兼容"""
        effective_language = source_language or self._project_language
        if not effective_language:
            return True
        
        tech_languages = tech_info.get("languages", [])
        if not tech_languages:
            tech_key = tech_info.get("name", "").lower()
            tech_languages = self._infer_tech_languages(tech_key, tech_info)
            if not tech_languages:
                return True
        
        return effective_language.lower() in [lang.lower() for lang in tech_languages]

    def _infer_tech_languages(self, tech_key: str, tech_info: dict) -> list[str]:
        """根据技术名称推断适用的语言"""
        java_prefixes = ("org.", "com.", "io.", "net.", "javax.", "jakarta.")
        ts_prefixes = ("@", "react-", "vue-", "@angular", "@nestjs", "@prisma", "@mui", "@redux", "@apollo", "@playwright")
        
        name_lower = tech_key.lower()
        description = tech_info.get("description", "").lower()
        
        if any(name_lower.startswith(prefix) for prefix in java_prefixes):
            return ["java"]
        
        if any(name_lower.startswith(prefix) for prefix in ts_prefixes):
            return ["typescript", "javascript"]
        
        if "java" in description or "spring" in description or "mybatis" in description:
            return ["java"]
        
        if "node.js" in description or "javascript" in description or "typescript" in description or "react" in description or "vue" in description:
            return ["typescript", "javascript"]
        
        if "python" in description or "django" in description or "flask" in description or "fastapi" in description:
            return ["python"]
        
        return []

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

    def _parse_package_json(self, file_path: Path) -> dict:
        """解析 package.json"""
        import json
        deps = {}
        try:
            content = file_path.read_text(encoding="utf-8")
            data = json.loads(content)

            for name, version in data.get("dependencies", {}).items():
                deps[name.lower()] = version
            for name, version in data.get("devDependencies", {}).items():
                deps[name.lower()] = version
        except Exception:
            pass
        return deps

    def _parse_pom_xml(self, file_path: Path) -> dict:
        """解析 pom.xml - 改进版，支持 scope 过滤和 parent 解析"""
        deps = {}
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(file_path)
            root = tree.getroot()

            ns = {'m': 'http://maven.apache.org/POM/4.0.0'}

            # 解析 dependencies
            for dep in root.findall('.//m:dependency', ns):
                group_id = dep.find('m:groupId', ns)
                artifact_id = dep.find('m:artifactId', ns)
                version = dep.find('m:version', ns)
                scope = dep.find('m:scope', ns)

                if group_id is not None and artifact_id is not None:
                    # 跳过 test 和 provided 依赖
                    if scope is not None and scope.text in ('test', 'provided'):
                        continue

                    name = f"{group_id.text}:{artifact_id.text}"
                    ver = version.text if version is not None else None
                    deps[name] = ver

            # 解析 dependencyManagement（用于获取版本号）
            for dep in root.findall('.//m:dependencyManagement/m:dependencies/m:dependency', ns):
                group_id = dep.find('m:groupId', ns)
                artifact_id = dep.find('m:artifactId', ns)
                version = dep.find('m:version', ns)

                if group_id is not None and artifact_id is not None:
                    name = f"{group_id.text}:{artifact_id.text}"
                    if name not in deps or deps[name] is None:
                        ver = version.text if version is not None else None
                        deps[name] = ver

            # 解析 parent
            parent = root.find('m:parent', ns)
            if parent is not None:
                parent_group = parent.find('m:groupId', ns)
                parent_artifact = parent.find('m:artifactId', ns)
                parent_version = parent.find('m:version', ns)
                if parent_group is not None and parent_artifact is not None:
                    name = f"{parent_group.text}:{parent_artifact.text}"
                    ver = parent_version.text if parent_version is not None else None
                    deps[name] = ver

        except Exception as e:
            # 静默处理解析错误，但保留调试可能性
            pass

        return deps

    def _parse_build_gradle(self, file_path: Path) -> dict:
        """解析 build.gradle"""
        deps = {}
        try:
            content = file_path.read_text(encoding="utf-8")
            import re

            patterns = [
                r"implementation\s*[\'\"]([^\'\":]+):([^\'\":]+):([^\'\"]+)[\'\"]",
                r"compile\s*[\'\"]([^\'\":]+):([^\'\":]+):([^\'\"]+)[\'\"]",
                r"api\s*[\'\"]([^\'\":]+):([^\'\":]+):([^\'\"]+)[\'\"]",
            ]

            for pattern in patterns:
                for match in re.finditer(pattern, content):
                    group_id = match.group(1)
                    artifact_id = match.group(2)
                    version = match.group(3)
                    name = f"{group_id}:{artifact_id}"
                    deps[name] = version
        except Exception:
            pass
        return deps

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
            "sanic": {"name": "Sanic", "category": "framework", "description": "异步 Web 框架"},
            "bottle": {"name": "Bottle", "category": "framework", "description": "微型 Web 框架"},
            "pyramid": {"name": "Pyramid", "category": "framework", "description": "通用 Web 框架"},

            "sqlalchemy": {"name": "SQLAlchemy", "category": "orm", "description": "Python ORM"},
            "django.db": {"name": "Django ORM", "category": "orm", "description": "Django 内置 ORM"},
            "peewee": {"name": "Peewee", "category": "orm", "description": "轻量级 ORM"},
            "tortoise": {"name": "Tortoise ORM", "category": "orm", "description": "异步 ORM"},
            "mongoengine": {"name": "MongoEngine", "category": "orm", "description": "MongoDB ODM"},
            "pony": {"name": "Pony", "category": "orm", "description": "ORM with identity map"},

            "pymongo": {"name": "PyMongo", "category": "database", "description": "MongoDB 驱动"},
            "redis": {"name": "Redis", "category": "cache", "description": "Redis 客户端"},
            "aioredis": {"name": "AIORedis", "category": "cache", "description": "异步 Redis 客户端"},
            "psycopg": {"name": "Psycopg", "category": "database", "description": "PostgreSQL 适配器"},
            "mysql": {"name": "MySQL Connector", "category": "database", "description": "MySQL 连接器"},
            "sqlite": {"name": "SQLite", "category": "database", "description": "SQLite 数据库"},
            "elasticsearch": {"name": "Elasticsearch", "category": "database", "description": "搜索引擎"},
            "pika": {"name": "Pika", "category": "message_queue", "description": "RabbitMQ 客户端"},

            "celery": {"name": "Celery", "category": "task_queue", "description": "分布式任务队列", "languages": ["python"]},
            "dramatiq": {"name": "Dramatiq", "category": "task_queue", "description": "任务队列", "languages": ["python"]},
            "huey": {"name": "Huey", "category": "task_queue", "description": "轻量级任务队列", "languages": ["python"]},
            "rq": {"name": "RQ", "category": "task_queue", "description": "Redis 队列", "languages": ["python"]},
            "dramatiq": {"name": "Dramatiq", "category": "task_queue", "description": "任务队列", "languages": ["python"]},

            "kafka": {"name": "Kafka", "category": "message_queue", "description": "Kafka 客户端", "languages": ["python"]},
            "aio_pika": {"name": "AIO Pika", "category": "message_queue", "description": "异步 RabbitMQ", "languages": ["python"]},
            "confluent_kafka": {"name": "Confluent Kafka", "category": "message_queue", "description": "Kafka 客户端", "languages": ["python"]},

            "pytest": {"name": "Pytest", "category": "testing", "description": "测试框架", "languages": ["python"]},
            "unittest": {"name": "Unittest", "category": "testing", "description": "内置测试框架", "languages": ["python"]},
            "nose": {"name": "Nose", "category": "testing", "description": "测试框架", "languages": ["python"]},
            "hypothesis": {"name": "Hypothesis", "category": "testing", "description": "属性测试", "languages": ["python"]},
            "faker": {"name": "Faker", "category": "testing", "description": "测试数据生成", "languages": ["python"]},
            "mock": {"name": "Mock", "category": "testing", "description": "Mock 库", "languages": ["python"]},

            "pydantic": {"name": "Pydantic", "category": "validation", "description": "数据验证", "languages": ["python"]},
            "marshmallow": {"name": "Marshmallow", "category": "validation", "description": "对象序列化", "languages": ["python"]},
            "cerberus": {"name": "Cerberus", "category": "validation", "description": "数据验证", "languages": ["python"]},
            "voluptuous": {"name": "Voluptuous", "category": "validation", "description": "数据验证", "languages": ["python"]},

            "requests": {"name": "Requests", "category": "http_client", "description": "HTTP 客户端", "languages": ["python"]},
            "httpx": {"name": "HTTPX", "category": "http_client", "description": "异步 HTTP 客户端", "languages": ["python"]},
            "urllib3": {"name": "urllib3", "category": "http_client", "description": "HTTP 库", "languages": ["python"]},
            "aiohttp": {"name": "AIOHTTP", "category": "http_client", "description": "异步 HTTP 客户端", "languages": ["python"]},

            "asyncio": {"name": "Asyncio", "category": "async", "description": "异步 IO", "languages": ["python"]},
            "trio": {"name": "Trio", "category": "async", "description": "异步框架", "languages": ["python"]},
            "anyio": {"name": "AnyIO", "category": "async", "description": "异步兼容层", "languages": ["python"]},

            "cryptography": {"name": "Cryptography", "category": "security", "description": "加密库", "languages": ["python"]},
            "passlib": {"name": "Passlib", "category": "security", "description": "密码哈希", "languages": ["python"]},
            "jwt": {"name": "PyJWT", "category": "security", "description": "JWT 处理", "languages": ["python"]},
            "authlib": {"name": "Authlib", "category": "security", "description": "认证库", "languages": ["python"]},
            "bcrypt": {"name": "Bcrypt", "category": "security", "description": "密码哈希", "languages": ["python"]},

            "logging": {"name": "Logging", "category": "logging", "description": "日志模块", "languages": ["python"]},
            "loguru": {"name": "Loguru", "category": "logging", "description": "日志库", "languages": ["python"]},
            "structlog": {"name": "Structlog", "category": "logging", "description": "结构化日志", "languages": ["python"]},

            "pyyaml": {"name": "PyYAML", "category": "config", "description": "YAML 解析", "languages": ["python"]},
            "toml": {"name": "TOML", "category": "config", "description": "TOML 解析", "languages": ["python"]},
            "dynaconf": {"name": "Dynaconf", "category": "config", "description": "配置管理", "languages": ["python"]},
            "python-dotenv": {"name": "Python-dotenv", "category": "config", "description": "环境变量", "languages": ["python"]},
            "dotenv": {"name": "Python-dotenv", "category": "config", "description": "环境变量", "languages": ["python"]},

            "prometheus": {"name": "Prometheus", "category": "monitoring", "description": "监控", "languages": ["python"]},
            "prometheus_client": {"name": "Prometheus Client", "category": "monitoring", "description": "Prometheus 客户端", "languages": ["python"]},
            "sentry": {"name": "Sentry", "category": "monitoring", "description": "错误追踪", "languages": ["python"]},
            "opentelemetry": {"name": "OpenTelemetry", "category": "monitoring", "description": "可观测性", "languages": ["python"]},

            "boto3": {"name": "Boto3", "category": "cloud", "description": "AWS SDK", "languages": ["python"]},
            "google.cloud": {"name": "Google Cloud", "category": "cloud", "description": "GCP SDK", "languages": ["python"]},
            "azure": {"name": "Azure SDK", "category": "cloud", "description": "Azure SDK", "languages": ["python"]},

            "pandas": {"name": "Pandas", "category": "orm", "description": "数据处理库", "languages": ["python"]},
            "numpy": {"name": "NumPy", "category": "orm", "description": "数值计算库", "languages": ["python"]},
            "scipy": {"name": "SciPy", "category": "orm", "description": "科学计算库", "languages": ["python"]},
            "sklearn": {"name": "Scikit-learn", "category": "orm", "description": "机器学习库", "languages": ["python"]},
            "torch": {"name": "PyTorch", "category": "orm", "description": "深度学习框架", "languages": ["python"]},
            "tensorflow": {"name": "TensorFlow", "category": "orm", "description": "深度学习框架", "languages": ["python"]},
            "transformers": {"name": "Transformers", "category": "orm", "description": "Hugging Face Transformers", "languages": ["python"]},

            "click": {"name": "Click", "category": "config", "description": "命令行工具库", "languages": ["python"]},
            "typer": {"name": "Typer", "category": "config", "description": "命令行工具库", "languages": ["python"]},
            "rich": {"name": "Rich", "category": "config", "description": "终端美化库", "languages": ["python"]},
            "argparse": {"name": "Argparse", "category": "config", "description": "命令行参数解析", "languages": ["python"]},

            "jinja2": {"name": "Jinja2", "category": "template_engine", "description": "模板引擎", "languages": ["python"]},
            "mako": {"name": "Mako", "category": "template_engine", "description": "模板引擎", "languages": ["python"]},
            "chameleon": {"name": "Chameleon", "category": "template_engine", "description": "模板引擎", "languages": ["python"]},

            "websockets": {"name": "WebSockets", "category": "websocket", "description": "WebSocket 库", "languages": ["python"]},
            "socketio": {"name": "Socket.IO", "category": "websocket", "description": "WebSocket 库", "languages": ["python"]},

            "orjson": {"name": "Orjson", "category": "serialization", "description": "高性能 JSON 库", "languages": ["python"]},
            "msgpack": {"name": "Msgpack", "category": "serialization", "description": "MessagePack 库", "languages": ["python"]},
            "ujson": {"name": "UJSON", "category": "serialization", "description": "快速 JSON 库", "languages": ["python"]},

            "abc": {"name": "ABC", "category": "config", "description": "抽象基类模块", "languages": ["python"]},
            "typing": {"name": "Typing", "category": "config", "description": "类型提示模块", "languages": ["python"]},
            "sys": {"name": "Sys", "category": "config", "description": "系统模块", "languages": ["python"]},
            "os": {"name": "OS", "category": "config", "description": "操作系统模块", "languages": ["python"]},
            "re": {"name": "Re", "category": "config", "description": "正则表达式模块", "languages": ["python"]},
            "json": {"name": "JSON", "category": "serialization", "description": "JSON 模块", "languages": ["python"]},
            "time": {"name": "Time", "category": "config", "description": "时间模块", "languages": ["python"]},
            "datetime": {"name": "Datetime", "category": "config", "description": "日期时间模块", "languages": ["python"]},
            "pathlib": {"name": "Pathlib", "category": "config", "description": "路径模块", "languages": ["python"]},
            "collections": {"name": "Collections", "category": "config", "description": "集合模块", "languages": ["python"]},
            "itertools": {"name": "Itertools", "category": "config", "description": "迭代器模块", "languages": ["python"]},
            "functools": {"name": "Functools", "category": "config", "description": "函数工具模块", "languages": ["python"]},
            "dataclasses": {"name": "Dataclasses", "category": "config", "description": "数据类模块", "languages": ["python"]},
            "enum": {"name": "Enum", "category": "config", "description": "枚举模块", "languages": ["python"]},
            "copy": {"name": "Copy", "category": "config", "description": "复制模块", "languages": ["python"]},
            "io": {"name": "IO", "category": "config", "description": "IO模块", "languages": ["python"]},
            "pickle": {"name": "Pickle", "category": "serialization", "description": "序列化模块", "languages": ["python"]},
            "threading": {"name": "Threading", "category": "async", "description": "线程模块", "languages": ["python"]},
            "multiprocessing": {"name": "Multiprocessing", "category": "async", "description": "多进程模块", "languages": ["python"]},
            "socket": {"name": "Socket", "category": "async", "description": "套接字模块", "languages": ["python"]},
            "ssl": {"name": "SSL", "category": "security", "description": "SSL模块", "languages": ["python"]},
            "hashlib": {"name": "Hashlib", "category": "security", "description": "哈希模块", "languages": ["python"]},
            "hmac": {"name": "HMAC", "category": "security", "description": "HMAC模块", "languages": ["python"]},
            "secrets": {"name": "Secrets", "category": "security", "description": "安全随机模块", "languages": ["python"]},
            "uuid": {"name": "UUID", "category": "config", "description": "UUID模块", "languages": ["python"]},
            "random": {"name": "Random", "category": "config", "description": "随机模块", "languages": ["python"]},
            "math": {"name": "Math", "category": "orm", "description": "数学模块", "languages": ["python"]},
            "decimal": {"name": "Decimal", "category": "orm", "description": "十进制模块", "languages": ["python"]},
            "fractions": {"name": "Fractions", "category": "orm", "description": "分数模块", "languages": ["python"]},
            "statistics": {"name": "Statistics", "category": "orm", "description": "统计模块", "languages": ["python"]},
            "tempfile": {"name": "Tempfile", "category": "config", "description": "临时文件模块", "languages": ["python"]},
            "shutil": {"name": "Shutil", "category": "config", "description": "文件操作模块", "languages": ["python"]},
            "glob": {"name": "Glob", "category": "config", "description": "文件匹配模块", "languages": ["python"]},
            "subprocess": {"name": "Subprocess", "category": "config", "description": "子进程模块", "languages": ["python"]},
            "contextlib": {"name": "Contextlib", "category": "config", "description": "上下文管理模块", "languages": ["python"]},
            "traceback": {"name": "Traceback", "category": "logging", "description": "追踪模块", "languages": ["python"]},
            "warnings": {"name": "Warnings", "category": "logging", "description": "警告模块", "languages": ["python"]},
            "weakref": {"name": "Weakref", "category": "config", "description": "弱引用模块", "languages": ["python"]},
            "heapq": {"name": "Heapq", "category": "config", "description": "堆队列模块", "languages": ["python"]},
            "bisect": {"name": "Bisect", "category": "config", "description": "二分查找模块", "languages": ["python"]},
            "array": {"name": "Array", "category": "orm", "description": "数组模块", "languages": ["python"]},
            "queue": {"name": "Queue", "category": "async", "description": "队列模块", "languages": ["python"]},
            "sched": {"name": "Sched", "category": "task_queue", "description": "调度模块", "languages": ["python"]},
            "html": {"name": "HTML", "category": "template_engine", "description": "HTML模块", "languages": ["python"]},
            "xml": {"name": "XML", "category": "serialization", "description": "XML模块", "languages": ["python"]},
            "csv": {"name": "CSV", "category": "serialization", "description": "CSV模块", "languages": ["python"]},
            "sqlite3": {"name": "SQLite3", "category": "database", "description": "SQLite模块", "languages": ["python"]},
            "zlib": {"name": "Zlib", "category": "config", "description": "压缩模块", "languages": ["python"]},
            "gzip": {"name": "Gzip", "category": "config", "description": "GZIP模块", "languages": ["python"]},
            "zipfile": {"name": "Zipfile", "category": "config", "description": "ZIP模块", "languages": ["python"]},
            "tarfile": {"name": "Tarfile", "category": "config", "description": "TAR模块", "languages": ["python"]},
            "base64": {"name": "Base64", "category": "serialization", "description": "Base64模块", "languages": ["python"]},
            "binascii": {"name": "Binascii", "category": "config", "description": "二进制ASCII模块", "languages": ["python"]},
            "struct": {"name": "Struct", "category": "serialization", "description": "结构体模块", "languages": ["python"]},
            "codecs": {"name": "Codecs", "category": "config", "description": "编解码模块", "languages": ["python"]},
            "locale": {"name": "Locale", "category": "config", "description": "本地化模块", "languages": ["python"]},
            "gettext": {"name": "Gettext", "category": "config", "description": "国际化模块", "languages": ["python"]},
            "argparse": {"name": "Argparse", "category": "config", "description": "命令行参数解析", "languages": ["python"]},
            "optparse": {"name": "Optparse", "category": "config", "description": "命令行选项解析", "languages": ["python"]},
            "getopt": {"name": "Getopt", "category": "config", "description": "命令行选项解析", "languages": ["python"]},
            "platform": {"name": "Platform", "category": "config", "description": "平台模块", "languages": ["python"]},
            "errno": {"name": "Errno", "category": "config", "description": "错误号模块", "languages": ["python"]},
            "signal": {"name": "Signal", "category": "async", "description": "信号模块", "languages": ["python"]},
            "mmap": {"name": "Mmap", "category": "config", "description": "内存映射模块", "languages": ["python"]},
            "select": {"name": "Select", "category": "async", "description": "IO多路复用模块", "languages": ["python"]},
            "selectors": {"name": "Selectors", "category": "async", "description": "选择器模块", "languages": ["python"]},
            "email": {"name": "Email", "category": "config", "description": "邮件模块", "languages": ["python"]},
            "smtplib": {"name": "Smtplib", "category": "http_client", "description": "SMTP模块", "languages": ["python"]},
            "poplib": {"name": "Poplib", "category": "http_client", "description": "POP3模块", "languages": ["python"]},
            "imaplib": {"name": "Imaplib", "category": "http_client", "description": "IMAP模块", "languages": ["python"]},
            "ftplib": {"name": "Ftplib", "category": "http_client", "description": "FTP模块", "languages": ["python"]},
            "http": {"name": "HTTP", "category": "http_client", "description": "HTTP模块", "languages": ["python"]},
            "urllib": {"name": "Urllib", "category": "http_client", "description": "URL模块", "languages": ["python"]},
            "xmlrpc": {"name": "XMLRPC", "category": "http_client", "description": "XML-RPC模块", "languages": ["python"]},
            "ipaddress": {"name": "Ipaddress", "category": "config", "description": "IP地址模块", "languages": ["python"]},
            "socketserver": {"name": "Socketserver", "category": "framework", "description": "套接字服务器模块", "languages": ["python"]},
            "http.server": {"name": "HTTP Server", "category": "framework", "description": "HTTP服务器模块", "languages": ["python"]},
            "cgi": {"name": "CGI", "category": "framework", "description": "CGI模块", "languages": ["python"]},
            "cgitb": {"name": "CGITB", "category": "logging", "description": "CGI追踪模块", "languages": ["python"]},
            "wsgiref": {"name": "WSGIRef", "category": "framework", "description": "WSGI参考模块", "languages": ["python"]},
            "asynchat": {"name": "Asynchat", "category": "async", "description": "异步聊天模块", "languages": ["python"]},
            "asyncore": {"name": "Asyncore", "category": "async", "description": "异步核心模块", "languages": ["python"]},

            "org.springframework": {"name": "Spring Framework", "category": "framework", "description": "Java 企业级框架", "languages": ["java"]},
            "org.springframework.boot": {"name": "Spring Boot", "category": "framework", "description": "Spring Boot 框架"},
            "org.springframework.cloud": {"name": "Spring Cloud", "category": "framework", "description": "微服务框架"},
            "org.springframework.security": {"name": "Spring Security", "category": "security", "description": "安全框架"},
            "org.springframework.data": {"name": "Spring Data", "category": "orm", "description": "数据访问框架"},

            "org.hibernate": {"name": "Hibernate", "category": "orm", "description": "Java ORM 框架"},
            "org.mybatis": {"name": "MyBatis", "category": "orm", "description": "Java 持久层框架"},
            "com.baomidou.mybatisplus": {"name": "MyBatis-Plus", "category": "orm", "description": "MyBatis 增强工具"},
            "org.apache.ibatis": {"name": "iBatis", "category": "orm", "description": "持久层框架"},

            "com.alibaba.fastjson": {"name": "Fastjson", "category": "serialization", "description": "JSON 库"},
            "com.fasterxml.jackson": {"name": "Jackson", "category": "serialization", "description": "JSON 库"},
            "com.google.gson": {"name": "Gson", "category": "serialization", "description": "JSON 库"},

            "org.apache.dubbo": {"name": "Dubbo", "category": "framework", "description": "RPC 框架"},
            "com.alibaba.dubbo": {"name": "Dubbo", "category": "framework", "description": "RPC 框架"},
            "io.grpc": {"name": "gRPC", "category": "framework", "description": "RPC 框架"},
            "org.apache.thrift": {"name": "Thrift", "category": "framework", "description": "RPC 框架"},

            "org.apache.kafka": {"name": "Kafka", "category": "message_queue", "description": "消息队列"},
            "org.apache.rocketmq": {"name": "RocketMQ", "category": "message_queue", "description": "消息队列"},
            "com.rabbitmq": {"name": "RabbitMQ", "category": "message_queue", "description": "消息队列"},

            "redis.clients": {"name": "Jedis", "category": "cache", "description": "Redis 客户端"},
            "io.lettuce": {"name": "Lettuce", "category": "cache", "description": "Redis 客户端"},
            "org.redisson": {"name": "Redisson", "category": "cache", "description": "Redis 客户端"},

            "com.mysql": {"name": "MySQL", "category": "database", "description": "MySQL 驱动"},
            "org.postgresql": {"name": "PostgreSQL", "category": "database", "description": "PostgreSQL 驱动"},
            "com.oracle": {"name": "Oracle", "category": "database", "description": "Oracle 驱动"},
            "org.mongodb": {"name": "MongoDB", "category": "database", "description": "MongoDB 驱动"},
            "io.lettuce.core": {"name": "Lettuce", "category": "database", "description": "Redis 客户端"},

            "org.apache.shiro": {"name": "Shiro", "category": "security", "description": "安全框架"},
            "io.jsonwebtoken": {"name": "JJWT", "category": "security", "description": "JWT 库"},

            "org.junit": {"name": "JUnit", "category": "testing", "description": "Java 测试框架"},
            "org.testng": {"name": "TestNG", "category": "testing", "description": "测试框架"},
            "org.mockito": {"name": "Mockito", "category": "testing", "description": "Mock 框架"},
            "org.assertj": {"name": "AssertJ", "category": "testing", "description": "断言库"},

            "io.netty": {"name": "Netty", "category": "async", "description": "网络框架"},
            "org.projectreactor": {"name": "Reactor", "category": "async", "description": "响应式编程"},
            "io.reactivex": {"name": "RxJava", "category": "async", "description": "响应式编程"},

            "org.apache.commons": {"name": "Apache Commons", "category": "orm", "description": "通用工具库"},
            "com.google.guava": {"name": "Guava", "category": "orm", "description": "Google 工具库"},
            "org.apache.http": {"name": "HttpClient", "category": "http_client", "description": "HTTP 客户端"},
            "okhttp3": {"name": "OkHttp", "category": "http_client", "description": "HTTP 客户端"},
            "okhttp": {"name": "OkHttp", "category": "http_client", "description": "HTTP 客户端"},
            "retrofit2": {"name": "Retrofit", "category": "http_client", "description": "HTTP 客户端"},
            "feign": {"name": "OpenFeign", "category": "http_client", "description": "HTTP 客户端"},

            "org.slf4j": {"name": "SLF4J", "category": "logging", "description": "日志门面"},
            "ch.qos.logback": {"name": "Logback", "category": "logging", "description": "日志框架"},
            "org.apache.logging": {"name": "Log4j", "category": "logging", "description": "日志框架"},

            "io.micrometer": {"name": "Micrometer", "category": "monitoring", "description": "监控门面"},
            "io.prometheus": {"name": "Prometheus", "category": "monitoring", "description": "监控"},
            "io.sentry": {"name": "Sentry", "category": "monitoring", "description": "错误追踪"},

            "io.kubernetes": {"name": "Kubernetes", "category": "cloud", "description": "Kubernetes 客户端"},
            "com.amazonaws": {"name": "AWS SDK", "category": "cloud", "description": "AWS SDK"},
            "com.google.cloud": {"name": "GCP SDK", "category": "cloud", "description": "Google Cloud SDK"},
            "com.azure": {"name": "Azure SDK", "category": "cloud", "description": "Azure SDK"},

            "com.alibaba.nacos": {"name": "Nacos", "category": "config", "description": "配置中心"},
            "org.apache.zookeeper": {"name": "ZooKeeper", "category": "config", "description": "配置中心"},
            "com.ctrip.framework.apollo": {"name": "Apollo", "category": "config", "description": "配置中心"},

            "com.alibaba.druid": {"name": "Druid", "category": "database", "description": "数据库连接池", "languages": ["java"]},
            "com.zaxxer.hikari": {"name": "HikariCP", "category": "database", "description": "数据库连接池", "languages": ["java"]},
            "org.apache.tomcat": {"name": "Tomcat", "category": "framework", "description": "Servlet 容器"},

            "com.baomidou": {"name": "MyBatis-Plus", "category": "orm", "description": "MyBatis 增强工具"},
            "cn.hutool": {"name": "Hutool", "category": "orm", "description": "Java 工具库"},
            "org.projectlombok": {"name": "Lombok", "category": "orm", "description": "代码简化库"},

            "react": {"name": "React", "category": "frontend", "description": "前端框架"},
            "vue": {"name": "Vue", "category": "frontend", "description": "前端框架"},
            "angular": {"name": "Angular", "category": "frontend", "description": "前端框架"},
            "svelte": {"name": "Svelte", "category": "frontend", "description": "前端框架"},
            "next": {"name": "Next.js", "category": "frontend", "description": "React 框架"},
            "nuxt": {"name": "Nuxt.js", "category": "frontend", "description": "Vue 框架"},
            "gatsby": {"name": "Gatsby", "category": "frontend", "description": "React 静态站点框架"},
            "remix": {"name": "Remix", "category": "frontend", "description": "React 框架"},
            "astro": {"name": "Astro", "category": "frontend", "description": "静态站点框架"},

            "antd": {"name": "Ant Design", "category": "ui_library", "description": "UI 组件库"},
            "ant-design": {"name": "Ant Design", "category": "ui_library", "description": "UI 组件库"},
            "element-plus": {"name": "Element Plus", "category": "ui_library", "description": "UI 组件库"},
            "element-ui": {"name": "Element UI", "category": "ui_library", "description": "UI 组件库"},
            "vuetify": {"name": "Vuetify", "category": "ui_library", "description": "UI 组件库"},
            "chakra-ui": {"name": "Chakra UI", "category": "ui_library", "description": "UI 组件库"},
            "mui": {"name": "Material UI", "category": "ui_library", "description": "UI 组件库"},
            "@mui": {"name": "Material UI", "category": "ui_library", "description": "UI 组件库"},
            "bootstrap": {"name": "Bootstrap", "category": "ui_library", "description": "UI 框架"},
            "tailwindcss": {"name": "Tailwind CSS", "category": "ui_library", "description": "CSS 框架"},
            "styled-components": {"name": "Styled Components", "category": "ui_library", "description": "CSS-in-JS"},
            "emotion": {"name": "Emotion", "category": "ui_library", "description": "CSS-in-JS"},

            "redux": {"name": "Redux", "category": "state_management", "description": "状态管理"},
            "@reduxjs": {"name": "Redux Toolkit", "category": "state_management", "description": "状态管理"},
            "vuex": {"name": "Vuex", "category": "state_management", "description": "状态管理"},
            "pinia": {"name": "Pinia", "category": "state_management", "description": "状态管理"},
            "mobx": {"name": "MobX", "category": "state_management", "description": "状态管理"},
            "zustand": {"name": "Zustand", "category": "state_management", "description": "状态管理"},
            "recoil": {"name": "Recoil", "category": "state_management", "description": "状态管理"},
            "jotai": {"name": "Jotai", "category": "state_management", "description": "状态管理"},

            "express": {"name": "Express", "category": "framework", "description": "Node.js Web 框架"},
            "koa": {"name": "Koa", "category": "framework", "description": "Node.js Web 框架"},
            "nestjs": {"name": "NestJS", "category": "framework", "description": "Node.js 企业级框架"},
            "@nestjs": {"name": "NestJS", "category": "framework", "description": "Node.js 企业级框架"},
            "fastify": {"name": "Fastify", "category": "framework", "description": "Node.js Web 框架"},
            "hapi": {"name": "Hapi", "category": "framework", "description": "Node.js Web 框架"},
            "egg": {"name": "Egg.js", "category": "framework", "description": "Node.js 企业级框架"},
            "midway": {"name": "Midway", "category": "framework", "description": "Node.js 企业级框架"},

            "typescript": {"name": "TypeScript", "category": "orm", "description": "JavaScript 超集"},
            "axios": {"name": "Axios", "category": "http_client", "description": "HTTP 客户端"},
            "fetch": {"name": "Fetch API", "category": "http_client", "description": "HTTP 客户端"},

            "prisma": {"name": "Prisma", "category": "orm", "description": "ORM 工具"},
            "@prisma": {"name": "Prisma", "category": "orm", "description": "ORM 工具"},
            "typeorm": {"name": "TypeORM", "category": "orm", "description": "ORM 框架"},
            "sequelize": {"name": "Sequelize", "category": "orm", "description": "ORM 框架"},
            "mongoose": {"name": "Mongoose", "category": "orm", "description": "MongoDB ODM"},
            "knex": {"name": "Knex.js", "category": "orm", "description": "SQL 查询构建器"},

            "jest": {"name": "Jest", "category": "testing", "description": "测试框架"},
            "vitest": {"name": "Vitest", "category": "testing", "description": "测试框架"},
            "mocha": {"name": "Mocha", "category": "testing", "description": "测试框架"},
            "cypress": {"name": "Cypress", "category": "testing", "description": "E2E 测试框架"},
            "playwright": {"name": "Playwright", "category": "testing", "description": "E2E 测试框架"},
            "@playwright": {"name": "Playwright", "category": "testing", "description": "E2E 测试框架"},
            "puppeteer": {"name": "Puppeteer", "category": "testing", "description": "浏览器自动化"},

            "webpack": {"name": "Webpack", "category": "build_tool", "description": "打包工具"},
            "vite": {"name": "Vite", "category": "build_tool", "description": "构建工具"},
            "rollup": {"name": "Rollup", "category": "build_tool", "description": "打包工具"},
            "esbuild": {"name": "esbuild", "category": "build_tool", "description": "打包工具"},
            "parcel": {"name": "Parcel", "category": "build_tool", "description": "打包工具"},
            "turbo": {"name": "Turborepo", "category": "build_tool", "description": "构建系统"},
            "nx": {"name": "Nx", "category": "build_tool", "description": "构建系统"},

            "zod": {"name": "Zod", "category": "validation", "description": "数据验证"},
            "yup": {"name": "Yup", "category": "validation", "description": "数据验证"},
            "joi": {"name": "Joi", "category": "validation", "description": "数据验证"},
            "class-validator": {"name": "class-validator", "category": "validation", "description": "数据验证"},

            "winston": {"name": "Winston", "category": "logging", "description": "日志库"},
            "pino": {"name": "Pino", "category": "logging", "description": "日志库"},
            "bunyan": {"name": "Bunyan", "category": "logging", "description": "日志库"},

            "socket.io": {"name": "Socket.IO", "category": "websocket", "description": "WebSocket 库"},
            "ws": {"name": "ws", "category": "websocket", "description": "WebSocket 库"},

            "graphql": {"name": "GraphQL", "category": "framework", "description": "API 查询语言"},
            "apollo-server": {"name": "Apollo Server", "category": "framework", "description": "GraphQL 服务器"},
            "@apollo": {"name": "Apollo", "category": "framework", "description": "GraphQL 平台"},
            "urql": {"name": "URQL", "category": "framework", "description": "GraphQL 客户端"},

            "ioredis": {"name": "IORedis", "category": "cache", "description": "Redis 客户端"},
            "bull": {"name": "Bull", "category": "task_queue", "description": "任务队列"},
            "bullmq": {"name": "BullMQ", "category": "task_queue", "description": "任务队列"},
            "agenda": {"name": "Agenda", "category": "task_queue", "description": "任务调度"},

            "zookeeper": {"name": "ZooKeeper", "category": "config", "description": "配置中心"},
            "consul": {"name": "Consul", "category": "config", "description": "服务发现"},
            "etcd": {"name": "etcd", "category": "config", "description": "配置中心"},
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
