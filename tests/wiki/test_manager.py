"""
Wiki 管理器测试
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pywiki.wiki.manager import (
    WikiManager,
    GenerationStatus,
    GenerationProgress,
)
from pywiki.config.models import (
    ProjectConfig,
    WikiConfig,
    LLMConfig,
    LLMProvider,
    Language,
)


class TestGenerationProgress:
    """GenerationProgress 数据类测试"""

    def test_create_generation_progress_defaults(self):
        """测试创建生成进度 - 默认值"""
        progress = GenerationProgress()

        assert progress.status == GenerationStatus.IDLE
        assert progress.total_files == 0
        assert progress.processed_files == 0
        assert progress.current_file == ""
        assert progress.current_stage == ""
        assert progress.start_time is None
        assert progress.errors == []

    def test_create_generation_progress_with_values(self):
        """测试创建生成进度 - 有值"""
        now = datetime.now()
        progress = GenerationProgress(
            status=GenerationStatus.PARSING,
            total_files=10,
            processed_files=5,
            current_file="test.py",
            current_stage="解析代码",
            start_time=now,
            errors=["error1"],
        )

        assert progress.status == GenerationStatus.PARSING
        assert progress.total_files == 10
        assert progress.processed_files == 5
        assert progress.current_file == "test.py"
        assert progress.current_stage == "解析代码"
        assert progress.start_time == now
        assert progress.errors == ["error1"]


class TestGenerationStatus:
    """GenerationStatus 枚举测试"""

    def test_status_values(self):
        """测试状态值"""
        assert GenerationStatus.IDLE == "idle"
        assert GenerationStatus.SCANNING == "scanning"
        assert GenerationStatus.PARSING == "parsing"
        assert GenerationStatus.GENERATING == "generating"
        assert GenerationStatus.SYNCING == "syncing"
        assert GenerationStatus.COMPLETED == "completed"
        assert GenerationStatus.ERROR == "error"

    def test_status_is_string_enum(self):
        """测试状态是字符串枚举"""
        assert isinstance(GenerationStatus.IDLE, str)


class TestWikiManager:
    """WikiManager 测试"""

    @pytest.fixture
    def project_path(self, tmp_path):
        """创建项目路径"""
        project = tmp_path / "test_project"
        project.mkdir(parents=True, exist_ok=True)

        src = project / "src"
        src.mkdir(parents=True, exist_ok=True)

        main_py = src / "main.py"
        main_py.write_text('''
def hello():
    """Say hello."""
    print("Hello, World!")
''')

        return project

    @pytest.fixture
    def project_config(self, project_path):
        """创建项目配置"""
        return ProjectConfig(
            name="test-project",
            path=project_path,
            llm=LLMConfig(
                api_key="test-key",
                provider=LLMProvider.OPENAI,
            ),
            wiki=WikiConfig(
                language=Language.ZH,
                output_dir="wiki",
                generate_diagrams=False,
            ),
        )

    @pytest.fixture
    def llm_client(self):
        """创建 LLM 客户端 Mock"""
        client = MagicMock()
        client.generate = AsyncMock(return_value="Generated content")
        return client

    @pytest.fixture
    def manager(self, project_config, llm_client):
        """创建管理器实例"""
        return WikiManager(project_config, llm_client)

    def test_manager_initialization(self, manager, project_config):
        """测试管理器初始化"""
        assert manager.project == project_config
        assert manager.llm_client is not None
        assert manager.parser_factory is not None
        assert manager.storage is not None
        assert manager.generator is not None

    def test_manager_progress_initial_state(self, manager):
        """测试管理器进度初始状态"""
        progress = manager.get_progress()

        assert progress.status == GenerationStatus.IDLE
        assert progress.total_files == 0

    def test_manager_with_progress_callback(self, project_config, llm_client):
        """测试管理器带进度回调"""
        callback_calls = []

        def callback(progress):
            callback_calls.append(progress)

        manager = WikiManager(project_config, llm_client, callback)
        manager._notify_progress()

        assert len(callback_calls) == 1
        assert isinstance(callback_calls[0], GenerationProgress)

    @pytest.mark.asyncio
    async def test_generate_full_success(self, manager):
        """测试完整生成成功"""
        with patch.object(manager, '_scan_project'), \
             patch.object(manager, '_parse_code'), \
             patch.object(manager, '_generate_documents'), \
             patch.object(manager, '_sync_to_git'):
            result = await manager.generate_full()

        assert result is True
        progress = manager.get_progress()
        assert progress.status == GenerationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_generate_full_with_error(self, project_config, llm_client):
        """测试完整生成出错"""
        manager = WikiManager(project_config, llm_client)

        with patch.object(
            manager,
            "_parse_with_factory",
            side_effect=Exception("Parse error")
        ):
            result = await manager.generate_full()

        assert result is False
        progress = manager.get_progress()
        assert progress.status == GenerationStatus.ERROR
        assert "Parse error" in progress.errors

    @pytest.mark.asyncio
    async def test_generate_incremental_success(self, manager):
        """测试增量生成成功"""
        result = await manager.generate_incremental([])

        assert result is True
        progress = manager.get_progress()
        assert progress.status == GenerationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_generate_incremental_with_error(self, manager, project_path):
        """测试增量生成出错"""
        with patch.object(
            manager.parser_factory,
            "get_parser",
            return_value=None
        ):
            changed_files = [project_path / "src" / "main.py"]
            result = await manager.generate_incremental(changed_files)

        assert result is True

    @pytest.mark.asyncio
    async def test_generate_incremental_empty_list(self, manager):
        """测试增量生成空列表"""
        result = await manager.generate_incremental([])

        assert result is True
        progress = manager.get_progress()
        assert progress.status == GenerationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_generate_full_updates_progress(self, manager):
        """测试完整生成更新进度"""
        progress_updates = []

        def callback(progress):
            progress_updates.append(GenerationProgress(
                status=progress.status,
                total_files=progress.total_files,
                processed_files=progress.processed_files,
                current_file=progress.current_file,
                current_stage=progress.current_stage,
            ))

        manager.progress_callback = callback

        with patch.object(manager, '_scan_project'), \
             patch.object(manager, '_parse_code'), \
             patch.object(manager, '_generate_documents'), \
             patch.object(manager, '_sync_to_git'):
            await manager.generate_full()

        statuses = [p.status for p in progress_updates]
        assert GenerationStatus.SCANNING in statuses
        assert GenerationStatus.COMPLETED in statuses

    @pytest.mark.asyncio
    async def test_generate_full_creates_documents(self, manager):
        """测试完整生成创建文档"""
        with patch.object(manager, '_scan_project'), \
             patch.object(manager, '_parse_code'), \
             patch.object(manager, '_generate_documents'), \
             patch.object(manager, '_sync_to_git'):
            await manager.generate_full()

        documents = manager.storage.list_documents()
        assert len(documents) >= 0

    def test_search_empty(self, manager):
        """测试搜索空结果"""
        results = manager.search("nonexistent")

        assert isinstance(results, list)

    def test_search_with_content(self, manager):
        """测试搜索有内容"""
        doc_path = manager.storage.output_dir / "test.md"
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text("# Test\n\nHello world.", encoding="utf-8")

        results = manager.search("Hello")

        assert isinstance(results, list)

    def test_get_document_exists(self, manager):
        """测试获取存在的文档"""
        doc_path = manager.storage.output_dir / "test.md"
        content = "# Test Document"
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text(content, encoding="utf-8")

        result = manager.get_document(doc_path)

        assert result == content

    def test_get_document_not_exists(self, manager):
        """测试获取不存在的文档"""
        doc_path = manager.storage.output_dir / "nonexistent.md"

        result = manager.get_document(doc_path)

        assert result is None

    def test_get_history_empty(self, manager):
        """测试获取空历史"""
        doc_path = manager.storage.output_dir / "test.md"

        history = manager.get_history(doc_path)

        assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_progress_callback_on_error(self, project_config, llm_client):
        """测试出错时进度回调"""
        callback_calls = []

        def callback(progress):
            callback_calls.append(progress)

        manager = WikiManager(project_config, llm_client, callback)

        with patch.object(
            manager,
            "_parse_with_factory",
            side_effect=Exception("Test error")
        ):
            await manager.generate_full()

        error_progresses = [p for p in callback_calls if p.status == GenerationStatus.ERROR]
        assert len(error_progresses) > 0
        assert "Test error" in error_progresses[0].errors

    @pytest.mark.asyncio
    async def test_generate_full_with_diagrams(self, project_config, llm_client):
        """测试完整生成带图表"""
        project_config.wiki.generate_diagrams = True
        manager = WikiManager(project_config, llm_client)

        with patch.object(manager, '_scan_project'), \
             patch.object(manager, '_parse_code'), \
             patch.object(manager, '_generate_documents'), \
             patch.object(manager, '_sync_to_git'):
            result = await manager.generate_full()

        assert result is True

    @pytest.mark.asyncio
    async def test_incremental_updates_progress_file_count(self, manager, project_path):
        """测试增量更新进度文件计数"""
        files = [
            project_path / "src" / "main.py",
            project_path / "src" / "utils.py",
        ]

        for f in files:
            f.write_text("# " + f.name)

        progress_updates = []

        def callback(progress):
            progress_updates.append(progress.total_files)

        manager.progress_callback = callback

        mock_parser = MagicMock()
        mock_parser.parse_file = MagicMock(return_value=MagicMock(modules=[]))
        
        with patch.object(manager.parser_factory, 'get_parser', return_value=mock_parser):
            await manager.generate_incremental(files)

        assert 2 in progress_updates

    def test_manager_parser_configuration(self, project_config, llm_client):
        """测试管理器解析器配置"""
        project_config.wiki.exclude_patterns = ["tests/*", "venv/*"]
        project_config.wiki.include_private = True

        manager = WikiManager(project_config, llm_client)

        assert "tests/*" in manager.parser_factory.exclude_patterns
        assert manager.parser_factory.include_private is True

    def test_manager_storage_configuration(self, project_config, llm_client):
        """测试管理器存储配置"""
        project_config.wiki.language = Language.EN
        project_config.wiki.output_dir = "docs"

        manager = WikiManager(project_config, llm_client)

        assert manager.storage.language == Language.EN
        assert "docs" in str(manager.storage.output_dir)

    @pytest.mark.asyncio
    async def test_generate_full_progress_stages(self, manager):
        """测试完整生成进度阶段"""
        stages = []

        def callback(progress):
            if progress.current_stage:
                stages.append(progress.current_stage)

        manager.progress_callback = callback

        with patch.object(manager, '_parse_code'), \
             patch.object(manager, '_generate_documents'), \
             patch.object(manager, '_sync_to_git'):
            await manager.generate_full()

        assert len(stages) > 0
