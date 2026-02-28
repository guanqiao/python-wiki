"""
设计模式检测器测试
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pywiki.insights.pattern_detector import (
    PatternCategory,
    DetectedPattern,
    DesignPatternDetector,
)
from pywiki.parsers.types import (
    ModuleInfo,
    ClassInfo,
    FunctionInfo,
    PropertyInfo,
    Visibility,
)


class TestPatternCategory:
    """PatternCategory 枚举测试"""

    def test_category_values(self):
        """测试类别值"""
        assert PatternCategory.CREATIONAL.value == "creational"
        assert PatternCategory.STRUCTURAL.value == "structural"
        assert PatternCategory.BEHAVIORAL.value == "behavioral"
        assert PatternCategory.ARCHITECTURAL.value == "architectural"


class TestDetectedPattern:
    """DetectedPattern 数据类测试"""

    def test_create_detected_pattern(self):
        """测试创建检测到的模式"""
        pattern = DetectedPattern(
            pattern_name="Singleton",
            category=PatternCategory.CREATIONAL,
            description="A singleton pattern implementation",
            location="my_module.MyClass",
            confidence=0.8,
        )

        assert pattern.pattern_name == "Singleton"
        assert pattern.category == PatternCategory.CREATIONAL
        assert pattern.confidence == 0.8
        assert pattern.evidence == []
        assert pattern.participants == []
        assert pattern.benefits == []
        assert pattern.drawbacks == []

    def test_create_pattern_with_evidence(self):
        """测试创建带证据的模式"""
        pattern = DetectedPattern(
            pattern_name="Factory Method",
            category=PatternCategory.CREATIONAL,
            description="Factory method pattern",
            location="factory.py",
            confidence=0.75,
            evidence=["create_", "build_"],
            participants=["Factory", "Product"],
            benefits=["Encapsulation", "Flexibility"],
            drawbacks=["Complexity"],
        )

        assert len(pattern.evidence) == 2
        assert len(pattern.participants) == 2
        assert "Encapsulation" in pattern.benefits


class TestDesignPatternDetector:
    """DesignPatternDetector 测试"""

    @pytest.fixture
    def detector(self):
        """创建检测器实例"""
        return DesignPatternDetector()

    def test_detector_initialization(self, detector: DesignPatternDetector):
        """测试检测器初始化"""
        assert detector._pattern_rules is not None
        assert "creational" in detector._pattern_rules
        assert "structural" in detector._pattern_rules
        assert "behavioral" in detector._pattern_rules


class TestSingletonDetection:
    """单例模式检测测试"""

    @pytest.fixture
    def detector(self):
        return DesignPatternDetector()

    def test_detect_singleton_with_instance_variable(self, detector: DesignPatternDetector):
        """测试检测带实例变量的单例"""
        cls = ClassInfo(
            name="Singleton",
            full_name="module.Singleton",
            class_variables=[
                PropertyInfo(name="_instance", type_hint="Singleton"),
            ],
        )

        patterns = detector._detect_singleton(cls)

        assert len(patterns) == 1
        assert patterns[0].pattern_name == "Singleton"
        assert patterns[0].confidence >= 0.6

    def test_detect_singleton_with_new_method(self, detector: DesignPatternDetector):
        """测试检测带 __new__ 方法的单例"""
        cls = ClassInfo(
            name="Singleton",
            full_name="module.Singleton",
            methods=[
                FunctionInfo(name="__new__", full_name="module.Singleton.__new__"),
            ],
        )

        patterns = detector._detect_singleton(cls)

        assert len(patterns) == 1
        assert patterns[0].pattern_name == "Singleton"

    def test_detect_singleton_with_get_instance(self, detector: DesignPatternDetector):
        """测试检测带 get_instance 方法的单例"""
        cls = ClassInfo(
            name="Singleton",
            full_name="module.Singleton",
            methods=[
                FunctionInfo(name="get_instance", full_name="module.Singleton.get_instance"),
            ],
        )

        patterns = detector._detect_singleton(cls)

        assert len(patterns) == 1

    def test_detect_singleton_high_confidence(self, detector: DesignPatternDetector):
        """测试高置信度单例检测"""
        cls = ClassInfo(
            name="Singleton",
            full_name="module.Singleton",
            class_variables=[
                PropertyInfo(name="_instance", type_hint="Singleton"),
            ],
            methods=[
                FunctionInfo(name="__new__", full_name="module.Singleton.__new__"),
                FunctionInfo(name="get_instance", full_name="module.Singleton.get_instance"),
            ],
        )

        patterns = detector._detect_singleton(cls)

        assert len(patterns) == 1
        assert patterns[0].confidence == 0.8

    def test_no_singleton_detected(self, detector: DesignPatternDetector):
        """测试未检测到单例"""
        cls = ClassInfo(
            name="RegularClass",
            full_name="module.RegularClass",
            methods=[
                FunctionInfo(name="do_something", full_name="module.RegularClass.do_something"),
            ],
        )

        patterns = detector._detect_singleton(cls)

        assert len(patterns) == 0


class TestFactoryDetection:
    """工厂模式检测测试"""

    @pytest.fixture
    def detector(self):
        return DesignPatternDetector()

    def test_detect_factory_method(self, detector: DesignPatternDetector):
        """测试检测工厂方法"""
        cls = ClassInfo(
            name="Factory",
            full_name="module.Factory",
            methods=[
                FunctionInfo(name="create_object", full_name="module.Factory.create_object"),
                FunctionInfo(name="build_instance", full_name="module.Factory.build_instance"),
            ],
        )

        patterns = detector._detect_factory(cls)

        assert len(patterns) == 1
        assert patterns[0].pattern_name == "Factory Method"

    def test_detect_factory_with_make_method(self, detector: DesignPatternDetector):
        """测试检测带 make 方法的工厂"""
        cls = ClassInfo(
            name="ObjectFactory",
            full_name="module.ObjectFactory",
            methods=[
                FunctionInfo(name="make_product", full_name="module.ObjectFactory.make_product"),
            ],
        )

        patterns = detector._detect_factory(cls)

        assert len(patterns) == 1

    def test_no_factory_detected(self, detector: DesignPatternDetector):
        """测试未检测到工厂"""
        cls = ClassInfo(
            name="RegularClass",
            full_name="module.RegularClass",
            methods=[
                FunctionInfo(name="process", full_name="module.RegularClass.process"),
            ],
        )

        patterns = detector._detect_factory(cls)

        assert len(patterns) == 0


class TestBuilderDetection:
    """构建者模式检测测试"""

    @pytest.fixture
    def detector(self):
        return DesignPatternDetector()

    def test_detect_builder_pattern(self, detector: DesignPatternDetector):
        """测试检测构建者模式"""
        method_with_self = MagicMock()
        method_with_self.name = "with_name"
        method_with_self.return_type = "self"

        method_with_age = MagicMock()
        method_with_age.name = "with_age"
        method_with_age.return_type = "self"

        cls = ClassInfo(
            name="UserBuilder",
            full_name="module.UserBuilder",
            methods=[
                FunctionInfo(name="build", full_name="module.UserBuilder.build"),
                method_with_self,
                method_with_age,
            ],
        )

        patterns = detector._detect_builder(cls)

        assert len(patterns) == 1
        assert patterns[0].pattern_name == "Builder"

    def test_no_builder_without_build(self, detector: DesignPatternDetector):
        """测试无 build 方法不检测构建者"""
        method_with_self = MagicMock()
        method_with_self.name = "with_name"
        method_with_self.return_type = "self"

        cls = ClassInfo(
            name="ConfigBuilder",
            full_name="module.ConfigBuilder",
            methods=[
                method_with_self,
            ],
        )

        patterns = detector._detect_builder(cls)

        assert len(patterns) == 0


class TestObserverDetection:
    """观察者模式检测测试"""

    @pytest.fixture
    def detector(self):
        return DesignPatternDetector()

    def test_detect_observer_pattern(self, detector: DesignPatternDetector):
        """测试检测观察者模式"""
        cls = ClassInfo(
            name="Subject",
            full_name="module.Subject",
            methods=[
                FunctionInfo(name="subscribe", full_name="module.Subject.subscribe"),
                FunctionInfo(name="notify", full_name="module.Subject.notify"),
                FunctionInfo(name="unsubscribe", full_name="module.Subject.unsubscribe"),
            ],
        )

        patterns = detector._detect_observer(cls)

        assert len(patterns) == 1
        assert patterns[0].pattern_name == "Observer"

    def test_detect_observer_with_attach_detach(self, detector: DesignPatternDetector):
        """测试检测 attach/detach 风格观察者"""
        cls = ClassInfo(
            name="Observable",
            full_name="module.Observable",
            methods=[
                FunctionInfo(name="attach", full_name="module.Observable.attach"),
                FunctionInfo(name="notify", full_name="module.Observable.notify"),
            ],
        )

        patterns = detector._detect_observer(cls)

        assert len(patterns) == 1

    def test_detect_observer_with_emit(self, detector: DesignPatternDetector):
        """测试检测 emit 风格观察者"""
        cls = ClassInfo(
            name="EventEmitter",
            full_name="module.EventEmitter",
            methods=[
                FunctionInfo(name="subscribe", full_name="module.EventEmitter.subscribe"),
                FunctionInfo(name="emit", full_name="module.EventEmitter.emit"),
            ],
        )

        patterns = detector._detect_observer(cls)

        assert len(patterns) == 1

    def test_no_observer_without_notify(self, detector: DesignPatternDetector):
        """测试无 notify 方法不检测观察者"""
        cls = ClassInfo(
            name="RegularClass",
            full_name="module.RegularClass",
            methods=[
                FunctionInfo(name="subscribe", full_name="module.RegularClass.subscribe"),
            ],
        )

        patterns = detector._detect_observer(cls)

        assert len(patterns) == 0


class TestStrategyDetection:
    """策略模式检测测试"""

    @pytest.fixture
    def detector(self):
        return DesignPatternDetector()

    def test_detect_strategy_pattern(self, detector: DesignPatternDetector):
        """测试检测策略模式"""
        cls = ClassInfo(
            name="SortStrategy",
            full_name="module.SortStrategy",
            is_abstract=True,
            methods=[
                FunctionInfo(name="sort", full_name="module.SortStrategy.sort"),
                FunctionInfo(name="compare", full_name="module.SortStrategy.compare"),
            ],
        )

        patterns = detector._detect_strategy(cls)

        assert len(patterns) == 1
        assert patterns[0].pattern_name == "Strategy"

    def test_detect_strategy_with_abc_base(self, detector: DesignPatternDetector):
        """测试检测 ABC 基类策略"""
        cls = ClassInfo(
            name="PaymentStrategy",
            full_name="module.PaymentStrategy",
            bases=["ABC"],
            methods=[
                FunctionInfo(name="pay", full_name="module.PaymentStrategy.pay"),
                FunctionInfo(name="validate", full_name="module.PaymentStrategy.validate"),
            ],
        )

        patterns = detector._detect_strategy(cls)

        assert len(patterns) == 1


class TestDecoratorPatternDetection:
    """装饰器模式检测测试"""

    @pytest.fixture
    def detector(self):
        return DesignPatternDetector()

    def test_detect_decorator_pattern(self, detector: DesignPatternDetector):
        """测试检测装饰器模式"""
        cls = ClassInfo(
            name="CoffeeDecorator",
            full_name="module.CoffeeDecorator",
            bases=["Coffee"],
            properties=[
                PropertyInfo(name="_wrapped", type_hint="Coffee"),
            ],
        )

        patterns = detector._detect_decorator_pattern(cls)

        assert len(patterns) == 1
        assert patterns[0].pattern_name == "Decorator"

    def test_detect_wrapper_pattern(self, detector: DesignPatternDetector):
        """测试检测 Wrapper 模式"""
        cls = ClassInfo(
            name="ServiceWrapper",
            full_name="module.ServiceWrapper",
            bases=["Service"],
            properties=[
                PropertyInfo(name="_component", type_hint="Service"),
            ],
        )

        patterns = detector._detect_decorator_pattern(cls)

        assert len(patterns) == 1


class TestAdapterPatternDetection:
    """适配器模式检测测试"""

    @pytest.fixture
    def detector(self):
        return DesignPatternDetector()

    def test_detect_adapter_by_name(self, detector: DesignPatternDetector):
        """测试通过名称检测适配器"""
        cls = ClassInfo(
            name="DataAdapter",
            full_name="module.DataAdapter",
        )

        result = detector._is_adapter_pattern(cls)

        assert result is True

    def test_detect_wrapper_as_adapter(self, detector: DesignPatternDetector):
        """测试检测 Wrapper 作为适配器"""
        cls = ClassInfo(
            name="APIWrapper",
            full_name="module.APIWrapper",
        )

        result = detector._is_adapter_pattern(cls)

        assert result is True

    def test_no_adapter_detected(self, detector: DesignPatternDetector):
        """测试未检测到适配器"""
        cls = ClassInfo(
            name="DataService",
            full_name="module.DataService",
        )

        result = detector._is_adapter_pattern(cls)

        assert result is False


class TestFacadePatternDetection:
    """外观模式检测测试"""

    @pytest.fixture
    def detector(self):
        return DesignPatternDetector()

    def test_detect_facade_pattern(self, detector: DesignPatternDetector):
        """测试检测外观模式"""
        module = ModuleInfo(
            name="facade_module",
            file_path=Path("/fake/path.py"),
        )

        cls = ClassInfo(
            name="DatabaseFacade",
            full_name="facade_module.DatabaseFacade",
            methods=[
                FunctionInfo(name="method1", full_name="facade_module.DatabaseFacade.method1"),
                FunctionInfo(name="method2", full_name="facade_module.DatabaseFacade.method2"),
                FunctionInfo(name="method3", full_name="facade_module.DatabaseFacade.method3"),
                FunctionInfo(name="method4", full_name="facade_module.DatabaseFacade.method4"),
            ],
        )

        result = detector._is_facade_pattern(cls, module)

        assert result is True

    def test_no_facade_with_few_methods(self, detector: DesignPatternDetector):
        """测试方法少时不检测外观"""
        module = ModuleInfo(
            name="facade_module",
            file_path=Path("/fake/path.py"),
        )

        cls = ClassInfo(
            name="SimpleFacade",
            full_name="facade_module.SimpleFacade",
            methods=[
                FunctionInfo(name="method1", full_name="facade_module.SimpleFacade.method1"),
            ],
        )

        result = detector._is_facade_pattern(cls, module)

        assert result is False


class TestModulePatternDetection:
    """模块级模式检测测试"""

    @pytest.fixture
    def detector(self):
        return DesignPatternDetector()

    def test_detect_from_module(self, detector: DesignPatternDetector):
        """测试从模块检测模式"""
        module = ModuleInfo(
            name="test_module",
            file_path=Path("/fake/path.py"),
            classes=[
                ClassInfo(
                    name="Singleton",
                    full_name="test_module.Singleton",
                    class_variables=[
                        PropertyInfo(name="_instance", type_hint="Singleton"),
                    ],
                    methods=[
                        FunctionInfo(name="get_instance", full_name="test_module.Singleton.get_instance"),
                    ],
                ),
            ],
        )

        patterns = detector.detect_from_module(module)

        assert len(patterns) >= 1
        singleton_patterns = [p for p in patterns if p.pattern_name == "Singleton"]
        assert len(singleton_patterns) >= 1

    def test_detect_from_class(self, detector: DesignPatternDetector):
        """测试从类检测模式"""
        cls = ClassInfo(
            name="Observable",
            full_name="module.Observable",
            methods=[
                FunctionInfo(name="subscribe", full_name="module.Observable.subscribe"),
                FunctionInfo(name="notify", full_name="module.Observable.notify"),
            ],
        )

        patterns = detector.detect_from_class(cls)

        assert len(patterns) >= 1


class TestPatternReport:
    """模式报告生成测试"""

    @pytest.fixture
    def detector(self):
        return DesignPatternDetector()

    def test_generate_pattern_report(self, detector: DesignPatternDetector):
        """测试生成模式报告"""
        patterns = [
            DetectedPattern(
                pattern_name="Singleton",
                category=PatternCategory.CREATIONAL,
                description="Singleton pattern",
                location="module.Singleton",
                confidence=0.8,
            ),
            DetectedPattern(
                pattern_name="Observer",
                category=PatternCategory.BEHAVIORAL,
                description="Observer pattern",
                location="module.Observer",
                confidence=0.7,
            ),
        ]

        report = detector.generate_pattern_report(patterns)

        assert report["total_patterns"] == 2
        assert report["by_category"]["creational"] == 1
        assert report["by_category"]["behavioral"] == 1
        assert len(report["patterns"]) == 2

    def test_generate_empty_report(self, detector: DesignPatternDetector):
        """测试生成空报告"""
        report = detector.generate_pattern_report([])

        assert report["total_patterns"] == 0
        assert report["by_category"] == {}
        assert report["patterns"] == []


class TestHelperMethods:
    """辅助方法测试"""

    @pytest.fixture
    def detector(self):
        return DesignPatternDetector()

    def test_is_factory_function(self, detector: DesignPatternDetector):
        """测试工厂函数检测"""
        create_func = MagicMock()
        create_func.name = "create_user"

        build_func = MagicMock()
        build_func.name = "build_config"

        regular_func = MagicMock()
        regular_func.name = "process_data"

        assert detector._is_factory_function(create_func) is True
        assert detector._is_factory_function(build_func) is True
        assert detector._is_factory_function(regular_func) is False

    def test_is_fluent_method(self, detector: DesignPatternDetector):
        """测试链式方法检测"""
        fluent_method = MagicMock()
        fluent_method.return_type = "self"

        regular_method = MagicMock()
        regular_method.return_type = "void"

        assert detector._is_fluent_method(fluent_method) is True
        assert detector._is_fluent_method(regular_method) is False

    def test_is_observer_pattern_by_name(self, detector: DesignPatternDetector):
        """测试通过名称检测观察者"""
        observer_cls = ClassInfo(name="ClickObserver", full_name="module.ClickObserver")
        listener_cls = ClassInfo(name="EventListener", full_name="module.EventListener")
        subject_cls = ClassInfo(name="EventSubject", full_name="module.EventSubject")
        regular_cls = ClassInfo(name="DataService", full_name="module.DataService")

        assert detector._is_observer_pattern(observer_cls) is True
        assert detector._is_observer_pattern(listener_cls) is True
        assert detector._is_observer_pattern(subject_cls) is True
        assert detector._is_observer_pattern(regular_cls) is False

    def test_is_strategy_pattern_by_name(self, detector: DesignPatternDetector):
        """测试通过名称检测策略"""
        strategy_cls = ClassInfo(name="SortStrategy", full_name="module.SortStrategy")
        policy_cls = ClassInfo(name="CachePolicy", full_name="module.CachePolicy")
        regular_cls = ClassInfo(name="DataService", full_name="module.DataService")

        assert detector._is_strategy_pattern(strategy_cls) is True
        assert detector._is_strategy_pattern(policy_cls) is True
        assert detector._is_strategy_pattern(regular_cls) is False
