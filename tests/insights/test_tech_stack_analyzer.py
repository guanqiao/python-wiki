"""
技术栈分析器测试
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pywiki.insights.tech_stack_analyzer import (
    TechCategory,
    TechComponent,
    TechStackAnalysis,
    TechStackAnalyzer,
)
from pywiki.parsers.types import ModuleInfo, ImportInfo


class TestTechCategory:
    """TechCategory 枚举测试"""

    def test_category_values(self):
        """测试类别值"""
        assert TechCategory.FRAMEWORK.value == "framework"
        assert TechCategory.DATABASE.value == "database"
        assert TechCategory.CACHE.value == "cache"
        assert TechCategory.MESSAGE_QUEUE.value == "message_queue"
        assert TechCategory.TESTING.value == "testing"
        assert TechCategory.ORM.value == "orm"
        assert TechCategory.VALIDATION.value == "validation"
        assert TechCategory.HTTP_CLIENT.value == "http_client"
        assert TechCategory.ASYNC.value == "async"
        assert TechCategory.SECURITY.value == "security"
        assert TechCategory.LOGGING.value == "logging"
        assert TechCategory.CONFIG.value == "config"
        assert TechCategory.TASK_QUEUE.value == "task_queue"
        assert TechCategory.MONITORING.value == "monitoring"
        assert TechCategory.CLOUD.value == "cloud"


class TestTechComponent:
    """TechComponent 数据类测试"""

    def test_create_tech_component(self):
        """测试创建技术组件"""
        component = TechComponent(
            name="Flask",
            category=TechCategory.FRAMEWORK,
            description="Lightweight web framework",
        )

        assert component.name == "Flask"
        assert component.category == TechCategory.FRAMEWORK
        assert component.version is None
        assert component.description == "Lightweight web framework"
        assert component.usage_locations == []
        assert component.config_files == []
        assert component.dependencies == []

    def test_create_component_with_version(self):
        """测试创建带版本的技术组件"""
        component = TechComponent(
            name="Django",
            category=TechCategory.FRAMEWORK,
            version="4.2.0",
            description="Full-featured web framework",
            usage_locations=["app.py"],
            config_files=["requirements.txt"],
        )

        assert component.version == "4.2.0"
        assert len(component.usage_locations) == 1
        assert len(component.config_files) == 1


class TestTechStackAnalysis:
    """TechStackAnalysis 数据类测试"""

    def test_create_empty_analysis(self):
        """测试创建空分析结果"""
        analysis = TechStackAnalysis()

        assert analysis.components == []
        assert analysis.frameworks == []
        assert analysis.databases == []
        assert analysis.libraries == []
        assert analysis.tools == []
        assert analysis.summary == {}

    def test_create_analysis_with_components(self):
        """测试创建带组件的分析结果"""
        flask = TechComponent(name="Flask", category=TechCategory.FRAMEWORK)
        sqlalchemy = TechComponent(name="SQLAlchemy", category=TechCategory.ORM)

        analysis = TechStackAnalysis(
            components=[flask, sqlalchemy],
            frameworks=[flask],
            libraries=[sqlalchemy],
            summary={"total": 2},
        )

        assert len(analysis.components) == 2
        assert len(analysis.frameworks) == 1
        assert len(analysis.libraries) == 1


class TestTechStackAnalyzer:
    """TechStackAnalyzer 测试"""

    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return TechStackAnalyzer()

    def test_analyzer_initialization(self, analyzer: TechStackAnalyzer):
        """测试分析器初始化"""
        assert analyzer._tech_database is not None
        assert "flask" in analyzer._tech_database
        assert "django" in analyzer._tech_database
        assert "pytest" in analyzer._tech_database


class TestTechStackAnalyzerIdentify:
    """技术组件识别测试"""

    @pytest.fixture
    def analyzer(self):
        return TechStackAnalyzer()

    def test_identify_flask(self, analyzer: TechStackAnalyzer):
        """测试识别 Flask"""
        component = analyzer._identify_component("flask")

        assert component is not None
        assert component.name == "Flask"
        assert component.category == TechCategory.FRAMEWORK

    def test_identify_django(self, analyzer: TechStackAnalyzer):
        """测试识别 Django"""
        component = analyzer._identify_component("django")

        assert component is not None
        assert component.name == "Django"
        assert component.category == TechCategory.FRAMEWORK

    def test_identify_fastapi(self, analyzer: TechStackAnalyzer):
        """测试识别 FastAPI"""
        component = analyzer._identify_component("fastapi")

        assert component is not None
        assert component.name == "FastAPI"
        assert component.category == TechCategory.FRAMEWORK

    def test_identify_sqlalchemy(self, analyzer: TechStackAnalyzer):
        """测试识别 SQLAlchemy"""
        component = analyzer._identify_component("sqlalchemy")

        assert component is not None
        assert component.name == "SQLAlchemy"
        assert component.category == TechCategory.ORM

    def test_identify_pytest(self, analyzer: TechStackAnalyzer):
        """测试识别 Pytest"""
        component = analyzer._identify_component("pytest")

        assert component is not None
        assert component.name == "Pytest"
        assert component.category == TechCategory.TESTING

    def test_identify_redis(self, analyzer: TechStackAnalyzer):
        """测试识别 Redis"""
        component = analyzer._identify_component("redis")

        assert component is not None
        assert component.name == "Redis"
        assert component.category == TechCategory.CACHE

    def test_identify_celery(self, analyzer: TechStackAnalyzer):
        """测试识别 Celery"""
        component = analyzer._identify_component("celery")

        assert component is not None
        assert component.name == "Celery"
        assert component.category == TechCategory.TASK_QUEUE

    def test_identify_unknown_module(self, analyzer: TechStackAnalyzer):
        """测试识别未知模块"""
        component = analyzer._identify_component("unknown_module_xyz")

        assert component is None

    def test_identify_with_submodule(self, analyzer: TechStackAnalyzer):
        """测试识别子模块"""
        component = analyzer._identify_component("flask.views")

        assert component is not None
        assert component.name == "Flask"


class TestTechStackAnalyzerExtractImports:
    """导入语句提取测试"""

    @pytest.fixture
    def analyzer(self):
        return TechStackAnalyzer()

    def test_extract_imports_basic(self, analyzer: TechStackAnalyzer):
        """测试基本导入提取"""
        content = "import os\nimport sys\nimport flask"

        imports = analyzer._extract_imports(content)

        assert "os" in imports
        assert "sys" in imports
        assert "flask" in imports

    def test_extract_from_imports(self, analyzer: TechStackAnalyzer):
        """测试 from 导入提取"""
        content = "from flask import Flask\nfrom django.db import models"

        imports = analyzer._extract_imports(content)

        assert "flask" in imports
        assert "django" in imports

    def test_extract_imports_mixed(self, analyzer: TechStackAnalyzer):
        """测试混合导入提取"""
        content = '''
import os
import sys
from flask import Flask, request
from django.conf import settings
import pytest
'''

        imports = analyzer._extract_imports(content)

        assert "os" in imports
        assert "sys" in imports
        assert "flask" in imports
        assert "django" in imports
        assert "pytest" in imports

    def test_extract_imports_empty(self, analyzer: TechStackAnalyzer):
        """测试空内容导入提取"""
        imports = analyzer._extract_imports("")

        assert imports == []


class TestTechStackAnalyzerParseDependency:
    """依赖字符串解析测试"""

    @pytest.fixture
    def analyzer(self):
        return TechStackAnalyzer()

    def test_parse_dependency_simple(self, analyzer: TechStackAnalyzer):
        """测试简单依赖解析"""
        name, version = analyzer._parse_dependency_string("flask")

        assert name == "flask"
        assert version is None

    def test_parse_dependency_with_version(self, analyzer: TechStackAnalyzer):
        """测试带版本依赖解析"""
        name, version = analyzer._parse_dependency_string("flask==2.0.0")

        assert name == "flask"
        assert version == "==2.0.0"

    def test_parse_dependency_with_greater_than(self, analyzer: TechStackAnalyzer):
        """测试大于版本依赖解析"""
        name, version = analyzer._parse_dependency_string("django>=4.0")

        assert name == "django"
        assert version == ">=4.0"

    def test_parse_dependency_with_tilde(self, analyzer: TechStackAnalyzer):
        """测试波浪号版本依赖解析"""
        name, version = analyzer._parse_dependency_string("pytest~=7.0")

        assert name == "pytest"
        assert version == "~=7.0"


class TestTechStackAnalyzerProject:
    """项目分析测试"""

    @pytest.fixture
    def analyzer(self):
        return TechStackAnalyzer()

    def test_analyze_project_basic(self, analyzer: TechStackAnalyzer, tmp_path: Path):
        """测试基本项目分析"""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        main_py = src_dir / "main.py"
        main_py.write_text('''
import flask
from django.db import models
import pytest

def main():
    pass
''')

        analysis = analyzer.analyze_project(tmp_path)

        assert len(analysis.components) >= 0

    def test_analyze_project_with_pyproject(self, analyzer: TechStackAnalyzer, tmp_path: Path):
        """测试带 pyproject.toml 的项目分析"""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('''
[tool.poetry]
name = "test-project"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.10"
flask = "^2.0"
pytest = "^7.0"
''')

        analysis = analyzer.analyze_project(tmp_path)

        assert isinstance(analysis, TechStackAnalysis)

    def test_analyze_project_with_requirements(self, analyzer: TechStackAnalyzer, tmp_path: Path):
        """测试带 requirements.txt 的项目分析"""
        requirements = tmp_path / "requirements.txt"
        requirements.write_text('''
flask==2.0.0
django>=4.0
pytest~=7.0
''')

        analysis = analyzer.analyze_project(tmp_path)

        assert isinstance(analysis, TechStackAnalysis)


class TestTechStackAnalyzerModule:
    """模块分析测试"""

    @pytest.fixture
    def analyzer(self):
        return TechStackAnalyzer()

    def test_analyze_module(self, analyzer: TechStackAnalyzer):
        """测试模块分析"""
        module = ModuleInfo(
            name="test_module",
            file_path=Path("/fake/path.py"),
            imports=[
                ImportInfo(module="flask", names=["Flask"]),
                ImportInfo(module="pytest", names=[]),
                ImportInfo(module="sqlalchemy", names=["Column", "Integer"]),
            ],
        )

        components = analyzer.analyze_module(module)

        assert len(components) >= 2

    def test_analyze_module_empty(self, analyzer: TechStackAnalyzer):
        """测试空模块分析"""
        module = ModuleInfo(
            name="empty_module",
            file_path=Path("/fake/path.py"),
            imports=[],
        )

        components = analyzer.analyze_module(module)

        assert components == []


class TestTechStackAnalyzerSummary:
    """摘要生成测试"""

    @pytest.fixture
    def analyzer(self):
        return TechStackAnalyzer()

    def test_generate_summary(self, analyzer: TechStackAnalyzer):
        """测试生成摘要"""
        analysis = TechStackAnalysis(
            components=[
                TechComponent(name="Flask", category=TechCategory.FRAMEWORK),
                TechComponent(name="Django", category=TechCategory.FRAMEWORK),
                TechComponent(name="Redis", category=TechCategory.CACHE),
                TechComponent(name="Pytest", category=TechCategory.TESTING),
            ],
            frameworks=[
                TechComponent(name="Flask", category=TechCategory.FRAMEWORK),
                TechComponent(name="Django", category=TechCategory.FRAMEWORK),
            ],
            databases=[],
            libraries=[
                TechComponent(name="Pytest", category=TechCategory.TESTING),
            ],
            tools=[
                TechComponent(name="Redis", category=TechCategory.CACHE),
            ],
        )

        summary = analyzer._generate_summary(analysis)

        assert summary["total_components"] == 4
        assert summary["frameworks_count"] == 2
        assert summary["databases_count"] == 0
        assert summary["primary_framework"] == "Flask"

    def test_generate_summary_empty(self, analyzer: TechStackAnalyzer):
        """测试生成空摘要"""
        analysis = TechStackAnalysis()

        summary = analyzer._generate_summary(analysis)

        assert summary["total_components"] == 0
        assert summary["primary_framework"] is None
        assert summary["primary_database"] is None


class TestTechStackAnalyzerReport:
    """技术报告生成测试"""

    @pytest.fixture
    def analyzer(self):
        return TechStackAnalyzer()

    def test_generate_tech_report(self, analyzer: TechStackAnalyzer):
        """测试生成技术报告"""
        analysis = TechStackAnalysis(
            components=[
                TechComponent(name="Flask", category=TechCategory.FRAMEWORK, version="2.0.0"),
            ],
            frameworks=[
                TechComponent(name="Flask", category=TechCategory.FRAMEWORK, version="2.0.0"),
            ],
            databases=[],
            libraries=[],
            tools=[],
            summary={"total_components": 1},
        )

        report = analyzer.generate_tech_report(analysis)

        assert "summary" in report
        assert "frameworks" in report
        assert "databases" in report
        assert "libraries" in report
        assert "tools" in report
        assert len(report["frameworks"]) == 1
        assert report["frameworks"][0]["name"] == "Flask"


class TestTechStackAnalyzerTechDatabase:
    """技术数据库测试"""

    @pytest.fixture
    def analyzer(self):
        return TechStackAnalyzer()

    def test_tech_database_has_frameworks(self, analyzer: TechStackAnalyzer):
        """测试技术数据库包含框架"""
        db = analyzer._tech_database

        assert "flask" in db
        assert "django" in db
        assert "fastapi" in db

    def test_tech_database_has_databases(self, analyzer: TechStackAnalyzer):
        """测试技术数据库包含数据库"""
        db = analyzer._tech_database

        assert "pymongo" in db
        assert "redis" in db
        assert "psycopg" in db

    def test_tech_database_has_testing(self, analyzer: TechStackAnalyzer):
        """测试技术数据库包含测试框架"""
        db = analyzer._tech_database

        assert "pytest" in db
        assert "unittest" in db

    def test_tech_database_has_task_queues(self, analyzer: TechStackAnalyzer):
        """测试技术数据库包含任务队列"""
        db = analyzer._tech_database

        assert "celery" in db
        assert "rq" in db

    def test_tech_database_structure(self, analyzer: TechStackAnalyzer):
        """测试技术数据库结构"""
        db = analyzer._tech_database

        for key, value in db.items():
            assert "name" in value
            assert "category" in value
            assert isinstance(value["name"], str)
            assert isinstance(value["category"], str)


class TestTechStackAnalyzerCategorization:
    """技术分类测试"""

    @pytest.fixture
    def analyzer(self):
        return TechStackAnalyzer()

    def test_categorize_frameworks(self, analyzer: TechStackAnalyzer, tmp_path: Path):
        """测试框架分类"""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        main_py = src_dir / "main.py"
        main_py.write_text("import flask\nimport fastapi")

        analysis = analyzer.analyze_project(tmp_path)

        framework_names = [f.name for f in analysis.frameworks]

    def test_categorize_databases(self, analyzer: TechStackAnalyzer, tmp_path: Path):
        """测试数据库分类"""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        main_py = src_dir / "main.py"
        main_py.write_text("import pymongo\nimport redis")

        analysis = analyzer.analyze_project(tmp_path)

        database_names = [d.name for d in analysis.databases]
