"""
LLM 统一客户端实现
"""

import ssl
import time
from typing import Any, AsyncIterator, Iterator, Optional

import httpx
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from pywiki.config.models import LLMConfig, LLMProvider
from pywiki.llm.base import BaseLLMClient
from pywiki.monitor.logger import logger


class LLMClient(BaseLLMClient):
    """统一 LLM 客户端，支持多种 Provider"""

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
        provider: str = LLMProvider.OPENAI,
        **kwargs: Any
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.ca_cert = ca_cert
        self.timeout = timeout
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.provider = provider
        self._kwargs = kwargs

        self._http_client: Optional[httpx.AsyncClient] = None
        self._langchain_llm: Optional[ChatOpenAI] = None
        self._ssl_context: Optional[ssl.SSLContext] = None

        logger.info(f"LLMClient 初始化: provider={provider}, model={model}, endpoint={endpoint}")
        
        self._setup_ssl()
        self._setup_client()

    def _setup_ssl(self) -> None:
        if self.ca_cert:
            logger.debug(f"加载 SSL 证书: {self.ca_cert}")
            self._ssl_context = ssl.create_default_context()
            self._ssl_context.load_verify_locations(self.ca_cert)

    def _setup_client(self) -> None:
        http_client_kwargs = {
            "timeout": httpx.Timeout(self.timeout),
        }
        if self._ssl_context:
            http_client_kwargs["verify"] = self._ssl_context

        self._http_client = httpx.AsyncClient(**http_client_kwargs)

        self._langchain_llm = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url=self.endpoint,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )
        logger.debug("LLM 客户端设置完成")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        start_time = time.time()
        logger.debug(f"LLM 同步调用: model={self.model}, prompt_length={len(prompt)}")
        
        try:
            messages = []
            if system_prompt:
                messages.append(("system", system_prompt))
            messages.append(("human", prompt))

            response = self._langchain_llm.invoke(messages)
            duration_ms = (time.time() - start_time) * 1000
            logger.debug(f"LLM 同步响应: 成功, 耗时={duration_ms:.0f}ms, response_length={len(response.content)}")
            return response.content
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"LLM 同步调用失败: 耗时={duration_ms:.0f}ms, 错误={str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def agenerate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        start_time = time.time()
        logger.debug(f"LLM 异步调用: model={self.model}, prompt_length={len(prompt)}")
        
        try:
            messages = []
            if system_prompt:
                messages.append(("system", system_prompt))
            messages.append(("human", prompt))

            response = await self._langchain_llm.ainvoke(messages)
            duration_ms = (time.time() - start_time) * 1000
            logger.debug(f"LLM 异步响应: 成功, 耗时={duration_ms:.0f}ms, response_length={len(response.content)}")
            return response.content
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"LLM 异步调用失败: 耗时={duration_ms:.0f}ms, 错误={str(e)}")
            raise

    def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> Iterator[str]:
        logger.debug(f"LLM 流式调用: model={self.model}, prompt_length={len(prompt)}")
        try:
            messages = []
            if system_prompt:
                messages.append(("system", system_prompt))
            messages.append(("human", prompt))

            for chunk in self._langchain_llm.stream(messages):
                yield chunk.content
            logger.debug("LLM 流式响应完成")
        except Exception as e:
            logger.error(f"LLM 流式调用失败: {str(e)}")
            raise

    async def astream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> AsyncIterator[str]:
        logger.debug(f"LLM 异步流式调用: model={self.model}, prompt_length={len(prompt)}")
        try:
            messages = []
            if system_prompt:
                messages.append(("system", system_prompt))
            messages.append(("human", prompt))

            async for chunk in self._langchain_llm.astream(messages):
                yield chunk.content
            logger.debug("LLM 异步流式响应完成")
        except Exception as e:
            logger.error(f"LLM 异步流式调用失败: {str(e)}")
            raise

    def count_tokens(self, text: str) -> int:
        return self._langchain_llm.get_num_tokens(text)

    async def test_connection(self) -> bool:
        logger.info(f"测试 LLM 连接: model={self.model}, endpoint={self.endpoint}")
        try:
            response = await self.agenerate("Hello", max_tokens=10)
            success = bool(response)
            if success:
                logger.info("LLM 连接测试成功")
            else:
                logger.warning("LLM 连接测试失败: 响应为空")
            return success
        except Exception as e:
            logger.error(f"LLM 连接测试失败: {str(e)}")
            return False

    @classmethod
    def from_config(cls, config: LLMConfig) -> "LLMClient":
        logger.debug(f"从配置创建 LLM 客户端: model={config.model}")
        return cls(
            endpoint=config.endpoint,
            api_key=config.api_key.get_secret_value(),
            model=config.model,
            ca_cert=str(config.ca_cert) if config.ca_cert else None,
            timeout=config.timeout,
            max_retries=config.max_retries,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            provider=config.provider,
        )

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
            logger.debug("LLM 客户端 HTTP 连接已关闭")
