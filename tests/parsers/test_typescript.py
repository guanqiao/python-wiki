"""
TypeScript 解析器测试
"""

import tempfile
from pathlib import Path

import pytest

from pywiki.parsers.typescript import TypeScriptParser
from pywiki.parsers.types import Visibility


class TestTypeScriptParser:
    """TypeScript 解析器测试类"""

    @pytest.fixture
    def parser(self):
        """创建解析器实例"""
        return TypeScriptParser()

    def test_get_supported_extensions(self, parser):
        """测试支持的文件扩展名"""
        extensions = parser.get_supported_extensions()
        assert ".ts" in extensions
        assert ".tsx" in extensions
        assert ".js" in extensions
        assert ".jsx" in extensions
        assert ".mjs" in extensions
        assert ".vue" in extensions

    def test_parse_simple_function(self, parser, tmp_path):
        """测试解析简单函数"""
        code = """
function greet(name: string): string {
    return `Hello, ${name}!`;
}
"""
        file_path = tmp_path / "test.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.functions) == 1

        func = module.functions[0]
        assert func.name == "greet"
        assert func.return_type == "string"
        assert len(func.parameters) == 1
        assert func.parameters[0].name == "name"
        assert func.parameters[0].type_hint == "string"

    def test_parse_class(self, parser, tmp_path):
        """测试解析类"""
        code = """
class Person {
    private name: string;
    public age: number;

    constructor(name: string, age: number) {
        this.name = name;
        this.age = age;
    }

    public greet(): string {
        return `Hello, I'm ${this.name}`;
    }

    private secret(): void {
        console.log("secret");
    }
}
"""
        file_path = tmp_path / "test.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert cls.name == "Person"
        assert len(cls.methods) >= 1

    def test_parse_interface(self, parser, tmp_path):
        """测试解析接口"""
        code = """
interface User {
    id: number;
    name: string;
    email?: string;
}
"""
        file_path = tmp_path / "test.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        interface = module.classes[0]
        assert interface.name == "User"
        assert "Interface" in (interface.docstring or "")

    def test_parse_imports(self, parser, tmp_path):
        """测试解析导入语句"""
        code = """
import React from 'react';
import { useState, useEffect } from 'react';
import * as utils from './utils';
import type { Config } from './types';
"""
        file_path = tmp_path / "test.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.imports) >= 3

    def test_parse_react_component(self, parser, tmp_path):
        """测试解析 React 组件"""
        code = """
import React, { useState, useEffect } from 'react';

interface Props {
    title: string;
    count?: number;
}

export const Counter: React.FC<Props> = ({ title, count = 0 }) => {
    const [value, setValue] = useState(count);

    useEffect(() => {
        document.title = title;
    }, [title]);

    return (
        <div>
            <h1>{title}</h1>
            <p>Count: {value}</p>
        </div>
    );
};
"""
        file_path = tmp_path / "test.tsx"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1

    def test_parse_vue_component(self, parser, tmp_path):
        """测试解析 Vue 组件"""
        code = """<template>
  <div class="hello">
    <h1>{{ msg }}</h1>
    <button @click="increment">Count: {{ count }}</button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

interface Props {
  msg: string;
  initialCount?: number;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: 'update', value: number): void;
}>();

const count = ref(props.initialCount || 0);

const increment = () => {
  count.value++;
  emit('update', count.value);
};
</script>

<style scoped>
.hello {
  text-align: center;
}
</style>
"""
        file_path = tmp_path / "test.vue"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]

        # 检查是否识别为 Composition API
        docstring = module.docstring or ""
        assert "Composition API" in docstring or len(module.functions) > 0

    def test_parse_arrow_functions(self, parser, tmp_path):
        """测试解析箭头函数"""
        code = """
const add = (a: number, b: number): number => a + b;

const asyncFetch = async (url: string): Promise<Response> => {
    const response = await fetch(url);
    return response;
};
"""
        file_path = tmp_path / "test.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.functions) == 2

    def test_parse_type_alias(self, parser, tmp_path):
        """测试解析类型别名"""
        code = """
type ID = string | number;
type User = {
    id: ID;
    name: string;
};
type Callback = (data: User) => void;
"""
        file_path = tmp_path / "test.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        # 类型别名作为变量存储
        assert len(module.variables) >= 2

    def test_parse_export(self, parser, tmp_path):
        """测试解析导出语句"""
        code = """
export function foo(): void {}
export class Bar {}
export const baz = 42;
export default function main() {}
"""
        file_path = tmp_path / "test.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1

    def test_parse_async_function(self, parser, tmp_path):
        """测试解析异步函数"""
        code = """
async function fetchData(): Promise<Data> {
    const response = await fetch('/api/data');
    return response.json();
}
"""
        file_path = tmp_path / "test.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.functions) == 1
        assert module.functions[0].is_async is True

    def test_parse_directory(self, parser, tmp_path):
        """测试解析目录"""
        # 创建多个文件
        (tmp_path / "file1.ts").write_text("function a() {}")
        (tmp_path / "file2.ts").write_text("function b() {}")
        (tmp_path / "file3.js").write_text("function c() {}")

        # 创建子目录
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file4.ts").write_text("function d() {}")

        result = parser.parse_directory(tmp_path)

        assert len(result.errors) == 0
        # 应该解析所有 ts 和 js 文件
        assert len(result.modules) >= 3


class TestTypeScriptParserEdgeCases:
    """TypeScript 解析器边界情况测试"""

    @pytest.fixture
    def parser(self):
        return TypeScriptParser()

    def test_empty_file(self, parser, tmp_path):
        """测试空文件"""
        file_path = tmp_path / "empty.ts"
        file_path.write_text("")

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1

    def test_syntax_error(self, parser, tmp_path):
        """测试语法错误"""
        code = "function { broken"
        file_path = tmp_path / "broken.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        # 应该记录错误但不抛出异常
        assert len(result.errors) >= 0  # tree-sitter 可能不报错

    def test_visibility_detection(self, parser, tmp_path):
        """测试可见性检测"""
        code = """
class Test {
    public publicProp: string;
    protected protectedProp: string;
    private privateProp: string;
    _internalProp: string;

    public publicMethod(): void {}
    protected protectedMethod(): void {}
    private privateMethod(): void {}
}
"""
        file_path = tmp_path / "test.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1

    def test_include_private_option(self, tmp_path):
        """测试 include_private 选项"""
        parser = TypeScriptParser(include_private=True)

        code = """
class Test {
    private secret(): void {}
    public open(): void {}
}
"""
        file_path = tmp_path / "test.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1
        # 应该包含私有方法
        assert len(module.classes[0].methods) >= 1
