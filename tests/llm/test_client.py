"""
LLM 客户端测试
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pywiki.llm.client import LLMClient
from pywiki.llm.base import BaseLLMClient
from pywiki.config.models import LLMConfig, LLMProvider


class TestLLMClientInit:
    """LLMClient 初始化测试"""

    def test_init_basic(self):
        """测试基本初始化"""
        with patch.object(LLMClient, '_setup_ssl'), \
             patch.object(LLMClient, '_setup_client'):
            client = LLMClient(
                endpoint="https://api.openai.com/v1",
                api_key="test-key",
                model="gpt-4",
            )

        assert client.endpoint == "https://api.openai.com/v1"
        assert client.api_key == "test-key"
        assert client.model == "gpt-4"
        assert client.timeout == 300
        assert client.max_retries == 5
        assert client.temperature == 0.7
        assert client.max_tokens == 4096

    def test_init_with_custom_params(self):
        """测试自定义参数初始化"""
        with patch.object(LLMClient, '_setup_ssl'), \
             patch.object(LLMClient, '_setup_client'):
            client = LLMClient(
                endpoint="https://api.example.com",
                api_key="custom-key",
                model="custom-model",
                timeout=120,
                max_retries=3,
                temperature=0.5,
                max_tokens=2048,
                provider="custom",
            )

        assert client.timeout == 120
        assert client.max_retries == 3
        assert client.temperature == 0.5
        assert client.max_tokens == 2048
        assert client.provider == "custom"

    def test_init_strips_endpoint_slash(self):
        """测试 endpoint 尾部斜杠被移除"""
        with patch.object(LLMClient, '_setup_ssl'), \
             patch.object(LLMClient, '_setup_client'):
            client = LLMClient(
                endpoint="https://api.openai.com/v1/",
                api_key="test-key",
                model="gpt-4",
            )

        assert client.endpoint == "https://api.openai.com/v1"

    def test_from_config(self, tmp_path: Path):
        """测试从配置创建客户端"""
        config = LLMConfig(
            endpoint="https://api.openai.com/v1",
            api_key="test-api-key",
            model="gpt-4-turbo",
            provider=LLMProvider.OPENAI,
            timeout=60,
            max_retries=3,
            temperature=0.8,
            max_tokens=8192,
        )

        with patch.object(LLMClient, '_setup_ssl'), \
             patch.object(LLMClient, '_setup_client'):
            client = LLMClient.from_config(config)

        assert client.endpoint == "https://api.openai.com/v1"
        assert client.model == "gpt-4-turbo"
        assert client.timeout == 60
        assert client.temperature == 0.8
        assert client.max_tokens == 8192


class TestLLMClientSSL:
    """LLMClient SSL 配置测试"""

    def test_setup_ssl_without_cert(self):
        """测试无证书时 SSL 设置"""
        with patch.object(LLMClient, '_setup_client'):
            client = LLMClient(
                endpoint="https://api.openai.com/v1",
                api_key="test-key",
                model="gpt-4",
            )

        assert client._ssl_context is None

    def test_setup_ssl_with_cert(self, tmp_path: Path):
        """测试有证书时 SSL 设置"""
        cert_file = tmp_path / "ca.crt"
        cert_file.write_text("-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----")

        with patch.object(LLMClient, '_setup_client'):
            with patch('ssl.create_default_context') as mock_ssl:
                mock_context = MagicMock()
                mock_ssl.return_value = mock_context

                client = LLMClient(
                    endpoint="https://api.openai.com/v1",
                    api_key="test-key",
                    model="gpt-4",
                    ca_cert=str(cert_file),
                )

                mock_ssl.assert_called_once()
                mock_context.load_verify_locations.assert_called_once()


class TestLLMClientGenerate:
    """LLMClient 生成方法测试"""

    @pytest.fixture
    def mock_client(self):
        """创建 Mock 客户端"""
        with patch.object(LLMClient, '_setup_ssl'), \
             patch.object(LLMClient, '_setup_client'):
            client = LLMClient(
                endpoint="https://api.openai.com/v1",
                api_key="test-key",
                model="gpt-4",
            )

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Generated response"
        mock_llm.invoke.return_value = mock_response
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        client._langchain_llm = mock_llm

        return client

    def test_generate_basic(self, mock_client: LLMClient):
        """测试基本同步生成"""
        result = mock_client.generate("Hello, world!")

        assert result == "Generated response"
        mock_client._langchain_llm.invoke.assert_called_once()

    def test_generate_with_system_prompt(self, mock_client: LLMClient):
        """测试带系统提示的同步生成"""
        result = mock_client.generate(
            prompt="Hello",
            system_prompt="You are a helpful assistant.",
        )

        assert result == "Generated response"
        call_args = mock_client._langchain_llm.invoke.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0] == ("system", "You are a helpful assistant.")
        assert call_args[1] == ("human", "Hello")

    @pytest.mark.asyncio
    async def test_agenerate_basic(self, mock_client: LLMClient):
        """测试基本异步生成"""
        result = await mock_client.agenerate("Hello, world!")

        assert result == "Generated response"
        mock_client._langchain_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_agenerate_with_system_prompt(self, mock_client: LLMClient):
        """测试带系统提示的异步生成"""
        result = await mock_client.agenerate(
            prompt="Hello",
            system_prompt="You are a helpful assistant.",
        )

        assert result == "Generated response"


class TestLLMClientStream:
    """LLMClient 流式生成测试"""

    @pytest.fixture
    def mock_stream_client(self):
        """创建支持流式的 Mock 客户端"""
        with patch.object(LLMClient, '_setup_ssl'), \
             patch.object(LLMClient, '_setup_client'):
            client = LLMClient(
                endpoint="https://api.openai.com/v1",
                api_key="test-key",
                model="gpt-4",
            )

        mock_llm = MagicMock()
        mock_chunks = [
            MagicMock(content="Hello"),
            MagicMock(content=" "),
            MagicMock(content="World"),
        ]
        mock_llm.stream.return_value = iter(mock_chunks)

        async_chunks = [
            MagicMock(content="Hello"),
            MagicMock(content=" "),
            MagicMock(content="World"),
        ]
        mock_llm.astream = AsyncMock()
        mock_llm.astream.return_value.__aiter__ = lambda self: self
        mock_llm.astream.return_value.__anext__ = AsyncMock(side_effect=[
            async_chunks[0], async_chunks[1], async_chunks[2], StopAsyncIteration
        ])

        client._langchain_llm = mock_llm
        return client

    def test_stream_basic(self, mock_stream_client: LLMClient):
        """测试基本流式生成"""
        results = list(mock_stream_client.stream("Hello"))

        assert len(results) == 3
        assert results[0] == "Hello"
        assert results[1] == " "
        assert results[2] == "World"

    @pytest.mark.asyncio
    async def test_astream_basic(self, mock_stream_client: LLMClient):
        """测试基本异步流式生成"""
        mock_chunks = [
            MagicMock(content="Hello"),
            MagicMock(content=" World"),
        ]

        async def async_gen(*args, **kwargs):
            for chunk in mock_chunks:
                yield chunk

        mock_stream_client._langchain_llm.astream = async_gen

        results = []
        async for chunk in mock_stream_client.astream("Hello"):
            results.append(chunk)

        assert len(results) == 2


class TestLLMClientTokenCount:
    """LLMClient Token 计数测试"""

    def test_count_tokens(self):
        """测试 token 计数"""
        with patch.object(LLMClient, '_setup_ssl'), \
             patch.object(LLMClient, '_setup_client'):
            client = LLMClient(
                endpoint="https://api.openai.com/v1",
                api_key="test-key",
                model="gpt-4",
            )

        mock_llm = MagicMock()
        mock_llm.get_num_tokens.return_value = 10
        client._langchain_llm = mock_llm

        result = client.count_tokens("Hello, world!")

        assert result == 10
        mock_llm.get_num_tokens.assert_called_once_with("Hello, world!")


class TestLLMClientConnection:
    """LLMClient 连接测试"""

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """测试连接成功"""
        with patch.object(LLMClient, '_setup_ssl'), \
             patch.object(LLMClient, '_setup_client'):
            client = LLMClient(
                endpoint="https://api.openai.com/v1",
                api_key="test-key",
                model="gpt-4",
            )

        client.agenerate = AsyncMock(return_value="Hello")

        result = await client.test_connection()

        assert result is True
        client.agenerate.assert_called_once_with("Hello", max_tokens=10)

    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """测试连接失败"""
        with patch.object(LLMClient, '_setup_ssl'), \
             patch.object(LLMClient, '_setup_client'):
            client = LLMClient(
                endpoint="https://api.openai.com/v1",
                api_key="test-key",
                model="gpt-4",
            )

        client.agenerate = AsyncMock(side_effect=Exception("Connection error"))

        result = await client.test_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_test_connection_empty_response(self):
        """测试连接返回空响应"""
        with patch.object(LLMClient, '_setup_ssl'), \
             patch.object(LLMClient, '_setup_client'):
            client = LLMClient(
                endpoint="https://api.openai.com/v1",
                api_key="test-key",
                model="gpt-4",
            )

        client.agenerate = AsyncMock(return_value="")

        result = await client.test_connection()

        assert result is False


class TestLLMClientClose:
    """LLMClient 关闭测试"""

    @pytest.mark.asyncio
    async def test_close_with_http_client(self):
        """测试关闭 HTTP 客户端"""
        with patch.object(LLMClient, '_setup_ssl'), \
             patch.object(LLMClient, '_setup_client'):
            client = LLMClient(
                endpoint="https://api.openai.com/v1",
                api_key="test-key",
                model="gpt-4",
            )

        mock_http_client = AsyncMock()
        client._http_client = mock_http_client

        await client.close()

        mock_http_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_http_client(self):
        """测试无 HTTP 客户端时关闭"""
        with patch.object(LLMClient, '_setup_ssl'), \
             patch.object(LLMClient, '_setup_client'):
            client = LLMClient(
                endpoint="https://api.openai.com/v1",
                api_key="test-key",
                model="gpt-4",
            )

        client._http_client = None

        await client.close()


class TestLLMClientErrorHandling:
    """LLMClient 错误处理测试"""

    def test_generate_with_error(self):
        """测试生成时错误处理"""
        with patch.object(LLMClient, '_setup_ssl'), \
             patch.object(LLMClient, '_setup_client'):
            client = LLMClient(
                endpoint="https://api.openai.com/v1",
                api_key="test-key",
                model="gpt-4",
            )

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("API Error")
        client._langchain_llm = mock_llm

        with pytest.raises(Exception, match="API Error"):
            client.generate("Hello")

    @pytest.mark.asyncio
    async def test_agenerate_with_error(self):
        """测试异步生成时错误处理"""
        with patch.object(LLMClient, '_setup_ssl'), \
             patch.object(LLMClient, '_setup_client'):
            client = LLMClient(
                endpoint="https://api.openai.com/v1",
                api_key="test-key",
                model="gpt-4",
            )

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("API Error"))
        client._langchain_llm = mock_llm

        with pytest.raises(Exception, match="API Error"):
            await client.agenerate("Hello")


class TestLLMClientInheritance:
    """LLMClient 继承测试"""

    def test_inherits_from_base(self):
        """测试继承自 BaseLLMClient"""
        with patch.object(LLMClient, '_setup_ssl'), \
             patch.object(LLMClient, '_setup_client'):
            client = LLMClient(
                endpoint="https://api.openai.com/v1",
                api_key="test-key",
                model="gpt-4",
            )

        assert isinstance(client, BaseLLMClient)
