"""
LLM 统一客户端实现
"""

import ssl
from typing import Any, AsyncIterator, Iterator, Optional

import httpx
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from pywiki.config.models import LLMConfig, LLMProvider
from pywiki.llm.base import BaseLLMClient


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

        self._setup_ssl()
        self._setup_client()

    def _setup_ssl(self) -> None:
        if self.ca_cert:
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
            openai_api_key=self.api_key,
            openai_api_base=self.endpoint,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

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
        messages = []
        if system_prompt:
            messages.append(("system", system_prompt))
        messages.append(("human", prompt))

        response = self._langchain_llm.invoke(messages)
        return response.content

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
        messages = []
        if system_prompt:
            messages.append(("system", system_prompt))
        messages.append(("human", prompt))

        response = await self._langchain_llm.ainvoke(messages)
        return response.content

    def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> Iterator[str]:
        messages = []
        if system_prompt:
            messages.append(("system", system_prompt))
        messages.append(("human", prompt))

        for chunk in self._langchain_llm.stream(messages):
            yield chunk.content

    async def astream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> AsyncIterator[str]:
        messages = []
        if system_prompt:
            messages.append(("system", system_prompt))
        messages.append(("human", prompt))

        async for chunk in self._langchain_llm.astream(messages):
            yield chunk.content

    def count_tokens(self, text: str) -> int:
        return self._langchain_llm.get_num_tokens(text)

    async def test_connection(self) -> bool:
        try:
            response = await self.agenerate("Hello", max_tokens=10)
            return bool(response)
        except Exception:
            return False

    @classmethod
    def from_config(cls, config: LLMConfig) -> "LLMClient":
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
