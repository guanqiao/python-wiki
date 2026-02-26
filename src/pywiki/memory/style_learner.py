
"""
编码风格学习器
从代码中自动学习编码风格偏好
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import re

from pywiki.parsers.types import ModuleInfo, ClassInfo, FunctionInfo
from pywiki.memory.memory_manager import MemoryManager
from pywiki.memory.memory_entry import MemoryCategory


@dataclass
class StyleObservation:
    name: str
    value: Any
    count: int = 1
    examples: list[str] = field(default_factory=list)


class StyleLearner:
    """编码风格学习器"""

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self._observations: dict[str, StyleObservation] = {}

    def analyze_module(self, module: ModuleInfo) -&gt; dict:
        """分析模块并学习编码风格"""
        observations = {}

        naming_observations = self._analyze_naming_conventions(module)
        self._merge_observations(naming_observations)

        docstring_observations = self._analyze_docstring_style(module)
        self._merge_observations(docstring_observations)

        import_observations = self._analyze_import_style(module)
        self._merge_observations(import_observations)

        type_hint_observations = self._analyze_type_hint_usage(module)
        self._merge_observations(type_hint_observations)

        for cls in module.classes:
            class_observations = self._analyze_class_style(cls)
            self._merge_observations(class_observations)

        for func in module.functions:
            func_observations = self._analyze_function_style(func)
            self._merge_observations(func_observations)

        return dict(self._observations)

    def _analyze_naming_conventions(self, module: ModuleInfo) -&gt; dict[str, StyleObservation]:
        """分析命名规范"""
        observations = {}

        snake_case_funcs = 0
        camel_case_funcs = 0

        for func in module.functions:
            if "_" in func.name and func.name.islower():
                snake_case_funcs += 1
            elif func.name[0].islower():
                camel_case_funcs += 1

        if snake_case_funcs &gt; camel_case_funcs:
            observations["function_naming"] = StyleObservation(
                name="function_naming",
                value="snake_case",
                count=snake_case_funcs,
                examples=[f.name for f in module.functions[:3]],
            )
        elif camel_case_funcs &gt; 0:
            observations["function_naming"] = StyleObservation(
                name="function_naming",
                value="camelCase",
                count=camel_case_funcs,
                examples=[f.name for f in module.functions[:3]],
            )

        class_count = len(module.classes)
        if class_count &gt; 0:
            observations["class_naming"] = StyleObservation(
                name="class_naming",
                value="PascalCase",
                count=class_count,
                examples=[c.name for c in module.classes[:3]],
            )

        private_funcs = sum(1 for f in module.functions if f.name.startswith("_"))
        if private_funcs &gt; 0:
            observations["private_prefix"] = StyleObservation(
                name="private_prefix",
                value="single_underscore",
                count=private_funcs,
                examples=[f.name for f in module.functions if f.name.startswith("_")][:3],
            )

        return observations

    def _analyze_docstring_style(self, module: ModuleInfo) -&gt; dict[str, StyleObservation]:
        """分析文档字符串风格"""
        observations = {}

        google_style = 0
        numpy_style = 0
        sphinx_style = 0
        no_docstring = 0

        for func in module.functions:
            if not func.docstring:
                no_docstring += 1
                continue

            if "Args:" in func.docstring or "Returns:" in func.docstring:
                google_style += 1
            elif "Parameters" in func.docstring and "----------" in func.docstring:
                numpy_style += 1
            elif ":param " in func.docstring or ":return:" in func.docstring:
                sphinx_style += 1

        total_docstrings = google_style + numpy_style + sphinx_style
        if total_docstrings &gt; 0:
            if google_style &gt;= numpy_style and google_style &gt;= sphinx_style:
                observations["docstring_style"] = StyleObservation(
                    name="docstring_style",
                    value="google",
                    count=google_style,
                )
            elif numpy_style &gt;= sphinx_style:
                observations["docstring_style"] = StyleObservation(
                    name="docstring_style",
                    value="numpy",
                    count=numpy_style,
                )
            else:
                observations["docstring_style"] = StyleObservation(
                    name="docstring_style",
                    value="sphinx",
                    count=sphinx_style,
                )

        if no_docstring &gt; 0:
            observations["docstring_coverage"] = StyleObservation(
                name="docstring_coverage",
                value=f"{(total_docstrings / (total_docstrings + no_docstring)) * 100:.1f}%",
                count=total_docstrings,
            )

        return observations

    def _analyze_import_style(self, module: ModuleInfo) -&gt; dict[str, StyleObservation]:
        """分析导入风格"""
        observations = {}

        from_imports = sum(1 for imp in module.imports if imp.is_from_import)
        direct_imports = len(module.imports) - from_imports

        if from_imports &gt; direct_imports:
            observations["import_style"] = StyleObservation(
                name="import_style",
                value="from_import",
                count=from_imports,
            )
        else:
            observations["import_style"] = StyleObservation(
                name="import_style",
                value="direct_import",
                count=direct_imports,
            )

        sorted_imports = all(
            module.imports[i].module &lt;= module.imports[i + 1].module
            for i in range(len(module.imports) - 1)
        )
        if sorted_imports and len(module.imports) &gt; 1:
            observations["import_ordering"] = StyleObservation(
                name="import_ordering",
                value="alphabetical",
                count=len(module.imports),
            )

        return observations

    def _analyze_type_hint_usage(self, module: ModuleInfo) -&gt; dict[str, StyleObservation]:
        """分析类型提示使用"""
        observations = {}

        typed_funcs = 0
        untyped_funcs = 0
        return_typed = 0

        for func in module.functions:
            has_param_types = any(p.type_hint for p in func.parameters)
            has_return_type = func.return_type is not None

            if has_param_types:
                typed_funcs += 1
            else:
                untyped_funcs += 1

            if has_return_type:
                return_typed += 1

        total_funcs = typed_funcs + untyped_funcs
        if total_funcs &gt; 0:
            observations["type_hint_usage"] = StyleObservation(
                name="type_hint_usage",
                value=f"{(typed_funcs / total_funcs) * 100:.1f}%",
                count=typed_funcs,
            )

            observations["return_type_hints"] = StyleObservation(
                name="return_type_hints",
                value=f"{(return_typed / total_funcs) * 100:.1f}%",
                count=return_typed,
            )

        return observations

    def _analyze_class_style(self, cls: ClassInfo) -&gt; dict[str, StyleObservation]:
        """分析类风格"""
        observations = {}

        if cls.is_dataclass:
            observations["dataclass_usage"] = StyleObservation(
                name="dataclass_usage",
                value=True,
                count=1,
                examples=[cls.name],
            )

        if cls.docstring:
            observations["class_docstring"] = StyleObservation(
                name="class_docstring",
                value=True,
                count=1,
                examples=[cls.name],
            )

        property_methods = sum(1 for m in cls.methods if "@property" in m.decorators)
        if property_methods &gt; 0:
            observations["property_usage"] = StyleObservation(
                name="property_usage",
                value=True,
                count=property_methods,
                examples=[m.name for m in cls.methods if "@property" in m.decorators][:3],
            )

        return observations

    def _analyze_function_style(self, func: FunctionInfo) -&gt; dict[str, StyleObservation]:
        """分析函数风格"""
        observations = {}

        if func.is_async:
            observations["async_usage"] = StyleObservation(
                name="async_usage",
                value=True,
                count=1,
                examples=[func.name],
            )

        if len(func.decorators) &gt; 0:
            observations["decorator_usage"] = StyleObservation(
                name="decorator_usage",
                value=True,
                count=len(func.decorators),
                examples=func.decorators[:3],
            )

        line_count = func.line_end - func.line_start if func.line_end and func.line_start else 0
        if line_count &gt; 0:
            observations["avg_function_length"] = StyleObservation(
                name="avg_function_length",
                value=line_count,
                count=1,
            )

        return observations

    def _merge_observations(self, new_observations: dict[str, StyleObservation]) -&gt; None:
        """合并观察结果"""
        for name, obs in new_observations.items():
            if name in self._observations:
                existing = self._observations[name]
                existing.count += obs.count
                existing.examples.extend(obs.examples)
            else:
                self._observations[name] = obs

    def learn_and_save(self) -&gt; dict:
        """学习并保存编码风格"""
        learned_styles = {}

        for name, obs in self._observations.items():
            if obs.count &gt;= 3:
                self.memory_manager.learn_from_interaction("code_style", {
                    "name": name,
                    "value": obs.value,
                    "project_specific": False,
                })
                learned_styles[name] = obs.value

        return learned_styles

    def get_style_report(self) -&gt; dict:
        """获取风格报告"""
        return {
            name: {
                "value": obs.value,
                "confidence": min(obs.count / 10, 1.0),
                "examples": obs.examples[:5],
            }
            for name, obs in self._observations.items()
        }

    def reset(self) -&gt; None:
        """重置观察"""
        self._observations.clear()
