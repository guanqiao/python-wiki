"""
图表生成器基类
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseDiagramGenerator(ABC):
    """Mermaid 图表生成器基类"""

    @abstractmethod
    def generate(self, data: Any, title: Optional[str] = None) -> str:
        """生成 Mermaid 图表代码"""
        pass

    def wrap_mermaid(self, content: str) -> str:
        """包装 Mermaid 代码块"""
        return f"```mermaid\n{content}\n```"

    def sanitize_id(self, name: str) -> str:
        """将名称转换为有效的 Mermaid ID"""
        return name.replace(".", "_").replace("-", "_").replace(" ", "_")

    def sanitize_label(self, label: str) -> str:
        """清理标签中的特殊字符"""
        return label.replace('"', "'").replace("\n", " ")
