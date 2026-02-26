
"""
Wiki 文档导出功能
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

    def _markdown_to_html(self, md_content: str, title: str = "Wiki") -> str:
        """
        将 Markdown 转换为 HTML
        
        Args:
            md_content: Markdown 内容
            title: 页面标题
            
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
        
        html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
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
    </style>
</head>
<body>
    {html_content}
</body>
</html>"""
        
        return html_template

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
        
        if single_file:
            output_path = output_path.with_suffix(".html")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            all_content = ""
            md_files = sorted(self._get_wiki_files())
            
            for md_file in md_files:
                relative_path = md_file.relative_to(self.wiki_dir)
                all_content += f"\n## {relative_path}\n\n"
                
                with open(md_file, "r", encoding="utf-8") as f:
                    all_content += f.read() + "\n"
            
            html_content = self._markdown_to_html(all_content, title="Wiki Documentation")
            
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
                    title=relative_path.stem
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
        from weasyprint import HTML
        
        if output_path is None:
            output_path = self.output_dir / "wiki.pdf"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        all_content = ""
        md_files = sorted(self._get_wiki_files())
        
        for md_file in md_files:
            relative_path = md_file.relative_to(self.wiki_dir)
            all_content += f"\n# {relative_path}\n\n"
            
            with open(md_file, "r", encoding="utf-8") as f:
                all_content += f.read() + "\n"
        
        html_content = self._markdown_to_html(all_content, title="Wiki Documentation")
        
        HTML(string=html_content).write_pdf(output_path)
        
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
