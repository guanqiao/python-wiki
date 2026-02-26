"""
内容处理工具
"""

import re
from typing import Optional


class ContentUtils:
    """内容处理工具"""

    @staticmethod
    def extract_code_blocks(content: str) -> list[dict]:
        """提取代码块"""
        pattern = r"```(\w+)?\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)
        return [
            {"language": lang or "text", "code": code.strip()}
            for lang, code in matches
        ]

    @staticmethod
    def extract_headings(content: str) -> list[dict]:
        """提取标题"""
        pattern = r"^(#{1,6})\s+(.+)$"
        matches = re.findall(pattern, content, re.MULTILINE)
        return [
            {"level": len(hashes), "text": text.strip()}
            for hashes, text in matches
        ]

    @staticmethod
    def extract_links(content: str) -> list[dict]:
        """提取链接"""
        pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        matches = re.findall(pattern, content)
        return [{"text": text, "url": url} for text, url in matches]

    @staticmethod
    def extract_images(content: str) -> list[dict]:
        """提取图片"""
        pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
        matches = re.findall(pattern, content)
        return [{"alt": alt, "url": url} for alt, url in matches]

    @staticmethod
    def extract_tables(content: str) -> list[dict]:
        """提取表格"""
        tables = []
        lines = content.split("\n")
        current_table = []
        in_table = False

        for line in lines:
            if "|" in line and line.strip().startswith("|"):
                if not in_table:
                    in_table = True
                    current_table = []
                current_table.append(line.strip())
            else:
                if in_table and current_table:
                    tables.append(ContentUtils._parse_table(current_table))
                    current_table = []
                    in_table = False

        if current_table:
            tables.append(ContentUtils._parse_table(current_table))

        return tables

    @staticmethod
    def _parse_table(lines: list[str]) -> dict:
        """解析表格"""
        if len(lines) < 2:
            return {"headers": [], "rows": []}

        headers = [cell.strip() for cell in lines[0].split("|")[1:-1]]
        rows = []

        for line in lines[2:]:
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            if cells:
                rows.append(cells)

        return {"headers": headers, "rows": rows}

    @staticmethod
    def generate_toc(content: str, max_level: int = 3) -> str:
        """生成目录"""
        headings = ContentUtils.extract_headings(content)
        toc_lines = []

        for heading in headings:
            if heading["level"] > max_level:
                continue

            indent = "  " * (heading["level"] - 1)
            anchor = ContentUtils._generate_anchor(heading["text"])
            toc_lines.append(f"{indent}- [{heading['text']}](#{anchor})")

        return "\n".join(toc_lines)

    @staticmethod
    def _generate_anchor(text: str) -> str:
        """生成锚点"""
        anchor = text.lower()
        anchor = re.sub(r"[^\w\s-]", "", anchor)
        anchor = re.sub(r"[\s]+", "-", anchor)
        return anchor

    @staticmethod
    def truncate_content(
        content: str,
        max_length: int = 500,
        suffix: str = "..."
    ) -> str:
        """截断内容"""
        if len(content) <= max_length:
            return content

        truncated = content[:max_length]
        last_space = truncated.rfind(" ")

        if last_space > max_length * 0.8:
            truncated = truncated[:last_space]

        return truncated + suffix

    @staticmethod
    def count_words(content: str) -> int:
        """统计字数"""
        content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
        content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)
        content = re.sub(r"[#*_`~\[\]()>|-]", "", content)
        words = content.split()
        return len(words)

    @staticmethod
    def count_lines(content: str) -> int:
        """统计行数"""
        return len(content.split("\n"))

    @staticmethod
    def normalize_whitespace(content: str) -> str:
        """规范化空白字符"""
        content = re.sub(r"\r\n", "\n", content)
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = re.sub(r"[ \t]+$", "", content, flags=re.MULTILINE)
        return content.strip()

    @staticmethod
    def escape_markdown(text: str) -> str:
        """转义 Markdown 特殊字符"""
        special_chars = r"\`*_{}[]()#+-.!|"
        for char in special_chars:
            text = text.replace(char, f"\\{char}")
        return text

    @staticmethod
    def unescape_markdown(text: str) -> str:
        """反转义 Markdown 特殊字符"""
        special_chars = r"\`*_{}[]()#+-.!|"
        for char in special_chars:
            text = text.replace(f"\\{char}", char)
        return text
