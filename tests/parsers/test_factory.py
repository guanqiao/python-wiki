"""
解析器工厂测试
"""

from pathlib import Path

import pytest

from pywiki.parsers.factory import ParserFactory, get_parser_for_file, parse_file
from pywiki.parsers.java import JavaParser
from pywiki.parsers.python import PythonParser
from pywiki.parsers.typescript import TypeScriptParser


class TestParserFactory:
    """解析器工厂测试类"""

    @pytest.fixture
    def factory(self):
        """创建工厂实例"""
        return ParserFactory()

    def test_get_supported_extensions(self, factory):
        """测试获取支持的扩展名"""
        extensions = factory.get_supported_extensions()
        assert ".py" in extensions
        assert ".java" in extensions
        assert ".ts" in extensions
        assert ".tsx" in extensions
        assert ".js" in extensions
        assert ".vue" in extensions

    def test_get_parser_for_python(self, factory):
        """测试获取 Python 解析器"""
        parser = factory.get_parser(Path("test.py"))
        assert isinstance(parser, PythonParser)

        parser = factory.get_parser(Path("test.pyi"))
        assert isinstance(parser, PythonParser)

    def test_get_parser_for_typescript(self, factory):
        """测试获取 TypeScript 解析器"""
        parser = factory.get_parser(Path("test.ts"))
        assert isinstance(parser, TypeScriptParser)

        parser = factory.get_parser(Path("test.tsx"))
        assert isinstance(parser, TypeScriptParser)

    def test_get_parser_for_javascript(self, factory):
        """测试获取 JavaScript 解析器"""
        parser = factory.get_parser(Path("test.js"))
        assert isinstance(parser, TypeScriptParser)

        parser = factory.get_parser(Path("test.jsx"))
        assert isinstance(parser, TypeScriptParser)

        parser = factory.get_parser(Path("test.mjs"))
        assert isinstance(parser, TypeScriptParser)

    def test_get_parser_for_vue(self, factory):
        """测试获取 Vue 解析器"""
        parser = factory.get_parser(Path("test.vue"))
        assert isinstance(parser, TypeScriptParser)

    def test_get_parser_for_java(self, factory):
        """测试获取 Java 解析器"""
        parser = factory.get_parser(Path("test.java"))
        assert isinstance(parser, JavaParser)

    def test_get_parser_for_unsupported(self, factory):
        """测试获取不支持的文件类型的解析器"""
        parser = factory.get_parser(Path("test.go"))
        assert parser is None

        parser = factory.get_parser(Path("test.rs"))
        assert parser is None

        parser = factory.get_parser(Path("test.c"))
        assert parser is None

    def test_is_supported(self, factory):
        """测试文件类型是否受支持"""
        assert factory.is_supported(Path("test.py")) is True
        assert factory.is_supported(Path("test.java")) is True
        assert factory.is_supported(Path("test.ts")) is True
        assert factory.is_supported(Path("test.vue")) is True
        assert factory.is_supported(Path("test.go")) is False

    def test_get_parser_info(self, factory):
        """测试获取解析器信息"""
        info = factory.get_parser_info()
        assert ".py" in info
        assert info[".py"] == "PythonParser"
        assert ".java" in info
        assert info[".java"] == "JavaParser"
        assert ".ts" in info
        assert info[".ts"] == "TypeScriptParser"

    def test_register_parser(self, factory):
        """测试注册新解析器"""

        class MockParser:
            pass

        factory.register_parser([".mock"], MockParser)
        assert factory.is_supported(Path("test.mock")) is True

        parser_class = factory.get_parser_for_extension(".mock")
        assert parser_class == MockParser

    def test_register_parser_override(self, factory):
        """测试覆盖已存在的解析器"""

        class NewPythonParser:
            pass

        # 不覆盖应该报错
        with pytest.raises(ValueError):
            factory.register_parser([".py"], NewPythonParser, override=False)

        # 覆盖应该成功
        factory.register_parser([".py"], NewPythonParser, override=True)
        parser_class = factory.get_parser_for_extension(".py")
        assert parser_class == NewPythonParser

    def test_unregister_parser(self, factory):
        """测试注销解析器"""
        assert factory.is_supported(Path("test.py")) is True

        factory.unregister_parser([".py"])
        assert factory.is_supported(Path("test.py")) is False

    def test_parser_caching(self, factory):
        """测试解析器缓存"""
        parser1 = factory.get_parser(Path("test.py"))
        parser2 = factory.get_parser(Path("test.py"))

        # 应该返回同一个实例
        assert parser1 is parser2

    def test_create_default(self):
        """测试创建默认工厂"""
        factory = ParserFactory.create_default()

        assert "node_modules" in factory.exclude_patterns
        assert ".git" in factory.exclude_patterns
        assert factory.include_private is False


class TestHelperFunctions:
    """辅助函数测试类"""

    def test_get_parser_for_file(self):
        """测试 get_parser_for_file 函数"""
        parser = get_parser_for_file(Path("test.py"))
        assert isinstance(parser, PythonParser)

        parser = get_parser_for_file(Path("test.java"))
        assert isinstance(parser, JavaParser)

        parser = get_parser_for_file(Path("test.ts"))
        assert isinstance(parser, TypeScriptParser)

        parser = get_parser_for_file(Path("test.unknown"))
        assert parser is None

    def test_parse_file(self, tmp_path):
        """测试 parse_file 函数"""
        # 创建测试文件
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def hello():
    pass
""")

        result = parse_file(test_file)
        assert result is not None
        assert len(result.modules) == 1

    def test_parse_file_unsupported(self, tmp_path):
        """测试解析不支持的文件类型"""
        test_file = tmp_path / "test.unknown"
        test_file.write_text("content")

        result = parse_file(test_file)
        assert result is None


class TestParserFactoryWithOptions:
    """带选项的工厂测试"""

    def test_exclude_patterns(self, tmp_path):
        """测试排除模式"""
        factory = ParserFactory(
            exclude_patterns=["node_modules", ".git"],
            include_private=False
        )

        parser = factory.get_parser(Path("test.py"))
        assert parser is not None
        assert parser.exclude_patterns == ["node_modules", ".git"]

    def test_include_private_option(self, tmp_path):
        """测试 include_private 选项"""
        factory = ParserFactory(include_private=True)

        parser = factory.get_parser(Path("test.py"))
        assert parser is not None
        assert parser.include_private is True

        parser = factory.get_parser(Path("test.java"))
        assert parser is not None
        assert parser.include_private is True
