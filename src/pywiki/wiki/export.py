"""
Wiki 文档导出功能
支持 Markdown、HTML、PDF 格式导出
增强版：支持 Mermaid 图表渲染、导航侧边栏、搜索功能
"""

import asyncio
from pathlib import Path
from typing import Optional, List

import markdown


class WikiExporter:
    """Wiki 文档导出器"""

    def __init__(self, wiki_dir: Path, output_dir: Optional[Path] = None):
        self.wiki_dir = wiki_dir
        self.output_dir = output_dir or wiki_dir.parent / "exports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_wiki_files(self) -> List[Path]:
        """获取所有 Wiki Markdown 文件"""
        return list(self.wiki_dir.rglob("*.md"))

    def _build_file_tree(self) -> dict:
        """构建文件树结构用于导航"""
        files = self._get_wiki_files()
        tree = {}

        for file in files:
            relative = file.relative_to(self.wiki_dir)
            parts = relative.parts

            current = tree
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            current[parts[-1]] = str(relative)

        return tree

    def _generate_nav_html(self, tree: dict, base_path: str = "") -> str:
        """生成导航 HTML"""
        html = "<ul>\n"

        for name, value in sorted(tree.items()):
            if isinstance(value, str):
                # 文件
                link = value.replace(".md", ".html")
                html += f'<li><a href="{link}">{name.replace(".md", "")}</a></li>\n'
            else:
                # 目录
                html += f'<li class="folder">{name}\n'
                html += self._generate_nav_html(value, base_path)
                html += "</li>\n"

        html += "</ul>\n"
        return html

    async def export_markdown(
        self,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        导出为 Markdown 格式（打包所有文件）

        Args:
            output_path: 输出路径，如果为 None 则使用默认路径

        Returns:
            输出目录路径
        """
        if output_path is None:
            output_path = self.output_dir / "markdown"

        output_path.mkdir(parents=True, exist_ok=True)

        md_files = self._get_wiki_files()

        for md_file in md_files:
            relative_path = md_file.relative_to(self.wiki_dir)
            dest_path = output_path / relative_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            with open(md_file, "r", encoding="utf-8") as src:
                with open(dest_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())

        return output_path

    def _markdown_to_html(self, md_content: str, title: str = "Wiki", nav_html: str = "") -> str:
        """
        将 Markdown 转换为 HTML，支持 Mermaid 图表

        Args:
            md_content: Markdown 内容
            title: 页面标题
            nav_html: 导航 HTML

        Returns:
            HTML 内容
        """
        html_content = markdown.markdown(
            md_content,
            extensions=[
                "extra",
                "codehilite",
                "tables",
                "toc",
                "fenced_code",
            ]
        )

        # 检测 Mermaid 图表并添加标记
        html_content = self._process_mermaid(html_content)

        html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            display: flex;
            min-height: 100vh;
        }}
        .sidebar {{
            width: 280px;
            background-color: #f5f5f5;
            border-right: 1px solid #ddd;
            padding: 20px;
            overflow-y: auto;
            position: fixed;
            height: 100vh;
        }}
        .sidebar h2 {{
            margin-top: 0;
            font-size: 1.2em;
            color: #2c3e50;
        }}
        .sidebar ul {{
            list-style: none;
            padding-left: 15px;
        }}
        .sidebar li {{
            margin: 5px 0;
        }}
        .sidebar a {{
            color: #333;
            text-decoration: none;
            font-size: 0.9em;
        }}
        .sidebar a:hover {{
            color: #3498db;
        }}
        .sidebar .folder {{
            font-weight: bold;
            color: #2c3e50;
        }}
        .search-box {{
            width: 100%;
            padding: 8px;
            margin-bottom: 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 0.9em;
        }}
        .content {{
            flex: 1;
            margin-left: 280px;
            padding: 30px;
            max-width: 900px;
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: #2c3e50;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }}
        h1 {{
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "Courier New", monospace;
        }}
        pre {{
            background-color: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        pre code {{
            background-color: transparent;
            color: inherit;
            padding: 0;
        }}
        blockquote {{
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin-left: 0;
            color: #666;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background-color: #f4f4f4;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
        .toc {{
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            padding: 15px;
            margin: 1em 0;
            border-radius: 5px;
        }}
        .toc-title {{
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .mermaid {{
            background-color: #fff;
            padding: 15px;
            border-radius: 5px;
            text-align: center;
        }}
        @media print {{
            .sidebar {{
                display: none;
            }}
            .content {{
                margin-left: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>📚 Wiki 导航</h2>
        <input type="text" class="search-box" placeholder="搜索文档..." id="searchBox">
        {nav_html}
    </div>
    <div class="content">
        {html_content}
    </div>
    <script>
        // 初始化 Mermaid
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose'
        }});

        // 搜索功能
        document.getElementById('searchBox').addEventListener('input', function(e) {{
            const searchTerm = e.target.value.toLowerCase();
            const links = document.querySelectorAll('.sidebar a');

            links.forEach(link => {{
                const text = link.textContent.toLowerCase();
                const li = link.closest('li');
                if (text.includes(searchTerm)) {{
                    li.style.display = 'block';
                }} else {{
                    li.style.display = 'none';
                }}
            }});
        }});
    </script>
</body>
</html>"""

        return html_template

    def _process_mermaid(self, html_content: str) -> str:
        """处理 Mermaid 图表代码块"""
        import re

        # 查找 mermaid 代码块并转换为 mermaid div
        pattern = r'<pre><code class="language-mermaid">(.*?)</code></pre>'
        replacement = r'<div class="mermaid">\1</div>'

        return re.sub(pattern, replacement, html_content, flags=re.DOTALL)

    async def export_html(
        self,
        output_path: Optional[Path] = None,
        single_file: bool = False,
    ) -> Path:
        """
        导出为 HTML 格式

        Args:
            output_path: 输出路径，如果为 None 则使用默认路径
            single_file: 是否导出为单个 HTML 文件

        Returns:
            输出文件或目录路径
        """
        if output_path is None:
            output_path = self.output_dir / "html"

        # 构建导航
        file_tree = self._build_file_tree()
        nav_html = self._generate_nav_html(file_tree)

        if single_file:
            output_path = output_path.with_suffix(".html")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            all_content = ""
            md_files = sorted(self._get_wiki_files())

            for md_file in md_files:
                relative_path = md_file.relative_to(self.wiki_dir)
                all_content += f"\n<h1 id='{str(relative_path).replace('.', '-')}'>{relative_path}</h1>\n"

                with open(md_file, "r", encoding="utf-8") as f:
                    all_content += f.read() + "\n"

            html_content = self._markdown_to_html(all_content, title="Wiki Documentation", nav_html=nav_html)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        else:
            output_path.mkdir(parents=True, exist_ok=True)
            md_files = self._get_wiki_files()

            for md_file in md_files:
                relative_path = md_file.relative_to(self.wiki_dir)
                dest_path = output_path / relative_path.with_suffix(".html")
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                with open(md_file, "r", encoding="utf-8") as f:
                    md_content = f.read()

                html_content = self._markdown_to_html(
                    md_content,
                    title=relative_path.stem,
                    nav_html=nav_html
                )

                with open(dest_path, "w", encoding="utf-8") as f:
                    f.write(html_content)

        return output_path

    async def export_pdf(
        self,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        导出为 PDF 格式

        Args:
            output_path: 输出路径，如果为 None 则使用默认路径

        Returns:
            输出 PDF 文件路径
        """
        try:
            from weasyprint import HTML
        except ImportError:
            # 如果没有 weasyprint，使用替代方案
            return await self._export_pdf_with_playwright(output_path)

        if output_path is None:
            output_path = self.output_dir / "wiki.pdf"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        all_content = ""
        md_files = sorted(self._get_wiki_files())

        for md_file in md_files:
            relative_path = md_file.relative_to(self.wiki_dir)
            all_content += f"\n<h1>{relative_path}</h1>\n"

            with open(md_file, "r", encoding="utf-8") as f:
                all_content += f.read() + "\n"

        html_content = self._markdown_to_html(all_content, title="Wiki Documentation", nav_html="")

        HTML(string=html_content).write_pdf(output_path)

        return output_path

    async def _export_pdf_with_playwright(
        self,
        output_path: Optional[Path] = None,
    ) -> Path:
        """使用 Playwright 导出 PDF（备用方案）"""
        if output_path is None:
            output_path = self.output_dir / "wiki.pdf"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 先导出 HTML
        html_path = await self.export_html(single_file=True)

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                await page.goto(f"file://{html_path.absolute()}")
                await page.pdf(path=output_path, format="A4")
                await browser.close()
        except ImportError:
            # 如果 Playwright 也不可用，返回 HTML 文件
            return html_path

        return output_path

    async def export_all(
        self,
        formats: Optional[List[str]] = None,
    ) -> dict[str, Path]:
        """
        导出为多种格式

        Args:
            formats: 要导出的格式列表，默认为 ["markdown", "html", "pdf"]

        Returns:
            格式到输出路径的映射字典
        """
        if formats is None:
            formats = ["markdown", "html", "pdf"]

        results = {}

        for fmt in formats:
            if fmt == "markdown":
                results[fmt] = await self.export_markdown()
            elif fmt == "html":
                results[fmt] = await self.export_html(single_file=True)
            elif fmt == "pdf":
                results[fmt] = await self.export_pdf()

        return results


class WikiSharingManager:
    """
    Wiki 共享管理器
    支持将 Wiki 推送到 Git 仓库
    """

    def __init__(self, wiki_dir: Path, project_dir: Path):
        self.wiki_dir = wiki_dir
        self.project_dir = project_dir

    def prepare_for_sharing(self) -> dict:
        """
        准备 Wiki 共享

        Returns:
            共享信息字典
        """
        import subprocess

        # 检查 Git 状态
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain", str(self.wiki_dir)],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True
            )
            has_changes = bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            has_changes = False

        # 统计文件
        md_files = list(self.wiki_dir.rglob("*.md"))
        total_files = len(md_files)
        total_size = sum(f.stat().st_size for f in md_files)

        return {
            "wiki_dir": str(self.wiki_dir),
            "total_files": total_files,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "has_uncommitted_changes": has_changes,
            "git_commands": [
                f"git add {self.wiki_dir}",
                f'git commit -m "Update Wiki documentation"',
                "git push"
            ]
        }

    def generate_gitignore_suggestion(self) -> str:
        """生成 .gitignore 建议"""
        return """
# Python Wiki - 可选：忽略自动生成的 Wiki 目录
# 取消注释以下行如果你不想将 Wiki 提交到 Git
# .python-wiki/

# 但保留导出的文档（可选）
# !.python-wiki/exports/
""".strip()
