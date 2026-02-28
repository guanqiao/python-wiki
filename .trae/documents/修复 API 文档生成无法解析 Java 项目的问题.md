## 修复计划

### 问题
`WikiManager` 硬编码使用 `PythonParser`，导致 Java 项目无法被正确解析，API 文档生成无内容。

### 修复方案

**修改 `manager.py`**：
1. 导入 `ParserFactory` 替代直接导入 `PythonParser`
2. 在 `__init__` 中根据项目语言或使用 `ParserFactory` 创建多语言解析器
3. 修改 `_parse_code` 方法使用工厂模式获取合适的解析器
4. 添加项目语言检测逻辑

### 具体改动

```python
# manager.py 修改
from pywiki.parsers.factory import ParserFactory

class WikiManager:
    def __init__(self, ...):
        # 使用 ParserFactory 替代硬编码 PythonParser
        self.parser_factory = ParserFactory(
            exclude_patterns=self.wiki_config.exclude_patterns,
            include_private=self.wiki_config.include_private,
        )
        
    async def _parse_code(self) -> None:
        # 检测项目语言并使用对应解析器
        project_language = self._detect_project_language()
        parser = self.parser_factory.get_parser_for_language(project_language)
        self._parse_result = parser.parse_directory(self.project.path)
```

### 预期效果
- Java 项目将被 `JavaParser` 正确解析
- API 文档将包含 Controller、Service 等模块信息
- 支持多语言项目的自动识别