"""
设计动机提取器测试
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pywiki.knowledge.design_motivation import (
    DesignPattern,
    DESIGN_PATTERNS,
    DesignMotivationExtractor,
)
from pywiki.knowledge.implicit_extractor import (
    ExtractionContext,
    ImplicitKnowledge,
    KnowledgeType,
    KnowledgePriority,
)
from pywiki.parsers.types import (
    ClassInfo,
    FunctionInfo,
    ModuleInfo,
    PropertyInfo,
)


class TestDesignPattern:
    """DesignPattern 数据类测试"""

    def test_create_design_pattern(self):
        """测试创建设计模式实例"""
        pattern = DesignPattern(
            name="TestPattern",
            category="creational",
            indicators=["test", "pattern"],
            motivation="测试动机",
            benefits=["优点1", "优点2"],
            drawbacks=["缺点1"],
        )

        assert pattern.name == "TestPattern"
        assert pattern.category == "creational"
        assert pattern.indicators == ["test", "pattern"]
        assert pattern.motivation == "测试动机"
        assert pattern.benefits == ["优点1", "优点2"]
        assert pattern.drawbacks == ["缺点1"]

    def test_design_pattern_is_frozen(self):
        """测试设计模式实例可修改"""
        pattern = DesignPattern(
            name="Test",
            category="test",
            indicators=[],
            motivation="",
            benefits=[],
            drawbacks=[],
        )

        pattern.name = "ModifiedTest"
        assert pattern.name == "ModifiedTest"


class TestDesignPatterns:
    """DESIGN_PATTERNS 字典测试"""

    def test_design_patterns_contains_expected_patterns(self):
        """测试包含所有预期的设计模式"""
        expected_patterns = [
            "singleton",
            "factory",
            "builder",
            "observer",
            "strategy",
            "decorator",
            "adapter",
            "facade",
        ]

        for pattern_name in expected_patterns:
            assert pattern_name in DESIGN_PATTERNS
            assert isinstance(DESIGN_PATTERNS[pattern_name], DesignPattern)

    def test_singleton_pattern_definition(self):
        """测试单例模式定义"""
        singleton = DESIGN_PATTERNS["singleton"]

        assert singleton.name == "Singleton"
        assert singleton.category == "creational"
        assert "_instance" in singleton.indicators
        assert "__new__" in singleton.indicators
        assert "get_instance" in singleton.indicators

    def test_factory_pattern_definition(self):
        """测试工厂模式定义"""
        factory = DESIGN_PATTERNS["factory"]

        assert factory.name == "Factory Method"
        assert factory.category == "creational"
        assert "create_" in factory.indicators
        assert "factory" in factory.indicators

    def test_observer_pattern_definition(self):
        """测试观察者模式定义"""
        observer = DESIGN_PATTERNS["observer"]

        assert observer.name == "Observer"
        assert observer.category == "behavioral"
        assert "subscribe" in observer.indicators
        assert "notify" in observer.indicators

    def test_all_patterns_have_required_attributes(self):
        """测试所有模式都有必需属性"""
        for pattern_name, pattern in DESIGN_PATTERNS.items():
            assert pattern.name, f"{pattern_name} 缺少 name"
            assert pattern.category, f"{pattern_name} 缺少 category"
            assert len(pattern.indicators) > 0, f"{pattern_name} 缺少 indicators"
            assert pattern.motivation, f"{pattern_name} 缺少 motivation"
            assert len(pattern.benefits) > 0, f"{pattern_name} 缺少 benefits"
            assert len(pattern.drawbacks) > 0, f"{pattern_name} 缺少 drawbacks"


class TestDesignMotivationExtractor:
    """DesignMotivationExtractor 测试"""

    @pytest.fixture
    def extractor(self):
        """创建提取器实例"""
        return DesignMotivationExtractor()

    @pytest.fixture
    def project_path(self, tmp_path):
        """创建项目路径"""
        return tmp_path

    def test_knowledge_type(self, extractor):
        """测试知识类型属性"""
        assert extractor.knowledge_type == KnowledgeType.DESIGN_DECISION

    def test_extract_returns_list(self, extractor, project_path):
        """测试 extract 方法返回列表"""
        context = ExtractionContext(project_path=project_path)
        result = extractor.extract(context)

        assert isinstance(result, list)

    def test_extract_from_class_singleton(self, extractor, project_path):
        """测试从类提取单例模式"""
        cls = ClassInfo(
            name="DatabaseConnection",
            full_name="app.database.DatabaseConnection",
            class_variables=[
                PropertyInfo(name="_instance"),
            ],
            methods=[
                FunctionInfo(
                    name="get_instance",
                    full_name="app.database.DatabaseConnection.get_instance",
                ),
                FunctionInfo(
                    name="__new__",
                    full_name="app.database.DatabaseConnection.__new__",
                ),
            ],
        )

        context = ExtractionContext(
            project_path=project_path,
            class_info=cls,
        )

        result = extractor.extract(context)

        singleton_knowledge = [
            k for k in result
            if "Singleton" in k.title
        ]

        assert len(singleton_knowledge) > 0
        assert singleton_knowledge[0].confidence > 0

    def test_extract_from_class_factory(self, extractor, project_path):
        """测试从类提取工厂模式"""
        cls = ClassInfo(
            name="WidgetFactory",
            full_name="app.factories.WidgetFactory",
            methods=[
                FunctionInfo(
                    name="create_widget",
                    full_name="app.factories.WidgetFactory.create_widget",
                ),
                FunctionInfo(
                    name="build_widget",
                    full_name="app.factories.WidgetFactory.build_widget",
                ),
            ],
        )

        context = ExtractionContext(
            project_path=project_path,
            class_info=cls,
        )

        result = extractor.extract(context)

        factory_knowledge = [
            k for k in result
            if "Factory" in k.title
        ]

        assert len(factory_knowledge) > 0

    def test_extract_from_class_builder(self, extractor, project_path):
        """测试从类提取建造者模式"""
        cls = ClassInfo(
            name="QueryBuilder",
            full_name="app.query.QueryBuilder",
            methods=[
                FunctionInfo(
                    name="with_filter",
                    full_name="app.query.QueryBuilder.with_filter",
                ),
                FunctionInfo(
                    name="with_sort",
                    full_name="app.query.QueryBuilder.with_sort",
                ),
                FunctionInfo(
                    name="build",
                    full_name="app.query.QueryBuilder.build",
                ),
            ],
        )

        context = ExtractionContext(
            project_path=project_path,
            class_info=cls,
        )

        result = extractor.extract(context)

        builder_knowledge = [
            k for k in result
            if "Builder" in k.title
        ]

        assert len(builder_knowledge) > 0

    def test_extract_from_class_observer(self, extractor, project_path):
        """测试从类提取观察者模式"""
        cls = ClassInfo(
            name="EventEmitter",
            full_name="app.events.EventEmitter",
            methods=[
                FunctionInfo(
                    name="subscribe",
                    full_name="app.events.EventEmitter.subscribe",
                ),
                FunctionInfo(
                    name="notify",
                    full_name="app.events.EventEmitter.notify",
                ),
                FunctionInfo(
                    name="emit",
                    full_name="app.events.EventEmitter.emit",
                ),
            ],
        )

        context = ExtractionContext(
            project_path=project_path,
            class_info=cls,
        )

        result = extractor.extract(context)

        observer_knowledge = [
            k for k in result
            if "Observer" in k.title
        ]

        assert len(observer_knowledge) > 0

    def test_extract_from_class_strategy(self, extractor, project_path):
        """测试从类提取策略模式"""
        cls = ClassInfo(
            name="SortingStrategy",
            full_name="app.strategies.SortingStrategy",
            methods=[
                FunctionInfo(
                    name="execute",
                    full_name="app.strategies.SortingStrategy.execute",
                ),
            ],
        )

        context = ExtractionContext(
            project_path=project_path,
            class_info=cls,
        )

        result = extractor.extract(context)

        strategy_knowledge = [
            k for k in result
            if "Strategy" in k.title
        ]

        assert len(strategy_knowledge) > 0

    def test_extract_from_class_decorator(self, extractor, project_path):
        """测试从类提取装饰器模式"""
        cls = ClassInfo(
            name="CoffeeDecorator",
            full_name="app.decorators.CoffeeDecorator",
            properties=[
                PropertyInfo(name="_wrapped"),
            ],
        )

        context = ExtractionContext(
            project_path=project_path,
            class_info=cls,
        )

        result = extractor.extract(context)

        decorator_knowledge = [
            k for k in result
            if "Decorator" in k.title
        ]

        assert len(decorator_knowledge) > 0

    def test_extract_from_class_adapter(self, extractor, project_path):
        """测试从类提取适配器模式"""
        cls = ClassInfo(
            name="DataAdapter",
            full_name="app.adapters.DataAdapter",
            methods=[
                FunctionInfo(
                    name="convert",
                    full_name="app.adapters.DataAdapter.convert",
                ),
            ],
        )

        context = ExtractionContext(
            project_path=project_path,
            class_info=cls,
        )

        result = extractor.extract(context)

        adapter_knowledge = [
            k for k in result
            if "Adapter" in k.title
        ]

        assert len(adapter_knowledge) > 0

    def test_extract_from_class_facade(self, extractor, project_path):
        """测试从类提取外观模式"""
        cls = ClassInfo(
            name="DatabaseFacade",
            full_name="app.facades.DatabaseFacade",
        )

        context = ExtractionContext(
            project_path=project_path,
            class_info=cls,
        )

        result = extractor.extract(context)

        facade_knowledge = [
            k for k in result
            if "Facade" in k.title
        ]

        assert len(facade_knowledge) > 0

    def test_extract_abstract_class(self, extractor, project_path):
        """测试提取抽象基类"""
        cls = ClassInfo(
            name="AbstractRepository",
            full_name="app.repositories.AbstractRepository",
            is_abstract=True,
            bases=["ABC"],
        )

        context = ExtractionContext(
            project_path=project_path,
            class_info=cls,
        )

        result = extractor.extract(context)

        abstract_knowledge = [
            k for k in result
            if "抽象基类" in k.title
        ]

        assert len(abstract_knowledge) > 0
        assert abstract_knowledge[0].confidence == 0.9

    def test_extract_multiple_inheritance(self, extractor, project_path):
        """测试提取多重继承"""
        cls = ClassInfo(
            name="MultiClass",
            full_name="app.classes.MultiClass",
            bases=["BaseClass1", "BaseClass2", "MixinClass"],
        )

        context = ExtractionContext(
            project_path=project_path,
            class_info=cls,
        )

        result = extractor.extract(context)

        inheritance_knowledge = [
            k for k in result
            if "多重继承" in k.title
        ]

        assert len(inheritance_knowledge) > 0
        assert inheritance_knowledge[0].confidence == 0.95
        assert inheritance_knowledge[0].priority == KnowledgePriority.HIGH

    def test_extract_from_module_factory_functions(self, extractor, project_path):
        """测试从模块提取工厂函数"""
        module = ModuleInfo(
            name="factory_module",
            file_path=project_path / "factory_module.py",
            functions=[
                FunctionInfo(name="create_user", full_name="factory_module.create_user"),
                FunctionInfo(name="create_order", full_name="factory_module.create_order"),
                FunctionInfo(name="build_config", full_name="factory_module.build_config"),
            ],
        )

        context = ExtractionContext(
            project_path=project_path,
            module_info=module,
        )

        result = extractor.extract(context)

        factory_knowledge = [
            k for k in result
            if "工厂函数" in k.title
        ]

        assert len(factory_knowledge) > 0
        assert factory_knowledge[0].confidence == 0.8

    def test_extract_from_module_large_module(self, extractor, project_path):
        """测试从大型模块提取"""
        classes = [
            ClassInfo(name=f"Class{i}", full_name=f"module.Class{i}")
            for i in range(15)
        ]

        module = ModuleInfo(
            name="large_module",
            file_path=project_path / "large_module.py",
            classes=classes,
        )

        context = ExtractionContext(
            project_path=project_path,
            module_info=module,
        )

        result = extractor.extract(context)

        large_module_knowledge = [
            k for k in result
            if "大型模块" in k.title
        ]

        assert len(large_module_knowledge) > 0
        assert large_module_knowledge[0].priority == KnowledgePriority.LOW

    def test_extract_from_code_todo_markers(self, extractor, project_path):
        """测试从代码提取 TODO 标记"""
        code = '''
def process_data(data):
    # TODO: Add validation
    pass

def calculate_total(items):
    # FIXME: Handle empty list
    return sum(items)

def legacy_code():
    # XXX: This is a hack
    pass
'''

        context = ExtractionContext(
            project_path=project_path,
            code_content=code,
        )

        result = extractor.extract(context)

        todo_knowledge = [
            k for k in result
            if k.knowledge_type == KnowledgeType.TECH_DEBT
        ]

        assert len(todo_knowledge) >= 3

        fixme_knowledge = [
            k for k in todo_knowledge
            if "FIXME" in k.title
        ]
        xxx_knowledge = [
            k for k in todo_knowledge
            if "XXX" in k.title
        ]

        assert len(fixme_knowledge) > 0
        assert fixme_knowledge[0].priority == KnowledgePriority.HIGH

        assert len(xxx_knowledge) > 0
        assert xxx_knowledge[0].priority == KnowledgePriority.HIGH

    def test_extract_from_code_deprecated(self, extractor, project_path):
        """测试从代码提取废弃标记"""
        code = '''
@deprecated
def old_function():
    pass

class OldClass:
    """deprecated: use NewClass instead"""
    pass
'''

        context = ExtractionContext(
            project_path=project_path,
            code_content=code,
        )

        result = extractor.extract(context)

        deprecated_knowledge = [
            k for k in result
            if "废弃" in k.title
        ]

        assert len(deprecated_knowledge) > 0
        assert deprecated_knowledge[0].priority == KnowledgePriority.HIGH

    def test_detect_pattern_in_class_with_name_match(self, extractor, project_path):
        """测试类名匹配模式检测"""
        pattern = DESIGN_PATTERNS["facade"]

        cls = ClassInfo(
            name="DatabaseFacade",
            full_name="app.database.DatabaseFacade",
        )

        result = extractor._detect_pattern_in_class(cls, pattern)

        assert result is not None
        assert "类名包含" in result["evidence"][0]

    def test_detect_pattern_in_class_with_method_match(self, extractor, project_path):
        """测试方法名匹配模式检测"""
        pattern = DESIGN_PATTERNS["factory"]

        cls = ClassInfo(
            name="MyClass",
            full_name="app.MyClass",
            methods=[
                FunctionInfo(name="create_product", full_name="app.MyClass.create_product"),
                FunctionInfo(name="factory_method", full_name="app.MyClass.factory_method"),
            ],
        )

        result = extractor._detect_pattern_in_class(cls, pattern)

        assert result is not None
        assert any("方法" in e for e in result["evidence"])

    def test_detect_pattern_in_class_no_match(self, extractor, project_path):
        """测试无匹配的模式检测"""
        pattern = DESIGN_PATTERNS["singleton"]

        cls = ClassInfo(
            name="RegularClass",
            full_name="app.RegularClass",
            methods=[
                FunctionInfo(name="do_something", full_name="app.RegularClass.do_something"),
            ],
        )

        result = extractor._detect_pattern_in_class(cls, pattern)

        assert result is None

    def test_generate_impact(self, extractor):
        """测试影响描述生成"""
        pattern = DESIGN_PATTERNS["singleton"]
        impact = extractor._generate_impact(pattern)

        assert "优点" in impact
        assert "潜在问题" in impact

    def test_generate_recommendation_creational(self, extractor):
        """测试创建型模式建议生成"""
        pattern = DESIGN_PATTERNS["factory"]
        cls = ClassInfo(name="WidgetFactory", full_name="app.WidgetFactory")

        recommendation = extractor._generate_recommendation(pattern, cls)

        assert "WidgetFactory" in recommendation
        assert "单一职责" in recommendation

    def test_generate_recommendation_behavioral(self, extractor):
        """测试行为型模式建议生成"""
        pattern = DESIGN_PATTERNS["observer"]
        cls = ClassInfo(name="EventEmitter", full_name="app.EventEmitter")

        recommendation = extractor._generate_recommendation(pattern, cls)

        assert "EventEmitter" in recommendation
        assert "生命周期" in recommendation

    def test_generate_recommendation_structural(self, extractor):
        """测试结构型模式建议生成"""
        pattern = DESIGN_PATTERNS["adapter"]
        cls = ClassInfo(name="DataAdapter", full_name="app.DataAdapter")

        recommendation = extractor._generate_recommendation(pattern, cls)

        assert "DataAdapter" in recommendation
        assert "接口简洁" in recommendation

    def test_extract_with_all_contexts(self, extractor, project_path):
        """测试同时提供所有上下文"""
        cls = ClassInfo(
            name="SingletonService",
            full_name="app.services.SingletonService",
            class_variables=[PropertyInfo(name="_instance")],
            methods=[
                FunctionInfo(name="get_instance", full_name="app.services.SingletonService.get_instance"),
            ],
        )

        module = ModuleInfo(
            name="services",
            file_path=project_path / "services.py",
            classes=[cls],
            functions=[
                FunctionInfo(name="create_service", full_name="services.create_service"),
            ],
        )

        code = '''
# TODO: Add caching
class SingletonService:
    _instance = None
    
    def get_instance(cls):
        pass
'''

        context = ExtractionContext(
            project_path=project_path,
            module_info=module,
            class_info=cls,
            code_content=code,
        )

        result = extractor.extract(context)

        assert len(result) > 0

        knowledge_types = {k.knowledge_type for k in result}
        assert KnowledgeType.DESIGN_DECISION in knowledge_types

    def test_extract_empty_context(self, extractor, project_path):
        """测试空上下文提取"""
        context = ExtractionContext(project_path=project_path)

        result = extractor.extract(context)

        assert isinstance(result, list)
        assert len(result) == 0
