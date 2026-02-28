"""
隐性知识提取器测试
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pywiki.knowledge.implicit_extractor import (
    KnowledgeType,
    KnowledgePriority,
    ImplicitKnowledge,
    ExtractionContext,
    BaseKnowledgeExtractor,
    ImplicitKnowledgeExtractor,
)
from pywiki.parsers.types import ModuleInfo, ClassInfo, FunctionInfo


class TestKnowledgeType:
    """KnowledgeType 枚举测试"""

    def test_knowledge_type_values(self):
        """测试知识类型值"""
        assert KnowledgeType.DESIGN_DECISION.value == "design_decision"
        assert KnowledgeType.ARCHITECTURE_PATTERN.value == "architecture_pattern"
        assert KnowledgeType.TECH_DEBT.value == "tech_debt"
        assert KnowledgeType.CODE_SMELL.value == "code_smell"
        assert KnowledgeType.BEST_PRACTICE.value == "best_practice"
        assert KnowledgeType.ANTI_PATTERN.value == "anti_pattern"
        assert KnowledgeType.TRADE_OFF.value == "trade_off"
        assert KnowledgeType.CONSTRAINT.value == "constraint"


class TestKnowledgePriority:
    """KnowledgePriority 枚举测试"""

    def test_priority_values(self):
        """测试优先级值"""
        assert KnowledgePriority.LOW.value == "low"
        assert KnowledgePriority.MEDIUM.value == "medium"
        assert KnowledgePriority.HIGH.value == "high"
        assert KnowledgePriority.CRITICAL.value == "critical"


class TestImplicitKnowledge:
    """ImplicitKnowledge 数据类测试"""

    def test_create_implicit_knowledge(self):
        """测试创建隐性知识"""
        knowledge = ImplicitKnowledge(
            knowledge_type=KnowledgeType.DESIGN_DECISION,
            title="Use Repository Pattern",
            description="Use repository pattern for data access",
            location="data/repository.py",
        )

        assert knowledge.knowledge_type == KnowledgeType.DESIGN_DECISION
        assert knowledge.title == "Use Repository Pattern"
        assert knowledge.confidence == 0.0
        assert knowledge.priority == KnowledgePriority.MEDIUM
        assert knowledge.evidence == []

    def test_create_knowledge_with_all_fields(self):
        """测试创建带所有字段的隐性知识"""
        knowledge = ImplicitKnowledge(
            knowledge_type=KnowledgeType.TECH_DEBT,
            title="Legacy Code",
            description="Legacy code needs refactoring",
            location="legacy/old_module.py",
            evidence=["High complexity", "No tests"],
            confidence=0.85,
            priority=KnowledgePriority.HIGH,
            impact="Maintenance difficulty",
            recommendation="Refactor gradually",
            metadata={"lines": 500},
        )

        assert knowledge.confidence == 0.85
        assert knowledge.priority == KnowledgePriority.HIGH
        assert len(knowledge.evidence) == 2
        assert knowledge.impact == "Maintenance difficulty"
        assert knowledge.recommendation == "Refactor gradually"
        assert knowledge.metadata["lines"] == 500

    def test_to_dict(self):
        """测试转换为字典"""
        knowledge = ImplicitKnowledge(
            knowledge_type=KnowledgeType.BEST_PRACTICE,
            title="Use Type Hints",
            description="Add type hints to all functions",
            location="utils/helpers.py",
            confidence=0.9,
        )

        result = knowledge.to_dict()

        assert result["knowledge_type"] == "best_practice"
        assert result["title"] == "Use Type Hints"
        assert result["confidence"] == 0.9
        assert "created_at" in result


class TestExtractionContext:
    """ExtractionContext 数据类测试"""

    def test_create_empty_context(self):
        """测试创建空上下文"""
        context = ExtractionContext(project_path=Path("/project"))

        assert context.project_path == Path("/project")
        assert context.module_info is None
        assert context.class_info is None
        assert context.function_info is None
        assert context.code_content == ""
        assert context.commit_messages == []

    def test_create_context_with_module(self):
        """测试创建带模块的上下文"""
        module = ModuleInfo(
            name="test_module",
            file_path=Path("/project/test.py"),
        )

        context = ExtractionContext(
            project_path=Path("/project"),
            module_info=module,
            code_content="def hello(): pass",
            commit_messages=["Initial commit", "Add feature"],
        )

        assert context.module_info == module
        assert context.code_content == "def hello(): pass"
        assert len(context.commit_messages) == 2


class TestBaseKnowledgeExtractor:
    """BaseKnowledgeExtractor 基类测试"""

    def test_calculate_confidence_zero_evidence(self):
        """测试零证据置信度计算"""
        class MockExtractor(BaseKnowledgeExtractor):
            @property
            def knowledge_type(self):
                return KnowledgeType.DESIGN_DECISION

            def extract(self, context):
                return []

        extractor = MockExtractor()
        confidence = extractor._calculate_confidence(0)

        assert confidence == 0.0

    def test_calculate_confidence_max_evidence(self):
        """测试最大证据置信度计算"""
        class MockExtractor(BaseKnowledgeExtractor):
            @property
            def knowledge_type(self):
                return KnowledgeType.DESIGN_DECISION

            def extract(self, context):
                return []

        extractor = MockExtractor()
        confidence = extractor._calculate_confidence(5)

        assert confidence == 1.0

    def test_calculate_confidence_partial_evidence(self):
        """测试部分证据置信度计算"""
        class MockExtractor(BaseKnowledgeExtractor):
            @property
            def knowledge_type(self):
                return KnowledgeType.DESIGN_DECISION

            def extract(self, context):
                return []

        extractor = MockExtractor()
        confidence = extractor._calculate_confidence(3)

        assert confidence == 0.6


class TestImplicitKnowledgeExtractor:
    """ImplicitKnowledgeExtractor 测试"""

    @pytest.fixture
    def extractor(self):
        """创建提取器实例"""
        with patch('pywiki.knowledge.implicit_extractor.DesignMotivationExtractor'), \
             patch('pywiki.knowledge.implicit_extractor.ArchitectureDecisionExtractor'), \
             patch('pywiki.knowledge.implicit_extractor.TechDebtDetector'):
            return ImplicitKnowledgeExtractor()

    def test_extractor_initialization(self, extractor: ImplicitKnowledgeExtractor):
        """测试提取器初始化"""
        assert extractor._extractors is not None
        assert extractor._knowledge_cache == {}

    def test_add_extractor(self, extractor: ImplicitKnowledgeExtractor):
        """测试添加提取器"""
        class CustomExtractor(BaseKnowledgeExtractor):
            @property
            def knowledge_type(self):
                return KnowledgeType.BEST_PRACTICE

            def extract(self, context):
                return []

        custom = CustomExtractor()
        initial_count = len(extractor._extractors)

        extractor.add_extractor(custom)

        assert len(extractor._extractors) == initial_count + 1

    def test_remove_extractor(self, extractor: ImplicitKnowledgeExtractor):
        """测试移除提取器"""
        extractor.remove_extractor(KnowledgeType.DESIGN_DECISION)

    def test_remove_nonexistent_extractor(self, extractor: ImplicitKnowledgeExtractor):
        """测试移除不存在的提取器"""
        result = extractor.remove_extractor(KnowledgeType.ANTI_PATTERN)

        assert result is False


class TestImplicitKnowledgeExtractorFromModule:
    """从模块提取隐性知识测试"""

    @pytest.fixture
    def extractor(self):
        with patch('pywiki.knowledge.implicit_extractor.DesignMotivationExtractor') as mock_dm, \
             patch('pywiki.knowledge.implicit_extractor.ArchitectureDecisionExtractor') as mock_ad, \
             patch('pywiki.knowledge.implicit_extractor.TechDebtDetector') as mock_td:

            mock_dm_instance = MagicMock()
            mock_dm_instance.extract.return_value = []
            mock_dm.return_value = mock_dm_instance

            mock_ad_instance = MagicMock()
            mock_ad_instance.extract.return_value = []
            mock_ad.return_value = mock_ad_instance

            mock_td_instance = MagicMock()
            mock_td_instance.extract.return_value = []
            mock_td.return_value = mock_td_instance

            return ImplicitKnowledgeExtractor()

    def test_extract_from_module(self, extractor: ImplicitKnowledgeExtractor):
        """测试从模块提取隐性知识"""
        module = ModuleInfo(
            name="test_module",
            file_path=Path("/project/test.py"),
            classes=[],
        )

        knowledge = extractor.extract_from_module(
            project_path=Path("/project"),
            module=module,
            code_content="def hello(): pass",
        )

        assert isinstance(knowledge, list)

    def test_extract_from_module_with_classes(self, extractor: ImplicitKnowledgeExtractor):
        """测试从带类的模块提取隐性知识"""
        cls = ClassInfo(
            name="TestClass",
            full_name="test_module.TestClass",
            methods=[
                FunctionInfo(name="method1", full_name="test_module.TestClass.method1"),
            ],
        )

        module = ModuleInfo(
            name="test_module",
            file_path=Path("/project/test.py"),
            classes=[cls],
        )

        knowledge = extractor.extract_from_module(
            project_path=Path("/project"),
            module=module,
        )

        assert isinstance(knowledge, list)


class TestImplicitKnowledgeExtractorFromClass:
    """从类提取隐性知识测试"""

    @pytest.fixture
    def extractor(self):
        with patch('pywiki.knowledge.implicit_extractor.DesignMotivationExtractor') as mock_dm, \
             patch('pywiki.knowledge.implicit_extractor.ArchitectureDecisionExtractor') as mock_ad, \
             patch('pywiki.knowledge.implicit_extractor.TechDebtDetector') as mock_td:

            mock_dm_instance = MagicMock()
            mock_dm_instance.extract.return_value = []
            mock_dm.return_value = mock_dm_instance

            mock_ad_instance = MagicMock()
            mock_ad_instance.extract.return_value = []
            mock_ad.return_value = mock_ad_instance

            mock_td_instance = MagicMock()
            mock_td_instance.extract.return_value = []
            mock_td.return_value = mock_td_instance

            return ImplicitKnowledgeExtractor()

    def test_extract_from_class(self, extractor: ImplicitKnowledgeExtractor):
        """测试从类提取隐性知识"""
        cls = ClassInfo(
            name="ServiceClass",
            full_name="module.ServiceClass",
            methods=[
                FunctionInfo(name="process", full_name="module.ServiceClass.process"),
            ],
        )

        knowledge = extractor.extract_from_class(
            project_path=Path("/project"),
            cls=cls,
        )

        assert isinstance(knowledge, list)

    def test_extract_from_class_with_module(self, extractor: ImplicitKnowledgeExtractor):
        """测试从带模块上下文的类提取隐性知识"""
        module = ModuleInfo(
            name="service_module",
            file_path=Path("/project/service.py"),
        )

        cls = ClassInfo(
            name="DataService",
            full_name="service_module.DataService",
        )

        knowledge = extractor.extract_from_class(
            project_path=Path("/project"),
            cls=cls,
            module=module,
            code_content="class DataService: pass",
        )

        assert isinstance(knowledge, list)


class TestImplicitKnowledgeExtractorFromCode:
    """从代码提取隐性知识测试"""

    @pytest.fixture
    def extractor(self):
        with patch('pywiki.knowledge.implicit_extractor.DesignMotivationExtractor') as mock_dm, \
             patch('pywiki.knowledge.implicit_extractor.ArchitectureDecisionExtractor') as mock_ad, \
             patch('pywiki.knowledge.implicit_extractor.TechDebtDetector') as mock_td:

            mock_dm_instance = MagicMock()
            mock_dm_instance.extract.return_value = []
            mock_dm.return_value = mock_dm_instance

            mock_ad_instance = MagicMock()
            mock_ad_instance.extract.return_value = []
            mock_ad.return_value = mock_ad_instance

            mock_td_instance = MagicMock()
            mock_td_instance.extract.return_value = []
            mock_td.return_value = mock_td_instance

            return ImplicitKnowledgeExtractor()

    def test_extract_from_code(self, extractor: ImplicitKnowledgeExtractor):
        """测试从代码内容提取隐性知识"""
        code = '''
def process_data(data):
    """Process the data."""
    # TODO: Refactor this
    result = []
    for item in data:
        result.append(item.upper())
    return result
'''

        knowledge = extractor.extract_from_code(
            project_path=Path("/project"),
            code_content=code,
        )

        assert isinstance(knowledge, list)

    def test_extract_from_code_with_file_path(self, extractor: ImplicitKnowledgeExtractor):
        """测试从代码内容带文件路径提取隐性知识"""
        knowledge = extractor.extract_from_code(
            project_path=Path("/project"),
            code_content="def hello(): pass",
            file_path=Path("/project/hello.py"),
        )

        assert isinstance(knowledge, list)


class TestImplicitKnowledgeExtractorFiltering:
    """隐性知识筛选测试"""

    @pytest.fixture
    def extractor(self):
        with patch('pywiki.knowledge.implicit_extractor.DesignMotivationExtractor'), \
             patch('pywiki.knowledge.implicit_extractor.ArchitectureDecisionExtractor'), \
             patch('pywiki.knowledge.implicit_extractor.TechDebtDetector'):
            return ImplicitKnowledgeExtractor()

    def test_get_knowledge_by_type(self, extractor: ImplicitKnowledgeExtractor):
        """测试按类型筛选知识"""
        knowledge_list = [
            ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title="Decision 1",
                description="Description",
                location="loc1",
            ),
            ImplicitKnowledge(
                knowledge_type=KnowledgeType.TECH_DEBT,
                title="Debt 1",
                description="Description",
                location="loc2",
            ),
            ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title="Decision 2",
                description="Description",
                location="loc3",
            ),
        ]

        filtered = extractor.get_knowledge_by_type(
            knowledge_list,
            KnowledgeType.DESIGN_DECISION,
        )

        assert len(filtered) == 2
        for k in filtered:
            assert k.knowledge_type == KnowledgeType.DESIGN_DECISION

    def test_get_knowledge_by_priority(self, extractor: ImplicitKnowledgeExtractor):
        """测试按优先级筛选知识"""
        knowledge_list = [
            ImplicitKnowledge(
                knowledge_type=KnowledgeType.TECH_DEBT,
                title="Low",
                description="Description",
                location="loc1",
                priority=KnowledgePriority.LOW,
            ),
            ImplicitKnowledge(
                knowledge_type=KnowledgeType.TECH_DEBT,
                title="High",
                description="Description",
                location="loc2",
                priority=KnowledgePriority.HIGH,
            ),
            ImplicitKnowledge(
                knowledge_type=KnowledgeType.TECH_DEBT,
                title="Critical",
                description="Description",
                location="loc3",
                priority=KnowledgePriority.CRITICAL,
            ),
        ]

        filtered = extractor.get_knowledge_by_priority(
            knowledge_list,
            KnowledgePriority.HIGH,
        )

        assert len(filtered) == 2
        for k in filtered:
            assert k.priority in [KnowledgePriority.HIGH, KnowledgePriority.CRITICAL]

    def test_get_high_confidence_knowledge(self, extractor: ImplicitKnowledgeExtractor):
        """测试获取高置信度知识"""
        knowledge_list = [
            ImplicitKnowledge(
                knowledge_type=KnowledgeType.BEST_PRACTICE,
                title="Low confidence",
                description="Description",
                location="loc1",
                confidence=0.5,
            ),
            ImplicitKnowledge(
                knowledge_type=KnowledgeType.BEST_PRACTICE,
                title="High confidence",
                description="Description",
                location="loc2",
                confidence=0.9,
            ),
        ]

        filtered = extractor.get_high_confidence_knowledge(
            knowledge_list,
            min_confidence=0.7,
        )

        assert len(filtered) == 1
        assert filtered[0].confidence >= 0.7


class TestImplicitKnowledgeExtractorReport:
    """知识报告生成测试"""

    @pytest.fixture
    def extractor(self):
        with patch('pywiki.knowledge.implicit_extractor.DesignMotivationExtractor'), \
             patch('pywiki.knowledge.implicit_extractor.ArchitectureDecisionExtractor'), \
             patch('pywiki.knowledge.implicit_extractor.TechDebtDetector'):
            return ImplicitKnowledgeExtractor()

    def test_generate_report(self, extractor: ImplicitKnowledgeExtractor):
        """测试生成知识报告"""
        knowledge_list = [
            ImplicitKnowledge(
                knowledge_type=KnowledgeType.DESIGN_DECISION,
                title="Decision 1",
                description="Description",
                location="loc1",
                confidence=0.8,
                priority=KnowledgePriority.HIGH,
            ),
            ImplicitKnowledge(
                knowledge_type=KnowledgeType.TECH_DEBT,
                title="Debt 1",
                description="Description",
                location="loc2",
                confidence=0.9,
                priority=KnowledgePriority.CRITICAL,
            ),
        ]

        report = extractor.generate_report(knowledge_list)

        assert report["total_knowledge"] == 2
        assert "by_type" in report
        assert "by_priority" in report
        assert report["high_confidence_count"] == 2
        assert len(report["knowledge"]) == 2

    def test_generate_empty_report(self, extractor: ImplicitKnowledgeExtractor):
        """测试生成空知识报告"""
        report = extractor.generate_report([])

        assert report["total_knowledge"] == 0
        assert report["by_type"] == {}
        assert report["by_priority"] == {}
        assert report["high_confidence_count"] == 0
        assert report["knowledge"] == []


class TestImplicitKnowledgeExtractorCache:
    """缓存测试"""

    @pytest.fixture
    def extractor(self):
        with patch('pywiki.knowledge.implicit_extractor.DesignMotivationExtractor'), \
             patch('pywiki.knowledge.implicit_extractor.ArchitectureDecisionExtractor'), \
             patch('pywiki.knowledge.implicit_extractor.TechDebtDetector'):
            return ImplicitKnowledgeExtractor()

    def test_clear_cache(self, extractor: ImplicitKnowledgeExtractor):
        """测试清空缓存"""
        extractor._knowledge_cache["test_key"] = []

        extractor.clear_cache()

        assert extractor._knowledge_cache == {}

    def test_cache_initially_empty(self, extractor: ImplicitKnowledgeExtractor):
        """测试缓存初始为空"""
        assert extractor._knowledge_cache == {}
