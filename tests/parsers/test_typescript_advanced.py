"""
TypeScript 解析器高级功能测试
测试枚举、命名空间、Vue Options API 支持
"""

from pathlib import Path

import pytest

from pywiki.parsers.typescript import TypeScriptParser


class TestTypeScriptEnum:
    """TypeScript 枚举测试"""

    @pytest.fixture
    def parser(self):
        return TypeScriptParser()

    def test_parse_simple_enum(self, parser, tmp_path):
        """测试解析简单枚举"""
        code = """
enum Status {
    Active,
    Inactive,
    Pending,
    Deleted
}
"""
        file_path = tmp_path / "test.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        enum = module.classes[0]
        assert enum.name == "Status"
        assert enum.is_enum is True
        assert len(enum.class_variables) == 4

    def test_parse_const_enum(self, parser, tmp_path):
        """测试解析 const 枚举"""
        code = """
const enum Direction {
    Up,
    Down,
    Left,
    Right
}
"""
        file_path = tmp_path / "test.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        enum = result.modules[0].classes[0]
        assert "const" in (enum.docstring or "")

    def test_parse_enum_with_values(self, parser, tmp_path):
        """测试解析带值的枚举"""
        code = """
enum HttpStatus {
    OK = 200,
    NotFound = 404,
    Error = 500
}
"""
        file_path = tmp_path / "test.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        enum = result.modules[0].classes[0]
        assert enum.name == "HttpStatus"


class TestTypeScriptNamespace:
    """TypeScript 命名空间测试"""

    @pytest.fixture
    def parser(self):
        return TypeScriptParser()

    def test_parse_namespace(self, parser, tmp_path):
        """测试解析命名空间"""
        code = """
namespace Utils {
    export function log(message: string): void {
        console.log(message);
    }

    export class Logger {
        debug(msg: string): void {
            console.debug(msg);
        }
    }

    export interface Config {
        level: string;
    }
}
"""
        file_path = tmp_path / "test.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert "Utils" in module.submodules

    def test_parse_nested_namespace(self, parser, tmp_path):
        """测试解析嵌套命名空间"""
        code = """
namespace Outer {
    export namespace Inner {
        export const value = 42;
    }
}
"""
        file_path = tmp_path / "test.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1

    def test_parse_module_declaration(self, parser, tmp_path):
        """测试解析模块声明"""
        code = """
declare module "my-module" {
    export interface MyInterface {
        name: string;
    }

    export type MyType = string | number;
}
"""
        file_path = tmp_path / "test.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1


class TestVueOptionsAPI:
    """Vue Options API 测试"""

    @pytest.fixture
    def parser(self):
        return TypeScriptParser()

    def test_parse_vue_options_api(self, parser, tmp_path):
        """测试解析 Vue Options API 组件"""
        code = """<template>
  <div>
    <h1>{{ title }}</h1>
    <p>{{ message }}</p>
    <button @click="increment">Count: {{ count }}</button>
  </div>
</template>

<script>
export default {
  name: 'CounterComponent',

  props: {
    title: {
      type: String,
      required: true
    },
    initialCount: {
      type: Number,
      default: 0
    }
  },

  emits: ['update', 'change'],

  data() {
    return {
      count: this.initialCount,
      message: 'Hello'
    };
  },

  computed: {
    doubleCount() {
      return this.count * 2;
    },
    displayMessage() {
      return this.message.toUpperCase();
    }
  },

  methods: {
    increment() {
      this.count++;
      this.$emit('update', this.count);
    },
    reset() {
      this.count = this.initialCount;
      this.$emit('change', this.count);
    }
  },

  mounted() {
    console.log('Component mounted');
  },

  beforeUnmount() {
    console.log('Component will unmount');
  }
};
</script>
"""
        file_path = tmp_path / "test.vue"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]

        docstring = module.docstring or ""
        assert "Options API" in docstring
        assert "组件名: CounterComponent" in docstring
        assert "Props: title, initialCount" in docstring
        assert "Emits: update, change" in docstring
        assert "Computed: doubleCount, displayMessage" in docstring
        assert "Methods: increment, reset" in docstring
        assert "生命周期: mounted, beforeUnmount" in docstring

    def test_parse_vue_mixed_api(self, parser, tmp_path):
        """测试解析混合 API 的 Vue 组件"""
        code = """<template>
  <div>{{ msg }}</div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  msg: String
});

const count = ref(0);
const double = computed(() => count.value * 2);
</script>
"""
        file_path = tmp_path / "test.vue"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        module = result.modules[0]
        assert "Composition API" in (module.docstring or "")


class TestTypeScriptAdvancedTypes:
    """TypeScript 高级类型测试"""

    @pytest.fixture
    def parser(self):
        return TypeScriptParser()

    def test_parse_generic_constraints(self, parser, tmp_path):
        """测试解析泛型约束"""
        code = """
interface HasId {
    id: number;
}

function findById<T extends HasId>(items: T[], id: number): T | undefined {
    return items.find(item => item.id === id);
}

class Repository<T extends HasId> {
    private items: T[] = [];

    add(item: T): void {
        this.items.push(item);
    }

    find(id: number): T | undefined {
        return this.items.find(item => item.id === id);
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
        assert len(module.functions) == 1

    def test_parse_mapped_types(self, parser, tmp_path):
        """测试解析映射类型"""
        code = """
type Readonly<T> = {
    readonly [P in keyof T]: T[P];
};

type Optional<T> = {
    [P in keyof T]?: T[P];
};

type Nullable<T> = {
    [P in keyof T]: T[P] | null;
};
"""
        file_path = tmp_path / "test.ts"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
