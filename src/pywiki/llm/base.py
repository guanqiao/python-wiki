"""
LLM 基础接口定义
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Iterator, Optional


class BaseLLMClient(ABC):
    """LLM 客户端基类"""

    @abstractmethod
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        ca_cert: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any
    ):
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """同步生成文本"""
        pass

    @abstractmethod
    async def agenerate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """异步生成文本"""
        pass

    @abstractmethod
    def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> Iterator[str]:
        """流式生成文本"""
        pass

    @abstractmethod
    async def astream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> AsyncIterator[str]:
        """异步流式生成文本"""
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """计算 token 数量"""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """测试连接"""
        pass
