"""
Python Wiki 测试
"""

import pytest
from pathlib import Path
from pywiki.config.models import LLMConfig, WikiConfig, ProjectConfig, LLMProvider, Language


class TestModels:
    """配置模型测试"""

    def test_llm_config_defaults(self):
        """测试 LLM 配置默认值"""
        config = LLMConfig(api_key="test-key")
        assert config.provider == LLMProvider.OPENAI
        assert config.endpoint == "https://api.openai.com/v1"
        assert config.model == "gpt-4"
        assert config.timeout == 60
        assert config.max_retries == 3
        assert config.temperature == 0.7
        assert config.max_tokens == 4096

    def test_wiki_config_defaults(self):
        """测试 Wiki 配置默认值"""
        config = WikiConfig()
        assert config.language == Language.ZH
        assert config.max_files == 6000
        assert config.generate_diagrams is True
        assert len(config.exclude_patterns) > 0

    def test_project_config(self):
        """测试项目配置"""
        config = ProjectConfig(
            name="test-project",
            path=Path("/tmp/test"),
            llm=LLMConfig(api_key="test-key"),
        )
        assert config.name == "test-project"
        assert config.path == Path("/tmp/test")


class TestPythonParser:
    """Python 解析器测试"""

    def test_parse_simple_function(self, tmp_path):
        """测试解析简单函数"""
        from pywiki.parsers.python import PythonParser

        test_file = tmp_path / "test.py"
        test_file.write_text('''
def hello(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"
''')

        parser = PythonParser()
        result = parser.parse_file(test_file)

        assert len(result.modules) == 1
        assert len(result.modules[0].functions) == 1
        assert result.modules[0].functions[0].name == "hello"

    def test_parse_class(self, tmp_path):
        """测试解析类"""
        from pywiki.parsers.python import PythonParser

        test_file = tmp_path / "test.py"
        test_file.write_text('''
class Calculator:
    """A simple calculator."""

    def add(self, a: int, b: int) -> int:
        return a + b

    def subtract(self, a: int, b: int) -> int:
        return a - b
''')

        parser = PythonParser()
        result = parser.parse_file(test_file)

        assert len(result.modules[0].classes) == 1
        cls = result.modules[0].classes[0]
        assert cls.name == "Calculator"
        assert len(cls.methods) == 2


class TestDiagramGenerators:
    """图表生成器测试"""

    def test_architecture_diagram(self):
        """测试架构图生成"""
        from pywiki.generators.diagrams import ArchitectureDiagramGenerator

        gen = ArchitectureDiagramGenerator()
        result = gen.generate({
            "layers": [
                {
                    "name": "Frontend",
                    "components": [{"name": "UI", "type": "node"}]
                },
                {
                    "name": "Backend",
                    "components": [{"name": "API", "type": "node"}]
                }
            ],
            "connections": [
                {"source": "UI", "target": "API"}
            ]
        })

        assert "graph TB" in result
        assert "Frontend" in result
        assert "Backend" in result

    def test_flowchart_generator(self):
        """测试流程图生成"""
        from pywiki.generators.diagrams import FlowchartGenerator

        gen = FlowchartGenerator()
        result = gen.generate({
            "nodes": [
                {"id": "start", "label": "开始", "type": "start"},
                {"id": "end", "label": "结束", "type": "end"},
            ],
            "edges": [
                {"source": "start", "target": "end"}
            ]
        })

        assert "flowchart TD" in result
        assert "开始" in result
        assert "结束" in result

    def test_class_diagram(self):
        """测试类图生成"""
        from pywiki.generators.diagrams import ClassDiagramGenerator

        gen = ClassDiagramGenerator()
        result = gen.generate({
            "classes": [
                {
                    "name": "User",
                    "attributes": [
                        {"name": "id", "type": "int", "visibility": "public"}
                    ],
                    "methods": [
                        {"name": "save", "visibility": "public"}
                    ]
                }
            ],
            "relationships": []
        })

        assert "classDiagram" in result
        assert "User" in result


class TestMarkdownGenerator:
    """Markdown 生成器测试"""

    def test_generate_module_doc(self):
        """测试生成模块文档"""
        from pywiki.generators.markdown import MarkdownGenerator
        from pywiki.parsers.types import ModuleInfo

        gen = MarkdownGenerator()
        module = ModuleInfo(
            name="test_module",
            file_path=Path("/tmp/test.py"),
            docstring="Test module docstring.",
        )

        result = gen.generate_module_doc(module)

        assert "# test_module" in result
        assert "Test module docstring" in result
