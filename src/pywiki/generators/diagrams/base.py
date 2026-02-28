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
        import re
        
        if not name:
            return "node"
        
        sanitized = name
        
        if re.match(r'^[A-Za-z]:[\\/]', sanitized) or sanitized.startswith('/') or sanitized.startswith('\\'):
            parts = re.split(r'[\\/]', sanitized)
            meaningful_parts = [p for p in parts if p and p != '.' and p != '..' and not re.match(r'^[A-Za-z]:$', p)]
            if meaningful_parts:
                if len(meaningful_parts) > 3:
                    sanitized = '_'.join(meaningful_parts[-3:])
                else:
                    sanitized = '_'.join(meaningful_parts)
        
        sanitized = re.sub(r'[\\/:]', '_', sanitized)
        sanitized = sanitized.replace(".", "_").replace("-", "_").replace(" ", "_")
        sanitized = sanitized.replace("(", "_").replace(")", "_")
        sanitized = sanitized.replace("[", "_").replace("]", "_").replace("{", "_").replace("}", "_")
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', sanitized)
        
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")
        
        sanitized = sanitized.strip("_")
        
        if not sanitized:
            return "node"
        
        if sanitized[0].isdigit():
            sanitized = "n_" + sanitized
        
        return sanitized[:50] if len(sanitized) > 50 else sanitized

    def sanitize_label(self, label: str) -> str:
        """清理标签中的特殊字符"""
        return label.replace('"', "'").replace("\n", " ")
