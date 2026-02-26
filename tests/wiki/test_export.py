"""
Wiki 文档导出功能测试
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pywiki.wiki.export import WikiExporter, WikiSharingManager


class TestWikiExporter:
    """WikiExporter 测试"""

    @pytest.fixture
    def wiki_dir(self, tmp_path):
        """创建 wiki 目录"""
        wiki = tmp_path / "wiki"
        wiki.mkdir(parents=True, exist_ok=True)
        return wiki

    @pytest.fixture
    def exporter(self, wiki_dir):
        """创建导出器实例"""
        return WikiExporter(wiki_dir)

    def test_exporter_initialization(self, wiki_dir):
        """测试导出器初始化"""
        exporter = WikiExporter(wiki_dir)

        assert exporter.wiki_dir == wiki_dir
        assert exporter.output_dir.exists()
        assert exporter.output_dir.name == "exports"

    def test_exporter_with_custom_output_dir(self, wiki_dir, tmp_path):
        """测试自定义输出目录"""
        custom_output = tmp_path / "custom_exports"
        exporter = WikiExporter(wiki_dir, custom_output)

        assert exporter.output_dir == custom_output
        assert exporter.output_dir.exists()

    def test_get_wiki_files_empty(self, exporter):
        """测试获取空目录文件"""
        files = exporter._get_wiki_files()

        assert len(files) == 0

    def test_get_wiki_files_with_files(self, exporter, wiki_dir):
        """测试获取有文件的目录"""
        (wiki_dir / "doc1.md").write_text("# Doc 1", encoding="utf-8")
        (wiki_dir / "subdir" / "doc2.md").parent.mkdir(parents=True, exist_ok=True)
        (wiki_dir / "subdir" / "doc2.md").write_text("# Doc 2", encoding="utf-8")

        files = exporter._get_wiki_files()

        assert len(files) == 2

    def test_build_file_tree_empty(self, exporter):
        """测试构建空文件树"""
        tree = exporter._build_file_tree()

        assert tree == {}

    def test_build_file_tree_flat(self, exporter, wiki_dir):
        """测试构建扁平文件树"""
        (wiki_dir / "doc1.md").write_text("# Doc 1", encoding="utf-8")
        (wiki_dir / "doc2.md").write_text("# Doc 2", encoding="utf-8")

        tree = exporter._build_file_tree()

        assert "doc1.md" in tree
        assert "doc2.md" in tree

    def test_build_file_tree_nested(self, exporter, wiki_dir):
        """测试构建嵌套文件树"""
        (wiki_dir / "doc1.md").write_text("# Doc 1", encoding="utf-8")
        (wiki_dir / "subdir" / "doc2.md").parent.mkdir(parents=True, exist_ok=True)
        (wiki_dir / "subdir" / "doc2.md").write_text("# Doc 2", encoding="utf-8")

        tree = exporter._build_file_tree()

        assert "doc1.md" in tree
        assert "subdir" in tree
        assert "doc2.md" in tree["subdir"]

    def test_generate_nav_html_files(self, exporter):
        """测试生成导航 HTML - 文件"""
        tree = {
            "doc1.md": "doc1.md",
            "doc2.md": "doc2.md",
        }

        html = exporter._generate_nav_html(tree)

        assert "<ul>" in html
        assert "</ul>" in html
        assert "doc1.html" in html
        assert "doc2.html" in html

    def test_generate_nav_html_nested(self, exporter):
        """测试生成导航 HTML - 嵌套"""
        tree = {
            "doc1.md": "doc1.md",
            "subdir": {
                "doc2.md": "subdir/doc2.md",
            },
        }

        html = exporter._generate_nav_html(tree)

        assert "folder" in html
        assert "subdir" in html

    def test_markdown_to_html_basic(self, exporter):
        """测试 Markdown 转 HTML - 基础"""
        md_content = "# Title\n\nThis is **bold** text."
        html = exporter._markdown_to_html(md_content)

        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "<title>Wiki</title>" in html
        assert '<h1 id="title">Title</h1>' in html
        assert "<strong>bold</strong>" in html

    def test_markdown_to_html_with_title(self, exporter):
        """测试 Markdown 转 HTML - 自定义标题"""
        md_content = "# Test"
        html = exporter._markdown_to_html(md_content, title="Custom Title")

        assert "<title>Custom Title</title>" in html

    def test_markdown_to_html_with_nav(self, exporter):
        """测试 Markdown 转 HTML - 带导航"""
        md_content = "# Test"
        nav_html = "<ul><li><a href='test.html'>Test</a></li></ul>"
        html = exporter._markdown_to_html(md_content, nav_html=nav_html)

        assert "sidebar" in html
        assert "test.html" in html

    def test_markdown_to_html_code_blocks(self, exporter):
        """测试 Markdown 转 HTML - 代码块"""
        md_content = "```python\nprint('hello')\n```"
        html = exporter._markdown_to_html(md_content)

        assert "<pre>" in html
        assert "<code" in html

    def test_markdown_to_html_tables(self, exporter):
        """测试 Markdown 转 HTML - 表格"""
        md_content = "| A | B |\n|---|---|\n| 1 | 2 |"
        html = exporter._markdown_to_html(md_content)

        assert "<table>" in html
        assert "<th>" in html or "<td>" in html

    def test_process_mermaid(self, exporter):
        """测试 Mermaid 图表处理"""
        html_content = '<pre><code class="language-mermaid">graph TD\nA--&gt;B</code></pre>'
        result = exporter._process_mermaid(html_content)

        assert '<div class="mermaid">' in result
        assert "</div>" in result

    def test_process_mermaid_no_mermaid(self, exporter):
        """测试 Mermaid 处理 - 无 Mermaid"""
        html_content = "<pre><code>print('hello')</code></pre>"
        result = exporter._process_mermaid(html_content)

        assert '<div class="mermaid">' not in result

    @pytest.mark.asyncio
    async def test_export_markdown(self, exporter, wiki_dir):
        """测试导出 Markdown"""
        (wiki_dir / "doc1.md").write_text("# Doc 1", encoding="utf-8")

        output_path = await exporter.export_markdown()

        assert output_path.exists()
        assert (output_path / "doc1.md").exists()
        assert (output_path / "doc1.md").read_text(encoding="utf-8") == "# Doc 1"

    @pytest.mark.asyncio
    async def test_export_markdown_custom_path(self, exporter, wiki_dir, tmp_path):
        """测试导出 Markdown - 自定义路径"""
        (wiki_dir / "doc1.md").write_text("# Doc 1", encoding="utf-8")
        custom_output = tmp_path / "custom_md"

        output_path = await exporter.export_markdown(custom_output)

        assert output_path == custom_output
        assert (output_path / "doc1.md").exists()

    @pytest.mark.asyncio
    async def test_export_markdown_nested(self, exporter, wiki_dir):
        """测试导出 Markdown - 嵌套目录"""
        (wiki_dir / "subdir" / "doc.md").parent.mkdir(parents=True, exist_ok=True)
        (wiki_dir / "subdir" / "doc.md").write_text("# Nested", encoding="utf-8")

        output_path = await exporter.export_markdown()

        assert (output_path / "subdir" / "doc.md").exists()

    @pytest.mark.asyncio
    async def test_export_html_single_file(self, exporter, wiki_dir):
        """测试导出 HTML - 单文件"""
        (wiki_dir / "doc1.md").write_text("# Doc 1\n\nContent.", encoding="utf-8")

        output_path = await exporter.export_html(single_file=True)

        assert output_path.suffix == ".html"
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "Doc 1" in content

    @pytest.mark.asyncio
    async def test_export_html_multiple_files(self, exporter, wiki_dir):
        """测试导出 HTML - 多文件"""
        (wiki_dir / "doc1.md").write_text("# Doc 1", encoding="utf-8")
        (wiki_dir / "doc2.md").write_text("# Doc 2", encoding="utf-8")

        output_path = await exporter.export_html(single_file=False)

        assert output_path.is_dir()
        assert (output_path / "doc1.html").exists()
        assert (output_path / "doc2.html").exists()

    @pytest.mark.asyncio
    async def test_export_html_with_nav(self, exporter, wiki_dir):
        """测试导出 HTML - 带导航"""
        (wiki_dir / "doc1.md").write_text("# Doc 1", encoding="utf-8")

        output_path = await exporter.export_html(single_file=False)
        content = (output_path / "doc1.html").read_text(encoding="utf-8")

        assert "sidebar" in content
        assert "Wiki" in content

    @pytest.mark.asyncio
    async def test_export_html_custom_path(self, exporter, wiki_dir, tmp_path):
        """测试导出 HTML - 自定义路径"""
        (wiki_dir / "doc1.md").write_text("# Doc 1", encoding="utf-8")
        custom_output = tmp_path / "custom_html"

        output_path = await exporter.export_html(custom_output, single_file=False)

        assert output_path == custom_output

    @pytest.mark.asyncio
    async def test_export_pdf_with_weasyprint(self, exporter, wiki_dir):
        """测试导出 PDF - WeasyPrint"""
        (wiki_dir / "doc1.md").write_text("# Doc 1\n\nContent.", encoding="utf-8")

        with patch.dict("sys.modules", {"weasyprint": MagicMock()}):
            mock_html = MagicMock()
            mock_html.return_value.write_pdf = MagicMock()
            with patch.dict("sys.modules", {"weasyprint.HTML": mock_html}):
                output_path = await exporter.export_pdf()

                assert output_path.suffix == ".pdf"

    @pytest.mark.asyncio
    async def test_export_all(self, exporter, wiki_dir):
        """测试批量导出"""
        (wiki_dir / "doc1.md").write_text("# Doc 1", encoding="utf-8")

        with patch.object(exporter, "export_pdf") as mock_pdf:
            mock_pdf.return_value = Path("/tmp/wiki.pdf")
            results = await exporter.export_all(["markdown", "html"])

            assert "markdown" in results
            assert "html" in results

    @pytest.mark.asyncio
    async def test_export_all_custom_formats(self, exporter, wiki_dir):
        """测试批量导出 - 自定义格式"""
        (wiki_dir / "doc1.md").write_text("# Doc 1", encoding="utf-8")

        results = await exporter.export_all(["markdown"])

        assert "markdown" in results
        assert "html" not in results


class TestWikiSharingManager:
    """WikiSharingManager 测试"""

    @pytest.fixture
    def wiki_dir(self, tmp_path):
        """创建 wiki 目录"""
        wiki = tmp_path / "wiki"
        wiki.mkdir(parents=True, exist_ok=True)
        return wiki

    @pytest.fixture
    def project_dir(self, tmp_path):
        """创建项目目录"""
        return tmp_path

    @pytest.fixture
    def sharing_manager(self, wiki_dir, project_dir):
        """创建共享管理器实例"""
        return WikiSharingManager(wiki_dir, project_dir)

    def test_sharing_manager_initialization(self, wiki_dir, project_dir):
        """测试共享管理器初始化"""
        manager = WikiSharingManager(wiki_dir, project_dir)

        assert manager.wiki_dir == wiki_dir
        assert manager.project_dir == project_dir

    def test_prepare_for_sharing_empty(self, sharing_manager):
        """测试准备共享 - 空目录"""
        result = sharing_manager.prepare_for_sharing()

        assert "wiki_dir" in result
        assert result["total_files"] == 0
        assert result["total_size_mb"] == 0.0
        assert "git_commands" in result

    def test_prepare_for_sharing_with_files(self, sharing_manager, wiki_dir):
        """测试准备共享 - 有文件"""
        (wiki_dir / "doc1.md").write_text("# Doc 1\n\nContent here.", encoding="utf-8")
        (wiki_dir / "doc2.md").write_text("# Doc 2\n\nMore content.", encoding="utf-8")

        result = sharing_manager.prepare_for_sharing()

        assert result["total_files"] == 2
        assert result["total_size_mb"] >= 0

    def test_generate_gitignore_suggestion(self, sharing_manager):
        """测试生成 gitignore 建议"""
        suggestion = sharing_manager.generate_gitignore_suggestion()

        assert "gitignore" in suggestion.lower() or ".python-wiki" in suggestion
        assert len(suggestion) > 0

    def test_prepare_for_sharing_git_status(self, sharing_manager, wiki_dir, project_dir):
        """测试准备共享 - Git 状态"""
        (wiki_dir / "doc.md").write_text("# Doc", encoding="utf-8")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=0)
            result = sharing_manager.prepare_for_sharing()

            assert "has_uncommitted_changes" in result
