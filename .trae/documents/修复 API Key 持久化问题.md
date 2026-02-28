## 问题
API Key 在保存到配置文件时被序列化为 `"**********"`，因为 Pydantic 的 `SecretStr` 类型默认会隐藏实际值。

## 修复方案
在 [models.py](file:///d:\opensource\github\python-wiki\src\pywiki\config\models.py) 中为 `LLMConfig.api_key` 字段添加自定义序列化器：

```python
from pydantic import field_serializer

class LLMConfig(BaseModel):
    api_key: SecretStr = Field(..., description="API Key")
    
    @field_serializer('api_key', when_used='json')
    def _serialize_api_key(self, value: SecretStr) -> str:
        return value.get_secret_value()
```

这样在调用 `model_dump_json()` 时，API key 会被正确序列化为实际值，而不是星号掩码。