## 修复方案

**修改文件：** `src/pywiki/llm/client.py`

**修改内容：** 在 `_setup_client` 方法中，将自定义的 `httpx.AsyncClient` 传递给 `ChatOpenAI`

```python
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
        http_async_client=self._http_client,  # ← 添加这行
    )
```

**原理：** `ChatOpenAI` 支持 `http_async_client` 参数，用于传入自定义的异步 HTTP 客户端，这样 SSL 配置才能生效。