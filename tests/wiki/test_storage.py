"""
Wiki 存储服务测试
"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pywiki.wiki.storage import WikiStorage
from pywiki.config.models import Language


class TestWikiStorage:
    """WikiStorage 测试"""

    @pytest.fixture
    def output_dir(self, tmp_path):
        """创建输出目录"""
        return tmp_path / "wiki"

    @pytest.fixture
    def storage(self, output_dir):
        """创建存储实例"""
        return WikiStorage(output_dir, Language.ZH)

    def test_storage_initialization(self, output_dir):
        """测试存储初始化"""
        storage = WikiStorage(output_dir, Language.ZH)

        assert storage.output_dir.exists()
        assert storage.language_dir.exists()
        assert storage.history_dir.exists()
        assert storage.index_file.exists() is False

    def test_storage_with_english_language(self, tmp_path):
        """测试英语语言存储"""
        output_dir = tmp_path / "wiki"
        storage = WikiStorage(output_dir, Language.EN)

        assert storage.language == Language.EN
        assert storage.language_dir.name == "en"

    def test_get_module_path(self, storage):
        """测试获取模块路径"""
        path = storage.get_module_path("mymodule")

        assert "modules" in str(path)
        assert path.suffix == ".md"

    def test_get_module_path_nested(self, storage):
        """测试获取嵌套模块路径"""
        path = storage.get_module_path("package.submodule")

        assert "package" in str(path)
        assert "submodule.md" in str(path)

    @pytest.mark.asyncio
    async def test_save_document_new(self, storage):
        """测试保存新文档"""
        doc_path = storage.output_dir / "test.md"
        content = "# Test Document\n\nThis is a test."

        await storage.save_document(doc_path, content)

        assert doc_path.exists()
        assert doc_path.read_text(encoding="utf-8") == content

    @pytest.mark.asyncio
    async def test_save_document_update(self, storage):
        """测试更新文档"""
        doc_path = storage.output_dir / "test.md"
        old_content = "# Old Content"
        new_content = "# New Content"

        await storage.save_document(doc_path, old_content)
        await storage.save_document(doc_path, new_content)

        assert doc_path.read_text(encoding="utf-8") == new_content
        assert len(list(storage.history_dir.glob("*.md"))) > 0

    @pytest.mark.asyncio
    async def test_save_document_same_content(self, storage):
        """测试保存相同内容"""
        doc_path = storage.output_dir / "test.md"
        content = "# Same Content"

        await storage.save_document(doc_path, content)
        await storage.save_document(doc_path, content)

        history_files = list(storage.history_dir.glob("*.md"))
        assert len(history_files) == 0

    @pytest.mark.asyncio
    async def test_save_document_creates_directories(self, storage):
        """测试保存文档创建目录"""
        doc_path = storage.output_dir / "deeply" / "nested" / "path" / "test.md"
        content = "# Test"

        await storage.save_document(doc_path, content)

        assert doc_path.exists()
        assert doc_path.parent.exists()

    def test_get_document_exists(self, storage):
        """测试获取存在的文档"""
        doc_path = storage.output_dir / "test.md"
        content = "# Test Content"
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text(content, encoding="utf-8")

        result = storage.get_document(doc_path)

        assert result == content

    def test_get_document_not_exists(self, storage):
        """测试获取不存在的文档"""
        doc_path = storage.output_dir / "nonexistent.md"

        result = storage.get_document(doc_path)

        assert result is None

    def test_delete_document_exists(self, storage):
        """测试删除存在的文档"""
        doc_path = storage.output_dir / "test.md"
        content = "# Test"
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text(content, encoding="utf-8")

        result = storage.delete_document(doc_path)

        assert result is True
        assert not doc_path.exists()

    def test_delete_document_not_exists(self, storage):
        """测试删除不存在的文档"""
        doc_path = storage.output_dir / "nonexistent.md"

        result = storage.delete_document(doc_path)

        assert result is False

    def test_list_documents_empty(self, storage):
        """测试列出空目录文档"""
        documents = storage.list_documents()

        assert len(documents) == 0

    def test_list_documents_with_files(self, storage):
        """测试列出有文件的目录"""
        (storage.language_dir / "doc1.md").parent.mkdir(parents=True, exist_ok=True)
        (storage.language_dir / "doc1.md").write_text("# Doc 1", encoding="utf-8")
        (storage.language_dir / "subdir" / "doc2.md").parent.mkdir(parents=True, exist_ok=True)
        (storage.language_dir / "subdir" / "doc2.md").write_text("# Doc 2", encoding="utf-8")

        documents = storage.list_documents()

        assert len(documents) == 2

    def test_search_no_matches(self, storage):
        """测试搜索无匹配"""
        (storage.language_dir / "test.md").parent.mkdir(parents=True, exist_ok=True)
        (storage.language_dir / "test.md").write_text("# Test\n\nHello world.", encoding="utf-8")

        results = storage.search("nonexistent")

        assert len(results) == 0

    def test_search_with_matches(self, storage):
        """测试搜索有匹配"""
        (storage.language_dir / "test.md").parent.mkdir(parents=True, exist_ok=True)
        (storage.language_dir / "test.md").write_text("# Test\n\nHello world. Python is great.", encoding="utf-8")

        results = storage.search("Python")

        assert len(results) == 1
        assert "test.md" in results[0]["path"]
        assert len(results[0]["matches"]) > 0

    def test_search_case_insensitive(self, storage):
        """测试搜索大小写不敏感"""
        (storage.language_dir / "test.md").parent.mkdir(parents=True, exist_ok=True)
        (storage.language_dir / "test.md").write_text("# Test\n\nPYTHON programming.", encoding="utf-8")

        results = storage.search("python")

        assert len(results) == 1

    def test_search_multiple_matches(self, storage):
        """测试搜索多个匹配"""
        (storage.language_dir / "test.md").parent.mkdir(parents=True, exist_ok=True)
        (storage.language_dir / "test.md").write_text(
            "# Test\n\nLine 1 has python.\nLine 2 has python.\nLine 3 has python.",
            encoding="utf-8"
        )

        results = storage.search("python")

        assert len(results[0]["matches"]) == 3

    def test_get_document_hash_no_index(self, storage):
        """测试获取文档哈希 - 无索引"""
        doc_path = storage.output_dir / "test.md"

        result = storage.get_document_hash(doc_path)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_document_hash_with_index(self, storage):
        """测试获取文档哈希 - 有索引"""
        doc_path = storage.output_dir / "test.md"
        content = "# Test"

        await storage.save_document(doc_path, content)

        result = storage.get_document_hash(doc_path)

        assert result is not None
        assert len(result) == 32

    def test_is_document_changed_no_stored(self, storage):
        """测试文档是否更改 - 无存储"""
        doc_path = storage.output_dir / "test.md"
        content = "# Test"

        result = storage.is_document_changed(doc_path, content)

        assert result is True

    @pytest.mark.asyncio
    async def test_is_document_changed_same_content(self, storage):
        """测试文档是否更改 - 相同内容"""
        doc_path = storage.output_dir / "test.md"
        content = "# Test"

        await storage.save_document(doc_path, content)
        result = storage.is_document_changed(doc_path, content)

        assert result is False

    @pytest.mark.asyncio
    async def test_is_document_changed_different_content(self, storage):
        """测试文档是否更改 - 不同内容"""
        doc_path = storage.output_dir / "test.md"
        old_content = "# Old"
        new_content = "# New"

        await storage.save_document(doc_path, old_content)
        result = storage.is_document_changed(doc_path, new_content)

        assert result is True

    @pytest.mark.asyncio
    async def test_index_persistence(self, output_dir):
        """测试索引持久化"""
        storage1 = WikiStorage(output_dir, Language.ZH)
        doc_path = output_dir / "test.md"
        content = "# Test"

        await storage1.save_document(doc_path, content)

        storage2 = WikiStorage(output_dir, Language.ZH)
        result = storage2.get_document_hash(doc_path)

        assert result is not None

    @pytest.mark.asyncio
    async def test_history_saved_on_update(self, storage):
        """测试更新时保存历史"""
        doc_path = storage.output_dir / "test.md"

        await storage.save_document(doc_path, "# Version 1")
        await storage.save_document(doc_path, "# Version 2")

        history_files = list(storage.history_dir.glob("*.md"))
        assert len(history_files) == 1
        assert "Version 1" in history_files[0].read_text(encoding="utf-8")

    @pytest.mark.asyncio
    async def test_multiple_updates_multiple_history(self, storage):
        """测试多次更新多次历史"""
        import asyncio
        doc_path = storage.output_dir / "test.md"

        await storage.save_document(doc_path, "# Version 1")
        await asyncio.sleep(0.01)
        await storage.save_document(doc_path, "# Version 2")
        await asyncio.sleep(0.01)
        await storage.save_document(doc_path, "# Version 3")

        history_files = list(storage.history_dir.glob("*.md"))
        assert len(history_files) >= 1

    def test_search_context_lines(self, storage):
        """测试搜索上下文行"""
        content = "Line 1\nLine 2\nLine 3 has python\nLine 4\nLine 5"
        (storage.language_dir / "test.md").parent.mkdir(parents=True, exist_ok=True)
        (storage.language_dir / "test.md").write_text(content, encoding="utf-8")

        results = storage.search("python")

        assert "Line 1" in results[0]["matches"][0]["context"]
        assert "Line 5" in results[0]["matches"][0]["context"]

    @pytest.mark.asyncio
    async def test_delete_document_updates_index(self, storage):
        """测试删除文档更新索引"""
        doc_path = storage.output_dir / "test.md"
        content = "# Test"

        await storage.save_document(doc_path, content)
        assert storage.get_document_hash(doc_path) is not None

        storage.delete_document(doc_path)
        assert storage.get_document_hash(doc_path) is None
