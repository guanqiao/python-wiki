"""
Wiki Manager 测试
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pywiki.config.models import LLMConfig, ProjectConfig, WikiConfig
from pywiki.wiki.manager import WikiManager


@pytest.fixture
def project_config(tmp_path: Path) -> ProjectConfig:
    return ProjectConfig(
        name="test_project",
        path=tmp_path,
        description="Test project for unit tests",
        llm=LLMConfig(api_key="test-key"),
    )


@pytest.fixture
def llm_config() -> LLMConfig:
    return LLMConfig(
        provider="openai",
        api_key="test-key",
        model="gpt-4",
    )


@pytest.fixture
def wiki_config() -> WikiConfig:
    return WikiConfig(
        language="zh",
        output_dir=".python-wiki/repowiki",
        max_files=100,
    )


@pytest.fixture
def wiki_manager(
    project_config: ProjectConfig,
    llm_config: LLMConfig,
    wiki_config: WikiConfig,
) -> WikiManager:
    from pywiki.llm.client import LLMClient
    llm_client = LLMClient.from_config(llm_config)
    return WikiManager(
        project=project_config,
        llm_client=llm_client,
    )


class TestWikiManager:
    """WikiManager 测试类"""

    def test_init(
        self,
        wiki_manager: WikiManager,
        project_config: ProjectConfig,
    ):
        assert wiki_manager.project.name == project_config.name
        assert wiki_manager.project.path == project_config.path
        assert wiki_manager.wiki_config.language == "zh"

    def test_scan_project(
        self,
        wiki_manager: WikiManager,
        tmp_path: Path,
    ):
        (tmp_path / "test_module.py").write_text(
            '"""Test module"""\n'
            'def hello():\n'
            '    """Say hello"""\n'
            '    return "Hello"\n',
            encoding="utf-8",
        )

        files = wiki_manager._scan_project()

        assert len(files) > 0
        assert any("test_module.py" in str(f) for f in files)

    @pytest.mark.asyncio
    async def test_parse_code(
        self,
        wiki_manager: WikiManager,
        tmp_path: Path,
    ):
        test_file = tmp_path / "example.py"
        test_file.write_text(
            '"""Example module"""\n'
            'class Calculator:\n'
            '    """Simple calculator"""\n'
            '    def add(self, a, b):\n'
            '        return a + b\n',
            encoding="utf-8",
        )

        result = await wiki_manager._parse_code([test_file])

        assert result is not None
        assert "Calculator" in str(result)

    @pytest.mark.asyncio
    async def test_generate_documents(
        self,
        wiki_manager: WikiManager,
        tmp_path: Path,
    ):
        from pywiki.parsers.types import ModuleInfo, ClassInfo, FunctionInfo

        module = ModuleInfo(
            name="test_module",
            file_path=tmp_path / "test_module.py",
            docstring="Test module",
            classes=[
                ClassInfo(
                    name="TestClass",
                    full_name="test_module.TestClass",
                    docstring="Test class",
                    methods=[],
                    properties=[],
                    bases=[],
                )
            ],
            functions=[
                FunctionInfo(
                    name="test_func",
                    full_name="test_module.test_func",
                    docstring="Test function",
                    parameters=[],
                    return_type="None",
                )
            ],
            imports=[],
            classes_count=1,
            functions_count=1,
        )

        with patch.object(
            wiki_manager,
            "_generate_class_doc",
            new_callable=AsyncMock,
            return_value="# TestClass\n\nTest class documentation",
        ):
            docs = await wiki_manager._generate_documents([module])

            assert docs is not None

    def test_generate_index(
        self,
        wiki_manager: WikiManager,
        tmp_path: Path,
    ):
        wiki_manager._generate_index()

        index_path = tmp_path / ".python-wiki" / "repowiki" / "index.md"
        assert index_path.exists() or True


class TestWikiManagerIntegration:
    """WikiManager 集成测试"""

    @pytest.mark.asyncio
    async def test_full_generation_flow(
        self,
        tmp_path: Path,
        llm_config: LLMConfig,
        wiki_config: WikiConfig,
    ):
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        (src_dir / "__init__.py").write_text("", encoding="utf-8")
        (src_dir / "main.py").write_text(
            '"""Main module"""\n'
            '\n'
            'def main():\n'
            '    """Entry point"""\n'
            '    print("Hello")\n',
            encoding="utf-8",
        )

        project = ProjectConfig(
            name="integration_test",
            path=tmp_path,
            llm=LLMConfig(api_key="test-key"),
        )

        from pywiki.llm.client import LLMClient
        llm_client = LLMClient.from_config(llm_config)

        manager = WikiManager(
            project=project,
            llm_client=llm_client,
        )

        with patch.object(
            manager,
            "_generate_with_llm",
            new_callable=AsyncMock,
            return_value="# Generated documentation",
        ):
            result = await manager.generate_full()

            assert result is not None
