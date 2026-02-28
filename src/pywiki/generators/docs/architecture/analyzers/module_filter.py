"""
模块过滤器
用于过滤第三方库和非项目模块
"""

import re
from typing import Any


class ModuleFilter:
    """模块过滤器"""

    THIRD_PARTY_PREFIXES = {
        "org.", "com.", "io.", "net.", "javax.", "java.",
        "liquibase.", "flowable.", "activiti.", "camunda.",
        "springframework.", "hibernate.", "mybatis.", "apache.",
        "lombok.", "slf4j.", "log4j.", "junit.", "mockito.",
        "jackson.", "gson.", "fastjson.", "okhttp.",
        "retrofit.", "feign.", "dubbo.", "nacos.", "sentinel.",
        "sharding.", "druid.", "hikari.", "redis.clients.", "mongodb.driver.",
        "elasticsearch.", "kafka.", "rabbitmq.", "zookeeper.",
        "curator.", "netty.", "vertx.", "quarkus.", "micronaut.",
        "jakarta.", "sun.", "jdk.", "oracle.", "ibm.",
    }

    STANDARD_LIBS = {
        "typing", "os", "sys", "json", "pathlib", "asyncio", "abc",
        "dataclasses", "collections", "functools", "itertools", "re",
        "logging", "time", "datetime", "copy", "enum", "io", "warnings",
        "contextlib", "threading", "multiprocessing", "concurrent",
        "subprocess", "shutil", "tempfile", "hashlib", "hmac", "secrets",
        "argparse", "configparser", "traceback", "inspect", "dis",
        "unittest", "pytest", "mock", "socket", "ssl", "http", "urllib",
        "email", "html", "xml", "csv", "sqlite3", "heapq", "bisect",
        "array", "weakref", "types", "numbers", "math", "random",
        "statistics", "decimal", "fractions", "operator", "pickle",
    }

    EXTERNAL_CATEGORIES = {
        "web_framework": ["fastapi", "flask", "django", "tornado", "starlette", "sanic", "aiohttp"],
        "database": ["sqlalchemy", "pymongo", "redis", "psycopg", "mysql", "sqlite", "databases"],
        "orm": ["sqlalchemy", "peewee", "tortoise", "django.db", "pony"],
        "validation": ["pydantic", "marshmallow", "cerberus", "voluptuous"],
        "testing": ["pytest", "unittest", "mock", "hypothesis", "faker"],
        "async": ["asyncio", "aiohttp", "aiofiles", "aioredis", "aiomysql"],
        "http_client": ["requests", "httpx", "aiohttp", "urllib3", "http.client"],
        "serialization": ["json", "pickle", "yaml", "msgpack", "orjson"],
        "cli": ["click", "argparse", "typer", "rich"],
        "config": ["pydantic", "dynaconf", "python-dotenv", "configparser"],
        "logging": ["logging", "loguru", "structlog"],
        "task_queue": ["celery", "rq", "dramatiq", "huey"],
        "cache": ["redis", "memcache", "cachetools", "aiocache"],
        "message_queue": ["kafka", "pika", "aio_pika", "celery"],
        "security": ["cryptography", "jwt", "passlib", "bcrypt"],
        "data_science": ["pandas", "numpy", "scipy", "sklearn"],
        "ml": ["torch", "tensorflow", "sklearn", "transformers"],
    }

    @classmethod
    def is_third_party_module(cls, module_name: str, project_name: str) -> bool:
        """判断是否为第三方库模块或需要过滤的非项目模块"""
        module_lower = module_name.lower()

        # 检查是否是第三方库前缀
        for prefix in cls.THIRD_PARTY_PREFIXES:
            if module_lower.startswith(prefix):
                return True

        # 处理文件路径格式（如 Python 脚本路径）
        if re.match(r'^[A-Za-z]:[\\/]', module_name) or module_name.startswith('/') or module_name.startswith('\\'):
            normalized = module_name.replace('\\', '/').lower()
            parts = normalized.split('/')
            meaningful_parts = [p for p in parts if p and p != '.' and p != '..' and not re.match(r'^[A-Za-z]:$', p)]

            if not meaningful_parts:
                return True

            first_meaningful = meaningful_parts[0].lower()

            # 过滤掉工具脚本目录
            tool_dirs = {'tools', 'scripts', 'utils', 'convertor', 'converter', 'migration'}
            if first_meaningful in tool_dirs:
                return True

            # 如果是 Python 文件路径（包含 .py 文件），可能是工具脚本
            if any(p.endswith('.py') for p in meaningful_parts):
                # 检查是否在项目源码目录中
                src_indicators = {'src', 'main', 'java', 'python', 'kotlin'}
                if not any(p.lower() in src_indicators for p in meaningful_parts):
                    return True

            # 检查是否是 Java 包路径
            if first_meaningful in {'org', 'com', 'io', 'net', 'javax', 'java', 'liquibase', 'flowable'}:
                return True

            return False

        return False

    @classmethod
    def filter_project_modules(cls, modules: list, project_name: str) -> list:
        """过滤出项目自身的模块"""
        return [m for m in modules if not cls.is_third_party_module(
            m.name if hasattr(m, 'name') else str(m),
            project_name
        )]

    @classmethod
    def get_external_category(cls, module_name: str) -> str:
        """获取外部依赖的分类"""
        base = module_name.split(".")[0].lower()

        if base in cls.STANDARD_LIBS:
            return "standard_library"

        for category, libs in cls.EXTERNAL_CATEGORIES.items():
            if base in libs:
                return category

        return "other"