"""
文档生成器测试
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pywiki.generators.docs.base import (
    BaseDocGenerator,
    DocGeneratorContext,
    DocGeneratorResult,
    DocType,
)
from pywiki.generators.docs.overview_generator import OverviewGenerator
from pywiki.generators.docs.techstack_generator import TechStackGenerator
from pywiki.generators.docs.api_generator import APIGenerator
from pywiki.generators.docs.architecture_generator import ArchitectureDocGenerator
from pywiki.config.models import Language


class TestDocGeneratorContext:
    """测试 DocGeneratorContext"""

    def test_create_context(self, tmp_path):
        """测试创建上下文"""
        context = DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

        assert context.project_path == tmp_path
        assert context.project_name == "test_project"
        assert context.language == Language.ZH

    def test_get_output_path(self, tmp_path):
        """测试获取输出路径"""
        context = DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            output_dir=tmp_path / "docs",
        )

        path = context.get_output_path(DocType.OVERVIEW)
        assert path.name == "overview.md"

        path = context.get_output_path(DocType.TECH_STACK)
        assert path.name == "tech-stack.md"


class TestOverviewGenerator:
    """测试 OverviewGenerator"""

    @pytest.fixture
    def generator(self):
        return OverviewGenerator(language=Language.ZH)

    @pytest.fixture
    def context(self, tmp_path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    @pytest.mark.asyncio
    async def test_generate_basic(self, generator, context, tmp_path):
        """测试基本生成"""
        readme = tmp_path / "README.md"
        readme.write_text("# Test Project\n\nThis is a test project.")

        result = await generator.generate(context)

        assert result.success
        assert result.doc_type == DocType.OVERVIEW
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_generate_with_pyproject(self, generator, context, tmp_path):
        """测试使用 pyproject.toml 生成"""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.poetry]
name = "test-project"
version = "0.1.0"
description = "A test project"
""")

        result = await generator.generate(context)

        assert result.success


class TestTechStackGenerator:
    """测试 TechStackGenerator"""

    @pytest.fixture
    def generator(self):
        return TechStackGenerator(language=Language.ZH)

    @pytest.fixture
    def context(self, tmp_path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    @pytest.mark.asyncio
    async def test_generate_basic(self, generator, context, tmp_path):
        """测试基本生成"""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.poetry.dependencies]
python = "^3.10"
flask = "^2.0"
pytest = "^7.0"
""")

        result = await generator.generate(context)

        assert result.success
        assert result.doc_type == DocType.TECH_STACK


class TestAPIGenerator:
    """测试 APIGenerator"""

    @pytest.fixture
    def generator(self):
        return APIGenerator(language=Language.ZH)

    @pytest.fixture
    def context(self, tmp_path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    @pytest.mark.asyncio
    async def test_generate_basic(self, generator, context):
        """测试基本生成"""
        result = await generator.generate(context)

        assert result.success
        assert result.doc_type == DocType.API


class TestArchitectureDocGenerator:
    """测试 ArchitectureDocGenerator"""

    @pytest.fixture
    def generator(self):
        return ArchitectureDocGenerator(language=Language.ZH)

    @pytest.fixture
    def context(self, tmp_path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    @pytest.mark.asyncio
    async def test_generate_basic(self, generator, context):
        """测试基本生成"""
        result = await generator.generate(context)

        assert result.success
        assert result.doc_type == DocType.ARCHITECTURE


class TestDocGeneratorResult:
    """测试 DocGeneratorResult"""

    def test_create_result(self, tmp_path):
        """测试创建结果"""
        result = DocGeneratorResult(
            doc_type=DocType.OVERVIEW,
            content="# Test",
            file_path=tmp_path / "overview.md",
            success=True,
            message="Success",
        )

        assert result.doc_type == DocType.OVERVIEW
        assert result.content == "# Test"
        assert result.success

    def test_to_dict(self, tmp_path):
        """测试转换为字典"""
        result = DocGeneratorResult(
            doc_type=DocType.OVERVIEW,
            content="# Test",
            file_path=tmp_path / "overview.md",
            success=True,
        )

        d = result.to_dict()

        assert d["doc_type"] == "overview"
        assert d["success"]


class TestDocType:
    """测试 DocType"""

    def test_doc_types(self):
        """测试文档类型枚举"""
        assert DocType.OVERVIEW.value == "overview"
        assert DocType.TECH_STACK.value == "tech-stack"
        assert DocType.API.value == "api"
        assert DocType.ARCHITECTURE.value == "architecture"
        assert DocType.MODULE.value == "module"
        assert DocType.DEPENDENCIES.value == "dependencies"
        assert DocType.CONFIGURATION.value == "configuration"
        assert DocType.DEVELOPMENT.value == "development"
        assert DocType.DATABASE.value == "database"
        assert DocType.TSD.value == "tsd"
